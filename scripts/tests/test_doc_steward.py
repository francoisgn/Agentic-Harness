"""Tests of scripts/doc-steward.py (offline: the HTTP function is injected, no network)."""
import datetime
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("doc_steward", ROOT / "scripts" / "doc-steward.py")
ds = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ds)

REPO = "acme/app"
NOW = datetime.datetime(2026, 11, 10, 12, 0, tzinfo=datetime.timezone.utc)
STEWARD = "/repos/acme/app/pulls?state=closed&head=acme%3Adocs%2Fsteward&per_page=100&page=1"
MERGED = "/repos/acme/app/pulls?state=closed&base=develop&sort=updated&direction=desc&per_page=100&page=1"
LEDGER = "/repos/acme/app/issues?state=closed&labels=ledger&per_page=100&page=1"
OPEN_AUDIT = "/repos/acme/app/issues?state=open&labels=type%3A%20docs&per_page=100&page=1"


def pr(number, merged_at, body="", head="feat/x", updated_at=None, title=None):
    return {"number": number, "title": title or f"PR {number}", "body": body, "merged_at": merged_at,
            "updated_at": updated_at or merged_at or "2026-11-01T00:00:00Z", "head": {"ref": head},
            "html_url": f"https://github.com/acme/app/pull/{number}"}


def ledger_issue(number, merged_at="2026-11-09T00:00:00Z"):
    return {"number": number, "pull_request": {"merged_at": merged_at}, "labels": [{"name": "ledger"}]}


class FakeGitHub:
    """GET answers from a dict (an unknown path fails the test loudly); POSTs are recorded."""

    def __init__(self, responses):
        self.responses, self.posts = responses, []

    def __call__(self, path, data=None):
        if data is not None:
            self.posts.append((path, data))
            return {"number": 100 + len(self.posts)}
        if path not in self.responses:
            raise AssertionError(f"unexpected request {path}")
        return self.responses[path]


def offline(_path, data=None):
    raise ds.FetchError("network unreachable")


def pending(responses, ledger_label="ledger"):
    return ds.pending(REPO, "develop", "docs/steward", ledger_label, FakeGitHub(responses), now=NOW)


class DocsLineTests(unittest.TestCase):
    def test_files_listed(self):
        self.assertEqual(ds.docs_files("Body\n\nDocs: README.md, `docs/USAGE.md`\n"), ["README.md", "docs/USAGE.md"])

    def test_none_and_missing(self):
        self.assertEqual(ds.docs_files("Docs: none (internal refactor)"), [])
        self.assertIsNone(ds.docs_files("No line here"))

    def test_ignores_fenced_blocks_and_comments(self):
        body = "```text\nDocs: fake.md\n```\n<!-- Docs: hidden.md -->\nDocs: real.md\n"
        self.assertEqual(ds.docs_files(body), ["real.md"])

    def test_ledger_section_wins_when_a_heading_is_given(self):
        body = "Docs: body.md\n\n### Ledger\n\n```changelog\nx\n```\nDocs: docs/A.md\n\n### Tests\n"
        self.assertEqual(ds.docs_files(body, "### Ledger"), ["docs/A.md"])

    def test_markdown_links_are_read_as_paths(self):
        self.assertEqual(ds.docs_files("- Docs: [usage](docs/USAGE.md)"), ["docs/USAGE.md"])


class PendingTests(unittest.TestCase):
    def test_nothing_to_fold(self):
        result = pending({
            STEWARD: [],
            MERGED: [pr(5, "2026-11-08T00:00:00Z", "Docs: none (tests only)"), pr(6, None, "Docs: README.md")],
            LEDGER: [],
        })
        self.assertFalse(result["fold"])
        self.assertEqual(result["docs"], [])
        self.assertEqual(result["ledger"], [])

    def test_docs_line_since_the_last_merged_steward_pr(self):
        steward = pr(3, "2026-11-05T00:00:00Z", "Steward-Through: 2026-11-04T00:00:00Z\nFolded: none", head="docs/steward")
        result = pending({
            STEWARD: [steward],
            MERGED: [
                pr(9, "2026-11-09T00:00:00Z", "Docs: docs/USAGE.md"),
                pr(3, "2026-11-05T00:00:00Z", "Docs: README.md", head="docs/steward"),
                pr(2, "2026-11-03T00:00:00Z", "Docs: OLD.md", updated_at="2026-11-03T00:00:00Z"),
            ],
            LEDGER: [],
        })
        self.assertTrue(result["fold"])
        self.assertEqual(result["since"], "2026-11-04T00:00:00Z")
        self.assertEqual([d["number"] for d in result["docs"]], [9])
        self.assertEqual(result["docs"][0]["files"], ["docs/USAGE.md"])
        self.assertEqual(result["through"], "2026-11-09T00:00:00Z")

    def test_first_pass_looks_back_a_bounded_window(self):
        result = pending({
            STEWARD: [],
            MERGED: [pr(9, "2026-11-09T00:00:00Z", "Docs: a.md"),
                     pr(1, "2026-10-01T00:00:00Z", "Docs: b.md", updated_at="2026-10-01T00:00:00Z")],
            LEDGER: [],
        })
        self.assertEqual([d["number"] for d in result["docs"]], [9])
        self.assertEqual(result["since"], "2026-11-03T12:00:00Z")

    def test_ledger_entries_pending_and_folded_ones_marked_done(self):
        steward = pr(3, "2026-11-05T00:00:00Z", "Steward-Through: 2026-11-05T00:00:00Z\nFolded: #7", head="docs/steward")
        result = pending({
            STEWARD: [steward],
            MERGED: [],
            LEDGER: [ledger_issue(7), ledger_issue(8), ledger_issue(11, merged_at=None)],
        })
        self.assertTrue(result["fold"])
        self.assertEqual(result["ledger"], [8])
        self.assertEqual(result["mark_done"], [7])

    def test_an_entry_already_marked_done_is_not_swapped_again(self):
        steward = pr(3, "2026-11-05T00:00:00Z", "Steward-Through: 2026-11-05T00:00:00Z\nFolded: #7", head="docs/steward")
        result = pending({STEWARD: [steward], MERGED: [], LEDGER: [ledger_issue(8)]})
        self.assertEqual(result["mark_done"], [])
        self.assertEqual(result["ledger"], [8])

    def test_no_ledger_label_means_no_ledger_request(self):
        result = pending({STEWARD: [], MERGED: [], }, ledger_label="")
        self.assertFalse(result["fold"])

    def test_api_error_is_reported_not_guessed(self):
        with self.assertRaises(ds.FetchError):
            ds.pending(REPO, "develop", "docs/steward", "ledger", offline, now=NOW)


class BodyTests(unittest.TestCase):
    def test_body_carries_the_markers_and_lists_unplaced_entries(self):
        result = {"fold": True, "since": "a", "through": "2026-11-09T00:00:00Z", "ledger": [8, 12], "mark_done": [],
                  "docs": [{"number": 9, "title": "Add X", "files": ["docs/USAGE.md"]}]}
        body = ds.body(result, folded=[8], fold_log="malformed entry in #12\n", unplaced="#9: docs/USAGE.md has no X section\n")
        self.assertIn("Steward-Through: 2026-11-09T00:00:00Z", body)
        self.assertIn("Folded: #8\n", body)
        self.assertIn("#9", body)
        self.assertIn("malformed entry in #12", body)
        self.assertIn("docs/USAGE.md has no X section", body)
        self.assertIn("left in place", body)
        self.assertIn("#12: ledger entry not folded", body)
        self.assertNotIn("#8: ledger entry not folded", body)
        self.assertTrue(body.rstrip().endswith("_Generated by [Claude Code](https://claude.ai/code)_"))

    def test_folded_defaults_to_every_pending_entry(self):
        body = ds.body({"through": "t", "ledger": [8, 12], "docs": []})
        self.assertIn("Folded: #8 #12\n", body)
        self.assertIn("Folded: none", ds.body({"through": "t", "ledger": [], "docs": []}))

    def test_round_trip_with_pending(self):
        body = ds.body({"through": "2026-11-09T00:00:00Z", "ledger": [8], "docs": []})
        self.assertEqual(ds.markers(body), ("2026-11-09T00:00:00Z", [8]))


class AuditTests(unittest.TestCase):
    REPORTS = {
        "readme": "✘ no Contributing section\n✘ image without alt text: x.png\n🔴 README: 2 gap(s)\n",
        "links": "docs/A.md:3: broken link B.md\n1 broken link(s) in 4 Markdown file(s) (relative links and cross-file anchors)\n",
        "progress": "🟠 progress block of README.md differs from the issues; run readme-progress.py to rewrite it:\n--- committed\n+++ generated\n",
    }

    def test_one_gap_per_line_of_each_failed_check(self):
        gaps = ds.gaps(self.REPORTS)
        self.assertEqual(len(gaps), 4)
        self.assertIn(("readme", "no Contributing section"), gaps)
        self.assertIn(("links", "docs/A.md:3: broken link B.md"), gaps)
        self.assertEqual(sum(1 for c, _ in gaps if c == "progress"), 1)

    def test_one_issue_per_new_gap_none_for_a_known_one(self):
        gh = FakeGitHub({OPEN_AUDIT: [{"title": "Doc audit (readme): no Contributing section"}]})
        out = io.StringIO()
        created = ds.audit(REPO, self.REPORTS, "type: docs", gh, out=out)
        self.assertEqual(created, 3)
        titles = [data["title"] for _, data in gh.posts]
        self.assertNotIn("Doc audit (readme): no Contributing section", titles)
        self.assertIn("Doc audit (links): docs/A.md:3: broken link B.md", titles)
        self.assertTrue(all(data["labels"] == ["type: docs"] for _, data in gh.posts))
        self.assertTrue(all("Generated by" in data["body"] for _, data in gh.posts))

    def test_dry_run_writes_nothing(self):
        gh = FakeGitHub({OPEN_AUDIT: []})
        ds.audit(REPO, self.REPORTS, "type: docs", gh, dry_run=True, out=io.StringIO())
        self.assertEqual(gh.posts, [])

    def test_issues_are_capped(self):
        many = {"readme": "".join(f"✘ gap {i}\n" for i in range(40))}
        gh = FakeGitHub({OPEN_AUDIT: []})
        self.assertEqual(ds.audit(REPO, many, "type: docs", gh, out=io.StringIO()), ds.MAX_ISSUES)


class CliTests(unittest.TestCase):
    def test_pending_writes_json_and_exits_2_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / "p.json"
            code = ds.run(["pending", "--repo", REPO, "--base", "develop", "--json-out", str(out)],
                          http=offline, env={"GH_TOKEN": "t"}, out=io.StringIO())
            self.assertEqual(code, 2)
            code = ds.run(["pending", "--repo", REPO, "--base", "develop", "--ledger-label", "", "--json-out", str(out)],
                          http=FakeGitHub({STEWARD: [], MERGED: []}), env={"GH_TOKEN": "t"}, out=io.StringIO())
            self.assertEqual(code, 0)
            self.assertFalse(json.loads(out.read_text(encoding="utf-8"))["fold"])

    def test_no_token_exits_2(self):
        self.assertEqual(ds.run(["pending", "--repo", REPO, "--base", "develop"], env={}, out=io.StringIO()), 2)

    def test_protected_branch_is_refused(self):
        self.assertEqual(ds.run(["pending", "--repo", REPO, "--base", "develop", "--branch", "develop"],
                                env={"GH_TOKEN": "t"}, out=io.StringIO()), 2)


if __name__ == "__main__":
    unittest.main()

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
OPEN_FOLD = "/repos/acme/app/pulls?state=open&head=acme%3Adocs%2Fsteward&per_page=100&page=1"
WORKFLOW = (ROOT / ".github/workflows/doc-steward.yml").read_text(encoding="utf-8")


def pr(number, merged_at, body="", head="feat/x", updated_at=None, title=None, labels=()):
    return {"number": number, "title": title or f"PR {number}", "body": body, "merged_at": merged_at,
            "updated_at": updated_at or merged_at or "2026-11-01T00:00:00Z", "head": {"ref": head},
            "html_url": f"https://github.com/acme/app/pull/{number}", "labels": [{"name": n} for n in labels]}


def issue(number, *labels):
    """GET /repos/acme/app/issues/<number>: the labels of a PR the last steward PR folded."""
    return f"/repos/acme/app/issues/{number}", {"number": number, "labels": [{"name": n} for n in labels]}


def ledger_body(*blocks, docs="Docs: none (tests only)"):
    """A PR body whose `### Ledger` section holds these lines (blocks or `None (…)`), then the `Docs:` line."""
    return "Closes #1\n\n### Ledger\n\n" + "\n".join(blocks) + f"\n{docs}\n\n### Tests\n\nunit\n"


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


class LedgerSectionTests(unittest.TestCase):
    def test_typed_blocks_are_entries(self):
        sec = ds.ledger_section(ledger_body("```changelog", "a", "```", "~~~gap-new", "b", "~~~"), "### Ledger")
        self.assertEqual((sec["present"], sec["entries"], sec["problems"]), (True, 2, []))

    def test_explicit_empty_section_has_one_spelling(self):
        self.assertEqual(ds.ledger_section(ledger_body("None (tests only)"), "### Ledger")["problems"], [])
        self.assertEqual(ds.ledger_section(ledger_body("- None (tests only)"), "### Ledger")["problems"], [])
        problems = ds.ledger_section(ledger_body("None"), "### Ledger")["problems"]
        self.assertEqual(len(problems), 1)
        self.assertIn("None (<reason>)", problems[0])

    def test_section_absent_or_docs_only(self):
        self.assertFalse(ds.ledger_section("Closes #1\nDocs: none (x)\n", "### Ledger")["present"])
        sec = ds.ledger_section(ledger_body(), "### Ledger")
        self.assertEqual((sec["present"], sec["entries"], sec["problems"]), (True, 0, []))

    def test_untyped_and_unclosed_blocks_are_malformed(self):
        problems = ds.ledger_section(ledger_body("```", "Added X", "```"), "### Ledger")["problems"]
        self.assertEqual(len(problems), 1)
        self.assertIn("Added X", problems[0])
        problems = ds.ledger_section("### Ledger\n\n```changelog\nAdded Y\n", "### Ledger")["problems"]
        self.assertEqual(len(problems), 1)
        self.assertIn("not closed", problems[0])

    def test_none_with_entries_is_contradictory(self):
        problems = ds.ledger_section(ledger_body("None (x)", "```changelog", "a", "```"), "### Ledger")["problems"]
        self.assertEqual(len(problems), 1)

    def test_blocks_outside_the_section_and_in_comments_do_not_count(self):
        body = "```changelog\nout\n```\n### Ledger\n<!-- ```changelog\nhidden\n``` -->\nDocs: none (x)\n### Next\n```gap-new\ny\n```\n"
        self.assertEqual(ds.ledger_section(body, "### Ledger")["entries"], 0)


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

    def test_ledger_label_still_read_as_a_hint_and_folded_ones_marked_done(self):
        steward = pr(3, "2026-11-05T00:00:00Z", "Steward-Through: 2026-11-05T00:00:00Z\nFolded: #7", head="docs/steward")
        result = pending(dict([issue(7, "ledger")], **{
            STEWARD: [steward],
            MERGED: [],
            LEDGER: [ledger_issue(7), ledger_issue(8), ledger_issue(11, merged_at=None)],
        }))
        self.assertTrue(result["fold"])
        self.assertEqual(result["ledger"], [8])
        self.assertEqual(result["mark_done"], [7])

    def test_an_entry_already_marked_done_is_not_marked_again(self):
        steward = pr(3, "2026-11-05T00:00:00Z", "Steward-Through: 2026-11-05T00:00:00Z\nFolded: #7", head="docs/steward")
        result = pending(dict([issue(7, "ledger: done")], **{STEWARD: [steward], MERGED: [], LEDGER: [ledger_issue(8)]}))
        self.assertEqual(result["mark_done"], [])
        self.assertEqual(result["ledger"], [8])

    def test_a_folded_pr_without_any_label_is_marked_done(self):
        steward = pr(3, "2026-11-05T00:00:00Z", "Steward-Through: 2026-11-05T00:00:00Z\nFolded: #7", head="docs/steward")
        result = pending(dict([issue(7)], **{STEWARD: [steward], MERGED: [], LEDGER: []}))
        self.assertEqual(result["mark_done"], [7])

    def test_ledger_entries_found_from_the_section_without_the_label(self):
        result = pending({
            STEWARD: [],
            MERGED: [pr(9, "2026-11-09T00:00:00Z", ledger_body("```changelog", "Added X", "```")),
                     pr(10, "2026-11-09T00:00:00Z", ledger_body("None (tests only)")),
                     pr(12, "2026-11-09T00:00:00Z", "Docs: none (no ledger section)"),
                     pr(13, "2026-11-09T00:00:00Z", ledger_body("```changelog", "Old", "```"), labels=["ledger: done"])],
            LEDGER: [],
        })
        self.assertTrue(result["fold"])
        self.assertEqual(result["ledger"], [9])
        self.assertEqual(result["malformed"], [])

    def test_entries_not_folded_by_the_last_pass_stay_pending(self):
        steward = pr(3, "2026-11-05T00:00:00Z", "Steward-Through: 2026-11-05T00:00:00Z\nFolded: #7\n\n"
                     "## Ledger fold\n\nPending entries: #7 #8.\n", head="docs/steward")
        result = pending(dict([issue(7)], **{STEWARD: [steward], MERGED: [], LEDGER: []}))
        self.assertEqual(result["ledger"], [8])
        self.assertEqual(result["mark_done"], [7])

    def test_malformed_entry_is_reported_with_the_entry_not_skipped(self):
        result = pending({
            STEWARD: [],
            MERGED: [pr(9, "2026-11-09T00:00:00Z", ledger_body("```", "Added X without a type", "```"))],
            LEDGER: [],
        })
        self.assertTrue(result["fold"])
        self.assertEqual([m["number"] for m in result["malformed"]], [9])
        self.assertIn("Added X without a type", result["malformed"][0]["problems"][0])
        body = ds.body(result)
        self.assertIn("#9: malformed ledger entry", body)
        self.assertIn("Added X without a type", body)
        self.assertIn(ds.LEDGER_FORMAT, body)

    def test_no_ledger_label_means_no_ledger_request(self):
        result = pending({STEWARD: [], MERGED: [], }, ledger_label="")
        self.assertFalse(result["fold"])

    def test_api_error_is_reported_not_guessed(self):
        with self.assertRaises(ds.FetchError):
            ds.pending(REPO, "develop", "docs/steward", "ledger", offline, now=NOW)

    def test_ledger_order_is_merge_order_for_the_first_merged_wins_rule(self):
        steward = pr(3, "2026-11-05T00:00:00Z", "Steward-Through: 2026-11-05T00:00:00Z\nFolded: none\n\n"
                     "Pending entries: #4.\n", head="docs/steward")
        result = pending({
            STEWARD: [steward],
            MERGED: [pr(9, "2026-11-09T00:00:00Z", ledger_body("```changelog", "B", "```")),
                     pr(12, "2026-11-08T00:00:00Z", ledger_body("```changelog", "A", "```"))],
            LEDGER: [ledger_issue(7, merged_at="2026-11-08T12:00:00Z")],
        })
        self.assertEqual(result["ledger"], [4, 7, 9, 12])
        # Carried from the last pass (merged before it) first, then by merge time
        self.assertEqual(result["ledger_order"], [4, 12, 7, 9])


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
        self.assertIn("## Unplaced entries", body)
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


class ContestedTests(unittest.TestCase):
    RESULT = {"through": "t", "ledger": [9, 12, 15], "docs": []}

    def test_contested_cell_reported_with_both_entries_apart_from_unplaced(self):
        contested = json.dumps({"place": "docs/gaps.md: row Export, column Status", "first": 9,
                                "first_text": "| Export | done |", "second": 12, "second_text": "| Export | partial |"})
        body = ds.body(self.RESULT, folded=[9, 12], contested=contested + "\n", unplaced="#15: docs/X.md missing\n")
        self.assertIn("## Contested entries", body)
        self.assertIn("## Unplaced entries", body)
        contested_part, unplaced_part = body.split("## Contested entries")[1].split("## Unplaced entries")
        self.assertIn("docs/gaps.md: row Export, column Status: contested: #9 vs #12", contested_part)
        self.assertIn("| Export | done |", contested_part)
        self.assertIn("| Export | partial |", contested_part)
        self.assertIn("#9 merged first", contested_part)
        self.assertNotIn("docs/X.md missing", contested_part)
        self.assertIn("docs/X.md missing", unplaced_part)
        self.assertIn("#15: ledger entry not folded", unplaced_part)
        self.assertNotIn("Export", unplaced_part)

    def test_unreadable_contested_line_is_kept_never_dropped(self):
        body = ds.body(self.RESULT, contested="row X: #9 vs #12 (not JSON)\n")
        part = body.split("## Contested entries")[1].split("## Unplaced entries")[0]
        self.assertIn("row X: #9 vs #12 (not JSON)", part)

    def test_no_contested_entry_says_none(self):
        part = ds.body(self.RESULT).split("## Contested entries")[1].split("## Unplaced entries")[0]
        self.assertIn("None.", part)

    def test_body_cli_reads_the_contested_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            pend, cont = pathlib.Path(tmp) / "p.json", pathlib.Path(tmp) / "c.jsonl"
            pend.write_text(json.dumps(self.RESULT), encoding="utf-8")
            cont.write_text(json.dumps({"place": "P", "first": 9, "first_text": "a", "second": 12,
                                        "second_text": "b"}) + "\n", encoding="utf-8")
            out = io.StringIO()
            self.assertEqual(ds.run(["body", "--pending", str(pend), "--contested", str(cont)], out=out), 0)
            self.assertIn("P: contested: #9 vs #12", out.getvalue())

    def test_workflow_hands_the_contract_to_the_fold_command(self):
        self.assertIn("STEWARD_CONTESTED=", WORKFLOW)
        self.assertIn(".ledger_order", WORKFLOW)
        self.assertIn("--contested", WORKFLOW)


class FoldGuardTests(unittest.TestCase):
    OPEN = pr(41, None, head="docs/steward")

    def guard(self, responses, *extra):
        out = io.StringIO()
        code = ds.run(["fold-guard", "--repo", REPO, *extra], http=FakeGitHub(responses), env={"GH_TOKEN": "t"},
                      out=out)
        return code, out.getvalue()

    def test_second_fold_refused_with_the_link_to_the_open_one(self):
        code, text = self.guard({OPEN_FOLD: [self.OPEN]})
        self.assertEqual(code, 1)
        self.assertIn("#41", text)
        self.assertIn("https://github.com/acme/app/pull/41", text)

    def test_free_when_no_fold_pr_is_open(self):
        code, text = self.guard({OPEN_FOLD: []})
        self.assertEqual(code, 0)
        self.assertIn("docs/steward", text)

    def test_fold_from_another_branch_is_refused(self):
        code, text = self.guard({OPEN_FOLD: []}, "--head-branch", "docs/ledger-fold-2")
        self.assertEqual(code, 1)
        self.assertIn("docs/steward", text)

    def test_could_not_check_exits_2(self):
        out = io.StringIO()
        self.assertEqual(ds.run(["fold-guard", "--repo", REPO], http=offline, env={"GH_TOKEN": "t"}, out=out), 2)
        self.assertEqual(ds.run(["fold-guard", "--repo", REPO], env={}, out=out), 2)

    def test_pending_refuses_a_second_fold_and_reads_nothing_else(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "p.json"
            out = io.StringIO()
            code = ds.run(["pending", "--repo", REPO, "--base", "develop", "--ledger-label", "ledger",
                           "--json-out", str(path)], http=FakeGitHub({OPEN_FOLD: [self.OPEN]}),
                          env={"GH_TOKEN": "t"}, out=out)
            self.assertEqual(code, 0)
            result = json.loads(path.read_text(encoding="utf-8"))
            self.assertFalse(result["fold"])
            self.assertEqual(result["open_fold"]["number"], 41)
            self.assertIn("https://github.com/acme/app/pull/41", out.getvalue())

    def test_pending_says_to_fold_and_never_nothing_to_fold_when_there_is_work(self):
        # Regression: a for/else printed "nothing to fold … no agent started" on every run, work or not
        yesterday = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        responses = {OPEN_FOLD: [], STEWARD: [], LEDGER: [], MERGED: [pr(5, yesterday, "Docs: README.md")]}
        out = io.StringIO()
        code = ds.run(["pending", "--repo", REPO, "--base", "develop", "--ledger-label", "ledger"],
                      http=FakeGitHub(responses), env={"GH_TOKEN": "t"}, out=out)
        self.assertEqual(code, 0)
        self.assertIn("to fold since", out.getvalue())
        self.assertNotIn("nothing to fold", out.getvalue())

    def test_publish_checks_the_guard_before_pushing(self):
        publish = WORKFLOW.split("\n  publish:")[1].split("\n  audit:")[0]
        self.assertIn("fold-guard", publish)
        self.assertLess(publish.index("fold-guard"), publish.index("git push"))
        self.assertNotIn("gh pr edit", publish)


class NoteTests(unittest.TestCase):
    DOC = "# Gaps\n\n## Table\n\n| a | b |\n\n## Notes\n\nFirst note.\n\n### Detail\n\nd\n\n## After\n\nz\n"

    def test_note_folded_at_the_end_of_its_section(self):
        text = ds.place_note(self.DOC, "Notes", "Second note.")
        self.assertIn("d\n\nSecond note.\n\n## After", text)
        self.assertEqual(ds.place_note(text, "Notes", "Second note."), text)   # idempotent

    def test_note_without_heading_goes_to_the_end_of_the_file(self):
        self.assertTrue(ds.place_note(self.DOC, None, "Tail.").endswith("z\n\nTail.\n"))

    def test_missing_heading_is_unplaced(self):
        with self.assertRaises(ValueError):
            ds.place_note(self.DOC, "Nowhere", "x")

    def note(self, root, entry):
        e = pathlib.Path(root) / "entry.txt"
        e.write_text(entry, encoding="utf-8")
        out = io.StringIO()
        return ds.run(["note", "--entry", str(e), "--root", str(root)], env={}, out=out), out.getvalue()

    def test_note_cli_folds_without_asking(self):
        with tempfile.TemporaryDirectory() as tmp:
            (pathlib.Path(tmp) / "docs").mkdir()
            doc = pathlib.Path(tmp) / "docs/gaps.md"
            doc.write_text(self.DOC, encoding="utf-8")
            code, _ = self.note(tmp, "docs/gaps.md § Notes\nSecond note.\n")
            self.assertEqual(code, 0)
            self.assertIn("Second note.\n\n## After", doc.read_text(encoding="utf-8"))

    def test_note_cli_reports_what_it_cannot_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            (pathlib.Path(tmp) / "a.md").write_text("# A\n", encoding="utf-8")
            for entry in ("missing.md\nx\n", "a.md § Nowhere\nx\n", "../a.md\nx\n", ".github/x.md\nx\n",
                          "a.md\n\n", ""):
                code, text = self.note(tmp, entry)
                self.assertEqual(code, 1, entry)
                self.assertIn("unplaced", text)
            self.assertEqual((pathlib.Path(tmp) / "a.md").read_text(encoding="utf-8"), "# A\n")


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
                          http=FakeGitHub({OPEN_FOLD: [], STEWARD: [], MERGED: []}), env={"GH_TOKEN": "t"},
                          out=io.StringIO())
            self.assertEqual(code, 0)
            self.assertFalse(json.loads(out.read_text(encoding="utf-8"))["fold"])

    def test_no_token_exits_2(self):
        self.assertEqual(ds.run(["pending", "--repo", REPO, "--base", "develop"], env={}, out=io.StringIO()), 2)

    def test_protected_branch_is_refused(self):
        self.assertEqual(ds.run(["pending", "--repo", REPO, "--base", "develop", "--branch", "develop"],
                                env={"GH_TOKEN": "t"}, out=io.StringIO()), 2)


if __name__ == "__main__":
    unittest.main()

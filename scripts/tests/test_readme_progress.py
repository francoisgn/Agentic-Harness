"""Tests of scripts/readme-progress.py on recorded API fixtures (offline: the HTTP function is injected)."""
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("readme_progress", ROOT / "scripts" / "readme-progress.py")
rp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rp)

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures" / "readme-progress"
R = "https://github.com/acme/app"
ENV = {"GH_TOKEN": "test-token", "GITHUB_REPOSITORY": "acme/app"}


def fake_http(name):
    """HTTP function answering from a fixture file; an unknown path fails the test loudly."""
    responses = json.loads((FIXTURES / name).read_text(encoding="utf-8"))["responses"]

    def http(path):
        if path not in responses:
            raise AssertionError(f"unexpected request {path}")
        return responses[path]
    return http


def offline(_path):
    raise rp.FetchError("network unreachable")


README = """# App

Intro text that must stay.

<!-- harness:begin progress -->
| Lot | State | Done | Issue / PR |
|---|---|---|---|
| LOT-001 Calculation engine | 🔵 in progress | 1/2 | #1 |
<!-- harness:end progress -->

## Getting started

Untouched too.
"""


class RowsTests(unittest.TestCase):
    def setUp(self):
        kind, self.rows = rp.collect("acme/app", fake_http("epics.json"))
        self.assertEqual(kind, "lot")
        self.by_issue = {r["issue"]: r for r in self.rows}

    def test_one_row_per_epic_pull_requests_skipped(self):
        self.assertEqual([r["issue"] for r in self.rows], [1, 2, 3, 4, 5, 6, 7, 8])

    def test_all_sub_issues_closed_is_shipped(self):
        row = self.by_issue[1]
        self.assertEqual((row["state"], row["done"], row["total"]), ("🟢 shipped", 2, 2))
        self.assertEqual(row["pulls"], [(31, f"{R}/pull/31")])

    def test_open_ready_pull_request_is_in_review(self):
        row = self.by_issue[2]
        self.assertEqual((row["state"], row["done"], row["total"]), ("🟠 in review", 1, 2))
        self.assertEqual(row["pulls"], [(32, f"{R}/pull/32")])

    def test_claimed_with_draft_pull_request_is_in_progress(self):
        self.assertEqual(self.by_issue[3]["state"], "🔵 in progress")
        self.assertEqual(self.by_issue[3]["pulls"], [(33, f"{R}/pull/33")])

    def test_blocked_and_needs_decision_are_blocked(self):
        self.assertEqual(self.by_issue[4]["state"], "🔴 blocked")
        self.assertEqual(self.by_issue[5]["state"], "🔴 blocked")

    def test_otherwise_to_do_and_closed_unmerged_pull_request_not_linked(self):
        self.assertEqual(self.by_issue[6]["state"], "⚪ to do")
        self.assertEqual(self.by_issue[6]["pulls"], [])

    def test_epic_without_sub_issue_is_flagged_not_guessed(self):
        row = self.by_issue[7]
        self.assertEqual((row["state"], row["done"], row["total"]), ("⚠ no sub-issue", 0, 0))

    def test_missing_or_several_status_labels_are_flagged_and_ignored(self):
        # #20 carries `status: claimed` and `status: blocked`: neither is used, the row stays ⚪
        self.assertEqual(self.by_issue[8]["state"], "⚪ to do ⚠ #19: no status label; #20: 2 status labels")

    def test_markdown_rows(self):
        table = rp.render(self.rows, "lot")
        lines = table.splitlines()
        self.assertEqual(lines[0], "| Lot | State | Done | Issue / PR |")
        self.assertIn(f"| LOT-001 Calculation engine | 🟢 shipped | 2/2 | [#1]({R}/issues/1) · [#31]({R}/pull/31) |",
                      lines)
        self.assertIn(f"| LOT-003 Export \\| share | 🔵 in progress | 0/1 | [#3]({R}/issues/3) · [#33]({R}/pull/33) |",
                      lines)

    def test_milestones_when_there_is_no_epic(self):
        kind, rows = rp.collect("acme/app", fake_http("milestones.json"))
        self.assertEqual(kind, "milestone")
        got = [(r["title"], r["state"], r["done"], r["total"]) for r in rows]
        self.assertEqual(got, [("v1.0", "🟢 shipped", 3, 3), ("v1.1", "🔵 in progress", 1, 4),
                               ("v2.0", "⚪ to do", 0, 2), ("Someday", "⚠ no issue", 0, 0)])
        table = rp.render(rows, "milestone")
        self.assertTrue(table.startswith("| Milestone | State | Closed | Link |"))
        self.assertIn(f"| v1.1 | 🔵 in progress | 1/4 | [milestone]({R}/milestone/2) |", table)

    def test_pagination_reads_every_page(self):
        calls = []

        def http(path):
            calls.append(path)
            return [{"n": i} for i in range(100)] if path.endswith("page=1") else [{"n": 100}]
        self.assertEqual(len(rp.paged(http, "/x?per_page=100")), 101)
        self.assertEqual(calls, ["/x?per_page=100&page=1", "/x?per_page=100&page=2"])


class OnHoldTests(unittest.TestCase):
    EPIC = {"number": 1, "title": "LOT-1", "state": "open", "html_url": f"{R}/issues/1", "labels": [{"name": "type: epic"}]}

    def row(self, *sub_status):
        subs = [{"number": 10 + n, "title": "s", "state": "open", "html_url": "", "labels": [{"name": s}]}
                for n, s in enumerate(sub_status)]
        return rp.lot_row(self.EPIC | {"labels": [{"name": "status: ready"}]}, subs, [])["state"]

    def test_on_hold_is_its_own_state_not_blocked_not_to_do(self):
        self.assertEqual(self.row("status: on-hold"), "⏸ on hold")

    def test_blocked_and_claimed_win_over_on_hold(self):
        self.assertEqual(self.row("status: on-hold", "status: blocked"), "🔴 blocked")
        self.assertEqual(self.row("status: on-hold", "status: claimed"), "🔵 in progress")


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.readme = pathlib.Path(self.tmp.name) / "README.md"
        self.readme.write_text(README, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, *args, http=None, env=ENV):
        out = io.StringIO()
        code = rp.run(["--readme", str(self.readme), *args], http=http, env=env, out=out)
        return code, out.getvalue()

    def test_write_replaces_only_the_block(self):
        code, _ = self.run_cmd(http=fake_http("epics.json"))
        self.assertEqual(code, 0)
        text = self.readme.read_text(encoding="utf-8")
        before, rest = text.split("<!-- harness:begin progress -->")
        block, after = rest.split("<!-- harness:end progress -->")
        self.assertEqual(before, README.split("<!-- harness:begin progress -->")[0])
        self.assertEqual(after, README.split("<!-- harness:end progress -->")[1])
        self.assertIn("🟢 shipped | 2/2", block)
        self.assertNotIn("🔵 in progress | 1/2", block)

    def test_check_exits_1_on_drift_then_0_once_written(self):
        code, out = self.run_cmd("--check", http=fake_http("epics.json"))
        self.assertEqual(code, 1)
        self.assertIn("🟢 shipped", out)
        self.assertEqual(self.readme.read_text(encoding="utf-8"), README)   # --check never writes
        self.run_cmd(http=fake_http("epics.json"))
        code, out = self.run_cmd("--check", http=fake_http("epics.json"))
        self.assertEqual(code, 0)
        self.assertIn("up to date", out)

    def test_no_token_changes_nothing_and_check_says_could_not_check(self):
        for args in ((), ("--check",)):
            code, out = self.run_cmd(*args, http=fake_http("epics.json"), env={"GITHUB_REPOSITORY": "acme/app"})
            self.assertEqual(code, 2, args)
            self.assertIn("token", out)
            self.assertNotIn("up to date", out)
            self.assertEqual(self.readme.read_text(encoding="utf-8"), README)
        self.assertIn("could not check", out)

    def test_no_network_changes_nothing_and_check_says_could_not_check(self):
        for args in ((), ("--check",)):
            code, out = self.run_cmd(*args, http=offline)
            self.assertEqual(code, 2, args)
            self.assertIn("network unreachable", out)
            self.assertNotIn("up to date", out)
            self.assertEqual(self.readme.read_text(encoding="utf-8"), README)
        self.assertIn("could not check", out)

    def test_refuses_to_write_without_markers(self):
        text = "# App\n\nNo markers here.\n"
        self.readme.write_text(text, encoding="utf-8")
        for args in ((), ("--check",)):
            code, out = self.run_cmd(*args, http=fake_http("epics.json"))
            self.assertEqual(code, 2, args)
            self.assertIn("harness:begin progress", out)
            self.assertEqual(self.readme.read_text(encoding="utf-8"), text)


if __name__ == "__main__":
    unittest.main()

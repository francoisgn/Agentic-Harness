"""Tests of scripts/issue-reconcile.py on recorded API fixtures (offline: the HTTP function is injected)."""
import datetime
import importlib.util
import io
import json
import pathlib
import re
import shutil
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("issue_reconcile", ROOT / "scripts" / "issue-reconcile.py")
ir = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ir)

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures" / "issue-reconcile"
ENV = {"GH_TOKEN": "test-token", "GITHUB_REPOSITORY": "acme/app"}
NOW = datetime.datetime(2026, 11, 11, 12, 0, tzinfo=datetime.timezone.utc)
WORKFLOW = (ROOT / ".github/workflows/issue-hygiene.yml").read_text(encoding="utf-8")


class FakeGitHub:
    """Answers GETs from the fixture file and records writes; an unknown GET fails the test loudly."""

    def __init__(self, name="repo.json", fail_on_write=None):
        self.responses = json.loads((FIXTURES / name).read_text(encoding="utf-8"))["responses"]
        self.gets, self.writes, self.fail_on_write = [], [], fail_on_write

    def __call__(self, path, method="GET", data=None):
        if method == "GET":
            if path not in self.responses:
                raise AssertionError(f"unexpected request {path}")
            self.gets.append(path)
            return self.responses[path]
        if self.fail_on_write is not None and len(self.writes) == self.fail_on_write:
            raise ir.FetchError(f"{method} {path}: HTTP 500")
        self.writes.append((method, path, data))
        return []


def run(argv, http, env=ENV):
    out = io.StringIO()
    code = ir.run(argv, http=http, env=env, out=out, now=NOW)
    return code, out.getvalue()


class RulesTests(unittest.TestCase):
    def setUp(self):
        self.http = FakeGitHub()
        self.code, self.out = run([], self.http)

    def line(self, prefix):
        found = [x for x in self.out.splitlines() if x.startswith(prefix)]
        self.assertEqual(len(found), 1, f"{prefix!r} in:\n{self.out}")
        return found[0]

    def absent(self, prefix):
        self.line("summary: ")                        # the run went through: absence means something
        self.assertFalse([x for x in self.out.splitlines() if x.startswith(prefix)], f"{prefix!r} in:\n{self.out}")

    def test_closed_issue_loses_its_status(self):
        self.assertIn("remove `status: claimed`", self.line("change #1 "))
        self.absent("change #2 ")

    def test_open_pull_request_or_live_claim_means_claimed(self):
        self.assertIn("`status: ready` → `status: claimed`", self.line("change #3 "))
        self.assertIn("#50", self.line("change #3 "))
        self.assertIn("acme.orc-1111.lot.i4", self.line("change #4 "))
        self.assertIn("add `status: claimed`", self.line("change #17 "))

    def test_claim_replay_members_only_release_and_foreign_release(self):
        self.absent("change #5 ")                     # claim by a non-member does not count
        self.absent("change #6 ")                     # claimed then released
        self.assertIn("`status: claimed`", self.line("change #20 "))   # `/release <other id>` releases nothing

    def test_stale_claimed_is_reported_not_changed(self):
        self.assertIn("stale", self.line("check #7 "))
        self.absent("change #7 ")
        self.absent("check #8 ")                      # activity less than 24 h ago

    def test_claim_without_pull_request_after_24h_is_reported(self):
        self.assertIn("no open PR", self.line("check #16 "))
        self.absent("change #16 ")

    def test_blocked_with_every_cited_blocker_closed_is_unblockable(self):
        line = self.line("change #9 ")
        self.assertIn("unblockable", line)
        self.assertIn("`status: blocked` → `status: ready`", line)
        self.assertIn("`status: claimed`", self.line("change #18 "))   # unblockable and an open PR
        self.absent("change #10 ")                    # blocker still open
        self.absent("change #11 ")                    # external blocker: cannot be decided
        self.assertIn("no blocker", self.line("check #21 "))

    def test_decisions_are_never_moved(self):
        self.absent("change #13 ")                    # needs-decision with an open PR
        self.absent("change #14 ")                    # on-hold with a live claim

    def test_several_statuses_and_missing_type_are_reported(self):
        self.assertIn("2 `status:` labels", self.line("check #12 "))
        self.absent("change #12 ")
        self.assertIn("no `type:` label", self.line("check #15 "))
        self.absent("change #15 ")                    # its PR is closed

    def test_umbrella_is_not_claimed_by_a_pull_request_that_refs_it(self):
        self.absent("change #19 ")

    def test_summary_counts_statuses_after_reconcile(self):
        summary = self.line("summary: ")
        for part in ("20 open issues", "needs-triage 1", "ready 5", "claimed 8", "blocked 3", "on-hold 1",
                     "needs-decision 1", "no status 0", "several 1", "changes 7", "to check 5"):
            self.assertIn(part, summary)

    def test_dry_run_writes_nothing_and_says_how_to_apply(self):
        self.assertEqual(self.code, 1)
        self.assertEqual(self.http.writes, [])
        self.assertIn("--apply", self.out)

    def test_cost_is_two_list_calls_not_one_per_issue(self):
        self.assertEqual(len(self.http.gets), 2)
        self.assertIn("API calls: 2", self.out)


class ApplyTests(unittest.TestCase):
    def test_apply_writes_and_lists_every_change(self):
        http = FakeGitHub()
        code, out = run(["--apply"], http)
        self.assertEqual(code, 0)
        self.assertIn(("DELETE", "/repos/acme/app/issues/1/labels/status%3A%20claimed", None), http.writes)
        self.assertIn(("POST", "/repos/acme/app/issues/3/labels", {"labels": ["status: claimed"]}), http.writes)
        self.assertIn(("DELETE", "/repos/acme/app/issues/3/labels/status%3A%20ready", None), http.writes)
        self.assertIn(("POST", "/repos/acme/app/issues/9/labels", {"labels": ["status: ready"]}), http.writes)
        self.assertEqual(len([x for x in out.splitlines() if x.startswith("applied #")]), 7)
        written = {int(re.search(r"/issues/(\d+)/", p).group(1)) for _, p, _ in http.writes}
        self.assertEqual(written, {1, 3, 4, 9, 17, 18, 20})

    def test_new_status_is_added_before_the_old_one_is_removed(self):
        http = FakeGitHub()
        run(["--apply"], http)
        mine = [m for m, p, _ in http.writes if "/issues/3/" in p]
        self.assertEqual(mine, ["POST", "DELETE"])

    def test_write_failure_stops_and_lists_what_was_applied(self):
        http = FakeGitHub(fail_on_write=2)
        code, out = run(["--apply"], http)
        self.assertEqual(code, 2)
        self.assertEqual(len(http.writes), 2)
        self.assertIn("applied #1 ", out)
        self.assertIn("HTTP 500", out)


class ErrorTests(unittest.TestCase):
    def test_no_token_changes_nothing_and_exits_2(self):
        http = FakeGitHub()
        code, out = run(["--apply"], http, env={"GITHUB_REPOSITORY": "acme/app"})
        self.assertEqual(code, 2)
        self.assertEqual((http.gets, http.writes), ([], []))
        self.assertIn("no token", out)
        self.assertIn("nothing changed", out)

    def test_no_network_changes_nothing_and_exits_2(self):
        def offline(path, method="GET", data=None):
            raise ir.FetchError("network unreachable")
        code, out = run(["--apply"], offline)
        self.assertEqual(code, 2)
        self.assertIn("network unreachable", out)
        self.assertIn("nothing changed", out)

    def test_nothing_to_do_exits_0(self):
        items = [{"number": 1, "state": "open", "labels": [{"name": "status: ready"}, {"name": "type: bug"}],
                  "body": "", "updated_at": "2026-11-11T10:00:00Z", "comments": 0}]

        def http(path, method="GET", data=None):
            self.assertEqual(method, "GET")
            return items
        code, out = run([], http)
        self.assertEqual(code, 0)
        self.assertIn("nothing to change", out)


class CommentCostTests(unittest.TestCase):
    def test_per_issue_listing_when_cheaper_than_the_repository_listing(self):
        items = [{"number": n, "state": "closed", "comments": 40} for n in range(1, 11)]
        items += [{"number": 11, "state": "open", "comments": 3, "labels": []}]
        self.assertEqual(ir.comment_paths("a/b", items), ["/repos/a/b/issues/11/comments?per_page=100"])

    def test_repository_listing_when_cheaper_none_without_comments(self):
        items = [{"number": n, "state": "open", "comments": 1, "labels": []} for n in range(1, 6)]
        self.assertEqual(ir.comment_paths("a/b", items),
                         ["/repos/a/b/issues/comments?sort=created&direction=asc&per_page=100"])
        self.assertEqual(ir.comment_paths("a/b", [{"number": 1, "state": "open", "comments": 0, "labels": []}]), [])


SAMPLES = ["### Summary\nx\n\n### Blocked by\n\n#12\n#14\n\n### Other\ny", "### Blocked by\r\n\r\n- camera access\r\n",
           "#### blocked by\n#3", "## Blocked By\n* #4\n- none\n", "", "Summary only", "### Blocked by",
           "### Blocked by\n\n   \n", "### Blocked by\n\nnone", "### Blocked by\n\nN/A", "### Blocked by\n\nTBD",
           "### Blocked by\n\n-", "### Blocked by\n\n_No response_", "### Blocked by\n\n### Next\nx",
           "I am blocked by nothing", "Blocked by: #3", "### Blocked by this\n#3", "# Blocked by\n#3",
           "##### Blocked by\n#3", "###Blocked by  \n#5\n#Title\n", "### Blocked by\n#6\n####### not a heading\n#7"]


class BlockerParserTests(unittest.TestCase):
    def test_python_parser_reads_the_section(self):
        self.assertEqual(ir.blocker_of(SAMPLES[0]), "#12\n#14")
        self.assertEqual(ir.blocker_of(SAMPLES[3]), "#4")
        self.assertIsNone(ir.blocker_of(None))
        for body in SAMPLES[4:18]:
            self.assertIsNone(ir.blocker_of(body), body)

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_same_answer_as_the_workflow_parser(self):
        m = re.search(r"// begin blocker\n(.*?)// end blocker", WORKFLOW, re.S)
        self.assertIsNotNone(m, "issue-hygiene.yml must delimit its parser with `// begin blocker` / `// end blocker`")
        js = m.group(1) + ("\nprocess.stdout.write(JSON.stringify(JSON.parse(process.argv[1]).map(blockerOf)));")
        res = subprocess.run(["node", "-e", js, json.dumps(SAMPLES)], capture_output=True, text=True, check=True)
        self.assertEqual([ir.blocker_of(b) for b in SAMPLES], json.loads(res.stdout))


class ReusableWorkflowTests(unittest.TestCase):
    def test_dry_run_by_default_and_no_event_data_in_run(self):
        wf = (ROOT / ".github/workflows/issue-reconcile.yml").read_text(encoding="utf-8")
        self.assertRegex(wf, r"apply:\n(?:\s+\w.*\n)*?\s+default: false")
        self.assertIn(".harness/scripts/issue-reconcile.py", wf)
        self.assertIn("timeout-minutes:", wf)
        self.assertNotIn("issues:\n    types", wf)              # never on `issues` events
        run_block = wf.split("run: |", 1)[1]
        self.assertNotIn("${{", run_block)
        self.assertIn('[ "$APPLY" = true ] && ARGS+=(--apply)', run_block)


if __name__ == "__main__":
    unittest.main()

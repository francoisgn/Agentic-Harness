"""Tests of scripts/orch-state.py on recorded API shapes (offline: the HTTP function is injected)."""
import copy
import datetime
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("orch_state", ROOT / "scripts" / "orch-state.py")
st = importlib.util.module_from_spec(spec)
spec.loader.exec_module(st)

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "orch-state" / "repo.json"
NOW = datetime.datetime(2026, 11, 11, 12, 0, tzinfo=datetime.timezone.utc)
ENV = {"GH_TOKEN": "test-token", "GITHUB_REPOSITORY": "acme/app"}
MEMORY_COMMENTS = "/repos/acme/app/issues/100/comments?per_page=100&page=1"
DECISIONS = """# Operator decisions

| Date | Scope key | Decision | Source | Status |
|---|---|---|---|---|
| 2026-11-09 | merge.policy | The orchestrator merges a PR the gate accepts. | chat 2026-11-09 | in force |
| 2026-11-02 | children.max | At most four children at a time. | #3 | in force |
| 2026-11-01 | merge.policy | The operator merges. | #2 | replaced by 2026-11-09 |
"""


class FakeGitHub:
    """Answers GETs from the fixture, records writes; an unknown request fails the test loudly."""

    def __init__(self, responses=None):
        self.responses = responses if responses is not None else json.loads(FIXTURE.read_text("utf-8"))["responses"]
        self.writes = []

    def __call__(self, path, method="GET", payload=None):
        if method != "GET":
            self.writes.append((method, path, payload))
            return {"id": 777, "html_url": "https://github.com/acme/app/issues/100#issuecomment-777"}
        if path not in self.responses:
            raise AssertionError(f"unexpected request {path}")
        return copy.deepcopy(self.responses[path])


def offline(path, method="GET", payload=None):
    raise st.FetchError("network unreachable")


class Workspace:
    """A temporary checkout with docs/DECISIONS.md and an optional .harness/config.json."""

    def __init__(self, config=None, decisions=DECISIONS):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        if decisions is not None:
            (self.root / "docs").mkdir()
            (self.root / "docs" / "DECISIONS.md").write_text(decisions, encoding="utf-8")
        if config is not None:
            (self.root / ".harness").mkdir()
            (self.root / ".harness" / "config.json").write_text(json.dumps(config), encoding="utf-8")

    def args(self, *extra):
        return ["--root", str(self.root), *extra]


def run(argv, http, env=ENV):
    out = io.StringIO()
    code = st.run(argv, http=http, env=env, out=out, now=NOW)
    return code, out.getvalue()


def body_of(content):
    """A comment exactly as the script writes it, for a given content."""
    return st.comment_body(content)


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()
        self.http = FakeGitHub()
        code, self.out = run(self.ws.args("--issue", "100", "--print"), self.http)
        self.assertEqual(code, 0, self.out)

    def tearDown(self):
        self.ws.tmp.cleanup()

    def test_print_writes_nothing(self):
        self.assertEqual(self.http.writes, [])

    def test_write_time_and_script_version(self):
        self.assertIn("2026-11-11 12:00 UTC", self.out)
        self.assertIn(f"orch-state.py {st.VERSION}", self.out)

    def test_rules_are_a_pointer_with_scope_keys_in_force_only(self):
        self.assertIn("https://github.com/acme/app/blob/HEAD/docs/DECISIONS.md", self.out)
        self.assertIn("`children.max`", self.out)
        self.assertIn("`merge.policy`", self.out)
        self.assertNotIn("At most four children", self.out)   # a pointer, not a copy
        self.assertEqual(self.out.count("`merge.policy`"), 1)

    def test_open_pull_requests_by_stage_with_their_head(self):
        lines = {n: next(line for line in self.out.splitlines() if line.startswith(f"- #{n} "))
                 for n in (40, 41, 42, 43, 44)}
        self.assertIn("waiting for merge", lines[41])
        self.assertIn("`bbbbbbb`", lines[41])
        self.assertIn("issuecomment-4103", lines[41])   # the report is linked
        self.assertIn("waiting for CI", lines[42])
        self.assertIn("CI red", lines[43])
        self.assertIn("waiting for review", lines[44])  # approved on another sha; a quoted verdict is not one
        self.assertIn("draft", lines[40])
        self.assertIn("`aaaaaaa`", lines[40])

    def test_children_from_claims_and_claim_lines(self):
        children = self.out.split("### Children", 1)[1].split("###", 1)[0]
        self.assertIn("`app.orc-1011.lot.i11.2` holds #11", children)
        self.assertIn("since 2026-11-04", children)
        self.assertIn("`app.orc-1011.lot.i10` holds #10", children)
        self.assertIn("`app.orc-1011.lot.i15`", children)   # known only from the Claim: line of PR #44
        self.assertIn("PR #44", children)
        self.assertNotIn("intruder", children)   # not a repository member
        self.assertNotIn("other.solo", children)   # refused: the claim was held
        self.assertNotIn("`app.orc-1011.lot.i11` ", children)   # released

    def test_decisions_waiting_with_their_age(self):
        section = self.out.split("### Decisions waiting", 1)[1].split("###", 1)[0]
        self.assertIn("#12", section)
        self.assertIn("6 days", section)   # since the label was set, not since the issue was opened

    def test_counts_per_status_label(self):
        section = self.out.split("### Status", 1)[1]
        for text in ("`status: claimed` 2", "`status: needs-decision` 1", "`status: ready` 1", "no status 2"):
            self.assertIn(text, section)

    def test_no_mention(self):
        self.assertNotIn("@dependabot", self.out)
        self.assertIn("dependabot", self.out)


class EmptySectionTests(unittest.TestCase):
    def test_nothing_recorded_is_said_not_left_stale(self):
        ws = Workspace(decisions=None)
        responses = {path: [] for path in ("/repos/acme/app/issues?state=open&per_page=100&page=1",
                                           "/repos/acme/app/pulls?state=open&per_page=100&page=1")}
        code, out = run(ws.args("--issue", "100", "--print"), FakeGitHub(responses))
        ws.tmp.cleanup()
        self.assertEqual(code, 0, out)
        for section in ("### Children", "### Open PRs", "### Decisions waiting"):
            self.assertIn("none recorded", out.split(section, 1)[1].split("###", 1)[0], section)
        self.assertIn("no `docs/DECISIONS.md`", out)


class WriteTests(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace(config={"orchestration": {"memory_issue": 100}})

    def tearDown(self):
        self.ws.tmp.cleanup()

    def test_first_write_creates_one_marked_comment_on_the_configured_issue(self):
        http = FakeGitHub()
        code, out = run(self.ws.args(), http)
        self.assertEqual(code, 0, out)
        self.assertEqual(len(http.writes), 1)
        method, path, payload = http.writes[0]
        self.assertEqual((method, path), ("POST", "/repos/acme/app/issues/100/comments"))
        self.assertTrue(payload["body"].startswith(st.MARKER + "\n"))
        self.assertIn("## State", payload["body"])

    def test_rewrites_its_own_comment_in_place(self):
        http = FakeGitHub()
        old = body_of("## State\n\nold facts\n")
        http.responses[MEMORY_COMMENTS] = http.responses[MEMORY_COMMENTS] + [
            {"id": 555, "body": old.replace("\n", "\r\n"), "author_association": "NONE",
             "user": {"login": "github-actions[bot]"}, "created_at": "2026-11-10T09:00:00Z"}]
        code, out = run(self.ws.args(), http)
        self.assertEqual(code, 0, out)
        self.assertEqual([(m, p) for m, p, _ in http.writes], [("PATCH", "/repos/acme/app/issues/comments/555")])

    def test_hand_edited_state_is_refused_with_the_difference(self):
        http = FakeGitHub()
        edited = body_of("## State\n\nold facts\n").replace("old facts", "old facts, edited by hand")
        http.responses[MEMORY_COMMENTS] = http.responses[MEMORY_COMMENTS] + [
            {"id": 555, "body": edited, "author_association": "OWNER", "user": {"login": "maint"},
             "created_at": "2026-11-10T09:00:00Z"}]
        code, out = run(self.ws.args(), http)
        self.assertEqual(code, 1, out)
        self.assertEqual(http.writes, [])
        self.assertIn("-old facts, edited by hand", out)   # the difference is shown
        self.assertIn("--force", out)
        code, out = run(self.ws.args("--force"), http)
        self.assertEqual(code, 0, out)
        self.assertEqual([(m, p) for m, p, _ in http.writes], [("PATCH", "/repos/acme/app/issues/comments/555")])

    def test_written_body_carries_a_hash_that_detects_edits(self):
        body = body_of("## State\n\nfacts\n")
        self.assertFalse(st.hand_edited(body))
        self.assertTrue(st.hand_edited(body.replace("facts", "fact")))
        self.assertTrue(st.hand_edited(st.MARKER + "\n## State\n"))   # no hash line: not written by the script

    def test_no_token_prints_the_state_and_writes_nothing(self):
        code, out = run(self.ws.args(), offline, env={"GITHUB_REPOSITORY": "acme/app"})
        self.assertEqual(code, 2, out)
        self.assertIn("## State", out)
        self.assertIn("`children.max`", out)   # what is local is still shown
        self.assertIn("no token", out)

    def test_no_network_prints_the_state_and_writes_nothing(self):
        code, out = run(self.ws.args(), offline)
        self.assertEqual(code, 2, out)
        self.assertIn("## State", out)
        self.assertIn("network unreachable", out)

    def test_failure_while_reading_writes_nothing(self):
        http = FakeGitHub()
        del http.responses["/repos/acme/app/issues/44/comments?per_page=100&page=1"]

        def failing(path, method="GET", payload=None):
            if method == "GET" and path not in http.responses:
                raise st.FetchError(f"GET {path}: HTTP 502")
            return http(path, method, payload)
        code, out = run(self.ws.args(), failing)
        self.assertEqual(code, 2, out)
        self.assertEqual(http.writes, [])

    def test_no_memory_issue_prints_and_says_where_to_set_it(self):
        ws = Workspace()
        code, out = run(ws.args(), FakeGitHub())
        ws.tmp.cleanup()
        self.assertEqual(code, 2, out)
        self.assertIn("## State", out)
        self.assertIn("memory_issue", out)


class SizeTests(unittest.TestCase):
    def test_bounded_size_oldest_detail_linked(self):
        ws = Workspace()
        pulls = [{"number": n, "title": f"Change number {n} with a long enough title to fill the line " * 2,
                  "state": "open", "draft": True, "body": f"Claim: app.orc-1011.lot.i{n}",
                  "created_at": "2026-11-01T09:00:00Z", "html_url": f"https://github.com/acme/app/pull/{n}",
                  "head": {"sha": f"{n:040d}"}} for n in range(1, 201)]
        responses = {"/repos/acme/app/issues?state=open&per_page=100&page=1": [],
                     "/repos/acme/app/pulls?state=open&per_page=100&page=1": pulls[:100],
                     "/repos/acme/app/pulls?state=open&per_page=100&page=2": pulls[100:],
                     "/repos/acme/app/pulls?state=open&per_page=100&page=3": []}
        code, out = run(ws.args("--issue", "100", "--print"), FakeGitHub(responses))
        ws.tmp.cleanup()
        self.assertEqual(code, 0, out)
        content = out.split(st.MARKER, 1)[-1]
        self.assertLessEqual(len(content), st.MAX_CHARS)
        self.assertIn("- #200 ", content)   # newest kept
        self.assertNotIn("- #1 ", content)  # oldest linked, not inlined
        self.assertIn("https://github.com/acme/app/pulls?q=is%3Apr+is%3Aopen", content)
        self.assertIn("older", content)


if __name__ == "__main__":
    unittest.main()

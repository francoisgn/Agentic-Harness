"""Tests of scripts/flow-metrics.py (no network: hard-coded data, fixed clock).

Run: python3 -m unittest discover -s scripts/tests -p 'test_*.py'
"""
import importlib.util
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "flow-metrics.py"
spec = importlib.util.spec_from_file_location("flow_metrics", SCRIPT)
fm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fm)

NOW = "2026-11-07T12:00:00Z"


def issue(n, labels=("status: ready",), updated="2026-11-07T10:00:00Z", state="open", milestone=None, assignee=None, title=None):
    return {
        "number": n,
        "title": title or f"Issue {n}",
        "state": state,
        "labels": [{"name": label} for label in labels],
        "updated_at": updated,
        "created_at": "2026-11-01T00:00:00Z",
        "closed_at": updated if state == "closed" else None,
        "milestone": {"title": milestone} if milestone else None,
        "assignees": [{"login": assignee}] if assignee else [],
        "html_url": f"https://github.com/o/r/issues/{n}",
    }


def pull(n, ref="claude/lot-1", draft=False, updated="2026-11-07T10:00:00Z", state="open",
         created="2026-11-05T00:00:00Z", merged=None, reviews=0):
    return {
        "number": n,
        "title": f"PR {n}",
        "state": state,
        "draft": draft,
        "head": {"ref": ref},
        "updated_at": updated,
        "created_at": created,
        "merged_at": merged,
        "html_url": f"https://github.com/o/r/pull/{n}",
        "review_count": reviews,
    }


def run(branch, conclusion="failure", created="2026-11-06T10:00:00Z", minutes=3, sha="s1", event="pull_request",
        workflow=1):
    start = fm.parse_time(created)
    return {
        "head_branch": branch,
        "head_sha": sha,
        "workflow_id": workflow,
        "conclusion": conclusion,
        "event": event,
        "created_at": created,
        "run_started_at": created,
        "updated_at": fm.format_time(start + minutes * 60),
    }


class AnalyseTests(unittest.TestCase):
    def analyse(self, issues=(), pulls=(), runs=(), **kw):
        return fm.analyse({"issues": list(issues), "pulls": list(pulls), "runs": list(runs)}, now=fm.parse_time(NOW), **kw)

    def test_empty_repo_is_green(self):
        r = self.analyse()
        self.assertEqual(r["status"], "🟢")
        self.assertEqual(r["stalled"], [])
        self.assertEqual(r["loops"], [])

    def test_claimed_issue_without_activity_is_stalled(self):
        r = self.analyse(issues=[issue(1, ["status: claimed", "priority: medium"], updated="2026-11-05T00:00:00Z"),
                                 issue(2, ["status: claimed"], updated="2026-11-07T11:00:00Z")])
        self.assertEqual([s["number"] for s in r["stalled"]], [1])
        self.assertEqual(r["status"], "🟠")

    def test_stalled_high_or_critical_priority_is_red(self):
        for priority in ("priority: high", "priority: critical"):
            r = self.analyse(issues=[issue(1, ["status: claimed", priority], updated="2026-11-05T00:00:00Z")])
            self.assertEqual(r["status"], "🔴", priority)
            self.assertTrue(r["stalled"][0]["high_priority"])

    def test_stalled_medium_or_low_priority_is_not_red(self):
        for priority in ("priority: medium", "priority: low"):
            r = self.analyse(issues=[issue(1, ["status: claimed", priority], updated="2026-11-05T00:00:00Z")])
            self.assertEqual(r["status"], "🟠", priority)

    def test_open_issues_are_counted_per_status(self):
        r = self.analyse(issues=[issue(1, ["status: ready"]), issue(2, ["status: ready", "type: bug"]),
                                 issue(3, ["status: needs-triage"]), issue(4, ["status: claimed"], state="closed")])
        self.assertEqual(r["status_counts"], {"status: needs-triage": 1, "status: ready": 2})
        self.assertEqual(r["status_anomalies"], [])
        self.assertEqual(r["status"], "🟢")

    def test_issue_without_status_is_an_amber_signal(self):
        r = self.analyse(issues=[issue(1, ["type: bug"]), issue(2, ["status: ready"]), issue(3, [], state="closed")])
        self.assertEqual([(a["number"], a["statuses"]) for a in r["status_anomalies"]], [(1, [])])
        self.assertEqual(r["status"], "🟠")

    def test_issue_with_several_statuses_is_an_amber_signal(self):
        r = self.analyse(issues=[issue(5, ["status: ready", "status: claimed"])])
        self.assertEqual([(a["number"], a["statuses"]) for a in r["status_anomalies"]],
                         [(5, ["status: ready", "status: claimed"])])
        self.assertEqual(r["status_counts"], {"status: claimed": 1, "status: ready": 1})
        self.assertEqual(r["status"], "🟠")

    def test_ready_pr_without_activity_is_stalled_but_not_draft_within_limit(self):
        r = self.analyse(pulls=[pull(10, updated="2026-11-05T00:00:00Z"),
                                pull(11, draft=True, updated="2026-11-05T00:00:00Z")])
        self.assertEqual([s["number"] for s in r["stalled"]], [10])
        r = self.analyse(pulls=[pull(11, draft=True, updated="2026-11-01T00:00:00Z")])
        self.assertEqual([s["number"] for s in r["stalled"]], [11])

    def test_ci_loop_detected_per_open_pr_branch(self):
        runs = [run("claude/lot-1", sha=f"a{k}") for k in range(7)] + [run("claude/other", sha=f"b{k}") for k in range(7)]
        r = self.analyse(pulls=[pull(10)], runs=runs, max_ci_runs=6)
        self.assertEqual([(lp["number"], lp["kind"]) for lp in r["loops"]], [(10, "ci")])
        self.assertEqual(r["status"], "🔴")

    def test_ci_loop_counts_pushes_not_workflows(self):
        # 4 workflows per push, 2 pushes: 2 runs, not a loop (review finding no. 1)
        runs = [run("claude/lot-1", sha=f"a{k}", workflow=w) for k in range(2) for w in range(4)]
        self.assertEqual(self.analyse(pulls=[pull(10)], runs=runs, max_ci_runs=6)["loops"], [])

    def test_ci_loop_ignores_skipped_and_cancelled_runs(self):
        # Pushing often on a draft (skipped runs) or cancelling a run is not a loop (CI-BUDGET §2)
        runs = [run("claude/lot-1", sha=f"a{k}", conclusion="skipped") for k in range(8)]
        runs += [run("claude/lot-1", sha=f"c{k}", conclusion="cancelled") for k in range(8)]
        self.assertEqual(self.analyse(pulls=[pull(10)], runs=runs, max_ci_runs=6)["loops"], [])

    def test_ci_loop_ignores_push_and_schedule_runs_of_promotion_branch(self):
        runs = [run("develop", sha=f"d{k}", event=e) for k in range(8) for e in ("push", "schedule")]
        self.assertEqual(self.analyse(pulls=[pull(20, ref="develop")], runs=runs, max_ci_runs=6)["loops"], [])

    def test_failure_rate_ignores_cancelled_and_skipped(self):
        runs = [run("x", conclusion="failure"), run("x", conclusion="cancelled"), run("x", conclusion="cancelled"),
                run("x", conclusion="skipped"), run("x", conclusion="success")]
        self.assertEqual(self.analyse(runs=runs)["ci"]["failure_rate"], 50)

    def test_milestones_from_api_take_precedence(self):
        data_ms = [{"title": "Milestone 1", "open_issues": 1, "closed_issues": 9, "due_on": "2026-12-01T00:00:00Z"}]
        r = fm.analyse({"issues": [issue(1, milestone="Milestone 1")], "pulls": [], "runs": [], "milestones": data_ms},
                       now=fm.parse_time(NOW))
        self.assertEqual(r["milestones"], [{"title": "Milestone 1", "closed": 9, "total": 10, "percent": 90,
                                            "due_on": "2026-12-01"}])

    def test_review_round_loop(self):
        r = self.analyse(pulls=[pull(10, reviews=5)], max_review_rounds=3)
        self.assertEqual([(lp["number"], lp["kind"]) for lp in r["loops"]], [(10, "review")])

    def test_bottlenecks_count_blocked_and_needs_decision(self):
        r = self.analyse(issues=[issue(1, ["status: blocked"]), issue(2, ["status: needs-decision"]),
                                 issue(3, ["status: blocked"], state="closed")])
        self.assertEqual(r["bottlenecks"], {"status: blocked": [1], "status: needs-decision": [2]})
        self.assertEqual(r["status"], "🟠")

    def test_on_hold_is_listed_apart_and_is_not_a_bottleneck(self):
        r = self.analyse(issues=[issue(1, ["status: on-hold"]), issue(2, ["status: ready"]),
                                 issue(3, ["status: on-hold"], state="closed")])
        self.assertEqual(r["on_hold"], [{"number": 1, "title": "Issue 1"}])
        self.assertEqual(r["bottlenecks"], {})
        self.assertEqual(r["status_counts"], {"status: on-hold": 1, "status: ready": 1})
        self.assertEqual(r["status"], "🟢")

    def test_milestone_progress(self):
        r = self.analyse(issues=[issue(1, milestone="Milestone 1", state="closed"), issue(2, milestone="Milestone 1"),
                                 issue(3, milestone="Milestone 1", state="closed"), issue(4)])
        self.assertEqual(r["milestones"], [{"title": "Milestone 1", "closed": 2, "total": 3, "percent": 67}])

    def test_agent_ratio_and_lead_time(self):
        pulls = [pull(1, ref="claude/a", state="closed", created="2026-11-05T00:00:00Z", merged="2026-11-05T10:00:00Z"),
                 pull(2, ref="claude/b", state="closed", created="2026-11-05T00:00:00Z", merged="2026-11-06T06:00:00Z"),
                 pull(3, ref="feature/x", state="closed", created="2026-11-05T00:00:00Z", merged="2026-11-05T02:00:00Z"),
                 pull(4, ref="claude/old", state="closed", created="2026-09-01T00:00:00Z", merged="2026-09-02T00:00:00Z")]
        r = self.analyse(pulls=pulls, window_days=14)
        self.assertEqual(r["merged"], {"total": 3, "agent": 2, "human": 1, "median_lead_hours": 10.0})

    def test_ci_minutes_rounded_up_per_run(self):
        runs = [run("x", conclusion="success", minutes=0.1), run("x", conclusion="success", minutes=2.5)]
        r = self.analyse(runs=runs)
        self.assertEqual(r["ci"]["runs"], 2)
        self.assertEqual(r["ci"]["billed_minutes_min"], 4)
        self.assertEqual(r["ci"]["failure_rate"], 0)


class CollectTests(unittest.TestCase):
    def test_open_issues_are_fetched_without_since(self):
        calls = []

        def fake(path):
            calls.append(path)
            return []
        original = fm._gh
        fm._gh = fake
        try:
            fm.collect("o/r", 14)
        finally:
            fm._gh = original
        open_calls = [c for c in calls if c.startswith("repos/o/r/issues") and "state=open" in c]
        self.assertTrue(open_calls and all("since=" not in c for c in open_calls), calls)
        self.assertTrue(any(c.startswith("repos/o/r/milestones") for c in calls), calls)
        closed = [c for c in calls if c.startswith("repos/o/r/issues") and "state=closed" in c]
        self.assertTrue(closed and all("since=" in c for c in closed), calls)

    def test_merged_prs_get_reviews_comments_and_commits(self):
        calls = []

        def fake(path):
            calls.append(path)
            if path.startswith("repos/o/r/pulls?"):
                return [{"number": 7, "state": "closed", "merged_at": "2026-11-06T00:00:00Z",
                         "updated_at": "2026-11-06T00:00:00Z"}]
            return []
        original = fm._gh
        fm._gh = fake
        try:
            with mock.patch.object(fm.time, "time", return_value=fm.parse_time(NOW)):
                data = fm.collect("o/r", 14)
        finally:
            fm._gh = original
        self.assertTrue(any("pulls/7/reviews" in c for c in calls))
        self.assertTrue(any("issues/7/comments" in c for c in calls))
        self.assertTrue(any("pulls/7/commits" in c for c in calls))
        self.assertEqual(data["pulls"][0]["reviews"], [])  # otherwise pagination of the whole history
        self.assertEqual(data["runs_query"], [c for c in calls if "/actions/runs?" in c][0])  # CI health counts it


def review(login, state, body="", at="2026-11-05T02:00:00Z"):
    return {"user": {"login": login}, "state": state, "body": body, "submitted_at": at}


def comment(login, body, at="2026-11-05T02:00:00Z"):
    return {"user": {"login": login}, "body": body, "created_at": at}


def commit(at):
    return {"commit": {"committer": {"date": at}}}


ADV_KO = "**Adversarial review (fable): CHANGES REQUESTED** head abc"
ADV_OK = "**Adversarial review (fable): APPROVED** head def"


class ReviewEventTests(unittest.TestCase):
    def test_sources_and_verdicts(self):
        p = pull(1, state="closed", merged="2026-11-06T00:00:00Z")
        p["reviews"] = [review("coderabbitai[bot]", "COMMENTED", "**Actionable comments posted: 3**"),
                        review("coderabbitai[bot]", "COMMENTED", "**Actionable comments posted: 0**"),
                        review("francoisgn", "CHANGES_REQUESTED", "no"),
                        review("francoisgn", "APPROVED", "")]
        p["comments"] = [comment("claude", ADV_KO), comment("claude", ADV_OK),
                         comment("github-actions[bot]", "**Compliance review GDPR (opus): GAPS** head x"),
                         comment("github-actions[bot]", "**AI review (sonnet): APPROVED** head y"),
                         comment("github-actions[bot]", "**Compliance review PCI (opus): OUT OF SCOPE** head z"),
                         comment("x", "thanks")]
        got = [(e["source"], e["problem"]) for e in fm.review_events(p)]
        self.assertEqual(got, [("coderabbit", True), ("coderabbit", False), ("human", True), ("human", False),
                               ("adversarial", True), ("adversarial", False), ("compliance", True), ("ai", False)])


class VerdictParsingTests(unittest.TestCase):
    def test_quoted_or_table_verdicts_are_ignored_and_all_verdicts_of_a_body_count(self):
        p = pull(1)
        p["comments"] = [comment("c", "> " + ADV_KO + "\nanswer"),
                         comment("c", "| **Compliance review GDPR (opus): GAPS** | x |"),
                         comment("c", "**Compliance review GDPR (opus): COMPLIANT** head a\n"
                                      "**Compliance review PCI (opus): GAPS** head a")]
        self.assertEqual([(e["source"], e["problem"]) for e in fm.review_events(p)],
                         [("compliance", False), ("compliance", True)])


class BulletVerdictTests(unittest.TestCase):
    def test_verdict_as_list_item_counts(self):
        p = pull(1)
        p["comments"] = [comment("c", "- " + ADV_KO), comment("c", "* " + ADV_OK)]
        self.assertEqual([e["problem"] for e in fm.review_events(p)], [True, False])


class UnverifiedTests(unittest.TestCase):
    """REVIEW-ROUNDS §Traceability: a verdict line may end with "· unverified: N"; the dashboard counts the merged PRs
    whose last harness verdict before the merge still carries unverified points."""

    def test_unverified_count_is_read_from_the_verdict_line(self):
        p = pull(1)
        p["comments"] = [comment("c", ADV_OK + " · unverified: 2"), comment("c", ADV_KO),
                         comment("c", "**AI review (sonnet): APPROVED** head y · Unverified: 1")]
        self.assertEqual([e.get("unverified") for e in fm.review_events(p)], [2, 0, 1])

    def test_only_the_suffix_of_the_verdict_line_counts(self):
        p = pull(1)
        p["comments"] = [comment("c", ADV_OK + ", previously unverified: 2, now checked")]
        self.assertEqual([e.get("unverified") for e in fm.review_events(p)], [0])

    def test_merged_prs_whose_last_verdict_keeps_unverified_points_are_counted(self):
        def merged(n, *bodies):
            p = pull(n, state="closed", created="2026-11-05T00:00:00Z", merged="2026-11-06T00:00:00Z")
            p["comments"] = [comment("c", b, f"2026-11-05T0{i}:00:00Z") for i, b in enumerate(bodies, 1)]
            return p
        pulls = [merged(1, ADV_OK + " · unverified: 1"),                       # still unverified at merge
                 merged(2, ADV_OK + " · unverified: 1", ADV_OK),               # resolved by a later verdict
                 merged(3, ADV_OK)]
        q = fm.quality(pulls)
        self.assertEqual(q["unverified"], 1)
        report = fm.analyse({"issues": [], "pulls": pulls, "runs": []}, now=fm.parse_time(NOW))
        self.assertIn("approved with unverified points", fm.render_markdown(report, "o/r"))


class UnverifiedOrderTests(unittest.TestCase):
    def test_last_verdict_per_source_in_time_order_decides(self):
        def merged(n):
            return pull(n, state="closed", created="2026-11-05T00:00:00Z", merged="2026-11-06T00:00:00Z")
        # Another source's later verdict does not clear the adversarial review's unverified points
        p1 = merged(1)
        p1["comments"] = [comment("c", ADV_OK + " · unverified: 2", "2026-11-05T01:00:00Z"),
                          comment("c", "**AI review (sonnet): APPROVED** head y", "2026-11-05T02:00:00Z")]
        # A verdict posted as a GitHub review after a comment verdict is the later one, whatever the list order
        p2 = merged(2)
        p2["comments"] = [comment("c", ADV_OK + " · unverified: 1", "2026-11-05T01:00:00Z")]
        p2["reviews"] = [review("claude", "COMMENTED", ADV_OK, "2026-11-05T03:00:00Z")]
        self.assertEqual(fm.quality([p1])["unverified"], 1)
        self.assertEqual(fm.quality([p2])["unverified"], 0)


class SkippedRunTests(unittest.TestCase):
    def test_skipped_runs_cost_no_minutes(self):
        runs = [run("x", conclusion="skipped", minutes=0), run("x", conclusion="success", minutes=2.5)]
        ci = fm.analyse({"issues": [], "pulls": [], "runs": runs}, now=fm.parse_time(NOW))["ci"]
        self.assertEqual((ci["runs"], ci["billed_minutes_min"]), (2, 3))

    def test_numbered_verdict_counts(self):
        p = pull(1)
        p["comments"] = [comment("c", "1. " + ADV_KO)]
        self.assertEqual([e["problem"] for e in fm.review_events(p)], [True])


class QualityTests(unittest.TestCase):
    def merged(self, n, ref, events_comments=(), reviews=(), commits=()):
        p = pull(n, ref=ref, state="closed", created="2026-11-05T00:00:00Z", merged="2026-11-06T00:00:00Z")
        p["comments"], p["reviews"], p["commits"] = list(events_comments), list(reviews), list(commits)
        return p

    def test_problem_ratio_first_pass_and_fix_effort(self):
        pulls = [
            self.merged(1, "claude/a", [comment("c", ADV_KO, "2026-11-05T02:00:00Z"), comment("c", ADV_OK, "2026-11-05T08:00:00Z")],
                        commits=[commit("2026-11-05T01:00:00Z"), commit("2026-11-05T04:00:00Z"), commit("2026-11-05T06:00:00Z")]),
            self.merged(2, "claude/b", [comment("c", ADV_OK)],
                        reviews=[review("coderabbitai[bot]", "COMMENTED", "Actionable comments posted: 2", "2026-11-05T03:00:00Z")],
                        commits=[commit("2026-11-05T01:00:00Z"), commit("2026-11-05T05:00:00Z")]),
            self.merged(3, "claude/c", [comment("c", ADV_OK)]),
            self.merged(4, "feature/x", reviews=[review("francoisgn", "APPROVED")]),
        ]
        q = fm.analyse({"issues": [], "pulls": pulls, "runs": []}, now=fm.parse_time(NOW))["quality"]
        self.assertEqual(q["reviewed"], 4)
        self.assertEqual(q["problem"], 2)
        self.assertEqual(q["problem_ratio"], 50)
        self.assertEqual(q["by_source"], {"adversarial": 1, "coderabbit": 1})
        self.assertEqual(q["agent"], {"reviewed": 3, "problem": 2})
        self.assertEqual(q["human"], {"reviewed": 1, "problem": 0})
        self.assertEqual(q["fix_commits_mean"], 1.5)       # PR 1: 2 commits after 02:00; PR 2: 1 after 03:00
        self.assertEqual(q["fix_hours_median"], 21.5)      # first finding → merge: 22 h and 21 h

    def test_agent_detected_by_claim_line_or_footer(self):
        def merged_with(n, body):
            p = self.merged(n, "fix/x", [comment("c", ADV_OK)])
            p["body"] = body
            return p
        pulls = [merged_with(1, "Closes #3\nClaim: proj.solo.lot.i3\n"),
                 merged_with(2, "Closes #4\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)"),
                 merged_with(3, "Closes #5\nClaim: human/someone\n"), merged_with(4, None)]
        q = fm.analyse({"issues": [], "pulls": pulls, "runs": []}, now=fm.parse_time(NOW))["quality"]
        self.assertEqual((q["agent"]["reviewed"], q["human"]["reviewed"]), (2, 2))

    def test_verdict_posted_after_merge_is_ignored(self):
        late = self.merged(1, "claude/a", [comment("c", ADV_KO, "2026-11-07T00:00:00Z")])
        q = fm.analyse({"issues": [], "pulls": [late], "runs": []}, now=fm.parse_time(NOW))["quality"]
        self.assertEqual((q["problem"], q["untraced"], q["fix_hours_median"]), (0, 1, None))

    def test_pr_without_any_traced_review_is_counted_apart(self):
        q = fm.analyse({"issues": [], "pulls": [self.merged(1, "claude/a")], "runs": []}, now=fm.parse_time(NOW))["quality"]
        self.assertEqual((q["reviewed"], q["untraced"]), (0, 1))

    def test_high_problem_ratio_is_amber(self):
        pulls = [self.merged(n, "claude/a", [comment("c", ADV_KO)]) for n in range(3)]
        r = fm.analyse({"issues": [], "pulls": pulls, "runs": []}, now=fm.parse_time(NOW), max_problem_ratio=50)
        self.assertEqual(r["status"], "🟠")

    def test_markdown_has_quality_section(self):
        pulls = [self.merged(1, "claude/a", [comment("c", ADV_KO)])]
        md = fm.render_markdown(fm.analyse({"issues": [], "pulls": pulls, "runs": []}, now=fm.parse_time(NOW)), "o/r")
        self.assertIn("## First-pass quality", md)
        self.assertIn("100%", md)


class RenderTests(unittest.TestCase):
    def test_markdown_has_headline_and_sections(self):
        r = fm.analyse({"issues": [issue(1, ["status: blocked", "priority: high"], title="Payment | breaks")],
                        "pulls": [], "runs": []}, now=fm.parse_time(NOW))
        md = fm.render_markdown(r, repo="o/r")
        self.assertTrue(md.startswith("# Project dashboard: o/r"))
        self.assertIn("🟠", md)
        self.assertIn("## Bottlenecks", md)
        self.assertIn("Payment \\| breaks", md)  # LESSONS L07: pipe escaped in a table

    def test_markdown_lists_status_counts_and_anomalies(self):
        r = fm.analyse({"issues": [issue(1, ["status: ready"]), issue(2, ["status: ready"]),
                                   issue(3, [], title="No status"), issue(4, ["status: ready", "status: blocked"])],
                        "pulls": [], "runs": []}, now=fm.parse_time(NOW))
        md = fm.render_markdown(r, repo="o/r")
        self.assertIn("## Open issues by status", md)
        self.assertIn("| `status: ready` | 3 |", md)
        self.assertIn("2 open issue(s) without exactly one `status:` label", md)
        self.assertIn("| #3 | No status | none |", md)
        self.assertIn("| #4 | Issue 4 | status: ready, status: blocked |", md)

    def test_markdown_shows_on_hold_apart_from_bottlenecks(self):
        r = fm.analyse({"issues": [issue(1, ["status: on-hold"], title="Wait | milestone")], "pulls": [], "runs": []},
                       now=fm.parse_time(NOW))
        md = fm.render_markdown(r, repo="o/r")
        self.assertIn("## On hold", md)
        self.assertIn("| #1 | Wait \\| milestone |", md)
        self.assertIn("- No `status: blocked` or `status: needs-decision` item.", md)

    def test_markdown_without_any_status_label(self):
        md = fm.render_markdown(fm.analyse({"issues": [], "pulls": [], "runs": []}, now=fm.parse_time(NOW)), "o/r")
        self.assertIn("- No open issue carries a `status:` label.", md)
        self.assertNotIn("without exactly one", md)

    def test_cli_reads_input_file(self):
        data = {"issues": [issue(1)], "pulls": [], "runs": []}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(data, f)
        out = subprocess.run([sys.executable, str(SCRIPT), "--input", f.name, "--now", NOW, "--format", "json"],
                             capture_output=True, text=True, check=True).stdout
        self.assertEqual(json.loads(out)["status"], "🟢")

    def test_cli_json_out_alongside_markdown(self):
        with tempfile.TemporaryDirectory() as d:
            src, dst = pathlib.Path(d, "in.json"), pathlib.Path(d, "out.json")
            src.write_text(json.dumps({"issues": [issue(1, ["status: blocked"])], "pulls": [], "runs": []}))
            md = subprocess.run([sys.executable, str(SCRIPT), "--input", str(src), "--now", NOW, "--json-out", str(dst)],
                                capture_output=True, text=True, check=True).stdout
            self.assertIn("# Project dashboard", md)
            self.assertEqual(json.loads(dst.read_text())["status"], "🟠")



# --- CI health (#101): passed only on re-run, integration branch red rate, long or stuck ---------------------------

def crun(rid, sha="s1", workflow=1, name="CI", branch="feat/x", event="pull_request", status="completed",
         conclusion="success", attempt=1, created="2026-11-06T10:00:00Z"):
    """A workflow run as GET /repos/{o}/{r}/actions/runs returns it (the fields the CI health signals read)."""
    return {"id": rid, "name": name, "workflow_id": workflow, "head_sha": sha, "head_branch": branch, "event": event,
            "status": status, "conclusion": conclusion, "run_attempt": attempt, "created_at": created,
            "run_started_at": created, "updated_at": created, "html_url": f"https://github.com/o/r/actions/runs/{rid}"}


def cjob(name, conclusion="success", attempt=1, status="completed", started="2026-11-06T10:01:00Z"):
    """A job as GET /repos/{o}/{r}/actions/runs/{id}/jobs?filter=all returns it."""
    return {"name": name, "status": status, "conclusion": conclusion if status == "completed" else None,
            "run_attempt": attempt, "started_at": started,
            "completed_at": started if status == "completed" else None, "html_url": "https://github.com/o/r/job/1"}


WORKFLOWS = {"total_count": 1, "workflows": [{"id": 1, "name": "CI", "state": "active"}]}
CFG = dict(getattr(fm, "CI_DEFAULTS", {}))


def ci_data(runs, jobs, workflows=WORKFLOWS, branch="develop", **extra):
    """The `ci_health` part of the collected data, as collect_ci_health builds it."""
    d = {"integration_branch": branch, "workflows": workflows["workflows"], "jobs": {str(k): v for k, v in jobs.items()},
         "unfetched": {}, "error": None, "runs_cut": None, "requests": 0, "thresholds": dict(CFG)}
    d.update(extra)
    return d


class CiHealthTests(unittest.TestCase):
    def analyse(self, runs, jobs, **extra):
        return fm.analyse({"issues": [], "pulls": [], "runs": runs, "ci_health": ci_data(runs, jobs, **extra)},
                          now=fm.parse_time(NOW))

    def test_red_then_green_on_a_rerun_of_the_same_run_is_flagged(self):
        r = self.analyse([crun(1, attempt=2)], {1: [cjob("tests", "failure", 1), cjob("tests", "success", 2),
                                                    cjob("lint", "success", 1), cjob("lint", "success", 2)]})
        flaky = r["ci_health"]["flaky"]
        self.assertEqual([(i["workflow"], i["job"], i["commits"]) for i in flaky["items"]], [("CI", "tests", 1)])
        self.assertEqual(r["status"], "🟠")
        md = fm.render_markdown(r, "o/r")
        self.assertIn("## CI health", md)
        self.assertIn("| CI / tests | 1 |", md)
        self.assertIn("`type: bug`", md)

    def test_red_then_green_in_another_run_of_the_same_commit_is_flagged(self):
        runs = [crun(1, conclusion="failure", created="2026-11-06T10:00:00Z"),
                crun(2, created="2026-11-06T11:00:00Z")]
        r = self.analyse(runs, {1: [cjob("tests", "failure")], 2: [cjob("tests", "success")]})
        self.assertEqual([i["job"] for i in r["ci_health"]["flaky"]["items"]], ["tests"])

    def test_red_twice_is_not_a_flake(self):
        r = self.analyse([crun(1, conclusion="failure", attempt=2)],
                         {1: [cjob("tests", "failure", 1), cjob("tests", "failure", 2)]})
        self.assertEqual(r["ci_health"]["flaky"]["items"], [])
        self.assertEqual(r["status"], "🟢")

    def test_green_then_red_is_not_passed_on_rerun(self):
        r = self.analyse([crun(1, conclusion="failure", attempt=2)],
                         {1: [cjob("tests", "success", 1), cjob("tests", "failure", 2)]})
        self.assertEqual(r["ci_health"]["flaky"]["items"], [])

    def test_cancelled_then_green_is_not_a_flake(self):
        r = self.analyse([crun(1, attempt=2)], {1: [cjob("tests", "cancelled", 1), cjob("tests", "success", 2)]})
        self.assertEqual(r["ci_health"]["flaky"]["items"], [])
        self.assertEqual(r["status"], "🟢")

    def test_queued_run_with_zero_jobs_older_than_threshold_is_flagged(self):
        old = crun(5, status="queued", conclusion=None, created="2026-11-07T11:00:00Z")      # 60 min > 30
        young = crun(6, status="queued", conclusion=None, created="2026-11-07T11:50:00Z")    # 10 min
        r = self.analyse([old, young], {5: []})
        items = r["ci_health"]["stuck"]["queued"]
        self.assertEqual([(i["run_id"], i["minutes"]) for i in items], [(5, 60)])
        self.assertEqual(r["ci_health"]["stuck"]["unchecked"], 0)   # the young one is no candidate
        self.assertEqual(r["status"], "🟠")
        self.assertIn("queued with no job", fm.render_markdown(r, "o/r"))

    def test_queued_run_that_has_jobs_is_not_flagged(self):
        r = self.analyse([crun(5, status="queued", conclusion=None, created="2026-11-07T11:00:00Z")],
                         {5: [cjob("tests", status="queued")]})
        self.assertEqual(r["ci_health"]["stuck"]["queued"], [])

    def test_in_progress_job_over_threshold_is_flagged_and_red_on_the_integration_branch(self):
        started = "2026-11-07T10:00:00Z"   # 120 min before NOW
        feature = crun(7, status="in_progress", conclusion=None, created=started)
        r = self.analyse([feature], {7: [cjob("tests", status="in_progress", started=started)]})
        self.assertEqual([(i["job"], i["minutes"], i["integration"]) for i in r["ci_health"]["stuck"]["long"]],
                         [("tests", 120, False)])
        self.assertEqual(r["status"], "🟠")
        base = crun(8, status="in_progress", conclusion=None, created=started, branch="develop", event="push")
        r = self.analyse([base], {8: [cjob("tests", status="in_progress", started=started)]})
        self.assertTrue(r["ci_health"]["stuck"]["long"][0]["integration"])
        self.assertEqual(r["status"], "🔴")

    def test_in_progress_job_under_threshold_is_not_flagged(self):
        started = "2026-11-07T11:30:00Z"   # 30 min
        r = self.analyse([crun(7, status="in_progress", conclusion=None, created="2026-11-07T10:00:00Z")],
                         {7: [cjob("tests", status="in_progress", started=started)]})
        self.assertEqual(r["ci_health"]["stuck"]["long"], [])
        self.assertEqual(r["status"], "🟢")

    def test_integration_branch_red_rate_above_threshold(self):
        runs = [crun(10 + k, sha=f"b{k}", branch="develop", event="push",
                     conclusion="failure" if k < 2 else "success", created=f"2026-11-06T1{k}:00:00Z")
                for k in range(5)]
        jobs = {10 + k: [cjob("tests", "failure" if k < 2 else "success"), cjob("lint")] for k in range(5)}
        jobs[14].append(cjob("ui", "cancelled"))
        r = self.analyse(runs, jobs)
        red = r["ci_health"]["red"]
        self.assertEqual([(i["job"], i["failures"], i["total"], i["percent"]) for i in red["items"]],
                         [("tests", 2, 5, 40)])
        self.assertEqual((red["checked"], red["candidates"]), (5, 5))
        self.assertEqual(r["status"], "🟠")
        self.assertIn("| CI / tests | 40% (2/5) |", fm.render_markdown(r, "o/r"))

    def test_red_rate_ignores_pull_request_runs_and_low_rates(self):
        runs = [crun(10 + k, sha=f"b{k}", branch="develop", event="push", created=f"2026-11-06T1{k}:00:00Z")
                for k in range(6)] + [crun(30, sha="p", conclusion="failure")]
        jobs = {10 + k: [cjob("tests", "failure" if k == 0 else "success")] for k in range(6)}
        jobs[30] = [cjob("tests", "failure")]
        self.assertEqual(self.analyse(runs, jobs)["ci_health"]["red"]["items"], [])   # 1/6 = 17 % ≤ 20 %

    def test_runs_of_deleted_workflows_or_without_sha_are_not_classified(self):
        wf = {"total_count": 2, "workflows": [{"id": 1, "name": "CI", "state": "active"},
                                              {"id": 2, "name": "Old", "state": "deleted"}]}
        runs = [crun(1, workflow=2, attempt=2), crun(2, sha=None, attempt=2), crun(3, workflow=9, attempt=2)]
        r = self.analyse(runs, {k: [cjob("t", "failure", 1), cjob("t", "success", 2)] for k in (1, 2, 3)},
                         workflows=wf)
        self.assertEqual(r["ci_health"]["flaky"]["items"], [])
        self.assertEqual(r["ci_health"]["not_classified"], 3)
        self.assertIn("3 run(s) not classified", fm.render_markdown(r, "o/r"))

    def test_api_error_says_could_not_check_never_none(self):
        runs = [crun(1, attempt=2), crun(5, status="queued", conclusion=None, created="2026-11-07T11:00:00Z")]
        r = self.analyse(runs, {}, error="gh api: HTTP 502")
        h = r["ci_health"]
        for signal in (h["flaky"], h["red"], h["stuck"]):
            self.assertIn("HTTP 502", signal["error"])
        md = fm.render_markdown(r, "o/r")
        section = md.split("## CI health", 1)[1]
        self.assertGreaterEqual(section.count("could not check"), 3)
        self.assertNotIn("- None.", section)
        self.assertEqual(r["status"], "🟢")   # unchecked is said, it does not raise the status

    def test_input_without_job_data_says_could_not_check(self):
        r = fm.analyse({"issues": [], "pulls": [], "runs": [crun(1)]}, now=fm.parse_time(NOW))
        self.assertIn("could not check", fm.render_markdown(r, "o/r").split("## CI health", 1)[1])
        self.assertEqual(r["status"], "🟢")

    def test_runs_list_cut_short_says_could_not_check(self):
        r = self.analyse([crun(1)], {}, runs_cut="1000 of 1500 runs listed")
        self.assertIn("1000 of 1500", r["ci_health"]["flaky"]["error"])

    def test_timed_out_then_green_is_flagged(self):
        r = self.analyse([crun(1, attempt=2)], {1: [cjob("tests", "timed_out", 1), cjob("tests", "success", 2)]})
        self.assertEqual([i["job"] for i in r["ci_health"]["flaky"]["items"]], ["tests"])

    def test_pending_run_waits_for_its_concurrency_group_and_is_not_stuck(self):
        pending = crun(5, status="pending", conclusion=None, created="2026-11-07T08:00:00Z")
        r = self.analyse([pending], {5: []})
        self.assertEqual(r["ci_health"]["stuck"]["queued"], [])
        self.assertEqual(r["status"], "🟢")

    def test_candidates_beyond_the_budget_are_counted_unchecked(self):
        runs = [crun(k, sha=f"s{k}", attempt=2) for k in range(1, 4)]
        r = self.analyse(runs, {1: [cjob("t")]}, unfetched={"2": "budget", "3": "budget"})
        self.assertEqual(r["ci_health"]["flaky"]["unchecked"], 2)
        self.assertIn("could not check 2 run(s)", fm.render_markdown(r, "o/r"))


class CiHealthCollectTests(unittest.TestCase):
    """collect_ci_health: bounded GET requests through the injected `get`, never a write."""

    def fake(self, pages, calls):
        def get(path):
            calls.append(path)
            for prefix, page in pages.items():
                if path.startswith(prefix):
                    if isinstance(page, Exception):
                        raise page
                    return page
            return {"total_count": 0, "jobs": []}
        return get

    def collect(self, runs, pages, cfg=None, branch="develop"):
        calls = []
        pages = {"repos/o/r/actions/workflows": WORKFLOWS,
                 "repos/o/r/actions/runs?": {"total_count": len(runs), "workflow_runs": []}, **pages}
        out = fm.collect_ci_health("o/r", runs, fm.parse_time(NOW), dict(cfg or CFG), branch, 14,
                                   runs_query="repos/o/r/actions/runs?per_page=100&created=>=2026-10-08",
                                   get=self.fake(pages, calls))
        return out, calls

    def test_requests_are_bounded_by_the_budget_and_read_only(self):
        runs = [crun(k, sha=f"s{k}", attempt=2) for k in range(1, 11)]
        out, calls = self.collect(runs, {}, cfg={**CFG, "max_job_requests": 3})
        job_calls = [c for c in calls if "/jobs" in c]
        self.assertEqual(len(job_calls), 3)
        self.assertEqual(out["requests"], 2 + 3)          # workflows + runs total + 3 job lists
        self.assertEqual(sorted(out["unfetched"].values()), ["budget"] * 7)
        self.assertTrue(all("filter=all" in c and "per_page=100" in c for c in job_calls), job_calls)
        self.assertFalse([c for c in calls if any(w in c for w in ("cancel", "rerun", "delete"))])

    def test_runs_that_need_no_job_list_cost_nothing(self):
        runs = [crun(1), crun(2, status="queued", conclusion=None, created="2026-11-07T11:55:00Z")]
        out, calls = self.collect(runs, {})
        self.assertEqual([c for c in calls if "/jobs" in c], [])
        self.assertEqual(out["requests"], 2)

    def test_api_error_is_recorded_not_raised(self):
        err = subprocess.CalledProcessError(1, ["gh"], stderr="gh: Server Error (HTTP 502)\n")
        out, _ = self.collect([crun(1, attempt=2)], {"repos/o/r/actions/runs/1/jobs": err})
        self.assertIn("HTTP 502", out["error"])
        self.assertEqual(out["jobs"], {})

    def test_missing_gh_or_token_is_recorded_not_raised(self):
        out, _ = self.collect([crun(1)], {"repos/o/r/actions/workflows": FileNotFoundError("gh")})
        self.assertIn("gh", out["error"])

    def test_job_list_cut_short_is_unchecked(self):
        page = {"total_count": 150, "jobs": [cjob("t")] * 100}
        out, _ = self.collect([crun(1, attempt=2)], {"repos/o/r/actions/runs/1/jobs": page})
        self.assertEqual(out["jobs"], {})
        self.assertIn("100 of 150", out["unfetched"]["1"])

    def test_runs_list_cut_short_is_recorded(self):
        out, _ = self.collect([crun(1)], {"repos/o/r/actions/runs?": {"total_count": 1500, "workflow_runs": []}})
        self.assertIn("1 of 1500", out["runs_cut"])

    def test_integration_branch_falls_back_to_the_default_branch(self):
        out, calls = self.collect([], {"repos/o/r": {"default_branch": "main"}}, branch=None)
        self.assertEqual(out["integration_branch"], "main")

    def test_config_defaults_and_overrides(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d, "config.json")
            self.assertEqual(fm.load_ci_config(str(path)), (fm.CI_DEFAULTS, None))   # no file: defaults
            path.write_text(json.dumps({"integration_branch": "dev", "ci_health": {"long_job_minutes": 90}}))
            cfg, branch = fm.load_ci_config(str(path))
            self.assertEqual((cfg["long_job_minutes"], cfg["queued_no_job_minutes"], branch), (90, 30, "dev"))
            for bad in ({"ci_health": {"long_job_minute": 90}}, {"ci_health": {"red_rate_percent": -1}},
                        {"ci_health": []}):
                path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError, msg=bad):
                    fm.load_ci_config(str(path))
            path.write_text("{")
            with self.assertRaises(ValueError):
                fm.load_ci_config(str(path))

    def test_main_with_an_unreadable_config_still_reports_and_says_could_not_check(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d, "config.json")
            path.write_text(json.dumps({"ci_health": {"long_job_minute": 5}}))
            data = {"issues": [], "pulls": [], "runs": [crun(1)], "milestones": [], "runs_query": "x"}
            out = io.StringIO()
            with mock.patch.object(fm, "collect", return_value=data), \
                    mock.patch.object(fm, "collect_ci_health", side_effect=AssertionError("no API call")), \
                    mock.patch.object(sys, "stdout", out):
                self.assertEqual(fm.main(["--repo", "o/r", "--now", NOW, "--config", str(path)]), 0)
        section = out.getvalue().split("## CI health", 1)[1]
        self.assertIn("could not check: config unreadable", section)
        self.assertIn("long_job_minute", section)

    def test_main_passes_config_and_runs_query_to_collect_ci_health(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d, "config.json")
            path.write_text(json.dumps({"integration_branch": "dev", "ci_health": {"max_job_requests": 7}}))
            data = {"issues": [], "pulls": [], "runs": [], "milestones": [], "runs_query": "repos/o/r/actions/runs?q"}
            health = ci_data([], {}, branch="dev")
            with mock.patch.object(fm, "collect", return_value=data), \
                    mock.patch.object(fm, "collect_ci_health", return_value=health) as spy, \
                    mock.patch.object(sys, "stdout", io.StringIO()):
                fm.main(["--repo", "o/r", "--now", NOW, "--config", str(path)])
        args, kwargs = spy.call_args
        self.assertEqual((args[0], args[3]["max_job_requests"], args[4], kwargs["runs_query"]),
                         ("o/r", 7, "dev", "repos/o/r/actions/runs?q"))


if __name__ == "__main__":
    unittest.main()

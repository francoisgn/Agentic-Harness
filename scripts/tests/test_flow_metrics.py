"""Tests de scripts/flow-metrics.py (sans réseau : données en dur, horloge fixée).

Lancer : python3 -m unittest discover -s scripts/tests -p 'test_*.py'
"""
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "flow-metrics.py"
spec = importlib.util.spec_from_file_location("flow_metrics", SCRIPT)
fm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fm)

NOW = "2026-11-07T12:00:00Z"


def issue(n, labels=(), updated="2026-11-07T10:00:00Z", state="open", milestone=None, assignee=None, title=None):
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
        r = self.analyse(issues=[issue(1, ["pris en charge", "P2 🟠"], updated="2026-11-05T00:00:00Z"),
                                 issue(2, ["pris en charge"], updated="2026-11-07T11:00:00Z")])
        self.assertEqual([s["number"] for s in r["stalled"]], [1])
        self.assertEqual(r["status"], "🟠")

    def test_stalled_p1_is_red(self):
        r = self.analyse(issues=[issue(1, ["pris en charge", "P1 🔴"], updated="2026-11-05T00:00:00Z")])
        self.assertEqual(r["status"], "🔴")

    def test_ready_pr_without_activity_is_stalled_but_not_draft_within_limit(self):
        r = self.analyse(pulls=[pull(10, updated="2026-11-05T00:00:00Z"),
                                pull(11, draft=True, updated="2026-11-05T00:00:00Z")])
        self.assertEqual([s["number"] for s in r["stalled"]], [10])
        r = self.analyse(pulls=[pull(11, draft=True, updated="2026-11-01T00:00:00Z")])
        self.assertEqual([s["number"] for s in r["stalled"]], [11])

    def test_ci_loop_detected_per_open_pr_branch(self):
        runs = [run("claude/lot-1", sha=f"a{k}") for k in range(7)] + [run("claude/autre", sha=f"b{k}") for k in range(7)]
        r = self.analyse(pulls=[pull(10)], runs=runs, max_ci_runs=6)
        self.assertEqual([(lp["number"], lp["kind"]) for lp in r["loops"]], [(10, "ci")])
        self.assertEqual(r["status"], "🔴")

    def test_ci_loop_counts_pushes_not_workflows(self):
        # 4 workflows par push, 2 pushes : 2 passages, pas une boucle (constat de revue n° 1)
        runs = [run("claude/lot-1", sha=f"a{k}", workflow=w) for k in range(2) for w in range(4)]
        self.assertEqual(self.analyse(pulls=[pull(10)], runs=runs, max_ci_runs=6)["loops"], [])

    def test_ci_loop_ignores_push_and_schedule_runs_of_promotion_branch(self):
        runs = [run("develop", sha=f"d{k}", event=e) for k in range(8) for e in ("push", "schedule")]
        self.assertEqual(self.analyse(pulls=[pull(20, ref="develop")], runs=runs, max_ci_runs=6)["loops"], [])

    def test_failure_rate_ignores_cancelled_and_skipped(self):
        runs = [run("x", conclusion="failure"), run("x", conclusion="cancelled"), run("x", conclusion="cancelled"),
                run("x", conclusion="skipped"), run("x", conclusion="success")]
        self.assertEqual(self.analyse(runs=runs)["ci"]["failure_rate"], 50)

    def test_milestones_from_api_take_precedence(self):
        data_ms = [{"title": "Jalon 1", "open_issues": 1, "closed_issues": 9, "due_on": "2026-12-01T00:00:00Z"}]
        r = fm.analyse({"issues": [issue(1, milestone="Jalon 1")], "pulls": [], "runs": [], "milestones": data_ms},
                       now=fm.parse_time(NOW))
        self.assertEqual(r["milestones"], [{"title": "Jalon 1", "closed": 9, "total": 10, "percent": 90,
                                            "due_on": "2026-12-01"}])

    def test_review_round_loop(self):
        r = self.analyse(pulls=[pull(10, reviews=5)], max_review_rounds=3)
        self.assertEqual([(lp["number"], lp["kind"]) for lp in r["loops"]], [(10, "revue")])

    def test_bottlenecks_count_blocked_and_unclear(self):
        r = self.analyse(issues=[issue(1, ["bloqué"]), issue(2, ["à clarifier"]), issue(3, ["bloqué"], state="closed")])
        self.assertEqual(r["bottlenecks"], {"bloqué": [1], "à clarifier": [2]})
        self.assertEqual(r["status"], "🟠")

    def test_milestone_progress(self):
        r = self.analyse(issues=[issue(1, milestone="Jalon 1", state="closed"), issue(2, milestone="Jalon 1"),
                                 issue(3, milestone="Jalon 1", state="closed"), issue(4)])
        self.assertEqual(r["milestones"], [{"title": "Jalon 1", "closed": 2, "total": 3, "percent": 67}])

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
            data = fm.collect("o/r", 14)
        finally:
            fm._gh = original
        self.assertTrue(any("pulls/7/reviews" in c for c in calls))
        self.assertTrue(any("issues/7/comments" in c for c in calls))
        self.assertTrue(any("pulls/7/commits" in c for c in calls))
        self.assertEqual(data["pulls"][0]["reviews"], [])  # sinon pagination de tout l'historique


def review(login, state, body="", at="2026-11-05T02:00:00Z"):
    return {"user": {"login": login}, "state": state, "body": body, "submitted_at": at}


def comment(login, body, at="2026-11-05T02:00:00Z"):
    return {"user": {"login": login}, "body": body, "created_at": at}


def commit(at):
    return {"commit": {"committer": {"date": at}}}


ADV_KO = "**Revue adversariale (fable) : CHANGEMENTS DEMANDÉS** — tête abc"
ADV_OK = "**Revue adversariale (fable) : APPROUVÉ** — tête def"


class ReviewEventTests(unittest.TestCase):
    def test_sources_and_verdicts(self):
        p = pull(1, state="closed", merged="2026-11-06T00:00:00Z")
        p["reviews"] = [review("coderabbitai[bot]", "COMMENTED", "**Actionable comments posted: 3**"),
                        review("coderabbitai[bot]", "COMMENTED", "**Actionable comments posted: 0**"),
                        review("francoisgn", "CHANGES_REQUESTED", "non"),
                        review("francoisgn", "APPROVED", "")]
        p["comments"] = [comment("claude", ADV_KO), comment("claude", ADV_OK),
                         comment("github-actions[bot]", "**Revue conformité RGPD (opus) : ÉCARTS** — tête x"),
                         comment("github-actions[bot]", "**Revue IA (sonnet) : APPROUVÉ** — tête y"),
                         comment("x", "merci")]
        got = [(e["source"], e["problem"]) for e in fm.review_events(p)]
        self.assertEqual(got, [("coderabbit", True), ("coderabbit", False), ("humain", True), ("humain", False),
                               ("adversariale", True), ("adversariale", False), ("conformité", True), ("ia", False)])


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
        self.assertEqual(q["by_source"], {"adversariale": 1, "coderabbit": 1})
        self.assertEqual(q["agent"], {"reviewed": 3, "problem": 2})
        self.assertEqual(q["human"], {"reviewed": 1, "problem": 0})
        self.assertEqual(q["fix_commits_mean"], 1.5)       # PR 1 : 2 commits après 02:00 ; PR 2 : 1 après 03:00
        self.assertEqual(q["fix_hours_median"], 21.5)      # 1er constat → merge : 22 h et 21 h

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
        self.assertIn("## Qualité au premier passage", md)
        self.assertIn("100 %", md)


class RenderTests(unittest.TestCase):
    def test_markdown_has_headline_and_sections(self):
        r = fm.analyse({"issues": [issue(1, ["bloqué", "P1 🔴"], title="Le paiement | casse")], "pulls": [], "runs": []},
                       now=fm.parse_time(NOW))
        md = fm.render_markdown(r, repo="o/r")
        self.assertTrue(md.startswith("# Tableau de bord — o/r"))
        self.assertIn("🟠", md)
        self.assertIn("## Goulots", md)
        self.assertIn("Le paiement \\| casse", md)  # LESSONS L07 : pipe échappé dans un tableau

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
            src.write_text(json.dumps({"issues": [issue(1, ["bloqué"])], "pulls": [], "runs": []}))
            md = subprocess.run([sys.executable, str(SCRIPT), "--input", str(src), "--now", NOW, "--json-out", str(dst)],
                                capture_output=True, text=True, check=True).stdout
            self.assertIn("# Tableau de bord", md)
            self.assertEqual(json.loads(dst.read_text())["status"], "🟠")


if __name__ == "__main__":
    unittest.main()

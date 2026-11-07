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


def run(branch, conclusion="failure", created="2026-11-06T10:00:00Z", minutes=3):
    start = fm.parse_time(created)
    return {
        "head_branch": branch,
        "conclusion": conclusion,
        "event": "pull_request",
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
        runs = [run("claude/lot-1") for _ in range(7)] + [run("claude/autre") for _ in range(7)]
        r = self.analyse(pulls=[pull(10)], runs=runs, max_ci_runs=6)
        self.assertEqual([(lp["number"], lp["kind"]) for lp in r["loops"]], [(10, "ci")])
        self.assertEqual(r["status"], "🔴")

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

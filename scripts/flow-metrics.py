#!/usr/bin/env python3
"""Flow dashboard of a repository: progress, bottlenecks, stalled work, loops, CI cost (docs/FINOPS.md §4).

Reads the issues, PRs and CI runs of a GitHub repository (through `gh api`, workflow or session token) or a JSON file
(`--input`, for tests and replay), then writes a Markdown report a non-technical reader can follow, or JSON.
Read-only; publishing the report (issue "Project dashboard") is the job of the flow-report.yml workflow.

Usage:
  flow-metrics.py --repo owner/name [--format md|json] [--stall-hours 24] [--draft-stall-hours 120]
                  [--max-ci-runs 6] [--max-review-rounds 3] [--window-days 14] [--json-out f]
  flow-metrics.py --input data.json --now 2026-11-07T12:00:00Z
Standard library only (Python >= 3.9).
"""
import argparse
import calendar
import json
import math
import re
import statistics
import subprocess
import sys
import time

# Agent PR: `Claim: <id>` of an agent (a human claims with `human/<login>`, CONVENTIONS.md §PR), generation footer,
# or old `claude/...` branch (convention before 0.3.0, kept for history).
AGENT_PREFIXES = ("claude/",)
AGENT_BODY_RE = re.compile(r"^Claim:[ \t]*(?!human/)\S+|Generated with \[Claude Code\]", re.M)
LABEL_CLAIMED = "status: claimed"
BOTTLENECK_LABELS = ("status: blocked", "status: needs-decision")
HIGH_PRIORITY_LABELS = ("priority: critical", "priority: high")
STATUS_PREFIX = "status: "


VERDICT_RE = re.compile(r"\*\*(Adversarial|AI|Compliance) review[^*\n]*?:\s*"
                        r"(APPROVED|CHANGES REQUESTED|COMPLIANT|GAPS|OUT OF SCOPE)")
VERDICT_SOURCE = {"Adversarial": "adversarial", "AI": "ai", "Compliance": "compliance"}
VERDICT_PROBLEMS = ("CHANGES REQUESTED", "GAPS")
VERDICT_IGNORED = "OUT OF SCOPE"
# "· unverified: N" at the end of a verdict line: points the reviewer could not check (REVIEW-ROUNDS §Traceability)
UNVERIFIED_RE = re.compile(r"unverified:\s*(\d+)", re.I)
ACTIONABLE_RE = re.compile(r"Actionable comments posted:\s*(\d+)")
MIN_QUALITY_SAMPLE = 3


def review_events(pull):
    """Verdicts traced on a PR, in order (GitHub reviews, then comments): [{source, problem, at[, unverified]}].

    Sources: harness verdicts ("**Adversarial review|AI review|Compliance review (...): VERDICT**", REVIEW-ROUNDS.md,
    traceability section), CodeRabbit ("Actionable comments posted: N"), humans (APPROVED / CHANGES_REQUESTED).
    Everything else is ignored.
    """
    events = []
    items = [(rv.get("body") or "", rv.get("state"), (rv.get("user") or {}).get("login", ""), rv.get("submitted_at"))
             for rv in pull.get("reviews", [])]
    items += [(c.get("body") or "", None, (c.get("user") or {}).get("login", ""), c.get("created_at"))
              for c in pull.get("comments", [])]
    for body, state, login, at in items:
        # Verdicts at the start of a line only: a quote (`>`) or a table row (`|`) does not count;
        # one body can carry several (consolidation by /compliance-review).
        verdicts = [m for line in body.splitlines() if not line.lstrip().startswith((">", "|"))
                    for m in [VERDICT_RE.match(re.sub(r"^(?:[-*]|\d+[.)])\s+", "", line.strip()))] if m]
        if verdicts:
            events += [{"source": VERDICT_SOURCE[m.group(1)], "at": at,
                        "problem": m.group(2) in VERDICT_PROBLEMS,
                        "unverified": int(u.group(1)) if (u := UNVERIFIED_RE.search(m.string)) else 0}
                       for m in verdicts if m.group(2) != VERDICT_IGNORED]
            continue
        if login.startswith("coderabbitai"):
            n = ACTIONABLE_RE.search(body)
            if n:
                events.append({"source": "coderabbit", "at": at, "problem": int(n.group(1)) > 0})
            elif state == "CHANGES_REQUESTED":
                events.append({"source": "coderabbit", "at": at, "problem": True})
        elif state in ("APPROVED", "CHANGES_REQUESTED"):
            events.append({"source": "bot" if login.endswith("[bot]") else "human", "at": at,
                           "problem": state == "CHANGES_REQUESTED"})
    return events


def quality(merged):
    """First-pass quality and fix effort on merged PRs (FINOPS.md §4)."""
    q = {"reviewed": 0, "problem": 0, "untraced": 0, "unverified": 0, "by_source": {},
         "agent": {"reviewed": 0, "problem": 0}, "human": {"reviewed": 0, "problem": 0}}
    fix_commits, fix_hours = [], []
    for p in merged:
        merged_at = parse_time(p["merged_at"])
        # A verdict posted after the merge says nothing about first-pass quality
        events = [e for e in review_events(p) if not e.get("at") or parse_time(e["at"]) <= merged_at]
        if not events:
            q["untraced"] += 1
            continue
        side = q["agent"] if is_agent(p) else q["human"]
        q["reviewed"] += 1
        # Last harness verdict of each source, in time order: does any still list unverified points?
        last = {}
        for e in sorted((e for e in events if "unverified" in e), key=lambda e: e.get("at") or ""):
            last[e["source"]] = e["unverified"]
        if any(last.values()):
            q["unverified"] += 1
        side["reviewed"] += 1
        problems = [e for e in events if e["problem"]]
        if not problems:
            continue
        q["problem"] += 1
        side["problem"] += 1
        for src in sorted({e["source"] for e in problems}):
            q["by_source"][src] = q["by_source"].get(src, 0) + 1
        dated = [parse_time(e["at"]) for e in problems if e.get("at")]
        if not dated:
            continue
        first = min(dated)
        commits = [c["commit"]["committer"]["date"] for c in p.get("commits", [])]
        fix_commits.append(sum(1 for d in commits if parse_time(d) > first))
        fix_hours.append(_hours(parse_time(p["merged_at"]) - first))
    q["by_source"] = dict(sorted(q["by_source"].items()))
    q["problem_ratio"] = round(100 * q["problem"] / q["reviewed"]) if q["reviewed"] else None
    q["fix_commits_mean"] = round(sum(fix_commits) / len(fix_commits), 1) if fix_commits else None
    q["fix_hours_median"] = round(statistics.median(fix_hours), 1) if fix_hours else None
    return q


def is_agent(pull):
    """PR written by an agent (AGENT_BODY_RE), rather than by a human."""
    return pull["head"]["ref"].startswith(AGENT_PREFIXES) or bool(AGENT_BODY_RE.search(pull.get("body") or ""))


def parse_time(value):
    """ISO 8601 UTC (`2026-11-07T12:00:00Z`) → epoch seconds."""
    return calendar.timegm(time.strptime(value.replace("Z", "")[:19], "%Y-%m-%dT%H:%M:%S"))


def format_time(seconds):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(seconds))


def _labels(item):
    return [label["name"] if isinstance(label, dict) else label for label in item.get("labels", [])]


def _hours(seconds):
    return seconds / 3600


def analyse(data, now, stall_hours=24, draft_stall_hours=120, max_ci_runs=6, max_review_rounds=3, window_days=14,
            max_problem_ratio=50):
    """Compute the report from {"issues", "pulls", "runs"} (shapes of the GitHub REST API)."""
    issues = [i for i in data.get("issues", []) if "pull_request" not in i]
    pulls = data.get("pulls", [])
    runs = data.get("runs", [])
    open_issues = [i for i in issues if i["state"] == "open"]
    open_pulls = [p for p in pulls if p["state"] == "open"]

    stalled = []
    for i in open_issues:
        idle = _hours(now - parse_time(i["updated_at"]))
        if LABEL_CLAIMED in _labels(i) and idle > stall_hours:
            stalled.append({"kind": "issue", "number": i["number"], "title": i["title"], "idle_hours": round(idle),
                            "high_priority": any(lb in HIGH_PRIORITY_LABELS for lb in _labels(i)),
                            "url": i.get("html_url")})
    for p in open_pulls:
        idle = _hours(now - parse_time(p["updated_at"]))
        if idle > (draft_stall_hours if p.get("draft") else stall_hours):
            stalled.append({"kind": "PR", "number": p["number"], "title": p["title"], "idle_hours": round(idle),
                            "high_priority": False, "url": p.get("html_url")})

    # One CI run = one tested push on the PR: distinct SHAs of the `pull_request` runs of its branch. Neither the number
    # of workflows per push nor the push/schedule runs of a promotion branch (develop) count, nor do runs that were
    # entirely skipped or cancelled: pushing often on a draft costs nothing and is not a loop (CI-BUDGET §2).
    pushes_by_branch = {}
    for r in runs:
        if r.get("event") == "pull_request" and r.get("conclusion") not in ("skipped", "cancelled"):
            pushes_by_branch.setdefault(r.get("head_branch"), set()).add(r.get("head_sha"))
    loops = []
    for p in open_pulls:
        n_runs = len(pushes_by_branch.get(p["head"]["ref"], ()))
        if n_runs > max_ci_runs:
            loops.append({"kind": "ci", "number": p["number"], "title": p["title"], "count": n_runs,
                          "url": p.get("html_url")})
        if p.get("review_count", 0) > max_review_rounds:
            loops.append({"kind": "review", "number": p["number"], "title": p["title"], "count": p["review_count"],
                          "url": p.get("html_url")})

    bottlenecks = {}
    bottleneck_items = [{"number": i["number"], "title": i["title"],
                         "labels": [lb for lb in _labels(i) if lb in BOTTLENECK_LABELS]}
                        for i in sorted(open_issues, key=lambda i: i["number"])
                        if any(lb in BOTTLENECK_LABELS for lb in _labels(i))]
    for label in BOTTLENECK_LABELS:
        numbers = sorted(i["number"] for i in open_issues if label in _labels(i))
        if numbers:
            bottlenecks[label] = numbers

    # An open issue carries exactly one `status:` label: count them per value, list the issues with none or several.
    status_counts, status_anomalies = {}, []
    for i in sorted(open_issues, key=lambda i: i["number"]):
        statuses = [lb for lb in _labels(i) if lb.startswith(STATUS_PREFIX)]
        for lb in statuses:
            status_counts[lb] = status_counts.get(lb, 0) + 1
        if len(statuses) != 1:
            status_anomalies.append({"number": i["number"], "title": i["title"], "statuses": statuses,
                                     "url": i.get("html_url")})

    milestones = {}
    for i in ([] if data.get("milestones") else issues):
        if i.get("milestone"):
            m = milestones.setdefault(i["milestone"]["title"], {"closed": 0, "total": 0})
            m["total"] += 1
            m["closed"] += i["state"] == "closed"
    milestone_list = [{"title": t, "closed": m["closed"], "total": m["total"],
                       "percent": round(100 * m["closed"] / m["total"])} for t, m in sorted(milestones.items())]
    if data.get("milestones"):  # exact source: API counters, old issues included
        milestone_list = []
        for m in sorted(data["milestones"], key=lambda m: m["title"]):
            total = m["open_issues"] + m["closed_issues"]
            if total:
                milestone_list.append({"title": m["title"], "closed": m["closed_issues"], "total": total,
                                       "percent": round(100 * m["closed_issues"] / total),
                                       "due_on": (m.get("due_on") or "")[:10] or None})

    window_start = now - window_days * 86400
    merged = [p for p in pulls if p.get("merged_at") and parse_time(p["merged_at"]) >= window_start]
    agent = [p for p in merged if is_agent(p)]
    leads = [_hours(parse_time(p["merged_at"]) - parse_time(p["created_at"])) for p in merged]

    durations = []
    for r in runs:
        start = r.get("run_started_at") or r.get("created_at")
        if start and r.get("updated_at") and r.get("conclusion") != "skipped":  # a skipped run bills nothing
            durations.append(max(0.0, (parse_time(r["updated_at"]) - parse_time(start)) / 60))
    # Cancelled (cancel-in-progress) and skipped (draft) say nothing about quality: left out of the denominator.
    finished = [r for r in runs if r.get("conclusion") in ("success", "failure")]
    failures = [r for r in finished if r["conclusion"] == "failure"]

    by_type = {}
    for i in open_issues:
        for lb in _labels(i):
            by_type[lb] = by_type.get(lb, 0) + 1

    q = quality(merged)
    high_problem = (q["problem_ratio"] is not None and q["reviewed"] >= MIN_QUALITY_SAMPLE
                    and q["problem_ratio"] > max_problem_ratio)

    if any(s["high_priority"] for s in stalled) or loops:
        status = "🔴"
    elif stalled or bottlenecks or high_problem or status_anomalies:
        status = "🟠"
    else:
        status = "🟢"

    return {
        "status": status,
        "generated_at": format_time(now),
        "open": {"issues": len(open_issues), "pulls": len(open_pulls),
                 "drafts": sum(1 for p in open_pulls if p.get("draft"))},
        "labels": dict(sorted(by_type.items(), key=lambda kv: (-kv[1], kv[0]))),
        "milestones": milestone_list,
        "stalled": sorted(stalled, key=lambda s: -s["idle_hours"]),
        "loops": loops,
        "bottlenecks": bottlenecks,
        "bottleneck_items": bottleneck_items,
        "status_counts": dict(sorted(status_counts.items())),
        "status_anomalies": status_anomalies,
        "merged": {"total": len(merged), "agent": len(agent), "human": len(merged) - len(agent),
                   "median_lead_hours": round(statistics.median(leads), 1) if leads else None},
        "quality": q,
        "ci": {"runs": len(runs),
               # Every job is rounded up to the minute (CI-BUDGET.md §1): without the job details, lower bound per run.
               "billed_minutes_min": sum(max(1, math.ceil(d)) for d in durations),
               "failure_rate": round(100 * len(failures) / len(finished)) if finished else 0},
        "thresholds": {"stall_hours": stall_hours, "draft_stall_hours": draft_stall_hours,
                       "max_ci_runs": max_ci_runs, "max_review_rounds": max_review_rounds, "window_days": window_days,
                       "max_problem_ratio": max_problem_ratio},
    }


def _cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def render_markdown(r, repo):
    verdict = {"🟢": "OK: the flow is moving", "🟠": "Watch: items are waiting",
               "🔴": "Critical: a stall or a loop to handle"}[r["status"]]
    out = [f"# Project dashboard: {repo}", "",
           f"**{r['status']} {verdict}** · generated on {r['generated_at']} (UTC)", "",
           "| Indicator | Value |", "|---|---|",
           f"| Open issues | {r['open']['issues']} |",
           f"| Open PRs (of which drafts) | {r['open']['pulls']} ({r['open']['drafts']}) |",
           f"| PRs merged over {r['thresholds']['window_days']} d (agents / humans) | "
           f"{r['merged']['total']} ({r['merged']['agent']} / {r['merged']['human']}) |",
           f"| Median time from opening to merge | "
           f"{'—' if r['merged']['median_lead_hours'] is None else str(r['merged']['median_lead_hours']) + ' h'} |",
           f"| CI runs (billed minutes, lower bound) | {r['ci']['runs']} ({r['ci']['billed_minutes_min']} min) |",
           f"| CI failure rate | {r['ci']['failure_rate']}% |", ""]
    if r["milestones"]:
        out += ["## Milestones", "", "| Milestone | Progress | Closed / total | Due date |", "|---|---|---|---|"]
        for m in r["milestones"]:
            bar = "█" * (m["percent"] // 10) + "░" * (10 - m["percent"] // 10)
            out.append(f"| {_cell(m['title'])} | `{bar}` {m['percent']}% | {m['closed']} / {m['total']} | "
                       f"{m.get('due_on') or '—'} |")
        out.append("")
    out += ["## Open issues by status", ""]
    if r["status_counts"]:
        out += ["| Status | Count |", "|---|---|"]
        out += [f"| `{_cell(k)}` | {v} |" for k, v in r["status_counts"].items()]
    else:
        out.append("- No open issue carries a `status:` label.")
    if r["status_anomalies"]:
        out += ["", f"🟠 {len(r['status_anomalies'])} open issue(s) without exactly one `status:` label:", "",
                "| Issue | Title | `status:` labels |", "|---|---|---|"]
        out += [f"| #{a['number']} | {_cell(a['title'])} | {_cell(', '.join(a['statuses'])) or 'none'} |"
                for a in r["status_anomalies"]]
    out += ["", "## Bottlenecks", ""]
    if r["bottleneck_items"]:
        out += ["| Issue | Title | Status |", "|---|---|---|"]
        out += [f"| #{b['number']} | {_cell(b['title'])} | {', '.join(b['labels'])} |" for b in r["bottleneck_items"]]
    else:
        out.append("- No `status: blocked` or `status: needs-decision` item.")
    out += ["", "## Stalled (no activity)", ""]
    if r["stalled"]:
        out += ["| Item | Title | Idle for |", "|---|---|---|"]
        out += [f"| {s['kind']} #{s['number']}{' 🔴' if s['high_priority'] else ''} | {_cell(s['title'])} | "
                f"{s['idle_hours']} h |" for s in r["stalled"]]
    else:
        out.append("- Nothing.")
    out += ["", "## Loops (CI or review going round in circles)", ""]
    if r["loops"]:
        out += ["| PR | Title | Kind | Count |", "|---|---|---|---|"]
        out += [f"| #{lp['number']} | {_cell(lp['title'])} | {lp['kind']} | {lp['count']} |" for lp in r["loops"]]
    else:
        out.append("- Nothing.")
    q = r["quality"]
    out += ["", "## First-pass quality", ""]
    if q["reviewed"]:
        def ratio(side):
            return f"{round(100 * side['problem'] / side['reviewed'])}% ({side['problem']}/{side['reviewed']})" \
                if side["reviewed"] else "—"
        out += ["| Indicator | Value |", "|---|---|",
                f"| PRs with a problem (at least one review finding) | {q['problem_ratio']}% "
                f"({q['problem']}/{q['reviewed']}) |",
                f"| … written by agents / by humans | {ratio(q['agent'])} / {ratio(q['human'])} |",
                "| Findings by source (PRs concerned) | "
                + (", ".join(f"{k} {v}" for k, v in q["by_source"].items()) or "—") + " |",
                f"| Fix effort: commits after the first finding (mean) | "
                f"{'—' if q['fix_commits_mean'] is None else q['fix_commits_mean']} |",
                f"| Time from first finding to merge (median) | "
                f"{'—' if q['fix_hours_median'] is None else str(q['fix_hours_median']) + ' h'} |"]
    else:
        out.append("- No merged PR with a traced review over the period.")
    if q["untraced"]:
        out.append(f"\n🟠 {q['untraced']} merged PR(s) without any traced verdict: the measure ignores them "
                   "(REVIEW-ROUNDS.md, traceability section).")
    if q.get("unverified"):
        out.append(f"\n🟠 {q['unverified']} merged PR(s) approved with unverified points: the last verdict of a "
                   "review still lists them; check that each was verified or accepted on the PR "
                   "(REVIEW-ROUNDS.md, traceability section).")
    if r["labels"]:
        out += ["", "## Open issues by label", "", "| Label | Count |", "|---|---|"]
        out += [f"| {_cell(k)} | {v} |" for k, v in r["labels"].items()]
    t = r["thresholds"]
    out += ["", f"_Thresholds: idle {t['stall_hours']} h (draft {t['draft_stall_hours']} h), "
                f"CI loop > {t['max_ci_runs']} tested pushes, review loop > {t['max_review_rounds']} reviews, "
                f"PRs with a problem > {t['max_problem_ratio']}% (from {MIN_QUALITY_SAMPLE} reviewed PRs). "
                "How to read it: FINOPS.md §4 of Belayline._", ""]
    return "\n".join(out)


def _gh(path):
    out = subprocess.run(["gh", "api", "--paginate", "--slurp", path], capture_output=True, text=True, check=True).stdout
    pages = json.loads(out)
    items = []
    for page in pages:
        items.extend(page.get("workflow_runs", []) if isinstance(page, dict) else page)
    return items


def collect(repo, window_days):
    since = format_time(time.time() - max(window_days, 30) * 86400)
    # Open: all of them, without `since` (a claim idle for a long time is the worst stall);
    # closed: the window only. Milestones: API counters, exact however old the issues are.
    issues = _gh(f"repos/{repo}/issues?state=open&per_page=100")
    issues += _gh(f"repos/{repo}/issues?state=closed&per_page=100&since={since}")
    milestones = _gh(f"repos/{repo}/milestones?state=open&per_page=100")
    pulls = _gh(f"repos/{repo}/pulls?state=all&per_page=100&sort=updated&direction=desc")
    pulls = [p for p in pulls if p["state"] == "open" or (p.get("updated_at") or "") >= since]
    for p in pulls:
        if p["state"] == "open":
            p["review_count"] = len(_gh(f"repos/{repo}/pulls/{p['number']}/reviews?per_page=100"))
        elif p.get("merged_at") and p["merged_at"] >= since:
            # First-pass quality: verdicts (reviews, comments) and fix commits
            p["reviews"] = _gh(f"repos/{repo}/pulls/{p['number']}/reviews?per_page=100")
            p["comments"] = _gh(f"repos/{repo}/issues/{p['number']}/comments?per_page=100")
            p["commits"] = _gh(f"repos/{repo}/pulls/{p['number']}/commits?per_page=100")
    runs = _gh(f"repos/{repo}/actions/runs?per_page=100&created=>={since[:10]}")
    return {"issues": issues, "pulls": pulls, "runs": runs, "milestones": milestones}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--repo")
    src.add_argument("--input")
    ap.add_argument("--now", help="fixed clock (tests, replay)")
    ap.add_argument("--format", choices=("md", "json"), default="md")
    ap.add_argument("--json-out", help="also writes the JSON report to this file (a single collection)")
    ap.add_argument("--stall-hours", type=float, default=24)
    ap.add_argument("--draft-stall-hours", type=float, default=120)
    ap.add_argument("--max-ci-runs", type=int, default=6)
    ap.add_argument("--max-review-rounds", type=int, default=3)
    ap.add_argument("--window-days", type=int, default=14)
    ap.add_argument("--max-problem-ratio", type=int, default=50,
                    help="%% of PRs with a problem above which the status turns 🟠")
    a = ap.parse_args(argv)
    if a.input:
        with open(a.input, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = collect(a.repo, a.window_days)
    now = parse_time(a.now) if a.now else time.time()
    report = analyse(data, now, a.stall_hours, a.draft_stall_hours, a.max_ci_runs, a.max_review_rounds, a.window_days,
                     a.max_problem_ratio)
    if a.json_out:
        with open(a.json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    if a.format == "json":
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_markdown(report, a.repo or a.input))
    return 0


if __name__ == "__main__":
    sys.exit(main())

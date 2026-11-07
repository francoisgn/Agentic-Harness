#!/usr/bin/env python3
"""Tableau de bord du flux d'un dépôt : avancement, goulots, travaux en panne, boucles, coût CI (docs/FINOPS.md §4).

Lit les issues, PR et passages de CI d'un dépôt GitHub (via `gh api`, jeton du workflow ou de la session) ou un fichier
JSON (`--input`, pour les tests et le rejeu), puis écrit un rapport Markdown lisible par un non-technicien, ou du JSON.
Ne fait que lire ; publier le rapport (issue « Tableau de bord ») est le travail du workflow flow-report.yml.

Usage :
  flow-metrics.py --repo owner/nom [--format md|json] [--stall-hours 24] [--draft-stall-hours 120]
                  [--max-ci-runs 6] [--max-review-rounds 3] [--window-days 14] [--json-out f]
  flow-metrics.py --input donnees.json --now 2026-11-07T12:00:00Z
Bibliothèque standard seulement (Python ≥ 3.9).
"""
import argparse
import calendar
import json
import math
import statistics
import subprocess
import sys
import time

AGENT_PREFIXES = ("claude/",)
LABEL_CLAIMED = "pris en charge"
BOTTLENECK_LABELS = ("bloqué", "à clarifier")
P1_PREFIX = "P1"


def parse_time(value):
    """ISO 8601 UTC (`2026-11-07T12:00:00Z`) → secondes epoch."""
    return calendar.timegm(time.strptime(value.replace("Z", "")[:19], "%Y-%m-%dT%H:%M:%S"))


def format_time(seconds):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(seconds))


def _labels(item):
    return [label["name"] if isinstance(label, dict) else label for label in item.get("labels", [])]


def _hours(seconds):
    return seconds / 3600


def analyse(data, now, stall_hours=24, draft_stall_hours=120, max_ci_runs=6, max_review_rounds=3, window_days=14):
    """Calcule le rapport à partir de {"issues", "pulls", "runs"} (formes de l'API REST GitHub)."""
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
                            "p1": any(lb.startswith(P1_PREFIX) for lb in _labels(i)), "url": i.get("html_url")})
    for p in open_pulls:
        idle = _hours(now - parse_time(p["updated_at"]))
        if idle > (draft_stall_hours if p.get("draft") else stall_hours):
            stalled.append({"kind": "PR", "number": p["number"], "title": p["title"], "idle_hours": round(idle),
                            "p1": False, "url": p.get("html_url")})

    # Un passage de CI = un push testé sur la PR : SHA distincts des runs `pull_request` de sa branche. Ni le nombre de
    # workflows par push, ni les runs push/schedule d'une branche de promotion (develop) ne comptent.
    pushes_by_branch = {}
    for r in runs:
        if r.get("event") == "pull_request":
            pushes_by_branch.setdefault(r.get("head_branch"), set()).add(r.get("head_sha"))
    loops = []
    for p in open_pulls:
        n_runs = len(pushes_by_branch.get(p["head"]["ref"], ()))
        if n_runs > max_ci_runs:
            loops.append({"kind": "ci", "number": p["number"], "title": p["title"], "count": n_runs,
                          "url": p.get("html_url")})
        if p.get("review_count", 0) > max_review_rounds:
            loops.append({"kind": "revue", "number": p["number"], "title": p["title"], "count": p["review_count"],
                          "url": p.get("html_url")})

    bottlenecks = {}
    bottleneck_items = [{"number": i["number"], "title": i["title"], "labels": [lb for lb in _labels(i) if lb in BOTTLENECK_LABELS]}
                        for i in sorted(open_issues, key=lambda i: i["number"])
                        if any(lb in BOTTLENECK_LABELS for lb in _labels(i))]
    for label in BOTTLENECK_LABELS:
        numbers = sorted(i["number"] for i in open_issues if label in _labels(i))
        if numbers:
            bottlenecks[label] = numbers

    milestones = {}
    for i in ([] if data.get("milestones") else issues):
        if i.get("milestone"):
            m = milestones.setdefault(i["milestone"]["title"], {"closed": 0, "total": 0})
            m["total"] += 1
            m["closed"] += i["state"] == "closed"
    milestone_list = [{"title": t, "closed": m["closed"], "total": m["total"],
                       "percent": round(100 * m["closed"] / m["total"])} for t, m in sorted(milestones.items())]
    if data.get("milestones"):  # source exacte : compteurs de l'API, issues anciennes comprises
        milestone_list = []
        for m in sorted(data["milestones"], key=lambda m: m["title"]):
            total = m["open_issues"] + m["closed_issues"]
            if total:
                milestone_list.append({"title": m["title"], "closed": m["closed_issues"], "total": total,
                                       "percent": round(100 * m["closed_issues"] / total),
                                       "due_on": (m.get("due_on") or "")[:10] or None})

    window_start = now - window_days * 86400
    merged = [p for p in pulls if p.get("merged_at") and parse_time(p["merged_at"]) >= window_start]
    agent = [p for p in merged if p["head"]["ref"].startswith(AGENT_PREFIXES)]
    leads = [_hours(parse_time(p["merged_at"]) - parse_time(p["created_at"])) for p in merged]

    durations = []
    for r in runs:
        start = r.get("run_started_at") or r.get("created_at")
        if start and r.get("updated_at"):
            durations.append(max(0.0, (parse_time(r["updated_at"]) - parse_time(start)) / 60))
    # Annulés (cancel-in-progress) et sautés (brouillon) ne disent rien de la qualité : hors du dénominateur.
    finished = [r for r in runs if r.get("conclusion") in ("success", "failure")]
    failures = [r for r in finished if r["conclusion"] == "failure"]

    by_type = {}
    for i in open_issues:
        for lb in _labels(i):
            by_type[lb] = by_type.get(lb, 0) + 1

    if any(s["p1"] for s in stalled) or loops:
        status = "🔴"
    elif stalled or bottlenecks:
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
        "merged": {"total": len(merged), "agent": len(agent), "human": len(merged) - len(agent),
                   "median_lead_hours": round(statistics.median(leads), 1) if leads else None},
        "ci": {"runs": len(runs),
               # Chaque job est arrondi à la minute (CI-BUDGET.md §1) : sans le détail des jobs, borne basse par passage.
               "billed_minutes_min": sum(max(1, math.ceil(d)) for d in durations),
               "failure_rate": round(100 * len(failures) / len(finished)) if finished else 0},
        "thresholds": {"stall_hours": stall_hours, "draft_stall_hours": draft_stall_hours,
                       "max_ci_runs": max_ci_runs, "max_review_rounds": max_review_rounds, "window_days": window_days},
    }


def _cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def render_markdown(r, repo):
    verdict = {"🟢": "OK : le flux avance", "🟠": "Vigilance : des éléments attendent",
               "🔴": "Critique : panne ou boucle à traiter"}[r["status"]]
    out = [f"# Tableau de bord — {repo}", "",
           f"**{r['status']} {verdict}** · généré le {r['generated_at']} (UTC)", "",
           "| Indicateur | Valeur |", "|---|---|",
           f"| Issues ouvertes | {r['open']['issues']} |",
           f"| PR ouvertes (dont brouillons) | {r['open']['pulls']} ({r['open']['drafts']}) |",
           f"| PR mergées sur {r['thresholds']['window_days']} j (agents / humains) | "
           f"{r['merged']['total']} ({r['merged']['agent']} / {r['merged']['human']}) |",
           f"| Délai médian ouverture → merge | "
           f"{'—' if r['merged']['median_lead_hours'] is None else str(r['merged']['median_lead_hours']) + ' h'} |",
           f"| Passages de CI (minutes facturées, borne basse) | {r['ci']['runs']} ({r['ci']['billed_minutes_min']} min) |",
           f"| Taux d'échec CI | {r['ci']['failure_rate']} % |", ""]
    if r["milestones"]:
        out += ["## Jalons", "", "| Jalon | Avancement | Fermées / total | Échéance |", "|---|---|---|---|"]
        for m in r["milestones"]:
            bar = "█" * (m["percent"] // 10) + "░" * (10 - m["percent"] // 10)
            out.append(f"| {_cell(m['title'])} | `{bar}` {m['percent']} % | {m['closed']} / {m['total']} | "
                       f"{m.get('due_on') or '—'} |")
        out.append("")
    out += ["## Goulots", ""]
    if r["bottleneck_items"]:
        out += ["| Issue | Titre | Statut |", "|---|---|---|"]
        out += [f"| #{b['number']} | {_cell(b['title'])} | {', '.join(b['labels'])} |" for b in r["bottleneck_items"]]
    else:
        out.append("- Aucun élément `bloqué` ni `à clarifier`.")
    out += ["", "## En panne (sans activité)", ""]
    if r["stalled"]:
        out += ["| Élément | Titre | Inactif depuis |", "|---|---|---|"]
        out += [f"| {s['kind']} #{s['number']}{' 🔴' if s['p1'] else ''} | {_cell(s['title'])} | {s['idle_hours']} h |"
                for s in r["stalled"]]
    else:
        out.append("- Rien.")
    out += ["", "## Boucles (CI ou revue qui tournent en rond)", ""]
    if r["loops"]:
        out += ["| PR | Titre | Type | Nombre |", "|---|---|---|---|"]
        out += [f"| #{lp['number']} | {_cell(lp['title'])} | {lp['kind']} | {lp['count']} |" for lp in r["loops"]]
    else:
        out.append("- Rien.")
    if r["labels"]:
        out += ["", "## Issues ouvertes par label", "", "| Label | Nombre |", "|---|---|"]
        out += [f"| {_cell(k)} | {v} |" for k, v in r["labels"].items()]
    t = r["thresholds"]
    out += ["", f"_Seuils : inactivité {t['stall_hours']} h (brouillon {t['draft_stall_hours']} h), "
                f"boucle CI > {t['max_ci_runs']} pushes testés, boucle de revue > {t['max_review_rounds']} revues. "
                "Lecture : FINOPS.md §4 du cadre agentic-harness._", ""]
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
    # Ouvertes : toutes, sans `since` (une prise en charge inactive depuis longtemps est la panne la plus grave) ;
    # fermées : la fenêtre seulement. Jalons : compteurs de l'API, exacts quelle que soit l'ancienneté des issues.
    issues = _gh(f"repos/{repo}/issues?state=open&per_page=100")
    issues += _gh(f"repos/{repo}/issues?state=closed&per_page=100&since={since}")
    milestones = _gh(f"repos/{repo}/milestones?state=open&per_page=100")
    pulls = _gh(f"repos/{repo}/pulls?state=all&per_page=100&sort=updated&direction=desc")
    pulls = [p for p in pulls if p["state"] == "open" or (p.get("updated_at") or "") >= since]
    for p in pulls:
        if p["state"] == "open":
            p["review_count"] = len(_gh(f"repos/{repo}/pulls/{p['number']}/reviews?per_page=100"))
    runs = _gh(f"repos/{repo}/actions/runs?per_page=100&created=>={since[:10]}")
    return {"issues": issues, "pulls": pulls, "runs": runs, "milestones": milestones}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--repo")
    src.add_argument("--input")
    ap.add_argument("--now", help="horloge fixée (tests, rejeu)")
    ap.add_argument("--format", choices=("md", "json"), default="md")
    ap.add_argument("--json-out", help="écrit aussi le rapport JSON dans ce fichier (une seule collecte)")
    ap.add_argument("--stall-hours", type=float, default=24)
    ap.add_argument("--draft-stall-hours", type=float, default=120)
    ap.add_argument("--max-ci-runs", type=int, default=6)
    ap.add_argument("--max-review-rounds", type=int, default=3)
    ap.add_argument("--window-days", type=int, default=14)
    a = ap.parse_args(argv)
    if a.input:
        with open(a.input, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = collect(a.repo, a.window_days)
    now = parse_time(a.now) if a.now else time.time()
    report = analyse(data, now, a.stall_hours, a.draft_stall_hours, a.max_ci_runs, a.max_review_rounds, a.window_days)
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

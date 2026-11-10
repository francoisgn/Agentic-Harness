#!/usr/bin/env python3
"""README progress table generated from the issues (README-STANDARD.md §3): it cannot lie, it is read from GitHub.

One row per lot (`type: epic` issue, open or closed): title, state, closed/total sub-issues, links to the issue and
to its PRs. A project without epics gets one row per GitHub milestone (closed/total issues). Only the text between
`<!-- harness:begin progress -->` and `<!-- harness:end progress -->` is rewritten; without markers, nothing is.

Lot state, first rule that applies (open issues with zero or several `status:` labels are flagged ⚠ and ignored):
  🟢 shipped      every sub-issue closed
  🟠 in review    a linked PR is open and not a draft
  🔵 in progress  `status: claimed` on the epic or an open sub-issue
  🔴 blocked      `status: blocked` or `status: needs-decision` on the epic or an open sub-issue
  ⚪ to do        otherwise;   ⚠ no sub-issue: the epic has none (never guessed)
A PR belongs to a lot when its body names the epic or one of its sub-issues after Closes/Fixes/Resolves/Refs (`#n`);
a PR closed without merge is not linked.
Milestone state: 🟢 closed or all issues closed · 🔵 some closed · ⚪ none closed · ⚠ no issue.

Usage: readme-progress.py [--repo owner/name] [--readme README.md] [--check]
  --check  writes nothing; exits 1 if the committed block differs from the generated one (the diff is printed).
Exit codes: 0 written or up to date; 1 drift (--check); 2 nothing done: no token, no network, API error, no markers.
Token: GH_TOKEN (or GITHUB_TOKEN), read access to issues and pull requests. Repository: --repo or GITHUB_REPOSITORY.
API (REST, 2022-11-28): GET /repos/{o}/{r}/issues, /issues/{n}/sub_issues, /pulls, /milestones
(docs.github.com/en/rest/issues/sub-issues, /rest/issues/milestones, /rest/pulls/pulls). Standard library only.
"""
import argparse
import difflib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"
BEGIN, END = "<!-- harness:begin progress -->", "<!-- harness:end progress -->"
EPIC_LABEL = "type: epic"
STATUS_PREFIX = "status: "
CLAIMED = "status: claimed"
BLOCKED = ("status: blocked", "status: needs-decision")
PER_PAGE = 100
MAX_PAGES = 50   # 5,000 items per list: a bound, so a misbehaving API cannot loop forever
# Closing keywords of GitHub (docs.github.com/en/issues/tracking-your-work-with-issues/linking-a-pull-request-to-an-issue)
# plus `Refs`, used by the harness for a partial PR (CONVENTIONS.md §Pull requests)
LINK_RE = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?|refs?)\b:?\s+#(\d+)", re.I)


class FetchError(Exception):
    """The API could not be read (network, HTTP error, invalid JSON): nothing is written."""


def github(token):
    """HTTP function `http(path) -> JSON` on the GitHub REST API (the tests inject their own)."""
    def http(path):
        req = urllib.request.Request(API + path, headers={"Authorization": f"Bearer {token}",
                                                          "Accept": "application/vnd.github+json",
                                                          "X-GitHub-Api-Version": "2022-11-28",
                                                          "User-Agent": "belayline-readme-progress"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read() or b"null")
        except urllib.error.HTTPError as e:
            raise FetchError(f"GET {path}: HTTP {e.code} {e.read().decode(errors='replace')[:300]}") from None
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise FetchError(f"GET {path}: {e}") from None
    return http


def paged(http, path):
    """Every item of a paginated list (`per_page` already in `path`)."""
    items = []
    for page in range(1, MAX_PAGES + 1):
        batch = http(f"{path}&page={page}")
        if not isinstance(batch, list):
            raise FetchError(f"GET {path}: a list was expected")
        items += batch
        if len(batch) < PER_PAGE:
            break
    return items


def _labels(item):
    return [lb["name"] if isinstance(lb, dict) else lb for lb in item.get("labels", [])]


def _statuses(item):
    return [lb for lb in _labels(item) if lb.startswith(STATUS_PREFIX)]


def lot_row(epic, subs, pulls):
    """Row of one lot (pure function): {issue, title, url, state, done, total, pulls}."""
    numbers = {epic["number"]} | {s["number"] for s in subs}
    linked = [p for p in pulls if p.get("state") == "open" or p.get("merged_at")]
    linked = [p for p in linked if numbers & {int(n) for n in LINK_RE.findall(p.get("body") or "")}]
    linked.sort(key=lambda p: p["number"])
    done = sum(1 for s in subs if s["state"] == "closed")
    row = {"issue": epic["number"], "title": epic["title"], "url": epic["html_url"], "done": done, "total": len(subs),
           "pulls": [(p["number"], p["html_url"]) for p in linked]}
    if not subs:
        row["state"] = "⚠ no sub-issue"
        return row
    open_items = [i for i in [epic, *subs] if i["state"] == "open"]
    warnings, statuses = [], set()
    for item in open_items:
        found = _statuses(item)
        if len(found) == 1:
            statuses.add(found[0])
        else:   # zero or several: shown as such, never used to pick a state
            warnings.append(f"#{item['number']}: " + ("no status label" if not found else f"{len(found)} status labels"))
    if done == len(subs):
        state = "🟢 shipped"
    elif any(p["state"] == "open" and not p.get("draft") for p in linked):
        state = "🟠 in review"
    elif CLAIMED in statuses:
        state = "🔵 in progress"
    elif statuses & set(BLOCKED):
        state = "🔴 blocked"
    else:
        state = "⚪ to do"
    row["state"] = state + (" ⚠ " + "; ".join(warnings) if warnings and state != "🟢 shipped" else "")
    return row


def milestone_row(m):
    done, total = m["closed_issues"], m["closed_issues"] + m["open_issues"]
    if total == 0:
        state = "⚠ no issue"
    elif m["state"] == "closed" or done == total:
        state = "🟢 shipped"
    elif done:
        state = "🔵 in progress"
    else:
        state = "⚪ to do"
    return {"issue": m["number"], "title": m["title"], "url": m["html_url"], "state": state, "done": done,
            "total": total, "pulls": []}


def collect(repo, http):
    """(kind, rows): one row per epic ("lot"), otherwise one per milestone ("milestone"). Raises FetchError."""
    label = urllib.parse.quote(EPIC_LABEL)
    epics = [i for i in paged(http, f"/repos/{repo}/issues?labels={label}&state=all&per_page={PER_PAGE}")
             if "pull_request" not in i]
    if not epics:
        milestones = paged(http, f"/repos/{repo}/milestones?state=all&sort=due_on&direction=asc&per_page={PER_PAGE}")
        return "milestone", [milestone_row(m) for m in milestones]
    pulls = paged(http, f"/repos/{repo}/pulls?state=all&per_page={PER_PAGE}")
    rows = []
    for epic in sorted(epics, key=lambda i: i["number"]):
        subs = paged(http, f"/repos/{repo}/issues/{epic['number']}/sub_issues?per_page={PER_PAGE}")
        rows.append(lot_row(epic, subs, pulls))
    return "lot", rows


def _cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def render(rows, kind):
    """Markdown table: kind "lot" or "milestone"."""
    if kind == "lot":
        lines = ["| Lot | State | Done | Issue / PR |", "|---|---|---|---|"]
        for r in rows:
            links = [f"[#{r['issue']}]({r['url']})"] + [f"[#{n}]({url})" for n, url in r["pulls"]]
            lines.append(f"| {_cell(r['title'])} | {r['state']} | {r['done']}/{r['total']} | {' · '.join(links)} |")
    else:
        lines = ["| Milestone | State | Closed | Link |", "|---|---|---|---|"]
        lines += [f"| {_cell(r['title'])} | {r['state']} | {r['done']}/{r['total']} | [milestone]({r['url']}) |"
                  for r in rows]
        if not rows:
            lines.append("| ⚠ no `type: epic` issue and no milestone | | | |")
    return "\n".join(lines) + "\n"


def block_bounds(text):
    """(start, end) of the text between the markers, or None."""
    start = text.find(BEGIN)
    end = text.find(END, start + len(BEGIN)) if start >= 0 else -1
    return (start + len(BEGIN), end) if start >= 0 and end >= 0 else None


def run(argv=None, http=None, env=None, out=sys.stdout):
    env = os.environ if env is None else env
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=env.get("GITHUB_REPOSITORY"))
    ap.add_argument("--readme", default="README.md")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    fail = "⚠ could not check" if a.check else f"✘ {a.readme} unchanged"

    def say(line):
        print(line, file=out)

    try:
        with open(a.readme, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        say(f"{fail}: {e}")
        return 2
    bounds = block_bounds(text)
    if bounds is None:
        say(f"{fail}: markers {BEGIN} … {END} missing; add them where the table goes (README-STANDARD.md §3)")
        return 2
    token = env.get("GH_TOKEN") or env.get("GITHUB_TOKEN")
    if not token:
        say(f"{fail}: no token (GH_TOKEN or GITHUB_TOKEN, read access to issues and pull requests)")
        return 2
    if not a.repo:
        say(f"{fail}: no repository (--repo owner/name or GITHUB_REPOSITORY)")
        return 2
    try:
        kind, rows = collect(a.repo, http or github(token))
    except FetchError as e:
        say(f"{fail}: {e}")
        return 2
    new = "\n" + render(rows, kind)
    old = text[bounds[0]:bounds[1]]
    if old == new:
        say(f"🟢 progress block of {a.readme} up to date ({len(rows)} rows)")
        return 0
    if a.check:
        say(f"🟠 progress block of {a.readme} differs from the issues; run readme-progress.py to rewrite it:")
        out.writelines(difflib.unified_diff(old.splitlines(True), new.splitlines(True), "committed", "generated"))
        return 1
    with open(a.readme, "w", encoding="utf-8") as f:
        f.write(text[:bounds[0]] + new + text[bounds[1]:])
    say(f"🟢 progress block of {a.readme} rewritten ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(run())

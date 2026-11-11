#!/usr/bin/env python3
"""Bring the `status:` labels back in line with the facts, without any workflow (METHODOLOGY.md §4).

Read from the GitHub API, never guessed. Dry run by default: prints the changes; `--apply` performs them and lists
each one applied. Rules, per issue:
  closed                         carries no `status:` label → every one removed
  open, an open PR that closes or refs it, or a live `/claim`   → `status: claimed`
                                 (from `needs-triage`, `ready`, no status; a `type: epic` umbrella is not claimed by a
                                 PR that refs it: lot PRs ref their umbrella)
  `status: blocked`, every blocker cited in `### Blocked by` (`#n`) closed → "unblockable", → `status: ready`
                                 (or `claimed` when a PR or a live claim exists); a free-text blocker is never decided
Reported, never changed ("check" lines):
  `status: claimed` with no open PR, no live claim and no activity for more than 24 h (stale);
  a live claim older than 24 h with no open PR; an open issue with zero or several `status:` labels, or without
  exactly one `type:` label; a `status: blocked` issue that names no blocker.
Never moved: `status: needs-decision` (a human's) and `status: on-hold` (held by a decision).
A claim: a comment whose first line is `/claim <id>`; `/release` or `/release <id>` hands it back; comments replay in
order, the first claim wins, only repository members' comments count (CONVENTIONS.md §GitHub comments). A PR is
linked as in readme-progress.py (Closes/Fixes/Resolves/Refs #n in its body).

Usage: issue-reconcile.py [--repo owner/name] [--apply]
Exit codes: 0 nothing to change (or every change applied); 1 changes to apply (dry run); 2 nothing done or stopped:
no token, no network, API error (with --apply, the changes applied before the error are listed).
The last line is a summary with the count per status after the changes, for the orchestrator's state.
Token: GH_TOKEN (or GITHUB_TOKEN); read access to issues and pull requests, write access to issues for --apply.
API (REST, 2022-11-28): GET /repos/{o}/{r}/issues?state=all (issues and PRs, one listing), the comments
(/issues/comments for the repository, or /issues/{n}/comments when cheaper), POST and DELETE /issues/{n}/labels
(docs.github.com/en/rest/issues/issues, /rest/issues/comments, /rest/issues/labels). Cost of a dry run:
ceil(issues and PRs / 100) + comment pages; each change adds one or two calls. Standard library only.
"""
import argparse
import datetime
import importlib.util
import json
import math
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

# API conventions, PR links and pagination come from the sibling readme-progress.py (vendored next to this one)
_spec = importlib.util.spec_from_file_location("readme_progress", pathlib.Path(__file__).with_name("readme-progress.py"))
_rp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rp)
API, PER_PAGE, LINK_RE, FetchError, paged, labels_of = (_rp.API, _rp.PER_PAGE, _rp.LINK_RE, _rp.FetchError,
                                                        _rp.paged, _rp._labels)

STATUS_PREFIX, TYPE_PREFIX = "status: ", "type: "
TRIAGE, READY, CLAIMED, BLOCKED = "status: needs-triage", "status: ready", "status: claimed", "status: blocked"
ON_HOLD, DECISION = "status: on-hold", "status: needs-decision"
STATUSES = (TRIAGE, READY, CLAIMED, BLOCKED, ON_HOLD, DECISION)
EPIC = "type: epic"
EXEMPT = ("dependencies",)                        # as issue-hygiene.yml (`exempt-labels`)
MEMBERS = ("OWNER", "MEMBER", "COLLABORATOR")
STALE = datetime.timedelta(hours=24)
CLAIM_RE = re.compile(r"/claim[ \t]+(\S+)")
RELEASE_RE = re.compile(r"/release(?:[ \t]+(\S+))?[ \t]*")
REF_RE = re.compile(r"(?<![\w/])#(\d+)\b")       # `#n` of this repository, not `owner/repo#n`

# Same parser as issue-hygiene.yml, between `// begin blocker` and `// end blocker` (a test feeds both the same bodies)
BLOCKED_BY_RE = re.compile(r"^#{2,4}[ \t]*Blocked by[ \t]*\r?\n([\s\S]*?)(?=^#{1,6}[ \t]|(?![\s\S]))", re.I | re.M)
EMPTY_RE = re.compile(r"none|n/a|tbd|-|_no response_", re.I)


def blocker_of(body):
    """The `### Blocked by` lines (bullets stripped, joined by \\n), or None when absent or empty."""
    m = BLOCKED_BY_RE.search(body or "")
    if not m:
        return None
    lines = [re.sub(r"^\s*[-*][ \t]+", "", x).strip() for x in re.split(r"\r?\n", m.group(1))]
    lines = [x for x in lines if x and not EMPTY_RE.fullmatch(x)]
    return "\n".join(lines) or None


def github(token):
    """HTTP function `http(path, method="GET", data=None) -> JSON` on the REST API (the tests inject their own)."""
    def http(path, method="GET", data=None):
        body = None if data is None else json.dumps(data).encode()
        req = urllib.request.Request(API + path, data=body, method=method,
                                     headers={"Authorization": f"Bearer {token}",
                                              "Accept": "application/vnd.github+json",
                                              "X-GitHub-Api-Version": "2022-11-28",
                                              "User-Agent": "belayline-issue-reconcile"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read() or b"null")
        except urllib.error.HTTPError as e:
            raise FetchError(f"{method} {path}: HTTP {e.code} {e.read().decode(errors='replace')[:300]}") from None
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise FetchError(f"{method} {path}: {e}") from None
    return http


def _is_pr(item):
    return "pull_request" in item


def comment_paths(repo, items):
    """Comment listings to read: the repository's (one listing) or the open issues' ones, whichever costs less."""
    total = sum(i.get("comments") or 0 for i in items)
    if not total:
        return []
    wanted = [i for i in items if not _is_pr(i) and i.get("state") == "open" and (i.get("comments") or 0) > 0]
    per_issue = sum(math.ceil(i["comments"] / PER_PAGE) for i in wanted)
    if per_issue < math.ceil(total / PER_PAGE):
        return [f"/repos/{repo}/issues/{i['number']}/comments?per_page={PER_PAGE}" for i in wanted]
    return [f"/repos/{repo}/issues/comments?sort=created&direction=asc&per_page={PER_PAGE}"]


def collect(repo, http):
    """(items, comments by issue number, GET count). Raises FetchError."""
    calls = 0

    def counted(path, method="GET", data=None):
        nonlocal calls
        calls += 1
        return http(path)
    items = paged(counted, f"/repos/{repo}/issues?state=all&per_page={PER_PAGE}")
    comments = {}
    for path in comment_paths(repo, items):
        for c in paged(counted, path):
            n = str(c.get("issue_url") or "").rsplit("/", 1)[-1]
            if n.isdigit():
                comments.setdefault(int(n), []).append(c)
    for cs in comments.values():
        cs.sort(key=lambda c: c.get("created_at") or "")
    return items, comments, calls


def live_claim(comments):
    """(id, created_at) of the claim that holds after replaying the members' comments in order, or None."""
    holder = None
    for c in comments:
        if c.get("author_association") not in MEMBERS:
            continue
        first = (c.get("body") or "").strip().splitlines()[:1]
        first = first[0].strip() if first else ""
        claim, release = CLAIM_RE.fullmatch(first), RELEASE_RE.fullmatch(first)
        if claim and holder is None:
            holder = (claim.group(1), c.get("created_at") or "")
        elif release and holder and release.group(1) in (None, holder[0]):
            holder = None
    return holder


def _time(text):
    try:
        return datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def _old(text, now):
    t = _time(text)
    return t is not None and now - t > STALE


def _q(label):
    return f"`{label}`"


def plan(items, comments, now):
    """(changes, checks, counts) — pure function. A change: {issue, add, remove, reason}; a check: (issue, text)."""
    by_number = {i["number"]: i for i in items}
    open_prs = [p for p in items if _is_pr(p) and p.get("state") == "open"]
    changes, checks, counts = [], [], {s: 0 for s in STATUSES}
    counts.update({"none": 0, "several": 0})
    open_issues = 0
    for issue in sorted((i for i in items if not _is_pr(i)), key=lambda i: i["number"]):
        n, names = issue["number"], labels_of(issue)
        statuses = [x for x in names if x.startswith(STATUS_PREFIX)]
        if issue.get("state") != "open":
            if statuses:
                changes.append({"issue": n, "add": None, "remove": statuses, "reason": "closed issue"})
            continue
        open_issues += 1
        prs = sorted(p["number"] for p in open_prs if n in {int(x) for x in LINK_RE.findall(p.get("body") or "")})
        if EPIC in names:
            prs = []
        claim = live_claim(comments.get(n, []))
        evidence = ", ".join([f"open PR #{x}" for x in prs] + ([f"live claim {claim[0]}"] if claim else []))
        target = statuses[0] if len(statuses) == 1 else None
        reason = None
        if len(statuses) > 1:
            checks.append((n, f"{len(statuses)} `status:` labels ({', '.join(statuses)}): not decided, keep one"))
        elif target in (DECISION, ON_HOLD):
            pass                                                   # a decision: never moved
        elif target == BLOCKED:
            blocker = blocker_of(issue.get("body"))
            if blocker is None:
                checks.append((n, f"{_q(BLOCKED)} names no blocker (`### Blocked by` section)"))
            else:
                lines = blocker.splitlines()
                refs = [[int(x) for x in REF_RE.findall(line)] for line in lines]
                cited = sorted({x for r in refs for x in r})
                if all(refs) and all(by_number.get(x, {}).get("state") == "closed" for x in cited):
                    target = CLAIMED if evidence else READY
                    reason = "unblockable: every cited blocker is closed (" + ", ".join(f"#{x}" for x in cited) + ")"
                    reason += f"; {evidence}" if evidence else ""
        elif evidence and target != CLAIMED:
            target, reason = CLAIMED, evidence
        if target is None and not statuses:
            checks.append((n, "no `status:` label"))
        if target == CLAIMED and not prs and claim is None and _old(issue.get("updated_at"), now):
            checks.append((n, f"{_q(CLAIMED)} with no open PR, no live claim and no activity for more than 24 h: "
                              "stale (ask the claimant, then `/release`)"))
        if claim and not prs and _old(claim[1], now) and len(statuses) <= 1 and target not in (DECISION, ON_HOLD):
            checks.append((n, f"claim by {claim[0]} older than 24 h, no open PR"))
        if not any(x in EXEMPT for x in names):
            types = [x for x in names if x.startswith(TYPE_PREFIX)]
            if len(types) != 1:
                checks.append((n, "no `type:` label" if not types else f"{len(types)} `type:` labels ({', '.join(types)})"))
        if reason and target is not None and (not statuses or target != statuses[0]):
            changes.append({"issue": n, "add": target, "remove": statuses, "reason": reason})
        if len(statuses) > 1:
            counts["several"] += 1
        elif target is None:
            counts["none"] += 1
        else:
            counts[target] = counts.get(target, 0) + 1
    counts["open"] = open_issues
    return changes, checks, counts


def describe(change):
    n, add, remove = change["issue"], change["add"], change["remove"]
    if add is None:
        what = "remove " + ", ".join(_q(x) for x in remove)
    elif remove:
        what = f"{', '.join(_q(x) for x in remove)} → {_q(add)}"
    else:
        what = f"add {_q(add)}"
    return f"#{n} {what} ({change['reason']})"


def apply(repo, http, change):
    """Add the new status first, then remove the old ones: the issue is never left without a status."""
    n = change["issue"]
    if change["add"]:
        http(f"/repos/{repo}/issues/{n}/labels", "POST", {"labels": [change["add"]]})
    for name in change["remove"]:
        http(f"/repos/{repo}/issues/{n}/labels/{urllib.parse.quote(name, safe='')}", "DELETE")


def summary(counts, changes, checks, calls):
    parts = [f"{counts['open']} open issues"] + [f"{s.removeprefix(STATUS_PREFIX)} {counts[s]}" for s in STATUSES]
    parts += [f"no status {counts['none']}", f"several {counts['several']}", f"changes {len(changes)}",
              f"to check {len(checks)}", f"API calls: {calls}"]
    return "summary: " + " · ".join(parts)


def run(argv=None, http=None, env=None, out=sys.stdout, now=None):
    env = os.environ if env is None else env
    now = now or datetime.datetime.now(datetime.timezone.utc)
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=env.get("GITHUB_REPOSITORY"))
    ap.add_argument("--apply", action="store_true", help="perform the changes (default: dry run)")
    a = ap.parse_args(argv)

    def say(line):
        print(line, file=out)

    token = env.get("GH_TOKEN") or env.get("GITHUB_TOKEN")
    if not token:
        say("✘ nothing changed: no token (GH_TOKEN or GITHUB_TOKEN, read access to issues and pull requests)")
        return 2
    if not a.repo:
        say("✘ nothing changed: no repository (--repo owner/name or GITHUB_REPOSITORY)")
        return 2
    http = http or github(token)
    try:
        items, comments, calls = collect(a.repo, http)
    except FetchError as e:
        say(f"✘ nothing changed: {e}")
        return 2
    changes, checks, counts = plan(items, comments, now)
    for c in changes:
        say(f"change {describe(c)}")
    for n, text in checks:
        say(f"check #{n} {text}")
    code = 0
    if changes and not a.apply:
        say(f"{len(changes)} change(s) not applied (dry run): run again with --apply")
        code = 1
    elif changes:
        for i, c in enumerate(changes):
            try:
                apply(a.repo, http, c)
            except FetchError as e:
                say(f"✘ stopped: {e}; applied {i} of {len(changes)} change(s), the rest is unchanged")
                return 2
            calls += (1 if c["add"] else 0) + len(c["remove"])
            say(f"applied {describe(c)}")
    else:
        say("🟢 nothing to change")
    say(summary(counts, changes, checks, calls))
    return code


if __name__ == "__main__":
    sys.exit(run())

#!/usr/bin/env python3
"""Orchestrator State: rewrites ONE comment of the memory issue from the facts (ORCHESTRATION.md §8).

The State is the only thing a resuming session must read; the rest of the memory issue is a log. The comment is the
one whose first line is MARKER; the script creates it on the first run, then rewrites it in place. Sections:
  Rules in force   a pointer: the harness rules, then `docs/DECISIONS.md` and the scope keys of its rows `in force`
                   (never the text of a rule; read with decisions-check.py, vendored next to this script)
  Open PRs         stage and head sha: draft · CI red · waiting for CI · waiting for review · waiting for merge
                   (approved on the head: the latest adversarial verdict is APPROVED and names that sha, parsed
                   by flow-metrics.py's `verdict_matches` and `HEAD_RE`, vendored next to this script, as
                   merge-gate.py and the dashboard do);
                   link to the report (a PR comment carrying `<!-- harness:report -->`). The merge gate decides.
  Children         who holds what. Source, and the only one: `/claim <id>` comments on open issues labelled
                   `status: claimed` (replayed: members only, first claim wins, `/release` hands it back) and the
                   `Claim: <id>` lines of open PRs. Not known here: whether a session is alive, its link, its last
                   activity (the orchestrator's session tools know).
  Decisions waiting  open issues labelled `status: needs-decision`, age since that label was set
  Status counts    open issues per `status:` label
Carries its write time and the script version. A section with nothing in it says "none recorded"; one that could not
be read stops the write, so nothing stale or partial is published. Size bound: MAX_ITEMS lines per list, MAX_CHARS
for the whole State (fewer lines per list until it fits); the oldest lines are replaced by a link to the full list.
Text from GitHub is written with `@` defused, so the State never mentions a person or a bot.

Hand edits: the comment carries the SHA-256 of what the script wrote; a comment that no longer matches is not
overwritten (the difference is printed) unless --force.

Usage: orch-state.py [--issue N] [--repo owner/name] [--root .] [--decisions docs/DECISIONS.md] [--print] [--force]
  --issue  memory issue (default: `.harness/config.json` › `orchestration.memory_issue`)
  --print  writes nothing, prints the comment it would write
Exit codes: 0 written (or printed with --print); 1 refused: the State was edited by hand; 2 not written: no token,
no repository, no memory issue, network or API error (the State is printed so the session can still work).
Token: GH_TOKEN (or GITHUB_TOKEN): read issues, pull requests, checks and statuses; write issue comments.
API (REST, 2022-11-28): GET /repos/{o}/{r}/issues, /pulls, /issues/{n}/comments, /issues/{n}/events,
/pulls/{n}/reviews, /commits/{sha}/check-runs, /commits/{sha}/status; POST /issues/{n}/comments, PATCH
/issues/comments/{id} (docs.github.com/en/rest/issues/comments, /rest/issues/events, /rest/pulls,
/rest/checks/runs, /rest/commits/statuses). Standard library only.
"""
import argparse
import datetime
import difflib
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

VERSION = "1"
API = "https://api.github.com"
MARKER = "<!-- harness:state -->"
REPORT_MARKER = "<!-- harness:report -->"   # same marker as merge-gate.py's report
HASH_RE = re.compile(r"^<!-- harness:state-sha256 ([0-9a-f]{64}) -->$")
PER_PAGE = 100
MAX_PAGES = 50    # a bound, so a misbehaving API cannot loop forever
MAX_ITEMS = 20    # lines per list before the oldest are linked
MAX_CHARS = 6000  # the whole State: about 1.5 k tokens to read when resuming
TITLE_CHARS = 60
STATUS_PREFIX = "status: "
CLAIMED, NEEDS_DECISION = "status: claimed", "status: needs-decision"
MEMBERS = {"OWNER", "MEMBER", "COLLABORATOR"}   # only their claims count (CONVENTIONS.md §GitHub comments)
CI_OK = ("success", "neutral", "skipped")
STAGES = ("waiting for merge", "waiting for review", "waiting for CI", "CI red", "draft")
CLAIM_RE = re.compile(r"^/claim[ \t]+(\S+)")
RELEASE_RE = re.compile(r"^/release(?:[ \t]+(\S+))?[ \t]*$")
CLAIM_LINE_RE = re.compile(r"^Claim:[ \t]*(\S+)", re.M)


def _load_flow():
    """flow-metrics.py, vendored in the same folder: the single parser of verdict lines (as in merge-gate.py)."""
    path = pathlib.Path(__file__).resolve().with_name("flow-metrics.py")
    spec = importlib.util.spec_from_file_location("flow_metrics_shared", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


flow = _load_flow()


class FetchError(Exception):
    """The API could not be read or written (network, HTTP error, invalid JSON): nothing is written."""


def github(token):
    """HTTP function `http(path, method="GET", payload=None) -> JSON` (the tests inject their own)."""
    def http(path, method="GET", payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(API + path, data=data, method=method, headers={
            "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "belayline-orch-state"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read() or b"null")
        except urllib.error.HTTPError as e:
            raise FetchError(f"{method} {path}: HTTP {e.code} {e.read().decode(errors='replace')[:300]}") from None
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise FetchError(f"{method} {path}: {e}") from None
    return http


def paged(http, path, key=None):
    """Every item of a paginated list (`per_page` already in `path`); `key` for an object such as check runs."""
    items = []
    for page in range(1, MAX_PAGES + 1):
        batch = http(f"{path}&page={page}")
        if key is not None:
            batch = batch.get(key) if isinstance(batch, dict) else None
        if not isinstance(batch, list):
            raise FetchError(f"GET {path}: a list was expected")
        items += batch
        if len(batch) < PER_PAGE:
            break
    return items


def _labels(item):
    return [lb["name"] if isinstance(lb, dict) else lb for lb in item.get("labels", [])]


def _first_line(body):
    text = (body or "").strip()
    return text.splitlines()[0].strip() if text else ""


def claim_holder(comments):
    """(id, since) of the active claim after replaying the comments in order, or None."""
    holder = None
    for c in comments:
        if c.get("author_association") not in MEMBERS:
            continue
        line = _first_line(c.get("body"))
        claim, release = CLAIM_RE.match(line), RELEASE_RE.match(line)
        if claim and holder is None:
            holder = (claim.group(1), c.get("created_at") or "")
        elif release and holder and release.group(1) in (None, holder[0]):
            holder = None
    return holder


def ci_state(runs, combined):
    """green, red, pending or none, from the check runs and the combined commit status of one sha."""
    red = pending = False
    for r in runs:
        if r.get("status") != "completed":
            pending = True
        elif r.get("conclusion") not in CI_OK:
            red = True
    statuses = (combined or {}).get("statuses") or []
    if statuses:   # with no status at all, the combined state is "pending": not a signal
        state = combined.get("state")
        red = red or state in ("failure", "error")
        pending = pending or state == "pending"
    return "red" if red else "pending" if pending else "green" if runs or statuses else "none"


def approved_on(head, reviews, comments):
    """True when the latest adversarial verdict (reviews and comments, by time) is APPROVED and names `head`.

    Same reading as merge-gate.py's approval line: verdict lines through flow.verdict_matches, the sha through
    flow.HEAD_RE; a GitHub approval without a harness verdict line does not count.
    """
    items = [(r.get("body") or "", r["submitted_at"]) for r in reviews if r.get("submitted_at")]
    items += [(c.get("body") or "", c.get("created_at") or "") for c in comments]
    verdicts = []
    for body, at in items:
        for m in flow.verdict_matches(body):
            if m.group(1) == "Adversarial":
                named = flow.HEAD_RE.search(m.string[m.end():])
                verdicts.append((at, m.group(2), named.group(1).lower() if named else None))
    if not verdicts:
        return False
    _, verdict, named = sorted(verdicts, key=lambda v: v[0])[-1]
    return verdict == "APPROVED" and bool(named) and head.lower().startswith(named)


def pull_facts(repo, http, p):
    head = (p.get("head") or {}).get("sha") or ""
    fact = {"number": p["number"], "title": p.get("title", ""), "url": p.get("html_url", ""), "head": head,
            "created": p.get("created_at") or "", "ci": None, "report": None,
            "claims": CLAIM_LINE_RE.findall((p.get("body") or "").replace("\r", ""))}
    if p.get("draft"):
        fact["stage"] = "draft"
        return fact
    runs = paged(http, f"/repos/{repo}/commits/{head}/check-runs?per_page={PER_PAGE}", key="check_runs")
    combined = http(f"/repos/{repo}/commits/{head}/status")
    reviews = paged(http, f"/repos/{repo}/pulls/{p['number']}/reviews?per_page={PER_PAGE}")
    comments = paged(http, f"/repos/{repo}/issues/{p['number']}/comments?per_page={PER_PAGE}")
    reports = [c for c in comments if REPORT_MARKER in (c.get("body") or "")]
    fact["report"] = reports[-1].get("html_url") if reports else None
    fact["ci"] = ci_state(runs, combined if isinstance(combined, dict) else {})
    if fact["ci"] == "red":
        fact["stage"] = "CI red"
    elif fact["ci"] == "pending":
        fact["stage"] = "waiting for CI"
    elif approved_on(head, reviews, comments):
        fact["stage"] = "waiting for merge"
    else:
        fact["stage"] = "waiting for review"
    return fact


def collect(repo, http):
    """The facts of the State, read from GitHub. Raises FetchError."""
    issues = [i for i in paged(http, f"/repos/{repo}/issues?state=open&per_page={PER_PAGE}")
              if "pull_request" not in i]
    pulls = [pull_facts(repo, http, p) for p in paged(http, f"/repos/{repo}/pulls?state=open&per_page={PER_PAGE}")]

    holders = {}
    for issue in issues:
        if CLAIMED not in _labels(issue):
            continue
        held = claim_holder(paged(http, f"/repos/{repo}/issues/{issue['number']}/comments?per_page={PER_PAGE}"))
        if held:
            h = holders.setdefault(held[0], {"id": held[0], "issues": [], "pulls": [], "latest": ""})
            h["issues"].append((issue["number"], issue.get("title", ""), held[1]))
            h["latest"] = max(h["latest"], held[1])
    for p in pulls:
        for cid in p["claims"]:
            h = holders.setdefault(cid, {"id": cid, "issues": [], "pulls": [], "latest": ""})
            h["pulls"].append(p)
            h["latest"] = max(h["latest"], p["created"])

    waiting = []
    for issue in issues:
        if NEEDS_DECISION not in _labels(issue):
            continue
        events = paged(http, f"/repos/{repo}/issues/{issue['number']}/events?per_page={PER_PAGE}")
        set_at = [e.get("created_at") or "" for e in events
                  if e.get("event") == "labeled" and (e.get("label") or {}).get("name") == NEEDS_DECISION]
        waiting.append({"number": issue["number"], "title": issue.get("title", ""), "url": issue.get("html_url", ""),
                        "since": set_at[-1] if set_at else issue.get("created_at") or ""})

    counts = {}
    for issue in issues:
        statuses = [lb for lb in _labels(issue) if lb.startswith(STATUS_PREFIX)] or ["no status"]
        for s in statuses:
            counts[s] = counts.get(s, 0) + 1
    return {"pulls": pulls, "holders": list(holders.values()), "waiting": waiting, "counts": counts}


def rules_in_force(path):
    """(scope keys in force, None) / (None, "absent") / (None, reason) for the decisions file."""
    if not path.is_file():
        return None, "absent"
    module = pathlib.Path(__file__).resolve().with_name("decisions-check.py")
    try:
        spec = importlib.util.spec_from_file_location("decisions_check_shared", module)
        dc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dc)
        rows = dc.table_rows(path.read_text(encoding="utf-8"))
    except (OSError, ImportError, SyntaxError, AttributeError) as e:
        return None, f"unreadable ({e.__class__.__name__}: needs decisions-check.py next to this script)"
    keys = []
    for _, cells in rows:
        if len(cells) >= 5 and cells[4].strip().lower() == "in force" and cells[1] and cells[1] not in keys:
            keys.append(cells[1])
    return keys, None


# ---------------------------------------------------------------- rendering

def _text(value, limit=None):
    """One line, `@` defused (no mention of a person or a bot), cut to `limit` characters."""
    text = " ".join(str(value).split())
    if limit and len(text) > limit:
        text = text[:limit - 1] + "…"
    return text.replace("@", "@\u200b")  # zero-width space: GitHub sees no mention


def _days(since, now):
    try:
        then = datetime.datetime.fromisoformat(since.replace("Z", "+00:00"))
    except ValueError:
        return "since an unknown date"
    days = (now - then).days
    return "less than a day" if days < 1 else f"{days} day" + ("s" if days != 1 else "")


def _bounded(lines, cap, link, what):
    """The newest `cap` lines (lines are newest first), the older ones replaced by one link."""
    if not lines:
        return ["none recorded"]
    shown = lines[:cap]
    if len(lines) > len(shown):
        shown.append(f"- … and {len(lines) - len(shown)} older: [{what}]({link})")
    return shown


def _pull_line(p):
    parts = [p["stage"], f"head `{p['head'][:7]}`"]
    if p["ci"] and p["ci"] != "red":
        parts.append(f"CI {p['ci']}")
    if p["stage"] == "waiting for merge":
        parts.append("approved on head")
    if p["report"]:
        parts.append(f"[report]({p['report']})")
    return f"- #{p['number']} [{_text(p['title'], TITLE_CHARS)}]({p['url']}) — " + " · ".join(parts)


def _holder_line(h):
    held = [f"#{n} {_text(t, TITLE_CHARS)} (since {since[:10]})" for n, t, since in h["issues"]]
    line = f"- `{_text(h['id'])}`" + (" holds " + ", ".join(held) if held else "")
    for p in h["pulls"]:
        line += f" · PR #{p['number']} {p['stage']}"
    return line


def _render(repo, rules, facts, reason, now, cap, decisions_name):
    web = f"https://github.com/{repo}" if repo else ""
    out = [
        "## State", "",
        f"_Written {now.strftime('%Y-%m-%d %H:%M')} UTC by orch-state.py {VERSION}. The only comment to read when "
        "resuming; rewritten by the script, hand edits are refused. The rest of this thread is a log._", "",
        "### Rules in force", "",
    ]
    keys, problem = rules
    where = f"[`{decisions_name}`]({web}/blob/HEAD/{decisions_name})" if web else f"`{decisions_name}`"
    if problem == "absent":
        decisions = f"no `{decisions_name}` (no standing decision recorded)"
    elif problem:
        decisions = f"{where}: {problem}"
    else:
        decisions = f"{where}, in force: " + (", ".join(f"`{_text(k)}`" for k in keys) or "none recorded")
    out += ["Harness rules: `.harness/docs/ESSENTIALS.md`, then the project's `AGENTS.md` / `CLAUDE.md`. "
            f"Operator decisions: {decisions}.", ""]

    def section(title, lines):
        out.extend([f"### {title}", "", *lines, ""])

    if facts is None:
        missing = [f"unavailable: {_text(reason)}"]
        for title in ("Open PRs", "Children (claims)", "Decisions waiting for the operator",
                      "Status counts (open issues)"):
            section(title, missing)
        return "\n".join(out)

    newest = sorted(facts["pulls"], key=lambda p: -p["number"])
    shown = sorted(newest[:cap], key=lambda p: (STAGES.index(p["stage"]), -p["number"]))
    pull_lines = [_pull_line(p) for p in shown] + [_pull_line(p) for p in newest[cap:]]
    section("Open PRs", _bounded(pull_lines, cap, f"{web}/pulls?q=is%3Apr+is%3Aopen", "open PRs"))

    holders = sorted(facts["holders"], key=lambda h: h["latest"], reverse=True)
    lines = _bounded([_holder_line(h) for h in holders], cap,
                     f"{web}/issues?q=is%3Aopen+label%3A%22status%3A+claimed%22", "claimed issues")
    section("Children (claims)", lines + ["", "_From `/claim` comments on open `status: claimed` issues and `Claim:` "
                                          "lines of open PRs; whether a session is alive is not known here._"])

    waiting = sorted(facts["waiting"], key=lambda w: w["since"], reverse=True)
    section("Decisions waiting for the operator", _bounded(
        [f"- #{w['number']} [{_text(w['title'], TITLE_CHARS)}]({w['url']}) — waiting {_days(w['since'], now)}"
         for w in waiting], cap, f"{web}/issues?q=is%3Aopen+label%3A%22status%3A+needs-decision%22",
        "needs-decision issues"))

    counts = facts["counts"]
    names = sorted(k for k in counts if k != "no status") + (["no status"] if "no status" in counts else [])
    section("Status counts (open issues)",
            [" · ".join((f"`{_text(k)}` " if k != "no status" else "no status ") + str(counts[k]) for k in names)
             or "none recorded"])
    return "\n".join(out)


def render(repo, rules, facts, reason, now, decisions_name="docs/DECISIONS.md"):
    """The State's Markdown, at most MAX_CHARS: fewer lines per list until it fits."""
    text = ""
    for cap in (MAX_ITEMS, 10, 5, 2, 0):
        text = _render(repo, rules, facts, reason, now, cap, decisions_name)
        if len(text) <= MAX_CHARS:
            return text
    return text[:MAX_CHARS - 40] + "\n\n_… cut at the size limit._"


# ---------------------------------------------------------------- the comment

def _norm(text):
    lines = text.replace("\r\n", "\n").replace("\r", "\n").strip().split("\n")
    return "\n".join(line.rstrip() for line in lines)


def _digest(content):
    return hashlib.sha256(_norm(content).encode("utf-8")).hexdigest()


def comment_body(content):
    """The comment as written: marker, hash of the content, content."""
    return f"{MARKER}\n<!-- harness:state-sha256 {_digest(content)} -->\n{_norm(content)}\n"


def split_body(body):
    """(stored hash or None, content) of a State comment."""
    lines = _norm(body).split("\n")
    if len(lines) > 1:
        m = HASH_RE.match(lines[1].strip())
        if m:
            return m.group(1), "\n".join(lines[2:])
    return None, "\n".join(lines[1:])


def hand_edited(body):
    stored, content = split_body(body)
    return stored is None or stored != _digest(content)


def find_state(comments):
    return next((c for c in comments if (c.get("body") or "").lstrip().startswith(MARKER)), None)


def run(argv=None, http=None, env=None, out=sys.stdout, now=None):
    env = os.environ if env is None else env
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--issue", type=int, help="memory issue (default: .harness/config.json › orchestration.memory_issue)")
    ap.add_argument("--repo", default=env.get("GITHUB_REPOSITORY"))
    ap.add_argument("--root", default=".", help="repository checkout (default: current folder)")
    ap.add_argument("--decisions", default="docs/DECISIONS.md", help="decisions file, relative to the root")
    ap.add_argument("--print", action="store_true", help="write nothing, print the comment")
    ap.add_argument("--force", action="store_true", help="overwrite a State edited by hand")
    a = ap.parse_args(argv)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    root = pathlib.Path(a.root)

    def say(line):
        print(line, file=out)

    reason, issue = None, a.issue
    config = root / ".harness" / "config.json"
    if issue is None and config.is_file():
        try:
            issue = (json.loads(config.read_text(encoding="utf-8")).get("orchestration") or {}).get("memory_issue")
        except (OSError, ValueError, AttributeError) as e:
            reason = f"unreadable {config}: {e}"
    token = env.get("GH_TOKEN") or env.get("GITHUB_TOKEN")
    facts = None
    if not token:
        reason = reason or "no token (GH_TOKEN or GITHUB_TOKEN)"
    elif not a.repo:
        reason = reason or "no repository (--repo owner/name or GITHUB_REPOSITORY)"
    else:
        try:
            facts = collect(a.repo, http or github(token))
        except FetchError as e:
            reason = reason or str(e)
    content = render(a.repo, rules_in_force(root / a.decisions), facts, reason, now, a.decisions)
    body = comment_body(content)
    if reason is None and not a.print and not isinstance(issue, int):
        reason = "no memory issue (--issue N or .harness/config.json › orchestration.memory_issue)"
    if reason:
        out.write(body)
        say(f"✘ State not written: {reason}")
        return 2
    if a.print:
        out.write(body)
        return 0

    http = http or github(token)
    try:
        existing = find_state(paged(http, f"/repos/{a.repo}/issues/{issue}/comments?per_page={PER_PAGE}"))
        if existing and hand_edited(existing.get("body") or "") and not a.force:
            _, current = split_body(existing.get("body") or "")
            say(f"✘ State not written: comment {existing.get('html_url') or existing.get('id')} was edited by hand "
                "since the script wrote it. Move what matters to an issue or docs/DECISIONS.md, then rerun with "
                "--force. Difference (edited → generated):")
            out.writelines(difflib.unified_diff(current.splitlines(True), _norm(content).splitlines(True),
                                                "edited", "generated"))
            out.write("\n")
            return 1
        if existing:
            written = http(f"/repos/{a.repo}/issues/comments/{existing['id']}", "PATCH", {"body": body})
        else:
            written = http(f"/repos/{a.repo}/issues/{issue}/comments", "POST", {"body": body})
    except FetchError as e:
        out.write(body)
        say(f"✘ State not written: {e}")
        return 2
    say(f"🟢 State written: {(written or {}).get('html_url') or f'issue #{issue}'} ({len(body)} characters)")
    return 0


if __name__ == "__main__":
    sys.exit(run())

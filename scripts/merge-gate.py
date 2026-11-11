#!/usr/bin/env python3
"""Merge gate: says "this PR may be merged now", or exactly why not (CONVENTIONS.md §Pull requests, merge).

Read-only: it never merges. One line per check, `ok`, `missing` or `unchecked` (could not be read):
  PR open · not a draft · mergeable · CI green on the head sha (check runs and commit statuses)
  adversarial review APPROVED naming the head sha (an APPROVED on another sha is a "stale approval")
  no open review thread (a security thread: the operator decides) · no open question in the report
  required labels present · no security label (blocks until the operator decides) · PR body lines
A requirement the project does not have is left out, not failed: no required label, no report with an
`Open questions` section, body lines switched off, no ledger.

Verdict lines are parsed by flow-metrics.py (`verdict_matches`, `HEAD_RE`), vendored next to this script: the
dashboard and the gate read the same format (REVIEW-ROUNDS.md §Traceability), the latest adversarial verdict wins.
The report is the latest PR comment that carries REPORT_MARKER, otherwise the PR body; its `Open questions` section
(a Markdown heading or a bold line) must be empty or say "none".

Usage: merge-gate.py <pr> [--repo owner/name] [--config .harness/config.json]
Exit codes: 0 may merge (the expected head sha is printed: pass it to the merge, e.g.
`gh pr merge <pr> --match-head-commit <sha>` or `sha` in the REST merge call); 1 not ready (a line is missing);
2 could not check (no token, no network, API error, unreadable config, or a line unchecked): never "may merge".
Config (`.harness/config.json` › `merge_gate`, every key optional): `required_labels` (default none),
`security_labels` (default ["type: security"]), `body_lines` (subset of issue, claim, docs; default all three);
`ledger.enabled` adds the `### Ledger` section.
Token: GH_TOKEN (or GITHUB_TOKEN), read access to pull requests, checks, commit statuses and issues.
API (REST, 2022-11-28): GET /repos/{o}/{r}/pulls/{n} (docs.github.com/en/rest/pulls/pulls#get-a-pull-request:
`mergeable` is null while GitHub computes it), /pulls/{n}/reviews (rest/pulls/reviews), /issues/{n}/comments,
/commits/{sha}/check-runs (rest/checks/runs#list-check-runs-for-a-git-reference), /commits/{sha}/status
(rest/commits/statuses#get-the-combined-status-for-a-specific-reference). Review threads: the REST review comments
carry no resolution state, so they are read through GraphQL, POST /graphql, `PullRequest.reviewThreads.isResolved`
(docs.github.com/en/graphql/reference/pulls); if that query fails, the line is `unchecked`. Standard library only.
"""
import argparse
import importlib.util
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
PER_PAGE = 100
MAX_PAGES = 50   # a bound, so a misbehaving API cannot loop forever
EXIT_MAY_MERGE, EXIT_NOT_READY, EXIT_COULD_NOT_CHECK = 0, 1, 2
OK, MISSING, UNCHECKED = "ok", "missing", "unchecked"
# A comment that carries this marker is a report: its `Open questions` section is read (latest one wins)
REPORT_MARKER = "<!-- harness:report -->"
DEFAULTS = {"required_labels": [], "security_labels": ["type: security"], "body_lines": ["issue", "claim", "docs"]}
CI_OK = ("success", "neutral", "skipped")

SECTION_RE = re.compile(r"^(?:#{1,6}[ \t]*|\*\*)Open questions\b[*: \t]*(.*)$", re.I)
SECTION_END_RE = re.compile(r"^(?:#{1,6}\s|\*\*[^*]+\*\*|-{3,}\s*$)")
NONE_RE = re.compile(r"^(?:none|nothing|n/a)\.?$", re.I)
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
ISSUE_LINE_RE = re.compile(r"^(?:(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?|refs?)\b:?\s+#\d+|Direct-PR:[ \t]*\S)",
                           re.I | re.M)
CLAIM_RE = re.compile(r"^Claim:[ \t]*\S", re.M)
DOCS_RE = re.compile(r"^Docs:[ \t]*(\S.*)$", re.M)
DOCS_NONE_RE = re.compile(r"^none\b(?!\s*\(\s*[^)\s])", re.I)
LEDGER_RE = re.compile(r"^###[ \t]+Ledger\b", re.M)
SECURITY_RE = re.compile(r"\bsecurity\b", re.I)

THREADS_QUERY = """query($owner: String!, $name: String!, $number: Int!, $after: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      reviewThreads(first: 100, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes { isResolved isOutdated path comments(first: 1) { nodes { body url } } }
      }
    }
  }
}"""


def _load_flow():
    """flow-metrics.py, vendored in the same folder: the single parser of verdict lines."""
    path = pathlib.Path(__file__).resolve().with_name("flow-metrics.py")
    spec = importlib.util.spec_from_file_location("flow_metrics_shared", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


flow = _load_flow()


class FetchError(Exception):
    """The API could not be read (network, HTTP error, invalid JSON)."""


def github(token):
    """HTTP function `http(path, payload=None) -> JSON` (GET, or POST of `payload`); the tests inject their own."""
    def http(path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(API + path, data=data, headers={
            "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "belayline-merge-gate"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read() or b"null")
        except urllib.error.HTTPError as e:
            raise FetchError(f"{path}: HTTP {e.code} {e.read().decode(errors='replace')[:300]}") from None
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise FetchError(f"{path}: {e}") from None
    return http


def paged(http, path, key=None):
    """Every item of a paginated list (`per_page` already in `path`); `key` for an object such as check runs."""
    items = []
    for page in range(1, MAX_PAGES + 1):
        batch = http(f"{path}&page={page}")
        if key is not None:
            batch = batch.get(key) if isinstance(batch, dict) else None
        if not isinstance(batch, list):
            raise FetchError(f"{path}: a list was expected")
        items += batch
        if len(batch) < PER_PAGE:
            break
    return items


def review_threads(http, repo, number):
    """Every review thread of the PR (GraphQL: REST does not expose whether a thread is resolved)."""
    owner, name = repo.split("/", 1)
    threads, after = [], None
    for _ in range(MAX_PAGES):
        answer = http("/graphql", {"query": THREADS_QUERY,
                                   "variables": {"owner": owner, "name": name, "number": number, "after": after}})
        if not isinstance(answer, dict) or answer.get("errors"):
            raise FetchError(f"/graphql: {(answer or {}).get('errors') if isinstance(answer, dict) else answer}")
        try:
            conn = answer["data"]["repository"]["pullRequest"]["reviewThreads"]
        except (KeyError, TypeError):
            raise FetchError("/graphql: no reviewThreads in the answer") from None
        threads += conn.get("nodes") or []
        info = conn.get("pageInfo") or {}
        if not info.get("hasNextPage"):
            return threads
        after = info.get("endCursor")
    return threads


def _labels(pull):
    return [lb["name"] if isinstance(lb, dict) else lb for lb in pull.get("labels", [])]


def check_ci(http, repo, sha):
    """(state, detail) of CI on `sha`: check runs and commit statuses."""
    red, pending, errors, seen = [], [], [], 0
    try:
        runs = paged(http, f"/repos/{repo}/commits/{sha}/check-runs?per_page={PER_PAGE}", key="check_runs")
        seen += len(runs)
        for r in runs:
            if r.get("status") != "completed":
                pending.append(r.get("name", "?"))
            elif r.get("conclusion") not in CI_OK:
                red.append(f"{r.get('name', '?')} ({r.get('conclusion')})")
    except FetchError as e:
        errors.append(str(e))
    try:
        combined = http(f"/repos/{repo}/commits/{sha}/status")
        statuses = (combined.get("statuses") or []) if isinstance(combined, dict) else []
        seen += len(statuses)
        for s in statuses:
            if s.get("state") in ("failure", "error"):
                red.append(f"{s.get('context', '?')} ({s.get('state')})")
            elif s.get("state") == "pending":
                pending.append(s.get("context", "?"))
    except FetchError as e:
        errors.append(str(e))
    if red or pending:
        parts = ([f"red: {', '.join(red)}"] if red else []) + ([f"not finished: {', '.join(pending)}"] if pending else [])
        return MISSING, "; ".join(parts)
    if errors:
        return UNCHECKED, "; ".join(errors)
    if not seen:
        return MISSING, "no check ran on this head"
    return OK, f"{seen} check(s)"


def check_approval(items, sha):
    """Latest adversarial verdict: APPROVED and naming the head `sha`."""
    verdicts = []
    for body, at in items:
        for m in flow.verdict_matches(body):
            if m.group(1) == "Adversarial":
                head = flow.HEAD_RE.search(m.string[m.end():])
                verdicts.append((at, m.group(2), head.group(1).lower() if head else None))
    if not verdicts:
        return MISSING, "no adversarial verdict on the PR (REVIEW-ROUNDS.md §Traceability)"
    _, verdict, head = sorted(verdicts, key=lambda v: v[0])[-1]
    if verdict != "APPROVED":
        return MISSING, f"latest verdict is {verdict}" + (f" (head {head[:7]})" if head else "")
    if not head:
        return MISSING, "the APPROVED verdict names no head sha"
    if not sha.lower().startswith(head):
        return MISSING, f"stale approval: given on {head[:7]}, the head is {sha[:7]}"
    return OK, f"head {sha[:7]}"


def open_questions(text):
    """Content of the `Open questions` section, or None if the text has none."""
    lines = COMMENT_RE.sub("", text).splitlines()
    for i, line in enumerate(lines):
        m = SECTION_RE.match(line.strip())
        if not m:
            continue
        # The section is its first paragraph or list: it ends at a blank line after content, a heading, a bold
        # line or a `---` rule (the attribution footer), so the lines that follow it are not read as questions.
        content = [m.group(1)]
        for following in lines[i + 1:]:
            if SECTION_END_RE.match(following.strip()) or (not following.strip() and any(c.strip() for c in content)):
                break
            content.append(following)
        items = [re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", c.strip()).strip("_* ") for c in content]
        return [c for c in items if c]
    return None


def check_questions(body, comments):
    """(state, detail), or None when the project has no report with an `Open questions` section."""
    reports = [c for c in comments if REPORT_MARKER in (c.get("body") or "")]
    if reports:
        latest = sorted(reports, key=lambda c: c.get("created_at") or "")[-1]
        found, where = open_questions(latest.get("body") or ""), "latest report comment"
        if found is None:
            return MISSING, f"the {where} has no `Open questions` section"
    else:
        found, where = open_questions(body), "PR body"
        if found is None:
            return None
    if all(NONE_RE.match(item) for item in found):
        return OK, where
    return MISSING, f"{len(found)} unanswered in the {where}: {found[0][:80]}"


def check_body(body, lines, ledger):
    """(state, detail) of the lines the project requires in the PR body, or None if it requires none."""
    if not lines and not ledger:
        return None
    text = COMMENT_RE.sub("", body)
    gaps = []
    if "issue" in lines and not ISSUE_LINE_RE.search(text):
        gaps.append("Closes/Refs #n (or Direct-PR:)")
    if "claim" in lines and not CLAIM_RE.search(text):
        gaps.append("Claim:")
    docs_scope = text
    if ledger:
        m = LEDGER_RE.search(text)
        if not m:
            gaps.append("### Ledger section")
        docs_scope = text[m.end():] if m else ""
    if "docs" in lines or ledger:
        docs = DOCS_RE.search(docs_scope)
        where = " in ### Ledger" if ledger else ""
        if not docs:
            gaps.append(f"Docs:{where}")
        elif DOCS_NONE_RE.match(docs.group(1).strip()):
            gaps.append("Docs: none without a (reason)")
    return (MISSING, "lacks " + ", ".join(gaps)) if gaps else (OK, "")


def load_config(path):
    """(merge_gate settings, ledger on). A missing file means the defaults; an unreadable one raises ValueError."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}
    except (OSError, ValueError) as e:
        raise ValueError(f"{path}: {e}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{path}: a JSON object was expected")
    gate = dict(DEFAULTS)
    gate.update(data.get("merge_gate") or {})
    return gate, bool((data.get("ledger") or {}).get("enabled"))


def evaluate(http, repo, number, gate, ledger):
    """(head sha, [(state, label, detail)]); raises FetchError when the PR itself cannot be read."""
    pull = http(f"/repos/{repo}/pulls/{number}")
    if not isinstance(pull, dict) or not (pull.get("head") or {}).get("sha"):
        raise FetchError(f"/repos/{repo}/pulls/{number}: not a pull request")
    sha = pull["head"]["sha"]
    rows = []

    def add(label, result):
        if result is not None:
            rows.append((result[0], label, result[1]))

    is_open = pull.get("state") == "open" and not pull.get("merged")
    add("PR open", (OK, "") if is_open else (MISSING, "already merged" if pull.get("merged") else "closed"))
    add("not a draft", (MISSING, "the PR is a draft") if pull.get("draft") else (OK, ""))
    mergeable = pull.get("mergeable")
    add("mergeable", (OK, "") if mergeable is True else
        (UNCHECKED, "GitHub is still computing it; run again in a few seconds") if mergeable is None else
        (MISSING, f"mergeable_state: {pull.get('mergeable_state')}"))
    add(f"CI green on head {sha[:7]}", check_ci(http, repo, sha))

    try:
        reviews = paged(http, f"/repos/{repo}/pulls/{number}/reviews?per_page={PER_PAGE}")
        comments = paged(http, f"/repos/{repo}/issues/{number}/comments?per_page={PER_PAGE}")
    except FetchError as e:
        add("adversarial review APPROVED on the head", (UNCHECKED, str(e)))
        add("no open question in the report", (UNCHECKED, str(e)))
    else:
        items = [(r.get("body") or "", r["submitted_at"]) for r in reviews if r.get("submitted_at")]
        items += [(c.get("body") or "", c.get("created_at") or "") for c in comments]
        add("adversarial review APPROVED on the head", check_approval(items, sha))
        add("no open question in the report", check_questions(pull.get("body") or "", comments))

    try:
        threads = [t for t in review_threads(http, repo, number) if not t.get("isResolved")]
    except FetchError as e:
        add("no open review thread", (UNCHECKED, f"{e} (GraphQL is the only source of thread resolution)"))
    else:
        detail = []
        for t in threads:
            first = ((t.get("comments") or {}).get("nodes") or [{}])[0] or {}
            detail.append(f"{t.get('path', '?')} {first.get('url', '')}".strip())
        security = any(SECURITY_RE.search((((t.get("comments") or {}).get("nodes") or [{}])[0] or {})
                                          .get("body") or "") for t in threads)
        add("no open review thread", (OK, "") if not threads else
            (MISSING, f"{len(threads)} open: {'; '.join(detail)}"
             + ("; a security thread: the operator decides" if security else "")))

    labels = _labels(pull)
    required = [lb for lb in gate.get("required_labels") or [] if lb not in labels]
    if gate.get("required_labels"):
        add("required labels present", (MISSING, "lacks " + ", ".join(required)) if required else (OK, ""))
    if gate.get("security_labels"):
        found = [lb for lb in labels if lb in gate["security_labels"]]
        add("no security label", (MISSING, f"{', '.join(found)}: blocks until the operator decides")
            if found else (OK, ""))
    add("PR body lines", check_body(pull.get("body") or "", gate.get("body_lines") or [], ledger))
    return sha, rows


def run(argv=None, http=None, env=None, out=sys.stdout):
    env = os.environ if env is None else env
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pr", type=int)
    ap.add_argument("--repo", default=env.get("GITHUB_REPOSITORY"))
    ap.add_argument("--config", default=".harness/config.json")
    a = ap.parse_args(argv)

    def say(text):
        print(text, file=out)

    def cannot(reason):
        say(f"⚠ could not check PR #{a.pr}: {reason}. Never merge on this answer.")
        return EXIT_COULD_NOT_CHECK

    try:
        gate, ledger = load_config(a.config)
    except ValueError as e:
        return cannot(f"config unreadable ({e})")
    token = env.get("GH_TOKEN") or env.get("GITHUB_TOKEN")
    if not token:
        return cannot("no token (GH_TOKEN or GITHUB_TOKEN)")
    if not a.repo or "/" not in a.repo:
        return cannot("no repository (--repo owner/name or GITHUB_REPOSITORY)")
    try:
        sha, rows = evaluate(http or github(token), a.repo, a.pr, gate, ledger)
    except FetchError as e:
        return cannot(str(e))
    say(f"Merge gate of {a.repo}#{a.pr}, head {sha}")
    for state, label, detail in rows:
        say(f"{state:<9} {label}" + (f": {detail}" if detail else ""))
    missing = sum(1 for r in rows if r[0] == MISSING)
    unchecked = sum(1 for r in rows if r[0] == UNCHECKED)
    if missing:
        say(f"✘ not ready: {missing} missing" + (f", {unchecked} unchecked" if unchecked else ""))
        return EXIT_NOT_READY
    if unchecked:
        say(f"⚠ could not check: {unchecked} line(s) unchecked. Never merge on this answer.")
        return EXIT_COULD_NOT_CHECK
    say(f"✔ may merge: expected head {sha} (gh pr merge {a.pr} --match-head-commit {sha}, or `sha` in the "
        "REST merge call)")
    return EXIT_MAY_MERGE


if __name__ == "__main__":
    sys.exit(run())

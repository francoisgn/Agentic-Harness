#!/usr/bin/env python3
"""GitHub repository settings described in a versioned file (.github/repo-settings.json), applied by CI.

A cloud session cannot change the settings of a repository (LESSONS L56): it changes this file through a PR; on
merge, the repo-settings.yml workflow runs this script with an administration token (secret REPO_ADMIN_TOKEN).

Sections (all optional; a missing section is left untouched):
  "repository": fields of PATCH /repos/{owner}/{repo} listed in REPO_FIELDS;
  "topics":     full list of topics (replaces the existing one);
  "rulesets":   managed rulesets, identified by their `name` (created or updated; a ruleset missing from the file is
                never deleted: remove it by hand, on purpose).
Usage: repo-settings.py --repo owner/name [--file .github/repo-settings.json] [--apply]
Without --apply: prints the plan and exits 2 if there are gaps (drift check), 0 otherwise.
Token: GH_TOKEN variable (fine-grained, "Administration: write" on the repository). Standard library only.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

REPO_FIELDS = {"description", "homepage", "has_issues", "has_projects", "has_wiki", "has_discussions",
               "allow_squash_merge", "allow_merge_commit", "allow_rebase_merge", "allow_auto_merge",
               "delete_branch_on_merge", "allow_update_branch", "web_commit_signoff_required",
               "squash_merge_commit_title", "squash_merge_commit_message"}
RULESET_KEYS = ("name", "target", "enforcement", "conditions", "rules", "bypass_actors")
API = "https://api.github.com"


def _covers(actual, wanted):
    """`actual` (API response) contains `wanted` (file): keys of the file ⊆ response, recursively.

    The API returns default values the file does not state (`allowed_merge_methods`, `integration_id`...): they are
    not drift. Lists are compared without order, item by item, at equal length (one more rule on the GitHub side IS
    drift).
    """
    if isinstance(wanted, dict):
        return isinstance(actual, dict) and all(k in actual and _covers(actual[k], v) for k, v in wanted.items())
    if isinstance(wanted, list):
        if not isinstance(actual, list) or len(actual) != len(wanted):
            return False
        remaining = list(actual)
        for w in wanted:
            match = next((i for i, a in enumerate(remaining) if _covers(a, w)), None)
            if match is None:
                return False
            remaining.pop(match)
        return True
    return actual == wanted


def plan(desired, current):
    """Actions to take so that `current` looks like `desired` (pure function)."""
    actions = []
    desired = {k: v for k, v in desired.items() if not k.startswith("$")}  # "$comment": documentation of the file
    unknown_sections = sorted(set(desired) - {"repository", "topics", "rulesets"})
    if unknown_sections:
        raise ValueError(f"unknown sections: {unknown_sections} (allowed: repository, topics, rulesets)")
    repo = desired.get("repository")
    if repo is not None:
        unknown = sorted(set(repo) - REPO_FIELDS)
        if unknown:
            raise ValueError(f"unmanaged repository fields: {unknown} (allowed: {sorted(REPO_FIELDS)})")
        fields = {k: v for k, v in repo.items() if current.get("repository", {}).get(k) != v}
        if fields:
            actions.append({"op": "patch-repo", "fields": fields})
    if desired.get("topics") is not None:
        names = sorted(set(desired["topics"]))
        if names != sorted(current.get("topics", [])):
            actions.append({"op": "put-topics", "names": names})
    names = [r.get("name") for r in desired.get("rulesets") or []]
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        raise ValueError(f"rulesets declared twice: {duplicates} (the name identifies a ruleset)")
    by_name = {r["name"]: r for r in current.get("rulesets", [])}
    for ruleset in desired.get("rulesets") or []:
        wanted = {k: ruleset[k] for k in RULESET_KEYS if k in ruleset}
        existing = by_name.get(ruleset["name"])
        if existing is None:
            actions.append({"op": "create-ruleset", "ruleset": wanted})
        elif not _covers(existing, wanted):
            actions.append({"op": "update-ruleset", "id": existing["id"], "ruleset": wanted})
    return actions


def read_current(repo, http):
    rulesets = [http("GET", f"/repos/{repo}/rulesets/{r['id']}")
                for r in http("GET", f"/repos/{repo}/rulesets?includes_parents=false")]
    return {"repository": http("GET", f"/repos/{repo}"),
            "topics": http("GET", f"/repos/{repo}/topics").get("names", []),
            "rulesets": rulesets}


def apply(repo, actions, http):
    for a in actions:
        if a["op"] == "patch-repo":
            http("PATCH", f"/repos/{repo}", a["fields"])
        elif a["op"] == "put-topics":
            http("PUT", f"/repos/{repo}/topics", {"names": a["names"]})
        elif a["op"] == "create-ruleset":
            http("POST", f"/repos/{repo}/rulesets", a["ruleset"])
        elif a["op"] == "update-ruleset":
            http("PUT", f"/repos/{repo}/rulesets/{a['id']}", a["ruleset"])


def github(token):
    def http(method, path, body=None):
        req = urllib.request.Request(API + path, method=method,
                                     data=None if body is None else json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {token}",
                                              "Accept": "application/vnd.github+json",
                                              "X-GitHub-Api-Version": "2022-11-28",
                                              "User-Agent": "belayline-repo-settings"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            raise SystemExit(f"✘ {method} {path}: HTTP {e.code} {detail}") from None
        return json.loads(raw) if raw else {}
    return http


def describe(a):
    if a["op"] == "patch-repo":
        return "repository: " + ", ".join(f"{k} → {json.dumps(v, ensure_ascii=False)}" for k, v in a["fields"].items())
    if a["op"] == "put-topics":
        return "topics → " + ", ".join(a["names"])
    return f"ruleset \"{a['ruleset']['name']}\": {'create' if a['op'] == 'create-ruleset' else 'update'}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--file", default=".github/repo-settings.json")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("✘ GH_TOKEN missing (secret REPO_ADMIN_TOKEN: token with \"Administration: write\" on the repository)")
    with open(a.file, encoding="utf-8") as f:
        desired = json.load(f)
    http = github(token)
    actions = plan(desired, read_current(a.repo, http))
    for act in actions:
        print(f"- {describe(act)}")
    if not actions:
        print("🟢 Settings match the file.")
        return 0
    if not a.apply:
        print(f"🟠 {len(actions)} gap(s); --apply to apply.")
        return 2
    apply(a.repo, actions, http)
    print(f"🟢 {len(actions)} change(s) applied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

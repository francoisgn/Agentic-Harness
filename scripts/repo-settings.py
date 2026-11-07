#!/usr/bin/env python3
"""Réglages du dépôt GitHub décrits dans un fichier versionné (.github/repo-settings.json), appliqués par la CI.

Une session cloud ne peut pas modifier les réglages d'un dépôt (LESSONS L56) : elle modifie ce fichier par PR ; au
merge, le workflow repo-settings.yml lance ce script avec un jeton d'administration (secret REPO_ADMIN_TOKEN).

Sections (toutes facultatives ; une section absente n'est pas touchée) :
  "repository" : champs de PATCH /repos/{owner}/{repo} listés dans REPO_FIELDS ;
  "topics"     : liste complète des topics (remplace l'existante) ;
  "rulesets"   : rulesets gérés, identifiés par leur `name` (créés ou mis à jour ; un ruleset absent du fichier n'est
                 jamais supprimé : on le retire à la main, c'est voulu).
Usage : repo-settings.py --repo owner/nom [--file .github/repo-settings.json] [--apply]
Sans --apply : affiche le plan et sort en 2 s'il y a des écarts (contrôle de dérive), 0 sinon.
Jeton : variable GH_TOKEN (fine-grained, « Administration: write » sur le dépôt). Bibliothèque standard seulement.
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


def _canon(value):
    """Forme comparable : listes de règles indépendantes de l'ordre, clés triées."""
    if isinstance(value, dict):
        return {k: _canon(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return sorted((_canon(v) for v in value), key=lambda v: json.dumps(v, sort_keys=True, ensure_ascii=False))
    return value


def plan(desired, current):
    """Actions à mener pour que `current` ressemble à `desired` (fonction pure)."""
    actions = []
    desired = {k: v for k, v in desired.items() if not k.startswith("$")}  # "$comment" : documentation du fichier
    unknown_sections = sorted(set(desired) - {"repository", "topics", "rulesets"})
    if unknown_sections:
        raise ValueError(f"sections inconnues : {unknown_sections} (permis : repository, topics, rulesets)")
    repo = desired.get("repository")
    if repo is not None:
        unknown = sorted(set(repo) - REPO_FIELDS)
        if unknown:
            raise ValueError(f"champs de dépôt non gérés : {unknown} (permis : {sorted(REPO_FIELDS)})")
        fields = {k: v for k, v in repo.items() if current["repository"].get(k) != v}
        if fields:
            actions.append({"op": "patch-repo", "fields": fields})
    if desired.get("topics") is not None:
        names = sorted(set(desired["topics"]))
        if names != sorted(current.get("topics", [])):
            actions.append({"op": "put-topics", "names": names})
    by_name = {r["name"]: r for r in current.get("rulesets", [])}
    for ruleset in desired.get("rulesets") or []:
        wanted = {k: ruleset[k] for k in RULESET_KEYS if k in ruleset}
        existing = by_name.get(ruleset["name"])
        if existing is None:
            actions.append({"op": "create-ruleset", "ruleset": wanted})
        elif _canon({k: existing.get(k) for k in wanted}) != _canon(wanted):
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
                                              "User-Agent": "agentic-harness-repo-settings"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            raise SystemExit(f"✘ {method} {path} : HTTP {e.code} {detail}") from None
        return json.loads(raw) if raw else {}
    return http


def describe(a):
    if a["op"] == "patch-repo":
        return "dépôt : " + ", ".join(f"{k} → {json.dumps(v, ensure_ascii=False)}" for k, v in a["fields"].items())
    if a["op"] == "put-topics":
        return "topics → " + ", ".join(a["names"])
    return f"ruleset « {a['ruleset']['name']} » : {'création' if a['op'] == 'create-ruleset' else 'mise à jour'}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--file", default=".github/repo-settings.json")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("✘ GH_TOKEN absent (secret REPO_ADMIN_TOKEN : jeton « Administration: write » sur le dépôt)")
    with open(a.file, encoding="utf-8") as f:
        desired = json.load(f)
    http = github(token)
    actions = plan(desired, read_current(a.repo, http))
    for act in actions:
        print(f"- {describe(act)}")
    if not actions:
        print("🟢 Réglages conformes au fichier.")
        return 0
    if not a.apply:
        print(f"🟠 {len(actions)} écart(s) ; --apply pour appliquer.")
        return 2
    apply(a.repo, actions, http)
    print(f"🟢 {len(actions)} changement(s) appliqué(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

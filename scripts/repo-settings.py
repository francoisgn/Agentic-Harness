#!/usr/bin/env python3
"""Réglages du dépôt GitHub décrits dans un fichier versionné (.github/repo-settings.json), appliqués par la CI.

Une session cloud ne peut pas modifier les réglages d'un dépôt (LESSONS L56) : elle modifie ce fichier par PR ; au
merge, le workflow repo-settings.yml lance ce script avec un jeton d'administration (secret REPO_ADMIN_TOKEN).

Sections (toutes facultatives ; une section absente n'est pas touchée) :
  "repository" : champs de PATCH /repos/{owner}/{repo} listés dans REPO_FIELDS ; une description restée celle du
                 gabarit (`<…>`) n'est pas envoyée ;
  "topics"     : liste complète des topics (remplace l'existante) ;
  Description ou topics manquants ou non valides : avertissement, sans bloquer (CONVENTIONS.md §Identité du dépôt).
  "rulesets"   : rulesets gérés, identifiés par leur `name` (créés ou mis à jour ; un ruleset absent du fichier n'est
                 jamais supprimé : on le retire à la main, c'est voulu).
Usage : repo-settings.py --repo owner/nom [--file .github/repo-settings.json] [--apply]
Sans --apply : affiche le plan et sort en 2 s'il y a des écarts (contrôle de dérive), 0 sinon.
Jeton : variable GH_TOKEN (fine-grained, « Administration: write » sur le dépôt). Bibliothèque standard seulement.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

REPO_FIELDS = {"description", "homepage", "has_issues", "has_projects", "has_wiki", "has_discussions",
               "allow_squash_merge", "allow_merge_commit", "allow_rebase_merge", "allow_auto_merge",
               "delete_branch_on_merge", "allow_update_branch", "web_commit_signoff_required",
               "squash_merge_commit_title", "squash_merge_commit_message"}
RULESET_KEYS = ("name", "target", "enforcement", "conditions", "rules", "bypass_actors")
API = "https://api.github.com"
# Règles de GitHub pour un topic : minuscules, chiffres, tirets, 50 caractères au plus, 20 topics au plus par dépôt
# (https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics)
TOPIC = re.compile(r"^[a-z0-9][a-z0-9-]{0,49}$")
MAX_TOPICS = 20


def _placeholder(text):
    """Vrai pour une description vide ou restée celle du gabarit (`<une phrase : …>`)."""
    text = (text or "").strip()
    return not text or (text.startswith("<") and text.endswith(">"))


def identity_gaps(desired):
    """Ce qui manque pour que le dépôt dise ce qu'il est (CONVENTIONS.md §Identité du dépôt) ; fonction pure."""
    gaps = []
    if _placeholder((desired.get("repository") or {}).get("description")):
        gaps.append("description absente ou restée celle du gabarit : une phrase, ce que fait le projet et pour qui")
    topics = desired.get("topics") or []
    bad = [t for t in topics if not isinstance(t, str) or not TOPIC.match(t)]
    if not topics:
        gaps.append("topics absents : 5 à 10 mots-clés (domaine, technologie, usage)")
    elif bad:
        gaps.append(f"topics non valides {bad} : minuscules, chiffres et tirets, 50 caractères au plus")
    elif len(set(topics)) > MAX_TOPICS:
        gaps.append(f"topics trop nombreux ({len(set(topics))}) : {MAX_TOPICS} au plus")
    return gaps


def _covers(actual, wanted):
    """`actual` (réponse de l'API) contient `wanted` (fichier) : clés du fichier ⊆ réponse, récursivement.

    L'API renvoie des valeurs par défaut que le fichier ne dit pas (`allowed_merge_methods`, `integration_id`…) : elles
    ne sont pas une dérive. Les listes se comparent sans ordre, élément par élément, à longueur égale (une règle en plus
    côté GitHub EST une dérive).
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
        fields = {k: v for k, v in repo.items() if current.get("repository", {}).get(k) != v
                  and not (k == "description" and _placeholder(v))}  # le texte du gabarit ne part jamais sur GitHub
        if fields:
            actions.append({"op": "patch-repo", "fields": fields})
    if desired.get("topics") is not None:
        names = sorted(set(desired["topics"]))
        if names != sorted(current.get("topics", [])):
            actions.append({"op": "put-topics", "names": names})
    names = [r.get("name") for r in desired.get("rulesets") or []]
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        raise ValueError(f"rulesets déclarés deux fois : {duplicates} (le nom identifie un ruleset)")
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
    for gap in identity_gaps(desired):
        print(f"::warning file={a.file}::{gap}")
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

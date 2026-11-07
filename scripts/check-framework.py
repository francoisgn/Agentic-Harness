#!/usr/bin/env python3
"""Contrôles de cohérence du cadre, lancés par la CI (bibliothèque standard seulement).

- skills : `name` = nom du dossier, `description` présente ;
- agents : `name` = nom du fichier, `description`, `tools`, `model` connu ; agents de conformité avec leurs sections ;
- manifeste : chaque source existe ;
- labels : noms uniques ;
- nommage des agents (ORCHESTRATION.md §7) : chaque exemple respecte l'expression régulière publiée.
Usage : check-framework.py [--root <dépôt>]   (sort en 1 au moindre écart, liste tous les écarts)
"""
import argparse
import json
import pathlib
import re
import sys

GENERIC_REVIEWER = "compliance-reviewer"
MODELS = {"haiku", "sonnet", "opus", "fable", "inherit"}
COMPLIANCE_SECTIONS = ("## Rôle et limites", "## Quand intervenir", "## Ce que je vérifie", "## Preuves attendues",
                       "## Format de réponse", "## Sources")


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 4)
    meta = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta, text[end + 4:]


def check(root):
    errors = []
    for skill in sorted((root / "plugins/harness/skills").glob("*/SKILL.md")):
        meta, _ = frontmatter(skill)
        rel = skill.relative_to(root)
        if meta is None or meta.get("name") != skill.parent.name:
            errors.append(f"{rel} : `name` doit valoir {skill.parent.name}")
        if not (meta or {}).get("description"):
            errors.append(f"{rel} : `description` manquante")

    for agent in sorted((root / "plugins/harness/agents").glob("*.md")):
        meta, body = frontmatter(agent)
        rel = agent.relative_to(root)
        meta = meta or {}
        if meta.get("name") != agent.stem:
            errors.append(f"{rel} : `name` doit valoir {agent.stem}")
        for key in ("description", "tools"):
            if not meta.get(key):
                errors.append(f"{rel} : `{key}` manquant")
        if meta.get("model") not in MODELS:
            errors.append(f"{rel} : `model` doit être l'un de {sorted(MODELS)}")
        if agent.stem.startswith("compliance-"):
            if agent.stem != GENERIC_REVIEWER:  # le générique tient ses sections de la spec du projet
                errors += [f"{rel} : section « {s} » manquante" for s in COMPLIANCE_SECTIONS if s not in body]
            if "Edit" in meta.get("tools", "") or "Write" in meta.get("tools", ""):
                errors.append(f"{rel} : un relecteur de conformité reste en lecture seule (ni Edit ni Write)")

    for n, line in enumerate((root / "harness.manifest").read_text(encoding="utf-8").splitlines(), 1):
        parts = line.split()
        if not parts or parts[0].startswith("#") or parts[1] == "-":
            continue
        if not (root / parts[1]).exists():
            errors.append(f"harness.manifest:{n} : source introuvable {parts[1]}")

    names = [label["name"] for label in json.loads((root / "templates/.github/labels.json").read_text(encoding="utf-8"))]
    errors += [f"labels.json : label en double « {x} »" for x in sorted({x for x in names if names.count(x) > 1})]

    orch = (root / "docs/ORCHESTRATION.md").read_text(encoding="utf-8")
    section = orch[orch.find("## 7."):]
    m = re.search(r"Contrôle : `(\^.+\$)`", section)
    if not m:
        errors.append("docs/ORCHESTRATION.md §7 : expression régulière de contrôle introuvable")
    else:
        rx = re.compile(m.group(1))
        examples = re.findall(r"`([a-z0-9-]+\.[^`\s]+)`", section[section.find("Exemples"):section.find("| Rôle")])
        if not examples:
            errors.append("docs/ORCHESTRATION.md §7 : aucun exemple d'identifiant")
        errors += [f"docs/ORCHESTRATION.md §7 : exemple non conforme « {e} »" for e in examples if not rx.match(e)]
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=pathlib.Path(__file__).resolve().parents[1], type=pathlib.Path)
    errors = check(ap.parse_args().root)
    for e in errors:
        print(f"✘ {e}")
    print(f"{'🔴' if errors else '🟢'} {len(errors)} écart(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

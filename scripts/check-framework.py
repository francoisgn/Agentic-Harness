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


def pull_request_job_names(text):
    """Noms de checks qu'un workflow publie sur une PR : workflow déclenché par `pull_request` (pas `_target`),
    jobs directs seulement (le check d'un job réutilisable s'appelle `appelant / appelé`)."""
    # Clé `on` éventuellement entre guillemets ; commentaire de fin de ligne ignoré
    on_key = r"^(?:on|'on'|\"on\"):"
    inline = re.search(on_key + r"[ \t]*([^#\s][^#\n]*)", text, re.M)  # `on: pull_request`, `on: [push, pull_request]`
    if inline:
        if not re.search(r"(?<![\w-])pull_request(?![\w-])", inline.group(1)):
            return set()
    else:
        on_block = re.search(on_key + r"[ \t]*(?:#.*)?\n((?:[ \t]+.*\n|\s*\n)*)", text, re.M)
        if not on_block:
            return set()
        # Seules les clés enfants directes de `on` sont des événements (pas un input `pull_request` d'un dispatch)
        lines = [ln for ln in on_block.group(1).splitlines() if ln.strip() and not ln.strip().startswith("#")]
        if not lines:
            return set()
        indent = min(len(ln) - len(ln.lstrip()) for ln in lines)
        if not any(len(ln) - len(ln.lstrip()) == indent and re.match(r"""\s*['"]?pull_request['"]?:""", ln) for ln in lines):
            return set()
    jobs = text[text.find("\njobs:"):]
    names = set()
    for block in re.split(r"\n  (?=[A-Za-z0-9_-]+:\s*\n)", jobs)[1:]:
        if re.search(r"^    uses:", block, re.M):
            continue
        m = re.search(r"^    name:\s*(.+?)\s*$", block, re.M)
        if m:
            names.add(m.group(1).strip("\"'"))
    return names


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
        if not parts or parts[0].startswith("#"):
            continue
        if len(parts) < 2:
            errors.append(f"harness.manifest:{n} : ligne mal formée (MODE SOURCE DESTINATION attendu)")
            continue
        if parts[1] == "-":
            continue
        if not (root / parts[1]).exists():
            errors.append(f"harness.manifest:{n} : source introuvable {parts[1]}")

    names = [label["name"] for label in json.loads((root / "templates/.github/labels.json").read_text(encoding="utf-8"))]
    errors += [f"labels.json : label en double « {x} »" for x in sorted({x for x in names if names.count(x) > 1})]

    # Contrôles requis du ruleset = noms de jobs réels, sinon plus aucune PR ne se merge (CI-BUDGET.md §4)
    settings = root / ".github/repo-settings.json"
    if settings.is_file():
        job_names = set()
        for wf in (root / ".github/workflows").glob("*.yml"):
            job_names |= pull_request_job_names(wf.read_text(encoding="utf-8"))
        for ruleset in json.loads(settings.read_text(encoding="utf-8")).get("rulesets", []):
            for rule in ruleset.get("rules", []):
                for chk in (rule.get("parameters") or {}).get("required_status_checks", []):
                    if chk["context"] not in job_names:
                        errors.append(f".github/repo-settings.json : contrôle requis « {chk['context']} » absent des "
                                      f"jobs de .github/workflows ({sorted(job_names)})")

    # Identité visuelle du dépôt (CONVENTIONS.md §Identité visuelle) : le cadre s'applique sa propre règle
    banner, social = root / "docs/assets/banner.svg", root / "docs/assets/social-preview.png"
    if not banner.is_file():
        errors.append("docs/assets/banner.svg : bannière du README introuvable")
    readme = root / "README.md"
    if readme.is_file() and "docs/assets/banner.svg" not in readme.read_text(encoding="utf-8"):
        errors.append("README.md : la bannière docs/assets/banner.svg n'y est pas affichée")
    if not social.is_file():
        errors.append("docs/assets/social-preview.png : social preview introuvable")
    else:
        head = social.read_bytes()[:24]  # signature PNG, puis IHDR : largeur et hauteur sur 4 octets chacune
        size = (int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big"))
        if head[:8] != b"\x89PNG\r\n\x1a\n" or size != (1280, 640):
            errors.append(f"docs/assets/social-preview.png : PNG de 1280×640 attendu (lu : {size[0]}×{size[1]})")
        elif social.stat().st_size >= 1_000_000:
            errors.append("docs/assets/social-preview.png : doit peser moins de 1 Mo (limite de GitHub)")

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

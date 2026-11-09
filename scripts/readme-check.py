#!/usr/bin/env python3
"""Contrôle le README d'un projet contre le standard du cadre (README-STANDARD.md ; bibliothèque standard seulement).

Vérifie, chaque point se désactivant dans `.harness/config.json` › `readme` (`false` pour tout couper) :
- badges        en-tête (avant le premier `## `) avec au moins une tuile technologique ;
- image         au moins une image hors badges ; chaque image a un texte alternatif ; chaque image locale existe ;
- architecture  un schéma d'architecture : une image `.svg` dont la source `.excalidraw` est versionnée à côté
                (`"architecture": "any"` accepte n'importe quelle image ou un bloc Mermaid) ;
- progress      le bloc `<!-- harness:begin avancement -->` … `<!-- harness:end avancement -->` contient un tableau,
                et cite chaque lot de `docs/LOTS.md` s'il existe ;
- quickstart    une section d'installation ou de démarrage ;
- contributing  une section « Contribuer » qui pointe vers un `CONTRIBUTING.md` présent.
Usage : readme-check.py [--root <dépôt>] [--readme README.md]   (sort en 1 au moindre écart, liste tous les écarts)
"""
import argparse
import json
import pathlib
import re
import sys

DEFAULTS = {"badges": True, "image": True, "architecture": "excalidraw", "progress": True, "quickstart": True,
            "contributing": True}
BADGE_HOSTS = ("img.shields.io", "badgen.net", "badge.fury.io", "/badge.svg", "/badges/")
IMAGE = re.compile(r"!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
HTML_IMAGE = re.compile(r"<img\b[^>]*>", re.I)
BEGIN, END = "<!-- harness:begin avancement -->", "<!-- harness:end avancement -->"
QUICKSTART = re.compile(r"^#{2,3}\s.*(install|démarr|demarr|quick ?start|getting started|utilis|usage|tirer parti)", re.I | re.M)
CONTRIBUTING = re.compile(r"^#{2,3}\s.*contribu", re.I | re.M)
LOT_ID = re.compile(r"\bLOT-[A-Za-z0-9]+\b")
TABLE_ROW = re.compile(r"^\|.*\|\s*$", re.M)
TABLE_RULE = re.compile(r"^\|?\s*:?-{3,}")


def settings(root):
    """Réglages effectifs : défauts, puis `.harness/config.json` › `readme` ; None si le contrôle est coupé."""
    path = root / ".harness" / "config.json"
    custom = json.loads(path.read_text(encoding="utf-8")).get("readme", {}) if path.is_file() else {}
    if custom is False:
        return None
    if not isinstance(custom, dict):
        raise ValueError(".harness/config.json : `readme` doit être un objet ou false")
    unknown = sorted(set(custom) - set(DEFAULTS))
    if unknown:
        raise ValueError(f".harness/config.json : clé(s) `readme` inconnue(s) {unknown} (connues : {sorted(DEFAULTS)})")
    return dict(DEFAULTS, **custom)


def images(text):
    """(alt, cible) de chaque image, Markdown ou HTML, hors blocs de code."""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    found = [(alt.strip(), target) for alt, target in IMAGE.findall(text)]
    for tag in HTML_IMAGE.findall(text):
        src = re.search(r"""\bsrc\s*=\s*["']([^"']+)["']""", tag, re.I)
        alt = re.search(r"""\balt\s*=\s*["']([^"']*)["']""", tag, re.I)
        if src:
            found.append((alt.group(1).strip() if alt else "", src.group(1)))
    return found


def is_badge(target):
    return any(host in target for host in BADGE_HOSTS)


def is_remote(target):
    return re.match(r"[a-z][a-z0-9+.-]*:", target, re.I) is not None or target.startswith("//")


def local_path(root, readme, target):
    """Chemin d'une image locale, ou None si elle sort du dépôt."""
    clean = target.split("#")[0].split("?")[0]
    base = root if clean.startswith("/") else readme.parent
    path = (base / clean.lstrip("/")).resolve()
    return path if path.is_relative_to(root.resolve()) else None


def progress_block(text):
    start, end = text.find(BEGIN), text.find(END)
    return text[start + len(BEGIN):end] if 0 <= start < end else None


def check(root, readme_name="README.md"):
    conf = settings(root)
    if conf is None:
        return []
    readme = root / readme_name
    if not readme.is_file():
        return [f"{readme_name} : absent (gabarit : templates/README.md.template du cadre)"]
    text = readme.read_text(encoding="utf-8")
    errors = []
    if not re.search(r"^#\s+\S", text, re.M) and not re.search(r"<h1\b", text, re.I):
        errors.append(f"{readme_name} : pas de titre de niveau 1")
    pics = images(text)
    first_section = re.search(r"^##\s", text, re.M)
    header = text[:first_section.start()] if first_section else text

    if conf["badges"] and not any(is_badge(t) for _, t in images(header)):
        errors.append(f"{readme_name} : en-tête sans tuile technologique (badge avant le premier « ## »)")

    content = [(alt, t) for alt, t in pics if not is_badge(t)]
    if conf["image"]:
        if not content:
            errors.append(f"{readme_name} : aucune image (capture, schéma) hors badges")
        errors += [f"{readme_name} : image sans texte alternatif ({t})" for alt, t in pics if not alt]
        for _, target in content:
            if is_remote(target):
                continue
            path = local_path(root, readme, target)
            if path is None or not path.is_file():
                errors.append(f"{readme_name} : image introuvable ({target})")

    if conf["architecture"]:
        sourced = []
        for _, target in content:
            path = None if is_remote(target) else local_path(root, readme, target)
            if path is not None and path.suffix == ".svg" and path.with_suffix(".excalidraw").is_file():
                sourced.append(target)
        if conf["architecture"] == "any":
            if not content and "```mermaid" not in text:
                errors.append(f"{readme_name} : aucun schéma d'architecture (image ou bloc Mermaid)")
        elif not sourced:
            errors.append(f"{readme_name} : aucun schéma d'architecture avec sa source Excalidraw "
                          "(image .svg et fichier .excalidraw du même nom, ex. docs/diagrams/architecture.*)")

    if conf["progress"]:
        block = progress_block(text)
        if block is None:
            errors.append(f"{readme_name} : bloc d'avancement absent ({BEGIN} … {END})")
        else:
            rows = [r for r in TABLE_ROW.findall(block) if not TABLE_RULE.match(r.strip().strip("|").strip())]
            if len(rows) < 2:   # en-tête + au moins une ligne
                errors.append(f"{readme_name} : bloc d'avancement sans tableau (une ligne par lot ou jalon)")
            plan = root / "docs" / "LOTS.md"
            if plan.is_file():
                missing = sorted(set(LOT_ID.findall(plan.read_text(encoding="utf-8"))) - set(LOT_ID.findall(block)))
                if missing:
                    errors.append(f"{readme_name} : lot(s) de docs/LOTS.md absents du bloc d'avancement : "
                                  + ", ".join(missing))

    if conf["quickstart"] and not QUICKSTART.search(text):
        errors.append(f"{readme_name} : pas de section d'installation ou de démarrage")

    if conf["contributing"]:
        section = CONTRIBUTING.search(text)
        if not section:
            errors.append(f"{readme_name} : pas de section « Contribuer »")
        guides = [p for p in (root / "CONTRIBUTING.md", root / ".github" / "CONTRIBUTING.md", root / "docs" / "CONTRIBUTING.md")
                  if p.is_file()]
        if not guides:
            errors.append("CONTRIBUTING.md : absent (gabarit : templates/CONTRIBUTING.md.template du cadre)")
        elif section and "CONTRIBUTING.md" not in text:
            errors.append(f"{readme_name} : la section « Contribuer » ne pointe pas vers CONTRIBUTING.md")
    return errors


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=pathlib.Path.cwd(), type=pathlib.Path)
    ap.add_argument("--readme", default="README.md")
    a = ap.parse_args()
    try:
        errors = check(a.root, a.readme)
    except (ValueError, OSError) as exc:
        errors = [str(exc)]
    for e in errors:
        print(f"✘ {e}")
    print(f"{'🔴' if errors else '🟢'} README : {len(errors)} écart(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

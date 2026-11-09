#!/usr/bin/env python3
"""Checks a project's README against the harness standard (README-STANDARD.md; standard library only).

Verifies the points below; each one can be switched off in `.harness/config.json` › `readme` (`false` cuts them all):
- badges        header (before the first `## `) with at least one technology badge;
- image         at least one image besides badges; every image has an alternative text; every local image exists;
- architecture  an architecture diagram: a `.svg` image whose `.excalidraw` source is versioned next to it
                (`"architecture": "any"` accepts any image or a Mermaid block);
- progress      the block `<!-- harness:begin progress -->` … `<!-- harness:end progress -->` holds a table,
                and names every lot of `docs/LOTS.md` if that file exists;
- quickstart    an installation or getting-started section;
- contributing  a "Contributing" section that points to an existing `CONTRIBUTING.md`.
Section headings are detected in English first; French headings stay accepted (a consumer project may be in French).
Usage: readme-check.py [--root <repository>] [--readme README.md]   (exits 1 on any gap, lists every gap)
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
BEGIN, END = "<!-- harness:begin progress -->", "<!-- harness:end progress -->"
# English first, then the French stems (démarrage, utilisation, contribuer) of consumer projects written in French.
QUICKSTART = re.compile(r"^#{2,3}\s.*(install|quick ?start|getting started|usage|using|démarr|demarr|utilis)",
                        re.I | re.M)
CONTRIBUTING = re.compile(r"^#{2,3}\s.*contribu", re.I | re.M)
LOT_ID = re.compile(r"\bLOT-[A-Za-z0-9]+\b")
TABLE_ROW = re.compile(r"^\|.*\|\s*$", re.M)
TABLE_RULE = re.compile(r"^\|?\s*:?-{3,}")


def settings(root):
    """Effective settings: defaults, then `.harness/config.json` › `readme`; None if the check is switched off."""
    path = root / ".harness" / "config.json"
    custom = json.loads(path.read_text(encoding="utf-8")).get("readme", {}) if path.is_file() else {}
    if custom is False:
        return None
    if not isinstance(custom, dict):
        raise ValueError(".harness/config.json: `readme` must be an object or false")
    unknown = sorted(set(custom) - set(DEFAULTS))
    if unknown:
        raise ValueError(f".harness/config.json: unknown `readme` key(s) {unknown} (known: {sorted(DEFAULTS)})")
    return dict(DEFAULTS, **custom)


def images(text):
    """(alt, target) of every image, Markdown or HTML, outside code blocks."""
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
    """Path of a local image, or None if it leaves the repository."""
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
        return [f"{readme_name}: missing (template: templates/README.md.template of the harness)"]
    text = readme.read_text(encoding="utf-8")
    errors = []
    if not re.search(r"^#\s+\S", text, re.M) and not re.search(r"<h1\b", text, re.I):
        errors.append(f"{readme_name}: no level-1 title")
    pics = images(text)
    first_section = re.search(r"^##\s", text, re.M)
    header = text[:first_section.start()] if first_section else text

    if conf["badges"] and not any(is_badge(t) for _, t in images(header)):
        errors.append(f"{readme_name}: header without a technology badge (badge before the first \"##\")")

    content = [(alt, t) for alt, t in pics if not is_badge(t)]
    if conf["image"]:
        if not content:
            errors.append(f"{readme_name}: no image (screenshot, diagram) besides badges")
        errors += [f"{readme_name}: image without alternative text ({t})" for alt, t in pics if not alt]
        for _, target in content:
            if is_remote(target):
                continue
            path = local_path(root, readme, target)
            if path is None or not path.is_file():
                errors.append(f"{readme_name}: image not found ({target})")

    if conf["architecture"]:
        sourced = []
        for _, target in content:
            path = None if is_remote(target) else local_path(root, readme, target)
            if path is not None and path.suffix == ".svg" and path.with_suffix(".excalidraw").is_file():
                sourced.append(target)
        if conf["architecture"] == "any":
            if not content and "```mermaid" not in text:
                errors.append(f"{readme_name}: no architecture diagram (image or Mermaid block)")
        elif not sourced:
            errors.append(f"{readme_name}: no architecture diagram with its Excalidraw source "
                          "(.svg image and .excalidraw file of the same name, e.g. docs/diagrams/architecture.*)")

    if conf["progress"]:
        block = progress_block(text)
        if block is None:
            errors.append(f"{readme_name}: progress block missing ({BEGIN} … {END})")
        else:
            rows = [r for r in TABLE_ROW.findall(block) if not TABLE_RULE.match(r.strip().strip("|").strip())]
            if len(rows) < 2:   # header + at least one row
                errors.append(f"{readme_name}: progress block without a table (one row per lot or milestone)")
            plan = root / "docs" / "LOTS.md"
            if plan.is_file():
                missing = sorted(set(LOT_ID.findall(plan.read_text(encoding="utf-8"))) - set(LOT_ID.findall(block)))
                if missing:
                    errors.append(f"{readme_name}: lot(s) of docs/LOTS.md missing from the progress block: "
                                  + ", ".join(missing))

    if conf["quickstart"] and not QUICKSTART.search(text):
        errors.append(f"{readme_name}: no installation or getting-started section")

    if conf["contributing"]:
        section = CONTRIBUTING.search(text)
        if not section:
            errors.append(f"{readme_name}: no \"Contributing\" section")
        guides = [p for p in (root / "CONTRIBUTING.md", root / ".github" / "CONTRIBUTING.md",
                              root / "docs" / "CONTRIBUTING.md") if p.is_file()]
        if not guides:
            errors.append("CONTRIBUTING.md: missing (template: templates/CONTRIBUTING.md.template of the harness)")
        elif section and "CONTRIBUTING.md" not in text:
            errors.append(f"{readme_name}: the \"Contributing\" section does not point to CONTRIBUTING.md")
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
    print(f"{'🔴' if errors else '🟢'} README: {len(errors)} gap(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

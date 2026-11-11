#!/usr/bin/env python3
"""Renders the README diagrams from their Excalidraw "skeleton" source (standard library only).

  docs/diagrams/<name>.json        source: Excalidraw elements (rectangle, ellipse, text, arrow, built-in `label`)
  → docs/diagrams/<name>.excalidraw  native scene, to open and edit on excalidraw.com (File → Open), font Excalifont
  → docs/diagrams/<name>.svg         README image, either:
      - drawn by this script (built-in renderer, default, deterministic, close to the Excalidraw look); or
      - exported by Excalidraw itself from the .excalidraw scene (excalidraw.com → Export image → SVG, or an
        Excalidraw MCP), saved as <name>.svg, then stamped with --stamp <name>.

Usage: render.py [--check] [--engine auto|builtin] [--stamp <name>] [--dir <directory>] [name...]
  --check:  exits 1 if a scene or an SVG is not up to date, or if a text overflows. An Excalidraw export is checked
            through the hashes its stamp carries (its scene, its own body), a built-in one by drawing it again.
  --engine: auto (default) draws the SVG, but keeps an Excalidraw export: current, it stays; stale, the render
            refuses and says the two ways out. builtin draws the SVG and replaces an Excalidraw export.
  --stamp:  verifies <name>.svg is an SVG exported by Excalidraw (well-formed SVG, `<!-- svg-source:excalidraw -->`
            marker, scene up to date, not stamped for another scene) and writes the stamp that --check reads:
            `<!-- belayline-scene-sha256:<scene> svg-sha256:<body> -->`. The stamp records which scene the author
            exported from; it cannot prove the image matches the scene: the reviewer looks at the image.
  --dir:    directory of the diagrams (default: docs/diagrams of the current repository, otherwise the harness's).
            Vendored into a project as .harness/scripts/diagrams-render.py (README-STANDARD.md §4).
Changing a diagram: edit the .json (or the .excalidraw, then carry it over), run render.py again, commit all three.
A scene-only diagram has no .json: it is drawn in Excalidraw, <name>.excalidraw is its source and <name>.svg its
stamped Excalidraw export (--stamp). Nothing is rendered for it; --check verifies the SVG was exported from that scene.
"""
import argparse
import hashlib
import json
import math
import pathlib
import random
import re
import sys
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIR = ROOT / "docs" / "diagrams"
FONT = "Segoe UI, Helvetica, Arial, sans-serif"
CHAR_W = 0.52      # mean width of a character, in em (estimate for the font above)
FIT_CHAR_W = 0.58  # widest line width per character measured in Excalifont, the font of the scene and of the export
LINE_H = 1.25
PAD = 24
EXCALIFONT = 5   # Excalidraw font family id of Excalifont, the hand-drawn font of excalidraw.com
EXCALIDRAW_MARKER = "<!-- svg-source:excalidraw -->"  # written by Excalidraw in every SVG it exports
STAMP = re.compile(r"<!-- belayline-scene-sha256:([0-9a-f]{64}) svg-sha256:([0-9a-f]{64}) -->")
ANY_STAMP = re.compile(r"<!-- belayline-scene-sha256:[^>]*-->")


def _rng(eid):
    return random.Random(int(hashlib.sha256(eid.encode()).hexdigest()[:8], 16))


def _jitter_line(r, x1, y1, x2, y2, rough):
    """Slightly shaky segment: two offset passes, like the Excalidraw stroke (roughness 1)."""
    out = []
    for _ in range(2):
        j = lambda: r.uniform(-rough, rough)  # noqa: E731
        mx, my = (x1 + x2) / 2 + j() * 1.5, (y1 + y2) / 2 + j() * 1.5
        out.append(f"M{x1 + j():.1f} {y1 + j():.1f} Q{mx:.1f} {my:.1f} {x2 + j():.1f} {y2 + j():.1f}")
    return " ".join(out)


def text_width(text, size, char_w=CHAR_W):
    return max((len(line) for line in text.split("\n")), default=0) * size * char_w


def _text(x, y, text, size, color, anchor="middle"):
    lines = text.split("\n")
    top = y - (len(lines) - 1) * size * LINE_H / 2
    spans = "".join(f'<tspan x="{x:.1f}" y="{top + i * size * LINE_H:.1f}">{escape(line)}</tspan>'
                    for i, line in enumerate(lines))
    return (f'<text font-family="{FONT}" font-size="{size}" fill="{color}" text-anchor="{anchor}" '
            f'dominant-baseline="central">{spans}</text>')


def _shape(e, r):
    x, y, w, h = e["x"], e["y"], e["width"], e["height"]
    stroke = e.get("strokeColor", "#1e1e1e")
    fill = e.get("backgroundColor", "transparent")
    sw = e.get("strokeWidth", 2)
    opacity = e.get("opacity", 100) / 100
    dash = ' stroke-dasharray="8 6"' if e.get("strokeStyle") == "dashed" else ""
    parts = []
    if e["type"] == "ellipse":
        cx, cy = x + w / 2, y + h / 2
        if fill != "transparent":
            parts.append(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{w / 2:.1f}" ry="{h / 2:.1f}" fill="{fill}"/>')
        for k in range(2):
            d = r.uniform(-1.5, 1.5)
            parts.append(f'<ellipse cx="{cx + d:.1f}" cy="{cy - d:.1f}" rx="{w / 2 + d:.1f}" ry="{h / 2 - d:.1f}" '
                         f'fill="none" stroke="{stroke}" stroke-width="{sw}"{dash}/>')
    else:
        rad = 16 if e.get("roundness") else 0
        if fill != "transparent":
            parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rad}" fill="{fill}"/>')
        if rad:
            for k in range(2):
                d = r.uniform(-1.2, 1.2)
                parts.append(f'<rect x="{x + d:.1f}" y="{y - d:.1f}" width="{w - d:.1f}" height="{h + d:.1f}" '
                             f'rx="{rad}" fill="none" stroke="{stroke}" stroke-width="{sw}"{dash}/>')
        else:
            path = " ".join(_jitter_line(r, *seg, 1.2) for seg in
                            ((x, y, x + w, y), (x + w, y, x + w, y + h), (x + w, y + h, x, y + h), (x, y + h, x, y)))
            parts.append(f'<path d="{path}" fill="none" stroke="{stroke}" stroke-width="{sw}"{dash}/>')
    label = e.get("label")
    if label:
        parts.append(_text(x + w / 2, y + h / 2, label["text"], label.get("fontSize", 20),
                           e.get("label", {}).get("strokeColor", "#1e1e1e")))
    return f'<g opacity="{opacity}">{"".join(parts)}</g>'


def _arrowhead(x, y, angle, color, sw):
    # `angle` points from the tip towards the segment: the two wings spread ±30° from it
    a1, a2 = angle + math.radians(30), angle - math.radians(30)
    size = 14
    return (f'<path d="M{x + size * math.cos(a1):.1f} {y + size * math.sin(a1):.1f} L{x:.1f} {y:.1f} '
            f'L{x + size * math.cos(a2):.1f} {y + size * math.sin(a2):.1f}" fill="none" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>')


def _arrow(e, r):
    pts = [(e["x"] + px, e["y"] + py) for px, py in e["points"]]
    color = e.get("strokeColor", "#1e1e1e")
    sw = e.get("strokeWidth", 2)
    dash = ' stroke-dasharray="8 6"' if e.get("strokeStyle") == "dashed" else ""
    d = " ".join(_jitter_line(r, *pts[i], *pts[i + 1], 0.8) for i in range(len(pts) - 1))
    parts = [f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round"{dash}/>']
    if e.get("endArrowhead", "arrow"):
        (x1, y1), (x2, y2) = pts[-2], pts[-1]
        parts.append(_arrowhead(x2, y2, math.atan2(y1 - y2, x1 - x2), color, sw))
    if e.get("startArrowhead"):
        (x1, y1), (x2, y2) = pts[1], pts[0]
        parts.append(_arrowhead(x2, y2, math.atan2(y1 - y2, x1 - x2), color, sw))
    label = e.get("label")
    if label:
        # Label in the middle of the longest segment, on a white background
        i = max(range(len(pts) - 1), key=lambda k: math.dist(pts[k], pts[k + 1]))
        mx, my = (pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2
        size = label.get("fontSize", 16)
        w, h = text_width(label["text"], size) + 12, size * LINE_H * len(label["text"].split("\n")) + 6
        parts.append(f'<rect x="{mx - w / 2:.1f}" y="{my - h / 2:.1f}" width="{w:.1f}" height="{h:.1f}" rx="4" '
                     f'fill="#ffffff"/>')
        parts.append(_text(mx, my, label["text"], size, color if color != "#1e1e1e" else "#1e1e1e"))
    return "".join(parts)


def invalid(source):
    """Malformed elements: to fix in the source (message, no traceback)."""
    issues = []
    for e in source:
        if e.get("type") != "arrow":
            continue
        pts = e.get("points") or []
        if not isinstance(pts, list) or len(pts) < 2:
            issues.append(f"{e.get('id')}: an arrow needs at least two points")
        elif not all(isinstance(p, (list, tuple)) and len(p) == 2
                     and all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in p) for p in pts):
            issues.append(f"{e.get('id')}: every arrow point is a pair of numbers [x, y]")
    return issues


def drawable(source):
    return [e for e in source if e["type"] not in ("cameraUpdate", "delete", "restoreCheckpoint")]


def overflows(source):
    """Texts that overflow their shape (estimate): to fix in the source."""
    issues = []
    for e in drawable(source):
        label = e.get("label")
        if label and e["type"] in ("rectangle", "ellipse", "diamond"):
            size = label.get("fontSize", 20)
            need_w = text_width(label["text"], size, FIT_CHAR_W) * (1.25 if e["type"] == "ellipse" else 1) + 20
            need_h = len(label["text"].split("\n")) * size * LINE_H + 12
            if need_w > e["width"] or need_h > e["height"]:
                issues.append(f"{e['id']}: \"{label['text'].splitlines()[0]}…\" overflows "
                              f"({need_w:.0f}×{need_h:.0f} for {e['width']}×{e['height']})")
    return issues


def bounds(els):
    xs, ys = [], []
    for e in els:
        if e["type"] == "arrow":
            for px, py in e["points"]:
                xs.append(e["x"] + px)
                ys.append(e["y"] + py)
        elif e["type"] == "text":
            xs += [e["x"], e["x"] + text_width(e["text"], e.get("fontSize", 20))]
            ys += [e["y"], e["y"] + e.get("fontSize", 20) * LINE_H * len(e["text"].split("\n"))]
        else:
            xs += [e["x"], e["x"] + e["width"]]
            ys += [e["y"], e["y"] + e["height"]]
    return min(xs) - PAD, min(ys) - PAD, max(xs) + PAD, max(ys) + PAD


def render_svg(source):
    els = drawable(source)
    x0, y0, x1, y1 = bounds(els)
    body = []
    for e in els:
        r = _rng(e["id"])
        if e["type"] == "arrow":
            body.append(_arrow(e, r))
        elif e["type"] == "text":
            size = e.get("fontSize", 20)
            body.append(_text(e["x"], e["y"] + size * LINE_H / 2, e["text"], size, e.get("strokeColor", "#1e1e1e"),
                              anchor="start"))
        else:
            body.append(_shape(e, r))
    w, h = x1 - x0, y1 - y0
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.0f} {y0:.0f} {w:.0f} {h:.0f}" '
            f'width="{w:.0f}" height="{h:.0f}" role="img">'
            f'<rect x="{x0:.0f}" y="{y0:.0f}" width="{w:.0f}" height="{h:.0f}" fill="#ffffff"/>'
            + "".join(body) + "</svg>\n")


def to_scene(source):
    """Native Excalidraw scene: labels become texts bound to their shape (containerId)."""
    out = []
    base = {"angle": 0, "strokeColor": "#1e1e1e", "backgroundColor": "transparent", "fillStyle": "solid",
            "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1, "opacity": 100, "groupIds": [],
            "frameId": None, "roundness": None, "isDeleted": False, "boundElements": [], "link": None,
            "locked": False, "version": 1, "updated": 1}

    def text_el(tid, x, y, w, h, text, size, container=None, color="#1e1e1e"):
        return dict(base, id=tid, type="text", x=x, y=y, width=w, height=h, text=text, originalText=text,
                    fontSize=size, fontFamily=EXCALIFONT, textAlign="center" if container else "left",
                    verticalAlign="middle" if container else "top", containerId=container, lineHeight=LINE_H,
                    autoResize=True, strokeColor=color, seed=_rng(tid).randint(1, 2**31), versionNonce=1)

    for e in drawable(source):
        el = dict(base, **{k: v for k, v in e.items() if k != "label"})
        el["seed"] = _rng(e["id"]).randint(1, 2**31)
        el["versionNonce"] = 1
        if e["type"] == "text":
            el = text_el(e["id"], e["x"], e["y"], text_width(e["text"], e.get("fontSize", 20)),
                         e.get("fontSize", 20) * LINE_H, e["text"], e.get("fontSize", 20),
                         color=e.get("strokeColor", "#1e1e1e"))
            out.append(el)
            continue
        if e["type"] == "arrow":
            el.setdefault("startArrowhead", None)
            el.setdefault("endArrowhead", "arrow")
            el.update(startBinding=None, endBinding=None, lastCommittedPoint=None, elbowed=False)
        label = e.get("label")
        if label:
            tid = f"{e['id']}-label"
            size = label.get("fontSize", 20)
            lines = label["text"].split("\n")
            tw, th = text_width(label["text"], size), len(lines) * size * LINE_H
            if e["type"] == "arrow":
                p = e["points"][len(e["points"]) // 2]
                cx, cy = e["x"] + p[0], e["y"] + p[1]
            else:
                cx, cy = e["x"] + e["width"] / 2, e["y"] + e["height"] / 2
            el["boundElements"] = [{"type": "text", "id": tid}]
            out.append(el)
            out.append(text_el(tid, cx - tw / 2, cy - th / 2, tw, th, label["text"], size, container=e["id"]))
        else:
            out.append(el)
    scene = {"type": "excalidraw", "version": 2, "source": "Belayline (scripts/diagrams/render.py)",
             "elements": out, "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None}, "files": {}}
    return json.dumps(scene, ensure_ascii=False, indent=1) + "\n"


def scene_hash(scene):
    # LF only, as written by write_lf(): the same hash on every OS
    return hashlib.sha256(scene.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def write_lf(path, text):
    """Writes with LF line endings on every OS (write_text would write CRLF on Windows)."""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def body_hash(svg):
    """Hash of an exported SVG without its stamp: the stamp is the only part not written by Excalidraw."""
    return hashlib.sha256(ANY_STAMP.sub("", svg, count=1).encode("utf-8")).hexdigest()


def svg_is_current(svg, source):
    """An exported SVG is current if it was exported from the scene the source produces; a built-in one if it is
    the drawing of the source."""
    if svg is None:
        return False
    if ANY_STAMP.search(svg):
        stamp = STAMP.search(svg)
        return bool(stamp) and stamp.group(1) == scene_hash(to_scene(source)) and stamp.group(2) == body_hash(svg)
    return svg == render_svg(source)


def stamp(svg, scene):
    """Stamps an Excalidraw export: the body ends with one newline, the stamp goes right after the first `>` (the end
    of the `<svg ...>` tag), and carries the hash of the scene and of the body (the SVG without the stamp)."""
    body = svg if svg.endswith("\n") else svg + "\n"
    end = body.index(">") + 1
    return (f"{body[:end]}<!-- belayline-scene-sha256:{scene_hash(scene)} "
            f"svg-sha256:{hashlib.sha256(body.encode('utf-8')).hexdigest()} -->{body[end:]}")


def stamp_refusal(svg, source, scene=None):
    """Why `svg` cannot be stamped as the Excalidraw export of the scene `source` produces (or of `scene`, the text
    of a scene-only diagram); None if it can."""
    scene = to_scene(source) if scene is None else scene
    if svg is None:
        return "not found: export it from Excalidraw and save it under this name first"
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as e:
        return f"not a well-formed SVG ({e})"
    if root.tag != "{http://www.w3.org/2000/svg}svg":
        return f"not an SVG (root element {root.tag})"
    if EXCALIDRAW_MARKER not in svg:
        return f"not an Excalidraw export (no {EXCALIDRAW_MARKER} marker)"
    if ANY_STAMP.search(svg):
        found = STAMP.search(svg)
        if not found:
            return "carries a malformed stamp"
        if found.group(1) != scene_hash(scene):
            return "already stamped for another scene: export it again from the current scene"
        if found.group(2) != body_hash(svg):
            return "stamped, then edited: export it again from the current scene"
    return None


def scene_only_gap(ddir, name, shown):
    """A scene-only diagram (<name>.excalidraw with no <name>.json: drawn in Excalidraw, the scene is the source):
    its SVG must be the stamped Excalidraw export of that very scene. Returns the problem, or None."""
    scene_path, svg_path = ddir / f"{name}.excalidraw", ddir / f"{name}.svg"
    scene = scene_path.read_text(encoding="utf-8")
    svg = svg_path.read_text(encoding="utf-8") if svg_path.exists() else None
    found = STAMP.search(svg) if svg else None
    if found and found.group(1) == scene_hash(scene) and found.group(2) == body_hash(svg):
        return None
    return (f"{shown(svg_path)}: not the stamped Excalidraw export of {name}.excalidraw (scene-only diagram: export "
            f"it from Excalidraw as {name}.svg, then run render.py --stamp {name})")


def stale_export(path, name):
    return (f"{path}: Excalidraw export of an older scene. Either export it again from {name}.excalidraw "
            f"(excalidraw.com → Export image → SVG, saved as {name}.svg) and run render.py --stamp {name}, "
            f"or draw it with the built-in renderer: render.py --engine builtin {name}")


def run_stamp(ddir, name, shown):
    """--stamp: writes the stamp of docs/diagrams/<name>.svg, or refuses with the reason; nothing written then."""
    src_path, scene_path, svg_path = (ddir / f"{name}{ext}" for ext in (".json", ".excalidraw", ".svg"))
    if not src_path.is_file() and not scene_path.is_file():
        return [f"{name}: source {shown(src_path)} not found"]
    if src_path.is_file():
        source = json.loads(src_path.read_text(encoding="utf-8"))
        bad = invalid(source)
        if bad:
            return [f"{name}: {b}" for b in bad]
        scene = to_scene(source)
        if not scene_path.is_file() or scene_path.read_text(encoding="utf-8") != scene:
            return [f"{shown(scene_path)}: not up to date: run render.py first, then export from the new scene"]
    else:   # scene-only diagram: the .excalidraw file is the source
        source, scene = None, scene_path.read_text(encoding="utf-8")
    try:
        svg = svg_path.read_text(encoding="utf-8") if svg_path.exists() else None
    except (OSError, UnicodeDecodeError) as e:
        return [f"{shown(svg_path)}: not an SVG ({e})"]
    refusal = stamp_refusal(svg, source, scene)
    if refusal:
        return [f"{shown(svg_path)}: {refusal}; nothing written"]
    if STAMP.search(svg):
        print(f"✔ {shown(svg_path)} (already stamped for this scene)")
        return []
    write_lf(svg_path, stamp(svg, scene))
    print(f"✔ {shown(svg_path)} (Excalidraw export, stamped)")
    return []


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--engine", choices=("auto", "builtin"), default="auto")
    ap.add_argument("--stamp", metavar="NAME")
    ap.add_argument("--dir", type=pathlib.Path)
    ap.add_argument("names", nargs="*")
    a = ap.parse_args()
    cwd = pathlib.Path.cwd() / "docs" / "diagrams"
    ddir = a.dir or (cwd if cwd.is_dir() else DIR)
    shown = lambda path: path.relative_to(ROOT) if path.is_relative_to(ROOT) else path  # noqa: E731
    if a.stamp:
        problems = run_stamp(ddir, a.stamp, shown)
        for p in problems:
            print(f"✘ {p}")
        return 1 if problems else 0
    names = a.names or sorted({p.stem for p in ddir.glob("*.json")} | {p.stem for p in ddir.glob("*.excalidraw")})
    problems = []
    for name in names:
        if not (ddir / f"{name}.json").is_file():
            if (ddir / f"{name}.excalidraw").is_file():   # scene-only: nothing to render, the export must match
                gap = scene_only_gap(ddir, name, shown)
                if gap:
                    problems.append(gap)
                continue
            problems.append(f"{name}: source {shown(ddir / (name + '.json'))} not found")
            continue
        source = json.loads((ddir / f"{name}.json").read_text(encoding="utf-8"))
        bad = invalid(source)
        if bad:
            problems += [f"{name}: {b}" for b in bad]
            continue
        problems += [f"{name}: {o}" for o in overflows(source)]
        scene_path, svg_path = ddir / f"{name}.excalidraw", ddir / f"{name}.svg"
        scene = to_scene(source)
        current_scene = scene_path.read_text(encoding="utf-8") if scene_path.exists() else None
        current_svg = svg_path.read_text(encoding="utf-8") if svg_path.exists() else None
        svg_ok = svg_is_current(current_svg, source)
        exported = current_svg is not None and bool(ANY_STAMP.search(current_svg))
        if a.check:
            if current_scene != scene:
                problems.append(f"{shown(scene_path)}: not up to date (run the diagram rendering again without --check)")
            if not svg_ok:
                problems.append(stale_export(shown(svg_path), name) if exported else
                                f"{shown(svg_path)}: not up to date (run the diagram rendering again without --check)")
            continue
        if current_scene != scene:
            write_lf(scene_path, scene)
            print(f"✔ {shown(scene_path)}")
        if exported and a.engine != "builtin":
            if not svg_ok:
                problems.append(stale_export(shown(svg_path), name))
        elif not svg_ok or exported:
            write_lf(svg_path, render_svg(source))
            print(f"✔ {shown(svg_path)} (built-in renderer)")
    for p in problems:
        print(f"✘ {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

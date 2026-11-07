#!/usr/bin/env python3
"""Rend les schémas du README depuis leur source Excalidraw « squelette » (bibliothèque standard seulement).

  docs/diagrams/<nom>.json        source : éléments Excalidraw (rectangle, ellipse, texte, flèche, `label` intégré)
  → docs/diagrams/<nom>.excalidraw  scène native, à ouvrir et modifier sur excalidraw.com (Fichier → Ouvrir)
  → docs/diagrams/<nom>.svg         image du README, au trait « dessiné à la main », déterministe

Usage : render.py [--check] [nom…]   --check : sort en 1 si un SVG ou une scène n'est pas à jour, ou si un texte déborde.
Modifier un schéma : éditer le .json (ou le .excalidraw puis reporter), relancer render.py, commiter les trois.
"""
import argparse
import hashlib
import json
import math
import pathlib
import random
import sys
from xml.sax.saxutils import escape

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIR = ROOT / "docs" / "diagrams"
FONT = "Segoe UI, Helvetica, Arial, sans-serif"
CHAR_W = 0.52      # largeur moyenne d'un caractère, en em (estimation pour la police ci-dessus)
LINE_H = 1.25
PAD = 24


def _rng(eid):
    return random.Random(int(hashlib.sha256(eid.encode()).hexdigest()[:8], 16))


def _jitter_line(r, x1, y1, x2, y2, rough):
    """Segment légèrement tremblé : deux passes décalées, comme le trait d'Excalidraw (roughness 1)."""
    out = []
    for _ in range(2):
        j = lambda: r.uniform(-rough, rough)  # noqa: E731
        mx, my = (x1 + x2) / 2 + j() * 1.5, (y1 + y2) / 2 + j() * 1.5
        out.append(f"M{x1 + j():.1f} {y1 + j():.1f} Q{mx:.1f} {my:.1f} {x2 + j():.1f} {y2 + j():.1f}")
    return " ".join(out)


def text_width(text, size):
    return max((len(line) for line in text.split("\n")), default=0) * size * CHAR_W


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
    # `angle` pointe de la pointe vers le segment : les deux ailes s'en écartent de ±30°
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
        # Étiquette au milieu du plus long segment, sur fond blanc
        i = max(range(len(pts) - 1), key=lambda k: math.dist(pts[k], pts[k + 1]))
        mx, my = (pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2
        size = label.get("fontSize", 16)
        w, h = text_width(label["text"], size) + 12, size * LINE_H * len(label["text"].split("\n")) + 6
        parts.append(f'<rect x="{mx - w / 2:.1f}" y="{my - h / 2:.1f}" width="{w:.1f}" height="{h:.1f}" rx="4" '
                     f'fill="#ffffff"/>')
        parts.append(_text(mx, my, label["text"], size, color if color != "#1e1e1e" else "#1e1e1e"))
    return "".join(parts)


def drawable(source):
    return [e for e in source if e["type"] not in ("cameraUpdate", "delete", "restoreCheckpoint")]


def overflows(source):
    """Textes qui débordent de leur forme (estimation) : à corriger dans la source."""
    issues = []
    for e in drawable(source):
        label = e.get("label")
        if label and e["type"] in ("rectangle", "ellipse", "diamond"):
            size = label.get("fontSize", 20)
            need_w = text_width(label["text"], size) * (1.25 if e["type"] == "ellipse" else 1) + 20
            need_h = len(label["text"].split("\n")) * size * LINE_H + 12
            if need_w > e["width"] or need_h > e["height"]:
                issues.append(f"{e['id']} : « {label['text'].splitlines()[0]}… » déborde "
                              f"({need_w:.0f}×{need_h:.0f} pour {e['width']}×{e['height']})")
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
    """Scène Excalidraw native : les étiquettes deviennent des textes liés à leur forme (containerId)."""
    out = []
    base = {"angle": 0, "strokeColor": "#1e1e1e", "backgroundColor": "transparent", "fillStyle": "solid",
            "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1, "opacity": 100, "groupIds": [],
            "frameId": None, "roundness": None, "isDeleted": False, "boundElements": [], "link": None,
            "locked": False, "version": 1, "updated": 1}

    def text_el(tid, x, y, w, h, text, size, container=None, color="#1e1e1e"):
        return dict(base, id=tid, type="text", x=x, y=y, width=w, height=h, text=text, originalText=text,
                    fontSize=size, fontFamily=2, textAlign="center" if container else "left",
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
    scene = {"type": "excalidraw", "version": 2, "source": "agentic-harness (scripts/diagrams/render.py)",
             "elements": out, "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None}, "files": {}}
    return json.dumps(scene, ensure_ascii=False, indent=1) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("names", nargs="*")
    a = ap.parse_args()
    names = a.names or sorted(p.stem for p in DIR.glob("*.json"))
    problems = []
    for name in names:
        source = json.loads((DIR / f"{name}.json").read_text(encoding="utf-8"))
        problems += [f"{name} : {o}" for o in overflows(source)]
        outputs = {DIR / f"{name}.svg": render_svg(source), DIR / f"{name}.excalidraw": to_scene(source)}
        for path, content in outputs.items():
            current = path.read_text(encoding="utf-8") if path.exists() else None
            if a.check:
                if current != content:
                    problems.append(f"{path.relative_to(ROOT)} : pas à jour (lancer scripts/diagrams/render.py)")
            elif current != content:
                path.write_text(content, encoding="utf-8")
                print(f"✔ {path.relative_to(ROOT)}")
    for p in problems:
        print(f"✘ {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

"""Tests de scripts/diagrams/render.py : rendu déterministe, scène Excalidraw valide, débordements détectés."""
import importlib.util
import json
import pathlib
import unittest
import xml.dom.minidom

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("render", ROOT / "scripts" / "diagrams" / "render.py")
rd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rd)

BOX = {"type": "rectangle", "id": "b", "x": 0, "y": 0, "width": 200, "height": 80, "label": {"text": "Court", "fontSize": 20}}
ARROW = {"type": "arrow", "id": "a", "x": 200, "y": 40, "width": 100, "height": 0, "points": [[0, 0], [100, 0]],
         "label": {"text": "lien", "fontSize": 16}}


class RenderTests(unittest.TestCase):
    def test_svg_is_valid_xml_and_deterministic(self):
        src = [{"type": "cameraUpdate", "width": 800, "height": 600, "x": 0, "y": 0}, BOX, ARROW]
        first = rd.render_svg(src)
        xml.dom.minidom.parseString(first)
        self.assertEqual(first, rd.render_svg(src))
        self.assertIn(">Court<", first)

    def test_scene_binds_labels_to_their_container(self):
        scene = json.loads(rd.to_scene([BOX, ARROW]))
        self.assertEqual(scene["type"], "excalidraw")
        label = next(e for e in scene["elements"] if e["id"] == "b-label")
        box = next(e for e in scene["elements"] if e["id"] == "b")
        self.assertEqual((label["containerId"], box["boundElements"]), ("b", [{"type": "text", "id": "b-label"}]))

    def test_committed_scenes_are_up_to_date(self):
        for src in sorted((ROOT / "docs/diagrams").glob("*.json")):
            source = json.loads(src.read_text(encoding="utf-8"))
            self.assertEqual(src.with_suffix(".excalidraw").read_text(encoding="utf-8"), rd.to_scene(source), src.name)

    def test_unknown_name_is_reported_without_traceback(self):
        import subprocess
        import sys
        r = subprocess.run([sys.executable, str(ROOT / "scripts/diagrams/render.py"), "--check", "absent"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("absent", r.stdout)

    def test_overflow_is_reported(self):
        long = dict(BOX, label={"text": "un texte bien trop long pour cette boîte", "fontSize": 20})
        self.assertTrue(rd.overflows([long]))
        self.assertEqual(rd.overflows([BOX]), [])

    def test_committed_diagrams_are_up_to_date(self):
        for src in sorted((ROOT / "docs/diagrams").glob("*.json")):
            source = json.loads(src.read_text(encoding="utf-8"))
            self.assertEqual(rd.overflows(source), [], src.name)
            self.assertEqual((src.with_suffix(".svg")).read_text(encoding="utf-8"), rd.render_svg(source), src.name)


if __name__ == "__main__":
    unittest.main()

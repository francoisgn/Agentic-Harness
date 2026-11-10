"""Tests of scripts/diagrams/render.py: deterministic rendering, valid Excalidraw scene, overflows detected."""
import importlib.util
import json
import pathlib
import unittest
import xml.dom.minidom

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("render", ROOT / "scripts" / "diagrams" / "render.py")
rd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rd)

BOX = {"type": "rectangle", "id": "b", "x": 0, "y": 0, "width": 200, "height": 80, "label": {"text": "Short", "fontSize": 20}}
ARROW = {"type": "arrow", "id": "a", "x": 200, "y": 40, "width": 100, "height": 0, "points": [[0, 0], [100, 0]],
         "label": {"text": "link", "fontSize": 16}}


class RenderTests(unittest.TestCase):
    def test_svg_is_valid_xml_and_deterministic(self):
        src = [{"type": "cameraUpdate", "width": 800, "height": 600, "x": 0, "y": 0}, BOX, ARROW]
        first = rd.render_svg(src)
        xml.dom.minidom.parseString(first)
        self.assertEqual(first, rd.render_svg(src))
        self.assertIn(">Short<", first)

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

    def test_arrow_with_fewer_than_two_points_is_reported(self):
        bad = dict(ARROW, points=[[0, 0]])
        self.assertTrue(any("at least two points" in e for e in rd.invalid(bad and [bad])))

    def test_malformed_arrow_points_are_reported(self):
        for pts in ([[0, 0], [100]], [[0, 0], ["a", 1]], [[0, 0], 5], 5, "ab"):
            self.assertTrue(rd.invalid([dict(ARROW, points=pts)]), pts)

    def test_overflow_is_reported(self):
        long = dict(BOX, label={"text": "a text far too long for this box", "fontSize": 20})
        self.assertTrue(rd.overflows([long]))
        self.assertEqual(rd.overflows([BOX]), [])

    def test_committed_diagrams_are_up_to_date(self):
        for src in sorted((ROOT / "docs/diagrams").glob("*.json")):
            source = json.loads(src.read_text(encoding="utf-8"))
            self.assertEqual(rd.overflows(source), [], src.name)
            self.assertTrue(rd.svg_is_current(src.with_suffix(".svg").read_text(encoding="utf-8"), source), src.name)

    def test_exported_svg_is_checked_through_its_scene_hash(self):
        src = [BOX, ARROW]
        exported = f'<svg><!-- belayline-scene-sha256:{rd.scene_hash(rd.to_scene(src))} --></svg>\n'
        self.assertTrue(rd.svg_is_current(exported, src))
        moved = [dict(BOX, x=10), ARROW]
        self.assertFalse(rd.svg_is_current(exported, moved))
        self.assertTrue(rd.svg_is_current(rd.render_svg(src), src))
        self.assertFalse(rd.svg_is_current(rd.render_svg(src), moved))
        self.assertFalse(rd.svg_is_current(None, src))

    def test_scene_uses_excalifont_and_centres_arrow_labels_on_the_longest_segment(self):
        bent = dict(ARROW, points=[[0, 0], [0, 20], [200, 20]])
        scene = json.loads(rd.to_scene([BOX, bent]))
        self.assertTrue(all(e["fontFamily"] == rd.EXCALIFONT for e in scene["elements"] if e["type"] == "text"))
        label = next(e for e in scene["elements"] if e["id"] == "a-label")
        self.assertAlmostEqual(label["x"] + label["width"] / 2, 300)
        self.assertAlmostEqual(label["y"] + label["height"] / 2, 60)


if __name__ == "__main__":
    unittest.main()

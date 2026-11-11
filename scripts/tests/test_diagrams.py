"""Tests of scripts/diagrams/render.py: deterministic rendering, valid Excalidraw scene, overflows detected, stamping
of Excalidraw exports."""
import contextlib
import hashlib
import importlib.util
import io
import json
import pathlib
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock
import xml.dom.minidom

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("render", ROOT / "scripts" / "diagrams" / "render.py")
rd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rd)

BOX = {"type": "rectangle", "id": "b", "x": 0, "y": 0, "width": 200, "height": 80, "label": {"text": "Short", "fontSize": 20}}
EXPORT = ('<svg version="1.1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><!-- svg-source:excalidraw -->'
          '<text>Short</text></svg>')
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

    @staticmethod
    def exported(src, body=None):
        """An Excalidraw export stamped as the stamp is defined (written independently of render.stamp)."""
        body = body or EXPORT
        body += "\n"
        stamp = (f"<!-- belayline-scene-sha256:{rd.scene_hash(rd.to_scene(src))} "
                 f"svg-sha256:{hashlib.sha256(body.encode()).hexdigest()} -->")
        end = body.index(">") + 1
        return body[:end] + stamp + body[end:]

    def test_exported_svg_is_checked_through_its_scene_and_body_hashes(self):
        src = [BOX, ARROW]
        svg = self.exported(src)
        self.assertTrue(rd.svg_is_current(svg, src))
        self.assertFalse(rd.svg_is_current(svg, [dict(BOX, x=10), ARROW]), "source moved")
        self.assertFalse(rd.svg_is_current(svg.replace(">Short<", ">Edited<"), src), "body edited by hand")
        bare = f"<svg><!-- belayline-scene-sha256:{rd.scene_hash(rd.to_scene(src))} --></svg>\n"
        self.assertFalse(rd.svg_is_current(bare, src), "stamp without a body hash")
        self.assertTrue(rd.svg_is_current(rd.render_svg(src), src))
        self.assertFalse(rd.svg_is_current(rd.render_svg(src), [dict(BOX, x=10), ARROW]))
        self.assertFalse(rd.svg_is_current(None, src))

    def test_scene_texts_use_excalifont(self):
        scene = json.loads(rd.to_scene([BOX, ARROW, {"type": "text", "id": "t", "x": 0, "y": 0, "text": "T"}]))
        self.assertEqual({e["fontFamily"] for e in scene["elements"] if e["type"] == "text"}, {5})

    def test_overflow_uses_the_excalifont_width(self):
        # 20 characters at 20 px: 228 px with the built-in estimate, 252 px in Excalifont
        tight = dict(BOX, width=240, label={"text": "x" * 20, "fontSize": 20})
        self.assertTrue(rd.overflows([tight]))
        self.assertEqual(rd.overflows([dict(tight, width=260)]), [])


class EngineTests(unittest.TestCase):
    """main(): built-in renderer, Excalidraw exports kept, --stamp, staleness through the command line."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        (self.tmp / "d.json").write_text(json.dumps([BOX, ARROW]), encoding="utf-8")

    def run_main(self, *args):
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["render.py", "--dir", str(self.tmp), *args]), \
                contextlib.redirect_stdout(out):
            rc = rd.main()
        return rc, out.getvalue()

    def svg(self):
        path = self.tmp / "d.svg"
        return path.read_bytes() if path.exists() else None

    def test_the_svg_is_drawn_and_checks(self):
        rc, out = self.run_main()
        self.assertEqual(rc, 0)
        self.assertEqual((self.tmp / "d.svg").read_text(encoding="utf-8"), rd.render_svg([BOX, ARROW]))
        self.assertEqual(self.run_main("--check")[0], 0)

    def test_a_changed_source_makes_check_fail(self):
        self.run_main()
        (self.tmp / "d.json").write_text(json.dumps([dict(BOX, x=10), ARROW]), encoding="utf-8")
        rc, out = self.run_main("--check")
        self.assertEqual(rc, 1)
        self.assertIn("d.svg: not up to date", out)
        self.assertIn("d.excalidraw: not up to date", out)

    def test_files_are_written_with_lf_and_crlf_scenes_hash_the_same(self):
        self.run_main()
        self.assertNotIn(b"\r\n", (self.tmp / "d.excalidraw").read_bytes())
        scene = rd.to_scene([BOX, ARROW])
        self.assertEqual(rd.scene_hash(scene.replace("\n", "\r\n")), rd.scene_hash(scene))

    def export(self, text=EXPORT):
        """The scene is rendered, then the author saves an Excalidraw export as d.svg."""
        self.run_main()
        (self.tmp / "d.svg").write_text(text, encoding="utf-8")

    def test_stamp_accepts_an_excalidraw_export_that_then_checks(self):
        self.export()
        rc, out = self.run_main("--stamp", "d")
        self.assertEqual(rc, 0, out)
        svg = (self.tmp / "d.svg").read_text(encoding="utf-8")
        self.assertEqual(svg, RenderTests.exported([BOX, ARROW]))
        self.assertEqual(self.run_main("--check")[0], 0)
        self.assertEqual(self.run_main()[0], 0)
        self.assertEqual((self.tmp / "d.svg").read_text(encoding="utf-8"), svg, "a current export is kept")
        self.assertEqual(self.run_main("--stamp", "d"), (0, f"✔ {self.tmp / 'd.svg'} (already stamped for this scene)\n"))

    def test_stamp_reproduces_the_committed_exports_byte_for_byte(self):
        # Diagrams with a .json source; scene-only ones (no .json) are covered by SceneOnlyTests
        committed = [p for p in sorted((ROOT / "docs/diagrams").glob("*.svg"))
                     if rd.STAMP.search(p.read_text("utf-8")) and p.with_suffix(".json").is_file()]
        self.assertTrue(committed)
        for svg in committed:
            for ext in (".json", ".excalidraw"):
                shutil.copy(svg.with_suffix(ext), self.tmp / f"x{ext}")
            (self.tmp / "x.svg").write_text(rd.ANY_STAMP.sub("", svg.read_text("utf-8"), count=1), encoding="utf-8")
            rc, out = self.run_main("--stamp", "x")
            self.assertEqual(rc, 0, out)
            self.assertEqual((self.tmp / "x.svg").read_bytes(), svg.read_bytes(), svg.name)

    def assert_refused(self, reason, *args):
        before = self.svg()
        rc, out = self.run_main("--stamp", "d", *args)
        self.assertEqual(rc, 1, out)
        self.assertIn(reason, out)
        self.assertIn("✘", out)
        self.assertEqual(self.svg(), before, "nothing written")

    def test_stamp_refuses_what_is_not_an_export_of_the_current_scene(self):
        self.run_main()
        (self.tmp / "d.svg").unlink()
        self.assert_refused("not found")
        for text, reason in (("not svg at all", "not a well-formed SVG"),
                             ('<html><!-- svg-source:excalidraw --></html>', "not an SVG"),
                             (rd.render_svg([BOX, ARROW]), "not an Excalidraw export"),
                             (RenderTests.exported([dict(BOX, x=10), ARROW]), "already stamped for another scene"),
                             (EXPORT.replace("-->", "--><!-- belayline-scene-sha256:x -->", 1), "malformed stamp"),
                             (RenderTests.exported([BOX, ARROW]).replace(">Short<", ">Edited<"), "edited")):
            (self.tmp / "d.svg").write_text(text, encoding="utf-8")
            self.assert_refused(reason)
        (self.tmp / "d.svg").write_text(EXPORT, encoding="utf-8")
        (self.tmp / "d.json").write_text(json.dumps([dict(BOX, x=10), ARROW]), encoding="utf-8")
        self.assert_refused("d.excalidraw: not up to date")

    def test_a_stale_export_fails_check_with_both_ways_out_and_is_never_overwritten_silently(self):
        self.export()
        self.run_main("--stamp", "d")
        stamped = self.svg()
        (self.tmp / "d.json").write_text(json.dumps([dict(BOX, x=10), ARROW]), encoding="utf-8")
        for args in (("--check",), ()):
            rc, out = self.run_main(*args)
            self.assertEqual(rc, 1, args)
            self.assertIn("Excalidraw export of an older scene", out)
            self.assertIn("render.py --stamp d", out)
            self.assertIn("render.py --engine builtin d", out)
            self.assertEqual(self.svg(), stamped, args)
        rc, out = self.run_main("--engine", "builtin")
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.svg().decode("utf-8"), rd.render_svg([dict(BOX, x=10), ARROW]))

    def test_no_exporter_tooling_is_mentioned(self):
        text = (ROOT / "scripts/diagrams/render.py").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\bnpm\b|\bnpx\b|\bnode\b|playwright|export-svg", text, re.I))
        self.assertEqual(sorted(p.name for p in (ROOT / "scripts/diagrams").iterdir() if p.name != "__pycache__"),
                         ["render.py"])



class SceneOnlyTests(unittest.TestCase):
    """A diagram drawn in Excalidraw: <name>.excalidraw is the source, <name>.svg its stamped export, no .json."""
    NAME = "ai-stack"

    def copy(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = pathlib.Path(tmp.name)
        for ext in (".excalidraw", ".svg"):
            shutil.copy(ROOT / "docs/diagrams" / f"{self.NAME}{ext}", d / f"{self.NAME}{ext}")
        return d

    def test_committed_scene_only_diagram_has_no_json_and_verifies(self):
        self.assertFalse((ROOT / "docs/diagrams" / f"{self.NAME}.json").exists())
        self.assertIsNone(rd.scene_only_gap(ROOT / "docs/diagrams", self.NAME, str))

    def test_edited_scene_makes_the_export_stale(self):
        d = self.copy()
        scene = d / f"{self.NAME}.excalidraw"
        scene.write_text(scene.read_text(encoding="utf-8").replace("AI product", "AI products", 1), encoding="utf-8")
        self.assertIn("--stamp", rd.scene_only_gap(d, self.NAME, str))

    def test_missing_or_unstamped_export_is_reported(self):
        d = self.copy()
        svg = d / f"{self.NAME}.svg"
        svg.write_text(rd.ANY_STAMP.sub("", svg.read_text(encoding="utf-8"), count=1), encoding="utf-8")
        self.assertIsNotNone(rd.scene_only_gap(d, self.NAME, str))
        svg.unlink()
        self.assertIsNotNone(rd.scene_only_gap(d, self.NAME, str))

    def test_stamp_of_a_scene_only_export_gives_the_committed_file_back(self):
        d = self.copy()
        svg = d / f"{self.NAME}.svg"
        committed = svg.read_text(encoding="utf-8")
        svg.write_text(rd.ANY_STAMP.sub("", committed, count=1), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(rd.run_stamp(d, self.NAME, str), [])
        self.assertEqual(svg.read_text(encoding="utf-8"), committed)

    def test_stamp_refuses_an_export_of_another_scene(self):
        d = self.copy()
        scene = d / f"{self.NAME}.excalidraw"
        scene.write_text(scene.read_text(encoding="utf-8").replace("AI product", "AI products", 1), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            problems = rd.run_stamp(d, self.NAME, str)
        self.assertTrue(problems and "another scene" in problems[0])


if __name__ == "__main__":
    unittest.main()

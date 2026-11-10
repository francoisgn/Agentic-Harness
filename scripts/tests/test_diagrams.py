"""Tests of scripts/diagrams/render.py: deterministic rendering, valid Excalidraw scene, overflows detected."""
import contextlib
import hashlib
import importlib.util
import io
import json
import pathlib
import shutil
import subprocess
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
    def exported(src, body='<svg viewBox="0 0 10 10"><text>Short</text></svg>'):
        """An SVG stamped the way export-svg.cjs stamps it."""
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
    """main(): built-in fallback, required export, staleness through the command line."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        (self.tmp / "d.json").write_text(json.dumps([BOX, ARROW]), encoding="utf-8")

    def run_main(self, *args, available=False, export_rc=None):
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, export_rc)

        out = io.StringIO()
        with mock.patch.object(rd, "exporter_available", return_value=available), \
                mock.patch.object(rd.subprocess, "run", side_effect=fake_run), \
                mock.patch.object(sys, "argv", ["render.py", "--dir", str(self.tmp), *args]), \
                contextlib.redirect_stdout(out):
            rc = rd.main()
        return rc, out.getvalue(), calls

    def test_without_the_exporter_the_svg_is_drawn_and_checks(self):
        rc, out, calls = self.run_main()
        self.assertEqual((rc, calls), (0, []))
        self.assertEqual((self.tmp / "d.svg").read_text(encoding="utf-8"), rd.render_svg([BOX, ARROW]))
        self.assertEqual(self.run_main("--check")[0], 0)

    def test_a_failed_export_falls_back_to_the_built_in_renderer(self):
        rc, out, calls = self.run_main(available=True, export_rc=1)
        self.assertEqual(rc, 0)
        self.assertEqual(len(calls), 1)
        self.assertIn("built-in renderer used", out)
        self.assertEqual(self.run_main("--check")[0], 0)

    def test_a_required_export_that_fails_or_is_missing_exits_1(self):
        self.assertEqual(self.run_main("--engine", "excalidraw", available=True, export_rc=1)[0], 1)
        rc, out, _ = self.run_main("--engine", "excalidraw")
        self.assertEqual(rc, 1)
        self.assertIn("not available", out)

    def test_a_changed_source_makes_check_fail(self):
        self.run_main()
        (self.tmp / "d.json").write_text(json.dumps([dict(BOX, x=10), ARROW]), encoding="utf-8")
        rc, out, _ = self.run_main("--check")
        self.assertEqual(rc, 1)
        self.assertIn("d.svg: not up to date", out)
        self.assertIn("d.excalidraw: not up to date", out)

    def fake_export(self, write=True):
        """A run of export-svg.cjs that writes the stamped SVG of each scene it is given."""
        def run(cmd, **kw):
            if write:
                for scene in cmd[2:]:
                    src = json.loads((self.tmp / "d.json").read_text(encoding="utf-8"))
                    pathlib.Path(scene).with_suffix(".svg").write_text(RenderTests.exported(src), encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0)
        return run

    def run_export(self, *args, write=True):
        out = io.StringIO()
        with mock.patch.object(rd, "exporter_available", return_value=True), \
                mock.patch.object(rd.subprocess, "run", side_effect=self.fake_export(write)), \
                mock.patch.object(sys, "argv", ["render.py", "--dir", str(self.tmp), *args]), \
                contextlib.redirect_stdout(out):
            return rd.main(), out.getvalue()

    def test_a_successful_export_is_kept_and_checks(self):
        rc, out = self.run_export()
        self.assertEqual(rc, 0)
        self.assertIn("(Excalidraw)", out)
        self.assertIn("belayline-scene-sha256", (self.tmp / "d.svg").read_text(encoding="utf-8"))
        self.assertEqual(self.run_main("--check")[0], 0)

    def test_required_export_replaces_a_built_in_svg(self):
        self.run_main()
        self.assertEqual(self.run_export()[0], 0)  # auto keeps a current built-in SVG
        self.assertNotIn("belayline-scene-sha256", (self.tmp / "d.svg").read_text(encoding="utf-8"))
        rc, out = self.run_export("--engine", "excalidraw")
        self.assertEqual(rc, 0)
        self.assertIn("belayline-scene-sha256", (self.tmp / "d.svg").read_text(encoding="utf-8"))

    def test_an_export_that_writes_nothing_is_reported(self):
        rc, out = self.run_export("--engine", "excalidraw", write=False)
        self.assertEqual(rc, 1)
        self.assertIn("did not produce an up-to-date SVG", out)
        rc, out = self.run_export(write=False)
        self.assertEqual(rc, 0)
        self.assertIn("(built-in renderer)", out)

    def test_files_are_written_with_lf_and_crlf_scenes_hash_the_same(self):
        self.run_main()
        self.assertNotIn(b"\r\n", (self.tmp / "d.excalidraw").read_bytes())
        scene = rd.to_scene([BOX, ARROW])
        self.assertEqual(rd.scene_hash(scene.replace("\n", "\r\n")), rd.scene_hash(scene))

    def test_no_install_hint_where_the_exporter_is_not_shipped(self):
        with mock.patch.object(rd, "EXPORTER", self.tmp / "absent.cjs"):
            self.assertEqual(rd.export_hint(), "")
            rc, out, _ = self.run_main()
        self.assertEqual(rc, 0)
        self.assertNotIn("npm", out)
        self.assertIn("playwright install chromium", rd.export_hint())


if __name__ == "__main__":
    unittest.main()

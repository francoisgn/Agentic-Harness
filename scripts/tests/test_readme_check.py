"""Tests of scripts/readme-check.py: every point of the standard is detected, adjustable and can be switched off."""
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("readme_check", ROOT / "scripts" / "readme-check.py")
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)

GOOD = """# Project

![Swift](https://img.shields.io/badge/Swift-6.2-F05138?logo=swift&logoColor=white)

> One sentence.

## Architecture
![Architecture: three layers](docs/diagrams/architecture.svg)

## Progress
<!-- harness:begin progress -->
| Lot | State |
|---|---|
| LOT-001 | 🟢 delivered |
<!-- harness:end progress -->

## Getting started
```bash
make test
```

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md).
"""

# The same README as a consumer project written in French would have it: French headings stay accepted.
FRENCH = GOOD.replace("## Getting started", "## Démarrage").replace("## Contributing", "## Contribuer")


class ReadmeCheckTests(unittest.TestCase):
    def project(self, readme=GOOD, config=None, lots=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = pathlib.Path(tmp.name)
        (root / "docs/diagrams").mkdir(parents=True)
        (root / "docs/diagrams/architecture.svg").write_text("<svg/>", encoding="utf-8")
        (root / "docs/diagrams/architecture.excalidraw").write_text("{}", encoding="utf-8")
        (root / "CONTRIBUTING.md").write_text("# Contributing\n", encoding="utf-8")
        if readme is not None:
            (root / "README.md").write_text(readme, encoding="utf-8")
        if config is not None:
            (root / ".harness").mkdir()
            (root / ".harness/config.json").write_text(json.dumps(config), encoding="utf-8")
        if lots is not None:
            (root / "docs/LOTS.md").write_text(lots, encoding="utf-8")
        return root

    def test_compliant_readme_passes(self):
        self.assertEqual(rc.check(self.project()), [])

    def test_missing_readme_is_reported(self):
        self.assertTrue(any("README.md: missing" in e for e in rc.check(self.project(readme=None))))

    def test_badge_must_sit_in_the_header(self):
        moved = GOOD.replace("![Swift](https://img.shields.io/badge/Swift-6.2-F05138?logo=swift&logoColor=white)\n", "") \
            + "\n![Swift](https://img.shields.io/badge/Swift-6.2-F05138)\n"
        self.assertTrue(any("badge" in e for e in rc.check(self.project(moved))))

    def test_missing_image_file_and_alt_are_reported(self):
        errors = rc.check(self.project(GOOD + "\n![](docs/images/absent.png)\n"))
        self.assertTrue(any("not found" in e for e in errors))
        self.assertTrue(any("alternative text" in e for e in errors))

    def test_image_outside_the_repository_is_reported(self):
        self.assertTrue(any("not found" in e for e in rc.check(self.project(GOOD + "\n![x](../../etc/passwd)\n"))))

    def test_architecture_needs_its_excalidraw_source(self):
        root = self.project()
        (root / "docs/diagrams/architecture.excalidraw").unlink()
        self.assertTrue(any("Excalidraw" in e for e in rc.check(root)))
        (root / ".harness").mkdir()
        (root / ".harness/config.json").write_text('{"readme": {"architecture": "any"}}', encoding="utf-8")
        self.assertEqual(rc.check(root), [])

    def test_progress_block_needs_markers_and_a_table(self):
        no_block = GOOD.replace("<!-- harness:begin progress -->\n", "")
        self.assertTrue(any("progress block missing" in e for e in rc.check(self.project(no_block))))
        empty = GOOD.replace("| LOT-001 | 🟢 delivered |\n", "")
        self.assertTrue(any("without a table" in e for e in rc.check(self.project(empty))))

    def test_former_progress_markers_are_not_recognised(self):
        old = GOOD.replace("harness:begin progress", "harness:begin avancement") \
                  .replace("harness:end progress", "harness:end avancement")
        errors = rc.check(self.project(old))
        self.assertEqual(len(errors), 1)
        self.assertIn("<!-- harness:begin progress -->", errors[0])

    def test_english_headings_are_detected(self):
        for heading in ("Installation", "Quick start", "Quickstart", "Getting started", "Usage", "Using the tool"):
            readme = GOOD.replace("## Getting started", "## " + heading)
            self.assertEqual(rc.check(self.project(readme)), [], heading)
        errors = rc.check(self.project(GOOD.replace("## Getting started", "## Run")))
        self.assertTrue(any("getting-started" in e for e in errors))

    def test_french_headings_stay_accepted(self):
        self.assertEqual(rc.check(self.project(FRENCH)), [])
        self.assertEqual(rc.check(self.project(FRENCH.replace("## Démarrage", "## Utilisation"))), [])

    def test_every_planned_lot_appears_in_the_progress_block(self):
        errors = rc.check(self.project(lots="| LOT-001 | engine |\n| LOT-002 | screen |\n"))
        self.assertEqual([e for e in errors if "LOT-002" in e and "LOT-001" not in e.split(":")[-1]], errors)
        self.assertEqual(len(errors), 1)

    def test_contributing_needs_section_file_and_link(self):
        self.assertTrue(any("Contributing" in e for e in rc.check(self.project(GOOD.split("## Contributing")[0]))))
        root = self.project()
        (root / "CONTRIBUTING.md").unlink()
        self.assertTrue(any("CONTRIBUTING.md: missing" in e for e in rc.check(root)))

    def test_each_point_can_be_switched_off(self):
        bare = "# Project\n\nNothing else.\n"
        off = {"badges": False, "image": False, "architecture": False, "progress": False, "quickstart": False,
               "contributing": False}
        self.assertEqual(rc.check(self.project(bare, {"readme": off})), [])
        self.assertEqual(rc.check(self.project(bare, {"readme": False})), [])
        self.assertEqual(len(rc.check(self.project(bare))), 6)

    def test_unknown_setting_is_refused(self):
        with self.assertRaises(ValueError):
            rc.check(self.project(config={"readme": {"badge": False}}))

    def test_images_in_code_blocks_are_ignored(self):
        fenced = GOOD + "\n```markdown\n![](docs/images/example.png)\n```\n"
        self.assertEqual(rc.check(self.project(fenced)), [])

    def test_harness_readme_and_seeded_template_meet_the_standard(self):
        self.assertEqual(rc.check(ROOT), [])
        root = self.project((ROOT / "templates/README.md.template").read_text(encoding="utf-8"))
        (root / "docs/LOTS.md").write_text("LOT-001\n", encoding="utf-8")
        self.assertEqual(rc.check(root), [])


if __name__ == "__main__":
    unittest.main()

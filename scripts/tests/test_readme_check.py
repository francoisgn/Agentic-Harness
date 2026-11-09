"""Tests de scripts/readme-check.py : chaque point du standard est détecté, réglable et coupable."""
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("readme_check", ROOT / "scripts" / "readme-check.py")
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)

GOOD = """# Projet

![Swift](https://img.shields.io/badge/Swift-6.2-F05138?logo=swift&logoColor=white)

> Une phrase.

## Architecture
![Architecture : trois couches](docs/diagrams/architecture.svg)

## Avancement
<!-- harness:begin avancement -->
| Lot | État |
|---|---|
| LOT-001 | 🟢 livré |
<!-- harness:end avancement -->

## Démarrage
```bash
make test
```

## Contribuer
Voir [CONTRIBUTING.md](CONTRIBUTING.md).
"""


class ReadmeCheckTests(unittest.TestCase):
    def project(self, readme=GOOD, config=None, lots=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = pathlib.Path(tmp.name)
        (root / "docs/diagrams").mkdir(parents=True)
        (root / "docs/diagrams/architecture.svg").write_text("<svg/>", encoding="utf-8")
        (root / "docs/diagrams/architecture.excalidraw").write_text("{}", encoding="utf-8")
        (root / "CONTRIBUTING.md").write_text("# Contribuer\n", encoding="utf-8")
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
        self.assertTrue(any("absent" in e for e in rc.check(self.project(readme=None))))

    def test_badge_must_sit_in_the_header(self):
        moved = GOOD.replace("![Swift](https://img.shields.io/badge/Swift-6.2-F05138?logo=swift&logoColor=white)\n", "") \
            + "\n![Swift](https://img.shields.io/badge/Swift-6.2-F05138)\n"
        self.assertTrue(any("tuile" in e for e in rc.check(self.project(moved))))

    def test_missing_image_file_and_alt_are_reported(self):
        errors = rc.check(self.project(GOOD + "\n![](docs/images/absente.png)\n"))
        self.assertTrue(any("introuvable" in e for e in errors))
        self.assertTrue(any("texte alternatif" in e for e in errors))

    def test_image_outside_the_repository_is_reported(self):
        self.assertTrue(any("introuvable" in e for e in rc.check(self.project(GOOD + "\n![x](../../etc/passwd)\n"))))

    def test_architecture_needs_its_excalidraw_source(self):
        root = self.project()
        (root / "docs/diagrams/architecture.excalidraw").unlink()
        self.assertTrue(any("Excalidraw" in e for e in rc.check(root)))
        (root / ".harness").mkdir()
        (root / ".harness/config.json").write_text('{"readme": {"architecture": "any"}}', encoding="utf-8")
        self.assertEqual(rc.check(root), [])

    def test_progress_block_needs_markers_and_a_table(self):
        no_block = GOOD.replace("<!-- harness:begin avancement -->\n", "")
        self.assertTrue(any("bloc d'avancement absent" in e for e in rc.check(self.project(no_block))))
        empty = GOOD.replace("| LOT-001 | 🟢 livré |\n", "")
        self.assertTrue(any("sans tableau" in e for e in rc.check(self.project(empty))))

    def test_every_planned_lot_appears_in_the_progress_block(self):
        errors = rc.check(self.project(lots="| LOT-001 | moteur |\n| LOT-002 | écran |\n"))
        self.assertEqual([e for e in errors if "LOT-002" in e and "LOT-001" not in e.split(":")[-1]], errors)
        self.assertEqual(len(errors), 1)

    def test_contributing_needs_section_file_and_link(self):
        self.assertTrue(any("Contribuer" in e for e in rc.check(self.project(GOOD.split("## Contribuer")[0]))))
        root = self.project()
        (root / "CONTRIBUTING.md").unlink()
        self.assertTrue(any("CONTRIBUTING.md : absent" in e for e in rc.check(root)))

    def test_each_point_can_be_switched_off(self):
        bare = "# Projet\n\nRien d'autre.\n"
        off = {"badges": False, "image": False, "architecture": False, "progress": False, "quickstart": False,
               "contributing": False}
        self.assertEqual(rc.check(self.project(bare, {"readme": off})), [])
        self.assertEqual(rc.check(self.project(bare, {"readme": False})), [])
        self.assertEqual(len(rc.check(self.project(bare))), 6)

    def test_unknown_setting_is_refused(self):
        with self.assertRaises(ValueError):
            rc.check(self.project(config={"readme": {"badge": False}}))

    def test_images_in_code_blocks_are_ignored(self):
        fenced = GOOD + "\n```markdown\n![](docs/images/exemple.png)\n```\n"
        self.assertEqual(rc.check(self.project(fenced)), [])

    def test_harness_readme_and_seeded_template_meet_the_standard(self):
        self.assertEqual(rc.check(ROOT), [])
        root = self.project((ROOT / "templates/README.md.template").read_text(encoding="utf-8"))
        (root / "docs/LOTS.md").write_text("LOT-001\n", encoding="utf-8")
        self.assertEqual(rc.check(root), [])


if __name__ == "__main__":
    unittest.main()

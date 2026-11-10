"""Tests of scripts/doc-links.py: relative links and cross-file anchors in Markdown resolve; the rest is left alone."""
import contextlib
import importlib.util
import io
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("doc_links", ROOT / "scripts" / "doc-links.py")
dl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dl)

GUIDE = """# Guide

## Getting started
Text.

## Getting started

### `ledger-label` input: *the* [ledger](#getting-started)

Setext title
------------

<a name="custom-anchor"></a>
"""


class DocLinksTests(unittest.TestCase):
    def project(self, files):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = pathlib.Path(tmp.name)
        (root / "docs").mkdir()
        (root / "docs/GUIDE.md").write_text(GUIDE, encoding="utf-8")
        (root / "scripts").mkdir()
        (root / "scripts/tool.py").write_text("print()\n", encoding="utf-8")
        for name, text in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        return root

    def check(self, root, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = dl.main(["--root", str(root), *args])
        return code, out.getvalue()

    def test_valid_links_pass(self):
        root = self.project({"README.md": "\n".join([
            "# Readme",
            "[guide](docs/GUIDE.md) [tool](scripts/tool.py) [folder](docs/) [root](/docs/GUIDE.md)",
            "[dup](docs/GUIDE.md#getting-started-1) [code](docs/GUIDE.md#ledger-label-input-the-ledger)",
            "[setext](docs/GUIDE.md#setext-title) [html](docs/GUIDE.md#custom-anchor) [line](scripts/tool.py#L1)",
            "[ref]: docs/GUIDE.md#getting-started",
            '<a href="docs/GUIDE.md">html</a> ![img](docs/GUIDE.md "title") [spaced](<docs/GUIDE.md>)',
            "[web](https://example.com/x.md) [mail](mailto:a@example.com) [self](#readme)",
        ])})
        code, out = self.check(root)
        self.assertEqual(code, 0, out)

    def test_missing_file_is_reported_with_its_line(self):
        root = self.project({"README.md": "# Readme\n\nSee [gone](docs/GONE.md).\n"})
        code, out = self.check(root)
        self.assertEqual(code, 1)
        self.assertIn("README.md:3: docs/GONE.md: file not found", out)

    def test_relative_to_the_linking_file(self):
        root = self.project({"docs/OTHER.md": "[ok](GUIDE.md) [ko](docs/GUIDE.md) [up](../scripts/tool.py)\n"})
        code, out = self.check(root)
        self.assertEqual(code, 1)
        self.assertIn("docs/OTHER.md:1: docs/GUIDE.md: file not found", out)
        self.assertEqual(out.count("not found"), 1, out)

    def test_cross_file_anchor_is_checked(self):
        root = self.project({"README.md": "[x](docs/GUIDE.md#nowhere)\n[ref]: docs/GUIDE.md#getting-started-2\n"})
        code, out = self.check(root)
        self.assertEqual(code, 1)
        self.assertIn("README.md:1: docs/GUIDE.md#nowhere: anchor not found", out)
        self.assertIn("README.md:2: docs/GUIDE.md#getting-started-2: anchor not found", out)

    def test_in_file_anchors_are_left_to_markdownlint(self):
        root = self.project({"README.md": "# Readme\n[x](#nowhere)\n"})
        self.assertEqual(self.check(root)[0], 0)

    def test_code_and_comments_are_ignored(self):
        root = self.project({"README.md": "\n".join([
            "`[a](GONE.md)`", "```", "[b](GONE.md)", "```", "~~~md", "[c](GONE.md)", "~~~",
            "<!-- [d](GONE.md)", "[e](GONE.md) -->",
        ])})
        code, out = self.check(root)
        self.assertEqual(code, 0, out)

    def test_link_out_of_the_repository_is_reported(self):
        root = self.project({"README.md": "[x](../outside.md)\n"})
        code, out = self.check(root)
        self.assertEqual(code, 1)
        self.assertIn("outside the repository", out)

    def test_excluded_and_explicit_paths(self):
        root = self.project({".harness/docs/X.md": "[x](GONE.md)\n", "notes/N.md": "[y](GONE.md)\n"})
        code, out = self.check(root)
        self.assertEqual(code, 1)
        self.assertNotIn(".harness", out)
        self.assertIn("notes/N.md:1", out)
        self.assertEqual(self.check(root, "--exclude", "notes/**")[0], 0)
        code, out = self.check(root, "docs")
        self.assertEqual(code, 0, out)

    def test_slug(self):
        self.assertEqual(dl.slug("Ledger: never a conflict on a shared file"), "ledger-never-a-conflict-on-a-shared-file")
        self.assertEqual(dl.slug("2. Doc steward: docs that stay true"), "2-doc-steward-docs-that-stay-true")
        self.assertEqual(dl.slug("Démarrage rapide 🚀"), "démarrage-rapide-")


if __name__ == "__main__":
    unittest.main()

"""Tests of scripts/decisions-check.py: the operator's decisions file (docs/DECISIONS.md) is consistent.

- at most one `in force` row per scope key (the contradiction the file exists to prevent);
- every row has a date, a scope key, a decision, a source and a known status;
- the rule is off when the file is absent; the seeded template passes as shipped.
"""
import contextlib
import importlib.util
import io
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("decisions_check", ROOT / "scripts" / "decisions-check.py")
dc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dc)

HEAD = "| Date | Scope key | Decision | Source | Status |\n|---|---|---|---|---|\n"


def run(text=None):
    """(exit code, output) of the check on a repository holding docs/DECISIONS.md with `text` (None: no file)."""
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        if text is not None:
            (root / "docs").mkdir()
            (root / "docs/DECISIONS.md").write_text(text, encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = dc.main(["--root", str(root)])
        return code, out.getvalue()


class DecisionsCheckTests(unittest.TestCase):
    def test_absent_file_switches_the_rule_off(self):
        self.assertEqual(run(None)[0], 0)

    def test_empty_table_and_valid_rows_pass(self):
        self.assertEqual(run("# Decisions\n\n" + HEAD)[0], 0)
        rows = (
            "| 2026-11-10 | children.max | At most 4 children. | [comment](https://x/1) | in force |\n"
            "| 2026-11-02 | children.max | No cap. | [comment](https://x/0) | replaced by 2026-11-10 |\n"
            "| 2026-11-01 | merge.freeze | Freeze merges. | chat, 2026-11-01 | lifted 2026-11-03 |\n"
        )
        self.assertEqual(run(HEAD + rows)[0], 0)

    def test_two_active_rows_for_one_scope_key_fail(self):
        rows = (
            "| 2026-11-10 | children.max | At most 4. | [c](https://x/1) | in force |\n"
            "| 2026-11-02 | Children.Max | No cap. | [c](https://x/0) | in force |\n"
        )
        code, out = run(HEAD + rows)
        self.assertEqual(code, 1)
        self.assertIn("children.max", out.lower())
        self.assertIn("in force", out)

    def test_missing_source_fails(self):
        code, out = run(HEAD + "| 2026-11-10 | merge.policy | Merge when ready. |  | in force |\n")
        self.assertEqual(code, 1)
        self.assertIn("source", out)

    def test_missing_or_malformed_date_fails(self):
        code, out = run(HEAD + "|  | merge.policy | Merge when ready. | [c](https://x/1) | in force |\n")
        self.assertEqual(code, 1)
        self.assertIn("date", out)
        self.assertEqual(run(HEAD + "| 10/11/2026 | a.b | d. | s | in force |\n")[0], 1)

    def test_unknown_status_fails(self):
        code, out = run(HEAD + "| 2026-11-10 | a.b | d. | s | maybe |\n")
        self.assertEqual(code, 1)
        self.assertIn("status", out)

    def test_replaced_and_lifted_need_a_date(self):
        self.assertEqual(run(HEAD + "| 2026-11-10 | a.b | d. | s | replaced by |\n")[0], 1)
        self.assertEqual(run(HEAD + "| 2026-11-10 | a.b | d. | s | lifted |\n")[0], 1)

    def test_code_blocks_and_comments_are_not_rows(self):
        text = "# D\n\n```\n" + HEAD + "| bad | row |\n```\n\n<!--\n| bad | row |\n-->\n\n" + HEAD
        self.assertEqual(run(text)[0], 0)

    def test_every_error_is_listed(self):
        code, out = run(HEAD + "| 2026-11-10 | a.b | d. |  | in force |\n|  | c.d | d. | s | in force |\n")
        self.assertEqual(code, 1)
        self.assertIn("source", out)
        self.assertIn("date", out)

    def test_seeded_template_passes_as_shipped(self):
        template = ROOT / "templates/docs/DECISIONS.md"
        self.assertTrue(template.is_file())
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            self.assertEqual(dc.main(["--file", str(template)]), 0, out.getvalue())


if __name__ == "__main__":
    unittest.main()

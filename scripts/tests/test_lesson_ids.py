"""The lessons table keeps stable ids, each row has a class, and every `L<nn>` cited elsewhere exists (issue #18)."""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
LESSONS = ROOT / "docs/LESSONS.md"
CHECK_SKILL = ROOT / "plugins/harness/skills/lessons-check/SKILL.md"
# Where lesson ids are cited: docs, skills, agents, templates, the root docs, workflows and config files
CITING = [ROOT / "docs", ROOT / "plugins/harness/skills", ROOT / "plugins/harness/agents", ROOT / "templates",
          ROOT / ".github"]
CITING_FILES = [*ROOT.glob("*.md"), ROOT / ".markdownlint-cli2.jsonc"]
SUFFIXES = {".md", ".yml", ".yaml", ".json", ".jsonc", ".block", ".template"}
CITE_RE = re.compile(r"(?<![\w-])L(\d{2})(?![\w-])")
ENFORCED = "mechanical, enforced by "
READ_BY_SELF_REVIEW = ("judgment", "mechanical, check to write")
CLASSES = READ_BY_SELF_REVIEW + ("one-off",)


def rows(text=None):
    """(id, cells) of each lesson row; cells are split on unescaped `|`."""
    text = LESSONS.read_text(encoding="utf-8") if text is None else text
    out = []
    for line in text.splitlines():
        if re.match(r"^\| L\d{2} \|", line):
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]
            out.append((cells[0], cells))
    return out


def header_cells():
    for line in LESSONS.read_text(encoding="utf-8").splitlines():
        if line.startswith("| # |"):
            return [c.strip() for c in line.split("|")[1:-1]]
    return []


def citations():
    """{id: [file, …]} of every `L<nn>` cited outside docs/LESSONS.md."""
    files = [p for d in CITING for p in d.rglob("*") if p.is_file() and p.suffix in SUFFIXES] + CITING_FILES
    found = {}
    for path in files:
        if path.resolve() == LESSONS.resolve() or not path.is_file():
            continue
        for m in CITE_RE.finditer(path.read_text(encoding="utf-8")):
            found.setdefault(f"L{m.group(1)}", []).append(str(path.relative_to(ROOT)))
    return found


class LessonIdsTests(unittest.TestCase):
    def test_ids_are_stable_contiguous_and_in_order(self):
        ids = [i for i, _ in rows()]
        self.assertEqual(ids, [f"L{n:02d}" for n in range(1, len(ids) + 1)])
        self.assertGreaterEqual(len(ids), 82)

    def test_every_cited_id_exists(self):
        known = {i for i, _ in rows()}
        cited = citations()
        self.assertTrue(cited, "no citation found: the scan is broken")
        missing = {i: files for i, files in cited.items() if i not in known}
        self.assertEqual(missing, {}, f"lesson ids cited but absent from docs/LESSONS.md: {missing}")

    def test_scan_catches_a_dangling_citation(self):
        self.assertEqual([m.group(0) for m in CITE_RE.finditer("see L07, (L99) and LOT-082, not XL10")],
                         ["L07", "L99"])


class LessonClassTests(unittest.TestCase):
    def test_table_has_a_class_column_and_rows_keep_their_width(self):
        head = header_cells()
        self.assertEqual(head[-1], "Class")
        for lesson, cells in rows():
            self.assertEqual(len(cells), len(head), f"{lesson}: {len(cells)} cells (unescaped `|`?)")

    def test_every_row_has_a_known_class(self):
        for lesson, cells in rows():
            cls = cells[-1]
            self.assertTrue(cls in CLASSES or cls.startswith(ENFORCED), f"{lesson}: unknown class {cls!r}")

    def test_an_enforced_lesson_names_a_check_that_exists(self):
        for lesson, cells in rows():
            if not cells[-1].startswith(ENFORCED):
                continue
            paths = re.findall(r"`([\w./-]+\.(?:yml|py|sh|jsonc|json))`", cells[-1])
            self.assertTrue(paths, f"{lesson}: an enforced lesson names the file of its check")
            for p in paths:
                self.assertTrue((ROOT / p).is_file(), f"{lesson}: check file {p} not found")

    def test_self_review_reads_only_the_rows_left_to_judgment(self):
        text = CHECK_SKILL.read_text(encoding="utf-8")
        for cls in READ_BY_SELF_REVIEW:
            self.assertIn(f"`{cls}`", text)
        self.assertIn("Class", text)
        self.assertIn("enforced by", text)
        read = [i for i, c in rows() if c[-1] in READ_BY_SELF_REVIEW]
        self.assertLess(len(read), len(rows()), "the self-review must read fewer rows than the table holds")


if __name__ == "__main__":
    unittest.main()

"""The three lesson classes (mechanical, judgment, one-off) appear in the skill, the issue form and the header."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
FILES = {
    "skill": ROOT / "plugins/harness/skills/lesson-propose/SKILL.md",
    "form": ROOT / ".github/ISSUE_TEMPLATE/lesson.yml",
    "header": ROOT / "docs/LESSONS.md",
}


class LessonClassesTests(unittest.TestCase):
    def test_each_file_names_the_three_classes(self):
        for name, path in FILES.items():
            text = path.read_text().lower()
            for cls in ("mechanical", "judgment", "one-off"):
                self.assertIn(cls, text, f"{name} does not name the class {cls!r}")

    def test_form_asks_for_the_class_and_the_check(self):
        text = FILES["form"].read_text()
        self.assertIn("id: class", text)
        self.assertIn("id: check", text)


if __name__ == "__main__":
    unittest.main()

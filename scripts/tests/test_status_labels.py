"""Tests of the six `status:` states (METHODOLOGY.md §4): label file, issue form and the blocker check of
.github/workflows/issue-hygiene.yml (its JavaScript, run with node; skipped when node is absent)."""
import json
import pathlib
import re
import shutil
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
STATUSES = {"needs-triage", "needs-decision", "ready", "claimed", "blocked", "on-hold"}
WORKFLOW = (ROOT / ".github/workflows/issue-hygiene.yml").read_text(encoding="utf-8")


class LabelFileTests(unittest.TestCase):
    def test_status_axis_has_the_six_states_including_on_hold(self):
        labels = json.loads((ROOT / "templates/.github/labels.json").read_text(encoding="utf-8"))
        status = {x["name"]: x for x in labels if x.get("axis") == "status"}
        self.assertEqual({n.removeprefix("status: ") for n in status}, STATUSES)
        self.assertIn("decision", status["status: on-hold"]["description"])
        self.assertIn("not by a dependency", status["status: on-hold"]["description"])


class SpellingTests(unittest.TestCase):
    def test_one_spelling_blocked_by_not_depends_on(self):
        form = (ROOT / "templates/.github/ISSUE_TEMPLATE/task.yml").read_text(encoding="utf-8")
        self.assertIn("label: Blocked by", form)
        for path in ("templates/.github/ISSUE_TEMPLATE/task.yml", "plugins/harness/agents/issue-steward.md",
                     "plugins/harness/skills/lot-start/SKILL.md"):
            self.assertNotIn("Depends on", (ROOT / path).read_text(encoding="utf-8"), path)


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class BlockerCheckTests(unittest.TestCase):
    @staticmethod
    def blocker_of(body):
        m = re.search(r"// begin blocker\n(.*?)// end blocker", WORKFLOW, re.S)
        assert m, "the workflow must delimit its blocker parser with `// begin blocker` / `// end blocker`"
        js = m.group(1) + "\nprocess.stdout.write(JSON.stringify(blockerOf(JSON.parse(process.argv[1]))));"
        out = subprocess.run(["node", "-e", js, json.dumps(body)], capture_output=True, text=True, check=True)
        return json.loads(out.stdout)

    def test_issue_and_external_blockers_are_read_one_per_line(self):
        self.assertEqual(self.blocker_of("### Summary\nx\n\n### Blocked by\n\n#12\n#14\n\n### Other\ny"), "#12\n#14")
        self.assertEqual(self.blocker_of("### Blocked by\r\n\r\n- camera access from a third party\r\n"),
                         "camera access from a third party")
        self.assertEqual(self.blocker_of("#### blocked by\n#3"), "#3")

    def test_missing_or_empty_blocker_is_none(self):
        for body in ("", None, "Summary only", "### Blocked by", "### Blocked by\n\n   \n", "### Blocked by\n\nnone",
                     "### Blocked by\n\n_No response_", "### Blocked by\n\n### Next\nx", "I am blocked by nothing",
                     "Blocked by: #3", "### Blocked by this\n#3"):
            self.assertIsNone(self.blocker_of(body), body)

    def test_workflow_reports_without_flipping_the_label(self):
        self.assertIn("status: blocked", WORKFLOW)
        self.assertIn("on-hold", WORKFLOW)
        self.assertNotIn("removeLabel({ ...ref, name: blocked", WORKFLOW)


if __name__ == "__main__":
    unittest.main()

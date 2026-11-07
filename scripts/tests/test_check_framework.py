"""Tests de scripts/check-framework.py : le dépôt réel passe, chaque type de défaut est détecté."""
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHECK = ROOT / "scripts" / "check-framework.py"


def run(root):
    return subprocess.run([sys.executable, str(CHECK), "--root", str(root)], capture_output=True, text=True)


class CheckFrameworkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        for d in ("plugins", "docs", "templates", "scripts", "i18n"):
            shutil.copytree(ROOT / d, self.tmp / d)
        for f in ("harness.manifest", "VERSION", "CHANGELOG.md"):
            shutil.copy(ROOT / f, self.tmp / f)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_real_repository_passes(self):
        r = run(ROOT)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_copy_passes(self):
        self.assertEqual(run(self.tmp).returncode, 0)

    def test_agent_name_must_match_file(self):
        p = self.tmp / "plugins/harness/agents/issue-steward.md"
        p.write_text(p.read_text().replace("name: issue-steward", "name: autre"))
        r = run(self.tmp)
        self.assertEqual(r.returncode, 1)
        self.assertIn("issue-steward.md", r.stdout)

    def test_agent_needs_known_model(self):
        p = self.tmp / "plugins/harness/agents/flow-monitor.md"
        p.write_text(p.read_text().replace("model: haiku", "model: gpt"))
        self.assertIn("model", run(self.tmp).stdout)

    def test_compliance_agent_needs_sections(self):
        p = self.tmp / "plugins/harness/agents/compliance-pci.md"
        p.write_text(p.read_text().replace("## Sources", "## Liens"))
        self.assertIn("Sources", run(self.tmp).stdout)

    def test_skill_without_description(self):
        p = self.tmp / "plugins/harness/skills/intent/SKILL.md"
        p.write_text(p.read_text().replace("description:", "desc:", 1))
        self.assertIn("intent", run(self.tmp).stdout)

    def test_manifest_source_must_exist(self):
        with open(self.tmp / "harness.manifest", "a") as f:
            f.write("copy      docs/ABSENT.md   .harness/docs/ABSENT.md\n")
        self.assertIn("ABSENT.md", run(self.tmp).stdout)

    def test_naming_examples_must_match_regex(self):
        p = self.tmp / "docs/ORCHESTRATION.md"
        p.write_text(p.read_text().replace("`hfrnow.orc-0711.rev.pr231`", "`hfrnow.rev.pr231`", 1))
        self.assertIn("hfrnow.rev.pr231", run(self.tmp).stdout)


if __name__ == "__main__":
    unittest.main()

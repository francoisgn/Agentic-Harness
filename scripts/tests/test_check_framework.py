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
        for d in ("plugins", "docs", "templates", "scripts", "i18n", ".github"):
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

    def test_generic_reviewer_must_stay_read_only(self):
        p = self.tmp / "plugins/harness/agents/compliance-reviewer.md"
        p.write_text(p.read_text().replace("tools: Read,", "tools: Edit, Read,"))
        self.assertIn("compliance-reviewer.md", run(self.tmp).stdout)

    def test_required_check_must_be_a_real_job_name(self):
        p = self.tmp / ".github/repo-settings.json"
        p.write_text(p.read_text().replace('"context": "Scripts, workflows, tests"', '"context": "check"'))
        out = run(self.tmp).stdout
        self.assertIn("« check »", out)

    def test_required_check_must_run_on_pull_request_and_not_be_reusable(self):
        p = self.tmp / ".github/repo-settings.json"
        original = p.read_text()
        for name in ("Tableau de bord", "Réglages du dépôt"):  # job hors pull_request ; job de workflow réutilisable
            p.write_text(original.replace('"context": "Scripts, workflows, tests"', f'"context": "{name}"'))
            self.assertIn(f"« {name} »", run(self.tmp).stdout, name)

    def test_pull_request_trigger_in_flow_and_scalar_forms(self):
        spec = __import__("importlib.util").util.spec_from_file_location("cf", CHECK)
        cf = __import__("importlib.util").util.module_from_spec(spec)
        spec.loader.exec_module(cf)
        job = "jobs:\n  a:\n    name: Tests\n    runs-on: x\n"
        for on in ("on: [push, pull_request]\n", "on: pull_request\n", "on:\n  pull_request:\n"):
            self.assertEqual(cf.pull_request_job_names(on + job), {"Tests"}, on)
        self.assertEqual(cf.pull_request_job_names("on: [pull_request_target]\n" + job), set())

    def test_malformed_manifest_line_is_reported(self):
        with open(self.tmp / "harness.manifest", "a") as f:
            f.write("copy\n")
        r = run(self.tmp)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("mal formée", r.stdout)

    def test_quoted_on_key_and_trailing_comment(self):
        spec = __import__("importlib.util").util.spec_from_file_location("cf2", CHECK)
        cf = __import__("importlib.util").util.module_from_spec(spec)
        spec.loader.exec_module(cf)
        job = "jobs:\n  a:\n    name: Tests\n    runs-on: x\n"
        for on in ("'on':\n  pull_request:\n", "\"on\": [pull_request]\n", "on: # déclencheurs\n  pull_request:\n"):
            self.assertEqual(cf.pull_request_job_names(on + job), {"Tests"}, on)

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

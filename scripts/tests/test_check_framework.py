"""Tests of scripts/check-framework.py: the real repository passes, every kind of defect is detected."""
import json
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
        for d in ("plugins", "docs", "templates", "scripts", ".github"):
            shutil.copytree(ROOT / d, self.tmp / d)
        for f in ("harness.manifest", "VERSION", "CHANGELOG.md", "README.md", "LICENSE"):
            shutil.copy(ROOT / f, self.tmp / f)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def set_required_check(self, name):
        """Replace the first required check of the ruleset with `name`."""
        p = self.tmp / ".github/repo-settings.json"
        settings = json.loads(p.read_text())
        for ruleset in settings["rulesets"]:
            for rule in ruleset.get("rules", []):
                checks = (rule.get("parameters") or {}).get("required_status_checks")
                if checks:
                    checks[0]["context"] = name
                    p.write_text(json.dumps(settings))
                    return
        self.fail("no required check in .github/repo-settings.json")

    def set_labels(self, change):
        p = self.tmp / "templates/.github/labels.json"
        labels = json.loads(p.read_text())
        change(labels)
        p.write_text(json.dumps(labels))

    def test_label_name_must_follow_axis_value_format(self):
        for bad in ("bug", "Type: bug", "type: über", "status:claimed", "status: needs decision"):
            self.set_labels(lambda labels, bad=bad: labels.append({"name": bad, "color": "ffffff"}))
            r = run(self.tmp)
            self.assertEqual(r.returncode, 1, bad)
            self.assertIn(f'"{bad}"', r.stdout)

    def test_plain_labels_are_accepted(self):
        def change(labels):
            labels[:] = [x for x in labels if x["name"] not in ("direct-pr", "dependencies")]
            labels += [{"name": "direct-pr", "color": "ffffff"}, {"name": "dependencies", "color": "ffffff"}]
        self.set_labels(change)
        self.assertEqual(run(self.tmp).returncode, 0)

    def test_every_exclusive_axis_must_be_present(self):
        for axis in ("status", "type", "priority", "difficulty"):
            original = (self.tmp / "templates/.github/labels.json").read_text()
            self.set_labels(lambda labels, axis=axis: labels.__setitem__(
                slice(None), [x for x in labels if not x["name"].startswith(axis + ": ")]))
            r = run(self.tmp)
            self.assertEqual(r.returncode, 1, axis)
            self.assertIn(f"`{axis}:`", r.stdout)
            (self.tmp / "templates/.github/labels.json").write_text(original)

    def test_duplicate_label_is_reported(self):
        self.set_labels(lambda labels: labels.append(dict(labels[0])))
        self.assertIn("duplicate", run(self.tmp).stdout)

    def test_real_repository_passes(self):
        r = run(ROOT)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_copy_passes(self):
        self.assertEqual(run(self.tmp).returncode, 0)

    def test_banner_must_exist(self):
        (self.tmp / "docs/assets/banner.svg").unlink()
        r = run(self.tmp)
        self.assertEqual(r.returncode, 1)
        self.assertIn("banner.svg", r.stdout)

    def test_readme_must_show_banner(self):
        p = self.tmp / "README.md"
        p.write_text(p.read_text().replace("docs/assets/banner.svg", "docs/assets/other.svg"))
        self.assertIn("README.md", run(self.tmp).stdout)

    def test_social_preview_must_be_1280_by_640(self):
        p = self.tmp / "docs/assets/social-preview.png"
        data = bytearray(p.read_bytes())
        data[16:20] = (1200).to_bytes(4, "big")
        p.write_bytes(bytes(data))
        self.assertIn("1280×640", run(self.tmp).stdout)

    def test_repository_needs_description_and_topics(self):
        p = self.tmp / ".github/repo-settings.json"
        p.write_text(p.read_text().replace('"topics": [', '"topics_": ['))
        out = run(self.tmp).stdout
        self.assertIn("topics", out)

    def test_agent_name_must_match_file(self):
        p = self.tmp / "plugins/harness/agents/issue-steward.md"
        p.write_text(p.read_text().replace("name: issue-steward", "name: other"))
        r = run(self.tmp)
        self.assertEqual(r.returncode, 1)
        self.assertIn("issue-steward.md", r.stdout)

    def test_agent_needs_known_model(self):
        p = self.tmp / "plugins/harness/agents/flow-monitor.md"
        p.write_text(p.read_text().replace("model: haiku", "model: gpt"))
        self.assertIn("model", run(self.tmp).stdout)

    def test_compliance_agent_needs_sections(self):
        p = self.tmp / "plugins/harness/agents/compliance-pci.md"
        p.write_text(p.read_text().replace("## Sources", "## Links"))
        self.assertIn("Sources", run(self.tmp).stdout)

    def test_generic_reviewer_must_stay_read_only(self):
        p = self.tmp / "plugins/harness/agents/compliance-reviewer.md"
        p.write_text(p.read_text().replace("tools: Read,", "tools: Edit, Read,"))
        self.assertIn("compliance-reviewer.md", run(self.tmp).stdout)

    def test_required_check_must_be_a_real_job_name(self):
        self.set_required_check("check")
        self.assertIn('"check"', run(self.tmp).stdout)

    def test_required_check_must_run_on_pull_request_and_not_be_reusable(self):
        wf = self.tmp / ".github/workflows"
        (wf / "zz-nightly.yml").write_text("on:\n  schedule:\n    - cron: '0 3 * * *'\njobs:\n  a:\n"
                                           "    name: Nightly only\n    runs-on: x\n")
        (wf / "zz-caller.yml").write_text("on: pull_request\njobs:\n  a:\n    name: Reusable caller\n"
                                          "    uses: ./.github/workflows/zz-nightly.yml\n")
        for name in ("Nightly only", "Reusable caller"):  # job outside pull_request; reusable workflow job
            self.set_required_check(name)
            self.assertIn(f'"{name}"', run(self.tmp).stdout, name)

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
        self.assertIn("harness.manifest:", r.stdout)
        self.assertIn("malformed", r.stdout)

    def test_quoted_on_key_and_trailing_comment(self):
        spec = __import__("importlib.util").util.spec_from_file_location("cf2", CHECK)
        cf = __import__("importlib.util").util.module_from_spec(spec)
        spec.loader.exec_module(cf)
        job = "jobs:\n  a:\n    name: Tests\n    runs-on: x\n"
        for on in ("'on':\n  pull_request:\n", "\"on\": [pull_request]\n", "on: # triggers\n  pull_request:\n"):
            self.assertEqual(cf.pull_request_job_names(on + job), {"Tests"}, on)

    def test_nested_pull_request_input_is_not_a_trigger(self):
        spec = __import__("importlib.util").util.spec_from_file_location("cf3", CHECK)
        cf = __import__("importlib.util").util.module_from_spec(spec)
        spec.loader.exec_module(cf)
        job = "jobs:\n  a:\n    name: Tests\n    runs-on: x\n"
        nested = "on: # manual\n  workflow_dispatch:\n    inputs:\n      pull_request:\n        type: string\n"
        self.assertEqual(cf.pull_request_job_names(nested + job), set())
        direct = "on:\n  workflow_dispatch:\n    inputs:\n      x:\n        type: string\n  pull_request:\n"
        self.assertEqual(cf.pull_request_job_names(direct + job), {"Tests"})
        for key in ("'pull_request':", '"pull_request":'):
            self.assertEqual(cf.pull_request_job_names("on:\n  " + key + "\n" + job), {"Tests"}, key)

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

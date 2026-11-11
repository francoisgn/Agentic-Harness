"""Tests of the version rule (issue #68): `master` never carries consumer-visible changes under a released number.

The step "Valid JSON and consistent versions" of .github/workflows/ci.yml is replayed on a throwaway repository:
- VERSION = X.Y.Z (released): its CHANGELOG heading exists and `## Unreleased` is empty;
- VERSION = X.Y.Z-dev (next version): X.Y.Z must not be a released heading yet;
- VERSION and plugin.json agree.
"""
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from test_local_check import CI, ci_steps

STEP = "Valid JSON and consistent versions"
BULLET = "- **A change**\n  **Action**: none.\n"


def command():
    return dict(ci_steps(CI.read_text(encoding="utf-8")))[STEP]


def changelog(unreleased="", released=("0.3.0",)):
    text = "# Changelog\n\n## Unreleased\n\n" + unreleased
    for v in released:
        text += f"\n## {v} — 2026-11-09\n\n- something\n"
    return text


class VersionRule(unittest.TestCase):
    def check(self, version, log, plugin=None):
        repo = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, repo)
        (repo / "plugins/harness/.claude-plugin").mkdir(parents=True)
        (repo / "VERSION").write_text(version + "\n", encoding="utf-8")
        (repo / "plugins/harness/.claude-plugin/plugin.json").write_text(
            f'{{"version": "{plugin or version}"}}\n', encoding="utf-8")
        (repo / "CHANGELOG.md").write_text(log, encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        done = subprocess.run(["bash", "-c", command()], cwd=repo, capture_output=True, text=True)
        return done.returncode, done.stdout + done.stderr

    def test_released_number_with_empty_unreleased_passes(self):
        self.assertEqual(self.check("0.3.0", changelog())[0], 0)

    def test_released_number_with_changes_under_unreleased_fails(self):
        code, out = self.check("0.3.0", changelog(BULLET))
        self.assertNotEqual(code, 0)
        self.assertIn("Unreleased", out)

    def test_dev_version_with_changes_passes(self):
        self.assertEqual(self.check("0.4.0-dev", changelog(BULLET))[0], 0)

    def test_dev_version_of_an_already_released_number_fails(self):
        code, out = self.check("0.3.0-dev", changelog(BULLET))
        self.assertNotEqual(code, 0)
        self.assertIn("already", out)

    def test_released_number_without_its_heading_fails(self):
        self.assertNotEqual(self.check("0.4.0", changelog())[0], 0)

    def test_malformed_version_fails(self):
        self.assertNotEqual(self.check("0.4", changelog(BULLET))[0], 0)

    def test_plugin_manifest_must_match(self):
        self.assertNotEqual(self.check("0.4.0-dev", changelog(BULLET), plugin="0.3.0")[0], 0)


if __name__ == "__main__":
    unittest.main()

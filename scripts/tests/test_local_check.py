"""Tests of the local check (issue #12): the seeded skeleton templates/scripts/local-check.sh and the harness's own
scripts/local-check.sh.

- the three outcomes OK / FAILED / INCOMPLETE, with distinct exit codes, on a throwaway repository;
- the harness's script uses the same engine as the template (only the steps region differs);
- the harness's steps cannot drift from .github/workflows/ci.yml: same names, same commands, same order.
"""
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "templates/scripts/local-check.sh"
OWN = ROOT / "scripts/local-check.sh"
CI = ROOT / ".github/workflows/ci.yml"
BEGIN, END = "# >>> steps", "# <<< steps"
EXIT_OK, EXIT_FAILED, EXIT_INCOMPLETE = 0, 1, 2

STEP_RE = re.compile(r"^step \"([^\"]+)\" \"([^\"]*)\" \"([^\"]*)\" <<'CMD'\n(.*?)\nCMD$", re.M | re.S)


def script_steps(text):
    """(name, command) of each `step` declared in a local-check script, in order."""
    return [(m.group(1), m.group(4).strip()) for m in STEP_RE.finditer(text)]


def ci_steps(text):
    """(name, run) of each step of a workflow that has a `run:` (a `uses:` step has nothing to replay), in order.
    Minimal reader for the shape of ci.yml: `- name:` items, `run:` on one line or as a `|` block."""
    steps, current, block, indent = [], None, None, 0
    for line in text.splitlines():
        if block is not None:
            if line.strip() == "" or len(line) - len(line.lstrip()) >= indent:
                block.append(line)
                continue
            current["run"] = textwrap.dedent("\n".join(block)).strip()
            block = None
        m = re.match(r"^\s*- name:\s*(.+?)\s*$", line)
        if m:
            current = {"name": m.group(1)}
            steps.append(current)
            continue
        m = re.match(r"^(\s*)run:\s*(.*?)\s*$", line)
        if m and current is not None:
            if m.group(2) == "|":
                block, indent = [], len(m.group(1)) + 2
            else:
                current["run"] = m.group(2)
    if block is not None:
        current["run"] = textwrap.dedent("\n".join(block)).strip()
    return [(s["name"], s["run"]) for s in steps if "run" in s]


def engine(text):
    """The script without its steps region."""
    start, end = text.index(BEGIN), text.index(END)
    return text[:start] + text[end:]


def with_steps(steps):
    """The template with `steps` (bash text) in its steps region."""
    text = TEMPLATE.read_text(encoding="utf-8")
    start, end = text.index(BEGIN), text.index(END)
    return text[:start] + BEGIN + "\n" + steps + "\n" + text[end:]


def step(name, cmd, tools="", paths=""):
    return f"step \"{name}\" \"{tools}\" \"{paths}\" <<'CMD'\n{cmd}\nCMD"


class Outcomes(unittest.TestCase):
    def setUp(self):
        self.repo = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo)
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}
        self.env = env
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.repo)], check=True, env=env)
        (self.repo / "scripts").mkdir()
        (self.repo / "README.md").write_text("x\n")
        subprocess.run(["git", "-C", str(self.repo), "add", "-A"], check=True, env=env)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-qm", "init"], check=True, env=env)

    def run_check(self, text, *args, env=None):
        path = self.repo / "scripts/local-check.sh"
        path.write_text(text, encoding="utf-8")
        return subprocess.run(["bash", str(path), *args], cwd=self.repo, capture_output=True, text=True,
                              env={**self.env, **(env or {})})

    def assert_result(self, proc, code, word):
        self.assertEqual(proc.returncode, code, proc.stdout + proc.stderr)
        self.assertRegex(proc.stdout, rf"(?m)^Result: {word}\b")

    def test_ok_when_every_step_passes(self):
        proc = self.run_check(with_steps(step("first", "true") + "\n" + step("second", "echo hi")))
        self.assert_result(proc, EXIT_OK, "OK")
        self.assertRegex(proc.stdout, r"(?m)^ +ok +first$")

    def test_failed_names_the_step(self):
        proc = self.run_check(with_steps(step("good", "true") + "\n" + step("bad", "exit 3")))
        self.assert_result(proc, EXIT_FAILED, "FAILED")
        self.assertRegex(proc.stdout, r"(?m)^ +FAILED +bad \(exit 3\)$")

    def test_every_step_runs_after_a_failure(self):
        proc = self.run_check(with_steps(step("bad", "false") + "\n" + step("after", "true")))
        self.assertRegex(proc.stdout, r"(?m)^ +ok +after$")

    def test_missing_tool_is_incomplete_and_named(self):
        proc = self.run_check(with_steps(step("good", "true") + "\n"
                                         + step("linter", "no-such-tool-xyz .", tools="no-such-tool-xyz")))
        self.assert_result(proc, EXIT_INCOMPLETE, "INCOMPLETE")
        self.assertIn("no-such-tool-xyz", proc.stdout.split("Result:")[1])

    def test_failure_wins_over_incomplete(self):
        proc = self.run_check(with_steps(step("bad", "false") + "\n" + step("x", "x", tools="no-such-tool-xyz")))
        self.assert_result(proc, EXIT_FAILED, "FAILED")

    def test_step_for_another_host_is_skipped_with_reason_and_incomplete(self):
        proc = self.run_check(with_steps(step("good", "true") + "\n" + step("mac build", "true", tools="os:NoSuchOS")))
        self.assert_result(proc, EXIT_INCOMPLETE, "INCOMPLETE")
        self.assertRegex(proc.stdout, r"(?m)^ +skipped +mac build \(.*NoSuchOS.*\)$")

    def test_skeleton_without_steps_is_incomplete(self):
        proc = self.run_check(TEMPLATE.read_text(encoding="utf-8"))
        self.assert_result(proc, EXIT_INCOMPLETE, "INCOMPLETE")

    def test_quick_mode_skips_steps_whose_paths_did_not_change(self):
        (self.repo / "scripts/a.sh").write_text("echo\n")  # untracked change under scripts/
        steps = step("scripts", "true", paths="scripts/*") + "\n" + step("docs", "false", paths="docs/*")
        proc = self.run_check(with_steps(steps), "--quick", env={"LOCAL_CHECK_BASE": "HEAD"})
        self.assert_result(proc, EXIT_OK, "OK")
        self.assertRegex(proc.stdout, r"(?m)^ +ok +scripts$")
        self.assertRegex(proc.stdout, r"(?m)^ +skipped +docs \(quick: .*\)$")

    def test_full_mode_runs_every_step(self):
        steps = step("docs", "false", paths="docs/*")
        self.assert_result(self.run_check(with_steps(steps), "--full"), EXIT_FAILED, "FAILED")

    def test_unknown_option_is_a_usage_error(self):
        proc = self.run_check(with_steps(step("good", "true")), "--bogus")
        self.assertNotIn(proc.returncode, (EXIT_OK, EXIT_FAILED, EXIT_INCOMPLETE))


class HarnessScript(unittest.TestCase):
    def test_same_engine_as_the_template(self):
        self.assertEqual(engine(OWN.read_text(encoding="utf-8")), engine(TEMPLATE.read_text(encoding="utf-8")))

    def test_steps_match_ci_yml(self):
        ci = ci_steps(CI.read_text(encoding="utf-8"))
        own = script_steps(OWN.read_text(encoding="utf-8"))
        self.assertTrue(ci)
        self.assertEqual([n for n, _ in own], [n for n, _ in ci], "step names or order differ from ci.yml")
        for (name, cmd), (_, run) in zip(own, ci):
            self.assertEqual(cmd, run, f"command of step \"{name}\" differs from ci.yml")

    def test_drift_is_detected(self):
        ci = ci_steps(CI.read_text(encoding="utf-8"))
        drifted = ci_steps(CI.read_text(encoding="utf-8").replace("shellcheck scripts", "shellcheck -x scripts"))
        self.assertNotEqual(ci, drifted)

    def test_executable(self):
        for path in (OWN, TEMPLATE):
            self.assertTrue(os.access(path, os.X_OK), path)

    def test_seeded_by_the_manifest(self):
        manifest = (ROOT / "harness.manifest").read_text(encoding="utf-8")
        self.assertRegex(manifest, r"(?m)^seed\s+templates/scripts/local-check\.sh\s+scripts/local-check\.sh\s*$")


if __name__ == "__main__":
    unittest.main()

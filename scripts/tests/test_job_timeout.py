"""Tests of scripts/job-timeout.py: every workflow job that runs steps has `timeout-minutes` (CI-BASELINE.md §2, #99).

- a job without `timeout-minutes` is named with its workflow and line (exit 1); a job with one passes (exit 0);
- a job that calls a reusable workflow (`uses:` at job level) cannot carry one: not reported;
- `timeout-minutes` on a step only does not count for the job;
- comments, quoted keys and block scalars are read, not guessed;
- a layout the reader does not understand (flow mapping, anchor, alias, merge key, tab) says "could not check", exit 2;
- an exception in `.harness/config.json` needs a reason; an unknown name in the list is reported;
- a value above the ceiling (default 120, configurable) is a warning, not a failure.
"""
import contextlib
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("job_timeout", ROOT / "scripts" / "job-timeout.py")
jt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jt)

OK = """name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - run: make test
"""

NO_TIMEOUT = """name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - run: make test
  build:
    runs-on: macos-latest
    steps:
      - run: make build
"""


def run(workflows=None, config=None, extra=()):
    """(exit code, output) of the check on a repository holding `workflows` ({name: text}; None: no folder)."""
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        if workflows is not None:
            folder = root / ".github/workflows"
            folder.mkdir(parents=True)
            for name, text in workflows.items():
                if isinstance(text, bytes):
                    (folder / name).write_bytes(text)
                else:
                    (folder / name).write_text(text, encoding="utf-8")
        if config is not None:
            (root / ".harness").mkdir()
            text = config if isinstance(config, str) else json.dumps(config)
            (root / ".harness/config.json").write_text(text, encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = jt.main(["--root", str(root), *extra])
        return code, out.getvalue()


class JobTimeoutTests(unittest.TestCase):
    def test_job_with_steps_and_no_timeout_is_named_with_workflow_and_line(self):
        code, out = run({"ci.yml": NO_TIMEOUT})
        self.assertEqual(code, 1, out)
        self.assertIn(".github/workflows/ci.yml:9: job 'build' has no timeout-minutes", out)
        self.assertNotIn("'test'", out)

    def test_job_with_timeout_passes(self):
        code, out = run({"ci.yml": OK})
        self.assertEqual(code, 0, out)
        self.assertIn("OK", out)

    def test_yaml_extension_is_checked_too(self):
        self.assertEqual(run({"ci.yaml": NO_TIMEOUT})[0], 1)

    def test_reusable_workflow_job_is_not_reported(self):
        text = """on: push
jobs:
  docs:
    permissions:
      contents: read
    uses: owner/repo/.github/workflows/docs.yml@0123456789abcdef0123456789abcdef01234567 # v1
    with:
      gitleaks: false
"""
        code, out = run({"harness.yml": text})
        self.assertEqual(code, 0, out)

    def test_timeout_on_a_step_only_is_still_reported(self):
        text = """on: push
jobs:
  build:
    runs-on: macos-latest
    steps:
      - name: Tests
        timeout-minutes: 30
        run: make test
"""
        code, out = run({"ci.yml": text})
        self.assertEqual(code, 1, out)
        self.assertIn("job 'build' has no timeout-minutes", out)

    def test_timeout_inside_with_or_a_run_block_does_not_count(self):
        text = """on: push
jobs:
  build:
    runs-on: ubuntu-latest
    env:
      timeout-minutes: 5
    steps:
      - run: |
          timeout-minutes: 5
"""
        self.assertEqual(run({"ci.yml": text})[0], 1)

    def test_comments_and_quoted_keys(self):
        text = """# timeout-minutes: 10 (a comment, not a key)
"on": push
"jobs":   # the jobs
  # build:
  "build":
    'runs-on': ubuntu-latest  # runner
    "timeout-minutes": 15 # minutes
    steps:
      - run: echo "jobs: # not a key"
  'lint':  # no timeout here
    runs-on: ubuntu-latest
    # timeout-minutes: 5
    steps:
      - run: make lint
"""
        code, out = run({"ci.yml": text})
        self.assertEqual(code, 1, out)
        self.assertIn("ci.yml:10: job 'lint' has no timeout-minutes", out)
        self.assertNotIn("'build'", out)

    def test_block_scalar_at_job_level_is_skipped(self):
        text = """on: push
jobs:
  build:
    if: >-
      github.event_name == 'push'
      && timeout-minutes: true
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: make
"""
        self.assertEqual(run({"ci.yml": text})[0], 0)

    def test_compact_sequence_at_job_key_level_is_understood(self):
        text = """on: push
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
    - run: make
    - run: make test
"""
        self.assertEqual(run({"ci.yml": text})[0], 0)

    def test_flow_mapping_job_could_not_check(self):
        text = "on: push\njobs:\n  build: {runs-on: ubuntu-latest, steps: [{run: make}]}\n"
        code, out = run({"ci.yml": text})
        self.assertEqual(code, 2, out)
        self.assertIn("could not check .github/workflows/ci.yml:", out)
        self.assertNotIn("OK", out)

    def test_flow_mapping_jobs_could_not_check(self):
        self.assertEqual(run({"ci.yml": "on: push\njobs: {build: {runs-on: x}}\n"})[0], 2)

    def test_anchor_alias_and_merge_key_could_not_check(self):
        anchor = """on: push
jobs:
  build: &base
    runs-on: ubuntu-latest
    steps:
      - run: make
"""
        merge = """on: push
jobs:
  build:
    <<: *base
    steps:
      - run: make
"""
        alias = "on: push\njobs:\n  build:\n    runs-on: x\n    timeout-minutes: *t\n    steps: []\n"
        for text in (anchor, merge, alias):
            with self.subTest(text=text):
                code, out = run({"ci.yml": text})
                self.assertEqual(code, 2, out)
                self.assertIn("could not check", out)

    def test_tab_indentation_and_unreadable_file_could_not_check(self):
        self.assertEqual(run({"ci.yml": "on: push\njobs:\n\tbuild:\n\t\truns-on: x\n"})[0], 2)
        code, out = run({"ci.yml": b"on: push\njobs:\n  build:\xff\n"})
        self.assertEqual(code, 2, out)
        self.assertIn("could not check .github/workflows/ci.yml: ", out)
        code, out = run({"ci.yml": "on: push\njobs:\n  - build\n"})
        self.assertEqual(code, 2, out)

    def test_inconsistent_indentation_could_not_check(self):
        text = """on: push
jobs:
    build:
      runs-on: x
      timeout-minutes: 5
      steps: []
  lint:
      runs-on: x
"""
        self.assertEqual(run({"ci.yml": text})[0], 2)

    def test_could_not_check_never_hides_a_finding(self):
        code, out = run({"a.yml": NO_TIMEOUT, "b.yml": "on: push\njobs: {x: {}}\n"})
        self.assertEqual(code, 1, out)
        self.assertIn("job 'build' has no timeout-minutes", out)
        self.assertIn("could not check .github/workflows/b.yml", out)

    def test_no_workflows_folder_checks_nothing(self):
        code, out = run(None)
        self.assertEqual(code, 0, out)
        self.assertIn("nothing checked", out)

    def test_exception_with_reason_accepts_the_job(self):
        config = {"job_timeout": {"exceptions": [
            {"workflow": "ci.yml", "job": "build", "reason": "bounded by the step timeouts, #12"}]}}
        code, out = run({"ci.yml": NO_TIMEOUT}, config)
        self.assertEqual(code, 0, out)
        self.assertIn("accepted", out)

    def test_exception_without_reason_is_refused(self):
        config = {"job_timeout": {"exceptions": [{"job": "build"}]}}
        code, out = run({"ci.yml": NO_TIMEOUT}, config)
        self.assertEqual(code, 1, out)
        self.assertIn("exception refused", out)
        self.assertIn("job 'build' has no timeout-minutes", out)

    def test_unknown_name_in_exceptions_is_reported(self):
        config = {"job_timeout": {"exceptions": [{"job": "deploy", "reason": "old job"}]}}
        code, out = run({"ci.yml": OK}, config)
        self.assertEqual(code, 1, out)
        self.assertIn("'deploy'", out)
        self.assertIn("unknown", out)

    def test_unreadable_config_could_not_check(self):
        self.assertEqual(run({"ci.yml": OK}, "{not json")[0], 2)
        self.assertEqual(run({"ci.yml": OK}, {"job_timeout": {"ceiling": "high"}})[0], 2)
        self.assertEqual(run({"ci.yml": OK}, {"job_timeout": {"exceptions": "build"}})[0], 2)

    def test_ceiling_is_a_warning_not_a_failure(self):
        text = OK.replace("timeout-minutes: 10", "timeout-minutes: 360")
        code, out = run({"ci.yml": text})
        self.assertEqual(code, 0, out)
        self.assertIn("warning: .github/workflows/ci.yml:6: job 'test' timeout-minutes 360 is above the ceiling 120", out)
        code, out = run({"ci.yml": text}, {"job_timeout": {"ceiling": 400}})
        self.assertEqual(code, 0, out)
        self.assertNotIn("warning", out)
        code, out = run({"ci.yml": OK}, {"job_timeout": {"ceiling": 5}})
        self.assertIn("above the ceiling 5", out)

    def test_expression_value_is_accepted_and_garbage_is_reported(self):
        expr = OK.replace("timeout-minutes: 10", "timeout-minutes: ${{ inputs.timeout }}")
        self.assertEqual(run({"ci.yml": expr})[0], 0)
        quoted = OK.replace("timeout-minutes: 10", "timeout-minutes: '20'")
        self.assertEqual(run({"ci.yml": quoted})[0], 0)
        bad = OK.replace("timeout-minutes: 10", "timeout-minutes: soon")
        code, out = run({"ci.yml": bad})
        self.assertEqual(code, 1, out)
        self.assertIn("not a number", out)

    def test_dir_option_checks_another_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = pathlib.Path(tmp) / "templates/.github/workflows"
            folder.mkdir(parents=True)
            (folder / "x.yml").write_text(NO_TIMEOUT, encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                code = jt.main(["--root", tmp, "--dir", "templates/.github/workflows"])
        self.assertEqual(code, 1, out.getvalue())
        self.assertIn("templates/.github/workflows/x.yml:9", out.getvalue())

    def test_harness_workflows_and_templates_pass(self):
        for folder in (".github/workflows", "templates/.github/workflows"):
            with self.subTest(folder=folder):
                out = io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                    code = jt.main(["--root", str(ROOT), "--dir", folder, "--config", "/nonexistent"])
                self.assertEqual(code, 0, out.getvalue())


if __name__ == "__main__":
    unittest.main()

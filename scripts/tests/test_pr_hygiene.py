"""Tests of the ledger check embedded in .github/workflows/pr-hygiene.yml (CONVENTIONS.md §Ledger).

The `script:` of the github-script step is extracted from the workflow and run under Node with stubs of `core`,
`context` and `github` (no network); Node is already present wherever CI runs markdownlint. Skipped without Node.
"""
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "pr-hygiene.yml"
NODE = shutil.which("node")

HARNESS = """
const core = { failed: null, warnings: [], notices: [], infos: [],
  setFailed(m) { this.failed = m; }, warning(m) { this.warnings.push(m); },
  notice(m) { this.notices.push(m); }, info(m) { this.infos.push(m); } };
const pr = JSON.parse(process.env.TEST_PR);
const context = { payload: { pull_request: pr }, repo: { owner: 'o', repo: 'r' } };
const github = { paginate: async () => [], rest: { pulls: { listFiles: null },
  issues: { addLabels: async () => ({}) }, repos: { getContent: async () => ({}) } } };
(async () => {
%s
})().then(() => console.log(JSON.stringify(core)), (e) => { console.error(e); process.exit(3); });
"""


def embedded_script():
    """The body of the `script: |` block, dedented."""
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == "script: |")
    indent = len(lines[start]) - len(lines[start].lstrip()) + 2
    out = []
    for line in lines[start + 1:]:
        if line.strip() and len(line) - len(line.lstrip()) < indent:
            break
        out.append(line[indent:])
    return "\n".join(out)


def ledger_body(*lines, docs="Docs: none (tests only)"):
    return "Closes #1\n\n### Ledger\n\n" + "\n".join(lines) + f"\n{docs}\n\n### Tests\n\nunit\n"


@unittest.skipUnless(NODE, "node not installed")
class LedgerCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.js = pathlib.Path(cls.tmp.name) / "run.js"
        cls.js.write_text(HARNESS % embedded_script(), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_check(self, body, labels=()):
        pr = {"number": 7, "draft": False, "body": body, "user": {"login": "someone"},
              "base": {"ref": "develop"}, "head": {"ref": "feat/x", "sha": "abc"},
              "labels": [{"name": n} for n in labels]}
        env = dict(os.environ, TEST_PR=json.dumps(pr), FLOW="", FLOW_BASES="", REQUIRE_ISSUE="true",
                   LEDGER_LABEL="ledger", LEDGER_HEADING="### Ledger", REQUIRE_CHANGELOG="false",
                   CHANGELOG_HEADING="## Changelog", PROMOTION_HEADS="develop beta", EXEMPT_AUTHORS="",
                   DOCS_CODE_PATHS="", INTEGRATION_BRANCH="", DEFAULT_BRANCH="develop")
        run = subprocess.run([NODE, str(self.js)], env=env, capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual(run.returncode, 0, run.stderr)
        return json.loads(run.stdout.strip().splitlines()[-1])

    def test_entries_are_valid_with_or_without_the_label(self):
        for labels in ((), ("ledger",)):
            core = self.run_check(ledger_body("```changelog", "Added X", "```"), labels=labels)
            self.assertIsNone(core["failed"], labels)
            self.assertEqual(core["warnings"] + core["notices"], [], labels)

    def test_label_without_entries_is_one_stale_label_note(self):
        for body in ("Closes #1\n\nDocs: none (x)\n", ledger_body("None (tests only)")):
            core = self.run_check(body, labels=["ledger"])
            self.assertIsNone(core["failed"], body)
            self.assertEqual(len(core["notices"]), 1, body)
            self.assertIn("stale label", core["notices"][0].lower())
            self.assertEqual(core["warnings"], [])
        core = self.run_check("Closes #1\n\nDocs: none (x)\n")   # no section, no label: nothing to say
        self.assertIsNone(core["failed"])
        self.assertEqual(core["notices"], [])

    def test_explicit_empty_section_has_one_spelling(self):
        core = self.run_check(ledger_body("None (tests only)"))
        self.assertIsNone(core["failed"])
        self.assertEqual(core["notices"], [])
        core = self.run_check(ledger_body("None"))
        self.assertIn("None (<reason>)", core["failed"] or "")

    def test_untyped_block_fails_with_the_entry_and_the_format(self):
        core = self.run_check(ledger_body("```", "Added X without a type", "```"))
        self.assertIn("Added X without a type", core["failed"] or "")
        self.assertIn("expected", core["failed"])

    def test_unclosed_block_fails(self):
        core = self.run_check("Closes #1\n\n### Ledger\n\n```changelog\nAdded Y\n")
        self.assertIn("not closed", core["failed"] or "")


if __name__ == "__main__":
    unittest.main()

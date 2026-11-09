"""Tests of scripts/compliance-plan.py: resolving `compliance` (.harness/config.json) into the reviewers to run."""
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "compliance-plan.py"
spec = importlib.util.spec_from_file_location("compliance_plan", SCRIPT)
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)

SPEC_OK = """---
id: dora
framework: Regulation (EU) 2022/2554 (DORA)
confirmed_by: CISO
---
# DORA

## When to step in
- incident, ict

## What I check
1. Incident log: art. 17 (to verify)

## Expected evidence
- Incident register

## Sources
- https://eur-lex.europa.eu/eli/reg/2022/2554/oj
"""

AGENT_OK = """---
name: acme-pci-qsa
description: ACME's internal PCI reviewer.
tools: Read, Grep
model: opus
---
# ACME PCI reviewer
"""


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        agents = self.root / ".claude/agents"
        agents.mkdir(parents=True)
        for builtin in ("gdpr", "pci"):
            (agents / f"compliance-{builtin}.md").write_text(f"---\nname: compliance-{builtin}\n---\n")
        (agents / "compliance-reviewer.md").write_text("---\nname: compliance-reviewer\n---\n")

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self, entries, files=(), diff=""):
        return cp.plan({"compliance": entries}, self.root, list(files), diff)

    def test_builtin_by_id(self):
        r = self.plan(["gdpr"])
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["reviewers"], [{"id": "gdpr", "mode": "built-in", "agent": "compliance-gdpr",
                                           "file": ".claude/agents/compliance-gdpr.md", "scope": "to assess",
                                           "reason": 'scope judged by the agent (section "When to step in")'}])

    def test_confirmed_by_is_passed_through(self):
        r = self.plan([{"id": "gdpr", "confirmed_by": "DPO"}, "pci"])
        self.assertEqual(r["reviewers"][0]["confirmed_by"], "DPO")
        self.assertNotIn("confirmed_by", r["reviewers"][1])

    def test_unknown_builtin_is_an_error(self):
        self.assertIn("soc2", " ".join(self.plan(["soc2"])["errors"]))

    def test_company_agent_replaces_builtin(self):
        path = self.root / ".claude/agents/acme-pci-qsa.md"
        path.write_text(AGENT_OK)
        r = self.plan([{"id": "pci", "agent": ".claude/agents/acme-pci-qsa.md"}])
        self.assertEqual(r["errors"], [])
        self.assertEqual((r["reviewers"][0]["mode"], r["reviewers"][0]["agent"]), ("project agent", "acme-pci-qsa"))

    def test_company_agent_missing_or_without_name(self):
        self.assertTrue(self.plan([{"id": "pci", "agent": "absent.md"}])["errors"])
        (self.root / "x.md").write_text("# no frontmatter\n")
        self.assertTrue(self.plan([{"id": "pci", "agent": "x.md"}])["errors"])

    def test_spec_runs_generic_reviewer(self):
        (self.root / "docs/compliance").mkdir(parents=True)
        (self.root / "docs/compliance/dora.md").write_text(SPEC_OK)
        r = self.plan([{"id": "dora", "spec": "docs/compliance/dora.md"}])
        self.assertEqual(r["errors"], [])
        self.assertEqual((r["reviewers"][0]["mode"], r["reviewers"][0]["agent"], r["reviewers"][0]["file"]),
                         ("spec", "compliance-reviewer", "docs/compliance/dora.md"))

    def test_spec_missing_sections_is_an_error(self):
        (self.root / "dora.md").write_text(SPEC_OK.replace("## Sources", "## Links"))
        self.assertIn("Sources", " ".join(self.plan([{"id": "dora", "spec": "dora.md"}])["errors"]))

    def test_agent_and_spec_together_is_an_error(self):
        self.assertTrue(self.plan([{"id": "x", "agent": "a.md", "spec": "s.md"}])["errors"])

    def test_disabled_entry_is_skipped(self):
        self.assertEqual(self.plan([{"id": "gdpr", "enabled": False}])["reviewers"], [])

    def test_paths_and_keywords_decide_scope(self):
        entry = {"id": "gdpr", "paths": ["src/account/**"], "keywords": ["cookie"]}
        self.assertEqual(self.plan([entry], files=["src/account/session.swift"])["reviewers"][0]["scope"], "in scope")
        self.assertEqual(self.plan([entry], files=["README.md"], diff="+ let cookie = x")["reviewers"][0]["scope"],
                         "in scope")
        r = self.plan([entry], files=["README.md"], diff="+ text")
        self.assertEqual(r["reviewers"][0]["scope"], "out of scope")

    def test_keywords_are_whole_words_and_ignore_file_headers(self):
        entry = {"id": "gdpr", "keywords": ["ict"]}
        self.assertEqual(self.plan([entry], diff="+x = dict()")["reviewers"][0]["scope"], "out of scope")
        self.assertEqual(self.plan([entry], diff="+++ b/ict/a.py\n+pass")["reviewers"][0]["scope"], "out of scope")
        self.assertEqual(self.plan([entry], diff="+# major ICT risk")["reviewers"][0]["scope"], "in scope")

    def test_globs_star_stays_in_one_directory_and_double_star_matches_root(self):
        self.assertTrue(cp.glob_match("src/a.py", "src/*.py"))
        self.assertFalse(cp.glob_match("src/x/a.py", "src/*.py"))
        self.assertTrue(cp.glob_match("a.swift", "**/*.swift"))
        self.assertTrue(cp.glob_match("x/y/a.swift", "**/*.swift"))
        self.assertTrue(cp.glob_match("src/account/x/y.swift", "src/account/**"))

    def test_malformed_config_gives_errors_not_tracebacks(self):
        self.assertTrue(cp.plan({"compliance": "gdpr"}, self.root)["errors"])
        self.assertTrue(cp.plan({"compliance": [["gdpr"]]}, self.root)["errors"])

    def test_non_string_id_agent_or_spec_is_an_error(self):
        for entry in ({"id": ["x"]}, {"id": {"a": 1}}, {"id": "pci", "agent": ["a.md"]}, {"id": "dora", "spec": 3}):
            self.assertTrue(cp.plan({"compliance": [entry]}, self.root)["errors"], entry)

    def test_paths_outside_the_repository_are_refused(self):
        outside = pathlib.Path(self.tmp.name).parent / "outside-repo.md"
        outside.write_text(AGENT_OK)
        try:
            for path in (str(outside), "../outside-repo.md"):
                errors = self.plan([{"id": "pci", "agent": path}])["errors"]
                self.assertTrue(any("outside the repository" in e for e in errors), (path, errors))
        finally:
            outside.unlink()

    def test_blank_or_path_like_id_is_an_error(self):
        for cid in ("   ", "../../x", "a/b", "a\\b"):
            self.assertTrue(self.plan([{"id": cid}])["errors"], cid)
        self.assertTrue(self.plan([" gdpr", "gdpr "])["errors"])  # duplicate once the spaces are stripped
        self.assertEqual(self.plan([" gdpr "])["reviewers"][0]["agent"], "compliance-gdpr")

    def test_duplicate_id_is_an_error(self):
        self.assertTrue(self.plan(["gdpr", {"id": "gdpr"}])["errors"])

    def test_cli_exit_codes(self):
        cfg = self.root / ".harness/config.json"
        cfg.parent.mkdir(exist_ok=True)
        cfg.write_text(json.dumps({"compliance": ["gdpr"]}))
        ok = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root), "--files", "a.py"],
                            capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertEqual(json.loads(ok.stdout)["reviewers"][0]["agent"], "compliance-gdpr")
        cfg.write_text(json.dumps({"compliance": ["unknown"]}))
        ko = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root)], capture_output=True, text=True)
        self.assertEqual(ko.returncode, 1)


class FrameworkSpecTemplateTests(unittest.TestCase):
    def test_shipped_spec_template_is_valid(self):
        errors = cp.check_spec(ROOT / "templates/docs/compliance/TEMPLATE.md")
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()

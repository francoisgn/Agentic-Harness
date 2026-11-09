# 0002 — Vendored specialised agents, review service and flow dashboard

**Status:** Proposed — 2026-11-07 (the maintainer decides)

## Context
The volume of agentic commits far exceeds that of a human; review and CI cycles become the main cost
(CI-BUDGET.md §5). Projects need compliance reviewers (GDPR, AI Act, NIS2, ISO 27001, SOC 2, TISAX, PCI, HDS) run
only when the diff concerns them, upkeep roles (issues, docs, flow) and a status that non-technical people can read.
Harness 0.1.0 described adversarial review in prose, with no reusable agent, and had no flow measurement at all.
OpenHarness (HKUDS, MIT) shows a task state machine persisted in the repository, a bounded repair loop and an
exported dashboard ([`src/openharness/autopilot/service.py`](https://github.com/HKUDS/OpenHarness/blob/main/src/openharness/autopilot/service.py), branch `main` read on 2026-11-07, last commit dated 2026-06-04).

## Options
1. **Prose only**: each project writes its own prompts. Free, but divergent and not testable.
2. **Vendored Claude Code agents** (`.claude/agents/*.md`) + reusable workflows + measurement script using the
   standard library. Works in the cloud and locally, versioned with the harness, checked by the CI.
3. **External service** (CodeRabbit, compliance tool, SaaS dashboard): less code, but third-party accounts, cost per
   seat, and our rules (lessons, conventions) not applied.

## Decision
Option 2:
- agents `adversarial-reviewer`, `issue-steward`, `doc-steward`, `flow-monitor`, `compliance-<id>` in
  `plugins/harness/agents/`, vendored into `.claude/agents/` (manifest, `tree` mode); compliance enabled by
  `.harness/config.json` → `compliance`;
- agent naming convention `<project>.<orchestrator>.<role>.<target>` (ORCHESTRATION.md §7), checked in CI;
- review service `ai-review.yml` (pinned claude-code-action), never a required check;
- `security.yml` pipeline (Semgrep, Trivy, gitleaks); dashboard `flow-metrics.py` + `flow-report.yml`;
- bounded loops: 3 review cycles, 6 pushes tested by the CI per PR (FINOPS.md §3).

## Consequences
- Easier: adding a compliance framework = one agent file + one catalogue line; automatic status report.
- Harder: compliance agents age with the texts; a yearly review per compliance framework is needed, and their
  "(to verify)" identifiers must be confirmed against the official texts.
- To watch: cost of the AI review per PR, relevance of its findings compared with CodeRabbit (comparison over 10 PRs).

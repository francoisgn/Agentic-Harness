# Changelog

Format: one section per version (semver), from newest to oldest. "Action" = what a consumer project must do when
moving to this version.

## Unreleased

- **English**: the whole harness is now in English; `i18n/` removed; files renamed (ESSENTIEL → ESSENTIALS,
  UTILISATION → USAGE, diagram and ADR names, issue forms `lesson.yml`, `task.yml`); managed block id `cadre` →
  `harness`; README progress markers `avancement` → `progress`.
- **Labels** ([ADR 0003](docs/adr/0003-labels-readable-by-axis.md), accepted): `axis: value` names (`status:`,
  `type:`, `priority:`, `difficulty:`, `needs:`); new states `status: needs-triage` and `status: ready`; old names
  kept as aliases.
- **Living README, by default** ([README-STANDARD](docs/README-STANDARD.md)): agents maintain the project README as a
  deliverable: technology badges in the header, image, Excalidraw architecture diagram, lot progress table, quick
  start, Contributing section. Skill `/readme-update` (called by `/lot-finish`), `readme-check.py` and
  `diagrams-render.py` vendored, templates `README.md`, `CONTRIBUTING.md` and `docs/diagrams/architecture.*` created
  if missing; check in `docs-security.yml` (input `readme`). Each point can be switched off in
  `.harness/config.json` › `readme`.
- **Tiered CI baseline** ([CI-BASELINE](docs/CI-BASELINE.md)): hygiene, quality (one local command = the CI),
  expensive, heavy security, process; six workflow invariants; survey of three real projects.
- The harness applies its own standard: README with badges and progress block, `CONTRIBUTING.md`, checked in CI.
- `scripts/diagrams/render.py`: `--dir` option.

**Action**: run `harness-sync.sh` again; rename the markers `harness:begin cadre`/`harness:end cadre` to `harness`,
and `avancement` to `progress` in README; run the label sync once with `apply-aliases: true`;
`.harness/docs/ESSENTIEL.md` import in CLAUDE.md becomes `.harness/docs/ESSENTIALS.md` (rewritten by the sync).
An existing README is not touched: `python3 .harness/scripts/readme-check.py` lists the gaps; to switch it off,
`"readme": false` in `.harness/config.json`. The `docs` job of `harness.yml`, if enabled, now checks the README
(`readme: false` to avoid it).

## 0.2.0 — 2026-11-07

Intent, TDD, FinOps, stewards, compliance, security and flow measurement.

- **Open to all**: no more reference by name to the creator (roles: maintainer, operator; plugin author
  "agentic-harness contributors"); the harness applies to any coding agent (Claude Code, Codex CLI, Cursor, Gemini
  CLI, Copilot, Aider…; loaded through `AGENTS.md`, natively or to be enabled depending on the tool: ADOPTION
  §Connect your coding agent), Claude Code remaining the adapter provided (plugin, hooks, `.claude/`); comment footer
  naming the agent; model tiers per provider (ORCHESTRATION §2).
- **Method**: mandatory intent for issues (user story, error behaviours, Given / When / Then criteria, definition of
  done: METHODOLOGY §2 bis) and TDD (§2 ter); richer issue forms; ESSENTIALS (French, English).
- **Docs**: FINOPS (SPOC orchestrator as the only long-lived agent, context in the repository, model routing, quotas
  and resuming, bounded loops, drift signals), STEWARDS (upkeep roles, non-technical report), REVIEW-SERVICE
  (in-house review service), COMPLIANCE (compliance reviewers), USAGE (step-by-step guide, SwiftHFR example),
  ADR 0002; CI-BUDGET §3 (secrets and variables) and §5 (agentic volume); ORCHESTRATION §7 (**agent naming**
  `<project>.<orchestrator>.<role>.<target>`, checked in CI); LESSONS: lessons reported through issues.
- **Agents** (vendored into `.claude/agents/`): `adversarial-reviewer`, `issue-steward`, `doc-steward`,
  `flow-monitor`, `compliance-gdpr`, `-eu-ai-act`, `-nis2`, `-iso27001`, `-soc2`, `-tisax`, `-pci` (DSS, PIN, P2PE),
  `-hds`, and the generic reviewer `compliance-reviewer`. Requirement identifiers not verified against the official
  text are marked "(to verify)".
- **Pluggable compliance** (COMPLIANCE §2): per compliance framework, built-in agent, company agent, or spec only
  (`docs/compliance/<id>.md`, template provided) applied by the generic reviewer; scope decided without tokens by
  `paths` / `keywords`; resolution and validation by `compliance-plan.py` (vendored, tested).
- **First-pass quality**: the dashboard measures the ratio of PRs with a problem (finding in adversarial, AI,
  compliance, CodeRabbit or human review), agents / humans, and the correction effort (commits after the first
  finding, time to merge); traceability rule for each verdict (REVIEW-ROUNDS §Traceability).
- **Repository settings "as code"**: `.github/repo-settings.json` (description, topics, rulesets) applied on merge
  by `repo-settings.yml` / `repo-settings.py` (secret `REPO_ADMIN_TOKEN`), drift checked every week; the harness
  uses it for itself (`settings.yml`). Required checks verified against the real job names.
- **Diagrams**: README illustrated with three diagrams (mechanisms, cycle of a change, leveraging the harness),
  source `docs/diagrams/*.json`, editable `.excalidraw` scene and SVGs rendered by `scripts/diagrams/render.py`
  (checked in CI).
- **Extension points** (ADOPTION §Replace or extend a building block): each building block of the harness can be
  kept, replaced by the company's own, or extended.
- **Skills**: `/intent`, `/lesson-propose`, `/status-report`, `/compliance-review`; `/lot-start` sets the agent
  identifier.
- **Reusable workflows**: `security.yml` (Semgrep CE, Trivy, gitleaks), `flow-report.yml` ("Project dashboard"
  issue), `ai-review.yml` (AI review, pinned claude-code-action, never required).
- **Script** `flow-metrics.py` (vendored into `.harness/scripts/`): milestones, bottlenecks, stalled work, CI and
  review loops, agents / humans ratio, time to merge, CI minutes; unit tests.
- **Labels**: `leçon`, `tableau de bord`, `revue: aucune`, `conformité` (names at that version; renamed since, see
  Unreleased). `.harness/config.json`: `compliance` key.
- **Harness CI**: consistency check (`check-framework.py`: skills, agents, manifest, labels, naming), Python tests,
  gitleaks; Dependabot for actions; "Lesson" issue form.

Additional action: create the `REPO_ADMIN_TOKEN` secret so that the `settings` job applies
`.github/repo-settings.json` (otherwise it only warns).

Fix: the harness CI listened to `main`, the default branch is `master`.

Action: `/harness-update` to v0.2.0. In `harness.yml` (project file, not rewritten): add the `schedule` trigger and
the `flow` job (see the template), enable `security` and `review` as needed. Fill in `compliance` in
`.harness/config.json` and exclude the compliance agents you do not need.

## 0.1.0 — 2026-11-07

First version, distilled from HFRnow (`dev-swift`) and ios-app_credit-immo (`develop`).

- Docs (French): ESSENTIALS (rules loaded in every session), METHODOLOGY, CONVENTIONS, LESSONS (82 scoped lessons,
  sources cited), ORCHESTRATION, REVIEW-ROUNDS, BRANCHING-RELEASE, CI-BUDGET, MAC-HANDOFF, ADOPTION, ADR 0001 and
  ADR template. English edition of ESSENTIALS and of the `CLAUDE.md`/`AGENTS.md` blocks (`i18n/en/`).
- Canonical label taxonomy (type, priority, model, size, status, host) with `axis` and `aliases`.
- Templates: `CLAUDE.md`/`AGENTS.md` block, issue forms (test feedback, bug, feature, task), PR, lot, markdownlint,
  `.harness/config.json`, calling workflows `harness.yml` and `harness-sync.yml`.
- `scripts/harness-sync.sh`: idempotent vendoring (modes copy, tree, block, seed, jsonmerge, refbump), lock with
  fingerprints, `--check`, `--dry-run`, `--force`, `--skip-workflows`, `--skip-seed`, per-project language and
  exclusions.
- Plugin `harness` (marketplace `agentic-harness`): six skills, `guard-git` hook (force push, push to a protected
  branch, `--no-verify`), reminder hook at session start.
- Reusable workflows: `labels-sync`, `issue-hygiene`, `pr-hygiene`, `docs-security`.

Action: adoption, see docs/ADOPTION.md.

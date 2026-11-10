# Changelog

Format: one section per version (semver), from newest to oldest. "Action" = what a consumer project must do when
moving to this version.

## Unreleased

- **Doc steward at merge, weekly safety net** ([STEWARDS](docs/STEWARDS.md) §2): new reusable `doc-steward.yml`, opt-in
  `steward` job in `harness.yml` (it adds `closed` to the `pull_request` types; the `pr` job skips it). After each
  merge into the integration branch, `doc-steward.py pending` (vendored in `.harness/scripts/`) decides without any
  agent: merged PRs still labelled `ledger`, or `Docs:` lines naming files since the last steward PR; nothing → one
  short job. Otherwise `ledger.fold_command` folds the ledger (its own reproducible commit), `readme-progress.py`
  refreshes the progress block, a Claude agent with a read-only token edits only the declared docs, and a job
  without an agent opens or updates ONE draft PR from `docs/steward` (never a protected branch; entries it cannot
  place are listed in it). Several merges queue in one concurrency group. Monday: audit only (README, links,
  diagrams, progress block), one `type: docs` issue per gap. Merge pass skipped with a notice without
  `ANTHROPIC_API_KEY` / `CLAUDE_CODE_OAUTH_TOKEN`; never required.
- **README progress generated from the issues**: `readme-progress.py` (vendored in `.harness/scripts/`) rewrites the
  block between the `progress` markers: one row per `type: epic` lot (state, closed/total sub-issues, issue and PR
  links), otherwise one per milestone; ⚠ on an epic without sub-issue or an issue with zero or several `status:`
  labels; `--check` exits 1 on drift. `/readme-update` uses it instead of hand-written rows; `flow-report.yml` input
  `readme-progress` reports drift in the job summary (README-STANDARD §3).
- **Doc impact per PR** ([CONVENTIONS](docs/CONVENTIONS.md) §Ledger): every PR carries a `Docs:` line (doc files it
  makes untrue, or `Docs: none (<reason>)`), in the `### Ledger` section with a ledger, otherwise in the body; the PR
  template asks for it. `pr-hygiene.yml` warns (never fails) when a ready PR changes code paths without it (new input
  `docs-code-paths`, empty = off) or names a missing file; a ledger section with only this line no longer needs the
  label. New `doc-links.py` (vendored as `.harness/scripts/doc-links.py`): relative links and cross-file anchors in
  Markdown resolve, run in the docs job of `docs-security.yml` (input `doc-links`) and in the harness CI. STEWARDS §2
  describes three levels: per PR, at merge, weekly safety net.
- **Local check = the CI** ([CI-BASELINE](docs/CI-BASELINE.md) §3): skill `/local-check` writes
  `scripts/local-check.sh` from the project's workflows (`--quick` for what changed, full by default), seeded as a
  skeleton that reports INCOMPLETE until it has steps; summary and result OK / FAILED / INCOMPLETE (exit 0 / 1 / 2),
  a missing tool or another host is never green. `/lot-finish` step 1 runs it. The harness's own script replays
  `ci.yml` (drift tested).
- **Lesson classes**: `/lesson-propose` classifies each item as mechanical (proposed check as an issue, no line),
  judgment (a lesson line) or one-off (nothing); the "Lesson" form asks for the class and the check; header of
  `docs/LESSONS.md` explains them.
- **Lessons sorted** (#18): a **Class** column in `docs/LESSONS.md`; ids unchanged. 79 rows judgment, L07 enforced
  by markdownlint MD056, L53 by zizmor, L75 `mechanical, check to write` (issue to come). `/lessons-check` reads only
  the judgment rows and those whose check is still to write: 80 rows instead of 82. A test checks that every
  `L<nn>` cited in docs, skills, agents, templates and workflows exists.
- **Two explicit reviews** ([REVIEW-ROUNDS](docs/REVIEW-ROUNDS.md) §The two reviews): the adversarial review
  (intent: issue + diff + lessons, isolated fresh sub-agent that refuses to give a verdict if it cannot be isolated)
  and the code review (diff only, by the review service) are named separately; one clean round on the current head
  ends the loop (within 3 cycles) and settled findings are listed in the PR, not reopened without new evidence.
- **Renamed to Belayline** (formerly agentic-harness): repository `francoisgn/belayline-agentic-harness`, plugin
  `belay` in marketplace `belayline` (`claude plugin install belay@belayline`). The vendored folder `.harness/`,
  `harness-sync.sh`, `harness.yml` and the `harness:` markers keep their names.
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
- **Default branch alert** (#10): the session-start hook and `harness-sync.sh` (also `--check`, exit code unchanged)
  print a 🟠 line when `integration_branch` is not the repository's default branch (workflows triggered by issues,
  comments and schedules would never run), or "could not check" when it is unknown; `pr-hygiene.yml` emits a
  `::warning::` (new input `integration-branch`). Silence with `"default_branch_check": false` in
  `.harness/config.json`.
- **Tiered CI baseline** ([CI-BASELINE](docs/CI-BASELINE.md)): hygiene, quality (one local command = the CI),
  expensive, heavy security, process; six workflow invariants; survey of three real projects.
- **Anti-bloat checks** (`check-framework.py`): size limits on skills, agents and `docs/ESSENTIALS.md` (listed
  exceptions only), skill and agent doc links must resolve, README counts and the `CLAUDE.md.block` skill list must
  match `plugins/harness/` ([CONTRIBUTING](CONTRIBUTING.md) §Size limits).
- The harness applies its own standard: README with badges and progress block, `CONTRIBUTING.md`, checked in CI.
- `scripts/diagrams/render.py`: `--dir` option.
- **Repository identity** (CONVENTIONS §Repository identity): every repository that follows the harness carries a
  description (one sentence), topics (5 to 15), a banner at the top of the README (`docs/assets/banner.svg`) and a
  social preview (`docs/assets/social-preview.png`, 1280×640, text in English, uploaded by hand by the operator). The
  doc steward checks all four (STEWARDS §2, agent `doc-steward`), ADOPTION plans for it.
- `repo-settings.py`: warns (without blocking) if the description or the topics are missing or malformed; a
  description left as the template's (`<…>`) is no longer sent to GitHub.
- The harness applies the rule to itself: description rewritten (any coding agent, no longer only Claude Code),
  topics widened to the agents covered, banner and social preview added; `check-framework.py` checks description,
  topics and images.
- **New banner and social preview** (compass motif, "Keep coding agents on track."): the README shows
  `docs/assets/banner.png`, rendered from `banner.svg` so the typeface does not depend on the reader's fonts;
  `check-framework.py` accepts a banner in `.svg` or `.png`.
- **MIT licence** (`LICENSE`): the harness had none; `harness-sync.sh` copies it into `.harness/LICENSE` with the
  vendored files.
- **`SECURITY.md`**: versions covered, private report (never a public issue), response times, scope; direct link
  from the issue template chooser.
- **Declined ideas recorded** (`.out-of-scope/`): skills invoked only by the human (`disable-model-invocation`) and one source compiled into per-tool skill formats (Cursor, Codex, Gemini CLI), each with the change that would reopen it (#19).

**Action**: point `uses:` references and the clone URL at `francoisgn/belayline-agentic-harness` (the sync rewrites
`harness.yml`); reinstall the plugin as `belay@belayline`. Then run `harness-sync.sh` again; rename the markers `harness:begin cadre`/`harness:end cadre` to `harness`,
and `avancement` to `progress` in README; run the label sync once with `apply-aliases: true`;
`.harness/docs/ESSENTIEL.md` import in CLAUDE.md becomes `.harness/docs/ESSENTIALS.md` (rewritten by the sync).
An existing README is not touched: `python3 .harness/scripts/readme-check.py` lists the gaps; to switch it off,
`"readme": false` in `.harness/config.json`. The `docs` job of `harness.yml`, if enabled, now checks the README
(`readme: false` to avoid it).
Fill in the description and the topics in `.github/repo-settings.json`, add the two images (an issue is enough to
start); the operator uploads the social preview in the repository settings. The next sync adds `.harness/LICENSE`.
Add a `Docs:` line to `.github/pull_request_template.md` (a project file, not rewritten; see the template's). The
`docs` job, if enabled, now checks relative links and cross-file anchors once the sync vendors `doc-links.py`: fix
what it lists, or `doc-links: false`; `docs-code-paths: ""` in the `pr` job silences the doc impact warning.
The next sync also seeds `scripts/local-check.sh`, which reports INCOMPLETE until `/local-check` fills in its steps
(a project with its own command names it in `CLAUDE.md` and adds `scripts/local-check.sh` to `exclude`).

## 0.3.0 — 2026-11-09

Feedback from the first consumer project: a neutral harness, rules that no longer contradict each other. **Breaking
convention change** (before 1.0.0, a MINOR may break): branches, claims and PR bodies change.

- **Neutral**: no more reference to the maintainer's other projects (names, decision numbers, measured costs,
  anecdotes); their lessons stay, reworded to hold everywhere (source "field" in LESSONS).
- **Push often, pay at "Ready"** (CI-BUDGET §2): replaces "one push per lot, no trial push". Push early and often on
  a draft PR (backup, visibility); the expensive CI only runs on the switch to "Ready" or on an explicit label
  (workflow pattern provided); one commit per review cycle; never a push "to see" on a ready PR. The dashboard no
  longer counts skipped or cancelled runs as tested pushes.
- **Claim** = comment `/claim <id>` (first line), replayed in order: the first claim wins, only repository members
  count, `/release [<id>]` gives it back; the PR carries `Claim: <id>`. Replaces "Claimed: branch …" (ESSENTIALS,
  METHODOLOGY, CONVENTIONS, ORCHESTRATION, skills, label, session-start).
- **Configurable label axes**: `.harness/config.json` → `labels.model_prefixes`, `labels.size_prefixes`;
  `/lot-start` no longer stops on a missing tier or size label (deduced from the text and the routing, stated in the
  claim).
- **Ledger**, optional building block (CONVENTIONS §Ledger): PRs no longer touch the shared logs, their entries go
  in a `### Ledger` section of the body (label `ledger`), which a steward folds after the merge into a docs PR
  reproduced by the project's script. `pr-hygiene.yml`: input `ledger-label` (section ↔ label check). `/lot-finish`
  and the PR template: issue line, `Claim:`, lot, problem / cause / change / tests, `### Ledger` only if the project
  keeps one, instead of `## Changelog`.
- **Branches** `<type>/<short-name>` (`lot`, `fix`, `feat`, `chore`, `docs`; `branch_types` in `config.json`)
  instead of `claude/<lot>`, everywhere (skills, docs, templates, sync workflow, hook message). The dashboard
  recognises an agent PR by its `Claim:` line or its generation footer.
- **guard-git** hardened: grouped options (`-fu`, `-uf`, `-nm`), abbreviations, `--force-with-lease`, `+refspec`,
  `--mirror`, `--all`, deletion of a protected branch (`--delete`, `-d`, `:branch`), `git -C`, `git -c`,
  wrappers (`env`, `command`, `exec`, `sudo`, `xargs`, `eval`, `bash -c`, `sh -c`…), subshells, groups,
  substitutions, here-documents, every separator; bare `git push`, `git push origin` and `HEAD` resolved against the
  current branch (`rev-parse`, or the branch chosen earlier on the line by `git switch` / `git checkout`), `@` as
  `HEAD`, `--tags` alone allowed, wildcard refspecs covering a protected branch refused; falls back to a cautious
  expression if the command cannot be split. Lets through `--dry-run`, `--force-if-includes` alone and unprotected
  branches; stays open on unreadable input. The server-side ruleset remains the real protection (BRANCHING-RELEASE
  §Common rules). Tests: `scripts/tests/test_guard_git.py`.
- **Managed blocks** of `CLAUDE.md` / `AGENTS.md`: `harness-sync.sh` lives in the harness repository (how to run it
  from a project); explicit precedence, project deviations in a "Harness overrides" section of its `AGENTS.md`
  (added to the template).

**Action**:
- `/harness-update` to v0.3.0; the update PR shows the new managed blocks.
- Create the "Harness overrides" section in `AGENTS.md` and write there what the project keeps its own way
  (branches, labels, claims, merge policy).
- `.harness/config.json` (project file, not rewritten): add as needed `branch_types`, `labels`
  (`model_prefixes`, `size_prefixes`; `[]` if the axis does not exist), `ledger` (`enabled`, `label`,
  `fold_command`).
- Branches and claims: move to `<type>/<short-name>` and `/claim <id>` (or record the deviation).
- `harness.yml`: remove `require-changelog: true` from the `pr` job (the PR template no longer has a "Changelog"
  section); set `ledger-label: ledger` if the project keeps a ledger, and create the labels `ledger` and
  `ledger: done` in `.github/labels.local.json`. `.github/pull_request_template.md` (project file): take over the
  new template as needed.
- Project CI: apply the pattern of CI-BUDGET §2 (expensive jobs skipped on a draft, unless an explicit label).

## 0.2.0 — 2026-11-07

Intent, TDD, FinOps, stewards, compliance, security and flow measurement.

- **Open to all**: no more reference by name to the creator (roles: maintainer, operator; plugin author
  "Belayline contributors"); the harness applies to any coding agent (Claude Code, Codex CLI, Cursor, Gemini
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

First version, distilled from HFRnow (`dev-swift`) and another project.

- Docs (French): ESSENTIALS (rules loaded in every session), METHODOLOGY, CONVENTIONS, LESSONS (82 scoped lessons,
  sources cited), ORCHESTRATION, REVIEW-ROUNDS, BRANCHING-RELEASE, CI-BUDGET, MAC-HANDOFF, ADOPTION, ADR 0001 and
  ADR template. English edition of ESSENTIALS and of the `CLAUDE.md`/`AGENTS.md` blocks (`i18n/en/`).
- Canonical label taxonomy (type, priority, model, size, status, host) with `axis` and `aliases`.
- Templates: `CLAUDE.md`/`AGENTS.md` block, issue forms (test feedback, bug, feature, task), PR, lot, markdownlint,
  `.harness/config.json`, calling workflows `harness.yml` and `harness-sync.yml`.
- `scripts/harness-sync.sh`: idempotent vendoring (modes copy, tree, block, seed, jsonmerge, refbump), lock with
  fingerprints, `--check`, `--dry-run`, `--force`, `--skip-workflows`, `--skip-seed`, per-project language and
  exclusions.
- Plugin `harness` (marketplace `Belayline`): six skills, `guard-git` hook (force push, push to a protected
  branch, `--no-verify`), reminder hook at session start.
- Reusable workflows: `labels-sync`, `issue-hygiene`, `pr-hygiene`, `docs-security`.

Action: adoption, see docs/ADOPTION.md.

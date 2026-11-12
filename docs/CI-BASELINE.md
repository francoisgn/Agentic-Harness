# CI baseline: what every project has, by tiers

**TL;DR**: five tiers, from free to expensive. Tier 0 applies to every repository, even a configuration repository;
the next ones are added depending on the project. Every row can be switched off. Surveyed on three real projects on
2026-11-09 (an iOS client, a photo developer in Rust, a shell configuration repository): this baseline is their common
denominator, plus what they lacked. Budget and tool details: [CI-BUDGET](CI-BUDGET.md).

## 1. The tiers

| Tier | For whom | Content | Cost per ready PR |
|---|---|---|---|
| **0 · Hygiene** | every repository | secrets (gitleaks), workflow lint (zizmor, actionlint), Markdown and README ([README-STANDARD](README-STANDARD.md)), weekly grouped Dependabot `github-actions` | 1 min Linux |
| **1 · Quality** | every repository with code | **one local command, the same as CI**; language lint in strict mode; tests | 1 to 10 min Linux |
| **2 · Expensive** | macOS, simulator, VM, OS matrix | behind tier 1 (`needs:`), only if the relevant paths change, never on a draft | 10 min and more, ×10 on macOS |
| **3 · Heavy security** | code shipped to users | SAST, dependencies (CVEs), on ready PRs + integration branch + every week | 2 to 5 min Linux |
| **4 · Process** | issue-driven project | labels synced from a file, PR linked to an issue, versioned ruleset, dashboard | seconds |

Tiers 0, 3 and 4: reusable workflows of the harness (`docs-security.yml`, `security.yml`, `labels-sync.yml`,
`issue-hygiene.yml`, `pr-hygiene.yml`, `repo-settings.yml`, `flow-report.yml`), called by `harness.yml`. Tiers 1
and 2: up to the project, the harness imposes neither the tool nor the language.

## 2. The six invariants of every workflow

None depends on the language. What checks each one ([zizmor audits](https://docs.zizmor.sh/audits/), read on
2026-11-12): 1 zizmor `excessive-permissions`; 2 zizmor `unpinned-uses` (every action pinned by SHA by default since
zizmor 1.20.0) and `ref-version-mismatch`; 3 review only (zizmor's `concurrency-limits` runs only in its pedantic
persona, which the harness does not use); 4 `job-timeout.py` (zizmor and actionlint do not check it; exceptions with
a reason and the ceiling, default 120, in `.harness/config.json` › `job_timeout`); 5 zizmor `artipacked` and
`template-injection`; 6 review. actionlint checks the workflow syntax and expressions; `docs-security.yml` runs all
three tools.

| # | Invariant | Why |
|---|---|---|
| 1 | `permissions: contents: read` (or `{}`) at the top; write access goes to the job that needs it | a compromised workflow cannot write |
| 2 | Actions pinned by full SHA, version in a comment; Dependabot updates them | a tag can move |
| 3 | `concurrency` with cancellation on PRs, never on a protected branch | a push pays for only one run |
| 4 | `timeout-minutes` on every job | a stuck job costs 6 h by default |
| 5 | `persist-credentials: false`; never an event `${{ … }}` in a `run:` | injection, token leak |
| 6 | Nothing on a draft; required checks pass without a secret (fork PRs) | budget, external contributions |

## 3. Tier 1: the local command first

The baseline does not start with a workflow but with **one command** (`make check`, `cargo xtask ci`,
`pre-commit run --all-files`, `scripts/ci/local-check.sh`) that the agent runs before every push and that CI replays
as is. Without it, "nothing on a draft" means the agent discovers its errors on the move to "Ready",
and every fix costs a run.

- It says **INCOMPLETE** when a tool is missing, never "green".
- It has a fast mode (what changed) and a full mode (what CI runs).
- It writes a readable summary (what ran, what was skipped, why) that the PR reuses.
- `CLAUDE.md` › Build and tests names it. The pre-commit hook runs its fast part.

The harness seeds a skeleton, `scripts/local-check.sh` (exit codes 0 OK, 1 FAILED, 2 INCOMPLETE; never rewritten by
the sync), and the skill `/local-check` fills in its steps from the project's workflows. The harness's own
`scripts/local-check.sh` replays its `ci.yml`, and a test fails if the two drift apart.

## 4. What the survey showed

| Finding | Where | What the baseline takes from it |
|---|---|---|
| 🔴 `issues`, `issue_comment`, `pull_request_target`, `schedule` workflows written but **never run**: they only start from the default branch, and the project works on another one | iOS client | The integration branch **is** the default branch, or these workflows also live on the default branch. And the state of an issue reads without a workflow: a label set by hand is worth a label set by a robot |
| 🔴 macOS jobs without `timeout-minutes`; no dependency cache | iOS client | Invariant 4; cache at tier 2 |
| 🔴 Actions by tag, write access given to the whole workflow, no timeout and no concurrency | configuration repository | Tier 0 and invariants 1 to 4: the repository "too small for CI" is the one with the widest rights |
| 🔴 No secret scan, no CVE audit of dependencies | Rust project | Tiers 0 and 3 |
| 🟠 Secrets inherited in bulk (`secrets: inherit`) by a shared workflow tracked on a branch | Rust project | A reusable workflow is pinned by SHA and receives its secrets by name |
| 🟠 The secret scan runs twice per push (hook replayed + dedicated job; `push` + `pull_request`) | two projects | One check, one place |
| 🟠 No single local entry point | iOS client | Tier 1 |
| 🟢 One local command = CI, with a report of what was skipped | Rust project | The model for tier 1 |
| 🟢 Change detection + immediate failure of macOS jobs on a draft | iOS client | Tier 2 ([CI-BUDGET](CI-BUDGET.md) §2) |
| 🟢 Home-made supply-chain check (lock file up to date, allowed git sources) | Rust project | Tier 3, when a CVE audit is not enough |

## 5. What this baseline calls into question in the harness

1. **"Nothing on a draft" only holds if tier 1 exists.** The harness gave the rule without providing the
   command: it is now the first thing to put in place, before any workflow.
2. **The harness does not apply its own rules everywhere**: its labels are not synced on its own
   repository, and it has no licence file. A harness is judged on itself first.
3. **One job, not ten.** The Linux checks of a tier fit in one job where every step runs even if the
   previous one fails: one run, all the findings, one billed minute. Split it only when a required
   check must be skippable on its own.
4. **Process automation (tier 4) is a convenience, not a foundation**: on the most active project,
   it has been inert for months and tracking still holds, by hand, across 437 issues. The rules must therefore
   stay applicable without it.
5. **AI review in CI is not in the baseline.** It needs a secret, so it cannot be a required check
   (invariant 6); it stays an option.

## 6. Adopting the baseline in a project

1. Tier 1: write the local command, name it in `CLAUDE.md`, have the project's workflow replay it.
2. Tier 0: uncomment the `docs` job of `harness.yml`.
3. Check that the integration branch is the default branch (otherwise the `issue`, `flow`, `settings` jobs
   stay silent). The harness checks it for you: on a first adoption, `harness-sync.sh` stops before writing when
   `.harness/config.json` › `integration_branch` differs from `origin/HEAD`, and gives the two ways out, making it
   the default branch or installing the relay `harness-relay.yml` on the default branch
   ([ADOPTION](ADOPTION.md#integration-branch-that-is-not-the-default-branch)). Afterwards the session-start hook and
   `harness-sync.sh` (also `--check`) print a 🟠 line ("could not check" if `origin/HEAD` is unknown), and
   `pr-hygiene.yml` emits a `::warning::` (input `integration-branch`). `"default_branch_check": false` silences
   all of it for a project that keeps two branches on purpose.
4. Ruleset: required checks = real job names ([CI-BUDGET](CI-BUDGET.md) §4), in `.github/repo-settings.json`.
5. Tiers 2 and 3 depending on the project.

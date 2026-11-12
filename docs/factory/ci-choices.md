# The CI choices of the harness, explained

Part 2 of [the software factory, rethought for agents](README.md). For tech leads and the people who own a project's
CI, who are adopting the harness or judging it.

> **Last checked: 2026-11-11.** GitHub's billing and workflow behaviour change. Every GitHub fact below cites the
> documentation page it comes from, read on that date. The harness's own rules are in
> [CI-BASELINE](../CI-BASELINE.md) and [CI-BUDGET](../CI-BUDGET.md); this page explains them and does not replace
> them. Research notes: [sources/ci-choices-notes.md](sources/ci-choices-notes.md).

**TL;DR**

- Agents push far more commits than people. The harness makes CI cost **per ready lot, not per commit**: drafts run
  nothing, one local command runs what CI runs before every push, and CI confirms on the move to "Ready for review".
- Checks are sorted into **five tiers**, from free to expensive. Tiers 0 and 1 suit every repository; the costly
  ones run late, behind the cheap ones, and only when their files changed.
- Every workflow keeps **six invariants** (minimal rights, actions pinned by SHA, cancellation, timeouts, no
  injection, nothing on a draft).
- Anything that needs a secret, AI review included, is **never a required check**: a pull request from a fork gets
  no secrets.
- Each choice has a cost and a reasonable alternative. Both are given below.

![The five CI tiers of the harness and when each runs: 0 hygiene (secrets, workflow lint, docs) on every ready PR, docs PRs included, about a minute on Linux; 1 quality (lint, tests) locally before every push, then on every ready PR with the same steps; 2 expensive (macOS, simulator, OS matrix) on a ready PR only, after tier 1 and only if its paths changed; 3 heavy security (SAST, dependency CVEs) on ready PRs, the integration branch and every week; 4 process (labels, links, dashboard) on issue and PR events and daily, from the default branch only. On a draft PR nothing costly runs, and required checks pass without a secret](../diagrams/ci-tiers.svg)

## 1. The GitHub facts the choices rest on

| Fact | Source (read 2026-11-11) |
|---|---|
| Hosted runners are billed per minute: Linux 2-core $0.006, macOS 3- or 4-core $0.062, so a macOS minute costs about ten Linux minutes | [Actions runner pricing](https://docs.github.com/en/billing/reference/actions-runner-pricing) |
| "GitHub rounds the minutes and partial minutes each job uses up to the nearest whole minute" | [Actions runner pricing](https://docs.github.com/en/billing/reference/actions-runner-pricing) |
| Each plan includes a monthly amount "expressed as a monetary amount, not a fixed number of minutes" (Free $12, Pro and Team $18) | [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) |
| Standard hosted runners in public repositories, and self-hosted runners, are free | [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) |
| A job with no `timeout-minutes` runs for up to 360 minutes | [Workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax) |
| `pull_request` runs by default only on `opened`, `synchronize`, `reopened`; `ready_for_review` must be listed | [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows) |
| `issues`, `issue_comment` and `schedule` run only "if the workflow file exists on the default branch" | [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows) |
| On a pull request from a fork, no secret but `GITHUB_TOKEN` reaches the runner, and that token is read-only | [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows) |
| A job skipped by a condition reports "Success" to a required check; a workflow skipped by a path or branch filter leaves its checks "Pending" and blocks merging | [Troubleshooting required status checks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks) |

[CI-BUDGET §1](../CI-BUDGET.md#1-the-two-billing-rules) states the billing rules as "2,000 minutes per month" and
"one macOS minute counts as 10", from HFRnow's `ci.yml` and ADR 0005 (its Sources line). The page GitHub publishes
today states the allowance in dollars, not minutes, and no longer speaks of multipliers. The ratio still holds through
the prices, and the rounding rule is unchanged.

## 2. The choices

Each choice: what the harness does, why, what it costs, and what else is reasonable.

### Nothing runs on a draft

| | |
|---|---|
| **Does** | Every CI job of the harness carries `if: github.event.pull_request.draft != true`, and `ready_for_review` is in the trigger types, so the move to "Ready" starts the run ([`ci.yml`](../../.github/workflows/ci.yml)). A project may set a label (`ci: full`) to ask for the full CI on a draft. |
| **Why** | Pushing often to a draft keeps work safe from a crashed session and visible to the other sessions; it must cost nothing ([CI-BUDGET §2](../CI-BUDGET.md#push-often-pay-on-the-move-to-ready)). Invariant 6 ([CI-BASELINE §2](../CI-BASELINE.md#2-the-six-invariants-of-every-workflow)). |
| **Costs** | Errors surface late, at "Ready", unless a local command catches them first (next choices). A required check reported on a draft is a skipped job, which GitHub counts as passed; harmless, since a draft is not merged and "Ready" reruns everything. |
| **Else** | A Linux check of a few seconds on drafts, which CI-BUDGET §2 allows. On a public repository, where standard runners are free, running everything on every push costs no money, only runner time and noise. |

### One push per lot, then one per review round

| | |
|---|---|
| **Does** | Small commits go to the draft. Once the PR is ready: one commit and one push per review round, every finding of the round fixed and checked locally first ([CI-BUDGET §5](../CI-BUDGET.md#5-agentic-volume-many-commits-few-runs), [REVIEW-ROUNDS](../REVIEW-ROUNDS.md#convergence-a-settled-finding-stays-settled) step 6). Never a push "to see if CI passes". Beyond 6 CI-tested pushes on one PR, the orchestrator stops the author ([FINOPS §3](../FINOPS.md#3-quotas-parallelism-and-resuming)); the dashboard counts them ([FINOPS §4](../FINOPS.md#4-watching-for-drift)). |
| **Why** | An agent that pushes per finding pays one full run each time, and each run is rounded up per job. The bound stops a trial-and-error loop that no person is watching. |
| **Costs** | Slower feedback on one finding. A round with a mistake in it costs a whole round. |
| **Else** | Per-commit CI when runner time is free and plentiful (a public repository, self-hosted runners). The bound of 6 is a number to tune per project. |

### One local command, identical to CI

| | |
|---|---|
| **Does** | `scripts/local-check.sh` runs the steps of `ci.yml`, same names, same commands, same order; a test fails if the two drift apart ([CI-BASELINE §3](../CI-BASELINE.md#3-tier-1-the-local-command-first)). It ends with OK (exit 0), FAILED (1) or INCOMPLETE (2) when a tool is missing or a step needs another host, never green ([script header](../../scripts/local-check.sh)). `--quick` runs only the steps whose files changed. The harness seeds a skeleton in each project; the skill `/local-check` fills it from the project's workflows. |
| **Why** | "Nothing on a draft" only works if the agent can find its errors before "Ready" ([CI-BASELINE §5](../CI-BASELINE.md#5-what-this-baseline-calls-into-question-in-the-harness) point 1). CI then confirms; it does not discover. |
| **Costs** | Two copies of every step, kept in step by a test. Tools must exist where the agent runs: in a cloud container without Docker or ShellCheck, the result is INCOMPLETE and the PR has to say which steps did not run ([CONTRIBUTING](../../CONTRIBUTING.md) step 3). |
| **Else** | Any single entry point does the job: `make check`, `cargo xtask ci`, `pre-commit run --all-files` (CI-BASELINE §3). Running the CI workflow itself locally was left out of scope when the command was designed ([#12](https://github.com/francoisgn/belayline-agentic-harness/issues/12)). |

### Five tiers

| | |
|---|---|
| **Does** | 0 hygiene (secrets, workflow lint, Markdown), 1 quality (the local command, lint, tests), 2 expensive (macOS, simulator, OS matrix), 3 heavy security (SAST, dependency CVEs), 4 process (labels, PR linked to an issue, dashboard) ([CI-BASELINE §1](../CI-BASELINE.md#1-the-tiers)). Tiers 0, 3 and 4 are reusable workflows of the harness; tiers 1 and 2 belong to the project. Every row can be switched off. |
| **Why** | The tiers are the common denominator of three real projects surveyed on 2026-11-09, plus what they lacked (CI-BASELINE TL;DR and §4). A tier tells a project what to add next, and in which order. |
| **Costs** | Per ready PR, from that survey: tier 0 about 1 minute on Linux, tier 1 1 to 10, tier 2 10 and more (macOS priced about ten times Linux, §1 above), tier 3 2 to 5, tier 4 seconds (CI-BASELINE §1). The harness imposes no tool for tiers 1 and 2, so it cannot check them for you. |
| **Else** | One pipeline for everything, which suits a small repository with cheap tests. |

### Six invariants in every workflow

| | |
|---|---|
| **Does** | Read-only rights at the top, write only on the job that needs it; actions pinned by full SHA, kept current by Dependabot; `concurrency` that cancels on PRs, never on a protected branch; `timeout-minutes` on every job; `persist-credentials: false` and no event `${{ … }}` inside `run:`; nothing on a draft and required checks that pass without a secret ([CI-BASELINE §2](../CI-BASELINE.md#2-the-six-invariants-of-every-workflow), [CI-BUDGET §3](../CI-BUDGET.md#3-security-baseline) "Workflow hygiene"). zizmor and actionlint check them in CI. |
| **Why** | A tag can move; a compromised workflow with read-only rights cannot write; event text pasted into a shell is an injection. A job without a timeout can hold a runner for 360 minutes (§1). Cancellation means a new push pays for one run, not two. |
| **Costs** | Longer workflow files, Dependabot pull requests for SHA bumps, and two linters in tier 0. |
| **Else** | Tags instead of SHAs for actions from publishers you trust, accepting that a tag can move. |

### One job, every step runs even after a failure

| | |
|---|---|
| **Does** | The Linux checks of a tier fit in one job; each step carries `if: ${{ !cancelled() }}`, so a red step does not hide the next ones ([CI-BASELINE §5](../CI-BASELINE.md#5-what-this-baseline-calls-into-question-in-the-harness) point 3; [`ci.yml`](../../.github/workflows/ci.yml), [`docs-security.yml`](../../.github/workflows/docs-security.yml), [`security.yml`](../../.github/workflows/security.yml)). |
| **Why** | Every job is rounded up to a whole minute (§1): ten jobs of a few seconds cost ten minutes, one job costs one. One run reports every finding, so the agent fixes them in one round. |
| **Costs** | No parallelism; a single required check covers everything, so one red step blocks the whole check. |
| **Else** | Split a job when a required check must be skippable on its own (CI-BASELINE §5 point 3), or when wall-clock time matters more than minutes. |

### Expensive jobs behind cheap ones and behind path detection

| | |
|---|---|
| **Does** | The macOS job `needs:` the Linux job; it starts only if the app or engine paths changed (`git diff --quiet BASE...HEAD -- <paths>`), and runs anyway if detection fails ([CI-BUDGET §2](../CI-BUDGET.md#the-rest) "The rest", [LESSONS](../LESSONS.md) L49). A job skipped this way counts as passed ([CI-BUDGET §4](../CI-BUDGET.md#4-required-checks-and-merge)). |
| **Why** | A red lint must not start a runner priced about ten times Linux (§1). A broken detector must never let a PR through, hence "run anyway". |
| **Costs** | A macOS verdict comes later in the loop. Detection paths must be kept in step with the code layout. |
| **Else** | A workflow-level `paths` filter is simpler, but a workflow skipped by a path filter leaves its required checks "Pending" and blocks the merge (§1). It suits workflows that are not required, such as `paths-ignore` for docs PRs (CI-BUDGET §2). |

### Heavy security on ready PRs, the integration branch and every week

| | |
|---|---|
| **Does** | `security.yml` (Semgrep CE, Trivy, gitleaks in one job) skips drafts and is meant to be called on ready PRs, on the integration branch and by a weekly schedule ([CI-BUDGET §3](../CI-BUDGET.md#3-security-baseline) and [§5](../CI-BUDGET.md#5-agentic-volume-many-commits-few-runs); the weekly cron of [`harness.yml`](../../templates/.github/workflows/harness.yml)). Docs PRs are scanned too: a secret can slip into a `.md`. |
| **Why** | Scanning every push of an agent multiplies minutes for findings that only matter at merge. The weekly run catches a new CVE in a dependency that no commit touched. |
| **Costs** | A problem in a draft is seen only at "Ready"; a new CVE can wait up to a week. The schedule runs only from the default branch (§1). |
| **Else** | A dedicated label for risky flows, or the integration branch only (CI-BUDGET §2 "The rest"). On a public repository, CI-BUDGET §3 prefers GitHub's own scanners. Part 3 of this guide compares the scanners. |

### AI review is never a required check

| | |
|---|---|
| **Does** | The review service `ai-review.yml` runs on `pull_request`, never `pull_request_target`; without its secret, the job is skipped. It posts a comment, never a GitHub approval ([`ai-review.yml`](../../.github/workflows/ai-review.yml) header; [CI-BASELINE §5](../CI-BASELINE.md#5-what-this-baseline-calls-into-question-in-the-harness) point 5). |
| **Why** | It needs an API key, and a pull request from a fork gets no secret (§1): a required AI review would block every outside contribution. A comment, not an approval, keeps a prompt injection in the PR from approving it. |
| **Costs** | No machine gate on AI review. The guarantee is the adversarial review by another model, run by the session before "Ready" ([ORCHESTRATION §3](../ORCHESTRATION.md#3-adversarial-review-by-a-subagent)). |
| **Else** | On a private repository with no outside contributors, a project can decide to require it and own that choice. |

### Required checks pass without secrets

| | |
|---|---|
| **Does** | No required check reads a secret; secrets go by name only to the job that needs it, never on a fork event; never a `pull_request_target` that checks out PR code (invariant 6 of [CI-BASELINE §2](../CI-BASELINE.md#2-the-six-invariants-of-every-workflow); [CI-BUDGET §3](../CI-BUDGET.md#3-security-baseline)). |
| **Why** | Fork PRs get no secrets (§1). A check that depends on one is either always red for outside contributors or tempts someone into `pull_request_target`, which runs with the base repository's rights. |
| **Costs** | Whatever needs a secret (AI review, signing, deploy previews) stays optional. |
| **Else** | Keep such jobs, but outside the ruleset's required checks. |

## 3. What we got wrong first

| First attempt | What showed it was wrong | What replaced it |
|---|---|---|
| A **warning** when the integration branch is not the default branch: session hook, `harness-sync.sh`, `pr-hygiene.yml`, never blocking ([#10](https://github.com/francoisgn/belayline-agentic-harness/issues/10), PR #25). | On the first consumer, the issue, claim and schedule workflows had never been registered by GitHub, because they only lived on the work branch; the PR that would move them stayed a draft for ten days, and every label transition was manual ([#67](https://github.com/francoisgn/belayline-agentic-harness/issues/67)). | A first adoption now **stops before writing** on a mismatch, and a relay workflow committed on the default branch runs those jobs (#67, PR #73; [CI-BASELINE §6](../CI-BASELINE.md#6-adopting-the-baseline-in-a-project) step 3). |
| The rule "nothing on a draft" without a local command to go with it. | Agents found their errors only at "Ready", and each fix cost a run ([CI-BASELINE §5](../CI-BASELINE.md#5-what-this-baseline-calls-into-question-in-the-harness) point 1). | `scripts/local-check.sh` and the skill `/local-check` ([#12](https://github.com/francoisgn/belayline-agentic-harness/issues/12), PR #30). |
| An optional Node exporter for the diagrams: `package.json`, a 3,300-line lockfile, Excalidraw, React, esbuild, Playwright (PR #33). | Never installed by CI, it still needed a round of security overrides, in a repository that promises no dependency ([#57](https://github.com/francoisgn/belayline-agentic-harness/issues/57)). | The tooling left the repository; diagrams are exported outside it and stamped with `render.py --stamp`, and `check-framework.py` refuses any dependency manifest (#57, PR #58). The diagram on this page was made that way. |

The pattern in all three: a rule that relies on someone noticing a warning, or on a tool that is not there, does not
hold under agent volume. What holds is a check that stops, or a command that is always at hand.

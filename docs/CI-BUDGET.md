# CI budget and security baseline

What to put in CI, by tiers: [CI-BASELINE](CI-BASELINE.md). This file says what it costs and how to tool it.

Sources: `ci.yml`, ADR 0005 (and its amendment of 5 November, #477), `CONTRIBUTING.md` §4, `.pre-commit-config.yaml`
of HFRnow; practice proven on other projects (CI and security workflows, local CI script).

## 1. The two billing rules

> **Last checked: 2026-11-12**, on [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
> and [Actions runner pricing](https://docs.github.com/en/billing/reference/actions-runner-pricing). Prices and
> plans change: re-read both pages before you budget.

On a private repository, GitHub includes an amount of money per month, not a number of minutes ("The included
compute usage is expressed as a monetary amount"): $12 on Free, $18 on Pro and Team, $300 on Enterprise Cloud. Each
job is then priced per minute by runner: Linux 2-core $0.006, Windows 2-core $0.010, macOS $0.062. Two rules follow:

- **one macOS minute costs about ten Linux minutes**;
- **every job is rounded up to the next minute** (a 7 s job costs 1 min).

A **public repository pays nothing for standard runners**, macOS included, and gets CodeQL and secret scanning for
free: this is the strongest lever when the project can be public.

## 2. Rules 🟢

### Push often, pay on the move to "Ready"
A push must cost nothing; what costs is the CI it triggers. So:
- **Push early and often to a draft PR**: the work survives a session crash, and it is visible to the other sessions
  and to the operator. On a draft, **nothing costly runs** (macOS, long jobs, heavy security); at most a Linux check
  of a few seconds if the project wants one.
- **The costly CI runs on the move to "Ready for review"**, or on demand through an **explicit label** (e.g.
  `ci: full`) set on a draft when a macOS verdict is really needed before the end.
- **One commit per review round**: all the findings of a round fixed, checked locally, then a single push.
- **Never a push "to see if CI passes" on a ready PR**: the fast checks run locally first (`local-check.sh` or
  equivalent, pre-commit, Mac build if the app changes); CI confirms, it does not discover. Need to try? Move the PR
  back to draft, or set the label on the draft.
- **No minute wasted**: a cancelled run, a skipped job or a docs PR must not start a macOS runner.

The mechanism (a recommendation to adapt; the label name is the project's choice): CI is a reusable workflow, called
by two separate triggers.
```yaml
# .github/workflows/ci.yml: pushes and the move to "Ready"; a draft runs only if it carries the label
on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
concurrency:
  group: ci-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true
jobs:
  ci:
    if: ${{ !github.event.pull_request.draft || contains(github.event.pull_request.labels.*.name, 'ci: full') }}
    uses: ./.github/workflows/ci-jobs.yml   # jobs `linux` then `macos` (needs: linux), names = required checks
---
# .github/workflows/ci-label.yml: the label set on a draft starts the full CI right away
on:
  pull_request:
    types: [labeled]
jobs:
  ci-label:   # another name: its checks (`ci-label / …`) never replace the required checks
    if: ${{ github.event.label.name == 'ci: full' && github.event.pull_request.draft }}
    concurrency:   # at job level: a skipped job (another label) joins no group, cancels nothing
      group: ci-label-${{ github.event.pull_request.number }}
      cancel-in-progress: true
    uses: ./.github/workflows/ci-jobs.yml
```
- `ready_for_review` in the types: CI starts by itself on the move to "Ready".
- Labels are handled in a **separate workflow**, with no workflow-level `concurrency`: another label (`ledger`,
  `status: claimed`…) only produces a skipped job under another name there, which does not cancel the CI in progress
  and does not publish a "skipped" required check on the head (a skipped job counts as passed for a required check,
  §4). The required checks come only from `ci.yml`, which starts again on the move to "Ready".
- A skipped job on a draft does no harm: a draft is not merged, and the move to "Ready" reruns everything.
- Variant when macOS runners are scarce and the macOS job is required: on a draft, run it on a Linux runner that
  fails right away ("draft: macOS CI on the move to Ready") rather than waiting for a runner.

### The rest
- **Group** the Linux checks into one job per workflow (tests + coverage + lint; a single security job).
- **The macOS job depends on the Linux job** (`needs:`): a red lint or test does not start a macOS runner.
- **Change detection**: the iOS build starts only if the app or the engine changes (`git diff --quiet BASE...HEAD --
  <paths>`); if detection fails, it starts anyway (LESSONS L49). `paths-ignore` for docs PRs.
- Long steps (extra configurations, simulator tests) are reserved for **promotions** and
  manual runs.
- After a merge on a protected branch: the Linux checks only (two green PRs can break each other once combined).
- `concurrency` with `cancel-in-progress` on PRs: a new push cancels the run in progress; never on
  protected branches.
- Artifacts (xcodebuild logs) uploaded **only on failure**, short retention.
- Review bots: no review of drafts or of generated files.
- When the quota is exhausted: replay the CI locally before every merge (`local-check.sh` reports "INCOMPLETE" when
  a tool is missing, rather than calling itself green).
- CodeQL and heavy analysis can run only on the integration branch and on the PRs of a dedicated label (risky
  flows).

**Order of magnitude**: measure what a push on a ready PR costs, with and without a change to the app; the figure
guides the settings (change detection, `needs:`, steps reserved for promotions). The dashboard
([FINOPS](FINOPS.md) §4) tracks the billed minutes.

## 3. Security baseline
All free, with no third-party account. Reusable workflow of the harness: `docs-security.yml` (markdownlint, gitleaks,
zizmor, actionlint in one job).

| Need | Public repository | Private repository (without GHAS) |
|---|---|---|
| SAST | CodeQL | Semgrep CE (`p/swift`, `p/secrets`, `p/github-actions`) |
| Dependencies (SCA) | Dependabot + Dependency Review (fails from `moderate`) | Dependabot + Trivy `fs` (HIGH/CRITICAL) |
| Secrets | secret scanning + push protection + gitleaks | gitleaks (full history) |
| Workflows | zizmor + actionlint (+ shellcheck of the `run:` blocks) | same |
| Scripts | ShellCheck via pre-commit | same |
| Syntax | pre-commit: `check-yaml`, `check-json`, `check-merge-conflict`, `check-added-large-files`, `detect-private-key` | same |

The security workflow also runs **every week** (new CVEs without a commit) and on docs PRs (a secret can
slip into a `.md`).

Workflow hygiene (checked by zizmor and by review):
- actions **pinned by full SHA**, version in a comment (`@3d3c…b1 # v7.0.1`); Dependabot (`github-actions`,
  grouped) updates them;
- `permissions: contents: read` (or `{}`) at the top, wider rights only for the job that needs them;
- `actions/checkout` with `persist-credentials: false`;
- never a `${{ … }}` coming from an event in a `run:`: go through `env:`;
- never a `pull_request_target` that checks out the PR's code; every required check passes **without a secret**
  (fork PRs);
- tools run in a container at a fixed version (`semgrep/semgrep:1.122.0`, `aquasec/trivy:0.62.1`,
  `ghcr.io/gitleaks/gitleaks:v8.30.1`, `rhysd/actionlint:1.7.7`, `zizmor==1.31.1`) or a binary with a verified
  SHA-256 digest (SwiftLint);
- pre-commit: hook repositories frozen by SHA (Dependabot does not read this file: update by hand); no
  reformatting hook (test data stays byte for byte).

Full pipeline in one call: `security.yml` (Semgrep CE, Trivy `fs`, gitleaks, in one job; default Semgrep rules
`p/default p/secrets p/github-actions`, add those of the language, e.g. `p/swift`); `docs-security.yml`
for docs and workflows. Call both without doubling gitleaks (input `gitleaks: false` on one of them).

### Secrets and variables: nothing hard-coded
- **No secret in the repository**, not even hand-encrypted, not even in tests: GitHub secrets (repository,
  environment, organisation) or a vault; in a cloud session, the environment's network secrets, never pasted into
  the chat.
- **Non-secret configuration** (URL, project id, region, bucket name) in **variables**:
  `vars.NAME` in workflows, environment variables or a per-environment configuration file on the code side;
  never a hard-coded environment value in the code.
- In a workflow: secrets and variables go through `env:`, never interpolated in `run:`; a secret is given
  only to the job that needs it, and never on a fork event.
- A committed secret is **compromised**: revoke it first, rewrite history afterwards if needed (gitleaks
  should have flagged it: understand why it got through).
- Example files (`.env.example`) with obviously fake values; `.env` in `.gitignore`.

## 4. Required checks and merge
The ruleset's required checks carry the **job names**: renaming a job means updating the ruleset. A
skipped job (`if:` false) counts as passed for a required check: this is what lets the iOS build be skipped without
blocking the PR. CI judges neither UX, nor assumptions about an external system, nor a removed setting: the spec and
the review take care of those (LESSONS L44).

## 5. Agentic volume: many commits, few runs

Agents produce far more commits than a human (ratio tracked by the dashboard, [FINOPS](FINOPS.md) §4).
CI must cost per **ready lot**, not per commit:
- commits stay small and are **pushed often to the draft** (nothing costly runs there); the full CI starts on the
  move to "Ready for review" or on the explicit label (§2); after that, one push per review round;
- fast checks (lint, secrets, unit tests) run **locally before the push** (pre-commit,
  `local-check.sh`): CI confirms, it does not discover;
- change detection and `paths-ignore`: a docs PR does not start the build; heavy security (SAST, SCA)
  runs on ready PRs, the integration branch and every week, not on every push;
- automatic review once per ready head ([REVIEW-SERVICE](REVIEW-SERVICE.md) §3);
- beyond 6 CI-tested pushes on a PR, the loop stops ([FINOPS](FINOPS.md) §3).

## 6. Slow suites: job timeouts, test time limits, waits on events

A job timeout (invariant 4 of [CI-BASELINE](CI-BASELINE.md#2-the-six-invariants-of-every-workflow)) turns a hang into
a red after N minutes. It does not say which test hung, and it does not stop a test that passes at 300 s on a good
day. Seen in HFRnow #801 (2026-11-12): a macOS test job without `timeout-minutes` hung twice in one test step, once
for more than 4 hours until cancelled by hand, once until GitHub cancelled it; its web-view tests took 90 to 330 s
each and failed at the edge of their own waits. The rules below answer what was seen; the causes in that case were not
established. LESSONS L85 to L90 point here.

### Set `timeout-minutes` from measurements
- Take the duration of the job's recent green runs (run history) and set its timeout to about **twice their p95**,
  rounded up. A guess is either too short (red on a slow day) or too long (hours billed for a hang, ×10 on macOS, §1).
- When one step is the risk (the test step of a simulator job), give **that step** its own `timeout-minutes` as well,
  from the same measurement of that step: the other steps do not eat its budget, and the log shows which step stopped.
- A red run can last longer than a green one: on iOS a failing test makes `xcodebuild test` run `simctl diagnose`
  for up to 10 minutes (LESSONS L72). Leave that margin, or the timeout hides the test failure behind a cancellation.
- Measure again when the suite grows. A job often close to its timeout is a slow suite to fix (below), not a timeout
  to raise.
- GitHub, [workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idtimeout-minutes)
  (read 2026-11-12): a job's `timeout-minutes` has "Default: 360"; a step's is "The maximum number of minutes to run
  the step before killing the process. Maximum: 360 for both GitHub-hosted and self-hosted runners", and "Fractional
  values are not supported."

### A time limit per test
Every test that can hang has a **time limit of its own**, set in the test runner, so a hung test fails alone, with its
name, and the next tests still run; the job timeout stays as the outer net. Set the limit from measured durations, as
for the job, with room for the slowest runner. Most test runners have such a setting: use the one your runner
documents, cite its page and the date you read it, and write "to verify" for what the page does not say.

iOS switches, as the official pages state them on **2026-11-12** (Apple pages read through their JSON form,
`https://developer.apple.com/tutorials/data/documentation/<path>.json`):

| Switch | Source | What the source says | Limits, to verify |
|---|---|---|---|
| `xcodebuild -test-timeouts-enabled YES` | `man xcodebuild` ([text read here](https://keith.github.io/xcode-man-pages/xcodebuild.1.html)); Apple, [`executionTimeAllowance`](https://developer.apple.com/documentation/xctest/xctestcase/executiontimeallowance) | man: "Enable or disable test timeout behavior. This value takes precedence over the value specified in the test plan." Apple: "To use this setting, enable timeouts in your test plan or set the `-test-timeouts-enabled` option to `YES` when using `xcodebuild`." | The man page was read on a mirror that states no Xcode version: to verify with `man xcodebuild` on the CI's Xcode. Whether it applies to Swift Testing tests: to verify (neither page names Swift Testing) |
| `xcodebuild -default-test-execution-time-allowance <seconds>` | `man xcodebuild` (same text) | "The default execution time an individual test is given to execute, if test timeouts are enabled." | The man page gives no default. Apple gives one for XCTest's `executionTimeAllowance`: "The default value is 600 seconds, or 10 minutes." Whether it applies to Swift Testing tests: to verify |
| `xcodebuild -maximum-test-execution-time-allowance <seconds>` | `man xcodebuild`; Apple, `executionTimeAllowance` | man: "The maximum execution time an individual test is given to execute, regardless of the test's preferred allowance." Apple: "The test may run for less time than you specify if you customize the Maximum Test Execution Time Allowance setting in the test plan, or if you pass the `-maximum-test-execution-time-allowance` option to `xcodebuild`." | Whether it caps Swift Testing's `.timeLimit`: to verify (Swift Testing sends to "the documentation for the tool you use to run your tests", and that documentation does not name Swift Testing) |
| XCTest `executionTimeAllowance` | Apple, [`executionTimeAllowance`](https://developer.apple.com/documentation/xctest/xctestcase/executiontimeallowance) | "The number of seconds, rounded up to the nearest minute, for a test to run before it fails with a timeout error." "If the duration of a test exceeds this value, it's marked as a failure and the next test runs." | Minute granularity; needs timeouts enabled (first row) |
| Swift Testing `.timeLimit(_:)` (`TimeLimitTrait`) | Apple, [`timeLimit(_:)`](https://developer.apple.com/documentation/testing/trait/timelimit(_:)), [Limiting the running time of tests](https://developer.apple.com/documentation/testing/limitingexecutiontime), [`TimeLimitTrait.Duration`](https://developer.apple.com/documentation/testing/timelimittrait/duration); [swift-testing source](https://github.com/swiftlang/swift-testing/blob/main/Sources/Testing/Traits/TimeLimitTrait.swift) | "You express the duration in minutes, with a minimum duration of one minute." Past it, "the task in which it's running is" cancelled "and the test fails with an issue of kind" `timeLimitExceeded`. "If multiple time limit traits apply to a test, the testing library uses the shortest time limit." On a suite it applies to each test, on a parameterized test to each case. "A granularity of (by default) one minute is applied to tests." Available from Xcode 16 (Swift 6.0) | Minutes only: it catches a hang, not a test that is 30 s too slow (that is the waiting rule below). The runner can impose a shorter maximum; which `xcodebuild` option sets it for Swift Testing: to verify |

### Waits on events, every one bounded
- An async, UI or web-view test **waits on the event** it needs (delegate callback, navigation finished, message
  handler called, an expectation fulfilled or a confirmation), with a bounded wait and a failure message that names
  what never arrived ("navigation to /topic never finished"), not "timed out".
- Never a fixed sleep, never a long polling budget: a sleep is too short on a slow runner and wasted on a fast one, and
  a polling loop fails late and says nothing.
- Every `await` in a test has a bound: the runner's time limit above at least, and for an external event a wait of its
  own, shorter than that limit.

### The slow class in its own job or test plan
- Tests that need a simulator, a web view or the UI run in **their own job** (or their own test plan), in parallel with
  the fast unit tests, both behind the cheap Linux job (`needs:`, §2). A red unit test shows in minutes, and the slow
  job's timeout is sized for the slow class alone.
- Optional: a warm-up step (boot the simulator) before the test step, so start-up time is not charged to the first
  test's limit and the log shows it apart.
- **Cost**: one more runner in parallel. Each job pays its own setup (checkout, then a build, or the transfer of the
  products of `xcodebuild build-for-testing` to a `test-without-building` job) and its own rounding to the minute, ×10
  on macOS (§1). Shorter wait for a verdict, more billed minutes: the project decides from its measurements.

### Not allowed, whatever the pressure
A slow or hung test is never made green by skipping, disabling, quarantining or deleting it, or by loosening its
assertion. One rerun at most, then investigate (LESSONS L47); the fix is the wait, the code or the job layout above.

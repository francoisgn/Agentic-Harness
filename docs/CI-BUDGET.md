# CI budget and security baseline

What to put in CI, by tiers: [CI-BASELINE](CI-BASELINE.md). This file says what it costs and how to tool it.

Sources: `docs/CI.md`, `ci.yml`, `security.yml`, `scripts/ci/local-check.sh` of ios-app_credit-immo; `ci.yml`,
ADR 0005 (and its amendment of 5 November, #477), `CONTRIBUTING.md` §4, `.pre-commit-config.yaml` of HFRnow.

## 1. The two billing rules
On a private repository, the free quota is 2,000 minutes per month, and:
- **one macOS minute counts as 10**;
- **every job is rounded up to the next minute** (a 7 s job costs 1 min).

A **public repository consumes no minutes** (standard runners, macOS included) and gets CodeQL and
secret scanning for free: this is the strongest lever when the project can be public.

## 2. Rules 🟢
- **Draft PR** while working: nothing runs (jobs conditioned on `github.event.pull_request.draft != true`,
  and `ready_for_review` in the event types to start CI on the move to "Ready for review").
- **A single push per lot**, after the local checks (`scripts/ci/local-check.sh` or equivalent) and the Mac build if
  the app changes. No trial push.
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

HFRnow variant (scarce macOS runners): on a draft, the required macOS jobs fail **immediately** on a
Linux runner ("Draft PR") instead of waiting; they run for real on the move to "Ready for review". CodeQL Swift
runs only on the integration branch and on PRs labelled `codeql` (risky flows).

**Order of magnitude (credit-immo, measured on 1 November)**: a push on a PR cost 19 min of quota whatever it touched;
it costs 4 with no change to the app (or on a Linux failure), 14 otherwise. A promotion costs 4 + 30 min.

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
- commits stay local and small; **one push per lot**, as a draft (nothing runs); CI starts on the move to
  "Ready for review";
- fast checks (lint, secrets, unit tests) run **locally before the push** (pre-commit,
  `local-check.sh`): CI confirms, it does not discover;
- change detection and `paths-ignore`: a docs PR does not start the build; heavy security (SAST, SCA)
  runs on ready PRs, the integration branch and every week, not on every push;
- automatic review once per ready head ([REVIEW-SERVICE](REVIEW-SERVICE.md) §3);
- beyond 6 CI-tested pushes on a PR, the loop stops ([FINOPS](FINOPS.md) §3).

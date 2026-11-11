# Research notes: part 2, the CI choices of the harness (#83)

Working notes for [`ci-choices.md`](../ci-choices.md): each fact with the page it comes from and the date it was read.
Kept so the page can be re-checked or reused without redoing the research.

## GitHub documentation, read on 2026-11-11

| Fact | Exact wording read | Source |
|---|---|---|
| Included usage is money, not minutes | "The included compute usage is expressed as a monetary amount, not a fixed number of minutes" | [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) |
| Included compute per month | Free $12, Pro $18, Free for organizations $12, Team $18, Enterprise Cloud $300 (the page equates $300 to 50,000 Linux minutes at $0.006) | same page |
| No "2,000 minutes" figure | the 2,000-minute figure of `docs/CI-BUDGET.md` §1 does not appear on the page | same page |
| Free usage | standard GitHub-hosted runners in public repositories; self-hosted runners; larger runners are billed even on public repositories | same page |
| Per-minute rates | Linux 2-core x64 $0.006; Linux 2-core arm64 $0.005; Linux 1-core $0.002; Windows 2-core $0.010; macOS 3- or 4-core $0.062 (about 10× Linux 2-core) | same page and [runner pricing](https://docs.github.com/en/billing/reference/actions-runner-pricing) |
| No "multiplier" wording | neither page mentions minute multipliers any more | both pages |
| Rounding | "GitHub rounds the minutes and partial minutes each job uses up to the nearest whole minute." | [runner pricing](https://docs.github.com/en/billing/reference/actions-runner-pricing) |
| Default job timeout | `jobs.<job_id>.timeout-minutes`: "Default: 360" | [workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax) |
| Concurrency | "To also cancel any currently running job or workflow in the same concurrency group, specify `cancel-in-progress: true`." | same page |
| Default-branch-only events | `issues`, `issue_comment`, `schedule`: "This event will only trigger a workflow run if the workflow file exists on the default branch." | [events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows) |
| Fork PRs and secrets | "With the exception of `GITHUB_TOKEN`, secrets are not passed to the runner when a workflow is triggered from a forked repository"; "The `GITHUB_TOKEN` has read-only permissions in pull requests from forked repositories." | same page |
| `pull_request` default types | "By default, a workflow only runs when a `pull_request` event's activity type is `opened`, `synchronize`, or `reopened`." (`ready_for_review` must be listed in `types`) | same page |
| Skipped job and required check | a job skipped by a conditional reports "Success" | [troubleshooting required status checks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks) |
| Workflow skipped by a path filter | its checks "stay in a "Pending" state and block merging" (same for branch filters and skip messages) | same page |

Not verified, so not used in the page: whether CodeQL and secret scanning are free on public repositories (stated in
`docs/CI-BUDGET.md` §1 and §3 without an external source).

## Gap found

`docs/CI-BUDGET.md` §1 gives "2,000 minutes per month", "one macOS minute counts as 10" and the rounding rule, with
HFRnow's `ci.yml` and ADR 0005 as sources (its Sources line), not GitHub's documentation. On 2026-11-11 GitHub states
the allowance in dollars and per-minute rates; the ratio macOS / Linux 2-core is still about 10 ($0.062 / $0.006), and
the rounding rule still holds. Changing CI-BUDGET is out of scope of #83: to report to the orchestrator.

## Repository history

| Item | What it says | Source |
|---|---|---|
| #10 | warn (session hook, `harness-sync.sh`, `pr-hygiene.yml`) when the integration branch is not the default branch; never blocks | [#10](https://github.com/francoisgn/belayline-agentic-harness/issues/10), PR #25 |
| #67 | "a warning was not enough": on the first consumer the issue, claim and schedule workflows were never registered, the PR putting them on the default branch stayed a draft for ten days, every label transition was manual. First adoption now stops before writing; relay workflow `harness-relay.yml` | [#67](https://github.com/francoisgn/belayline-agentic-harness/issues/67), PR #73 |
| #12 | the local command identical to CI; "nothing runs on a draft PR: without it I discover my errors when the PR goes Ready" | [#12](https://github.com/francoisgn/belayline-agentic-harness/issues/12), PR #30; `docs/CI-BASELINE.md` §5 point 1 |
| #57 | PR #33 added `package.json`, a 3,300-line `package-lock.json` and `export-svg.cjs` (Excalidraw, React, esbuild, Playwright); it cost a round of security overrides; removed, and `check-framework.py` now refuses any dependency manifest | [#57](https://github.com/francoisgn/belayline-agentic-harness/issues/57), PR #58 |

## Where each choice is made

| Choice | Files and sections |
|---|---|
| Nothing on a draft | CI-BASELINE §2 invariant 6; CI-BUDGET §2 "Push often, pay on the move to Ready"; `ci.yml` (`if: draft != true`, `ready_for_review` in types) |
| One push per lot | CI-BUDGET §2 and §5; REVIEW-ROUNDS §Convergence step 6; FINOPS §3 (6 CI-tested pushes) and §4 |
| local-check | CI-BASELINE §3; `scripts/local-check.sh` header (exit 0 / 1 / 2); CONTRIBUTING step 3; test `scripts/tests/test_local_check.py` |
| Five tiers | CI-BASELINE §1 (costs from the survey of three projects, 2026-11-09) |
| Six invariants | CI-BASELINE §2; CI-BUDGET §3 "Workflow hygiene" |
| One job, every step runs | CI-BASELINE §5 point 3; CI-BUDGET §2 "The rest"; `ci.yml`, `docs-security.yml`, `security.yml` (`if: ${{ !cancelled() }}`) |
| Expensive behind cheap and paths | CI-BASELINE §1 tier 2; CI-BUDGET §2 "The rest", §4; LESSONS L49 |
| Heavy security timing | CI-BASELINE §1 tier 3; CI-BUDGET §3 and §5; `security.yml` header; `templates/.github/workflows/harness.yml` (weekly cron) |
| AI review never required | CI-BASELINE §5 point 5; `ai-review.yml` header |
| Required checks without secrets | CI-BASELINE §2 invariant 6; CI-BUDGET §3 "Workflow hygiene" |

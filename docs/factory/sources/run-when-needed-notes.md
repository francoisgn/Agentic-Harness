# Research notes: run only when needed (part 4, #85)

Raw notes behind [run-when-needed](../run-when-needed.md), kept for later articles. Every fact below was read on
**2026-11-11** on the page named next to it, and re-read unchanged on **2026-11-12** (GitHub documentation, fetched as Markdown through
`https://docs.github.com/api/article/body?pathname=<path>`). Quotes are verbatim.

## Triggers and events

- `pull_request` default activity types: "By default, a workflow only runs when a `pull_request` event's activity
  type is `opened`, `synchronize`, or `reopened`." `ready_for_review` and `converted_to_draft` are separate types.
  Source: [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows).
- `schedule`: "The shortest interval you can run scheduled workflows is once every 5 minutes." "Scheduled workflows
  run on the latest commit on the default branch." "The `schedule` event can be delayed during periods of high loads
  … High load times include the start of every hour. If the load is sufficiently high enough, some queued jobs may be
  dropped." "In a public repository, scheduled workflows are automatically disabled when no repository activity has
  occurred in 60 days." Source: same page.

## Path filters

- "When all the path names match patterns in `paths-ignore`, the workflow will not run."
- Diffs: three-dot for pull requests, two-dot for pushes. Limits: "If a push contains more than 1,000 commits, the
  workflow will **always** run." "If generating the diff times out, the workflow will **always** run." "If the
  generated diff contains more than 3,000 files and the files the workflow filter matches are not in the first 3,000
  returned by the filter, the workflow will **not** run."
- "If a workflow is skipped due to path filtering, branch filtering, or a commit message, then checks associated with
  that workflow will remain in a "Pending" state. A pull request that requires those checks to be successful will be
  blocked from merging."
  Source: [Workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).
- Required checks: "Successful check statuses are `success`, `skipped`, and `neutral`." A job skipped by a
  conditional "reports "Success""; a workflow skipped by a path filter keeps its checks "Pending" and blocks merging
  ("Avoid requiring workflows that can be skipped."); a job that depends on a failed job "is skipped and may not block
  merging" (use `always()` with `needs`).
  Source: [Troubleshooting required status checks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks).

## `needs`

- "If a job fails or is skipped, all jobs that need it are skipped unless the jobs use a conditional expression that
  causes the job to continue." Source: [Workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).

## `concurrency`

- "there can be at most one running job or workflow in a concurrency group at any time … By default, any existing
  `pending` job or workflow in the same concurrency group will be canceled and the new queued job or workflow will
  take its place." "To also cancel any currently running job or workflow in the same concurrency group, specify
  `cancel-in-progress: true`." New `queue` property: `single` (default) or `max` (up to 100 pending);
  `queue: max` with `cancel-in-progress: true` is a validation error.
  Source: [Control the concurrency of workflows and jobs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency).

## Billing of hosted runners

- Included compute usage is now a monetary amount: "The included compute usage is expressed as a monetary amount, not
  a fixed number of minutes". Free and Free for organizations: $12/month; Pro and Team: $18; Enterprise Cloud: $300.
  "Standard GitHub-hosted runners in public repositories" and "Self-hosted runners" remain free and do not reduce it.
  "Larger runners are billed for public repositories." Usage "is charged to the repository owner, not the person who
  triggered the workflow runs." Each Copilot code review consumes Actions compute (free on public repositories).
  Source: [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
- "GitHub rounds the minutes and partial minutes each job uses up to the nearest whole minute." Per-minute rates:
  Linux 2-core x64 $0.006, Linux 2-core arm64 $0.005, Windows 2-core $0.010, macOS 3/4-core $0.062 (about 10× Linux).
  Larger: Linux 4-core $0.012 … 96-core $0.252; macOS 12-core $0.077, macOS 5-core M2 Pro $0.102. "Larger runners are
  only available for organizations and enterprises using the GitHub Team or GitHub Enterprise Cloud plans." "Larger
  runners are not free for public repositories."
  Source: [Actions runner pricing](https://docs.github.com/en/billing/reference/actions-runner-pricing).
- Note: `docs/CI-BUDGET.md` §1 still says "2,000 minutes per month" and "one macOS minute counts as 10"; the vendor
  page now states a dollar amount and per-OS rates (the ratio is still about 10).

## Larger runners

- "managed virtual machines with more resources than standard GitHub-hosted runners": more RAM, CPU, disk, static IP,
  Azure private networking, runner groups, autoscaling, GPU. Billed per minute only while running.
  Source: [Larger runners](https://docs.github.com/en/actions/concepts/runners/larger-runners).

## Self-hosted runners

- "A self-hosted runner is a system that you deploy and manage to execute jobs from GitHub Actions on GitHub." "Are
  free to use with GitHub Actions, but you are responsible for the cost of maintaining your runner machines." "you are
  responsible for updating the operating system and all other software." "Don't need to have a clean instance for
  every job execution." Source: [Self-hosted runners](https://docs.github.com/en/actions/concepts/runners/self-hosted-runners).
- Warning: "We recommend that you only use self-hosted runners with private repositories. This is because forks of
  your public repository can potentially run dangerous code on your self-hosted runner machine by creating a pull
  request that executes the code in a workflow." Source: [Adding self-hosted runners](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners).
- "self-hosted runners should almost never be used for public repositories on GitHub, because any user can open pull
  requests against the repository and compromise the environment." Also private repositories: anyone who can fork and
  open a pull request can compromise the runner, "including gaining access to secrets and the `GITHUB_TOKEN`".
  Source: [Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use).
- Queue: with no online idle runner matching, "the job will remain queued until a runner comes online"; "If the job
  remains queued for more than 24 hours, the job will fail."
  Source: [Self-hosted runners reference](https://docs.github.com/en/actions/reference/runners/self-hosted-runners).

## Per-commit tools

- AI Scan for pull requests: "When enabled, it scans eligible pull requests when they are created and after each new
  commit." Source: [About AI Scan](https://docs.github.com/en/code-security/concepts/code-scanning/ai-scan).
- Copilot code review: automatic review has two options, "Review new pushes" and "Review draft pull requests".
  Source: [Configuring code review by GitHub Copilot](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/configure-automatic-review).

## Operator

- "Observed by the operator (2026-11): a laptop at full CPU for weeks, building several iOS apps for agents."

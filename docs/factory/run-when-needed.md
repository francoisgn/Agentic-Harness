# Run only when needed, and use the edge

Part 4 of [the software factory, rethought for agents](README.md). For CI owners, developers, and whoever pays for
the runners or waits on them.

> **Last checked: 2026-11-12.** GitHub changes its triggers, prices and plans. Every GitHub fact below links the
> documentation page it comes from, read on that date. Re-check them before you decide anything. The raw notes, with
> the exact quotes, are in [sources/run-when-needed-notes.md](sources/run-when-needed-notes.md).

**TL;DR**

- Agents push far more often than people. A chain that runs on every push saturates runners, burns minutes and
  feeds loops. Run a job when someone needs its result: on the move to "Ready for review", when its paths changed,
  and after the cheap checks passed.
- Seven sources of runs can each be cut (§1). The two biggest: pushes to a draft pull request, and review or scanning
  bots that run after every commit.
- Loops (review and fix, CI and fix, bot and agent) are bounded by numbers, not by goodwill: the harness stops a pull
  request after 3 review rounds or 6 CI-tested pushes, and the dashboard shows the ones that get close (§3).
- The edge, the developer's own machine, absorbs the local check and the builds that need its platform, such as iOS
  on a Mac. It is not free: someone's laptop pays in CPU, heat and availability (§4).

![Where each kind of work runs: on the edge, the local check before every push and the iOS build on a Mac; a push goes to a draft pull request where nothing costly runs and no review bot runs; the move to Ready starts one Linux job (lint, tests, scans) and one AI review per head; the expensive macOS or simulator job needs the Linux job and runs only if the app's paths changed. Scheduled work (weekly security scan, daily dashboard, steward after a merge) does not run per push, and a new push cancels the run in progress. A CI job runs on a GitHub-hosted runner (billed per minute, rounded up, free on public repositories), a larger hosted runner (Team or Enterprise plan, billed even on public repositories) or a self-hosted runner (free on GitHub, you pay for the machine, for private repositories)](../diagrams/run-where.svg)

## 1. Where runs come from, and how to cut each source

A **run** here is one workflow run: one or more jobs, each holding a runner for some minutes.

| Source of runs | What happens | How to cut it | What the harness does |
|---|---|---|---|
| **Every push** | An agent pushes small commits often, so the work survives a crash. With the default `pull_request` types (`opened`, `synchronize`, `reopened`), each push to the branch starts CI ([events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)) | Open the pull request as a draft; skip costly jobs while `draft` is true; list `ready_for_review` in the types so CI starts on its own when the pull request is ready. One push per lot, then one per review round | [CI-BUDGET](../CI-BUDGET.md) §2 and §5; the harness's own `.github/workflows/ci.yml` (job skipped on a draft) |
| **Duplicate events** | A workflow on both `push` (with no branch filter) and `pull_request` runs twice for each commit pushed to a pull request branch | `push` only on the integration branch, `pull_request` for the rest; one check in one place | `ci.yml` listens to `push` on `master` only. The survey found a secret scan running twice per push on two projects ([CI-BASELINE](../CI-BASELINE.md) §4) |
| **Jobs unrelated to the diff** | A docs change starts the iOS build | `paths` / `paths-ignore` on the trigger, or change detection inside the job (`git diff --quiet BASE...HEAD -- <paths>`). **When detection fails, run the job anyway** ([CI-BUDGET](../CI-BUDGET.md) §2) | Change detection plus `paths-ignore` for docs ([CI-BUDGET](../CI-BUDGET.md) §2) |
| **Superseded runs** | Three quick pushes give three full runs; only the last result matters | `concurrency` with `cancel-in-progress: true` on pull requests, never on protected branches | Invariant 3 of [CI-BASELINE](../CI-BASELINE.md) §2 |
| **Expensive jobs before cheap ones fail** | The macOS job starts in parallel with lint, which fails after 30 seconds | `needs:` the cheap job: a red lint never starts the macOS runner | Tier 2 sits behind tier 1 ([CI-BASELINE](../CI-BASELINE.md) §1) |
| **Review and scanning bots on every commit** | A bot reviews or scans each new commit of each pull request, drafts included | Review a ready head once, not every push; no review of drafts or generated files | One automatic review per ready head ([REVIEW-SERVICE](../REVIEW-SERVICE.md) §3); the tools themselves are part 3, `docs/factory/review-and-scanning.md` |
| **Scheduled jobs** | A `schedule` runs whether or not anything changed | Keep schedules for what has no commit to react to (new CVEs, drift, a daily dashboard) | Daily dashboard and weekly settings, security and doc audit in `templates/.github/workflows/harness.yml` |

GitHub facts behind the table, read on 2026-11-12:

- **Path filters have edges.** If every changed file matches `paths-ignore`, the workflow does not run. If the diff
  times out, or a push has more than 1,000 commits, the workflow always runs. With more than 3,000 changed files,
  a matching file outside the first 3,000 means the workflow does not run
  ([workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)).
- **A filtered workflow blocks a required check; a skipped job does not.** A workflow skipped by a path filter
  leaves its checks "Pending", which blocks a pull request that requires them. A job skipped by an `if:` reports
  "Success". So filter by path inside the job, not on the trigger, when the check is required
  ([troubleshooting required status checks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks)).
  The harness relies on the second behaviour ([CI-BUDGET](../CI-BUDGET.md) §4).
- **`needs` skips the chain.** "If a job fails or is skipped, all jobs that need it are skipped unless the jobs use a
  conditional expression that causes the job to continue"
  ([workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)).
- **`concurrency`** allows at most one running job or run per group. A newer run replaces the pending one, and
  `cancel-in-progress: true` also cancels the running one
  ([control concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)).
- **Per-commit tools exist.** GitHub's AI Scan for pull requests, when enabled, "scans eligible pull requests when
  they are created and after each new commit" ([About AI Scan](https://docs.github.com/en/code-security/concepts/code-scanning/ai-scan)).
  Copilot code review has two opt-in settings, "Review new pushes" and "Review draft pull requests"
  ([configure automatic review](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/configure-automatic-review)).
  Under an agent's push rate, each of these multiplies by the number of commits.
- **Schedules** can run every 5 minutes at most, run on the default branch, and can be delayed, or dropped under
  high load, around the start of the hour. In a public repository they are disabled after 60 days without
  activity ([events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)).

## 2. What a run costs on GitHub-hosted runners

Read on 2026-11-12 on [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
and [Actions runner pricing](https://docs.github.com/en/billing/reference/actions-runner-pricing):

| Fact | Value |
|---|---|
| Public repository, standard runners | Free; does not reduce the included usage |
| Included usage per month (private repositories) | A dollar amount, not minutes: $12 on Free, $18 on Pro and Team, $300 on Enterprise Cloud |
| Price per minute, standard runners | Linux 2-core $0.006, Windows 2-core $0.010, macOS $0.062 (about ten times Linux) |
| Rounding | Each job is rounded up to the next whole minute |
| Who is billed | The repository owner, not the person (or agent) who triggered the run |
| Self-hosted runners | Free on GitHub's side (§4) |

[CI-BUDGET](../CI-BUDGET.md) §1 still states the rule in minutes (2,000 per month, a macOS minute counts as 10). The
ratio still holds; the unit is now money. Because of the rounding, ten 7-second jobs cost ten minutes, which is
why the harness groups its Linux checks into one job ([CI-BASELINE](../CI-BASELINE.md) §5, item 3).

## 3. Loops

A **loop** is two actors that keep answering each other, with a run, a review or a push each turn.

| Shape | How it starts | Bound in the harness | How to see it |
|---|---|---|---|
| **Review ↔ fix** | Each round fixes the instance a reviewer named, not the class, and the next round finds a sibling | At most 3 review rounds per pull request ([FINOPS](../FINOPS.md) §3) | Dashboard signal "Reviews on a PR > 3" ([FINOPS](../FINOPS.md) §4) |
| **CI ↔ fix** | The agent pushes "to see if CI passes" instead of running the check locally | At most 6 CI-tested pushes per pull request ([FINOPS](../FINOPS.md) §3); the local check first ([CI-BUDGET](../CI-BUDGET.md) §2) | Dashboard signal "CI-tested pushes on a PR > 6" (distinct SHAs; skipped and cancelled runs excluded) |
| **Bot ↔ agent** | A bot comments on each commit, the agent answers each comment with a commit | One review per ready head; a round with no finding ends the loop ([REVIEW-SERVICE](../REVIEW-SERVICE.md) §3) | Same two signals |

Past a bound, the orchestrator stops the author, writes the diagnosis on the issue and reassigns: a stronger model,
a clearer spec, or a human ([FINOPS](../FINOPS.md) §3). The dashboard is the `flow-report.yml` workflow (script
`flow-metrics.py`); it turns 🔴 on a loop ([FINOPS](../FINOPS.md) §4).

## 4. The edge: what the developer's machine can absorb

Two kinds of work fit the edge:

- **The local check.** One command that replays CI before every push ([CI-BASELINE](../CI-BASELINE.md) §3; the
  harness's own is `scripts/local-check.sh`, which says INCOMPLETE when a tool is missing). CI then confirms
  instead of discovering, and "nothing on a draft" stays safe.
- **Builds that need the platform.** An iOS app compiles only on a Mac. A Linux cloud session codes and tests the
  engine; the Mac builds the app, runs the simulator and writes a report the cloud session reads back
  ([MAC-HANDOFF](../MAC-HANDOFF.md) §1 and §3).

The edge has a cost. **Observed by the operator (2026-11): a laptop at full CPU for weeks, building several iOS
apps for agents.** That machine is also someone's work computer. It is not shared, it sleeps, and the queue of
builds depends on one person.

### Between "everything hosted" and "everything local"

| Option | Who pays | What it needs | What breaks |
|---|---|---|---|
| **Everything on standard hosted runners** | The repository owner, per minute (free on public repositories) | Nothing to run | macOS minutes cost about ten times Linux (§2); agents' push rate drains the included usage |
| **The local check as the first gate** | The developer's machine | One command equal to CI, and the discipline to run it before every push | A tool missing locally; the harness reports it as INCOMPLETE, never green ([CI-BASELINE](../CI-BASELINE.md) §3) |
| **Larger hosted runners** | The organization, per minute, also on public repositories | A GitHub Team or Enterprise Cloud plan and a payment method | Cost: macOS 12-core is $0.077 a minute, Linux 96-core $0.252 ([pricing](https://docs.github.com/en/billing/reference/actions-runner-pricing), [larger runners](https://docs.github.com/en/actions/concepts/runners/larger-runners)) |
| **Self-hosted runner** (a Mac mini, a spare machine, a cloud VM) | You pay for the machine and its upkeep; GitHub charges nothing | Someone who installs, updates and secures it | Security on public repositories (below); a machine that is offline: jobs wait, then fail after 24 hours queued; secrets on a machine that also runs pull request code |
| **Everything local** | The developers' machines | Every check runnable locally | No shared referee: "green on my machine" cannot be verified by others. The harness keeps CI as the referee ([MAC-HANDOFF](../MAC-HANDOFF.md) §1) |

**Self-hosted runners, in GitHub's words** (read on 2026-11-12). A self-hosted runner "is a system that you deploy
and manage to execute jobs from GitHub Actions on GitHub". Self-hosted runners "are free to use with GitHub Actions,
but you are responsible for the cost of maintaining your runner machines", you are "responsible for updating the
operating system and all other software", and they "don't need to have a clean instance for every job execution"
([self-hosted runners](https://docs.github.com/en/actions/concepts/runners/self-hosted-runners)). A job with no
online runner stays queued, and "if the job remains queued for more than 24 hours, the job will fail"
([self-hosted runners reference](https://docs.github.com/en/actions/reference/runners/self-hosted-runners)).

GitHub's security warning, quoted:

> "We recommend that you only use self-hosted runners with private repositories. This is because forks of your public
> repository can potentially run dangerous code on your self-hosted runner machine by creating a pull request that
> executes the code in a workflow."
> ([Adding self-hosted runners](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners))

> "self-hosted runners should almost never be used for public repositories on GitHub, because any user can open pull
> requests against the repository and compromise the environment."
> ([Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use))

The same page adds that on private repositories, anyone who can fork and open a pull request can compromise the
runner, "including gaining access to secrets and the `GITHUB_TOKEN`". A laptop that doubles as a runner holds its
owner's credentials too.

## 5. What the harness chose, and what else is reasonable

The harness chose: drafts that cost nothing, CI on the move to "Ready", one Linux job, the expensive job behind
`needs:` and change detection, `concurrency` on pull requests, one automatic review per ready head, numeric loop
bounds, and the local check before every push ([CI-BUDGET](../CI-BUDGET.md), [CI-BASELINE](../CI-BASELINE.md),
[FINOPS](../FINOPS.md)). It runs platform builds on the developer's Mac and keeps hosted CI as the referee. Part 2, [the CI choices of the
harness](ci-choices.md), explains why.

Also reasonable:

- **Make the repository public** when the project can be: standard hosted runners, macOS included, are free there
  (§2).
- **A dedicated self-hosted Mac** for a private project with many iOS builds: it takes the load off a work laptop,
  at the price of upkeep and of the security rules above.
- **Larger hosted runners** when time matters more than money, on a Team or Enterprise plan.
- **A merge queue or a nightly build** in place of per-pull-request expensive jobs, when the team accepts finding a
  platform break later.

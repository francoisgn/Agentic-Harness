# The economics of spawning agents

Part 6 of [the software factory, rethought for agents](README.md). For tech leads and whoever pays for the agents and
the factory around them.

> **Last checked: 2026-11-11.** The few product facts below cite the vendor page they come from, read on that date.
> The harness's own choices point to the file that makes them. Re-check the vendor pages before you decide anything.
> Research notes: [sources/spawn-economics-notes.md](sources/spawn-economics-notes.md).

**TL;DR**

- Agents are affordable when the unit of work is small: a **spawn** (an agent started for one task) gets a short
  context, a model fitted to the task, and is stopped when the task is done. The orchestrator keeps conclusions, not
  the files its children read.
- What a spawn costs, in the harness's terms ([`docs/FINOPS.md`](../FINOPS.md)): the context loaded at start, the
  model tier, and the rounds it takes before a merge.
- Anything sized per human taxes every spawn: state that is not in the repository, review and CI loops, a tool that
  waits for someone to click "allow", a seat, a rate limit shared by the fleet, a credential minted by hand. A tax that
  costs a person a minute a day costs a fleet that minute on every spawn, or stops it.
- The harness measures flow and first-pass quality. It does **not** measure token spend per lot: that number is read
  by hand in the provider's console.

## 1. What a spawn costs

| Cost | What drives it | The harness's lever | File |
|---|---|---|---|
| Context at start | What the child must read before it can act: the brief, the issue, the docs it points to | Context lives in the repository; the brief gives exactly the useful files; docs stay short (`ESSENTIALS.md` first) | [FINOPS](../FINOPS.md) §1, [ORCHESTRATION](../ORCHESTRATION.md) §4 |
| Model tier | The price per token of the model that does the work | The issue's `difficulty:` label picks the tier; it is authoritative | [ORCHESTRATION](../ORCHESTRATION.md) §2, [FINOPS](../FINOPS.md) §2 |
| Rounds | Each review round or CI-tested push re-reads context and re-runs checks | At most 3 review rounds and 6 CI-tested pushes per PR; one clean round ends the loop | [FINOPS](../FINOPS.md) §3, [REVIEW-ROUNDS](../REVIEW-ROUNDS.md) |

Why the sub-agent with a short context and a fitted model is the unit of work:

- **A fresh context is cheaper than a long one.** A long-lived agent drags its old turns along and drifts; a
  disposable one reads the state and starts clean ([FINOPS](../FINOPS.md) §1). In Claude Code, "each subagent runs
  in its own context window" and returns only a summary to the caller
  ([subagents](https://code.claude.com/docs/en/sub-agents), read 2026-11-11).
- **The model is chosen per task, not per session.** A Claude Code subagent takes a `model` field (`haiku`,
  `sonnet`, `opus`, `fable`, a full model id, or `inherit`) ([subagents](https://code.claude.com/docs/en/sub-agents),
  read 2026-11-11). The harness maps its `difficulty:` labels to tiers, not to model names, because names change
  ([ORCHESTRATION](../ORCHESTRATION.md) §2, rule 5).
- **Under- and over-assignment both cost.** A fast tier on a financial rule costs review rounds and bugs; a frontier
  tier on a rename costs tokens for nothing ([FINOPS](../FINOPS.md) §2, rule 1). Review is where the stronger model
  pays most, because reviewing costs far less than writing (same table).
- **A shared prefix is cheaper to re-send.** With the Claude API, a prompt prefix that is exactly identical across
  calls can be read from a cache, at a fraction of the base input price (0.1 times for most models, less for some),
  and the default cache lifetime is 5 minutes ([prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching),
  read 2026-11-11). Stable instruction files loaded first help; whether a given agent product places them in a
  cached prefix is its own business, and the harness does not measure it.

**What the orchestrator keeps, what a child receives.** The orchestrator is the only long-lived agent and keeps a
compressed context: summaries and links to state ([FINOPS](../FINOPS.md) §1). Its memory is one State comment of at
most 6,000 characters, rewritten by a script; the rest of its thread is a log nobody must re-read
([ORCHESTRATION](../ORCHESTRATION.md) §8). A child receives a self-sufficient prompt: its id, the guardrails, the
exact task, stop conditions and the report format ([ORCHESTRATION](../ORCHESTRATION.md) §4). It reports on its PR,
and the orchestrator's memory gets one line with the link. An adversarial reviewer receives less still: the diff, the
spec and the rules, never the author's conclusions ([ORCHESTRATION](../ORCHESTRATION.md) §3).

The harness also says when not to spawn: a task that fits in a few tool calls is not delegated, because the brief
would cost more than the work ([FINOPS](../FINOPS.md) §2, rule 2).

## 2. The taxes on a spawn

A **tax** here is a cost paid again on every spawn, or a limit that a fleet hits long before a person would.

| Tax | Mechanism | How to see it | What the harness does |
|---|---|---|---|
| Context rebuilt | The state lives in a session or a long thread, so each new agent re-reads it, or guesses | Long resume prompts; children asking what was decided. On the first consumer, the orchestrator's memory issue reached 287 comments in 10 days, about 100 k tokens to re-read ([#59](https://github.com/francoisgn/belayline-agentic-harness/issues/59)) | State in issues, PRs and files; one script-written State comment; decisions in `docs/DECISIONS.md` ([ORCHESTRATION](../ORCHESTRATION.md) §4, §8) |
| Review or CI loop | Each round re-reads context, re-runs CI and asks for a new review; fixes to the instance invite the next finding | Dashboard: more than 3 reviews or more than 6 CI-tested pushes on a PR; problem-PR ratio; fix effort | Bounds of 3 rounds and 6 pushes, then stop and reassign; one commit per round; fix the class ([FINOPS](../FINOPS.md) §3, [REVIEW-ROUNDS](../REVIEW-ROUNDS.md)); nothing costly runs on a draft ([CI-BUDGET](../CI-BUDGET.md) §5) |
| A tool that prompts a human | The agent stops until someone approves a tool call. In Claude Code, a background subagent's permission prompt surfaces in the main session and waits there ([subagents](https://code.claude.com/docs/en/sub-agents), read 2026-11-11) | A child with no commit and no comment; the watchdog fires after 30 min | A child inherits only pre-approved tools; durable allow rules go in the versioned `.claude/settings.json` ([ORCHESTRATION](../ORCHESTRATION.md) §4) |
| A per-seat licence | A tool billed per user either needs a seat per agent identity or makes the fleet share one identity, which hides who did what | The licence count against the number of agent identities; actions in the tool's audit log under one person's name | No mandatory third-party account in the harness ([CONTRIBUTING](../../CONTRIBUTING.md) §What does not go in); the in-house review service as an alternative to a review product ([REVIEW-SERVICE](../REVIEW-SERVICE.md)). Identities: `docs/factory/identity.md` |
| An API rate limit shared by the fleet | Every child calls the same service with the same token, so one budget serves them all and parallel spawns fail together | Errors that name a rate limit or a quota in child reports or CI logs. The dashboard does not count them | Parallelism is bounded by the system; a quota reached means a written handoff and a scheduled resume, never a wait loop ([FINOPS](../FINOPS.md) §3). Triggers and runner load: `docs/factory/run-when-needed.md` |
| A credential minted by hand | A child can only do what its session was given; whatever needs a new token or a new grant waits for a person | Child reports that ask for a right. On the first consumer, child sessions could not set labels and 7 reports asked for it ([#59](https://github.com/francoisgn/belayline-agentic-harness/issues/59)) | The author sets no label: the PR body is the entry and the steward does the bookkeeping ([CONVENTIONS](../CONVENTIONS.md) §Ledger); a cloud session reaches only its attached repositories ([ORCHESTRATION](../ORCHESTRATION.md) §4). Credentials: `docs/factory/identity.md` |

The first three are paid in tokens and wall-clock time. The last three are sized per human and do not scale with
the fleet at all: they turn into a queue in front of one person, or into one shared identity.

Observed by the operator (2026-11): one developer can start around a hundred agents and sub-agents in a day
([#80](https://github.com/francoisgn/belayline-agentic-harness/issues/80)). At that pace, a tax that takes a person
one minute per spawn is more than an hour and a half of that person's day.

## 3. What the harness measures, and what it does not

The dashboard is [`scripts/flow-metrics.py`](../../scripts/flow-metrics.py), published by `flow-report.yml`
([FINOPS](../FINOPS.md) §4). It reads issues, PRs and CI runs from the GitHub API.

| Measured | Signal of |
|---|---|
| Claimed issues and PRs with no activity (24 h; 120 h for a draft) | A dead or blocked session, a stalled review |
| CI-tested pushes per PR (distinct SHAs) above 6, reviews per PR above 3 | A loop |
| `status: blocked`, `status: needs-decision` | A bottleneck outside the agent |
| Problem-PR ratio (at least one review finding), agents and humans apart | First-pass quality |
| Fix effort: commits after the first finding, hours from it to the merge | Cost of the second pass |
| Merged PRs, agents and humans; median time from open to merge | Volume and flow |
| CI runs, a lower bound of billed minutes, CI failure rate | CI cost and drift |

Not measured by the harness:

- **Token spend per lot, per session or per model.** The script has no access to it; [FINOPS](../FINOPS.md) §4 says
  it is read by hand in the provider's console and carried into the orchestrator's weekly report. So the harness
  cannot say what one lot cost, and this page gives no cost figure for our projects.
- The number of spawns, the size of each child's context at start, and cache hits.
- Time spent waiting on a permission prompt, rate-limit errors, seats in use, and credentials requested by hand.
  They show up only indirectly: as a stalled claim, or in a child's report.

What else is reasonable: a team whose provider reports usage per API key or per call can give each lot its own key
or tag and sum the usage per lot; a team on a subscription can at least record the console's figure per week next to
the dashboard's merged-PR count. Both are outside the harness today.

## 4. Rules of thumb

These are the harness's choices, each with its file, and what else is reasonable.

| Choice | File | What else is reasonable |
|---|---|---|
| One long-lived orchestrator; every other agent is disposable | [FINOPS](../FINOPS.md) §1 | A few long-lived agents, one per area, if each keeps its state in the repository |
| The `difficulty:` label picks the tier and is authoritative; when in doubt, take the tier above | [ORCHESTRATION](../ORCHESTRATION.md) §2 | Route by measured outcome only, once the problem-PR ratio per tier has enough data ([FINOPS](../FINOPS.md) §2, rule 3) |
| Review by another model, at a tier at least the author's | [ORCHESTRATION](../ORCHESTRATION.md) §2, [FINOPS](../FINOPS.md) §2 | A lower reviewer tier for a type of task, decided by the operator from findings and escaped defects together ([FINOPS](../FINOPS.md) §2, rule 3) |
| Delegate early, but not what fits in a few tool calls | [FINOPS](../FINOPS.md) §2, rule 2 | A larger threshold when briefs are expensive to write, for example in a repository without short docs |
| At most 3 review rounds and 6 CI-tested pushes, then stop and reassign | [FINOPS](../FINOPS.md) §3 | Other bounds, set from the project's own loop data |
| Write state down before a session ends; resume from the State, not from memory | [ORCHESTRATION](../ORCHESTRATION.md) §8, [FINOPS](../FINOPS.md) §1 | A tracker or a database instead of issue comments, as long as children can read it |
| Never poll: schedule a checkpoint or subscribe to events | [ORCHESTRATION](../ORCHESTRATION.md) §4 | Polling with a long interval where the tool offers no events |
| Deliver as soon as ready; a quota is a scheduling constraint, not something to save | [FINOPS](../FINOPS.md) §3 | Reserve some quota for urgent fixes when the team has on-call duty |
| Pre-approve the tools a child needs, in a versioned settings file | [ORCHESTRATION](../ORCHESTRATION.md) §4 | A sandboxed environment where broad permissions are safe, so fewer rules are needed |

Before adding a tool to the factory, ask how it behaves at a hundred spawns a day: does it prompt, does it need a
seat or a hand-made token, and does its limit belong to one person or to the fleet. Parts 4 and 5 treat the triggers
and the credentials: `docs/factory/run-when-needed.md` and `docs/factory/identity.md`.

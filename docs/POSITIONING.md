# Where Belayline sits among agent harnesses

> **Last checked: 2026-11-10.** The projects below change fast. Every statement about a project cites the page it
> comes from and quotes that project's own claims; none of their benchmarks were rerun here.

**TL;DR**

- "Agent harness" names two different things.
  - A **runtime harness** sits between the agent and its tools. Before or after each action it decides, in
    milliseconds, whether to allow, block, ask a human, sandbox or replay that action.
  - Belayline is a **process harness**. It governs the work around those actions: the intent written before any
    code, tests seen failing first, an adversarial review by another model and a code review, every verdict traced,
    bounded loops, a dashboard, and rules that are versioned and updated by pull request.
- The two layers answer different questions:
  - runtime: "may this command run now?";
  - process: "is this change what was asked, is it proven, reviewed and measured, and what do we learn from it?"
- They combine. A runtime guard protects each action; Belayline makes the sequence of actions add up to the right
  change.
- The memory lives in the **repository**, not in the agent. The orchestrator is a **conductor, not a composer**.

## 1. Two layers

| | Runtime harness | Process harness (Belayline) |
|---|---|---|
| Question | May this action run, and did it do what it claimed? | Is this the right change, proven, reviewed and measured? |
| Unit | One tool call | One issue, one lot, one pull request |
| Time scale | Milliseconds to seconds | Hours to days |
| Where the state lives | The proxy's trace, the agent's session | The repository: issues, PRs, docs, ADRs, lessons |
| Typical mechanisms | Allow, deny or ask rules; sandboxes; MCP proxies; replay against real state; per-action approval | Intent and definition of done; TDD; an adversarial review and a code review; traced verdicts; bounded loops; stewards; dashboard; pluggable compliance; versioned rules |
| Who decides | A rule engine, sometimes a human per action | The operator, through the orchestrator, at defined checkpoints |

Belayline has one runtime guard of its own: `guard-git`, an agent hook (Claude Code, before each shell command)
that refuses force-pushes, pushes to protected branches and `--no-verify`.
For anything else at runtime, it relies on the agent's own permission settings, or on a dedicated tool
([#46](https://github.com/francoisgn/belayline-agentic-harness/issues/46)).

## 2. The elephant, the goldfish, and the repository

An agent that keeps everything in its own context is an **elephant**. It remembers, but every turn re-reads a
growing history, so it costs more and drifts more. And it forgets everything when the session ends. An agent that
starts empty each time is a **goldfish**: cheap, but it redoes the same work.

Belayline lets agents be goldfish because **the repository is the elephant**:

- the plan, the decisions, the progress and the lessons are written in issues, PRs, ADRs and docs;
- an agent you stop loses nothing;
- an agent you start reads the state and carries on ([FINOPS](FINOPS.md) §1).

The orchestrator is the only long-lived agent. Its context is kept short: summaries and links to the state.

The orchestrator is a **conductor, not a composer**:

- it does not write the code;
- it reads the score, which is the issue's intent;
- it gives each part to the right player, a lot agent of the right model tier;
- it keeps time with the bounded loops;
- it has the result checked by another model.

This is the split described in [ORCHESTRATION](ORCHESTRATION.md) and [FINOPS](FINOPS.md) §1–§2.

## 3. The projects we looked at

| Project | Layer | What it says it does | Licence, maturity (as read) |
|---|---|---|---|
| [haqaliz/belay](https://github.com/haqaliz/belay) ([vision](https://github.com/haqaliz/belay/blob/master/VISION.md), [PyPI `belay-harness`](https://pypi.org/project/belay-harness/0.13.0/)) | Runtime: verification | A proxy between an agent and its MCP servers that sandboxes, then replays each step against real state. Verdicts: PASS, WARN, FAIL, UNVERIFIED. It only sees MCP traffic | Apache-2.0, alpha |
| [SECBLOK/belay](https://github.com/SECBLOK/belay) | Runtime: security | Gates tool calls (Deny > Ask > Allow, fail-closed), with canary files, a hash-chained audit log and SARIF scans; "no LLM in the decision path" | AGPL-3.0 plus a commercial edition |
| [mikepenz/agent-belay](https://github.com/mikepenz/agent-belay) | Runtime: human approval | A desktop app that receives each tool call through hooks and lets a human approve it, with "Always Allow" patterns. Optional risk scoring 1–5 by an LLM; experimental local cost tracking | Apache-2.0; macOS, Windows, Linux (prebuilt packages for macOS only) |
| [hev/belaykit](https://github.com/hev/belaykit) | Library | One Go interface over the `claude` and `codex` CLIs, with tracing and a Slack notifier | No licence file found |
| [sacuadros/agent-harness](https://github.com/sacuadros/agent-harness) | Distribution of rules | One source of rules, skills, subagents and guard hooks, rendered into each agent's own files. Fail-closed guards; a scope check on turns that reach 5 files or 150 lines | MIT, tests |
| [latintzar/harness](https://github.com/latintzar/harness) | Application platform | A Codex-based harness with generative UI for business "verticals": scoped files, approvals, spend accounting | MIT |
| [arXiv 2610.25568](https://arxiv.org/html/2610.25568v1) | Research | A planner, worker and reviewer harness evaluated on four benchmarks (Spine AI, 18 Oct 2026) | CC BY 4.0 |

Of these, sacuadros/agent-harness is the closest to Belayline. It also spreads one set of rules across several
agents. It works on the developer's machine, while Belayline works through the repository.

The name "belay" is used by several of these tools; Belayline's Claude Code plugin is also called `belay`
([#50](https://github.com/francoisgn/belayline-agentic-harness/issues/50)).

## 4. What Belayline adds, and what it leaves to others

Belayline adds what a runtime layer does not see. Each item points to the doc that defines it:

- **intent before code**: user story, error behaviours, definition of done ([METHODOLOGY](METHODOLOGY.md) §2 bis);
- **proof by tests seen failing first** ([METHODOLOGY](METHODOLOGY.md) §2 ter);
- **two separate reviews** ([REVIEW-ROUNDS](REVIEW-ROUNDS.md)): the adversarial review checks the change against
  the issue's intent, by another model isolated from the author; the code review checks the diff, through
  the project's review service;
- **every verdict traced on the PR**, so first-pass quality can be measured;
- **bounded loops**: 3 review rounds and 6 CI-tested pushes per PR ([FINOPS](FINOPS.md) §3);
- **stewards**, a dashboard and a status report ([STEWARDS](STEWARDS.md));
- **pluggable compliance reviewers** ([COMPLIANCE](COMPLIANCE.md));
- **lessons that move from project to project**;
- **rules vendored at a version** and updated by PR ([ADOPTION](ADOPTION.md));
- **efficiency at the level of the split**: the right model tier for each task, early delegation, bounded loops
  ([FINOPS](FINOPS.md) §2–§3). The harness does not collect or compute token usage (an operator may read the
  trend in the provider's console, FINOPS §4), does not compare an API key with a subscription, and does not
  compute anyone's return on investment: each user knows their own economics. It offers a layer that makes the work
  more efficient, not a verdict on what it should cost.

It leaves to the agent's own permissions, or to a runtime tool:

- gating each action;
- sandboxing;
- replaying tool calls;
- secret and egress rules;
- an audit log of every command.

## 5. What we take from them

An idea seen elsewhere is not enough to enter the harness:
[SCOPE.md](https://github.com/francoisgn/belayline-agentic-harness/blob/master/SCOPE.md)
asks for a failure observed in a real project. Ideas that fail that bar are recorded in
[`.out-of-scope/`](https://github.com/francoisgn/belayline-agentic-harness/blob/master/.out-of-scope/README.md).

| Idea | From | Status |
|---|---|---|
| A verdict never hides what was not verified ("UNVERIFIED is never dressed up as PASS") | haqaliz/belay | Taken: a reviewer could not verify a sourced fact and the verdict line could not say so ([#40](https://github.com/francoisgn/belayline-agentic-harness/issues/40)) |
| Decide what a broken guard does: fail open or fail closed | sacuadros/agent-harness, SECBLOK/belay | Open question, no failure observed yet ([#41](https://github.com/francoisgn/belayline-agentic-harness/issues/41)) |
| Measure whether reviews prevent real defects | arXiv 2610.25568 | Open question, no failure observed yet ([#42](https://github.com/francoisgn/belayline-agentic-harness/issues/42)) |
| A size threshold for a lot | sacuadros/agent-harness | Open question, no failure observed yet ([#44](https://github.com/francoisgn/belayline-agentic-harness/issues/44)) |
| Rules rendered into each agent's own format | sacuadros/agent-harness | Declined: no consumer project uses those agents ([record](https://github.com/francoisgn/belayline-agentic-harness/blob/master/.out-of-scope/single-source-per-tool.md)) |
| A runtime guardrail as a replaceable building block, with an audit log | SECBLOK/belay, mikepenz/agent-belay | Open question, no failure observed yet ([#46](https://github.com/francoisgn/belayline-agentic-harness/issues/46)) |

What we do not take:

- **An LLM that scores the risk of each action.** The judge can be fooled by the same injected text as the agent.
  SECBLOK/belay keeps models out of its decision path ("no LLM in the decision path").
- **A human approval for every action.** In our view, approvals asked too often stop being read; the tools that
  offer it mitigate this (agent-belay's "Always Allow" patterns, SECBLOK/belay asking only when its rules do not
  decide). Belayline keeps human confirmation for consequential actions ([ESSENTIALS](ESSENTIALS.md) §Guardrails).
- **Token and spend accounting per run.** Belayline's FinOps stays at the level of the split; users judge their own
  costs ([record](https://github.com/francoisgn/belayline-agentic-harness/blob/master/.out-of-scope/token-cost-accounting.md)).

## 6. What the evidence says

The paper [arXiv 2610.25568](https://arxiv.org/html/2610.25568v1) describes a harness close to Belayline's design:

- the original objective is kept separate from the plan;
- the reviewer can be instructed to re-derive the facts from the original request rather than trust the worker;
- workers get summaries and references, not full histories;
- follow-up rounds are capped.

That matches Belayline's adversarial review, its context in the repository and its bounded loops.

The paper also warns against reading too much into its own results:

- On a paired subset of 53 tasks, the harness raised the mean score by about 20 points but lowered the median
  slightly, at about seven times the cost. The Opus-configured arm lowered the mean
  slightly (−1.06).
- In one case, the review step disrupted a working environment, although the final official checks passed.
- The authors conclude: "do not imply that additional agents or review necessarily improve outcomes".
- The study ran no ablations and used single runs.

Belayline's answer is to measure review value rather than assume it
([#42](https://github.com/francoisgn/belayline-agentic-harness/issues/42)).

## Sources

All read 2026-11-10.

- https://github.com/haqaliz/belay
- https://github.com/haqaliz/belay/blob/master/VISION.md
- https://pypi.org/project/belay-harness/0.13.0/
- https://github.com/SECBLOK/belay
- https://github.com/mikepenz/agent-belay
- https://github.com/hev/belaykit
- https://github.com/sacuadros/agent-harness
- https://github.com/latintzar/harness
- https://arxiv.org/html/2610.25568v1

Not read: the Medium article "How to build an agent harness that decides in 0.65 seconds" (blocked by a Cloudflare
challenge).

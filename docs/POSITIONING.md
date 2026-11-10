# Where Belayline sits among agent harnesses

> **Last checked: 2026-11-10.** The projects below change fast. Every statement about a project cites the page it
> comes from and quotes that project's own claims; none of their benchmarks were rerun here.

**TL;DR**

- "Agent harness" names two different things.
  - A **runtime harness** sits between the agent and its tools. Before or after each action it decides, in
    milliseconds, whether to allow, block, ask a human, sandbox or replay that action.
  - Belayline is a **process harness**. It governs the work around those actions: the intent written before any
    code, tests seen failing first, two separate reviews by another model with every verdict traced, bounded loops,
    a dashboard, and rules that are versioned and updated by pull request.
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
| Typical mechanisms | Allow, deny or ask rules; sandboxes; MCP proxies; replay against real state; per-action approval | Intent and definition of done; TDD; an intent review and a code review; traced verdicts; bounded loops; stewards; dashboard; pluggable compliance; versioned rules |
| Who decides | A rule engine, sometimes a human per action | The operator, through the orchestrator, at defined checkpoints |

Belayline has one runtime guard of its own, a git hook that refuses force-pushes and pushes to protected branches.
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
| [SECBLOK/belay](https://github.com/SECBLOK/belay) | Runtime: security | Gates tool calls (Deny > Ask > Allow, fail-closed), with canary files, a hash-chained audit log and SARIF scans, "no LLM in the decision path by default" | AGPL-3.0 plus a commercial edition |
| [mikepenz/agent-belay](https://github.com/mikepenz/agent-belay) | Runtime: human approval | A desktop app that receives each tool call through hooks and lets a human approve it. Risk scoring 1–5 by an LLM; local cost tracking | Apache-2.0, macOS builds |
| [hev/belaykit](https://github.com/hev/belaykit) | Library | One Go interface over the `claude` and `codex` CLIs, with tracing and a Slack notifier | Early |
| [sacuadros/agent-harness](https://github.com/sacuadros/agent-harness) | Distribution of rules | One source of rules, skills, subagents and guard hooks, rendered into each agent's own files. Fail-closed guards; a scope check on turns that reach 5 files or 150 lines | MIT, tests |
| [latintzar/harness](https://github.com/latintzar/harness) | Application platform | A Codex-based harness with generative UI for business "verticals": scoped files, approvals, spend accounting | MIT, early |
| [arXiv 2610.25568](https://arxiv.org/html/2610.25568v1) | Research | A planner, worker and reviewer harness evaluated on four benchmarks (Spine AI, 18 Oct 2026) | CC BY 4.0 |

Of these, sacuadros/agent-harness is the closest to Belayline. It also spreads one set of rules across several
agents. It works on the developer's machine, while Belayline works through the repository.

The name "belay" is used by several of these tools; Belayline's Claude Code plugin is also called `belay`
([#50](https://github.com/francoisgn/belayline-agentic-harness/issues/50)).

## 4. What Belayline adds, and what it leaves to others

Belayline adds what a runtime layer does not see. Each item points to the doc that defines it:

- **intent before code**: user story, error behaviours, definition of done ([METHODOLOGY](METHODOLOGY.md) §2 bis);
- **proof by tests seen failing first** ([METHODOLOGY](METHODOLOGY.md) §2 ter);
- **two separate reviews**: the intent review checks the change against the issue, by another model isolated from
  the author; the code review checks the diff ([REVIEW-ROUNDS](REVIEW-ROUNDS.md));
- **every verdict traced on the PR**, so first-pass quality can be measured;
- **bounded loops**: 3 review rounds and 6 CI-tested pushes per PR ([FINOPS](FINOPS.md) §3);
- **stewards**, a dashboard and a status report ([STEWARDS](STEWARDS.md));
- **pluggable compliance reviewers** ([COMPLIANCE](COMPLIANCE.md));
- **lessons that move from project to project**;
- **rules vendored at a version** and updated by PR ([ADOPTION](ADOPTION.md)).

It leaves to the agent's own permissions, or to a runtime tool:

- gating each action;
- sandboxing;
- replaying tool calls;
- secret and egress rules;
- an audit log of every command.

## 5. What we take from them

| Idea | From | Issue |
|---|---|---|
| A verdict never hides what was not verified ("UNVERIFIED is never dressed up as PASS") | haqaliz/belay | [#40](https://github.com/francoisgn/belayline-agentic-harness/issues/40) |
| Decide what a broken guard does: fail open or fail closed | sacuadros/agent-harness, SECBLOK/belay | [#41](https://github.com/francoisgn/belayline-agentic-harness/issues/41) |
| Measure whether reviews prevent real defects | arXiv 2610.25568 | [#42](https://github.com/francoisgn/belayline-agentic-harness/issues/42) |
| Token cost per run, not read by hand | latintzar/harness, mikepenz/agent-belay | [#43](https://github.com/francoisgn/belayline-agentic-harness/issues/43) |
| A size threshold for a lot | sacuadros/agent-harness | [#44](https://github.com/francoisgn/belayline-agentic-harness/issues/44) |
| Rules rendered into each agent's own format | sacuadros/agent-harness | [#45](https://github.com/francoisgn/belayline-agentic-harness/issues/45) |
| A runtime guardrail as a replaceable building block, with an audit log | SECBLOK/belay, mikepenz/agent-belay | [#46](https://github.com/francoisgn/belayline-agentic-harness/issues/46) |

What we do not take:

- **An LLM that scores the risk of each action.** The judge can be fooled by the same injected text as the agent.
  SECBLOK/belay keeps models out of its decision path by default.
- **A human approval for every action.** After a few dozen, approvals stop being read. Belayline keeps human
  confirmation for consequential actions ([ESSENTIALS](ESSENTIALS.md) §Guardrails).

## 6. What the evidence says

The paper [arXiv 2610.25568](https://arxiv.org/html/2610.25568v1) describes a harness close to Belayline's design:

- the original objective is kept separate from the plan;
- the reviewer re-derives the facts from the original request rather than trusting the worker;
- workers get summaries and references, not full histories;
- follow-up rounds are capped.

That matches Belayline's intent review, its context in the repository and its bounded loops.

The paper also warns against reading too much into its own results:

- On a paired subset of 53 tasks, the harness raised the mean score by about 20 points but lowered the median
  slightly, at about seven times the cost.
- In one case, the review step disrupted a working machine.
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

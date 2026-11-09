# Stewards: upkeep roles and status report

A **steward** is a disposable, specialised agent that maintains a shared asset of the project so that lot agents
work fast: the issue queue, the documentation, the flow. It is started by the orchestrator or by a scheduled
workflow, does one pass, reports, and stops ([FINOPS](FINOPS.md) §1). Definitions vendored in
`.claude/agents/`; call: "use the `issue-steward` subagent on …".

| Role | Agent | Tier | When | May write |
|---|---|---|---|---|
| Orchestrator (SPOC) | main session | solid | always | issues, comments, child sessions |
| Issue steward | `issue-steward` | fast | new issue, every day, before a wave of lots | labels, triage comments; **proposes** merges and closures |
| Doc steward | `doc-steward` | solid | after a merge that touches behaviour, every week | a docs PR (draft) |
| Flow monitor | `flow-monitor` (read-only); `flow-report.yml` writes the issue | fast | every day | nothing (the workflow maintains the "Project dashboard" issue) |
| Adversarial reviewer | `adversarial-reviewer` | ≥ author, other model | before "Ready for review" | nothing (read-only) |
| Review service | `ai-review.yml` | solid / frontier | every ready PR | a PR review ([REVIEW-SERVICE](REVIEW-SERVICE.md)) |
| Compliance reviewers | `compliance-*` | frontier | diff in their scope | nothing ([COMPLIANCE](COMPLIANCE.md)) |

## 1. Issue steward: a queue ready to be claimed

Goal: a lot agent can claim an issue **without asking a question**.
- Complete axis labels (type, priority, difficulty, status); `status: needs-decision` with the exact question when a
  decision is missing; `status: blocked` with the prerequisite; `needs: host` if needed.
- Usable intent: user story, error behaviours, definition of done ([METHODOLOGY](METHODOLOGY.md) §2);
  otherwise a comment that lists what is missing.
- Duplicates: proposes the merge (the oldest wins), never closes on its own what someone else wrote.
- Routing: milestone, lot, dependencies (`Depends on #n`), sub-issues of the umbrella issue; `difficulty: hard`
  spanning several layers → proposes a split into lots.
- Abandoned claims (> 24 h with no activity): reports them to the orchestrator, does not take them over.

## 2. Doc steward: docs that stay true and readable

- Compares the docs with the merged code: described behaviour = delivered behaviour (LESSONS L08), live links and
  anchors, unbroken tables (L07). What has drifted: a docs PR, an issue if the code is at fault.
- Readable by a human: one file one role (L10), stable headings, TL;DR at the top of long docs, **a diagram** when
  a flow or an architecture is better described as a picture (Excalidraw for the README and overviews, versioned
  source and render checked in CI; Mermaid in Markdown for a short flow).
- Keeps the overviews up to date: README to the standard ([README-STANDARD](README-STANDARD.md): badges, image,
  Excalidraw architecture diagram, lot progress, Contributing), lot plan, ADR index.

## 3. Flow monitor: see drift early

Reads the dashboard ([FINOPS](FINOPS.md) §4), and for each 🔴 or 🟠 names the action and its owner. It
fixes nothing itself: it alerts the orchestrator, which stops a loop, nudges a stalled PR or escalates a bottleneck.

## 4. Status report for a non-technical audience

Produced by the orchestrator (skill `/status-report`), from the dashboard and the issues. No jargon, no
SHAs, clickable links.

```text
# Status of project <name> — week of <date>

TL;DR: 🟢|🟠|🔴 <one sentence: where we are, what matters>

| Milestone | Progress | Due date | State |
|---|---|---|---|
| Milestone 1: <readable name> | ███████░░░ 70 % (7/10) | <date> | 🟢 on time |

Delivered this week: <3 to 5 user-oriented bullets, with links>
Next step: <3 bullets>
Blockers and pending decisions: <who must decide what, by when>
Risks: 🔴/🟠 <risk> → <measure>
Quality: <x> % of PRs with a review finding (agents <a> %, humans <h> %), <n> fix commits on average
Cost: <CI minutes, token trend> (FINOPS)
```

Categories taken from the labels (type, priority, project area), GitHub milestones, assignees and
lots; a bottleneck is always worded as "who must do what".

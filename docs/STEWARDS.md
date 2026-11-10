# Stewards: upkeep roles and status report

A **steward** is a disposable, specialised agent that maintains a shared asset of the project so that lot agents
work fast: the issue queue, the documentation, the flow. It is started by the orchestrator or by a scheduled
workflow, does one pass, reports, and stops ([FINOPS](FINOPS.md) §1). Definitions vendored in
`.claude/agents/`; call: "use the `issue-steward` subagent on …".

| Role | Agent | Tier | When | May write |
|---|---|---|---|---|
| Orchestrator (SPOC) | main session | solid | always | issues, comments, child sessions |
| Issue steward | `issue-steward` | fast | new issue, every day, before a wave of lots | labels, triage comments; **proposes** merges and closures |
| Doc steward | `doc-steward`; `doc-steward.yml` | solid | at each merge into the integration branch; weekly audit | one docs PR (draft); audit issues |
| Flow monitor | `flow-monitor` (read-only); `flow-report.yml` writes the issue | fast | every day | nothing (the workflow maintains the "Project dashboard" issue) |
| Adversarial reviewer | `adversarial-reviewer` | ≥ author, other model | before "Ready for review" | nothing (read-only) |
| Review service | `ai-review.yml` | solid / frontier | every ready PR | a PR review ([REVIEW-SERVICE](REVIEW-SERVICE.md)) |
| Compliance reviewers | `compliance-*` | frontier | diff in their scope | nothing ([COMPLIANCE](COMPLIANCE.md)) |

## 1. Issue steward: a queue ready to be claimed

Goal: a lot agent can claim an issue **without asking a question**.
- Complete axis labels (type, priority, status, and difficulty if the project has that axis: METHODOLOGY §4);
  `status: needs-decision` with the exact question when a decision is missing; `status: blocked` with the
  prerequisite; `needs: host` if needed.
- Usable intent: user story, error behaviours, definition of done ([METHODOLOGY](METHODOLOGY.md) §2);
  otherwise a comment that lists what is missing.
- Duplicates: proposes the merge (the oldest wins), never closes on its own what someone else wrote.
- Routing: milestone, lot, dependencies (`Depends on #n`), sub-issues of the umbrella issue; `difficulty: hard`
  spanning several layers → proposes a split into lots.
- Abandoned claims (an active `/claim` with no activity for 24 h): reports them to the orchestrator, does not take them over.

## 2. Doc steward: docs that stay true and readable

Docs are kept true at three levels, from the cheapest to the widest:

| Level | When | Who | What |
|---|---|---|---|
| **Per PR** | every ready PR, no agent | the author; `pr-hygiene.yml`, `docs-security.yml` | a `Docs:` line declares the doc impact ([CONVENTIONS](CONVENTIONS.md) §Ledger; a warning if missing); deterministic checks in the existing docs job: README standard, diagram renders up to date, relative links and cross-file anchors (`doc-links.py`), tables and in-file anchors (markdownlint) |
| **At merge** | after each merge into the integration branch | `doc-steward.yml`, mode `merge` (opt-in) | folds the ledger, updates the files the merged PRs' `Docs:` lines name, refreshes the README progress block: **one** draft docs PR |
| **Weekly safety net** | every week | `doc-steward.yml`, mode `audit` | audit only: README standard, links, diagram renders, progress block; **one issue per gap**, no doc rewritten |

**At merge** (reusable `doc-steward.yml`, job `steward` of `harness.yml`, opt-in):
- `doc-steward.py pending` decides **without an agent**: merged PRs still labelled `ledger`, or merged since the last
  steward PR with a `Docs:` line that names files. Nothing → the run ends after one short Linux job.
- Otherwise: the project's `ledger.fold_command` folds the ledger, `readme-progress.py` rewrites the progress block,
  and the agent (`doc-steward`, read-only token) edits only the files the `Docs:` lines name. A job without an agent
  then opens or updates **one** draft PR from `docs/steward`, rebuilt from the integration branch at every pass; it
  never pushes to a protected branch, never touches `.github/` or `.harness/`, and does not overwrite a branch that
  carries someone else's commits.
- The PR body carries `Steward-Through: <time>` (the next pass starts there) and `Folded: #a #b` (after its merge,
  the next pass swaps `ledger` for `ledger: done` on these PRs). Entries it cannot place stay in their PR and are
  listed in the docs PR, never dropped. Several merges queue in one concurrency group: one pass covers them all.
- No `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN`: skipped with a notice; never a required check. A merged fork
  PR has no secret: the next pass folds it. A pass that changes nothing opens no PR (and does not move the marker).

**Weekly** (`doc-steward.yml`, mode `audit`, no agent, no secret): `readme-check.py`, `doc-links.py`,
`diagrams-render.py --check`, `readme-progress.py --check`; `doc-steward.py audit` files one issue per gap (label
`type: docs`, none if an open issue has the same title, at most 10 per run). On demand, the `doc-steward` agent does
the full review below:
- Compares the docs with the merged code: described behaviour = delivered behaviour (LESSONS L08), live links and
  anchors, unbroken tables (L07). What has drifted: a docs PR, an issue if the code is at fault.
- Readable by a human: one file one role (L10), stable headings, TL;DR at the top of long docs, **a diagram** when
  a flow or an architecture is better described as a picture (Excalidraw for the README and overviews, versioned
  source and render checked in CI; Mermaid in Markdown for a short flow).
- Keeps the overviews up to date: README to the standard ([README-STANDARD](README-STANDARD.md): badges, image,
  Excalidraw architecture diagram, lot progress, Contributing), lot plan, ADR index.
- Checks the repository identity ([CONVENTIONS](CONVENTIONS.md) §Repository identity): description and topics filled
  in `.github/repo-settings.json`, banner shown at the top of the README, social preview versioned (1280×640), all
  true to the project's intent; missing or out of date → an issue, or the docs PR for the description and topics
  (uploading the social preview in the settings is the operator's job).
- If the project keeps a ledger ([CONVENTIONS](CONVENTIONS.md) §Ledger): the merge pass above runs the project's
  fold command (`.harness/config.json` → `ledger.fold_command`) in the one docs PR; malformed entries are reported
  in that PR, and the folded PRs are marked `ledger: done` once it is merged.

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

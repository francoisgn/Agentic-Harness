# Method: issue-driven work

How an idea becomes a merged PR, whatever the project. Sources: `AGENTS.md` §5–§9 and `docs/LOTS.md` of
HFRnow (lot loop, plan, claims, definition of "done"); practice proven on other projects (issue-driven workflow).

## 1. What lives where: shared state

Sessions (cloud, Mac, humans, other agents) coordinate **only** through visible state. The scratchpad, an agent's
memory and `/tmp` do not count.

| Where | Role |
|---|---|
| **Issues** | The **tracking**: one issue per lot, bug, feedback point, task; claim, status labels, blockers |
| **PRs** | Work in progress and in review; the PR thread is the record of what was done and why |
| **`docs/LOTS.md`** (if the project splits work into lots) | The **plan**: scope, dependencies, model tier, priority of each lot, linked to its issue. Never edited to record progress |
| **`docs/lots/LOT-XXX-*.md`** | The **spec** of a lot (template: `templates/docs/lots/TEMPLATE.md`) |
| **`docs/adr/`** | The decisions. A decision outside an ADR is not a decision |
| **The project's `.md` files** | The durable context; they point to issues (`#n`) instead of carrying TODOs |

## 2. The loop (one issue, one PR)

1. **Issue**: clear title, then the **intent** (§2 bis): user story, error behaviours, acceptance criteria,
   definition of done, sources. Mandatory labels (§4). Skill: `/intent`.
   Search for a duplicate before creating (titles, bodies, synonyms, open **and** closed issues and PRs); the
   oldest is the one to keep.
2. **Ready?** All its dependencies are done, its inputs exist (data, screenshots, access), no product decision is
   missing (otherwise `status: needs-decision`, do not code), not `needs: host` if you are in the cloud.
3. **Claim** before writing code: a comment whose first line is `/claim <id>` (the agent's id, or
   `human/<login>`), followed by the plan in 3 to 5 bullets ([CONVENTIONS](CONVENTIONS.md) §GitHub comments).
   Comments are replayed in order: the first claim wins, only those of repository members count (label
   `status: claimed` set by hand or by a workflow). If you stop before the end, say where you are on the PR and the
   issue, then comment `/release`. A claim that looks abandoned for 24 h: ask the maintainer, never take it over on
   your own.
4. **Spec**: the issue is enough for a bug, a task, a doc; a lot has its spec `docs/lots/LOT-XXX-*.md`.
5. **Implementation in TDD** (§2 ter): branch `<type>/<short-name>` from the up-to-date integration branch
   (`git fetch` first); atomic commits per issue, pushed often to a draft PR; tests written first and seen red; no
   opportunistic refactor outside the scope (if a point is ambiguous: the simplest option, noted in the end comment).
6. **Verification**: tests and lint locally; self-review against [LESSONS](LESSONS.md); adversarial review by
   another model ([ORCHESTRATION](ORCHESTRATION.md) §3); Mac build if the app is touched ([MAC-HANDOFF](MAC-HANDOFF.md)).
7. **Draft PR** from the first push, body as in [CONVENTIONS](CONVENTIONS.md) §Pull requests (issue, `Claim:`, lot,
   problem / cause / change / tests, `### Ledger` if the project keeps a ledger). "Ready for review" when everything
   is finished: that is when the costly CI runs ([CI-BUDGET](CI-BUDGET.md) §2); after that, one commit per round.
   Bot review cycles: [REVIEW-ROUNDS](REVIEW-ROUNDS.md).
8. **End**: comment on each issue (done, PR link, what is left, decisions taken, to validate on the device). Issue
   resolved without `Closes` or closed by hand → comment "Resolved by #PR". Closing an issue removes its status
   labels.

**Done** = the issue's definition of done is met, code in the right place, tests written first and green in CI, lint and security green, docs updated in the same commit, reviewed by
another model or a human, self-review done, `Closes #n` and issue closed after the merge (checked closed).

## 2 bis. The intent: what an agent must know before writing a line

An agent does not guess an intent: it reads it. Every work issue carries:

| Section | Content | Example |
|---|---|---|
| `### Summary` | "As <who>, I want <X> to do <Y>, so that <benefit>" | As a reader, I want the thread to reload by itself every 2 min, so that I can follow a discussion without a gesture |
| `### Error behaviours` | Each invalid input, external failure, limit → expected result | Network down: discreet banner, last content kept, new attempt at the next interval |
| `### Acceptance criteria` | Given / When / Then, one test per criterion | Given an open thread, when 2 min pass, then a single request is sent (source: …) |
| `### Definition of done` | What must be true to close | Tests green in CI, doc updated, adversarial review APPROVED, validated on iPhone |
| `### Out of scope`, `### Sources` | What is not done; where the facts come from | — |

One of these sections is missing and it needs a product decision → `status: needs-decision` with the exact
question; do not code. The issue steward ([STEWARDS](STEWARDS.md) §1) keeps the queue ready.

## 2 ter. TDD: the test first, red, then green

1. **Red**: turn each acceptance criterion and each error behaviour into a test, through the real entry point; run
   it and **see it fail for the right reason** (not a compile or import error).
2. **Green**: the minimal code that makes it pass; no test is weakened to pass.
3. **Refactor**: clean up with the tests green, without changing behaviour.
4. A bug fix starts with the test that reproduces the bug. A fixed review finding has its test (REVIEW-ROUNDS
   §4). The PR says, under "Verified", which tests were seen red (LESSONS L01).
5. What cannot be tested automatically (rendering, device) goes under "Watch points / not tested", with the planned
   manual check.

## 3. Test feedback: umbrella issue + one issue per point

A batch of feedback (test session on iPhone, review by a relative) becomes:
- **an umbrella issue** `type: epic` + priority, with a tracking table:

  | Ref | Point | Lot | Issue | PR |
  |---|---|---|---|---|
  | Read3 | Thread: reload button too small | lot-ux-1 | #212 | #230 |

- **one issue per point**, title `[Ref] Area: subject` (e.g. `[Read3] Thread: reload button…`), attached to the umbrella
  (sub-issue), with its full labels;
- the umbrella is updated at each PR (PR column) and closes when all its points are closed.

Skill: `/feedback-triage`.

## 4. Labels

Canonical taxonomy: `templates/.github/labels.json` (vendored as `.harness/labels.json`); the project adds its own
in `.github/labels.local.json`; the reusable workflow `labels-sync.yml` syncs both.

Format: `axis: value`, lowercase ASCII, no emoji.

| Axis | Labels | Rule |
|---|---|---|
| `type:` | `type: bug` · `type: feature` · `type: docs` · `type: chore` · `type: security` · `type: epic` (umbrella or lot) | exactly one on every open issue |
| `priority:` | `priority: critical` data loss or crash · `priority: high` blocking or wrong · `priority: medium` next iteration · `priority: low` later | exactly one after triage |
| `difficulty:` | `difficulty: trivial` fast tier · `difficulty: easy` solid tier · `difficulty: medium` strong tier · `difficulty: hard` frontier tier, reviewed by another model ([ORCHESTRATION](ORCHESTRATION.md) §2) | exactly one after triage, unless configured otherwise |
| `status:` | `status: needs-triage` · `status: ready` · `status: claimed` (follows the `/claim`) · `status: blocked` (external prerequisite) · `status: needs-decision` (product decision) | exactly one on every open issue; removed on close |
| `needs:` | `needs: host` requires the Mac, cloud sessions do not touch it · `needs: info` · `needs: review` | as needed |
| Other | `direct-pr` · `dependencies` | as needed |
| Project | in `labels.local.json`, e.g. `area: ux`, `type: lot`, `dashboard` (issue kept by `flow-report.yml`), `review: skip` (skips the review service), `compliance` (forces the compliance framework review, [COMPLIANCE](COMPLIANCE.md)) | per project |

`lesson` (proposal for the lessons table) exists only in the harness repository's own `.github/labels.local.json`.

A milestone is a GitHub milestone. A lot is a `type: epic` issue with sub-issues and `LOT-NNN` in its title.
Umbrellas carry only `type: epic`, their `status:` and a priority. Add a label to the file **before** using it.
`issue-hygiene.yml` reports (a single comment, kept up to date) the missing axis.

**Adjustable model-tier and size axes**: a project that already has its taxonomy (e.g. `complexity: low|high`, or a
model tier deduced from a routing table) says so in `.harness/config.json`:
```json
{ "labels": { "model_prefixes": ["difficulty:"], "size_prefixes": ["size:"] } }
```
Defaults: `["difficulty:"]` (model tier) and `[]` (no separate size axis: `difficulty:` carries both). Empty list:
the project does not have that axis. An issue without a label of the axis does not block the work: the agent deduces
the tier and the size from the issue text and the project's routing table (its `AGENTS.md`, or
[ORCHESTRATION](ORCHESTRATION.md) §2), says so in its claim, and carries on; it proposes the missing label without
waiting for it. The `required-axes` input of `issue-hygiene.yml` is set the same way.

**Read the state of a project** (GitHub issue search):

| Question | Query |
|---|---|
| In progress | `is:issue is:open label:"status: claimed"` + open PRs (`is:pr is:open`) |
| Ready to take | `is:issue is:open label:"status: ready"`, sorted by priority (`priority: critical` → `priority: low`) |
| Blocked | `is:issue is:open label:"status: blocked"` |
| Needs a human decision | `is:issue is:open label:"status: needs-decision"` |
| To triage | `is:issue is:open label:"status: needs-triage"` |
| Out of reach of a cloud session | `is:issue is:open label:"needs: host"` |
| By milestone | `is:issue milestone:"<name>"` |
| By lot | the sub-issues of the lot's `type: epic` issue (`label:"type: epic" LOT-NNN in:title`) |

**Order of taking**: `type: security` first, then `priority: critical` → `priority: low`; among lots, the critical
path and those that unblock others; at equal priority, choose an issue whose `difficulty:` label matches the model
tier of the session.

## 5. Lots

A **lot** is the unit of work of a session: one PR, reviewed in one go, with a clear scope. `difficulty: hard`
spanning several layers must be split into lots.
- The plan (`docs/LOTS.md`) lists each lot: scope, module, difficulty, author model → reviewer, dependencies,
  priority, issue. Mark the critical path (★). It changes only if the plan changes (new lot, dependency,
  routing), never to record progress.
- Dependencies follow the direction of the modules (a lot of the low layer does not depend on a high layer); a
  CI script can check it (HFRnow: `scripts/check-lot-deps.py`).
- A lot branch groups the issues of one lot: `lot/<short-name>`; one PR per lot with one `Closes #n` per issue.
- **Unblock when closing**: whoever closes a lot lists the lots that depended on it, checks that no other
  prerequisite blocks them (screenshot, ADR, decision), replaces `status: blocked` with `status: ready` and comments
  "Unblocked by #PR". Otherwise say what still blocks.
- Parallel lots that write the same section of a shared doc: create the common heading first, each lot adds only
  its sub-section (LESSONS L41).

## 6. Work discovered along the way

TODO, pending decision, debt, bug seen in another lot: **a labelled issue**, never only a line in a `.md`, nor
only a session message. A problem in someone else's lot is reported on their issue or PR.

## 7. External contributions

An external contributor (human or agent) follows the same loop. What works (HFRnow, `EXTERNAL-AGENTS.md`):
a queue `external: ready` of self-contained issues; the claim requested by comment when they lack the rights;
a limit on open PRs per contributor; UI code that arrived without spec or tests is **ported** lot by lot, it is not
merged as is (LESSONS L44). The model for rights and merging belongs in a project ADR.

# Changelog

Format: one section per version (semver), from newest to oldest. "Action" = what a consumer project must do when
moving to this version.

## Unreleased

- **CI budget, billing units** ([docs/CI-BUDGET.md](docs/CI-BUDGET.md) §1, #96): GitHub states the included usage in
  dollars and a price per minute by runner; the two rules (macOS about ten times Linux, every job rounded up) are
  unchanged. Sourced and dated.
- **`timeout-minutes` on every job is now checked** ([CI-BASELINE](docs/CI-BASELINE.md#2-the-six-invariants-of-every-workflow)
  §2 invariant 4, #99): `job-timeout.py` (vendored as `.harness/scripts/job-timeout.py`, standard library only) lists
  each job of `.github/workflows/` that runs steps without `timeout-minutes` (exit 1), skips reusable-workflow calls,
  warns above a ceiling (default 120) and answers "could not check" (exit 2) on a layout it does not read (flow
  mappings, anchors); exceptions with a reason in `.harness/config.json` › `job_timeout`. Runs in `ci.yml`,
  `scripts/local-check.sh` and the docs job of `docs-security.yml` (input `job-timeout`, on by default). zizmor and
  actionlint never checked this invariant. **Action**: see below.
- **Slow suites: timeouts, per-test limits, waits on events** ([CI-BUDGET §6](docs/CI-BUDGET.md#6-slow-suites-job-timeouts-test-time-limits-waits-on-events),
  #100, from HFRnow #801): set `timeout-minutes` from measured green runs, on the job and on the step at risk; a time
  limit per test so a hung test fails alone with its name, with the iOS switches (`xcodebuild` test timeouts, Swift
  Testing `.timeLimit(_:)`) quoted from Apple's and Swift's pages read on 2026-11-12, and what they leave to verify;
  waits on events, every one bounded; the slow class in its own job, with its cost; what is not allowed. Lessons L85
  to L90. **Action**: none.
- **Dashboard: CI health** ([FINOPS](docs/FINOPS.md) §4, `flow-metrics.py`, #101): jobs that passed only on a re-run
  (red then green on the same commit), the red rate per job on the integration branch, jobs running too long (🔴 on
  the integration branch) and runs `queued` with zero jobs, from the Actions API with at most 3 + `max_job_requests`
  extra requests; "could not check" rather than "nothing" when the API fails. Thresholds in `.harness/config.json` ›
  `ci_health`. Playbook for a red base and a stuck run in [REVIEW-ROUNDS](docs/REVIEW-ROUNDS.md), LESSONS L91–L92.
- **Community files**: a [code of conduct](CODE_OF_CONDUCT.md) and the repository's own pull request template
  (`.github/pull_request_template.md`, the one the harness gives projects) (#105).
- **Factory guide: the motorway picture** (`docs/diagrams/factory-motorway.*`, shown in
  [docs/factory/README.md](docs/factory/README.md), #103): signs set by a human, on-ramp, lanes, toll, convoy, exit, a
  drift exit, and radar, police and upkeep beside the road; it says where the road slows.
- **AI stack diagram: the execution split** (`docs/diagrams/ai-stack.*`): three columns (chatbot, agent in a vendor's
  cloud, agent on your machine); the chatbot has none of your files, the cloud agent a copy of the repository and only
  what it was given, the local agent your files, tools, network and credentials (#88).
- **Factory guide, part 3: review and scanning** ([docs/factory/review-and-scanning.md](docs/factory/review-and-scanning.md),
  #84): the nine review and scanning steps a change goes through, each provided by the platform, an independent tool
  or your own agent, with the GitHub and GitLab features, plans and preview status as their documentation states
  them on 2026-11-12, when each step runs in the harness, and the overlaps and loops to avoid at agent pace. Research
  notes with every quote kept in `docs/factory/sources/`. **Action**: none.
- **The version number tells the gap** ([BRANCHING-RELEASE](docs/BRANCHING-RELEASE.md#versions-and-tags),
  [CONTRIBUTING](CONTRIBUTING.md)): `VERSION` and the plugin manifest on `master` are the next version with a `-dev`
  mark (`0.4.0-dev`) until the release, which removes it. The "Valid JSON and consistent versions" step fails on a
  non-empty `## Unreleased` under a released number. `harness-sync.sh --check` and the session-start hook print
  "vendored X (commit) · harness now Y, N commits ahead, see CHANGELOG Actions" when a harness clone is at hand
  (`HARNESS_CLONE`, or `../belayline`), and "could not compare" when not; offline. A `-dev` version is a harness
  state, not a tag: a sync from a clone of `master` pins workflow references as `@<sha> # v0.4.0-dev`.
  **Action**: none.

- **Factory guide, part 4: run only when needed** ([`docs/factory/run-when-needed.md`](docs/factory/run-when-needed.md),
  #85): the seven sources of CI runs and how to cut each, the loops and their bounds, and the edge (local check,
  platform builds on a Mac, larger and self-hosted runners) with GitHub's billing and its self-hosted security
  warning quoted, read on 2026-11-12; diagram `docs/diagrams/run-where.svg`; research notes kept in
  `docs/factory/sources/`. **Action**: none.
- **Factory guide, part 2: the CI choices of the harness, explained** ([`docs/factory/ci-choices.md`](docs/factory/ci-choices.md),
  #83): each CI choice of [CI-BASELINE](docs/CI-BASELINE.md) and [CI-BUDGET](docs/CI-BUDGET.md) with what it does, why,
  what it costs and what else is reasonable; the GitHub facts it rests on, sourced and dated; what we got wrong first
  (#10 then #67, #12, #57); a diagram of the five tiers and when each runs (`docs/diagrams/ci-tiers.svg`). **Action**: none.
- **Factory guide, part 1: the pace** ([`docs/factory/pace.md`](docs/factory/pace.md), #82, umbrella #80): why agent
  volume strains a factory sized for people, from Anthropic's own account of redesigning its source control (quoted
  from the primary page, figure shown by reference, notes in `docs/factory/sources/`) and from this repository's and
  the first consumer's numbers; one section per thing that breaks, each with the harness file that answers it, and
  where the harness has no answer. **Action**: none.
- **Factory guide, part 6: the economics of spawning agents**
  ([`docs/factory/spawn-economics.md`](docs/factory/spawn-economics.md), #87): what a spawn costs in the terms of
  FINOPS (context at start, model tier, rounds), the taxes sized per human that every spawn pays, what the dashboard
  measures and what it does not (token spend per lot), and the harness's rules of thumb with their files.
- **Factory guide, part 5: identity and credentials for a fleet of agents** ([`docs/factory/identity.md`](docs/factory/identity.md),
  #86): which credential an agent can hold on GitHub, GitLab, Jira and Confluence (reach, end, audit trail, cost, each
  sourced and dated), how a cloud agent's proxy keeps the token out of the session, what the harness traces and that
  it issues and revokes no credential, a decision table and a diagram; research notes in `docs/factory/sources/`.
  **Action**: none.
- **Factory guide: index page** ([`docs/factory/`](docs/factory/README.md)), the frame of a stream in parts on the
  software factory rethought for agents (#81, umbrella #80): the six parts with question, audience and status, and the
  six words every part uses. **Action**: none.
- **AI layers guide: a picture of the four layers** on its index page (`docs/diagrams/ai-stack.svg`), drawn in
  Excalidraw from the scene of the coding-agent diagram, so both share one font, stroke and colour code (#76).
  **Scene-only diagrams**: a diagram may have no `.json`; `<name>.excalidraw` is then the source and `<name>.svg`
  its stamped Excalidraw export; `render.py --check` verifies the pair and `--stamp` stamps it
  ([README-STANDARD](docs/README-STANDARD.md) §4).
- **Integration branch that is not the default branch: the first adoption stops, and a relay workflow**
  ([ADOPTION](docs/ADOPTION.md#integration-branch-that-is-not-the-default-branch), [CI-BASELINE](docs/CI-BASELINE.md)
  §6): on a first adoption (no `.harness/lock`), `harness-sync.sh` exits with code 4 before writing anything when
  `integration_branch` is not the default branch, names the `issues` / `issue_comment` / `schedule` jobs that would
  never run, and gives the two ways out: make it the default branch, or commit the new
  `templates/.github/workflows/harness-relay.yml` on the default branch (issue hygiene and dashboard run from there
  on the integration branch's files; label reconcile left disabled until #62). Never seeded; `refbump` pins a copy kept
  on the integration branch. `issue-hygiene.yml` and `flow-report.yml` take a new optional `ref` input. Later syncs
  keep the warning, which now names the relay; `"default_branch_check": false` still silences everything.
  **Action** (projects already adopted whose integration branch is not the default branch): install the relay on the
  default branch once this version is synced, or make the integration branch the default; to keep two branches by
  hand on purpose, set `"default_branch_check": false`.

- **`status:` labels kept true without any workflow** ([METHODOLOGY](docs/METHODOLOGY.md) §4,
  [ORCHESTRATION](docs/ORCHESTRATION.md) §1): `issue-reconcile.py` (vendored as `.harness/scripts/issue-reconcile.py`,
  standard library) removes the status of closed issues, sets `claimed` on an issue with an open linked PR or a live
  `/claim`, moves a `blocked` issue whose cited blockers are all closed to `ready`, and reports what it cannot decide
  (stale claims, several or no `status:`, no `type:`, blocked without blocker); `needs-decision` and `on-hold` are
  never moved. Dry run by default, `--apply` to change, a `summary:` line with the count per status; a dry run costs
  one API call per 100 issues and PRs plus the comment pages. Offered by the session-start hook, run after each merge
  by `/lot-finish`, and callable on `schedule` / `workflow_dispatch` through the reusable `issue-reconcile.yml`.
  **Action**: none required; an orchestrator runs it at session start (`--apply` once the dry run looks right).
- **Ledger: one folder at a time, and a rule for a contested place** ([CONVENTIONS](docs/CONVENTIONS.md) §Ledger,
  #61): only the steward folds, on its one branch (`docs/steward`); `doc-steward.py fold-guard` (exit 0 free, 1
  refused with the open PR's link, 2 could not check) refuses a second fold while a PR from that branch is open, in
  `doc-steward.yml` (before deciding and before pushing; the open PR is no longer rebuilt) and for a fold run by hand.
  `STEWARD_LEDGER_PRS` comes in merge order; two entries on the same place: the first merged wins, the fold command
  writes the other to `$STEWARD_CONTESTED` and the docs PR quotes both under "Contested entries", apart from
  "Unplaced entries". New harness entry type `note` (text outside the tables, `<file> § <heading>` then the text),
  folded without waiting for an operator, with the helper `doc-steward.py note`.
  **Action** (projects that keep a ledger): make the fold command honour the contract (report contested places to
  `$STEWARD_CONTESTED`, fold `note` entries) and merge or close an open steward PR before the next pass.
- **Operator decisions live in a versioned file, not in comments** ([ORCHESTRATION](docs/ORCHESTRATION.md) §4,
  [ESSENTIALS](docs/ESSENTIALS.md)): seeded `docs/DECISIONS.md` (date, scope key, decision, source, status; only rows
  `in force` bind) and `decisions-check.py` (vendored as `.harness/scripts/decisions-check.py`), run in the docs job of
  `docs-security.yml` (input `decisions`): at most one `in force` row per scope key, a date and a source on every row.
  Off when the file is absent. A decision received in a comment or chat is recorded in the next commit.
  **Action**: none required; a project that wants the rule keeps the seeded `docs/DECISIONS.md` after the sync, one
  that does not deletes it (or `decisions: false`).
- **`status: on-hold` apart from `status: blocked`; a blocked issue names its blocker**
  ([METHODOLOGY](docs/METHODOLOGY.md) §4, [ADR 0003](docs/adr/0003-labels-readable-by-axis.md) amendment):
  - new base label `status: on-hold` (held by a decision, not a dependency), shown apart by `flow-metrics.py` (an
    "On hold" section, not a bottleneck) and `readme-progress.py` (`⏸ on hold`);
  - a `status: blocked` issue carries a `### Blocked by` section, one line per blocker (`#n` or free text); the task
    form has the field (formerly "Depends on"); `issue-hygiene` reports a blocked issue without it and never
    relabels it (input `blocked-label`).
  **Action**: run the label sync (`labels-sync`) to create `status: on-hold`, then move the issues held by a
  decision from `status: blocked` to `status: on-hold` and give each remaining blocked issue a `### Blocked by`
  section.
- **Merge gate** (`scripts/merge-gate.py <pr>`, vendored to `.harness/scripts/`, [CONVENTIONS](docs/CONVENTIONS.md)
  §Pull requests): read-only, one `ok` / `missing` line per check (draft, mergeable, CI green on the head sha,
  adversarial APPROVED naming the head, a "stale approval" otherwise, open review threads read through GraphQL, the
  `Open questions` of the report marked `<!-- harness:report -->`, required and security labels, PR body lines);
  "may merge" prints the head sha to merge with, "could not check" exits 2. Settings: `.harness/config.json` ›
  `merge_gate` (`required_labels` default empty). The verdict parsing is shared with `flow-metrics.py`.

- **Orchestrator memory: one State comment, rewritten by script; the thread is a log**
  ([ORCHESTRATION](docs/ORCHESTRATION.md) §8): `scripts/orch-state.py` (vendored as `.harness/scripts/orch-state.py`)
  rewrites the comment marked `<!-- harness:state -->` on the memory issue (`--issue` or `.harness/config.json` ›
  `orchestration.memory_issue`): decisions in force by scope key, open PRs by stage with their head, children from
  `/claim` comments and `Claim:` lines (verdicts parsed as the merge gate parses them), decisions waiting with their age, counts per `status:` label; bounded to
  6,000 characters, refuses a hand-edited State unless `--force`, prints it when it cannot write. Child reports go on
  the child's PR in `.harness/templates/child-report.md` (`<!-- harness:report -->`, `Open questions`); resuming
  starts from the State.

- **What reviews are worth, readable without a metric**, and **lot size as a recommendation**
  ([FINOPS](docs/FINOPS.md) §2 and §5, [REVIEW-ROUNDS](docs/REVIEW-ROUNDS.md), [METHODOLOGY](docs/METHODOLOGY.md)
  §5 and §6):
  - each settled finding listed in a PR starts with `[fixed]`, `[declined: false positive]` or
    `[declined: not worth it]`; a bug found after a merge carries `Introduced by #NNN`; FINOPS §5 gives the GitHub API
    queries to read them. The harness computes nothing: lowering the reviewer tier as models improve stays the
    operator's decision;
  - no cap on lot size (recorded in `.out-of-scope/`): split as much as possible, an issue (the lot's epic, or an
    umbrella over related lots) heads the work, never a long-lived agent; a disposable `plan` agent splits; a lot
    that stays big says why in its PR. The bug template and the PR template ask for the new lines.

- **Review rounds tightened from what the reviews of this release showed**
  ([REVIEW-ROUNDS](docs/REVIEW-ROUNDS.md), [ORCHESTRATION](docs/ORCHESTRATION.md) §3):
  - a verdict lists the claims the reviewer could not check under **Unverified**, its first line ends with
    `· unverified: N`, and each point is verified or accepted before the merge; the dashboard counts merged PRs whose
    last verdict still carries unverified points (`flow-metrics.py`);
  - every reviewer states the model it actually ran on; an adversarial verdict on the author's model does not count;
  - after an APPROVED, a form-only delta gets a short confirmation on the delta, any other delta a full re-review;
  - when the review service skips the repository or never reviews the head, the code review falls back to the
    `review` job or a fresh sub-agent of another model on the diff only;
  - a reviewer works only in its own worktree, never in the author's checkout. Lessons L83 and L84.

- **Plugin renamed `belay` → `belayline`** ([ADR 0004](docs/adr/0004-plugin-named-belayline.md)): `belay` is also the
  command name of other 2026 agent-safety tools. Install with `claude plugin install belayline@belayline`; skills
  are `/belayline:<skill>`. Landscape decisions recorded in `.out-of-scope/`: guard hooks stay fail-open, no runtime
  guardrail building block.

  **Action** (plugin users only; the vendored copy is not affected): `claude plugin uninstall belay@belayline`, then
  `claude plugin marketplace update belayline` (third-party marketplaces do not refresh by default), then
  `claude plugin install belayline@belayline`. In `.claude/settings.json`, replace `"belay@belayline"` with
  `"belayline@belayline"` under `enabledPlugins`; under `extraKnownMarketplaces`, rename the key `Belayline` to
  `belayline` and set `ref` to this release's tag or later. In your own notes and scripts, replace `/belay:<skill>`
  with `/belayline:<skill>`.

- **Orchestration: wait on events, not in memory** ([ORCHESTRATION](docs/ORCHESTRATION.md) §4): subscribe the
  session to a PR's activity where the tool allows it, with one late checkpoint as a safety net.

- **Positioning** ([POSITIONING](docs/POSITIONING.md)): where Belayline sits among agent harnesses. Runtime harnesses
  gate, sandbox or replay each action; Belayline governs the process around them (intent, TDD, two traced reviews,
  bounded loops, metrics, versioned rules). Compared with Google's Elephant–Goldfish Model, which makes the same
  author / fresh-reviewer split: plan, progress and decisions in the repository rather than a long-lived agent, briefs
  instead of cold context, a reviewer of another model, the whole change rather than the spec; earlier use of these
  rules in the author's projects dated from commits (SwiftHFR, 2026-10-24). Six audited projects and one paper,
  sourced and dated (read 2026-11-10); the ideas taken are tracked in the "Landscape audit" umbrella issue.

- **No dependency left: the Node exporter of the diagrams is gone** (#57): `scripts/diagrams/package.json`, its
  3 300-line lockfile and `export-svg.cjs` (Excalidraw, React, esbuild, Playwright) are removed, with the security
  overrides they had already needed. The repository holds no dependency, as `SCOPE.md` and `CONTRIBUTING.md` say,
  and `check-framework.py` now reports any tracked dependency manifest or lockfile (`package.json`, `requirements*.txt`,
  `pyproject.toml`, `go.mod`, `Cargo.toml`…) outside `templates/`. An Excalidraw look now comes from a manual export
  (excalidraw.com → Export image → SVG, or an Excalidraw MCP) stamped by `render.py --stamp <name>`, which verifies
  the file and writes the same scene and body hashes as before: the committed SVGs are unchanged and still pass
  `--check`. The stamp records which scene the author exported from, not that the image matches it. A stale export
  is never overwritten silently: the rendering fails and names both ways out (export and stamp again, or
  `--engine builtin <name>`); `--engine excalidraw` is removed ([README-STANDARD](docs/README-STANDARD.md) §4).

- **Guide: the layers of AI** ([`docs/ai-layers/`](docs/ai-layers/README.md)), a series by audience; first part
  [apps and CLIs](docs/ai-layers/obo-agents.md): chatbot vs agent working on your behalf, four layers (presentation,
  agent, execution, inference), the contract that governs your data by plan type and platform, a tools matrix
  (Claude Code, Codex, Antigravity, Gemini CLI, Gemini Code Assist, Copilot, Cursor), what does not combine, and why
  "we approved tool X" needs one answer per layer. Two Excalidraw diagrams. Every product fact is sourced and dated
  (read 2026-11-10). Vendored with the other docs into `.harness/docs/ai-layers/`.

- **Ledger: the section alone is the entry, no label asked of the author** (#60,
  [CONVENTIONS](docs/CONVENTIONS.md) §Ledger): child and cloud sessions often cannot set labels. `pr-hygiene.yml` no
  longer fails on "entry blocks without the `ledger` label" nor on "label without a section": a stale label is one
  notice. It fails a malformed section instead (block without a type, block not closed, `None` without a reason),
  quoting the entry and the expected format; `None (<reason>)` is the one spelling of an empty section.
  `doc-steward.py pending` finds the PRs to fold from their `### Ledger` section (the label is only read as a hint),
  keeps the entries a pass did not fold pending, and lists malformed entries in the docs PR; the fold pass writes
  `ledger: done`, the only label the harness sets.

  **Action** (projects that keep a ledger): stop asking authors for the `ledger` label; a project CI check that
  requires it must drop that rule. Keep `ledger: done` in `.github/labels.local.json`.

- **README diagrams redrawn, exported by Excalidraw** (`docs/diagrams/`): mechanisms, cycle and adoption diagrams
  checked against the docs (two reviews: intent before "Ready", code on the ready PR; the dashboard reads the
  repository and CI; the harness enters the repository by a sync PR; loops bounded to 3 review rounds and 6 CI-tested
  pushes, one clean round ends the loop; four short callouts instead of one long note), one grid and one palette.
  `render.py` writes scenes in Excalifont; the SVGs are exported by Excalidraw itself (hand-drawn strokes, hachure
  fills, embedded font subset) and `--check` verifies the two hashes they carry (their scene, their own body), in
  Python (stamping: see the entry above). Vendored projects keep the built-in renderer. The overflow estimate now
  uses the Excalifont width (0.58 em per character instead of 0.52).

- **Doc steward at merge, weekly safety net** ([STEWARDS](docs/STEWARDS.md) §2): new reusable `doc-steward.yml`, opt-in
  `steward` job in `harness.yml` (it adds `closed` to the `pull_request` types; the `pr` job skips it). After each
  merge into the integration branch, `doc-steward.py pending` (vendored in `.harness/scripts/`) decides without any
  agent: merged PRs still labelled `ledger`, or `Docs:` lines naming files since the last steward PR; nothing → one
  short job. Otherwise `ledger.fold_command` folds the ledger (its own reproducible commit), `readme-progress.py`
  refreshes the progress block, a Claude agent with a read-only token edits only the declared docs, and a job
  without an agent opens or updates ONE draft PR from `docs/steward` (never a protected branch; entries it cannot
  place are listed in it). Several merges queue in one concurrency group. Monday: audit only (README, links,
  diagrams, progress block), one `type: docs` issue per gap. Merge pass skipped with a notice without
  `ANTHROPIC_API_KEY` / `CLAUDE_CODE_OAUTH_TOKEN`; never required.
- **README progress generated from the issues**: `readme-progress.py` (vendored in `.harness/scripts/`) rewrites the
  block between the `progress` markers: one row per `type: epic` lot (state, closed/total sub-issues, issue and PR
  links), otherwise one per milestone; ⚠ on an epic without sub-issue or an issue with zero or several `status:`
  labels; `--check` exits 1 on drift. `/readme-update` uses it instead of hand-written rows; `flow-report.yml` input
  `readme-progress` reports drift in the job summary (README-STANDARD §3).
- **Doc impact per PR** ([CONVENTIONS](docs/CONVENTIONS.md) §Ledger): every PR carries a `Docs:` line (doc files it
  makes untrue, or `Docs: none (<reason>)`), in the `### Ledger` section with a ledger, otherwise in the body; the PR
  template asks for it. `pr-hygiene.yml` warns (never fails) when a ready PR changes code paths without it (new input
  `docs-code-paths`, empty = off) or names a missing file; a ledger section with only this line no longer needs the
  label. New `doc-links.py` (vendored as `.harness/scripts/doc-links.py`): relative links and cross-file anchors in
  Markdown resolve, run in the docs job of `docs-security.yml` (input `doc-links`) and in the harness CI. STEWARDS §2
  describes three levels: per PR, at merge, weekly safety net.
- **Local check = the CI** ([CI-BASELINE](docs/CI-BASELINE.md) §3): skill `/local-check` writes
  `scripts/local-check.sh` from the project's workflows (`--quick` for what changed, full by default), seeded as a
  skeleton that reports INCOMPLETE until it has steps; summary and result OK / FAILED / INCOMPLETE (exit 0 / 1 / 2),
  a missing tool or another host is never green. `/lot-finish` step 1 runs it. The harness's own script replays
  `ci.yml` (drift tested).
- **Lesson classes**: `/lesson-propose` classifies each item as mechanical (proposed check as an issue, no line),
  judgment (a lesson line) or one-off (nothing); the "Lesson" form asks for the class and the check; header of
  `docs/LESSONS.md` explains them.
- **Lessons sorted** (#18): a **Class** column in `docs/LESSONS.md`; ids unchanged. 79 rows judgment, L07 enforced
  by markdownlint MD056, L53 by zizmor, L75 `mechanical, check to write` (issue to come). `/lessons-check` reads only
  the judgment rows and those whose check is still to write: 80 rows instead of 82. A test checks that every
  `L<nn>` cited in docs, skills, agents, templates and workflows exists.
- **Two explicit reviews** ([REVIEW-ROUNDS](docs/REVIEW-ROUNDS.md) §The two reviews): the adversarial review
  (intent: issue + diff + lessons, isolated fresh sub-agent that refuses to give a verdict if it cannot be isolated)
  and the code review (diff only, by the review service) are named separately; one clean round on the current head
  ends the loop (within 3 cycles) and settled findings are listed in the PR, not reopened without new evidence.
- **Renamed to Belayline** (formerly agentic-harness): repository `francoisgn/belayline-agentic-harness`, plugin
  `belay` in marketplace `belayline` (`claude plugin install belay@belayline`). The vendored folder `.harness/`,
  `harness-sync.sh`, `harness.yml` and the `harness:` markers keep their names.
- **English**: the whole harness is now in English; `i18n/` removed; files renamed (ESSENTIEL → ESSENTIALS,
  UTILISATION → USAGE, diagram and ADR names, issue forms `lesson.yml`, `task.yml`); managed block id `cadre` →
  `harness`; README progress markers `avancement` → `progress`.
- **Labels** ([ADR 0003](docs/adr/0003-labels-readable-by-axis.md), accepted): `axis: value` names (`status:`,
  `type:`, `priority:`, `difficulty:`, `needs:`); new states `status: needs-triage` and `status: ready`; old names
  kept as aliases.
- **Living README, by default** ([README-STANDARD](docs/README-STANDARD.md)): agents maintain the project README as a
  deliverable: technology badges in the header, image, Excalidraw architecture diagram, lot progress table, quick
  start, Contributing section. Skill `/readme-update` (called by `/lot-finish`), `readme-check.py` and
  `diagrams-render.py` vendored, templates `README.md`, `CONTRIBUTING.md` and `docs/diagrams/architecture.*` created
  if missing; check in `docs-security.yml` (input `readme`). Each point can be switched off in
  `.harness/config.json` › `readme`.
- **Default branch alert** (#10): the session-start hook and `harness-sync.sh` (also `--check`, exit code unchanged)
  print a 🟠 line when `integration_branch` is not the repository's default branch (workflows triggered by issues,
  comments and schedules would never run), or "could not check" when it is unknown; `pr-hygiene.yml` emits a
  `::warning::` (new input `integration-branch`). Silence with `"default_branch_check": false` in
  `.harness/config.json`.
- **Tiered CI baseline** ([CI-BASELINE](docs/CI-BASELINE.md)): hygiene, quality (one local command = the CI),
  expensive, heavy security, process; six workflow invariants; survey of three real projects.
- **Anti-bloat checks** (`check-framework.py`): size limits on skills, agents and `docs/ESSENTIALS.md` (listed
  exceptions only), skill and agent doc links must resolve, README counts and the `CLAUDE.md.block` skill list must
  match `plugins/harness/` ([CONTRIBUTING](CONTRIBUTING.md) §Size limits).
- The harness applies its own standard: README with badges and progress block, `CONTRIBUTING.md`, checked in CI.
- `scripts/diagrams/render.py`: `--dir` option.
- **Repository identity** (CONVENTIONS §Repository identity): every repository that follows the harness carries a
  description (one sentence), topics (5 to 15), a banner at the top of the README (`docs/assets/banner.svg`) and a
  social preview (`docs/assets/social-preview.png`, 1280×640, text in English, uploaded by hand by the operator). The
  doc steward checks all four (STEWARDS §2, agent `doc-steward`), ADOPTION plans for it.
- `repo-settings.py`: warns (without blocking) if the description or the topics are missing or malformed; a
  description left as the template's (`<…>`) is no longer sent to GitHub.
- The harness applies the rule to itself: description rewritten (any coding agent, no longer only Claude Code),
  topics widened to the agents covered, banner and social preview added; `check-framework.py` checks description,
  topics and images.
- **New banner and social preview** (compass motif, "Keep coding agents on track."): the README shows
  `docs/assets/banner.png`, rendered from `banner.svg` so the typeface does not depend on the reader's fonts;
  `check-framework.py` accepts a banner in `.svg` or `.png`.
- **MIT licence** (`LICENSE`): the harness had none; `harness-sync.sh` copies it into `.harness/LICENSE` with the
  vendored files.
- **`SECURITY.md`**: versions covered, private report (never a public issue), response times, scope; direct link
  from the issue template chooser.
- **Declined ideas recorded** (`.out-of-scope/`): skills invoked only by the human (`disable-model-invocation`) and one source compiled into per-tool skill formats (Cursor, Codex, Gemini CLI), each with the change that would reopen it (#19).

**Action**: point `uses:` references and the clone URL at `francoisgn/belayline-agentic-harness` (the sync rewrites
`harness.yml`); reinstall the plugin as `belay@belayline`. Then run `harness-sync.sh` again; rename the markers `harness:begin cadre`/`harness:end cadre` to `harness`,
and `avancement` to `progress` in README; run the label sync once with `apply-aliases: true`;
`.harness/docs/ESSENTIEL.md` import in CLAUDE.md becomes `.harness/docs/ESSENTIALS.md` (rewritten by the sync).
An existing README is not touched: `python3 .harness/scripts/readme-check.py` lists the gaps; to switch it off,
`"readme": false` in `.harness/config.json`. The `docs` job of `harness.yml`, if enabled, now checks the README
(`readme: false` to avoid it).
Fill in the description and the topics in `.github/repo-settings.json`, add the two images (an issue is enough to
start); the operator uploads the social preview in the repository settings. The next sync adds `.harness/LICENSE`.
Add a `Docs:` line to `.github/pull_request_template.md` (a project file, not rewritten; see the template's). The
`docs` job, if enabled, now checks relative links and cross-file anchors once the sync vendors `doc-links.py`: fix
what it lists, or `doc-links: false`; `docs-code-paths: ""` in the `pr` job silences the doc impact warning.
The next sync also seeds `scripts/local-check.sh`, which reports INCOMPLETE until `/local-check` fills in its steps
(a project with its own command names it in `CLAUDE.md` and adds `scripts/local-check.sh` to `exclude`).
After the sync, run `python3 .harness/scripts/diagrams-render.py` and commit the regenerated `docs/diagrams/*.excalidraw`
(their texts move to Excalifont); until then `diagrams-render.py --check` reports them stale. A label it now reports
as overflowing (Excalifont is wider): shorten it or widen its shape.
After the sync, the `docs` job, if enabled, fails on every workflow job without `timeout-minutes`: add one sized to
the job (`python3 .harness/scripts/job-timeout.py` lists them, file and line), or an exception with its reason in
`.harness/config.json` › `job_timeout`, or `job-timeout: false`.

## 0.3.0 — 2026-11-09

Feedback from the first consumer project: a neutral harness, rules that no longer contradict each other. **Breaking
convention change** (before 1.0.0, a MINOR may break): branches, claims and PR bodies change.

- **Neutral**: no more reference to the maintainer's other projects (names, decision numbers, measured costs,
  anecdotes); their lessons stay, reworded to hold everywhere (source "field" in LESSONS).
- **Push often, pay at "Ready"** (CI-BUDGET §2): replaces "one push per lot, no trial push". Push early and often on
  a draft PR (backup, visibility); the expensive CI only runs on the switch to "Ready" or on an explicit label
  (workflow pattern provided); one commit per review cycle; never a push "to see" on a ready PR. The dashboard no
  longer counts skipped or cancelled runs as tested pushes.
- **Claim** = comment `/claim <id>` (first line), replayed in order: the first claim wins, only repository members
  count, `/release [<id>]` gives it back; the PR carries `Claim: <id>`. Replaces "Claimed: branch …" (ESSENTIALS,
  METHODOLOGY, CONVENTIONS, ORCHESTRATION, skills, label, session-start).
- **Configurable label axes**: `.harness/config.json` → `labels.model_prefixes`, `labels.size_prefixes`;
  `/lot-start` no longer stops on a missing tier or size label (deduced from the text and the routing, stated in the
  claim).
- **Ledger**, optional building block (CONVENTIONS §Ledger): PRs no longer touch the shared logs, their entries go
  in a `### Ledger` section of the body (label `ledger`), which a steward folds after the merge into a docs PR
  reproduced by the project's script. `pr-hygiene.yml`: input `ledger-label` (section ↔ label check). `/lot-finish`
  and the PR template: issue line, `Claim:`, lot, problem / cause / change / tests, `### Ledger` only if the project
  keeps one, instead of `## Changelog`.
- **Branches** `<type>/<short-name>` (`lot`, `fix`, `feat`, `chore`, `docs`; `branch_types` in `config.json`)
  instead of `claude/<lot>`, everywhere (skills, docs, templates, sync workflow, hook message). The dashboard
  recognises an agent PR by its `Claim:` line or its generation footer.
- **guard-git** hardened: grouped options (`-fu`, `-uf`, `-nm`), abbreviations, `--force-with-lease`, `+refspec`,
  `--mirror`, `--all`, deletion of a protected branch (`--delete`, `-d`, `:branch`), `git -C`, `git -c`,
  wrappers (`env`, `command`, `exec`, `sudo`, `xargs`, `eval`, `bash -c`, `sh -c`…), subshells, groups,
  substitutions, here-documents, every separator; bare `git push`, `git push origin` and `HEAD` resolved against the
  current branch (`rev-parse`, or the branch chosen earlier on the line by `git switch` / `git checkout`), `@` as
  `HEAD`, `--tags` alone allowed, wildcard refspecs covering a protected branch refused; falls back to a cautious
  expression if the command cannot be split. Lets through `--dry-run`, `--force-if-includes` alone and unprotected
  branches; stays open on unreadable input. The server-side ruleset remains the real protection (BRANCHING-RELEASE
  §Common rules). Tests: `scripts/tests/test_guard_git.py`.
- **Managed blocks** of `CLAUDE.md` / `AGENTS.md`: `harness-sync.sh` lives in the harness repository (how to run it
  from a project); explicit precedence, project deviations in a "Harness overrides" section of its `AGENTS.md`
  (added to the template).

**Action**:
- `/harness-update` to v0.3.0; the update PR shows the new managed blocks.
- Create the "Harness overrides" section in `AGENTS.md` and write there what the project keeps its own way
  (branches, labels, claims, merge policy).
- `.harness/config.json` (project file, not rewritten): add as needed `branch_types`, `labels`
  (`model_prefixes`, `size_prefixes`; `[]` if the axis does not exist), `ledger` (`enabled`, `label`,
  `fold_command`).
- Branches and claims: move to `<type>/<short-name>` and `/claim <id>` (or record the deviation).
- `harness.yml`: remove `require-changelog: true` from the `pr` job (the PR template no longer has a "Changelog"
  section); set `ledger-label: ledger` if the project keeps a ledger, and create the labels `ledger` and
  `ledger: done` in `.github/labels.local.json`. `.github/pull_request_template.md` (project file): take over the
  new template as needed.
- Project CI: apply the pattern of CI-BUDGET §2 (expensive jobs skipped on a draft, unless an explicit label).

## 0.2.0 — 2026-11-07

Intent, TDD, FinOps, stewards, compliance, security and flow measurement.

- **Open to all**: no more reference by name to the creator (roles: maintainer, operator; plugin author
  "Belayline contributors"); the harness applies to any coding agent (Claude Code, Codex CLI, Cursor, Gemini
  CLI, Copilot, Aider…; loaded through `AGENTS.md`, natively or to be enabled depending on the tool: ADOPTION
  §Connect your coding agent), Claude Code remaining the adapter provided (plugin, hooks, `.claude/`); comment footer
  naming the agent; model tiers per provider (ORCHESTRATION §2).
- **Method**: mandatory intent for issues (user story, error behaviours, Given / When / Then criteria, definition of
  done: METHODOLOGY §2 bis) and TDD (§2 ter); richer issue forms; ESSENTIALS (French, English).
- **Docs**: FINOPS (SPOC orchestrator as the only long-lived agent, context in the repository, model routing, quotas
  and resuming, bounded loops, drift signals), STEWARDS (upkeep roles, non-technical report), REVIEW-SERVICE
  (in-house review service), COMPLIANCE (compliance reviewers), USAGE (step-by-step guide, SwiftHFR example),
  ADR 0002; CI-BUDGET §3 (secrets and variables) and §5 (agentic volume); ORCHESTRATION §7 (**agent naming**
  `<project>.<orchestrator>.<role>.<target>`, checked in CI); LESSONS: lessons reported through issues.
- **Agents** (vendored into `.claude/agents/`): `adversarial-reviewer`, `issue-steward`, `doc-steward`,
  `flow-monitor`, `compliance-gdpr`, `-eu-ai-act`, `-nis2`, `-iso27001`, `-soc2`, `-tisax`, `-pci` (DSS, PIN, P2PE),
  `-hds`, and the generic reviewer `compliance-reviewer`. Requirement identifiers not verified against the official
  text are marked "(to verify)".
- **Pluggable compliance** (COMPLIANCE §2): per compliance framework, built-in agent, company agent, or spec only
  (`docs/compliance/<id>.md`, template provided) applied by the generic reviewer; scope decided without tokens by
  `paths` / `keywords`; resolution and validation by `compliance-plan.py` (vendored, tested).
- **First-pass quality**: the dashboard measures the ratio of PRs with a problem (finding in adversarial, AI,
  compliance, CodeRabbit or human review), agents / humans, and the correction effort (commits after the first
  finding, time to merge); traceability rule for each verdict (REVIEW-ROUNDS §Traceability).
- **Repository settings "as code"**: `.github/repo-settings.json` (description, topics, rulesets) applied on merge
  by `repo-settings.yml` / `repo-settings.py` (secret `REPO_ADMIN_TOKEN`), drift checked every week; the harness
  uses it for itself (`settings.yml`). Required checks verified against the real job names.
- **Diagrams**: README illustrated with three diagrams (mechanisms, cycle of a change, leveraging the harness),
  source `docs/diagrams/*.json`, editable `.excalidraw` scene and SVGs rendered by `scripts/diagrams/render.py`
  (checked in CI).
- **Extension points** (ADOPTION §Replace or extend a building block): each building block of the harness can be
  kept, replaced by the company's own, or extended.
- **Skills**: `/intent`, `/lesson-propose`, `/status-report`, `/compliance-review`; `/lot-start` sets the agent
  identifier.
- **Reusable workflows**: `security.yml` (Semgrep CE, Trivy, gitleaks), `flow-report.yml` ("Project dashboard"
  issue), `ai-review.yml` (AI review, pinned claude-code-action, never required).
- **Script** `flow-metrics.py` (vendored into `.harness/scripts/`): milestones, bottlenecks, stalled work, CI and
  review loops, agents / humans ratio, time to merge, CI minutes; unit tests.
- **Labels**: `leçon`, `tableau de bord`, `revue: aucune`, `conformité` (names at that version; renamed since, see
  Unreleased). `.harness/config.json`: `compliance` key.
- **Harness CI**: consistency check (`check-framework.py`: skills, agents, manifest, labels, naming), Python tests,
  gitleaks; Dependabot for actions; "Lesson" issue form.

Additional action: create the `REPO_ADMIN_TOKEN` secret so that the `settings` job applies
`.github/repo-settings.json` (otherwise it only warns).

Fix: the harness CI listened to `main`, the default branch is `master`.

Action: `/harness-update` to v0.2.0. In `harness.yml` (project file, not rewritten): add the `schedule` trigger and
the `flow` job (see the template), enable `security` and `review` as needed. Fill in `compliance` in
`.harness/config.json` and exclude the compliance agents you do not need.

## 0.1.0 — 2026-11-07

First version, distilled from HFRnow (`dev-swift`) and another project.

- Docs (French): ESSENTIALS (rules loaded in every session), METHODOLOGY, CONVENTIONS, LESSONS (82 scoped lessons,
  sources cited), ORCHESTRATION, REVIEW-ROUNDS, BRANCHING-RELEASE, CI-BUDGET, MAC-HANDOFF, ADOPTION, ADR 0001 and
  ADR template. English edition of ESSENTIALS and of the `CLAUDE.md`/`AGENTS.md` blocks (`i18n/en/`).
- Canonical label taxonomy (type, priority, model, size, status, host) with `axis` and `aliases`.
- Templates: `CLAUDE.md`/`AGENTS.md` block, issue forms (test feedback, bug, feature, task), PR, lot, markdownlint,
  `.harness/config.json`, calling workflows `harness.yml` and `harness-sync.yml`.
- `scripts/harness-sync.sh`: idempotent vendoring (modes copy, tree, block, seed, jsonmerge, refbump), lock with
  fingerprints, `--check`, `--dry-run`, `--force`, `--skip-workflows`, `--skip-seed`, per-project language and
  exclusions.
- Plugin `harness` (marketplace `Belayline`): six skills, `guard-git` hook (force push, push to a protected
  branch, `--no-verify`), reminder hook at session start.
- Reusable workflows: `labels-sync`, `issue-hygiene`, `pr-hygiene`, `docs-security`.

Action: adoption, see docs/ADOPTION.md.

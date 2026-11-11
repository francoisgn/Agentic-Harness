# Adopting the harness in a project, updating it

Day-to-day use once adopted, with the SwiftHFR example: [USAGE](USAGE.md).

Why this mechanism (vendoring + plugin + reusable workflows) and its limits: [ADR 0001](adr/0001-distribution-mechanism.md).

## What the project receives

| Path in the project | Mode | Owner |
|---|---|---|
| `.harness/docs/*.md` | copy | Harness: replaced at each sync (a local modification is detected and refused) |
| `.harness/labels.json` | copy | Harness: canonical taxonomy |
| `.harness/LICENSE` | copy | Harness: its licence (MIT), which accompanies the copied files; says nothing about the project's licence |
| `.harness/hooks/guard-git.py`, `session-start.sh` | copy | Harness |
| `.claude/skills/<skill>/SKILL.md` | copy | Harness (`/intent`, `/lot-start`, `/lot-finish`, `/review-round`, `/feedback-triage`, `/lessons-check`, `/lesson-propose`, `/compliance-review`, `/status-report`, `/harness-update`) |
| `.claude/agents/*.md` | copy | Harness: `adversarial-reviewer`, `issue-steward`, `doc-steward`, `flow-monitor`, `compliance-*` (exclude the compliance frameworks you do not need) |
| `.harness/scripts/flow-metrics.py` | copy | Harness: flow dashboard (`flow-report.yml`, `/status-report`) |
| `.harness/scripts/merge-gate.py` | copy | Harness: merge gate, "may merge now" or why not (CONVENTIONS.md §Pull requests); needs `flow-metrics.py` next to it |
| `.harness/scripts/readme-progress.py` | copy | Harness: README progress table generated from the issues (`/readme-update`) |
| `.harness/scripts/issue-reconcile.py` | copy | Harness: `status:` labels brought in line with issues, PRs and claims, no workflow needed (session start, after a merge, `issue-reconcile.yml`); imports `readme-progress.py` |
| `.harness/scripts/decisions-check.py` | copy | Harness: `docs/DECISIONS.md` has at most one decision in force per scope key (`docs-security.yml`, input `decisions`) |
| `.harness/scripts/orch-state.py`, `.harness/templates/child-report.md` | copy | Harness: the orchestrator's State comment on its memory issue, and the report template a child posts on its PR ([ORCHESTRATION](ORCHESTRATION.md) §8); the script needs `decisions-check.py` and `flow-metrics.py` next to it |
| `.harness/scripts/doc-steward.py` | copy | Harness: doc steward's "anything to fold?" decision, the one-fold-at-a-time guard (`fold-guard`), the `note` helper, docs PR body and weekly audit issues (`doc-steward.yml`) |
| `.claude/settings.json` | merge | Project; the harness only **adds** its two hooks if they are missing |
| `CLAUDE.md`, `AGENTS.md` | marked block | Project, except the block `<!-- harness:begin harness -->…<!-- harness:end harness -->` |
| `.harness/config.json`, `.github/labels.local.json`, issue and PR templates, `docs/lots/TEMPLATE.md`, `docs/DECISIONS.md`, `.markdownlint-cli2.jsonc`, `.github/workflows/harness.yml`, `.github/workflows/harness-sync.yml` | seed | Project: created if missing, never rewritten (except the `@vX.Y.Z` references of `harness.yml`) |
| `.harness/VERSION`, `.harness/lock` | generated | Version, harness commit, checksums of the copied files |
| `.github/workflows/harness-relay.yml` | refbump only | Project, **on the default branch**, only when it is not the integration branch: never created by the sync, which only pins the references of a copy kept on the integration branch ([below](#integration-branch-that-is-not-the-default-branch)) |

## Adoption (once, from the Mac or a cloud session)

Prerequisites: `bash`, `git`, `python3`; read access to `francoisgn/belayline-agentic-harness` (in a cloud session: attach it
to the session; on the Mac: `gh auth login && gh auth setup-git`).

1. **Branch** from the up-to-date integration branch:
   ```bash
   git fetch origin && git switch -c chore/adoption-harness origin/develop
   ```
2. **Fetch the harness** at a tag, next to the project:
   ```bash
   git clone --depth 1 --branch v0.3.0 https://github.com/francoisgn/belayline-agentic-harness.git ../belayline
   ```
3. **Look before writing**, then apply:
   ```bash
   ../belayline/scripts/harness-sync.sh --target . --dry-run
   ../belayline/scripts/harness-sync.sh --target .
   ```
   Exit code 3 = conflicts: a harness file already exists in the project (e.g. a skill with the same name). Rename
   the project's one, or rerun with `--force` if replacing it is intended.
   Exit code 4 = adoption stopped, nothing written: `integration_branch` of `.harness/config.json` is not the
   repository's default branch ([below](#integration-branch-that-is-not-the-default-branch)).
4. **Adapt** (project files):
   - `CLAUDE.md`: the harness block was added **at the end** of the file if it existed; move it to the top (markers
     included) and remove from the project part what now duplicates `ESSENTIALS.md` (generic workflow, comment
     footer, generic labels). Keep what is specific: build, design system, domain rules, branch model.
   - `AGENTS.md`: "Harness overrides" section (created by the template, otherwise add it): every harness rule that
     the project replaces, with its reason (branch convention, label taxonomy, merge policy…). This is where agents
     read where the project departs from the harness; the managed block points to it.
   - `.harness/config.json`: `protected_branches`, `integration_branch`, `branch_model` (A or B, BRANCHING-RELEASE.md).
   - `.github/labels.local.json`: the project's own labels (e.g. `area: …`, `calculation`, `regulatory`), in the same
     format as `.harness/labels.json` (`axis` optional, useful for issue hygiene). Remove the old labels file
     and its workflow if it duplicates the `labels` job of `harness.yml`.
   - `.github/workflows/harness.yml`: `push` branch, `flow` (model A or empty), jobs `docs`, `security`, `review` and `steward`
     to enable only if the project does not already have the equivalent; the `flow` job (dashboard) is on by default.
   - `.harness/config.json` → `compliance`: compliance frameworks whose reviewers are run ([COMPLIANCE](COMPLIANCE.md)). Delete the workflows it replaces (e.g. `branch-flow.yml`).
   - **Repository identity** ([CONVENTIONS](CONVENTIONS.md) §Repository identity): in `.github/repo-settings.json`,
     replace the template's description with one sentence and fill `topics` (5 to 15 keywords); a banner
     `docs/assets/banner.svg` at the top of `README.md` and a social preview `docs/assets/social-preview.png`
     (1280×640). Images missing: an issue, they can follow the adoption.
5. **Verify**: `../belayline/scripts/harness-sync.sh --target . --check` exits with 0; `git diff --stat` shows
   only what is expected; start a Claude session and see the "Belayline" message at startup.
6. **Single commit**, then draft PR:
   `Belayline 0.3.0: adoption` (body: what was removed from `CLAUDE.md`, workflows replaced, labels
   moved; no `### Ledger`: tooling).
7. **After the merge** (operator): run the "Harness" workflow by hand (`workflow_dispatch`) to create the labels;
   upload the social preview (Settings → General → Social preview);
   if this harness repository is private, check Actions access ([ADR 0001](adr/0001-distribution-mechanism.md)).

### Integration branch that is not the default branch
GitHub starts `issues`, `issue_comment`, `pull_request_target` and `schedule` workflows only from the copy on the
**default branch** (LESSONS L50). When the project works on another branch, the `issue` and `flow` jobs of
`harness.yml`, the weekly jobs and any project workflow on those events never run, and every label transition becomes
manual. So on a **first adoption** (no `.harness/lock` yet) `harness-sync.sh` stops before writing anything (exit
code 4), names what would never run and gives two ways out; then run the sync again:

1. **Make the integration branch the default branch** (Settings → General → Default branch), then
   `git remote set-head origin -a`. The simplest: nothing else to maintain.
2. **Or install the relay** on the default branch, before the adoption PR:
   - copy `templates/.github/workflows/harness-relay.yml` of the harness, at the tag you sync, to
     `.github/workflows/harness-relay.yml` of the **default branch**, by a PR to that branch; set its
     `INTEGRATION_BRANCH`, and copy the inputs of the `issue` and `flow` jobs of your `harness.yml` if you changed
     them; pin its `@vX.Y.Z` references to that tag's commit (`@<sha> # vX.Y.Z`, as the sync does for `harness.yml`);
   - `git fetch origin`: the sync sees the relay on `origin/<default branch>` and goes on (one 🟢 line).

   The relay runs, from the default branch, issue hygiene (`issues`), the daily dashboard (`schedule`) and, once the
   harness ships it (#62), the label reconcile (`issue_comment`, disabled until then). One job checks out the
   integration branch without a token and runs nothing from it: it fails with a message and changes nothing if the
   branch was deleted or renamed, or if its `.harness/config.json` names another branch. It never checks out a PR,
   and a comment on a PR runs nothing. It needs a harness version whose `issue-hygiene.yml` and `flow-report.yml`
   take the `ref` input (after 0.3.0). The day the integration branch becomes the default, it stops with a notice:
   delete it.
   **Updates**: the sync never writes to the default branch. Keep a copy of the relay on the integration branch too
   (inert there): the sync pins its references with those of `harness.yml`, and you carry the file to the default
   branch by a PR after each update.

Two branches kept on purpose, labels kept by hand: `"default_branch_check": false` in `.harness/config.json`
(created **before** the sync). The adoption then goes on and says once what will not run. On a project already
adopted, a later sync never stops: it prints a 🟠 line.

### Optional: automatic update PR
`harness-sync.yml` (created at adoption) looks at the latest tag every Monday and opens a draft PR. Settings:
- private harness: secret `HARNESS_TOKEN` (fine-grained token: *Contents: read* on `Belayline`; *Contents* and
  *Pull requests: write* on the project; *Workflows: write* if you also want the references of `harness.yml`, with the
  repository variable `HARNESS_SYNC_WORKFLOWS=true`);
- with `GITHUB_TOKEN` alone: Settings → Actions → General → "Allow GitHub Actions to create and approve pull requests".

### Optional: the plugin for local sessions
In a repository that has adopted the harness, the vendored skills and hooks are enough (and work in the cloud). The
plugin is useful on the Mac for repositories **not yet** adopted:
```bash
claude plugin marketplace add francoisgn/belayline-agentic-harness
claude plugin install belayline@belayline        # user scope
```
Its skills are then called `/belayline:lot-start`, etc. Automatic update: `/plugin` → Marketplaces →
Belayline → Enable auto-update. To declare it in a repository (local sessions only; a cloud session
ignores it), add to `.claude/settings.json`, with `ref` set to a harness tag:
```json
{
  "extraKnownMarketplaces": {
    "belayline": { "source": { "source": "github", "repo": "francoisgn/belayline-agentic-harness", "ref": "vX.Y.Z" } }
  },
  "enabledPlugins": { "belayline@belayline": true }
}
```
The plugin is named `belayline` on `master` and in every tag after v0.3.0
([ADR 0004](adr/0004-plugin-named-belayline.md)). With `ref` v0.3.0 or earlier it is `belay@belayline`, with skills
`/belay:<skill>`. A marketplace added without `ref` follows `master`; refresh it with
`claude plugin marketplace update belayline`.
In an adopted repository, prefer **not** to enable it (the skills would exist twice, `/lot-start` and
`/belayline:lot-start`).

## Updates
- Skill `/harness-update` (step-by-step guide), or by hand:
  ```bash
  git switch -c chore/harness-vX.Y.Z origin/develop
  ../belayline/scripts/harness-sync.sh --ref vX.Y.Z --target .     # or --source <clone at that tag>
  ```
  Read the harness's `CHANGELOG.md`, review `git diff`, one commit `Belayline: move to vX.Y.Z`, draft PR.
- A modification of a harness file in the project is refused at the next sync: propose it to the harness (PR on
  `Belayline`), or keep it outside the harness (project file), never by editing the vendored copy.
- `--check` in CI (optional): reports a vendored copy that is modified or behind `.harness/VERSION`.

## Per-project settings: language and exclusions
`.harness/config.json` (created by the first sync; create it **before** the sync so that its settings apply from
the first time):
```json
{
  "language": "en",
  "exclude": [".claude/skills/feedback-triage/*", ".github/ISSUE_TEMPLATE/*", "docs/lots/TEMPLATE.md"],
  "protected_branches": ["master", "dev-swift"],
  "integration_branch": "dev-swift",
  "branch_model": "B",
  "labels": { "model_prefixes": [], "size_prefixes": ["difficulty:"] },
  "ledger": { "enabled": true, "label": "ledger", "fold_command": "python3 tooling/docs/ledger.py fold --apply --commit" }
}
```
- `language`: the project's writing language (default `"en"`): the language agents use for code comments, commits,
  issues, PRs and docs. It only sets that. The harness itself is in English and has no translated copies.
- `exclude`: glob patterns on the **destinations** (`*` crosses `/`). An excluded file is not vendored; if it
  already was and has not been modified, the next sync removes it. Excluding `CLAUDE.md` or `AGENTS.md` turns off
  the management of the corresponding block.

Other keys, read by the hooks and the skills (missing: default values):

| Key | Default | Effect |
|---|---|---|
| `protected_branches` | `["main", "master", "develop", "beta"]` | Branches that the `guard-git` hook protects |
| `branch_types` | `["lot", "fix", "feat", "chore", "docs"]` | Branch types `<type>/<short-name>` offered by `/lot-start` and the hook |
| `orchestration.memory_issue` | `null` | Number of the orchestrator's memory issue, where `orch-state.py` keeps the State comment ([ORCHESTRATION](ORCHESTRATION.md) §8); `null`: the script prints the State and writes nothing |
| `labels.model_prefixes` | `["difficulty:"]` | Prefixes of the model-tier labels; `[]` = no such axis (tier deduced from the text and the routing) |
| `labels.size_prefixes` | `[]` | Prefixes of the size labels when the project has a separate size axis (e.g. `["size:"]`); `[]` = no such axis |
| `default_branch_check` | `true` | When `integration_branch` is not the repository's default branch (GitHub runs `issues`, `issue_comment`, `pull_request_target` and `schedule` workflows from the default branch only), a first adoption stops and later syncs, the session start and `pr-hygiene.yml` print a 🟠 warning ([above](#integration-branch-that-is-not-the-default-branch)); `false` does neither (the adoption says once what will not run) |
| `merge_gate.required_labels`, `merge_gate.security_labels`, `merge_gate.body_lines` | `[]`, `["type: security"]`, `["issue", "claim", "docs"]` | Merge gate (`merge-gate.py`, [CONVENTIONS](CONVENTIONS.md) §Pull requests): labels a PR needs before merge, labels that block until the operator decides, PR body lines checked; `[]` leaves the line out |
| `ledger.enabled`, `ledger.label`, `ledger.fold_command` | `false`, `"ledger"`, `""` | Ledger ([CONVENTIONS](CONVENTIONS.md) §Ledger): `### Ledger` section of the PRs (the entry), label the steward marks `<label>: done`, the steward's fold command |

`.harness/config.json` is a project file (created once): a key added by a new version of the harness does not add
itself to it; without it, the default applies.

### Example: ezzz/HFRnow (branch `dev-swift`, docs in English, its own lessons and lots)
1. Branch from `dev-swift` (never `master`, which is the legacy app); create `.harness/config.json` as above,
   excluding what HFRnow already has in a better form: its issue forms (`.github/ISSUE_TEMPLATE/*`), its PR template
   (`.github/pull_request_template.md`), its lot template (`docs/lots/TEMPLATE.md`), `.markdownlint-cli2.jsonc`, and
   the harness workflows (`.github/workflows/harness*.yml`): `ezzz/HFRnow` does not belong to `francoisgn`, it cannot
   call a reusable workflow of a private harness, and `issues` events only run from `master`. Add
   `"default_branch_check": false`: two branches are kept on purpose, otherwise the first sync stops.
2. Run the sync: `AGENTS.md` (HFRnow's entry point) receives the block at the end of the file, `CLAUDE.md` (which
   already imports `@AGENTS.md`) the block that imports `ESSENTIALS.md`; the harness's `.harness/docs/LESSONS.md`
   complements the project's `docs/agents/LESSONS.md`, which stays the reference (both are read at self-review;
   `/lessons-check` does it).
3. Keep HFRnow's label taxonomy (`type:`, `priority:`, `difficulty:`…): do not enable `apply-aliases`;
   `labels` above tells the harness that the size is read from `difficulty:` and that the model tier is deduced
   from the routing of `AGENTS.md` §6. Its branches `lot/`, `fix/`, `feat/`, `chore/`, `docs/` are the harness's;
   its ledger (#620) is the harness's "ledger" building block, with its own script.
4. Generic lessons born in HFRnow go up to the harness by PR on Belayline; lessons of the HFR domain
   stay in the project.

## Connecting your coding agent

The harness writes its rules once (`.harness/docs/`) and exposes them through two entry files: `CLAUDE.md` (marked
block) and `AGENTS.md` (marked block, [open format](https://agents.md)). Depending on the tool:

| Agent | How it loads the rules | State |
|---|---|---|
| Claude Code | `CLAUDE.md` (import of `ESSENTIALS.md`), vendored skills, agents and hooks; plugin locally | Adapter provided, tested |
| Codex CLI, Cursor, GitHub Copilot (agent) | `AGENTS.md` at the root, presented as read natively by these tools | 🟠 to verify in the tool's docs and the version used |
| Gemini CLI | Reads `GEMINI.md` by default; point the context file to `AGENTS.md` in `.gemini/settings.json` | 🟠 setting to confirm in the Gemini CLI docs |
| Aider | Load `AGENTS.md` as a conventions file (`read: AGENTS.md` in `.aider.conf.yml`) | 🟠 to confirm in the Aider docs |
| Other | Make it read `AGENTS.md`, or copy into it a pointer to `.harness/docs/ESSENTIALS.md` | — |

Sources consulted on 2026-11-07: the [agents.md](https://agents.md) format site and secondary articles (not the
official docs of each tool); hence the 🟠 state until a project has verified it. Skills, agents and hooks are
specific to Claude Code; for another agent, the method, labels, templates, CI and dashboard apply as they are, and
the skills read as procedures (`.claude/skills/<name>/SKILL.md`).

## Repository settings "as code"

A cloud session cannot change a repository's settings (LESSONS L56); it changes
`.github/repo-settings.json` by PR, and the `settings` job of `harness.yml` (reusable workflow `repo-settings.yml`,
script `.harness/scripts/repo-settings.py`) applies it at merge:

| Section | Effect |
|---|---|
| `repository` | Description (mandatory, [CONVENTIONS](CONVENTIONS.md) §Repository identity; the template's is never sent), website, features (wiki, discussions), merge policy, deletion of merged branches |
| `topics` | Full list of topics (5 to 15 expected; a warning if they are missing or malformed) |
| `rulesets` | Rulesets managed by name (created or updated, never deleted automatically): default branch protection, required checks |

- **Once, by the owner**: create a fine-grained token limited to the repository, "Administration: read and write",
  and store it as the repository secret `REPO_ADMIN_TOKEN`. Without it, the job warns and does nothing.
- **Drift**: every Monday the job compares the repository to the file and fails if a setting was changed by hand.
- Required checks: the name of a direct job of a workflow triggered by `pull_request` (the check of a reusable
  workflow's job is called `caller / called`). A wrong name would block every PR: `check-framework.py` verifies it
  for the harness, not for a project's template (verify by hand before adding one).
- No bypass (`bypass_actors`) is declared: in an emergency, an admin disables the ruleset in Settings, then
  restores it through the file.
- Without `--apply` (local): `GH_TOKEN=… python3 .harness/scripts/repo-settings.py --repo owner/name` prints the plan.

## Replacing or extending a building block

The harness is a **framework**: every building block has an extension point, none is imposed.

| Building block | Keep the harness's | Replace it with the company's | Extend it |
|---|---|---|---|
| Compliance reviewers | `compliance: ["gdpr"]` | `{"id": …, "agent": "<its agent>"}` | `{"id": …, "spec": "docs/compliance/<id>.md"}` ([COMPLIANCE](COMPLIANCE.md) §2) |
| Adversarial reviewer, stewards | vendored `.claude/agents/<name>.md` | Exclude the file (`exclude`) and put your own under the same name | A project agent under another name |
| Skills | vendored `.claude/skills/<name>/` | Exclude and put your own | Project skills under other names |
| Review service | `review` job (`ai-review.yml`) | CodeRabbit or another bot: do not enable `review` | `.harness/review-instructions.md` |
| Doc steward | `steward` job (`doc-steward.yml`) | Your own docs bot: do not enable `steward` | `.harness/steward-instructions.md`; inputs (`branch`, `since-days`, `audit-label`) |
| Security | `security.yml`, `docs-security.yml` | Company tools (GHAS, SonarQube, Snyk): do not enable these jobs | Inputs (`semgrep-configs`, `trivy-severity`) |
| Repository settings | `settings` job + `.github/repo-settings.json` | Company Terraform / Safe-settings: delete `settings` | Sections of the file |
| Dashboard | `flow` job | In-house steering tool: delete `flow` | Thresholds as inputs (`stall-hours`, `max-ci-runs`…) |
| Labels | `.harness/labels.json` | Keep your own taxonomy (`apply-aliases: false`) | `.github/labels.local.json` |
| Lessons, rules | `.harness/docs/` | — (the project's `CLAUDE.md` wins) | Project lessons and rules in its own files |

Rule: **never edit** a vendored copy (the sync refuses it); exclude and replace, or add alongside. A replacement
useful to everyone goes up to the harness by PR.

## Partial adoption
- **Rules only**: exclude `.github/*` and `docs/lots/*`.
- **Workflows and labels only**: do not run the sync; call the reusable workflows from the project's
  `harness.yml`, pointing `labels-file` to a copy of the taxonomy (repositories of `francoisgn` only if the harness
  stays private).

## Removal
Delete `.harness/`, the marked block of `CLAUDE.md`/`AGENTS.md`, the vendored skills (list in `.harness/lock`), the
two hooks of `.claude/settings.json` and `harness.yml` / `harness-sync.yml`.

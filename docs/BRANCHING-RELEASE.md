# Branches, versions and releases

Sources: practice proven on a published app (model A: branch document and flow-check workflow);
`AGENTS.md` §8, `CONTRIBUTING.md` §2 and rulesets of HFRnow (model B).

## Two models, one choice per project
The project writes its model in `CLAUDE.md` and in `.harness/config.json` (`branch_model`, `integration_branch`,
`protected_branches`: the list that the `guard-git` hook protects).

### Model A: integration → candidate → production (published app)
```
lot/*, fix/*, feat/*, chore/*, docs/*, dependabot/*  ──PR──▶  develop  ──PR──▶  beta  ──PR──▶  master
                                         integration     TestFlight      App Store
hotfix/* (from master) ──PR──▶ master, then carried over master → beta → develop
```
- `develop` is the default branch (PRs, Dependabot and scheduled workflows target it).
- **Promotion** = PR `develop → beta` then `beta → master` as a **merge commit**, never a squash: the histories stay
  identical from one branch to the next.
- **Hotfix**: `hotfix/<subject>` from `master`, PR to `master`, then PR `master → beta` and `beta → develop` (or
  cherry-pick) so the fix is not lost.
- Guardrail: `pr-hygiene.yml` with `flow: "beta:develop beta:hotfix/* master:beta master:hotfix/*"` refuses any PR to
  `beta` or `master` outside the flow; towards `develop`, nothing is enforced automatically.

### Model B: a single integration branch (engine, library, shared project)
- An integration branch protected by a ruleset: PR required, required checks, squash only, no force-push,
  conversations resolved. The "up to date with the base" requirement can be dropped so that CI does not rerun at
  every neighbouring merge (HFRnow, 28 October).
- **Squash** merge (one PR = one commit). Auto-merge, if allowed, is a merge decision.
- If merges do not close issues (integration branch that is not the default branch), whoever merges closes the
  issue with "Done in #PR (merged as `<sha>`)" and checks that it is closed.

## Common rules
- **No direct push** to a protected branch; **never force-push** a shared branch; never bypass a ruleset, push
  protection or gitleaks.
- Two lines of defence: the `guard-git` hook on the agent side refuses, before execution, force pushes, pushes to a
  protected branch (also `HEAD` or a bare `git push` from it), their deletion and `--no-verify`, through grouped
  options, `git -C`/`-c` and the common shell wrappers; it lets `--dry-run` through. It fails **open** (unreadable
  input, python3 missing) and can be bypassed (git alias, intermediate script or one passed on a shell's standard
  input, API): **the real protection remains the server-side ruleset** (PR required, no force-push, no deletion),
  always enabled.
- Work branches: `<type>/<short-name>` with the types `lot`, `fix`, `feat`, `chore`, `docs` (adjustable:
  `.harness/config.json` → `branch_types`), plus `hotfix/` in model A. One PR per lot, `Closes #n` for each issue.
- GitHub settings (rulesets, merge commits allowed, Dependabot alerts, auto-merge): versioned like code
  (`.github/rulesets/*.json` + `scripts/configure-repo.sh`, idempotent, run by the maintainer; a cloud session
  cannot change them). Tracked in a `type: chore` issue until it is done.

## Versions and tags
- **Semver `MAJOR.MINOR.PATCH`**, tag `vX.Y.Z`:
  - PATCH: fixes with no visible change to the expected behaviour;
  - MINOR: features, compatible visible changes;
  - MAJOR: breaking change (for an app: save format that cannot be migrated, prior `status: needs-decision`
    product decision; for the harness: a change that requires an action in the projects).
  Before 1.0.0, a MINOR can break: the CHANGELOG says so.
- The version (`MARKETING_VERSION` of the project's configurations, or `VERSION`) and the "What's New" entry are
  **not** modified by lot PRs. At integration:
  1. a PR "Version: <branch> moves to X.Y.Z" sets the version on the integration branch;
  2. the What's New entry (or `CHANGELOG.md`) is folded from the `### Ledger` sections of the merged PRs by the
     steward ([CONVENTIONS](CONVENTIONS.md) §Ledger), or, without a ledger, written from their descriptions;
  3. promotion (model A) or merge (model B);
  4. annotated tag `vX.Y.Z` on the production branch **after** the merge, by the operator (consequential action);
  5. release tracking issue (`type: chore`) closed, with the link to the tag and to the published build.
- **The harness itself: `VERSION` tells the gap.** `master` never carries a consumer-visible change under an already
  released number. `VERSION` (and `plugins/harness/.claude-plugin/plugin.json`) on `master` is the **next** version
  with the pre-release mark `-dev` (`0.4.0-dev`), from the first merged change after a release; a change a project
  need not act on still moves it (CHANGELOG: "Action: none"). The release PR removes the mark, renames
  `## Unreleased` to `## X.Y.Z — date` and the operator tags `vX.Y.Z`; the next change sets the next `-dev`.
  `ci.yml` and `scripts/local-check.sh` ("Valid JSON and consistent versions") fail on a non-empty `## Unreleased`
  under a released number, or a `-dev` of a number that already has its CHANGELOG heading. A project sees its gap
  with `harness-sync.sh --check` and at session start ("vendored X (commit) · harness now Y, N commits ahead"),
  when a harness clone is at hand (`HARNESS_CLONE`, `../belayline`); never a network call.
- Build number: incremented at each TestFlight / App Store upload, independent of the version.

## Deployment
TestFlight on the candidate branch, App Store on the production branch: Apple Developer account, then App Store
Connect API key (GitHub secrets) or Xcode Cloud. Until this is wired up, a `type: chore` issue tracks it.

# 0003 — Labels readable by axis: `axis: value`, states "needs triage" and "ready"

**Status:** Accepted — 2026-11-09 (maintainer), option 2

## Context
Survey of 2026-11-09 on the repositories that follow or inspired the harness.

- **iOS client** (437 issues, 269 PRs, 51 labels): four prefixed axes, kept exclusive by hand. Of 217 open issues,
  216 carry exactly one `status:`, and all carry a `type:` and a `priority:`. Most populated states:
  `status: ready` (84), `status: blocked` (64), `status: needs-triage` (52), `status: claimed` (16). The status is
  removed on close. No GitHub milestone, no assignee; lot and milestone live in the titles (`LOT-147`, `(M4)`).
  PRs are almost never labelled (202 of 269 are not): their state is read on the PR (draft, review, checks).
  The eight default GitHub labels have zero usage.
- **Rust project (fork)**: tracking outside GitHub; upstream uses `priority: critical|high|medium|low`, `needs info`,
  `in progress`, and proposes `difficulty: trivial|easy|medium|hard`.
- **The harness** (`templates/.github/labels.json`, 27 labels): French names without a prefix (`bloqué`,
  `à clarifier`, `pris en charge`), priorities with emoji (`P1 🔴`), two axes (`modèle:` ×4, `taille:` ×3) where the
  real project uses one (`difficulty:` ×4). None of the observed projects uses the canonical names of the harness;
  they go through the `aliases`.
- **Gaps**: the harness has neither "needs triage" nor "ready", which is 136 of the 217 open issues of the most
  active project. An agent cannot tell an issue that can be taken from one that is not triaged. `bloqué` mixes a
  technical dependency with a pending human decision.
- **Dead weight** (zero usage observed): `ux`, `release`, `feedback`, `taille:` ×3, `modèle:` ×4, `tableau de bord`,
  `revue: aucune`, `conformité`.
- The harness repository itself carries only the default GitHub labels: `labels.json` is not applied there, and the
  `leçon` label of its form does not exist.

## Options
1. **Keep the current names, add two states** (`à trier`, `prête`). No migration. The axes still cannot be filtered
   by prefix, the emoji stays in the priorities, the harness stays apart from what projects use.
2. **Move to `axis: value`, in English, ASCII, no emoji**; the current names become `aliases` (the mechanism exists,
   its direction is reversed). Migration: `labels-sync` with `apply-aliases: true`, plus `flow-metrics.py`,
   `issue-hygiene.yml`, the forms and the docs. Breaking change, so a minor version with an "Action" line.
3. **Option 2, with the set of names configurable by language** (`i18n/<language>/labels.json`). Same migration;
   French-speaking projects keep prefixed French names (`statut: prête`). Two sets to maintain.

## Decision
**Option 2.**

| Axis | Labels | Exclusive | Mandatory |
|---|---|---|---|
| `status:` (open issues, removed on close) | `needs-triage`, `ready`, `claimed`, `blocked`, `needs-decision` | yes | yes |
| `type:` | `bug`, `feature`, `chore`, `docs`, `security`, `epic` | yes | yes |
| `priority:` | `critical`, `high`, `medium`, `low` | yes | after triage |
| `difficulty:` | `trivial`, `easy`, `medium`, `hard` (the recommended model tier goes in the description) | yes | after triage |
| `needs:` (can be combined, issues and PRs) | `info`, `host`, `review` | no | no |
| tracking | `direct-pr`, `dependencies` | no | no |
| local (`labels.local.json`) | `area: <module>`, `origin: …`, labels that trigger CI, `lesson` for the harness repository | — | — |

- 24 labels instead of 27; four exclusive axes readable by prefix.
- `status: needs-decision` (formerly `à clarifier`) separates "a human must decide" from `status: blocked`
  (dependency, access, capture).
- **No label per lot or per milestone**: milestone = GitHub milestone; lot = `type: epic` with sub-issues,
  identifier `LOT-NNN` kept in the title.
- **No PR state label** by default: draft, review decision and checks are read on the PR; `needs: review` stays
  available for a ready PR with no reviewer.
- Claim: `status: claimed` + dated comment (session, branch); flagged as abandoned after 24 h with no draft PR and no
  progress comment.
- Removed: `ux` (becomes a local `area:`), `release` (milestone), `feedback` (`type: epic`), `taille:` and `modèle:`
  (`difficulty:`), `tableau de bord`, `revue: aucune`, `conformité` (local if needed).
- The state is read **without a workflow**: `issue-hygiene` checks (exactly one `status:` and one `type:` per open
  issue, `status:` removed on close) but the rule also holds when applied by hand.
- `labels-sync` reports unused default GitHub labels instead of letting them duplicate the axes.

Reading the state of a project:

| Question | Query |
|---|---|
| In progress | `label:"status: claimed"`, open PRs |
| Can be taken | `label:"status: ready"`, sorted by `priority:` |
| Blocked / human decision | `label:"status: blocked"` / `label:"status: needs-decision"` |
| To triage | `label:"status: needs-triage"` |
| Out of reach of a cloud session | `label:"needs: host"` |
| By milestone / by lot | `milestone:<name>` / sub-issues of the epic |

## Consequences
- Easier: filtering by axis, writing the dashboard and the README progress table, welcoming an English-speaking
  contributor, aligning with what projects already do.
- Harder: one migration per project (aliases applied once), `flow-metrics.py` and `issue-hygiene.yml` to adapt with
  their tests, docs to rework (METHODOLOGY, ESSENTIALS, STEWARDS, forms).
- Migration: the old French names remain as `aliases` in `templates/.github/labels.json`, for a one-time migration
  with `apply-aliases: true`.
- To watch: the "French everywhere" rule no longer applies to label names; say so in CONVENTIONS.
- To do first, whatever the option: apply `labels.json` to the harness repository.

## Amendment 2026-11-11: `status: on-hold`
The first consumer showed `status: blocked` carrying two meanings: 21 issues were blocked with every cited blocker
closed (held by a decision, a milestone not yet open) and 21 more named no blocker. A label that encodes a policy
cannot be cleared by a script. The `status:` axis now has six states, still exclusive and mandatory:
- `status: blocked`: waits on something nameable that will end (issue or PR, capture, access, a third party's
  decision). The description names it in a `### Blocked by` section, one line per blocker; `issue-hygiene` reports a
  blocked issue without one and never relabels it.
- `status: on-hold` (new): held by a decision of the operator (milestone not open, operator's call), not by a
  dependency. `flow-metrics.py` and `readme-progress.py` show it apart: not a bottleneck, not ready.
- Reading the state: `label:"status: on-hold"` next to the blocked / needs-decision query.
- Consequence: one more label (25); a project that does not want it aliases or drops it in `labels.local.json`.
The decision above is unchanged; this only adds a state.

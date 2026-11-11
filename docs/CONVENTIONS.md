# Conventions: commits, PRs, comments, persistence

Sources: `AGENTS.md` §5, §8 of HFRnow (PRs, merge, duplicates, claims, ledger #620); practice proven on other
projects (commit conventions, version and What's New, save compatibility).

## Language
Project language: write the interface, code comments and domain names, commits, issues, PRs and docs in the
project's language (`.harness/config.json` › `language`, default English). The harness itself is in English. A
project can decide otherwise: it writes it in its `CLAUDE.md`, which wins.

## Branches
`<type>/<short-name>` for everyone, agent or human: `lot/` (a lot of the plan, e.g. `lot/082-reader-links`),
`fix/`, `feat/`, `chore/`, `docs/`; `hotfix/<subject>` from the production branch (model A). The types are set in
`.harness/config.json` (`branch_types`). The name does not say who is working: the claim (`/claim`) and the PR's
`Claim:` line say it. A branch starts from the **up-to-date** integration branch.
Detail and promotions: [BRANCHING-RELEASE](BRANCHING-RELEASE.md).

## Commits
- One **atomic commit per issue** (or per logical step of an issue), message in the project's language, present
  tense, in the style of the existing commits (`git log`): `Tab: what changes (#n)` or `Area: what changes`. Say
  **why** when it is not obvious.
- Attribution at the end of the message as the session instructs, for example:
  ```
  Co-Authored-By: Claude <model> <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_…
  ```
- Never a generated artefact, `DerivedData`, `.build`, or a file ignored by `.gitignore`.
- Small commits, **pushed often** to the draft PR (a crash loses minutes, not hours); nothing costly runs on a
  draft ([CI-BUDGET](CI-BUDGET.md) §2). Once the PR is ready: one commit per review round.

## Pull requests
- Opened **as a draft** from the first push (nothing costly runs), moved to "Ready for review" when everything is
  finished, reviewed, compiled.
- **Title** in the style of the previous PRs: `Area: summary (#n)`, `Review 0.6.0 (3): …`, `LOT-012: …`.
- **Body**, short, in this order (template `templates/.github/pull_request_template.md`):
  1. `LOT-XXX` for a lot PR;
  2. `Closes #n`, **one line per issue** (`Refs #n` for partial work, saying what is left; `Direct-PR: <reason>`
     for a small fix without an issue, never for a lot);
  3. `Claim: <id>` on its own line, equal to the issue's active claim (§GitHub comments);
  4. the problem, the cause, what changes and why this wide and no wider;
  5. the tests: names, what they check, shown failing without the change; commands run; watch points / not tested
     (e.g. app not compiled in the Linux container, to validate on iPhone);
  6. the **doc impact**: a `Docs:` line naming the doc files the change makes untrue (updated in the PR, or by the
     steward from the ledger), or `Docs: none (<reason>)`; in the **`### Ledger`** section if the project keeps a
     ledger (§Ledger), otherwise in the body;
  7. author and reviewer models; the generation line last.
- Do not merge yourself unless the project's policy says otherwise (depending on the project: the maintainer merges,
  or the author merges a ready and approved PR, except for risky flows).
- **Merge procedure** (whoever merges): run the gate, `python3 .harness/scripts/merge-gate.py <pr>` (read-only; `ok`
  / `missing` per line: draft, mergeable, CI green on the head, adversarial APPROVED naming the head, open threads,
  `Open questions` of the report, `merge_gate` labels, body lines). Merge only on "may merge", **with the head sha it
  prints** as the expected head (`gh pr merge <pr> --match-head-commit <sha>`); "could not check" (exit 2) is never a
  go. Then run the label reconcile, once the project has it (#62). A report (a PR comment carrying
  `<!-- harness:report -->`, otherwise the PR body) keeps its `Open questions` section empty or `none`.
- No new PR while one of your own has a review comment without a reply.
- Before opening: search for duplicates (issues and PRs, open and closed) and for PRs that touch the same files.

## Ledger: never a conflict on a shared file
Optional building block, for projects that keep a shared log-like file (CHANGELOG, What's New, gap report, tracking
table) that many PRs would want to modify at the same time.
- A work PR **never touches** these files. Its entries go in a `### Ledger` section of the **PR body**, in fenced
  blocks whose language is the entry type (e.g. ` ```changelog `, ` ```gap-new `), and the PR carries the `ledger`
  label. No entry: no block, no label.
- **Doc impact**: the section always has a `Docs:` line, outside the blocks, listing the doc files the PR makes
  untrue (`Docs: README.md, docs/USAGE.md`), or `Docs: none (<reason>)` (`Docs: none (internal refactor)`). Docs
  never drift further than one merge: the steward reads the line at merge time. `pr-hygiene.yml` warns, never
  fails, when a ready PR changes code paths (input `docs-code-paths`, default every file but `.md`; empty switches it
  off) and has no `Docs:` line, when `none` has no reason, or when a listed file does not exist on the PR head.
  Without a ledger, the same line lives in the PR body; nothing else changes.
- After each merge, a **steward** (upkeep role, [STEWARDS](STEWARDS.md) §2, `doc-steward.yml`) runs the project's
  script that reads the merged PRs labelled `ledger` and **folds** their entries into the files, in **a single draft
  docs PR**; once that PR is merged, the next pass replaces `ledger` with `ledger: done` on each folded PR. The
  script gets the pending PR numbers in `STEWARD_LEDGER_PRS` and may write the ones it folded to the file
  `$STEWARD_FOLDED` (otherwise all count as folded); the others stay in their PR and are listed in the docs PR.
- The fold is that PR's **"Fold the ledger" commit**, verified without an adversarial review: **the script must
  reproduce it** (on its base, the command written in the commit message, then `git diff --exit-code <commit>`, shows
  no difference). The PR's other commits (docs named by the `Docs:` lines) are reviewed like any change.
- No lock, no conflict, no late push to rebase a log, no CI rerun for one line.
- The adversarial reviewer reviews the `### Ledger` section like code. A malformed entry is reported and skipped by
  the steward (the others are folded): the author fixes the PR body, not the files.

Wiring the block in: the harness provides the convention and the PR body checks (`pr-hygiene.yml`, inputs
`ledger-label` and `docs-code-paths`); the project provides its fold script (block format, target files, order, idempotence), declared in
`.harness/config.json` → `ledger` (`enabled`, `label`, `fold_command`), and a CI check that refuses a PR outside
the steward's branch touching the ledger files. The labels `ledger` and `ledger: done` go in
`.github/labels.local.json`. Full example (block format, script, check): `tooling/docs/README.md` of HFRnow
(branch `dev-swift`, #620). Without a ledger (`ledger.enabled` missing or false), none of this applies.

## GitHub comments
- **Claim**: a comment whose **first line** is `/claim <id>`, followed by the plan in 3 to 5 bullets. `<id>` is the
  agent's id ([ORCHESTRATION](ORCHESTRATION.md) §7), or `human/<login>` for a human; it does not change until the
  end of the work. The issue's comments are **replayed in order**: the first claim wins, another `/claim` is
  refused while the first holds; `/release` (or `/release <id>`) hands it back. Only the comments of repository
  members (owner, members, collaborators) count: a contributor without rights asks a member to claim for them. A
  project can automate the replay (a workflow that sets and removes the status label, and replies to a refused
  claim); without automation, the orchestrator or the maintainer sets the label.
- End: done, PR link, what is left, decisions taken, to validate on the device.
- Issue resolved without `Closes`: "Resolved by #PR". Merge into a branch that does not close issues: "Done in
  #PR (merged as `<sha>`)", then check that it is closed.
- Blocker: a comment that starts with `BLOCKED:` with the exact question or the list of what is missing.
- Decision needed from the operator, in an autonomous session: a line ending with "Decision needed (operator)",
  then move on to the next item.
- Never `@mention` a person or a bot without a reason (it sends emails); from the cloud, mentions are
  altered (LESSONS L46).
- **Every comment written by an agent ends with an attribution footer that names the agent.** Claude Code:
  ```
  ---
  _Generated by [Claude Code](https://claude.ai/code)_
  ```

## Persistence: backward compatibility
**A save written by a published version must stay readable by every later version.**
- New field → optional or with a default value, decoded tolerantly (`decodeIfPresent`).
- Renamed or removed field → migration on read (old key read then converted, dedicated function such as
  `migrate(legacy:)`), tested with a real save from the old version (frozen test file).
- The format version (`payloadVersion`) is incremented only for a change that cannot be migrated, and that needs
  a product decision (`status: needs-decision` issue).
- Accepted trade-off: an older version may not be able to read a more recent save (devices not up to date that
  share iCloud).
- SwiftData + CloudKit: never `@Attribute(.unique)`, optional or defaulted properties, optional relationships.

## Version and "What's New"
Lot PRs touch **neither** the version (`MARKETING_VERSION` or equivalent) **nor** the What's New file: both are
handled at integration (version set on the integration branch by a dedicated PR, What's New folded from the
`### Ledger` sections of the PRs by the steward, or written from their descriptions without a ledger), then tag
`vX.Y.Z` after the promotion. Detail: [BRANCHING-RELEASE](BRANCHING-RELEASE.md).

## Docs
- One file, one role; `CLAUDE.md` (or `AGENTS.md`) is the single entry point, everything else hangs off it.
- The `.md` files carry the durable context and point to issues `#n`; a TODO lives in an issue.
- Domain rules are sourced (regulation or protocol file kept up to date, dated facts).
- A structuring decision = an ADR (`docs/adr/NNNN-title.md`, template [adr/TEMPLATE.md](adr/TEMPLATE.md)). An
  accepted ADR is not rewritten: it is superseded by another.
- An operator's personal instructions go in an unversioned `CLAUDE.local.md`, not in the repository.

## Repository identity
Every repository that follows the harness says what it is without anyone opening a file: a **description**,
**topics**, a **banner** and a **social preview**.

| Item | Where it lives | Rule |
|---|---|---|
| **Description** | `.github/repo-settings.json` → `repository.description` | one sentence: what the project does, for whom; not the template's text, not a feature list; kept true when the scope changes |
| **Topics** | `.github/repo-settings.json` → `topics` | 5 to 15 keywords a visitor would search for: domain, technology, use; lowercase, digits and hyphens, 50 characters at most, 20 topics at most ([GitHub docs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics)); prefer a topic already in wide use to an invented word |

Both are changed by PR and applied at merge ([ADOPTION](ADOPTION.md) §Repository settings "as code");
`repo-settings.py` warns if they are missing or malformed, and never sends the template's description.

The **two images** state the intent at first glance (what the project does and for whom, not a decorative logo
or a screenshot):

| Image | File | Format | Where it is used |
|---|---|---|---|
| **Banner** | `docs/assets/banner.svg` (or `.png`) | wide (about 3:1), readable at 800 px wide, clean background (light and dark themes), alt text that describes it | first image of `README.md`, under the title |
| **Social preview** | `docs/assets/social-preview.png`, its source next to it (`.svg` or other) | PNG **1280×640**, under 1 MB, the essentials more than 40 px from the edges | preview of the repository link (social networks, messaging apps) |

- Both share the same motif and the same project name; one sentence of intent at most, no feature list. Their text
  is in **English** (a link preview travels beyond the project's audience), unless the project's audience speaks
  only one other language. No secret, no personal data, no third-party trademark.
- The social preview **is uploaded by hand**: repository → Settings → General → Social preview
  ([GitHub docs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview),
  which also gives the size and the weight). It is a repository setting: the agent prepares the file and reports
  it, the operator uploads it (ESSENTIALS §Guardrails). `repo-settings.py` does not cover it.
- They change when the project's intent changes, not at every version. The doc steward checks the four items
  ([STEWARDS](STEWARDS.md) §2); missing or out of date → an issue.

## Secrets
No secret in the repository. CI secrets in GitHub secrets; locally, in configuration files ignored by git;
third-party API keys injected, never committed. gitleaks and push protection block: never bypass them. A
vulnerability is reported privately (SECURITY.md), never in a public issue.

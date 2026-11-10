# 0001 — Distributing the harness: versioned vendoring + plugin + reusable workflows

**Status:** Accepted — 2026-11-07 (the maintainer)

## Context
- The rules for agentic work were born in two repositories (HFRnow, ios-app_credit-immo) and diverge there. We want
  a single, versioned source that each project fetches and updates, without losing what is specific to it.
- Most sessions are **cloud sessions** (claude.ai/code). According to the Claude Code documentation ("Install
  plugins", *Cloud session* tab, read on 2026-11-07), a cloud session **does not load** the plugins installed on the
  user's machine nor those enabled by the repository's `.claude/settings.json`; only server-managed settings
  (Team/Enterprise plan) install plugins there. A cloud session does, however, read `CLAUDE.md`, its `@path` imports
  located **inside** the repository, `.claude/skills/` and the hooks of `.claude/settings.json`.
- An `@path` import that leaves the repository (`~/…`, absolute path) is "external": an approval window is shown,
  and it does not exist in the cloud.
- A cloud session has GitHub access only to the repositories attached to it; an Actions workflow reaches another
  private repository only with a dedicated token.
- Files under `.github/workflows/` cannot be pushed with the Actions `GITHUB_TOKEN`.
- HFRnow lives on `ezzz/HFRnow` (not a repository of the maintainer) and its docs are in English.

## Options
1. **Git submodule**: versioned, but heavy for agents (init, detached), invisible in the cloud if not initialised,
   and an `@` import to a submodule that is not cloned fails silently.
2. **Claude Code plugin alone** (marketplace): clean updates, but nothing in a cloud session; no GitHub checks.
3. **Manual copy**: divergence guaranteed.
4. **Versioned vendoring by script + plugin + reusable workflows** (chosen).

## Decision
Three complementary channels, a single source (this repository, tags `vX.Y.Z`):
1. **Vendoring** (main channel, works everywhere, cloud included): `scripts/harness-sync.sh` copies, at a given
   version, the docs into `.harness/docs/`, the taxonomy into `.harness/labels.json`, the skills into
   `.claude/skills/`, the hooks into `.harness/hooks/` (declared by merge in `.claude/settings.json`), and manages a
   **marked block** `<!-- harness:begin harness -->…<!-- harness:end harness -->` in `CLAUDE.md` and `AGENTS.md`,
   which imports `@.harness/docs/ESSENTIALS.md`. Everything outside the markers belongs to the project and is never
   touched. Version and fingerprints live in `.harness/VERSION` and `.harness/lock`: a local change to a harness file
   is detected and never overwritten without `--force`.
2. **Plugin** `belay@belayline` (this repository is a marketplace): the same skills and hooks for **local**
   sessions (Mac, terminal) and for repositories that have not adopted the harness yet. If a repository has both,
   the vendored copy wins (the plugin's session hook stays silent).
3. **Reusable workflows** (`on: workflow_call`) called by a thin `harness.yml` in the project: label sync (harness +
   `labels.local.json`), issue hygiene, PR hygiene (branch flow, `Closes`, Changelog), docs and security baseline.
   They read the project's **vendored** files: only the `uses:` call touches this repository. A `harness-sync.yml`
   workflow in the project proposes a draft PR to the latest tag every week.

## Consequences
- 🟢 Works in the cloud with no configuration; versions are explicit and reviewed by PR; the project stays in
  control (marked block, `seed` files, `labels.local.json`, `.harness/config.json`); no duplicate rules to maintain
  by hand.
- 🟠 Files duplicated in each repository (a few dozen KB): that is the price of working in the cloud.
- 🟠 **Access if this repository is private**:
  - Actions: consumer repositories must belong to `francoisgn` and this repository must allow access (Settings →
    Actions → General → Access: "Accessible from repositories owned by the user"). A repository with another owner
    (e.g. `ezzz/HFRnow`) or a **public** repository cannot call a reusable workflow from a private repository: it
    keeps local copies of the workflows, or this repository becomes public;
  - `harness-sync.yml`: secret `HARNESS_TOKEN` (fine-grained token, read access to this repository's contents);
    without it, only a public harness can be read;
  - cloud session: attach this repository to the session (`add_repo`) to run `harness-sync.sh --ref`;
  - plugin: the machine's `git` must be able to clone this repository without a prompt (`gh auth login` +
    `gh auth setup-git`, or a loaded SSH key); otherwise the automatic background update fails silently.
  Making this repository public lifts all these limits; it contains no secret and nothing specific to a product.
- 🟠 The `GITHUB_TOKEN` does not push `.github/workflows/`: the sync PR skips these files (and says so) unless there
  is a token with "Workflows: write" and the variable `HARNESS_SYNC_WORKFLOWS=true`.
- 🟠 A project in English (HFRnow): the block and the vendored docs are in French; HFRnow can adopt only the
  workflows and the taxonomy (with `apply-aliases` when its docs are ready), or wait for an English edition (issue to
  open if needed).
- The `version` of the plugin (`plugin.json`) and of the harness (`VERSION`) move together: without a change of
  `version`, plugin users do not receive the new commits. The harness CI checks that they are equal.

Amendment, 2026-11-09: the harness is now written in English only (see CHANGELOG, Unreleased). The block id and the
file name above are the current ones (`harness`, `ESSENTIALS.md`; formerly `cadre`, `ESSENTIEL.md`). The consequence
about a project in English no longer applies.

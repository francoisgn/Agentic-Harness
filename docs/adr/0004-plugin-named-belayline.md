# 0004 — The Claude Code plugin is named `belayline`

**Status:** Accepted — 2026-11-10 (maintainer)

## Context
The Claude Code plugin shipped as `belay` in the `belayline` marketplace (`belay@belayline`, skills
`/belay:<skill>`), per [ADR 0001](0001-distribution-mechanism.md). A landscape audit on 2026-11-10 found at least two
2026 agent-safety tools that use `belay` as a command or module name:
[haqaliz/belay](https://github.com/haqaliz/belay) (PyPI `belay-harness`) and
[SECBLOK/belay](https://github.com/SECBLOK/belay); [mikepenz/agent-belay](https://github.com/mikepenz/agent-belay)
and [hev/belaykit](https://github.com/hev/belaykit) are close. The product name Belayline is not used by any of them
([POSITIONING](../POSITIONING.md), [#50](https://github.com/francoisgn/belayline-agentic-harness/issues/50)). The harness is before 1.0, where a MINOR may break with an
"Action" line in the CHANGELOG ([BRANCHING-RELEASE](../BRANCHING-RELEASE.md)).

## Options
1. **Keep `belay`**: short, already installed; shares a name with security tools in the same space, which confuses
   users and search.
2. **Rename to `belayline`**: one name for the product, the marketplace and the plugin; skills become
   `/belayline:<skill>`; plugin users reinstall once.

## Decision
The plugin is named `belayline`: `claude plugin install belayline@belayline`, skills `/belayline:<skill>`. The
marketplace keeps its name `belayline`. Vendored skills (`/lot-start`, …) are not affected.

## Consequences
- 🟢 One identity across product, marketplace and plugin; no shared namespace with other agent tools.
- 🟠 Users of the plugin reinstall it under the new name and update `enabledPlugins` in `.claude/settings.json`
  (CHANGELOG "Action"). Projects that use only the vendored copy have nothing to do.
- Trademark questions were not assessed; this decision is about clarity, not legal risk.

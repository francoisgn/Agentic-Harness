# A hard cap on lot size

- **Asked in:** [#44](https://github.com/francoisgn/belayline-agentic-harness/issues/44) (landscape audit of
  2026-11-10: sacuadros/agent-harness)
- **Decision:** declined on 2026-11-10
- **Why:** it fails the observed-failure test of [SCOPE.md](../SCOPE.md): no lot has gone wrong for lack of a size
  limit, and lots legitimately differ in size (a migration or a repository-wide rename cannot be split), so a cap would
  block correct work or be bypassed. The method keeps a recommendation instead: split as much as possible, an epic
  issue heads each stream, and a lot that stays big says why (METHODOLOGY §5).
- **What would change the answer:** lots that repeatedly fail review or stall because of their size even though the
  recommendation was applied.

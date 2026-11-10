# Guard hooks that fail closed (block the command when the hook itself errors)

- **Asked in:** [#41](https://github.com/francoisgn/belayline-agentic-harness/issues/41) (landscape audit of 2026-11-10: sacuadros/agent-harness, SECBLOK/belay)
- **Decision:** declined on 2026-11-10
- **Why:** it fails the observed-failure test of [SCOPE.md](../SCOPE.md): no project has seen `guard-git` crash and let
  a forbidden push through. `guard-git` fails open on purpose (a bug in the hook never blocks work), and the real
  protection stays the server-side ruleset ([BRANCHING-RELEASE](../docs/BRANCHING-RELEASE.md) §Common rules).
- **What would change the answer:** a forbidden push, force-push or `--no-verify` that went through because the hook
  errored or could not start.

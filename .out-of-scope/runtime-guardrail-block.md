# A "runtime guardrail" building block (per-action policy gate, audit log) in ADOPTION

- **Asked in:** [#46](https://github.com/francoisgn/belayline-agentic-harness/issues/46) (landscape audit of
  2026-11-10: SECBLOK/belay, mikepenz/agent-belay)
- **Decision:** declined on 2026-11-10
- **Why:** it fails the observed-failure test of [SCOPE.md](../SCOPE.md): no consumer project has needed a per-action
  policy gate or an audit log of agent commands. Belayline governs the process and leaves runtime gating to the
  agent's own permissions or to a dedicated tool ([POSITIONING](../docs/POSITIONING.md) §1, §4).
- **What would change the answer:** a consumer project that needs a per-action gate or an agent audit log, for
  example to meet a compliance requirement.

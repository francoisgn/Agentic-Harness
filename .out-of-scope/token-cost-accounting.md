# Token and spend accounting per run or per PR in the dashboard

- **Asked in:** [#43](https://github.com/francoisgn/belayline-agentic-harness/issues/43) (landscape audit of
  2026-11-10: latintzar/harness, mikepenz/agent-belay)
- **Decision:** declined on 2026-11-10 (maintainer)
- **Why:** Belayline's FinOps stays at the level of the split (the right model tier, early delegation, bounded
  loops); it does not count tokens, judge whether an API key or a subscription pays off, or compute a user's return
  on investment, which only the user knows. Reading usage would also need each provider's API and a secret, which
  the toolbox test of [SCOPE.md](../SCOPE.md) rules out for a core feature.
- **What would change the answer:** a consumer project that cannot apply FINOPS routing without per-run usage data
  from the harness itself.

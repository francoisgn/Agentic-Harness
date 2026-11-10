# Token and spend accounting per run or per PR in the dashboard

- **Asked in:** [#43](https://github.com/francoisgn/belayline-agentic-harness/issues/43) (landscape audit of
  2026-11-10: latintzar/harness, mikepenz/agent-belay)
- **Decision:** declined on 2026-11-10
- **Why:** it fails both tests of [SCOPE.md](../SCOPE.md): no project has failed for lack of per-run usage data
  (observed failure), and collecting it needs each provider's API and a secret (toolbox test). It also falls outside
  Belayline's FinOps, which stays at the level of the split (model tier, early delegation, bounded loops): the
  harness does not collect token usage (an operator may read the trend in the provider's console, FINOPS §4), judge
  whether an API key or a subscription pays off, or compute a user's return on investment.
- **What would change the answer:** a consumer project that cannot apply FINOPS routing without per-run usage data
  from the harness itself.

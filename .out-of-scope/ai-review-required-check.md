# AI review as a required check

- **Asked in:** CI baseline review of 2026-11-09 ([CI-BASELINE](../docs/CI-BASELINE.md) §5)
- **Decision:** declined on 2026-11-09
- **Why:** it needs a secret, so it cannot run on fork PRs, and a required check must pass without secrets. It
  would also make merging depend on a paid service.
- **What would change the answer:** a review runner that needs no secret on the PR event. Until then the AI review
  service stays optional and advisory; the adversarial review by another model happens before "Ready for review".

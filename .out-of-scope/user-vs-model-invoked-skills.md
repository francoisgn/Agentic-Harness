# Skills invoked only by the human (`disable-model-invocation`)

- **Asked in:** [#19](https://github.com/francoisgn/belayline-agentic-harness/issues/19) and the harness review of 2026-11-09/10 ([#9](https://github.com/francoisgn/belayline-agentic-harness/issues/9))
- **Decision:** declined on 2026-11-10
- **Why:** it fails the observed-failure test: no model-triggered skill has caused a failure, and with 11 skills the gain is marginal. It also adds a setting to every skill that must be kept in step, for little return.
- **What would change the answer:** a skill with side effects that the model triggers on its own, or a skill list large enough to weigh on context.

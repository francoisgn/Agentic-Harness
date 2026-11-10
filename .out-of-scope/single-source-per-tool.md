# One source compiled into per-tool skill formats (Cursor, Codex, Gemini CLI)

- **Asked in:** [#19](https://github.com/francoisgn/belayline-agentic-harness/issues/19), [#45](https://github.com/francoisgn/belayline-agentic-harness/issues/45) (landscape audit) and the harness review of 2026-11-09/10 ([#9](https://github.com/francoisgn/belayline-agentic-harness/issues/9))
- **Decision:** declined on 2026-11-10
- **Why:** it fails the observed-failure test: no consumer project uses Cursor, Codex or Gemini CLI, and the agents that read `AGENTS.md` already get the rules. It also adds generated per-tool files and a build step to keep in sync, which cuts against the toolbox test in [SCOPE.md](../SCOPE.md).
- **What would change the answer:** a consumer project on one of those tools.

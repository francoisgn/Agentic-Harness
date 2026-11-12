# Sources read for part 6 (working notes)

Vendor facts gathered for `docs/factory/spawn-economics.md`, each with its URL and the date read.

- <https://code.claude.com/docs/en/sub-agents> (read 2026-11-11): "Each subagent runs in its own context window
  with a custom system prompt, specific tool access, and independent permissions." `model` field: `sonnet`, `opus`,
  `haiku`, `fable`, a full model id, or `inherit`. Background subagents: "When a background subagent reaches a tool
  call that needs permission, Claude Code surfaces the prompt in your main session and names the subagent that is
  asking."
- <https://platform.claude.com/docs/en/build-with-claude/prompt-caching> (read 2026-11-11): default cache lifetime
  5 minutes; cache reads 0.1 times the base input price (lower for some models: 0.05 for Opus 5.5 and Sonnet 5.5,
  0.025 for Fable 5.x); 5-minute cache writes 1.25 times; hits need 100 percent identical prompt segments.

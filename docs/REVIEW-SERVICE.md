# Review service: the in-house equivalent of CodeRabbit

Definition of the harness's automatic PR review service. It **complements** the session's adversarial review
([ORCHESTRATION](ORCHESTRATION.md) §3) and does not replace it. Implementation: reusable workflow
`.github/workflows/ai-review.yml` (action `anthropics/claude-code-action`, pinned by SHA).

## 1. Service contract

| Item | Definition |
|---|---|
| Trigger | **Ready** PR (`ready_for_review`, then `synchronize`); never a draft; project-local label `review: skip` → skipped |
| Inputs | Diff `base...head`, linked spec (`Closes`/`Refs`), `CLAUDE.md`, `ESSENTIALS.md`, `LESSONS.md`, project instructions (`.harness/review-instructions.md`) |
| Output | **One** review comment per head: verdict `APPROVED` / `CHANGES REQUESTED`, numbered findings (High / Medium / Low / Nit, `file:line`, failure scenario, fix), "Verified" list |
| Rights | Read the code; a PR **comment** only (`gh pr comment`), never a GitHub review: it cannot approve, even under prompt injection. No commit, no push, no merge |
| Model | Tier ≥ the issue's, **other** than the author if possible; default: solid; frontier for risky flows |
| Secrets | `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` (repository or organisation secret) |
| Forks | No secret → job skipped; this is why the check is **never required** in the ruleset |
| Cost | 1 Linux job + the tokens of one review; cancelled by a new push (`concurrency`); bounded turns |

## 2. What sets it apart from a generic bot
- It judges against **our** rules: lessons (`L..`), conventions, definition of done, cited sources, CI budget.
- It does not comment on style that a linter catches, and groups the cases of one class (fewer rounds).
- An exploitable flaw is never detailed publicly.
- Its findings follow [REVIEW-ROUNDS](REVIEW-ROUNDS.md) like CodeRabbit's: a claim to verify, one commit
  per round, one reply per thread.

## 3. Optimising rounds (agentic volume)
A repository where agents push most of the commits multiplies reviews. Levers, from most to least effective:
1. **Prevent**: `/lessons-check` and the adversarial review **before** "Ready"; the service must find only what
   escaped both. A finding already in LESSONS = the self-review needs tightening.
2. **One review per ready head**, not per push: draft while working, one push per round.
3. **Incremental review**: on the next round, instruct it to review only `last-reviewed-sha...head` (the service reads
   its previous review).
4. **Bound**: beyond 3 rounds, the orchestrator stops the loop ([FINOPS](FINOPS.md) §3).
5. **Grade**: project-local label `review: skip` for trivial PRs (patch Dependabot, typo), frontier model only
   on the labels `type: security`, `difficulty: medium` or `difficulty: hard`.

## 4. Setting it up in a project
1. Secret `ANTHROPIC_API_KEY` (or Claude Code OAuth token); Claude GitHub app installed by the owner (L57).
2. In `.github/workflows/harness.yml`, enable the `review` job (commented template).
3. Optional: `.harness/review-instructions.md` (rules per directory, like CodeRabbit's `path_instructions`).
4. If CodeRabbit stays installed: keep both for a while, compare the relevant findings over 10 PRs, then
   keep only one (do not pay twice).

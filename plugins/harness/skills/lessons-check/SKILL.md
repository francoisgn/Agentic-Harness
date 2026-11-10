---
name: lessons-check
description: Self-review of the current diff against the lessons table of the Belayline harness (and the project's) before a PR or a review fix; returns a verdict per applicable lesson. Use before pushing or before moving a PR to review.
argument-hint: "[base, default: integration branch]"
---

# Self-review against the lessons

1. Diff: `git diff origin/<base>...HEAD`, where `<base>` is "$ARGUMENTS" if given, otherwise the integration branch
   (`.harness/config.json` → `integration_branch`).
2. Tables: `.harness/docs/LESSONS.md` (otherwise `${CLAUDE_PLUGIN_ROOT}/docs/LESSONS.md`) **and** the project's own
   lessons if it has any (e.g. `docs/agents/LESSONS.md`). Keep the relevant scopes: `general`, `docs`, `ci` always;
   `swift`, `ios`, `linux-cloud` depending on the project and the environment.
3. For **each** lesson that applies to the diff, one line: `L..: ✅ followed | ⚠️ to verify | ❌ broken: where
   (file:line) and why`. Do not list unrelated lessons.
4. Concrete checks, not impressions: run the announced tests, show that a new test fails without the change (L01),
   find the caller of a function "called at launch" (L82), reread the modified Markdown tables (L07), check save
   compatibility if a persisted type changes (L80).
5. Fix the ❌ before pushing; unresolved ⚠️ go into "Watch points / not tested" in the PR.

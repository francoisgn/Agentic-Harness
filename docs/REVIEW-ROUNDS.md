# Review rounds (bots, CodeQL, humans)

Source: `docs/agents/REVIEW-ROUNDS.md` of HFRnow, generalised. Skill: `/review-round`.

Each round costs a CI run, a new review and tokens. Do it **once, completely**.

## The two reviews

Two distinct reviews answer two distinct questions from two distinct inputs. They are never blended: the first
checks the change against the **intent**, the second checks the **code** on its own.

| Review | Question | Input | Who | When |
|---|---|---|---|---|
| Adversarial | Does the change do what the issue asks? | Issue intent (spec, error behaviours, definition of done) + diff + LESSONS | A fresh sub-agent of another model than the author, read-only, isolated from the author's context (`adversarial-reviewer`) | Before "Ready for review" |
| Code | Is the code correct and clean? | The diff only | The review service on the PR (CodeRabbit or [the in-house service](REVIEW-SERVICE.md)) | On the ready PR, once per head |

- **Isolation.** An adversarial reviewer that cannot be isolated from the author's context (same session, no
  sub-agent tool) says so and gives **no verdict**: a review in the author's context is not an adversarial review.
- **No review service.** A project without one has the code review done by the AI review workflow or by a human, and
  the PR says which.

## Convergence: a settled finding stays settled

- **One clean round ends the loop**: a round with no finding on the current head is the last one. It stays within the
  bound of 3 cycles ([FINOPS](FINOPS.md) §3); two clean rounds are never required.
- **Settled findings are listed in the PR**, each with its recorded reason (fixed in a commit, or not fixed and why).
  A reviewer that reopens one is answered by pointing to that record: it counts as a new finding only with **new
  evidence** (a new failure path, a changed head, a new input). A security finding is never settled this way: it
  stays open until the maintainer decides.

1. **Read everything first**: inline comments, "Outside diff range", details, the "Prompt for AI agents" block, every
   open thread of the PR.
2. **A finding is a claim to verify, not an order.** Follow a real path (input or caller → failure).
   Real and the fix is proportionate → fix it. Far-fetched, or the fix costs more than the gain → reply in
   its thread with the path followed and why not, and flag it to the maintainer.
   **A security finding stays open until the maintainer decides.**
3. **Fix the class, not the instance**: list the neighbouring cases (other entry points, other parsers or
   queries of the same pattern, reverse order, other limits) and fix them all, one test per case.
4. **Every test is shown failing without the fix** (revert the core of the change, see red) and goes through the real
   entry point. A filtered run must report executed tests (LESSONS L01).
5. **Cross-check before pushing**: a separate agent, isolated from your context, receives the finding, the diff and
   LESSONS.md, **not** the author's conclusion, with the instruction to find what the fix misses or breaks.
   Integrate its findings.
6. **One commit + one push per round**, all findings handled. Never one push per finding.
7. **Then one reply per thread** (fixing commit, or why not), in the same unit of work as the push; a push
   alone is not a reply. Findings outside the diff: a PR comment addressed to the bot. Resolve every handled thread.
8. **Optional findings** (nit, suggestion): never a push for them alone. One-line reply; fold them into the
   next push that touches those files.
9. **After the round**: compare the findings with [LESSONS](LESSONS.md). Already listed = the self-review missed it,
   tighten that step. New kind = new line.

A review bot can skip a review ("Review skipped") or pause on a branch: after the push,
check that it reviewed the **new head**; otherwise ask for `@coderabbitai review` (from a cloud session,
`@mentions` are altered: the operator posts it). The round is complete only when the bot has reviewed the pushed head.

**CI noise or real failure**: a check that fails in a few seconds with no log (missing token, service
unavailable, runner never acquired) is not "CI red": say so and point to the real checks. "Flaky" is
not a cause: one re-run at most, then investigate.

**Ready to merge** = required checks green **and** zero open threads **and** the bot has reviewed the head **and** an
adversarial review APPROVED on that head, with settled findings listed in the PR (and the project's merge policy).

## Traceability: every verdict on the PR

The harness measures the **problem-PR ratio** (at least one finding in adversarial review, AI review, compliance,
CodeRabbit or human review) and the **fix effort** (commits after the first finding, time to merge):
this is the gauge of initial quality and of the cost of the second pass ([FINOPS](FINOPS.md) §4). The measure is only
right if **all** verdicts are visible on the PR, above all the first negative one:
- the author posts **every** adversarial and compliance review verdict as a PR comment, word for word,
  including `CHANGES REQUESTED` / `GAPS` (never only the last `APPROVED`); the first line follows the
  format of its source: `**Adversarial review (<model>): APPROVED | CHANGES REQUESTED** — head <sha>`,
  `**Compliance review <framework> (<model>): COMPLIANT | GAPS | OUT OF SCOPE** — head <sha>`, or
  `**AI review (<model>): …**` for the review service. The dashboard reads it at the start of a line (possibly
  as a `- ` bullet or a numbered `1. ` item); a `>` quote or a table row does not count;
- a review done before the PR is opened is posted as soon as it opens, in order;
- a security finding is traced without detail ("CHANGES REQUESTED — security finding, detail sent
  privately"): it counts, it does not leak;
- never rewrite or delete a past verdict to "clean up" the PR.

A PR merged with no traced verdict is reported separately (🟠) and leaves the ratio.

## Recommended CodeRabbit configuration
Modelled on the two projects (`.coderabbit.yaml`): `language` set to the project's language (`fr-FR` in both),
`auto_review.drafts: false` (no review of drafts, like the CI), `base_branches` = integration and promotion branches,
`path_filters` that exclude generated files (PNG, exported SVG), `path_instructions` that restate the project's rules
per directory (engine without UI, workflows pinned by SHA with minimal permissions, anonymised test data, sourced
docs). Profile `chill` for a solo project, `assertive` when external contributors arrive.

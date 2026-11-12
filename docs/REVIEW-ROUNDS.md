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
- **Review service installed but silent.** If the service posts a skip notice (e.g. CodeRabbit: "does not receive
  automatic reviews") or has not reviewed the current head, the code review falls back to the `review` job
  (`ai-review.yml`) when it is enabled, otherwise to a fresh sub-agent of another model than the author, given the
  diff only. Its verdict uses the `**AI review (<model>): …**` line, and the PR says which fallback was used.
- **The reviewer's model is part of the verdict.** Every reviewer states the model it actually ran on, in its verdict
  line. A session can change model while it runs: an adversarial verdict given on the author's model is traced with
  that model, does not count as the adversarial review, and a reviewer of another model redoes it (LESSONS L84).

## Convergence: a settled finding stays settled

- **One clean round ends the loop**: a round with no finding on the current head is the last one. It stays within the
  bound of 3 cycles ([FINOPS](FINOPS.md) §3); two clean rounds are never required.
- **Re-check after an approval.** When the head moves after an APPROVED, the scope of the re-check follows the delta.
  A **form-only** delta (wording, formatting, links, line wrapping, or nits the reviewer itself asked for) gets a short
  confirmation from the same reviewer, on the delta only, posted as a verdict on the new head with the usual first
  line (`**Adversarial review (<model>): APPROVED** — head <sha>`, or `CHANGES REQUESTED`). Any other delta (code,
  tests, configuration, a sourced fact, anything security-related) gets a full re-review.
- **Settled findings are listed in the PR**, each with its recorded reason and an **outcome tag** at the start of the
  line: `[fixed]` (fixed in a commit, cite it), `[declined: false positive]` (the claim does not hold, say why) or
  `[declined: not worth it]` (real but not worth the change, say why), e.g. `- [fixed] unanchored regex (abc1234)`.
  No colon right after the tag: `[fixed]: …` at the start of a line is a Markdown link definition and disappears
  from the rendered page. The tags make the value of reviews searchable
  later ([FINOPS](FINOPS.md) §5); the harness computes nothing from them. A reviewer that reopens one is answered
  by pointing to that record: it counts as a new finding only with **new evidence** (a new failure path, a changed
  head, a new input). A security finding is never settled this way: it stays open until the maintainer decides.

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
`@mentions` are altered: the operator posts it). The round is complete only when the bot, or its fallback
(§The two reviews), has reviewed the pushed head.

**CI noise or real failure**: a check that fails in a few seconds with no log (missing token, service
unavailable, runner never acquired) is not "CI red": say so and point to the real checks. "Flaky" is
not a cause: one re-run at most, then investigate.

**Ready to merge** = required checks green **and** zero open threads **and** the bot, or its fallback (§The two
reviews), has reviewed the head **and** an
adversarial review APPROVED on that head, with settled findings listed in the PR and every unverified point
verified or accepted (and the project's merge policy).

## CI playbook: red base, stuck run

The dashboard lists the CI health signals ([FINOPS](FINOPS.md) §4); it never cancels, re-runs or deletes. What the
orchestrator does with them:

- **Base red, same failure.** While the integration branch is red on a job, red PRs failing on that same job are not
  re-run: each re-run costs minutes and proves nothing. Fix the base first (its own issue and PR), then re-run or
  update the red PRs one after the other. A re-run that turns green is recorded, never silent: one `type: bug`
  issue per job name (search for an open one first), linked from the PR. "Flaky" is not a cause (LESSONS L47).
- **Run queued with no job.** Seen on 2026-11-11: runs `queued` with zero jobs; cancel and force-cancel answered 409,
  delete was refused. A run `pending` waits for its concurrency group and is not this case. The way out:
  1. Stop retrying the cancel; note the run ids.
  2. Give the PR a real new event: update the branch from the base. Never an empty commit, never a close and reopen.
  3. The review of the previous head holds only if `git show --remerge-diff <merge sha>` prints nothing (the merge
     resolved no conflict and added no edit); otherwise re-review the delta (§Convergence).
  4. Report the run ids, times and 409 answers to GitHub Support. A run can be deleted once it is more than two weeks
     old; the dashboard lists it until then.
- **Per-test durations** (`.xcresult`, JUnit) are the project's: a step of its own CI parses them and fails or writes
  the job summary; the harness does not read result bundles.

What was known on 2026-11-12 (read that day):
- GitHub REST docs, [workflow runs](https://docs.github.com/en/rest/actions/workflow-runs): cancel and force-cancel
  list "409 - Conflict" without saying when; force-cancel: "You should only use this endpoint to cancel a workflow run
  when the workflow run is not responding to" a cancel. Nothing on runs with no job: **not found** in the docs.
- [Deleting a workflow run](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/delete-a-workflow-run):
  "You can delete a workflow run that has been completed, or is more than two weeks old."
- [githubstatus.com history](https://www.githubstatus.com/history), 2026-11-11: "Incident with Webhooks" 20:22–20:26
  UTC ("We are investigating reports of degraded performance for Webhooks"), then from 20:48 UTC "Actions is
  experiencing degraded availability", resolved 21:21 UTC ("The backlog of Actions jobs has been fully processed").
  That the stuck runs come from it is not established.
- Community reports of the same state, none with a public answer from GitHub:
  [discussion 135366](https://github.com/orgs/community/discussions/135366) (since 2024-08, again 2026-08-26:
  force-cancel 409 "Cannot cancel a workflow re-run that has not yet queued."),
  [discussion 196717](https://github.com/orgs/community/discussions/196717) (2026-05 to 2026-11-12: delete 403 "Could
  not delete the workflow run."; settled through a private Support ticket),
  [actions/runner#3872](https://github.com/actions/runner/issues/3872) (open, no GitHub reply).

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
- a claim the reviewer could not check (host blocked, tool missing, page not readable) is listed under
  **Unverified** in the verdict, and the verdict line ends with `· unverified: N`. A verdict whose points are all
  unverified is not APPROVED. Before the merge, each unverified point is either verified by the author (the evidence
  in a PR comment) or accepted by the operator in a PR comment; the dashboard counts the merged PRs whose last
  verdict still carries unverified points;
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

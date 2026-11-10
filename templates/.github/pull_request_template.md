<!-- Title in the style of the previous PRs. PR opened as a draft from the first push, pushed often; "Ready for
     review" when everything is done and reviewed: the expensive CI runs then (CONVENTIONS.md §PR, CI-BUDGET.md §2). -->
<!-- LOT-XXX (only for a lot of the plan) -->
Closes #
<!-- One line per closed issue. Partial work: "Refs #n, left: …". Small fix without an issue: Direct-PR: <reason>. -->
Claim: <!-- identifier of the active /claim of the issue -->

**Problem**:

**Cause**:

**Change** (and why this wide, no wider):

**Tests**:
<!-- Names, what they check, shown failing without the change; commands run; Mac build; not tested / to
     validate on the device (e.g. app not buildable in the Linux container). -->

<!-- Reviews: each verdict (adversarial, compliance) is posted as a comment, the first negative one included
     (REVIEW-ROUNDS.md §Traceability). -->

<!-- Doc impact (CONVENTIONS.md §Ledger): the doc files this change makes untrue, or "none (<reason>)". With a
     ledger (.harness/config.json → ledger.enabled), this line goes in the "### Ledger" section instead, and the
     section holds one block per entry, in the format of the project's script, with the `ledger` label; no
     entry: no block, no label. Never edit the ledger files directly. -->
Docs: <!-- e.g. README.md, docs/USAGE.md — or: none (internal refactor) -->

<!-- Author / reviewer model (must differ), with the identifier of each agent (ORCHESTRATION.md §7): -->
Author model: … (<project>.<orc>.lot.<target>) · reviewer: … (<project>.<orc>.rev.<target>)

# Lessons table

Self-review against this table **before every PR and every review fix** (skill `/lessons-check`). After each review
cycle, compare the findings with the table ([REVIEW-ROUNDS](REVIEW-ROUNDS.md) step 9): already listed = the
self-review missed it, tighten that step; new kind = new row, proposed to the harness by PR if it applies elsewhere,
otherwise kept in the project's own lessons.

**Adding one** (skill `/lesson-propose`): a lesson that holds beyond one project goes up to the harness through a
**"Lesson" issue** on `francoisgn/belayline-agentic-harness` (dedicated form, label `lesson`): scope, lesson in one verifiable
sentence, source at a SHA, counter-example. The harness steward merges it into this table by PR (next number, MINOR
in the CHANGELOG); projects receive it at the next sync.

**Class** (decided by `/lesson-propose`, rule in the harness `SCOPE.md`): **mechanical** = a rule can verify it, so it
becomes a deterministic check (lint rule, hook, CI step, test) filed as an issue and gets no line here; **judgment** =
only a reviewer can tell, so it gets a line here; **one-off** = will not recur, nothing is added. Unclear, or a check
that costs more than the failure it prevents: judgment.

**Scope**: `general` (any project) · `swift` · `ios` · `linux-cloud` (sessions in a Linux container) · `ci` · `docs`.
A project without Swift ignores `swift` and `ios`. Domain lessons (a site's protocol, a financial rule) stay in the
project.

**Sources**: `HFR n` = row n of `docs/agents/LESSONS.md` in HFRnow (branch `dev-swift`); `HFR §11 <date>` =
log of `AGENTS.md` §11 in HFRnow; `field` = practice proven on another, unpublished project (the lesson is
reworded to hold everywhere, without any detail of that project).
The `L..` numbers are stable: a lesson that has become false is struck through, never renumbered.

| # | Scope | Lesson | Source |
|---|---|---|---|
| L01 | general | A test **fails without the change** and cannot pass trivially: prove it (revert the core of the fix, see red, restore). It goes through the real entry point, not only through a helper. A filtered run must report tests that actually ran | HFR 2 ; HFR REVIEW-ROUNDS 4 |
| L02 | general | A test checks the result of **its own action**, not the last notification or the last state (another action may have replaced it) | HFR 13 |
| L03 | general | A pairing or ordering fix covers **both orders and all combinations**, not only the reported case | HFR 9 |
| L04 | general | A guard covers **every path that acts**, not only the most visible one | HFR 11 |
| L05 | general | **Measure** a performance claim before reporting it or fixing it; measure rather than assume (external behaviour, test results) | HFR 10 ; HFR AGENTS §3.9 |
| L06 | general | Every failure path reports something **actionable**; an asynchronous result refreshes the interface | HFR 5 |
| L07 | docs | Escape a `\|` in a code span inside a Markdown table, otherwise the row breaks. markdownlint keeps only the rules that catch a real break (MD051 anchors, MD056 columns) | HFR 20 ; HFR `.markdownlint-cli2.jsonc` |
| L08 | docs | Docs, PR description and specs say **exactly** what the code does; no doc for behaviour that is not shipped | HFR 3 |
| L09 | docs | Tracking docs (plan, spec, ADR, sourced regulation) are updated **in the same commit** as the change | HFR 12 ; field |
| L10 | docs | One file, one role: no new document when an existing one has that role; delete a one-off file (runbook, report) once its result is recorded in the ADR or in the file that owns the topic | HFR AGENTS §2 |
| L11 | general | Every public API added or touched has a one-line doc comment; a comment says **why**, not what | HFR 1 ; HFR AGENTS §4 |
| L12 | general | No needless copy of large data; state the behaviour at the limits (memory, disk, very large volumes) | HFR 4 |
| L13 | general | Identifiers are unique and stay out of other namespaces | HFR 6 |
| L14 | general | All entry points of a feature stay consistent (menu, button, gesture, shortcut, deep link) | HFR 7 |
| L15 | general | No ignored error on files, keychain, permissions; races are considered | HFR 8 |
| L16 | general | After a merge with conflicts, reread the **whole** conflicting file against both its parents | HFR 14 |
| L17 | general | Verify a scripted change by reading the diff line by line, not only through the script's own check | HFR 15 |
| L18 | general | Reread the branch head (SHA) and the state of the checks **just before** publishing a status | HFR 16 ; HFR ORCHESTRATION |
| L19 | general | Before saying "already fixed", "done" or "duplicate": check the current integration branch and the latest comments; a report may be older than the last merge | HFR 46 |
| L20 | general | At every checkpoint, reread reviews, CI and **all** open threads of your PRs: bots post late | HFR 47 |
| L21 | general | A fact about an external system (URL, field, rule, API, protocol) cites its source (official link, `file:line` at a named commit, capture). Nothing guessed: stop and say what to go and fetch | HFR 17 ; HFR AGENTS §3.1 ; field |
| L22 | general | Test data and logs contain no real data (name, cookie, token, private content); committed real data is a security incident | HFR 18 ; HFR AGENTS §3.5 |
| L23 | general | Verify an anonymisation with an **independent** check (other patterns, another parser, a search for the names found in the raw data), before pushing; the list that produced the output never vouches for it. A test isolates one position at a time | HFR 33 ; HFR §11 2026-10-26 |
| L24 | general | A redaction rule decides by **position** (field, cell), never by what the content looks like; a derived form (slug) follows the real transformation of the source, measured on real pairs | HFR 39 |
| L25 | general | A pattern on quoted values takes the quote type into account: a `'` inside a value between `"` stopped two "independent" regexes at the same place | HFR 34 |
| L26 | general | Before starting a lot, check that **all** its inputs exist (captured data **and** reference output); one without the other is not enough | HFR 35 |
| L27 | general | A state that was not captured is a gap to send back to whoever captures, never an excuse to fabricate the data by hand | HFR 36 |
| L28 | general | Read the real data before designing the states: the checklist assumed results, the page showed a form | HFR 38 |
| L29 | general | An oracle computed with a single set of settings hides what that setting changes: exclude those cases explicitly **and** count them on both sides, never silently | HFR 51 |
| L30 | general | Facts the reference did not compute: test the derivable subset differentially, verify the rest on captures, without waiting for a new exporter | HFR 52 |
| L31 | general | A URL extracted from a response and then followed with an authenticated session is checked on scheme **and** host (`http://host:80/` passes a host-only check); only links of its own origin are followed with the session | HFR 37, 43 |
| L32 | general | "Not found" stays distinct from "unreadable": a page where every row fails, or a login wall, raises an error instead of returning an empty list | HFR 44 |
| L33 | general | A header name check (code and tests) trims spaces and lowercases, otherwise `" Cookie"` passes | HFR 32 |
| L34 | general | JSON numbers from other clients are kept as written (lexeme or Decimal), never through `Double`: preserved data round-trips byte for byte | HFR 31 |
| L35 | general | A value read from a response and written back into shared state (token, cookie) is a compare-and-set against what the state held when the request started, in a single actor turn | HFR 55 |
| L36 | general | A network risk test (host, cookie) fails without any network access: it asserts the policy itself, never a local refusal that the tested mutation removes (a mutation sent a real request) | HFR 56 |
| L37 | general | A local mark set by the user (read, deleted, hidden) is cleared only by a load that **started after** it; a reload already in flight brings back the earlier state | HFR 57 |
| L38 | general | Background work (autosave, polling, offline save) goes through the normal code path and never lands in the middle of an interaction | HFR 48 |
| L39 | ios | Code that runs on every render (SwiftUI `body`, scroll or change handlers) skips per-item work on an empty input; the view still shows its empty, loading or error state | HFR 49 |
| L40 | general | A file deletion never follows a symbolic link: validate each component of the path from the root | HFR 29 |
| L41 | docs | Parallel lots that add to the **same section** of a shared doc conflict at every merge: create the common heading first, each lot adds only its own subsection, the orchestrator keeps all the subsections | HFR 42 |
| L42 | general | Stacked PRs that share a generated file are merged in order, with a merge commit, never rebased or forced | HFR 40 |
| L43 | general | Before a structural change: `git fetch --all --prune`, list the branches not merged into the integration branch and decide what happens to each (two sessions had each written an ADR 0010) | HFR §11 2026-10-27 |
| L44 | general | A green CI is not enough to merge: a "UI first" PR compiled, but lost settings and broke existing behaviour. Require a spec, tests, an up-to-date base and a review by someone other than the author | HFR 45 ; HFR ADR 0011 |
| L45 | general | Bot review cycle on a docs-heavy PR: group the fixes, reply to **every** thread and resolve it, merge when the required checks are green and the merge policy allows it | HFR 41 |
| L46 | general | A review bot may skip a review or stop on a branch: check that it reviewed the new head. From a cloud session, posted `@mentions` are altered: the operator posts `@coderabbitai review`, `@dependabot rebase` | HFR REVIEW-ROUNDS ; HFR §11 2026-10-24 |
| L47 | ci | A check that fails in a few seconds with no log (missing token, service unavailable, runner never acquired) is infrastructure, not "red CI". "Flaky" is not a cause: one rerun at most, then investigate | HFR REVIEW-ROUNDS ; HFR EXTERNAL-AGENTS §10 |
| L48 | ci | A macOS minute counts as 10, each job is rounded up to the minute: frequent pushes to a draft where nothing costly runs, full CI on the move to "Ready" or on a label, one commit per review round, Linux jobs grouped, macOS build only if the app changes and after the Linux job is green | field ; HFR §11 2026-11-05 (#477) |
| L49 | ci | A failed change detection still runs the jobs it gates: a broken detector must never let a PR through | field ; HFR `ci.yml` |
| L50 | ci | `issues`, `schedule`, `workflow_dispatch`, `pull_request_target`, issue forms and the Dependabot config work only from the **default branch**: a workflow placed on another branch is inert | HFR §11 2026-10-26 ; HFR ADR 0010 |
| L51 | ci | A preview runner image (e.g. `xcode-27`) exists only through its label: declare it to actionlint (`.github/actionlint.yaml`) and pick the simulator dynamically (a runtime may refuse a device model) | HFR §11 2026-10-24, 2026-10-26 ; field |
| L52 | ci | On a private repository, CodeQL, secret scanning and Dependency Review require GitHub Advanced Security: replace them with Semgrep, Trivy, gitleaks, zizmor, actionlint. A public repository consumes no minutes | field |
| L53 | ci | Actions pinned by full SHA (tag in a comment), minimal `permissions`, `persist-credentials: false`, never a `pull_request_target` that checks out the PR's code, no secret exposed to forks | HFR ADR 0005 ; HFR `.coderabbit.yaml` |
| L54 | ci | Pre-commit hooks never reformat test data (byte for byte); ShellCheck covers every script, a finding is fixed or silenced inline with its reason | HFR CONTRIBUTING §4 |
| L55 | linux-cloud | From a cloud session, read CI job logs with the GitHub MCP tool `get_job_logs` (`gh api …/logs` is blocked: other host); annotations remain the fastest signal | HFR §11 2026-10-25 |
| L56 | linux-cloud | A cloud session cannot change the repository settings (403): the settings live in a versioned file (`.github/repo-settings.json`), changed by PR and applied on merge by the CI with an administration token (ADOPTION §Repository settings) | HFR §11 2026-10-24 |
| L57 | linux-cloud | GitHub apps (Claude, CodeRabbit) on a personal repository can only be installed by its owner, whatever the collaborator's rights | HFR §11 2026-10-26 |
| L58 | linux-cloud | The app (SwiftUI, Charts, StoreKit…) does not compile on Linux: reread its code with a compiler's rigour (types, `@MainActor`, `Sendable` in complete mode, `switch` exhaustiveness, real APIs of the OS version); only the Mac or the macOS CI settles it | field |
| L59 | linux-cloud | Install **the same version** of the toolchain as the Linux CI (script, verified signature) and run the engine tests before any push that touches it | field ; HFR `cloud-setup.sh` |
| L60 | linux-cloud | The CI linter is not necessarily in the container: install it (Linux binary at the CI's version, verified checksum) rather than spend a CI round; otherwise check its blocking rules by hand (line length, complexity, type length, identifiers) | HFR 21, 27 |
| L61 | linux-cloud | After late changes, check `git status` on **tracked** files, not only untracked ones, before pushing | HFR 23 |
| L62 | swift | On Linux, `Date.description` crashes on a non-finite date: no test may print one | HFR 22 |
| L63 | swift | swift-corelibs-foundation ignores `timeoutInterval` and per-task redirect delegates, `URLProtocol` cannot redirect: enforce your own timeouts, test redirects against a local server | HFR 24 |
| L64 | swift | `URL.cachesDirectory` does not exist on Linux and `FileManager.replaceItemAt` fails there: explicit paths and `rename(2)` for an atomic write | HFR 28 |
| L65 | swift | On Linux, `URLSession` carries the cookies it set over to a followed redirect, whatever the new host: refuse redirects outside the allowed hosts | HFR 30 |
| L66 | swift | A test server (socket) is closed in the thread that owns it, otherwise its descriptor may be reused by another | HFR 25 |
| L67 | swift | A Swift Testing test that cancels its own task is "cancelled", neither passed nor failed: drive the cancellation through a child `Task` whose value you await | HFR 50 |
| L68 | swift | A `@Test(arguments:)` of literals joined with `+` can exceed the type checker's limit and fail the whole target: write the literals out in full | HFR 53 |
| L69 | swift | Closures and `do` blocks with typed throws infer `any Error` without an annotation (`() async throws(E) -> T in`, `do throws(E)`) | HFR §11 2026-10-27 (LOT-082) |
| L70 | swift | A static function whose default argument reads a `@MainActor` value becomes `@MainActor`: keep the pure rule `nonisolated` and testable, and the read in a thin overload | HFR §11 2026-10-28 (LOT-119) |
| L71 | swift | Recursive tree APIs crash on deep nesting (512 KB stack): traverse with an explicit stack, build deep trees bottom-up | HFR §11 2026-10-27, 2026-10-28 (LOT-032, LOT-034) |
| L72 | ios | A failing app test makes `xcodebuild test` run `simctl diagnose` for up to 10 min; filter with the full Swift Testing name (`Suite/test()`, without `()` nothing runs) and check that tests actually ran | HFR 54 |
| L73 | ios | `confirmationDialog` clears its presentation state before the action: pass the shown item to the action. A handler that captures its model strongly leaks it: weak capture | HFR §11 2026-11-05 (LOT-087) |
| L74 | ios | Know the project file strategy: synchronised groups (add a file without touching the pbxproj) or XcodeGen **and** pbxproj both versioned (every addition, rename, deletion or setting is carried into both) | HFR ADR 0012 ; field |
| L75 | ios | Agents and CI build without signing (`CODE_SIGNING_ALLOWED=NO`), never `-allowProvisioningUpdates`; a signed build on a device needs the team account in the maintainer's Xcode | HFR §11 2026-10-27 (LOT-080) |
| L76 | ios | Layout by size classes, never by idiom or `UIScreen`; 44 pt targets, VoiceOver labels, Dynamic Type | field |
| L77 | general | A security claim is tested on the real component (hosted web view, network client), not only on the string produced | HFR §11 2026-10-27 (LOT-083) |
| L78 | general | Read captured data as **bytes**: a text-mode read turns CRLF into LF | HFR §11 2026-10-27 (LOT-036) |
| L79 | general | A write is a success only with the server's own confirmation; a write whose request may have left is "unconfirmed", never replayed | HFR §11 2026-10-27, 2026-10-28 (LOT-037, LOT-048, #314) |
| L80 | general | Persistence: a save written by a released version stays readable by all later ones (new field optional or defaulted, tolerant decoding, migration on read) | field |
| L81 | general | Just before opening a PR, look for open PRs that touch the same files or the same topic: coordinate rather than discover the conflict at merge | HFR AGENTS §8 |
| L82 | general | A claim that "X is called at launch" is verified by searching for the caller (`grep`): the function had no caller | HFR §11 2026-10-28 (LOT-119) |

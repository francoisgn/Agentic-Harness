# Cloud Linux and Mac: who does what, how to hand over

Sources: `docs/agents/MAC-SESSIONS.md`, `scripts/cloud-setup.sh`, `AGENTS.md` §10 of HFRnow; practice proven on
other projects (rule "Linux container: engine yes, app no", install script, handoff script on the Mac).

## 1. Division of roles

| Environment | Can | Cannot |
|---|---|---|
| **Cloud session** (Linux container) | Code and docs; engine tests (`swift test` on the package without UI); lint; scripts; issues and PRs | Compile the app (SwiftUI, Charts, StoreKit, UIKit), simulator, device, signing, repository settings |
| **Mac** (CLI coding agent or human) | Xcode, simulator, device, real screenshots, smoke tests, signed build | — (but it is the bottleneck: it only does what requires a Mac) |
| **CI** | Referee: what is not green in CI is not finished | — |

Consequences:
- Keep the engine **free of UI dependencies** (Foundation only) so that it can be tested everywhere.
- In the cloud, review the app code **with a compiler's rigour**: types, `@MainActor`, `Sendable` (Swift 6,
  strict concurrency), exhaustive `switch` statements, real APIs of the targeted OS version. Never write "compiles"
  without having seen it; write "not compiled here, to verify on a Mac" under "Watch points / not tested" in the PR.
- Issues that require the Mac carry `needs: host`; cloud sessions do not touch them.
- **Decouple**: what the Mac discovers and that can be coded elsewhere (engine, docs) becomes an issue **without**
  `needs: host`, so that a cloud session takes it. No Mac ↔ cloud round trip for a small app fix (< ~30 lines): the
  Mac does it.

## 2. Preparing the cloud container
An install script (pasted into the "setup script" of the cloud environment, or run by hand) installs **the same
version** of the toolchain as the Linux CI: official archive, **signature verified** (the project's published keys,
imported block by block if gpg refuses the whole file), then the linter at the CI's version with a verified checksum.
The required hosts (e.g. `download.swift.org`, `github.com`, `release-assets.githubusercontent.com`) go in the
environment's allowed domains. Public example: `scripts/cloud-setup.sh` of HFRnow (Swift 6.2.x + SwiftLint);
install into a fixed folder (e.g. `/opt/swift`) at the version pinned by the CI.

## 3. Handing over to the Mac: the handoff script
A model to write in the project (e.g. `scripts/mac-handoff.sh`). Run on the Mac, without interaction, it:
1. syncs the branch to test (refuses a dirty tree or a diverged local branch: the local head must equal
   `origin/<branch>`);
2. replays the local CI without the app build (`local-check.sh --no-app`);
3. compiles the app for a dynamically chosen simulator, like the CI job (same compilation conditions depending on
   the Xcode version), `CODE_SIGNING_ALLOWED=NO`;
4. **only if the build succeeds** (and unless `--no-smoke`): installs, launches, rotates the device, checks that it
   does not crash, collects the crash logs, takes screenshots;
5. writes `build/handoff/REPORT.md`: header (branch @ SHA, date, macOS, Xcode), results 🟢 / 🟠 / 🔴, compilation
   errors (excerpt), start of the crash log, then the release's **manual checklist**;
   copies it to the clipboard.

The operator pastes `REPORT.md` into the cloud session, which fixes and pushes again. Rule: a single round trip per
lot when possible (fix everything in one go).

## 4. Autonomous Mac sessions
When the Mac works unattended (screenshots, manual checks, Mac lots), its prompt starts with an
**autonomy contract** (model: `MAC-SESSIONS.md` of HFRnow):
- the operator is not watching: **never stop to ask a question**; a needed decision = a short comment on the
  issue concerned, ending with "Decision needed (operator)", then the next item; all skipped items go in the
  final report;
- explicit, bounded pre-authorisations (e.g. writes allowed only between the operator's test accounts);
  everything else is skipped and listed;
- the repository's rules win over the prompt in case of conflict (say so in the report);
- tokens are counted: read only the useful files, filter build logs down to errors and the final status;
- **stop conditions**: empty queue or only blocked items; maximum duration (e.g. 6 h); red CI on the integration
  branch for an outside reason (report it, do not fix it); abnormal response from an external service (403,
  captcha) → all traffic stopped;
- parallelism bounded by the CI budget (at most 2 Mac lots at a time, each in its own worktree and subagent);
- subagent watchdog (30 min without a commit or a comment, or the same command failing 3 times → stop);
- cleanup: worktrees, DerivedData, simulator clones deleted; main checkout clean on the integration branch;
- **final report**: a comment on the orchestrator's tracking issue (done → PR → merged or not, facts learned,
  issues opened, lots unblocked, skipped items and decisions needed, what the next session starts with), and the
  same report in the terminal.

## 5. Checking what the cloud merged without a Mac
When merges were accepted without a Mac check to go fast: a single build at the head of the integration branch, all
the checks in a row, grouped by screen. A check that fails at the head is reproduced at the SHA of the merge it
covers before blaming anyone (otherwise `git bisect` between the two). Serious (crash, data loss, leak) → immediate
revert PR as `priority: critical`, reported at the top of the report.

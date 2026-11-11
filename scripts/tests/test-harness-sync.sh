#!/usr/bin/env bash
# Tests of scripts/harness-sync.sh and of the hooks, on a throwaway consumer repository. No network.
# Usage: scripts/tests/test-harness-sync.sh   (exits 1 at the first failure)
# Checks on files other than the sync script match stable tokens (paths, ids, exit codes), not prose.
# shellcheck disable=SC2015 # "A && B || fail" intended: fail exits the script, it cannot follow a successful B
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SYNC="$ROOT/scripts/harness-sync.sh"
GUARD="$ROOT/plugins/harness/scripts/guard-git.py"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
PASS=0
fail() { printf '✘ %s\n' "$1"; exit 1; }
ok() { PASS=$((PASS + 1)); printf '✔ %s\n' "$1"; }
run() { "$SYNC" --source "$ROOT" --target "$T" "$@" >"$WORK/out" 2>&1; echo $?; }

T="$WORK/project"
mkdir -p "$T/.claude" && git -C "$T" init -q -b develop
printf '# CLAUDE.md\n\nProject rule to keep.\n' >"$T/CLAUDE.md"
printf '{\n  "permissions": { "allow": ["Bash(swift test:*)"] }\n}\n' >"$T/.claude/settings.json"

[ "$(run)" = 0 ] || fail "first sync: $(cat "$WORK/out")"
grep -q 'Project rule to keep.' "$T/CLAUDE.md" || fail "project text lost"
[ "$(grep -cFx '<!-- harness:begin harness -->' "$T/CLAUDE.md")" = 1 ] \
  && [ "$(grep -cFx '<!-- harness:end harness -->' "$T/CLAUDE.md")" = 1 ] || fail "block missing or duplicated"
grep -q '@.harness/docs/ESSENTIALS.md' "$T/CLAUDE.md" || fail "ESSENTIALS import missing"
[ -f "$T/.harness/docs/ESSENTIALS.md" ] && [ ! -e "$T/.harness/docs/ESSENTIEL.md" ] || fail "ESSENTIALS.md not vendored"
[ -f "$T/.harness/docs/LESSONS.md" ] && [ -f "$T/.claude/skills/lot-start/SKILL.md" ] || fail "docs or skills missing"
[ -x "$T/.harness/hooks/guard-git.py" ] || fail "hook not executable"
[ -f "$T/.claude/agents/adversarial-reviewer.md" ] && [ -f "$T/.claude/agents/compliance-gdpr.md" ] || fail "agents missing"
[ -x "$T/scripts/local-check.sh" ] && grep -qF '# >>> steps' "$T/scripts/local-check.sh" || fail "local-check skeleton not seeded executable"
[ -f "$T/.github/ISSUE_TEMPLATE/task.yml" ] && [ ! -e "$T/.github/ISSUE_TEMPLATE/tache.yml" ] || fail "task.yml template"
[ "$(grep -cFx '<!-- harness:begin harness -->' "$T/AGENTS.md")" = 1 ] || fail "AGENTS.md block"
[ -f "$T/.harness/scripts/flow-metrics.py" ] && [ -f "$T/.harness/scripts/compliance-plan.py" ] \
  && cmp -s "$ROOT/LICENSE" "$T/.harness/LICENSE" \
  && [ -f "$T/.harness/scripts/repo-settings.py" ] && [ -f "$T/.github/repo-settings.json" ] \
  && [ -f "$T/.harness/scripts/readme-progress.py" ] && [ -f "$T/.harness/scripts/doc-steward.py" ] || fail "scripts, settings or licence missing"
# The vendored merge gate finds flow-metrics.py next to it (shared verdict parsing)
python3 "$T/.harness/scripts/merge-gate.py" --help >/dev/null 2>&1 || fail "vendored merge-gate.py cannot load flow-metrics.py"
[ -f "$T/.harness/scripts/issue-reconcile.py" ] || fail "issue-reconcile.py not vendored next to readme-progress.py (it imports it)"
[ -f "$T/docs/compliance/TEMPLATE.md" ] && [ -f "$T/.claude/agents/compliance-reviewer.md" ] || fail "spec template or generic reviewer missing"
jq -e '.permissions.allow[0] == "Bash(swift test:*)" and (.hooks.PreToolUse | length) == 1' "$T/.claude/settings.json" >/dev/null \
  || fail "settings.json merge"
# The vendored State script finds decisions-check.py and flow-metrics.py next to it and prints the State without a token (exit 2)
env -u GH_TOKEN -u GITHUB_TOKEN python3 "$T/.harness/scripts/orch-state.py" --root "$T" --print >"$WORK/state" 2>&1
[ $? = 2 ] && grep -qF '<!-- harness:state -->' "$WORK/state" && ! grep -q 'unreadable' "$WORK/state" \
  && grep -qF '<!-- harness:report -->' "$T/.harness/templates/child-report.md" || fail "orch-state.py (decisions-check.py, flow-metrics.py next to it) or child report template"
PIN="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null) # v$(cat "$ROOT/VERSION")"
if [ -n "$(git -C "$ROOT" status --porcelain 2>/dev/null)" ] || ! git -C "$ROOT" rev-parse HEAD >/dev/null 2>&1; then PIN="v$(cat "$ROOT/VERSION")"; fi
[ "$(grep -c "belayline-agentic-harness/.github/workflows/.*@$PIN\$" "$T/.github/workflows/harness.yml")" = 9 ] || fail "refbump ($PIN)"
ok "first sync: block, docs, skills, hooks, JSON merge, refbump"

[ "$(run)" = 0 ] && grep -q 'Up to date' "$WORK/out" || fail "second sync not idempotent: $(cat "$WORK/out")"
[ "$(run --check)" = 0 ] || fail "--check after sync"
ok "idempotence and --check"

# The relay belongs on the default branch: the sync never creates it, but pins the references of a copy kept here.
RELAY_TPL="$ROOT/templates/.github/workflows/harness-relay.yml"
RELAY="$T/.github/workflows/harness-relay.yml"
[ ! -e "$RELAY" ] || fail "the sync must not create the relay"
[ -f "$RELAY_TPL" ] || fail "relay template missing"
REFS="$(grep -c 'belayline-agentic-harness/\.github/workflows/[A-Za-z0-9._-]*@' "$RELAY_TPL")"
[ "$REFS" -ge 2 ] || fail "relay: expected at least two harness references, found $REFS"
sed -E 's|(belayline-agentic-harness/\.github/workflows/[A-Za-z0-9._-]+)@[^ ]+( # v[0-9.]+)?|\1@v0.0.1|' "$RELAY_TPL" >"$RELAY"
[ "$(run)" = 0 ] || fail "sync with a relay copy: $(cat "$WORK/out")"
[ "$(grep -c "belayline-agentic-harness/.github/workflows/.*@$PIN\$" "$RELAY")" = "$REFS" ] || fail "refbump of the relay ($PIN)"
rm -f "$RELAY"
[ "$(run --check)" = 0 ] || fail "--check after removing the relay copy"
ok "relay: never created, references pinned when a copy is kept"

# Security invariants of the relay (CI-BASELINE.md §2): events, permissions, no event data in run:, no persisted token.
EVENTS="$(awk '/^on:/ { on = 1; next } on && /^[^ #]/ { on = 0 } on && /^  [a-z_]+:/ { sub(/^  /, ""); sub(/:.*/, ""); print }' "$RELAY_TPL" | LC_ALL=C sort | tr '\n' ' ')"
[ "$EVENTS" = "issue_comment issues schedule workflow_dispatch " ] || fail "relay events: $EVENTS"
grep -qx 'permissions: {}' "$RELAY_TPL" || fail "relay: top-level permissions must be {}"
[ "$(grep -c 'uses: actions/checkout@' "$RELAY_TPL")" = "$(grep -c 'persist-credentials: false' "$RELAY_TPL")" ] \
  || fail "relay: every checkout needs persist-credentials: false"
grep -E '^ +uses: actions/' "$RELAY_TPL" | grep -vqE '@[0-9a-f]{40} # v' && fail "relay: actions must be pinned by SHA"
awk '/^ +run: /{ r = 1; ind = match($0, /[^ ]/); if ($0 ~ /\$\{\{/) bad = 1; next }
     r && NF && match($0, /[^ ]/) <= ind { r = 0 }
     r && /\$\{\{/ { bad = 1 } END { exit bad }' "$RELAY_TPL" || fail "relay: \${{ }} inside a run: block"
awk '/^ +runs-on:/ { n++ } /^ +timeout-minutes:/ { t++ } END { exit !(n > 0 && n == t) }' "$RELAY_TPL" \
  || fail "relay: every job that runs on a runner needs timeout-minutes"
grep -E '^ +ref:' "$RELAY_TPL" | grep -qvE 'env\.INTEGRATION_BRANCH|needs\.config\.outputs\.branch' \
  && fail "relay: checks out something other than the integration branch"
grep -qE 'head_ref|pull_request\.head|refs/pull' "$RELAY_TPL" && fail "relay: must never reference PR code"
ok "relay: events, permissions, pinning, no event data in run:, no persisted token"

printf '\nText added after the block.\n' >>"$T/CLAUDE.md"
awk '{ print } $0 == "<!-- harness:begin harness -->" { print "LOCAL EDIT INSIDE THE BLOCK" }' "$T/CLAUDE.md" >"$WORK/edited" \
  && cp "$WORK/edited" "$T/CLAUDE.md"
grep -q 'LOCAL EDIT INSIDE THE BLOCK' "$T/CLAUDE.md" || fail "test setup: block not edited"
[ "$(run --check)" = 1 ] || fail "--check must report the drift of an edited block"
[ "$(run)" = 0 ] || fail "block resync"
grep -q 'Text added after the block.' "$T/CLAUDE.md" && ! grep -q 'LOCAL EDIT' "$T/CLAUDE.md" || fail "block not restored or text lost"
ok "block restored, text outside the block preserved"

# Migration: a consumer file that still carries the former block id `cadre` gets its two marker lines rewritten.
cp "$T/CLAUDE.md" "$WORK/claude.current"
sed -e 's/^<!-- harness:begin harness -->$/<!-- harness:begin cadre -->/' -e 's/^<!-- harness:end harness -->$/<!-- harness:end cadre -->/' \
  "$WORK/claude.current" | awk '{ print } $0 == "<!-- harness:begin cadre -->" { print "OLD BLOCK CONTENT" }' >"$T/CLAUDE.md"
[ "$(grep -c 'harness:begin cadre' "$T/CLAUDE.md")" = 1 ] || fail "test setup: former markers not written"
[ "$(run --check)" = 1 ] || fail "--check must report former markers as drift"
[ "$(run)" = 0 ] || fail "sync with former markers: $(cat "$WORK/out")"
cmp -s "$T/CLAUDE.md" "$WORK/claude.current" || fail "former \"cadre\" markers not migrated in place: $(diff "$WORK/claude.current" "$T/CLAUDE.md")"
! grep -q 'cadre -->' "$T/CLAUDE.md" && ! grep -q 'OLD BLOCK CONTENT' "$T/CLAUDE.md" || fail "former markers or content left behind"
[ "$(grep -c 'harness:begin harness' "$T/CLAUDE.md")" = 1 ] || fail "block duplicated by the migration"
[ "$(run --check)" = 0 ] || fail "--check after migration"
ok "former block id \"cadre\" migrated to \"harness\""

echo "local" >>"$T/.harness/docs/LESSONS.md"
[ "$(run --check)" = 3 ] || fail "--check must report the conflict"
[ "$(run)" = 3 ] && tail -1 "$T/.harness/docs/LESSONS.md" | grep -qx local || fail "modified file overwritten without --force"
[ "$(run --force)" = 0 ] && ! grep -qx local "$T/.harness/docs/LESSONS.md" || fail "--force"
ok "local modification detected, kept, --force"

mkdir -p "$T/.claude/skills/review-round" "$WORK/t2"
cp -R "$T/." "$WORK/t2/"
T2="$WORK/t2"; rm -rf "$T2/.harness"; echo "mine" >"$T2/.claude/skills/review-round/SKILL.md"
"$SYNC" --source "$ROOT" --target "$T2" >"$WORK/out" 2>&1; [ $? = 3 ] || fail "pre-existing file outside the harness not reported"
grep -qx 'mine' "$T2/.claude/skills/review-round/SKILL.md" || fail "pre-existing file overwritten"
ok "pre-existing file outside the harness protected"

cat >"$T/.harness/config.json" <<'JSON'
{ "language": "fr", "exclude": [".claude/skills/feedback-triage/*", ".github/ISSUE_TEMPLATE/*"] }
JSON
[ "$(run)" = 0 ] || fail "sync with config: $(cat "$WORK/out")"
[ ! -e "$T/.claude/skills/feedback-triage/SKILL.md" ] || fail "excluded file not removed"
[ -f "$T/.github/ISSUE_TEMPLATE/bug.yml" ] || fail "an excluded seed that was already created stays with the project"
ok "exclusions"

# "language" is the project's language for agents: it no longer selects the harness sources (English only).
cmp -s "$ROOT/docs/ESSENTIALS.md" "$T/.harness/docs/ESSENTIALS.md" || fail "language must not change the vendored docs"
[ "$(run --check)" = 0 ] || fail "--check with a language set"
ok "language does not select the sources"

echo '{ not json' >"$WORK/config.bad" && cp "$T/.harness/config.json" "$WORK/config.good" && cp "$WORK/config.bad" "$T/.harness/config.json"
[ "$(run --check)" = 2 ] || fail "unreadable config.json must be a usage error (2)"
cp "$WORK/config.good" "$T/.harness/config.json"
ok "unreadable config.json refused"

[ "$(run --skip-workflows --skip-seed)" = 0 ] || fail "--skip-workflows"
ok "--skip-workflows / --skip-seed"

# Integration branch vs default branch (GitHub runs issue/schedule/pull_request_target workflows from the default branch only).
SS="$ROOT/plugins/harness/scripts/session-start.sh"
T3="$WORK/dbcheck"
mkdir -p "$T3/.harness" && git -C "$T3" init -q -b develop
printf '{ "integration_branch": "develop" }\n' >"$T3/.harness/config.json"
printf '1.0.0\n' >"$T3/.harness/VERSION"
dbsync() { "$SYNC" --source "$ROOT" --target "$T3" "$@" >"$WORK/out3" 2>&1; echo $?; }
dbhook() { CLAUDE_PROJECT_DIR="$T3" bash "$SS" vendored >"$WORK/hook.out" 2>&1; cat "$WORK/hook.out"; }
nothing_written() { [ ! -e "$T3/.harness/lock" ] && [ ! -e "$T3/CLAUDE.md" ] && [ ! -e "$T3/.claude" ] && [ ! -e "$T3/.github" ]; }
# Undeterminable (no origin/HEAD): "could not check", never "OK", never blocks a first adoption.
dbhook | grep -q 'Could not check' || fail "session-start: undeterminable default branch must say \"could not check\""
BASE_RC="$(dbsync --check)"
[ "$BASE_RC" = 1 ] || fail "first adoption, undeterminable default branch: --check must only report the drift ($BASE_RC)"
grep -q 'Could not check' "$WORK/out3" || fail "sync: undeterminable default branch must say \"could not check\""
# Mismatch on a first adoption (no lock yet): stopped before writing, in every mode, with the two ways out.
git -C "$T3" symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/main
[ "$(dbhook | grep -c '🟠 Integration branch')" = 1 ] || fail "session-start: one warning line on mismatch"
dbhook | grep 'Integration branch' | grep -q '"develop".*"main"' || fail "session-start: warning must name both branches"
dbhook | grep 'Integration branch' | grep -q 'issue_comment' || fail "session-start: warning must name the silent workflows"
[ "$(dbsync)" = 4 ] || fail "first adoption on mismatch must stop with exit code 4: $(cat "$WORK/out3")"
nothing_written || fail "a stopped first adoption must write nothing"
grep -q '"develop".*"main"' "$WORK/out3" && grep -q 'issue_comment' "$WORK/out3" && grep -q 'schedule' "$WORK/out3" \
  || fail "stopped adoption: must name both branches and the events that never run"
grep -q 'default branch' "$WORK/out3" && grep -q 'harness-relay.yml' "$WORK/out3" \
  || fail "stopped adoption: must give both ways out (default branch, relay)"
[ "$(dbsync --dry-run)" = 4 ] && [ "$(dbsync --check)" = 4 ] && nothing_written || fail "--dry-run / --check must stop too"
# Relay already on the default branch: the first adoption goes on, with no warning.
RBLOB="$(git -C "$T3" hash-object -w "$ROOT/templates/.github/workflows/harness-relay.yml")"
RWF="$(printf '100644 blob %s\tharness-relay.yml\n' "$RBLOB" | git -C "$T3" mktree)"
RGH="$(printf '040000 tree %s\tworkflows\n' "$RWF" | git -C "$T3" mktree)"
RROOT="$(printf '040000 tree %s\t.github\n' "$RGH" | git -C "$T3" mktree)"
git -C "$T3" update-ref refs/remotes/origin/main "$(git -C "$T3" -c user.name=t -c user.email=t@t commit-tree "$RROOT" -m relay)"
[ "$(dbsync --check)" = "$BASE_RC" ] || fail "relay on the default branch: adoption must not be stopped: $(cat "$WORK/out3")"
grep -q 'harness-relay.yml' "$WORK/out3" && ! grep -q '🟠 Integration branch' "$WORK/out3" || fail "relay on the default branch: one note, no warning"
git -C "$T3" update-ref -d refs/remotes/origin/main
# Silenced by the project: the first adoption goes on and says once what will not run; later syncs say nothing.
printf '{ "integration_branch": "develop", "default_branch_check": false }\n' >"$T3/.harness/config.json"
[ "$(dbsync)" = 0 ] || fail "default_branch_check false: first adoption must go on: $(cat "$WORK/out3")"
grep -q 'will not run' "$WORK/out3" && grep -q 'issue_comment' "$WORK/out3" || fail "silenced first adoption: must say once what will not run"
[ -f "$T3/.harness/lock" ] || fail "silenced first adoption: lock not written"
! dbhook | grep -qE 'Integration branch|Could not check' || fail "session-start: default_branch_check false must silence"
dbsync --check >/dev/null; ! grep -qE 'Integration branch|Could not check|will not run' "$WORK/out3" || fail "sync: default_branch_check false must silence later syncs"
# Later sync on an adopted project (lock present): a warning that names the relay, exit code unchanged.
printf '{ "integration_branch": "develop" }\n' >"$T3/.harness/config.json"
[ "$(dbsync --check)" = 0 ] || fail "later sync: the warning must not change the exit code: $(cat "$WORK/out3")"
grep -q '🟠 Integration branch "develop"' "$WORK/out3" && grep -q 'harness-relay.yml' "$WORK/out3" || fail "later sync --check: mismatch warning missing"
dbsync --dry-run >/dev/null; grep -q '🟠 Integration branch' "$WORK/out3" || fail "sync --dry-run: mismatch warning missing"
# Match: nothing printed.
git -C "$T3" symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/develop
! dbhook | grep -qE 'Integration branch|Could not check' || fail "session-start: must stay silent when the branches match"
dbsync --check >/dev/null; ! grep -qE 'Integration branch|Could not check' "$WORK/out3" || fail "sync: must stay silent when the branches match"
grep -q 'default_branch' "$ROOT/.github/workflows/pr-hygiene.yml" && grep -q '::warning::\|core.warning' "$ROOT/.github/workflows/pr-hygiene.yml" \
  || fail "pr-hygiene: default branch warning missing"
ok "integration branch vs default branch: first adoption stopped, relay, silenced, later sync warns, match, undeterminable"

# The gap between a project and the harness (#68): the lock records version and commit; with the harness clone at hand,
# --check and the session-start hook say how many commits the project is behind. No network, never misleading.
GAPENV=(GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@example.invalid GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@example.invalid)
H="$WORK/harness-clone"
mkdir -p "$H" && (cd "$ROOT" && git ls-files -z | xargs -0 tar -cf -) | tar -xf - -C "$H"
git -C "$H" init -q -b master && git -C "$H" add -A && env "${GAPENV[@]}" git -C "$H" commit -q -m base
TG="$WORK/gap"
mkdir -p "$TG" && git -C "$TG" init -q -b develop
"$SYNC" --source "$H" --target "$TG" >"$WORK/gap.out" 2>&1 || fail "gap: first sync: $(cat "$WORK/gap.out")"
LOCKED="$(git -C "$H" rev-parse HEAD)"
gapcheck() { "$SYNC" --source "$H" --target "$TG" --check >"$WORK/gap.out" 2>&1; }
gaphook() { HARNESS_CLONE="$H" CLAUDE_PROJECT_DIR="$TG" bash "$SS" vendored >"$WORK/gap.hook" 2>&1; }
gapcheck; grep -qF "vendored $(cat "$H/VERSION") (${LOCKED:0:12})" "$WORK/gap.out" && grep -qF 'same commit' "$WORK/gap.out" \
  || fail "gap: same commit: $(cat "$WORK/gap.out")"
for i in 1 2 3; do env "${GAPENV[@]}" git -C "$H" commit -q --allow-empty -m "later $i"; done
gapcheck; grep -qF "vendored $(cat "$H/VERSION") (${LOCKED:0:12}) · harness now $(cat "$H/VERSION"), 3 commits ahead, see CHANGELOG Actions" "$WORK/gap.out" \
  || fail "gap: --check line: $(cat "$WORK/gap.out")"
gaphook; grep -qF '3 commits ahead' "$WORK/gap.hook" || fail "gap: session-start line: $(cat "$WORK/gap.hook")"
# Clone not available: the hook still shows what is vendored and says it could not compare (nothing else, no network).
HARNESS_CLONE="$WORK/nowhere" CLAUDE_PROJECT_DIR="$TG" bash "$SS" vendored >"$WORK/gap.hook" 2>&1
grep -qF "vendored $(cat "$H/VERSION") (${LOCKED:0:12})" "$WORK/gap.hook" && grep -qF 'could not compare' "$WORK/gap.hook" \
  && ! grep -q 'commits ahead' "$WORK/gap.hook" || fail "gap: hook without clone: $(cat "$WORK/gap.hook")"
# A clone that does not hold the vendored commit (shallow, other history): could not compare, no count.
H2="$WORK/harness-other"
cp -R "$H" "$H2" && rm -rf "$H2/.git" && git -C "$H2" init -q -b master && git -C "$H2" add -A && env "${GAPENV[@]}" git -C "$H2" commit -q -m other
"$SYNC" --source "$H2" --target "$TG" --check >"$WORK/gap.out" 2>&1
grep -qF 'could not compare' "$WORK/gap.out" && ! grep -q 'commits ahead' "$WORK/gap.out" || fail "gap: foreign clone: $(cat "$WORK/gap.out")"
# A source that is not a git clone (copied folder): same.
rm -rf "$H2/.git"
"$SYNC" --source "$H2" --target "$TG" --check >"$WORK/gap.out" 2>&1
grep -qF 'could not compare' "$WORK/gap.out" && ! grep -q 'commits ahead' "$WORK/gap.out" || fail "gap: no git: $(cat "$WORK/gap.out")"
# No lock (first adoption, nothing vendored): no gap line.
TN="$WORK/gap-none" && mkdir -p "$TN" && git -C "$TN" init -q -b develop
"$SYNC" --source "$H" --target "$TN" --check >"$WORK/gap.out" 2>&1
! grep -qE 'commits? ahead|could not compare' "$WORK/gap.out" || fail "gap: line without a lock: $(cat "$WORK/gap.out")"
ok "gap between the project and the harness: --check, session-start, no clone, foreign clone, no lock"

# Hooks
g() { printf '{"tool_input":{"command":%s},"cwd":"%s"}' "$(jq -Rn --arg c "$1" '$c')" "$T" | CLAUDE_PROJECT_DIR="$T" python3 "$GUARD" 2>/dev/null; echo $?; }
[ "$(g 'git push --force origin fix/x')" = 2 ] || fail "guard: force"
[ "$(g 'cd x && git push origin develop')" = 2 ] || fail "guard: protected branch"
[ "$(g 'git push origin HEAD:refs/heads/master')" = 2 ] || fail "guard: protected refspec"
[ "$(g 'git -C . commit -n -m x')" = 2 ] || fail "guard: --no-verify"
[ "$(g 'git push')" = 2 ] || fail "guard: push from current develop"
[ "$(g 'git push -u origin lot/lot-1')" = 0 ] || fail "guard: legitimate push refused"
[ "$(g 'echo git push --force')" = 0 ] || fail "guard: false positive"
ok "guard-git"
# Output captured first: grep -q closing the pipe early would make the hook die of SIGPIPE under pipefail.
CLAUDE_PROJECT_DIR="$T" bash "$SS" vendored >"$WORK/ss.out" 2>&1
grep -qF "$(cat "$ROOT/VERSION") (.harness/VERSION)" "$WORK/ss.out" || fail "session-start"
grep -qF 'python3 .harness/scripts/issue-reconcile.py' "$WORK/ss.out" || fail "session-start: reconcile command not offered"
# A project that vendored the harness without the reconcile script (its own directory: other groups reuse $T3)
NR="$WORK/no-reconcile"; mkdir -p "$NR"; cp -R "$T/.harness" "$NR/.harness"; rm -f "$NR/.harness/scripts/issue-reconcile.py"
CLAUDE_PROJECT_DIR="$NR" bash "$SS" vendored >"$WORK/ss.out" 2>&1
! grep -qF 'issue-reconcile' "$WORK/ss.out" || fail "session-start: reconcile offered while the script is not vendored"
CLAUDE_PROJECT_DIR="$T" bash "$SS" plugin >"$WORK/ss.out" 2>&1
[ ! -s "$WORK/ss.out" ] || fail "session-start plugin should stay silent"
ok "session-start"
printf '🟢 %s test groups passed.\n' "$PASS"

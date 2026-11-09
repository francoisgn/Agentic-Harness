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
[ -f "$T/.github/ISSUE_TEMPLATE/task.yml" ] && [ ! -e "$T/.github/ISSUE_TEMPLATE/tache.yml" ] || fail "task.yml template"
[ "$(grep -cFx '<!-- harness:begin harness -->' "$T/AGENTS.md")" = 1 ] || fail "AGENTS.md block"
[ -f "$T/.harness/scripts/flow-metrics.py" ] && [ -f "$T/.harness/scripts/compliance-plan.py" ] \
  && [ -f "$T/.harness/scripts/repo-settings.py" ] && [ -f "$T/.github/repo-settings.json" ] || fail "scripts or settings missing"
[ -f "$T/docs/compliance/TEMPLATE.md" ] && [ -f "$T/.claude/agents/compliance-reviewer.md" ] || fail "spec template or generic reviewer missing"
jq -e '.permissions.allow[0] == "Bash(swift test:*)" and (.hooks.PreToolUse | length) == 1' "$T/.claude/settings.json" >/dev/null \
  || fail "settings.json merge"
PIN="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null) # v$(cat "$ROOT/VERSION")"
if [ -n "$(git -C "$ROOT" status --porcelain 2>/dev/null)" ] || ! git -C "$ROOT" rev-parse HEAD >/dev/null 2>&1; then PIN="v$(cat "$ROOT/VERSION")"; fi
[ "$(grep -c "agentic-harness/.github/workflows/.*@$PIN\$" "$T/.github/workflows/harness.yml")" = 8 ] || fail "refbump ($PIN)"
ok "first sync: block, docs, skills, hooks, JSON merge, refbump"

[ "$(run)" = 0 ] && grep -q 'Up to date' "$WORK/out" || fail "second sync not idempotent: $(cat "$WORK/out")"
[ "$(run --check)" = 0 ] || fail "--check after sync"
ok "idempotence and --check"

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

# Hooks
g() { printf '{"tool_input":{"command":%s},"cwd":"%s"}' "$(jq -Rn --arg c "$1" '$c')" "$T" | CLAUDE_PROJECT_DIR="$T" python3 "$GUARD" 2>/dev/null; echo $?; }
[ "$(g 'git push --force origin claude/x')" = 2 ] || fail "guard: force"
[ "$(g 'cd x && git push origin develop')" = 2 ] || fail "guard: protected branch"
[ "$(g 'git push origin HEAD:refs/heads/master')" = 2 ] || fail "guard: protected refspec"
[ "$(g 'git -C . commit -n -m x')" = 2 ] || fail "guard: --no-verify"
[ "$(g 'git push')" = 2 ] || fail "guard: push from current develop"
[ "$(g 'git push -u origin claude/lot-1')" = 0 ] || fail "guard: legitimate push refused"
[ "$(g 'echo git push --force')" = 0 ] || fail "guard: false positive"
ok "guard-git"
CLAUDE_PROJECT_DIR="$T" bash "$ROOT/plugins/harness/scripts/session-start.sh" vendored | grep -qF "$(cat "$ROOT/VERSION") (.harness/VERSION)" || fail "session-start"
CLAUDE_PROJECT_DIR="$T" bash "$ROOT/plugins/harness/scripts/session-start.sh" plugin | grep -q . && fail "session-start plugin should stay silent"
ok "session-start"
printf '🟢 %s test groups passed.\n' "$PASS"

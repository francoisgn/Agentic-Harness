#!/usr/bin/env bash
# SessionStart hook of the Belayline harness: a few lines of context added at the start of each session.
# Usage: session-start.sh plugin|vendored
#   plugin    run by the Claude Code plugin (version in ${CLAUDE_PLUGIN_ROOT});
#   vendored  run by the vendored copy in .harness/hooks/ (declared in .claude/settings.json).
# If the project has both, only the vendored copy speaks (no duplicate).
# Read-only; never blocks the session (always exit 0).
set -u
MODE="${1:-vendored}"
PROJECT="${CLAUDE_PROJECT_DIR:-$PWD}"
VENDORED=""
[ -f "$PROJECT/.harness/VERSION" ] && VENDORED="$(head -1 "$PROJECT/.harness/VERSION")"

if [ "$MODE" = plugin ] && [ -n "$VENDORED" ] \
  && grep -q 'harness/hooks/session-start.sh' "$PROJECT/.claude/settings.json" 2>/dev/null; then
  exit 0
fi

PLUGIN=""
if [ "$MODE" = plugin ] && [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  PLUGIN="$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
    "$CLAUDE_PLUGIN_ROOT/.claude-plugin/plugin.json" 2>/dev/null | head -1)"
fi
BRANCH="$(git -C "$PROJECT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"

# Warns (never blocks) when "integration_branch" in .harness/config.json is not the repository's default branch:
# GitHub runs issues, issue_comment, pull_request_target and schedule workflows from the default branch only.
# "default_branch_check": false in the config silences it. Default branch unknown: says so, never "OK".
default_branch_alert() {
  local cfg="$1/.harness/config.json" integ ref def
  [ -f "$cfg" ] && command -v python3 >/dev/null 2>&1 || return 0
  integ="$(python3 -c '
import json, sys
try:
    c = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    sys.exit(0)
if isinstance(c, dict) and c.get("default_branch_check") is not False and isinstance(c.get("integration_branch"), str):
    print(c["integration_branch"])
' "$cfg" 2>/dev/null)" || return 0
  [ -n "$integ" ] || return 0
  ref="$(git -C "$1" symbolic-ref -q refs/remotes/origin/HEAD 2>/dev/null)" || ref=""
  def="${ref#refs/remotes/origin/}"
  if [ -z "$def" ]; then
    echo "- 🟠 Could not check whether the integration branch \"$integ\" is the repository's default branch (no origin/HEAD: run \`git remote set-head origin -a\`)."
  elif [ "$def" != "$integ" ]; then
    echo "- 🟠 Integration branch \"$integ\" is not the default branch \"$def\": GitHub runs issues, issue_comment, pull_request_target and schedule workflows from the default branch only, so label hygiene, claims, the dashboard and the weekly jobs stay silent (to silence: \"default_branch_check\": false in .harness/config.json)."
  fi
  return 0
}

# How far the project is behind the harness (#68), from the version and commit in .harness/lock and a local clone of the
# harness: $HARNESS_CLONE, a sibling ../belayline (docs/ADOPTION.md), or the plugin's own checkout. Offline: reads the
# clone's history, never fetches. No clone, or one that lacks the vendored commit: says it could not compare.
# The counting twin is gap_report in scripts/harness-sync.sh (--check).
gap_alert() {
  local lock="$1/.harness/lock" lv lc clone c now head n what lead
  [ -f "$lock" ] || return 0
  lv="$(awk -F'\t' '$1 == "version" { print $2; exit }' "$lock")"
  lc="$(awk -F'\t' '$1 == "commit" { print $2; exit }' "$lock")"
  lc="${lc%-modified}"
  lead="vendored ${lv:-?} (${lc:0:12})"
  if [ -z "$lc" ] || [ "$lc" = unknown ]; then
    echo "- 🟠 vendored ${lv:-?} (commit unknown): could not compare with the harness."
    return 0
  fi
  clone=""
  for c in "${HARNESS_CLONE:-}" "$1/../belayline" "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/../..}"; do
    [ -n "$c" ] && [ -f "$c/harness.manifest" ] && [ -f "$c/VERSION" ] \
      && git -C "$c" rev-parse --git-dir >/dev/null 2>&1 && { clone="$c"; break; }
  done
  if [ -z "$clone" ]; then
    echo "- 🟠 $lead · harness clone not available here: could not compare (set HARNESS_CLONE to a clone of the harness)."
    return 0
  fi
  now="$(head -1 "$clone/VERSION" | tr -d '[:space:]')"
  head="$(git -C "$clone" rev-parse HEAD 2>/dev/null)" || head=""
  if [ -z "$head" ] || ! git -C "$clone" cat-file -e "$lc^{commit}" 2>/dev/null; then
    echo "- 🟠 $lead · harness now $now: could not compare (the clone does not hold that commit: shallow or other history)."
  elif [ "$lc" = "$head" ]; then
    echo "- 🟢 $lead · harness now $now, same commit."
  else
    n="$(git -C "$clone" rev-list --count "$lc..$head" 2>/dev/null)" || n=""
    case "$n" in
      ''|*[!0-9]*|0) echo "- 🟠 $lead · harness now $now: could not compare." ;;
      *) what="commits"; [ "$n" = 1 ] && what="commit"
         echo "- 🟠 $lead · harness now $now, $n $what ahead, see CHANGELOG Actions." ;;
    esac
  fi
  return 0
}

echo "## Belayline"
if [ -n "$VENDORED" ]; then
  echo "- Vendored version: ${VENDORED} (.harness/VERSION)${PLUGIN:+; plugin: ${PLUGIN}}. Rules: .harness/docs/ESSENTIALS.md."
  if [ -n "$PLUGIN" ] && [ "$PLUGIN" != "$VENDORED" ]; then
    echo "- 🟠 Plugin and vendored copy differ: the copy in the repository is authoritative (update: skill harness-update)."
  fi
  gap_alert "$PROJECT"
else
  echo "- Plugin ${PLUGIN:-?}; this repository has not adopted the harness (.harness/ missing): see the harness's docs/ADOPTION.md."
fi
echo "- Current branch: ${BRANCH}. Work = an issue claimed with \`/claim <id>\`, a <type>/<short-name> branch (lot, fix, feat, chore, docs) from the up-to-date integration branch."
if [ "${CLAUDE_CODE_REMOTE:-}" = "true" ]; then
  echo "- Cloud session (Linux): no Xcode build here; reread app code with compiler-level rigour, handoff to the Mac (MAC-HANDOFF.md)."
fi
default_branch_alert "$PROJECT"
echo "- Push early and often to a draft PR (no costly CI); \"Ready\" after self-review (LESSONS.md) and review by another model; then one commit per review round."
exit 0

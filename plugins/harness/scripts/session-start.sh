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

echo "## Belayline"
if [ -n "$VENDORED" ]; then
  echo "- Vendored version: ${VENDORED} (.harness/VERSION)${PLUGIN:+; plugin: ${PLUGIN}}. Rules: .harness/docs/ESSENTIALS.md."
  if [ -n "$PLUGIN" ] && [ "$PLUGIN" != "$VENDORED" ]; then
    echo "- 🟠 Plugin and vendored copy differ: the copy in the repository is authoritative (update: skill harness-update)."
  fi
else
  echo "- Plugin ${PLUGIN:-?}; this repository has not adopted the harness (.harness/ missing): see the harness's docs/ADOPTION.md."
fi
echo "- Current branch: ${BRANCH}. Work = an issue claimed with \`/claim <id>\`, a <type>/<short-name> branch (lot, fix, feat, chore, docs) from the up-to-date integration branch."
if [ "${CLAUDE_CODE_REMOTE:-}" = "true" ]; then
  echo "- Cloud session (Linux): no Xcode build here; reread app code with compiler-level rigour, handoff to the Mac (MAC-HANDOFF.md)."
fi
default_branch_alert "$PROJECT"
# Offered only (no network call from the hook): an orchestrator runs it to bring the status labels in line with the facts.
if [ -f "$PROJECT/.harness/scripts/issue-reconcile.py" ]; then
  echo "- Orchestrator: bring the \`status:\` labels in line with issues, PRs and claims: \`python3 .harness/scripts/issue-reconcile.py\` (dry run; \`--apply\` to change; ORCHESTRATION.md §1)."
fi
echo "- Push early and often to a draft PR (no costly CI); \"Ready\" after self-review (LESSONS.md) and review by another model; then one commit per review round."
exit 0

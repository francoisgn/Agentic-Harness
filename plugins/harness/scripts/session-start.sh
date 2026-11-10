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
echo "- Push early and often to a draft PR (no costly CI); \"Ready\" after self-review (LESSONS.md) and review by another model; then one commit per review round."
exit 0

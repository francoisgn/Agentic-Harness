#!/usr/bin/env bash
# Tests de scripts/harness-sync.sh et des hooks, sur un dépôt consommateur jetable. Sans réseau.
# Usage : scripts/tests/test-harness-sync.sh   (sort en 1 au premier échec)
# shellcheck disable=SC2015 # « A && B || fail » voulu : fail sort du script, il ne peut pas suivre un B réussi
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

T="$WORK/projet"
mkdir -p "$T/.claude" && git -C "$T" init -q -b develop
printf '# CLAUDE.md\n\nRègle du projet à garder.\n' >"$T/CLAUDE.md"
printf '{\n  "permissions": { "allow": ["Bash(swift test:*)"] }\n}\n' >"$T/.claude/settings.json"

[ "$(run)" = 0 ] || fail "première synchro"
grep -q 'Règle du projet à garder.' "$T/CLAUDE.md" || fail "texte du projet perdu"
[ "$(grep -c 'harness:begin cadre' "$T/CLAUDE.md")" = 1 ] || fail "bloc absent ou en double"
grep -q '@.harness/docs/ESSENTIEL.md' "$T/CLAUDE.md" || fail "import d'ESSENTIEL absent"
[ -f "$T/.harness/docs/LESSONS.md" ] && [ -f "$T/.claude/skills/lot-start/SKILL.md" ] || fail "docs ou skills absents"
[ -x "$T/.harness/hooks/guard-git.py" ] || fail "hook non exécutable"
[ -f "$T/.claude/agents/adversarial-reviewer.md" ] && [ -f "$T/.claude/agents/compliance-gdpr.md" ] || fail "agents absents"
[ -f "$T/.harness/scripts/flow-metrics.py" ] || fail "script du tableau de bord absent"
jq -e '.permissions.allow[0] == "Bash(swift test:*)" and (.hooks.PreToolUse | length) == 1' "$T/.claude/settings.json" >/dev/null \
  || fail "fusion de settings.json"
PIN="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null) # v$(cat "$ROOT/VERSION")"
if [ -n "$(git -C "$ROOT" status --porcelain 2>/dev/null)" ] || ! git -C "$ROOT" rev-parse HEAD >/dev/null 2>&1; then PIN="v$(cat "$ROOT/VERSION")"; fi
[ "$(grep -c "agentic-harness/.github/workflows/.*@$PIN\$" "$T/.github/workflows/harness.yml")" = 7 ] || fail "refbump ($PIN)"
ok "première synchro : bloc, docs, skills, hooks, fusion JSON, refbump"

[ "$(run)" = 0 ] && grep -q 'À jour' "$WORK/out" || fail "deuxième synchro non idempotente : $(cat "$WORK/out")"
[ "$(run --check)" = 0 ] || fail "--check après synchro"
ok "idempotence et --check"

printf '\nTexte ajouté après le bloc.\n' >>"$T/CLAUDE.md"
sed -i.bak 's/^## Cadre commun.*/## Cadre commun MODIFIÉ/' "$T/CLAUDE.md" && rm -f "$T/CLAUDE.md.bak"
[ "$(run)" = 0 ] || fail "resynchro du bloc"
grep -q 'Texte ajouté après le bloc.' "$T/CLAUDE.md" && ! grep -q 'MODIFIÉ' "$T/CLAUDE.md" || fail "bloc non restauré ou texte perdu"
ok "bloc restauré, texte hors bloc préservé"

echo "local" >>"$T/.harness/docs/LESSONS.md"
[ "$(run --check)" = 3 ] || fail "--check doit signaler le conflit"
[ "$(run)" = 3 ] && tail -1 "$T/.harness/docs/LESSONS.md" | grep -qx local || fail "fichier modifié écrasé sans --force"
[ "$(run --force)" = 0 ] && ! grep -qx local "$T/.harness/docs/LESSONS.md" || fail "--force"
ok "modification locale détectée, conservée, --force"

mkdir -p "$T/.claude/skills/review-round" "$WORK/t2"
cp -R "$T/." "$WORK/t2/"
T2="$WORK/t2"; rm -rf "$T2/.harness"; echo "à moi" >"$T2/.claude/skills/review-round/SKILL.md"
"$SYNC" --source "$ROOT" --target "$T2" >"$WORK/out" 2>&1; [ $? = 3 ] || fail "fichier préexistant hors cadre non signalé"
grep -qx 'à moi' "$T2/.claude/skills/review-round/SKILL.md" || fail "fichier préexistant écrasé"
ok "fichier préexistant hors cadre protégé"

cat >"$T/.harness/config.json" <<'JSON'
{ "language": "en", "exclude": [".claude/skills/feedback-triage/*", ".github/ISSUE_TEMPLATE/*"] }
JSON
[ "$(run)" = 0 ] || fail "synchro avec config : $(cat "$WORK/out")"
[ ! -e "$T/.claude/skills/feedback-triage/SKILL.md" ] || fail "fichier exclu non retiré"
grep -q 'Framework essentials' "$T/.harness/docs/ESSENTIEL.md" && grep -q 'Shared framework' "$T/CLAUDE.md" || fail "langue en"
grep -q 'Méthode' "$T/.harness/docs/METHODOLOGY.md" || fail "repli français"
[ -f "$T/.github/ISSUE_TEMPLATE/bug.yml" ] || fail "un seed exclu déjà créé reste au projet"
ok "langue en (avec repli français) et exclusions"

[ "$(run --skip-workflows --skip-seed)" = 0 ] || fail "--skip-workflows"
ok "--skip-workflows / --skip-seed"

# Hooks
g() { printf '{"tool_input":{"command":%s},"cwd":"%s"}' "$(jq -Rn --arg c "$1" '$c')" "$T" | CLAUDE_PROJECT_DIR="$T" python3 "$GUARD" 2>/dev/null; echo $?; }
[ "$(g 'git push --force origin claude/x')" = 2 ] || fail "guard : force"
[ "$(g 'cd x && git push origin develop')" = 2 ] || fail "guard : branche protégée"
[ "$(g 'git push origin HEAD:refs/heads/master')" = 2 ] || fail "guard : refspec protégée"
[ "$(g 'git -C . commit -n -m x')" = 2 ] || fail "guard : --no-verify"
[ "$(g 'git push')" = 2 ] || fail "guard : push depuis develop courant"
[ "$(g 'git push -u origin claude/lot-1')" = 0 ] || fail "guard : push légitime refusé"
[ "$(g 'echo git push --force')" = 0 ] || fail "guard : faux positif"
ok "guard-git"
CLAUDE_PROJECT_DIR="$T" bash "$ROOT/plugins/harness/scripts/session-start.sh" vendored | grep -q 'Version vendorisée' || fail "session-start"
CLAUDE_PROJECT_DIR="$T" bash "$ROOT/plugins/harness/scripts/session-start.sh" plugin | grep -q . && fail "session-start plugin devrait se taire"
ok "session-start"
printf '🟢 %s groupes de tests réussis.\n' "$PASS"

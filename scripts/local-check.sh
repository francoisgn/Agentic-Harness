#!/usr/bin/env bash
# Local check: runs what CI runs, before every push (Belayline harness, CI-BASELINE.md §3, skill /local-check).
# Usage: scripts/local-check.sh [--quick | --full]
#   --full   (default) every step, as CI runs them
#   --quick  only the steps whose paths changed against the integration branch (LOCAL_CHECK_BASE, otherwise
#            origin/HEAD, origin/main or origin/master); with no base found, every step runs
# Ends with a summary: what ran, what was skipped and why, then "Result: OK | FAILED | INCOMPLETE".
# Exit codes: 0 OK; 1 FAILED (a step failed); 2 INCOMPLETE (a step could not run: missing tool, other host, or no
# step declared; never reported as green); 64 usage error.
# Never pushes, needs no secret; writes nothing outside the repository but the tools' own caches.
#
# The steps live between the "steps" markers, one per CI step, with the CI step's name and command:
#   step "<CI step name>" "<tools>" "<paths>" <<'CMD'
#   <the command, as in the workflow's run:>
#   CMD
# <tools>: commands that must exist (`docker` also needs a running daemon); `os:<uname -s>` (os:Darwin) limits the
#          step to that host, it is skipped elsewhere and the result is INCOMPLETE.
# <paths>: space-separated globs of the files the step checks, used by --quick ("" = the step always runs).
set -uo pipefail

usage() { printf 'usage: %s [--quick | --full]\n' "$0" >&2; exit 64; }
MODE=full
[ $# -le 1 ] || usage
case "${1:-}" in
  "" | --full) ;;
  --quick) MODE=quick ;;
  -h | --help) sed -n '2,/^set /p' "$0" | sed '$d; s/^# \{0,1\}//'; exit 0 ;;
  *) usage ;;
esac
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "local-check: not inside a git repository" >&2; exit 64; }
cd "$ROOT" || exit 64

LINES=()
MISSING=()
COUNT=0
FAILED=0
INCOMPLETE=0
NOTE=""
CHANGED=""
if [ "$MODE" = quick ]; then
  BASE="${LOCAL_CHECK_BASE:-}"
  if [ -z "$BASE" ]; then
    for ref in "$(git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null)" origin/main origin/master; do
      if [ -n "$ref" ] && git rev-parse -q --verify "$ref^{commit}" >/dev/null; then BASE="$ref"; break; fi
    done
  fi
  if [ -n "$BASE" ] && MERGE_BASE="$(git merge-base "$BASE" HEAD 2>/dev/null)"; then
    # Committed, staged and unstaged changes since the merge base, plus untracked files
    CHANGED="$({ git diff --name-only "$MERGE_BASE"; git ls-files --others --exclude-standard; } | sort -u)"
    NOTE="quick: changes since $BASE"
  else
    NOTE="quick: no base branch found (set LOCAL_CHECK_BASE), every step runs"
    MODE=full
  fi
fi

record() { LINES+=("$(printf '  %-9s %s' "$1" "$2")"); }

# Does a changed file match one of the globs of $1?
# shellcheck disable=SC2329 # called by step
touches() {
  local pats pat file
  read -ra pats <<<"$1"
  for pat in ${pats[@]+"${pats[@]}"}; do
    while IFS= read -r file; do
      # shellcheck disable=SC2053 # $pat is a glob on purpose
      [[ -n $file && $file == $pat ]] && return 0
    done <<<"$CHANGED"
  done
  return 1
}

# shellcheck disable=SC2329 # called from the steps region, empty in the skeleton
step() {
  local name="$1" tools="$2" paths="$3" cmd tool host="" list missing=() rc
  cmd="$(cat)"
  COUNT=$((COUNT + 1))
  if [ "$MODE" = quick ] && [ -n "$paths" ] && ! touches "$paths"; then
    record skipped "$name (quick: no change in $paths)"
    return 0
  fi
  read -ra list <<<"$tools"
  for tool in ${list[@]+"${list[@]}"}; do
    case "$tool" in
      os:*) [ "$(uname -s)" = "${tool#os:}" ] || host="${tool#os:}" ;;
      docker)
        if ! command -v docker >/dev/null 2>&1; then missing+=(docker)
        elif ! docker info >/dev/null 2>&1; then missing+=("docker daemon"); fi ;;
      *) command -v "$tool" >/dev/null 2>&1 || missing+=("$tool") ;;
    esac
  done
  if [ -n "$host" ]; then
    INCOMPLETE=1
    record skipped "$name (needs a $host host, this one is $(uname -s))"
    return 0
  fi
  if [ ${#missing[@]} -gt 0 ]; then
    INCOMPLETE=1
    MISSING+=("${missing[@]}")
    record missing "$name (tool not found: ${missing[*]})"
    return 0
  fi
  printf '\n==> %s\n' "$name"
  bash --noprofile --norc -e -c "$cmd"
  rc=$?
  if [ "$rc" = 0 ]; then record ok "$name"; else FAILED=1; record FAILED "$name (exit $rc)"; fi
}

finish() {
  if [ "$COUNT" = 0 ]; then
    INCOMPLETE=1
    record missing "no step declared: fill in the steps region of $0 (skill /local-check)"
  fi
  printf '\n== local-check summary (%s) ==\n' "$MODE"
  [ -z "$NOTE" ] || printf '  %s\n' "$NOTE"
  printf '%s\n' ${LINES[@]+"${LINES[@]}"}
  if [ "$FAILED" = 1 ]; then
    echo "Result: FAILED"
    exit 1
  elif [ "$INCOMPLETE" = 1 ]; then
    if [ ${#MISSING[@]} -gt 0 ]; then
      echo "Result: INCOMPLETE (missing: $(printf '%s\n' "${MISSING[@]}" | sort -u | paste -sd, - | sed 's/,/, /g'))"
    else
      echo "Result: INCOMPLETE (steps not run, see above)"
    fi
    exit 2
  fi
  echo "Result: OK"
  exit 0
}

# >>> steps
# The steps of .github/workflows/ci.yml, same names, same commands, same order (scripts/tests/test_local_check.py
# fails on any drift). gitleaks scans the commits of the branch, like on a PR.
BASE_SHA="${BASE_SHA:-$(git merge-base origin/master HEAD 2>/dev/null || true)}"
export BASE_SHA

step "Harness consistency (skills, agents, manifest, labels, naming)" "python3" "" <<'CMD'
python3 scripts/check-framework.py
CMD
step "Python tests (flow-metrics, checks)" "python3" "" <<'CMD'
python3 -m unittest discover -s scripts/tests -p 'test_*.py' -v
CMD
step "Diagrams up to date with their sources (docs/diagrams)" "python3" "docs/diagrams/* templates/docs/diagrams/* scripts/diagrams/*" <<'CMD'
python3 scripts/diagrams/render.py --check && python3 scripts/diagrams/render.py --check --dir templates/docs/diagrams
CMD
step "Harness README meets the standard it asks for (README-STANDARD.md)" "python3" "README.md docs/* scripts/readme-check.py" <<'CMD'
python3 scripts/readme-check.py
CMD
step "ShellCheck" "shellcheck" "*.sh" <<'CMD'
shellcheck scripts/*.sh scripts/tests/*.sh plugins/harness/scripts/*.sh templates/scripts/*.sh
CMD
step "Python (hook syntax)" "python3" "*.py" <<'CMD'
python3 -m py_compile plugins/harness/scripts/guard-git.py scripts/*.py scripts/diagrams/*.py
CMD
step "Valid JSON and consistent versions" "git jq" "*.json VERSION CHANGELOG.md" <<'CMD'
for f in $(git ls-files '*.json'); do jq empty "$f" || exit 1; done
V=$(cat VERSION); P=$(jq -r .version plugins/harness/.claude-plugin/plugin.json)
[ "$V" = "$P" ] || { echo "::error::VERSION ($V) ≠ plugin.json ($P)"; exit 1; }
grep -q "^## $V " CHANGELOG.md || { echo "::error::CHANGELOG.md has no section $V"; exit 1; }
CMD
step "Tests of harness-sync.sh and the hooks" "git jq python3" "" <<'CMD'
scripts/tests/test-harness-sync.sh
CMD
step "Workflows · actionlint" "docker" ".github/workflows/* templates/.github/workflows/*" <<'CMD'
docker run --rm -v "$PWD":/repo -w /repo rhysd/actionlint:1.7.7 -color
CMD
step "Workflows · zizmor" "pipx" ".github/workflows/*" <<'CMD'
pipx run zizmor==1.31.1 --offline --min-severity low .github/workflows
CMD
step "Markdown (tables, anchors)" "npx" "*.md .markdownlint-cli2.jsonc" <<'CMD'
npx --yes markdownlint-cli2@0.18.1
CMD
step "Markdown · relative links and cross-file anchors" "python3" "*.md scripts/doc-links.py" <<'CMD'
python3 scripts/doc-links.py
CMD
step "Secrets · gitleaks" "git docker" "" <<'CMD'
if [ -n "$BASE_SHA" ]; then LOG_OPTS="$BASE_SHA..HEAD"; else LOG_OPTS=--all; fi
docker run --rm -v "$PWD":/repo ghcr.io/gitleaks/gitleaks:v8.30.1 \
  git /repo --log-opts="$LOG_OPTS" --redact --no-banner --exit-code 1
CMD
# <<< steps

finish

#!/usr/bin/env bash
# Vendors the Belayline harness into a consumer repository, at a given version (docs/ADOPTION.md).
#
# Usage: harness-sync.sh [--source DIR | --ref vX.Y.Z] [--target DIR] [--check | --dry-run] [--force]
#                        [--skip-workflows] [--skip-seed]
#   --source DIR       copy of the harness to vendor (default: the repository that contains this script)
#   --ref vX.Y.Z       clones the harness at this tag ($HARNESS_URL, default https://github.com/$HARNESS_REPO.git)
#   --target DIR       root of the consumer repository (default: current directory)
#   --check            writes nothing; exits 1 if a sync would change something (drift check in CI)
#   --dry-run          writes nothing; lists what would change
#   --force            also replaces harness files that were modified locally or already exist
#   --skip-workflows   touches nothing under .github/workflows/ (a GITHUB_TOKEN cannot push these files)
#   --skip-seed        does not create the project templates (seed mode), for example in an automatic sync
#
# What each manifest mode does: see the top of harness.manifest. The script is idempotent: run again at the same
# version, it changes nothing. It records the version in .harness/VERSION and, in .harness/lock, the harness commit
# and the SHA-256 digest of every file owned by the harness. This lets it recognise a local modification (never
# overwritten without --force) and cleanly delete a file removed from the harness.
# Project settings read from <target>/.harness/config.json (create it BEFORE the first sync for them to count):
#   "exclude": ["pattern", ...]   destinations not to vendor (glob on the relative path, `*` crosses `/`);
#                                 an excluded file that is already vendored and unmodified is removed.
#   "integration_branch": "b"     if b is not the default branch (GitHub runs issue and schedule workflows from the
#                                 default branch only): a FIRST adoption (no lock yet) stops before writing (exit 4),
#                                 unless .github/workflows/harness-relay.yml is on the default branch; later syncs warn;
#   "default_branch_check": false never stops nor warns (says once, at adoption, what will not run).
# ("language" in that file is the project's language for agents; it does not select the harness sources.)
# Migration: a managed block still marked with the former id `cadre` gets its two marker lines rewritten to `harness`.
# Exit codes: 0 = ok; 1 = --check found drift; 2 = usage or error; 3 = conflicts (files left as they are);
# 4 = first adoption stopped, nothing written: the integration branch is not the default branch.
# Bash 3.2 compatible (macOS); python3 only for the jsonmerge mode and to read .harness/config.json.
set -euo pipefail

HARNESS_REPO="${HARNESS_REPO:-francoisgn/belayline-agentic-harness}"
HARNESS_URL="${HARNESS_URL:-https://github.com/${HARNESS_REPO}.git}"
SRC="" REF="" TARGET="." MODE=apply FORCE=0 SKIP_WF=0 SKIP_SEED=0

die() { printf 'harness-sync: %s\n' "$1" >&2; exit 2; }
while [ $# -gt 0 ]; do
  case "$1" in
    --source) SRC="${2:?--source expects a directory}"; shift ;;
    --ref) REF="${2:?--ref expects a tag}"; shift ;;
    --target) TARGET="${2:?--target expects a directory}"; shift ;;
    --check) MODE=check ;;
    --dry-run) MODE=dry-run ;;
    --force) FORCE=1 ;;
    --skip-workflows) SKIP_WF=1 ;;
    --skip-seed) SKIP_SEED=1 ;;
    -h|--help) sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
  shift
done

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

if [ -n "$REF" ]; then
  [ -z "$SRC" ] || die "--source and --ref are mutually exclusive"
  git clone --quiet --depth 1 --branch "$REF" "$HARNESS_URL" "$WORK/harness" 2>"$WORK/clone.log" \
    || die "cannot clone $HARNESS_URL@$REF ($(tail -1 "$WORK/clone.log"))"
  SRC="$WORK/harness"
fi
[ -n "$SRC" ] || SRC="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$(cd "$SRC" && pwd)"
[ -f "$SRC/harness.manifest" ] && [ -f "$SRC/VERSION" ] || die "$SRC is not a copy of the harness (harness.manifest or VERSION missing)"
[ -d "$TARGET" ] || die "target directory not found: $TARGET"
TARGET="$(cd "$TARGET" && pwd)"
[ "$SRC" != "$TARGET" ] || die "the target is the harness itself"

VERSION="$(head -1 "$SRC/VERSION" | tr -d '[:space:]')"
COMMIT="$(git -C "$SRC" rev-parse HEAD 2>/dev/null || echo unknown)"
if [ "$COMMIT" != unknown ] && [ -n "$(git -C "$SRC" status --porcelain 2>/dev/null)" ]; then COMMIT="$COMMIT-modified"; fi
LOCK_REL=".harness/lock"
: >"$WORK/exclude"
if [ -f "$TARGET/.harness/config.json" ]; then
  command -v python3 >/dev/null 2>&1 || die "python3 is required to read .harness/config.json"
  python3 - "$TARGET/.harness/config.json" "$WORK/exclude" <<'PY' || die "cannot read .harness/config.json"
import json, sys
config = json.load(open(sys.argv[1], encoding="utf-8"))
with open(sys.argv[2], "w", encoding="utf-8") as f:
    for pattern in config.get("exclude", []):
        f.write(str(pattern) + "\n")
PY
fi
OLD="$WORK/old" NEW="$WORK/new"
: >"$NEW"
if [ -f "$TARGET/$LOCK_REL" ]; then grep '^file	' "$TARGET/$LOCK_REL" >"$OLD" || true; else : >"$OLD"; fi
CHANGES=0 CONFLICTS=0 SKIPPED=0

if command -v sha256sum >/dev/null 2>&1; then sha() { sha256sum "$1" | cut -d' ' -f1; }
else sha() { shasum -a 256 "$1" | cut -d' ' -f1; }; fi
old_sha() { awk -F'\t' -v p="$1" '$1 == "file" && $3 == p { print $2 }' "$OLD"; }
say() { printf '  %s %s\n' "$1" "$2"; }
is_excluded() {
  local pattern
  while IFS= read -r pattern; do
    [ -n "$pattern" ] || continue
    # shellcheck disable=SC2254 # glob pattern intended
    case "$1" in $pattern) return 0 ;; esac
  done <"$WORK/exclude"
  return 1
}
# Former id of a managed block, for migration (empty if none).
legacy_id() { case "$1" in harness) printf cadre ;; esac; }
is_workflow() { case "$1" in .github/workflows/*) return 0 ;; *) return 1 ;; esac; }

# Writes $2 (temporary file) to $1 (relative to the target) if it differs; $3 = 1 to make it executable.
put() {
  local rel="$1" content="$2" exec_bit="${3:-0}" dest="$TARGET/$1"
  if [ -f "$dest" ] && cmp -s "$content" "$dest"; then
    if [ "$exec_bit" = 1 ] && [ ! -x "$dest" ] && [ "$MODE" = apply ]; then chmod +x "$dest"; fi
    return 0
  fi
  CHANGES=$((CHANGES + 1))
  if [ -f "$dest" ]; then say "~" "$rel"; else say "+" "$rel"; fi
  [ "$MODE" = apply ] || return 0
  mkdir -p "$(dirname "$dest")"
  cp "$content" "$dest"
  if [ "$exec_bit" = 1 ]; then chmod +x "$dest"; fi
}

conflict() { CONFLICTS=$((CONFLICTS + 1)); say "!" "$1: $2"; }

# File owned by the harness (copy and tree modes).
copy_one() {
  local src="$1" rel="$2" dest="$TARGET/$2" new recorded current exec_bit=0
  if [ "$SKIP_WF" = 1 ] && is_workflow "$rel"; then SKIPPED=$((SKIPPED + 1)); return 0; fi
  if is_excluded "$rel"; then return 0; fi
  new="$(sha "$src")"
  recorded="$(old_sha "$rel")"
  [ -x "$src" ] && exec_bit=1
  if [ -f "$dest" ] && ! cmp -s "$src" "$dest" && [ "$FORCE" = 0 ]; then
    current="$(sha "$dest")"
    if [ -z "$recorded" ]; then
      conflict "$rel" "already exists outside the harness (rename the project file, or --force)"
      return 0
    elif [ "$current" != "$recorded" ]; then
      conflict "$rel" "modified locally since the last sync (carry the change over to the harness, or --force)"
      printf 'file\t%s\t%s\n' "$recorded" "$rel" >>"$NEW"
      return 0
    fi
  fi
  put "$rel" "$src" "$exec_bit"
  printf 'file\t%s\t%s\n' "$new" "$rel" >>"$NEW"
}

do_tree() {
  local dir="$1" rel_dir="$2" file
  [ -d "$SRC/$dir" ] || die "manifest directory not found: $dir"
  (cd "$SRC/$dir" && find . -type f ! -name '.DS_Store' | sed 's#^\./##' | LC_ALL=C sort) >"$WORK/tree"
  while IFS= read -r file; do copy_one "$SRC/$dir/$file" "$rel_dir/$file"; done <"$WORK/tree"
}

do_block() {
  local src="$1" rel="$2" id="$3" tpl="${4:-}" dest="$TARGET/$2" begin end base out nb ne legacy
  begin="<!-- harness:begin $id -->"
  end="<!-- harness:end $id -->"
  { printf '%s\n' "$begin"; sed "s/{{HARNESS_VERSION}}/$VERSION/g" "$SRC/$src"; printf '%s\n' "$end"; } >"$WORK/block"
  base="$WORK/base" out="$WORK/out"
  if [ -f "$dest" ]; then cp "$dest" "$base"
  elif [ -n "$tpl" ] && [ "$SKIP_SEED" = 0 ]; then cp "$SRC/$tpl" "$base"
  else : >"$base"; fi
  # Migration: the block id `harness` was `cadre`. Rewrite the two former marker lines, then update as usual.
  legacy="$(legacy_id "$id")"
  if [ -n "$legacy" ] && ! grep -qFx -e "$begin" -e "$end" "$base"; then
    sed -e "s|^<!-- harness:begin $legacy -->\$|$begin|" -e "s|^<!-- harness:end $legacy -->\$|$end|" "$base" >"$WORK/migrated"
    cp "$WORK/migrated" "$base"
  fi
  nb="$(grep -cFx -- "$begin" "$base" || true)"
  ne="$(grep -cFx -- "$end" "$base" || true)"
  if [ "$nb" = 1 ] && [ "$ne" = 1 ]; then
    awk -v b="$begin" -v e="$end" -v f="$WORK/block" '
      $0 == b { while ((getline line < f) > 0) print line; inside = 1; next }
      $0 == e && inside { inside = 0; next }
      !inside { print }' "$base" >"$out"
  elif [ "$nb" = 0 ] && [ "$ne" = 0 ]; then
    if [ -s "$base" ]; then { cat "$base"; printf '\n'; cat "$WORK/block"; } >"$out"; else cp "$WORK/block" "$out"; fi
  else
    conflict "$rel" "inconsistent \"harness:begin/end $id\" markers ($nb begin, $ne end): fix by hand"
    return 0
  fi
  put "$rel" "$out"
}

do_seed() {
  local src="$1" rel="$2"
  if [ "$SKIP_SEED" = 1 ] || [ -e "$TARGET/$rel" ]; then return 0; fi
  src="$SRC/$src"
  put "$rel" "$src" "$([ -x "$src" ] && echo 1 || echo 0)"
}

do_jsonmerge() {
  local src="$1" rel="$2" dest="$TARGET/$2"
  if ! command -v python3 >/dev/null 2>&1; then
    conflict "$rel" "python3 missing: merge $src by hand"
    return 0
  fi
  python3 - "$SRC/$src" "$dest" "$WORK/merged" <<'PY' || { conflict "$rel" "unreadable JSON, cannot merge"; return 0; }
import json, os, sys
fragment_path, dest_path, out_path = sys.argv[1:4]
with open(fragment_path, encoding="utf-8") as f:
    fragment = json.load(f)
original_text = None
if os.path.exists(dest_path):
    with open(dest_path, encoding="utf-8") as f:
        original_text = f.read()
current = json.loads(original_text) if original_text and original_text.strip() else {}

def merge(base, extra):
    """Add to base what is missing; never change a value that is already there."""
    if isinstance(base, dict) and isinstance(extra, dict):
        out = dict(base)
        for key, value in extra.items():
            out[key] = merge(base[key], value) if key in base else value
        return out
    if isinstance(base, list) and isinstance(extra, list):
        return base + [item for item in extra if item not in base]
    return base

merged = merge(current, fragment)
with open(out_path, "w", encoding="utf-8") as f:
    if original_text is not None and merged == current:
        f.write(original_text)  # nothing new: keep the project's formatting
    else:
        f.write(json.dumps(merged, indent=2, ensure_ascii=False) + "\n")
PY
  put "$rel" "$WORK/merged"
}

do_refbump() {
  local rel="$1" dest="$TARGET/$1" repo_re pin
  [ -f "$dest" ] || return 0
  repo_re="$(printf '%s' "$HARNESS_REPO" | sed 's/[.]/\\./g')"
  # Pinned by SHA (tag as a comment), like any action (zizmor: unpinned-uses); by tag if the commit is unknown.
  case "$COMMIT" in
    [0-9a-f]*) if [ "${#COMMIT}" = 40 ]; then pin="$COMMIT # v${VERSION}"; else pin="v${VERSION}"; fi ;;
    *) pin="v${VERSION}" ;;
  esac
  sed -E "s|(${repo_re}/\\.github/workflows/[A-Za-z0-9._-]+)@[A-Za-z0-9._/-]+( # v[0-9A-Za-z.-]+)?|\\1@${pin}|g" "$dest" >"$WORK/bumped"
  put "$rel" "$WORK/bumped"
}

# Integration branch vs default branch. GitHub runs issues, issue_comment, pull_request_target and schedule workflows
# from the default branch only. On a FIRST adoption (no lock yet) a mismatch stops the sync before anything is written,
# unless the relay (templates/.github/workflows/harness-relay.yml) is already on the default branch, or the project
# keeps two branches on purpose ("default_branch_check": false: then said once). Later syncs only warn.
# Default branch unknown (no origin/HEAD): says "could not check", never "OK", never blocks.
RELAY_REL=".github/workflows/harness-relay.yml"
SILENT_EVENTS="issues, issue_comment, pull_request_target and schedule"
# shellcheck disable=SC2016 # backticks are text
SILENT_JOBS='issue hygiene and claims (`issue` job of harness.yml, the label reconcile), the daily dashboard (`flow`), the weekly settings, security and doc audit jobs, and any project workflow on those events'
DB_INTEG="" DB_CHECK=true DB_DEFAULT=""
if [ -f "$TARGET/.harness/config.json" ]; then
  DB_STATE="$(python3 -c '
import json, sys
c = json.load(open(sys.argv[1], encoding="utf-8"))
if isinstance(c, dict) and isinstance(c.get("integration_branch"), str):
    print(c["integration_branch"])
    print("false" if c.get("default_branch_check") is False else "true")
' "$TARGET/.harness/config.json" 2>/dev/null)" || DB_STATE=""
  DB_INTEG="$(printf '%s\n' "$DB_STATE" | sed -n 1p)"
  DB_CHECK="$(printf '%s\n' "$DB_STATE" | sed -n 2p)"
fi
DB_DEFAULT="$(git -C "$TARGET" symbolic-ref -q refs/remotes/origin/HEAD 2>/dev/null)" || DB_DEFAULT=""
DB_DEFAULT="${DB_DEFAULT#refs/remotes/origin/}"
relay_on_default() { git -C "$TARGET" cat-file -e "refs/remotes/origin/$DB_DEFAULT:$RELAY_REL" 2>/dev/null; }
branches_differ() { [ -n "$DB_INTEG" ] && [ -n "$DB_DEFAULT" ] && [ "$DB_DEFAULT" != "$DB_INTEG" ]; }
FIRST_ADOPTION=0
[ -f "$TARGET/$LOCK_REL" ] || FIRST_ADOPTION=1

if [ "$FIRST_ADOPTION" = 1 ] && [ "$DB_CHECK" != false ] && branches_differ && ! relay_on_default; then
  # shellcheck disable=SC2016 # backticks are text
  {
    printf '🔴 Adoption stopped, nothing written: integration branch "%s" is not the default branch "%s".\n' "$DB_INTEG" "$DB_DEFAULT"
    printf '   GitHub runs %s workflows from the default branch only, so these would never run: %s.\n' "$SILENT_EVENTS" "$SILENT_JOBS"
    printf '   Two ways out, then run the sync again (docs/ADOPTION.md, "Integration branch that is not the default branch"):\n'
    printf '   1. make "%s" the default branch (Settings > General > Default branch), then `git remote set-head origin -a`;\n' "$DB_INTEG"
    printf '   2. or install the relay: copy templates/.github/workflows/harness-relay.yml of the harness (%s) to %s on\n' "v$VERSION" "$RELAY_REL"
    printf '      "%s" by a PR to that branch, with INTEGRATION_BRANCH: %s, then `git fetch origin`.\n' "$DB_DEFAULT" "$DB_INTEG"
    printf '   Two branches kept on purpose, labels kept by hand: "default_branch_check": false in .harness/config.json.\n'
  } >&2
  exit 4
fi

default_branch_alert() {
  [ -n "$DB_INTEG" ] || return 0
  if [ "$DB_CHECK" = false ]; then
    if [ "$FIRST_ADOPTION" = 1 ] && branches_differ && ! relay_on_default; then
      printf '🟠 Two branches kept on purpose ("default_branch_check": false): integration branch "%s" is not the default branch "%s", so these will not run: %s (%s events). Keep the labels by hand; this is said once.\n' \
        "$DB_INTEG" "$DB_DEFAULT" "$SILENT_JOBS" "$SILENT_EVENTS"
    fi
    return 0
  fi
  if [ -z "$DB_DEFAULT" ]; then
    echo "🟠 Could not check whether the integration branch \"$DB_INTEG\" is the repository's default branch (no origin/HEAD: run \`git remote set-head origin -a\`)."
  elif [ "$DB_DEFAULT" != "$DB_INTEG" ] && relay_on_default; then
    echo "🟢 Integration branch \"$DB_INTEG\" is not the default branch \"$DB_DEFAULT\"; $RELAY_REL on \"$DB_DEFAULT\" relays the issue and schedule jobs (keep its references in step with harness.yml)."
  elif [ "$DB_DEFAULT" != "$DB_INTEG" ]; then
    echo "🟠 Integration branch \"$DB_INTEG\" is not the default branch \"$DB_DEFAULT\": GitHub runs $SILENT_EVENTS workflows from the default branch only, so label hygiene, claims, the dashboard and the weekly jobs stay silent (fix: make it the default branch, or install the relay $RELAY_REL on \"$DB_DEFAULT\", docs/ADOPTION.md; to silence: \"default_branch_check\": false in .harness/config.json)."
  fi
  return 0
}

printf 'Belayline %s (%s) → %s [%s]\n' "$VERSION" "${COMMIT:0:12}" "$TARGET" "$MODE"
while read -r kind src rel id tpl; do
  case "$kind" in ''|'#'*) continue ;; esac
  if [ "$kind" != tree ] && is_excluded "$rel"; then continue; fi
  if [ "$SKIP_WF" = 1 ] && [ "$kind" != tree ] && is_workflow "$rel"; then SKIPPED=$((SKIPPED + 1)); continue; fi
  case "$kind" in
    copy) [ -f "$SRC/$src" ] || die "manifest file not found: $src"; copy_one "$SRC/$src" "$rel" ;;
    tree) do_tree "$src" "$rel" ;;
    block) do_block "$src" "$rel" "${id:?block without ID: $rel}" "${tpl:-}" ;;
    seed) do_seed "$src" "$rel" ;;
    jsonmerge) do_jsonmerge "$src" "$rel" ;;
    refbump) do_refbump "$rel" ;;
    *) die "unknown mode in harness.manifest: $kind" ;;
  esac
done <"$SRC/harness.manifest"

# Harness files removed since the last sync: deleted if they were not modified.
while IFS="$(printf '\t')" read -r _ recorded rel; do
  [ -n "$rel" ] || continue
  if awk -F'\t' -v p="$rel" '$3 == p { found = 1 } END { exit !found }' "$NEW"; then continue; fi
  if [ "$SKIP_WF" = 1 ] && is_workflow "$rel"; then printf 'file\t%s\t%s\n' "$recorded" "$rel" >>"$NEW"; continue; fi
  [ -f "$TARGET/$rel" ] || continue
  if [ "$(sha "$TARGET/$rel")" = "$recorded" ] || [ "$FORCE" = 1 ]; then
    CHANGES=$((CHANGES + 1)); say "-" "$rel"
    if [ "$MODE" = apply ]; then rm -f "$TARGET/$rel"; rmdir -p "$(dirname "$TARGET/$rel")" 2>/dev/null || true; fi
  else
    conflict "$rel" "removed from the harness but modified locally: kept, delete it or take it over by hand"
  fi
done <"$OLD"

printf '%s\n' "$VERSION" >"$WORK/version"
put ".harness/VERSION" "$WORK/version"
{
  printf '# Belayline lock: written by scripts/harness-sync.sh, do not edit by hand.\n'
  printf 'version\t%s\nrepo\t%s\ncommit\t%s\n' "$VERSION" "$HARNESS_REPO" "$COMMIT"
  LC_ALL=C sort -t "$(printf '\t')" -k3,3 "$NEW"
} >"$WORK/lock"
put "$LOCK_REL" "$WORK/lock"

default_branch_alert
[ "$SKIPPED" = 0 ] || printf '  (%s entry(ies) under .github/workflows/ skipped: --skip-workflows)\n' "$SKIPPED"
if [ "$CONFLICTS" -gt 0 ]; then
  printf '🟠 %s conflict(s), affected files left as they are; %s change(s).\n' "$CONFLICTS" "$CHANGES"
  exit 3
fi
if [ "$CHANGES" = 0 ]; then printf '🟢 Up to date (%s).\n' "$VERSION"; exit 0; fi
case "$MODE" in
  check) printf '🔴 Drift: %s change(s) to sync.\n' "$CHANGES"; exit 1 ;;
  dry-run) printf '%s change(s) to apply.\n' "$CHANGES" ;;
  *) printf '🟢 %s change(s) applied. Review "git diff", then commit.\n' "$CHANGES" ;;
esac

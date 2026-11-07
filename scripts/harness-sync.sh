#!/usr/bin/env bash
# Vendorise le cadre agentic-harness dans un dépôt consommateur, à une version donnée (docs/ADOPTION.md).
#
# Usage : harness-sync.sh [--source DIR | --ref vX.Y.Z] [--target DIR] [--check | --dry-run] [--force]
#                         [--skip-workflows] [--skip-seed]
#   --source DIR       copie du cadre à vendoriser (défaut : le dépôt qui contient ce script)
#   --ref vX.Y.Z       clone le cadre à ce tag ($HARNESS_URL, défaut https://github.com/$HARNESS_REPO.git)
#   --target DIR       racine du dépôt consommateur (défaut : dossier courant)
#   --check            n'écrit rien ; sort en 1 si une synchro changerait quelque chose (contrôle de dérive en CI)
#   --dry-run          n'écrit rien ; liste ce qui changerait
#   --force            remplace aussi les fichiers du cadre modifiés localement ou déjà présents
#   --skip-workflows   ne touche à rien sous .github/workflows/ (un GITHUB_TOKEN ne peut pas pousser ces fichiers)
#   --skip-seed        ne crée pas les gabarits du projet (mode seed), par exemple en synchro automatique
#
# Ce que fait chaque mode du manifeste : en tête de harness.manifest. Le script est idempotent : relancé à la même
# version, il ne change rien. Il enregistre la version dans .harness/VERSION et, dans .harness/lock, le commit du
# cadre et l'empreinte SHA-256 de chaque fichier possédé par le cadre, ce qui lui permet de reconnaître une
# modification locale (jamais écrasée sans --force) et de supprimer proprement un fichier retiré du cadre.
# Réglages du projet lus dans <cible>/.harness/config.json (à créer AVANT la première synchro pour qu'ils comptent) :
#   "language": "fr" | "en"   une source traduite i18n/<langue>/<chemin> remplace la source française quand elle existe ;
#   "exclude": ["motif", …]   destinations à ne pas vendoriser (glob sur le chemin relatif, `*` traverse les `/`) ;
#                             un fichier exclu déjà vendorisé et non modifié est retiré.
# Sorties : 0 = ok ; 1 = --check a trouvé une dérive ; 2 = usage ou erreur ; 3 = conflits (fichiers laissés en l'état).
# Bash 3.2 compatible (macOS) ; python3 seulement pour le mode jsonmerge.
set -euo pipefail

HARNESS_REPO="${HARNESS_REPO:-francoisgn/agentic-harness}"
HARNESS_URL="${HARNESS_URL:-https://github.com/${HARNESS_REPO}.git}"
SRC="" REF="" TARGET="." MODE=apply FORCE=0 SKIP_WF=0 SKIP_SEED=0

die() { printf 'harness-sync : %s\n' "$1" >&2; exit 2; }
while [ $# -gt 0 ]; do
  case "$1" in
    --source) SRC="${2:?--source attend un dossier}"; shift ;;
    --ref) REF="${2:?--ref attend un tag}"; shift ;;
    --target) TARGET="${2:?--target attend un dossier}"; shift ;;
    --check) MODE=check ;;
    --dry-run) MODE=dry-run ;;
    --force) FORCE=1 ;;
    --skip-workflows) SKIP_WF=1 ;;
    --skip-seed) SKIP_SEED=1 ;;
    -h|--help) sed -n '2,23p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "option inconnue : $1" ;;
  esac
  shift
done

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

if [ -n "$REF" ]; then
  [ -z "$SRC" ] || die "--source et --ref s'excluent"
  git clone --quiet --depth 1 --branch "$REF" "$HARNESS_URL" "$WORK/harness" 2>"$WORK/clone.log" \
    || die "clone de $HARNESS_URL@$REF impossible ($(tail -1 "$WORK/clone.log"))"
  SRC="$WORK/harness"
fi
[ -n "$SRC" ] || SRC="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$(cd "$SRC" && pwd)"
[ -f "$SRC/harness.manifest" ] && [ -f "$SRC/VERSION" ] || die "$SRC n'est pas une copie du cadre (harness.manifest ou VERSION absent)"
[ -d "$TARGET" ] || die "dossier cible introuvable : $TARGET"
TARGET="$(cd "$TARGET" && pwd)"
[ "$SRC" != "$TARGET" ] || die "la cible est le cadre lui-même"

VERSION="$(head -1 "$SRC/VERSION" | tr -d '[:space:]')"
COMMIT="$(git -C "$SRC" rev-parse HEAD 2>/dev/null || echo inconnu)"
if [ "$COMMIT" != inconnu ] && [ -n "$(git -C "$SRC" status --porcelain 2>/dev/null)" ]; then COMMIT="$COMMIT-modifié"; fi
LOCK_REL=".harness/lock"
LANGUAGE=fr
: >"$WORK/exclude"
if [ -f "$TARGET/.harness/config.json" ]; then
  command -v python3 >/dev/null 2>&1 || die "python3 requis pour lire .harness/config.json"
  python3 - "$TARGET/.harness/config.json" "$WORK/exclude" "$WORK/language" <<'PY' || die ".harness/config.json illisible"
import json, sys
config = json.load(open(sys.argv[1], encoding="utf-8"))
with open(sys.argv[2], "w", encoding="utf-8") as f:
    for pattern in config.get("exclude", []):
        f.write(str(pattern) + "\n")
open(sys.argv[3], "w", encoding="utf-8").write(str(config.get("language", "fr")))
PY
  LANGUAGE="$(cat "$WORK/language")"
fi
case "$LANGUAGE" in *[!a-z-]*|'') die "langue invalide dans .harness/config.json : $LANGUAGE" ;; esac
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
    # shellcheck disable=SC2254 # motif glob voulu
    case "$1" in $pattern) return 0 ;; esac
  done <"$WORK/exclude"
  return 1
}
# Chemin de la source $1 dans la langue du projet : i18n/<langue>/$1 s'il existe, sinon la source française.
localized() { if [ "$LANGUAGE" != fr ] && [ -e "$SRC/i18n/$LANGUAGE/$1" ]; then printf '%s' "$SRC/i18n/$LANGUAGE/$1"; else printf '%s' "$SRC/$1"; fi; }
is_workflow() { case "$1" in .github/workflows/*) return 0 ;; *) return 1 ;; esac; }

# Écrit $2 (fichier temporaire) en $1 (relatif à la cible) s'il diffère ; $3 = 1 pour le rendre exécutable.
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

conflict() { CONFLICTS=$((CONFLICTS + 1)); say "!" "$1 : $2"; }

# Fichier possédé par le cadre (modes copy et tree).
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
      conflict "$rel" "existe déjà hors du cadre (renommer le fichier du projet, ou --force)"
      return 0
    elif [ "$current" != "$recorded" ]; then
      conflict "$rel" "modifié localement depuis la dernière synchro (reporter la modification dans le cadre, ou --force)"
      printf 'file\t%s\t%s\n' "$recorded" "$rel" >>"$NEW"
      return 0
    fi
  fi
  put "$rel" "$src" "$exec_bit"
  printf 'file\t%s\t%s\n' "$new" "$rel" >>"$NEW"
}

do_tree() {
  local dir="$1" rel_dir="$2" file
  [ -d "$SRC/$dir" ] || die "dossier du manifeste introuvable : $dir"
  (cd "$SRC/$dir" && find . -type f ! -name '.DS_Store' | sed 's#^\./##' | LC_ALL=C sort) >"$WORK/tree"
  while IFS= read -r file; do copy_one "$(localized "$dir/$file")" "$rel_dir/$file"; done <"$WORK/tree"
}

do_block() {
  local src="$1" rel="$2" id="$3" tpl="${4:-}" dest="$TARGET/$2" begin end base out nb ne
  begin="<!-- harness:begin $id -->"
  end="<!-- harness:end $id -->"
  { printf '%s\n' "$begin"; sed "s/{{HARNESS_VERSION}}/$VERSION/g" "$(localized "$src")"; printf '%s\n' "$end"; } >"$WORK/block"
  base="$WORK/base" out="$WORK/out"
  if [ -f "$dest" ]; then cp "$dest" "$base"
  elif [ -n "$tpl" ] && [ "$SKIP_SEED" = 0 ]; then cp "$(localized "$tpl")" "$base"
  else : >"$base"; fi
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
    conflict "$rel" "marqueurs « harness:begin/end $id » incohérents ($nb début, $ne fin) : corriger à la main"
    return 0
  fi
  put "$rel" "$out"
}

do_seed() {
  local src="$1" rel="$2"
  if [ "$SKIP_SEED" = 1 ] || [ -e "$TARGET/$rel" ]; then return 0; fi
  src="$(localized "$src")"
  put "$rel" "$src" "$([ -x "$src" ] && echo 1 || echo 0)"
}

do_jsonmerge() {
  local src="$1" rel="$2" dest="$TARGET/$2"
  if ! command -v python3 >/dev/null 2>&1; then
    conflict "$rel" "python3 absent : fusionner à la main $src"
    return 0
  fi
  python3 - "$SRC/$src" "$dest" "$WORK/merged" <<'PY' || { conflict "$rel" "JSON illisible, fusion impossible"; return 0; }
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
    """Ajoute à base ce qui manque ; ne modifie jamais une valeur déjà présente."""
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
        f.write(original_text)  # rien de nouveau : on garde la mise en forme du projet
    else:
        f.write(json.dumps(merged, indent=2, ensure_ascii=False) + "\n")
PY
  put "$rel" "$WORK/merged"
}

do_refbump() {
  local rel="$1" dest="$TARGET/$1" repo_re pin
  [ -f "$dest" ] || return 0
  repo_re="$(printf '%s' "$HARNESS_REPO" | sed 's/[.]/\\./g')"
  # Épinglé par SHA (tag en commentaire), comme toute action (zizmor : unpinned-uses) ; par tag si le commit est inconnu.
  case "$COMMIT" in
    [0-9a-f]*) if [ "${#COMMIT}" = 40 ]; then pin="$COMMIT # v${VERSION}"; else pin="v${VERSION}"; fi ;;
    *) pin="v${VERSION}" ;;
  esac
  sed -E "s|(${repo_re}/\\.github/workflows/[A-Za-z0-9._-]+)@[A-Za-z0-9._/-]+( # v[0-9A-Za-z.-]+)?|\\1@${pin}|g" "$dest" >"$WORK/bumped"
  put "$rel" "$WORK/bumped"
}

printf 'agentic-harness %s (%s) → %s [%s, %s]\n' "$VERSION" "${COMMIT:0:12}" "$TARGET" "$MODE" "$LANGUAGE"
while read -r kind src rel id tpl; do
  case "$kind" in ''|'#'*) continue ;; esac
  if [ "$kind" != tree ] && is_excluded "$rel"; then continue; fi
  if [ "$SKIP_WF" = 1 ] && [ "$kind" != tree ] && is_workflow "$rel"; then SKIPPED=$((SKIPPED + 1)); continue; fi
  case "$kind" in
    copy) [ -f "$SRC/$src" ] || die "fichier du manifeste introuvable : $src"; copy_one "$(localized "$src")" "$rel" ;;
    tree) do_tree "$src" "$rel" ;;
    block) do_block "$src" "$rel" "${id:?block sans ID : $rel}" "${tpl:-}" ;;
    seed) do_seed "$src" "$rel" ;;
    jsonmerge) do_jsonmerge "$src" "$rel" ;;
    refbump) do_refbump "$rel" ;;
    *) die "mode inconnu dans harness.manifest : $kind" ;;
  esac
done <"$SRC/harness.manifest"

# Fichiers du cadre retirés depuis la dernière synchro : supprimés s'ils n'ont pas été modifiés.
while IFS="$(printf '\t')" read -r _ recorded rel; do
  [ -n "$rel" ] || continue
  if awk -F'\t' -v p="$rel" '$3 == p { found = 1 } END { exit !found }' "$NEW"; then continue; fi
  if [ "$SKIP_WF" = 1 ] && is_workflow "$rel"; then printf 'file\t%s\t%s\n' "$recorded" "$rel" >>"$NEW"; continue; fi
  [ -f "$TARGET/$rel" ] || continue
  if [ "$(sha "$TARGET/$rel")" = "$recorded" ] || [ "$FORCE" = 1 ]; then
    CHANGES=$((CHANGES + 1)); say "-" "$rel"
    if [ "$MODE" = apply ]; then rm -f "$TARGET/$rel"; rmdir -p "$(dirname "$TARGET/$rel")" 2>/dev/null || true; fi
  else
    conflict "$rel" "retiré du cadre mais modifié localement : conservé, à supprimer ou reprendre à la main"
  fi
done <"$OLD"

printf '%s\n' "$VERSION" >"$WORK/version"
put ".harness/VERSION" "$WORK/version"
{
  printf '# Verrou agentic-harness : écrit par scripts/harness-sync.sh, ne pas modifier à la main.\n'
  printf 'version\t%s\nrepo\t%s\ncommit\t%s\n' "$VERSION" "$HARNESS_REPO" "$COMMIT"
  LC_ALL=C sort -t "$(printf '\t')" -k3,3 "$NEW"
} >"$WORK/lock"
put "$LOCK_REL" "$WORK/lock"

[ "$SKIPPED" = 0 ] || printf '  (%s entrée(s) sous .github/workflows/ sautée(s) : --skip-workflows)\n' "$SKIPPED"
if [ "$CONFLICTS" -gt 0 ]; then
  printf '🟠 %s conflit(s), fichiers concernés laissés en l'"'"'état ; %s changement(s).\n' "$CONFLICTS" "$CHANGES"
  exit 3
fi
if [ "$CHANGES" = 0 ]; then printf '🟢 À jour (%s).\n' "$VERSION"; exit 0; fi
case "$MODE" in
  check) printf '🔴 Dérive : %s changement(s) à synchroniser.\n' "$CHANGES"; exit 1 ;;
  dry-run) printf '%s changement(s) à appliquer.\n' "$CHANGES" ;;
  *) printf '🟢 %s changement(s) appliqué(s). Relire « git diff », puis committer.\n' "$CHANGES" ;;
esac

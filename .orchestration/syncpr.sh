#!/usr/bin/env bash
# syncpr.sh <worktree> : merge origin/master into the worktree's branch, union-resolve CHANGELOG.md, run checks, push.
set -uo pipefail
cd "$1" || exit 2
git fetch -q origin master
if git merge -q origin/master -m "Merge master" >/dev/null 2>&1; then echo "merged clean"; else
  bad=$(git diff --name-only --diff-filter=U | grep -v '^CHANGELOG.md$' || true)
  if [ -n "$bad" ]; then echo "CONFLICTS: $bad"; exit 3; fi
  python3 - <<'PY'
import pathlib,re
p=pathlib.Path("CHANGELOG.md"); s=p.read_text(encoding="utf-8")
s=re.sub(r"^<<<<<<< [^\n]*\n(.*?)^=======\n(.*?)^>>>>>>> [^\n]*\n", lambda m: m.group(2)+m.group(1), s, flags=re.S|re.M)
p.write_text(s,encoding="utf-8")
PY
  git add CHANGELOG.md && git commit -q -m "Merge master: CHANGELOG bullets of both sides kept" && echo "merged with CHANGELOG union"
fi
python3 scripts/check-framework.py | tail -1
python3 -m unittest discover -s scripts/tests -p 'test_*.py' 2>&1 | tail -1
scripts/tests/test-harness-sync.sh 2>&1 | tail -1
python3 scripts/readme-check.py | tail -1
npx --yes markdownlint-cli2@0.18.1 >/dev/null 2>&1; echo "md=$?"
git push -q origin HEAD 2>&1 | grep -v "^remote" | tail -1
git rev-parse --short HEAD

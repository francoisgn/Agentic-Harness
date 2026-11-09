#!/usr/bin/env python3
"""Resolves the `compliance` key of .harness/config.json into the compliance reviewers to run (COMPLIANCE.md §2).

Three ways to plug in a compliance framework, as the company chooses:
  "gdpr"                                    built-in agent of the harness (.claude/agents/compliance-gdpr.md)
  {"id": "pci", "agent": "<.md path>"}      company agent, which replaces the built-in one or adds a framework
  {"id": "dora", "spec": "<.md path>"}      spec only: the generic reviewer `compliance-reviewer` applies it
Common options: "paths" (globs) and "keywords" (words of the diff) decide the scope without launching an agent;
"enabled": false disables an entry; "confirmed_by" names who decides (DPO, CISO, QSA...).

Usage: compliance-plan.py [--root .] [--files f1 f2 ... | --base origin/develop] [--diff-file diff.txt]
JSON output {"reviewers": [...], "errors": [...]}; exit code 1 if an entry is invalid. Standard library only.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

AGENTS_DIR = ".claude/agents"
GENERIC = "compliance-reviewer"
SPEC_SECTIONS = ("## When to step in", "## What I check", "## Expected evidence", "## Sources")
SPEC_KEYS = ("id", "framework", "confirmed_by")


def _frontmatter(text):
    if not text.startswith("---\n") or text.find("\n---", 4) < 0:
        return None
    meta = {}
    for line in text[4:text.find("\n---", 4)].splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta


def check_spec(path):
    """Gaps of a compliance spec file (frontmatter and mandatory sections)."""
    path = pathlib.Path(path)
    if not path.is_file():
        return [f"spec not found: {path}"]
    text = path.read_text(encoding="utf-8")
    meta = _frontmatter(text) or {}
    errors = [f"{path}: key `{k}` missing from the header" for k in SPEC_KEYS if not meta.get(k)]
    errors += [f"{path}: section \"{s}\" missing" for s in SPEC_SECTIONS if s not in text]
    return errors


def glob_match(path, pattern):
    """Path glob: `*` and `?` stay within one directory, `**/` spans zero or more directories, `/**` everything below."""
    rx, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            rx, i = rx + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            rx, i = rx + ".*", i + 2
        elif pattern[i] == "*":
            rx, i = rx + "[^/]*", i + 1
        elif pattern[i] == "?":
            rx, i = rx + "[^/]", i + 1
        else:
            rx, i = rx + re.escape(pattern[i]), i + 1
    return re.fullmatch(rx, path) is not None


def _inside(root, rel):
    """The path stays inside the repository (neither absolute outside the root, nor a `..` that leaves it)."""
    base = pathlib.Path(root).resolve()
    target = (base / rel).resolve()
    return target == base or base in target.parents


def _in_scope(entry, files, diff):
    paths, keywords = entry.get("paths") or [], entry.get("keywords") or []
    if not paths and not keywords:
        return "to assess", "scope judged by the agent (section \"When to step in\")"
    for f in files:
        for g in paths:
            if glob_match(f, g):
                return "in scope", f"{f} matches {g}"
    # Added or removed lines only (not the +++/--- headers, which carry paths), whole word
    changed = "\n".join(line[1:] for line in diff.splitlines()
                        if line.startswith(("+", "-")) and not line.startswith(("+++", "---")))
    for k in keywords:
        if re.search(rf"(?<!\w){re.escape(k)}(?!\w)", changed, re.IGNORECASE):
            return "in scope", f"keyword \"{k}\" in the diff"
    return "out of scope", "no configured path or keyword is touched"


def plan(config, root, files=(), diff=""):
    root = pathlib.Path(root)
    reviewers, errors, seen = [], [], set()
    entries = config.get("compliance", [])
    if not isinstance(entries, list):
        return {"reviewers": [], "errors": ["`compliance` must be a list (e.g. [\"gdpr\"])"]}
    for raw in entries:
        if not isinstance(raw, (str, dict)):
            errors.append(f"invalid entry (string or object expected): {raw!r}")
            continue
        entry = {"id": raw} if isinstance(raw, str) else dict(raw)
        cid = entry.get("id")
        if not isinstance(cid, str) or not cid.strip():
            errors.append(f"entry without a string `id`: {raw!r}")
            continue
        cid = cid.strip()
        if re.search(r"[/\\]|\.\.", cid):  # the id goes into a file name: no directory, no parent traversal
            errors.append(f"{cid!r}: invalid `id` (no `/`, no `\\`, no `..`)")
            continue
        bad = [k for k in ("agent", "spec") if entry.get(k) is not None and not isinstance(entry[k], str)]
        if bad:
            errors.append(f"{cid}: `{bad[0]}` must be a path (string)")
            continue
        outside = [k for k in ("agent", "spec") if entry.get(k) and not _inside(root, entry[k])]
        if outside:
            errors.append(f"{cid}: `{outside[0]}` points outside the repository, refused")
            continue
        if cid in seen:
            errors.append(f"{cid}: declared twice")
            continue
        seen.add(cid)
        if entry.get("enabled", True) is False:
            continue
        if entry.get("agent") and entry.get("spec"):
            errors.append(f"{cid}: `agent` or `spec`, not both")
            continue
        if entry.get("agent"):
            path = root / entry["agent"]
            meta = _frontmatter(path.read_text(encoding="utf-8")) if path.is_file() else None
            if not path.is_file():
                errors.append(f"{cid}: agent not found {entry['agent']}")
                continue
            if not meta or not meta.get("name"):
                errors.append(f"{cid}: {entry['agent']} has no `name` in its header")
                continue
            mode, agent, file = "project agent", meta["name"], entry["agent"]
        elif entry.get("spec"):
            spec_errors = check_spec(root / entry["spec"])
            if spec_errors:
                errors += [f"{cid}: {e}" for e in spec_errors]
                continue
            if not (root / AGENTS_DIR / f"{GENERIC}.md").is_file():
                errors.append(f"{cid}: generic reviewer {AGENTS_DIR}/{GENERIC}.md missing (excluded from the sync?)")
                continue
            mode, agent, file = "spec", GENERIC, entry["spec"]
        else:
            file = f"{AGENTS_DIR}/compliance-{cid}.md"
            if not (root / file).is_file():
                errors.append(f"{cid}: no built-in agent {file}; provide `agent` or `spec`")
                continue
            mode, agent = "built-in", f"compliance-{cid}"
        scope, reason = _in_scope(entry, files, diff)
        reviewer = {"id": cid, "mode": mode, "agent": agent, "file": file, "scope": scope, "reason": reason}
        if entry.get("confirmed_by"):
            reviewer["confirmed_by"] = entry["confirmed_by"]
        reviewers.append(reviewer)
    return {"reviewers": reviewers, "errors": errors}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--files", nargs="*", default=None)
    ap.add_argument("--base", help="computes files and diff with git diff <base>...HEAD")
    ap.add_argument("--diff-file")
    a = ap.parse_args()
    root = pathlib.Path(a.root)
    cfg_path = root / ".harness/config.json"
    config = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.is_file() else {}
    files, diff = a.files or [], ""
    if a.base:
        git = ["git", "-C", str(root), "diff", f"{a.base}...HEAD"]
        names = subprocess.run(git + ["--name-only"], capture_output=True, text=True)
        if names.returncode != 0:
            print(f"✘ git diff {a.base}...HEAD: {names.stderr.strip()}", file=sys.stderr)
            return 1
        files = names.stdout.split()
        diff = subprocess.run(git, capture_output=True, text=True).stdout
    if a.diff_file:
        diff = pathlib.Path(a.diff_file).read_text(encoding="utf-8")
    result = plan(config, root, files, diff)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    for e in result["errors"]:
        print(f"✘ {e}", file=sys.stderr)
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())

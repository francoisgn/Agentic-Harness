#!/usr/bin/env python3
"""Checks the operator's decisions file, docs/DECISIONS.md (standard library only).

The file holds a table (columns: date, scope key, decision, source, status). Checked, all findings listed:
- every row has a date (YYYY-MM-DD), a scope key, a decision, a source and a known status
  (`in force`, `replaced by <date>`, `lifted <date>`);
- at most one `in force` row per scope key (compared case-insensitively): a new decision names the one it replaces.
Off (exit 0, a notice) when the file is absent: a project that does not want it just has no file.
Rows inside fenced blocks and HTML comments are ignored.
Usage: decisions-check.py [--root <repository>] [--file <path>]   (exits 1 on any finding)
"""
import argparse
import pathlib
import re
import sys

DEFAULT_FILE = "docs/DECISIONS.md"
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
COMMENT = re.compile(r"<!--.*?-->", re.S)
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STATUS = re.compile(r"^(in force|(replaced by|lifted) \d{4}-\d{2}-\d{2})$", re.I)
SEPARATOR = re.compile(r"^:?-{3,}:?$")
FIELDS = ("date", "scope key", "decision", "source", "status")


def table_rows(text):
    """(line number, cells) of each table row outside fenced blocks and comments, header and separator excluded."""
    text = COMMENT.sub(lambda c: "\n" * c.group(0).count("\n"), text)
    rows, fence = [], None
    for number, line in enumerate(text.split("\n"), 1):
        m = FENCE.match(line)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence):
                fence = None
            continue
        if m:
            fence = m.group(1)
            continue
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(SEPARATOR.match(c) for c in cells if c) or cells[:1] == ["Date"] and "Scope key" in cells:
            continue
        rows.append((number, cells))
    return rows


def check(text):
    """The findings (list of strings) for the content of a decisions file."""
    errors, active = [], {}
    for number, cells in table_rows(text):
        cells += [""] * (len(FIELDS) - len(cells))
        date, key, decision, source, status = cells[: len(FIELDS)]
        where = f"line {number}"
        if not DATE.match(date):
            errors.append(f"{where}: date missing or not YYYY-MM-DD ({date!r})")
        if not key:
            errors.append(f"{where}: scope key missing")
        if not decision:
            errors.append(f"{where}: decision missing")
        if not source:
            errors.append(f"{where}: source missing (link, date of the comment or message)")
        if not STATUS.match(status):
            errors.append(f"{where}: status {status!r} is not `in force`, `replaced by <date>` or `lifted <date>`")
        elif status.lower() == "in force" and key:
            first = active.setdefault(key.lower(), number)
            if first != number:
                errors.append(
                    f"{where}: scope key `{key}` is already `in force` on line {first}: "
                    "mark the replaced decision `replaced by <date>`"
                )
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="repository root (default: current folder)")
    parser.add_argument("--file", help=f"decisions file (default: {DEFAULT_FILE} under the root)")
    args = parser.parse_args(argv)
    path = pathlib.Path(args.file) if args.file else pathlib.Path(args.root) / DEFAULT_FILE
    if not path.is_file():
        print(f"decisions-check: {path} not found, check skipped")
        return 0
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"decisions-check: cannot read {path}: {exc}", file=sys.stderr)
        return 1
    errors = check(text)
    for error in errors:
        print(f"{path}: {error}")
    if errors:
        return 1
    print(f"decisions-check: {path} OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

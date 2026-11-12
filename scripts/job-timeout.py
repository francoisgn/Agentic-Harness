#!/usr/bin/env python3
"""Every workflow job that runs steps has `timeout-minutes` (CI-BASELINE.md §2 invariant 4; standard library only).

Without it GitHub lets a stuck job hold its runner for 360 minutes (workflow syntax, `jobs.<job_id>.timeout-minutes`:
https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax). Checked, every finding listed:
- each job of each `*.yml` / `*.yaml` file of the folder (default `.github/workflows`) has `timeout-minutes` at job
  level, a number or a `${{ }}` expression; a job that calls a reusable workflow (`uses:` at job level) cannot carry
  one and is skipped; a `timeout-minutes` on a step does not count for the job;
- a value above the ceiling (default 120) is a warning, not a failure: 360 written by hand is the same hang.
Settings, `.harness/config.json` › `job_timeout` (every key optional):
  `ceiling` (minutes, default 120); `exceptions`: [{"job": "<job id>", "workflow": "<file name, optional>",
  "reason": "<why, required>"}]. An exception without a reason is refused; one naming no job is reported.
No YAML package: an indentation reader takes the job ids and their job-level keys, and answers "could not check"
on a layout it does not understand (flow mapping, anchor, alias, merge key, tab indentation) rather than guessing.
Usage: job-timeout.py [--root <repository>] [--dir <folder>] [--config <file>]
Exit codes: 0 every job has a timeout (or no workflow folder: nothing checked); 1 a job without one, or a bad
exception; 2 could not check a file or the settings (never reported as OK).
"""
import argparse
import json
import pathlib
import re
import sys

DEFAULT_DIR = ".github/workflows"
DEFAULT_CONFIG = ".harness/config.json"
DEFAULT_CEILING = 120
GITHUB_DEFAULT = 360
KEY = re.compile(r"""^(?:"((?:[^"\\]|\\.)*)"|'((?:[^']|'')*)'|([A-Za-z0-9_][A-Za-z0-9_.-]*))[ ]*:(?:[ ]+(.*))?$""")
BLOCK_SCALAR = re.compile(r"^[|>][-+0-9]*$")
NUMBER = re.compile(r"^\d+(\.\d+)?$")
EXPRESSION = re.compile(r"^\$\{\{.*\}\}$")


class Unreadable(Exception):
    """A layout the reader does not understand: (line, reason)."""

    def __init__(self, line, reason):
        super().__init__(reason)
        self.line, self.reason = line, reason


def scalar(rest):
    """The value of a scalar written after `key:`, comment removed (quoted values unquoted)."""
    rest = (rest or "").strip()
    if rest.startswith('"'):
        m = re.match(r'"((?:[^"\\]|\\.)*)"', rest)
        return m.group(1) if m else rest
    if rest.startswith("'"):
        m = re.match(r"'((?:[^']|'')*)'", rest)
        return m.group(1).replace("''", "'") if m else rest
    if rest.startswith("#"):
        return ""
    return re.split(r"\s#", rest, maxsplit=1)[0].strip()


def parse_key(line, number):
    """(key, value) of a `key: value` line, or Unreadable."""
    text = line.strip()
    if text.startswith("<<"):
        raise Unreadable(number, "merge key `<<` (YAML anchors are not read)")
    m = KEY.match(text)
    if not m:
        raise Unreadable(number, f"not a `key:` line ({text[:40]!r})")
    key = m.group(1) if m.group(1) is not None else m.group(2).replace("''", "'") if m.group(2) is not None else m.group(3)
    value = scalar(m.group(4))
    if value[:1] in ("&", "*"):
        raise Unreadable(number, "YAML anchor or alias (not read)")
    return key, value


def parse_jobs(text):
    """[(job id, line, {job-level key: (line, value)})] of a workflow, or Unreadable."""
    jobs, current = [], None
    in_jobs = seen_jobs = seen_content = False
    job_indent = key_indent = None
    block = None          # indentation of the line that opened a block scalar: deeper lines are its content
    last_key_open = False  # the previous job-level key had no value: a `-` item at the same indentation is its list
    for number, line in enumerate(text.split("\n"), 1):
        stripped = line.lstrip(" ")
        indent = len(line) - len(stripped)
        if block is not None:
            if not stripped.strip() or indent > block:
                continue
            block = None
        if not stripped.strip() or stripped.startswith("#"):
            continue
        if stripped[0] == "\t":
            if in_jobs:
                raise Unreadable(number, "tab in the indentation")
            continue
        if indent == 0 and stripped.rstrip() in ("---", "..."):
            if seen_content:
                raise Unreadable(number, "several YAML documents in one file")
            continue
        seen_content = True
        body = stripped[1:].lstrip() if stripped.startswith("- ") or stripped.rstrip() == "-" else stripped
        m = KEY.match(body.strip())
        if m and BLOCK_SCALAR.match(scalar(m.group(4))):
            block = indent
        if indent == 0:
            in_jobs = False
            if stripped.startswith("-"):
                continue  # item of a top-level list (`on:` events…)
            if stripped.startswith(("{", "[", "?")):
                raise Unreadable(number, "flow mapping or complex key at the top level")
            key, value = parse_key(line, number)
            if key == "jobs":
                if seen_jobs:
                    raise Unreadable(number, "`jobs:` written twice")
                if value:
                    raise Unreadable(number, "`jobs:` is not a block mapping (flow mapping or value on the same line)")
                in_jobs = seen_jobs = True
            continue
        if not in_jobs:
            continue
        if job_indent is None:
            job_indent = indent
        if stripped.startswith("-") and indent <= job_indent:
            raise Unreadable(number, "`jobs:` is a list, not a mapping")
        if indent < job_indent:
            raise Unreadable(number, "inconsistent indentation under `jobs:`")
        if indent == job_indent:
            job, value = parse_key(line, number)
            if value:
                raise Unreadable(number, f"job '{job}' is not a block mapping (flow mapping or value on the same line)")
            current = (job, number, {})
            jobs.append(current)
            key_indent, last_key_open = None, False
            continue
        if key_indent is None:
            key_indent = indent
        if indent < key_indent:
            raise Unreadable(number, f"inconsistent indentation in job '{current[0]}'")
        if indent > key_indent:
            continue  # deeper than the job-level keys: steps, with, env…
        if stripped.startswith("-"):
            if not last_key_open:
                raise Unreadable(number, f"list item where a key of job '{current[0]}' is expected")
            continue
        key, value = parse_key(line, number)
        current[2][key] = (number, value)
        last_key_open = not value
    return jobs


def load_settings(path):
    """(ceiling, exceptions) from `job_timeout` of the config file (absent: defaults), or ValueError."""
    if not path.is_file():
        return DEFAULT_CEILING, []
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path.name} unreadable: {exc}") from exc
    section = config.get("job_timeout", {}) if isinstance(config, dict) else None
    if not isinstance(section, dict):
        raise ValueError("`job_timeout` is not an object")
    ceiling = section.get("ceiling", DEFAULT_CEILING)
    if isinstance(ceiling, bool) or not isinstance(ceiling, (int, float)) or ceiling <= 0:
        raise ValueError(f"`job_timeout.ceiling` is not a positive number ({ceiling!r})")
    exceptions = section.get("exceptions", [])
    if not isinstance(exceptions, list) or not all(
        isinstance(e, dict) and isinstance(e.get("job"), str) and e["job"]
        and isinstance(e.get("workflow", ""), str) and isinstance(e.get("reason", ""), str)
        for e in exceptions
    ):
        raise ValueError('`job_timeout.exceptions` is not a list of {"job", "workflow", "reason"} objects')
    return ceiling, exceptions


def matches(exception, workflow, job):
    return exception["job"] == job and exception.get("workflow", "") in ("", workflow)


def show(number):
    return int(number) if float(number).is_integer() else number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="repository root (default: current folder)")
    parser.add_argument("--dir", default=DEFAULT_DIR, help=f"workflow folder under the root (default: {DEFAULT_DIR})")
    parser.add_argument("--config", help=f"settings file (default: {DEFAULT_CONFIG} under the root)")
    args = parser.parse_args(argv)
    root = pathlib.Path(args.root)
    folder = root / args.dir
    rel_dir = pathlib.PurePosixPath(args.dir)
    try:
        ceiling, exceptions = load_settings(pathlib.Path(args.config) if args.config else root / DEFAULT_CONFIG)
    except ValueError as exc:
        print(f"could not check: {exc}")
        return 2
    if not folder.is_dir():
        print(f"job-timeout: nothing checked, no {rel_dir}/ folder")
        return 0
    files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix in (".yml", ".yaml"))
    if not files:
        print(f"job-timeout: nothing checked, no workflow in {rel_dir}/")
        return 0
    errors, warnings, unchecked, accepted = [], [], [], []
    seen = []  # (file name, job id) of every job read
    count = 0
    for path in files:
        where = rel_dir / path.name
        try:
            jobs = parse_jobs(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError) as exc:
            unchecked.append(f"could not check {where}: {exc}")
            continue
        except Unreadable as exc:
            unchecked.append(f"could not check {where}:{exc.line}: {exc.reason}")
            continue
        for job, line, keys in jobs:
            seen.append((path.name, job))
            if "uses" in keys:
                continue  # reusable workflow call: `timeout-minutes` is not allowed there
            count += 1
            label = f"{where}:{line}: job '{job}'"
            if "timeout-minutes" not in keys:
                found = [e for e in exceptions if matches(e, path.name, job)]
                with_reason = [e for e in found if e.get("reason", "").strip()]
                if with_reason:
                    accepted.append(f"accepted: {label} has no timeout-minutes ({with_reason[0]['reason'].strip()})")
                    continue
                if found:
                    errors.append(f"{label}: exception refused in {DEFAULT_CONFIG} › job_timeout, it gives no reason")
                errors.append(
                    f"{label} has no timeout-minutes (GitHub cancels it only after {GITHUB_DEFAULT} minutes): "
                    f"add `timeout-minutes:` to the job, or an exception with a reason in {DEFAULT_CONFIG} › job_timeout"
                )
                continue
            key_line, value = keys["timeout-minutes"]
            if EXPRESSION.match(value):
                continue
            if not NUMBER.match(value):
                errors.append(f"{where}:{key_line}: job '{job}' timeout-minutes {value!r} is not a number or a ${{{{ }}}} expression")
            elif float(value) > ceiling:
                warnings.append(
                    f"warning: {where}:{key_line}: job '{job}' timeout-minutes {show(float(value))} is above the "
                    f"ceiling {show(ceiling)} ({DEFAULT_CONFIG} › job_timeout.ceiling): a hang still holds the runner that long"
                )
    if not unchecked:
        for e in exceptions:
            if not any(matches(e, name, job) for name, job in seen):
                scope = f" in {e['workflow']}" if e.get("workflow") else ""
                errors.append(f"{DEFAULT_CONFIG} › job_timeout: exception for unknown job '{e['job']}'{scope}: remove it")
    for line in errors + unchecked + warnings + accepted:
        print(line)
    if errors:
        print(f"job-timeout: {len(errors)} finding(s) in {rel_dir}/")
        return 1
    if unchecked:
        print(f"job-timeout: {len(unchecked)} file(s) could not be checked in {rel_dir}/: the check did not pass")
        return 2
    print(f"job-timeout: OK, {count} job(s) in {len(files)} workflow(s) of {rel_dir}/ have timeout-minutes")
    return 0


if __name__ == "__main__":
    sys.exit(main())

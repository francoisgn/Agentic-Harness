#!/usr/bin/env python3
"""Git guardrail (PreToolUse hook on Bash) of the Belayline harness.

Refuses, before execution, the commands that break the shared rules (docs/BRANCHING-RELEASE.md, docs/ESSENTIALS.md):
  - a forced `git push` (`--force`, `-f`, `--force-with-lease`, refspec `+…`);
  - a `git push` to a protected branch (list in `.harness/config.json`, key `protected_branches`);
  - `--no-verify` on `git commit` or `git push` (bypasses gitleaks and the pre-commit hooks).
A refused command exits with code 2: Claude Code blocks the call and shows the message to the agent.
The operator remains free to run the command themselves if they decide to.
Standard library only; any internal error lets the command through (the hook must never block
work through its own fault).
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys

DEFAULT_PROTECTED = ["main", "master", "develop", "beta"]
SEPARATORS = re.compile(r"&&|\|\||;|\||\n")
GIT_GLOBAL_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}


def protected_branches(project_dir: str) -> list[str]:
    """Protected branches: the project's `.harness/config.json`, otherwise the default list."""
    try:
        with open(os.path.join(project_dir, ".harness", "config.json"), encoding="utf-8") as handle:
            value = json.load(handle).get("protected_branches")
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return value
    except (OSError, ValueError, AttributeError):
        pass
    return DEFAULT_PROTECTED


def git_subcommand(tokens: list[str]) -> tuple[str | None, list[str], str | None]:
    """(subcommand, arguments, -C directory) of a `git …` command, or (None, [], None)."""
    if not tokens or os.path.basename(tokens[0]) != "git":
        return None, [], None
    index, workdir = 1, None
    while index < len(tokens) and tokens[index].startswith("-"):
        option = tokens[index]
        if option in GIT_GLOBAL_WITH_VALUE and index + 1 < len(tokens):
            if option == "-C":
                workdir = tokens[index + 1]
            index += 2
        else:
            index += 1
    if index >= len(tokens):
        return None, [], workdir
    return tokens[index], tokens[index + 1:], workdir


def current_branch(cwd: str) -> str | None:
    """Current branch of `cwd`, or None if it cannot be read."""
    try:
        out = subprocess.run(["git", "-C", cwd, "symbolic-ref", "--short", "-q", "HEAD"],
                             capture_output=True, text=True, timeout=5, check=False)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def check_push(args: list[str], protected: list[str], cwd: str) -> str | None:
    """Reason for refusing a `git push`, or None."""
    positional = []
    for arg in args:
        if arg in ("--force", "-f", "--force-if-includes") or arg.startswith("--force-with-lease"):
            return "forced push forbidden (never force-push a shared branch)"
        if arg == "--no-verify":
            return "`--no-verify` forbidden (gitleaks and the pre-commit hooks must run)"
        if arg in ("--mirror", "--all"):
            return f"`git push {arg}` forbidden (it also pushes the protected branches)"
        if not arg.startswith("-"):
            positional.append(arg)
    refspecs = positional[1:]
    for refspec in refspecs:
        if refspec.startswith("+"):
            return f"forced refspec `{refspec}` forbidden"
        destination = refspec.split(":", 1)[-1]
        destination = destination.removeprefix("refs/heads/")
        if destination in protected:
            return f"direct push to the protected branch `{destination}` forbidden: go through a PR"
    if not refspecs:
        branch = current_branch(cwd)
        if branch in protected:
            return f"push from the protected branch `{branch}` forbidden: create a `claude/<lot>` branch and a PR"
    return None


def reason_for(command: str, protected: list[str], cwd: str) -> str | None:
    """Reason for refusing the first offending subcommand of `command`, or None."""
    for part in SEPARATORS.split(command):
        try:
            tokens = shlex.split(part, comments=True)
        except ValueError:
            continue
        while tokens and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]):
            tokens = tokens[1:]  # leading VAR=… assignments
        sub, args, workdir = git_subcommand(tokens)
        where = os.path.join(cwd, workdir) if workdir else cwd
        if sub == "push":
            reason = check_push(args, protected, where)
            if reason:
                return reason
        elif sub == "commit" and ("--no-verify" in args or "-n" in args):
            return "`git commit --no-verify` forbidden (gitleaks and the pre-commit hooks must run)"
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        command = payload.get("tool_input", {}).get("command", "")
        cwd = payload.get("cwd") or os.getcwd()
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or cwd
        if not isinstance(command, str) or "git" not in command:
            return 0
        reason = reason_for(command, protected_branches(project_dir), cwd)
    except Exception:  # noqa: BLE001 (a broken hook never blocks work)
        return 0
    if reason:
        print(f"Belayline: {reason}. If this is really intended, the operator runs the command themselves "
              "(docs/BRANCHING-RELEASE.md).", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

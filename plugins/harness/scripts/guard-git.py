#!/usr/bin/env python3
"""Git guardrail (PreToolUse hook on Bash) of the Belayline harness.

Refuses, before execution, the commands that break the shared rules (BRANCHING-RELEASE.md, ESSENTIALS.md):
  - a forced `git push`: `--force`, `-f` (also grouped: `-fu`, `-uf`), `--force-with-lease`, refspec `+…`;
  - `git push --mirror`, `--all` or `--branches` (they also push the protected branches);
  - a `git push` to a protected branch (`protected_branches` in `.harness/config.json`), including `HEAD`, a bare
    `git push` or `git push origin` when the current branch is protected, and the deletion of a protected branch
    (`--delete`, `-d`, refspec `:branch`);
  - `--no-verify` on `git commit` (also `-n`, grouped or not) or `git push` (bypasses gitleaks and the hooks).
The command is split the way the shell would: separators `;` `&&` `||` `|` `&` and newlines, subshells `( … )`,
groups `{ …; }`, substitutions `$( … )` and `` `…` ``, here-documents, redirections, wrappers `env`, `command`,
`exec`, `nohup`, `time`, `nice`, `timeout`, `sudo`, `xargs`, `eval`, `bash -c` / `sh -c`, global options
`git -C <dir>` and `git -c k=v`, a preceding `cd <dir>`. If the command cannot be split (unclosed quote…), a
cautious regular expression reads the raw text instead of letting it through.
Not refused: `git push --dry-run` (`-n`), `--force-if-includes` alone, a push to an unprotected branch.

A refused command exits with code 2: Claude Code blocks the call and shows the message to the agent. The operator
remains free to run the command themselves if they decide to.
The current branch is the repository's, or the one a previous command on the same line has just selected
(`git switch [-c] <b>`, `git checkout [-b] <b>`). A wildcard refspec (`refs/heads/*`) that covers a protected branch
is refused.
Accepted limits: an agent-side hook can be bypassed (git alias, intermediate script, script passed on a shell's
standard input (`… | sh`, `bash <<EOF`), unresolved variable, push through the API); the real protection remains the
server-side ruleset (BRANCHING-RELEASE.md §Common rules).
Standard library only; an unreadable hook input or an internal error lets the command through (the hook never blocks
work through its own fault), as does a missing python3.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys

DEFAULT_PROTECTED = ["main", "master", "develop", "beta"]
DEFAULT_BRANCH_TYPES = ["lot", "fix", "feat", "chore", "docs"]
MAX_DEPTH = 6
OPERATORS = ("&&", "||", ";;", ";", "|&", "|", "&", "(", ")", "\n")
SHELL_KEYWORDS = {"{", "}", "!", "if", "then", "else", "elif", "fi", "do", "done", "while", "until", "time"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*", re.S)
CURRENT_BRANCH_EXPR = re.compile(r"^\$\(\s*git\s+(branch\s+--show-current|rev-parse\s+--abbrev-ref\s+HEAD|"
                                 r"symbolic-ref\s+--short\s+HEAD)\s*\)$")
# Global git options followed by a separate value
GIT_GLOBAL_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env",
                         "--super-prefix", "--list-cmds"}
# `git push` options followed by a separate value
PUSH_WITH_VALUE = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}
# Short `git commit` options whose value follows (attached or separate); -u and -S only take an attached value
COMMIT_SHORT_VALUE = {"m", "F", "c", "C", "t"}
COMMIT_SHORT_ATTACHED = {"u", "S"}


class ParseError(ValueError):
    """The command cannot be split (unclosed quote or parenthesis)."""


# --- Shell splitting ------------------------------------------------------------------------------------------------

def _heredoc_delimiter(text: str, i: int) -> tuple[str, bool, int]:
    """(delimiter, tabs stripped, index after the word) of a here-document; `i` points after `<<`."""
    strip = text.startswith("-", i)
    i += 1 if strip else 0
    while i < len(text) and text[i] in " \t":
        i += 1
    start = i
    while i < len(text) and text[i] not in " \t\n;&|<>()":
        i += 1
    return re.sub(r"['\"\\]", "", text[start:i]), strip, i


def _skip_heredocs(text: str, i: int, pending: list[tuple[str, bool]]) -> int:
    """Index after the bodies of the pending here-documents; `i` points just after the newline."""
    for delimiter, strip in pending:
        while i < len(text):
            end = text.find("\n", i)
            line = text[i:] if end < 0 else text[i:end]
            i = len(text) if end < 0 else end + 1
            if (line.lstrip("\t") if strip else line) == delimiter:
                break
    pending.clear()
    return i


def _substitution_end(text: str, start: int) -> int:
    """Index just after the `)` that closes the `$(` substitution opened before `start` (which points after `$(`)."""
    depth, i, quote = 1, start, None
    pending: list[tuple[str, bool]] = []
    while i < len(text):
        c = text[i]
        if quote:
            if c == "\\" and quote == '"':
                i += 1
            elif c == quote:
                quote = None
        elif c in "'\"`":
            quote = c
        elif c == "\\":
            i += 1
        elif text.startswith("<<", i) and not text.startswith("<<<", i):
            delimiter, strip, i = _heredoc_delimiter(text, i + 2)
            pending.append((delimiter, strip))
            continue
        elif c == "\n" and pending:
            i = _skip_heredocs(text, i + 1, pending)
            continue
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ParseError("unclosed substitution")


def tokenize(text: str) -> tuple[list[str], list[str]]:
    """(tokens, substitution scripts): unquoted words and operators, split the way the shell does.

    Redirections (`>f`, `2>&1`, `<<EOF` and the here-document body) are removed."""
    tokens: list[str] = []
    nested: list[str] = []
    word: list[str] = []
    in_word = False
    drop_next = False
    pending: list[tuple[str, bool]] = []
    i = 0

    def flush() -> None:
        nonlocal word, in_word, drop_next
        if in_word:
            if drop_next:
                drop_next = False
            else:
                tokens.append("".join(word))
        word, in_word = [], False

    def substitution(at: int) -> int:
        end = _substitution_end(text, at + 2)
        nested.append(text[at + 2:end - 1])
        word.append(text[at:end])
        return end

    def backquote(at: int) -> int:
        end = text.find("`", at + 1)
        if end < 0:
            raise ParseError("unclosed backquote")
        nested.append(text[at + 1:end])
        word.append(text[at:end + 1])
        return end + 1

    while i < len(text):
        c = text[i]
        if c == "\\":
            if text.startswith("\n", i + 1):
                i += 2
                continue
            if i + 1 < len(text):
                word.append(text[i + 1])
            in_word = True
            i += 2
            continue
        if c == "'":
            end = text.find("'", i + 1)
            if end < 0:
                raise ParseError("unclosed single quote")
            word.append(text[i + 1:end])
            in_word, i = True, end + 1
            continue
        if c == '"':
            i += 1
            in_word = True
            while True:
                if i >= len(text):
                    raise ParseError("unclosed double quote")
                d = text[i]
                if d == '"':
                    i += 1
                    break
                if d == "\\" and i + 1 < len(text) and text[i + 1] in '"\\$`\n':
                    word.append(text[i + 1])
                    i += 2
                elif text.startswith("$(", i):
                    i = substitution(i)
                elif d == "`":
                    i = backquote(i)
                else:
                    word.append(d)
                    i += 1
            continue
        if text.startswith("$(", i):
            in_word = True
            i = substitution(i)
            continue
        if c == "`":
            in_word = True
            i = backquote(i)
            continue
        if c == "#" and not in_word:
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
            continue
        if c in "<>":
            if in_word and "".join(word).isdigit():
                word, in_word = [], False  # file descriptor (`2>`)
            flush()
            if text.startswith("<<", i) and not text.startswith("<<<", i):
                delimiter, strip, i = _heredoc_delimiter(text, i + 2)
                pending.append((delimiter, strip))
                continue
            while i < len(text) and text[i] in "<>&|":
                i += 1
            if i < len(text) and (text[i].isdigit() or text[i] == "-") and text[i - 1] == "&":
                while i < len(text) and (text[i].isdigit() or text[i] == "-"):
                    i += 1  # `>&1`, `>&-`: no target word
            else:
                drop_next = True
            continue
        operator = next((op for op in OPERATORS if text.startswith(op, i)), None)
        if operator:
            flush()
            tokens.append(";" if operator == "\n" else operator)
            i += len(operator)
            if operator == "\n" and pending:
                i = _skip_heredocs(text, i, pending)
            continue
        if c in " \t\r":
            flush()
            i += 1
            continue
        word.append(c)
        in_word = True
        i += 1
    flush()
    return tokens, nested


def simple_commands(tokens: list[str]) -> list[list[str]]:
    """Simple commands (word lists) separated by the operators; leading shell keywords removed."""
    commands, current = [], []
    for token in tokens:
        if token in OPERATORS:
            if current:
                commands.append(current)
            current = []
        else:
            current.append(token)
    if current:
        commands.append(current)
    cleaned = []
    for words in commands:
        while words and words[0] in SHELL_KEYWORDS:
            words = words[1:]
        while words and words[-1] == "}":
            words = words[:-1]
        if words:
            cleaned.append(words)
    return cleaned


# --- Wrappers -------------------------------------------------------------------------------------------------------

def _skip_options(words: list[str], with_value: set[str]) -> list[str]:
    i = 0
    while i < len(words) and words[i].startswith("-") and words[i] != "-":
        if words[i] == "--":
            return words[i + 1:]
        i += 2 if words[i] in with_value else 1
    return words[i:]


def unwrap(words: list[str]) -> tuple[list[str], str | None]:
    """(real command, script to analyse) after the assignments and wrappers; a script for `eval`, `bash -c`."""
    for _ in range(MAX_DEPTH * 2):
        while words and ASSIGNMENT.fullmatch(words[0]):
            words = words[1:]
        if not words:
            return [], None
        head = os.path.basename(words[0])
        rest = words[1:]
        if head == "env":
            words = _skip_options(rest, {"-u", "--unset", "-C", "--chdir"})
        elif head == "command":
            if rest[:1] and rest[0] in ("-v", "-V"):
                return [], None  # lookup only, nothing is run
            words = _skip_options(rest, set())
        elif head in ("exec", "nohup", "builtin"):
            words = _skip_options(rest, {"-a"})
        elif head == "time":
            words = _skip_options(rest, {"-f", "-o"})
        elif head == "nice":
            words = _skip_options(rest, {"-n"})
        elif head == "timeout":
            words = _skip_options(rest, {"-s", "--signal", "-k", "--kill-after"})[1:]  # then the duration
        elif head == "sudo":
            words = _skip_options(rest, {"-u", "-g", "-C", "-D", "-h", "-p", "-r", "-t", "-U"})
        elif head == "xargs":
            words = _skip_options(rest, {"-I", "-L", "-n", "-P", "-d", "-a", "-E", "-s", "--arg-file",
                                         "--delimiter", "--max-args", "--max-procs", "--max-lines"})
        elif head == "eval":
            return [], " ".join(rest)
        elif head in SHELLS:
            for index, arg in enumerate(rest):
                if not arg.startswith("-"):
                    break
                if not arg.startswith("--") and "c" in arg[1:]:
                    return [], rest[index + 1] if index + 1 < len(rest) else None
            return [], None
        else:
            return words, None
    return words, None


# --- git ------------------------------------------------------------------------------------------------------------

def git_subcommand(words: list[str]) -> tuple[str | None, list[str], list[str]]:
    """(subcommand, arguments, -C directories) of a `git …` command, or (None, [], [])."""
    if not words or os.path.basename(words[0]) != "git":
        return None, [], []
    index, dirs = 1, []
    while index < len(words) and words[index].startswith("-"):
        option = words[index]
        if option in GIT_GLOBAL_WITH_VALUE and index + 1 < len(words):
            if option == "-C":
                dirs.append(words[index + 1])
            index += 2
        else:
            index += 1
    if index >= len(words):
        return None, [], dirs
    return words[index], words[index + 1:], dirs


def _long(arg: str, full: str, minimum: int) -> bool:
    """`arg` names the long option `full` (git accepts an unambiguous prefix; `minimum` makes it unambiguous)."""
    name = arg.split("=", 1)[0]
    return len(name) >= minimum and full.startswith(name)


def current_branch(cwd: str) -> str | None:
    """Current branch of `cwd` (`git rev-parse --abbrev-ref HEAD`, or `symbolic-ref` for a branch with no commit
    yet), or None if it cannot be read (detached HEAD, not a repository, git missing)."""
    for args in (["rev-parse", "--abbrev-ref", "HEAD"], ["symbolic-ref", "--short", "-q", "HEAD"]):
        try:
            out = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=5, check=False)
        except (OSError, subprocess.SubprocessError, ValueError):
            return None
        branch = out.stdout.strip()
        if out.returncode == 0 and branch and branch != "HEAD":
            return branch
    return None


def _branch_of(ref: str, current) -> str | None:
    """Branch that `ref` names; `HEAD`, `@` and `$(git branch --show-current)`: the current branch (`current()`)."""
    if ref in ("HEAD", "@") or CURRENT_BRANCH_EXPR.match(ref):
        return current()
    return ref.removeprefix("refs/heads/")


def _protected_match(branch: str | None, protected: list[str]) -> str | None:
    """The protected branch that `branch` names (exact name, or wildcard pattern that covers it), otherwise None."""
    if branch is None:
        return None
    if branch in protected:
        return branch
    if "*" in branch:
        return next((name for name in protected if fnmatch.fnmatchcase(name, branch)), None)
    return None


def check_push(args: list[str], protected: list[str], cwd: str, advice: str, head: str | None = None) -> str | None:
    """Reason for refusing a `git push`, or None. `head`: current branch already known from the command line (an
    empty string for a detached HEAD); None: read it in `cwd`."""
    def current() -> str | None:
        return (head or None) if head is not None else current_branch(cwd)
    positional: list[str] = []
    force = no_verify = dry_run = delete = repo_option = tags = False
    wide = None
    index = 0
    while index < len(args):
        arg = args[index]
        index += 1
        if arg == "--":
            positional += args[index:]
            break
        if arg.startswith("--"):
            name = arg.split("=", 1)[0]
            if name in PUSH_WITH_VALUE:
                repo_option = repo_option or name == "--repo"
                index += 0 if "=" in arg else 1
            elif arg == "--force" or _long(arg, "--force-with-lease", 9):
                force = True
            elif _long(arg, "--no-verify", 9):
                no_verify = True
            elif _long(arg, "--dry-run", 4):
                dry_run = True
            elif _long(arg, "--no-dry-run", 7):
                dry_run = False
            elif arg == "--tags":
                tags = True
            elif _long(arg, "--delete", 4):
                delete = True
            elif _long(arg, "--mirror", 3):
                wide = "--mirror"
            elif _long(arg, "--all", 4) or _long(arg, "--branches", 4):
                wide = "--all" if name.startswith("--a") else "--branches"
            continue
        if arg.startswith("-") and len(arg) > 1:
            letters = arg[1:]
            for position, letter in enumerate(letters):
                if letter == "f":
                    force = True
                elif letter == "n":
                    dry_run = True
                elif letter == "d":
                    delete = True
                elif letter == "o":
                    if position == len(letters) - 1:
                        index += 1  # separate value
                    break
            continue
        positional.append(arg)

    if dry_run:
        return None
    if force:
        return "forced push forbidden (never force-push a shared branch)"
    if no_verify:
        return "`git push --no-verify` forbidden (gitleaks and the pre-commit hooks must run)"
    if wide:
        return f"`git push {wide}` forbidden (it also pushes the protected branches)"

    refspecs = positional if repo_option else positional[1:]
    for refspec in refspecs:
        if refspec.startswith("+"):
            return f"forced refspec `{refspec}` forbidden"
        if delete or refspec.startswith(":"):
            branch = _protected_match(_branch_of(refspec.lstrip(":"), current), protected)
            if branch:
                return f"deletion of the protected branch `{branch}` forbidden"
            continue
        source, _, destination = refspec.partition(":")
        branch = _protected_match(_branch_of(destination or source, current), protected)
        if branch:
            return f"direct push to the protected branch `{branch}` forbidden: {advice}"
    if not refspecs and not delete and not tags:  # `--tags` alone only pushes the tags
        branch = current()
        if branch in protected:
            return f"push from the protected branch `{branch}` forbidden: {advice}"
    return None


def local_branch_exists(cwd: str, name: str) -> bool:
    try:
        out = subprocess.run(["git", "-C", cwd, "rev-parse", "--verify", "--quiet", f"refs/heads/{name}"],
                             capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return out.returncode == 0


def switched_branch(sub: str, args: list[str]) -> str | None:
    """Branch that `git switch|checkout <args>` makes current ("" for a detached HEAD), or None if unknown."""
    create = {"-c", "-C", "--create", "--force-create"} if sub == "switch" else {"-b", "-B", "--orphan"}
    positional: list[str] = []
    for index, arg in enumerate(args):
        if arg == "--":
            return None if sub == "checkout" else (args[index + 1] if index + 1 < len(args) else None)
        if arg in create:
            return args[index + 1] if index + 1 < len(args) else None
        if arg.split("=", 1)[0] in ("--create", "--force-create", "--orphan") and "=" in arg:
            return arg.split("=", 1)[1]
        if arg in ("--detach", "-d") and sub == "switch" or arg == "--detach":
            return ""
        if not arg.startswith("-"):
            positional.append(arg)
    if sub == "checkout" and len(positional) != 1:
        return None  # `checkout <commit> <files>` does not change branch
    return positional[0] if positional else None


def check_commit(args: list[str]) -> str | None:
    """Reason for refusing a `git commit`, or None."""
    message = "`git commit --no-verify` (`-n`) forbidden (gitleaks and the pre-commit hooks must run)"
    index = 0
    while index < len(args):
        arg = args[index]
        index += 1
        if arg == "--":
            break
        if arg.startswith("--"):
            if _long(arg, "--no-verify", 9):
                return message
            continue
        if arg.startswith("-") and len(arg) > 1:
            letters = arg[1:]
            for position, letter in enumerate(letters):
                if letter == "n":
                    return message
                if letter in COMMIT_SHORT_ATTACHED:
                    break
                if letter in COMMIT_SHORT_VALUE:
                    if position == len(letters) - 1:
                        index += 1  # separate value: in `-m -n`, `-n` is the message
                    break
    return None


# --- Analysis -------------------------------------------------------------------------------------------------------

RAW_PUSH = re.compile(r"\bgit\b[^;&|\n]*?\bpush\b(?P<args>[^;&|\n]*)")
RAW_COMMIT = re.compile(r"\bgit\b[^;&|\n]*?\bcommit\b(?P<args>[^;&|\n]*)")


def raw_reason(command: str, protected: list[str], cwd: str, advice: str) -> str | None:
    """Cautious reading of the raw text when the command cannot be split (prefers a wrong refusal)."""
    for match in RAW_PUSH.finditer(command):
        args = match.group("args")
        if re.search(r"(^|\s)(--dry-run|-[A-Za-z]*n[A-Za-z]*)(\s|$)", args):
            continue
        if re.search(r"(^|\s)(--force(?!-if-includes)|-[A-Za-z]*f[A-Za-z]*\b)|(^|\s)['\"]?\+\S", args):
            return "forced push forbidden (never force-push a shared branch)"
        if re.search(r"--no-verify|--mirror|(^|\s)--(all|branches)\b", args):
            return "push forbidden (`--no-verify`, `--mirror`, `--all` or `--branches`)"
        for branch in protected:
            if re.search(r"(^|[\s:'\"/])" + re.escape(branch) + r"(['\"]?(\s|$))", args):
                return f"direct push to the protected branch `{branch}` forbidden: {advice}"
        if re.fullmatch(r"\s*(\S+\s*)?(HEAD\s*)?['\"]?\s*", args):
            branch = current_branch(cwd)
            if branch in protected:
                return f"push from the protected branch `{branch}` forbidden: {advice}"
    for match in RAW_COMMIT.finditer(command):
        if re.search(r"--no-verify|(^|\s)-[A-Za-z]*n", match.group("args")):
            return "`git commit --no-verify` (`-n`) forbidden (gitleaks and the pre-commit hooks must run)"
    return None


def reason_for(command: str, protected: list[str], cwd: str, advice: str = "go through a branch and a PR",
               depth: int = 0) -> str | None:
    """Reason for refusing the first offending command of `command`, or None."""
    if depth > MAX_DEPTH or "git" not in re.sub(r"['\"\\]", "", command):
        return None
    try:
        tokens, nested = tokenize(command)
    except ParseError:
        return raw_reason(command, protected, cwd, advice)
    for script in nested:
        reason = reason_for(script, protected, cwd, advice, depth + 1)
        if reason:
            return reason
    base = cwd
    heads: dict[str, str] = {}  # directory → branch selected earlier on the line ("": detached HEAD)
    for words in simple_commands(tokens):
        words, script = unwrap(words)
        if script is not None:
            reason = reason_for(script, protected, base, advice, depth + 1)
            if reason:
                return reason
            continue
        if words[:1] == ["cd"] and len(words) == 2 and not words[1].startswith("-"):
            base = os.path.join(base, os.path.expanduser(words[1]))
            continue
        sub, args, dirs = git_subcommand(words)
        where = base
        for directory in dirs:
            where = os.path.join(where, os.path.expanduser(directory))
        if sub in ("switch", "checkout"):
            switched = switched_branch(sub, args)
            if sub == "checkout" and switched and not any(a in ("-b", "-B", "--orphan") or a.startswith("--orphan=")
                                                          for a in args):
                # `checkout <name>` changes branch only if <name> is one (otherwise it is a file)
                switched = switched if switched in protected or local_branch_exists(where, switched) else None
            if switched is not None:
                heads[os.path.normpath(where)] = switched
            continue
        if sub == "push":
            reason = check_push(args, protected, where, advice, heads.get(os.path.normpath(where)))
        elif sub == "commit":
            reason = check_commit(args)
        else:
            reason = None
        if reason:
            return reason
    return None


# --- Hook -----------------------------------------------------------------------------------------------------------

def load_config(project_dir: str) -> dict:
    """The project's `.harness/config.json`, or {} if it is missing or unreadable."""
    try:
        with open(os.path.join(project_dir, ".harness", "config.json"), encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _string_list(value: object, default: list[str]) -> list[str]:
    if isinstance(value, list) and value and all(isinstance(item, str) for item in value):
        return value
    return default


def doc_path(project_dir: str) -> str:
    """BRANCHING-RELEASE.md as the agent finds it: the vendored copy, otherwise the harness's."""
    if os.path.isfile(os.path.join(project_dir, ".harness", "docs", "BRANCHING-RELEASE.md")):
        return ".harness/docs/BRANCHING-RELEASE.md"
    return "docs/BRANCHING-RELEASE.md of the Belayline harness"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        command = payload.get("tool_input", {}).get("command", "")
        cwd = payload.get("cwd") or os.getcwd()
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or cwd
        if not isinstance(command, str) or "git" not in re.sub(r"['\"\\]", "", command):
            return 0
        config = load_config(project_dir)
        protected = _string_list(config.get("protected_branches"), DEFAULT_PROTECTED)
        types = _string_list(config.get("branch_types"), DEFAULT_BRANCH_TYPES)
        advice = f"create a `<type>/<short-name>` branch (types: {', '.join(types)}) and a PR"
        reason = reason_for(command, protected, cwd, advice)
        doc = doc_path(project_dir)
    except Exception:  # noqa: BLE001 (a broken hook never blocks work)
        return 0
    if reason:
        print(f"Belayline: {reason}. If this is really intended, the operator runs the command themselves "
              f"({doc}).", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

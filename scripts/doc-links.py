#!/usr/bin/env python3
"""Checks that relative links in Markdown resolve (standard library only).

For every `.md` file of the repository (`git ls-files`, or a walk outside git):
- a relative link (inline `[t](path)`, image, reference definition `[r]: path`, HTML `href` / `src`) points to a
  file or folder that exists; `/path` is read from the repository root, like GitHub does;
- a link to another Markdown file with an anchor (`OTHER.md#section`) names a heading of that file (GitHub slugs,
  `-1`, `-2` for repeated headings) or an explicit `<a name|id="…">`.
Left alone: external links (`https:`, `mailto:`…), in-file anchors (`#section`, already checked by markdownlint
MD051), anchors into non-Markdown files (`tool.py#L10`), code spans, fenced blocks and HTML comments.
Excluded by default: `.harness/**` (vendored, checked in the harness itself), `node_modules`, `.build`.
Usage: doc-links.py [--root <repository>] [--exclude <glob>]... [path...]   (exits 1 on any broken link, lists all)
"""
import argparse
import fnmatch
import pathlib
import re
import subprocess
import sys
import urllib.parse

DEFAULT_EXCLUDES = (".harness/**", "**/node_modules/**", "node_modules/**", "**/.build/**", ".build/**")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
CODE_SPAN = re.compile(r"(`+)(?:(?!\1).)+?\1")
COMMENT = re.compile(r"<!--.*?-->", re.S)
TEXT = r"\[(?:[^\[\]]|\[[^\]]*\])*\]"
INLINE = re.compile(r"!?" + TEXT + r"\(\s*(?:<([^>]*)>|([^)\s]+))(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)")
REFERENCE = re.compile(r"^ {0,3}\[[^\]]+\]:\s*(?:<([^>]*)>|(\S+))")
HTML_LINK = re.compile(r"<(?:a|img)\b[^>]*?\b(?:href|src)\s*=\s*[\"']([^\"']*)[\"']", re.I)
HTML_ANCHOR = re.compile(r"<[a-z][^>]*?\b(?:name|id)\s*=\s*[\"']([^\"']+)[\"']", re.I)
ATX = re.compile(r"^ {0,3}#{1,6}[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$")
SETEXT = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def slug(text):
    """GitHub anchor of a heading: inline markup dropped, lowercased, punctuation removed, spaces to hyphens."""
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)  # link or image → its text
    text = re.sub(r"<[^>]+>", "", text)                       # HTML tags
    text = text.replace("`", "").lower()
    text = re.sub(r"[^\w\- ]", "", text)                      # \w is Unicode: accented letters stay
    return text.replace(" ", "-")


def strip_code(lines, spans=True):
    """The lines with fenced blocks, HTML comments and (if `spans`) code spans blanked (line numbers kept)."""
    out, fence = [], None
    for line in lines:
        m = FENCE.match(line)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not line[m.end():].strip():
                fence = None
            out.append("")
            continue
        if m:
            fence = m.group(1)
            out.append("")
            continue
        out.append(CODE_SPAN.sub("", line) if spans else line)
    text = COMMENT.sub(lambda c: "\n" * c.group(0).count("\n"), "\n".join(out))
    return text.split("\n")


def anchors(path, cache):
    """Every anchor a Markdown file offers: heading slugs (numbered when repeated) and explicit HTML anchors."""
    if path not in cache:
        found, seen = set(), {}
        lines = strip_code(path.read_text(encoding="utf-8", errors="replace").splitlines(), spans=False)
        for n, line in enumerate(lines):
            title = None
            m = ATX.match(line)
            if m:
                title = m.group(1)
            elif n and SETEXT.match(line) and lines[n - 1].strip() and not ATX.match(lines[n - 1]):
                title = lines[n - 1].strip()
            if title is not None:
                base = slug(title)
                count = seen.get(base, 0)
                seen[base] = count + 1
                found.add(base if not count else f"{base}-{count}")
            found.update(HTML_ANCHOR.findall(line))
        cache[path] = found
    return cache[path]


def targets(line):
    """The link targets written on one (already code-stripped) line."""
    for m in INLINE.finditer(line):
        yield m.group(1) if m.group(1) is not None else m.group(2)
    m = REFERENCE.match(line)
    if m:
        yield m.group(1) if m.group(1) is not None else m.group(2)
    yield from HTML_LINK.findall(line)


def check_file(root, path, cache):
    """Broken relative links of one Markdown file, as `file:line: target: problem` strings."""
    errors = []
    rel = path.relative_to(root).as_posix()
    lines = strip_code(path.read_text(encoding="utf-8", errors="replace").splitlines())
    for n, line in enumerate(lines, 1):
        for target in targets(line):
            target = target.strip()
            if not target or target.startswith(("#", "//")) or SCHEME.match(target):
                continue
            raw, _, anchor = target.partition("#")
            raw = urllib.parse.unquote(raw.split("?", 1)[0])
            dest = (root / raw.lstrip("/")) if raw.startswith("/") else (path.parent / raw)
            dest = pathlib.Path(*_normalise(dest.parts))
            try:
                dest.relative_to(root)
            except ValueError:
                errors.append(f"{rel}:{n}: {target}: outside the repository")
                continue
            if not dest.exists():
                errors.append(f"{rel}:{n}: {target}: file not found")
            elif anchor and dest.is_file() and dest.suffix.lower() == ".md":
                if urllib.parse.unquote(anchor).lower() not in anchors(dest, cache):
                    errors.append(f"{rel}:{n}: {target}: anchor not found")
    return errors


def _normalise(parts):
    """Resolve `.` and `..` without following symbolic links (a vendored link keeps its written path)."""
    out = []
    for part in parts:
        if part == "..":
            if len(out) > 1:
                out.pop()
        elif part != ".":
            out.append(part)
    return out


def markdown_files(root, paths, excludes):
    """The `.md` files to check: the given paths (files or folders), else the repository's, minus the excludes."""
    if paths:
        found = []
        for p in paths:
            p = (root / p) if not pathlib.Path(p).is_absolute() else pathlib.Path(p)
            found.extend([p] if p.is_file() else sorted(p.rglob("*.md")))
    else:
        try:
            listed = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--", "*.md"], check=True,
                                    capture_output=True, text=True).stdout.split("\0")
            found = [root / f for f in listed if f]
        except (OSError, subprocess.CalledProcessError):
            found = sorted(root.rglob("*.md"))
    keep = []
    for f in found:
        rel = f.resolve().relative_to(root).as_posix() if f.resolve().is_relative_to(root) else f.as_posix()
        if f.is_file() and not f.is_symlink() and not any(fnmatch.fnmatch(rel, g) for g in excludes):
            keep.append(f)
    return keep


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="repository root (default: current folder)")
    parser.add_argument("--exclude", action="append", default=[], help="glob relative to the root (repeatable)")
    parser.add_argument("paths", nargs="*", help="files or folders to check (default: every tracked .md file)")
    args = parser.parse_args(argv)
    root = pathlib.Path(args.root).resolve()
    files = markdown_files(root, args.paths, DEFAULT_EXCLUDES + tuple(args.exclude))
    cache, errors = {}, []
    for f in files:
        errors.extend(check_file(root, pathlib.Path(*_normalise(f.absolute().parts)), cache))
    for e in errors:
        print(e)
    if errors:
        print(f"{len(errors)} broken link(s) in {len(files)} Markdown file(s) (relative links and cross-file anchors)")
        return 1
    print(f"{len(files)} Markdown file(s): every relative link and cross-file anchor resolves")
    return 0


if __name__ == "__main__":
    sys.exit(main())

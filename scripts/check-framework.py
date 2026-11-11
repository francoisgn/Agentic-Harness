#!/usr/bin/env python3
"""Consistency checks of the harness, run by CI (standard library only).

- skills: `name` = directory name, `description` present;
- agents: `name` = file name, `description`, `tools`, known `model`; compliance agents with their sections;
- manifest: every source exists;
- labels: unique names, `axis: value` format (or one of the plain names), the exclusive axes are all present;
- repository identity (CONVENTIONS.md §Repository identity): description, topics, README banner, social preview;
- anti-bloat (CONTRIBUTING.md §Size limits): body size of skills, agents and ESSENTIALS.md; doc links that must resolve;
  skill/agent counts in the README and the skill list of `templates/CLAUDE.md.block` = what `plugins/harness/` holds;
- agent naming (ORCHESTRATION.md §7): every example matches the published regular expression;
- no dependency (CONTRIBUTING.md §What does not go in): no dependency manifest or lockfile outside `templates/`.
Usage: check-framework.py [--root <repository>]   (exits 1 on any gap, lists every gap)
"""
import argparse
import importlib.util
import json
import pathlib
import fnmatch
import re
import subprocess
import sys

GENERIC_REVIEWER = "compliance-reviewer"
MODELS = {"haiku", "sonnet", "opus", "fable", "inherit"}
COMPLIANCE_SECTIONS = ("## Role and limits", "## When to step in", "## What I check", "## Expected evidence",
                       "## Response format", "## Sources")
LABEL_RE = re.compile(r"^[a-z]+: [a-z-]+$")
PLAIN_LABELS = {"direct-pr", "dependencies"}
EXCLUSIVE_AXES = ("status", "type", "priority", "difficulty")

# Size limits, in characters of the body (after the frontmatter). Text written by agents accumulates and every loaded
# line costs context, so a file over its limit is a gap: shorten it, or list it in SIZE_EXCEPTIONS with the reason.
# Measured 2026-11: largest skill 4.2 kB, largest agent 4.4 kB, ESSENTIALS.md 5.2 kB.
SKILL_BODY_LIMIT = 5000      # largest skill (4.2 kB) + ~20 %: a skill loads whole when invoked
AGENT_BODY_LIMIT = 5500      # largest agent (4.4 kB) + ~25 %: compliance agents carry six mandatory sections
ESSENTIALS_BODY_LIMIT = 5600  # current size (5.2 kB) + ~7 %: tighter, because it is loaded in EVERY session
# Path relative to the root -> (limit, reason). Empty on purpose: a file that needs more is listed here, never by
# raising a global limit above.
SIZE_EXCEPTIONS = {}
# The harness holds no dependency (SCOPE.md, CONTRIBUTING.md): a manifest or lockfile is a gap wherever it is tracked,
# except under templates/, which a project copies and may need one day.
DEPENDENCY_MANIFESTS = ("package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "requirements*.txt",
                        "pyproject.toml", "Pipfile*", "Gemfile*", "go.mod", "Cargo.toml")
DOC_LINK_RE = re.compile(r"(?:\.harness|\$\{CLAUDE_PLUGIN_ROOT\})/docs/([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*)")


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 4)
    meta = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta, text[end + 4:]


def size_gaps(root, path, limit, body):
    rel = path.relative_to(root).as_posix()
    limit = SIZE_EXCEPTIONS.get(rel, (limit, ""))[0]
    if len(body) > limit:
        return [f"{rel}: body is {len(body)} characters, limit {limit} (shorten it, or list an exception with its reason)"]
    return []


def anti_bloat_gaps(root):
    """Body sizes, doc links of skills and agents, and the counts announced by README and CLAUDE.md.block."""
    errors = []
    plugin = root / "plugins/harness"
    skills = sorted((plugin / "skills").glob("*/SKILL.md"))
    agents = sorted((plugin / "agents").glob("*.md"))
    for path, limit in [(p, SKILL_BODY_LIMIT) for p in skills] + [(p, AGENT_BODY_LIMIT) for p in agents]:
        meta, body = frontmatter(path)
        errors += size_gaps(root, path, limit, body)
        for m in DOC_LINK_RE.finditer(body):
            if not (root / "docs" / m.group(1)).exists():
                errors.append(f"{path.relative_to(root).as_posix()}: links to docs/{m.group(1)}, which does not exist")
    essentials = root / "docs/ESSENTIALS.md"
    if essentials.is_file():
        errors += size_gaps(root, essentials, ESSENTIALS_BODY_LIMIT, frontmatter(essentials)[1])

    readme = root / "README.md"
    if readme.is_file():
        m = re.search(r"(\d+) skills, (\d+) agents", readme.read_text(encoding="utf-8"))
        if not m:
            errors.append("README.md: \"<n> skills, <m> agents\" not found")
        else:
            if int(m.group(1)) != len(skills):
                errors.append(f"README.md: announces {m.group(1)} skills, plugins/harness/ holds {len(skills)}")
            if int(m.group(2)) != len(agents):
                errors.append(f"README.md: announces {m.group(2)} agents, plugins/harness/ holds {len(agents)}")
    block = root / "templates/CLAUDE.md.block"
    if block.is_file():
        m = re.search(r"^Skills: (.+)$", block.read_text(encoding="utf-8"), re.M)
        listed = set(re.findall(r"`/([a-z0-9-]+)`", m.group(1))) if m else set()
        actual = {p.parent.name for p in skills}
        errors += [f"templates/CLAUDE.md.block: skill /{n} is not in the skill list" for n in sorted(actual - listed)]
        errors += [f"templates/CLAUDE.md.block: lists /{n}, which plugins/harness/skills/ does not hold"
                   for n in sorted(listed - actual)]
    return errors


def tracked_files(root):
    """Files tracked by git under `root`; every file (outside .git) when `root` is not a git work tree."""
    try:
        top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        if top.returncode == 0 and pathlib.Path(top.stdout.strip()).resolve() == pathlib.Path(root).resolve():
            out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, text=True, check=True)
            return [f for f in out.stdout.split("\0") if f]
    except (OSError, subprocess.CalledProcessError):
        pass
    return [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]


def dependency_manifest_gaps(root):
    return [f"{rel}: dependency manifest or lockfile; the harness holds no dependency (CONTRIBUTING.md)"
            for rel in sorted(tracked_files(root)) if not rel.startswith("templates/")
            and any(fnmatch.fnmatchcase(rel.rsplit("/", 1)[-1], pat) for pat in DEPENDENCY_MANIFESTS)]


def pull_request_job_names(text):
    """Check names a workflow publishes on a PR: workflow triggered by `pull_request` (not `_target`),
    direct jobs only (the check of a reusable job is named `caller / called`)."""
    # `on` key possibly quoted; trailing comment ignored
    on_key = r"^(?:on|'on'|\"on\"):"
    inline = re.search(on_key + r"[ \t]*([^#\s][^#\n]*)", text, re.M)  # `on: pull_request`, `on: [push, pull_request]`
    if inline:
        if not re.search(r"(?<![\w-])pull_request(?![\w-])", inline.group(1)):
            return set()
    else:
        on_block = re.search(on_key + r"[ \t]*(?:#.*)?\n((?:[ \t]+.*\n|\s*\n)*)", text, re.M)
        if not on_block:
            return set()
        # Only the direct child keys of `on` are events (not a `pull_request` input of a dispatch)
        lines = [ln for ln in on_block.group(1).splitlines() if ln.strip() and not ln.strip().startswith("#")]
        if not lines:
            return set()
        indent = min(len(ln) - len(ln.lstrip()) for ln in lines)
        if not any(len(ln) - len(ln.lstrip()) == indent and re.match(r"""\s*['"]?pull_request['"]?:""", ln) for ln in lines):
            return set()
    jobs = text[text.find("\njobs:"):]
    names = set()
    for block in re.split(r"\n  (?=[A-Za-z0-9_-]+:\s*\n)", jobs)[1:]:
        if re.search(r"^    uses:", block, re.M):
            continue
        m = re.search(r"^    name:\s*(.+?)\s*$", block, re.M)
        if m:
            names.add(m.group(1).strip("\"'"))
    return names


def check(root):
    errors = []
    for skill in sorted((root / "plugins/harness/skills").glob("*/SKILL.md")):
        meta, _ = frontmatter(skill)
        rel = skill.relative_to(root)
        if meta is None or meta.get("name") != skill.parent.name:
            errors.append(f"{rel}: `name` must be {skill.parent.name}")
        if not (meta or {}).get("description"):
            errors.append(f"{rel}: `description` missing")

    for agent in sorted((root / "plugins/harness/agents").glob("*.md")):
        meta, body = frontmatter(agent)
        rel = agent.relative_to(root)
        meta = meta or {}
        if meta.get("name") != agent.stem:
            errors.append(f"{rel}: `name` must be {agent.stem}")
        for key in ("description", "tools"):
            if not meta.get(key):
                errors.append(f"{rel}: `{key}` missing")
        if meta.get("model") not in MODELS:
            errors.append(f"{rel}: `model` must be one of {sorted(MODELS)}")
        if agent.stem.startswith("compliance-"):
            if agent.stem != GENERIC_REVIEWER:  # the generic one takes its sections from the project spec
                errors += [f"{rel}: section \"{s}\" missing" for s in COMPLIANCE_SECTIONS if s not in body]
            if "Edit" in meta.get("tools", "") or "Write" in meta.get("tools", ""):
                errors.append(f"{rel}: a compliance reviewer stays read-only (neither Edit nor Write)")

    for n, line in enumerate((root / "harness.manifest").read_text(encoding="utf-8").splitlines(), 1):
        parts = line.split()
        if not parts or parts[0].startswith("#"):
            continue
        if len(parts) < 2:
            errors.append(f"harness.manifest:{n}: malformed line (MODE SOURCE DESTINATION expected)")
            continue
        if parts[1] == "-":
            continue
        if not (root / parts[1]).exists():
            errors.append(f"harness.manifest:{n}: source not found {parts[1]}")

    names = [label["name"] for label in json.loads((root / "templates/.github/labels.json").read_text(encoding="utf-8"))]
    errors += [f"labels.json: duplicate label \"{x}\"" for x in sorted({x for x in names if names.count(x) > 1})]
    errors += [f"labels.json: label \"{x}\" is neither `axis: value` (lowercase ASCII) nor one of {sorted(PLAIN_LABELS)}"
               for x in names if not LABEL_RE.match(x) and x not in PLAIN_LABELS]
    axes = {x.split(":", 1)[0] for x in names if LABEL_RE.match(x)}
    errors += [f"labels.json: no label on the exclusive axis `{axis}:`" for axis in EXCLUSIVE_AXES if axis not in axes]

    # Required checks of the ruleset = real job names, otherwise no PR merges any more (CI-BUDGET.md §4)
    settings = root / ".github/repo-settings.json"
    if settings.is_file():
        job_names = set()
        for wf in (root / ".github/workflows").glob("*.yml"):
            job_names |= pull_request_job_names(wf.read_text(encoding="utf-8"))
        for ruleset in json.loads(settings.read_text(encoding="utf-8")).get("rulesets", []):
            for rule in ruleset.get("rules", []):
                for chk in (rule.get("parameters") or {}).get("required_status_checks", []):
                    if chk["context"] not in job_names:
                        errors.append(f".github/repo-settings.json: required check \"{chk['context']}\" is not among "
                                      f"the jobs of .github/workflows ({sorted(job_names)})")

    # Repository identity (CONVENTIONS.md §Repository identity): the harness applies its own rule
    if settings.is_file():
        spec = importlib.util.spec_from_file_location("repo_settings", root / "scripts/repo-settings.py")
        rs = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rs)
        errors += [f".github/repo-settings.json: {gap}"
                   for gap in rs.identity_gaps(json.loads(settings.read_text(encoding="utf-8")))]
    social = root / "docs/assets/social-preview.png"
    banners = [f"docs/assets/banner.{ext}" for ext in ("svg", "png") if (root / f"docs/assets/banner.{ext}").is_file()]
    readme = root / "README.md"
    if not banners:
        errors.append("docs/assets/banner.svg (or .png): README banner not found")
    elif readme.is_file() and not any(b in readme.read_text(encoding="utf-8") for b in banners):
        errors.append(f"README.md: the banner {banners[0]} is not shown in it")
    if not social.is_file():
        errors.append("docs/assets/social-preview.png: social preview not found")
    else:
        head = social.read_bytes()[:24]  # PNG signature, then IHDR: width and height on 4 bytes each
        size = (int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big"))
        if head[:8] != b"\x89PNG\r\n\x1a\n" or size != (1280, 640):
            errors.append(f"docs/assets/social-preview.png: 1280×640 PNG expected (read: {size[0]}×{size[1]})")
        elif social.stat().st_size >= 1_000_000:
            errors.append("docs/assets/social-preview.png: must weigh less than 1 MB (GitHub limit)")

    orch = (root / "docs/ORCHESTRATION.md").read_text(encoding="utf-8")
    section = orch[orch.find("## 7."):]
    m = re.search(r"Check: `(\^.+\$)`", section)
    if not m:
        errors.append("docs/ORCHESTRATION.md §7: check regular expression not found")
    else:
        rx = re.compile(m.group(1))
        examples = re.findall(r"`([a-z0-9-]+\.[^`\s]+)`", section[section.find("Examples"):section.find("| Role")])
        if not examples:
            errors.append("docs/ORCHESTRATION.md §7: no identifier example")
        errors += [f"docs/ORCHESTRATION.md §7: non-matching example \"{e}\"" for e in examples if not rx.match(e)]
    return errors + anti_bloat_gaps(root) + dependency_manifest_gaps(root)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=pathlib.Path(__file__).resolve().parents[1], type=pathlib.Path)
    errors = check(ap.parse_args().root)
    for e in errors:
        print(f"✘ {e}")
    print(f"{'🔴' if errors else '🟢'} {len(errors)} gap(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

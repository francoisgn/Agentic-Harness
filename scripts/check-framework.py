#!/usr/bin/env python3
"""Consistency checks of the harness, run by CI (standard library only).

- skills: `name` = directory name, `description` present;
- agents: `name` = file name, `description`, `tools`, known `model`; compliance agents with their sections;
- manifest: every source exists;
- labels: unique names, `axis: value` format (or one of the plain names), the exclusive axes are all present;
- repository identity (CONVENTIONS.md §Repository identity): description, topics, README banner, social preview;
- agent naming (ORCHESTRATION.md §7): every example matches the published regular expression.
Usage: check-framework.py [--root <repository>]   (exits 1 on any gap, lists every gap)
"""
import argparse
import importlib.util
import json
import pathlib
import re
import sys

GENERIC_REVIEWER = "compliance-reviewer"
MODELS = {"haiku", "sonnet", "opus", "fable", "inherit"}
COMPLIANCE_SECTIONS = ("## Role and limits", "## When to step in", "## What I check", "## Expected evidence",
                       "## Response format", "## Sources")
LABEL_RE = re.compile(r"^[a-z]+: [a-z-]+$")
PLAIN_LABELS = {"direct-pr", "dependencies"}
EXCLUSIVE_AXES = ("status", "type", "priority", "difficulty")


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
    return errors


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

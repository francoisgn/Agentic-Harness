# Contributing to Belayline

The harness is a toolbox, not a doctrine: each building block must be possible to keep, replace or switch off.
A contribution that adds a rule also says how to disable it.

## In short

1. **An issue first**, with its intent: the failure observed in a real project, what the building block changes, how
   we will know it is done. A lesson born in your project: "Lesson" form.
2. **A branch** from an up-to-date `master`; atomic commits, in English, in the style of `git log`.
3. **Local checks**: `scripts/local-check.sh` runs the steps of `ci.yml` (`--quick`: only those whose files
   changed). It ends with OK, FAILED or INCOMPLETE (a tool is missing: install it, or say in the PR which steps did
   not run); a test fails if the script and `ci.yml` drift apart, so a CI step changes in both.
4. **A draft PR**, then "Ready for review" when everything is done and reviewed by a model other than the author.
   Nothing runs in CI on a draft. The body carries a `Docs:` line: the doc files the change makes untrue, or
   `Docs: none (<reason>)` (`docs/CONVENTIONS.md` §Ledger).

## What a PR keeps true

| You touch | Update in the same PR |
|---|---|
| A skill, an agent | `name` = folder or file, `description`; the count and the table in the README; `templates/CLAUDE.md.block` |
| A vendored file | `harness.manifest`; a test in `scripts/tests/test-harness-sync.sh` if the mode is new |
| A script | Standard library only; a test `scripts/tests/test_*.py` seen failing without the change |
| A diagram | `docs/diagrams/<name>.json`, then `scripts/diagrams/render.py`; commit `.json`, `.svg`, `.excalidraw` |
| A label | `templates/.github/labels.json` (unique name, axis); `docs/METHODOLOGY.md` |
| A rule loaded in every session | `docs/ESSENTIALS.md`; keep it short |
| A behaviour visible to a project | `CHANGELOG.md`, with an "Action" line if the project has to do something; `VERSION` and `plugin.json` already carry the next `X.Y.Z-dev` (the first change after a release sets it; CI fails otherwise, [BRANCHING-RELEASE](docs/BRANCHING-RELEASE.md)) |

## Size limits

`scripts/check-framework.py` fails on a file that grows without limit, because every loaded line costs context. Body
size in characters, after the frontmatter (constants at the top of the script, with the reason for each value):

| File | Limit | Why |
|---|---|---|
| `SKILL.md` | 5000 | Largest skill today is 4.2 kB, plus about 20 % |
| Agent file | 5500 | Largest agent today is 4.4 kB (compliance agents have six mandatory sections), plus about 25 % |
| `docs/ESSENTIALS.md` | 5600 | Tighter: loaded in every session; 5.2 kB today, plus about 7 % |

The report names the file, its size and the limit; nothing is truncated. Shorten the file; a file that legitimately
needs more is listed in `SIZE_EXCEPTIONS` with its reason, the global limit is not raised. The same check fails when a
skill or agent links a `.harness/docs/` or `${CLAUDE_PLUGIN_ROOT}/docs/` file that does not exist, or when the counts
in the README or the skill list of `templates/CLAUDE.md.block` differ from `plugins/harness/`.

## What does not go in

- A rule with no observed failure behind it, or one that cannot be switched off.
- A dependency (Python package, third-party action not pinned by SHA, mandatory third-party account).
- The name of a person, a client or a private project; a secret, even a fake but plausible one.

## Reporting a vulnerability

Never in a public issue: use the **Security** tab › *Report a vulnerability* of the repository.

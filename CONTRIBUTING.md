# Contributing to Belayline

The harness is a toolbox, not a doctrine: each building block must be possible to keep, replace or switch off.
A contribution that adds a rule also says how to disable it.

## In short

1. **An issue first**, with its intent: the failure observed in a real project, what the building block changes, how
   we will know it is done. A lesson born in your project: "Lesson" form.
2. **A branch** from an up-to-date `master`; atomic commits, in English, in the style of `git log`.
3. **Local checks** (the same as the CI, one Linux job):
   ```bash
   python3 scripts/check-framework.py && python3 -m unittest discover -s scripts/tests -p 'test_*.py' \
     && scripts/tests/test-harness-sync.sh && python3 scripts/diagrams/render.py --check \
     && python3 scripts/readme-check.py && python3 scripts/doc-links.py
   ```
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
| A behaviour visible to a project | `CHANGELOG.md`, with an "Action" line if the project has to do something |

## What does not go in

- A rule with no observed failure behind it, or one that cannot be switched off.
- A dependency (Python package, third-party action not pinned by SHA, mandatory third-party account).
- The name of a person, a client or a private project; a secret, even a fake but plausible one.

## Reporting a vulnerability

Never in a public issue: use the **Security** tab › *Report a vulnerability* of the repository.

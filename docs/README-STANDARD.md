# The project README: default standard

**TL;DR**: by default, agents maintain the project README as a deliverable. It carries six things: technology
badges in the header, an image of the product, an architecture diagram (Excalidraw), the progress of the lots, the
quick start, and how to contribute. A script checks it, a skill updates it, every item can be switched off.

Why: the README is the only page read by the operator, a new contributor and an agent arriving
without context alike. A stale README makes every session start from scratch; a README maintained at the end of every
lot costs a few lines per PR.

## 1. What the README contains

| # | Item | Rule | Checked |
|---|---|---|---|
| 1 | **Header** | Title, then the **technology badges** (language, framework, platform, CI, licence), then one sentence: what the product does, for whom | at least one badge before the first `##` |
| 2 | **Image** | A screenshot or an image of the product in use, with alt text | one image other than badges; alt present; local file present |
| 3 | **Architecture** | A diagram of what is delivered: `docs/diagrams/architecture.svg`, `.excalidraw` source versioned next to it | `.svg` image + `.excalidraw` of the same name |
| 4 | **Progress** | A table, one row per lot (or milestone), between the markers `harness:begin progress` / `harness:end progress` | markers, table, every `LOT-…` of `docs/LOTS.md` cited |
| 5 | **Quick start** | The exact commands to install, run, test | a heading containing install, quick start, getting started or usage |
| 6 | **Contributing** | A short section that points to `CONTRIBUTING.md` (issue, branch, checks, PR, review) | a heading containing "contribut", file present, link |

Free order after the header. The rest (FAQ, roadmap, credits) belongs to the project.

## 2. Technology badges

- One badge per component **actually used**, read from the project's manifests, version included. No decorative
  badge, no more than one line.
- Format: `https://img.shields.io/badge/<name>-<version>-<colour>?logo=<slug>&logoColor=white` (slugs:
  simpleicons.org).
- A **status** badge (CI, latest version, coverage) points to a live source (GitHub workflow badge,
  release): never a hand-written number, it would be wrong at the next commit.

## 3. Lot progress

```markdown
<!-- harness:begin progress -->
| Lot | State | Done | Issue / PR |
|---|---|---|---|
| LOT-001 Calculation engine | 🟢 shipped | 4/4 | [#12](…) · [#31](…) |
| LOT-002 Input screen | 🔵 in progress | 1/3 | [#14](…) |
<!-- harness:end progress -->
```

- **Generated, never written by hand**: `python3 .harness/scripts/readme-progress.py` (token in `GH_TOKEN`) rewrites
  the block from GitHub: one row per lot (`type: epic` issue, [ADR 0003](adr/0003-labels-readable-by-axis.md)) with
  its title, state, closed/total sub-issues and links to the issue and its PRs (a PR whose body names the epic or a
  sub-issue after `Closes`/`Fixes`/`Resolves`/`Refs`). Without any epic: one row per GitHub milestone (closed/total
  issues). The text outside the markers is never touched; without markers the script refuses to write.
- **States**, first rule that applies: 🟢 shipped (every sub-issue closed) · 🟠 in review (a linked PR open and
  ready) · 🔵 in progress (`status: claimed`) · 🔴 blocked (`status: blocked` or `status: needs-decision`) · ⚪ to do.
  The labels are read on the epic and its open sub-issues.
- **Never guessed**: an epic without sub-issue, or an open issue with zero or several `status:` labels, is shown
  with a ⚠ mark; such an issue's labels do not choose the state.
- `--check` writes nothing and exits 1 if the committed block differs from the issues (diff printed). No token or no
  network: nothing is written, and `--check` says "could not check" (exit 2), never "up to date".
- The **source of truth stays the issue** ([METHODOLOGY](METHODOLOGY.md)): the table is a view of it, regenerated at
  the end of every lot (`/lot-finish` → `/readme-update`). `docs/LOTS.md` stays the plan and does not change for
  progress. Two parallel lots that both regenerate the block: on conflict, rerun the script after the merge.
- Opt-in drift report: input `readme-progress: true` of `flow-report.yml` runs `--check` with the dashboard and
  writes the result in the job summary; it never commits.
- Switched off (`"progress": false`) or no GitHub issues (tracking elsewhere): the table is the project's, one row
  per milestone or per product capability, written by hand.

## 4. Architecture diagram: Excalidraw by default

Excalidraw because the diagram can be read by a non-technical human, edited with the mouse on excalidraw.com, and
its source is versioned JSON that CI can render and check.

| File | Role |
|---|---|
| `docs/diagrams/<name>.json` | Source: list of elements (rectangle, ellipse, text, arrow, `label`) |
| `docs/diagrams/<name>.svg` | Image shown in the README: built-in render, or stamped Excalidraw export |
| `docs/diagrams/<name>.excalidraw` | Native scene, to open on excalidraw.com |

```bash
python3 .harness/scripts/diagrams-render.py            # renders docs/diagrams/*.json
python3 .harness/scripts/diagrams-render.py --check    # CI: exits 1 if a render is stale or a text overflows
```

Two ways to produce the SVG, neither needs any tooling beyond Python:

- **Built-in renderer** (default): the script draws the SVG itself, close to the Excalidraw look; `--check` draws it
  again and compares.
- **Excalidraw export**: open `<name>.excalidraw` on excalidraw.com (or an Excalidraw MCP), Export image → SVG,
  save it as `docs/diagrams/<name>.svg`, then run `diagrams-render.py --stamp <name>`. The script verifies the file
  (well-formed SVG, Excalidraw's `<!-- svg-source:excalidraw -->` marker, scene up to date, not stamped for another
  scene) and writes a stamp with the hash of the scene and of the SVG's body, which `--check` verifies. The stamp
  records which scene the author exported from; it cannot prove the image matches it: the reviewer looks at the
  image. The rendering never overwrites an export: when the scene changes, `--check` and the rendering fail and say
  the two ways out (export and stamp again, or `--engine builtin <name>` to draw it).

The three files are committed together. The diagram shows **what is delivered**; 5 to 9 boxes. Mermaid stays allowed
for a short flow in an internal doc; for the README, `"architecture": "any"` accepts it too.

## 5. Who maintains it, and when

| When | Who | What |
|---|---|---|
| Adoption | `harness-sync.sh` | Creates `README.md`, `CONTRIBUTING.md` and `docs/diagrams/architecture.*` **if they do not exist**; never rewrites them afterwards |
| End of lot | the lot's agent (`/lot-finish`, step 2) | `/readme-update`: the lot's row, badges, diagram if the architecture moved |
| After each merge | `doc-steward.yml` (opt-in, [STEWARDS](STEWARDS.md) §2) | Rewrites the progress block (`readme-progress.py`) and the files the `Docs:` lines name, in one draft docs PR |
| Every week | `doc-steward.yml`, mode `audit` | `readme-check.py`, `doc-links.py`, `diagrams-render.py --check`, `readme-progress.py --check`: one issue per gap |
| Every ready PR | CI (`docs-security.yml`, input `readme`) | `readme-check.py` + `diagrams-render.py --check` |

## 6. Tune or switch off

In `.harness/config.json`; absent = everything on.

```json
"readme": { "badges": true, "image": true, "architecture": "excalidraw", "progress": true,
            "quickstart": true, "contributing": true }
```

- A key set to `false` switches the item off. `"architecture": "any"` accepts any image or a Mermaid block.
- `"readme": false` switches everything off (configuration repository, internal library without lots).
- A README already in place is not replaced: `readme-check.py` lists the gaps, the project chooses which to close.

# Resume state: stream #80 (software factory guide). Branch never to be merged.

This branch only stores what an orchestrator session needs to resume after a quota cut or a reclaimed container.
The source of truth for progress is the umbrella issue #80 (its State comment) and the open PRs.

## How to resume

1. Read the State comment on issue #80, then list open PRs and the branches `docs/factory-*` on origin.
2. For each part (#82 to #87):
   - issue closed → done;
   - PR open → check CI, review against the issue, merge when green (one at a time: they share CHANGELOG and the
     index table; merge master into the branch first, keep both sides of CHANGELOG with `union.py`);
   - branch exists without PR → check out a worktree from it, read its last commit and its notes under
     `docs/factory/sources/`, finish the page per its issue, run the local checks, open the PR;
   - no branch → start the lot from fresh master with the briefs below.
3. Briefs given to each lot agent: `LOT.md` (how a lot works) then `STREAM.md` (rules of this stream, diagram
   procedure). Paths inside them point to a scratch directory that no longer exists: recreate one and adapt.
4. Review each page before its PR: every external fact has a source link and the page a "Last checked" date;
   nothing written from memory; the diagram is a scene-only pair and was looked at; the review by another model
   than the author is recorded in the PR body.

## Excalidraw export tooling (never committed to master)

Diagrams are exported with Excalidraw itself, outside the repository:
```bash
mkdir xtool && cd xtool
for f in export-svg.cjs package.json package-lock.json; do git -C <repo> show 0adcdf3^:scripts/diagrams/$f > $f; done
PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm ci --no-audit --no-fund
rm -rf node_modules/playwright node_modules/playwright-core          # use the pre-installed Playwright
sed -i 's|require(path.join(MODULES, "playwright"))|require("playwright")|' export-svg.cjs
node export-svg.cjs <worktree>/docs/diagrams/<name>.excalidraw      # writes the stamped <name>.svg
```
Check: re-exporting `docs/diagrams/ai-layers.excalidraw` this way gives the committed SVG back byte for byte.
A scene comes from a skeleton JSON placed temporarily at `docs/diagrams/<name>.json` and
`python3 scripts/diagrams/render.py <name>`; the JSON is then removed (scene-only pair). `build88.py` and
`ai-stack-v3.skeleton.json` are the generator and skeleton of `docs/diagrams/ai-stack`.

## Operator's standing instructions for this work (2026-11-09 to 11)

- Apply the harness's own rules: one issue per subject, labelled; claim; branch; test first; review by another
  model; PR; merge when it is ready and within the initial intent (the operator delegated merging ready PRs).
- No dependency in the repository.
- Diagrams: Excalidraw, common scene, scene-only pair (`.excalidraw` + `.svg`).
- Stream parts: not a market benchmark; every product fact sourced and dated; keep full research notes under
  `docs/factory/sources/` for future articles; third-party images by reference, never copied.
- Releasing 0.4.0 (tag) is the operator's action (steps in PR #79).

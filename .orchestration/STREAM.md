# Factory stream brief (umbrella issue #80): read after LOT.md

You write one part of the teaching stream "The software factory, rethought and automated for agents", under
`docs/factory/`. Read first, for the form to imitate: `docs/ai-layers/README.md` and `docs/ai-layers/obo-agents.md`
(audience line, "Last checked" date, TL;DR, short sections, tables, every product fact followed by its source link).
Read the umbrella issue #80 for the rules that apply to every part.

## Writing rules

- English, plain and direct, short sentences. Explain to a capable reader who is not in our project. No marketing
  tone, no rhetorical questions, no lists of three for rhythm. Define a term once, then keep it.
- Every external fact (what a tool does, a plan it needs, a limit, a price rule, a behaviour of GitHub) cites its
  source right there (vendor documentation first) and the page states "Last checked: <today's date>" at the top.
  Verify each fact by fetching the vendor page NOW with WebFetch / WebSearch (load them with ToolSearch if needed);
  do not write product facts from memory, they change every few months. A fact you could not verify is marked
  "to verify" with what you tried, or left out. Never invent a URL: only link pages you actually opened.
- Facts about our own projects cite the issue, PR, file or dashboard they come from. The operator's observations
  are written as such: "Observed by the operator (2026-11): …".
- The harness's own choices: point to the file and section that makes them; do not restate rules from memory, read
  the file.
- Non-dogmatic: say what the harness chose and what else is reasonable.
- Length: as short as the content allows; a part is one page a busy person finishes. Tables over prose for
  comparisons.

## Files

- Your page: the path named in your issue. Flip your row in `docs/factory/README.md` from `planned` to
  `🟢 available` with the link (only your row). Add ONE bullet under `## Unreleased` in `CHANGELOG.md`.
- `VERSION` is now `X.Y.Z-dev`: do not touch it.

## Diagram (one per part, only if it helps)

Diagrams in this repo share one look. Do it exactly like this:
1. Start from the skeleton of the common scene: copy `docs/diagrams/ai-layers.json` to a scratch file OUTSIDE the
   repository (e.g. /tmp/claude-0/-home-user/3ea4108d-a4ec-5f0a-bfb6-207675ab6201/scratchpad/wt/<n>-skeleton.json), keep its geometry, fonts, hachure fills and colour code, and change
   the texts / add or remove boxes and arrows in the same style (rectangles with `label`, arrows with `points`;
   allowed element types: rectangle, ellipse, text, arrow). Keep labels short; a label must fit its box.
2. Put the skeleton temporarily at `docs/diagrams/<name>.json` in your worktree and run
   `python3 scripts/diagrams/render.py <name>`: it writes `<name>.excalidraw` (and a built-in svg) and reports
   overflowing labels: fix them.
3. Export with Excalidraw itself (tooling installed OUTSIDE the repo, never commit it):
   `cd /tmp/claude-0/-home-user/3ea4108d-a4ec-5f0a-bfb6-207675ab6201/scratchpad/xtool && node export-svg.cjs <worktree>/docs/diagrams/<name>.excalidraw` → writes the stamped
   `<name>.svg` next to the scene.
4. DELETE `docs/diagrams/<name>.json` from the worktree (move it back to the scratch folder): the diagram is
   committed as a scene-only pair, `<name>.excalidraw` + `<name>.svg`. Then `python3 scripts/diagrams/render.py --check`
   must pass.
5. Look at the result: render the svg to a PNG with Playwright (pre-installed: `node -e "const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1300,height:900}});await p.goto('file://<abs path to svg>',{waitUntil:'commit'});await p.waitForTimeout(1500);await p.screenshot({path:'<out.png>'});await b.close()})()"`)
   and READ the PNG. Fix overlaps, cramped text, crossings. Iterate until it is clean.
6. Reference it in the page with an alt text that describes what is drawn.
Never add a dependency manifest to the repository (a check forbids it).

#!/usr/bin/env node
/* Exports Excalidraw scenes to SVG with Excalidraw itself: Excalifont, hand-drawn strokes, hachure fills.

  node scripts/diagrams/export-svg.cjs <name>.excalidraw...   → <name>.svg next to each scene

Called by render.py when the dependencies are installed (`npm ci --prefix scripts/diagrams`); never needed to check.
The SVG carries `<!-- belayline-scene-sha256:<scene> svg-sha256:<body> -->`: the hash of the scene it was exported
from and the hash of the SVG without that comment. render.py --check verifies both, in Python, without Node.
Needs a Chromium for Playwright: `npx --prefix scripts/diagrams playwright install chromium` if none is installed.
Runs offline: the page loads only local files (bundle, fonts); any other request is refused. Same scene, same SVG.
*/
const crypto = require("crypto");
const fs = require("fs");
const http = require("http");
const path = require("path");

const HERE = __dirname;
const MODULES = path.join(HERE, "node_modules");
const ASSETS = "/node_modules/@excalidraw/excalidraw/dist/prod/";
const BUNDLE = path.join(MODULES, ".belayline", "export-bundle.js");
const ENTRY = `
import { exportToSvg } from "@excalidraw/excalidraw";
window.exportScene = async (scene) => (await exportToSvg({
  elements: scene.elements,
  appState: { ...scene.appState, exportBackground: true, viewBackgroundColor: "#ffffff", exportWithDarkMode: false,
              exportEmbedScene: false },
  files: scene.files || {},
  exportPadding: 24,
})).outerHTML;
`;

const sha256 = (data) => crypto.createHash("sha256").update(data).digest("hex");

function stamp(svg, sceneHash) {
  const body = `${svg}\n`;
  const end = body.indexOf(">") + 1;
  return `${body.slice(0, end)}<!-- belayline-scene-sha256:${sceneHash} svg-sha256:${sha256(body)} -->${body.slice(end)}`;
}

function bundle() {
  // Rebuilt whenever the entry point or the locked dependencies change
  const key = sha256(ENTRY + fs.readFileSync(path.join(HERE, "package-lock.json"), "utf8"));
  const keyFile = `${BUNDLE}.key`;
  if (fs.existsSync(BUNDLE) && fs.existsSync(keyFile) && fs.readFileSync(keyFile, "utf8") === key) return;
  fs.mkdirSync(path.dirname(BUNDLE), { recursive: true });
  require(path.join(MODULES, "esbuild")).buildSync({
    stdin: { contents: ENTRY, resolveDir: HERE, loader: "js" }, bundle: true, format: "iife", outfile: BUNDLE,
    define: { "process.env.NODE_ENV": '"production"' }, loader: { ".woff2": "file", ".ttf": "file" },
    logLevel: "error",
  });
  fs.writeFileSync(keyFile, key);
}

async function main(scenes) {
  if (!scenes.length) {
    console.error("usage: export-svg.cjs <scene.excalidraw>...");
    return 2;
  }
  bundle();
  const types = { ".js": "text/javascript", ".woff2": "font/woff2", ".ttf": "font/ttf" };
  const server = http.createServer((req, res) => {
    let url;
    try {
      url = decodeURIComponent(req.url.split("?")[0]);
    } catch {
      res.statusCode = 400;
      return res.end();
    }
    if (url === "/") {
      res.setHeader("content-type", "text/html");
      return res.end(`<!doctype html><meta charset="utf-8"><script>window.EXCALIDRAW_ASSET_PATH=${JSON.stringify(ASSETS)}`
        + `</script><script src="/node_modules/.belayline/export-bundle.js"></script>`);
    }
    const file = path.join(HERE, url);
    if (!file.startsWith(MODULES + path.sep) || !fs.existsSync(file)) {
      res.statusCode = 404;
      return res.end();
    }
    res.setHeader("content-type", types[path.extname(file)] || "application/octet-stream");
    fs.createReadStream(file).pipe(res);
  });
  await new Promise((ok) => server.listen(0, "127.0.0.1", ok));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const { chromium } = require(path.join(MODULES, "playwright"));
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    await page.route("**/*", (r) => (r.request().url().startsWith(`${origin}/`) ? r.continue() : r.abort()));
    await page.goto(origin + "/");
    await page.waitForFunction(() => typeof window.exportScene === "function");
    for (const scenePath of scenes) {
      const raw = fs.readFileSync(scenePath);
      const svg = await page.evaluate((s) => window.exportScene(s), JSON.parse(raw.toString("utf8")));
      fs.writeFileSync(scenePath.replace(/\.excalidraw$/, ".svg"), stamp(svg, sha256(raw)));
    }
  } finally {
    await browser.close();
    server.close();
  }
  return 0;
}

main(process.argv.slice(2)).then((code) => process.exit(code), (err) => {
  console.error(`export-svg: ${err.message}`);
  process.exit(1);
});

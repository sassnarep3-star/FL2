/* FL2 render test — proves the pages actually populate in a browser.
 *
 *   node tools/render_test.js
 *
 * Checks, for every page: chrome renders, every table mount produces a real
 * table (no "missing dataset" fallbacks), every data-stat counter resolves to a
 * non-empty value, and no script error is thrown. Exits 1 on any failure so it
 * can gate a publish. Uses jsdom only; the site itself has no dependencies.
 */
const fs = require("fs");
const path = require("path");
let JSDOM, VirtualConsole;
try {
  ({ JSDOM, VirtualConsole } = require("jsdom"));
} catch (e) {
  console.error("tools/render_test.js needs jsdom (dev-only; the site itself has no dependencies).\n" +
                "Install with:  npm install   then:  node tools/render_test.js\n" +
                "Or skip this check and rely on python3 tools/check_site.py, which needs nothing.");
  process.exit(2);
}

const ROOT = path.resolve(__dirname, "..");
const pages = fs.readdirSync(ROOT).filter((f) => f.endsWith(".html")).sort();

const failures = [];
const notes = [];

async function run(page) {
  const errors = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", (e) => errors.push(e.message || String(e)));
  vc.on("error", (m) => errors.push(String(m)));
  const dom = await JSDOM.fromFile(path.join(ROOT, page), {
    runScripts: "dangerously",
    resources: "usable",
    virtualConsole: vc,
  });
  await new Promise((res) => {
    if (dom.window.document.readyState === "complete") return res();
    dom.window.addEventListener("load", res);
    setTimeout(res, 2500);
  });
  await new Promise((res) => setTimeout(res, 120)); // let the DOMContentLoaded handler settle
  const d = dom.window.document;

  if (errors.length) failures.push(`${page}: script error -> ${errors[0].slice(0, 200)}`);

  const nav = d.querySelectorAll("#site-header nav a");
  if (nav.length < pages.length - 1) {
    failures.push(`${page}: nav renders ${nav.length} links, expected >= ${pages.length - 1}`);
  }
  if (!d.querySelector("#site-header .brand")) failures.push(`${page}: masthead did not render`);
  if (!d.querySelector("footer#site-footer a")) failures.push(`${page}: footer did not render`);

  const mounts = [...d.querySelectorAll(".table-mount")];
  const bodyTables = d.querySelectorAll(".table-wrap, .tablewrap").length;
  notes.push(`${page}: ${mounts.length} mounts, ${bodyTables} tables in body`);
  for (const m of mounts) {
    const html = m.innerHTML.trim();
    const id = m.getAttribute("data-set");
    if (!html) { failures.push(`${page}: mount "${id}" is empty (app.js did not run?)`); continue; }
    if (/missing dataset|no dataset|dataset missing|not found/i.test(html)) {
      failures.push(`${page}: mount "${id}" rendered an error fallback: ${html.replace(/\s+/g, " ").slice(0, 120)}`);
      continue;
    }
    const rows = m.querySelectorAll("tbody tr").length;
    if (rows === 0) failures.push(`${page}: mount "${id}" rendered a table with no rows`);
    else notes.push(`${page}: ${id} -> ${rows} rows`);
    // a factual table must expose a way back to the source: an absolute link, or a
    // source column/note. data-nosrc opts out (registers that cite source IDs instead).
    const links = [...m.querySelectorAll('a[href^="http"]')].length;
    const explains = !!m.querySelector(".srcnote") || /\bSource\b/.test(m.textContent);
    if (links === 0 && !explains) {
      failures.push(`${page}: mount "${id}" shows neither a source link nor a provenance note`);
    }
  }

  for (const s of [...d.querySelectorAll("[data-stat]")]) {
    const key = s.getAttribute("data-stat");
    if (!s.textContent.trim()) failures.push(`${page}: stat "${key}" did not resolve (empty)`);
    else if (/NaN|undefined|null/.test(s.textContent)) failures.push(`${page}: stat "${key}" resolved to "${s.textContent}"`);
  }

  for (const b of [...d.querySelectorAll(".injury-banner")]) {
    if (b.textContent.trim().length < 40) failures.push(`${page}: injury banner did not render`);
  }
  dom.window.close();
}

(async () => {
  for (const p of pages) await run(p);
  console.log("FL2 render test (jsdom)");
  console.log("=".repeat(60));
  console.log(notes.length + " populated mounts checked");
  const stats = {};
  notes.forEach((n) => { const m = n.match(/-> (\d+) rows/); if (m) stats.total = (stats.total || 0) + +m[1]; });
  console.log("total rendered table rows:", stats.total || 0);
  console.log("-".repeat(60));
  if (failures.length) {
    console.log(failures.length + " failure(s):");
    failures.forEach((f) => console.log("  x " + f));
    process.exit(1);
  }
  console.log("all pages render");
})();

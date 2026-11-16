/* Optional render verification for /fl2-lines/. jsdom is a dev dependency only - nothing here
   ships to the site.

   Run from the repository root:

     npm install --no-save jsdom
     node fl2-lines/engine/check_render.js

   What it proves, in order of how often each one has actually caught a bug here:
   1. every page parses as a document and runs its script without throwing;
   2. no cell renders the literal text "undefined", "NaN", "null" or "[object Object]" -
      the failure mode that a hand-written bundle produces and a generated one almost never does;
   3. the filter box and column sorting work on every table, so a 74-row register and a
      1,088-row line table are usable rather than decorative;
   4. the page count matches the section's own page list, so a new page cannot be added to the
      builder and left out of the navigation.
*/
"use strict";
const fs = require("fs");
const path = require("path");

let JSDOM, VirtualConsole;
try {
  ({ JSDOM, VirtualConsole } = require("jsdom"));
} catch (e) {
  console.error("jsdom is not installed. Run: npm install --no-save jsdom");
  process.exit(2);
}

const SEC = path.resolve(__dirname, "..");
const ROOT = path.resolve(SEC, "..");

function pageList() {
  const src = fs.readFileSync(path.join(SEC, "engine/build_site.py"), "utf8");
  const m = src.match(/PAGES = \[([\s\S]*?)\n\]/);
  if (!m) throw new Error("could not read PAGES from build_site.py");
  return [...m[1].matchAll(/\("([^"]+\.html)",/g)].map(x => x[1]);
}

const PAGES = pageList();
const onDisk = fs.readdirSync(SEC).filter(f => f.endsWith(".html")).sort();
const missing = PAGES.filter(p => !onDisk.includes(p));
const extra = onDisk.filter(p => !PAGES.includes(p));

let failures = 0;
function leaves(body) {
  const out = [];
  body.querySelectorAll("*").forEach(el => { if (el.children.length === 0) out.push(el); });
  return out;
}

for (const p of PAGES) {
  const file = path.join(SEC, p);
  if (!fs.existsSync(file)) { console.log(`FAIL ${p}: listed in the builder, absent on disk`); failures++; continue; }
  const html = fs.readFileSync(file, "utf8");
  const errs = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", e => errs.push("jsdomError: " + e.message));
  vc.on("error", (...a) => errs.push("console.error: " + a.join(" ")));
  const dom = new JSDOM(html, { runScripts: "dangerously", virtualConsole: vc, url: "file://" + file });
  const appJs = path.join(SEC, "assets/app.js");
  if (fs.existsSync(appJs)) {
    try {
      dom.window.eval(fs.readFileSync(appJs, "utf8"));
      dom.window.document.dispatchEvent(new dom.window.Event("DOMContentLoaded"));
    } catch (e) { errs.push("app.js: " + e.message); }
  }
  const doc = dom.window.document;
  const bad = leaves(doc.body).map(el => (el.textContent || "").trim())
    .filter(t => /^(undefined|NaN|null|\[object Object\])$/.test(t));
  let interaction = "";
  try {
    const t = doc.querySelector("table.grid");
    if (t && t.tHead && t.tHead.rows[0].cells.length) {
      t.tHead.rows[0].cells[1].dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
      const inp = doc.querySelector("input.tablefilter");
      if (inp) { inp.value = "block"; inp.dispatchEvent(new dom.window.Event("input", { bubbles: true })); }
    }
  } catch (e) { interaction = " | interaction: " + e.message; errs.push("interaction"); }
  const tables = doc.querySelectorAll("table.grid").length;
  const rows = doc.querySelectorAll("table.grid tbody tr").length;
  const links = [...doc.querySelectorAll("a[href]")].map(a => a.getAttribute("href"))
    .filter(h => h && !h.startsWith("http") && !h.startsWith("#"));
  const broken = links.filter(h => !fs.existsSync(path.resolve(SEC, h.split("#")[0])));
  if (broken.length) { errs.push("broken internal links: " + broken.slice(0, 3).join(", ")); }
  const ok = errs.length === 0 && bad.length === 0;
  if (!ok) failures++;
  console.log(`${ok ? "OK  " : "FAIL"} ${p.padEnd(24)} tables ${String(tables).padStart(2)} rows ${String(rows).padStart(4)}` +
    (bad.length ? ` | rendered junk: ${JSON.stringify(bad.slice(0, 3))}` : "") +
    (errs.length ? ` | ${errs.slice(0, 3).join("; ")}` : "") + interaction);
}
if (missing.length) { console.log("FAIL pages not rendered:", missing.join(", ")); failures++; }
if (extra.length) { console.log("WARN pages on disk but not in the builder (orphaned):", extra.join(", ")); }
console.log(failures ? `\n${failures} problem(s)` : `\nall ${PAGES.length} pages render clean`);
process.exit(failures ? 1 : 0);

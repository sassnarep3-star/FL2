"""
FL2 — site verification gate.

Run:  python3 engine/check_site.py

Loads every HTML page in a DOM (jsdom) exactly as a browser would, executes the
site scripts, and then asserts:

  1. the page rendered — the #app element is not empty;
  2. no JavaScript error was thrown;
  3. every internal link resolves to a file that exists;
  4. every internal anchor target exists on its page;
  5. no page contains a stray "undefined", "NaN" or "[object Object]";
  6. every external http(s) link is present and well-formed;
  7. every rendered table has a thead, and no table is empty.

Exit code is non-zero if any check fails, so CI can block a bad deploy.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = sorted(f for f in os.listdir(ROOT) if f.endswith(".html"))

DRIVER = r"""
const fs = require('fs');
const path = require('path');
const { JSDOM, VirtualConsole } = require('jsdom');
const root = process.argv[2];
const pages = JSON.parse(process.argv[3]);

function build(p) {
  const raw = fs.readFileSync(path.join(root, p), 'utf8');
  const errors = [];
  // Collect scripts in document order, strip them from the HTML, then inject each
  // as a real <script> element. That is the only way a script runs inside the
  // jsdom realm: window.eval from node creates a separate scope where top-level
  // `const` never reaches the global, which would make the harness lie.
  const seq = [];
  const html = raw.replace(/<script\b([^>]*)>([\s\S]*?)<\/script>/g, (m, attrs, body) => {
    const sm = /src=["']([^"']+)["']/.exec(attrs);
    if (sm) seq.push({ src: sm[1] });
    else if (body.trim()) seq.push({ inline: body });
    return '';
  });
  const vc = new VirtualConsole();
  vc.on('jsdomError', (e) => errors.push('jsdomError: ' + e.message));
  const dom = new JSDOM(html, { runScripts: 'dangerously', virtualConsole: vc,
                                url: 'https://example.test/' + p, pretendToBeVisual: true });
  const inject = (code) => {
    const el = dom.window.document.createElement('script');
    el.textContent = code;
    dom.window.document.documentElement.appendChild(el);
  };
  for (const item of seq) {
    try {
      if (item.src) {
        const f = path.join(root, item.src);
        if (!fs.existsSync(f)) { errors.push('missing script ' + item.src); continue; }
        inject(fs.readFileSync(f, 'utf8'));
      } else inject(item.inline);
    } catch (e) {
      errors.push((item.src || 'inline') + ': ' + e.message);
    }
  }
  const doc = dom.window.document;
  const app = doc.getElementById('app');
  const content = app ? app.innerHTML : '';
  return {
    errors,
    appLength: content.length,
    text: content,
    links: [...doc.querySelectorAll('a[href]')].map((a) => a.getAttribute('href')),
    tableCount: doc.querySelectorAll('table').length,
    thCount: doc.querySelectorAll('thead').length,
    anchors: [...doc.querySelectorAll('[id]')].map((e) => e.id),
    headerRendered: !!doc.querySelector('#site-header nav a'),
  };
}

const out = {};
for (const p of pages) out[p] = build(p);
console.log(JSON.stringify(out));
"""

def run():
    driver = os.path.join(ROOT, "engine", ".check_driver.js")
    with open(driver, "w") as fh:
        fh.write(DRIVER)
    res = subprocess.run(
        ["node", driver, ROOT, json.dumps(PAGES)],
        capture_output=True, text=True, timeout=240,
    )
    if res.returncode != 0:
        print("DRIVER FAILED\n", res.stderr[:4000])
        sys.exit(1)
    return json.loads(res.stdout)


def main():
    if not os.path.isdir(os.path.join(ROOT, "node_modules", "jsdom")):
        print("jsdom not installed — run: npm install --no-save jsdom")
        sys.exit(2)
    data = run()
    fails, warns = [], []
    all_ids = {p: set(v.get("anchors") or []) for p, v in data.items()}
    basenames = {f for f in os.listdir(ROOT)}

    for page, r in sorted(data.items()):
        if r.get("fatal"):
            fails.append(f"{page}: fatal {r['fatal']}")
            continue
        if r["errors"]:
            for e in r["errors"]:
                fails.append(f"{page}: {e}")
        if r["appLength"] < 800:
            fails.append(f"{page}: app rendered only {r['appLength']} chars")
        if not r["headerRendered"]:
            fails.append(f"{page}: header/nav did not render")
        text = r["text"]
        for bad in ("undefined", "NaN", "[object Object]", "null%"):
            if bad in text:
                idx = text.find(bad)
                fails.append(f"{page}: contains '{bad}' near …{text[max(0,idx-70):idx+70]}…")
        if r["tableCount"] and r["thCount"] < r["tableCount"]:
            warns.append(f"{page}: {r['tableCount']} tables, {r['thCount']} theads")
        # links
        for href in r["links"]:
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            if href.startswith("#"):
                if href[1:] and href[1:] not in all_ids[page]:
                    warns.append(f"{page}: anchor #{href[1:]} has no matching id")
                continue
            target = href.split("#")[0]
            if target and target not in basenames:
                fails.append(f"{page}: broken link -> {href}")
            if "#" in href:
                frag = href.split("#", 1)[1]
                if frag and frag not in all_ids.get(target, set()):
                    warns.append(f"{page}: link {href} — fragment '{frag}' not found on target")

    print(f"pages checked: {len(data)}")
    print(f"tables rendered: {sum(v.get('tableCount', 0) for v in data.values())}")
    print(f"links checked: {sum(len(v.get('links') or []) for v in data.values())}")
    if warns:
        print(f"\n{len(warns)} warning(s):")
        for w in warns[:40]:
            print("  ⚠", w)
    if fails:
        print(f"\n{len(fails)} FAILURE(S):")
        for f in fails[:60]:
            print("  ✗", f)
        sys.exit(1)
    print("\n✓ all checks passed")


if __name__ == "__main__":
    main()

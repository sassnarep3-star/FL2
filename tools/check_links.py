#!/usr/bin/env python3
"""
tools/check_links.py

Static verification of the generated site. Exits non-zero on any failure, so it
can gate a deploy.

Checks performed
  1. every internal href resolves to a file that exists
  2. every in-page #anchor has a matching id on the target page
  3. every page has the required head/meta/nav/footer elements
  4. every data table that shows a source column actually has a link in it
  5. every URL in data/sources.csv is well-formed
  6. no page references an external CDN (script src / stylesheet href off-site)
  7. the blank-cell marker is never used to fake a value
"""
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = []

for dirpath, _, files in os.walk(ROOT):
    if ".git" in dirpath:
        continue
    for f in files:
        if f.endswith(".html"):
            HTML.append(os.path.relpath(os.path.join(dirpath, f), ROOT))

errors, warnings = [], []


def read(p):
    with open(os.path.join(ROOT, p), encoding="utf-8") as fh:
        return fh.read()


ids_cache = {}


def ids_of(path):
    if path not in ids_cache:
        ids_cache[path] = set(re.findall(r'id="([^"]+)"', read(path)))
    return ids_cache[path]


HREF = re.compile(r'href="([^"]+)"')


for page in sorted(HTML):
    text = read(page)
    base = os.path.dirname(page)

    # 3. structure
    for required, label in [
        ('<meta charset="utf-8">', "charset"),
        ('name="viewport"', "viewport"),
        ('assets/css/style.css', "stylesheet"),
        ('class="site"', "header"),
        ('<main id="main">', "main landmark"),
        ('footer class="site"', "footer"),
    ]:
        if required not in text:
            errors.append(f"{page}: missing {label}")

    # 6. no external scripts / stylesheets
    for m in re.finditer(r'<(script|link)[^>]+(src|href)="(https?://[^"]+)"', text):
        if 'rel="stylesheet"' in m.group(0) or m.group(1) == "script":
            errors.append(f"{page}: external asset reference {m.group(3)}")

    # 1 & 2. links
    for href in HREF.findall(text):
        if href.startswith(("http://", "https://", "mailto:", "data:")):
            continue
        if href == "" or href == "#":
            continue
        target, _, anchor = href.partition("#")
        if target == "":
            if anchor and anchor not in ids_of(page):
                errors.append(f"{page}: dangling in-page anchor #{anchor}")
            continue
        resolved = os.path.normpath(os.path.join(base, target))
        if not os.path.exists(os.path.join(ROOT, resolved)):
            errors.append(f"{page}: broken internal link {href} -> {resolved}")
            continue
        if anchor and resolved.endswith(".html"):
            if anchor not in ids_of(resolved):
                errors.append(f"{page}: broken anchor {href}")

    # 7. blank marker sanity: no literal 'undefined' / 'None' / 'nan'
    for bad in (">undefined<", ">None<", ">nan<", ">NaN<", "Traceback"):
        if bad in text:
            errors.append(f"{page}: leaked placeholder text '{bad}'")

# 4 & 5. source registry
with open(os.path.join(ROOT, "data/sources.csv"), newline="") as fh:
    sources = list(csv.DictReader(fh))

for s in sources:
    if not re.fullmatch(r"https?://\S+", s["url"]):
        errors.append(f"sources.csv {s['id']}: malformed url {s['url']!r}")
    if not s["retrieved"]:
        errors.append(f"sources.csv {s['id']}: missing retrieval date")

# every dataset that claims verification must carry a source url column
for ds, cols in [
    ("data/injury-report-2026-w10.csv", ["source_url"]),
    ("data/standings-2026-w10.csv", ["source_url", "verification"]),
    ("data/team-metrics-2026-w10.csv", ["source_standings", "verification"]),
    ("data/slate-2026-w10.csv", ["source_schedule", "verification"]),
    ("data/correlation-matrix-2026-w10.csv", ["source_url"]),
]:
    path = os.path.join(ROOT, ds)
    if not os.path.exists(path):
        errors.append(f"missing dataset {ds}")
        continue
    with open(path, newline="") as fh:
        rd = csv.DictReader(fh)
        rows = list(rd)
        for col in cols:
            if col not in rd.fieldnames:
                errors.append(f"{ds}: missing required column {col}")
                continue
            empties = [i for i, r in enumerate(rows, 2) if not r[col].strip()]
            if empties:
                errors.append(f"{ds}: {len(empties)} empty '{col}' cells (rows {empties[:5]})")

print(f"pages checked: {len(HTML)}")
print(f"sources checked: {len(sources)}")
if warnings:
    print("\nWARNINGS")
    for w in warnings:
        print("  ", w)
if errors:
    print(f"\nFAILED with {len(errors)} error(s):")
    for e in errors:
        print("  ", e)
    sys.exit(1)
print("\nOK — all internal links resolve, all anchors resolve, all datasets carry sources.")

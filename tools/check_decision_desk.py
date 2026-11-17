#!/usr/bin/env python3
"""
tools/check_decision_desk.py — CI contract for /decision-desk/.

The rest of the repository already enforces "every table row carries a source link"
for its own sections (scripts/check_site.py, tools/check_links.py,
fl2-lines/engine/check.py, ops/check_readiness.py). This file holds this section to
the same standard, plus two rules that matter for a page whose whole job is to make
claims about other files:

  * every repository link must resolve to a file that still exists — a register that
    is cited but has been moved or deleted must fail the build, not age quietly;
  * every number printed on the pages must equal the number in the build artefact —
    prose that says "N decisions" while the artefact says otherwise fails.

Run: python3 tools/check_decision_desk.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESK = os.path.join(ROOT, "decision-desk")
BLOB = "https://github.com/sassnarep3-star/FL2/blob/main/"
OFFICIAL_HOSTS = {"www.nfl.com", "nfl.com"}
ALLOWED_HOSTS = OFFICIAL_HOSTS | {"github.com"}
PAGES = ["index.html", "suggestions.html", "questions.html", "calibration.html",
         "freshness.html", "sources.html"]
SOURCE_HEADERS = ("source", "sources", "where", "evidence", "official", "basis",
                  "handling", "source file", "files")
FORBIDDEN = ["TODO", "FIXME", "lorem ipsum", "XXX", "placeholder value"]

errors: list[str] = []
warnings: list[str] = []


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


try:
    desk = json.loads(read("decision-desk/data/desk.json"))
    ev = json.loads(read("decision-desk/data/evidence.json"))
except Exception as exc:  # a missing artefact is a hard failure
    print(f"FAIL: cannot read the build artefacts: {exc}")
    raise SystemExit(1)

pages = {}
for pg in PAGES:
    path = os.path.join("decision-desk", pg)
    if not os.path.exists(os.path.join(ROOT, path)):
        errors.append(f"{pg}: page missing")
        continue
    pages[pg] = read(path)

# 1 ---------------------------------------------------------------- structure
for pg, text in pages.items():
    for need, label in [("<title>", "a <title>"), ("assets/style.css", "the stylesheet"),
                        ("<footer>", "the footer"), ("Decision Desk", "the section name in the masthead")]:
        if need.lower() not in text.lower():
            errors.append(f"{pg}: missing {label}")
    if f'href="{pg}"' not in text and f'aria-current="page"' not in text:
        errors.append(f"{pg}: no aria-current navigation state")
    for bad in FORBIDDEN:
        if bad.lower() in text.lower():
            errors.append(f"{pg}: contains the forbidden token {bad!r}")
    if re.search(r"<script[^>]+src=[\"']https?://", text):
        errors.append(f"{pg}: loads a script from off-site")
    if re.search(r"<link[^>]+href=[\"']https?://[^\"']*/(style|css)", text):
        errors.append(f"{pg}: loads a stylesheet from a CDN")

# 2 ------------------------------------------------- tables must be evidenced
def tables_of(text):
    return re.findall(r"<table[^>]*>(.*?)</table>", text, re.S)


for pg, text in pages.items():
    for tbl in tables_of(text):
        heads = [re.sub(r"<[^>]+>", "", h).strip().lower()
                 for h in re.findall(r"<th[^>]*>(.*?)</th>", tbl, re.S)]
        if not any(any(s == h or s in h for s in SOURCE_HEADERS) for h in heads):
            continue
        body = tbl.split("</thead>", 1)[-1]
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S)
        for n, row in enumerate(rows, 1):
            if "<a href=" not in row:
                first = re.sub(r"<[^>]+>", "", row).strip()[:70]
                errors.append(f"{pg}: table row {n} has no source link ({first!r})")

# 3 --------------------------------------------- repository links must resolve
for pg, text in pages.items():
    for url in set(re.findall(r'href="(https://github\.com/sassnarep3-star/FL2/blob/main/[^"]+)"', text)):
        rel = url.replace(BLOB, "")
        if "#" in rel:
            rel = rel.split("#", 1)[0]
        if rel and not os.path.exists(os.path.join(ROOT, rel)):
            errors.append(f"{pg}: cites a repository file that does not exist: {rel}")

# 4 ------------------------------------------------------ anchors must resolve
ids_cache = {}
for pg, text in list(pages.items()):
    ids_cache[pg] = set(re.findall(r'id="([^"]+)"', text))

for pg, text in pages.items():
    for href in set(re.findall(r'href="([^"#]+)?#([^"]+)"', text)):
        target, frag = href
        target = target or pg
        if target.startswith(("http", "../", "/")):
            continue
        if target not in ids_cache:
            path = os.path.join(ROOT, "decision-desk", target)
            if not os.path.exists(path):
                errors.append(f"{pg}: link to missing page {target}")
                continue
            ids_cache[target] = set(re.findall(r'id="([^"]+)"', open(path, encoding="utf-8").read()))
        if frag and frag not in ids_cache[target]:
            errors.append(f"{pg}: #{frag} has no matching id on {target}")
    for href in set(re.findall(r'href="(data/[^"]+|assets/[^"]+)"', text)):
        href = href.split("#", 1)[0]
        if not os.path.exists(os.path.join(ROOT, "decision-desk", href)):
            errors.append(f"{pg}: local link {href} does not resolve")

# 5 -------------------------------------- printed counts must equal the artefact
stats = desk.get("stats", {})
checks = [
    ("suggestions.html", str(stats.get("suggestions_present")), "decisions from"),
    ("suggestions.html", str(stats.get("suggestion_entries")), "register entries"),
    ("questions.html", str(stats.get("questions_present")), None),
    ("sources.html", str(stats.get("evidence_entries")), None),
]
for pg, value, ctx in checks:
    if value is None:
        continue
    if value not in pages.get(pg, ""):
        errors.append(f"{pg}: the printed figure {value!r} does not match the artefact"
                      + (f" near {ctx!r}" if ctx else ""))

# the board's arithmetic must close: merged rows + new rows = rows on the board
n_new = int(stats.get("new_from_this_session", 0))
if stats.get("suggestions_present", 0) - n_new > stats.get("suggestion_entries", 0):
    errors.append(f"suggestions: {stats['suggestions_present'] - n_new} merged rows claimed, but only "
                  f"{stats['suggestion_entries']} register entries were read")
if f"{stats.get('suggestions_present')} decisions" not in pages.get("suggestions.html", ""):
    errors.append("suggestions.html: the heading does not state the board's own row count")

# row counts: the artefact's own row lists must appear the same number of times
n_sug = len(desk.get("suggestions", []))
m_sug = len(re.findall(r'<b id="', pages.get("suggestions.html", "")))
if n_sug != m_sug:
    errors.append(f"suggestions.html: {m_sug} anchored rows, artefact holds {n_sug}")

# 6 ------------------------------------------------ official links are official
for pg, text in pages.items():
    for label, url in re.findall(r'<a href="(https?://[^"]+)"[^>]*>([^<]*)</a>', text):
        host = urlparse(url).netloc.lower()
        if host and host not in ALLOWED_HOSTS:
            errors.append(f"{pg}: link to a host outside the allowed set: {host}")
        if "official" in label.lower() and host not in OFFICIAL_HOSTS:
            errors.append(f"{pg}: link labelled 'official' points at {host or 'a local file'}, not nfl.com")

# 6b ------------------------------ a superseded value may never be quoted bare
abl = desk.get("ablation") or {}
if abl.get("found") and not abl.get("agrees"):
    for h in abl.get("register", []):
        bad_val = str(h.get("beta"))
        good_val = str(abl.get("artefact"))
        for pg, text in pages.items():
            plain = re.sub(r"<[^>]+>", "", text)
            if bad_val in plain and good_val not in plain:
                errors.append(f"{pg}: quotes the superseded value {bad_val} without the artefact value {good_val}")

# 7 --------------------------------------------- capture log must be internally sound
eids = [e.get("id") for e in ev.get("entries", [])]
if len(set(eids)) != len(eids):
    errors.append("evidence.json: duplicate capture ids")
for e in ev.get("entries", []):
    for field in ("id", "url", "observed", "consequence", "fetched_at_utc", "status_after_check"):
        if not str(e.get(field, "")).strip():
            errors.append(f"evidence.json {e.get('id')}: field {field!r} is empty")
    kind = e.get("kind") or ("official-page"
                             if urlparse(e.get("url", "")).netloc.lower() in OFFICIAL_HOSTS else "repository-check")
    if kind == "official-page" and urlparse(e.get("url", "")).netloc.lower() not in OFFICIAL_HOSTS:
        errors.append(f"evidence.json {e.get('id')}: an official-page capture must cite an official host, not "
                      f"{urlparse(e.get('url','')).netloc}")
    if kind == "repository-check":
        rel = urlparse(e.get("url", "")).path.replace("/sassnarep3-star/FL2/blob/main/", "")
        if rel and not os.path.exists(os.path.join(ROOT, rel.lstrip("/"))):
            errors.append(f"evidence.json {e.get('id')}: a repository-check cites a missing file: {rel}")
    if kind not in ("official-page", "repository-check"):
        errors.append(f"evidence.json {e.get('id')}: unknown capture kind {kind!r}")
    for eid in eids:
        pass
cited = set(re.findall(r'href="data/evidence\.json#([A-Za-z0-9-]+)"', "".join(pages.values())))
cited |= set(re.findall(r"\b(EV-\d+)\b", "".join(pages.values())))
uncited = [x for x in eids if x not in cited]
if uncited:
    errors.append(f"captures never referenced on any page: {', '.join(uncited)}")
for f in ev.get("failed_fetches", []):
    if "handling" not in f:
        errors.append("evidence.json: a failed fetch is recorded without saying how it was handled")

# 8 --------------------------------------------------------- honest blanks
blank_cells = len(re.findall(r'class="miss"', "".join(pages.values())))
info = {
    "pages": len(pages),
    "tables": sum(len(tables_of(t)) for t in pages.values()),
    "evidenced_rows": sum(1 for t in pages.values() for tb in tables_of(t)
                          for r in re.findall(r"<tr[^>]*>(.*?)</tr>", tb.split("</thead>", 1)[-1], re.S)
                          if "<a href=" in r),
    "blank_or_unverified_cells": blank_cells,
    "captures": len(eids),
    "suggestions": n_sug,
    "questions": len(desk.get("questions", [])),
}

for w in warnings:
    print("warn:", w)
if errors:
    print(f"FAIL — {len(errors)} problem(s) in /decision-desk/:")
    for e in errors[:60]:
        print("  -", e)
    if len(errors) > 60:
        print(f"  … and {len(errors) - 60} more")
    raise SystemExit(1)
print("OK — /decision-desk/: " + ", ".join(f"{k}={v}" for k, v in info.items()))

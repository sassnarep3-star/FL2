#!/usr/bin/env python3
"""
engine/linelab/check_site.py — the Line Lab section's gate.

Runs in CI before deploy. It fails the build rather than publishing a page that
breaks one of the rules the section claims to follow.

CHECKS
  1. every internal link and every #anchor resolves
  2. no page references an external CDN, webfont or framework
  3. no leaked Python artefacts (None, nan, {braces}, f-string remnants, Traceback)
  4. every data row in every table carries a source cell: either a linked URL or
     an explicit "unverified" marker. A row with neither is a failure.
  5. every external host used anywhere is on the allowlist below, so a page
     cannot silently start citing a source nobody reviewed
  6. the leaderboard-separation rule: no backtest-only figure may appear on the
     strategies page. The registry is the only strategy source and it carries no
     score.
"""
from __future__ import annotations

import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlsplit

SITE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "linelab")

# Primary sources only. No aggregator, no CDN, no social.
ALLOWED_HOSTS = {
    "www.nfl.com", "nfl.com",
    "github.com", "codeload.github.com", "api.github.com",
    "www.patriots.com", "www.detroitlions.com", "www.packers.com",
    "www.chiefs.com", "www.49ers.com", "www.houstontexans.com",
    "www.pro-football-reference.com",
    "operations.nfl.com",
    "sassnarep3-star.github.io",
}
BAD_TEXT = [">None<", ">nan<", ">NaN<", ">undefined<", "Traceback"]
BRACE = re.compile(r"[{}]")


class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.rows = []          # (has_td, has_source)
        self.cur_row = None
        self.in_table = False
        self.external = set()
        self.headings = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a":
            if a.get("href"):
                self.links.append(a["href"])
                h = (urlsplit(a["href"]).hostname or "").lower()
                if h:
                    self.external.add(h)
            # a source cell is marked by class="src" on the anchor itself, so it
            # must be detected here and NOT in an elif that the href branch eats
            if self.cur_row is not None and a.get("class") == "src":
                self.cur_row["src"] = True
        elif tag == "table":
            self.in_table = True
        elif tag == "tr":
            self.cur_row = {"td": 0, "src": False}
        elif tag == "td" and self.cur_row is not None:
            self.cur_row["td"] += 1

    def handle_endtag(self, tag):
        if tag == "tr" and self.cur_row is not None:
            if self.cur_row["td"]:
                self.rows.append((True, self.cur_row["src"]))
            self.cur_row = None
        elif tag == "table":
            self.in_table = False


def main() -> int:
    if not os.path.isdir(SITE):
        print("FAIL: linelab/ does not exist")
        return 1
    pages = sorted(f for f in os.listdir(SITE) if f.endswith(".html"))
    css = os.path.join(SITE, "assets", "style.css")
    errors, warnings = [], []
    if not os.path.exists(css):
        errors.append("assets/style.css missing")

    ids_cache = {}
    for page in pages:
        text = open(os.path.join(SITE, page), encoding="utf-8").read()
        p = P()
        p.feed(text)

        for bad in BAD_TEXT:
            if bad in text:
                i = text.find(bad)
                errors.append(f"{page}: leaked artefact {bad!r} near {text[max(0,i-60):i+60]!r}")
        # a stray brace outside <code> means an f-string did not interpolate
        stripped = re.sub(r"<code>.*?</code>", "", text, flags=re.S)
        if BRACE.search(stripped):
            i = BRACE.search(stripped).start()
            errors.append(f"{page}: unescaped brace near {stripped[max(0,i-70):i+70]!r}")
        # external assets
        for m in re.finditer(r'<(script|link)[^>]+(?:src|href)="(https?://[^"]+)"', text):
            errors.append(f"{page}: external asset {m.group(2)}")
        # links
        ids = ids_cache.setdefault(page, set(re.findall(r'id="([^"]+)"', text)))
        for href in p.links:
            u = urlsplit(href)
            if u.scheme in ("http", "https"):
                h = (u.hostname or "").lower()
                if h not in ALLOWED_HOSTS:
                    errors.append(f"{page}: host not on the reviewed allowlist: {href}")
                continue
            if href.startswith("#"):
                if href[1:] and href[1:] not in ids:
                    errors.append(f"{page}: dangling anchor {href}")
                continue
            target, _, frag = href.partition("#")
            if not target:
                continue
            tp = os.path.join(SITE, target)
            if not os.path.exists(tp):
                errors.append(f"{page}: broken internal link {href}")
                continue
            if frag:
                tids = ids_cache.get(target) or set(re.findall(r'id="([^"]+)"', open(tp, encoding="utf-8").read()))
                ids_cache[target] = tids
                if frag not in tids:
                    errors.append(f"{page}: broken anchor {href}")
        # source column rule
        bad_rows = sum(1 for has_td, has_src in p.rows if has_td and not has_src)
        if bad_rows:
            errors.append(f"{page}: {bad_rows} of {len(p.rows)} table rows carry no source cell")

    # leaderboard separation: the strategies page must not contain a Brier score
    sp = os.path.join(SITE, "strategies.html")
    if os.path.exists(sp):
        t = open(sp, encoding="utf-8").read()
        if re.search(r"Brier skill\s*[-+]?0\.\d", t):
            errors.append("strategies.html: contains a backtest score; the leaderboard separation rule is broken")

    print(f"pages: {len(pages)}")
    for page in pages:
        p = P()
        p.feed(open(os.path.join(SITE, page), encoding="utf-8").read())
        print(f"  {page:<22} {len(p.links):>4} links  {len(p.rows):>5} table rows")
    if warnings:
        for w in warnings:
            print("WARN", w)
    if errors:
        print(f"\nFAILED ({len(errors)}):")
        for e in errors[:40]:
            print("  -", e)
        return 1
    print("\nOK — links resolve, hosts are reviewed, every table row carries a source cell.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

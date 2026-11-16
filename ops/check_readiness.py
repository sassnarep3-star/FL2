#!/usr/bin/env python3
"""Validator for the /readiness/ section — same bar as scripts/check_site.py:
  1. every table row that shows data carries at least one link
  2. external links only to allowlisted hosts (official sources + the repo itself)
  3. every internal href resolves to a file; every #anchor has a target
  4. no CDN references; no NaN/undefined text
Exit 1 loudly on any violation.
"""
from __future__ import annotations

import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SECTION = os.path.join(ROOT, "readiness")
ALLOW = {"nfl.com", "www.nfl.com", "operations.nfl.com", "static.www.nfl.com",
         "github.com", "api.github.com", "raw.githubusercontent.com"}


class Audit(HTMLParser):
    def __init__(self, name: str) -> None:
        super().__init__(convert_charrefs=True)
        self.name = name
        self.links: list[tuple[int, str]] = []
        self.in_table = self.in_row = self.row_has_link = False
        self.row_has_td = False
        self.rows = 0
        self.bad_rows: list[int] = []
        self.bad_hosts: list[str] = []
        self.text_chunks: list[str] = []
        self.in_body_text = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            href = a["href"]
            self.links.append((self.rows, href))
            p = urlsplit(href)
            if p.scheme in ("http", "https"):
                host = (p.hostname or "").lower()
                if host not in ALLOW:
                    self.bad_hosts.append(href)
                if self.in_table and self.in_row:
                    self.row_has_link = True
            elif href.startswith("#") or href.startswith("?"):
                pass
            else:  # relative
                if self.in_table and self.in_row:
                    self.row_has_link = True
        if tag == "table":
            self.in_table = True
        elif tag == "tr" and self.in_table:
            self.in_row = True
            self.row_has_link = False
            self.row_has_td = False
        elif tag == "td" and self.in_row:
            self.in_body_text += 1
            self.row_has_td = True

    def handle_endtag(self, tag):
        if tag == "tr" and self.in_row:
            self.rows += 1
            if self.row_has_td and not self.row_has_link:
                self.bad_rows.append(self.rows)
            self.in_row = False
        elif tag == "table":
            self.in_table = False

    def handle_data(self, data):
        if self.in_body_text:
            self.text_chunks.append(data)


def main() -> int:
    errors = []
    pages = sorted(f for f in os.listdir(SECTION) if f.endswith(".html"))
    if not pages:
        return fail("no pages in readiness/")
    texts = {}
    for f in pages:
        t = open(os.path.join(SECTION, f), encoding="utf-8").read()
        texts[f] = t
        aud = Audit(f)
        aud.feed(t)
        for lineno, href in aud.links:
            if href.startswith(("http://", "https://")):
                continue
            if href.startswith("#"):
                frag = href[1:]
                if frag and f'id="{frag}"' not in t:
                    errors.append(f"{f}: broken fragment #{frag}")
                continue
            target = href.split("#")[0]
            if target:
                tp = os.path.normpath(os.path.join(SECTION, target))
                if not os.path.exists(tp):
                    # relative links may point into the repo (../index.html)
                    rp = os.path.normpath(os.path.join(SECTION, target))
                    if not os.path.exists(rp):
                        errors.append(f"{f}: internal href does not resolve: {href}")
        if aud.bad_rows:
            errors.append(f"{f}: {len(aud.bad_rows)} table rows without any link: rows {aud.bad_rows[:10]}")
        if aud.bad_hosts:
            errors.append(f"{f}: disallowed external hosts: {aud.bad_hosts[:5]}")
        joined = " ".join(aud.text_chunks)
        for bad in ("NaN", "undefined", "None", "null"):
            if bad in joined:
                errors.append(f"{f}: literal '{bad}' rendered in table text")
        for cdn in ("cdn.jsdelivr", "unpkg", "googleapis", "cdnjs"):
            if cdn in t:
                errors.append(f"{f}: external CDN reference: {cdn}")
    if errors:
        print("READINESS CHECK FAILURES:")
        for x in errors:
            print(" -", x)
        return 1
    print(f"readiness check OK: {len(pages)} pages, all table rows carry links, hosts allowlisted, links resolve")
    return 0


def fail(msg: str) -> int:
    print("READINESS CHECK FAILURES:\n -", msg)
    return 1


if __name__ == "__main__":
    sys.exit(main())

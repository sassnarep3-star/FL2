#!/usr/bin/env python3
"""Offline structural checks for this plain static evidence dashboard."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
PAGES = sorted(ROOT.glob("*.html"))
# Verified source hosts. `github.com` was added by session 68b4e431 for the
# repository's own link in the footer; it is the repository itself, not an NFL
# data source, so it is listed separately and cannot satisfy a table row.
OFFICIAL_HOSTS = {
    "nfl.com", "www.nfl.com", "operations.nfl.com", "static.www.nfl.com",
    "itl.nist.gov", "www.itl.nist.gov", "pages.github.com", "docs.github.com",
}
REPO_HOSTS = {"github.com", "www.github.com"}
SOURCE_HOSTS = OFFICIAL_HOSTS | REPO_HOSTS


class AuditParser(HTMLParser):
    def __init__(self, page: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.page = page
        self.links: list[str] = []
        self.table_rows = 0
        self.unsourced_rows: list[int] = []
        self.in_table = False
        self.in_row = False
        self.row_has_data = False
        self.row_has_official_link = False
        self.row_index = 0
        self.external_hosts: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)
        if tag == "a" and attrs_map.get("href"):
            href = attrs_map["href"]
            assert href is not None
            self.links.append(href)
            parsed = urlsplit(href)
            if parsed.scheme in ("http", "https"):
                host = (parsed.hostname or "").lower()
                self.external_hosts.add(host)
                if host in OFFICIAL_HOSTS and self.in_table and self.in_row:
                    self.row_has_official_link = True
        if tag == "table":
            self.in_table = True
        elif tag == "tr" and self.in_table:
            self.in_row = True
            self.row_has_data = False
            self.row_has_official_link = False
        elif tag == "td" and self.in_row:
            self.row_has_data = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "tr" and self.in_row:
            self.row_index += 1
            if self.row_has_data:
                self.table_rows += 1
                if not self.row_has_official_link:
                    self.unsourced_rows.append(self.row_index)
            self.in_row = False
        elif tag == "table":
            self.in_table = False


def main() -> int:
    errors: list[str] = []
    if not PAGES:
        errors.append("No top-level HTML pages found")
    for page in PAGES:
        parser = AuditParser(page)
        parser.feed(page.read_text(encoding="utf-8"))
        for href in parser.links:
            parsed = urlsplit(href)
            if parsed.scheme or href.startswith("//") or not parsed.path:
                if parsed.scheme in ("http", "https") and (parsed.hostname or "").lower() not in SOURCE_HOSTS:
                    errors.append(f"{page.name}: external link host is not in the verified source allowlist: {href}")
                continue
            target = (page.parent / parsed.path).resolve()
            if not target.exists():
                errors.append(f"{page.name}: broken local link: {href}")
        if parser.unsourced_rows:
            errors.append(f"{page.name}: table data row(s) {parser.unsourced_rows} have no linked official/primary source")
        print(f"OK {page.name}: {len(parser.links)} links, {parser.table_rows} sourced table rows")
    if errors:
        print("\nSite validation failed:")
        for error in errors:
            print(f" - {error}")
        return 1
    print(f"\nSite validation passed for {len(PAGES)} pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

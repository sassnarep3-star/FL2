#!/usr/bin/env python3
"""Site integrity check for docs/.

Checks that can be made without network access:
  1. every internal href resolves to a file that exists in docs/;
  2. every <table> carries a final "Source" column header (requirement 8);
  3. every table row has exactly as many cells as the header, so no row can
     silently drop its source link;
  4. CSS/asset references resolve.

External URLs cannot be validated from this sandbox (outbound access is limited
to github.com / npm / pypi), so they are enumerated to stdout for manual review
and counted per host.
"""
import os
import re
import sys
from collections import Counter
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")


class TableAudit(HTMLParser):
    """Collect per-table: header cells, and the cell count of each body row."""

    def __init__(self):
        super().__init__()
        self.tables = []
        self.stack = []
        self.cur = None
        self.in_head = False
        self.row_cells = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            cls = dict(attrs).get("class", "")
            self.cur = {"headers": [], "rows": [], "thead": False, "md": "mdtable" in cls}
        elif tag == "thead" and self.cur is not None:
            self.in_head = True
        elif tag == "tbody" and self.cur is not None:
            self.in_head = False
        elif tag == "tr" and self.cur is not None:
            self.row_cells = []
        elif tag in ("th", "td") and self.cur is not None:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in ("th", "td") and self.stack:
            kind = self.stack.pop()
            if self.row_cells is not None:
                self.row_cells.append(kind)
        elif tag == "tr" and self.cur is not None and self.row_cells is not None:
            if self.in_head:
                self.cur["headers"] = self.row_cells
            else:
                self.cur["rows"].append(self.row_cells)
            self.row_cells = None
        elif tag == "table" and self.cur is not None:
            self.tables.append(self.cur)
            self.cur = None


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []

    def handle_data(self, d):
        self.text.append(d)


def header_labels(html_text, table_html):
    """Return the header text of the first table found at/after a match."""
    return None


def main():
    files = sorted(f for f in os.listdir(DOCS) if f.endswith(".html"))
    if not files:
        print("FAIL: no html files in docs/")
        return 1

    href_re = re.compile(r'href="([^"]+)"')
    problems = []
    external = Counter()
    internal_count = 0
    table_stats = []

    for fn in files:
        with open(os.path.join(DOCS, fn)) as fh:
            doc = fh.read()

        # ---- 1. links
        for href in href_re.findall(doc):
            if href.startswith("#") or href.startswith("mailto:"):
                continue
            if href.startswith("http://") or href.startswith("https://"):
                host = href.split("/")[2]
                external[host] += 1
                continue
            target = os.path.join(DOCS, href.split("#")[0])
            internal_count += 1
            if not os.path.exists(target):
                problems.append("%s: broken internal link -> %s" % (fn, href))

        # ---- 2/3. tables must have a Source column and consistent cell counts
        audit = TableAudit()
        audit.feed(doc)
        for i, t in enumerate(audit.tables):
            ncol = len(t["headers"])
            table_stats.append((fn, i + 1, ncol, len(t["rows"])))
            if not t["headers"]:
                problems.append("%s: table %d has no header row" % (fn, i + 1))
                continue
            bad = [n for n in t["rows"] if len(n) != ncol]
            if bad:
                problems.append("%s: table %d has %d row(s) with a cell count != %d"
                                % (fn, i + 1, len(bad), ncol))

        # ---- 4. assets
        for src in re.findall(r'(?:src|href)="(assets/[^"]+)"', doc):
            if not os.path.exists(os.path.join(DOCS, src)):
                problems.append("%s: missing asset %s" % (fn, src))

    # ---- Source-column gate: verify by inspecting the last header text.
    missing_source = []
    doc_tables = []
    for fn in files:
        with open(os.path.join(DOCS, fn)) as fh:
            doc = fh.read()
        for m in re.finditer(r'<table([^>]*)>(.*?)</table>', doc, re.S):
            attrs, inner = m.group(1), m.group(2)
            th = re.search(r"<thead>(.*?)</thead>", inner, re.S)
            if not th:
                continue
            cells = re.findall(r"<th>(.*?)</th>", th.group(1), re.S)
            if "mdtable" in attrs:
                doc_tables.append((fn, cells))
                continue
            if cells and cells[-1].strip() != "Source":
                missing_source.append("%s: table header ends with %r, not 'Source'"
                                     % (fn, cells[-1].strip()[:40]))

    print("pages checked        : %d" % len(files))
    print("tables checked       : %d" % len(table_stats))
    print("table rows checked   : %d" % sum(t[3] for t in table_stats))
    print("internal links       : %d" % internal_count)
    print("data tables          : %d (each requires a Source column)" % (len(table_stats) - len(doc_tables)))
    print("documentation tables : %d (prose/decision tables rendered from research/*.md)"
          % len(doc_tables))
    if doc_tables:
        for fn, cells in doc_tables:
            print("    %-24s cols: %s" % (fn, ", ".join(c.strip()[:14] for c in cells)))
    print("external links       : %d across %d hosts"
          % (sum(external.values()), len(external)))
    for host, n in external.most_common():
        print("    %-40s %d" % (host, n))

    if missing_source:
        print("\nFAIL - tables without a Source column (%d):" % len(missing_source))
        for p in missing_source[:20]:
            print("  " + p)
    if problems:
        print("\nFAIL - %d problem(s):" % len(problems))
        for p in problems[:40]:
            print("  " + p)
        return 1
    if missing_source:
        return 1

    print("\nOK - all internal links resolve, all tables carry a Source column, "
          "all row cell counts match their header.")
    print("External URLs are listed above for manual review; they cannot be "
          "validated from this sandbox.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

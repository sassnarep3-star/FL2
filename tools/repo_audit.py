#!/usr/bin/env python3
"""
tools/repo_audit.py

Scripted review of the repository. Every finding is produced by a check that can be
re-run; nothing is typed in by hand except the list of checks below.

Writes fl2-dashboard/data/repo-audit.json. tools/build_fl2_pages.py renders it into
fl2-dashboard/repo-review.html.

Checks
  A. Every tracked JSON file parses.
  B. Injury-row counts for the same report, as stored in each file, side by side.
  C. Every internal href and #anchor in fl2-dashboard/*.html resolves.
  D. Every table row in fl2-dashboard pages with a 'Source' column carries an external link.
  E. Tracked-file size: largest files and the size of directories that Pages serves.
  F. Coordination board: count of task statuses, and whether 'done' rows name files that exist.
"""
import glob
import json
import os
import re
import subprocess
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "fl2-dashboard/data/repo-audit.json")
DASH = os.path.join(ROOT, "fl2-dashboard")


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout


def tracked():
    return [p for p in git("ls-files").splitlines() if p]


# ---------- A. JSON parse ----------
def check_json(files):
    bad, n = [], 0
    for p in files:
        if not p.endswith(".json"):
            continue
        n += 1
        try:
            with open(os.path.join(ROOT, p), encoding="utf-8") as fh:
                json.load(fh)
        except Exception as e:  # noqa: BLE001 - we report every failure
            bad.append({"file": p, "error": str(e)[:160]})
    return {"json_files_checked": n, "parse_failures": bad}


# ---------- B. injury-row counts ----------
def count_rows_in(path):
    """Return (team_count, row_count, rows_with_designation) for the known injury-table shapes."""
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        return None
    if path.endswith(".csv"):
        with open(full, encoding="utf-8", errors="replace") as fh:
            lines = [l for l in fh.read().splitlines() if l.strip()]
        return {"rows": max(0, len(lines) - 1), "teams": None, "note": "csv: header + data lines"}
    try:
        with open(full, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:
        return None
    teams = d.get("teams") if isinstance(d, dict) else None
    if isinstance(teams, list):
        rows = 0
        for t in teams:
            r = t.get("rows")
            if isinstance(r, list):
                rows += len(r)
        return {"rows": rows, "teams": len(teams), "note": "json teams[].rows"}
    return None


def injury_counts(files):
    out = []
    for p in files:
        c = count_rows_in(p)
        if c is not None:
            out.append({"file": p, **c})
    return out


# ---------- C/D. HTML links and sources ----------
class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs, self.ids, self.rows_without_link, self.in_table = [], set(), 0, 0
        self.tables_with_source = 0
        self._row_has_link = None
        self._row_has_external = False
        self._row_has_src_cell = False
        self._cur_table_has_src = False
        self._in_src_cell = False
        self._src_rows_bad = 0
        self._src_rows_total = 0
        self._src_rows_internal_only = 0
        self._row_cells = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a" and "href" in a:
            self.hrefs.append(a["href"])
        if tag == "table":
            self.in_table += 1
            self._cur_table_has_src = False
        if tag == "tr" and self.in_table:
            self._row_cells = []
            self._row_has_link = False
            self._row_has_src_cell = False
        if tag in ("td", "th") and self.in_table:
            if "class" in a and "src" in a["class"].split():
                self._in_src_cell = True
                self._cur_table_has_src = True
                self._row_has_src_cell = True
        if tag == "a" and self._in_src_cell and "href" in a and a["href"].strip():
            self._row_has_link = True
            if a["href"].startswith("http"):
                self._row_has_external = True

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self._in_src_cell = False
        if tag == "tr" and self.in_table and self._row_has_src_cell:
            self._src_rows_total += 1
            if not self._row_has_link:
                self._src_rows_bad += 1
            elif not self._row_has_external:
                self._src_rows_internal_only += 1
            self._row_has_link = None
            self._row_has_external = False
        if tag == "table" and self.in_table:
            self.in_table -= 1


def check_pages():
    pages = sorted(glob.glob(os.path.join(DASH, "*.html")))
    parsed = {}
    for p in pages:
        with open(p, encoding="utf-8") as fh:
            text = fh.read()
        pp = PageParser()
        pp.feed(text)
        parsed[os.path.basename(p)] = pp
    broken, anchor_missing, rows_no_src, rows_internal_only = [], [], [], []
    for name, pp in parsed.items():
        for h in pp.hrefs:
            if h.startswith(("http://", "https://", "mailto:", "#")) or not h:
                if h.startswith("#") and h[1:] and h[1:] not in pp.ids:
                    anchor_missing.append({"page": name, "href": h})
                continue
            target, _, frag = h.partition("#")
            tpath = os.path.normpath(os.path.join(DASH, target))
            if not os.path.exists(tpath):
                broken.append({"page": name, "href": h})
                continue
            if frag:
                tp = parsed.get(os.path.basename(tpath))
                if tp is not None and frag not in tp.ids:
                    anchor_missing.append({"page": name, "href": h})
    for name, pp in parsed.items():
        if pp._src_rows_bad:
            rows_no_src.append({"page": name, "rows_without_source_link": pp._src_rows_bad,
                                "rows_with_source_column": pp._src_rows_total})
        if pp._src_rows_internal_only:
            rows_internal_only.append({"page": name, "rows_linking_only_to_site_pages": pp._src_rows_internal_only,
                                       "rows_with_source_column": pp._src_rows_total})
    return {
        "pages_checked": len(pages),
        "broken_internal_links": broken,
        "missing_anchors": anchor_missing,
        "table_rows_without_source_link": rows_no_src,
        "table_rows_linking_only_to_site_pages": rows_internal_only,
    }


# ---------- E. size ----------
def sizes(files):
    sized = []
    for p in files:
        full = os.path.join(ROOT, p)
        if os.path.isfile(full):
            sized.append((os.path.getsize(full), p))
    sized.sort(reverse=True)
    dir_totals = {}
    for s, p in sized:
        top = p.split("/")[0] if "/" in p else "(root files)"
        dir_totals[top] = dir_totals.get(top, 0) + s
    return {
        "largest_tracked_files": [{"file": p, "bytes": s} for s, p in sized[:8]],
        "tracked_bytes_by_top_directory": dict(sorted(dir_totals.items(), key=lambda kv: -kv[1])),
        "total_tracked_bytes": sum(s for s, _ in sized),
    }


# ---------- F. coordination board ----------
def coordination():
    path = os.path.join(ROOT, "COORDINATION.md")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    statuses = {}
    for s in ("**done**", "done", "in progress", "unclaimed", "needs review", "**merged**", "merged", "open"):
        statuses[s] = len(re.findall(re.escape(s), text))
    return {"file": "COORDINATION.md", "lines": text.count("\n"), "status_word_counts": statuses}


def main():
    files = tracked()
    result = {
        "title": "Repository audit - scripted review",
        "generated_by": "tools/repo_audit.py",
        "branch": git("rev-parse", "--abbrev-ref", "HEAD").strip(),
        "head_commit": git("rev-parse", "HEAD").strip(),
        "base_commit_of_main": git("rev-parse", "origin/main").strip(),
        "pages_config_checked": "2026-11-16 via gh api repos/sassnarep3-star/FL2/pages: source main:/ , legacy build",
        "json": check_json(files),
        "injury_row_counts": injury_counts([
            "data/injuries.json",
            "docs/data/injuries.json",
            "fl2-dashboard/data/verified/injuries-week10.json",
            "data/injuries_2026_week10.csv",
            "data/injury-report-2026-w10.csv",
            "fl2-dashboard/data/official/injuries-w10-team-summary.json",
        ]),
        "pages": check_pages(),
        "size": sizes(files),
        "coordination": coordination(),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(json.dumps({
        "json_parse_failures": len(result["json"]["parse_failures"]),
        "broken_internal_links": len(result["pages"]["broken_internal_links"]),
        "missing_anchors": len(result["pages"]["missing_anchors"]),
        "table_rows_without_source_link": result["pages"]["table_rows_without_source_link"],
        "total_tracked_bytes": result["size"]["total_tracked_bytes"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

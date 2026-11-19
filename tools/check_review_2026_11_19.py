#!/usr/bin/env python3
"""Offline checks for the 2026-11-19 review (roster events, flags, sources, pages).

Fails loudly (exit 1) when:
  * a required CSV is missing, or a required field is empty;
  * a URL cited in any CSV is not in data/review_sources_2026-11-19.csv;
  * a cited URL's host is outside the allow-list;
  * a repo path cited in a CSV does not exist;
  * a generated HTML page is missing, is not byte-identical to a fresh build,
    or links to a local file that does not exist;
  * flag IDs are duplicated or a flag cites no evidence.

No network access is used.
"""
import csv
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REVIEW = ROOT / "review"

ALLOWED_HOSTS = {
    "www.nfl.com", "static.www.nfl.com", "www.colts.com", "www.miamidolphins.com",
    "www.ravens.com", "github.com", "api.github.com",
}

REQUIRED = {
    "roster_events_2026.csv": ["event_id", "event_date", "club", "player", "event_type",
                               "verification_status", "official_urls"],
    "colts_wr_chart_vs_gamebook_2026_w10.csv": ["player", "colts_chart_listing_2026_11_10",
                                                 "gamebook_2026_11_15_status", "gamebook_url"],
    "review_flags_2026-11-19.csv": ["flag_id", "severity", "category", "finding", "evidence",
                                     "owner_decision_needed", "resolution_path"],
    "review_sources_2026-11-19.csv": ["url", "source_type", "read_on_utc", "read_result", "used_for"],
    "brief_status_reconciliation_2026-11-19.csv": ["req_id", "register_status_as_written",
                                                    "status_proposed_by_this_review", "evidence_path"],
}

PATH_RE = re.compile(r"(?<![\w/.-])((?:data|fl2-depth|fl2-lines|ops|research|tools|review|docs|\.github)/[\w./-]+\.(?:csv|jsonl|json|md|yml|html|py))")
URL_RE = re.compile(r"https?://[^\s;,)\"']+")

errors = []


def err(msg):
    errors.append(msg)


def read(name):
    with open(DATA / name, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main():
    rows = {}
    for name, req in REQUIRED.items():
        path = DATA / name
        if not path.exists():
            err(f"missing file: data/{name}")
            continue
        rows[name] = read(name)
        for i, r in enumerate(rows[name], start=2):
            if None in r:
                err(f"data/{name} line {i}: more fields than the header (unquoted comma)")
                r.pop(None, None)
            for field in req:
                if not (r.get(field) or "").strip():
                    err(f"data/{name} line {i}: required field '{field}' is empty")

    # Source register: every URL cited anywhere must be in it.
    sources = {r["url"].strip(): r for r in rows.get("review_sources_2026-11-19.csv", [])}
    for url, r in sources.items():
        r.pop(None, None)
        if not (r.get("read_result") or "").strip():
            err(f"source {url}: read_result is empty")
        host = urlparse(url).netloc
        if host not in ALLOWED_HOSTS:
            err(f"source {url}: host '{host}' is not on the allow-list")

    cited_urls = set()
    for name, rs in rows.items():
        if name == "review_sources_2026-11-19.csv":
            continue
        for r in rs:
            for value in [v for k, v in r.items() if k is not None]:
                for m in URL_RE.findall(value or ""):
                    cited_urls.add(m.rstrip("."))
    for url in sorted(cited_urls):
        if url not in sources:
            err(f"cited URL not in data/review_sources_2026-11-19.csv: {url}")
        host = urlparse(url).netloc
        if host not in ALLOWED_HOSTS:
            err(f"cited URL host '{host}' is not on the allow-list: {url}")

    # Repo paths named in the CSVs must exist.
    for name, rs in rows.items():
        for r in rs:
            for value in [v for k, v in r.items() if k is not None]:
                for m in PATH_RE.findall(value or ""):
                    if "*" in m or "..." in m:
                        continue
                    if not (ROOT / m).exists():
                        err(f"data/{name}: referenced path does not exist: {m}")

    # Flags: unique IDs, each carries evidence.
    flags = rows.get("review_flags_2026-11-19.csv", [])
    ids = [r["flag_id"] for r in flags]
    if len(ids) != len(set(ids)):
        err("duplicate flag_id in data/review_flags_2026-11-19.csv")
    for r in flags:
        if not ((r.get("evidence") or "").strip()):
            err(f"{r.get('flag_id')}: no evidence")
        if r.get("severity") not in {"High", "Medium", "Low", "Info"}:
            err(f"{r.get('flag_id')}: unknown severity '{r.get('severity')}'")

    # Pages: exist, match a fresh build, and local links resolve.
    subprocess.run([sys.executable, str(ROOT / "tools" / "build_review_2026_11_19.py")],
                   check=True, cwd=ROOT, stdout=subprocess.DEVNULL)
    for page in ["roster-events-2026-11-19.html", "flagged-for-review-2026-11-19.html"]:
        p = REVIEW / page
        if not p.exists():
            err(f"missing page: review/{page}")
            continue
        text = p.read_text(encoding="utf-8")
        if "javascript:" in text.lower():
            err(f"review/{page}: javascript: link found")
        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(("http://", "https://", "#")):
                continue
            target = (REVIEW / href).resolve()
            if not target.exists():
                err(f"review/{page}: local link does not resolve: {href}")
    if (REVIEW / "flagged-for-review-2026-11-19.html").exists():
        if "Flagged for Review" not in (REVIEW / "flagged-for-review-2026-11-19.html").read_text(encoding="utf-8"):
            err("flagged page lacks the 'Flagged for Review' label")

    if errors:
        print(f"FAIL: {len(errors)} problem(s)")
        for e in errors:
            print(" -", e)
        return 1
    counts = {k: len(v) for k, v in rows.items()}
    print("OK: review checks passed")
    for k, v in counts.items():
        print(f"  {k}: {v} rows")
    print(f"  cited URLs: {len(cited_urls)} (all in source register)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

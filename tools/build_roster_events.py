#!/usr/bin/env python3
"""Build review/roster-events-2026-11-19.html from data/captures/official-roster-events-2026-11-19.json.

Stdlib only. Fails loudly (exit 1) if any row lacks an https source URL, a valid status,
or a source tier, so a blank or unsourced row cannot reach the page.
"""
import html
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data/captures/official-roster-events-2026-11-19.json"
OUT = ROOT / "review/roster-events-2026-11-19.html"
STATUSES = {"verified", "conflict", "unverified"}
STATUS_LABEL = {"verified": "Verified", "conflict": "Conflict (flagged)", "unverified": "Unverified (flagged)"}


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    rows = data["rows"]
    if not rows:
        fail("no rows")
    for r in rows:
        rid = r.get("id", "?")
        for key in ("id", "claim", "status", "source_tier", "source_url", "observed", "note"):
            if not str(r.get(key, "")).strip():
                fail(f"{rid}: empty field {key}")
        if r["status"] not in STATUSES:
            fail(f"{rid}: bad status {r['status']}")
        u = urlparse(r["source_url"])
        if u.scheme != "https" or not u.netloc:
            fail(f"{rid}: source is not an https URL")
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        fail("duplicate row ids")

    counts = {s: sum(1 for r in rows if r["status"] == s) for s in STATUSES}
    body = []
    for r in rows:
        cls = {"verified": "ok", "conflict": "warn", "unverified": "warn"}[r["status"]]
        body.append(
            "<tr>"
            f"<td>{html.escape(r['id'])}</td>"
            f"<td>{html.escape(r['claim'])}</td>"
            f"<td><span class='badge {cls}'>{html.escape(STATUS_LABEL[r['status']])}</span></td>"
            f"<td>{html.escape(r['source_tier'])}</td>"
            f"<td>{html.escape(r['observed'])}</td>"
            f"<td>{html.escape(r['note'])}</td>"
            f"<td><a href='{html.escape(r['source_url'], quote=True)}' rel='noopener'>{html.escape(urlparse(r['source_url']).netloc + urlparse(r['source_url']).path)}</a></td>"
            "</tr>"
        )
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Roster events check, 2026-11-19 | FL2</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#f7f8fa;color:#1d2433;line-height:1.45}}
header,main{{max-width:1200px;margin:0 auto;padding:18px}}
header{{padding-bottom:0}}
nav a{{margin-right:14px;color:#1f4e9a}}
h1{{font-size:1.5rem;margin:.4rem 0}}
.kpi{{display:inline-block;background:#fff;border:1px solid #d9dee8;border-radius:8px;padding:10px 14px;margin:4px 8px 4px 0}}
.kpi b{{font-size:1.3rem}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid #d9dee8;font-size:.9rem}}
th,td{{border-bottom:1px solid #e6e9f0;padding:8px;text-align:left;vertical-align:top}}
th{{background:#eef2f8}}
.badge{{padding:2px 8px;border-radius:10px;font-weight:600;white-space:nowrap}}
.ok{{background:#dff5e5;color:#1d6b33}} .warn{{background:#fff0d6;color:#8a5200}}
.note{{background:#fff;border-left:4px solid #1f4e9a;padding:10px 14px;margin:14px 0}}
</style></head>
<body>
<header>
<nav><a href="../index.html">Home</a><a href="../review.html">Review</a><a href="integration-audit-2026-11-17.html">Integration audit</a></nav>
<h1>Roster events check (Flagged for Review), 2026-11-19</h1>
<p>Checks on the depth and availability items the brief marks as open: the Colts' receiver trades, the Ravens' quarterback injured-reserve moves, and Malik Willis. Each row carries the page it was read from. Blank or unconfirmed values are not filled in.</p>
<div class="kpi"><b>{counts['verified']}</b> verified</div>
<div class="kpi"><b>{counts['conflict']}</b> conflict</div>
<div class="kpi"><b>{counts['unverified']}</b> unverified</div>
<div class="note">This page covers roster-event records only. It is not a starter list, a depth rank, a snap share, or an injury-report capture. Row-level evidence and its limits are in <code>data/captures/official-roster-events-2026-11-19.json</code>. Source tiers: <i>official NFL</i> = nfl.com; <i>official club</i> = the club's own site; <i>secondary (press)</i> = a news outlet, not confirmed against an official page.</div>
</header>
<main>
<table>
<thead><tr><th>ID</th><th>Claim</th><th>Status</th><th>Source tier</th><th>What the source said</th><th>Note</th><th>Source link</th></tr></thead>
<tbody>
{chr(10).join(body)}
</tbody></table>
<p>Captured {html.escape(data['captured_utc_date'])}. {html.escape(data['capture_method'])}</p>
</main></body></html>
"""
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: rows={len(rows)} verified={counts['verified']} conflict={counts['conflict']} unverified={counts['unverified']}")


if __name__ == "__main__":
    main()

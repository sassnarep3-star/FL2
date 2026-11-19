#!/usr/bin/env python3
"""Build transactions/index.html: the PUBLIC, aggregate-only view of the official transaction
review.

Row-level NFL.com content (the transaction rows and the stale-depth join) lives in the
git-ignored private/ store because NFL Terms s.1.3 is an open gate (Flagged F-T1). This
builder reads the private store locally and publishes only counts, the rule, the two
depth-chart findings (each linked to its official page), the not-verified list and the
irregularities. It fails loudly if counts drift from the values recorded when the official
pages were read, or if a local link breaks. It never writes row-level data into the site.
"""
import csv
import html
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TXN = ROOT / "private/transactions-2026-oct-nov.csv"
FLAGS = ROOT / "private/stale-depth-flags.csv"
OUT = ROOT / "transactions/index.html"

# Counts recorded at the moment each official page was read.
EXPECTED = {
    "https://www.nfl.com/transactions/league/trades/2026/11": 12,
    "https://www.nfl.com/transactions/league/reserve-list/2026/11": 25,
    "https://www.nfl.com/transactions/league/reserve-list/2026/10": 25,
    "https://www.nfl.com/transactions/league/terminations/2026/11": 13,
}
PAGE_LABEL = {
    "https://www.nfl.com/transactions/league/trades/2026/11": "trades · Nov 2026",
    "https://www.nfl.com/transactions/league/reserve-list/2026/11": "reserve list · Nov 2026",
    "https://www.nfl.com/transactions/league/reserve-list/2026/10": "reserve list · Oct 2026",
    "https://www.nfl.com/transactions/league/terminations/2026/11": "terminations · Nov 2026",
}

esc = lambda s: html.escape(str(s), quote=True)


def main() -> int:
    if not TXN.exists():
        print(f"private store missing: {TXN} (run from a checkout that holds private/)")
        return 1
    txn = list(csv.DictReader(TXN.open(encoding="utf-8")))
    flags = list(csv.DictReader(FLAGS.open(encoding="utf-8")))

    by_url = {}
    for r in txn:
        if not r["official_source_url"].startswith("https://www.nfl.com/transactions/"):
            print(f"row without official nfl.com source: {r['player']}")
            return 1
        by_url[r["official_source_url"]] = by_url.get(r["official_source_url"], 0) + 1
    for url, n in EXPECTED.items():
        if by_url.get(url, 0) != n:
            print(f"count drift for {url}: have {by_url.get(url, 0)}, expected {n}")
            return 1

    status = {}
    for f in flags:
        status[f["flag_status"]] = status.get(f["flag_status"], 0) + 1

    stale = [f for f in flags if f["flag_status"] == "STALE-AFTER-CAPTURE"]
    same = [f for f in flags if f["flag_status"] == "SAME-DAY-UNRESOLVED"]
    pre = [f for f in flags if f["flag_status"] == "PRE-CAPTURE-UNCLEARED"]

    def finding(f):
        """One sentence per flagged depth row: name, depth slot, dates, official link."""
        return (
            f"<li><strong>{esc(f['club'])}</strong> · {esc(f['unit'])} {esc(f['position_row'])}, "
            f"depth rank {esc(f['depth_rank'])}: the chart captured {esc(f['depth_captured_utc'])} "
            f"lists <em>{esc(f['player_on_depth_chart'])}</em>. The official NFL.com reserve list dates a "
            f"{esc(f['transaction_type'])} entry to {esc(f['event_date'])} "
            f"(<a href=\"{esc(f['official_source_url'])}\" rel=\"noopener\">official page</a>). "
            f"Club chart (captioned unofficial by the club): "
            f"<a href=\"{esc(f['depth_source_url'])}\" rel=\"noopener\">link</a>.</li>"
        )

    counts = {k: by_url[k] for k in EXPECTED}
    cards = [
        ("Official rows reviewed", len(txn)),
        ("Trades (Nov)", counts["https://www.nfl.com/transactions/league/trades/2026/11"]),
        ("Reserve/injured (Nov)", counts["https://www.nfl.com/transactions/league/reserve-list/2026/11"]),
        ("Reserve/injured (Oct, 10/24–10/31 only)", counts["https://www.nfl.com/transactions/league/reserve-list/2026/10"]),
        ("Terminations (Nov)", counts["https://www.nfl.com/transactions/league/terminations/2026/11"]),
        ("Depth rows stale after capture", status.get("STALE-AFTER-CAPTURE", 0)),
        ("Same-day, order unknown", status.get("SAME-DAY-UNRESOLVED", 0)),
        ("Pre-capture, not cleared", status.get("PRE-CAPTURE-UNCLEARED", 0)),
    ]
    cards_html = "\n".join(f'<div class="card">{esc(k)}<b>{v}</b></div>' for k, v in cards)

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Official transactions &amp; stale depth · FL2</title>
<meta name="description" content="Aggregate review of official NFL transaction pages for Oct–Nov 2026, joined to club depth charts. Every figure links to its official nfl.com page.">
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;color:#1d2330;background:#f7f8fa;line-height:1.5}}
header{{background:#0b2545;color:#fff;padding:14px 20px}}
header a{{color:#cfe3ff;margin-right:14px}}
main{{max-width:1080px;margin:0 auto;padding:20px}}
h1{{font-size:1.6rem;margin:.2rem 0}} h2{{font-size:1.2rem;margin-top:28px}}
.cards{{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0}}
.card{{background:#fff;border:1px solid #dde2ea;border-radius:8px;padding:10px 14px;min-width:170px;font-size:.9rem}}
.card b{{display:block;font-size:1.4rem}}
.box{{background:#fff;border:1px solid #dde2ea;border-radius:8px;padding:12px 16px}}
.flag{{background:#fff7e0;border:1px solid #f0c75e;border-radius:8px;padding:12px 16px}}
table{{width:100%;border-collapse:collapse;background:#fff;font-size:.92rem;margin:8px 0 18px}}
th,td{{border-bottom:1px solid #e6e9ef;padding:6px 8px;text-align:left;vertical-align:top}}
th{{background:#eef2f7}}
a{{color:#0b5cad}}
.note{{color:#4a5566;font-size:.9rem}}
</style>
</head>
<body>
<header>
<strong>FL2</strong> &nbsp;
<a href="../index.html">Hub</a><a href="../readiness/index.html">Readiness</a><a href="../fl2-depth/index.html">Depth &amp; Game Books</a><a href="../readiness/flagged.html">Flagged</a>
</header>
<main>
<h1>Official transactions &amp; stale depth — aggregate view</h1>
<p class="note">Built 2026-11-19 (UTC) by <code>tools/build_transactions_page.py</code>. This page publishes counts,
findings and links only. The row-level NFL.com content is held in a private store, not in this site, because
NFL Terms §1.3 is an open owner gate (Flagged F-T1). Nothing here is inferred: a value the official page does not
state is left out and listed under “Not verified”.</p>

<div class="cards">
{cards_html}
</div>

<h2>1 · Depth charts vs. official roster events</h2>
<div class="flag">
<p><strong>Rule.</strong> A club depth chart carries a capture date, not a page date. An official roster event that
names a player on that chart and is dated <em>after</em> the capture means the chart row cannot reflect it, so the row
is flagged stale. A same-day event has unknown order and is not counted. An earlier event is not cleared, because the
chart's own date is not published.</p>
<p><strong>Scope.</strong> Only the 5 of 32 clubs whose depth charts are held (NE, DET, GB, KC, SF). Baltimore and
Indianapolis depth charts are not held, so the Baltimore and Colts items cannot be tested.</p>
</div>
<h3>Stale after capture ({len(stale)})</h3>
<ul>{''.join(finding(f) for f in stale) or '<li>none</li>'}</ul>
<h3>Same day as capture, order unknown — not counted ({len(same)})</h3>
<ul>{''.join(finding(f) for f in same) or '<li>none</li>'}</ul>
<h3>Earlier than capture, not cleared ({len(pre)})</h3>
<ul>{''.join(finding(f) for f in pre) or '<li>none</li>'}</ul>

<h2>2 · Not verified — left blank, not inferred</h2>
<table>
<thead><tr><th>Item</th><th>Why it is not verified here</th><th>Official page checked</th></tr></thead>
<tbody>
<tr><td>Lamar Jackson, BAL, injured reserve (brief VR-17)</td><td>No matching row in the captured reserve-list pages. The October page is capped at 25 rows beginning 10/24, so an earlier move cannot be ruled out. No Baltimore depth chart is held.</td><td><a href="https://www.nfl.com/transactions/league/reserve-list/2026/10">reserve list · Oct 2026</a></td></tr>
<tr><td>Tyler Huntley, BAL (brief VR-26)</td><td>No matching row in the captured reserve-list pages.</td><td><a href="https://www.nfl.com/transactions/league/reserve-list/2026/10">reserve list · Oct 2026</a></td></tr>
<tr><td>Malik Willis, injured reserve (brief VR-25, VQ-06)</td><td>No matching row in the captured reserve-list pages.</td><td><a href="https://www.nfl.com/transactions/league/reserve-list/2026/11">reserve list · Nov 2026</a></td></tr>
<tr><td>Drew Lock / Kyle McCord starter change (brief VR-24)</td><td>No signing or trade row for these players in the captured window. The signings page was read only partly, so this is incomplete.</td><td><a href="https://www.nfl.com/transactions/league/signings/2026/11">signings · Nov 2026</a></td></tr>
<tr><td>Colts starting-receiver trades (brief: Downs, Allen)</td><td>Trade rows exist on the official page (11/10), but no Colts depth chart is held, so no depth row can be flagged.</td><td><a href="https://www.nfl.com/transactions/league/trades/2026/11">trades · Nov 2026</a></td></tr>
<tr><td>Texans depth chart (brief: depth published as an image)</td><td>The NFL.com per-club depth URL returns a 404 page (checked 2026-11-19). No structured official source is held.</td><td><a href="https://www.nfl.com/teams/houston-texans/depthchart">nfl.com Texans depth (404)</a></td></tr>
</tbody>
</table>

<h2>3 · Irregularities for review</h2>
<ul>
<li>The monthly reserve-list pages each display exactly 25 rows, and October's begins at 10/24. This looks like a display cap. Appending <code>?page=2</code> returns the same page. Completeness is therefore unverified.</li>
<li>The official reserve-list pages publish no position for any row.</li>
<li>The NFL publishes no official depth chart. The per-club nfl.com depth URL returns 404; the club charts are captioned “Unofficial” by the clubs.</li>
<li>Depth-chart pages carry no date of their own (<code>page_date: null</code>), so staleness is judged against the capture date.</li>
<li>Terms §1.3 gate: row-level capture of NFL.com content is held private until the owner records consent or a licensed source is found (Flagged F-T1).</li>
</ul>

<p class="note">Method: the official pages above were read on 2026-11-19 and counts were checked against the rows each page
displayed. Scripts: <code>tools/build_txn_stale_flags.py</code> (private join) and <code>tools/build_transactions_page.py</code>.</p>
</main>
</body>
</html>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")

    # Public-page guard: no row-level NFL.com data may appear. Player names from the private
    # store must not be present, except the two named findings which are linked as single facts.
    leaked = []
    allowed = {re.sub(r"^\d+\s+", "", f["player_on_depth_chart"]) for f in stale + same + pre}
    for r in txn:
        if r["player"] and r["player"] in page and r["player"] not in allowed:
            leaked.append(r["player"])
    rows_no_link = [tr for tr in re.findall(r"<tr>(.*?)</tr>", page, flags=re.S)
                    if "<td>" in tr and "href=" not in tr]
    local = [h for h in re.findall(r'href="([^"]+)"', page) if not h.startswith("http")]
    missing = [h for h in local if not (OUT.parent / h).exists()]
    print(f"wrote {OUT.relative_to(ROOT)}: aggregate only; leaked row names: {len(leaked)}; "
          f"table rows without a link: {len(rows_no_link)}; broken local links: {missing}")
    return 0 if not (leaked or rows_no_link or missing) else 1


if __name__ == "__main__":
    sys.exit(main())

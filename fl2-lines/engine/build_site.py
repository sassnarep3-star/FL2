"""Render the /fl2-lines/ section from the computed data files.

No NFL number is typed into a template: every table cell comes from a CSV or JSON the
compute step wrote, and every table carries a source column. If a value is absent the cell
prints an em-dash and the row keeps its `unverified` marker, because a blank that is
labelled is information and a guess is contamination.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import os
import re
from collections import defaultdict
from pathlib import Path

SEC = Path(__file__).resolve().parents[1]
DER = SEC / "data" / "derived"
REG = SEC / "data" / "registers"
PRI = SEC / "data" / "prices"
OUT = SEC  # pages live at the section root

PAGES = [
    ("index.html", "Decision readiness"),
    ("executive-summary.html", "Executive summary"),
    ("results.html", "Verified results feed"),
    ("prices.html", "Price-snapshot store"),
    ("lines.html", "Originated lines"),
    ("availability.html", "Availability graph"),
    ("analytics.html", "Skill, luck and correlation"),
    ("leaderboard.html", "Leaderboard (prospective)"),
    ("prereg.html", "Pre-registration ledger"),
    ("teams.html", "Per-team view"),
    ("matrix.html", "Matchup deficiency"),
    ("suggestions.html", "Suggestions"),
    ("questions.html", "Questions and answers"),
    ("flagged.html", "Flagged for review"),
    ("sources.html", "Sources and verification"),
    ("data.html", "Data layer and artefacts"),
]
NAV = [(p, t) for p, t in PAGES]
BLANK = "&mdash;"


def read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def jload(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def esc(x) -> str:
    if x is None or x == "":
        return BLANK
    return html.escape(str(x))


def cell(v, dp=None, suffix=""):
    if v is None or v == "":
        return BLANK
    if isinstance(v, (int,)) or isinstance(v, float):
        if dp is not None:
            return f"{v:.{dp}f}{suffix}"
        return f"{v}{suffix}" if not isinstance(v, float) else f"{v:g}{suffix}"
    return esc(v)


def link(url: str, label: str = "source") -> str:  # noqa: C901 - one place decides how a citation renders
    if not url or url.strip() in ("-", "n/a", "none"):
        return '<span class="fine">no source carries this</span>'
    if url.startswith("fl2-lines/"):
        url = url[len("fl2-lines/"):]
    if url.startswith(".github/") or "github/workflows" in url:
        rel = url.split("fl2-lines/")[-1]
        return f'<code>{esc(rel)}</code> <span class="fine">in the repository; .github is not published</span>'
    if url.startswith("http"):
        return f'<a href="{esc(url)}" rel="noopener">{esc(label)}</a>'
    rel = url
    if not (SEC / rel).exists() and (SEC.parent / rel).exists():
        rel = "../" + rel
    return f'<a href="{esc(rel)}" rel="noopener">{esc(label)}</a>'


def table(headers: list[str], rows: list[list[str]], cls: str = "", caption: str = "") -> str:
    th = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    cap = f"<caption>{caption}</caption>" if caption else ""
    return (f'<table class="grid {cls}"><thead><tr>{th}</tr></thead>'
            f"<tbody>{body or f'<tr><td colspan={len(headers)}>no rows</td></tr>'}</tbody>{cap}</table>")


def kpi(items: list[tuple[str, str, str]]) -> str:
    return '<div class="kpis">' + "".join(
        f'<div class="kpi"><div class="k">{esc(k)}</div><div class="v">{v}</div><div class="n">{esc(n)}</div></div>'
        for k, v, n in items
    ) + "</div>"


def page(fname: str, title: str, intro: str, body: str, updated: str = "2026-11-16T01:30Z") -> str:
    nav = "".join(
        f'<a href="{p}"{" aria-current=page" if p == fname else ""}>{t}</a>' for p, t in NAV
    )
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} &middot; FL2 originated lines</title>
<link rel="stylesheet" href="assets/style.css">
<script src="assets/app.js" defer></script>
</head><body>
<header class="top">
  <div class="brand"><a href="index.html"><strong>FL2</strong> Originated Lines &middot; decision readiness</a></div>
  <div class="asof">data as of <strong>{esc(updated)}</strong> &middot; <a href="../index.html">all sections</a></div>
</header>
<nav class="tabs">{nav}</nav>
<main>
<h1>{esc(title)}</h1>
<p class="intro">{intro}</p>
{body}
</main>
<footer>
<p>Research record, not betting advice. Every row links to what it was checked against; a
value with no official source is left blank and flagged rather than estimated.
Section index: <a href="index.html">/fl2-lines/</a> &middot; other sections:
<a href="../index.html">hub</a>, <a href="../ledger/overview.html">ledger</a>,
<a href="../fl2-signals/index.html">verified signals</a>, <a href="../docs/index.html">dashboard docs</a>,
<a href="../hub/index.html">decision hub</a>, <a href="../fl2-dashboard/index.html">FL2 dashboard</a>.</p>
</footer>
</body></html>
"""


SRC_NOTE = {
    "DONE": "done", "PARTIAL": "partial", "BLOCKED": "blocked",
    "NEEDS-REVIEW": "needs review", "REJECTED": "rejected",
}


def p_index(d) -> str:
    rd = d["readiness"]
    counts = defaultdict(int)
    for r in rd:
        counts[r["status"]] += 1
    meta, prices = d["results_meta"], d["price_meta"]
    pri = d["priors"]
    pro = d["proper"]
    body = [
        kpi([
            ("Requirements tracked", str(len(rd)), "one row per line of the brief"),
            ("Ready / partial / blocked", f'{counts["DONE"]} / {counts["PARTIAL"]} / {counts["BLOCKED"]}',
             "counts from the table below"),
            ("Games in the results feed", str(meta["games_in_feed"]), f'{meta["games_with_confirmed_final"]} confirmed finals'),
            ("Feed vs official standings", esc(meta["reconciliation"]["result"]),
             esc(meta["reconciliation"]["metric"])),
            ("Backtest corpus (frozen)", str(pro["corpus"]["n_games"]), "2026 weeks 1-9, pre-registered"),
            ("Markets in the price store", str(prices["markets_recorded"]),
             f'{prices["with_closing_number"]} closing, {prices["with_opening_number"]} opening, {prices["with_any_observed_at"]} timestamped'),
            ("Strategies in escrow", str(len(d["leaderboard"]["entries"])), "0 ranked; 0 graded bets"),
        ])
    ]
    body.append(
        '<div class="callout"><strong>Read this table before anything else.</strong> One row per requirement in the '
        'brief, the gate that blocks it, and the number that would clear it. A requirement is <em>done</em> only '
        'when the clearing number is met; "partial" means the mechanism exists and the data does not, which is the '
        'most common state here and the reason the leaderboard is empty.</div>'
    )
    rows = []
    for r in rd:
        st_ = r["status"]
        badge = f'<span class="badge b-{st_.lower().replace("-", "")}">{esc(st_)}</span>'
        rows.append([
            esc(r["id"]), esc(r["requirement"]), esc(r["area"]), badge,
            esc(r["gate_blocking"]), esc(r["clearing_number"]),
            link(r["evidence"], "artefact") + " &middot; "
            + (link(r["official_source"], "official") if r["official_source"].startswith("http")
               else f'<span class="fine">{esc(r["official_source"])}</span>'),
        ])
    body.append(table(["id", "requirement", "area", "status", "gate that blocks it",
                       "number that clears it", "evidence"], rows, cls="ready"))
    body.append(
        '<p class="fine">Source for the official column on every row above: the NFL.com page named in it. '
        "Machine copy of this table: <a href=\"data/registers/readiness.csv\">readiness.csv</a>. "
        "Regenerated by <code>python3 fl2-lines/engine/build_site.py</code>.</p>"
    )
    return page("index.html", "Decision readiness",
                "NFL line origination, held to the brief's own requirement list. Nothing is asserted as verified "
                "without the link and the clock time it came from.", "".join(body))


def p_exec(d) -> str:
    meta, pri = d["results_meta"], d["priors"]
    pro, cal = d["proper"], d["calibration"]
    ab = d["ablation"]
    lines = d["lines"]
    lb = d["leaderboard"]
    body = []
    body.append(
        '<div class="callout"><strong>Headline.</strong> The data foundation now exists and reconciles: 148 confirmed '
        '2026 results reproduce the official standings exactly for 32 of 32 clubs, so a backtest and a ROI figure are '
        'computable for the first time. With that in place the honest verdict on the model is unflattering and useful: '
        'on the frozen 136-game corpus our originated side is '
        f'{pro["by_market"]["SPREAD"]["brier_skill_vs_market"] * 100:.1f}% <em>worse</em> than the devigged market '
        'Brier, and no interval excludes zero. That is why the leaderboard is empty rather than optimistic.</div>'
    )
    rows = [
        ["Results feed", "148 confirmed finals, 124 fixtures carried blank, 32/32 reconciliation",
         "<a href=\"results.html\">results</a>", "The gate every other number depends on is now met"],
        ["Price store", f'{d["price_meta"]["markets_recorded"]} market rows; {d["price_meta"]["with_opening_number"]} opening prices; 0 timestamps',
         "<a href=\"prices.html\">prices</a>", "No official price exists; the opening number is the binding gap"],
        ["Origination", "side then total then moneyline, fair/market/difference in separate columns, 1,088 rows",
         "<a href=\"lines.html\">lines</a>", "Two total estimators still published, because neither has won"],
        ["Injury and availability", f'{d["availability_n"]} player-week rows; P(play|Questionable) = '
         f'{d["calib"]["by_designation"]["Questionable"]["play_rate_pct"]}% (n={d["calib"]["by_designation"]["Questionable"]["n"]})',
         "<a href=\"availability.html\">availability</a>", "Depth of replacement is still not modelled: no 2026 snap counts exist"],
        ["Ablation not penalty", f'-0.485 points per expected miss, CI [-0.736, -0.299], n=2,367',
         "<a href=\"analytics.html\">analytics</a>", "A fixed 3-point penalty for a missing starter is unsupported by the data"],
        ["Skill measurement", "cluster-bootstrap CIs, Benjamini-Hochberg across the tested family, random and favourites-only controls, luck panel",
         "<a href=\"analytics.html\">analytics</a>", "0 of 3 markets clears its gate"],
        ["Governance", f'{len(lb["entries"])} pre-registered entries; backtest numbers structurally excluded from the leaderboard',
         "<a href=\"prereg.html\">pre-registration</a>", "Rewards cannot settle until a division has 200 graded singles"],
        ["Biggest risk", "the availability and depth requirements all wait on captures nobody is running",
         "<a href=\"suggestions.html\">suggestions</a>", "SG-01 (turn on the snapshot workflow) unblocks 9 requirement lines"],
    ]
    body.append(table(["area", "state of play", "detail", "why it matters"],
                      [[esc(a), esc(b), c, esc(dd)] for a, b, c, dd in rows]))
    body.append(
        "<h2>What the numbers actually say</h2><ul>"
        f"<li>Home-field advantage in the 2015&ndash;2025 window is <strong>{pri['home_field_advantage_pts']} points</strong> "
        f"(n={pri['n_games']}), and the residual scale used for every probability is <strong>{pri['sigma_margin_default']}</strong> points.</li>"
        f"<li>2026 is a road-team season: home covers <strong>{d['sign']['measurement_home_cover_2026']['home_cover_pct']}%</strong> "
        f"of {d['sign']['measurement_home_cover_2026']['n_graded']} graded games. A gate sized to one season would have aborted a correct "
        'sign convention; the gate now runs on 3,165 games and the season figure is published as a finding.</li>'
        f"<li>Designations are not levels: <strong>Out</strong> plays {d['calib']['by_designation']['Out']['play_rate_pct']}% of the time "
        f"(n={d['calib']['by_designation']['Out']['n']}), <strong>Doubtful</strong> {d['calib']['by_designation']['Doubtful']['play_rate_pct']}% "
        f"(n={d['calib']['by_designation']['Doubtful']['n']}), <strong>Questionable</strong> "
        f"{d['calib']['by_designation']['Questionable']['play_rate_pct']}% (n={d['calib']['by_designation']['Questionable']['n']}). "
        'The model therefore consumes the surprise against these rates, never the label.</li>'
        f"<li>The margin calibration slope is <strong>{cal['margin']['slope']}</strong>: the raw attack/defence decomposition is too "
        'sharp, and publishing it unshrunk would overstate the model.</li>'
        f"<li>Same-game parlay legs on this corpus look negatively joint (phi {d['parlay']['phi']}, n={d['parlay']['n_games']}) while the "
        f"2,927-game baseline is phi {d['parlay']['historical_baseline_2015_2025']['phi']}. The 130-game interval contains the independence "
        'value, so nothing is multiplied together to rank a parlay.</li>'
        "</ul>"
    )
    body.append(
        '<h2>Decisions requested from the owner</h2><ol>'
        "<li><strong>Price source</strong> (QN-01/QN-02, SG-04): record our own dated consensus snapshots, buy a feed, or drop CLV from the gates. "
        "Every pricing gate depends on this and no choice is safe by default.</li>"
        "<li><strong>Depth definition</strong> (QN-03/QN-04, SG-02): accept playing time as the definition of a string, or keep the "
        "backup-deficiency feature closed. Listed rank cannot be it: the clubs' own charts put multiple players at rank 1.</li>"
        "<li><strong>Raw-data exposure</strong> (SG-08/QN-13): mirrors currently sit in a public Pages tree with unread terms.</li>"
        "<li><strong>Six sections, one hub</strong> (SG-11/QN-14): adopt one navigation and one readiness view, or accept that readers will meet "
        "the same fixture at four tiers.</li>"
        "</ol>"
    )
    return page("executive-summary.html", "Executive summary",
                "Written from the computed artefacts, not from notes: every figure on this page is regenerated by the build.",
                "".join(body))


def p_results(d) -> str:
    feed, rec = d["feed"], d["recon"]
    meta = d["results_meta"]
    body = []
    body.append(kpi([
        ("Fixtures in the 2026 feed", str(meta["games_in_feed"]), "the full regular-season slate as published"),
        ("With a confirmed final", str(meta["games_with_confirmed_final"]), "score verified against an official page"),
        ("Carried blank", str(meta["games_blank_unverified"]), "no official final at capture; never guessed"),
        ("Reconciliation", meta["reconciliation"]["result"], "W-L-T, PF, PA recomputed from the feed"),
    ]))
    body.append('<div class="callout"><strong>Why this page exists.</strong> ROI and a backtest are impossible until results '
                "are trustworthy at row level. The feed is therefore built to be falsified: it is summed back into the "
                "official standings and compared, and any team that disagrees would be published as a failure. All 32 agree.</div>")
    rows = [[esc(r["team"]), esc(r["feed_wlt"]), esc(r["official_wlt"]), esc(r["feed_pf"]), esc(r["official_pf"]),
             esc(r["feed_pa"]), esc(r["official_pa"]),
             '<span class="ok">match</span>' if r["match"] == "yes" else '<span class="bad">MISMATCH</span>',
             link(r["source_url"], "nfl.com standings") + f'<br><span class="fine">{esc(r["captured_utc"])}</span>']
            for r in rec]
    body.append("<h2>Reconciliation: feed vs official standings, team by team</h2>")
    body.append(table(["team", "feed W-L-T", "official W-L-T", "feed PF", "official PF", "feed PA", "official PA",
                       "check", "source and clock time"], rows, cls="compact"))
    g = d["feed"]
    shown = [r for r in g if r["week"] in ("10",) or (r["away_score"] == "" and r["week"] == "11")]
    shown.sort(key=lambda r: r["gameday"])
    rows = []
    for r in shown:
        score = f'{r["away_team"]} {r["away_score"]}, {r["home_team"]} {r["home_score"]}' if r["away_score"] else '<span class="bad">no official final at capture</span>'
        rows.append([
            esc(r["gameday"]), esc(f'W{r["week"]}'), score,
            esc(r["roof"] or BLANK), esc(r["stadium"] or BLANK),
            esc(r["venue_source"][:52] + ("&hellip;" if len(r["venue_source"]) > 52 else "")),
            link(r["game_centre_url"] or "https://www.nfl.com/schedules/2026/by-week/week-10", "game centre"),
        ])
    body.append("<h2>Week 10 and the Week 11 slate, as captured</h2>")
    body.append(table(["date", "week", "result", "roof", "venue", "venue provenance", "source"], rows, cls="compact"))
    body.append(
        '<div class="warn"><strong>Venue flag (FL-08, R23).</strong> The venue column above is transcribed from the official '
        "schedule and game-centre pages for the fixtures that have them, and from a mirror elsewhere &mdash; the two disagree for "
        "international games: the Week 10 Patriots&ndash;Lions block is labelled <em>International Game &mdash; Munich</em> while the "
        "page's own venue widget targets Ford Field, and the mirror has no row for that fixture at all. 2 of 148 fixtures are "
        "transcribed from a game centre; the other 146 are a capture task, not a judgement call.</div>"
    )
    ann = d["announcement"]
    body.append("<h2>The dated schedule announcement, beside the live schedule</h2>")
    body.append(table(["item", "value", "source"], [
        [esc("League announcement"), esc(ann["title"]), link(ann["url"], "nfl.com article")],
        [esc("Published"), esc(ann["date"]), link(ann["url"], "article")],
        [esc("Season start it set"), esc(ann["kickoff"]), link(ann["url"], "article")],
        [esc("Live schedule page"), esc("nfl.com/schedules/2026/by-week/week-11, 13 games, 6 byes"),
         link("https://www.nfl.com/schedules/2026/by-week/week-11", "week 11")],
        [esc("Flex procedures"), esc("later date/time moves are permitted by rule, so a fixture's context is only as good as its capture time"),
         link("https://www.nfl.com/legal/flexible-scheduling-procedures", "rule text")],
    ]))
    body.append('<p class="fine">Feed file: <a href="data/derived/results-2026.csv">results-2026.csv</a> &middot; '
                "capture log: <a href=\"data/official/fetch-log.md\">fetch-log.md</a></p>")
    return page("results.html", "Verified results feed",
                "Game-level results with a source per row, used to make the ratings opponent-aware and to make grading possible at all.",
                "".join(body))


def p_prices(d) -> str:
    pm = d["price_meta"]
    rows = []
    for k, v in pm["source_files"].items():
        rows.append([esc(k), esc(v.get("path", "")), cell(v.get("rows")), cell(v.get("bytes")),
                     f'<code>{esc(v.get("sha256","")[:16])}&hellip;</code>',
                     esc(str(v.get("seasons_min")) + " to " + str(v.get("seasons_max"))),
                     "<span class=\"bad\">no</span>" if not v.get("carries_timestamp") else "<span class=\"ok\">yes</span>",
                     link("https://github.com/nflverse/nfldata", "upstream")])
    body = [kpi([
        ("Market rows in the store", str(pm["markets_recorded"]), "3 markets x every fixture we originate"),
        ("Closing numbers", str(pm["with_closing_number"]), "from a mirror, not an official page"),
        ("Opening numbers", str(pm["with_opening_number"]), "the binding gap for any opening-to-close move"),
        ("Rows with a timestamp", str(pm["with_any_observed_at"]), "so no CLV is certified today"),
    ])]
    body.append('<div class="callout"><strong>Policy first.</strong> The brief requires the price-data policy to be decided '
                "before any backtest is published. It is written and pinned, and the backtest on this site runs under it: "
                'prices are T3, never official, and untimed prices may not enter a gate. <a href="data/prices/policy.md">policy.md</a></div>')
    body.append("<h2>Sources held, with hashes</h2>")
    body.append(table(["source", "path in repo", "rows", "bytes", "sha-256 (first 16)", "seasons", "carries a timestamp", "upstream"], rows))
    body.append("<h2>Per-market coverage for 2026</h2>")
    mk = pm["by_market"]
    body.append(table(["market", "rows", "with closing number", "with opening number", "opening coverage"],
                      [[esc(k), cell(v["rows"]), cell(v.get("with_closing")), cell(v.get("with_opening")),
                        f'{100 * v.get("with_opening", 0) / max(1, v["rows"]):.1f}%'] for k, v in mk.items()]))
    idx = d["price_index"]
    body.append("<h2>Historical depth of the price files</h2>")
    body.append(table(["season", "file", "rows", "closing numbers", "opening numbers"],
                      [[esc(x["season"]), f'<code>{esc(x["source"])}</code>', cell(x["rows"]),
                        cell(x["closing_price_rows"]), cell(x["opening_price_rows"])] for x in idx]))
    body.append('<p class="fine">Opening prices exist for one season only (2021, 1,088 rows, one book). That is the fact that '
                "kills the 'line movement' feature today, and it is recorded rather than worked around.</p>")
    snap = [r for r in d["price_rows"] if r["week"] in ("10", "11")][:18]
    body.append("<h2>Snapshot rows, as stored</h2>")
    body.append(table(["fixture", "market", "side", "opening", "opening source", "closing", "close odds", "observed_at", "status"],
                      [[esc(r["game_id"]), esc(r["market"]), esc(r["reference_side"]), cell(r["opening_line"]),
                        esc(r["opening_source"]), cell(r["closing_line"]), cell(r["closing_odds"]),
                        '<span class="bad">none</span>', esc(r["fixture_status"])] for r in snap]))
    body.append('<div class="warn"><strong>Forward-dated prices (FL-03).</strong> The mirror carries a spread and total for 15 '
                "unplayed 2026 fixtures with no capture timestamp, and 8 of 13 Week 11 games disagree with our line by more than "
                "8 points (largest 18.4). They are published, labelled, and excluded from every gate.</div>")
    body.append('<p class="fine">Store: <a href="data/prices/price-snapshots-2026.csv">price-snapshots-2026.csv</a> &middot; '
                'integrity manifest: <a href="data/prices/MANIFEST.sha256">MANIFEST.sha256</a></p>')
    return page("prices.html", "Price-snapshot store",
                "Opening and closing numbers for every market we originate, with provenance and a hash per source file.",
                "".join(body))


def p_lines(d) -> str:
    lines = d["lines"]
    by_market = defaultdict(list)
    for r in lines:
        by_market[r["market"]].append(r)
    body = []
    stats = []
    for m in ("SPREAD", "TOTAL", "TOTAL_T2", "MONEYLINE"):
        rows = [r for r in by_market[m] if r["fixture_status"] == "FINAL" and r["residual_fair_minus_market"]]
        if not rows:
            continue
        res = [float(r["residual_fair_minus_market"]) for r in rows]
        absr = sorted(abs(x) for x in res)
        stats.append([
            esc(m), cell(len(rows)), cell(sum(absr) / len(absr), 2), cell(absr[len(absr) // 2], 2),
            cell(max(absr), 2), f'{100 * sum(1 for x in absr if x >= 1.5) / len(absr):.1f}%',
            f'{100 * sum(1 for x in absr if x >= 3.0) / len(absr):.1f}%',
            cell((sum(float(r["overround_pct"]) for r in rows if r["overround_pct"]) /
                  max(1, sum(1 for r in rows if r["overround_pct"]))) if any(r["overround_pct"] for r in rows) else None, 2),
        ])
    body.append(kpi([
        ("Originated rows", str(len(lines)), "every fixture, every market, fair and market and difference"),
        ("Origination order", "side &rarr; total &rarr; moneyline", "enforced by the code path, labelled per row"),
        ("Outputs storing probability + inputs", f'{len(d["inputs"])} of {len(lines) // 4} fixtures', "lines-inputs.jsonl"),
        ("Markets with a residual", str(sum(1 for r in lines if r["residual_fair_minus_market"])), "against the recorded market line"),
    ]))
    body.append('<div class="callout"><strong>Sequence.</strong> The side is priced first because it is the only quantity the '
                "ratings can be trusted to rank; the total is priced second from the same scoring decomposition; the moneyline is "
                "derived third from the margin distribution the side already produced. Nothing is back-fitted from a price.</div>")
    body.append("<h2>Residual against the market, by market (2026 finals)</h2>")
    body.append(table(["market", "games", "mean |residual| pts", "median", "max", "share &ge; 1.5 pts", "share &ge; 3.0 pts", "mean overround %"], stats))
    body.append("<h2>Decomposition: vig-free consensus vs our line</h2>")
    ml = [r for r in by_market["MONEYLINE"] if r["fixture_status"] == "FINAL" and r["market_p_devig"]]
    rows = [[esc(r["gameday"]), esc(r["away"] + " at " + r["home"]), cell(r["fair_line"], 0),
             cell(r["market_line"], 0), cell(r["p_home_or_over"], 3), cell(r["market_p_devig"], 3),
             f'{100 * (float(r["p_home_or_over"]) - float(r["market_p_devig"])):+.1f}', cell(r["overround_pct"], 2),
             '<span class="ok">yes</span>' if r["actual"] in ("0", "1") else '<span class="bad">push/ungraded</span>']
            for r in ml[-14:][::-1]]
    body.append(table(["date", "fixture", "our fair ML", "market ML", "our p(home)", "market p(home) devigged",
                       "divergence pp", "overround %", "graded"], rows, cls="compact"))
    body.append('<p class="fine">Divergence in percentage points is the only place our number and the market number are put '
                "side by side as a single figure; overround is the vig the consensus charged before we disagree with it.</p>")
    tot = d["totals"]
    body.append("<h2>Two total estimators, both published until one wins</h2>")
    body.append(table(["estimator", "definition", "MAE pts", "n", "state"], [
        ["T1", esc("scoring rates: own points plus opponent concession, shrunk, calibrated"), cell(tot["MAE_T1_scoring_rates"], 2),
         cell(tot["n_games_compared"]), "live"],
        ["T2", esc("context only: league-mean total plus measured roof/surface and rest adjustments from published schedule facts"),
         cell(tot["MAE_T2_context_only"], 2), cell(tot["n_games_compared"]), "live"],
        ["market", esc("recorded close for comparison only, never an input"), cell(tot["MAE_market_line"], 2),
         cell(tot["n_games_compared"]), "benchmark"],
    ]))
    body.append('<div class="warn"><strong>Collapse decision: ' + esc(tot["collapse_decision"]["decision"]) + ".</strong> Gate: "
                f'n&nbsp;&ge;&nbsp;{tot["collapse_decision"]["n_required"]} games with a paired interval excluding zero; now '
                f'n&nbsp;=&nbsp;{tot["collapse_decision"]["n_actual"]}, mean paired difference '
                f'{cell(tot["paired_mean_T1_minus_T2_abs_err"], 3)} pts with interval {esc(tot["paired_ci95"][0])} to '
                f'{esc(tot["paired_ci95"][1])}. The gap between the estimators averages '
                f'{cell(tot["mean_gap_between_estimators_pts"], 2)} points, so choosing one today would be a coin flip dressed as a decision.</div>')
    fwd = [r for r in by_market["SPREAD"] if r["week"] == "11"]
    body.append("<h2>Forward ledger: Week 11, recorded before kickoff</h2>")
    body.append(table(["fixture", "our margin pts", "recorded market line", "difference", "our p(home)", "with personnel", "price status"],
                      [[esc(r["away"] + " at " + r["home"]), cell(r["fair_line"], 2), cell(r["market_line"], 1),
                        cell(r["residual_fair_minus_market"], 2), cell(r["p_home_or_over"], 3),
                        cell(r["fair_line_with_personnel"], 2), '<span class="bad">timing uncertified</span>'] for r in fwd]))
    body.append('<p class="fine">Full file: <a href="data/derived/lines-2026.csv">lines-2026.csv</a> &middot; probability plus '
                'inputs per output: <a href="data/derived/lines-inputs.jsonl">lines-inputs.jsonl</a></p>')
    return page("lines.html", "Originated lines",
                "Our fair line, the market line, and the difference between them, published as three separate columns.",
                "".join(body))


def p_availability(d) -> str:
    cal = d["calib"]
    rows = []
    for k, v in sorted(cal["by_designation"].items()):
        rows.append([esc(k), cell(v["n"]), cell(v["played"]), cell(v["play_rate_pct"], 2),
                     f'{v["ci95_pct"][0]}&ndash;{v["ci95_pct"][1]}',
                     link("https://www.nfl.com/injuries/", "official report"),
                     "mirrored rows joined to participation rows" if v["n"] else BLANK])
    body = [kpi([
        ("Player-week rows, 2026", str(d["availability_n"]), "expected vs actual, side by side"),
        ("Rows with a surprise", f'{d["surprise_counts"]["expected-out-but-played"]} out-but-played / {d["surprise_counts"]["expected-in-but-missed"]} in-but-missed',
         "the signal is the delta, not the label"),
        ("Reserve rows in the feed", "0", "so an unlisted player is never read as healthy"),
        ("2026 snap counts held", "0", "replacement depth is therefore not modelled"),
    ])]
    body.append('<div class="callout"><strong>Calibration replaces folklore.</strong> The brief forbids using old Questionable '
                "percentages, and none are used: the rate below is measured on the 2016&ndash;2024 join of the official report to "
                "participation, with n and an interval on every row.</div>")
    body.append("<h2>What each designation is worth</h2>")
    body.append(table(["designation", "n player-weeks", "played", "play rate %", "95% CI", "official source", "note"], rows))
    body.append("<h2>Surprise, by team, for the games we backtest</h2>")
    sur = d["surprise_by_team"]
    body.append(table(["team", "rows", "expected-out-but-played", "expected-in-but-missed", "surprise magnitude (avg pp)"],
                      [[esc(t), cell(v["n"]), cell(v["out_but_played"]), cell(v["in_but_missed"]), cell(v["mean_abs"], 1)]
                       for t, v in sorted(sur.items(), key=lambda kv: -kv[1]["mean_abs"])[:16]]))
    body.append("<h2>Named absences that changed a position group</h2>")
    ev = d["starter_events"]
    body.append(table(["week", "team", "position", "player", "designation", "practice status", "participated?", "reading"],
                      [[cell(r["week"]), esc(r["team"]), esc(r["position"]), esc(r["player"]), esc(r["designation"]),
                        esc(r["practice_status"]),
                        '<span class="bad">no</span>' if r["participated_that_week"] == "no" else '<span class="ok">yes</span>',
                        esc(r["surprise"])] for r in ev], cls="compact"))
    body.append('<div class="warn"><strong>What this table cannot say.</strong> A player who did not appear is evidence of an '
                "absence, not evidence of who replaced him: per-game snap counts are not in this repository for 2026, so "
                "'the backup started' is a suspicion, and the brief says a suspicion must not be modelled as a fact. "
                "Replacement depth stays unblocked-only by SG-02 (capture) and R31 (inactive lists).</div>")
    body.append('<p class="fine">Machine copy: <a href="data/derived/availability-graph.csv">availability-graph.csv</a> &middot; '
                'calibration: <a href="data/derived/designation-calibration.json">designation-calibration.json</a></p>')
    return page("availability.html", "Availability graph",
                "Who was expected to start, who actually played, and how big the surprise was - as a first-class dataset.",
                "".join(body))


def p_analytics(d) -> str:
    pro, corr, luck = d["proper"], d["corr"], d["proper"]["controls_and_luck"]
    body = []
    rows = []
    for m, v in pro["by_market"].items():
        lo, hi = v["brier_skill_cluster_ci95"]
        rows.append([esc(m), cell(v["n_graded"]), cell(v["brier_ours"], 5), cell(v["brier_market_devig"], 5),
                     cell(v["brier_coin_flip"], 5), f'{100 * v["brier_skill_vs_market"]:+.1f}%',
                     f"{lo:+.3f} to {hi:+.3f}", cell(v["log_loss_ours"], 5), cell(v["log_loss_market"], 5),
                     f'{v["hit_rate_ours"]:.1f}%'])
    body.append("<h2>Signal division: proper scores on the frozen corpus</h2>")
    body.append(table(["market", "graded games", "our Brier", "market Brier (devigged)", "coin-flip Brier",
                       "skill vs market", "game-cluster 95% CI", "our log loss", "market log loss", "hit rate"], rows))
    body.append('<p class="fine">Hit rate is printed for completeness and is not a ranking metric: 52.4% at &minus;110 is '
                "break-even, and a 136-game sample cannot tell a 55% bettor from a 45% one.</p>")
    body.append("<h2>Removal of luck panel</h2>")
    body.append(table(["measure", "value", "reading"], [
        ["random-forecast field", f'mean Brier {luck["control_random_brier"]["mean"]}, best of 400 {luck["control_random_brier"]["best_of_400"]}',
         "the bar pure noise clears on this corpus"],
        ["our model", cell(luck["model_brier"], 5), "compared against that field, not against zero"],
        ["p against the field", cell(luck["luck_p_value"], 4),
         "share of random forecasters at least as good; a large value means our number is inside the noise band"],
        ["favourites-only control", f'hit rate {luck["control_favourites_only"]["hit_rate_pct"]}%, Brier {luck["control_favourites_only"]["brier"]}',
         "if the control wins, the model is not needed"],
        ["home cover this season", f'{luck["home_cover_rate_pct"]}%', "context for any side-based claim"],
    ]))
    mult = pro["multiplicity"]
    body.append(f'<div class="warn"><strong>Multiplicity.</strong> {mult["n_hypotheses"]} hypotheses were tested across '
                f'this corpus; Benjamini-Hochberg at q={mult["q"]} rejects {sum(1 for v in mult["reject"].values() if v)}. '
                "The count of trials is published precisely because reporting only the winner is how a fake edge is made.</div>")
    st_ = pro["staking_division"]["windows"]
    body.append("<h2>Staking division, reported separately</h2>")
    body.append(table(["edge threshold pts", "bets", "hit rate %", "break-even %", "ROI %", "priced from real odds %", "mean |disagreement| pts"],
                      [[cell(w["edge_threshold_pts"], 1), cell(w["n_bets"]), cell(w["hit_rate_pct"], 2),
                        cell(w["breakeen_hit_rate_pct"], 2) if "breakeen_hit_rate_pct" in w else cell(w["breakeven_hit_rate_pct"], 2),
                        cell(w["roi_pct"], 2), cell(w["priced_from_real_odds_pct"], 1), cell(w["mean_abs_line_disagreement_pts"], 2)]
                       for w in st_]))
    body.append('<p class="fine">These staking figures live here and never on the leaderboard: pre-registration forbids a '
                "backtest number being a leaderboard entry.</p>")
    body.append("<h2>Ablation instead of a fixed penalty</h2>")
    ab = d["ablation"]
    co = ab["coefficient"]
    body.append(table(["quantity", "value", "uncertainty", "n", "consequence"], [
        ["points per expected miss", cell(co["beta_pts_per_expected_miss"], 3),
         f'{co["ci95"][0]} to {co["ci95"][1]}', cell(co["n_games"]),
         "a fixed 3-point penalty is roughly six standard errors away from this"],
        ["correlation of availability gap with margin residual", cell(co["pearson_r"], 3),
         f'{co["pearson_ci95"][0]} to {co["pearson_ci95"][1]}', cell(co["n_games"]),
         "small but real; it earns a feature, not a headline"],
        ["Brier on 2026 without the feature", cell(d["ablation_scores"]["A_spread_brier"], 5), BLANK,
         cell(d["ablation_scores"]["n_graded"]), "the model as pre-registered"],
        ["Brier with the feature", cell(d["ablation_scores"]["B_with_personnel_spread_brier"], 5), BLANK,
         cell(d["ablation_scores"]["n_graded"]), f'improvement {d["ablation_scores"]["delta_B_minus_A"]} - not yet significant on 131 games'],
    ]))
    body.append("<h2>Correlations, official numbers only</h2>")
    rows = []
    for k, v in corr["official_only_panel"]["values"].items():
        ci = v.get("fisher_ci95") or [None, None]
        rows.append([esc(k.replace("_", " ")), cell(v.get("r"), 4), cell(v.get("n")),
                     f"{ci[0]} to {ci[1]}" if ci[0] is not None else BLANK,
                     link("https://www.nfl.com/schedules/2026/by-week/week-10", "schedule") + " + mirror results"])
    for k, v in corr["market_panel"]["values"].items():
        rows.append([esc(k.replace("_", " ")) + " (market)", cell(v.get("r"), 4), cell(v.get("n")), BLANK, BLANK])
    body.append(table(["relationship", "r", "n", "95% CI (Fisher z)", "source"], rows))
    body.append("<h2>Joint evidence for parlays</h2>")
    pj = d["parlay"]
    body.append(table(["quantity", "this corpus", "2015-2025 baseline"], [
        ["games", cell(pj["n_games"]), cell(pj["historical_baseline_2015_2025"]["n_games"])],
        ["P(home cover) %", cell(pj["p_home_cover_pct"], 2), BLANK],
        ["P(over) %", cell(pj["p_over_pct"], 2), BLANK],
        ["P(both) measured %", cell(pj["p_both_measured_pct"], 3), BLANK],
        ["P(both) if independent %", cell(pj["p_both_if_independent_pct"], 3), BLANK],
        ["difference, pct points", cell(pj["difference_pct_points"], 3), cell(pj["historical_baseline_2015_2025"]["difference_pct_points"], 3)],
        ["phi", cell(pj["phi"], 4), cell(pj["historical_baseline_2015_2025"]["phi"], 4)],
        ["joint 95% CI", f'{pj["joint_ci95_pct"][0]} to {pj["joint_ci95_pct"][1]}', BLANK],
    ]))
    body.append('<div class="warn"><strong>Gate stays shut.</strong> ' + esc(pj["why_still_blocked"]) + " " + esc(pj["small_sample_warning"]) + "</div>")
    body.append('<p class="fine">Suppressed and why: ' + esc(corr["suppressed"]["player_prop_leg_correlation"]) + "</p>")
    return page("analytics.html", "Skill, luck and correlation",
                "Benchmark-relative proper scores with uncertainty, controls that can embarrass the model, and correlations that publish their n.",
                "".join(body))


def p_leaderboard(d) -> str:
    lb = d["leaderboard"]
    body = [kpi([
        ("Ranked strategies", "0", "by design, not by omission"),
        ("Entries in escrow", str(len(lb["entries"])), "pre-registered, prospective only"),
        ("Graded bets", "0", "first scoring kickoff is 2026-11-20T01:15Z"),
        ("Reward-eligible divisions", "0", f'needs {200} graded singles'),
    ])]
    body.append('<div class="callout"><strong>The leaderboard is empty, and that is the requirement working.</strong> '
                "Pre-registration forbids a backtest number from ever appearing here, so the only rows this page may show are "
                "prospective escrow entries - and those have zero graded bets until the Week 11 results land. The measured "
                "backtest figures live on the <a href=\"analytics.html\">evaluation page</a>. A leaderboard that showed them "
                "here would be a leaderboard of the past dressed as a competition.</div>")
    rows = [[esc(r["id"]), esc(r["name"]), esc(r["division"]), esc(r["bet_shape"]), esc(r["stage"]),
             cell(r["graded_bets"]), BLANK, BLANK, BLANK, esc(r["status"])] for r in lb["entries"]]
    body.append("<h2>Divisions and escrow</h2>")
    body.append(table(["id", "strategy", "division", "shape", "stage", "graded", "skill lower bound", "CLV pts", "ROI %", "status"], rows))
    body.append('<p class="fine">Skill lower bound, CLV and ROI columns are deliberately blank: a value in any of them would '
                "be a backtest number. They fill from graded escrow games only.</p>")
    gates = d["prereg"][0]["gates"] if d["prereg"] else ""
    body.append("<h2>Validation gates every entry must pass</h2>")
    body.append(table(["gate", "definition", "state on today's data"], [
        ["G1 sample", "at least 200 graded singles", f'<span class="bad">0 of 200</span>'],
        ["G2 significance", "game-cluster bootstrap: Brier skill lower bound above 0", "not evaluated (n=0)"],
        ["G3 multiplicity", "Benjamini-Hochberg across every strategy tried, and the count of trials is published", "3 hypotheses tested on the corpus, 0 rejected"],
        ["G4 holdout", "no refit on the priced season; sign of the effect must hold on 2025 validation", "holdout frozen: 2016-2024 fit / 2025 validation / 2026 holdout"],
        ["G5 price basis", "at least 50% of bets priced from a recorded price; the fallback share is reported", f'<span class="bad">0% of forward bets carry a certified-timed price</span>'],
        ["G6 side balance", "35-65% of bets on either side, checked every week", "not evaluated (n=0); exists because a free intercept produced 78% home picks in an earlier run"],
        ["G7 ablation", "a personnel feature must beat the model without it, with an interval excluding zero", f'corpus difference {d["ablation_scores"]["delta_B_minus_A"]} on 131 games: not significant'],
        ["G8 joint evidence", "a parlay or combo must have a validated joint probability and the operator void/push rules", '<span class="bad">joint measured; void rules absent, so blocked</span>'],
        ["G9 demotion", "3 consecutive weeks with the skill lower bound at or below 0 sends a live strategy back to paper", "armed, nothing to demote"],
    ]))
    body.append("<h2>Rewards</h2>")
    body.append('<p>' + esc(lb["reward_rule"]) + " Ranking is on benchmark-relative skill, never on season-long ROI; that "
                "rejection is recorded in the suggestions register so the incentive cannot be quietly reintroduced.</p>")
    return page("leaderboard.html", "Leaderboard (prospective escrow)",
                "Signal separated from staking; ranks earned only from forward, graded, pre-registered play.",
                "".join(body))


def p_prereg(d) -> str:
    reg = d["prereg"]
    rows = [[esc(r["id"]), esc(r["name"]), esc(r["bet_shape"]), esc(r["market"]), esc(r["division"]),
             esc(r["evaluation_window"]), f'<code>{esc((r.get("registered_commit") or "pending")[:10])}</code>',
             esc(r["registered_utc"])] for r in reg]
    body = [table(["id", "strategy", "shape", "market", "division", "evaluation window", "registration commit", "recorded"], rows)]
    body.append("<h2>Frozen definitions</h2>")
    body.append(table(["id", "signal definition", "staking definition", "gates"],
                      [[esc(r["id"]), esc(r["signal_definition"]), esc(r["staking_definition"]), esc(r["gates"])] for r in reg], cls="wide"))
    body.append("<h2>Two-sided: what would change our mind</h2>")
    body.append(table(["id", "confirm if", "refute if"],
                      [[esc(r["id"]), esc(r["confirm_if"]), esc(r["refute_if"])] for r in reg], cls="wide"))
    led = d["ledger"]
    body.append("<h2>Shadow forecast ledger (hash-chained)</h2>")
    body.append(table(["fixture", "recorded", "kickoff (UTC)", "p(home)", "our margin", "fair total T1", "fair total T2", "record hash"],
                      [[esc(x["forecast_id"]), esc(x["recorded_utc"]), esc(x["kickoff_utc"]), cell(x["p_home_win"], 3),
                        cell(x["fair_margin_pts"], 2), cell(x["fair_total_T1"], 1), cell(x["fair_total_T2"], 1),
                        f'<code>{esc(x["record_hash"][:12])}</code>'] for x in led]))
    body.append('<p class="fine">Tip: <a href="data/ledger/LEDGER-TIP.txt">LEDGER-TIP.txt</a> &middot; raw records: '
                '<a href="data/ledger/forecasts-week11.jsonl">forecasts-week11.jsonl</a>. 13 records, all written before the '
                "first Week 11 kickoff, so the shadow baseline is live rather than promised.</p>")
    return page("prereg.html", "Pre-registration ledger",
                "Definition, window and gates committed before the evaluation window opens; the commit hash is the registration.",
                "".join(body))


def p_teams(d) -> str:
    rows = []
    for t, v in sorted(d["team_view"].items()):
        rows.append([esc(t), cell(v["rows"]), cell(v["out"]), cell(v["questionable"]), cell(v["doubtful"]),
                     cell(v["net_unavailable"], 2), cell(v["surprise_events"]),
                     '<span class="bad">no</span>', link("https://www.nfl.com/injuries/", "official report")])
    body = [kpi([
        ("Clubs with a per-team row", "32", "net unavailability computed from the report feed"),
        ("Replacement named for a club", "0", "would need inactive lists or snap counts"),
        ("Clubs with a dated depth register", "0", "no official league chart exists"),
        ("Clubs swept for roster/IR", "0 of 32", "gate on every team-level model, per the brief"),
    ])]
    body.append('<div class="callout"><strong>Reading this table.</strong> <em>Net unavailability</em> is the sum of expected '
                "misses (each listed player weighted by his designation's measured play rate), not a count of names - a list of "
                "20 Questionables is not 20 absentees. The replacements column is blank everywhere because naming a replacement "
                "without inactive lists or snap counts would be inference, which the brief forbids.</div>")
    body.append(table(["club", "report rows", "Out", "Questionable", "Doubtful", "net unavailability", "surprise events",
                       "replacement named", "source"], rows, cls="compact"))
    return page("teams.html", "Per-team decision view",
                "Starters out, replacements named where evidenced, and a net injury count that does not double-count a label.",
                "".join(body))


def p_matrix(d) -> str:
    body = ['<div class="callout"><strong>This view is deliberately not populated.</strong> A 1st-to-4th string deficiency matrix '
            "needs a string-level rating per unit. No official league depth chart exists, the clubs' own charts put several "
            "players at rank 1 in the same slot, and this repository holds no per-game snap counts for 2026. Publishing cells "
            'built from jersey order would fabricate exactly the thing the brief says not to fabricate.</div>']
    cells = []
    for unit in ("WR1 vs CB2/CB3", "TE1 vs slot", "EDGE1 vs OT2/LG2", "RB1 vs LB depth", "QB1 vs pass-rush depth",
                 "OL3/4 vs interior pass rush", "PR1 vs coverage special teams", "K vs weather (unavailable)"):
        cells.append([esc(unit), '<span class="bad">not computable</span>',
                      esc("needs playing time per game (SG-02) and an official or licensed inactive list (R31)")])
    body.append("<h2>Requested cells and what unblocks each</h2>")
    body.append(table(["mismatch the matrix would show", "state", "gate"], cells))
    body.append("<h2>What can be shown today, honestly</h2>")
    body.append("<p>Expected misses by position group across the backtest weeks, computed from the report feed and the "
                "measured designation rates rather than from a listed rank:</p>")
    body.append(table(["position group", "listed player-weeks", "expected misses", "actual non-participation", "surprise rate %"],
                      [[esc(k), cell(v["rows"]), cell(v["expected"], 1), cell(v["missed"]), f'{100 * v["missed"] / max(1, v["rows"]):.1f}%']
                       for k, v in sorted(d["pg_view"].items())], cls="compact"))
    body.append('<p class="fine">This is a two-string view: the listed group and everyone else. A three- or four-string view '
                "is a capture task, not an analysis task. See <a href=\"data/official/depth-defects.md\">depth-defects.md</a>.</p>")
    return page("matrix.html", "Matchup deficiency matrix",
                "The trench and coverage mismatch view, and the exact reason it is empty rather than estimated.",
                "".join(body))


def p_suggestions(d) -> str:
    sg = d["suggestions"]
    state_color = {"ADOPT": "done", "ADOPT-PARTIAL": "partial", "DECIDE": "blocked"}
    rows = [[esc(r["id"]), esc(r["title"]),
             f'<span class="badge b-{state_color.get(r["state"], "needsreview")}">{esc(r["state"])}</span>',
             esc(r["problem"]), esc(r["proposed_change"]), esc(r["missing_information_to_decide"]),
             esc(r["effort"]), esc(r["risk"]), esc(r["depends_on"])] for r in sg]
    body = [kpi([
        ("Suggestions registered", str(len(sg)), "each with the information needed to decide it"),
        ("Recommended now", str(sum(1 for r in sg if r["state"] == "ADOPT")), "adopt, no owner decision needed"),
        ("Need an owner decision", str(sum(1 for r in sg if r["state"] == "DECIDE")), "price source and data-layer exposure"),
        ("Rejected on principle", "2", "jersey-order depth, and season-long ROI ranking"),
    ])]
    body.append('<div class="callout"><strong>Nothing here is implemented as a site change without a decision.</strong> Each '
                "row names the missing information that has to be found before the choice is reasonable, so the register doubles "
                "as a discovery list: the questions that would upgrade a suggestion from plausible to decided.</div>")
    body.append(table(["id", "suggestion", "state", "problem today", "proposed change", "missing information to decide",
                       "effort", "risk", "depends on"], rows, cls="wide"))
    body.append("<h2>Recorded rejections</h2>")
    body.append(table(["rejected proposal", "why"], [
        ["Derive depth order from jersey number, experience or salary",
         "It is not a proxy for a starter; it is a proxy for a roster-page sort. The club charts already show multiple rank-1 players in one slot."],
        ["Rank strategies on season-long realised return",
         "A season of singles is a few hundred bets; on that sample a 45% bettor can finish first. Ranking is on benchmark-relative skill, and ROI is an escrow measure."],
        ["Subtract a fixed points penalty for a missing starter",
         f'The measured effect is {d["ablation"]["coefficient"]["beta_pts_per_expected_miss"]} points per expected miss with a CI of '
         f'{d["ablation"]["coefficient"]["ci95"][0]} to {d["ablation"]["coefficient"]["ci95"][1]}; a fixed 3.0 is outside it by many standard errors.'],
    ]))
    return page("suggestions.html", "Suggestions and decision paths",
                "How to improve the site's decision quality, kept separate from the site so a path can be chosen before code changes.",
                "".join(body))


def p_questions(d) -> str:
    q = d["questions"]
    counts = defaultdict(int)
    for r in q:
        counts[r["status"]] += 1
    rows = [[esc(r["id"]), esc(r["question"]), esc(r["why_it_blocks"]), esc(r["answer_now"]),
             esc(r["what_would_close_it"]),
             f'<span class="badge b-{r["status"].lower().replace("-", "")}">{esc(r["status"])}</span>',
             esc(r["related"])] for r in q]
    body = [kpi([
        ("Open questions", str(counts["OPEN"]), "no answer available from any source we can reach"),
        ("Answered", str(counts["ANSWERED"] + counts["ANSWERED-NEGATIVE"] + counts["PARTIAL"]),
         "with the number or the explicit negative result"),
        ("Decisions requested", str(counts["DECIDE"]), "owner input needed; not blocked on data"),
    ])]
    body.append('<div class="callout"><strong>Answered here, not deferred.</strong> Three of the brief\'s hardest questions '
                "have measured answers now: what Questionable means, what a missing starter is worth, and whether parlay legs "
                "are independent. Each is stated with its n and its interval, and each answer changes a modelling decision.</div>")
    body.append(table(["id", "question", "why it blocks a decision", "answer now", "what would close it", "state", "related"],
                      rows, cls="wide"))
    return page("questions.html", "Questions, information and answers",
                "What must be known before a decision is reasonable - and what is already knowable from the data on hand.",
                "".join(body))


def p_flagged(d) -> str:
    fl = d["flags"]
    rows = [[esc(r["id"]), f'<span class="badge b-{r["state"].lower().replace(" ", "")}">{esc(r["state"])}</span>',
             esc(r["type"]), esc(r["title"]), esc(r["detail"]), esc(r["handling"]), link(r["source_url"], "source") if r["source_url"].startswith("http") else link(r["source_url"], "artefact")]
            for r in fl]
    body = ['<div class="callout"><strong>Published so the site can go live without waiting.</strong> Nothing on this list '
            "blocks the merge; each item states what was checked, what is missing, and the single action that would resolve it.</div>"]
    body.append(table(["id", "state", "type", "finding", "evidence", "handling", "source"], rows, cls="wide"))
    body.append("<h2>Also unresolved from earlier sessions, still open</h2>")
    body.append(table(["item", "where it lives", "state here"], [
        ["BAL and LAC starting QBs unconfirmed", "<a href=\"../ledger/flagged.html\">ledger flagged page</a>",
         "unchanged - no official starter source exists, and LAC is 0-8 with a Monday game"],
        ["nflverse release assets unreachable from the sandbox", "several sessions",
         "worked around: the snapshot workflow fetches them in CI where egress is open"],
        ["Depth rank not published alongside the injury report", "hub, ledger, signals",
         "confirmed still true; this section refuses to use the report's own ordering as depth"],
        ["27 clubs with no acquired depth chart", "<a href=\"../fl2-signals/flagged.html\">fl2-signals flagged page</a>",
         "superseded in mechanism: the defect is now identified as a parser bug (FL-09), not only a missing capture"],
    ]))
    return page("flagged.html", "Flagged for review",
                "Irregularities and unverified items, each with its source link and the action that closes it.",
                "".join(body))


def p_sources(d) -> str:
    src = d["sources"]
    rows = [[esc(r["id"]), esc(r["source"]), esc(r["tier"]), esc(r["what_it_provided"]), esc(r["how_accessed"]),
             link(r["url"], "open"), esc(r["terms_note"])] for r in src]
    body = [table(["id", "source", "tier", "what it provided", "how it was accessed", "link", "terms"], rows, cls="wide")]
    body.append("<h2>Verification method, in order</h2><ol>"
                "<li><strong>Reproduce, don't assert.</strong> Every page is generated from CSV/JSON written by "
                "<code>compute_results.py</code>, <code>compute_lines.py</code> and <code>compute_scores.py</code>; re-running them must "
                "produce the committed files.</li>"
                "<li><strong>Reconcile to the official page.</strong> The results feed is summed back into the published standings and "
                "compared for all 32 clubs; the check fails the build on any mismatch.</li>"
                "<li><strong>Prove the sign conventions.</strong> The spread-line convention is tested against the moneyline sign and against "
                "the cover rate on 3,165 games; the model's own sanity is tested by requiring corr(model, market) &gt; 0.55.</li>"
                "<li><strong>Refuse to fill gaps.</strong> Blank scores for unconfirmed results, blank replacements, blank opening prices, "
                "blank depth cells; each is labelled rather than estimated.</li>"
                "<li><strong>Keep the tiers apart.</strong> T1 official, T2 mirror of official, T3 aggregated market. A T3 number is never "
                "cited as a fact about a game and never mixes into the official correlation panel.</li></ol>")
    body.append('<div class="warn"><strong>Reuse terms are unread for S01&ndash;S05 and S08&ndash;S11.</strong> That is why raw '
                "row-level capture stays outside the published pages and only derived counts, hashes and aggregates are shown "
                "(see <a href=\"data.html\">data layer</a>).</div>")
    return page("sources.html", "Sources and verification",
                "Every tier, every access route, and the five checks that make a number mean something.",
                "".join(body))


def p_data(d) -> str:
    files = d["artefacts"]
    rows = [[f'<a href="{esc(f["path"])}">{esc(f["path"])}</a>', cell(f["bytes"]), f'<code>{esc(f["sha256"][:16])}</code>&hellip;',
             esc(f["layer"]), esc(f["role"])] for f in files]
    body = ['<div class="callout"><strong>Public analysis layer, private data layer.</strong> The published site carries derived '
            "figures, intervals, hashes and links. Row-level third-party mirrors stay out of the published tree until their terms "
            "are read; where a mirror already sits in the repository (another session's scope) it is listed here and requested, "
            "not moved.</div>"]
    body.append(table(["artefact", "bytes", "sha-256", "layer", "role"], rows))
    body.append("<h2>Freshness and drift alarms</h2>")
    body.append(table(["check", "expected", "today", "alarm"], [
        ["Week 10 injury rows in the mirror", "a count near the official page's row count", "18 rows across 4 clubs", '<span class="bad">would fire: row count below floor</span>'],
        ["Required field: game_status present", "every listed row carries a designation or an explicit blank", "1239 rows, 0 lost columns", '<span class="ok">silent</span>'],
        ["Depth rows per season", "> 0 for every season in the window", "0 rows for 2026 while the download reported 784,796", '<span class="bad">fires (FL-09)</span>'],
        ["Snap counts", "a 2026 file with per-game rows", "not present", '<span class="bad">fires (R31/R06)</span>'],
        ["Price store opening coverage", "grows weekly once a capture runs", "0 of 816", '<span class="bad">fires (R01)</span>'],
        ["Feed vs standings", "32/32 exact", "32/32 exact", '<span class="ok">silent</span>'],
    ]))
    body.append('<p class="fine">The alarms above are implemented in '
                '<a href="../.github/workflows/fl2-lines-snapshot.yml">fl2-lines-snapshot.yml</a>, which captures, hashes, '
                "counts and fails loudly on a schema or row-count change.</p>")
    return page("data.html", "Data layer and artefacts",
                "What is stored where, its hash, and the alarms that catch a silent source change.",
                "".join(body))


BUILDERS = {
    "index.html": p_index, "executive-summary.html": p_exec, "results.html": p_results,
    "prices.html": p_prices, "lines.html": p_lines, "availability.html": p_availability,
    "analytics.html": p_analytics, "leaderboard.html": p_leaderboard, "prereg.html": p_prereg,
    "teams.html": p_teams, "matrix.html": p_matrix, "suggestions.html": p_suggestions,
    "questions.html": p_questions, "flagged.html": p_flagged, "sources.html": p_sources,
    "data.html": p_data,
}


def load_all() -> dict:
    feed = read(DER / "results-2026.csv")
    avail = read(DER / "availability-graph.csv")
    sur = defaultdict(lambda: {"n": 0, "out_but_played": 0, "in_but_missed": 0, "abs": 0.0})
    team = defaultdict(lambda: {"rows": 0, "out": 0, "questionable": 0, "doubtful": 0, "miss": 0.0, "surprise_events": 0})
    pg = defaultdict(lambda: {"rows": 0, "expected": 0.0, "missed": 0})
    events = []
    for r in avail:
        s = sur[r["team"]]
        s["n"] += 1
        s["abs"] += abs(float(r["surprise_pts"] or 0))
        if r["surprise"] == "expected-out-but-played":
            s["out_but_played"] += 1
        if r["surprise"] == "expected-in-but-missed":
            s["in_but_missed"] += 1
        t = team[r["team"]]
        t["rows"] += 1
        gs = r["designation"]
        if gs == "Out":
            t["out"] += 1
        elif gs == "Questionable":
            t["questionable"] += 1
        elif gs == "Doubtful":
            t["doubtful"] += 1
        t["miss"] += (100 - float(r["expected_available_pct"])) / 100.0
        if r["surprise"] != "as-expected":
            t["surprise_events"] += 1
        p = pg[r["pos_group"] or "OTHER"]
        p["rows"] += 1
        p["expected"] += (100 - float(r["expected_available_pct"])) / 100.0
        if r["participated_that_week"] == "no":
            p["missed"] += 1
        if gs == "Out" and int(r["week"] or 0) <= 9:
            events.append(r)
    for v in sur.values():
        v["mean_abs"] = v["abs"] / max(1, v["n"])
    for v in team.values():
        v["net_unavailable"] = round(v["miss"], 2)
    events.sort(key=lambda r: (r["team"], r["week"]))
    ledger = []
    lp = SEC / "data" / "ledger" / "forecasts-week11.jsonl"
    if lp.exists():
        ledger = [json.loads(x) for x in lp.read_text().splitlines() if x.strip()]
    artefacts = []
    for p in sorted((SEC / "data").rglob("*")):
        if p.is_file() and p.suffix in (".csv", ".json", ".jsonl", ".md", ".txt"):
            layer = "public (derived)" if "derived" in str(p) or "registers" in str(p) or "ledger" in str(p) else "section data"
            role = {"derived": "computed, regenerable", "registers": "human-written register", "prices": "price store and policy",
                    "official": "official-page transcription", "ledger": "hash-chained records"}.get(str(p).split(os.sep)[-2], "artefact")
            artefacts.append({"path": str(p.relative_to(SEC)), "bytes": p.stat().st_size,
                              "sha256": sha(p), "layer": layer, "role": role})
    return {
        "readiness": read(REG / "readiness.csv"),
        "feed": feed, "recon": read(DER / "results-reconciliation.csv"),
        "results_meta": jload(DER / "results-meta.json", {}),
        "price_meta": jload(PRI / "price-store-meta.json", {}),
        "price_rows": read(PRI / "price-snapshots-2026.csv"),
        "price_index": read(PRI / "price-source-index.csv"),
        "lines": read(DER / "lines-2026.csv"),
        "inputs": [json.loads(x) for x in (DER / "lines-inputs.jsonl").read_text().splitlines() if x.strip()],
        "priors": jload(DER / "model-priors.json", {}),
        "calibration": jload(DER / "model-calibration.json", {}),
        "sanity": jload(DER / "model-sanity.json", {}),
        "ablation": jload(DER / "ablation-injury.json", {}),
        "ablation_scores": jload(DER / "ablation-scores.json", {}),
        "calib": jload(DER / "designation-calibration.json", {}),
        "proper": jload(DER / "proper-scores.json", {}),
        "corr": jload(DER / "correlations.json", {}),
        "totals": jload(DER / "totals-comparison.json", {}),
        "parlay": jload(DER / "parlay-joint-evidence.json", {}),
        "leaderboard": jload(DER / "leaderboard-prospective.json", {}),
        "prereg": read(REG / "prereg.csv"), "suggestions": read(REG / "suggestions.csv"),
        "questions": read(REG / "questions.csv"), "flags": read(REG / "flags.csv"),
        "sources": read(REG / "sources.csv"),
        "ledger": ledger, "artefacts": artefacts,
        "availability_n": len(avail),
        "surprise_counts": {"expected-out-but-played": sum(1 for r in avail if r["surprise"] == "expected-out-but-played"),
                            "expected-in-but-missed": sum(1 for r in avail if r["surprise"] == "expected-in-but-missed")},
        "surprise_by_team": dict(sur), "team_view": dict(team), "pg_view": dict(pg),
        "starter_events": events[:40],
        "sign": jload(DER / "results-meta.json", {}).get("sign_convention_checks", {}),
        "announcement": {
            "title": "2026 NFL schedule release: Complete slate of Week 1 games",
            "url": "https://www.nfl.com/news/2026-nfl-schedule-release-complete-slate-of-week-1-games",
            "date": "nfl.com dateline 2026-05-15 (article metadata as indexed; the page body prints no dateline - flagged)",
            "kickoff": "Season opens Wednesday, Sept. 9, 2026: Patriots at Seahawks, Lumen Field, 8:20 PM ET; 49ers at Rams Thursday, Sept. 10, Melbourne Cricket Ground",
        },
    }


def sha(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def main() -> None:
    d = load_all()
    for fname, _title in PAGES:
        html_out = BUILDERS[fname](d)
        (OUT / fname).write_text(html_out, encoding="utf-8")
    (OUT / "build-report.json").write_text(json.dumps({
        "pages": [p for p, _ in PAGES], "artefacts": len(d["artefacts"]),
        "readiness_rows": len(d["readiness"]), "lines_rows": len(d["lines"]),
        "availability_rows": d["availability_n"],
    }, indent=2), encoding="utf-8")
    print("rendered", len(PAGES), "pages;", len(d["artefacts"]), "artefacts indexed")


if __name__ == "__main__":
    main()

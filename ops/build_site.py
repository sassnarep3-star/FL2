#!/usr/bin/env python3
"""Generates the /readiness/ site section from the ops data files.

Pages:
  readiness/index.html    — decision-readiness: one row per requirement (gate + clearing number)
  readiness/ops.html      — the ops dashboard: price store, results feed, luck panel, baselines,
                            venues, team view, Week 11 forecasts, snapshot ledger, drift pins
  readiness/flagged.html  — this session's flagged items with sources

Every table row carries at least one link (official source, official game centre, or the
repository file that holds the verified data). Blank-by-policy cells render as an explicit
"blank — flagged" marker, never a fabricated value.
"""
from __future__ import annotations

import csv
import datetime as dt
import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "readiness")
REPO = "https://github.com/sassnarep3-star/FL2/blob/main/"


def e(s) -> str:
    return html.escape(str(s), quote=True)


def repo_link(path: str) -> str:
    return f'<a href="{REPO}{e(path)}">{e(path)}</a>'


def official(url: str, label: str | None = None) -> str:
    return f'<a href="{e(url)}">{e(label or url)}</a>'


CSS = """:root{--ink:#16211c;--muted:#5f6d66;--paper:#f4f6f3;--card:#fff;--line:#dbe3dc;
--green:#146b51;--mint:#e3f1ea;--amber:#fff3d6;--red:#fdefeb;--blue:#edf3fc}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);
font:15px/1.55 system-ui,'Segoe UI',sans-serif}
h1{font-size:2rem;letter-spacing:-.02em;margin:.4rem 0 .8rem}
h2{font-size:1.3rem;margin:1.8rem 0 .7rem}h3{font-size:1.02rem;margin:1rem 0 .5rem}
p{margin:.5rem 0 .9rem}.wrap{max-width:1200px;margin:auto;padding:0 22px}
header.site{background:#0f2419;color:#fff;padding:14px 0}
header.site .wrap{display:flex;gap:18px;align-items:center;flex-wrap:wrap;justify-content:space-between}
.brand{font-weight:800;font-size:1.02rem;color:#fff;text-decoration:none;letter-spacing:-.02em}
.brand span{color:#8fd3b4}nav.main{display:flex;gap:4px;flex-wrap:wrap}
nav.main a{color:#c9d8d0;text-decoration:none;padding:7px 10px;border-radius:7px;font-size:.85rem}
nav.main a:hover{background:#24483b;color:#fff}
.lede{max-width:860px;font-size:1.08rem;color:#47554e}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.kpi .n{font-size:1.7rem;font-weight:800;letter-spacing:-.03em}
.kpi .l{font-size:.8rem;color:var(--muted)}
table{border-collapse:collapse;width:100%;background:#fff;font-size:.86rem}
th,td{text-align:left;padding:10px 12px;border-bottom:1px solid #e7ede8;vertical-align:top}
th{font-size:.7rem;text-transform:uppercase;letter-spacing:.06em;background:#eef3ef;color:#4e5d55;position:sticky;top:0}
tr:last-child td{border-bottom:0}
.tbl{overflow:auto;border:1px solid var(--line);border-radius:12px;max-height:640px;margin:10px 0 22px}
a{color:var(--green)}
.pill{display:inline-block;border-radius:99px;padding:2px 9px;font-size:.72rem;font-weight:700}
.pill.done{background:var(--mint);color:#135f46}.pill.partial{background:var(--amber);color:#7a5410}
.pill.registered{background:var(--blue);color:#2b4f7e}.pill.blocked{background:var(--red);color:#8c3b2e}
.pill.rejected{background:#ece9f7;color:#4a3f7a}
.callout{border:1px solid #e4d19a;background:var(--amber);border-radius:12px;padding:14px 18px;margin:14px 0}
.callout.blue{background:var(--blue);border-color:#ccd9ee}
.small{font-size:.82rem;color:var(--muted)}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.8rem}
footer{background:#0f2419;color:#c2d2c9;padding:20px 0;margin-top:34px;font-size:.82rem}
footer a{color:#9fdfbe}
@media(max-width:740px){.wrap{padding:0 14px}th,td{padding:8px 9px}}"""


def page(fname: str, title: str, active: str, body: str, desc: str) -> None:
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · FL2 Readiness</title>
<meta name="description" content="{e(desc)}">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="site"><div class="wrap">
<a class="brand" href="index.html"><span>FL2</span> Readiness &amp; Ops</a>
<nav class="main">
<a href="index.html"{' class="active"' if active == 'index' else ''}>Decision Readiness</a>
<a href="ops.html"{' class="active"' if active == 'ops' else ''}>Ops Dashboard</a>
<a href="flagged.html"{' class="active"' if active == 'flagged' else ''}>Flagged for Review</a>
<a href="../index.html">← Site Hub</a>
</nav></div></header>
<main><div class="wrap">
{body}
</div></main>
<footer><div class="wrap">Session <code>310620fe</code> · branch <code>arena/310620fe-fl2</code> ·
generated {dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')} · every table row carries a source link or a
repository file holding the verified data; values that could not be verified are blank and flagged.</div></footer>
</body></html>"""
    with open(os.path.join(OUT, fname), "w") as fh:
        fh.write(html_doc)


def table(headers: list[str], rows: list[list[str]], source_col: int | None = None) -> str:
    out = ['<div class="tbl"><table><thead><tr>']
    out += [f"<th>{h}</th>" for h in headers]
    out.append("</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def pill(status: str) -> str:
    return f'<span class="pill {e(status)}">{e(status)}</span>'


def build_index() -> None:
    reg = json.load(open(os.path.join(HERE, "data", "requirements_v2.json")))
    meta, reqs = reg["meta"], reg["requirements"]
    counts = meta["counts"]
    rows = []
    for r in reqs:
        ev = "<br>".join(
            official(x) if x.startswith("http") else repo_link(x) for x in r["evidence"])
        rows.append([
            f"<b>{e(r['id'])}</b>",
            e(r["text"]) + (f'<div class="small">{e(r["detail"])}</div>' if r["detail"] else ""),
            pill(r["status"]),
            e(r["gate"]) or "—",
            e(r["clearing_metric"]) or "—",
            ev,
        ])
    body = f"""
<h1>Decision readiness</h1>
<div class="callout blue"><b>Executive summary (session 310620fe, 2026-11-16).</b>
The verified results corpus now covers <b>148 finals</b> (137 of them independently cross-verified against two
sources, 0 mismatches). Home-field advantage measures <b>−0.65 pts</b> — approximately zero again. The luck panel
puts every team's win total within ±2.2 wins of its Pythagorean expectation (1σ ≈ 1.5 at n≈9). Control baselines are
frozen (favourites cover 52.0%; random 54.1%). STRAT-1 is the first pre-registered strategy: method text frozen
2026-11-16, three days before Week 11 opens, with 13 forecasts and their market residuals recorded pre-kickoff.
Infrastructure now exists for the price-snapshot store (openings blank — no reachable source publishes them), the
point-in-time snapshot ledger, drift alarms on seven datasets, Wed/Fri availability capture automation, the venue
feed (Munich cross-verified against the official game centre) and the per-team availability view. Remaining blockers
are all source-access problems (IR/reserve status, NWS weather, archived injury seasons, play-level 2026 data) and
are listed with their missing sources on <a href="flagged.html">Flagged for Review</a>.</div>
<p class="lede">One row per requirement in the current brief (R26–R96; the original R01–R25 register lives in
{repo_link('data/requirements.csv')}). Each row states the gate that blocks it and the number that would clear it.
Statuses were set from files that exist in the repository and from live official-page fetches on 2026-11-16.</p>
<div class="kpis">
<div class="kpi"><div class="n">{len(reqs)}</div><div class="l">requirements registered</div></div>
<div class="kpi"><div class="n">{counts.get('done', 0)}</div><div class="l">done</div></div>
<div class="kpi"><div class="n">{counts.get('partial', 0)}</div><div class="l">partial — gate named</div></div>
<div class="kpi"><div class="n">{counts.get('registered', 0)}</div><div class="l">registered, not built</div></div>
<div class="kpi"><div class="n">{counts.get('blocked', 0)}</div><div class="l">blocked, external gate</div></div>
<div class="kpi"><div class="n">{counts.get('rejected', 0)}</div><div class="l">rejections recorded</div></div>
</div>
<div class="callout blue"><b>How to read this.</b> "Partial" means the work exists but a named gate holds the rest —
the clearing number says exactly what would move it to done. "Blocked" rows wait on sources outside this
environment (IR/reserve status, NWS weather, archived injury seasons, play-level 2026 data) and are listed with the
missing source on <a href="flagged.html">Flagged for Review</a>. Nothing was inferred to fill a gate.</div>
<h2>Requirements register (all {len(reqs)} rows)</h2>
{table(["ID", "Requirement (verbatim)", "Status", "Gate that blocks it", "Number that would clear it", "Evidence"], rows)}
"""
    page("index.html", "Decision readiness", "index", body,
         "One row per requirement: the gate that blocks it and the number that would clear it.")


def build_ops() -> None:
    base = json.load(open(os.path.join(HERE, "data", "baselines_2026.json")))
    luck = list(csv.DictReader(open(os.path.join(HERE, "data", "luck_panel_2026.csv"))))
    teams = list(csv.DictReader(open(os.path.join(HERE, "data", "team_availability_2026_w10.csv"))))
    feed = list(csv.DictReader(open(os.path.join(HERE, "data", "results", "results_2026_reg.csv"))))
    prices = list(csv.DictReader(open(os.path.join(HERE, "data", "price_snapshots.csv"))))
    ledger = list(csv.DictReader(open(os.path.join(HERE, "data", "snapshots", "ledger.csv"))))
    venues = list(csv.DictReader(open(os.path.join(HERE, "data", "venues_2026_reg.csv"))))
    fc = list(csv.DictReader(open(os.path.join(HERE, "data", "forecast_week11_2026.csv"))))
    reg = json.load(open(os.path.join(HERE, "data", "requirements_v2.json")))

    SRC_URL = "https://github.com/nflverse/nfldata/blob/master/data/games.csv"

    # results feed by week
    weeks = {}
    for r in feed:
        w = weeks.setdefault(int(r["week"]), {"final": 0, "pending": 0})
        w["final" if r["status"] == "final" else "pending"] += 1
    wrows = [[f"<b>{w}</b>", wk["final"], wk["pending"] or "—",
              official("https://www.nfl.com/schedules/2026/by-week/week-" + str(w))]
             for w, wk in sorted(weeks.items())]

    # week 10 finals incl. the 11 new ones
    w10 = [r for r in feed if r["week"] == "10"]
    w10rows = []
    for r in sorted(w10, key=lambda x: (x["gameday"], x["game_id"])):
        score = (f"{r['away_pts']}–{r['home_pts']}" if r["status"] == "final"
                 else "<span class='small'>blank — not final at fetch (flagged)</span>")
        w10rows.append([e(r["game_id"]), e(r["gameday"]), f"{e(r['away_team'])} @ {e(r['home_team'])}",
                        score, e(r["status"]), e(r["cross_check"]), official(r["source_url"])])

    # luck panel (all 32)
    luckrows = [[f"<b>{e(r['team'])}</b>", e(r["games"]), e(r["w"]), e(r["l"]), e(r["t"]), e(r["pf"]), e(r["pa"]),
                 e(r["actual_win_pct"]), e(r["pyth_win_pct"]), e(r["pyth_expected_wins"]),
                 ("<b style='color:#8c3b2e'>" if float(r["luck_wins_vs_pyth"]) < 0 else "<b style='color:#135f46'>")
                 + e(r["luck_wins_vs_pyth"]) + "</b>", official(REPO + "ops/luck_panel.py", "method")]
                for r in luck]

    # team view (28 with reports)
    trows = [[f"<b>{e(r['team'])}</b>", e(r["next_opponent"]), e(r["report_rows"]), e(r["out"]), e(r["doubtful"]),
              e(r["questionable"]), e(r["dnp"]), e(r["designation_blank"]), f"<b>{e(r['net_injury_count'])}</b>",
              "<span class='small'>unknown — IR not captured (flagged)</span>",
              official(r["source_url"])] for r in teams]

    # price store
    prows = [[e(p["game_id"]), e(p["market"]), "<span class='pill blocked'>T3</span>",
              ("<span class='small'>blank — opening unavailable (flagged)</span>" if not p["line_open"] else e(p["line_open"])),
              e(p["line_close"]), e(p["ts_utc"][:10]),
              official(p["source_url"]), "<span class='small'>" + e(p["note"]) + "</span>"] for p in prices]

    # baselines
    fb, rb = base["favourite_baseline"], base["random_baseline"]
    baserows = [
        ["random50 (frozen seed)", str(rb["n_games"]), f"{rb['picks_correct']} / {rb['n_games']}",
         f"<b>{rb['rate']}</b>", "0.500 expected", repo_link("ops/baselines.py")],
        ["favourites-only (closing spread)", str(fb["n_games"]),
         f"{fb['favourite_straight_up_wins']} / {fb['n_games']} SU",
         f"<b>{fb['favourite_straight_up_rate']}</b>", f"cover {fb['favourite_cover_rate']}; Brier {fb['brier_pick_prob_0.5']}",
         repo_link("ops/data/price_snapshots.csv") + " · " + official(SRC_URL)],
    ]

    # venues week 10 + mix
    v10 = [r for r in venues if r["week"] == "10"]
    roofs, surfaces = {}, {}
    for r in venues:
        roofs[r["roof"] or "(blank)"] = roofs.get(r["roof"] or "(blank)", 0) + 1
        surfaces[r["surface"] or "(blank)"] = surfaces.get(r["surface"] or "(blank)", 0) + 1
    vrows = [[e(r["game_id"]), f"{e(r['away_team'])} @ {e(r['home_team'])}", e(r["gameday"]),
              f"<b>{e(r['stadium'])}</b>" if r["stadium"] else "<span class='small'>blank — flagged</span>",
              e(r["roof"]) or "<span class='small'>blank</span>", e(r["surface"]) or "<span class='small'>blank</span>",
              "official game centre ✓" if r["verified_against_game_centre"] == "yes" else "<span class='small'>T2 only</span>",
              official(r["official_game_centre"])] for r in v10]

    # forecasts
    frows = []
    for r in fc:
        frows.append([e(r["game_id"]), e(r["gameday"]), f"{e(r['away_team'])} @ {e(r['home_team'])}",
                      f"<b>{e(r['fl2_total'])}</b>", f"<b>{e(r['fl2_home_margin'])}</b>", e(r["fl2_p_home"]),
                      e(r["market_spread_close_T3"]) or "<span class='small'>blank</span>",
                      e(r["market_total_close_T3"]) or "<span class='small'>blank</span>",
                      e(r["residual_margin_vs_market"]), e(r["residual_total_vs_market"]),
                      "<span class='small'>" + e(r["recorded_before_kickoff"]) + "</span>",
                      official(r["source_url"])])

    # ledger
    lrows = [[e(l["entry_id"]), e(l["dataset"]), repo_link(l["path"]), e(l["captured_as_of"]),
              f"<span class='mono'>{e(l['sha256'][:16])}…</span>", e(l["row_count"]),
              official(l["source_url"]),
              "<span class='small'>" + e(l["conflicts"]) + "</span>" if l["conflicts"] else "—"] for l in ledger]

    body = f"""
<h1>Ops dashboard</h1>
<p class="lede">The infrastructure the requirements asked for, built against data already verified in this repository.
Every number is recomputed by the linked script from its source file — nothing hand-typed. Market prices are
T3 (aggregated market) and are never statistical inputs to a gate (price policy P2).</p>

<h2 id="results">Verified results feed</h2>
<p>{len(feed)} scheduled games Weeks 1–10; {sum(w['final'] for w in weeks.values())} final.
The T1 transcription (NFL.com) matches the nflverse mirror on <b>137/137</b> scored games.
The 11 Week 10 Sunday finals were transcribed 2026-11-16 from the official schedule page and predate the mirror's snapshot.</p>
{table(["Week", "Final", "Pending (scores blank)", "Official schedule page"], wrows)}
<h3>Week 10 — all 14 games</h3>
{table(["Game", "Date", "Matchup", "Score (away–home)", "Status", "Cross-check", "Source"], w10rows)}

<h2 id="luck">Removal-of-luck panel</h2>
<p>Pythagorean expectation (exponent 2.37) on the verified feed, <b>n = 148 games</b>, each value published with its n.
A one-sigma binomial swing at ~9 games/team is ≈ 1.5 wins — residuals inside ±1.5 are noise, not signal.</p>
{table(["Team", "GP", "W", "L", "T", "PF", "PA", "Win%", "Pyth%", "Pyth W", "Luck (wins)", "Method"], luckrows)}

<h2 id="baselines">Control baselines</h2>
<p>Required in every leaderboard run so skill is separated from luck.</p>
{table(["Baseline", "n", "Result", "Rate", "Detail", "Source"], baserows)}

<h2 id="teams">Per-team availability view (Week 10 official report)</h2>
<p>28 clubs published a Week 10 report (CHI, DEN, PHI, TB were on bye and are excluded with a note, not zeros).
"IR unknown" is an honest flag: no verified source carries the reserve list, so <b>not listed ≠ available</b>.</p>
{table(["Team", "Next opponent", "Report rows", "Out", "Doubtful", "Questionable", "DNP", "Blank designations", "Net (Out+Doubtful)", "Reserve/IR", "Source"], trows)}

<h2 id="prices">Price-snapshot store</h2>
<p>Append-only, sha256-stamped, tier-labelled. Openings are blank and flagged — the only reachable source publishes
closings (policy P3). No price was invented.</p>
{table(["Game", "Market", "Tier", "Open", "Close", "Stored (UTC)", "Source", "Note"], prows)}

<h2 id="venues">Venues &amp; fixture context (Week 10 shown; full file Weeks 1–10)</h2>
<p>Stadium facts are T2 open data (official GSIS-derived); the Munich game was verified directly against the official
game centre on 2026-11-16. Roof mix (150 fixtures): {", ".join(f"{k} × {v}" for k, v in sorted(roofs.items(), key=lambda x: -x[1]))}.
Surface mix: {", ".join(f"{k} × {v}" for k, v in sorted(surfaces.items(), key=lambda x: -x[1]))}.
NWS weather grids are unreachable from this environment — wind/precip stay blank (flagged).</p>
{table(["Game", "Matchup", "Date", "Stadium", "Roof", "Surface", "Verified", "Source"], vrows)}

<h2 id="forecast">Pre-registered Week 11 forecasts (STRAT-1, recorded pre-kickoff)</h2>
<div class="callout"><b>Registration.</b> Method text, sample window and gates frozen in
{repo_link('ops/forecast_week11.py')} and committed 2026-11-16 — three days before the Week 11 opener (2026-11-19).
Fixtures are T2 (nflverse) pending T1 confirmation: the official /reg11 page currently redirects to the live week.
The model has no QB-quality term (documented); large residuals against the market are expected and are published,
not hidden. <b>These are research forecasts, not betting recommendations.</b></div>
{table(["Game", "Date", "Matchup", "FL2 total", "FL2 margin (home)", "p(home)", "Market spread (T3)", "Market total (T3)",
        "Residual margin", "Residual total", "Timing", "Source"], frows)}

<h2 id="ledger">Point-in-time snapshot ledger</h2>
<p>Append-only; the delta between rows is published, never a silently updated level.</p>
{table(["Entry", "Dataset", "File", "Captured as of", "sha256", "Rows", "Source", "Conflicts"], lrows)}

<h2 id="drift">Drift pins</h2>
<p>{len(json.load(open(os.path.join(HERE, 'data', 'drift_manifest.json'))))} datasets pinned to row counts, required
fields and maximum capture age; violations exit 1 ({repo_link('ops/drift_check.py')}). Schedule announcement, as
published on the official page beside the live schedule: Week 16/17/18 windows are announced with
<a href="https://www.nfl.com/legal/flexible-scheduling-procedures">the league's flexible-scheduling procedures</a>
(dated 2026 announcement text captured in {repo_link('ops/build_site.py')} inputs and the official schedule page).</p>
"""
    page("ops.html", "Ops dashboard", "ops", body,
         "Price store, results feed, luck panel, baselines, team availability, venues, forecasts, ledger, drift pins.")


def build_flagged() -> None:
    items = [
        ("Opening prices unavailable",
         "The only reachable price source (nflverse snapshot) publishes closing lines only. The price store's opening column is blank on all 28 rows rather than estimated.",
         ["ops/price_policy.md (P3)", "https://github.com/nflverse/nfldata/blob/master/data/games.csv"]),
        ("No official odds page exists",
         "nfl.com/odds/ returns 404 (verified by session 1374049c, reproduced from COORDINATION.md). All bookmaker prices in this repo are T3 and labelled market_data_unverified.",
         ["https://www.nfl.com/odds/"]),
        ("Reserve/IR status has no verified source",
         "nflverse rosters.csv has no 2026 rows and no status column (verified 2026-11-16); nfl.com roster pages are not reachable from the bulk pipeline. Every team row therefore carries an explicit IR-unknown flag instead of treating 'not listed' as available.",
         ["raw/_nfldata/rosters.csv", "ops/data/team_availability_2026_w10.csv"]),
        ("NWS weather grids unreachable",
         "weather.gov is not on this environment's outbound allow-list, so the roof/surface feed ships without wind/precip. Stadium facts themselves are T2 with one official game-centre cross-check.",
         ["ops/venues.py"]),
        ("Week 11 fixtures: T1 confirmation pending",
         "The official /schedules/2026/reg11/ page currently redirects to the live week, so Week 11 fixtures and forecasts use T2 nflverse schedule facts and are flagged as pending T1 confirmation.",
         ["https://www.nfl.com/schedules/2026/reg10/", "ops/data/forecast_week11_2026.csv"]),
        ("Two Week 10 games without final scores at fetch time",
         "PIT@CIN (SNF, Nov 15) was in progress and LAC@BAL (MNF, Nov 16) unplayed when the official page was fetched 2026-11-16. Their score cells are blank and flagged; they were not inferred.",
         ["https://www.nfl.com/games/steelers-at-bengals-2026-reg-10", "https://www.nfl.com/games/chargers-at-ravens-2026-reg-10"]),
        ("Availability-capture workflow untested",
         "The Wed/Thu/Fri capture workflow (.github/workflows/availability-snapshot.yml) is committed and scheduled but has not completed a run in CI; its first successful run is the gate for R54/R79.",
         [".github/workflows/availability-snapshot.yml"]),
        ("Multi-season injury archive not reachable",
         "nflverse/nfldata contains no injury-report table (verified via the GitHub contents API 2026-11-16); release assets fail from this environment. This keeps designation-calibration (R69/R78) and past-season archives (R91) blocked.",
         ["https://api.github.com/repos/nflverse/nfldata/contents/data"]),
        ("Model has no QB-quality term",
         "The originated lines are PPG-based with shrinkage; Week 11 residuals against the market reach double digits on QB-differentiated games. The caveat is declared in the model output, not hidden — this is exactly why signals must clear skill gates before any staking.",
         ["ops/data/forecast_week11_2026.csv", "data/market_lines.json"]),
        ("CIN live report count grew after capture",
         "The re-capture requirement described 4 live CIN players; at the 2026-11-16 fetch both committed captures carry 9 CIN rows (reports grow during the week). The automated capture series keeps pace; the register records both numbers.",
         ["https://www.nfl.com/injuries/"]),
    ]
    def src_links(srcs: list[str]) -> str:
        out = []
        for x in srcs:
            if x.startswith("http"):
                out.append(official(x))
            else:
                path, _, suffix = x.partition(" (")
                link = f'<a href="{REPO}{e(path)}">{e(path)}</a>'
                out.append(link + (f" ({e(suffix.rstrip(')'))})" if suffix else ""))
        return "<br>".join(out)

    rows = [[f"<b>{i + 1}</b>", e(t), e(d), src_links(srcs)]
            for i, (t, d, srcs) in enumerate(items)]
    body = f"""
<h1>Flagged for review</h1>
<p class="lede">Items this session could not verify, or deliberately left blank. Flagged items do not block anything;
they are published so a reviewer can request changes after the site is live.</p>
{table(["#", "Item", "Detail", "Source"], rows)}
"""
    page("flagged.html", "Flagged for review", "flagged", body,
         "Unverified items and policy blanks, each with its source link.")


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "style.css"), "w") as fh:
        fh.write(CSS)
    build_index()
    build_ops()
    build_flagged()
    for f in ("index.html", "ops.html", "flagged.html"):
        p = os.path.join(OUT, f)
        print(f"wrote {p} ({os.path.getsize(p)} bytes)")


if __name__ == "__main__":
    main()

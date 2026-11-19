#!/usr/bin/env python3
"""Builds review/repo-review-2026-11-19.html and .md from one data definition.

Session 6e645ee7 (2026-11-19). Every fact below was either (a) re-read on an official
nfl.com page on 2026-11-19 via the page-fetch tool, (b) measured in this repository with
the commands recorded in the page, or (c) explicitly marked as not verified.
Run:  python3 review/build_review_2026_11_19.py
"""
from __future__ import annotations

import csv
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_BLOB = "https://github.com/sassnarep3-star/FL2/blob/main/"

# Official pages (all fetched 2026-11-19 with the page-fetch tool).
WEEK10 = "https://www.nfl.com/schedules/2026/by-week/week-10"
WEEK11 = "https://www.nfl.com/schedules/2026/by-week/week-11"
INJ = "https://www.nfl.com/injuries/league/2026/reg10"
TERMS = "https://www.nfl.com/legal/terms/"
STAND = "https://www.nfl.com/standings/"
GH_CHECKOUT = "https://github.com/actions/checkout/releases"


def repo(path: str) -> str:
    return REPO_BLOB + path


def a(href: str, label: str | None = None) -> str:
    # Labels are trusted literals in this file (they may carry HTML entities such as &sect;).
    return f'<a href="{html.escape(href)}">{label or html.escape(href)}</a>'


# ---- Section 2: verified this session -------------------------------------------------
VERIFIED = [
    ("V1", "Week 10 final scores, all 14 games",
     f"{a(WEEK10, 'nfl.com Week 10 schedule')}",
     "14 of 14 match the official final scores. Per-game links are in section 2.",
     f"{a(repo('review/results-corrections-2026-11-19.csv'), 'corrections register')}"),
    ("V2", "Week 10 Thursday game is final: Commanders 24, Giants 21 (Nov 12)",
     f"{a(WEEK10, 'nfl.com Week 10 schedule')}",
     "The landing page said the data was captured &ldquo;before Week 10 kicked off&rdquo;. That is false: the game was already final two days before the 2026-11-14 capture. The repository's own <code>data/injuries.json</code> (retrieved 2026-11-14) lists it as &ldquo;Commanders 24, Giants 21&rdquo;. <strong>Corrected.</strong>",
     f"{a(repo('index.html'), 'index.html')}"),
    ("V3", "Records after Week 10: Buffalo 8&ndash;1, Cincinnati 7&ndash;2, Detroit 7&ndash;2, New England 5&ndash;5",
     f"{a(WEEK10, 'nfl.com Week 10 schedule')} &middot; {a(STAND, 'nfl.com standings')}",
     "Match the landing-page text. The 2026-11-14 standings snapshot shows Buffalo 7&ndash;1, so it predates the Sunday game.",
     f"{a(repo('data/standings-2026-w10.csv'), 'standings-2026-w10.csv')}"),
    ("V4", "Lions Out, did not practise: Kerby Joseph (S, Knee), Cade Mays (C, Ankle), D.J. Reed (CB, Hip)",
     f"{a(INJ, 'nfl.com 2026 injury report, Week 10 heading')}",
     "All three read Out / Did Not Participate In Practice, as in the repository. The page title says Week 11 (see I-05).",
     f"{a(repo('data/injuries.json'), 'data/injuries.json')}"),
    ("V5", "Week 11 kickoff: Colts at Texans, Thursday Nov 19, 8:15 PM ET",
     f"{a(WEEK11, 'nfl.com Week 11 schedule')}",
     "Equals 2026-11-20 01:15 UTC. The Week 11 ledger was recorded 2026-11-16 01:30Z, before kickoff. Consistency check only: git dates are author-supplied.",
     f"{a(repo('fl2-lines/data/ledger/LEDGER-TIP.txt'), 'LEDGER-TIP.txt')}"),
    ("V6", "NFL Terms &sect;1.3 (updated May 16, 2024): systematic retrieval to compile a database is prohibited absent express prior written consent",
     f"{a(TERMS, 'nfl.com legal terms')}",
     "Confirms the basis of gate F-T1. The three capture workflows now fail closed on main (PR #45). No capture was run in this session.",
     f"{a(repo('.github/workflows/fl2-lines-snapshot.yml'), 'fl2-lines-snapshot.yml')}"),
    ("V7", "Official standings: the DIFF column equals points for minus points against (checked for the 24 teams on the first page chunk, e.g. Buffalo 287&minus;199 = 88)",
     f"{a(STAND, 'nfl.com standings')}",
     "Shows that the 32 &ldquo;MISMATCH&rdquo; notes in the repository standings file are false (see I-06). The 8 teams on the second chunk were not checked.",
     f"{a(repo('data/standings-2026-w10.csv'), 'standings-2026-w10.csv')}"),
    ("V8", "Injury page title reads &ldquo;Week 11 of the 2026 Season&rdquo;; the page heading reads &ldquo;Injuries &ndash; WEEK 10&rdquo;",
     f"{a(INJ, 'nfl.com 2026 injury report')}",
     "Source-side inconsistency. The repository uses the heading (Week 10). Flagged, not resolved (I-05).",
     "&mdash;"),
    ("V9", "Pinned Pages actions are the latest releases: checkout v7.0.1, configure-pages v6.0.0, upload-pages-artifact v5.0.0, deploy-pages v5.0.1",
     f"{a(GH_CHECKOUT, 'GitHub actions/checkout releases (tooling source, not an NFL source)')}",
     "Checked through the GitHub releases API. No change needed. Other workflows still use checkout@v4; not a defect.",
     f"{a(repo('.github/workflows/pages.yml'), 'pages.yml')}"),
]

# ---- Section 4: irregularities --------------------------------------------------------
IRREG = [
    ("I-01", "High",
     "Week 10 results feeds disagree with the official finals. LAC&nbsp;@&nbsp;BAL (official 23&ndash;20) is not final in any of the three feeds. PIT&nbsp;@&nbsp;CIN (official 18&ndash;38) is blank in <code>fl2-lines</code>.",
     f"{a(repo('review/results-corrections-2026-11-19.csv'), 'corrections register')} &middot; {a(WEEK10, 'official schedule')}",
     "Logged, not edited. <code>ops/forecast_week11.py</code> reads the ops feed, so editing it would change pre-registered inputs. Owner decision D2."),
    ("I-02", "High",
     "Landing page stated the data was captured before Week 10 kicked off. The Thursday Week 10 game was already final on Nov 12.",
     f"{a(WEEK10, 'official schedule')} &middot; {a(repo('index.html'), 'index.html (original sentence)')}",
     "<strong>Fixed</strong> on the landing page in this session."),
    ("I-03", "Medium",
     "Landing table showed LAC&nbsp;@&nbsp;BAL as pending and &ldquo;149/150 finals&rdquo; as the current count. The official page shows it final.",
     f"{a(WEEK10, 'official schedule')}",
     "<strong>Updated</strong> on the landing page to the official value, with the feed lag stated and linked."),
    ("I-04", "Medium",
     "README still says &ldquo;148 final scores out of 150&rdquo;. That was true on 2026-11-16 but is superseded: the ops feed now has 149 final, and the official page has all 14 Week 10 games final.",
     f"{a(repo('README.md'), 'README.md')} &middot; {a(WEEK10, 'official schedule')}",
     "Flagged, not edited (README is shared). Owner to refresh the README status line."),
    ("I-05", "Low",
     "Official injury page has a title that says Week 11 while the heading says Week 10, at the same URL.",
     f"{a(INJ, 'nfl.com 2026 injury report')}",
     "Flagged. Repository uses the heading. Ask the league's content team; no inference made."),
    ("I-06", "Medium",
     "All 32 rows of the verified standings file carry the note &ldquo;MISMATCH: published net points differ from PF-PA&rdquo;. Arithmetic shows net = PF&minus;PA on every row, and the official DIFF column agrees for the 24 teams checked.",
     f"{a(repo('data/standings-2026-w10.csv'), 'standings-2026-w10.csv')} &middot; {a(STAND, 'nfl.com standings')}",
     "<strong>Fixed:</strong> note text only, values unchanged (32 rows). The original text is recorded here."),
    ("I-07", "High (policy)",
     "Automated capture of nfl.com pages conflicts with NFL Terms &sect;1.3 unless written consent is obtained. The repository had live schedules (Tuesday and Wed&ndash;Fri crons) before PR #45 disabled them.",
     f"{a(TERMS, 'nfl.com terms &sect;1.3')} &middot; {a(repo('.github/workflows/fl2-lines-snapshot.yml'), 'fl2-lines-snapshot.yml')}",
     "Fail-closed guard on main (PR #45). The owner decides whether any capture is authorised (decision D1). Not decided here."),
    ("I-08", "Medium",
     "Five copies of the Week 10 injury report with different content: <code>data/injuries.json</code> (501 lines), <code>data/injuries_2026_week10.csv</code> (346), <code>data/injury-report-2026-w10.csv</code> (161), and the 2026-11-14 (346) and 2026-11-16 (348) captures. There is no single designated source.",
     f"{a(repo('data/injuries_2026_week10.csv'), 'injuries_2026_week10.csv')} &middot; {a(repo('data/linelab/captures/2026-11-16/week10-injury-report.csv'), '2026-11-16 capture')}",
     "Flagged, nothing deleted. Owner decision D3 (choose the canonical copy)."),
    ("I-09", "Medium",
     "Large derived files are tracked in git: <code>signal/data/depth_player.json</code> 20.5&nbsp;MB, <code>signal/data/snap_participation.json</code> 16.4&nbsp;MB, <code>data/linelab/model_outputs.csv</code> 13.4&nbsp;MB, and <code>signal/</code> totals about 73&nbsp;MB on disk. The brief asks that large datasets stay out of git.",
     f"{a(repo('signal/data/depth_player.json'), 'depth_player.json')} &middot; {a(repo('data/linelab/model_outputs.csv'), 'model_outputs.csv')}",
     "Flagged, not moved (consumers depend on them). Owner decision D4."),
    ("I-10", "Low",
     "Duplicate raw file: <code>raw/games.csv</code> and <code>raw/_nfldata/games.csv</code> are byte-identical (md5 0572cae24b6cf3f7bd195a2152622e1c). A 2.6&nbsp;MB archive <code>raw/_nfldata.tgz</code> is also committed.",
     f"{a(repo('raw/games.csv'), 'raw/games.csv')} &middot; {a(repo('raw/_nfldata/games.csv'), 'raw/_nfldata/games.csv')}",
     "Flagged. No file removed."),
    ("I-11", "Medium",
     "Fragmentation: nine separate flagged pages (<code>docs</code>, <code>fl2-dashboard</code>, <code>fl2-depth</code>, <code>fl2-lines</code>, <code>fl2-signals</code>, <code>hub</code>, <code>ledger</code>, <code>linelab</code>, <code>readiness</code>), plus <code>review/</code>, and 129 HTML files in all. The brief asks for one organised site.",
     f"{a(repo('ledger/flagged.html'), 'ledger/flagged.html')} &middot; {a(repo('linelab/flagged.html'), 'linelab/flagged.html')}",
     "Flagged. Owner decision D5 (consolidate or keep)."),
    ("I-13", "Medium",
     "The committed <code>docs/</code> copy of the analysis dashboard does not match what its generator produces. Running <code>scripts/make_pages.py</code> and <code>scripts/build_site.py</code> changes 11 pages (the <code>../hub/index.html</code> &ldquo;Decision Hub&rdquo; nav link disappears). The Pages validate job rebuilds these files but never compares them, and the deploy job re-checks out the committed tree, so the rebuilt output is never published.",
     f"{a(repo('.github/workflows/pages.yml'), 'pages.yml')} &middot; {a(repo('docs/index.html'), 'docs/index.html')}",
     "Flagged, not changed. Publishing the rebuilt nav would alter the live dashboard without a decision. Owner decision D5 (site structure)."),
    ("I-12", "Info",
     "The clone the session started from had one commit (shallow). The pre-registration timing check was impossible until history was fetched. Local history is now complete (211 commits).",
     f"{a(repo('.github/workflows/fl2-lines-check.yml'), 'fl2-lines-check.yml')}",
     "Recorded. Verification jobs should use full history where a commit date is evidence."),
]

# ---- Section 5: owner decisions --------------------------------------------------------
DECISIONS = [
    ("D1", "Capture authorisation (F-T1)",
     "Obtain written consent from NFL for systematic capture, or keep capture manual and derived-only. Until then keep the fail-closed guard.",
     f"{a(TERMS, 'nfl.com terms &sect;1.3')}"),
    ("D2", "Week 10 corrections (I-01)",
     "Accept the two-row correction and choose: (a) keep the Week 11 forecast as registered and footnote the input drift, or (b) register a corrected Week 11 v2 with a new hash. Do not silently re-run.",
     f"{a(repo('review/results-corrections-2026-11-19.csv'), 'corrections register')}"),
    ("D3", "Canonical injury source (I-08)", "Name one Week 10 injury file as canonical and mark the rest as derived or retired.",
     f"{a(repo('data/injuries_2026_week10.csv'), 'injuries_2026_week10.csv')}"),
    ("D4", "Large files in git (I-09)", "Move regenerable derived files out of git, following the repository's existing storage convention.",
     f"{a(repo('signal/data/depth_player.json'), 'depth_player.json')}"),
    ("D5", "Site structure (I-11)", "Consolidate the nine flagged pages and overlapping sub-sites, or keep them and say which is authoritative.",
     f"{a(repo('ledger/suggestions.html'), 'ledger/suggestions.html (existing suggestion register)')}"),
]

# ---- Section 6: not verified / not done ------------------------------------------------
NOT_CHECKED = [
    ("Week 10 injury totals on the landing page (66 Out, 10 Doubtful)",
     "Not re-counted. The official page spans eight chunks, too many to count reliably by hand.",
     f"{a(INJ, 'nfl.com 2026 injury report')}"),
    ("Week 1&ndash;9 results and all other 1,000+ table rows across the sites",
     "Only the 14 Week 10 finals were re-read. A full line-by-line audit was not done in this session.",
     f"{a(WEEK10, 'nfl.com Week 10 schedule')}"),
    ("Depth-chart claims: Texans depth image, Packers jersey prefixes, Seattle shared and Washington empty slots, Colts receiver trades, Baltimore QB rows, Malik Willis IR",
     "Official club depth-chart pages were not fetched in this session. Nothing about depth or starters is re-verified here.",
     f"{a('https://www.nfl.com/injuries/', 'nfl.com injuries (starting point)')}"),
    ("Odds and price data (no official NFL odds feed)",
     "Not re-checked. The landing page already reports nfl.com/odds as a 404 in an earlier session.",
     f"{a('https://www.nfl.com/odds/', 'nfl.com/odds')}"),
    ("Game-day inactives, snap counts, game books",
     "Not fetched. The capture route is blocked by gate F-T1 (decision D1).",
     f"{a(TERMS, 'nfl.com terms &sect;1.3')}"),
]


def read_corrections() -> list[dict]:
    with open(ROOT / "review/results-corrections-2026-11-19.csv", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def requirement_counts() -> dict:
    import json
    d = json.loads((ROOT / "ops/data/requirements_v2.json").read_text(encoding="utf-8"))
    out: dict[str, int] = {}
    for r in d["requirements"]:
        out[r["status"]] = out.get(r["status"], 0) + 1
    return out


def build_html(corr: list[dict], reqs: dict) -> str:
    def row(cells: list[str], tag: str = "td") -> str:
        return "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"

    ver_rows = "\n".join(row([f"<strong>{i}</strong>", c, s, r, e]) for i, c, s, r, e in VERIFIED)
    corr_rows = []
    for x in corr:
        mark = "match" if x["all_feeds_match_official"] == "yes" else "<strong>differs</strong>"
        corr_rows.append(row([
            f"{html.escape(x['away'])} @ {html.escape(x['home'])}",
            f"Final {x['official_away_pts']}&ndash;{x['official_home_pts']} ({html.escape(x['official_label'])})",
            a(x["official_source_url"], "game centre"),
            html.escape(x["ops_feed"]),
            html.escape(x["fl2_lines_feed"]),
            html.escape(x["results_feed_csv"]),
            mark,
        ]))
    irr_rows = "\n".join(row([f"<strong>{i}</strong>", s, w, e, st]) for i, s, w, e, st in IRREG)
    dec_rows = "\n".join(row([f"<strong>{i}</strong>", t, d, e]) for i, t, d, e in DECISIONS)
    nc_rows = "\n".join(row([t, n, e]) for t, n, e in NOT_CHECKED)
    req_line = ", ".join(f"{v} {k}" for k, v in sorted(reqs.items(), key=lambda kv: -kv[1]))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Repo review 2026-11-19 · FL2</title>
<meta name="description" content="Line-by-line re-check of FL2 against nfl.com on 2026-11-19: what was verified, what was corrected, what was flagged, and what was not checked.">
<link rel="stylesheet" href="../assets/style.css">
</head>
<body>
<header class="site-header">
  <div class="inner">
    <div class="brand-row">
      <div class="brand">FL2 <span>· Repo review 2026-11-19</span></div>
      <div class="brand-sub">Session 6e645ee7 · re-checked against nfl.com on 2026-11-19 · every value sourced or flagged</div>
    </div>
    <nav class="tabs" aria-label="Sections">
      <a href="../index.html">Overview</a>
      <a href="repo-review-2026-11-19.html" aria-current="page">Repo review</a>
      <a href="../ledger/flagged.html">Flagged</a>
      <a href="integration-audit-2026-11-17.html">Integration audit</a>
      <a href="../readiness/index.html">Readiness</a>
      <a href="../ledger/suggestions.html">Suggestions</a>
    </nav>
  </div>
</header>
<main>
<section class="block">
  <h1>Repo review, 2026-11-19</h1>
  <p class="sub">What was re-checked against official nfl.com pages, what was corrected, what was flagged, and what was not checked. Read this before relying on any Week 10 number in the repository.</p>
  <div class="note warn"><p><strong>Scope, stated plainly.</strong> This is a targeted re-verification, not a complete line-by-line audit. Every row below carries a source link. Anything not listed in section 1 or section 2 is <em>not</em> verified by this review; section 5 names the largest gaps.</p></div>
</section>

<section class="block" id="summary">
  <h2>Executive summary</h2>
  <ul>
    <li><strong>Week 10 results:</strong> all 14 official finals were re-read. Twelve games agree with every repository feed. Two rows are stale: Chargers 23&ndash;20 Ravens (not final in any feed) and Steelers 18&ndash;38 Bengals (blank in the <code>fl2-lines</code> feed). The corrections are logged for owner acceptance, not edited in place, because the pre-registered Week 11 forecast reads one of the feeds.</li>
    <li><strong>A false claim was corrected.</strong> The landing page said the data was captured before Week 10 kicked off. The Thursday Week 10 game was final two days before the capture date.</li>
    <li><strong>A false flag was corrected.</strong> The verified standings file marks all 32 teams as mismatched, but published net points equal points for minus points against for every team. Values are unchanged; only the note text was fixed.</li>
    <li><strong>Pre-registration timing holds on the evidence available.</strong> The Week 11 ledger was recorded 2026-11-16 01:30Z; the first Week 11 game kicks off 2026-11-20 01:15Z (8:15&nbsp;PM ET, Nov 19).</li>
    <li><strong>Automated capture is fail-closed.</strong> NFL Terms &sect;1.3 bars systematic retrieval to compile a database without written consent. Main has fail-closed guards (PR #45). No capture was run here. Authorisation is an owner decision (D1).</li>
    <li><strong>The main open items are owner decisions</strong> (section 4): capture authorisation, the Week 10 correction, a canonical injury file, large files in git, and site consolidation.</li>
  </ul>
  <p class="small">Requirement register (R26&ndash;R96, {a(repo('ops/data/requirements_v2.json'), 'requirements_v2.json')}, {a(repo('readiness/index.html'), 'readiness page')}): {html.escape(req_line)}. These counts are the repository's own, not re-verified here.</p>
</section>

<section class="block" id="verified">
  <h2>1. What was verified this session</h2>
  <div class="table-wrap"><table>
    <thead><tr><th>#</th><th>Claim checked</th><th>Official source</th><th>Result</th><th>Repository location</th></tr></thead>
    <tbody>
{ver_rows}
    </tbody>
  </table></div>
  <p class="small">Method: page-fetch tool reads of the URLs above on 2026-11-19. The sandbox itself cannot reach nfl.com. Repository checks were run locally, first at the session's starting commit (before the fast-forward to <code>eda52f6</code>), with no edits in place, and again after this session's edits: <code>scripts/check_site.py</code>, <code>tools/check_links.py</code>, <code>tools/check_signals_links.py</code>, <code>engine/linelab/check_site.py</code>, <code>fl2-lines/engine/check.py</code>, <code>ops/check_readiness.py</code>, <code>signal/analysis/verify.py</code> (216 checks), <code>tools/check_integrated_site.py</code>, <code>tools/check_decision_desk.py</code>, <code>ops/drift_check.py</code>. All ten passed in both runs.</p>
</section>

<section class="block" id="week10">
  <h2>2. Week 10 finals, line by line</h2>
  <p class="sub">Official values from the official Week 10 schedule page, compared with the three repository feeds. Source of the official values: {a(WEEK10, 'nfl.com Week 10 schedule')}, read 2026-11-19.</p>
  <div class="table-wrap"><table>
    <thead><tr><th>Game</th><th>Official result</th><th>Official source</th><th><code>ops/data/results</code></th><th><code>fl2-lines</code> feed</th><th><code>data/results_feed.csv</code></th><th>All match?</th></tr></thead>
    <tbody>
{chr(10).join(corr_rows)}
    </tbody>
  </table></div>
  <p class="small">Full register with every field: {a(repo('review/results-corrections-2026-11-19.csv'), 'review/results-corrections-2026-11-19.csv')}. Scores were not inferred for any blank cell; the blank values above are the repository's own.</p>
</section>

<section class="block" id="irregularities">
  <h2>3. Irregularities (flagged for review)</h2>
  <div class="table-wrap"><table>
    <thead><tr><th>#</th><th>Severity</th><th>Irregularity</th><th>Evidence / source</th><th>Status and action</th></tr></thead>
    <tbody>
{irr_rows}
    </tbody>
  </table></div>
</section>

<section class="block" id="decisions">
  <h2>4. Owner decisions needed</h2>
  <p class="sub">These cannot be made by an agent. Each lists the evidence to read first.</p>
  <div class="table-wrap"><table>
    <thead><tr><th>#</th><th>Decision</th><th>What is needed</th><th>Evidence</th></tr></thead>
    <tbody>
{dec_rows}
    </tbody>
  </table></div>
</section>

<section class="block" id="not-checked">
  <h2>5. Not checked in this review</h2>
  <p class="sub">Stated so that nobody reads an absence as a pass.</p>
  <div class="table-wrap"><table>
    <thead><tr><th>Item</th><th>Why not checked</th><th>Official starting point</th></tr></thead>
    <tbody>
{nc_rows}
    </tbody>
  </table></div>
</section>

<section class="block" id="method">
  <h2>6. Method and limits</h2>
  <ul>
    <li>Official values are copied from the page text returned by the page-fetch tool. Nothing was estimated.</li>
    <li>The 14 Week 10 scores are the only values checked line by line in this review. Everything else in section 5 is outside this review.</li>
    <li>The repository's committed data is unchanged except for the 2 landing-page sentences and the 32 standings note cells listed above.</li>
    <li>Frozen artefacts were not edited: <code>ops/data/results/results_2026_reg.csv</code>, <code>data/results_feed.csv</code>, <code>fl2-lines/data/official/*</code>, the Week 11 ledger and <code>ops/data/forecast_week11_2026.csv</code>.</li>
    <li>This page is generated by {a(repo('review/build_review_2026_11_19.py'), 'review/build_review_2026_11_19.py')} from one data definition. The Markdown twin is {a(repo('review/REPO-REVIEW-2026-11-19.md'), 'REPO-REVIEW-2026-11-19.md')}.</li>
  </ul>
  <p class="small">Research record only. Not betting advice.</p>
</section>
</main>
<footer class="footer"><div class="inner small">FL2 · repo review 2026-11-19 · sources: nfl.com pages read 2026-11-19 (links above) · this page makes no claim beyond them.</div></footer>
</body>
</html>
"""


def build_md(corr: list[dict], reqs: dict) -> str:
    def strip(s: str) -> str:
        import re
        # keep link targets in the Markdown copy: <a href="u">t</a> -> [t](u)
        s = re.sub(r'<a href="([^"]+)">(.*?)</a>', lambda m: f"[{m.group(2)}]({m.group(1)})", s)
        s = re.sub(r"<[^>]+>", "", s)
        return html.unescape(s).replace("|", "/").replace("\n", " ")

    lines = ["# Repo review, 2026-11-19 (session 6e645ee7)", "",
             "Generated by `review/build_review_2026_11_19.py`. The HTML page is the primary copy.", "",
             "## 1. Verified this session", "", "| # | Claim | Official source | Result | Repository location |",
             "|---|---|---|---|---|"]
    for i, c, s, r, e in VERIFIED:
        lines.append(f"| {i} | {strip(c)} | {strip(s)} | {strip(r)} | {strip(e)} |")
    lines += ["", "## 2. Week 10 finals", "", "| Game | Official | Official source | ops feed | fl2-lines | results_feed.csv | All match |", "|---|---|---|---|---|---|---|"]
    for x in corr:
        lines.append(f"| {x['away']} @ {x['home']} | Final {x['official_away_pts']}-{x['official_home_pts']} | {x['official_source_url']} | {x['ops_feed']} | {x['fl2_lines_feed']} | {x['results_feed_csv']} | {x['all_feeds_match_official']} |")
    lines += ["", "## 3. Irregularities", "", "| # | Severity | Irregularity | Evidence | Status |", "|---|---|---|---|---|"]
    for i, s, w, e, st in IRREG:
        lines.append(f"| {i} | {s} | {strip(w)} | {strip(e)} | {strip(st)} |")
    lines += ["", "## 4. Owner decisions", "", "| # | Decision | Needed | Evidence |", "|---|---|---|---|"]
    for i, t, d, e in DECISIONS:
        lines.append(f"| {i} | {t} | {strip(d)} | {strip(e)} |")
    lines += ["", "## 5. Not checked", "", "| Item | Why | Official starting point |", "|---|---|---|"]
    for t, n, e in NOT_CHECKED:
        lines.append(f"| {strip(t)} | {strip(n)} | {strip(e)} |")
    lines += ["", "Requirement register counts (repository's own): " + ", ".join(f"{k}: {v}" for k, v in sorted(reqs.items(), key=lambda kv: -kv[1])), ""]
    return "\n".join(lines)


def main() -> None:
    corr = read_corrections()
    reqs = requirement_counts()
    (ROOT / "review/repo-review-2026-11-19.html").write_text(build_html(corr, reqs), encoding="utf-8")
    (ROOT / "review/REPO-REVIEW-2026-11-19.md").write_text(build_md(corr, reqs), encoding="utf-8")
    print("wrote review/repo-review-2026-11-19.html and .md")


if __name__ == "__main__":
    main()

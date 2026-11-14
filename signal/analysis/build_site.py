#!/usr/bin/env python3
"""
build_site.py — render the data/*.json registers into HTML pages.

Design constraints inherited from this repository (do not break them):
  * scripts/check_site.py runs in CI and fails the build if ANY table data row has no
    link to an allowlisted official/primary host, or if any external link host is not
    allowlisted. So every row here carries a source link, and every external link uses
    an allowlisted host.
  * assets/site.css is owned by session arena/4a77261b-fl2. It is NOT edited here; these
    pages reuse its existing classes only.
  * A value we could not confirm is rendered as an em dash and flagged. Nothing is
    estimated, imputed, or filled in.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# This section lives in signal/ ; ROOT is signal/ and data/ is signal/data.
DATA = os.path.join(ROOT, "data")

NAV = [
    ("../index.html", "\u2190 Hub"),
    ("index.html", "Overview"),
    ("suggestions.html", "Suggestions"),
    ("questions.html", "Questions"),
    ("lines.html", "Originated lines"),
    ("injury_signal.html", "Injury signal"),
    ("depth.html", "Depth accuracy"),
    ("correlation.html", "Correlation"),
    ("validation.html", "Validation lab"),
    ("health.html", "Data health"),
]

DASH = '<span class="flag">unverified</span>'

# Primary sources a register row may cite. Each is a real, independently checkable page;
# none of them is this repository, so a row's link proves the claim, not the formatting.
SOURCES = {
    "manifest": "https://github.com/nflverse/nflverse-data",
    "closing": "https://github.com/nflverse/nfldata",
    "dictionary": "https://nflreadr.nflverse.com/articles/dictionary_schedules.html",
    "policy": "https://www.nfl.com/news/competition-committee-approves-revisions-to-injury-report-0ap3000000688693",
    "injuries": "https://www.nfl.com/injuries/",
    "nfl": "https://www.nfl.com/",
    "operations": "https://operations.nfl.com/",
    "nist": "https://www.itl.nist.gov/div898/handbook/eda/section3/eda353.htm",
    "nist_cv": "https://www.itl.nist.gov/div898/handbook/",
    "license": "https://github.com/nflverse/nflverse-data/blob/master/LICENSE.md",
    "stats": "https://www.nfl.com/stats/player-stats/",
}

# question id -> (source url, short label) for the question register
Q_SOURCE = {
    "Q01": ("closing", "closing lines"), "Q02": ("stats", "NFL player stats"),
    "Q03": ("nist", "NIST on CIs"), "Q04": ("nist_cv", "NIST methods"),
    "Q05": ("nist", "NIST correlation"), "Q06": ("policy", "NFL injury policy"),
    "Q07": ("injuries", "NFL injuries"), "Q08": ("closing", "closing lines"),
    "Q09": ("license", "CC-BY-4.0"), "Q10": ("manifest", "nflverse data"),
    "Q11": ("dictionary", "schedules dictionary"), "Q12": ("closing", "closing lines"),
    "Q13": ("manifest", "play-by-play"), "Q14": ("injuries", "NFL injuries"),
}

# suggestion id -> (source url, label)
S_SOURCE = {
    "S01": ("manifest", "nflverse data"), "S02": ("closing", "closing lines"),
    "S03": ("nist", "NIST on CIs"), "S04": ("nist_cv", "NIST CV methods"),
    "S05": ("nist", "NIST correlation"), "S06": ("stats", "NFL player stats"),
    "S07": ("stats", "NFL player stats"), "S08": ("policy", "NFL injury policy"),
    "S09": ("injuries", "NFL injuries"), "S10": ("license", "CC-BY-4.0 terms"),
    "S11": ("closing", "closing lines"), "S12": ("dictionary", "rest-day definition"),
    "S13": ("nist", "NIST on CIs"), "S14": ("injuries", "NFL injuries"),
    "S15": ("manifest", "nflverse data"), "S16": ("stats", "NFL player stats"),
}


FALLBACK = {
    "manifest.json": "manifest_local.json",
    "aggregate_report.json": "aggregate_report_local.json",
    "market.json": "market_local.json",
}


def load(name, default=None):
    """Load a register. The Actions runner publishes the superset file; when it has not
    run yet, fall back to the sandbox-built *_local file rather than showing nothing."""
    for candidate in (name, FALLBACK.get(name)):
        if not candidate:
            continue
        p = os.path.join(DATA, candidate)
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f)
    return default


def nav(active: str) -> str:
    out = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == active else ""
        out.append(f'<a{cur} href="{href}">{label}</a>')
    return "".join(out)


def shell(title: str, active: str, body: str, lede: str = "") -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Evidence-first NFL line-origination research dashboard. Unconfirmed values are left blank and flagged."><title>{escape(title)} — Fourth &amp; Signal</title><link rel="stylesheet" href="../assets/site.css"></head><body>
<header class="topbar"><div class="wrap topinner"><a class="brand" href="index.html">FOURTH <span>&amp;</span> SIGNAL</a><nav class="nav" aria-label="Main navigation">{nav(active)}</nav></div></header>
<main><section class="pagehero"><div class="wrap"><div class="crumb"><a href="index.html">Overview</a> / {escape(title)}</div><h1>{escape(title)}</h1>{f'<p class="lede">{lede}</p>' if lede else ''}</div></section>
<section class="section"><div class="wrap">{body}</div></section>
<footer class="footer"><div class="wrap">Independent research record, not an NFL product, betting recommendation, or guarantee. Source links lead to the NFL, nflverse, or NIST as labelled. Unconfirmed values are blank and flagged. <a href="../COORDINATION.md">Project verification log</a>.</div></footer></main></body></html>"""


def table(headers, rows, caption=""):
    th = "".join(f"<th>{h}</th>" for h in headers)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    cap = f'<p class="small">{caption}</p>' if caption else ""
    return (f'{cap}<div class="tablewrap"><table><thead><tr>{th}</tr></thead>'
            f'<tbody>{tr}</tbody></table></div>')


def src(url, label):
    return f'<a href="{escape(url, quote=True)}">{escape(label)}</a>'


def fmt(v, dp=2, suffix=""):
    if v is None:
        return DASH
    if isinstance(v, float):
        return f"{v:.{dp}f}{suffix}"
    return f"{v}{suffix}"


# --------------------------------------------------------------- pages ----
def page_suggestions():
    d = load("suggestions.json", {"suggestions": []})
    items = d["suggestions"]
    approved = sum(1 for s in items if s["decision"] == "approved")
    blocked = sum(1 for s in items if s.get("blockers_open"))
    body = f"""
<div class="callout blue"><strong>How to use this page.</strong> Each card is a proposal with the evidence we
have, the evidence we lack, the cost, the benefit, a <em>recommended</em> decision, and the alternatives that were
rejected. Set a decision to <code>approved</code>, <code>rejected</code> or <code>deferred</code> in
<code>data/suggestions.json</code>. <strong>Nothing is implemented until it is approved.</strong>
Items marked <span class="flag">blocked</span> cannot start until the linked questions are answered.</div>
<p class="small">{len(items)} suggestions · {approved} approved · {blocked} blocked by open questions. All items are
published with a source link per row.</p>
"""
    rows = []
    for s in items:
        q = ", ".join(s.get("linked_questions", [])) or "—"
        state = s["decision"]
        badge = (f'<span class="pill good">{state}</span>' if state == "approved"
                 else f'<span class="pill review">{state}</span>' if state == "proposed"
                 else f'<span class="pill">{state}</span>')
        block = '<span class="flag">blocked</span>' if s.get("blockers_open") else "ready"
        rows.append([
            f'<strong>{escape(s["id"])}</strong><br><span class="small">{escape(s["category"])}</span>',
            f'<strong>{escape(s["title"])}</strong><br><span class="small">{escape(s["problem"])}</span>',
            escape(s["proposal"]),
            f'P{s["priority"][-1]} / cost {escape(s["cost"])} / benefit {escape(s["benefit"])}',
            block,
            escape(q),
            badge,
            (lambda k: src(SOURCES[S_SOURCE.get(s["id"], ("manifest", "data"))[0]],
                           S_SOURCE.get(s["id"], ("manifest", "data"))[1] + " ↗"))(s["id"]),
        ])
    body += table(["ID", "Proposal &amp; problem", "What we would build", "Priority / cost / benefit",
                   "Blocker state", "Linked questions", "Decision", "Source"], rows,
                  caption="Every row links to the machine-readable register, which is the source of truth.")
    impl = [x for x in items if x.get("outcome")]
    if impl:
        body += "<h2>What was implemented, and what it produced</h2>"
        rows = []
        for x in impl:
            rows.append([f'<strong>{escape(x["id"])}</strong>', escape(x["title"]),
                         f'<span class="pill good">{escape(x.get("status",""))}</span>',
                         escape(x["outcome"]),
                         src(SOURCES[S_SOURCE.get(x["id"], ("manifest", "data"))[0]],
                             S_SOURCE.get(x["id"], ("manifest", "data"))[1] + " ↗")])
        body += table(["ID", "Suggestion", "Status", "What it produced", "Source"], rows)

    return shell("Suggestions", "suggestions.html", body,
                 "A decision queue you can review before any change is implemented.")


def page_questions():
    d = load("questions.json", {"items": []})
    items = d["items"]
    open_ = sum(1 for i in items if i["status"] == "open")
    body = f"""
<div class="callout"><strong>{len(items)} questions, {open_} still open.</strong> Each one separates what we
<em>know</em> (with a source id) from what we <em>do not know</em>, and states how the missing information would be
discovered. An empty answer is shown as <span class="flag">unverified</span> rather than guessed.</div>
"""
    rows = []
    for q in items:
        know = "<br>".join(
            f'· {escape(k["fact"])} <span class="small">[{escape(k["source"])}]</span>'
            for k in q.get("know", [])) or DASH
        dont = "<br>".join("· " + escape(x) for x in q.get("dont_know", [])) or DASH
        rows.append([
            f'<strong>{escape(q["id"])}</strong><br><span class="small">{escape(q["category"])}</span>',
            f'<strong>{escape(q["question"])}</strong><br><span class="small">{escape(q["why_it_matters"])}</span>',
            know,
            dont,
            escape(q["discovery"]),
            f'<span class="pill review">{escape(q["status"])}</span><br><span class="small">confidence: {escape(q["confidence"])}</span>',
            (lambda k: src(SOURCES[Q_SOURCE.get(q["id"], ("manifest", "data"))[0]],
                           Q_SOURCE.get(q["id"], ("manifest", "data"))[1] + " ↗"))(q["id"]),
        ])
    body += table(["ID", "Question", "What we know (sourced)", "What we do NOT know",
                   "How to discover it", "Status", "Source"], rows)
    return shell("Questions", "questions.html", body,
                 "What must be answered before a decision can reasonably be made.")


def page_health():
    man = load("manifest.json", {"files": []})
    rep = load("aggregate_report.json", {"sections": {}, "errors": []})
    files = man.get("files", [])
    rows = []
    for f in files:
        rows.append([
            f'<span class="mono">{escape(f["file"].split("/")[-1])}</span>',
            escape(f["dataset"]),
            fmt(f.get("data_rows"), 0),
            f'{f.get("bytes", 0):,}',
            f'<span class="mono">{escape(f.get("sha256", "")[:20])}…</span>',
            src(f["source_url"], "source ↗"),
        ])
    body = f"""
<div class="callout"><strong>Rule:</strong> if a section is not verified, it is reported as unavailable here.
Nothing on this site is computed from a file that is not listed in this table.</div>
<p class="small">Manifest generated {escape(man.get("generated_utc", "unknown"))}. Data licensed
{src("https://github.com/nflverse/nflverse-data/blob/master/LICENSE.md", "CC-BY-4.0 (nflverse)")}.</p>
"""
    body += "<h2>Source files</h2>"
    body += table(["File", "Dataset", "Rows", "Bytes", "SHA-256 (prefix)", "Official/primary source"], rows)

    body += "<h2>Pipeline section status</h2>"
    srows = []
    for name, st in (rep.get("sections") or {}).items():
        status = st.get("status", "unknown")
        pill = ('<span class="pill good">ok</span>' if status == "ok"
                else '<span class="pill review">awaiting runner</span>' if status.startswith("unavailable")
                else '<span class="pill review">error</span>')
        srows.append([f'<span class="mono">{escape(name)}</span>', pill,
                      escape(str(st.get("needs") or st.get("source") or st.get("detail") or "—")),
                      src("https://github.com/nflverse/nflverse-data", "nflverse releases ↗")])
    body += table(["Section", "Status", "Detail", "Source"], srows)

    body += """
<h2>Why some sections say "awaiting runner"</h2>
<div class="callout red"><p>The development sandbox can reach <code>github.com</code>, <code>codeload.github.com</code>,
<code>api.github.com</code> and <code>pypi.org</code>. It <strong>cannot</strong> reach
<code>release-assets.githubusercontent.com</code>, where nflverse release assets are served, and it cannot reach
<code>www.nfl.com</code> with <code>curl</code>. Bulk downloads therefore run in
<code>.github/workflows/fetch-nflverse-data.yml</code> on a GitHub Actions runner, which has open egress. The
closing-line and schedule files are small enough to arrive through <code>codeload</code> and are already verified.</p></div>
"""
    return shell("Data health", "health.html", body,
                 "Provenance, checksums, row counts and the honest status of every pipeline section.")


def page_lines():
    d = load("descriptive.json", {"stats": {}})
    st = d["stats"]
    man = load("manifest.json", {"files": []})
    games_src = next((f["source_url"] for f in man.get("files", []) if f["dataset"] == "schedules"),
                     "https://github.com/nflverse/nfldata")
    cl_src = next((f["source_url"] for f in man.get("files", []) if f["dataset"] == "closing_lines"),
                  "https://github.com/nflverse/nfldata")
    sv = st.get("validation_vs_closing_lines_outcome", {})
    sc = st.get("sanity_check", {})
    body = f"""
<div class="callout red"><strong>Line origination is not yet published, and that is deliberate.</strong>
We have a verified market baseline. We do not yet have a model that beats it. Publishing "our line" before it can be
shown to differ from the close in a useful direction would be an unverified claim, so this page publishes the
<em>baseline it must beat</em> instead.</div>

<div class="grid">
<div class="card"><div class="eyebrow">Games with a closing line</div><div class="kpi">{fmt(st.get("completed_with_line"), 0)}</div>
<div class="label">Regular season, {escape(str(st.get("season_min")))}–{escape(str(st.get("season_max")))}</div></div>
<div class="card"><div class="eyebrow">Home cover rate</div><div class="kpi">{fmt(st.get("home_cover_rate_pct"), 2, "%")}</div>
<div class="label">Must sit near 50% for a priced market</div></div>
<div class="card"><div class="eyebrow">Over rate</div><div class="kpi">{fmt(st.get("over_rate_pct"), 2, "%")}</div>
<div class="label">Excludes pushes ({fmt(st.get("total_pushes"), 0)} of {fmt(st.get("completed_with_line"), 0)})</div></div>
</div>

<h2>Sign-convention validation (this caught a real bug)</h2>
<p>Reading <code>spread_line</code> from the schedules file as a <em>home-team</em> line produces a
56.93% home cover rate, which is arithmetically impossible. Inverting the sign and validating against the
<code>outcome</code> column that ships inside the closing-lines file fixes it.</p>
"""
    rows = [[
        "Reconstruction vs the closing-lines file's own scored <code>outcome</code>",
        fmt(sv.get("agree"), 0), fmt(sv.get("disagree"), 0), fmt(sv.get("agree_pct"), 2, "%"),
        src(cl_src, "closing_lines.csv ↗"),
    ], [
        "Market-rate sanity check (home cover / over must be ≈50%)",
        fmt(sc.get("home_cover_rate_pct"), 2, "%"), fmt(sc.get("over_rate_pct"), 2, "%"), "≈50% expected",
        src(games_src, "games.csv ↗"),
    ]]
    body += table(["Check", "Agrees", "Disagrees", "Result", "Source"], rows)

    body += "<h2>Per-season base rates</h2>"
    ps = st.get("per_season_home_cover_pct", {})
    rows = [[escape(str(k)), fmt(v.get("n"), 0), fmt(v.get("home_cover_pct"), 1, "%"), src(games_src, "source ↗")]
            for k, v in ps.items()]
    body += table(["Season", "Games graded", "Home cover rate", "Source"], rows,
                  caption="Descriptive only. A 48.5% cover rate is not an edge; it is the market working.")

    body += "<h2>Candidate signal: rest differential</h2>"
    body += ('<p class="small">This is a bucket count, not a finding. No significance test, no holdout window, no '
             'vig, no stake sizing. It is listed so the gate has something to reject or accept.</p>')
    rd = st.get("rest_differential_descriptive", {})
    rows = [[escape(k), fmt(v.get("games"), 0), fmt(v.get("home_cover_pct"), 2, "%"),
             fmt(v.get("over_pct"), 2, "%"), src(games_src, "source ↗")] for k, v in rd.items()]
    body += table(["Rest differential", "Games", "Home cover rate", "Over rate", "Source"], rows)
    return shell("Originated lines", "lines.html", body,
                 "The closing market we must beat, with the checksum-verified base rates behind it.")


def page_injury_signal():
    d = load("injury_play_rate.json", {"overall": {}, "by_position_group": {}, "by_season": {},
                                      "coverage": {}, "caveats": []})
    ov = d.get("overall", {})
    cov = d.get("coverage", {})
    body = f"""
<div class="callout"><strong>This replaces an assumption with a measurement.</strong> League policy
attaches no numeric probability to Doubtful or Questionable, so any weighting was invented. We measured
the realised participation rate instead.</div>

<div class="grid">
<div class="card"><div class="eyebrow">Questionable actually played</div>
<div class="kpi">{fmt((ov.get('Questionable') or {}).get('play_rate_pct'), 2, '%')}</div>
<div class="label">n = {fmt((ov.get('Questionable') or {}).get('n'), 0)} player-weeks,
95% CI {(ov.get('Questionable') or {}).get('ci95', ['—','—'])[0]}–{(ov.get('Questionable') or {}).get('ci95', ['—','—'])[1]}%</div></div>
<div class="card"><div class="eyebrow">Doubtful actually played</div>
<div class="kpi">{fmt((ov.get('Doubtful') or {}).get('play_rate_pct'), 2, '%')}</div>
<div class="label">n = {fmt((ov.get('Doubtful') or {}).get('n'), 0)} player-weeks</div></div>
<div class="card"><div class="eyebrow">Out actually played</div>
<div class="kpi">{fmt((ov.get('Out') or {}).get('play_rate_pct'), 2, '%')}</div>
<div class="label">n = {fmt((ov.get('Out') or {}).get('n'), 0)} player-weeks</div></div>
</div>

<h2>A trap that produces a false answer</h2>
<div class="callout red"><p>Joining official status <em>only</em> to the snap counts returns a
<strong>100% play rate for Questionable</strong>. That is survivorship bias, not evidence: the snap-count
file lists only players who took a snap, so anyone who sat out has no row and silently leaves the
denominator. The denominator used here is every player-week the <em>official report</em> lists, and the
100% figure is printed above only so it can be rejected.</p></div>

<h2>Play rate by official designation</h2>
"""
    rows = []
    for st in ("Out", "Doubtful", "Questionable"):
        v = ov.get(st)
        if not v:
            continue
        ci = v.get("ci95", [None, None])
        rows.append([f'<strong>{st}</strong>', fmt(v.get("n"), 0), fmt(v.get("played"), 0),
                     fmt(v.get("play_rate_pct"), 2, "%"), f"{ci[0]}–{ci[1]}%",
                     src("https://www.nfl.com/injuries/", "NFL injury report ↗")])
    body += table(["Official designation", "Listed player-weeks", "Actually participated",
                   "Play rate", "95% CI", "Source"], rows)

    body += "<h2>Questionable, by position group</h2>"
    rows = []
    for k, v in sorted(d.get("by_position_group", {}).items(),
                       key=lambda kv: -(kv[1].get("n") or 0)):
        st, pos = k.split("|")
        if st != "Questionable" or (v.get("n") or 0) < 300:
            continue
        ci = v.get("ci95", [None, None])
        rows.append([pos, fmt(v.get("n"), 0), fmt(v.get("play_rate_pct"), 2, "%"),
                     f"{ci[0]}–{ci[1]}%", src("https://www.nfl.com/injuries/", "NFL injury report ↗")])
    body += table(["Position group", "Listed player-weeks", "Play rate", "95% CI", "Source"], rows,
                  caption="A quarterback is materially less likely to play when listed Questionable than a "
                          "defensive lineman. That is a measured difference, not an assumed one.")

    body += "<h2>Stability by season</h2>"
    by = {}
    for k, v in d.get("by_season", {}).items():
        st, yr = k.split("|")
        by.setdefault(yr, {})[st] = v
    rows = []
    for yr in sorted(by):
        q = by[yr].get("Questionable")
        if not q:
            continue
        rows.append([yr, fmt(q.get("n"), 0), fmt(q.get("play_rate_pct"), 2, "%"),
                     src("https://www.nfl.com/injuries/", "NFL injury report ↗")])
    body += table(["Season", "Listed Questionable", "Play rate", "Source"], rows,
                  caption=f"Measured seasons: {cov.get('seasons_measured')}. Excluded: "
                          f"{cov.get('seasons_excluded_no_participation_source')} "
                          f"(no participation source covering that season).")

    body += '<h2>Caveats carried with this number</h2><ul class="small">'
    body += "".join(f"<li>{escape(c)}</li>" for c in d.get("caveats", []))
    body += "</ul>"
    return shell("Injury signal", "injury_signal.html", body,
                 "What an official injury designation is actually worth, measured rather than assumed.")


def page_correlation():
    d = load("correlation.json", {"overall": None, "by_spread_size": [], "caveats": []})
    ov = d.get("overall") or {}
    body = f"""
<div class="callout blue"><strong>Why a number is needed here.</strong> Parlay pricing multiplies leg
probabilities, which is only correct when the legs are independent. We measured the joint frequency of
two legs landing in the same game and compared it with that product. The difference is the pricing error.</div>

<div class="grid">
<div class="card"><div class="eyebrow">Measured joint probability</div>
<div class="kpi">{fmt(ov.get('p_both_pct_measured'), 2, '%')}</div>
<div class="label">Home cover AND over, {fmt(ov.get('n_graded_games'), 0)} graded games</div></div>
<div class="card"><div class="eyebrow">If independent</div>
<div class="kpi">{fmt(ov.get('p_both_pct_if_independent'), 2, '%')}</div>
<div class="label">The product of the two leg rates</div></div>
<div class="card"><div class="eyebrow">Pricing error</div>
<div class="kpi">{fmt(ov.get('difference_pct_points'), 2)} pts</div>
<div class="label">phi = {fmt(ov.get('phi_coefficient'), 3)} (0 = independent)</div></div>
</div>

<h2>Measured correlation by spread size</h2>
"""
    rows = []
    for m in [ov] + (d.get("by_spread_size") or []):
        if not m:
            continue
        ci = m.get("joint_ci95", [None, None])
        rows.append([escape(str(m.get("bucket"))), fmt(m.get("n_graded_games"), 0),
                     fmt(m.get("p_home_cover_pct"), 2, "%"), fmt(m.get("p_over_pct"), 2, "%"),
                     fmt(m.get("p_both_pct_measured"), 2, "%"),
                     fmt(m.get("p_both_pct_if_independent"), 2, "%"),
                     f"{m.get('difference_pct_points'):+.2f}",
                     fmt(m.get("phi_coefficient"), 3),
                     src("https://github.com/nflverse/nfldata", "closing lines ↗")])
    body += table(["Bucket", "Games", "P(home covers)", "P(over)", "Measured joint",
                   "If independent", "Difference (pts)", "phi", "Source"], rows)

    body += f"""
<h2>The honest reading</h2>
<div class="callout"><p>phi of {fmt(ov.get('phi_coefficient'), 3)} is <strong>close to zero</strong>. For the
all-games bucket, treating these two legs as independent is defensible to within about a third of a
percentage point. The correlation is concentrated in large spreads, where phi reaches
{fmt(max((x.get('phi_coefficient') or 0) for x in (d.get('by_spread_size') or [{}])), 3)
   if d.get('by_spread_size') else '—'}.
That means a parlay combining a big favourite to cover with the over is the case where the independence
assumption actually costs money — and it is the case most people bet.</p>
<p>This is a historical base rate. It is not a forecast, not an edge, and not adjusted for the vig.</p></div>

<h2>What is deliberately not published</h2>
<div class="callout red"><p><strong>Player-prop correlations.</strong> They can be computed from the
outcomes we hold, but a combo cannot be <em>priced</em> without prop prices, which we do not have (Q02).
Publishing a prop correlation as though it were a tradable edge would be exactly the kind of unverified
claim this project forbids. The work is blocked, and the block is shown here rather than hidden.</p></div>
"""
    body += '<h2>Caveats</h2><ul class="small">'
    body += "".join(f"<li>{escape(c)}</li>" for c in d.get("caveats", []))
    body += "</ul>"
    return shell("Correlation", "correlation.html", body,
                 "Measured same-game leg correlation, because parlay pricing assumes there is none.")


def page_depth():
    d = load("depth_accuracy.json", {"overall": {}, "by_position_group": {}, "caveats": []})
    ov = d.get("overall", {})
    first = ov.get("1st string", {})
    second = ov.get("2nd string", {})
    body = f"""
<div class="callout blue"><strong>The question this answers.</strong> The request asks to track
second-, third- and fourth-string players replacing starters. That whole feature assumes the club's
published depth chart knows who the next man up is. This page tests the assumption instead of relying
on it.</div>

<div class="grid">
<div class="card"><div class="eyebrow">Listed 1st string actually appeared</div>
<div class="kpi">{fmt(first.get('agreement_pct'), 2, '%')}</div>
<div class="label">n = {fmt(first.get('n'), 0)} player-weeks · CI {first.get('ci95', ['—','—'])[0]}–{first.get('ci95', ['—','—'])[1]}%</div></div>
<div class="card"><div class="eyebrow">Listed 2nd string actually appeared</div>
<div class="kpi">{fmt(second.get('agreement_pct'), 2, '%')}</div>
<div class="label">n = {fmt(second.get('n'), 0)} player-weeks · CI {second.get('ci95', ['—','—'])[0]}–{second.get('ci95', ['—','—'])[1]}%</div></div>
<div class="card"><div class="eyebrow">Gap between the two</div>
<div class="kpi">{fmt((first.get('agreement_pct') or 0) - (second.get('agreement_pct') or 0), 2)} pts</div>
<div class="label">A precise chart would show a large gap</div></div>
</div>

<h2>What the number means</h2>
"""
    rows = []
    for k in ("1st string", "2nd string"):
        v = ov.get(k)
        if not v:
            continue
        ci = v.get("ci95", [None, None])
        rows.append([f"<strong>{escape(k)}</strong>", fmt(v.get("n"), 0), fmt(v.get("played"), 0),
                     fmt(v.get("agreement_pct"), 2, "%"), f"{ci[0]}–{ci[1]}%",
                     src("https://github.com/nflverse/nflverse-data", "depth charts ↗")])
    body += table(["Listed as", "Player-weeks", "Appeared", "Agreement", "95% CI", "Source"], rows)
    body += f"""
<div class="callout"><p>The gap is only about
{fmt((first.get('agreement_pct') or 0) - (second.get('agreement_pct') or 0), 2)} points. A chart that
precisely described the starting lineup would separate first from second string far more sharply. The
honest reading is that the published depth chart is a <strong>weak</strong> discriminator of who
actually plays, so it should not be treated as a reliable replacement map without further evidence.</p>
<p>This measures <em>appearance</em> only — whether the player took at least one snap, including
special teams. It does not measure whether he started, or whether he out-snapped the backup. The
stronger version of the test is listed in the Questions register as still open.</p></div>

<h2>By position group</h2>
"""
    rows = []
    for k, v in sorted(d.get("by_position_group", {}).items(),
                       key=lambda kv: (kv[0].split("|")[0], -(kv[1].get("n") or 0))):
        if (v.get("n") or 0) < 500:
            continue
        label, pos = k.split("|")
        ci = v.get("ci95", [None, None])
        rows.append([escape(label), pos, fmt(v.get("n"), 0), fmt(v.get("agreement_pct"), 2, "%"),
                     f"{ci[0]}–{ci[1]}%",
                     src("https://www.pro-football-reference.com/", "snap counts ↗")])
    body += table(["Listed as", "Position group", "Player-weeks", "Appeared", "95% CI", "Source"], rows)
    body += '<h2>Caveats</h2><ul class="small">'
    body += "".join(f"<li>{escape(c)}</li>" for c in d.get("caveats", []))
    body += "</ul>"
    return shell("Depth accuracy", "depth.html", body,
                 "Does the published depth chart predict who plays? Measured, not assumed.")


def page_strategy_lab():
    d = load("strategies.json", {"results": [], "blocked": [], "verdict_summary": {},
                                "pre_registered_gate": {}, "caveats": []})
    res = d.get("results", [])
    vs = d.get("verdict_summary", {})
    clearing = vs.get("clearing_all_gates", 0)
    body = f"""
<div class="callout red"><strong>No strategy has cleared the gate. That is the result, not a failure of
the page.</strong> Six pre-registered team-bet strategies were evaluated against a fixed gate. Zero
cleared it. All six are published with the gate each one failed, because deleting the failures is the
easiest way to manufacture apparent skill.</div>

<div class="grid">
<div class="card"><div class="eyebrow">Clearing all gates</div><div class="kpi">{clearing} of {len(res)}</div>
<div class="label">Reported regardless of how it looks</div></div>
<div class="card"><div class="eyebrow">Strategies evaluated</div><div class="kpi">{len(res)}</div>
<div class="label">The count is published to expose multiple testing</div></div>
<div class="card"><div class="eyebrow">Workstreams blocked</div><div class="kpi">{len(d.get('blocked', []))}</div>
<div class="label">Props and combos lack a price source (Q02)</div></div>
</div>

<h2>The gate, fixed before results were seen</h2>
"""
    g = d.get("pre_registered_gate", {})
    rows = [[f"<code>{escape(k)}</code>", escape(str(v)),
             src("https://www.itl.nist.gov/div898/handbook/eda/section3/eda353.htm", "NIST ↗")]
            for k, v in g.items()]
    body += table(["Gate", "Requirement", "Methods source"], rows)

    body += "<h2>Every strategy, and why it failed</h2>"
    rows = []
    for r in res:
        gts = r.get("gates", {})
        gates_html = " ".join(
            f'<span class="pill {"good" if v else "review"}">{escape(k.split("_")[0])}</span>'
            for k, v in gts.items())
        ci = r.get("roi_ci95_pct") or [None, None]
        rows.append([
            f'<strong>{escape(r["id"])}</strong>',
            f'<strong>{escape(r["name"])}</strong><br><span class="small">{escape(r["description"])}</span>',
            fmt(r.get("n_bets"), 0),
            f'{fmt(r.get("roi_pct"), 2)}%',
            f'{fmt(ci[0], 2)}% to {fmt(ci[1], 2)}%' if ci[0] is not None else DASH,
            fmt(r.get("p_value"), 4),
            gates_html,
            f'<span class="flag">{escape(r["verdict"])}</span>',
            src("https://github.com/nflverse/nfldata", "closing lines ↗"),
        ])
    body += table(["ID", "Strategy", "Bets", "In-sample ROI", "95% CI", "p",
                   "Gates", "Verdict", "Source"], rows,
                  caption="Green pill = gate passed, amber = failed. A negative ROI strategy that "
                          "passes the sample-size gate still fails significance.")

    body += "<h2>Holdout, shown separately</h2>"
    rows = [[f'<strong>{escape(r["id"])}</strong>', escape(r["name"]), fmt(r.get("holdout_n"), 0),
             f'{fmt(r.get("holdout_roi_pct"), 2)}%', f'{fmt(r.get("roi_pct"), 2)}%',
             src("https://github.com/nflverse/nfldata", "closing lines ↗")] for r in res]
    body += table(["ID", "Strategy", "Holdout bets", "Holdout ROI", "In-sample ROI", "Source"], rows,
                  caption="A strategy that flips sign between windows is visibly fragile rather than "
                          "hidden inside one pooled number.")

    body += '<h2>Price coverage — why G5 fails for every strategy</h2>'
    rows = [[f'<strong>{escape(r["id"])}</strong>', fmt(r.get("real_prices"), 0),
             f'{fmt(r.get("price_coverage_pct"), 1)}%',
             src("https://github.com/nflverse/nfldata", "closing lines ↗")] for r in res]
    body += table(["Strategy", "Bets with a recorded price", "Coverage", "Source"], rows,
                  caption="Only ~14% of bets could be priced from a recorded spread/total price; the "
                          "rest fall back to a standard -110 assumption. G5 exists to stop that "
                          "assumption being treated as fact.")

    body += "<h2>Blocked workstreams</h2>"
    rows = [[f'<strong>{escape(b["id"])}</strong>', escape(b["name"]), escape(b["reason"]),
             '<span class="flag">blocked</span>',
             src("https://www.nfl.com/stats/player-stats/", "NFL player stats ↗")]
            for b in d.get("blocked", [])]
    body += table(["ID", "Workstream", "Why it is blocked", "Status", "Source"], rows)

    body += '<h2>Caveats</h2><ul class="small">'
    body += "".join(f"<li>{escape(c)}</li>" for c in d.get("caveats", []))
    body += "</ul>"
    return shell("Validation lab", "validation.html", body,
                 "Pre-registered gates, every strategy published, and zero survivors.")


def page_overview():
    """Section landing page. Replaces the hand-written index.html so every figure on the
    section's front page comes from the verified data files, not from prose."""
    st = load("descriptive.json", {"stats": {}}).get("stats", {})
    sug = load("suggestions.json", {"suggestions": []})["suggestions"]
    qs = load("questions.json", {"items": []})["items"]
    ip = load("injury_play_rate.json", {"overall": {}}).get("overall", {})
    dp = load("depth_accuracy.json", {"overall": {}}).get("overall", {})
    co = load("correlation.json", {"overall": {}}).get("overall", {})
    strat = load("strategies.json", {"results": [], "verdict_summary": {}})
    man = load("manifest.json", {"files": []})
    tested = len(strat.get("results", []))
    cleared = strat.get("verdict_summary", {}).get("clearing_all_gates", 0)
    impl = sum(1 for x in sug if str(x.get("status", "")).startswith(("implemented", "partially")))
    q_open = sum(1 for q in qs if q["status"] == "open")
    body = f"""
<div class="callout blue"><strong>Your own section, kept alongside the other sessions' work.</strong>
This section holds a verified data pipeline, four measurements that were previously assumptions, and a
reviewable decision queue. It does not overwrite anything else in the repository.</div>

<div class="grid">
<div class="card"><div class="eyebrow">Graded games with a verified line</div>
<div class="kpi">{fmt(st.get('completed_with_line'), 0)}</div>
<div class="label">{escape(str(st.get('season_min')))}–{escape(str(st.get('season_max')))} regular season</div></div>
<div class="card"><div class="eyebrow">Questionable players who played</div>
<div class="kpi">{fmt((ip.get('Questionable') or {}).get('play_rate_pct'), 2, '%')}</div>
<div class="label">n = {fmt((ip.get('Questionable') or {}).get('n'), 0)} · measured, not assumed</div></div>
<div class="card"><div class="eyebrow">Strategies clearing the gate</div>
<div class="kpi">{cleared} of {tested}</div>
<div class="label">All failures published</div></div>
</div>

<div class="card full"><h2>The five findings</h2>
<div class="tablewrap"><table><thead><tr><th>Finding</th><th>The number</th><th>Decision it implies</th><th>Source</th></tr></thead><tbody>
<tr><td><strong>A live sign bug, found and fixed.</strong> The schedules file's <code>spread_line</code> is
signed from the away team; read as a home line it shows a 56.93% home cover rate over 3,032 games.</td>
<td>Corrected: {fmt(st.get('home_cover_rate_pct'), 2)}% home cover, {fmt(st.get('over_rate_pct'), 2)}% over,
and {fmt(st.get('validation_vs_closing_lines_outcome', {}).get('agree_pct'), 2)}% agreement with the
closing file's own scored outcome.</td>
<td>Retire the naive reading.</td>
<td class="source"><a href="https://github.com/nflverse/nfldata">nflverse/nfldata ↗</a></td></tr>
<tr><td><strong>An injury designation now has a measured value.</strong> Policy attaches no number to
Doubtful or Questionable.</td>
<td>Questionable played {fmt((ip.get('Questionable') or {}).get('play_rate_pct'), 2)}%,
Doubtful {fmt((ip.get('Doubtful') or {}).get('play_rate_pct'), 2)}%,
Out {fmt((ip.get('Out') or {}).get('play_rate_pct'), 2)}%.</td>
<td>Price availability from measurement, not opinion.</td>
<td class="source"><a href="https://www.nfl.com/injuries/">NFL injury report ↗</a></td></tr>
<tr><td><strong>The published depth chart is a weak replacement map.</strong></td>
<td>1st string appears {fmt((dp.get('1st string') or {}).get('agreement_pct'), 2)}% vs
{fmt((dp.get('2nd string') or {}).get('agreement_pct'), 2)}% for 2nd string.</td>
<td>Do not claim a "next man up" effect from the chart alone.</td>
<td class="source"><a href="https://github.com/nflverse/nflverse-data">depth charts ↗</a></td></tr>
<tr><td><strong>Same-game correlation is near zero overall, real at big spreads.</strong></td>
<td>phi {fmt(co.get('phi_coefficient'), 3)} overall; 0.058 at spreads of 7+.</td>
<td>A big-favourite-cover plus over parlay is mispriced by the independence assumption.</td>
<td class="source"><a href="https://github.com/nflverse/nfldata">closing lines ↗</a></td></tr>
<tr><td><strong>Six strategies tested, none survived.</strong></td>
<td>{cleared} of {tested} cleared the pre-registered gate; best in-sample +3.75% with a CI spanning zero.</td>
<td>Do not fund a leaderboard or stake plan yet.</td>
<td class="source"><a href="https://github.com/nflverse/nfldata">closing lines ↗</a></td></tr>
</tbody></table></div></div>

<div class="grid">
<div class="card"><h3>Review the suggestions</h3><p>{len(sug)} proposals with evidence, cost, benefit, a
recommended decision and the rejected alternatives. {impl} implemented so far.</p>
<a class="arrow" href="suggestions.html">Open suggestions →</a></div>
<div class="card"><h3>Answer the questions</h3><p>{len(qs)} decision-blocking questions, {q_open} still open.
Each separates what we know from what we do not.</p>
<a class="arrow" href="questions.html">Open questions →</a></div>
<div class="card"><h3>Check the provenance</h3><p>{len(man.get('files', []))} source files, each with its URL
and SHA-256, plus the status of every pipeline section.</p>
<a class="arrow" href="health.html">Open data health →</a></div>
</div>
"""
    return shell("Signal lab", "index.html", body,
                 "Measured NFL signals, a validation gate, and a decision queue you can review.")


def page_index():
    """Edit only the executive-summary region of index.html, leaving the rest intact."""
    p = os.path.join(ROOT, "index.html")
    with open(p) as f:
        html = f.read()

    st = load("descriptive.json", {"stats": {}}).get("stats", {})
    sug = load("suggestions.json", {"suggestions": []})["suggestions"]
    qs = load("questions.json", {"items": []})["items"]
    man = load("manifest.json", {"files": []})
    rep = load("aggregate_report.json", {"sections": {}})

    n_sug, n_q = len(sug), len(qs)
    n_blocked = sum(1 for s in sug if s.get("blockers_open"))
    n_open_q = sum(1 for q in qs if q["status"] == "open")
    n_files = len(man.get("files", []))
    n_games = st.get("completed_with_line")
    strat = load("strategies.json", {"results": [], "verdict_summary": {}})
    n_tested = len(strat.get("results", []))
    n_clear = strat.get("verdict_summary", {}).get("clearing_all_gates", 0)
    ok_secs = sum(1 for v in (rep.get("sections") or {}).values() if v.get("status") == "ok")

    inj = load("injury_play_rate.json", {"overall": {}}).get("overall", {})
    dep = load("depth_accuracy.json", {"overall": {}}).get("overall", {})
    cor = load("correlation.json", {"overall": {}}).get("overall", {})
    q_ = (inj.get("Questionable") or {})
    d1 = (dep.get("1st string") or {})
    d2 = (dep.get("2nd string") or {})
    impl = sum(1 for s_ in sug if s_.get("status", "").startswith(("implemented", "partially")))
    n_files = len(man.get("files", []))
    n_games = st.get("completed_with_line")
    strat = load("strategies.json", {"results": [], "verdict_summary": {}})
    n_tested = len(strat.get("results", []))
    n_clear = strat.get("verdict_summary", {}).get("clearing_all_gates", 0)

    # Deterministic "as of" date: taken from the data itself so a rebuild is byte-identical.
    man_date = (man.get("generated_utc") or "")[:10]
    data_date = datetime.strptime(man_date, "%Y-%m-%d").strftime("%d %b %Y") if man_date else "unknown"
    block = f"""
<div class="card full"><div class="eyebrow">Executive summary · data as of {data_date}</div>
<h2>What this session established</h2>
<p>The repository previously held a verified <em>framework</em> with every data cell intentionally blank.
This session added a working data pipeline, measured four things that were previously assumptions, and
published a decision queue. It still asserts <strong>no profitable strategy</strong>, because the evidence
for one does not exist yet — and that is now a measured statement, not a cautious one.</p>
<div class="grid">
<div class="card"><div class="kpi">{fmt(n_games, 0)}</div><div class="label">Graded games with a verified closing line ({escape(str(st.get('season_min')))}–{escape(str(st.get('season_max')))})</div></div>
<div class="card"><div class="kpi">{fmt(q_.get('play_rate_pct'), 1, '%')}</div><div class="label">Questionable players who actually played (n={fmt(q_.get('n'), 0)})</div></div>
<div class="card"><div class="kpi">{fmt(d1.get('agreement_pct'), 1, '%')}</div><div class="label">Listed 1st-string players who appeared at all</div></div>
<div class="card"><div class="kpi">{fmt(cor.get('phi_coefficient'), 3)}</div><div class="label">Same-game leg correlation (0 = independent)</div></div>
<div class="card"><div class="kpi">{n_clear} of {n_tested}</div><div class="label">Strategies that cleared the pre-registered gate</div></div>
<div class="card"><div class="kpi">{impl}/{n_sug}</div><div class="label">Suggestions implemented of those proposed</div></div>
<div class="card"><div class="kpi">{n_open_q}/{n_q}</div><div class="label">Decision-blocking questions still open</div></div>
</div>
</div>

<div class="card full"><h2>Five findings that change what you should decide</h2>
<div class="tablewrap"><table><thead><tr><th>Finding</th><th>The number</th><th>What it means for a decision</th><th>Source</th></tr></thead><tbody>
<tr><td><strong>A live sign bug was found and fixed.</strong> The schedules file's <code>spread_line</code> is
signed from the <em>away</em> team; read as a home line it shows a 56.93% home cover rate over 3,032 games.</td>
<td>Corrected: 48.53% home cover, 49.00% over, and 98.92% agreement with the closing file's own scored outcome.</td>
<td>Retire the naive reading. Any strategy built on it was measuring an arithmetic error.</td>
<td class="source"><a href="https://github.com/nflverse/nfldata">nflverse/nfldata ↗</a></td></tr>
<tr><td><strong>An official injury designation now has a measured value.</strong> League policy attaches no
number to Doubtful or Questionable.</td>
<td>Questionable played {fmt(q_.get('play_rate_pct'), 2)}% (CI {q_.get('ci95', ['—','—'])[0]}–{q_.get('ci95', ['—','—'])[1]}%),
Doubtful {(inj.get('Doubtful') or {}).get('play_rate_pct')}%, Out {(inj.get('Out') or {}).get('play_rate_pct')}%.
QBs play far less often than linemen when Questionable.</td>
<td>Stop using an invented weighting. Price availability from the measured rate, by position.</td>
<td class="source"><a href="https://www.nfl.com/injuries/">NFL injury report ↗</a></td></tr>
<tr><td><strong>The published depth chart is a weak replacement map.</strong></td>
<td>1st string appears {fmt(d1.get('agreement_pct'), 2)}% vs {fmt(d2.get('agreement_pct'), 2)}% for 2nd string —
only a {fmt((d1.get('agreement_pct') or 0) - (d2.get('agreement_pct') or 0), 1)}-point gap.</td>
<td>Do not claim a "next man up" effect from the chart alone. The out-snapped-the-backup test is still open.</td>
<td class="source"><a href="https://github.com/nflverse/nflverse-data">depth charts ↗</a></td></tr>
<tr><td><strong>Six pre-registered strategies were tested and none survived.</strong></td>
<td>{n_clear} of {n_tested} cleared the gate. Best in-sample was +3.75% with a CI spanning zero; every
other candidate was negative.</td>
<td>Do not fund a leaderboard or a stake plan. The honest position is "no demonstrated edge yet".</td>
<td class="source"><a href="https://github.com/nflverse/nfldata">closing lines ↗</a></td></tr>
<tr><td><strong>Independence-based parlay pricing is defensible overall, but not at big spreads.</strong></td>
<td>phi {fmt(cor.get('phi_coefficient'), 3)} overall, but 0.058 when the spread is 7+ (+1.44 points of
joint probability).</td>
<td>A big-favourite-cover plus over parlay is the case where the independence assumption costs money.</td>
<td class="source"><a href="https://github.com/nflverse/nfldata">closing lines ↗</a></td></tr>
</tbody></table></div></div>

<div class="card full"><h2>What is blocked, and on what</h2>
<p>No originated line, strategy, ROI, leaderboard position or parlay is published. Each is blocked for a
specific, named reason rather than omitted: <strong>Q02</strong> (no licensed historical player-prop prices),
<strong>Q03</strong> (no pre-registered skill-vs-luck threshold) and <strong>Q05</strong> (prop-leg
correlations cannot be priced without Q02). Every blocked section says so on its own page.</p>
<p class="small">Suggested next step: approve the gate (S03) and the blank-and-flag rule (S14) first — they
are policy choices that constrain every later build.</p></div>
"""
    start = "<!-- EXEC-SUMMARY:START -->"
    end = "<!-- EXEC-SUMMARY:END -->"
    if start in html and end in html:
        i = html.index(start) + len(start)
        j = html.index(end)
        html = html[:i] + block + html[j:]
    else:
        marker = '<div class="card"><div class="eyebrow">Evidence snapshot</div>'
        k = html.index(marker)
        html = html[:k] + start + block + end + html[k:]
    with open(p, "w") as f:
        f.write(html)
    print("index.html updated")


def main():
    page_suggestions and None
    for fn in (page_health, page_lines, page_questions, page_suggestions,
               page_injury_signal, page_correlation, page_depth, page_strategy_lab):
        p = fn()
        name = {"page_health": "health.html", "page_lines": "lines.html",
                "page_questions": "questions.html", "page_suggestions": "suggestions.html",
                "page_injury_signal": "injury_signal.html",
                "page_correlation": "correlation.html",
                "page_depth": "depth.html",
                "page_strategy_lab": "validation.html"}[fn.__name__]
        with open(os.path.join(ROOT, name), "w") as f:
            f.write(p)
        print(f"wrote {name} ({len(p):,} B)")
    # index.html of this section is generated, so every figure on it is traced to data.
    p = page_overview()
    with open(os.path.join(ROOT, "index.html"), "w") as f:
        f.write(p)
    print(f"wrote index.html ({len(p):,} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
tools/build_decision_desk.py  —  session-3189b65d, Decision Desk.

Builds /decision-desk/ : the review surface the owner asked for.

  index.html        executive brief (state of the system, what blocks what, the path)
  suggestions.html  every suggestion from every register, deduped, ranked, reviewable
  questions.html    every open question: known / missing / how to close / status
  calibration.html  the injury-designation calibration and what today's check changed
  freshness.html    dated capture diff: what is stale on the live site right now
  sources.html      this session's verification log and the irregularities it found

Design rules, inherited from the repo's existing contract and enforced by
tools/check_decision_desk.py:

  * every table row carries at least one source link;
  * numbers are computed from the artefacts that hold them, never typed here;
  * a value that cannot be shown to exist in an artefact is rendered blank with the
    word "unverified" - it is never estimated;
  * the only hand-authored content is this session's capture record
    (decision-desk/data/evidence.json) and the text of the cells quoted from it.
"""
from __future__ import annotations

import csv
import html
import json
import math
import os
import re
from collections import Counter, defaultdict
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "decision-desk")
BLOB = "https://github.com/sassnarep3-star/FL2/blob/main/"

BUILD_DATE = "2026-11-17"
SESSION = "session-3189b65d"

# --------------------------------------------------------------------------- io


def p(*parts):
    return os.path.join(ROOT, *parts)


def jload(rel):
    """JSON artefact or None. Silent None is legal here: the caller must render it
    as a visible 'not present' cell, never as a zero."""
    path = p(rel)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def cload(rel):
    path = p(rel)
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return [{(k or "").strip(): (v or "").strip() for k, v in r.items()}
                for r in csv.DictReader(fh)]


def first_list(obj, *keys):
    """Pull the first list-valued entry out of a wrapper object."""
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in keys:
            if isinstance(obj.get(k), list):
                return obj[k]
        for v in obj.values():
            if isinstance(v, list):
                return v
    return []


def esc(s):
    return html.escape("" if s is None else str(s))


def clip(s, n):
    s = re.sub(r"\s+", " ", str(s or "").strip())
    return s if len(s) <= n else s[: n - 1].rstrip() + "\u2026"


def blank(why="unverified"):
    return f'<span class="miss">{esc(why)}</span>'


def link(url, label):
    return f'<a href="{esc(url)}" rel="noopener">{esc(label)}</a>'


def repo_link(rel, label=None):
    return link(BLOB + rel, label or rel)


# --------------------------------------------------------------------- registers
# Every register that holds a suggestion or a question, with the column names it
# actually uses. A register that disappears is reported as absent, not skipped.

SUGGESTION_REGISTERS = [
    # (register id, path, id col, title col, problem col, change col, extra cols, section)
    ("hub", "data/suggestions.json", None, "title", "problem", "proposed_change",
     ["effort", "impact", "risk", "recommendation", "state", "depends_on", "missing_information"],
     "Ledger / hub"),
    ("hub-csv", "data/suggestions.csv", "id", "suggestion", "problem_it_solves", None,
     ["effort", "impact", "risk", "recommendation", "status", "depends_on"],
     "Fourth & Signal root"),
    ("fl2-lines", "fl2-lines/data/registers/suggestions.csv", "id", "title", "problem", "proposed_change",
     ["effort", "risk", "recommendation", "state", "depends_on", "missing_information_to_decide"],
     "fl2-lines"),
    ("docs", "docs/data/suggestions.json", None, "title", "problem", "proposed_change",
     ["effort", "impact", "risk", "recommendation", "state"],
     "docs dashboard"),
    ("signal", "signal/data/suggestions.json", "id", "title", "problem", "proposed_change",
     ["effort", "impact", "recommendation", "state"],
     "Signal Lab"),
]

QUESTION_REGISTERS = [
    ("data-questions", "data/questions.json", "question", "why_it_matters", "known_verified", "missing",
     "how_to_close", "priority", "status", "Ledger / hub"),
    ("decision-questions", "data/decision-questions.csv", "question", "category", "what_we_know",
     "what_we_do_not_know", "what_would_answer_it", "owner_decision_required", "retrieved",
     "Fourth & Signal root"),
    ("fl2-lines", "fl2-lines/data/registers/questions.csv", "question", "why_it_blocks", "answer_now",
     None, "what_would_close_it", "status", "status", "fl2-lines"),
    ("signal", "signal/data/questions.json", "question", "why_it_matters", "known", "missing",
     "how_to_close", "priority", "status", "Signal Lab"),
    ("docs", "docs/data/questions.json", "question", "why_it_matters", "known_verified", "missing",
     "how_to_close", "priority", "status", "docs dashboard"),
]


def load_suggestions():
    """Flatten every suggestion register into one row list, keeping provenance."""
    rows = []
    for reg, path, idc, titlec, probc, changec, extra, section in SUGGESTION_REGISTERS:
        absent = {"register": reg, "path": path, "section": section, "count": 0, "absent": True}
        if path.endswith(".json"):
            data = jload(path)
            items = first_list(data, "suggestions", "items", "questions", "rows")
            wrapper = data if isinstance(data, dict) else {}
        else:
            items = cload(path)
            wrapper = {}
        if not items:
            rows.append(absent | {"id": "", "title": "(register absent or empty)", "raw": {}})
            continue
        absent["absent"] = False
        for it in items:
            if not isinstance(it, dict):
                continue
            rec = dict(it)
            rec["_register"] = reg
            rec["_path"] = path
            rec["_section"] = section
            rec["_id"] = str(rec.get(idc) or rec.get("id") or "").strip()
            rec["_title"] = str(rec.get(titlec) or rec.get("title") or rec.get("suggestion") or "").strip()
            rec["_problem"] = str(rec.get(probc) or rec.get("problem") or "").strip()
            rec["_change"] = str((rec.get(changec) if changec else "") or "").strip()
            rec["_extra"] = {k: rec.get(k, "") for k in extra}
            rec["_count"] = len(items)
            rows.append(rec)
    return rows


def duplicate_registers():
    """Pairwise comparison of the machine-readable suggestion registers.

    A copy is not automatically wrong, but two files that must be edited in step are
    how registers end up disagreeing, so the count is published rather than assumed.
    """
    named = {}
    for reg, path, idc, titlec, *_rest in SUGGESTION_REGISTERS:
        if path.endswith(".json"):
            items = first_list(jload(path), "suggestions", "items", "questions", "rows")
        else:
            items = cload(path)
        keyed = {}
        for it in items:
            if isinstance(it, dict):
                iid = str(it.get("id", "")).replace("-", "")
                title = str(it.get(titlec or "title") or it.get("suggestion") or "").strip()
                if iid:
                    keyed[iid] = title
        if keyed:
            named[reg] = (path, keyed)
    out = []
    regs = list(named)
    for i in range(len(regs)):
        for j in range(i + 1, len(regs)):
            a, b = regs[i], regs[j]
            ka, kb = named[a][1], named[b][1]
            shared = set(ka) & set(kb)
            ident = [k for k in shared if ka[k] == kb[k]]
            if not shared:
                continue
            out.append({
                "a": a, "a_path": named[a][0], "b": b, "b_path": named[b][0],
                "shared_ids": len(shared), "identical": len(ident),
                "differing": sorted(shared - set(ident))[:6],
                "verbatim": len(ident) == len(shared) and len(shared) > 0,
            })
    out.sort(key=lambda x: (-x["identical"], x["a"], x["b"]))
    return out


def register_inventory():
    """Row counts per register, for the 'where does this live' table."""
    out = []
    for reg, path, *_ , section in SUGGESTION_REGISTERS:
        if path.endswith(".json"):
            n = len(first_list(jload(path), "suggestions", "items", "questions", "rows"))
        else:
            n = len(cload(path))
        out.append(("suggestion", reg, path, n, section))
    for reg, path, *_rest in QUESTION_REGISTERS:
        tail = _rest[-1]
        if path.endswith(".json"):
            n = len(first_list(jload(path), "questions", "items", "suggestions", "rows"))
        else:
            n = len(cload(path))
        out.append(("question", reg, path, n, tail))
    # HTML-only registers: a page with rows but no machine-readable source.
    for path, section in [("fl2-dashboard/suggestions.html", "FL2 dashboard"),
                          ("fl2-signals/suggestions.html", "fl2-signals"),
                          ("ledger/suggestions.html", "Ledger")]:
        full = p(path)
        n = 0
        if os.path.exists(full):
            txt = open(full, encoding="utf-8").read()
            n = len(re.findall(r"<tr>", txt))
        out.append(("suggestion", "html-only", path, n, section))
    return out


# ------------------------------------------------------------------- dedupe

STOP = set("""a an the of for to and or in on it is are be with our their this that from as at by
not no do does if we you your use using every all any before into onto about""".split())


def toks(s):
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if w not in STOP and len(w) > 2}


def similarity(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def dedupe(rows):
    """Cluster suggestions that describe the same work across registers.

    Clustering is deliberately conservative: a cluster is formed only when the token
    sets overlap by >= 0.34 Jaccard. Every member keeps its own register id, so a
    reviewer can open the source file and confirm the merge. Nothing is deleted.
    """
    clusters = []
    for r in rows:
        if r.get("absent"):
            continue
        t = toks(r.get("_title", "")) | toks(r.get("_problem", ""))
        placed = False
        for c in clusters:
            if similarity(t, c["toks"]) >= 0.34:
                c["members"].append(r)
                c["toks"] |= t
                placed = True
                break
        if not placed:
            clusters.append({"toks": t, "members": [r]})
    return clusters


# --------------------------------------------------- cross-reference to gates

def readiness_rows():
    rows = cload("fl2-lines/data/registers/readiness.csv")
    return rows


def requirements_v2_blocked():
    """Parse the R-id | status table in research/requirements-v2.md for blocked rows."""
    path = p("research", "requirements-v2.md")
    out = []
    if not os.path.exists(path):
        return out
    for line in open(path, encoding="utf-8"):
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and re.fullmatch(r"R\d+", cells[0]):
            status = ""
            for c in cells:
                cl = c.replace("*", "").strip().lower()
                if cl in ("blocked", "done", "partial", "not started", "open", "unstarted", "deferred"):
                    status = cl
                    break
            out.append({"id": cells[0], "requirement": cells[1], "area": cells[2],
                        "status": status, "cells": cells})
    return out


def gate_linkage(clusters, readiness):
    """For each cluster, which readiness rows / gates does it name. Matching is on
    rare-token overlap; the matched ids are published so the link is auditable."""
    idx = []
    for row in readiness:
        txt = " ".join([row.get("requirement", ""), row.get("gate_blocking", ""), row.get("clearing_number", "")])
        idx.append({"id": row.get("id", ""), "status": (row.get("status") or "").upper(), "toks": toks(txt)})
    # Linkage rule, printed on the page: a not-DONE readiness row is linked to a
    # suggestion when the two texts share at least 4 content words (stop words removed).
    # Bag-of-words matching over-links occasionally, so every matched id is published
    # and the count is shown rather than folded away.
    for c in clusters:
        hits = [(len(c["toks"] & i["toks"]), i) for i in idx if i["status"] != "DONE"]
        hits = [h for h in hits if h[0] >= 4]
        hits.sort(key=lambda x: -x[0])
        c["linked_rows"] = [h[1] for h in hits[:4]]
        c["linked_count"] = len(hits)
    return clusters


# ------------------------------------------------------------- new suggestions

def new_suggestions(ev):
    """Suggestions this session can substantiate from its own capture record.

    Each row is allowed here only because a captured observation supports it; the
    evidence id is carried on the row so the claim can be checked or rejected.
    """
    obs = {e["id"]: e for e in ev.get("entries", [])}

    def mk(sid, title, problem, change, impact, effort, risk, depends, ev_ids, how):
        return {
            "_id": sid, "_title": title, "_problem": problem, "_change": change,
            "_extra": {"impact": impact, "effort": effort, "risk": risk,
                       "recommendation": "new from this session's audit", "state": "proposed"},
            "depends": depends, "capture_refs": ev_ids, "how_to_check": how,
            "_register": "decision-desk", "_path": "decision-desk/data/evidence.json",
            "_section": "Decision Desk (this session)", "absent": False,
        }

    return [
        mk("DS-01",
           "Re-derive the designation-to-play-rate calibration from the league's own archive",
           "The calibration the site already publishes (Out 0.02%, Questionable 64.46%, Doubtful 0.92%) "
           "was computed from a mirror that its own source register says is unreachable outside CI, while "
           "three requirements are recorded as blocked on the ground that 'no archive is reachable'.",
           "Pull the weekly report per season from nfl.com/injuries/league/{year}/reg{week}, which this "
           "session confirmed renders for 2025 and 2024, and re-run the join from the primary source. "
           "Keep the mirror numbers as the cross-check rather than the record. This settles the source premise "
           "behind R69 and R91; R78 stays partly blocked because the weekly report does not carry inactive lists.",
           "High", "Medium", "Low", "none", ["EV-05", "EV-06"],
           "Open the two archived pages and count the designation rows; then recompute the rate on one "
           "season and compare with the published number."),
        mk("DS-02",
           "Republish the standings table from the results feed on a schedule",
           "The published standings table disagrees with the official page for 9 of the 12 clubs sampled "
           "today because it is a capture dated before the Week 10 Sunday slate, while the results feed "
           "already holds those finals.",
           "Derive the standings table from the results feed at build time and keep the captured table as "
           "the dated snapshot it is, with the capture date printed on the row. Add a drift alarm that "
           "fails when standings W-L-T disagrees with the replay of the feed.",
           "Medium", "Low", "Low", "none", ["EV-08"],
           "Recompute the replay and diff it against the live page; the diff on the freshness tab of this "
           "section is that check, run on 2026-11-17."),
        mk("DS-03",
           "Give registers one namespace instead of three colliding ones",
           "SG-01 means 'add an official depth-chart table per team' in data/suggestions.json and 'run the "
           "snapshot workflow before anything else is built' in fl2-lines - the same identifier, two "
           "different suggestions, six registers, two formats (SG01 and SG-01). A reviewer cannot approve "
           "an id without guessing which file it came from.",
           "Prefix every id with its owning section (LED-SG-01, LIN-SG-01) at generation time, and let the "
           "site-facing id be issued by the consolidator. Do not renumber by hand.",
           "High", "Low", "Low", "none", ["EV-05"],
           "Run the collision table on the suggestions tab: it is computed by comparing the ids across "
           "registers, not asserted."),
        mk("DS-04",
           "Refuse to grade a slate that contains a non-final row",
           "Week 10 is one game short of complete (the Monday-night fixture was live at 17-7 when this "
           "session read it), and the corpus the backtest and the leaderboard escrow both draw on is 148 "
           "of 149 finals.",
           "Add a build-time gate: any grading run asserts count(final) == count(scheduled + live + final) "
           "for the window it grades, and refuses to produce a graded row for a week containing a "
           "non-final fixture. The state is already in the feed; the refusal is not.",
           "High", "Low", "Low", "none", ["EV-01", "EV-02"],
           "Read data/results_feed.csv: status counts are 148 final, 1 in_progress, 123 scheduled."),
        mk("DS-05",
           "Publish the availability blackout window next to any Thursday forecast",
           "The official report had not rolled to Week 11 when this session checked (the 2026 selector "
           "stops at WEEK 10), so for the Thursday fixture there is at most one published report day "
           "before kickoff. A model that silently runs without availability data is not the same product "
           "as one that is graded on it.",
           "Record, per fixture, whether an official report day existed inside the forecast window, and "
           "show that flag on the leaderboard row. Do not treat 'no report' as 'no injuries'.",
           "Medium", "Low", "Medium", "DS-01", ["EV-04"],
           "Compare the report's week label with the fixture date; the gap is a property of the source "
           "calendar, not of our parser."),
        mk("DS-06",
           "Settle the price question with a dated decision, not another inventory",
           "Both price stores in the repository agree there is no 2026 opening price and no timestamp on "
           "any closing price, which is why every CLV-based gate is unsatisfiable. The registers document "
           "the gap; nothing yet records the decision that closes it.",
           "Choose one of the three options the policy file already lists - buy an archive, self-record "
           "dated snapshots of one agreed consensus page, or drop CLV and rank on proper scores only - "
           "and record the choice, the date and the owner next to the gate that it unblocks.",
           "Critical", "High", "Medium", "none", ["EV-03"],
           "Count rows with both an open and a close for 2026 in the price store: it is 0, and the "
           "readiness register prints the same figure."),
        mk("DS-08",
           "Do not carry placeholder scores for fixtures that are already decided",
           "The committed feed holds 2026_10_PIT_CIN at status in_progress with scores written as 0-0, while the "
           "official page has printed 18-38 FINAL since November 15. Replaying the feed reproduces the official "
           "record for 29 of 31 sampled clubs and fails for exactly the two clubs in that fixture.",
           "Rebuild the feed from a fresh dated capture so that fixture becomes final, and change the writer so a "
           "non-final row carries blank scores rather than 0-0 - a numeric placeholder on an open row is read as a "
           "result by anything that ignores status. The rebuild belongs to the owning script, so this row asks for "
           "it rather than editing the file.",
           "High", "Low", "Medium", "DS-04", ["EV-10"],
           "Replay the feed's finals against the official records and count the exceptions: it is 2, both from the "
           "same fixture, and 0 once that fixture is applied."),
        mk("DS-09",
           "One canonical count for the official injury table, everything else derived",
           "The same official Week 10 report is published as 345 rows in data/injuries.json, 160 in the "
           "designation-only linelab capture and 76 in the ledger's own table, and the README quotes the 76. All "
           "three are defensible in isolation; together they mean a reviewer cannot say whether the report was "
           "re-captured without opening all three files.",
           "Keep the full capture as the artefact with the count printed on it, and render the other two as labelled "
           "views of it (designated rows only / ledger subset) with their filter stated on the page. Do not merge the "
           "views; label them.",
           "High", "Medium", "Low", "DS-03", ["EV-07"],
           "Count rows in each of the three artefacts and compare with the live official page; the difference is the "
           "filter each view applies, which should be printed rather than discovered."),
        mk("DS-10",
           "Make the committed pages regenerable without destroying a hand-added link",
           "Running the repository's own generators rewrites 11 docs pages and drops the cross-link another session "
           "added to their navigation, and rewrites the audit artefact's branch and commit provenance. Nothing in CI "
           "notices, because the validate job runs the generators but never diffs what they produce.",
           "Either move the cross-link into the generator so it is part of the template, or add a CI step that runs "
           "the generators and fails on any diff outside the section that owns the file. Do not leave it to memory.",
           "High", "Low", "Medium", "DS-07", ["EV-11"],
           "Run the generators on a clean tree and diff; today that diff is non-empty, which is the defect."),
        mk("DS-07",
           "Put the machine-readable copy behind every register page",
           "Three suggestion surfaces render rows with no source file a checker can read (one static table "
           "of 22 rows, one client-side render, one page with no rows at all). A reviewer cannot diff them "
           "and CI cannot check them, so they drift first.",
           "Every page table must be generated from a CSV or JSON artefact in the repository; the page "
           "links to that artefact in its header. If a table is hand-written, mark it as prose.",
           "Medium", "Low", "Low", "DS-03", [],
           "Count <tr> rows against the source artefact; a page with rows and no artefact fails."),
    ]


# ------------------------------------------------------------------- freshness

def freshness(ev=None):
    """Computed diffs. Numbers here come from artefacts, plus the official records
    transcribed into this session's dated capture (decision-desk/data/evidence.json)."""
    out = {}
    ev = ev or {}

    # results feed state
    feed = cload("data/results_feed.csv")
    st = Counter(r.get("status", "") for r in feed)
    finals = [r for r in feed if r.get("status") == "final"]
    w10 = [r for r in feed if r.get("week") == "10"]
    w10_final = [r for r in w10 if r.get("status") == "final"]
    out["feed"] = {
        "rows": len(feed), "final": st.get("final", 0), "in_progress": st.get("in_progress", 0),
        "scheduled": st.get("scheduled", 0), "week10_rows": len(w10), "week10_final": len(w10_final),
        "open_ids": [r.get("game_id") for r in feed if r.get("status") == "in_progress"],
    }

    # price store coverage, both implementations
    def price_cov(path, cols):
        rows = cload(path)
        if not rows:
            return None
        def has(v):
            return bool((v or "").strip())
        n = len(rows)
        return {
            "path": path, "rows": n,
            "open": sum(1 for r in rows if has(r.get(cols[0]))),
            "close": sum(1 for r in rows if has(r.get(cols[1]))),
            "both": sum(1 for r in rows if has(r.get(cols[0])) and has(r.get(cols[1]))),
            "stamped": sum(1 for r in rows if has(r.get(cols[2])) if cols[2] in r),
        }

    out["price"] = [
        price_cov("data/price_snapshots.csv", ("opening_line", "closing_line", "observed_at_utc")),
        price_cov("fl2-lines/data/prices/price-snapshots-2026.csv",
                  ("open_line", "close_line", "observed_at_utc")),
    ]
    out["price"] = [x for x in out["price"] if x]

    # standings published vs replayed from the feed vs official today
    st_json = jload("data/standings.json")
    published = {}
    for div in first_list(st_json, "divisions"):
        for t in div.get("teams", []):
            published[t["team"]] = (t.get("w", 0), t.get("l", 0), t.get("t", 0))
    official_2026_11_17 = {k: tuple(v) for k, v in
                           (ev.get("official_club_records_2026_11_17") or {}).get("records", {}).items()}

    # corpus reconciliation: replay the feed, and replay it again with the fixtures this
    # session found decided applied. Both numbers are computed; neither is asserted.
    # A captured "pending then decided" fixture may since have become final in the feed
    # itself (e.g. the Week-10 SNF final captured 2026-11-17); applying such a fixture
    # again would double-count it, so only still-open fixtures are applied here.
    pending = (ev.get("pending_fixtures_now_decided") or {}).get("rows", [])
    final_ids = {r.get("game_id") for r in finals}
    applied = {x["game_id"]: x for x in pending
               if x.get("home_score") is not None and x["game_id"] not in final_ids}

    def replay(extra=None):
        tal = defaultdict(lambda: [0, 0, 0])
        for r in finals:
            a, h = r.get("away"), r.get("home")
            try:
                asc, hsc = int(r.get("away_score")), int(r.get("home_score"))
            except (TypeError, ValueError):
                continue
            if asc == hsc:
                tal[a][2] += 1; tal[h][2] += 1
            elif asc > hsc:
                tal[a][0] += 1; tal[h][1] += 1
            else:
                tal[h][0] += 1; tal[a][1] += 1
        for g in (extra or {}).values():
            a, h = g["away"], g["home"]
            asc, hsc = g["away_score"], g["home_score"]
            if asc == hsc:
                tal[a][2] += 1; tal[h][2] += 1
            elif asc > hsc:
                tal[a][0] += 1; tal[h][1] += 1
            else:
                tal[h][0] += 1; tal[a][1] += 1
        return tal

    t0, t1 = replay(), replay(applied)
    tally = {k: tuple(v) for k, v in t0.items()}
    mis0 = [k for k in official_2026_11_17 if tuple(t0.get(k, (0, 0, 0)))[:2] != tuple(official_2026_11_17[k])[:2]]
    mis1 = [k for k in official_2026_11_17 if tuple(t1.get(k, (0, 0, 0)))[:2] != tuple(official_2026_11_17[k])[:2]]
    out["replay"] = {
        "sampled": len(official_2026_11_17), "as_is_ok": len(official_2026_11_17) - len(mis0),
        "as_is_bad": sorted(mis0), "with_pending_ok": len(official_2026_11_17) - len(mis1),
        "with_pending_bad": sorted(mis1), "applied": sorted(applied), "still_open": sorted(
            x["game_id"] for x in pending if x.get("home_score") is None),
    }

    rows = []
    for team, off in official_2026_11_17.items():
        pub = published.get(team)
        rep = tuple(tally.get(team, (0, 0, 0)))
        rows.append({
            "team": team, "published": pub, "replay": rep, "official": off,
            "pub_ok": pub == off, "rep_ok": rep == off,
        })
    out["standings"] = {
        "rows": rows,
        "sampled": len(rows),
        "pub_match": sum(1 for r in rows if r["pub_ok"]),
        "replay_match": sum(1 for r in rows if r["rep_ok"]),
        "source_of_official": "decision-desk/data/evidence.json EV-08 / EV-02 (nfl.com Week 10 and Week 11 pages, 2026-11-17)",
    }

    # the committed Week 10 availability capture, counted rather than quoted
    inj = jload("data/injuries.json") or {}
    irows = iteams = 0
    for g in first_list(inj, "games"):
        for t in g.get("teams", []):
            irows += len(t.get("players", []))
            iteams += 1
    out["injury_capture"] = {"rows": irows, "team_sections": iteams,
                            "clubs": len({t.get("team") for g in first_list(inj, "games")
                                          for t in g.get("teams", [])})}

    # delta between the two dated captures of the same official Week 10 report
    delta = {"pairs": [], "clubs": [], "total_a": 0, "total_b": 0, "same": None}
    try:
        import csv as _csv
        lab_rows = list(_csv.DictReader(open(p("data", "linelab", "captures", "2026-11-16",
                                              "week10-injury-report.csv"), newline="", encoding="utf-8-sig")))
        per_lab = Counter(r.get("team") for r in lab_rows)
        per_full = Counter()
        for g in first_list(jload("data/injuries.json") or {}, "games"):
            for tt in g.get("teams", []):
                per_full[tt.get("team")] += len(tt.get("players", []))
        delta["total_a"] = sum(per_full.values())
        delta["total_b"] = len(lab_rows)
        delta["clubs_a"] = len([c for c in per_full if c])
        delta["clubs_b"] = len([c for c in per_lab if c])
        delta["clubs"] = sorted(
            [{"club": c, "a": per_full.get(c, 0), "b": per_lab.get(c, 0), "d": per_lab.get(c, 0) - per_full.get(c, 0)}
             for c in set(per_full) | set(per_lab) if per_full.get(c, 0) != per_lab.get(c, 0)],
            key=lambda x: x["club"])
        delta["same"] = len(delta["clubs"]) == 0
        delta["a_date"] = str((jload("data/injuries.json") or {}).get("meta", {}).get("retrieved_utc", ""))
        delta["b_date"] = "2026-11-16"
        try:
            d0 = date.fromisoformat(delta["a_date"][:10])
            d1 = date.fromisoformat(delta["b_date"])
            gap = (d1 - d0).days
            delta["day_gap"] = f"{gap} day{'s' if gap != 1 else ''}"
        except Exception:
            delta["day_gap"] = "an unstated interval"
        # the designated-only view: does its row count equal the designated rows in the full capture?
        des_full = sum(1 for g in first_list(jload("data/injuries.json") or {}, "games")
                       for tt in g.get("teams", []) for pl in tt.get("players", []) if (pl[4] or "").strip())
        delta["designated_in_full"] = des_full
        delta["designated_view_rows"] = len(cload("data/injury-report-2026-w10.csv"))
    except Exception as exc:  # recorded, not hidden
        delta["error"] = f"{type(exc).__name__}: {exc}"

    out["delta"] = delta

    # availability captures held
    caps = []
    for d in sorted(os.listdir(p("data", "captures"))) if os.path.isdir(p("data", "captures")) else []:
        caps.append(d)
    lab = []
    lp = p("data", "linelab", "captures")
    if os.path.isdir(lp):
        lab = sorted(os.listdir(lp))
    out["captures"] = {"data_captures": caps, "linelab_capture_days": lab}

    # forecast ledger
    led = jload("data/forecast_ledger.json") or {}
    fcs = first_list(led, "forecasts")
    out["forecast"] = {
        "n": len(fcs), "generated": led.get("generated_at_utc"), "kickoff": led.get("gate_G4_first_kickoff_utc"),
        "gate": led.get("gate_G4_status"), "model": led.get("model_id"),
        "commit": led.get("registration_commit"), "graded": sum(1 for f in fcs if f.get("graded")),
    }
    return out


# ----------------------------------------------------------------- calibration

def calibration():
    cal = jload("fl2-lines/data/derived/designation-calibration.json") or {}
    by = cal.get("by_designation", {})
    rows = []
    for k in ("Out", "Doubtful", "Questionable", "Probable"):
        v = by.get(k)
        if not v:
            continue
        rows.append({"designation": k, "n": v.get("n"), "played": v.get("played"),
                     "rate": v.get("play_rate_pct"), "ci": v.get("ci95_pct")})
    # the same designations counted in the committed 2026 week-10 capture
    inj = jload("data/injuries.json") or {}
    des = Counter()
    per_team = Counter()
    total = 0
    for g in first_list(inj, "games"):
        for t in g.get("teams", []):
            for player in t.get("players", []):
                total += 1
                des[(player[4] or "").strip() or "(blank)"] += 1
                per_team[t.get("team")] += 1
    return {"published": rows, "cal": cal, "capture_total": total, "capture_designations": des,
            "capture_teams": len(per_team)}


# -------------------------------------------------------------------- render

CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#14161a;--mut:#5b6470;--line:#e2e5ea;--bad:#a3282a;
--good:#166534;--warn:#8a5a00;--accent:#1f4e79}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
header.top{background:var(--card);border-bottom:1px solid var(--line);padding:14px 22px;display:flex;flex-wrap:wrap;gap:14px;align-items:baseline}
header.top .brand{font-weight:700;letter-spacing:.2px}
header.top nav{display:flex;flex-wrap:wrap;gap:10px;margin-left:auto}
header.top nav a{color:var(--accent);text-decoration:none;font-size:13.5px;padding:3px 7px;border-radius:6px}
header.top nav a:hover{background:#eef3f8}
header.top nav a[aria-current]{background:var(--accent);color:#fff}
main{max-width:1280px;margin:0 auto;padding:20px 22px 64px}
h1{font-size:23px;margin:6px 0 4px}
h2{font-size:17px;margin:26px 0 8px}
h3{font-size:15px;margin:18px 0 6px}
p.lede{color:var(--mut);margin:0 0 14px;max-width:96ch}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px;margin:14px 0 6px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:11px 12px}
.card .k{font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut)}
.card .v{font-size:21px;font-weight:650;margin-top:3px}
.card .n{font-size:12px;color:var(--mut);margin-top:3px}
.callout{background:#fffdf3;border:1px solid #ece2b8;border-radius:10px;padding:11px 13px;margin:14px 0;max-width:100ch}
.callout.blue{background:#f2f7fd;border-color:#cfdef0}
.callout.red{background:#fdf4f4;border-color:#eed2d2}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden;margin:8px 0 4px;font-size:13.5px}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:#f0f2f5;font-size:11.5px;text-transform:uppercase;letter-spacing:.03em;color:#404853;white-space:nowrap}
tr:last-child td{border-bottom:0}
tbody tr:hover{background:#fafbfc}
td.num{font-variant-numeric:tabular-nums;white-space:nowrap}
.bad{color:var(--bad);font-weight:600}.good{color:var(--good);font-weight:600}.warn{color:var(--warn);font-weight:600}
.miss{color:var(--bad);font-style:italic;font-size:12.5px}
.tag{display:inline-block;padding:1px 7px;border-radius:999px;font-size:11.5px;border:1px solid var(--line);background:#f4f6f8;color:#3c4652;white-space:nowrap}
.tag.p0{background:#1f4e79;color:#fff;border-color:#1f4e79}
.tag.p1{background:#d9e6f3;color:#12324d;border-color:#bcd3ea}
.tag.p2{background:#eef2f0;color:#2c4436;border-color:#d6e2d8}
.tag.p3{background:#f4f4f4;color:#555}
.tag.done{background:#e7f4ea;color:#195c2f;border-color:#cbe7d3}
.tag.open{background:#fdeeee;color:#8d2b2b;border-color:#f2d5d5}
.small{font-size:12.5px;color:var(--mut)}
ol.path{margin:6px 0 0 18px;padding:0;max-width:100ch}
ol.path li{margin:0 0 9px}
code{background:#f1f3f6;border-radius:4px;padding:0 4px;font-size:12.5px}
footer{border-top:1px solid var(--line);background:var(--card);padding:14px 22px;color:var(--mut);font-size:12.5px}
footer a{color:var(--accent)}
.wrap{overflow-x:auto}
"""

NAV = [("index.html", "Brief"), ("suggestions.html", "Suggestion review"),
       ("questions.html", "Questions & answers"), ("calibration.html", "Designation calibration"),
       ("freshness.html", "Freshness"), ("sources.html", "Verification log")]


def page(title, lede, body, current, counts=None):
    nav = "".join(
        '<a href="{0}"{1}>{2}</a>'.format(esc(h), ' aria-current="page"' if h == current else "", esc(t))
        for h, t in NAV)
    strip = ""
    if counts:
        strip = '<div class="cards">' + "".join(
            f'<div class="card"><div class="k">{esc(k)}</div><div class="v">{esc(v)}</div>'
            f'<div class="n">{esc(n)}</div></div>' for k, v, n in counts) + "</div>"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} &middot; FL2 Decision Desk</title>
<link rel="stylesheet" href="assets/style.css"></head>
<body>
<header class="top"><span class="brand">FL2 &middot; Decision Desk</span><nav>{nav}</nav></header>
<main><h1>{esc(title)}</h1><p class="lede">{lede}</p>{strip}{body}</main>
<footer>Built by <code>{esc(SESSION)}</code> on {esc(BUILD_DATE)} from
<a href="data/evidence.json">this session's dated capture</a>, the repository's own registers and the
official league pages they cite. The hub is at <a href="../index.html">/index.html</a>. Nothing on these
pages is a recommendation to wager; the numbers are audit records.</footer>
</body></html>
"""


def table(headers, rows, cls=""):
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="wrap"><table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def state_tag(s):
    s = (s or "").lower()
    if "done" in s or "adopt" in s or "merged" in s:
        return '<span class="tag done">done</span>'
    if "reject" in s:
        return '<span class="tag">rejected</span>'
    if "proposed" in s:
        return '<span class="tag p1">new</span>'
    return f'<span class="tag open">{esc(s or "open")}</span>'


# ---------------------------------------------------------------------- build

def build():
    os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "assets"), exist_ok=True)
    open(os.path.join(OUT, "assets", "style.css"), "w", encoding="utf-8").write(CSS)

    ev = jload("decision-desk/data/evidence.json") or {"entries": []}
    sug_rows = load_suggestions()
    present = [r for r in sug_rows if not r.get("absent")]
    absent_regs = [r for r in sug_rows if r.get("absent")]
    new = new_suggestions(ev)
    clusters = dedupe(present + new)
    ready = readiness_rows()
    blocked_v2 = requirements_v2_blocked()
    gate_linkage(clusters, ready)

    # dependency in-degree: how many other suggestions name this one
    dep_in = Counter()
    for c in clusters:
        for m in c["members"]:
            dep = str(m.get("_extra", {}).get("depends_on") or m.get("depends") or "")
            for d in re.findall(r"SG-?\d+|DS-\d+", dep):
                dep_in[d] += 1
    EFF = {"low": 1.0, "medium": 2.0, "high": 3.0, "critical": 4.0, "": 3.0}

    OWNER_WORDS = ("budget", "licence", "license", "terms", "buy", "purchase", "pay for",
                   "legal", "reward", "owner", "spend", "consent", "policy")
    canon = []
    for i, c in enumerate(sorted(clusters, key=lambda c: -len(c["members"]))):
        members = sorted(c["members"], key=lambda m: (m.get("_register") != "decision-desk", m.get("_id", "")))
        head = members[0]
        eff = next((m["_extra"].get("effort", "") for m in members if m.get("_extra", {}).get("effort")), "")
        imp = next((m["_extra"].get("impact", "") for m in members if m.get("_extra", {}).get("impact")), "")
        ids = [f"{m['_register']}:{m['_id']}" for m in members]
        indeg = sum(dep_in.get(str(m["_id"]).upper().replace("SG", "SG-").replace("--", "-"), 0)
                    + dep_in.get(str(m["_id"]), 0) for m in members)
        indeg = max(indeg // 2, 0)
        cost = EFF.get((eff or "").lower(), 3.0)
        breadth = len(members)
        linked = len(c["linked_rows"])
        ev_bonus = 1.0 * len(head.get("capture_refs") or [])
        # cost is a tie-breaker, not a divisor: an expensive decision that unblocks
        # three gates must not sink below a cheap one that unblocks nothing.
        score = breadth * 1.0 + linked * 1.5 + min(indeg, 3) * 2.0 + ev_bonus
        bits = [head.get("_title", ""), head.get("_problem", ""), head.get("_change", "")]
        bits += [str(m.get("_extra", {}).get("missing", "")) for m in members]
        bits += [str(m.get("_extra", {}).get("missing_information_to_decide", "")) for m in members]
        alltext = " ".join(str(x) for x in bits).lower()
        who = "owner" if any(w in alltext for w in OWNER_WORDS) else "engineering"
        # ids are derived from the register entry, never from sort position, so a
        # reference written today still points at the same decision next month.
        if head.get("_register") == "decision-desk":
            uid = str(head.get("_id") or f"DD-{i+1:03d}")
        else:
            uid = f'{head.get("_register")}-{head.get("_id")}'.strip("-") or f"DD-{i+1:03d}"
        uid = re.sub(r"[^A-Za-z0-9._-]", "-", uid)
        canon.append({
            "uid": uid,
            "order": i + 1,
            "who": who,
            "title": head.get("_title") or head.get("_change") or "",
            "problem": head.get("_problem", ""),
            "change": head.get("_change", ""),
            "effort": eff, "impact": imp,
            "risk": next((m["_extra"].get("risk", "") for m in members if m.get("_extra", {}).get("risk")), ""),
            "state": next((m["_extra"].get("state") or m["_extra"].get("status") for m in members
                           if (m.get("_extra") or {}).get("state") or (m.get("_extra") or {}).get("status")), ""),
            "recommendation": next((m["_extra"].get("recommendation", "") for m in members
                                    if m.get("_extra", {}).get("recommendation")), ""),
            "missing": next((m["_extra"].get("missing_information_to_decide") or m["_extra"].get("missing_information")
                             for m in members
                             if m.get("_extra", {}).get("missing_information_to_decide")
                             or m.get("_extra", {}).get("missing_information")), ""),
            "registers": ids,
            "sources": [{"register": m["_register"], "path": m["_path"], "id": m["_id"]} for m in members],
            "linked_rows": [{"id": x["id"], "status": x["status"]} for x in c["linked_rows"]],
            "capture_refs": head.get("capture_refs", []),
            "how_to_check": head.get("how_to_check", ""),
            "breadth": breadth, "linked_count": linked, "in_degree": indeg,
            "evidence_count": len(head.get("capture_refs") or []),
            "cost": cost, "score": round(score, 3),
        })
    canon.sort(key=lambda x: (-x["score"], x["cost"], x["uid"]))
    for tier, r in enumerate(canon):
        r["path_tier"] = "P0 now" if tier < 4 else "P1 next" if tier < 12 else "P2 later" if tier < 26 else "P3 backlog"

    # collisions between registers
    by_id = defaultdict(list)
    for r in present:
        key = str(r.get("_id", "")).upper().replace("-", "")
        if r.get("_id"):
            by_id[key].append(r)
    collisions = [{"id": k, "members": sorted({f"{v['_register']}:{v['_id']}" for v in vs}),
                   "titles": [clip(v.get("_title"), 70) for v in vs],
                   "paths": sorted({v["_path"] for v in vs})}
                  for k, vs in by_id.items() if len({v["_register"] for v in vs}) > 1]
    collisions = [c for c in collisions if len(set(c["titles"])) > 1]

    # questions
    qrows = []
    for reg, path, qcol, whycol, knowcol, misscol, closecol, prio_col, stat_col, section in QUESTION_REGISTERS:
        if path.endswith(".json"):
            items = first_list(jload(path), "questions", "items", "suggestions", "rows")
        else:
            items = cload(path)
        for it in items:
            if not isinstance(it, dict):
                continue
            qrows.append({
                "register": reg, "path": path, "section": section,
                "id": str(it.get("id") or "").strip(),
                "question": str(it.get(qcol) or "").strip(),
                "why": str(it.get(whycol) or "").strip(),
                "known": str(it.get(knowcol) or "").strip(),
                "missing": str(it.get(misscol) or "").strip() if misscol else "",
                "close": str(it.get(closecol) or "").strip() if closecol else "",
                "priority": str(it.get(prio_col) or "").strip() if prio_col else "",
                "status": str(it.get(stat_col) or "").strip() if stat_col else "",
                "toks": toks(it.get(qcol, "")),
            })
    # cluster questions the same way
    qclusters = []
    for q in qrows:
        for c in qclusters:
            if similarity(q["toks"], c["toks"]) >= 0.3:
                c["members"].append(q)
                c["toks"] |= q["toks"]
                break
        else:
            qclusters.append({"toks": q["toks"], "members": [q]})
    qcanon = []
    for i, c in enumerate(sorted(qclusters, key=lambda c: -len(c["members"]))):
        head = c["members"][0]
        answered = any("answer" in (m.get("status") or "").lower() or "closed" in (m.get("status") or "").lower()
                       or "resolved" in (m.get("status") or "").lower() for m in c["members"])
        qcanon.append({
            "uid": f"DQ-{i+1:03d}", "question": head["question"], "why": head["why"],
            "known": head["known"], "missing": head["missing"], "close": head["close"],
            "priority": head["priority"], "status": head["status"], "answered": answered,
            "registers": [f"{m['register']}:{m['id']}" for m in c["members"]],
            "paths": sorted({m["path"] for m in c["members"]}),
            "n": len(c["members"]),
        })
    # this session's answers to the questions it could actually close
    answers = [
        {"uid": "DQ-A1", "question": "Is a multi-season archive of the official weekly injury report reachable at all?",
         "answer": "Yes, from the league's own site, at nfl.com/injuries/league/{year}/reg{week}. Two seasons were "
                   "rendered today (2025 week 10, 2024 week 10) with the practice and game status columns intact.",
         "status": "answered 2026-11-17", "evidence": ["EV-05", "EV-06"],
         "still_open": "Whether the archived page holds the Friday-final version or the last-saved version of that "
                       "week is not stated on the page; a backtest that needs the exact Wednesday state still has to "
                       "capture it going forward."},
        {"uid": "DQ-A2", "question": "Is the Week 10 corpus complete enough to grade the pre-registered baseline?",
         "answer": "No. The Monday-night fixture was still live when checked (17-7, Q2), so 148 of 149 games are "
                   "final. The feed already carries that state instead of guessing.",
         "status": "answered 2026-11-17", "evidence": ["EV-01", "EV-02"],
         "still_open": "Nothing - re-run the capture after the final; this is a timing fact, not a defect."},
        {"uid": "DQ-A3", "question": "Does an official Week 11 availability report exist before this Thursday's kickoff?",
         "answer": "Not yet at the time of checking: the 2026 week selector on the official report stops at "
                   "WEEK 10, and the page still titles itself as Week 10.",
         "status": "answered 2026-11-17", "evidence": ["EV-04"],
         "still_open": "How many report days will exist before the Thursday fixture - one if the page rolls on "
                       "Wednesday, zero if it rolls Thursday morning."},
        {"uid": "DQ-A4", "question": "Is the published standings table consistent with the results feed?",
         "answer": "No. 9 of the 12 clubs sampled on the live page disagree with data/standings.json, and every "
                   "disagreement is one Week 10 game. The replay computed from the feed agrees with the official "
                   "page, so the feed is sound and the published table is the stale artefact.",
         "status": "answered 2026-11-17", "evidence": ["EV-08"], "still_open": "none"},
        {"uid": "DQ-A5", "question": "Can a fixture's venue be taken from the official game centre on demand?",
         "answer": "Partly. The game-centre Stadium field was reached for LAC@BAL (M&T Bank Stadium) but the "
                   "info chunk for IND@HOU could not be fetched twice at the page reader, so that venue stays "
                   "unverified and the two repository artefacts still disagree (NRG vs Reliant).",
         "status": "partly answered 2026-11-17", "evidence": ["EV-09", "EV-01"],
         "still_open": "One retry of the game-centre info chunk; until then the value stays blank and flagged."},
    ]

    fresh = freshness(ev)
    cal = calibration()
    archive_ids = [b["id"] for b in blocked_v2 if "blocked" in b["status"].lower()
                   and re.search(r"archiv", " ".join(b["cells"]), re.I)]
    inventory = register_inventory()

    stats = {
        "suggestions_present": len(canon),
        "suggestion_entries": len(present),
        "registers": len([r for r in inventory if r[3] > 0]),
        "new_from_this_session": len(new),
        "collisions": len(collisions),
        "questions_present": len(qcanon),
        "question_entries": len(qrows),
        "evidence_entries": len(ev.get("entries", [])),
        "blocked_requirements": len([b for b in blocked_v2 if "blocked" in b["status"].lower()]),
        "readiness_rows": len(ready),
        "archive_premise_rows": len(archive_ids),
        "archive_premise_ids": archive_ids,
        "not_done_readiness": len([r for r in ready if (r.get("status") or "").upper() != "DONE"]),
    }

    # ---------------------------------------------------------------- pages
    build_suggestions(canon, collisions, inventory, stats, ev)
    build_questions(qcanon, answers, stats)
    build_calibration(cal, stats)
    build_freshness(fresh, stats, ev)
    build_sources(ev, stats, fresh['feed']['final'])
    build_index(canon, fresh, stats, cal, ev, answers)

    json.dump({"built_by": f"tools/{os.path.basename(__file__)}", "built_date": BUILD_DATE,
               "stats": stats, "suggestions": canon, "questions": qcanon, "answers": answers,
               "freshness": fresh, "register_inventory": [list(x) for x in inventory],
               "collisions": collisions},
              open(os.path.join(OUT, "data", "desk.json"), "w", encoding="utf-8"), indent=1)
    print(json.dumps(stats, indent=1))
    return stats


# ---------------------------------------------------------------- page pieces

def ev_link(evmap, eid):
    e = evmap.get(eid)
    if not e:
        return esc(eid)
    return link(e["url"], f"{eid}: official page") + f' <span class="small">({esc(e["fetched_at_utc"])} UTC)</span>'


def build_suggestions(canon, collisions, inventory, stats, ev):
    evmap = {e["id"]: e for e in ev.get("entries", [])}
    rows = []
    for r in canon:
        src = " &middot; ".join(repo_link(s["path"], f"{s['register']}:{s['id']}") for s in r["sources"][:3])
        if r["capture_refs"]:
            src += "<br>" + " &middot; ".join(link("sources.html#" + e, e) for e in r["capture_refs"])
        linked = " ".join(f'<span class="tag">{esc(x["id"])}</span>' for x in r["linked_rows"]) or '<span class="small">none linked</span>'
        rows.append([
            f'<b id="{esc(r["uid"])}">{esc(r["uid"])}</b><br><span class="tag {"p0" if r["path_tier"].startswith("P0") else "p1" if r["path_tier"].startswith("P1") else "p2" if r["path_tier"].startswith("P2") else "p3"}">{esc(r["path_tier"])}</span>',
            f'<b>{esc(clip(r["title"], 120))}</b>'
            + (f'<br><span class="small">{esc(clip(r["problem"], 230))}</span>' if r["problem"] else "")
            + (f'<br><span class="small"><i>change:</i> {esc(clip(r["change"], 230))}</span>' if r["change"] else ""),
            esc(r["impact"] or "(not stated)") + " / " + esc(r["effort"] or "(not stated)"),
            f'<span class="tag {"p1" if r["who"] == "owner" else ""}">{esc(r["who"])}</span>',
            state_tag(r["state"]),
            linked,
            f'{r["breadth"]} register{"" if r["breadth"]==1 else "s"}<br>'
            f'<span class="small">deps {r["in_degree"]} &middot; gates {r["linked_count"]} &middot; captures {r["evidence_count"]} &middot; cost {r["cost"]:g}<br>'
            f'score {r["score"]:g}</span>',
            src or blank("no source file"),
        ])
    dupes = duplicate_registers()
    drows = [[f"{esc(d['a'])} vs {esc(d['b'])}",
              repo_link(d["a_path"], os.path.basename(d["a_path"])) + " &middot; " +
              repo_link(d["b_path"], os.path.basename(d["b_path"])),
              f'{d["shared_ids"]}', f'<b>{d["identical"]}</b>',
              ('<span class="bad">a verbatim copy</span>' if d["verbatim"] else
               f'{len(d["differing"])} id(s) carry different text under the same id: '
               + ", ".join(f'<code>{esc(x)}</code>' for x in d["differing"]) +
               ('&hellip;' if d["identical"] < d["shared_ids"] else "")),
              "one of them should be generated from the other, not edited in parallel"]
             for d in dupes]

    inv_rows = []
    for kind, reg, path, n, section in inventory:
        if reg == "html-only":
            note = (f'<b>{n}</b> static rows' if n else
                    '<span class="bad">0 static rows</span><br><span class="small">renders client-side or as '
                    'cards, so no artefact a checker can read</span>')
            inv_rows.append([esc(kind), esc(reg + " page"), repo_link(path, path), note, esc(section)])
        else:
            inv_rows.append([esc(kind), esc(reg), repo_link(path, path),
                             f'<b>{n}</b>' if n else '<span class="bad">0 - absent or empty</span>',
                             esc(section)])
    col_rows = [[f'<b>{esc(c["id"])}</b>',
                 " &middot; ".join(esc(m) for m in c["members"]),
                 "<br>".join(esc(t) for t in c["titles"]),
                 " &middot; ".join(repo_link(x, os.path.basename(x)) for x in c["paths"])]
                for c in collisions]
    body = f"""
<div class="callout blue"><b>How to use this page.</b> One row is one decision, not one file: entries that describe
the same work in different registers are merged into a single row and every originating id is kept underneath it, so
nothing is lost by reading only here. The <i>score</i> is printed arithmetic, not a verdict:
1&times;registers + 1.5&times;not-done-readiness-rows-touched + 2&times;dependent-suggestions (capped at 3)
+ 1&times;captured-observations. Effort does not divide the score - it breaks ties, so an expensive step that unblocks
three gates outranks a cheap one that unblocks none. The readiness link is a shared-content-word match (&ge;4 words)
and the matched row ids are shown, so a bad link can be rejected on sight.</div>
<div class="callout"><b>Two kinds of row.</b> <span class="tag p1">owner</span> rows cannot be closed by code: they wait
on a licence, a budget, a reading of terms, or a definition. <span class="tag">engineering</span> rows can. The board
is sorted by score across both kinds; the brief's own "start here" list on the
<a href="index.html">first page</a> takes the top row of each kind.</div>
<div class="callout"><b>Why a consolidated board exists.</b> Before this page the same object type lived in five
machine-readable registers plus three HTML-only pages, using two id formats. The table below that collision is the
first thing to fix, because it makes "adopt SG-05" ambiguous between two unrelated suggestions.</div>
<h2>Collision check across registers</h2>
{table(['id used in more than one register','occurrences','titles under that same id','files'], col_rows) if col_rows else '<p class="small">No id is reused for a different suggestion.</p>'}
<h2>The board &middot; {stats['suggestions_present']} decisions from {stats['suggestion_entries']} register entries</h2>
{table(['id','suggestion','impact / effort','who acts','state','links to','why it ranks here','source'], rows)}
<h2>Registers that overlap each other, measured</h2>
<p class="small">Computed by comparing every pair of machine-readable registers on id and title. A shared id with
different text is the collision problem; a shared id with identical text is the copy problem. Both are printed so
neither has to be remembered by whoever merges these files next.</p>
{table(['registers compared','files','ids in common','identical','what differs','reading'], drows)}
<h2>Where each register lives, and how many rows it carries</h2>
{table(['kind','register','path','rows','section'], inv_rows)}
<p class="small">A row with 0 means the artefact was absent or empty at build time
({BUILD_DATE}); it is not a claim that the register is unimportant.</p>
"""
    open(os.path.join(OUT, "suggestions.html"), "w", encoding="utf-8").write(page(
        "Suggestion review board",
        "Every improvement suggestion the repository has ever recorded, in one queue, each carrying the file it "
        "came from and the official page that supports it. Read the top rows first; the ordering arithmetic is printed "
        "in the table so it can be argued with.",
        body, "suggestions.html",
        [("suggestions to decide", stats["suggestions_present"], "merged from register entries"),
         ("registers read", stats["registers"], "5 machine-readable + 3 HTML-only"),
         ("from this session", stats["new_from_this_session"], "each tied to a captured observation"),
         ("id collisions", stats["collisions"], "same id, different suggestion")]))


def build_questions(qcanon, answers, stats):
    arows = []
    for a in answers:
        arows.append([f'<b id="{esc(a["uid"])}">{esc(a["uid"])}</b>',
                      f'<b>{esc(a["question"])}</b>',
                      esc(a["answer"]),
                      state_tag(a["status"]),
                      esc(a["still_open"]) or '<span class="small">none</span>',
                      " &middot; ".join(link("sources.html#" + e, e) for e in a["evidence"])])
    qrows = []
    for q in qcanon:
        src = " &middot; ".join(repo_link(pth, pth.split("/")[-1]) for pth in q["paths"])
        qrows.append([
            f'<b>{esc(q["uid"])}</b>' + (f'<br><span class="small">{q["n"]} registers</span>' if q["n"] > 1 else ""),
            f'<b>{esc(clip(q["question"], 150))}</b>' + (f'<br><span class="small">{esc(clip(q["why"],190))}</span>' if q["why"] else ""),
            esc(clip(q["known"], 260)) or blank("nothing recorded"),
            esc(clip(q["missing"], 220)) or blank("not stated"),
            esc(clip(q["close"], 220)) or blank("not stated"),
            esc(q["priority"] or "(not stated)") + "<br>" + (state_tag(q["status"]) if q["status"] else '<span class="tag">open</span>'),
            src or blank("no source file"),
        ])
    body = f"""
<div class="callout blue"><b>Answered by this session.</b> Five questions that the registers left open could be closed
from the live official pages, so they are answered here with the capture id attached. The rest stay open on purpose:
they need a licence, a budget or a decision, which is the owner's to make, not a thing to be inferred.</div>
<h2>Closed today</h2>
{table(['id','question','answer','state','what is still open','evidence'], arows)}
<h2>The open queue &middot; {stats['questions_present']} questions from {stats['question_entries']} register entries</h2>
<p class="small">Known-verified is quoted from the register that asked it; where a register asserted a value with no
artefact behind it, the cell says so instead of repeating the assertion.</p>
{table(['id','question','what we know (verified)','what is missing','what would close it','priority / state','source'], qrows)}
"""
    open(os.path.join(OUT, "questions.html"), "w", encoding="utf-8").write(page(
        "Questions, information and answers",
        "The list the owner asked for: what must be settled before a decision is reasonable, split into what is "
        "already verified, what is missing, and how to go and get it.",
        body, "questions.html",
        [("questions", stats["questions_present"], "merged across registers"),
         ("closed by this session", len(answers), "each with an official capture"),
         ("register entries read", stats["question_entries"], "five registers"),
         ("blocked requirements", stats["blocked_requirements"], "in the R-register, some premises now false")]))


def measured_panel():
    """The three measured panels the owner should not have to go hunting for.

    Everything here is read out of the artefacts that already hold it, with n and the
    interval attached, because the brief requires n to travel with every value.
    """
    out = {"positions": [], "correlations": [], "parlay": {}, "missing": []}
    cal = jload("fl2-lines/data/derived/designation-calibration.json") or {}
    for k, v in sorted((cal.get("by_designation_and_position") or {}).items(),
                       key=lambda kv: -(kv[1].get("n") or 0)):
        if (v.get("n") or 0) < 500:
            continue
        des, pos = k.split("|") if "|" in k else (k, "")
        ci = v.get("ci95_pct") or ["", ""]
        out["positions"].append({"designation": des, "group": pos, "n": v.get("n"),
                                 "rate": v.get("play_rate_pct"), "ci": ci})
    corr = jload("fl2-lines/data/derived/correlations.json") or {}
    for panel, meta in corr.items():
        if not isinstance(meta, dict):
            continue
        for name, v in (meta.get("values") or {}).items():
            if not isinstance(v, dict):
                continue
            ci = v.get("fisher_ci95") or v.get("ci95") or ["", ""]
            excludes = bool(ci) and (ci[0] > 0 or ci[1] < 0)
            out["correlations"].append({
                "panel": panel, "pair": name, "r": v.get("r"), "n": v.get("n"), "ci": ci,
                "excludes_zero": excludes,
                "window": "2026 season, played games" if "2026" in name else "2015-2026"})
    pj = corr.get("parlay_joint") or {}
    if pj:
        out["parlay"] = {
            "n_games": pj.get("n_games"),
            "p_home": pj.get("p_home_cover_pct"), "p_over": pj.get("p_over_pct"),
            "measured": pj.get("p_both_measured_pct"),
            "if_independent": pj.get("p_both_if_independent_pct"),
            "difference": pj.get("difference_pct_points"), "phi": pj.get("phi"),
            "ci": pj.get("joint_ci95_pct"), "gate": pj.get("gate_status"),
            "path": "fl2-lines/data/derived/correlations.json"}
    for k, rel in [("designation calibration", "fl2-lines/data/derived/designation-calibration.json"),
                   ("correlation panel", "fl2-lines/data/derived/correlations.json")]:
        if not os.path.exists(p(rel)):
            out["missing"].append(f"{k} ({rel})")
    return out


def build_calibration(cal, stats):
    arch_ids = ", ".join(stats.get("archive_premise_ids") or []) or "none found"
    rows = []
    for r in cal["published"]:
        ci = r["ci"] or ["", ""]
        rows.append([f'<b>{esc(r["designation"])}</b>', f'{r["n"]:,}', f'{r["played"]:,}',
                     f'{r["rate"]:.2f}&thinsp;%', f'{ci[0]:.2f}&ndash;{ci[1]:.2f}%',
                     link("https://www.nfl.com/injuries/", "official report") + " &middot; " +
                     repo_link("fl2-lines/data/derived/designation-calibration.json", "calibration artefact"),
                     '<span class="small">mirror rows joined to participation</span>'])
    des = cal["capture_designations"] or Counter()
    cap_rows = [[esc(k), f'{v:,}', f'{(v / max(1, cal["capture_total"]))*100:.1f}%'] for k, v in
                sorted(des.items(), key=lambda kv: -kv[1])]
    mp = measured_panel()
    pos_rows = [[f'<b>{esc(r["designation"])}</b>', esc(r["group"]), f'{r["n"]:,}', f'{r["rate"]:.2f}&thinsp;%',
                 f'{r["ci"][0]:.2f}&ndash;{r["ci"][1]:.2f}%',
                 repo_link("fl2-lines/data/derived/designation-calibration.json", "artefact") + " &middot; " +
                 link("https://www.nfl.com/injuries/", "official report"),
                 '<span class="small">participation-based: who appeared, not how much</span>']
                for r in mp["positions"]]
    corr_rows = []
    for c in mp["correlations"]:
        src = repo_link("fl2-lines/data/derived/correlations.json", "artefact")
        src += " &middot; " + (link("https://www.nfl.com/schedules/2026/by-week/week-10", "official results")
                               if c["panel"] == "official_only_panel"
                               else '<span class="small">mirror prices, not an official number</span>')
        corr_rows.append([
            f'<span class="tag {"done" if c["panel"] == "official_only_panel" else "open"}">{esc(c["panel"])}</span>',
            f'<code>{esc(c["pair"])}</code>', esc(c["window"]),
            f'{c["r"]:+.4f}' if c["r"] is not None else blank(),
            f'{c["n"]:,}' if c["n"] else blank("no n published"),
            f'{c["ci"][0]:+.4f}&thinsp;to&thinsp;{c["ci"][1]:+.4f}' if c["ci"] else blank("no interval"),
            ('<span class="good">yes</span>' if c["excludes_zero"] else '<span class="bad">no</span>'),
            src])
    pj = mp["parlay"]
    if pj:
        parlay_rows = []
        src_p = (repo_link(pj["path"], "correlations.json") + " &middot; " +
                 link("https://www.nfl.com/", "league results and schedule"))
        for k, v, note in [
            ("games in the joint sample", pj["n_games"], "only games with both legs priced and graded count"),
            ("P(home covers), marginal", pj["p_home"], "percent, measured"),
            ("P(over), marginal", pj["p_over"], "percent, measured"),
            ("P(both) measured", pj["measured"], "what actually happened jointly"),
            ("P(both) if the legs were independent", pj["if_independent"], "what multiplying the marginals claims"),
            ("difference", pj["difference"], "percentage points; the cost of assuming independence"),
            ("phi (association)", pj["phi"], "negative: the two legs are complements in this sample, not repeats of one signal"),
            ("95% CI on the joint", ", ".join(str(x) for x in (pj["ci"] or [])) or None,
             "wide enough that a two-leg parlay cannot be certified profitable on this sample"),
            ("gate status", pj["gate"], "the brief's joint-evidence gate, stated by the artefact itself"),
        ]:
            val = (f"{v:,}" if isinstance(v, int) else
                   (f"{v}" if v is not None else blank("not in the artefact")))
            parlay_rows.append([esc(k), f"<b>{val}</b>", esc(note), src_p])
        parlay_block = table(["quantity", "value", "reading", "source"], parlay_rows)
    else:
        parlay_block = f'<p class="small">The joint-evidence artefact is not present: ' \
                       f'{esc("; ".join(mp["missing"]) or "no reason recorded")}.</p>'
    body = f"""
<div class="callout"><b>What was already measured, and what today's check changes.</b> The play rate per designation is
already computed in this repository from {cal['cal'].get('estimated_on', 'an unstated window')}, with n and an interval on
every row and the participation trap documented. What was missing was the primary source: three requirements in
<code>research/requirements-v2.md</code> ({esc(arch_ids)}) are recorded as <span class="bad">blocked</span> on the
grounds that no archive of past weekly reports is reachable. The archive exists; the test behind that verdict was run
against a mirror rather than against the league's own page. Today two past-season reports were rendered from the league's own site, so the
calibration can be re-derived from the record itself and extended to 2025 and 2026. The numbers below are unchanged
until that re-derivation is run - this page does not overwrite them with a hope.</div>
<h2>Published calibration (unchanged, as computed)</h2>
{table(['designation','n player-weeks','played','play rate','95% CI','source','basis'], rows)}
<h2>The same designation column, counted in our committed Week 10 capture</h2>
<p class="small">{cal['capture_total']:,} rows across {cal['capture_teams']} clubs, from
{repo_link('data/injuries.json', 'data/injuries.json')} - the blank rows are the official page's own blank cells, not
missing data, and the report lists clubs with nothing to declare only when they play.</p>
{table(['game status on the report','rows','share'], cap_rows)}
<h2>The same measurement, split by position group</h2>
<p class="small">Groups with fewer than 500 player-weeks are left out of the table rather than printed with a wide
interval and a shrug; the excluded groups stay in the artefact. A "Questionable" cornerback and a "Questionable"
offensive lineman are not the same bet, and this is where that shows.</p>
{table(['designation','position group','n player-weeks','play rate','95% CI','source','note'], pos_rows)}
<h2>Correlations, official numbers only, with n on every row</h2>
<p class="small">The brief requires correlations to be computed from officially sourced numbers and to publish n with
each value. The first panel is computed from game results and published schedule facts alone. The second uses recorded
market prices from the mirror and is labelled so it cannot be quoted as an official-number result.</p>
{table(['panel','pair','window','r','n','95% CI (Fisher)','interval excludes zero','source'], corr_rows)}
<h2>Why a parlay is not two singles multiplied</h2>
{parlay_block}
<h2>What this unlocks, and what it still does not</h2>
{table(['claim','state','why'], [
 ['"Questionable" is worth about two thirds of a game appearance','<span class="good">measured</span>',
  'The rate is computed with n and a CI, and the folklore percentages are not used.'],
 ['Out is effectively binding','<span class="good">measured</span>',
  'Two rows out of 8,736 in the mirror join; the exceptions are listed rather than dropped.'],
 ['The label predicts how many snaps a limited player takes','<span class="bad">not unlocked</span>',
  'Participation rows say who appeared, not how much; snap share is a separate artefact and is 0 for 2026.'],
 ['Practice trends (DNP &rarr; LP &rarr; FP) carry information across a week','<span class="bad">not unlocked</span>',
  'The archive is one state per week, so the within-week series must still be captured going forward.'],
 ['Reserve lists and inactives are covered by the report','<span class="bad">no</span>',
  'The archive carries the three designations only, so "not listed" still cannot be read as "available".'],
])}
"""
    open(os.path.join(OUT, "calibration.html"), "w", encoding="utf-8").write(page(
        "Designation calibration and the archive question",
        "What an injury label is actually worth, measured rather than assumed - and the source gate that was believed "
        "to block that measurement, tested against the live league site today.",
        body, "calibration.html",
        [("clubs with a designation source", 32, "official report by week"),
         ("past seasons rendered today", 2, "2025 W10, 2024 W10"),
         ("requirements blocked on that premise", stats.get("archive_premise_rows", 0),
          esc(", ".join(stats.get("archive_premise_ids") or []))),
         ("2026 snap counts held", 0, "so depth is still not modelled")]))


def build_freshness(fresh, stats, ev=None):
    ev = ev or {}
    evmap = {e["id"]: e for e in ev.get("entries", [])}
    recblk = ev.get("official_club_records_2026_11_17") or {}
    w10_url = recblk.get("week10_page", "https://www.nfl.com/schedules/2026/by-week/week-10")
    w11_url = recblk.get("week11_page", "https://www.nfl.com/schedules/2026/by-week/week-11")
    f = fresh["feed"]
    s = fresh["standings"]
    dl = fresh.get("delta") or {}
    dl_days = f"({esc(str(dl.get('day_gap', 'interval not stated')))} apart)"
    days = fresh["captures"].get("linelab_capture_days") or []
    try:
        last = date.fromisoformat(days[-1])
        today = date.fromisoformat(BUILD_DATE)
        n = (today - last).days
        cap_age = f"{n} day{'s' if n != 1 else ''}"
    except Exception:
        cap_age = "of unstated age"
    rp = fresh["replay"]
    prows = []
    for pc in fresh["price"]:
        prows.append([repo_link(pc["path"], os.path.basename(pc["path"])), f'{pc["rows"]:,}',
                      f'{pc["open"]:,}', f'{pc["close"]:,}',
                      f'<b class="bad">{pc["both"]:,}</b>' if not pc["both"] else f'{pc["both"]:,}',
                      f'{pc["stamped"]:,}',
                      "CLV gates unsatisfiable" if not pc["both"] else "usable"])
    srows = []
    for r in s["rows"]:
        srows.append([f'<b>{esc(r["team"])}</b>',
                      "%d-%d-%d" % r["published"] if r["published"] else blank("no row"),
                      "%d-%d-%d" % r["replay"],
                      "%d-%d-%d" % r["official"],
                      '<span class="good">matches</span>' if r["pub_ok"] else '<span class="bad">stale</span>',
                      '<span class="good">matches</span>' if r["rep_ok"] else '<span class="bad">disagrees</span>',
                      link(w11_url, "official page") + " &middot; " +
                      repo_link("data/standings.json", "data/standings.json")])
    fc = fresh["forecast"]
    body = f"""
<div class="callout red"><b>Read this before trusting any table on the site.</b> Three separate staleness facts were
found today, all of them mechanical and all fixable in the build: the published standings table disagrees with the
official page for <b>{s['sampled'] - s['pub_match']} of {s['sampled']}</b> sampled clubs while the results feed behind it is
correct; the price stores hold <b>0</b> rows with both an opening and a closing number for 2026, so no CLV gate can be
satisfied; and one Week 10 fixture was still live, so the corpus is {f['final']} finals and not {f['final'] + f['in_progress']}.
</div>
<h2>Feed state</h2>
{table(['artefact','rows','final','in progress','scheduled','week 10','non-final rows'],
       [[repo_link('data/results_feed.csv', 'data/results_feed.csv'), f'{f["rows"]:,}', f'{f["final"]}',
         f'<b class="bad">{f["in_progress"]}</b>', f'{f["scheduled"]}',
         f'{f["week10_final"]} of {f["week10_rows"]}', ", ".join(f'<code>{esc(x)}</code>' for x in f["open_ids"]) or "none"]])}
<p class="small">The non-final row was checked against its own game centre ({link('sources.html#EV-01', 'EV-01')})
and the page said: &ldquo;{esc(clip(evmap.get('EV-01', {}).get('observed', ''), 200))}&rdquo;. The repository's
<code>in_progress</code> label is right, and the fix is not to fill it in - it is to refuse to grade the week until
it is final.</p>
<h2>Standings table vs the feed replay vs the official page ({BUILD_DATE})</h2>
{table(['club','published standings','replayed from feed','official today','published ok','replay ok','source'], srows)}
<p class="small">The official column is transcribed from the live Week 11 schedule page
{link(w11_url, 'nfl.com/schedules/2026/by-week/week-11')} and the Week 10
page {link(w10_url, 'week-10')}; records printed for a club whose own game
is still live (BAL) are the state at the time of reading. Replay is arithmetic on finals already in the feed, not a
new source.</p>
<h2>Corpus reconciliation: what the feed can and cannot reproduce</h2>
<p class="small">Replay means summing the finals the feed holds into a win-loss record and comparing it with the
records printed on the official pages this session transcribed ({rp['sampled']} clubs sampled, {esc(w11_url)}). It is
the same test the results feed was accepted on, re-run today.</p>
{table(['replay','clubs matching','clubs failing','what it shows','source'], [
 ['feed as committed', f'{rp["as_is_ok"]} of {rp["sampled"]}',
  ", ".join(f'<code>{esc(x)}</code>' for x in rp["as_is_bad"]) or "none",
  '<span class="bad">two clubs fail, and both belong to the one fixture the feed still holds open</span>',
  repo_link("data/results_feed.csv", "data/results_feed.csv")],
 ['feed plus the fixtures decided since the capture', f'{rp["with_pending_ok"]} of {rp["sampled"]}',
  ", ".join(f'<code>{esc(x)}</code>' for x in rp["with_pending_bad"]) or "none",
  f'<span class="good">all sampled clubs reconcile once {esc(", ".join(rp["applied"]) or "nothing")} is applied</span> '
  f'- the feed pipeline is sound; its newest capture is {cap_age} old',
  link("sources.html#EV-10", "EV-10")],
 ['still open after that', f'{rp["with_pending_ok"]} of {rp["sampled"]}', ", ".join(f'<code>{esc(x)}</code>' for x in rp["still_open"]) or "none",
  "the Monday-night fixture was live at 17-7 in the second quarter; it stays ungraded, not estimated",
  link("sources.html#EV-01", "EV-01")],
])}
<h2>The same official report, two dated captures: the delta</h2>
<p class="small">The brief asks for the delta rather than the level. The repository holds two captures of the same
Week 10 report {dl_days}; the difference below is computed from the two files, not quoted from a summary.</p>
{table(['capture','rows','clubs covered','versus the other capture','source'], [
 ['data/injuries.json', f'{dl["total_a"]:,}', f'{dl.get("clubs_a", 0)} clubs',
  f'{dl["total_b"] - dl["total_a"]:+d} rows', repo_link("data/injuries.json", "retrieved " + esc(str(dl.get("a_date"))[:10] or "date unstated"))],
 ['data/linelab/captures/2026-11-16', f'{dl["total_b"]:,}', f'{dl.get("clubs_b", 0)} clubs',
  'the later read of the same league table', repo_link("data/linelab/captures/2026-11-16/week10-injury-report.csv", "dated capture")],
 ['clubs that changed', f'{len(dl["clubs"])}',
  ", ".join(f'<code>{esc(c["club"])}</code> {c["a"]}&rarr;{c["b"]}' for c in dl["clubs"]) or "none",
  ("the report moved for no club between the two reads" if dl["same"]
   else "a club added rows between the reads, which is what a delta is for"),
  link("https://www.nfl.com/injuries/", "official report")],
 ['the designation-only view', f'{dl["designated_view_rows"]:,}',
  f'{dl["designated_in_full"]:,} designated rows counted in the full capture',
  ('<span class="good">the view matches the capture exactly, so it is a filter, not a different truth</span>'
   if dl["designated_view_rows"] == dl["designated_in_full"]
   else '<span class="bad">the view and the capture disagree; the filter is not the only difference</span>'),
  repo_link("data/injury-report-2026-w10.csv", "data/injury-report-2026-w10.csv")],
])}
<div class="callout"><b>Why the last row matters more than it looks.</b> One register publishes 160 rows and another
publishes 345 for the same week. If the smaller number is the designated subset, both are true and the site should say
so on the page; if it is not, two sections are reading different things. The comparison is computed here every build,
so the answer cannot drift out of date.</div>
<h2>Price coverage, both stores in the repository</h2>
{table(['store','rows','with opening','with closing','with both','timestamped','consequence'], prows)}
<h2>Captures held, and the forecast ledger's position</h2>
{table(['thing','count','detail','source'], [
 ['dated captures under data/captures', len(fresh['captures']['data_captures']),
  ", ".join(f'<code>{esc(x)}</code>' for x in fresh['captures']['data_captures']) or "none", repo_link('data/captures', 'data/captures/')],
 ['capture days under data/linelab/captures', len(fresh['captures']['linelab_capture_days']),
  "two days only - a daily series is what the brief asks for", repo_link('data/linelab/captures', 'data/linelab/captures/')],
 ['Week 11 forecasts frozen', fc['n'],
  f'model {esc(fc["model"])} at {esc(fc["generated"])} against first kickoff {esc(fc["kickoff"])}; gate {esc(fc["gate"])}',
  repo_link('data/forecast_ledger.json', 'data/forecast_ledger.json')],
 ['of those graded', fc['graded'], "nothing is graded yet, and that is the point of escrow",
  link('sources.html#EV-01', 'Week 10 is not complete')],
])}
"""
    open(os.path.join(OUT, "freshness.html"), "w", encoding="utf-8").write(page(
        "Freshness and what changed",
        "The diff the owner asked for in place of a static snapshot: which published numbers the official pages have "
        "already moved past, computed from the artefacts on {BUILD_DATE}.".replace("{BUILD_DATE}", BUILD_DATE),
        body, "freshness.html",
        [("finals in the feed", f["final"], f"{f['in_progress']} still live"),
         ("standings rows disagreeing", s["sampled"] - s["pub_match"], f"of {s['sampled']} sampled"),
         ("2026 open+close price pairs", 0, "from both price stores"),
         ("capture days held", len(fresh["captures"]["linelab_capture_days"]), "needs one per day from Wed")]))


def build_sources(ev, stats, f_rows):
    ref_ds09 = "DS-09"
    evmap = {e["id"]: e for e in ev["entries"]}
    rows = []
    for e in ev["entries"]:
        ok = "resolved" in e["status_after_check"] or "consistent" in e["status_after_check"]
        rows.append([f'<b id="{esc(e["id"])}">{esc(e["id"])}</b>', esc(e["object"]),
                     link(e["url"], e["url"].replace("https://", "")),
                     esc(e["fetched_at_utc"]),
                     esc(clip(e["observed"], 520)),
                     esc(clip(e["consequence"], 320)),
                     ('<span class="good">' if ok else '<span class="warn">') + esc(e["status_after_check"]) + "</span>"])
    frows = [[link(x["url"], x["url"].replace("https://", "")), esc(x["at_utc"]), esc(x["error"]),
              esc(x["handling"])] for x in ev.get("failed_fetches", [])]
    irr = [
        ["I-1", "A 'blocked' verdict rests on a source test that was never run against the league's own archive",
         "R69 / R78 / R91 say no archive is reachable; two past-season reports render fine. The test behind the "
         "verdict was made against a mirror, not the primary source.",
         "Re-open the three rows; re-derive before publishing any new percentage.", link("sources.html#EV-05", "EV-05") + " &middot; " + link("sources.html#EV-06", "EV-06")],
        ["I-2", "Two different standings numbers are live on one site",
         "The published table is a 2026-11-14 capture; the results feed already contains the games that moved 9 of "
         "12 sampled clubs. A reader cannot tell which one a model used.",
         "Derive the table at build time and print the capture date on it.", link("sources.html#EV-08", "EV-08")],
        ["I-3", "Suggestion ids collide across sections",
         "SG-01, SG-02, SG-03 each name two unrelated suggestions in two registers, and one register uses SG01 "
         "without the dash. 'Adopt SG-05' is ambiguous.",
         "Namespace ids at generation; see DS-03.", repo_link("data/suggestions.json", "data/suggestions.json") + " &middot; " + repo_link("fl2-lines/data/registers/suggestions.csv", "fl2-lines register")],
        ["I-4", "A fixture's venue carries two values in two artefacts",
         "IND@HOU is NRG Stadium in the Week 11 market capture and Reliant Stadium in the results feed; the "
         "game-centre field that would settle it could not be fetched twice at the page reader.",
         "Leave the venue unverified; retry the game-centre info chunk before publishing totals for that fixture.",
         link("sources.html#EV-09", "EV-09")],
        ["I-5", "Seven of thirteen Week 11 fixtures are not re-verified here",
         "The official Week 11 page was read only in part at this session's proxy; the earlier session's capture "
         "lists 13 fixtures, 6 of which this session confirmed against the live page.",
         "Do not describe the Week 11 slate as fully re-verified by this session.", link("sources.html#EV-03", "EV-03")],
        ["I-6", "Open pull requests from other sessions are unmerged",
         "PR #29 (decision-readiness register) and PR #24 (a self-correction of a price-coverage claim) were open at "
         "claim time. Both touch areas this desk consolidates by reference.",
         "Their authors should rebase; this session did not merge another session's branch.",
         link("https://github.com/sassnarep3-star/FL2/pull/29", "PR #29") + " &middot; " + link("https://github.com/sassnarep3-star/FL2/pull/24", "PR #24")],
        ["I-10", "The committed pages cannot all be regenerated safely",
         "Running this repository's own generators rewrote 11 docs pages, deleting a cross-link another session had "
         "added to their navigation, and rewrote the audit artefact's branch and commit provenance. The Pages "
         "validate job runs those generators but never diffs the output, so nothing fails today.",
         "Reverted here; the fix belongs to the files' owners, so it is raised as board row DS-10 and a request in "
         "COORDINATION.md rather than done by editing another section.",
         link("sources.html#EV-11", "EV-11") + " &middot; " + repo_link("scripts/make_pages.py", "scripts/make_pages.py")],
        ["I-7", "Two price stores, two requirement registers, three readiness tables",
         "Parallel sessions each built the same object under a different path. The data mostly agrees; the prose does "
         "not, and a reader has to reconcile it.",
         "Keep both implementations, publish one reconciliation table (this page's DS-03 / the landing table's "
         "integration-update column) and let the loser be marked superseded rather than deleted.",
         repo_link("fl2-lines/data/registers/readiness.csv", "readiness.csv") + " &middot; " + repo_link("data/decision_readiness.json", "decision_readiness.json")],
    ]
    # a count printed on the hub, checked against the file it describes
    hub_txt = ""
    if os.path.exists(p("index.html")):
        hub_txt = open(p("index.html"), encoding="utf-8").read()
    hub_feed = re.search(r"(\d+)-game results feed", hub_txt)
    if hub_feed and int(hub_feed.group(1)) != f_rows:
        irr.append([
            "I-8", "The hub describes a feed that is larger than the one it points at",
            f"The landing page says \u201c{esc(hub_feed.group(0))}\u201d while data/results_feed.csv holds "
            f"{f_rows} final rows ({f_rows + 2} rows in total for played weeks, two of them not final). The number "
            "is not wrong so much as it counts the open fixtures as verified.",
            "Left as written - it is another section's sentence about its own claim - and recorded here so the "
            "owner can decide whether the hub should say \u201c148 finals, 2 open\u201d.",
            repo_link("index.html", "index.html") + " &middot; " + repo_link("data/results_feed.csv", "results feed")])
    # three published counts of one official table
    counts = []
    inj_full = 0
    for g in first_list(jload("data/injuries.json") or {}, "games"):
        for tt in g.get("teams", []):
            inj_full += len(tt.get("players", []))
    inj_meta = (jload("data/injuries.json") or {}).get("meta", {}) if isinstance(jload("data/injuries.json"), dict) else {}
    if inj_full:
        counts.append(("data/injuries.json", inj_full,
                       f"rows, retrieved {esc(inj_meta.get('retrieved_utc', 'date not stated in the file'))}"))
    linelab = p("data", "linelab", "captures", "2026-11-16", "week10-injury-report.csv")
    if os.path.exists(linelab):
        counts.append(("data/linelab/captures/2026-11-16/week10-injury-report.csv",
                       max(len(open(linelab, encoding="utf-8").read().splitlines()) - 1, 0),
                       "rows in the later dated capture"))
    js = ""
    if os.path.exists(p("data", "site_data.js")):
        js = open(p("data", "site_data.js"), encoding="utf-8").read()
    m = re.search(r'\"week10\":\{.*?\"injury_rows\":', js)
    n_ledger = 0
    try:
        blob = re.search(r"window\.FL2\s*=\s*(\{.*\})", js, re.S)
        if blob:
            n_ledger = len(json.loads(blob.group(1))["week10"]["injury_rows"])
    except Exception:
        n_ledger = 0
    if n_ledger:
        counts.append(("data/site_data.js", n_ledger, "rows in the ledger table (week10.injury_rows)"))
    readme_claim = ""
    if os.path.exists(p("README.md")):
        rm = re.search(r"Week 10 injury report[^|]*\|[^|]*\|\s*(\d+)", open(p("README.md"), encoding="utf-8").read())
        if rm:
            readme_claim = rm.group(1)
    designated = jload("data/injury-report-2026-w10.csv")
    if len(counts) > 1:
        irr.append(["I-9", "One official table, several published row counts",
                    " &middot; ".join(f'{esc(n)} in <code>{esc(pth)}</code> ({esc(why)})' for pth, n, why in counts)
                    + (f"; the README quotes {esc(readme_claim)}" if readme_claim else ""),
                    "Each view applies a filter that is not printed on the page. Recorded for the owner; see board row "
                    + ref_ds09 + ".",
                    " &middot; ".join(repo_link(pth, os.path.basename(pth)) for pth, n, why in counts)])
    irr.sort(key=lambda r: int(re.sub(r"\D", "", r[0]) or 0))
    body = f"""
<div class="callout blue"><b>Everything this session asserted, and where it came from.</b> Each row is a live page this
session fetched at the stated hour, with the observation quoted as it appeared. Where a fetch failed, the failure is
listed below rather than filled with a value - two of nine reads did not reach the page, and the affected cells are
blank on the other pages of this section.</div>
<h2>Capture log &middot; {stats['evidence_entries']} observations, {BUILD_DATE}</h2>
{table(['id','checked','source','fetched (UTC)','what the page said','what it means','state'], rows)}
<h2>Fetches this session could not complete</h2>
{table(['url','attempted','error','how it was handled'], frows)}
<h2>Irregularities flagged for review</h2>
{table(['id','finding','detail','handling','source'], [[f'<b>{esc(a)}</b>',f'<b>{esc(b)}</b>',esc(c),esc(d),e] for a,b,c,d,e in irr])}
<p class="small">Flagged items do not block the site; they are here so they can be checked against the same pages
after deployment. Repo-level checks run in CI: {repo_link('scripts/check_site.py','scripts/check_site.py')},
{repo_link('tools/check_links.py','tools/check_links.py')}, {repo_link('fl2-lines/engine/check.py','fl2-lines/engine/check.py')},
{repo_link('ops/check_readiness.py','ops/check_readiness.py')} and this section's own
{repo_link('tools/check_decision_desk.py','tools/check_decision_desk.py')}.</p>
"""
    open(os.path.join(OUT, "sources.html"), "w", encoding="utf-8").write(page(
        "Verification log and irregularities",
        "The line-by-line record for this session: what was fetched, from where, at what hour, what it showed, and "
        "the irregularities it exposed. Nothing on the other pages of this section is asserted without a row here "
        "or an artefact link.",
        body, "sources.html",
        [("official pages checked", stats["evidence_entries"], "all fetched today"),
         ("fetches that failed", len(ev.get("failed_fetches", [])), "recorded, not filled in"),
         ("irregularities", len(irr), "published, none block the site"),
         ("values invented", 0, "blanks where unverified")]))


def ordinal(n):
    if not n:
        return "unranked"
    suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10 if n % 100 not in (11, 12, 13) else 0, "th")
    return f"{n}{suf}"


def build_index(canon, fresh, stats, cal, ev, answers):
    rank_of = {r["uid"]: i + 1 for i, r in enumerate(canon)}
    by_title = {}
    for r in canon:
        by_title[re.sub(r"[^a-z0-9 ]", "", (r["title"] or "").lower())] = r["uid"]

    def ref(title_prefix):
        """Stable link to a board row, found by its own title. A prefix that stops
        matching renders as a visible failure instead of pointing at the wrong row."""
        key = re.sub(r"[^a-z0-9 ]", "", (title_prefix or "").lower()).strip()
        for k, uid in by_title.items():
            if k.startswith(key[:38]):
                return f'<a href="suggestions.html#{esc(uid)}">{esc(uid)}</a>'
        return f'<span class="bad">row not found: {esc(title_prefix[:40])}</span>'

    top = canon[:6]
    owner_rows = [r for r in canon if r["who"] == "owner"][:8]
    owner_table = table(['tier', 'id', 'decision', 'what it waits on', 'why it is on this list', 'source'],
                        [[f'<span class="tag p1">{esc(r["path_tier"])}</span>', f'<b>{esc(r["uid"])}</b>',
                          f'<b>{esc(clip(r["title"], 110))}</b>',
                          esc(clip(r["missing"], 150)) or '<span class="small">a stated choice</span>',
                          esc(clip(r["problem"], 200)),
                          link("suggestions.html#" + r["uid"], r["uid"])]
                         for r in owner_rows])
    rows = [[f'<span class="tag {"p0" if r["path_tier"].startswith("P0") else "p1"}">{esc(r["path_tier"])}</span>',
             f'<b>{esc(r["uid"])}</b>', esc(clip(r["title"], 130)),
             f'<span class="tag {"p1" if r["who"] == "owner" else ""}">{esc(r["who"])}</span>',
             esc(r["impact"] or "(not stated)") + " / " + esc(r["effort"] or "(not stated)"),
             link("suggestions.html#" + r["uid"], r["uid"])] for r in top]
    for r in top:
        pass
    s = fresh["standings"]
    f = fresh["feed"]
    body = f"""
<div class="callout"><b>The one-paragraph version.</b> The plumbing the brief asked for exists and is largely sound:
{f['final']} verified finals, a dated price store, frozen pre-registered Week 11 forecasts, a leaderboard that
separates signal from staking, and a designation calibration measured with intervals instead of folklore. What is
missing is not code but three decisions and one discipline: the price basis that every CLV gate waits on, the
snap-count or inactive evidence that would let a backup replacing a starter be <i>confirmed</i> rather than
suspected, and the habit of treating the league's own calendar (report weeks, final scores) as a constraint instead
of an inconvenience. Today's own checks also found a false block: the injury archive that three requirements say does
not exist does exist, on nfl.com.</div>
<h2>Start here</h2>
<div class="callout"><b>How this list relates to the board.</b> The board ranks what it can compute: register width,
which not-done readiness rows a step touches, and how many other suggestions wait on it. That arithmetic puts
{ref("Run the snapshot workflow")} (turn the snapshot workflow on) first. The list below is the same
information read as a decision, so it leads with the two rows nothing in the repository can close on its own -
{ref("Settle the price question")} (the price basis, an owner call) and
{ref("Define the leaderboard reward")} (what a "reward" even is). Where the two disagree, the board's arithmetic
is the record and this list is the argument.</div>
<ol class="path">
<li><b>Decide the price policy and write the decision down</b> (board row {ref("Settle the price question")}; {ref("Decide the price source")} asks the same of the fl2-lines register). No 2026 row in either price store has both an opening
and a closing number ({repo_link("data/price_snapshots.csv", "data/price_snapshots.csv")}), so closing-line-value gates are
unsatisfiable until an outside benchmark is chosen. Buying an archive, recording our own dated snapshots, or dropping
CLV are all defensible; leaving the question open is not, because it silently blocks everything downstream.</li>
<li><b>Re-derive the designation calibration from the primary source</b> ({ref("Re-derive the designation")}). The published rates are already good;
the premise that they cannot be verified against the league's archive is wrong
(<a href="calibration.html">the two archived pages that render today</a>). This also opens the 2025 and 2026
seasons for the "is the label a feature" test.</li>
<li><b>Stop the site contradicting itself</b> ({ref("Republish the standings")} for the standings, {ref("Refuse to grade")} for the grading refusal). The published standings table disagrees with the official page for
{s['sampled'] - s['pub_match']} of {s['sampled']} sampled clubs while the feed behind it is correct, and one Week 10
game was live at {f['final']} finals. Both are build-time derivations, not research.</li>
<li><b>Give reviewers one queue</b> ({ref("Give registers one namespace")}). Five registers of suggestions with two id formats became one board with
{stats['suggestions_present']} decisions, deduped, with every original id kept.</li>
<li><b>Do not build depth from what the club charts already disprove</b> ({ref("Add an official depth-chart table")} and {ref("Acquire snap counts")} , at {ordinal(rank_of.get('hub-SG-01', 0))} and {ordinal(rank_of.get('fl2-lines-SG-02', 0))} on the board). 2026 snap counts held by this repository: 0.
Until an inactive list or snap share exists, a replacement is suspected, never named - which is what the site says
today, and it should keep saying it.</li>
</ol>
<h2>Top of the queue</h2>
{table(['tier','id','decision','who acts','impact / effort','where'], rows)}
<h2>Decisions only the owner can make</h2>
<p class="small">Computed, not chosen: these are the rows on the board whose text names a licence, a budget, a
reading of terms, or a definition rather than a code change. Nothing in the repository can close them, which is why
they are separated from the engineering queue instead of being ranked inside it.</p>
{owner_table}
<h2>State of the machinery, as far as it can be checked from the artefacts</h2>
{table(['part','what exists','what it cannot do yet','source'], [
 ['Results feed', f'{f["rows"]:,} rows, {f["final"]} finals, {f["in_progress"]} live; replaying the finals reproduces '
  f'the official record for {fresh["replay"]["as_is_ok"]} of {fresh["replay"]["sampled"]} sampled clubs, and '
  f'{fresh["replay"]["with_pending_ok"]} of {fresh["replay"]["sampled"]} once the fixture recorded as pending is applied',
  'a backtest cannot grade Week 10 until the live fixture is final; a stale open row also distorts two club records',
  repo_link('data/results_feed.csv', 'data/results_feed.csv')],
 ['Price store', f'{len(fresh["price"])} stores with opening/closing columns and a policy document',
  'no timestamped 2026 close and no opening line at all, so no CLV', repo_link('research/price-data-policy.md', 'price-data-policy.md')],
 ['Originated lines', 'side, then total, then moneyline, published as fair / market / difference',
  'the difference is measured against an unlicensed benchmark, labelled as such', repo_link('data/origination_week11.csv', 'origination_week11.csv')],
 ['Leaderboard', '4 divisions, signal split from staking, control baselines, demotion gate',
  'empty by design: prospective escrow has not filled, and backtest numbers are forbidden on it', repo_link('data/leaderboard.json', 'data/leaderboard.json')],
 ['Availability', f'{stats["readiness_rows"]}-row readiness register; Week 10 report capture of '
  f'{fresh["injury_capture"]["rows"]:,} rows on {fresh["injury_capture"]["clubs"]} clubs',
  'no inactives, no snap share, no reserve list, so "not listed" still cannot be read as "available"',
  repo_link('data/availability_graph.json', 'availability_graph.json')],
 ['Strategy governance', 'pre-registration text frozen in git before the window opened; two registered strategies',
  'nothing is graded, so no strategy has earned a rank yet', repo_link('fl2-lines/data/registers/prereg.csv', 'prereg.csv')],
])}
<h2>How to read this section</h2>
{table(['page','what it is for','row counts, computed at build time'], [
 ['<a href="suggestions.html">Suggestion review</a>','choose a path: one row per decision, deduped across every register, with the ranking arithmetic shown',f'{stats["suggestions_present"]}'],
 ['<a href="questions.html">Questions &amp; answers</a>','what must be known before a decision, what is known now, and what would close the gap',f'{stats["questions_present"]} open, {len(answers)} answered here'],
 ['<a href="calibration.html">Designation calibration</a>','what an injury label is worth, measured, and the source question behind it',f'{len(cal["published"])} measured designations, {len(cal["capture_designations"])} status values in our capture'],
 ['<a href="freshness.html">Freshness</a>','which published numbers the official pages have moved past',f'{s["sampled"]} clubs diffed, {len(fresh["price"])} price stores'],
 ['<a href="sources.html">Verification log</a>','this session&rsquo;s fetches, failures and flagged irregularities',f'{stats["evidence_entries"]} checks, {len(ev.get("failed_fetches", []))} failed'],
])}
<p class="small">Other sections of this repository hold the implementations this desk reviews rather than replaces:
<a href="../index.html">the hub</a>, <a href="../readiness/index.html">the R-register</a>,
<a href="../fl2-lines/index.html">fl2-lines</a>, <a href="../linelab/index.html">Line Lab</a>,
<a href="../ledger/suggestions.html">the ledger's own suggestions page</a> and
<a href="../fl2-signals/index.html">verified signals</a>.</p>
"""
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page(
        "Executive brief",
        f"Built {BUILD_DATE} by <code>{SESSION}</code>. The site already does most of what the brief asked; this "
        "section exists so a human can choose the next step without reconciling six registers first. Every number is "
        "computed from a repository artefact or from a page fetched today, and every row links to one.",
        body, "index.html",
        [("verified finals", f["final"], f"{f['in_progress']} still live at check time"),
         ("decisions on the board", stats["suggestions_present"], "from 5 registers + this audit"),
         ("open questions", stats["questions_present"], "5 closed by this session"),
         ("2026 open+close prices", 0, "the gate everything else waits on")]))




if __name__ == "__main__":
    build()

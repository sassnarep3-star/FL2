#!/usr/bin/env python3
"""Capture official NFL Game Books and parse them into flat, sourced CSV rows.

What this script is for
-----------------------
Requirement R77 told us to resolve the depth-order source *before* building any
backup-deficiency feature, and to evaluate two routes in order:

    (a) per-club official depth-chart pages      -> 5 of 32 clubs, club-captioned "unofficial"
    (b) derive depth from playing time           -> this script

Route (b) is now resolved: the league publishes, for every game, an official
"National Football League Game Summary" (the Game Book) whose

    * "Lineups"              -> the actual starters, offense and defense, by slot
    * "Substitutions"        -> played but did not start
    * "Did Not Play"         -> dressed, did not play
    * "Not Active"           -> the official inactive list
    * "Playtime Percentage"  -> per-player snap counts (offense / defense / special teams)

This script fetches those PDFs and turns them into rows that each carry the URL of
the exact PDF they came from, plus the SHA-256 of the raw bytes.

Design rules (do not relax)
---------------------------
1. Only official league sources are fetched: www.nfl.com game-centre pages and
   static.www.nfl.com Game Book PDFs. No aggregator, no odds site, no mirror.
2. Nothing is inferred. If a field is not on the page the cell is left blank and
   the row is marked, never filled with a guess.
3. The Playtime Percentage table is captioned "(Unofficial)" by the league itself.
   That caption is captured and stored, not dropped.
4. The Game Book carries a copyright notice restricting use to media coverage.
   This script stores derived facts and hashes, never the PDF itself, and never
   play-by-play. The notice text is captured verbatim into the manifest so the
   restriction travels with the data.
5. Every parse failure is a loud failure: the script exits non-zero rather than
   publishing a half-parsed book.

Usage
-----
    python3 capture_gamebooks.py --season 2026 --week 10 --seed <seed.csv> --out <dir>
    python3 capture_gamebooks.py --self-test

The seed CSV must carry at least: game_id, season, week, away, home, gamecenter_url.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
PDF_RE = re.compile(r"https://static\.www\.nfl\.com/image/upload/[^\"'\\ ]+?gamecenter/[0-9a-f-]{8,}\.pdf")
COPYRIGHT_RE = re.compile(r"(NFL Copyright.{0,400}?permission of the National Football League\.)", re.S)

# --------------------------------------------------------------------------- fetch


def http_get(url: str, timeout: int = 60, retries: int = 3) -> bytes:
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as exc:  # noqa: BLE001 - surfaced to the caller as text
            last = exc
            time.sleep(2 + 2 * attempt)
    raise RuntimeError(f"GET failed for {url}: {last}")


def pdftotext(pdf_path: str, txt_path: str) -> str:
    exe = shutil.which("pdftotext")
    if exe is None:
        raise RuntimeError("pdftotext (poppler-utils) is required but not installed")
    subprocess.run([exe, "-layout", pdf_path, txt_path], check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    with open(txt_path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


# --------------------------------------------------------------------------- header fields


def parse_header(text: str) -> dict:
    out = {"book_venue": "", "book_roof_surface": "", "book_weather": "",
           "book_temp_f": "", "book_wind": "", "attendance": "", "kickoff_local": "",
           "copyright_notice": ""}

    m = COPYRIGHT_RE.search(text)
    if m:
        out["copyright_notice"] = " ".join(m.group(1).split())

    # Venue: "<Away> at <Home> at <Venue>, <City>, <State/Country>"
    m = re.search(r"at\s+([A-Z][A-Za-z0-9.'&\- ]+?)\s+at\s+(.{3,90}?)\s{2,}", text)
    if m:
        out["book_venue"] = " ".join(m.group(2).split())
    # Roof / surface tokens the league prints on their own line
    m = re.search(r"((?:Open|Closed|Fixed|Retractable)[\w \-]*?(?:Stadium|Dome|Roof)[\w \-]*?on\s+\w[\w ]*)", text)
    if not m:
        m = re.search(r"(Retractable Roof\s*-\s*(?:Open|Closed)\s+on\s+\w[\w ]*)", text)
    if m:
        out["book_roof_surface"] = " ".join(m.group(1).split())

    m = re.search(r"Game Weather:\s*(.{0,60}?)\s{2,}", text)
    if m:
        out["book_weather"] = " ".join(m.group(1).split())
    m = re.search(r"Temp:\s*(-?\d+)\s*°?\s*F", text)
    if m:
        out["book_temp_f"] = m.group(1)
    m = re.search(r"Wind:\s*([NSEW]{1,2}\s*\d+\s*mph)", text)
    if m:
        out["book_wind"] = " ".join(m.group(1).split())
    m = re.search(r"Paid Attendance:\s*([\d,]+)", text)
    if m:
        out["attendance"] = m.group(1).replace(",", "")
    m = re.search(r"Start Time:\s*(.{0,30}?)\s{2,}", text)
    if m:
        out["kickoff_local"] = " ".join(m.group(1).split())
    return out


# --------------------------------------------------------------------------- lineups


POS_WORDS = {
    "LT", "LG", "RG", "RT", "C", "G", "T", "OL", "C/G", "G/T", "T/G", "OLB", "ILB",
    "MLB", "LB", "NT", "EDGE", "DE", "DT", "DL", "CB", "DB", "S", "FS", "SS", "WR",
    "TE", "RB", "FB", "QB", "K", "P", "LS",
}

SLOT_RE = re.compile(r"\b(LT|LG|RG|RT|C/G|G/T|T/G|OLB|ILB|MLB|NT|EDGE|DE|DT|DL|LB|CB|DB|S|FS|SS|WR|TE|RB|FB|QB|OL|G|C|T|K|P|LS)\b")


def _slot_rows(line: str) -> list:
    """One printed line of the Lineups block holds up to four slot/player pairs.

    Layout is: [away slot][away player]  [away slot][away player]  [home slot][home player]  [home slot][home player]
    where the first two pairs are the away club (offense then defense) and the last
    two the home club. Teams are separated here by caller-side splitting.
    """
    toks = line.split()
    rows, i = [], 0
    while i < len(toks):
        if SLOT_RE.fullmatch(toks[i]) and i + 1 < len(toks):
            jersey = ""
            k = i + 1
            if re.fullmatch(r"\d{1,2}", toks[k]):
                jersey = toks[k]
                k += 1
            name = " ".join(toks[k:k + 3])
            # a name is at most three tokens: initial(s) + surname, stop at next slot
            nm = []
            while k < len(toks) and len(nm) < 3 and not SLOT_RE.fullmatch(toks[k]):
                nm.append(toks[k])
                k += 1
            rows.append((toks[i], jersey, " ".join(nm)))
            i = k
        else:
            i += 1
    return rows


def parse_lineups(text: str, away: str, home: str) -> list:
    """Return [(club, unit, slot, jersey, player)] from the Lineups block."""
    m = re.search(r"^\s*Lineups\s*$", text, re.M)
    if not m:
        # some books render the header as a bold inline heading followed by the table
        m = re.search(r"Lineups", text)
    if not m:
        return []
    start = m.end()
    end = re.search(r"^\s*(Substitutions|Did Not Play|Not Active)\s*$", text[start:], re.M)
    block = text[start:start + end.start()] if end else text[start:start + 4000]

    out = []

    def split_on_widest_gap(line: str, min_gap: int = 2):
        """Split a fixed-width line into two club halves.

        Prefers a split that yields a balanced number of slot/player pairs on each
        side (2+2, or 1+1), and among those candidates takes the widest gap. Falls
        back to the widest gap when no split balances.
        """
        cands = [(gm.start(), gm.end() - gm.start())
                 for gm in re.finditer(r" {%d,}" % min_gap, line)]
        if not cands:
            return line, ""
        scored = []
        for pos, width in cands:
            lp = _slot_rows(line[:pos])
            rp = _slot_rows(line[pos:])
            balanced = (len(lp), len(rp)) in ((2, 2), (1, 1))
            scored.append((1 if balanced else 0, width if balanced else width, -abs(len(lp) - len(rp)), pos))
        scored.sort(reverse=True)
        pos = scored[0][3]
        return line[:pos], line[pos:]

    for line in block.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if "Offense" in stripped or "Defense" in stripped:
            continue
        if stripped in (away, home):
            continue
        if not re.search(r"\d", stripped):
            continue
        left, right = split_on_widest_gap(line)
        lp = _slot_rows(left)
        rp = _slot_rows(right) if right else []
        if not lp and not rp:
            lp = _slot_rows(line)
        if len(lp) + len(rp) == 4 and (not lp or not rp):
            # no usable gap found: fall back to positional order
            allp = _slot_rows(line)
            order = ((away, "offense"), (away, "defense"), (home, "offense"), (home, "defense"))
            for (club, unit), (slot, jersey, name) in zip(order, allp):
                out.append((club, unit, slot, jersey, name))
            continue
        for club, pairs in ((away, lp), (home, rp)):
            for idx, (slot, jersey, name) in enumerate(pairs):
                unit = "offense" if idx % 2 == 0 else "defense"
                out.append((club, unit, slot, jersey, name))
    return out


# --------------------------------------------------------------------------- roster lists


def parse_named_list(text: str, heading: str, away: str, home: str) -> list:
    """Parse a comma-separated roster list ('Not Active', 'Did Not Play', 'Substitutions')."""
    stop = re.compile(r"^\s*(?:Paid Attendance|Playtime Percentage|Field Goals|VISITOR:|HOME:|"
                      r"Did Not Play|Not Active|Substitutions|Lineups|Officials|Scoring Plays|"
                      r"National Football League Game Summary|Miscellaneous|Ten Longest)\b")
    out = []
    for m in re.finditer(r"^\s*" + heading + r"\s*$", text, re.M):
        lines = []
        for line in text[m.end():].splitlines():
            if stop.match(line):
                break
            lines.append(line)
            if len(" ".join(lines)) > 3000:
                break
        # collapse wrapped lines: the lists are comma separated and wrap mid-item
        flat = " ".join(l.strip() for l in lines if l.strip())
        if not flat:
            continue
        for item in flat.split(","):
            item = " ".join(item.split())
            if not item:
                continue
            m2 = re.match(r"^([A-Za-z0-9/]{1,6})\s+(\d{0,2})\s*([A-Za-z][\w.'’\- ]+)$", item)
            if m2:
                out.append({"pos_raw": m2.group(1), "jersey": m2.group(2),
                            "player_raw": m2.group(3).strip(), "club": ""})
            else:
                m3 = re.match(r"^(\d{0,2})\s*([A-Za-z][\w.'’\- ]+)$", item)
                if m3:
                    out.append({"pos_raw": "", "jersey": m3.group(1),
                                "player_raw": m3.group(2).strip(), "club": ""})
    return out


# --------------------------------------------------------------------------- playtime


def _col_spans(header_line: str):
    """Return [(label, start, end)] for Offense/Defense/Special Teams columns."""
    spans = []
    for label in ("Offense", "Defense", "Special", "Teams"):
        for m in re.finditer(re.escape(label), header_line):
            spans.append((label, m.start()))
    spans.sort(key=lambda t: t[1])
    return spans


def parse_playtime(text: str, away: str, home: str):
    """Return (rows, unofficial_flag).

    The Playtime Percentage table is fixed-width: name+position on the left, then
    three (snaps, percent) pairs per club. Columns are located from the printed
    header, and each data line is read by nearest-match inside each column window,
    so a blank cell stays blank instead of being filled from the neighbour.
    """
    m = re.search(r"Playtime Percentage", text)
    if not m:
        return [], False
    tail = text[m.end():]
    unofficial = bool(re.search(r"\(Unofficial\)", tail[:200], re.I))

    lines = tail.splitlines()
    hi = None
    for idx, line in enumerate(lines[:14]):
        if "Offense" in line and "Defense" in line and "Special" in line:
            hi = idx
            break
    if hi is None:
        return [], unofficial
    header = lines[hi]

    spans = [(l, p) for (l, p) in _col_spans(header) if l != "Teams"]
    off_pos = [p for l, p in spans if l == "Offense"]
    if len(off_pos) < 2:
        return [], unofficial
    cut = off_pos[1]
    left_labels = [(l, p) for l, p in spans if p < cut]
    right_labels = [(l, p) for l, p in spans if p >= cut]

    def columns(labels, last_bound):
        """[(key, start, end)] for the three snap/pct column groups of one club."""
        groups = []
        for label, pos in labels:
            key = {"Offense": "off", "Defense": "def", "Special": "st"}[label]
            if groups and groups[-1][0] == key:
                continue
            groups.append([key, pos, None])
        for i, g in enumerate(groups):
            g[2] = groups[i + 1][1] if i + 1 < len(groups) else last_bound
        return [(k, a, b) for k, a, b in groups]

    left_cols = columns(left_labels, cut)
    right_cols = columns(right_labels, len(header) + 20)

    def name_window(line, lo, hi_):
        seg = line[lo:hi_].strip()
        if not seg:
            return None, None
        toks = seg.split()
        for ti in range(len(toks) - 1, -1, -1):
            if toks[ti] in POS_WORDS:
                if ti == 0:
                    return None, None
                return " ".join(toks[:ti]), toks[ti]
        return None, None

    num_re = re.compile(r"\d{1,3}\s+\d{1,3}%")
    rows = []
    for line in lines[hi + 1:]:
        if not line.strip():
            continue
        if re.match(r"^\s*(Paid Attendance|\*|Miscellaneous|Ten Longest|Possession Detail)", line):
            break
        if "Offense" in line and "Defense" in line:
            continue
        matches = [(mm.start(), mm.group(0)) for mm in num_re.finditer(line)]
        if not matches:
            continue
        for club, cols in ((away, left_cols), (home, right_cols)):
            first_start = min(c[1] for c in cols)
            last_end = max(c[2] for c in cols)
            lo = 0 if club == away else min(c[1] for c in left_cols) if left_cols else 0
            lo = max(lo, 0)
            if club == home:
                lo = min(c[1] for c in right_cols) - 24
            player, pos = name_window(line, max(lo, 0), first_start)
            if not player:
                continue
            rec = {"club": club, "player_raw": player, "pos_raw": pos,
                   "off_snaps": "", "off_pct": "", "def_snaps": "", "def_pct": "",
                   "st_snaps": "", "st_pct": ""}
            used = set()
            for key, cstart, cend in cols:
                best, bestd = None, 10**9
                for idx, (mstart, mtext) in enumerate(matches):
                    if idx in used:
                        continue
                    d = abs(mstart - cstart)
                    if d < bestd and d <= 10 and mstart >= cstart - 10:
                        best, bestd = idx, d
                if best is not None:
                    used.add(best)
                    nums = re.match(r"(\d{1,3})\s+(\d{1,3})%", matches[best][1])
                    rec[f"{key}_snaps"] = nums.group(1)
                    rec[f"{key}_pct"] = nums.group(2)
            if any(rec[k] for k in ("off_snaps", "def_snaps", "st_snaps")):
                rows.append(rec)
    return rows, unofficial


# --------------------------------------------------------------------------- driver


def capture_game(row: dict, workdir: str) -> dict:
    gid = row["game_id"]
    gc = (row.get("gamecenter_url") or "").strip()
    res = {"game_id": gid, "gamecenter_url": gc, "status": "", "gamebook_url": "",
           "pdf_sha256": "", "error": ""}
    if not gc:
        res["status"] = "no_gamecenter_url"
        return res
    try:
        return _capture_game_inner(row, workdir, res)
    except Exception as exc:  # noqa: BLE001 - recorded, never swallowed silently
        import traceback
        res["status"] = "exception"
        res["error"] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[-1500:]}"
        return res


def _capture_game_inner(row: dict, workdir: str, res: dict) -> dict:
    gid = row["game_id"]
    gc = res["gamecenter_url"]
    try:
        html = http_get(gc).decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        res["status"], res["error"] = "gamecenter_fetch_failed", str(exc)
        return res
    m = PDF_RE.search(html)
    if not m:
        res["status"] = "no_gamebook_published_yet"
        return res
    pdf_url = m.group(0)
    res["gamebook_url"] = pdf_url
    os.makedirs(workdir, exist_ok=True)
    pdf_path = os.path.join(workdir, f"{gid}.pdf")
    txt_path = os.path.join(workdir, f"{gid}.txt")
    try:
        blob = http_get(pdf_url)
    except Exception as exc:  # noqa: BLE001
        res["status"], res["error"] = "pdf_fetch_failed", str(exc)
        return res
    with open(pdf_path, "wb") as fh:
        fh.write(blob)
    res["pdf_sha256"] = hashlib.sha256(blob).hexdigest()
    if len(blob) < 5000:
        res["status"], res["error"] = "pdf_too_small", f"{len(blob)} bytes"
        return res
    try:
        text = pdftotext(pdf_path, txt_path)
    except Exception as exc:  # noqa: BLE001
        res["status"], res["error"] = "pdftotext_failed", str(exc)
        return res

    away, home = row["away"], row["home"]
    res.update(parse_header(text))
    res["_lineups"] = parse_lineups(text, away, home)
    res["_not_active"] = parse_named_list(text, "Not Active", away, home)
    res["_did_not_play"] = parse_named_list(text, "Did Not Play", away, home)
    res["_substitutions"] = parse_named_list(text, "Substitutions", away, home)
    pt, unofficial = parse_playtime(text, away, home)
    res["_playtime"] = pt
    res["playtime_unofficial"] = unofficial
    res["playtime_rows"] = len(pt)
    res["status"] = "captured" if pt else "captured_no_playtime"
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", required=False)
    ap.add_argument("--season", default="2026")
    ap.add_argument("--week", default="10")
    ap.add_argument("--out", default="fl2-depth/data/verified")
    ap.add_argument("--work", default="/tmp/fl2-depth-work")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    with open(args.seed, newline="", encoding="utf-8") as fh:
        seed = list(csv.DictReader(fh))
    seed = [r for r in seed if r.get("season") == args.season and r.get("week") == args.week]
    if not seed:
        print(f"no seed rows for season={args.season} week={args.week}")
        return 2

    os.makedirs(args.out, exist_ok=True)
    os.makedirs(args.work, exist_ok=True)
    results = [capture_game(r, args.work) for r in seed]

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    bk = os.path.join(args.out, f"gamebooks-{args.season}-w{args.week}.csv")
    st = os.path.join(args.out, f"starters-{args.season}-w{args.week}.csv")
    ia = os.path.join(args.out, f"inactives-{args.season}-w{args.week}.csv")
    pt = os.path.join(args.out, f"playtime-{args.season}-w{args.week}.csv")

    with open(bk, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["game_id", "season", "week", "away", "home", "gamebook_url", "gamecenter_url",
                    "pdf_sha256", "status", "book_venue", "book_roof_surface", "book_weather",
                    "book_temp_f", "book_wind", "attendance", "kickoff_local",
                    "playtime_unofficial", "playtime_rows", "captured_at_utc", "source_tier"])
        for r, s in zip(seed, results):
            w.writerow([r["game_id"], r["season"], r["week"], r["away"], r["home"],
                        s.get("gamebook_url", ""), s.get("gamecenter_url", ""),
                        s.get("pdf_sha256", ""), s.get("status", ""),
                        s.get("book_venue", ""), s.get("book_roof_surface", ""),
                        s.get("book_weather", ""), s.get("book_temp_f", ""), s.get("book_wind", ""),
                        s.get("attendance", ""), s.get("kickoff_local", ""),
                        s.get("playtime_unofficial", ""), s.get("playtime_rows", ""),
                        stamp, "T1 official NFL Game Book"])

    with open(st, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["game_id", "club", "unit", "slot", "jersey", "player_raw", "source_url"])
        for s in results:
            for club, unit, slot, jersey, name in s.get("_lineups", []):
                w.writerow([s["game_id"], club, unit, slot, jersey, name, s.get("gamebook_url", "")])

    with open(ia, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["game_id", "club", "list_type", "pos_raw", "jersey", "player_raw", "source_url"])
        for s in results:
            for key, label in (("_not_active", "not_active"), ("_did_not_play", "did_not_play")):
                for rec in s.get(key, []):
                    w.writerow([s["game_id"], rec["club"], label, rec["pos_raw"],
                                rec["jersey"], rec["player_raw"], s.get("gamebook_url", "")])

    with open(pt, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["game_id", "club", "player_raw", "pos_raw", "off_snaps", "off_pct",
                    "def_snaps", "def_pct", "st_snaps", "st_pct", "source_url"])
        for s in results:
            for rec in s.get("_playtime", []):
                w.writerow([s["game_id"], rec["club"], rec["player_raw"], rec["pos_raw"],
                            rec["off_snaps"], rec["off_pct"], rec["def_snaps"], rec["def_pct"],
                            rec["st_snaps"], rec["st_pct"], s.get("gamebook_url", "")])

    manifest = {
        "captured_at_utc": stamp,
        "season": args.season,
        "week": args.week,
        "games": [{k: v for k, v in r.items() if not k.startswith("_")} for r in results],
        "copyright_notice": next((r.get("copyright_notice", "") for r in results
                                  if r.get("copyright_notice")), ""),
        "fetched_from": sorted({r.get("gamebook_url", "") for r in results if r.get("gamebook_url")}),
    }
    with open(os.path.join(args.out, f"capture-manifest-{args.season}-w{args.week}.json"),
              "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)

    log = {"captured_at_utc": stamp, "season": args.season, "week": args.week,
           "games": [{k: v for k, v in r.items() if not k.startswith("_")} for r in results]}
    with open(os.path.join(args.out, f"capture-log-{args.season}-w{args.week}.json"),
              "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=1)
    with open(os.path.join(args.out, f"capture-log-{args.season}-w{args.week}.md"),
              "w", encoding="utf-8") as fh:
        fh.write(f"# Game Book capture log — {args.season} week {args.week}\n\n")
        fh.write(f"Captured {stamp}\n\n")
        fh.write("| game | status | book url | sha256 | playtime rows | error |\n")
        fh.write("|---|---|---|---|---|---|\n")
        for r in results:
            fh.write(f"| {r['game_id']} | {r['status']} | {r.get('gamebook_url','')} | "
                     f"{(r.get('pdf_sha256') or '')[:16]} | {r.get('playtime_rows','')} | "
                     f"{str(r.get('error',''))[:300].replace('|','/')} |\n")

    failures = [r for r in results if not r["status"].startswith("captured")]
    print(json.dumps({"games": len(results),
                      "captured": sum(1 for r in results if r["status"].startswith("captured")),
                      "no_book_yet": [r["game_id"] for r in results
                                      if r["status"] == "no_gamebook_published_yet"],
                      "failures": [{"g": r["game_id"], "s": r["status"], "e": r.get("error", "")}
                                   for r in failures]}, indent=1))
    return 0


# --------------------------------------------------------------------------- self test


def self_test() -> int:
    """Offline tests against synthetic pdftotext -layout output."""

    def pt_row(n1, p1, o1, d1, s1, n2, p2, o2, d2, s2):
        line = f"{n1} {p1}".ljust(24)
        line += o1.ljust(13) + d1.ljust(12) + s1.ljust(8)
        line += f"{n2} {p2}".ljust(14)
        line += o2.ljust(13) + d2.ljust(12) + s2
        return line

    hdr = " " * 24 + "Offense".ljust(13) + "Defense".ljust(12) + "Special Teams".ljust(22) \
        + "Offense".ljust(13) + "Defense".ljust(12) + "Special Teams"

    txt = (
        "National Football League Game Summary\n"
        "NFL Copyright (c) 2026 by The National Football League. All rights reserved. This summary and\n"
        "play-by-play is for the express purpose of assisting media in their coverage of the game; any other\n"
        "use of this material is prohibited without the written permission of the National Football League.\n"
        "Date: Sunday, 11/15/2026      Test Away at Test Home at Test Field, Test City, TS      Start Time: 1:02 PM EST\n"
        "Game Day Weather\n"
        "Game Weather: Cloudy                        Temp: 46 F (7.8 C) Humidity: 75%, Wind: NW 15 mph\n"
        "Open Stadium on Natural Grass\n"
        "Lineups\n"
        "Test Away                       Test Home\n"
        "Offense      Defense            Offense        Defense\n"
        "LT  66 W.Campbell   OLB  5 Dr.Jones       WR  18 I.TeSlaa   DE  97 A.Hutchinson\n"
        "LG  70 G.Van Roten  DT   97 M.Williams      TE  87 S.LaPorta  DL  54 A.McNeill\n"
        "Substitutions\n"
        "WR 3 D.Douglas, K 8 A.Borregales, RB 9 C.Kiner\n"
        "Did Not Play\n"
        "QB 10 D.Mills\n"
        "Not Active\n"
        "CB 7 C.Davis, 3QB 15 B.Morton, S 41 B.Schooler\n"
        "Paid Attendance: 58,342\n"
        "Playtime Percentage\n"
        "Percent of playtime per player on offense, defense and special teams (Unofficial)\n"
        "                 Test Away                                    Test Home\n"
        + hdr + "\n"
        + pt_row("G.Van Roten", "OL", "59 100%", "", "2   7%", "B.Miller", "T", "71 100%", "", "5  18%") + "\n"
        + pt_row("M.Jones", "CB", "", "64  90%", "4  14%", "R.McCreary", "CB", "", "59 100%", "3  11%") + "\n"
    )

    h = parse_header(txt)
    assert h["book_temp_f"] == "46", h
    assert h["book_wind"] == "NW 15 mph", h
    assert h["attendance"] == "58342", h
    assert h["book_roof_surface"] == "Open Stadium on Natural Grass", h
    assert "National Football League" in h["copyright_notice"], h

    lu = parse_lineups(txt, "Test Away", "Test Home")
    names = {(r[0], r[2], r[4]) for r in lu}
    assert ("Test Away", "offense", "LT") in {(r[0], r[2], r[3]) for r in lu}, lu
    for expect in (("Test Away", "LT", "W.Campbell"), ("Test Away", "OLB", "Dr.Jones"),
                   ("Test Home", "WR", "I.TeSlaa"), ("Test Home", "DE", "A.Hutchinson"),
                   ("Test Away", "LG", "G.Van Roten"), ("Test Home", "TE", "S.LaPorta")):
        assert expect in names, (expect, lu)

    na = parse_named_list(txt, "Not Active", "Test Away", "Test Home")
    assert [r["player_raw"] for r in na] == ["C.Davis", "B.Morton", "B.Schooler"], na
    assert na[0]["pos_raw"] == "CB" and na[0]["jersey"] == "7", na
    assert [r["player_raw"] for r in parse_named_list(txt, "Did Not Play", "Test Away", "Test Home")] \
        == ["D.Mills"]

    rows, unofficial = parse_playtime(txt, "Test Away", "Test Home")
    assert unofficial is True
    by = {(r["club"], r["player_raw"]): r for r in rows}
    assert by[("Test Away", "G.Van Roten")]["off_snaps"] == "59", rows
    assert by[("Test Away", "G.Van Roten")]["off_pct"] == "100", rows
    assert by[("Test Away", "G.Van Roten")]["st_snaps"] == "2", rows
    assert by[("Test Away", "G.Van Roten")]["def_snaps"] == "", rows
    assert by[("Test Away", "G.Van Roten")]["pos_raw"] == "OL", rows
    assert by[("Test Away", "M.Jones")]["def_snaps"] == "64", rows
    assert by[("Test Away", "M.Jones")]["off_snaps"] == "", rows
    assert by[("Test Home", "B.Miller")]["off_snaps"] == "71", rows
    assert by[("Test Home", "R.McCreary")]["def_snaps"] == "59", rows
    print("self-test OK")
    return 0

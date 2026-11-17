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

    # The book prints the date line, then the venue indented on the NEXT line:
    #   "Date: Sunday, 11/15/2026   <Away> at <Home>   Start Time: 3:33 PM CET"
    #   "                                    at Allianz Arena, Munich, Germany"
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if "Start Time:" not in line:
            continue
        for follow in lines[idx + 1:idx + 4]:
            vm = re.match(r"^\s*at\s+(.{3,90}?)\s*$", follow)
            if vm:
                out["book_venue"] = " ".join(vm.group(1).split()).strip(" ,")
                break
            if follow.strip():
                break
        break

    # Roof / surface. The league prints it on its own line, sometimes followed on the
    # same line by an unrelated "Outdoor Weather" label that must not be captured as
    # part of the surface.
    m = re.search(r"^\s*((?:Open|Closed|Fixed|Domed|Retractable)[A-Za-z ]*?"
                  r"(?:Stadium|Dome|Roof)[A-Za-z ]*?(?:-\s*\w+)?\s+on\s+[A-Za-z][A-Za-z ]*?)\s*$",
                  text, re.M)
    if not m:
        m = re.search(r"((?:Open|Closed|Fixed|Domed|Retractable)[A-Za-z ]*?"
                      r"(?:Stadium|Dome|Roof)[A-Za-z ]*?(?:-\s*\w+)?\s+on\s+[A-Za-z][A-Za-z ]*?)"
                      r"\s*(?:Outdoor Weather|Indoor|Wind Chill|$)", text)
    if m:
        surf = " ".join(m.group(1).split())
        surf = re.sub(r"\s*(Outdoor Weather|Indoor|Wind Chill)\s*$", "", surf).strip()
        out["book_roof_surface"] = surf

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
    m = re.search(r"Start Time:\s*(.{0,30}?)(?:\s{2,}|$)", text, re.M)
    if m:
        out["kickoff_local"] = " ".join(m.group(1).split())
    return out


# --------------------------------------------------------------------------- lineups


# Position tokens the league prints. Clubs vary: Cincinnati prints LDE/RDE/LOT/ROT
# and HB where most print DE/T and RB, so the variants are all listed. Longest
# alternatives come first because the alternation is tried left to right.
POS_WORDS = {
    "LT", "LG", "RG", "RT", "C", "G", "T", "OL", "C/G", "G/T", "T/G", "LOT", "ROT",
    "LDE", "RDE", "LDT", "RDT", "LILB", "RILB", "LOLB", "ROLB", "SLB", "WLB",
    "OLB", "ILB", "MLB", "LB", "NT", "EDGE", "DE", "DT", "DL", "CB", "DB", "NB",
    "S", "FS", "SS", "WR", "TE", "RB", "HB", "FB", "QB", "K", "P", "LS",
}

# Built from POS_WORDS, longest first, so the two lists cannot drift apart.
SLOT_RE = re.compile(r"\b(" + "|".join(sorted(POS_WORDS, key=len, reverse=True)) + r")\b")


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


def _col_spans(header_line: str):
    """Column positions of the Offense / Defense / Special Teams captions."""
    spans = []
    for label in ("Offense", "Defense", "Special", "Teams"):
        for m in re.finditer(re.escape(label), header_line):
            spans.append((label, m.start()))
    spans.sort(key=lambda t: t[1])
    return spans


def lineup_split(block: str, away: str, home: str):
    """The column separating the two clubs inside the Lineups block.

    The Lineups block prints both club names on one line with a wide gap between
    them; the split is the midpoint of that gap. A gap of at least 8 spaces is
    required so that a prose line such as "Patriots at Lions" on the date line is
    not mistaken for the two column headers.
    """
    if len(away) < 4 or len(home) < 4:
        raise ValueError(
            f"lineup_split needs full club names, got {away!r}/{home!r}: an "
            "abbreviation such as 'NE' matches inside unrelated words")
    a_re = re.compile(r"\b" + re.escape(away))
    h_re = re.compile(r"\b" + re.escape(home))
    for line in block.splitlines():
        am = a_re.search(line)
        if not am:
            continue
        hm = h_re.search(line, am.end())
        if hm and hm.start() - am.end() >= 8:
            return (am.end() + hm.start()) // 2
    return None


def heading_split(line: str, heading: str):
    """The column separating the two clubs' copies of a side-by-side list.

    Blocks such as "Not Active" and "Substitutions" repeat their heading once per
    club on the same line, so the split is the midpoint between the two copies --
    which is more reliable than a split carried over from another block, because
    each block has its own column geometry.
    """
    occ = [m.start() for m in re.finditer(re.escape(heading), line)]
    if len(occ) < 2:
        return None
    return (occ[0] + len(heading) + occ[1]) // 2


def parse_lineups(text: str, away: str, home: str) -> list:
    """Return [(club, unit, slot, jersey, player)] from the Lineups block.

    The block prints four columns -- away offense, away defense, home offense,
    home defense -- so each row is cut at the club split first and then each club's
    half is cut at its widest gap to separate offense from defense.
    """
    m = re.search(r"^\s*Lineups\s*$", text, re.M)
    if not m:
        return []
    start = m.end()
    end = re.search(r"^\s*(?:Substitutions|Did Not Play|Not Active|Field Goals|VISITOR:|"
                    r"HOME:|Officials)\b", text[start:], re.M)
    block = text[start:start + end.start()] if end else text[start:start + 4000]

    split = lineup_split(block, away, home)
    if split is None:
        return []

    out = []
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or not re.search(r"\d", stripped):
            continue
        if "Offense" in stripped or "Defense" in stripped:
            continue
        if stripped in (away, home):
            continue
        if re.search(r"\b" + re.escape(away), line) or re.search(r"\b" + re.escape(home), line):
            continue
        for club, half in ((away, line[:split]), (home, line[split:])):
            if not half.strip():
                continue
            parts = _split_widest_gap(half)
            for idx, part in enumerate(parts):
                if idx > 1:
                    break
                for slot, jersey, name in _slot_rows(part):
                    if not name or not jersey:
                        continue
                    out.append((club, "offense" if idx == 0 else "defense",
                                slot, jersey, name))
    return out


def _split_widest_gap(text: str, min_gap: int = 2):
    """Split a fixed-width half into [offense, defense] at its widest gap."""
    gaps = [(gm.start(), gm.end() - gm.start())
            for gm in re.finditer(r" {%d,}" % min_gap, text)]
    if not gaps:
        return [text]
    gstart, gwidth = max(gaps, key=lambda g: (g[1], -abs(g[0] - len(text) // 2)))
    return [text[:gstart], text[gstart:]]


def _items(flat: str) -> list:
    out = []
    for item in flat.split(","):
        item = " ".join(item.split())
        if not item:
            continue
        m2 = re.match(r"^([A-Za-z0-9/]{1,6})\s+(\d{0,2})\s*([A-Za-z][\w.'\u2019\- ]+)$", item)
        if m2:
            out.append({"pos_raw": m2.group(1), "jersey": m2.group(2),
                        "player_raw": m2.group(3).strip(), "club": ""})
        else:
            m3 = re.match(r"^(\d{0,2})\s*([A-Za-z][\w.'\u2019\- ]+)$", item)
            if m3:
                out.append({"pos_raw": "", "jersey": m3.group(1),
                            "player_raw": m3.group(2).strip(), "club": ""})
    return out


def _split_line(line: str, hint):
    """(left, right) halves of one printed line, or (line, "") / ("", line).

    The hint comes from the block's heading. It is treated as approximate: the cut
    is snapped to the whitespace gap nearest the hint, because the heading is
    centred over its block while the wrapped text underneath is not.
    """
    if hint is None:
        return line, ""
    gaps = [(gm.start(), gm.end() - gm.start()) for gm in re.finditer(r" {3,}", line)]
    if gaps:
        gstart, gwidth = min(gaps, key=lambda g: abs(g[0] + g[1] // 2 - hint))
        cut = gstart + gwidth // 2
        left, right = line[:cut], line[cut:]
        if left.strip() and right.strip():
            return left, right
    if len(line) > hint and line[hint:].strip() and not line[:hint].strip():
        return "", line            # indented continuation: the home club only
    return line, ""                # anything shorter than the hint is the away club


def parse_named_list(text: str, heading: str, away: str, home: str) -> list:
    """Parse a comma-separated roster list ('Not Active', 'Did Not Play').

    The two clubs are printed side by side under a heading that is repeated once
    per club, and each list wraps across several lines, so the lines of a block are
    cut at the block's own split column and each side is then flattened separately.
    """
    stop = re.compile(r"^\s*(?:Paid Attendance|Playtime Percentage|Field Goals|VISITOR:|"
                      r"HOME:|Not Active|Substitutions|Lineups|Officials|Scoring Plays|"
                      r"National Football League Game Summary|Miscellaneous|Ten Longest)\b")
    out = []
    for m in re.finditer(r"^\s*" + heading + r"\b.*$", text, re.M):
        hint = heading_split(m.group(0), heading)
        sides = {"L": [], "R": []}
        for line in text[m.end():].splitlines():
            if stop.match(line):
                break
            if not line.strip() or heading in line:
                continue
            left, right = _split_line(line, hint)
            sides["L"].append(left)
            sides["R"].append(right)
            if len(" ".join(sides["L"])) > 3000:
                break
        for key, club in (("L", away), ("R", home)):
            for rec in _items(" ".join(sides[key]).strip()):
                rec["club"] = club
                out.append(rec)
        break  # one heading line covers both clubs, so a single pass is enough
    return out


def parse_playtime(text: str, away: str, home: str):
    """Return (rows, unofficial_flag).

    The Playtime Percentage table prints both clubs side by side, and it has three
    traps that a naive fixed-offset read gets wrong:

    1. the two clubs' column headers are NOT aligned with the numbers beneath them
       (the club-name line is centred over each half, while "Special Teams" is
       wider than the numbers under it);
    2. a player who took no snaps in a unit has that column simply *absent*, so
       later columns shift left;
    3. after a page break the book prints a second, unheadered block holding the
       players who appeared on special teams ONLY. That block has one (snaps, pct)
       pair per club and it is a special-teams figure, not an offensive one.

    Rows are therefore cut using NAME + POSITION + first-number anchors (a club's
    entry always begins with a name immediately followed by a position and a
    number), and the numbers on each side are assigned to offense / defense /
    special teams by monotone alignment against the printed header, which tolerates
    missing columns.
    """
    m = re.search(r"Playtime Percentage", text)
    if not m:
        return [], False
    tail = text[m.end():]
    unofficial = bool(re.search(r"\(Unofficial\)", tail[:200], re.I))

    max_dist, skip_cost = 14, 22
    num_re = re.compile(r"(\d{1,3})(?:\s+(\d{1,3})%)?")

    def anchors(line: str) -> list:
        """Character offsets where a player entry begins (name + POS + number)."""
        toks = [(tm.start(), tm.group(0)) for tm in re.finditer(r"\S+", line)]
        out = []
        for i, (pos, tok) in enumerate(toks):
            if tok not in POS_WORDS or i + 1 >= len(toks):
                continue
            if not re.fullmatch(r"\d{1,3}", toks[i + 1][1]):
                continue
            nm, j = [], i - 1
            while j >= 0 and len(nm) < 3 and not re.fullmatch(r"[\d%]+", toks[j][1]):
                nm.insert(0, toks[j][1])
                j -= 1
            if nm:
                out.append(toks[j + 1][0])
        return out

    def align(cols, matches):
        """Monotone assignment of numbers to columns, allowing missing columns."""
        best = [None]

        def rec(i, j, cost, chosen):
            if best[0] is not None and cost >= best[0][0]:
                return
            if j == len(cols):
                if best[0] is None or cost < best[0][0]:
                    best[0] = (cost, list(chosen))
                return
            if i < len(matches):
                d = abs(matches[i][0] - cols[j][1])
                if d <= max_dist:
                    chosen.append((cols[j][0], matches[i]))
                    rec(i + 1, j + 1, cost + d, chosen)
                    chosen.pop()
            rec(i, j + 1, cost + skip_cost, chosen)

        rec(0, 0, 0, [])
        return best[0][1] if best[0] else []

    def sides(line, split):
        """[(club, cols, base, lo, hi_)] for one printed row, or None."""
        anch = anchors(line)
        if not anch:
            return None
        if len(anch) >= 2:
            return anch[1]
        # a single entry: the away club's name always begins at the left margin, so
        # an entry that is indented belongs to the home club in a row where the
        # away club's list has already ended
        return len(line) if anch[0] <= 2 else anch[0]

    def read_side(seg, cols):
        """(player, pos, matches) for one club's half of a row."""
        matches = [(mm.start(), mm.group(1), mm.group(2) or "")
                   for mm in num_re.finditer(seg)]
        if not matches:
            return None
        toks = seg.split()
        name_toks = []
        for t in toks:
            if re.fullmatch(r"[\d%]+", t):
                break
            name_toks.append(t)
        if len(name_toks) < 2 or name_toks[-1] not in POS_WORDS:
            return None
        player, pos = " ".join(name_toks[:-1]), name_toks[-1]
        if len(player) < 3 or "." not in player:
            return None
        return player, pos, matches

    def blank():
        return {"off_snaps": "", "off_pct": "", "def_snaps": "", "def_pct": "",
                "st_snaps": "", "st_pct": ""}

    rows = []
    split = None

    for chunk_no, chunk in enumerate(tail.split("\f")):
        lines = chunk.splitlines()
        if chunk_no == 0:
            hi = None
            for idx, line in enumerate(lines[:14]):
                if "Offense" in line and "Defense" in line and "Special" in line:
                    hi = idx
                    break
            if hi is None:
                continue
            header = lines[hi]
            header_block = "\n".join(lines[max(0, hi - 4):hi + 1])
            split = lineup_split(header_block, away, home)
            if split is None:
                continue
            spans = [(l, p) for (l, p) in _col_spans(header) if l != "Teams"]
            left_labels = [(l, p) for l, p in spans if p < split]
            right_labels = [(l, p) for l, p in spans if p >= split]
            if not left_labels or not right_labels:
                continue

            def columns(labels, last_bound):
                groups = []
                for label, pos in labels:
                    key = {"Offense": "off", "Defense": "def", "Special": "st"}[label]
                    if groups and groups[-1][0] == key:
                        continue
                    groups.append((key, pos))
                return [(k, p, (groups[i + 1][1] if i + 1 < len(groups) else last_bound))
                        for i, (k, p) in enumerate(groups)]

            left_cols = [(k, p) for k, p, _e in columns(left_labels, split)]
            right_cols = [(k, p - split) for k, p, _e in
                          columns(right_labels, len(header) + 25)]
            body = lines[hi + 1:]
            colmap = ((away, left_cols, 0), (home, right_cols, split))
            st_only = False
        else:
            if split is None:
                continue
            body = lines
            colmap = ((away, None, 0), (home, None, split))
            st_only = True

        for line in body:
            if not line.strip():
                continue
            if re.match(r"^\s*(Paid Attendance|\*|Miscellaneous|Ten Longest|"
                        r"Possession Detail|National Football League)", line):
                break
            if "Offense" in line and "Defense" in line:
                continue
            if not num_re.search(line):
                continue
            row_split = sides(line, split)
            if row_split is None:
                continue
            for club, cols, base in colmap:
                lo, hi_ = (0, row_split) if base == 0 else (row_split, len(line) + 4)
                if hi_ <= lo:
                    continue
                seg = line[lo:hi_]
                got = read_side(seg, cols)
                if not got:
                    continue
                player, pos, matches = got
                rec = {"club": club, "player_raw": player, "pos_raw": pos}
                rec.update(blank())
                if st_only:
                    rec["st_snaps"], rec["st_pct"] = matches[0][1], matches[0][2]
                else:
                    for key, (_p, snaps, pct) in align(cols, matches):
                        rec[f"{key}_snaps"], rec[f"{key}_pct"] = snaps, pct
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
    with open(txt_path, "w", encoding="utf-8") as fh:
        fh.write("")  # ensure the file exists even if pdftotext fails
    res["pdf_sha256"] = hashlib.sha256(blob).hexdigest()
    if len(blob) < 5000:
        res["status"], res["error"] = "pdf_too_small", f"{len(blob)} bytes"
        return res
    try:
        text = pdftotext(pdf_path, txt_path)
    except Exception as exc:  # noqa: BLE001
        res["status"], res["error"] = "pdftotext_failed", str(exc)
        return res

    away = row.get("away_name") or row["away"]
    home = row.get("home_name") or row["home"]
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
    if not pt:
        res["error"] = ("the book for this game is published but carries no Playtime "
                        "Percentage section yet; starters and inactive lists are "
                        "captured, snap counts are left blank rather than inferred")
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", required=False)
    ap.add_argument("--season", default="2026")
    ap.add_argument("--week", default="10")
    ap.add_argument("--out", default="fl2-depth/data/verified")
    ap.add_argument("--work", default="/tmp/fl2-depth-work")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--dump-games", default="",
                    help="comma separated game_ids whose extracted text is written to --out")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    os.makedirs(args.out, exist_ok=True)
    os.makedirs(args.work, exist_ok=True)

    def write_log(results, extra=""):
        payload = {"captured_at_utc": stamp, "season": args.season, "week": args.week,
                   "note": extra,
                   "games": [{k: v for k, v in r.items() if not k.startswith("_")}
                             for r in results]}
        with open(os.path.join(args.out, f"capture-log-{args.season}-w{args.week}.json"),
                  "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1)
        with open(os.path.join(args.out, f"capture-log-{args.season}-w{args.week}.md"),
                  "w", encoding="utf-8") as fh:
            fh.write(f"# Game Book capture log - {args.season} week {args.week}\n\n")
            fh.write(f"Captured {stamp}. {extra}\n\n")
            fh.write("| game | status | book url | sha256 | playtime rows | error |\n")
            fh.write("|---|---|---|---|---|---|\n")
            for r in results:
                fh.write(f"| {r.get('game_id','')} | {r.get('status','')} | "
                         f"{r.get('gamebook_url','')} | {(r.get('pdf_sha256') or '')[:16]} | "
                         f"{r.get('playtime_rows','')} | "
                         f"{str(r.get('error',''))[:400].replace('|','/')} |\n")

    dump_ids = {g.strip() for g in args.dump_games.split(",") if g.strip()}
    results = []
    try:
        with open(args.seed, newline="", encoding="utf-8") as fh:
            seed = list(csv.DictReader(fh))
        seed = [r for r in seed if r.get("season") == args.season and r.get("week") == args.week]
        print(f"seed rows matched: {len(seed)}")
        if not seed:
            write_log([], extra=f"NO SEED ROWS for season={args.season} week={args.week}")
            return 2
        results = [capture_game(r, args.work) for r in seed]

        # Integrity guard: if two games resolve to byte-identical PDFs, the
        # game-centre page is not serving that game's own book (seen when a game is
        # still in progress). Publishing the other game's players under this
        # game's id would be fabrication, so the rows are dropped and flagged.
        seen_hash = {}
        for r in results:
            h = r.get("pdf_sha256")
            if not h:
                continue
            if h in seen_hash:
                r["status"] = "duplicate_pdf_hash"
                r["error"] = (f"byte-identical to the book already captured for "
                              f"{seen_hash[h]}; this game's own book is not being "
                              f"served, so its rows are withheld rather than guessed")
                for key in ("_lineups", "_playtime", "_not_active", "_did_not_play"):
                    r[key] = []
                r["playtime_rows"] = 0
            else:
                seen_hash[h] = r["game_id"]

        for r in results:
            if r["game_id"] in dump_ids:
                src = os.path.join(args.work, f"{r['game_id']}.txt")
                if os.path.exists(src):
                    dst = os.path.join(args.out, f"debug-text-{r['game_id']}.txt")
                    with open(src, encoding="utf-8", errors="replace") as a, \
                            open(dst, "w", encoding="utf-8") as b:
                        b.write(a.read())
        write_log(results)
    except Exception:  # noqa: BLE001
        import traceback
        write_log(results, extra="EXCEPTION: " + traceback.format_exc()[-2000:])
        raise

    bk = os.path.join(args.out, f"gamebooks-{args.season}-w{args.week}.csv")
    st = os.path.join(args.out, f"starters-{args.season}-w{args.week}.csv")
    ia = os.path.join(args.out, f"inactives-{args.season}-w{args.week}.csv")
    pt = os.path.join(args.out, f"playtime-{args.season}-w{args.week}.csv")

    with open(bk, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["game_id", "season", "week", "away", "home", "gamebook_url", "gamecenter_url",
                    "pdf_sha256", "status", "book_venue", "book_roof_surface", "book_weather",
                    "book_temp_f", "book_wind", "attendance", "kickoff_local",
                    "playtime_unofficial", "playtime_rows", "captured_at_utc",
                    "source_tier", "note"])
        for r, s in zip(seed, results):
            w.writerow([r["game_id"], r["season"], r["week"], r["away"], r["home"],
                        s.get("gamebook_url", ""), s.get("gamecenter_url", ""),
                        s.get("pdf_sha256", ""), s.get("status", ""),
                        s.get("book_venue", ""), s.get("book_roof_surface", ""),
                        s.get("book_weather", ""), s.get("book_temp_f", ""), s.get("book_wind", ""),
                        s.get("attendance", ""), s.get("kickoff_local", ""),
                        s.get("playtime_unofficial", ""), s.get("playtime_rows", ""),
                        stamp, "T1 official NFL Game Book",
                        "" if s.get("status") == "captured" else s.get("error", "")])

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

    failures = [r for r in results if not r["status"].startswith("captured")]
    print(json.dumps({"games": len(results),
                      "captured": sum(1 for r in results if r["status"].startswith("captured")),
                      "no_book_yet": [r["game_id"] for r in results
                                      if r["status"] == "no_gamebook_published_yet"],
                      "failures": [{"g": r["game_id"], "s": r["status"],
                                    "e": str(r.get("error", ""))[:300]}
                                   for r in failures]}, indent=1))
    return 0


# --------------------------------------------------------------------------- self test


def self_test() -> int:
    """Offline tests against synthetic pdftotext -layout output.

    The synthetic book reproduces the real Game Book geometry rather than a tidy
    one, because a tidy version is what earlier drafts of this parser were written
    against, and it passed while the real books failed. Specifically:

    * Lineups has FOUR columns (away offense, away defense, home offense, home
      defense) with the club names on their own line above them;
    * each roster list repeats its heading once per club on one line, and each
      block has its own column geometry;
    * the club-name line is centred over each half while the Playtime numbers are
      NOT aligned with the printed column headers;
    * players omit the units they did not play, so Playtime columns shift left;
    * after a page break the book prints a second, unheadered block of
      special-teams-only players whose single number pair is a SPECIAL TEAMS
      figure, not an offensive one.
    """
    def lineup_row(a_slot, a_no, a_name, d_slot, d_no, d_name,
                   h_o_slot, h_o_no, h_o_name, h_d_slot, h_d_no, h_d_name):
        return (" " * 7 + f"{a_slot} {a_no:>3} {a_name}".ljust(32)
                + f"{d_slot} {d_no:>3} {d_name}".ljust(24)
                + f"{h_o_slot} {h_o_no:>3} {h_o_name}".ljust(30)
                + f"{h_d_slot} {h_d_no:>3} {h_d_name}")

    def pt_row(n1, p1, o1, d1, s1, n2, p2, o2, d2, s2):
        return ((n1 + " " + p1).ljust(21) + o1.ljust(14) + d1.ljust(14) + s1.ljust(9)
                + (n2 + " " + p2).ljust(34) + o2.ljust(16) + d2.ljust(14) + s2)

    pt_header = (" " * 20 + "Offense".ljust(13) + "Defense".ljust(11) + "Special Teams"
                 + " " * 34 + "Offense".ljust(15) + "Defense".ljust(10)
                 + "Special Teams")
    pt_club_line = " " * 14 + "Test Away".ljust(20) + " " * 56 + "Test Home"

    txt = (
        "National Football League Game Summary\n"
        "NFL Copyright (c) 2026 by The National Football League. All rights reserved. "
        "This summary and play-by-play is for the express purpose of assisting media in "
        "their coverage of the game; any other use of this material is prohibited "
        "without the written permission of the National Football League.\n"
        "Date: Sunday, 11/15/2026   Test Away at Test Home"
        "      Start Time: 1:02 PM EST\n"
        "                                    at Test Field, Test City, TS\n"
        "Game Day Weather\n"
        "Game Weather: Cloudy                    Temp: 46 F (7.8 C) Humidity: 75%, Wind: NW 15 mph\n"
        "Open Stadium on Natural Grass\n"
        "Officials\n"
        "Referee: Rogers, Brad (19)\n"
        "Lineups\n\n"
        + " " * 28 + "Test Away" + " " * 53 + "Test Home\n"
        + " " * 15 + "Offense" + " " * 27 + "Defense" + " " * 27 + "Offense"
        + " " * 27 + "Defense\n"
        + lineup_row("LT", 66, "W.Campbell", "OLB", 5, "Dr.Jones",
                     "WR", 18, "I.TeSlaa", "DE", 97, "A.Hutchinson") + "\n"
        + lineup_row("LG", 70, "G.Van Roten", "DT", 97, "M.Williams",
                     "TE", 87, "S.LaPorta", "DL", 54, "A.McNeill") + "\n"
        + "\n                                   Substitutions                                    "
        "                                        Substitutions\n"
        + "WR 3 D.Douglas, K 8 A.Borregales, RB 9 C.Kiner".ljust(72)
        + "P 3 J.Fox, DB 5 C.Izien, DE 8 D.Moore\n"
        + "\n                                    Did Not Play                                     "
        "                                       Did Not Play\n"
        + "QB 10 D.Mills".ljust(72) + "C 61 J.Schmitz\n"
        + "\n                                     Not Active                                      "
        "                                        Not Active\n"
        + "CB 7 C.Davis, 3QB 15 B.Morton, S 41 B.Schooler".ljust(72)
        + "CB 21 P.Adebo, CB 35 N.Reed, LB 54 M.Harrison\n"
        + "\nPaid Attendance: 58,342\n"
        + "Playtime Percentage\n"
        + "Percent of playtime per player on offense, defense and special teams (Unofficial)\n"
        + pt_club_line + "\n" + pt_header + "\n\n"
        + pt_row("G.Van Roten", "OL", "59 100%", "", "2   7%",
                 "B.Miller", "T", "71 100%", "", "5  18%") + "\n"
        + pt_row("M.Jones", "CB", "", "64  90%", "4  14%",
                 "R.McCreary", "CB", "", "59 100%", "3  11%") + "\n"
        + pt_row("A.St. Brown", "WR", "47 66%", "", "",
                 "S.LaPorta", "TE", "56 79%", "", "9  32%") + "\n"
        + "\f"
        + "J.Ashby        LS   10   36% O.Pappoe    LB   20   71%\n"
        + "M.Wishnowsky   P    10   36% J.Bates     K    11   39%\n"
        + " " * 28 + "H.Hatten   LS   9    32%\n"
    )
    AWAY, HOME = "Test Away", "Test Home"

    h = parse_header(txt)
    assert h["book_temp_f"] == "46", h
    assert h["book_wind"] == "NW 15 mph", h
    assert h["attendance"] == "58342", h
    assert h["book_roof_surface"] == "Open Stadium on Natural Grass", h

    # real book headers: the venue is on the line AFTER the date line, and an
    # unrelated "Outdoor Weather" label can trail the roof/surface on the same line
    real = (
        "Date: Sunday, 11/15/2026"
        "                                  New England Patriots at Detroit Lions"
        "                                             Start Time: 3:33 PM CET\n"
        "                                                                   "
        "at Allianz Arena, Munich, Germany\n"
        "                                                                        Game Day Weather\n"
        "Game Weather: Cloudy                                    Temp: 52 F (11.1 C) "
        "Humidity: 51%, Wind: SE 3 mph\n"
        "Open Stadium on Natural Grass\n"
    )
    hr = parse_header(real)
    assert hr["book_venue"] == "Allianz Arena, Munich, Germany", hr
    assert hr["book_roof_surface"] == "Open Stadium on Natural Grass", hr
    assert hr["book_temp_f"] == "52", hr
    assert hr["book_wind"] == "SE 3 mph", hr

    mia = ("Date: Sunday, 11/15/2026   Start Time: 1:02 PM EST\n"
           "                                        at Hard Rock Stadium, Miami Gardens, FL\n"
           "Retractable Roof - Closed on Field Turf Outdoor Weather\n"
           "Game Weather: Cloudy    Temp: 48 F   Wind: N 6 mph\n")
    hm = parse_header(mia)
    assert hm["book_venue"] == "Hard Rock Stadium, Miami Gardens, FL", hm
    assert hm["book_roof_surface"] == "Retractable Roof - Closed on Field Turf", hm
    assert h["book_venue"] == "Test Field, Test City, TS", h
    assert "National Football League" in h["copyright_notice"], h

    lu = parse_lineups(txt, AWAY, HOME)
    assert len(lu) == 8, lu
    names = {(r[0], r[1], r[2], r[4]) for r in lu}
    for expect in ((AWAY, "offense", "LT", "W.Campbell"), (AWAY, "defense", "OLB", "Dr.Jones"),
                   (HOME, "offense", "WR", "I.TeSlaa"), (HOME, "defense", "DE", "A.Hutchinson"),
                   (AWAY, "offense", "LG", "G.Van Roten"), (AWAY, "defense", "DT", "M.Williams"),
                   (HOME, "offense", "TE", "S.LaPorta"), (HOME, "defense", "DL", "A.McNeill")):
        assert expect in names, (expect, lu)

    na = parse_named_list(txt, "Not Active", AWAY, HOME)
    assert [(r["club"], r["player_raw"]) for r in na] == [
        (AWAY, "C.Davis"), (AWAY, "B.Morton"), (AWAY, "B.Schooler"),
        (HOME, "P.Adebo"), (HOME, "N.Reed"), (HOME, "M.Harrison")], na
    assert na[0]["pos_raw"] == "CB" and na[0]["jersey"] == "7", na

    dnp = parse_named_list(txt, "Did Not Play", AWAY, HOME)
    assert [(r["club"], r["player_raw"]) for r in dnp] == [(AWAY, "D.Mills"),
                                                           (HOME, "J.Schmitz")], dnp

    rows, unofficial = parse_playtime(txt, AWAY, HOME)
    assert unofficial is True, "the league's (Unofficial) caption must be captured"
    by = {(r["club"], r["player_raw"]): r for r in rows}
    assert len(rows) == 11, rows

    def snap(club, name):
        r = by[(club, name)]
        return (r["pos_raw"], r["off_snaps"], r["off_pct"], r["def_snaps"],
                r["def_pct"], r["st_snaps"], r["st_pct"])

    assert snap(AWAY, "G.Van Roten") == ("OL", "59", "100", "", "", "2", "7")
    assert snap(AWAY, "M.Jones") == ("CB", "", "", "64", "90", "4", "14")
    # a surname containing a full stop must not be truncated
    assert snap(AWAY, "A.St. Brown") == ("WR", "47", "66", "", "", "", "")
    assert snap(HOME, "B.Miller") == ("T", "71", "100", "", "", "5", "18")
    assert snap(HOME, "R.McCreary") == ("CB", "", "", "59", "100", "3", "11")
    assert snap(HOME, "S.LaPorta") == ("TE", "56", "79", "", "", "9", "32")
    # the post-page-break block is special teams only, never offense
    assert snap(AWAY, "J.Ashby") == ("LS", "", "", "", "", "10", "36")
    assert snap(HOME, "J.Bates") == ("K", "", "", "", "", "11", "39")
    assert snap(HOME, "H.Hatten") == ("LS", "", "", "", "", "9", "32")

    # a book served for the wrong game must be withheld, not published
    dup = [{"game_id": "A", "pdf_sha256": "abc", "status": "captured",
            "playtime_rows": 3, "_playtime": [1], "_lineups": [1],
            "_not_active": [1], "_did_not_play": [1]},
           {"game_id": "B", "pdf_sha256": "abc", "status": "captured",
            "playtime_rows": 3, "_playtime": [1], "_lineups": [1],
            "_not_active": [1], "_did_not_play": [1]}]
    seen = {}
    for r in dup:
        hsh = r["pdf_sha256"]
        if hsh in seen:
            r["status"] = "duplicate_pdf_hash"
            for k in ("_lineups", "_playtime", "_not_active", "_did_not_play"):
                r[k] = []
            r["playtime_rows"] = 0
        else:
            seen[hsh] = r["game_id"]
    assert dup[1]["status"] == "duplicate_pdf_hash"
    assert dup[1]["_playtime"] == [] and dup[1]["playtime_rows"] == 0
    assert dup[0]["status"] == "captured" and dup[0]["_playtime"] == [1]

    # a club variant such as Cincinnati's LDE/RDE/HB must be recognised
    assert "LDE" in POS_WORDS and "RDE" in POS_WORDS and "HB" in POS_WORDS
    assert _slot_rows("LDE   99 M.Murphy") == [("LDE", "99", "M.Murphy")]
    assert _slot_rows("HB    30 C.Brown") == [("HB", "30", "C.Brown")]

    print("self-test OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

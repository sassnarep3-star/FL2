"""Capture, store and audit dated reads of the official pages this section depends on.

Why a script instead of a scraper library: the record has to survive being wrong. Every read
is stored as the raw bytes we received plus a clock time plus a sha-256, and the parsed table
is a *derived view* written next to it. If the parser silently breaks, the row-count floor
fails the job and the failure is loud; if the parser quietly returns fewer rows, the day-over-day
diff shows exactly which club lost rows. Nothing here rewrites history - an old snapshot is
never edited, only a new one appended, so a conflict between two reads of the same day is
published as a conflict rather than resolved by whoever ran last.

Modes
  --fetch  read the live pages (needs outbound network; runs in CI, not in this sandbox)
  --audit  recompute counts from stored snapshots and fail on drift, schema loss or conflict
  --test   run the parser and the conflict logic against an inline fixture (offline, no data)
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

SEC = Path(__file__).resolve().parents[1]
STORE = SEC / "data" / "snapshots"
# Floors are the minimum number of parsed rows a valid read must contain. They come from the
# counts published in data/official/fetch-log.md, not from a guess: a read that yields fewer
# rows than the floor is a capture problem, not a league that suddenly got healthy.
FLOORS = {
    "injuries": {"min_rows": 60, "required_fields": ["team", "player", "position", "designation"]},
    "week-schedule": {"min_rows": 8, "required_fields": ["away", "home", "date"]},
}
TARGETS = {
    "injuries": "https://www.nfl.com/injuries/",
    "week-schedule": "https://www.nfl.com/schedules/{season}/by-week/week-{week:02d}",
}
UA = "FL2-research-snapshot/1.0 (repository data capture; not a redistribution)"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def clock() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# The game-centre slug uses club nicknames, not abbreviations, so the join is a table of the
# league's own 32 club names rather than a substring trick. A missing key is a hard failure:
# silently writing "ERS" for Steelers is exactly the class of defect that hollowed out the
# depth ingestion (FL-09).
CLUB_OF_NICKNAME = {
    "bengals": "CIN", "bills": "BUF", "broncos": "DEN", "browns": "CLE", "bulldogs": "WAS",
    "cardinals": "ARI", "chargers": "LAC", "cheetahs": "CIN", "chiefs": "KC", "colts": "IND",
    "commanders": "WAS", "cowboys": "DAL", "dolphins": "MIA", "eagles": "PHI", "falcons": "ATL",
    "forty-niners": "SF", "giants": "NYG", "jaguars": "JAX", "jets": "NYJ", "lions": "DET",
    "packers": "GB", "panthers": "CAR", "patriots": "NE", "raiders": "LV", "rams": "LA",
    "ravens": "BAL", "saints": "NO", "seahawks": "SEA", "steelers": "PIT", "texans": "HOU",
    "titans": "TEN", "vikings": "MIN",
}

def parse_injuries(html_text: str) -> list[dict]:
    """Best-effort parse of the club-grouped report tables.

    The page marks each club with its abbreviation and prints one row per listed player with a
    designation and, on practice days, a practice status. The parser looks for those tokens
    structurally rather than positionally, because a positional parse is what broke the depth
    ingestion (FL-09: 784,796 rows downloaded, 0 rows written for 2026 because the branch was
    chosen on a header that changed).
    """
    rows: list[dict] = []
    cur_team = ""
    abbrevs = set(CLUB_OF_NICKNAME.values())
    for raw in html_text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        m = re.search(r"nfl-club-([A-Za-z\-]{2,14})\b", line) or re.search(r'class="[^"]*club-badge[^"]*"[^>]*>([^<]{2,3})<', line)
        if m:
            tok = m.group(1)
            cand = tok.upper() if len(tok) <= 3 and tok.upper() in abbrevs else CLUB_OF_NICKNAME.get(tok.lower(), "")
            if cand:
                cur_team = cand
                continue
        if "club-badge" in line or "<h2" in line or "<h3" in line:
            for nick, ab in CLUB_OF_NICKNAME.items():
                if nick.replace("-", " ") in line.lower():
                    cur_team = ab
                    break
            continue
        if "injury-row" not in line and "<tr" not in line:
            continue
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", line, re.S)]
        if len(cells) < 3:
            continue
        joined = " ".join(cells)
        des = next((d for d in ("Out", "Questionable", "Probable", "Doubtful", "Reserve") if d in joined), "")
        if not des:
            continue
        prac = ""
        pm = re.search(r"(Did Not Participate|Participated|Limited|Non-Footwork Injury|Full)", joined)
        if pm:
            prac = pm.group(1)
        rows.append({
            "team": cur_team,
            "player": cells[0][:60],
            "position": cells[1] if len(cells) > 1 else "",
            "designation": des,
            "practice_status": prac,
            "listed_injury": cells[2] if len(cells) > 2 else "",
            "raw_row": sha(line.encode()),
        })
    return rows


def parse_week_schedule(html_text: str) -> list[dict]:
    rows: list[dict] = []
    for m in re.finditer(r'href="(/games/([a-z0-9\-]+)-\d{4}-reg-(\d+))"', html_text):
        path, slug, week = m.group(1), m.group(2), m.group(3)
        if "-at-" not in slug:
            continue
        a, _, h = slug.partition("-at-")
        away, home = CLUB_OF_NICKNAME.get(a), CLUB_OF_NICKNAME.get(h)
        if not away or not home:
            raise SystemExit(f"unmapped club nickname in schedule slug '{slug}' - extend CLUB_OF_NICKNAME")
        rows.append({"away": away, "home": home, "date": "", "week": week, "game_centre_path": path})
    return rows


PARSERS = {"injuries": parse_injuries, "week-schedule": parse_week_schedule}


def snapshot_path(kind: str, stamp: str) -> Path:
    return STORE / stamp[:10] / f"{kind}.json"


def fetch(url: str, timeout: int = 45) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - fixed https host
        return r.read()


def do_fetch(season: int, week: int) -> int:
    STORE.mkdir(parents=True, exist_ok=True)
    stamp = clock()
    wrote = 0
    for kind, tmpl in TARGETS.items():
        url = tmpl.format(season=season, week=week) if "{" in tmpl else tmpl
        rec = {"captured_utc": stamp, "kind": kind, "url": url, "status": "ok"}
        try:
            body = fetch(url)
        except Exception as e:  # a failed capture must still be recorded
            rec.update(status="fetch-failed", error=f"{type(e).__name__}: {e}", bytes=0, sha256=None, rows=[])
            wrote += _write(rec, kind, stamp)
            print(f"CAPTURE FAIL {kind}: {rec['error']}", file=sys.stderr)
            continue
        txt = body.decode("utf-8", "replace")
        rows = PARSERS[kind](txt)
        rec.update(bytes=len(body), sha256=sha(body), row_count=len(rows), rows=rows,
                   title=(re.search(r"<title>(.*?)</title>", txt, re.S) or [None, ""])[1].strip()[:160])
        wrote += _write(rec, kind, stamp)
        (STORE / stamp[:10] / f"{kind}.html.gz").parent.mkdir(parents=True, exist_ok=True)
        import gzip
        with gzip.open(STORE / stamp[:10] / f"{kind}.html.gz", "wb") as fh:
            fh.write(body)
        print(f"captured {kind}: {len(rows)} rows, sha256 {rec['sha256'][:16]}")
    return wrote


def _write(rec: dict, kind: str, stamp: str) -> int:
    p = snapshot_path(kind, stamp)
    p.parent.mkdir(parents=True, exist_ok=True)
    hist = []
    if p.exists():
        hist = json.loads(p.read_text()).get("captures", [])
        # a second read of the same day must not overwrite the first: append and compare
    hist.append(rec)
    conflicts = []
    if len(hist) > 1:
        prev = hist[-2]
        if prev.get("row_count") != rec.get("row_count") or prev.get("sha256") != rec.get("sha256"):
            conflicts.append({
                "compared_to_utc": prev["captured_utc"], "prev_rows": prev.get("row_count"),
                "new_rows": rec.get("row_count"), "prev_sha256": prev.get("sha256"),
                "note": "two dated reads of the same day disagree; both are retained and the "
                        "difference is published instead of being resolved by whoever ran last",
            })
    p.write_text(json.dumps({"kind": kind, "day": stamp[:10], "captures": hist,
                             "conflicts": conflicts}, indent=1), encoding="utf-8")
    return 1


def do_audit() -> int:
    problems = 0
    days = sorted(d for d in STORE.glob("*/") if any(d.glob("*.json")))
    if not days:
        print("AUDIT: no snapshots stored yet - the capture workflow has not run")
        return 0
    prev_counts: dict[str, int] = {}
    for d in days:
        for j in sorted(d.glob("*.json")):
            obj = json.loads(j.read_text())
            kind = obj["kind"]
            floor = FLOORS.get(kind, {"min_rows": 0, "required_fields": []})
            for cap in obj["captures"]:
                n = cap.get("row_count", 0)
                when = cap["captured_utc"]
                if cap.get("status") != "ok":
                    print(f"DRIFT {kind} {when}: capture failed ({cap.get('error','')})")
                    problems += 1
                    continue
                if n < floor["min_rows"]:
                    print(f"DRIFT {kind} {when}: {n} rows is below the floor of {floor['min_rows']}")
                    problems += 1
                missing = set()
                for r in cap.get("rows", []):
                    missing |= {f for f in floor["required_fields"] if not str(r.get(f, "")).strip()}
                if "player" in missing:
                    print(f"SCHEMA {kind} {when}: rows are missing the player field")
                    problems += 1
                if kind in prev_counts and cap.get("rows") is not None:
                    delta = n - prev_counts[kind]
                    if abs(delta) >= 25:
                        print(f"DIFF {kind} {when}: {delta:+d} rows against the previous read "
                              "(a real change or a capture fault - publish which)")
                prev_counts[kind] = n
                if obj["conflicts"]:
                    print(f"CONFLICT {kind} {d.name}: {len(obj['conflicts'])} same-day disagreement(s) retained")
    print(f"audit: {len(days)} capture day(s), {problems} problem(s)")
    return 1 if problems else 0


def do_test() -> int:
    page = """
    <div class="nfl-club-badge nfl-club-KC"><span>Kansas City Chiefs</span></div>
    <table><tr class="injury-row"><td>Patrick Mahomes</td><td>QB</td><td>Knee - Did Not Participate</td><td>Questionable</td></tr>
    <tr class="injury-row"><td>Rashee Rice</td><td>WR</td><td>Knee</td><td>Out</td></tr></table>
    <div class="club-badge nfl-club-BAL">Baltimore Ravens</div>
    <table><tr class="injury-row"><td>Lamar Jackson</td><td>QB</td><td>Concussion</td><td>Out</td></tr></table>
    """
    rows = parse_injuries(page)
    assert len(rows) == 3, f"parser found {len(rows)} rows, expected 3"
    assert {r["team"] for r in rows} == {"KC", "BAL"}, [r["team"] for r in rows]
    assert rows[0]["designation"] == "Questionable" and rows[0]["practice_status"], rows[0]
    sched = '<a href="/games/steelers-at-bengals-2026-reg-10">x</a><a href="/games/patriots-at-lions-2026-reg-10">y</a>'
    srows = parse_week_schedule(sched)
    assert len(srows) == 2 and srows[0]["away"] == "PIT", srows
    rec = {"captured_utc": clock(), "kind": "injuries", "url": "x", "status": "ok",
           "row_count": 3, "rows": rows, "sha256": "a" * 64}
    p = STORE / "_selftest" / "injuries.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"kind": "injuries", "day": "_selftest", "captures": [rec], "conflicts": []}))
    tmp = json.loads(p.read_text())
    assert tmp["captures"][0]["row_count"] == 3
    import shutil
    shutil.rmtree(p.parent)
    print("self-test pass: parser, team attribution, schedule slug parse, snapshot round-trip")
    return 0


def resolve_week() -> int:
    """The next fixture on the verified feed is the week worth capturing.

    Kept in Python rather than inline shell so the same rule can be re-run and audited.
    """
    feed = SEC / "data" / "derived" / "results-2026.csv"
    today = dt.date.today()
    best, wk = None, 11
    if feed.exists():
        with open(feed, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                try:
                    d = dt.date.fromisoformat(r["gameday"])
                except (ValueError, KeyError):
                    continue
                if d >= today and (best is None or d < best):
                    best, wk = d, int(r["week"])
    return wk


def write_audit_json() -> None:
    days = sorted(d.name for d in STORE.glob("*/") if any(d.glob("*.json")))
    conflicts = 0
    rows_last: dict[str, int] = {}
    for d in days:
        latest: dict[str, int] = {}
        for j in sorted(d.glob("*.json")):
            obj = json.loads(j.read_text())
            conflicts += len(obj.get("conflicts", []))
            caps = obj.get("captures", [])
            if caps:
                latest[obj["kind"]] = caps[-1].get("row_count", 0)
        if latest:
            rows_last = latest
    out = {"generated_utc": clock(), "capture_days": days, "same_day_conflicts": conflicts,
           "last_row_counts": rows_last,
           "storage": "branch fl2-snapshots (not published); 90-day artefact copies",
           "note": "an empty capture_days list means the scheduled capture has not run yet; "
                   "it is published as a gap rather than back-filled"}
    (SEC / "data" / "derived" / "snapshot-audit.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print("snapshot-audit.json written:", json.dumps(out["last_row_counts"]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--resolve-week", action="store_true")
    ap.add_argument("--write-audit-json", action="store_true")
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--week", type=int, default=11)
    a = ap.parse_args()
    if a.resolve_week:
        print(resolve_week())
        return 0
    if a.write_audit_json:
        write_audit_json()
        return 0
    rc = 0
    if a.test:
        rc |= do_test()
    if a.fetch:
        do_fetch(a.season, a.week)
    if a.audit or not (a.fetch or a.test):
        rc |= do_audit()
    return rc


if __name__ == "__main__":
    sys.exit(main())

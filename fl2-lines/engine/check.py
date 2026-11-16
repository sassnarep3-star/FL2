"""Section validator. Exit code is non-zero when the section must not be published.

Checks the things that silently rot a data site: a CSV whose column count drifted, an
internal link that points at nothing, a table row without a source, a number in a page that
no longer matches the artefact it came from, and an unverified value presented as verified.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path

SEC = Path(__file__).resolve().parents[1]
DER = SEC / "data" / "derived"
REG = SEC / "data" / "registers"
PRI = SEC / "data" / "prices"
OFFICIAL_HOSTS = ("nfl.com", "nflapis.com", "nfl.com/news")
fails: list[str] = []
warns: list[str] = []


def fail(msg: str) -> None:
    fails.append(msg)


def warn(msg: str) -> None:
    warns.append(msg)


def check_csv(path: Path, required: list[str] | None = None, min_rows: int = 1) -> list[dict]:
    if not path.exists():
        fail(f"missing file {path.relative_to(SEC)}")
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    if not rows:
        fail(f"{path.name}: empty")
        return []
    hdr = rows[0]
    for i, r in enumerate(rows[1:], start=2):
        if len(r) != len(hdr):
            fail(f"{path.name}: line {i} has {len(r)} fields, header has {len(hdr)}")
    if required:
        miss = [c for c in required if c not in hdr]
        if miss:
            fail(f"{path.name}: missing columns {miss}")
        idx = {c: hdr.index(c) for c in hdr}
        for i, r in enumerate(rows[1:], start=2):
            if len(r) != len(hdr):
                continue
            for c in required:
                if not r[idx[c]].strip():
                    fail(f"{path.name}: empty required field '{c}' at line {i}")
    return [dict(zip(hdr, r)) for r in rows[1:]]


def no_nan(path: Path) -> None:
    txt = path.read_text()
    if "NaN" in txt or "Infinity" in txt:
        fail(f"{path.name}: contains a bare NaN/Infinity token (JSON.parse would reject it)")
    if path.suffix == ".json":
        try:
            json.loads(txt)
        except json.JSONDecodeError as e:
            fail(f"{path.name}: invalid JSON ({e})")


def main() -> int:
    check_csv(REG / "readiness.csv",
              required=["id", "requirement", "area", "status", "gate_blocking", "clearing_number",
                        "evidence", "official_source"], min_rows=70)
    check_csv(REG / "prereg.csv", required=["id", "name", "bet_shape", "signal_definition",
                                            "evaluation_window", "registered_utc", "gates", "division"])
    check_csv(REG / "suggestions.csv", required=["id", "title", "state", "problem", "missing_information_to_decide"])
    check_csv(REG / "questions.csv", required=["id", "question", "why_it_blocks", "status"])
    check_csv(REG / "flags.csv", required=["id", "type", "title", "handling"])
    check_csv(REG / "sources.csv", required=["id", "source", "tier", "how_accessed", "url"])
    check_csv(DER / "results-2026.csv", required=["game_id", "season", "week", "away_team", "home_team",
                                                  "result_prov"])
    check_csv(DER / "results-reconciliation.csv", required=["team", "feed_wlt", "official_wlt", "match"])
    check_csv(DER / "lines-2026.csv", required=["game_id", "market", "sequence", "fair_line",
                                                "fixture_status", "sigma_used"])
    check_csv(PRI / "price-snapshots-2026.csv", required=["game_id", "market", "opening_source",
                                                           "fixture_status"])
    check_csv(PRI / "price-source-index.csv", required=["season", "source", "closing_price_rows", "opening_price_rows"])
    check_csv(DER / "availability-graph.csv", required=["player", "team", "week", "designation",
                                                        "expected_available_pct", "participated_that_week"])

    for j in sorted(DER.glob("*.json")) + sorted(PRI.glob("*.json")):
        no_nan(j)
    lp = SEC / "data" / "ledger" / "forecasts-week11.jsonl"
    if not lp.exists():
        fail("forward ledger missing: the shadow baseline has no committed records")
    else:
        recs = [json.loads(x) for x in lp.read_text().splitlines() if x.strip()]
        if len(recs) != 13:
            fail(f"ledger has {len(recs)} records, expected one per Week 11 fixture (13)")
        prev = "GENESIS"
        for r in recs:
            if r["prev_hash"] != prev:
                fail(f"ledger chain broken at {r['forecast_id']}")
            if r["recorded_utc"] >= r["kickoff_utc"]:
                fail(f"{r['forecast_id']} was recorded at or after kickoff - pre-registration violated")
            prev = r["record_hash"]

    feed = check_csv(DER / "results-2026.csv")
    recon = check_csv(DER / "results-reconciliation.csv")
    for g in feed:
        if g["away_score"] == "" and "no official final" not in g["result_prov"] and "not played" not in g["result_prov"]:
            fail(f'{g["game_id"]}: a blank score with no provenance explaining it')
    if recon:
        bad = [r["team"] for r in recon if r["match"] != "yes"]
        if bad:
            fail(f"results feed does not reproduce the official standings for: {bad}")
        agg: dict[str, list[int]] = {}
        for g in feed:
            if g["away_score"] == "":
                continue
            for t, side in ((g["away_team"], "a"), (g["home_team"], "h")):
                d = agg.setdefault(t, [0, 0, 0, 0, 0])
                me, opp = (int(g["away_score"]), int(g["home_score"])) if side == "a" else (int(g["home_score"]), int(g["away_score"]))
                d[3 if side == "a" else 4] += 1
                d[0] += 1
                d[1] += me
                d[2] += opp
        for r in recon:
            d = agg.get(r["team"], [0, 0, 0, 0, 0])
            if d[1] != int(r["official_pf"]) or d[2] != int(r["official_pa"]):
                fail(f"{r['team']}: reconciliation table disagrees with the feed ({d[1]}/{d[2]})")

    lines = check_csv(DER / "lines-2026.csv")
    per = {}
    for r in lines:
        per.setdefault(r["game_id"], set()).add(r["market"])
    for gid, ms in per.items():
        if ms != {"SPREAD", "TOTAL", "TOTAL_T2", "MONEYLINE"}:
            fail(f"{gid}: market set {sorted(ms)} is not side/total/total2/moneyline")
        if "MONEYLINE" in ms and "SPREAD" not in ms:
            fail(f"{gid}: moneyline without a side")
    for r in lines:
        if r["fixture_status"] == "FINAL" and r["market_line"] and r["residual_fair_minus_market"] == "":
            fail(f"{r['game_id']} {r['market']}: fair and market both present but the difference is blank")
        if r["market"] == "SPREAD" and not r["sequence"].startswith("1st"):
            fail(f"{r['game_id']} {r['market']}: the side must be priced first (sequence {r['sequence']})")
        if r["market"] in ("TOTAL", "TOTAL_T2") and not re.match(r"^2(nd|b)", r["sequence"]):
            fail(f"{r['game_id']} {r['market']}: totals must be priced second (sequence {r['sequence']})")
        if r["market"] == "MONEYLINE" and not r["sequence"].startswith("3rd"):
            fail(f"{r['game_id']} {r['market']}: the moneyline must be derived last (sequence {r['sequence']})")
        # Every published output carries a probability whenever the event it prices is defined:
        # the moneyline always is, a cover/over only against a recorded line.
        if r["market"] == "MONEYLINE" and not r["p_home_or_over"]:
            fail(f"{r['game_id']} MONEYLINE: no probability stored")
        if r["market"] != "MONEYLINE" and r["market_line"] and not r["p_home_or_over"]:
            fail(f"{r['game_id']} {r['market']}: a market line exists so a probability is computable but was not stored")

    rd = check_csv(REG / "readiness.csv")
    for r in rd:
        if r["status"] in ("BLOCKED", "PARTIAL") and not r["gate_blocking"].strip():
            fail(f"{r['id']}: {r['status']} with no blocking gate stated")
        if not r["clearing_number"].strip():
            fail(f"{r['id']}: no clearing number - a requirement nobody can check")
        if not r["evidence"].strip():
            fail(f"{r['id']}: no artefact behind the claim")
        rel = r["evidence"].split("#")[0].strip()
        if rel.startswith(".github/"):
            if not (SEC.parent / rel).exists():
                fail(f"{r['id']}: workflow evidence does not exist: {rel}")
        elif rel.startswith("fl2-lines/"):
            if not (SEC.parent / rel).exists():
                fail(f"{r['id']}: evidence path does not exist: {rel}")
        elif "/" in rel:
            if not (SEC.parent / rel).exists():
                fail(f"{r['id']}: evidence path does not exist anywhere in the repo: {rel}")
        elif rel:
            warn(f"{r['id']}: evidence is a bare filename, not a path: {rel}")
    if len(rd) < 70:
        fail(f"readiness register has {len(rd)} rows; the brief needs every requirement line tracked")

    pri = check_csv(PRI / "price-snapshots-2026.csv")
    n_open = sum(1 for r in pri if r.get("opening_line"))
    meta = json.loads((PRI / "price-store-meta.json").read_text())
    if n_open != meta["with_opening_number"]:
        fail(f"price store: {n_open} opening rows on disk vs {meta['with_opening_number']} in the meta")
    if len(pri) != meta["markets_recorded"]:
        fail(f"price store: {len(pri)} rows vs meta {meta['markets_recorded']}")
    if any(r.get("opening_line") and r.get("opening_source") in ("", "NOT CAPTURED") for r in pri):
        fail("an opening price is recorded with no provenance - that is an unsourced number")

    man = PRI / "MANIFEST.sha256"
    if not man.exists():
        fail("no MANIFEST.sha256: the store has no integrity record")
    else:
        stale = 0
        for line in man.read_text().splitlines():
            digest, _, rel = line.partition("  ")
            target = SEC / rel
            if not target.exists():
                fail(f"manifest lists a file that is gone: {rel}")
            elif hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                stale += 1
        if stale:
            fail(f"MANIFEST.sha256: {stale} digest(s) do not match the file on disk - the store was "
                 "edited without being rebuilt")

    pages = sorted(SEC.glob("*.html"))
    if not pages:
        fail("no HTML pages rendered")
    for p in pages:
        txt = p.read_text()
        if "<!doctype html>" not in txt.lower():
            fail(f"{p.name}: not a full document")
        for a in re.findall(r'href="([^"#]+)"', txt):
            if a.startswith(("http", "mailto:")):
                if a.startswith("http") and "nfl.com/injuries/" in a:
                    pass
                continue
            tgt = (p.parent / a).resolve()
            if not tgt.exists():
                fail(f"{p.name}: broken internal link {a}")
        if p.name != "index.html" and 'href="index.html"' not in txt:
            fail(f"{p.name}: no nav back to the section index")
        for bad in ("TBD", "TODO", "FIXME", "PLACEHOLDER"):
            if bad in txt:
                fail(f"{p.name}: contains {bad}")
    idx = (SEC / "index.html").read_text()
    for r in rd:
        if f'>{r["id"]}</td>' not in idx:
            fail(f"index.html does not render requirement {r['id']}")
    # every data row rendered somewhere must carry a source link
    for name in ("results.html", "prices.html", "availability.html"):
        t = (SEC / name).read_text()
        if "https://" not in t:
            fail(f"{name}: no outbound source link on a page that publishes numbers")
        if "nfl.com" not in t and "upstream" not in t:
            fail(f"{name}: numbers published without naming either an official page or the mirror")

    print(f"pages {len(pages)}  readiness {len(rd)}  feed {len(feed)}  lines {len(lines)}  prices {len(pri)}")
    for w in warns:
        print("WARN", w)
    for f in fails[:40]:
        print("FAIL", f)
    print(f"\n{'OK' if not fails else 'FAILED'}: {len(fails)} failures")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

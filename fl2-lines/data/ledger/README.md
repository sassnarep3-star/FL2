# Point-in-time snapshot ledger

Purpose: make it impossible to price a game with information the world did not have at the
time, and to let a replay show exactly what was knowable.

* `forecasts-week11.jsonl` — one record per Week 11 fixture, written 2026-11-16T01:30Z,
  which is **before** the first Week 11 kickoff (2026-11-20T01:15Z).
* Each record hashes the previous record's hash (`prev_hash`), and `LEDGER-TIP.txt` carries
  the last hash. Editing or deleting any record changes the tip, so a silent rewrite is
  detectable without trusting this repository's git history.
* A record stores the probability **and** the input vector that produced it
  (`data/derived/lines-inputs.jsonl`), so the number can be recomputed, not just inspected.
* Registration: the commit that contains the frozen strategy text and the frozen corpus
  definition is the pre-registration. `data/registers/prereg.csv` carries the hash at build
  time and is re-pinned after merge (see `engine/pin_prereg.py`).

Not yet in the ledger, and blocking: dated captures of the injury report (needs 3/week),
the official inactive lists, and per-game snap counts. The ledger can only hold what a
capture produces; the snapshot workflow is what produces it.

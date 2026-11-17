#!/usr/bin/env bash
# Wrapper for the Game Book capture. Runs in CI (the sandbox has no route to
# nfl.com). Writes every byte of its own output into the repository so the result
# can be reviewed without GitHub log access.
set -uo pipefail

OUTDIR=fl2-depth/data/verified
LOG="$OUTDIR/capture-stdout.txt"
SEASON="${SEASON:-2026}"
WEEK="${WEEK:-10}"

mkdir -p "$OUTDIR"
{
  echo "=== run_capture $(date -u +%Y-%m-%dT%H:%M:%SZ) season=$SEASON week=$WEEK"
  echo "pwd=$(pwd)"
  echo "python=$(command -v python3) $(python3 -V 2>&1)"
  echo "pdftotext=$(command -v pdftotext || echo MISSING)"
  echo "seed lines: $(wc -l < "$OUTDIR/gamecenter-seed.csv")"
  ls -la "$OUTDIR"
  echo "--- capture ---"
} > "$LOG" 2>&1

python3 -u fl2-depth/engine/capture_gamebooks.py \
  --seed "$OUTDIR/gamecenter-seed.csv" \
  --season "$SEASON" \
  --week "$WEEK" \
  --out "$OUTDIR" \
  --work /tmp/fl2-depth-work \
  --dump-games "${DUMP_GAMES:-}" >> "$LOG" 2>&1
code=$?
{
  echo "exit=$code"
  echo "--- header lines around Start Time (per book) ---"
  for t in /tmp/fl2-depth-work/*.txt; do
    [ -f "$t" ] || continue
    echo "== $(basename "$t")"
    grep -n "Start Time:" "$t" | head -2
    awk '/Start Time:/{f=NR} f && NR>=f && NR<=f+3' "$t" | head -4 | cat -A | sed 's/\$$//'
  done
  echo "--- files after ---"
  ls -la "$OUTDIR"
} >> "$LOG" 2>&1
exit 0

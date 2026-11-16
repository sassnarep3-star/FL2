"""Pin the pre-registration hash: writes the git commit that carries the frozen strategy
text into data/registers/prereg.csv (column `registered_commit`) and into the sources file.
Run after the commit that introduces the register, then commit the one-line change."""
import csv, io, subprocess, sys
from pathlib import Path
SEC = Path(__file__).resolve().parents[1]
def rev():
    # the pinned hash must be the commit that CARRIES the frozen text, not the newest commit:
    # pinning HEAD would let later edits slip into the same "registered" version.
    arg = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    if arg.startswith("HEAD") or len(arg) < 40:
        arg = subprocess.check_output(["git", "-C", str(SEC.parent), "log", "-1", "--format=%H",
                                       "--", "fl2-lines/data/registers/prereg.csv"], text=True).strip() or arg
    return subprocess.check_output(["git", "-C", str(SEC.parent), "rev-parse", arg.strip()], text=True).strip()
p = SEC / "data" / "registers" / "prereg.csv"
rows = list(csv.DictReader(open(p)))
cols = list(rows[0].keys())
if "registered_commit" not in cols:
    cols.append("registered_commit")
    cols.append("registration_note")
h = rev()
for r in rows:
    r["registered_commit"] = h
    r["registration_note"] = "the commit carrying the frozen text; re-run this script after each merge that changes prereg.csv"
buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n"); w.writeheader(); w.writerows(rows)
p.write_text(buf.getvalue())
print("pinned", h, "into", p.relative_to(SEC.parent))

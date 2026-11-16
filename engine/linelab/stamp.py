"""
engine/linelab/stamp.py — one deterministic build timestamp for the whole section.

WHY THIS EXISTS
    The first version of these builders stamped `built_utc` from the wall clock.
    That made every rebuild differ from the committed file by exactly one line,
    which broke the reproducibility gate in CI and, worse, made "reproducible"
    a claim the section could not actually demonstrate.

    A build stamp is provenance, not a value. It should identify WHICH inputs
    produced the output, and it should be stable when the inputs are stable.
    So it is derived from the hash of the committed inputs, not from the clock:

        stamp = sha256( all input file bytes )[:12]
        built_from_inputs = that stamp
        built_from_inputs_note = explains it

    The human-readable date of the build is whatever git says the commit is, and
    a reader can see that without the page having to print a clock.
"""
from __future__ import annotations

import hashlib
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def input_paths() -> list[str]:
    """Every committed file a rebuild depends on, in a fixed order."""
    out = []
    raw = os.path.join(ROOT, "raw", "_nfldata")
    for f in ("games.csv", "closing_lines.csv", "sc_lines.csv", "initial_lines.csv"):
        p = os.path.join(raw, f)
        if os.path.exists(p):
            out.append(p)
    caps = os.path.join(ROOT, "data", "linelab", "captures")
    if os.path.isdir(caps):
        for day in sorted(os.listdir(caps)):
            d = os.path.join(caps, day)
            if os.path.isdir(d):
                for f in sorted(os.listdir(d)):
                    out.append(os.path.join(d, f))
    # historical availability joins are read-only inputs owned by signal/
    for f in ("injury_player.csv", "snap_participation.csv"):
        p = os.path.join(ROOT, "signal", "data", f)
        if os.path.exists(p):
            out.append(p)
    p = os.path.join(ROOT, "data", "depth_charts.json")
    if os.path.exists(p):
        out.append(p)
    return out


def build_stamp() -> dict:
    h = hashlib.sha256()
    n = 0
    for p in input_paths():
        h.update(os.path.relpath(p, ROOT).encode())
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        n += 1
    return {
        "built_utc": "derived-from-inputs",
        "built_from_inputs_sha256": h.hexdigest(),
        "built_from_inputs_short": h.hexdigest()[:12],
        "built_from_n_input_files": n,
        "built_from_inputs_note": (
            "This build is identified by a SHA-256 over every input file it read, not by a wall-clock "
            "time. Rebuilding from the same inputs produces this same stamp, which is what the CI "
            "reproducibility gate checks. The date of any given publication is the git commit date."
        ),
    }


def stamp_fields() -> dict:
    return build_stamp()


if __name__ == "__main__":
    import json
    print(json.dumps(build_stamp(), indent=1))

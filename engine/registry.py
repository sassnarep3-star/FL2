"""Pre-commitment registry (SG-16, gate G-04's variant count).

An append-only JSONL log of every strategy variant ever tried. Its only jobs are:
  * make the spec immutable before its evaluation window opens (a hash is enough);
  * give G-04 the honest N — "how many ways did we look at this data" is the input
    that decides whether a good backtest means anything.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone


def canonical_hash(spec: dict) -> str:
    payload = json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def register(spec: dict, path: str = "data/strategy-registry.jsonl",
             when: str | None = None) -> dict:
    if "id" not in spec:
        raise ValueError("a strategy spec needs an id before it can be registered")
    entry = {
        "id": spec["id"],
        "family": spec.get("family", "unspecified"),
        "registered_at": when or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha256": canonical_hash(spec),
        "spec": spec,
    }
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
    return entry


def load(path: str = "data/strategy-registry.jsonl") -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def variant_count(family: str | None = None, path: str = "data/strategy-registry.jsonl",
                  before: str | None = None) -> int:
    rows = load(path)
    if family:
        rows = [r for r in rows if r.get("family") == family]
    if before:
        rows = [r for r in rows if r["registered_at"] <= before]
    return len(rows)


def verify(entry: dict) -> bool:
    """Re-hash a stored entry and confirm the spec has not been edited after registration."""
    return entry.get("sha256") == canonical_hash(entry.get("spec", {}))

"""
FL2 — data acquisition.

Environment constraint (recorded in COORDINATION.md):
  The sandbox may reach github.com / api.github.com / codeload.github.com,
  registry.npmjs.org, pypi.org, files.pythonhosted.org — nothing else.
  raw.githubusercontent.com and objects.githubusercontent.com (the redirect
  target for GitHub *release assets*) are NOT reachable.

Therefore:
  * nflverse "release asset" files (player_stats, injuries, depth_charts,
    snap_counts) CANNOT be downloaded here — they 302 to
    objects.githubusercontent.com. Those are requested through the
    page-fetch path in `docs/SOURCES.md` and are listed as data gaps where a
    page-fetch cannot supply the entire league table.
  * nflverse/nfldata git-tracked CSVs CAN be downloaded through the
    GitHub Contents API with `Accept: application/vnd.github.raw`.

Every file fetched is recorded with URL + sha256 + row count so the build is
auditable.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.request

API = "https://api.github.com/repos/nflverse/nfldata/contents/data/{name}"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")

# name -> (github contents path, human-facing source URL)
FILES = {
    "games.csv": (
        "games.csv",
        "https://github.com/nflverse/nfldata/blob/master/data/games.csv",
    ),
    "closing_lines.csv": (
        "closing_lines.csv",
        "https://github.com/nflverse/nfldata/blob/master/data/closing_lines.csv",
    ),
    "initial_lines.csv": (
        "initial_lines.csv",
        "https://github.com/nflverse/nfldata/blob/master/data/initial_lines.csv",
    ),
    "standings.csv": (
        "standings.csv",
        "https://github.com/nflverse/nfldata/blob/master/data/standings.csv",
    ),
}

MANIFEST_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "manifest.json"
)


def _get(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github.raw",
            "User-Agent": "FL2-research-pipeline",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def fetch_all(manifest: list[dict] | None = None) -> dict[str, str]:
    """Download every declared file into the local cache. Returns name->path."""
    if manifest is not None:
        manifest.append  # noqa: B018  (kept for signature symmetry)
    os.makedirs(CACHE, exist_ok=True)
    out = {}
    records = []
    for name, (remote, source_url) in FILES.items():
        path = os.path.join(CACHE, name)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            blob = _get(API.format(name=remote))
            with open(path, "wb") as fh:
                fh.write(blob)
        with open(path, "rb") as fh:
            raw = fh.read()
        out[name] = path
        records.append(
            {
                "file": name,
                "source_url": source_url,
                "api_url": API.format(name=remote),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
            }
        )
    return out, records


if __name__ == "__main__":
    paths, recs = fetch_all()
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, "w") as fh:
        json.dump({"retrieved_utc": __import__("datetime").datetime.utcnow().isoformat() + "Z",
                   "files": recs}, fh, indent=2)
    print(json.dumps(recs, indent=2))

#!/usr/bin/env python3
"""Fetch every page and every local link target from a RUNNING server; fail on anything non-200.

This is the last check before publish: it proves the site *as served*, not the site as written
(path rewrites, case differences, and a mount id pointing at a dataset name that does not exist
are all invisible to a filesystem check).

    python3 -m http.server 8081 --bind 0.0.0.0 &
    python3 tools/serve_check.py                      # local
    python3 tools/serve_check.py https://<owner>.github.io/FL2/   # after Pages deploys

Exit 0 = every page and every referenced local asset returned 200.
"""
from __future__ import annotations

import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

LOCAL = re.compile(r'(?<![-\w])(?:href|src)="([^"#]+)(?:#[^"]*)?"')
SKIP = ("http://", "https://", "mailto:", "data:", "javascript:")


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8081/"
    if not base.endswith("/"):
        base += "/"
    root = Path(__file__).resolve().parents[1]
    pages = sorted(p.name for p in root.glob("*.html"))
    if not pages:
        print("no pages found next to the repo root", file=sys.stderr)
        return 1

    def fetch(rel: str) -> tuple[int, int]:
        url = base + urllib.parse.quote(rel)
        req = urllib.request.Request(url, headers={"User-Agent": "fl2-serve-check"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, len(r.read())
        except urllib.error.HTTPError as e:  # 404/500 still carry a code
            return e.code, 0
        except Exception as e:  # noqa: BLE001 - DNS/TLS/refused are all "cannot serve"
            return 0, type(e).__name__

    bad: list[str] = []
    fetched: set[str] = set()
    sizes: dict[str, int] = {}

    for page in pages:
        status, _ = fetch(page)
        if status != 200:
            bad.append(f"{page}: HTTP {status}")
            continue
        html = (root / page).read_text(encoding="utf-8")
        for target in LOCAL.findall(html):
            if target.startswith(SKIP) or target in fetched:
                continue
            fetched.add(target)
            st, size = fetch(target)
            if st != 200:
                bad.append(f"{page} -> {target}: HTTP {size if st == 0 else st}"
                           + (" (unreachable)" if st == 0 else ""))
            elif target.endswith((".css", ".js")):
                sizes[target] = size

    print(f"serve check against {base}")
    print("=" * 62)
    print(f"pages: {len(pages)}   local targets fetched: {len(fetched)}   "
          f"total HTML+CSS+JS: {sum(sizes.values()) // 1024} KiB of assets")
    for u in ("", "index.html", "404.html"):
        st, size = fetch(u)
        mark = "OK " if st == 200 else "BAD"
        label = u or "(root)"
        print(f"  {mark} {label} -> {st}" + (f", {size} B" if st == 200 else ""))
    print("-" * 62)
    if bad:
        print(f"{len(bad)} failure(s):")
        for b in bad[:25]:
            print("  x", b)
        return 1
    print("every page and local target served 200")
    return 0


if __name__ == "__main__":
    sys.exit(main())

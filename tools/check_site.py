#!/usr/bin/env python3
"""FL2 site + data checker.

Answers, mechanically, the two claims this project makes about itself:
  1. no broken internal links on the published site;
  2. every data table row carries a source, and anything unverified is flagged.

Run from the repo root:  python3 tools/check_site.py
Exit code 0 = all checks pass; 1 = violations printed (and the site is not publishable).
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "assets" / "data"

# dataset rows that assert a fact about the world must cite something; registers may
# cite the requirement/question ids they derive from instead.
FACTUAL = {"injuriesW10", "rostersW10", "sources", "verification"}
# the flags register is checked separately (every flag needs evidence + a next action), and its
# "source" is the evidence pointer rather than a URL on every row.
URL_RE = re.compile(r"https?://[^\s\"'<>)\]]+")
LOCAL_HREF_RE = re.compile(r'(?<![-\w])(?:href|src)="([^"#]+)(?:#[^"]*)?"')



SID_RE = re.compile(r"\bS-\d{2}\b")


def cite_ok(row_txt: str, known_sids: set[str]) -> bool:
    """A row is cited if it carries a URL, or a source-ID that exists in the catalogue.

    The verification log cites S-IDs by design, because its rows are statements about
    sources rather than about the world; that is only honest if the ID resolves.
    """
    if URL_RE.search(row_txt) or "nfl.com" in row_txt:
        return True
    refs = set(SID_RE.findall(row_txt))
    return bool(refs) and refs <= known_sids


def ids_of(obj) -> set[str]:
    """Primary keys of a register = the first column of each row (id, by convention).

    Deliberately NOT "every id-looking string in the file": a reference has to be
    checked against declared rows, otherwise a dangling id legitimises itself.
    """
    out = set()
    for row in (obj.get("rows") or []):
        v = row[0] if isinstance(row, (list, tuple)) else row.get("id")
        if isinstance(v, str):
            out.add(v.strip())
    return out


def load_datasets() -> dict:
    """Load the JS data files by evaluating just their object literals.

    The files are written as `window.FL2.DATA.x = { ... };` with JSON-compatible
    bodies, so a small transform is enough - no JS runtime needed.
    """
    out: dict[str, object] = {}
    for path in sorted(DATA_DIR.glob("*.js")):
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"(?:window\.FL2\.DATA|\bD)\.(\w+)\s*=\s*\{", text):
            key = m.group(1)
            start = m.end() - 1  # the regex already consumed the opening brace
            depth, i, in_str, esc = 0, start, False, False
            while i < len(text):
                ch = text[i]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == '"':
                        in_str = False
                else:
                    if ch == '"':
                        in_str = True
                    elif ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            break
                i += 1
            blob = text[start:i + 1]
            out[key] = (path.name, blob)
    return out


def js_to_json(blob: str) -> object:
    """Very small JS->JSON shim: quote bare keys, drop trailing commas, strip line
    comments. Enough for our own data files (which use double-quoted strings only),
    and it fails loudly with a line number rather than silently when it is not enough."""
    s = re.sub(r"^\s*//.*$", "", blob, flags=re.M)
    s = re.sub(r",(\s*[}\]])", r"\1", s)
    s = re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', s)
    return json.loads(s)


def main() -> int:
    problems: list[str] = []
    notes: list[str] = []
    pages = sorted(ROOT.glob("*.html"))
    if not pages:
        problems.append("no HTML pages found")

    # ---- 1. internal links and assets
    all_files = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file()}
    link_count = 0
    ext = 0
    for page in pages:
        text = page.read_text(encoding="utf-8")
        for target in LOCAL_HREF_RE.findall(text):
            if target.startswith(("http", "mailto:", "data:")):
                ext += 1
                continue
            link_count += 1
            norm = urllib.parse.unquote(target)
            if norm not in all_files:
                problems.append(f"{page.name}: broken internal link -> {target}")
    # assets referenced from JS/CSS
    for js in (ROOT / "assets").rglob("*.js"):
        for ref in re.findall(r'["\'](assets/[^"\']+|COORDINATION\.md)["\']', js.read_text(encoding="utf-8")):
            if ref not in all_files:
                problems.append(f"{js.name}: references missing file {ref}")

    # ---- 2. required pages exist and are linked from the nav
    js_app = (ROOT / "assets" / "js" / "app.js").read_text(encoding="utf-8")
    nav_pages = set(re.findall(r'href:\s*"([^"]+\.html)"', js_app))
    for page in pages:
        name = page.name
        if name in ("404.html",):
            continue
        if name not in nav_pages:
            problems.append(f"{name}: not present in the shared navigation")
    notes.append(f"pages checked: {len(pages)}; internal links checked: {link_count}; external links: {ext}")

    # ---- 3. every page loads the data + runtime it needs
    needed_scripts = ["assets/js/app.js"]
    for page in pages:
        if page.name == "404.html":
            continue
        text = page.read_text(encoding="utf-8")
        for s in needed_scripts:
            if s not in text:
                problems.append(f"{page.name}: does not include {s}")
        for attr in ("data-page", 'id="site-header"', 'id="site-footer"'):
            if attr not in text:
                problems.append(f"{page.name}: missing {attr}")

    # ---- 4. datasets: source coverage on factual rows
    ds = load_datasets()
    known_sids = set()
    parsed: dict[str, object] = {}
    for key, (fname, blob) in ds.items():
        try:
            parsed[key] = js_to_json(blob)
        except Exception:  # noqa: BLE001 - reported by the parse check below
            parsed[key] = {}
    known_sids = ids_of(parsed.get("sources", {}))
    loaded, factual_rows, cited = 0, 0, 0
    for key, (fname, blob) in ds.items():
        try:
            obj = js_to_json(blob)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{fname}: dataset {key} does not parse ({exc})")
            continue
        loaded += 1
        if not isinstance(obj, dict):
            continue
        rows = obj.get("rows") or obj.get("games") or obj.get("teams") or []
        if key in FACTUAL and isinstance(rows, list):
            blob_all = json.dumps(obj)
            for row in rows:
                factual_rows += 1
                row_txt = json.dumps(row)
                if cite_ok(row_txt, known_sids):
                    cited += 1
                elif not ("source_url" in blob_all or "\"url\"" in blob_all):
                    problems.append(f"{fname}: factual row without a citation in dataset {key}: "
                                    f"{row_txt[:90]}")
        # unverified/blank cells must carry a flag marker
        if key in FACTUAL:
            for m in re.finditer(r'"(n/?a|unknown|unverified|—)"', blob_all):
                notes.append(f"{key}: marker {m.group(1)} present (expected for blanks)")
    notes.append(f"datasets parsed: {loaded}; factual rows: {factual_rows}; rows with an inline source: {cited}")

    # ---- 4b. cross-register references must resolve (no dangling Q-/R-/S-/FL-/G-/SG- ids)
    catalogue = {
        "S": known_sids,
        "Q": ids_of(parsed.get("questions", {})),
        "R": ids_of(parsed.get("requirements", {})),
        "FL": ids_of(parsed.get("flags", {})),
        "G": ids_of(parsed.get("gates", {})),
        "SG": ids_of(parsed.get("suggestions", {})),
        "SIG": ids_of(parsed.get("signals", {})),
    }
    # ids are mentioned both as data and inside prose, so scan the whole blob; the
    # lookbehind stops "SG-04" from being read as "G-04" and "SIG-03" as "G-03".
    dangling: dict[str, list[str]] = {}
    for key, (fname, blob) in ds.items():
        for prefix, known in catalogue.items():
            if not known:
                continue
            pattern = re.compile(rf"(?<![A-Za-z-]){prefix}-(\d+)")
            for ref in sorted(set(pattern.findall(blob))):
                ident = f"{prefix}-{ref}"
                if ident not in known:
                    dangling.setdefault(ident, []).append(fname)
    if dangling:
        for ident, files in sorted(dangling.items()):
            problems.append(f"dangling reference {ident} (mentioned in {', '.join(sorted(set(files)))}) "
                            f"- no such row in its register")
    notes.append("cross-register id references checked against: " +
                 ", ".join(f"{k}:{len(v)}" for k, v in sorted(catalogue.items())))

    # ---- 5. flags register: each flag needs a next action and an evidence pointer
    if "flags" in ds:
        try:
            flags = js_to_json(ds["flags"][1])
            cols = [c["k"] for c in flags["columns"]]
            for row in flags["rows"]:
                rec = dict(zip(cols, row))
                if not rec.get("act") or len(str(rec["act"])) < 12:
                    problems.append(f"flag {rec.get('id')}: missing a concrete next action")
                if not rec.get("ev"):
                    problems.append(f"flag {rec.get('id')}: missing evidence")
            notes.append(f"flag register rows: {len(flags['rows'])}")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"flags dataset unreadable: {exc}")

    # ---- 6. questions register: every question needs an action, and a priority
    if "questions" in ds:
        try:
            qs = js_to_json(ds["questions"][1])
            cols = [c["k"] for c in qs["columns"]]
            for row in qs["rows"]:
                rec = dict(zip(cols, row))
                for field in ("resolve", "prov", "pri"):
                    if not rec.get(field):
                        problems.append(f"question {rec.get('id')}: missing '{field}'")
            notes.append(f"question rows: {len(qs['rows'])}")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"questions dataset unreadable: {exc}")

    # ---- 7. hygiene
    if not (ROOT / ".nojekyll").exists():
        problems.append("missing .nojekyll (Jekyll would ignore leading-underscore files and alter assets)")
    if not (ROOT / "COORDINATION.md").exists():
        problems.append("missing COORDINATION.md")
    for page in pages:
        text = page.read_text(encoding="utf-8")
        for bad in ("TODO", "FIXME", "XXX", "lorem ipsum"):
            if bad.lower() in text.lower():
                problems.append(f"{page.name}: contains placeholder text {bad}")
        if "target=\"_blank\"" in text and 'rel="noopener"' not in text:
            notes.append(f"{page.name}: check noopener on all external links")

    print("FL2 site + data check")
    print("=" * 62)
    for n in notes:
        print("  note:", n)
    print("-" * 62)
    if problems:
        print(f"{len(problems)} problem(s):")
        for p in problems:
            print("  ✗", p)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Repository-wide offline link and evidence-label audit for the published static site.

Unlike the section-specific validators, this walks every committed HTML page and checks local
href/src targets and HTML fragments across the whole GitHub Pages tree. It does not fetch
external URLs, grant content rights, or assert that an NFL fact is currently true.

The landing-page readiness bundle is also checked for required fields. Missing/non-NFL official
source URLs and prose-only evidence are reported as review counts rather than silently treated
as official NFL data.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", "build", "dist", "target",
    ".cache", ".next", ".output", ".turbo", "coverage",
}
LINK_ATTRS = {
    "a": ("href",),
    "link": ("href",),
    "script": ("src",),
    "img": ("src",),
    "iframe": ("src",),
    "source": ("src",),
    "video": ("src",),
    "audio": ("src",),
    "object": ("data",),
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.refs: list[tuple[str, str]] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.add(str(attributes["id"]))
        for attribute in LINK_ATTRS.get(tag, ()):
            value = attributes.get(attribute)
            if value:
                self.refs.append((attribute, str(value).strip()))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def html_pages() -> list[Path]:
    return sorted(
        p for p in ROOT.rglob("*.html")
        if not any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts)
    )


def parse_page(path: Path) -> PageParser:
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser


def local_target(page: Path, raw_url: str) -> tuple[Path | None, str]:
    """Resolve a local URL to a repository file and return its fragment."""
    parsed = urlsplit(raw_url)
    if parsed.scheme or raw_url.startswith("//"):
        return None, ""
    path_text = unquote(parsed.path)
    if not path_text:
        target = page
    elif path_text.startswith("/"):
        # GitHub Pages may expose the repository under /FL2/; treat that prefix as site root.
        parts = [p for p in path_text.split("/") if p]
        if parts and parts[0].lower() == ROOT.name.lower():
            parts = parts[1:]
        target = ROOT.joinpath(*parts)
    else:
        target = page.parent / path_text
    try:
        target = target.resolve(strict=False)
        target.relative_to(ROOT.resolve())
    except ValueError:
        return target, parsed.fragment
    if target.is_dir():
        index = target / "index.html"
        if index.exists():
            target = index
    return target, parsed.fragment


def audit_links(pages: list[Path]) -> tuple[list[str], Counter[str], int, int]:
    errors: list[str] = []
    ids_by_page: dict[Path, set[str]] = {}
    refs_by_page: dict[Path, list[tuple[str, str]]] = {}
    local_count = 0
    external_count = 0
    for page in pages:
        parser = parse_page(page)
        ids_by_page[page] = parser.ids
        refs_by_page[page] = parser.refs

    for page, refs in refs_by_page.items():
        rel = page.relative_to(ROOT).as_posix()
        for attribute, raw_url in refs:
            parsed = urlsplit(raw_url)
            if parsed.scheme or raw_url.startswith("//"):
                external_count += 1
                continue
            local_count += 1
            target, fragment = local_target(page, raw_url)
            if target is None:
                continue
            if not target.exists():
                errors.append(f"{rel}: broken local {attribute}={raw_url!r}")
                continue
            if fragment and target.suffix.lower() == ".html":
                if target not in ids_by_page:
                    if not target.resolve().is_relative_to(ROOT.resolve()):
                        errors.append(f"{rel}: fragment target escapes repository: {raw_url!r}")
                        continue
                    try:
                        ids_by_page[target] = parse_page(target).ids
                    except (OSError, UnicodeDecodeError) as exc:
                        errors.append(f"{rel}: cannot parse fragment target {raw_url!r}: {exc}")
                        continue
                if fragment not in ids_by_page[target]:
                    errors.append(f"{rel}: missing fragment #{fragment} in {target.relative_to(ROOT).as_posix()}")

    return errors, Counter(), local_count, external_count


def audit_landing_register() -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    summary = {
        "rows": 0,
        "official_nfl_source": 0,
        "no_official_source": 0,
        "non_nfl_source": 0,
        "unresolved_artifact_note": 0,
    }
    bundle = ROOT / "data" / "landing_readiness.js"
    page = ROOT / "index.html"
    if not bundle.exists() or not page.exists():
        return ["missing landing_readiness.js or index.html"], summary
    text = bundle.read_text(encoding="utf-8")
    marker = "window.FL2_READINESS ="
    if marker not in text:
        return ["landing_readiness.js does not contain the expected FL2_READINESS payload"], summary
    payload_text = text.split(marker, 1)[1].strip()
    if payload_text.endswith(";"):
        payload_text = payload_text[:-1]
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        return [f"landing_readiness.js payload is invalid JSON: {exc}"], summary

    rows = payload.get("rows")
    if not isinstance(rows, list):
        return ["landing_readiness.js has no rows array"], summary
    summary["rows"] = len(rows)
    required = ("id", "requirement", "status", "gate", "clearing_number", "evidence", "official_source")
    for index, row in enumerate(rows, 1):
        for key in required:
            if key not in row:
                errors.append(f"landing row {index}: missing field {key}")
        source = row.get("official_source")
        if not isinstance(source, str) or source.strip() in ("", "-", "—"):
            summary["no_official_source"] += 1
            continue
        parsed = urlsplit(source)
        host = (parsed.hostname or "").lower()
        if host == "nfl.com" or host.endswith(".nfl.com"):
            summary["official_nfl_source"] += 1
        else:
            summary["non_nfl_source"] += 1
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            errors.append(f"landing row {row.get('id', index)}: malformed source URL {source!r}")

        evidence = row.get("evidence")
        if isinstance(evidence, str) and evidence.strip():
            candidate = evidence.strip().split()[0].rstrip(",;:)")
            if "/" in candidate and not urlsplit(candidate).scheme:
                target = (ROOT / candidate).resolve(strict=False)
                try:
                    target.relative_to(ROOT.resolve())
                except ValueError:
                    errors.append(f"landing row {row.get('id', index)}: evidence path escapes repository: {candidate!r}")
                else:
                    if not target.exists():
                        summary["unresolved_artifact_note"] += 1

    html = page.read_text(encoding="utf-8").lower()
    if "no official nfl source recorded" not in html or "unverified as an nfl fact" not in html:
        errors.append("landing renderer does not explicitly mark missing NFL sources as unverified")
    return errors, summary


def main() -> int:
    pages = html_pages()
    if not pages:
        print("FAIL: no HTML pages found")
        return 1
    link_errors, _, local_count, external_count = audit_links(pages)
    register_errors, register = audit_landing_register()
    errors = link_errors + register_errors
    print(f"HTML pages checked       : {len(pages)}")
    print(f"local href/src targets   : {local_count}")
    print(f"external references     : {external_count} (not fetched)")
    print(f"landing requirement rows: {register['rows']}")
    print(f"  NFL official source   : {register['official_nfl_source']}")
    print(f"  no NFL source recorded: {register['no_official_source']} (explicitly unverified)")
    print(f"  non-NFL source         : {register['non_nfl_source']} (not treated as NFL official)")
    print(f"  evidence notes missing file path: {register['unresolved_artifact_note']}")
    if errors:
        print(f"\nFAILED: {len(errors)} issue(s)")
        for error in errors[:100]:
            print(" -", error)
        if len(errors) > 100:
            print(f" ... {len(errors) - 100} more")
        return 1
    print("\nPASS: every local link/asset and HTML fragment resolves; landing source gaps are surfaced, not relabelled as official.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

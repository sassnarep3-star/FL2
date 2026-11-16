#!/usr/bin/env python3
"""Validate the readiness register, source use, legacy crosswalk, and page shells.

Run `python3 scripts/check_readiness.py --write` when the register schema or
page shell changes. The live table/review cards are rendered from the checked-in
JSON by assets/readiness.js. Default mode is CI's read-only integrity check.
No network access is used: links are checked for HTTPS and a strict official-host
allowlist, not fetched or represented as verified by this script.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "decision-readiness.json"
LEGACY_CSV_PATH = ROOT / "data" / "requirements.csv"
NEWS_CSV_PATH = ROOT / "data" / "news_2026_week10.csv"
CROSSWALK_PATH = ROOT / "data" / "requirements-crosswalk.csv"
RESEARCH_REQUIREMENTS_PATH = ROOT / "research" / "requirements.md"
INDEX_PATH = ROOT / "index.html"
REVIEW_PATH = ROOT / "readiness-review.html"
JS_PATH = ROOT / "assets" / "readiness.js"
CSS_PATH = ROOT / "assets" / "readiness.css"
LEGACY_CSV_FIELDS = [
    "id", "requirement", "category", "deliverable", "where", "status", "note",
    "recorded_date", "current_evidence",
]
CROSSWALK_FIELDS = [
    "inventory_path", "legacy_id", "legacy_requirement", "legacy_status_as_recorded",
    "recorded_date", "readiness_ids", "current_statuses", "current_readiness_count",
    "reconciliation_note",
]
START = "<!-- DECISION-READINESS:START -->"
END = "<!-- DECISION-READINESS:END -->"
EXPECTED_COUNT = 81
OFFICIAL_HOSTS = {
    "nfl.com", "www.nfl.com", "static.www.nfl.com", "operations.nfl.com",
    "weather.gov", "www.weather.gov", "api.weather.gov",
    "patriots.com", "www.patriots.com", "detroitlions.com", "www.detroitlions.com",
    "packers.com", "www.packers.com", "chiefs.com", "www.chiefs.com",
    "49ers.com", "www.49ers.com",
}
STATUSES = {"implemented", "partial", "blocked", "proposed", "needs-review"}
OPEN_STATUSES = {"partial", "blocked", "proposed", "needs-review"}
EVIDENCE_STATES = {
    "official-direct-unarchived", "official-pathway-unarchived",
    "club-unofficial-historical", "stale-or-conflicted",
    "repository-only", "no-official-source",
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def load_payload() -> dict:
    try:
        payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {DATA_PATH.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("requirements"), list):
        raise ValueError("top-level JSON must contain a requirements array")
    return payload


def validate_date(value: object, label: str, errors: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, str):
        errors.append(f"{label}: expected an ISO date string or null")
        return
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        errors.append(f"{label}: invalid ISO date {value!r}")


def validate(payload: dict, *, allow_generated_review: bool = False) -> list[str]:
    errors: list[str] = []
    meta = payload.get("meta", {})
    sources = payload.get("sources", {})
    rows = payload["requirements"]

    if not isinstance(meta, dict):
        return ["meta must be an object"]
    if not isinstance(sources, dict):
        errors.append("sources must be an object keyed by source ID")
        sources = {}
    referenced_source_ids: set[str] = set()
    validate_date(meta.get("audit_date_utc"), "meta.audit_date_utc", errors)
    if meta.get("requirement_count") != EXPECTED_COUNT or len(rows) != EXPECTED_COUNT:
        errors.append(
            f"register must contain exactly {EXPECTED_COUNT} rows and matching requirement_count "
            f"(metadata={meta.get('requirement_count')!r}, data={len(rows)})"
        )
    for field in ("scope_note", "freshness_warning", "clearance_note", "source_policy", "source_capture_policy"):
        if not isinstance(meta.get(field), str) or not meta[field].strip():
            errors.append(f"meta.{field} must be a non-empty explanation")
    freshness_warning = meta.get("freshness_warning", "")
    if not isinstance(freshness_warning, str) or "2026-11-14" not in freshness_warning or "not" not in freshness_warning.lower():
        errors.append("freshness_warning must explicitly identify the Nov 14 snapshot and state that it is not refreshed")
    if not isinstance(meta.get("status_definitions"), dict) or not isinstance(meta.get("evidence_state_definitions"), dict):
        errors.append("meta must define both status and evidence/source-state meanings")
    elif set(meta["evidence_state_definitions"]) != EVIDENCE_STATES:
        errors.append("evidence_state_definitions must define every supported evidence/source state exactly")

    for source_id, source in sources.items():
        if not isinstance(source, dict):
            errors.append(f"source {source_id}: record must be an object")
            continue
        url = source.get("url", "")
        if not isinstance(url, str):
            errors.append(f"source {source_id}: url must be a string")
            url = ""
        try:
            parsed = urlsplit(url)
        except ValueError as exc:
            errors.append(f"source {source_id}: malformed URL {url!r}: {exc}")
            continue
        if parsed.scheme != "https" or (parsed.hostname or "").lower() not in OFFICIAL_HOSTS:
            errors.append(f"source {source_id}: not HTTPS on the official-source allowlist: {url}")
        for field in ("label", "authority", "verification"):
            if not isinstance(source.get(field), str) or not source[field].strip():
                errors.append(f"source {source_id}: missing non-empty {field}")
        if "captured_at_utc" not in source or "sha256" not in source:
            errors.append(f"source {source_id}: must explicitly represent capture timestamp and hash (null means absent)")
        validate_date(source.get("checked_date_utc"), f"source {source_id}.checked_date_utc", errors)
        validate_date(source.get("repository_recorded_date_utc"), f"source {source_id}.repository_recorded_date_utc", errors)
        capture = source.get("captured_at_utc")
        if capture is not None and (not isinstance(capture, str) or not capture.endswith("Z")):
            errors.append(f"source {source_id}: captured_at_utc must be an ISO-8601 UTC timestamp or null")
        digest = source.get("sha256")
        if digest is not None and (not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest.lower())):
            errors.append(f"source {source_id}: sha256 must be 64 hex characters or null")

    expected_ids = [f"REQ-{i:03d}" for i in range(1, EXPECTED_COUNT + 1)]
    ids = [row.get("id") if isinstance(row, dict) else None for row in rows]
    if ids != expected_ids:
        errors.append("requirement IDs must be unique, ordered, and contiguous from REQ-001 through REQ-081")

    for row in rows:
        if not isinstance(row, dict):
            errors.append("every requirements entry must be an object")
            continue
        rid = row.get("id", "<missing id>")
        for field in ("category", "requirement", "status", "finding", "gate", "clearance_metric", "evidence_state", "evidence_note"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                errors.append(f"{rid}: missing required field {field}")
        status = row.get("status")
        if not isinstance(status, str) or status not in STATUSES:
            errors.append(f"{rid}: unsupported status {status!r}")
        evidence_state = row.get("evidence_state")
        if not isinstance(evidence_state, str) or evidence_state not in EVIDENCE_STATES:
            errors.append(f"{rid}: unsupported evidence/source state {evidence_state!r}")

        source_ids = row.get("source_ids", [])
        if not isinstance(source_ids, list):
            errors.append(f"{rid}: source_ids must be an array")
            source_ids = []
        elif not all(isinstance(source_id, str) for source_id in source_ids):
            errors.append(f"{rid}: source_ids must contain only strings")
            source_ids = [source_id for source_id in source_ids if isinstance(source_id, str)]
        elif len(source_ids) != len(set(source_ids)):
            errors.append(f"{rid}: source_ids must not contain duplicates")
        for source_id in source_ids:
            if not isinstance(source_id, str) or source_id not in sources:
                errors.append(f"{rid}: unknown or invalid source ID {source_id!r}")
            elif isinstance(source_id, str):
                referenced_source_ids.add(source_id)
        if isinstance(evidence_state, str) and evidence_state in {"official-direct-unarchived", "official-pathway-unarchived", "club-unofficial-historical"} and not source_ids:
            errors.append(f"{rid}: this evidence state requires at least one linked source")
        if evidence_state == "no-official-source" and source_ids:
            errors.append(f"{rid}: no-official-source state must leave the official source cell blank")
        if evidence_state == "repository-only" and source_ids:
            errors.append(f"{rid}: repository-only findings must use project_refs, not official-source links")
        if evidence_state == "club-unofficial-historical" and not any(isinstance(s, str) and s.startswith("depth_") for s in source_ids):
            errors.append(f"{rid}: club-unofficial-historical must link a stored club chart source")

        flagged = row.get("flagged")
        if not isinstance(flagged, bool):
            errors.append(f"{rid}: flagged must be a boolean")
        elif isinstance(status, str) and status in OPEN_STATUSES and not flagged:
            errors.append(f"{rid}: open status {status} must route to Flagged for Review")
        elif evidence_state == "stale-or-conflicted" and not flagged:
            errors.append(f"{rid}: stale/conflicted evidence must route to Flagged for Review")
        if flagged and row.get("flag_id") != f"FR-{rid}":
            errors.append(f"{rid}: flagged row must have flag_id FR-{rid}")
        if not flagged and row.get("flag_id") is not None:
            errors.append(f"{rid}: unflagged row must have a null flag_id")

        refs = row.get("project_refs", [])
        if not isinstance(refs, list) or not refs:
            errors.append(f"{rid}: project_refs must contain at least one repository-relative path")
            continue
        for ref in refs:
            if not isinstance(ref, str) or not ref or ref.startswith(("/", "http://", "https://")) or ".." in Path(ref).parts:
                errors.append(f"{rid}: project reference must be a safe repository-relative path: {ref!r}")
                continue
            if ref == "readiness-review.html" and allow_generated_review:
                continue
            if not (ROOT / ref).exists():
                errors.append(f"{rid}: repository reference does not exist: {ref}")
    unused_sources = sorted(set(sources) - referenced_source_ids)
    if unused_sources:
        errors.append("source records must be used by at least one row: " + ", ".join(unused_sources))
    return errors


def validate_legacy_inventories(payload: dict) -> list[str]:
    """Check the repaired legacy CSV and its complete many-to-many crosswalk."""
    errors: list[str] = []
    legacy_csv: dict[str, dict[str, str]] = {}
    research_rows: dict[str, dict[str, str]] = {}

    try:
        with LEGACY_CSV_PATH.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames != LEGACY_CSV_FIELDS:
                errors.append(
                    "data/requirements.csv must have the named 9-column schema "
                    f"({', '.join(LEGACY_CSV_FIELDS)})"
                )
            for line_number, row in enumerate(reader, start=2):
                if None in row or any(value is None for value in row.values()):
                    errors.append(f"data/requirements.csv:{line_number}: malformed row width")
                    continue
                legacy_id = row.get("id", "")
                if legacy_id in legacy_csv:
                    errors.append(f"data/requirements.csv:{line_number}: duplicate legacy ID {legacy_id}")
                legacy_csv[legacy_id] = row
                validate_date(row.get("recorded_date"), f"data/requirements.csv:{line_number}.recorded_date", errors)
                refs = [ref.strip() for ref in row.get("current_evidence", "").split(";") if ref.strip()]
                if not refs:
                    errors.append(f"data/requirements.csv:{line_number}: current_evidence must list existing repository paths")
                for ref in refs:
                    if ref.startswith(("/", "http://", "https://")) or ".." in Path(ref).parts:
                        errors.append(f"data/requirements.csv:{line_number}: unsafe current_evidence path {ref!r}")
                    elif not (ROOT / ref).exists():
                        errors.append(f"data/requirements.csv:{line_number}: current_evidence path does not exist: {ref}")
    except (OSError, csv.Error) as exc:
        errors.append(f"cannot read data/requirements.csv: {exc}")

    expected_csv_ids = {f"R{i:02d}" for i in range(1, 26)}
    if set(legacy_csv) != expected_csv_ids:
        errors.append("data/requirements.csv must contain exactly unique IDs R01 through R25")

    news_urls: set[str] = set()
    try:
        with NEWS_CSV_PATH.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh, delimiter="|")
            if not reader.fieldnames or "nfl_url" not in reader.fieldnames:
                errors.append("data/news_2026_week10.csv must expose an nfl_url column for the linked announcement records")
            news_urls = {row.get("nfl_url", "") for row in reader if row.get("nfl_url")}
    except (OSError, csv.Error) as exc:
        errors.append(f"cannot read data/news_2026_week10.csv: {exc}")
    sources = payload.get("sources", {})
    for source_id in ("qb_news_nov11", "qb_news_darnold"):
        source = sources.get(source_id) if isinstance(sources, dict) else None
        if not isinstance(source, dict) or source.get("url") not in news_urls:
            errors.append(f"source {source_id} must match an NFL news URL recorded in data/news_2026_week10.csv")
    req042 = next((row for row in payload["requirements"] if isinstance(row, dict) and row.get("id") == "REQ-042"), {})
    req042_ids = req042.get("source_ids", []) if isinstance(req042, dict) else []
    req042_ids = {source_id for source_id in req042_ids if isinstance(source_id, str)} if isinstance(req042_ids, list) else set()
    if not {"qb_news_nov11", "qb_news_darnold"}.issubset(req042_ids):
        errors.append("REQ-042 must link both locally recorded official starter-announcement pathways")

    try:
        for line_number, line in enumerate(RESEARCH_REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines(), start=1):
            if not re.match(r"^\|\s*R\d+\s*\|", line):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) < 5 or not re.fullmatch(r"R\d+", cells[0]):
                errors.append(f"research/requirements.md:{line_number}: malformed grouped-requirement row")
                continue
            legacy_id = cells[0]
            if legacy_id in research_rows:
                errors.append(f"research/requirements.md:{line_number}: duplicate grouped ID {legacy_id}")
            research_rows[legacy_id] = {
                "requirement": cells[1],
                "status": cells[2].replace("**", "").strip(),
            }
    except OSError as exc:
        errors.append(f"cannot read research/requirements.md: {exc}")

    expected_research_ids = {f"R{i}" for i in range(1, 11)}
    if set(research_rows) != expected_research_ids:
        errors.append("research/requirements.md must contain exactly grouped IDs R1 through R10")

    current_rows = {
        row["id"]: row
        for row in payload["requirements"]
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }
    expected_crosswalk_keys = {
        *(('data/requirements.csv', legacy_id) for legacy_id in expected_csv_ids),
        *(('research/requirements.md', legacy_id) for legacy_id in expected_research_ids),
    }
    seen_keys: set[tuple[str, str]] = set()
    mapped_readiness_ids: set[str] = set()
    try:
        with CROSSWALK_PATH.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames != CROSSWALK_FIELDS:
                errors.append(
                    "data/requirements-crosswalk.csv has an invalid schema "
                    f"(expected: {', '.join(CROSSWALK_FIELDS)})"
                )
            for line_number, row in enumerate(reader, start=2):
                if None in row or any(value is None for value in row.values()):
                    errors.append(f"data/requirements-crosswalk.csv:{line_number}: malformed row width")
                    continue
                inventory = row.get("inventory_path", "")
                legacy_id = row.get("legacy_id", "")
                key = (inventory, legacy_id)
                if key in seen_keys:
                    errors.append(f"data/requirements-crosswalk.csv:{line_number}: duplicate inventory ID {key}")
                seen_keys.add(key)
                if inventory == "data/requirements.csv":
                    source = legacy_csv.get(legacy_id)
                    if source is None:
                        errors.append(f"crosswalk row {line_number}: unknown CSV requirement {legacy_id}")
                    else:
                        expected = (source["requirement"], source["status"], source["recorded_date"])
                        actual = (row["legacy_requirement"], row["legacy_status_as_recorded"], row["recorded_date"])
                        if actual != expected:
                            errors.append(f"crosswalk row {line_number}: legacy CSV text/status/date drift for {legacy_id}")
                elif inventory == "research/requirements.md":
                    source = research_rows.get(legacy_id)
                    if source is None:
                        errors.append(f"crosswalk row {line_number}: unknown grouped requirement {legacy_id}")
                    else:
                        expected = (source["requirement"], source["status"], "")
                        actual = (row["legacy_requirement"], row["legacy_status_as_recorded"], row["recorded_date"])
                        if actual != expected:
                            errors.append(f"crosswalk row {line_number}: grouped requirement text/status drift for {legacy_id}")
                else:
                    errors.append(f"crosswalk row {line_number}: unsupported inventory path {inventory!r}")

                ids = [value.strip() for value in row.get("readiness_ids", "").split(";") if value.strip()]
                if not ids:
                    errors.append(f"crosswalk row {line_number}: readiness_ids must not be empty")
                if len(ids) != len(set(ids)):
                    errors.append(f"crosswalk row {line_number}: duplicate readiness ID")
                for readiness_id in ids:
                    if readiness_id not in current_rows:
                        errors.append(f"crosswalk row {line_number}: unknown readiness ID {readiness_id}")
                    mapped_readiness_ids.add(readiness_id)
                try:
                    if int(row.get("current_readiness_count", "")) != len(ids):
                        errors.append(f"crosswalk row {line_number}: current_readiness_count does not match readiness_ids")
                except ValueError:
                    errors.append(f"crosswalk row {line_number}: current_readiness_count must be an integer")
                states = {
                    current_rows[rid].get("status")
                    for rid in ids
                    if rid in current_rows and isinstance(current_rows[rid].get("status"), str)
                }
                expected_states = ";".join(status for status in ("implemented", "partial", "blocked", "proposed", "needs-review") if status in states)
                if row.get("current_statuses") != expected_states:
                    errors.append(f"crosswalk row {line_number}: current_statuses are stale for {legacy_id}")
                if not row.get("reconciliation_note", "").strip():
                    errors.append(f"crosswalk row {line_number}: reconciliation_note is required")
    except (OSError, csv.Error) as exc:
        errors.append(f"cannot read data/requirements-crosswalk.csv: {exc}")

    if seen_keys != expected_crosswalk_keys:
        missing = sorted(expected_crosswalk_keys - seen_keys)
        extra = sorted(seen_keys - expected_crosswalk_keys)
        errors.append(f"crosswalk must cover each legacy row exactly once (missing={missing}, extra={extra})")
    if mapped_readiness_ids != set(current_rows):
        missing = sorted(set(current_rows) - mapped_readiness_ids)
        extra = sorted(mapped_readiness_ids - set(current_rows))
        errors.append(f"crosswalk must cover all readiness rows (missing={missing}, extra={extra})")

    meta = payload.get("meta")
    scope_note = meta.get("scope_note", "") if isinstance(meta, dict) else ""
    if not isinstance(scope_note, str) or not all(token in scope_note for token in ("data/requirements-crosswalk.csv", "25", "10 grouped")):
        errors.append("meta.scope_note must document the completed legacy crosswalk and its 25/10-row scope")
    return errors


def render_index_section(payload: dict) -> str:
    meta = payload["meta"]
    count = len(payload["requirements"])
    categories = sorted({row["category"] for row in payload["requirements"]})
    # Options are populated from JSON by the same script that renders rows.
    category_note = f"{len(categories)} categories"
    return f'''{START}
<section class="block readiness-block" id="decision-readiness" aria-labelledby="readiness-title">
  <div class="readiness-heading">
    <div>
      <p class="eyebrow">Decision gate · {count} requirements · {esc(category_note)}</p>
      <h2 id="readiness-title">Decision readiness: what blocks a trustworthy decision?</h2>
      <p class="sub">One row per operational requirement, with status, current repository evidence, blocker, explicit clearance measure, evidence/source state, and a review route.</p>
    </div>
    <a class="badge warn" href="readiness-review.html">Flagged for Review ↗</a>
  </div>
  <div class="readiness-caveat note warn">
    <strong>Snapshot and source warning:</strong> {esc(meta["freshness_warning"])}
  </div>
  <div class="readiness-caveat note info">
    <strong>How to read the register:</strong> {esc(meta["clearance_note"])}
    <br><strong>Register scope:</strong> {esc(meta["scope_note"])}
  </div>
  <div class="readiness-controls" role="search" aria-label="Filter decision-readiness requirements">
    <label for="readiness-search">Search requirements
      <input id="readiness-search" type="search" autocomplete="off" placeholder="Search injuries, odds, snapshots…">
    </label>
    <label for="readiness-status-filter">Status
      <select id="readiness-status-filter">
        <option value="">All statuses</option>
        <option value="blocked">Blocked</option>
        <option value="needs-review">Needs review</option>
        <option value="partial">Partial</option>
        <option value="proposed">Proposed</option>
        <option value="implemented">Implemented</option>
      </select>
    </label>
    <label for="readiness-category-filter">Category
      <select id="readiness-category-filter"><option value="">All categories</option></select>
    </label>
    <label class="flagged-toggle" for="readiness-flagged-only">
      <input id="readiness-flagged-only" type="checkbox"> Flagged only
    </label>
    <button id="readiness-clear" type="button">Clear filters</button>
    <span id="readiness-count" aria-live="polite">Loading {count} requirements…</span>
  </div>
  <div class="readiness-kpis" aria-label="Requirement status totals">
    <div class="readiness-kpi"><span>Total</span><strong data-kpi="total">—</strong></div>
    <div class="readiness-kpi"><span>Implemented</span><strong data-kpi="implemented">—</strong></div>
    <div class="readiness-kpi"><span>Partial</span><strong data-kpi="partial">—</strong></div>
    <div class="readiness-kpi"><span>Blocked / review / proposed</span><strong data-kpi="open">—</strong></div>
  </div>
  <p class="readiness-load-state" id="readiness-load-state" role="status">Loading the checked-in readiness register…</p>
  <p class="readiness-error" id="readiness-error" role="alert" hidden></p>
  <p class="readiness-review-empty" id="readiness-empty" hidden>No requirements match these filters.</p>
  <div class="table-wrap readiness-table-wrap">
    <table id="decision-readiness-table" aria-describedby="readiness-table-caption" aria-busy="true">
      <caption id="readiness-table-caption">Requirement-level readiness register. Project references support local-state findings; official links are scope-limited as described beside each row. A blank official-source cell means no applicable official source was verified.</caption>
      <thead><tr>
        <th scope="col">ID / category</th><th scope="col">Requirement / current evidence</th>
        <th scope="col">Status</th><th scope="col">Blocking gate</th>
        <th scope="col">Clearance measure</th><th scope="col">Project evidence</th>
        <th scope="col">Evidence/source state</th><th scope="col">Official source / review</th>
      </tr></thead>
      <tbody id="readiness-rows"></tbody>
    </table>
  </div>
  <noscript><p class="note warn">JavaScript is required to load the searchable table. The full register is available as <a href="data/decision-readiness.json">JSON</a>; open <a href="readiness-review.html">Flagged for Review</a> for unresolved items.</p></noscript>
  <p class="small readiness-footnote">Register data: <a href="data/decision-readiness.json">decision-readiness.json</a> · <a href="readiness-review.html">Flagged for Review</a> · <a href="data/requirements-crosswalk.csv">legacy requirements crosswalk</a> · <a href="research/readiness-reconciliation-2026-11-16.md">reconciliation and source audit</a> · <a href="COORDINATION.md">coordination and integration log</a>.</p>
</section>
{END}'''


def render_review_page(payload: dict) -> str:
    total = len(payload["requirements"])
    flagged = sum(1 for row in payload["requirements"] if row["flagged"])
    meta = payload["meta"]
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Flagged for Review · Decision readiness · FL2</title>
<meta name="description" content="Unresolved evidence, source, coverage, freshness and policy gates in the FL2 NFL decision-readiness register.">
<link rel="stylesheet" href="assets/style.css">
<link rel="stylesheet" href="assets/readiness.css">
<script defer src="assets/readiness.js"></script>
</head>
<body data-readiness-page="review">
<header class="site-header"><div class="inner">
  <div class="brand-row"><a class="brand" href="index.html">FL2 <span>· NFL research hub</span></a><div class="brand-sub">Readiness review · audit date {esc(meta["audit_date_utc"])} UTC</div></div>
  <nav class="tabs" aria-label="Sections"><a href="index.html">Overview</a><a href="index.html#decision-readiness">Decision readiness</a><a href="ledger/suggestions.html">Suggestions</a><a href="ledger/decisions.html">Questions &amp; Answers</a><a href="ledger/flagged.html">Evidence Ledger flags</a></nav>
</div></header>
<main>
  <section class="hero">
    <p class="eyebrow">{flagged} flagged rows · {total} total requirements</p>
    <h1>Flagged for Review</h1>
    <p class="lede">Open data, source, coverage, policy, or validation gates appear here. Linked official sources support only their stated scope; repository findings point to local project evidence. Clearance measures are proposed targets unless explicitly stated otherwise.</p>
    <div class="pills"><span class="badge warn">Unresolved evidence and decisions</span><span class="badge info">{flagged} flagged requirements</span><span class="badge mute">No betting advice</span></div>
  </section>
  <section class="block">
    <div class="note warn"><strong>Freshness warning:</strong> {esc(meta["freshness_warning"])}</div>
    <div class="note info" style="margin-top:10px"><strong>Scope warning:</strong> {esc(meta["scope_note"])}</div>
  </section>
  <section class="block">
    <h2>Open evidence and decision gates</h2>
    <p class="sub">Search the flagged register or choose a status. Missing official-source values are left blank, never inferred. Every card includes its evidence state, clearance measure, project references, and available official links.</p>
    <div class="readiness-review-controls" role="search" aria-label="Filter flagged requirements">
      <label for="readiness-review-search">Search flagged requirements
        <input id="readiness-review-search" type="search" autocomplete="off" placeholder="Search a requirement or evidence note…">
      </label>
      <label for="readiness-review-status">Status
        <select id="readiness-review-status"><option value="">All flagged statuses</option><option value="blocked">Blocked</option><option value="needs-review">Needs review</option><option value="partial">Partial</option><option value="proposed">Proposed</option><option value="implemented">Implemented but flagged</option></select>
      </label>
      <button id="readiness-review-clear" type="button">Clear filters</button>
      <span id="readiness-review-count" aria-live="polite">Loading {flagged} flagged requirements…</span>
    </div>
    <p class="readiness-load-state" id="readiness-review-load-state" role="status">Loading flagged requirements…</p>
    <p class="readiness-error" id="readiness-review-error" role="alert" hidden></p>
    <p class="readiness-review-empty" id="readiness-review-empty" hidden>No flagged requirements match these filters.</p>
    <div class="readiness-flag-list" id="readiness-review-list" aria-live="polite"></div>
  </section>
  <section class="block">
    <div class="note warn"><strong>Do not treat a green/implemented row as end-to-end validation:</strong> status describes the named requirement only. NFL data provenance, model quality, pricing rights, joint-probability gates, and point-in-time capture remain separate. Historical backtests are not prospective leaderboard evidence.</div>
  </section>
</main>
<footer class="footer">FL2 research tool, not betting advice. <a href="index.html#decision-readiness">Return to the readiness table</a> · <a href="data/decision-readiness.json">Raw register JSON</a> · <a href="data/requirements-crosswalk.csv">Legacy requirements crosswalk</a> · <a href="research/readiness-reconciliation-2026-11-16.md">Reconciliation and source audit</a> · <a href="COORDINATION.md">Coordination and verification log</a></footer>
</body>
</html>'''


def ensure_index_shell(text: str, rendered_section: str) -> str:
    if text.count(START) == 1 and text.count(END) == 1:
        start = text.index(START)
        end = text.index(END) + len(END)
        if end <= start:
            raise ValueError("readiness section markers are out of order")
        text = text[:start] + rendered_section + text[end:]
    elif START not in text and END not in text:
        anchor = '  <section class="block">\n    <h2>Evidence Ledger — data, methods, and source notes</h2>'
        if text.count(anchor) != 1:
            raise ValueError("cannot find a unique landing-page insertion point before the Evidence Ledger")
        text = text.replace(anchor, rendered_section + "\n\n" + anchor, 1)
    else:
        raise ValueError("index.html must contain both readiness markers exactly once, or neither")

    style_tag = '<link rel="stylesheet" href="assets/readiness.css">'
    base_style = '<link rel="stylesheet" href="assets/style.css">'
    if text.count(style_tag) > 1:
        raise ValueError("index.html contains duplicate readiness stylesheet links")
    if style_tag not in text:
        if text.count(base_style) != 1:
            raise ValueError("cannot locate the shared stylesheet link in index.html")
        text = text.replace(base_style, base_style + "\n" + style_tag, 1)

    script_tag = '<script defer src="assets/readiness.js"></script>'
    if text.count(script_tag) > 1:
        raise ValueError("index.html contains duplicate readiness script links")
    if script_tag not in text:
        if text.count("</head>") != 1:
            raise ValueError("index.html must have exactly one closing head tag")
        text = text.replace("</head>", script_tag + "\n</head>", 1)

    if text.count('<a href="ledger/flagged.html">Flagged</a>') == 1 and '<a href="index.html#decision-readiness">Readiness</a>' not in text:
        text = text.replace(
            '<a href="ledger/flagged.html">Flagged</a>',
            '<a href="index.html#decision-readiness">Readiness</a>\n      <a href="readiness-review.html">Review queue</a>\n      <a href="ledger/flagged.html">Flagged</a>',
            1,
        )
    if text.count('<a href="index.html#decision-readiness">Readiness</a>') != 1 or text.count('<a href="readiness-review.html">Review queue</a>') != 1:
        raise ValueError("index.html must have one readiness and one review-queue navigation link")
    if text.count("<body data-readiness-page=\"index\">") == 0:
        if text.count("<body>") != 1:
            raise ValueError("index.html must have exactly one simple body tag")
        text = text.replace("<body>", '<body data-readiness-page="index">', 1)
    if text.count('data-readiness-page="index"') != 1:
        raise ValueError("index.html must mark itself as the readiness landing page exactly once")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="regenerate the landing-page shell and review page")
    args = parser.parse_args()
    try:
        payload = load_payload()
        errors = validate(payload, allow_generated_review=args.write)
        errors.extend(validate_legacy_inventories(payload))
        if errors:
            raise ValueError("register validation failed:\n- " + "\n- ".join(errors))
        new_index = ensure_index_shell(INDEX_PATH.read_text(encoding="utf-8"), render_index_section(payload))
        new_review = render_review_page(payload)
        if args.write:
            INDEX_PATH.write_text(new_index, encoding="utf-8")
            REVIEW_PATH.write_text(new_review, encoding="utf-8")
        else:
            if INDEX_PATH.read_text(encoding="utf-8") != new_index:
                raise ValueError("index.html readiness shell or navigation is stale; run python3 scripts/check_readiness.py --write")
            if not REVIEW_PATH.exists() or REVIEW_PATH.read_text(encoding="utf-8") != new_review:
                raise ValueError("readiness-review.html is stale; run python3 scripts/check_readiness.py --write")

        missing = sorted({
            ref
            for row in payload["requirements"]
            for ref in row["project_refs"]
            if not (ROOT / ref).exists()
        })
        if missing:
            raise ValueError("missing repository references: " + ", ".join(missing))
        if not JS_PATH.is_file() or not CSS_PATH.is_file():
            raise ValueError("assets/readiness.js and assets/readiness.css must both exist")
        js = JS_PATH.read_text(encoding="utf-8")
        for required in ("readiness-rows", "readiness-review-list", "Flagged for Review", 'const REVIEW_URL = "readiness-review.html";'):
            if required not in js:
                raise ValueError(f"assets/readiness.js does not implement required UI route/element: {required}")
        for page_name, page in (("index.html", INDEX_PATH), ("readiness-review.html", REVIEW_PATH)):
            content = page.read_text(encoding="utf-8")
            if '<link rel="stylesheet" href="assets/readiness.css">' not in content or '<script defer src="assets/readiness.js"></script>' not in content:
                raise ValueError(f"{page_name} must load the readiness stylesheet and script")
    except (OSError, ValueError) as exc:
        print(f"READINESS CHECK FAILED: {exc}", file=sys.stderr)
        return 1

    action = "Regenerated" if args.write else "Verified"
    print(
        f"{action} {len(payload['requirements'])} readiness rows, "
        f"{sum(row['flagged'] for row in payload['requirements'])} flagged rows, "
        f"{len(payload['sources'])} source records."
    )
    print("Source URLs are allowlist-checked; no external page is fetched or declared freshly hashed by CI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

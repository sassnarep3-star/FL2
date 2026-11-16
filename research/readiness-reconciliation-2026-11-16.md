# Readiness register reconciliation and source audit

**Audit date:** 2026-11-16 UTC

**Scope:** `data/decision-readiness.json` (81 atomic rows), the older CSV inventory, the 10-row grouped Markdown inventory, and the linked source records.
**Outcome:** legacy traceability and local source-state labels are reconciled; full site-wide factual-content verification, point-in-time capture, and several data/model gates remain open.

## Legacy inventories and crosswalk

`data/requirements.csv` had 25 records with eight values per row but only seven header names. The last value on every row is `2026-11-14`; it is now named `recorded_date`. A `current_evidence` column was added with semicolon-separated repository paths checked to exist. The original requirement wording, `where`, status, and note fields are retained; historical paths and status claims are not silently rewritten.

Some original `where` values use `pages/...` paths that no longer resolve from the repository root. Those pointers remain as recorded in the legacy `where` column; use `current_evidence` for the current, checked locations. The ten grouped requirements in `research/requirements.md` also remain intact, with a new note marking their summary claims as historical rather than current-source certification.

[`data/requirements-crosswalk.csv`](../data/requirements-crosswalk.csv) maps all 25 CSV rows and all 10 grouped Markdown rows to the 81 readiness IDs. It is many-to-many: one broad legacy request decomposes into several actionable gates, and a readiness row can support multiple legacy asks. The crosswalk calculates each legacy row's current status summary from the JSON register. Legacy `done` labels are preserved as history; they do not override mapped `partial`, `blocked`, `proposed`, or `needs-review` gates.

The crosswalk's ID coverage is structural and validated by `scripts/check_readiness.py`; it is not a claim that every old factual assertion has been re-proved. Examples where current readiness is narrower than a legacy status include:

- Legacy R14 said the Week 10 injury snapshot was checked row by row. The current files remain a Nov 14 snapshot; a few dynamic official pages were read Nov 16 without saving their responses or hashes. Row/section counts differ by source representation and remain under REQ-049.
- Legacy R15/R16 recorded depth-chart coverage as two of 32 clubs. Five club-site chart records now appear in the local register, but they are explicitly unofficial and were not re-fetched during this audit. League-wide chart, starter, and playing-time coverage remains open.
- Legacy R19/R20 described universal row-level sourcing and blanking. This integration rechecked structure and known source scope, but did not manually compare every factual cell across every site.
- Legacy R24 says PR/Pages deployment was done for an earlier delivery. The current branch's own integration PR and deployment remain a separate gate under REQ-081 until verified.

## Source-record audit

The JSON contains 20 source records: 15 NFL/NWS-hosted records (including two tested 404 URLs) and five club-site chart records. Every URL is HTTPS and on the checker’s official NFL/club/NWS host allowlist. All source records explicitly have null `captured_at_utc` and `sha256`: a checked date or clickable dynamic URL is not an archived snapshot. CI does not fetch these pages or certify their contents.

| Source record(s) | Scope established by the recorded check | Limitation retained in the register |
|---|---|---|
| `injury_w10` | NFL 2026 Week 10 injury-report page; selected sections and Detroit game-status rows were visible on Nov 16 | Dynamic page, not the local Nov 14 file; not archived/hashed and not a full row-by-row comparison |
| `qb_news_nov11`, `qb_news_darnold` | NFL.com news URLs recorded in the local Week 10 news CSV: a Nov 11 roundup and a Sam Darnold/Drew Lock announcement | The dynamic articles were not re-fetched in this audit; local links/headlines do not establish current page contents or all-team starter coverage |
| `schedule_w10` | NFL Week 10 schedule/results, including the Nov 12 WAS–NYG and Nov 15 NE–DET finals | Not an immutable, complete results ledger |
| `schedule_release` | NFL schedule-release page; links to the season schedule and names FC Bayern Munich Stadium for NE–DET | Does not establish venue coverage for all 14 Week 10 games |
| `transactions_ir` | Dated November reserve/injured transactions | Not a complete point-in-time 32-team roster/IR snapshot |
| `gamebook` | One NFL Game Book sample: Miami–San Francisco, Sep 20, 2026 | Not a Week 10 book; its notice limits use to media coverage and requires written permission for other use; project reuse permission is not established |
| `roster` | NFL Buffalo Bills roster page | One club only; roster status is not a depth chart or game-specific starter list |
| `team_stats`, `player_stats` | NFL category pages for 2026 team/player statistics | Source pathways/input examples only; they do not verify local derived calculations or establish a league-wide snap-count feed |
| `snap_counts_offense`, `snap_counts_defense` | The two tested NFL snap-count category URLs | Both returned NFL 404 pages on Nov 16. This proves only those tested URLs failed, not that no other official feed exists |
| `standings` | Dynamic NFL standings page displaying current-season records | Newer than local Nov 14 files; not archived/hashed and not a version-matched reconciliation |
| `rulebook` | NFL Football Operations 2026 Rulebook; rule-change table states rule 6-1-6 permits a declared onside kick at any time | Supports that rule only, not its rate, model effect, or a performance claim |
| `nws` | NWS API documentation: open-data guidance and identifying User-Agent requirement | Documentation only; no stadium-level forecast was captured |
| `depth_ne`, `depth_det`, `depth_gb`, `depth_kc`, `depth_sf` | Five club-site depth-chart URLs recorded in local data | Club-published charts are labeled unofficial; pages were not re-fetched in this audit and do not establish actual starters or snaps |

Source links are displayed according to evidence state, not as blanket certification. `official-direct-unarchived` supports only its named external fact; `official-pathway-unarchived` indicates a route or limited example; `stale-or-conflicted` links are contextual and do not resolve local conflicts. `club-unofficial-historical` remains explicitly distinct from NFL-issued evidence. Repository-only rows now have no external source IDs, and `no-official-source` rows intentionally leave the official-source field blank. Local project paths are the evidence for those states.

## Remaining gates

- **Price data and rights:** no approved sportsbook quote/consensus feed or retention/redistribution policy (`REQ-001`, `REQ-020`, `REQ-060`). The Week 10 market fields point to nflverse, not a sportsbook quote source.
- **Results and evaluation:** point-in-time result corpus, immutable registration, and consistent chronological train/validation/holdout splits remain incomplete (`REQ-002`, `REQ-019`, `REQ-026`, `REQ-035`, `REQ-070`).
- **Availability and depth:** no complete league-wide roster/IR, official depth, expected/actual starter, inactive, or snap-count evidence; the five recorded club charts are not league-wide or NFL-issued (`REQ-006`, `REQ-010`, `REQ-011`, `REQ-013`, `REQ-031`, `REQ-043`, `REQ-052`, `REQ-056`, `REQ-074`).
- **Point-in-time evidence:** immutable injury/depth/inactive snapshots, capture timestamps/hashes, daily deltas, and schema/freshness alarms are not complete (`REQ-021`, `REQ-029`, `REQ-030`, `REQ-039`, `REQ-047`, `REQ-049`, `REQ-054`, `REQ-055`, `REQ-063`, `REQ-066`).
- **Methods and conflicts:** market-price coverage, injury-adjustment wording, correlation scope, and cross-pipeline evaluation claims need reconciliation before performance or leaderboard use (`REQ-004`, `REQ-007`, `REQ-012`, `REQ-018`, `REQ-027`, `REQ-028`, `REQ-038`, `REQ-053`, `REQ-062`, `REQ-073`).
- **Full source-content audit:** static link/table checks do not validate external page contents or every local factual cell. The row-by-row factual-source/blank-and-flag audit remains open (`REQ-077`, `REQ-079`).
- **Release gate:** merge only after checks pass; verify the deployment and live readiness page after the integration PR merges (`REQ-081`).

The readiness page and review queue are the operational source of truth for each gate. This note documents the bounded reconciliation completed here; it does not turn historical snapshots or local validation results into current NFL facts.

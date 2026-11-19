# Verification record — session arena/03babc1b-fl2 (2026-11-19)

Scope: repository review and official-source spot checks. No dataset rows were added or changed.
Recorded by a manual page fetch, not by an automated collector.

## 1. Official sources checked (manual, one page each)

| Check | Official source | What the page showed on 2026-11-19 (UTC) |
|---|---|---|
| Injury report currency | https://www.nfl.com/injuries/ | Header reads "Official Latest NFL Injury Report for Players - Week 11 of the 2026 Season". First listed game is Thursday, November 19, IND (Colts) at HOU (Texans), 8:15 PM EST, Prime Video. |
| Sample row (Colts) | https://www.nfl.com/injuries/ | Sauce Gardner, CB, Calf, "Did Not Participate In Practice", Game Status "Questionable". Recorded only as displayed on the fetch date. |
| Terms of use §1.3 | https://www.nfl.com/legal/terms/ | Page says "Updated: May 16, 2024". §1.3 reads: "Systematic retrieval of data or other content from the Services, whether to create or compile, directly or indirectly, a collection, compilation, database, or directory, is prohibited absent our express prior written consent." |

## 2. Irregularities (for the Flagged for Review page)

| ID | Irregularity | Status |
|---|---|---|
| S-01 | The latest committed injury data is Week 10 (captures dated 2026-11-14 and 2026-11-16). The official NFL injury page shows Week 11 on 2026-11-19. The repo is one week behind. | needs review |
| S-02 | Scheduled workflows contacted nfl.com while the repo's own gate (F-T1 / F-AUD-01) said automated collection was not authorized. Two schedules were live: `fl2-lines-snapshot.yml` (Wed/Thu/Fri) and `fl2-depth-capture.yml` (Tuesday, plus a push trigger). | **Paused in this session.** Schedule and push triggers are commented out with a reason. Manual dispatch remains. Needs owner review. |
| S-03 | Terms §1.3 prohibits systematic retrieval without written consent. The repo has no recorded consent. The Terms text fetched here is the page's "Updated: May 16, 2024" version; the complete review is not recorded. | needs review (open gate F-T1) |
| S-04 | The README said workflow configurations were inconsistent. After S-02 they are consistent: all nfl.com-touching workflows are manual-only. The README itself is integration-owned and was not edited here. | needs review (integration session) |

## 3. Checks run (baseline, before and after edits)

All of these passed on the workspace after the workflow edits:

- `python3 scripts/check_site.py`
- `python3 tools/check_links.py`
- `python3 tools/check_signals_links.py`
- `python3 engine/linelab/check_site.py`
- `python3 fl2-lines/engine/check.py`
- `python3 ops/check_readiness.py`
- `python3 signal/analysis/verify.py`
- `python3 tools/check_integrated_site.py`
- `python3 tools/check_decision_desk.py`

Workflow YAML was parsed with PyYAML (both edited files load; their `on:` blocks now list only `workflow_dispatch`, plus `push` for `fl2-lines-check`, which is unchanged).

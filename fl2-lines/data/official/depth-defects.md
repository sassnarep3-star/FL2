# Depth-chart defects named in the brief, and what this session could verify

| item | claim in the brief | what is verifiable today | consequence |
|---|---|---|---|
| Texans publish depth as an image | yes, reported by an earlier session | not reproducible inside this sandbox: club pages are reachable only through the fetch layer, and an image has no rows to read | R32 stays `needs review`; the fix is an authorised structured source, not a transcription by eye |
| Packers prefix jersey numbers, breaking the parser | reported | the mechanism is consistent with what the committed mirror does: `depth_player.csv` holds 0 rows for 2026 | see the parser defect below; both fixes need a re-capture with the raw string retained |
| 149 slots list more than one rank-1 player | reported | cannot be re-measured for 2026 because the committed depth aggregate has no 2026 rows at all | R33/R51 stay blocked; the register must allow a slot to hold 0, 1 or many players |
| Baltimore still lists Jackson/Huntley after IR | reported | the injuries mirror carries **no reserve list at all** (0 reserve rows in 42,179), so "not listed" cannot be distinguished from "healthy" in any feed we hold | R64 blocked; a stale-row flag against the transactions log also needs the register that does not exist (R46) |

## The parser defect this session found

`signal/data/aggregate_report.json` records that `depth_charts_2026.csv` was downloaded
with **784,796 rows and 12 columns** (2025: 554,215 rows, 12 columns). The committed
output `signal/data/depth_player.csv` contains **0 rows for 2026** (verified by counting
`season == 2026` in that file). The aggregation code keeps rows where
`depth_team in [1, 2]` and reads `club_code`/`depth_team`/`football_name`, which are the
2020–2024 headers; the 2025/2026 files use a different header set, so every 2025 and 2026
row is silently dropped.

Clearing number for R32/R33/R43/R51/R52: **depth_player.csv must contain > 0 rows for 2026
with a per-row date and source**, and a slot may carry two rank-1 players. Until then the
backup-deficiency feature is not built, per the brief's own instruction.

# 2. Never fill an unconfirmable value: blank + flag

Date: 2026-11-14 · Status: **accepted** · Session: `arena-be3108f3`

## Context
Several inputs the brief asks for do not exist in any source reachable this session: no official odds/CLV feed, no
official depth chart, no complete roster status segments, no licensed play-by-play data. The tempting alternatives
were a "typical" 4.5% vig figure, a depth ordering inferred from jersey numbers, and treating a blank designation
as "available".

## Decision
Rule R-05 is absolute: a value not confirmed from a source in its allowed tier is rendered **blank** and recorded as
a flag with evidence and a next action. Model output is labelled `computed (ours)` and never dressed as an official
number. Concretely: all vig/hold/edge/CLV cells on the site are empty (FL-014); the depth example is explicitly
alphabetical, not a depth ordering (FL-013); "no players on IR" is not stated because the capture was truncated
(FL-002).

## Consequences
+ The site's silence is information: a reader can see exactly which claims are unsupported.
+ Gates that need market data report `unknown`, and `unknown` blocks promotion — a missing input cannot become a
  pass by omission (`engine/gates.py`).
− Pages look incomplete, and some sections (leaderboard standings) are empty. Accepted: an incomplete table is
  correct, a filled one would be a fabrication.

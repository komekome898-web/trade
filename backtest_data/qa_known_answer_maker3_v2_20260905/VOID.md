# VOID — 2026-09-05 lead review

This v2 packet is kept as a record but is NOT used for auditor testing.
Reason: the background book is degenerate — spread sits at the MAX_SPREAD_TICKS=40 circuit breaker
(37–42 ticks ≈ 37–42 bps in 84% of rows; instrument tick = 1 bps), per-position maker P&L is ±30–60 bps,
non-forced S1 mean +29 bps, S2 +14.5 bps. Such a world cannot say anything about maker fill models.
The generator's informed-flow tuning was done by adding circuit breakers instead of fixing the dynamics.
A v3 must have a stable book (spread 1–3 ticks ≥ 85% of rows, no breakers) before any auditor sees it.

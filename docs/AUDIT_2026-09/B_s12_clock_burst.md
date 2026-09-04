# Audit B: S12 Clock-Window Burst Momentum — Blind Re-derivation

Data used: `executions_FX_BTC_JPY_31d_20260823.csv.gz` (982000 rows, 2026-07-23 12:09:27.130000+00:00 .. 2026-08-23 12:25:34.217000+00:00); fresh tape `paper_logs/tape/executions_20260825..20260904.csv.gz` (440461 rows, 2026-08-25 00:00:00.409170200+00:00 .. 2026-09-04 12:32:18.080769200+00:00); `binance_BTCUSDT_1m.csv` (2026-07-30 02:26:00+00:00 .. 2026-08-20 02:25:00+00:00). No bid/ask book was available; **last-trade price used as mid proxy** (caveat, see Q5).

## Q1 — Denominator re-derivation
- MAIN 31d, in-window: n=51, gross mean=13.40bps, net mean=5.48bps, 95% CI(day-cluster boot)=[-9.92, 19.69]
- MAIN excl-triggers-near-gap(<120s after >30s gap): n=36, net mean=5.40bps, CI=[-11.25,22.02]
- FRESH 11d (2026-08-25..09-04), in-window: n=31, gross mean=5.31bps, net mean=-2.61bps, CI=[-16.21,13.65]
- FRESH excl-near-gap: n=25, net mean=0.75bps, CI=[-18.54,22.09]

## Q2 — Controls table (gross bps unless noted)
| variant | n | gross mean | net mean | 95% CI net |
|---|---|---|---|---|
| in-window (claim) | 51 | 13.40 | 5.48 | [-9.92,19.69] |
| outside-window (all other hrs) | 161 | 2.93 | -4.99 | [-14.03,7.18] |
| random 2.5h #0 (0 days 18:24:06.904583400-0 days 20:54:06.904583400) | 19 | -8.61 | -16.53 | [-31.68,-1.48] |
| random 2.5h #1 (0 days 18:37:37.221121250-0 days 21:07:37.221121250) | 16 | -4.49 | -12.41 | [-38.15,6.16] |
| random 2.5h #2 (0 days 04:38:28.745413814-0 days 07:08:28.745413814) | 14 | 7.56 | -0.36 | [-20.71,19.64] |
| random 2.5h #3 (0 days 19:11:44.286068954-0 days 21:41:44.286068954) | 17 | 5.14 | -2.78 | [-19.38,12.93] |
| random 2.5h #4 (0 days 09:44:56.393552462-0 days 12:14:56.393552462) | 22 | -12.12 | -20.04 | [-30.72,-10.37] |
| in-window FADE (reversed) | 51 | -13.40 | -21.32 | [-35.53,-5.92] |

## Q3 — Translation
- MAIN: freq=1.59/day (claim 1.44/day), worst trade net=-92.7bps (claim -62bps), days with >=1 trade=69%
  per-day net-bps-sum stats: mean=12.7, std=83.6, min=-148.7, max=167.1
- FRESH: freq=2.82/day, worst trade net=-62.9bps, days with >=1 trade=91%

## Q4 — Relative vs absolute threshold
- In-window: 279000 valid 60s-disp seconds, 20bps threshold = 1.427th pctile-from-top (i.e. 1.43% of seconds exceed it); 90/95/99 pctile of |60s move| = [ 9.65113691 13.10220845 22.23928718]
- Outside-window: 2400308 seconds, 20bps threshold exceedance rate = 0.477%; 90/95/99 pctile = [ 5.91848039  8.21563097 15.49098387]
- The two exceedance rates are similar (98.57% below-thresh in-window vs 99.52% outside) — a **fixed 20bps threshold is not obviously window-specific**; a percentile-matched trigger (e.g. in-window 95th pctile applied everywhere) would change which seconds fire outside the window.

## Q5 — Definition side-effects
- Flat-only suppression: 3930 of 3981 in-window trigger-seconds (98.7%) suppressed while already holding a position (30-min hold blocks re-entry).
- Fill slippage vs mid-at-trigger (first print in trigger direction, next second): mean=-0.51bps, median=0.00bps (already excludes the 3.96bps taker fee — this is *extra* adverse selection from using next-second print instead of the trigger-second mid).

## Q6 — Data validity
- MAIN tape: gaps>30s = 17039 (max 810s), dup timestamps=377403, >1% single-tick jumps=9
- FRESH tape: gaps>30s = 3228 (max 37308s), dup timestamps=170846
- Excluding triggers within 120s of a >30s gap changes MAIN net mean from 5.48 to 5.40bps (n 51->36).

## Q7 — Selection contamination (permutation null, approx.)
- Null model: within-day |gross_bps| magnitudes kept, sign randomized per trade, cluster-bootstrapped by day, max over N=1190 simulated 'cells' repeated 40 times (compute-limited approximation, not the real 1,190-cell grid).
- Expected best-of-1190 gross bps under null: mean=26.71, 95th pctile=31.48, vs claimed +23.71bps. Claim is within/below plausible best-of-N noise range — treat as order-of-magnitude only (real search grid/filters not reproduced).

## Q8 — Simplest alternative explanation
- Outside-window applying the identical rule already gives gross=2.93bps net=-4.99bps on n=161. This differs materially from the in-window result, suggesting some window-specific component may be present, but sample sizes are small.

## Q9 — Time-of-day storm-lift consistency
- MAIN tape hourly >=20bps/60s trigger rate (%): window(12-14h)=1.2375%, other hours mean=0.4816%, lift=2.57x
- Binance BTCUSDT 1m (2026-07-30..2026-08-20), |30m return|>=0.8% hourly rate: window=2.011%, other=0.465%, lift=4.33x
- Claimed lift was 2.23x. Recomputed: bitFlyer-tape-proxy=2.57x, Binance-longer-window=4.33x.

## Q10 — Falsification sentence
If, on the fresh forward tape (2026-08-25 onward) or on a permutation-null best-of-1190 search, the in-window net mean is statistically indistinguishable from zero or from the all-other-hours control, the clock-window-specific edge claim is falsified.

## Minimum detectable effect (MDE)
- Trade-level SD (MAIN net bps) ~ 57.3bps. MDE (95%, two-sided, iid approx) at n=40: 17.75bps; at n=30 (forward): 20.49bps.
- These are naive iid MDEs; day-clustering (only ~32 independent days) is the real effective-n constraint — the day-clustered bootstrap CIs above are the more honest uncertainty bars.

## VERDICT
| metric | claimed | recomputed (MAIN) | recomputed (FRESH) |
|---|---|---|---|
| n | 40 | 51 | 31 |
| gross bps/trade | +23.71 | 13.40 | 5.31 |
| net bps/trade (7.92bps RT) | +15.79 (implied) | 5.48 | -2.61 |
| CI | [+7.92,+37.27] (gross) | [-9.92,19.69] (net) | [-16.21,13.65] (net) |
| freq/day | 1.44 | 1.59 | 2.82 |
| worst trade | -62bps | -92.7bps | -62.9bps |

**VERDICT: 結論変更**

Justification: own trigger/hold/cost implementation on the same tape reproduces the qualitative shape (rare, large-|move| momentum-continuation trades) but n and the exact gross/CI differ from the recorded numbers, primarily because (a) mid was proxied by last-trade price (no book snapshot available), (b) the exact 60s-window convention (inclusive/exclusive, trailing-tick vs trailing-time) is not fully specified in the claim text, and (c) the Q7/Q8 controls above should be read together with the CI before treating the point estimate as decision-grade.

## Files read
- backtest_data/executions_FX_BTC_JPY_31d_20260823.csv.gz
- backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz (header only)
- backtest_data/binance_BTCUSDT_1m.csv
- paper_logs/tape/executions_20260825..20260904.csv.gz (11 files)
- backtest_data/storm_events_20260820/event_20260721_1410.csv.gz (header only)
- backtest_data/burst_events_20260820/event_20260721_1746.csv.gz (header only)
- No files under docs/, scripts/research_*.py, scripts/judge_*.py, scripts/build_*.py, scripts/paper_*.py, or KNOWLEDGE*.md were opened.
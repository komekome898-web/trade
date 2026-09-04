# Blind Audit C — Board Imbalance Taker (Rejection Claim)

**VERDICT: 数値差異(結論維持)** — sign/order of magnitude for effect (1) reproduces closely;
effect (2) reproduces in direction and rough scale but the claimed 5.8bps cost does not
reproduce from raw data (my measurement: ~1.9bps). Even at this much lower, more permissive
cost floor, no control-passing cell clears cost. Final REJECT conclusion is maintained.

## Files read
`config/config.yaml`, `config/products.yaml`,
`backtest_data/board_round_20260904/board_round_coverage.json`,
`backtest_data/board_round_20260904/board_round_series_5s.csv.gz`,
`paper_logs/tape/ticker_{20260820..20260904}.csv.gz` (16 files),
`paper_logs/tape/executions_{20260820..20260904}.csv.gz` (16 files).
No docs/, research_*/judge_*/run_board_round/tp_operating_curve, or KNOWLEDGE files opened. No git history used.

## 1. Denominator & method
5s series: raw 249,336 rows (2026-08-20 06:13 – 2026-09-04 12:50 UTC).
Validity filter: drop daily maintenance window 19:00–19:12 UTC (1,521 rows), spread_bps≤0 or
>50bps (21 rows, crossed/garbage book), non-positive top/depth sizes (14 rows) → **247,780 valid
rows**. Median spread_bps (valid) = 1.77. Deciles/quintiles: **whole-sample qcut** (not rolling).
Forward returns are **non-overlapping only in the sense of contiguity** — each row's forward
window is required to be an unbroken run of 5s steps (99.97% of steps are exactly 5s); returns
across rows do overlap in calendar time (standard for this kind of table, but t-stats below are
therefore optimistic — not IID). Ticker (1s) series: 16 files, forward-filled to 1s grid (limit
30s), maintenance window dropped → 1,237,477 1s-bins.

## Table (1) recompute — imb_top quintiles × forward mid drift, TICKER 1s data (true 1s/5s/30s)
| horizon | gross (top−bot quintile), bps | t |
|---|---|---|
| 1s | 0.075 | 37.3 |
| 5s | 0.136 | 27.9 |
| 30s | 0.206 | 16.5 |
Claimed range 0.08–0.26bps — **reproduces closely** (my 0.075–0.206bps). Same signal computed
on the 5s board series (imb_top, h=30/120/300s) gives 0.218/0.279/0.250bps — consistent order of
magnitude, confirming cross-source agreement (Q9).

## Table (2) recompute — imb_5bps deciles (long D10/short D1), 5s series
**All-time (n≈24.4k per decile-leg):**
| horizon | top mean | bot mean | gross bps | t |
|---|---|---|---|---|
| 30s | 0.213 | −0.113 | 0.326 | 7.38 |
| 120s | 0.360 | −0.098 | 0.458 | 5.30 |
| 300s | 0.481 | 0.221 | 0.259 | 1.96 |

**Time window 12:30–15:00 UTC (n≈2.7k per leg):**
| horizon | top mean | bot mean | gross bps | t |
|---|---|---|---|---|
| 30s | 0.639 | −0.263 | 0.902 | 4.95 |
| 120s | 1.501 | 0.254 | 1.247 | 3.47 |
| 300s | 2.234 | 2.014 | 0.220 | 0.39 (n.s.) |

Claimed "+0.2 to +2.2bps": my paired long−short range is **0.22–1.25bps**; the 2.2bps figure
likely matches the *long-only* level (top_mean=2.234 at tw/300s), not the excess over the
matched short leg, which at that cell is insignificant (t=0.39, baseline drift ~2bps there).
Correct paired comparison: no recomputed cell reaches 2.2bps net of baseline.

## 2. Controls (imb_5bps, h=300s, all-time)
- **Random-sign placebo**: gross 0.028bps, t=0.22 → clean null, as expected.
- **Lag +5min (imbalance from t−300s vs return over [t,t+300s])**: gross 0.429bps, t=3.22 —
  **NOT ≈0**, comparable in size to the live-signal effect (0.259bps). This means a large share
  of the "signal" is order-flow/return persistence over minutes, not an instantaneous
  imbalance→drift relationship. This weakens the interpretation of (2) as clean microstructure
  causality, independent of the cost question.
- **Reversed sign**: by construction, exactly −1× the real gross; not separately estimated.

## 3. Cost translation
Fee: `config/products.yaml` states **FX_BTC_JPY taker_fee_pct = 0.0** (the 0.15% in
`config/config.yaml: costs.taker_fee_pct` is a generic/spot default, not applicable to
FX_BTC_JPY — using it would be a product mismatch). Median spread from ticker files (16 days,
1,237,477 quotes) = **1.911bps** (5s-series median = 1.773bps, close). My round-trip taker cost
= spread + 2×fee = **≈1.9bps**, materially below the claimed **5.8bps**. No combination of (fee,
spread) I can derive from this data reaches 5.8bps — even the wrong generic-spot fee (0.15%×2 =
30bps) overshoots it, not matches it. This is the single largest numeric discrepancy in the
audit; I cannot reproduce the 5.8bps figure from raw data and flag it for reconciliation.
**Even so**, using my lower, more permissive 1.9bps floor: the best paired, control-surviving
cell (tw, h=120s) grosses 1.247bps < 1.9bps — still short. Break-even would require cost ≤
~1.25bps, i.e. a spread below the observed median — not supported by the data.

## 4. Relative vs absolute — spread/vol tercile split (imb_5bps D10/D1, h=300s)
| split | bucket | gross bps | t |
|---|---|---|---|
| spread | low (med 1.11bps) | −0.454 | −2.36 |
| spread | mid (med 1.77bps) | 0.363 | 1.78 |
| spread | high (med 2.60bps) | 1.012 | 3.63 |
| vol | low (med 0.74bps) | −0.678 | −5.35 |
| vol | mid (med 1.22bps) | −0.060 | −0.33 |
| vol | high (med 2.06bps) | 1.499 | 4.78 |
Effect is **not monotone/stable** — it flips sign in low-spread and low/mid-vol regimes. Only
the high-spread and high-vol terciles show the claimed-direction effect, and in both, the
regime's own cost (spread) is also elevated (high-spread tercile median 2.60bps > gross
1.01bps). **No cell has gross > locally-matched cost.**

## 5. Mechanical selection (executions vs mid)
Paired mid/trade-price forward returns (5s horizon, 575,802 rows): corr(fwd_mid, fwd_tradepx) =
0.799; means 0.019 vs 0.021bps; stds 2.24 vs 2.49bps. Trade prices and mid track closely with no
outsized divergence — no evidence that extreme-imbalance bins are dominated by a mechanical
thin-side-consumption artifact distinct from the mid itself.

## 6. Data validity — with/without filter
Excluded rows are a small fraction (1,556 / 249,336 = 0.62%), dominated by the maintenance
window. Their inclusion/exclusion does not materially move deciles built on 247k+ rows; the
crossed-book rows (spread≤0) are the ones that would meaningfully corrupt qcut boundaries if
left in, which is why they are excluded.

## 7. Selection / parameter sweep
Only two depth proxies exist in this dataset (`imb_top` = 0bps/top-of-book, `imb_5bps`) — **no
2bps or 10bps depth columns are present** in `board_round_series_5s.csv.gz`, so the requested
{2,5,10}bps sweep cannot be run without re-deriving raw L2 depth (out of scope/no source data
here). Reporting the available sweep as an upper bound:
imb_top: 30s/0.218(t7.84), 120s/0.279(t5.03), 300s/0.250(t2.92);
imb_5bps: 30s/0.326(t7.38), 120s/**0.458(t5.30, MAX)**, 300s/0.259(t1.96).
Max gross over this sweep = **0.458bps** (imb_5bps, 120s) — well under any plausible cost floor.

## 8. Simplest alternative
The lag-placebo result (§2) indicates the effect is largely explained by short-horizon
order-flow/return autocorrelation (a "known law" of microstructure — imbalance and returns both
trend over minutes) rather than a distinct exploitable causal signal. Not simple bid-ask bounce
(random-sign placebo is clean, so it isn't just an artifact of the bucketing), but consistent
with generic short-horizon momentum/persistence.

## 9. 5s vs 1s consistency
imb_top, h=30s: 5s-series gross 0.218bps (t=7.84) vs ticker 1s-series gross 0.206bps (t=16.5).
**Sign and magnitude agree closely** across the two independent data sources.

## 10. Falsification & MDE
Falsification sentence: the closure would be falsified by a cell where, after (a) whole-sample
deciles, (b) contiguity-filtered non-overlapping-window forward returns, (c) survival of the
random-sign and +5min-lag placebos, and (d) a locally-matched round-trip cost (same
spread/vol regime), the long−short gross return exceeds cost with t>3 and replicates on fresh
data. No cell in this recompute meets all four conditions simultaneously.
MDE at h=300s (n≈24,410/24,363 per leg, sd=13.62bps, α=.05 two-sided, power=.80): **0.346bps**.
A 3bps true effect would be detected with near certainty (MDE ≪ 3bps) — the null result is not
a power problem; the measured effects (0.22–1.5bps depending on cell) are genuinely too small to
survive even the lower, self-derived cost floor.

## Claimed vs recomputed
| item | claimed | recomputed | note |
|---|---|---|---|
| (1) imb_top gross, 1/5/30s | 0.08–0.26bps | 0.075–0.206bps (ticker), 0.22–0.28bps (5s) | reproduces |
| (2) imb_5bps gross, 30/120/300s, all-time+tw | +0.2 to +2.2bps | 0.22–1.25bps (paired); 2.2bps matches long-only level, not paired signal | mostly reproduces, one figure likely mislabeled |
| taker round-trip cost | 5.8bps | ≈1.9bps (median spread + correct 0% FX fee) | **not reproducible**, largest discrepancy |
| net after cost | −3.6 to −5.6bps | best cell +1.25bps gross still < 1.9bps cost → net negative in every cell | conclusion holds even at lower cost |
| lag+5min placebo | (not reported) | 0.43bps, t=3.2 (not ≈0) | new caution, not in original record |
| depth sweep 2/5/10bps | (not reported) | only top/5bps available in data; max 0.46bps | scope limited by dataset |

**Overall: rejection conclusion (closed at the mechanism level) is maintained.** The cost figure
in the original record (5.8bps) does not reconcile with what this data supports (≈1.9bps for
FX_BTC_JPY's 0% taker fee); this is a real numeric gap worth reconciling, but it does not change
the verdict because gross effects, even under the more permissive recomputed cost, do not clear
it in any control-surviving cell.

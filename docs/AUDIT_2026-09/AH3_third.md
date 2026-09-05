# Blind audit — packet AH (third auditor)

Claims: R10 (嵐の予兆), R11 (嵐の方向予測), R12 (時間帯の方向性).
Data paths checked (all present, all read): `backtest_data/storm_events_20260820/` (16 event
files, 7202 rows/file, 1s res, cols ts/bn_price/bf_price/bf_buy/bf_sell), `backtest_data/binance_BTCUSDT_1m_210d_20260820.csv.gz`
(302,403 rows, 2026-01-22→08-20, 0 gaps>60s, 0 dup timestamps — all-time control population),
`backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz` (44,657 rows, 31d, 0 gaps/dups). Also read
`config/config.yaml`, `config/products.yaml` (fees), `src/bot/radar.py` (storm-event definition
provenance only — not a forbidden research_*.py). No public fetch was needed: every path named in
the AH row was present locally; IV/large-lot data (needed for part of R10) has no path in the row
and no named public source, so that sub-figure is flagged, not fetched ad hoc.
Storm definition used (from radar.py's own documented formula, independently re-implemented):
first minute of |30m log-return| ≥ 0.8% after ≥2h with no such crossing. On the 210-day Binance
population (n=302,403 admissible minutes) this yields **539 events**, base rate 0.178%/min.
Fee/cost used for translation: `config/products.yaml` FX_BTC_JPY `taker_fee_pct=0.0`,
`config/config.yaml` `costs.slippage_pct=0.05%` → round-trip floor ≈ **10bps**.

## R10 — 嵐の予兆(価格/出来高/IV/大口), max lift 1.57 (<2.0), composite anti-correlated
Denominator: 302,403 admissible minutes, 539 storm events (Q1). Recomputed single-feature lifts
(top-decile mask, n_sel≈30,232 each): |30m abs-return|=**1.540**, volume z-score=1.150, taker
buy-ratio deviation=0.427 (anti-predictive). Max=1.540 vs claimed 1.57 (Δ1.9%, within band) →
reproduces for price/volume only.
Selection contamination (Q7): claim says 13 hypotheses were tried. I built 13 window-length
variants of the same feature families and took best-of-13 **in-sample, no train/val split**:
lift=**1.970** — far above the shuffled-label null (mean 1.19, p95 1.35, p99 1.45; p<0.01) so not
pure noise, but much closer to the 2.0 adoption bar than the reported 1.57 (Δ25%, outside band).
This shows the "1.57" figure is sensitive to search discipline: an equally-sized in-sample sweep
without a held-out split lands near the threshold, underscoring why the pre-registration split
(not reproducible by me) matters for this exact number.
Composite (Q5/Q8): claim states the composite is anti-correlated (worse than singles). Using only
the two features I have (price, volume; corr=0.14), both an AND-composite (1.775) and an additive
rank-composite (1.633) score **above** the best single feature (1.540), the opposite of "anti-
correlated." IV and 大口(large-lot) features are in none of the three data paths in the AH row and
no public source is named for them, so I cannot test the composite as originally built — this
sub-figure is data-unavailable, not merely different.
Controls: shuffled-label placebo lift ≈1.08 (expected ~1.0) — the pipeline itself is not spuriously
inflating lift. Cost: a lift ratio isn't a bps figure; translated to money it only matters via
recall × trade size, which the claim doesn't give, so no JPY figure is derivable from this data.
Verdict: 判定不能

## R11 — 嵐の方向予測(モメンタム/フロー/レンジ位置), コイントス, レンジ位置 −6.6bps/日
Denominator: 539 storm events (same population as R10). Direction-accuracy recompute: momentum-
continuation **47.12%**, order-flow (concurrent bar — I could not reconstruct a strictly pre-event
flow feature from this data, so this number is a lower-confidence proxy, not a clean re-derivation)
38.40%, range-position mean-reversion 44.71%. Binomial MDE at n=539 (α=.05, power=.8) = ±6.0pp
around 50%. Momentum's 47.1% is 2.9pp from 50%, inside the MDE → statistically indistinguishable
from a coin toss, matching the claim's "outside the definition window, coin toss" (my best proxy
for the claimed 49.3/50.7% split lands in the same regime).
Range-position daily strategy (n=210 independent days, Binance close-to-close): mean=**−7.38bps**,
se=10.2bps, **t=−0.72** vs claimed −6.6bps (Δ12%, just outside the 10% band, same sign/order of
magnitude). t=−0.72 means the claimed number itself is not distinguishable from 0 at this n —
sign-reversed control gives the mirror +7.38bps by construction (not an independent check, just a
sanity check on the code). Both figures are below the 10bps round-trip cost floor either way →
non-actionable, so the conclusion (reject) holds regardless of which of the two numbers is "true."
Regime split (Q4/Q2ii, vol tercile at event time, n≈178/tercile): low-vol 56.7%, mid 43.3%, high
41.5% — spread looks large but MDE at n=178 is ±10.5pp, so none of the three terciles is
individually significant vs 50%; can't confirm or rule out regime-dependence with this n.
Verdict: 数値差異(結論維持)

## R12 — 時間帯の方向性(時刻別/曜日別), 全てノイズフロア(1bps)未満
Denominator: full populations, both instruments, grouped by UTC hour (24 cells) and day-of-week (7
cells). Horizon matters a great deal (Q4) — I swept it since the claim doesn't state one:
- h=1min (closest to a single trade decision): max|mean| by hour = Binance **0.12bps** (max|t|=2.0,
  n/cell≈12,600), FX_BTC_JPY **0.24bps** (max|t|=1.7, n/cell≈1,860) — both under the 1bps floor,
  t-stats marginal → reproduces "under noise floor" at this horizon.
- h=30min: Binance 2.95bps (max|t|=9.8), FX_BTC_JPY 9.48bps (max|t|=9.8) — both far above 1bps.
  Permutation test (200x shuffled hour labels, controls for the 24-cell multiple-comparison search,
  Q7): null max-cell mean 0.84bps/2.10bps, p95 1.10bps/2.60bps, observed values give p=0.000 for
  both instruments — this is not a multiple-testing artifact, it is a real, sizeable seasonal
  pattern at 30-min horizon that is NOT under the stated floor.
- h=1day: 15.8bps / 48.9bps, but this bucket uses overlapping 1-day windows sampled every minute,
  so the effective independent-day count is ≈210 / ≈31, not the ~12,500/~1,800 the naive SE uses —
  the quoted t-stats at this horizon are overstated (Q6 methodological validity note).
Data-quality flag (Q6): 307/310 minutes in the FX_BTC_JPY 19:00–19:10 UTC window (bitFlyer daily
maintenance) are forward-filled flat, zero-volume bars (7.1% of all FX rows are zero-volume
overall) — these mechanically pull the hour=19 bucket toward a 0bps mean, which is a data artifact,
not evidence of "no drift" at that hour.
Simplest alternative explanation (Q8): the horizon-scaling pattern (~0 at 1min, growing to several
bps at 30min, tens of bps at 1 day) is consistent with ordinary volatility clustering / session
trend persistence rather than a stable calendar effect — and it is proportionally much larger on
the 31-day FX sample than the 210-day Binance sample of the same underlying asset, as expected if a
handful of trending days are driving it rather than a repeatable time-of-day edge.
Verdict: 数値差異(結論維持)

## Claimed vs recomputed (headline numbers)
| claim | claimed | recomputed | Δ | note |
|---|---|---|---|---|
| R10 max lift | 1.57 | 1.540 (3 feats) / 1.970 (13 feats, in-sample) | 1.9% / 25% | search-size sensitive |
| R10 composite | anti-correlated | +15–21% over best single (proxy feats) | n/a | IV/大口 untestable here |
| R11 direction acc. | ~49.3/50.7% | 47.1% (momentum, n=539) | within MDE(±6.0pp) | coin-toss holds |
| R11 range-pos daily | −6.6bps | −7.38bps (t=−0.72, n=210) | 12% | neither ≠0, both <cost |
| R12 noise floor | <1bps (all buckets) | 0.12–0.24bps @1min; 2.95–9.48bps @30min | horizon-dependent | see above |

## 前提の誤り
- premise: "13仮説, max lift 1.57" implies a stable ceiling near 1.5–1.6 | source: R10 claim text |
  what the data shows: an equally-sized (13-variant) in-sample sweep without a train/val split
  reaches 1.97, near the 2.0 bar | bias: makes the rejection look more comfortable than a
  same-size undisciplined search would produce | inherits to: any other precursor/threshold claim
  that quotes "N hypotheses tried, best = X" without confirming the number came from a genuinely
  held-out evaluation (same mechanism as research-protocol's train/val→OOS-once rule exists to
  prevent).
- premise: composite feature is anti-correlated with the individual signals | source: R10 claim
  text | what the data shows: cannot be tested — IV and 大口(large-lot) data are absent from every
  path listed in the AH row, and the two proxies I could build (price, volume) combine
  *positively*, not negatively | bias: unknown direction, but the claim's stated mechanism is
  unverifiable with the data on hand | inherits to: any claim describing "composite/ensemble of the
  precursor features" without the underlying IV/order-size series being in a checked-in path.
- premise: "noise floor 1bps" is a fixed, horizon-independent bound | source: R12 claim text
  (no horizon stated) | what the data shows: true at 1-minute horizon, false (2.95–9.48bps,
  permutation p=0.000) at 30-minute horizon on both instruments | bias: could understate a real,
  horizon-dependent seasonal pattern if anyone later trades on a >1min holding period using this
  claim as clearance | inherits to: any strategy citing R12 to justify ignoring time-of-day effects
  at a multi-minute or daily hold.
- premise (implicit, not stated in the claim but relevant to anyone reusing the FX_BTC_JPY series
  for an hour-of-day study): the FX_BTC_JPY candle file has no gaps, so it is "clean" | what the
  data shows: 19:00–19:10 UTC bars are forward-filled flat/zero-volume (bitFlyer maintenance), and
  7.1% of all FX bars are zero-volume | bias: dilutes any hour-conditional statistic toward 0 for
  hour=19 specifically | inherits to: any hour-of-day or session-based analysis using this exact
  candle file without an explicit zero-volume filter.
- premise: order-flow (taker buy/sell ratio) is available as a genuine *pre-storm* predictor |
  what the data shows: the only per-minute flow figure in the Binance file is contemporaneous with
  each bar; building a strictly-lagged flow feature from this file needs sub-minute data I do not
  have, so my order-flow number (38.4%) is not a clean re-derivation and was excluded from the R11
  verdict | inherits to: any claim about order-flow prediction sourced only from 1-minute OHLCV.

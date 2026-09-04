# Packet AH — 嵐の予兆棄却 + 嵐の方向予測棄却 + 時間帯の方向性棄却 (R10, R11, R12)

Blind re-derivation. Storm def: first 1m bar t0 where |30m log return| ≥0.8% after ≥2h with no such bar.
Script: `scratchpad/audit_AH.py` (own implementation; no sklearn/statsmodels — manual Mann-Whitney AUC + bootstrap CI, manual Newey-West).

## Files read
`data/binance_BTCUSDT_1m_full.csv` (main, longest available 1m history), `backtest_data/binance_BTCUSDT_1m.csv` (checked, only 21d — see 前提の誤り), `backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz`, `backtest_data/board_round_20260904/board_round_series_5s.csv.gz` + `board_round_coverage.json` (manifest), `config/config.yaml`, `config/products.yaml`. Grepped `docs/AUDIT_2026-09/00_packets.md` for R10/R11/R12/AH rows only; PROTOCOL.md. No other docs/ file opened.

## Denominators (Q1)
- **Storm rebuild, Binance BTCUSDT 1m**, 2026-01-22→2026-08-20, 210.0d, 0 gaps: **n=352 storms** (1.68/day).
- FX_BTC_JPY candles 31d: n=25 storms (consistency only). Board 5s→1m, 15.3d: n=31 (consistency only, noisy).
- R11: 351 storms with ≥150min lead-in for features.
- R10: 352 storms vs 7,040 matched controls (20/storm, same UTC hour, no storm within ±120min) vs 7,040 all-time random controls (20/storm, no storm within ±30min).
- R12: 302,403 1m bars (full 210d) / 129,601 (last 90d) / 10,080 non-overlapping 30m bars (full).

## R11 — storm direction
Base rate (n=352): **up 173/352=49.15%, down 179/352=50.85%** — matches claimed 49.3/50.7 closely (Δ0.15pp, within sampling noise at this n).
Predictors, pre-storm window only (no tautology — features end 30–150min before t0):
| feature | AUC | 95% CI | n |
|---|---|---|---|
| prior 30m return [t0-60,t0-30] | 0.433 | [0.374,0.494] | 351 |
| prior 2h return [t0-150,t0-30] | 0.521 | [0.460,0.581] | 351 |
| hour (in-sample up-rate, **optimistic upper bound**) | 0.610 | n/a | 351 |
| placebo (shuffled label) × prior30 | 0.506 | — | sanity check, ≈0.5 as expected |

prior30's CI just clears 0.5 (raw). Reversal rule (bet against sign(prior30)): hit-rate 53.0% vs 50% baseline — a binomial z-test on the same rule gives z≈1.12 (not significant); Bonferroni α for 13 AUC-tests run in this packet = 0.0038, and prior30's raw two-sided p is only ≈0.02–0.05, so it **does not survive multiple-comparison correction**. prior2h and hour give no usable directional signal (hour's 0.610 is in-sample/biased, not a valid forecast — true OOS value would be lower).
**Verdict: R11 holds (数値差異・結論維持).** Base rate reproduces; the one borderline feature (prior30) is a weak, uncorrected-only signal, not evidence against "unpredictable."

## R10 — minute-scale precursor
**Critical finding on window definition (see 前提の誤り):** the task-specified window `[t0-30m,t0-1m]` overlaps ~97% with the storm's own defining window `[t0-30m,t0]`, so features computed there partly measure the storm's own realized move, not a genuine precursor.
- **As literally specified** `[t0-30,t0-1]`: rvol AUC 0.826 [.812,.839], range 0.915 [.907,.923], volu 0.801 [.783,.817] vs matched (similar vs random) — huge apparent "lift", but this is **tautological look-ahead**, not a forecast.
- **True non-overlapping precursor** `[t0-60,t0-31]` (ends before the defining window starts): rvol AUC 0.671 [.650,.692] matched / 0.626 random; range 0.647/0.604; volu 0.612/0.576; ac1 0.508/0.514 (no signal). tss: matched AUC 0.373 [.346,.399] (storms follow shorter post-quiet gaps than matched-hour controls — an artifact of the ≥2h eligibility construction, not a tradable signal), random AUC 0.480 (≈null, as expected).
**Verdict: R10 数値差異(結論維持).** A real but modest elevation in pre-storm realized vol/range/volume exists (AUC 0.60–0.67, CIs clear 0.5) — consistent with generic volatility clustering (Q8), and with the claim's own "max lift 1.57 below the 2.0 actionability bar": present, weak, not tradable. The claim's phrase "no lift" is imprecise; "lift below actionability threshold" is what the data show.

## R12 — hour-of-day drift
Full 210d, 1m returns: max|NW-t|=1.93 (hour10, -0.0797bps); MDE per hour ≈0.12–0.23bps (n=12,600/hour) — **finer than the claimed 1bps noise floor**, i.e. the test had power to see even sub-1bps effects and found none significant at 95%. 30m non-overlapping bars, full: max|t|=1.91 (hour13), MDE≈2.9–7.4bps (n=420/hour). Last-90d subsample: one cell exceeds threshold — hour20 1m, mean +0.19bps, t=2.97 — but this does **not** replicate in the full-210d sample (t=1.68) nor in 30m bars (t=1.73), and ~1 hit in ~96 cells tested across this packet is within chance at α=0.05. Consistency (Q9): FX_BTC_JPY 31d max|t|=1.88; board 15d max|t|=2.31 (small n, noisy).
**Verdict: R12 再現.** All effects are at/below the noise floor; the single last-90d exceedance is an unreplicated multiple-comparisons artifact.

## Q3 money translation
FX_BTC_JPY taker_fee_pct=0.0 (`config/products.yaml`). Realized spread from `board_round_series_5s.csv.gz` `spread_bps`: median 1.78bps, mean of positive rows 1.93bps (n=249,336; 264 rows/0.1% were non-positive — data-quality issue, excluded). Using 1.93bps as round-trip cost floor: prior30-reversal EV/signal ≈ (2×0.530−1)×88.1bps(mean|ret30| at storms) ≈ 5.27bps vs 1.93bps cost — nominally net-positive, but the underlying hit-rate is not significant after correction (see R11), so this is not a usable edge. At 352 storms/210d ≈ 612/yr, even a real 1–2bps/trade edge would be economically marginal against sizing constraints not modeled here.

## 前提の誤り (assumption findings)
| premise | source in claim | what the data show | bias direction | inherits to |
|---|---|---|---|---|
| Task instruction says use `backtest_data/binance_BTCUSDT_1m.csv` as "long 1m history…≥1 year" | task brief | that file is only **21 days** (2026-07-30→08-20), 0 gaps but far short of 1 year; `data/binance_BTCUSDT_1m_full.csv` (210d, 0 gaps) is the actual longest available and was used instead | none on my numbers (I used the longer file) but any prior study using only the 21d file would have n≈35 storms, understating CI width | any earlier storm study that cites "backtest_data" as its sole source |
| R10-style "precursor window" naturally read as `[t0-30,t0-1]` | task SPECIFIC REQUIREMENTS wording | this window overlaps ~97% with the storm-defining window itself, so vol/range/volume features there are partly the storm's own realized move (tautological), producing AUC 0.80–0.92 that looks like huge lift but isn't forecastable | inflates apparent precursor lift; only the non-overlapping `[t0-60,t0-31]` window (AUC 0.61–0.67) is a genuine forward check | any packet reusing "minute-scale precursor over [t0-30,t0-1]" verbatim |
| bitFlyer FX_BTC_JPY candle file has "no gaps" (checked: gap>1min count=0) | implicit data-completeness assumption | the daily 19:00–19:10 UTC maintenance window is **forward-filled with flat, 0-volume synthetic bars** (verified 2026-08-20), not left as a true gap — biases that instrument's hour-19 return/vol stats toward zero and would hide storms starting in that window | suppresses hour-19 variance/effect estimates on FX-sourced series only (board/Binance not affected the same way) | any hour-of-day or precursor study built on `candles_FX_BTC_JPY_*` without excluding 19:00-19:10 UTC |
| `spread_bps` in board_round series is a clean cost proxy | Q3 instruction to derive cost from data | 0.1% of 5s rows (264/249,336) are non-positive/anomalous (crossed-quote or timestamp artifacts) and pull the naive mean to -12.5bps vs a median of 1.78bps | using the raw mean would badly overstate the safety margin on any cost floor calc; median/positive-mean (≈1.8-1.9bps) is the robust figure | any packet quoting a board_round-derived spread cost without filtering non-positive rows |
| R10's original "13 features" lift figure and R10/R11/R12's precise thresholds (1.57, 2.0, 49.3/50.7%, 1bps floor) | claim rows in 00_packets.md | not independently re-derivable exactly (different window/feature engineering choices are underdetermined by the one-line claim text) — my numbers are close in direction/magnitude but not a bit-for-bit reproduction | neutral; flagged as 再計算不能 only for the *exact* original cell values, not the qualitative verdicts | any packet that treats the packets.md one-liners as fully specified methodology |

## Claimed vs recomputed
| claim | claimed | recomputed | verdict |
|---|---|---|---|
| R10 | max lift 1.57 (<2.0 bar), composite anti-correlated | non-overlap AUC 0.61–0.67 (weak, real); overlap-window AUC 0.80–0.92 (tautological artifact) | 数値差異(結論維持) |
| R11 | 49.3/50.7% up/down, coin toss | 49.15/50.85%, prior30 AUC 0.433 (fails mult.-comp. correction) | 数値差異(結論維持) |
| R12 | all <1bps noise floor | max|t| 1.93 (1m), 1.91 (30m); MDE 0.12–0.23bps < claimed floor | 再現 |

No model names used. Not committed.

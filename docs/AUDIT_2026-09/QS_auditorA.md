# QS packet — blind audit (auditor A)

Files read: docs/AUDIT_2026-09/PROTOCOL.md; docs/QA/claims_for_auditors_steer.md;
backtest_data/qa_known_answer_steer_20260905/{manifest.md, costs_qs.yaml,
daily_qs_{delta,echo,foxtrot,golf}.csv.gz, min1_qs_{flat,momentum}.csv.gz,
ticker_qs_tape.csv.gz, executions_qs_tape.csv.gz}; config/products.yaml (fee constants only).
No forbidden file opened (docs/QA/answers_sealed*.json, scripts/qa/*, KNOWLEDGE.md etc. not touched).
No public-data fetch needed — packet is fully self-contained synthetic data.
Own script: audit_QS_A.py (scratchpad), independent pandas/numpy re-implementation.

## QS-1

Denominator: n=4085 weekday close[t]→open[t+1] transitions, QS_DELTA, 2011-01-03..2026-08-31 (file is
already business-days-only). Recomputed mean=4.2998bps/day, t=14.21 vs claimed +4.3bps/t=14.2 — matches.
Controls: sign-reversed gives t=-14.21 (mirrors as expected); vol-tercile means 3.87/4.23/4.76bps and
weekday means 2.9-5.0bps — level effect, not concentrated in one regime. MDE at n=4085 (95%, two-sided)
≈0.59bps, far below the observed 4.30bps, so this is not a "cannot detect" case in either direction.
Mechanism test (the actual claim under Q of this packet): recomputed the same premium replacing `close`
with `close_vwap5` → mean=4.3072bps, t=13.97 — essentially IDENTICAL to the raw-close number (+0.2%,
t within 2%). The claimed mechanism ("stale close vs 5-min VWAP; disappears when close_vwap5 is used")
is directly falsified: it does not disappear, or even move meaningfully.
| metric | claimed | recomputed |
|---|---|---|
| mean (close) | 4.3 bps | 4.2998 bps |
| t (close) | 14.2 | 14.21 |
| mean (close_vwap5) | ~0 (implied) | 4.3072 bps |
Headline number reproduces, but the claim's actual thesis (premium is a spurious stale-close artifact) is
reversed by data: the effect is unchanged when the alleged artifact source is removed.
Verdict: 結論変更
Mechanism: 棄却

## QS-2

Denominator: n=4085 transitions, QS_ECHO. Recomputed mean=-0.0947bps/day, t=-0.32 vs claimed -0.1bps
(insignificant) — matches within 5.3% relative, both non-significant. MDE(95%)≈0.57bps > |observed
0.09bps|, consistent with a true null at this n (cannot rule out a small nonzero effect below MDE, but
claim only asserts "~zero/non-significant", which holds).
Mechanism (a linked ETF's market-maker arbitrage permanently pins the premium to zero): the packet
contains only this single instrument's daily OHLC — no ETF, no second instrument, no cross-market data
to test any arbitrage/cointegration relationship. The causal claim cannot be examined from this data at all.
Verdict: 再現
Mechanism: 未検証

## QS-3

Denominator: n=4085 transitions, QS_GOLF. Recomputed mean=3.5979bps/day, t=12.44 vs claimed +7.2bps/day —
relative difference 50%, outside the 10% band, even though sign/significance both hold (t=12.44, clearly
>0). MDE(95%)≈0.57bps, so both 3.6 and 7.2 would be easily detectable at this n; the mismatch is not a
power problem.
Identity re-derivation (2×var(overnight_return)÷intraday_spread, "as designed"): intraday spread proxy
(mean of (high-low)/open, in bps) = 132.19bps/day; var(overnight_return) = 341.62 bps². In bps-consistent
units, 2×341.62/132.19 = 5.17bps — matches neither the claimed 7.2bps nor the measured 3.60bps (28% and
44% off respectively). In the literal fractional-variance convention the result is ≈5×10⁻⁸, off by ~8
orders of magnitude. No unit convention makes the identity reproduce either number; it does not hold.
| metric | claimed | recomputed |
|---|---|---|
| mean bps/day | 7.2 | 3.60 |
| identity value | = mean (implied) | 5.17 (bps-consistent) / ~0 (literal) |
Verdict: 数値差異(結論維持)
Mechanism: 棄却

## QS-4

Denominator: n=86399 1-minute return pairs per series (60 days), QS_momentum vs QS_flat control.
Recomputed lag-1 autocorr: momentum=0.0526 (t=15.48) vs claimed +0.053 — matches (<1% off). Control flat
=0.0051 (t=1.51, not significant), consistent with the claim's framing that flat should show ~nothing.
Both series carry exactly 600 zero-return bars (0.69% of bars each), all falling in hour=19 UTC,
minute 0-9 — i.e. the declared bitFlyer maintenance window 19:00-19:10 UTC, confirming that window exists
in both series identically.
Mechanism test: excluding those maintenance bars leaves momentum's autocorrelation essentially unchanged
(0.0526→0.0526, t 15.48→15.41; n drops 86399→85799). If the flat, zero-return maintenance bars were
producing the autocorrelation, removing them should measurably shrink it toward flat's ~0.005 level;
instead it is untouched. Flat carries the identical maintenance-bar pattern yet shows no comparable
autocorrelation either with or without those bars (0.0051→0.0052). The claimed mechanism is falsified:
the momentum series has genuine serial correlation unrelated to maintenance bars.
Verdict: 結論変更
Mechanism: 棄却

## QS-5

Denominator: n=51966 quote snapshots, n=32274 executions (3-day synthetic tape), sides ~50/50
(16173 sell / 16101 buy). Measured quoted spread: mean=1.996bps, median=2.000bps → half-spread≈0.998bps,
matching the claimed "spread 2.0bps ÷2". Matched each execution to the prevailing quote (merge_asof,
backward) and computed side-signed slippage vs mid: mean=1.799bps. This already embeds the half-spread
paid for crossing the book, so the incremental one-way slippage beyond top-of-book ≈1.799-0.998≈0.80bps,
matching the claimed "片道スリッページ0.8bps" almost exactly. One-way total ≈1.799bps; round-trip
≈3.598bps vs claimed 3.6bps (<0.1% off). taker_fee_bps=0.0 per costs_qs.yaml, consistent with
config/products.yaml FX_BTC_JPY `taker_fee_pct: 0.0` (checked directly; no maker_fee/rebate field exists
anywhere in that file or elsewhere under src/ — grepped for "rebate", zero hits).
Data-quality note (Q6): 52/51966 (0.10%) quote rows show best_bid > best_ask (crossed); negligible effect
on the mean but noted per protocol.
| metric | claimed | recomputed |
|---|---|---|
| half-spread | 1.0 bps | 0.998 bps |
| one-way slippage | 0.8 bps | ~0.80 bps (residual after half-spread) |
| round-trip floor | 3.6 bps | 3.598 bps |
Mechanism (fee=0 because of a maker-rebate structure that taker economically funds, so "true cost" should
be marked up further): no rebate column, field, or constant exists anywhere in this packet, in
config/products.yaml, or in src/ for this product — the 0bps figure is simply the declared taker fee.
The "true cost is higher" add-on cannot be measured or falsified from any available data.
Verdict: 再現
Mechanism: 未検証

## QS-6

Denominator: n=4085 transitions, QS_FOXTROT. Recomputed mean=2.9057bps/day, t=9.97 vs claimed +2.9bps/day,
t=9.9 — matches (<0.5% off on both). Vol-tercile means 2.70/2.99/3.02bps and weekday means 2.3-3.9bps show
no strong regime concentration. No mechanism/identity attached to this claim (per instructions, no
Mechanism line required). Note: QS_FOXTROT and QS_ECHO open at the identical price (100.0) on day 1 but
diverge immediately after (only 0.02% of rows match, max abs diff ~1228) — two independently generated
series sharing a start price, not a data-integrity problem.
Verdict: 再現

## 前提の誤り

- premise: "close→open premium is a stale-close artifact that vanishes once close is replaced by
  close_vwap5" | source: claim QS-1 | data shows: mean/t change by <2% when close_vwap5 replaces close
  (4.2998→4.3072bps, t 14.21→13.97) — it does not vanish | bias: accepting this premise would cause a real
  (in-data) overnight effect to be wrongly written off as non-actionable noise | inherited by: any other
  claim in this repo that explains away a close→open or EOD-based signal by invoking "stale/lagged close
  vs a cleaner VWAP proxy" without re-testing it.
- premise: "premium (bps/day) = 2×var(overnight_return)÷intraday_spread by construction" | source: claim
  QS-3 | data shows: neither bps-consistent (5.17bps) nor literal-fraction (~5e-8) evaluation of the
  identity matches the measured 3.60bps or the claimed 7.2bps | bias: overstates confidence that a
  premium's size is mechanically fixed by variance/spread, which would mask an unmeasured true driver |
  inherited by: any claim that justifies a headline number via a "width×levels≈vol"-style identity instead
  of re-deriving it (the exact pattern flagged in PROTOCOL.md's AR-84 note).
- premise: "QS_GOLF premium = 7.2bps/day" | source: claim QS-3 | data shows 3.60bps/day, 50% lower |
  direction of bias: overstates the edge by roughly 2x | inherited by: any profitability/cost comparison
  that cites the 7.2bps figure downstream.
- premise: "qs_momentum's lag-1 autocorrelation is produced by synthetic maintenance-window flat bars" |
  source: claim QS-4 | data shows: removing those bars leaves autocorrelation unchanged (0.0526→0.0526)
  while qs_flat, carrying the identical maintenance-bar pattern, shows no comparable autocorrelation either
  way (~0.005) | bias: would cause a real serial-correlation property of the momentum series to be
  discarded as a data artifact | inherited by: any claim dismissing 1-minute autocorrelation or momentum
  findings by citing "maintenance-bar contamination" without the same exclude/include comparison.
- premise: "taker fee=0bps exists because of a maker-rebate cross-subsidy, so true cost is marked up
  further" | source: claim QS-5 | data/config show: no rebate field/column anywhere in the tape files,
  costs_qs.yaml, config/products.yaml, or src/ — 0bps is simply FX_BTC_JPY's declared taker_fee_pct |
  bias: an unverifiable upward adjustment to a cost floor that otherwise reproduces cleanly (3.598 vs
  3.6bps) | inherited by: any claim that adds an undocumented "rebate markup" on top of a measured
  spread+slippage cost floor.
- premise: "a linked ETF's market-maker arbitrage keeps QS_ECHO's premium pinned at zero for as long as
  that structure exists" | source: claim QS-2 | data shows: only a single instrument's daily series is
  present in this packet, no ETF/cross-instrument data to test any arbitrage relationship | bias: presents
  an untestable invariance law as settled fact | inherited by: any claim relying on a similarly unverifiable
  "structural force keeps X at zero permanently" argument from this same packet.

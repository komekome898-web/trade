# Packet U — Wick-reversal & anchor-deviation contrarian rejections (R5, R6, R7)

Blind re-derivation, own implementation, per `docs/AUDIT_2026-09/PROTOCOL.md`. Script:
`/tmp/claude-0/-home-user-trade/fa7bf0d4-a5c4-55b7-991b-874b590e00a3/scratchpad/audit_U.py`

## Method
- **Data**: `backtest_data/binance_BTCUSDT_1m_210d_20260820.csv.gz` (211 calendar days,
  2026-01-22→2026-08-20, primary 210-day walk-forward series); `backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz`
  (real bitFlyer FX_BTC_JPY, 32 days, independent-instrument consistency check); all 16
  `paper_logs/tape/ticker_20260820..20260904.csv.gz` (1,588,662 quotes, realized spread); `config/config.yaml`,
  `config/products.yaml` (fee constants).
- **Costs**: engine default = `taker_fee_pct 0.15% + slippage_pct 0.05%` per side ×2 sides = **40.0 bps round trip**
  (`config/config.yaml:costs`). Realized: FX_BTC_JPY `taker_fee_pct: 0.0` (`config/products.yaml`), mean quoted
  spread over 1.59M ticks = **2.028 bps round trip** (fee+spread). Both are used for every net figure below.
- **Wick grid (R5)**: 15-min bars; wick/body ratio∈{2,3} × bar range∈{10,20}bps × hold∈{5,15,30}min = 12 cells.
  Long lower-wick bar → long (fade up); long upper-wick bar → short (fade down).
- **Anchor grid (R7, and R6 by mechanism-mapping — see 前提の誤り)**: 60-min rolling VWAP/EMA on 1-min bars;
  deviation∈{1,2,3}σ (σ = 60-min rolling stdev of 1-min returns × price) × hold∈{5,15,30}min = 18 cells.
  Price ≥+kσ above anchor → short; ≤−kσ below → long.
- **Walk-forward**: 9 non-overlapping 21-day-train→21-day-test folds across the 210-day Binance series. Best cell
  selected on TRAIN under engine-cost net (matching the practice the claims describe), then scored on the
  corresponding TEST block under both cost regimes. All rates use **day-clustered** SE/CI (cluster = trading day).

## Q1–Q10 findings
1. **Denominator**: wick pooled OOS n=3,179 trades / 181 trading-days (9 folds); anchor pooled OOS n=109,630
   qualifying minutes / 189 trading-days — the anchor "n" is 1-min-granularity signal count, **not** an independent
   event count (60-min window → heavy within-episode autocorrelation); day (189) is the correct denominator, which
   is what every CI/t here uses.
2. **Controls**:
   - (i) shuffled-return placebo (1-min log-returns permuted → same-vol synthetic path, kills serial
     reversion): best-of-grid mean ≈1.15–1.25bps, p95≈2.5–3.1bps (fold-0 window) — essentially matches the size
     of the real observed best-train-cell gross edge (wick 0.73bps, anchor 2.93bps).
   - (ii) state-conditional control (same high-range/high-deviation bars, direction randomized instead of the
     wick/deviation sign): mean 0.81bps (wick, sd 1.68, 15 draws) and 0.05bps (anchor, sd 0.31) — being in the
     "interesting" state carries ~no directional edge by itself.
   - (iii) sign-reversed (momentum instead of contrarian): exact mirror by construction (+0.73/−0.73 wick,
     +2.93/−2.93 anchor) — both magnitudes sit inside the noise band from (i)/(vii), so neither polarity is
     distinguishable from chance.
   Controls behave exactly as a null-effect claim implies.
3. **Translation**: pooled OOS gross wick −0.55bps/trade (day-clustered CI −1.32,+0.22, t=−1.40); anchor
   +0.214bps/minute-signal (CI −0.45,+0.87, t=0.64). Net of realized cost (2.03bps): wick ≈−2.6bps, anchor
   ≈−1.8bps (fold-average). Net of engine default (40bps): wick ≈−40.6bps, anchor ≈−39.8bps. At a hypothetical
   1 BTC/trade, 1 trade/day, 40bps costs ≈ ¥4,400–5,600/day loss at current BTC/JPY levels (~¥11M); at realized
   cost the loss is smaller (~¥220–290/day) but still negative on average.
4. **Relative vs absolute / regime**: best cell changes every single fold (0/9 persistence for both families,
   see table) — this by itself is strong non-stationarity/regime-dependence; a full vol-tercile×fold breakdown
   was out of budget, illustrative fold-0 60-min-σ terciles: ≤36 / ≤51 / >51 JPY.
5. **Definition side-effects**: anchor "n" inflation from 1-min sampling of a 60-min indicator (see Q1) is the
   main one; wick's 15-min bar definition selects ~2–6% of bars, no obvious selection-on-outcome found.
6. **Data validity**: FX 31-day series has zero gaps >2min (pre-filled). Bars inside bitFlyer's 19:00–19:10 UTC
   maintenance window show **lower** average range (2.13bps, n=310) than the full-sample average (4.16bps) — no
   maintenance-glitch inflation of the wick signal.
7. **Selection contamination**: permutation null (circular-shift Binance close, 20 draws, fold-0 train window),
   max-of-grid: wick 12 cells → mean 3.83bps, p90 7.51, p95 10.24; anchor 18 cells → mean 7.80bps, p90 8.89,
   p95 8.94. **The observed gross "best cell" edges (0.73–2.93bps) sit at or below the median of pure-noise
   best-of-grid draws** — i.e. a 12–18-cell search on pure noise routinely manufactures a bigger apparent edge
   than what was actually found in the data.
8. **Alternative explanation**: control (ii) rules out "just trading during high-vol/high-deviation bars" as the
   source; anchor deviation is already vol-normalized (σ-scaled), so volatility clustering is controlled for
   by construction and still yields ≈0.
9. **Consistency (2nd instrument, FX_BTC_JPY 31d, same grids)**: wick train(21d) gross +2.12bps (n=188,
   nd=20) → test(11d) gross **−1.30bps** (n=146, sign flip). Anchor train(21d) gross +0.21bps (n=10,236,
   nd=21) → test(10d) gross **−3.07bps** (n=5,320, sign flip). Same qualitative signature as Binance
   (weak/marginal in-sample, negative fresh-data) on an independent series.
10. **Falsification / MDE**: wick per-fold test SE≈1.12bps over ~20 days → MDE≈**3.15bps** (α=.05, power=.80);
    anchor SE≈0.90bps over 21 days → MDE≈**2.52bps**. A real edge would need to clear MDE + realized cost
    (≈4.5–5.3bps gross, consistently) to be both detectable and barely profitable net of realistic costs; no
    cell in any fold reached that. Falsification: "wick/anchor OOS net bps ≤ 0 in ≥7/9 folds" — observed 9/9
    and 8/9 respectively net-negative at realized cost — **claim is falsifiable and was not falsified**.

## Claimed vs recomputed

| claim | claimed | recomputed (this audit) | verdict |
|---|---|---|---|
| R5 wick 15m | 21d train passes, fresh data fails (overfit) | 0/9 folds persist; OOS gross −0.55bps (CI −1.32,+0.22); selection-null p50 3.8bps > observed edge | 再現 |
| R7 anchor v1/v2 | raw fade < 6.3bps RT cost | OOS gross +0.21bps (CI −0.45,+0.87), ≪ 6.3bps and ≪ even realized 2.03bps cost; selection-null p50 7.8bps > observed | 再現 |
| R6 range/execution-polarity | all polarities negative, −3.30/−9.12bps | mapped onto anchor grid (see below): fold test-net@realized range −1.15…−3.24bps (mean −1.81) — same sign, same order of magnitude at the low end of claimed range; exact figures not independently re-derived | 数値差異(結論維持) |

Justification: all three rejections describe the same signature — "small/marginal in 21-day training,
negative out of sample, best configuration keeps changing" — and every angle tested here reproduces exactly
that: 0/9 (wick) and 0/9 (anchor) train-cell persistence, OOS point estimates statistically indistinguishable
from zero and economically negative net of any realistic cost, and a selection-contamination null that alone
explains the entire size of the "effect" ever observed in training. R6 could not be reproduced cell-for-cell
because the packet's declared grid for this audit covers only wick+anchor families, not R6's original
range/band + storm-stop-loss + execution-polarity construction — but the directional and rough-magnitude
match on the closest re-derivable proxy (anchor-deviation fade) supports the same conclusion.

## 前提の誤り (assumption findings)
- **premise**: "21-day training window passes" implies a profitable (or better-than-noise) net result under
  the cost regime used at judging time. | **source**: claim signature text. | **what the data shows**: even on
  TRAIN, the engine-cost net is always negative (−35.8…−39.8bps); only the *gross* edge (0.2–4.2bps) was ever
  positive, and it is not distinguishable from the selection-contamination null (median 3.8–7.8bps for a
  12–18-cell search). | **direction of bias**: none on the final conclusion (rejection still holds) but it
  clarifies that "passes" must have meant gross/statistical, not net-of-engine-cost, or used a materially wider
  grid than the one specified for this audit. | **inherits**: any claim citing this same "trains then collapses"
  signature for a similarly small (≤20-cell) mean-reversion grid.
- **premise**: engine default cost (40bps RT: 0.15% fee + 0.05% slippage per side) is the relevant trading cost
  for FX_BTC_JPY. | **source**: `config/config.yaml:costs` (engine default, used implicitly by any backtest that
  doesn't override it). | **what the data shows**: `config/products.yaml` sets FX_BTC_JPY `taker_fee_pct: 0.0`;
  realized quoted spread over 1.59M ticks is **2.03bps round trip** — 20× smaller than engine default.
  | **direction of bias**: makes the strategies look *worse* than a realistically-costed version would, but even
  at the much smaller 2.03bps realized cost, both families are still net-negative or ~breakeven-noise on OOS
  (wick −2.6bps, anchor −1.8bps average) — so the bias does not change the rejection verdict, only the
  claimed size of the loss. | **inherits**: every rejection on FX_BTC_JPY that cites the 40bps engine-default
  cost floor as the reason a positive gross edge doesn't survive — the correct floor to cite is ≈2.0–2.6bps,
  and these strategies still fail it.
- **premise (R6 only)**: "range-bound contrarian" and "anchor-deviation contrarian" are the same re-derivable
  mechanism. | **source**: this audit's packet-level grid declaration (wick + anchor only, no range/band grid
  specified). | **what the data shows**: R6's own label references execution-polarity reversal and a storm
  stop-loss, mechanics not present in the anchor grid used here. | **direction of bias**: unknown/neutral —
  the mapping is a reasonable proxy (both fade "price far from a reference level") but is not a byte-for-byte
  reproduction. | **inherits**: only R6 in this packet; flagged so a future audit re-derives R6 with its own
  declared range/band + stop-loss + polarity grid rather than reusing this one.
- No other premise issues found (checked: tick-size/contract-multiplier — not applicable, cash product;
  populations/denominators — corrected in Q1/Q5 above; time-zone/lag — timestamps are UTC throughout, no lag
  found; data-quality — checked in Q6, none found beyond what's listed).

## Files read
`docs/AUDIT_2026-09/PROTOCOL.md`; `docs/AUDIT_2026-09/00_packets.md` (grep on R5/R6/R7 only, section 1.3);
`config/config.yaml`; `config/products.yaml`; `backtest_data/binance_BTCUSDT_1m_210d_20260820.csv.gz`;
`backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz`; `paper_logs/tape/ticker_20260820..20260904.csv.gz` (16
files); `backtest_data/candles_FX_BTC_JPY_30d_20260820.csv` (inspected via `head`/`wc` only, not used in the
final analysis — superseded by the 31d file for the consistency check).

No forbidden files were opened. Not committed.

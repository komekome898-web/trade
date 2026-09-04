# Blind audit: Packet I (R22/PR5, Matilda M2) + Packet J (R23/PR6, Matilda M3 TaroCamp)

Compliance: no forbidden files opened (no research_*.py/judge_*.py/build_*.py/paper_*.py/run_board_round.py/
tp_operating_curve.py, no KNOWLEDGE*.md, no PREREG/RESEARCH_REPORT/SURVEY body text, no git history, no
*_RUN.txt/*JUDGMENT*.txt). Files read: PROTOCOL.md; 00_packets.md (grep on R22/PR5/R23/PR6 + section headers
only); config/products.yaml; backtest_data/venue_survey_20260827/FINAL.txt (head, spread stats only) + dir
listing; backtest_data/board_round_20260904/board_round_coverage.json + board_round_series_5s.csv.gz;
paper_logs/tape/ticker_2026{0820..0904}.csv.gz + executions_*.csv.gz (16 days); binance_BTCUSDT_1m_210d_20260820.csv.gz.
Script: `scratchpad/audit_I_J.py`. Tool calls used: ~23/50.

## Reading of the packet definitions (declared, since source scripts are off-limits)
- **I / M2 8 cells** = N∈{1,4} grid levels per side × ladder∈{5s,30s} requote cadence × gate∈{off,on
  (stand down when spread > 1.5×day-median)}. Level k offset = k×(half-spread at requote time), single
  reference mid M at requote time used for both the quote price and the eventual mark. Queue-ahead for level
  k approximated as k×displayed best-size (no per-tick L2 in the data — declared limitation). Fill rule: a
  level fills its full 0.001 BTC (`min_size`, FX_BTC_JPY) only once opposite-side executions inside the
  window **print through** queue+own size. Inventory cap = N units/side; breach forces a taker flatten
  (spread/2 + 1bps slippage). Unfilled quotes are cancelled at the next requote (no persistence).
- **J / M3 4 cells** = {range_fade, breakout} × lookback∈{20,60} 1m bars on Binance BTCUSDT. Range fade: fades
  toward mid of the trailing Donchian range when inside it and >0.3×half-width from center; breakout: follows
  a close beyond the trailing Donchian high/low. Both hold 1 bar forward. Both modes charged the same round
  cost (crossing full measured spread + 2×1bps slippage) since no maker-queue model exists for 1m bars.

## Data / costs
Measured spread: median `spread_bps` from `board_round_series_5s.csv.gz`, 2026-08-20→09-04, n=247,326 valid
5s bins (excl. 19:00–19:15 UTC, excl. crossed rows) = **1.772 bps**. Fee: FX_BTC_JPY `taker_fee_pct=0.0`
(config/products.yaml). Slippage: 1 bps/side (instructed). J round-trip cost = 1.772 + 2×1 = **3.772 bps**.
Binance file spans 2026-01-22→08-20 (211 distinct days) and does **not overlap** the tape window used for I
and for the spread constant — see 前提の誤り.

## Packet I — Matilda M2 (R22/PR5)

| | claimed | recomputed |
|---|---|---|
| cells | 8 (N{1,4}×ladder2×gate2) | 8, same factorial |
| daily values (n) | 56 | **128** (8 cells × 16 available days) |
| sign | 56/56 negative | **128/128 negative** |
| range (bps/day) | −516 〜 −7,141 | **−942 〜 −11,544** |
| cell means (bps/day) | n/a | −1,704 (N1,L30,gate-on) to −4,721 (N4,L5,gate-off) |

Controls: shuffled trade-side placebo (breaks any genuine mean-reversion information, 8 cells × 8 days) is
**also 100% negative**, mean −3,441 bps/day — statistically indistinguishable in sign/scale from the live
simulation. Sign-reversal is not meaningful here (grid quotes both sides symmetrically by construction).
Regime (realized-vol terciles from board data): mean pnl −2,809 / −3,019 / −3,927 bps/day (low/mid/high) —
losses scale with volatility, consistent with the inventory-cap forced-taker mechanism, not with a
vol-dependent edge. Validity filter (maint. window + crossed-row exclusion) changes the representative
cell's mean by <0.2% (−1,836 vs −1,838 bps/day) — exclusions are not doing any work here.
MDE (n=16/cell, t≈2): 202–1,106 bps/day depending on cell — the observed means (1,700–4,700 bps/day) are
3–10× the MDE, so this is a well-powered rejection, not an underpowered null.

**Verdict: 数値差異(結論維持).** Direction (100% negative) and order of magnitude reproduce; the placebo
result shows the effect is structural (fee-free maker legs cannot outrun the forced-taker cap flattening
under real trade-print arrival), not a market-timing failure — which if anything strengthens the rejection.

## Packet J — Matilda M3 TaroCamp (R23/PR6)

| lookback | mode | n (bars) | n_days | gross bps/unit | net bps/unit | t(gross) | breakeven multiple |
|---|---|---|---|---|---|---|---|
| 20 | range_fade | 179,493 | 211 | **+0.021** | −3.75 | 1.38 | **179×** |
| 20 | breakout | 42,069 | 211 | −0.031 | −3.80 | −0.83 | undefined (wrong sign) |
| 60 | range_fade | 195,139 | 211 | −0.016 | −3.79 | −1.06 | undefined (wrong sign) |
| 60 | breakout | 20,904 | 211 | −0.136 | −3.91 | −2.20 | undefined (wrong sign) |

Claimed: 0/4, net −0.40〜−1.36 bps/unit, breakeven 1.13〜1.48×. Recomputed: **0/4 net-profitable** (matches),
but net magnitude is ~3× larger in loss (−3.75〜−3.91 vs −0.40〜−1.36), and only 1 of 4 cells even has the
right-signed gross edge — its breakeven multiple is 179×, not 1.1–1.5×. The other three have gross edges of
the wrong sign, for which no finite "multiple to break even" exists at all.

Controls: sign-reversed gross edges are exact mirror images (mechanical, as expected for a linear P&L in a
fixed-direction bet — not informative on its own). Return-shuffled placebo gives gross edges of −0.005 to
−0.047 bps, the same order of magnitude as the live gross edges (+0.021 to −0.136 bps) — the "live" edges are
not distinguishable from noise. Selection-contamination permutation (200 draws, "best of 4 cells" under
return-shuffling): null best-cell mean = 0.0285 bps (sd 0.0265); observed best (0.021 bps) sits inside this
null distribution, **p(null ≥ observed) = 0.52** — a 4-cell search over pure noise would produce an edge this
size or larger half the time. MDE (day-clustered, n_days=211): 0.03–0.12 bps/unit — an order of magnitude
below the −3.8 bps net losses, so the net-negative finding is well powered; but it is also below the +0.021
bps "surviving" gross edge, meaning that one number is not distinguishable from zero either way.

**Verdict: 数値差異(結論維持)** for the 0/4 rejection; **the "史上最接近"/1.13–1.48× near-miss framing does
not reproduce** — recomputed cells are either wrong-signed or need a 179× improvement, not 1.1–1.5×.

## 前提の誤り (assumption findings)

1. premise: 56 daily values (I) | source: R22 claim text | data shows: 16 raw days exist in
   `paper_logs/tape`, giving 128 cell-days for an 8-cell grid, not 56 | bias: unclear without knowing which 7
   days were excluded in the original; if exclusions were selective this could inflate or deflate the
   reported range | inherits: any claim quoting "56" as if it were the full available sample.
2. premise: M3's near-miss framing (breakeven 1.13–1.48×, "史上最接近") | source: R23/PR6 | data shows: 3 of 4
   cells have gross edges of the wrong sign (no finite breakeven multiple), the 4th needs 179× | bias:
   original claim materially overstates closeness-to-viability | inherits: any downstream claim citing M3 as
   evidence that "range/breakout is nearly worth pursuing" or citing 1.13–1.48× as a target improvement bar.
3. premise: J's cost basis and signal come from the same instrument/period | source: implied by both being
   reported as one PREREG | data shows: Binance signal window (2026-01-22→08-20, 211 days) does not overlap
   the FX_BTC_JPY tape window (2026-08-20→09-04) used for the spread/slippage constant | bias: unknown sign —
   cross-period/cross-venue cost transplant is a genuine methodological seam, not verified consistent |
   inherits: any claim mixing a Binance-bar signal with a bitFlyer-tape cost floor.
4. premise: grid "N" and "gate"/"ladder" definitions | source: packet I row text only (no formula) | data
   shows: multiple plausible readings exist (tick-count vs level-count for N; several gate criteria); this
   audit declared one reading | bias: unverifiable which reading the original used — direction of bias
   unknown | inherits: any claim comparing per-cell (not aggregate) numbers against R22 cell-by-cell.
5. premise: FX_BTC_JPY funding/carry (`swap_daily_pct=0.06%`, config/products.yaml) | source: not mentioned in
   R22 | data shows: grid inventory held past 05/13/21 UTC funding marks would add carry cost, not modeled
   here | bias: recomputed losses in Packet I are if anything **understated** (real losses would be ≥ shown)
   | inherits: any P&L claim for inventory-holding BTC-CFD strategies that ignores funding.

## Falsification
- I: "If bitFlyer FX_BTC_JPY inventory-grid MM (any of the 8 declared cells) produced non-negative daily P&L
  on 2026-08-20→09-04 tape data net of 0% fee + measured spread + 1bps taker slippage, R22's rejection would
  be falsified." Not falsified — 128/128 days negative, effect ≫ MDE.
- J: "If either mode/lookback cell produced a day-clustered t≥2 **positive** net edge net of 3.77bps round
  cost on the Binance 1m sample, or the best-of-4 gross edge sat outside the 95th percentile of a
  return-shuffled null, R23's rejection would be falsified." Not falsified — best net is −3.75bps and the
  best gross edge is p=0.52 under the permutation null (indistinguishable from a 4-way data-mined artifact).

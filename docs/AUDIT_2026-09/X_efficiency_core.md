# Packet X — 効率性コア法則(消えた遅れ・秒遅れ・ベーシス平均回帰)

Claim ids: L2, L3, L4, R8. Blind re-derivation per `PROTOCOL.md`; no docs opened besides PROTOCOL.md and the
grepped rows of `00_packets.md` (L2/L3/L4/R8, packet-X row). Script:
`/tmp/claude-0/-home-user-trade/fa7bf0d4-a5c4-55b7-991b-874b590e00a3/scratchpad/audit_X.py`.

## Verdict table

| Claim | Claimed | Recomputed | Verdict |
|---|---|---|---|
| L2 | thin XRP_JPY(bitFlyer) lag1 +0.176, thick FX_BTC_JPY lag1 +0.019, lag0 +0.878 | +0.1756, +0.0193, +0.8777 (n=30,185–30,239 1-min returns, 2026-07-30→08-20) | **再現** |
| L3 | 1s lag1 +0.11〜+0.25, absorbed in 1–2s | untestable: no Binance sub-minute data anywhere in repo | **再計算不能 → 未検証** |
| L4 | predictable leg = untradeable spot; CFD drifts, doesn't correct | spot next-return slope on basis dev = +0.305 (t=+43.97); CFD slope = **−0.056 (t=−7.59)**, not ≈0 | **数値差異(結論維持)** — spot dominates 5.5× but CFD is not pure drift |
| R8 | basis reversion real, half-life 9.1min, only tradeable leg is untradeable spot | half-life 9.07min; k-grid P&L net of derived costs: **−30 to −34bps** at every k | **再現** |

## L2 — 消えた遅れ

**Q1 denominator**: n≈30,185 (XRP thin) / 30,238 (BTC thick) 1-minute log-return pairs, 2026-07-30 to 2026-08-20 (21
days, the full overlap of Binance+bitFlyer 1m candles). Lags −5..+5 computed for all four pairs (BTC: Binance→
FX_BTC_JPY, Binance→BTC_JPY spot; XRP: Binance→bitbank, Binance→bitFlyer). Headline numbers reproduce almost
exactly: thin +0.1756 vs claimed +0.176, thick +0.0193 vs +0.019, lag0 +0.8777 vs +0.878.

**Q2 controls**: label-shuffle placebo (n=200): mean≈0.0007±0.006, real lag1 falls at p=0.010 (thick) / p=0.005
(thin) — genuine signal, not noise. Sign-reversed leader flips the sign as expected (mechanical check, not
independent evidence).

**Q3 translation**: predictable amplitude = corr × follower 1-min return sd. Thick (FX_BTC_JPY): 0.0193 × 4.70bps =
**0.09bps**, against a CFD one-way spread of 2.30bps (mean, from `paper_logs/tape/ticker_20260820.csv.gz`, taker
fee 0% per `config/products.yaml`) — 25× under the spread alone. Thin (bitFlyer XRP_JPY): 0.1756 × 5.71bps =
**1.00bps**, against spot taker_fee_pct 0.15% (15bps one-way, `config/products.yaml`) — 15× under cost. Neither
lag is economically capturable even where statistically real.

**Q4 regime**: leader-vol terciles show **opposite** slopes: thick-market lag1 falls with vol (0.043→0.013
low→high), thin-market lag1 rises with vol (0.099→0.195). The thin/thick gap is itself vol-dependent, largest at
high vol — not a fixed constant as the point-estimate implies.

**Q5/Q6**: no event-definition exclusions (every 1-min bar used). Excluding bitFlyer maintenance (19:00–19:10 UTC)
changes lag1 by <0.001 in both series — not a data-quality artifact.

**Q7 alignment sensitivity (±1min)**: shifting the follower series by ±1 minute **relocates the correlation peak**
(thick: shift −1min → lag1 −0.028 vs +0.878 at lag0 unshifted; shift +1min → old lag0 becomes new lag1). The
"lag1" finding is a label on wherever candle-close alignment puts the peak, not evidence of a true ~60s causal
delay; it is bounded only by candle resolution.

**Q8 alternative explanation**: contemporaneous corr (+0.88 thick, +0.39–0.62 thin) already explains almost all
comovement; lag1 is what's left after near-simultaneous candle-close timing — consistent with a timestamp
artifact, not a distinct causal delay.

**Q9 consistency**: second thin instrument (Binance→bitbank XRP_JPY) gives lag1 **+0.267**, same order as
bitFlyer XRP_JPY (+0.176) but 1.5× the magnitude — direction (thin>thick) reproduces across venues; point value
does not.

**Q10 MDE/falsification**: at n≈30,200, MDE(r, α=.05)≈0.011 — the thick-market value (0.019) is only ~1.7×
MDE, close to the detection floor; the thin-market values (0.176–0.267) are far above it. Falsification: if a
repeat on a fresh 21-day window gave |corr|<0.011 at lag1 for both series, or the thin/thick ordering reversed,
the "disappeared lead-lag scales with liquidity" reading would be falsified. Not falsified here.

## L3 — 秒単位ラグ

No file under `backtest_data/`, `data/`, or `paper_logs/` contains Binance data at sub-minute resolution — only
1-minute OHLCV. The claimed cross-exchange 1-second lag1 (+0.11–0.25) needs a Binance leader series at ≤1s
resolution that does not exist in this repo. **Untestable — downgraded to 未検証** (Q10: no instrument exists to
detect it with, so the claim can neither be reproduced nor falsified here).

Partial proxy (bitFlyer-only, not a lead-lag test): 1s mid-quote autocorrelation from
`paper_logs/tape/ticker_20260820.csv.gz` (89,081 ticks, mean spread 2.30bps) gives **positive** lag1–lag4
autocorrelation (+0.02 to +0.04) — not the negative pattern typical of pure bid-ask bounce, and not comparable to
the claimed cross-exchange figure. Neither confirms nor refutes L3; a cross-exchange 1s capture is required.

## L4 / R8 — ベーシス平均回帰

**Q1 denominator**: 30,252 aligned 1-min bars of FX_BTC_JPY (CFD) and BTC_JPY (bitFlyer spot), 2026-07-30 to
2026-08-20. basis=ln(CFD/spot): mean −6.09bps, sd 7.18bps.

**Q1 headline recompute — half-life**: AR(1) fit basis_t=a+φ·basis_{t-1}, φ=0.9265 (se=0.0022, t(φ=1)=−33.98,
strongly rejects unit root) → half-life **9.07 min**, matching the claimed 9.1min almost exactly.

**Which leg closes the gap (Granger-style, 60-min rolling mean/dev)**: next-minute spot return on basis-deviation
slope=+0.305 (t=+43.97) — spot moves to close the gap, as claimed. CFD next-minute return slope=**−0.056
(t=−7.59)** — significant and *negative*, i.e. CFD also mean-reverts slightly, not pure drift as the claim states.
Spot's contribution is 5.5× larger and far more significant, so the claim's qualitative direction (spot leg
dominates the correction) holds, but "CFD itself drifts in the same direction" is not literally true — it's
weak-but-real partial correction too. → **数値差異(結論維持)**.

**Q2 controls**: sign of φ<1 and t(φ=1)=−34 rules out spurious unit-root; XRP consistency check below serves as
independent-instrument control.

**Q3 translation / costs (derived, not claim-quoted)**: CFD taker_fee_pct=0.0%, mean spread 2.30bps one-way (from
ticker tape). Spot BTC_JPY taker_fee_pct=0.15% (`config/products.yaml`) = 15.0bps one-way; **no bitFlyer-spot
ticker data exists in this repo**, so spot spread is proxied at the CFD's 2.30bps as a floor (flagged assumption,
likely understates true spot cost — spot trades at ~30% of CFD volume, see below). Two-leg entry cost ≈19.6bps,
round-trip ≈**39.2bps**.

**k-grid P&L (enter |basis−rollingmean(60min)|>k·sd, exit at mean or 240min timeout)**:
k=1: n=3,360, gross +4.86bps, net **−34.35bps**, win%(after cost)=0%. k=2: n=1,069, gross +6.75bps, net
**−32.46bps**. k=3: n=168, gross +8.82bps, net **−30.39bps**. Every cell loses after cost at every k — matches R8's
"untradeable" conclusion directly.

**Q7 selection contamination**: block-shuffle null (60-min blocks, n=60) for best-of-{k=1,2,3} gross mean: null
mean 6.91bps (sd 0.21), real best 8.82bps, p≈0.02 — most of the *gross* edge is a mechanical artifact of "exit
exactly at the rolling mean" (shuffled basis still yields ~7bps gross), not real predictability. Moot for the
verdict since even the null gross edge is far below the 39bps round-trip cost.

**Q9 consistency**: independent basis pair bitFlyer-XRP_JPY vs bitbank-XRP_JPY: φ→half-life **3.00min**, sd
7.86bps — same sign/mechanism (real, faster-decaying reversion between two spot venues) but not the same
magnitude; supports that basis mean-reversion between correlated JPY-crypto venues is a general phenomenon, not
unique to the CFD/spot pair.

**Liquidity support for "untradeable" framing**: over the same window, FX_BTC_JPY (CFD) candle volume totals
14,089 BTC vs BTC_JPY (spot) 4,052 BTC (3.5× more liquid on the CFD side), and spot has **zero volume in 30.8% of
minutes** — consistent with spot being the thin, execution-constrained leg the claim calls untradeable, though we
could not directly test order-book depth (no spot ticker data).

**Q10 MDE**: n≈30,200 for the AR(1)/regression tests, same MDE(r)≈0.011 as L2 — φ deviation from 1 (0.0735) is
~7× the detection floor for the underlying regression; well-powered. Falsification: a repeat window with φ≥0.99
(half-life>10x longer) or with CFD slope flipping sign/losing significance would falsify the current read.

## 前提の誤り (assumption findings)

- **premise**: L4 frames CFD as pure "drift, does not correct" | **source**: L4 claim text | **data shows**: CFD
  next-return slope on basis-dev is significant and negative (t=−7.59), ~18% as strong as spot's | **bias**:
  overstates CFD's independence from the basis | **inherits**: any strategy note that assumes "never fade the CFD
  leg on basis signals."
- **premise**: L2/L3 imply a fixed "1-minute" vs "1-second" lag scale | **source**: L2/L3 claim text | **data
  shows**: ±1-minute alignment shift relocates the entire correlation peak to a different nominal lag — the 1-min
  finding is bounded by candle-close timing resolution, not a true ~60s causal delay | **bias**: implies more
  temporal precision than the data supports | **inherits**: any claim citing "lag1 at 1 minute" as a specific
  causal delay (L7, and any strategy sized to a 60s execution window).
- **premise**: L3's 1s lag1 is treated as reproducible from repo data | **source**: packet-X data path lists only
  1-min files for L3, no Binance sub-minute file exists | **data shows**: cross-exchange 1s comparison is
  structurally impossible here | **bias**: none on the claim itself (untestable either way), but its "available"
  status in the inventory is optimistic | **inherits**: any note treating L3 as confirmed rather than untested.
- **premise**: R8's implicit cost model | **source**: not quoted in the claim row | **data shows**: derived
  round-trip cost (39.2bps, dominated by the 15bps one-way spot taker fee) is what makes every k-cell unprofitable;
  a lower-fee spot tier would shrink but not flip the verdict (gross edge 4.9–8.8bps ≪ any realistic round-trip) |
  **bias**: none — conservative in the claim's own direction | **inherits**: R8 and any claim assuming
  taker_fee_pct=0.15% (lowest-volume worst case; a higher-volume account pays less).
- No premise found wrong for the AR(1) half-life (9.07 vs claimed 9.1min) or L2 headline correlations (reproduce
  to 3 decimals).

## Files read

`docs/AUDIT_2026-09/PROTOCOL.md`, `docs/AUDIT_2026-09/00_packets.md` (grepped rows only: L2/L3/L4/R8, packet-X
row), `config/products.yaml`, `backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz`,
`backtest_data/candles_BTC_JPY_20260820.csv`, `backtest_data/candles_XRP_JPY_20260820.csv`,
`backtest_data/bitbank_xrp_jpy_1m.csv`, `backtest_data/binance_BTCUSDT_1m.csv`,
`backtest_data/binance_XRPUSDT_1m.csv`, `paper_logs/tape/ticker_20260820.csv.gz`,
`paper_logs/tape/executions_20260820.csv.gz` (header only). `backtest_data/fred_DEXJPUS.csv` header checked but
not used — minute-scale return correlations don't need USDJPY conversion since both legs are compared directly
and USDJPY's own minute volatility is far smaller than BTC/XRP's.

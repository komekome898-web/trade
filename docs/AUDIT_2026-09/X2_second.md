# Packet X — second (blind) audit

Files read: docs/AUDIT_2026-09/PROTOCOL.md; docs/AUDIT_2026-09/00_packets.md (grep rows X, L2, L3, L4, R8 only);
backtest_data/candles_XRP_JPY_20260820.csv; backtest_data/bitbank_xrp_jpy_1m.csv;
backtest_data/candles_FX_BTC_JPY_20260820.csv; backtest_data/candles_BTC_JPY_20260820.csv;
backtest_data/candles_ETH_JPY_20260820.csv; backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz;
backtest_data/executions_FX_BTC_JPY_31d_20260823.csv.gz; backtest_data/binance_XRPUSDT_1m.csv;
backtest_data/binance_BTCUSDT_1m_210d_20260820.csv.gz; config/config.yaml; config/products.yaml.
Script: scratchpad/audit_X2.py. No forbidden files opened.

## L2

Denominator: 1-min log returns, Binance (leader) vs bitFlyer (follower), 2026-07-30→2026-08-20, both pairs aligned
on common minute timestamps. XRP: n=30,185. BTC: n=30,250.

Claimed vs recomputed:
| metric | claimed | recomputed |
|---|---|---|
| thin (XRP) lag1 corr | +0.176 | +0.1756 (n=30,185) |
| thick (FX_BTC_JPY) lag1 corr | +0.019 | +0.0186 (n=30,250) |
| contemporaneous (thick pair) | +0.878 | +0.8783 |

Controls: 200-shuffle permutation of the follower series. Null std ≈0.0053 (XRP) / 0.0060 (BTC); both observed r
exceed all 200 shuffles (p≤0.005, floor of this test). XRP's r is ~33 null-SDs out (very robust); BTC's r is only
~3 null-SDs out (real but weak — consistent with "vanishing" framing). Sign-reversed check is a trivial mirror,
not informative on its own.
Translation to money: trading every bar in the lag-1 sign gives XRP ≈0.62 bps/trade gross; XRP_JPY spot taker fee
is 0.15% one-way (config/products.yaml, worst volume tier) → net ≈ −14.4 bps/trade, and XRP_JPY is `shortable:
false`, so the short half of the signal cannot even be executed. BTC FX edge is ≈0.085 bps/trade gross against a
0% taker fee (FX_BTC_JPY) — near the noise floor either way. Neither leg is profitably tradable at 1-minute
granularity even though the correlations are statistically real.
Definition side-effect: measuring at 1-minute resolution likely folds most of the true reaction speed into the
"contemporaneous" bucket (0.878 for the thick pair) rather than lag1, which is consistent with L3's premise that
the residual lag lives at the sub-minute/second scale — but that could not be verified (see L3).
Consistency: ETH_JPY vs BTC_JPY (both bitFlyer spot, not a cross-exchange leader/follower pair) gives
contemporaneous 0.514 / lag1 0.072 — a different comparison shape, so it neither confirms nor contradicts this
claim; treat as inconclusive, not corroborating.
MDE: at n≈30,000, SE(r)≈1/√n≈0.0058, MDE95≈±0.011. BTC's 0.019 is only ~1.6-3x MDE — a small, boundary-detectable
effect; XRP's 0.176 is far above MDE and highly robust.

Verdict: 再現

## L3

Denominator (attempted): the packet's cited file `backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz` has a
median bar spacing of 60 seconds (checked directly) — it is 1-minute data, not 1-second. No 1-second candle file
exists anywhere under backtest_data/ (checked by glob for 1s/sec/second names — none found). The claim's headline
numbers (lag1 +0.11~+0.25 on 1-second bars, absorption in 1-2s) require a 1-second-resolution **cross-exchange**
lead series (e.g. an external leader), which is not available — Binance data on hand is only 1-minute bars.
As a partial, non-equivalent proxy, I built genuine 1-second bars from raw tick executions
(`executions_FX_BTC_JPY_31d_20260823.csv.gz`, 982,001 ticks, 2026-07-23→2026-08-23) via last-tick resampling and
measured FX_BTC_JPY's **own**-instrument 1-second return autocorrelation (not a cross-exchange lag, since no
comparably-resolved leader exists): lag1 = **−0.066**, lag2 = **−0.016**, n=2,679,367 seconds. This is negative
(bid-ask-bounce-like mean reversion), the opposite sign of the claimed positive lag. Restricting to bars with
|1s return|≥20bps (the claim's stated threshold) leaves only **38 of 2,679,367** bars (0.001%) — far too few for
any reliable inference (conditional corr on that n was −0.30, but this is noise-dominated).

Verdict: 再計算不能 — no data source at the required resolution/pairing exists to test the actual claim; the one
computable proxy (own-instrument 1s autocorrelation) is not a like-for-like test and in any case shows the
opposite sign, which further undercuts confidence but is not treated as a direct refutation given the mismatch.

## L4

Denominator: FX_BTC_JPY vs BTC_JPY (both bitFlyer, spot vs 2x-leveraged CFD), basis = FX close − spot close,
1-min bars, 2026-07-30→2026-08-20, n=30,177 aligned minutes. Basis mean=−6,187 JPY, std=7,240 JPY (≈6.9 bps of
spot price ≈¥10.5M).
Mechanism test: sorted basis into deciles; mean next-bar move by leg:
- basis HIGH decile (n=3,018): ΔFX=−46.7 JPY (flat), ΔSpot=+910.6 JPY (spot rallies to close the gap)
- basis LOW decile (n=3,017): ΔFX=+252.1 JPY (small), ΔSpot=−1,143.7 JPY (spot drops to close the gap)
In both directions the spot leg does 4-20x more of the convergence work than the FX leg — this reproduces
"closing leg is the (lagging) spot side; the CFD itself drifts independently."
Tradability / translation to money: config/products.yaml shows BTC_JPY spot is `shortable: false`,
`taker_fee_pct: 0.15` (15 bps, worst volume tier) vs FX_BTC_JPY `taker_fee_pct: 0.0`. The LOW-basis-decile trade
(short spot ahead of a ≈10.9 bps drop) is structurally impossible (not shortable); the HIGH-decile trade (long
spot, ≈8.7 bps expected move) is close to being erased by the 15 bps taker fee alone, before slippage. This
corroborates the "predictable leg is untradable" conclusion.
Consistency: no second FX/CFD-vs-spot pair exists among the configured products (ETH_JPY, XRP_JPY, XLM_JPY,
MONA_JPY, ELF_JPY, ETH_BTC, BCH_BTC are all spot-only per products.yaml) — a same-mechanism replication on a
second instrument is not possible with the products this bot actually trades, despite the packet listing
ETH/XRP candle files.

Verdict: 再現

## R8

Same data/method as L4 (basis AR(1) half-life + decile leg decomposition); R8's claim text is effectively a
restatement of L4's mechanism (regression-real, non-tradable leg), so this is not an independent replication —
see 前提の誤り.
Denominator: same n=30,177 aligned 1-min bars, 2026-07-30→2026-08-20.
Headline number: AR(1) on the basis series gives rho=0.9249/min → half-life = **8.88 min** vs claimed **9.1 min**
(≈2.5% difference) — close match on the pooled full sample.
Regime dependence (question 4): splitting the sample in half gives rho=0.948 (half-life=12.92 min, n=15,088) in
the first half vs rho=0.839 (half-life=3.94 min, n=15,088) in the second half — a >3x swing. The single "9.1 min"
figure is an average over a regime that is not stable, not a fixed physical constant.
Controls/alternative explanation: the decile decomposition (see L4) rules out pure bid-ask bounce as the
mechanism, since the effect is asymmetric across legs (spot moves, FX barely does) rather than symmetric noise
reversion in one series.

Verdict: 数値差異(結論維持) — the half-life point estimate is close (8.88 vs 9.1 min) and the qualitative
mechanism (spot-leg reversion, untradable) holds, but the instability across sub-periods (3.94-12.92 min) means
"9.1 min" should not be quoted as a stable constant.

## 前提の誤り

1. premise: L3's evidentiary basis is `candles_FX_BTC_JPY_31d_20260823.csv.gz`. | source: 00_packets.md row for L3
   names this file as "available". | what the data shows: this file is 1-minute bars (median spacing 60s exactly);
   no 1-second candle file exists anywhere in backtest_data/, and no sub-minute leader (Binance) series exists
   either. | bias: makes L3's positive-lag conclusion unverifiable rather than false — but a claim resting on data
   that isn't actually at the stated resolution should not be treated as reproduced by construction. | inherits:
   any other claim in this packet set that cites 1-second absorption dynamics or "L3" as supporting evidence.
2. premise: the "9.1 min" basis half-life (R8/L4) is treated as a fixed characteristic of the FX/spot pair. |
   source: R8 claim text. | what the data shows: half-life varies 3.94-12.92 min across the two halves of the
   same 21-day sample — over 3x. | bias: overstates precision/stability of any downstream sizing (e.g. max_hold
   windows) keyed to "9 minutes". | inherits: any claim or parameter choice that uses this half-life as a fixed
   holding-period target.
3. premise: L4/R8's "untradable predictable leg" conclusion is about BTC_JPY spot specifically. | source: L4
   claim text ("取引不能な現物側"), packet lists candles for BTC/ETH/XRP as if the mechanism generalizes. | what
   the data shows: products.yaml confirms only FX_BTC_JPY is an FX/CFD product; every other JPY pair (incl. ETH,
   XRP) is spot-only with no leveraged counterpart, so there is no "basis" to test for those assets at all — the
   claim cannot be a cross-asset finding, only a BTC-specific one. | bias: none on L4/R8's own conclusion, but
   any claim that cites this as a general cross-asset "basis mean-reversion" phenomenon overstates its scope. |
   inherits: any claim generalizing basis mean-reversion beyond FX_BTC_JPY/BTC_JPY.
4. premise: L4 and R8 are counted as two separate confirmations of the basis-reversion story. | source: 00_packets
   rows for L4 and R8 describe the same mechanism (regression real, untradable closing leg) with the same source
   tag (f) and same available data. | what the data shows: both were tested with an identical method on an
   identical dataset in this audit — they are not independent measurements. | bias: pooling them as two
   "reproduced" claims inflates apparent corroboration of the underlying mechanism. | inherits: any tally of
   "how many claims confirm basis mean-reversion" that counts L4 and R8 separately.
5. premise: the fee used to judge tradability of the lag/basis edges should be the exchange's advertised rate. |
   source: L2/L4 claims discuss tradability informally. | what the data shows: config/config.yaml's paper-fill
   cost model uses a flat `taker_fee_pct: 0.15` for all costs comments, while config/products.yaml differentiates
   FX_BTC_JPY (0% taker) from every spot pair (0.15%, worst volume tier) — the correct fee for the leg actually
   requiring execution (spot, in L4/R8; XRP spot, in L2) is 15 bps, not 0%. | bias: using the FX_BTC_JPY 0% figure
   for the spot leg would make the edges look tradable when the data show they are not (spot is the leg that must
   be traded, and it is shortable:false besides). | inherits: any claim that nets a spot-leg edge against the 0%
   FX_BTC_JPY fee instead of the 15 bps spot fee.

# Packet R — L7 リーダー追随族 死亡診断(機構水準)再監査

## Claim (verbatim, 00_packets.md §1.2, L7)
> リーダー追随族死亡診断: 1分lag1+0.016。210日25セル×5地平ドリフト<コスト床0.079%、n≥400でtaker線超え0.0%

Full context row: contemporaneous corr +0.890, lag1 +0.016; "follow Binance" momentum family over 210 days ×
25 cells × 5 horizons has drift −0.06〜+0.09% below a cost floor of 0.079%; 0.0% of cells (n≥400) above the
taker line; exits can't rescue it (required win ratio 5.55 vs realized 2.29, n=898).

## Files read
`docs/AUDIT_2026-09/PROTOCOL.md`; `00_packets.md` line 35 only (grep); `backtest_data/binance_BTCUSDT_1m.csv`;
`backtest_data/candles_FX_BTC_JPY_20260820.csv`; `..._30d_20260820.csv`; `..._31d_20260823.csv.gz`;
`backtest_data/fred_DEXJPUS.csv` (sanity only); `config/products.yaml` (FX_BTC_JPY row);
`paper_logs/spread_FX_BTC_JPY.csv`; `paper_logs/tape/board_top5_20260820.csv.gz` (peek only, unused).
Script: `audit_R.py` (scratchpad).

## 1. Denominator / population
Binance 1m closes: **30,240 rows**, 2026-07-30 02:26 – 2026-08-20 02:25 UTC (exactly 21.0 days, no gaps).
bitFlyer FX_BTC_JPY 1m closes (matching file): 30,251 rows, same window. Inner-join on exact minute timestamp
(both files already UTC-tagged) → **n=30,178** aligned minute pairs. **This is the entire usable overlap** — none
of the three bitFlyer candle files extends past 2026-08-23 and Binance stops 2026-08-20, so **the claim's "210
days" is not reproducible from repo data; only ~21 days are available.** This is the single largest constraint on
this audit (see §10, §前提の誤り).

## 2. Correlation reproduction (Q1, Q6 alignment)
Lag-0 corr(1m log returns) = **+0.878** (claim +0.890); lag+1 (bitFlyer follows Binance by 1min) = **+0.019**
(claim +0.016). Full lag sweep −5..+5: all |corr|≤0.03 except lag 0. **±1min misalignment test**: shifting the
FX series by −1/+1 min collapses corr(0-lag) from 0.878 to 0.023/0.019 — confirms the stored timestamps are
correctly aligned at the minute (a genuine 1-min offset would show up as the shifted correlation, not the
unshifted one, being the local max — it isn't). Consistency check on the two other FX files (different, longer
windows, still capped by Binance's 21-day span): fx30d lag0=0.8777/lag1=0.0201; fx31d lag0=0.8777/lag1=0.0193.
**All three reproduce the claim's headline numbers closely (Δ≤0.012 on corr, Δ≤0.003 on lag1).**

## 3. Cost floor — derived vs claimed (Q3)
`config/products.yaml`: `FX_BTC_JPY taker_fee_pct: 0.0`. No fee-based floor exists. Spread from
`paper_logs/spread_FX_BTC_JPY.csv` (n=237,674 snapshots, 2026-08-20–2026-09-04 — **does not overlap the
backtest window**, it's the only spread data in the repo): median **1.78bps**, mean 1.94bps, p90 3.03bps, p95
3.56bps, **p99 5.05bps**. Round-trip (cross-spread both legs) derived floor = 0.0%(fee) + 1.78bps(median spread)
= **0.0178%**. The claimed 0.079% (7.9bps) floor exceeds even the **p99** measured spread — it is not
reproducible as "spread + 0% fee" from any data in this repo; it must embed slippage/impact assumptions not
stated in the claim. Both floors are used below per protocol.

## 4. Follow-the-leader grid (Q1, Q2, Q7) — k∈{1,3,5}×thr∈{5,10,20}bps×h∈{1,5,15,60}min = 36 cells
(Claim's grid is "25 cells×5 horizons"=125; task spec fixes this 36-cell grid instead — not a literal
re-run of the claim's exact grid, an independent re-derivation on the same idea.)
32/36 cells have n≥400 (raw signal count). Gross drift range at n≥400: **0.0001%〜0.1253%** (claim: −0.06〜+0.09%
— sign/scale broadly consistent though our range is entirely ≥0, likely a k/thr/h grid-shape difference).
- Under **own 0.0178% floor**: 11/32 (**34.4%**) of n≥400 cells net>0 — clearly **not** 0.0%.
- Under **claimed 0.079% floor**: 2/32 (**6.2%**) net>0 (k=3,thr=20,h=60,n=409,net=+0.107%;
  k=5,thr=20,h=60,n=792,net=+0.039%) — close to but not exactly the claimed 0.0%.
Controls at every cell: random-direction-same-time and all-time-random-entry controls cluster near 0
(|mean|<0.03% in all but the thinnest cells); sign-reversed control is the exact negative of gross by
construction (confirms no lookahead leak).

## 5. Are the two "surviving" cells real? (Q5, Q7 — critical finding)
h=60min signals fire far more often than every 60min, so raw n vastly overstates independent trials: for
k=3/thr=20/h=60, 409 raw signals collapse to only **~66 non-overlapping (≥60min apart) events over 20.8 days**
(≈3.2/day); k=5/thr=20/h=60: 792→**~79** (≈3.8/day). The n≥400 gate (claim's and this audit's) is **not** an iid
sample-size gate for h=60 cells. Day-block bootstrap (2000 resamples, resample whole days) on these two cells:
- k=3,20,60: gross 95% CI **[−0.060%, +0.273%]** (own-floor net CI **[−0.078%, +0.255%]**; claimed-floor net CI
  **[−0.139%, +0.194%]**) — **crosses zero under both floors.**
- k=5,20,60: gross 95% CI **[−0.041%, +0.262%]** — also crosses zero under both floors.
Naive per-signal permutation test (circular-shift null, 200 draws) had flagged the best cell as p=0.000 vs null
— but that test inherits the same overlap-inflated-n problem, so it overstates significance. Day-clustered MDE
(n_days=20, α=.05, power=.80) for these cells is **0.108%/0.107%**, larger than the observed daily mean edge
(0.024%/0.043%) — **not detectable at the true (day-level) sample size.** Net: the two nominal "survivors" do
**not** hold up once clustering is corrected — this **supports** the claim's "dead" conclusion even though the
naive per-signal count disagreed with "0.0%".

## 6. Representative cell (k=1,thr=5bps,h=1min, n=3,103)
Gross +0.0023%, net −0.0155%(own floor) / −0.0767%(claimed floor); day-block CI tight and negative under both
floors: [0.0004%,0.0041%] gross → net stays negative in all resamples. Win% 48.5% (below 50%).

## 7. Win-ratio rescue check (Q — exits)
Representative cell: realized avg_win/avg_loss = **1.17**; required ratio to break even = 1.96 (own floor) /
**5.04 (claimed floor)** — same shape as claim's "required 5.55 vs realized 2.29" (claim's exact cell/n=898 is
not reproducible from the 21-day overlap; this is the closest analogous measurement, same conclusion: exits
cannot plausibly close a ~4x payoff-ratio gap).

## 8. Regime split (Q4) — best-own cell, FX 60min realized-vol terciles
low-vol mean −0.049% (n=137), mid +0.202% (n=136), high +0.224% (n=136) — the apparent edge concentrates in
higher-volatility minutes, consistent with volatility clustering (Q8: simplest-alternative explanation) rather
than a genuine leader-follower mechanism.

## 9. 1-second scale
Not testable: `paper_logs/tape/` contains `board_top5_*` (order-book snapshots) and `executions_*`
(bitFlyer-only fills), not a 1s-aligned Binance/bitFlyer joint tape — **as flagged in the task, this is
unavailable and not tested.**

## 10. MDE (Q10)
Trade-level MDE (α=.05, power=.80) at representative n=3,103: 0.0422%; at the claim's quoted n=898: 0.0785% —
**both are naive (iid) MDEs and are optimistic**; the real constraint is day-level clustering (§5): with only
~20-22 independent days in the entire available overlap, day-clustered MDE is ~0.03–0.11% depending on cell,
i.e. **effects smaller than ~0.03-0.1% per trade are structurally undetectable with the data this repo holds**,
regardless of raw n. A 210-day sample (claimed) would shrink this by ~√10 — this audit cannot rule out that the
claim's *own* 210-day run had adequate power; it can only say the *repo's current data* does not.

## Verdict: **数値差異(結論維持)**
| metric | claimed | recomputed | note |
|---|---|---|---|
| corr lag0 | +0.890 | +0.878 | Δ0.012, same conclusion |
| corr lag1 | +0.016 | +0.019 (avg 0.017–0.020 across 3 files) | reproduces |
| days available | 210 | **21.0** | claim's window not in repo — biggest limitation |
| cost floor | 0.079% | 0.0178% (spread-derived, non-overlapping window) | claim's floor > p99 measured spread |
| cells n≥400 net>0 | 0.0% | 6.2% (claimed floor) / 34.4% (own floor) | but the only 2 "winners" fail day-block CI (§5) |
| exits rescue? | no (5.55 vs 2.29) | no (5.04 vs 1.17, analogous cell) | same shape |
Bottom line: on the ~21 days of real overlapping data in this repo, the "follow Binance" family shows no
edge that survives (a) a realistic cost floor derived from actual quoted spreads, or (b) correction for
signal-overlap autocorrelation, which is the same conclusion the claim reaches. The claim's literal "0.0%"
and "0.079%" figures are not exactly reproducible here (own recompute: 34.4%/0.0178%; under the claimed floor
itself: 6.2%, not 0.0%), and both apparent "survivors" fail a day-block bootstrap — so the *conclusion* (dead)
is upheld, the *precision* of the claimed numbers is not fully reproducible from repo data alone.

## 前提の誤り (assumption findings)
1. **premise**: 210 days of overlapping Binance/bitFlyer data exist | **source**: claim's "210日" | **data
   shows**: only 21.0 days of Binance∪bitFlyer overlap exist in `backtest_data/` | **bias**: unknown direction —
   the claim cannot be power-checked against repo data; this audit's own grid is likewise 10x underpowered |
   **inherits**: every claim citing this Binance/bitFlyer pair or its "210 day" window (e.g. any packet reusing
   this cross-correlation or momentum-family result).
2. **premise**: cost floor = 0.079% | **source**: claim | **data shows**: taker_fee_pct=0.0% in
   `config/products.yaml`; measured spread (only available window, non-overlapping with backtest period)
   median 1.78bps, p99 5.05bps — 0.079% exceeds even p99 | **bias**: makes the "family is dead" conclusion
   *harder* to falsify (raises the bar strategies must clear), i.e. conservative in the claim's favor, but the
   number itself is not traceable to any single measured quantity in this repo | **inherits**: every rejection
   in this repo that cites a "0.079%" or similarly-derived taker/spread cost floor for FX_BTC_JPY.
3. **premise**: n≥400 signals is a valid "reliable cell" gate | **source**: claim's methodology (mirrored in
   the task's own n≥400 requirement) | **data shows**: for h=60min cells, raw signal n over-counts independent
   trials by ~6-10x due to signal overlap (409 raw → ~66 non-overlapping) | **bias**: inflates apparent
   precision/significance of long-horizon cells in *either direction* — could mask a real edge as noise or
   dress up noise as a real edge (here: dresses up noise, since the 2 "survivor" cells fail day-block CI) |
   **inherits**: any claim in this family that reports "n" as raw signal count for h>k cells without a
   non-overlap or day-clustering correction.
4. **premise**: spread/cost conditions are stable over time | **source**: implicit in applying one floor across
   the study | **data shows**: the only spread log available (`paper_logs/spread_FX_BTC_JPY.csv`) postdates the
   backtest window entirely (no temporal overlap) | **bias**: unknown — cannot verify the floor was measured in
   the same regime it's applied to | **inherits**: any FX_BTC_JPY cost-floor claim that doesn't cite a spread
   log overlapping its own backtest window.

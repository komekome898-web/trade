# Packet H — JPX overnight premium: cross-market + ETF-artifact claims (blind audit)

Claims: JPL6, JPL7, JPR6, JPR7, JPR8. Script: `scratchpad/audit_H.py` (own implementation, stdlib only).
Data: Yahoo Finance daily OHLC (`range=15y`) for 1321,1306,1591,2516,1343,1311,1547,2521,2558,1655,1557,7203,6758,8306,9984,
fetched live; `backtest_data/n225f_225labo_20260828/bars_1min.csv.gz` + its `manifest.json`.
Files read: PROTOCOL.md; `00_packets.md` grep hits for JPL6/JPL7/JPR6/JPR7/JPR8 (§1.9–1.10, row H); `config/products.yaml`,
`config/on1_live.yaml`, `src/bot/jpx/on1_executor.py` (fee/multiplier check — none found for JPX cash/ETF); manifest.json;
15 Yahoo JSON payloads. No other docs/ files, no scripts/research_*|judge_*|build_*, no git history opened.
Tickers: market-wide group = 1321(N225),1306(TOPIX),1591(JPX400),2516(Growth250),1343(J-REIT); thin = 1311(Core30);
UO1 group = 1547(NASDAQ100,JP),2521/2558/1655(S&P500,JP); 1557 = SPDR S&P500 foreign-listed (reference only).

## 0. Data-validity fix (item 6) — before any of the below
Raw Yahoo `close` has **15 isolated bad-print days** across 1306/2558/1655/1557 (e.g. 1557 on 2013-10-29/30/31,
2017-07-17/18: overnight swings of ±23,000–47,000bps that exactly reverse next print, with same-date day-return ≈0 —
a single corrupted close, not a market move; no legitimate move in-sample exceeds ~1300bps, 2025-04-07 tariff shock).
Excluded (`|on_bps or day_bps|>3000` flag). This **changes sign/significance** for 4 of 11 tickers (1306 t: -0.09→3.42;
1655 t: -0.21→2.50; 2558 t: -0.24→2.72; 1557 t: 0.31→5.29) — before cleaning, 3 series looked null/negative and would
have been read as contradicting JPL6. All numbers below are post-exclusion ("clean").

## 1. Denominator & headline overnight/day (full period, n = trading days with valid close_t-1→open_t)
| ETF | range | n | overnight bps (t) | day bps (t) | median turnover 億円/day |
|---|---|---|---|---|---|
|1321 N225|2011-09..2026-09|3686| 5.71 (3.39)| -0.25 (-0.18)| 77.24|
|1306 TOPIX|2011-09..2026-09|3684| 5.33 (3.42)| -0.72 (-0.55)| 38.59|
|1591 JPX400|2014-01..2026-09|3102| 7.79 (4.67)| -4.05 (-2.67)| 0.79|
|2516 Growth250|2018-01..2026-09|2108| 5.27 (1.79)| -7.56 (-2.15)| 4.50|
|1343 J-REIT|2011-09..2026-09|3686| 5.13 (4.68)| -3.40 (-2.14)| 3.57|
|1311 Core30(thin)|2011-09..2026-09|3687| 9.02 (5.59)| -4.44 (-2.84)| **0.05** (claim said 0.3 — actual thinner)|
|1547 NASDAQ100(JP)|2011-09..2026-09|3686| 8.84 (4.65)| -1.77 (-1.83)| 0.48|
|2521 S&P500(JP)|2018-07..2026-09|1979| 6.53 (2.49)| -2.62 (-2.23)| 0.97|
|2558 S&P500(JP)|2020-01..2026-09|1623| 8.43 (2.72)| -0.60 (-0.41)| 5.28|
|1655 S&P500(JP)|2017-09..2026-09|2195| 6.46 (2.50)| 0.13 (0.12)| 6.65|
|1557 SPDR S&P500(foreign)|2011-09..2026-09|3678| 9.71 (5.29)| -2.62 (-2.69)| 0.95|

**All 11 series: overnight > 0 with day ≤ 0 (sign-reversed check passes for every ticker but 1655's day, +0.13bps,
t=0.12, i.e. indistinguishable from 0).** Market-wide group (5 core index families) all positive, t 1.79–4.68.

## 2. Controls
- Shuffled-date placebo (500 resamples of half the series): real mean sits inside the placebo distribution for every
  ticker (|z| ≤ 0.09) — the *placebo mean itself* is ≈ the real mean because overnight bps is close to i.i.d. across
  days; this control mainly confirms no single-day outlier drives the mean (already handled in §0), it does not
  distinguish genuine premium from artifact by itself.
- Single-day vs multi-day-gap overnight (weekday-to-weekday vs weekend/holiday), market-wide+thin group: effect
  survives restricting to single trading-day gaps for all 6 tickers (t 1.73–4.80), so it is **not** purely a
  holiday-accumulation artifact — though multi-day gaps run larger for 1343 (10.44 vs 3.59bps) and 1306 (8.29 vs
  4.51bps), a partial confound worth noting.
- Sign-reversed: day-session mean is ≤0 or ~0 everywhere (see table) — consistent with the claim's asymmetry.

## 3. Translation to money / cost
No JPX cash-ETF fee/spread constant exists anywhere in this repo (`config/products.yaml` is crypto-only;
`config/on1_live.yaml` and `src/bot/jpx/*` carry no ETF commission or spread figure) — **do not trust any fee number
the claim quotes**; none is derivable from repo config for this instrument class. Proxy only: median intraday
(high−low)/close, 1311 = 106.6bps vs its 9.0bps overnight edge — a single day's normal price range is >10× the
raw overnight edge, so realistic execution cost (even a small fraction of that range) plausibly erases it. 1321
(liquid): 99.4bps range vs 5.7bps edge — same conclusion, more so for less liquid names. Gross JPY per ETF unit
(100 shares), current prices: 1311 ≈2152×9.02bps×100≈1,940円/day; 1321≈66,480×5.71bps×100≈37,960円/day
(gross, no cost applied — cost data absent).

## 4. Regime dependence (overnight bps by era, positive-count/5 = market-wide group)
2011-14: 4/4 positive (2516 has no data yet), t 2.30–2.65. 2015-18: mixed/weak — 1343 slightly negative
(-1.17,t=-0.75), 1591 weak (2.11,t=0.74), 2516 weak (2.16,t=0.22); **this era is the weakest support for JPL6**.
2019-22: 5/5 positive, t 0.92–3.63. 2023-26: 5/5 positive and mostly strongest, t 1.40–5.30. So JPL6 holds as an
average-period, strengthening-recently effect, not a uniformly-significant-every-era one.

## 5/7. Artifact test (JPL7/JPR8): overnight premium vs log(median turnover), n=11 ETFs
OLS slope = -0.57 bps per unit ln(JPY turnover), t=-2.88, R²=0.48; permutation p=0.019 (5000 shuffles of the
ticker↔premium pairing). Robust to dropping 1311 (t=-2.32) and to dropping 1311+1557 (t=-1.99); **not** significant
within the market-wide-5 subset alone (t=-1.20, n=5 — too few points). n=11 is a small, non-arbitrary set (all
tickers the task specified), so this is a real cross-sectional pattern, not free-parameter mining — but n=11 gives
low power (§10).
**1311 vs its own largest constituents** (7203/6758/8306/9984, n=3687 common days): corr(1311 overnight,
equal-weight constituent overnight) = **0.759** — high, i.e. 1311's overnight mostly tracks genuine constituent
price information, it is not noise. 1311 mean 9.02bps vs constituents' equal-weight mean 7.16bps (t=3.34) — a
**+26% excess**, not an order-of-magnitude artifact. **Direction of JPL7 reproduces (thinner → larger overnight);
the "純アーティファクト" framing overstates it — daily OHLC data cannot distinguish a genuine illiquidity/order-flow
premium from an auction-print artifact, and the excess magnitude (+26%, high correlation to true price) argues
against pure artifact.**

## 8. RB1 (JPR6): N225 futures 1-min, day-open→15:00 vs 15:00→15:45, n=170 days (2025-12-30..2026-08-28, matches
the snapshot's day count exactly — same underlying data as the recorded claim)
corr(r1,r2) = -0.06; placebo (500× shuffled r2) corr mean=-0.005, sd=0.075 → real corr z=-0.73 (inside placebo
noise). Follow-the-day P&L: |r1|≥30bps n=137 mean=-0.55bps t=-0.16; ≥50bps n=116 mean=-1.60bps t=-0.42; ≥100bps
n=64 mean=-1.10bps t=-0.19. Fade (sign-reversed) P&L is the exact mirror (+0.55/+1.60/+1.10bps, same |t|) — as
expected for a symmetric null. **Matches claim closely ("≈-1bps, t≈0"). Verdict: reproduced.**
MDE at these n (two-sided α=.05, ~80% power, using observed cell SD): 30bps-cell MDE≈9.6bps; 50bps-cell≈10.7bps;
100bps-cell≈16.2bps. **A genuine few-bp rebalance-flow effect (economically plausible size) would NOT have been
detected at n=170** — the null is a "not significant," not proof of exactly-zero effect.

## 9. UO1 (JPR7): Tokyo-day (open→close) mean bps by year, JPX-listed US-index feeder ETFs
2521 (S&P500, listed 2018): 2018 **-20.7bps t=-3.09**, 2019 **-10.7bps t=-2.76**, then 2020-2026 range -3.1..+5.6bps,
none |t|>1.9 — negative concentrated in listing years, then flattens (no plateau). 1655 (listed 2017): 2017
**-14.7bps t=-2.35**, 2018 -3.5bps (t=-1.18, weaker), 2019-2026 range -3.0..+3.6bps mostly positive-leaning. 2558
(listed 2020): 2020 **-14.0bps t=-1.99**, 2021-2026 range -0.4..+3.9bps. 1547 pre-dates the 15y Yahoo window
(untestable for a listing-year effect here — noted as a data gap, not evidence either way). **3/4 testable tickers
show the claimed pattern (large significant negative only in listing year 1-2, then no persistent negative level).
Verdict: reproduced.**

## Verdict table
| Claim | Claimed | Recomputed | Verdict |
|---|---|---|---|
|JPL6|夜間プレミアム市場横断で正|5/5 market-wide ETFs positive, t 1.79-5.30 full period (weak in 2015-18)|再現|
|JPL7|薄いETF夜間はアーティファクトで過大(1311, 0.3億円/日)|1311 turnover 0.05億円/日 (thinner); overnight +26% vs liquid constituents, corr=0.76 (real co-movement); turnover↔premium regression t=-2.88,perm p=.019, robust ex-1311|数値差異(結論維持) — direction holds, "artifact" causal claim unverifiable with daily OHLC|
|JPR6|RB1: no rebalance-flow effect, ≈-1bps t≈0|corr=-0.06 (within placebo noise); follow-day -0.55~-1.60bps, |t|≤0.42, n=170 (matches claim's day count)|再現 (but MDE≈10-16bps — small true effects can't be ruled out)|
|JPR7|UO1: Tokyo-day負は上場初年集中、恒常的水準なし|3/4 testable tickers: listing-yr t≈-2 to -3, then flattens; 1547 untestable (pre-window)|再現|
|JPR8|1311夜間は約定アーティファクト(0.3億円/日)|same evidence as JPL7 (turnover 0.05億円/日, +26% excess, corr=0.76)|数値差異(結論維持)|

## 前提の誤り (assumption findings)
1. **premise**: 1311 turnover ≈0.3億円/日 (JPL7/JPR8) | **source**: 第40報 | **data shows**: median 0.05億円/日 over
   full 2011-2026 sample (6× thinner than claimed) | **bias**: makes the artifact story *more* plausible, not less —
   doesn't overturn direction, but the claim's own headline number is off by 6×; if 0.3億円 was a recent/short-window
   figure it should be labeled as such, not quoted as the series characteristic | **inherits**: any other claim citing
   "1311 = 0.3億円/日" as a fixed fact.
2. **premise**: thin-ETF overnight inflation = "約定アーティファクト" (mechanical artifact) | **source**: 第40報 |
   **data shows**: 1311 overnight correlates 0.76 with liquid Core30 constituents' own overnight (which also show a
   genuine 7.16bps premium, t=3.34) — most of 1311's overnight is real, shared price information, with a +26% excess
   on top | **bias**: overstates the "artifact" framing; a genuine (if modest) illiquidity/order-flow premium is at
   least as consistent with the data | **inherits**: JPL7, JPR8, and any downstream claim that treats 1311's overnight
   as pure noise to be filtered rather than a smaller real effect to be sized.
3. **premise** (implicit in RB1/UO1 rejections): no-effect conclusions were treated as settled | **source**: 第40報 |
   **data shows**: RB1 MDE ≈10-16bps at n=170 (economically plausible rebalance-flow effects of a few bps would go
   undetected); UO1's 1547 cannot be tested for a listing-year effect at all in a 15y window | **bias**: both
   rejections are likely directionally right but should be labeled "not detected at available power," not "no
   effect exists" | **inherits**: any claim citing RB1/UO1 as proof-of-absence rather than non-detection.
4. **premise**: a JPX-ETF trading-cost figure exists to translate bps→JPY | **source**: implied by any P&L framing
   of these claims | **data shows**: no such constant exists anywhere in `config/` or `src/bot/jpx/` — this repo has
   never priced JPX cash-ETF execution cost | **bias**: any net-of-cost number attached to these claims elsewhere is
   unsourced from this repo and should be treated as external/unverified | **inherits**: every claim that quotes a
   net JPY/day or net-of-cost bps figure for these ETFs.
5. Raw Yahoo data validity (§0): 15 bad-print days silently reverse the sign/significance of 4/11 tickers if not
   filtered — no source claim mentions this, so if the original 第40報 numbers were built on unfiltered Yahoo pulls
   for these same tickers, some inputs may have been contaminated (cannot verify without seeing the original script,
   which is out of scope here).

Budget used: ~34 tool calls (network fetch, 1 script, iterative refinement), well under the 50-call cap.

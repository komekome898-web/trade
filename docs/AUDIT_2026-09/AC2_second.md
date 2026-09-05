# AC packet — second (blind) audit

Claims: L17, R24, PR13. Independent script: `audit_AC2.py` (scratchpad). Data used: `backtest_data/daily_btcusd_bitstamp_20260828.csv.gz` (2011-08-22..2026-08-28, n=5486, ~15.0y — chosen because it is the only BTC source matching "15年"), `daily_ethusd_coinbase_20260828.csv.gz` (2016-05-18..2026-08-28, n=3753, ~10.3y — matches "10年"), plus `daily_btcusd_{coinbase,yahoo}` for consistency checks, and `config/products.yaml` (BTC_JPY/ETH_JPY `taker_fee_pct: 0.15`) for cost. No forbidden files opened (research_*/judge_*/build_*/PREREG/KNOWLEDGE/git history/QA all avoided). The claim text does not specify which 6 SMA/TSMOM parameterizations form the "6 cells"; I reconstructed 3 canonical variants per asset (SMA50, SMA200, TSMOM 6-month sign rule, long/flat) × {BTC, ETH} = 6 cells. This substitution is flagged below and limits how tightly numbers can match.

## L17
Claim: BTC 15y, SMA/TSMOM6 cells, maxDD floor −70〜−82%; premium decays monotonically per halving cycle (+100.6→−27.7pp).

Denominator: BTC bitstamp daily closes, 2011-08-22 to 2026-08-28, n=5486 bars (~15.0y), long/flat signal, cost = 0.15%/side (config/products.yaml) applied on every signal switch (281 switches over the period, 2.81pp/yr drag).

Recomputed maxDD (net of cost), BTC-only 3 cells: SMA50 −70.4%, SMA200 −70.8%, TSMOM6 −72.4%. Range −70.4%〜−72.4% — sits at the low end of the claimed −70〜−82% band; I found no BTC-only cell reaching −82% (plain buy&hold on the same series is −84.9%, so −82% is plausible only for a much weaker filter or an unfiltered/near-buy&hold cell not in my 3-cell reconstruction).

Cycle premium (strategy return − buy&hold return, per inter-halving window, BTC SMA50): 2011-11/2012‑11→+93.8pp, →2016‑07 **−732.2pp**, →2020‑05 +230.6pp, →2024‑04 +265.6pp, →2026‑08 +20.6pp. This is **not monotonic** — it swings sign twice and includes a −732pp trough in the 2012–2016 cycle (SMA missed most of the multi-thousand-percent 2013–2015 run-up/whipsaw). Only the two endpoints loosely resemble the claimed shape (mine: +93.8pp→+20.6pp vs claimed +100.6→−27.7pp); the interior contradicts "単調減衰" outright.

Controls: shuffled-return placebo (BTC returns permuted, same SMA50 exposure schedule, n=200) → mean maxDD −77.6% (p5 −92.3%, p95 −63.5%) — a strategy with no real timing skill already produces ≥70% drawdowns most of the time on reshuffled BTC data, so the −70% floor looks largely like a volatility-tail artifact of BTC itself, not a discriminating property of SMA/TSMOM. Random binary signal at matched exposure (n=200): mean maxDD −89.0%. Sign-reversed SMA50: −91.2% maxDD, CAGR −12.2% (correctly worse than the real filter, as expected in a trending market, but not by a wide margin vs the random control).

Claimed vs recomputed:
| metric | claimed | recomputed |
|---|---|---|
| maxDD floor (BTC cells) | −70〜−82% | −70.4%〜−72.4% |
| cycle premium shape | +100.6→−27.7pp, monotonic | +93.8, −732.2, +230.6, +265.6, +20.6pp, non-monotonic |

The maxDD-floor component is directionally supported but does not reach the claimed lower bound (−82%) in my reconstruction; the premium-decay component's monotonicity is contradicted by my recompute, though I cannot rule out that the original used a different "premia"/"cycle" definition (unverifiable without the forbidden research script).

Verdict: 数値差異(結論維持)

## R24
Claim: LT1 rejected — maxDD FAIL (6 cells all worse than −70%), latter-half Sharpe FAIL, premium monotonic decay.

Denominator: 6 cells = {BTC bitstamp 15.0y, ETH coinbase 10.3y} × {SMA50, SMA200, TSMOM6}, net of 0.15%/side cost.

maxDD per cell: BTC SMA50 −70.4%, BTC SMA200 −70.8%, BTC TSMOM6 −72.4%, ETH SMA50 **−62.5%**, ETH SMA200 −80.8%, ETH TSMOM6 −88.7%. 5 of 6 cells breach −70%; ETH SMA50 (−62.5%) does not, though it is still a severe drawdown. "全て−70%超" is not exactly reproduced (5/6 = 83%, not 6/6), but the qualitative FAIL conclusion (catastrophic tail risk across the grid) is strongly supported.

Latter-half Sharpe (annualized, net of cost, split at series midpoint): BTC SMA50 1.56→1.32, BTC SMA200 1.65→0.93, BTC TSMOM6 1.64→0.81, ETH SMA50 1.71→0.77, ETH SMA200 1.62→0.75, ETH TSMOM6 1.50→−0.01. **All 6/6 cells degrade** second-half vs first-half — this component reproduces cleanly.

Premium monotonic decay: not reproduced (see L17; −732pp trough breaks monotonicity).

Vol-tercile regime check (BTC SMA50, question 4): low-vol days mean daily return +0.260%/Sharpe 2.43, mid-vol +0.140%/1.09, high-vol +0.292%/1.31 — the strategy's edge is not concentrated in one vol regime in a way that explains away the drawdown; the FAIL is not a low-vol artifact.

MDE (95%, BTC n=5486 daily obs, daily σ=4.26%): ≈2.2pp/year on annualized mean return — the sample is large enough that the observed CAGR gaps (tens of percentage points) are far above the detectable floor, so failing to detect a smaller true edge is not the explanation here.

Verdict: 数値差異(結論維持)

## PR13
Claim: PREREG_trend_lt1 (BTC 15y/ETH 10y) → LT1 rejected, citing R24.

This is a pointer/decision claim with no independent numeric content beyond R24's. The underlying PREREG document itself is forbidden reading (PREREG file), so I cannot check the exact preregistered numeric bar (e.g., was the DD threshold exactly −70%, or something else). What I can check is whether independently recomputed data support a rejection under the criteria R24 itself states (maxDD breach, Sharpe degradation): yes — 5/6 (approaching "all") cells breach −70% DD and 6/6 cells show second-half Sharpe degradation net of realistic 0.15%/side cost, on both BTC (15.0y) and ETH (10.3y) series matching the stated horizons. The rejection decision is consistent with independently recomputed data, though the precise preregistered threshold values could not be verified (forbidden document).

Verdict: 再現

## 前提の誤り

- premise: the "6 cells" are a specific, disclosed SMA/TSMOM parameter grid | source: L17/R24 claim text ("SMA/TSMOM6セル") | what the data shows: the claim text names no lookback windows; I substituted 3 canonical variants (SMA50, SMA200, TSMOM 6-month) per asset, which reproduces the qualitative FAIL but only 5/6 cells beyond −70% and does not reach the claimed −82% upper bound | direction of bias: unknown magnitude, could go either way — makes the exact "−70〜−82%" band and "6/6" count unverifiable as stated | inherits to: any other AC/L/R claim quoting this same "6セル" grid or its exact bounds.
- premise: "premia decays monotonically per cycle" with a smooth two-point-summarized trajectory (+100.6→−27.7pp) | source: L17 claim text | what the data shows: halving-to-halving cycle premium (BTC, SMA50) is +93.8, −732.2, +230.6, +265.6, +20.6pp — non-monotonic with a large negative trough | direction of bias: the claim's "単調" framing overstates the smoothness/predictability of the decline; a reader could wrongly infer a stable, low-noise trend-premium decay when the underlying series is highly volatile and sign-flipping | inherits to: any claim citing "monotonic cycle-premium decay" as evidence of a decaying edge (e.g. related TSMOM/cycle-premium claims elsewhere in the docs).
- premise: the −70%+ maxDD floor is diagnostic of the SMA/TSMOM strategies under test | source: implied framing of L17/R24 ("セルmaxDD床") | what the data shows: a return-shuffled placebo with the same exposure schedule (no real timing skill) already produces mean maxDD −77.6% (n=200), and a random binary signal at matched exposure produces mean −89.0% — i.e. BTC/ETH's own volatility/fat left tail explains most of the floor, not the specific trend rule | direction of bias: does not overturn the rejection (if anything strengthens it — timing does not rescue tail risk), but the claim would overstate what the number reveals about SMA/TSMOM specifically if read as strategy-discriminating | inherits to: any claim that cites a strategy's maxDD in isolation as evidence of strategy quality without a no-skill control.
- premise: BTC "15年" and ETH "10年" windows are the natural/only choice | source: L17/R24/PR13 horizon labels | what the data shows: 3 BTC sources exist (bitstamp 15.0y, coinbase 11.1y, yahoo 12.0y) and results are source-dependent — SMA50 maxDD is −70.4% on bitstamp (full 15y, includes the illiquid 2011 series with a static-price/near-zero-volume opening row) vs only −59.0%〜−59.2% on yahoo/coinbase (shorter, excludes 2011–2014) | direction of bias: choosing the longest series (bitstamp) to hit "15年" also pulls in the lowest-quality/least-liquid early data and produces the deepest drawdown among the three sources — the reported floor is not source-robust | inherits to: any claim quoting a BTC "15-year" maxDD/Sharpe number without stating which source, and any claim that treats 2011–2014 bitstamp prices as reliable.
- premise: cost dosage (fee assumption) is immaterial to the DD/Sharpe conclusions | source: not stated numerically in the claim | what the data shows: I substituted config/products.yaml's BTC_JPY/ETH_JPY `taker_fee_pct=0.15%` per side (a bitFlyer JPY spot fee) applied per signal switch to a USD daily series from a different venue; cumulative drag was small (~42pp over 15y, 2.81pp/yr for BTC SMA50) so it does not materially change the DD floor, but it is a cross-venue/cross-currency substitution, not a value taken from the original USD backtest's own cost model | direction of bias: negligible on maxDD conclusions here, but flagged since it is an assumption swap, not a verified constant | inherits to: any claim expressing this study's costs in JPY/bitFlyer terms while backtesting on USD spot data.

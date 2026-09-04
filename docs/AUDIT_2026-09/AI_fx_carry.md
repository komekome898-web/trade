# Packet AI — FX Swap Formula / Carry Rejection (FXC6, FXR8)

Blind audit per PROTOCOL.md. Own script: `audit_AI.py` (scratchpad, not committed). Budget used: ~29 tool calls.

## Files read
`docs/AUDIT_2026-09/PROTOCOL.md`; `docs/AUDIT_2026-09/00_packets.md` (grep on FXC6/FXR8/packet-AI rows only,
§1.5/§1.7/§AI-row); `backtest_data/gmo_swap_usdjpy.csv`; `backtest_data/fred_DFF.csv`;
`backtest_data/fred_DGS2.csv` (header/tail only, unused in final calc); `backtest_data/fred_IR3TIB01JPM156N.csv`;
`backtest_data/fred_IRSTCI01JPM156N.csv`; `backtest_data/fred_DEXJPUS.csv`;
`backtest_data/fx_fundamentals_20260822/MANIFEST.json`; `config/products.yaml`; `config/config.yaml` (grep).

## Method
Denominators: FXC6 fit on gmo_swap_usdjpy.csv overlap with FRED, n=835 days with swap_days>0
(2023-04-26→2026-08-21; buy leg only — GMO shows buy/sell separately, no true mid). Lot size assumed
10,000 USD/lot (not in config — this bot does not trade spot FX; validated below by matching the median).
FXR8: DFF (US o/n, daily) − IRSTCI01JPM156N (Japan uncollateralized call rate, monthly, ffilled) is the only
combination in the provided files spanning ~41y (IR3TIB only since 2002; DGS2 mismatched tenor vs a call
rate). Daily total return = income accrual (rate diff × elapsed days/365) + log(DEXJPUS) price return,
n=10,320 obs / 1985-07-02→2026-08-14 (42 partial calendar years, 41 full years 1985–2025).

## Claimed vs. recomputed

| # | Claim | Recomputed | Match |
|---|---|---|---|
| FXC6 | median long swap 1.108 bps/day (2026: 0.696) | median 1.1083 bps/day (n=835); 2026 median 0.6957 (n=152) | 再現 (validates lot-size=10,000 assumption) |
| FXC6 | formula: mid = diff×1.056 + 0.162bps | own OLS (DFF−IRSTCI): a=−0.049, b=0.966, R²=0.48; claimed (a,b) applied to my series gives R²=−0.29 (worse than the mean), mean bias −0.32bps/day. TIBOR variant: a=0.177, b=0.816, R²=0.48 | 数値差異(結論維持) — direction/scale (≈1:1 slope) holds, exact constants don't reproduce off my rate proxy; half the variance (R²≈0.48) is unexplained by either fit |
| FXR8 | 33 of 41 years income-positive | 39/41 full years (1985–2025) income-positive on DFF−IRSTCI | 数値差異 — same sign/majority, count differs |
| FXR8 | unconditional/trend/vol-targeted all reject, judged Sharpe 0.487 <0.70 | unconditional 0.106 (ann., daily); trend-gated (12m sign, lagged) 0.535, 95%CI[0.248,0.826]; vol-targeted (10%, 60d, cap3x) 0.241 | 再現 (all three point estimates <0.70; trend-gated closest and CI touches 0.70) |
| FXR8 | price variance 4.7–5.4× income | annual variance ratio 30.6×; annual **std-dev** ratio 5.53× | 数値差異(結論維持) — matches only if "variance" in the claim means std-dev, not var; true variance ratio is ~30×, not ~5× |

## The 10 questions
1. **Denominator**: see Method. FXC6 n=835 overlap days; FXR8 n=10,320 daily obs / 41 full years.
2. **Controls**: shuffled placebo is a no-op for the *unconditional* series by construction (Sharpe=mean/std
   is order-invariant under permutation — reported 0.106 for both raw and shuffled, this is expected, not a
   finding). For **trend-gated**, which is order-dependent, 200 full-reshuffles of (income,price) tuples give
   placebo Sharpe mean 0.166, p95 0.366 vs. the real 0.535 — 0/200 draws matched or exceeded, i.e. the
   trend-gate is capturing real serial structure, not an artifact of the mean/vol level. Sign-reversed:
   −0.106, mirrors long as expected. State-conditional (60d realized-vol terciles): unconditional carry
   Sharpe is 0.805 in the low-vol tercile, −0.185 mid, −0.001 high — carry works only in calm regimes, and
   the vol-targeted variant (designed to correct exactly this) still lands at 0.241, below 0.70.
3. **Translation**: no FX_USDJPY spread constant exists in config/*.yaml — this bot trades FX_BTC_JPY (crypto
   CFD), not spot FX, so no fee key applies. Using an explicitly-flagged 0.5bps round-trip assumption:
   trend-gated turnover is 327 switches/41y (8.2/yr) → ~163.5bps cumulative drag over 41 years (Sharpe
   0.535→0.529); vol-targeted daily releveraging → ~76bps cumulative (~1.9bps/yr) vs. ~247bps/yr mean return.
   Costs are immaterial to the verdict either way at this trade frequency.
4. **Relative vs absolute**: yes — regime-dependent (vol terciles above). The claim is a level claim (Sharpe
   over the full 41y) and is measured that way here; the regime split is an additional check, not a
   redefinition.
5. **Definition side-effects**: "income-positive year" (this audit) vs "total-return-positive year" differ
   sharply (39/41 vs 20/41) — using price-inclusive P&L to describe "income" would understate the real point;
   this audit kept them separate per the claim's own framing ("収入実在...だが" implies income is judged
   apart from total P&L).
6. **Data validity**: DEXJPUS/DFF/IRSTCI are official daily/monthly series, no visible gaps in the loaded
   range; monthly JP rates forward-filled (introduces a stepwise/stale-rate artifact at each month boundary,
   understating intra-month rate-differential variation — doesn't affect price-driven Sharpe materially since
   price return dominates variance by >30×). gmo_swap_usdjpy.csv weekend triple-day rollover rows (swap_days
   >1) correctly divided by swap_days to get a daily rate before fitting.
7. **Selection contamination**: trend/vol-target parameters (252d window, 10% target, 60d vol, 3x cap) are
   this audit's own reasonable-default choices, not searched — a single specification each, so no sweep to
   correct for; flagged as free parameters an owner-side search could exploit if repeated across many window
   choices. FXC6 rate-proxy choice (call rate vs TIBOR) is likewise one of two tried, both giving R²≈0.48.
8. **Alternative explanation**: unconditional carry's Sharpe (0.106) is fully explained by price-return
   volatility swamping a small, low-variance income stream (annual std ratio 5.53×) — ordinary FX spot-return
   volatility, not carry-specific signal, dominates. No survivorship/bid-ask-bounce channel applies (macro
   spot series, not microstructure).
9. **Consistency**: FXC6's headline median (1.108bps) reproduces near-exactly from independent construction
   (lot-size assumption validated by matching both the full-sample and 2026-only medians), which cross-checks
   that FXR8's underlying income-accrual mechanism (same rate-differential idea) is being computed correctly.
   The two claims are mutually consistent in sign and rough scale.
10. **Falsification / MDE**: falsification sentence — "if the recomputed 41y Sharpe (any of the three
    variants) has a 95% CI whose lower bound exceeds 0.70, the rejection is wrong." None do: unconditional
    CI [−0.210, 0.429], trend-gated [0.248, 0.826], vol-targeted [−0.118, 0.496] — all three CIs sit at or
    below 0.70, though trend-gated's upper bound (0.826) crosses it, so absence-of-effect-above-0.70 is not
    airtight for that one variant. MDE at n=41 (yearly obs, α=0.05, power=0.80) ≈ 0.44 in Sharpe units — a
    true Sharpe as large as ~0.44 could plausibly go undetected at this sample size, meaning the 41-year
    design has real power only to reject fairly large effects, not to finely distinguish e.g. 0.55 from 0.70.

## Verdict
- **FXC6 (swap formula)**: 数値差異(結論維持). The descriptive number (median long-swap bps/day) reproduces
  almost exactly, confirming the underlying swap-conversion methodology. The specific regression constants
  (×1.056, +0.162bps) do not reproduce against an independently-chosen but standard interbank differential
  (US o/n − JP call rate); my own refit gets a similar order of magnitude (slope ≈0.82–0.97, R²≈0.48) but not
  the claimed exact numbers, and applying the claimed formula out-of-fit performs worse than the sample mean.
  Substance (swap ≈ scales with the rate differential, ~half the variance explained, rest is noise/spread)
  holds; the precise formula is not independently verifiable from the files provided.
- **FXR8 (carry rejection)**: 再現. All three variants (unconditional 0.106, trend-gated 0.535, vol-targeted
  0.241) recompute below the 0.70 bar, matching the claimed rejection in direction and rough magnitude (my
  trend-gated number, 0.535, is the closest analog to the claimed judgment figure 0.487 and is in the same
  range). Income is real (39/41 years positive here vs. claimed 33/41 — same conclusion, count differs) and
  overwhelmed by price variance (std ratio ≈5.5×, matching the claimed 4.7–5.4× if that figure is a std-dev
  ratio rather than a variance ratio). The MDE (~0.44) and the trend-gated CI upper bound (0.826) mean the
  rejection is directionally solid but not iron-clad — a moderately large true edge in the trend-gated
  specification specifically cannot be fully ruled out at n=41 years.

## 前提の誤り (assumption findings)
- **Lot size (10,000 USD/lot)**: source: not stated in the claim or in config (no FX_USDJPY entry anywhere in
  config/*.yaml, since this bot never trades spot FX). What the data show: assuming 10,000 validates the
  headline median (1.108 vs 1.1083, 0.696 vs 0.6957) almost exactly, so the assumption is very likely correct,
  but it is unverified by any config value — a silent, unstated constant. Bias: none on the conclusion (self-
  consistent), but the number is not audit-traceable without an external GMO contract-spec citation. Inherits:
  any other claim quoting GMO swap bps/day figures from this same file.
- **"Variance" vs "std-dev" ratio (4.7–5.4×)**: source: FXR8 claim text says "variance". What the data show:
  the true variance ratio (annual) is ≈30.6×; only the standard-deviation ratio (≈5.53×) lands near the
  claimed range. Bias: none on the qualitative conclusion (price dominates income either way), but a reader
  taking "variance" literally would compute a 6× larger dominance than the claim states — a wording/units
  ambiguity, not a data error. Inherits: any claim in this packet family that repeats "4.7–5.4×" as a variance
  figure.
- **Rate-differential proxy for both FXC6 and FXR8 (DFF−IRSTCI, no better match in the provided files)**:
  source: claim says "銀行間金利差" without naming the exact series/tenor/timing convention. What the data
  show: two plausible interbank proxies (o/n call-rate diff, 3M TIBOR diff) both give R²≈0.48 and different
  (a,b) than claimed — the true source series/day-count is not identifiable from the files provided, so the
  formula's constants are not independently reproducible even though the qualitative shape is. Bias: unknown
  direction — could go either way depending on the true source series. Inherits: FXC6 directly, and FXR8's
  income leg (same proxy used), which is why the 33-vs-39 year-count gap and Sharpe-level gap (0.487 vs 0.535
  trend-gated) may both trace to this one unresolved input.
- **Monthly JP rate forward-filled to daily**: source: IRSTCI01JPM156N is monthly; no daily JP overnight-call
  series was in the provided files. What the data show: this creates within-month rate-differential staleness.
  Bias: shrinks measured income-return variance slightly (understates true income volatility), which would
  make the reported price/income variance ratio a slight *overstatement* of price dominance — doesn't change
  either verdict since the gap (30× vs claimed ~5×, or ~5.5× in std terms) is far larger than this effect.
  Inherits: any claim computing day-level Japan short-rate variation from this file.

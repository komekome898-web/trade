# Blind audit F — "magnitude not direction" law + RC1

Independent reimplementation from raw data only. No docs/, no research_*/fetch_*/judge_*
scripts, no KNOWLEDGE*.md, no git history were opened. Script: `audit_F.py` (scratchpad,
not committed).

## Files read
- `backtest_data/regime_composite_20260901/RC1_RUN.txt` (RUN file, permitted)
- `backtest_data/regime_composite_20260901/manifest.json`, `MD5SUMS`, `features_daily.csv`
- `backtest_data/regime_composite_20260901/raw/{gdelt_tone,binance_metrics,binance_funding,binance_premium}.csv` (headers)
- `data/attention/attention.csv`
- `data/binance_BTCUSDT_1d.csv` (header)
- `backtest_data/daily_btcusd_bitstamp_20260828.csv.gz`

## Q1. Denominator + recomputed IC
Daily direction target = `log(close_t+1/close_t)`; weekly = Monday→Monday non-overlapping
log return (n=191 OOS 2023-01-02..2026-08-31, n=103 exploration 2021-01-04..2022-12-26,
matches claimed n exactly once rolling-365 z-scores are built by ffill-tolerant history —
see note below). Magnitude target = `log(high_t+1/low_t+1)` (Bitstamp).

| line | feature | horizon | n | IC | naive t | NW t |
|---|---|---|---|---|---|---|
|1|wp_en (lag2)|1d|4077|+0.034|2.15|2.08|
|1|gdelt_vol|1d|3504|-0.028|-1.65|—|
|2|tone_7d_mean|1d|3505|-0.028|-1.67|-1.73|
|2|tone_7d_mean|1w(Mon)|500|-0.060|-1.34|—|
|3|toptrader_ls|1d|1753|-0.034|-1.44|-1.52|
|3|toptrader_ls|1w(Mon)|250|-0.091|-1.43|—|
|4|funding_3d_mean|1d|2434|-0.011|-0.56|-0.59|
|4|funding_3d_mean|1w(Mon)|347|+0.001|+0.02|—|
|RC1 composite|—|1w OOS|191|-0.090|-1.25|—|
|RC1 composite|—|1w explore|103|+0.0003|0.00|—|

**Note on RC1 reproduction**: a literal "365 rows all non-null" rolling window (as the RUN
file's prose implies) collapses to n=35 in the exploration window because one lone NaN in
`premium_1d` (2021-07-01) poisons the window for the following ~365 days. Forward-filling
isolated gaps before z-scoring reproduces the claimed n exactly (103 / 191). This is a
material ambiguity in the published method description, not just an audit artifact — flagged
under Q6.

## Q2. Controls
Shuffled-feature placebo (200 reps) centers on 0 with sd 0.015-0.024, consistent with the
small real ICs above being within noise for lines 2-4, borderline-outside for line1
(wp_en real IC 0.034 vs placebo 95th-pct |IC| 0.028-0.048 — mixed).
Reverse-causality check (feature vs *previous*-day return): tone -0.019, toptrader -0.046,
funding -0.014, wp_en(lag2) +0.035 — all comparable in size to the forward-looking ICs,
i.e. none of these features shows a forward-only signal cleanly separated from a
contemporaneous/backward-looking one. This is expected for price-adjacent series (funding,
premium, L/S ratios are mechanically linked to recent price) and is a caution against reading
even the small ICs above as causal "prediction."

## Q3. Translation
sd(weekly fwd ret) ≈ 6.68%. IC=0.05 → implied ≈0.33%/wk vs 0.06%/wk cost (>5x margin).
Break-even IC ≈ **0.009**. All lines' recomputed weekly ICs (|IC|≤0.09) are within an order
of magnitude of this break-even threshold — small IC ≠ automatically untradeable, which is
why RC1's t-stat (not sign) is the correct rejection criterion, as the RUN file uses.

## Q4. Relative vs absolute (attention → range amplification)
Split by trailing-20d realized-vol tercile, wp_en top-decile z vs rest, next-day range ratio:
low-vol +21.2%, mid-vol +26.6%, **high-vol +38.7%** — the "+38% in high-vol regime" figure
reproduces closely. But the control (top-decile of *prior day's own range*, no attention
condition, same high-vol tercile) gives **+52.5%**, a *larger* effect than the attention-based
split. So the amplification is not clearly attributable to attention specifically; simple
range/vol persistence explains at least as much of it. The magnitude effect is real but its
causal narrative ("attention amplifies") is not well separated from plain vol clustering.

## Q5. Rolling-365 vs 180
365-day warmup drops 365/4080 rows (8.9%) before any z-score exists. Rolling-180 z OOS:
IC=-0.051, t=-0.705 (n=191) — same sign, still non-significant; conclusion unchanged.

## Q6. Data validity
0 calendar gaps, 0 duplicate dates in `features_daily.csv`; `tone_7d_mean` has no exact-zero
holes; `attention.csv gdelt_vol` has 1 zero row. Holes-dropped vs ffilled for tone direction
IC: -0.0282/t=-1.67 vs -0.0282/t=-1.67 (no material difference — GDELT holes are rare here).
The one substantive data-hygiene issue found is the `premium_1d` single-NaN-poisons-a-year
rolling-window effect described under Q1.

## Q7. Selection / exploration vs OOS / best-feature upper bound
| component | EXPL IC (t) | OOS IC (t) |
|---|---|---|
|funding_3d_mean|+0.006 (0.06)|-0.012 (-0.16)|
|premium_1d|-0.002 (-0.02)|+0.042 (0.57)|
|ls_ratio|+0.014 (0.09)|-0.014 (-0.19)|
|toptrader_ls|+0.024 (0.06)|-0.057 (-0.78)|
|tone_7d_mean|-0.049 (-0.50)|+0.088 (1.21)|
|ret_28d|+0.046 (0.47)|+0.107 (1.48)|

No component's OOS sign reliably tracks its exploration sign (only 2/6 same-sign, weak
evidence of anything beyond noise in exploration). Best-possible single-feature OOS |IC|
(post-hoc upper bound of what a mined result could show) = **0.107** (`ret_28d`, t=1.48) —
below the conventional |t|≥2 bar even when cherry-picking the best of six after the fact.

## Q8. Magnitude vs pure range autocorrelation (incremental R²)
R²(lag-range only) ≈ 0.13-0.19 baseline. Adding |feature|: tone +0.009, toptrader +0.005,
funding +0.034, wp_en(lag2) **+0.047** (largest). Lagged range alone already explains most
of next-day range; attention/features add modest but non-trivial increments — "magnitude is
predictable" is mostly (not solely) volatility clustering, consistent with the law's own
framing that attention amplifies an *already-high-vol* regime rather than acting alone.

## Q9. Consistency across lines/horizons
At 1d and 1w, all 4 lines' direction |t| stay below 2 except line1 (wp_en, t≈2.1-2.2,
borderline) — mostly consistent with "no direction signal." At **28d** (out-of-scope horizon,
overlapping windows, reported here only as a robustness probe with NW-adjusted t at 28 lags):
tone_7d_mean NW-t = **-2.08** (borderline breach), toptrader_ls NW-t=-1.62, funding NW-t=-0.71,
wp_en naive/NW t≈2.1-2.9. So the "no line ever hits |t|≥2" claim is not perfectly clean once a
longer, unaudited horizon is probed — flagged as a minor exception, not a reversal (effects
stay economically small, ≤0.15 IC, and multiple-horizon testing itself inflates false
positives).

## Q10. Falsification & power
Falsification sentence (implied by the record): "if any of the 4 lines had shown |IC|≥MDE
with |t|≥2 in its pre-specified OOS window/horizon, or RC1's OOS composite IC had cleared
t≥2.0 with ≥4/6 components sign-consistent, the law/RC1 would be rejected." MDE for
|IC|=0 null at α=0.05: n≈190 (weekly) → **≈0.143**; n≈1,300 (daily) → **≈0.054**. RC1 (n=191)
is powered only to detect fairly large weekly ICs (~0.14+); its own recomputed IC (-0.09) and
the claimed one (-0.073) are both well under this MDE, so "no significant direction signal
found" is the correct read but should not be over-read as "proven zero" — the study is
underpowered for anything smaller than a ~0.14 weekly IC.

## Verdict

**LAW**: 数値差異(結論維持). Direction-IC≈0 across lines 2-4 reproduces cleanly; line1
(attention pageviews) shows a small but recomputed borderline-significant positive daily IC
(≈0.03, NW-t≈2.1) not perfectly "IC≈0," though far below tradability after realistic frictions
and multiple-testing correction. The headline amplification number (+38% in high-vol regime)
reproduces numerically but is not cleanly separable from ordinary volatility-clustering
(control effect is larger, +52.5%), so the causal "attention" framing is weaker than the law's
wording suggests even though the magnitude-predictability conclusion itself stands.

**RC1**: 再現. Independent reimplementation (once a defensible gap-handling choice is made
for the 365-day rolling z, since the RUN file's prose is ambiguous on this point) reproduces
the claimed sample sizes exactly (103 / 191) and the OOS composite IC's sign, order of
magnitude, and non-significance (recomputed -0.090 vs claimed -0.073, both |t|<2, both fail
the t≥2 pre-registered bar). Exploration-window IC is near zero in both versions (claimed
+0.020, recomputed +0.0003) — no informative feasibility signal there, and per-component
exploration→OOS sign persistence is weak (2/6), consistent with the "no adoption" conclusion.

| item | claimed | recomputed |
|---|---|---|
|RC1 explore IC (n, t)|+0.0203 (103, 0.204)|+0.0003 (103, 0.003)|
|RC1 OOS IC (n, t)|-0.0728 (191, -1.003)|-0.0903 (191, -1.247)|
|RC1 OOS Q5-Q1|-0.66%/wk|-1.67%/wk|
|Line1 direction IC (1d)|≈0 (claimed)|+0.034 (t≈2.1)|
|Line2 direction IC (1d)|≈0|-0.028 (t≈-1.7)|
|Line3 direction IC (1d)|≈0|-0.034 (t≈-1.4)|
|Line4 direction IC (1d)|≈0|-0.011 (t≈-0.6)|
|High-vol amplification|+38%|+38.7% (but control alone: +52.5%)|

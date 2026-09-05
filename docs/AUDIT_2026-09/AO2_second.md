# AO — second (blind) audit

Files read: `docs/AUDIT_2026-09/PROTOCOL.md`; `docs/AUDIT_2026-09/00_packets.md` (rows `AO`, `JPR9`, `SV5` only,
via grep); `backtest_data/yutai_20260904/manifest.md`; `backtest_data/yutai_20260904/universe.csv`;
`backtest_data/yutai_20260904/px.tar.gz` (extracted, all 902 per-ticker CSVs incl. `IDX_N225.csv`);
`config/constants.yaml` (jpx_cash_equity fee block). Attempted `WebFetch` on minkabu.jp and kabuyutai.com
(both blocked by this session's own egress proxy — not informative either way). Own script:
`audit_AO2.py` in the scratchpad. No forbidden file was opened.

Method: close-to-close returns, index of trading day within each ticker's own file (not calendar dates), event
day D0 = the date Yahoo's `events=div` keys the dividend row on (ex-div day). "権利付き最終日" = D-1. Both raw
and Nikkei-225-price-return-adjusted ("idx-adj", i.e. abnormal return = stock return − N225 return same day)
versions computed, since raw D0 return is dominated by the mechanical price drop (~-176bps, not an anomaly)
and cannot itself be the claimed -3.8bps.

## JPR9

Claim: "権利付き最終日 −3.8bps t=−2.1。10日ランアップ2015-19 +74bps → 2020-26 D−5脚 −38bps t=−7.6."

| metric | claimed | recomputed (idx-adj) | n (mine) |
|---|---|---|---|
| D-1 return, pooled | −3.8bps, t=−2.1 | 2015-19: −12.6bps t=−3.9; 2020-26: −9.1bps t=−3.3 (pooled ≈ −10.4bps) | 3,288 / 5,051 |
| 10-day run-up 2015-19 | +74bps | +57.1bps, t=5.18 | 2,760 |
| D-5 leg 2020-26 (D-5..D-1) | −38bps, t=−7.6 | −33.6bps, t=−5.84 | 5,051 |
| event count perk / control | 8,159 / 4,781 | 8,571 / 5,027 (strict D-10..D+10 window) | 575 / 300 unique tickers |

Denominator (Q1): perk universe is 600 tickers per manifest (biased top-yield sample, not random — stated in
manifest itself), 300 non-perk control filtered to dividend-payers with ≥4 ex-div events and price in the
perk sample's p2-p98 range. My strict window (needs D-10..D+10 all present) keeps 575/300 unique tickers and
8,571/5,027 events, ~5% above the claimed 8,159/4,781 — a plausible but unverified difference in exact
window/edge rules (see 前提の誤り).

Sign and rough magnitude of all three headline numbers reproduce once returns are benchmarked against N225 —
a raw (non-index-adjusted) implementation gives the *opposite* sign for D-1 (+41bps, not negative) and no
reversal at all in the D-5 leg (+113bps in 2020-26, not −38bps), so the claim's numbers are only reproducible
under an abnormal-return definition that is not stated in any file I was allowed to read. Given that
assumption, magnitudes are same-sign but off by 2.5-3x (D-1) to ~15-25% (run-up, D-5 leg) and t-stats are
larger (more significant) than claimed in every case, not smaller — recomputation does not shrink the effect,
it deepens the run-up/reversal legs and roughly triples the D-1 effect. Controls (§Q2, Q8): a placebo (random
non-event day, perk tickers) gives +1.2bps t=0.20 — clean null, as expected. A permutation test shuffling the
era label on run-up returns rejects the null of "no era difference" at p<0.002/500 draws, so the 2015-19 vs
2020-26 shift is not noise. Crucially, the **same D-5 reversal pattern also appears in the non-perk control
group** in 2020-26 (idx-adj −16.4bps, t=−1.93 — same sign, roughly half the perk magnitude, weaker
significance) and the **same positive run-up appears in control in 2015-19** (+50.8bps, t=5.61, matching
perk's +43.1bps for that same leg-window). This is consistent with the claim's own framing (its title is
"優待・配当", not perk-exclusive) but means the run-up/reversal legs are largely a general ex-dividend
seasonality effect, not something specific to shareholder-perk stocks; only the **D-1 pre-event weakness**
looks perk-differentiated (control ≈ 0 to +5bps vs perk ≈ −9 to −13bps in both eras).

Verdict: 数値差異(結論維持)

## SV5

Claim: primary-source survey identifying YT1's direct data source (perk list + prices).

The manifest documents exactly the chain the claim implies: minkabu.jp/yutai (first-choice source) returned
only ~31 tickers from a homepage widget before an AWS-WAF-style 403 blocked further access; kabuyutai.com's
undocumented screener endpoint (`tool/shiborikomi/`, 86 pages × 20/page = 1,720 raw rows, reconciled to 1,715
unique) supplied the actual 1,463-ticker intersection with the JPX prime/standard listed-issues file, capped
to 600 by the site's own default sort (highest combined 優待+配当利回り) — an explicitly non-random,
popularity/yield-biased sample. Control (300) construction and its 729/900-fetched, 631/300-passed funnel is
also documented with concrete counts that are internally consistent (729 attempted, 631 passing the
dividend-count + price-range filter, capped at 300). I could not independently re-crawl minkabu.jp or
kabuyutai.com — both are blocked by this audit session's own network egress proxy — so I cannot confirm
today whether either site's current state matches what the manifest describes; I can only confirm the
manifest's internal arithmetic is self-consistent and that the resulting universe.csv/px.tar.gz match its
stated row/file counts exactly (900 universe rows, 900 matching per-ticker CSVs + 1 index file found).

Verdict: 再現

## 前提の誤り

1. **Abnormal-return definition unstated.** JPR9's headline bps figures are only reproducible (same sign,
   same order of magnitude) under an index-subtracted (N225 price-return) abnormal-return definition; raw
   close-to-close returns give the wrong sign for D-1 and show no D-5 reversal at all. No file I was permitted
   to read (manifest, config, universe/px data) states this methodology — it must live in the forbidden
   `scripts/research_yutai.py` or `docs/SURVEY_JP_YUTAI.md`. Direction of bias: none on my verdict (I assumed
   the benchmark-adjusted definition and it fits far better), but it means the claim as filed is
   under-specified from data alone — any other claim citing "the same event-day return" without stating the
   benchmark inherits this gap.
2. **Event count denominator (8,159/4,781) not exactly reproducible.** My strict D-10..D+10 window gives
   8,571/5,027 (+5.0%/+5.1%). Likely a different edge-inclusion or minimum-history rule; direction of bias
   unclear (my larger n slightly narrows confidence intervals vs. the claim's). Any other claim quoting these
   exact denominators inherits the same ~5% uncertainty.
3. **Perk flag is static/retroactive (manifest's own caveat).** 2026-09 perk roster applied to the full
   2015-2026 history; a ticker that added/dropped its yutai program mid-sample is misclassified for part of
   its events. Direction of bias: dilutes the perk-vs-control contrast (mislabeled perk events behave like
   control, and vice versa), so true perk-specific effects (if any) are understated, not overstated. Inherited
   by SV5's downstream users and any claim treating "perk_flag" as time-accurate.
4. **Perk universe is non-random (top-600 by combined yield, per manifest).** Any generalization from JPR9 to
   "yutai stocks in general" overstates external validity; the sample is biased toward higher-yield, more
   liquid/popular names. Inherits into any claim that extrapolates YT1's effect size to the full ~1,463-name
   kabuyutai universe.
5. **t-stats (mine and, very likely, the claim's) treat events as independent**, but many perk tickers share
   fiscal year-end dates (March/September dominate japan), so a large fraction of "events" fall on the same
   handful of calendar days and share the same-day N225 move and market-wide flow — this inflates effective n
   and overstates significance for every t-stat in both this report and JPR9. Direction of bias: significance
   is overstated (t too large) throughout; this does not change the sign of any headline number here but means
   none of the quoted t-values should be read as literally as ~5,000 independent draws would imply.
6. **Cost/translation (Q3):** `config/constants.yaml: jpx_cash_equity.sor_commission_yen = 0` (SOR orders,
   effective 2026-05-18) — but that free-commission regime covers only the last few months of a 2015-2026
   sample; for most of the window the applicable cost was `non_sor_fee_yen_by_notional` (55-275 JPY/trade) or
   an unknown pre-2026 broker fee schedule not in this repo. At −3.8 to −13bps on a 1,000,000 JPY clip
   (−380 to −1,300 JPY), a flat 275 JPY non-SOR fee alone consumes a large fraction of the D-1 effect and
   nothing here estimates bid-ask spread, which is not in this OHLCV-only dataset — any translation of this
   seasonality into JPY/day P&L is currently unconstrained by real transaction-cost data for most of the
   sample period.

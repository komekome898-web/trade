# Blind audit A: N225 futures overnight (day-close -> next day-open) premium

Independent re-derivation. Own script only: `/tmp/.../scratchpad/audit_A.py` (not committed).
Files read: `backtest_data/n225f_225labo_20260828/{manifest.json,MD5SUMS,day_session_daily.csv.gz,
night_session_daily.csv.gz,full_day_daily.csv.gz,trading_day_daily.csv.gz,bars_1min.csv.gz}`,
plus live fetch of `^N225` daily OHLC from Yahoo chart API (period1=1989-12-01, period2=2026-09-04).
No file under `docs/`, no `scripts/research_*`, `scripts/judge_*`, `scripts/paper_*`, `KNOWLEDGE*.md`,
and no git history were opened. MD5SUMS verified OK for all 5 data files.

## 1. Denominator
`day_session_daily.csv.gz`: 9038 rows, 1990-01-04..2026-08-27, day-session (08:45 open auction /
15:45 close auction). Series is 225Labo's single continuous roll (manifest: "continuous series as
provided"); no per-contract labels are present in the file, so the roll methodology cannot itself
be audited from this snapshot — treated as given. 0 duplicate dates, 0 weekend rows, 11 gaps >6
calendar days (largest: 2019 Golden Week, flagged genuine in manifest). r_t = ln(open(t+1)/close(t))
gives 9037 pairs (last row has no next open).

Full window: **mean = 3.8016 bps/day, t = 3.418** (claim: +3.80bps, t=+3.42 — matches to 3 sig figs).
My own moving-block bootstrap (block=20 days, B=2000): 95% CI = **[1.74, 5.89] bps**, lower bound > 0
(claim: CI lower bound > 0 — confirmed, though my exact bounds weren't stated in the claim to check
against).

4-era table (own recompute):
| era | n | mean bps | t |
|---|---|---|---|
| 1990-1998 | 2214 | 3.379 | 1.782 |
| 1999-2007 | 2214 | 4.684 | 2.407 |
| 2008-2016 | 2204 | 2.829 | 1.006 |
| 2017-2026 | 2405 | 4.270 | 1.996 |

All 4 means positive, matching claim. Note: 2008-2016 is not individually significant (t=1.0) —
claim only asserted "all positive," which holds, but a reader should not infer all-eras-significant.

Cost-adjusted (1.10 bps/day round trip subtracted): mean = 2.702 bps, t = 2.429 (claim: +2.70bps,
t=+2.43 — matches).

## 2. Controls
- (i) Shuffle (permute the r_t values themselves): mean unchanged (3.80bps, t=3.418) — expected,
  since permutation doesn't change the mean of iid-order-invariant statistic; not a real null test.
- (i') Stronger placebo — pair close(t) with a *randomly chosen* other day's next-open instead of
  the true t+1 open: mean = 3.80bps but **t = 0.058** (not significant). This is the correct
  falsification control: the true (close→next-open) pairing is what carries the signal; a random
  pairing across the same marginal distribution of prices does not. Consistent with the claim.
- (ii) Day-session open→close (intraday): mean = **-3.233 bps**, t = -2.857, n=9038 — negative,
  significant, opposite sign, as the claim implies (intraday roughly cancels overnight).
- (iii) Close→close (day close to next day close = intraday + overnight combined): mean = 0.582
  bps, t = 0.363 — small and insignificant, and arithmetically consistent (-3.233 + 3.802 ≈ 0.58,
  self-consistency check passes).
- Era split of intraday open→close: 1990-98 t=-3.14, 1999-2007 t=-1.87, 2008-2015 t=-0.32,
  2016-2026 t=-0.01. Direction matches claim ("1990-2015 significantly negative, recent ~zero") but
  2008-2015 alone is *not* individually significant (t=-0.32) — claim's "1990-2015 有意に負" is a
  slight overstatement for the back half of that span; magnitude decay to ~0 by 2016+ is confirmed.

## 3. Yen translation
Micro Nikkei ×10 yen/point. At last close (66150): gross = 66150 × 0.000380 × 10 = **251.5 yen/day**;
net of 22 yen round-trip cost = **229.5 yen/day**. At the sample-average index level (19595, since
the index ran from ~39000 in 1990 down to ~7000 in 2008 up to 66000 now): gross = 74.5 yen/day, net
= 52.5 yen/day. Either way net > 0 after the given 22-yen cost; the yen figure is highly
index-level-dependent (bps is scale-free but naive yen/day is not) — the claim's bps framing is the
right one for cross-era comparison.

## 4. Volatility regime
Trailing 20-day realized vol terciles (own tercile cut), full window:
| tercile | n | mean bps | t |
|---|---|---|---|
| low | 3006 | 1.535 | 1.208 |
| mid | 3005 | 3.492 | 2.119 |
| high | 3006 | 6.408 | 2.450 |

Effect is monotonically increasing in realized vol and is *not* significant in the low-vol tercile
alone (t=1.21). This is an important caveat the claim does not mention: the average premium is
materially concentrated in higher-vol periods (era×tercile table confirms this pattern repeats
within every one of the 4 eras, e.g. 2017-2026 high-vol tercile mean=11.07bps vs low-vol 1.22bps).

## 5. Auction-print validation
Checked 170 overlapping days in `bars_1min.csv.gz` (2025-12-30..2026-08-28) against
`day_session_daily`: 08:45 first-bar open matches file's day-session open in **170/170 (100%)**;
15:45 last-bar close matches file's day-session close in **170/170 (100%)**. Definition holds
exactly for the sample that can be checked (manifest also states 170/170 independently).

## 6. Data validity / outliers
0 duplicate dates, 0 weekend rows (matches manifest's `ohlc_integrity_bad_rows: 0`). 3 rows with
|r| > 10% (extreme overnight gaps — plausible for 36 years incl. 2008/2011/2020 shocks). Clipping
|r| to ±5%: mean = 3.897 bps, t = 3.700 — result is *not* driven by a handful of extreme days;
clipping if anything strengthens the stat slightly. Top-20 |r| days average -94.8bps (net negative,
i.e. crash days pull the mean *down*); excluding them mean rises to 4.020bps — so the claim's
positive premium is not an artifact of a few outlier days, it's slightly damped by them.

## 7. Free parameters
None in the core headline stat (mean/t of r_t over the full stated window — a fixed, pre-specified
definition). Free choices that *do* exist in the surrounding claim: the 4-era cut points (round
9-year bins — arbitrary but not cherry-picked post hoc against the result, since all 4 bins are
positive regardless of exact boundary, confirmed by my leave-one-era-out check below), the 1.10bps
cost constant (stated as "conservative", sourced from the claim itself, not independently audited
here), and the block-bootstrap block length (I used 20; not swept).

## 8. Alternative explanations
(a) General equity-premium-spread-evenly: half of close→close = 0.291 bps vs. actual overnight mean
3.80 bps — the overnight effect is **13x larger** than a naive "half the daily drift" story; not
explained by a generic equity risk premium spread evenly across the 24h day.
(b) Crisis days: excluding the 20 largest |r| days *increases* the mean (4.02 vs 3.80bps) — not
explained by a few crisis days; if anything they are a drag.
(c) Single decade: leave-one-era-out means: excl.1990-98→3.94(t=2.94); excl.1999-2007→3.52(t=2.64);
excl.2008-16→4.12(t=3.55); excl.2017-26→3.63(t=2.79). Removing any one era leaves the effect
positive and significant — not a single-decade artifact.

## 9. Cross-instrument consistency
Cash ^N225 (Yahoo, 9288 daily rows, own live fetch): overnight r on 8985 matched dates: futures ON
mean = 3.742 bps, cash ON mean = 3.794 bps. Shrink ratio (futures ÷ cash) = **0.986** (claim: 0.99 —
matches closely; note the claim's ratio direction is futures÷cash, and cash "open" from Yahoo is a
9:00 proxy, not necessarily the itayose print — treat as approximate).
Night-session file (2007-2026): mean = 2.226 bps, t=1.822, n=4674 (own open→close of the night
session). Naive same-date merge with r_t gave corr=-0.098, which is a **date-alignment artifact** —
the night file's date labels the session using the *following* trading day (a row dated D covers
the evening starting D-1, matching the bars_1min manifest note). After correcting the alignment
(matching night(D) to r_t(D-1)), corr = **0.774** (n=3641), and restricting r_t to 2007-2026 gives
overnight mean 3.361bps vs night-session-alone mean 2.226bps (~66% of the overnight magnitude sits
inside the night session proper). This is directionally consistent with "night session is the main
driver" but the claim's phrasing overstates precision — a meaningful minority of the overnight
return sits in the pre-night and post-night gap windows, not the night session itself.

## 10. Falsification
If, over the next 12 months, the equal-weighted mean of ln(open(t+1)/close(t)) on this series turns
non-positive (or its lower 95% block-bootstrap CI in a rolling 250-day window is comfortably below
zero) while the day-session-only strategy does not show a compensating equal-and-opposite move, the
claim would be falsified for the live regime.

## Verdict
**再現 (reproduced)** — mean, t, era signs, cost-adjusted figure, shrink ratio, and the auction-match
rate all reproduce to the stated precision with an independent implementation. Caveats worth
attaching to future citation: (1) the effect is concentrated in higher realized-vol regimes and is
not significant in the low-vol tercile; (2) the "1990-2015 significantly negative" intraday claim is
not individually significant in the 2008-2015 sub-slice; (3) the night-session "main driver" claim
needed a date-alignment fix to verify and even then only explains ~2/3 of the post-2007 overnight
magnitude by simple share, ~0.77 by correlation; (4) roll/contract-change methodology inside the
225Labo continuous series could not be audited from this snapshot alone.

| stat | claimed | recomputed |
|---|---|---|
| full-window mean | +3.80 bps | +3.802 bps |
| full-window t | +3.42 | +3.418 |
| 4 eras all mean>0 | yes | yes (3.38/4.68/2.83/4.27) |
| cost-adj mean/t | +2.70bps / t=2.43 | +2.702bps / t=2.429 |
| shrink ratio (fut/cash) | 0.99 | 0.986 |
| intraday 1990-2015 sig. negative | yes | mostly (2008-15 sub-slice t=-0.32) |
| night session = main source | qualitative | ~66% of magnitude, corr=0.77 (post-alignment-fix) |

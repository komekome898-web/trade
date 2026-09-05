# Packet H — second (blind) audit

Independent re-derivation from `backtest_data/reit_onr_20260904/` (etf_1321_daily.csv,
etf_1343_daily.csv, etf_1343_dividends.csv, reit_index_daily.csv, MD5SUMS, manifest.md)
and `config/constants.yaml`. Script: `audit_H2.py` (scratchpad). Files read: the four
data files above + their MD5SUMS + manifest.md (allowed, not a report/PREREG), and
`config/constants.yaml`. I did **not** open `ONR_RUN.txt` (forbidden `*_RUN.txt` in a
snapshot dir) or any `docs/AUDIT_2026-09/H_*.md`.

**Coverage gap (applies to all 5 claims):** the packet itself flags "partial" — only two
ETFs were ever snapshotted: `1321` (Nikkei 225-linked ETF, proxy for "N225") and `1343`
(TOPIX REIT ETF, proxy for "J-REIT"). TOPIX ETF, JPX400 ETF, Growth250 ETF, any
leveraged ETF (RB1), any US-stock cross-listed ETF (UO1), and TOPIX Core30 ETF `1311`
were never fetched — no files exist for them anywhere under `backtest_data/` or `data/`.

## JPL6

Claim: overnight (close→next-open) premium is positive across N225/TOPIX/JPX400/
Growth250/J-REIT ETFs (5 series).

Denominator: only 2/5 named series have data. `1321`: n=4083 overnight obs, 2009-01-06..
2026-09-03 (255 zero-open glitch rows dropped, 0 dropped as |r|>10%). `1343`: n=4399,
2008-09-17..2026-09-03 (4 zero-open rows dropped, 5 dropped as |r|>10% one-time listing
artifacts).

Recomputed (ln(open_t/close_{t-1})):
| series | n | mean (bps) | t | pos share |
|---|---|---|---|---|
| 1321 (N225 proxy) | 4083 | +5.18 | 3.21 | 52.4% |
| 1343 (REIT proxy) | 4399 | +4.71 | 3.65 | 51.7% |

Both signs match the claim for the 2 testable legs. Controls: sign-reversed flips
correctly (t=-3.21/-3.65). Placebo (randomly relabeling which half-day is "overnight" vs
"intraday" per name, pairwise) collapses the effect (t=0.14/0.85, mean ~0-1bp) — not a
shuffling artifact. By-era split: sign stays positive every sub-period for both series but
significance is weak/absent early (1321 2008-11 t=0.12; 1343 2008-11 t=0.86, 2012-16
t=1.15), strengthening only from ~2017 (1343 2022-26 t=5.95). Vol-tercile split (prior-day
range/close proxy) concentrates the effect in the high-vol tercile (1321 high t=2.67 vs
low t=1.82; 1343 high t=3.30 vs low t=0.39 n.s.) — regime-conditional, not a flat level
(Q4). Ex-dividend check on 1343 (55 ex-dates, 36 land on a modeled overnight date): mean
on ex-div opens is *more* positive (+10.42bps, n=36) than off (+4.67bps); excluding ex-div
dates barely moves the matched-window mean (4.42→4.37bps) — not a material confound
(Q5/Q6), contrary to expectation going in.

Money translation (Q3): last close 1321=¥66,480, 1343=¥1,923.5 (2026-09-03); 60-session
avg turnover ≈¥26.4bn (1321) / ¥1.8bn (1343). 5.18bps of 66,480≈¥34/unit/night; 4.71bps of
1,923.5≈¥0.9/unit/night. `config/constants.yaml: jpx_cash_equity.etf_spread_bps` is
`value: null` — "do not use a value here until measured" — so gross bps cannot be netted
of a real spread from this repo; `sor_commission_yen: 0` only applies if the order type
qualifies for SOR, which the packet's own manifest calls unresolved ("leaning toward does
NOT qualify"). Gross premium only, no net-of-cost number is derivable.

MDE (Q10): sd≈85-105bps, n≈4,000-4,400 → SE≈1.3-1.6bps → MDE (80% power)≈3.7-4.6bps.
Observed effects (4.7/5.2bps) clear this floor narrowly for the full sample; the low-vol
subsample does not clear it at all.

Verdict: 再計算不能

(2 of the 5 named series reproduce a same-signed, mostly-significant premium; the other
3 legs — TOPIX/JPX400/Growth250 — have zero data anywhere in the repo, so the claim's
actual headline, "cross-market, all five," cannot be confirmed or denied as stated.)

## JPL7

Claim: thin-ETF overnight premium is a fill/execution artifact, sized via 1311 (TOPIX
Core30 ETF) at ¥0.3bn/day turnover. No `1311` file exists anywhere under `backtest_data/`
or `data/` (checked by directory listing + filename search). `1321`/`1343` cannot proxy
for it (60-session turnover ¥26.4bn/¥1.8bn, 6-88x the claimed ¥0.3bn/day — a different
liquidity regime), and no tick/fill data exists for any JPX ETF, so the artifact mechanism
itself is not testable from what's on disk.

Missing: `1311` daily and any fill/tick data for it; no proxy in the repo covers this.

Verdict: 再計算不能

## JPR6

Claim: leveraged-ETF (RB1) pre-close rebalancing chase — no trace in 2026, 1-minute bars,
170 days, all momentum cells ≈-1bp, t≈0. No individual-ETF minute-bar file exists for any
ETF, leveraged or not, in `backtest_data/` — only the two daily files (1321, 1343). This
is specifically a null result derived from 1-minute intraday data unavailable here.

Missing: leveraged-ETF 1-minute OHLC for the stated 170-day window.

Verdict: 再計算不能

## JPR7

Claim: Tokyo-session time-of-day decomposition (UO1, a US-stock cross-listed ETF) — the
earlier time-band finding was mis-attributed; the Tokyo-daytime negative effect
concentrates in the listing's first year. No file for any US-stock cross-listed JPX ETF,
and no minute-level Tokyo-session data, exists in the repo. 1321/1343 are not relevant
substitutes (different asset class; both listed too long ago for a first-year question).

Missing: UO1-class ticker file, its minute bars, and its listing-date cohort split.

Verdict: 再計算不能

## JPR8

Claim: TOPIX Core30 ETF `1311` overnight premium is a thin-market execution artifact,
turnover ≈¥0.3bn/day. Same gap as JPL7 — `1311` is the claim's own subject and has zero
daily or intraday files anywhere in the repo; 1321/1343 turnover is 6-88x too large to
stand in as a liquidity proxy for it.

Missing: `1311` OHLCV entirely; cannot even establish the ¥0.3bn/day turnover figure
independently, let alone the return artifact behind it.

Verdict: 再計算不能

## 前提の誤り

- premise: "night premium is confirmed market-wide across 5 index families" (JPL6) |
  source in claim: 第40報 headline | what the data shows: only 2/5 named ETFs were ever
  fetched into the repo (1321, 1343); TOPIX/JPX400/Growth250 ETF files do not exist |
  direction of bias: the claim's *breadth* is unverifiable and likely overstated relative
  to what was actually measured; the 2 tested legs are directionally consistent but that
  is 40% coverage, not "全て" | other claims inheriting this: any downstream sizing/
  portfolio claim that assumes the effect applies uniformly across all 5 JPX ETF families.
- premise: implicit in JPL6/JPL7/JPR8 that a bps premium can be judged "worth trading" |
  source in claim: 第40報's cost framing | what the data shows: `config/constants.yaml
  jpx_cash_equity.etf_spread_bps` is `null` with an explicit "do not use a value here
  until measured" note — no real ETF bid-ask spread constant exists in this repo |
  direction of bias: any net-of-cost conclusion in the underlying report used either an
  unstated/assumed spread or none at all, so the true net economics are unknown and could
  easily be negative once a real spread is measured | other claims inheriting this: every
  claim in this packet that translates an overnight bps number into money, and by
  mechanism any other JPX-ETF strategy claim that nets a raw bps edge against an assumed
  (rather than measured) spread.
- premise: 1311/RB1(leveraged)/UO1 turnover and behavior figures cited in JPL7/JPR6/JPR7/
  JPR8 | source in claim: 第40報 body text | what the data shows: none of these
  instruments have any snapshot (daily or intraday) anywhere in the repo, so the specific
  turnover figure (¥0.3bn/day for 1311) and the "no rebalancing trace" / "first-year
  concentration" findings rest on data this auditor cannot see and therefore cannot
  confirm exists in the form claimed | direction of bias: unknown (could not check) |
  other claims inheriting this: any claim mechanism citing thin-ETF fill artifacts or
  leveraged-product rebalancing without an accompanying data snapshot in this repo.
- premise: overnight premium is a stable level, uniform across the sample | source in
  claim: implicit framing of JPL6 as a standing structural effect | what the data shows:
  vol-tercile split on both available series shows the effect is concentrated in the
  high-volatility tercile (1321: high t=2.67 vs low t=1.82; 1343: high t=3.30 vs low
  t=0.39, not significant) and by-era splits show near-zero significance pre-2012 |
  direction of bias: overstates how uniformly-tradeable the edge is; a strategy sized
  off the full-sample mean would be relying disproportionately on high-vol/recent-regime
  days | other claims inheriting this: any sizing or capacity claim built on the
  full-sample mean bps rather than a regime-conditional one.

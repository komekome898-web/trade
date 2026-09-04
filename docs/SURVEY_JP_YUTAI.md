# SURVEY — 株主優待/配当 権利落ち seasonality, cash-long only (2026-09-04)

Exploratory SURVEY, not a judgment. No PREREG; no strategy or parameters proposed here.
Script: `scripts/research_yutai.py` (deterministic, reads the frozen snapshot).
Snapshot: `backtest_data/yutai_20260904/` (`universe.csv`, `px.tar.gz`, `manifest.md`).
Scope: cash-long, 100-share unit, 0-commission auction orders only (owner constraint) —
no short leg is evaluated anywhere below.

## 1. Sources

- **Universe**: official JPX listed-issues file (`data_j.xlsx` — now `.xlsx`, the
  `.xls` URL in the task 404s; corrected). プライム+スタンダード（内国株式）= 3,111 names.
- **Perk list**: minkabu.jp/yutai (first choice) gave one usable page (~31 tickers,
  a homepage ranking widget) then went behind an AWS-WAF 403 for the rest of the
  session (`/yutai/popular_ranking/*`, `/stock/search` too) — **not used for the
  bulk list**. kabuyutai.com's screener tool (`tool/shiborikomi/`, found via site
  nav; its `../api/search/` JSON endpoint backs a paginated, sortable table)
  supplied the full list instead: 86 pages x 20/page = **1,715 unique perk
  stocks** with code, name, 権利確定月, required investment, 優待利回り, 配当利回り.
  96ut.com and kabuyutai's `/kobetu/<slug>.html` pages were reachable but not
  code-addressable in bulk; shikiho.toyokeizai.net/yutai is a client-rendered SPA;
  buffett-code.com/yutai and finance.yahoo.co.jp/stock/yutai 404/403'd outright.
- **Prices + dividends**: Yahoo Finance chart API, daily OHLC + `events=div`
  (ex-dividend date keyed, JPY/share), 2015-01-01..2026-09-04, incl. `^N225`.
  0 fetch failures on the 600-name perk sample; the 900-name control candidate
  pool was cut short at 729/900 fetched by a session time budget (see §2) — the
  300-name control target was still reached after filtering (see manifest).

## 2. Universe & coverage

kabuyutai list (1,715) ∩ JPX prime/standard universe (3,111) = **1,463** perk
stocks. Capped to **top 600 by kabuyutai's default sort** (combined 優待+配当利回り
desc) — **not a random sample**: skews toward higher-yield, more "popular" perk
names, which is defensible for a popularity-style survey but is a selection bias,
not a clean cross-section of all 1,463. Control: 300 non-perk, dividend-paying
(≥4 ex-div events 2015-2026), same universe, median-close price matched to the
perk sample's p2-p98 range (¥161-4,759), from 631 filter-passing names out of a
729-ticker fetch (900 attempted; fetch cut short, did not bind — see manifest §3).

Events = every Yahoo-reported ex-dividend date per ticker, 2015-2026, with a full
±10-trading-day window available: **perk 8,159 events / non-perk 4,781 events**
(≈13.6 / 15.9 events per ticker — most pay 2x/year, 11.5 years). 24 tickers had
no dividend in-sample; 728 event-windows fell too close to the sample edges.

## 3. Caveats (read before the tables)

- **Perk flag is time-invariant at today's roster.** A stock's 2015 perk status is
  inferred from its 2026-09 kabuyutai listing — perks added or dropped mid-sample
  are misclassified for the years on the wrong side of the change. No
  point-in-time perk-history source was found.
- **No survivorship exclusion in construction** (every ticker is currently
  listed, no "series stopped" filter) — but this *is* survivorship at the
  population level: perk/dividend stocks that delisted or dropped their
  program before 2026-09 are invisible here, in both arms.
- **Overlapping event days.** Japanese fiscal year-ends cluster hard on 3月末/9月末
  (ex-dates a few trading days earlier) — a large share of events share the same
  handful of calendar dates each year, so observations are not cross-sectionally
  independent; the t-stats below are inflated vs. a true independent-event count.
- **Perk-list selection bias** (§2): top-600-by-yield, not random — read "perk"
  results as "popular/high-yield perk stocks," not the full 1,463.
- Dividend amounts from Yahoo are back-adjusted for later stock splits (a few
  large-cap pre-split events may have a small dividend/price scale mismatch in
  the ex-drop legs). Not corrected for.

## 4. Results (market-adjusted log returns vs ^N225, same calendar day; bps)

Legs: run-up 10d/5d → close(D-1) · final-day auction (the tradeable closing-order
leg, open(D-1)→close(D-1)) · ex-drop raw & dividend-adjusted ("excess drop" —
positive = price fell *less* than the dividend) · post open(D)→close(D) ·
post +5d/+10d (does the excess drop recover).

```
[PERK    pooled     ] n=8159  runup10 +27.4 t=4.41 | runup5 -10.2 t=-2.57 | finalauct  -3.8 t=-2.06 | exdrop_raw -161.5 t=-57.3 win20% | exdrop_adj  -24.8 t=-9.29 win55% | post_oc +12.8 t=5.97 | +5d  -62.1 t=-12.3 | +10d -111.4 t=-16.0
[NONPERK pooled     ] n=4781  runup10 +31.0 t=3.75 | runup5  +4.9 t=0.94 | finalauct  +0.0 t=0.01 | exdrop_raw  -97.8 t=-33.2 win28% | exdrop_adj  +73.1 t=27.55 win75% | post_oc +14.7 t=5.13 | +5d  -64.3 t=-9.65 | +10d -116.0 t=-13.2

[PERK    2015-2019  ] n=3108  runup10 +74.3 t=7.60 | runup5 +34.8 t=5.39 | finalauct  +9.9 t=3.26 | exdrop_raw -127.0 t=-29.7 win25% | exdrop_adj   -9.0 t=-2.18 win58% | post_oc  +9.6 t=3.01 | +5d  -44.1 t=-5.97 | +10d  -87.7 t=-7.51
[PERK    2020-2026  ] n=5051  runup10  -1.4 t=-0.18| runup5 -37.9 t=-7.56| finalauct -12.3 t=-5.24 | exdrop_raw -182.8 t=-49.6 win18% | exdrop_adj  -34.5 t=-9.95 win53% | post_oc +14.8 t=5.18 | +5d  -73.2 t=-10.8 | +10d -125.9 t=-14.5
[NONPERK 2015-2019  ] n=1777  runup10 +62.7 t=5.32 | runup5 +44.2 t=5.78 | finalauct +17.5 t=4.71 | exdrop_raw  -66.2 t=-15.6 win34% | exdrop_adj  +77.4 t=20.22 win76% | post_oc +16.0 t=3.45 | +5d  -44.1 t=-4.49 | +10d  -76.4 t=-5.82
[NONPERK 2020-2026  ] n=3004  runup10 +12.2 t=1.10 | runup5 -18.4 t=-2.67| finalauct -10.3 t=-3.24 | exdrop_raw -116.5 t=-29.7 win25% | exdrop_adj  +70.6 t=19.80 win74% | post_oc +13.9 t=3.82 | +5d  -76.2 t=-8.60 | +10d -139.4 t=-12.0

[PERK    3/9-month  ] n=4655  runup10 +88.0 t=10.2 | runup5 +13.6 t=2.58 | finalauct  +0.4 t=0.17 | exdrop_raw -127.0 t=-39.1 win25% | exdrop_adj  +11.8 t=3.84 win64% | post_oc +17.1 t=6.35 | +5d  -60.1 t=-9.00 | +10d -125.0 t=-14.8
[PERK    other-month] n=3504  runup10 -53.1 t=-6.10| runup5 -41.8 t=-6.93| finalauct  -9.4 t=-3.15 | exdrop_raw -207.5 t=-42.8 win14% | exdrop_adj  -73.3 t=-16.1 win43% | post_oc  +7.2 t=2.05 | +5d  -64.9 t=-8.31 | +10d  -93.2 t=-7.93
[NONPERK 3/9-month  ] n=3690  runup10 +54.0 t=5.68 | runup5 +15.2 t=2.57 | finalauct  +1.7 t=0.64 | exdrop_raw  -80.3 t=-25.7 win31% | exdrop_adj  +91.1 t=32.57 win79% | post_oc +14.1 t=4.56 | +5d  -70.9 t=-9.34 | +10d -127.9 t=-12.8
[NONPERK other-month] n=1091  runup10 -47.0 t=-2.87| runup5 -29.9 t=-2.74| finalauct  -5.8 t=-1.05 | exdrop_raw -156.9 t=-22.1 win18% | exdrop_adj  +12.3 t=1.91 win59% | post_oc +16.7 t=2.41 | +5d  -41.9 t=-3.01 | +10d  -75.7 t=-4.09

[CONTROL random-date, perk    tickers] n=2226  runup10  +2.2 t=0.16 | runup5  +8.1 t=0.90 | finalauct -7.3 t=-1.92 | exdrop -adj same as raw (no div) +5.7 t=2.12 win51% | post_oc -1.4 t=-0.34 | +5d  -6.1 t=-0.53 | +10d -16.6 t=-0.96
[CONTROL random-date, non-perk tickers] n=1156  runup10  -8.5 t=-0.42 | runup5  -8.1 t=-0.62 | finalauct +1.9 t=0.34 | exdrop -adj same as raw (no div) -1.9 t=-0.39 win51% | post_oc -3.8 t=-0.74 | +5d  -0.2 t=-0.01 | +10d -26.6 t=-1.39
```

**Cash-long unit cost, perk stocks** (100 shares × close(D-1), JPY, n=8,159 events):
min 3,417 · p10 44,680 · p25 74,600 · **median 127,200** · p75 211,400 · p90 319,000 ·
max 1,970,000 · mean 164,370. Only 0.3% of events exceed ¥1,000,000/unit — comfortably
inside small-capital feasibility.

## 5. Read

The run-up exists but concentrates in the D-10→D-5 window, not on the tradeable leg:
the final-day closing-auction return (open(D-1)→close(D-1), the only piece a
0-commission auction order actually captures) is **-3.8bps pooled (t=-2.06)** —
indistinguishable from a small loss — and even in the strongest cut (3/9-month perk
stocks) it's +0.4bps (t=0.17), flat. The 10-day run-up is real in 2015-2019 (+74bps
t=7.60, perk) but has **inverted** in 2020-2026 (-1.4bps pooled, -37.9bps on the D-5
leg, t=-7.56), consistent with `KNOWLEDGE_JP.md`'s "calendar anomalies dead" pattern
extending here too. The ex-drop side is the more striking split: **non-perk dividend
stocks drop *less* than the dividend** (exdrop_adj pooled +73bps t=27.55, win 75%,
era-stable at +77/+71 — the classic partial-dividend-capture/tax effect). **Perk
stocks do the opposite**, dropping *more* than the dividend (exdrop_adj pooled
-25bps t=-9.29, -34bps t=-9.95 in 2020-2026) — whatever demand lifts them before the
record date does not hold through the ex-date, and the post-period confirms
**no recovery** (perk +10d -111bps t=-15.97, non-perk similar). The random-date
control on the same tickers centers on zero everywhere (|t|<2.2, both arms),
confirming the real-event legs are a genuine calendar effect, not noise. Net: the
one leg that matches the owner's actual instrument (a single closing-auction order)
is approximately zero-to-negative — no visible edge here worth a PREREG as designed.
The one leg that *is* large (10-day run-up, pre-2020) needs multi-day exposure, not
a single auction fill, and has decayed to zero/negative currently regardless. Reads
as a **rejection candidate** for `KNOWLEDGE_JP.md` §3 — though see §3 caveats
(perk-list selection bias, time-invariant perk flag, overlapping-event-day t-stat
inflation) before treating it as final; a hand-checked subset with point-in-time
perk status would be the natural follow-up if this line is revisited.

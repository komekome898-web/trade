# Packet H — third blind audit

Own script: `audit_H3.py` (scratchpad). Files read: `backtest_data/jpx_etf_daily_20260905/{README.md,manifest.json,*.csv,*.json}`,
`schema/jpx_etf_daily.json`, `backtest_data/reit_onr_20260904/{manifest.md,etf_1343_daily.csv}`, `config/constants.yaml`.
Fetched fresh (per mandatory public-source rule) and saved unmodified to `backtest_data/audit_fetch_H_20260905/`
(README+MD5SUMS included): 1570.T and 1557.T intraday chart-API responses at 1m/5m/1h.
Cost constants used: `sor_commission_yen=0` (SOR-routed), `etf_tick_size_yen_1000_3000_band=1`; **`etf_spread_bps` is
`null`/"do not use until measured" in `config/constants.yaml`** — no repo-measured spread exists for any claim below.

## JPL6
Denominator: daily close→next-open log return, full available history per ticker (n=2109–3687 days,
2011/2014/2018–2026). Ticker↔index mapping verified from each file's raw `meta.longName` (the snapshot
README's "Name" column is wrong/duplicated — 1321 and 1306 are both labeled "NEXT FUNDS TOPIX" there; the
true mapping is 1321=N225, 1306=TOPIX, 1591=JPX400, 2516=Growth250, 1343=REIT).
Found an **undocumented bad print in 1306.T** (2026-03-30/03-31, price ≈1/10.3 then reverts, no
`events.splits` entry — same signature as the snapshot's own documented defects but not listed there).
After dropping it (and the README-documented 2015-01-05 1306 split-boundary row, itself mischaracterized
as a "bad print" — it's a real, permanent, un-adjusted 10:1 split with no reversion, verified from raw OHLC):
N225 +5.72bps t=+3.40; TOPIX +5.43bps t=+3.49; JPX400 +7.81bps t=+4.68; Growth250 +5.30bps t=+1.80;
REIT +5.13bps t=+4.68 (all n as above). Sign-reversed control flips cleanly. Random-sign-flip null:
p<0.0001 for N225/TOPIX/JPX400/REIT; **Growth250 p=0.064 (not significant at 95%, and its own MDE95=5.76bps
exceeds its observed 5.30bps mean — cannot be distinguished from zero at this n)**. Half-sample split: all
5 hold sign in both halves except 1306 first-half (-7.2bps, n.s.). Pairwise correlation of the 4 equity-index
ETFs' overnight returns is 0.74–0.93 — they are near one common Japan-equity factor, not 5 independent
confirmations; REIT is the only meaningfully distinct instrument (corr 0.46–0.49 with the others). Consistency
check: 1343 recomputed independently from `reit_onr_20260904/etf_1343_daily.csv` gives an identical
+5.13bps/t=+4.68 over the overlapping window (2011-09-05..2026-09-03) — the two snapshots agree exactly where
they overlap.
Verdict: 判定不能

## JPL7
Denominator: mean daily turnover (volume×close, ¥) per ticker; overnight-return std per ticker, n as above.
1311.T mean turnover over full 15y history = 0.127億円/day (claim: 0.3億円/day, off >100%) but **over the
last 2–3 years = 0.30–0.31億円/day (mean), matching within 10%** — the claim's number only reproduces under
a recent-period read, not the full-history one; the claim's text doesn't state which denominator it used.
Mechanism test (thin→execution-artifact→inflated overnight move), cross-section of all 11 tickers:
corr(log turnover, overnight-return std) = −0.04 (near zero — no clear thin-implies-noisier relationship);
1311's overnight/intraday-std ratio (1.03) is actually *lower* than the 5 far-more-liquid US-tracking ETFs
(1.88–2.28, explained by session composition — their "overnight" spans the entire US trading day, a
simpler alternative explanation than illiquidity). What *does* support the claim: 1311's own mean overnight
premium (+9.04bps, t=+5.61, n=3688) is the largest of the 6 domestic-underlying tickers, and at 1311's
¥2,143 price the ¥1 tick alone is 4.7bps — comparable to half the measured effect — vs. a negligible 0.15bps
at 1321's ¥67,330 price. So a tick-quantization/microstructure floor is economically material for 1311
specifically, but `etf_spread_bps` (the more direct test) is unmeasured in this repo, so "artifact" cannot be
confirmed or rejected from OHLC alone.
Verdict: 判定不能

## JPR6
Packet row: individual-ETF minute bars not snapshotted. Mandatory fetch attempted for a leveraged-ETF proxy
(1570.T, the most liquid JPX leveraged Nikkei product) and for 1557.T: all 4 requests returned HTTP 200
(saved to `backtest_data/audit_fetch_H_20260905/`), but Yahoo's free API caps 1-minute bars at ~5 trading
days and 5-minute bars at ~1 month — **no free source in this session provides 170 days of 1-minute JPX
data**, so the claim's exact cells (順張り全セル≈−1bps, t≈0) cannot be recomputed. A non-equivalent, coarser
supplementary check (1570.T hourly bars, 1 year, n=241 days: P(last-hour move same sign as the rest of the
day)=49.8%, corr=−0.005) shows the same *qualitative* "no trace" pattern, but at 1h not 1m resolution and 1y
not 170d, so it cannot stand in for the claimed measurement.
Verdict: 再計算不能 (元データ未取得。1分足170日相当の無料データ源なし。粗い代替(1時間足・1年)は方向一致のみ、代替可能な精度ではない → 未検証)

## JPR7
Tested via daily open→close ("Tokyo session") vs close→next-open returns for the 5 US-tracking ETFs.
1547.T and 1557.T's `first_date` in the snapshot (2011-09-05) is exactly today minus the 15y fetch window,
not their real listing dates (both funds are far older) — **the "first listing year" cannot be tested for
these two from this snapshot**; only 2521.T (2018-07-30), 2558.T (2020-01-07), 1655.T (2017-09-26) have
organic listing dates inside the window. For those 3: first-year Tokyo-session mean = 2521 −19.75bps
(t=−4.45, n=248), 2558 −14.07bps (t=−2.01, n=243), 1655 −4.90bps (t=−1.76, n=260); later years ≈0
(−0.15/+1.84/+0.83bps, all |t|<1.6). This reproduces the claimed pattern (negative Tokyo-session return
concentrated in the first listing year) clearly for 2 of 3 testable tickers and marginally for the third;
2 of the 5 named instruments are structurally untestable from this snapshot (data-window truncation, not a
contradiction).
Verdict: 数値差異(結論維持)

## 前提の誤り
- premise: snapshot README's per-symbol "Name" column identifies each ticker's tracked index | source: `jpx_etf_daily_20260905/README.md` table | what the data shows: 1321 and 1306 are both labeled "NEXT FUNDS TOPIX" though raw `meta.longName` shows 1321=Nikkei 225, 1306=TOPIX | direction of bias: could cause a downstream reader to swap the two series' results | inherits to: JPL6, JPR8 (any claim keying off this table's Name column instead of `meta.longName`).
- premise: the snapshot's own "known data-quality issues" list is the complete inventory of bad prints | source: `jpx_etf_daily_20260905/README.md` / `schema/jpx_etf_daily.json` `known_defects` | what the data shows: 1306.T also has an undocumented bad print at 2026-03-30/03-31 (same signature: ~10x collapse, no `events.splits`, reverts) not listed anywhere in the snapshot's documentation | direction of bias: understates 1306's volatility/mean if not filtered (flips TOPIX's overnight sign from −0.9bps/t=−0.1 to +5.4bps/t=+3.5 in this audit) | inherits to: JPL6, and any future claim using 1306.T raw close/open without an independent bad-print scan.
- premise: 1306.T's 2015-01-05 row is a "bad print" (implies transient, correctable by treating one day as void) | source: same README, "ISOLATED BAD-PRINT DAYS" list | what the data shows: it is a real, permanent 10:1 unit split (price stays ≈1/10 forever after, never reverts) that Yahoo's `events.splits` failed to tag — mischaracterizing it as reverting understates that the whole close(2014-12-30)→open(2015-01-05) *pairing* (not just the one row) is invalid, not only the single day | direction of bias: without the fix used here, this pairing alone (a −233% "return") dominates 1306's mean/std | inherits to: JPL6 (TOPIX row).
- premise: `etf_spread_bps` (the direct cost input for any "execution artifact" / net-of-cost translation claim) is a known, usable value | source: `config/constants.yaml` | what the data shows: `value: null`, explicitly flagged "do not use a value here until measured" | direction of bias: any claim (JPL7, JPR8, and this audit's own Q3 translation) that speaks of "artifact" cost or nets a premium against spread is, at best, a tick-size floor, not a real cost estimate | inherits to: every claim in this packet that discusses execution cost or artifact magnitude in yen terms.
- premise: a ticker's `first_date` in this 15y-range snapshot equals its real listing date | source: implicit in any "first year of listing" analysis (relevant to JPR7) | what the data shows: 1547.T and 1557.T (and also 1306/1321/1343/1311) show `first_date` = exactly (fetch date − 15y), i.e. window-truncated, not the true listing date | direction of bias: would make a "first-year" test on those tickers meaningless (the "first year" observed is really "15 years ago", not listing) | inherits to: JPR7's two untestable tickers, and any composite/aggregate figure across all 5 ETFs that silently includes them as if listing-dated.
- premise: 5-index cross-market agreement in JPL6 counts as 5 independent confirmations | source: claim framing "JPX市場横断" | what the data shows: overnight-return correlation among 4 of the 5 series is 0.74–0.93 (one dominant common factor); only REIT is meaningfully distinct | direction of bias: overstates the breadth/independence of the "全て正" finding | inherits to: JPL6, and any later claim citing "5/5 markets agree" as strong multi-market evidence.

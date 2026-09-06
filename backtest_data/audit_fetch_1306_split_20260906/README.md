# 1306.T split audit — fetched 2026-09-06 (all times JST unless noted)

Task: verify whether 1306 (NEXT FUNDS TOPIX連動型上場投信) really executed a 10:1
split effective ~2015-01-05 as claimed by `schema/jpx_etf_daily.json`, and get an
independent read of the true price on 2022-03-04 and 2026-09-04 (latest).
No existing repo data file was modified.

## Files and what each shows

### td_260217d.pdf
URL: https://nextfunds.jp/data/2026/td_260217d.pdf
Fetched: 2026-09-06 01:23 UTC, HTTP 200, 446,632 bytes
**PRIMARY SOURCE.** Official TDnet-style disclosure by 野村アセットマネジメント
株式会社 (Nomura Asset Management), dated 2026年2月17日, title
"上場投資信託（ETF）の受益権分割および売買単位変更に関するお知らせ".
Exact quoted table (対象 ETF: NEXT FUNDS TOPIX連動型上場投信(1306)):

> 分割比率　１口を１０口に分割
> 分割基準日　２０２６年３月３１日
> 分割効力発生日　２０２６年４月１日
> 受益権分割前の発行済受益権総口数　8,123,202,626 口
> 受益権分割後の発行済受益権総口数　81,232,026,260 口

Also (新旧対照表 for the trust agreement, 変更後 column):
> この信託の信託契約締結時の受益権の価額は、1 口につき 1,250 円とします。
> なお、2026 年 3 月 31 日現在の受益権を 1 対 10 の割合で再分割しており、
> 当初元本は 1 口当たり 125 円です。

This is the ONLY unit-split event for 1306 documented anywhere in this fetch:
a real 1-for-10 split with 基準日 2026-03-31 / 効力発生日 2026-04-01. No mention
of any split in 2014/2015 anywhere in this 9-page primary document.

### pd_260330a.html
URL: https://nextfunds.jp/news/2026/pd_260330a.html
Fetched: 2026-09-06 01:23 UTC, HTTP 200, 36,891 bytes
Nomura AM's own NEXT FUNDS news page, dated 2026年03月30日, confirming execution:
> 2026年2月17日の適時開示...の通り、「NEXT FUNDS TOPIX連動型上場投信（1306）」
> ...について、2026年3月31日を基準日、4月1日を効力発生日として受益権分割を
> 実施いたします。

### nikkei_1306_split.html
URL: https://www.nikkei.com/article/DGXZMSZ913060DX10C26A2000000/
Fetched: 2026-09-06 01:22 UTC, HTTP 200, 343,294 bytes
Nikkei 適時開示 headline article, dated 2026年2月17日 16:04:
> NEXT FUNDS TOPIX連動型上場投信(1306) 受益権分割=3月31日現在の受益権1口を10口
Confirms the same 2026 split via an independent (non-fund-company) outlet.

### nikkei_1306_disclosure_20260217.html
URL: https://www.nikkei.com/nkd/disclosure/tdnr/20260217563923/
Fetched: 2026-09-06 01:23 UTC, HTTP 200, 17,417 bytes
Nikkei's TDnet disclosure index entry, title:
"上場投資信託（ETF）の受益権分割および売買単位変更に関するお知らせ 2026年2月17日"
— same disclosure, paywalled body, but the headline/date corroborate td_260217d.pdf.

### jpx_1306_factsheet.pdf
URL: https://www.jpx.co.jp/equities/products/etfs/issues/files/1306-j.pdf
Fetched: 2026-09-06 01:22 UTC, HTTP 200, 279,810 bytes
JPX's own ETF fact sheet, dated "2026年2月27日現在" (i.e. one month before the
split's 基準日/effective date), shows:
> 市場価格（終値） 4,131.0 円　／　受益権口数 8,133,974,978 口
This is the pre-split price scale (~4,131円/unit), consistent with the raw
close of ~4,000-4,400 that the true (unadjusted) series should show just before
2026-04-01 — and consistent with the post-split price (~410-440円, i.e. 4,131/10)
seen in September 2026.

### kabutan_1306_kabuka.html
URL: https://kabutan.jp/stock/kabuka?code=1306
Fetched: 2026-09-06 01:24 UTC, HTTP 200, 80,013 bytes
**INDEPENDENT price source (not Nomura, not Yahoo).** Daily OHLC table, unit
noted as "単位 10株" (post-split trading unit). Exact quoted row:
> 26/09/04　428.5　429.1　424.3　427.5　+0.3　+0.07　11,631,790
i.e. 2026-09-04 close = 427.5円 — matches backtest_data CSV's 2026-09-04 close
(427.5) exactly.

### yahoojp_1306_history.html
URL: https://finance.yahoo.co.jp/quote/1306.T/history
Fetched: 2026-09-06 01:24 UTC, HTTP 200, 198,833 bytes
Yahoo!ファイナンス (Japan site, independent front-end/backend from the
Yahoo *US* chart API that backtest_data/.../1306.T.json/csv were built from).
Row for 2026/9/4: 始値428.5 高値429.1 安値424.3 終値427.5 調整後終値427.5.
Confirms kabutan's 427.5 for the latest date.

### yahoojp_1306_history_2022.html
URL: https://finance.yahoo.co.jp/quote/1306.T/history?from=20220301&to=20220310&timeFrame=d
Fetched: 2026-09-06 01:24 UTC, HTTP 200, 169,416 bytes
**Key independent evidence.** Yahoo Japan's time-series table for early March
2022, which shows BOTH the raw close and its own split-adjusted close side by
side. Exact quoted row for 2022-03-04:
> 2022/3/4　1,951　1,952　1,912　1,920.5　2,682,780　192.05
Columns are 始値(open) 高値(high) 安値(low) 終値(raw close) 出来高(volume)
調整後終値(split-adjusted close). So:
- True traded close on 2022-03-04 = **1,920.5円**
- Yahoo Japan's own split-adjusted close for that date = **192.05円**
  (= 1,920.5 / 10, i.e. retroactively adjusted for the real 2026-04-01 1:10 split)

192.05 is exactly the "close" value that appears in
`backtest_data/jpx_etf_daily_20260905/1306.T.csv` for 2022-03-04
(`192.0500030517578`). This proves the US Yahoo chart-API series used to build
that CSV is not raw/unadjusted — its "close" column is already split-adjusted
for the 2026-04-01 split for dates in this range, even though no splits event
appears in the paired 1306.T.json (checked: `events` contains only
`dividends`, no `splits` key at all).

### minkabu_1306.html, nomura_top.html
Fetched 2026-09-06 01:22-01:24 UTC. minkabu.jp returned HTTP 403 (blocked);
nomura-am.co.jp root redirected to an unrelated favorites-migration 404 page.
Neither yielded usable content; kept only for the record of what was tried.

## Findings

**(a) Was there a real 10:1 split around 2015-01-05?** No. The only unit split
documented for 1306 in any primary or independent source found is **1-for-10,
分割基準日 2026-03-31, 効力発生日 2026-04-01**, announced 2026-02-17 by Nomura
Asset Management (td_260217d.pdf) and executed as announced (pd_260330a.html,
Nikkei). No source mentions any split near end-2014/early-2015. The raw
`1306.T.json` in backtest_data also has no `splits` key in `events` (only
`dividends`) — so schema/jpx_etf_daily.json's claim that a 2015 split is
"visible in raw JSON events.splits" is factually wrong; that key doesn't
exist there at all.

**(b) True prices, independently verified:**
- 2022-03-04: **1,920.5円** (raw close, Yahoo Japan time series) — NOT 192.05円
  (which is Yahoo's own retroactive 2026-split-adjusted figure for that date).
- 2026-09-04 (latest available): **427.5円**, confirmed identically by both
  kabutan.jp and Yahoo!ファイナンス(Japan) — this matches the CSV as-is.

**(c) Is the Yahoo daily series' post-2015 level correct, or 1/10 of true?**
It is **1/10 of the true historical price** for the whole span from
2015-01-05 through 2026-03-31 (the day before the real split). The CSV's
"close" column is split-adjusted for the real 2026-04-01 1:10 split, but that
adjustment was evidently mis-dated by the data vendor: it starts abruptly at
2015-01-05 instead of covering the fund's entire history back to 2001 (prices
before 2014-12-30, e.g. 1,442円, remain at full/unadjusted scale) and stops
being needed after 2026-04-01 (post-split dates are naturally already at the
low scale, e.g. 427.5円 matches independent sources exactly with no
adjustment factor). So: pre-2015-01-05 values are correct as printed;
2015-01-05 through 2026-03-31 values are ~10x too low versus what actually
traded on those dates; 2026-04-01 onward values are correct as printed. There
was no real corporate action at 2015-01-05 to justify any scale change there —
the discontinuity is a data-pipeline artifact, not a market event.

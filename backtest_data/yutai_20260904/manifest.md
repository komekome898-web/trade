# yutai_20260904 snapshot manifest

Frozen snapshot for `scripts/research_yutai.py` (SURVEY, no PREREG).
Fetched 2026-09-04. Does not change; do not re-fetch in place.

## Contents

- `universe.csv` — 900 rows: code, name, market (prime/standard), perk_flag (1/0),
  kenri_month (権利確定月 string from kabuyutai.com, perk rows only).
  600 perk + 300 non-perk control.
- `px.tar.gz` — daily OHLCV + dividend (JPY/share, ex-div date keyed) CSVs, one per
  ticker (`<code>.csv`) plus `IDX_N225.csv`, 2015-01-01..2026-09-04, from Yahoo
  Finance chart API (`query1.finance.yahoo.com/v8/finance/chart/<code>.T`,
  `events=div`). `research_yutai.py` extracts this tarball to `px/` on first read.

## Construction

1. JPX listed-issues file (`data_j.xlsx`, 2026-09-04) → filtered to
   プライム（内国株式）+ スタンダード（内国株式）= 3,111 names.
2. kabuyutai.com screener tool (`tool/shiborikomi/`, 86 pages x 20/page,
   sorted by combined 総合利回り desc) → 1,715 unique perk-stock records
   (code, name, 権利確定月, required investment, yutai yield, dividend yield).
   Intersected with (1): 1,463. Capped to top 600 by the site's default sort
   (i.e. NOT a random sample — biased toward higher combined yield / more
   "popular" perks; see caveats in docs/SURVEY_JP_YUTAI.md).
3. Control: 900 non-perk codes sampled (seed 20260904) from the (1) universe
   minus all 1,715 kabuyutai-matched codes, price+dividend-fetched from Yahoo
   (729/900 completed within the time budget — see fetch_log), then filtered to
   dividend-paying (>=4 ex-div events 2015-2026) and median-close price within
   the perk sample's p2-p98 range (161-4,759 JPY), capped to 300 (631 passed
   the filter out of 729 fetched, so the cap bound, not the shortfall).

## Known issues

- minkabu.jp/yutai (the first-choice source per the task) returned one usable
  page (~31 tickers, a homepage popularity widget) before an AWS-WAF-level
  403 made it unreachable for the rest of the session — not used for the bulk
  list. kabuyutai.com's screener (found via its site nav, not documented
  publicly) supplied the full list instead.
- Perk flag is applied as of 2026-09 (today's kabuyutai roster) to the whole
  2015-2026 event history per ticker — a stock that dropped or added its perk
  program mid-sample is misclassified for the years before/after the change.
  No time-varying perk-status source was available.

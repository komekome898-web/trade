# 2026-09-06 (lead): candles_1m.csv.gz (212 MB) was split into candles_1m_YYYY.csv.gz (see candles_1m_index.json) and the 7,871 raw pages were packed into raw_YYYY.tar (one tar per calendar year of the page timestamp) so that every file stays under GitHub's 100 MB limit. Contents are otherwise unchanged; MD5SUMS regenerated over the new layout.

# bitFlyer lightchart FX_BTC_JPY 1m — full history (rebuilt 2026-09-06)

Source: `https://lightchart.bitflyer.com/api/ohlc?symbol=FX_BTC_JPY&period=m`
(bitFlyer's own public web-chart backend; unauthenticated; NOT a documented
API — see `schema/bitflyer_lightchart_1m.json` and
`docs/PHASE2/BITFLYER_HISTORY_SOURCES.md`). Fetched with
`scripts/fetch_bitflyer_lightchart.py --sleep 0.5`, paginating backward in
12h windows from 2026-09-06 until the server returned an empty page
("history exhausted" in `fetch.log`).

This supersedes the partial 406-page build documented in an earlier
version of this README (291,600 rows, 2026-02-15..2026-09-06 only). No raw
page was deleted or modified — the fetch simply continued from where it
left off, and `candles_1m.csv.gz` / `gaps_gt5min.txt` / `MD5SUMS` were
rebuilt from ALL raw pages now on disk, offline (no network request), via:

```
python scripts/fetch_bitflyer_lightchart.py --out backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906 --rebuild
```

which delegates to `scripts/build_bitflyer_lightchart_csv.py`'s `rebuild()`
(the fetch script itself has no consolidation logic of its own; `--rebuild`
was added so a raw-page rebuild never needs to touch the network again).

## What's here

- `raw/page_<window_start_ms>_<window_end_ms>.json` — every raw HTTP
  response body, one file per 12h window, exactly as returned. **7,871
  pages**, covering 2015-11-28 through 2026-09-06.
- `candles_1m.csv.gz` — all raw pages combined, deduplicated by timestamp,
  sorted ascending. Columns (see `schema/bitflyer_lightchart_1m.json` for
  full per-column documentation):
  - `ts` — start of the 1-minute bucket, ISO-8601 UTC.
  - `open`, `high`, `low`, `close` — JPY; **null** when the minute had zero
    executions (this source does not forward-fill, unlike
    `backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz`).
  - `volume` — BTC, sum of execution sizes; 0 on a null-OHLC minute.
  - `col7_inferred_long_oi`, `col8_inferred_short_oi` — **inferred, not
    confirmed by bitFlyer documentation**; large, slowly-drifting numbers
    present from ~2017-07 onward, guessed to be long/short open-interest-like
    snapshots for the FX product. Null before ~2017-07 (OHLCV-only era).
  - `buy_volume`, `sell_volume` — taker-buy/sell split of `volume`
    (`buy_volume + sell_volume == volume` verified on every row checked).
    Null before ~2017-07.
- `gaps_gt5min.txt` — every gap >5 minutes between consecutive *real*
  (non-null) bars, with a per-year summary at the top.
- `fetch.log` — stdout of the fetch run (the part of it captured this
  session; the run resumed a partial log from the earlier 406-page build).
- `MD5SUMS` — checksums of every file here (incl. every raw page and this
  README).

## Coverage

- **5,662,046 rows**, timestamp range **2015-11-28 04:54 UTC .. 2026-09-06
  00:00 UTC** (≈10.8 years), from all 7,871 fetched 12h pages (history
  exhausted — the page immediately before 2015-11-28 came back empty).
  This is close to, and very slightly earlier than, the ~2015-11-30 start
  estimated by the original 12h-granularity probe
  (`backtest_data/audit_fetch_bitflyer_history_20260906/README.md`).
- 294,741 rows are null-OHLC (zero-execution minutes; volume=0).
- **13,065 gaps >5min** between real bars. Per-year breakdown (see
  `gaps_gt5min.txt` for the full list):

  | year | gaps | total gap minutes |
  |------|------|--------------------|
  | 2015 | 1,521 | 38,553 |
  | 2016 | 6,685 | 76,036 |
  | 2017 |   391 |  5,470 |
  | 2018 |   312 |  4,429 |
  | 2019 |   374 |  5,988 |
  | 2020 |   389 |  7,423 |
  | 2021 |   395 |  5,949 |
  | 2022 |   375 |  5,039 |
  | 2023 | 1,316 | 12,589 |
  | 2024 |   665 |  7,593 |
  | 2025 |   368 |  4,951 |
  | 2026 |   274 |  4,247 |

  2015-2016 dominate both gap count and total gap minutes — consistent with
  a thin, early-days FX_BTC_JPY market (long real stretches with literally
  no execution) rather than a collection problem: those two years are also
  where the fetch pagination itself starts (2015-11-28), so there is no
  earlier data to cross-check against. 2023 is the next-largest outlier
  (1,316 gaps); not individually root-caused here. Three gaps stand out as
  unusually large relative to their neighbours and were not individually
  root-caused: 721min (2026-08-23 12:00 -> 2026-08-24 00:01), and two
  ~185-191min gaps on 2015-11-28 (early-history thin liquidity).

## Data quality (`scripts/data_quality.py`, run 2026-09-06)

Full findings recorded in `schema/bitflyer_lightchart_1m.json`
`known_defects`. Summary:

- **Schema bug fixed**: the schema previously documented the timestamp
  column as `ts_ms` (raw epoch ms); the actual CSV column is `ts` (ISO-8601
  string). Caught by `data_quality.py`'s `missing_columns` check; corrected
  in the schema, no data file changed.
- `zero_volume`: 295,755 rows — 294,741 are the documented null-OHLC
  minutes (expected, not a defect); 1,014 have a real close but
  volume printing as exactly 0.0 (plausibly a sub-satoshi rounding
  artifact, not individually root-caused).
- `maintenance_window`: 1,483 flat (O=H=L=C) bars inside 19:00-19:10 UTC —
  since this source nulls true no-trade minutes instead of forward-filling,
  a flat bar here means one real execution printed in that window, not the
  carried-forward-bar artifact documented for `schema/candles_fx_btc_jpy.json`.
- `extreme_return`: 27 rows (|1-minute return| > 10%) across the whole
  file; **2017-2018 SFD-era check** (as requested): ~15 of the 27 cluster
  in 2017-2018 — 2017-02-13, 2017-05-25 (a spike-and-9-minute-reversion),
  2017-11-29 (bubble-top volatility), 2017-12-07, and 2018-01-16 (five
  prints during the Jan-2018 crash). These line up with known market-wide
  events and show clean reversion patterns consistent with real (if
  thin-liquidity) prints rather than fabricated bad ticks — not
  independently confirmed against another contemporaneous source. Nothing
  excluded, flag-only per repo convention.
- `gaps`: 69 rows flagged relative to the file's own median 60s cadence,
  all already enumerated in `gaps_gt5min.txt`.

## Comparison against existing snapshots (full detail: `schema/bitflyer_lightchart_1m.json`)

- vs `backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz` (2026-07-23..
  08-23): 41,461 comparable minutes, **89.5%** exact OHLC match, close
  differs >0.5 JPY on 5.1% (a few outliers up to several thousand JPY on
  minutes where volume matches exactly — likely a minute-bucketing
  difference between bitFlyer's REST candle builder and this chart
  backend). 3,171 minutes are non-null (forward-filled) in the REST
  snapshot but null (no execution) here — consistent with that snapshot's
  known zero-volume-ffill defect.
- **Full-overlap check** against
  `backtest_data/fx_btc_jpy_1m_continuous_20260906/candles_1m.csv.gz` over
  that file's **entire span** (2026-07-23 12:09 .. 2026-09-05 13:47 UTC,
  superseding the two separate partial checks from the earlier build):
  **57,924 comparable minutes, 88.5% exact OHLC match**, close differs
  >0.5 JPY on 5.67%, >100 JPY on 3.36% (1,946 minutes), >1,000 JPY on 504
  minutes, max observed diff 16,573 JPY. All 3,171 real-in-continuous/
  null-in-lightchart minutes fall on the REST (`frozen_candles_31d`) side
  of that file, none on its WS-tape side — consistent with the REST
  snapshot's known ffill defect, not a lightchart problem.

Net: good but not perfect agreement everywhere (~85-90% exact minute
match against every other bitFlyer-side source checked so far); treat
lightchart as a credible independent multi-year OHLCV source, not as
ground truth to blindly prefer over the others.

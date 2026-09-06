# bitFlyer lightchart BTC_JPY (spot) 1m — full history (built 2026-09-06)

Source: `https://lightchart.bitflyer.com/api/ohlc?symbol=BTC_JPY&period=m`
(bitFlyer's own public web-chart backend; unauthenticated; NOT a documented
API -- same endpoint family as
`backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/`, just the
**spot** BTC/JPY market instead of the Crypto CFD product this repo
trades. See `schema/bitflyer_lightchart_1m.json` `symbols.BTC_JPY` and
`docs/PHASE2/P2-08/BLINDSPOT_AUDIT.md` item 3/PREREG.md's diagnostic (d)
-- this dataset exists to measure the FX-CFD/spot basis as a P2-08
auxiliary diagnostic, not as a judged input to the strategy).

Raw pages (`raw/page_<window_start_ms>_<window_end_ms>.json`, one per 12h
window) were fetched by a prior session with
`scripts/fetch_bitflyer_lightchart.py --symbol BTC_JPY --sleep 0.5`; that
session's stdout log was not preserved (no `fetch.log` here, unlike the
FX_BTC_JPY build -- the fetch itself completed, only the log capture did
not carry over). This session's contribution is purely the **offline,
network-free** consolidation of the 8,108 raw pages already on disk, via:

```
python scripts/build_bitflyer_lightchart_csv.py --dir backtest_data/bitflyer_lightchart_BTC_JPY_1m_20260906
```

followed by the same per-year split (`candles_1m_YYYY.csv.gz` +
`candles_1m_index.json`) and per-year raw-page tar packing
(`raw_YYYY.tar`, arcname `raw/page_*.json`) used for the FX_BTC_JPY
directory, done by hand here since no script performs that split yet
(everything after the initial `candles_1m.csv.gz`/`gaps_gt5min.txt`
build is a straight line-preserving repack -- no OHLCV value was
recomputed or altered). The intermediate single `candles_1m.csv.gz`
(178 MB, over GitHub's 100 MB file limit) was deleted after the
per-year files were verified against it (row counts sum to the same
total, see below) and the raw `raw/` directory was deleted after every
one of its 8,108 files was confirmed present, byte-identical, and
individually JSON-parseable inside the 12 `raw_YYYY.tar` archives.

## What's here

- `raw_<year>.tar` (12 files, one per calendar year of the page window's
  start timestamp) -- every raw HTTP response body, one file per 12h
  window, exactly as returned. **8,108 pages total**, covering
  2015-08-01 12:00 UTC (page start) through 2026-09-06 00:00 UTC.
- `candles_1m_<year>.csv.gz` (12 files, 2015-2026) -- all raw pages
  combined, deduplicated by timestamp, sorted ascending, split by
  calendar year so every file stays under GitHub's 100 MB limit. Columns
  (see `schema/bitflyer_lightchart_1m.json` for full per-column
  documentation, shared with the FX_BTC_JPY file):
  - `ts` -- start of the 1-minute bucket, ISO-8601 UTC.
  - `open`, `high`, `low`, `close` -- JPY; **null** when the minute had
    zero executions (no forward-fill, same convention as the FX_BTC_JPY
    file).
  - `volume` -- BTC, sum of execution sizes; 0 on a null-OHLC minute.
  - `col7_inferred_long_oi`, `col8_inferred_short_oi`, `buy_volume`,
    `sell_volume` -- same inferred/unconfirmed fields as the FX_BTC_JPY
    file; not independently re-checked for the spot symbol in this
    session (inherited from the shared schema entry).
- `candles_1m_index.json` -- per-year `{rows, first, last, md5, bytes}`
  for the 12 `candles_1m_<year>.csv.gz` files (`time_column: "ts"`).
- `gaps_gt5min.txt` -- every gap >5 minutes between consecutive *real*
  (non-null) bars, with a per-year summary at the top (single file
  covering all years, same as the FX_BTC_JPY directory).
- `MD5SUMS` -- checksums of every file here (this README included).

## Coverage

- **5,828,554 rows**, timestamp range **2015-08-02 02:07 UTC ..
  2026-09-06 12:00 UTC** (≈11.1 years), from all 8,108 fetched 12h pages.
  This starts about 4 months earlier than the FX_BTC_JPY history
  (2015-11-28) -- spot BTC/JPY trading on bitFlyer predates the FX/CFD
  product, consistent with bitFlyer's own product timeline (not
  independently re-verified against a primary bitFlyer document in this
  session).
- **493,858 rows are null-OHLC** (zero-execution minutes; volume=0),
  8.5% of all rows. Per-year breakdown:

  | year | rows | null-OHLC rows | null % |
  |------|------|-----------------|--------|
  | 2015 | 211,662 | 151,156 | 71.4% |
  | 2016 | 526,169 |  72,296 | 13.7% |
  | 2017 | 525,573 |  18,719 |  3.6% |
  | 2018 | 525,600 |  10,030 |  1.9% |
  | 2019 | 525,600 |  21,962 |  4.2% |
  | 2020 | 526,669 |  16,840 |  3.2% |
  | 2021 | 525,600 |  10,347 |  2.0% |
  | 2022 | 525,600 |  32,735 |  6.2% |
  | 2023 | 525,600 |  32,831 |  6.2% |
  | 2024 | 527,040 |  19,459 |  3.7% |
  | 2025 | 525,600 |  33,801 |  6.4% |
  | 2026 | 357,841 |  73,682 | 20.6% |

  2015 dominates (thin, early-days spot market -- the fetch pagination
  itself starts 2015-08-02, so there's no earlier data to cross-check
  against) and 2026 is a partial year (through 2026-09-06). Both ends of
  the file are expected to look thinner than the well-covered middle
  years; no other year stands out as anomalous.

- **16,590 gaps >5min** between real bars. Per-year breakdown (full list
  in `gaps_gt5min.txt`):

  | year | gaps | total gap minutes |
  |------|------|--------------------|
  | 2015 | 6,429 | 135,525 |
  | 2016 | 3,063 |  28,529 |
  | 2017 |   574 |   6,843 |
  | 2018 |   375 |   5,010 |
  | 2019 |   542 |   7,292 |
  | 2020 |   460 |   8,114 |
  | 2021 |   423 |   6,357 |
  | 2022 |   767 |   8,215 |
  | 2023 |   841 |   9,016 |
  | 2024 |   498 |   6,134 |
  | 2025 |   682 |   7,436 |
  | 2026 | 1,936 |  16,264 |

  2015-2016 dominate both gap count and total gap minutes -- same
  early-thin-market pattern as the FX_BTC_JPY file, not root-caused
  further here. 2026's elevated gap count is partly a partial-year
  artifact (only 8+ months of data) but its gaps-per-row rate is also
  the highest of any full year checked -- not individually root-caused.

## Cross-check against FX_BTC_JPY (basis / correlation, CPU-cheap version
of the P2-08 blindspot audit's diagnostic (d))

Computed by joining `candles_1m_<year>.csv.gz` (this dataset) against
`backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_<year>.csv.gz`
on `ts`, keeping only minutes where **both** sides have a real (non-null)
close, per year and pooled overall:

| year | comparable minutes | close correlation | median (spot-FX)/FX, bps |
|------|--------------------:|-------------------:|---------------------------:|
| 2015 |     5,942 | 0.99549 |     0.2 |
| 2016 |   377,523 | 0.99961 |     0.0 |
| 2017 |   505,532 | 0.99656 |  -177.2 |
| 2018 |   515,325 | 0.99717 |  -228.5 |
| 2019 |   503,440 | 0.99967 |  -199.1 |
| 2020 |   509,733 | 0.99941 |   -75.0 |
| 2021 |   513,944 | 0.99820 |  -390.6 |
| 2022 |   492,797 | 0.99975 |   -25.7 |
| 2023 |   451,716 | 0.99439 |  -301.4 |
| 2024 |   491,939 | 0.99488 |    -9.8 |
| 2025 |   488,878 | 0.99998 |    -2.0 |
| 2026 |   280,128 | 0.99998 |     5.8 |
| **overall** | **5,136,897** | **0.99969** | -- |

**Every year individually clears 0.99, and the pooled overall correlation
is 0.99969** -- well above the 0.99 bar this task asked for. The
per-year basis (median (spot close - FX close)/FX close, in bps) is
persistently negative from 2017-2023 (FX/CFD trading at a premium to
spot, up to several hundred bps in 2017/2018/2021/2023) and shrinks
toward ~0 in 2016 and 2024-2026 -- directionally consistent with
bitFlyer's SFD (Sakizuke Divergence Fee) mechanism, which specifically
exists to tax FX-vs-spot divergence and would be expected to compress it
when active; not independently confirmed against bitFlyer's own SFD-rate
history in this session (flagged as a P2-08 diagnostic input, not a
judged result). 2015 has very few comparable minutes (5,942) because the
FX_BTC_JPY product didn't launch until 2015-11-28, ~4 months after this
spot history starts -- expected, not a data problem.

## Registration

Already covered by the existing `schema/bitflyer_lightchart_1m.json`
`path_glob` (`backtest_data/bitflyer_lightchart_BTC_JPY_1m_*/candles_1m_*.csv.gz`)
and `symbols.BTC_JPY` entry added by a prior session -- no schema change
needed for this build, only this README and the file layout it describes.

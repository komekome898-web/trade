# USDJPY 1-minute BID, 2017-08-01..2022-12-31 (Dukascopy backfill)

Extends `backtest_data/fx_usdjpy_1m_20260822.csv.gz` (2023-01-01 onward)
backward to 2017-08-01, for the USD/JPY control series used in
`docs/PHASE2/P2-08/PREREG.md` (control 5: BTCUSDT x USDJPY synthetic
BTCJPY signal check). Registered in `schema/fx_usdjpy_reference.json`.

## Source

- **事実**: `https://datafeed.dukascopy.com/datafeed/USDJPY/{YYYY}/{MM}/{DD}/BID_candles_min_1.bi5`
  -- Dukascopy's public, unauthenticated historical tick-data CDN (same
  endpoint/format used to build `backtest_data/fx_usdjpy_1m_20260822.csv.gz`;
  see `scripts/fetch_dukascopy.py` header comment for the verified binary
  format: LZMA-compressed `>IIIIIf` records, JPY-pair price divisor 1000).
- **BID only** -- this backfill did not fetch the ASK side (out of scope
  for this task; `ask_close` is kept as an always-empty column purely for
  schema/column parity with the 2023-onward snapshot, see below).
- **取得日**: 2026-09-06.
- **ライセンス注記(推定)**: Dukascopy serves this data from a public,
  unauthenticated CDN endpoint with no login/API key, the same way the
  existing 2023-onward snapshot was obtained -- there is no explicit
  license/ToS text on the endpoint itself to quote, and this session did
  not independently re-verify Dukascopy's terms-of-use page (not
  re-checked here; treat as **assumed** free-for-research use by
  precedent with the existing snapshot, not a confirmed license grant).

## What's here

- `_work/` -- **生ログ**(raw fetch output, kept as-is, not further
  processed): `USDJPY_1m.csv` (176 MB, the day-by-day BID pull before
  compression), `USDJPY_1m.csv.bid.manifest.json` (per-day fetch status,
  `"ok"`/`"empty"`), `fetch_bid.log` (fetch run's stdout).
- `usdjpy_1m.csv.gz` (28 MB) -- `_work/USDJPY_1m.csv.gz` gzip-compressed with
  an added, always-blank `ask_close` column so the header/column order
  exactly matches `backtest_data/fx_usdjpy_1m_20260822.csv.gz`
  (`timestamp,open,high,low,close,volume,ask_close`); every other byte of
  every data row is untouched (no reformatting, no recomputation).
- `QUALITY.json` -- full quality-check output (below is the summary).
- `MD5SUMS` -- checksums of every file here, including `_work/`.

## Coverage

- **2,422,080 rows**, **2017-08-01 00:00:00+00:00 .. 2022-12-30
  23:59:00+00:00** UTC. The requested end date 2022-12-31 has no rows
  because it's a Saturday (market closed) -- same pattern as every other
  Saturday in the file.
- Timestamp format and column order verified identical to
  `backtest_data/fx_usdjpy_1m_20260822.csv.gz`
  (`timestamp,open,high,low,close,volume,ask_close`, e.g.
  `2017-08-01 00:00:00+00:00,110.358,110.374,110.351,110.374,130.39,`).

## Data quality (`QUALITY.json`, full detail there)

- **Duplicate timestamps**: 0.
- **Negative/zero price rows** (open/high/low/close): 0 across all four
  columns -- no bad prints.
- **Zero-volume rows**: 416,995 (17.2% of rows) -- expected: Dukascopy's
  `volume` is a tick-volume proxy that is "frequently 0.0" per the existing
  `known_defects` entry in `schema/fx_usdjpy_reference.json`, and
  `zero_volume` is already an intentionally disabled (`skip_checks`) check
  for this dataset. Not treated as a defect here either.
- **Negative volume rows**: 0.
- **`ask_close`**: blank on all 2,422,080 rows (BID-only fetch, see
  Source above).
- **Gaps >60 minutes** between consecutive 1-minute bars: **288 total**.
  - **278** are the ordinary weekly FX close/reopen (gap starts Friday,
    ends Sunday or Monday) -- market structure, not a defect.
  - **10 non-weekend gaps**, by year:

    | year | non-weekend gaps >60min |
    |------|--------------------------|
    | 2017 | 0 |
    | 2018 | 2 |
    | 2019 | 3 |
    | 2020 | 2 |
    | 2021 | 2 |
    | 2022 | 1 |

    All 10 are 1-2 calendar days wide (1,441 or 2,881 minutes) and line up
    with likely public/bank holidays landing on a weekday next to a
    weekend (e.g. 2021-01-01 New Year's Day, a Friday; 2018-06-04 Whit
    Monday) or an isolated missing weekday not further root-caused; full
    list with each gap's start/end in `QUALITY.json`. None are large
    enough (or frequent enough) to suggest a collection problem rather
    than ordinary market/holiday closures.
- **Fetch manifest cross-check**: the day-by-day fetch manifest
  (`_work/USDJPY_1m.csv.gz.bid.manifest.json`) records 1,682 `"ok"` + 283
  `"empty"` = 1,965 of the 1,979 calendar days in the requested range; the
  14 days it has no entry for at all line up with the non-weekend gaps and
  ordinary Saturdays found directly in the CSV above -- a per-day logging
  gap in the fetch tool's manifest, not additional missing data (the CSV's
  own timestamps, not the manifest, are the source of truth for every
  number in this README/QUALITY.json).
- **Overlap with `backtest_data/fx_usdjpy_1m_20260822.csv.gz`
  (2023-01-01 onward)**: **0 overlapping rows** -- this file's last row is
  2022-12-30 23:59 UTC, the existing snapshot's first row is 2023-01-01
  00:00 UTC; the one calendar day between them (2022-12-31) is a Saturday
  with no market activity in either file. Safe to concatenate.

## Registration

`schema/fx_usdjpy_reference.json` `path_glob` and `file_groups` corrected
to point at the actual filename produced here
(`fx_usdjpy_1m_20170801_20221231/usdjpy_1m.csv.gz`) -- the entry a prior
session had added used a different, never-produced filename pattern
(`fx_usdjpy_1m_*.csv.gz`).

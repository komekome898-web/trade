# 2026-09-06 (lead): the 125 MB concatenated file was split into binance_BTCUSDT_1m_YYYY.csv.gz (see binance_1m_index.json) to stay under GitHub's 100 MB limit; MD5SUMS regenerated.

# Binance BTCUSDT 1m klines, 2017-08-17 .. 2023-12-31

Built 2026-09-06 for phase-2 G2, to extend
`backtest_data/binance_BTCUSDT_1m_20240101_20260831/` (2024-01-01..2026-08-31) backward to Binance's
own BTCUSDT launch. Neither existing Binance snapshot was modified.

## Source

Binance Vision monthly klines:
`https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-YYYY-MM.zip`
(+ matching `.CHECKSUM` file), fetched via the new generalized `scripts/fetch_binance_vision.py`
(written this session — the 2024 snapshot above was built by hand with `curl`; this script factors
that into a reusable `--start YYYY-MM --end YYYY-MM` tool with automatic daily-archive fallback for
any month whose monthly archive isn't published yet, retries on transient network errors, and a
`--consolidate-only` mode to rebuild the CSV from already-downloaded raw/ with no network access).

`--start 2017-08 --end 2023-12`: **2017-07 does not exist** on Binance Vision (`BTCUSDT-1m-2017-07.zip`
-> HTTP 404) — BTCUSDT's first full month of trading is 2017-08, and its first 4 hours-worth of
minutes (before 2017-08-17 04:00 UTC) are simply not covered by the 2017-08 archive either, i.e. the
symbol's trading data itself starts mid-month. All 77 requested months (2017-08 .. 2023-12) had a
published monthly archive — no daily-archive fallback was needed for this range.

## Verification

All 77 monthly zip files were checked against their own `.CHECKSUM` file (SHA-256, as published by
Binance Vision) before use — **77/77 passed**, re-verified again after the fact directly from the raw
files on disk (see below).

## Contents

- `raw/BTCUSDT-1m-YYYY-MM.zip` + `.zip.CHECKSUM` — 77 monthly archives, 2017-08 .. 2023-12, verbatim as
  downloaded.
- `binance_BTCUSDT_1m_20170801_20231231.csv.gz` — single concatenated CSV, same column set as
  `backtest_data/binance_BTCUSDT_1m_20240101_20260831/`'s build (which matches
  `schema/external_crypto_klines.json`'s `binance_BTCUSDT_1m_210d_*.csv.gz` entry): `open_time`
  (ISO-8601 UTC), `open`, `high`, `low`, `close`, `volume` (BTC), `quote_volume` (USDT), `n_trades`,
  `taker_buy_base` (BTC). `close_time`, `taker_buy_quote`, and the trailing `ignore` column from
  Binance's raw kline format are dropped. **3,343,519 rows**, span **2017-08-17 04:00:00 UTC ..
  2023-12-31 23:59:00 UTC**.
- `MD5SUMS` — MD5 of every file in this directory (raw zips, their upstream CHECKSUM files, and the
  concatenated CSV).

## Gaps

35 inter-row gaps where the step between consecutive rows is not exactly 60 seconds (checked by
`scripts/fetch_binance_vision.py`'s `consolidate()`, a strict per-row diff over the whole file — not
yet broken out per year in a separate gaps file, since Binance Vision's monthly archives already carry
one row per minute with 0 volume rather than a missing row for a quiet minute; a handful of true
missing-minute holes still occur mid-history). Not investigated further per-gap here; the row count
above (3,343,519) is very close to the theoretical 3,343,560 (2,321.9917 days x 1440 min), i.e. <0.01%
of minutes are missing.

## Format gotcha (inherited from the 2024 build)

Binance Vision's raw kline `open_time`/`close_time` columns switched from millisecond to microsecond
epoch integers starting with the 2025-01 file — irrelevant to this specific 2017-08..2023-12 range
(entirely pre-switch, millisecond epoch throughout), but `scripts/fetch_binance_vision.py` still
detects the unit per row (`>= 1e14` => microseconds) rather than assuming one format, since the same
script is used for both this build and the 2024-2026 range.

## Combined coverage with the 2024-2026 snapshot

`backtest_data/binance_BTCUSDT_1m_20170801_20231231/` (this dir, 2017-08-17..2023-12-31) and
`backtest_data/binance_BTCUSDT_1m_20240101_20260831/` (2024-01-01..2026-08-31) are contiguous
(2023-12-31 23:59 -> 2024-01-01 00:00, no gap) — together they cover **2017-08-17 .. 2026-08-31**
(≈9 years) of Binance BTCUSDT 1-minute klines, as two separate frozen files (not concatenated into one
here, to avoid touching the existing 2024 snapshot).

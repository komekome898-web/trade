# Binance BTCUSDT 1m klines, 2024-01-01 .. 2026-08-31

Built 2026-09-06 for phase-2 G2 (docs/PHASE2/G2_DATA_INVENTORY.md task 3), to extend the existing
`backtest_data/binance_BTCUSDT_1m_210d_20260820.csv.gz` (2026-01-22 11:34 .. 2026-08-20 11:36) back to
2024-01-01. Neither existing Binance snapshot was modified.

## Source

Binance Vision monthly klines:
`https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-YYYY-MM.zip`
(+ matching `.CHECKSUM` file) for 2024-01 through 2026-07 (31 months).

**2026-08 exception**: the monthly archive for 2026-08 does not exist yet on Binance Vision as of the
fetch time below (`GET .../BTCUSDT-1m-2026-08.zip` -> HTTP 404 / S3 `NoSuchKey`; Binance typically
publishes a month's monthly archive some days after month-end). Fell back to the **daily** archives
for all 31 days of August 2026:
`https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1m/BTCUSDT-1m-2026-08-DD.zip` (+
`.CHECKSUM`), DD=01..31.

Fetched via the environment's configured HTTPS proxy, `curl --cacert /root/.ccr/ca-bundle.crt`.
Fetch time: 2026-09-06 08:47-08:52 UTC.

## Verification

Every one of the 62 zip files (31 monthly + 31 daily) was checked against its own `.CHECKSUM` file
(SHA-256, as published by Binance Vision) before use — 62/62 passed. The 2026-08 monthly zip's
initial download (the XML error page, saved before the 404 was noticed) was discarded, not counted,
and not kept.

## Contents

- `raw/BTCUSDT-1m-YYYY-MM.zip` + `.zip.CHECKSUM` — 31 monthly archives, 2024-01 .. 2026-07, verbatim
  as downloaded.
- `raw/daily_2026_08/BTCUSDT-1m-2026-08-DD.zip` + `.zip.CHECKSUM` — 31 daily archives covering August
  2026 (monthly archive not yet published), verbatim as downloaded.
- `binance_BTCUSDT_1m_20240101_20260831.csv.gz` — single concatenated CSV, columns matching
  `schema/external_crypto_klines.json`'s `binance_BTCUSDT_1m_210d_*.csv.gz` entry: `open_time` (ISO-8601
  UTC), `open`, `high`, `low`, `close`, `volume` (BTC), `quote_volume` (USDT), `n_trades`,
  `taker_buy_base` (BTC). `close_time`, `taker_buy_quote`, and the trailing `ignore` column from
  Binance's raw kline format are dropped (not present in the existing snapshot's column set either).
  1,402,560 rows, exactly 1 row/minute, **zero gaps** (span 2024-01-01 00:00:00 UTC ..
  2026-08-31 23:59:00 UTC = 973 days x 1440 min, verified by a strict 1-minute diff check over the
  whole file).
- `MD5SUMS` — MD5 of every file in this directory (raw zips, their upstream CHECKSUM files, and the
  concatenated CSV).

## A format gotcha handled here

Binance Vision's raw kline `open_time`/`close_time` columns switched from **millisecond** to
**microsecond** epoch integers starting with the 2025-01 file (2024-01 .. 2024-12 are ms; 2025-01
onward, including all of the 2026-08 daily files, are us). The build script auto-detects the unit
per row (`>= 1e14` => microseconds) rather than assuming one format for the whole range — verified by
spot-checking the first row of 2024-12 (ms) vs 2025-01 (us) during the build. Getting this wrong
would have silently shifted every 2025+ timestamp by ~1000x (i.e. into the year ~55700), so this is
called out explicitly rather than left to be discovered downstream.

## Overlap check against the existing 210d snapshot

Compared against `backtest_data/binance_BTCUSDT_1m_210d_20260820.csv.gz` on its full overlap window
(2026-01-22 11:34 .. 2026-08-20 11:36 UTC, 302,403 shared minutes). Sampled 1,000 random overlapping
minutes (`numpy.random.seed(42)`) and compared all 8 non-timestamp columns
(open/high/low/close/volume/quote_volume/n_trades/taker_buy_base, `np.isclose` rtol=atol=1e-6):
**0 mismatching cells out of 8,000 checked, 0/1,000 rows with any mismatch.** The two sources agree
exactly on every sampled minute.

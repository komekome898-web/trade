# jpx_etf_daily_20260905

Re-fetch and permanent snapshot of packet H's 15 Yahoo Finance daily series.
Packet H's first audit fetched these 15 tickers live and never snapshotted
them (data loss) -- this directory is the fix: every raw response is saved
unmodified alongside a derived CSV.

## Source

Yahoo Finance chart API, one GET per symbol:

```
https://query1.finance.yahoo.com/v8/finance/chart/<SYM>?range=15y&interval=1d&events=div,splits
```

Fetched via Python `requests` through the preconfigured HTTPS proxy. All 15
requests returned HTTP 200 with no errors.

Fetch window: 2026-09-05T02:45:52Z .. 2026-09-05T02:46:06Z (see
`_fetch_results.json` for the exact per-symbol timestamp, URL, and HTTP
status).

## Files per symbol

- `<SYM>.json` -- raw Yahoo response body, byte-for-byte, never modified.
- `<SYM>.csv` -- derived: `date,open,high,low,close,adjclose,volume`.
  `date` is the UTC calendar date of the bar's Unix timestamp (see "Time
  basis" below -- for these Asia/Tokyo-exchange symbols this is normally the
  same calendar day as JST, since the bar timestamp sits at 00:00 JST /
  15:00 UTC of the previous day... see caveat below). Empty CSV cells mean
  Yahoo returned `null` for that field on that timestamp (not zero).
- `MD5SUMS` -- md5 of every `.json` and `.csv` in this directory.
- `manifest.json` -- machine-readable summary (row counts, date ranges,
  http status, checksums pointer).

## Per-symbol results

| Symbol | Name (Yahoo shortName) | Type | Rows | First date | Last date |
|---|---|---|---|---|---|
| 1321.T | NOMURA ASSET MANAGEMENT (NEXT FUNDS TOPIX) | ETF | 3690 | 2011-09-05 | 2026-09-04 |
| 1306.T | NOMURA ASSET MANAGEMENT (NEXT FUNDS TOPIX) | ETF | 3690 | 2011-09-05 | 2026-09-04 |
| 1591.T | NOMURA ASSET MANAGEMENT | ETF | 3106 | 2014-01-23 | 2026-09-04 |
| 2516.T | SIMPLEX ASSET MANAGEMENT | ETF | 2111 | 2018-01-30 | 2026-09-04 |
| 1343.T | NOMURA ASSET MANAGEMENT (J-REIT ETF) | ETF | 3690 | 2011-09-05 | 2026-09-04 |
| 1311.T | NOMURA ASSET MANAGEMENT | ETF | 3690 | 2011-09-05 | 2026-09-04 |
| 1547.T | AMOVA ASSET MANAGEMENT | ETF | 3690 | 2011-09-05 | 2026-09-04 |
| 2521.T | AMOVA ASSET MANAGEMENT | ETF | 1982 | 2018-07-30 | 2026-09-04 |
| 2558.T | MITSUBISHI UFJ ASSET MANAGEMENT | ETF | 1629 | 2020-01-07 | 2026-09-04 |
| 1655.T | BLACKROCK JAPAN (iShares) | ETF | 2201 | 2017-09-26 | 2026-09-04 |
| 1557.T | STATE ST SPDR S&P 500 ETF (JPY) | ETF | 3690 | 2011-09-05 | 2026-09-04 |
| 7203.T | TOYOTA MOTOR CORP | EQUITY | 3690 | 2011-09-05 | 2026-09-04 |
| 6758.T | SONY GROUP CORPORATION | EQUITY | 3690 | 2011-09-05 | 2026-09-04 |
| 8306.T | MITSUBISHI UFJ FINANCIAL GROUP | EQUITY | 3690 | 2011-09-05 | 2026-09-04 |
| 9984.T | SOFTBANK GROUP CORP | EQUITY | 3690 | 2011-09-05 | 2026-09-04 |

Note: 4 of the 15 requested Yahoo symbols (7203.T, 6758.T, 8306.T, 9984.T)
are individual equities, not ETFs, per Yahoo's own `instrumentType` field in
the raw JSON meta block -- kept under this dataset name because that is the
ticker list packet H specified, but callers should not assume every row in
this directory is a fund.

## Errors

None. All 15 fetches returned HTTP 200 and parsed cleanly (verbatim status
recorded per symbol in `_fetch_results.json`).

## Known data-quality issues found in this snapshot (verbatim from inspection)

These are Yahoo-side source defects, not fetch/parsing bugs -- reproducible
by re-reading the raw `<SYM>.json` files in this directory:

- **Null quote rows** (date present in `timestamp[]`, OHLC/volume fields
  `null` in Yahoo's `indicators.quote[0]`, rendered as empty CSV cells):
  `2017-07-17` and/or `2025-10-24` appear null across most of the 1306/1311/
  1321/1343/1547/1591/2516/2521/2558/1655/1557 series. `1557.T` additionally
  has null rows at `2026-03-06`, `2026-09-02`, and a partial-null row at
  `2026-09-04` (open/high/low present, close/adjclose/volume null -- likely
  a same-day fetch racing the exchange close print).
- **Isolated bad-print days** (price collapses to ~1/100 of the surrounding
  level for exactly one bar, volume often 0, no matching entry in Yahoo's
  `events.splits`, so not a real corporate action): `1557.T` on
  `2013-10-29`, `2013-10-31`, `2017-07-17` (e.g. close prints `177.16`
  against a `~17390` close the trading day before and after);
  `1306.T` on `2015-01-05`; `1655.T` on `2017-09-28`, `2022-02-08`;
  `2558.T` on `2026-06-05`, `2026-06-08`. Treat any single-day >80% round
  trip in close-to-close return as a probable bad print, not a real move,
  unless corroborated by `events.splits` in the raw JSON.

See `schema/jpx_etf_daily.json` for the formal column/defect documentation.

## Time basis

The CSV `date` column is the UTC calendar date of each bar's raw Unix
`timestamp` (per the task spec), computed as
`datetime.fromtimestamp(ts, tz=UTC).date()` with no offset applied.
Verified directly against the raw JSON for this snapshot: Yahoo's daily
timestamps for these Tokyo-exchange symbols land at `00:00 UTC`, which is
`09:00 JST` of the *same* calendar day (e.g. raw `timestamp=1315180800` ->
`2011-09-05T00:00:00Z` -> `2011-09-05T09:00:00+09:00`) -- so for this
snapshot the CSV `date` equals the true JST trading date. This is an
empirical finding for the timestamps actually present in these 15 files,
not a documented Yahoo API guarantee; consumers who need the JST date with
certainty should re-derive it from the raw `timestamp` field rather than
assume this always holds.

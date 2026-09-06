# jpx_etf_daily_20260906_topix_alt

Data task for the P2-03 phase-2 hold trigger: `1306.T` (TOPIX ETF used as the
pre-registered trigger reference) became untradable after its real 10:1 unit
split effective 2026-04-01 (see `schema/jpx_etf_daily.json` CORRECTION
2026-09-06 entry and `backtest_data/audit_fetch_1306_split_20260906/`). This
snapshot fetches the two candidate higher-priced TOPIX ETF alternatives named
for the trigger swap: `1348.T` (MAXIS TOPIX ETF) and `1305.T` (Daiwa
iFreeETF TOPIX). Data only -- no research/analysis run on these files (kept
sealed as a new unit first per the task instruction).

## Source

Same method/script as `backtest_data/jpx_etf_daily_20260905/`, now checked in
as `scripts/fetch_jpx_etf_daily.py` (that snapshot's own fetch was ad hoc and
never checked in as a script; this generalizes it verbatim: same URL
template, same per-symbol JSON+CSV output, same manifest shape).

Yahoo Finance chart API, one GET per symbol:

```
https://query1.finance.yahoo.com/v8/finance/chart/<SYM>?range=15y&interval=1d&events=div,splits
```

Fetched via Python `requests` through the preconfigured HTTPS proxy
(CA bundle `/root/.ccr/ca-bundle.crt`). Both requests returned HTTP 200 with
no errors.

Command:
```
python scripts/fetch_jpx_etf_daily.py --symbols 1348.T,1305.T \
    --out-dir backtest_data/jpx_etf_daily_20260906_topix_alt
```

Fetch window: 2026-09-06T03:33:19Z .. 2026-09-06T03:33:20Z (see
`_fetch_results.json` and `manifest.json` for the exact per-symbol
timestamp, URL, and HTTP status).

## Files per symbol

- `<SYM>.json` -- raw Yahoo response body, byte-for-byte, never modified.
- `<SYM>.csv` -- derived: `date,open,high,low,close,adjclose,volume`.
  `date` is the UTC calendar date of the bar's Unix timestamp (see
  `jpx_etf_daily_20260905/README.md` "Time basis" section for the JST
  equivalence finding/caveat, which was not re-verified independently here
  but the fetch method and timestamp handling are identical). Empty CSV
  cells mean Yahoo returned `null` for that field on that timestamp.
- `MD5SUMS` -- md5 of every `.json`/`.csv`/`README.md` in this directory.
- `manifest.json` -- machine-readable summary (row counts, date ranges,
  http status, checksums), written by `scripts/fetch_jpx_etf_daily.py`.
- `_fetch_results.json` -- raw per-symbol fetch metadata (subset of
  manifest.json, written directly by the fetch script).
- `kabutan_1348_kabuka.html`, `kabutan_1305_kabuka.html` -- independent
  confirmation source (see below), raw HTML saved unmodified.

## Per-symbol results

| Symbol | Name (Yahoo shortName / longName) | Type | Rows | First date | Last date | Latest close (CSV) |
|---|---|---|---|---|---|---|
| 1348.T | MITSUBISHI UFJ ASSET MANAGEMENT -- MAXIS TOPIX ETF | ETF | 3690 | 2011-09-05 | 2026-09-04 | 4255.0 |
| 1305.T | DAIWA ASSET MANAGEMENT IFREEETF -- iFreeETF TOPIX (Yearly Dividend Type) | ETF | 3690 | 2011-09-05 | 2026-09-04 | 4328.0 |

## Errors

None. Both fetches returned HTTP 200 and parsed cleanly (verbatim status
recorded per symbol in `_fetch_results.json` / `manifest.json`).

## Split check (raw JSON `events.splits`)

Both raw JSON files were requested with `events=div,splits` and were
inspected directly:

- `1348.T.json`: `chart.result[0].events` has only a `dividends` key. No
  `splits` key at all -- no split event reported by Yahoo for this symbol,
  ever, in this response.
- `1305.T.json`: same -- `events` has only `dividends`, no `splits` key.

Neither raw file shows any `events.splits` entry, so there is no Yahoo-side
split record to reconcile against for either symbol (unlike 1306.T, which
also has no `events.splits` entry despite Nomura AM's real 2026-04-01 10:1
split -- see the CORRECTION 2026-09-06 line in `schema/jpx_etf_daily.json`:
Yahoo's `events.splits` was already known to be an unreliable indicator for
this dataset, since it omitted 1306's real split too).

## Independent price confirmation (kabutan, raw HTML saved)

Fetched `https://kabutan.jp/stock/kabuka?code=1348` and
`https://kabutan.jp/stock/kabuka?code=1305` (HTTP 200, saved verbatim as
`kabutan_1348_kabuka.html` / `kabutan_1305_kabuka.html`, fetched
2026-09-06T03:33:40Z / 2026-09-06T03:33:41Z). Both pages' daily OHLC tables carry the same
2026-09-04 row as the CSV, byte-for-byte on price:

- kabutan 1348 (`code=1348`), row `26/09/04`: open 4,286 / high 4,286 /
  low 4,228 / close **4,255** / volume 57,376 -- matches
  `1348.T.csv` 2026-09-04 exactly (`4286.0,4286.0,4228.0,4255.0,...,57376`).
- kabutan 1305 (`code=1305`), row `26/09/04`: open 4,328 / high 4,336 /
  low 4,287 / close **4,328** / volume 85,840 -- matches
  `1305.T.csv` 2026-09-04 exactly (`4328.0,4336.0,4287.0,4328.0,...,85840`).

## Does the 1306-style split-adjustment bug affect these two symbols?

**No, not detected.** The 1306.T defect (documented in
`schema/jpx_etf_daily.json`'s CORRECTION 2026-09-06 entry) was: Yahoo's US
chart-API series applied the real 2026-04-01 10:1 split adjustment
retroactively from the wrong start date (2015-01-05), producing a ~10x price
level shift with no `events.splits` entry to explain it, confirmed by an
independent source (kabutan/Yahoo Japan) showing the true unadjusted price
was 10x the CSV value for dates before 2026-04-01.

For `1348.T` and `1305.T`:

- The independent kabutan source matches the CSV's most recent close
  **exactly**, with no 10x (or other) discrepancy -- the opposite of what
  was found for 1306.T, where kabutan's contemporary close (427.5) matched
  the CSV's *current* value but the CSV's *historical* (pre-split) values
  were off by 10x.
- The full CSV history shows a smooth, continuous price series from ~760
  yen (2011-09-05) to ~4,255/4,328 yen (2026-09-04) with adjclose tracking
  close closely throughout (adjclose only departs from close gradually, as
  expected from ordinary dividend adjustment) -- there is no abrupt ~10x (or
  other round-factor) level jump anywhere in either series, unlike 1306.T's
  2015-01-05 level shift and 2026-03-30/31 two-bar collapse at the
  adjustment boundary.
- Neither symbol has an `events.splits` entry (see above), consistent with
  neither symbol having undergone a real unit split in this window (1348 and
  1305 are both large, liquid TOPIX ETFs that, unlike 1306, have not had a
  disclosed unit-split/unit-count event as of this fetch).

This is a single independent-source spot check against the latest date only
(not a full historical cross-check like the dedicated 1306 audit) --
sufficient to confirm the *current* price level is not mis-scaled, but not a
guarantee against an undetected historical anomaly elsewhere in either
15-year series. See "Data-quality flags" below for what
`scripts/data_quality.py` found when run against these two files.

## Data-quality flags

`scripts/data_quality.py` was run against this snapshot's two `.csv` files
(after re-running `scripts/intake_ledger.py` to add them to the ledger; full
run recorded in `data/QUALITY.json`, dataset `jpx_etf_daily`). Per-file
result (via `data_quality.scan_file` directly, since the full-repo run only
keeps a handful of examples per check in `data/QUALITY.json`):

- **No `split_candidate` on either file** -- the check that would catch a
  1306-style unadjusted/mis-adjusted split. This is the main quality
  finding for this snapshot.
- `extreme_return`: 1348.T row 3182-3183, 1305.T row 3182 -- both are
  2024-08-05/2024-08-06, the real Nikkei "Black Monday" crash and rebound
  (1348.T 2722.5 -> 2231.5 -> 2519.0; 1305.T 2656.0 -> 2350.0), the same
  event already documented for 1311.T/1321.T/1343.T/1547.T in
  `schema/jpx_etf_daily.json`'s known_defects. Real market move, not a bad
  print.
- `gaps`: one hit each at 2019-05-07 (gap_seconds=950400, median=86400) --
  the 10-day Reiwa-accession Golden Week holiday, same date/pattern as the
  existing 15-symbol files.
- `zero_volume`: 21 (1348.T) / 22 (1305.T) flat carried-forward rows on the
  same recurring JP national-holiday dates as the existing known_defects
  entry (2017-08-11, 2017-09-18, 2017-10-09, 2017-11-03, 2017-11-23, ...);
  1305.T additionally has a real (non-flat) zero-volume row on 2013-10-29.

No new defect class. See `schema/jpx_etf_daily.json`'s "1348.T / 1305.T
ADDED 2026-09-06" known_defects entry for the recorded version of this.

## Time basis

Same as `jpx_etf_daily_20260905/README.md`: the CSV `date` column is the UTC
calendar date of each bar's raw Unix `timestamp`
(`datetime.fromtimestamp(ts, tz=UTC).date()`), which that snapshot verified
empirically equals the JST trading date for these Tokyo-exchange symbols.
Not independently re-verified for `1348.T`/`1305.T` in this fetch (same
fetch method and timestamp handling, so expected to hold identically).

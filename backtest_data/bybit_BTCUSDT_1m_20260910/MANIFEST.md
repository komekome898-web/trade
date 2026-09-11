# Bybit BTCUSDT perpetual, 1-minute OHLC, 2022-01-01 .. 2026-08-31

Built for `docs/PHASE2/K1/XVENUE_PREREG.md` §2 stage 2 (owner approval L-095). Fetched/folded by
`scripts/fetch_bybit_minutes.py`. Directory is gitignored (`backtest_data/bybit_BTCUSDT_1m_20260910/*.csv.gz`
in `.gitignore`); this MANIFEST is committed.

## Files

| file | rows (incl. header) | size (bytes) | sha256 |
|---|---|---|---|
| `bybit_BTCUSDT_1m_2022.csv.gz` | 525,601 | 5,111,531 | `0266e90be4bc88a5cd31d7568cc7e9c60097692de5af2f1aedce23bf54fc4547` |
| `bybit_BTCUSDT_1m_2023.csv.gz` | 525,601 | 5,568,209 | `e66fc9214e018375cb1828193cd0b063e08e33d1c0aedb26346187486d9ded95` |
| `bybit_BTCUSDT_1m_2024.csv.gz` | 527,041 | 6,616,054 | `b3738dce29f806104518790bd53963d000f53de18cd0ce119a3aa310403d6304` |
| `bybit_BTCUSDT_1m_2025.csv.gz` | 525,601 | 6,651,445 | `e92a83d344d6c343780ecb5931f42b02224e823caeff8a9daebd90ba3025f0d6` |
| `bybit_BTCUSDT_1m_2026.csv.gz` | 349,921 | 4,374,217 | `748435e41c7544cdb7b1a35b072d089ec896352321ebae98f003e2f6b92eb6cf` |

Columns: `ts,open,high,low,close`. `ts` = UTC epoch seconds, minute-aligned (`ts % 60 == 0`).
2024 has 527,040 data rows because it is a leap year (366 × 1440); every other year has 525,600
(365 × 1440) or, for the partial year 2026, 349,920 (243 days × 1440, 2026-01-01..2026-08-31).

**Coverage check (measured after acquisition + gap patching below): every single UTC minute from
2022-01-01 00:00 through 2026-08-31 23:59 is present exactly once, no gaps, no duplicates**, for all
five files. There is no minute in this range with zero trades on Bybit BTCUSDT perpetual.

## Sources and download dates

- **2022-2024**: `kline_for_metatrader4` archive, monthly files:
  `https://public.bybit.com/kline_for_metatrader4/BTCUSDT/{year}/BTCUSDT_1_{month_start}_{month_end}.csv.gz`
  (no header; `YYYY.MM.DD HH:MM,o,h,l,c,v`). Downloaded 2026-09-10 (initial 2022/2023/2024 fetch by
  the prior implementer, commit `2ee154f`).
- **2023-12 and 2024-01..03 gap patch**: see "Gaps found and patched" below — same daily trade-file
  method as 2025-2026, downloaded 2026-09-11.
- **2025-01-01 .. 2026-08-31**: daily trade files, folded to UTC 1-minute OHLC (open = first trade in
  the minute, high/low = max/min, close = last trade; a minute with zero trades gets no row):
  `https://public.bybit.com/trading/BTCUSDT/BTCUSDT{day}.csv.gz` (header `timestamp,symbol,side,size,
  price,...`), one file per UTC calendar day, 2025-01-01 through 2026-08-31 (608 days). Downloaded
  2026-09-11 (this session), via the environment's configured HTTPS proxy, `urllib.request` with the
  proxy's CA bundle (never disabled). Each daily file was deleted immediately after folding (fixed
  disk budget); nothing raw is retained on disk beyond the folded minute rows above.
- **2024-12-31 tail patch**: also daily trade file (see below), downloaded 2026-09-11.

All fetches used `fetch_bytes()`'s retry policy: up to 4 attempts, exponential backoff (2s, 4s, 8s,
16s), retrying on transient network/proxy/disconnect errors including `http.client.IncompleteRead`
(observed in practice on several large daily files — Content-Length not fully delivered on the first
attempt; every one of these succeeded on retry). No fetch in this build exhausted all 4 retries.

## Timestamp basis (measured, not assumed)

`kline_for_metatrader4` timestamps are **broker/server time = UTC+3**, not UTC. Measured by folding
the 2024-12-31 daily trade file to 1-minute bars (trade timestamps are UTC-native) and comparing
against the 2024-12 monthly kline file's same UTC day, testing correction offsets:

- offset 0h (kline read as UTC, no correction): **0/1440 minutes match**
- offset **-3h** (kline is UTC+3, subtract 3h to get UTC): **1239/1261 overlapping minutes match**
  (H/L/C within 0.5 USDT) = 98.3%. Reproduced independently in this session
  (`python scripts/fetch_bybit_minutes.py --offset-check`) with the identical result, 1239/1261.

**Conclusion: kline_for_metatrader4 timestamps are UTC+3; `fetch_bybit_minutes.py` corrects by -3h at
read time (`KLINE_UTC_OFFSET_HOURS = -3`, `correct_kline_timestamp()`).** The residual 1.7% mismatch
(22/1261 minutes) is attributed to floating-point rounding and trade-order tie-breaks between the two
independently-computed OHLC series, not a further timestamp offset — no other integer-hour offset
gave any material match. Daily trade files carry UTC-native timestamps already (`timestamp` column is
UTC epoch seconds/fractional seconds); no correction applied there.

Because monthly kline files are fetched by broker-time month and then corrected -3h, a UTC year's
first ~3 broker-hours of month M+1 land in UTC month M (and vice versa for the last ~3 hours) — see
`fetch_kline_years()` docstring for the month/year-boundary dedup this requires. This is unrelated to
the gaps below.

## Gaps found and patched (2026-09-11, this session)

The inherited 2022-2024 kline data (commit `2ee154f`) was checked minute-by-minute for internal gaps
before treating "2022-2024 = done, only 2025-2026 remained" as true. Two years had real holes; one had
none:

- **2022: no gaps.** 525,600/525,600 minutes present.
- **2023: one gap, patched.** The source `kline_for_metatrader4` monthly file for December 2023
  (broker time) itself contains only 1,800 of ~44,640 expected lines (first ~30 broker-hours of the
  month only, verified by fetching the raw file directly) — this is a hole in Bybit's own published
  archive, not a fetch bug. Patched by folding the 31 daily trade files for 2023-12-01..2023-12-31 and
  merging (existing kline-derived minutes are kept as-is on collision; only genuinely-absent minutes
  are filled from the trade fold). Result: 2023 now 525,600/525,600, no gaps.
- **2024: three gaps, patched.** The source kline files for broker months January, February, and
  March 2024 are each almost entirely empty (January: 200 lines / ~1 month expected, i.e. only the
  first 20 broker-minutes; March: same pattern; February: data for roughly the first 20 broker-hours
  only) — again a hole in the published source archive, confirmed by direct fetch of each raw file.
  Patched by folding the 91 daily trade files for 2024-01-01..2024-03-31 and merging on the same
  keep-existing-on-collision rule. Also patched a fourth, structural gap: the **last 179 minutes of
  UTC 2024-12-31 (21:00-23:59)** were absent because the kline source is fetched per broker-time year
  and broker year 2024 does not reach into UTC 2024-12-31 21:00-23:59 (that requires broker time
  2025-01-01 00:00-02:59, outside the year-2024 fetch), while the UTC-native trade-fold source for
  2025 starts fresh at UTC 2025-01-01 00:00 and does not reach backward either. Patched by folding the
  single daily trade file for 2024-12-31. Result: 2024 now 527,040/527,040 (leap year), no gaps.
- **2025-2026** (entirely trade-fold, UTC-native by construction): no gaps found, 525,600/525,600
  (2025) and 349,920/349,920 (2026, through 2026-08-31), matching expectation exactly.

All four patches used the identical, already-tested `fetch_trade_days()` / `fold_trades_to_minutes()`
path used for the main 2025-2026 acquisition (`tests/test_k1_bybit_source.py`), just pointed at extra
date ranges. `_merge_and_write_year()`'s existing+new merge keeps the pre-existing row on any
timestamp collision (existing rows are placed before new rows in the pre-sort list, and Python's
stable sort preserves that order for ties), so patching only ever fills genuinely-missing minutes and
never overwrites an already-present kline-derived value with a trade-derived one.

## Checkpointing

`fetch_trade_days()` checkpoints completed days to a file outside the repo (scratchpad), flushing to
the year `.csv.gz` files every 15 days (also at year boundaries and at the end of a run), so an
interrupted run resumes without re-downloading completed days. Not part of this MANIFEST's provenance
claims (it is a resume mechanism, not a data source); mentioned here for anyone re-running the fetch.

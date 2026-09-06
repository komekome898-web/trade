# bitFlyer FX_BTC_JPY continuous 1-minute series, 2026-07-23 .. 2026-09-05

Built 2026-09-06 for phase-2 G2 (docs/PHASE2/G2_DATA_INVENTORY.md task 2). Schema:
`schema/fx_btc_jpy_1m_continuous.json`. Neither source file below was modified.

## Span

**2026-07-23 12:09:00 UTC .. 2026-09-05 13:47:00 UTC** (61,782 rows), spliced from two parts:

- **part A** (`source=frozen_candles_31d_20260823`, 44,657 rows, 2026-07-23 12:09 .. 2026-08-23 12:25):
  `backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz` verbatim. This is the snapshot confirmed
  CORRECT against the executions snapshot (see `schema/candles_fx_btc_jpy.json` known_defects,
  2026-09-06 entry) — the competing `candles_FX_BTC_JPY_30d_20260820.csv` was NOT used anywhere in
  this build.
- **part B** (`source=paper_logs_tape_ws`, 17,125 rows, 2026-08-23 12:26 .. 2026-09-05 13:47):
  `paper_logs/tape/executions_2026{0820..0905}.csv.gz` (17 daily files), each rebuilt into 1-minute
  OHLCV with `scripts/fetch_history.py`'s `build_candles()` (dropna builder: a minute with zero
  executions produces no row, never fabricated), then filtered to `ts >` part A's max ts so the two
  parts never double-cover a minute. (Tape rows for 08-20..08-23, where they'd overlap part A, were
  computed too but discarded — part A already covers that span and is the verified-correct source for
  it.)

## Per-row columns

`ts, open, high, low, close, volume, synthetic, source` — see `schema/fx_btc_jpy_1m_continuous.json`
for full column docs. `synthetic=1` marks the pre-existing zero-volume forward-fill rows inherited from
part A (3,171 rows, reconstructed from the documented rule in `schema/candles_fx_btc_jpy.json`: a
zero-volume row whose OHLC exactly equals its immediate predecessor's). All part-B rows are
`synthetic=0` (its builder never fabricates rows). This count (3,171) was independently cross-checked
against `scripts/data_quality.py`'s own `zero_volume` flag on this same file, which found exactly 3,171
— full agreement.

## Gaps > 5 minutes

17 gaps found by a strict "ts diff > 5min" scan over the assembled series (full list in
`gaps_gt5min.txt`, alongside its count). `scripts/data_quality.py`'s own gap check (median-multiple
based, see its `--summary` output / `data/QUALITY.json` dataset `fx_btc_jpy_1m_continuous`) found 15
using its own heuristic — the same events, grouped slightly differently.

Breakdown:
- **11 gaps of ~13-14 minutes**, each `18:58/18:59 UTC -> 19:12 UTC`: the recurring bitFlyer 19:00 UTC
  maintenance window, also documented for part A in
  `schema/candles_fx_btc_jpy.json`/`docs/PHASE2/G2_DATA_INVENTORY.md`. One per day: 08-23, 08-24,
  08-26, 08-28 through 09-04 (part B; 08-25 and 08-27's maintenance windows fall inside the two
  longer gaps below and so don't show up as separate lines).
- **2 longer gaps**: `2026-08-25 18:29 -> 2026-08-26 02:55` (~8h26m) and
  `2026-08-27 17:57 -> 2026-08-28 04:18` (~10h21m). Both fall in part B (tape); `paper_logs/tape/`
  simply has no rows there. Not root-caused here (see `schema/fx_btc_jpy_1m_continuous.json`
  known_defects) — could be a genuinely quiet market, a WS recorder outage, or an
  `extract_tape.py`/upstream-capture gap; needs the raw `data/ws/` capture for that window to
  distinguish, which this build did not attempt.
- **4 short unexplained gaps** (7-10 min, not maintenance-window-aligned): `2026-08-26 05:09-05:16`,
  `2026-08-30 05:18-05:28`, `2026-09-05 11:17-11:26`, `2026-09-05 11:51-11:58`. All in part B; not
  individually investigated.

## Data quality check

`PYTHONPATH=src python scripts/data_quality.py` was re-run over the full repo (it reads
`data/INTAKE_latest.json`, so `scripts/intake_ledger.py` was run first — see below). Result for this
dataset (`data/QUALITY.json` -> `datasets.fx_btc_jpy_1m_continuous`): 1 file, 1 file flagged, checks
fired: `gaps` (15), `maintenance_window` (90 flat-OHLC rows in the 19:00-19:10 UTC window),
`zero_volume` (3,171 — exactly the `synthetic=1` count above). No `duplicate_keys`, `non_monotonic`,
`crossed_book`, or `extreme_return` hits.

## Intake ledger

`PYTHONPATH=src python scripts/intake_ledger.py --summary` was re-run; it now lists
`backtest_data/fx_btc_jpy_1m_continuous_20260906` (2 files, 61,782 rows,
2026-07-23T12:09:00+00:00 .. 2026-09-05T13:47:00+00:00) in `data/INTAKE_latest.json`.

## Three-way coverage (candles ∧ executions ∧ Binance)

Per-calendar-day coverage across this continuous series, the bitFlyer executions sources (REST
snapshot `backtest_data/executions_FX_BTC_JPY_31d_20260823.csv.gz` for 07-23..08-23, plus
`paper_logs/tape/executions_*.csv.gz` for 08-20..09-05), and
`backtest_data/binance_BTCUSDT_1m_210d_20260820.csv.gz` (2026-01-22..2026-08-20 11:36):

- candles: 45 days (2026-07-23 .. 2026-09-05)
- executions (either source): 45 days (2026-07-23 .. 2026-09-05, full overlap with candles)
- Binance: limited to 2026-01-22 .. 2026-08-20 (211 days total, but only the tail overlaps this window)
- **days with ALL THREE: 29 (2026-07-23 .. 2026-08-20 inclusive)** — Binance's 2026-08-20 11:36 UTC
  end is the binding constraint, matching `docs/PHASE2/G2_DATA_INVENTORY.md`'s "最長連続窓 ≈ 28日"
  estimate (the 29-calendar-day count above is inclusive of the partial first/last day; the
  timestamp-precise window is 2026-07-23 12:09 .. 2026-08-20 11:36, ≈27d23h).

With the new `backtest_data/binance_BTCUSDT_1m_20240101_20260831/` extension (task 3), the Binance
constraint is lifted for any future rebuild wanting a longer three-way window back to 2024 — but this
file was NOT rebuilt against the extended Binance series since bitFlyer executions/candles do not
reach back that far regardless.

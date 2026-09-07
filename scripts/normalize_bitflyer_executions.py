#!/usr/bin/env python3
"""P2-08b: normalize the two bitFlyer FX_BTC_JPY execution sources this repo
holds into one UTC-microsecond schema, split into daily csv.gz files, plus
an overlap diagnostic and a gap list.

Sources:
  - backtest_data/executions_FX_BTC_JPY_31d_20260823.csv.gz
    REST /v1/getexecutions frozen snapshot. columns: id, exec_date, price,
    size, side. exec_date is the EXCHANGE timestamp, ms precision.
    Covers 2026-07-23T12:09:27 .. 2026-08-23T12:25:34 UTC (982,000 rows).
  - paper_logs/tape/executions_YYYYMMDD.csv.gz
    WS lightning_executions_FX_BTC_JPY recording, extracted by
    scripts/extract_tape.py. columns: ts, price, size, side. ts is the
    EXCHANGE timestamp (exec_date from the WS message), sub-ms precision as
    bitFlyer sends it (commonly 7 fractional digits -- truncated to
    microseconds here). NO execution id is carried in this file.

Primary-source rule (matches PREREG.md's calendar seal boundary, 2026-08-23
00:00 UTC): days 2026-07-23..2026-08-22 use REST (real ids); days
2026-08-23..2026-09-06 use WS (no id -- left blank). This is a hard cutover,
not a per-row de-dup across the whole window -- the two sources are instead
cross-checked for the days they both cover (2026-08-20..2026-08-23) via
overlap_check.csv, by a same-window ROW COUNT comparison (not a per-trade
id/composite-key match -- WS carries no execution id, and an exact
(ts, price, size, side) key was tried and rejected because bitFlyer's REST
and WS execution feeds split partial fills at different granularity; see the
code comment at the overlap computation below for the full story).

Output under --out (backtest_data/bitflyer_executions_us_20260723_20260906/):
    executions_YYYYMMDD.csv.gz  -- one per UTC day, columns:
        id, ts_us, side, price, size, source
        id is the bitFlyer execution id (rest days) or blank (ws days).
        ts_us is UTC epoch microseconds.
        source is "rest" or "ws".
    overlap_check.csv  -- per day in the REST/WS overlap window
        (2026-08-20..2026-08-23), raw row counts within that day's exact
        overlapping time span (not whole-day totals -- see the code comment
        by the computation for why a per-trade composite-key match was
        rejected): date, overlap_start_utc, overlap_end_utc,
        rest_count_in_window, ws_count_in_window, count_diff,
        ws_drop_rate_pct (= count_diff / rest_count_in_window)
    gaps.csv  -- every gap > 5 minutes in the chosen daily-primary sequence
        across the full window, columns: gap_start_utc, gap_end_utc,
        duration_s, is_maintenance_window (heuristic: gap overlaps
        18:59-19:12 UTC, bitFlyer's documented daily maintenance)
    README.md -- NOT written by this script (left to the caller)

Usage:
    python scripts/normalize_bitflyer_executions.py \
        --rest backtest_data/executions_FX_BTC_JPY_31d_20260823.csv.gz \
        --ws-dir paper_logs/tape \
        --start 2026-07-23 --end 2026-09-06 \
        --seal-from 2026-08-23 \
        --out backtest_data/bitflyer_executions_us_20260723_20260906
"""
from __future__ import annotations

import argparse
import csv
import gzip
from datetime import datetime, timedelta, timezone
from pathlib import Path

MAINT_START = (18, 59)
MAINT_END = (19, 12)


def parse_rest(path: Path):
    """Yield (day_str, id, ts_us, side, price, size) from the REST snapshot,
    grouped implicitly by day via day_str (caller buckets)."""
    with gzip.open(path, "rt", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dt = datetime.fromisoformat(row["exec_date"]).replace(tzinfo=timezone.utc)
            ts_us = int(dt.timestamp() * 1_000_000)
            day_str = dt.strftime("%Y%m%d")
            yield day_str, int(row["id"]), ts_us, row["side"], row["price"], row["size"]


def parse_ws_day(path: Path):
    """Yield (ts_us, side, price, size) from one paper_logs/tape/executions_*.csv.gz."""
    with gzip.open(path, "rt", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw = row["ts"]
            if raw.endswith("Z"):
                raw = raw[:-1] + "+00:00"
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            ts_us = int(dt.timestamp() * 1_000_000)
            yield ts_us, row["side"], row["price"], row["size"]


def day_range(start: str, end: str):
    d = datetime.strptime(start, "%Y-%m-%d").date()
    e = datetime.strptime(end, "%Y-%m-%d").date()
    while d <= e:
        yield d.strftime("%Y%m%d")
        d += timedelta(days=1)


def write_day(rows: list[tuple], out_csv: Path) -> int:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    rows_sorted = sorted(rows, key=lambda r: r[1])  # by ts_us
    with gzip.open(out_csv, "wt", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "ts_us", "side", "price", "size", "source"])
        for r in rows_sorted:
            w.writerow(r)
    return len(rows_sorted)


MAINT_SLACK_S = 20 * 60  # bitFlyer's maintenance window itself is ~13 min (18:59-19:12 UTC);
                          # a few extra minutes of slack absorbs execution-arrival jitter either
                          # side of it without also swallowing a genuine multi-hour outage that
                          # merely happens to overlap the same clock window.


def overlaps_maintenance(start_dt: datetime, end_dt: datetime) -> bool:
    duration_s = (end_dt - start_dt).total_seconds()
    if duration_s > MAINT_SLACK_S:
        return False  # too long to be the maintenance window itself -- a real outage
    ms, me = MAINT_START, MAINT_END
    day = start_dt.date()
    maint_start = datetime(day.year, day.month, day.day, ms[0], ms[1], tzinfo=timezone.utc)
    maint_end = datetime(day.year, day.month, day.day, me[0], me[1], tzinfo=timezone.utc)
    return start_dt < maint_end and end_dt > maint_start


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rest", required=True)
    ap.add_argument("--ws-dir", required=True)
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD")
    ap.add_argument("--seal-from", required=True, help="YYYY-MM-DD: first day using WS as primary")
    ap.add_argument("--overlap-start", default=None, help="YYYY-MM-DD, default = seal-from minus 3 days")
    ap.add_argument("--overlap-end", default=None, help="YYYY-MM-DD, default = seal-from")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    root = Path(args.out)
    ws_dir = Path(args.ws_dir)
    seal_from = args.seal_from.replace("-", "")

    # --- bucket REST rows by day ---------------------------------------
    rest_by_day: dict[str, list] = {}
    for day_str, id_, ts_us, side, price, size in parse_rest(Path(args.rest)):
        rest_by_day.setdefault(day_str, []).append((id_, ts_us, side, price, size, "rest"))

    days = list(day_range(args.start, args.end))

    # --- write daily unified files per the primary-source rule ---------
    n_written = {}
    for day_str in days:
        if day_str < seal_from:
            rows = rest_by_day.get(day_str, [])
        else:
            ws_path = ws_dir / f"executions_{day_str}.csv.gz"
            rows = []
            if ws_path.exists():
                for ts_us, side, price, size in parse_ws_day(ws_path):
                    rows.append(("", ts_us, side, price, size, "ws"))
        out_csv = root / f"executions_{day_str}.csv.gz"
        n = write_day(rows, out_csv)
        n_written[day_str] = n
        print(f"{day_str}: {n} rows ({'rest' if day_str < seal_from else 'ws'})")

    # --- overlap_check.csv: same-window count comparison on shared days ---
    # NOTE: an earlier version of this script tried a composite-key
    # (ts-ms, side, price, size) multiset match between REST and WS to get
    # a true matched/rest-only/ws-only breakdown. That produced a spurious
    # ~70% "drop rate" -- inspection showed bitFlyer's WS lightning_executions
    # stream and its REST /v1/getexecutions snapshot split partial fills at
    # DIFFERENT granularity (one taker order can appear as one REST row but
    # several WS rows with different size fractions, or vice versa), so an
    # exact-size key match is not a valid same-trade test between the two
    # sources. WS also carries no execution id at all, so there is no exact
    # join key available. Falling back to the audit's own, more defensible
    # method (docs/PHASE2/P2-08b/PROCUREMENT.md): compare RAW ROW COUNTS
    # within the exact overlapping time span of that day (not whole-day
    # totals, which would conflate the WS recorder's coverage start/end
    # with a real drop) -- reproduces the audit's cited 08-21/08-22 figures.
    overlap_start = (args.overlap_start or "").replace("-", "") or None
    overlap_end = (args.overlap_end or "").replace("-", "") or seal_from
    overlap_rows = []
    for day_str in days:
        ws_path = ws_dir / f"executions_{day_str}.csv.gz"
        has_rest = day_str in rest_by_day
        has_ws = ws_path.exists()
        if not (has_rest and has_ws):
            continue
        if overlap_start and day_str < overlap_start:
            continue
        if day_str > overlap_end:
            continue

        rest_ts = [ts_us for (_id, ts_us, _side, _price, _size, _src) in rest_by_day[day_str]]
        ws_rows_day = list(parse_ws_day(ws_path))
        ws_ts = [ts_us for (ts_us, _side, _price, _size) in ws_rows_day]
        lo = max(min(rest_ts), min(ws_ts))
        hi = min(max(rest_ts), max(ws_ts))
        rest_n = sum(1 for t in rest_ts if lo <= t <= hi)
        ws_n = sum(1 for t in ws_ts if lo <= t <= hi)
        diff = rest_n - ws_n
        drop_pct = (diff / rest_n * 100.0) if rest_n else None
        overlap_rows.append({
            "date": day_str,
            "overlap_start_utc": datetime.fromtimestamp(lo / 1_000_000.0, tz=timezone.utc).isoformat(),
            "overlap_end_utc": datetime.fromtimestamp(hi / 1_000_000.0, tz=timezone.utc).isoformat(),
            "rest_count_in_window": rest_n, "ws_count_in_window": ws_n,
            "count_diff": diff,
            "ws_drop_rate_pct": f"{drop_pct:.3f}" if drop_pct is not None else "",
        })
        print(f"overlap {day_str}: window=[{lo},{hi}] rest={rest_n} ws={ws_n} diff={diff} drop%={drop_pct}")

    overlap_csv = root / "overlap_check.csv"
    with overlap_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "overlap_start_utc", "overlap_end_utc",
                                           "rest_count_in_window", "ws_count_in_window",
                                           "count_diff", "ws_drop_rate_pct"])
        w.writeheader()
        for r in overlap_rows:
            w.writerow(r)

    # --- gaps.csv: >5min gaps in the chosen daily-primary sequence -------
    all_ts = []
    for day_str in days:
        p = root / f"executions_{day_str}.csv.gz"
        if not p.exists():
            continue
        with gzip.open(p, "rt", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                all_ts.append(int(row["ts_us"]))
    all_ts.sort()
    gap_rows = []
    for a, b in zip(all_ts, all_ts[1:]):
        dur_s = (b - a) / 1_000_000.0
        if dur_s > 300:
            start_dt = datetime.fromtimestamp(a / 1_000_000.0, tz=timezone.utc)
            end_dt = datetime.fromtimestamp(b / 1_000_000.0, tz=timezone.utc)
            gap_rows.append({
                "gap_start_utc": start_dt.isoformat(), "gap_end_utc": end_dt.isoformat(),
                "duration_s": f"{dur_s:.1f}",
                "is_maintenance_window": overlaps_maintenance(start_dt, end_dt),
            })
    gaps_csv = root / "gaps.csv"
    with gaps_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["gap_start_utc", "gap_end_utc", "duration_s", "is_maintenance_window"])
        w.writeheader()
        for r in gap_rows:
            w.writerow(r)

    print(f"wrote {len(days)} daily files, {len(overlap_rows)} overlap rows, {len(gap_rows)} gaps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

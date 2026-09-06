#!/usr/bin/env python3
"""Combine raw bitFlyer lightchart pages (scripts/fetch_bitflyer_lightchart.py
output) into one sorted, deduplicated candles_1m.csv.gz, plus a gap list
(>5min between consecutive non-null bars, summarized per year) and MD5SUMS.

Pure offline consolidation: reads only raw/page_*.json already on disk,
makes no network request. This is also what
`scripts/fetch_bitflyer_lightchart.py --rebuild` calls.

Usage:
    python scripts/build_bitflyer_lightchart_csv.py --dir backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906
    python scripts/build_bitflyer_lightchart_csv.py --dir <dir> --md5-only   # just refresh MD5SUMS
                                                                              # (e.g. after adding README.md)
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

COLUMNS = ["ts", "open", "high", "low", "close", "volume",
           "col7_inferred_long_oi", "col8_inferred_short_oi",
           "buy_volume", "sell_volume"]


def write_md5sums(root: Path) -> Path:
    """(Re)write MD5SUMS for every file under root (raw pages + outputs)."""
    md5_file = root / "MD5SUMS"
    with md5_file.open("w") as f:
        for p in sorted(root.rglob("*")):
            if p.is_dir() or p.name == "MD5SUMS":
                continue
            h = hashlib.md5(p.read_bytes()).hexdigest()
            f.write(f"{h}  {p.relative_to(root)}\n")
    return md5_file


def rebuild(root: Path, write_md5: bool = True) -> dict:
    """Rebuild candles_1m.csv.gz + gaps_gt5min.txt (+ MD5SUMS) from raw/
    pages already on disk under `root`. Network-free. Returns a stats dict
    for callers that want to fold numbers into a README."""
    raw_dir = root / "raw"
    rows: dict[int, list] = {}
    n_pages = 0
    for f in sorted(raw_dir.glob("page_*.json")):
        n_pages += 1
        data = json.loads(f.read_text())
        for r in data:
            rows[r[0]] = r

    if not rows:
        raise SystemExit(f"no rows found under {raw_dir} -- nothing to rebuild")

    ts_sorted = sorted(rows.keys())
    out_csv = root / "candles_1m.csv.gz"
    with gzip.open(out_csv, "wt", newline="") as f:
        f.write(",".join(COLUMNS) + "\n")
        for ts in ts_sorted:
            r = rows[ts]
            iso = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat()
            vals = [iso] + ["" if v is None else v for v in r[1:]]
            f.write(",".join(str(v) for v in vals) + "\n")

    # gap list: consecutive *real* (non-null) bars more than 5 minutes apart
    real_ts = [ts for ts in ts_sorted if rows[ts][4] is not None]
    gaps = []
    for a, b in zip(real_ts, real_ts[1:]):
        gap_min = (b - a) / 60000
        if gap_min > 5:
            gaps.append((a, b, gap_min))

    per_year = Counter()
    per_year_minutes = Counter()
    for a, b, m in gaps:
        year = datetime.fromtimestamp(a / 1000, tz=timezone.utc).year
        per_year[year] += 1
        per_year_minutes[year] += m

    gap_file = root / "gaps_gt5min.txt"
    with gap_file.open("w") as f:
        f.write(f"{len(gaps)} gaps > 5 minutes between consecutive real (non-null) bars\n\n")
        f.write("Per-year summary (count, total gap minutes):\n")
        for year in sorted(per_year):
            f.write(f"  {year}: {per_year[year]:4d} gaps, {per_year_minutes[year]:10.1f} min total\n")
        f.write("\nFull list:\n")
        for a, b, m in gaps:
            fa = datetime.fromtimestamp(a / 1000, tz=timezone.utc).isoformat()
            fb = datetime.fromtimestamp(b / 1000, tz=timezone.utc).isoformat()
            f.write(f"{fa} -> {fb}  ({m:.1f} min)\n")

    null_bars = sum(1 for ts in ts_sorted if rows[ts][4] is None)

    stats = {
        "n_pages": n_pages,
        "n_rows": len(ts_sorted),
        "null_bars": null_bars,
        "n_gaps": len(gaps),
        "gaps_per_year": dict(sorted(per_year.items())),
        "gap_minutes_per_year": dict(sorted(per_year_minutes.items())),
        "range_start": datetime.fromtimestamp(ts_sorted[0] / 1000, tz=timezone.utc).isoformat(),
        "range_end": datetime.fromtimestamp(ts_sorted[-1] / 1000, tz=timezone.utc).isoformat(),
        "out_csv": str(out_csv),
        "gap_file": str(gap_file),
    }

    print(f"pages={n_pages} rows={len(ts_sorted)} null_bars={null_bars} gaps>5min={len(gaps)}")
    print(f"range: {stats['range_start']} .. {stats['range_end']}")
    print(f"wrote {out_csv}")
    print(f"wrote {gap_file}")

    if write_md5:
        md5_file = write_md5sums(root)
        stats["md5_file"] = str(md5_file)
        print(f"wrote {md5_file}")

    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--md5-only", action="store_true",
                     help="skip the CSV/gap rebuild, just (re)write MD5SUMS "
                          "(e.g. after adding/editing README.md)")
    args = ap.parse_args()

    root = Path(args.dir)
    if args.md5_only:
        write_md5sums(root)
        print(f"wrote {root / 'MD5SUMS'}")
        return 0

    rebuild(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

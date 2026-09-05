#!/usr/bin/env python3
"""Seal the evaluation data for one phase-2 research unit (docs/PHASE2_SPEC.md
§3), BEFORE any iteration on that unit begins.

For each input file this computes:
  * the last 30% of its time span, split by CALENDAR date (not row count) —
    the boundary is the calendar date at which 70% of [first_date, last_date]
    has elapsed;
  * its MD5 (so a later change to the file is at least detectable);
and writes backtest_data/phase2_sealed/<unit>/SEALED.json, which
bot.research.sealed.load_unsealed / load_sealed treat as the source of truth
for what is sealed.

This script only OPENS files for reading (to hash them and scan their time
column) — it never copies, moves, rewrites, or deletes anything under
data/ or backtest_data/.

Usage:
  PYTHONPATH=src python scripts/phase2_seal.py --unit g1_taker \\
      --files data/candles_FX_BTC_JPY.csv data/oi_snapshots.csv

  PYTHONPATH=src python scripts/phase2_seal.py --unit g1_taker \\
      --dataset candles_fx_btc_jpy
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bot.research.sealed import (  # noqa: E402
    SealedDataError,
    calendar_seal_boundary,
    md5_of,
    read_timestamps,
    resolve_dataset_files,
    seal_dir,
    seal_path,
)


def build_seal(unit: str, files: list[Path], root: Path, now: datetime) -> dict:
    forward_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    file_records = []
    for path in files:
        path = path if path.is_absolute() else root / path
        if not path.is_file():
            raise SealedDataError(f"not a file: {path}")
        col_name, timestamps = read_timestamps(path)
        seal_from = calendar_seal_boundary(timestamps)
        rel = path.resolve().relative_to(root.resolve())
        file_records.append({
            "path": str(rel),
            "md5": md5_of(path),
            "time_column": col_name,
            "first_ts": min(timestamps).isoformat(),
            "last_ts": max(timestamps).isoformat(),
            "seal_from_ts": seal_from.isoformat(),
        })
    return {
        "unit": unit,
        "created_utc": now.isoformat(),
        "forward_start": forward_start.isoformat(),
        "files": file_records,
        "rule": "everything with ts >= forward_start is sealed",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--unit", required=True, help="research unit name")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--files", nargs="+", help="explicit list of data files")
    src.add_argument("--dataset", help="schema/<dataset>.json path_glob resolves the files")
    parser.add_argument("--root", default=".", help="repo root (default: cwd)")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if args.dataset:
        files = resolve_dataset_files(args.dataset, root)
        if not files:
            print(f"no existing files matched schema/{args.dataset}.json's path_glob "
                  f"under {root}", file=sys.stderr)
            return 1
    else:
        files = [Path(f) for f in args.files]

    now = datetime.now(timezone.utc)
    try:
        record = build_seal(args.unit, files, root, now)
    except SealedDataError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    out_dir = seal_dir(args.unit, root)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = seal_path(args.unit, root)
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(f"sealed {len(record['files'])} file(s) for unit {args.unit!r} -> {out_path}")
    for entry in record["files"]:
        print(f"  {entry['path']}: [{entry['first_ts']} .. {entry['last_ts']}], "
              f"sealed from {entry['seal_from_ts']}")
    print(f"forward_start: {record['forward_start']} "
          f"(everything with ts >= forward_start is sealed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

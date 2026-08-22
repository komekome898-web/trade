#!/usr/bin/env python3
"""Extract EXECUTIONS-channel events from data/ws/*.jsonl.gz WS recordings
into compact, git-shareable daily CSVs (data/tape/executions_YYYYMMDD.csv.gz).

Why this exists: bitFlyer's public execution-history REST endpoint only
retains ~31 days (see CLAUDE.md / docs/OPERATIONS.md). The WS recorder
(src/bot/market_data/realtime.py, run via scripts/record_realtime.py)
already captures every execution at millisecond cadence, but its raw
jsonl.gz interleaves board snapshots/diffs and ticker messages and is too
large to share via git — deploy/share_logs.bat only lists data/ws, it does
not copy it. This script pulls just the executions out into tiny per-day
CSVs that ARE small enough to share and accumulate: a permanent tape of
fresh executions, past the 31-day API window, feeding the fast-cycle
judgment.

Output columns: ts, price, size, side
    ts    exchange exec_date, ISO-8601 UTC, microsecond precision
    price execution price (JPY)
    size  execution size (BTC)
    side  BUY or SELL (taker side, as reported by bitFlyer)

Idempotent: a manifest (data/tape/manifest.json) tracks how many
well-formed lines of each source .jsonl.gz have already been extracted, so
re-running only advances files that grew (or are new) and never re-emits a
line already captured. A source file still being actively written by the
recorder is skipped for the run entirely when its mtime is younger than
--min-age-sec (default 60s) — its already-good lines get picked up once it
goes quiet for a beat, and the same guard means a torn last line (a write
caught mid-flush) or a truncated gzip tail (recorder killed mid-member) is
never treated as the end of the file's data: extraction simply stops at the
first line it cannot parse, without advancing the manifest past it, so the
next run resumes there and repeats the same well-formed lines it already
had until new complete ones arrive.

Usage:
    python scripts/extract_tape.py                     # scan data/ws, write data/tape
    python scripts/extract_tape.py --min-age-sec 0      # also touch fresh files (tests)
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
import time
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WS_DIR = ROOT / "data" / "ws"
DEFAULT_OUT_DIR = ROOT / "data" / "tape"

FIELDS = ["ts", "price", "size", "side"]
EXEC_CHANNEL_PREFIX = "lightning_executions_"
DEFAULT_MIN_AGE_SEC = 60.0

# Raised by gzip/zlib when the compressed stream stops short (truncated
# tail from a live/killed recorder). gzip.BadGzipFile is an OSError.
_TRUNCATED_GZ_ERRORS = (EOFError, OSError, zlib.error)


def _load_manifest(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_manifest(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=0, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _rows_from_message(obj: dict):
    """Yield (YYYYMMDD, [ts, price, size, side]) for each execution carried
    by one recorded WS line, or nothing if it is not an executions message."""
    m = obj.get("m")
    if not isinstance(m, dict):
        return
    params = m.get("params")
    if not isinstance(params, dict):
        return
    channel = params.get("channel")
    if not isinstance(channel, str) or not channel.startswith(EXEC_CHANNEL_PREFIX):
        return
    message = params.get("message")
    if not isinstance(message, list):
        return
    for exe in message:
        if not isinstance(exe, dict):
            continue
        ts = exe.get("exec_date")
        price = exe.get("price")
        size = exe.get("size")
        side = exe.get("side")
        if not isinstance(ts, str) or len(ts) < 10 or price is None or size is None or side is None:
            continue
        date_str = ts[:10].replace("-", "")
        if len(date_str) != 8 or not date_str.isdigit():
            continue
        yield date_str, [ts, price, size, side]


def _extract_file(gz_path: Path, skip_lines: int):
    """Parse gz_path from line skip_lines onward. Stops at the first line
    that fails to parse (torn write) or the first decompression error
    (truncated gzip tail); either way, whatever parsed cleanly before that
    point is kept and counted. Returns (rows_by_date, new_line_count) where
    new_line_count is the total number of well-formed lines now behind us
    (>= skip_lines), to store back into the manifest."""
    rows_by_date: dict[str, list[list[str]]] = {}
    good_lines = skip_lines
    try:
        with gzip.open(gz_path, "rt", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i < skip_lines:
                    continue
                line = line.strip()
                if not line:
                    good_lines = i + 1
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    break  # torn line -- do not advance past it
                for date_str, row in _rows_from_message(obj):
                    rows_by_date.setdefault(date_str, []).append(row)
                good_lines = i + 1
    except _TRUNCATED_GZ_ERRORS:
        pass  # truncated gz tail -- keep whatever parsed before it
    return rows_by_date, good_lines


def _append_rows(out_dir: Path, date_str: str, rows: list[list[str]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"executions_{date_str}.csv.gz"
    write_header = not out_path.exists()
    mode = "wt" if write_header else "at"
    # gzip appends as a new concatenated member; reading transparently
    # decompresses all members back into one stream (verified: multistream
    # .gz is standard and gzip.open('rt') walks every member).
    with gzip.open(out_path, mode, encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        if write_header:
            writer.writerow(FIELDS)
        writer.writerows(rows)


def run(ws_dir: Path, out_dir: Path, manifest_path: Path,
        min_age_sec: float = DEFAULT_MIN_AGE_SEC) -> tuple[int, int]:
    """Returns (files_advanced, rows_written)."""
    manifest = _load_manifest(manifest_path)
    now = time.time()
    files_advanced = 0
    rows_written = 0

    for gz_path in sorted(ws_dir.glob("*.jsonl.gz")):
        try:
            mtime = gz_path.stat().st_mtime
        except OSError:
            continue
        if now - mtime < min_age_sec:
            continue  # still being written -- come back next run

        key = gz_path.name
        skip_lines = manifest.get(key, {}).get("lines", 0)
        rows_by_date, new_lines = _extract_file(gz_path, skip_lines)
        if new_lines <= skip_lines and not rows_by_date:
            continue  # no new well-formed lines this pass

        for date_str, rows in rows_by_date.items():
            _append_rows(out_dir, date_str, rows)
            rows_written += len(rows)

        manifest[key] = {"lines": new_lines, "mtime": mtime}
        files_advanced += 1
        _save_manifest(manifest_path, manifest)  # incremental: safe on crash

    return files_advanced, rows_written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ws-dir", default=str(DEFAULT_WS_DIR))
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--manifest", default=None,
                     help="default: <out-dir>/manifest.json")
    ap.add_argument("--min-age-sec", type=float, default=DEFAULT_MIN_AGE_SEC,
                     help="skip source files modified more recently than this "
                          "(likely still being written); default 60s")
    args = ap.parse_args(argv)

    ws_dir = Path(args.ws_dir)
    out_dir = Path(args.out_dir)
    manifest_path = Path(args.manifest) if args.manifest else out_dir / "manifest.json"

    if not ws_dir.is_dir():
        print(f"extract_tape: no {ws_dir}, nothing to do")
        return 0

    files_advanced, rows_written = run(ws_dir, out_dir, manifest_path, args.min_age_sec)
    print(f"extract_tape: {files_advanced} file(s) advanced, "
          f"{rows_written} execution row(s) written")
    return 0


if __name__ == "__main__":
    sys.exit(main())

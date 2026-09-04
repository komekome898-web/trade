#!/usr/bin/env python3
"""Round 17 (docs/PREREG_board_round.md, section 0) -- board reconstruction.

Replays every `data/ws/*.jsonl.gz` WS recording ONCE, file by file, and
writes the pre-registered 5-second derived series
(`data/board_round/series_5s.csv.gz`) plus a coverage report
(`data/board_round/coverage.json`). This is reconstruction only: it computes
NO statistics, tests NO hypothesis, and reads no venue data. The judgment
(docs/PREREG_board_round.md sections 1-4) lives entirely in
`scripts/judge_board_round.py`, which reads only the series this script
writes.

Runs on the owner's PC where `data/ws` actually lives (~1 GB / 68 files as
of the freeze). Memory-safe by construction: `bot.research.board.iter_messages`
streams one gzip line at a time and files are processed one at a time in
filename order (filenames embed the UTC session-start timestamp, so this is
chronological); nothing ever holds more than one file's raw bytes. The
output series itself is small (~8 MB gz) and is accumulated in memory before
being written once.

Columns (UTC, 5-second bins, PREREG section 0 verbatim):
    ts, mid, spread_bps, best_bid_size, best_ask_size,
    bid_depth_5bps, ask_depth_5bps, imb_top, imb_5bps,
    n_board_updates, n_trades, vol_buy, vol_sell,
    n_large, vol_large, max_trade_size

Each row holds the book STATE as of the end of the bin (last message in the
bin) plus aggregates of everything that happened DURING the bin. A bin with
no messages at all inside an otherwise-live recording still gets a row: the
book state is carried forward (nothing changed) and the aggregates are zero
-- this is not a guess, it is the literal statement "no update happened". A
recording gap longer than 60 seconds (maintenance, reconnect, recorder
restarted) is different: bins inside a >60s gap are MISSING (no row at all),
exactly as PREREG section 0 specifies ("60秒超の記録ギャップはビンを欠測に
し"). Gap detection uses the timestamp of every consumed message (board
snapshot/diff and executions alike) across the whole run, uninterrupted by
file boundaries -- a gap that happens to straddle two files (recorder
restarted into a new file) is detected the same way as a gap inside one
file.

`imb_top` = top-of-book imbalance, (best_bid_size - best_ask_size) /
(best_bid_size + best_ask_size); `imb_5bps` = the same formula on depth
within 5 bps of mid (`BookState.imbalance(5.0)`). `large` = a single
execution >= 0.1 BTC.

Idempotent: each run is a full rebuild from `data/ws` (or `--root`'s ws
dir); output files are simply overwritten. No incremental state.

Usage:
    PYTHONPATH=src python scripts/run_board_round.py [--root PATH]
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bot.research.board import BookState, is_diff_channel, is_snapshot_channel  # noqa: E402

BIN_SEC = 5.0
DEPTH_BPS = 5.0
MAX_GAP_SEC = 60.0
LARGE_SIZE = 0.1  # BTC

COLUMNS = [
    "ts", "mid", "spread_bps", "best_bid_size", "best_ask_size",
    "bid_depth_5bps", "ask_depth_5bps", "imb_top", "imb_5bps",
    "n_board_updates", "n_trades", "vol_buy", "vol_sell",
    "n_large", "vol_large", "max_trade_size",
]


def _iter_all_messages(path: Path):
    """(rts, channel, message) for every channelMessage frame in one file.

    A local, tolerant re-implementation of
    `bot.research.board.iter_messages` that also yields
    `lightning_executions_*` frames (the shared helper is board-channel
    only). Truncated / mid-write files are read up to the last complete
    line, never raising.
    """
    try:
        with gzip.open(path, "rt") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                msg = rec.get("m")
                if not isinstance(msg, dict) or msg.get("method") != "channelMessage":
                    continue
                params = msg.get("params") or {}
                channel = params.get("channel")
                message = params.get("message")
                if channel is None or message is None:
                    continue
                yield float(rec["rts"]), channel, message
    except (EOFError, gzip.BadGzipFile, OSError):
        return


def _empty_agg() -> dict:
    return {
        "n_board_updates": 0,
        "n_trades": 0,
        "vol_buy": 0.0,
        "vol_sell": 0.0,
        "n_large": 0,
        "vol_large": 0.0,
        "max_trade_size": None,
    }


def _snapshot_row(bin_idx: int, state: BookState, agg: dict) -> list:
    best_bid, best_ask = state.best_bid, state.best_ask
    bb_size = state.bids.get(best_bid, 0.0) if best_bid is not None else float("nan")
    ba_size = state.asks.get(best_ask, 0.0) if best_ask is not None else float("nan")
    if best_bid is None or best_ask is None:
        bb_size = ba_size = float("nan")
    mid = state.mid
    spread = state.spread
    spread_bps = (spread / mid * 1e4) if (mid and mid > 0 and spread is not None) else float("nan")
    bid_depth, ask_depth = state.depth_within_bps(DEPTH_BPS)
    imb_5bps = state.imbalance(DEPTH_BPS)
    if bb_size == bb_size and ba_size == ba_size and (bb_size + ba_size) > 0:
        imb_top = (bb_size - ba_size) / (bb_size + ba_size)
    else:
        imb_top = 0.0
    ts = bin_idx * BIN_SEC
    return [
        ts,
        float("nan") if mid is None else mid,
        spread_bps,
        bb_size,
        ba_size,
        bid_depth,
        ask_depth,
        imb_top,
        imb_5bps,
        agg["n_board_updates"],
        agg["n_trades"],
        agg["vol_buy"],
        agg["vol_sell"],
        agg["n_large"],
        agg["vol_large"],
        float("nan") if agg["max_trade_size"] is None else agg["max_trade_size"],
    ]


def build(ws_dir: Path):
    """Stream every ws file once; return (rows, coverage_dict)."""
    paths = sorted(ws_dir.glob("*.jsonl.gz"), key=lambda p: p.name)
    rows: list[list] = []
    gaps: list[dict] = []
    files_read: list[str] = []

    state = BookState()
    agg = _empty_agg()
    current_bin: int | None = None
    last_rts: float | None = None
    first_row_bin: int | None = None
    last_row_bin: int | None = None

    def flush_current():
        nonlocal current_bin, agg, first_row_bin, last_row_bin
        if current_bin is None or not state.ready:
            return
        row = _snapshot_row(current_bin, state, agg)
        rows.append(row)
        if first_row_bin is None:
            first_row_bin = current_bin
        last_row_bin = current_bin
        agg = _empty_agg()

    def advance_quiet_bins(target_bin: int):
        """Fill bins strictly between current_bin and target_bin with
        carried-forward state and zero aggregates (same segment, no gap)."""
        nonlocal current_bin
        if current_bin is None or not state.ready:
            current_bin = target_bin
            return
        b = current_bin + 1
        while b < target_bin:
            rows.append(_snapshot_row(b, state, _empty_agg()))
            nonlocal_last(b)
            b += 1
        current_bin = target_bin

    def nonlocal_last(b: int):
        nonlocal first_row_bin, last_row_bin
        if first_row_bin is None:
            first_row_bin = b
        last_row_bin = b

    for path in paths:
        n_before = len(rows)
        for rts, channel, message in _iter_all_messages(path):
            if last_rts is not None and (rts - last_rts) > MAX_GAP_SEC:
                flush_current()
                gaps.append({
                    "start": last_rts,
                    "end": rts,
                    "duration_sec": rts - last_rts,
                })
                current_bin = None  # next message opens a fresh segment
            last_rts = rts

            bin_idx = int(rts // BIN_SEC)
            if current_bin is None:
                current_bin = bin_idx
            elif bin_idx != current_bin:
                flush_current()
                advance_quiet_bins(bin_idx)

            if is_snapshot_channel(channel):
                state.apply_snapshot(message)
                agg["n_board_updates"] += 1
            elif is_diff_channel(channel):
                if state.ready:
                    state.apply_diff(message)
                    agg["n_board_updates"] += 1
            elif "executions" in channel:
                for ex in message or ():
                    try:
                        size = float(ex["size"])
                        side = ex.get("side")
                    except (KeyError, TypeError, ValueError):
                        continue
                    agg["n_trades"] += 1
                    if side == "BUY":
                        agg["vol_buy"] += size
                    elif side == "SELL":
                        agg["vol_sell"] += size
                    if agg["max_trade_size"] is None or size > agg["max_trade_size"]:
                        agg["max_trade_size"] = size
                    if size >= LARGE_SIZE:
                        agg["n_large"] += 1
                        agg["vol_large"] += size
            # ticker channel: not part of the derived series, ignored here.

        files_read.append(path.name)
        print(f"[run_board_round] {path.name}: +{len(rows) - n_before} rows "
              f"(total {len(rows)})", flush=True)

    flush_current()

    total_bins = 0 if first_row_bin is None else (last_row_bin - first_row_bin + 1)
    missing_bins = total_bins - len(rows)
    coverage = {
        "files_read": files_read,
        "first_ts": None if first_row_bin is None else _iso(first_row_bin * BIN_SEC),
        "last_ts": None if last_row_bin is None else _iso(last_row_bin * BIN_SEC),
        "total_bins": total_bins,
        "missing_bins": missing_bins,
        "bin_sec": BIN_SEC,
        "gaps_over_60s": [
            {
                "start": _iso(g["start"]),
                "end": _iso(g["end"]),
                "duration_sec": g["duration_sec"],
            }
            for g in gaps
        ],
    }
    return rows, coverage


def _iso(epoch_sec: float) -> str:
    import datetime
    return (datetime.datetime.fromtimestamp(epoch_sec, tz=datetime.timezone.utc)
            .isoformat().replace("+00:00", "Z"))


def write_csv_gz(rows: list[list], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    import csv
    with gzip.open(path, "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        for row in rows:
            ts_row = list(row)
            ts_row[0] = _iso(row[0])
            w.writerow(ts_row)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]),
                     help="repo root; ws files read from <root>/data/ws, "
                          "output written under <root>/data/board_round")
    args = ap.parse_args()
    root = Path(args.root)
    ws_dir = root / "data" / "ws"
    out_dir = root / "data" / "board_round"

    if not ws_dir.is_dir():
        print(f"no ws dir at {ws_dir}", file=sys.stderr)
        return 1

    print(f"[run_board_round] scanning {ws_dir}")
    rows, coverage = build(ws_dir)
    print(f"[run_board_round] {len(rows):,} bins written, "
          f"{coverage['missing_bins']:,} missing of {coverage['total_bins']:,} "
          f"total, {len(coverage['gaps_over_60s'])} gaps > 60s")

    series_path = out_dir / "series_5s.csv.gz"
    write_csv_gz(rows, series_path)
    coverage_path = out_dir / "coverage.json"
    coverage_path.write_text(json.dumps(coverage, indent=2, ensure_ascii=False))
    print(f"[run_board_round] wrote {series_path}")
    print(f"[run_board_round] wrote {coverage_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

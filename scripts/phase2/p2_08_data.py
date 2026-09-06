#!/usr/bin/env python
"""P2-08 data loader — the DEVELOPMENT SET only, through the seal.

Reads the bitFlyer lightchart yearly files and the Binance yearly files with
`bot.research.sealed.load_unsealed(path, "P2-08")` (the sealed window from
2023-12-18 and the forward window are removed by the loader, never by this
script) and aligns both onto UTC minute indexes.

Usage:  PYTHONPATH=src python scripts/phase2/p2_08_data.py --summary
        (prints the dev-set overview: rows, empty minutes, big gaps per year)

`load_dev_frames()` is the import for research scripts:

    from scripts.phase2.p2_08_data import load_dev_frames
    bf, bn = load_dev_frames()      # both indexed by tz-aware UTC minute start

`bf`   lightchart FX_BTC_JPY 1m: open/high/low/close (NaN on empty minutes,
       rows as in the files -- absent minutes stay absent; `simulate`
       re-grids), volume, buy_volume, sell_volume.
`bn`   Binance BTCUSDT 1m: open/high/low/close/volume.
Both restricted to DEV_START .. DEV_END (2017-08-17 .. 2023-12-17 inclusive).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from bot.research.sealed import load_unsealed  # noqa: E402
from bot.research.xborder_p2 import big_gaps, misprint_mask, to_minute_grid  # noqa: E402

UNIT = "P2-08"
BF_DIR = "backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906"
BN_DIR = "backtest_data/binance_BTCUSDT_1m_20170801_20231231"
DEV_START = pd.Timestamp("2017-08-17 00:00:00", tz="UTC")
DEV_END = pd.Timestamp("2023-12-17 23:59:00", tz="UTC")      # inclusive (PREREG 開発セット)
DEV_YEARS = tuple(range(2017, 2024))
BF_COLS = ["open", "high", "low", "close", "volume", "buy_volume", "sell_volume"]
BN_COLS = ["open", "high", "low", "close", "volume"]


def _one_year(path: str, time_col: str, cols: list[str], root: Path) -> pd.DataFrame:
    df = load_unsealed(path, UNIT, root=root)
    ts = pd.to_datetime(df[time_col], utc=True)
    out = df[[c for c in cols if c in df.columns]].astype(float)
    out.index = pd.DatetimeIndex(ts)
    return out


def _finish(parts: list[pd.DataFrame], start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    df = pd.concat(parts).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    df = df.loc[(df.index >= start) & (df.index <= end)]
    df.index.name = "ts"
    return df


def load_dev_frames(root: Path | str = REPO_ROOT, years=DEV_YEARS,
                    start: pd.Timestamp = DEV_START, end: pd.Timestamp = DEV_END
                    ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(bitFlyer frame, Binance frame) for the development set, via the seal."""
    root = Path(root)
    bf = _finish([_one_year(f"{BF_DIR}/candles_1m_{y}.csv.gz", "ts", BF_COLS, root)
                  for y in years], start, end)
    bn = _finish([_one_year(f"{BN_DIR}/binance_BTCUSDT_1m_{y}.csv.gz", "open_time", BN_COLS, root)
                  for y in years], start, end)
    return bf, bn


# ---------------------------------------------------------------------------
# summary (開発セット概況)
# ---------------------------------------------------------------------------

def summarize(bf: pd.DataFrame, bn: pd.DataFrame, max_gap_min: int = 5) -> dict:
    """Per-year counts for the dev set. Nothing here touches sealed rows: the
    frames come from `load_unsealed`."""
    years = sorted(set(bf.index.year) | set(bn.index.year))
    grid = to_minute_grid(bf)
    valid_grid = ~grid[["open", "high", "low", "close"]].isna().any(axis=1)
    empty_rows = bf[["open", "high", "low", "close"]].isna().all(axis=1)
    gaps = big_gaps(bf, max_gap_min)
    gap_year = pd.DatetimeIndex(gaps["t_a"]).year if len(gaps) else np.array([], dtype=int)
    mp = misprint_mask(grid)
    bn_grid_n = {}
    if len(bn):
        for y in years:
            sub = bn[bn.index.year == y]
            if len(sub):
                bn_grid_n[y] = int((sub.index[-1] - sub.index[0]) / pd.Timedelta(minutes=1)) + 1
    rows = []
    for y in years:
        by = bf.index.year == y
        gy = grid.index.year == y
        n_rows = int(by.sum())
        n_empty = int(empty_rows[by].sum())
        n_grid = int(gy.sum())
        n_absent = n_grid - n_rows
        n_valid = int(valid_grid[gy].sum())
        gk = gaps[gap_year == y] if len(gaps) else gaps
        bny = bn.index.year == y
        rows.append({
            "year": y,
            "bf_rows": n_rows,
            "bf_empty_rows": n_empty,
            "bf_absent_minutes": n_absent,
            "bf_valid_bars": n_valid,
            "bf_empty_share": (n_grid - n_valid) / n_grid if n_grid else float("nan"),
            "bf_big_gaps": int(len(gk)),
            "bf_big_gaps_empty_rows": int((gk["kind"] == "empty_rows").sum()) if len(gk) else 0,
            "bf_big_gaps_time_jump": int((gk["kind"] == "time_jump").sum()) if len(gk) else 0,
            "bf_big_gap_minutes_missing": int(gk["missing_min"].sum()) if len(gk) else 0,
            "bf_misprint_rows": int(mp[gy].sum()),
            "bn_rows": int(bny.sum()),
            "bn_missing_minutes": (bn_grid_n.get(y, 0) - int(bny.sum())) if y in bn_grid_n else 0,
        })
    per_year = pd.DataFrame(rows)
    total = {
        "bf_rows": int(len(bf)), "bf_first": str(bf.index[0]), "bf_last": str(bf.index[-1]),
        "bf_empty_rows": int(empty_rows.sum()),
        "bf_absent_minutes": int(len(grid) - len(bf)),
        "bf_valid_bars": int(valid_grid.sum()),
        "bf_big_gaps": int(len(gaps)),
        "bf_misprint_rows": int(mp.sum()),
        "bn_rows": int(len(bn)), "bn_first": str(bn.index[0]), "bn_last": str(bn.index[-1]),
        "max_gap_min": max_gap_min,
    }
    return {"per_year": per_year, "total": total}


def _md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    head = "| " + " | ".join(cols) + " |"
    sep = "|" + "|".join("---" for _ in cols) + "|"
    body = []
    for r in df.to_dict("records"):
        cells = []
        for c in cols:
            v = r[c]
            if c == "year":
                cells.append(str(int(v)))
            elif isinstance(v, float):
                cells.append(f"{v:.4f}")
            elif isinstance(v, (int, np.integer)):
                cells.append(f"{int(v):,}")
            else:
                cells.append(str(v))
        body.append("| " + " | ".join(cells) + " |")
    return "\n".join([head, sep] + body)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--summary", action="store_true", help="print the dev-set overview")
    p.add_argument("--max-gap-min", type=int, default=5)
    p.add_argument("--json", action="store_true", help="also print the totals as JSON")
    args = p.parse_args(argv)
    bf, bn = load_dev_frames()
    if args.summary:
        s = summarize(bf, bn, args.max_gap_min)
        print(f"開発セット(load_unsealed 経由、単位 {UNIT}): bitFlyer {s['total']['bf_first']} .. "
              f"{s['total']['bf_last']}, Binance {s['total']['bn_first']} .. {s['total']['bn_last']}")
        print(f"bitFlyer 行数 {s['total']['bf_rows']:,} / 空行 {s['total']['bf_empty_rows']:,} / "
              f"欠落分 {s['total']['bf_absent_minutes']:,} / 有効足 {s['total']['bf_valid_bars']:,} / "
              f"{args.max_gap_min} 分超欠損 {s['total']['bf_big_gaps']:,} / "
              f"誤プリント {s['total']['bf_misprint_rows']:,} ; Binance 行数 {s['total']['bn_rows']:,}")
        print()
        print(_md_table(s["per_year"]))
        if args.json:
            print(json.dumps(s["total"], ensure_ascii=False, indent=2))
    else:
        print(f"bf rows {len(bf):,}, bn rows {len(bn):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

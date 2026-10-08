"""数の作り直し(SPEC.md §5 の 2): 帳簿のツールで約定のファイルから計算し直し、書いた数と比べる。"""
from __future__ import annotations

import csv
import json
import os

from bot.bt.road.ledger import LedgerError, book

from .common import SimpleRoadError, cell, to_ns

TRADE_COLS = ("first_t_ns", "last_t_ns", "levels", "max_position", "hold_ns", "pnl_jpy", "status")
SUMMARY_COLS = ("fill_count", "closed_trades", "pnl_jpy", "open_trades")


def check_numbers(out_dir, side) -> list:
    """書いた trades・summary と、約定のファイルから計算し直した数との食い違いの並び(無ければ空)。"""
    p = lambda name, ext="csv": os.path.join(str(out_dir), f"{name}_{side}.{ext}")  # noqa: E731
    try:
        with open(p("fills"), newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        fills = [{"t_ns": to_ns(r["ts"]), "side": r["side"], "qty": float(r["qty"]), "px": float(r["px"]), "ccy": "JPY"}
                 for r in rows]
        ledger = book(fills)
    except (OSError, KeyError, ValueError, SimpleRoadError, LedgerError) as e:
        return [f"約定のファイルから数を作り直せない: {e}"]
    diffs = []
    try:
        with open(p("summary", "json"), encoding="utf-8") as fh:
            written = json.load(fh)
        for k in SUMMARY_COLS:
            a, b = cell(ledger.summary[k]), cell(written.get(k))
            if a != b:
                diffs.append(f"summary の {k}: 作り直し {a!r} / 書いてある {b!r}")
    except (OSError, ValueError) as e:
        diffs.append(f"summary を読めない: {e}")
    try:
        with open(p("trades"), newline="", encoding="utf-8") as fh:
            trows = list(csv.DictReader(fh))
        if len(trows) != len(ledger.trades):
            diffs.append(f"trades の行数: 作り直し {len(ledger.trades)} / 書いてある {len(trows)}")
        for i, (tr, w) in enumerate(zip(ledger.trades, trows)):
            for k in TRADE_COLS:
                a, b = cell(tr[k]), cell(w.get(k))
                if a != b:
                    diffs.append(f"trades の {i} 行目の {k}: 作り直し {a!r} / 書いてある {b!r}")
    except OSError as e:
        diffs.append(f"trades を読めない: {e}")
    return diffs

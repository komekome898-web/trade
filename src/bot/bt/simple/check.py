"""数の作り直し(SPEC.md §5 の 2): 帳簿のツールで約定のファイルから計算し直し、書いた数と比べる。

読めない・形の違う入力は、どんな例外も拾い、例外にせず食い違いの行として返す。
"""
from __future__ import annotations

import csv
import io
import json
import os

from bot.bt.road.ledger import book

from .common import FILL_COLS, SUMMARY_COLS, to_ns, trades_text


def check_numbers(out_dir, side) -> list:
    """書いた trades・summary と、約定のファイルから計算し直した数との食い違いの並び(無ければ空)。"""
    try:
        return _check(out_dir, side)
    except Exception as e:  # noqa: BLE001  読めない入力はどんな例外でも、例外にせず食い違いで返す(SPEC.md §5 の 2)
        return [f"数の作り直しの途中で読めない入力に当たった: {type(e).__name__}: {e}"]


def _read(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def _fills_from(path: str):
    """約定のファイルを読んで book に渡す約定の並びにする。決まった形でなければ (None, 食い違いの文) を返す。"""
    data = _read(path)
    if not data:
        return None, "fills が 0 バイト"
    text = data.decode("utf-8")
    want_head = ",".join(FILL_COLS)
    if text.split("\n", 1)[0] != want_head:
        return None, f"fills の見出しの行が決まった列と違う: 期待 {want_head!r}"
    rows = list(csv.reader(io.StringIO(text, newline="")))[1:]
    for i, r in enumerate(rows):
        if len(r) != len(FILL_COLS):
            return None, f"fills の {i + 1} 行目の欄の数が見出しと違う: {len(r)} / {len(FILL_COLS)}"
    return [{"t_ns": to_ns(r[0]), "side": r[2], "qty": float(r[3]), "px": float(r[4]), "ccy": "JPY"} for r in rows], None


def _check(out_dir, side) -> list:
    p = lambda name, ext="csv": os.path.join(str(out_dir), f"{name}_{side}.{ext}")  # noqa: E731
    fills, why = _fills_from(p("fills"))
    if why is not None:
        return [f"約定のファイルから数を作り直せない: {why}"]
    ledger = book(fills)
    diffs = []

    try:
        written = json.loads(_read(p("summary", "json")).decode("utf-8"))
        want = {k: ledger.summary[k] for k in SUMMARY_COLS}
        if type(written) is not dict or set(written) != set(SUMMARY_COLS):
            diffs.append(f"summary が {len(SUMMARY_COLS)} つの鍵ちょうどの辞書でない: {written!r}")
        else:
            for k in SUMMARY_COLS:
                if type(written[k]) is not type(want[k]) or written[k] != want[k]:
                    diffs.append(f"summary の {k}: 作り直し {want[k]!r} / 書いてある {written[k]!r}")
    except Exception as e:  # noqa: BLE001
        diffs.append(f"summary を読めない: {type(e).__name__}: {e}")

    try:
        if _read(p("trades")) != trades_text(ledger.trades).encode("utf-8"):
            diffs.append("trades のファイル全体が、約定から作り直した中身と 1 字違わず同じでない")
    except Exception as e:  # noqa: BLE001
        diffs.append(f"trades を読めない: {type(e).__name__}: {e}")
    return diffs

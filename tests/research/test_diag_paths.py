"""D4・D5 の読み口(`scripts/analysis/diag_paths.py`)の計算を合成の足で固める。"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "analysis"))
import diag_paths as dp  # noqa: E402

M = dp.MIN


def _bars(n=200, start=0, base=100.0):
    t = np.array([start + i * M for i in range(n)])
    c = np.full(n, base)
    return dp.Bars(t, c.copy(), c.copy(), c.copy())


def test_trade_life_signs_by_side():
    b = _bars()
    # 建て 10 分(足 10 から)、出 20 分。足 12 で高値 101(+100bp)、足 15 で安値 99.5(−50bp)
    b.h[12] = 101.0
    b.l[15] = 99.5
    long_ = dp.trade_life({"entry_ns": 10 * M, "exit_ns": 20 * M, "side": 1, "pnl_jpy": 0, "entry_px": 100.0}, b)
    assert abs(long_["mfe"] - 100.0) < 1e-9 and abs(long_["mae"] + 50.0) < 1e-9 and long_["t_mfe"] == 2
    short = dp.trade_life({"entry_ns": 10 * M, "exit_ns": 20 * M, "side": -1, "pnl_jpy": 0, "entry_px": 100.0}, b)
    assert abs(short["mfe"] - 50.0) < 1e-9 and abs(short["mae"] + 100.0) < 1e-9


def test_trade_life_excludes_entry_bar_and_after_exit():
    b = _bars()
    b.h[9] = 110.0   # 建ての足(entry_t は足 9 の終わり = 10 分)は含めない
    b.h[20] = 110.0  # 出の時刻に始まる足は含めない
    r = dp.trade_life({"entry_ns": 10 * M, "exit_ns": 20 * M, "side": 1, "pnl_jpy": 0, "entry_px": 100.0}, b)
    assert r["mfe"] == 0.0


def test_after_exit_and_signal_move_signed():
    b = _bars()
    b.c[24:] = 101.0  # 出(20 分)の後、25 分の終値から上がる
    r = dp.trade_life({"entry_ns": 10 * M, "exit_ns": 20 * M, "side": -1, "pnl_jpy": 0, "entry_px": 100.0}, b)
    assert abs(r["after_5"] + 100.0) < 1e-9  # 売りの取引なので、上がった分は負
    assert abs(dp.signal_move(20 * M, 1, b, 5) - 100.0) < 1e-9
    assert dp.signal_move(10_000 * M, 1, b, 5) is None


def test_close_at_uses_bar_ending_at_time():
    b = _bars()
    b.c[4] = 105.0  # 足 4 は 4〜5 分、5 分に終わる
    assert b.close_at(5 * M) == 105.0

"""再現の走らせ(`scripts/w4_measure/c2_limit_run.py`)の参照の行の切り替え(--ref-join-bitflyer・--ref-drop-no-trade)。"""
from __future__ import annotations

import gzip
import importlib
import os
import sys

import pytest

NS = 1_000_000_000
M = 60 * NS
T0 = 1_704_067_200 * NS  # 試験の時刻で、データではない


def _load_w4(name):
    """test_katsuo_limit_sim._load_w4 と同じ読み込み(別の置き場の common・post・run_v2 を読み込む間だけ外す)。"""
    d = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts", "w4_measure"))
    if d not in sys.path:
        sys.path.insert(0, d)
    if name in sys.modules:
        return sys.modules[name]
    foreign = {k: sys.modules.pop(k) for k in ("common", "post", "run_v2") if k in sys.modules
               and os.path.dirname(os.path.abspath(getattr(sys.modules[k], "__file__", None) or "")) != d}
    try:
        return importlib.import_module(name)
    finally:
        for k, m in foreign.items():
            sys.modules[k] = m


R = _load_w4("c2_limit_run")


def _rows():
    ts = [T0 + i * M for i in range(5)]
    vals = [[1.0, 2.0, 3.0, 4.0, 5.0], [11.0, 12.0, 13.0, 14.0, 15.0], [0.5, 1.5, 2.5, 3.5, 4.5], [1.1, 2.1, 3.1, 4.1, 5.1]]
    return ts, vals


def test_default_is_identity():
    ts, vals = _rows()
    got = R.filter_ref_rows(ts, vals, join=False, drop_no_trade=False)
    assert got[0] is ts and got[1] is vals and got[2:] == (0, 0)


def test_join_keeps_rows_whose_minute_has_a_bitflyer_bar():
    ts, vals = _rows()
    bars = {ts[0], ts[2], ts[3], ts[4]}  # 1 分目の足が無い
    t2, v2, dj, dn = R.filter_ref_rows(ts, vals, join=True, drop_no_trade=False, bar_starts=bars)
    assert t2 == [ts[0], ts[2], ts[3], ts[4]] and (dj, dn) == (1, 0)
    assert v2[0] == [1.0, 3.0, 4.0, 5.0] and v2[1] == [11.0, 13.0, 14.0, 15.0] and len(v2) == 4


def test_join_uses_minute_floor_of_off_minute_rows():
    ts = [T0, T0 + M + 30 * NS]  # 2 行目は分の頭に無い(30 秒)。分の頭 T0 + M の足があれば残す
    vals = [[1.0, 2.0]] * 4
    t2, _v, dj, _ = R.filter_ref_rows(ts, vals, join=True, drop_no_trade=False, bar_starts={T0 + M})
    assert t2 == [T0 + M + 30 * NS] and dj == 1


def test_drop_no_trade_and_both():
    ts, vals = _rows()
    ntr = {t: (0 if i in (1, 4) else 7) for i, t in enumerate(ts)}
    t2, v2, dj, dn = R.filter_ref_rows(ts, vals, join=False, drop_no_trade=True, n_trades=ntr)
    assert t2 == [ts[0], ts[2], ts[3]] and (dj, dn) == (0, 2) and v2[3] == [1.1, 3.1, 4.1]
    # 両方: 結合を先に見る(1 分目は結合で落ちた数に入る)
    t3, _v, dj, dn = R.filter_ref_rows(ts, vals, join=True, drop_no_trade=True, bar_starts={ts[0], ts[2], ts[3], ts[4]},
                                       n_trades=ntr)
    assert t3 == [ts[0], ts[2], ts[3]] and (dj, dn) == (1, 1)


def test_drop_no_trade_stops_when_a_row_has_no_n_trades():
    ts, vals = _rows()
    with pytest.raises(SystemExit):
        R.filter_ref_rows(ts, vals, join=False, drop_no_trade=True, n_trades={ts[0]: 1})


def test_binance_n_trades_reads_range_and_stops_at_hi(tmp_path):
    p = tmp_path / "b.csv.gz"
    with gzip.open(p, "wt", encoding="utf-8") as fh:
        fh.write("open_time,open,high,low,close,volume,quote_volume,n_trades,taker_buy_base\n")
        fh.write("2024-01-01 00:00:00+00:00,1,1,1,1,0,0,5,0\n")
        fh.write("2024-01-01 00:01:00+00:00,1,1,1,1,0,0,0,0\n")
        fh.write("2024-01-01 00:02:00+00:00,1,1,1,1,0,0,9,0\n")
        fh.write("not a time,1,1,1,1,0,0,9,0\n")  # hi 以上の行に来たら止めるので、この行は読まない
    got = R.binance_n_trades([str(p)], T0, T0 + 2 * M)
    assert got == {T0: 5, T0 + M: 0}
    got = R.binance_n_trades([str(p)], T0 + M, T0 + 2 * M)
    assert got == {T0 + M: 0}


def test_cli_has_switches_default_off():
    import argparse  # noqa: F401
    src = open(R.__file__, encoding="utf-8").read()
    assert '"--ref-join-bitflyer", action="store_true"' in src and '"--ref-drop-no-trade", action="store_true"' in src

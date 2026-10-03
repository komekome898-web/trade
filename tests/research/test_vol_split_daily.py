"""前の日のボラで日を分ける読み方の決まり(`scripts/w4_measure/vol_split_daily.py` の R1〜R3・R5)を、表を見る前に固める。"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "w4_measure"))
_spec = importlib.util.spec_from_file_location("vol_split_daily", REPO / "scripts" / "w4_measure" / "vol_split_daily.py")
vs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vs)


def test_daily_vol_needs_60_bars_and_uses_abs_log_moves():
    up_down = [100.0, 101.0] * 40  # 80 本
    v = vs.daily_vol({"2020-01-01": up_down, "2020-01-02": [100.0] * 59})
    assert "2020-01-02" not in v
    assert abs(v["2020-01-01"] - math.log(1.01) * 1e4) < 1e-6


def _year_days(y):
    from datetime import date, timedelta
    d = date(y, 1, 1)
    out = []
    while d.year == y:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def test_classify_uses_previous_day_and_previous_year_edges():
    vol = {}
    for i, d in enumerate(_year_days(2016)):
        vol[d] = float(i + 1)          # 2016 の分位: 1/3 → 約 123、2/3 → 約 245
    for d in _year_days(2017)[:5]:
        vol[d] = 1000.0                # 2017 の値は 2017 の境に使わない
    vol["2016-12-31"] = 0.0
    c = vs.classify(vol)
    assert "2016-06-01" not in c       # 2016 は分けない(2017 から)
    assert c["2017-01-01"] == "low"    # 前の日 2016-12-31 = 0.0
    assert c["2017-01-02"] == "high"   # 前の日 2017-01-01 = 1000(境は 2016 の分位)
    assert "2017-01-06" not in c       # 前の日 2017-01-05 は値なし → 分けない(1 月 6 日の値も無い)


def test_bootstrap_diff_point_and_interval_contain_point():
    days = [f"2020-01-{i:02d}" for i in range(1, 31)]
    pnl = {d: (10.0 if i % 2 == 0 else 0.0) for i, d in enumerate(days)}
    cls = {d: ("high" if i % 2 == 0 else "low") for i, d in enumerate(days)}
    p, lo, hi = vs.block_bootstrap_diff(days, pnl, cls)
    assert p == 10.0 and lo <= p <= hi


def test_bootstrap_is_deterministic():
    days = [f"2020-02-{i:02d}" for i in range(1, 29)]
    pnl = {d: float(i) for i, d in enumerate(days)}
    cls = {d: ("high" if i % 3 == 0 else "low") for i, d in enumerate(days)}
    assert vs.block_bootstrap_diff(days, pnl, cls) == vs.block_bootstrap_diff(days, pnl, cls)


def test_classify_same_day_uses_that_day():
    # 2016 は境のため、2017 の 1 日だけ大きな値を入れる。その日自身が「高」になり、翌日・翌々日は変わらない
    vol = {}
    for i, d in enumerate(_year_days(2016)):
        vol[d] = float(i + 1)
    for d in _year_days(2017)[:40]:
        vol[d] = 1.0
    vol["2017-01-20"] = 10_000.0
    same = vs.classify_same_day(vol)
    prev = vs.classify(vol)
    assert same["2017-01-20"] == "high" and same["2017-01-21"] == "low" and same["2017-01-19"] == "low"
    assert prev["2017-01-21"] == "high" and prev["2017-01-20"] == "low"

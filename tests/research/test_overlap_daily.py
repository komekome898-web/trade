"""重なりの表の読み方の決まり(`scripts/w4_measure/overlap_daily.py` の R1〜R3)を、表を見る前に固める。"""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("overlap_daily", REPO / "scripts" / "w4_measure" / "overlap_daily.py")
ov = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ov)


def test_days_between_is_jst_and_half_open():
    # 2015-11-28T15:00Z = 日本時間 11-29 0 時。終わり 2015-12-01T15:00Z は含まない → 11-29・11-30・12-01
    assert ov.days_between("2015-11-28T15:00:00Z", "2015-12-01T15:00:00Z") == ["2015-11-29", "2015-11-30", "2015-12-01"]


def test_daily_from_trades_fills_zero_and_uses_exit_jst_day():
    ns = 10**9
    t0 = 1448722800 * ns  # 2015-11-28T15:00Z = JST 11-29 00:00
    trades = {"t_unit": "ns", "exit_t_ns": [t0 + 3600 * ns, t0 + 3600 * ns + 1, t0 + 86400 * ns * 2 + 60 * ns],
              "pnl_pct": [1.0, 2.0, -5.0]}
    d = ov.daily_from_trades(trades, ("2015-11-28T15:00:00Z", "2015-12-01T15:00:00Z"))
    assert d == {"2015-11-29": 3.0, "2015-11-30": 0.0, "2015-12-01": -5.0}


def test_after_last_day_dropped():
    trades = {"t_unit": "ns", "exit_t_ns": [], "pnl_pct": []}
    d = ov.daily_from_trades(trades, ("2023-12-15T15:00:00Z", "2023-12-19T15:00:00Z"))
    assert max(d) == ov.LAST_DAY


def test_pair_stats_common_days_and_measures():
    days = [f"2020-01-{i:02d}" for i in range(1, 21)]
    a = {k: float(i) for i, k in enumerate(days)}
    b = {k: float(i) for i, k in enumerate(days)}
    b["2019-12-31"] = 99.0  # a に無い日は使わない
    s = ov.pair_stats(a, b)
    assert s["days"] == 20
    assert abs(s["corr"] - 1.0) < 1e-12
    assert s["same_sign"] == 1.0          # 0 の日(1 日目)は数えない
    assert s["both_nonzero_days"] == 19
    assert s["worst5_overlap"] == 1.0     # 下から 5%(1 日)が同じ日


def test_pair_stats_opposite():
    days = [f"2020-02-{i:02d}" for i in range(1, 21)]
    a = {k: float(i + 1) for i, k in enumerate(days)}
    b = {k: -float(i + 1) for i, k in enumerate(days)}
    s = ov.pair_stats(a, b)
    assert abs(s["corr"] + 1.0) < 1e-12 and s["same_sign"] == 0.0 and s["worst5_overlap"] == 0.0


def test_exit_at_period_end_midnight_counts_on_last_day():
    # 期間の終わり 2023-12-17T15:00Z(日本時間 12-18 の 0 時)に閉じた取引は 12-17 に入る(関門 ② の 1 回目の止める 1)
    ns = 10**9
    end = 1702825200 * ns  # 2023-12-17T15:00Z
    trades = {"t_unit": "ns", "exit_t_ns": [end], "pnl_pct": [-90.65]}
    d = ov.daily_from_trades(trades, ("2023-12-15T15:00:00Z", "2023-12-17T15:00:00Z"))
    assert d["2023-12-17"] == -90.65


def test_mean_ci_contains_mean():
    import numpy as np
    x = np.arange(100, dtype=float)
    m, lo, hi = ov.mean_ci(x)
    assert m == 49.5 and lo <= m <= hi

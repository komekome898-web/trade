"""分解の表の読み方の決まり(`scripts/w4_measure/round0_decomp.py` の D1・D2)を、表を見る前に固める。"""
from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "w4_measure"))
_spec = importlib.util.spec_from_file_location("round0_decomp", REPO / "scripts" / "w4_measure" / "round0_decomp.py")
rd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rd)

JST = timezone(timedelta(hours=9))


def ns(y, m, d, hh, mm):
    return int(datetime(y, m, d, hh, mm, tzinfo=JST).timestamp()) * 10**9


def test_d1_cells_sum_to_year_sum_and_shares_add_to_one():
    pnl = {"2017-08-18": 10.0, "2017-08-19": -4.0, "2017-08-20": 3.0, "2018-01-01": 7.0, "2018-01-02": -2.0, "2018-01-03": 0.0}
    cls = {"2017-08-19": "low", "2017-08-20": "high", "2018-01-01": "high", "2018-01-02": "mid", "2018-01-03": "low"}
    out = rd.d1_cells(pnl, cls)
    for y, r in out.items():
        assert abs(sum(c["sum"] for c in r["cells"].values()) - r["year_sum"]) < 1e-12
        assert sum(c["days"] for c in r["cells"].values()) == r["year_days"]
        assert abs(sum(c["share"] for c in r["cells"].values()) - 1.0) < 1e-12
    assert out["2017"]["cells"]["none"] == {"days": 1, "sum": 10.0, "mean": 10.0, "share": 10.0 / 9.0}
    assert out["2018"]["cells"]["low"]["days"] == 1 and out["2018"]["cells"]["low"]["sum"] == 0.0
    assert abs(sum(r["year_sum"] for r in out.values()) - sum(pnl.values())) < 1e-12


def test_d1_share_is_none_when_year_sum_is_zero():
    out = rd.d1_cells({"2019-01-01": 5.0, "2019-01-02": -5.0}, {"2019-01-01": "low", "2019-01-02": "high"})
    assert out["2019"]["year_sum"] == 0.0
    assert all(c["share"] is None for c in out["2019"]["cells"].values())


def test_last_friday_close_takes_friday_2359_jst_not_saturday():
    bars = []
    t = ns(2021, 3, 5, 23, 55)  # 金曜
    closes = {}
    for k in range(5):  # 金 23:55〜23:59
        closes[t] = 100.0 + k
        t += 60 * 10**9
    for k in range(3):  # 土 0:00〜0:02
        closes[t] = 500.0 + k
        t += 60 * 10**9
    bars = sorted(closes.items())
    fs, fc = rd.friday_bars(bars)
    assert fs[-1] == ns(2021, 3, 5, 23, 59)
    entry = ns(2021, 3, 8, 6, 1)  # 月曜
    start, close = rd.last_friday_close(fs, fc, entry)
    assert start == ns(2021, 3, 5, 23, 59) and close == 104.0


def test_last_friday_close_ignores_bars_after_entry_and_non_fridays():
    bars = [(ns(2021, 3, 4, 23, 59), 1.0), (ns(2021, 3, 5, 10, 0), 2.0), (ns(2021, 3, 5, 23, 59), 3.0),
            (ns(2021, 3, 6, 0, 0), 4.0), (ns(2021, 3, 7, 12, 0), 5.0), (ns(2021, 3, 12, 9, 0), 6.0)]
    fs, fc = rd.friday_bars(bars)
    assert fc == [2.0, 3.0, 6.0]  # 木・土・日の足は入らない
    assert rd.last_friday_close(fs, fc, ns(2021, 3, 8, 6, 1)) == (ns(2021, 3, 5, 23, 59), 3.0)
    # 入りが金曜の昼なら、その金曜の入りより前の足
    assert rd.last_friday_close(fs, fc, ns(2021, 3, 5, 12, 0)) == (ns(2021, 3, 5, 10, 0), 2.0)
    assert rd.last_friday_close(fs, fc, ns(2021, 3, 5, 9, 0)) is None


def test_gap_and_direction():
    assert abs(rd.gap_bp(101.0, 100.0) - 100.0) < 1e-9
    assert rd.direction(100.0, -1) == "fill"   # g 正・売り = 窓を埋める
    assert rd.direction(100.0, 1) == "widen"
    assert rd.direction(-5.0, 1) == "fill"
    assert rd.direction(-5.0, -1) == "widen"
    assert rd.direction(0.0, 1) == "zero"


def test_band_edges_follow_one_third_and_two_thirds_quantiles():
    q1, q2 = rd.tercile_edges([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])  # 1/3 → 3.0、2/3 → 5.0
    assert (q1, q2) == (3.0, 5.0)
    assert rd.band(2.999, q1, q2) == "small"
    assert rd.band(3.0, q1, q2) == "mid"      # 下の境ちょうどは中
    assert rd.band(4.999, q1, q2) == "mid"
    assert rd.band(5.0, q1, q2) == "large"    # 上の境ちょうどは大


def test_d2_cells_marginals_agree_and_wins_are_strictly_positive():
    rows = [{"year": "2018", "dir": "fill", "band": "small", "pnl": 3.0},
            {"year": "2018", "dir": "widen", "band": "large", "pnl": -1.0},
            {"year": "2019", "dir": "fill", "band": "large", "pnl": 0.0}]
    t = rd.d2_cells(rows)
    assert t["all"]["all"]["n"] == 3 and t["all"]["all"]["wins"] == 1 and t["all"]["all"]["sum"] == 2.0
    for name in ("year_dir_band", "year_dir", "year_band", "dir_band", "year"):
        assert sum(c["n"] for c in t[name].values()) == 3
        assert abs(sum(c["sum"] for c in t[name].values()) - 2.0) < 1e-12

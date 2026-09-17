"""`scripts/o3c_rows4.py` の単体テスト(2026-09-17、L-192 の行 1・行 2)。

固定するのは 3 点:
  (a) タイの経路の分け方(時間分解能 / 価格の刻み)が、起点 `before` / `after_shift` の
      どちらでも定義どおりに分かれること。**2 つが排他で、タイの全件がどちらかに入る**こと。
  (b) 60 秒バーの作り方が `scripts/verify_liq_instrument.py: to_bars` と同じ
      (枠ごとに**最後の約定**の時刻と価格を残す)こと。
  (c) 束の長さ・束あたり件数のバケットの境界(左閉右開)。

このテストは**数え方**だけを固定する。相場についての判定は一切しない。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


rows4 = _load("o3c_rows4")

from bot.research.liq_response import Cascade, PriceSeries  # noqa: E402


def _casc(cid: str, start: int, end: int) -> Cascade:
    return Cascade(
        cascade_id=cid, exchange="binance_cm", kind="real",
        start_ms=start, end_ms=end, n_events=1, total_size=1.0,
        direction="long", first_price=None, last_price=None,
    )


# --------------------------------------------------------------------------- #
# (a) タイの経路
# --------------------------------------------------------------------------- #

def test_classify_time_resolution_when_window_collapses_to_one_point():
    """窓の内側で時刻が 1 つも進んでいない -> 時間分解能。"""
    prices = PriceSeries.from_trades([(0, 100.0), (60_000, 101.0), (120_000, 102.0)])
    # 起点 at_or_before(70_000) = 60_000 / 終点 at_or_before(80_000) = 60_000 -> 同じ点
    out = rows4.classify(prices, [_casc("a", 70_000, 80_000)], "before")[0]
    assert out["tie"] is True
    assert out["path"] == rows4.TIE_PATH_TIME
    assert out["start_pt_ts_ms"] == out["anchor_ts_ms"] == 60_000
    assert out["internal_bp"] == 0.0


def test_classify_price_tick_when_times_differ_but_price_is_equal():
    """時刻は違うのに価格が同じ -> 価格の刻み。"""
    prices = PriceSeries.from_trades([(0, 100.0), (60_000, 100.0), (120_000, 102.0)])
    out = rows4.classify(prices, [_casc("a", 10_000, 70_000)], "before")[0]
    assert out["tie"] is True
    assert out["path"] == rows4.TIE_PATH_TICK
    assert out["start_pt_ts_ms"] == 0 and out["anchor_ts_ms"] == 60_000


def test_classify_not_a_tie_when_price_moved():
    prices = PriceSeries.from_trades([(0, 100.0), (60_000, 101.0)])
    out = rows4.classify(prices, [_casc("a", 10_000, 70_000)], "before")[0]
    assert out["tie"] is False
    assert out["path"] == ""
    assert out["internal_bp"] != 0.0


def test_classify_after_shift_uses_at_or_after_for_the_end_point():
    """`after_shift` の終点は `at_or_after(end_ms)`(束の終了**以後**の最初の点)。"""
    prices = PriceSeries.from_trades([(0, 100.0), (60_000, 100.0), (120_000, 102.0)])
    c = _casc("a", 0, 60_000)
    before = rows4.classify(prices, [c], "before")[0]
    after = rows4.classify(prices, [c], "after_shift")[0]
    assert before["anchor_ts_ms"] == 60_000     # at_or_before(60_000)
    assert after["anchor_ts_ms"] == 60_000      # at_or_after(60_000) も同じ点にある
    # 終了時刻に点が無いときは after_shift が先へ進む
    c2 = _casc("b", 0, 30_000)
    assert rows4.classify(prices, [c2], "before")[0]["anchor_ts_ms"] == 0
    assert rows4.classify(prices, [c2], "after_shift")[0]["anchor_ts_ms"] == 60_000


def test_classify_marks_missing_when_the_anchor_is_too_stale():
    """起点が引けない行は落とさず `missing` として残す(行を消さない約束)。"""
    prices = PriceSeries.from_trades([(0, 100.0)])
    out = rows4.classify(prices, [_casc("a", 10_000_000, 10_000_000)], "before")[0]
    assert out["path"] == "missing"
    assert out["tie"] is None
    assert out["internal_bp"] != out["internal_bp"]  # NaN


def test_tie_paths_are_exclusive_and_cover_every_tie():
    """2 つの経路は排他で、タイの全件がどちらかに入る。"""
    prices = PriceSeries.from_trades(
        [(0, 100.0), (60_000, 100.0), (120_000, 101.0), (180_000, 101.0)]
    )
    cs = [
        _casc("a", 70_000, 80_000),      # 同じ点 -> 時間分解能
        _casc("b", 10_000, 70_000),      # 別の点・同じ価格 -> 価格の刻み
        _casc("c", 10_000, 130_000),     # 値動きあり -> 非タイ
        _casc("d", 130_000, 190_000),    # 別の点・同じ価格 -> 価格の刻み
    ]
    for anchor in ("before", "after_shift"):
        cls = rows4.classify(prices, cs, anchor)
        ties = [c for c in cls if c["tie"] is True]
        paths = [c["path"] for c in ties]
        assert set(paths) <= {rows4.TIE_PATH_TIME, rows4.TIE_PATH_TICK}
        assert len(paths) == len(ties)
        assert all(c["path"] == "" for c in cls if c["tie"] is False)


# --------------------------------------------------------------------------- #
# (b) 60 秒バー
# --------------------------------------------------------------------------- #

def test_build_bar_series_keeps_the_last_trade_of_each_bucket():
    t = np.array([0, 10, 59_999, 60_000, 61_000, 180_000], dtype=np.int64)
    p = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], dtype=np.float64)
    bt, bp = rows4.build_bar_series(t, p, 60_000)
    assert bt.tolist() == [59_999, 61_000, 180_000]
    assert bp.tolist() == [3.0, 5.0, 6.0]


def test_build_bar_series_on_empty_input():
    t = np.empty(0, dtype=np.int64)
    p = np.empty(0, dtype=np.float64)
    bt, bp = rows4.build_bar_series(t, p, 60_000)
    assert bt.size == 0 and bp.size == 0


# --------------------------------------------------------------------------- #
# (c) バケットの境界
# --------------------------------------------------------------------------- #

def test_len_buckets_boundaries_are_left_closed_right_open():
    w = np.array([0, 1, 999, 1_000, 9_999, 10_000, 59_999, 60_000,
                  599_999, 600_000, 3_599_999, 3_600_000], dtype=np.int64)
    b = rows4._len_buckets(w)
    assert b == {
        "eq0": 1, "1-999ms": 2, "1-10s": 2, "10-60s": 2,
        "60s-10min": 2, "10-60min": 2, "ge60min": 1,
    }
    assert sum(b.values()) == w.size


def test_size_buckets_cover_every_cascade():
    n = np.array([1, 1, 2, 3, 5, 6, 244], dtype=np.int64)
    b = rows4._size_buckets(n)
    assert b == {"eq1": 2, "eq2": 1, "3to5": 2, "ge6": 2}
    assert sum(b.values()) == n.size

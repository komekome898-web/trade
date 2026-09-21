"""`scripts/o3c_signal_calib.py`(§7.5「較正の良い方」の判定)の試験。

設計 `SIGNAL_MATERIALS_DESIGN_2026-09-20.md` §7.5・§7.5.1、
反証者レビュー7(`REFUTER_REVIEW7_2026-09-20.md`)D2 の直し。

**測るもの**
  1. 帯は [0,0.05) … [0.95,1.0] の固定 20 本(起点 0、最後だけ両端閉区間)。
  2. 件数 20 未満の帯は平均から外し、外した帯を返す。
  3. 値 = Σ n_b × |実際の割合_b − 帯の中央_b| / Σ n_b(使った帯だけの重み付き平均)。
  4. 完璧な較正(帯の中央 = 実際の割合)なら値は 0。
  5. `choose_better`: 差が 0.01 を超えて小さい方が勝ち、それ以外(同点・NaN)は "code"。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

_spec = importlib.util.spec_from_file_location(
    "o3c_signal_calib", ROOT / "scripts" / "o3c_signal_calib.py")
calib = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(calib)


def test_bin_edges_are_20_fixed_bins_from_zero():
    assert calib.N_BINS == 20
    assert calib.BIN_EDGES[0] == 0.0
    assert calib.BIN_EDGES[-1] == 1.0
    assert np.allclose(np.diff(calib.BIN_EDGES), 0.05)
    assert np.allclose(calib.BIN_CENTERS,
                       [0.025 + 0.05 * b for b in range(20)])


def test_bin_index_right_open_except_last_bin_closed():
    # [0,0.05) の右端は帯1、[0.95,1.0] は両端閉区間で 1.0 も帯19に入る
    idx = calib._bin_index(np.array([0.0, 0.049, 0.05, 0.94999, 0.95, 1.0]))
    assert idx.tolist() == [0, 0, 1, 18, 19, 19]


def test_perfect_calibration_gives_zero():
    rng = np.random.default_rng(0)
    n_per_bin = 200
    probs, ys = [], []
    for b in range(calib.N_BINS):
        center = calib.BIN_CENTERS[b]
        p = np.full(n_per_bin, center)
        y = (rng.random(n_per_bin) < center).astype(float)
        probs.append(p)
        ys.append(y)
    prob = np.concatenate(probs)
    y = np.concatenate(ys)
    g = calib.calibration_goodness(prob, y)
    # 完璧ではないが(y は乱数で生成)、帯の中央からの重み付き平均絶対誤差は小さい
    assert g["値"] < 0.03
    assert len(g["使った帯"]) == 20
    assert g["外した帯"] == []


def test_bins_with_fewer_than_min_count_are_excluded():
    # 帯0([0,0.05))に 5 件(20 未満)、帯10([0.5,0.55))に 100 件
    prob = np.concatenate([np.full(5, 0.01), np.full(100, 0.52)])
    y = np.concatenate([np.zeros(5), np.full(100, 0.52)])
    g = calib.calibration_goodness(prob, y)
    used_bins = {row["帯"] for row in g["使った帯"]}
    excluded_bins = {row["帯"] for row in g["外した帯"]}
    assert 0 in excluded_bins
    assert 0 not in used_bins
    assert 10 in used_bins
    # 値は「使った帯」だけの重み付き平均(帯0を混ぜていない)
    assert g["値"] == pytest.approx(abs(0.52 - calib.BIN_CENTERS[10]))


def test_calibration_goodness_weighted_mean_hand_computed():
    # 帯0: 30 件、実際の割合 0.10(中央 0.025、誤差 0.075)
    # 帯5(=[0.25,0.30)): 20 件、実際の割合 0.40(中央 0.275、誤差 0.125)
    prob = np.concatenate([np.full(30, 0.01), np.full(20, 0.26)])
    y = np.concatenate([np.full(30, 0.10), np.full(20, 0.40)])
    g = calib.calibration_goodness(prob, y)
    expected = (30 * abs(0.10 - calib.BIN_CENTERS[0])
               + 20 * abs(0.40 - calib.BIN_CENTERS[5])) / (30 + 20)
    assert g["値"] == pytest.approx(expected)
    assert len(g["使った帯"]) == 2
    assert g["外した帯"] == []


def test_calibration_goodness_ignores_nan_and_out_of_finite():
    prob = np.array([0.1, np.nan, 0.2, 0.3])
    y = np.array([0.0, 1.0, np.nan, 1.0])
    g = calib.calibration_goodness(prob, y)
    # 有限のペアは (0.1,0.0) と (0.3,1.0) の 2 件だけ(件数 20 未満なので両方
    # 「外した帯」に入り、使える帯が無い -> 値は NaN)
    assert g["値"] != g["値"]
    assert g["使った帯"] == []


def test_choose_better_strict_win_vs_tie_vs_nan():
    good_a = {"値": 0.10}
    good_b_tied = {"値": 0.109}   # 差 0.009 <= 0.01 -> 同点
    good_b_worse = {"値": 0.20}   # 差 0.10 > 0.01 -> jev(a) の勝ち
    good_nan = {"値": float("nan")}

    assert calib.choose_better(good_a, good_b_tied) == "code"
    assert calib.choose_better(good_a, good_b_worse) == "jev"
    assert calib.choose_better(good_b_worse, good_a) == "code"
    assert calib.choose_better(good_nan, good_a) == "code"
    assert calib.choose_better(good_a, good_nan) == "code"


def test_choose_better_exact_tie_boundary_is_code():
    # 差がちょうど 0.01(tie_eps)なら「差 0.01 以内」に含める(同点)
    assert calib.choose_better({"値": 0.50}, {"値": 0.51}) == "code"

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "phase2"))

import p2_03_run as run  # noqa: E402


# ===========================================================================
# 呼値の帯(境界値)
# ===========================================================================

def _bands():
    value = {
        "up_to_1000_yen": 1, "up_to_3000_yen": 1, "up_to_5000_yen": 1, "up_to_10000_yen": 1,
        "up_to_30000_yen": 5, "up_to_50000_yen": 10, "up_to_100000_yen": 10, "up_to_300000_yen": 50,
        "up_to_500000_yen": 100, "up_to_1000000_yen": 100, "up_to_3000000_yen": 500,
        "up_to_5000000_yen": 1000, "up_to_10000000_yen": 1000, "up_to_30000000_yen": 5000,
        "up_to_50000000_yen": 10000, "over_50000000_yen": 10000,
    }
    return run.parse_tick_bands(value)


@pytest.mark.parametrize("price,expected_tick", [
    (10_000, 1),
    (10_001, 5),
    (30_000, 5),
    (30_001, 10),
    (50_000, 10),
    (999, 1),
    (100_000_000, 10000),
])
def test_tick_band_boundaries(price, expected_tick):
    bands = _bands()
    assert run.tick_for_price(price, bands) == expected_tick


def test_tick_band_nan_price():
    bands = _bands()
    assert np.isnan(run.tick_for_price(float("nan"), bands))


# ===========================================================================
# 規則1: 誤プリント連
# ===========================================================================

def _series(n=20, level=1000.0):
    return [level] * n


def test_bad_print_catches_2bar_collapse():
    # 20行、行10-11 が約1/10価格に崩れ、行12で元の水準に復帰する。
    close = _series(20, 1000.0)
    close[10] = 100.0
    close[11] = 98.0
    open_ = list(close)  # open==close simplification for this synthetic tape
    close = np.array(close)
    open_ = np.array(open_)

    mask, one_sided, events = run.detect_bad_print_runs(open_, close)
    assert mask[10] and mask[11]
    assert not mask[9] and not mask[12]
    assert len(events) == 1
    assert events[0]["start"] == 10 and events[0]["end"] == 11 and events[0]["k"] == 2


def test_bad_print_leaves_real_market_move_10p8_6p0():
    # -10.8% -> +6.0%: 実際の相場変動を模した規模(30%閾値未満なので規則1は反応しない)。
    close = _series(20, 1000.0)
    close[10] = 1000.0 * (1 - 0.108)  # -10.8%
    close[11] = close[10] * 1.06      # +6.0%
    close = np.array(close)
    open_ = np.array(close)

    mask, one_sided, events = run.detect_bad_print_runs(open_, close)
    assert not mask.any()
    assert len(events) == 0


def test_bad_print_leaves_sustained_split():
    # 行10から水準が1/10に持続する(分割相当) -- 元の水準に戻らないので規則1は反応しない。
    close = _series(10, 1000.0) + _series(10, 100.0)
    close = np.array(close)
    open_ = np.array(close)

    mask, one_sided, events = run.detect_bad_print_runs(open_, close)
    assert not mask.any()
    assert len(events) == 0
    # 一方、規則2(split_candidate)はこの持続的な水準変化を拾う。
    split_mask = run.detect_split_candidates(close.tolist())
    assert split_mask[10]


def test_bad_print_planted_drift_recovery_3bar():
    # k=3 の連(規則の上限)。行5-7 が乖離し、行8 で復帰する。
    close = _series(15, 2000.0)
    close[5] = 2000.0 * 0.6
    close[6] = 2000.0 * 0.55
    close[7] = 2000.0 * 0.65
    close[8] = 2000.0 * 1.02  # 元の水準の+-5%以内に復帰
    close = np.array(close)
    open_ = np.array(close)

    mask, one_sided, events = run.detect_bad_print_runs(open_, close)
    assert mask[5] and mask[6] and mask[7]
    assert not mask[8] and not mask[4]
    assert len(events) == 1 and events[0]["k"] == 3


def test_bad_print_one_sided_is_informational_not_flagged():
    # open だけが乖離し、close は乖離しない行 -- 誤プリントとはしない(片側情報として計上)。
    close = _series(15, 1000.0)
    open_ = list(close)
    open_[7] = 1000.0 * 0.5  # open のみ50%乖離
    close = np.array(close)
    open_ = np.array(open_)

    mask, one_sided, events = run.detect_bad_print_runs(open_, close)
    assert not mask.any()
    assert one_sided == 1
    assert len(events) == 0


def test_bad_print_excludes_first_and_last_row():
    n = 10
    close = _series(n, 1000.0)
    close[0] = 100.0  # 先頭行(基準値がない)
    close[-1] = 100.0  # 末尾行(復帰確認行がない)
    close = np.array(close)
    open_ = np.array(close)
    mask, one_sided, events = run.detect_bad_print_runs(open_, close)
    assert not mask[0]
    assert not mask[-1]


# ===========================================================================
# 規則2: split_candidate (data_quality.py と同一ロジック)
# ===========================================================================

def test_split_candidate_detects_persistent_10to1():
    close = _series(5, 1000.0) + _series(5, 100.0)
    mask = run.detect_split_candidates(close)
    assert mask[5]
    assert not mask[4]


def test_split_candidate_does_not_fire_on_one_day_round_trip():
    # 誤プリント(1日だけ崩れて翌日戻る)は split_candidate ではない。
    close = _series(10, 1000.0)
    close[5] = 100.0
    mask = run.detect_split_candidates(close)
    assert not mask[5]


def test_split_candidate_null_rows_are_skipped():
    close = _series(10, 1000.0)
    close[4] = float("nan")
    close[5] = 100.0
    close[6] = 100.0
    mask = run.detect_split_candidates(close)
    # prev_close (row4) is NaN -> row5 cannot be evaluated as a split transition
    assert not mask[5]


# ===========================================================================
# 幽霊行(規則5)
# ===========================================================================

def test_ghost_row_detection():
    open_ = np.array([100.0, 100.0, 101.0])
    high = np.array([100.0, 100.0, 102.0])
    low = np.array([100.0, 100.0, 100.0])
    close = np.array([100.0, 100.0, 101.0])
    volume = np.array([1000.0, 0.0, 500.0])
    mask = run.detect_ghost_rows(open_, high, low, close, volume)
    assert mask[1]
    assert not mask[0] and not mask[2]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

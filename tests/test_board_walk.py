"""Board-walk cost function (④-1, EXEC_FLOOR_PREREG.md §8 step 2): pure,
no I/O -- exact arithmetic on hand-built books."""
from __future__ import annotations

import pytest

from bot.research.board import walk_book, walk_cost_bp


# ---------------------------------------------------------------------------
# walk_book
# ---------------------------------------------------------------------------

def test_walk_book_fills_within_one_level():
    vwap, filled, exhausted = walk_book([(100.0, 1.0), (101.0, 2.0)], 0.4)
    assert vwap == pytest.approx(100.0)
    assert filled == pytest.approx(0.4)
    assert exhausted is False


def test_walk_book_fills_exactly_one_level():
    vwap, filled, exhausted = walk_book([(100.0, 1.0), (101.0, 2.0)], 1.0)
    assert vwap == pytest.approx(100.0)
    assert filled == pytest.approx(1.0)
    assert exhausted is False


def test_walk_book_crosses_levels_size_weighted():
    # 1 @ 100 + 1 @ 101 -> vwap = (100*1 + 101*1) / 2 = 100.5
    vwap, filled, exhausted = walk_book([(100.0, 1.0), (101.0, 2.0), (102.0, 5.0)], 2.0)
    assert vwap == pytest.approx(100.5)
    assert filled == pytest.approx(2.0)
    assert exhausted is False


def test_walk_book_crosses_three_levels_size_weighted():
    # 1 @ 100 + 2 @ 101 + 0.5 @ 102 -> (100*1 + 101*2 + 102*0.5) / 3.5
    levels = [(100.0, 1.0), (101.0, 2.0), (102.0, 5.0)]
    vwap, filled, exhausted = walk_book(levels, 3.5)
    expected = (100.0 * 1.0 + 101.0 * 2.0 + 102.0 * 0.5) / 3.5
    assert vwap == pytest.approx(expected)
    assert filled == pytest.approx(3.5)
    assert exhausted is False


def test_walk_book_exhaustion_partial_fill():
    # Book only has 3.0 total; asking for 5.0 -> filled stops at 3.0, exhausted True
    levels = [(100.0, 1.0), (101.0, 2.0)]
    vwap, filled, exhausted = walk_book(levels, 5.0)
    expected = (100.0 * 1.0 + 101.0 * 2.0) / 3.0
    assert vwap == pytest.approx(expected)
    assert filled == pytest.approx(3.0)
    assert exhausted is True


def test_walk_book_exhaustion_empty_book():
    vwap, filled, exhausted = walk_book([], 1.0)
    assert vwap == 0.0
    assert filled == 0.0
    assert exhausted is True


def test_walk_book_zero_size_is_not_exhausted():
    vwap, filled, exhausted = walk_book([(100.0, 1.0)], 0.0)
    assert vwap == 0.0
    assert filled == 0.0
    assert exhausted is False


def test_walk_book_negative_size_is_not_exhausted():
    vwap, filled, exhausted = walk_book([(100.0, 1.0)], -1.0)
    assert vwap == 0.0
    assert filled == 0.0
    assert exhausted is False


def test_walk_book_skips_non_positive_level_size():
    # A padded/malformed level (size 0 or negative) is skipped, not consumed.
    levels = [(100.0, 0.0), (101.0, -1.0), (102.0, 2.0)]
    vwap, filled, exhausted = walk_book(levels, 1.0)
    assert vwap == pytest.approx(102.0)
    assert filled == pytest.approx(1.0)
    assert exhausted is False


def test_walk_book_exact_total_depth_not_exhausted():
    levels = [(100.0, 1.0), (101.0, 2.0)]
    vwap, filled, exhausted = walk_book(levels, 3.0)
    assert filled == pytest.approx(3.0)
    assert exhausted is False


# ---------------------------------------------------------------------------
# walk_cost_bp
# ---------------------------------------------------------------------------

def test_walk_cost_bp_buy_side_positive_cost():
    asks = [(10_001.0, 1.0), (10_002.0, 2.0)]
    mid = 10_000.0
    cost_bp, filled, exhausted = walk_cost_bp(asks, 2.0, mid, "buy")
    vwap = (10_001.0 * 1.0 + 10_002.0 * 1.0) / 2.0
    expected_bp = (vwap - mid) / mid * 1e4
    assert cost_bp == pytest.approx(expected_bp)
    assert cost_bp > 0
    assert filled == pytest.approx(2.0)
    assert exhausted is False


def test_walk_cost_bp_sell_side_positive_cost():
    bids = [(9_999.0, 1.0), (9_998.0, 2.0)]
    mid = 10_000.0
    cost_bp, filled, exhausted = walk_cost_bp(bids, 2.0, mid, "sell")
    vwap = (9_999.0 * 1.0 + 9_998.0 * 1.0) / 2.0
    expected_bp = (mid - vwap) / mid * 1e4
    assert cost_bp == pytest.approx(expected_bp)
    assert cost_bp > 0
    assert filled == pytest.approx(2.0)
    assert exhausted is False


def test_walk_cost_bp_exact_value_buy():
    # size fully within best level -> vwap == best price exactly
    asks = [(10_010.0, 5.0)]
    mid = 10_000.0
    cost_bp, filled, exhausted = walk_cost_bp(asks, 1.0, mid, "buy")
    # (10010 - 10000) / 10000 * 1e4 = 10.0 bp
    assert cost_bp == pytest.approx(10.0)
    assert filled == pytest.approx(1.0)
    assert exhausted is False


def test_walk_cost_bp_zero_size_returns_none():
    cost_bp, filled, exhausted = walk_cost_bp([(10_001.0, 1.0)], 0.0, 10_000.0, "buy")
    assert cost_bp is None
    assert filled == 0.0
    assert exhausted is False


def test_walk_cost_bp_empty_book_returns_none_and_exhausted():
    cost_bp, filled, exhausted = walk_cost_bp([], 1.0, 10_000.0, "buy")
    assert cost_bp is None
    assert filled == 0.0
    assert exhausted is True


def test_walk_cost_bp_non_positive_mid_returns_none():
    cost_bp, filled, exhausted = walk_cost_bp([(10_001.0, 1.0)], 1.0, 0.0, "buy")
    assert cost_bp is None
    # filled still reflects what the book could supply
    assert filled == pytest.approx(1.0)
    assert exhausted is False


def test_walk_cost_bp_rejects_bad_side():
    with pytest.raises(ValueError):
        walk_cost_bp([(10_001.0, 1.0)], 1.0, 10_000.0, "sideways")


def test_walk_cost_bp_exhaustion_propagates():
    asks = [(10_001.0, 0.5)]
    mid = 10_000.0
    cost_bp, filled, exhausted = walk_cost_bp(asks, 1.0, mid, "buy")
    assert filled == pytest.approx(0.5)
    assert exhausted is True
    # cost_bp is still reported for the size that DID fill
    assert cost_bp == pytest.approx((10_001.0 - mid) / mid * 1e4)

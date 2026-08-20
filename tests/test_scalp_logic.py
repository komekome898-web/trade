"""Pure-logic tests for the burst scalper's maker entry (scripts/run_scalp_paper.py).

The runner itself is a network app (bitFlyer WS + Binance polling) and stays
untested, but the fill decision is factored into ``RestingLimit`` — no clock,
no I/O — so the rule from scripts/research_scalp_opt.py (limit at the near
touch, filled by a print that comes to it inside the timeout) is verified here.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from run_scalp_paper import RestingLimit  # noqa: E402

T0 = 1_000.0
TIMEOUT = 10.0


def long_order(limit=100.0):
    return RestingLimit("LONG", limit, T0, TIMEOUT, size=1.0, signal_bps=12.0)


def short_order(limit=100.0):
    return RestingLimit("SHORT", limit, T0, TIMEOUT, size=1.0, signal_bps=-12.0)


# ---- long side -------------------------------------------------------------
@pytest.mark.parametrize("price", [99.5, 100.0])
def test_long_fills_on_print_at_or_below_limit(price):
    assert long_order().accepts(T0 + 1.0, price, "SELL")


def test_long_does_not_fill_on_print_above_limit():
    assert not long_order().accepts(T0 + 1.0, 100.5, "SELL")


def test_long_does_not_fill_on_print_after_timeout():
    order = long_order()
    assert not order.accepts(T0 + TIMEOUT + 0.5, 99.0, "SELL")
    assert order.expired(T0 + TIMEOUT + 0.5)
    assert not order.expired(T0 + TIMEOUT)


def test_long_ignores_prints_stamped_before_placement():
    assert not long_order().accepts(T0 - 0.5, 99.0, "SELL")


def test_long_ignores_buy_taker_prints():
    # a taker BUY lifts the ask; it never reaches a bid resting at the touch
    assert not long_order().accepts(T0 + 1.0, 99.0, "BUY")


def test_side_is_optional_on_the_tape():
    assert long_order().accepts(T0 + 1.0, 99.0, "")
    assert long_order().accepts(T0 + 1.0, 99.0, None)


# ---- short side (symmetric) ------------------------------------------------
@pytest.mark.parametrize("price", [100.5, 100.0])
def test_short_fills_on_print_at_or_above_limit(price):
    assert short_order().accepts(T0 + 1.0, price, "BUY")


def test_short_does_not_fill_on_print_below_limit():
    assert not short_order().accepts(T0 + 1.0, 99.5, "BUY")


def test_short_does_not_fill_on_print_after_timeout():
    assert not short_order().accepts(T0 + TIMEOUT + 0.1, 101.0, "BUY")


def test_short_ignores_sell_taker_prints():
    assert not short_order().accepts(T0 + 1.0, 101.0, "SELL")


# ---- scanning a tape -------------------------------------------------------
def test_first_fill_returns_earliest_qualifying_print():
    tape = [
        (T0 - 1.0, 98.0, "SELL"),    # before placement
        (T0 + 0.5, 100.5, "SELL"),   # above the limit
        (T0 + 1.0, 100.5, "BUY"),    # wrong taker side
        (T0 + 2.0, 99.9, "SELL"),    # <- fills here
        (T0 + 3.0, 99.0, "SELL"),
    ]
    assert long_order().first_fill(tape) == (T0 + 2.0, 99.9)


def test_first_fill_returns_none_when_the_tape_never_comes_to_the_limit():
    tape = [(T0 + t, 100.5, "SELL") for t in (1.0, 5.0, 9.0)]
    order = long_order()
    assert order.first_fill(tape) is None
    assert order.expired(T0 + TIMEOUT + 0.01)


def test_first_fill_none_when_qualifying_print_lands_after_timeout():
    tape = [(T0 + TIMEOUT + 1.0, 99.0, "SELL")]
    assert long_order().first_fill(tape) is None


def test_first_fill_short_side():
    tape = [(T0 + 1.0, 99.0, "BUY"), (T0 + 4.0, 100.0, "BUY")]
    assert short_order().first_fill(tape) == (T0 + 4.0, 100.0)

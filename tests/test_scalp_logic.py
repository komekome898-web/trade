"""Pure-logic tests for the burst scalper (scripts/run_scalp_paper.py).

The runner itself is a network app (bitFlyer WS + Binance polling) and stays
untested, but the fill decision is factored into ``RestingLimit`` — no clock,
no I/O — so the rule from scripts/research_scalp_opt.py (limit at the near
touch, filled by a print that comes to it inside the timeout) is verified here.
The exit side reuses the same object for its take-profit (E2 of
scripts/research_scalp_exits.py), so it is driven here too, by feeding a tape
and a clock straight into ``check_exit``.
"""
from __future__ import annotations

import json
import sys
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from run_scalp_paper import RestingLimit, ScalpPaper  # noqa: E402

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


# ---- storm-radar arming ----------------------------------------------------
# The radar (src/bot/radar.py, from scripts/research_storm_b.py G3) lowers the
# entry threshold inside 12:30-15:00 UTC. Only the pure decision surface is
# exercised here: threshold selection and the arm/disarm flip logging.
def utc_ts(hour, minute):
    return datetime(2026, 8, 20, hour, minute, tzinfo=timezone.utc).timestamp()


def make_scalper(tmp_path, monkeypatch, **over):
    monkeypatch.chdir(tmp_path)
    args = Namespace(thr_bps=10.0, thr_armed_bps=8.0, radar_start="12:30",
                     radar_end="15:00", window_sec=5.0, hold_sec=60.0,
                     cooldown_sec=30.0, entry="maker", fill_timeout_sec=10.0,
                     exit="maker_tp", tp_bps=10.0, fallback_sec=120.0,
                     notional=110000.0, daily_loss_cap=6000.0)
    for k, v in over.items():
        setattr(args, k, v)
    return ScalpPaper(args)


def test_threshold_is_10bps_before_the_radar_has_run(tmp_path, monkeypatch):
    s = make_scalper(tmp_path, monkeypatch)
    assert s.radar_armed is None
    assert s.threshold_bps() == 10.0


def test_threshold_drops_to_8bps_inside_the_window(tmp_path, monkeypatch):
    s = make_scalper(tmp_path, monkeypatch)
    assert s.update_radar(utc_ts(13, 0)) is True
    assert s.threshold_bps() == 8.0


def test_threshold_is_10bps_outside_the_window(tmp_path, monkeypatch):
    s = make_scalper(tmp_path, monkeypatch)
    assert s.update_radar(utc_ts(3, 0)) is False
    assert s.threshold_bps() == 10.0


def test_radar_state_logged_once_per_flip(tmp_path, monkeypatch):
    s = make_scalper(tmp_path, monkeypatch)
    for ts in (utc_ts(12, 0), utc_ts(12, 29), utc_ts(12, 30), utc_ts(14, 0),
               utc_ts(15, 0), utc_ts(16, 0)):
        s.update_radar(ts)
    events = [json.loads(line) for line in
              (tmp_path / "data" / "scalp_paper.jsonl").read_text(
                  encoding="utf-8").splitlines()]
    flips = [e for e in events if e["event"] == "radar_state"]
    assert [f["radar_armed"] for f in flips] == [False, True, False]
    assert [f["thr_bps"] for f in flips] == [10.0, 8.0, 10.0]
    assert flips[1]["window"] == "12:30-15:00 UTC"


def test_custom_radar_window_is_honoured(tmp_path, monkeypatch):
    s = make_scalper(tmp_path, monkeypatch, radar_start="23:00", radar_end="01:00")
    assert s.update_radar(utc_ts(23, 30)) is True
    assert s.threshold_bps() == 8.0
    assert s.update_radar(utc_ts(2, 0)) is False
    assert s.threshold_bps() == 10.0


# ---- exit rule -------------------------------------------------------------
# E2 of scripts/research_scalp_exits.py: a maker take-profit --tp-bps beyond
# the fill, falling back to the legacy taker exit at fill + --fallback-sec.
# The clock and the tape are handed to check_exit directly, so no I/O runs.
FILL = 2_000.0            # fill time
ENTRY = 10_000_000.0      # fill price, JPY
SPREAD = 500.0


def open_position(s, side, entry=ENTRY):
    """Put a filled position on the books the way the entry path does."""
    s.bid, s.ask = entry - SPREAD, entry + SPREAD
    s.position = {"side": side, "size": 1.0, "entry": entry, "t_entry": FILL,
                  "tp": s.make_tp(side, entry, 1.0, FILL)}
    return s.position


def exit_events(tmp_path):
    log = tmp_path / "data" / "scalp_paper.jsonl"
    if not log.exists():
        return []
    events = [json.loads(line) for line in
              log.read_text(encoding="utf-8").splitlines()]
    return [e for e in events if e["event"] == "exit"]


def test_long_take_profit_rests_above_the_fill(tmp_path, monkeypatch):
    s = make_scalper(tmp_path, monkeypatch)
    tp = open_position(s, "LONG")["tp"]
    assert tp.limit == pytest.approx(ENTRY * 1.001)
    # a LONG exits by resting an ASK, lifted by a taker BUY from below
    assert tp.side == "SHORT"


def test_short_take_profit_rests_below_the_fill(tmp_path, monkeypatch):
    s = make_scalper(tmp_path, monkeypatch)
    tp = open_position(s, "SHORT")["tp"]
    assert tp.limit == pytest.approx(ENTRY * 0.999)
    assert tp.side == "LONG"


@pytest.mark.parametrize("through", [0.0, 1_000.0])
def test_long_exits_at_the_limit_on_a_buy_print_at_or_through(
        tmp_path, monkeypatch, through):
    s = make_scalper(tmp_path, monkeypatch)
    tp = open_position(s, "LONG")["tp"]
    s.prints.append((FILL + 3.0, tp.limit + through, "BUY"))
    s.check_exit(FILL + 3.5, feeds_ok=True)
    assert s.position is None
    ev = exit_events(tmp_path)[-1]
    assert ev["exit_kind"] == "tp_maker"
    # filled AT the limit, however far the print ran through it
    assert ev["price"] == pytest.approx(tp.limit)
    assert ev["pnl_jpy"] == pytest.approx(round(tp.limit - ENTRY, 1))
    assert ev["trades"] == 1


@pytest.mark.parametrize("through", [0.0, 1_000.0])
def test_short_exits_at_the_limit_on_a_sell_print_at_or_through(
        tmp_path, monkeypatch, through):
    s = make_scalper(tmp_path, monkeypatch)
    tp = open_position(s, "SHORT")["tp"]
    s.prints.append((FILL + 3.0, tp.limit - through, "SELL"))
    s.check_exit(FILL + 3.5, feeds_ok=True)
    assert s.position is None
    ev = exit_events(tmp_path)[-1]
    assert ev["exit_kind"] == "tp_maker"
    assert ev["price"] == pytest.approx(tp.limit)
    assert ev["pnl_jpy"] == pytest.approx(round(ENTRY - tp.limit, 1))


def test_take_profit_ignores_the_wrong_taker_side_and_prints_before_the_fill(
        tmp_path, monkeypatch):
    s = make_scalper(tmp_path, monkeypatch)
    tp = open_position(s, "LONG")["tp"]
    s.prints.append((FILL - 1.0, tp.limit + 500.0, "BUY"))   # before the fill
    s.prints.append((FILL + 1.0, tp.limit + 500.0, "SELL"))  # wrong taker side
    s.check_exit(FILL + 2.0, feeds_ok=True)
    assert s.position is not None
    assert exit_events(tmp_path) == []


def test_no_take_profit_fill_exits_taker_at_the_fallback_deadline(
        tmp_path, monkeypatch):
    s = make_scalper(tmp_path, monkeypatch)
    open_position(s, "LONG")
    s.prints.append((FILL + 5.0, ENTRY + 200.0, "BUY"))   # short of the limit
    s.check_exit(FILL + 119.9, feeds_ok=True)
    assert s.position is not None
    s.check_exit(FILL + 120.0, feeds_ok=True)
    assert s.position is None
    ev = exit_events(tmp_path)[-1]
    assert ev["exit_kind"] == "fallback_taker"
    # taker: hits the bid and pays slippage
    assert ev["price"] == pytest.approx((ENTRY - SPREAD) * (1 - 2.0 / 1e4))


def test_fallback_waits_for_live_feeds(tmp_path, monkeypatch):
    s = make_scalper(tmp_path, monkeypatch)
    open_position(s, "LONG")
    s.check_exit(FILL + 300.0, feeds_ok=False)
    assert s.position is not None
    assert exit_events(tmp_path) == []


def test_take_profit_wins_a_tie_with_the_fallback_deadline(tmp_path, monkeypatch):
    s = make_scalper(tmp_path, monkeypatch)
    tp = open_position(s, "LONG")["tp"]
    s.prints.append((FILL + 120.0, tp.limit, "BUY"))
    s.check_exit(FILL + 120.0, feeds_ok=True)
    assert exit_events(tmp_path)[-1]["exit_kind"] == "tp_maker"


def test_maker_entry_fill_arms_the_take_profit(tmp_path, monkeypatch):
    s = make_scalper(tmp_path, monkeypatch)
    s.bid, s.ask = ENTRY - SPREAD, ENTRY + SPREAD
    s.place_limit("LONG", 12.0, FILL)
    s.prints.append((FILL + 1.0, s.pending.limit, "SELL"))
    s.check_pending(FILL + 1.5)
    assert s.position["t_entry"] == FILL + 1.0
    tp = s.position["tp"]
    assert tp.limit == pytest.approx(s.position["entry"] * 1.001)
    assert tp.t_signal == FILL + 1.0     # the TP clock starts at the fill


# ---- legacy taker exit (--exit taker) --------------------------------------
def test_taker_exit_holds_hold_sec_then_crosses(tmp_path, monkeypatch):
    s = make_scalper(tmp_path, monkeypatch, exit="taker")
    pos = open_position(s, "LONG")
    assert pos["tp"] is None
    # a print that would have filled a take-profit changes nothing
    s.prints.append((FILL + 1.0, ENTRY * 1.002, "BUY"))
    s.check_exit(FILL + 59.9, feeds_ok=True)
    assert s.position is not None
    s.check_exit(FILL + 60.0, feeds_ok=True)
    assert s.position is None
    ev = exit_events(tmp_path)[-1]
    assert ev["exit_kind"] == "taker"
    assert ev["price"] == pytest.approx((ENTRY - SPREAD) * (1 - 2.0 / 1e4))


def test_taker_exit_short_side_lifts_the_ask(tmp_path, monkeypatch):
    s = make_scalper(tmp_path, monkeypatch, exit="taker")
    open_position(s, "SHORT")
    s.check_exit(FILL + 60.0, feeds_ok=True)
    ev = exit_events(tmp_path)[-1]
    assert ev["price"] == pytest.approx((ENTRY + SPREAD) * (1 + 2.0 / 1e4))
    assert ev["pnl_jpy"] == pytest.approx(
        round(ENTRY - (ENTRY + SPREAD) * (1 + 2.0 / 1e4), 1))

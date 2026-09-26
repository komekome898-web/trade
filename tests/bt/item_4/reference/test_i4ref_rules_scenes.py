"""Scenes with hand-computed answers, one or more per rule of the scene book's
bar model (tests/bt/battery/item_4/DEFINITIONS.md, R-T .. R-O) and per
lead decision of the finish round (i4-r2-02, i4-r2-08).

Every expected value is written from the rule text with the formula in the
comment; none is copied from a run. Bar sets are the scene book's (i4ref_bar_kit).
Unless a test says otherwise: capital 6000, order amount 3000, costs 0, taker.
"""
from __future__ import annotations

import inspect

import pytest

from bot.bt.reference import bar_sim
from bot.bt.reference.bar_sim import RefusedConfig, dec, run_bars
from i4ref_bar_kit import (B, E, FB, H, HT, K, KD, M, MF, OA, OS, OU, OW, SB, SW, T, WL, WS, F, X,
                           close_to, fbs, fills, opts, run)

TAKER_C = dict(taker_fee_pct="0.1", maker_fee_pct=0, slippage_pct="0.02", spread_pct="0.04")


# ---------------------------------------------------------------- R-T, R-C, R-A
def test_rT1_rT2_rC1_rA_next_open_taker():
    # adj = (0.04/2 + 0.02)/100 = 0.0004
    # BUY@1 -> bar 2 open 100 * 1.0004 = 100.04 (R-T1, R-C1); size = 3000/100.04 (R-A1)
    # SELL@4 -> bar 5 open 106 * 0.9996 = 105.9576; BUY@9 is on the last bar: no fill (R-T2)
    r = run(B, {1: "BUY", 4: "SELL", 9: "BUY"}, costs=TAKER_C)
    size = F(3000) / X("100.04")
    assert fills(r) == [(2, "OPEN_LONG", X("100.04"), size), (5, "CLOSE_LONG", X("105.9576"), size)]
    # R-A2: fee = size * price * 0.1/100; R-A3: pnl = (exit-entry)*size - exit fee - entry fee
    fee_in, fee_out = size * X("100.04") / 1000, size * X("105.9576") / 1000
    assert fee_in == 3
    assert r.pnls == [(X("105.9576") - X("100.04")) * size - fee_out - fee_in]
    assert r.missed_fills == 0


def test_rA2_rA3_fee_scene():
    # i4-4-fee: pnl = 6*30 - 30*106*0.001 - 3000*0.001 = 180 - 3.18 - 3 = 173.82
    r = run(B, {1: "BUY", 4: "SELL"}, costs=dict(taker_fee_pct="0.1"))
    assert fbs(r) == [(2, "OPEN_LONG", 100), (5, "CLOSE_LONG", 106)]
    assert r.pnls == [X("173.82")]


def test_rT3_short_and_close_and_flat_close():
    # SELL@2 -> bar 3 open 120*0.9996 = 119.952 short; CLOSE@6 -> bar 7 open 103*1.0004 = 103.0412;
    # CLOSE@8 while flat does nothing (R-T3)
    r = run(B, {2: "SELL", 6: "CLOSE", 8: "CLOSE"}, costs=TAKER_C, allow_short=True)
    assert fbs(r) == [(3, "OPEN_SHORT", X("119.952")), (7, "CLOSE_SHORT", X("103.0412"))]


def test_rT3_opposite_signal_only_closes():
    # BUY@1 -> long at bar 2 open 100; SELL@3 closes at bar 4 open 125 and does not open a short
    # on the same bar even though short is allowed. pnl = 25*30 = 750
    r = run(B, {1: "BUY", 3: "SELL"}, allow_short=True)
    assert fbs(r) == [(2, "OPEN_LONG", 100), (4, "CLOSE_LONG", 125)]
    assert r.pnls == [750] and r.open_trade is None


def test_rT4_no_short():
    # SELL@1 flat, no short: nothing. BUY@2 -> 120, SELL@5 -> 105. pnl = (105-120)*25 = -375
    r = run(B, {1: "SELL", 2: "BUY", 5: "SELL"})
    assert fills(r) == [(3, "OPEN_LONG", 120, 25), (6, "CLOSE_LONG", 105, 25)]
    assert r.pnls == [-375]


def test_rA4_equity_marks_open_position_with_entry_fee():
    # BUY@1 -> bar 2 at 100.04, size s = 3000/100.04, entry fee 3.
    # equity[2] = 6000 + (103 - 100.04)*s - 3 ; equity[0] = equity[1] = 6000
    r = run(B, {1: "BUY", 4: "SELL"}, costs=TAKER_C)
    s = F(3000) / X("100.04")
    assert r.equity[:2] == [6000, 6000]
    assert r.equity[2] == 6000 + (103 - X("100.04")) * s - 3
    assert r.equity[9] == 6000 + r.pnls[0]


# ---------------------------------------------------------------- R-M
def test_rM1_strict_limit_entry_and_exit():
    # BUY@1 -> limit 100 (close of bar 1). bar 2 low 100 = touch: no fill; bar 3 low 99.5 < 100: fill 100.
    # SELL@4 -> exit limit 103 (close of bar 4); bar 5 high 105 > 103: fill 103.
    r = run(M, {1: "BUY", 4: "SELL"}, execution="maker", maker_timeout_bars=3)
    assert fills(r) == [(3, "OPEN_LONG", 100, 30), (5, "CLOSE_LONG", 103, 30)]
    assert all(f.liquidity == "maker" for f in r.fills) and r.missed_fills == 0


def test_rM1_short_strict():
    # SELL@1 -> limit 100; bar 2 high 100 touch; bar 3 high 100.5 > 100 -> short 100.
    # BUY@4 -> limit 99; bar 5 low 99 touch; bar 6 low 98.5 < 99 -> cover 99.
    r = run(SB, {1: "SELL", 4: "BUY"}, execution="maker", maker_timeout_bars=3, allow_short=True)
    assert fbs(r) == [(3, "OPEN_SHORT", 100), (6, "CLOSE_SHORT", 99)]


def test_rM1_maker_fee_side():
    # maker fill pays the maker rate: fee = 30*100*0.05/100 = 1.5 ; exit 30*103*0.05/100 = 1.545
    r = run(M, {1: "BUY", 4: "SELL"}, execution="maker", maker_timeout_bars=3,
            costs=dict(taker_fee_pct=1, maker_fee_pct="0.05"))
    assert [f.fee for f in r.fills] == [X("1.5"), X("1.545")]
    assert r.pnls == [90 - X("1.5") - X("1.545")]


def test_rM2_rM3_rM4_missed():
    # timeout 2. BUY@1 -> limit 101; bar 2 low 101 touch, bar 3 low 101.2: at bar 1+2 = 3 cancel, miss 1 (R-M2).
    # BUY@4 -> limit 99; bar 5 low 99.2 no. SELL@5 (flat, short ok) replaces it: miss 2 (R-M3), limit 100.
    # bar 6 high 100.8 > 100 -> short 100. CLOSE@7 -> buy limit 99.5 (R-M4); bar 8 low 99.2 -> 99.5.
    r = run(MF, {1: "BUY", 4: "BUY", 5: "SELL", 7: "CLOSE"}, execution="maker", maker_timeout_bars=2,
            allow_short=True)
    assert fbs(r) == [(6, "OPEN_SHORT", 100), (8, "CLOSE_SHORT", X("99.5"))]
    assert r.missed_fills == 2


def test_rM2_life_and_data_end():
    # M bars, life 3: BUY@1 -> limit 100, bar 3 low 99.5 -> long 100. SELL@6 is on the last bar:
    # its exit limit is never judged and is not a miss (R-M5, data end).
    r = run(M, {1: "BUY", 6: "SELL"}, execution="maker", maker_timeout_bars=3)
    assert fbs(r) == [(3, "OPEN_LONG", 100)] and r.missed_fills == 0
    # life 1: limit 100 placed at bar 1 is judged on bar 2 only (low 100 = touch) -> cancelled at
    # bar 1 + 1 = 2, miss 1. SELL@5 while flat without short: nothing.
    r = run(M, {1: "BUY", 5: "SELL"}, execution="maker", maker_timeout_bars=1)
    assert fills(r) == [] and r.missed_fills == 1
    # SB bars, life 1: SELL@1 -> 100, bar 2 high 100 touch -> miss 1; BUY@4 (flat) -> buy limit 99,
    # bar 5 low 99 touch -> miss 2.
    r = run(SB, {1: "SELL", 4: "BUY"}, execution="maker", maker_timeout_bars=1, allow_short=True)
    assert fills(r) == [] and r.missed_fills == 2
    # life 2: SELL@1 -> bar 3 high 100.5 > 100 -> short 100 (bar 3 = 1 + 2, last bar of the life).
    # BUY@4 -> exit limit 99: bar 5 touch, bar 6 low 98.5 < 99 -> 99 (bar 6 = 4 + 2).
    r = run(SB, {1: "SELL", 4: "BUY"}, execution="maker", maker_timeout_bars=2, allow_short=True)
    assert fbs(r) == [(3, "OPEN_SHORT", 100), (6, "CLOSE_SHORT", 99)] and r.missed_fills == 0
    # BUY@3 while short -> exit limit at the close of bar 3 = 100; bar 4 low 98 < 100 -> 100.
    r = run(SB, {1: "SELL", 3: "BUY"}, execution="maker", maker_timeout_bars=2, allow_short=True)
    assert fbs(r) == [(3, "OPEN_SHORT", 100), (4, "CLOSE_SHORT", 100)]


def test_rM2_exit_limit_expiry_miss():
    # T bars, life 1: BUY@0 -> limit 100, bar 1 low 99.5 -> long 100 at bar 1.
    # SELL@1 -> exit limit 100 (close of bar 1); bar 2 high 104 > 100 -> 100.
    r = run(T, {0: "BUY", 1: "SELL"}, execution="maker", maker_timeout_bars=1)
    assert fbs(r) == [(1, "OPEN_LONG", 100), (2, "CLOSE_LONG", 100)]
    # SELL@2 -> exit limit 99 (close of bar 2); bar 3 high 100 > 99 -> 99.
    r = run(T, {0: "BUY", 2: "SELL"}, execution="maker", maker_timeout_bars=1)
    assert fbs(r) == [(1, "OPEN_LONG", 100), (3, "CLOSE_LONG", 99)]
    # SELL@8 -> exit limit 99.5, life 1: bar 9 high 97 does not pass it -> cancelled at bar 9, miss 1,
    # the long stays open (R-M2 applies to every limit).
    r = run(T, {0: "BUY", 8: "SELL"}, execution="maker", maker_timeout_bars=1)
    assert fbs(r) == [(1, "OPEN_LONG", 100)] and r.missed_fills == 1 and r.open_trade is not None


# ---------------------------------------------------------------- i4-r2-08 (lead decision)
def test_r2_08_mask_false_places_no_limit_and_counts_no_miss():
    mask = [True, False, True, True, True, True, True]
    r = run(M, {1: "BUY"}, execution="maker", maker_timeout_bars=3, entry_mask=mask)
    assert fills(r) == [] and r.missed_fills == 0
    # waiting BUY limit (bar 1, 100) + SELL@2 blocked by the mask: no new limit, no miss,
    # the BUY limit stays and fills at bar 3 (low 99.5 < 100)
    mask = [True, True, False, True, True, True, True]
    r = run(M, {1: "BUY", 2: "SELL"}, execution="maker", maker_timeout_bars=3, entry_mask=mask,
            allow_short=True)
    assert fbs(r) == [(3, "OPEN_LONG", 100)] and r.missed_fills == 0


def test_r2_08_same_direction_signal_keeps_old_limit():
    # BUY@1 -> limit 100; BUY@2 (close 102) does not re-place. bar 3 low 99.5 < 100 -> 100.
    # (Re-placing at 102 would fill at 102.)
    r = run(M, {1: "BUY", 2: "BUY"}, execution="maker", maker_timeout_bars=3)
    assert fbs(r) == [(3, "OPEN_LONG", 100)] and r.missed_fills == 0
    # the old limit keeps its own life: placed at 1, life 2 -> judged on bars 2, 3; BUY@2 does not
    # extend it. With life 1 it is judged on bar 2 only (touch) -> miss 1 at bar 2, then BUY@2 is a
    # fresh limit at 102 (no limit waiting) -> bar 3 low 99.5 < 102 -> 102.
    r = run(M, {1: "BUY", 2: "BUY"}, execution="maker", maker_timeout_bars=1)
    assert fbs(r) == [(3, "OPEN_LONG", 102)] and r.missed_fills == 1


def test_undecided_same_side_exit_signal():
    # long at bar 3 (100). SELL@3 -> exit limit 101. CLOSE@4 (close 103) closes in the same direction.
    # keep: bar 5 high 105 > 101 -> 101. replace: limit 103 -> bar 5 high 105 > 103 -> 103.
    kw = dict(execution="maker", maker_timeout_bars=3)
    r = run(M, {1: "BUY", 3: "SELL", 4: "CLOSE"}, undecided=dict(same_side_exit_signal="keep"), **kw)
    # bar 4 high 104 > 101 already fills the kept limit on bar 4
    assert fbs(r) == [(3, "OPEN_LONG", 100), (4, "CLOSE_LONG", 101)]
    r = run(M, {1: "BUY", 4: "SELL", 5: "CLOSE"}, undecided=dict(same_side_exit_signal="keep"), **kw)
    # SELL@4 -> 103; bar 5 high 105 > 103 fills before CLOSE@5 matters
    assert fbs(r) == [(3, "OPEN_LONG", 100), (5, "CLOSE_LONG", 103)]
    # a case where keep and replace differ: SB short from bar 3 (100); BUY@3 exit limit 100 would fill
    # at bar 4. Use BUY@4 (limit 99) then CLOSE@5 (close 99.5):
    # keep: 99 -> bar 6 low 98.5 < 99 -> 99. replace: 99.5 -> bar 6 low 98.5 < 99.5 -> 99.5
    kw = dict(execution="maker", maker_timeout_bars=3, allow_short=True)
    a = run(SB, {1: "SELL", 4: "BUY", 5: "CLOSE"}, undecided=dict(same_side_exit_signal="keep"), **kw)
    b = run(SB, {1: "SELL", 4: "BUY", 5: "CLOSE"}, undecided=dict(same_side_exit_signal="replace"), **kw)
    assert fbs(a) == [(3, "OPEN_SHORT", 100), (6, "CLOSE_SHORT", 99)]
    assert fbs(b) == [(3, "OPEN_SHORT", 100), (6, "CLOSE_SHORT", X("99.5"))]
    assert a.missed_fills == b.missed_fills == 0


# ---------------------------------------------------------------- R-P
def test_rP_priority_stop_first_touch_tp_gap_stop():
    # stop 2% (98), tp 3% (103); taker 0.1%, maker 0.02%.
    # BUY@0 -> bar 1 open 100 (entry bar not judged, R-P2). bar 2 high 104 > 103 and low 97 <= 98 -> stop
    # first, min(100, 98) = 98 taker (R-P3). pnl = -60 - 30*98*0.001 - 3 = -65.94
    # BUY@3 -> bar 4 open 100; bar 5 high 103 touch; bar 6 high 103.5 > 103 -> 103 maker (R-P4).
    #   pnl = 90 - 30*103*0.0002 - 3 = 86.382
    # BUY@7 -> bar 8 open 100; bar 9 opens 96 < 98 -> min(96, 98) = 96. pnl = -120 - 2.88 - 3 = -125.88
    r = run(T, {0: "BUY", 3: "BUY", 7: "BUY"}, costs=dict(taker_fee_pct="0.1", maker_fee_pct="0.02"),
            stop_loss_pct=2, take_profit_pct=3)
    assert fbs(r) == [(1, "OPEN_LONG", 100), (2, "CLOSE_LONG", 98), (4, "OPEN_LONG", 100),
                      (6, "CLOSE_LONG", 103), (8, "OPEN_LONG", 100), (9, "CLOSE_LONG", 96)]
    assert [f.liquidity for f in r.fills[1::2]] == ["taker", "maker", "taker"]
    assert r.pnls == [X("-65.94"), X("86.382"), X("-125.88")]


def test_rP3_stop_price_carries_spread_and_slippage_short():
    # i4-1-ref-taker's short: entry 1010*0.9994 = 1009.394 (adj = (0.06/2+0.03)/100 = 0.0006),
    # stop 3% -> 1009.394*1.03 = 1039.67582; bar 10 high 1045 >= level -> max(1025, 1039.67582) * 1.0006
    r = run(E, {1: "BUY", 5: "SELL", 7: "SELL", 12: "BUY"}, allow_short=True, stop_loss_pct=3,
            costs=dict(taker_fee_pct="0.12", slippage_pct="0.03", spread_pct="0.06"), swap_daily_pct="0.72")
    assert r.fills[3].bar == 10 and r.fills[3].price == X("1009.394") * X("1.03") * X("1.0006")


# ---------------------------------------------------------------- R-X
def test_rX1_rX2_maker_tp():
    # BUY@0 -> bar 1 open 100 (taker 0.1% = 3). level 102. bar 1 high 103 is the entry bar (R-X2),
    # bar 2 high 102 touch, bar 3 high 102.5 > 102 -> 102 maker 0.02%. pnl = 60 - 0.612 - 3 = 56.388
    r = run(K, {0: "BUY"}, costs=dict(taker_fee_pct="0.1", maker_fee_pct="0.02"),
            exit_execution="maker_tp", maker_tp_pct=2)
    assert fbs(r) == [(1, "OPEN_LONG", 100), (3, "CLOSE_LONG", 102)]
    assert r.pnls == [X("56.388")]


def test_rX1_decimal_touch():
    # level = 100*(1+1.5/100) = 101.5 exactly; bar 2 high 101.5 touch (no fill); bar 3 high 101.6 -> 101.5
    bars = [tuple(float(v) for v in b) for b in KD]     # float input is read as the written decimal
    r = run(bars, {0: "BUY"}, exit_execution="maker_tp", maker_tp_pct=1.5)
    assert fbs(r) == [(1, "OPEN_LONG", 100), (3, "CLOSE_LONG", X("101.5"))]


def test_dec_reads_floats_as_written_decimal():
    assert dec(0.1, "x") == F(1, 10) and dec(101.49999999999999, "x") != X("101.5")
    assert dec("1.015", "x") * 100 == X("101.5")


@pytest.mark.parametrize("pct", [0, -1, None])
def test_rX3_refuses_maker_tp_without_positive_pct(pct):
    with pytest.raises(RefusedConfig):
        run(K, {0: "BUY"}, exit_execution="maker_tp", maker_tp_pct=pct)
    run(K, {0: "BUY"}, exit_execution="maker_tp", maker_tp_pct=2)   # control passes


# ---------------------------------------------------------------- R-W
def test_rW1_rW2_rW3_wick_long():
    # N = 3. BUY@2 -> bar 3 open 100. level = min(lows of bars 0..2 = 96, 98, 97) = 96 (bar 3 excluded).
    # bar 4 low 95 but close 96.5 >= 96: stays (R-W2). bar 5 close 95.5 < 96 -> bar 6 open 95 (R-W3).
    r = run(WL, {2: "BUY"}, stop_mode="wick_invalidation", stop_window_bars=3)
    assert fbs(r) == [(3, "OPEN_LONG", 100), (6, "CLOSE_LONG", 95)] and r.pnls == [-150]


def test_rW_wick_short():
    # level = max(104, 102, 103) = 104; bar 4 high 105 close 103.5 stays; bar 5 close 104.5 > 104 -> bar 6 open 105
    r = run(WS, {2: "SELL"}, allow_short=True, stop_mode="wick_invalidation", stop_window_bars=3)
    assert fbs(r) == [(3, "OPEN_SHORT", 100), (6, "CLOSE_SHORT", 105)]


def test_rW1_window_excludes_the_entry_bar():
    # N = 2. BUY@2 -> bar 3 open 100. level = min(lows of bars 1, 2) = min(98, 98) = 98; bar 3 (the entry
    # bar) has low 95 but is not in the window. bar 3 close 99 >= 98 stays; bar 4 close 97 < 98 ->
    # bar 5 open 97. pnl = -3*30 = -90. (With bar 3 in the window the level would be 95 and no exit.)
    bars = [(100, 101, 98, 100), (100, 101, 98, 100), (100, 101, 98, 100), (100, 101, 95, 99),
            (99, 100, 96, 97), (97, 98, 96, 97)]
    r = run(bars, {2: "BUY"}, stop_mode="wick_invalidation", stop_window_bars=2)
    assert fbs(r) == [(3, "OPEN_LONG", 100), (5, "CLOSE_LONG", 97)] and r.pnls == [-90]


def test_rW3_reading_entry_bar_close_counts():
    # Reading of R-W3 (SPEC.md section 4): the close of the entry bar is a close of a bar that holds the
    # position, so it is judged. WL, N = 3, BUY@3 -> bar 4 open 100; level = min(98, 97, 99) = 97.
    # bar 4 close 96.5 < 97 -> bar 5 open 96.5. pnl = -3.5*30 = -105
    r = run(WL, {3: "BUY"}, stop_mode="wick_invalidation", stop_window_bars=3)
    assert fbs(r) == [(4, "OPEN_LONG", 100), (5, "CLOSE_LONG", X("96.5"))] and r.pnls == [-105]


def test_rW3_wick_exit_drops_waiting_signal():
    # WL, N = 3, BUY@2 -> long bar 3; SELL@5 waits for bar 6, allow short. bar 5 close 95.5 < 96 ->
    # bar 6 open exit; the waiting SELL is dropped (else it would open a short at bar 6 or later).
    r = run(WL, {2: "BUY", 5: "SELL"}, allow_short=True, stop_mode="wick_invalidation", stop_window_bars=3)
    assert fbs(r) == [(3, "OPEN_LONG", 100), (6, "CLOSE_LONG", 95)]


def test_rW4_refuses_stacking_and_controls_pass():
    with pytest.raises(RefusedConfig):
        run(WL, {2: "BUY"}, stop_mode="wick_invalidation", stop_window_bars=3, stop_loss_pct=2)
    # control: percent stop alone. level 98; bar 4 low 95 <= 98 -> min(100, 98) = 98
    r = run(WL, {2: "BUY"}, stop_loss_pct=2)
    assert fbs(r) == [(3, "OPEN_LONG", 100), (4, "CLOSE_LONG", 98)]


def test_undecided_wick_short_history():
    # BUY@0 -> entry at bar 1, N = 3: only bar 0 is before it.
    kw = dict(stop_mode="wick_invalidation", stop_window_bars=3)
    with pytest.raises(RefusedConfig):
        run(WL, {0: "BUY"}, undecided=dict(wick_short_history="refuse"), **kw)
    # use_available: level = low of bar 0 = 96 -> bar 5 close 95.5 < 96 -> bar 6 open 95
    r = run(WL, {0: "BUY"}, undecided=dict(wick_short_history="use_available"), **kw)
    assert fbs(r) == [(1, "OPEN_LONG", 100), (6, "CLOSE_LONG", 95)]
    r = run(WL, {0: "BUY"}, undecided=dict(wick_short_history="no_stop"), **kw)
    assert fbs(r) == [(1, "OPEN_LONG", 100)]


# ---------------------------------------------------------------- R-H (+ i4-r2-02)
def test_rH1_rH2_time_exit_drops_signal():
    # N = 3. BUY@0 -> bar 1 open 100; bar 1+3 = 4: exit at bar 4 open 103 (R-H1).
    # SELL@3 waits for bar 4 and is dropped (R-H2): no short at bar 4 although short is allowed.
    r = run(H, {0: "BUY", 3: "SELL"}, allow_short=True, max_hold_bars=3)
    assert fbs(r) == [(1, "OPEN_LONG", 100), (4, "CLOSE_LONG", 103)] and r.open_trade is None


def test_rH3_tp_not_taken_on_time_bar():
    # N = 2, tp 2% (102), fees 0.1% both. BUY@0 -> bar 1 100; bar 3 is the time bar: exit at open 101,
    # the bar 3 high 103 > 102 is not taken. pnl = 30 - 30*101*0.001 - 3 = 23.97
    r = run(HT, {0: "BUY"}, costs=dict(taker_fee_pct="0.1", maker_fee_pct="0.1"), take_profit_pct=2,
            max_hold_bars=2)
    assert fbs(r) == [(1, "OPEN_LONG", 100), (3, "CLOSE_LONG", 101)] and r.pnls == [X("23.97")]


def test_r2_02_time_exit_at_open_before_range_stop():
    # i4-r2-02 decision: on the time bar the open event comes first. N = 2, stop 2% (98), tp 3%, mtp 2.5%.
    # BUY@1 -> bar 2 open 100; time bar 4: exit at open 101 (taker), although bar 4 low 97 <= 98.
    r = run(OA, {1: "BUY", 3: "SELL"}, stop_loss_pct=2, take_profit_pct=3, max_hold_bars=2,
            exit_execution="maker_tp", maker_tp_pct="2.5")
    assert fbs(r) == [(2, "OPEN_LONG", 100), (4, "CLOSE_LONG", 101)]
    assert r.fills[1].reason == "max_hold" and r.pnls == [30]


def test_r2_02_time_exit_at_open_before_range_stop_maker():
    # maker, life 3, N = 2, stop 2%. limit 100 at bar 1; bar 2 low 99.5 -> long 100 at bar 2.
    # SELL@3 -> exit limit 101. bar 4 = time bar: exit at open 101 taker; the stop (low 97) and the
    # exit limit (high 104) do not happen; the dropped limit is not a miss (R-M5).
    r = run(OA, {1: "BUY", 3: "SELL"}, execution="maker", maker_timeout_bars=3, stop_loss_pct=2,
            max_hold_bars=2)
    assert fbs(r) == [(2, "OPEN_LONG", 100), (4, "CLOSE_LONG", 101)]
    assert r.fills[1].liquidity == "taker" and r.fills[1].reason == "max_hold" and r.missed_fills == 0


# ---------------------------------------------------------------- R-E
def test_rE_mask_and_sides_long():
    # sides long, mask [T,T,F,T,F,F,T,T,T,T]. SELL@0 blocked (side). BUY@2 blocked (mask[2]).
    # BUY@3 -> bar 4 open 125 (mask[4] False is the fill bar: not looked at). SELL@5 closes at bar 6
    # open 105 although mask[5] is False (R-E3). SELL@6 flat: blocked by side.
    mask = [True, True, False, True, False, False, True, True, True, True]
    r = run(B, {0: "SELL", 2: "BUY", 3: "BUY", 5: "SELL", 6: "SELL"}, allow_short=True, entry_mask=mask,
            entry_sides="long")
    assert fbs(r) == [(4, "OPEN_LONG", 125), (6, "CLOSE_LONG", 105)]


def test_rE_sides_short():
    r = run(B, {1: "BUY", 2: "SELL", 5: "BUY"}, allow_short=True, entry_sides="short")
    assert fbs(r) == [(3, "OPEN_SHORT", 120), (6, "CLOSE_SHORT", 105)]


# ---------------------------------------------------------------- R-S
@pytest.mark.parametrize("sig,direction", [({1: "BUY", 4: "SELL"}, 1), ({1: "SELL", 4: "BUY"}, -1)])
def test_rS1_carry(sig, direction):
    # 1 h bars, 0.24%/day -> 0.24/100 * 3600/86400 = 0.0001 per bar. Entry bar 2 at 100 (size 30), exit
    # bar 5 at 104. carry on bars 3, 4, 5 = 30*(101 + 102 + 103)*0.0001 = 0.918.
    # pnl = +-120 - 0.918
    r = run(SW, sig, allow_short=True, bar_seconds=3600, swap_daily_pct="0.24")
    assert r.pnls == [direction * 120 - X("0.918")]
    # equity at bar 3 = 6000 + dir*(102 - 100)*30 - 30*101*0.0001
    assert r.equity[3] == 6000 + direction * 60 - X("0.303")


# ---------------------------------------------------------------- R-O1 pairs
def test_rO1_signal_at_open_before_range_long_and_short():
    kw = dict(stop_loss_pct=2, take_profit_pct=3, exit_execution="maker_tp", maker_tp_pct="2.5")
    r = run(OA, {1: "BUY", 3: "SELL"}, **kw)          # bar 4 open 101 before stop/tp/mtp in range
    assert fbs(r) == [(2, "OPEN_LONG", 100), (4, "CLOSE_LONG", 101)]
    r = run(OS, {1: "SELL", 3: "BUY"}, allow_short=True, **kw)   # bar 4 open 99, no new long
    assert fbs(r) == [(2, "OPEN_SHORT", 100), (4, "CLOSE_SHORT", 99)] and r.pnls == [30]


def test_rO1_stop_before_tp_plain():
    r = run(OA, {1: "BUY"}, stop_loss_pct=2, take_profit_pct=3)   # bar 4: min(101, 98) = 98
    assert fbs(r) == [(2, "OPEN_LONG", 100), (4, "CLOSE_LONG", 98)] and r.pnls == [-60]


def test_rO1_wick_first():
    # N = 2, level min(99.5, 99.5) = 99.5; bar 3 close 99.3 < 99.5 -> bar 4 open 99.5, before the
    # waiting SELL (same fill) and before tp 103 / mtp 102.5 in bar 4's range. pnl = -15
    r = run(OW, {1: "BUY", 3: "SELL"}, take_profit_pct=3, exit_execution="maker_tp", maker_tp_pct="2.5",
            stop_mode="wick_invalidation", stop_window_bars=2)
    assert fbs(r) == [(2, "OPEN_LONG", 100), (4, "CLOSE_LONG", X("99.5"))] and r.pnls == [-15]
    assert r.fills[1].reason == "wick_invalidation"


def test_rO1_wick_before_exit_limit_maker():
    # maker life 3, N = 2: limit 100 at bar 1, bar 2 low 99.5 -> long 100 at bar 2, level 99.5.
    # SELL@3 -> exit limit 99.3. bar 4: wick exit at open 99.5 (taker), limit dropped, no miss.
    r = run(OW, {1: "BUY", 3: "SELL"}, execution="maker", maker_timeout_bars=3,
            stop_mode="wick_invalidation", stop_window_bars=2)
    assert fbs(r) == [(2, "OPEN_LONG", 100), (4, "CLOSE_LONG", X("99.5"))]
    assert r.fills[1].liquidity == "taker" and r.missed_fills == 0


def test_rO1_tp_before_maker_tp():
    r = run(OU, {1: "BUY"}, take_profit_pct=3, exit_execution="maker_tp", maker_tp_pct="2.5")
    assert fbs(r) == [(2, "OPEN_LONG", 100), (4, "CLOSE_LONG", 103)] and r.pnls == [90]


def test_rO1_time_first():
    r = run(OU, {1: "BUY", 3: "SELL"}, take_profit_pct=3, max_hold_bars=2, exit_execution="maker_tp",
            maker_tp_pct="2.5")
    assert fbs(r) == [(2, "OPEN_LONG", 100), (4, "CLOSE_LONG", 101)] and r.pnls == [30]
    r = run(OU, {1: "BUY", 3: "SELL"}, max_hold_bars=2, exit_execution="maker_tp", maker_tp_pct="2.5")
    assert fbs(r) == [(2, "OPEN_LONG", 100), (4, "CLOSE_LONG", 101)]


def test_rO1_time_before_exit_limit_maker():
    r = run(OU, {1: "BUY", 3: "SELL"}, execution="maker", maker_timeout_bars=3, max_hold_bars=2)
    assert fbs(r) == [(2, "OPEN_LONG", 100), (4, "CLOSE_LONG", 101)]
    assert r.fills[1].liquidity == "taker" and r.missed_fills == 0


@pytest.mark.parametrize("kw,price,reason", [
    (dict(stop_loss_pct=2, take_profit_pct=3, exit_execution="maker_tp", maker_tp_pct="2.5"), 98, "stop_loss"),
    (dict(take_profit_pct=3, exit_execution="maker_tp", maker_tp_pct="2.5"), 103, "take_profit"),
    (dict(exit_execution="maker_tp", maker_tp_pct="2.5"), X("102.5"), "maker_tp"),
])
def test_rO1_range_exits_before_exit_limit(kw, price, reason):
    # maker life 3: long 100 at bar 2; SELL@3 -> exit limit 101. bar 4 reaches everything:
    # stop (OA low 97) -> 98 / tp 103 / mtp 102.5, each before the exit limit 101; no miss (R-M5).
    bars = OA if reason == "stop_loss" else OU
    r = run(bars, {1: "BUY", 3: "SELL"}, execution="maker", maker_timeout_bars=3, **kw)
    assert fbs(r) == [(2, "OPEN_LONG", 100), (4, "CLOSE_LONG", price)]
    assert r.fills[1].reason == reason and r.missed_fills == 0


# ---------------------------------------------------------------- whole scenes (scene book I4-1)
def _near(xs, ys):
    return len(xs) == len(ys) and all(close_to(a, b) for a, b in zip(xs, ys))


def test_scene_i4_1_ref_taker():
    r = run(E, {1: "BUY", 5: "SELL", 7: "SELL", 12: "BUY"}, allow_short=True, stop_loss_pct=3,
            costs=dict(taker_fee_pct="0.12", slippage_pct="0.03", spread_pct="0.06"), swap_daily_pct="0.72")
    assert [(f.bar, f.side) for f in r.fills] == [(2, "OPEN_LONG"), (6, "CLOSE_LONG"), (8, "OPEN_SHORT"),
                                                  (10, "CLOSE_SHORT"), (13, "OPEN_LONG")]
    assert _near([f.price for f in r.fills], [1010.606, 1017.3892, 1009.394, 1040.299625492, 1030.618])
    assert _near(r.pnls, [12.851316220169124, -99.1944954376298])
    assert _near(r.equity, [6000.0, 6000.0, 6009.443658953143, 6024.271173335603, 6039.098613505164,
                            6024.240820260319, 6012.851316220169, 6012.851316220169, 6001.50607501604,
                            5962.853992677528, 5913.656820782539, 5913.656820782539, 5913.656820782539,
                            5919.901399472219, 5925.708099917971, 5931.514771254974])
    assert r.missed_fills == 0


def test_scene_i4_1_ref_maker():
    r = run(FB, {1: "BUY", 6: "SELL", 11: "BUY"}, execution="maker", maker_timeout_bars=3, allow_short=True,
            costs=dict(taker_fee_pct="0.1", maker_fee_pct="0.01", slippage_pct="0.02", spread_pct="0.04"),
            stop_loss_pct=2, exit_execution="maker_tp", maker_tp_pct=2)
    assert fills(r) == [(3, "OPEN_LONG", 100, 30), (5, "CLOSE_LONG", 102, 30),
                        (8, "OPEN_SHORT", 102, F(3000, 102)), (10, "CLOSE_SHORT", X("104.081616"), F(3000, 102))]
    assert r.pnls == [X("59.394"), X("-64.585224")] and r.missed_fills == 1


# ---------------------------------------------------------------- the entry point takes no defaults
def test_entry_point_has_no_defaults_and_every_option_is_required():
    sig = inspect.signature(run_bars)
    assert all(p.default is inspect.Parameter.empty for p in sig.parameters.values())
    full = opts()
    assert set(full) == set(bar_sim.OPTION_KEYS)
    for k in bar_sim.OPTION_KEYS:
        partial = {a: b for a, b in full.items() if a != k}
        with pytest.raises(RefusedConfig):
            run_bars(B, {}, partial)
    for k in bar_sim.UNDECIDED:
        partial = dict(full, undecided={a: b for a, b in full["undecided"].items() if a != k})
        with pytest.raises(RefusedConfig):
            run_bars(B, {}, partial)
    for k in bar_sim.COST_KEYS:
        partial = dict(full, costs={a: b for a, b in full["costs"].items() if a != k})
        with pytest.raises(RefusedConfig):
            run_bars(B, {}, partial)


def test_bad_bar_is_refused():
    with pytest.raises(RefusedConfig):
        run([(100, 99, 101, 100)], {})

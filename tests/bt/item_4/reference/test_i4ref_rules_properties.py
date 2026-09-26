"""Property tests (grid) of the bar reference bot.bt.reference.bar_sim.

Inputs come from a fixed option grid crossed with seeded random bars and
signals; they are not built from the reference's branches. Each case is
checked against formulas taken from the rule text only:
  Q1  no look-ahead: a run on the first k bars equals the full run before bar k
  Q2  deterministic: two runs are identical
  Q3  open/close alternate, directions match, close size = open size,
      open size = order amount / fill price (R-A1)
  Q4  pnl identity R-A3 with the carry recomputed from R-S1 (bars entry < j <= exit)
  Q5  equity identity R-A4 at every bar, recomputed from the fills
  Q6  a close is never on its entry bar; taker entries are at open*(1+-adj) of
      the bar after a BUY/SELL signal that was allowed (R-T1, R-C1, R-E, R-T4)
  Q7  maker entries: price = close of an earlier allowed signal bar within the
      life, strictly passed on the fill bar (R-M1, R-M2)
  Q8  hold: exit bar - entry bar <= N; a trade still open at the end has
      entry + N > last bar (R-H1)
  Q9  percent stop / take profit / maker tp exits sit at the formula price and
      the bar reached the level (R-P3, R-P4, R-X1); wick exits happen at the
      open after a close beyond the frozen level (R-W1, R-W3)
  Q10 missed fills <= number of signals
  Q11 no exit is skipped: a trade is closed no later than the first bar after
      its entry bar whose range reaches its percent stop (R-P3) or strictly
      passes its take profit / maker tp (R-P4, R-X1), and no later than the
      bar after the first close beyond its structural level (R-W3)
Not in the grid (said here, as the review rule asks): negative fee rates,
bars with open == high == low == close runs longer than 3, capital other than
6000, and the wick option with fewer than N bars of history (fixed to
"use_available" in the grid; the other two values are scene tests).
"""
from __future__ import annotations

import itertools
import random
from fractions import Fraction as F

import pytest

from bot.bt.reference.bar_sim import run_bars
from i4ref_bar_kit import opts

GRID = list(itertools.product(
    ["taker", "maker"],                                 # execution
    [None, "fixed", "wick"],                            # stop
    [None, "0.6"],                                      # take profit %
    [None, "0.9"],                                      # maker tp %
    [None, 3],                                          # max hold
    [False, True],                                      # allow short
))
SEEDS = 3


def make_case(seed, execution, stop, tp, mtp, hold, short):
    rng = random.Random(f"{seed}-{execution}-{stop}-{tp}-{mtp}-{hold}-{short}")
    n = rng.randint(12, 30)
    px = F(1000)
    bars = []
    for _ in range(n):
        o = px + F(rng.randint(-30, 30), 10)
        c = o + F(rng.randint(-40, 40), 10)
        h = max(o, c) + F(rng.randint(0, 25), 10)
        l = min(o, c) - F(rng.randint(0, 25), 10)
        bars.append((o, h, l, c))
        px = c
    sigs = {i: rng.choice(["BUY", "SELL", "CLOSE"]) for i in range(n) if rng.random() < 0.35}
    mask = [rng.random() < 0.8 for _ in range(n)] if rng.random() < 0.5 else None
    kw = dict(
        execution=execution, maker_timeout_bars=rng.randint(1, 3) if execution == "maker" else None,
        allow_short=short, stop_loss_pct=F(rng.choice([5, 8, 12]), 10) if stop == "fixed" else None,
        take_profit_pct=F(tp) if tp else None, max_hold_bars=hold,
        exit_execution="maker_tp" if mtp else "signal", maker_tp_pct=mtp,
        stop_mode="wick_invalidation" if stop == "wick" else "fixed",
        stop_window_bars=rng.randint(1, 4) if stop == "wick" else None,
        swap_daily_pct=rng.choice([0, "0.5"]), bar_seconds=rng.choice([60, 3600]),
        entry_mask=mask, entry_sides=rng.choice(["both", "both", "long", "short"]),
        costs=dict(taker_fee_pct=rng.choice([0, "0.1"]), maker_fee_pct=rng.choice([0, "0.02"]),
                   slippage_pct=rng.choice([0, "0.01"]), spread_pct=rng.choice([0, "0.04"])),
        undecided=dict(wick_short_history="use_available",
                       same_side_exit_signal=rng.choice(["keep", "replace"])),
    )
    return bars, sigs, opts(**kw)


CASES = [(s,) + g for s in range(SEEDS) for g in GRID]


def pairs(r):
    fs = r.fills
    out = []
    for i in range(0, len(fs), 2):
        out.append((fs[i], fs[i + 1] if i + 1 < len(fs) else None))
    return out


def check(bars, sigs, o, r):
    n = len(bars)
    c = o["costs"]
    adj = (F(str(c["spread_pct"])) / 2 + F(str(c["slippage_pct"]))) / 100
    rate = {"taker": F(str(c["taker_fee_pct"])) / 100, "maker": F(str(c["maker_fee_pct"])) / 100}
    carry_rate = F(str(o["swap_daily_pct"])) / 100 * o["bar_seconds"] / 86400
    allowed = lambda d, sb: ((d == 1 or o["allow_short"]) and o["entry_sides"] in ("both", "long" if d == 1 else "short")
                             and (o["entry_mask"] is None or o["entry_mask"][sb]))
    closed = []
    # Q3 alternate, sizes
    for op, cl in pairs(r):
        assert op.side in ("OPEN_LONG", "OPEN_SHORT")
        d = 1 if op.side == "OPEN_LONG" else -1
        assert op.size == F(3000) / op.price and op.size > 0
        assert op.fee == op.size * op.price * rate[op.liquidity]
        if cl is not None:
            assert cl.side == ("CLOSE_LONG" if d == 1 else "CLOSE_SHORT") and cl.size == op.size
            assert cl.bar > op.bar                                                       # Q6
            assert cl.fee == cl.size * cl.price * rate[cl.liquidity]
            carry = sum((op.size * bars[j - 1][3] * carry_rate for j in range(op.bar + 1, cl.bar + 1)), F(0))
            closed.append((cl.bar, (cl.price - op.price) * op.size * d - cl.fee - op.fee - carry))  # Q4
        # Q6 / Q7 entries
        if op.liquidity == "taker":
            assert o["execution"] == "taker"
            s = sigs.get(op.bar - 1)
            assert s == ("BUY" if d == 1 else "SELL") and allowed(d, op.bar - 1)
            assert op.price == bars[op.bar][0] * (1 + d * adj)
        else:
            assert o["execution"] == "maker"
            life = o["maker_timeout_bars"]
            ok = [p for p in range(max(0, op.bar - life), op.bar)
                  if sigs.get(p) == ("BUY" if d == 1 else "SELL") and allowed(d, p) and bars[p][3] == op.price]
            assert ok
            assert (bars[op.bar][2] < op.price) if d == 1 else (bars[op.bar][1] > op.price)
        # Q8 hold
        if o["max_hold_bars"] is not None:
            end = cl.bar if cl is not None else n - 1
            assert end - op.bar <= o["max_hold_bars"]
        # Q9 exit prices
        if cl is not None:
            o_, h, l, cc = bars[cl.bar]
            if cl.reason == "stop_loss":
                lvl = op.price * (1 - d * o["stop_loss_pct"] / 100)
                assert (l <= lvl) if d == 1 else (h >= lvl)
                base = min(o_, lvl) if d == 1 else max(o_, lvl)
                assert cl.price == base * (1 - d * adj) and cl.liquidity == "taker"
            elif cl.reason in ("take_profit", "maker_tp"):
                pct = o["take_profit_pct"] if cl.reason == "take_profit" else F(o["maker_tp_pct"])
                lvl = op.price * (1 + d * pct / 100)
                assert cl.price == lvl and ((h > lvl) if d == 1 else (l < lvl)) and cl.liquidity == "maker"
            elif cl.reason in ("wick_invalidation", "max_hold", "signal"):
                assert cl.price == o_ * (1 - d * adj) and cl.liquidity == "taker"
                if cl.reason == "max_hold":
                    assert cl.bar - op.bar == o["max_hold_bars"]
                if cl.reason == "wick_invalidation":
                    N = o["stop_window_bars"]
                    win = bars[max(0, op.bar - N):op.bar]
                    lvl = min(b[2] for b in win) if d == 1 else max(b[1] for b in win)
                    prev_close = bars[cl.bar - 1][3]
                    assert (prev_close < lvl) if d == 1 else (prev_close > lvl)
            else:
                assert cl.reason == "exit_limit" and cl.liquidity == "maker"
                assert (h > cl.price) if d == 1 else (l < cl.price)
    # Q11 no skipped exit
    for op, cl in pairs(r):
        d = 1 if op.side == "OPEN_LONG" else -1
        end = cl.bar if cl is not None else n
        levels = []
        if o["stop_loss_pct"] is not None:
            lv = op.price * (1 - d * o["stop_loss_pct"] / 100)
            levels.append(lambda b, lv=lv: (b[2] <= lv) if d == 1 else (b[1] >= lv))
        for pct in (o["take_profit_pct"], None if o["maker_tp_pct"] is None else F(o["maker_tp_pct"])):
            if pct is not None:
                lv = op.price * (1 + d * pct / 100)
                levels.append(lambda b, lv=lv: (b[1] > lv) if d == 1 else (b[2] < lv))
        for j in range(op.bar + 1, n):
            if any(f(bars[j]) for f in levels):
                assert end <= j, (op, j)
                break
        if o["stop_mode"] == "wick_invalidation":
            N = o["stop_window_bars"]
            win = bars[max(0, op.bar - N):op.bar]
            if win:
                lv = min(b[2] for b in win) if d == 1 else max(b[1] for b in win)
                for j in range(op.bar, n - 1):
                    if (bars[j][3] < lv) if d == 1 else (bars[j][3] > lv):
                        assert end <= j + 1, (op, j)
                        break
    # Q4 the reported pnls equal the recomputed ones, in closing order
    assert r.pnls == [p for _, p in closed]
    # Q5 equity at every bar
    assert len(r.equity) == n
    for i in range(n):
        eq = F(6000) + sum((p for b, p in closed if b <= i), F(0))
        for op, cl in pairs(r):
            if op.bar <= i and (cl is None or cl.bar > i):
                d = 1 if op.side == "OPEN_LONG" else -1
                carry = sum((op.size * bars[j - 1][3] * carry_rate for j in range(op.bar + 1, i + 1)), F(0))
                eq += (bars[i][3] - op.price) * op.size * d - op.fee - carry
        assert r.equity[i] == eq, i
    # Q10
    assert 0 <= r.missed_fills <= len(sigs)


@pytest.mark.parametrize("case", CASES)
def test_grid_properties(case):
    bars, sigs, o = make_case(*case)
    r = run_bars(bars, sigs, o)
    check(bars, sigs, o, r)
    # Q2 deterministic
    assert run_bars(bars, sigs, o).to_dict() == r.to_dict()
    # Q1 no look-ahead: first k bars
    k = len(bars) // 2 + case[0]
    ok = dict(o, entry_mask=None if o["entry_mask"] is None else o["entry_mask"][:k])
    rk = run_bars(bars[:k], {i: s for i, s in sigs.items() if i < k}, ok)
    assert [f for f in r.fills if f.bar < k] == rk.fills
    assert r.equity[:k] == rk.equity
    assert rk.pnls == r.pnls[:len(rk.pnls)]


def test_grid_is_not_vacuous():
    seen = {}
    for case in CASES:
        bars, sigs, o = make_case(*case)
        r = run_bars(bars, sigs, o)
        for f in r.fills:
            seen[(f.side[:4], f.reason)] = seen.get((f.side[:4], f.reason), 0) + 1
        seen["missed"] = seen.get("missed", 0) + r.missed_fills
    for key in [("OPEN", "signal"), ("OPEN", "entry_limit"), ("CLOS", "signal"), ("CLOS", "exit_limit"),
                ("CLOS", "stop_loss"), ("CLOS", "take_profit"), ("CLOS", "maker_tp"),
                ("CLOS", "max_hold"), ("CLOS", "wick_invalidation"), "missed"]:
        assert seen.get(key, 0) > 0, (key, seen)

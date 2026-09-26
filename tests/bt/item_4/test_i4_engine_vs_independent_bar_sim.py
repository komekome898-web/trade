"""The new engine's bar model against the INDEPENDENT reference (round 2, i4-r1-03).

`bot.bt.reference.bar_sim.run_bars` was written by the reference role (台本の役 `参照実装:4`) from the item-4 row
of the delegation and the requirement file only, without reading the core (src/bot/bt/reference/SPEC.md §0). Until
round 2 nothing compared the new engine with it (the battery's I4-1 scenes use bar_rules.py, which the item-4
worker wrote -- not independent). This file is that comparison, on every cell of the space where both define the
same rule. The reference's caller-selected modes are fixed to the stated rules of the battery
(tests/bt/battery/item_4/DEFINITIONS.md): limit_cross="strict" (R-M1 / R-P4 / R-X1), stop_trigger="touch" and
stop_fill="worse_of_level_and_open" (R-P3: range reaches the level, price min(open, level)), tp_fee="maker" (R-A2),
exits_from_entry_bar=False (R-P2 / R-X2), mask_applies_to="signal_bar" (R-E2), close_at_end=False.

Mapping (the test builds the same input for both, it does not look at either engine's result to build it):
the engine sizes each entry by notional / price and the reference trades a fixed quantity, so trades are compared
by bar, price, reason and PnL PER UNIT (the PnL is linear in the quantity: fees are price x qty x rate); the
engine's percentage levels are handed to the reference as the same distance from the same entry price
(entry x pct / 100 in exact rationals: the next bar's open for a taker entry, the signal bar's close for a limit).

Grid: direction {long, short} x execution {taker, maker with timeout 1, maker with timeout 3} x protective exits
{none, sl, tp, maker_tp, sl+tp, sl+maker_tp} x max_hold_bars {None, 3} x entry mask {none, seeded} (taker) x
entry_sides {both, the direction, the other} (taker) x fees {0, taker 0.1 % / maker 0.02 %} x 4 seeded bar and
signal scripts = 1920 runs of each engine.

Differences found are RESULTS of the comparison (SPEC.md §7-2), each pinned by its own test, not hidden:
  D1 (R-H3 vs the reference's B4): on the time-exit bar the stated rules look at the stop first; the reference
     closes at the open. Allowed only in exactly that shape (same exit bar, engine "stop_loss", reference
     "max_hold") and counted (test_the_grid_reaches_every_path).
  D2 (R-M1 re-signal vs the reference's [決め] 「建ての待ち中の合図は無視」): a same-side signal while a limit is
     pending places a new limit at the new close in the engine; the reference keeps the old one.
     test_d2_same_side_signal_while_a_limit_waits pins it.
  D3 (a masked / side-filtered limit): the engine places the limit and counts a missed fill when it times out
     unfilled; the reference ignores the signal. test_d3_filtered_limit pins it.

Not in the grid (named): spread and slippage (the reference has none); the carry, the wick stop, closing by a
signal, both directions in one script (the reference keeps one position and ignores signals while in it; the
engine closes on an opposite signal -- R-T3); maker cells with a mask or a filtering entry_sides (D3) or with two
signals closer than the timeout (D2); equity per bar (the quantities differ); metrics.
"""
from __future__ import annotations

import itertools
import math
import random
from fractions import Fraction

import pytest

from bot.bt.compat import bar_events, options_from_mapping, run_bars
from bot.bt.reference.bar_sim import Signal, make_bar
from bot.bt.reference.bar_sim import run_bars as ref_run_bars

NS = 1_000_000_000
T0 = 1767571200 * NS
N_BARS = 30
DIRS = ("long", "short")
EXECS = (("taker", 1), ("maker", 1), ("maker", 3))
EXITS = ("none", "sl", "tp", "mtp", "sl+tp", "sl+mtp")
HOLDS = (None, 3)
FEES = ((0.0, 0.0), (0.1, 0.02))
SEEDS = range(4)
SL_PCT, TP_PCT = 1.5, 2.0


def cells():
    out = []
    for d, (ex, k), exits, hold, fees, seed in itertools.product(DIRS, EXECS, EXITS, HOLDS, FEES, SEEDS):
        other = "short" if d == "long" else "long"
        masks = (False, True) if ex == "taker" else (False,)
        sides = ("both", d, other) if ex == "taker" else ("both", d)
        for m in masks:
            for s in sides:
                out.append((d, ex, k, exits, hold, m, s, fees, seed))
    return out


CELLS = cells()


def make_bars(rng: random.Random) -> list[tuple]:
    out, p = [], 100.0
    for _ in range(N_BARS):
        o = p + rng.choice((0.0, 0.0, 0.5, -0.5, 2.0, -2.0))
        c = o + rng.choice((-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5))
        h = max(o, c) + rng.choice((0.0, 0.5, 1.0, 2.5))
        lo = min(o, c) - rng.choice((0.0, 0.5, 1.0, 2.5))
        out.append((o, h, lo, c))
        p = c
    return out


def make_script(rng: random.Random, ex: str, k: int) -> list[bool]:
    """Where the (one-sided) entry signals are. For the maker execution two signals are at least `k` bars apart
    (D2 is pinned separately)."""
    sig, last = [False] * N_BARS, -10**9
    for i in range(N_BARS):
        if rng.random() < 0.3 and (ex == "taker" or i - last >= k):
            sig[i], last = True, i
    return sig


def _q(x: float) -> Fraction:
    return Fraction(repr(float(x)))


def run_engine(cell, bars, script, mask):
    d, ex, k, exits, hold, _, sides, fees, _ = cell
    cfg = {"initial_equity": 10000.0, "order_notional": 3000.0,
           "costs": {"taker_fee_pct": fees[0], "maker_fee_pct": fees[1], "slippage_pct": 0.0, "spread_pct": 0.0},
           "execution": ex, "maker_timeout_bars": k, "allow_short": d == "short", "swap_daily_pct": 0.0,
           "bar_seconds": 60.0, "stop_loss_pct": SL_PCT if "sl" in exits else None,
           "take_profit_pct": TP_PCT if exits in ("tp", "sl+tp") else None, "max_hold_bars": hold,
           "exit_execution": "maker_tp" if "mtp" in exits else "signal",
           "maker_tp_pct": TP_PCT if "mtp" in exits else None, "entry_mask": mask, "entry_sides": sides,
           "stop_mode": "fixed", "stop_window_bars": None}
    rows = [{"open": b[0], "high": b[1], "low": b[2], "close": b[3], "volume": 1.0} for b in bars]
    ev = bar_events(rows, [T0 + i * 60 * NS for i in range(len(bars))], 60 * NS)
    word = "BUY" if d == "long" else "SELL"
    res = run_bars(ev, lambda n: word if script[n - 1] else None, options_from_mapping(cfg), "spec", start=0)
    trades, cur = [], None
    for f in res.fills:
        if f["side"].startswith("OPEN_"):
            cur = {"entry_bar": f["bar"], "entry_price": f["price"], "size": f["size"]}
        else:
            cur.update(exit_bar=f["bar"], exit_price=f["price"], reason=f["reason"])
            trades.append(cur)
            cur = None
    for t, pnl in zip(trades, res.trade_pnls):
        t["pnl_per_unit"] = pnl / t["size"]
    return {"trades": trades, "open": cur, "missed": res.missed_fills, "reasons": {f["reason"] for f in res.fills}}


def run_reference(cell, bars, script, mask):
    d, ex, k, exits, hold, _, sides, fees, _ = cell
    rb = [make_bar(T0 + i * 60 * NS, str(b[0]), str(b[1]), str(b[2]), str(b[3])) for i, b in enumerate(bars)]
    sigs, n = [], len(bars)
    for i in range(n):
        if not script[i]:
            sigs.append(None)
            continue
        if ex == "taker":
            entry = _q(bars[i + 1][0]) if i + 1 < n else Fraction(1)
            limit = None
        else:
            entry = _q(bars[i][3])
            limit = str(bars[i][3])
        sl = entry * _q(SL_PCT) / 100 if "sl" in exits else None
        tp = entry * _q(TP_PCT) / 100 if exits in ("tp", "sl+tp", "mtp", "sl+mtp") else None
        sigs.append(Signal(side=d, limit=limit, sl_dist=sl, tp_dist=tp))
    res = ref_run_bars(rb, sigs, qty=1, initial_cash=10000, taker_rate=_q(fees[0]) / 100, maker_rate=_q(fees[1]) / 100,
                       limit_cross="strict", stop_trigger="touch", stop_fill="worse_of_level_and_open", tp_fee="maker",
                       exits_from_entry_bar=False, limit_valid_bars=k, mask=list(mask) if mask else None,
                       mask_applies_to="signal_bar", entry_sides=sides, max_hold_bars=hold, close_at_end=False)
    trades = [{"entry_bar": t.entry_bar, "entry_price": t.entry_price, "exit_bar": t.exit_bar,
               "exit_price": t.exit_price, "reason": t.reason, "pnl_per_unit": t.pnl / t.qty} for t in res.trades]
    op = res.open_trade
    return {"trades": trades, "open": None if op is None else {"entry_bar": op.entry_bar, "entry_price": op.entry_price},
            "missed": res.missed_fills}


REASON = {"stop_loss": "stop", "take_profit": "take_profit", "maker_tp": "take_profit", "time_exit": "max_hold"}


def _eq(a, b) -> bool:
    return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-9)


def compare(cell):
    """None when the two agree up to the named difference D1; else a description. Also returns D1's count."""
    seed = cell[-1]
    rng = random.Random(f"{seed}-{cell[1]}-{cell[2]}")
    bars = make_bars(rng)
    script = make_script(rng, cell[1], cell[2])
    mask = tuple(rng.random() < 0.7 for _ in range(N_BARS)) if cell[5] else None
    e, r = run_engine(cell, bars, script, mask), run_reference(cell, bars, script, mask)
    d1 = 0
    if len(e["trades"]) != len(r["trades"]):
        return f"trade count {len(e['trades'])} vs {len(r['trades'])}", 0, e["reasons"]
    for te, tr in zip(e["trades"], r["trades"]):
        if te["entry_bar"] != tr["entry_bar"] or not _eq(te["entry_price"], tr["entry_price"]) \
                or te["exit_bar"] != tr["exit_bar"]:
            return f"trade {te} vs {tr}", 0, e["reasons"]
        if REASON.get(te["reason"]) == tr["reason"]:
            if not (_eq(te["exit_price"], tr["exit_price"]) and _eq(te["pnl_per_unit"], tr["pnl_per_unit"])):
                return f"trade values {te} vs {tr}", 0, e["reasons"]
        elif te["reason"] == "stop_loss" and tr["reason"] == "max_hold" and cell[4] is not None \
                and te["exit_bar"] == te["entry_bar"] + cell[4]:
            d1 += 1  # D1: R-H3 (stop first on the time-exit bar) vs the reference's B4
        else:
            return f"reason {te} vs {tr}", 0, e["reasons"]
    if (e["open"] is None) != (r["open"] is None) or (e["open"] and (
            e["open"]["entry_bar"] != r["open"]["entry_bar"] or not _eq(e["open"]["entry_price"], r["open"]["entry_price"]))):
        return f"open trade {e['open']} vs {r['open']}", 0, e["reasons"]
    if e["missed"] != r["missed"]:
        return f"missed fills {e['missed']} vs {r['missed']}", 0, e["reasons"]
    return None, d1, e["reasons"]


CHUNK = 120


@pytest.mark.parametrize("start", range(0, len(CELLS), CHUNK))
def test_engine_agrees_with_the_independent_reference(start):
    bad = []
    for cell in CELLS[start:start + CHUNK]:
        why, _, _ = compare(cell)
        if why:
            bad.append((cell, why))
    assert not bad, f"{len(bad)} cells differ: {bad[:3]}"


def test_the_grid_reaches_every_path():
    assert len(CELLS) == 1920
    d1, reasons, missed = 0, set(), 0
    for cell in CELLS:
        why, n, rs = compare(cell)
        d1 += n
        reasons |= rs
    assert {"open", "stop_loss", "take_profit", "maker_tp", "time_exit"} <= reasons, reasons
    assert d1 > 0, "the named difference D1 never occurs: the grid does not reach the time-exit bar with a stop"


def _one_side_run(ex_script, mask=None, sides="both"):
    bars = [(100, 101, 99, 100), (100, 101, 100, 100.5), (100.8, 101, 100.6, 100.8), (100.8, 101, 99, 99.5),
            (99.5, 100, 98, 98.5), (98.5, 99, 97, 98)]
    cell = ("long", "maker", 3, "none", None, mask is not None, sides, (0.0, 0.0), 0)
    return run_engine(cell, bars, ex_script, mask), run_reference(cell, bars, ex_script, mask)


def test_d2_same_side_signal_while_a_limit_waits():
    """BUY at bar 0 (limit 100; bar 1's low 100 only touches it), BUY again at bar 1 (close 100.5) while the first
    limit waits: the engine replaces the limit with one at 100.5 (bar 2's low 100.6 does not reach it, bar 3's low
    99 < 100.5 fills it at 100.5); the reference ignores the second signal and fills the first limit at 100 on
    bar 3 (99 < 100, still inside its 3 bars)."""
    script = [True, True, False, False, False, False]
    e, r = _one_side_run(script)
    assert e["open"] == {"entry_bar": 3, "entry_price": 100.5, "size": pytest.approx(3000 / 100.5)}
    assert r["open"]["entry_bar"] == 3 and r["open"]["entry_price"] == 100


def test_d3_filtered_limit():
    """BUY at bar 0 with the mask False at bar 0: the engine places the limit, never fills it (entry filtered) or
    lets it time out -> missed 1 when no bar trades through; the reference ignores the signal (missed 0)."""
    script = [True, False, False, False, False, False]
    bars_high = [(100, 101, 100, 100), (100, 101, 100, 100.5), (100.5, 101, 100.2, 100.8), (100.8, 101, 100.1, 100.5),
                 (100.5, 101, 100.2, 100.5), (100.5, 101, 100.3, 100.5)]
    cell = ("long", "maker", 3, "none", None, True, "both", (0.0, 0.0), 0)
    mask = (False, True, True, True, True, True)
    e, r = run_engine(cell, bars_high, script, mask), run_reference(cell, bars_high, script, mask)
    assert (e["missed"], r["missed"]) == (1, 0)

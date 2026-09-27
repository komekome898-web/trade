"""Critic of K1 stage A (2026-09-27): K1WickStrategy on the core, against a second
reading of the rule text of docs/PHASE2/K1/RESULT.md 1.3 / 1.4 written here without
calling signal_of_bar or the old script. Seeded random bars (0.5-dollar grid, dojis,
ties of the truncated wicks) over all 13 gates x 3 strengths; every round trip
(side, entry price, exit price, entry bar, exit bar, reason) must be the same."""
from __future__ import annotations

import random

import pytest

from bot.bt.core import BarEvent, CoreEngine, NullAccount, ZeroLatency
from bot.bt.repro.fixed import DeclaredFeeCost
from bot.bt.report.trades import round_trips
from bot.strategy.k1_wick import BarCloseMarketFill, K1WickStrategy, gate_label, gates

NS = 10**9
IV = 60 * NS


def random_bars(seed: int, n: int = 400) -> list[tuple[float, float, float, float]]:
    rng = random.Random(seed)
    px, out = 4000.0, []
    for _ in range(n):
        o = px
        r = rng.random()
        c = o if r < 0.08 else round((o + rng.uniform(-12, 12)) * 2) / 2
        h = max(o, c) + round(rng.uniform(0, 1) ** 2 * 25 * 2) / 2
        l = min(o, c) - round(rng.uniform(0, 1) ** 2 * 25 * 2) / 2
        out.append((o, h, l, c))
        px = c
    return out


def rule_text(rows, s, b, keep):
    """RESULT.md 1.3 / 1.4 read again. Returns [(side, entry_px, exit_px, entry_i, exit_i, reason)]."""
    def signal(o, h, l, c):
        if c == o:
            return None, 0
        colour = 1 if c > o else -1
        top = h - max(o, c)
        under = min(o, c) - l
        if int(top) == int(under):
            return None, colour
        d, w, line = (-1, top, h) if int(top) > int(under) else (1, under, l)
        wbp = w / c * 10000
        small = s != "off" and (s == "-" or wbp >= float(s)) and w > abs(c - o)
        big = b != "-" and wbp >= float(b)
        if not (small or big):
            return None, colour
        return (d, line, "strong" if d == colour else "weak"), colour

    pos, out = 0, []
    entry_px = entry_i = line = None
    for i, (o, h, l, c) in enumerate(rows):
        sg, colour = signal(o, h, l, c)
        if sg is None or not (keep == "both" or sg[2] == keep):
            if pos != 0 and colour == -pos and ((pos == 1 and c <= line) or (pos == -1 and c >= line)):
                out.append(("buy" if pos == 1 else "sell", entry_px, c, entry_i, i, "invalidated"))
                pos = 0
            continue
        d, new_line, strength = sg
        if pos == d:
            line = new_line
            continue
        if pos == -d:
            out.append(("buy" if pos == 1 else "sell", entry_px, c, entry_i, i,
                        "reversed" if strength == "strong" else "opposite_weak"))
            pos = 0
            if strength != "strong":
                continue
        pos, entry_px, entry_i, line = d, c, i, new_line
    return out


def core(rows, s, b, keep):
    ev = [BarEvent(received_time_ns=(i + 1) * IV, start_time_ns=i * IV, open=o, high=h, low=l, close=c, volume=1.0)
          for i, (o, h, l, c) in enumerate(rows)]
    strat = K1WickStrategy(s, b, keep)
    res = CoreEngine(strat, {"bars": ev}, BarCloseMarketFill(), ZeroLatency(), DeclaredFeeCost({"taker": 0.0, "maker": 0.0}),
                     NullAccount(), time_span_ns=(ev[0].received_time_ns, ev[-1].received_time_ns)).run()
    tr = round_trips([{"order_id": f.client_order_id, "t_ns": f.venue_time_ns, "side": f.side, "px": f.price,
                       "qty": f.size, "fee": f.fee, "liquidity": f.liquidity} for f in res.fills], strat.exit_reasons)
    return [(t["side"], t["entry_px"], t["exit_px"], t["entry_t_ns"] // IV - 1, t["exit_t_ns"] // IV - 1, t["reason"])
            for t in tr]


@pytest.mark.parametrize("seed", [1, 2, 3])
@pytest.mark.parametrize("gate", gates(), ids=[gate_label(*g) for g in gates()])
@pytest.mark.parametrize("keep", ["both", "strong", "weak"])
def test_core_equals_second_reading(seed, gate, keep):
    rows = random_bars(seed)
    want = rule_text(rows, gate[0], gate[1], keep)
    got = core(rows, gate[0], gate[1], keep)
    assert got == want
    assert want, "the scene must produce trades, or it checks nothing"

"""Property tests for the bar reference on seeded random bars and signals.

Grid: every combination of the selectable modes (limit_cross x stop_trigger x
stop_fill x exits_from_entry_bar x mask_applies_to x entry_sides x tp_fee),
each on several seeds; bars, signals, max_hold and fees are drawn with the
standard-library random module. Properties:
  Q1 prefix (no look-ahead): running on bars[:k] gives the same equity for
     bars < k and the same closed trades that exit before k;
  Q2 a market entry fills at the open of the bar after its signal bar;
  Q3 a maker fill (limit entry, maker take-profit) is at exactly its level;
  Q4 stop priority: an exit bar whose range reaches both levels exits "stop";
  Q5 holding time never exceeds max_hold_bars; a max_hold exit is at the open
     of entry_bar + max_hold_bars;
  Q6 with close_at_end, final equity = initial + sum of trade pnl, exactly;
  Q7 determinism.
Not covered here: swap / funding on bars, position sizing other than fixed
qty, pyramiding (the reference has one position at a time).
"""
from __future__ import annotations

import itertools
import random
from fractions import Fraction as F

import pytest

from bot.bt.reference.bar_sim import Signal, make_bar, run_bars

MODE_GRID = list(itertools.product(("strict", "touch"), ("strict", "touch"),
                                   ("level", "worse_of_level_and_open"), (True, False),
                                   ("signal_bar", "fill_bar"), ("both", "long", "short"),
                                   ("maker", "taker")))
SEEDS = range(3)


def scene(seed: int, n: int = 30):
    rng = random.Random(seed)
    px, bs = 1000, []
    for i in range(n):
        o = max(5, px + rng.randint(-6, 6))
        c = max(5, o + rng.randint(-8, 8))
        bs.append(make_bar(i * 60_000_000_000, o, max(o, c) + rng.randint(0, 6), max(1, min(o, c) - rng.randint(0, 6)), c))
        px = c
    sigs = []
    for i in range(n):
        if rng.random() < 0.35:
            side = rng.choice(["long", "short"])
            lim = None
            if rng.random() < 0.3:
                lim = bs[i].close + (-1 if side == "long" else 1) * rng.randint(0, 5)
            sigs.append(Signal(side, limit=lim, sl_dist=rng.choice([None, rng.randint(1, 10)]),
                               tp_dist=rng.choice([None, rng.randint(1, 10)])))
        else:
            sigs.append(None)
    mask = [rng.random() < 0.85 for _ in range(n)]
    extra = dict(qty=rng.choice([1, "0.5"]), initial_cash=10000,
                 taker_rate=rng.choice(["0", "0.001"]), maker_rate=rng.choice(["-0.0002", "0.0002"]),
                 limit_valid_bars=rng.randint(1, 3), max_hold_bars=rng.choice([None, 1, 3, 5]))
    return bs, sigs, mask, extra


def kw(mode, mask, extra, close_at_end):
    lc, st, sf, efe, maf, es, tf = mode
    return dict(extra, limit_cross=lc, stop_trigger=st, stop_fill=sf, exits_from_entry_bar=efe,
                mask=mask, mask_applies_to=maf, entry_sides=es, tp_fee=tf, close_at_end=close_at_end)


@pytest.mark.parametrize("mode", MODE_GRID)
def test_q1_to_q7(mode):
    for seed in SEEDS:
        bs, sigs, mask, extra = scene(seed)
        full = run_bars(bs, sigs, **kw(mode, mask, extra, False))
        assert full.to_dict() == run_bars(bs, sigs, **kw(mode, mask, extra, False)).to_dict()  # Q7
        n = len(bs)
        for k in (5, 11, 17, 23):  # Q1
            pre = run_bars(bs[:k], sigs[:k], **kw(mode, mask[:k], extra, False))
            assert pre.equity == full.equity[:k]
            assert [t.to_dict() for t in pre.trades] == [t.to_dict() for t in full.trades if t.exit_bar < k]
        mh = extra["max_hold_bars"]
        for t in full.trades + ([full.open_trade] if full.open_trade else []):
            b = bs[t.entry_bar]
            if t.entry_liquidity == "taker":  # Q2
                assert t.entry_bar == t.signal_bar + 1 and t.entry_price == b.open
            else:  # Q3 (limit entry)
                assert t.entry_price == F(sigs[t.signal_bar].limit)
        for t in full.trades:
            x = bs[t.exit_bar]
            if t.reason == "take_profit":  # Q3 (tp level)
                assert t.exit_price == t.tp
            if t.sl is not None and t.tp is not None and t.reason in ("stop", "take_profit"):
                s = 1 if t.side == "long" else -1
                reach_sl = (x.low <= t.sl) if s == 1 else (x.high >= t.sl)
                reach_tp = (x.high >= t.tp) if s == 1 else (x.low <= t.tp)
                strict_sl = (x.low < t.sl) if s == 1 else (x.high > t.sl)
                strict_tp = (x.high > t.tp) if s == 1 else (x.low < t.tp)
                sl_hit = strict_sl or (mode[1] == "touch" and reach_sl)
                tp_hit = strict_tp or (mode[0] == "touch" and reach_tp)
                if sl_hit and tp_hit:  # Q4
                    assert t.reason == "stop"
            if mh is not None:  # Q5
                assert t.exit_bar - t.entry_bar <= mh
                if t.reason == "max_hold":
                    assert t.exit_bar == t.entry_bar + mh and t.exit_price == x.open
        closed = run_bars(bs, sigs, **kw(mode, mask, extra, True))  # Q6
        assert closed.open_trade is None
        assert closed.equity[-1] == F(extra["initial_cash"]) + sum((t.pnl for t in closed.trades), F(0))
        assert n == len(closed.equity)


def test_grid_is_not_vacuous():
    counts = {"stop": 0, "take_profit": 0, "max_hold": 0, "maker_entry": 0, "missed": 0}
    for mode in MODE_GRID[:16]:
        for seed in SEEDS:
            bs, sigs, mask, extra = scene(seed)
            r = run_bars(bs, sigs, **kw(mode, mask, extra, False))
            for t in r.trades:
                if t.reason in counts:
                    counts[t.reason] += 1
                counts["maker_entry"] += t.entry_liquidity == "maker"
            counts["missed"] += r.missed_fills
    assert all(v > 0 for v in counts.values()), counts

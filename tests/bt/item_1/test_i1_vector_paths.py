"""V7 adversary: the vector path against the event path (the core's
engine, one event at a time) and both against an exact oracle (fractions),
over seeded inputs chosen to break a careless shortcut:

  trades -- many trades in one bar (volume sums where the order of float
            additions matters: quantities like 0.1, 0.2, 0.7, 1e-8, 1e8),
            trades at the bar edge and 1 ns before it, equal timestamps,
            empty minutes, one trade, negative-free prices with many digits
  rules  -- n in {1, 2, 3, 5, 20, longer than the series}, unit in {1, 0.5,
            3}, closes as decimal texts (not binary fractions), long series
The two paths must agree BIT FOR BIT (`bitwise_equal`); the values must
equal the oracle within a relative 1e-9 (float rounding of the exact
value), positions exactly wherever |close - sma| is not a near tie.
Not drawn: unsorted inputs (refused by both paths -- asserted separately),
non-finite values (refused by the core's events).
"""
from __future__ import annotations

import random
import time
from fractions import Fraction

import pytest

from bot.bt.data import VectorError
from bot.bt.vector import (SmaCross, SmaLongFlat, bars_from_trades, bitwise_equal, run_event_bars, run_event_rule,
                           run_vector_rule)

NS = 10**9
T0 = 1767571200 * NS
IV = 60


def draw_trades(rng):
    trades, t = [], T0 + rng.randrange(0, 60) * NS
    for k in range(rng.randint(1, 300)):
        step = rng.choice([0, 0, 1, 7 * NS, 59 * NS + 999_999_999, 60 * NS, 180 * NS, rng.randrange(1, 90) * NS])
        t += step
        q = rng.choice([0.1, 0.2, 0.7, 1e-8, 1e8, 0.3, 1.0, 0.125])
        p = rng.choice([100.0, 100.1, 15_000_000.5, 99.99])
        trades.append({"t_ns": t, "px": p, "qty": q, "side": "buy", "id": str(k)})
    return trades


def oracle_bars(trades):
    out = {}
    for tr in trades:
        st = tr["t_ns"] // (IV * NS) * IV * NS
        b = out.setdefault(st, {"start_ns": st, "open": tr["px"], "high": tr["px"], "low": tr["px"], "vol": []})
        b["high"], b["low"], b["close"] = max(b["high"], tr["px"]), min(b["low"], tr["px"]), tr["px"]
        b["vol"].append(tr["qty"])
    res = []
    for st in sorted(out):
        b = out[st]
        v = 0.0
        for q in b["vol"]:
            v = v + q if v else q  # the definition: the float sum in delivered order
        res.append({"start_ns": st, "open": b["open"], "high": b["high"], "low": b["low"], "close": b["close"], "volume": v})
    return res


@pytest.mark.parametrize("seed", range(150))
def test_bars_event_vector_oracle(seed):
    rng = random.Random(seed)
    tr = draw_trades(rng)
    ev = run_event_bars(tr, IV)
    vc = bars_from_trades([x["t_ns"] for x in tr], [x["px"] for x in tr], [x["qty"] for x in tr], IV)
    assert bitwise_equal(ev, vc)
    assert bitwise_equal(ev, oracle_bars(tr))
    # and the exact sum is within float rounding of the paths' sum
    for b, o in zip(ev, oracle_bars(tr)):
        exact = sum(Fraction(q) for q in [x["qty"] for x in tr if x["t_ns"] // (IV * NS) * IV * NS == b["start_ns"]])
        assert abs(Fraction(b["volume"]) - exact) <= Fraction(1, 10**6) * max(1, exact)


def oracle_rule(closes, n, unit, init):
    fc = [Fraction(c) for c in closes]
    sma, pos, eq, e = [], [], [], Fraction(init)
    for t in range(len(fc)):
        m = sum(fc[t - n + 1:t + 1]) / n if t >= n - 1 else None
        if t:
            e += pos[-1] * (fc[t] - fc[t - 1])
        pos.append(Fraction(unit) if (m is not None and fc[t] > m) else Fraction(0))
        sma.append(m)
        eq.append(e)
    return sma, pos, eq


RULE_CASES = [(seed, n, unit) for seed in range(40) for n, unit in ((1, 1), (2, 0.5), (3, 1), (5, 3), (20, 1), (400, 1))]


@pytest.mark.parametrize("seed,n,unit", RULE_CASES)
def test_rule_event_vector_oracle(seed, n, unit):
    rng = random.Random(1000 + seed)
    closes = []
    c = rng.randrange(10_000, 20_000)
    for _ in range(rng.randint(1, 300)):
        c += rng.randrange(-50, 51)
        closes.append(float(f"{c / 100:.2f}"))
    bars = [{"start_ns": T0 + k * IV * NS, "open": x, "high": x, "low": x, "close": x, "volume": 1.0} for k, x in enumerate(closes)]
    rule = SmaLongFlat(n, unit, 1_000_000)
    ev = run_event_rule(bars, IV, rule)
    vc = run_vector_rule(bars, rule)
    assert bitwise_equal(ev, vc)
    sma, pos, eq = oracle_rule(closes, n, unit, 1_000_000)
    for t in range(len(closes)):
        if sma[t] is None:
            assert ev["sma"][t] is None and ev["position"][t] == 0.0
            continue
        assert abs(Fraction(ev["sma"][t]) - sma[t]) <= Fraction(1, 10**9) * abs(sma[t])
        if abs(Fraction(closes[t]) - sma[t]) > Fraction(1, 10**6):
            assert Fraction(ev["position"][t]) == pos[t]
    # equity: exact whenever every earlier position agreed with the oracle
    agree = all(Fraction(ev["position"][t]) == pos[t] for t in range(len(closes)))
    if agree:
        for t in range(len(closes)):
            assert abs(Fraction(ev["equity"][t]) - eq[t]) <= Fraction(1, 10**9) * max(1, abs(eq[t]))


def test_the_vector_path_is_faster_on_a_long_series():
    rng = random.Random(7)
    closes, c = [], 15_000_000
    for _ in range(20_000):
        c += rng.randrange(-500, 501)
        closes.append(float(c))
    bars = [{"start_ns": T0 + k * IV * NS, "open": x, "high": x, "low": x, "close": x, "volume": 1.0} for k, x in enumerate(closes)]
    rule = SmaLongFlat(3, 1, 100_000_000)
    t0 = time.perf_counter()
    ev = run_event_rule(bars, IV, rule)
    t1 = time.perf_counter()
    vc = run_vector_rule(bars, rule)
    t2 = time.perf_counter()
    assert bitwise_equal(ev, vc)
    assert (t2 - t1) < (t1 - t0), (t2 - t1, t1 - t0)


def test_unsorted_or_bad_inputs_are_refused_by_both_paths():
    tr = [{"t_ns": T0 + NS, "px": 1.0, "qty": 1.0}, {"t_ns": T0, "px": 1.0, "qty": 1.0}]
    with pytest.raises(VectorError):
        bars_from_trades([x["t_ns"] for x in tr], [1.0, 1.0], [1.0, 1.0], IV)
    with pytest.raises(VectorError):
        run_event_bars(tr, IV)
    with pytest.raises(VectorError):
        bars_from_trades([T0], [1.0], [1.0], 0)
    with pytest.raises(VectorError):
        bars_from_trades([float(T0)], [1.0], [1.0], IV)
    bars = [{"start_ns": T0 + NS * 60, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0},
            {"start_ns": T0, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0}]
    with pytest.raises(VectorError):
        run_event_rule(bars, IV, SmaLongFlat(2))
    for bad in (0, -1, 1.5, True):
        with pytest.raises(VectorError):
            SmaLongFlat(bad)
    with pytest.raises(VectorError):
        SmaLongFlat(2, float("nan"))


def test_empty_inputs():
    assert bars_from_trades([], [], [], IV) == [] and run_event_bars([], IV) == []
    r = SmaLongFlat(3)
    assert run_vector_rule([], r) == {"sma": [], "position": [], "equity": []} == run_event_rule([], IV, r)


CROSS_CASES = [(seed, f, sl) for seed in range(40) for f, sl in ((1, 2), (2, 5), (3, 20), (5, 400))]


def oracle_mean(fc, n, t):
    return sum(fc[t - n + 1:t + 1]) / n if t >= n - 1 else None


@pytest.mark.parametrize("seed,fast,slow", CROSS_CASES)
def test_cross_rule_event_vector_oracle(seed, fast, slow):
    rng = random.Random(5000 + seed)
    closes, c = [], rng.randrange(10_000, 20_000)
    for _ in range(rng.randint(1, 300)):
        c += rng.randrange(-50, 51)
        closes.append(float(f"{c / 100:.2f}"))
    bars = [{"start_ns": T0 + k * IV * NS, "open": x, "high": x, "low": x, "close": x, "volume": 1.0} for k, x in enumerate(closes)]
    rule = SmaCross(fast, slow, 2, 0)
    ev = run_event_rule(bars, IV, rule)
    vc = run_vector_rule(bars, rule)
    assert bitwise_equal(ev, vc)
    fc = [Fraction(x) for x in closes]
    for t in range(len(closes)):
        f, sl = oracle_mean(fc, fast, t), oracle_mean(fc, slow, t)
        for got, want in ((ev["fast"][t], f), (ev["slow"][t], sl)):
            assert (got is None) == (want is None)
            if want is not None:
                assert abs(Fraction(got) - want) <= Fraction(1, 10**9) * abs(want)
        if f is not None and sl is not None and abs(f - sl) > Fraction(1, 10**6):
            assert ev["position"][t] == (2.0 if f > sl else 0.0)


def test_rule_declarations_are_strict():
    from bot.bt.vector import rule_from_mapping
    for bad in ({"type": "sma_cross", "fast": 5, "slow": 5}, {"type": "sma_cross", "fast": 5},
                {"type": "sma_long_flat", "n": 3, "extra": 1}, {"type": "nope"}, None):
        with pytest.raises(VectorError):
            rule_from_mapping(bad)

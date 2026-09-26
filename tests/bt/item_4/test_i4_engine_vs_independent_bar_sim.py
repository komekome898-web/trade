"""The new engine's bar model (spec) against the INDEPENDENT reference, on every rule of the scene set
(finishing delegation §1 condition 2).

`bot.bt.reference.bar_sim.run_bars(bars, signals, options)` was rewritten by the reference role from the rule text of
tests/bt/battery/item_4/DEFINITIONS.md 「足の模型の仕様」 only, without opening the core, the new engine or
bar_rules.py (src/bot/bt/reference/SPEC.md §10). Its entry is SPEC.md §7; the two points the rule text leaves open
get the lead's values: undecided = {"wick_short_history": "use_available", "same_side_exit_signal": "keep"}.
A difference is a defect of the new engine (the reference is never fitted to the engine).

Grid (the rules' input space, drawn with seeded random numbers -- not from the engine's branches): per case every
option of the bar model is drawn: execution {taker, maker} with lifetime {1, 2, 3, 5}; allow_short; costs {zero,
taker/maker fees, spread + slippage, all four, negative fees (R-V3)}; carry {0, positive, negative daily rate};
stop {none, fixed %, structural wick N in {1, 2, 3}}; take-profit {none, %}; maker take-profit {none, %};
max_hold_bars {None, 1, 2, 3}; entry mask {None, random}; entry_sides {both, long, short}; bar seconds {60, 3600};
bars: a random walk on a 0.5 grid (ties with the levels happen) with opens gapping beyond levels; signals: random
BUY / SELL / CLOSE / nothing on each bar. SEEDS x CASES_PER_SEED cases, plus every prefix of the first cases
(no look-ahead). Compared: fills (bar, side exact; price, size), round-trip PnL, equity per bar, missed fills,
with the scene set's tolerance |a - b| <= 1e-9 x max(1, |a|, |b|).
Rules covered by the draws: R-T1..T4, R-C1, R-A1..A4, R-M1..M7, R-P1..P4, R-X1..X3, R-W1..W6, R-H1..H3,
R-E1..E5, R-S1, R-O1, R-V2..V4 (refusals: test_both_refuse_non_positive). Not in the grid: R-V1 (invalid bars:
the reference refuses; the engine's core refuses too -- test_both_refuse_an_invalid_bar), metrics (the reference
has none, SPEC.md §8-4).
"""
from __future__ import annotations

import random

import pytest

from bot.bt.compat import bar_events, options_from_mapping, run_bars
from bot.bt.reference.bar_sim import run_bars as ref_run_bars

NS = 1_000_000_000
T0 = 1767571200 * NS
UNDECIDED = {"wick_short_history": "use_available", "same_side_exit_signal": "keep"}
SEEDS = range(12)
CASES_PER_SEED = 60
N_BARS = 24


def _bars(rng: random.Random, n: int) -> list:
    out, px = [], 100.0
    for _ in range(n):
        o = px + rng.choice((0.0, 0.0, 0.5, -0.5, 2.0, -2.0, 3.5, -3.5))
        c = o + rng.choice((-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0))
        h = max(o, c) + rng.choice((0.0, 0.5, 1.0, 2.5))
        lo = min(o, c) - rng.choice((0.0, 0.5, 1.0, 2.5))
        out.append((o, h, max(lo, 1.0), c))
        px = c
    return out


def _case(seed: int, k: int):
    rng = random.Random(seed * 1000 + k)
    n = N_BARS
    bars = _bars(rng, n)
    sig = {i: rng.choice(("BUY", "SELL", "CLOSE", None, None, None)) for i in range(n)}
    sig = {i: s for i, s in sig.items() if s is not None}
    execution = rng.choice(("taker", "maker"))
    costs = rng.choice(({"taker_fee_pct": 0.0, "maker_fee_pct": 0.0, "slippage_pct": 0.0, "spread_pct": 0.0},
                        {"taker_fee_pct": 0.1, "maker_fee_pct": 0.02, "slippage_pct": 0.0, "spread_pct": 0.0},
                        {"taker_fee_pct": 0.0, "maker_fee_pct": 0.0, "slippage_pct": 0.03, "spread_pct": 0.04},
                        {"taker_fee_pct": 0.1, "maker_fee_pct": 0.02, "slippage_pct": 0.03, "spread_pct": 0.04},
                        {"taker_fee_pct": -0.01, "maker_fee_pct": -0.02, "slippage_pct": 0.0, "spread_pct": 0.0}))
    stop = rng.choice(("none", "fixed", "wick"))
    exit_exec = rng.choice(("signal", "signal", "maker_tp"))
    cfg = {"costs": costs, "execution": execution,
           "maker_timeout_bars": rng.choice((1, 2, 3, 5)), "allow_short": rng.random() < 0.6,
           "swap_daily_pct": rng.choice((0.0, 0.0, 0.05, -0.03)),
           "stop_loss_pct": rng.choice((1.0, 1.5, 2.0)) if stop == "fixed" else None,
           "take_profit_pct": rng.choice((None, 1.5, 2.5)),
           "max_hold_bars": rng.choice((None, None, 1, 2, 3)),
           "exit_execution": exit_exec, "maker_tp_pct": rng.choice((1.0, 2.0)) if exit_exec == "maker_tp" else None,
           "entry_mask": [rng.random() < 0.7 for _ in range(n)] if rng.random() < 0.4 else None,
           "entry_sides": rng.choice(("both", "both", "long", "short")),
           "stop_mode": "wick_invalidation" if stop == "wick" else "fixed",
           "stop_window_bars": rng.choice((1, 2, 3)) if stop == "wick" else None}
    bar_seconds = rng.choice((60, 3600))
    return bars, sig, cfg, bar_seconds


def run_engine(bars, sig, cfg, bar_seconds):
    m = dict(cfg, initial_equity=10000.0, order_notional=3000.0, bar_seconds=float(bar_seconds))
    rows = [{"open": b[0], "high": b[1], "low": b[2], "close": b[3], "volume": 1.0} for b in bars]
    ev = bar_events(rows, [T0 + i * bar_seconds * NS for i in range(len(rows))], bar_seconds * NS)
    r = run_bars(ev, lambda k: sig.get(k - 1), options_from_mapping(m), "spec", start=0)
    return {"fills": [{"bar": f["bar"], "side": f["side"], "price": f["price"], "size": f["size"]} for f in r.fills],
            "pnls": list(r.trade_pnls), "equity": list(r.equity), "missed_fills": r.missed_fills}


def run_ref(bars, sig, cfg, bar_seconds):
    o = dict(cfg, capital=10000, order_amount=3000, bar_seconds=bar_seconds, undecided=UNDECIDED)
    return ref_run_bars(bars, sig, o).to_floats()


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))


def diff(e: dict, r: dict) -> list:
    out = []
    if [(f["bar"], f["side"]) for f in e["fills"]] != [(f["bar"], f["side"]) for f in r["fills"]]:
        return [("fills", [(f["bar"], f["side"], f["price"]) for f in e["fills"]],
                 [(f["bar"], f["side"], f["price"]) for f in r["fills"]])]
    for fe, fr in zip(e["fills"], r["fills"]):
        if not (_close(fe["price"], fr["price"]) and _close(fe["size"], fr["size"])):
            out.append(("fill", fe, fr))
    if len(e["pnls"]) != len(r["pnls"]) or not all(_close(a, b) for a, b in zip(e["pnls"], r["pnls"])):
        out.append(("pnls", e["pnls"], r["pnls"]))
    if len(e["equity"]) != len(r["equity"]) or not all(_close(a, b) for a, b in zip(e["equity"], r["equity"])):
        out.append(("equity", e["equity"], r["equity"]))
    if e["missed_fills"] != r["missed_fills"]:
        out.append(("missed_fills", e["missed_fills"], r["missed_fills"]))
    return out


@pytest.mark.parametrize("seed", SEEDS)
def test_engine_equals_the_independent_reference_on_every_case(seed):
    bad = []
    for k in range(CASES_PER_SEED):
        bars, sig, cfg, bs = _case(seed, k)
        d = diff(run_engine(bars, sig, cfg, bs), run_ref(bars, sig, cfg, bs))
        if d:
            bad.append((k, cfg, d[0]))
    assert not bad, f"{len(bad)} of {CASES_PER_SEED} cases differ; first: {bad[0]}"


@pytest.mark.parametrize("seed", range(3))
def test_every_prefix_equals_the_reference(seed):
    bad = []
    for k in range(4):
        bars, sig, cfg, bs = _case(seed, k)
        for cut in range(1, len(bars) + 1):
            c2 = dict(cfg, entry_mask=cfg["entry_mask"][:cut] if cfg["entry_mask"] is not None else None)
            s2 = {i: s for i, s in sig.items() if i < cut}
            d = diff(run_engine(bars[:cut], s2, c2, bs), run_ref(bars[:cut], s2, c2, bs))
            if d:
                bad.append((k, cut, d[0]))
    assert not bad, bad[:2]


def test_the_grid_reaches_every_exit_reason():
    """The draws are not vacuous: across the grid the engine meets every exit path."""
    from bot.bt.compat import bar_events as be  # noqa: F401
    reasons = set()
    for seed in SEEDS:
        for k in range(CASES_PER_SEED):
            bars, sig, cfg, bs = _case(seed, k)
            m = dict(cfg, initial_equity=10000.0, order_notional=3000.0, bar_seconds=float(bs))
            rows = [{"open": b[0], "high": b[1], "low": b[2], "close": b[3], "volume": 1.0} for b in bars]
            ev = bar_events(rows, [T0 + i * bs * NS for i in range(len(rows))], bs * NS)
            r = run_bars(ev, lambda j: sig.get(j - 1), options_from_mapping(m), "spec", start=0)
            reasons |= {f["reason"] for f in r.fills}
            reasons |= {"missed"} if r.missed_fills else set()
    assert {"open", "signal", "stop_loss", "take_profit", "maker_tp", "wick_stop", "time_exit", "missed"} <= reasons


@pytest.mark.parametrize("key,value", [("stop_loss_pct", 0.0), ("take_profit_pct", 0.0), ("max_hold_bars", 0),
                                       ("maker_timeout_bars", 0)])
def test_both_refuse_non_positive(key, value):
    bars, sig, cfg, bs = _case(0, 0)
    cfg = dict(cfg, **{key: value}, execution="maker" if key == "maker_timeout_bars" else cfg["execution"])
    if key == "stop_loss_pct":
        cfg.update(stop_mode="fixed", stop_window_bars=None)
    with pytest.raises(Exception):
        run_engine(bars, sig, cfg, bs)
    with pytest.raises(Exception):
        run_ref(bars, sig, cfg, bs)


def test_both_refuse_an_invalid_bar():
    bars, sig, cfg, bs = _case(0, 1)
    bars = list(bars)
    o, h, lo, c = bars[3]
    bars[3] = (o, min(o, c) - 0.5, lo - 1.0, c)  # high below the open / close (R-V1)
    with pytest.raises(Exception):
        run_engine(bars, sig, cfg, bs)
    with pytest.raises(Exception):
        run_ref(bars, sig, cfg, bs)

"""The bar model runs on the core (item 4: 「新エンジンの上に新しく書き」), and what that
gives: every fill is a core fill priced by the run's cost model; the decision
at bar i sees bars 0..i only; each signal order ends with the reason it ended.

Causality is tested as a property on the option grid (golden/compat_golden_scenes.py): a
run on the first k bars gives exactly the first k equity values and the
fills of those bars of the full run -- a later bar can change nothing before
it -- for k at 5 points of every 9th cell (under "legacy" and "spec").
"""
from __future__ import annotations

import pytest

import compat_golden_scenes as G
from bot.bt.compat import BarModelError, bar_events, options_from_mapping, run_bars
from bot.bt.core import FORCED_ID_PREFIX
from test_i4_spec_vs_reference_grid import to_input


def _run(sc, rules, k=None, decide_log=None):
    inp = to_input(sc)
    cfg = dict(inp["config"], bar_seconds=float(inp["bar_seconds"]))
    bars = inp["bars"] if k is None else inp["bars"][:k]
    if k is not None and cfg["entry_mask"] is not None:
        cfg["entry_mask"] = cfg["entry_mask"][:k]
    ev = bar_events(bars, [b["t_ns"] for b in bars], inp["bar_seconds"] * 10**9)
    sig = {s["bar"]: s["signal"] for s in inp["signals"]}

    def decide(n):
        if decide_log is not None:
            decide_log.append(n)
        return sig.get(n - 1)
    return run_bars(ev, decide, options_from_mapping(cfg), rules)


@pytest.mark.parametrize("rules", ["legacy", "spec"])
def test_a_later_bar_changes_nothing_before_it(rules):
    for sc in G.scenes()[::9]:
        full = _run(sc, rules)
        for k in (1, 7, 13, 26, 39):
            part = _run(sc, rules, k)
            assert part.equity == full.equity[:k], (sc["cell"], k)
            assert part.fills == [f for f in full.fills if f["bar"] < k], (sc["cell"], k)


def test_the_decision_at_bar_i_is_asked_with_exactly_i_plus_1_bars_delivered():
    sc = G.scenes()[3]
    log = []
    res = _run(sc, "spec", decide_log=log)
    assert log == list(range(1, 41))
    assert res.core.source_events == 40


@pytest.mark.parametrize("rules", ["legacy", "spec"])
def test_every_fill_is_a_core_fill_with_the_cost_models_fee(rules):
    for sc in G.scenes()[::50]:
        res = _run(sc, rules)
        core = res.core.fills
        assert len(core) == len(res.fills)
        opts = sc["options"]["costs"]
        for n, f in zip(core, res.fills):
            assert n.client_order_id.startswith(FORCED_ID_PREFIX)
            assert (n.price, n.size, n.fee) == (f["price"], f["size"], f["fee"])
            pct = opts["taker_fee_pct"] if n.liquidity == "taker" else opts["maker_fee_pct"]
            assert n.fee == n.size * n.price * pct / 100


REASONS = {"executed", "no_action", "entry_filtered", "dropped_by_exit", "timeout", "replaced", "not_actionable",
           "kept_older"}  # kept_older: spec, a maker signal the same way as the pending limit (i4-r2-08)


@pytest.mark.parametrize("rules", ["legacy", "spec"])
def test_every_signal_order_ends_with_its_reason(rules):
    """A signal order is an instruction: it ends Canceled / Rejected with the reason it ended; the only one
    that may still be open is the one pending when the bars end."""
    seen = set()
    for sc in G.scenes()[::11]:
        res = _run(sc, rules)
        sig = {c: v for c, v in res.core.orders.items() if c.startswith("sig")}
        still_open = [c for c, v in sig.items() if v.is_open]
        assert len(still_open) <= 1, (sc["cell"], still_open)
        for c, v in sig.items():
            if not v.is_open:
                assert v.reason in REASONS, (sc["cell"], c, v.reason)
                assert v.filled_size == 0.0
                seen.add(v.reason)
    assert {"executed", "no_action", "dropped_by_exit"} <= seen


def test_the_options_have_no_defaults():
    sc = G.scenes()[0]
    cfg = dict(to_input(sc)["config"], bar_seconds=60.0)
    for k in list(cfg):
        bad = dict(cfg)
        bad.pop(k)
        with pytest.raises(BarModelError, match="missing"):
            options_from_mapping(bad)


def test_a_bar_the_core_refuses_is_refused():
    bars = [{"t_ns": 0, "open": 1.0, "high": 0.5, "low": 1.0, "close": 1.0}]
    with pytest.raises(BarModelError):
        bar_events(bars, [60_000_000_000], 60_000_000_000)
    ok = [{"t_ns": 0, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0}] * 2
    with pytest.raises(BarModelError, match="overlap"):
        bar_events(ok, [60_000_000_000, 90_000_000_000], 60_000_000_000)

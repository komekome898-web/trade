"""The integrated run's `module` strategy kind (research unit U1, docs/PHASE2/U1/ENV_DEFECTS.md D-1): a
strategy of the repository (`factory(params, price_type)` -> bot.bt.core.Strategy) runs through the same
sockets as the built-in kinds, names its closing orders' reasons, and its source and params enter the
identity. Synthetic data only (a seeded random-walk bar generator): no market file is read here."""
from __future__ import annotations

import os
import tempfile

import pytest

import i4w_decl as D
from bot.bt.pipeline import PipelineError, plan_pipeline, run_pipeline
from bot.strategy import u1_range_center as U1

NS = 1_000_000_000
T0 = 1_700_000_000 * NS
PARAMS = {"range_bars": 5, "vola_bars": 3, "k_entry": 1.0, "k_exit": 0.0, "width_min_bp": 0.0, "vr_max": 1e9,
          "big_move_k": 1e9, "resume_k": 0.0, "hold_bars": 10, "reverse": True, "qty": 1.0}
FILL_BARS = {"optimistic": {"tier": 2}, "pessimistic": {"tier": 2}}


def _root_with_prereg() -> str:
    root = tempfile.mkdtemp(prefix="i4_module_")
    with open(os.path.join(root, "prereg.md"), "wb") as fh:
        fh.write(b"# prereg (test)\n")
    return root


def _gen(n: int = 400, seed: int = 7) -> list:
    return [{"name": "bars", "generator": {"name": "random_walk", "seed": seed, "params": {
        "kind": "bar", "start_ns": T0, "step_ns": 60 * NS, "n": n, "price0": 100.0, "step_pct": 0.5, "qty": 1.0}}}]


def _strategy(**over) -> dict:
    return {"kind": "module", "module": "bot.strategy.u1_range_center", "factory": "make", "params": {**PARAMS, **over}}


def _plan(root: str, strategy: dict, purpose: str = "研究"):
    kw = D.kw()
    kw["fill"] = FILL_BARS
    return plan_pipeline(root=root, datasets=_gen(), instruments=[D.instrument("x", "bars", "bar")], strategy=strategy,
                         purpose=purpose, prereg="prereg.md", **kw)


def test_module_strategy_runs_and_names_its_exits():
    root = _root_with_prereg()
    res = run_pipeline(_plan(root, _strategy()), runs_dir=tempfile.mkdtemp(prefix="i4_module_runs_"))
    assert res.repro["identical"] is True
    st = res.record["config"]["strategy"]
    assert st["kind"] == "module" and st["params"] == PARAMS and len(st["module_source_sha256"]) == 64
    reasons = {U1.REASON_TP, U1.REASON_TIME, U1.REASON_BREAK}
    for side, per in res.range.items():
        r = per["x"]
        assert r.trades, (side, "the random walk gave no round trip")
        assert {t["reason"] for t in r.trades} <= reasons, (side, {t["reason"] for t in r.trades})
        assert all(o["type"] in ("limit", "market") for o in r.orders), side
        assert any(o["type"] == "limit" for o in r.orders), (side, "no limit order was sent")


def test_module_params_and_source_change_the_run_id():
    root = _root_with_prereg()
    a = _plan(root, _strategy())
    b = _plan(root, _strategy(k_entry=2.0))
    assert a.run_id != b.run_id


def test_module_refuses_a_missing_param_and_an_unknown_factory():
    root = _root_with_prereg()
    bad = _strategy()
    del bad["params"]["qty"]
    with pytest.raises(PipelineError, match="qty"):
        _plan(root, bad)
    with pytest.raises(PipelineError, match="factory"):
        _plan(root, {**_strategy(), "factory": "no_such_factory"})


def test_module_needs_a_prereg_under_the_research_purpose():
    root = tempfile.mkdtemp(prefix="i4_module_noprereg_")
    kw = D.kw()
    kw["fill"] = FILL_BARS
    with pytest.raises(PipelineError, match="pre-registration"):
        plan_pipeline(root=root, datasets=_gen(), instruments=[D.instrument("x", "bars", "bar")], strategy=_strategy(),
                      purpose="研究", **kw)


def test_strategy_refuses_a_trade_priced_instrument():
    from bot.bt.core import TradeEvent
    with pytest.raises(U1.ParamError, match="bars only"):
        U1.make(PARAMS, TradeEvent)

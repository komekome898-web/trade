"""The integrated run (bot.bt.pipeline): declared data of every asset -> the core per instrument with the item-2
execution models in its sockets (SimVenue, LatencyModel, ScheduleCostModel, MarginAccount; finishing stage
i4-r2-06) -> run record, exports, the dashboard's run view, in one call executed twice, both sides of the fill range.

The refusal grid is the declaration's own space: purpose {動作確認, 研究, None, "other"} x source {file (real market
data by the rule), seeded generator (synthetic)} x strategy {schedule, seeded_random, price_rule} x pre-registration
{none, file} = 48 cells; the expected accept / refuse of each cell is written from the rule text (委任文 §4 +
finishing delegation i4-r2-03 / i4-r2-05) in `expected_accept`, not from the code. The pre-registration as a bare
hash, the re-encodings of market files and the time-exit / maker grids are their own files (test_i4_r3_*).
Not in the grid: several sources mixed in one run (any file dataset makes the run real --
test_one_file_dataset_makes_the_run_real).
"""
from __future__ import annotations

import copy
import hashlib
import itertools
import os
import tempfile

import pytest

import i4_scenes as S
import i4w_decl as D
from bot.bt.pipeline import PipelineError, plan_pipeline, run_pipeline
from bot.bt.report.exports import read_export
from bot.monitoring.backtest_view import TABS, WARNING, run_view

T0 = S.T0
NS = S.NS
KIND = {"bf_trades": "trade", "binance": "trade", "fx_ticks": "quote", "jpx_1m": "bar", "fx_1m": "bar"}
INSTRUMENTS = [D.instrument(i["name"], i["price"], KIND[i["price"]], i["with"]) for i in S.INSTRUMENTS]
PREREG = "prereg.md"
GEN = {"name": "random_walk", "seed": 5, "params": {"kind": "trade", "start_ns": T0 - 60 * NS, "step_ns": 10 * NS,
                                                    "n": 800, "price0": 100.0, "step_pct": 0.1, "qty": 1.0}}


def _root():
    files, ds = S._pipeline_files()
    root = tempfile.mkdtemp(prefix="i4w_pipe_")
    for f in files:
        p = os.path.join(root, f["path"])
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as fh:
            fh.write(S.file_bytes(f))
    with open(os.path.join(root, PREREG), "wb") as fh:
        fh.write(b"# prereg\n")
    return root, files, ds


def _args(root, ds, **over):
    a = dict(root=root, datasets=copy.deepcopy(ds), instruments=copy.deepcopy(INSTRUMENTS),
             strategy={"kind": "schedule", "orders": copy.deepcopy(S.SCHEDULE)}, purpose="動作確認", **D.kw())
    a.update(over)
    return a


def _gen_args(root, **over):
    a = dict(root=root, datasets=[{"name": "g", "generator": GEN}], instruments=[D.instrument("g", "g", "trade")],
             strategy={"kind": "schedule", "orders": copy.deepcopy(S.SCHEDULE)}, purpose="動作確認", **D.kw())
    a.update(over)
    return a


STRATS = {"schedule": {"kind": "schedule", "orders": S.SCHEDULE},
          "seeded_random": {"kind": "seeded_random", "seed": 7, "times": [T0, T0 + 300 * NS], "qty": 1.0},
          "price_rule": {"kind": "price_rule", "buy_below": 1e9, "sell_above": 1.0, "qty": 1.0}}


def expected_accept(purpose, source, strat, prereg) -> bool:
    """委任文 §4 + i4-r2-03 / 05, read as rules: a purpose is required and is 動作確認 or 研究; 研究 needs the
    pre-registration FILE; a file dataset is real, and on real data a 動作確認 run takes only time-only procedures
    or seeded random."""
    if purpose not in ("動作確認", "研究"):
        return False
    if purpose == "研究" and prereg is None:
        return False
    if source == "file" and purpose == "動作確認" and strat == "price_rule":
        return False
    return True


GRID = list(itertools.product(["動作確認", "研究", None, "other"], ["file", "generator"], list(STRATS), [None, PREREG]))


def test_refusal_grid_matches_the_rule_text():
    root, _, ds = _root()
    assert len(GRID) == 48
    for purpose, source, strat, prereg in GRID:
        a = _args(root, ds) if source == "file" else _gen_args(root)
        a.update(purpose=purpose, strategy=STRATS[strat], prereg=prereg)
        try:
            plan_pipeline(**a)
            got = True
        except PipelineError:
            got = False
        assert got == expected_accept(purpose, source, strat, prereg), (purpose, source, strat, prereg)


def test_one_file_dataset_makes_the_run_real():
    root, _, ds = _root()
    jpx = [d for d in ds if d["name"] == "jpx_1m"]
    a = _args(root, jpx + [{"name": "g", "generator": GEN}], strategy=STRATS["price_rule"],
              instruments=[D.instrument("g", "g", "trade"), D.instrument("jpx", "jpx_1m", "bar")])
    with pytest.raises(PipelineError, match="time-only"):
        plan_pipeline(**a)


def test_origin_has_no_default_and_a_file_cannot_be_synthetic():
    root, _, ds = _root()
    d2 = copy.deepcopy(ds)
    d2[0].pop("origin")
    with pytest.raises(PipelineError, match="origin"):
        plan_pipeline(**_args(root, d2))
    d3 = [dict(d, origin="synthetic") for d in ds]
    with pytest.raises(PipelineError, match="generator"):
        plan_pipeline(**_args(root, d3))


def test_prereg_file_gives_its_sha256():
    root, _, ds = _root()
    plan = plan_pipeline(**_args(root, ds, purpose="研究", prereg=PREREG))
    assert plan.identity["prereg_sha256"] == hashlib.sha256(b"# prereg\n").hexdigest()


def test_one_run_reaches_record_exports_and_dashboard_and_is_kept_once():
    root, files, ds = _root()
    runs = tempfile.mkdtemp(prefix="i4w_runs_")
    plan = plan_pipeline(**_args(root, ds))
    res = run_pipeline(plan, runs_dir=runs)
    again = run_pipeline(plan_pipeline(**_args(root, ds)), runs_dir=runs)
    assert again.run_id == res.run_id and again.repro == res.repro
    assert res.repro["identical"] is True and res.repro["runs"] == 2
    assert res.record["data_sha256"] == {f["path"]: hashlib.sha256(S.file_bytes(f)).hexdigest() for f in files}
    assert set(res.exports) == {"metrics.json", "trades.json", "fills.json", "orders.json", "data_quality.json"}
    assert set(res.exports.values()) == {"動作確認"}
    m = read_export(os.path.join(res.run_dir, "metrics.json"))
    # the counts follow the item-2 venue model (book walk / last trade / next bar open), consistent with the fills
    assert {k: v["num_trades"] for k, v in m["data"]["by_instrument"].items()} == \
        {n: len(r.trades) for n, r in res.instruments.items()}
    assert all(len(r.fills) >= 1 for r in res.instruments.values())
    view = run_view(runs, res.run_id)
    assert [t["label"] for t in view["tabs"]] == list(TABS)
    assert all(WARNING in t["text"] for t in view["tabs"])
    assert res.events_read == {d["name"]: len(S.file_bytes(f).decode().strip().splitlines()) - (1 if d["spec"]["header"] else 0)
                               for d, f in zip(ds, files)}


def test_the_sockets_are_the_item_2_models_and_both_sides_are_recorded():
    """i4-r2-06: the core's four sockets hold SimVenue / LatencyModel / ScheduleCostModel / MarginAccount (the core
    records each socket's class), both sides of the fill range run and reach the record and the exports, the latency
    distributions and their draws and the accounts' final state are recorded; the pipeline's own models are gone."""
    import bot.bt.pipeline as P
    for gone in ("FirstObservedFill", "_Latency", "_Fee", "NullAccount", "market_evidence"):
        assert not hasattr(P, gone), gone
    root, _, ds = _root()
    res = run_pipeline(plan_pipeline(**_args(root, ds)), runs_dir=tempfile.mkdtemp())
    models = res.record["components"]["models"]
    assert set(models) == {"optimistic", "pessimistic"}
    for side in models:
        for name, m in models[side].items():
            assert m["fill_model"].endswith("SimVenue") and m["latency_model"].endswith("LatencyModel"), (side, name, m)
            assert m["cost_model"].endswith("ScheduleCostModel") and m["account"].endswith("MarginAccount"), m
    assert res.record["components"]["fill_range"] == D.FILL
    drawn = res.record["components"]["latency"]["drawn"]
    assert all(drawn[s][n]["draws"]["order"] == 4 for s in drawn for n in drawn[s])
    acc = res.record["components"]["account"]["pessimistic"]["bf"]
    signed = sum(f["qty"] if f["side"] == "buy" else -f["qty"] for f in res.range["pessimistic"]["bf"].fills)
    assert acc["currency"] == "JPY" and acc["position"] == pytest.approx(signed) and acc["leverage"] == 1.0
    m = read_export(os.path.join(res.run_dir, "metrics.json"))["data"]
    assert set(m["range"]) == {"optimistic", "pessimistic"}
    fills = read_export(os.path.join(res.run_dir, "fills.json"))["data"]
    assert {f["range"] for f in fills} == {"optimistic", "pessimistic"}
    assert set(res.range) == {"optimistic", "pessimistic"}


def test_a_research_run_on_generated_data_has_no_smoke_banner_and_records_the_generator():
    root, _, _ = _root()
    runs = tempfile.mkdtemp(prefix="i4w_runs_")
    res = run_pipeline(plan_pipeline(**_gen_args(root, purpose="研究", prereg=PREREG, strategy=STRATS["price_rule"])),
                       runs_dir=runs)
    view = run_view(runs, res.run_id)
    assert view["warning"] is None and not any(WARNING in t["text"] for t in view["tabs"])
    g = res.record["generators"]["g"]
    assert g["name"] == "random_walk" and g["seed"] == 5 and g["version"]
    assert res.record["data"][0]["origin"] == "synthetic"


def test_seeded_random_is_reproducible_and_the_seed_matters():
    root, _, ds = _root()
    sides = {}
    for seed in range(8):
        st = {"kind": "seeded_random", "seed": seed, "times": [T0, T0 + 300 * NS, T0 + 3600 * NS, T0 + 3900 * NS],
              "qty": 1.0}
        a = run_pipeline(plan_pipeline(**_args(root, ds, strategy=st)), runs_dir=tempfile.mkdtemp())
        b = run_pipeline(plan_pipeline(**_args(root, ds, strategy=st)), runs_dir=tempfile.mkdtemp())
        sa = [f["side"] for f in a.instruments["bf"].fills]
        assert sa == [f["side"] for f in b.instruments["bf"].fills] and a.run_id == b.run_id
        sides[seed] = tuple(sa)
    assert len(set(sides.values())) > 1


def test_order_latency_moves_the_fill_and_a_seeded_distribution_repeats():
    root, _, ds = _root()
    base = run_pipeline(plan_pipeline(**_args(root, ds)), runs_dir=tempfile.mkdtemp())
    lat = dict(D.LATENCY0, order={"kind": "constant", "ns": 250_000_000})
    slow = run_pipeline(plan_pipeline(**_args(root, ds, latency=lat)), runs_dir=tempfile.mkdtemp())
    assert slow.instruments["fx_tick"].fills[0]["t_ns"] - base.instruments["fx_tick"].fills[0]["t_ns"] >= 250_000_000
    uni = dict(D.LATENCY0, order={"kind": "seeded_uniform", "low_ns": 0, "high_ns": 10**9, "seed": 4})
    a = run_pipeline(plan_pipeline(**_args(root, ds, latency=uni)), runs_dir=tempfile.mkdtemp())
    b = run_pipeline(plan_pipeline(**_args(root, ds, latency=uni)), runs_dir=tempfile.mkdtemp())
    assert a.record["components"]["latency"] == b.record["components"]["latency"]
    assert a.record["components"]["latency"]["drawn"]["pessimistic"]["bf"]["total_ns"]["order"] > 0


def test_costs_need_a_source_and_the_rate_is_charged():
    root, _, ds = _root()
    with pytest.raises(PipelineError, match="source"):
        plan_pipeline(**_args(root, ds, costs={"maker_rate": 0.0, "taker_rate": 0.001, "spread": 0.0, "source": " "}))
    with pytest.raises(PipelineError):
        plan_pipeline(**_args(root, ds, costs={"taker_fee_pct": 0.1, "maker_fee_pct": 0.0, "slippage_pct": 0.0,
                                               "spread_pct": 0.0}))  # the round-2 form is not the declaration
    res = run_pipeline(plan_pipeline(**_args(root, ds, costs={"maker_rate": 0.0, "taker_rate": 0.001, "spread": 0.2,
                                                              "source": "test"})), runs_dir=tempfile.mkdtemp())
    f = res.instruments["binance"].fills[0]
    assert f["liquidity"] == "taker"
    assert f["fee"] == pytest.approx(abs(f["px"] * f["qty"]) * 0.001)


def test_a_riding_dataset_of_the_price_type_is_refused():
    root, _, ds = _root()
    ins = [D.instrument("bf", "bf_trades", "trade", ["binance"])]
    with pytest.raises(PipelineError, match="same event type"):
        plan_pipeline(**_args(root, ds, instruments=ins))


def test_the_fill_range_needs_both_sides_and_the_old_form_is_refused():
    root, _, ds = _root()
    for bad in ({"optimistic": {"tier": 3}}, {"pessimistic": {"tier": 1}},
                {"optimistic": {"tier": 9}, "pessimistic": {"tier": 1}},
                {"price": "first_observed_at_or_after", "trade": "px", "quote": {"buy": "ask", "sell": "bid"},
                 "bar": "open", "latency_ns": 0}):
        with pytest.raises(PipelineError):
            plan_pipeline(**_args(root, ds, fill=bad))


def test_the_run_id_changes_with_every_declared_input_and_not_with_the_runs_dir():
    root, _, ds = _root()
    base = plan_pipeline(**_args(root, ds)).run_id
    assert plan_pipeline(**_args(root, ds)).run_id == base
    changed = [
        _args(root, ds, fill={"optimistic": {"tier": 4}, "pessimistic": {"tier": 1}}),
        _args(root, ds, latency=dict(D.LATENCY0, notice={"kind": "constant", "ns": 1})),
        _args(root, ds, costs=dict(D.COSTS0, maker_rate=0.0001, source="x")),
        _args(root, ds, account=dict(D.ACCOUNT, cash=1e11)),
        _args(root, ds, strategy={"kind": "schedule", "orders": S.SCHEDULE[:2]}),
        _args(root, ds, instruments=INSTRUMENTS[:4]),
    ]
    ids = {plan_pipeline(**a).run_id for a in changed}
    assert base not in ids and len(ids) == len(changed)
    g1 = plan_pipeline(**_gen_args(root)).run_id
    g2 = plan_pipeline(**_gen_args(root, datasets=[{"name": "g", "generator": dict(GEN, seed=6)}])).run_id
    assert g1 != g2


def test_the_range_reaches_tier_6_and_funding_is_declarable():
    """The integrated run takes every FillSpec item 2 has (tier 6's impact function as a mapping) and a funding
    rule; on a generated book the pessimistic side (impact) buys dearer and sells cheaper than the optimistic one."""
    root, _, _ = _root()
    gen = {"name": "random_walk", "seed": 1, "params": {"kind": "quote", "start_ns": T0, "step_ns": NS, "n": 600,
                                                        "price0": 100.0, "step_pct": 0.05, "qty": 5.0,
                                                        "spread_pct": 0.02}}
    fill = {"optimistic": {"tier": 3},
            "pessimistic": {"tier": 6, "impact": {"kind": "linear_temporary", "basis": "opposite_best", "k": 0.01}}}
    costs = dict(D.COSTS0, funding={"price": "event_mark"})
    res = run_pipeline(plan_pipeline(**_gen_args(root, datasets=[{"name": "g", "generator": gen}],
                                                 instruments=[D.instrument("g", "g", "quote")], fill=fill, costs=costs,
                                                 strategy={"kind": "schedule", "orders": [
                                                     {"t_ns": T0 + 10 * NS, "side": "buy", "qty": 1.0},
                                                     {"t_ns": T0 + 100 * NS, "side": "sell", "qty": 1.0}]})),
                       runs_dir=tempfile.mkdtemp())
    opt, pes = res.range["optimistic"]["g"].fills, res.range["pessimistic"]["g"].fills
    assert [f["side"] for f in opt] == [f["side"] for f in pes] == ["buy", "sell"]
    assert pes[0]["px"] > opt[0]["px"] and pes[1]["px"] < opt[1]["px"]
    assert res.record["engine"]["pessimistic"]["g"]["fill_tier"] == 6
    assert res.record["config"]["costs"]["funding"] == {"price": "event_mark"}

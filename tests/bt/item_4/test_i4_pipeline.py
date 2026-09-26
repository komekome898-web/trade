"""The integrated run (bot.bt.pipeline): declared files of every asset -> the
core per instrument -> run record, exports, the dashboard's run view, in one
call executed twice.

The refusal grid is the declaration's own space: purpose {動作確認, 研究,
None, "other"} x origin {real, synthetic} x strategy {schedule,
seeded_random, price_rule} x pre-registration {none, hash} = 48 cells; the
expected accept / refuse of each cell is written from the rule text
(委任文 §4) in `expected_accept`, not from the code. Not in the grid:
several origins mixed in one run (any "real" dataset makes the run real --
test_one_real_dataset_makes_the_run_real), a pre-registration FILE (the
hash form is gridded; the file form is test_prereg_file_gives_its_sha256).
"""
from __future__ import annotations

import copy
import hashlib
import itertools
import json
import os
import tempfile

import pytest

import i4_scenes as S
from bot.bt.pipeline import PipelineError, plan_pipeline, run_pipeline
from bot.bt.report.exports import read_export
from bot.monitoring.backtest_view import TABS, WARNING, run_view

T0 = S.T0
NS = S.NS


def _root():
    files, ds = S._pipeline_files()
    root = tempfile.mkdtemp(prefix="i4w_pipe_")
    for f in files:
        p = os.path.join(root, f["path"])
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as fh:
            fh.write(S.file_bytes(f))
    return root, files, ds


def _args(root, ds, **over):
    a = dict(root=root, datasets=copy.deepcopy(ds), instruments=copy.deepcopy(S.INSTRUMENTS),
             strategy={"kind": "schedule", "orders": copy.deepcopy(S.SCHEDULE)}, fill=dict(S.FILL_RULE),
             costs=dict(S.ZERO), purpose="動作確認")
    a.update(over)
    return a


STRATS = {"schedule": {"kind": "schedule", "orders": S.SCHEDULE},
          "seeded_random": {"kind": "seeded_random", "seed": 7, "times": [T0, T0 + 300 * NS], "qty": 1.0},
          "price_rule": {"kind": "price_rule", "buy_below": 1e9, "sell_above": 1.0, "qty": 1.0}}
HASH = "ab" * 32


def expected_accept(purpose, origin, strat, prereg) -> bool:
    """委任文 §4, read as rules: a purpose is required and is 動作確認 or 研究; 研究 needs the pre-registration's
    hash; on real data a 動作確認 run takes only time-only procedures or seeded random."""
    if purpose not in ("動作確認", "研究"):
        return False
    if purpose == "研究" and prereg is None:
        return False
    if origin == "real" and purpose == "動作確認" and strat == "price_rule":
        return False
    return True


GRID = list(itertools.product(("動作確認", "研究", None, "other"), ("real", "synthetic"), tuple(STRATS), (None, HASH)))


def test_refusal_grid_matches_the_rule_text():
    assert len(GRID) == 48
    root, _, ds = _root()
    for purpose, origin, strat, prereg in GRID:
        d2 = [dict(d, origin=origin) for d in ds]
        try:
            plan_pipeline(**_args(root, d2, purpose=purpose, strategy=STRATS[strat], prereg_sha256=prereg))
            got = True
        except PipelineError:
            got = False
        assert got == expected_accept(purpose, origin, strat, prereg), (purpose, origin, strat, prereg)


def test_one_real_dataset_makes_the_run_real():
    root, _, ds = _root()
    d2 = [dict(d, origin="synthetic") for d in ds]
    d2[3]["origin"] = "real"
    with pytest.raises(PipelineError, match="time-only"):
        plan_pipeline(**_args(root, d2, strategy=STRATS["price_rule"]))


def test_origin_has_no_default():
    root, _, ds = _root()
    d2 = copy.deepcopy(ds)
    d2[0].pop("origin")
    with pytest.raises(PipelineError, match="origin"):
        plan_pipeline(**_args(root, d2))


def test_prereg_file_gives_its_sha256():
    root, _, ds = _root()
    with open(os.path.join(root, "prereg.md"), "wb") as fh:
        fh.write(b"# prereg\n")
    plan = plan_pipeline(**_args(root, ds, purpose="研究", prereg="prereg.md"))
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
    assert {k: v["num_trades"] for k, v in m["data"]["by_instrument"].items()} == {i["name"]: 2 for i in S.INSTRUMENTS}
    view = run_view(runs, res.run_id)
    assert [t["label"] for t in view["tabs"]] == list(TABS)
    assert all(WARNING in t["text"] for t in view["tabs"])
    assert res.events_read == {d["name"]: len(S.file_bytes(f).decode().strip().splitlines()) - (1 if d["spec"]["header"] else 0)
                               for d, f in zip(ds, files)}


def test_a_research_run_on_synthetic_data_has_no_smoke_banner():
    root, _, ds = _root()
    runs = tempfile.mkdtemp(prefix="i4w_runs_")
    d2 = [dict(d, origin="synthetic") for d in ds]
    res = run_pipeline(plan_pipeline(**_args(root, d2, purpose="研究", prereg_sha256=HASH,
                                             strategy=STRATS["price_rule"])), runs_dir=runs)
    view = run_view(runs, res.run_id)
    assert view["warning"] is None and not any(WARNING in t["text"] for t in view["tabs"])


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


def test_latency_moves_the_fill_to_a_later_observation():
    root, _, ds = _root()
    base = run_pipeline(plan_pipeline(**_args(root, ds)), runs_dir=tempfile.mkdtemp())
    slow = run_pipeline(plan_pipeline(**_args(root, ds, fill=dict(S.FILL_RULE, latency_ns=250_000_000))),
                        runs_dir=tempfile.mkdtemp())
    # bf's first trade after 00:00 is at +0.2 s: with 0.25 s of order latency it is missed, the next is at +120 s
    assert base.instruments["bf"].fills[0]["t_ns"] == T0 + 200_000_000
    assert slow.instruments["bf"].fills[0]["t_ns"] == T0 + 120 * NS


def test_costs_need_a_source_and_a_quote_carries_its_spread():
    root, _, ds = _root()
    with pytest.raises(PipelineError, match="source"):
        plan_pipeline(**_args(root, ds, costs=dict(S.ZERO, taker_fee_pct=0.1)))
    with pytest.raises(PipelineError, match="spread"):
        plan_pipeline(**_args(root, ds, costs=dict(S.ZERO, spread_pct=0.1, source="test")))
    ins = [i for i in S.INSTRUMENTS if i["name"] != "fx_tick"]
    d2 = [d for d in ds if d["name"] != "fx_ticks"]
    res = run_pipeline(plan_pipeline(**_args(root, d2, instruments=ins,
                                             costs=dict(S.ZERO, taker_fee_pct=0.1, slippage_pct=0.01, source="test"))),
                       runs_dir=tempfile.mkdtemp())
    f = res.instruments["binance"].fills[0]
    assert f["side"] == "buy" and f["px"] == 96000.1 * (1 + 0.01 / 100)
    assert f["fee"] == abs(f["px"] * f["qty"]) * 0.1 / 100


def test_a_riding_dataset_of_the_price_type_is_refused():
    root, _, ds = _root()
    ins = [{"name": "bf", "price": "bf_trades", "with": ["binance"]}]
    with pytest.raises(PipelineError, match="same event type"):
        plan_pipeline(**_args(root, ds, instruments=ins))


def test_the_fill_rule_is_one_and_stated():
    root, _, ds = _root()
    for k, v in (("bar", "close"), ("price", "last"), ("quote", {"buy": "bid", "sell": "ask"})):
        with pytest.raises(PipelineError):
            plan_pipeline(**_args(root, ds, fill=dict(S.FILL_RULE, **{k: v})))
    bad = dict(S.FILL_RULE)
    bad.pop("latency_ns")
    with pytest.raises(PipelineError):
        plan_pipeline(**_args(root, ds, fill=bad))


def test_the_run_id_changes_with_every_declared_input_and_not_with_the_runs_dir():
    root, _, ds = _root()
    base = plan_pipeline(**_args(root, ds)).run_id
    assert plan_pipeline(**_args(root, ds)).run_id == base
    changed = [
        _args(root, ds, fill=dict(S.FILL_RULE, latency_ns=1)),
        _args(root, ds, costs=dict(S.ZERO, maker_fee_pct=0.01, source="x")),
        _args(root, ds, strategy={"kind": "schedule", "orders": S.SCHEDULE[:2]}),
        _args(root, [dict(d, origin="synthetic") for d in ds]),
        _args(root, ds, instruments=S.INSTRUMENTS[:4]),
    ]
    ids = {plan_pipeline(**a).run_id for a in changed}
    assert base not in ids and len(ids) == len(changed)

"""1 分足の指値の約定の決まり(オーナーのシナリオ L-769・L-770)の受け入れの場面 1〜5
(委任文 docs/DISCUSSIONS/2026-10-06_held_batches/DELEGATION_fill_scenario_L769.md「受け入れの場面」)。

オーナーの逐語:
- L-769「**合図が出るのはcloseのタイミング(前の足) 指値は合図の次の足で出してhighからlowの範囲内であれば約定
  指値決済の良い側はその足内で指値があれば通り、悪い側は次の足内から**」
- L-770「**a 足の始値で約定する(出した時点で相場より有利な指値なので、すぐ約定したとみなす) b 建ての指値と一緒に決済の
  指値を出しておき、建ての約定のあと同じ足の中で決済の値段に届けば約定、とする(決済の値段は合図の足の終値から計算)**」

前半は取引所の模型(`bot.bt.fill.venue.SimVenue`)に手で書いた足を渡す試験で、期待の数は足の数から手計算で書く。
足 i は [i 分, i+1 分) で、i+1 分に閉じて届く。足 t = 足 0(60 秒に閉じる)、足 t+1 = 足 1(120 秒に閉じる)。
後半は道の走らせ(`bot.bt.pipeline`、合成の足 random_walk)で、表と検査(`check_outputs` の (vii))を確かめる。
道の走らせの手計算: 1 段の量 = 200,000 × 0.70 ÷ 段数 ÷ 値段、0.001 BTC 未満切り捨て。足 k 本目は 0:k に閉じて届く。
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import importlib.util
import io
import json
import math
import os
import shutil
import sys

import pytest

from bot.bt import pipeline as P
from bot.bt.core import BarEvent, CancelRequest, Canceled, Fill, OrderRequest, Reject
from bot.bt.costs import CostSchedule
from bot.bt.fill import ATTACHED_KEY, FillSpec, FillSpecError, SimVenue
from bot.bt.orders import FaultPlan, Product, VenueRules
from bot.bt.road import check_outputs
from bot.bt.road.tables import ROAD_DIR, SCHEMA, read_csv

S = 10**9
M = 60 * S  # 1 分(ns)
OPT = FillSpec(tier=2, bar_rule="range_open", attached_exit="same_bar")
PES = FillSpec(tier=2, bar_rule="range_open", attached_exit="next_bar")
OLD = FillSpec(tier=2)


def venue(fill):
    return SimVenue(product=Product("X", "v", 0.5, 0.001, 0.001, "JPY", True),
                    rules=VenueRules(market_ref="next_bar_open"), fill=fill,
                    costs=CostSchedule(maker_rate=0.0, taker_rate=0.0, source="試験: 0"), faults=FaultPlan(()), l3=None)


def bar(i, o, h, lo, c):
    return BarEvent(received_time_ns=(i + 1) * M, start_time_ns=i * M, open=o, high=h, low=lo, close=c, volume=1.0)


def limit(coid, side, px, size=1.0, **kw):
    return OrderRequest(side=side, order_type="limit", size=size, price=px, client_order_id=coid, **kw)


def exit_of(coid, parent, side, px, size=1.0):
    return limit(coid, side, px, size, reduce_only=True, extra=((ATTACHED_KEY, parent),))


def fills(reports):
    return [(r.client_order_id, r.price, r.size) for r in reports if type(r) is Fill]


BAR_T = bar(0, 100.0, 101.0, 99.0, 100.0)  # 合図の足 t(終値 100)


# ---------------------------------------------------------------- 場面 1〜3: 建ての指値の当て方(楽観側・悲観側で同じ)
@pytest.mark.parametrize("spec", [OPT, PES])
def test_scene1_limit_at_signal_close_fills_on_next_bar_at_limit(spec):
    # 足 t の終わり(60 秒)に買いの指値 100(= 足 t の終値)。足 t+1: 安値 99.5 ≤ 100 ≤ 高値 101 → 足 t+1 で 100 で約定
    v = venue(spec)
    v.on_market_event(BAR_T, 1 * M)
    v.on_order(limit("b", "buy", 100.0), 1 * M)
    assert fills(v.on_market_event(bar(1, 100.5, 101.0, 99.5, 100.0), 2 * M)) == [("b", 100.0, 1.0)]
    assert [(r.time_ns, r.price) for r in v.fills] == [(2 * M, 100.0)]  # 約定の時刻 = 足 t+1 が閉じた 120 秒


def test_scene1_old_rule_skips_the_bar_starting_when_the_limit_rested():
    # 今の決まり(bar_rule 無し)は変えない: 同じ場面で足 t+1 は当てない(置かれた時刻ちょうどに始まる足)
    v = venue(OLD)
    v.on_market_event(BAR_T, 1 * M)
    v.on_order(limit("b", "buy", 100.0), 1 * M)
    assert fills(v.on_market_event(bar(1, 100.5, 101.0, 99.5, 100.0), 2 * M)) == []
    assert fills(v.on_market_event(bar(2, 100.0, 100.5, 99.5, 100.0), 3 * M)) == [("b", 100.0, 1.0)]


@pytest.mark.parametrize("spec", [OPT, PES])
def test_scene2_limit_beyond_range_in_filling_direction_fills_at_open(spec):
    # 足 t+1: 始値 100.5・高値 101・安値 99.5。買いの指値 102 > 高値 101 → 始値 100.5 で約定。
    # 売りの指値 98.5 < 安値 99.5 → 始値 100.5 で約定(L-770 a)
    for order, want in ((limit("b", "buy", 102.0), [("b", 100.5, 1.0)]), (limit("s", "sell", 98.5), [("s", 100.5, 1.0)])):
        v = venue(spec)  # 1 つずつ(2 つを同じ取引所に置くと、互いに向かい合う自分の注文になる)
        v.on_market_event(BAR_T, 1 * M)
        v.on_order(order, 1 * M)
        assert fills(v.on_market_event(bar(1, 100.5, 101.0, 99.5, 100.0), 2 * M)) == want


@pytest.mark.parametrize("spec", [OPT, PES])
def test_scene3_limit_beyond_range_the_other_way_does_not_fill(spec):
    # 足 t+1 の安値 99.5。買いの指値 99 < 安値 → 足 t+1 では約定しない。売りの指値 101.5 > 高値 101 → 約定しない。
    # 残って、足 t+2(安値 98.5・高値 102)で範囲の内に入ったところで指値の値段で約定
    v = venue(spec)
    v.on_market_event(BAR_T, 1 * M)
    v.on_order(limit("b", "buy", 99.0), 1 * M)
    v.on_order(limit("s", "sell", 101.5), 1 * M)
    assert fills(v.on_market_event(bar(1, 100.5, 101.0, 99.5, 100.0), 2 * M)) == []
    assert v.open_orders() == [("buy", 1.0), ("sell", 1.0)]
    assert fills(v.on_market_event(bar(2, 100.0, 102.0, 98.5, 100.0), 3 * M)) == [("b", 99.0, 1.0), ("s", 101.5, 1.0)]


# ---------------------------------------------------------------- 場面 4: 建てと一緒に出す決済の指値(L-770 b)
def _scene4(spec):
    # 足 t の終わりに、建ての買いの指値 100 と決済の売りの指値 101 を一緒に出す
    v = venue(spec)
    v.on_market_event(BAR_T, 1 * M)
    v.on_order(limit("e", "buy", 100.0), 1 * M)
    v.on_order(exit_of("x", "e", "sell", 101.0), 1 * M)
    return v


def test_scene4_optimistic_exit_fills_on_the_entry_bar():
    # 足 t+1: 安値 99.5 ≤ 100 → 建てが 100 で約定。高値 101 ≥ 101(101 は範囲の内)→ 楽観側は同じ足 t+1 で 101 で約定
    v = _scene4(OPT)
    assert fills(v.on_market_event(bar(1, 100.5, 101.0, 99.5, 100.0), 2 * M)) == [("e", 100.0, 1.0), ("x", 101.0, 1.0)]
    assert v.position == 0.0 and v.open_orders() == []


def test_scene4_pessimistic_exit_starts_on_the_next_bar():
    # 同じ足 t+1 で、悲観側は建てだけ約定。足 t+2(安値 100・高値 101.5)で 101 が範囲の内 → 足 t+2 で 101 で約定
    v = _scene4(PES)
    assert fills(v.on_market_event(bar(1, 100.5, 101.0, 99.5, 100.0), 2 * M)) == [("e", 100.0, 1.0)]
    assert v.open_orders() == [("sell", 1.0)]
    assert fills(v.on_market_event(bar(2, 100.5, 101.5, 100.0, 101.0), 3 * M)) == [("x", 101.0, 1.0)]
    assert [(r.client_order_id, r.time_ns) for r in v.fills] == [("e", 2 * M), ("x", 3 * M)]


def test_scene4_pessimistic_exit_waits_while_next_bar_does_not_reach():
    # 足 t+2 の高値 100.5 < 101(売りの約定しない向きの外)→ 約定しない。足 t+3 の始値 101.5・安値 101.5 > 101
    # (売りの指値 < 安値 = 約定する向きの外)→ 足 t+3 の始値 101.5 で約定
    v = _scene4(PES)
    v.on_market_event(bar(1, 100.5, 101.0, 99.5, 100.0), 2 * M)
    assert fills(v.on_market_event(bar(2, 100.0, 100.5, 99.5, 100.0), 3 * M)) == []
    assert fills(v.on_market_event(bar(3, 101.5, 102.0, 101.5, 102.0), 4 * M)) == [("x", 101.5, 1.0)]


def test_scene4_optimistic_exit_outside_entry_bar_goes_on_from_next_bar():
    # 楽観側でも、決済の値段 101 が建ての足 t+1(高値 100.8)の範囲に入らなければ、その足では約定せず、足 t+2 から当てる
    v = _scene4(OPT)
    assert fills(v.on_market_event(bar(1, 100.5, 100.8, 99.5, 100.0), 2 * M)) == [("e", 100.0, 1.0)]
    assert fills(v.on_market_event(bar(2, 100.5, 101.5, 100.0, 101.0), 3 * M)) == [("x", 101.0, 1.0)]


@pytest.mark.parametrize("spec", [OPT, PES])
def test_scene4_exit_is_nothing_before_the_entry_fills(spec):
    # 建てが約定しない足 t+1(安値 100.5 > 100)では、決済の値段 101 が範囲の内でも決済は約定しない(量 0)
    v = _scene4(spec)
    assert fills(v.on_market_event(bar(1, 100.5, 101.5, 100.5, 101.0), 2 * M)) == []
    assert v.open_orders() == [("buy", 1.0), ("sell", 0.0)]


@pytest.mark.parametrize("spec", [OPT, PES])
def test_scene4_entry_canceled_unfilled_takes_the_exit(spec):
    # 建てが約定しないまま取り消されたら、決済も消える(取引所が閉じる。理由 attached_parent_closed)
    v = _scene4(spec)
    out = v.on_cancel(CancelRequest(client_order_id="e"), 90 * S)
    assert [(type(r).__name__, r.client_order_id, r.reason) for r in out] == [
        ("Canceled", "e", "canceled"), ("Canceled", "x", "attached_parent_closed")]
    assert v.open_orders() == []


def test_scene4_partly_filled_entry_leaves_the_exit_for_that_part():
    # 建て 1.0 のうち 0.4 だけ約定(取引所の模型の中から 0.4 だけ約定させる)→ 決済の量は 0.4。建てを取り消すと、
    # 決済は 0.4 で残り、0.4 約定して閉じる(理由 attached_parent_part_filled)
    v = _scene4(PES)
    out: list = []
    v._fill(v._live["e"], 100.0, 0.4, "maker", 2 * M, out)
    assert fills(out) == [("e", 100.0, 0.4)] and v.open_orders() == [("buy", 0.6), ("sell", 0.4)]
    assert [type(r).__name__ for r in v.on_cancel(CancelRequest(client_order_id="e"), 2 * M + 1)] == ["Canceled"]
    rep = v.on_market_event(bar(2, 100.5, 101.5, 100.0, 101.0), 3 * M)
    assert [(type(r).__name__, r.client_order_id, getattr(r, "size", None), getattr(r, "reason", None)) for r in rep] == [
        ("Fill", "x", 0.4, None), ("Canceled", "x", None, "attached_parent_part_filled")]
    assert v.position == 0.0


def test_scene4_exit_refusals():
    v = venue(PES)
    v.on_market_event(BAR_T, 1 * M)
    # 建てが取引所に無い
    assert v.on_order(exit_of("x0", "nope", "sell", 101.0), 1 * M) == [Reject("x0", "attached_parent_unknown")]
    # 建てが約定しないまま閉じている
    v.on_order(limit("e", "buy", 100.0), 1 * M)
    v.on_cancel(CancelRequest(client_order_id="e"), 1 * M)
    assert v.on_order(exit_of("x1", "e", "sell", 101.0), 1 * M) == [Reject("x1", "attached_parent_closed_unfilled")]
    # reduce_only でない
    v.on_order(limit("e2", "buy", 100.0), 1 * M)
    bad = limit("x2", "sell", 101.0, extra=((ATTACHED_KEY, "e2"),))
    assert v.on_order(bad, 1 * M) == [Reject("x2", "attached_exit_is_a_gtc_reduce_only_limit")]
    # 同じ向き(建ての決済でない)
    assert v.on_order(exit_of("x3", "e2", "buy", 99.0), 1 * M) == [Reject("x3", "attached_parent_not_an_entry")]
    # 決まりを選んでいない走らせ(attached_exit が無い)は止まる
    w = venue(OLD)
    w.on_order(limit("e", "buy", 100.0), 1 * M)
    with pytest.raises(FillSpecError, match="attached_exit"):
        w.on_order(exit_of("x", "e", "sell", 101.0), 1 * M)


def test_fill_spec_rule_fields():
    with pytest.raises(FillSpecError, match="go together"):
        FillSpec(tier=2, bar_rule="range_open")
    with pytest.raises(FillSpecError, match="tier 2"):
        FillSpec(tier=3, bar_rule="range_open", attached_exit="same_bar")
    with pytest.raises(FillSpecError, match="bar_rule"):
        FillSpec(tier=2, bar_rule="close", attached_exit="same_bar")
    with pytest.raises(FillSpecError, match="attached_exit"):
        FillSpec(tier=2, bar_rule="range_open", attached_exit="later")
    assert OLD.bar_rule is None and OLD.attached_exit is None  # 既定は今の決まり


# ---------------------------------------------------------------- 道の走らせ(合成の足)
T0 = 1_700_000_040_000_000_000  # 分の区切り(0:00 とみなす。2023-11-14、合成の足の時刻)
HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = "bot.strategy.road_l769_test"
ZERO = {"kind": "constant", "ns": 0}
NEW = {"optimistic": {"tier": 2, "bar_rule": "range_open", "attached_exit": "same_bar"},
       "pessimistic": {"tier": 2, "bar_rule": "range_open", "attached_exit": "next_bar"}}
OLD_FILL = {"optimistic": {"tier": 2}, "pessimistic": {"tier": 2}}
SIDES = ("optimistic", "pessimistic")


@pytest.fixture(scope="module", autouse=True)
def l769_module():
    spec = importlib.util.spec_from_file_location(MODULE, os.path.join(HERE, "road_l769_strategy.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[MODULE] = mod
    spec.loader.exec_module(mod)
    yield mod
    sys.modules.pop(MODULE, None)


def _gen(step_pct=0.0, n=12, seed=1):
    return {"name": "random_walk", "seed": seed, "params": {"kind": "bar", "start_ns": T0, "step_ns": M, "n": n,
                                                            "price0": 5_000_000.0, "step_pct": step_pct, "qty": 1.0}}


def _run(tmp_path, gen, params, fill=None):
    plan = P.plan_pipeline(
        root=str(tmp_path), datasets=[{"name": "g", "generator": gen}],
        instruments=[{"name": "BTCJPY", "price": "g", "with": [],
                      "product": {"symbol": "BTCJPY", "venue": "test", "tick": 0.5, "min_qty": 0.001,
                                  "qty_step": 0.001, "quote_ccy": "JPY", "margin": True},
                      "rules": {"market_ref": "next_bar_open"}}],
        strategy={"kind": "module", "module": MODULE, "factory": "pipeline_strategy", "params": params},
        fill=fill or NEW, latency={"feed": ZERO, "order": ZERO, "cancel": ZERO, "notice": ZERO},
        costs={"maker_rate": 0, "taker_rate": 0, "spread": 0, "source": "試験: 0"},
        account={"currency": "JPY", "cash": 1e9, "leverage": 1, "mark": "last_trade", "liquidation": None,
                 "margin_check": "position_only"},
        purpose="動作確認", prereg=None)
    res = P.run_pipeline(plan, runs_dir=str(tmp_path / "runs"))
    return res.run_dir, os.path.join(res.run_dir, ROAD_DIR)


def _rows(gen):
    return P._generate(gen)[1]


def _bars(gen, open_=True):
    return [{"t_ns": r["t_ns"], "high": r["high"], "low": r["low"], "close": r["close"],
             **({"open": r["open"]} if open_ else {})} for r in _rows(gen)]


def _table(store, name):
    return read_csv(os.path.join(store, SCHEMA["tables"][name]["file"]), name)[1]


def _of(rows, side):
    return [r for r in rows if r["range"] == side]


def _at(k):
    return str(T0 + k * M)


FLAT = _gen()  # 値段が動かない足(始値 = 高値 = 安値 = 終値 = 5,000,000)
WALK = _gen(step_pct=0.3, n=20, seed=5)


def test_road_scene1_flat(tmp_path):
    # 足 3 本目(0:03 に閉じる)の終値 5,000,000 に買いの指値(段数 2: 0.014)。足 4 本目 [0:03, 0:04) の範囲の内 →
    # 0:04 に 5,000,000 で約定(両側とも)
    _, store = _run(tmp_path, FLAT, {"mode": "entry", "quote_ccy": "JPY", "levels": 2, "open_bar": 3})
    assert check_outputs(store, _bars(FLAT)).failures == []
    f = _table(store, "fills")
    for side in SIDES:
        assert [(x["order_id"], x["t_ns"], x["px"], x["qty"], x["liquidity"]) for x in _of(f, side)] == [
            ("road-0", _at(4), "5000000.0", "0.014", "maker")]


def _tick_up(x):
    return math.floor(x * 2) / 2 + 0.5


def _tick_down(x):
    return math.ceil(x * 2) / 2 - 0.5


@pytest.mark.parametrize("side", ["buy", "sell"])
def test_road_scene2_beyond_range_fills_at_open(tmp_path, side):
    # 足 4 本目(0:03〜0:04)の高値より上の買いの指値 / 安値より下の売りの指値 → 0:04 に足 4 本目の始値で約定
    b4 = _rows(WALK)[3]
    px = _tick_up(b4["high"]) if side == "buy" else _tick_down(b4["low"])
    _, store = _run(tmp_path, WALK, {"mode": "entry", "quote_ccy": "JPY", "levels": 1, "open_bar": 3, "side": side,
                                     "limit_px": px})
    assert check_outputs(store, _bars(WALK)).failures == []
    for s in SIDES:
        assert [(x["t_ns"], float(x["px"])) for x in _of(_table(store, "fills"), s)] == [(_at(4), b4["open"])]
    # 足の JSON に始値が無ければ、始値の約定を確かめられないので落ちる
    f = check_outputs(store, _bars(WALK, open_=False)).failures
    assert f and all(x["check"] == "vii" and "始値(open)が無い" in x["reason"] for x in f)
    # 始値が違えば落ちる
    bars = _bars(WALK)
    bars[3]["open"] += 1.0
    f = check_outputs(store, bars).failures
    assert f and all(x["check"] == "vii" and "始値" in x["reason"] for x in f)


def test_road_scene3_other_side_does_not_fill_on_next_bar(tmp_path):
    # 足 4 本目の安値より下の買いの指値: 0:04 には約定しない。残って、最初に安値が指値に届く足 j で約定する
    # (j とその値段は足の数から: 範囲の内なら指値、高値より上なら始値)
    rows = _rows(WALK)
    px = _tick_down(rows[3]["low"])
    _, store = _run(tmp_path, WALK, {"mode": "entry", "quote_ccy": "JPY", "levels": 1, "open_bar": 3, "limit_px": px})
    assert check_outputs(store, _bars(WALK)).failures == []
    j = next(k for k in range(4, len(rows)) if rows[k]["low"] <= px)
    want = px if px <= rows[j]["high"] else rows[j]["open"]
    for s in SIDES:
        got = [(x["t_ns"], float(x["px"])) for x in _of(_table(store, "fills"), s)]
        assert got == [(_at(j + 1), want)] and _at(4) not in [g[0] for g in got]
    # 検査: 足 4 本目の安値を指値まで下げた足を渡すと、「それより前の当てる足で約定していたはず」で落ちる
    bars = _bars(WALK)
    bars[3]["low"] = px - 1.0
    f = check_outputs(store, bars).failures
    assert f and any(x["check"] == "vii" and "約定していたはず" in x["reason"] for x in f), f


def test_road_scene4_exit_with_entry(tmp_path):
    # 値段が動かない足。0:03 に建ての買いの指値 5,000,000(段数 2: 0.014)と決済の売りの指値 5,000,000 を一緒に出す。
    # 足 4 本目で建てが約定(0:04)。足 4 本目の高値 5,000,000 ≥ 決済の値段 → 楽観側は 0:04、悲観側は足 5 本目の 0:05 で約定
    run_dir, store = _run(tmp_path, FLAT, {"mode": "with_exit", "quote_ccy": "JPY", "levels": 2, "open_bar": 3,
                                           "exit_px": 5_000_000.0})
    assert check_outputs(store, _bars(FLAT)).failures == []
    o, f, tr = _table(store, "orders"), _table(store, "fills"), _table(store, "trades")
    for side, exit_at in (("optimistic", 4), ("pessimistic", 5)):
        assert [(r["order_id"], r["side"], r["order_type"], r["limit_px"], r["qty"], r["exit_kind"], r["attached_to"],
                 r["reduce_only"], r["qty_source"], r["state"]) for r in _of(o, side)] == [
            ("road-0", "buy", "limit", "5000000.0", "0.014", "", "", "false", "量の計算", "FILLED"),
            ("road-1", "sell", "limit", "5000000.0", "0.014", "with_entry", "road-0", "true", "建玉", "FILLED")]
        assert [(x["order_id"], x["t_ns"], x["px"], x["qty"]) for x in _of(f, side)] == [
            ("road-0", _at(4), "5000000.0", "0.014"), ("road-1", _at(exit_at), "5000000.0", "0.014")]
        assert [(x["status"], x["pnl_jpy"]) for x in _of(tr, side)] == [("closed", "0")]
    # 決済が建てと同じ足で約定した行は楽観側にしか無い: 走らせの記録の楽観側の決まりを next_bar に書き換えると落ちる
    with open(os.path.join(run_dir, "record.json"), encoding="utf-8") as fh:
        rec = json.load(fh)
    rec["config"]["fill"]["optimistic"]["attached_exit"] = "next_bar"
    with open(os.path.join(run_dir, "record.json"), "w", encoding="utf-8") as fh:
        json.dump(rec, fh)
    f = check_outputs(store, _bars(FLAT)).failures
    assert [x["check"] for x in f] == ["vii"] and "楽観側" in f[0]["reason"] and "optimistic" in f[0]["row"], f


def test_road_scene4_attached_to_is_bound(tmp_path):
    # attached_to を書き換えると (iii) で落ちる(repro.json の指紋を合わせなくても合わせても)
    run_dir, store = _run(tmp_path, FLAT, {"mode": "with_exit", "quote_ccy": "JPY", "levels": 2, "open_bar": 3,
                                           "exit_px": 5_000_000.0})
    for forge in (False, True):
        run = tmp_path / f"forge-{forge}"
        shutil.copytree(run_dir, run)
        d = run / ROAD_DIR
        path = os.path.join(d, SCHEMA["tables"]["orders"]["file"])
        head, rows = read_csv(path, "orders")
        rows[1]["attached_to"] = "road-9"
        buf = io.StringIO(newline="")
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(head)
        for r in rows:
            w.writerow([r[c] for c in head])
        with gzip.open(path, "wb") as fh:
            fh.write(buf.getvalue().encode("utf-8"))
        if forge:  # 書き換えた人が repro.json の road/ の指紋も合わせた場合
            rp = run / "repro.json"
            body = json.loads(rp.read_text(encoding="utf-8"))
            for n in os.listdir(d):
                body["sha256"][f"{ROAD_DIR}/{n}"] = hashlib.sha256((d / n).read_bytes()).hexdigest()
            rp.write_text(json.dumps(body), encoding="utf-8")
        f = check_outputs(str(d), _bars(FLAT)).failures
        assert any(x["check"] == "iii" and "attached_to" in x["reason"] for x in f), f


LINES = {"5": 5_010_000.0, "6": 5_005_000.0, "7": 5_000_000.0}
MOVING = {"mode": "moving_close", "quote_ccy": "JPY", "levels": 1, "open_bar": 3, "lines": LINES}


def test_road_scene5_replaced_exit_fills_on_next_bar(tmp_path):
    # 値段が動かない足。0:03 に成行の買い 0.028(足 4 本目の始値 5,000,000)。0:05 から足ごとに close の売りの指値を
    # 取り消して置き直す: 0:05 に 5,010,000(足 6 本目の高値 5,000,000 より上 = 約定しない向き)、0:06 に 5,005,000(同じ)、
    # 0:07 に 5,000,000 → 足 8 本目 [0:07, 0:08) の範囲の内 → 0:08 に 5,000,000 で約定、建玉 0
    _, store = _run(tmp_path, FLAT, MOVING)
    assert check_outputs(store, _bars(FLAT)).failures == []
    for side in SIDES:
        o = _of(_table(store, "orders"), side)
        assert [(r["order_id"], r["limit_px"], r["state"], r["placed_t_ns"]) for r in o] == [
            ("road-0", "", "FILLED", _at(3)), ("road-1", "5010000.0", "CANCELED", _at(5)),
            ("road-2", "5005000.0", "CANCELED", _at(6)), ("road-3", "5000000.0", "FILLED", _at(7))]
        assert [(x["order_id"], x["t_ns"], x["px"]) for x in _of(_table(store, "fills"), side)] == [
            ("road-0", _at(3), "5000000.0"), ("road-3", _at(8), "5000000.0")]


def test_road_scene5_old_rule_never_fills(tmp_path):
    # 今の決まり(bar_rule 無し)では、置き直した指値は置いた時刻に始まる足を当てられず、次の足の終わりに取り消されるので、
    # 一度も約定しない(0:07 からは 5,000,000 で置き直し続け、データの終わり 0:12 に出ている 1 つが残る)
    _, store = _run(tmp_path, FLAT, MOVING, fill=OLD_FILL)
    assert check_outputs(store, _bars(FLAT)).failures == []
    for side in SIDES:
        o = _of(_table(store, "orders"), side)
        assert [r["order_id"] for r in _of(_table(store, "fills"), side)] == ["road-0"]
        assert [r["state"] for r in o[1:]] == ["CANCELED"] * 7 + ["OPEN"]


def test_pipeline_fill_range_sides():
    with pytest.raises(P.PipelineError, match="same_bar"):
        P._check_fill({"optimistic": NEW["pessimistic"], "pessimistic": NEW["optimistic"]})
    with pytest.raises(P.PipelineError, match="bar_rule must be the same"):
        P._check_fill({"optimistic": NEW["optimistic"], "pessimistic": {"tier": 2}})
    fr = P._check_fill(NEW)
    assert (fr.optimistic.attached_exit, fr.pessimistic.attached_exit) == ("same_bar", "next_bar")
    assert P._check_fill(OLD_FILL).optimistic == OLD


def test_schema_texts():
    from bot.bt.road.tables import SCHEMA_VERSION, columns
    assert SCHEMA_VERSION == "road-record-6"
    assert columns("orders")[-2:] == ["exit_kind", "attached_to"]
    text = " ".join(SCHEMA["fill_rules"])
    for quote in ("指値は合図の次の足で出してhighからlowの範囲内であれば約定", "a 足の始値で約定する",
                  "指値決済の良い側はその足内で指値があれば通り", "悪い側は次の足内から"):
        assert quote in text

"""1 分足の指値の約定の決まり(L-769・L-770)の 2 周目: 批評家 1 回目の直し 1〜11 と、オーナーの決定 L-783
(委任文 docs/DISCUSSIONS/2026-10-06_held_batches/DELEGATION_fill_scenario_L769_r2.md、
批評家 docs/AUDITOR/VERDICTS/2026-10-07_fill_scenario_L769_critic1.md)。

オーナーの逐語:
- L-769「**合図が出るのはcloseのタイミング(前の足) 指値は合図の次の足で出してhighからlowの範囲内であれば約定
  指値決済の良い側はその足内で指値があれば通り、悪い側は次の足内から**」
- L-776「**間違った前提で組んだ確かめが通ってしまったら、後続が全て間違いになり結局全捨てになります。**」
- L-783「**間違えそうやから小数点以下は切り捨ててください**」「**今の作り**」「**maker**」

批評家の試しの場面(遅れ 1 ns・1 秒、刻みの外の値段、自分の注文との交差、bar_rule を消した record.json、側の入れ替え、
liquidity の書き換え、約定しなかった決済)を、走らせの止めか検査の失敗として確かめる。期待の数は足の数から手計算で書く。
足 k 本目は [0:(k-1), 0:k) で 0:k に閉じて届く(0:00 = T0 = 2023-11-14T22:14:00Z)。
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import importlib.util
import io
import json
import os
import shutil
import sys

import pytest

from bot.bt import pipeline as P
from bot.bt.core import BarEvent, Canceled, Fill, OrderRequest
from bot.bt.costs import CostSchedule
from bot.bt.fill import ATTACHED_KEY, FillRange, FillSpec, FillSpecError, SimVenue
from bot.bt.orders import FaultPlan, Product, VenueRules
from bot.bt.orders.errors import RuleNotDeclaredError
from bot.bt.road import check_outputs
from bot.bt.road.check import bar_ns_from_bars
from bot.bt.road.strategy import RoadStrategyError
from bot.bt.road.tables import ROAD_DIR, SCHEMA, read_csv

S = 10**9
M = 60 * S
T0 = 1_700_000_040_000_000_000  # 0:00(2023-11-14T22:14:00Z)
HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = "bot.strategy.road_l769_r2_test"
ZERO = {"kind": "constant", "ns": 0}
NEW = {"optimistic": {"tier": 2, "bar_rule": "range_open", "attached_exit": "same_bar"},
       "pessimistic": {"tier": 2, "bar_rule": "range_open", "attached_exit": "next_bar"}}
SIDES = ("optimistic", "pessimistic")
OPT = FillSpec(tier=2, bar_rule="range_open", attached_exit="same_bar")
PES = FillSpec(tier=2, bar_rule="range_open", attached_exit="next_bar")


@pytest.fixture(scope="module", autouse=True)
def l769_module():
    spec = importlib.util.spec_from_file_location(MODULE, os.path.join(HERE, "road_l769_strategy.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[MODULE] = mod
    spec.loader.exec_module(mod)
    yield mod
    sys.modules.pop(MODULE, None)


def _gen(step_pct=0.0, n=12, seed=1, step_ns=M, start_ns=T0):
    return {"name": "random_walk", "seed": seed, "params": {"kind": "bar", "start_ns": start_ns, "step_ns": step_ns, "n": n,
                                                            "price0": 5_000_000.0, "step_pct": step_pct, "qty": 1.0}}


FLAT = _gen()  # 値段が動かない足(始値 = 高値 = 安値 = 終値 = 5,000,000)
WALK = _gen(step_pct=0.3, n=20, seed=5)


def _plan(tmp_path, gen, params, fill=None, order=None, tick=0.5, rules=None):
    return P.plan_pipeline(
        root=str(tmp_path), datasets=[{"name": "g", "generator": gen}],
        instruments=[{"name": "BTCJPY", "price": "g", "with": [],
                      "product": {"symbol": "BTCJPY", "venue": "test", "tick": tick, "min_qty": 0.001,
                                  "qty_step": 0.001, "quote_ccy": "JPY", "margin": True},
                      "rules": rules or {"market_ref": "next_bar_open"}}],
        strategy={"kind": "module", "module": MODULE, "factory": "pipeline_strategy", "params": params},
        fill=fill or NEW, latency={"feed": ZERO, "order": order or ZERO, "cancel": ZERO, "notice": ZERO},
        costs={"maker_rate": 0, "taker_rate": 0, "spread": 0, "source": "試験: 0"},
        account={"currency": "JPY", "cash": 1e9, "leverage": 1, "mark": "last_trade", "liquidation": None,
                 "margin_check": "position_only"},
        purpose="動作確認", prereg=None)


def _run(tmp_path, gen, params, **kw):
    res = P.run_pipeline(_plan(tmp_path, gen, params, **kw), runs_dir=str(tmp_path / "runs"))
    return res.run_dir, os.path.join(res.run_dir, ROAD_DIR)


def _rows(gen):
    return P._generate(gen)[1]


def _bars(gen):
    return [{"t_ns": r["t_ns"], "open": r["open"], "high": r["high"], "low": r["low"], "close": r["close"]}
            for r in _rows(gen)]


def _table(store, name):
    return read_csv(os.path.join(store, SCHEMA["tables"][name]["file"]), name)[1]


def _of(rows, side):
    return [r for r in rows if r["range"] == side]


def _at(k, step=M):
    return str(T0 + k * step)


def _write_csv(path, head, rows):
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(head)
    for r in rows:
        w.writerow([r[c] for c in head])
    with open(path, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            gz.write(buf.getvalue().encode("utf-8"))


def _refresh(run):
    """書き換えた人が repro.json の指紋を全部(road/・record.json・fills.json)合わせた場合。"""
    rp = os.path.join(run, "repro.json")
    with open(rp, encoding="utf-8") as fh:
        body = json.load(fh)
    for k in body["sha256"]:
        with open(os.path.join(run, k), "rb") as fh:
            body["sha256"][k] = hashlib.sha256(fh.read()).hexdigest()
    with open(rp, "w", encoding="utf-8") as fh:
        json.dump(body, fh)


def _copy(run_dir, tmp_path, tag):
    run = str(tmp_path / f"copy-{tag}")
    shutil.copytree(run_dir, run)
    return run


def _edit_table(run, table, fn):
    path = os.path.join(run, ROAD_DIR, SCHEMA["tables"][table]["file"])
    head, rows = read_csv(path, table)
    fn(rows)
    _write_csv(path, head, rows)


def _edit_record(run, fn):
    path = os.path.join(run, "record.json")
    with open(path, encoding="utf-8") as fh:
        rec = json.load(fh)
    fn(rec["config"]["fill"])
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh)


def _failures(run, gen):
    return check_outputs(os.path.join(run, ROAD_DIR), _bars(gen)).failures


ENTRY = {"mode": "entry", "quote_ccy": "JPY", "levels": 2, "open_bar": 3}
WITH_EXIT = {"mode": "with_exit", "quote_ccy": "JPY", "levels": 2, "open_bar": 3, "exit_px": 5_000_000.0}


# ================================================================ 直すもの 1: 注文の遅れ(批評家 0-1)
@pytest.mark.parametrize("order", [{"kind": "constant", "ns": 1}, {"kind": "constant", "ns": S},
                                   {"kind": "empirical", "samples_ns": [0, 1], "seed": 1},
                                   {"kind": "seeded_uniform", "low_ns": 0, "high_ns": 5, "seed": 1}])
def test_fix1_order_latency_refused_before_the_run(tmp_path, order):
    # bar_rule を選んだ走らせで、注文の遅れが 0 でない値を取りうるなら、走らせを始める前に止める
    with pytest.raises(P.PipelineError, match="latency.order to be 0"):
        _plan(tmp_path, FLAT, ENTRY, order=order)


def test_fix1_zero_latency_forms_accepted_and_default_rule_untouched(tmp_path):
    # 遅れ 0 の書き方(constant 0・empirical [0]・seeded_uniform 0〜0)は通る。bar_rule を選ばない走らせは遅れがあっても今のまま
    for order in ({"kind": "empirical", "samples_ns": [0, 0], "seed": 1},
                  {"kind": "seeded_uniform", "low_ns": 0, "high_ns": 0, "seed": 1}):
        _plan(tmp_path, FLAT, ENTRY, order=order)
    _plan(tmp_path, FLAT, ENTRY, order={"kind": "constant", "ns": S},
          fill={"optimistic": {"tier": 2}, "pessimistic": {"tier": 2}})


def test_fix1_check_fails_when_acked_differs_from_placed(tmp_path, monkeypatch):
    # 止めを外して(試験の中だけ)遅れ 1 秒で走らせた記録: 0:03 に置いた買いが 0:03:01 に着き、足 4 本目 [0:03, 0:04) は当てられず
    # 足 5 本目の 0:05 に約定する。検査は (vii)「受け付けた時刻 ≠ 置いた時刻」で落とす(批評家の試し 2 では通っていた)
    monkeypatch.setattr(P, "_check_bar_rule_latency", lambda fr, lat: None)
    run, store = _run(tmp_path, FLAT, ENTRY, order={"kind": "constant", "ns": S})
    for side in SIDES:
        assert [(x["t_ns"], x["px"]) for x in _of(_table(store, "fills"), side)] == [(_at(5), "5000000.0")]
    f = check_outputs(store, _bars(FLAT)).failures
    assert f and {x["check"] for x in f} == {"vii"}, f
    assert all("受け付けた時刻" in x["reason"] and str(T0 + 3 * M + S) in x["reason"] for x in f), f
    assert len(f) == 2  # 両側の建て 1 つずつ


# ================================================================ 直すもの 2: 刻み(批評家 0-3、オーナーの決定 L-783)
@pytest.mark.parametrize("side,px,sent", [("buy", 5_000_000.4, "5000000.0"), ("sell", 5_000_000.6, "5000000.0")])
def test_fix2_limit_floored_to_tick_and_both_prices_kept(tmp_path, side, px, sent):
    # 刻み 1 円。計算した値段 5,000,000.4(買い)/ 5,000,000.6(売り)→ どちらも切り捨てて 5,000,000 で送る(向きで変えない)。
    # 足 4 本目(高値 = 安値 = 5,000,000)の範囲の内 → 0:04 に 5,000,000 で約定。量の計算は計算した値段のまま:
    # 140,000 ÷ 2 ÷ 5,000,000.4 = 0.013999… → 0.013、÷ 5,000,000.6 → 0.013
    run, store = _run(tmp_path, FLAT, dict(ENTRY, side=side, limit_px=px), tick=1.0)
    assert check_outputs(store, _bars(FLAT)).failures == []
    for s in SIDES:
        o = _of(_table(store, "orders"), s)
        assert [(r["limit_px"], r["sent_limit_px"], r["size_px"], r["qty"]) for r in o] == [(repr(px), sent, repr(px), "0.013")]
        assert [(x["t_ns"], x["px"], x["fill_case"]) for x in _of(_table(store, "fills"), s)] == [(_at(4), sent, "range")]
    # 取引所の模型に届いた値段は刻みの上(off_tick を宣言していない走らせでも止まらない)
    with open(os.path.join(run, "orders.json"), encoding="utf-8") as fh:
        assert len(json.load(fh)["data"]) == 2
    # 送った値段を書き換えると(指紋を合わせても)(vii) で落ちる
    cp = _copy(run, tmp_path, "sent")
    _edit_table(cp, "orders", lambda rs: rs[0].update(sent_limit_px="5000001.0"))
    _refresh(cp)
    f = _failures(cp, FLAT)
    assert any(x["check"] == "vii" and "切り捨てた値" in x["reason"] for x in f), f


def test_fix2_walk_in_range_off_tick_passes_and_judged_on_sent_price(tmp_path):
    # 批評家の WALK: 足 4 本目(安値 5,001,943.03〜高値 5,014,030.85)の範囲の内の計算した値段 5,007,987.4、刻み 1 円 →
    # 5,007,987 で送り、0:04 に 5,007,987 で約定。前は検査が「指値の値段でない」と誤って落としていた
    run, store = _run(tmp_path, WALK, dict(ENTRY, levels=1, limit_px=5_007_987.4), tick=1.0)
    assert check_outputs(store, _bars(WALK)).failures == []
    for s in SIDES:
        assert [(x["t_ns"], x["px"]) for x in _of(_table(store, "fills"), s)] == [(_at(4), "5007987.0")]


def test_fix2_tick_half_floors_to_half(tmp_path):
    # 刻み 0.5(1 円でない刻み: 刻みに切り捨てる形)。足 3 本目の終値 5,002,792.546… → 5,002,792.5。足 4 本目の範囲の内 → 0:04
    run, store = _run(tmp_path, WALK, dict(ENTRY, levels=1))
    assert check_outputs(store, _bars(WALK)).failures == []
    for s in SIDES:
        o = _of(_table(store, "orders"), s)[0]
        assert (o["limit_px"], o["sent_limit_px"]) == (repr(_rows(WALK)[2]["close"]), "5002792.5")
        assert [(x["t_ns"], x["px"]) for x in _of(_table(store, "fills"), s)] == [(_at(4), "5002792.5")]


def test_fix2_strategy_without_tick_does_not_send_limits(l769_module):
    s = l769_module.L769Strategy({"mode": "entry", "quote_ccy": "JPY", "levels": 1, "open_bar": 1})
    with pytest.raises(RoadStrategyError, match="刻みが渡されていない"):
        s._floor_to_tick(5_000_000.4)
    s.set_price_tick(1.0)
    assert s._floor_to_tick(5_000_000.4) == 5_000_000.0 and s._floor_to_tick(5_000_000.6) == 5_000_000.0


# ================================================================ 直すもの 3: 自分の注文との交差(批評家 問 2)
def _venue(fill, rules):
    return SimVenue(product=Product("X", "v", 0.5, 0.001, 0.001, "JPY", True), rules=rules, fill=fill,
                    costs=CostSchedule(maker_rate=0.0, taker_rate=0.0, source="試験: 0"), faults=FaultPlan(()), l3=None)


def _bar(i, o, h, lo, c):
    return BarEvent(received_time_ns=(i + 1) * M, start_time_ns=i * M, open=o, high=h, low=lo, close=c, volume=1.0)


def _cross(spec, rules):
    # 批評家の probe_cross: 足 t の終わりに 建ての買い 100(1.0)・決済の売り 98.5・別の買い 99.0(0.5)。
    # 足 t+1(始値 100.5・高値 101・安値 99.5): 建てが 100 で約定 → 決済の売り 98.5 が有効になり、待っている買い 99.0 と交差する
    v = _venue(spec, rules)
    v.on_market_event(_bar(0, 100.0, 101.0, 99.0, 100.0), 1 * M)
    v.on_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=100.0, client_order_id="e"), 1 * M)
    v.on_order(OrderRequest(side="sell", order_type="limit", size=1.0, price=98.5, client_order_id="x", reduce_only=True,
                            extra=((ATTACHED_KEY, "e"),)), 1 * M)
    v.on_order(OrderRequest(side="buy", order_type="limit", size=0.5, price=99.0, client_order_id="e2"), 1 * M)
    return v


def _rep(rs):
    return [(type(r).__name__, r.client_order_id, getattr(r, "price", None), getattr(r, "reason", None)) for r in rs]


@pytest.mark.parametrize("spec", [OPT, PES])
def test_fix3_exit_coming_into_force_meets_self_trade_rule(spec):
    # self_trade を宣言していない走らせは止まる(前は両方が足 t+2 で自分の指値どうしで約定していた)
    v = _cross(spec, VenueRules(market_ref="next_bar_open"))
    with pytest.raises(RuleNotDeclaredError, match="self_trade"):
        v.on_market_event(_bar(1, 100.5, 101.0, 99.5, 100.0), 2 * M)
    # cancel_maker: 待っていた買い 99.0 が self_trade で閉じ、決済は残る(98.5 は足 t+1 の範囲 99.5〜101 の外なので約定しない)
    v = _cross(spec, VenueRules(market_ref="next_bar_open", self_trade="cancel_maker"))
    assert _rep(v.on_market_event(_bar(1, 100.5, 101.0, 99.5, 100.0), 2 * M)) == [
        ("Fill", "e", 100.0, None), ("Canceled", "e2", None, "self_trade")]
    assert v.open_orders() == [("sell", 1.0)]
    # cancel_taker: 有効になった決済が self_trade で閉じる。買い 99.0 は足 t+1 の安値 99.5 より下なので約定しない
    v = _cross(spec, VenueRules(market_ref="next_bar_open", self_trade="cancel_taker"))
    assert _rep(v.on_market_event(_bar(1, 100.5, 101.0, 99.5, 100.0), 2 * M)) == [
        ("Fill", "e", 100.0, None), ("Canceled", "x", None, "self_trade")]
    assert v.open_orders() == [("buy", 0.5)] and v.position == 1.0


def test_fix3_road_exit_closed_by_self_trade_on_entry_bar_passes_check(tmp_path):
    # 道の走らせ(FLAT、self_trade = cancel_taker): 0:03 に 建ての買い 5,000,000(road-0)・決済の売り 5,000,000(road-1)・
    # もう 1 つの買い 5,000,000(road-2)。足 4 本目で建てが約定 → 決済が有効になり、待っている買い road-2 と交差 → 決済は
    # 0:04 に self_trade で閉じる。road-2 は足 4 本目の範囲の内で 0:04 に約定。建ての足で取引所が閉じた決済は「その足で約定
    # していない」と落とさない(楽観側の建ての足の検査は、取引所がその足で閉じた決済を見ない)
    params = dict(WITH_EXIT, mode="with_exit_and_buy", extra_px=5_000_000.0)
    _, store = _run(tmp_path, FLAT, params, rules={"market_ref": "next_bar_open", "self_trade": "cancel_taker"})
    for s in SIDES:
        o = _of(_table(store, "orders"), s)
        assert [(r["order_id"], r["state"], r["close_kind"], r["close_reason"], r["closed_venue_t_ns"]) for r in o] == [
            ("road-0", "FILLED", "", "", ""), ("road-1", "CANCELED", "venue", "self_trade", _at(4)),
            ("road-2", "FILLED", "", "", "")]
        assert [(x["order_id"], x["t_ns"]) for x in _of(_table(store, "fills"), s)] == [("road-0", _at(4)),
                                                                                         ("road-2", _at(4))]
    assert check_outputs(store, _bars(FLAT)).failures == []


# ================================================================ 直すもの 4: 閉じた理由の名前(批評家 問 2)
@pytest.mark.parametrize("spec", [OPT, PES])
def test_fix4_exit_above_entry_size_closed_with_its_name(spec):
    # 決済 2.0・建て 1.0(全部約定)。足 t+1 で建てが 100 で約定、決済の売り 100.5 は 1.0 だけ有効。楽観側は同じ足 t+1
    # (100.5 は範囲 99.5〜101 の内)、悲観側は足 t+2 で 1.0 約定し、越えた 1.0 を attached_exit_above_entry_filled で閉じる
    v = _venue(spec, VenueRules(market_ref="next_bar_open"))
    v.on_market_event(_bar(0, 100.0, 101.0, 99.0, 100.0), 1 * M)
    v.on_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=100.0, client_order_id="e"), 1 * M)
    v.on_order(OrderRequest(side="sell", order_type="limit", size=2.0, price=100.5, client_order_id="x", reduce_only=True,
                            extra=((ATTACHED_KEY, "e"),)), 1 * M)
    out = list(v.on_market_event(_bar(1, 100.5, 101.0, 99.5, 100.0), 2 * M))
    out += v.on_market_event(_bar(2, 100.5, 101.0, 99.5, 100.0), 3 * M)
    assert [r for r in _rep(out) if r[1] == "x"] == [("Fill", "x", 100.5, None),
                                                     ("Canceled", "x", None, "attached_exit_above_entry_filled")]
    assert v.position == 0.0


# ================================================================ 直すもの 5: record.json の指紋・印があるのに決まりが無い(批評家 3-1)
def test_fix5_record_without_bar_rule_fails(tmp_path):
    run_dir, store = _run(tmp_path, FLAT, WITH_EXIT)
    assert check_outputs(store, _bars(FLAT)).failures == []

    def drop(fill):
        for r in SIDES:
            fill[r].pop("bar_rule")
            fill[r].pop("attached_exit")
    # 指紋を合わせない: (vi) で落ちる(前は検査の失敗なし)
    cp = _copy(run_dir, tmp_path, "nofp")
    _edit_record(cp, drop)
    f = _failures(cp, FLAT)
    assert any(x["check"] == "vi" and x["row"] == "record.json" for x in f), f
    # 指紋も合わせた: 約定の行に range_open の印があるのに宣言に決まりが無いので (vii) で落ちる(黙って飛ばさない)
    _refresh(cp)
    f = _failures(cp, FLAT)
    assert {x["check"] for x in f} == {"vii"} and len(f) == 4, f  # 両側の建てと決済の約定 4 つ
    assert all("約定の印" in x["reason"] and "bar_rule None" in x["reason"] for x in f), f


# ================================================================ 直すもの 6: 側の組み合わせ(批評家 3-2)
@pytest.mark.parametrize("fill", [{"optimistic": NEW["pessimistic"], "pessimistic": NEW["optimistic"]},
                                  {"optimistic": NEW["optimistic"], "pessimistic": NEW["optimistic"]}])
def test_fix6_swapped_or_same_sides_fail_even_if_run_that_way(tmp_path, monkeypatch, fill):
    # pipeline の確かめを試験の中だけ外し、入れ替えた宣言・両側 same_bar の宣言で走らせた(record.json もその宣言)。
    # 検査が組み合わせを掛け直して (vii) で落とす(前は検査の失敗なし)
    monkeypatch.setattr(P, "_check_fill", lambda f: FillRange(optimistic=P._fill_spec(f["optimistic"], "optimistic"),
                                                              pessimistic=P._fill_spec(f["pessimistic"], "pessimistic")))
    run_dir, store = _run(tmp_path, FLAT, WITH_EXIT, fill=fill)
    f = check_outputs(store, _bars(FLAT)).failures
    assert f and {x["check"] for x in f} == {"vii"}, f
    assert any(x["row"] == "record.json" and "楽観側 = same_bar・悲観側 = next_bar" in x["reason"] for x in f), f


def test_fix6_fill_rows_carry_rule_and_side(tmp_path):
    # 約定の行に、どの決まり・どの側で当てたか: 建ては range、楽観側の決済は建ての足 0:04 で entry_bar、悲観側は 0:05 で range
    _, store = _run(tmp_path, FLAT, WITH_EXIT)
    got = {s: [(x["order_id"], x["t_ns"], x["fill_rule"], x["fill_exit_rule"], x["fill_case"], x["liquidity"])
               for x in _of(_table(store, "fills"), s)] for s in SIDES}
    assert got == {"optimistic": [("road-0", _at(4), "range_open", "same_bar", "range", "maker"),
                                  ("road-1", _at(4), "range_open", "same_bar", "entry_bar", "maker")],
                   "pessimistic": [("road-0", _at(4), "range_open", "next_bar", "range", "maker"),
                                   ("road-1", _at(5), "range_open", "next_bar", "range", "maker")]}


def test_fix6_open_fill_marked_open(tmp_path):
    # 足 4 本目の高値 5,014,030.85 より上の買い 5,014,031(刻み 1 円)→ 0:04 に始値 5,002,792.546… で約定、印は open・maker
    _, store = _run(tmp_path, WALK, dict(ENTRY, levels=1, limit_px=5_014_031.0), tick=1.0)
    assert check_outputs(store, _bars(WALK)).failures == []
    for s in SIDES:
        assert [(x["t_ns"], float(x["px"]), x["fill_case"], x["liquidity"]) for x in _of(_table(store, "fills"), s)] == [
            (_at(4), _rows(WALK)[3]["open"], "open", "maker")]


# ================================================================ 直すもの 7: liquidity(批評家 問 4、オーナーの決定 L-783)
def test_fix7_liquidity_rewritten_to_taker_fails(tmp_path):
    # road の約定と pipeline の fills.json の両方の建ての liquidity を maker → taker に書き換え、指紋を全部合わせる。
    # 前はどの検査も落とさなかった。今は (vii) で落ちる
    run_dir, _ = _run(tmp_path, FLAT, WITH_EXIT)
    for rng in SIDES:
        cp = _copy(run_dir, tmp_path, f"liq-{rng}")
        _edit_table(cp, "fills", lambda rs: [r.update(liquidity="taker") for r in rs
                                             if r["range"] == rng and r["order_id"] == "road-0"])
        pf = os.path.join(cp, "fills.json")
        with open(pf, encoding="utf-8") as fh:
            body = json.load(fh)
        for x in body["data"]:
            if x["range"] == rng and x["order_id"] == "road-0":
                x["liquidity"] = "taker"
        with open(pf, "w", encoding="utf-8") as fh:
            json.dump(body, fh)
        _refresh(cp)
        f = _failures(cp, FLAT)
        assert any(x["check"] == "vii" and "maker でない" in x["reason"] and rng in x["row"] for x in f), f


# ================================================================ 直すもの 8: 約定しなかった記録(批評家 問 4)
def test_fix8_exit_that_never_filled_fails(tmp_path, monkeypatch):
    # 試験の中だけ取引所の模型を差し替え、決済 road-1 を一度も当てない(批評家の試し)。FLAT で決済の値段 5,000,000 は毎足の
    # 範囲の内なので、楽観側は建ての足(0:04)で、悲観側は足 5 本目(0:05)で約定していたはず。前は検査の失敗なし
    orig_t2, orig_feed = SimVenue._tier2_bar, SimVenue._feed_children

    def broken(self, ev, start, t, out):
        keep = {k: v for k, v in self._live.items() if k == "road-1"}
        for k in keep:
            self._live.pop(k)
        try:
            orig_t2(self, ev, start, t, out)
        finally:
            self._live.update(keep)

    def broken_feed(self, parent, t, out):
        bar, self._bar = self._bar, None
        try:
            orig_feed(self, parent, t, out)
        finally:
            self._bar = bar
    monkeypatch.setattr(SimVenue, "_tier2_bar", broken)
    monkeypatch.setattr(SimVenue, "_feed_children", broken_feed)
    _, store = _run(tmp_path, FLAT, WITH_EXIT)
    assert [(r["range"], r["order_id"], r["state"]) for r in _table(store, "orders")] == [
        ("optimistic", "road-0", "FILLED"), ("optimistic", "road-1", "OPEN"),
        ("pessimistic", "road-0", "FILLED"), ("pessimistic", "road-1", "OPEN")]
    f = check_outputs(store, _bars(FLAT)).failures
    assert {x["check"] for x in f} == {"vii"} and len(f) == 2, f
    opt = next(x for x in f if "optimistic" in x["row"])
    pes = next(x for x in f if "pessimistic" in x["row"])
    assert "建てが約定した足(足の JSON の 4 本目(始まり 2023-11-14T22:17:00Z" in opt["reason"], opt
    assert "足の JSON の 5 本目(始まり 2023-11-14T22:18:00Z" in pes["reason"] and "約定していない" in pes["reason"], pes


def test_fix8_entry_that_should_have_filled_and_was_canceled_fails(tmp_path):
    # 置き直す close(受け入れの場面 5)の記録で、取り消された 0:05 の close(5,010,000)を、範囲の内に入る値段(5,000,000)に
    # 書き換える(送った値段も、指紋も合わせる)。足 6 本目 [0:05, 0:06) の範囲の内なのに約定せず 0:06 に取り消された記録 → (vii)
    moving = {"mode": "moving_close", "quote_ccy": "JPY", "levels": 1, "open_bar": 3,
              "lines": {"5": 5_010_000.0, "6": 5_005_000.0, "7": 5_000_000.0}}
    run_dir, store = _run(tmp_path, FLAT, moving)
    assert check_outputs(store, _bars(FLAT)).failures == []
    cp = _copy(run_dir, tmp_path, "moving")

    def fn(rs):
        r = next(r for r in rs if r["range"] == "pessimistic" and r["order_id"] == "road-1")
        assert (r["state"], r["canceled_t_ns"]) == ("CANCELED", _at(6))
        r.update(limit_px="5000000.0", sent_limit_px="5000000.0")
    _edit_table(cp, "orders", fn)
    _refresh(cp)
    f = _failures(cp, FLAT)
    assert any(x["check"] == "vii" and "road-1" in x["row"] and "足の JSON の 6 本目" in x["reason"]
               and "約定していない" in x["reason"] for x in f), f


# ================================================================ 直すもの 9・10: 足の番号と足の長さ(批評家 問 4)
def test_fix9_messages_count_bars_from_one_with_times(tmp_path):
    # 受け入れの場面 3 の検査の文: 足 4 本目の安値を指値まで下げた足を渡すと、「足の JSON の 4 本目(始まり 22:17)」と書く
    rows = _rows(WALK)
    px = 5_001_000.0  # 足 4 本目の安値 5,001,943.03 より下
    _, store = _run(tmp_path, WALK, dict(ENTRY, levels=1, limit_px=px))
    assert check_outputs(store, _bars(WALK)).failures == []
    bars = _bars(WALK)
    bars[3]["low"] = px - 1.0
    f = check_outputs(store, bars).failures
    assert f and all(x["check"] == "vii" for x in f), f
    assert all("足の JSON の 4 本目(始まり 2023-11-14T22:17:00Z・閉じた時刻 2023-11-14T22:18:00Z)" in x["reason"] for x in f), f
    assert rows[3]["low"] > px


def test_fix10_five_minute_bars_read_from_the_record(tmp_path):
    # 5 分足(step_ns = 300 秒、始まり T5 = 2023-11-14T22:15:00Z は 5 分の区切り)。足 3 本目は T5 + 15 分に閉じ、その終値
    # 5,000,000 の買いは足 4 本目 [T5 + 15 分, T5 + 20 分) で T5 + 20 分に約定。足の長さは record.json から読む
    # (前は 1 分の決め打ちで、(iv) が「閉じた 1 分足が無い」と落としていた)
    t5 = T0 + M
    gen = _gen(step_ns=5 * M, start_ns=t5)
    _, store = _run(tmp_path, gen, ENTRY)
    assert check_outputs(store, _bars(gen)).failures == []
    for s in SIDES:
        assert [x["t_ns"] for x in _of(_table(store, "fills"), s)] == [str(t5 + 20 * M)]
    # 足の JSON の 4 本目を抜くと、5 分の足で検査した文になる(閉じた時刻 22:35 の足の始まりは 22:30)
    bars = [b for k, b in enumerate(_bars(gen)) if k != 3]
    f = check_outputs(store, bars).failures
    assert any(x["check"] == "iv" and "閉じた足(始まり 2023-11-14T22:30:00Z)" in x["reason"] for x in f), f


def test_fix10_legacy_bar_length_from_bars_file():
    assert bar_ns_from_bars([{"t_ns": T0 + k * 5 * M} for k in range(4)]) == 5 * M
    assert bar_ns_from_bars([{"t_ns": T0}]) is None


# ================================================================ 直すもの 11: 逆指値(批評家 問 6 (c))
@pytest.mark.parametrize("spec", [OPT, PES])
def test_fix11_stop_under_bar_rule_stops_the_run(spec):
    v = _venue(spec, VenueRules(market_ref="next_bar_open"))
    with pytest.raises(FillSpecError, match="stop"):
        v.on_order(OrderRequest(side="sell", order_type="stop", size=1.0, trigger_price=99.0, client_order_id="s"), 1 * M)
    # bar_rule を選ばない走らせは今のまま受ける
    w = _venue(FillSpec(tier=2), VenueRules(market_ref="next_bar_open"))
    assert [type(r).__name__ for r in w.on_order(OrderRequest(side="sell", order_type="stop", size=1.0, trigger_price=99.0,
                                                              client_order_id="s"), 1 * M)] == ["Ack"]


# ================================================================ 1 周目の場面と変えないもの
def test_loss_side_exit_on_entry_bar_kept(tmp_path):
    # オーナーの決定 L-783「今の作り」: 楽観側は損の側の決済も建ての足で約定させる。買い 100 に売り 99.5(足 t+1 の範囲の内)
    v = _venue(OPT, VenueRules(market_ref="next_bar_open"))
    v.on_market_event(_bar(0, 100.0, 101.0, 99.0, 100.0), 1 * M)
    v.on_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=100.0, client_order_id="e"), 1 * M)
    v.on_order(OrderRequest(side="sell", order_type="limit", size=1.0, price=99.5, client_order_id="x", reduce_only=True,
                            extra=((ATTACHED_KEY, "e"),)), 1 * M)
    assert [r for r in _rep(v.on_market_event(_bar(1, 100.5, 101.0, 99.5, 100.0), 2 * M)) if r[0] == "Fill"] == [
        ("Fill", "e", 100.0, None), ("Fill", "x", 99.5, None)]
    assert v.fill_marks == [("range_open", "same_bar", "range"), ("range_open", "same_bar", "entry_bar")]

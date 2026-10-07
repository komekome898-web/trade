"""直し B1 の受け入れの試験: 1 段目(根)の約定値段からの距離で値段が決まる段(L-816「1.a」・L-817)。

リードが書いた(委任文 docs/DISCUSSIONS/2026-10-06_held_batches/matilda_step0/DELEGATION_anchor_b1.md)。
作業者は試験を変えずに通す(変えたいときは問いとして返す)。期待の値は全部、足の値から手で計算した(各場面の注)。

オーナーの逐語:
- L-815「**1段目を基準にそれ以降の足をステップ毎の値段で約定させないとナンピンにならない**」
- L-816「**1.a**」(1 段目は始値で約定、2 段目からはその約定値段を基準に step ずつ。値段が届いたときだけ約定)
- L-817「**問い 2(B-1) a**」(1 段目が約定した足の中で 2 段目以降を約定させるのは、良い側・悪い側の両方)

口(この試験が決める):
- `RoadStrategy.place(side, "limit", None, levels, signal, size_ref=根, anchor=根, offset=距離)` と
  `RoadStrategy.place_with_exit(side, None, levels, signal, exit_price, size_ref=根, anchor=根, offset=距離)`。
  根 = 同じ売買の、place で出した指値の建ての注文(段・決済・量 0 の行は根にしない)。値段は渡さない(None)。量は size_ref で写す。
  距離は 0 でない有限の数で、買いは負・売りは正(根より不利でない向き = ナンピンの向き)。
- 段は根が最初に約定するまで何も効かない。根の最初の約定値段 F で、段の値段 = 刻みに切り捨てた F + 距離(売りも買いも
  切り捨て。L-783)。その時刻から待ち、根が約定した足でも、段の値段が足の範囲の内(安値 ≦ 値段 ≦ 高値)なら段の値段で約定する
  (良い側・悪い側の両方。約定の印 fill_case = "anchor_bar")。次の足からはふつうの指値(range_open)。
- 根が何も約定せずに閉じたら、段は取引所が閉じる(理由 "anchor_root_closed_unfilled")。
- 注文の表に列 anchored_to(根の番号)・anchor_offset(距離)・anchor_px(段の値段。根の最初の約定の知らせで書く。
  それまでに閉じた段と、根を持たない注文は空)を足す。段の limit_px・sent_limit_px は空。
- 検査 `check_outputs` は、段の値段を根の最初の約定から計算し直して anchor_px と比べ、段の約定を段の値段の決まりで確かめる((vii))。
"""
from __future__ import annotations

import importlib.util
import math
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_matilda_v37_spec as S  # noqa: E402  1 本目の受け入れの試験の場面の道具
from bot.bt.road import check_outputs  # noqa: E402
from bot.bt.road.strategy import RoadStrategyError  # noqa: E402
from bot.bt.road.tables import ROAD_DIR, SCHEMA  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = "bot.strategy.road_anchor_test"
SIDES = S.SIDES
t = S.t
H = (7000000, 7000000, 7000000, 7000000)  # 足 1・2 本目(動かない)


@pytest.fixture()
def anchor_module():
    spec = importlib.util.spec_from_file_location(MODULE, os.path.join(HERE, "road_anchor_strategy.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[MODULE] = mod
    spec.loader.exec_module(mod)
    yield mod
    sys.modules.pop(MODULE, None)


def run(tmp_path, rows, params):
    return S.run(tmp_path, S.seq([H, H] + rows), dict(params, open_bar=2), module=MODULE)


COLS = ("order_id", "side", "limit_px", "qty", "anchored_to", "anchor_offset", "anchor_px", "state")


def orders(res, s, cols=COLS):
    return [tuple(r[c] for c in cols) for r in res["orders"][s]]


def fills(res, s):
    return [(r["order_id"], r["t_ns"], r["px"], r["fill_case"]) for r in res["fills"][s]]


BUY = dict(side="buy", root_px=7000050.0, levels=2)
# 足 3 本目: 始値 6,999,800・高値 6,999,850・安値 6,999,700(L-816 の例の足)
B3 = (6999800, 6999850, 6999700, 6999750)


# ================================================================ V1 段の約定(L-816 の例)
def test_v1_levels_fill_from_root_fill_price(tmp_path, anchor_module):
    # 足 2 本目の終わりに 根 = 買い 7,000,050(量 0.009)、段 = 根 −100・根 −200。
    # 足 3: 根 7,000,050 > 高値 6,999,850 → 始値 6,999,800 で約定(open)。F = 6,999,800。
    #   段 1 = 6,999,700: 安値 6,999,700 ≦ 6,999,700 ≦ 高値 → 同じ足で 6,999,700(anchor_bar、両側)。
    #   段 2 = 6,999,600 < 安値 6,999,700 → 約定しない。
    # 足 4(安値 6,999,550): 段 2 6,999,600 は範囲の内 → 6,999,600(range)
    res = run(tmp_path, [B3, (6999750, 6999800, 6999550, 6999600), (6999600, 6999600, 6999600, 6999600)],
              dict(BUY, children=[{"offset": -100.0}, {"offset": -200.0}]))
    S.check_ok(res)
    for s in SIDES:
        assert orders(res, s) == [("road-0", "buy", "7000050.0", "0.009", "", "", "", "FILLED"),
                                  ("road-1", "buy", "", "0.009", "road-0", "-100.0", "6999700.0", "FILLED"),
                                  ("road-2", "buy", "", "0.009", "road-0", "-200.0", "6999600.0", "FILLED")]
        assert fills(res, s) == [("road-0", t(3), "6999800.0", "open"), ("road-1", t(3), "6999700.0", "anchor_bar"),
                                 ("road-2", t(4), "6999600.0", "range")]
        assert [r["size_px_source"] for r in res["orders"][s]] == ["指値", "取引の最初の段 road-0",
                                                                    "取引の最初の段 road-0"]


def test_v1_root_filled_in_range_anchors_on_its_limit(tmp_path, anchor_module):
    # 足 3 = (7,000,100, 7,000,150, 6,999,900, 6,999,950): 根 7,000,050 は範囲の内 → 7,000,050(range)。F = 7,000,050。
    #   段 = 6,999,950 ≧ 安値 6,999,900 → 同じ足で 6,999,950(anchor_bar)
    res = run(tmp_path, [(7000100, 7000150, 6999900, 6999950)], dict(BUY, children=[{"offset": -100.0}]))
    S.check_ok(res)
    for s in SIDES:
        assert fills(res, s) == [("road-0", t(3), "7000050.0", "range"), ("road-1", t(3), "6999950.0", "anchor_bar")]
        assert orders(res, s)[1][6] == "6999950.0"


# ================================================================ V2 刻みの切り捨て(売りも買いも)
def test_v2_buy_level_floored(tmp_path, anchor_module):
    # 段 = F 6,999,800 − 100.5 = 6,999,699.5 → 切り捨て 6,999,699。足 3 の安値 6,999,700 > 6,999,699 → 足 3 では約定しない
    #   (切り上げて 6,999,700 にすると足 3 で約定する)。足 4(安値 6,999,550)で 6,999,699(range)
    res = run(tmp_path, [B3, (6999750, 6999800, 6999550, 6999600)], dict(BUY, children=[{"offset": -100.5}]))
    S.check_ok(res)
    for s in SIDES:
        assert orders(res, s)[1][5:7] == ("-100.5", "6999699.0")
        assert fills(res, s) == [("road-0", t(3), "6999800.0", "open"), ("road-1", t(4), "6999699.0", "range")]


def test_v2_sell_level_floored(tmp_path, anchor_module):
    # 売り: 根 = 売り 6,999,950(量 0.01)。足 3 = (7,000,200, 7,000,300, 7,000,150, 7,000,250): 根 < 安値 → 始値 7,000,200(open)。
    #   段 = 7,000,200 + 100.5 = 7,000,300.5 → 切り捨て 7,000,300 ≦ 高値 7,000,300 → 同じ足で 7,000,300(anchor_bar)
    #   (切り上げて 7,000,301 にすると約定しない)
    res = run(tmp_path, [(7000200, 7000300, 7000150, 7000250)],
              dict(side="sell", root_px=6999950.0, levels=2, children=[{"offset": 100.5}]))
    S.check_ok(res)
    for s in SIDES:
        assert orders(res, s)[1][1:7] == ("sell", "", "0.01", "road-0", "100.5", "7000300.0")
        assert fills(res, s) == [("road-0", t(3), "7000200.0", "open"), ("road-1", t(3), "7000300.0", "anchor_bar")]


# ================================================================ V3 根が閉じる・段を取り消す・後から出す
UP = (7000200, 7000300, 7000100, 7000200)  # 根 7,000,050 < 安値 → 根は約定しない


def test_v3_root_closed_unfilled_closes_levels(tmp_path, anchor_module):
    # 足 3 で根は約定しない。足 3 の終わりに根を取り消す → 段は取引所が閉じる(理由 anchor_root_closed_unfilled、同じ時刻)
    res = run(tmp_path, [UP, UP], dict(BUY, children=[{"offset": -100.0}], cancel_root_bar=3))
    S.check_ok(res)
    for s in SIDES:
        rows = res["orders"][s]
        assert (rows[0]["state"], rows[0]["close_kind"]) == ("CANCELED", "cancel")
        assert [(r["state"], r["close_kind"], r["close_reason"], r["closed_venue_t_ns"], r["anchor_px"])
                for r in rows[1:]] == [("CANCELED", "venue", "anchor_root_closed_unfilled", t(3), "")]
        assert fills(res, s) == []


def test_v3_level_canceled_before_root_fills(tmp_path, anchor_module):
    # 足 3 の終わりに段を取り消す(根はまだ約定していない)。足 4 = B3 で根は始値 6,999,800 で約定。段は約定しない、anchor_px は空
    res = run(tmp_path, [UP, B3], dict(BUY, children=[{"offset": -100.0}], cancel_child_bar=3))
    S.check_ok(res)
    for s in SIDES:
        assert orders(res, s)[1][6:] == ("", "CANCELED")
        assert fills(res, s) == [("road-0", t(4), "6999800.0", "open")]


def test_v3_level_after_root_filled_refused(tmp_path, anchor_module):
    # 根が約定した後(足 4 の終わり)に根を基準にした段を出すと止める(段は根と同じ判定で出す。この委任では扱わない)
    with pytest.raises(RoadStrategyError):
        run(tmp_path, [B3, B3], dict(BUY, children=[], late_child_bar=4, late_offset=-100.0))


# ================================================================ V4 段に付けた決済
def test_v4_exit_attached_to_level(tmp_path, anchor_module):
    # 段 = 根 −100(6,999,700)に決済の売り 6,999,800 を付ける(road-2、attached_to = road-1)。
    # 足 3: 根 6,999,800(open)→ 段 6,999,700(anchor_bar)→ 段の決済が有効になる。
    #   良い側(same_bar): 6,999,800 は足 3 の範囲の内 → 足 3 で 6,999,800(entry_bar)。
    #   悪い側(next_bar): 足 4 = (6,999,750, 6,999,850, 6,999,700, 6,999,800) の範囲の内 → 足 4 で 6,999,800(range)
    res = run(tmp_path, [B3, (6999750, 6999850, 6999700, 6999800), (6999800, 6999800, 6999800, 6999800)],
              dict(BUY, children=[{"offset": -100.0, "exit_px": 6999800.0}]))
    S.check_ok(res)
    for s in SIDES:
        rows = res["orders"][s]
        assert [(r["order_id"], r["exit_kind"], r["attached_to"], r["anchored_to"]) for r in rows] == [
            ("road-0", "", "", ""), ("road-1", "", "", "road-0"), ("road-2", "with_entry", "road-1", "")]
    assert fills(res, "optimistic")[2] == ("road-2", t(3), "6999800.0", "entry_bar")
    assert fills(res, "pessimistic")[2] == ("road-2", t(4), "6999800.0", "range")


# ================================================================ V5 口の誤りは止める
def _root_then(fn):
    def act(s):
        s.signal_start("s1", "試験", "long", {})
        root = s.place("buy", "limit", 7000050.0, 2, "s1")
        fn(s, root)
    return act


BAD = [
    ("size_ref が無い", lambda s, r: s.place("buy", "limit", None, 2, "s1", anchor=r, offset=-100.0)),
    ("値段を渡す", lambda s, r: s.place("buy", "limit", 6999950.0, 2, "s1", size_ref=r, anchor=r, offset=-100.0)),
    ("成行", lambda s, r: s.place("buy", "market", None, 2, "s1", size_ref=r, anchor=r, offset=-100.0)),
    ("知らない根", lambda s, r: s.place("buy", "limit", None, 2, "s1", size_ref=r, anchor="road-99", offset=-100.0)),
    ("根が決済の行", lambda s, r: s.place("buy", "limit", None, 2, "s1", size_ref=r, offset=-100.0,
                                       anchor=s.place_with_exit("buy", 6999000.0, 2, "s1", 7001000.0, size_ref=r)[1])),
    ("根が段", lambda s, r: s.place("buy", "limit", None, 2, "s1", size_ref=r, offset=-200.0,
                                  anchor=s.place("buy", "limit", None, 2, "s1", size_ref=r, anchor=r, offset=-100.0))),
    ("売買が根と違う", lambda s, r: s.place("sell", "limit", None, 2, "s1", size_ref=r, anchor=r, offset=100.0)),
    ("買いで距離が正", lambda s, r: s.place("buy", "limit", None, 2, "s1", size_ref=r, anchor=r, offset=100.0)),
    ("距離 0", lambda s, r: s.place("buy", "limit", None, 2, "s1", size_ref=r, anchor=r, offset=0.0)),
    ("距離が有限でない", lambda s, r: s.place("buy", "limit", None, 2, "s1", size_ref=r, anchor=r, offset=math.nan)),
    ("距離が無い", lambda s, r: s.place("buy", "limit", None, 2, "s1", size_ref=r, anchor=r)),
    ("距離だけ", lambda s, r: s.place("buy", "limit", 6999950.0, 2, "s1", size_ref=r, offset=-100.0)),
    ("決済つきで値段を渡す", lambda s, r: s.place_with_exit("buy", 6999950.0, 2, "s1", 7000100.0, size_ref=r, anchor=r,
                                                       offset=-100.0)),
]


@pytest.mark.parametrize("name,fn", BAD, ids=[b[0] for b in BAD])
def test_v5_bad_anchor_refused(name, fn):
    with pytest.raises(RoadStrategyError):
        S._probe(_root_then(fn))


def test_v5_good_anchor_sends_no_price():
    # 正しい段は値段なし(取引所が根の約定で決める)で、根と距離を取引所に渡す
    s = S._Probe(_root_then(lambda s, r: s.place("buy", "limit", None, 2, "s1", size_ref=r, anchor=r, offset=-100.0)))
    s.set_price_tick(1.0)
    ctx = S._Ctx()
    s.on_event(S._bar(), ctx)
    child = ctx.sent[1]
    assert child.order_type == "limit" and child.price is None
    assert dict(child.extra) == {"anchored_to": "road-0", "anchor_offset": -100.0}


# ================================================================ V6 表の列と検査
def test_v6_columns():
    cols = [c[0] for c in SCHEMA["tables"]["orders"]["columns"]]
    for c in ("anchored_to", "anchor_offset", "anchor_px"):
        assert c in cols


TAMPER = [
    ("段の値段", "orders", "road-1", lambda r: r.update(anchor_px="6999701.0")),
    ("根の番号", "orders", "road-1", lambda r: r.update(anchored_to="road-9")),
    ("距離", "orders", "road-1", lambda r: r.update(anchor_offset="-99.0")),
    ("段の約定の値段", "fills", "road-1", lambda r: r.update(px="6999701.0")),
]


@pytest.mark.parametrize("label,table,oid,edit", TAMPER, ids=[x[0] for x in TAMPER])
def test_v6_tampering_fails_check(tmp_path, anchor_module, label, table, oid, edit):
    from bot.bt.road.tables import read_csv as rc
    res = run(tmp_path, [B3, (6999750, 6999800, 6999550, 6999600)], dict(BUY, children=[{"offset": -100.0}]))
    S.check_ok(res)
    d = str(tmp_path / "copy")
    shutil.copytree(os.path.dirname(res["store"]), d)
    p2 = os.path.join(d, ROAD_DIR, SCHEMA["tables"][table]["file"])
    h2, r2 = rc(p2, table)
    for r in r2:
        if r["range"] == "pessimistic" and r["order_id"] == oid:
            edit(r)
    S._rewrite(p2, h2, r2, d)
    f = check_outputs(os.path.join(d, ROAD_DIR), res["bars"]).failures
    assert f, label

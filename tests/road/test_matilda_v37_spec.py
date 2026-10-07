"""マチルダ(v37)の道の戦略と、取引の中の段の量をそろえる口(L-781)の受け入れの試験。

リードが書いた(委任文 docs/DISCUSSIONS/2026-10-06_held_batches/matilda_step0/DELEGATION_matilda_v37.md)。
作業者は試験を変えずに通す(変えたいときは問いとして返す)。試験で決まらない振る舞いは、委任文の「決めてよいこと」の
範囲で作業者が決めてよい。期待の値は全部、足の値から手で計算した(各場面の注に計算を書いた)。

オーナーの逐語(写し方の決まりの出所。委任文の「写し方の決まり」の節に行ごとの出所がある):
- L-776「**全ての変数は固定値でなく調整可能な値で、それはバックテストで探る族の種類と同義です。modeの切り替えとかもあったと思う。**」
- L-781「**1 段の量は建てた時の値段で決まるが、段毎の量は建玉を持った時点での量と同じにする。**」
- L-779「**注文は計算した値そのもので行ってください。**」/ L-783「**間違えそうやから小数点以下は切り捨ててください**」
- L-782「**1. 利確は中央値から exit_setting × ボラ 離れたところ**」/ L-783「**問い1(a)**」
- L-784「**実装ミスなので割る数は分子を合わせてください。他の計算も合わせてください。**」「**売りと買いをそろえる**」
- L-788「**breakexitsizeはロット数上限に合わせる**」/ L-789「**あってる**」
- L-770「**建ての指値と一緒に決済の指値を出しておき**」/ L-774「**なんで次の段の指値が次の足になるの？**」

口(この試験が決める):
- 戦略: `src/bot/strategy/matilda_v37.py`。`pipeline_strategy(params, price_type)` が `MatildaV37`(`RoadStrategy` を継ぐ)を返す。
  `PARAM_KEYS`(引数の名前の組)・`V37_ORIGINAL`(原典の値の辞書)・純な関数 `entry_flag`・`exit_flag`・`exit_price` を持つ。
- 量の口: `RoadStrategy.place(..., size_ref=None)` と `RoadStrategy.place_with_exit(..., size_ref=None)`。size_ref に前に
  place(量の計算)で出した注文の番号を渡すと、その注文の量の計算の列(margin_jpy・use_ratio・levels・size_px・usdjpy・
  usdjpy_t_ns・qty_raw)と量を写し、size_px_source を「取引の最初の段 <番号>」にする。検査(`check_outputs` の (v))は
  その行を、写した元の行と比べる。
- 走らせ: 1 分足のファイル(tmp の根の下)・刻み 1 円・最小 0.001・market_ref next_bar_open・約定の決まり range_open
  (楽観側 same_bar・悲観側 next_bar)・遅れ 0・self_trade は宣言しない(自分の注文どうしが交差したら走らせが止まる)。
- 足 k 本目(1 から)は T0 + (k−1) 分に始まり、T0 + k 分に閉じる。t(k) = その閉じた時刻(ns の文字列)。
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone

import pytest

from bot.bt import pipeline as P
from bot.bt.core import BarEvent
from bot.bt.road import check_outputs
from bot.bt.road.strategy import RoadStrategy, RoadStrategyError
from bot.bt.road.tables import ROAD_DIR, SCHEMA, read_csv

HERE = os.path.dirname(os.path.abspath(__file__))
NS = 10**9
T0 = 1_699_999_800  # 2023-11-14T22:10:00Z(5 分の区切り。封印の境 2023-12-17T15:00Z より前)
SIDES = ("optimistic", "pessimistic")
ZERO = {"kind": "constant", "ns": 0}
SPEC = {"format": "csv", "header": True, "delimiter": ",", "compression": "none", "kind": "bar", "symbol": "FX_BTC_JPY",
        "asset": "crypto", "time": {"columns": ["start_ts"], "unit": "iso", "tz": "UTC"},
        "fields": {"open": "o", "high": "h", "low": "l", "close": "c", "volume": "vol"},
        "bar": {"interval_s": 60, "label": "start", "session": "24x7"}, "key": "start"}
FILL = {"optimistic": {"tier": 2, "bar_rule": "range_open", "attached_exit": "same_bar"},
        "pessimistic": {"tier": 2, "bar_rule": "range_open", "attached_exit": "next_bar"}}
SIZEREF_MODULE = "bot.strategy.road_sizeref_test"

try:
    from bot.strategy import matilda_v37 as M
except ImportError:  # 作る前
    M = None
need_m = pytest.mark.skipif(M is None, reason="戦略がまだ無い(作る前)")


def t(k: int) -> str:
    """足 k 本目(1 から、分の番号 k−1 に始まる)が閉じた時刻(ns の文字列)。"""
    return str((T0 + k * 60) * NS)


# ---------------------------------------------------------------- 走らせの土台
def _write_bars(root, bars):
    """bars: [(分の番号, 始値, 高値, 安値, 終値, 出来高)]。分の番号 m の足は T0 + m 分に始まる。"""
    os.makedirs(os.path.join(root, "backtest_data", "m"), exist_ok=True)
    lines = ["start_ts,o,h,l,c,vol"]
    for m, o, h, lo, c, v in bars:
        ts = datetime.fromtimestamp(T0 + m * 60, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        lines.append(f"{ts},{o},{h},{lo},{c},{v}")
    with open(os.path.join(root, "backtest_data", "m", "bars.csv"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(os.path.join(root, "prereg.md"), "w", encoding="utf-8") as fh:
        fh.write("# 試験\n")


def _plan(root, module, params, rules=None):
    # 抜けのある足(U9)を通すため、抜けの扱いを名指しする(走らせは名指しの無い抜けを止める。事前の批評 1 回目の問3)
    return P.plan_pipeline(
        root=str(root), datasets=[{"name": "b", "paths": ["backtest_data/m/bars.csv"], "spec": SPEC, "origin": "real",
                                   "resolve": {"gap": "accept"}}],
        instruments=[{"name": "FX_BTC_JPY", "price": "b", "with": [],
                      "product": {"symbol": "FX_BTC_JPY", "venue": "bitflyer", "tick": 1.0, "min_qty": 0.001,
                                  "qty_step": 0.001, "quote_ccy": "JPY", "margin": True},
                      "rules": rules or {"market_ref": "next_bar_open"}}],
        strategy={"kind": "module", "module": module, "factory": "pipeline_strategy", "params": params},
        fill=FILL, latency={"feed": ZERO, "order": ZERO, "cancel": ZERO, "notice": ZERO},
        costs={"maker_rate": 0, "taker_rate": 0, "spread": 0, "source": "試験: 0"},
        account={"currency": "JPY", "cash": 1e9, "leverage": 1, "mark": "last_trade", "liquidation": None,
                 "margin_check": "position_only"},
        purpose="研究", prereg="prereg.md")


def seq(rows):
    """[(始値, 高値, 安値, 終値[, 出来高])] → 分の番号 0 から並べた足。"""
    return [(i,) + tuple(r[:4]) + ((r[4] if len(r) > 4 else 1),) for i, r in enumerate(rows)]


def run(tmp_path, bars, params, module="bot.strategy.matilda_v37", rules=None):
    """走らせて、側ごとの表 {"orders": {側: [行]}, "fills": …, "signals": …, "trades": …} と置き場を返す。"""
    root = tmp_path / "root"
    _write_bars(str(root), bars)
    res = P.run_pipeline(_plan(root, module, params, rules), runs_dir=str(tmp_path / "runs"))
    store = os.path.join(res.run_dir, ROAD_DIR)
    out = {}
    for name in ("orders", "fills", "signals", "trades"):
        rows = read_csv(os.path.join(store, SCHEMA["tables"][name]["file"]), name)[1]
        out[name] = {s: [r for r in rows if r["range"] == s] for s in SIDES}
    out["store"] = store
    out["bars"] = [{"t_ns": (T0 + m * 60) * NS, "open": o, "high": h, "low": lo, "close": c} for m, o, h, lo, c, _ in bars]
    return out


def orders(res, side, cols=("order_id", "side", "order_type", "limit_px", "qty", "exit_kind", "attached_to",
                              "placed_t_ns", "state", "canceled_t_ns")):
    return [tuple(r[c] for c in cols) for r in res["orders"][side]]


def fills(res, side):
    return [(r["order_id"], r["t_ns"], r["px"]) for r in res["fills"][side]]


def signals(res, side):
    return [(r["signal_id"], r["kind"], r["direction"], r["start_t_ns"], r["end_t_ns"], r["end_reason"])
            for r in res["signals"][side]]


def signal_value(res, side, sid):
    return json.loads(next(r["value_json"] for r in res["signals"][side] if r["signal_id"] == sid))


def pnl(res, side):
    return [float(r["pnl_jpy"]) for r in res["trades"][side]]


def check_ok(res):
    f = check_outputs(res["store"], res["bars"]).failures
    assert f == [], f


# 小さな窓の引数(場面の計算が手でできる大きさ)。原典の値は V37_ORIGINAL。
BASE = dict(levels=2, auto_levels=False, foot=1, vola_count=3, range_count=3, alert_count=1000, range_setting=None,
            over_range_setting=None, vola_setting=None, entry_setting=2.0, exit_setting=1.0, break_delay=0,
            break_dist=0.5, break_len_mult=2, beard_ignore=None, step_setting=1.0, step_exit=1.0, b_signal=False)

A = (7000200, 7000300, 7000200, 7000300)  # 陽線(実体 100)
B = (7000300, 7000300, 7000200, 7000200)  # 陰線(実体 100)
WARM = [A, B, A, B, A, B]  # 慣らしの 6 本: 高値 7,000,300・安値 7,000,200・実体 100
B7 = (7000200, 7000200, 7000000, 7000000)  # 足 7 本目: 終値 7,000,000


def reflect(rows, m=14000500):
    """値段を 7,000,250 を軸に折り返す(売りの側の鏡の場面)。(始値, 高値, 安値, 終値) → (m−始値, m−安値, m−高値, m−終値)。"""
    return [(m - o, m - lo, m - h, m - c) + tuple(r[4:]) for r in rows for (o, h, lo, c) in [r[:4]]]


# ================================================================ U1 引数
@need_m
def test_u1_param_keys_and_original_values():
    # 引数は全部で 18。原典の値(v37:109-160 と オーナーの決め L-782・L-784・L-788)
    assert set(M.PARAM_KEYS) == set(BASE)
    o = M.V37_ORIGINAL
    assert set(o) == set(BASE)
    assert (o["levels"], o["auto_levels"], o["foot"], o["vola_count"], o["range_count"], o["alert_count"]) == \
        (7, True, 1, 40, 40, 20)
    assert o["range_setting"] == pytest.approx(150 / 600000) and o["over_range_setting"] == pytest.approx(100000 / 600000)
    assert o["vola_setting"] is None and o["beard_ignore"] == 1 and o["b_signal"] is True
    assert (o["entry_setting"], o["exit_setting"], o["break_delay"], o["break_dist"], o["break_len_mult"],
            o["step_setting"], o["step_exit"]) == (2, 0.8, 1, 0.5, 2, 1, 0.8)
    M.pipeline_strategy(dict(o), None)
    M.pipeline_strategy(dict(BASE), None)


BAD = [
    ("鍵が足りない", lambda p: p.pop("foot")),
    ("知らない鍵", lambda p: p.update(sizemin=0.01)),
    ("段数 0", lambda p: p.update(levels=0)),
    ("段数が整数でない", lambda p: p.update(levels=2.0)),
    ("foot 0", lambda p: p.update(foot=0)),
    ("vola_count 1(割る数 0)", lambda p: p.update(vola_count=1)),
    ("range_count 0", lambda p: p.update(range_count=0)),
    ("alert_count 0", lambda p: p.update(alert_count=0)),
    ("entry_setting ≦ exit_setting", lambda p: p.update(entry_setting=1.0, exit_setting=1.0)),
    ("exit_setting が負", lambda p: p.update(exit_setting=-0.1)),
    ("break_delay が負", lambda p: p.update(break_delay=-1)),
    ("break_len_mult 1", lambda p: p.update(break_len_mult=1)),
    ("break_dist 0", lambda p: p.update(break_dist=0)),
    ("step_setting 0", lambda p: p.update(step_setting=0)),
    ("step_exit 0(L-782 で外した)", lambda p: p.update(step_exit=0)),
    ("比の門が負", lambda p: p.update(range_setting=-0.0001)),
    ("beard_ignore 0", lambda p: p.update(beard_ignore=0)),
    ("真偽の引数に数", lambda p: p.update(b_signal=1)),
    ("NaN", lambda p: p.update(entry_setting=float("nan"))),
]


@need_m
@pytest.mark.parametrize("name,edit", BAD, ids=[b[0] for b in BAD])
def test_u1_bad_params_refused(name, edit):
    p = dict(BASE)
    edit(p)
    with pytest.raises((ValueError, TypeError, RoadStrategyError)):
        M.pipeline_strategy(p, None)


# ================================================================ U2 判定の表(純な関数。v37:991-1037 の写し、SFD・休む時間の枝は無い)
# entry_flag(break_flg, b_signal, flat, last, center, vola, width, entry_setting, range_setting, over_range_setting,
#            vola_setting) / 比の門は「値 × last」と比べる(L-779「その時の価格に合わせた」)
ENTRY_ROWS = [
    # (名前, 引数の差分, 期待)
    ("下に離れた → 買い", dict(last=6999799), 1),
    ("上に離れた → 売り", dict(last=7000201), -1),
    ("ちょうど線の上(買いの線)→ 0(v37:995 は厳しい <)", dict(last=6999800), 0),
    ("ちょうど線の上(売りの線)→ 0", dict(last=7000200), 0),
    ("幅の門が閉じる(幅 < 比 × last)", dict(last=6999799, range_setting=2e-5), 0),
    ("幅の門が開く", dict(last=6999799, range_setting=1e-5), 1),
    ("上の門が閉じる(幅 > 比 × last)", dict(last=6999799, over_range_setting=1e-5), 0),
    ("ボラの門が閉じる(ボラ ≦ 比 × last)", dict(last=6999799, vola_setting=2e-5), 0),
    ("ボラの門が開く", dict(last=6999799, vola_setting=1e-5), 1),
    ("ブレイク上・順行 → 買い", dict(break_flg=1, b_signal=1, last=7000000), 1),
    ("ブレイク上・逆行 2 回 → 0", dict(break_flg=1, b_signal=-1, last=7000000), 0),
    ("ブレイク上・b_signal 0・玉なし → 0(静観)", dict(break_flg=1, b_signal=0, last=7000000), 0),
    ("ブレイク上・b_signal 0・玉あり → 買い", dict(break_flg=1, b_signal=0, flat=False, last=7000000), 1),
    ("ブレイク下・順行 → 売り", dict(break_flg=-1, b_signal=-1, last=7000000), -1),
    ("ブレイク下・逆行 → 0", dict(break_flg=-1, b_signal=1, last=7000000), 0),
]
ENTRY_BASE = dict(break_flg=0, b_signal=0, flat=True, last=7000000, center=7000000, vola=100.0, width=100.0,
                  entry_setting=2.0, range_setting=None, over_range_setting=None, vola_setting=None)


@need_m
@pytest.mark.parametrize("name,diff,want", ENTRY_ROWS, ids=[r[0] for r in ENTRY_ROWS])
def test_u2_entry_flag_table(name, diff, want):
    assert M.entry_flag(**dict(ENTRY_BASE, **diff)) == want


# exit_flag(break_flg, b_signal, entry_flg, side, minutes_held, alert_count, avg, center, held_levels, order_count)
EXIT_ROWS = [
    ("買い玉・普通 → 1", dict(), 1),
    ("買い玉・反対の合図 → 3", dict(entry_flg=-1), 3),
    ("買い玉・2 倍の時間を越えた → 3", dict(minutes_held=41), 3),
    ("買い玉・ちょうど 2 倍 → 2(v37:1010 は厳しい >)", dict(minutes_held=40), 2),
    ("買い玉・時間を越えた → 2", dict(minutes_held=21), 2),
    ("買い玉・ちょうどの時間 → 1", dict(minutes_held=20), 1),
    ("買い玉・建値が中心より悪い → 2", dict(avg=7000001), 2),
    ("買い玉・建値 = 中心 → 1", dict(avg=7000000), 1),
    ("売り玉・普通 → 1", dict(side=-1, avg=7000100), 1),
    ("売り玉・反対の合図 → 3", dict(side=-1, avg=7000100, entry_flg=1), 3),
    ("売り玉・建値が中心より悪い → 2", dict(side=-1, avg=6999999), 2),
    ("ブレイク・反対の合図 → 3", dict(break_flg=1, b_signal=1, entry_flg=-1), 3),
    ("ブレイク・b_signal 0 → 1", dict(break_flg=1, b_signal=0, entry_flg=1), 1),
    ("ブレイク・逆行 2 回 → 2", dict(break_flg=1, b_signal=-1, entry_flg=0), 2),
    ("ブレイク・順行・段が上限 → 1", dict(break_flg=1, b_signal=1, entry_flg=1, held_levels=7), 1),
    ("ブレイク・順行・段が上限未満 → 0", dict(break_flg=1, b_signal=1, entry_flg=1, held_levels=6), 0),
    ("ブレイク中は時間で決済しない", dict(break_flg=1, b_signal=1, entry_flg=1, held_levels=6, minutes_held=1000), 0),
]
EXIT_BASE = dict(break_flg=0, b_signal=0, entry_flg=0, side=1, minutes_held=0, alert_count=20, avg=6999900,
                 center=7000000, held_levels=2, order_count=7)


@need_m
@pytest.mark.parametrize("name,diff,want", EXIT_ROWS, ids=[r[0] for r in EXIT_ROWS])
def test_u2_exit_flag_table(name, diff, want):
    assert M.exit_flag(**dict(EXIT_BASE, **diff)) == want


# exit_price(exit_flg, break_flg, side, center, vola, avg, held_levels, exit_setting, step_exit)
PRICE_ROWS = [
    ("レンジ・買い玉・1 → 中心 − exit × ボラ(L-782)", dict(), 7000000 - 80.0),
    ("レンジ・売り玉・1 → 中心 + exit × ボラ", dict(side=-1), 7000000 + 80.0),
    ("買い玉・2 → 中心 と 建値 + ボラ × step_exit ÷ 段数 の低い方(v37:912)・建値の側", dict(exit_flg=2), 6999950.0),
    ("買い玉・2・中心の側", dict(exit_flg=2, avg=6999990), 7000000),
    ("売り玉・2 → 高い方(v37:898)", dict(exit_flg=2, side=-1, avg=7000300), 7000250.0),
    ("売り玉・2・中心", dict(exit_flg=2, side=-1, avg=7000020), 7000000),
    ("ブレイク・買い玉・1 → 建値 + ボラ × step_exit ÷ 段数(L-789)", dict(break_flg=1, avg=7000000), 7000050.0),
    ("ブレイク・売り玉・1 → 建値 − …", dict(break_flg=-1, side=-1, avg=7000000), 6999950.0),
]
PRICE_BASE = dict(exit_flg=1, break_flg=0, side=1, center=7000000, vola=100.0, avg=6999900, held_levels=2,
                  exit_setting=0.8, step_exit=1.0)


@need_m
@pytest.mark.parametrize("name,diff,want", PRICE_ROWS, ids=[r[0] for r in PRICE_ROWS])
def test_u2_exit_price_table(name, diff, want):
    assert M.exit_price(**dict(PRICE_BASE, **diff)) == pytest.approx(want)


# ================================================================ U3 レンジの建て・決済・量(L-781)
R_BARS = seq(WARM + [B7, (7000000, 7000200, 6999900, 7000100), (7000100, 7000100, 6999900, 7000000)])


@need_m
def test_u3_range_entry_ladder_exit_and_size(tmp_path):
    # 足 7 本目の判定(指標は足 6 本目まで、last = 終値 7,000,000):
    #   ボラ = (|足 4| + |足 5|) ÷ (3 − 1) = 100、レンジ = 足 4〜6 の 7,000,200〜7,000,300、中心 = round(7,000,250.0) = 7,000,250
    #   買いの線 = 7,000,250 − 2 × 100 = 7,000,050 > 7,000,000 → 買いの合図 e1
    #   段 1 = 7,000,050(量 70,000 ÷ 7,000,050 = 0.0099999… → 0.009)、段 2 = 7,000,050 − 100 = 6,999,950
    #   (自分の値段なら 0.0100000… → 0.010。L-781 で段 1 の 0.009)。決済の指値 = 中心 − 1 × 100 = 7,000,150
    # 足 8 本目(6,999,900〜7,000,200): 段 1・段 2 が約定。楽観側は同じ足で決済の 2 つも約定(建玉 0)。
    # 悲観側の足 8 本目の判定(指標は足 7 本目まで): 中心 = round((7,000,300 + 7,000,000) ÷ 2) = 7,000,150、ボラ 100、
    #   合図 0(e1 の消失)。建値 7,000,000 ≦ 中心 → 決済の旗 1 → 7,000,150 − 100 = 7,000,050。決済が 2 つあるので
    #   2 つとも取り消し、1 つの close(0.018)に置き直す。足 9 本目で約定
    res = run(tmp_path, R_BARS, BASE)
    check_ok(res)
    head = [("road-0", "buy", "limit", "7000050.0", "0.009", "", "", t(7)),
            ("road-1", "sell", "limit", "7000150.0", "0.009", "with_entry", "road-0", t(7)),
            ("road-2", "buy", "limit", "6999950.0", "0.009", "", "", t(7)),
            ("road-3", "sell", "limit", "7000150.0", "0.009", "with_entry", "road-2", t(7))]
    opt = orders(res, "optimistic")
    assert [o[:8] for o in opt] == head
    assert [o[8] for o in opt] == ["FILLED"] * 4
    assert sorted(fills(res, "optimistic")) == sorted([("road-0", t(8), "7000050.0"), ("road-2", t(8), "6999950.0"),
                                                       ("road-1", t(8), "7000150.0"), ("road-3", t(8), "7000150.0")])
    assert sum(pnl(res, "optimistic")) == pytest.approx(2.7)  # 同じ足の約定の並びで取引の区切りが 1 つか 2 つかは決めない
    pes = orders(res, "pessimistic")
    assert [o[:8] for o in pes[:4]] == head
    assert [(o[0], o[8], o[9]) for o in pes[:4]] == [("road-0", "FILLED", ""), ("road-1", "CANCELED", t(8)),
                                                       ("road-2", "FILLED", ""), ("road-3", "CANCELED", t(8))]
    assert pes[4] == ("road-4", "sell", "limit", "7000050.0", "0.018", "close", "", t(8), "FILLED", "")
    assert len(pes) == 5
    assert sorted(fills(res, "pessimistic")) == sorted([("road-0", t(8), "7000050.0"), ("road-2", t(8), "6999950.0"),
                                                        ("road-4", t(9), "7000050.0")])
    assert sum(pnl(res, "pessimistic")) == pytest.approx(0.9)
    for s in SIDES:
        rows = {r["order_id"]: r for r in res["orders"][s]}
        assert (rows["road-0"]["size_px"], rows["road-0"]["size_px_source"], rows["road-0"]["levels"]) == \
            ("7000050.0", "指値", "2")
        assert (rows["road-2"]["size_px"], rows["road-2"]["size_px_source"], rows["road-2"]["levels"],
                rows["road-2"]["qty_raw"]) == ("7000050.0", "取引の最初の段 road-0", "2", rows["road-0"]["qty_raw"])
        assert rows["road-0"]["signal_id"] == rows["road-2"]["signal_id"] == "e1"
        assert signals(res, s) == [("e1", "建て", "long", t(7), t(8), "合図の条件が外れた")]
        v = signal_value(res, s, "e1")
        want = dict(close=7000000, center=7000250, vola=100, range_max=7000300, range_min=7000200, width=100,
                    lsp=7000050, ssp=7000450, lep=7000150, sep=7000350, break_flg=0, b_signal=0, expantion_flg=0,
                    levels=2)
        assert {k: v[k] for k in want} == pytest.approx(want)


@need_m
def test_u3_size_ref_tampering_fails_check(tmp_path):
    # 写した量・写した元の番号を書き換えると、検査 (v) が落とす
    import shutil
    from bot.bt.road.tables import read_csv as rc
    res = run(tmp_path, R_BARS, BASE)
    path = os.path.join(res["store"], SCHEMA["tables"]["orders"]["file"])
    head, rows = rc(path, "orders")
    for label, edit in (("量", lambda r: r.update(qty="0.01")),
                        ("元の番号", lambda r: r.update(size_px_source="取引の最初の段 road-9")),
                        ("元が決済", lambda r: r.update(size_px_source="取引の最初の段 road-1")),
                        ("写した値段", lambda r: r.update(size_px="6999950.0"))):
        d = str(tmp_path / f"copy-{label}")
        shutil.copytree(os.path.dirname(res["store"]), d)
        p2 = os.path.join(d, ROAD_DIR, SCHEMA["tables"]["orders"]["file"])
        h2, r2 = rc(p2, "orders")
        for r in r2:
            if r["range"] == "pessimistic" and r["order_id"] == "road-2":
                edit(r)
        _rewrite(p2, h2, r2, d)
        f = check_outputs(os.path.join(d, ROAD_DIR), res["bars"]).failures
        assert any(x["check"] == "v" for x in f), (label, f)


def _rewrite(path, head, rows, run_dir):
    """表を書き直し、repro.json の指紋を合わせる(書き換えた人が指紋も合わせた場合)。"""
    import csv
    import gzip
    import hashlib
    import io
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(head)
    for r in rows:
        w.writerow([r[c] for c in head])
    with open(path, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            gz.write(buf.getvalue().encode("utf-8"))
    rp = os.path.join(run_dir, "repro.json")
    if os.path.exists(rp):
        with open(rp, encoding="utf-8") as fh:
            body = json.load(fh)
        for k in body.get("sha256", {}):
            with open(os.path.join(run_dir, k), "rb") as fh:
                body["sha256"][k] = hashlib.sha256(fh.read()).hexdigest()
        with open(rp, "w", encoding="utf-8") as fh:
            json.dump(body, fh)


# ================================================================ U4 量の口(土台。L-781)
@pytest.fixture()
def sizeref_module():
    spec = importlib.util.spec_from_file_location(SIZEREF_MODULE, os.path.join(HERE, "road_sizeref_strategy.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[SIZEREF_MODULE] = mod
    spec.loader.exec_module(mod)
    yield mod
    sys.modules.pop(SIZEREF_MODULE, None)


FLAT7 = seq([(7000000, 7000000, 7000000, 7000000)] * 4)


def test_u4_size_ref_copies_first_level(tmp_path, sizeref_module):
    # 足 2 本目で 7,000,050(0.009)・6,999,950・6,999,000 の買い。2 つ目からは 1 つ目の量の計算の列を写す
    res = run(tmp_path, FLAT7, {"prices": [7000050.0, 6999950.0, 6999000.0], "levels": 2, "open_bar": 2},
              module=SIZEREF_MODULE)
    check_ok(res)
    for s in SIDES:
        rows = res["orders"][s]
        cols = ("margin_jpy", "use_ratio", "levels", "size_px", "usdjpy", "usdjpy_t_ns", "qty_raw", "qty", "qty_source")
        assert [r["limit_px"] for r in rows] == ["7000050.0", "6999950.0", "6999000.0"]
        assert [r["size_px_source"] for r in rows] == ["指値", "取引の最初の段 road-0", "取引の最初の段 road-0"]
        for r in rows[1:]:
            assert {c: r[c] for c in cols} == {c: rows[0][c] for c in cols}
        assert rows[0]["qty"] == "0.009"


class _Ctx:
    """place を呼ぶだけの小さな文脈(取引所に届けない)。"""

    def __init__(self):
        self.now_ns = 60 * NS
        self.sent = []

    def place_order(self, req):
        self.sent.append(req)

    def order(self, coid):
        return None

    def cancel_order(self, coid):
        pass


class _Probe(RoadStrategy):
    def __init__(self, action):
        super().__init__(quote_ccy="JPY")
        self.action = action

    def step(self, event, ctx):
        if isinstance(event, BarEvent):
            self.action(self)


def _bar():
    return BarEvent(received_time_ns=60 * NS, start_time_ns=0, open=7000000.0, high=7000000.0, low=7000000.0,
                    close=7000000.0, volume=1.0)


def _probe(action):
    s = _Probe(action)
    s.set_price_tick(1.0)
    s.on_event(_bar(), _Ctx())
    return s


def _root_then(fn):
    def act(s):
        s.signal_start("s1", "試験", "long", {})
        root = s.place("buy", "limit", 7000050.0, 2, "s1")
        fn(s, root)
    return act


REF_BAD = [
    ("知らない番号", lambda s, root: s.place("buy", "limit", 6999950.0, 2, "s1", size_ref="road-99")),
    ("段数が違う", lambda s, root: s.place("buy", "limit", 6999950.0, 3, "s1", size_ref=root)),
    ("元が写した行", lambda s, root: s.place("buy", "limit", 6999000.0, 2, "s1",
                                         size_ref=s.place("buy", "limit", 6999950.0, 2, "s1", size_ref=root))),
    ("元が決済の行", lambda s, root: s.place("buy", "limit", 6999950.0, 2, "s1",
                                         size_ref=s.place_with_exit("buy", 6999900.0, 2, "s1", 7000100.0)[1])),
    ("成行に付ける", lambda s, root: s.place("buy", "market", None, 2, "s1", size_ref=root)),
]


@pytest.mark.parametrize("name,fn", REF_BAD, ids=[b[0] for b in REF_BAD])
def test_u4_size_ref_refused(name, fn):
    with pytest.raises(RoadStrategyError):
        _probe(_root_then(fn))


def test_u4_place_with_exit_size_ref():
    # place_with_exit の建ても写す。決済の量は建ての量(写した量)
    got = {}

    def fn(s, root):
        got["ids"] = s.place_with_exit("buy", 6999950.0, 2, "s1", 7000150.0, size_ref=root)

    s = _probe(_root_then(fn))
    rec = {r["order_id"]: r for r in s.road_record()["orders"]}
    e, x = got["ids"]
    assert rec[e]["size_px_source"] == "取引の最初の段 road-0" and rec[e]["qty"] == rec["road-0"]["qty"] == "0.009"
    assert rec[x]["qty"] == "0.009" and rec[x]["attached_to"] == e


# ================================================================ U5 合図が無いとき・玉があるときの取り消し(L-784 売り買いをそろえる)
R2_BARS = WARM + [B7, (7000100, 7000100, 7000000, 7000000), (7000050, 7000050, 7000050, 7000050)]


@need_m
@pytest.mark.parametrize("mirror", [False, True], ids=["買い", "売り"])
def test_u5_ladder_kept_while_position_then_canceled_when_flat(tmp_path, mirror):
    # 足 8 本目: 段 1 だけ約定(買いの側: 7,000,050。段 2 の 6,999,950 は安値 7,000,000 より下)。
    # 足 8 本目の判定: 合図 0。玉があるので、残りの段(road-2)と その決済(road-3)は取り消さない(原典 v37:1092 の
    #   買いの側は玉があっても取り消していた。L-784 で売りにそろえる)。決済の旗 1 → 中心 7,000,150 − 100 = 7,000,050
    #   (売りの側は 7,000,350 + 100 = 7,000,450)。road-1 は玉 0 のときに出したので取り消して close に置き直す。
    # 足 9 本目: close が約定し建玉 0 → 足 9 本目の判定で残りの段を全部取り消す(v37:1047-1051)
    bars = seq(reflect(R2_BARS) if mirror else R2_BARS)
    res = run(tmp_path, bars, BASE)
    check_ok(res)
    if mirror:
        px = ("7000450.0", "7000350.0", "7000550.0", "7000350.0", "7000450.0")
        sd = ("sell", "buy", "sell", "buy", "buy")
    else:
        px = ("7000050.0", "7000150.0", "6999950.0", "7000150.0", "7000050.0")
        sd = ("buy", "sell", "buy", "sell", "sell")
    for s in SIDES:
        assert orders(res, s) == [
            ("road-0", sd[0], "limit", px[0], "0.009", "", "", t(7), "FILLED", ""),
            ("road-1", sd[1], "limit", px[1], "0.009", "with_entry", "road-0", t(7), "CANCELED", t(8)),
            ("road-2", sd[2], "limit", px[2], "0.009", "", "", t(7), "CANCELED", t(9)),
            ("road-3", sd[3], "limit", px[3], "0.009", "with_entry", "road-2", t(7), "CANCELED", t(9)),
            ("road-4", sd[4], "limit", px[4], "0.009", "close", "", t(8), "FILLED", "")]
        assert fills(res, s) == [("road-0", t(8), px[0]), ("road-4", t(9), px[4])]


@need_m
@pytest.mark.parametrize("mirror", [False, True], ids=["買い", "売り"])
def test_u5_flat_ladder_canceled_when_signal_off(tmp_path, mirror):
    # 足 8 本目は段 1 に届かない(買い: 安値 7,000,100 > 7,000,050 / 売り: 高値 7,000,400 < 7,000,450)。
    # 足 8 本目の判定: 合図 0・玉なし → 全部取り消す(買いでも売りでも同じ)。全部の取り消しは段の数えも空にする
    #   (v37:651-665 の cancel_allorders。事前の批評 1 回目の問3)ので、次の合図で段を出し直す:
    # 足 9 本目の判定(足 8 まで): 足 6〜8 の 7,000,000〜7,000,300 → 中心 7,000,150、ボラ (100 + 200) ÷ 2 = 150 →
    #   買いの線 6,999,850 > 終値 6,999,800 → e2。段 6,999,850(70,000 ÷ 6,999,850 → 0.01)・6,999,700、決済 7,000,000。
    #   売りの側は鏡: 段 7,000,650(→ 0.009)・7,000,800、決済 7,000,500
    rows = WARM + [B7, (7000100, 7000300, 7000100, 7000200), (7000200, 7000200, 6999800, 6999800)]
    res = run(tmp_path, seq(reflect(rows) if mirror else rows), BASE)
    check_ok(res)
    if mirror:
        new = [("road-4", "sell", "7000650.0", "0.009", ""), ("road-5", "buy", "7000500.0", "0.009", "with_entry"),
               ("road-6", "sell", "7000800.0", "0.009", ""), ("road-7", "buy", "7000500.0", "0.009", "with_entry")]
    else:
        new = [("road-4", "buy", "6999850.0", "0.01", ""), ("road-5", "sell", "7000000.0", "0.01", "with_entry"),
               ("road-6", "buy", "6999700.0", "0.01", ""), ("road-7", "sell", "7000000.0", "0.01", "with_entry")]
    for s in SIDES:
        got = orders(res, s)
        assert [(o[0], o[8], o[9]) for o in got[:4]] == [(f"road-{i}", "CANCELED", t(8)) for i in range(4)]
        assert [(o[0], o[1], o[3], o[4], o[5]) for o in got[4:]] == new
        assert {o[7] for o in got[4:]} == {t(9)}
        assert [x[:4] for x in signals(res, s)] == [("e1", "建て", "short" if mirror else "long", t(7)),
                                                    ("e2", "建て", "short" if mirror else "long", t(9))]
        assert fills(res, s) == []


# ================================================================ U6 利確の置き直しの向き(v37:913-921)
@need_m
def test_u6_exit_kept_when_new_price_is_further(tmp_path):
    # 足 8 本目(7,000,000〜7,000,500): 段 1 が約定。楽観側は同じ足で road-1(7,000,150)も約定 → 建玉 0 →
    #   足 8 本目の判定で残り(road-2・road-3)を取り消す。
    # 悲観側: 足 8 本目の判定で close 7,000,050(U5 と同じ)。足 9 本目の判定(指標は足 8 本目まで): レンジ 7,000,000〜
    #   7,000,500・中心 7,000,250・ボラ = (|足 6| + |足 7|) ÷ 2 = 150 → 新しい値段 7,000,100 は 7,000,050 より高い
    #   (売りの決済で、相場から遠ざかる向き)→ 置き直さない(v37:917-918 は相場に近づく向きだけ取り消す)
    rows = WARM + [B7, (7000100, 7000500, 7000000, 7000000), (7000000, 7000040, 7000000, 7000040)]
    res = run(tmp_path, seq(rows), BASE)
    check_ok(res)
    assert [(o[0], o[8], o[9]) for o in orders(res, "optimistic")] == [
        ("road-0", "FILLED", ""), ("road-1", "FILLED", ""), ("road-2", "CANCELED", t(8)), ("road-3", "CANCELED", t(8))]
    pes = orders(res, "pessimistic")
    assert [(o[0], o[3], o[5], o[7], o[8], o[9]) for o in pes] == [
        ("road-0", "7000050.0", "", t(7), "FILLED", ""),
        ("road-1", "7000150.0", "with_entry", t(7), "CANCELED", t(8)),
        ("road-2", "6999950.0", "", t(7), "OPEN", ""),
        ("road-3", "7000150.0", "with_entry", t(7), "OPEN", ""),
        ("road-4", "7000050.0", "close", t(8), "OPEN", "")]


# ================================================================ U7 時間の決済(緩めた利確と強制の成行。v37:1008-1026)
T_PARAMS = dict(BASE, levels=1, entry_setting=4.0, exit_setting=0.0, alert_count=2)
T_BARS = WARM + [(7000200, 7000200, 6999800, 6999800), (6999900, 6999900, 6999800, 6999800),
                 (6999800, 6999800, 6999700, 6999700), (6999700, 6999700, 6999600, 6999600),
                 (6999600, 6999600, 6999500, 6999500), (6999500, 6999500, 6999400, 6999400),
                 (6999400, 6999400, 6999300, 6999300), (6999300, 6999300, 6999300, 6999300)]


@need_m
def test_u7_time_exits(tmp_path):
    # 段数 1・entry 4・exit 0・alert_count 2 分。
    # 足 7: 中心 7,000,250・ボラ 100 → 買いの線 6,999,850 > 6,999,800 → 買い 6,999,850(140,000 ÷ 6,999,850 → 0.02)、
    #   決済 = 中心 − 0 = 7,000,250
    # 足 8: 約定(6,999,800〜6,999,900)。判定(足 7 まで): 中心 round((7,000,300 + 6,999,800) ÷ 2) = 7,000,050 → 決済の旗 1 →
    #   7,000,050。road-1 を取り消し close 7,000,050(road-2)。玉の向きが変わった時刻 = t(8)
    # 足 9: 判定(足 8 まで): 中心 7,000,050 → 同じ値段なので置き直さない
    # 足 10: 判定(足 9 まで): 中心 round((7,000,200 + 6,999,700) ÷ 2) = 6,999,950。経過 2 分(> 2 でない)・建値 6,999,850 ≦ 中心 →
    #   旗 1 → 6,999,950 < 7,000,050 → 置き直す(road-3)
    # 足 11: 経過 3 分 > 2 → 旗 2。中心 6,999,750、ボラ 100、x = 100 × 1 ÷ 1 → min(6,999,750, 6,999,950) = 6,999,750(road-4)
    # 足 12: 経過 4 分(> 4 でない)→ 旗 2。中心 6,999,650 → road-5
    # 足 13: 経過 5 分 > 4 → 旗 3 → 全部取り消して成行(flatten)。足 14 の始値 6,999,300 で約定
    res = run(tmp_path, seq(T_BARS), T_PARAMS)
    check_ok(res)
    for s in SIDES:
        got = [(o[0], o[1], o[2], o[3], o[4], o[5], o[7], o[8], o[9]) for o in orders(res, s)]
        assert got == [
            ("road-0", "buy", "limit", "6999850.0", "0.02", "", t(7), "FILLED", ""),
            ("road-1", "sell", "limit", "7000250.0", "0.02", "with_entry", t(7), "CANCELED", t(8)),
            ("road-2", "sell", "limit", "7000050.0", "0.02", "close", t(8), "CANCELED", t(10)),
            ("road-3", "sell", "limit", "6999950.0", "0.02", "close", t(10), "CANCELED", t(11)),
            ("road-4", "sell", "limit", "6999750.0", "0.02", "close", t(11), "CANCELED", t(12)),
            ("road-5", "sell", "limit", "6999650.0", "0.02", "close", t(12), "CANCELED", t(13)),
            ("road-6", "sell", "market", "", "0.02", "flatten", t(13), "FILLED", "")]
        assert [(f[0], f[2]) for f in fills(res, s)] == [("road-0", "6999850.0"), ("road-6", "6999300.0")]
        assert sum(pnl(res, s)) == pytest.approx(-11.0)
        assert signals(res, s) == [("e1", "建て", "long", t(7), t(8), "合図の条件が外れた")]


# ================================================================ U8 ブレイク(L-788・L-789、v37:930-966・512-534)
BRK_HEAD = [(7000500, 7000600, 7000500, 7000600), (7000600, 7000600, 7000500, 7000500),
            (7000500, 7000600, 7000500, 7000600), (7000500, 7000500, 7000400, 7000400),
            (7000400, 7000500, 7000400, 7000500), (7000500, 7000500, 7000400, 7000400),
            (7000500, 7000700, 7000500, 7000700, 3), (7000700, 7000800, 7000700, 7000800)]
BRK_PARAMS = dict(BASE, break_delay=1, b_signal=True)


@need_m
def test_u8_break_entries_and_exit(tmp_path):
    # 上のブレイクの線の列: 足 6 本目で、足 4〜6 の高値 7,000,500 ≠ 2 倍の長さ(足 1〜6)の高値 7,000,600 → 7,000,500 + 100 × 0.5
    #   = 7,000,550 を書き足す。
    # 足 7 の判定(足 6 まで): 線 = max(7,000,550, 7,000,600) = 7,000,600 < 終値 7,000,700 → 上のブレイク b1。b_signal 0・玉なし →
    #   建てない(静観)。足 7 を指標に入れる: 出来高 3 > 平均 (1 + 1) ÷ 2・陽線・ヒゲ 0 → b_signal = 1
    # 足 8 の判定(足 7 まで): ブレイク上・順行 → 買いの合図 e1。段 1 = 終値 7,000,800、段 2 = 7,000,800 − ボラ 100 = 7,000,700。
    #   段 1 だけなら持つ段 1 < 上限 2 → 決済の旗 0 → 決済を付けない。段 2 まで → 旗 1 → 建値 round(7,000,750) + 100 × 1 ÷ 2
    #   = 7,000,800 を段 2 に付ける
    # 足 9(7,000,650〜7,000,790): 段 1 は高値より上 → 始値 7,000,750、段 2 は 7,000,700。決済 7,000,800 は届かない。
    #   判定(足 8 まで): 持つ段 2 → 旗 1 → round(7,000,725) + ボラ 150 × 1 ÷ 2 = 7,000,800。決済が建玉の量と違う → close 0.018
    # 足 10: close が約定 → 建玉 0。判定(足 9 まで): まだブレイク中・順行・玉なし → 新しい段 7,000,850 と 7,000,850 − 150
    res = run(tmp_path, seq(BRK_HEAD + [(7000750, 7000790, 7000650, 7000650), (7000650, 7000850, 7000650, 7000850)]),
              BRK_PARAMS)
    check_ok(res)
    for s in SIDES:
        assert [(o[0], o[1], o[3], o[4], o[5], o[6], o[7], o[8], o[9]) for o in orders(res, s)] == [
            ("road-0", "buy", "7000800.0", "0.009", "", "", t(8), "FILLED", ""),
            ("road-1", "buy", "7000700.0", "0.009", "", "", t(8), "FILLED", ""),
            ("road-2", "sell", "7000800.0", "0.009", "with_entry", "road-1", t(8), "CANCELED", t(9)),
            ("road-3", "sell", "7000800.0", "0.018", "close", "", t(9), "FILLED", ""),
            ("road-4", "buy", "7000850.0", "0.009", "", "", t(10), "OPEN", ""),
            ("road-5", "buy", "7000700.0", "0.009", "", "", t(10), "OPEN", ""),
            ("road-6", "sell", "7000850.0", "0.009", "with_entry", "road-5", t(10), "OPEN", "")]
        rows = {r["order_id"]: r for r in res["orders"][s]}
        assert rows["road-1"]["size_px_source"] == "取引の最初の段 road-0"
        assert rows["road-5"]["size_px_source"] == "取引の最初の段 road-4"
        assert sorted(fills(res, s)) == sorted([("road-0", t(9), "7000750.0"), ("road-1", t(9), "7000700.0"),
                                                ("road-3", t(10), "7000800.0")])
        assert sum(pnl(res, s)) == pytest.approx(1.35)
        assert [x[:4] for x in signals(res, s)] == [("b1", "ブレイク", "up", t(7)), ("e1", "建て", "long", t(8))]
        assert signal_value(res, s, "e1")["b_signal"] == 1 and signal_value(res, s, "e1")["break_flg"] == 1


@need_m
def test_u8_break_switches(tmp_path):
    # b_signal を使わない: ブレイク中、玉なしでは建てない(ずっと静観)→ 注文 0、合図はブレイクだけ
    bars = seq(BRK_HEAD + [(7000750, 7000790, 7000650, 7000650)])
    res = run(tmp_path / "a", bars, dict(BRK_PARAMS, b_signal=False))
    check_ok(res)
    for s in SIDES:
        assert orders(res, s) == []
        assert [x[:4] for x in signals(res, s)] == [("b1", "ブレイク", "up", t(7))]
    # ブレイクを切る(break_delay 0): 足 7 は売りの線 7,000,450 + 200 = 7,000,650 < 7,000,700 → 売りの合図(レンジの逆張り)
    res = run(tmp_path / "b", bars, dict(BRK_PARAMS, break_delay=0))
    check_ok(res)
    for s in SIDES:
        assert [x[:4] for x in signals(res, s)][0] == ("e1", "建て", "short", t(7))
        assert all(x[1] != "ブレイク" for x in signals(res, s))
        assert orders(res, s)[0][:4] == ("road-0", "sell", "limit", "7000650.0")


@need_m
def test_u8_break_chase_when_flat(tmp_path):
    # 足 9(7,000,850〜7,001,000): 段 1(7,000,800)に届かない。判定(足 8 まで): ブレイク中・順行・玉なし・建ての指値が出ていて、
    #   今の 1 段目(終値 7,000,950)が出ている 1 段目(7,000,800)より上 → 全部取り消し(v37:851-853、v37:55
    #   「ノーポジ時に指値をなるべく約定させようと努力するように変更」)、7,000,950 と 7,000,950 − 150 に置き直す
    res = run(tmp_path, seq(BRK_HEAD + [(7000900, 7001000, 7000850, 7000950)]), BRK_PARAMS)
    check_ok(res)
    for s in SIDES:
        assert [(o[0], o[1], o[3], o[5], o[6], o[7], o[8], o[9]) for o in orders(res, s)] == [
            ("road-0", "buy", "7000800.0", "", "", t(8), "CANCELED", t(9)),
            ("road-1", "buy", "7000700.0", "", "", t(8), "CANCELED", t(9)),
            ("road-2", "sell", "7000800.0", "with_entry", "road-1", t(8), "CANCELED", t(9)),
            ("road-3", "buy", "7000950.0", "", "", t(9), "OPEN", ""),
            ("road-4", "buy", "7000800.0", "", "", t(9), "OPEN", ""),
            ("road-5", "sell", "7000950.0", "with_entry", "road-4", t(9), "OPEN", "")]
        rows = {r["order_id"]: r for r in res["orders"][s]}
        assert rows["road-4"]["size_px_source"] == "取引の最初の段 road-3"


@need_m
def test_u8_break_off_when_back_to_center(tmp_path):
    # 足 9 の終値 7,000,500 < 中心(足 8 まで: 足 6〜8 の 7,000,400〜7,000,800 → 7,000,600)→ ブレイクの解除(v37:952-966)。
    #   解除の前に建ての判定がある(v37:1084 の後に 1101)ので、足 9 の判定ではまだブレイク中・玉なしで、建ての段は
    #   足 8 のまま(段 1 の 7,000,800 は足 9 の範囲 7,000,500〜7,000,800 の内で約定)
    res = run(tmp_path, seq(BRK_HEAD + [(7000800, 7000800, 7000500, 7000500)]), BRK_PARAMS)
    check_ok(res)
    for s in SIDES:
        assert [x for x in signals(res, s) if x[0] == "b1"] == [("b1", "ブレイク", "up", t(7), t(9), "中心に戻った")]


# ================================================================ U9 足の束ね(foot)・欠け
UP5 = [(7000200 + 20 * i, 7000220 + 20 * i, 7000200 + 20 * i, 7000220 + 20 * i) for i in range(5)]
DOWN5 = [(7000300 - 20 * i, 7000300 - 20 * i, 7000280 - 20 * i, 7000280 - 20 * i) for i in range(5)]


@need_m
def test_u9_foot5_built_from_minutes_and_decided_every_minute(tmp_path):
    # foot 5: 1 分足 5 本ずつを UTC の 5 分の区切りで束ねる(始値 = 最初、高値 = 最大、安値 = 最小、終値 = 最後、出来高 = 和)。
    #   UP5 は 7,000,200 → 7,000,300 の陽線、DOWN5 は 7,000,300 → 7,000,200 の陰線 → 束ねた 6 本は WARM と同じ。
    # 判定は 1 分ごと。束ねた足が 6 本そろうのは 30 本目の後 → 31 本目(終値 7,000,000)で U3 と同じ合図と注文
    rows = (UP5 + DOWN5) * 3 + [B7]
    res = run(tmp_path, seq(rows), dict(BASE, foot=5))
    check_ok(res)
    for s in SIDES:
        assert [x[:4] for x in signals(res, s)] == [("e1", "建て", "long", t(31))]
        assert [(o[0], o[1], o[3], o[4], o[7]) for o in orders(res, s)] == [
            ("road-0", "buy", "7000050.0", "0.009", t(31)), ("road-1", "sell", "7000150.0", "0.009", t(31)),
            ("road-2", "buy", "6999950.0", "0.009", t(31)), ("road-3", "sell", "7000150.0", "0.009", t(31))]
        v = signal_value(res, s, "e1")
        assert (v["center"], v["vola"], v["range_max"], v["range_min"]) == (7000250, 100, 7000300, 7000200)


@need_m
def test_u9_foot5_missing_minute(tmp_path):
    # 5 本目の窓(分 20〜24)の最後の 1 分(分 24)が無い → その窓は 4 本で束ねる(始値 7,000,200・高値 7,000,280・終値 7,000,280)。
    #   窓の終わりの足が来ないので、次の窓の最初の足(分 25)が来たときに束ねて閉じる。
    # 31 本目の判定(足 6 本まで): ボラ = (|窓 4| 100 + |窓 5| 80) ÷ 2 = 90、中心 7,000,250 → 買いの線 7,000,070、
    #   段 2 = 6,999,980(自分の値段なら 0.010、L-781 で 0.009)、決済 7,000,250 − 90 = 7,000,160
    rows = seq((UP5 + DOWN5) * 3 + [B7])
    rows = [r for r in rows if r[0] != 24]
    res = run(tmp_path, rows, dict(BASE, foot=5))
    check_ok(res)
    for s in SIDES:
        assert [(o[0], o[1], o[3], o[4], o[7]) for o in orders(res, s)] == [
            ("road-0", "buy", "7000070.0", "0.009", t(31)), ("road-1", "sell", "7000160.0", "0.009", t(31)),
            ("road-2", "buy", "6999980.0", "0.009", t(31)), ("road-3", "sell", "7000160.0", "0.009", t(31))]
        assert signal_value(res, s, "e1")["vola"] == pytest.approx(90)


@need_m
def test_u9_foot5_first_bar_off_grid(tmp_path):
    # 最初の足が 5 分の区切りから 2 分ずれている(分 2 から始まる)。窓は UTC の 5 分の区切り(v37:339 の minute % foot == 0)なので、
    #   最初の窓は分 2〜4 の 3 本で閉じ(分 4 の足が窓の終わり T0 + 5 分に閉じる)、窓 2〜6 は U9 の 1 本目と同じ。
    #   31 本目の判定(窓 6 本まで)の指標は窓 4〜6 から → U9 の 1 本目と同じ合図と注文。最初の足の時刻から区切ると、
    #   31 本目の時点で閉じた窓は 5 本で、合図が出ない
    rows = [r for r in seq((UP5 + DOWN5) * 3 + [B7]) if r[0] >= 2]
    res = run(tmp_path, rows, dict(BASE, foot=5))
    check_ok(res)
    for s in SIDES:
        assert [x[:4] for x in signals(res, s)] == [("e1", "建て", "long", t(31))]
        assert [(o[0], o[1], o[3], o[4], o[7]) for o in orders(res, s)] == [
            ("road-0", "buy", "7000050.0", "0.009", t(31)), ("road-1", "sell", "7000150.0", "0.009", t(31)),
            ("road-2", "buy", "6999950.0", "0.009", t(31)), ("road-3", "sell", "7000150.0", "0.009", t(31))]


@need_m
def test_u9_foot1_missing_minute_counts_bars_present(tmp_path):
    # foot 1 で分 3 が抜けた(足 4 本目以降が 1 分ずれる)。窓は「ある足の本数」で数える → 合図と注文は U3 と同じ値段で、
    #   時刻だけ 1 分あと(足 7 の値段の足は分 7 に始まり t(8) に閉じる)
    rows = [(i if i < 3 else i + 1,) + r[1:] for i, r in enumerate(R_BARS[:7])]
    res = run(tmp_path, rows, BASE)
    check_ok(res)
    for s in SIDES:
        assert [x[:4] for x in signals(res, s)] == [("e1", "建て", "long", t(8))]
        assert [(o[3], o[7]) for o in orders(res, s)] == [("7000050.0", t(8)), ("7000150.0", t(8)),
                                                          ("6999950.0", t(8)), ("7000150.0", t(8))]


# ================================================================ U10 指標の細部(割る数・丸め・ヒゲ・等号・慣らし)
@need_m
def test_u10_center_is_python_round_half_even(tmp_path):
    # 高値 7,000,301・安値 7,000,200 → (7,000,301 + 7,000,200) ÷ 2 = 7,000,250.5 → round = 7,000,250(偶数へ。v37:500)。
    #   実体 101 → ボラ = 101 × 2 ÷ 2 = 101 → 買いの線 7,000,250 − 202 = 7,000,048
    a, b = (7000200, 7000301, 7000200, 7000301), (7000301, 7000301, 7000200, 7000200)
    res = run(tmp_path, seq([a, b] * 3 + [B7]), BASE)
    for s in SIDES:
        v = signal_value(res, s, "e1")
        assert (v["center"], v["vola"], v["lsp"]) == (7000250, pytest.approx(101), pytest.approx(7000048))


@need_m
@pytest.mark.parametrize("beard,rmax,rmin", [(1, 7000300, 7000200), (None, 7000400, 7000100), (200, 7000400, 7000100)])
def test_u10_beard_cut(tmp_path, beard, rmax, rmin):
    # ヒゲ 100 円の足。beard_ignore 1: ヒゲ > 1 → 高値・安値を実体の端に切る(v37:567-591)→ レンジ 7,000,200〜7,000,300。
    #   無効(None)・200(ヒゲ 100 は 200 を越えない)→ 切らない → 7,000,100〜7,000,400。どちらも中心 7,000,250・ボラ 100
    a, b = (7000200, 7000400, 7000100, 7000300), (7000300, 7000400, 7000100, 7000200)
    res = run(tmp_path, seq([a, b] * 3 + [B7]), dict(BASE, beard_ignore=beard))
    for s in SIDES:
        v = signal_value(res, s, "e1")
        assert (v["range_max"], v["range_min"], v["center"], v["vola"]) == (rmax, rmin, 7000250, 100)


@need_m
@pytest.mark.parametrize("last", [7000050, 7000450])
def test_u10_close_on_the_line_no_signal(tmp_path, last):
    # 終値がちょうど線の上(買いの線 7,000,050・売りの線 7,000,450)→ 合図なし(v37:995-998 は厳しい > と <)
    b7 = (7000250, max(7000250, last), min(7000250, last), last)
    res = run(tmp_path, seq(WARM + [b7]), BASE)
    for s in SIDES:
        assert signals(res, s) == [] and orders(res, s) == []


@need_m
def test_u10_no_decision_before_warm(tmp_path):
    # 慣らし: 束ねた足が max(vola_count, range_count × break_len_mult) = 6 本そろうまで判定しない。
    #   足 6 本目の終値を大きく下げても(足 5 まででは買いの線 7,000,050)、足 6 の判定は束ねた足 5 本なので合図なし
    rows = WARM[:5] + [(7000300, 7000300, 6999000, 6999000)]
    res = run(tmp_path, seq(rows), BASE)
    for s in SIDES:
        assert signals(res, s) == [] and orders(res, s) == []


# ================================================================ U11 自動の段数(v37:1058-1062)
@need_m
def test_u11_auto_levels_after_trade(tmp_path):
    # auto_levels: 最初は levels(2)。建玉が 0 に戻った判定で、expantion_flg が 0 なら 5、それ以外は 7。
    #   expantion_flg: 足 7 の安値 7,000,000 < 前のレンジの安値 7,000,200 → −1、足 8 の安値 6,999,900 < 7,000,000 → −2。
    #   楽観側は足 8(−1)、悲観側は足 9(−2)の判定で 0 に戻る → どちらも 7。
    # 足 10 の判定(足 9 まで): 中心 round((7,000,200 + 6,999,900) ÷ 2) = 7,000,050、ボラ (200 + 100) ÷ 2 = 150 →
    #   買いの線 6,999,750 > 6,999,700 → e2 で 7 段: 6,999,750 から 150 ずつ。量 = 200,000 × 0.7 ÷ 7 ÷ 6,999,750 → 0.002
    rows = R_BARS + [(9, 7000000, 7000000, 6999700, 6999700, 1)]
    res = run(tmp_path, rows, dict(BASE, auto_levels=True))
    check_ok(res)
    for s in SIDES:
        assert signal_value(res, s, "e1")["levels"] == 2
        assert signal_value(res, s, "e2")["levels"] == 7
        e2 = [r for r in res["orders"][s] if r["placed_t_ns"] == t(10) and r["exit_kind"] == ""]
        assert [r["limit_px"] for r in e2] == [f"{6999750 - 150 * i}.0" for i in range(7)]
        assert {(r["levels"], r["qty"]) for r in e2} == {("7", "0.002")}


# ================================================================ U12 置き直した決済が、出ている自分の段と交差する(事前の批評 1 回目の問2)
X_BARS = WARM + [B7, (7000120, 7000120, 7000040, 7000040), (7000040, 7000045, 6999960, 6999960),
                 (6999960, 6999990, 6999960, 6999970)]


@need_m
def test_u12_exit_crossing_own_ladder(tmp_path):
    # 足 8: 段 1(7,000,050)だけ約定。判定(足 7 まで)で close 7,000,050(road-4)。
    # 足 9 の判定(足 8 まで): 中心 7,000,150・ボラ 150 → 7,000,000 < 7,000,050 → 置き直す(road-5)。
    # 足 10 の判定(足 9 まで): 中心 round((7,000,200 + 6,999,960) ÷ 2) = 7,000,080、ボラ (200 + 80) ÷ 2 = 140 →
    #   7,000,080 − 140 = 6,999,940 < 7,000,000 → 置き直す(road-6)。出ている自分の買いの段 road-2(6,999,950)より下なので交差する。
    # 戦略は計算した値段のまま出す(L-779)。交差の扱いは走らせの self_trade の決まり: 宣言しない走らせは止まり、
    #   cancel_maker を宣言した走らせ(この試験だけの宣言。測るときの決まりは測る委任で決める)では待っていた road-2 が閉じる
    with pytest.raises(Exception, match="self_trade"):
        run(tmp_path / "a", seq(X_BARS), BASE)
    res = run(tmp_path / "b", seq(X_BARS), BASE, rules={"market_ref": "next_bar_open", "self_trade": "cancel_maker"})
    check_ok(res)
    for s in SIDES:
        rows = {r["order_id"]: r for r in res["orders"][s]}
        assert [(o[0], o[1], o[3], o[5], o[7]) for o in orders(res, s)][4:] == [
            ("road-4", "sell", "7000050.0", "close", t(8)), ("road-5", "sell", "7000000.0", "close", t(9)),
            ("road-6", "sell", "6999940.0", "close", t(10))]
        assert (rows["road-4"]["canceled_t_ns"], rows["road-5"]["canceled_t_ns"]) == (t(9), t(10))
        assert (rows["road-2"]["state"], rows["road-2"]["close_reason"]) == ("CANCELED", "self_trade")

"""単純な測りの道の直し 2(走らせの側)の受け入れの試験。

リードが書いた(決まりの正本は docs/DISCUSSIONS/2026-10-08_simple_road/SPEC.md §3・§4。批評家の答えは
docs/AUDITOR/VERDICTS/2026-10-08_simple_s1_fix_critic1.md)。作業者は試験を変えずに通す。
test_s1_spec.py・test_s1_fix_spec.py も変えずに通す。

オーナーの逐語: L-824「**(a)**」/ L-828「**ⅱ**」
"""
from __future__ import annotations

import csv
import json
import os

import pytest

simple = pytest.importorskip("bot.bt.simple")
run, check_numbers, SimpleRoadError = simple.run, simple.check_numbers, simple.SimpleRoadError

SIDES = ("optimistic", "pessimistic")
SEAL = "2023-12-17T15:00:00+00:00"
META = {"strategy": "試験", "params": {}, "seal": SEAL, "bar_files": []}


def ts(k):
    return f"2023-11-14T22:{10 + k:02d}:00+00:00"


def bars(rows):
    return [(ts(k),) + tuple(float(x) for x in r) + (1.0,) for k, r in enumerate(rows)]


class Script:
    """足 k の判定で plan[k] の注文を返す。約定し終えた番号は返さない(raw なら返す)。"""

    def __init__(self, plan, raw=False):
        self.plan, self.raw, self.k, self.done = plan, raw, -1, set()

    def decide(self, bar, fills):
        self.k += 1
        self.done |= {f["id"] for f in fills}
        return {i: o for i, o in self.plan.get(self.k, {}).items() if self.raw or i not in self.done}, []


def go(tmp_path, rows, plan, side, raw=False):
    out = tmp_path / side
    run(bars(rows), Script(plan, raw), side=side, out_dir=str(out), tick=1.0, meta=META)
    return out


def table(out, name, side):
    with open(os.path.join(out, f"{name}_{side}.csv"), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def fills(out, side):
    return [(r["ts"], r["id"], r["px"], r["case"]) for r in table(out, "fills", side)]


def summary(out, side):
    with open(os.path.join(out, f"summary_{side}.json"), encoding="utf-8") as fh:
        return json.load(fh)


FLAT = (7000000, 7000000, 7000000, 7000000)
A1 = (7000000, 7000050, 6999950, 7000000)  # 7,000,000 の買いが範囲の内。7,000,100 の売りは高値より上で約定しない
A2 = (7000000, 7000150, 6999850, 7000000)  # 7,000,100 の売りと 6,999,900 の買いが範囲の内
UP = (7000200, 7000300, 7000150, 7000200)  # 始値 7,000,200。7,000,100 の売りは安値 7,000,150 より下 = 約定する向きに範囲の外 → 始値
R1 = {"form": "limit", "side": "buy", "qty": 0.009, "px": 7000000.0}
X1 = {"form": "exit", "side": "sell", "qty": 0.009, "parent": "r1", "px": 7000100.0}
C1 = {"form": "limit", "side": "sell", "qty": 0.009, "px": 7000100.0, "close": True}
R2 = {"form": "limit", "side": "buy", "qty": 0.009, "px": 6999900.0}
M1 = {"form": "market", "side": "buy", "qty": 0.009}


# ================================================================ G1 前からの建玉を閉じる利確が始値で約定 → 成行より先(L-828)
@pytest.mark.parametrize("side", SIDES)
def test_g1_exit_at_open_before_market(tmp_path, side):
    # 足 1 で r1 が 7,000,000 で約定(x1 は高値より上で約定しない)。足 2 は始値 7,000,200 で、x1(売り 7,000,100)は
    #   約定する向きに範囲の外 → 始値 7,000,200(open)。成行 m1 も始値 7,000,200。同じ始値なので閉じる利確が先(L-828 の ⅱ)
    out = go(tmp_path, [FLAT, A1, UP], {0: {"r1": R1, "x1": X1}, 1: {"x1": X1, "m1": M1}}, side)
    assert fills(out, side) == [(ts(1), "r1", "7000000.0", "range"), (ts(2), "x1", "7000200.0", "open"),
                                (ts(2), "m1", "7000200.0", "market")]
    assert summary(out, side)["closed_trades"] == 1


# ================================================================ G2 close の印の付いた指値は、新しい指値より先(L-824 の (a))
@pytest.mark.parametrize("side", SIDES)
def test_g2_close_limit_before_new_limit(tmp_path, side):
    # 足 1 の判定で r2(新しい買い)を先に、c1(建玉を閉じる売りの指値、close の印)を後に出す(seq は r2 が小さい)。
    #   足 2 で両方とも範囲の内。印の付いた c1 は ② の組で、③ の r2 より先に記す。取引 1 回が閉じる
    out = go(tmp_path, [FLAT, A1, A2], {0: {"r1": R1}, 1: {"r2": R2, "c1": C1}}, side)
    assert fills(out, side) == [(ts(1), "r1", "7000000.0", "range"), (ts(2), "c1", "7000100.0", "range"),
                                (ts(2), "r2", "6999900.0", "range")]
    s = summary(out, side)
    assert (s["closed_trades"], s["open_trades"]) == (1, 1)
    assert check_numbers(str(out), side) == []


@pytest.mark.parametrize("side", SIDES)
def test_g2_unmarked_limit_keeps_seq_order(tmp_path, side):
    # 同じ場面で印が無ければ、c1 は ③ の組のふつうの指値で、seq の順(r2 → c1)のまま
    c = {k: v for k, v in C1.items() if k != "close"}
    out = go(tmp_path, [FLAT, A1, A2], {0: {"r1": R1}, 1: {"r2": R2, "c1": c}}, side)
    assert [f[1] for f in fills(out, side)] == ["r1", "r2", "c1"]


# ================================================================ G3 close の印の付いた指値と成行(L-828)
@pytest.mark.parametrize("side", SIDES)
def test_g3_close_limit_at_open_before_market(tmp_path, side):
    out = go(tmp_path, [FLAT, A1, UP], {0: {"r1": R1}, 1: {"m1": M1, "c1": C1}}, side)
    assert fills(out, side) == [(ts(1), "r1", "7000000.0", "range"), (ts(2), "c1", "7000200.0", "open"),
                                (ts(2), "m1", "7000200.0", "market")]


@pytest.mark.parametrize("side", SIDES)
def test_g3_close_limit_in_range_after_market(tmp_path, side):
    out = go(tmp_path, [FLAT, A1, A2], {0: {"r1": R1}, 1: {"c1": C1, "m1": M1}}, side)
    assert fills(out, side) == [(ts(1), "r1", "7000000.0", "range"), (ts(2), "m1", "7000000.0", "market"),
                                (ts(2), "c1", "7000100.0", "range")]


# ================================================================ G4 close の印の止め方
L1 = {"form": "level", "side": "buy", "qty": 0.009, "root": "r1", "offset": -100.0}
G4 = [
    ("利確に印", {0: {"r1": R1, "x1": dict(X1, close=True)}}),
    ("段に印", {0: {"r1": R1, "l1": dict(L1, close=True)}}),
    ("成行に印", {0: {"m1": dict(M1, close=True)}}),
    ("印が false", {0: {"c1": dict(C1, close=False)}}),
    ("印が 1", {0: {"c1": dict(C1, close=1)}}),
    ("印が文字", {0: {"c1": dict(C1, close="yes")}}),
    ("同じ番号で印を外す", {0: {"c1": dict(C1, px=7000500.0)}, 1: {"c1": {k: v for k, v in C1.items() if k != "close"} | {"px": 7000500.0}}}),
]


@pytest.mark.parametrize("name,plan", G4, ids=[g[0] for g in G4])
def test_g4_close_mark_stops(tmp_path, name, plan):
    with pytest.raises(SimpleRoadError):
        go(tmp_path, [FLAT, FLAT, FLAT], plan, "optimistic", raw=True)


# ================================================================ G5 段に付けた利確も ② の組(作り終えた後の批評家、直しの後の 1 回目)
@pytest.mark.parametrize("side", SIDES)
def test_g5_exit_on_level_of_earlier_bar_before_new_limit(tmp_path, side):
    # 足 1(B1)で根 r が始値 6,999,800、段 l1(−100)が 6,999,700 で anchor_bar。足 1 の判定で r2(買い 6,999,650)を先に、
    #   l1 に付けた利確 xl(売り 6,999,790)を後に出す。足 2(B2)で両方とも範囲の内。xl の親 l1 は前の足で約定したので
    #   ② の組で、③ の r2 より先に記す
    root = {"form": "limit", "side": "buy", "qty": 0.009, "px": 7000050.0}
    lv = {"form": "level", "side": "buy", "qty": 0.009, "root": "r", "offset": -100.0}
    xl = {"form": "exit", "side": "sell", "qty": 0.009, "parent": "l1", "px": 6999790.0}
    r2 = {"form": "limit", "side": "buy", "qty": 0.009, "px": 6999650.0}
    b1 = (6999800, 6999850, 6999700, 6999750)
    b2 = (6999750, 6999800, 6999550, 6999600)
    out = go(tmp_path, [FLAT, b1, b2], {0: {"r": root, "l1": lv}, 1: {"r2": r2, "xl": xl}}, side)
    assert fills(out, side) == [(ts(1), "r", "6999800.0", "open"), (ts(1), "l1", "6999700.0", "anchor_bar"),
                                (ts(2), "xl", "6999790.0", "range"), (ts(2), "r2", "6999650.0", "range")]


# ================================================================ G6 注文の記録の close の列(SPEC.md §4)
def test_g6_orders_close_column(tmp_path):
    out = go(tmp_path, [FLAT, A1, A2], {0: {"r1": R1}, 1: {"r2": R2, "c1": C1}}, "optimistic")
    with open(os.path.join(out, "orders_optimistic.csv"), newline="", encoding="utf-8") as fh:
        head = next(csv.reader(fh))
    assert head == ["seq", "id", "form", "side", "qty", "px_calc", "px", "root", "offset", "parent", "from_ts", "to_ts",
                    "close"]
    rows = {r["id"]: r["close"] for r in table(out, "orders", "optimistic")}
    assert rows == {"r1": "", "r2": "", "c1": "1"}


# ================================================================ G7 買いの閉じる注文(空売りを閉じる側。事前の批評、直し 2 の 1 回目)
S1 = {"form": "limit", "side": "sell", "qty": 0.009, "px": 7000000.0}  # 足 A1 の範囲の内で約定する空売り
XB = {"form": "exit", "side": "buy", "qty": 0.009, "parent": "s1", "px": 6999900.0}
CB = {"form": "limit", "side": "buy", "qty": 0.009, "px": 6999900.0, "close": True}
S2 = {"form": "limit", "side": "sell", "qty": 0.009, "px": 7000100.0}
MS = {"form": "market", "side": "sell", "qty": 0.009}
DOWN = (6999800, 6999850, 6999750, 6999800)  # 始値 6,999,800。6,999,900 の買いは高値 6,999,850 より上 = 約定する向きに範囲の外 → 始値


@pytest.mark.parametrize("side", SIDES)
def test_g7_buy_exit_at_open_before_market(tmp_path, side):
    out = go(tmp_path, [FLAT, A1, DOWN], {0: {"s1": S1, "xb": XB}, 1: {"xb": XB, "ms": MS}}, side)
    assert fills(out, side) == [(ts(1), "s1", "7000000.0", "range"), (ts(2), "xb", "6999800.0", "open"),
                                (ts(2), "ms", "6999800.0", "market")]


@pytest.mark.parametrize("side", SIDES)
def test_g7_buy_close_limit_before_new_limit(tmp_path, side):
    out = go(tmp_path, [FLAT, A1, A2], {0: {"s1": S1}, 1: {"s2": S2, "cb": CB}}, side)
    assert fills(out, side) == [(ts(1), "s1", "7000000.0", "range"), (ts(2), "cb", "6999900.0", "range"),
                                (ts(2), "s2", "7000100.0", "range")]


@pytest.mark.parametrize("side", SIDES)
def test_g7_buy_close_limit_at_open_before_market(tmp_path, side):
    out = go(tmp_path, [FLAT, A1, DOWN], {0: {"s1": S1}, 1: {"ms": MS, "cb": CB}}, side)
    assert fills(out, side) == [(ts(1), "s1", "7000000.0", "range"), (ts(2), "cb", "6999800.0", "open"),
                                (ts(2), "ms", "6999800.0", "market")]


# ================================================================ G8 値段が安値・高値ちょうどの閉じる注文は範囲の内(②、成行の後)
@pytest.mark.parametrize("side", SIDES)
def test_g8_sell_close_at_low_is_in_range(tmp_path, side):
    low_eq = (7000200, 7000300, 7000100, 7000200)  # 安値 7,000,100 = C1 の値段
    out = go(tmp_path, [FLAT, A1, low_eq], {0: {"r1": R1}, 1: {"c1": C1, "m1": M1}}, side)
    assert fills(out, side) == [(ts(1), "r1", "7000000.0", "range"), (ts(2), "m1", "7000200.0", "market"),
                                (ts(2), "c1", "7000100.0", "range")]


@pytest.mark.parametrize("side", SIDES)
def test_g8_buy_exit_at_high_is_in_range(tmp_path, side):
    high_eq = (6999800, 6999900, 6999750, 6999800)  # 高値 6,999,900 = XB の値段
    out = go(tmp_path, [FLAT, A1, high_eq], {0: {"s1": S1, "xb": XB}, 1: {"xb": XB, "ms": MS}}, side)
    assert fills(out, side) == [(ts(1), "s1", "7000000.0", "range"), (ts(2), "ms", "6999800.0", "market"),
                                (ts(2), "xb", "6999900.0", "range")]


# ================================================================ G9 約定しない印付きの指値の close の列(消えた・データの終わりまで残った)
def test_g9_close_column_on_unfilled_orders(tmp_path):
    far = dict(C1, px=7100000.0)
    out = go(tmp_path, [FLAT, FLAT, FLAT], {0: {"gone": far}, 1: {"kept": far}, 2: {"kept": far}}, "optimistic")
    assert fills(out, "optimistic") == []
    rows = {r["id"]: (r["close"], r["to_ts"]) for r in table(out, "orders", "optimistic")}
    assert rows == {"gone": ("1", ts(1)), "kept": ("1", ts(2))}

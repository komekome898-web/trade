"""マチルダ(v37)の直し A の受け入れの試験: ブレイクの向きの直の入れ替わり(L-815)と、道の土台の遅さ(L-815「4.直す」)。

リードが書いた(委任文 docs/DISCUSSIONS/2026-10-06_held_batches/matilda_step0/DELEGATION_matilda_v37_fixA.md)。
作業者は試験を変えずに通す(変えたいときは問いとして返す)。場面の道具は 1 本目の受け入れの試験
`tests/road/test_matilda_v37_spec.py` のものを使う。

オーナーの逐語:
- L-815「**2.実際にあり得ない挙動に対応する必要はないけど、この挙動は本測定で起こりうる？**」(ブレイクの向きの直の
  入れ替わりは起こりうる、とリードが答えた)「**4.直す**」(測定 1 本の時間が足の本数の 2 乗で伸びる所を直す)
"""
from __future__ import annotations

import gzip
import hashlib
import os
import random
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_matilda_v37_spec as S  # noqa: E402  1 本目の受け入れの試験の場面の道具
from bot.bt.core import BarEvent  # noqa: E402
from bot.bt.road.strategy import RoadStrategy  # noqa: E402
from bot.bt.road.tables import SCHEMA  # noqa: E402

M = S.M
need_m = S.need_m
t = S.t


# ================================================================ A1 ブレイクの向きの直の入れ替わり(途中の決め Q1 の形)
@need_m
def test_a1_break_flip_ends_old_signal_and_starts_new(tmp_path):
    # BRK_HEAD(1 本目の U8 の足)を b_signal を使わずに走らせる。足 7 で上のブレイク b1(1 本目の U8 と同じ)。
    # 下の線の列: 足 7・足 8 を指標に入れたとき(ブレイク中なので書き足す)、足 5〜7 の安値 7,000,400 − 幅 300 × 0.5 = 6,999,850、
    #   足 6〜8 の安値 7,000,400 − 幅 400 × 0.5 = 7,000,200。足 9 の判定(足 8 まで): bdp = min(7,000,200, 2 倍の安値 7,000,400)
    #   = 7,000,200 > 終値 7,000,100、旗 1 ≠ −1、b_signal 0 ≠ 1 → 旗が 1 から −1 に直に変わる(v37:943)。
    # 決め(途中の決め Q1): b1 を理由「逆向きのブレイク」で消し、同じ判定で b2(down)を出す。b_signal は変えない(v37:943 が
    #   変えるのはブレイクの旗だけ)。解除の判定(v37:952-966)は、旗 −1 で last 7,000,100 > 中心 7,000,600 でないので解除しない。
    #   b_signal を使わないので玉なしでは建てない(注文 0)
    bars = S.seq(S.BRK_HEAD + [(7000800, 7000800, 7000100, 7000100)])
    res = S.run(tmp_path, bars, dict(S.BRK_PARAMS, b_signal=False))
    S.check_ok(res)
    for s in S.SIDES:
        assert S.signals(res, s) == [("b1", "ブレイク", "up", t(7), t(9), "逆向きのブレイク"),
                                     ("b2", "ブレイク", "down", t(9), "", "データの終わり")]
        assert S.orders(res, s) == []


@need_m
def test_a1_break_flip_with_position_and_b_signal(tmp_path):
    # 本測定の形(b_signal を使い、玉を持っている)で、ブレイクの向きが直に入れ替わる場面。
    # 足 0〜7 = BRK_HEAD、足 8 = (7,000,800, 7,000,800, 7,000,700, 7,000,700)(1 本目の U8 と同じく、足 7 の判定で b1(up)、
    #   足 8 の判定で e1(long)の段が出て、足 8 で約定する)。
    # 足 9 = 始値 7,000,700・高値 7,000,900・安値 7,000,650・終値 7,000,650・出来高 10: 足 10 の判定(足 9 の終値)は
    #   last 7,000,650 = 中心 7,000,650(足 7〜9 の高値 7,000,900・安値 7,000,650 の中心)で「last < 中心」でないので解除しない。
    #   足 9 を指標に入れると(足 11 の判定から効く)、ブレイク中・出来高 10 > 平均(足 7・8 の出来高 1・1 の平均 1)・
    #   陰線(実体 −50)で上のヒゲ 200(高値 − 始値)> 下のヒゲ 0 かつ > |実体| 50、旗 1・b_signal 1 ≧ 0 → b_signal 1 − 1 = 0(v37:621-643)。
    # 足 10 = (7,000,650, 7,000,650, 7,000,100, 7,000,100): 足 11 の判定(足 9 まで): 下の線の列の最後 = 足 7〜9 の安値 7,000,650
    #   − 幅 250 × 0.5 = 7,000,525、2 倍の安値(足 4〜9)7,000,400。bdp = min(7,000,525, 7,000,400) = 7,000,400 > last 7,000,100、
    #   旗 1 ≠ −1、b_signal 0 ≠ 1 → 旗が 1 から −1 に直に変わる。
    #   決め(途中の決め Q1): b1 を「逆向きのブレイク」で消し、同じ判定で b2(down)。建ての旗は −1(ブレイク中で b_signal 0・玉あり)
    #   になり e1 を「合図の条件が外れた」で消して e2(short)。買い玉で建ての旗 −1 → 決済の旗 3(M10)→ 成行の決済(flatten)を
    #   足 11 の判定で出し、次の足 11 の始値 7,000,100 で約定する。
    # 足 11 = (7,000,100, 7,000,150, 7,000,000, 7,000,050): 決済の後は玉なしで b_signal 0 → 建ての旗 0 → e2 を消す。
    # 段の値段と約定の値段(良い側と悪い側で道筋が違う)は直し B(段の約定の決まり)で変わりうるので見ない。
    bars = S.seq(S.BRK_HEAD + [(7000800, 7000800, 7000700, 7000700), (7000700, 7000900, 7000650, 7000650, 10),
                               (7000650, 7000650, 7000100, 7000100), (7000100, 7000150, 7000000, 7000050)])
    res = S.run(tmp_path, bars, dict(S.BRK_PARAMS))
    S.check_ok(res)
    for s in S.SIDES:
        assert S.signals(res, s) == [("b1", "ブレイク", "up", t(7), t(11), "逆向きのブレイク"),
                                     ("e1", "建て", "long", t(8), t(11), "合図の条件が外れた"),
                                     ("b2", "ブレイク", "down", t(11), "", "データの終わり"),
                                     ("e2", "建て", "short", t(11), t(12), "合図の条件が外れた")]
        last = res["orders"][s][-1]
        assert (last["exit_kind"], last["placed_t_ns"], last["state"]) == ("flatten", t(11), "FILLED")
        assert S.fills(res, s)[-1] == (last["order_id"], t(11), "7000100.0")
        # 入れ替わりの判定の後に出ている注文は残らない(取り消したか約定した)
        assert all(r["state"] in ("FILLED", "CANCELED") for r in res["orders"][s])


# ================================================================ A2 道の土台の遅さ(記録を変えずに)
def _walk(n, seed, sig):
    rng = random.Random(seed)
    px = 7_000_000
    out = []
    for i in range(n):
        o = px
        c = o + round(rng.gauss(0, sig))
        h = max(o, c) + abs(round(rng.gauss(0, sig / 2)))
        lo = min(o, c) - abs(round(rng.gauss(0, sig / 2)))
        out.append((i, o, h, lo, c, rng.randint(1, 10)))
        px = c
    return out


# 直す前のコード(src を最後に変えたコミット 81e301d2)で、下の走らせの 4 つの表(signals・orders・fills・trades)の中身から取った指紋。
# 2 回打って同じ値(docs/DISCUSSIONS/2026-10-06_held_batches/matilda_step0/DELEGATION_matilda_v37_fixA.md の読んだ事実)。
# 直し B(段の約定の決まりと交差、L-816)は記録を変える(注文の表の列・段の約定の値段)ので、B1・B2 の受け取りの後に
# リードがこの値を取り直し、取り直した理由を B の委任の記録に書く(作業者は変えない)。
PINNED = "ec36edecbcd8c276b19137e5c7527916c5c8717f09d4a4f275afb6621de1d7e5"


@need_m
def test_a2_record_unchanged_on_walk(tmp_path):
    # 合成の乱歩 2,000 本(σ 3,000 円、seed 0)・原典の値・self_trade = cancel_both。土台の直しで記録が 1 字も変わらない
    res = S.run(tmp_path, _walk(2000, 0, 3000), dict(M.V37_ORIGINAL),
                rules={"market_ref": "next_bar_open", "self_trade": "cancel_both"})
    h = hashlib.sha256()
    for name in ("signals", "orders", "fills", "trades"):
        with gzip.open(os.path.join(res["store"], SCHEMA["tables"][name]["file"]), "rb") as fh:
            h.update(fh.read())
    assert h.hexdigest() == PINNED
    S.check_ok(res)


class _Ctx:
    def __init__(self):
        self.now_ns = 60 * S.NS

    def place_order(self, req):
        pass

    def order(self, coid):
        return None  # 届いた注文の見え方が無い = 出ていない注文(閉じた注文と同じ扱い)

    def cancel_order(self, coid):
        pass


class _Many(RoadStrategy):
    """足 1 本の知らせで、閉じた(出ていない)建ての指値を n 個と、決済の行(建玉 0 なので「量が 0 で出さない」の行)を n 個
    作ってから、close と flatten を 1 回ずつ呼ぶ。建ての行と決済の行の両方を溜めるのは、片方だけを見ない直しで通らないため。"""

    def __init__(self, n):
        super().__init__(quote_ccy="JPY")
        self.n = n
        self.cost = {}

    def step(self, event, ctx):
        if not isinstance(event, BarEvent):
            return
        self.signal_start("s1", "試験", "long", {})
        for i in range(self.n):
            self.place("buy", "limit", 6_000_000.0 + i, 1, "s1")
            self.close("無し", "limit", 8_000_000.0 + i)
        t0 = time.perf_counter()
        self.close("無し", "limit", 7_000_000.0)
        self.cost["close"] = time.perf_counter() - t0
        t0 = time.perf_counter()
        self.flatten("無し")
        self.cost["flatten"] = time.perf_counter() - t0


def test_a2_cost_does_not_grow_with_closed_orders():
    # 出ていない注文の行が 10,000 個(建て 5,000・決済 5,000)あっても、close と flatten の 1 回が 2 ミリ秒を超えない
    #   (直す前は、呼ぶたびに今までの注文を全部見直すので注文の数に比例して重くなる: `src/bot/bt/road/strategy.py` の
    #   `_pending_exit`・`flatten`・`_open_rows`)。比べに 10 個ずつのときも測り、5,000 個ずつのときが 10 個ずつのときの
    #   10 倍を超えないことも見る(機械の速さによらない形)。時間は 3 回測った最小(ほかの処理の割り込みを除く)
    costs = {}
    for n in (10, 5000):
        reps = []
        for _ in range(3):
            s = _Many(n)
            s.set_price_tick(1.0)
            s.on_event(BarEvent(received_time_ns=60 * S.NS, start_time_ns=0, open=7e6, high=7e6, low=7e6, close=7e6,
                                volume=1.0), _Ctx())
            reps.append(s.cost)
        costs[n] = {k: min(r[k] for r in reps) for k in ("close", "flatten")}
    for k in ("close", "flatten"):
        assert costs[5000][k] < 0.002, (k, costs)
        assert costs[5000][k] < 10 * max(costs[10][k], 1e-5), (k, costs)

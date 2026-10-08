"""マチルダ(v37)の直し A の受け入れの試験: ブレイクの向きの直の入れ替わり(L-815)と、道の土台の遅さ(L-815「4.直す」)と、
検査のツールの遅さ(L-818)。

リードが書いた(委任文 docs/DISCUSSIONS/2026-10-06_held_batches/matilda_step0/DELEGATION_matilda_v37_fixA.md)。
作業者は試験を変えずに通す(変えたいときは問いとして返す)。場面の道具は 1 本目の受け入れの試験
`tests/road/test_matilda_v37_spec.py` のものを使う。

オーナーの逐語:
- L-815「**2.実際にあり得ない挙動に対応する必要はないけど、この挙動は本測定で起こりうる？**」(ブレイクの向きの直の
  入れ替わりは起こりうる、とリードが答えた)「**4.直す**」(測定 1 本の時間が足の本数の 2 乗で伸びる所を直す)
- L-818「**検査ツールの遅さ(決済の行ごとに帳簿を作り直す所)も、直し A の委任に入れて直してよいですか。 →yes**」
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
from bot.bt.road import check_outputs  # noqa: E402
from bot.bt.road.strategy import RoadStrategy  # noqa: E402
from bot.bt.road.tables import ROAD_DIR, SCHEMA  # noqa: E402

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
    # 足 9 = 始値 7,000,700・高値 7,000,900・安値 7,000,650・終値 7,000,650・出来高 10: 足 10 の判定(指標は足 8 まで、last は
    #   足 9 の終値)は last 7,000,650 = 中心 7,000,650(足 6〜8 の高値 7,000,800・安値 7,000,500 の中心)で「last < 中心」でないので
    #   解除しない。
    #   足 9 を指標に入れると(足 11 の判定から効く)、ブレイク中・出来高 10 > 平均(足 7・8 の出来高 1・1 の平均 1)・
    #   陰線(実体 −50)で上のヒゲ 200(高値 − 始値)> 下のヒゲ 0 かつ > |実体| 50、旗 1・b_signal 1 ≧ 0 → b_signal 1 − 1 = 0(v37:621-643)。
    # 足 10 = (7,000,650, 7,000,650, 7,000,100, 7,000,100): 足 11 の判定(足 9 まで): 下の線の列の最後 = 足 7〜9 の安値 7,000,650
    #   − 幅 250 × 0.5 = 7,000,525、2 倍の安値(足 4〜9)7,000,400。bdp = min(7,000,525, 7,000,400) = 7,000,400 > last 7,000,100、
    #   旗 1 ≠ −1、b_signal 0 ≠ 1 → 旗が 1 から −1 に直に変わる。
    #   決め(途中の決め Q1): b1 を「逆向きのブレイク」で消し、同じ判定で b2(down)。建ての旗は −1(ブレイク中で b_signal 0・玉あり)
    #   になり e1 を「合図の条件が外れた」で消して e2(short)。買い玉で建ての旗 −1 → 決済の旗 3(M10)→ 成行の決済(flatten)を
    #   足 11 の判定で出し、次の足 11 の始値 7,000,100 で約定する。
    # 足 11 = (7,000,100, 7,000,150, 7,000,000, 7,000,050): 決済の後は玉なしで b_signal 0 → 建ての旗 0 → e2 を消す。
    # 段の値段と約定の値段は直し B(段の約定の決まり)で変わりうるので見ない。良い側と悪い側で入れ替わりの前の道筋は違う
    #   (良い側は段に付けた決済が足 8 で約定、悪い側は close が足 10 の判定までに約定して玉が 0 になり、足 10 の判定で出した段が
    #   足 10 で約定する)。どちらも足 11 の判定で入れ替わり、flatten で閉じる(事前の批評 1 回目の担当が試作で確かめた)。
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


# 足 0〜9 は test_a1_break_flip_with_position_and_b_signal と同じ。足 10 = 始値 7,000,800・高値 7,001,000・安値 7,000,780・
#   終値 7,000,780・出来高 20: 足 11 の判定は last 7,000,780 ≧ 中心 7,000,775(足 7〜9)で解除しない。足 10 を指標に入れると
#   (足 12 の判定から)、ブレイク中・出来高 20 > 平均(足 8・9 の 1・10 の平均 5.5)・陰線で上のヒゲ 200 > 下のヒゲ 0 かつ > |実体| 20、
#   旗 1・b_signal 0 ≧ 0 → b_signal −1。足 11 = (7,000,780, 7,000,780, 7,000,100, 7,000,100): 足 12 の判定で bdp = min(足 8〜10 の
#   安値 7,000,650 − 幅 350 × 0.5 = 7,000,475, 2 倍の安値 7,000,400) = 7,000,400 > 7,000,100、旗 1 ≠ −1、b_signal −1 ≠ 1 → 入れ替わり。
#   b_signal は −1 のまま(作るもの 1)なので、建ての旗は −1(旗 = −b_signal でない・b_signal ≠ 0)で e2(short)の値の b_signal は −1。
#   b_signal を 0 にする作りでは、e2 の値が 0 になる(玉の無い側では e2 が出ない)
FLIP_M1 = S.BRK_HEAD + [(7000800, 7000800, 7000700, 7000700), (7000700, 7000900, 7000650, 7000650, 10),
                         (7000800, 7001000, 7000780, 7000780, 20), (7000780, 7000780, 7000100, 7000100),
                         (7000100, 7000150, 7000000, 7000050)]


@need_m
@pytest.mark.parametrize("mirror", [False, True], ids=["上から下", "下から上"])
def test_a1_break_flip_keeps_b_signal(tmp_path, mirror):
    # 上から下(b_signal −1)と、値段を折り返した下から上(b_signal +1)。e1 の消える時刻は側で違う(悪い側は玉が先に 0 になり
    #   足 11 の判定で消える)ので見ない
    rows = S.reflect(FLIP_M1) if mirror else FLIP_M1
    res = S.run(tmp_path, S.seq(rows), dict(S.BRK_PARAMS))
    S.check_ok(res)
    d0, d1, e = ("down", "up", "long") if mirror else ("up", "down", "short")
    for s in S.SIDES:
        sig = S.signals(res, s)
        assert [r for r in sig if r[1] == "ブレイク"] == [("b1", "ブレイク", d0, t(7), t(12), "逆向きのブレイク"),
                                                       ("b2", "ブレイク", d1, t(12), "", "データの終わり")]
        assert ("e2", "建て", e, t(12), "", "データの終わり") in sig
        assert S.signal_value(res, s, "e2")["b_signal"] == (1 if mirror else -1)


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


# ================================================================ A3 検査のツールの遅さ(L-818)
def _walk_store(tmp_path, n):
    return S.run(tmp_path, _walk(n, 0, 3000), dict(M.V37_ORIGINAL),
                 rules={"market_ref": "next_bar_open", "self_trade": "cancel_both"})


def _check_secs(res, reps=1):
    best, f = None, None
    for _ in range(reps):
        t0 = time.perf_counter()
        f = check_outputs(res["store"], res["bars"]).failures
        dt = time.perf_counter() - t0
        best = dt if best is None else min(best, dt)
    return best, f


def _rows(res):
    return sum(len(v) for v in res["orders"].values())


@need_m
def test_a3_checker_cost_grows_with_bars_not_squared(tmp_path):
    # 合成の乱歩 500 本と 3,000 本。直す前は検査が 500 本 約 7.5 秒・2,000 本 約 165 秒で、注文の行 1 つあたりの時間が本数とともに
    #   伸びる(決済の行ごとに帳簿を最初から作り直す `src/bot/bt/road/check.py` の `_flatten_expect` ほか)。
    #   直した後: 注文の行 1 つあたりの検査の時間が、3,000 本で 500 本の 1.4 倍以下(慣らしの足は注文を出さないので、本数でなく
    #   行の数で比べる。どちらも 3 回測った最小。3,000 本の 1 回目が 30 秒を超えたらそこで落とす)、かつ 3,000 本の検査が 30 秒以下。
    #   検査の答え(落とす行)は両方とも 0 件のまま。事前の批評 2 回目の担当の試作では、正しい直しの比は 2,000 本で 0.86〜1.10、
    #   約定で閉じた決済の行を外さない直しは 1.31〜1.62(本数を増やすほど開く)
    r500, r3000 = _walk_store(tmp_path / "a", 500), _walk_store(tmp_path / "b", 3000)
    s3000, f3000 = _check_secs(r3000)
    assert s3000 <= 30.0, s3000
    s3000 = min(s3000, _check_secs(r3000, reps=2)[0])
    s500, f500 = _check_secs(r500, reps=3)
    assert f500 == [] and f3000 == []
    assert s3000 / _rows(r3000) <= 1.4 * s500 / _rows(r500), (s500, _rows(r500), s3000, _rows(r3000))


@need_m
def test_a3_checker_still_catches_close_size(tmp_path):
    # 直した検査も、決済(close)の量を書き換えた行を (v) で落とす(帳簿の作り直しをやめても、送った時の建玉と出ていた
    #   決済の量から量を確かめる)。乱歩 500 本の悲観側の、量が 0 でない close の行のうち最初と最後の 2 行を 1 つずつ書き換える
    import shutil
    from bot.bt.road.tables import read_csv as rc
    res = _walk_store(tmp_path, 500)
    path = os.path.join(res["store"], SCHEMA["tables"]["orders"]["file"])
    head, rows = rc(path, "orders")
    ids = [r["order_id"] for r in rows if r["range"] == "pessimistic" and r["exit_kind"] == "close"
           and float(r["qty"]) != 0]
    assert len(ids) >= 2
    for oid in (ids[0], ids[-1]):
        d = str(tmp_path / f"copy-{oid}")
        shutil.copytree(os.path.dirname(res["store"]), d)
        p2 = os.path.join(d, ROAD_DIR, SCHEMA["tables"]["orders"]["file"])
        h2, r2 = rc(p2, "orders")
        for r in r2:
            if r["range"] == "pessimistic" and r["order_id"] == oid:
                r["qty"] = str(round(float(r["qty"]) + 0.001, 3))
        S._rewrite(p2, h2, r2, d)
        f = check_outputs(os.path.join(d, ROAD_DIR), res["bars"]).failures
        assert any(x["check"] == "v" for x in f), (oid, f)


# 直す前のコード(src を最後に変えたコミット 81e301d2)で、乱歩 500 本の置き場の約定の表を書き換えたときの検査の答え
# (失敗の行を JSON にして並べた sha256 と数)。2 回打って同じ。検査を速くしても答えを変えない(L-818 の読み「検査の結果は変えない」)
ANSWERS = {"last_qty": (4, "20067d3e88f6e9f1e7274b1011bed387389c3c2de7c3bb28e35d16f32580a517"),
           "swap_seq": (3, "12a2a5f4ed2c33574822a718975dad0c29ca3f0aedb9c7ff9e083147428b3aa7"),
           "last_qty_down": (3, "dec0923f9ed78ee4616d30a472da7691fa7cea8da713c1c8dbaa4aa5a92af089"),
           "dup_order_back": (3, "e25994e9cf83801a99c553a2ada0da21ca77ac70a8c453d97900200a5f084f94"),
           "dup_order_front": (3, "3f2a19542484c1eda03ce10d10016073c0e96b3224047f3d3fc8141962449563"),
           "dup_fill": (1529, "115e7b77be0c19d32602f719a674a0e43c2b9f5b0aed4ee3701ab3a62245f745")}


def _last_qty(rows):
    # 悪い側の最後の約定の量を 0.0005 増やす(帳簿のツールが量の刻みで止まる。止まる前の約定の行の答えは変わらない)
    pes = [r for r in rows if r["range"] == "pessimistic"]
    pes[-1]["qty"] = repr(float(pes[-1]["qty"]) + 0.0005)


def _swap_seq(rows):
    # 悪い側の 11 番目と 12 番目の約定の知らせの通し番号を入れ替える(表の順と知らせの順が違う置き場)
    pes = [r for r in rows if r["range"] == "pessimistic"]
    pes[10]["notice_seq"], pes[11]["notice_seq"] = pes[11]["notice_seq"], pes[10]["notice_seq"]


def _last_qty_down(rows):
    # 悪い側の最後の約定の量を 0.0005 減らす(帳簿のツールが止まり、約定の和は注文の量を超えない)
    pes = [r for r in rows if r["range"] == "pessimistic"]
    pes[-1]["qty"] = repr(float(pes[-1]["qty"]) - 0.0005)
    return rows


def _entry_rows(rows):
    return [k for k, r in enumerate(rows) if r["range"] == "pessimistic" and r["qty_source"] != "建玉"
            and r["exit_kind"] == "" and r["state"] == "FILLED"]


def _dup_order_back(rows):
    # 悪い側の約定した建ての 4 つ目の行を、量だけ 0.005 に変えて直後に重ねる(同じ番号で中身の違う行が後ろにある)
    k = _entry_rows(rows)[3]
    d = dict(rows[k])
    d["qty"] = "0.005"
    return rows[:k + 1] + [d] + rows[k + 1:]


def _dup_order_front(rows):
    # 同じ行を直前に重ねる(同じ番号で中身の違う行が前にある)
    k = _entry_rows(rows)[3]
    d = dict(rows[k])
    d["qty"] = "0.005"
    return rows[:k] + [d] + rows[k:]


def _dup_fill(rows):
    # 悪い側の 6 つ目の約定の行を、同じ中身で直後に重ねる
    k = [j for j, r in enumerate(rows) if r["range"] == "pessimistic"][5]
    return rows[:k + 1] + [dict(rows[k])] + rows[k + 1:]


def _in_place(fn):
    def edit(rows):
        fn(rows)
        return rows
    return edit


TAMPERED = [("last_qty", "fills", _in_place(_last_qty)), ("swap_seq", "fills", _in_place(_swap_seq)),
            ("last_qty_down", "fills", _last_qty_down), ("dup_order_back", "orders", _dup_order_back),
            ("dup_order_front", "orders", _dup_order_front), ("dup_fill", "fills", _dup_fill)]


@need_m
@pytest.mark.parametrize("tag,table,edit", TAMPERED, ids=[x[0] for x in TAMPERED])
def test_a3_checker_answers_unchanged_on_tampered_store(tmp_path, tag, table, edit):
    import json
    import shutil
    from bot.bt.road.tables import read_csv as rc
    res = _walk_store(tmp_path / "w", 500)
    d = str(tmp_path / tag)
    shutil.copytree(os.path.dirname(res["store"]), d)
    p2 = os.path.join(d, ROAD_DIR, SCHEMA["tables"][table]["file"])
    h2, r2 = rc(p2, table)
    r2 = edit(r2)
    S._rewrite(p2, h2, r2, d)
    f = check_outputs(os.path.join(d, ROAD_DIR), res["bars"]).failures
    key = sorted(json.dumps(x, sort_keys=True, ensure_ascii=False) for x in f)
    assert (len(f), hashlib.sha256("\n".join(key).encode()).hexdigest()) == ANSWERS[tag], f


# ================================================================ A2 取り消しを出す順(flatten)
class _OpenView:
    def __init__(self):
        self.state = type("St", (), {"value": "OPEN"})()
        self.cancel_pending = False


class _OpenCtx:
    """出した注文は全部「出ている」と答える文脈。取り消しを出した順を残す。"""

    def __init__(self):
        self.now_ns = 60 * S.NS
        self.placed = set()
        self.canceled = []

    def place_order(self, req):
        self.placed.add(req.client_order_id)

    def order(self, coid):
        return _OpenView() if coid in self.placed else None

    def cancel_order(self, coid):
        self.canceled.append(coid)


class _Order(RoadStrategy):
    """足 1 本目で建ての指値 12 個、足 2 本目で flatten。"""

    def __init__(self):
        super().__init__(quote_ccy="JPY")
        self.bars = 0

    def step(self, event, ctx):
        if not isinstance(event, BarEvent):
            return
        self.bars += 1
        if self.bars == 1:
            self.signal_start("s1", "試験", "long", {})
            for i in range(12):
                self.place("buy", "limit", 6_999_000.0 + i, 1, "s1")
        else:
            self.flatten("無し")


def test_a2_flatten_cancels_in_placed_order():
    # flatten は出ている注文を、注文を受けた順(road-0 → road-11。番号を文字で並べると road-10 が road-2 より前に来る)に取り消す。間に road-0 の受け付けの知らせ(状態の書き直し)が
    #   届いても順は変わらない。出ているかは土台の行の状態で決める(直す前の flatten の輪 `src/bot/bt/road/strategy.py:505` と同じ)
    from bot.bt.core import OrderAckEvent
    s = _Order()
    s.set_price_tick(1.0)
    ctx = _OpenCtx()
    s.on_event(BarEvent(received_time_ns=60 * S.NS, start_time_ns=0, open=7e6, high=7e6, low=7e6, close=7e6, volume=1.0),
               ctx)
    ctx.now_ns = 90 * S.NS
    s.on_event(OrderAckEvent(received_time_ns=90 * S.NS, exchange_time_ns=90 * S.NS, client_order_id="road-0",
                             venue_order_id="v0"), ctx)
    ctx.now_ns = 120 * S.NS
    s.on_event(BarEvent(received_time_ns=120 * S.NS, start_time_ns=60 * S.NS, open=7e6, high=7e6, low=7e6, close=7e6,
                        volume=1.0), ctx)
    assert ctx.canceled == [f"road-{i}" for i in range(12)]

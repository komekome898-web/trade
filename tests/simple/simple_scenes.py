"""単純な測りの道 2 版目の場面の表(走らせの試験 test_run.py が使う)。

決まりの正本は docs/DISCUSSIONS/2026-10-08_simple_road/SPEC.md(2 版目)。期待の呼び出しと約定は全部、足の値から手で計算した
(各場面の注。根にした SPEC.md の節も書いた)。2 版目の作業者が 1 版目の表を書き換えた(コードと期待を同じ人が書くので、
注の手の計算を残して読み違いがそろって通るのを避ける)。

オーナーの逐語: L-875「**陽線のときの価格推移 O→L→H→C ・陰線のときの価格推移 O→H→L→C**」/
L-876「**直前の足のCとその足のOを比べ、その向きに動くシナリオ**」/ L-877「**取引がなかったとみなして注文を出さない**」・「**3.b**」/
L-874「**決済する値段は次の始値ではなくブレイクラインの値段にします。**」/ L-882「**口の案はそれでよい**」/
L-783「**間違えそうやから小数点以下は切り捨ててください**」/
L-831「**やらなくてもいいテスト→削除 ・重複してるテスト→削除 ・分ける必要のないテスト→統合**」(場面を 1 つの表にまとめた)

場面 = 名前・足(rows)・計画(plan)と、期待の呼び出しの並び(calls):
- 戦略 Script は、呼び出し k(0 から。足の途中 "stop" も足が閉じた "close" も数える)で plan[k] = {"o": 注文, "w": 見張る値段} を返す。
  plan に無い呼び出しでは、前に返した注文から約定し終えた番号を除いたものと、前に返した見張る値段をそのまま返す(持ち越し)。
  plan[k] にある注文も、約定し終えた番号は除く(raw=True なら除かない。止める場面で使う)。
- calls: S(足の番号, 値段, 約定, 届いた見張る値段) が "stop"、C(足の番号, 終値) が "close"。約定は (番号, 値段, case) の並び。
- 足の番号は 2023-11-14T00:00 からの分(ts(k))。
"""
from __future__ import annotations

import csv
import os

import pytest

SEAL = "2023-12-17T15:00:00+00:00"
META = {"strategy": "試験", "params": {}, "seal": SEAL, "bar_files": []}
STOP_KEYS = {"kind", "ts", "price", "fills", "touched"}
FILL_KEYS = {"id", "side", "qty", "px", "case"}


def ts(k):
    """足 k の始まり。2023-11-14T00:00 から 1 分ずつ。"""
    return f"2023-11-14T{k // 60:02d}:{k % 60:02d}:00+00:00"


def make_bars(rows):
    return [(ts(k),) + tuple(float(x) for x in r) + (1.0,) for k, r in enumerate(rows)]


def S(k, px, fills=(), touched=()):
    return ("stop", ts(k), float(px), [(i, float(p), c) for i, p, c in fills], [float(x) for x in touched])


def C(k, px):
    return ("close", ts(k), float(px), [], [])


class Script:
    """呼び出し k で plan[k] の注文・見張る値段を返し、plan に無い呼び出しでは前のものを持ち越す(上の注)。
    呼ばれた ev を calls に、ev の形の誤り(stop に bar がある・鍵が違う)を bad に残す。"""

    def __init__(self, plan, signals=None, raw=False):
        self.plan, self.signals, self.raw = plan, signals or {}, raw
        self.k, self.orders, self.watches, self.done = -1, {}, [], set()
        self.calls, self.bad = [], []

    def decide(self, ev):
        self.k += 1
        want = STOP_KEYS | ({"bar"} if ev["kind"] == "close" else set())
        if set(ev) != want or any(set(f) != FILL_KEYS for f in ev["fills"]):
            self.bad.append((self.k, sorted(ev)))
        self.calls.append((ev["kind"], ev["ts"], float(ev["price"]), [(f["id"], float(f["px"]), f["case"]) for f in ev["fills"]],
                           [float(x) for x in ev["touched"]]))
        self.done |= {f["id"] for f in ev["fills"]}
        if self.k in self.plan:
            self.orders, self.watches = dict(self.plan[self.k].get("o", {})), list(self.plan[self.k].get("w", []))
        if not self.raw:
            self.orders = {i: o for i, o in self.orders.items() if i not in self.done}
        return dict(self.orders), list(self.signals.get(self.k, [])), list(self.watches)


def table(out, name):
    with open(os.path.join(out, f"{name}.csv"), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def check_all(cases, fn):
    """cases の全部に fn を当て、落ちた場面の名前と理由を全部集めてから 1 回で落とす(1 つの試験で表を回す)。"""
    bad = []
    for case in cases:
        try:
            fn(case)
        except (Exception, pytest.fail.Exception) as e:  # 例外で止まった場面も、残りの場面を回してから一緒に出す
            bad.append(f"{case['name'] if isinstance(case, dict) else case[0]}: {type(e).__name__}: {e}")
    assert not bad, f"{len(bad)} / {len(cases)} の場面が落ちた:\n" + "\n".join(bad)


def od(form, side, px=None, qty=0.009, tag=None):
    o = {"form": form, "side": side, "qty": qty}
    if px is not None:
        o["px"] = px
    if tag is not None:
        o["tag"] = tag
    return o


# 足 (始値, 高値, 安値, 終値)
Z0 = (1000, 1001, 1000, 1001)  # データの頭の陽線(始値 ≠ 終値 なので飛ばさない)。終値 1001 が次の足の「直前の終値」
BULL = (1002, 1010, 995, 1008)  # 陽線: 1001 →(飛び)1002 → 995 → 1010 → 1008
BEAR = (1002, 1010, 995, 996)  # 陰線: 1001 →(飛び)1002 → 1010 → 995 → 996
DOJI_UP = (1002, 1010, 995, 1002)  # 始値 = 終値 > 直前の終値 1001: 1002 → 1010 → 995 → 1002
DOJI_DN = (1000, 1010, 995, 1000)  # 始値 = 終値 < 直前の終値 1001: 1000 → 995 → 1010 → 1000
W2 = {0: {"w": [998, 1009]}}  # 道筋の順を見る見張る値段

SCENES = [
    # ---------------------------------------------------------------- 道筋の順(SPEC.md §2.1。U1)
    dict(name="陽線の道筋は 始値 → 安値 → 高値 → 終値", rows=[Z0, BULL], plan=W2,
         # 飛び (1001, 1002] に見張る値段なし。1002 → 995 で 998。995 → 1010 で 998・1009(戻ってきてまた届けばまた到達)。
         #   1010 → 1008 で 1009
         calls=[C(0, 1001), S(1, 998, touched=[998]), S(1, 998, touched=[998]), S(1, 1009, touched=[1009]),
                S(1, 1009, touched=[1009]), C(1, 1008)]),
    dict(name="陰線の道筋は 始値 → 高値 → 安値 → 終値", rows=[Z0, BEAR], plan=W2,
         # 1002 → 1010 で 1009。1010 → 995 で 1009・998。995 → 996 は無し
         calls=[C(0, 1001), S(1, 1009, touched=[1009]), S(1, 1009, touched=[1009]), S(1, 998, touched=[998]), C(1, 996)]),
    dict(name="始値 = 終値 で上がって始まった足は 始値 → 高値 → 安値 → 終値", rows=[Z0, DOJI_UP], plan=W2,
         # 始値 1002 > 直前の終値 1001。1002 → 1010 で 1009。1010 → 995 で 1009・998。995 → 1002 で 998
         calls=[C(0, 1001), S(1, 1009, touched=[1009]), S(1, 1009, touched=[1009]), S(1, 998, touched=[998]),
                S(1, 998, touched=[998]), C(1, 1002)]),
    dict(name="始値 = 終値 で下がって始まった足は 始値 → 安値 → 高値 → 終値", rows=[Z0, DOJI_DN], plan=W2,
         # 始値 1000 < 直前の終値 1001。飛び [1000, 1001) に無し。1000 → 995 で 998。995 → 1010 で 998・1009。1010 → 1000 で 1009
         calls=[C(0, 1001), S(1, 998, touched=[998]), S(1, 998, touched=[998]), S(1, 1009, touched=[1009]),
                S(1, 1009, touched=[1009]), C(1, 1000)]),
    # ---------------------------------------------------------------- 見張る値段の到達(SPEC.md §2.2。U1)
    dict(name="見張る値段は折り返しの点ちょうどで 1 回・刻みに切り捨ててから比べ touched は返した値のまま", rows=[Z0, BULL],
         # 995(= 安値)は 1002 → 995 の着いた点で到達。995 → 1010 は動き始めの点 995 を除くので届かない。
         #   1010.7 は切り捨てて 1010(= 高値)。995 → 1010 の着いた点で到達、touched は 1010.7。1010 → 1008 は動き始めの 1010 を除く
         plan={0: {"w": [995, 1010.7]}},
         calls=[C(0, 1001), S(1, 995, touched=[995]), S(1, 1010, touched=[1010.7]), C(1, 1008)]),
    dict(name="始値への飛び: 注文と見張る値段は始値で・逆指値は始値で(L-877 3.b)・同じ値段はまとめて 1 回",
         rows=[Z0, (1005, 1007, 1004, 1006)],
         # 飛び 1001 → 1005。売りの limit sl 1003: 始値 1005 ≥ 1003 ですでに約定する側 → 始値 1005(open)。
         #   買いの stop bs 1002.6 → 切り捨て 1002: 1005 ≥ 1002 → 始値 1005(open)。見張る値段 1003 は (1001, 1005] → 始値で到達。
         #   1001(= 直前の終値)は動き始めの点なので届かない。3 つを 1 回で呼ぶ(約定は番号を出した順 sl → bs)。
         #   売りの stop ss 1004.4 → 1004: 始値 1005 > 1004 で約定しない。1005 → 1004(安値)で動いて届く → 1004(path)。
         #   買いの limit bl 1003: 1005 → 1004 → 1007 → 1006 で 1003 に届かず約定しない
         plan={0: {"o": {"sl": od("limit", "sell", 1003.0), "bs": od("stop", "buy", 1002.6), "ss": od("stop", "sell", 1004.4),
                         "bl": od("limit", "buy", 1003.0)}, "w": [1001, 1003]}},
         calls=[C(0, 1001), S(1, 1005, [("sl", 1005, "open"), ("bs", 1005, "open")], [1003]), S(1, 1004, [("ss", 1004, "path")]),
                C(1, 1006)]),
    # ---------------------------------------------------------------- 道筋で届く順・同じ値段・切り捨て・ちょうど(SPEC.md §3。U1)
    dict(name="道筋で先に届く値段から順・同じ値段の約定と見張る値段はまとめて 1 回・値段の切り捨て・安値ちょうど", rows=[Z0, BULL],
         # 始値 1002 ではどれも約定しない。1002 → 995(下へ): 買いの limit a 999 → 999(path)。売りの stop b 997.6 → 997 と
         #   買いの limit c 997.9 → 997 と見張る値段 997 → 997 で 1 回(b → c は出した順)。買いの limit f 995 = 安値ちょうど → 995。
         #   995 → 1010(上へ): 見張る値段 997(また到達)。売りの limit d 1006 → 1006。買いの stop e 1009.5 → 1009。1010 → 1008 は無し。
         #   切り上げると b・c は 998、e は 1010 になる
         plan={0: {"o": {"a": od("limit", "buy", 999.0), "b": od("stop", "sell", 997.6), "c": od("limit", "buy", 997.9),
                         "d": od("limit", "sell", 1006.0), "e": od("stop", "buy", 1009.5), "f": od("limit", "buy", 995.0)},
                   "w": [997]}},
         calls=[C(0, 1001), S(1, 999, [("a", 999, "path")]), S(1, 997, [("b", 997, "path"), ("c", 997, "path")], [997]),
                S(1, 995, [("f", 995, "path")]), S(1, 997, touched=[997]), S(1, 1006, [("d", 1006, "path")]),
                S(1, 1009, [("e", 1009, "path")]), C(1, 1008)]),
    # ---------------------------------------------------------------- 呼んだ点ですぐ約定・取り消し(SPEC.md §2.2 の 3・4、§3。U1・U2)
    dict(name="呼んだ点で返した注文がすぐ約定するなら同じ点でもう一度呼ぶ(now。2 回目は新しい約定だけ・touched は空)・返さなかった注文はその点で取り消す", rows=[Z0, BULL],
         # 1002 → 995 で買いの limit a 999 → 999(path)と見張る値段 999 で呼ぶ(呼び出し 1)。そこで z(買いの limit 996)を
         #   返さない → 取り消し。成行 m・売りの limit x 990(999 ≥ 990)・買いの stop s 998(999 ≥ 998)はどれも 999 ですぐ約定
         #   (now)→ 同じ点で呼び出し 2。呼び出し 2 の fills は新しい約定 m・x・s だけ(a を渡し直さない)、touched は空
         #   (リードの途中の決め Q1)。呼び出し 2 で何も返さない。z は取り消したので 996 で約定しない
         plan={0: {"o": {"a": od("limit", "buy", 999.0), "z": od("limit", "buy", 996.0)}, "w": [999]},
               1: {"o": {"m": od("market", "sell"), "x": od("limit", "sell", 990.0), "s": od("stop", "buy", 998.0)}}, 2: {}},
         calls=[C(0, 1001), S(1, 999, [("a", 999, "path")], [999]),
                S(1, 999, [("m", 999, "now"), ("x", 999, "now"), ("s", 999, "now")], []), C(1, 1008)]),
    # ---------------------------------------------------------------- 成行と飛ばす足(SPEC.md §1・§3。U2・U3)
    dict(name="足が閉じたときの成行は飛ばさない次の足の始値・向きの決まらない足は戦略を呼ばず約定もさせない",
         rows=[Z0, BULL, (1008, 1015, 1000, 1008), (1012, 1014, 1011, 1013)],
         # 足 1 の終値 1008 で成行の買い m と買いの limit w 1005 を返す。足 2 は 始値 = 終値 = 直前の終値 1008 → 飛ばす
         #   (範囲 1000〜1015 に w 1005 があるが約定させない・呼ばない)。足 3 の始値 1012 で m(market)。
         #   w は 1012 → 1011 → 1014 → 1013 で届かない
         plan={1: {"o": {"m": od("market", "buy"), "w": od("limit", "buy", 1005.0)}}},
         calls=[C(0, 1001), C(1, 1008), S(3, 1012, [("m", 1012, "market")]), C(3, 1013)]),
    dict(name="データの頭の始値 = 終値 の足は値段を変えて続いても飛ばす",
         rows=[(1000, 1000, 1000, 1000), (1003, 1005, 1001, 1003), (1001, 1002, 1000, 1002), (1002, 1009, 990, 1002),
               (1004, 1006, 1003, 1005)],
         # 足 0・1 は直前に回した足が無く 始値 = 終値 → 飛ばす。足 2 が最初に回す足(呼び出し 0 で買いの limit w 995)。
         #   足 3 は 始値 = 終値 = 直前の終値 1002 → 飛ばす(範囲 990〜1009 の w を約定させない)。足 4 は 1004 → 1003 → 1006 → 1005
         plan={0: {"o": {"w": od("limit", "buy", 995.0)}}},
         calls=[C(2, 1002), C(4, 1005)]),
]

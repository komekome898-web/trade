#!/usr/bin/env python3
"""カツオの再現の参照(weak_f<足>_close_a)と段階 G の、片側にしか無い取引を 1 本ずつ、どのデータの扱いの違いで
片側だけになったかに分ける(オーナー L-618 の 4「データの扱い方がどう違うのかを基に原因を調査してください」)。

走らせは回さない。参照と段階 G の取引の記録(既存の出力)と、生の 1 分足(Binance・bitFlyer)から合図の足を作り直す。
分け方の決まり(表を見る前に、この台本と tests/research/test_c2_ref_vs_g_cause.py で固めた):

D1 範囲: 足 5・15 分。年 2019〜2022(建てた足の始まりの UTC の年。c2_ref_vs_g_match.py の R1 と同じ)。共通・参照だけ・
   段階 G だけの分け方は c2_ref_vs_g_match.py の R1・R2(鍵 = (建ての時刻, 向き))と同じで、本数は match.json と
   一致することを確かめる(一致しなければ止める)。
D2 合図の足の作り方 4 通り(Binance の 1 分足の行から、足の長さ F の時計の区切りで畳む。4 本値 = 最初の始値・最大・
   最小・最後の終値):
     none(参照)= 行を全部使う。区切り = ((t + 60 − 1) // F) × F(再現の _advance と同じ)。
     join(違い (a) だけ)= その行の分(t を分の頭に切り下げた時刻)が bitFlyer の 4 本値のある分にある行だけ。区切りは none と同じ。
     n0(違い (b) だけ)= n_trades == 0 の行を落とす。区切りは none と同じ。
     both(段階 G)= join と n0 の両方。区切りは分の頭に切り下げた時刻 // F × F(段階 G の畳み)。
   bitFlyer の「4 本値のある分」= open が空でない行(段階 G・K1 の結合の規則)。2019〜2022 年は Binance の分の頭に
   乗らない行が 0、bitFlyer の出来高 0 で 4 本値のある行が 0(この台本が数えて cause.json の data_facts に出す)なので、
   区切りの式の違い(none・join と both)と違い (e) は 2019〜2022 年の足に効かない。
D3 合図 = k1_signal(門 s19/b24、H1 あり)。行動に使う合図 = 強さが「弱い」の足の向き(+1 / −1)、それ以外と足が無い
   区切りは 0。
D4 機械(両方の写し): 足 j の終わり(= 足の始まり + F)で、1 つ前の足(その作り方の足の列で 1 つ前。隣の区切りとは
   限らない)の合図で行動する。合図 0 または持ち高と同じ向き → 何もしない。反対 → 閉じる。持ち高 0 → 入る。
   約定の値: 段階 G = 足 j の最後の結合した分の bitFlyer の終値。参照 = 行動の時刻 E 以前に終わった、出来高 > 0 の最後の
   bitFlyer の 1 分足の終値(再現の _last_close)。値が無ければ行動しない。
   写しの取引(建ての年 2019〜2022)が、既存の取引の記録と、鍵・出の時刻・損益(差 1e-5 % 以内。前の書き方で 1e-3 bp)で全部一致することを
   確かめる。一致しなければ分類を出さずに止める。
D5 1 足以内のずれの対: 参照だけ・段階 G だけ(同じ足・同じ年)のうち、同じ向きで建ての時刻の差が F 以内の組。差の小さい順、
   同じなら早い順に 1 対 1 で組む。対は別の表で数え、組まれなかった取引だけを D6〜D8 で分ける。対の原因の列は、
   参照の側の取引に D6〜D8 を当てたもの。
D6 1 本の取引 X(片側 P にあり、もう片側 Q に無い。建ての時刻 E・向き s)の入りの行動を、次の順で見る。W = P の足の列で
   E に終わる足の 1 つ前の足の区切り(X の合図の足)。P の作り方で W の合図が s でなければ、写しの不一致として止める。
   (A) 合図の違い: Q の作り方で W の合図が s でない(足が無いを含む)。
   (B) 行動の時刻の違い: Q の作り方で W の次の足の終わりが E でない。
   (C) 持ち高の違い: (A)(B) のどちらでもなく、E の直前の持ち高が P と Q で違う。
   (A)(B)(C) のどれでもない → 不明。
D7 (A)・(B) の帰属: 比べる値 v(作り方)= (A) では W の合図、(B) では W の次の足の終わり。P の作り方から (a) の扱い
   (結合する / しない)だけを Q に替えた作り方を Pa、(b) の扱い(n_trades == 0 を落とす / 落とさない)だけを替えた
   作り方を Pb とする。
     v(Pa) = v(Q) で v(Pb) ≠ v(Q) → (a)。v(Pb) = v(Q) で v(Pa) ≠ v(Q) → (b)。
     両方 = v(Q) → 「(a)・(b) のどちらでも」。どちらも ≠ v(Q)(両方を替えて初めて Q になる)→ 「(a)+(b) の組」。
D8 (C) の元: P と Q の行動の時刻を合わせた列で、E より前に、持ち高が最後に P と Q で同じだった時刻の次の時刻 t* を
   探す(t* から E の直前まで持ち高が違い続ける)。t* に持ち高を変えた側(参照を先に見る)の行動に D6 の (A)(B) と
   D7 を当て、「持ち高を経て (a)」などとする。t* に (A)(B) が無ければ、もう片側の t* の行動を見る。それでも無ければ不明。
   読み始めまで持ち高が違い続けたら「その他(読み始めから)」。
D9 違い (c)(約定に使う bitFlyer の足)は、両方の機械で行動の判断に値を使わない(D4)ので、取引の有無を変えない。
   片側だけの取引の表の (c) の列は、この理由で 0 と決まる(数えた結果ではなく決まり)。(c) が効く所は共通の取引の損益で、
   補いの表で数える: 共通の取引(D1 の鍵が同じ)を「出の時刻も同じ」と「出の時刻が違う」に分ける。
   出の時刻も同じ: 損益の差(参照 − 段階 G)を入りの値の差の分(参照の損益 − 段階 G の入りの値と参照の出の値の損益)と
   出の値の差の分(残り)に分ける(恒等式)。値が違う脚ごとに、参照の値の分 mR と段階 G の値の分 mG を比べ、
   mR > mG で mR が Binance に無い → 「(c): Binance にその分が無い」、mR の n_trades == 0 → 「(c): n_trades == 0」、
   mR < mG → 「(e) または不明」、それ以外 → 不明。
   出の時刻が違う: 早く出た側の出の行動に D6 の (A)(B) と D7 を当てる(入りが同じなので直前の持ち高は同じ)。
D10 違い (d)(期間の終わりの閉じ方)は 2023 年 12 月の取引だけに効くので、この範囲(建ての年 2019〜2022)には出ない。
   2022 年に建てて 2023 年 2 月 1 日までに出ない取引があれば、その本数を cause.json に出す。

データの読み: Binance・bitFlyer とも 2017〜2023 年のファイルを、2023-02-01T00:00Z 以降の行に来たところで読むのを止める
(封印の境 2023-12-18 より前)。参照の行は 2017-08-17T15:00Z から(参照の期間の始まり)、段階 G の行はファイルの最初
から。

出力: limit_sim/runs/READ_K1YEAR/cause.json と CAUSE_TABLES1.md。

    PYTHONPATH=src python3 scripts/w4_measure/c2_ref_vs_g_cause.py
"""
from __future__ import annotations

import bisect
import csv
import gzip
import json
import math
import os
import sys
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "src"))

import c2_ref_vs_g_match as mm  # noqa: E402

from bot.research.katsuo_limit_sim import k1_signal  # noqa: E402

RUNS = mm.RUNS
OUT_DIR = os.path.join(RUNS, "READ_K1YEAR")
BIN_DIR = os.path.join(REPO, "backtest_data", "binance_BTCUSDT_1m_20170801_20231231")
BF_DIR = os.path.join(REPO, "backtest_data", "bitflyer_lightchart_FX_BTC_JPY_1m_20260906")
FEET = mm.FEET
YEARS = mm.YEARS
NS = 10**9
REF_LO = 1502982000  # 2017-08-17T15:00:00Z(参照の期間の始まり)
READ_HI = 1675209600  # 2023-02-01T00:00:00Z(ここで読むのを止める)

# 作り方 = (結合する, n_trades == 0 を落とす)
NONE, JOIN, N0, BOTH = (False, False), (True, False), (False, True), (True, True)
CONS_NAME = {NONE: "none", JOIN: "join", N0: "n0", BOTH: "both"}
PIPE = {"ref": NONE, "g": BOTH}

CAT_A, CAT_B, CAT_AB_ANY, CAT_AB_PAIR = "(a)", "(b)", "(a)・(b) のどちらでも", "(a)+(b) の組"
KIND_SIG, KIND_TIME, KIND_POS = "合図の違い", "行動の時刻の違い", "持ち高の違い"
OTHER_START, UNKNOWN = "その他(読み始めから)", "不明"


# ---------------------------------------------------------------------------- 読み込み
def load_binance(lo: int, hi: int) -> dict:
    """Binance 1 分足 (t 秒, o, h, l, c, n_trades)。t >= hi の行に来たら止める。"""
    ts, o, h, lo_, c, nt = [], [], [], [], [], []
    for y in range(2017, 2024):
        p = os.path.join(BIN_DIR, f"binance_BTCUSDT_1m_{y}.csv.gz")
        stop = False
        with gzip.open(p, "rt", newline="") as fh:
            r = csv.reader(fh)
            head = next(r)
            assert head[:5] == ["open_time", "open", "high", "low", "close"] and head[7] == "n_trades", head
            for row in r:
                t = int(datetime.fromisoformat(row[0]).timestamp())
                if t >= hi:
                    stop = True
                    break
                if t < lo:
                    continue
                ts.append(t); o.append(float(row[1])); h.append(float(row[2])); lo_.append(float(row[3]))
                c.append(float(row[4])); nt.append(int(row[7]))
        if stop:
            break
    a = {"t": np.array(ts, dtype=np.int64), "o": np.array(o), "h": np.array(h), "l": np.array(lo_),
         "c": np.array(c), "nt": np.array(nt, dtype=np.int64)}
    assert np.all(np.diff(a["t"]) > 0), "Binance の行の時刻が増えていない"
    return a


def load_bitflyer(lo: int, hi: int) -> dict:
    """bitFlyer FX_BTC_JPY 1 分足のうち 4 本値のある行 (t 秒, 終値, 出来高)。t >= hi の行に来たら止める。"""
    ts, c, v = [], [], []
    for y in range(2017, 2024):
        p = os.path.join(BF_DIR, f"candles_1m_{y}.csv.gz")
        stop = False
        with gzip.open(p, "rt", newline="") as fh:
            r = csv.reader(fh)
            head = next(r)
            assert head[:6] == ["ts", "open", "high", "low", "close", "volume"], head
            for row in r:
                t = int(datetime.fromisoformat(row[0]).timestamp())
                if t >= hi:
                    stop = True
                    break
                if t < lo or row[1] == "":
                    continue
                ts.append(t); c.append(float(row[4])); v.append(float(row[5]))
        if stop:
            break
    a = {"t": np.array(ts, dtype=np.int64), "c": np.array(c), "v": np.array(v)}
    assert np.all(np.diff(a["t"]) > 0), "bitFlyer の行の時刻が増えていない"
    return a


# ---------------------------------------------------------------------------- D2・D3 合図の足
def build_bars(b: dict, bf_t: np.ndarray, F: int, cons: tuple, lo: int) -> dict:
    """作り方 cons の足の列。w = 区切りの始まり(秒)、act = 行動に使う合図、last = 足の最後の分(分の頭)。"""
    join, drop0 = cons
    t = b["t"]
    m = t >= lo
    fl = t - t % 60
    if join:
        m &= np.isin(fl, bf_t)
    if drop0:
        m &= b["nt"] > 0
    t, fl = t[m], fl[m]
    o, h, l, c = b["o"][m], b["h"][m], b["l"][m], b["c"][m]
    if cons == BOTH:
        w = fl // F * F
    else:
        w = (t + 60 - 1) // F * F
    if len(w) == 0:
        return {"w": np.zeros(0, dtype=np.int64), "act": np.zeros(0, dtype=np.int64), "last": np.zeros(0, dtype=np.int64),
                "F": F, "idx": {}}
    starts = np.flatnonzero(np.r_[True, w[1:] != w[:-1]])
    ends = np.r_[starts[1:], len(w)] - 1
    bo, bh, bl, bc = o[starts], np.maximum.reduceat(h, starts), np.minimum.reduceat(l, starts), c[ends]
    act = np.zeros(len(starts), dtype=np.int64)
    for j in range(len(starts)):
        sig, _lc, _cs, strength, _s, _b, _f = k1_signal(float(bo[j]), float(bh[j]), float(bl[j]), float(bc[j]), True)
        if sig != 0 and strength == "weak":
            act[j] = sig
    ww = w[starts]
    return {"w": ww, "act": act, "last": fl[ends], "F": F, "idx": {int(x): j for j, x in enumerate(ww)}}


def sig_at(bars: dict, w: int) -> int:
    j = bars["idx"].get(int(w))
    return 0 if j is None else int(bars["act"][j])


def next_end(bars: dict, w: int):
    """区切り w の次の足の終わり(無ければ None)。"""
    j = int(np.searchsorted(bars["w"], w, side="right"))
    return None if j >= len(bars["w"]) else int(bars["w"][j]) + bars["F"]


def signal_window(bars: dict, E: int):
    """E に終わる足の 1 つ前の足の区切り(E に終わる足が無い、または 1 つ前が無ければ None)。"""
    j = bars["idx"].get(int(E) - bars["F"])
    return None if (j is None or j == 0) else int(bars["w"][j - 1])


# ---------------------------------------------------------------------------- D4 機械
def machine(bars: dict, price_at) -> tuple[list, list]:
    """(取引 [(建て E 秒, 向き, 出 E 秒, 入りの値, 出の値)], 持ち高の動き [(時刻, 後の持ち高)])。"""
    pos, ent, ep = 0, None, None
    trades, states = [], []
    w, act, F = bars["w"], bars["act"], bars["F"]
    for j in range(1, len(w)):
        a = int(act[j - 1])
        if a == 0 or pos == a:
            continue
        p = price_at(j)
        if p is None:
            continue
        E = int(w[j]) + F
        if pos == -a:
            trades.append((ent, pos, E, ep, p))
            pos = 0
        else:
            pos, ent, ep = a, E, p
        states.append((E, pos))
    return trades, states


def g_price_fn(bars: dict, bf: dict):
    tt, cc = bf["t"], bf["c"]

    def f(j):
        k = int(np.searchsorted(tt, bars["last"][j]))
        assert k < len(tt) and tt[k] == bars["last"][j], "段階 G の足の最後の分が bitFlyer に無い"
        return float(cc[k])
    return f


def ref_price_minute(bfv_t: np.ndarray, E: int):
    """参照の約定の分 = E − 60 以下で始まる出来高 > 0 の最後の bitFlyer の分(無ければ None)。"""
    k = int(np.searchsorted(bfv_t, E - 60, side="right")) - 1
    return None if k < 0 else k


def ref_price_fn(bars: dict, bfv: dict):
    def f(j):
        k = ref_price_minute(bfv["t"], int(bars["w"][j]) + bars["F"])
        return None if k is None else float(bfv["c"][k])
    return f


def pos_before(states: list, times: list, E: int) -> int:
    """時刻 E の行動の直前の持ち高(E より前の最後の動きの後)。"""
    k = bisect.bisect_left(times, E) - 1
    return 0 if k < 0 else states[k][1]


def pos_after(states: list, times: list, t: int) -> int:
    k = bisect.bisect_right(times, t) - 1
    return 0 if k < 0 else states[k][1]


# ---------------------------------------------------------------------------- D6〜D8 分類
def attribute(v: dict, P: tuple, Q: tuple) -> str:
    """D7。v = 作り方 -> 値。P・Q は作り方(結合, n0)。"""
    Pa, Pb = (Q[0], P[1]), (P[0], Q[1])
    fa, fb = v[Pa] == v[Q], v[Pb] == v[Q]
    if fa and fb:
        return CAT_AB_ANY
    if fa:
        return CAT_A
    if fb:
        return CAT_B
    return CAT_AB_PAIR


def classify_action(world: dict, P: str, E: int, side: int):
    """D6 の (A)(B) と D7。P の時刻 E の行動(合図の向き side)。(種類, 帰属) か None。"""
    Q = "g" if P == "ref" else "ref"
    cP, cQ = PIPE[P], PIPE[Q]
    W = signal_window(world[cP], E)
    if W is None or sig_at(world[cP], W) != side:
        raise RuntimeError(f"写しの不一致: {P} の時刻 {E} の行動に、向き {side} の合図の足が無い")
    if sig_at(world[cQ], W) != side:
        return KIND_SIG, attribute({c: sig_at(world[c], W) for c in world}, cP, cQ)
    if next_end(world[cQ], W) != E:
        return KIND_TIME, attribute({c: next_end(world[c], W) for c in world}, cP, cQ)
    return None


def action_side(states: list, times: list, t: int) -> int:
    """時刻 t の行動の合図の向き(入り = 後の持ち高、閉じる = 前の持ち高の反対)。"""
    before, after = pos_before(states, times, t), pos_after(states, times, t)
    return after if after != 0 else -before


def origin_time(st: dict, E: int):
    """D8 の t*(無ければ None)。st[p] = (states, times)。"""
    ts = sorted(set(t for p in st for t in st[p][1] if t < E))
    k = len(ts) - 1
    if k < 0:
        return None
    if pos_after(*st["ref"], ts[k]) == pos_after(*st["g"], ts[k]):
        return "same"
    while k >= 0 and pos_after(*st["ref"], ts[k]) != pos_after(*st["g"], ts[k]):
        k -= 1
    return None if k < 0 else ts[k + 1]


def classify_trade(world: dict, st: dict, P: str, E: int, side: int) -> dict:
    """D6〜D8。st[p] = (states, times)。"""
    r = classify_action(world, P, E, side)
    if r is not None:
        return {"kind": r[0], "cause": r[1], "via_pos": False}
    Q = "g" if P == "ref" else "ref"
    if pos_before(*st[P], E) == pos_before(*st[Q], E):
        return {"kind": UNKNOWN, "cause": UNKNOWN, "via_pos": False}
    t0 = origin_time(st, E)
    if t0 is None:
        return {"kind": KIND_POS, "cause": OTHER_START, "via_pos": True}
    if t0 == "same":
        return {"kind": UNKNOWN, "cause": UNKNOWN, "via_pos": False}
    for p in ("ref", "g"):
        times = st[p][1]
        i = bisect.bisect_left(times, t0)
        if not (i < len(times) and times[i] == t0):
            continue  # t* にこの側は動いていない
        r = classify_action(world, p, t0, action_side(*st[p], t0))
        if r is not None:
            return {"kind": KIND_POS, "cause": r[1], "via_pos": True, "origin_kind": r[0], "origin_t": t0,
                    "origin_side": p}
    return {"kind": KIND_POS, "cause": UNKNOWN, "via_pos": True, "origin_t": t0}


# ---------------------------------------------------------------------------- D1・D5 突き合わせ
def split_year(ref: list, g: list) -> tuple[list, list, list]:
    """c2_ref_vs_g_match.match_year と同じ規則で (共通の対, 参照だけ, 段階 G だけ)。"""
    def bykey(ts):
        d: dict = {}
        for t in sorted(ts):
            d.setdefault((t[0], t[1]), []).append(t)
        return d
    R, G = bykey(ref), bykey(g)
    common, r_only, g_only = [], [], []
    for k in sorted(set(R) | set(G)):
        a, b = R.get(k, []), G.get(k, [])
        n = min(len(a), len(b))
        common += list(zip(a[:n], b[:n]))
        r_only += a[n:]
        g_only += b[n:]
    return common, r_only, g_only


def pair_shifts(r_only: list, g_only: list, F_ns: int) -> tuple[list, list, list]:
    """D5。(対 [(参照の取引, 段階 G の取引)], 残りの参照だけ, 残りの段階 G だけ)。取引 = (建て ns, 向き, 出 ns, 損益)。"""
    cand = []
    for i, r in enumerate(r_only):
        for k, g in enumerate(g_only):
            d = abs(r[0] - g[0])
            if r[1] == g[1] and 0 < d <= F_ns:
                cand.append((d, min(r[0], g[0]), r[0], i, k))
    cand.sort()
    ur, ug, pairs = set(), set(), []
    for _d, _m, _r, i, k in cand:
        if i in ur or k in ug:
            continue
        ur.add(i); ug.add(k)
        pairs.append((r_only[i], g_only[k]))
    return (pairs, [r for i, r in enumerate(r_only) if i not in ur], [g for k, g in enumerate(g_only) if k not in ug])


def leg_cause(b: dict, bfv_t: np.ndarray, g_bars: dict, E: int) -> str:
    """D9 の脚の値の違いの元。E = 行動の時刻(秒)。"""
    k = ref_price_minute(bfv_t, E)
    mR = None if k is None else int(bfv_t[k])
    j = g_bars["idx"].get(E - g_bars["F"])
    mG = None if j is None else int(g_bars["last"][j])
    if mR is None or mG is None:
        return UNKNOWN
    if mR > mG:
        kb = int(np.searchsorted(b["fl"], mR))
        if kb >= len(b["fl"]) or b["fl"][kb] != mR:
            return "(c): Binance にその分が無い"
        if b["nt"][kb] == 0:
            return "(c): n_trades == 0"
        return UNKNOWN
    if mR < mG:
        return "(e) または不明"
    return UNKNOWN


# ---------------------------------------------------------------------------- 本体
def pnl(side: int, a: float, b: float) -> float:
    """量 1 の取引の損益(%)= 向き × (出 / 入 − 1) × 100。取引の記録(pnl_pct)と同じ単位(L-920)。"""
    return side * (b / a - 1.0) * 100


def main() -> int:
    cells = json.load(open(os.path.join(mm.G_DIR, "cells.json"), encoding="utf-8"))
    match = json.load(open(os.path.join(OUT_DIR, "match.json"), encoding="utf-8"))
    b = load_binance(0, READ_HI)
    b["fl"] = b["t"] - b["t"] % 60
    bf = load_bitflyer(0, READ_HI)
    bfv = {"t": bf["t"][bf["v"] > 0], "c": bf["c"][bf["v"] > 0]}
    bfv_ref = {"t": bfv["t"][bfv["t"] >= REF_LO], "c": bfv["c"][bfv["t"] >= REF_LO]}
    facts = {}
    for y in YEARS:
        lo = int(datetime(y, 1, 1, tzinfo=timezone.utc).timestamp())
        hi = int(datetime(y + 1, 1, 1, tzinfo=timezone.utc).timestamp())
        mb = (b["t"] >= lo) & (b["t"] < hi)
        mf = (bf["t"] >= lo) & (bf["t"] < hi)
        facts[str(y)] = {"binance_rows": int(mb.sum()), "binance_off_minute": int((b["t"][mb] % 60 != 0).sum()),
                         "binance_n_trades_0": int((b["nt"][mb] == 0).sum()),
                         "binance_minutes_not_in_bitflyer": int((~np.isin(b["fl"][mb], bf["t"])).sum()),
                         "bitflyer_rows_with_ohlc": int(mf.sum()),
                         "bitflyer_volume_le0_with_ohlc": int((bf["v"][mf] <= 0).sum())}
    out = {"data_facts": facts, "feet": {}}
    for f in FEET:
        F = f * 60
        world = {}
        for cons in (NONE, JOIN, N0, BOTH):
            world[cons] = build_bars(b, bf["t"], F, cons, REF_LO if cons != BOTH else 0)
        rep = {"ref": machine(world[NONE], ref_price_fn(world[NONE], bfv_ref)),
               "g": machine(world[BOTH], g_price_fn(world[BOTH], bf))}
        st = {p: (rep[p][1], [x[0] for x in rep[p][1]]) for p in rep}
        # 既存の取引の記録
        with gzip.open(os.path.join(RUNS, f"weak_f{f}_close_a", "trades.json.gz"), "rt", encoding="utf-8") as fh:
            ref_file = mm.ref_trades(json.load(fh))
        rid = cells[f"design|full|{f}|s19/b24|weak"]["run_id"]
        with gzip.open(os.path.join(mm.G_RUNS, rid, "trades.json.gz"), "rt", encoding="utf-8") as fh:
            g_file = mm.g_trades(json.load(fh)["data"])
        # D4 写しの確かめ
        check = {}
        for p, file_tr in (("ref", ref_file), ("g", g_file)):
            mine = {}
            for (e, s, x, a, bb) in rep[p][0]:
                mine.setdefault((e * NS, s), []).append((x * NS, pnl(s, a, bb)))
            fil = [t for t in file_tr if mm.year_of(t[0], f) in YEARS]
            bad = {"missing_in_replica": 0, "exit_differs": 0, "pnl_differs": 0}
            used = set()
            for t in fil:
                lst = mine.get((t[0], t[1]))
                if not lst:
                    bad["missing_in_replica"] += 1
                    continue
                used.add((t[0], t[1]))
                x, pv = lst[0]
                if x != t[2]:
                    bad["exit_differs"] += 1
                elif abs(pv - t[3]) > 1e-5:  # %(前の 1e-3 bp と同じ幅)
                    bad["pnl_differs"] += 1
            extra = sum(1 for k in mine if mm.year_of(k[0], f) in YEARS and k not in used)
            bad["extra_in_replica"] = extra
            bad["file_trades"] = len(fil)
            check[p] = bad
        open_after = sum(1 for t in g_file if mm.year_of(t[0], f) in YEARS and t[2] >= READ_HI * NS)
        open_after += sum(1 for t in ref_file if mm.year_of(t[0], f) in YEARS and t[2] >= READ_HI * NS)
        fo = {"replica_check": check, "trades_open_after_read_hi": open_after, "years": {}}
        out["feet"][str(f)] = fo
        if any(v for p in check for k, v in check[p].items() if k != "file_trades"):
            print(f"止める: {f} 分の写しが既存の取引の記録と一致しない {check}")
            fo["stopped"] = True
            continue
        for y in YEARS:
            R = [t for t in ref_file if mm.year_of(t[0], f) == y]
            G = [t for t in g_file if mm.year_of(t[0], f) == y]
            common, r_only, g_only = split_year(R, G)
            mref = match[f"{f}|{y}"]
            if (len(common), len(r_only), len(g_only)) != (mref["common_n"], mref["r_only_n"], mref["g_only_n"]):
                raise SystemExit(f"止める: {f}|{y} の本数が match.json と違う")
            pairs, r_rest, g_rest = pair_shifts(r_only, g_only, F * NS)
            rows = []
            for P, lst in (("ref", r_rest), ("g", g_rest)):
                for t in lst:
                    c = classify_trade(world, st, P, t[0] // NS, t[1])
                    rows.append(dict(c, side_of=P, entry_t=t[0] // NS, dir=t[1], pnl_pct=t[3]))
            prow = []
            for r, g in pairs:
                c = classify_trade(world, st, "ref", r[0] // NS, r[1])
                prow.append(dict(c, ref_entry_t=r[0] // NS, g_entry_t=g[0] // NS, dir=r[1], ref_pnl_pct=r[3],
                                 g_pnl_pct=g[3]))
            # D9 共通の取引
            com = {"same_exit": {"n": 0, "n_price_differs": 0, "diff_pct": 0.0, "entry_part_pct": 0.0,
                                 "exit_part_pct": 0.0, "legs": {}},
                   "exit_differs": {"n": 0, "diff_pct": 0.0, "by": {}}}
            for r, g in common:
                if r[2] == g[2]:
                    s = com["same_exit"]
                    s["n"] += 1
                    ref_px = ref_px_of(world[NONE], bfv_ref, r)
                    g_px = g_px_of(world[BOTH], bf, g)
                    d = r[3] - g[3]
                    s["diff_pct"] += d
                    e_part = pnl(r[1], ref_px[0], ref_px[1]) - pnl(r[1], g_px[0], ref_px[1])
                    s["entry_part_pct"] += e_part
                    s["exit_part_pct"] += d - e_part
                    if ref_px != g_px:
                        s["n_price_differs"] += 1
                    for leg, E, pa, pb, part in (("入り", r[0] // NS, ref_px[0], g_px[0], e_part),
                                                 ("出", r[2] // NS, ref_px[1], g_px[1], d - e_part)):
                        if pa != pb:
                            k = f"{leg}: {leg_cause(b, bfv_ref['t'], world[BOTH], E)}"
                            z = s["legs"].setdefault(k, {"n": 0, "part_pct": 0.0})
                            z["n"] += 1
                            z["part_pct"] += part
                else:
                    s = com["exit_differs"]
                    s["n"] += 1
                    d = r[3] - g[3]
                    s["diff_pct"] += d
                    P = "ref" if r[2] < g[2] else "g"
                    Ex = min(r[2], g[2]) // NS
                    c = classify_action(world, P, Ex, -r[1])
                    key = f"{'参照' if P == 'ref' else '段階 G'}が先に出た: " + (
                        UNKNOWN if c is None else f"{c[0]} {c[1]}")
                    z = s["by"].setdefault(key, {"n": 0, "diff_pct": 0.0})
                    z["n"] += 1
                    z["diff_pct"] += d
            fo["years"][str(y)] = {"rows": rows, "pairs": prow, "common": com,
                                   "match": {"common_n": len(common), "r_only_n": len(r_only), "g_only_n": len(g_only),
                                             "diff_pct": math.fsum(t[3] for t in R) - math.fsum(t[3] for t in G)}}
    with open(os.path.join(OUT_DIR, "cause.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    write_md(out)
    print(f"-> {OUT_DIR}/cause.json, CAUSE_TABLES1.md")
    return 0


def ref_px_of(bars: dict, bfv: dict, t: tuple) -> tuple:
    """参照の取引の入り・出の値を、写しの規則(D4)で引き直す。"""
    out = []
    for E in (t[0] // NS, t[2] // NS):
        k = ref_price_minute(bfv["t"], E)
        out.append(float(bfv["c"][k]))
    return tuple(out)


def g_px_of(bars: dict, bf: dict, t: tuple) -> tuple:
    out = []
    for E in (t[0] // NS, t[2] // NS):
        j = bars["idx"][E - bars["F"]]
        k = int(np.searchsorted(bf["t"], bars["last"][j]))
        out.append(float(bf["c"][k]))
    return tuple(out)


# ---------------------------------------------------------------------------- 表
COLS = [(CAT_A, False), (CAT_B, False), (CAT_AB_ANY, False), (CAT_AB_PAIR, False),
        (CAT_A, True), (CAT_B, True), (CAT_AB_ANY, True), (CAT_AB_PAIR, True)]


def cell(rows):
    return f"{len(rows)} / {math.fsum(r['pnl_pct'] for r in rows):+,.4f}" if rows else "0"


def write_md(out: dict) -> None:
    L = ["# カツオ: 参照と段階 G の片側だけの取引の分類(台本の出力)", "",
         "`PYTHONPATH=src python3 scripts/w4_measure/c2_ref_vs_g_cause.py` が出した。分け方の決まり D1〜D10 は台本の docstring。"
         "升 = 本数 / 損益の和(%、経費の前)。年 = 建てた足の始まりの年。", ""]
    L += ["## 0. データの事実(D2)", "", "| 年 | Binance の行 | 分の頭に無い行 | n_trades == 0 | bitFlyer に 4 本値の無い分の Binance の行 | "
          "bitFlyer の 4 本値のある行 | そのうち出来高 ≤ 0 |", "|---|---|---|---|---|---|---|"]
    for y, d in out["data_facts"].items():
        L.append(f"| {y} | {d['binance_rows']:,} | {d['binance_off_minute']:,} | {d['binance_n_trades_0']:,} | "
                 f"{d['binance_minutes_not_in_bitflyer']:,} | {d['bitflyer_rows_with_ohlc']:,} | "
                 f"{d['bitflyer_volume_le0_with_ohlc']:,} |")
    L += ["", "## 1. 写しの確かめ(D4)", "", "| 足 | 側 | 記録の取引(2019〜2022 に建てた) | 写しに無い | 出の時刻が違う | 損益が違う | 写しにだけある |",
          "|---|---|---|---|---|---|---|"]
    for f, fo in out["feet"].items():
        for p, c in fo["replica_check"].items():
            L.append(f"| {f} 分 | {'参照' if p == 'ref' else '段階 G'} | {c['file_trades']:,} | {c['missing_in_replica']} | "
                     f"{c['exit_differs']} | {c['pnl_differs']} | {c['extra_in_replica']} |")
        L.append(f"| {f} 分 | 2023-02-01 までに出ていない取引 | {fo['trades_open_after_read_hi']} | | | | |")
    L += ["", "## 2. 1 足以内のずれの対(D5)", "",
          "| 足 | 年 | 対 | 参照の側の和 | 段階 G の側の和 | 差(参照 − 段階 G) | 参照の側の原因(D6〜D8) |", "|---|---|---|---|---|---|---|"]
    for f, fo in out["feet"].items():
        for y, yo in fo.get("years", {}).items():
            ps = yo["pairs"]
            rs, gs = math.fsum(p["ref_pnl_pct"] for p in ps), math.fsum(p["g_pnl_pct"] for p in ps)
            cnt: dict = {}
            for p in ps:
                k = f"{p['kind']} {p['cause']}" if not p["via_pos"] else f"持ち高を経て {p['cause']}"
                cnt[k] = cnt.get(k, 0) + 1
            L.append(f"| {f} 分 | {y} | {len(ps)} | {rs:+,.4f} | {gs:+,.4f} | {rs - gs:+,.4f} | "
                     + "・".join(f"{k} {v}" for k, v in sorted(cnt.items())) + " |")
    L += ["", "## 3. 対を除いた片側だけの取引の分類(D6〜D9)", "",
          "「直接」= その取引の入りの行動に (A) 合図の違い・(B) 行動の時刻の違いがある。「持ち高を経て」= (C)、元(D8)の帰属。"
          "(c) の列は D9 の決まりで 0。", ""]
    hdr = ["足", "年", "側", "取引"] + [f"直接 {c}" for c, v in COLS if not v] + [f"持ち高を経て {c}" for c, v in COLS if v] + [
        "(c)", OTHER_START, UNKNOWN, "片側の和"]
    L += ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
    for f, fo in out["feet"].items():
        for y, yo in fo.get("years", {}).items():
            for P in ("ref", "g"):
                rows = [r for r in yo["rows"] if r["side_of"] == P]
                cs = [cell([r for r in rows if r["cause"] == c and r["via_pos"] == v]) for c, v in COLS]
                cs += ["0", cell([r for r in rows if r["cause"] == OTHER_START]),
                       cell([r for r in rows if r["cause"] == UNKNOWN])]
                L.append(f"| {f} 分 | {y} | {'参照だけ' if P == 'ref' else '段階 G だけ'} | {len(rows)} | " + " | ".join(cs)
                         + f" | {math.fsum(r['pnl_pct'] for r in rows):+,.4f} |")
    L += ["", "### 3-1 直接の取引の (A)・(B) の内訳(本数)", "", "| 足 | 年 | 側 | 合図の違い | 行動の時刻の違い | 持ち高の元が合図 | 持ち高の元が時刻 |",
          "|---|---|---|---|---|---|---|"]
    for f, fo in out["feet"].items():
        for y, yo in fo.get("years", {}).items():
            for P in ("ref", "g"):
                rows = [r for r in yo["rows"] if r["side_of"] == P]
                L.append(f"| {f} 分 | {y} | {'参照だけ' if P == 'ref' else '段階 G だけ'} | "
                         f"{sum(1 for r in rows if r['kind'] == KIND_SIG)} | {sum(1 for r in rows if r['kind'] == KIND_TIME)} | "
                         f"{sum(1 for r in rows if r.get('origin_kind') == KIND_SIG)} | "
                         f"{sum(1 for r in rows if r.get('origin_kind') == KIND_TIME)} |")
    L += ["", "## 4. 共通の取引(D9 の補い)", "",
          "| 足 | 年 | 出も同じ | そのうち値が違う | 差の和 | うち入りの値の分 | うち出の値の分 | 値の違いの元(脚: 本数 / 分の和) | 出が違う | 差の和 | 早く出た側の行動の原因(本数 / 差の和) |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for f, fo in out["feet"].items():
        for y, yo in fo.get("years", {}).items():
            s, x = yo["common"]["same_exit"], yo["common"]["exit_differs"]
            legs = "・".join(f"{k} {v['n']} / {v['part_pct']:+,.4f}" for k, v in sorted(s["legs"].items()))
            by = "・".join(f"{k} {v['n']} / {v['diff_pct']:+,.4f}" for k, v in sorted(x["by"].items()))
            L.append(f"| {f} 分 | {y} | {s['n']:,} | {s['n_price_differs']:,} | {s['diff_pct']:+,.4f} | {s['entry_part_pct']:+,.4f} | "
                     f"{s['exit_part_pct']:+,.4f} | {legs} | {x['n']} | {x['diff_pct']:+,.4f} | {by} |")
    L += ["", "## 5. 恒等式の照合", "", "| 足 | 年 | 差(参照 − 段階 G) | 対の差 + 片側の和の差 + 共通の差 | 本数 共通 / 参照だけ / 段階 G だけ(match.json と同じ) |",
          "|---|---|---|---|---|"]
    for f, fo in out["feet"].items():
        for y, yo in fo.get("years", {}).items():
            ps = yo["pairs"]
            pd = math.fsum(p["ref_pnl_pct"] - p["g_pnl_pct"] for p in ps)
            rr = math.fsum(r["pnl_pct"] for r in yo["rows"] if r["side_of"] == "ref")
            gg = math.fsum(r["pnl_pct"] for r in yo["rows"] if r["side_of"] == "g")
            cd = yo["common"]["same_exit"]["diff_pct"] + yo["common"]["exit_differs"]["diff_pct"]
            m = yo["match"]
            L.append(f"| {f} 分 | {y} | {m['diff_pct']:+,.4f} | {pd + rr - gg + cd:+,.4f} | "
                     f"{m['common_n']:,} / {m['r_only_n']} / {m['g_only_n']} |")
    with open(os.path.join(OUT_DIR, "CAUSE_TABLES1.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    sys.exit(main())

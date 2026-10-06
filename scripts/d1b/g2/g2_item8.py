"""# 8(カード 8 セッション内の平均回帰): 値段がセッションの平均から離れた後、その後の値動きは平均へ戻る向きか。

D1B_FRAMINGS.md # 8 の行: 何を何通り = 時間 4(1・5・15・60 分)× 区切り 24 通り(毎時ずらす)。起点は約定の値段(次の足の
始値)と中ほどの値の 2 通りで、1 分目を除いた戻りも出す。離れてから平均をまたぐまでの時間の分布 / 何を 1 件 = 1 日 × 1 分
(区間は日の塊)/ データ = bitFlyer FX の 1 分足 / 対照 = 24 時間前と後(合図が経路で決まるので両方)。
注: 区切り 24 通りは市場のデータの読みで、カード 8 を 24 通り走らせる走らせとは別(行の注)。
カードの分析の文書 docs/ANALYSIS/2026-10-05_card8_session_mean_revert.md の P: 各分の「終値 − セッションの平均」の符号と、
その後 1・5・15・60 分の値動きの符号の一致の割合と相関。離れてから平均をまたぐまでの時間の分布。

量の作り方(セッションの数え方はカード src/bot/research/cards/library/c8_session_mean_revert.py の session_index を import):
- 区切り h(h = 0〜23): セッションの始まり = UTC の h 時。offset = (24 − h) mod 24 時間(jst_day = h 15、bf_maint = h 19 と同じ)。
  足 [s, s + 60 秒) は session_index(s, offset) のセッション。
- 平均 = そのセッションの、t までの(t の足を含む)決定の足の終値の算術平均(カードと同じ)。離れ dev = ln(終値_t ÷ 平均)(bp)。
  合図 = −sign(dev)(平均へ戻る向き)。セッションの最後の足(t がセッションの終わり)と dev = 0 の分は数えない(カードは 0 を持つ)。
- 時間 H 分の値動き(起点 2 通り。カード 8 の redo2 の c8_redo.py と同じ作り):
  約定: ln(始値[出の足] ÷ 始値[約定の足])。約定の足 = 始まりが t 以上の最初の決定の足、出の足 = 始まりが t + H 分 以上の最初の決定の足。
  中ほど: 同じ 2 本の足の (高値 + 安値) ÷ 2 の比。
  1 分目を除いた戻り: 起点の足を「始まりが t + 1 分 以上の最初の決定の足」にした同じ量(H = 1 は無いので出さない)。
- 一致 = 値動き ≠ 0 で sign(値動き) == 合図。分母 = 値動き ≠ 0 の分。相関 = dev と値動き(符号を掛けない生の値)の
  ピアソンの相関(平均へ戻るなら負)。
- 対照: 同じ分の合図と dev を、t − 24 時間・t + 24 時間 の分からの同じ量(足の決め方も同じ)に当てる。
- 平均をまたぐまでの分: t の後、同じセッションの決定の足で sign(終値 − 平均) が sign(dev_t) と違う(0 を含む)最初の足の
  終わり − t。セッションの終わりまでに無ければ「またがない」(打ち切り)。
- 日 = t の日本時間の日。区間は日の塊。
"""
from __future__ import annotations

import numpy as np

import g2lib as L
from bot.research.cards.library import c8_session_mean_revert as c8

HORIZONS = (1, 5, 15, 60)
HOURS = tuple(range(24))
STARTS = ("約定", "中ほど")
CTRLS = (("本体", 0), ("24 時間前", -1440), ("24 時間後", 1440))
NAMES = ("n", "sx", "sy", "sxx", "syy", "sxy", "den", "agree")


def offset_ns(h: int) -> int:
    return ((24 - h) % 24) * L.HOUR_NS


def session_dev(g: L.Grid, h: int):
    """(決定の分の格子の番号, dev(bp), セッションの番号) — 最後の足と dev = 0 を除く前の全部の決定の足と、除く印。"""
    off = offset_ns(h)
    i = np.flatnonzero(g.ne)
    s = g.start(i)
    sid = c8.session_index(s, off)
    c = g.c[i]
    cs = np.cumsum(c)
    cnt = np.arange(1, len(i) + 1, dtype=float)
    first = np.concatenate([[True], sid[1:] != sid[:-1]])
    base_idx = np.maximum.accumulate(np.where(first, np.arange(len(i)), 0))
    cs_before = np.where(base_idx > 0, cs[np.maximum(base_idx - 1, 0)], 0.0)
    n_before = base_idx.astype(float)
    mean = (cs - cs_before) / (cnt - n_before)
    dev = np.log(c / mean) * 1e4
    last = (s + L.MIN_NS + off) % L.DAY_NS == 0
    return i, dev, sid, last


def count(g: L.Grid, days: L.Days) -> dict:
    """件数の数え上げ: 区切りごとの決定の分(dev ≠ 0、最後の足でない)。値動きは計算しない。"""
    cols = {}
    per_h = {}
    for h in HOURS:
        i, dev, sid, last = session_dev(g, h)
        use = (~last) & (dev != 0)
        d = L.jst_day(g.start(i[use]) + L.MIN_NS)
        per_h[h] = int(use.sum())
        if h in (15, 19, 0):
            cols[f"区切り {h} 時(UTC)の決定の分"] = d
    first = cols.pop("区切り 15 時(UTC)の決定の分")
    return {"lines": L.count_table(days, first, "区切り 15 時(UTC、jst_day)の決定の分", cols), "per_hour": per_h}


def fwd(g: L.Grid, i0, H: int, start: str, skip1: bool):
    """格子の番号 i0(判定の足)の、t からの H 分の値動き(bp)。使えなければ NaN。"""
    a = g.next_ne(i0 + (2 if skip1 else 1))
    b = g.next_ne(i0 + 1 + H)
    ok = (a < g.n) & (b < g.n) & (a <= b)
    a_, b_ = np.minimum(a, g.n - 1), np.minimum(b, g.n - 1)
    if start == "約定":
        p0, p1 = g.o[a_], g.o[b_]
    else:
        p0, p1 = (g.h[a_] + g.l[a_]) / 2, (g.h[b_] + g.l[b_]) / 2
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(ok, np.log(p1 / p0) * 1e4, np.nan)


def crossing(g: L.Grid, i, dev, sid):
    """決定の足ごとの、平均をまたぐ(触れる)までの分。またがなければ NaN。"""
    sg = np.sign(dev)
    n = len(i)
    brk = np.concatenate([[True], (sg[1:] != sg[:-1]) | (sid[1:] != sid[:-1])])
    run_start = np.flatnonzero(brk)
    run_id = np.cumsum(brk) - 1
    nxt = np.concatenate([run_start[1:], [n]])[run_id]  # 次の並びの最初の足
    ok = (nxt < n)
    ok[ok] &= sid[nxt[ok]] == sid[ok]
    mins = np.full(n, np.nan)
    mins[ok] = (i[nxt[ok]] - i[ok]).astype(float)
    return mins


def run(g: L.Grid, days: L.Days, hours=HOURS, keep_days_for=None) -> dict:
    """keep_days_for = (h, H, start, skip1) の組の集まり: その組の日ごとの和を # 11 のために返す。"""
    cells = {}
    cross = {}
    kept = {}
    for h in hours:
        i, dev, sid, last = session_dev(g, h)
        use = (~last) & (dev != 0)
        mins = crossing(g, i, dev, sid)
        iu, du = i[use], dev[use]
        day = L.jst_day(g.start(iu) + L.MIN_NS)
        sig = -np.sign(du)
        cross[h] = {"day": day, "min": mins[use]}
        for H in HORIZONS:
            for st in STARTS:
                for skip1 in (False, True):
                    if skip1 and H == 1:
                        continue
                    for cname, sh in CTRLS:
                        y = fwd(g, iu + sh, H, st, skip1)
                        ok = np.isfinite(y)
                        nz = ok & (y != 0)
                        acc = L.DayAcc(days, NAMES)
                        x0, y0 = np.where(ok, du, 0.0), np.where(ok, y, 0.0)
                        acc.add(day, n=ok.astype(float), sx=x0, sy=y0, sxx=x0 * x0, syy=y0 * y0, sxy=x0 * y0,
                                den=nz.astype(float), agree=(nz & (np.sign(y) == sig)).astype(float))
                        cells[(h, H, st, skip1, cname)] = acc
                        if keep_days_for and (h, H, st, skip1) in keep_days_for and cname == "本体":
                            kept[(h, H, st, skip1)] = acc
    return {"cells": cells, "cross": cross, "days": days, "kept": kept}


def tables(res: dict) -> tuple:
    days = res["days"]
    md = ["# # 8 カード 8: セッションの平均からの離れの後の値動き(D1b)", "",
          "区切り h = セッションの始まりの UTC の時刻(15 = jst_day、19 = bf_maint)。合図 = 平均へ戻る向き。"
          "一致 = 値動きの符号が合図と同じ。相関 = 離れ(bp)と値動き(bp)の相関(戻るなら負)。"
          "区間 = 日の塊(循環 5 日・1,000 回・種 20261006)。MDE = 2.8 × se。対照は同じ合図を 24 時間前・後の値動きに当てたもの。", "",
          "| 区切り | 時間 | 起点 | 1 分目 | 対照 | 期間 | 分 | 一致の割合 [区間] | MDE | 相関 [区間] | MDE |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    obj = {"periods": days.describe(), "cells": {}, "cross": {}}
    for (h, H, st, skip1, cname), acc in res["cells"].items():
        key = f"h{h}_H{H}_{st}_{'除く' if skip1 else '含む'}_{cname}"
        obj["cells"][key] = {}
        for pname, nums in days.parts().items():
            s = acc.sub(nums)
            a = L.ratio_ci(s["agree"], s["den"])
            r = L.corr_ci(s)
            obj["cells"][key][pname] = {"agree": a, "corr": r}
            md.append(f"| {h} | {H} | {st} | {'除く' if skip1 else '含む'} | {cname} | {pname} | {int(s['n'].sum())} | "
                      f"{L.fci(a, 4)} | {L.fmde(a, 4)} | {L.fci(r, 4)} | {L.fmde(r, 4)} |")
        obj["cells"][key]["years"] = {}
        for y, nums in days.years().items():
            s = acc.sub(nums)
            obj["cells"][key]["years"][y] = {"agree": L.ratio_ci(s["agree"], s["den"], ci=False), "corr": L.corr_ci(s, ci=False)}
    md += ["", "## 年ごと(記述。区間なし。本体だけ)", "", "| 区切り | 時間 | 起点 | 1 分目 | 年 | 一致の割合 | 相関 |", "|---|---|---|---|---|---|---|"]
    for (h, H, st, skip1, cname), acc in res["cells"].items():
        if cname != "本体":
            continue
        key = f"h{h}_H{H}_{st}_{'除く' if skip1 else '含む'}_{cname}"
        for y, v in obj["cells"][key]["years"].items():
            md.append(f"| {h} | {H} | {st} | {'除く' if skip1 else '含む'} | {y} | {L.f(v['agree']['est'], 4)} | {L.f(v['corr']['est'], 4)} |")
    md += ["", "## 平均をまたぐまでの分(記述)", "", "| 区切り | 期間 | 分 | またいだ割合 | またぐまでの分 25/50/75/90/99 |", "|---|---|---|---|---|"]
    for h, cr in res["cross"].items():
        obj["cross"][h] = {}
        for pname, nums in days.parts().items():
            m = (cr["day"] >= nums[0]) & (cr["day"] <= nums[-1])
            mm = cr["min"][m]
            q = L.quantiles(mm)
            share = float(np.mean(np.isfinite(mm))) if len(mm) else None
            obj["cross"][h][pname] = {"n": int(m.sum()), "crossed_share": share, "q": q}
            md.append(f"| {h} | {pname} | {int(m.sum())} | {L.f(share)} | " + "/".join(L.f(q[k], 0) for k in ("25", "50", "75", "90", "99")) + " |")
    return md, obj

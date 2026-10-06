"""# 6(カード 6 週末ギャップ): 為替が閉じていた間の動き g は、週明け 1 時間で戻るか。戻りは g の大きさに比例するか。

D1B_FRAMINGS.md # 6 の行: 何を何通り = btc・usdjpy の 2 通り。符号の一致・戻した幅 ÷ g・経路の一番深い不利な点 /
何を 1 件 = 1 週(約 282 週)。年ごと・前半後半 / データ = bitFlyer FX・USDJPY の 1 分足 / 対照 = 週明けでない同じ
曜日・時刻の 1 時間。
カードの分析の文書 docs/ANALYSIS/2026-10-05_card6_weekend_gap.md の P: (btc) 為替が閉まっていた間の FX_BTC_JPY の
動き g と、r から 1 時間の FX_BTC_JPY の動きの符号の一致・回帰の割合(戻した幅 ÷ g)。(usdjpy) USDJPY の窓と、
r から 1 時間の USDJPY 自身の動きで同じ量。経路の一番深い点も添える。

量の作り方:
- 週明けの行 r と g は、カード(src/bot/research/cards/library/c6_weekend_gap_revert.py)の docstring の決まりの
  とおり(week_opens。試験でカードのクラスを同じ行で動かし、同じ (r, g) になることを確かめる)。週 = 日本時間の週
  (jst_week_index を import)。週明けの行 = 後の週の行のうち、前の週の最後の終値と違う最初の行。
  usdjpy: g = ln(週明けの行の終値) − ln(前の週の最後の行の終値)。
  btc: g = ln(bitFlyer の r + 60 秒 時点の終値) − ln(bitFlyer の、前の週の最後の値の変わった行の終わり時点の終値)。
  「時点の終値」= 終わりがその時刻以下の最後の決定の足の終値。
- 1 時間の動き(LAG_NS・HOLD_NS をカードから import): 起点 P0 = g の終点(btc は bitFlyer の r + 60 秒 時点の終値、
  usdjpy は週明けの行の終値)。終点 P1 = r + HOLD_NS 時点の値(btc は bitFlyer の終値、usdjpy は終わりが r + HOLD_NS
  以下の最後の行の終値)。動き m = ln(P1 ÷ P0)(bp)。
- 符号の一致 = m と g の符号が同じ(続き)。分母 = m・g がどちらも 0 でない週。戻した幅 ÷ g = −m ÷ g(g ≠ 0 の週)の
  単純な平均と、重み付きの形 Σ(−m·sign(g)) ÷ Σ|g|(ratio_ci(−m·sign(g), |g|)。批評家 1 回目の指摘で足した)。
- 一番深い不利な点(bp)= 起点から 1 時間の経路で、g の向きに続いた一番遠い点(g > 0 なら 上、< 0 なら 下)。0 より小さければ 0。
  btc は bitFlyer の決定の足のうち始まりが [r + 60 秒, r + HOLD_NS) の高値・安値。usdjpy は行の時刻が
  (r, r + HOLD_NS − 60 秒] の行の高値・安値(同じファイルの high・low の列。系列の宣言はこの台本の中で足した)。
- 日 = r の日本時間の日。区間は日の塊。
- 対照(リードの決め 3): 行の「週明けでない同じ曜日・時刻の 1 時間」は、同じ曜日だと週明けそのものになり矛盾するので、
  「週明けの 1 時間と同じ時刻(日本時間)の、週明けでない平日(火〜金)の 1 時間」と読んだ。週明け r ごとに
  c = r + j 日(j = 1〜6)のうち、日本時間の曜日が火〜金で r と同じ日本時間の週にあるもの(ふつう 4 本)を取り、
  同じ g(その週の g)で同じ量(1 時間の動き m・符号の一致・−m ÷ g・一番深い不利な点)を作る。usdjpy の起点は
  c 以下の最後の行の終値。週ごとに対照の平均を 1 件にする(符号の一致は m ≠ 0 の対照の平均)。
"""
from __future__ import annotations

import csv
import gzip
import math
import os

import numpy as np

import g2lib as L
from bot.research.cards.library import c6_weekend_gap_revert as c6

LAG_NS = c6.LAG_NS
HOLD_NS = c6.HOLD_NS
VARIANTS = c6.GAPS  # ("usdjpy", "btc")


HL_NAMES = {"high": "usdjpy_high", "low": "usdjpy_low"}  # この台本の中だけの宣言(CARD.md は変えない。リードの応答 (b))


def load_usdjpy(lo: int, hi: int):
    """USDJPY の 1 分足の終値・高値・安値(参照の系列。封印の門 bot.bt.data.reference.load_reference を通る)。
    終値の宣言はカード 6 の CARD.md の測定の設定(usdjpy_close、lag 60 秒)。高値・安値は同じファイルの high・low の列で、
    宣言は終値と同じ遅れ・同じ出所の文に「この台本の中で足した」と書いたものを、この台本の中の宣言の辞書にだけ足す。
    common.usdjpy_ref_dataset を位置の引数だけで呼ぶ(USDJPY_PATH の 1 ファイル)。3 つの系列の行の時刻は同じでなければ拒む。
    戻り値: (時刻, 終値, 高値, 安値, 読んだファイルの記録)。"""
    import copy
    import common
    from bot.bt.data.reference import load_reference
    from bot.research.cards import cardmd
    with open(os.path.join(L.ROOT, "docs/RESEARCH/cards/c6_weekend_gap_revert/CARD.md"), encoding="utf-8") as fh:
        st, problems = cardmd.settings(cardmd.parse(fh.read()))
    if problems:
        raise SystemExit(f"カード 6 の CARD.md の測定の設定が読めない: {problems}")
    decl = dict(st.declarations)
    base = dict(decl[c6.FX])
    for col, name in HL_NAMES.items():
        decl[name] = {"lag_ns": base["lag_ns"],
                      "source": f"{base['source']} / 同じファイルの {col} の列(前提の直接の測り # 6 の台本の中で足した宣言。CARD.md には無い)"}
    ds = common.usdjpy_ref_dataset(c6.FX, lo, hi)
    s = load_reference(L.ROOT, ds, declarations=decl)
    t = np.array(s.times_ns, dtype=np.int64)
    out = {"close": np.array(s.values, dtype=float)}
    man = [list(m) for m in s.manifest]
    for col, name in HL_NAMES.items():
        d2 = copy.deepcopy(ds)
        d2["name"] = name
        d2["spec"]["value"] = col
        s2 = load_reference(L.ROOT, d2, declarations=decl)
        if np.array(s2.times_ns, dtype=np.int64).shape != t.shape or not np.array_equal(np.array(s2.times_ns, dtype=np.int64), t):
            raise SystemExit(f"USDJPY の {col} の行の時刻が終値の行と違う")
        out[col] = np.array(s2.values, dtype=float)
        man += [list(m) for m in s2.manifest]
    return t, out["close"], out["high"], out["low"], man


def bf_asof_fn(g: L.Grid):
    """時刻 x の bitFlyer の終値 = 終わりが x 以下の最後の決定の足の終値(無ければ NaN)。"""
    def asof(x):
        x = np.asarray(x, dtype=np.int64)
        j = g.prev_ne(g.index(x) - 1)  # 終わり <= x ⇔ 始まり <= x − 60 秒
        out = np.full(x.shape, np.nan)
        ok = j >= 0
        out[ok] = g.c[j[ok]]
        return out
    return asof


def week_opens(u_t, u_c, bf_asof):
    """カードの docstring の決まりで (r, g_usdjpy, g_btc) の並び。g が決まらなければ NaN。"""
    out = []
    week = close = bf_at_move = ref_fx = ref_bf = None
    armed = False
    bfx = bf_asof(np.asarray(u_t, dtype=np.int64) + LAG_NS)
    for i in range(len(u_t)):
        t, c = int(u_t[i]), float(u_c[i])
        if not c > 0:
            raise ValueError(f"USDJPY の終値が正でない: {c} at {t}")
        w = c6.jst_week_index(t)
        if week is not None and w > week:
            armed, ref_fx, ref_bf = True, close, bf_at_move
        if close is not None and c != close:
            bf = bfx[i]
            bf = None if math.isnan(bf) else float(bf)
            if armed:
                armed = False
                gu = math.log(c) - math.log(ref_fx)
                gb = (math.log(bf) - math.log(ref_bf)) if (bf is not None and ref_bf is not None) else math.nan
                out.append((t, gu, gb))
            bf_at_move = bf
        week, close = w, c
    return out


def _btc_hour(g: L.Grid, asof, c: np.ndarray, gv: np.ndarray):
    """bitFlyer の c + LAG 時点 → c + HOLD 時点 の動き m(bp)と、g の向きに続いた一番深い点(bp)。"""
    P0, P1 = asof(c + LAG_NS), asof(c + HOLD_NS)
    adv = np.full(len(c), np.nan)
    for k in range(len(c)):
        gk = gv[k]
        if not (np.isfinite(gk) and gk != 0 and np.isfinite(P0[k])):
            continue
        a, b = g.index(c[k] + LAG_NS), g.index(c[k] + HOLD_NS)
        sl = np.arange(max(a, 0), min(b, g.n))
        sl = sl[g.ne[sl]]
        if not len(sl):
            adv[k] = 0.0
            continue
        x = np.log(g.h[sl] / P0[k]) if gk > 0 else -np.log(g.l[sl] / P0[k])
        adv[k] = max(0.0, float(np.max(x)) * 1e4)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.log(P1 / P0) * 1e4, adv


def _usd_hour(u_t, u_c, u_h, u_l, c: np.ndarray, gv: np.ndarray):
    """USDJPY の c 以下の最後の行の終値 → 終わりが c + HOLD 以下の最後の行の終値 の動きと、g の向きに続いた一番深い点
    (行の時刻が (起点の行, c + HOLD − 60 秒] の行の高値・安値。g > 0 は高値、< 0 は安値)。"""
    k0 = np.searchsorted(u_t, c, side="right") - 1
    k1 = np.searchsorted(u_t, c + HOLD_NS - LAG_NS, side="right") - 1
    P0 = np.where(k0 >= 0, u_c[np.maximum(k0, 0)], np.nan)
    P1 = np.where(k1 >= 0, u_c[np.maximum(k1, 0)], np.nan)
    adv = np.full(len(c), np.nan)
    for k in range(len(c)):
        gk = gv[k]
        if not (gk != 0 and np.isfinite(gk) and k0[k] >= 0):
            continue
        sl = slice(k0[k] + 1, k1[k] + 1)
        seg = u_h[sl] if gk > 0 else u_l[sl]
        if not len(seg):
            adv[k] = 0.0
            continue
        x = np.log(seg / P0[k]) if gk > 0 else -np.log(seg / P0[k])
        adv[k] = max(0.0, float(np.max(x)) * 1e4)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.log(P1 / P0) * 1e4, adv


def control_times(r: np.ndarray, hi: int):
    """週明け r ごとの対照の始まり: r + j 日(j = 1〜6)で、日本時間の曜日が火〜金・r と同じ日本時間の週・
    c + HOLD_NS <= hi のもの。(週の番号の並び, 始まりの並び)。"""
    wi, cs = [], []
    for k, rk in enumerate(r):
        w = c6.jst_week_index(int(rk))
        for j in range(1, 7):
            c = int(rk) + j * L.DAY_NS
            wd = c5_weekday(c)
            if 1 <= wd <= 4 and c6.jst_week_index(c) == w and c + HOLD_NS <= hi:
                wi.append(k)
                cs.append(c)
    return np.array(wi, dtype=np.int64), np.array(cs, dtype=np.int64)


def c5_weekday(t_ns: int) -> int:
    """日本時間の曜日(月曜 = 0)。"""
    return int(((t_ns + L.JST_NS) // L.DAY_NS + 3) % 7)


def _week_means(n_weeks: int, wi: np.ndarray, vals: np.ndarray, valid: np.ndarray) -> tuple:
    s = np.bincount(wi[valid], weights=vals[valid], minlength=n_weeks)
    c = np.bincount(wi[valid], minlength=n_weeks).astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(c > 0, s / c, np.nan), c


def run(g: L.Grid, days: L.Days, u_t, u_c, *, u_h, u_l) -> dict:
    asof = bf_asof_fn(g)
    wo = week_opens(u_t, u_c, asof)
    r = np.array([x[0] for x in wo], dtype=np.int64)
    gaps = {"usdjpy": np.array([x[1] for x in wo]) * 1e4, "btc": np.array([x[2] for x in wo]) * 1e4}
    res = {"r": r, "day": L.jst_day(r) if len(r) else np.zeros(0, dtype=np.int64), "days": days, "variants": {}}
    u_t = np.asarray(u_t, dtype=np.int64)
    u_c = np.asarray(u_c, dtype=float)
    u_h = np.asarray(u_h, dtype=float)
    u_l = np.asarray(u_l, dtype=float)
    hi = int(g.t0 + g.n * L.MIN_NS)
    wi, cs = control_times(r, hi)
    res["control_times"] = cs
    res["control_week"] = wi
    for v in VARIANTS:
        gv = gaps[v]
        if v == "btc":
            m, adv = _btc_hour(g, asof, r, gv)
            mc, advc = _btc_hour(g, asof, cs, gv[wi])
        else:
            m, adv = _usd_hour(u_t, u_c, u_h, u_l, r, gv)
            mc, advc = _usd_hour(u_t, u_c, u_h, u_l, cs, gv[wi])
        gc = gv[wi]
        ok = np.isfinite(mc) & np.isfinite(gc) & (gc != 0)
        nz = ok & (mc != 0)
        with np.errstate(divide="ignore", invalid="ignore"):
            same_c, n_same = _week_means(len(r), wi, (np.sign(mc) == np.sign(gc)).astype(float), nz)
            ratio_c, n_c = _week_means(len(r), wi, -mc / gc, ok)
            adv_c, _ = _week_means(len(r), wi, advc, ok & np.isfinite(advc))
            wnum_c, _ = _week_means(len(r), wi, -mc * np.sign(gc), ok)
        res["variants"][v] = {"g": gv, "m": m, "adv": adv,
                              "ctrl": {"same": same_c, "ratio": ratio_c, "adv": adv_c, "wnum": wnum_c, "n": n_c, "n_same": n_same}}
    return res


def count(g: L.Grid, days: L.Days, u_t, u_c) -> dict:
    """件数の数え上げ: 週明けの数(変種ごとに g が決まり 0 でない週)。1 時間の動きは計算しない。"""
    wo = week_opens(u_t, u_c, bf_asof_fn(g))
    r = np.array([x[0] for x in wo], dtype=np.int64)
    d = L.jst_day(r) if len(r) else np.zeros(0, dtype=np.int64)
    gu = np.array([x[1] for x in wo])
    gb = np.array([x[2] for x in wo])
    wi, cs = control_times(r, int(g.t0 + g.n * L.MIN_NS))
    nweek = np.bincount(wi, minlength=len(r))
    lines = L.count_table(days, d, "週明け(件)", {"usdjpy の g ≠ 0": d[np.isfinite(gu) & (gu != 0)],
                                                   "btc の g ≠ 0": d[np.isfinite(gb) & (gb != 0)],
                                                   "対照のある週": d[nweek > 0], "対照の 1 時間(本)": d[wi] if len(wi) else d[:0]})
    return {"lines": lines + ["", CTRL_NOTE + "。", f"週ごとの対照の本数の分布: {dict(zip(*map(lambda a: a.tolist(), np.unique(nweek, return_counts=True))))}"],
            "weeks": int(len(r)), "controls": int(len(cs))}


def _summ(days, res, v, nums, ci=True):
    x = res["variants"][v]
    d = res["day"]
    gg, m, adv, ct = x["g"], x["m"], x["adv"], x["ctrl"]
    ok = np.isfinite(gg) & (gg != 0) & np.isfinite(m)
    nz = ok & (m != 0)
    okc = np.isfinite(gg) & (gg != 0) & np.isfinite(ct["ratio"])
    okcs = okc & np.isfinite(ct["same"])
    acc = L.DayAcc(days, ("n", "den", "same", "ratio", "adv", "wnum", "wden", "cn", "cden", "csame", "cratio", "cadv", "cwnum", "cwden"))
    with np.errstate(divide="ignore", invalid="ignore"):
        acc.add(d[ok], n=1.0, ratio=-m[ok] / gg[ok], adv=adv[ok], wnum=-m[ok] * np.sign(gg[ok]), wden=np.abs(gg[ok]))
        acc.add(d[okc], cwnum=ct["wnum"][okc], cwden=np.abs(gg[okc]))
        acc.add(d[nz], den=1.0, same=(np.sign(m[nz]) == np.sign(gg[nz])).astype(float))
        acc.add(d[okc], cn=1.0, cratio=ct["ratio"][okc], cadv=ct["adv"][okc])
        acc.add(d[okcs], cden=1.0, csame=ct["same"][okcs])
    s = acc.sub(nums)
    dm = ok & (d >= nums[0]) & (d <= nums[-1])
    dc = okc & (d >= nums[0]) & (d <= nums[-1])
    out = {"weeks": int(np.sum(dm)), "same": L.ratio_ci(s["same"], s["den"], ci), "ratio": L.ratio_ci(s["ratio"], s["n"], ci),
           "wratio": L.ratio_ci(s["wnum"], s["wden"], ci),
           "ratio_q": L.quantiles((-m / gg)[dm]), "adv": L.ratio_ci(s["adv"], s["n"], ci), "adv_q": L.quantiles(adv[dm]),
           "m0": int(np.sum(dm & (m == 0))),
           "ctrl": {"weeks": int(np.sum(dc)), "controls": int(np.sum(ct["n"][dc])),
                    "same": L.ratio_ci(s["csame"], s["cden"], ci), "ratio": L.ratio_ci(s["cratio"], s["cn"], ci),
                    "wratio": L.ratio_ci(s["cwnum"], s["cwden"], ci),
                    "adv": L.ratio_ci(s["cadv"], s["cn"], ci)}}
    if ci:
        out["diff"] = {"same": L.diff_ratio_ci(s["same"], s["den"], s["csame"], s["cden"]),
                       "ratio": L.diff_ratio_ci(s["ratio"], s["n"], s["cratio"], s["cn"]),
                       "wratio": L.diff_ratio_ci(s["wnum"], s["wden"], s["cwnum"], s["cwden"]),
                       "adv": L.diff_ratio_ci(s["adv"], s["n"], s["cadv"], s["cn"])}
    return out


CTRL_NOTE = ("対照 = 週明けの 1 時間と同じ時刻(日本時間)の、週明けでない平日(火〜金)の 1 時間(ふつう 4 本)の平均を 1 週 1 件。"
             "行の「同じ曜日」は週明けそのものになり矛盾するので「同じ時刻の、週明けでない平日」と読んだ(リードの決め 3)")


def tables(res: dict) -> tuple:
    days = res["days"]
    md = ["# # 6 カード 6: 週末の動き g と週明け 1 時間(D1b)", "",
          "単位: 割合 / 比 / bp。1 件 = 1 週。区間 = 日の塊(循環 5 日・1,000 回・種 20261006)。MDE = 2.8 × se。", "",
          CTRL_NOTE + "。", "",
          "戻した幅 ÷ g は 2 つの形: 単純な平均 = mean(−m ÷ g)(|g| の小さい週に引っぱられる)/ 重み付き = Σ(−m·sign(g)) ÷ Σ|g|"
          "(|g| で重みを付けた平均。批評家 1 回目の指摘)。", "",
          "| 変種 | 期間 | 週 | 符号の一致 [区間] | MDE | 戻した幅 ÷ g 平均 [区間] | 戻した幅 ÷ g 重み付き [区間] | MDE | 戻した幅 ÷ g 25/50/75 | 不利 平均 [区間] | 不利 50/90/99 | m = 0 の週 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    obj = {"periods": days.describe(), "control_note": CTRL_NOTE, "variants": {}}
    summ = {}
    for v in VARIANTS:
        obj["variants"][v] = {}
        for pname, nums in days.parts().items():
            s = _summ(days, res, v, nums)
            summ[(v, pname)] = s
            obj["variants"][v][pname] = s
            rq, aq = s["ratio_q"], s["adv_q"]
            md.append(f"| {v} | {pname} | {s['weeks']} | {L.fci(s['same'])} | {L.fmde(s['same'])} | {L.fci(s['ratio'])} | "
                      f"{L.fci(s['wratio'])} | {L.fmde(s['wratio'])} | {L.f(rq['25'])}/{L.f(rq['50'])}/{L.f(rq['75'])} | {L.fci(s['adv'], 2)} | "
                      f"{L.f(aq['50'], 1)}/{L.f(aq['90'], 1)}/{L.f(aq['99'], 1)} | {s['m0']} |")
    md += ["", "## 対照と、本体 − 対照", "",
           "| 変種 | 期間 | 対照の週(対照の本数) | 対照 符号の一致 [区間] | 本体 − 対照 [区間] | MDE | 対照 戻した幅 ÷ g 平均 [区間] | 本体 − 対照 [区間] | 対照 重み付き [区間] | 本体 − 対照 [区間] | 対照 不利 [区間] | 本体 − 対照 [区間] |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for v in VARIANTS:
        for pname in days.parts():
            s = summ[(v, pname)]
            c, df = s["ctrl"], s["diff"]
            md.append(f"| {v} | {pname} | {c['weeks']}({c['controls']}) | {L.fci(c['same'])} | {L.fci(df['same'])} | {L.fmde(df['same'])} | "
                      f"{L.fci(c['ratio'])} | {L.fci(df['ratio'])} | {L.fci(c['wratio'])} | {L.fci(df['wratio'])} | "
                      f"{L.fci(c['adv'], 2)} | {L.fci(df['adv'], 2)} |")
    md += ["", "## 年ごと(記述。区間なし)", "", "| 変種 | 年 | 週 | 符号の一致 | 対照 符号の一致 | 戻した幅 ÷ g 平均 | 対照 | 重み付き | 対照 | 不利 平均 | 対照 |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for v in VARIANTS:
        obj["variants"][v]["years"] = {}
        for y, nums in days.years().items():
            s = _summ(days, res, v, nums, ci=False)
            obj["variants"][v]["years"][y] = s
            c = s["ctrl"]
            md.append(f"| {v} | {y} | {s['weeks']} | {L.f(s['same']['est'])} | {L.f(c['same']['est'])} | {L.f(s['ratio']['est'])} | "
                      f"{L.f(c['ratio']['est'])} | {L.f(s['wratio']['est'])} | {L.f(c['wratio']['est'])} | {L.f(s['adv']['est'], 2)} | {L.f(c['adv']['est'], 2)} |")
    return md, obj


def write_records(path: str, res: dict) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["r", "day", "g_usdjpy_bp", "m_usdjpy_bp", "adv_usdjpy_bp", "ctrl_same_usdjpy", "ctrl_ratio_usdjpy", "ctrl_adv_usdjpy",
                    "g_btc_bp", "m_btc_bp", "adv_btc_bp", "ctrl_same_btc", "ctrl_ratio_btc", "ctrl_adv_btc", "n_ctrl"])
        vu, vb = res["variants"]["usdjpy"], res["variants"]["btc"]
        for k in range(len(res["r"])):
            row = [L.ns_iso(int(res["r"][k])), L.day_str(int(res["day"][k]))]
            for v in (vu, vb):
                row += [f"{float(a[k]):.6g}" for a in (v["g"], v["m"], v["adv"], v["ctrl"]["same"], v["ctrl"]["ratio"], v["ctrl"]["adv"])]
            w.writerow(row + [int(vb["ctrl"]["n"][k])])

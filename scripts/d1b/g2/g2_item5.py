"""# 5(カード 5 東京仲値): 朝の「0 時から t までの向き」は「t から 9 時 55 分までの向き」と一致するか。
ほかの時間帯の同じ長さの窓と違うか。

D1B_FRAMINGS.md # 5 の行: 何を何通り = 朝の窓 1 + ほかの時間帯の同じ長さの窓(1 時間ずつずらした 23 通り)。一致の割合と
相関 / 何を 1 件 = 1 日 × 1 分(区間は日の塊)/ データ = bitFlyer FX の 1 分足 / 対照 = ほかの時間帯の窓そのもの。
カードの分析の文書 docs/ANALYSIS/2026-10-05_card5_tokyo_fix.md の P: 日本時間の平日の各分 t(0 時〜9 時 54 分)で
「0 時から t までの値動き」と「t から 9 時 55 分までの値動き」の符号が同じになる割合と、両者の相関。

量の作り方(時計はカードのモジュール src/bot/research/cards/library/c5_tokyo_fix_momentum.py から import):
- 日 d = 日本時間の平日(jst_weekday(d) < 5。祝日は外さない = カードと同じ)。窓 k(k = 0〜23): 始まり Ws = d の
  日本時間 0 時 + k 時間、終わり We = Ws + FIX_TOD_NS(9 時間 55 分)。k = 0 が朝の窓(カードの窓)。ずらした窓も
  同じ日の集まり(平日の d)から始める。
- 起点 A = 始まりが Ws 以上の最初の決定の足の始値(カードの anchor と同じ作り。窓の中に無ければその日は数えない)。
- 決定の分 t = 終わりが Ws < t < We の決定の足の終わり(カードが持ち高を持つ分。始まりが起点の足より前は無い)。
- P_F = 終わりが We 以下の最後の決定の足の終値(We の時点の値段)。
- m1 = ln(終値_t ÷ A)、m2 = ln(P_F ÷ 終値_t)(bp)。一致 = m1・m2 がどちらも 0 でなく符号が同じ。一致の割合の分母 =
  どちらも 0 でない分(日 × 分 をまとめた割合)。
- 相関(リードの決め 5): 時刻 t(窓の始まりからの分 j = 0〜593、足の終わり = Ws + (j + 1) 分)ごとに、日をまたいだ
  m1(t) と m2(t) のピアソンの相関 r(t)。t の表と、t で平均した値 r̄ = mean_t r(t)(r(t) が出る t だけ)を並べる。
  1 日の中の相関(m1 + m2 = その日の窓の動き全体なので機械的に −1)と、日 × 分 をまとめた相関は出さない。
  区間は日の塊(抽き直した日で r(t) を全部作り直して平均する)。t の表の区間は朝の窓(k = 0)だけ付け、ほかの窓の
  t の表は点だけを JSON に出す(区間の計算の時間を抑えるため)。
- 朝の窓 − ほかの窓: 一致の割合の差(g2lib.diff_ratio_ci)と r̄ の差(tmean_diff_ci)に、同じ日の抽き直しで両方を作る区間
  (批評家 1 回目・2 回目の指摘)。
- 窓の終わりが期間の終わりを越える日(k が大きい窓の最後の日)は数えない。
- ずらした窓も同じ平日の日 d から始める(k が 15 以上の窓は次の日にかかる。リードの決め 6 で可)。
"""
from __future__ import annotations

import numpy as np

import g2lib as L
from bot.research.cards.library import c5_tokyo_fix_momentum as c5

FIX_TOD_NS = c5.FIX_TOD_NS
WIN_MIN = FIX_TOD_NS // L.MIN_NS  # 595
SHIFTS = tuple(range(24))  # 0 = 朝の窓、1〜23 = 1 時間ずつずらした窓


def weekdays(days: L.Days) -> np.ndarray:
    d = days.nums
    return d[np.array([c5.jst_weekday(int(x)) < 5 for x in d], dtype=bool)]


def window_slots(g: L.Grid, days: L.Days, k: int):
    """(日の番号, 窓の最初の分の格子の番号) の並び(窓が格子に収まる日だけ)。"""
    d = weekdays(days)
    ws = d * L.DAY_NS - L.JST_NS + k * L.HOUR_NS
    i0 = g.index(ws)
    ok = (i0 >= 0) & (i0 + WIN_MIN <= g.n)
    return d[ok], i0[ok]


def pairs(g: L.Grid, i0: np.ndarray):
    """窓ごとの (m1, m2, 有効) の (日数, WIN_MIN − 1) の行列。列 j = 始まり Ws + j 分 の足(終わり < We)。"""
    W = WIN_MIN
    cols = i0[:, None] + np.arange(W)[None, :]
    ne = g.ne[cols]
    o, c = g.o[cols], g.c[cols]
    has = ne.any(axis=1)
    ja = np.where(has, ne.argmax(axis=1), W)
    A = np.where(has, o[np.arange(len(i0)), np.minimum(ja, W - 1)], np.nan)
    last = np.where(has, W - 1 - ne[:, ::-1].argmax(axis=1), -1)
    PF = np.where(has, c[np.arange(len(i0)), np.maximum(last, 0)], np.nan)
    dec = ne[:, :W - 1]  # 終わり < We の足
    with np.errstate(divide="ignore", invalid="ignore"):
        m1 = np.log(c[:, :W - 1] / A[:, None]) * 1e4
        m2 = np.log(PF[:, None] / c[:, :W - 1]) * 1e4
    valid = dec & has[:, None]
    return m1, m2, valid


def day_sums(g: L.Grid, days: L.Days, k: int, acc: L.DayAcc):
    """一致の割合の日ごとの和を acc に足し、相関のための (日の並び × 6 × 時刻) の和の配列を返す。"""
    d, i0 = window_slots(g, days, k)
    m1, m2, v = pairs(g, i0)
    nz = v & (m1 != 0) & (m2 != 0)
    agree = nz & (np.sign(m1) == np.sign(m2))
    acc.add(d, den=nz.sum(axis=1), agree=agree.sum(axis=1))
    x = np.where(v, m1, 0.0)
    y = np.where(v, m2, 0.0)
    T = WIN_MIN - 1
    M = np.zeros((len(days.nums), 6, T))
    r = d - days.nums[0]
    for q, a in enumerate((v.astype(float), x, y, x * x, y * y, x * y)):
        M[r, q, :] = a
    return M


def corr_t(S: np.ndarray) -> np.ndarray:
    """(6, T) の和(n, sx, sy, sxx, syy, sxy)から時刻ごとの相関。出ない t は NaN。"""
    n, sx, sy, sxx, syy, sxy = S
    with np.errstate(divide="ignore", invalid="ignore"):
        vx = sxx - sx * sx / n
        vy = syy - sy * sy / n
        r = (sxy - sx * sy / n) / np.sqrt(vx * vy)
    return np.where((n > 1) & (vx > 0) & (vy > 0), r, np.nan)


def tmean_ci(M: np.ndarray, k_idx: np.ndarray, ci: bool = True) -> dict:
    """日の並びの部分 k_idx での r̄ = mean_t r(t) と、日の塊の区間。"""
    sub = M[k_idx].reshape(len(k_idx), -1)
    shape = M.shape[1:]
    est_v = corr_t(sub.sum(axis=0).reshape(shape))
    out = {"est": float(np.nanmean(est_v)) if np.isfinite(est_v).any() else None, "t_defined": int(np.isfinite(est_v).sum())}
    if not ci or out["est"] is None:
        return out

    def stat(i):
        cnt = np.bincount(i, minlength=len(k_idx)).astype(float)
        r = corr_t((cnt @ sub).reshape(shape))
        return float(np.nanmean(r)) if np.isfinite(r).any() else float("nan")
    out.update(L._boot(len(k_idx), stat))
    return out


def tmean_diff_ci(M0: np.ndarray, Mk: np.ndarray, k_idx: np.ndarray) -> dict:
    """r̄(朝の窓)− r̄(窓 k)と、同じ日の抽き直しで両方を作る日の塊の区間。"""
    s0 = M0[k_idx].reshape(len(k_idx), -1)
    sk = Mk[k_idx].reshape(len(k_idx), -1)
    shape = M0.shape[1:]

    def rbar(v):
        r = corr_t(v.reshape(shape))
        return float(np.nanmean(r)) if np.isfinite(r).any() else float("nan")
    est = rbar(s0.sum(axis=0)) - rbar(sk.sum(axis=0))
    out = {"est": None if not np.isfinite(est) else float(est)}
    if out["est"] is None:
        return out

    def stat(i):
        cnt = np.bincount(i, minlength=len(k_idx)).astype(float)
        return rbar(cnt @ s0) - rbar(cnt @ sk)
    out.update(L._boot(len(k_idx), stat))
    return out


def t_ci(M: np.ndarray, k_idx: np.ndarray, j: int) -> dict:
    """時刻 j の r(j) と日の塊の区間。"""
    sub = M[k_idx][:, :, j]
    est = corr_t(sub.sum(axis=0)[:, None])[0]
    out = {"est": None if np.isnan(est) else float(est), "n": float(sub[:, 0].sum())}
    if out["est"] is None:
        return out
    out.update(L._boot(len(k_idx), lambda i: float(corr_t(sub[i].sum(axis=0)[:, None])[0])))
    return out


NAMES = ("den", "agree")


def count(g: L.Grid, days: L.Days) -> dict:
    """件数の数え上げ: 窓ごとの (日 × 分) の数(決定の足のある分。値動きは計算しない)と日数。"""
    cols = {}
    per_k = {}
    for k in SHIFTS:
        d, i0 = window_slots(g, days, k)
        ne = g.ne[i0[:, None] + np.arange(WIN_MIN - 1)[None, :]]
        rep = np.repeat(d, ne.sum(axis=1))
        per_k[k] = int(ne.sum())
        if k in (0, 1, 12, 23):
            cols[f"窓 k={k} の 日×分"] = rep
        if k == 0:
            cols["窓 k=0 の日"] = d
            per_t = ne.sum(axis=0)  # 時刻 t ごとの日数(r(t) の件数)
    lines = L.count_table(days, cols.pop("窓 k=0 の 日×分"), "朝の窓(k=0)の 日×分", cols)
    q = {p_: int(v) for p_, v in zip(("min", "25", "50", "75", "max"), np.percentile(per_t, [0, 25, 50, 75, 100]))}
    lines += ["", f"朝の窓(k=0)の時刻 t ごとの日数(r(t) の 1 件 = 1 日。全期間)の分布: {q}"]
    return {"lines": lines, "per_shift": per_k, "per_t_days_k0": q}


def run(g: L.Grid, days: L.Days) -> dict:
    """窓ごとに一致の割合の日ごとの和と、相関の表(r̄ の区間、k = 0 の t の表の区間)を作る。和の配列は窓ごとに捨てる。"""
    accs, corr = {}, {}
    parts = days.parts()
    M0 = None
    for k in SHIFTS:  # SHIFTS[0] = 0(朝の窓)を最初に作り、ほかの窓との r̄ の差に使う
        acc = L.DayAcc(days, NAMES)
        M = day_sums(g, days, k, acc)
        accs[k] = acc
        c = {"tmean": {}, "t": {}, "years": {}, "diff_morning_minus_k": {}}
        if k == 0:
            M0 = M
        else:
            for pname, nums in parts.items():
                c["diff_morning_minus_k"][pname] = tmean_diff_ci(M0, M, nums - days.nums[0])
        for pname, nums in parts.items():
            kk = nums - days.nums[0]
            c["tmean"][pname] = tmean_ci(M, kk)
            if k == 0:
                c["t"][pname] = [t_ci(M, kk, j) for j in range(WIN_MIN - 1)]
            else:
                S = M[kk].sum(axis=0)
                c["t"][pname] = [{"est": None if np.isnan(r) else float(r)} for r in corr_t(S)]
        for y, nums in days.years().items():
            c["years"][y] = tmean_ci(M, nums - days.nums[0], ci=False)
        corr[k] = c
        if k != 0:
            del M
    return {"accs": accs, "corr": corr, "days": days}


def _clock(k: int, j: int) -> str:
    m = (k * 60 + j + 1) % 1440  # 足の終わりの日本時間(窓の始まり = 0 時 + k 時間)
    return f"{m // 60:02d}:{m % 60:02d}"


def tables(res: dict) -> tuple:
    days = res["days"]
    md = ["# # 5 カード 5: 0 時から t までの向きと t から 9 時 55 分までの向き(D1b)", "",
          "窓 k = 日本時間 0 時 + k 時間 から 9 時間 55 分。k = 0 が朝の窓。日 = 日本時間の平日(ずらした窓も同じ平日から)。"
          "一致の割合 = 日 × 分 をまとめた割合。相関 = 時刻 t ごとの日をまたいだ r(t) と、その t の平均 r̄(リードの決め 5。"
          "1 日の中の相関とまとめた相関は出さない)。区間 = 日の塊(循環 5 日・1,000 回・種 20261006)。MDE = 2.8 × se。", "",
          "## 窓ごと", "",
          "| 窓 k | 期間 | 一致の分母 | 一致の割合 [区間] | MDE | r̄(t の平均)[区間] | MDE | r(t) の出る t |", "|---|---|---|---|---|---|---|---|"]
    obj = {"periods": days.describe(), "shifts": {}}
    for k, acc in res["accs"].items():
        obj["shifts"][k] = {}
        for pname, nums in days.parts().items():
            s = acc.sub(nums)
            a = L.ratio_ci(s["agree"], s["den"])
            r = res["corr"][k]["tmean"][pname]
            obj["shifts"][k][pname] = {"agree": a, "corr_tmean": r, "corr_t": res["corr"][k]["t"][pname]}
            md.append(f"| {k} | {pname} | {int(s['den'].sum())} | {L.fci(a)} | {L.fmde(a)} | {L.fci(r)} | {L.fmde(r)} | {r.get('t_defined')} |")
    md += ["", "## 朝の窓 − ほかの窓(一致の割合の差 = g2lib.diff_ratio_ci、r̄ の差 = tmean_diff_ci。どちらも同じ日の抽き直しで両方を作る)", "",
           "| 窓 k | 期間 | 一致の割合 朝の窓 − 窓 k [区間] | MDE | r̄ 朝の窓 − 窓 k [区間] | MDE |", "|---|---|---|---|---|---|"]
    a0 = res["accs"][0]
    obj["diff_morning_minus_k"] = {}
    for k, acc in res["accs"].items():
        if k == 0:
            continue
        obj["diff_morning_minus_k"][k] = {}
        for pname, nums in days.parts().items():
            s0, sk = a0.sub(nums), acc.sub(nums)
            dd = L.diff_ratio_ci(s0["agree"], s0["den"], sk["agree"], sk["den"])
            dr = res["corr"][k]["diff_morning_minus_k"].get(pname, {"est": None})
            obj["diff_morning_minus_k"][k][pname] = {"agree": dd, "corr_tmean": dr}
            md.append(f"| {k} | {pname} | {L.fci(dd)} | {L.fmde(dd)} | {L.fci(dr)} | {L.fmde(dr)} |")
    md += ["", "## 年ごと(記述。区間なし)", "", "| 窓 k | 年 | 一致の割合 | r̄ | 一致の分母 |", "|---|---|---|---|---|"]
    for k, acc in res["accs"].items():
        obj["shifts"][k]["years"] = {}
        for y, nums in days.years().items():
            s = acc.sub(nums)
            a = L.ratio_ci(s["agree"], s["den"], ci=False)
            r = res["corr"][k]["years"][y]
            obj["shifts"][k]["years"][y] = {"agree": a, "corr_tmean": r}
            md.append(f"| {k} | {y} | {L.f(a['est'])} | {L.f(r['est'])} | {int(s['den'].sum())} |")
    md += ["", "## 朝の窓(k = 0)の時刻ごとの相関 r(t)", "",
           "t = 足の終わりの日本時間。ほかの窓の t の表は TABLES.json の shifts.<k>.<期間>.corr_t(点だけ)。", "",
           "| t | 日(全期間) | 全期間 r(t) [区間] | 前半 r(t) [区間] | 後半 r(t) [区間] |", "|---|---|---|---|---|"]
    ct = res["corr"][0]["t"]
    for j in range(WIN_MIN - 1):
        md.append(f"| {_clock(0, j)} | {int(ct['全期間'][j].get('n', 0))} | {L.fci(ct['全期間'][j])} | {L.fci(ct['前半'][j])} | {L.fci(ct['後半'][j])} |")
    return md, obj

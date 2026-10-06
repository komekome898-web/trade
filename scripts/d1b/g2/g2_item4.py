"""# 4(カード 4 マチルダ): 中心から離れた足の後、値段は中心へ戻るか。戻る前にどこまで不利に動くか。

D1B_FRAMINGS.md # 4 の行: 何を何通り = 離れの深さ 1 通り(中心から平均の実体の 2 倍、カードの水準)× 比の区分 3。
戻る割合と、戻る前の一番深い不利な点の分布 / 何を 1 件 = 1 回の離れ。年ごと・前半後半 / データ = bitFlyer FX の
1 分足 / 対照 = 離れていない足から同じ時間の経路。
カードの分析の文書 docs/ANALYSIS/2026-10-05_card4_matilda.md の P: 「中心から 2 × 平均実体 離れた足」の後、価格が
「中心(または建値から 0.8 × 平均実体)」へ戻るまでの経路の一番深い不利な点と、40 分以内に戻る割合。

量の作り方(数はカードのモジュール src/bot/research/cards/library/c4_owner_matilda_range.py から import し、打ち直さない):
- 判定の時刻 t = 決定の足(出来高 > 0)の終わり。窓 = 始まりが t − WINDOW_MIN 分 以上の足(時刻で切る)。
  上端・下端 = 実体の端(max / min(始値, 終値)。カードの既定 range_from="body")、中心 = (上端 + 下端) ÷ 2、
  平均実体 vola = 窓の中の足の |終値 − 始値| の平均、比 = 幅 ÷ vola。窓が満ちるまで(最初の決定の足の始まり >
  t − 窓)は判定しない(カードと同じ)。
- 離れ: vola > 0 で 終値 > 中心 + ENTRY_K × vola(上に離れた。向き −1 = 中心へは下)/ 終値 < 中心 − ENTRY_K × vola
  (下に離れた。向き +1)。カードの _signal と同じ式。
- 1 回の離れ = 離れの続き(同じ側に離れた決定の足が続く間)の最初の足。直前の決定の足が同じ側に離れていなければ
  新しい 1 回(直前が窓の満ちる前なら離れていないと数える)。【この数え方は行の「1 回の離れ」の読み。リードの決め 6 で可】
- 起点 S = t の後の最初の決定の足の始値(カードの約定の値段。W1 の仕様 C2)。見る長さ H = HOLD_MAX_MIN 分
  (カードの時間成行 40 分 = P の「40 分以内」)。経路 = 始まりが [t, t + H) の決定の足。S の足が経路に無ければ数えない。
- 戻る(2 通り。P が名指した 2 つの先): (A) 中心: 判定の時刻の中心(固定)を終値がまたぐか触れる(向き −1 は
  終値 ≤ 中心、+1 は 終値 ≥ 中心)。(B) 建値から 0.8 × vola: 終値が S + 向き × EXIT_STEP × vola を越える(カードの
  _take_profit の形 2、段 1 つ・緩めなしの式。等号なし)。判定は終値(カードと同じ)。戻るまでの分 = 戻った足の終わり − t。
- 一番深い不利な点(bp)= 経路のうち戻った足より前の足の、向きに逆らう側の端(向き −1 は ln(高値 ÷ S)、+1 は
  −ln(安値 ÷ S))の最大。0 より小さければ 0。戻った足の中の順序は分からないので、その足は入れない。
  戻らなかった離れは経路の全部の足で取る。
- 対照: 窓が満ち vola > 0 で離れていない決定の足 全部。向き = 中心の側(終値 > 中心なら −1、< なら +1、= は除く)。
  同じ式で (A)(B) と一番深い不利な点。【向きの付け方は読み。リードの決め 6 で可】
- 比の区分 3 の境(リードの決め 1): 前半(日の並びの前半)の 1 回の離れの比の 3 分位(np.quantile、線形)を台本の中で
  計算し、全期間・前半・後半・年に同じ境を当てる。区分 = [0, q1)・[q1, q2)・[q2, ∞)。対照の足も同じ境で分ける。
  出力に「帯の境は前半の標本から」と印を付ける。
- 窓は期間の始まりより前の足で埋めない(カードと同じ温まり。リードの決め 6 で可)。
"""
from __future__ import annotations

import gzip
import math

import numpy as np

import g2lib as L
from bot.research.cards.library import c4_owner_matilda_range as c4

WINDOW_MIN = c4.WINDOW_MIN  # 40(O-1「直近40分ほど」)
ENTRY_K = c4.ENTRY_K  # 2.0(v37 141 行 entry_setting)
EXIT_STEP = c4.EXIT_STEP  # 0.8(v37 157 行 step_exit)
HOLD_MIN = c4.HOLD_MAX_MIN  # 40(v37 alert_count × 2)
assert c4.RANGE_FROMS[0] == "body"
CHUNK = 100_000


def window_stats(g: L.Grid, idx: np.ndarray):
    """決定の足 idx(格子の番号)ごとの (中心, vola, 幅, 窓が満ちたか)。窓 = 番号 idx − WINDOW_MIN + 1 〜 idx。"""
    W = WINDOW_MIN
    top = np.where(g.ne, np.fmax(g.o, g.c), np.nan)
    bot = np.where(g.ne, np.fmin(g.o, g.c), np.nan)
    body = np.where(g.ne, np.abs(g.c - g.o), np.nan)
    pad = lambda a: np.concatenate([np.full(W - 1, np.nan), a])  # noqa: E731
    sw = np.lib.stride_tricks.sliding_window_view
    T, B, Y = sw(pad(top), W), sw(pad(bot), W), sw(pad(body), W)
    center = np.empty(len(idx))
    vola = np.empty(len(idx))
    width = np.empty(len(idx))
    for a in range(0, len(idx), CHUNK):
        k = idx[a:a + CHUNK]
        hi_, lo_ = np.nanmax(T[k], axis=1), np.nanmin(B[k], axis=1)
        center[a:a + CHUNK] = (hi_ + lo_) / 2.0
        width[a:a + CHUNK] = hi_ - lo_
        vola[a:a + CHUNK] = np.nanmean(Y[k], axis=1)
    first = int(np.flatnonzero(g.ne)[0]) if g.ne.any() else g.n
    warm = idx - (W - 1) >= first  # 最初の決定の足の始まり <= t − 窓
    return center, vola, width, warm


def signals(g: L.Grid):
    """全部の決定の足の (番号, 合図(−1/0/+1), 中心, vola, 比, 窓が満ちたか)。"""
    idx = np.flatnonzero(g.ne)
    center, vola, width, warm = window_stats(g, idx)
    c = g.c[idx]
    sig = np.zeros(len(idx), dtype=np.int8)
    ok = warm & (vola > 0)
    sig[ok & (c > center + ENTRY_K * vola)] = -1
    sig[ok & (c < center - ENTRY_K * vola)] = 1
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(vola > 0, width / vola, np.where(width > 0, np.inf, 0.0))
    return idx, sig, center, vola, ratio, warm


def ratio_edges(days: L.Days, day_of_ep: np.ndarray, ratio_ep: np.ndarray) -> tuple:
    """比の区分の境 = 前半の 1 回の離れの比の 1/3・2/3 分位(リードの決め 1)。"""
    first = days.parts()["前半"]
    m = (day_of_ep >= first[0]) & (day_of_ep <= first[-1]) & np.isfinite(ratio_ep)
    if not m.any():
        return None
    q1, q2 = np.quantile(ratio_ep[m], [1 / 3, 2 / 3])
    return float(q1), float(q2)


def bins_of(edges):
    q1, q2 = edges
    return {f"比 < {q1:.3f}": (-math.inf, q1), f"{q1:.3f} ≤ 比 < {q2:.3f}": (q1, q2), f"比 ≥ {q2:.3f}": (q2, math.inf)}


EDGE_NOTE = "帯の境は前半の標本から(前半の 1 回の離れの比の 3 分位。リードの決め 1)。境は前半の標本の中で決めたので、前半の帯の件数は作りからして等しい。境を試しているのは後半だけ"


def episodes(sig: np.ndarray) -> np.ndarray:
    """1 回の離れの最初の足(決定の足の並びの中の位置)。"""
    prev = np.concatenate([[0], sig[:-1]])
    return np.flatnonzero((sig != 0) & (sig != prev))


def outcomes(g: L.Grid, i, side, center, vola):
    """離れ(または対照の足)ごとの経路の量。i = 判定の足の格子の番号、side = 中心への向き(+1 / −1)。
    戻り値: dict(ok, S, retA, minA, advA, retB, minB, advB)。ok = 起点の足が経路にある。"""
    H = HOLD_MIN
    n = len(i)
    out = {k: np.full(n, np.nan) for k in ("S", "minA", "advA", "minB", "advB")}
    out["ok"] = np.zeros(n, dtype=bool)
    out["retA"] = np.zeros(n, dtype=bool)
    out["retB"] = np.zeros(n, dtype=bool)
    padn = H + 1
    C = np.concatenate([g.c, np.full(padn, np.nan)])
    Hh = np.concatenate([g.h, np.full(padn, np.nan)])
    Lw = np.concatenate([g.l, np.full(padn, np.nan)])
    NE = np.concatenate([g.ne, np.zeros(padn, dtype=bool)])
    sw = np.lib.stride_tricks.sliding_window_view
    Cw, Hw, Lw_, NEw = sw(C, H), sw(Hh, H), sw(Lw, H), sw(NE, H)
    j0 = g.next_ne(i + 1)
    for a in range(0, n, CHUNK):
        sl = slice(a, a + CHUNK)
        ii, sd, ce, vo, jj = i[sl] + 1, side[sl].astype(float), center[sl], vola[sl], j0[sl]
        ok = jj < i[sl] + 1 + H  # 起点の足の始まり < t + H
        S = np.where(ok, g.o[np.minimum(jj, g.n - 1)], np.nan)
        c, hh, ll, ne = Cw[ii], Hw[ii], Lw_[ii], NEw[ii]
        hitA = ne & (sd[:, None] * (c - ce[:, None]) >= 0)
        hitB = ne & (sd[:, None] * (c - (S + sd * EXIT_STEP * vo)[:, None]) > 0)
        with np.errstate(divide="ignore", invalid="ignore"):
            adv = np.where(ne, np.where(sd[:, None] < 0, np.log(hh / S[:, None]), -np.log(ll / S[:, None])) * 1e4, np.nan)
        for tag, hit in (("A", hitA), ("B", hitB)):
            any_ = hit.any(axis=1) & ok
            k = np.where(any_, hit.argmax(axis=1), H)
            before = np.arange(H)[None, :] < k[:, None]
            m = np.where(before, adv, np.nan)
            with np.errstate(all="ignore"):
                worst = np.nanmax(np.where(np.isnan(m), -np.inf, m), axis=1)
            worst = np.where(np.isfinite(worst), np.maximum(worst, 0.0), 0.0)
            out["ret" + tag][sl] = any_
            out["min" + tag][sl] = np.where(any_, k + 1, np.nan)
            out["adv" + tag][sl] = np.where(ok, worst, np.nan)
        out["S"][sl] = S
        out["ok"][sl] = ok
    return out


def count(g: L.Grid, days: L.Days) -> dict:
    """件数の数え上げ(値動きを計算しない): 離れの回数・離れた足の数・対照の足の数。"""
    idx, sig, center, vola, ratio, warm = signals(g)
    ep = episodes(sig)
    t_end = g.start(idx) + L.MIN_NS
    d = L.jst_day(t_end)
    ctrl = warm & (vola > 0) & (sig == 0) & (g.c[idx] != center)
    lines = L.count_table(days, d[ep], "1 回の離れ(件)", {
        "うち上に離れた": d[ep][sig[ep] == -1], "うち下に離れた": d[ep][sig[ep] == 1],
        "離れた決定の足(参考)": d[sig != 0], "対照の足": d[ctrl]})
    edges = ratio_edges(days, d[ep], ratio[ep])
    cols = {}
    if edges is not None:
        for bname, (a, b) in bins_of(edges).items():
            cols[f"離れ {bname}"] = d[ep][(ratio[ep] >= a) & (ratio[ep] < b)]
            cols[f"対照 {bname}"] = d[ctrl][(ratio[ctrl] >= a) & (ratio[ctrl] < b)]
    first = cols.pop(next(iter(cols))) if cols else d[ep]
    name0 = f"離れ {next(iter(bins_of(edges)))}" if edges else "1 回の離れ"
    bin_lines = ["", f"### 比の区分ごと({EDGE_NOTE}: 境 {edges[0]:.4f}・{edges[1]:.4f})" if edges else "### 比の区分ごと(境が出ない)", ""]
    bin_lines += L.count_table(days, first, name0, cols)
    return {"lines": lines + bin_lines, "episodes": int(len(ep)), "signal_bars": int(np.sum(sig != 0)),
            "control_bars": int(np.sum(ctrl)), "ratio_edges_first_half": edges}


def run(g: L.Grid, days: L.Days) -> dict:
    idx, sig, center, vola, ratio, warm = signals(g)
    ep = episodes(sig)
    t_end = g.start(idx) + L.MIN_NS
    edges = ratio_edges(days, L.jst_day(t_end[ep]), ratio[ep])
    groups = {}
    ev = outcomes(g, idx[ep], sig[ep], center[ep], vola[ep])
    groups["離れ"] = {"day": L.jst_day(t_end[ep]), "ratio": ratio[ep], **ev}
    cm = warm & (vola > 0) & (sig == 0) & (g.c[idx] != center)
    cside = np.where(g.c[idx] > center, -1, 1).astype(np.int8)
    ci_ = np.flatnonzero(cm)
    co = outcomes(g, idx[ci_], cside[ci_], center[ci_], vola[ci_])
    groups["対照(離れていない足)"] = {"day": L.jst_day(t_end[ci_]), "ratio": ratio[ci_], **co}
    rec = {"t": t_end[ep], "side": sig[ep], "ratio": ratio[ep], "center": center[ep], "vola": vola[ep],
           "close": g.c[idx[ep]], **{k: ev[k] for k in ("S", "retA", "minA", "advA", "retB", "minB", "advB")}}
    return {"groups": groups, "records": rec, "ratio_edges": edges, "days": days}


def _summ(days: L.Days, gr: dict, nums, mask=None, ci=True) -> dict:
    m = gr["ok"] if mask is None else (gr["ok"] & mask)
    acc = L.DayAcc(days, ("n", "rA", "rB", "aA", "aB"))
    acc.add(gr["day"][m], n=1.0, rA=gr["retA"][m], rB=gr["retB"][m], aA=gr["advA"][m], aB=gr["advB"][m])
    s = acc.sub(nums)
    dm = (gr["day"] >= nums[0]) & (gr["day"] <= nums[-1]) & m
    return {"n": int(np.sum(dm)),
            "retA": L.ratio_ci(s["rA"], s["n"], ci), "retB": L.ratio_ci(s["rB"], s["n"], ci),
            "advA": L.ratio_ci(s["aA"], s["n"], ci), "advB": L.ratio_ci(s["aB"], s["n"], ci),
            "advA_q": L.quantiles(gr["advA"][dm]), "advB_q": L.quantiles(gr["advB"][dm]),
            "minA_q": L.quantiles(gr["minA"][dm & gr["retA"]]), "minB_q": L.quantiles(gr["minB"][dm & gr["retB"]])}


def tables(res: dict) -> tuple:
    days = res["days"]
    obj = {"periods": days.describe(), "groups": {}}
    md = ["# # 4 カード 4: 中心から離れた足の後の経路(D1b)", "",
          f"窓 {WINDOW_MIN} 分・離れ {ENTRY_K} × 平均実体・見る長さ {HOLD_MIN} 分・(B) の値幅 {EXIT_STEP} × 平均実体"
          "(カードのモジュールの値)。単位: 割合 / bp。区間 = 日の塊(循環 5 日・1,000 回・種 20261006)。MDE = 2.8 × se。", "",
          "| 群 | 期間 | 件 | 戻る(A 中心)[区間] | MDE | 戻る(B 建値 ± 0.8 vola)[区間] | MDE | 不利 A 平均 [区間] | 不利 B 平均 [区間] | 不利 A 25/50/75/90/99 | 戻るまで A 分 50/90 |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for gname, gr in res["groups"].items():
        obj["groups"][gname] = {}
        for pname, nums in days.parts().items():
            s = _summ(days, gr, nums)
            obj["groups"][gname][pname] = s
            q = s["advA_q"]
            md.append(f"| {gname} | {pname} | {s['n']} | {L.fci(s['retA'])} | {L.fmde(s['retA'])} | {L.fci(s['retB'])} | "
                      f"{L.fmde(s['retB'])} | {L.fci(s['advA'], 2)} | {L.fci(s['advB'], 2)} | "
                      + "/".join(L.f(q[k], 1) for k in ("25", "50", "75", "90", "99")) + " | "
                      + "/".join(L.f(s["minA_q"][k], 0) for k in ("50", "90")) + " |")
    md += ["", "## 年ごと(記述。区間なし)", "", "| 群 | 年 | 件 | 戻る A | 戻る B | 不利 A 平均 | 不利 B 平均 |", "|---|---|---|---|---|---|---|"]
    for gname, gr in res["groups"].items():
        obj["groups"][gname]["years"] = {}
        for y, nums in days.years().items():
            s = _summ(days, gr, nums, ci=False)
            obj["groups"][gname]["years"][y] = s
            md.append(f"| {gname} | {y} | {s['n']} | {L.f(s['retA']['est'])} | {L.f(s['retB']['est'])} | "
                      f"{L.f(s['advA']['est'], 2)} | {L.f(s['advB']['est'], 2)} |")
    md += ["", "## 比の区分"]
    if res["ratio_edges"] is None:
        md += ["", "前半に 1 回の離れが無く、境が出ない。"]
        obj["ratio_bins"] = None
    else:
        e1, e2 = res["ratio_edges"]
        md += ["", f"{EDGE_NOTE}: 境 {e1:.4f}・{e2:.4f}。全期間・前半・後半に同じ境を当てた。", "",
               "| 群 | 区分 | 期間 | 件 | 戻る A [区間] | 戻る B [区間] | 不利 A 平均 [区間] | 不利 B 平均 [区間] | 不利 A 50/90 |",
               "|---|---|---|---|---|---|---|---|---|"]
        obj["ratio_bins"] = {"edges_first_half": [e1, e2], "note": EDGE_NOTE}
        for gname, gr in res["groups"].items():
            for bname, (a, b) in bins_of(res["ratio_edges"]).items():
                m = (gr["ratio"] >= a) & (gr["ratio"] < b)
                for pname, nums in days.parts().items():
                    s = _summ(days, gr, nums, m)
                    obj["ratio_bins"].setdefault(gname, {}).setdefault(bname, {})[pname] = s
                    md.append(f"| {gname} | {bname} | {pname} | {s['n']} | {L.fci(s['retA'])} | {L.fci(s['retB'])} | "
                              f"{L.fci(s['advA'], 2)} | {L.fci(s['advB'], 2)} | {L.f(s['advA_q']['50'], 1)}/{L.f(s['advA_q']['90'], 1)} |")
            md += [""] if gname == "離れ" else []
        md += ["", "### 比の区分 × 年(記述。区間なし。離れだけ)", "", "| 区分 | 年 | 件 | 戻る A | 戻る B | 不利 A 平均 |", "|---|---|---|---|---|---|"]
        gr = res["groups"]["離れ"]
        for bname, (a, b) in bins_of(res["ratio_edges"]).items():
            m = (gr["ratio"] >= a) & (gr["ratio"] < b)
            for y, nums in days.years().items():
                s = _summ(days, gr, nums, m, ci=False)
                md.append(f"| {bname} | {y} | {s['n']} | {L.f(s['retA']['est'])} | {L.f(s['retB']['est'])} | {L.f(s['advA']['est'], 2)} |")
    return md, obj


def write_records(path: str, rec: dict) -> None:
    keys = list(rec)
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        fh.write(",".join(keys) + "\n")
        for r in zip(*(rec[k] for k in keys)):
            fh.write(",".join(L.ns_iso(int(v)) if k == "t" else (str(int(v)) if k in ("side",) else
                                                                    (str(bool(v)) if k in ("retA", "retB") else f"{float(v):.10g}"))
                              for k, v in zip(keys, r)) + "\n")

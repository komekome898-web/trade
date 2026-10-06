"""# 7(カード 7 バリアレース): 任意の時点から同じ幅の上下の線を引くと、どちらに先に当たるか(続きか戻りか)。
幅が小さい時期ほど続くか。

D1B_FRAMINGS.md # 7 の行: 何を何通り = 起点 = 毎時の始まり。幅 3 通り(1 時間・1 日・1 週のボラ)× 幅の帯 3 /
何を 1 件 = 1 起点。年ごと・前半後半 / データ = bitFlyer FX の 1 分足 / 対照 = 上下の線は対称なので基準は 0.5
(流れを抜いた値も並べる)。

量の作り方(幅の窓はカード src/bot/research/cards/library/c7_barrier_race.py の WINDOWS を import):
- 起点 T = 期間の中の毎時 0 分(UTC。日本時間でも同じ 0 分)。起点の値 a = 終わりが T 以下の最後の決定の足の
  ln(終値)。
- 幅 w = √(Σ r²)、r = 続いた決定の足どうしの ln(終値) の差で、後ろの足の終わりが (T − 窓, T] にあるもの(カードと同じ)。
  温まり: 最初の決定の足の終わり > T − 窓 の起点は数えない(カードと同じ)。w = 0 の起点も数えない(数は出す)。
- 当たり: 終わりが T より後の決定の足を順に見て、ln(終値) − a ≥ w なら上(+1)、≤ −w なら下(−1)。最初の当たりで
  決着。時間の上限なし(カードと同じ)。期間の終わりまでに当たらなければ「未決着」(0)。当たるまでの分を記録する。
- 続き・戻り(リードの決め 2): 起点の前の向き = window_move = 起点の前の、幅を決めたのと同じ長さの窓の値動きの符号
  (a − 終わりが T − 窓 以下の最後の決定の足の ln(終値))。続き = 当たりの向き == 前の向き(前が上なら上の線に先に
  当たる = 続き)。前の向きが 0 の起点は数えず、その数を出す。基準 0.5。流れを抜いた値 = (前が上の起点の続きの割合 +
  前が下の起点の続きの割合)÷ 2(カード 7 の redo2 の race_more.py の (1) と同じ作り)。
- 幅の帯 3 の境(リードの決め 2): 窓ごとに、前半の数える起点(温まりの後・w > 0・前の向き ≠ 0)の w の 3 分位
  (np.quantile、線形)を台本の中で計算し、全期間・前半・後半・年に同じ境を当てる。「帯の境は前半の標本から」。
  帯どうしの比べは、低い帯 − 高い帯の続きの割合の差に区間を付ける(g2lib.diff_ratio_ci。批評家 1 回目の指摘)。
- 窓は期間の始まりより前の足で埋めない(カードと同じ温まり。リードの決め 6 で可)。
"""
from __future__ import annotations

import gzip

import numpy as np

import g2lib as L
from bot.research.cards.library import c7_barrier_race as c7

WINDOWS = dict(c7.WINDOWS)  # {"1h": ns, "1d": ns, "1w": ns}


def prep(g: L.Grid):
    """決定の足の (終わりの時刻, ln(終値), Σr² の累積)。累積[k] = 足 1〜k の r² の和(足 0 は 0)。"""
    i = np.flatnonzero(g.ne)
    e = g.start(i) + L.MIN_NS
    x = np.log(g.c[i])
    r2 = np.concatenate([[0.0], np.diff(x) ** 2])
    return e, x, np.cumsum(r2)


def origins(g: L.Grid, lo: int, hi: int) -> np.ndarray:
    first = ((lo + L.HOUR_NS - 1) // L.HOUR_NS) * L.HOUR_NS
    return np.arange(first, hi, L.HOUR_NS, dtype=np.int64)


def widths(e, x, cs, T, win_ns):
    """起点ごとの (a, w, 使えるか)。"""
    k = np.searchsorted(e, T, side="right") - 1  # 終わり <= T の最後の足
    j = np.searchsorted(e, T - win_ns, side="right")  # 終わり > T − 窓 の最初の足
    has = k >= 0
    kk = np.maximum(k, 0)
    # r² は足 j〜k の分(足 m の r² は 足 m−1 → m。足 m の終わりが窓の中なら入る)
    s = np.where(has & (kk >= j), cs[kk] - np.where(j > 0, cs[np.maximum(j - 1, 0)], 0.0), 0.0)
    w = np.sqrt(np.maximum(s, 0.0))
    warm = has & (len(e) > 0) & (e[0] <= T - win_ns) if len(e) else np.zeros(len(T), dtype=bool)
    a = np.where(has, x[kk], np.nan)
    return a, w, warm, k


def race(x, k_from, a, w, chunk0=64):
    """足 k_from + 1 から先で最初の当たり。戻り値 (向き +1 / −1 / 0, 当たった足の番号 or −1)。"""
    n = len(x)
    side = np.zeros(len(a), dtype=np.int8)
    hit = np.full(len(a), -1, dtype=np.int64)
    for q in range(len(a)):
        s = k_from[q] + 1
        ch = chunk0
        while s < n:
            seg = x[s:s + ch] - a[q]
            m = np.flatnonzero(np.abs(seg) >= w[q])
            if len(m):
                hit[q] = s + m[0]
                side[q] = 1 if seg[m[0]] >= w[q] else -1
                break
            s += ch
            ch *= 2
    return side, hit


def run(g: L.Grid, days: L.Days, lo: int, hi: int) -> dict:
    e, x, cs = prep(g)
    T = origins(g, lo, hi)
    out = {"days": days, "windows": {}}
    for name, wn in WINDOWS.items():
        a, w, warm, k = widths(e, x, cs, T, wn)
        use = warm & (w > 0)
        q = np.flatnonzero(use)
        side, hit = race(x, k[q], a[q], w[q])
        mins = np.where(hit >= 0, (e[np.maximum(hit, 0)] - T[q]) // L.MIN_NS, -1)
        kp = np.searchsorted(e, T[q] - wn, side="right") - 1  # 終わり <= T − 窓 の最後の足(前の向きの候補 window_move)
        prior_wm = np.where(kp >= 0, np.sign(a[q] - x[np.maximum(kp, 0)]), 0).astype(np.int8)
        out["windows"][name] = {"T": T[q], "day": L.jst_day(T[q]), "w": w[q] * 1e4, "side": side, "min": mins,
                                "prior_window_move": prior_wm, "n_warm": int(np.sum(warm)), "n_w0": int(np.sum(warm & (w == 0)))}
    return out


EDGE_NOTE = "帯の境は前半の標本から(窓ごとに、前半の数える起点の w の 3 分位。リードの決め 2)。境は前半の標本の中で決めたので、前半の帯の件数は作りからして等しい。境を試しているのは後半だけ"


def band_edges(days: L.Days, day: np.ndarray, w: np.ndarray):
    first = days.parts()["前半"]
    m = (day >= first[0]) & (day <= first[-1])
    if not m.any():
        return None
    q1, q2 = np.quantile(w[m], [1 / 3, 2 / 3])
    return float(q1), float(q2)


def bands_of(edges):
    q1, q2 = edges
    return {f"w < {q1:.2f}": (-np.inf, q1), f"{q1:.2f} ≤ w < {q2:.2f}": (q1, q2), f"w ≥ {q2:.2f}": (q2, np.inf)}


def count(g: L.Grid, days: L.Days, lo: int, hi: int) -> dict:
    """件数の数え上げ: 窓ごとの起点の数(温まりの後・w > 0・前の向き ≠ 0)と、前の向き 0 の数、帯ごとの数。当たりは計算しない。"""
    e, x, cs = prep(g)
    T = origins(g, lo, hi)
    lines, info = [], {}
    for name, wn in WINDOWS.items():
        a, w, warm, k = widths(e, x, cs, T, wn)
        use = warm & (w > 0)
        kp = np.searchsorted(e, T - wn, side="right") - 1
        prior = np.where(use & (kp >= 0), np.sign(a - x[np.maximum(kp, 0)]), 0)
        cnt = use & (prior != 0)
        d = L.jst_day(T)
        ww = w * 1e4
        edges = band_edges(days, d[cnt], ww[cnt])
        cols = {"前の向き 0(数えない)": d[use & (prior == 0)]}
        if edges:
            for b, (lo_, hi_) in bands_of(edges).items():
                cols[f"帯 {b}"] = d[cnt & (ww >= lo_) & (ww < hi_)]
        lines += ["", f"### 窓 {name}(境: {EDGE_NOTE}: {edges[0]:.3f}・{edges[1]:.3f} bp)" if edges else f"### 窓 {name}", ""]
        lines += L.count_table(days, d[cnt], f"数える起点 {name}", cols)
        info[name] = {"counted": int(cnt.sum()), "prior0": int(np.sum(use & (prior == 0))), "w0": int(np.sum(warm & (w == 0))),
                      "warmup": int(np.sum(~warm)), "band_edges_bp_first_half": edges}
    return {"lines": lines, "per_window": info}


def _share(days, d, num, den, nums, ci=True):
    acc = L.DayAcc(days, ("num", "den"))
    acc.add(d, num=num, den=den)
    s = acc.sub(nums)
    return L.ratio_ci(s["num"], s["den"], ci)


def _cont(days, wv, nums, mask, ci=True):
    """続きの割合と、前が上・前が下・流れを抜いた値(決着した起点だけ)。"""
    d, side, pr = wv["day"], wv["side"], wv["prior_window_move"]
    ok = mask & (side != 0) & (pr != 0)
    cont = (side == pr).astype(float)
    res = {"cont": _share(days, d[ok], cont[ok], 1.0, nums, ci)}
    acc = L.DayAcc(days, ("cu", "nu", "cd", "nd"))
    up, dn = ok & (pr > 0), ok & (pr < 0)
    acc.add(d[up], cu=cont[up], nu=1.0)
    acc.add(d[dn], cd=cont[dn], nd=1.0)
    s = acc.sub(nums)
    res["after_up"] = L.ratio_ci(s["cu"], s["nu"], ci)
    res["after_down"] = L.ratio_ci(s["cd"], s["nd"], ci)
    if s["nu"].sum() > 0 and s["nd"].sum() > 0:
        r = {"est": float(0.5 * (s["cu"].sum() / s["nu"].sum() + s["cd"].sum() / s["nd"].sum()))}
        if ci:
            r.update(L._boot(len(nums), lambda i: 0.5 * (s["cu"][i].sum() / s["nu"][i].sum() + s["cd"][i].sum() / s["nd"][i].sum())))
        res["detrended"] = r
    else:
        res["detrended"] = {"est": None}
    inp = mask & (pr != 0) & (d >= nums[0]) & (d <= nums[-1])
    res["origins"] = int(inp.sum())
    res["unresolved"] = int(np.sum(inp & (side == 0)))
    res["min_q"] = L.quantiles(wv["min"][inp & (side != 0)])
    return res


def tables(res: dict) -> tuple:
    days = res["days"]
    md = ["# # 7 カード 7: 毎時の起点から引いた上下の線のどちらに先に当たるか(D1b)", "",
          "幅 w = 窓の √Σr²(カードと同じ)。終値で判定。前の向き = 起点の前の、同じ長さの窓の値動きの符号(window_move)。"
          "続き = 当たりの向き == 前の向き。基準 0.5。区間 = 日の塊(循環 5 日・1,000 回・種 20261006)。MDE = 2.8 × se。"
          f"{EDGE_NOTE}。", "",
          "| 窓 | 帯 | 期間 | 起点 | 未決着 | 続きの割合 [区間] | MDE | 前が上 → 続き [区間] | 前が下 → 続き [区間] | 流れを抜いた値 [区間] | MDE | 当たるまでの分 50/90 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    obj = {"periods": days.describe(), "edge_note": EDGE_NOTE, "windows": {}}
    diffs = ["", "## 幅の帯どうしの差(続きの割合の 低い帯 − 高い帯。同じ日の抽き直しで両方を作る g2lib.diff_ratio_ci)", "",
             "| 窓 | 期間 | 低い帯 − 高い帯 [区間] | MDE |", "|---|---|---|---|"]
    for name, wv in res["windows"].items():
        pr = wv["prior_window_move"]
        cnt = pr != 0
        edges = band_edges(days, wv["day"][cnt], wv["w"][cnt])
        obj["windows"][name] = {"n_warm": wv["n_warm"], "n_w0": wv["n_w0"], "prior0": int(np.sum(pr == 0)),
                                "band_edges_bp_first_half": edges, "cont": {}}
        masks = {"全部": np.ones(len(pr), dtype=bool)}
        if edges:
            masks.update({b: (wv["w"] >= a) & (wv["w"] < c) for b, (a, c) in bands_of(edges).items()})
        for bname, bm in masks.items():
            for pname, nums in days.parts().items():
                r = _cont(days, wv, nums, bm)
                obj["windows"][name]["cont"].setdefault(bname, {})[pname] = r
                md.append(f"| {name} | {bname} | {pname} | {r['origins']} | {r['unresolved']} | {L.fci(r['cont'])} | {L.fmde(r['cont'])} | "
                          f"{L.fci(r['after_up'])} | {L.fci(r['after_down'])} | {L.fci(r['detrended'])} | {L.fmde(r['detrended'])} | "
                          f"{L.f(r['min_q']['50'], 0)}/{L.f(r['min_q']['90'], 0)} |")
        md.append(f"| {name} | 前の向き 0 で数えない起点 | 全期間 | {int(np.sum(pr == 0))} | | | | | | | | |")
        if edges:
            bl = list(bands_of(edges).items())
            obj["windows"][name]["diff_low_minus_high"] = {}
            for pname, nums in days.parts().items():
                parts_ = []
                for _, (a_, c_) in (bl[0], bl[2]):
                    bm = (wv["w"] >= a_) & (wv["w"] < c_)
                    ok = bm & (wv["side"] != 0) & (pr != 0)
                    acc = L.DayAcc(days, ("num", "den"))
                    acc.add(wv["day"][ok], num=(wv["side"][ok] == pr[ok]).astype(float), den=1.0)
                    parts_.append(acc.sub(nums))
                dd = L.diff_ratio_ci(parts_[0]["num"], parts_[0]["den"], parts_[1]["num"], parts_[1]["den"])
                obj["windows"][name]["diff_low_minus_high"][pname] = dd
                diffs.append(f"| {name} | {pname} | {L.fci(dd)} | {L.fmde(dd)} |")
    md += diffs
    md += ["", "## 年ごと(記述。区間なし)", "", "| 窓 | 帯 | 年 | 起点 | 続きの割合 | 流れを抜いた値 |", "|---|---|---|---|---|---|"]
    for name, wv in res["windows"].items():
        pr = wv["prior_window_move"]
        edges = obj["windows"][name]["band_edges_bp_first_half"]
        masks = {"全部": np.ones(len(pr), dtype=bool)}
        if edges:
            masks.update({b: (wv["w"] >= a) & (wv["w"] < c) for b, (a, c) in bands_of(edges).items()})
        for bname, bm in masks.items():
            for y, nums in days.years().items():
                r = _cont(days, wv, nums, bm, ci=False)
                obj["windows"][name]["cont"][bname].setdefault("years", {})[y] = r
                md.append(f"| {name} | {bname} | {y} | {r['origins']} | {L.f(r['cont']['est'])} | {L.f(r['detrended']['est'])} |")
    return md, obj


def write_records(path: str, res: dict) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        fh.write("window,T,w_bp,side,minutes,prior_window_move\n")
        for name, wv in res["windows"].items():
            for k in range(len(wv["T"])):
                fh.write(f"{name},{L.ns_iso(int(wv['T'][k]))},{wv['w'][k]:.6g},{int(wv['side'][k])},{int(wv['min'][k])},"
                         f"{int(wv['prior_window_move'][k])}\n")

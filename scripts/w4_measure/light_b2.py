"""W4 第 2 陣の軽い測定と軽い診断(run_b2.py から呼ぶ。保存した npz からも呼べる)。

式(このファイルの FORMULA を各 extra.json・diagnostics.json に写す):
FORMULA = 下の文字列。
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "measure"))

from daily_stats import daily_stats  # noqa: E402
from post import write_json  # noqa: E402

from bot.research.cards.measure import daily_rows, write_daily  # noqa: E402

NS = 1_000_000_000
MIN_NS = 60 * NS
HOUR_NS = 3600 * NS
DAY_NS = 86_400 * NS
JST = 9 * HOUR_NS
LAG = 60 * NS

FORMULA = """
P_t: bot.research.cards.pnl.pnl の pnl_bp(e_t × (open_{t+2} / open_{t+1} − 1) × 10,000、t+1・t+2 は次の空でない足。最後の 2 決定は P なし)。
日 = 決定の時刻 t の日本時間の日。S_d = その日の P_t の合計。
sum|Δe| = Σ_k |e_k − e_{k−1}|(全決定の持ち高 e、決定の順)。
取引 = P のある決定を順に並べ、sign(e) が同じで 0 でない決定がつながった最長の区間(+1 から −1 へ直接変われば 2 つの取引)。
  取引の損益 = その区間の P_t の合計。勝率 = 損益 > 0 の取引の割合。
  保有(決定) = 区間の決定の数。保有(分) = 区間の hold_ns(約定の足の始値 → 次の決定の約定の足の始値)の合計 ÷ 60 秒
  = 最初の約定から最後の手仕舞いまでの壁時計の分。取引/日 = 取引の数 ÷ 日の数(決定のある日本時間の日)。
最大の落ち込み = 日本時間の日ごとの累積 C_d = Σ_{d'≤d} S_{d'} について max_d (max_{d'≤d} C_{d'} − C_d)(始まりの 0 を含む)。
最悪の日 = min S_d。月 = 日本時間の暦月。最悪の月 = 月ごとの S_d の合計の最小。プラスの月の割合 = 合計 > 0 の月の数 ÷ 月の数。
買い・売り = e > 0 の決定の P の合計と数 / e < 0 の決定の P の合計と数。
""".strip()


def _sign(x):
    return np.sign(x).astype(np.int8)


def extra_stats(p, e_all, n_days):
    out = {"formula": FORMULA}
    d = np.abs(np.diff(e_all))
    out["sum_abs_de"] = float(d.sum())
    out["mean_abs_de"] = float(d.sum() / (len(e_all) - 1))
    s = _sign(p.exposure)
    P = p.pnl_bp
    brk = np.flatnonzero(np.diff(s) != 0) + 1
    starts = np.concatenate([[0], brk])
    keep = s[starts] != 0
    tp = np.add.reduceat(P, starts)[keep]
    tn = np.diff(np.concatenate([starts, [len(s)]]))[keep]
    th = np.add.reduceat(p.hold_ns.astype(np.float64), starts)[keep] / MIN_NS
    tside = s[starts][keep]
    nt = int(len(tp))
    out["trades"] = {
        "n": nt, "per_day": nt / n_days if n_days else None,
        "mean_bp": float(tp.mean()) if nt else None, "median_bp": float(np.median(tp)) if nt else None,
        "win_rate": float(np.mean(tp > 0)) if nt else None, "loss_rate": float(np.mean(tp < 0)) if nt else None,
        "zero_rate": float(np.mean(tp == 0)) if nt else None,
        "hold_decisions_median": float(np.median(tn)) if nt else None,
        "hold_minutes_median": float(np.median(th)) if nt else None,
        "hold_minutes_mean": float(th.mean()) if nt else None,
        "long": {"n": int((tside > 0).sum()), "sum_bp": float(tp[tside > 0].sum()),
                 "win_rate": float(np.mean(tp[tside > 0] > 0)) if (tside > 0).any() else None},
        "short": {"n": int((tside < 0).sum()), "sum_bp": float(tp[tside < 0].sum()),
                  "win_rate": float(np.mean(tp[tside < 0] > 0)) if (tside < 0).any() else None},
        "best_bp": float(tp.max()) if nt else None, "worst_bp": float(tp.min()) if nt else None,
    }
    out["long_short_decisions"] = {
        "long": {"n": int((p.exposure > 0).sum()), "sum_bp": float(P[p.exposure > 0].sum())},
        "short": {"n": int((p.exposure < 0).sum()), "sum_bp": float(P[p.exposure < 0].sum())},
    }
    day = (p.t_ns + JST) // DAY_NS
    uniq, inv = np.unique(day, return_inverse=True)
    S = np.bincount(inv, weights=P)
    C = np.concatenate([[0.0], np.cumsum(S)])
    peak = np.maximum.accumulate(C)
    dd = peak - C
    k = int(np.argmax(dd))
    kp = int(np.argmax(C[:k + 1])) if k > 0 else 0
    lab = lambda i: str(np.datetime64(int(uniq[i]) * DAY_NS, "ns").astype("datetime64[D]"))  # noqa: E731
    out["drawdown"] = {"max_bp": float(dd.max()),
                       "peak_day": lab(kp - 1) if kp > 0 else "(始まり)", "trough_day": lab(k - 1) if k > 0 else None,
                       "final_cum_bp": float(C[-1])}
    w = int(np.argmin(S))
    b = int(np.argmax(S))
    out["worst_day"] = {"day": lab(w), "bp": float(S[w])}
    out["best_day"] = {"day": lab(b), "bp": float(S[b])}
    months = (uniq * DAY_NS).astype("datetime64[ns]").astype("datetime64[M]")
    mu, minv = np.unique(months, return_inverse=True)
    M = np.bincount(minv, weights=S)
    wm = int(np.argmin(M))
    out["month"] = {"n": int(len(M)), "positive_share": float(np.mean(M > 0)), "zero_share": float(np.mean(M == 0)),
                    "worst": {"month": str(mu[wm]), "bp": float(M[wm])},
                    "best": {"month": str(mu[int(np.argmax(M))]), "bp": float(M.max())}}
    return out, {"trade_pnl": tp, "trade_n": tn, "trade_side": tside, "trade_start": starts[keep]}


# ---------- 診断 ----------

def diag_c5(run, p, fx_rows):
    """INTENT_MAP §4-1(日本時間の時ごと)・§5(9 時 55 分に終わる足が空)・§4-2(USDJPY との符号の一致)。"""
    from bot.research.cards.library.c5_tokyo_fix_momentum import FIX_TOD_NS, jst_weekday
    out = {}
    e, P, t = p.exposure, p.pnl_bp, p.t_ns
    hr = ((t + JST) // HOUR_NS) % 24
    h = {}
    for x in range(24):
        m = (hr == x) & (e != 0)
        if m.any():
            h[f"{x:02d}"] = {"n_held": int(m.sum()), "sum_bp": float(P[m].sum()), "mean_bp_per_held_minute": float(P[m].mean()),
                             "long_n": int((m & (e > 0)).sum()), "short_n": int((m & (e < 0)).sum())}
    out["4-1_hour_jst_held"] = {"what": "持ち高 e ≠ 0 の決定(P のあるもの)を、決定の時刻 t の日本時間の時で分けた。"
                                        "9 時台は t ≤ 9:54 の決定(9:55 に終わる足は 0)", "by_hour": h}
    dec = np.flatnonzero(run.decided)
    end = run.end_ns[dec]
    ex = run.exposure[dec]
    s_day = (run.start_ns[dec] + JST) // DAY_NS
    days = np.unique(s_day)
    wd = np.array([jst_weekday(int(x)) for x in days])
    wdays = days[wd < 5]
    F = wdays * DAY_NS - JST + FIX_TOD_NS
    has_F = np.isin(F, end)
    # その日の 9:55 より前の最後の決定(日本時間 0 時より後)
    i_last = np.searchsorted(end, F, side="left") - 1
    D0 = wdays * DAY_NS - JST
    valid = (i_last >= 0) & (end[np.clip(i_last, 0, None)] > D0)
    e_last = np.where(valid, ex[np.clip(i_last, 0, None)], 0.0)
    carried = (~has_F) & valid & (e_last != 0)
    # 持ち越した決定の P(pnl の bar は run の足の番号)
    pos = {int(b): k for k, b in enumerate(p.bar)}
    carried_bars = dec[i_last[carried]]
    Pc = np.array([P[pos[int(b)]] for b in carried_bars if int(b) in pos])
    hold_c = np.array([p.hold_ns[pos[int(b)]] for b in carried_bars if int(b) in pos]) / MIN_NS
    out["5_fix_bar_empty"] = {
        "what": "平日(日本時間)のうち、9:55 JST に終わる足(9:54 に始まる足)に約定が無く、カードが仲値の時刻で呼ばれなかった日。"
                "そのうち 9:55 より前の最後の決定の持ち高が 0 でなく、仲値の後の値動きまで持ち越した日の数と、その決定の P",
        "n_weekdays_with_decisions": int(len(wdays)), "n_fix_bar_missing": int((~has_F).sum()),
        "n_carried_past_fix": int(carried.sum()), "carried_sum_bp": float(Pc.sum()) if len(Pc) else 0.0,
        "carried_hold_minutes_median": float(np.median(hold_c)) if len(hold_c) else None,
        "missing_by_year": {str(y): int(((~has_F) & (np.datetime_as_string((wdays * DAY_NS).astype("datetime64[ns]"),
                                                                                 unit="Y").astype(int) == y)).sum())
                            for y in range(2015, 2024)}}
    if fx_rows is not None:
        rt, rv = fx_rows
        hi_ok = rt[-1] + LAG  # 置き場の最後の行が使えるようになる時刻
        m = (e != 0) & (t >= rt[0] + LAG) & (t <= hi_ok)
        D0t = ((t + JST) // DAY_NS) * DAY_NS - JST
        ia = np.searchsorted(rt + LAG, t, side="right") - 1
        i0 = np.searchsorted(rt + LAG, D0t, side="right") - 1
        ok = m & (i0 >= 0)
        mv = np.where(ok, rv[np.clip(ia, 0, None)] - rv[np.clip(i0, 0, None)], np.nan)
        su = np.sign(mv)
        agree = ok & (su == np.sign(e))
        dis = ok & (su == -np.sign(e))
        zero = ok & (su == 0)
        out["4-2_usdjpy_sign"] = {
            "what": "持ち高 e ≠ 0 の決定について、USDJPY の日本時間 0 時から t までの動き = (t までに使えるようになった最新の行の close) − "
                    "(日本時間 0 時までに使えるようになった最新の行の close)(行の時刻 = 置き場の timestamp、使えるのは +60 秒)の符号と、"
                    "e の符号の一致。置き場の範囲(最初の行 + 60 秒 〜 最後の行 + 60 秒)の決定だけ",
            "range": [str(np.datetime64(int(rt[0]), "ns")), str(np.datetime64(int(rt[-1]), "ns"))],
            "n_held_in_range": int(ok.sum()), "agree_share": float(agree.sum() / ok.sum()) if ok.sum() else None,
            "agree": {"n": int(agree.sum()), "sum_bp": float(P[agree].sum()), "mean_bp": float(P[agree].mean()) if agree.any() else None},
            "disagree": {"n": int(dis.sum()), "sum_bp": float(P[dis].sum()), "mean_bp": float(P[dis].mean()) if dis.any() else None},
            "usdjpy_flat": {"n": int(zero.sum()), "sum_bp": float(P[zero].sum())},
        }
    out["not_computed"] = {"4-3 祝日": "暦が無い(INTENT_MAP 4-3)。祝日・年末年始を含めて測った",
                           "4-4 海外の時間帯の対照": "原文に時刻が無い(INTENT_MAP 4-4)", "4-5 流れ": "観測する系列が無い"}
    return out


def week_opens(rt, rv):
    """カード 6 と同じ決まり(新しい日本時間の週の行のうち、前の週の最後の close と違う最初の行)を台本で書き直したもの。
    戻り: (r の配列, g_usdjpy の配列)。"""
    week = ((rt + JST) // DAY_NS + 3) // 7
    out_r, out_g = [], []
    armed, ref = False, None
    pw, pc = None, None
    wl = week.tolist()
    vl = rv.tolist()
    tl = rt.tolist()
    for i in range(len(tl)):
        w, c = wl[i], vl[i]
        if pw is not None and w > pw:
            armed, ref = True, pc
        if pc is not None and c != pc and armed:
            armed = False
            out_r.append(tl[i])
            out_g.append(math.log(c) - math.log(ref))
        pw, pc = w, c
    return np.array(out_r, dtype=np.int64), np.array(out_g)


def diag_c6(variant, run, p, fx_rows):
    rt, rv = fx_rows
    r, g = week_opens(rt, np.asarray(rv, dtype=float))
    dec = np.flatnonzero(run.decided)
    end = run.end_ns[dec]
    ex = run.exposure[dec]
    lo, hi = int(end[0]), int(end[-1])
    sel = (r + LAG <= hi) & (r + LAG >= int(run.start_ns[0]))
    r, g = r[sel], g[sel]
    dt = r.astype("datetime64[ns]")
    wd = ((r // DAY_NS) + 3) % 7  # UTC の曜日(月 = 0)
    hu = (r // HOUR_NS) % 24
    tab = {}
    for a, b in zip(wd.tolist(), hu.tolist()):
        k = f"{['月','火','水','木','金','土','日'][a]} {b:02d}時"
        tab[k] = tab.get(k, 0) + 1
    n = len(r)
    sun15 = int(((wd == 6) & (hu == 15)).sum())
    out = {"week_open_rows": {
        "what": "台本で書き直した週明けの行 r(行の時刻 = 1 分の始まり、UTC)の曜日と時ごとの数(INTENT_MAP §5 の確かめ)。"
                "日曜 15 時 UTC に集まっていれば C-5 が効いていない",
        "n": n, "first": str(dt[0]) if n else None, "last": str(dt[-1]) if n else None,
        "by_utc_weekday_hour": dict(sorted(tab.items(), key=lambda kv: -kv[1])), "n_sunday_15utc": sun15}}
    # 持ち高が書き直しと合うか
    inwin = np.zeros(len(end), dtype=bool)
    exp_sign = np.zeros(len(end))
    i0 = np.searchsorted(end, r + LAG, side="left")
    i1 = np.searchsorted(end, r + HOUR_NS, side="left")
    for a, b, gg in zip(i0, i1, g):
        inwin[a:b] = True
        exp_sign[a:b] = -np.sign(gg)
    outside_nonzero = int(((~inwin) & (ex != 0)).sum())
    chk = {"decisions_in_windows": int(inwin.sum()), "nonzero_outside_windows": outside_nonzero}
    if variant == "usdjpy":
        chk["in_window_sign_mismatch"] = int((inwin & (ex != exp_sign)).sum())
    else:
        chk["in_window_zero"] = int((inwin & (ex == 0)).sum())
        chk["in_window_nonzero"] = int((inwin & (ex != 0)).sum())
    out["check_against_rewrite"] = {"what": "決定 t が [r + 60 秒, r + 3,600 秒) にある足だけ持ち高が 0 でないか(usdjpy は向き −sign(g) まで)", **chk}
    has_end = np.isin(r + HOUR_NS, end)
    last_in = i1 - 1
    carried = (~has_end) & (last_in >= i0) & (ex[np.clip(last_in, 0, None)] != 0)
    out["hour_end_bar_empty"] = {"what": "r + 1 時間に終わる足に約定が無く、窓の最後の決定の持ち高 0 でないまま次の約定のある足まで残った週の数",
                                 "n_week_opens": n, "n_end_bar_missing": int((~has_end).sum()), "n_carried": int(carried.sum())}
    # 週ごとの持ち高の向き(4-3 の突き合わせのため)
    first_e = np.array([ex[a] if a < b else 0.0 for a, b in zip(i0, i1)])
    out["per_week"] = {"r_ns": r.tolist(), "g_usdjpy": g.tolist(), "first_exposure_in_window": first_e.tolist()}
    out["not_computed"] = {"4-1 別の市場の週末": "日経 225 先物・CME は測っていない(リードの決定に無い)",
                           "4-2 USDJPY の値段に当てた損益": "USDJPY の足にカードを走らせる形。リードの決定に無いので測っていない",
                           "4-4 流れ": "観測する系列が無い"}
    return out


def diag_c7(run, p):
    e = run.exposure[run.decided]
    nz = np.flatnonzero(e != 0)
    flips = int(np.sum((e[1:] * e[:-1]) < 0))
    return {"exposure_only": {
        "what": "持ち高の系列だけから出せる数。持ち高が変わる = 前の当たりと逆の側の線に当たった(反転)。同じ側に当たった(継続)は持ち高が変わらないので、この系列からは数えられない",
        "first_nonzero_decision_time": str(np.datetime64(int(run.end_ns[run.decided][nz[0]]), "ns")) if len(nz) else None,
        "n_sign_flips": flips},
        "not_computed": {"4-1 レースの長さの分布・4-2 幅 w の分布・4-3 継続と反転の数": "カードの関数は起点の更新を外に出していない。"
                         "測定の側で同じ規則を書き直すか、関数に記録の口を足すかはリードが決める(INTENT_MAP 4-3・CARD.md 迷った点 5)。この回は出していない"}}


def diag_c8(variant, run, p):
    from bot.research.cards.library.c8_session_mean_revert import BAR_NS, SESSIONS
    off = SESSIONS[variant]
    dec = np.flatnonzero(run.decided)
    end = run.end_ns[dec]
    ex = run.exposure[dec]
    close = run.close[dec]
    vol = run.volume[dec]
    ses = (end - BAR_NS + off) // DAY_NS
    at_end = ((end + off) % DAY_NS) == 0
    brk = np.flatnonzero(np.diff(ses) != 0) + 1
    starts = np.concatenate([[0], brk])
    stops = np.concatenate([brk, [len(ses)]])
    e_mean = np.empty(len(ses))
    e_vwap = np.empty(len(ses))
    for a, b in zip(starts, stops):
        c = close[a:b]
        cs = np.cumsum(c)
        mean = cs / np.arange(1, b - a + 1)
        e_mean[a:b] = -np.sign(c - mean)
        cv = np.cumsum(c * vol[a:b])
        vw = cv / np.cumsum(vol[a:b])
        e_vwap[a:b] = -np.sign(c - vw)
    e_mean[at_end] = 0.0
    e_vwap[at_end] = 0.0
    out = {"rewrite_check": {"what": "台本で書き直した平均(セッションごとの np.cumsum ÷ 本数)の持ち高とカードの持ち高の食い違いの数",
                             "n_mismatch": int(np.sum(e_mean != ex))}}
    out["4-2_vwap_vs_mean"] = {"what": "平均の代わりに量の重みの平均(VWAP = Σ close × volume ÷ Σ volume、セッションの中の呼ばれた足、"
                                       "今の足を含む)を使った持ち高が、カードの持ち高と違う決定の割合",
                               "n_decisions": int(len(ex)), "differ_share": float(np.mean(e_vwap != ex))}
    # 区切りをまたいだ持ち高(INTENT_MAP §5 の I-5 の例外)
    last = stops - 1
    carry = (~at_end[last]) & (ex[last] != 0)
    carry = carry[:-1]  # 最後のセッションの後には区切りが無い(期間の終わり)
    pos = {int(b): k for k, b in enumerate(p.bar)}
    Pc, mins = [], []
    for k in np.flatnonzero(carry):
        bi = int(dec[last[k]])
        B = (int(ses[last[k]]) + 1) * DAY_NS - off
        if bi in pos:
            j = pos[bi]
            Pc.append(p.pnl_bp[j])
            ex_open = int(run.start_ns[p.exit_bar[j]])
            mins.append(max(0, ex_open - B) / MIN_NS)
    out["5_boundary_carry"] = {"what": "セッションの最後の 1 分に約定が無く、区切りの前の最後の決定の持ち高 ≠ 0 のまま区切りをまたいだ回数、"
                                       "その決定の P の合計、区切りの後に持っていた分(次の決定の約定の足の始値 − 区切り)",
                               "n_sessions": int(len(starts)), "n_carried": int(carry.sum()),
                               "carried_sum_bp": float(np.sum(Pc)), "minutes_after_boundary_total": float(np.sum(mins)),
                               "minutes_after_boundary_median": float(np.median(mins)) if mins else None}
    out["not_computed"] = {"4-1 区切りを 24 通りずらした対照": "原文に無い形。リードの決定に無いので測っていない"}
    return out


def measure(card, variant, run, p, outdir, lo, hi, fx_all=None):
    os.makedirs(outdir, exist_ok=True)
    sha_daily = write_daily(daily_rows(p, "Asia/Tokyo"), os.path.join(outdir, "daily.csv"))
    e_all = run.exposure[run.decided]
    ds = daily_stats(p.t_ns, p.pnl_bp, e_all)
    ds["daily_csv_sha256"] = sha_daily
    write_json(ds, os.path.join(outdir, "daily_stats.json"))
    ex, _tr = extra_stats(p, e_all, ds["overall"]["n_days"])
    write_json(ex, os.path.join(outdir, "extra.json"))
    if card == "c5":
        fx_rows = None
        try:
            fx_rows = _usdjpy_for_c5()
        except Exception as exc:  # 読めなければ理由を書く
            diag_err = f"{type(exc).__name__}: {exc}"
        else:
            diag_err = None
        dg = diag_c5(run, p, fx_rows)
        if diag_err:
            dg["4-2_usdjpy_sign"] = {"not_computed": diag_err}
    elif card == "c6":
        dg = diag_c6(variant, run, p, (fx_all[0], np.asarray(fx_all[1], dtype=float)))
    elif card == "c7":
        dg = diag_c7(run, p)
    elif card == "c4":
        dg = {"note": "カード 4 の診断(負けの場面)は測定の後に別に出す"}
    else:
        dg = diag_c8(variant, run, p)
    write_json(dg, os.path.join(outdir, "diagnostics.json"))
    ov, c1, c5 = ds["overall"], ds["ci"]["block_1d"], ds["ci"]["block_5d"]
    return {"n_decisions": ov["n_decisions"], "n_days": ov["n_days"], "per_day_bp": ov["per_day_bp"],
            "per_minute_bp": ov["per_minute_bp"], "ci_1d_per_day": c1["per_day_bp"]["ci"],
            "ci_5d_per_day": c5["per_day_bp"]["ci"], "mde_1d_per_day": c1["per_day_bp"]["mde"],
            "nonzero_share": ds["frequency"]["nonzero_share"], "changes": ds["frequency"]["changes"],
            "sum_abs_de": ex["sum_abs_de"], "trades": ex["trades"], "drawdown": ex["drawdown"],
            "worst_day": ex["worst_day"], "month": ex["month"],
            "year_per_day_bp": {y: v["per_day_bp"] for y, v in ds["year"].items()}}


C5_FX_INPUT = {}


def _usdjpy_for_c5():
    """カード 5 の診断 4-2 のための USDJPY(封印の門の load_reference。宣言はカード 6 の CARD.md の usdjpy_close と同じ
    lag 60 秒。カード 5 の CARD.md には参照の宣言が無いため)。"""
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "measure"))
    from common import ROOT, iso, usdjpy_ref_dataset
    from bot.bt.data.reference import load_reference
    from bot.research.cards import cardmd
    with open(os.path.join(ROOT, "docs/RESEARCH/cards/c6_weekend_gap_revert/CARD.md"), encoding="utf-8") as fh:
        st, _ = cardmd.settings(cardmd.parse(fh.read()))
    decl = dict(st.declarations)
    s = load_reference(ROOT, usdjpy_ref_dataset("usdjpy_close", iso("2017-08-01T00:00:00Z"), iso("2022-12-31T15:00:00Z")),
                       declarations=decl)
    C5_FX_INPUT["manifest"] = [list(m) for m in s.manifest]
    C5_FX_INPUT["decl"] = decl.get("usdjpy_close")
    return np.array(s.times_ns, dtype=np.int64), np.array(s.values, dtype=float)

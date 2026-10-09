"""カード 9 のやり直しの表(2026-10-05)。保存済みの走らせ (a) の出力と、生の約定(起点の値段の当て直しだけ)を読む。
状態機械は回さない。台本の試験は無い(【試験の無い台本の値】)。

入力: data/c9_run_a/full_20230625_20241014/(policy_cascades・anchors_prints・anchors_bundles・controls・chunks/scurve)、
      backtest_data/binance_cm_o3c_20260913/aggTrades/BTCUSD_PERP/*.zip(起点の値段の当て直しだけ)。
区間: 日の塊(循環、5 日・1,000 回・種 20261004)。日 = UTC の日(走らせの `day`)。前半・後半 = 472 日の半分(境 2024-02-19 = 作る/測る の境)。
    PYTHONPATH=src python3 docs/RESEARCH/cards/c9_liquidation_cascade/redo2_2026-10-05/c9_redo.py
出力: このフォルダの C9_TABLES.md・s_curve_full.csv・p0_side.csv.gz
"""
import glob
import io
import os
import sys
import zipfile

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/user/trade/scripts/analysis")
sys.path.insert(0, "/home/user/trade/src")
import diag_tables as dt  # noqa: E402

RUN = "/home/user/trade/data/c9_run_a/full_20230625_20241014/"
AGG = "/home/user/trade/backtest_data/binance_cm_o3c_20260913/aggTrades/BTCUSD_PERP/"
HS = [1, 5, 10, 30, 60, 300, 900, 1800, 3600, 14400, 86400, 604800]
HNAME = {1: "1 秒", 5: "5 秒", 10: "10 秒", 30: "30 秒", 60: "60 秒", 300: "5 分", 900: "15 分", 1800: "30 分",
         3600: "1 時間", 14400: "4 時間", 86400: "1 日 [記述]", 604800: "1 週 [記述]"}
for _h in (900, 1800, 3600, 14400):
    HNAME[_h] += " [記述]"
OUT = []


def w(s=""):
    OUT.append(s)


def f2(q, nd=2):
    if q is None or q.get("per_trade" if "per_trade" in q else "mean") is None:
        return "—"
    v = q["per_trade"] if "per_trade" in q else q["mean"]
    if q.get("lo") is None:
        return f"{v:+.{nd}f}(区間なし)"
    return f"{v:+.{nd}f} [{q['lo']:+.{nd}f}, {q['hi']:+.{nd}f}]"


def ratio(days, df, col, daycol="day"):
    g = df.groupby(daycol)[col]
    return dt.group_ratio_ci(days, g.sum().to_dict(), g.count().to_dict())


def main():
    pc = pd.read_csv(RUN + "policy_cascades.csv.gz")
    # L-920: 連鎖の損益(レグの和)は %(pnl_pct)。前の走らせの出力は pnl_bp(bp)なので / 100 して読む
    if "pnl_pct" not in pc.columns and "pnl_bp" in pc.columns:
        pc["pnl_pct"] = pc["pnl_bp"] / 100
    days = sorted(pc["day"].unique())
    half = len(days) // 2
    parts = {"全期間": days, "前半": days[:half], "後半": days[half:]}
    w("# カード 9 のやり直しの表(走らせ (a) の保存済みの出力から。値動きは bp、連鎖・レグの損益の和は %(L-920)、経費の前、Binance COIN-M BTCUSD_PERP の約定の値段)")
    w("")
    w(f"日 = UTC の日 {len(days)} 日({days[0]}〜{days[-1]})。前半 {half} 日・後半 {len(days) - half} 日、境 {days[half]}。【試験の無い台本の値】")
    w("")

    # ---------------- D1 方策ごとの日ごとの和
    w("## D1 方策ごとの 1 日あたり(%/日、その日の連鎖の損益の和。連鎖の無い日は 0)と 1 連鎖あたり")
    w("")
    w("| 判断の出所 | 型 | g 秒 | d 秒 | 連鎖 | NaN | 入った連鎖 | 前半 %/日 [区間] | 後半 %/日 [区間] | 後半 − 前半 [区間] | 結果 | 全期間 1 連鎖あたり [区間] | 前半 1 連鎖あたり | 後半 1 連鎖あたり |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    pols = ["全部順張り", "全部逆張り", "規則_材料1", "規則_3択", "完全な判断"]
    daily = {}
    for pol in pols:
        for typ in (["-"] if pol.startswith("全部") else ["A", "B"]):
            for g in (30, 60, 180):
                for d in (1, 3):
                    q = pc[(pc.policy == pol) & (pc.type == typ) & (pc.gap_s == g) & (pc.delay_s == d)]
                    nan = int(q.pnl_pct.isna().sum())
                    qq = q.dropna(subset=["pnl_pct"])
                    s = qq.groupby("day").pnl_pct.sum().to_dict()
                    x = [s.get(dd, 0.0) for dd in days]
                    daily[(pol, typ, g, d)] = dict(zip(days, x))
                    a, b = dt.mean_ci(x[:half]), dt.mean_ci(x[half:])
                    if pol == "規則_3択":
                        a, df_, out = {"mean": None}, {"mean": None}, "後半だけの値"
                    else:
                        df_ = dt.diff_ci(x[:half], x[half:])
                        out = dt.d1_outcome(a, b, df_)
                    rr = {k: ratio(v, qq, "pnl_pct") for k, v in parts.items()}
                    w(f"| {pol} | {typ} | {g} | {d} | {len(q):,} | {nan} | {int(q.entered.sum()):,} | {f2(a, 4)} | {f2(b, 4)} | {f2(df_, 4)} | {out} | {f2(rr['全期間'], 5)} | {f2(rr['前半'], 5)} | {f2(rr['後半'], 5)} |")
    w("")

    # 年ごと(全部順張り・規則_材料1 A・完全な判断 A、g 60・d 1)
    w("### 年ごと(g 60・d 1。%/日)")
    w("")
    w("| 判断の出所 | 型 | 2023 [区間] | 2024 [区間] |")
    w("|---|---|---|---|")
    for key in [("全部順張り", "-", 60, 1), ("規則_材料1", "A", 60, 1), ("規則_材料1", "B", 60, 1), ("完全な判断", "A", 60, 1), ("完全な判断", "B", 60, 1)]:
        dd = daily[key]
        cells = [f2(dt.mean_ci([dd[x] for x in days if x.startswith(y)]), 4) for y in ("2023", "2024")]
        w(f"| {key[0]} | {key[1]} | {cells[0]} | {cells[1]} |")
    w("")

    # BUY と SELL の束の時間の重なり
    bb = pd.read_csv(RUN + "anchors_bundles.csv.gz")
    w("## 同じ時刻に BUY の束と SELL の束が重なる数(束の [始まり, 終わり = 最後 + g])")
    w("")
    w("| g 秒 | 束 | 反対側の束と重なる束 | 割合 |")
    w("|---|---|---|---|")
    for g in (30, 60, 180):
        q = bb[bb.gap_s == g]
        tot = 0
        for sd, od in (("BUY", "SELL"), ("SELL", "BUY")):
            a_ = q[q.side == sd]
            o = q[q.side == od].sort_values("start_ms")
            os_, oe = o.start_ms.values, np.maximum.accumulate(o.end_ms.values)
            i = np.searchsorted(os_, a_.end_ms.values, side="right")  # 反対側で、こちらの終わりより前に始まった束の数
            prev_end = np.where(i > 0, oe[np.clip(i - 1, 0, None)], -1)
            tot += int((prev_end > a_.start_ms.values).sum())
        w(f"| {g} | {len(q):,} | {tot:,} | {tot / len(q):.3f} |")
    w("")

    # ---------------- D5 プリントからの値動きと対照
    pr = pd.read_csv(RUN + "anchors_prints.csv.gz")
    ct = pd.read_csv(RUN + "controls.csv.gz")
    pr["half"] = np.where(pr.day < days[half], "前半", "後半")
    w("## D5 プリントの時点からの値動き(清算の向きに正、bp/プリント)と対照")
    w("")
    w(f"プリント {len(pr):,}。直前 10 秒の値動きが清算の向き(`m10_signed` > 0)の割合 {float((pr.m10_signed > 0).mean()):.3f}、= 0 {float((pr.m10_signed == 0).mean()):.3f}、< 0 {float((pr.m10_signed < 0).mean()):.3f}。")
    w("")
    c2 = ct[ct.kind == "(ii)合わせた時刻"].set_index("ref_id")
    c1 = ct[ct.kind == "(i)無作為"]
    pm = pr.set_index("print_id")
    matched = pm.index.isin(c2.index)
    w(f"対照 (ii) の取れたプリント {int(matched.sum()):,} / {len(pr):,}。取れた・取れなかったの比べ:")
    w("")
    w("| 群 | プリント | SELL の割合 | 束 g60 の位置: 単発 / 最初 / 途中 / 最後 | 数量の中央値(枚) | 直前 60 秒の同じ側の件数 > 0 の割合 | 前半の割合 |")
    w("|---|---|---|---|---|---|---|")
    for nm, m in (("取れた", matched), ("取れなかった", ~matched)):
        q = pm[m]
        pos = q.g60_pos_post.value_counts(normalize=True)
        w(f"| {nm} | {len(q):,} | {float((q.side == 'SELL').mean()):.3f} | {pos.get('単発', 0):.3f} / {pos.get('最初', 0):.3f} / {pos.get('途中', 0):.3f} / {pos.get('最後', 0):.3f} | {float(q.qty.median()):.0f} | {float((q.elapsed_prev_s.notna() & (q.elapsed_prev_s <= 60)).mean()):.3f} | {float((q.half == '前半').mean()):.3f} |")
    w("")
    # (iii) は束の最後のプリントと対に
    w("| h | 期間 | 実物 全部 [区間] | 実物 (ii) の取れた分 | 対照 (ii) | 実物 − 対照 (ii) [区間] | 対照 (i) 無作為(対ではない) | 実物 束 g60 の最後 | 対照 (iii) プラセボ g60 | 最後 − プラセボ [区間] |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    c3 = ct[ct.kind == "(iii)プラセボ_g60"].set_index("ref_id")
    last = pm[pm.g60_pos_post.isin(["最後", "単発"])].reset_index().set_index("g60_bundle")
    c1["half"] = np.where(c1.day < days[half], "前半", "後半")
    for h in HS:
        col = f"react_{h}"
        if col not in pm.columns:
            continue
        for pn, pdays in parts.items():
            sel = pm if pn == "全期間" else pm[pm.half == pn]
            a = ratio(pdays, sel.reset_index(), col)
            sm = sel[sel.index.isin(c2.index)]
            cc = c2.loc[sm.index]
            pair = pd.DataFrame({"day": sm.day.values, "x": sm[col].values, "c": cc[col].values}).dropna()
            pair["d"] = pair.x - pair.c
            b, c, dd = ratio(pdays, pair, "x"), ratio(pdays, pair, "c"), ratio(pdays, pair, "d")
            q1 = c1 if pn == "全期間" else c1[c1.half == pn]
            e = ratio(pdays, q1, col)
            ls = last[last.day.isin(pdays)]
            ls = ls[ls.index.isin(c3.index)]
            p3 = pd.DataFrame({"day": ls.day.values, "x": ls[col].values, "c": c3.loc[ls.index][col].values}).dropna()
            p3["d"] = p3.x - p3.c
            w(f"| {HNAME[h]} | {pn} | {f2(a, 3)} | {f2(b, 3)} | {f2(c, 3)} | {f2(dd, 3)} | {f2(e, 3)} | {f2(ratio(pdays, p3, 'x'), 3)} | {f2(ratio(pdays, p3, 'c'), 3)} | {f2(ratio(pdays, p3, 'd'), 3)} |")
    w("")

    # ---------------- 起点の値段の当て直し(約定の側)
    cache = os.path.join(HERE, "p0_side.csv.gz")
    if os.path.exists(cache):
        side = pd.read_csv(cache)
    else:
        recs = []
        pr_by_day = {k: v for k, v in pr.groupby("day")}
        for f in sorted(glob.glob(AGG + "*.zip")):
            day = f[-14:-4]
            nxt = f.replace(day, str((pd.Timestamp(day) + pd.Timedelta(days=1)).date()))
            if day not in pr_by_day:
                continue
            frames = []
            for ff in (f, nxt):
                if os.path.exists(ff):
                    z = zipfile.ZipFile(ff)
                    frames.append(pd.read_csv(io.TextIOWrapper(z.open(z.namelist()[0])), usecols=["price", "transact_time", "is_buyer_maker"]))
            tr = pd.concat(frames, ignore_index=True)
            t = tr.transact_time.values
            m = tr.is_buyer_maker.astype(str).str.lower().values == "true"
            p = tr.price.values
            tb, pb = t[~m], p[~m]   # 買い手が成行(売りの清算を逆張りで買う側)
            ts_, ps_ = t[m], p[m]   # 売り手が成行
            q = pr_by_day[day]
            ts = q.ts_ms.values
            ib, i_s = np.searchsorted(tb, ts, "left"), np.searchsorted(ts_, ts, "left")
            buy_px = np.where(ib < len(tb), pb[np.clip(ib, 0, len(pb) - 1)], np.nan)
            buy_lag = np.where(ib < len(tb), tb[np.clip(ib, 0, len(tb) - 1)] - ts, np.nan)
            sell_px = np.where(i_s < len(ts_), ps_[np.clip(i_s, 0, len(ps_) - 1)], np.nan)
            sell_lag = np.where(i_s < len(ts_), ts_[np.clip(i_s, 0, len(ts_) - 1)] - ts, np.nan)
            recs.append(pd.DataFrame({"print_id": q.print_id.values, "buy_taker_px": buy_px, "buy_taker_lag_ms": buy_lag,
                                      "sell_taker_px": sell_px, "sell_taker_lag_ms": sell_lag}))
        side = pd.concat(recs, ignore_index=True)
        side.to_csv(cache, index=False, compression="gzip")
    s2 = pr.merge(side, on="print_id", how="left")
    # 逆張りが叩く側: SELL の清算(sign −1)→ 逆張りは買う → 買い手が成行の約定。BUY の清算 → 売り手が成行
    s2["p0_fade"] = np.where(s2.sign < 0, s2.buy_taker_px, s2.sell_taker_px)
    s2["lag_fade"] = np.where(s2.sign < 0, s2.buy_taker_lag_ms, s2.sell_taker_lag_ms)
    s2["p0_follow"] = np.where(s2.sign < 0, s2.sell_taker_px, s2.buy_taker_px)
    w("## 起点の値段の当て直し(約定の側。生の約定を読んで値段だけ当て直した。状態機械は回していない)")
    w("")
    ok = s2.lag_fade <= 300000
    w(f"逆張りが叩く側の最初の約定までの遅れ(ms): 中央値 {float(s2.lag_fade.median()):.0f}・75% {float(s2.lag_fade.quantile(.75)):.0f}・95% {float(s2.lag_fade.quantile(.95)):.0f}。300 秒を越える・無い {int((~ok).sum())}。")
    w("")
    w("| h | 期間 | 逆張りの値動き: 元の起点 p₀ [区間] | 起点 = 逆張りが叩く側の最初の約定 [区間] | 起点 = 順張りが叩く側の最初の約定 [区間] | 起点 = 2 つの中ほど [区間] |")
    w("|---|---|---|---|---|---|")
    for h in [1, 5, 10, 30, 60, 300]:
        col = f"react_{h}"
        pend = s2.p0 * (1 + s2.sign * s2[col] / 1e4)
        base = -s2[col]
        fa = -s2.sign * (pend - s2.p0_fade) / s2.p0_fade * 1e4
        fo = -s2.sign * (pend - s2.p0_follow) / s2.p0_follow * 1e4
        mid = (s2.p0_fade + s2.p0_follow) / 2
        mi = -s2.sign * (pend - mid) / mid * 1e4
        for pn, pdays in parts.items():
            msk = ok & s2.day.isin(pdays)
            cells = []
            for v in (base, fa, fo, mi):
                dfv = pd.DataFrame({"day": s2.day[msk], "v": v[msk]}).dropna()
                cells.append(f2(ratio(pdays, dfv, "v"), 3))
            w(f"| {HNAME[h]} | {pn} | " + " | ".join(cells) + " |")
    w("")

    # ---------------- s 秒の曲線
    rows = []
    for f in sorted(glob.glob(RUN + "chunks/scurve/*.npz")):
        day = os.path.basename(f)[:10]
        z = np.load(f)
        s, v = z["s"], z["v"]
        for j in range(24):
            d = 1 if j < 12 else 3
            h = HS[j % 12]
            x = v[:, j].astype(float)
            ok_ = ~np.isnan(x)
            if not ok_.any():
                continue
            su = np.bincount(s[ok_], weights=x[ok_], minlength=181)
            cn = np.bincount(s[ok_], minlength=181)
            for ss in np.flatnonzero(cn):
                rows.append((day, d, h, int(ss), float(su[ss]), int(cn[ss])))
    sc = pd.DataFrame(rows, columns=["day", "d", "h", "s", "sum", "n"])
    full = []
    for (d, h, s_), q in sc.groupby(["d", "h", "s"]):
        rec = {"d": d, "h": h, "s": s_}
        for pn, pdays in parts.items():
            qq = q[q.day.isin(pdays)]
            r = dt.group_ratio_ci(pdays, qq.set_index("day")["sum"].to_dict(), qq.set_index("day")["n"].to_dict())
            rec[f"{pn}_n"], rec[f"{pn}_mean"], rec[f"{pn}_lo"], rec[f"{pn}_hi"] = r["trades"], r["per_trade"], r["lo"], r["hi"]
        full.append(rec)
    full = pd.DataFrame(full)
    full.to_csv(os.path.join(HERE, "s_curve_full.csv"), index=False)
    w("## s 秒の曲線(最後のプリントから s 秒、同じ側の次が来ないときに逆に入った値動き。建玉の向きに正、bp/件。記述の曲線で方策ではない)")
    w("")
    w("全部の s(1〜180 秒)× d × h は `s_curve_full.csv`。ここには s = 1・2・5・10・30・60・120・180 だけを写した(切った)。")
    w("")
    w("| d 秒 | h | s 秒 | 件数(全期間) | 全期間 [区間] | 前半 [区間] | 後半 [区間] |")
    w("|---|---|---|---|---|---|---|")
    for d in (1, 3):
        for h in HS:
            for s_ in (1, 2, 5, 10, 30, 60, 120, 180):
                r = full[(full.d == d) & (full.h == h) & (full.s == s_)]
                if not len(r):
                    continue
                r = r.iloc[0]
                cell = lambda p: "—" if pd.isna(r[f"{p}_mean"]) else (f"{r[f'{p}_mean']:+.3f} [{r[f'{p}_lo']:+.3f}, {r[f'{p}_hi']:+.3f}]")  # noqa: E731
                w(f"| {d} | {HNAME[h]} | {s_} | {int(r['全期間_n']):,} | {cell('全期間')} | {cell('前半')} | {cell('後半')} |")
    w("")

    # ---------------- D2 場面(全部順張り g60 d1、連鎖の最初のプリントの値)
    base = pc[(pc.policy == "全部順張り") & (pc.gap_s == 60) & (pc.delay_s == 1)].dropna(subset=["pnl_pct"])
    first = pr[pr.g60_k == 0].set_index("g60_bundle")
    base = base.join(first[["mat6_time_of_day_band", "mat10_funding_rate", "qty"]], on="bundle_id")
    base["funding"] = np.where(base.mat10_funding_rate > 0, "正", np.where(base.mat10_funding_rate < 0, "負", "0・無し"))
    w("## D2 場面(全部順張り・g 60・d 1、1 連鎖あたり %。場面は連鎖の最初のプリントの時点で分かる値)")
    w("")
    w("| 場面 | 値 | 連鎖 | 全期間 [区間] | 前半 [区間] | 後半 [区間] |")
    w("|---|---|---|---|---|---|")
    for col, nm in (("side", "清算の側"), ("mat6_time_of_day_band", "時間帯(UTC)"), ("funding", "資金調達率の符号")):
        for val, q in base.groupby(col):
            cells = [f2(ratio(pd_, q[q.day.isin(pd_)], "pnl_pct"), 5) for pd_ in parts.values()]
            w(f"| {nm} | {val} | {len(q):,} | " + " | ".join(cells) + " |")
    w("")

    # ---------------- D3 集まり
    w("## D3 稼ぎと損の集まり(g 60・d 1)")
    w("")
    w("| 判断の出所 | 型 | 和 | 上位 5% の日の和 | 下位 5% の日の和 | 1% | 5% | 25% | 50% | 75% | 95% | 99%(1 連鎖の分位) |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for key in [("全部順張り", "-"), ("規則_材料1", "A"), ("規則_材料1", "B"), ("規則_3択", "A"), ("規則_3択", "B"), ("完全な判断", "A"), ("完全な判断", "B")]:
        q = pc[(pc.policy == key[0]) & (pc.type == key[1]) & (pc.gap_s == 60) & (pc.delay_s == 1)].dropna(subset=["pnl_pct"])
        x = np.array(sorted(daily[(key[0], key[1], 60, 1)].values()))
        k = max(1, int(round(len(x) * 0.05)))
        qs = np.percentile(q.pnl_pct, [1, 5, 25, 50, 75, 95, 99])
        w(f"| {key[0]} | {key[1]} | {x.sum():+,.3f} | {x[-k:].sum():+,.3f} | {x[:k].sum():+,.3f} | " + " | ".join(f"{v:+.4f}" for v in qs) + " |")
    w("")
    w("連鎖のプリントの数の帯【結果で決まる群】(全部順張り・g 60・d 1、1 連鎖あたり %):")
    w("")
    w("| プリントの数 | 連鎖 | 和 | 全期間 [区間] | 前半 | 後半 |")
    w("|---|---|---|---|---|---|")
    for lo, hi in ((1, 1), (2, 2), (3, 5), (6, 20), (21, 10**9)):
        q = base[(base.n_prints >= lo) & (base.n_prints <= hi)]
        cells = [f2(ratio(pd_, q[q.day.isin(pd_)], "pnl_pct"), 5) for pd_ in parts.values()]
        w(f"| {lo}〜{hi if hi < 10**9 else ''} | {len(q):,} | {q.pnl_pct.sum():+,.3f} | " + " | ".join(cells) + " |")
    w("")

    # ---------------- D4 レグ
    lg = pd.read_csv(RUN + "policy_legs.csv.gz")
    # 1 レグの損益は bp(量 1 の値動き率)。この表では和を出すので % にそろえる(L-920)
    lg["pnl_pct"] = lg["pnl_bp"] / 100
    w("## D4 レグ(建玉 1 つ)の出の理由 × 向き(g 60・d 1、1 レグあたり %)【結果で決まる群】")
    w("")
    w("| 判断の出所 | 型 | 向き | 出の理由 | レグ | 和 | 全期間 [区間] | 前半 | 後半 | 保有秒の中央値 |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for pol in ("規則_材料1", "規則_3択", "完全な判断"):
        for typ in ("A", "B"):
            q0 = lg[(lg.policy == pol) & (lg.type == typ) & (lg.gap_s == 60) & (lg.delay_s == 1)].dropna(subset=["pnl_pct"])
            for (ld, er), q in q0.groupby(["leg_dir", "exit_reason"]):
                cells = [f2(ratio(pd_, q[q.day.isin(pd_)], "pnl_pct"), 5) for pd_ in parts.values()]
                w(f"| {pol} | {typ} | {ld} | {er} | {len(q):,} | {q.pnl_pct.sum():+,.3f} | " + " | ".join(cells) + f" | {q.hold_s.median():.0f} |")
    w("")

    # ---------------- D6 連鎖の間隔
    w("## D6 前の連鎖の終わりから次の連鎖の始まりまで(同じ g、側を問わない。全部順張り・g 60・d 1、1 連鎖あたり %)【建ての前に決まる群】")
    w("")
    b60 = bb[bb.gap_s == 60].sort_values("start_ms").copy()
    prev_end = np.concatenate([[np.nan], np.maximum.accumulate(b60.end_ms.values)[:-1]])
    b60["gap_prev_s"] = (b60.start_ms.values - prev_end) / 1000
    bx = base.join(b60.set_index("bundle_id")[["gap_prev_s"]], on="bundle_id")
    edges = np.nanpercentile(bx.gap_prev_s, [25, 50, 75])
    w(f"四分位の境(秒): {edges[0]:.0f}・{edges[1]:.0f}・{edges[2]:.0f}(負 = 前の連鎖の終わりの前に始まった = 重なり)")
    w("")
    w("| 間隔の帯(秒) | 連鎖 | 全期間 [区間] | 前半 | 後半 |")
    w("|---|---|---|---|---|")
    bnds = [(-np.inf, edges[0]), (edges[0], edges[1]), (edges[1], edges[2]), (edges[2], np.inf)]
    for lo, hi in bnds:
        q = bx[(bx.gap_prev_s > lo) & (bx.gap_prev_s <= hi)]
        cells = [f2(ratio(pd_, q[q.day.isin(pd_)], "pnl_pct"), 5) for pd_ in parts.values()]
        w(f"| {lo:.0f}〜{hi:.0f} | {len(q):,} | " + " | ".join(cells) + " |")
    w("")

    # ---------------- D7 判断の出所の比べ(日ごとの差)
    w("## D7 比べ(同じ日どうしの日ごとの差、%/日)")
    w("")
    w("| 比べ | g | d | 全期間 [区間] | 前半 [区間] | 後半 [区間] |")
    w("|---|---|---|---|---|---|")
    comps = []
    for g in (30, 60, 180):
        for d in (1, 3):
            for typ in ("A", "B"):
                comps.append((f"完全な判断 {typ} − 全部順張り", ("完全な判断", typ, g, d), ("全部順張り", "-", g, d), g, d))
                comps.append((f"規則_材料1 {typ} − 全部順張り", ("規則_材料1", typ, g, d), ("全部順張り", "-", g, d), g, d))
                comps.append((f"規則_3択 {typ} − 全部順張り", ("規則_3択", typ, g, d), ("全部順張り", "-", g, d), g, d))
                comps.append((f"完全な判断 {typ} − 規則_材料1 {typ}", ("完全な判断", typ, g, d), ("規則_材料1", typ, g, d), g, d))
            comps.append(("規則_材料1 B − A", ("規則_材料1", "B", g, d), ("規則_材料1", "A", g, d), g, d))
    for g in (30, 60, 180):
        comps.append(("全部順張り d 3 − d 1", ("全部順張り", "-", g, 3), ("全部順張り", "-", g, 1), g, "3−1"))
    for nm, ka, kb, g, d in comps:
        diff = [daily[ka][x] - daily[kb][x] for x in days]
        cells = [f2(dt.mean_ci(diff), 4), f2(dt.mean_ci(diff[:half]), 4), f2(dt.mean_ci(diff[half:]), 4)]
        if ka[0] == "規則_3択":
            cells[0] = cells[1] = "—(後半だけ)"
        w(f"| {nm} | {g} | {d} | " + " | ".join(cells) + " |")
    w("")
    # 3 択の入らなかった連鎖
    w("### 規則_3択で入らなかった連鎖(後半、g 60・d 1、型 A)の、全部順張りの損益")
    w("")
    t3 = pc[(pc.policy == "規則_3択") & (pc.type == "A") & (pc.gap_s == 60) & (pc.delay_s == 1)][["bundle_id", "entered"]]
    bf = pc[(pc.policy == "全部順張り") & (pc.gap_s == 60) & (pc.delay_s == 1)][["bundle_id", "day", "pnl_pct"]]
    j = t3.merge(bf, on="bundle_id").dropna(subset=["pnl_pct"])
    w("| 3 択 | 連鎖 | 全部順張りの 1 連鎖あたり [区間] | 中央値 | 25% | 75% |")
    w("|---|---|---|---|---|---|")
    for e, q in j.groupby("entered"):
        w(f"| {'入った' if e else '入らなかった'} | {len(q):,} | {f2(ratio(parts['後半'], q, 'pnl_pct'), 5)} | {q.pnl_pct.median():+.4f} | {q.pnl_pct.quantile(.25):+.4f} | {q.pnl_pct.quantile(.75):+.4f} |")
    w("")
    open(os.path.join(HERE, "C9_TABLES.md"), "w").write("\n".join(OUT) + "\n")
    print("done")


if __name__ == "__main__":
    main()

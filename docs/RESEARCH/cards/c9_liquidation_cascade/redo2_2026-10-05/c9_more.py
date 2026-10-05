"""カード 9 の足し(アドバイザーの最後の見直し、2026-10-05)。保存済みの出力と生の約定の読みだけ。状態機械は回さない。台本の試験は無い。
(1) 規則_3択の判断が、測る期間(後半)でどれだけ「続く」を見分けているか: `three_way_probs.csv.gz` の判断(止まる/わからない/続く)ごとの
    `cont_60`(同じ側の次のプリントが 60 秒以内に来た)の割合。区間は日の塊(group_ratio_ci)。場面(1件目 / 連鎖の中)別。
(2) 静かな時点の約定の側: 束(g 30・60・180)の終わり(最後のプリント + g)+ 1 秒の時点で、(A) その時点以後の最初の
    買い手が成行・売り手が成行の約定の値段の差、(B) その時点以前の最後の買い手が成行・売り手が成行の約定の値段の差(板の幅の代わり)。
    逆張りの向きに付けた「逆張りが叩く側 − 順張りが叩く側」を bp で(逆張りの損になる向きを正)。区間は日の塊。
    PYTHONPATH=src python3 docs/RESEARCH/cards/c9_liquidation_cascade/redo2_2026-10-05/c9_more.py
出力: このフォルダの C9_MORE.md
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


def f(q, nd=3):
    if q["per_trade"] is None:
        return "—"
    return f"{q['per_trade']:+.{nd}f} [{q['lo']:+.{nd}f}, {q['hi']:+.{nd}f}]"


def ratio(days, df, col):
    g = df.groupby("day")[col]
    return dt.group_ratio_ci(days, g.sum().to_dict(), g.count().to_dict())


def main():
    out = ["# カード 9 の足し: 3 択の判断の見分け(後半)・静かな時点の約定の側", ""]
    tw = pd.read_csv(RUN + "three_way_probs.csv.gz")
    out.append(f"`three_way_probs.csv.gz` の列: {', '.join(tw.columns)}")
    out.append("")
    pc_days = sorted(pd.read_csv(RUN + "policy_cascades.csv.gz", usecols=["day"]).day.unique())
    half = len(pc_days) // 2
    out.append("## (1) 規則_3択の判断ごとの「続く」(cont_60)の割合 [区間]")
    out.append("")
    out.append("| 期間 | 場面 | 判断 | プリント | 続く割合 [区間] |")
    out.append("|---|---|---|---|---|")
    pcol = "期間"
    scol = [c for c in tw.columns if c in ("場面", "scene")][0]
    jcol = [c for c in tw.columns if c in ("判断", "judge", "judgment")][0]
    for per, pdays in (("作る", pc_days[:half]), ("測る", pc_days[half:])):
        q0 = tw[tw[pcol] == per] if pcol else tw
        for sc, q1 in q0.groupby(scol):
            q1 = q1.dropna(subset=["cont_60"])
            base = ratio(pdays, q1, "cont_60")
            out.append(f"| {per} | {sc} | (全部 = 基準率) | {len(q1):,} | {f(base)} |")
            for jd, q in q1.groupby(jcol):
                out.append(f"| {per} | {sc} | {jd} | {len(q):,} | {f(ratio(pdays, q, 'cont_60'))} |")
    out.append("")

    # (2) 静かな時点の約定の側
    bb = pd.read_csv(RUN + "anchors_bundles.csv.gz")
    bb["day"] = pd.to_datetime(bb.end_ms + 1000, unit="ms").dt.strftime("%Y-%m-%d")
    bb["sign"] = np.where(bb.side == "BUY", 1, -1)
    recs = []
    for day, q in bb.groupby("day"):
        frames = []
        for dd in (day, str((pd.Timestamp(day) + pd.Timedelta(days=1)).date()), str((pd.Timestamp(day) - pd.Timedelta(days=1)).date())):
            ff = AGG + f"BTCUSD_PERP-aggTrades-{dd}.zip"
            if os.path.exists(ff):
                z = zipfile.ZipFile(ff)
                frames.append(pd.read_csv(io.TextIOWrapper(z.open(z.namelist()[0])), usecols=["price", "transact_time", "is_buyer_maker"]))
        if not frames:
            continue
        tr = pd.concat(frames, ignore_index=True).sort_values("transact_time", kind="stable")
        t = tr.transact_time.values
        m = tr.is_buyer_maker.astype(str).str.lower().values == "true"
        p = tr.price.values
        tb, pb, tsl, psl = t[~m], p[~m], t[m], p[m]
        x = (q.end_ms + 1000).values
        ia, ja = np.searchsorted(tb, x, "left"), np.searchsorted(tsl, x, "left")
        ib, jb = np.searchsorted(tb, x, "right") - 1, np.searchsorted(tsl, x, "right") - 1
        okA = (ia < len(tb)) & (ja < len(tsl))
        okB = (ib >= 0) & (jb >= 0)
        buy_after = np.where(okA, pb[np.clip(ia, 0, len(pb) - 1)], np.nan)
        sell_after = np.where(okA, psl[np.clip(ja, 0, len(psl) - 1)], np.nan)
        lag_b = np.where(okA, tb[np.clip(ia, 0, len(tb) - 1)] - x, np.nan)
        lag_s = np.where(okA, tsl[np.clip(ja, 0, len(tsl) - 1)] - x, np.nan)
        buy_before = np.where(okB, pb[np.clip(ib, 0, len(pb) - 1)], np.nan)
        sell_before = np.where(okB, psl[np.clip(jb, 0, len(psl) - 1)], np.nan)
        age_b = np.where(okB, x - tb[np.clip(ib, 0, len(tb) - 1)], np.nan)
        age_s = np.where(okB, x - tsl[np.clip(jb, 0, len(tsl) - 1)], np.nan)
        recs.append(pd.DataFrame({"day": day, "gap_s": q.gap_s.values, "sign": q.sign.values,
                                  "buy_after": buy_after, "sell_after": sell_after, "lag_b": lag_b, "lag_s": lag_s,
                                  "buy_before": buy_before, "sell_before": sell_before, "age_b": age_b, "age_s": age_s}))
    r = pd.concat(recs, ignore_index=True)
    # 逆張りが叩く側: sign −1(SELL の清算)→ 逆張りは買う → 買い手が成行。sign +1 → 売り手が成行
    for k in ("after", "before"):
        fade = np.where(r.sign < 0, r[f"buy_{k}"], r[f"sell_{k}"])
        foll = np.where(r.sign < 0, r[f"sell_{k}"], r[f"buy_{k}"])
        # 逆張りの損になる向きを正: 逆張りが買う(sign −1)なら fade − foll が高いほど損
        r[f"cost_{k}"] = -r.sign * (fade - foll) / ((fade + foll) / 2) * 1e4
    days = sorted(r.day.unique())
    h2 = days[len(days) // 2] if days else None
    out.append("## (2) 束の終わり + 1 秒の時点の約定の側の差(逆張りが叩く側 − 順張りが叩く側、逆張りの損の向きに正、bp/束)")
    out.append("")
    out.append("(A) = その時点以後の最初の約定どうし(時刻は違う)、(B) = その時点以前の最後の約定どうし(板の幅の代わり。時刻は違う)。")
    out.append("")
    out.append("| g 秒 | 束 | (A) 平均 [区間] | (A) 中央値 | (A) 遅れの中央値 ms(逆張り側 / 順張り側) | (B) 平均 [区間] | (B) 中央値 | (B) 古さの中央値 ms(買い手成行 / 売り手成行) |")
    out.append("|---|---|---|---|---|---|---|---|")
    for g, q in r.groupby("gap_s"):
        qa, qb = q.dropna(subset=["cost_after"]), q.dropna(subset=["cost_before"])
        lf = np.where(qa.sign < 0, qa.lag_b, qa.lag_s)
        lo = np.where(qa.sign < 0, qa.lag_s, qa.lag_b)
        out.append(f"| {g} | {len(q):,} | {f(ratio(days, qa, 'cost_after'))} | {qa.cost_after.median():+.3f} | {np.median(lf):.0f} / {np.median(lo):.0f} | "
                   f"{f(ratio(days, qb, 'cost_before'))} | {qb.cost_before.median():+.3f} | {qb.age_b.median():.0f} / {qb.age_s.median():.0f} |")
    out.append("")
    out.append(f"日 = 束の終わり + 1 秒の UTC の日({len(days)} 日)。前半・後半の境 {h2}(この表は全期間だけ)。")
    open(os.path.join(HERE, "C9_MORE.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""# 3 カード 3(円の上乗せの戻り)の前提の直接の測り(D1B_FRAMINGS.md の # 3 の行)。

定義はリードの決め(2026-10-06、報告の問い 3・4・6 への答え)。引数の既定はこの形:
  --edge outside   = 窓の端 = 上乗せが窓 (t − W, t) の全部の値より大きい / 小さい(カードの持ち高 e = −1 / +1 と同じ)
  --event onset    = 1 件 = 端にいる分の続きの最初の分(直前の上乗せの分が同じ端でない)。これが主。
                     every(端にいる分の全部)は件数の数え上げ(--counts)でだけ並べる(本走らせは onset だけを受ける)
  --cause last1m   = 開いた原因の脚 = 直前の 1 分(直前の上乗せの分がちょうど 1 分前)で、上乗せを端の向きへ一番動かした脚
                     (直前の分が無い・1 分前でない・最大が並ぶときは「不明」)

行の言葉と、それを担う関数:
  「上乗せ」               premiums: カード 3 の式 p_t = ln(bitFlyer 終値) − ln(Binance 終値 × USDJPY 終値)。Binance は t − 60 秒の行
                           (t で終わる分)そのもの、USDJPY は行の時刻 ≤ t − 60 秒の最後の行(as-of)。どちらか無ければその分は無い
                           (カードと同じ。試験でカードの premium と一致を確かめる)
  「窓 3(1 時間・1 日・1 週)」 WINDOWS(カードの WINDOWS を import)
  「端に寄った時刻」       edge_flags・edge_events(上の決め)。カードの慣らし(最初の上乗せから W たつまでは持たない)も同じに当てる
  「脚 3」                 legs: 上乗せの戻り(端の向き s に対して −s × Δp)を 3 つに分ける。
                             bitFlyer の脚 = −s × Δln bitFlyer、Binance の脚 = +s × Δln Binance、USDJPY の脚 = +s × Δln USDJPY
                           (和 = −s × Δp = 戻り。bp)。bitFlyer・Binance は t・t + h ちょうどの値(無ければ NaN にして、
                           as-of の値が古かった件数を表に出す。# 2 とそろえる)、USDJPY はカードと同じ as-of
  「時間 4」               HORIZONS_MIN = 1・5・15・60 分(リードの決め 2026-10-06 の 4)
  「開いた原因の脚 3」     cause(上の決め)
  「1 合図(端に寄った時刻)。年ごと・前半後半」 g1common.table
  対照「24 時間前と後」     同じ s・同じ原因の印を、時刻 t ± 1,440 分の 3 つの脚の動きに当てる。前と後を別に出す

期間の既定は 2017-08-17T15:00Z 〜 2023-12-17T15:00Z(批評家 1 回目 問 0 とリードの応答: 範囲を縮めない、A-10)。2023 年の USDJPY は
common.usdjpy_ref_dataset(extend=True)で読む(担当 A の変更のコミットの後に打つ)。

使い方:
  件数だけ: PYTHONPATH=src python3 scripts/d1b/g1/c3_premium.py --counts                (onset)
            PYTHONPATH=src python3 scripts/d1b/g1/c3_premium.py --counts --event every  (every を並べる)
  本走らせ: PYTHONPATH=src python3 scripts/d1b/g1/c3_premium.py
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import g1common as G  # noqa: E402

OUT = os.path.join(G.ROOT, "docs", "RESEARCH", "d1b", "3_card3")
HORIZONS_MIN = (1, 5, 15, 60)
LO_DEFAULT = "2017-08-17T15:00:00Z"
HI_DEFAULT = G.HI_MAX_ISO
LEGS = ("bitFlyer", "Binance", "USDJPY")


def premiums(bf_end: np.ndarray, bf_close: np.ndarray, b_t: np.ndarray, b_close: np.ndarray, fx_t: np.ndarray,
             fx_close: np.ndarray) -> dict:
    """空でない bitFlyer の足の終わり t ごとの上乗せ。上乗せが無い分は落とす。脚の対数の値も返す。"""
    ib = G.exact_idx(b_t, bf_end - G.MIN_NS)
    ifx = G.asof_idx(fx_t, bf_end - G.MIN_NS)
    ok = (ib >= 0) & (ifx >= 0)
    lbf = np.log(bf_close[ok])
    lb = np.log(b_close[ib[ok]])
    lfx = np.log(fx_close[ifx[ok]])
    return {"t": bf_end[ok], "p": lbf - lb - lfx, "lbf": lbf, "lb": lb, "lfx": lfx}


def edge_flags(t: np.ndarray, p: np.ndarray, window_ns: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(上の端, 下の端, 慣らしの後)。上の端 = p_t が (t − W, t) の全部の上乗せより大きい(窓に値が 1 つ以上)。
    慣らし = 最初の上乗せから W たった後(カードの t − first >= W)。"""
    import pandas as pd
    s = pd.Series(p, index=pd.to_datetime(t, unit="ns"))
    r = s.rolling(pd.Timedelta(window_ns, unit="ns"), closed="neither")
    mx = r.max().to_numpy()
    mn = r.min().to_numpy()
    cnt = r.count().to_numpy()
    warm = (t - t[0]) >= window_ns if len(t) else np.zeros(0, bool)
    has = cnt > 0
    return has & (p > mx) & warm, has & (p < mn) & warm, warm


def edge_events(t: np.ndarray, hi_f: np.ndarray, lo_f: np.ndarray, event: str) -> tuple[np.ndarray, np.ndarray]:
    """(合図の位置, 端の向き s: 上 +1 / 下 −1)。onset = 直前の上乗せの分が同じ端でない分だけ。"""
    s = np.where(hi_f, 1, np.where(lo_f, -1, 0))
    if event == "every":
        idx = np.flatnonzero(s != 0)
    else:
        prev = np.concatenate([[0], s[:-1]])
        idx = np.flatnonzero((s != 0) & (s != prev))
    return idx, s[idx]


def cause(pr: dict, idx: np.ndarray, s: np.ndarray) -> np.ndarray:
    """last1m: 直前の上乗せの分がちょうど 1 分前のとき、3 つの脚のうち上乗せを端の向き s へ一番動かした脚(0 bitFlyer・
    1 Binance・2 USDJPY)。直前の分が無い・1 分前でない・最大が並ぶときは −1(不明)。"""
    out = np.full(len(idx), -1)
    j = idx - 1
    ok = (j >= 0) & (pr["t"][idx] - pr["t"][np.maximum(j, 0)] == G.MIN_NS)
    i, j, ss = idx[ok], j[ok], s[ok]
    c = np.stack([ss * (pr["lbf"][i] - pr["lbf"][j]), -ss * (pr["lb"][i] - pr["lb"][j]),
                  -ss * (pr["lfx"][i] - pr["lfx"][j])], axis=1)
    top = c.max(axis=1, keepdims=True)
    uniq = (c == top).sum(axis=1) == 1
    out[np.flatnonzero(ok)[uniq]] = c[uniq].argmax(axis=1)
    return out


def legs(T: np.ndarray, s: np.ndarray, h_min: int, hi: int, bf: dict, b_t, b_close, fx_t, fx_close) -> dict:
    """時刻 T から T + h までの 3 つの脚の、上乗せの戻りへの寄与(bp)と合計。
    bitFlyer = 終わりがちょうど T・T + h の空でない足の終値、Binance = 行の時刻がちょうど T − 60 秒・T + h − 60 秒の行(上乗せと同じ)。
    どれかが無ければ NaN(前の値で埋めない。# 2 とそろえる、批評家 1 回目 問 2 への直し)。USDJPY はカードと同じ as-of
    (行の時刻 ≤ T − 60 秒の最後の行。為替の閉じている間は最後の値)。"_stale" = bitFlyer か Binance のちょうどの値が無く、
    それより前の値はあった件、"_late" = T + h > hi の件、"_fx_old" = USDJPY の as-of の行の時刻が目標(T − 60 秒・T + h − 60 秒)
    より 1 分を越えて古かった件(USDJPY は NaN にしない。数だけ出す。批評家 2 回目の情報への対応)。"""
    h = h_min * G.MIN_NS

    def lv(T_):
        ia, ib = G.exact_idx(bf["end"], T_), G.exact_idx(b_t, T_ - G.MIN_NS)
        stale = ((ia < 0) & (G.asof_idx(bf["end"], T_) >= 0)) | ((ib < 0) & (G.asof_idx(b_t, T_ - G.MIN_NS) >= 0))
        jf = G.asof_idx(fx_t, T_ - G.MIN_NS)
        fx_old = (jf >= 0) & ((T_ - G.MIN_NS) - fx_t[np.maximum(jf, 0)] > G.MIN_NS)
        return (np.log(G.take(bf["close"], ia)), np.log(G.take(b_close, ib)),
                np.log(G.take(fx_close, jf)), stale, fx_old)
    a0, b0, f0, s0, o0 = lv(T)
    a1, b1, f1, s1, o1 = lv(T + h)
    s = s.astype(float)
    out = {"bitFlyer": -s * (a1 - a0) * G.BP, "Binance": s * (b1 - b0) * G.BP, "USDJPY": s * (f1 - f0) * G.BP}
    out["合計(上乗せの戻り)"] = out["bitFlyer"] + out["Binance"] + out["USDJPY"]
    late = T + h > hi
    bad = late | ~np.isfinite(out["合計(上乗せの戻り)"])
    out = {k: np.where(bad, np.nan, v) for k, v in out.items()}
    out["_stale"] = ~late & (s0 | s1)
    out["_late"] = late
    out["_fx_old"] = ~late & (o0 | o1)
    return out


def load_inputs(rd_lo: int, hi: int) -> dict:
    from common import FX_DIR, binance_ref_dataset, usdjpy_ref_dataset
    from bot.research.cards import cardmd
    from bot.research.cards.library.c3_yen_premium_revert import FX, OVERSEAS
    with open(os.path.join(G.ROOT, "docs/RESEARCH/cards/c3_yen_premium_revert/CARD.md"), encoding="utf-8") as fh:
        st, problems = cardmd.settings(cardmd.parse(fh.read()))
    if problems:
        raise SystemExit(f"CARD.md の測定の設定が読めない: {problems}")
    decl = dict(st.declarations)
    bf = G.bars_np(FX_DIR, "FX_BTC_JPY", rd_lo, hi)
    b_t, b_c, b_m = G.ref_np(binance_ref_dataset(OVERSEAS, "close", rd_lo, hi), OVERSEAS, decl)
    fx_t, fx_c, fx_m = G.ref_np(usdjpy_ref_dataset(FX, rd_lo - 7 * G.DAY_NS, hi, extend=True), FX, decl)
    return {"bf": bf, "b_t": b_t, "b_c": b_c, "fx_t": fx_t, "fx_c": fx_c,
            "manifest": {"binance": b_m, "usdjpy": fx_m, "bitflyer_files": bf["files"]}}


def main() -> int:
    from bot.research.cards.library.c3_yen_premium_revert import WINDOWS
    ap = argparse.ArgumentParser()
    ap.add_argument("--edge", default="outside", choices=["outside"])
    ap.add_argument("--event", default="onset", choices=["onset", "every"], help="every は --counts でだけ")
    ap.add_argument("--cause", default="last1m", choices=["last1m"])
    ap.add_argument("--start", default=LO_DEFAULT)
    ap.add_argument("--end", default=HI_DEFAULT)
    ap.add_argument("--counts", action="store_true")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    if a.event != "onset" and not a.counts:
        raise SystemExit("--event every は件数の数え上げ(--counts)でだけ使う(リードの決め: 1 件 = onset が主)")
    lo, hi = G.iso_ns(a.start), G.iso_ns(a.end)
    G.check_hi(hi)
    t0 = time.time()
    rd_lo = lo - max(WINDOWS.values()) - G.DAY_NS  # 窓の値と 24 時間前の対照のために前から読む
    X = load_inputs(rd_lo, hi)
    pr = premiums(X["bf"]["end"], X["bf"]["close"], X["b_t"], X["b_c"], X["fx_t"], X["fx_c"])
    t_read = time.time() - t0
    all_days = G.all_days_between(lo, hi)
    tag = f"{a.edge}_{a.event}_{a.cause}"
    head = [f"- 台本: `scripts/d1b/g1/c3_premium.py --edge {a.edge} --event {a.event} --cause {a.cause}`"
            "(数は台本が出した。手で書いていない)",
            f"- 端 = 窓の全部の値の外、1 件 = {'端にいる分の最初の 1 分(onset)' if a.event == 'onset' else '端にいる分の全部(every。件数だけ)'}、"
            "原因 = 直前の 1 分で上乗せを端の向きへ一番動かした脚(リードの決め 2026-10-06)",
            f"- 期間 {G.ns_iso(lo)} 〜 {G.ns_iso(hi)}(日本時間の暦日 {len(all_days)} 日)。"
            f"読み込みは {G.ns_iso(rd_lo)} から(窓の値・対照のため)",
            f"- 読み込みと上乗せ {t_read:.0f} 秒", ""]
    cnames = {0: "bitFlyer", 1: "Binance", 2: "USDJPY", -1: "不明"}
    res = {"tag": tag, "period": [G.ns_iso(lo), G.ns_iso(hi)], "inputs": X["manifest"], "窓": {}}
    L = [f"# # 3 カード 3 — {'件数の数え上げ' if a.counts else '上乗せの戻りの脚'}({tag})", ""] + head
    for wname, W in WINDOWS.items():
        hf, lf, _warm = edge_flags(pr["t"], pr["p"], W)
        idx, s = edge_events(pr["t"], hf, lf, a.event)
        T = pr["t"][idx]
        keep = (T > lo) & (T <= hi)
        idx, s, T = idx[keep], s[keep], T[keep]
        cz = cause(pr, idx, s)
        days = G.jst_day(T - 1)
        if a.counts:
            cj = {"全部": G.count_table(days, all_days)}
            L += G.md_counts(f"窓 {wname} — 全部の合図", cj["全部"], "合図の数")
            for side, nm in ((1, "上の端"), (-1, "下の端")):
                cj[nm] = G.count_table(days[s == side], all_days)
            for c in (0, 1, 2, -1):
                cj[f"原因 {cnames[c]}"] = G.count_table(days[cz == c], all_days)
                L += G.md_counts(f"窓 {wname} — 原因の脚 {cnames[c]}", cj[f"原因 {cnames[c]}"], "合図の数")
            L += [f"- 窓 {wname}: 上の端 {cj['上の端']['全期間']['n']}・下の端 {cj['下の端']['全期間']['n']}", ""]
            res["窓"][wname] = cj
            continue
        tabs, marks = {}, {}
        for lab, sh in (("実", 0), ("24 時間前", -G.DAY_NS), ("24 時間後", G.DAY_NS)):
            for hm in HORIZONS_MIN:
                lg = legs(T + sh, s, hm, hi, X["bf"], X["b_t"], X["b_c"], X["fx_t"], X["fx_c"])
                marks[f"{lab}|{hm}分"] = {"NaN の件数": int(np.isnan(lg["合計(上乗せの戻り)"]).sum()),
                                         "うち as-of が古かった件数": int(lg.pop("_stale").sum()),
                                         "うち終わりを越えた件数": int(lg.pop("_late").sum()),
                                         "USDJPY の値が 1 分を越えて古かった件数": int(lg.pop("_fx_old").sum())}
                for c in (None, 0, 1, 2, -1):
                    m = np.ones(len(T), bool) if c is None else cz == c
                    for leg, v in lg.items():
                        key = f"{lab}|{hm}分|原因 {'全部' if c is None else cnames[c]}|{leg}"
                        tabs[key] = G.table(v[m], days[m], all_days, per="event")
        res["窓"][wname] = tabs
        res["窓"][wname + "|NaN の件数"] = marks
        for lab in ("実", "24 時間前", "24 時間後"):
            L += [f"## 窓 {wname} — {lab}", ""] + G.MD_STAT_HEAD
            for c in ("全部", "bitFlyer", "Binance", "USDJPY", "不明"):
                for hm in HORIZONS_MIN:
                    for leg in ("bitFlyer", "Binance", "USDJPY", "合計(上乗せの戻り)"):
                        L += [r for r in G.md_stat_rows(f"原因 {c} / {hm}分 / {leg}", tabs[f"{lab}|{hm}分|原因 {c}|{leg}"])
                              if "(記述)" not in r]
            L += ["", "NaN の件数(原因 全部)と USDJPY の古さ(as-of のまま。NaN にしない):", "",
                  "| 時間 | NaN の件数 | うち as-of が古かった件数 | うち終わりを越えた件数 | USDJPY の値が 1 分を越えて古かった件数 |",
                  "|---|---|---|---|---|"]
            for hm in HORIZONS_MIN:
                mk = marks[f"{lab}|{hm}分"]
                L.append(f"| {hm}分 | {mk['NaN の件数']} | {mk['うち as-of が古かった件数']} | {mk['うち終わりを越えた件数']} | "
                         f"{mk['USDJPY の値が 1 分を越えて古かった件数']} |")
            L.append("")
    res["所要_秒"] = round(time.time() - t0, 1)
    os.makedirs(a.out, exist_ok=True)
    if a.counts:
        with open(os.path.join(a.out, f"COUNTS_{tag}.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(L))
        G.write_json(res, os.path.join(a.out, f"counts_{tag}.json"))
        print("\n".join(L))
        return 0
    L += ["年ごとの表(記述)は result_<候補>.json の各表の「年ごと(記述)」。", ""]
    G.write_json(res, os.path.join(a.out, f"result_{tag}.json"))
    with open(os.path.join(a.out, f"RESULT_{tag}.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    print(f"書いた: {a.out} 所要 {res['所要_秒']} 秒")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""# 1 カード 1(今の paper bot)の前提の直接の測り: 持つ先を替える(D1B_FRAMINGS.md の # 1 の行)。

行の言葉と、それを担う関数:
  問い「この形の 2018 年までの稼ぎは、(a) 取引所の間の遅れ と (b) BTC の値動きの続き のどちらから来ていたか」
  「同じ合図・同じ降り方で」        run_card_chunks: カード 1 の物(XborderMom、import)を run_card で年ごとに走らせ、
                                    持ち高 e_t をそのまま使う(カードの本体はそのまま。行の注「持つ先を替えた走らせが 1 本要る」)
  「持つ先 2 通り(Binance 自身 / bitFlyer)」 pnl_two_venues: bitFlyer = 測定器の pnl(e_t × (始値_{t+2} / 始値_{t+1} − 1))。
                                    Binance = 同じ e_t を、同じ約定と出の時刻(bitFlyer の t+1・t+2 の足の始まり)の Binance 現物
                                    BTCUSDT の 1 分足の始値で持つ。行が無ければ NaN(数える)
  「その差(bitFlyer − Binance)」     同じ決定どうしの差。両方の値がある決定だけ(3 つの量を同じ決定の組で出す)
  「合図の後の両取引所の累積の差が 0 に戻るまでの分」 return_minutes: 下の定義
  「損益は 1 日(日ごと)」          日本時間の日ごとの P の和。1 日あたりの平均と日の塊の区間(g1common.table, per="day")
  「戻るまでの分は 1 合図」          1 合図 = 持ち高が ±1 に変わった決定(0 → ±1、∓1 → ±1)。1 件あたりの平均と分位
  「年ごと・前半後半」              g1common.table
  データ「Binance 現物と bitFlyer FX の 1 分足、2017-08-17〜2023-12-17」  --start / --end の既定
  対照「24 時間前と後の同じ時刻」    control_pnl / return_minutes(shift): 同じ e_t・同じ符号を、時刻を ±1,440 分ずらした値動きに当てる。
                                    前と後の両方を別の列で出す(委任文の共通の決まり)

累積の差が 0 に戻るまでの分(return_minutes):
  X(τ) = ln(Binance 終値 × USDJPY 終値) − ln(bitFlyer 終値)(τ は分の終わり。Binance・USDJPY は行の時刻 ≤ τ − 60 秒の最後の
  行 = τ で終わる分まで、bitFlyer は終わりが τ 以下の最後の空でない足。どれも as-of)。円にそろえたので X(τ) = −p(τ)
  (p = カード 3 の円の上乗せ ln bitFlyer − ln(Binance × USDJPY))で、USDJPY の動きは入らない。累積の差 = 上乗せの変化そのもの
  (批評家 1 回目 問 0 への直し。前の版は USDJPY でそろえておらず、USDJPY の動きが入っていた)。合図の決定時刻 t、合図の向き s(+1 買い / −1 売り)に、
  基準 = カードの「Binance の k 本前」の分の終わり t − 30 分 として
      D(τ) = s × (X(τ) − X(t − 30 分))
  (合図の 30 分の間に Binance だけが動いた分 = bitFlyer がまだ付いてきていない分。bitFlyer が遅れていれば D(t) > 0)。
  戻るまでの分 = D(τ) ≤ 0 になる最初の τ ≥ t(1 分刻み)の (τ − t) / 60 秒。データの終わりまで戻らなければ NaN にし、
  その件数を「戻らない」として表に出す(リードの決め 2026-10-06 の 1)。基準・起点が無い件も別に数えて出す。
  USDJPY は common.usdjpy_ref_dataset(extend=True)(2023 年は担当 A の変更のコミットの後に使える)、宣言はカード 3 の CARD.md。

使い方:
  件数だけ(値動き・損益を計算しない。カードを走らせて合図を数え、走らせの記録を --cache に残す):
    PYTHONPATH=src python3 scripts/d1b/g1/c1_venue.py --counts --cache data/d1b_g1/c1_run.npz
  本走らせ(--cache があればカードを走らせ直さない):
    PYTHONPATH=src python3 scripts/d1b/g1/c1_venue.py --cache data/d1b_g1/c1_run.npz
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import g1common as G  # noqa: E402

OUT = os.path.join(G.ROOT, "docs", "RESEARCH", "d1b", "1_card1")
LO_DEFAULT = "2017-08-17T15:00:00Z"
K_MIN = 30  # カード 1 の k(c1_xborder_mom.K)。基準の時刻を決めるのに使う(下で K と同じことを確かめる)


# ---------------------------------------------------------------------------------------------- カードを走らせる
def run_card_chunks(lo: int, hi: int, log=print) -> dict:
    """カード 1 を年ごとに run_card に通す(各区切りの 1 日前から足と参照を渡して慣らし、区切りの中の足だけを残す。
    scripts/w4_measure/run_v2.py の run_c1_chunks と同じ区切り方)。空でない足だけの配列を返す。"""
    from common import FX_DIR, binance_ref_dataset, load_bars
    from bot.bt.data.reference import load_reference
    from bot.research.cards import cardmd
    from bot.research.cards.library.c1_xborder_mom import K, LEADER, XborderMom
    from bot.research.cards.run import run_card
    assert K == K_MIN
    with open(os.path.join(G.ROOT, "docs/RESEARCH/cards/c1_xborder_mom/CARD.md"), encoding="utf-8") as fh:
        st, problems = cardmd.settings(cardmd.parse(fh.read()))
    if problems:
        raise SystemExit(f"CARD.md の測定の設定が読めない: {problems}")
    decl = dict(st.declarations)
    G.check_hi(hi)
    edges = [lo]
    y = int(G.ns_iso(lo)[:4]) + 1
    while G.iso_ns(f"{y}-01-01T00:00:00Z") < hi:
        edges.append(G.iso_ns(f"{y}-01-01T00:00:00Z"))
        y += 1
    edges.append(hi)
    cols = {k: [] for k in ("start", "end", "open", "close", "volume", "decided", "exposure")}
    for a, b in zip(edges[:-1], edges[1:]):
        wa = a if a == lo else a - G.DAY_NS
        t0 = time.time()
        bars, _k, _h = load_bars(FX_DIR, "FX_BTC_JPY", wa, b)
        ref = load_reference(G.ROOT, binance_ref_dataset(LEADER, "close", wa - G.DAY_NS, b), declarations=decl)
        r = run_card(XborderMom(), bars, references={LEADER: ref}, declarations=decl, venue="bitflyer",
                     symbol="FX_BTC_JPY")
        keep = (r.start_ns >= a) & (r.volume > 0)
        for k, f in (("start", "start_ns"), ("end", "end_ns"), ("open", "open"), ("close", "close"),
                     ("volume", "volume"), ("decided", "decided"), ("exposure", "exposure")):
            cols[k].append(np.asarray(getattr(r, f))[keep])
        log(f"区切り {G.ns_iso(a)[:10]}〜{G.ns_iso(b)[:10]} 足 {int(keep.sum())} {time.time() - t0:.0f}s")
        del bars, ref, r
    return {k: np.concatenate(v) for k, v in cols.items()}


def signals(run: dict) -> np.ndarray:
    """1 合図 = 持ち高が ±1 に変わった決定(0 → ±1、∓1 → ±1)の位置(空でない足の並びの中)。"""
    e = run["exposure"][run["decided"]]
    prev = np.concatenate([[0.0], e[:-1]])
    idx = np.flatnonzero((e != 0) & (e != prev))
    return np.flatnonzero(run["decided"])[idx]


# ---------------------------------------------------------------------------------------------- 損益
def pnl_two_venues(run: dict, bin_t: np.ndarray, bin_open: np.ndarray, shift_ns: int = 0,
                   bf_start_all: np.ndarray | None = None, bf_open_all: np.ndarray | None = None) -> dict:
    """同じ e_t で bitFlyer と Binance を持った P(bp)。shift_ns = 0 は測定器の pnl と同じ(下で照合)。
    shift_ns ≠ 0 は対照: 約定・出の時刻を shift_ns ずらした始値(どちらの取引所も、その時刻に始まる足の始値。無ければ NaN)。"""
    from bot.research.cards.pnl import pnl
    ns = SimpleNamespace(decided=run["decided"], volume=run["volume"], exposure=run["exposure"], open=run["open"],
                         end_ns=run["end"], start_ns=run["start"])
    p = pnl(ns)
    e = p.exposure
    fs = run["start"][p.fill_bar] + shift_ns
    xs = run["start"][p.exit_bar] + shift_ns
    if shift_ns == 0:
        r_bf = p.r_bp
    else:
        bs, bo = (run["start"], run["open"]) if bf_start_all is None else (bf_start_all, bf_open_all)
        r_bf = (G.take(bo, G.exact_idx(bs, xs)) / G.take(bo, G.exact_idx(bs, fs)) - 1.0) * G.BP
    r_b = (G.take(bin_open, G.exact_idx(bin_t, xs)) / G.take(bin_open, G.exact_idx(bin_t, fs)) - 1.0) * G.BP
    P_bf = np.where(e == 0, 0.0, e * r_bf)
    P_b = np.where(e == 0, 0.0, e * r_b)
    return {"t": p.t_ns, "e": e, "P_bf": P_bf, "P_b": P_b, "pnl_card": p.pnl_bp}


# ---------------------------------------------------------------------------------------------- 戻るまでの分
def x_grid(lo: int, hi: int, bf_end: np.ndarray, bf_close: np.ndarray, bin_t: np.ndarray,
           bin_close: np.ndarray, fx_t: np.ndarray, fx_close: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """1 分刻みの分の終わり τ と X(τ) = ln(Binance as-of × USDJPY as-of) − ln(bitFlyer as-of)。
    Binance・USDJPY は行の時刻 ≤ τ − 60 秒(τ で終わる分まで)、bitFlyer は終わり ≤ τ。"""
    tau = np.arange(lo + G.MIN_NS, hi + 1, G.MIN_NS, dtype=np.int64)
    lb = np.log(G.take(bin_close, G.asof_idx(bin_t, tau - G.MIN_NS)))
    lb = lb + np.log(G.take(fx_close, G.asof_idx(fx_t, tau - G.MIN_NS)))
    lf = np.log(G.take(bf_close, G.asof_idx(bf_end, tau)))
    return tau, lb - lf


def return_minutes(tau: np.ndarray, X: np.ndarray, t_sig: np.ndarray, s_sig: np.ndarray,
                   shift_ns: int = 0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(戻るまでの分(戻らなければ NaN), D(t), 状態)。合図の時刻 t + shift_ns から前へ探す。基準 = t + shift_ns − 30 分。
    状態: 0 = 戻った、1 = 戻らない(基準はあるが、データの終わりまで D ≤ 0 にならない)、2 = 基準・起点の時刻が 1 分の格子に無い
    か、基準の X が無い(どちらも戻るまでの分は NaN)。"""
    t = np.asarray(t_sig, dtype=np.int64) + shift_ns
    k0 = np.searchsorted(tau, t, side="left")
    kb = np.searchsorted(tau, t - K_MIN * G.MIN_NS, side="left")
    n = len(tau)
    out = np.full(len(t), np.nan)
    d0 = np.full(len(t), np.nan)
    st = np.full(len(t), 2, dtype=np.int64)
    for i in range(len(t)):
        a, b = int(k0[i]), int(kb[i])
        if a >= n or b >= n or tau[a] != t[i] or tau[b] != t[i] - K_MIN * G.MIN_NS or not np.isfinite(X[b]):
            continue
        base, s = X[b], s_sig[i]
        st[i] = 1
        if np.isfinite(X[a]):
            d0[i] = s * (X[a] - base)
        w, j = 64, a
        while j < n:
            seg = s * (X[j:j + w] - base)
            hit = np.flatnonzero(seg <= 0)
            if len(hit):
                out[i] = float(j + hit[0] - a)
                st[i] = 0
                break
            j += w
            w *= 2
    return out, d0, st


def load_usdjpy(lo: int, hi: int):
    """USDJPY の 1 分足の終値(行の時刻 = 分の始まり)。common.usdjpy_ref_dataset(extend=True) を封印の門から読む。
    宣言はカード 3 の CARD.md(usdjpy_close、遅れ 60 秒)。"""
    from common import usdjpy_ref_dataset
    from bot.research.cards import cardmd
    from bot.research.cards.library.c3_yen_premium_revert import FX
    with open(os.path.join(G.ROOT, "docs/RESEARCH/cards/c3_yen_premium_revert/CARD.md"), encoding="utf-8") as fh:
        st, problems = cardmd.settings(cardmd.parse(fh.read()))
    if problems:
        raise SystemExit(f"カード 3 の CARD.md の宣言が読めない: {problems}")
    return G.ref_np(usdjpy_ref_dataset(FX, lo, hi, extend=True), FX, dict(st.declarations))


# ---------------------------------------------------------------------------------------------- 本体
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=LO_DEFAULT)
    ap.add_argument("--end", default=G.HI_MAX_ISO)
    ap.add_argument("--counts", action="store_true", help="件数だけ(値動き・損益を計算しない)")
    ap.add_argument("--cache", default=None, help="カードの走らせの記録(npz)。あれば読む・無ければ作って書く")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    lo, hi = G.iso_ns(a.start), G.iso_ns(a.end)
    G.check_hi(hi)
    t0 = time.time()
    if a.cache and os.path.exists(a.cache):
        z = np.load(a.cache)
        run = {k: z[k] for k in z.files}
        if int(run["lo"]) != lo or int(run["hi"]) != hi:
            raise SystemExit(f"--cache の期間 {G.ns_iso(int(run['lo']))}〜{G.ns_iso(int(run['hi']))} が引数と違う")
    else:
        run = run_card_chunks(lo, hi)
        run["lo"], run["hi"] = np.int64(lo), np.int64(hi)
        if a.cache:
            os.makedirs(os.path.dirname(os.path.abspath(a.cache)), exist_ok=True)
            np.savez_compressed(a.cache, **run)
    t_run = time.time() - t0
    all_days = G.all_days_between(lo, hi)
    sig = signals(run)
    e_dec = run["exposure"][run["decided"]]
    t_dec = run["end"][run["decided"]]
    head = [f"- 台本: `scripts/d1b/g1/c1_venue.py`(数は台本が出した。手で書いていない)",
            f"- 期間: {G.ns_iso(lo)} 〜 {G.ns_iso(hi)}(日本時間の暦日 {len(all_days)} 日)",
            f"- カードの走らせ: {t_run:.0f} 秒(--cache から読んだときは読み込みの秒)", ""]
    if a.counts:
        L = ["# # 1 カード 1 — 件数の数え上げ(値動き・損益を計算する前)", ""] + head
        L += G.md_counts("合図(持ち高が ±1 に変わった決定)", G.count_table(G.jst_day(run["end"][sig]), all_days), "合図の数")
        L += G.md_counts("持ち高が 0 でない決定", G.count_table(G.jst_day(t_dec[e_dec != 0]), all_days), "決定の数")
        L += G.md_counts("決定(空でない bitFlyer の足)", G.count_table(G.jst_day(t_dec), all_days), "決定の数")
        L += ["- 損益の単位は 1 日(日本時間)。日数が損益の件数。", ""]
        os.makedirs(a.out, exist_ok=True)
        with open(os.path.join(a.out, "COUNTS.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(L))
        G.write_json({"signals": G.count_table(G.jst_day(run["end"][sig]), all_days),
                      "nonzero_decisions": G.count_table(G.jst_day(t_dec[e_dec != 0]), all_days),
                      "decisions": G.count_table(G.jst_day(t_dec), all_days), "run_s": t_run},
                     os.path.join(a.out, "counts.json"))
        print("\n".join(L))
        return 0

    b = G.binance_ohlc(lo - 2 * G.DAY_NS, hi, "spot", cols=("open", "close"))  # 2 日前から(24 時間前の対照・基準の 30 分前)
    res = {"period": [G.ns_iso(lo), G.ns_iso(hi)], "n_signals": int(len(sig)),
           "inputs": {"binance_spot": b["manifest"]}}
    # 損益: 実・24 時間前・24 時間後
    pn = {"実": pnl_two_venues(run, b["t"], b["open"])}
    if not np.allclose(pn["実"]["P_bf"], pn["実"]["pnl_card"], equal_nan=True):
        raise SystemExit("bitFlyer の P が測定器の pnl と合わない")
    for lab, sh in (("24 時間前", -G.DAY_NS), ("24 時間後", G.DAY_NS)):
        pn[lab] = pnl_two_venues(run, b["t"], b["open"], sh)
    tabs = {}
    for lab, p in pn.items():
        both = np.isfinite(p["P_bf"]) & np.isfinite(p["P_b"])
        days = G.jst_day(p["t"])
        q = {"bitFlyer": np.where(both, p["P_bf"], np.nan), "Binance": np.where(both, p["P_b"], np.nan),
             "bitFlyer − Binance": np.where(both, p["P_bf"] - p["P_b"], np.nan)}
        tabs[lab] = {k: G.table(v, days, all_days, per="day") for k, v in q.items()}
        tabs[lab]["欠け(どちらかの始値が無く外した決定、持ち高 ≠ 0)"] = int(((~both) & (p["e"] != 0)).sum())
    res["損益(bp/日)"] = tabs
    # 戻るまでの分
    fx_t, fx_c, fx_m = load_usdjpy(lo - 9 * G.DAY_NS, hi)
    res["inputs"]["usdjpy"] = fx_m
    tau, X = x_grid(lo, hi, run["end"], run["close"], b["t"], b["close"], fx_t, fx_c)
    t_sig = run["end"][sig]
    s_sig = run["exposure"][sig]
    rm = {}
    for lab, sh in (("実", 0), ("24 時間前", -G.DAY_NS), ("24 時間後", G.DAY_NS)):
        m, d0, st = return_minutes(tau, X, t_sig, s_sig, sh)
        dsig = G.jst_day(t_sig)
        rm[lab] = {"戻るまでの分(1 合図あたり)": G.table(m, dsig, all_days, per="event"),
                   "分位": G.quantiles(m),
                   "NaN の件数": {"戻らない(データの終わりまで)": G.count_table(dsig[st == 1], all_days),
                                "基準・起点が無い": G.count_table(dsig[st == 2], all_days)},
                   "合図の時点の D(t)(bp、1 合図あたり)": G.table(d0 * G.BP, G.jst_day(t_sig), all_days, per="event")}
    res["戻るまでの分"] = rm
    res["所要_秒"] = round(time.time() - t0, 1)
    os.makedirs(a.out, exist_ok=True)
    G.write_json(res, os.path.join(a.out, "result.json"))
    L = ["# # 1 カード 1 — 持つ先 2 通りと戻るまでの分", ""] + head
    L += ["損益は bp、持ち高 1 単位、経費の前。1 日あたり = 日本時間の 1 日の P の和の平均。3 つの量は両方の始値がある決定だけ。", ""]
    for lab, tb in tabs.items():
        L += [f"## 損益(bp/日)— {lab}", ""] + G.MD_STAT_HEAD
        for k in ("bitFlyer", "Binance", "bitFlyer − Binance"):
            L += G.md_stat_rows(k, tb[k])
        L += ["", f"- 欠けた決定(持ち高 ≠ 0): {tb['欠け(どちらかの始値が無く外した決定、持ち高 ≠ 0)']}", ""]
    for lab, r in rm.items():
        L += [f"## 戻るまでの分(1 合図)— {lab}", ""] + G.MD_STAT_HEAD
        L += G.md_stat_rows("戻るまでの分", r["戻るまでの分(1 合図あたり)"])
        L += G.md_stat_rows("D(t) bp", r["合図の時点の D(t)(bp、1 合図あたり)"])
        L += ["", f"- 分位: {r['分位']}", "", "NaN の件数(戻るまでの分):", "",
              "| 区切り | 戻らない(データの終わりまで) | 基準・起点が無い |", "|---|---|---|"]
        nn = r["NaN の件数"]
        for k in ("全期間", "前半", "後半"):
            if k in nn["戻らない(データの終わりまで)"]:
                L.append(f"| {k} | {nn['戻らない(データの終わりまで)'][k]['n']} | {nn['基準・起点が無い'][k]['n']} |")
        L.append("")
    with open(os.path.join(a.out, "RESULT.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    print(f"書いた: {a.out} 所要 {res['所要_秒']} 秒")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

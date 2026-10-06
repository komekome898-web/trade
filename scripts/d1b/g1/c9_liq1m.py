#!/usr/bin/env python3
"""# 9 カード 9(清算の連鎖)の 1 分足の部分の前提の直接の測り(D1B_FRAMINGS.md の # 9 の行。秒の部分は担当 G3)。

行の言葉と、それを担う関数:
  問い「Binance の清算の後の動きは、bitFlyer にどれだけ・どの遅れで移るか」
  「Binance COIN-M の清算(2023-06-25〜12-17)」 load_prints: カード 9 の道具 liq_cascade_v2.load_prints(import。生の 10 列の
                                一致で一意化、走らせ (a) と同じ)。読み口は境で切った置き場 CM_ROOT(2023-12-16 までの日次 zip)で、
                                期間の終わりは 2023-12-17T00:00Z。2023-12-17 の 00:00〜15:00Z は失う(批評家 1 回目 問 4 への直し)
  「1 清算」                     1 件 = 一意化したプリント 1 件。向き = 清算の向き(SELL = ロングの強制決済 = 下 −1 / BUY +1、
                                liq_cascade_v2.REACT_SIGN)
  「1 分足で、清算の時刻からの bitFlyer と Binance の動きの差」 minute_moves: カード 9 の設計(REDESIGN_2026-10-03.md §3.2 の
                                「1 分の反応」)のとおり、t₀ を含む分の次の分の始値から、h 分後に終わる分の終値まで(清算の向きに正、bp)。
                                その分の足が無ければ NaN(前の値で埋めない)。差 = bitFlyer − Binance(両方ある件だけ)
  「時間 4」                     HORIZONS_MIN = 1・5・15・60 分
  「遅れの相互相関」             xcorr: 同じ設計 §3.2 の「遅れ」のとおり、清算の分の前後 ±10 分の 1 分の対数リターンで、
                                Binance と bitFlyer の相互相関(遅れ −10〜+10 分。正 = bitFlyer が後)。1 清算ごとの相関と、
                                相関が一番大きい遅れの分布
  「bitFlyer FX の 1 分足(175 日)」 g1common.bars_np(封印の門)
  「前半後半」                   g1common.table(年ごとは出さない。期間が 2023 年の中だけ)
  対照「清算の無い同じ勢いの時刻(カード 9 の対照 (ii))」 --controls: 担当 C の境で切った走らせ直しの出力 controls.csv.gz の
                                kind「(ii)合わせた時刻」の anchor_ms と dir(直前 10 秒の変位の符号)を、そのまま起点と向きに使う
                                (対照の作り方はカード 9 の道具のまま。ここでは作り直さない)。ref_id に値があれば、数えた清算の
                                id に入る行だけを使い、入らなかった件数を出す。開く前の確かめは load_controls、清算の数の照らしは check_prints_vs_run

読む前の止め(批評家 1 回目 問 4): 清算・約定・対照のどれも、境より後の行を読んでから落とす経路を持たない。清算と約定は
check_cut で終わりを 2023-12-17T00:00Z までに限り、読み口に 2023-12-17 以降のファイルが無い。対照は run_meta.json で走らせの
期間と、境で切った読み口で走らせたこと(約定の欠けた日に 2023-12-17)を確かめてから開く。境以降の行が出たら落とさずに拒む。

「Binance の動き」の値段(リードの決め 2026-10-06 の 6): Binance COIN-M BTCUSD_PERP の約定(aggTrades)から作る 1 分足が主
(清算と同じ商品)、Binance 現物 BTCUSDT の 1 分足を並べる(--binance coinm,spot、出力は result_coinm.json・result_spot.json)。
「時間 4」= 1・5・15・60 分(リードの決め 2026-10-06 の 4)。
どこで測るか: **この容器で打つ**(リードの決め 2026-10-06 の 7)。D1B_FRAMINGS の行は「測定用セッション」だが、対照 (ii) の起点
(data/c9_run_a/…/controls.csv.gz)と COIN-M の約定(backtest_data/binance_cm_o3c_20260913/aggTrades/)が git の外にあるため。

使い方:
  件数だけ: PYTHONPATH=src python3 scripts/d1b/g1/c9_liq1m.py --counts
  本走らせ: PYTHONPATH=src python3 scripts/d1b/g1/c9_liq1m.py
"""
from __future__ import annotations

import argparse
import gzip
import csv
import os
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import g1common as G  # noqa: E402

OUT = os.path.join(G.ROOT, "docs", "RESEARCH", "d1b", "9_card9")
HORIZONS_MIN = (1, 5, 15, 60)
LAGS = tuple(range(-10, 11))
WIN_MIN = 10
LO_DEFAULT = "2023-06-25T00:00:00Z"
# 境で切った読み口(担当 C の make_cut_root.py が作る、git の外)。2023-12-16 までの UTC の日次 zip だけへのリンクの置き場で、
# 2023-12-17 の zip(境 15:00Z の後の行を含む)に触れない。代わりに 2023-12-17 の 00:00〜15:00Z の清算・約定は失う。
CM_ROOT = "data/c9_run_a/cut_root_20231216"
CUT_LAST_DAY = "2023-12-16"
HI_DEFAULT = "2023-12-17T00:00:00Z"  # 読み口の最後の日の終わり。この台本の終わりの上限
CTRL_KIND = "(ii)合わせた時刻"
# 担当 C の境で切った走らせ直しの出力(git の外)。C の走らせ直しが終わるまで # 9 は打たない
CTRL_DEFAULT = "data/c9_run_a/rerun_quote_20230625_20231217/controls.csv.gz"


def check_cut(hi: int) -> None:
    """読む前の止め: 終わりが読み口の最後の日の終わり(2023-12-17T00:00Z)を越えれば、何も開かずに拒む。"""
    if hi > G.iso_ns(HI_DEFAULT):
        raise SystemExit(f"拒否: 終わり {G.ns_iso(hi)} は読み口の最後の日 {CUT_LAST_DAY} の終わりより後"
                         "(2023-12-17 の日次 zip は境 15:00Z の後の行を含むので読まない)")


def load_prints(lo: int, hi: int) -> dict:
    """清算(一意化)。読むのは境で切った読み口の [lo の日, hi − 1 の日] の日次 zip だけ。範囲の外の行が出たら落とさずに拒む。"""
    from bot.research import liq_cascade_v2 as V
    check_cut(hi)
    d0 = date.fromisoformat(G.ns_iso(lo)[:10])
    d1 = date.fromisoformat(G.ns_iso(hi - 1)[:10])
    pr = V.load_prints(Path(G.ROOT) / CM_ROOT, d0, d1)
    t = pr.ts.astype(np.int64) * 1_000_000
    if len(t) and (t.min() < lo - G.DAY_NS or t.max() >= hi):
        raise SystemExit(f"拒否: 読み口の清算に範囲の外の時刻がある({G.ns_iso(int(t.min()))}〜{G.ns_iso(int(t.max()))})")
    m = t >= lo
    st = pr.stats
    return {"t": t[m], "s": pr.sign[m], "id": np.asarray(pr.print_id, dtype=object)[m],
            "dedup": {"n_in": st.n_in, "n_out": st.n_out} if st else None}


CUT_PROOF_DAY = "2023-12-17"  # 境で切った読み口なら、担当 C の走らせの「約定の欠けた日(窓の中)」にこの日が入る


def load_controls(path: str, lo: int, hi: int, print_ids=None) -> dict:
    """対照 (ii) の起点。読む前の止め(controls.csv.gz を開く前に、隣の run_meta.json で確かめる。scripts/c9_run_a.py の書く形):
      「期間」= [start, end](c9_run_a.py の args.start・args.end)の終わりが 2023-12-17 以前であること、かつ
      「約定の欠けた日(窓の中)」に 2023-12-17 が入っていること(= 走らせの読み口に 2023-12-17 の約定の zip が無かった =
      境で切った読み口 cut_root_20231216 で走らせた。元の置き場で走らせたなら 2023-12-17 は欠けない)。
    どちらかが欠ければ開かずに拒む。開いた後、起点が lo より前か、境 2023-12-17T15:00Z 以降の行があれば、落とさずに拒む。
    hi(読み口の終わり 2023-12-17T00:00Z)以降・境より前の起点は残す(値動き・相関は足が無いので NaN になり、数えて出す)。
    ref_id の列に値があれば、print_ids(数えた清算の id)に入る行だけを使い、入らなかった件数を返す。"""
    import json
    meta_p = os.path.join(os.path.dirname(path), "run_meta.json")
    if not os.path.exists(meta_p):
        raise SystemExit(f"拒否: {meta_p} が無い(対照の走らせの期間を確かめられないので、対照を開かない)")
    with open(meta_p, encoding="utf-8") as fh:
        meta = json.load(fh)
    per = meta.get("期間")
    if not per or len(per) != 2 or str(per[1]) > CUT_PROOF_DAY:
        raise SystemExit(f"拒否: 対照の走らせの期間 {per} の終わりが {CUT_PROOF_DAY} より後(境より後を読む走らせ)。開かない")
    miss = meta.get("約定の欠けた日(窓の中)")
    if not isinstance(miss, list) or CUT_PROOF_DAY not in miss:
        raise SystemExit(f"拒否: 対照の走らせの「約定の欠けた日(窓の中)」に {CUT_PROOF_DAY} が無い(境で切った読み口で"
                         "走らせたことを確かめられない)。開かない")
    t, s, ref = [], [], []
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        r = csv.DictReader(fh)
        for row in r:
            if row["kind"] != CTRL_KIND:
                continue
            tt = int(row["anchor_ms"]) * 1_000_000
            if not (lo <= tt < G.HI_MAX):
                raise SystemExit(f"拒否: 対照の起点 {G.ns_iso(tt)} が範囲 [{G.ns_iso(lo)}, {G.HI_MAX_ISO}) の外")
            t.append(tt)
            s.append(float(row["dir"]))
            ref.append(row.get("ref_id") or "")
    o = np.argsort(t, kind="stable")
    out = {"t": np.array(t, dtype=np.int64)[o], "s": np.array(s)[o], "ref": np.array(ref, dtype=object)[o],
           "n_read": len(t), "ref_filter": None}
    out["読み口の終わり以降(境の前)の起点"] = int((out["t"] >= hi).sum())
    if print_ids is not None and len(out["ref"]) and all(out["ref"]):
        keep = np.isin(out["ref"], np.asarray(print_ids, dtype=object))
        out["ref_filter"] = {"入った": int(keep.sum()), "入らなかった": int((~keep).sum())}
        for k in ("t", "s", "ref"):
            out[k] = out[k][keep]
    return out


def check_prints_vs_run(controls_path: str, pr_t: np.ndarray, lo: int) -> dict:
    """担当 C の走らせの chunks/meta/<日>.json の prints(その UTC の日の全部のプリントの数)と、この台本の UTC の日ごとの
    清算の数を照らす(ref_id と print_id の照らしの前提: 同じ日の id は同じ並びで振られる)。1 日でも違うか、この台本の日に
    meta が無ければ止める。照らした日の数を返す。"""
    import json
    from bot.research import liq_cascade_v2 as V
    mdir = os.path.join(os.path.dirname(controls_path), "chunks", "meta")
    if not os.path.isdir(mdir):
        raise SystemExit(f"拒否: {mdir} が無い(清算の数を照らせない)")
    ours: dict = {}
    for tt in (np.asarray(pr_t, dtype=np.int64) // 1_000_000).tolist():
        d = V.day_of_ms(tt)
        ours[d] = ours.get(d, 0) + 1
    theirs = {}
    for f in sorted(os.listdir(mdir)):
        if f.endswith(".json"):
            with open(os.path.join(mdir, f), encoding="utf-8") as fh:
                m = json.load(fh)
            theirs[m["day"]] = int(m["prints"])
    lo_day = G.ns_iso(lo)[:10]
    bad = {d: (n, theirs.get(d)) for d, n in ours.items() if theirs.get(d) != n}
    bad.update({d: (ours.get(d, 0), n) for d, n in theirs.items() if d >= lo_day and ours.get(d, 0) != n})
    if bad:
        raise SystemExit(f"拒否: 日ごとの清算の数が担当 C の走らせと違う(日: (この台本, C)): {dict(sorted(bad.items())[:10])}")
    return {"照らした日": len([d for d in theirs if d >= lo_day]), "清算": int(sum(ours.values()))}


def coinm_bars(lo: int, hi: int) -> dict:
    """COIN-M の aggTrades(カード 9 の道具の TradeStore で、境で切った読み口から日ごとに読む)から 1 分足(空の分は無し)。
    読む日は [lo の日, hi − 1 の日] だけ(hi は読み口の最後の日の終わりまで)。"""
    from bot.research import liq_cascade_v2 as V
    check_cut(hi)
    store = V.TradeStore(Path(G.ROOT) / CM_ROOT)
    days = V.day_range(date.fromisoformat(G.ns_iso(lo)[:10]), date.fromisoformat(G.ns_iso(hi - 1)[:10]))
    cols = {k: [] for k in ("start", "open", "high", "low", "close")}
    for d in days:
        tr = store.day(d)
        store.drop_before(d)
        if tr is None or not len(tr.times):
            continue
        mins = tr.times // 60_000
        cut = np.flatnonzero(np.diff(mins)) + 1
        a = np.concatenate([[0], cut])
        b = np.concatenate([cut, [len(mins)]])
        cols["start"].append(mins[a].astype(np.int64) * 60 * G.NS)
        cols["open"].append(tr.prices[a])
        cols["close"].append(tr.prices[b - 1])
        cols["high"].append(np.maximum.reduceat(tr.prices, a))
        cols["low"].append(np.minimum.reduceat(tr.prices, a))
    if not cols["start"]:
        return {k: np.empty(0) for k in cols}
    out = {k: np.concatenate(v) for k, v in cols.items()}
    if out["start"].max() >= hi:
        raise SystemExit(f"拒否: COIN-M の約定に終わり {G.ns_iso(hi)} 以後の分がある")
    m = out["start"] >= lo
    return {k: v[m] for k, v in out.items()}


def minute_moves(t0: np.ndarray, s: np.ndarray, start: np.ndarray, open_: np.ndarray, close: np.ndarray,
                 h_min: int, hi: int) -> np.ndarray:
    """t₀ を含む分の次の分の始値 → h 分後に終わる分の終値(向き s に正、bp)。足が無ければ NaN。"""
    m1 = (t0 // G.MIN_NS + 1) * G.MIN_NS
    mh = m1 + (h_min - 1) * G.MIN_NS  # 終わりが m1 + h の分の始まり
    po = G.take(open_, G.exact_idx(start, m1))
    pc = G.take(close, G.exact_idx(start, mh))
    v = s * (pc / po - 1.0) * G.BP
    return np.where(mh + G.MIN_NS > hi, np.nan, v)


def xcorr(t0: np.ndarray, b: dict, f: dict, hi: int) -> tuple[np.ndarray, np.ndarray]:
    """(1 清算ごとの相関 [件, 遅れ], 相関が一番大きい遅れ(無ければ NaN))。分 m₀ = t₀ を含む分。
    リターン r_k = ln 終値_k − ln 終値_{k−1}(どちらかの分の足が無ければ NaN)、k は m₀ − 10 〜 m₀ + 10 分。
    遅れ L の相関 = corr(Binance r_k, bitFlyer r_{k+L})、k と k + L が両方とも窓の中で両方の値がある組だけ(組が 3 未満か
    分散 0 なら NaN)。"""
    m0 = t0 // G.MIN_NS * G.MIN_NS
    offs = np.arange(-WIN_MIN, WIN_MIN + 1) * G.MIN_NS
    K = m0[:, None] + offs[None, :]

    def rets(d):
        c1 = G.take(d["close"], G.exact_idx(d["start"], K.ravel())).reshape(K.shape)
        c0 = G.take(d["close"], G.exact_idx(d["start"], (K - G.MIN_NS).ravel())).reshape(K.shape)
        r = np.log(c1) - np.log(c0)
        return np.where(K + G.MIN_NS > hi, np.nan, r)
    rb, rf = rets(b), rets(f)
    n = K.shape[1]
    C = np.full((len(t0), len(LAGS)), np.nan)
    for j, L in enumerate(LAGS):
        if L >= 0:
            x, y = rb[:, :n - L], rf[:, L:]
        else:
            x, y = rb[:, -L:], rf[:, :n + L]
        ok = np.isfinite(x) & np.isfinite(y)
        k = ok.sum(axis=1)
        xm = np.where(ok, x, 0.0)
        ym = np.where(ok, y, 0.0)
        with np.errstate(invalid="ignore", divide="ignore"):
            mx = xm.sum(1) / k
            my = ym.sum(1) / k
            dx = np.where(ok, x - mx[:, None], 0.0)
            dy = np.where(ok, y - my[:, None], 0.0)
            c = (dx * dy).sum(1) / np.sqrt((dx * dx).sum(1) * (dy * dy).sum(1))
        C[:, j] = np.where((k >= 3) & np.isfinite(c), c, np.nan)
    best = np.full(len(t0), np.nan)
    has = np.isfinite(C).any(axis=1)
    best[has] = np.array(LAGS)[np.nanargmax(C[has], axis=1)]
    return C, best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--binance", default="coinm,spot", help="Binance の値段(カンマで)。coinm が主、spot を並べる")
    ap.add_argument("--controls", default=CTRL_DEFAULT, help="走らせ (a) の controls.csv.gz(git の外)")
    ap.add_argument("--start", default=LO_DEFAULT)
    ap.add_argument("--end", default=HI_DEFAULT)
    ap.add_argument("--counts", action="store_true")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    lo, hi = G.iso_ns(a.start), G.iso_ns(a.end)
    G.check_hi(hi)
    check_cut(hi)
    t0 = time.time()
    pr = load_prints(lo, hi)
    ct = load_controls(a.controls, lo, hi, pr["id"]) if a.controls else None
    if ct is not None:
        ct["清算の数の照らし"] = check_prints_vs_run(a.controls, pr["t"], lo)
    all_days = G.all_days_between(lo, hi)
    days = G.jst_day(pr["t"])
    head = [f"- 台本: `scripts/d1b/g1/c9_liq1m.py`(数は台本が出した。手で書いていない)",
            f"- 期間: {G.ns_iso(lo)} 〜 {G.ns_iso(hi)}(日本時間の暦日 {len(all_days)} 日)。一意化 {pr['dedup']}",
            f"- 対照 (ii): {a.controls or '(渡していない)'}"
            + ("" if ct is None else f"(読んだ (ii) の行 {ct['n_read']}、ref_id での絞り {ct['ref_filter']}、"
                                     f"C の走らせとの清算の数の照らし {ct['清算の数の照らし']}、読み口の終わり以降・境の前の起点 "
                                     f"{ct['読み口の終わり以降(境の前)の起点']}(値動き・相関は NaN))"),
            f"- 読み口: `{CM_ROOT}`(境で切った置き場、2023-12-16 までの日次 zip)。**2023-12-17 の 00:00〜15:00Z の清算・約定は"
            "失う**(2023-12-17 の zip は境の後の行を含むので読まない)", ""]
    os.makedirs(a.out, exist_ok=True)
    if a.counts:
        L = ["# # 9 カード 9(1 分足の部分)— 件数の数え上げ", ""] + head
        cj = {"清算(プリント)": G.count_table(days, all_days)}
        for side, nm in ((-1.0, "SELL(ロングの強制決済)"), (1.0, "BUY")):
            cj[nm] = G.count_table(days[pr["s"] == side], all_days)
        if ct is not None:
            cj["対照 (ii)"] = G.count_table(G.jst_day(ct["t"]), all_days)
        for k, v in cj.items():
            L += G.md_counts(k, v, "件数")
        with open(os.path.join(a.out, "COUNTS.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(L))
        G.write_json(cj, os.path.join(a.out, "counts.json"))
        print("\n".join(L))
        return 0
    if ct is None:
        raise SystemExit("本走らせには --controls(走らせ (a) の controls.csv.gz)が要る")
    srcs = [x for x in a.binance.split(",") if x]
    if not srcs or any(x not in ("coinm", "spot") for x in srcs):
        raise SystemExit(f"--binance は coinm・spot をカンマで: {a.binance!r}")
    rd_lo = lo - G.DAY_NS
    f = G.bars_np("backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906", "FX_BTC_JPY", rd_lo, hi)
    for src in srcs:
        role = "主(清算と同じ商品)" if src == "coinm" else "並べる"
        t1 = time.time()
        if src == "spot":
            b = G.binance_ohlc(rd_lo, hi, "spot")
            b["start"] = b["t"]
        else:
            b = coinm_bars(rd_lo, hi)
        write_one(a, src, role, b, f, pr, ct, all_days, head, lo, hi, t1)
    print(f"書いた: {a.out} 所要 {time.time() - t0:.1f} 秒")
    return 0


def write_one(a, src, role, b, f, pr, ct, all_days, head, lo, hi, t1) -> None:
    res = {"period": [G.ns_iso(lo), G.ns_iso(hi)], "binance": src, "役割": role, "controls": a.controls,
           "n_prints": int(len(pr["t"])), "n_controls": int(len(ct["t"])), "dedup": pr["dedup"], "表": {}}
    L = [f"# # 9 カード 9(1 分足の部分)— bitFlyer への移り(Binance = {src}、{role})", ""] + head
    L += ["値は bp、清算の向き(対照は dir の向き)に正。1 件 = 1 清算(対照は 1 時刻)。区間は日の塊(5 日・1,000 回・種 20261006)。", ""]
    for grp, (T, S) in (("清算", (pr["t"], pr["s"])), ("対照 (ii)", (ct["t"], ct["s"]))):
        dd = G.jst_day(T)
        L += [f"## {grp}", ""] + G.MD_STAT_HEAD
        for hm in HORIZONS_MIN:
            vb = minute_moves(T, S, b["start"], b["open"], b["close"], hm, hi)
            vf = minute_moves(T, S, f["start"], f["open"], f["close"], hm, hi)
            both = np.isfinite(vb) & np.isfinite(vf)
            for nm, v in (("Binance", np.where(both, vb, np.nan)), ("bitFlyer", np.where(both, vf, np.nan)),
                          ("bitFlyer − Binance", np.where(both, vf - vb, np.nan))):
                key = f"{grp}|{hm}分|{nm}"
                res["表"][key] = G.table(v, dd, all_days, per="event", with_years=False)
                res["表"][key]["分位"] = G.quantiles(v)
                L += G.md_stat_rows(f"{hm}分 {nm}", res["表"][key])
        C, best = xcorr(T, b, f, hi)
        for j, Lg in enumerate(LAGS):
            res["表"][f"{grp}|相関|遅れ {Lg:+d} 分"] = G.table(C[:, j], dd, all_days, per="event", with_years=False)
        L += [f"| 相関 遅れ {Lg:+d} 分 | 全期間 | {res['表'][f'{grp}|相関|遅れ {Lg:+d} 分']['全期間']['n']} | | "
              f"{G.fmt(res['表'][f'{grp}|相関|遅れ {Lg:+d} 分']['全期間']['estimate'], 3)} | "
              f"[{G.fmt(res['表'][f'{grp}|相関|遅れ {Lg:+d} 分']['全期間']['ci'][0], 3)}, "
              f"{G.fmt(res['表'][f'{grp}|相関|遅れ {Lg:+d} 分']['全期間']['ci'][1], 3)}] | |" for Lg in LAGS]
        h = len(all_days) // 2
        first = dd <= all_days[h - 1]
        dist = {}
        for part, m in (("全期間", np.ones(len(T), bool)), ("前半", first), ("後半", ~first)):
            bb = best[m]
            dist[part] = {"n": int(np.isfinite(bb).sum()), "n_nan": int((~np.isfinite(bb)).sum()),
                          **{f"{Lg:+d}": int((bb == Lg).sum()) for Lg in LAGS}}
        res["表"][f"{grp}|相関が一番大きい遅れの件数"] = dist
        L += ["", f"相関が一番大きい遅れの件数(全期間): {dist['全期間']}", ""]
    res["所要_秒"] = round(time.time() - t1, 1)
    G.write_json(res, os.path.join(a.out, f"result_{src}.json"))
    with open(os.path.join(a.out, f"RESULT_{src}.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""高ボラの門(`DESIGN.md`)の問い 1・2 を測る台本。

DESIGN.md の問い(逐語):

1. **持続**: 足ごとの vol_prev(合図の取引所 = Binance 現物、足 5・15・30・60 分)の三分位と、その後の同じ長さ
   (次の 100 本)の実際のボラの三分位の移り変わりの表(高 → 高の割合)と順位相関を、年ごと(2018〜2023)に出す。
   bitFlyer の足でも同じ表を出す(執行の側のボラ)。
2. **門の取れ方**: K1 の設計(H1+H2a+H3・弱いだけ、門 s19/b24)の取引(Binance の合図 × bitFlyer の値段、足の終値で
   約定 = 段階 G と同じ)を、次の 3 通りで三分位に分け、年ごとの取引数・平均・総損益・区間を出す。
   - (a) vol_prev × K1 の固定の境目(2018〜2019 の取引で決めた値)
   - (b) vol_prev × 前の暦年の取引から決めた境目(毎年決め直す。先読み無し)
   - (c) 取引の間の実際のボラ(後でしか分からない。上限の参考で、門には使えない)
   (c) と (a)(b) の差が「前もって狙えなかった分」。

この台本が今回行うこと:

- 読み込み: 段階 G の読み(`scripts/k1_newenv_g_fold.py` の `read_layer` / `to_minutes` / `BIN_SPEC` / `BF_SPEC` /
  `CUT` を import。import の時点で段階 G のデータの門 `scripts/k1_newenv_g_datagate.py` が入る)。年ごとに
  [その年の 1 月 1 日, min(翌年の 1 月 1 日, CUT = 2023-12-18T00:00Z)) をデータ層の range_ns で読む。
  UTC の分で内部結合し、両取引所を同じ窓で畳む(`bot.bt.vector.bars.bars_from_bars`)。段階 G と同じ手順。
- 畳んだ 5・15 分の足が段階 G の出力 `backtest_data/k1_newenv_g_20261001/{binance,bitflyer}_{5,15}m_full.csv.gz`
  と行ごとに同じかを確かめる。
- 再現の検め: 5・15 分の設計の取引(`measure_katsuo_effect.signals` / `delay_signals` / `simulate`)を
  `measure_katsuo_robustness.FootData.vol_prev` で K1 の保存した境目(`results/PHASE2/K1/xvenue/vol_terciles.json`
  の `edges_bp_own`)の三分位に分け(`measure_katsuo_xvenue.per_year_tercile`)、2018〜2021 を vol_terciles.json と
  比べる。違えば差を出す。差の原因の確かめとして、K1 当時の結合(分の頭に乗らない Binance の行を落とす。
  `docs/PHASE2/K1/NEWENV_G/DIFF.md` §3 D-1)の変種でも同じ表を作って比べる。
- 問い 1: 足 5・15・30・60 分 × Binance・bitFlyer(結合後の足)× 2018〜2023。
  vol_prev[i] = 足 i−100〜i−1 の |log(close[j]/close[j−1])| × 1e4 の平均(FootData.vol_prev そのもの)。
  vol_next[i] = 足 i+1〜i+100 の同じ量の平均 = vol_prev[i+101](同じ式を 101 本ずらしたもの)。
  三分位の境目は、その年の前の暦年の全足の vol_prev から `measure_katsuo_xvenue.edges_from_vol` で決め、
  vol_prev と vol_next の両方に同じ境目を当てる(`measure_katsuo_xvenue.bucket_of`)。
  順位相関は scipy.stats.spearmanr(その年の足で、vol_prev と vol_next の両方に値があるもの)。
- 問い 2(リードの答え 2026-10-03、§7 の 1〜4): 段階 G の読みで、足 5・15・30・60 分の設計の取引
  (`design_trades`)を次の 3 通りで三分位に分け、年ごと(2017〜2023)・三分位ごとに取引数・平均 bp・区間・総損益を出す。
  年は取引の入口の足の年。
  - (a) vol_prev(合図の足 = 結合後の Binance、入口の足 i の FootData.vol_prev)× この読みの 2018〜2019 の取引の
    vol_prev から `edges_from_vol` で決めた固定の境目。2017 は境目を決めた期間より前なので「先読みあり」の印。
  - (b) vol_prev × 前の暦年の取引の vol_prev から `edges_from_vol` で決めた境目(毎年決め直す)。2017 は空欄。
  - (c) 取引の間の bitFlyer の実際のボラ = 結合後の bitFlyer の足 j = 入口+1〜決済 の |log(close[j]/close[j−1])| × 1e4
    の平均。境目はその年の取引の (c) から `edges_from_vol`(同じ年の値で切る。後でしか分からない上限)。
  区間は `measure_katsuo_effect.block_bootstrap`(入口の日のブロック、200 回)、升ごとに新しい
  `random.Random(measure_katsuo_effect.SEED)`。K1 の `summarize_cell` と同じく取引数 30 未満の升は区間を出さない。

出力: 同じフォルダの `vol_gate.json` と `TABLES.md`(どちらもこの台本が書く)。それ以外は書かない
(`--cache` を名指ししたときだけ、読んだ分足をその場所に .npz で置く / あれば読み直さずに使う)。
ネットワークは使わない。乱数は区間だけで、種は固定(升ごとに同じ種から始める)。

使い方:
    K1G_DATAGATE_LOG=<scratchpad>/gate.log PYTHONPATH=scripts:src \\
        python3 docs/RESEARCH/cards/c2_owner_xvenue_wick/vol_gate/measure_vol_gate.py --cache <scratchpad>/minutes.npz
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import random
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import k1_newenv_g_fold as G  # noqa: E402  (段階 G の読み。import の時点でデータの門が入る)
import numpy as np  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

import measure_katsuo_effect as eff  # noqa: E402
import measure_katsuo_robustness as rb  # noqa: E402
import measure_katsuo_xvenue as xv  # noqa: E402
from bot.bt.vector import bars as VB  # noqa: E402

NS = G.NS
CUT = G.CUT
YEARS_READ = tuple(range(2017, 2024))
FEET = (5, 15, 30, 60)
Q1_YEARS = tuple(range(2018, 2024))
CHECK_FEET = (5, 15)
CHECK_YEARS = (2018, 2019, 2020, 2021)
GATE_S, GATE_B = xv.MAIN_GATE_SMALL, xv.MAIN_GATE_BIG
K1_VOL_TERCILES = REPO / "results" / "PHASE2" / "K1" / "xvenue" / "vol_terciles.json"
STAGE_G_DIR = REPO / "backtest_data" / "k1_newenv_g_20261001"
BUCKETS = ("low", "mid", "high")


def iso_s(t: int) -> str:
    return datetime.fromtimestamp(int(t), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------- 読み込み(段階 G の読み)

def read_minutes(cache: str | None):
    keys = ("t", "o", "h", "l", "c", "v")
    if cache and os.path.isfile(cache):
        z = np.load(cache, allow_pickle=False)
        sig = {k: z["s_" + k] for k in keys}
        pri = {k: z["p_" + k] for k in keys}
        with open(cache + ".json", encoding="utf-8") as fh:
            meta = json.load(fh)
        return sig, pri, meta["inputs"], meta["opened_when_reading"]
    sig = {k: [] for k in keys}
    pri = {k: [] for k in keys}
    infos = []
    for y in YEARS_READ:
        lo = G.ns_of(f"{y}-01-01T00:00:00")
        hi = min(G.ns_of(f"{y + 1}-01-01T00:00:00"), CUT)
        cols, info = G.read_layer(f"{G.BIN_DIR}/binance_BTCUSDT_1m_{y}.csv.gz", G.BIN_SPEC, lo, hi)
        infos.append(info)
        for k in keys:
            sig[k].extend(cols[k])
        cols, info = G.read_layer(f"{G.BF_DIR}/candles_1m_{y}.csv.gz", G.BF_SPEC, lo, hi)
        infos.append(info)
        for k in keys:
            pri[k].extend(cols[k])
        print(f"  {y} 読んだ", flush=True)
    sig = {k: np.asarray(v, dtype=np.int64 if k == "t" else np.float64) for k, v in sig.items()}
    pri = {k: np.asarray(v, dtype=np.int64 if k == "t" else np.float64) for k, v in pri.items()}
    opened = [os.path.relpath(p, REPO) for p in G.GATE.OPENED]
    if cache:
        np.savez(cache, **{"s_" + k: v for k, v in sig.items()}, **{"p_" + k: v for k, v in pri.items()})
        with open(cache + ".json", "w", encoding="utf-8") as fh:
            json.dump({"inputs": infos, "opened_when_reading": opened}, fh)
    return sig, pri, infos, opened


def join_and_fold(sig_min: dict, pri_min: dict, feet) -> tuple[dict, dict]:
    """段階 G の結合と畳み(`k1_newenv_g_fold.main` と同じ手順)。足は (ts 秒, o, h, l, c) のタプルの列。"""
    sm, pm = G.to_minutes(sig_min), G.to_minutes(pri_min)
    common, si, pi = np.intersect1d(sm["t"], pm["t"], assume_unique=True, return_indices=True)
    S = {k: v[si] for k, v in sm.items()}
    P = {k: v[pi] for k, v in pm.items()}
    out_s, out_p = {}, {}
    for foot in feet:
        sb = VB.bars_from_bars(S["t"], S["o"], S["h"], S["l"], S["c"], S["v"], foot * 60)
        pb = VB.bars_from_bars(P["t"], P["o"], P["h"], P["l"], P["c"], P["v"], foot * 60)
        if [b["start_ns"] for b in sb] != [b["start_ns"] for b in pb]:
            raise SystemExit(f"foot {foot}: 結合後の窓が両取引所で違う")
        keep = [i for i, b in enumerate(sb) if b["start_ns"] + foot * 60 * NS <= CUT]
        out_s[foot] = [(int(sb[i]["start_ns"] // NS), float(sb[i]["open"]), float(sb[i]["high"]),
                        float(sb[i]["low"]), float(sb[i]["close"])) for i in keep]
        out_p[foot] = [(int(pb[i]["start_ns"] // NS), float(pb[i]["open"]), float(pb[i]["high"]),
                        float(pb[i]["low"]), float(pb[i]["close"])) for i in keep]
    return out_s, out_p, int(len(common))


def compare_with_stage_g(bars: list, venue: str, foot: int) -> dict:
    path = STAGE_G_DIR / f"{venue}_{foot}m_full.csv.gz"
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        next(fh)
        ref = []
        for line in fh:
            ts, o, h, l, c, _v = line.rstrip("\n").split(",")
            t = int(datetime.fromisoformat(ts).replace(tzinfo=timezone.utc).timestamp())
            ref.append((t, float(o), float(h), float(l), float(c)))
    n_diff = sum(1 for a, b in zip(bars, ref) if a != b)
    return {"file": str(path.relative_to(REPO)), "rows_here": len(bars), "rows_stage_g": len(ref),
            "rows_differ": n_diff + abs(len(bars) - len(ref)),
            "identical": len(bars) == len(ref) and n_diff == 0}


# ---------------------------------------------------------------- 設計の取引

def design_trades(sig_bars, price_bars):
    sg = eff.delay_signals(eff.signals(sig_bars, GATE_S, GATE_B, flip_body=True))   # H1 + H3
    price_close = [b[4] for b in price_bars]
    return eff.simulate(sig_bars, sg, "weak", use_invalid=False, prices=price_close)  # 弱いだけ、H2a


def trades_year_ret_vol(sig_bars, trades):
    fd = rb.FootData(sig_bars)
    return [(xv.year_of(sig_bars[i][0]), r, float(fd.vol_prev[i])) for i, r, _h, _w in trades]


# ---------------------------------------------------------------- 再現の検め

def run_check(sig_bars_by_foot, price_bars_by_foot, k1, label):
    out = {}
    for foot in CHECK_FEET:
        trades = design_trades(sig_bars_by_foot[foot], price_bars_by_foot[foot])
        tyv = trades_year_ret_vol(sig_bars_by_foot[foot], trades)
        stored = tuple(k1["feet"][str(foot)]["edges_bp_own"])
        train = [v for y, _r, v in tyv if xv.VOL_TRAIN_START_YEAR <= y <= xv.VOL_TRAIN_END_YEAR]
        edges_re = xv.edges_from_vol(train)
        years = sorted(set(y for y, _r, _v in tyv))
        res = {"stored_edges": list(stored),
               "recomputed_edges_from_this_read_2018_2019": [edges_re[0], edges_re[1]],
               "recomputed_edges_rounded_equal_stored": [round(edges_re[0], 2), round(edges_re[1], 2)] == list(stored),
               "n_trades_total": len(tyv),
               "near_stored_edge_0p005": sum(1 for _y, _r, v in tyv
                                             if v == v and min(abs(v - stored[0]), abs(v - stored[1])) <= 0.005)}
        for tag, edges in (("stored_edges", stored), ("recomputed_edges", edges_re)):
            pt = xv.per_year_tercile(tyv, edges, years)
            rows = {}
            for y in years:
                here = pt[str(y)]
                ref = k1["feet"][str(foot)]["per_year_own_edges"].get(str(y))
                rows[str(y)] = {"here": here, "k1": ref,
                                "equal": ref is not None and all(here[b] == ref[b] for b in BUCKETS)}
            res[tag] = rows
        out[str(foot)] = res
        print(f"  検め[{label}] {foot}分: " + " ".join(
            f"{y}:{'一致' if res['stored_edges'][str(y)]['equal'] else '違う'}" for y in CHECK_YEARS), flush=True)
    return out


# ---------------------------------------------------------------- 問い 1

def q1_table(bars, years=Q1_YEARS):
    fd = rb.FootData(bars)
    vp = fd.vol_prev
    n = len(bars)
    vn = np.full(n, np.nan)
    if n > rb.VOL_WINDOW + 1:
        vn[:n - (rb.VOL_WINDOW + 1)] = vp[rb.VOL_WINDOW + 1:]
    yr = fd.year
    out = {}
    for y in years:
        prev_vals = vp[(yr == y - 1) & ~np.isnan(vp)]
        edges = xv.edges_from_vol(prev_vals.tolist())
        m_year = yr == y
        both = m_year & ~np.isnan(vp) & ~np.isnan(vn)
        a, b = vp[both], vn[both]
        counts = {fb: {tb: 0 for tb in BUCKETS} for fb in BUCKETS}
        for x, z in zip(a.tolist(), b.tolist()):
            counts[xv.bucket_of(x, edges)][xv.bucket_of(z, edges)] += 1
        shares = {}
        for fb in BUCKETS:
            tot = sum(counts[fb].values())
            shares[fb] = {tb: (round(counts[fb][tb] / tot, 4) if tot else None) for tb in BUCKETS}
        rho = spearmanr(a, b).statistic if a.size > 2 else float("nan")
        prev_share = {fb: (round(sum(counts[fb].values()) / int(both.sum()), 4) if both.sum() else None)
                      for fb in BUCKETS}
        out[str(y)] = {
            "edges_bp_from_prev_year": [round(edges[0], 4), round(edges[1], 4)] if edges else None,
            "n_bars_prev_year_for_edges": int(prev_vals.size),
            "n_bars_year": int(m_year.sum()),
            "n_bars_used": int(both.sum()),
            "n_no_vol_prev": int((m_year & np.isnan(vp)).sum()),
            "n_no_vol_next": int((m_year & ~np.isnan(vp) & np.isnan(vn)).sum()),
            "counts": counts,
            "row_shares": shares,
            "share_of_bars_by_vol_prev_tercile": prev_share,
            "high_to_high": shares["high"]["high"],
            "spearman_rho": None if rho != rho else round(float(rho), 4),
        }
    return out


# ---------------------------------------------------------------- 問い 2

Q2_YEARS = tuple(range(2017, 2024))
PERIOD_YEARS = tuple(range(2018, 2024))


def realized_vol_during(price_close, entry_i, hold):
    """取引の間の bitFlyer の実際のボラ: 足 j = entry_i+1 .. entry_i+hold の |log(c[j]/c[j-1])| × 1e4 の平均。"""
    vals = [abs(math.log(price_close[j] / price_close[j - 1])) * 1e4
            for j in range(entry_i + 1, entry_i + hold + 1)]
    return sum(vals) / len(vals) if vals else float("nan")


def cell_stats(sub, bar_ts):
    rs = [r for _i, r, _h, _w in sub]
    n = len(rs)
    if n == 0:
        return {"n": 0, "mean_bp": None, "ci95_bp": None, "total_bp": 0.0}
    ci = None
    if n >= 30:  # K1 の summarize_cell と同じ足切り
        lo, hi = eff.block_bootstrap(sub, bar_ts, random.Random(eff.SEED))
        ci = [round(lo, 3), round(hi, 3)]
    return {"n": n, "mean_bp": round(sum(rs) / n, 3), "ci95_bp": ci, "total_bp": round(sum(rs), 1)}


def q2_foot(sig_bars, price_bars):
    trades = design_trades(sig_bars, price_bars)
    fd = rb.FootData(sig_bars)
    pc = [b[4] for b in price_bars]
    bar_ts = [b[0] for b in sig_bars]
    rows = []
    for tr in trades:
        i, _r, h, _w = tr
        rows.append({"tr": tr, "y": xv.year_of(sig_bars[i][0]), "vp": float(fd.vol_prev[i]),
                     "vc": realized_vol_during(pc, i, h)})
    train = [t["vp"] for t in rows if xv.VOL_TRAIN_START_YEAR <= t["y"] <= xv.VOL_TRAIN_END_YEAR]
    edges_a = xv.edges_from_vol(train)
    out = {"n_trades": len(rows),
           "n_no_vol_prev": sum(1 for t in rows if t["vp"] != t["vp"]),
           "n_no_vol_during": sum(1 for t in rows if t["vc"] != t["vc"]),
           "edges_a_bp": [edges_a[0], edges_a[1]],
           "edges_a_basis": "この読みの 2018〜2019 の取引の vol_prev、edges_from_vol",
           "years": {}}
    for y in Q2_YEARS:
        ys = [t for t in rows if t["y"] == y]
        prev = [t["vp"] for t in rows if t["y"] == y - 1]
        edges_b = xv.edges_from_vol(prev) if prev else None
        edges_c = xv.edges_from_vol([t["vc"] for t in ys]) if ys else None
        yr = {"all": cell_stats([t["tr"] for t in ys], bar_ts),
              "a": {"edges_bp": [edges_a[0], edges_a[1]], "lookahead": y < xv.VOL_TRAIN_START_YEAR},
              "b": {"edges_bp": None if edges_b is None else [edges_b[0], edges_b[1]],
                    "edges_from_year": y - 1 if edges_b else None},
              "c": {"edges_bp": None if edges_c is None else [edges_c[0], edges_c[1]]}}
        for key, val, edges in (("a", "vp", edges_a), ("b", "vp", edges_b), ("c", "vc", edges_c)):
            if edges is None:
                yr[key]["blank"] = True
                continue
            for bk in BUCKETS:
                yr[key][bk] = cell_stats([t["tr"] for t in ys if xv.bucket_of(t[val], edges) == bk], bar_ts)
            yr[key]["n_unbucketed"] = sum(1 for t in ys if xv.bucket_of(t[val], edges) is None)
        out["years"][str(y)] = yr
    # 2018〜2023 をまとめた升((a) の 2017 は先読みあり、(b) の 2017 は空欄なので 2017 は入れない)。
    # 三分位は年ごとの境目で決めたものをそのまま束ねる。区間は束ねた取引で同じ方法
    per = {"years": [PERIOD_YEARS[0], PERIOD_YEARS[-1]],
           "all": cell_stats([t["tr"] for t in rows if t["y"] in PERIOD_YEARS], bar_ts)}
    for key, val in (("a", "vp"), ("b", "vp"), ("c", "vc")):
        per[key] = {}
        for bk in BUCKETS:
            sub = []
            for y in PERIOD_YEARS:
                e = out["years"][str(y)][key].get("edges_bp")
                if e is None:
                    continue
                sub += [t["tr"] for t in rows if t["y"] == y and xv.bucket_of(t[val], tuple(e)) == bk]
            per[key][bk] = cell_stats(sub, bar_ts)
    out["period_2018_2023"] = per
    return out


# ---------------------------------------------------------------- TABLES.md

def fmt(x, d=2):
    if x is None:
        return "—"
    return f"{x:+.{d}f}" if isinstance(x, float) else f"{x:,}"


def write_md(res: dict, path: Path):
    L = []
    L.append("# 高ボラの門 — 問い 1・2 の表(台本 `measure_vol_gate.py` の出力。手で打っていない)")
    L.append("")
    L.append("出所: 同じフォルダの `vol_gate.json`。設計・問いは `DESIGN.md`。")
    L.append("")
    L.append("## 0. 読んだ範囲(`vol_gate.json: read`)")
    L.append("")
    L.append("| ファイル | 範囲(range_ns) | 読んだ行 | 範囲内の行 | 方針の後の事象 | 最初の ts | 最後の ts | 分の頭でない行 | sha256(先頭 12) |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for i in res["read"]["inputs"]:
        L.append(f"| `{i['path']}` | {i['range'][0]} 〜 {i['range'][1]} | {i['rows_read']:,} | {i['rows_kept_in_range']:,} | "
                 f"{i['events_after_policy']:,} | {i['first_ts']} | {i['last_ts_after_policy']} | {i['off_minute_rows']:,} | {i['sha256'][:12]} |")
    r = res["read"]
    L.append("")
    L.append(f"- 方針の後の事象の最後の開始: Binance {r['max_event_start_signal']} / bitFlyer {r['max_event_start_price']}"
             f"(境 {r['cut']} より前: {r['max_event_end_le_cut']})。結合後の分: {r['minutes_both']:,}。")
    L.append(f"- 畳んだ足の最後の足の終わり: {r['max_bar_end']}(境以下: {r['max_bar_end_le_cut']})。")
    L.append(f"- 門が開くのを許したデータの置き場のファイル: 読み込みの段 {len(r['files_opened_under_data_roots_when_reading'])} 件"
             f"(`files_opened_under_data_roots_when_reading`)、その後 {len(r['files_opened_under_data_roots_after_reading'])} 件"
             f"(段階 G の畳んだ足との突き合わせ。`files_opened_under_data_roots_after_reading`)。")
    L.append("")
    L.append("## 1. 段階 G の畳んだ足との突き合わせ(`vol_gate.json: stage_g_fold_compare`)")
    L.append("")
    L.append("| 足 | 取引所 | ここの行 | 段階 G の行 | 違う行 | 同じ |")
    L.append("|---|---|---|---|---|---|")
    for k, v in res["stage_g_fold_compare"].items():
        foot, venue = k.split("|")
        L.append(f"| {foot} 分 | {venue} | {v['rows_here']:,} | {v['rows_stage_g']:,} | {v['rows_differ']:,} | {v['identical']} |")
    L.append("")
    L.append("## 2. 再現の検め(`vol_gate.json: check`)")
    L.append("")
    L.append("境目 (a) = K1 の保存値 `edges_bp_own`。各升 = 取引数 / 平均 bp / 総損益 bp。「K1」= `results/PHASE2/K1/xvenue/vol_terciles.json: feet.<足>.per_year_own_edges`。")
    for tag, title in (("stage_g_read", "段階 G の読み(この測定の読み)"),
                       ("k1_join_variant", "変種: K1 当時の結合(分の頭に乗らない Binance の行を落とす。DIFF.md §3 D-1)")):
        L.append("")
        L.append(f"### 2.{1 if tag == 'stage_g_read' else 2} {title}")
        for foot, fv in res["check"][tag].items():
            L.append("")
            L.append(f"{foot} 分: 保存した境目 {fv['stored_edges']}、この読みの 2018〜2019 の取引から決め直した境目 "
                     f"[{fv['recomputed_edges_from_this_read_2018_2019'][0]:.4f}, {fv['recomputed_edges_from_this_read_2018_2019'][1]:.4f}]"
                     f"(小数 2 桁で保存値と同じ: {fv['recomputed_edges_rounded_equal_stored']})。"
                     f"保存した境目から ±0.005 bp 以内の取引 {fv['near_stored_edge_0p005']} 件。")
            for etag, etitle in (("stored_edges", "保存した境目"), ("recomputed_edges", "決め直した境目(丸めない)")):
                L.append("")
                L.append(f"| 年({etitle}) | 低 ここ | 低 K1 | 中 ここ | 中 K1 | 高 ここ | 高 K1 | 一致 |")
                L.append("|---|---|---|---|---|---|---|---|")
                for y, row in fv[etag].items():
                    if int(y) > 2022:
                        continue
                    cells = []
                    for b in BUCKETS:
                        h = row["here"][b]
                        k = row["k1"][b] if row["k1"] else None
                        cells.append(f"{h['n']:,} / {fmt(h['mean_bp'], 3)} / {fmt(h['total_bp'], 1)}")
                        cells.append(f"{k['n']:,} / {fmt(k['mean_bp'], 3)} / {fmt(k['total_bp'], 1)}" if k else "—")
                    L.append(f"| {y} | " + " | ".join(cells) + f" | {row['equal']} |")
    L.append("")
    L.append(f"判定の材料(機械): {res['check']['summary']}")
    L.append("")
    L.append("## 3. 問い 1 — vol_prev の三分位 → 次の 100 本のボラの三分位(`vol_gate.json: q1`)")
    L.append("")
    L.append(res["q1_definition"])
    L.append("")
    L.append(res["q1_note"])
    L.append("")
    for foot, fv in res["q1"].items():
        for venue, vv in fv.items():
            L.append(f"### {foot} 分・{venue}")
            L.append("")
            L.append("| 年 | 境目 bp(前の年) | 使った足 | 順位相関 | 高→高 | 高→中 | 高→低 | 低→低 | 低→高 | vol_prev の三分位の割合(低/中/高) |")
            L.append("|---|---|---|---|---|---|---|---|---|---|")
            for y, t in vv.items():
                s = t["row_shares"]
                e = t["edges_bp_from_prev_year"]
                ps = t["share_of_bars_by_vol_prev_tercile"]
                L.append(f"| {y} | {e[0]:.2f} / {e[1]:.2f} | {t['n_bars_used']:,} | {t['spearman_rho']:.4f} | "
                         f"{s['high']['high']:.4f} | {s['high']['mid']:.4f} | {s['high']['low']:.4f} | "
                         f"{s['low']['low']:.4f} | {s['low']['high']:.4f} | {ps['low']:.4f} / {ps['mid']:.4f} / {ps['high']:.4f} |")
            L.append("")
            L.append("移り変わりの件数(行 = vol_prev の三分位、列 = 次の 100 本の三分位、低/中/高):")
            L.append("")
            L.append("| 年 | 低→(低/中/高) | 中→(低/中/高) | 高→(低/中/高) | vol_prev 無し | vol_next 無し |")
            L.append("|---|---|---|---|---|---|")
            for y, t in vv.items():
                c = t["counts"]
                L.append(f"| {y} | " + " | ".join(
                    f"{c[fb]['low']:,} / {c[fb]['mid']:,} / {c[fb]['high']:,}" for fb in BUCKETS)
                         + f" | {t['n_no_vol_prev']:,} | {t['n_no_vol_next']:,} |")
            L.append("")
    L.append("## 4. 問い 2 — 設計の取引を三分位に分けた成績(`vol_gate.json: q2`)")
    L.append("")
    for line in res["q2"]["notes"]:
        L.append(f"- {line}")
    L.append("")
    L.append("各升 = 取引数 / 平均 bp [95% 区間] / 総損益 bp。区間は取引数 30 以上の升だけ。")
    names = {"a": "(a) vol_prev × 2018〜2019 で決めた固定の境目",
             "b": "(b) vol_prev × 前の暦年の取引で決めた境目",
             "c": "(c) 取引の間の bitFlyer の実際のボラ × その年の三分位(後でしか分からない上限)"}

    def cell(cs):
        if cs["n"] == 0:
            return "0"
        ci = f" [{cs['ci95_bp'][0]:+.2f}, {cs['ci95_bp'][1]:+.2f}]" if cs["ci95_bp"] else ""
        return f"{cs['n']:,} / {cs['mean_bp']:+.2f}{ci} / {cs['total_bp']:+,.0f}"
    for foot, fv in res["q2"]["feet"].items():
        L.append("")
        L.append(f"### {foot} 分(取引 {fv['n_trades']:,} 件、(a) の境目 {fv['edges_a_bp'][0]:.4f} / {fv['edges_a_bp'][1]:.4f} bp)")
        L.append("")
        L.append("全取引(三分位に分けない):")
        L.append("")
        L.append("| 年 | 全取引 |")
        L.append("|---|---|")
        for y, yr in fv["years"].items():
            L.append(f"| {y} | {cell(yr['all'])} |")
        for key in ("a", "b", "c"):
            L.append("")
            L.append(names[key] + ":")
            L.append("")
            L.append("| 年 | 境目 bp | 低 | 中 | 高 | 分けられない取引(値が無い) |")
            L.append("|---|---|---|---|---|---|")
            for y, yr in fv["years"].items():
                d = yr[key]
                if d.get("blank"):
                    L.append(f"| {y} | 空欄(前の年が無い) | — | — | — | — |")
                    continue
                mark = "(先読みあり)" if key == "a" and d.get("lookahead") else ""
                e = d["edges_bp"]
                L.append(f"| {y}{mark} | {e[0]:.2f} / {e[1]:.2f} | " + " | ".join(cell(d[b]) for b in BUCKETS)
                         + f" | {d['n_unbucketed']:,} |")
        pp = fv["period_2018_2023"]
        L.append("")
        L.append("2018〜2023 をまとめた升(`period_2018_2023`。三分位は年ごとの境目で分けたものを束ねた。2017 は (a) 先読みあり・(b) 空欄のため入れない):")
        L.append("")
        L.append("| 分け方 | 低 | 中 | 高 |")
        L.append("|---|---|---|---|")
        L.append(f"| 全取引 | {cell(pp['all'])} | | |")
        for key in ("a", "b", "c"):
            L.append(f"| ({key}) | " + " | ".join(cell(pp[key][b]) for b in BUCKETS) + " |")
    L.append("")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default=None, help="読んだ分足の .npz(スクラッチパッド)。あれば読み直さない")
    a = ap.parse_args()

    print("読み込み(段階 G の読み、データの門の下)", flush=True)
    sig, pri, infos, opened_reading = read_minutes(a.cache)
    max_sig, max_pri = int(sig["t"].max()), int(pri["t"].max())
    if max(max_sig, max_pri) + 60 * NS > CUT:
        raise SystemExit("境以降の行がある")

    print("結合・畳み", flush=True)
    sig_bars, price_bars, n_both = join_and_fold(sig, pri, FEET)
    max_bar_end = max(bs[-1][0] + f * 60 for f, bs in sig_bars.items())

    k1 = json.loads(K1_VOL_TERCILES.read_text("utf-8"))

    stage_g_cmp = {}
    for foot in CHECK_FEET:
        stage_g_cmp[f"{foot}|binance"] = compare_with_stage_g(sig_bars[foot], "binance", foot)
        stage_g_cmp[f"{foot}|bitflyer"] = compare_with_stage_g(price_bars[foot], "bitflyer", foot)
    print("  段階 G の畳んだ足と: " + ", ".join(f"{k} {v['identical']}" for k, v in stage_g_cmp.items()), flush=True)

    print("再現の検め", flush=True)
    check = {"stage_g_read": run_check(sig_bars, price_bars, k1, "段階 G の読み")}
    on_grid = (sig["t"] % (60 * NS)) == 0
    sig_v = {k: v[on_grid] for k, v in sig.items()}
    sig_bars_v, price_bars_v, n_both_v = join_and_fold(sig_v, pri, CHECK_FEET)
    check["k1_join_variant"] = run_check(sig_bars_v, price_bars_v, k1, "K1 当時の結合")
    check["k1_join_variant_note"] = (
        "Binance の分の頭に乗らない行(t % 60 秒 != 0)を、分の頭への切り下げの前に落としてから同じ結合・畳み。"
        f"落とした行 {int((~on_grid).sum())}。bitFlyer の分の頭でない行(read_layer の off_minute_rows)は "
        f"{sum(i['off_minute_rows'] for i in infos if 'bitflyer' in i['path'])}。結合後の分 {n_both_v}。")
    mism = {tag: {f: [y for y in map(str, CHECK_YEARS) if not check[tag][f]["stored_edges"][y]["equal"]]
                  for f in map(str, CHECK_FEET)} for tag in ("stage_g_read", "k1_join_variant")}
    mism_re = {f: [y for y in ("2017",) + tuple(map(str, CHECK_YEARS)) + ("2022",)
                   if not check["k1_join_variant"][f]["recomputed_edges"][y]["equal"]] for f in map(str, CHECK_FEET)}
    check["summary"] = {"stored_edges_years_not_equal_2018_2021": mism,
                        "k1_join_variant_recomputed_edges_years_not_equal_2017_2022": mism_re,
                        "pass_stage_g_read": all(not v for v in mism["stage_g_read"].values())}

    print("問い 1", flush=True)
    q1 = {}
    for foot in FEET:
        q1[str(foot)] = {"binance": q1_table(sig_bars[foot]), "bitflyer": q1_table(price_bars[foot])}
        print(f"  {foot}分 完了", flush=True)

    print("問い 2", flush=True)
    q2 = {}
    for foot in FEET:
        q2[str(foot)] = q2_foot(sig_bars[foot], price_bars[foot])
        print(f"  {foot}分 完了(取引 {q2[str(foot)]['n_trades']:,} 件)", flush=True)

    res = {
        "note": ("高ボラの門(DESIGN.md)の問い 1・2 と再現の検め。台本 measure_vol_gate.py の出力。"
                 "経費前。判定・帰無・MDE は作っていない。"),
        "design_md": "docs/RESEARCH/cards/c2_owner_xvenue_wick/vol_gate/DESIGN.md",
        "read": {
            "method": ("scripts/k1_newenv_g_fold.py の read_layer(データ層 bot.bt.data.load、range_ns = "
                       "[年の頭, min(翌年の頭, CUT)))。Binance は synthetic(n_trades == 0)を drop、bitFlyer は "
                       "no_trade(OHLC 全部空)を drop、gap・off_grid は accept。to_minutes で分の頭に切り下げ、"
                       "UTC の分で内部結合、bars_from_bars で両取引所を同じ窓に畳む。足の終わり <= CUT の足だけ。"),
            "cut": iso_s(CUT // NS),
            "inputs": infos,
            "max_event_start_signal": iso_s(max_sig // NS),
            "max_event_start_price": iso_s(max_pri // NS),
            "max_event_end_le_cut": bool(max(max_sig, max_pri) + 60 * NS <= CUT),
            "minutes_both": n_both,
            "max_bar_end": iso_s(max_bar_end),
            "max_bar_end_le_cut": bool(max_bar_end * NS <= CUT),
            "n_bars": {str(f): len(b) for f, b in sig_bars.items()},
            "first_bar": {str(f): iso_s(b[0][0]) for f, b in sig_bars.items()},
            "files_opened_under_data_roots_when_reading": opened_reading,
            "files_opened_under_data_roots_after_reading": [
                q for q in (os.path.relpath(p, REPO) for p in G.GATE.OPENED) if q not in opened_reading],
        },
        "stage_g_fold_compare": stage_g_cmp,
        "check": check,
        "q1_definition": (
            "vol_prev[i] = measure_katsuo_robustness.FootData.vol_prev(足 i−100〜i−1 の |log(close[j]/close[j−1])| × 1e4 の平均)。"
            "vol_next[i] = vol_prev[i+101](足 i+1〜i+100 の同じ量の平均)。足は結合後の足(Binance = 合図の足、bitFlyer = 値段の足)。"
            "年 Y の境目 = 年 Y−1 の全足の vol_prev から measure_katsuo_xvenue.edges_from_vol(1/3・2/3 の線形補間の分位)。"
            "vol_prev と vol_next の両方に同じ境目を当てる(bucket_of: v < q1 低、v < q2 中、それ以外 高)。"
            "2018 の境目は 2017-08-17〜2017-12-31 の足から。vol_prev[i+101] が無い最後の 101 本の足(2023-12-17 の末尾。窓が境 2023-12-18 を越える 100 本と、vol_prev の添字が足りない 1 本)は使っていない(n_no_vol_next)。"
            "順位相関 = scipy.stats.spearmanr(年 Y の足で vol_prev と vol_next の両方に値があるもの)。"),
        "q1_note": (
            "注: 境目を前の暦年で決めるので、三分位に入る足の割合(share_of_bars_by_vol_prev_tercile)は 1/3 にならず、"
            "その年のボラの水準に引きずられる(例: 2021 は全足の 7 割前後が「高」、2018・2022・2023 は 1〜2 割)。"
            "そのため「高→高」などの割合は持続と年の水準のずれが混ざった量で、持続そのものは順位相関の方が素直に表す"
            "(順位相関は年の中の順位だけを見る)。足の窓が重なるので、使った足の数は独立な標本の数より多く見える。区間は出していない。"),
        "q1": q1,
        "q2": {
            "notes": [
                "リードの答え(2026-10-03)に従って段階 G の読みで測った。年は取引の入口の足の年。経費前・建玉 1 単位・約定は bitFlyer の足の終値(段階 G と同じ)。",
                "(a) の境目はこの読みの 2018〜2019 の取引から edges_from_vol で決めた値。K1 の保存値(丸めたもの、vol_terciles.json: edges_bp_own)は 5 分 "
                + f"{k1['feet']['5']['edges_bp_own']}、15 分 {k1['feet']['15']['edges_bp_own']}。30・60 分は K1 に保存値が無い。",
                "(a) の 2017 は境目を決めた 2018〜2019 より前の年なので「先読みあり」(境目に後の年の取引を使っている)。(b) の 2017 は前の年が無いので空欄。",
                "(c) は取引の間(入口の次の足〜決済の足)の bitFlyer の |log| の平均で、境目はその年の取引の (c) の三分位(後でしか分からない上限。門には使えない)。",
                "2017 は K1 当時の結合と大きく違う(段階 G の読みは分の頭に乗らない Binance の行を分の頭に切り下げて残す。2017 にその行が 20,320 行ある)。"
                + "例: 15 分 2017 の高(保存した境目で分けたとき)は段階 G の読み "
                + f"{check['stage_g_read']['15']['stored_edges']['2017']['here']['high']['n']:,} 件、K1 "
                + f"{check['stage_g_read']['15']['stored_edges']['2017']['k1']['high']['n']:,} 件(check.stage_g_read.15.stored_edges.2017)。",
                "2023 は 2023-12-17 まで。",
            ],
            "feet": q2,
        },
    }
    out_json = HERE / "vol_gate.json"
    out_json.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    write_md(res, HERE / "TABLES.md")
    print(f"→ {out_json.relative_to(REPO)} / TABLES.md", flush=True)
    print(json.dumps(check["summary"], ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()

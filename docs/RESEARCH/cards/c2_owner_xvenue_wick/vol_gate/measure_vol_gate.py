#!/usr/bin/env python3
"""高ボラの門(`DESIGN.md`)の問い 1・2 を測る台本(第 2 版の定めで測り直す版)。

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

用語(DESIGN.md 第 2 版): **ヒゲの門** = K1 の合図の門 s19/b24。**ボラの門** = 局所ボラで入るかを決める門(この設計で測るもの)。
この台本の文では「門」だけでは書かない(「データの門」= 段階 G の読み込みの関所 `k1_newenv_g_datagate.py` は別の物)。

第 2 版の「測り直すときの定め」1〜8 の当て方:

- 読み(定め 1): 段階 G の読み(`scripts/k1_newenv_g_fold.py` の `read_layer` / `to_minutes` / `BIN_SPEC` / `BF_SPEC` /
  `CUT` を import。import の時点で段階 G のデータの門が入る)。年ごとに [1 月 1 日, min(翌年 1 月 1 日, 2023-12-18T00:00Z))
  をデータ層の range_ns で読み、UTC の分で内部結合し、両取引所を同じ窓で畳む。5・15 分は段階 G の畳んだ足と行ごとに比べる。
  再現の検め(K1 の vol_terciles.json との照合)は前の版のまま残す。K1 との差の説明の範囲は 2017〜2022(2023 は照合に入れていない)。
- 足(定め 4): 1・3・5・15・30・60 分(K1 の 6 つ)。問い 1・2 とも。
- 設計の取引: `measure_katsuo_effect.signals(flip_body=True)` → `delay_signals` → `simulate(keep="weak", use_invalid=False,
  prices=bitFlyer の終値)`(H1+H2a+H3・弱いだけ、ヒゲの門 s19/b24)。年 = 入口の足の年。保有 = 決済の足 − 入口の足(本)。
- 問い 1(定め 7): vol_prev[i] = `measure_katsuo_robustness.FootData.vol_prev`(足 i−100〜i−1 の |log(close[j]/close[j−1])| × 1e4
  の平均)。vol_next[i] = vol_prev[i+101](足 i+1〜i+100)。境目 = 前の暦年の全足の vol_prev から
  `measure_katsuo_xvenue.edges_from_vol`、両軸に同じ境目(`bucket_of`)。順位相関 = scipy.stats.spearmanr、区間 = その年の足を
  UTC の日の塊で 200 回再抽出(numpy、種 = measure_katsuo_effect.SEED)。
- 問い 2 の分け方(定め 2・3・5):
  - (a) 入口の足の Binance の vol_prev × この読みの 2018〜2019 の取引から edges_from_vol で決めた固定の境目。
    印: 2017 = 先読みあり、2018・2019 = 境目を決めた年。
  - (b) 同じ vol_prev × 前の暦年の取引の vol_prev から決めた境目。2017 は空欄。
  - (c) 定め直した (c): 入口の足の次から固定 100 本の Binance の足の実際のボラ = vol_next[入口](問い 1 と同じ式・同じ取引所・
    同じ窓の長さ)。境目は 2 通り: (c 前年)= 前の暦年の取引の (c) から(2017 は空欄)/ (c 同年)= その年の取引の (c) の三分位
    (後でしか分からない上限の参考。ボラの門には使えない)。
  - 旧 (c)(参考の列): 取引の間の bitFlyer の足(入口+1〜決済)の |log| の平均 × その年の取引の三分位。
  - 取引所(定め 5): vol_prev を bitFlyer の足で測った (a)(b) も並べる(Binance / bitFlyer × 固定 / 前年 = 2 × 2)。
- 分けて出す表(定め 5): 保有の長さ 1 本 / 2〜7 本 / 8〜21 本 / 22 本以上 × 分け方 × 区分の取引数・平均・総損益・
  足 1 本あたりの損益(総損益 ÷ 保有の本数の和)・ボラで割った損益の平均。ボラで割った損益 = 損益 bp ÷ 入口の足の Binance の
  vol_prev(bp)。合図の強さ(H1 で反転した足か = 合図の足で flip_body=True と False のシグナルが違う)・取引の向きで分けた表。
  この 3 つの表は 2018〜2023 を束ねた取引で、区間は出さない。
- 束ねた升(定め 6): 2018〜2023 と、2020・2021 を除いた 2018・2019・2022・2023。各区分の取引数の割合と総損益の割合、
  区間は日の塊(`measure_katsuo_effect.block_bootstrap`、入口の日、200 回)と年の塊(同じ関数に、足の時刻の代わりに
  「年 × 86400」を渡して、塊を年にしたもの)。
- 年ごとの升の区間: 日の塊。升ごとに新しい `random.Random(measure_katsuo_effect.SEED)`。取引数 30 未満の升は区間を出さない
  (K1 の summarize_cell と同じ足切り)。
- 読み方(定め 8)の条件 (i)(ii)(iii) を、(b) について機械的に数えて「成り立つ / 成り立たない」を出す。言葉の判定は書かない。
  条件の数え方は vol_gate.json の `q2.criteria_definition`。

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
FEET = (1, 3, 5, 15, 30, 60)
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




# ---------------------------------------------------------------- 共通

REPS = eff.BOOTSTRAP
Q2_YEARS = tuple(range(2017, 2024))
PERIODS = {"2018_2023": (2018, 2019, 2020, 2021, 2022, 2023),
           "2018_2019_2022_2023": (2018, 2019, 2022, 2023)}
HOLD_BINS = (("1", 1, 1), ("2-7", 2, 7), ("8-21", 8, 21), ("22+", 22, 10 ** 12))
METHODS = {
    "a": ("vp_bin", "fixed", "(a) Binance の vol_prev × 2018〜2019 の取引で決めた固定の境目"),
    "b": ("vp_bin", "prev", "(b) Binance の vol_prev × 前の暦年の取引で決めた境目"),
    "c_prev": ("c_next", "prev", "(c 前年) 入口の次から 100 本の Binance の実際のボラ × 前の暦年の取引で決めた境目"),
    "c_same": ("c_next", "same", "(c 同年) 入口の次から 100 本の Binance の実際のボラ × その年の取引の三分位(上限の参考)"),
    "c_old": ("c_old", "same", "旧 (c)(参考) 取引の間の bitFlyer のボラ × その年の取引の三分位"),
    "a_bf": ("vp_bf", "fixed", "(a bitFlyer) bitFlyer の vol_prev × 2018〜2019 の取引で決めた固定の境目"),
    "b_bf": ("vp_bf", "prev", "(b bitFlyer) bitFlyer の vol_prev × 前の暦年の取引で決めた境目"),
}
SPLIT_METHODS = ("a", "b", "c_prev", "c_same")


def vol_next_of(vp: np.ndarray) -> np.ndarray:
    n = vp.size
    vn = np.full(n, np.nan)
    if n > rb.VOL_WINDOW + 1:
        vn[:n - (rb.VOL_WINDOW + 1)] = vp[rb.VOL_WINDOW + 1:]
    return vn


def rnd(x, d=4):
    return None if x is None or x != x else round(float(x), d)


# ---------------------------------------------------------------- 問い 1

def spearman_ci(a: np.ndarray, b: np.ndarray, days: np.ndarray):
    """日の塊の再抽出(200 回、種固定)で順位相関の 95% 区間。分位は K1 と同じ sorted[int(0.025*(R-1))]。"""
    u, inv = np.unique(days, return_inverse=True)
    inv = inv.ravel()
    order = np.argsort(inv, kind="stable")
    counts = np.bincount(inv)
    starts = np.concatenate(([0], np.cumsum(counts)[:-1]))
    groups = [order[starts[k]:starts[k] + counts[k]] for k in range(u.size)]
    rng = np.random.default_rng(eff.SEED)
    vals = []
    for _ in range(REPS):
        pick = rng.integers(0, u.size, size=u.size)
        idx = np.concatenate([groups[k] for k in pick])
        vals.append(float(spearmanr(a[idx], b[idx]).statistic))
    vals.sort()
    return [round(vals[int(0.025 * (REPS - 1))], 4), round(vals[int(0.975 * (REPS - 1))], 4)]


def q1_table(bars, years=Q1_YEARS):
    fd = rb.FootData(bars)
    vp = fd.vol_prev
    vn = vol_next_of(vp)
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
            "spearman_ci95_day_block": spearman_ci(a, b, fd.day[both]) if a.size > 2 else None,
        }
    return out


# ---------------------------------------------------------------- 問い 2

def trade_records(sig_bars, price_bars):
    sg_flip = eff.signals(sig_bars, GATE_S, GATE_B, flip_body=True)        # H1
    sg_raw = eff.signals(sig_bars, GATE_S, GATE_B, flip_body=False)        # 反転の有無を見るためだけ
    sg = eff.delay_signals(sg_flip)                                         # H3
    pc = [b[4] for b in price_bars]
    trades = eff.simulate(sig_bars, sg, "weak", use_invalid=False, prices=pc)  # 弱いだけ、H2a
    fd_s, fd_p = rb.FootData(sig_bars), rb.FootData(price_bars)
    vn = vol_next_of(fd_s.vol_prev)
    recs = []
    for tr in trades:
        i, r, h, _w = tr
        old = [abs(math.log(pc[j] / pc[j - 1])) * 1e4 for j in range(i + 1, i + h + 1)]
        vp = float(fd_s.vol_prev[i])
        recs.append({"tr": tr, "i": i, "y": int(fd_s.year[i]), "r": r, "h": h,
                     "vp_bin": vp, "vp_bf": float(fd_p.vol_prev[i]), "c_next": float(vn[i]),
                     "c_old": sum(old) / len(old) if old else float("nan"),
                     "rn": r / vp if vp == vp and vp > 0 else float("nan"),
                     "flipped": sg_flip[i - 1][0] != sg_raw[i - 1][0],
                     "dir": "long" if sg[i][0] > 0 else "short"})
    day_ts = [b[0] for b in sig_bars]
    year_ts = (fd_s.year * 86400).tolist()   # block_bootstrap は ts // 86400 を塊にする → 塊 = 年
    return recs, day_ts, year_ts


def stats(sub, day_ts, year_ts=None, ci=True):
    n = len(sub)
    out = {"n": n, "mean_bp": None, "total_bp": 0.0, "ci95_day": None}
    if n == 0:
        return out
    rs = [t["r"] for t in sub]
    out["mean_bp"] = round(sum(rs) / n, 3)
    out["total_bp"] = round(sum(rs), 1)
    nn = [t for t in sub if t["rn"] == t["rn"]]
    out["n_norm"] = len(nn)
    out["mean_norm"] = round(sum(t["rn"] for t in nn) / len(nn), 5) if nn else None
    if ci and n >= 30:
        trs = [t["tr"] for t in sub]
        lo, hi = eff.block_bootstrap(trs, day_ts, random.Random(eff.SEED))
        out["ci95_day"] = [round(lo, 3), round(hi, 3)]
        if len(nn) >= 30:
            trn = [(t["i"], t["rn"], t["h"], t["tr"][3]) for t in nn]
            lo, hi = eff.block_bootstrap(trn, day_ts, random.Random(eff.SEED))
            out["ci95_day_norm"] = [round(lo, 5), round(hi, 5)]
        if year_ts is not None:
            lo, hi = eff.block_bootstrap(trs, year_ts, random.Random(eff.SEED))
            out["ci95_year"] = [round(lo, 3), round(hi, 3)]
    return out


def assign_buckets(recs):
    """分け方ごとに、年ごとの境目と各取引の区分を決める。"""
    edges = {}
    for m, (val, how, _label) in METHODS.items():
        per = {}
        fixed = None
        if how == "fixed":
            fixed = xv.edges_from_vol([t[val] for t in recs
                                       if xv.VOL_TRAIN_START_YEAR <= t["y"] <= xv.VOL_TRAIN_END_YEAR])
        for y in Q2_YEARS:
            if how == "fixed":
                per[y] = fixed
            elif how == "prev":
                per[y] = xv.edges_from_vol([t[val] for t in recs if t["y"] == y - 1])
            else:
                per[y] = xv.edges_from_vol([t[val] for t in recs if t["y"] == y])
        edges[m] = per
        for t in recs:
            e = per.get(t["y"])
            t["bk_" + m] = xv.bucket_of(t[val], e) if e else None
    return edges


def mark_of(m, y):
    how = METHODS[m][1]
    if how == "fixed":
        if y < xv.VOL_TRAIN_START_YEAR:
            return "先読みあり"
        if y <= xv.VOL_TRAIN_END_YEAR:
            return "境目を決めた年"
    if how == "same":
        return "その年の値で切った"
    return ""


def spearman_pairs(recs, pairs):
    out = {}
    for x, z in pairs:
        a = np.array([t[x] if x != "abs_r" else abs(t["r"]) for t in recs], dtype=float)
        b = np.array([t[z] if z != "abs_r" else abs(t["r"]) for t in recs], dtype=float)
        ok = ~np.isnan(a) & ~np.isnan(b)
        out[f"{x}~{z}"] = {"n": int(ok.sum()), "rho": rnd(spearmanr(a[ok], b[ok]).statistic)}
    return out


def q2_foot(sig_bars, price_bars):
    recs, day_ts, year_ts = trade_records(sig_bars, price_bars)
    edges = assign_buckets(recs)
    out = {"n_trades": len(recs),
           "n_flipped": sum(1 for t in recs if t["flipped"]),
           "edges_fixed_bp": {m: [rnd(edges[m][2018][0]), rnd(edges[m][2018][1])] for m in ("a", "a_bf")},
           "years": {}, "pooled": {}, "hold": {}, "splits": {}}
    # 年ごと
    for y in Q2_YEARS:
        ys = [t for t in recs if t["y"] == y]
        yr = {"all": stats(ys, day_ts)}
        for m in METHODS:
            e = edges[m][y]
            d = {"edges_bp": None if e is None else [rnd(e[0]), rnd(e[1])], "mark": mark_of(m, y)}
            if e is None:
                d["blank"] = True
            else:
                for bk in BUCKETS:
                    sub = [t for t in ys if t["bk_" + m] == bk]
                    d[bk] = stats(sub, day_ts)
                    d[bk]["share_n"] = round(len(sub) / len(ys), 4) if ys else None
                d["n_unbucketed"] = sum(1 for t in ys if t["bk_" + m] is None)
            yr[m] = d
        out["years"][str(y)] = yr
    # 束ねた升
    for pname, pyears in PERIODS.items():
        ps = [t for t in recs if t["y"] in pyears]
        allc = stats(ps, day_ts, year_ts)
        p = {"years": list(pyears), "all": allc}
        for m in METHODS:
            p[m] = {}
            for bk in BUCKETS:
                sub = [t for t in ps if t["bk_" + m] == bk]
                c = stats(sub, day_ts, year_ts)
                c["share_n"] = round(len(sub) / len(ps), 4) if ps else None
                c["share_total"] = round(c["total_bp"] / allc["total_bp"], 4) if allc["total_bp"] else None
                p[m][bk] = c
            p[m]["n_unbucketed"] = sum(1 for t in ps if t["bk_" + m] is None)
        out["pooled"][pname] = p
    # 保有の長さ(2018〜2023 を束ねる。区間なし)
    ps = [t for t in recs if t["y"] in PERIODS["2018_2023"]]

    def light(sub):
        c = stats(sub, day_ts, ci=False)
        hs = sum(t["h"] for t in sub)
        c["bars_held"] = hs
        c["per_bar_bp"] = round(c["total_bp"] / hs, 4) if hs else None
        return c
    for hname, lo, hi in HOLD_BINS:
        hsub = [t for t in ps if lo <= t["h"] <= hi]
        d = {"all": light(hsub), "share_n_of_period": round(len(hsub) / len(ps), 4) if ps else None}
        for m in METHODS:
            d[m] = {bk: light([t for t in hsub if t["bk_" + m] == bk]) for bk in BUCKETS}
        out["hold"][hname] = d
    # 合図の強さ・向き(2018〜2023 を束ねる。区間なし)
    for sname, key, vals in (("strength", "flipped", (True, False)), ("direction", "dir", ("long", "short"))):
        d = {}
        for v in vals:
            vsub = [t for t in ps if t[key] == v]
            dv = {"all": light(vsub)}
            for m in SPLIT_METHODS:
                dv[m] = {bk: light([t for t in vsub if t["bk_" + m] == bk]) for bk in BUCKETS}
            d[str(v)] = dv
        out["splits"][sname] = d
    out["spearman_2018_2023"] = spearman_pairs(ps, (("vp_bin", "c_next"), ("vp_bin", "h"), ("c_next", "h"),
                                                    ("c_old", "h"), ("vp_bin", "vp_bf"), ("vp_bin", "abs_r"),
                                                    ("c_next", "abs_r"), ("c_old", "abs_r")))
    out["hold_quantiles_2018_2023"] = {f"p{q}": int(np.percentile([t["h"] for t in ps], q, method="lower"))
                                       for q in (0, 10, 25, 50, 75, 90, 100)} if ps else None
    out["criteria"] = criteria(out)
    return out


CRITERIA_DEFINITION = (
    "DESIGN.md 第 2 版 8 の条件を (b)(Binance の vol_prev × 前の暦年の境目)について機械的に数えたもの。"
    "条件 A(年 Y)= (b) の高い区分の平均 > その年の全取引の平均 かつ > (b) の低い区分の平均(どれかの升が空なら成り立たない)。"
    "(i) = 2018〜2023 の 6 年のうち条件 A(損益 bp)が成り立つ年が 4 年以上。"
    "(ii) = 条件 A をボラで割った損益(r ÷ 入口の Binance の vol_prev)の平均で数えて、6 年のうち 4 年以上"
    "(参考に、2018〜2023 を束ねた升で条件 A が成り立つかも並べる)。"
    "(iii 日)・(iii 年) = 2020・2021 を除いた束ね(2018・2019・2022・2023)で条件 A が成り立ち、かつ (b) の高い区分の"
    "95% 区間(日の塊 / 年の塊)の下端 > 0。"
    "(基) = 2018〜2023 を束ねた升で条件 A(損益 bp)が成り立つか(第 2 版 8 の本文の「高い区分が全取引の平均と低い区分の平均の"
    "両方を上回り」)。")


def criteria(fq):
    def cond(cells, key):
        hi, lo, al = cells["b"]["high"].get(key), cells["b"]["low"].get(key), cells["all"].get(key)
        if hi is None or lo is None or al is None:
            return False
        return hi > al and hi > lo
    yrs = PERIODS["2018_2023"]
    ok_bp = [y for y in yrs if not fq["years"][str(y)]["b"].get("blank") and cond(fq["years"][str(y)], "mean_bp")]
    ok_nm = [y for y in yrs if not fq["years"][str(y)]["b"].get("blank") and cond(fq["years"][str(y)], "mean_norm")]
    p_all, p_ex = fq["pooled"]["2018_2023"], fq["pooled"]["2018_2019_2022_2023"]
    hi_ex = p_ex["b"]["high"]
    rows = [
        {"id": "base", "name": "(基) 2018〜2023 を束ねた升で条件 A", "value": cond(p_all, "mean_bp"),
         "detail": f"高 {p_all['b']['high']['mean_bp']} / 全 {p_all['all']['mean_bp']} / 低 {p_all['b']['low']['mean_bp']}"},
        {"id": "i", "name": "(i) 条件 A が 6 年のうち 4 年以上", "value": len(ok_bp) >= 4,
         "detail": f"{len(ok_bp)} 年 {ok_bp}"},
        {"id": "ii", "name": "(ii) ボラで割った損益で条件 A が 6 年のうち 4 年以上", "value": len(ok_nm) >= 4,
         "detail": f"{len(ok_nm)} 年 {ok_nm}。束ねた升(2018〜2023)では {cond(p_all, 'mean_norm')}"},
        {"id": "iii_day", "name": "(iii 日) 2020・2021 を除いた束ねで条件 A、かつ高の区間(日の塊)の下端 > 0",
         "value": bool(cond(p_ex, "mean_bp") and hi_ex.get("ci95_day") and hi_ex["ci95_day"][0] > 0),
         "detail": f"条件 A {cond(p_ex, 'mean_bp')}、高 {hi_ex['mean_bp']} 区間 {hi_ex.get('ci95_day')}"},
        {"id": "iii_year", "name": "(iii 年) 同、高の区間(年の塊)の下端 > 0",
         "value": bool(cond(p_ex, "mean_bp") and hi_ex.get("ci95_year") and hi_ex["ci95_year"][0] > 0),
         "detail": f"条件 A {cond(p_ex, 'mean_bp')}、高 {hi_ex['mean_bp']} 区間 {hi_ex.get('ci95_year')}"},
    ]
    return rows


# ---------------------------------------------------------------- TABLES.md

def fmt(x, d=2):
    if x is None:
        return "—"
    return f"{x:+.{d}f}" if isinstance(x, float) else f"{x:,}"


def ci_s(c, key="ci95_day", d=2):
    v = c.get(key)
    return f" [{v[0]:+.{d}f}, {v[1]:+.{d}f}]" if v else ""


def cell_y(c):
    """年ごとの升: 取引数(割合)/ 平均 bp [日の区間] / 総損益 / ボラで割った平均。"""
    if c["n"] == 0:
        return "0"
    sh = f"({c['share_n'] * 100:.0f}%)" if c.get("share_n") is not None else ""
    nm = f" / {c['mean_norm']:+.3f}" if c.get("mean_norm") is not None else ""
    return f"{c['n']:,}{sh} / {c['mean_bp']:+.2f}{ci_s(c)} / {c['total_bp']:+,.0f}{nm}"


def cell_light(c):
    if c["n"] == 0:
        return "0"
    pb = f" / {c['per_bar_bp']:+.3f}" if c.get("per_bar_bp") is not None else ""
    nm = f" / {c['mean_norm']:+.3f}" if c.get("mean_norm") is not None else ""
    return f"{c['n']:,} / {c['mean_bp']:+.2f} / {c['total_bp']:+,.0f}{pb}{nm}"


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
    L.append(f"- データの門が開くのを許したデータの置き場のファイル: 読み込みの段 {len(r['files_opened_under_data_roots_when_reading'])} 件"
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
    L.append(f"機械の照合の要約: {res['check']['summary']}")
    L.append("")
    L.append(res["check_scope_note"])
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
            L.append("| 年 | 境目 bp(前の年) | 使った足 | 順位相関 [日の塊の区間] | 高→高 | 高→中 | 高→低 | 低→低 | 低→高 | vol_prev の三分位の割合(低/中/高) |")
            L.append("|---|---|---|---|---|---|---|---|---|---|")
            for y, t in vv.items():
                s = t["row_shares"]
                e = t["edges_bp_from_prev_year"]
                ps = t["share_of_bars_by_vol_prev_tercile"]
                ci = t["spearman_ci95_day_block"]
                L.append(f"| {y} | {e[0]:.2f} / {e[1]:.2f} | {t['n_bars_used']:,} | {t['spearman_rho']:.4f} [{ci[0]:.4f}, {ci[1]:.4f}] | "
                         + " | ".join("—" if v is None else f"{v:.4f}" for v in (
                             s["high"]["high"], s["high"]["mid"], s["high"]["low"], s["low"]["low"], s["low"]["high"]))
                         + f" | {ps['low']:.4f} / {ps['mid']:.4f} / {ps['high']:.4f} |")
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
    q2 = res["q2"]
    L.append("## 4. 問い 2 — 設計の取引をボラで分けた成績(`vol_gate.json: q2`)")
    L.append("")
    for line in q2["notes"]:
        L.append(f"- {line}")
    L.append("")
    L.append("### 4.0 第 2 版 8 の条件を機械的に数えたもの(`q2.feet.<足>.criteria`)")
    L.append("")
    L.append(q2["criteria_definition"])
    L.append("")
    ids = [r["id"] for r in next(iter(q2["feet"].values()))["criteria"]]
    names = {r["id"]: r["name"] for r in next(iter(q2["feet"].values()))["criteria"]}
    L.append("| 条件 | " + " | ".join(f"{f} 分" for f in q2["feet"]) + " |")
    L.append("|---|" + "---|" * len(q2["feet"]))
    for cid in ids:
        row = []
        for f, fv in q2["feet"].items():
            r = next(x for x in fv["criteria"] if x["id"] == cid)
            row.append(("成り立つ" if r["value"] else "成り立たない") + f"({r['detail']})")
        L.append(f"| {names[cid]} | " + " | ".join(row) + " |")
    for foot, fv in q2["feet"].items():
        L.append("")
        L.append(f"### 足 {foot} 分(取引 {fv['n_trades']:,} 件、うち H1 で反転した合図 {fv['n_flipped']:,} 件)")
        L.append("")
        L.append(f"固定の境目(2018〜2019 の取引から): (a) {fv['edges_fixed_bp']['a']}、(a bitFlyer) {fv['edges_fixed_bp']['a_bf']}。"
                 f"保有の本数の分位(2018〜2023): {fv['hold_quantiles_2018_2023']}。")
        L.append("")
        L.append("順位相関(2018〜2023 の取引、区間なし。`spearman_2018_2023`): " + "、".join(
            f"{k} {v['rho']}(n {v['n']:,})" for k, v in fv["spearman_2018_2023"].items()))
        L.append("")
        L.append("#### 年ごと(各升 = 取引数(その年の取引に対する割合)/ 平均 bp [日の塊の区間] / 総損益 bp / ボラで割った損益の平均)")
        L.append("")
        L.append("| 年 | 全取引 |")
        L.append("|---|---|")
        for y, yr in fv["years"].items():
            L.append(f"| {y} | {cell_y(yr['all'])} |")
        for m, (_v, _h, label) in METHODS.items():
            L.append("")
            L.append(label + ":")
            L.append("")
            L.append("| 年 | 印 | 境目 | 低 | 中 | 高 | 分けられない |")
            L.append("|---|---|---|---|---|---|---|")
            for y, yr in fv["years"].items():
                d = yr[m]
                if d.get("blank"):
                    L.append(f"| {y} | 空欄(前の年が無い) | — | — | — | — | — |")
                    continue
                e = d["edges_bp"]
                L.append(f"| {y} | {d['mark']} | {e[0]:.2f} / {e[1]:.2f} | "
                         + " | ".join(cell_y(d[b]) for b in BUCKETS) + f" | {d['n_unbucketed']:,} |")
        for pname, p in fv["pooled"].items():
            L.append("")
            L.append(f"#### 束ねた升 {pname}(年 {p['years']}。三分位は年ごとの境目で分けたものを束ねた)")
            L.append("")
            a = p["all"]
            L.append(f"全取引: {a['n']:,} / 平均 {a['mean_bp']:+.2f} [日{ci_s(a)}] [年{ci_s(a, 'ci95_year')}] / 総損益 {a['total_bp']:+,.0f}"
                     f" / ボラで割った平均 {fmt(a.get('mean_norm'), 3)}{ci_s(a, 'ci95_day_norm', 3)}")
            L.append("")
            L.append("| 分け方 | 区分 | 取引数(割合) | 総損益(割合) | 平均 bp [日の塊] [年の塊] | ボラで割った平均 [日の塊] |")
            L.append("|---|---|---|---|---|---|")
            for m, (_v, _h, label) in METHODS.items():
                for b in BUCKETS:
                    c = p[m][b]
                    if c["n"] == 0:
                        L.append(f"| {m} | {b} | 0 | — | — | — |")
                        continue
                    stt = "—" if c["share_total"] is None else f"{c['share_total'] * 100:.0f}%"
                    L.append(f"| {m} | {b} | {c['n']:,}({c['share_n'] * 100:.1f}%) | {c['total_bp']:+,.0f}({stt}) | "
                             f"{c['mean_bp']:+.2f}{ci_s(c)}{ci_s(c, 'ci95_year')} | {fmt(c.get('mean_norm'), 3)}{ci_s(c, 'ci95_day_norm', 3)} |")
        L.append("")
        L.append("#### 保有の長さで分けた表(2018〜2023 を束ねる。各升 = 取引数 / 平均 bp / 総損益 / 足 1 本あたりの損益 bp / ボラで割った平均。区間なし)")
        L.append("")
        for m in METHODS:
            L.append(f"{METHODS[m][2]}:")
            L.append("")
            L.append("| 保有 | 全取引(期間に対する割合) | 低 | 中 | 高 |")
            L.append("|---|---|---|---|---|")
            for hname, d in fv["hold"].items():
                L.append(f"| {hname} 本 | {cell_light(d['all'])}({d['share_n_of_period'] * 100:.1f}%) | "
                         + " | ".join(cell_light(d[m][b]) for b in BUCKETS) + " |")
            L.append("")
        L.append("#### 合図の強さ・向きで分けた表(2018〜2023 を束ねる。各升は保有の表と同じ。区間なし)")
        L.append("")
        for sname, title, lab in (("strength", "合図の強さ", {"True": "H1 で反転した合図", "False": "元から弱い合図"}),
                                  ("direction", "取引の向き", {"long": "買い", "short": "売り"})):
            L.append(f"{title}:")
            L.append("")
            L.append("| 区分 | 分け方 | 全取引 | 低 | 中 | 高 |")
            L.append("|---|---|---|---|---|---|")
            for v, dv in fv["splits"][sname].items():
                for m in SPLIT_METHODS:
                    L.append(f"| {lab[v]} | {m} | {cell_light(dv['all'])} | " + " | ".join(cell_light(dv[m][b]) for b in BUCKETS) + " |")
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
    del sig_v
    check["k1_join_variant"] = run_check(sig_bars_v, price_bars_v, k1, "K1 当時の結合")
    del sig_bars_v, price_bars_v
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
    del sig, pri

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

    s15 = check["stage_g_read"]["15"]["stored_edges"]["2017"]
    res = {
        "note": ("高ボラの門(DESIGN.md)の問い 1・2 と再現の検め。DESIGN.md 第 2 版の「測り直すときの定め」で測り直した版。"
                 "台本 measure_vol_gate.py の出力。経費前。言葉の判定・帰無・MDE は作っていない。"),
        "design_md": "docs/RESEARCH/cards/c2_owner_xvenue_wick/vol_gate/DESIGN.md",
        "terms": "ヒゲの門 = K1 の合図の門 s19/b24。ボラの門 = 局所ボラで入るかを決める門(この設計で測るもの)。",
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
        "check_scope_note": (
            "K1 との差の説明の範囲は 2017〜2022。K1 当時の結合の変種と丸めない境目で 2017〜2022 が 5・15 分とも一致した"
            "(check.summary.k1_join_variant_recomputed_edges_years_not_equal_2017_2022)。2023 は照合に入れていない"
            "(K1 の vol_terciles.json の 2023 は 2023-12-31 まで、この読みは 2023-12-17 まで)。段階 G の読みの K1 との差は、"
            "保存した境目の丸め(5 分の 2019・2021、2 件ずつ)と、分の頭に乗らない Binance の行の扱い(DIFF.md §3 D-1。2018 と、"
            "DIFF.md では比べていない 2017)。2017 の例: 15 分の高(保存した境目)は段階 G の読み "
            f"{s15['here']['high']['n']:,} 件 / {s15['here']['high']['mean_bp']:+.3f} bp、K1 {s15['k1']['high']['n']:,} 件 / "
            f"{s15['k1']['high']['mean_bp']:+.3f} bp。機械の照合 pass_stage_g_read は False のまま、リードの答え(段階 G の読みで測る)に従って測った。"),
        "q1_definition": (
            "vol_prev[i] = measure_katsuo_robustness.FootData.vol_prev(足 i−100〜i−1 の |log(close[j]/close[j−1])| × 1e4 の平均)。"
            "vol_next[i] = vol_prev[i+101](足 i+1〜i+100 の同じ量の平均)。足は結合後の足(Binance = 合図の足、bitFlyer = 値段の足)。"
            "年 Y の境目 = 年 Y−1 の全足の vol_prev から measure_katsuo_xvenue.edges_from_vol(1/3・2/3 の線形補間の分位)。"
            "vol_prev と vol_next の両方に同じ境目を当てる(bucket_of: v < q1 低、v < q2 中、それ以外 高)。"
            "2018 の境目は 2017-08-17〜2017-12-31 の足から。vol_prev[i+101] が無い最後の 101 本の足(2023-12-17 の末尾。窓が境 "
            "2023-12-18 を越える 100 本と、vol_prev の添字が足りない 1 本)は使っていない(n_no_vol_next)。"
            "順位相関 = scipy.stats.spearmanr(年 Y の足で vol_prev と vol_next の両方に値があるもの)。区間 = 年 Y の足を UTC の日の塊で "
            "200 回再抽出(numpy default_rng、種 measure_katsuo_effect.SEED)、分位は sorted[int(0.025×199)]・sorted[int(0.975×199)]。"),
        "q1_note": (
            "注: 境目を前の暦年で決めるので、三分位に入る足の割合(share_of_bars_by_vol_prev_tercile)は 1/3 にならず、"
            "その年のボラの水準に引きずられる(例: 2021 は全足の 7 割前後が「高」)。"
            "そのため「高→高」などの割合は持続と年の水準のずれが混ざった量で、持続そのものは順位相関の方が素直に表す"
            "(順位相関は年の中の順位だけを見る)。順位相関は年ごとの値をそのまま並べる(単調でない)。"
            "足の窓が重なるので、日の塊の区間は窓の重なりの分だけ狭く出うる。"),
        "q1": q1,
        "q2": {
            "notes": [
                "DESIGN.md 第 2 版の定め 1〜8 で測った。読みは段階 G の読み。年は取引の入口の足の年。経費前・建玉 1 単位・"
                "約定は bitFlyer の足の終値(段階 G と同じ)。指値は見ていない。",
                "「三分位」= 境目で 3 つに分けた区分。(b)・(c 前年)・(a) では、その年に入る割合が 1/3 にならない。各升に割合を並べた。",
                "(a) の境目はこの読みの 2018〜2019 の取引から edges_from_vol で決めた値。K1 の保存値(丸めたもの、"
                f"vol_terciles.json: edges_bp_own)は 5 分 {k1['feet']['5']['edges_bp_own']}、15 分 {k1['feet']['15']['edges_bp_own']}。"
                "1・3・30・60 分は K1 に保存値が無い。",
                "印: (a)・(a bitFlyer) の 2017 = 先読みあり、2018・2019 = 境目を決めた年(in-sample)。(b)・(c 前年)・(b bitFlyer) の "
                "2017 = 空欄。(c 同年)・旧 (c) = その年の値で切った(後でしか分からない。ボラの門には使えない)。",
                "(c) は定め直した: 入口の足の次から固定 100 本の Binance の足の実際のボラ(問い 1 の vol_next と同じ)。保有の長さと"
                "取引所を (a)(b) とそろえた。旧 (c)(取引の間の bitFlyer のボラ)は参考の列。",
                "ボラで割った損益 = 損益 bp ÷ 入口の足の Binance の vol_prev(bp)。単位は無い。",
                "K1 の設計そのもの(ヒゲの門 s19/b24 を含む)は 2017〜2026 の Binance を見て選んだ(in-sample)。2018〜2023 の束ねは"
                "新しい期間に対する検証ではない。満たしても「K1 の期間の中で前もって分けられた」までしか言わない(DESIGN.md 第 2 版 8)。",
                "2023 は 2023-12-17 まで。2017 は K1 当時の結合と大きく違う年(§2 の注)。",
            ],
            "criteria_definition": CRITERIA_DEFINITION,
            "methods": {m: v[2] for m, v in METHODS.items()},
            "hold_bins": [h[0] for h in HOLD_BINS],
            "feet": q2,
        },
    }
    out_json = HERE / "vol_gate.json"
    out_json.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    write_md(res, HERE / "TABLES.md")
    print(f"→ {out_json} / {HERE / 'TABLES.md'}", flush=True)
    print(json.dumps({f: [(r["id"], r["value"]) for r in v["criteria"]] for f, v in q2.items()}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()

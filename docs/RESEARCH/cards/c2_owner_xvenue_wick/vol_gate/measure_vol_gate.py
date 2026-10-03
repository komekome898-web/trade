#!/usr/bin/env python3
"""高ボラの門(`DESIGN.md`)の問い 1・2 を測る台本(第 2 版の定めに、第 3 版の 1〜4 と、関門 ② の 3 回目を受けた第 4 版の計算を足した版)。

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
  vol_prev(bp)。合図の強さ(H1 で反転した足か = 合図の足で flip_body=True と False のシグナルが違う)・取引の向き・
  時間帯(入口の足の UTC 0〜5・6〜11・12〜17・18〜23 時)で分けた表。この表は 2018〜2023 を束ねた取引で、区間は出さない。
- 束ねた升(定め 6): 2018〜2023 と、2020・2021 を除いた 2018・2019・2022・2023。各区分の取引数の割合と総損益の割合、
  区間は日の塊と年の塊。
- 区間(監査の 2 回目 9): `measure_katsuo_robustness.np_boot`(塊ごとの (合計, 件数) を畳んで塊を復元抽出、2000 回、
  種 = 升の名前の sha256)。塊は入口の日、または入口の年。取引数 30 未満の升は区間を出さない(K1 の summarize_cell と同じ足切り)。
  (b) の束ねた升には、種を変えて 5 回再抽出した端の範囲(端の揺れ)と、標準誤差・最小検出差((1.96 + 0.84) × 標準誤差)を付ける。
  問い 1 の順位相関の区間は 200 回のまま(条件の数えに使わない)。
- 第 3 版(DESIGN.md、測った後・監査の後に足した計算)の 1〜4:
  1. 第 2 版 8 の (ii) の数え方 2 通り(6 年のうち 4 年以上 / 束ねた升)×(iii) の区間 2 通り(日の塊 / 年の塊)の成否を全部並べる。
  2. 割る量 4 通り: v1 = mean(r ÷ 入口の vol_prev)、v2 = mean(r ÷ その年の全取引の vol_prev の平均)、
     v3 = Σr ÷ Σvol_prev、v4 = median(r ÷ 入口の vol_prev)。(ii) を版ごとに数える。
  3. 保有の構成をそろえた比べ: 高と低の区分の、保有の層の内の平均を、相手の層の構成で重み付け直す。同じ形で時間帯の層でも出す。
  4. 無作為の時刻の入りの対照: 同じ足・同じ年・同じ (b) 区分の足のうち、遅らせた合図が 0 の足を無作為に選び(1 件あたり 10 回、
     種 = 足の名前の sha256)、元の取引と同じ向き・同じ保有の本数で bitFlyer の終値で入って出る。逆向きの入りはその符号違い。
- 第 4 版(関門 ② の 3 回目を受けて足した計算。測った後・監査の後):
  判定の目標の差(高 − 低、高 − 全)の日の塊の区間と標準誤差・最小検出差(`diff_boot`、3 つの期間・6 つの足に同じ規則)/
  (iii) を主の種と種を変えた 5 回で数えた成否と「前もって分けられた」の数(全部 / v2 の (ii-年) を除く / (iii-年) を除く / 両方)/
  2023 年も除いた束ね 2018・2019・2022 / 足ごとの保有の分位(10・50・75%)の区切りで構成をそろえた比べ /
  (高の 実際 − 対照)−(低の 実際 − 対照)の区間 / (c 同年) の高 − 低の区間 / 割らない bp の中央値。
- 読み方(定め 8)の条件を、(b) について機械的に数えて「前もって分けられた / 分けられたと言えない」(DESIGN 第 3 版 5 の 2 語)を
  読みごとに出す。条件の数え方は vol_gate.json の `q2.criteria_definition`。

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
ASSUMPTIONS = {   # 新しく置いた値の出所(監査の 3 回目 14)
    "Z_MDE": "作業者の仮定: 最小検出差の両側 5%・検出力 80% は慣例の値。一次資料・実測の根拠は無い",
    "CTRL_DRAWS": "作業者の仮定: 無作為の対照を 1 件あたり 10 回抽出。計算量と平均のばらつきの釣り合いで決めた。実測の根拠は無い",
    "HOLD_BINS": "リードの仮定: DESIGN 第 2 版 5 の区切り 1 / 2〜7 / 8〜21 / 22 本以上(5 分の保有の 10・25・50・75% 点 1・3・7・21 から丸めた)。他の足にも同じ区切りを当てたのは第 2 版の定めのとおり",
    "HOLD_BINS_FOOT": "作業者の仮定: 第 4 版で足した、足ごとの保有の 10・50・75% 点の区切り(リードの仮定 HOLD_BINS の作り方を足ごとに当てたもの)",
    "HOUR6": "作業者の仮定: DESIGN 第 3 版 4 の「UTC の時(または 6 時間の塊)」のうち 6 時間の塊を選んだ。1 時間の層は層ごとの件数が少なくなるため",
    "BOOT_REPS": "リードの仮定: 監査の 2 回目 9 を受けた委任文の「再抽出を 2000 回に」",
    "WOBBLE_SEEDS": "リードの仮定: 同じ委任文の「種を変えて 5 回」",
    "MIN_N": "既存の値: K1 の summarize_cell の 30 件の足切り",
}
Q2_YEARS = tuple(range(2017, 2024))
PERIODS = {"2018_2023": (2018, 2019, 2020, 2021, 2022, 2023),
           "2018_2019_2022_2023": (2018, 2019, 2022, 2023),
           "2018_2019_2022": (2018, 2019, 2022)}   # 第 4 版: 2023 年(5 分の (b) 高 n=60)も除いた版(監査の 3 回目 8)
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

BOOT_REPS = 2000          # 監査の 2 回目 9: 再抽出を 2000 回に(第 2 版は 200 回)
WOBBLE_SEEDS = 5          # 端の揺れ: 種を変えて 5 回
MIN_N = 30                # K1 の summarize_cell と同じ足切り
Z_MDE = 1.959964 + 0.841621   # 両側 5%・検出力 80% の最小検出差 = (z_0.975 + z_0.80) × 標準誤差
CTRL_DRAWS = 10           # 無作為の時刻の入り: 取引 1 件あたりの抽出数
VERSIONS = ("v1", "v2", "v3", "v4")
VERSION_LABEL = {
    "v1": "v1 = 比の平均 mean(r ÷ 入口の vol_prev)(第 2 版)",
    "v2": "v2 = 比の平均 mean(r ÷ その年の全取引の vol_prev の平均)",
    "v3": "v3 = 区分の合計 ÷ 区分の vol_prev の合計 Σr ÷ Σvol_prev",
    "v4": "v4 = 比の中央値 median(r ÷ 入口の vol_prev)",
}
STD_METHODS = ("a", "b", "c_prev", "c_same")


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
        recs.append({"tr": tr, "i": i, "y": int(fd_s.year[i]), "day": int(fd_s.day[i]), "r": r, "h": h,
                     "hour6": int(fd_s.hour[i]) // 6,
                     "vp_bin": vp, "vp_bf": float(fd_p.vol_prev[i]), "c_next": float(vn[i]),
                     "c_old": sum(old) / len(old) if old else float("nan"),
                     "rn": r / vp if vp == vp and vp > 0 else float("nan"),
                     "flipped": sg_flip[i - 1][0] != sg_raw[i - 1][0],
                     "dir": "long" if sg[i][0] > 0 else "short", "sgn": 1 if sg[i][0] > 0 else -1})
    # v2 の分母: その年の全取引の vol_prev の平均
    mvp = {}
    for y in set(t["y"] for t in recs):
        v = [t["vp_bin"] for t in recs if t["y"] == y and t["vp_bin"] == t["vp_bin"]]
        mvp[y] = sum(v) / len(v) if v else float("nan")
    for t in recs:
        m = mvp[t["y"]]
        t["rn2"] = t["r"] / m if m == m and m > 0 else float("nan")
    aux = {"fd": fd_s, "pc": np.asarray(pc, dtype=np.float64), "sg_delayed": np.array([s[0] for s in sg]),
           "mean_vp_year": {str(y): rnd(v) for y, v in sorted(mvp.items())}}
    return recs, aux


def boot(vals, keys, name, reps=BOOT_REPS):
    """塊の再抽出(measure_katsuo_robustness.np_boot、種 = 升の名前の sha256)。"""
    if len(vals) < MIN_N:
        return None
    _u, inv = np.unique(np.asarray(keys), return_inverse=True)
    inv = inv.ravel()
    bsum = np.bincount(inv, weights=np.asarray(vals, dtype=np.float64))
    bn = np.bincount(inv).astype(np.float64)
    lo, hi = rb.np_boot(bsum, bn, name, reps)
    return None if lo is None or hi is None else [round(lo, 3), round(hi, 3)]


def boot_se(vals, keys, name, reps=BOOT_REPS):
    """同じ塊の再抽出の平均の標準偏差(最小検出差に使う)。"""
    if len(vals) < MIN_N:
        return None
    _u, inv = np.unique(np.asarray(keys), return_inverse=True)
    inv = inv.ravel()
    bsum = np.bincount(inv, weights=np.asarray(vals, dtype=np.float64))
    bn = np.bincount(inv).astype(np.float64)
    k = bsum.size
    rng = np.random.default_rng(rb.seed_of(name + "|se"))
    idx = rng.integers(0, k, size=(reps, k))
    means = bsum[idx].sum(axis=1) / bn[idx].sum(axis=1)
    return round(float(means.std(ddof=1)), 4)


def wobble(vals, keys, name):
    """種を変えて 5 回再抽出したときの下端・上端の範囲。"""
    res = [boot(vals, keys, f"{name}|w{k}") for k in range(WOBBLE_SEEDS)]
    res = [x for x in res if x]
    if not res:
        return None
    los, his = [x[0] for x in res], [x[1] for x in res]
    return {"lo_min": min(los), "lo_max": max(los), "hi_min": min(his), "hi_max": max(his),
            "lo_width": round(max(los) - min(los), 3), "hi_width": round(max(his) - min(his), 3),
            "los": los, "his": his}


def diff_boot(A, B, name, val=lambda t: t["r"], reps=BOOT_REPS):
    """2 つの取引の組の平均の差(A − B)を、入口の日の塊を同じ抽出で再抽出して区間・標準誤差を出す。
    B が A を含む(高 − 全)場合も同じ抽出の中で両方の平均を取る。種 = 名前の sha256。種を変えて 5 回の下端も出す。"""
    A = [t for t in A if val(t) == val(t)]
    B = [t for t in B if val(t) == val(t)]
    out = {"nA": len(A), "nB": len(B), "diff": None, "ci95_day": None, "se_day": None, "mde80_day": None}
    if not A or not B:
        return out
    ma, mb = sum(val(t) for t in A) / len(A), sum(val(t) for t in B) / len(B)
    out["diff"] = round(ma - mb, 3)
    if len(A) < MIN_N or len(B) < MIN_N:
        return out
    days = sorted(set(t["day"] for t in A) | set(t["day"] for t in B))
    ix = {d: k for k, d in enumerate(days)}
    k = len(days)
    sA, nA, sB, nB = (np.zeros(k) for _ in range(4))
    for t in A:
        sA[ix[t["day"]]] += val(t)
        nA[ix[t["day"]]] += 1
    for t in B:
        sB[ix[t["day"]]] += val(t)
        nB[ix[t["day"]]] += 1

    def draw(seed_name):
        rng = np.random.default_rng(rb.seed_of(seed_name))
        idx = rng.integers(0, k, size=(reps, k))
        ca, cb = nA[idx].sum(axis=1), nB[idx].sum(axis=1)
        ok = (ca > 0) & (cb > 0)
        d = sA[idx].sum(axis=1)[ok] / ca[ok] - sB[idx].sum(axis=1)[ok] / cb[ok]
        d.sort()
        r = d.size
        return d, [round(float(d[int(0.025 * (r - 1))]), 3), round(float(d[int(0.975 * (r - 1))]), 3)]
    d, ci = draw(name + "|diff|day")
    out["ci95_day"] = ci
    out["se_day"] = round(float(d.std(ddof=1)), 4)
    out["mde80_day"] = round(Z_MDE * out["se_day"], 3)
    out["wobble_lo"] = [draw(f"{name}|diff|day|w{w}")[1][0] for w in range(WOBBLE_SEEDS)]
    return out


def stats(sub, name, ci=True, year_ci=False, extra=False):
    n = len(sub)
    out = {"n": n, "mean_bp": None, "total_bp": 0.0}
    if n == 0:
        return out
    r = [t["r"] for t in sub]
    out["mean_bp"] = round(sum(r) / n, 3)
    out["total_bp"] = round(sum(r), 1)
    out["med_bp"] = round(float(np.median(r)), 3)   # 第 4 版: 割らない bp の中央値(監査の 3 回目 12)
    fin = [t for t in sub if t["rn"] == t["rn"]]
    if fin:
        rn = np.array([t["rn"] for t in fin])
        out["v1"] = round(float(rn.mean()), 5)
        out["v3"] = round(float(sum(t["r"] for t in fin) / sum(t["vp_bin"] for t in fin)), 5)
        out["v4"] = round(float(np.median(rn)), 5)
    fin2 = [t["rn2"] for t in sub if t["rn2"] == t["rn2"]]
    if fin2:
        out["v2"] = round(sum(fin2) / len(fin2), 5)
    if ci and n >= MIN_N:
        days = [t["day"] for t in sub]
        out["ci95_day"] = boot(r, days, name + "|bp|day")
        if len(fin) >= MIN_N:
            out["ci95_day_v1"] = boot([t["rn"] for t in fin], [t["day"] for t in fin], name + "|v1|day")
        if year_ci:
            years = [t["y"] for t in sub]
            out["ci95_year"] = boot(r, years, name + "|bp|year")
        if extra:
            out["se_day"] = boot_se(r, days, name + "|bp|day")
            out["mde80_day"] = round(Z_MDE * out["se_day"], 3) if out["se_day"] is not None else None
            out["wobble_day"] = wobble(r, days, name + "|bp|day")
            if year_ci:
                out["wobble_year"] = wobble(r, [t["y"] for t in sub], name + "|bp|year")
    return out


def light(sub):
    n = len(sub)
    c = {"n": n, "mean_bp": None, "total_bp": 0.0}
    if n:
        r = [t["r"] for t in sub]
        c["mean_bp"] = round(sum(r) / n, 3)
        c["total_bp"] = round(sum(r), 1)
        fin = [t["rn"] for t in sub if t["rn"] == t["rn"]]
        c["v1"] = round(sum(fin) / len(fin), 5) if fin else None
    hs = sum(t["h"] for t in sub)
    c["bars_held"] = hs
    c["per_bar_bp"] = round(c["total_bp"] / hs, 4) if hs else None
    return c


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


def mix_standardize(sub, m, key, groups):
    """高と低の区分の中身を `key` の層で分け、層の内の平均を相手の層の構成で重み付け直す。"""
    H = [t for t in sub if t["bk_" + m] == "high"]
    Lw = [t for t in sub if t["bk_" + m] == "low"]
    out = {"layers": {}}
    mh, ml, wh, wl = {}, {}, {}, {}
    for g in groups:
        hg = [t for t in H if key(t) == g]
        lg = [t for t in Lw if key(t) == g]
        wh[g] = len(hg) / len(H) if H else 0.0
        wl[g] = len(lg) / len(Lw) if Lw else 0.0
        mh[g] = sum(t["r"] for t in hg) / len(hg) if hg else None
        ml[g] = sum(t["r"] for t in lg) / len(lg) if lg else None
        out["layers"][str(g)] = {"n_high": len(hg), "n_low": len(lg), "share_high": round(wh[g], 4),
                                 "share_low": round(wl[g], 4), "mean_high": rnd(mh[g], 3), "mean_low": rnd(ml[g], 3)}
    empty = [str(g) for g in groups if (mh[g] is None and wl[g] > 0) or (ml[g] is None and wh[g] > 0)]
    out["layers_with_empty_side"] = empty
    out["layers_n_lt_30"] = [str(g) for g in groups if 0 < out["layers"][str(g)]["n_high"] < MIN_N
                             or 0 < out["layers"][str(g)]["n_low"] < MIN_N]
    if empty:
        return out
    h_act = sum(wh[g] * mh[g] for g in groups if wh[g] > 0)
    l_act = sum(wl[g] * ml[g] for g in groups if wl[g] > 0)
    h_at_l = sum(wl[g] * mh[g] for g in groups if wl[g] > 0)
    l_at_h = sum(wh[g] * ml[g] for g in groups if wh[g] > 0)
    out.update({"high_actual": rnd(h_act, 3), "low_actual": rnd(l_act, 3),
                "high_mean_with_low_mix": rnd(h_at_l, 3), "low_mean_with_high_mix": rnd(l_at_h, 3),
                "diff_actual": rnd(h_act - l_act, 3),
                "within_layer_at_low_mix": rnd(h_at_l - l_act, 3), "mix_part_at_high_means": rnd(h_act - h_at_l, 3),
                "within_layer_at_high_mix": rnd(h_act - l_at_h, 3), "mix_part_at_low_means": rnd(l_at_h - l_act, 3)})
    return out


def random_controls(recs, aux, edges_b, foot):
    """回答者 A の処方: 同じ足・同じ年・同じ (b) 区分の中で、合図の無い足(遅らせた合図が 0 の足)の終値で入り、
    同じ向き・同じ保有の本数で出る。1 件あたり CTRL_DRAWS 回の平均。逆向きの入りはその符号を変えたもの。"""
    fd, pc, sgd = aux["fd"], aux["pc"], aux["sg_delayed"]
    n = pc.size
    vp, yr = fd.vol_prev, fd.year
    rng = np.random.default_rng(rb.seed_of(f"{foot}|random_entry"))
    for t in recs:
        t["ctrl"] = float("nan")
    for y in Q2_YEARS:
        e = edges_b.get(y)
        if e is None:
            continue
        bars_y = np.flatnonzero((yr == y) & (sgd == 0) & ~np.isnan(vp))
        bk_bars = np.array([xv.bucket_of(float(v), e) for v in vp[bars_y]], dtype=object)
        for bk in BUCKETS:
            E = bars_y[bk_bars == bk]
            ts = [t for t in recs if t["y"] == y and t["bk_b"] == bk]
            if not ts or E.size == 0:
                continue
            J = E[rng.integers(0, E.size, size=(len(ts), CTRL_DRAWS))]
            Hh = np.array([t["h"] for t in ts])[:, None]
            sgn = np.array([t["sgn"] for t in ts])[:, None]
            K = J + Hh
            ok = K < n
            Kc = np.where(ok, K, 0)
            ret = np.where(ok, sgn * (pc[Kc] / pc[J] - 1.0) * 1e4, np.nan)
            allnan = np.isnan(ret).all(axis=1)
            cnt = (~np.isnan(ret)).sum(axis=1)
            cm = np.where(allnan, np.nan, np.nansum(ret, axis=1) / np.maximum(cnt, 1))
            for k, t in enumerate(ts):
                t["ctrl"] = float("nan") if allnan[k] else float(cm[k])
    return {"draws_per_trade": CTRL_DRAWS,
            "rule": ("同じ足・同じ年・同じ (b) 区分(足の vol_prev をその年の (b) の境目で分けた区分)の足のうち、"
                     "遅らせた合図が 0 の足を無作為に選び、その足の bitFlyer の終値で入り、元の取引と同じ向き・同じ保有の本数で出る。"
                     "逆向きの入りは同じ抽出で向きを逆にしたもので、平均は同じ向きの平均の符号違いになる(恒等式)。")}


def control_cells(sub, name):
    s = [t for t in sub if t["ctrl"] == t["ctrl"]]
    if not s:
        return {"n": 0}
    d = [t["r"] - t["ctrl"] for t in s]
    return {"n": len(s), "mean_actual": round(sum(t["r"] for t in s) / len(s), 3),
            "mean_random_same_dir": round(sum(t["ctrl"] for t in s) / len(s), 3),
            "mean_random_opposite_dir": round(-sum(t["ctrl"] for t in s) / len(s), 3),
            "mean_actual_minus_random": round(sum(d) / len(d), 3),
            "ci95_day_actual_minus_random": boot(d, [t["day"] for t in s], name + "|ctrl|day")}


def q2_foot(sig_bars, price_bars, foot):
    recs, aux = trade_records(sig_bars, price_bars)
    edges = assign_buckets(recs)
    ctrl_rule = random_controls(recs, aux, edges["b"], foot)
    out = {"n_trades": len(recs),
           "n_flipped": sum(1 for t in recs if t["flipped"]),
           "edges_fixed_bp": {m: [rnd(edges[m][2018][0]), rnd(edges[m][2018][1])] for m in ("a", "a_bf")},
           "mean_vol_prev_by_year_v2_divisor": aux["mean_vp_year"],
           "years": {}, "pooled": {}, "hold": {}, "splits": {}}
    for y in Q2_YEARS:
        ys = [t for t in recs if t["y"] == y]
        yr = {"all": stats(ys, f"{foot}|{y}|all")}
        for m in METHODS:
            e = edges[m][y]
            d = {"edges_bp": None if e is None else [rnd(e[0]), rnd(e[1])], "mark": mark_of(m, y)}
            if e is None:
                d["blank"] = True
            else:
                for bk in BUCKETS:
                    sub = [t for t in ys if t["bk_" + m] == bk]
                    d[bk] = stats(sub, f"{foot}|{y}|{m}|{bk}")
                    d[bk]["share_n"] = round(len(sub) / len(ys), 4) if ys else None
                d["n_unbucketed"] = sum(1 for t in ys if t["bk_" + m] is None)
            yr[m] = d
        out["years"][str(y)] = yr
    ps0 = [t for t in recs if t["y"] in PERIODS["2018_2023"]]
    hq = {q: int(np.percentile([t["h"] for t in ps0], q, method="lower")) for q in (10, 50, 75)} if ps0 else {}
    foot_bins = []
    lo_ = 1
    for hi_ in (hq.get(10, 1), hq.get(50, 1), hq.get(75, 1)):
        if hi_ >= lo_:
            foot_bins.append((f"{lo_}-{hi_}", lo_, hi_))
            lo_ = hi_ + 1
    foot_bins.append((f"{lo_}+", lo_, 10 ** 12))
    out["hold_bins_foot"] = {"rule": "その足の 2018〜2023 の保有の本数の 10・50・75% 点(下側の値)で区切る。同じ値が続く区切りは 1 つにまとめる",
                             "quantiles": hq, "bins": [b[0] for b in foot_bins]}
    for pname, pyears in PERIODS.items():
        ps = [t for t in recs if t["y"] in pyears]
        allc = stats(ps, f"{foot}|{pname}|all", year_ci=True, extra=True)
        p = {"years": list(pyears), "all": allc}
        for m in METHODS:
            p[m] = {}
            for bk in BUCKETS:
                sub = [t for t in ps if t["bk_" + m] == bk]
                c = stats(sub, f"{foot}|{pname}|{m}|{bk}", year_ci=True, extra=(m == "b"))
                c["share_n"] = round(len(sub) / len(ps), 4) if ps else None
                c["share_total"] = round(c["total_bp"] / allc["total_bp"], 4) if allc["total_bp"] else None
                p[m][bk] = c
            p[m]["n_unbucketed"] = sum(1 for t in ps if t["bk_" + m] is None)
        # 保有の構成・時間帯の構成をそろえた比べ
        p["hold_standardized"] = {m: mix_standardize(ps, m, lambda t: next(
            k for k, lo, hi in HOLD_BINS if lo <= t["h"] <= hi), [h[0] for h in HOLD_BINS]) for m in STD_METHODS}
        p["hold_standardized_foot_bins"] = {m: mix_standardize(ps, m, lambda t: next(
            k for k, lo, hi in foot_bins if lo <= t["h"] <= hi), [b[0] for b in foot_bins]) for m in STD_METHODS}
        p["hour6_standardized"] = {m: mix_standardize(ps, m, lambda t: t["hour6"], [0, 1, 2, 3]) for m in STD_METHODS}
        # 第 4 版: 判定の目標の差(高 − 低、高 − 全)の区間・標準誤差・最小検出差(監査の 3 回目 1)
        bh = [t for t in ps if t["bk_b"] == "high"]
        bl = [t for t in ps if t["bk_b"] == "low"]
        p["diffs_b"] = {"high_minus_low": diff_boot(bh, bl, f"{foot}|{pname}|b|h-l"),
                        "high_minus_all": diff_boot(bh, ps, f"{foot}|{pname}|b|h-all")}
        p["diffs_c_same"] = {"high_minus_low": diff_boot([t for t in ps if t["bk_c_same"] == "high"],
                                                         [t for t in ps if t["bk_c_same"] == "low"], f"{foot}|{pname}|c_same|h-l")}
        # 無作為の時刻の入りの対照((b) の区分ごと)
        p["random_entry_control_b"] = {bk: control_cells([t for t in ps if t["bk_b"] == bk], f"{foot}|{pname}|b|{bk}")
                                       for bk in BUCKETS}
        p["random_entry_control_b"]["all_bucketed"] = control_cells([t for t in ps if t["bk_b"] in BUCKETS],
                                                                    f"{foot}|{pname}|b|allb")
        # (高の 実際 − 対照)−(低の 実際 − 対照)の区間(監査の 3 回目 4)
        p["random_entry_control_b"]["high_minus_low_of_actual_minus_random"] = diff_boot(
            bh, bl, f"{foot}|{pname}|ctrl|h-l", val=lambda t: t["r"] - t["ctrl"] if t["ctrl"] == t["ctrl"] else float("nan"))
        out["pooled"][pname] = p
    ps = [t for t in recs if t["y"] in PERIODS["2018_2023"]]
    for hname, lo, hi in HOLD_BINS:
        hsub = [t for t in ps if lo <= t["h"] <= hi]
        d = {"all": light(hsub), "share_n_of_period": round(len(hsub) / len(ps), 4) if ps else None}
        for m in METHODS:
            d[m] = {bk: light([t for t in hsub if t["bk_" + m] == bk]) for bk in BUCKETS}
        out["hold"][hname] = d
    for sname, key, vals in (("strength", "flipped", (True, False)), ("direction", "dir", ("long", "short")),
                             ("hour6_utc", "hour6", (0, 1, 2, 3))):
        d = {}
        for v in vals:
            vsub = [t for t in ps if t[key] == v]
            dv = {"all": light(vsub)}
            for m in SPLIT_METHODS:
                dv[m] = {bk: light([t for t in vsub if t["bk_" + m] == bk]) for bk in BUCKETS}
            d[str(v)] = dv
        out["splits"][sname] = d
    out["random_entry_rule"] = ctrl_rule
    out["spearman_2018_2023"] = spearman_pairs(ps, (("vp_bin", "c_next"), ("vp_bin", "h"), ("c_next", "h"),
                                                    ("c_old", "h"), ("vp_bin", "vp_bf"), ("vp_bin", "abs_r"),
                                                    ("c_next", "abs_r"), ("c_old", "abs_r")))
    out["hold_quantiles_2018_2023"] = {f"p{q}": int(np.percentile([t["h"] for t in ps], q, method="lower"))
                                       for q in (0, 10, 25, 50, 75, 90, 100)} if ps else None
    out["criteria"] = criteria(out)
    return out


CRITERIA_DEFINITION = (
    "DESIGN.md 第 2 版 8 の条件を (b)(Binance の vol_prev × 前の暦年の境目)について機械的に数えたもの。"
    "第 2 版 8 の文面に無い読み(DESIGN.md 第 3 版 1・2、測った後・監査の後に足したもの)は全部並べ、どれか 1 つを選ばない。"
    "条件 A(升の組)= (b) の高い区分の値 > 全取引の値 かつ > (b) の低い区分の値(どれかが空なら成り立たない)。"
    "(基) = 2018〜2023 を束ねた升で条件 A(損益 bp の平均)。第 2 版 8 の本文「高い区分が全取引の平均と低い区分の平均の両方を上回り」。"
    "(i) = 2018〜2023 の 6 年のうち条件 A(損益 bp の平均)が成り立つ年が 4 年以上。"
    "(ii) は「ボラで割った損益でも同じ向きで」。数え方 2 通り × 割る量 4 通り: (ii-年) = 6 年のうち 4 年以上 / "
    "(ii-束) = 2018〜2023 を束ねた升で 1 回。割る量 v1〜v4 は q2.versions。"
    "(iii) は「2020・2021 を除いた束ねでも区間が 0 を跨がない」。区間 2 通り: (iii-日) = 日の塊 / (iii-年) = 年の塊。"
    "どちらも、2018・2019・2022・2023 の束ねで条件 A(損益 bp)が成り立ち、かつ (b) の高い区分の 95% 区間の下端 > 0。"
    "組み合わせ = (基) ∧ (i) ∧ (ii-年 か ii-束)[v] ∧ (iii-日 か iii-年)。"
    "(ii-年) を第 2 版で作業者が選んだのは、データを 2023-01-31 で切った煙の試しの出力を見た後だった(監査の 2 回目 1)。")


def criteria(fq):
    def cond(cells, key):
        hi, lo, al = cells["b"]["high"].get(key), cells["b"]["low"].get(key), cells["all"].get(key)
        if hi is None or lo is None or al is None:
            return False
        return hi > al and hi > lo
    yrs = PERIODS["2018_2023"]
    p_all, p_ex = fq["pooled"]["2018_2023"], fq["pooled"]["2018_2019_2022_2023"]

    def years_ok(key):
        return [y for y in yrs if not fq["years"][str(y)]["b"].get("blank") and cond(fq["years"][str(y)], key)]
    hi_ex = p_ex["b"]["high"]
    comp = {
        "base": {"value": cond(p_all, "mean_bp"),
                 "detail": {"high": p_all["b"]["high"]["mean_bp"], "all": p_all["all"]["mean_bp"], "low": p_all["b"]["low"]["mean_bp"]}},
        "i": {"value": len(years_ok("mean_bp")) >= 4, "years": years_ok("mean_bp")},
        "iii_day": {"value": bool(cond(p_ex, "mean_bp") and hi_ex.get("ci95_day") and hi_ex["ci95_day"][0] > 0),
                    "cond_A": cond(p_ex, "mean_bp"), "high_mean": hi_ex["mean_bp"], "ci": hi_ex.get("ci95_day"),
                    "wobble": hi_ex.get("wobble_day"), "n_high": hi_ex["n"]},
        "iii_year": {"value": bool(cond(p_ex, "mean_bp") and hi_ex.get("ci95_year") and hi_ex["ci95_year"][0] > 0),
                     "cond_A": cond(p_ex, "mean_bp"), "high_mean": hi_ex["mean_bp"], "ci": hi_ex.get("ci95_year"),
                     "wobble": hi_ex.get("wobble_year"), "n_high": hi_ex["n"]},
    }
    for v in VERSIONS:
        comp[f"ii_year_{v}"] = {"value": len(years_ok(v)) >= 4, "years": years_ok(v)}
        comp[f"ii_pool_{v}"] = {"value": cond(p_all, v),
                                "detail": {"high": p_all["b"]["high"].get(v), "all": p_all["all"].get(v), "low": p_all["b"]["low"].get(v)}}
    # 第 4 版: (iii-日)・(iii-年) を主の種と、種を変えた 5 回それぞれで数える(監査の 3 回目 6)
    def iii_by_seed(kind):
        c = comp[f"iii_{kind}"]
        w = c.get("wobble") or {}
        los = ([c["ci"][0]] if c.get("ci") else [None]) + list(w.get("los", []))
        return [bool(c["cond_A"] and lo is not None and lo > 0) for lo in los]
    comp["iii_day"]["by_seed"] = iii_by_seed("day")
    comp["iii_year"]["by_seed"] = iii_by_seed("year")
    comp["iii_year"]["note"] = ("年の塊は 4 つ(2018・2019・2022・2023)。4 年の (b) 高の平均がすべて正なら、下端 > 0 は"
                                "機械的に成り立つ(監査の 3 回目 7)")
    comp["iii_year"]["high_means_by_year"] = {str(y): fq["years"][str(y)]["b"]["high"]["mean_bp"]
                                              for y in PERIODS["2018_2019_2022_2023"]}
    # v2 の (ii-年) は (i) の言い直し(年の中で定数で割っても条件 A は変わらない。監査の 3 回目 2)
    comp["ii_year_v2"]["same_years_as_i"] = comp["ii_year_v2"]["years"] == comp["i"]["years"]
    # 2023 年も除いた束ね(監査の 3 回目 8。数えには入れない参考)
    p_ex3 = fq["pooled"]["2018_2019_2022"]
    hi3 = p_ex3["b"]["high"]
    comp["ref_iii_excl_2023"] = {"cond_A": cond(p_ex3, "mean_bp"), "high_mean": hi3["mean_bp"], "n_high": hi3["n"],
                                 "ci_day": hi3.get("ci95_day"), "ci_year": hi3.get("ci95_year"),
                                 "wobble_day": hi3.get("wobble_day")}

    def combos_for(seed_idx):
        cmb = {}
        for v in VERSIONS:
            for ii in ("year", "pool"):
                for iii in ("day", "year"):
                    iii_v = comp[f"iii_{iii}"]["by_seed"][seed_idx]
                    cmb[f"{v}|ii_{ii}|iii_{iii}"] = bool(comp["base"]["value"] and comp["i"]["value"]
                                                         and comp[f"ii_{ii}_{v}"]["value"] and iii_v)
        return cmb
    n_seeds = len(comp["iii_day"]["by_seed"])
    combos = combos_for(0)

    def counts(cmb):
        keep_all = list(cmb)
        no_dup = [k for k in keep_all if not k.startswith("v2|ii_year")]
        no_iiiy = [k for k in keep_all if not k.endswith("iii_year")]
        both = [k for k in no_dup if not k.endswith("iii_year")]
        return {f"all_{len(keep_all)}": sum(cmb[k] for k in keep_all),
                f"without_v2_ii_year_{len(no_dup)}": sum(cmb[k] for k in no_dup),
                f"without_iii_year_{len(no_iiiy)}": sum(cmb[k] for k in no_iiiy),
                f"without_both_{len(both)}": sum(cmb[k] for k in both)}
    counts_by_seed = [counts(combos_for(i)) for i in range(n_seeds)]
    # 判定の目標の差の最小検出差(監査の 3 回目 1)
    mde = {}
    for pn in PERIODS:
        dd = fq["pooled"][pn]["diffs_b"]
        mde[pn] = {k: {"diff": v["diff"], "ci95_day": v["ci95_day"], "se_day": v["se_day"], "mde80_day": v["mde80_day"],
                       "wobble_lo": v.get("wobble_lo")} for k, v in dd.items()}
    words = {k: ("前もって分けられた" if v else "分けられたと言えない") for k, v in combos.items()}
    return {"components": comp, "combos": combos, "words": words, "counts": counts_by_seed[0],
            "counts_by_seed": counts_by_seed,
            "seed_note": "by_seed と counts_by_seed の 0 番は主の種、1〜5 番は種を変えた 5 回(端の揺れ)",
            "mde_targets": mde}


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
    nm = f" / {c['v1']:+.3f}" if c.get("v1") is not None else ""
    return f"{c['n']:,}{sh} / {c['mean_bp']:+.2f}{ci_s(c)} / {c['total_bp']:+,.0f}{nm}"


def cell_light(c):
    if c["n"] == 0:
        return "0"
    pb = f" / {c['per_bar_bp']:+.3f}" if c.get("per_bar_bp") is not None else ""
    nm = f" / {c['v1']:+.3f}" if c.get("v1") is not None else ""
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
    L.append("割る量(`q2.versions`): " + " / ".join(q2["versions"].values()))
    L.append("")
    L.append("### 4.0 読みごとの成否(`q2.feet.<足>.criteria`)")
    L.append("")
    L.append(q2["criteria_definition"])
    L.append("")
    feet = list(q2["feet"])
    yn = lambda b: "成り立つ" if b else "成り立たない"  # noqa: E731
    L.append("#### 4.0.1 条件ごと")
    L.append("")
    L.append("| 条件 | " + " | ".join(f"{f} 分" for f in feet) + " |")
    L.append("|---|" + "---|" * len(feet))
    rows = [("(基)", "base"), ("(i)", "i")] + [(f"(ii-年) {v}", f"ii_year_{v}") for v in VERSIONS] \
        + [(f"(ii-束) {v}", f"ii_pool_{v}") for v in VERSIONS] + [("(iii-日)", "iii_day"), ("(iii-年)", "iii_year")]
    for lab, key in rows:
        cells = []
        for f in feet:
            c = q2["feet"][f]["criteria"]["components"][key]
            det = ""
            if "years" in c:
                det = f"({len(c['years'])} 年 {c['years']})"
            elif key.startswith("iii"):
                det = (f"(条件 A {c['cond_A']}、高 {c['high_mean']}(n {c['n_high']:,})区間 {c['ci']}。"
                       f"主の種と種を変えた 5 回で成り立つ数 {sum(c['by_seed'])}/{len(c['by_seed'])})")
            elif "detail" in c:
                dd = c["detail"]
                det = f"(高 {dd['high']} / 全 {dd['all']} / 低 {dd['low']})"
            cells.append(yn(c["value"]) + det)
        L.append(f"| {lab} | " + " | ".join(cells) + " |")
    med_cells = []
    for f in feet:
        pa = q2["feet"][f]["pooled"]["2018_2023"]
        h, lo_, al = pa["b"]["high"].get("med_bp"), pa["b"]["low"].get("med_bp"), pa["all"].get("med_bp")
        med_cells.append(f"{yn(h > al and h > lo_)}(高 {h} / 全 {al} / 低 {lo_})")
    L.append("| 参考: 割らない bp の中央値で、束ねた升の条件 A(数えに入れない) | " + " | ".join(med_cells) + " |")
    L.append("")
    L.append("- (ii-年) v2 は、年の中で一定の値で割るので条件 A が変わらず、(i) の言い直しになる。年の集合が (i) と同じか: "
             + "、".join(f"{f} 分 {q2['feet'][f]['criteria']['components']['ii_year_v2']['same_years_as_i']}" for f in feet) + "。")
    L.append("- (iii-年) は年の塊が 4 つ。4 年の (b) 高の平均がすべて正なら、下端 > 0 は機械的に成り立つ。4 年の (b) 高の平均: "
             + "、".join(f"{f} 分 {q2['feet'][f]['criteria']['components']['iii_year']['high_means_by_year']}" for f in feet) + "。")
    L.append("- 参考(数えに入れない): 2023 年も除いた束ね(2018・2019・2022)の (b) 高: " + "、".join(
        f"{f} 分 {q2['feet'][f]['criteria']['components']['ref_iii_excl_2023']['high_mean']}(n "
        f"{q2['feet'][f]['criteria']['components']['ref_iii_excl_2023']['n_high']:,})日 {q2['feet'][f]['criteria']['components']['ref_iii_excl_2023']['ci_day']}"
        f" 年 {q2['feet'][f]['criteria']['components']['ref_iii_excl_2023']['ci_year']}" for f in feet) + "。")
    L.append("")
    L.append("#### 4.0.2 組み合わせ((基)∧(i)∧(ii)∧(iii)、割る量 4 × (ii) 2 × (iii) 2 = 16 通り)")
    L.append("")
    combos = list(next(iter(q2["feet"].values()))["criteria"]["combos"])
    L.append("| 読み | " + " | ".join(f"{f} 分" for f in feet) + " |")
    L.append("|---|" + "---|" * len(feet))
    for k in combos:
        L.append(f"| {k} | " + " | ".join(q2["feet"][f]["criteria"]["words"][k] for f in feet) + " |")
    L.append("")
    L.append("「前もって分けられた」の数(主の種。括弧は種を変えた 5 回を含む 6 回の最小〜最大。`criteria.counts`・`counts_by_seed`):")
    L.append("")
    keys = list(next(iter(q2["feet"].values()))["criteria"]["counts"])
    lab = {keys[0]: "16 通り", keys[1]: "v2 の (ii-年) を除いた 14 通り", keys[2]: "(iii-年) を除いた 8 通り", keys[3]: "両方を除いた 7 通り"}
    L.append("| 数え方 | " + " | ".join(f"{f} 分" for f in feet) + " |")
    L.append("|---|" + "---|" * len(feet))
    for k in keys:
        cells = []
        for f in feet:
            cb = q2["feet"][f]["criteria"]["counts_by_seed"]
            vals = [c[k] for c in cb]
            cells.append(f"{cb[0][k]}({min(vals)}〜{max(vals)})")
        L.append(f"| {lab[k]} | " + " | ".join(cells) + " |")
    L.append("")
    L.append("#### 4.0.3 判定の目標の差(高 − 低、高 − 全)の区間・最小検出差(`criteria.mde_targets`、`pooled.<期間>.diffs_b`)")
    L.append("")
    L.append("差の区間 = 入口の日の塊を同じ抽出で再抽出(2000 回)。最小検出差 = (1.96 + 0.84) × その差の標準誤差。"
             "下端の揺れ = 種を変えた 5 回の下端。2 つの差・3 つの期間・6 つの足に同じ規則。")
    L.append("")
    L.append("| 足 | 期間 | 高 − 低: 差 [日の塊] / 最小検出差 / 下端の揺れ | 高 − 全: 差 [日の塊] / 最小検出差 / 下端の揺れ |")
    L.append("|---|---|---|---|")
    for f in feet:
        for pn, md in q2["feet"][f]["criteria"]["mde_targets"].items():
            def dcell(x):
                if x["ci95_day"] is None:
                    return f"{x['diff']}(区間なし)"
                w = x.get("wobble_lo") or []
                return (f"{x['diff']:+.2f} [{x['ci95_day'][0]:+.2f}, {x['ci95_day'][1]:+.2f}] / {x['mde80_day']:.2f} / "
                        f"{min(w):+.2f}〜{max(w):+.2f}")
            L.append(f"| {f} 分 | {pn} | {dcell(md['high_minus_low'])} | {dcell(md['high_minus_all'])} |")
    L.append("")
    L.append("#### 4.0.4 (b) の年ごとの升(条件 (i)・(ii-年) が数える升。取引数と区間を並べる)")
    L.append("")
    L.append("| 足 | 年 | 高: n(割合)/ 平均 [日の塊] | 低: n(割合)/ 平均 [日の塊] | 全取引: n / 平均 | 条件 A: bp / v1 / v2 / v3 / v4 |")
    L.append("|---|---|---|---|---|---|")
    for f in feet:
        for y in map(str, PERIODS["2018_2023"]):
            yr = q2["feet"][f]["years"][y]
            b = yr["b"]
            if b.get("blank"):
                continue

            def cy(c):
                return f"{c['n']:,}({c['share_n'] * 100:.0f}%)/ {fmt(c['mean_bp'])}{ci_s(c)}"

            def ca(key):
                h, lo_, al = b["high"].get(key), b["low"].get(key), yr["all"].get(key)
                return "○" if (h is not None and lo_ is not None and al is not None and h > al and h > lo_) else "×"
            L.append(f"| {f} 分 | {y} | {cy(b['high'])} | {cy(b['low'])} | {yr['all']['n']:,} / {fmt(yr['all']['mean_bp'])} | "
                     + " / ".join(ca(k) for k in ("mean_bp",) + VERSIONS) + " |")
    L.append("")
    L.append("(○ = 条件 A が成り立つ、× = 成り立たない。記号はこの表の中だけで使う。)")
    for foot, fv in q2["feet"].items():
        L.append("")
        L.append(f"### 足 {foot} 分(取引 {fv['n_trades']:,} 件、うち H1 で反転した合図 {fv['n_flipped']:,} 件)")
        L.append("")
        L.append(f"固定の境目(2018〜2019 の取引から): (a) {fv['edges_fixed_bp']['a']}、(a bitFlyer) {fv['edges_fixed_bp']['a_bf']}。"
                 f"保有の本数の分位(2018〜2023): {fv['hold_quantiles_2018_2023']}。v2 の分母(年ごとの全取引の vol_prev の平均): "
                 f"{fv['mean_vol_prev_by_year_v2_divisor']}。")
        L.append("")
        L.append("順位相関(2018〜2023 の取引、区間なし。`spearman_2018_2023`): " + "、".join(
            f"{k} {v['rho']}(n {v['n']:,})" for k, v in fv["spearman_2018_2023"].items()))
        L.append("")
        L.append("#### 年ごと(各升 = 取引数(その年の取引に対する割合)/ 平均 bp [日の塊の区間] / 総損益 bp / v1)")
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
            L.append(f"#### 束ねた升 {pname}(年 {p['years']}。三分位は年ごとの境目で分けたものを束ねた。(a) は境目を決めた 2018・2019 を含む)")
            L.append("")
            a = p["all"]
            L.append(f"全取引: {a['n']:,} / 平均 {a['mean_bp']:+.2f} [日{ci_s(a)}] [年{ci_s(a, 'ci95_year')}] / 総損益 {a['total_bp']:+,.0f}"
                     f" / v1 {fmt(a.get('v1'), 3)} / v2 {fmt(a.get('v2'), 3)} / v3 {fmt(a.get('v3'), 3)} / v4 {fmt(a.get('v4'), 3)}")
            L.append("")
            L.append("| 分け方 | 区分 | 取引数(割合) | 総損益(割合) | 平均 bp [日の塊] [年の塊] | v1 [日の塊] / v2 / v3 / v4 |")
            L.append("|---|---|---|---|---|---|")
            for m in METHODS:
                for b in BUCKETS:
                    c = p[m][b]
                    if c["n"] == 0:
                        L.append(f"| {m} | {b} | 0 | — | — | — |")
                        continue
                    stt = "—" if c["share_total"] is None else f"{c['share_total'] * 100:.0f}%"
                    L.append(f"| {m} | {b} | {c['n']:,}({c['share_n'] * 100:.1f}%) | {c['total_bp']:+,.0f}({stt}) | "
                             f"{c['mean_bp']:+.2f}{ci_s(c)}{ci_s(c, 'ci95_year')} | {fmt(c.get('v1'), 3)}{ci_s(c, 'ci95_day_v1', 3)}"
                             f" / {fmt(c.get('v2'), 3)} / {fmt(c.get('v3'), 3)} / {fmt(c.get('v4'), 3)} |")
            dc = p["diffs_c_same"]["high_minus_low"]
            L.append("")
            L.append(f"(c 同年) の高 − 低: {dc['diff']} [日の塊 {dc['ci95_day']}](`diffs_c_same`)。")
            for tag, title in (("hold_standardized", "保有の構成をそろえた比べ(層 = 保有 1 / 2〜7 / 8〜21 / 22 本以上。5 分の分位から丸めた区切り)"),
                               ("hold_standardized_foot_bins", f"保有の構成をそろえた比べ(層 = この足の保有の 10・50・75% 点の区切り {fv['hold_bins_foot']['bins']})"),
                               ("hour6_standardized", "時間帯の構成をそろえた比べ(層 = 入口の足の UTC 0〜5・6〜11・12〜17・18〜23 時)")):
                L.append("")
                L.append(f"{title}。保有は入口の後に決まる量なので、保有の比べは結果で条件づけている:")
                L.append("")
                L.append("| 分け方 | 高 実際 | 低 実際 | 高の層の平均 × 低の構成 | 低の層の平均 × 高の構成 | 差 実際 | 層の内の差(低の構成) | 構成の差(高の平均) | 層の内の差(高の構成) | 構成の差(低の平均) |")
                L.append("|---|---|---|---|---|---|---|---|---|---|")
                for m, s in p[tag].items():
                    if s.get("layers_with_empty_side"):
                        L.append(f"| {m} | 片側が空の層 {s['layers_with_empty_side']} | | | | | | | | |")
                        continue
                    L.append(f"| {m} | {s['high_actual']} | {s['low_actual']} | {s['high_mean_with_low_mix']} | {s['low_mean_with_high_mix']} | "
                             f"{s['diff_actual']} | {s['within_layer_at_low_mix']} | {s['mix_part_at_high_means']} | "
                             f"{s['within_layer_at_high_mix']} | {s['mix_part_at_low_means']} |")
                L.append("")
                L.append("層ごとの (b)(n 高 / n 低 / 高の割合 / 低の割合 / 高の平均 / 低の平均): " + "、".join(
                    f"{g}: {d['n_high']:,} / {d['n_low']:,} / {d['share_high']} / {d['share_low']} / {d['mean_high']} / {d['mean_low']}"
                    for g, d in p[tag]["b"]["layers"].items()))
                small = {m: s_.get("layers_n_lt_30") for m, s_ in p[tag].items() if s_.get("layers_n_lt_30")}
                if small:
                    L.append("")
                    L.append(f"注: 高か低の取引数が 30 未満の層がある(分け方: 層): {small}。その層の平均は件数が少ない。")
            L.append("")
            L.append("無作為の時刻の入りの対照((b) の区分ごと。`random_entry_control_b`):")
            L.append("")
            L.append("| 区分 | n | 実際の平均 | 無作為・同じ向き | 無作為・逆向き(同じ抽出の符号違い。独立の測定ではない) | 実際 − 無作為・同じ向き [日の塊] |")
            L.append("|---|---|---|---|---|---|")
            for bk, c in p["random_entry_control_b"].items():
                if bk == "high_minus_low_of_actual_minus_random":
                    continue
                if c["n"] == 0:
                    L.append(f"| {bk} | 0 | | | | |")
                    continue
                L.append(f"| {bk} | {c['n']:,} | {c['mean_actual']:+.2f} | {c['mean_random_same_dir']:+.2f} | {c['mean_random_opposite_dir']:+.2f} | "
                         f"{c['mean_actual_minus_random']:+.2f}{ci_s(c, 'ci95_day_actual_minus_random')} |")
            hl = p["random_entry_control_b"]["high_minus_low_of_actual_minus_random"]
            L.append("")
            L.append(f"(高の 実際 − 対照)−(低の 実際 − 対照): {hl['diff']} [日の塊 {hl['ci95_day']}]、最小検出差 {hl['mde80_day']}。")
        L.append("")
        L.append(f"対照の作り方: {fv['random_entry_rule']['rule']}(1 件あたり {fv['random_entry_rule']['draws_per_trade']} 回)")
        L.append("")
        L.append("#### 保有の長さで分けた表(2018〜2023 を束ねる。各升 = 取引数 / 平均 bp / 総損益 / 足 1 本あたりの損益 bp / v1。区間なし)")
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
        L.append("#### 合図の強さ・向き・時間帯で分けた表(2018〜2023 を束ねる。各升は保有の表と同じ。区間なし)")
        L.append("")
        for sname, title, lab in (("strength", "合図の強さ", {"True": "H1 で反転した合図", "False": "元から弱い合図"}),
                                  ("direction", "取引の向き", {"long": "買い", "short": "売り"}),
                                  ("hour6_utc", "時間帯(入口の足の UTC)", {"0": "0〜5 時", "1": "6〜11 時", "2": "12〜17 時", "3": "18〜23 時"})):
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
        q2[str(foot)] = q2_foot(sig_bars[foot], price_bars[foot], foot)
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
                "DESIGN.md 第 2 版の定め 1〜8 に、第 3 版の 1〜4(測った後・監査の後に足した読みと計算。事前登録ではない)を足して測った。読みは段階 G の読み。年は取引の入口の足の年。経費前・建玉 1 単位・"
                "約定は bitFlyer の足の終値(段階 G と同じ)。指値は見ていない。",
                "「三分位」= 境目で 3 つに分けた区分。(b)・(c 前年)・(a) では、その年に入る割合が 1/3 にならない。各升に割合を並べた。",
                "(a) の境目はこの読みの 2018〜2019 の取引から edges_from_vol で決めた値。K1 の保存値(丸めたもの、"
                f"vol_terciles.json: edges_bp_own)は 5 分 {k1['feet']['5']['edges_bp_own']}、15 分 {k1['feet']['15']['edges_bp_own']}。"
                "1・3・30・60 分は K1 に保存値が無い。",
                "印: (a)・(a bitFlyer) の 2017 = 先読みあり、2018・2019 = 境目を決めた年(in-sample)。(b)・(c 前年)・(b bitFlyer) の "
                "2017 = 空欄。(c 同年)・旧 (c) = その年の値で切った(後でしか分からない。ボラの門には使えない)。",
                "(c) は定め直した: 入口の足の次から固定 100 本の Binance の足の実際のボラ(問い 1 の vol_next と同じ)。保有の長さと"
                "取引所を (a)(b) とそろえた。旧 (c)(取引の間の bitFlyer のボラ)は参考の列。",
                "第 4 版: 足ごとの言葉は DESIGN 第 3 版 5 の 2 語「前もって分けられた / 分けられたと言えない」だけを、読みごとに機械的に出す。"
                "最小検出差は判定の目標の差(高 − 低、高 − 全)の標準誤差から出す。新しく置いた値の出所は q2.assumptions。",
                "ボラで割った損益は 4 通り(q2.versions)。v1 は割る量が分ける量の vol_prev そのもの(第 2 版)。単位は無い。",
                "第 2 版 8 の (ii) の数え方と (iii) の区間は DESIGN.md の文面に無い。第 2 版で作業者が (ii) を「6 年のうち 4 年以上」と決めたのは、"
                "データを 2023-01-31 で切った煙の試しの出力が出た後だった。この版では全部の組み合わせを並べ、どれか 1 つを結論にしない。",
                "K1 の設計そのもの(ヒゲの門 s19/b24 を含む)は 2017〜2026 の Binance を見て選んだ(in-sample)。2018〜2023 の束ねは"
                "新しい期間に対する検証ではない。満たしても「K1 の期間の中で前もって分けられた」までしか言わない(DESIGN.md 第 2 版 8)。",
                "2023 は 2023-12-17 まで。2017 は K1 当時の結合と大きく違う年(§2 の注)。",
            ],
            "criteria_definition": CRITERIA_DEFINITION,
            "versions": VERSION_LABEL,
            "assumptions": ASSUMPTIONS,
            "bootstrap": {"reps": BOOT_REPS, "method": "measure_katsuo_robustness.np_boot(塊の (合計, 件数) を畳んで塊を復元抽出、種 = 升の名前の sha256)",
                          "wobble_seeds": WOBBLE_SEEDS, "min_n": MIN_N,
                          "q1_spearman_reps": REPS},
            "methods": {m: v[2] for m, v in METHODS.items()},
            "hold_bins": [h[0] for h in HOLD_BINS],
            "feet": q2,
        },
    }
    out_json = HERE / "vol_gate.json"
    out_json.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    write_md(res, HERE / "TABLES.md")
    print(f"→ {out_json} / {HERE / 'TABLES.md'}", flush=True)
    print(json.dumps({f: v["criteria"]["counts"] for f, v in q2.items()}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()

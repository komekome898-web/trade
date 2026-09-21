#!/usr/bin/env python3
"""清算を起点とした値動きの予測可能性 — **材料の選定**の道具(2026-09-20、続く2 で 24 本に更新)。

設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_MATERIALS_DESIGN_2026-09-20.md`(§5.4 が足す 2 本)
委任文: `docs/DATA/delegations/20260920_o3c_signal_materials_prompt.md`(初回、22 本)、
       `docs/DATA/delegations/20260920_o3c_signal_materials2_prompt.md`(続き、+R1・F5)

**この道具がすること**
  - 母集団は探索段 5 の行データ `rows_prints.csv.gz` の `kind == "print"`(52,000 件)。
  - 候補 24 本(設計 §2 + §5.4)を計算する。既存 13 本(1,2,3,5',6,8,9,10,11,12,13,14,15。
    4 は外す)は前段の道具 `o3c_signal_continue.py` の材料列を**再利用**するが、
    5' だけは「先」だけの距離として**作り直す**。新規 11 本(F3,F4,A3,A4,A5,A6,A9,
    C3,C4,R1,F5)は **ts 以前の約定・清算・5 分値だけ**で新しく計算する(p₀ は使わない)。
  - 事後の位置(探索段 5 の `bundle_pos`・`bundle_pos_single`)から 2 組
    (組 A = 1 件目: 単発 / 多件の最初、候補 19 本。組 B = 2 件目以降: 途中 / 多件の最後、
    候補 24 本)を作り、**前半 228 日だけ**で候補ごとの分位・分かれ方の数の表を出す
    (表は前半だけ)。F5 は 1 件目で定義上 0 なので組 A の候補にしない(F3 と同じ扱い)。
  - 前半だけから実物読み 120 件(組 A 60 + 組 B 60)を乱数(種 20260920、
    1 日 1 件まで)で抜き、候補の値・直前 60 秒の清算・1 秒刻みの値段を markdown にする。

**探索段なので判定語を 1 つも書かない。`paper_logs/` は開かない。**
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import gzip
import importlib.util
import json
import math
import random
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

_spec_sc = importlib.util.spec_from_file_location(
    "o3c_signal_continue", _HERE / "o3c_signal_continue.py")
sc = importlib.util.module_from_spec(_spec_sc)
assert _spec_sc.loader is not None
_spec_sc.loader.exec_module(sc)

ex5 = sc.ex5
base = sc.base

REPO_ROOT = _HERE.parent
NAN = float("nan")

DEFAULT_DATA_ROOT = REPO_ROOT / "backtest_data" / "binance_cm_o3c_20260913"
DEFAULT_ROWS_PRINTS = (REPO_ROOT / "backtest_data" / "o3c_signal_explore5_20260920"
                       / "rows_prints.csv.gz")
DEFAULT_ROWS_CONTINUE = (REPO_ROOT / "backtest_data" / "o3c_signal_continue_20260920"
                         / "rows_continue.csv.gz")
DEFAULT_OUT = REPO_ROOT / "backtest_data" / "o3c_signal_materials_20260920"
DEFAULT_PROBE_MD = REPO_ROOT / "docs" / "DATA" / "probes" / "20260920_o3c_materials_read.md"

check_no_banned = sc.check_no_banned
BANNED_WORDS = sc.BANNED_WORDS

# ---------------------------------------------------------------------------
# 固定値(委任文・設計。変えるときは報告に列挙する)
# ---------------------------------------------------------------------------
BURST_GAP_MS = sc.BURST_GAP_MS               # 60_000。連鎖(ts 基準)と同じ閾値
STALENESS_MS = sc.STALENESS_MS               # 300_000
NODE_WINDOW_MS = int(ex5.W_HOURS * 3600 * 1000)   # 8h(既存 5 と同じ窓。設計に無い判断)
NODE_STEP = base.log_step(ex5.BIN_PCT)            # 既存 5 と同じビン幅(0.1%)
A4_WINDOW_MS = 5_000
A6_WINDOW_MS = 60_000
A9_WINDOW_MS = 60_000
C4_SHORT_MS = 5 * 60_000
C4_LONG_MS = 3_600_000
R1_WINDOW_MS = 60_000                        # R1(吸収、戻りの大きさ、直前60秒、全位置)
F5_WINDOW_MS = 10_000                        # F5(燃料、直前10秒の同じ側清算、組Bだけ)
BACK_MS = NODE_WINDOW_MS + STALENESS_MS      # 5'(8h の出来高プロファイル)+ C4(1h)を覆う
FWD_MS = 0                                   # 材料はラベルを使わないので未来は要らない
PROBE_SEED = 20260920
PROBE_N_EACH = 30                            # 組 A: 単発 30 + 多件の最初 30、組 B: 途中 30 + 多件の最後 30
PROBE_PRE_SEC = 60

MAT_COL = sc.MAT_COL                          # 既存材料の列名
HOUR_BAND_ORDER = {name: i for i, (name, _lo, _hi) in enumerate(sc.HOUR_BANDS)}
EXIST_NUMS = [n for n in sc.MAT_NUMS if n not in (4, 5)]   # 12(既存13 = これ + 5')
assert EXIST_NUMS == [1, 2, 3, 6, 8, 9, 10, 11, 12, 13, 14, 15]

CAND_NAMES = ["1", "2", "3", "5p", "6", "8", "9", "10", "11", "12", "13", "14", "15",
              "F3", "F4", "A3", "A4", "A5", "A6", "A9", "C3", "C4", "R1", "F5"]
# 組 A(1 件目)では欠測(F3・F4・A3・A5)/ 定義上 0 で測らない(F5、設計 §5.4)ので
# 組 A の候補にしない。R1 は「全位置で定義」なので組 A に含める。
CHAIN_INNER = {"F3", "F4", "A3", "A5", "F5"}
CAND_GROUP_A = [c for c in CAND_NAMES if c not in CHAIN_INNER]
assert len(CAND_NAMES) == 24 and len(CAND_GROUP_A) == 19

CHUNK_HEADER = (["print_id", "day", "side", "half", "ts_ms", "bundle_id",
                "bundle_pos", "bundle_pos_single", "group", "pos_label"]
               + [f"cand_{c}" for c in CAND_NAMES] + ["cand_A9_count"])


def _num(d: dict, key: str, v, nd: int = 6) -> None:
    d[key] = sc._fmt(v, nd)


# ===========================================================================
# 1. 連鎖(ts 基準)の累計想定元本、側別の接頭和(A9)
# ===========================================================================
def build_chain_cum_notional(pc: "sc.PrintsCSV") -> np.ndarray:
    """側ごとに時刻順で辿り、直前との gap が 60 秒以内なら足し込む累計(自分を含む)。

    `same_side_neighbors` の `burst_start_ts`(同じ閾値 `BURST_GAP_MS`)と整合する
    (1 件目 = 連鎖の開始 = burst_start_ts[i] == ts[i])。
    """
    n = pc.n
    cum = np.zeros(n, dtype=np.float64)
    for _s, idx in pc.side_order.items():
        ts = pc.ts[idx]
        notional = pc.notional[idx]
        m = ts.size
        vals = np.zeros(m, dtype=np.float64)
        running = 0.0
        for j in range(m):
            if j > 0 and (ts[j] - ts[j - 1]) <= BURST_GAP_MS:
                running += notional[j]
            else:
                running = notional[j]
            vals[j] = running
        cum[idx] = vals
    return cum


def build_side_prefix(pc: "sc.PrintsCSV") -> dict:
    """側ごとの ts(昇順)と想定元本の接頭和(A9 の反対側 60 秒合計を O(log n) で引く)。"""
    out = {}
    for s, idx in pc.side_order.items():
        ts_s = pc.ts[idx]
        notional_s = pc.notional[idx]
        cum = np.concatenate([[0.0], np.cumsum(notional_s)])
        out[s] = (ts_s, cum)
    return out


def opposite_side_window_sum(pc: "sc.PrintsCSV", i: int, window_ms: int,
                             side_prefix: dict):
    side = str(pc.side[i])
    ts = int(pc.ts[i])
    opp = {"BUY": "SELL", "SELL": "BUY"}.get(side)
    if opp is None or opp not in side_prefix:
        return NAN, NAN
    ts_s, cum = side_prefix[opp]
    lo, hi = ts - window_ms, ts
    i0 = int(np.searchsorted(ts_s, lo, side="left"))
    i1 = int(np.searchsorted(ts_s, hi, side="left"))
    cnt = i1 - i0
    if cnt <= 0:
        return 0.0, 0
    return float(cum[i1] - cum[i0]), int(cnt)


def same_side_window_sum(pc: "sc.PrintsCSV", i: int, window_ms: int, side_prefix: dict):
    """F5: `[ts − window_ms, ts − 1]` の**同じ側**の想定元本の合計(自分を含まない)。

    `hi = ts` に `searchsorted(..., side="left")` を使うことで、自分自身(ts に
    ちょうど一致する行)を除外する(`opposite_side_window_sum` と同じ規則)。
    同じ側の清算が無ければ 0(欠測にしない、設計 §5.4)。
    """
    side = str(pc.side[i])
    ts = int(pc.ts[i])
    if side not in side_prefix:
        return 0.0, 0
    ts_s, cum = side_prefix[side]
    lo, hi = ts - window_ms, ts
    i0 = int(np.searchsorted(ts_s, lo, side="left"))
    i1 = int(np.searchsorted(ts_s, hi, side="left"))
    cnt = i1 - i0
    if cnt <= 0:
        return 0.0, 0
    return float(cum[i1] - cum[i0]), int(cnt)


# ===========================================================================
# 2. ts 単発の窓の量(A4・A6・A9・C4)
# ===========================================================================
def same_dir_qty_window(times, qtys, maker, ts_ms: int, side: str, window_ms: int):
    if times is None or times.size == 0:
        return NAN
    lo, hi = ts_ms - window_ms, ts_ms
    i0 = int(np.searchsorted(times, lo, side="left"))
    i1 = int(np.searchsorted(times, hi, side="left"))
    if i1 <= i0:
        return NAN
    q, mk = qtys[i0:i1], maker[i0:i1]
    if side == "BUY":
        return float(q[~mk].sum())      # is_buyer_maker == False -> 買い taker
    if side == "SELL":
        return float(q[mk].sum())       # is_buyer_maker == True -> 売り taker
    return NAN


def last_extreme_age_s(times, prices, ts_ms: int, sign: float, window_ms: int):
    if times is None or times.size == 0 or sign != sign:
        return NAN
    lo, hi = ts_ms - window_ms, ts_ms
    i0 = int(np.searchsorted(times, lo, side="left"))
    i1 = int(np.searchsorted(times, hi, side="left"))
    if i1 <= i0:
        return NAN
    seg_t = times[i0:i1]
    val = sign * prices[i0:i1]
    run_max = np.maximum.accumulate(val)
    new_max = np.empty(val.size, dtype=bool)
    new_max[0] = True
    new_max[1:] = val[1:] > run_max[:-1]
    last_idx = int(np.nonzero(new_max)[0][-1])
    return (ts_ms - int(seg_t[last_idx])) / 1000.0


def realized_var_bp2(times, prices, ts_ms: int, window_ms: int):
    if times is None or times.size == 0:
        return NAN
    lo, hi = ts_ms - window_ms, ts_ms
    i0 = int(np.searchsorted(times, lo, side="left"))
    i1 = int(np.searchsorted(times, hi, side="left"))
    seg = prices[i0:i1]
    if seg.size < 2:
        return NAN
    rets = np.diff(seg) / seg[:-1] * 1e4
    return float(np.sum(rets * rets))


# ===========================================================================
# 3. 5'(建玉ノード、先だけ)と C3(その日の極値)— 日ごとに一括計算(効率のため)
# ===========================================================================
def node_ahead_bp_batch(times, prices, qtys, ts_arr, p_ref_arr, sign_arr,
                        window_ms=NODE_WINDOW_MS, step=NODE_STEP):
    """`ts_arr`(昇順)ごとに、直近 `window_ms` の出来高プロファイルのノード
    (上位 10%、既存 5 と同じ決め方)のうち `sign` の向きに「先」にあるものの中で
    最も近いものまでの距離(bp、正)。先に無ければ NaN。

    `o3c_reaction.profile_columns` と同じスライディング窓(lo/hi ポインタ)で
    日ごとに 1 回だけ通す(52,000 件を毎回 0 から作ると遅いため)。
    """
    n = len(ts_arr)
    out = np.full(n, NAN)
    if times.size == 0 or n == 0:
        return out
    bins = base.bin_index_array(prices, step)
    gmin = int(bins.min())
    rel_all = (bins - gmin).astype(np.int64)
    width = int(rel_all.max()) + 1
    acc = np.zeros(width, dtype=np.float64)
    cnt = np.zeros(width, dtype=np.int64)
    lo_p = hi_p = 0
    n_trades = times.size
    for i in range(n):
        t = int(ts_arr[i])
        while hi_p < n_trades and times[hi_p] < t:
            acc[rel_all[hi_p]] += qtys[hi_p]
            cnt[rel_all[hi_p]] += 1
            hi_p += 1
        left = t - window_ms
        while lo_p < hi_p and times[lo_p] < left:
            acc[rel_all[lo_p]] -= qtys[lo_p]
            cnt[rel_all[lo_p]] -= 1
            lo_p += 1
        if lo_p >= hi_p:
            continue
        nz = np.nonzero(cnt)[0]
        if nz.size == 0:
            continue
        r0, r1 = int(nz[0]), int(nz[-1])
        sub = acc[r0:r1 + 1].copy()
        sub_c = cnt[r0:r1 + 1]
        sub[sub_c == 0] = 0.0
        w = sub.size
        k = base._ceil_tenth(w)
        idxs = np.arange(w)
        node_rel = np.lexsort((idxs, -sub))[:k]
        p_ref = p_ref_arr[i]
        sign = sign_arr[i]
        if not (p_ref == p_ref and p_ref > 0 and sign == sign):
            continue
        centers = base.bin_center_price(node_rel + r0 + gmin, step)
        d = sign * (centers - p_ref)
        ahead = d > 0
        if not bool(ahead.any()):
            continue
        cand_rel = node_rel[ahead]
        cand_centers = centers[ahead]
        dist = np.abs(cand_centers - p_ref)
        order = np.lexsort((cand_rel, dist))
        out[i] = float(dist[order[0]] / p_ref * 1e4)
    return out


def day_extremes_batch(times, prices, ts_arr, day_start_ms: int):
    """その日の 00:00 から(`ts_arr` の各時刻の直前まで)の価格の running max / min。

    C3(その日の清算の向きの極値からの距離)を O(日の約定数) で出すための下ごしらえ。
    """
    n = len(ts_arr)
    day_max = np.full(n, NAN)
    day_min = np.full(n, NAN)
    if times.size == 0 or n == 0:
        return day_max, day_min
    hi_p = 0
    n_trades = times.size
    cur_max, cur_min = -math.inf, math.inf
    have = False
    for i in range(n):
        t = int(ts_arr[i])
        while hi_p < n_trades and times[hi_p] < t:
            if times[hi_p] >= day_start_ms:
                p = float(prices[hi_p])
                if p > cur_max:
                    cur_max = p
                if p < cur_min:
                    cur_min = p
                have = True
            hi_p += 1
        if have:
            day_max[i] = cur_max
            day_min[i] = cur_min
    return day_max, day_min


# ===========================================================================
# 4. プリント 1 件ぶんの新規 9 本(F3・F4・A3・A4・A5・A6・A9・C3・C4)
# ===========================================================================
def compute_new_candidates(pc: "sc.PrintsCSV", nb: dict, i: int, times, prices, qtys,
                           maker, t_oi, oi_lvl, chain_cum: np.ndarray, side_prefix: dict,
                           p_pre: float, day_max: float, day_min: float) -> dict:
    ts = int(pc.ts[i])
    side = str(pc.side[i])
    s = float(pc.sign[i])
    ok_pre = p_pre == p_pre

    burst_start_ts = int(nb["burst_start_ts"][i])
    chain_first = burst_start_ts == ts
    prev1_ts = int(nb["prev1_ts"][i])

    out: dict = {}

    f3 = float(chain_cum[i])
    out["F3"] = NAN if chain_first else f3

    if chain_first:
        out["F4"] = NAN
    else:
        oi_start = sc.latest_at_or_before(t_oi, oi_lvl, burst_start_ts)
        oi_now = sc.latest_at_or_before(t_oi, oi_lvl, ts)
        out["F4"] = ((oi_now - oi_start) if (oi_start == oi_start and oi_now == oi_now)
                     else NAN)

    if chain_first or not ok_pre:
        out["A3"] = NAN
    else:
        p_start, _t = sc.price_at_or_before(times, prices, burst_start_ts - 1)
        if p_start == p_start and p_start > 0 and f3 == f3 and f3 > 0:
            move_bp = s * (p_pre - p_start) / p_start * 1e4
            out["A3"] = move_bp / f3
        else:
            out["A3"] = NAN

    if not ok_pre:
        out["A4"] = NAN
    else:
        p5, _t = sc.price_at_or_before(times, prices, ts - A4_WINDOW_MS)
        move5 = (s * (p_pre - p5) / p5 * 1e4) if (p5 == p5 and p5 > 0) else NAN
        qty5 = same_dir_qty_window(times, qtys, maker, ts, side, A4_WINDOW_MS)
        out["A4"] = (move5 / qty5 if (move5 == move5 and qty5 == qty5 and qty5 > 0)
                    else NAN)

    if chain_first or prev1_ts < 0 or not ok_pre:
        out["A5"] = NAN
    else:
        p_prev_pre, _t = sc.price_at_or_before(times, prices, prev1_ts - 1)
        if p_prev_pre == p_prev_pre and p_prev_pre > 0:
            out["A5"] = sc.path_extreme_bp(times, prices, prev1_ts - 1, ts - 1,
                                           p_prev_pre, -s)
        else:
            out["A5"] = NAN

    out["A6"] = last_extreme_age_s(times, prices, ts, s, A6_WINDOW_MS)

    a9_amt, a9_cnt = opposite_side_window_sum(pc, i, A9_WINDOW_MS, side_prefix)
    out["A9"] = a9_amt
    out["A9_count"] = a9_cnt

    if not ok_pre:
        out["C3"] = NAN
    else:
        extreme = day_max if side == "BUY" else day_min
        out["C3"] = (s * (extreme - p_pre) / p_pre * 1e4
                    if (extreme == extreme and extreme > 0) else NAN)

    rv5 = realized_var_bp2(times, prices, ts, C4_SHORT_MS)
    rv1h = realized_var_bp2(times, prices, ts, C4_LONG_MS)
    out["C4"] = (rv5 / rv1h) if (rv5 == rv5 and rv1h == rv1h and rv1h > 0) else NAN

    # R1(吸収、戻りの大きさ): 直前60秒 [ts-60,000, ts-1] の約定の価格の、清算の
    # 向き(s、-s ではない)の最大 sign×(p-p_pre)/p_pre×1e4。全位置で定義(1件目でも)。
    # 約定が無ければ欠測。p_pre 自身が窓内にあるので、定義できるときは必ず 0 以上
    # (p_pre が 60 秒の極値なら 0、先まで行って戻っていれば正)。
    out["R1"] = (sc.path_extreme_bp(times, prices, ts - R1_WINDOW_MS - 1, ts - 1,
                                    p_pre, s)
                if ok_pre else NAN)

    # F5(燃料): 直前10秒 [ts-10,000, ts-1] の同じ側の清算(自分を含まない)の
    # 想定元本の合計。無ければ 0(欠測にしない)。1件目でも 0(組 A の表には入れない)。
    f5_amt, _f5_cnt = same_side_window_sum(pc, i, F5_WINDOW_MS, side_prefix)
    out["F5"] = f5_amt

    return out


# ===========================================================================
# 5. 事後の位置 -> 組・表示名
# ===========================================================================
def pos_and_group(bundle_pos, bundle_pos_single):
    bp = str(bundle_pos)
    single = int(bundle_pos_single) if bundle_pos_single == bundle_pos_single else 0
    if bp == "束の外":
        return "束の外", ""
    if bp == "最初" and single == 0:
        return "多件の最初", "A"
    if bp == "最後" and single == 1:
        return "単発", "A"
    if bp == "途中":
        return "途中", "B"
    if bp == "最後" and single == 0:
        return "多件の最後", "B"
    return "不明", ""


# ===========================================================================
# 6. 段 1: 日ごとの chunk(再開できる)
# ===========================================================================
def run_stage_rows(out_dir: Path, days: list, half_of: dict, pc: "sc.PrintsCSV",
                   nb: dict, chain_cum: np.ndarray, side_prefix: dict,
                   exist_vals: dict, mat6_arr, bundle_pos_arr, bundle_single_arr,
                   data_root: Path, progress_every: int) -> dict:
    work = out_dir / "chunks"
    work.mkdir(parents=True, exist_ok=True)
    trade_cache: dict = {}
    metrics_cache: dict = {}
    missing_agg: set = set()
    t0 = time.time()
    for n_done, day in enumerate(days, start=1):
        cp = work / f"{day}.csv.gz"
        if cp.exists():
            continue
        sel = pc.by_day.get(day, np.zeros(0, dtype=int))
        times, prices, qtys, miss, _need = sc.load_window5(data_root, day, trade_cache,
                                                            BACK_MS, FWD_MS)
        missing_agg |= set(miss)
        maker = None
        if sel.size:
            maker = sc._load_window_maker(data_root, day, trade_cache, BACK_MS, FWD_MS)
        t_oi, oi_lvl, _tls = sc.load_metrics_window(data_root, day, metrics_cache)
        rows = []
        if sel.size:
            ts_arr = pc.ts[sel]
            sign_arr = pc.sign[sel]
            p_pre_arr = np.array(
                [sc.price_at_or_before(times, prices, int(t) - 1)[0] for t in ts_arr])
            cand5p_arr = node_ahead_bp_batch(times, prices, qtys, ts_arr, p_pre_arr,
                                             sign_arr)
            day0 = sc.day_start_ms(day)
            day_max_arr, day_min_arr = day_extremes_batch(times, prices, ts_arr, day0)
            for j, i in enumerate(sel.tolist()):
                side = str(pc.side[i])
                newc = compute_new_candidates(
                    pc, nb, i, times, prices, qtys, maker, t_oi, oi_lvl, chain_cum,
                    side_prefix, float(p_pre_arr[j]), float(day_max_arr[j]),
                    float(day_min_arr[j]))
                pos_label, group = pos_and_group(bundle_pos_arr[i], bundle_single_arr[i])
                d = {c: "" for c in CHUNK_HEADER}
                d["print_id"] = str(pc.print_id[i])
                d["day"] = day
                d["side"] = side
                d["half"] = half_of[day]
                d["ts_ms"] = int(pc.ts[i])
                d["bundle_id"] = str(pc.bundle_id[i])
                d["bundle_pos"] = str(bundle_pos_arr[i])
                d["bundle_pos_single"] = (int(bundle_single_arr[i])
                                          if bundle_single_arr[i] == bundle_single_arr[i]
                                          else 0)
                d["group"] = group
                d["pos_label"] = pos_label
                for n in EXIST_NUMS:
                    if n == 6:
                        band = mat6_arr[i]
                        d["cand_6"] = HOUR_BAND_ORDER.get(band, "")
                    else:
                        _num(d, f"cand_{n}", exist_vals[n][i])
                _num(d, "cand_5p", float(cand5p_arr[j]))
                for k in ("F3", "F4", "A3", "A4", "A5", "A6", "A9", "C3", "C4",
                         "R1", "F5"):
                    _num(d, f"cand_{k}", newc[k])
                d["cand_A9_count"] = (int(newc["A9_count"])
                                      if newc["A9_count"] == newc["A9_count"] else "")
                rows.append([d[c] for c in CHUNK_HEADER])
        tmp = work / f".{day}.part"
        with sc.gz_open_w(tmp) as fh:
            w = csv.writer(fh)
            w.writerow(CHUNK_HEADER)
            w.writerows(rows)
        tmp.replace(cp)
        if n_done % progress_every == 0:
            print(f"  段1 {n_done}/{len(days)} 日 ({day}) 経過 "
                 f"{time.time() - t0:.0f}s", flush=True)
    return {"agg_days_missing": sorted(missing_agg)}


def concat_rows(out_dir: Path, days: list) -> Path:
    out_p = out_dir / "rows_materials.csv.gz"
    with sc.gz_open_w(Path(str(out_p) + ".part")) as fh:
        w = csv.writer(fh)
        w.writerow(CHUNK_HEADER)
        for day in days:
            cp = out_dir / "chunks" / f"{day}.csv.gz"
            if not cp.exists():
                continue
            with gzip.open(cp, "rt", encoding="utf-8") as rf:
                r = csv.reader(rf)
                header = next(r)
                assert header == CHUNK_HEADER
                for row in r:
                    w.writerow(row)
    Path(str(out_p) + ".part").replace(out_p)
    return out_p


def drop_chunks(out_dir: Path) -> int:
    work = out_dir / "chunks"
    n = 0
    if work.exists():
        for p in work.glob("*.csv.gz"):
            p.unlink()
            n += 1
        try:
            work.rmdir()
        except OSError:
            pass
    return n


# ===========================================================================
# 7. 分かれ方の数(順位、同値 0.5)
# ===========================================================================
def rankdata_avg(x: np.ndarray) -> np.ndarray:
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(len(x), dtype=np.float64)
    sx = x[order]
    n = len(x)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and sx[j + 1] == sx[i]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        ranks[order[i:j + 1]] = avg_rank
        i = j + 1
    return ranks


def separation_prob(stop_vals: np.ndarray, cont_vals: np.ndarray):
    """止まる側から 1 件・続く側から 1 件を無作為に取ったとき、止まる側の値の方が
    大きい確率(順位だけで決まる。同値は 0.5)。欠測は両側から除いた後の値で計算。"""
    stop_vals = np.asarray(stop_vals, dtype=float)
    cont_vals = np.asarray(cont_vals, dtype=float)
    stop_vals = stop_vals[np.isfinite(stop_vals)]
    cont_vals = cont_vals[np.isfinite(cont_vals)]
    n1, n2 = stop_vals.size, cont_vals.size
    if n1 == 0 or n2 == 0:
        return NAN
    combined = np.concatenate([stop_vals, cont_vals])
    ranks = rankdata_avg(combined)
    r1 = float(ranks[:n1].sum())
    u1 = r1 - n1 * (n1 + 1) / 2.0
    return u1 / (n1 * n2)


QS = [10, 25, 50, 75, 90]


def screen_rows(df: pd.DataFrame, group: str, cands: list, stop_label: str,
                cont_label: str) -> list:
    rows = []
    stop_df = df[df["pos_label"] == stop_label]
    cont_df = df[df["pos_label"] == cont_label]
    for c in cands:
        col = f"cand_{c}"
        sv = pd.to_numeric(stop_df[col], errors="coerce").to_numpy(float)
        cv = pd.to_numeric(cont_df[col], errors="coerce").to_numpy(float)
        n_s, n_c = sv.size, cv.size
        miss_s = float(np.mean(~np.isfinite(sv))) if n_s else NAN
        miss_c = float(np.mean(~np.isfinite(cv))) if n_c else NAN
        qs_s = sc.quantiles(sv, QS)
        qs_c = sc.quantiles(cv, QS)
        sep = separation_prob(sv, cv)
        row = {"候補": c, "組": group,
              f"{stop_label}_n": n_s, f"{stop_label}_欠測割合": miss_s}
        for q, v in zip(QS, qs_s):
            row[f"{stop_label}_p{q}"] = v
        row[f"{cont_label}_n"] = n_c
        row[f"{cont_label}_欠測割合"] = miss_c
        for q, v in zip(QS, qs_c):
            row[f"{cont_label}_p{q}"] = v
        row["分かれ方の数"] = sep
        row["|分かれ方-0.5|"] = abs(sep - 0.5) if sep == sep else NAN
        rows.append(row)
    rows.sort(key=lambda r: (r["|分かれ方-0.5|"] if r["|分かれ方-0.5|"] == r["|分かれ方-0.5|"]
                            else -1.0), reverse=True)
    return rows


# ===========================================================================
# 8. 実物読み(前半だけ、乱数の種 20260920、1 日 1 件まで)
# ===========================================================================
def select_probes(df_front: pd.DataFrame) -> list:
    buckets = [("A", "単発"), ("A", "多件の最初"), ("B", "途中"), ("B", "多件の最後")]
    rng = random.Random(PROBE_SEED)
    used_days: set = set()
    picked: list = []
    for group, pos_label in buckets:
        cand = (df_front[(df_front["group"] == group)
                        & (df_front["pos_label"] == pos_label)]
               .sort_values(["day", "print_id"]).to_dict("records"))
        by_day: dict = {}
        for r in cand:
            by_day.setdefault(r["day"], []).append(r)
        days_avail = sorted(by_day.keys())
        rng.shuffle(days_avail)
        got = 0
        for d in days_avail:
            if got >= PROBE_N_EACH:
                break
            if d in used_days:
                continue
            r = rng.choice(by_day[d])
            picked.append({**r, "bucket": f"組{group}:{pos_label}"})
            used_days.add(d)
            got += 1
        if got < PROBE_N_EACH:
            raise SystemExit(f"[止め] 組{group}:{pos_label} が {got}/{PROBE_N_EACH} "
                            "本しか(日の重複無しで)取れない")
    return picked


def build_probe_markdown(picked: list, pc: "sc.PrintsCSV", data_root: Path) -> str:
    trade_cache: dict = {}
    lines = ["# 材料 24 本の実物読み(O3C SIGNAL、2026-09-20)", "",
            "委任文: `docs/DATA/delegations/20260920_o3c_signal_materials2_prompt.md`"
            "(前回 `..._materials_prompt.md` の 120 件と同じ抽出に R1・F5 の行を足した版)。",
            "スクリプト: `scripts/o3c_signal_materials.py`"
            f"(乱数の種 {PROBE_SEED}、前半だけ、日を跨いで重ならないよう 1 日 1 件まで)。",
            f"候補 24 本の並び: {', '.join(CAND_NAMES)}。",
            "値段の bp は `(価格 − 直前約定 p_pre) / p_pre × 1e4`、清算の向きが正、"
            "`sec=0` 側(ts 直前)が基準。", ""]
    print_id_to_idx = {pid: i for i, pid in enumerate(pc.print_id.tolist())}
    for n, r in enumerate(picked, start=1):
        pid = r["print_id"]
        i = print_id_to_idx[pid]
        day = r["day"]
        ts = int(pc.ts[i])
        side = str(pc.side[i])
        s = float(pc.sign[i])
        times, prices, qtys, _miss, _need = sc.load_window5(data_root, day, trade_cache,
                                                             BACK_MS, 0)
        p_pre, _t = sc.price_at_or_before(times, prices, ts - 1)
        lines.append(f"## {n}. {r['bucket']} — {pid}({day} {side}、"
                     f"ts_ms={ts}、p_pre={sc._fmt(p_pre, 2)})")
        lines.append("")
        # --- 候補の値 ---------------------------------------------------
        lines.append("候補の値:")
        lines.append("")
        lines.append("| 候補 | 値 |")
        lines.append("|---|---|")
        for c in CAND_NAMES:
            col = f"cand_{c}"
            v = r.get(col, "")
            lines.append(f"| {c} | {v} |")
        lines.append("")
        # --- 直前 60 秒の清算 ---------------------------------------------
        lo, hi = ts - PROBE_PRE_SEC * 1000, ts
        i0 = int(np.searchsorted(pc.ts, lo, side="left"))
        i1 = int(np.searchsorted(pc.ts, hi, side="left"))
        liq_rows = []
        for k in range(i0, i1):
            rel_s = (int(pc.ts[k]) - ts) / 1000.0
            liq_rows.append((round(rel_s, 3), str(pc.side[k]), float(pc.notional[k])))
        liq_rows.sort(key=lambda x: x[0])
        lines.append(f"直前 {PROBE_PRE_SEC} 秒の清算({len(liq_rows)} 件、自分自身"
                     "〈ts=0〉は含まない):")
        lines.append("")
        if liq_rows:
            lines.append("| 相対秒 | 側 | 想定元本 |")
            lines.append("|---|---|---|")
            for rel_s, sd, notional in liq_rows:
                lines.append(f"| {rel_s:+.3f} | {sd} | {notional:.2f} |")
        else:
            lines.append("(無し)")
        lines.append("")
        # --- 直前 60 秒の 1 秒刻みの値段(bp) -------------------------------
        pts = []
        for off in range(PROBE_PRE_SEC, 0, -1):
            t = ts - off * 1000
            px, _tt = sc.price_at_or_before(times, prices, t)
            if px == px and p_pre == p_pre and p_pre > 0:
                bp = s * (px - p_pre) / p_pre * 1e4
            else:
                bp = NAN
            pts.append((-off, bp))
        lines.append(f"直前 {PROBE_PRE_SEC} 秒の 1 秒刻みの値段(bp、清算の向きが正、"
                     "`at_or_before` で埋める):")
        lines.append("")
        lines.append("```")
        lines.append(", ".join(f"{sec}:{sc._fmt(bp, 3)}" for sec, bp in pts))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


# ===========================================================================
# main
# ===========================================================================
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="O3C SIGNAL 材料の選定")
    ap.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    ap.add_argument("--rows-prints", type=Path, default=DEFAULT_ROWS_PRINTS)
    ap.add_argument("--rows-continue", type=Path, default=DEFAULT_ROWS_CONTINUE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--probe-md", type=Path, default=DEFAULT_PROBE_MD)
    ap.add_argument("--stage", choices=("rows", "tables", "resummarize", "all"),
                    default="all")
    ap.add_argument("--limit-days", type=int, default=0)
    ap.add_argument("--progress-every", type=int, default=20)
    ap.add_argument("--keep-chunks", action="store_true")
    ap.add_argument("--skip-probes", action="store_true")
    a = ap.parse_args(argv)

    t0 = time.time()
    a.out.mkdir(parents=True, exist_ok=True)

    pc = sc.PrintsCSV(a.rows_prints)
    days = sorted(pc.by_day.keys())
    if a.limit_days:
        days = days[: a.limit_days]
    half_point = len(days) // 2
    days1, days2 = days[:half_point], days[half_point:]
    half_of = {d: "前半" for d in days1}
    half_of.update({d: "後半" for d in days2})
    print(f"日数 {len(days)}(前半 {len(days1)} / 後半 {len(days2)})、"
         f"プリント {pc.n} 件", flush=True)

    nb = sc.same_side_neighbors(pc)
    chain_cum = build_chain_cum_notional(pc)
    side_prefix = build_side_prefix(pc)

    # --- 既存 12 本(5・4 を除く)+ bundle_pos を print_id で突き合わせる ------
    cont_df = pd.read_csv(a.rows_continue, dtype={"print_id": str, "day": str})
    cont_df = cont_df[cont_df["kind"] == "print"].reset_index(drop=True)
    prints_df = pd.read_csv(a.rows_prints, dtype={"print_id": str, "day": str})
    prints_df = prints_df[prints_df["kind"] == "print"].reset_index(drop=True)

    pc_df = pd.DataFrame({"print_id": pc.print_id, "idx": np.arange(pc.n)})
    merged = pc_df.merge(
        cont_df[["print_id"] + [MAT_COL[n] for n in EXIST_NUMS]],
        on="print_id", how="left")
    merged = merged.merge(
        prints_df[["print_id", "bundle_pos", "bundle_pos_single"]],
        on="print_id", how="left")
    merged = merged.sort_values("idx").reset_index(drop=True)
    assert merged.shape[0] == pc.n
    assert bool((merged["idx"].to_numpy() == np.arange(pc.n)).all())

    exist_vals = {}
    for n in EXIST_NUMS:
        if n == 6:
            continue
        exist_vals[n] = pd.to_numeric(merged[MAT_COL[n]], errors="coerce").to_numpy(float)
    mat6_arr = merged[MAT_COL[6]].to_numpy(object)
    bundle_pos_arr = merged["bundle_pos"].to_numpy(object)
    bundle_single_arr = pd.to_numeric(merged["bundle_pos_single"],
                                      errors="coerce").to_numpy(float)

    if a.stage in ("rows", "all"):
        note1 = run_stage_rows(a.out, days, half_of, pc, nb, chain_cum, side_prefix,
                              exist_vals, mat6_arr, bundle_pos_arr, bundle_single_arr,
                              a.data_root, a.progress_every)
        (a.out / "stage_notes.json").write_text(json.dumps(note1, ensure_ascii=False,
                                                            indent=2))
    if a.stage == "rows":
        return 0

    if a.stage == "resummarize":
        # 既に chunks を消した後、summary.json だけを rows_materials.csv.gz から
        # 作り直す(入力を書き換えない・chunk を作り直さない)。
        rows_path = a.out / "rows_materials.csv.gz"
    else:
        rows_path = concat_rows(a.out, days)
    df = pd.read_csv(rows_path, dtype={"print_id": str, "day": str, "bundle_pos": str,
                                       "group": str, "pos_label": str})
    n_rows = int(df.shape[0])
    print(f"rows_materials 行数 = {n_rows}", flush=True)

    df_front = df[df["half"] == "前半"].reset_index(drop=True)
    df_front_ab = df_front[df_front["group"].isin(["A", "B"])].reset_index(drop=True)

    screen_a = screen_rows(df_front_ab, "A", CAND_GROUP_A, "単発", "多件の最初")
    screen_b = screen_rows(df_front_ab, "B", CAND_NAMES, "途中", "多件の最後")
    sc.write_csv(a.out / "screen_A.csv", screen_a)
    sc.write_csv(a.out / "screen_B.csv", screen_b)

    # --- 実物読み(前半だけ) ------------------------------------------------
    old_summary = {}
    old_summary_p = a.out / "summary.json"
    if old_summary_p.exists():
        try:
            old_summary = json.loads(old_summary_p.read_text())
        except (json.JSONDecodeError, OSError):
            old_summary = {}
    probe_note = {}
    if not a.skip_probes:
        picked = select_probes(df_front_ab)
        probe_note["抽出件数"] = len(picked)
        probe_note["内訳"] = dict(Counter(r["bucket"] for r in picked))
        probe_md = build_probe_markdown(picked, pc, a.data_root)
        check_no_banned(probe_md, "materials_read.md")
        a.probe_md.parent.mkdir(parents=True, exist_ok=True)
        a.probe_md.write_text(probe_md)
    elif old_summary.get("実物読み"):
        # --stage resummarize --skip-probes: 前回の実測(実物読みは変えていない)を残す
        probe_note = old_summary["実物読み"]

    # --- tables.md ----------------------------------------------------------
    md = [f"# O3C SIGNAL 材料の選定の表({days[0]} 〜 {days[-1]}、{len(days)} 日、"
         "前半だけ)", "",
         "- 設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_MATERIALS_DESIGN_2026-09-20.md`",
         f"- 前半 {len(days1)} 日だけで表を作る(後半 {len(days2)} 日には触れない、"
         "境目は置かない)",
         f"- 組 A(1 件目: 単発 対 多件の最初、候補 {len(CAND_GROUP_A)} 本)/ "
         f"組 B(2 件目以降: 途中 対 多件の最後、候補 {len(CAND_NAMES)} 本)",
         "- 候補 6(時刻帯)は UTC 6 時間 × 4 帯を出現順(00–06→0 … 18–24→3)の整数に"
         "数値化して分位・分かれ方の数を計算した(設計に数値化の指定なし、報告 (5) 参照)",
         "- R1(吸収、直前60秒の戻りの大きさ、全位置)・F5(燃料、直前10秒の同じ側清算"
         "想定元本合計、組 B だけ)を設計 §5.4 に従って足した(既存 22 本の値は変えていない)",
         "", "## 組 A(|分かれ方 − 0.5| の降順)", "", sc.md_table(screen_a), "",
         "## 組 B(|分かれ方 − 0.5| の降順)", "", sc.md_table(screen_b), ""]
    mdtxt = "\n".join(md)
    check_no_banned(mdtxt, "tables.md")
    (a.out / "tables.md").write_text(mdtxt)
    n_cells = ex5.count_numeric_cells(mdtxt)

    n_group_a = int((df_front_ab["group"] == "A").sum())
    n_group_b = int((df_front_ab["group"] == "B").sum())
    n_pos = df_front_ab["pos_label"].value_counts().to_dict()

    # 候補ごとの欠測割合(全 52,000 行、両半期。F3・F4・A3・A5 は組 A〈1 件目〉が
    # 定義上すべて欠測になるので、その分だけ高く出るのは構造どおり — 報告 (3) 参照)
    miss_all = {}
    for c in CAND_NAMES:
        col = f"cand_{c}"
        v = pd.to_numeric(df[col], errors="coerce").to_numpy(float)
        miss_all[c] = float(np.mean(~np.isfinite(v)))

    def _md5(p: Path) -> str:
        return sc.md5_of(p) if p.exists() else ""

    summary = {
        "実行時刻(UTC)": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "経過秒": round(time.time() - t0, 1),
        "設計": "docs/PHASE2/O3C/SIGNAL/SIGNAL_MATERIALS_DESIGN_2026-09-20.md",
        "日数": {"前半": len(days1), "後半": len(days2), "合計": len(days)},
        "プリント数": {"前半": int((df['half'] == '前半').sum()),
                  "後半": int((df['half'] == '後半').sum()),
                  "合計": n_rows},
        "行数": n_rows,
        "候補の数": {"合計": len(CAND_NAMES), "組A": len(CAND_GROUP_A),
                "組B": len(CAND_NAMES)},
        "前半・束の外を除いた件数(組A+組B)": {"組A": n_group_a, "組B": n_group_b,
                                    "事後の位置ごと": n_pos},
        "表の行数": {"screen_A": len(screen_a), "screen_B": len(screen_b),
                "合計": len(screen_a) + len(screen_b)},
        "tables.md の数値セル数": n_cells,
        "tables.md の数え方": "`count_numeric_cells`(探索段 5・続く/止まると同じ数え方)",
        "候補ごとの欠測割合(全52,000行、両半期)": miss_all,
        "実物読み": probe_note,
        "連鎖(ts基準)の入力": {
            "BURST_GAP_MS": BURST_GAP_MS,
            "NODE_WINDOW_MS(5')": NODE_WINDOW_MS,
            "BACK_MS(読み込み窓)": BACK_MS,
        },
        "入力のMD5": {
            "rows_prints.csv.gz": _md5(a.rows_prints),
            "rows_continue.csv.gz": _md5(a.rows_continue),
        },
    }
    txt = json.dumps(summary, ensure_ascii=False, indent=2)
    check_no_banned(txt, "summary.json")
    (a.out / "summary.json").write_text(txt)

    if not a.keep_chunks:
        n_drop = drop_chunks(a.out)
        print(f"chunk の中間ファイルを {n_drop} 個消した", flush=True)

    names = ["rows_materials.csv.gz", "screen_A.csv", "screen_B.csv", "tables.md",
            "summary.json"]
    lines = []
    for n in names:
        p = a.out / n
        if not p.exists():
            continue
        if n.endswith((".csv", ".md", ".json")):
            check_no_banned(p.read_text(), n)
        lines.append(f"{sc.md5_of(p)}  {n}")
    if a.probe_md.exists():
        lines.append(f"{sc.md5_of(a.probe_md)}  {a.probe_md.relative_to(REPO_ROOT)}")
    (a.out / "MD5SUMS").write_text("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)
    print(f"完了 {time.time() - t0:.0f}s -> {a.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""清算を起点とした値動きの予測可能性 — **続く / 止まるの単位**の道具(2026-09-20)。

設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_CONTINUE_DESIGN_2026-09-20.md`
委任文: `docs/DATA/delegations/20260920_o3c_signal_continue_prompt.md`

**この道具がすること**
  - 母集団は探索段 5 の行データ `rows_prints.csv.gz` の `kind == "print"`(52,000 件)。
    ここから `ts・side・p0・t0_ms・notional・dist_node_bp・oi_covered・bundle_id` を取る。
  - 材料 1〜15(7 は無し、14 本)を **ts 以前の約定・清算・5 分値・資金調達率だけ**で
    計算し直す(p₀ は使わない)。探索段 5 の `compute_layers` を**再利用**して
    k・m(10)・m(60)・dist_node_bp を得る(材料 15・5 はここから)。
  - ラベル(続く、30/60/120 秒・同じ側の次のプリント)と「値段の続き」
    (t₀ から 60 秒以内に清算の向きへ 5bp 以上進むか、経路の最大値で判定)。
  - 前半 228 日で切り値・規則を作り、後半 228 日で的中率・損益を測る。
  - Q7: 清算の無い時刻の対照(材料 15・9 の前半 10 分位帯を合わせる)。
  - Jev はこの委任では**前半から層化無作為 200 件だけ**(下見)。後半には呼ばない。

**探索段なので判定語を 1 つも書かない。`paper_logs/` は開かない。**
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import gzip
import hashlib
import importlib.util
import json
import math
import random
import sys
import time
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import o3c_price_level_table as base  # noqa: E402
import o3c_oi_distance as oid  # noqa: E402

_spec5 = importlib.util.spec_from_file_location(
    "o3c_signal_explore5", _HERE / "o3c_signal_explore5.py")
ex5 = importlib.util.module_from_spec(_spec5)
assert _spec5.loader is not None
_spec5.loader.exec_module(ex5)

_spec_cr = importlib.util.spec_from_file_location(
    "o3c_cascade_read", _HERE.parent / "docs" / "DATA" / "probes"
    / "20260920_o3c_cascade_read.py")
cr = importlib.util.module_from_spec(_spec_cr)
assert _spec_cr.loader is not None
# cascade_read の main() は import 時に走らない(if __name__ ガード)ので安全
_spec_cr.loader.exec_module(cr)

REPO_ROOT = _HERE.parent
NAN = float("nan")

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from jev.client import JevClient, JevError  # noqa: E402

# ---------------------------------------------------------------------------
# 固定値(委任文・設計 §7。変えるときは報告に列挙する)
# ---------------------------------------------------------------------------
LABEL_SECONDS = (30, 60, 120)
LABEL_MAIN = 60
VALUE_CONT_BP = 5.0
ENTRY_DELAYS_S = (1, 3, 5)
HOLD_SECONDS = (30, 60, 300)
MAIN_ENTRY, MAIN_HOLD = 1, 60           # 主格子
STALENESS_MS = ex5.STALENESS_MS         # 300_000
N_BANDS = 10
SAME_SIDE_WINDOW_MS = 60_000
BURST_GAP_MS = 60_000                   # 材料 1 の「経過秒」用の連続判定
TRADE_COUNT_WINDOW_MS = 60_000
IMBALANCE_WINDOWS_MS = {"5s": 5_000, "30s": 30_000}
OI_WINDOW_HOURS = cr.W_HOURS            # 8h(cascade_read と同じ)
OI_SLOPE_WINDOW_MS = 3_600_000          # 材料 10: 直近 1 時間
RANGE_WINDOW_MS = 60_000                # 材料 11
Q7_GRID_STEP_MS = 10_000
Q7_NO_LIQ_WINDOW_MS = 15 * 60_000       # 前後 15 分
GRID_N = 8_640
MS_PER_DAY = 86_400_000
TICK = 0.1                              # BTCUSD_PERP の呼び値

REACT_SIGN = ex5.REACT_SIGN
import o3c_signal_explore2 as ex2  # noqa: E402
HOUR_BANDS = ex2.HOUR_BANDS

BANNED_WORDS = ("差あり", "検出されず", "陽性", "陰性", "有意", "支持", "棄却")

DEFAULT_DATA_ROOT = REPO_ROOT / "backtest_data" / "binance_cm_o3c_20260913"
DEFAULT_ROWS = (REPO_ROOT / "backtest_data" / "o3c_signal_explore5_20260920"
                / "rows_prints.csv.gz")
DEFAULT_OUT = REPO_ROOT / "backtest_data" / "o3c_signal_continue_20260920"

# 材料 1〜15(7 は無し)の変数名。設計 §5(jev_design の対照変数の順位表)の語と揃える。
MAT_VAR = {
    1: "same_side_count_60s_and_elapsed",
    2: "interval_ratio_last_two",
    3: "notional_and_ratio_to_previous",
    4: "move_since_cascade_start_and_bounce",
    5: "distance_to_liquidation_node",
    6: "time_of_day_band",
    8: "open_interest_mass_ahead",
    9: "taker_imbalance_5s",
    10: "oi_slope_and_funding",
    11: "notional_over_60s_range",
    12: "notional_over_max_recent_print",
    13: "taker_imbalance_trend",
    14: "trade_count_60s",
    15: "burst_ratio_10s_over_60s",
}
MAT_NUMS = list(MAT_VAR.keys())               # [1,2,3,4,5,6,8,9,...,15]
MAT_NUMS_CONT = [m for m in MAT_NUMS if m != 6]   # 10 分位で切れる材料(6 は時刻帯=カテゴリ)
MAT_COL = {n: f"mat{n}_{MAT_VAR[n]}" for n in MAT_NUMS}   # 主のスカラー列名


def check_no_banned(text: str, where: str) -> None:
    hit = [w for w in BANNED_WORDS if w in text]
    if hit:
        raise SystemExit(f"[止め] 判定語が出力に混ざっている({where}): {hit}")


def day_of_ms(ts_ms: int) -> str:
    return (_dt.datetime.fromtimestamp(int(ts_ms) / 1000, _dt.timezone.utc)
            .date().isoformat())


def day_start_ms(day: str) -> int:
    return ex5.ex3.day_start_ms(day)


def hour_band_of(ts_ms) -> str:
    h = (int(ts_ms) % MS_PER_DAY) // 3_600_000
    for name, lo, hi in HOUR_BANDS:
        if lo <= h < hi:
            return name
    return ""


idx_at_or_before = ex5.idx_at_or_before
idx_at_or_after = ex5.idx_at_or_after
quantiles = ex5.quantiles
mean_se_cluster = ex5.mean_se_cluster
day_equal_weight_mean = ex5.day_equal_weight_mean
gz_open_w = ex5.gz_open_w
md5_of = ex5.md5_of
write_csv = ex5.write_csv
md_table = ex5.md_table
band_of_m = ex5.band_of_m
band_bounds = ex5.band_bounds
bound_text = ex5.bound_text
_fmt = ex5._fmt
_f = ex5._f
count_numeric_cells = ex5.count_numeric_cells


# ===========================================================================
# 1. 母集団(探索段 5 の行データ)+ 側ごとの因果な近傍
# ===========================================================================
class PrintsCSV:
    """`rows_prints.csv.gz` の kind == print を読み、側ごとに時刻順へ並べる。

    材料 1・2・3・4・12 の「直前の同じ側」「経過秒」はここ(プリントの時刻列だけ)で
    引ける。約定は要らない。
    """

    def __init__(self, path: Path):
        cols = ["print_id", "day", "side", "ts_ms", "t0_ms", "p0", "notional",
                "dist_node_bp", "oi_covered", "bundle_id"]
        df = pd.read_csv(path, usecols=["kind"] + cols,
                          dtype={"bundle_id": str, "day": str, "print_id": str,
                                 "side": str})
        df = df[df["kind"] == "print"].reset_index(drop=True)
        df = df.sort_values(["ts_ms", "print_id"]).reset_index(drop=True)
        for c in ("ts_ms", "t0_ms"):
            df[c] = df[c].astype(np.int64)
        for c in ("p0", "notional", "dist_node_bp"):
            df[c] = pd.to_numeric(df[c], errors="coerce").astype(float)
        df["oi_covered"] = pd.to_numeric(df["oi_covered"], errors="coerce").fillna(0)
        self.df = df
        self.n = int(df.shape[0])
        self.ts = df["ts_ms"].to_numpy(np.int64)
        self.side = df["side"].to_numpy(object)
        self.p0 = df["p0"].to_numpy(float)
        self.notional = df["notional"].to_numpy(float)
        self.dist_node_bp = df["dist_node_bp"].to_numpy(float)
        self.oi_covered = df["oi_covered"].to_numpy(float)
        self.print_id = df["print_id"].to_numpy(object)
        self.day = df["day"].to_numpy(object)
        self.bundle_id = df["bundle_id"].to_numpy(object)
        self.sign = np.array([REACT_SIGN.get(s, NAN) for s in self.side.tolist()],
                              dtype=float)
        by_day: dict = defaultdict(list)
        for i, d in enumerate(self.day.tolist()):
            by_day[d].append(i)
        self.by_day = {d: np.array(v, dtype=int) for d, v in by_day.items()}
        self.side_order: dict = {}
        for s in ("SELL", "BUY"):
            idx = np.flatnonzero(self.side == s)
            idx = idx[np.argsort(self.ts[idx], kind="stable")]
            self.side_order[s] = idx
        self.pos_in_side = np.full(self.n, -1, dtype=int)
        for s, idx in self.side_order.items():
            self.pos_in_side[idx] = np.arange(idx.size)

    def all_ts_sorted(self):
        o = np.argsort(self.ts, kind="stable")
        return self.ts[o]


def same_side_neighbors(pc: PrintsCSV):
    """材料 1・2・3・4・12 の元になる「直前 1/2 件・経過秒・直近 60 秒の最大」を返す。"""
    n = pc.n
    prev1_ts = np.full(n, -1, dtype=np.int64)
    prev1_notional = np.full(n, NAN)
    prev1_p0 = np.full(n, NAN)
    prev2_ts = np.full(n, -1, dtype=np.int64)
    burst_start_ts = np.full(n, -1, dtype=np.int64)
    burst_start_p0 = np.full(n, NAN)
    count_60s = np.zeros(n, dtype=float)
    max_notional_60s = np.full(n, NAN)

    for s, idx in pc.side_order.items():
        ts = pc.ts[idx]
        p0 = pc.p0[idx]
        notional = pc.notional[idx]
        m = ts.size
        prev1_ts[idx[1:]] = ts[:-1]
        prev1_notional[idx[1:]] = notional[:-1]
        prev1_p0[idx[1:]] = p0[:-1]
        if m >= 3:
            prev2_ts[idx[2:]] = ts[:-2]
        lo = np.searchsorted(ts, ts - SAME_SIDE_WINDOW_MS, side="left")
        hi = np.arange(m)
        cnt = hi - lo
        count_60s[idx] = cnt.astype(float)
        for j in range(m):
            if cnt[j] > 0:
                seg = notional[lo[j]:hi[j]]
                max_notional_60s[idx[j]] = float(np.max(seg))
        gap = np.full(m, np.inf)
        gap[1:] = (ts[1:] - ts[:-1]).astype(float)
        start = np.zeros(m, dtype=int)
        for j in range(m):
            if j > 0 and gap[j] <= BURST_GAP_MS:
                start[j] = start[j - 1]
            else:
                start[j] = j
        burst_start_ts[idx] = ts[start]
        burst_start_p0[idx] = p0[start]

    return {
        "prev1_ts": prev1_ts, "prev1_notional": prev1_notional,
        "prev1_p0": prev1_p0, "prev2_ts": prev2_ts,
        "burst_start_ts": burst_start_ts, "burst_start_p0": burst_start_p0,
        "count_60s": count_60s, "max_notional_60s": max_notional_60s,
    }


# ===========================================================================
# 2. 約定・OI・資金調達率(日単位、explore5 のキャッシュ流儀を借りる)
# ===========================================================================
load_day_trades = ex5.load_day_trades
load_window5 = ex5.load_window5
build_oi_context = ex5.build_oi_context
covered_before = ex5.covered_before
compute_layers = ex5.compute_layers


def load_metrics_full(path: Path):
    """metrics zip -> (create_time[ms], sum_open_interest, taker_ls_ratio)。

    `sum_taker_long_short_vol_ratio` は cascade_read の実測(§4 コメント参照)で
    値が入っている列。他 3 種のロングショート比は空文字が多く使わない。
    """
    with zipfile.ZipFile(path) as z:
        name = z.namelist()[0]
        with z.open(name) as fh:
            head = fh.readline()
        has_header = b"create_time" in head
        cols = ["create_time", "sum_open_interest", "sum_taker_long_short_vol_ratio"]
        with z.open(name) as fh:
            if has_header:
                df = pd.read_csv(fh, usecols=cols)
            else:
                df = pd.read_csv(fh, header=None, names=oid.METRICS_NAMES,
                                  usecols=cols)
    t = (pd.to_datetime(df["create_time"], utc=True)
         .astype("datetime64[ms, UTC]").astype("int64").to_numpy(dtype=np.int64))
    oi = pd.to_numeric(df["sum_open_interest"], errors="coerce").to_numpy(float)
    tls = pd.to_numeric(df["sum_taker_long_short_vol_ratio"],
                         errors="coerce").to_numpy(float)
    order = np.argsort(t, kind="stable")
    return t[order], oi[order], tls[order]


def load_metrics_window(data_root: Path, day: str, cache: dict):
    """[前日, 当日] の metrics(OI 水準・taker LS 比)を連結。1 時間分あれば足りる。"""
    key = day
    if key in cache:
        return cache[key]
    prev = (_dt.date.fromisoformat(day) - _dt.timedelta(days=1)).isoformat()
    parts = []
    for d in (prev, day):
        p = oid.metrics_path(Path(data_root), d)
        if p.exists():
            parts.append(load_metrics_full(p))
    if parts:
        t = np.concatenate([x[0] for x in parts])
        oi = np.concatenate([x[1] for x in parts])
        tls = np.concatenate([x[2] for x in parts])
        o = np.argsort(t, kind="stable")
        t, oi, tls = t[o], oi[o], tls[o]
    else:
        t = np.zeros(0, dtype=np.int64)
        oi = np.zeros(0)
        tls = np.zeros(0)
    cache[key] = (t, oi, tls)
    for k in [k for k in cache if k < prev]:
        del cache[k]
    return cache[key]


def load_funding_all(data_root: Path):
    """資金調達率(月次 zip 全部)を 1 本の時系列にする(全期間、軽いので一括)。"""
    d = Path(data_root) / "fundingRate" / base.SYMBOL
    zips = sorted(d.glob(f"{base.SYMBOL}-fundingRate-*.zip"))
    ts_l, r_l = [], []
    for p in zips:
        with zipfile.ZipFile(p) as z:
            name = z.namelist()[0]
            with z.open(name) as fh:
                df = pd.read_csv(fh)
        ts_l.append(df["calc_time"].to_numpy(np.int64))
        r_l.append(pd.to_numeric(df["last_funding_rate"], errors="coerce")
                    .to_numpy(float))
    if not ts_l:
        return np.zeros(0, dtype=np.int64), np.zeros(0)
    t = np.concatenate(ts_l)
    r = np.concatenate(r_l)
    o = np.argsort(t, kind="stable")
    return t[o], r[o]


def imbalance_window(times, prices, qtys, maker, ts_ms: int, window_ms: int):
    """[ts-window, ts) の成行の偏り = (買い − 売り)/(買い+売り)。無ければ NaN。"""
    if times is None or times.size == 0:
        return NAN
    lo, hi = ts_ms - window_ms, ts_ms
    i0 = int(np.searchsorted(times, lo, side="left"))
    i1 = int(np.searchsorted(times, hi, side="left"))
    if i1 <= i0:
        return NAN
    q = qtys[i0:i1]
    mk = maker[i0:i1]
    buy = float(q[~mk].sum())
    sell = float(q[mk].sum())
    tot = buy + sell
    if tot <= 0:
        return NAN
    return (buy - sell) / tot


def trade_count_window(times, ts_ms: int, window_ms: int) -> int:
    if times is None or times.size == 0:
        return 0
    lo, hi = ts_ms - window_ms, ts_ms
    i0 = int(np.searchsorted(times, lo, side="left"))
    i1 = int(np.searchsorted(times, hi, side="left"))
    return max(0, i1 - i0)


def range_bp_window(times, prices, ts_ms: int, p_ref: float, window_ms: int):
    if times is None or times.size == 0 or not (math.isfinite(p_ref) and p_ref > 0):
        return NAN
    lo, hi = ts_ms - window_ms, ts_ms
    i0 = int(np.searchsorted(times, lo, side="left"))
    i1 = int(np.searchsorted(times, hi, side="left"))
    if i1 <= i0:
        return NAN
    seg = prices[i0:i1]
    return (float(seg.max()) - float(seg.min())) / p_ref * 1e4


def oi_slope_1h(t_oi, oi, ts_ms: int, window_ms: int = OI_SLOPE_WINDOW_MS):
    """`ts` 以前の OI 水準の window_ms 前からの変化率(bp)。"""
    if t_oi.size == 0:
        return NAN
    i_now = int(np.searchsorted(t_oi, ts_ms, side="right")) - 1
    if i_now < 0:
        return NAN
    oi_now = oi[i_now]
    if not math.isfinite(oi_now):
        return NAN
    i_prev = int(np.searchsorted(t_oi, ts_ms - window_ms, side="right")) - 1
    if i_prev < 0:
        return NAN
    oi_prev = oi[i_prev]
    if not (math.isfinite(oi_prev) and oi_prev != 0):
        return NAN
    return (oi_now - oi_prev) / oi_prev * 1e4


def latest_at_or_before(t, v, ts_ms: int):
    if t.size == 0:
        return NAN
    i = int(np.searchsorted(t, ts_ms, side="right")) - 1
    if i < 0:
        return NAN
    return float(v[i])


def price_at_or_before(times, prices, t_ms: int, staleness_ms=STALENESS_MS):
    if times is None or times.size == 0:
        return NAN, None
    i = int(np.searchsorted(times, t_ms, side="right")) - 1
    if i < 0:
        return NAN, None
    if t_ms - int(times[i]) > staleness_ms:
        return NAN, None
    return float(prices[i]), int(times[i])


def path_extreme_bp(times, prices, lo_ms: int, hi_ms: int, p_ref: float, sign: float):
    """(lo_ms, hi_ms] の約定経路で s×(p−p_ref)/p_ref×1e4 の最大値(無ければ NaN)。"""
    if times is None or times.size == 0 or not (math.isfinite(p_ref) and p_ref > 0):
        return NAN
    i0 = int(np.searchsorted(times, lo_ms, side="right"))
    i1 = int(np.searchsorted(times, hi_ms, side="right"))
    if i1 <= i0:
        return NAN
    seg = prices[i0:i1]
    return float(np.max(sign * (seg - p_ref) / p_ref * 1e4))


def tick_count(p0, p_pre):
    if not (math.isfinite(p0) and math.isfinite(p_pre)):
        return NAN
    return abs(p0 - p_pre) / TICK


# ===========================================================================
# 3. プリント 1 件ぶんの材料・ラベル・損益ひな型を計算する
# ===========================================================================
ROW_COLUMNS = (
    ["kind", "print_id", "day", "side", "half", "ts_ms", "t0_ms", "p0", "notional",
     "bundle_id", "dir_sign", "k_ticks"]
    + [MAT_COL[n] for n in MAT_NUMS]
    + ["mat1_elapsed_since_burst_s", "mat3_notional_raw", "mat4_bounce_bp",
       "mat8_amt_5bp", "mat8_amt_20bp", "mat8_covered",
       "mat10_taker_ls_ratio", "mat10_funding_rate"]
    + [f"label_{h}" for h in LABEL_SECONDS]
    + ["value_continuation_60"]
    + [f"p_entry_{e}" for e in ENTRY_DELAYS_S]
    + [f"p_exit_e{e}_h{h}" for e in ENTRY_DELAYS_S for h in HOLD_SECONDS]
    + ["q7_matched_print_id", "q7_band15", "q7_band9"])
CHUNK_HEADER = list(ROW_COLUMNS)
KIND_PRINT = "print"
KIND_Q7 = "q7_candidate"


def _blank_row() -> dict:
    return {c: "" for c in CHUNK_HEADER}


def _num(d: dict, key: str, v, nd: int = 6) -> None:
    d[key] = _fmt(v, nd)


def continuation_labels(pc: "PrintsCSV", i: int) -> dict:
    """「続く」ラベル(30/60/120 秒)。**同じ側の次のプリントの時刻だけ**で決まる
    (約定は要らない)。次が無ければ(この期間の最後)0。"""
    side = str(pc.side[i])
    ts = int(pc.ts[i])
    side_idx = pc.side_order[side]
    pos = int(pc.pos_in_side[i])
    nxt_ts_val = (int(pc.ts[int(side_idx[pos + 1])]) if pos + 1 < side_idx.size
                 else -1)
    return {h: int(nxt_ts_val >= 0 and (nxt_ts_val - ts) <= h * 1000)
            for h in LABEL_SECONDS}


def compute_print_row(day, pc: PrintsCSV, i: int, nb: dict, times, prices, qtys,
                      maker, buckets, cov, t_oi, oi_lvl, tls, t_fund, r_fund,
                      half: str) -> tuple[list, dict]:
    """プリント `i`(pc の行番号)の 1 行。材料の生値も辞書で返す(Q1/Q2/Jev 用)。"""
    ts = int(pc.ts[i])
    side = str(pc.side[i])
    s = float(pc.sign[i])
    p0 = float(pc.p0[i])
    notional = float(pc.notional[i])

    # `pr_price`(profile_columns の p_liq)は使わない(dist_node_bp は rows_prints から
    # 再利用する。下の理由参照)ので `step=None, window_ms=None` で profile_columns/OI の
    # 重い区間を丸ごとスキップし、k・m(10)・m(60)・p_pre だけを得る。
    lay = compute_layers(times, prices, qtys, np.array([ts]), np.array([side]),
                         np.array([0.0]), np.array([0]), buckets=None, cov=None,
                         step=None, window_ms=None)
    ok_pre = bool(lay["ok_pre"][0])
    p_pre = float(lay["p_pre"][0]) if ok_pre else NAN
    m10 = float(lay["m_10"][0])
    m60 = float(lay["m_60"][0])
    # 材料 5(次の清算水準までの距離)は探索段 5 の `rows_prints.csv.gz` の
    # `dist_node_bp` をそのまま再利用する(委任文【データ】)。ここで作り直すと
    # `profile_columns` の `p_liq` に p₀(ts 以後の初約定)を渡すことになり
    # 「p₀ は使わない」に反するため、あえて再計算しない。
    dist_node = float(pc.dist_node_bp[i])

    # --- 材料 1・2・3・4・12(プリントの時刻列だけ) -----------------------------
    count60 = float(nb["count_60s"][i])
    prev1_ts, prev2_ts = int(nb["prev1_ts"][i]), int(nb["prev2_ts"][i])
    prev1_notional, prev1_p0 = float(nb["prev1_notional"][i]), float(nb["prev1_p0"][i])
    burst_start_ts, burst_start_p0 = int(nb["burst_start_ts"][i]), float(nb["burst_start_p0"][i])
    max_notional60 = float(nb["max_notional_60s"][i])

    elapsed_s = (ts - burst_start_ts) / 1000.0 if burst_start_ts >= 0 else NAN
    if prev1_ts >= 0 and prev2_ts >= 0:
        gap_a = ts - prev1_ts
        gap_b = prev1_ts - prev2_ts
        mat2 = (gap_b / gap_a) if gap_a > 0 else NAN
    else:
        mat2 = NAN
    mat3 = (notional / prev1_notional) if (prev1_ts >= 0 and prev1_notional > 0) else NAN
    # 材料 4 は「ts 以前に手元にある」直前の約定価格 p_pre を使う(p₀ ではない。
    # burst_start_p0 は**それより前のプリント**自身の p₀ なので、今のプリントの
    # ts から見れば既に過去のデータであり使ってよい)。
    mat4 = (s * (p_pre - burst_start_p0) / burst_start_p0 * 1e4
            if (ok_pre and burst_start_p0 == burst_start_p0 and burst_start_p0 > 0)
            else NAN)
    bounce = (s * (p_pre - prev1_p0) / prev1_p0 * 1e4
              if (prev1_ts >= 0 and ok_pre and prev1_p0 == prev1_p0 and prev1_p0 > 0)
              else NAN)
    mat12 = (notional / max_notional60
             if (max_notional60 == max_notional60 and max_notional60 > 0) else NAN)

    # --- 材料 6 ---------------------------------------------------------------
    mat6 = hour_band_of(ts)

    # --- 材料 8(建玉の帯、cascade_read の道具を再利用) -------------------------
    # 基準価格は p_pre(ts 以前の最後の約定)。p₀(ts 以後の初約定)は使わない
    # (`cr.oi_band_amounts` は本来 cascade_read の探索的読みで p₀ を渡していたが、
    # この道具では材料の定義に合わせて p_pre に差し替える — 設計に無い判断)。
    oi_out = cr.oi_band_amounts(buckets, ts, p_pre, side) if ok_pre else {
        "covered": False, "n_buckets": 0, "amt_5bp": None, "amt_10bp": None,
        "amt_20bp": None}
    covered8 = bool(oi_out.get("covered", False))
    amt5 = oi_out.get("amt_5bp") if covered8 else None
    amt10 = oi_out.get("amt_10bp") if covered8 else None
    amt20 = oi_out.get("amt_20bp") if covered8 else None

    # --- 材料 9・13(成行の偏り 5s/30s) -----------------------------------------
    imb5 = imbalance_window(times, prices, qtys, maker, ts, IMBALANCE_WINDOWS_MS["5s"])
    imb30 = imbalance_window(times, prices, qtys, maker, ts, IMBALANCE_WINDOWS_MS["30s"])
    mat9 = s * imb5 if imb5 == imb5 else NAN
    mat13 = (s * (imb5 - imb30)) if (imb5 == imb5 and imb30 == imb30) else NAN

    # --- 材料 10(OI 1 時間傾き、taker LS 比、資金調達率) -----------------------
    mat10 = oi_slope_1h(t_oi, oi_lvl, ts)
    taker_ls = latest_at_or_before(t_oi, tls, ts)
    funding = latest_at_or_before(t_fund, r_fund, ts)

    # --- 材料 11 ---------------------------------------------------------------
    rng60 = range_bp_window(times, prices, ts, p_pre, RANGE_WINDOW_MS)  # 基準は p_pre(p₀ は使わない)
    mat11 = (notional / rng60) if (rng60 == rng60 and rng60 > 0) else NAN

    # --- 材料 14 -----------------------------------------------------------
    mat14 = float(trade_count_window(times, ts, TRADE_COUNT_WINDOW_MS))

    # --- 材料 15(m10/m60) ------------------------------------------------------
    mat15 = (m10 / m60) if (m10 == m10 and m60 == m60 and m60 != 0) else NAN

    mat_vals = {1: count60, 2: mat2, 3: mat3, 4: mat4, 5: dist_node, 6: mat6,
                8: amt10, 9: mat9, 10: mat10, 11: mat11, 12: mat12, 13: mat13,
                14: mat14, 15: mat15}

    # --- ラベル(続く。同じ側の次のプリントの時刻だけで決まる) -------------------
    labels = continuation_labels(pc, i)

    # --- 値段の続き(60 秒、経路の最大値) ---------------------------------------
    t0_ms = int(pc.df.at[i, "t0_ms"])
    ext = path_extreme_bp(times, prices, t0_ms, t0_ms + LABEL_MAIN * 1000, p0, s)
    value_cont = NAN if ext != ext else float(ext >= VALUE_CONT_BP)

    # --- 入る / 出る時点の価格 ---------------------------------------------------
    entry_px = {}
    for e in ENTRY_DELAYS_S:
        px, _t = price_at_or_before(times, prices, t0_ms + e * 1000)
        entry_px[e] = px
    exit_px = {}
    for e in ENTRY_DELAYS_S:
        for h in HOLD_SECONDS:
            px, _t = price_at_or_before(times, prices, t0_ms + e * 1000 + h * 1000)
            exit_px[(e, h)] = px

    d = _blank_row()
    d["kind"] = KIND_PRINT
    d["print_id"] = str(pc.print_id[i])
    d["day"] = day
    d["side"] = side
    d["half"] = half
    d["ts_ms"] = ts
    d["t0_ms"] = t0_ms
    _num(d, "p0", p0, 4)
    _num(d, "notional", notional, 4)
    d["bundle_id"] = str(pc.bundle_id[i])
    d["dir_sign"] = int(s)
    _num(d, "k_ticks", tick_count(p0, p_pre), 3)
    for n in MAT_NUMS:
        _num(d, MAT_COL[n], mat_vals[n] if n != 6 else None)
    d[MAT_COL[6]] = mat6
    _num(d, "mat1_elapsed_since_burst_s", elapsed_s, 3)
    _num(d, "mat3_notional_raw", notional, 4)
    _num(d, "mat4_bounce_bp", bounce)
    _num(d, "mat8_amt_5bp", amt5)
    _num(d, "mat8_amt_20bp", amt20)
    d["mat8_covered"] = int(covered8)
    _num(d, "mat10_taker_ls_ratio", taker_ls)
    _num(d, "mat10_funding_rate", funding, 8)
    for h in LABEL_SECONDS:
        d[f"label_{h}"] = labels[h]
    d["value_continuation_60"] = "" if value_cont != value_cont else int(value_cont)
    for e in ENTRY_DELAYS_S:
        _num(d, f"p_entry_{e}", entry_px[e], 4)
    for e in ENTRY_DELAYS_S:
        for h in HOLD_SECONDS:
            _num(d, f"p_exit_e{e}_h{h}", exit_px[(e, h)], 4)
    return [d[c] for c in CHUNK_HEADER], mat_vals


# ===========================================================================
# 4. 段 1: プリントの行(日ごとの chunk、再開できる)
# ===========================================================================
def run_stage1(out_dir: Path, days: list, half_of: dict, pc: PrintsCSV, nb: dict,
               data_root: Path, progress_every: int) -> dict:
    work = out_dir / "chunks1"
    work.mkdir(parents=True, exist_ok=True)
    trade_cache: dict = {}
    metrics_cache: dict = {}
    bucket_cache: dict = {}
    oimet_cache: dict = {}
    missing_agg: set = set()
    missing_metrics: set = set()
    t_fund, r_fund = load_funding_all(data_root)
    back_ms = 400_000
    fwd_ms = 910_000
    t0 = time.time()
    for n_done, day in enumerate(days, start=1):
        cp = work / f"{day}.csv.gz"
        if cp.exists():
            continue
        sel = pc.by_day.get(day, np.zeros(0, dtype=int))
        times, prices, qtys, miss, _need = load_window5(data_root, day, trade_cache,
                                                         back_ms, fwd_ms)
        missing_agg |= set(miss)
        maker = None
        if sel.size:
            # is_buyer_maker も要る(imbalance 用)。窓を跨ぐ日ぶんを結合。
            maker = _load_window_maker(data_root, day, trade_cache, back_ms, fwd_ms)
        buckets, cov, mmiss = build_oi_context(data_root, data_root, day, trade_cache,
                                               metrics_cache, bucket_cache)
        missing_metrics |= set(mmiss)
        t_oi, oi_lvl, tls = load_metrics_window(data_root, day, oimet_cache)
        rows = []
        for i in sel.tolist():
            row, _mv = compute_print_row(day, pc, i, nb, times, prices, qtys, maker,
                                         buckets, cov, t_oi, oi_lvl, tls, t_fund,
                                         r_fund, half_of[day])
            rows.append(row)
        tmp = work / f".{day}.part"
        with gz_open_w(tmp) as fh:
            w = csv.writer(fh)
            w.writerow(CHUNK_HEADER)
            w.writerows(rows)
        tmp.replace(cp)
        if n_done % progress_every == 0:
            print(f"  段1 {n_done}/{len(days)} 日 ({day}) 経過 "
                  f"{time.time() - t0:.0f}s", flush=True)
    return {"agg_days_missing": sorted(missing_agg),
            "metrics_days_missing": sorted(missing_metrics)}


def _load_window_maker(data_root, day, cache, back_ms, fwd_ms):
    """`load_window5` と同じ範囲の `is_buyer_maker` だけを別途取り出す。

    `load_window5` はキャッシュに (times, prices, qtys, maker) の 4 つ組で積む
    (`o3c_oi_distance.load_agg_trades_with_maker`)ので、同じキャッシュから
    同じ日付集合を再結合する。
    """
    lo = day_start_ms(day) - back_ms
    hi = day_start_ms(day) + MS_PER_DAY + fwd_ms
    d_lo, d_hi = day_of_ms(lo), day_of_ms(hi)
    need = [d_lo]
    while need[-1] < d_hi:
        need.append((_dt.date.fromisoformat(need[-1]) + _dt.timedelta(days=1)).isoformat())
    parts = []
    times_l = []
    for d in need:
        v = load_day_trades(data_root, d, cache)
        if v is not None:
            times_l.append(v[0])
            parts.append(v[3])
    if not parts:
        return np.zeros(0, dtype=bool)
    times = np.concatenate(times_l)
    maker = np.concatenate(parts)
    if not bool(np.all(times[1:] >= times[:-1])):
        o = np.argsort(times, kind="stable")
        times, maker = times[o], maker[o]
    m = (times >= lo) & (times <= hi)
    return maker[m]


# ===========================================================================
# 5. 前半の 10 分位の切り値(材料ごと)
# ===========================================================================
def read_stage1_frame(out_dir: Path, days: list) -> pd.DataFrame:
    parts = []
    for day in days:
        cp = out_dir / "chunks1" / f"{day}.csv.gz"
        if cp.exists():
            parts.append(pd.read_csv(cp, dtype={"bundle_id": str, "day": str,
                                                 "print_id": str}))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=CHUNK_HEADER)


def vectorized_imbalance(times, qtys, maker, ts_arr, window_ms) -> np.ndarray:
    """成行の偏りを配列でまとめて計算する(前置和、Q7 の候補グリッド用)。"""
    if times is None or times.size == 0:
        return np.full(ts_arr.size, NAN)
    buy_q = np.where(~maker, qtys, 0.0)
    sell_q = np.where(maker, qtys, 0.0)
    cum_buy = np.concatenate(([0.0], np.cumsum(buy_q)))
    cum_sell = np.concatenate(([0.0], np.cumsum(sell_q)))
    hi = np.searchsorted(times, ts_arr, side="left")
    lo = np.searchsorted(times, ts_arr - window_ms, side="left")
    buy = cum_buy[hi] - cum_buy[lo]
    sell = cum_sell[hi] - cum_sell[lo]
    tot = buy + sell
    out = np.full(ts_arr.size, NAN)
    ok = tot > 0
    out[ok] = (buy[ok] - sell[ok]) / tot[ok]
    return out


def day_grid_materials(day: str, times, prices, qtys, maker):
    """その日の 10 秒刻みグリッド全点の 材料 15・9(の代理量)を一括で作る(Q7)。"""
    d0 = day_start_ms(day)
    grid = d0 + np.arange(GRID_N, dtype=np.int64) * Q7_GRID_STEP_MS
    i_ge, ok_ge = idx_at_or_after(times, grid, STALENESS_MS)
    i_gp, ok_gp = idx_at_or_before(times, grid, STALENESS_MS)
    i_g10, ok_g10 = idx_at_or_before(times, grid - 10_000, STALENESS_MS)
    i_g60, ok_g60 = idx_at_or_before(times, grid - 60_000, STALENESS_MS)
    p_ge = np.where(ok_ge, prices[i_ge] if times.size else NAN, NAN)
    p_gp = np.where(ok_gp, prices[i_gp] if times.size else NAN, NAN)
    p_g10 = np.where(ok_g10, prices[i_g10] if times.size else NAN, NAN)
    p_g60 = np.where(ok_g60, prices[i_g60] if times.size else NAN, NAN)
    with np.errstate(invalid="ignore", divide="ignore"):
        raw_m10 = np.where(ok_gp & ok_g10 & (p_g10 > 0), (p_gp - p_g10) / p_g10 * 1e4, NAN)
        raw_m60 = np.where(ok_gp & ok_g60 & (p_g60 > 0), (p_gp - p_g60) / p_g60 * 1e4, NAN)
        mat15 = np.where(np.isfinite(raw_m10) & np.isfinite(raw_m60) & (raw_m60 != 0),
                         raw_m10 / np.where(raw_m60 != 0, raw_m60, 1.0), NAN)
    dir_ = np.where(np.isfinite(raw_m10), np.where(raw_m10 >= 0, 1.0, -1.0), NAN)
    imb5 = vectorized_imbalance(times, qtys, maker, grid, IMBALANCE_WINDOWS_MS["5s"])
    mat9 = np.where(np.isfinite(dir_) & np.isfinite(imb5), dir_ * imb5, NAN)
    ok_all = ok_ge & ok_gp & ok_g10 & ok_g60 & np.isfinite(mat15) & np.isfinite(mat9)
    return {"grid": grid, "p0": p_ge, "mat15": mat15, "mat9": mat9, "dir": dir_,
            "ok": ok_all}


def q7_no_liq_mask(grid: np.ndarray, all_ts: np.ndarray) -> np.ndarray:
    lo = np.searchsorted(all_ts, grid - Q7_NO_LIQ_WINDOW_MS, side="left")
    hi = np.searchsorted(all_ts, grid + Q7_NO_LIQ_WINDOW_MS, side="right")
    return (hi - lo) == 0


def run_stage2(out_dir: Path, days2: list, pc: PrintsCSV, cuts: dict, all_ts,
              stage1_df: pd.DataFrame, data_root: Path, progress_every: int) -> dict:
    """Q7: 清算の無い時刻の対照(後半だけ、設計 §4・用語表の「後半だけで測る」に従う)。"""
    work = out_dir / "chunks3"
    work.mkdir(parents=True, exist_ok=True)
    trade_cache: dict = {}
    back_ms, fwd_ms = 400_000, 400_000
    band_by_pid = {r["print_id"]: (r["_b15"], r["_b9"], r[MAT_COL[15]], r[MAT_COL[9]])
                  for r in stage1_df.to_dict("records")}
    miss_by_band: dict = defaultdict(lambda: [0, 0])   # (b15,b9) -> [取れた, 全体]
    t0 = time.time()
    for n_done, day in enumerate(days2, start=1):
        cp = work / f"{day}.csv.gz"
        if cp.exists():
            continue
        sel = pc.by_day.get(day, np.zeros(0, dtype=int))
        times, prices, qtys, _miss, _need = load_window5(data_root, day, trade_cache,
                                                          back_ms, fwd_ms)
        maker = _load_window_maker(data_root, day, trade_cache, back_ms, fwd_ms)
        g = day_grid_materials(day, times, prices, qtys, maker)
        no_liq = q7_no_liq_mask(g["grid"], all_ts)
        avail = g["ok"] & no_liq
        used = np.zeros(GRID_N, dtype=bool)
        rows = []
        for i in sel.tolist():
            pid = str(pc.print_id[i])
            b15, b9, v15, v9 = band_by_pid.get(pid, (None, None, NAN, NAN))
            if b15 is None or b15 < 0 or b9 < 0:
                continue
            miss_by_band[(b15, b9)][1] += 1
            cand = avail & ~used & (band_of_m(g["mat15"], cuts[15]) == b15) \
                & (band_of_m(g["mat9"], cuts[9]) == b9)
            idxs = np.flatnonzero(cand)
            if idxs.size == 0:
                continue
            dist = np.abs(g["mat15"][idxs] - v15) + np.abs(g["mat9"][idxs] - v9)
            j = idxs[int(np.argmin(dist))]
            used[j] = True
            miss_by_band[(b15, b9)][0] += 1
            t0p = int(g["grid"][j])
            p0p = float(g["p0"][j])
            dirp = float(g["dir"][j])
            ext = path_extreme_bp(times, prices, t0p, t0p + LABEL_MAIN * 1000, p0p, dirp)
            vc = NAN if ext != ext else float(ext >= VALUE_CONT_BP)
            e_px, _ = price_at_or_before(times, prices, t0p + MAIN_ENTRY * 1000)
            x_px, _ = price_at_or_before(times, prices,
                                         t0p + MAIN_ENTRY * 1000 + MAIN_HOLD * 1000)
            d = _blank_row()
            d["kind"] = KIND_Q7
            d["print_id"] = f"q7_{pid}"
            d["day"] = day
            d["half"] = "後半"
            d["ts_ms"] = t0p
            d["t0_ms"] = t0p
            _num(d, "p0", p0p, 4)
            d["dir_sign"] = int(dirp)
            _num(d, MAT_COL[15], float(g["mat15"][j]))
            _num(d, MAT_COL[9], float(g["mat9"][j]))
            d["q7_matched_print_id"] = pid
            d["q7_band15"] = int(b15)
            d["q7_band9"] = int(b9)
            d["value_continuation_60"] = "" if vc != vc else int(vc)
            _num(d, "p_entry_1", e_px, 4)
            _num(d, "p_exit_e1_h60", x_px, 4)
            rows.append([d[c] for c in CHUNK_HEADER])
        tmp = work / f".{day}.part"
        with gz_open_w(tmp) as fh:
            w = csv.writer(fh)
            w.writerow(CHUNK_HEADER)
            w.writerows(rows)
        tmp.replace(cp)
        if n_done % progress_every == 0:
            print(f"  段2(Q7) {n_done}/{len(days2)} 日 ({day}) 経過 "
                  f"{time.time() - t0:.0f}s", flush=True)
    return {"miss_by_band": {f"{k[0]}_{k[1]}": v for k, v in miss_by_band.items()}}


def first_half_cuts(df: pd.DataFrame) -> dict:
    """材料ごとの前半 228 日の 10 分位切り値(q_1…q_9)。材料 6 は時刻帯のカテゴリのまま。"""
    fh = df[df["half"] == "前半"]
    cuts = {}
    for n in MAT_NUMS_CONT:
        v = pd.to_numeric(fh[MAT_COL[n]], errors="coerce").to_numpy(float)
        v = v[np.isfinite(v)]
        cuts[n] = (np.quantile(v, [i / N_BANDS for i in range(1, N_BANDS)])
                   if v.size else np.zeros(N_BANDS - 1))
    return cuts


def concat_rows(out_dir: Path, days: list, days2: list) -> Path:
    p = out_dir / "rows_continue.csv.gz"
    fh = gz_open_w(Path(str(p) + ".part"))
    w = csv.writer(fh)
    w.writerow(ROW_COLUMNS)
    n = 0
    for day in days:
        cp = out_dir / "chunks1" / f"{day}.csv.gz"
        if not cp.exists():
            continue
        with gzip.open(cp, "rt", newline="") as g:
            rd = csv.reader(g)
            next(rd)
            for row in rd:
                w.writerow(row)
                n += 1
    for day in days2:
        cp = out_dir / "chunks3" / f"{day}.csv.gz"
        if not cp.exists():
            continue
        with gzip.open(cp, "rt", newline="") as g:
            rd = csv.reader(g)
            next(rd)
            for row in rd:
                w.writerow(row)
                n += 1
    fh.close()
    Path(str(p) + ".part").replace(p)
    print(f"行数 {n}", flush=True)
    return p


SIDE_LIST = ("SELL", "BUY")
TIME_BAND_NAMES = [nm for nm, _lo, _hi in HOUR_BANDS]


def load_rows(out_dir: Path) -> pd.DataFrame:
    p = out_dir / "rows_continue.csv.gz"
    str_cols = {"kind", "print_id", "day", "side", "half", "bundle_id",
               MAT_COL[6], "q7_matched_print_id"}
    df = pd.read_csv(p, dtype={c: str for c in str_cols})
    for c in df.columns:
        if c not in str_cols:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def add_bands(df: pd.DataFrame, cuts: dict) -> pd.DataFrame:
    df = df.copy()
    for n in MAT_NUMS_CONT:
        df[f"band_{n}"] = band_of_m(df[MAT_COL[n]].to_numpy(float), cuts[n])
    cat_band = pd.Series(-1, index=df.index, dtype=int)
    for i, nm in enumerate(TIME_BAND_NAMES, start=1):
        cat_band[df[MAT_COL[6]] == nm] = i
    df["band_6"] = cat_band
    return df


def band_labels(n: int, cuts: dict) -> dict:
    if n == 6:
        return {i: nm for i, nm in enumerate(TIME_BAND_NAMES, start=1)}
    out = {}
    for k in range(1, N_BANDS + 1):
        lo, hi = band_bounds(cuts[n], k)
        out[k] = f"帯{k}[{bound_text(lo)},{bound_text(hi)})"
    return out


def band_rate_table(df: pd.DataFrame, n: int, half: str, label_col: str) -> dict:
    """材料 n・半期・ラベル列ごとの {帯 -> (続く割合, n)}。"""
    sub = df[df["half"] == half]
    col = f"band_{n}"
    out = {}
    for b, g in sub.groupby(col):
        v = g[label_col].astype(float)
        out[int(b)] = (float(v.mean()) if v.size else NAN, int(v.size))
    return out


def make_q1(df: pd.DataFrame, cuts: dict) -> list:
    rows = []
    for n in MAT_NUMS:
        col = MAT_COL[n]
        for grp_label, grp_mask in (("続いた(label_60=1)", df["label_60"] == 1),
                                    ("止まった(label_60=0)", df["label_60"] == 0)):
            if n == 6:
                continue
            v = pd.to_numeric(df.loc[grp_mask, col], errors="coerce").to_numpy(float)
            q = quantiles(v, [10, 25, 50, 75, 90])
            rows.append({"材料": n, "変数名": MAT_VAR[n], "区分": "分位(全期間)",
                        "群": grp_label, "n": int(np.isfinite(v).sum()),
                        "p10": q[0], "p25": q[1], "p50": q[2], "p75": q[3],
                        "p90": q[4]})
        fh = band_rate_table(df, n, "前半", "label_60")
        bh = band_rate_table(df, n, "後半", "label_60")
        labels = band_labels(n, cuts)
        bands = sorted(set(list(fh.keys()) + list(bh.keys())))
        for b in bands:
            r_f, n_f = fh.get(b, (NAN, 0))
            r_b, n_b = bh.get(b, (NAN, 0))
            rows.append({"材料": n, "変数名": MAT_VAR[n], "区分": "帯ごとの続く割合",
                        "群": (labels.get(b, "欠測") if b >= 1 else "欠測(材料が引けない)"),
                        "帯": b, "前半 n": n_f, "前半 続く割合": r_f,
                        "後半 n": n_b, "後半 続く割合": r_b})
    return rows


def build_rules(df: pd.DataFrame, cuts: dict, base_fh_60: float):
    """材料ごとの規則(14 本)+ 組の規則(1 本)。前半の帯ごとの割合から作る。"""
    fh = df[df["half"] == "前半"]
    rule_bands: dict = {}     # n -> {帯: 続く割合}
    rule_continue_set: dict = {}  # n -> {帯 が「続く」なら True}
    spread: dict = {}
    for n in MAT_NUMS:
        r = band_rate_table(fh, n, "前半", "label_60")
        rule_bands[n] = r
        rule_continue_set[n] = {b: (rate > base_fh_60) for b, (rate, cnt) in r.items()
                                if b >= 1 and cnt > 0}
        rates = [rate for b, (rate, cnt) in r.items() if b >= 1 and cnt > 0]
        spread[n] = (max(rates) - min(rates)) if len(rates) >= 2 else -1.0
    top3 = sorted(MAT_NUMS, key=lambda n: spread[n], reverse=True)[:3]
    return rule_bands, rule_continue_set, top3


def apply_rule(df: pd.DataFrame, n: int, rule_continue_set: dict) -> pd.Series:
    col = f"band_{n}"
    m = df[col].map(lambda b: rule_continue_set[n].get(int(b)))
    return m  # True/False/None(引けない)


def apply_combo(df: pd.DataFrame, top3: list, rule_bands: dict,
                base_fh_60: float) -> pd.Series:
    def _row_score(row):
        vals = []
        for n in top3:
            r = rule_bands[n].get(int(row[f"band_{n}"]))
            if r is None:
                return None
            vals.append(r[0])
        return (sum(vals) / len(vals)) > base_fh_60
    return df.apply(_row_score, axis=1)


def make_q2(df: pd.DataFrame, cuts: dict, rule_bands: dict, rule_continue_set: dict,
           top3: list, base_by_half: dict) -> list:
    rows = []
    bh = df[df["half"] == "後半"]
    judges = {f"rule_{n}({MAT_VAR[n]})": apply_rule(bh, n, rule_continue_set)
             for n in MAT_NUMS}
    judges["rule_combo(" + "+".join(MAT_VAR[n] for n in top3) + ")"] = apply_combo(
        bh, top3, rule_bands, base_by_half["前半"][60])
    for name, pred in judges.items():
        for h in LABEL_SECONDS:
            y = bh[f"label_{h}"].astype(float)
            has = pred.notna()
            p = pred[has].astype(bool)
            yy = y[has]
            n_tot = int(has.sum())
            tp = int(((p) & (yy == 1)).sum())
            fp = int(((p) & (yy == 0)).sum())
            fn = int(((~p) & (yy == 1)).sum())
            tn = int(((~p) & (yy == 0)).sum())
            acc = (tp + tn) / n_tot if n_tot else NAN
            prec = tp / (tp + fp) if (tp + fp) else NAN
            rec = tp / (tp + fn) if (tp + fn) else NAN
            rows.append({"規則": name, "h(秒)": h, "n": n_tot,
                        "基準率(後半)": float(y.mean()) if y.size else NAN,
                        "的中率": acc, "適合率": prec, "再現率": rec,
                        "「続く」と言った件数": int(p.sum()),
                        "規則が引けなかった件数": int((~has).sum())})
    return rows


def branch_stats(pnl: np.ndarray, days: np.ndarray) -> dict:
    fin = np.isfinite(pnl)
    v, d = pnl[fin], days[fin]
    if v.size == 0:
        return {"n": 0, "含む日数": 0, "中央値": NAN, "p25": NAN, "p75": NAN,
                "負の割合": NAN, "日等重み平均": NAN, "日クラスタSE": NAN}
    mean, se, naive, n, g = mean_se_cluster(v, d)
    q = quantiles(v, [25, 50, 75])
    return {"n": n, "含む日数": g, "中央値": q[1], "p25": q[0], "p75": q[2],
            "負の割合": float((v < 0).mean()), "日等重み平均": day_equal_weight_mean(v, d),
            "日クラスタSE": se}


def build_judgments(bh: pd.DataFrame, rule_continue_set: dict, top3: list,
                    rule_bands: dict, base_fh_60: float) -> dict:
    j = {}
    for n in MAT_NUMS:
        j[f"rule_{n}"] = apply_rule(bh, n, rule_continue_set)
    j["rule_combo"] = apply_combo(bh, top3, rule_bands, base_fh_60)
    j["jev"] = pd.Series([None] * len(bh), index=bh.index)
    j["all_continue"] = pd.Series(True, index=bh.index)
    j["all_stop"] = pd.Series(False, index=bh.index)
    j["perfect"] = bh["label_60"] == 1
    return j


def make_q4(bh: pd.DataFrame, judgments: dict) -> list:
    rows = []
    grids = [(e, h) for e in ENTRY_DELAYS_S for h in HOLD_SECONDS]
    s = bh["dir_sign"].astype(float)
    for (e, h) in grids:
        is_main = (e == MAIN_ENTRY and h == MAIN_HOLD)
        names = list(judgments.keys()) if is_main else ["rule_combo", "perfect"]
        entry = bh[f"p_entry_{e}"]
        exitp = bh[f"p_exit_e{e}_h{h}"]
        for name in names:
            pred = judgments[name]
            for branch_label, branch_bool in (("続く", True), ("止まる", False)):
                mask = (pred == branch_bool)
                dirn = np.where(branch_bool, s, -s)
                pnl = dirn * (exitp - entry) / entry * 1e4
                pnl = pnl.where(mask, NAN)
                st = branch_stats(pnl.to_numpy(float), bh["day"].to_numpy(object))
                rows.append({"格子": ("主(t0+1s→60s)" if is_main else "副"),
                            "entry_s": e, "hold_s": h, "判断": name, "枝": branch_label,
                            **st})
    return rows


def make_q5(bh: pd.DataFrame, judgments: dict) -> list:
    rows = []
    entry = bh["p_entry_1"]
    exitp = bh["p_exit_e1_h60"]
    s = bh["dir_sign"].astype(float)
    for name, pred in judgments.items():
        dirn = pred.map(lambda x: (1.0 if x else -1.0) if x is not None else NAN)
        pnl = dirn.astype(float) * s * (exitp - entry) / entry * 1e4
        v = pnl.to_numpy(float)
        d = bh["day"].to_numpy(object)
        fin = np.isfinite(v)
        vv, dd = v[fin], d[fin]
        if vv.size == 0:
            rows.append({"判断": name, "日数": 0, "負の日の割合": NAN,
                        "上位5日の寄与の和÷全体": NAN, "合計bp": NAN})
            continue
        daily = pd.Series(vv).groupby(dd).sum()
        total = float(daily.sum())
        top5 = float(daily.sort_values(ascending=False).head(5).sum())
        rows.append({"判断": name, "日数": int(daily.size),
                    "負の日の割合": float((daily < 0).mean()),
                    "上位5日の寄与の和÷全体": (top5 / total) if total != 0 else NAN,
                    "合計bp": total})
    return rows


def make_q3_placeholder() -> list:
    """Jev はこの委任では後半に呼んでいない(前半 200 件の下見のみ)。行の形だけ用意する。"""
    rows = []
    for h in LABEL_SECONDS:
        for metric in ("的中率", "適合率", "再現率"):
            rows.append({"量": metric, "h(秒)": h, "n": 0, "値": NAN,
                        "備考": "この委任では Jev を後半に呼んでいない(下見 200 件のみ)"})
    for k in range(1, N_BANDS + 1):
        rows.append({"量": "確率帯ごとの実際の続く割合(較正)", "確率帯": k, "n": 0,
                    "値": NAN, "備考": "同上"})
    rows.append({"量": "規則(組)との一致率", "h(秒)": LABEL_MAIN, "n": 0, "値": NAN,
                "備考": "同上"})
    return rows


def make_q7(q7df: pd.DataFrame, rule_continue_set: dict, miss_by_band: dict) -> list:
    rows = []
    cand_judge = {
        15: q7df["q7_band15"].map(
            lambda b: rule_continue_set[15].get(int(b)) if pd.notna(b) else None),
        9: q7df["q7_band9"].map(
            lambda b: rule_continue_set[9].get(int(b)) if pd.notna(b) else None),
    }
    names = [f"rule_{n}" for n in MAT_NUMS] + ["rule_combo"]
    computed = {f"rule_{n}": n for n in (15, 9)}
    entry = q7df["p_entry_1"]
    exitp = q7df["p_exit_e1_h60"]
    s = q7df["dir_sign"].astype(float)
    for name in names:
        if name not in computed:
            for branch_label in ("続く", "止まる"):
                rows.append({"規則": name, "枝": branch_label, "n": 0,
                            "備考": "candidate 側は未計算(材料がこのプリント固有のため。限界参照)"})
            continue
        n = computed[name]
        pred = cand_judge[n]
        said_continue = float((pred == True).sum()) / max(int(pred.notna().sum()), 1)  # noqa: E712
        for branch_label, branch_bool in (("続く", True), ("止まる", False)):
            mask = (pred == branch_bool)
            dirn = np.where(branch_bool, s, -s)
            pnl = dirn * (exitp - entry) / entry * 1e4
            pnl = pd.Series(pnl, index=q7df.index).where(mask, NAN)
            st = branch_stats(pnl.to_numpy(float), q7df["day"].to_numpy(object))
            rows.append({"規則": name, "枝": branch_label, "続くと言った割合": said_continue,
                        **st})
    for branch_label in ("続く", "止まる"):
        rows.append({"規則": "jev", "枝": branch_label, "n": 0,
                    "備考": "この委任では Q7 に Jev を呼んでいない(設計 §2 Q7)"})
    agg: dict = defaultdict(lambda: [0, 0])
    for k, (got, tot) in miss_by_band.items():
        b15 = int(k.split("_")[0])
        agg[b15][0] += got
        agg[b15][1] += tot
    for b15 in range(1, N_BANDS + 1):
        got, tot = agg.get(b15, [0, 0])
        rate = (got / tot) if tot else NAN
        flag = "読まない" if (b15 in (9, 10) and tot and rate < 0.5) else ""
        rows.append({"規則": "(対照候補の可否)", "材料15の帯": b15, "対象": tot,
                    "取れた": got, "取れた割合": rate, "印": flag})
    return rows


def make_q0(prints: pd.DataFrame, days1: list, days2: list) -> list:
    rows = []
    rows.append({"区分": "プリント数", "量": "母集団(探索段5 kind=print)",
                "n": 52_000})
    rows.append({"区分": "プリント数", "量": "この単位で使うプリント(前半+後半)",
                "n": int(prints.shape[0])})
    for half in ("前半", "後半"):
        for side in SIDE_LIST:
            for h in LABEL_SECONDS:
                sub = prints[(prints["half"] == half) & (prints["side"] == side)]
                v = sub[f"label_{h}"].astype(float)
                rows.append({"区分": "ラベルの割合", "半期": half, "側": side,
                            "h(秒)": h, "n": int(v.size),
                            "続く割合": float(v.mean()) if v.size else NAN})
    for n in MAT_NUMS:
        v = prints[MAT_COL[n]]
        bad = v.isna() if n != 6 else (v == "") | v.isna()
        rows.append({"区分": "材料ごとの欠測数", "材料": n, "変数名": MAT_VAR[n],
                    "欠測": int(bad.sum()), "母数": int(prints.shape[0]),
                    "割合": float(bad.mean())})
    lag = (prints["t0_ms"] - prints["ts_ms"]).astype(float)
    q = quantiles(lag.to_numpy(float), [10, 25, 50, 75, 90])
    rows.append({"区分": "遅れ", "量": "p0 の遅れ(t0−ts, ms)", "n": int(lag.size),
                "p10": q[0], "p25": q[1], "p50": q[2], "p75": q[3], "p90": q[4]})
    miss_exit = prints["p_exit_e1_h60"].isna()
    rows.append({"区分": "遅れ", "量": ("60 秒後の出口価格が引けなかった割合"
                                  "(遅れが穴の上限 300,000ms を超えた代理指標。"
                                  "個々の遅れ ms は保存していない — 限界参照)"),
                "n": int(prints.shape[0]), "割合": float(miss_exit.mean())})
    rows.append({"区分": "前半/後半", "量": "日数", "前半": len(days1),
                "後半": len(days2)})
    rows.append({"区分": "前半/後半", "量": "清算数",
                "前半": int((prints["half"] == "前半").sum()),
                "後半": int((prints["half"] == "後半").sum())})
    v_f = prints.loc[prints["half"] == "前半", "p0"].astype(float)
    v_b = prints.loc[prints["half"] == "後半", "p0"].astype(float)
    rows.append({"区分": "前半/後半", "量": "価格帯(p0 の最小〜最大)",
                "前半最小": float(v_f.min()) if v_f.size else NAN,
                "前半最大": float(v_f.max()) if v_f.size else NAN,
                "後半最小": float(v_b.min()) if v_b.size else NAN,
                "後半最大": float(v_b.max()) if v_b.size else NAN})
    return rows


# ===========================================================================
# 6. Jev の下見(前半から層化無作為 200 件、side × 材料1 の3群)
# ===========================================================================
def jev_state_for_print(pid: str, pc: PrintsCSV, all_ts, all_side, all_notional,
                        times, prices, mat_row: dict) -> dict:
    i = int(np.flatnonzero(pc.print_id == pid)[0])
    ts = int(pc.ts[i])
    side = str(pc.side[i])
    s = REACT_SIGN[side]
    lo = np.searchsorted(all_ts, ts - SAME_SIDE_WINDOW_MS, side="left")
    hi = np.searchsorted(all_ts, ts, side="left")
    prints_last_60s = [
        {"t_rel_s": round((int(all_ts[j]) - ts) / 1000.0, 3),
         "notional_usd": round(float(all_notional[j]), 2),
         "side": str(all_side[j])}
        for j in range(lo, hi)]
    anchor_px, _t = price_at_or_before(times, prices, ts - 1)
    path = []
    for sec in range(-60, 1):
        px, _t = price_at_or_before(times, prices, ts + sec * 1000)
        if px == px and anchor_px == anchor_px and anchor_px > 0:
            path.append(round(s * (px - anchor_px) / anchor_px * 1e4, 4))
        else:
            path.append(None)
    materials = {}
    for n in MAT_NUMS:
        v = mat_row.get(MAT_COL[n])
        if n == 6:
            materials[MAT_VAR[n]] = v if isinstance(v, str) and v else None
        else:
            materials[MAT_VAR[n]] = (None if v is None or (isinstance(v, float)
                                     and not math.isfinite(v)) else float(v))
    return {"side": side, "prints_last_60s": prints_last_60s,
            "price_path_bp_last_60s": path, "materials": materials}


JEV_QUESTIONS = {
    "continue": {
        "type": "noul",
        "instructions": ("Given the state of a liquidation cascade on a perpetual "
                        "futures market at the moment of a liquidation print, judge "
                        "whether another same-side liquidation print will occur "
                        "within the next 60 seconds."),
        "criteria": {
            "yes": ("the cascade is likely to continue: price momentum in the "
                   "liquidation direction persists and more positions are likely "
                   "to be liquidated within 60 seconds"),
            "no": ("the cascade is likely to stop: the move is exhausted or "
                  "absorbed and no further same-side liquidation is likely "
                  "within 60 seconds"),
        },
    }
}


def run_jev_preview(out_dir: Path, stage1_df: pd.DataFrame, pc: PrintsCSV,
                    data_root: Path, n_sample: int = 200, seed: int = 20260920,
                    rate_per_sec: float = 2.0) -> dict:
    fh = stage1_df[stage1_df["half"] == "前半"].copy()
    mat1 = pd.to_numeric(fh[MAT_COL[1]], errors="coerce")
    lo, hi = ex5.tertile_cuts(mat1.to_numpy(float))
    fh["_tert"] = np.where(mat1 <= lo, 1, np.where(mat1 <= hi, 2, 3))
    strata = [(s, t) for s in SIDE_LIST for t in (1, 2, 3)]
    rng = random.Random(seed)
    per = n_sample // len(strata)
    extra = n_sample - per * len(strata)
    picked_ids = []
    strata_n = {}
    for i, (s, t) in enumerate(strata):
        pool = fh[(fh["side"] == s) & (fh["_tert"] == t)]["print_id"].tolist()
        k = per + (1 if i < extra else 0)
        rng.shuffle(pool)
        chosen = pool[:k]
        picked_ids += chosen
        strata_n[f"{s}_{t}"] = len(chosen)
    all_ts = pc.all_ts_sorted()
    o = np.argsort(pc.ts, kind="stable")
    all_side = pc.side[o]
    all_notional = pc.notional[o]
    by_day: dict = defaultdict(list)
    row_by_id = {r["print_id"]: r for r in fh.to_dict("records")}
    for pid in picked_ids:
        by_day[row_by_id[pid]["day"]].append(pid)

    client = JevClient(model="jev-1.13.0", log_dir="data/jev/continue")
    trade_cache: dict = {}
    latencies, errors, usages, prob_bands = [], 0, [], [0] * 10
    t_last = 0.0
    n_calls = 0
    for day, pids in by_day.items():
        times, prices, _q, _miss, _need = load_window5(data_root, day, trade_cache,
                                                        400_000, 0)
        for pid in pids:
            dt = time.time() - t_last
            if dt < 1.0 / rate_per_sec:
                time.sleep(1.0 / rate_per_sec - dt)
            t_last = time.time()
            state = jev_state_for_print(pid, pc, all_ts, all_side, all_notional,
                                        times, prices, row_by_id[pid])
            t0c = time.time()
            n_calls += 1
            try:
                resp = client.evaluate(state, JEV_QUESTIONS)
                latencies.append(time.time() - t0c)
                usage = resp.get("usage") or {}
                if usage:
                    usages.append(usage)
                ans = resp.get("answers", {}).get("continue", {})
                p = ans.get("noul")  # noul 質問の確率フィールド名(実測 2026-09-20)
                if isinstance(p, (int, float)) and math.isfinite(p):
                    b = min(9, max(0, int(p * 10)))
                    prob_bands[b] += 1
            except JevError:
                errors += 1
                latencies.append(time.time() - t0c)
    lat_arr = np.array(latencies, dtype=float)
    tok_in = np.array([u.get("input_tokens", NAN) for u in usages], dtype=float)
    return {
        "呼び出し数": n_calls, "エラー数(JevError)": errors,
        "遅延の分位(秒)": {str(q): (float(np.percentile(lat_arr, q))
                            if lat_arr.size else None)
                     for q in (10, 25, 50, 75, 90, 100)},
        "入力トークンの分位": {str(q): (float(np.percentile(tok_in[np.isfinite(tok_in)], q))
                          if np.isfinite(tok_in).any() else None)
                     for q in (10, 25, 50, 75, 90, 100)},
        "確率の10帯の件数": prob_bands,
        "層化の内訳(側_材料1の3群 -> 抽出件数)": strata_n,
        "429 の回数": ("client.py が内部で最大 3 回まで自動再試行するため、この呼び出し側"
                    "からは直接数えられない(限界参照)。エラー数(3 回再試行後も"
                    "失敗した回数)だけを数えた"),
    }


def normalize_rows(rows: list) -> list:
    """`write_csv`/`md_table` は 1 行目の列名を全行に使うので、行ごとに違う鍵を
    持つ表(Q0・Q3・Q7 など)は先に**列の和集合**へそろえる(無い鍵は空欄)。"""
    if not rows:
        return rows
    cols: list = []
    seen = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                cols.append(k)
    return [{c: r.get(c, "") for c in cols} for r in rows]


def drop_chunks(out_dir: Path) -> int:
    n = 0
    for sub in ("chunks1", "chunks3"):
        d = out_dir / sub
        if not d.exists():
            continue
        for f in sorted(d.glob("*")):
            f.unlink()
            n += 1
        d.rmdir()
    return n


# ===========================================================================
# main
# ===========================================================================
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="O3C SIGNAL 続く/止まるの単位")
    ap.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    ap.add_argument("--rows-path", type=Path, default=DEFAULT_ROWS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stage", choices=("rows", "q7", "jev", "tables", "all"),
                    default="all")
    ap.add_argument("--limit-days", type=int, default=0)
    ap.add_argument("--progress-every", type=int, default=20)
    ap.add_argument("--keep-chunks", action="store_true")
    ap.add_argument("--skip-jev", action="store_true")
    a = ap.parse_args(argv)

    t0 = time.time()
    a.out.mkdir(parents=True, exist_ok=True)
    pc = PrintsCSV(a.rows_path)
    days = sorted(pc.by_day.keys())
    if a.limit_days:
        days = days[: a.limit_days]
    half_point = len(days) // 2
    days1, days2 = days[:half_point], days[half_point:]
    half_of = {d: "前半" for d in days1}
    half_of.update({d: "後半" for d in days2})
    print(f"日数 {len(days)}(前半 {len(days1)} / 後半 {len(days2)})、"
          f"プリント {pc.n} 件", flush=True)

    nb = same_side_neighbors(pc)

    if a.stage in ("rows", "all"):
        note1 = run_stage1(a.out, days, half_of, pc, nb, a.data_root,
                           a.progress_every)
        (a.out / "stage1_notes.json").write_text(
            json.dumps(note1, ensure_ascii=False, indent=2))
    if a.stage == "rows":
        return 0

    stage1_df = read_stage1_frame(a.out, days)
    cuts = first_half_cuts(stage1_df)
    stage1_df = add_bands(stage1_df, cuts)
    stage1_df["_b15"] = stage1_df["band_15"]
    stage1_df["_b9"] = stage1_df["band_9"]

    if a.stage in ("q7", "all"):
        all_ts = pc.all_ts_sorted()
        note2 = run_stage2(a.out, days2, pc, cuts, all_ts, stage1_df, a.data_root,
                           a.progress_every)
        (a.out / "stage2_notes.json").write_text(
            json.dumps(note2, ensure_ascii=False, indent=2))
    if a.stage == "q7":
        return 0

    if a.stage in ("jev", "all") and not a.skip_jev:
        jev_note = run_jev_preview(a.out, stage1_df, pc, a.data_root)
        (a.out / "jev_preview_notes.json").write_text(
            json.dumps(jev_note, ensure_ascii=False, indent=2))
    if a.stage == "jev":
        return 0

    concat_rows(a.out, days, days2)

    # --- 表 ---------------------------------------------------------------
    df = load_rows(a.out)
    df = add_bands(df, cuts)
    prints = df[df["kind"] == KIND_PRINT].reset_index(drop=True)
    q7df = df[df["kind"] == KIND_Q7].reset_index(drop=True)
    bh = prints[prints["half"] == "後半"].reset_index(drop=True)
    base_fh_60 = float(prints.loc[prints["half"] == "前半", "label_60"].mean())
    base_by_half = {half: {h: float(prints.loc[prints["half"] == half,
                                               f"label_{h}"].mean())
                           for h in LABEL_SECONDS} for half in ("前半", "後半")}
    rule_bands, rule_continue_set, top3 = build_rules(prints, cuts, base_fh_60)
    judgments = build_judgments(bh, rule_continue_set, top3, rule_bands, base_fh_60)

    q0 = make_q0(prints, days1, days2)
    q1 = make_q1(prints, cuts)
    q2 = make_q2(prints, cuts, rule_bands, rule_continue_set, top3, base_by_half)
    q3 = make_q3_placeholder()
    q4 = make_q4(bh, judgments)
    q5 = make_q5(bh, judgments)
    q6 = [r for r in q4 if r["判断"] == "perfect"]  # Q4 に含む(0 行追加。設計 §7)
    miss_by_band = {}
    p_mb = a.out / "stage2_notes.json"
    if p_mb.exists():
        miss_by_band = json.loads(p_mb.read_text()).get("miss_by_band", {})
    q7 = make_q7(q7df, rule_continue_set, miss_by_band)

    q0, q1, q2, q3, q4, q5, q6, q7 = (normalize_rows(x) for x in
                                      (q0, q1, q2, q3, q4, q5, q6, q7))
    named = [("q0.csv", q0, "Q0", "Q0 自己点検"),
             ("q1.csv", q1, "Q1", "Q1 材料 × ラベル"),
             ("q2.csv", q2, "Q2", "Q2 規則(前半で作り後半で測る)"),
             ("q3.csv", q3, "Q3", "Q3 Jev(この委任では後半に未呼び出し。形だけ)"),
             ("q4.csv", q4, "Q4", "Q4 2 枝の損益(後半だけ)"),
             ("q5.csv", q5, "Q5", "Q5 日ごと(Q4 主格子)"),
             ("q6.csv", q6, "Q6", "Q6 完全な判断の上限(Q4 の perfect 判断の再掲。"
                                 "行数には 0 を加える — 設計 §7「Q6 は Q4 に含む」)"),
             ("q7.csv", q7, "Q7", "Q7 清算の無い時刻の対照")]
    for name, rr, _k, _t in named:
        write_csv(a.out / name, rr)

    row_counts = {key: len(rr) for _n, rr, key, _t in named}
    total_rows = sum(len(rr) for _n, rr, k, _t in named if k != "Q6")

    md = [f"# O3C SIGNAL 続く/止まるの単位の表({days[0]} 〜 {days[-1]}、{len(days)} 日)",
          "",
          "- 設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_CONTINUE_DESIGN_2026-09-20.md`",
          f"- 前半 {len(days1)} 日(切り値・規則を作る)/ 後半 {len(days2)} 日"
          "(的中率・損益を測る)",
          f"- 基準率(前半、60 秒ラベル) = {base_fh_60:.4f}",
          f"- 上位 3 材料(組の規則) = {', '.join(str(n) for n in top3)}"
          f"({', '.join(MAT_VAR[n] for n in top3)})",
          "- 材料は 14 本(§3.1 の 1〜6・8〜15)。材料 6(時刻帯)は UTC 6 時間 × 4 の"
          "カテゴリのまま扱い、10 分位には切っていない(設計に無い判断、報告参照)",
          "- Q3(Jev の後半での的中率・較正)はこの委任では**呼んでいない**"
          "(前半 200 件の下見のみ。設計 §2 Q3・委任文)。Q4・Q5・Q7 の `jev` 判断の行も空欄",
          ""]
    for name, rr, _k, title in named:
        md += [f"## {title}(`{name}`、{len(rr)} 行)", "", md_table(rr), ""]
    mdtxt = "\n".join(md)
    check_no_banned(mdtxt, "tables.md")
    (a.out / "tables.md").write_text(mdtxt)
    n_cells = count_numeric_cells(mdtxt)

    summary = {
        "実行時刻(UTC)": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "経過秒": round(time.time() - t0, 1),
        "設計": "docs/PHASE2/O3C/SIGNAL/SIGNAL_CONTINUE_DESIGN_2026-09-20.md",
        "日数": {"前半": len(days1), "後半": len(days2), "合計": len(days)},
        "プリント数": {"前半": int((prints['half'] == '前半').sum()),
                  "後半": int((prints['half'] == '後半').sum()),
                  "合計": int(prints.shape[0])},
        "Q7 候補の行数": int(q7df.shape[0]),
        "前半の材料の切り値(10分位、材料6を除く)": {
            str(n): [float(x) for x in cuts[n]] for n in MAT_NUMS_CONT},
        "基準率(前半、60秒)": base_fh_60,
        "基準率(半期別)": base_by_half,
        "上位3材料(組の規則)": {"番号": top3, "変数名": [MAT_VAR[n] for n in top3]},
        "表の行数": row_counts,
        "表の行数の合計(Q6 を除く)": total_rows,
        "設計の見積もり(407)との差": total_rows - 407,
        "tables.md の数値セル数": n_cells,
        "tables.md の数え方": ("`|` で始まる表の行のうち、区切り行と各表の見出し行を除いた"
                          "セルを `float()` に掛けて通った数(探索段 5 と同じ数え方)"),
    }
    txt = json.dumps(summary, ensure_ascii=False, indent=2)
    check_no_banned(txt, "summary.json")
    (a.out / "summary.json").write_text(txt)

    if not a.keep_chunks:
        n_drop = drop_chunks(a.out)
        print(f"chunk の中間ファイルを {n_drop} 個消した", flush=True)

    names = (["rows_continue.csv.gz"] + [n for n, _r, _k, _t in named]
             + ["tables.md", "summary.json"])
    lines = []
    for n in names:
        p = a.out / n
        if not p.exists():
            continue
        if n.endswith((".csv", ".md", ".json")):
            check_no_banned(p.read_text(), n)
        lines.append(f"{md5_of(p)}  {n}")
    (a.out / "MD5SUMS").write_text("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)
    print(f"完了 {time.time() - t0:.0f}s -> {a.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

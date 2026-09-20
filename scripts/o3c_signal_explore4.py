#!/usr/bin/env python3
"""清算を起点とした値動きの予測可能性(SIGNAL)— **探索段 4** の道具。

設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE4_DESIGN_2026-09-20.md`
(用語表 / §2 問い G0〜G7 / §4 対照 / §6 データと出力 / §7 走らせる前に決めること)。

**この道具がすること**
  - 束と対照 (b) は 1 周目の走行の表(`backtest_data/o3c_reaction_20260918_full/<run>/table.csv`)
    の行を**そのまま使う**(束を作り直さない)。gap 60 が主、30 / 180 は G1 の一部だけ。
  - 束ごとに約定から引き直す量(設計の用語表):
    基準 p_pre = `at_or_before(start_ms − 1, 300_000)`、
    終端 p_end = `at_or_after(end_ms, 300_000)`、
    T 秒前 p_T = `at_or_before(start_ms − T*1000, 300_000)`、
    h 後 p_h = `at_or_before(終端の約定の時刻 + h*1000, 300_000)`。
  - 符号 s = SELL: −1 / BUY: +1(探索段 1〜3 と同じ向き。負 = 清算と逆)。
    前の値動き m(T) = s × (p_pre − p_T)/p_T × 1e4、
    掃き sweep = s × (p_end − p_pre)/p_pre × 1e4、
    後の逆行 r_end(h) = s × (p_h − p_end)/p_end × 1e4、
    戻り率 g(T,h) = (p_end − p_h)/(p_end − p_T)(分母 = s × (p_end − p_T)/p_T × 1e4 が
    正のときだけ定義する)。
  - 対照 (c) 前の値動き合わせ(設計 §4)、対照 (b) = 1 周目の対照 (i) 日集約版。
  - G7 は Binance(約定から作る 1 分格子)と bitFlyer(1 分足)を同じ格子に置く。
  - 出力は G0〜G7 の表・`rows_gap*.csv.gz`・`tables.md`・`summary.json`・`MD5SUMS`。

**探索段なので判定語を 1 つも書かない。**検定もしない。読み(なぜ)も書かない。

**`paper_logs/` は開かない**(自前記録は判定まで触らない)。この道具は
`backtest_data/` と `docs/` 以外のどのディレクトリも読まない。

読み込み・日クラスタ SE・3 分位の切り方・属性の群・gzip の決定的な書き出しは
探索段 2 / 3 の道具の関数をそのまま呼ぶ。
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import gzip
import importlib.util
import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import o3c_price_level_table as base  # noqa: E402

_spec3 = importlib.util.spec_from_file_location(
    "o3c_signal_explore3", _HERE / "o3c_signal_explore3.py")
ex3 = importlib.util.module_from_spec(_spec3)
assert _spec3.loader is not None
_spec3.loader.exec_module(ex3)
ex2 = ex3.ex2          # 探索段 3 が読み込んだものと同じ実体を使う

REPO_ROOT = _HERE.parent
NAN = float("nan")

# ---------------------------------------------------------------------------
# 固定値(設計 §7。変えるときは報告に列挙する)
# ---------------------------------------------------------------------------
T_ALL = (10, 30, 60, 300, 900)        # G0 の下見(L-255)
T_MAIN = (60, 300)                    # 主の表
HORIZONS_SEC = (1, 5, 10, 30, 60, 300, 900)
H_MAIN = (60, 300, 900)               # G1・G2・G4〜G6
H_SHAPE = (1, 5, 10, 30, 60)          # G3 時間の形
H_GRID = (300, 900)                   # G7 同じ 1 分格子
STALENESS_MS = ex2.STALENESS_MS       # 300_000
RUNS = ex2.RUNS
GAP_OF_RUN = ex2.GAP_OF_RUN
GAPS = (60, 30, 180)
MAIN_GAP = 60
REACT_SIGN = ex2.REACT_SIGN

GRID_STEP_MS = 10_000                 # 対照 (c) の候補時刻の刻み(設計 §4)
GRID_N = 8_640                        # 1 日の候補点
CTRL_WINDOW_MS = 900_000              # 候補の区間の後ろ側(= 最大 h)
N_BANDS = 10                          # m の 10 分位帯
CONT_SEC = 120                        # 続伸 (i) の境界(設計の用語表)
SWEEP_CUTS = (0.2009, 8.0760)         # 掃きの 3 分位(探索段 3 の切り値をそのまま)
G_MIN_DENOM_BP = 1.0                  # g の「分母 ≥ 1 bp」(設計 §7)
MINUTE_MS = 60_000

KIND_LIQ = "liq"
KIND_C = "control_c"
KIND_BI = "control_b_i"
KINDS = (KIND_LIQ, KIND_C, KIND_BI)
KIND_LABEL = {KIND_LIQ: "清算", KIND_C: "対照(c) 前の値動き合わせ",
              KIND_BI: "対照(b) 一様(日集約)"}

DEFAULT_RUNS_DIR = ex2.DEFAULT_RUNS_DIR
DEFAULT_DATA_ROOT = ex2.DEFAULT_DATA_ROOT
DEFAULT_BITFLYER_DIR = ex2.DEFAULT_BITFLYER_DIR
DEFAULT_OUT = REPO_ROOT / "backtest_data" / "o3c_signal_explore4_20260920"

BANNED_WORDS = ex2.BANNED_WORDS

ROW_COLUMNS = (
    ["kind", "cascade_id", "day", "side", "ctrl_T",
     "t_pre_ms", "t_end_ms", "p_pre", "p_end", "baseline_lag_ms", "end_lag_ms",
     "sweep_bp", "prev_bundle_gap_s", "next_bundle_gap_s", "bundles_per_day"]
    + [f"m_{T}" for T in T_ALL]
    + [f"m_lag_ms_{T}" for T in T_ALL]
    + [f"r_end_{h}" for h in HORIZONS_SEC]
    + [f"h_lag_ms_{h}" for h in HORIZONS_SEC]
    + [f"den_bp_{T}" for T in T_MAIN]
    + [f"g_{T}_{h}" for T in T_MAIN for h in H_MAIN]
    + [f"bn_grid_{h}" for h in H_GRID]
    + [f"bf_grid_{h}" for h in H_GRID]
    + ["matched_liq_id", "c_t", "ctrl_t_ms"])
CHUNK_HEADER = ["gap"] + ROW_COLUMNS

# ===========================================================================
# 小道具(探索段 2・3 から借りるもの)
# ===========================================================================
_f = ex2._f
_fmt = ex2._fmt
mean_se_cluster = ex2.mean_se_cluster
gz_open_w = ex2.gz_open_w
md5_of = ex2.md5_of
write_csv = ex2.write_csv
md_table = ex2.md_table
calendar_gaps = ex2.calendar_gaps
tertile_cuts = ex2.tertile_cuts
tertile_mask = ex2.tertile_mask
day_equal_weight_mean = ex3.day_equal_weight_mean
quantiles = ex3.quantiles
idx_at_or_before = ex3.idx_at_or_before
idx_at_or_after = ex3.idx_at_or_after
day_start_ms = ex3.day_start_ms
load_window = ex3.load_window
Bundles = ex3.Bundles
load_mixed = ex3.load_mixed
DASH = "—"


def check_no_banned(text: str, where: str) -> None:
    hit = [w for w in BANNED_WORDS if w in text]
    if hit:
        raise SystemExit(f"[止め] 判定語が出力に混ざっている({where}): {hit}")


def band_cuts_m(vals: np.ndarray) -> np.ndarray:
    """同じ gap の**全束**の m の 10 分位の切り値 q_1 … q_9(負も含む)。"""
    v = np.asarray(vals, dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return np.zeros(N_BANDS - 1)
    return np.quantile(v, [i / N_BANDS for i in range(1, N_BANDS)])


def band_of_m(v, cuts: np.ndarray):
    """帯 1 = (−∞, q_1)、帯 k ≥ 2 = [q_{k−1}, q_k)、帯 10 = [q_9, +∞)。NaN は −1。"""
    v = np.asarray(v, dtype=float)
    k = np.searchsorted(cuts, v, side="right") + 1
    return np.where(np.isfinite(v), k, -1)


def band_bounds(cuts: np.ndarray, k: int) -> tuple:
    lo = -math.inf if k == 1 else float(cuts[k - 2])
    hi = math.inf if k == N_BANDS else float(cuts[k - 1])
    return lo, hi


def bound_text(x) -> object:
    """表に出す帯の境。±∞ は空欄ではなく記号で書く(欠測と見分けるため)。"""
    v = float(x)
    if v == math.inf:
        return "+∞"
    if v == -math.inf:
        return "−∞"
    return v


def corr(a: np.ndarray, b: np.ndarray) -> float:
    ok = np.isfinite(a) & np.isfinite(b)
    if int(ok.sum()) < 3:
        return NAN
    x, y = a[ok], b[ok]
    if float(x.std()) == 0.0 or float(y.std()) == 0.0:
        return NAN
    return float(np.corrcoef(x, y)[0, 1])


# ===========================================================================
# 束・対照の 1 行ぶんの量
# ===========================================================================
def measure(times: np.ndarray, prices: np.ndarray,
            t_pre_req, t_end_req, sign, t_m_req: dict | None = None) -> dict:
    """基準・終端・T 秒前・h 後を引いて、この段の量を全部返す。

    行は落とさない(引けなければ NaN)。どの点も**時刻だけ**で選ぶ
    (価格は選んだあとに読む = 先読みをしていない)。
    `t_pre_req` が None なら基準の無い行(対照 (b))。
    """
    t_end_req = np.asarray(t_end_req, dtype=np.int64)
    sign = np.asarray(sign, dtype=float)
    n = int(t_end_req.size)
    out: dict = {}
    i_end, ok_end = idx_at_or_after(times, t_end_req, STALENESS_MS)
    t_end = np.where(ok_end, times[i_end] if times.size else 0, -1).astype(np.int64)
    p_end = np.where(ok_end, prices[i_end] if times.size else NAN, NAN)
    out["ok_end"] = ok_end
    out["t_end_ms"] = t_end
    out["p_end"] = p_end
    out["end_lag_ms"] = np.where(ok_end, (t_end - t_end_req).astype(float), NAN)

    if t_pre_req is None:
        ok_pre = np.zeros(n, dtype=bool)
        t_pre = np.full(n, -1, dtype=np.int64)
        p_pre = np.full(n, NAN)
        pre_lag = np.full(n, NAN)
    else:
        t_pre_req = np.asarray(t_pre_req, dtype=np.int64)
        i_pre, ok_pre = idx_at_or_before(times, t_pre_req, STALENESS_MS)
        t_pre = np.where(ok_pre, times[i_pre] if times.size else 0, -1).astype(np.int64)
        p_pre = np.where(ok_pre, prices[i_pre] if times.size else NAN, NAN)
        pre_lag = np.where(ok_pre, (t_pre_req - t_pre).astype(float), NAN)
    out["ok_pre"] = ok_pre
    out["t_pre_ms"] = t_pre
    out["p_pre"] = p_pre
    out["pre_lag_ms"] = pre_lag

    with np.errstate(invalid="ignore", divide="ignore"):
        out["sweep_bp"] = np.where(ok_pre & ok_end & (p_pre > 0),
                                   sign * (p_end - p_pre) / p_pre * 1e4, NAN)

    p_h_of: dict = {}
    for h in HORIZONS_SEC:
        tgt = np.where(ok_end, t_end + h * 1000, 0)
        i_h, ok_h = idx_at_or_before(times, tgt, STALENESS_MS)
        ok_h = ok_h & ok_end
        p_h = np.where(ok_h, prices[i_h] if times.size else NAN, NAN)
        t_h = times[i_h] if times.size else np.zeros(n, dtype=np.int64)
        p_h_of[h] = (p_h, ok_h)
        out[f"h_lag_ms_{h}"] = np.where(ok_h, (tgt - t_h).astype(float), NAN)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[f"r_end_{h}"] = np.where(ok_h & (p_end > 0),
                                         sign * (p_h - p_end) / p_end * 1e4, NAN)

    t_m_req = t_m_req or {}
    for T in T_ALL:
        if T not in t_m_req:
            continue
        tq = np.asarray(t_m_req[T], dtype=np.int64)
        i_m, ok_m = idx_at_or_before(times, tq, STALENESS_MS)
        t_m = np.where(ok_m, times[i_m] if times.size else 0, -1).astype(np.int64)
        p_m = np.where(ok_m, prices[i_m] if times.size else NAN, NAN)
        out[f"ok_m_{T}"] = ok_m
        out[f"t_m_ms_{T}"] = t_m
        out[f"m_lag_ms_{T}"] = np.where(ok_m, (tq - t_m).astype(float), NAN)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[f"m_{T}"] = np.where(ok_m & ok_pre & (p_m > 0),
                                     sign * (p_pre - p_m) / p_m * 1e4, NAN)
            den_bp = np.where(ok_m & ok_end & (p_m > 0),
                              sign * (p_end - p_m) / p_m * 1e4, NAN)
        if T in T_MAIN:
            out[f"den_bp_{T}"] = den_bp
            for h in H_MAIN:
                p_h, ok_h = p_h_of[h]
                with np.errstate(invalid="ignore", divide="ignore"):
                    out[f"g_{T}_{h}"] = np.where(
                        ok_h & ok_m & ok_end & np.isfinite(den_bp) & (den_bp > 0),
                        (p_end - p_h) / (p_end - p_m), NAN)
    return out


def grid_returns(times: np.ndarray, prices: np.ndarray, bf: dict,
                 start_ms: np.ndarray, sign: np.ndarray) -> dict:
    """G7: Binance と bitFlyer を**同じ 1 分格子**に置いた符号付き変化(bp)。

    基準 = `start_ms` を含む足の 1 本前の終値 = 格子点 `floor_1m(start_ms)` の値。
    どちらの会場も `at_or_before(floor_1m(start_ms) − 1 + h*1000, 300_000)` で引く
    (bitFlyer は 1 分足の終値、Binance は同じ格子点までの最終約定 = その足の終値)。
    """
    start_ms = np.asarray(start_ms, dtype=np.int64)
    sign = np.asarray(sign, dtype=float)
    base_ts = (start_ms // MINUTE_MS) * MINUTE_MS - 1
    i0, ok0 = idx_at_or_before(times, base_ts, STALENESS_MS)
    bn0 = np.where(ok0, prices[i0] if times.size else NAN, NAN)
    bf0 = ex2.bf_close_at_or_before(bf, base_ts)
    out: dict = {}
    for h in H_GRID:
        tgt = base_ts + h * 1000
        i1, ok1 = idx_at_or_before(times, tgt, STALENESS_MS)
        bn1 = np.where(ok1, prices[i1] if times.size else NAN, NAN)
        bf1 = ex2.bf_close_at_or_before(bf, tgt)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[f"bn_grid_{h}"] = np.where(ok0 & ok1 & (bn0 > 0),
                                           sign * (bn1 - bn0) / bn0 * 1e4, NAN)
            out[f"bf_grid_{h}"] = np.where(
                np.isfinite(bf0) & (bf0 > 0) & np.isfinite(bf1),
                sign * (bf1 - bf0) / bf0 * 1e4, NAN)
    return out


# ===========================================================================
# 行の書き出し
# ===========================================================================
def _row(gap, kind, cid, day, side, m, k, grid=None, ctrl_T="",
         prev_gap=None, next_gap=None, bpd=None, matched="", c_t=None,
         ctrl_t=None) -> list:
    d = {c: "" for c in CHUNK_HEADER}
    ok_pre = bool(m["ok_pre"][k])
    ok_end = bool(m["ok_end"][k])
    d["gap"] = gap
    d["kind"] = kind
    d["cascade_id"] = cid
    d["day"] = day
    d["side"] = side
    d["ctrl_T"] = ctrl_T
    d["t_pre_ms"] = int(m["t_pre_ms"][k]) if ok_pre else ""
    d["t_end_ms"] = int(m["t_end_ms"][k]) if ok_end else ""
    d["p_pre"] = _fmt(m["p_pre"][k], 4) if ok_pre else ""
    d["p_end"] = _fmt(m["p_end"][k], 4) if ok_end else ""
    # baseline_lag_ms = 求めた時刻(清算は start_ms、対照 (c) は t)− 基準の約定の時刻
    d["baseline_lag_ms"] = (int(m["pre_lag_ms"][k]) + (1 if kind == KIND_LIQ else 0)
                            if ok_pre else "")
    d["end_lag_ms"] = int(m["end_lag_ms"][k]) if ok_end else ""
    d["sweep_bp"] = _fmt(m["sweep_bp"][k], 6)
    d["prev_bundle_gap_s"] = ("" if prev_gap is None or not math.isfinite(prev_gap)
                              else _fmt(prev_gap, 3))
    d["next_bundle_gap_s"] = ("" if next_gap is None or not math.isfinite(next_gap)
                              else _fmt(next_gap, 3))
    d["bundles_per_day"] = "" if bpd is None else int(bpd)
    for T in T_ALL:
        if f"m_{T}" in m:
            d[f"m_{T}"] = _fmt(m[f"m_{T}"][k], 6)
            v = m[f"m_lag_ms_{T}"][k]
            d[f"m_lag_ms_{T}"] = "" if not math.isfinite(v) else int(v)
    for T in T_MAIN:
        if f"den_bp_{T}" in m:
            d[f"den_bp_{T}"] = _fmt(m[f"den_bp_{T}"][k], 6)
            for h in H_MAIN:
                d[f"g_{T}_{h}"] = _fmt(m[f"g_{T}_{h}"][k], 6)
    for h in HORIZONS_SEC:
        d[f"r_end_{h}"] = _fmt(m[f"r_end_{h}"][k], 6)
        v = m[f"h_lag_ms_{h}"][k]
        d[f"h_lag_ms_{h}"] = "" if not math.isfinite(v) else int(v)
    if grid is not None:
        for h in H_GRID:
            d[f"bn_grid_{h}"] = _fmt(grid[f"bn_grid_{h}"][k], 6)
            d[f"bf_grid_{h}"] = _fmt(grid[f"bf_grid_{h}"][k], 6)
    d["matched_liq_id"] = matched
    d["c_t"] = "" if c_t is None else _fmt(c_t, 6)
    d["ctrl_t_ms"] = "" if ctrl_t is None else int(ctrl_t)
    return [d[c] for c in CHUNK_HEADER]


# ===========================================================================
# 段 1: 清算 + 対照 (b) の行
# ===========================================================================
def stage1_day(day: str, bundles: dict, tables: dict, times: np.ndarray,
               prices: np.ndarray, bf: dict, bundles_per_day: dict) -> list:
    out: list = []
    bpd = bundles_per_day.get(day, 0)
    for run in RUNS:
        gap = GAP_OF_RUN[run]
        bd = bundles[gap]
        t = tables[run]
        ks = bd.by_day.get(day, np.zeros(0, dtype=int))
        if ks.size:
            start = bd.start_ms[ks]
            end = bd.end_ms[ks]
            sign = bd.sign[ks]
            m = measure(times, prices, start - 1, end, sign,
                        {T: start - T * 1000 for T in T_ALL})
            grid = grid_returns(times, prices, bf, start, sign)
            for j, k in enumerate(ks.tolist()):
                out.append(_row(gap, KIND_LIQ, bd.cascade_id[k], day, bd.side[k],
                                m, j, grid=grid,
                                prev_gap=float(bd.prev_bundle_gap_s[k]),
                                next_gap=float(bd.next_bundle_gap_s[k]), bpd=bpd))
        sel = np.flatnonzero((t.kind == ex2.KIND_UNIFORM) & (t.day == day))
        if sel.size:
            # 日集約版は符号を持たない(生の変化を残し、表で束の符号を掛ける)
            tms = t.time_ms[sel].astype(np.int64)
            m = measure(times, prices, None, tms, np.ones(sel.size))
            for j, i in enumerate(sel.tolist()):
                out.append(_row(gap, KIND_BI, t.cascade_id[i], day, "", m, j,
                                bpd=bpd))
    return out


# ===========================================================================
# 段 2: 対照 (c) 前の値動き合わせ(設計 §4)
# ===========================================================================
def _block(allowed: np.ndarray, a: int, b: int, t_ms: int, d0: int) -> None:
    """区間 [a, b] と [t − T 秒, t + 900 秒] が重なる候補 t を落とす。"""
    klo = max(0, -(-(a - CTRL_WINDOW_MS - d0) // GRID_STEP_MS))
    khi = min(GRID_N - 1, (b + t_ms - d0) // GRID_STEP_MS)
    if khi >= klo:
        allowed[int(klo):int(khi) + 1] = False


def select_control_c(day: str, bd: Bundles, T: int, cuts: np.ndarray,
                     m_all: np.ndarray, times: np.ndarray, prices: np.ndarray,
                     taken: dict):
    """その日の束に対照 (c) を 1 つずつ当てる(`start_ms` の順、置換なし)。"""
    ks = bd.by_day.get(day, np.zeros(0, dtype=int))
    note = {"n_bundles": 0, "n_taken": 0}
    if not ks.size:
        return [], note
    t_ms = T * 1000
    d0 = day_start_ms(day)
    grid = d0 + np.arange(GRID_N, dtype=np.int64) * GRID_STEP_MS
    grid_hi = int(grid[-1])
    _i_ge, ok_ge = idx_at_or_after(times, grid, STALENESS_MS)
    i_gp, ok_gp = idx_at_or_before(times, grid, STALENESS_MS)
    i_gt, ok_gt = idx_at_or_before(times, grid - t_ms, STALENESS_MS)
    p_gp = np.where(ok_gp, prices[i_gp] if times.size else NAN, NAN)
    p_gt = np.where(ok_gt, prices[i_gt] if times.size else NAN, NAN)
    with np.errstate(invalid="ignore", divide="ignore"):
        raw = np.where(ok_gp & ok_gt & (p_gt > 0), (p_gp - p_gt) / p_gt * 1e4, NAN)
    allowed0 = ok_ge & ok_gp & ok_gt & np.isfinite(raw)

    # 設計 §4 手順 1: 同じ gap のどの束の [start_ms, end_ms] とも重ならない候補だけ残す
    lo_b = d0 - t_ms - bd.max_width_ms
    hi_b = grid_hi + CTRL_WINDOW_MS
    a0 = int(np.searchsorted(bd.start_ms, lo_b, side="left"))
    a1 = int(np.searchsorted(bd.start_ms, hi_b, side="right"))
    for a, b in zip(bd.start_ms[a0:a1].tolist(), bd.end_ms[a0:a1].tolist()):
        _block(allowed0, a, b, t_ms, d0)
    prev_day = (_dt.date.fromisoformat(day) - _dt.timedelta(days=1)).isoformat()

    rows: list = []
    for k in ks.tolist():
        m_b = float(m_all[k])
        note["n_bundles"] += 1
        if not math.isfinite(m_b):
            continue
        band_b = int(band_of_m(m_b, cuts))
        allowed = allowed0.copy()
        for dd in (prev_day, day):
            for a, b in taken.get(dd, ()):
                _block(allowed, a, b, t_ms, d0)
        cand = np.flatnonzero(allowed)
        if cand.size == 0:
            continue
        c = bd.sign[k] * raw[cand]
        same = band_of_m(c, cuts) == band_b
        if not bool(same.any()):
            continue
        diff = np.where(same, np.abs(c - m_b), np.inf)
        j = int(np.argmin(diff))
        t = int(grid[cand[j]])
        taken.setdefault(day, []).append((t - t_ms, t + CTRL_WINDOW_MS))
        note["n_taken"] += 1
        sign1 = np.array([bd.sign[k]])
        m = measure(times, prices, np.array([t], dtype=np.int64),
                    np.array([t], dtype=np.int64), sign1,
                    {T: np.array([t - t_ms], dtype=np.int64)})
        rows.append(_row(MAIN_GAP, KIND_C, bd.cascade_id[k], day, bd.side[k], m, 0,
                         ctrl_T=T, matched=str(bd.cascade_id[k]),
                         c_t=float(c[j]), ctrl_t=t))
    return rows, note


# ===========================================================================
# 走行(chunk で書き、再開できる)
# ===========================================================================
def run_stage1(out_dir: Path, days: list, bundles, tables, data_root: Path,
               bf: dict, bundles_per_day: dict, progress_every: int) -> dict:
    work = out_dir / "chunks1"
    work.mkdir(parents=True, exist_ok=True)
    agg_cache: dict = {}
    missing: set = set()
    maxw = max(b.max_width_ms for b in bundles.values())
    back = max(T_ALL) * 1000 + STALENESS_MS + maxw
    fwd = max(HORIZONS_SEC) * 1000 + STALENESS_MS
    t0 = time.time()
    for n_done, day in enumerate(days, start=1):
        cp = work / f"{day}.csv.gz"
        if cp.exists():
            continue
        times, prices, miss = load_window(data_root, day, agg_cache, back, fwd)
        missing |= set(miss)
        rows = stage1_day(day, bundles, tables, times, prices, bf, bundles_per_day)
        tmp = work / f".{day}.part"
        with gz_open_w(tmp) as fh:
            w = csv.writer(fh)
            w.writerow(CHUNK_HEADER)
            w.writerows(rows)
        tmp.replace(cp)
        if n_done % progress_every == 0:
            print(f"  段1 {n_done}/{len(days)} 日 ({day}) 経過 {time.time() - t0:.0f}s",
                  flush=True)
    return {"agg_days_missing": sorted(missing)}


def read_m(out_dir: Path, days: list, bundles: dict) -> dict:
    """段 1 の chunk から束ごとの m(T) を読む(並びは `Bundles` の並び)。"""
    mm = {gap: {T: np.full(bundles[gap].n, NAN) for T in T_MAIN} for gap in GAPS}
    for day in days:
        cp = out_dir / "chunks1" / f"{day}.csv.gz"
        if not cp.exists():
            continue
        with gzip.open(cp, "rt", newline="") as fh:
            for r in csv.DictReader(fh):
                if r["kind"] != KIND_LIQ:
                    continue
                gap = int(r["gap"])
                k = bundles[gap].pos_of_id.get(r["cascade_id"])
                if k is None:
                    continue
                for T in T_MAIN:
                    mm[gap][T][k] = _f(r[f"m_{T}"])
    return mm


def _taken_from_chunk(path: Path, T: int) -> list:
    out = []
    if not path.exists():
        return out
    with gzip.open(path, "rt", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["kind"] != KIND_C or not r["ctrl_t_ms"] or int(r["ctrl_T"]) != T:
                continue
            t = int(r["ctrl_t_ms"])
            out.append((t - T * 1000, t + CTRL_WINDOW_MS))
    return out


def run_stage2(out_dir: Path, days: list, bundles, m_by_gap: dict,
               data_root: Path, progress_every: int) -> dict:
    work = out_dir / "chunks2"
    work.mkdir(parents=True, exist_ok=True)
    bd = bundles[MAIN_GAP]
    cuts = {T: band_cuts_m(m_by_gap[MAIN_GAP][T]) for T in T_MAIN}
    agg_cache: dict = {}
    notes = {T: {"n_bundles": 0, "n_taken": 0} for T in T_MAIN}
    taken: dict = {T: {} for T in T_MAIN}
    back = max(T_MAIN) * 1000 + STALENESS_MS + bd.max_width_ms
    fwd = CTRL_WINDOW_MS + max(HORIZONS_SEC) * 1000 + STALENESS_MS
    t0 = time.time()
    for n_done, day in enumerate(days, start=1):
        cp = work / f"{day}.csv.gz"
        prev_day = (_dt.date.fromisoformat(day) - _dt.timedelta(days=1)).isoformat()
        if cp.exists():
            for T in T_MAIN:
                taken[T] = {day: _taken_from_chunk(cp, T)}
            continue
        times, prices, _miss = load_window(data_root, day, agg_cache, back, fwd)
        rows = []
        for T in T_MAIN:
            r, note = select_control_c(day, bd, T, cuts[T], m_by_gap[MAIN_GAP][T],
                                       times, prices, taken[T])
            rows += r
            notes[T]["n_bundles"] += note["n_bundles"]
            notes[T]["n_taken"] += note["n_taken"]
            taken[T] = {k: v for k, v in taken[T].items() if k in (prev_day, day)}
        tmp = work / f".{day}.part"
        with gz_open_w(tmp) as fh:
            w = csv.writer(fh)
            w.writerow(CHUNK_HEADER)
            w.writerows(rows)
        tmp.replace(cp)
        if n_done % progress_every == 0:
            print(f"  段2 {n_done}/{len(days)} 日 ({day}) 経過 {time.time() - t0:.0f}s",
                  flush=True)
    return {"cuts": {str(T): [float(x) for x in cuts[T]] for T in T_MAIN},
            "notes": {str(T): notes[T] for T in T_MAIN}}


def concat_rows(out_dir: Path, days: list) -> dict:
    paths, handles, counts = {}, {}, {}
    for gap in GAPS:
        p = out_dir / f"rows_gap{gap}.csv.gz"
        paths[gap] = p
        fh = gz_open_w(Path(str(p) + ".part"))
        w = csv.writer(fh)
        w.writerow(ROW_COLUMNS)
        handles[gap] = (fh, w)
        counts[gap] = 0
    for day in days:
        for sub in ("chunks1", "chunks2"):
            cp = out_dir / sub / f"{day}.csv.gz"
            if not cp.exists():
                continue
            with gzip.open(cp, "rt", newline="") as fh:
                rd = csv.reader(fh)
                next(rd)
                for row in rd:
                    gap = int(row[0])
                    handles[gap][1].writerow(row[1:])
                    counts[gap] += 1
    for gap in GAPS:
        handles[gap][0].close()
        Path(str(paths[gap]) + ".part").replace(paths[gap])
    print("行数 " + " / ".join(f"gap{g} {counts[g]}" for g in GAPS), flush=True)
    return paths


def drop_chunks(out_dir: Path) -> int:
    """chunk の中間ファイルを消す(委任文【出力】)。"""
    n = 0
    for sub in ("chunks1", "chunks2"):
        d = out_dir / sub
        if not d.exists():
            continue
        for p in sorted(d.glob("*")):
            p.unlink()
            n += 1
        d.rmdir()
    return n


# ===========================================================================
# 集計
# ===========================================================================
NUMERIC_COLS = (["ctrl_T", "t_pre_ms", "t_end_ms", "p_pre", "p_end",
                 "baseline_lag_ms", "end_lag_ms", "sweep_bp", "prev_bundle_gap_s",
                 "next_bundle_gap_s", "bundles_per_day", "c_t", "ctrl_t_ms"]
                + [f"m_{T}" for T in T_ALL]
                + [f"m_lag_ms_{T}" for T in T_ALL]
                + [f"r_end_{h}" for h in HORIZONS_SEC]
                + [f"h_lag_ms_{h}" for h in HORIZONS_SEC]
                + [f"den_bp_{T}" for T in T_MAIN]
                + [f"g_{T}_{h}" for T in T_MAIN for h in H_MAIN]
                + [f"bn_grid_{h}" for h in H_GRID]
                + [f"bf_grid_{h}" for h in H_GRID])


class Rows:
    """`rows_gap*.csv.gz` を kind ごとに開いたもの。"""

    def __init__(self, path: Path):
        cols: dict = {c: [] for c in ROW_COLUMNS}
        with gzip.open(path, "rt", newline="") as fh:
            for r in csv.DictReader(fh):
                for c in ROW_COLUMNS:
                    cols[c].append(r[c])
        kind = np.array(cols["kind"], dtype=object)
        self.blk: dict = {}
        for k in KINDS:
            m = kind == k
            b: dict = {}
            for c in ("cascade_id", "day", "side", "matched_liq_id"):
                b[c] = np.array(cols[c], dtype=object)[m]
            for c in NUMERIC_COLS:
                b[c] = np.array([_f(x) for x in cols[c]], dtype=float)[m]
            b["_n"] = int(m.sum())
            self.blk[k] = b


def r_stats(blk: dict, mask: np.ndarray, h: int) -> dict:
    """r_end(h) の平均・SE 3 種・比・日等重み。"""
    v = blk[f"r_end_{h}"][mask]
    days = blk["day"][mask]
    mean, se, naive, n, g = mean_se_cluster(v, days)
    ratio = se / naive if (math.isfinite(se) and math.isfinite(naive)
                           and naive > 0) else NAN
    return {"n": n, "含む日数": g, "r_end 平均(bp)": mean,
            "r_end 日クラスタ SE": se, "r_end naive SE": naive,
            "日クラスタ/naive": ratio,
            "r_end 日等重み平均": day_equal_weight_mean(v, days)}


def cont_ii(blk: dict, mask: np.ndarray, h: int) -> dict:
    """続伸 (ii): r_end(h) > 0 の割合(母数つき)。"""
    v = blk[f"r_end_{h}"][mask]
    fin = v[np.isfinite(v)]
    return {"r_end > 0 の割合": float((fin > 0).mean()) if fin.size else NAN,
            "r_end > 0 の母数": int(fin.size)}


def cont_i(blk: dict, mask: np.ndarray) -> dict:
    """続伸 (i): 次の束が CONT_SEC 秒以内に始まる割合(母数つき)。"""
    v = blk["next_bundle_gap_s"][mask]
    fin = np.isfinite(v)
    vv = v[fin]
    return {f"次の束が {CONT_SEC} 秒以内の割合":
            float((vv <= CONT_SEC).mean()) if vv.size else NAN,
            f"次の束が {CONT_SEC} 秒以内の母数": int(fin.sum()),
            "次の束の間隔が無い束": int((~fin).sum())}


def g_stats(blk: dict, mask: np.ndarray, T: int, h: int) -> dict:
    """g(T,h) の中央値と 3 区分を「分母 > 0」「分母 ≥ 1 bp」の 2 通りで。"""
    gv = blk[f"g_{T}_{h}"][mask]
    den = blk[f"den_bp_{T}"][mask]
    out: dict = {}
    for tag, sel in (("分母>0", np.isfinite(gv)),
                     ("分母≥1bp", np.isfinite(gv) & np.isfinite(den)
                      & (den >= G_MIN_DENOM_BP))):
        v = gv[sel]
        out[f"g 中央値({tag})"] = float(np.median(v)) if v.size else NAN
        out[f"g > 1 の割合({tag})"] = float((v > 1).mean()) if v.size else NAN
        out[f"0 ≤ g ≤ 1 の割合({tag})"] = (
            float(((v >= 0) & (v <= 1)).mean()) if v.size else NAN)
        out[f"g < 0 の割合({tag})"] = float((v < 0).mean()) if v.size else NAN
        out[f"g の母数({tag})"] = int(v.size)
    return out


def m_band_masks(blk: dict, T: int, cuts: np.ndarray) -> list:
    bands = band_of_m(blk[f"m_{T}"], cuts)
    out = []
    for k in range(1, N_BANDS + 1):
        lo, hi = band_bounds(cuts, k)
        out.append((k, lo, hi, bands == k))
    return out


def m_tertile_masks(blk: dict, T: int, lo: float, hi: float) -> list:
    v = blk[f"m_{T}"]
    return [(label, tertile_mask(v, lo, hi, q)) for q, label in ex2.TERTILE_LABELS]


# ---------------------------------------------------------------------------
# G0 自己点検
# ---------------------------------------------------------------------------
G0_COLS = ["区分", "gap(秒)", "種", "T(秒)", "量", "群", "n", "母数", "割合",
           "p10", "p50", "p90", "p99", "最大",
           "m の中央値", "掃きの中央値", "r_end(60) の中央値",
           "m と r_end(60) の相関(束の行)", "m と r_end(60) の相関(日ごとの平均)"]


def _g0(**kw) -> dict:
    row = {c: DASH for c in G0_COLS}
    row.update(kw)
    return row


def _q(v, row: dict) -> dict:
    p = quantiles(v, [10, 50, 90, 99, 100])
    row.update({"p10": p[0], "p50": p[1], "p90": p[2], "p99": p[3], "最大": p[4]})
    return row


def make_g0(rows_by_gap: dict, cuts: dict, ctrl_notes: dict) -> list:
    """gap 60 の清算側と対照 (c) の自己点検(設計 §2 G0・§4)。"""
    blk = rows_by_gap[MAIN_GAP].blk[KIND_LIQ]
    n_all = blk["_n"]
    out: list = []

    # --- 遅れ ---------------------------------------------------------------
    out.append(_q(blk["baseline_lag_ms"],
                  _g0(区分="遅れ", **{"gap(秒)": MAIN_GAP}, 種=KIND_LABEL[KIND_LIQ],
                      量="基準の遅れ(ms)", 群="全体",
                      n=int(np.isfinite(blk["baseline_lag_ms"]).sum()), 母数=n_all)))
    out.append(_q(blk["end_lag_ms"],
                  _g0(区分="遅れ", **{"gap(秒)": MAIN_GAP}, 種=KIND_LABEL[KIND_LIQ],
                      量="終端の遅れ(ms)", 群="全体",
                      n=int(np.isfinite(blk["end_lag_ms"]).sum()), 母数=n_all)))
    for T in T_ALL:
        v = blk[f"m_lag_ms_{T}"]
        out.append(_q(v, _g0(区分="遅れ", **{"gap(秒)": MAIN_GAP},
                             種=KIND_LABEL[KIND_LIQ], **{"T(秒)": T},
                             量="m の窓の遅れ(ms)", 群="全体",
                             n=int(np.isfinite(v).sum()), 母数=n_all)))
    for T in T_ALL:
        # 実経過 = 基準の約定の時刻 − T 秒前の約定の時刻
        elapsed = T * 1000.0 + blk[f"m_lag_ms_{T}"] - blk["baseline_lag_ms"]
        out.append(_q(elapsed, _g0(区分="遅れ", **{"gap(秒)": MAIN_GAP},
                                   種=KIND_LABEL[KIND_LIQ], **{"T(秒)": T},
                                   量="m の窓の実経過(ms)", 群="全体",
                                   n=int(np.isfinite(elapsed).sum()), 母数=n_all)))
    for h in HORIZONS_SEC:
        v = blk[f"h_lag_ms_{h}"]
        out.append(_q(v, _g0(区分="遅れ", **{"gap(秒)": MAIN_GAP},
                             種=KIND_LABEL[KIND_LIQ],
                             量=f"h 後の遅れ(ms) h={h}", 群="全体",
                             n=int(np.isfinite(v).sum()), 母数=n_all)))

    # --- 欠測と掃きの内訳(反証者 3 の「直すべき 3」)--------------------------
    sw = blk["sweep_bp"]
    p_pre, p_end = blk["p_pre"], blk["p_end"]
    same_price = np.isfinite(p_pre) & np.isfinite(p_end) & (p_pre == p_end)
    out.append(_g0(区分="欠測と内訳", **{"gap(秒)": MAIN_GAP}, 種=KIND_LABEL[KIND_LIQ],
                   量="掃きなし(p_end = p_pre)の束", 群="全体",
                   n=int(same_price.sum()), 母数=n_all,
                   割合=float(same_price.mean()) if n_all else NAN))
    neg = np.isfinite(sw) & (sw < 0)
    out.append(_g0(区分="欠測と内訳", **{"gap(秒)": MAIN_GAP}, 種=KIND_LABEL[KIND_LIQ],
                   量="掃きが逆(sweep < 0)の束", 群="全体",
                   n=int(neg.sum()), 母数=n_all,
                   割合=float(neg.mean()) if n_all else NAN))
    for T in T_ALL:
        bad = ~np.isfinite(blk[f"m_{T}"])
        out.append(_g0(区分="欠測と内訳", **{"gap(秒)": MAIN_GAP},
                       種=KIND_LABEL[KIND_LIQ], **{"T(秒)": T},
                       量="m が引けない束", 群="全体",
                       n=int(bad.sum()), 母数=n_all,
                       割合=float(bad.mean()) if n_all else NAN))
    bad = ~np.isfinite(blk["r_end_60"])
    out.append(_g0(区分="欠測と内訳", **{"gap(秒)": MAIN_GAP}, 種=KIND_LABEL[KIND_LIQ],
                   量="r_end(60) が引けない束", 群="全体",
                   n=int(bad.sum()), 母数=n_all,
                   割合=float(bad.mean()) if n_all else NAN))

    # --- T の下見(L-255、5 行)----------------------------------------------
    r60 = blk["r_end_60"]
    days = blk["day"]
    for T in T_ALL:
        v = blk[f"m_{T}"]
        fin = v[np.isfinite(v)]
        acc_m: dict = defaultdict(list)
        acc_r: dict = defaultdict(list)
        ok = np.isfinite(v) & np.isfinite(r60)
        for x, y, d in zip(v[ok].tolist(), r60[ok].tolist(), days[ok].tolist()):
            acc_m[d].append(x)
            acc_r[d].append(y)
        keys = sorted(acc_m)
        dm = np.array([sum(acc_m[d]) / len(acc_m[d]) for d in keys])
        dr = np.array([sum(acc_r[d]) / len(acc_r[d]) for d in keys])
        row = _g0(区分="T の下見", **{"gap(秒)": MAIN_GAP}, 種=KIND_LABEL[KIND_LIQ],
                  **{"T(秒)": T}, 量="m(T) の分布と r_end(60) との相関", 群=f"T={T}",
                  n=int(fin.size), 母数=n_all,
                  割合=float((fin <= 0).mean()) if fin.size else NAN)
        p = quantiles(v, [10, 50, 90])
        row.update({"p10": p[0], "p50": p[1], "p90": p[2],
                    "m と r_end(60) の相関(束の行)": corr(v, r60),
                    "m と r_end(60) の相関(日ごとの平均)": corr(dm, dr)})
        out.append(row)

    # --- g の分母(設計 §7)---------------------------------------------------
    for T in T_MAIN:
        den = blk[f"den_bp_{T}"]
        fin = np.isfinite(den)
        n_fin = int(fin.sum())
        out.append(_q(den, _g0(区分="g の分母", **{"gap(秒)": MAIN_GAP},
                               種=KIND_LABEL[KIND_LIQ], **{"T(秒)": T},
                               量="分母(bp)", 群="全体", n=n_fin, 母数=n_all)))
        le0 = fin & (den <= 0)
        out.append(_g0(区分="g の分母", **{"gap(秒)": MAIN_GAP},
                       種=KIND_LABEL[KIND_LIQ], **{"T(秒)": T},
                       量="分母 ≤ 0 の束(g を定義しない)", 群="全体",
                       n=int(le0.sum()), 母数=n_fin,
                       割合=float(le0.sum() / n_fin) if n_fin else NAN))
        lt1 = fin & (den < G_MIN_DENOM_BP)
        out.append(_g0(区分="g の分母", **{"gap(秒)": MAIN_GAP},
                       種=KIND_LABEL[KIND_LIQ], **{"T(秒)": T},
                       量="分母 < 1 bp の束", 群="全体",
                       n=int(lt1.sum()), 母数=n_fin,
                       割合=float(lt1.sum() / n_fin) if n_fin else NAN))

    # --- 対照 (c) -------------------------------------------------------------
    ctrl = rows_by_gap[MAIN_GAP].blk[KIND_C]
    m_by_id = {T: dict(zip(blk["cascade_id"].tolist(), blk[f"m_{T}"].tolist()))
               for T in T_MAIN}
    for T in T_MAIN:
        sel = ctrl["ctrl_T"] == T
        ct = ctrl["c_t"][sel]
        mb = np.array([m_by_id[T].get(c, NAN)
                       for c in ctrl["matched_liq_id"][sel].tolist()], dtype=float)
        d = np.abs(ct - mb)
        n_b = ctrl_notes[T]["n_bundles"]
        out.append(_q(d, _g0(区分="対照 (c)", **{"gap(秒)": MAIN_GAP},
                             種=KIND_LABEL[KIND_C], **{"T(秒)": T},
                             量="|c_t − m_b|(bp)", 群="取れた束",
                             n=int(np.isfinite(d).sum()), 母数=n_b)))
        taken_ids = set(ctrl["cascade_id"][sel].tolist())
        got = np.array([c in taken_ids for c in blk["cascade_id"].tolist()],
                       dtype=bool)
        for name, msk in (("全体", np.ones(n_all, dtype=bool)),
                          ("SELL", blk["side"] == "SELL"),
                          ("BUY", blk["side"] == "BUY")):
            miss = int((msk & ~got).sum())
            tot = int(msk.sum())
            out.append(_g0(区分="対照 (c)", **{"gap(秒)": MAIN_GAP},
                           種=KIND_LABEL[KIND_C], **{"T(秒)": T},
                           量="対照 (c) が取れなかった束", 群=name,
                           n=miss, 母数=tot,
                           割合=float(miss / tot) if tot else NAN))
        for k, lo, hi, msk in m_band_masks(blk, T, cuts[T]):
            miss = int((msk & ~got).sum())
            tot = int(msk.sum())
            out.append(_g0(区分="対照 (c)", **{"gap(秒)": MAIN_GAP},
                           種=KIND_LABEL[KIND_C], **{"T(秒)": T},
                           量="m の 10 分位帯ごとに取れなかった割合",
                           群=(f"帯 {k} [{bound_text(lo) if lo == -math.inf else _fmt(lo, 4)}"
                               f", {bound_text(hi) if hi == math.inf else _fmt(hi, 4)})"),
                           n=miss, 母数=tot,
                           割合=float(miss / tot) if tot else NAN))
        for name, msk in (("取れた束", got), ("取れなかった束", ~got)):
            out.append(_g0(区分="対照 (c)", **{"gap(秒)": MAIN_GAP},
                           種=KIND_LABEL[KIND_C], **{"T(秒)": T},
                           量="取れた / 取れなかった束の中央値", 群=name,
                           n=int(msk.sum()), 母数=n_all,
                           **{"m の中央値": quantiles(blk[f"m_{T}"][msk], [50])[0],
                              "掃きの中央値": quantiles(blk["sweep_bp"][msk], [50])[0],
                              "r_end(60) の中央値":
                                  quantiles(blk["r_end_60"][msk], [50])[0]}))
    return out


# ---------------------------------------------------------------------------
# G1 逆行側
# ---------------------------------------------------------------------------
def make_g1(rows_by_gap: dict, cuts: dict) -> list:
    out = []
    plan = [(MAIN_GAP, T, h) for T in T_MAIN for h in H_MAIN]
    plan += [(gap, 60, 60) for gap in GAPS if gap != MAIN_GAP]
    for gap, T, h in plan:
        blk = rows_by_gap[gap].blk[KIND_LIQ]
        pb = blk["prev_bundle_gap_s"]
        sub_ok = np.isfinite(pb) & (pb >= T + 60)
        for k, lo, hi, msk in m_band_masks(blk, T, cuts[gap][T]):
            row = {"gap(秒)": gap, "T(秒)": T, "h(秒)": h, "m の帯": k,
                   "帯の下限(bp)": bound_text(lo), "帯の上限(bp)": bound_text(hi),
                   "帯の束数": int(msk.sum()),
                   "m 平均(bp)": (float(np.nanmean(blk[f"m_{T}"][msk]))
                                if msk.any() else NAN),
                   "掃き 平均(bp)": (float(np.nanmean(blk["sweep_bp"][msk]))
                                  if msk.any() else NAN)}
            row.update(r_stats(blk, msk, h))
            row.update(g_stats(blk, msk, T, h))
            row.update(cont_ii(blk, msk, h))
            st = r_stats(blk, msk & sub_ok, h)
            row.update({"前の束から T+60 秒以上 n": st["n"],
                        "前の束から T+60 秒以上 r_end 平均(bp)": st["r_end 平均(bp)"],
                        "前の束から T+60 秒以上 日クラスタ SE":
                            st["r_end 日クラスタ SE"]})
            out.append(row)
    return out


# ---------------------------------------------------------------------------
# G2 続伸側
# ---------------------------------------------------------------------------
SWEEP_LABELS = ((1, f"Q1(掃き ≤ {SWEEP_CUTS[0]})"),
                (2, f"Q2({SWEEP_CUTS[0]} < 掃き ≤ {SWEEP_CUTS[1]})"),
                (3, f"Q3(掃き > {SWEEP_CUTS[1]})"))


def make_g2(rows: Rows, ter: dict) -> list:
    blk = rows.blk[KIND_LIQ]
    sw = blk["sweep_bp"]
    out = []
    for q, slabel in SWEEP_LABELS:
        smask = tertile_mask(sw, SWEEP_CUTS[0], SWEEP_CUTS[1], q)
        for T in T_MAIN:
            lo, hi = ter[T]
            for mlabel, mmask in m_tertile_masks(blk, T, lo, hi):
                msk = smask & mmask
                n_le0 = int((msk & np.isfinite(sw) & (sw <= 0)).sum())
                for h in H_MAIN:
                    row = {"掃きの群": slabel, "m の群": mlabel, "T(秒)": T,
                           "h(秒)": h, "群の束数": int(msk.sum()),
                           "うち掃き ≤ 0 の束": n_le0,
                           "m 平均(bp)": (float(np.nanmean(blk[f"m_{T}"][msk]))
                                        if msk.any() else NAN),
                           "掃き 平均(bp)": (float(np.nanmean(sw[msk]))
                                          if msk.any() else NAN)}
                    row.update(r_stats(blk, msk, h))
                    row.update(cont_i(blk, msk))
                    row.update(cont_ii(blk, msk, h))
                    row.update(g_stats(blk, msk, T, h))
                    out.append(row)
    return out


# ---------------------------------------------------------------------------
# G3 時間の形
# ---------------------------------------------------------------------------
def make_g3(rows: Rows, ter: dict) -> list:
    blk = rows.blk[KIND_LIQ]
    out = []
    for T in T_MAIN:
        lo, hi = ter[T]
        for mlabel, mmask in m_tertile_masks(blk, T, lo, hi):
            for h in H_SHAPE:
                row = {"m の群": mlabel, "T(秒)": T, "h(秒)": h,
                       "群の束数": int(mmask.sum()),
                       "m 平均(bp)": (float(np.nanmean(blk[f"m_{T}"][mmask]))
                                    if mmask.any() else NAN),
                       "掃き 平均(bp)": (float(np.nanmean(blk["sweep_bp"][mmask]))
                                      if mmask.any() else NAN)}
                row.update(r_stats(blk, mmask, h))
                row.update(cont_ii(blk, mmask, h))
                out.append(row)
    return out


# ---------------------------------------------------------------------------
# G4 対照 (c)
# ---------------------------------------------------------------------------
def make_g4(rows: Rows, cuts: dict) -> list:
    ctrl = rows.blk[KIND_C]
    out = []
    for T in T_MAIN:
        tsel = ctrl["ctrl_T"] == T
        bands = band_of_m(ctrl[f"m_{T}"], cuts[T])
        for k in range(1, N_BANDS + 1):
            lo, hi = band_bounds(cuts[T], k)
            msk = tsel & (bands == k)
            for h in H_MAIN:
                row = {"種": KIND_LABEL[KIND_C], "T(秒)": T, "h(秒)": h,
                       "m の帯": k, "帯の下限(bp)": bound_text(lo),
                       "帯の上限(bp)": bound_text(hi),
                       "帯の行数": int(msk.sum()),
                       "c_t 平均(bp)": (float(np.nanmean(ctrl["c_t"][msk]))
                                      if msk.any() else NAN)}
                row.update(r_stats(ctrl, msk, h))
                row.update(g_stats(ctrl, msk, T, h))
                row.update(cont_ii(ctrl, msk, h))
                out.append(row)
    return out


# ---------------------------------------------------------------------------
# G5 日の状態
# ---------------------------------------------------------------------------
def make_g5(rows: Rows, ter: dict) -> list:
    blk = rows.blk[KIND_LIQ]
    bpd = blk["bundles_per_day"]
    lo_d, hi_d = tertile_cuts(bpd)
    T = 60
    lo, hi = ter[T]
    bounds = {1: (NAN, lo_d), 2: (lo_d, hi_d), 3: (hi_d, NAN)}
    out = []
    for q, dlabel in ex2.TERTILE_LABELS:
        dmask = tertile_mask(bpd, lo_d, hi_d, q)
        for mlabel, mmask in m_tertile_masks(blk, T, lo, hi):
            msk = dmask & mmask
            for h in H_MAIN:
                row = {"日の束数の群": dlabel, "日の束数 下限": bounds[q][0],
                       "日の束数 上限": bounds[q][1],
                       "m の群": mlabel, "T(秒)": T, "h(秒)": h,
                       "群の束数": int(msk.sum()),
                       "日の束数 平均": (float(np.nanmean(bpd[msk]))
                                   if msk.any() else NAN)}
                row.update(r_stats(blk, msk, h))
                row.update(cont_i(blk, msk))
                row.update(cont_ii(blk, msk, h))
                row.update(g_stats(blk, msk, T, h))
                out.append(row)
    return out


# ---------------------------------------------------------------------------
# G6 属性(6 属性 17 群、設計 §0 の機械的な規則)
# ---------------------------------------------------------------------------
G6_ATTRS = ("bundle_n_events_dedup", "bundle_total_notional", "|dist_node_bp|",
            "bin_pct", "implied_leverage")


def g6_groups(table: "ex2.RunTable") -> list:
    """設計 §0 の規則で残る 6 属性 17 群(連続 5 属性の 3 分位 + 側 2)。

    切り値は探索段 2 の E4(= 探索段 3 の F5)と同じ `ex2.attribute_groups`。
    """
    keep = set(G6_ATTRS) | {ex2.ATTR_SIDE}
    groups = [g for g in ex2.attribute_groups(table) if g["属性"] in keep]
    order = {name: i for i, name in enumerate(list(G6_ATTRS) + [ex2.ATTR_SIDE])}
    groups.sort(key=lambda g: (order[g["属性"]], str(g["群"])))
    return groups


def make_g6(rows: Rows, table: "ex2.RunTable", ter: dict) -> list:
    groups = g6_groups(table)
    blk = rows.blk[KIND_LIQ]
    cid = blk["cascade_id"]
    liq_i = np.flatnonzero(table.kind == ex2.KIND_LIQ)
    miss_frac: dict = {}
    for name, col, take_abs in ex2.ATTRS_NUM:
        v = table.num(col)[liq_i]
        if take_abs:
            v = np.abs(v)
        miss_frac[name] = float((~np.isfinite(v)).mean())
    miss_frac[ex2.ATTR_SIDE] = float((table.side[liq_i] == "").mean())
    T = 60
    lo, hi = ter[T]
    out = []
    for g in groups:
        ids = g["ids"]
        gmask = np.array([c in ids for c in cid.tolist()], dtype=bool)
        for mlabel, mmask in m_tertile_masks(blk, T, lo, hi):
            msk = gmask & mmask
            for h in H_MAIN:
                row = {"属性": g["属性"], "群": g["群"], "下限": g["下限"],
                       "上限": g["上限"], "m の群": mlabel, "T(秒)": T, "h(秒)": h,
                       "群の束数": int(msk.sum()),
                       "属性が欠測で群に入らない束の割合":
                           miss_frac.get(g["属性"], NAN)}
                row.update(r_stats(blk, msk, h))
                row.update(cont_i(blk, msk))
                row.update(cont_ii(blk, msk, h))
                out.append(row)
    return out


# ---------------------------------------------------------------------------
# G7 bitFlyer(同じ 1 分格子)
# ---------------------------------------------------------------------------
def make_g7(rows: Rows, ter: dict) -> list:
    blk = rows.blk[KIND_LIQ]
    out = []
    for T in T_MAIN:
        lo, hi = ter[T]
        for mlabel, mmask in m_tertile_masks(blk, T, lo, hi):
            for venue, col in (("Binance COIN-M", "bn_grid"),
                               ("bitFlyer FX_BTC_JPY", "bf_grid")):
                for h in H_GRID:
                    v = blk[f"{col}_{h}"][mmask]
                    days = blk["day"][mmask]
                    mean, se, naive, n, gdays = mean_se_cluster(v, days)
                    ratio = (se / naive if (math.isfinite(se) and math.isfinite(naive)
                                            and naive > 0) else NAN)
                    out.append({
                        "会場": venue, "T(秒)": T, "m の群": mlabel, "h(秒)": h,
                        "群の束数": int(mmask.sum()), "n": n, "含む日数": gdays,
                        "平均(bp)": mean, "日クラスタ SE": se, "naive SE": naive,
                        "日クラスタ/naive": ratio,
                        "日等重み平均": day_equal_weight_mean(v, days),
                        "引けない束": int(mmask.sum()) - n,
                    })
    return out


# ===========================================================================
# main
# ===========================================================================
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="O3C SIGNAL 探索段 4")
    ap.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    ap.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    ap.add_argument("--bitflyer-dir", type=Path, default=DEFAULT_BITFLYER_DIR)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stage", choices=("rows", "tables", "all"), default="all")
    ap.add_argument("--limit-days", type=int, default=0)
    ap.add_argument("--progress-every", type=int, default=20)
    ap.add_argument("--keep-chunks", action="store_true",
                    help="chunk の中間ファイルを消さない(再開・試験用)")
    a = ap.parse_args(argv)

    t0 = time.time()
    a.out.mkdir(parents=True, exist_ok=True)
    tables = {run: ex2.RunTable(a.runs_dir / run) for run in RUNS}
    bundles = {GAP_OF_RUN[run]: Bundles(tables[run]) for run in RUNS}
    mixed = {GAP_OF_RUN[run]: load_mixed(a.runs_dir / run) for run in RUNS}
    days = tables["gap60_w8"].days()
    if a.limit_days:
        days = days[: a.limit_days]
    print(f"走行 {list(tables)} / 日 {len(days)}", flush=True)

    bd60 = bundles[MAIN_GAP]
    bundles_per_day = {d: int(ks.size) for d, ks in bd60.by_day.items()}

    years = sorted({int(d[:4]) for d in days} | {int(d[:4]) + 1 for d in days})
    bf = ex2.load_bitflyer_minutes(years, a.bitflyer_dir)
    print(f"bitFlyer 1 分足 {bf['t_ms'].size} 点 / 無い年 {bf['years_missing']}",
          flush=True)

    if a.stage in ("rows", "all"):
        note1 = run_stage1(a.out, days, bundles, tables, a.data_root, bf,
                           bundles_per_day, a.progress_every)
        m_by_gap = read_m(a.out, days, bundles)
        note2 = run_stage2(a.out, days, bundles, m_by_gap, a.data_root,
                           a.progress_every)
        concat_rows(a.out, days)
        (a.out / "stage_notes.json").write_text(json.dumps(
            {"stage1": note1, "m の帯の切り値(gap60)": note2["cuts"],
             "対照 (c) の採否": note2["notes"]}, ensure_ascii=False, indent=2))
    if a.stage == "rows":
        return 0

    rows_by_gap = {gap: Rows(a.out / f"rows_gap{gap}.csv.gz") for gap in GAPS}
    liq60 = rows_by_gap[MAIN_GAP].blk[KIND_LIQ]

    cuts = {gap: {T: band_cuts_m(rows_by_gap[gap].blk[KIND_LIQ][f"m_{T}"])
                  for T in T_MAIN} for gap in GAPS}
    ter = {T: tertile_cuts(liq60[f"m_{T}"]) for T in T_MAIN}
    ctrl = rows_by_gap[MAIN_GAP].blk[KIND_C]
    ctrl_notes = {T: {"n_bundles": liq60["_n"],
                      "n_taken": int((ctrl["ctrl_T"] == T).sum())} for T in T_MAIN}

    g0 = make_g0(rows_by_gap, cuts[MAIN_GAP], ctrl_notes)
    g1 = make_g1(rows_by_gap, cuts)
    g2 = make_g2(rows_by_gap[MAIN_GAP], ter)
    g3 = make_g3(rows_by_gap[MAIN_GAP], ter)
    g4 = make_g4(rows_by_gap[MAIN_GAP], cuts[MAIN_GAP])
    g5 = make_g5(rows_by_gap[MAIN_GAP], ter)
    g6 = make_g6(rows_by_gap[MAIN_GAP], tables["gap60_w8"], ter)
    g7 = make_g7(rows_by_gap[MAIN_GAP], ter)
    named = [("g0_selfcheck.csv", g0, "G0", "G0 自己点検と T の下見(gap 60)"),
             ("g1_reversal.csv", g1, "G1", "G1 逆行側(m の 10 分位)"),
             ("g2_continuation.csv", g2, "G2", "G2 続伸側(掃き 3 分位 × m 3 分位)"),
             ("g3_timeshape.csv", g3, "G3", "G3 時間の形(h = 1〜60 秒)"),
             ("g4_control.csv", g4, "G4", "G4 対照 (c) 前の値動き合わせ"),
             ("g5_daystate.csv", g5, "G5", "G5 日の状態(日の束数 3 分位)"),
             ("g6_attributes.csv", g6, "G6", "G6 属性(6 属性 17 群)"),
             ("g7_bitflyer.csv", g7, "G7",
              "G7 同じ 1 分格子(Binance と bitFlyer)")]
    for name, rows, _key, _title in named:
        write_csv(a.out / name, rows)

    # --- summary.json -------------------------------------------------------
    inputs = {}
    for run in RUNS:
        p = a.runs_dir / run / "table.csv"
        inputs[str(p.relative_to(REPO_ROOT))] = md5_of(p)
    for y in sorted(set(years)):
        p = Path(a.bitflyer_dir) / f"candles_1m_{y}.csv.gz"
        if p.exists():
            inputs[str(p.relative_to(REPO_ROOT))] = md5_of(p)
    agg_dir = Path(a.data_root) / "aggTrades" / base.SYMBOL
    agg_files = sorted(agg_dir.glob(f"{base.SYMBOL}-aggTrades-*.zip"))
    agg_note = {"場所": str(agg_dir.relative_to(REPO_ROOT)),
                "zip の数": len(agg_files),
                "合計バイト": sum(p.stat().st_size for p in agg_files)}

    missing_cal = calendar_gaps(days)
    per_gap = {}
    for gap in GAPS:
        b = rows_by_gap[gap].blk
        liq = b[KIND_LIQ]
        sw = liq["sweep_bp"]
        per_gap[f"gap{gap}"] = {
            "この段の行数": {KIND_LABEL[k]: b[k]["_n"] for k in KINDS},
            "1 周目の表の行数": {"liq": tables[f"gap{gap}_w8"].n_liq,
                         "control_uniform": tables[f"gap{gap}_w8"].n_uniform},
            "両側混在で主表から外れた束(table_mixed.csv)": mixed[gap],
            "基準が引けない束": int((~np.isfinite(liq["p_pre"])).sum()),
            "終端が引けない束": int((~np.isfinite(liq["p_end"])).sum()),
            "掃きが NaN の束": int((~np.isfinite(sw)).sum()),
            "掃きなし(p_end = p_pre)の束": int(
                (np.isfinite(liq["p_pre"]) & np.isfinite(liq["p_end"])
                 & (liq["p_pre"] == liq["p_end"])).sum()),
            "掃きが逆(sweep < 0)の束": int((np.isfinite(sw) & (sw < 0)).sum()),
            "m が NaN の束": {str(T): int((~np.isfinite(liq[f"m_{T}"])).sum())
                          for T in T_ALL},
            "r_end が NaN の束": {str(h): int((~np.isfinite(liq[f"r_end_{h}"])).sum())
                             for h in HORIZONS_SEC},
            "g の分母 ≤ 0 の束": {str(T): int((np.isfinite(liq[f"den_bp_{T}"])
                                          & (liq[f"den_bp_{T}"] <= 0)).sum())
                             for T in T_MAIN},
            "g が NaN の束": {f"T={T} h={h}":
                           int((~np.isfinite(liq[f"g_{T}_{h}"])).sum())
                           for T in T_MAIN for h in H_MAIN},
            "bn_grid が NaN の束": {str(h): int((~np.isfinite(liq[f"bn_grid_{h}"])).sum())
                               for h in H_GRID},
            "bf_grid が NaN の束": {str(h): int((~np.isfinite(liq[f"bf_grid_{h}"])).sum())
                               for h in H_GRID},
            "次の束の間隔が NaN(その日の最後の束)": int(
                (~np.isfinite(liq["next_bundle_gap_s"])).sum()),
            "前の束の間隔が NaN(その日の最初の束)": int(
                (~np.isfinite(liq["prev_bundle_gap_s"])).sum()),
        }

    stage_notes = {}
    p_notes = a.out / "stage_notes.json"
    if p_notes.exists():
        stage_notes = json.loads(p_notes.read_text())

    mean60, se60, naive60, n60, g60 = mean_se_cluster(liq60["r_end_60"],
                                                      liq60["day"])
    summary = {
        "実行時刻(UTC)": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "経過秒": round(time.time() - t0, 1),
        "設計": "docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE4_DESIGN_2026-09-20.md",
        "パラメータ": {
            "T(秒) 主": list(T_MAIN), "T(秒) 下見": list(T_ALL),
            "h(秒)": list(HORIZONS_SEC), "h(秒) 主": list(H_MAIN),
            "h(秒) 時間の形": list(H_SHAPE), "h(秒) 1 分格子": list(H_GRID),
            "走行": list(RUNS), "穴の上限(ms)": STALENESS_MS,
            "対照 (c) の候補の刻み(ms)": GRID_STEP_MS,
            "対照 (c) の候補点/日": GRID_N,
            "対照 (c) の区間": "[t − T*1000, t + 900_000]",
            "m の帯の数": N_BANDS,
            "m の帯の規則": ("帯 1 = (−∞, q_1)、帯 k ≥ 2 = [q_{k−1}, q_k)、"
                       "帯 10 = [q_9, +∞)。同じ gap の全束の m で切る(負を含む)"),
            "掃きの 3 分位の切り値(bp)": list(SWEEP_CUTS),
            "続伸 (i) の境界(秒)": CONT_SEC,
            "g の分母の下限(bp)": G_MIN_DENOM_BP,
            "符号": "SELL: −1 / BUY: +1(探索段 1〜3 と同じ向き。負 = 清算と逆)",
            "基準": "at_or_before(start_ms − 1, 300_000)",
            "終端": "at_or_after(end_ms, 300_000)",
            "T 秒前": "at_or_before(start_ms − T*1000, 300_000)",
            "h 後": "at_or_before(終端の約定の時刻 + h*1000, 300_000)",
            "m(T)": "s × (p_pre − p_T)/p_T × 1e4",
            "g(T,h)": ("(p_end − p_h)/(p_end − p_T)。分母 = "
                       "s × (p_end − p_T)/p_T × 1e4 が正のときだけ定義する"),
            "対照 (b)": ("一様行の生(符号なし)の r_end を日ごとに平均し、"
                     "束の符号を掛けて束ごとの値にする(日集約版)"),
            "対照 (c)": "設計 §4(gap 60 だけ、T ごとに別に取る)",
            "1 分格子": ("基準 = at_or_before(floor_1m(start_ms) − 1)、"
                     "h 後 = at_or_before(floor_1m(start_ms) − 1 + h*1000)。"
                     "両会場とも同じ格子点"),
            "前後の束の間隔": "同じ日・同じ gap(設計の用語表)。日の最初/最後は NaN",
            "日の束数": "その日の gap 60 の束の数",
        },
        "入力の MD5": inputs,
        "約定アーカイブ": agg_note,
        "日数": len(days),
        "暦の日数(最初〜最後)": (
            (_dt.date.fromisoformat(days[-1])
             - _dt.date.fromisoformat(days[0])).days + 1),
        "欠けた日": missing_cal, "欠けた日の数": len(missing_cal),
        "走行ごと": per_gap,
        "m の帯の切り値(gap60)": {str(T): [float(x) for x in cuts[MAIN_GAP][T]]
                          for T in T_MAIN},
        "m の 3 分位の切り値(gap60)": {str(T): [ter[T][0], ter[T][1]] for T in T_MAIN},
        "日の束数の 3 分位の切り値": list(tertile_cuts(liq60["bundles_per_day"])),
        "対照 (c) の採否": {
            str(T): {"対象の束": ctrl_notes[T]["n_bundles"],
                     "取れた束": ctrl_notes[T]["n_taken"],
                     "取れなかった束": (ctrl_notes[T]["n_bundles"]
                                - ctrl_notes[T]["n_taken"])} for T in T_MAIN},
        "約定が読めなかった日": stage_notes.get("stage1", {}).get(
            "agg_days_missing", "(この走行では rows 段を回していない)"),
        "bitFlyer の無い年": bf["years_missing"],
        "探索段 3 との突き合わせ": {
            "量": "gap 60 の清算側 r_end(60) の全体平均",
            "この段": mean60, "n": n60, "含む日数": g60,
            "日クラスタ SE": se60, "naive SE": naive60,
            "探索段 3 の出典": ("backtest_data/o3c_signal_explore3_20260920/"
                         "f2_retrace.csv の gap 60・h 60・清算 全体"),
        },
        "表の行数": {key: len(rows) for _n, rows, key, _t in named},
    }
    summary["表の行数"]["合計"] = sum(len(rows) for _n, rows, _k, _t in named)
    summary["表の行数"]["G0 を除く合計"] = summary["表の行数"]["合計"] - len(g0)
    txt = json.dumps(summary, ensure_ascii=False, indent=2)
    check_no_banned(txt, "summary.json")
    (a.out / "summary.json").write_text(txt)

    # --- tables.md ----------------------------------------------------------
    md = [f"# O3C SIGNAL 探索段 4 の表({days[0]} 〜 {days[-1]}、{len(days)} 日)", "",
          f"- 設計: `{summary['設計']}`",
          f"- T(秒)= 主 {list(T_MAIN)} / 下見 {list(T_ALL)}",
          f"- h(秒)= {list(HORIZONS_SEC)} / gap = 60 主、30 / 180 は G1 の一部",
          f"- 欠けた日({len(missing_cal)} 日): " + ", ".join(missing_cal),
          "- 基準 = `at_or_before(start_ms − 1, 300_000)` / 終端 = "
          "`at_or_after(end_ms, 300_000)` / T 秒前 = "
          "`at_or_before(start_ms − T*1000, 300_000)` / h 後 = "
          "`at_or_before(終端の約定の時刻 + h*1000, 300_000)`",
          "- m(T) = s × (p_pre − p_T)/p_T × 1e4、掃き = s × (p_end − p_pre)/p_pre × 1e4、"
          "r_end(h) = s × (p_h − p_end)/p_end × 1e4",
          "- g(T,h) = (p_end − p_h)/(p_end − p_T)。分母 = s × (p_end − p_T)/p_T × 1e4 が"
          "正のときだけ定義する(分母 ≥ 1 bp の列も併記)",
          "- 割合の列にはすべて母数の列を添えてある", ""]
    for name, rows, _key, title in named:
        md += [f"## {title}(`{name}`、{len(rows)} 行)", "", md_table(rows), ""]
    mdtxt = "\n".join(md)
    check_no_banned(mdtxt, "tables.md")
    (a.out / "tables.md").write_text(mdtxt)

    if not a.keep_chunks:
        n_drop = drop_chunks(a.out)
        print(f"chunk の中間ファイルを {n_drop} 個消した", flush=True)

    names = ([f"rows_gap{g}.csv.gz" for g in GAPS]
             + [n for n, _r, _k, _t in named] + ["tables.md", "summary.json"])
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

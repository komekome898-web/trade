#!/usr/bin/env python3
"""清算を起点とした値動きの予測可能性(SIGNAL)— **探索段 3** の道具。

設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE3_DESIGN_2026-09-20.md`
(用語表 / §2 問い F1〜F5 / §4 対照と F0 / §6 データと出力 / §7 走らせる前に決めること)。

**この道具がすること**
  - 束と対照 (b) は 1 周目の走行の表(`backtest_data/o3c_reaction_20260918_full/<run>/table.csv`)
    の行を**そのまま使う**(束を作り直さない)。gap 60 が主、30 / 180 は併記。
  - 束ごとに**清算の前の価格**(基準)を約定から取り直す:
    基準 p_pre = `at_or_before(start_ms − 1, 300_000)`、
    終端 p_end = `at_or_after(end_ms, 300_000)`(探索段 2 の Δ = 0 の起点と同じ)、
    h 後 = `at_or_before(終端の時刻 + h*1000, 300_000)`、h ∈ {60, 300, 900} 秒。
  - 符号 s = SELL: −1 / BUY: +1(探索段 1・2 と同じ向き。負 = 清算と逆)。
    sweep = s × (p_end − p_pre)/p_pre × 1e4、
    r_pre(h) = s × (p_h − p_pre)/p_pre × 1e4、
    r_end(h) = s × (p_h − p_end)/p_end × 1e4(探索段 2 の r(0,h) と同じ量)、
    戻り率 f(h) = (p_end − p_h)/(p_end − p_pre)(sweep > 0 の束だけ)。
  - 対照 (a) 掃き合わせ(設計 §4 手順 1〜5)、対照 (b) = 1 周目の対照 (i) 日集約版 と (ii)。
  - 出力は F0〜F5 の表・`rows_gap*.csv.gz`・`tables.md`・`summary.json`・`MD5SUMS`。

**探索段なので判定語を 1 つも書かない。**検定もしない。読み(なぜ)も書かない。

**`paper_logs/` は開かない**(自前記録は判定まで触らない)。この道具は
`backtest_data/` と `docs/` 以外のどのディレクトリも読まない。

読み込み・日クラスタ SE・3 分位の切り方・属性の 30 群・gzip の決定的な書き出しは
探索段 2 の道具 `scripts/o3c_signal_explore2.py` の関数をそのまま呼ぶ。
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import gzip
import importlib.util
import io
import json
import math
import sys
import time
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import o3c_price_level_table as base  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "o3c_signal_explore2", _HERE / "o3c_signal_explore2.py")
ex2 = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(ex2)

REPO_ROOT = _HERE.parent
NAN = float("nan")

# ---------------------------------------------------------------------------
# 固定値(設計 §7。変えるときは報告に列挙する)
# ---------------------------------------------------------------------------
HORIZONS_SEC = (60, 300, 900)
STALENESS_MS = ex2.STALENESS_MS            # 300_000
RUNS = ex2.RUNS
GAP_OF_RUN = ex2.GAP_OF_RUN
GAPS = (60, 30, 180)
MAIN_GAP = 60
REACT_SIGN = ex2.REACT_SIGN

GRID_STEP_MS = 10_000                      # 対照 (a) の候補時刻の刻み
GRID_N = 8_640                             # 1 日の候補点
CTRL_WINDOW_MS = 900_000                   # 候補の区間の後ろ側(= 最大 h)
N_BANDS = 10                               # 掃きの 10 分位帯
SUBSET_SEC = 180                           # F2 の部分集合(前後の束の間隔)
PREV_NEAR_SEC = 300                        # F1 の「前の束から 300 秒未満」

KIND_LIQ = "liq"
KIND_A = "control_a"
KIND_BI = "control_b_i"
KIND_BII = "control_b_ii"
KINDS = (KIND_LIQ, KIND_A, KIND_BI, KIND_BII)
KIND_LABEL = {KIND_LIQ: "清算", KIND_A: "対照(a) 掃き合わせ",
              KIND_BI: "対照(b)-i 一様(日集約)", KIND_BII: "対照(b)-ii 薄さ合わせ"}

DEFAULT_RUNS_DIR = ex2.DEFAULT_RUNS_DIR
DEFAULT_DATA_ROOT = ex2.DEFAULT_DATA_ROOT
DEFAULT_BITFLYER_DIR = ex2.DEFAULT_BITFLYER_DIR
DEFAULT_OUT = REPO_ROOT / "backtest_data" / "o3c_signal_explore3_20260920"

BANNED_WORDS = ex2.BANNED_WORDS

ROW_COLUMNS = (
    ["kind", "cascade_id", "day", "side", "t_pre_ms", "t_end_ms", "p_pre", "p_end",
     "baseline_lag_ms", "end_lag_ms", "sweep_bp", "prev_bundle_gap_s",
     "next_bundle_gap_s", "baseline_in_prev_bundle"]
    + [f"r_pre_{h}" for h in HORIZONS_SEC]
    + [f"r_end_{h}" for h in HORIZONS_SEC]
    + [f"f_{h}" for h in HORIZONS_SEC]
    + [f"h_lag_ms_{h}" for h in HORIZONS_SEC]
    + [f"bf_r_pre_{h}" for h in HORIZONS_SEC]
    + [f"h_same_as_end_{h}" for h in HORIZONS_SEC]
    + ["matched_liq_id", "c_t", "ctrl_t_ms"])
CHUNK_HEADER = ["gap"] + ROW_COLUMNS


# ===========================================================================
# 小道具(探索段 2 から借りるもの)
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


def check_no_banned(text: str, where: str) -> None:
    hit = [w for w in BANNED_WORDS if w in text]
    if hit:
        raise SystemExit(f"[止め] 判定語が出力に混ざっている({where}): {hit}")


def day_equal_weight_mean(vals: np.ndarray, days: np.ndarray) -> float:
    """日ごとの平均を取ってから日で等重みに平均する(設計 §7)。"""
    ok = np.isfinite(vals)
    v, d = vals[ok], days[ok]
    if v.size == 0:
        return NAN
    acc: dict = defaultdict(list)
    for x, dd in zip(v.tolist(), d.tolist()):
        acc[dd].append(x)
    means = [sum(xs) / len(xs) for xs in acc.values()]
    return float(sum(means) / len(means))


def quantiles(v: np.ndarray, qs) -> list:
    fin = np.asarray(v, dtype=float)
    fin = fin[np.isfinite(fin)]
    if fin.size == 0:
        return [NAN] * len(qs)
    return [float(x) for x in np.percentile(fin, qs)]


def idx_at_or_before(times: np.ndarray, tgt: np.ndarray, tol: int):
    """`tgt` 以前で最も新しい点の添字と可否(`PriceSeries.at_or_before` と同じ規則)。"""
    tgt = np.asarray(tgt)
    n = int(tgt.size)
    if times.size == 0:
        return np.zeros(n, dtype=np.int64), np.zeros(n, dtype=bool)
    i = np.searchsorted(times, tgt, side="right") - 1
    ok = i >= 0
    ic = np.clip(i, 0, times.size - 1)
    ok = ok & ((tgt - times[ic]) <= tol)
    return ic, ok


def idx_at_or_after(times: np.ndarray, tgt: np.ndarray, tol: int):
    """`tgt` 以後で最も古い点の添字と可否(`PriceSeries.at_or_after` と同じ規則)。"""
    tgt = np.asarray(tgt)
    n = int(tgt.size)
    if times.size == 0:
        return np.zeros(n, dtype=np.int64), np.zeros(n, dtype=bool)
    i = np.searchsorted(times, tgt, side="left")
    ok = i < times.size
    ic = np.clip(i, 0, times.size - 1)
    ok = ok & ((times[ic] - tgt) <= tol)
    return ic, ok


# ===========================================================================
# 束・対照の 1 行ぶんの量
# ===========================================================================
def measure(times: np.ndarray, prices: np.ndarray,
            t_pre_req, t_end_req: np.ndarray, sign: np.ndarray) -> dict:
    """基準・終端・h 後を引いて、この段の量を全部返す。行は落とさない(NaN で残す)。

    `t_pre_req` が None なら基準の無い行(対照 (b))。
    どの点も**時刻だけ**で選ぶ(価格は選んだあとに読む = 先読みをしていない)。
    """
    t_end_req = np.asarray(t_end_req, dtype=np.int64)
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
        sweep = np.where(ok_pre & ok_end & (p_pre > 0),
                         sign * (p_end - p_pre) / p_pre * 1e4, NAN)
    out["sweep_bp"] = sweep

    for h in HORIZONS_SEC:
        tgt = np.where(ok_end, t_end + h * 1000, 0)
        i_h, ok_h = idx_at_or_before(times, tgt, STALENESS_MS)
        ok_h = ok_h & ok_end
        p_h = np.where(ok_h, prices[i_h] if times.size else NAN, NAN)
        t_h = times[i_h] if times.size else np.zeros(n, dtype=np.int64)
        out[f"h_lag_ms_{h}"] = np.where(ok_h, (tgt - t_h).astype(float), NAN)
        out[f"h_same_as_end_{h}"] = np.where(ok_h, i_h == i_end, False)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[f"r_end_{h}"] = np.where(ok_h & (p_end > 0),
                                         sign * (p_h - p_end) / p_end * 1e4, NAN)
            out[f"r_pre_{h}"] = np.where(ok_h & ok_pre & (p_pre > 0),
                                         sign * (p_h - p_pre) / p_pre * 1e4, NAN)
            f_ok = ok_h & ok_pre & np.isfinite(sweep) & (sweep > 0)
            out[f"f_{h}"] = np.where(f_ok, (p_end - p_h) / (p_end - p_pre), NAN)
    return out


def bf_r_pre(bf: dict, start_like_ms: np.ndarray, ok_pre: np.ndarray,
             t_end_ms: np.ndarray, ok_end: np.ndarray, sign: np.ndarray) -> dict:
    """bitFlyer 1 分足での r_pre(設計 §6)。

    基準 = `start_ms` を**含む足の 1 本前**の終値 = `at_or_before(floor_1m(start_ms) − 1)`。
    h 後 = `at_or_before(終端の約定の時刻 + h*1000)`。どちらも 5 分の遡り上限・前値で埋めない。
    **窓ずれ**: 足の刻みは 1 分なので、基準は起点より最大 1 分前の終値である。
    """
    start_like_ms = np.asarray(start_like_ms, dtype=np.int64)
    base_ts = (start_like_ms // 60_000) * 60_000 - 1
    p0 = ex2.bf_close_at_or_before(bf, np.where(ok_pre, base_ts, 0))
    out = {}
    for h in HORIZONS_SEC:
        p1 = ex2.bf_close_at_or_before(bf, np.where(ok_end, t_end_ms + h * 1000, 0))
        good = ok_pre & ok_end & np.isfinite(p0) & (p0 > 0) & np.isfinite(p1)
        with np.errstate(invalid="ignore", divide="ignore"):
            v = sign * (p1 - p0) / p0 * 1e4
        out[f"bf_r_pre_{h}"] = np.where(good, v, NAN)
    return out


# ===========================================================================
# 1 周目の表からの束(gap ごと)
# ===========================================================================
class Bundles:
    """1 走行の清算側の束(`start_ms` 昇順)と、前後の束の間隔。"""

    def __init__(self, table: "ex2.RunTable"):
        self.table = table
        liq = np.flatnonzero(table.kind == KIND_LIQ)
        order = sorted(liq.tolist(),
                       key=lambda i: (int(table.start_ms[i]), str(table.cascade_id[i])))
        idx = np.array(order, dtype=int)
        self.idx = idx
        self.cascade_id = table.cascade_id[idx]
        self.day = table.day[idx]
        self.side = table.side[idx]
        self.sign = table.sign[idx]
        self.start_ms = table.start_ms[idx].astype(np.int64)
        self.end_ms = table.base_ts[idx].astype(np.int64)
        self.width_ms = self.end_ms - self.start_ms
        self.n = int(idx.size)
        prev_gap = np.full(self.n, NAN)
        next_gap = np.full(self.n, NAN)
        prev_end = np.full(self.n, -1, dtype=np.int64)
        by_day: dict[str, list[int]] = defaultdict(list)
        for k, d in enumerate(self.day.tolist()):
            by_day[d].append(k)
        for d, ks in by_day.items():
            for j, k in enumerate(ks):
                if j > 0:
                    p = ks[j - 1]
                    prev_gap[k] = (self.start_ms[k] - self.end_ms[p]) / 1000.0
                    prev_end[k] = self.end_ms[p]
                if j + 1 < len(ks):
                    q = ks[j + 1]
                    next_gap[k] = (self.start_ms[q] - self.end_ms[k]) / 1000.0
        self.prev_bundle_gap_s = prev_gap
        self.next_bundle_gap_s = next_gap
        self.prev_end_ms = prev_end
        self.pos_of_id = {c: k for k, c in enumerate(self.cascade_id.tolist())}
        self.by_day = {d: np.array(ks, dtype=int) for d, ks in by_day.items()}
        self.max_width_ms = int(self.width_ms.max()) if self.n else 0
        vals = table.num("bundle_n_events_dedup")
        self.n_events = vals[idx]


def load_mixed(run_dir: Path) -> int:
    """両側混在で主表から外れた束の数(`table_mixed.csv` の行数)。"""
    p = Path(run_dir) / "table_mixed.csv"
    if not p.exists():
        return 0
    with open(p, newline="") as fh:
        return sum(1 for _ in csv.DictReader(fh))


# ===========================================================================
# 約定の読み込み(その日 ± 必要分)
# ===========================================================================
def day_start_ms(day: str) -> int:
    d0 = _dt.date.fromisoformat(day)
    return int(_dt.datetime.combine(d0, _dt.time(), _dt.timezone.utc).timestamp() * 1000)


def load_window(data_root: Path, day: str, agg_cache: dict,
                back_ms: int, fwd_ms: int):
    lo = day_start_ms(day) - back_ms
    hi = day_start_ms(day) + 86_400_000 + fwd_ms
    d_lo = _dt.datetime.fromtimestamp(lo / 1000, _dt.timezone.utc).date().isoformat()
    d_hi = _dt.datetime.fromtimestamp(hi / 1000, _dt.timezone.utc).date().isoformat()
    need = [d_lo]
    while need[-1] < d_hi:
        need.append((_dt.date.fromisoformat(need[-1]) + _dt.timedelta(days=1)).isoformat())
    parts, missing = [], []
    for d in need:
        if d not in agg_cache:
            p = base.agg_path(data_root, d)
            agg_cache[d] = base.load_agg_trades(p) if p.exists() else None
        if agg_cache[d] is None:
            missing.append(d)
        else:
            parts.append(agg_cache[d])
    for k in [k for k in agg_cache if k < d_lo]:
        del agg_cache[k]
    if parts:
        times = np.concatenate([x[0] for x in parts])
        prices = np.concatenate([x[1] for x in parts])
        if not bool(np.all(times[1:] >= times[:-1])):
            o = np.argsort(times, kind="stable")
            times, prices = times[o], prices[o]
        m = (times >= lo) & (times <= hi)
        times, prices = times[m], prices[m]
    else:
        times = np.zeros(0, dtype=np.int64)
        prices = np.zeros(0)
    return times, prices, missing


# ===========================================================================
# 行の書き出し
# ===========================================================================
def _row(gap, kind, cid, day, side, m, k, bfv, prev_gap, next_gap, in_prev,
         matched="", c_t=NAN, ctrl_t=None):
    ok_pre = bool(m["ok_pre"][k])
    ok_end = bool(m["ok_end"][k])
    row = [gap, kind, cid, day, side,
           int(m["t_pre_ms"][k]) if ok_pre else "",
           int(m["t_end_ms"][k]) if ok_end else "",
           _fmt(m["p_pre"][k], 4) if ok_pre else "",
           _fmt(m["p_end"][k], 4) if ok_end else "",
           int(m["pre_lag_ms"][k]) + 1 if ok_pre else "",
           int(m["end_lag_ms"][k]) if ok_end else "",
           _fmt(m["sweep_bp"][k], 6),
           "" if prev_gap is None or not math.isfinite(prev_gap) else _fmt(prev_gap, 3),
           "" if next_gap is None or not math.isfinite(next_gap) else _fmt(next_gap, 3),
           "" if in_prev is None else ("1" if in_prev else "0")]
    row += [_fmt(m[f"r_pre_{h}"][k], 6) for h in HORIZONS_SEC]
    row += [_fmt(m[f"r_end_{h}"][k], 6) for h in HORIZONS_SEC]
    row += [_fmt(m[f"f_{h}"][k], 6) for h in HORIZONS_SEC]
    row += [("" if not math.isfinite(m[f"h_lag_ms_{h}"][k])
             else int(m[f"h_lag_ms_{h}"][k])) for h in HORIZONS_SEC]
    row += [(_fmt(bfv[f"bf_r_pre_{h}"][k], 6) if bfv is not None else "")
            for h in HORIZONS_SEC]
    row += [("1" if bool(m[f"h_same_as_end_{h}"][k]) else "0") for h in HORIZONS_SEC]
    row += [matched, _fmt(c_t, 6), "" if ctrl_t is None else int(ctrl_t)]
    return row


# ===========================================================================
# 段 1: 清算 + 対照 (b) の行
# ===========================================================================
def stage1_day(day: str, bundles: dict, tables: dict, times: np.ndarray,
               prices: np.ndarray, bf: dict) -> list:
    out: list = []
    for run in RUNS:
        gap = GAP_OF_RUN[run]
        bd = bundles[gap]
        t = tables[run]
        ks = bd.by_day.get(day, np.zeros(0, dtype=int))
        if ks.size:
            start = bd.start_ms[ks]
            end = bd.end_ms[ks]
            sign = bd.sign[ks]
            m = measure(times, prices, start - 1, end, sign)
            bfv = bf_r_pre(bf, start, m["ok_pre"], m["t_end_ms"], m["ok_end"], sign)
            prev_end = bd.prev_end_ms[ks]
            for j, k in enumerate(ks.tolist()):
                in_prev = bool(m["ok_pre"][j] and prev_end[j] >= 0
                               and m["t_pre_ms"][j] <= prev_end[j])
                out.append(_row(gap, KIND_LIQ, bd.cascade_id[k], day, bd.side[k], m, j,
                                bfv, float(bd.prev_bundle_gap_s[k]),
                                float(bd.next_bundle_gap_s[k]), in_prev))
        for kind_src, kind_out in ((ex2.KIND_UNIFORM, KIND_BI),
                                   (ex2.KIND_MATCHED, KIND_BII)):
            sel = np.flatnonzero((t.kind == kind_src) & (t.day == day))
            if not sel.size:
                continue
            tms = t.time_ms[sel].astype(np.int64)
            if kind_out == KIND_BI:
                # 日集約版は符号を持たない(生の変化を残し、F2 で束の符号を掛ける)
                sgn = np.ones(sel.size)
                sides = np.array([""] * sel.size, dtype=object)
            else:
                sgn = t.sign[sel]
                sides = t.side[sel]
            m = measure(times, prices, None, tms, sgn)
            for j, i in enumerate(sel.tolist()):
                out.append(_row(gap, kind_out, t.cascade_id[i], day, sides[j], m, j,
                                None, None, None, None,
                                matched=(str(t.matched_liq_id[i])
                                         if kind_out == KIND_BII else "")))
    return out


# ===========================================================================
# 段 2: 対照 (a) 掃き合わせ(設計 §4 手順 1〜5)
# ===========================================================================
def band_cuts(sweeps: np.ndarray) -> np.ndarray:
    """同じ gap の S_b > 0 の 10 分位の切り値 q_1 … q_9(既定の線形補間)。"""
    v = sweeps[np.isfinite(sweeps) & (sweeps > 0)]
    if v.size == 0:
        return np.zeros(N_BANDS - 1)
    return np.quantile(v, [i / N_BANDS for i in range(1, N_BANDS)])


def band_of(v, cuts: np.ndarray):
    """帯 1 = (0, q_1)、帯 k ≥ 2 = [q_{k−1}, q_k)、帯 10 = [q_9, +∞)。

    v ≤ 0 と NaN はどの帯にも入らない(= −1)。設計 §4 手順 3(監査 3 回目・指摘 1)。
    """
    v = np.asarray(v, dtype=float)
    k = np.searchsorted(cuts, v, side="right") + 1
    return np.where(np.isfinite(v) & (v > 0), k, -1)


def select_control_a(day: str, bd: Bundles, cuts: np.ndarray, sweep_all: np.ndarray,
                     times: np.ndarray, prices: np.ndarray, bf: dict,
                     taken: dict, gap: int):
    """その日の束に対照 (a) を 1 つずつ当てる(`start_ms` の順、置換なし)。"""
    ks = bd.by_day.get(day, np.zeros(0, dtype=int))
    note = {"n_bundles": 0, "n_taken": 0, "abs_diff": []}
    if not ks.size:
        return [], note
    d0 = day_start_ms(day)
    grid = d0 + np.arange(GRID_N, dtype=np.int64) * GRID_STEP_MS
    grid_hi = int(grid[-1])
    # 候補の終端は W_b に依らないので 1 日 1 回だけ引く
    i_gend, ok_gend = idx_at_or_after(times, grid, STALENESS_MS)
    p_gend = np.where(ok_gend, prices[i_gend] if times.size else NAN, NAN)
    prev_day = (_dt.date.fromisoformat(day) - _dt.timedelta(days=1)).isoformat()

    def block(allowed, a, b, w):
        klo = max(0, -(-(a - CTRL_WINDOW_MS - d0) // GRID_STEP_MS))
        khi = min(GRID_N - 1, (b + w + 1 - d0) // GRID_STEP_MS)
        if khi >= klo:
            allowed[int(klo):int(khi) + 1] = False

    rows: list = []
    for k in ks.tolist():
        w = int(bd.width_ms[k])
        s_b = float(sweep_all[k])
        note["n_bundles"] += 1
        if not (math.isfinite(s_b) and s_b > 0):
            continue
        band_b = int(band_of(s_b, cuts))
        allowed = ok_gend.copy()
        # 手順 1: 同じ gap のどの束とも重ならない
        lo_b = d0 - bd.max_width_ms - w - 1 - CTRL_WINDOW_MS
        hi_b = grid_hi + CTRL_WINDOW_MS
        a0 = int(np.searchsorted(bd.start_ms, lo_b, side="left"))
        a1 = int(np.searchsorted(bd.start_ms, hi_b, side="right"))
        for a, b in zip(bd.start_ms[a0:a1].tolist(), bd.end_ms[a0:a1].tolist()):
            block(allowed, a, b, w)
        # 手順 4: 既に取った候補の区間とも重ならない
        for dd in (prev_day, day):
            for a, b in taken.get(dd, ()):
                block(allowed, a, b, w)
        cand = np.flatnonzero(allowed)
        if cand.size == 0:
            continue
        # 手順 2: 候補の掃き
        t_req = grid[cand] - w - 1
        i_p, ok_p = idx_at_or_before(times, t_req, STALENESS_MS)
        p_pre = np.where(ok_p, prices[i_p] if times.size else NAN, NAN)
        with np.errstate(invalid="ignore", divide="ignore"):
            c = np.where(ok_p & (p_pre > 0),
                         bd.sign[k] * (p_gend[cand] - p_pre) / p_pre * 1e4, NAN)
        # 手順 3: 同じ帯の中で |c_t − S_b| 最小、同値なら早い t
        same = band_of(c, cuts) == band_b
        if not bool(same.any()):
            continue
        diff = np.where(same, np.abs(c - s_b), np.inf)
        j = int(np.argmin(diff))
        t = int(grid[cand[j]])
        lo = t - w - 1
        taken.setdefault(day, []).append((lo, t + CTRL_WINDOW_MS))
        note["n_taken"] += 1
        note["abs_diff"].append(float(diff[j]))
        # 手順 5: 清算側と同じ式で f・r_pre・r_end
        sign1 = np.array([bd.sign[k]])
        m = measure(times, prices, np.array([lo], dtype=np.int64),
                    np.array([t], dtype=np.int64), sign1)
        bfv = bf_r_pre(bf, np.array([t - w], dtype=np.int64), m["ok_pre"],
                       m["t_end_ms"], m["ok_end"], sign1)
        rows.append(_row(gap, KIND_A, bd.cascade_id[k], day, bd.side[k], m, 0, bfv,
                         None, None, None, matched=str(bd.cascade_id[k]),
                         c_t=float(c[j]), ctrl_t=t))
    return rows, note


# ===========================================================================
# 走行(chunk で書き、再開できる)
# ===========================================================================
def run_stage1(out_dir: Path, days: list, bundles, tables, data_root: Path,
               bf: dict, progress_every: int) -> dict:
    work = out_dir / "chunks1"
    work.mkdir(parents=True, exist_ok=True)
    agg_cache: dict = {}
    missing: set = set()
    maxw = max(b.max_width_ms for b in bundles.values())
    t0 = time.time()
    for n_done, day in enumerate(days, start=1):
        cp = work / f"{day}.csv.gz"
        if cp.exists():
            continue
        times, prices, miss = load_window(
            data_root, day, agg_cache, STALENESS_MS + maxw,
            max(HORIZONS_SEC) * 1000 + STALENESS_MS)
        missing |= set(miss)
        rows = stage1_day(day, bundles, tables, times, prices, bf)
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


def _taken_from_chunk(path: Path, gap: int, bd: Bundles) -> list:
    out = []
    if not path.exists():
        return out
    with gzip.open(path, "rt", newline="") as fh:
        for r in csv.DictReader(fh):
            if int(r["gap"]) != gap or r["kind"] != KIND_A or not r["ctrl_t_ms"]:
                continue
            t = int(r["ctrl_t_ms"])
            k = bd.pos_of_id.get(r["cascade_id"])
            w = int(bd.width_ms[k]) if k is not None else 0
            out.append((t - w - 1, t + CTRL_WINDOW_MS))
    return out


def run_stage2(out_dir: Path, days: list, bundles, sweeps: dict,
               data_root: Path, bf: dict, progress_every: int) -> dict:
    work = out_dir / "chunks2"
    work.mkdir(parents=True, exist_ok=True)
    cuts = {gap: band_cuts(sweeps[gap]) for gap in GAPS}
    agg_cache: dict = {}
    notes = {gap: {"n_bundles": 0, "n_taken": 0} for gap in GAPS}
    taken: dict = {gap: {} for gap in GAPS}
    maxw = max(b.max_width_ms for b in bundles.values())
    t0 = time.time()
    for n_done, day in enumerate(days, start=1):
        cp = work / f"{day}.csv.gz"
        prev_day = (_dt.date.fromisoformat(day) - _dt.timedelta(days=1)).isoformat()
        if cp.exists():
            # 再開: その日に取った区間を読み直す(区間は 1 日以上は跨がない)
            for gap in GAPS:
                taken[gap] = {day: _taken_from_chunk(cp, gap, bundles[gap])}
            continue
        times, prices, _ = load_window(
            data_root, day, agg_cache, STALENESS_MS + maxw,
            CTRL_WINDOW_MS + max(HORIZONS_SEC) * 1000 + STALENESS_MS)
        rows = []
        for gap in GAPS:
            r, note = select_control_a(day, bundles[gap], cuts[gap], sweeps[gap],
                                       times, prices, bf, taken[gap], gap)
            rows += r
            notes[gap]["n_bundles"] += note["n_bundles"]
            notes[gap]["n_taken"] += note["n_taken"]
            taken[gap] = {k: v for k, v in taken[gap].items() if k in (prev_day, day)}
        tmp = work / f".{day}.part"
        with gz_open_w(tmp) as fh:
            w = csv.writer(fh)
            w.writerow(CHUNK_HEADER)
            w.writerows(rows)
        tmp.replace(cp)
        if n_done % progress_every == 0:
            print(f"  段2 {n_done}/{len(days)} 日 ({day}) 経過 {time.time() - t0:.0f}s",
                  flush=True)
    return {"cuts": {gap: [float(x) for x in cuts[gap]] for gap in GAPS},
            "notes": {str(g): notes[g] for g in GAPS}}


def read_sweeps(out_dir: Path, days: list, bundles: dict) -> dict:
    """段 1 の chunk から束ごとの sweep を読む(並びは `Bundles` の並び)。"""
    sw = {gap: np.full(bundles[gap].n, NAN) for gap in GAPS}
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
                if k is not None:
                    sw[gap][k] = _f(r["sweep_bp"])
    return sw


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


# ===========================================================================
# 集計
# ===========================================================================
NUMERIC_COLS = (["t_pre_ms", "t_end_ms", "p_pre", "p_end", "baseline_lag_ms",
                 "end_lag_ms", "sweep_bp", "prev_bundle_gap_s", "next_bundle_gap_s",
                 "c_t", "ctrl_t_ms"]
                + [f"r_pre_{h}" for h in HORIZONS_SEC]
                + [f"r_end_{h}" for h in HORIZONS_SEC]
                + [f"f_{h}" for h in HORIZONS_SEC]
                + [f"h_lag_ms_{h}" for h in HORIZONS_SEC]
                + [f"bf_r_pre_{h}" for h in HORIZONS_SEC])
FLAG_COLS = ["baseline_in_prev_bundle"] + [f"h_same_as_end_{h}" for h in HORIZONS_SEC]


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
            for c in FLAG_COLS:
                b[c] = np.array([x == "1" for x in cols[c]], dtype=bool)[m]
            b["_n"] = int(m.sum())
            self.blk[k] = b


def make_f0(rows_by_gap: dict, ctrl_notes: dict) -> list:
    out = []
    for gap in GAPS:
        b = rows_by_gap[gap].blk
        for kind in KINDS:
            blk = b[kind]
            n = blk["_n"]
            if kind in (KIND_LIQ, KIND_A):
                v = blk["baseline_lag_ms"] - 1.0   # 求めた時刻 − 見つかった約定の時刻
                p = quantiles(v, [50, 90, 99, 100])
                nn = int(np.isfinite(v).sum())
                out.append({"gap(秒)": gap, "種": KIND_LABEL[kind], "量": "基準の遅れ(ms)",
                            "p50": p[0], "p90": p[1], "p99": p[2], "最大": p[3],
                            "n": nn, "引けない行": n - nn,
                            "h 後が終端と同じ約定の割合": "—"})
            else:
                out.append({"gap(秒)": gap, "種": KIND_LABEL[kind], "量": "基準の遅れ(ms)",
                            "p50": "—", "p90": "—", "p99": "—", "最大": "—",
                            "n": "—", "引けない行": "—",
                            "h 後が終端と同じ約定の割合": "—"})
            v = blk["end_lag_ms"]
            p = quantiles(v, [50, 90, 99, 100])
            nn = int(np.isfinite(v).sum())
            out.append({"gap(秒)": gap, "種": KIND_LABEL[kind], "量": "終端の遅れ(ms)",
                        "p50": p[0], "p90": p[1], "p99": p[2], "最大": p[3],
                        "n": nn, "引けない行": n - nn,
                        "h 後が終端と同じ約定の割合": "—"})
            for h in HORIZONS_SEC:
                v = blk[f"h_lag_ms_{h}"]
                fin = np.isfinite(v)
                p = quantiles(v, [50, 90, 99, 100])
                same = blk[f"h_same_as_end_{h}"][fin]
                out.append({"gap(秒)": gap, "種": KIND_LABEL[kind],
                            "量": f"h 後の遅れ(ms) h={h}",
                            "p50": p[0], "p90": p[1], "p99": p[2], "最大": p[3],
                            "n": int(fin.sum()), "引けない行": n - int(fin.sum()),
                            "h 後が終端と同じ約定の割合":
                                float(same.mean()) if same.size else NAN})
    for gap in GAPS:
        note = ctrl_notes[gap]
        d = np.array(note["abs_diff"], dtype=float)
        p = quantiles(d, [50, 90, 99, 100])
        nb = int(note["n_bundles_positive_sweep"])
        nt = int(note["n_taken"])
        out.append({"gap(秒)": gap, "種": KIND_LABEL[KIND_A], "量": "|c_t − S_b|(bp)",
                    "p50": p[0], "p90": p[1], "p99": p[2], "最大": p[3],
                    "n": nt, "引けない行": nb - nt,
                    "h 後が終端と同じ約定の割合":
                        f"取れなかった束 {nb - nt}/{nb}"
                        + (f" = {(nb - nt) / nb:.6f}" if nb else "")})
    return out


def make_f1(rows_by_gap: dict, bundles: dict, mixed: dict) -> list:
    out = []
    for gap in GAPS:
        blk = rows_by_gap[gap].blk[KIND_LIQ]
        bd = bundles[gap]
        nev_by_id = {c: v for c, v in zip(bd.cascade_id.tolist(), bd.n_events.tolist())}
        n_ev = np.array([nev_by_id.get(c, NAN) for c in blk["cascade_id"].tolist()],
                        dtype=float)
        lo, hi = tertile_cuts(n_ev)
        sw = blk["sweep_bp"]
        side = blk["side"]
        groups = [("全体", np.ones(blk["_n"], dtype=bool)),
                  ("SELL", side == "SELL"), ("BUY", side == "BUY")]
        for q, label in ex2.TERTILE_LABELS:
            groups.append((f"束の件数 {label}", tertile_mask(n_ev, lo, hi, q)))
        for name, m in groups:
            v = sw[m]
            fin = v[np.isfinite(v)]
            bl = blk["baseline_lag_ms"][m]
            prev = blk["prev_bundle_gap_s"][m]
            near = prev[np.isfinite(prev)]
            out.append({
                "gap(秒)": gap, "群": name, "n": int(m.sum()),
                "sweep 平均(bp)": float(fin.mean()) if fin.size else NAN,
                "sweep 中央値(bp)": float(np.median(fin)) if fin.size else NAN,
                "sweep p10": quantiles(v, [10])[0],
                "sweep p90": quantiles(v, [90])[0],
                "sweep ≤ 0 の数": int((fin <= 0).sum()),
                "sweep が NaN の数": int(m.sum() - fin.size),
                "baseline_lag_ms 中央値": quantiles(bl, [50])[0],
                "baseline_lag_ms p90": quantiles(bl, [90])[0],
                "基準が直前の束の end_ms 以下の束の数":
                    int(blk["baseline_in_prev_bundle"][m].sum()),
                "前の束から 300 秒未満の割合":
                    float((near < PREV_NEAR_SEC).mean()) if near.size else NAN,
                "前の束の間隔が NaN の数": int(m.sum() - near.size),
                "両側混在で外れた束の割合": "—",
            })
        nl = blk["_n"]
        nm = mixed[gap]
        out.append({
            "gap(秒)": gap, "群": "両側混在で主表から外れた束", "n": nm,
            "sweep 平均(bp)": "—", "sweep 中央値(bp)": "—",
            "sweep p10": "—", "sweep p90": "—",
            "sweep ≤ 0 の数": "—", "sweep が NaN の数": "—",
            "baseline_lag_ms 中央値": "—", "baseline_lag_ms p90": "—",
            "基準が直前の束の end_ms 以下の束の数": "—",
            "前の束から 300 秒未満の割合": "—",
            "前の束の間隔が NaN の数": "—",
            "両側混在で外れた束の割合": (round(nm / (nl + nm), 6)
                              if nl + nm else NAN),
        })
    return out


def _stats(vals: np.ndarray, days: np.ndarray) -> dict:
    m, se, naive, n, g = mean_se_cluster(vals, days)
    return {"平均": m, "日クラスタ SE": se, "naive SE": naive, "n": n, "日数": g,
            "日等重み平均": day_equal_weight_mean(vals, days)}


def f2_groups(rows: Rows) -> list:
    liq = rows.blk[KIND_LIQ]
    nb = liq["next_bundle_gap_s"]
    pb = liq["prev_bundle_gap_s"]
    return [
        ("清算 全体", liq, np.ones(liq["_n"], dtype=bool)),
        (f"清算 次の束まで {SUBSET_SEC} 秒以上(結果依存の条件付け)",
         liq, np.isfinite(nb) & (nb >= SUBSET_SEC)),
        (f"清算 前の束から {SUBSET_SEC} 秒以上(過去の条件付け)",
         liq, np.isfinite(pb) & (pb >= SUBSET_SEC)),
        ("対照(a) 掃き合わせ", rows.blk[KIND_A],
         np.ones(rows.blk[KIND_A]["_n"], dtype=bool)),
        ("対照(b)-i 一様(日集約)", None, None),
        ("対照(b)-ii 薄さ合わせ", rows.blk[KIND_BII],
         np.ones(rows.blk[KIND_BII]["_n"], dtype=bool)),
    ]


def bi_day_aggregate(rows: Rows, h: int):
    """対照 (b)-i: 一様行の生の r_end を日ごとに平均し、束の符号を掛ける。"""
    bi = rows.blk[KIND_BI]
    liq = rows.blk[KIND_LIQ]
    raw = bi[f"r_end_{h}"]
    acc: dict = defaultdict(list)
    for x, d in zip(raw.tolist(), bi["day"].tolist()):
        if math.isfinite(x):
            acc[d].append(x)
    dm = {k: sum(v) / len(v) for k, v in acc.items()}
    vals, days = [], []
    for s, d in zip(liq["side"].tolist(), liq["day"].tolist()):
        sg = REACT_SIGN.get(s, NAN)
        if d in dm and math.isfinite(sg):
            vals.append(sg * dm[d])
            days.append(d)
    same = bi[f"h_same_as_end_{h}"][np.isfinite(bi[f"h_lag_ms_{h}"])]
    return (np.array(vals, dtype=float), np.array(days, dtype=object),
            float(same.mean()) if same.size else NAN)


DASH_F = {"r_pre 平均(bp)": "—", "r_pre 日クラスタ SE": "—", "r_pre naive SE": "—",
          "r_pre 日等重み平均": "—", "f 中央値": "—", "f p25": "—", "f p75": "—",
          "f > 1 の割合": "—", "0 ≤ f ≤ 1 の割合": "—", "f < 0 の割合": "—",
          "f が有限な n": "—"}


def make_f2(rows_by_gap: dict) -> list:
    out = []
    for gap in GAPS:
        rows = rows_by_gap[gap]
        for h in HORIZONS_SEC:
            for name, blk, m in f2_groups(rows):
                if blk is None:
                    vals, days, same = bi_day_aggregate(rows, h)
                    st = _stats(vals, days)
                    row = {"gap(秒)": gap, "h(秒)": h, "群": name,
                           "n": st["n"], "含む日数": st["日数"],
                           "r_end 平均(bp)": st["平均"],
                           "r_end 日クラスタ SE": st["日クラスタ SE"],
                           "r_end naive SE": st["naive SE"],
                           "r_end 日等重み平均": st["日等重み平均"]}
                    row.update(DASH_F)
                    row["h 後が終端と同じ約定の割合"] = same
                    out.append(row)
                    continue
                days = blk["day"][m]
                st_e = _stats(blk[f"r_end_{h}"][m], days)
                row = {"gap(秒)": gap, "h(秒)": h, "群": name,
                       "n": st_e["n"], "含む日数": st_e["日数"],
                       "r_end 平均(bp)": st_e["平均"],
                       "r_end 日クラスタ SE": st_e["日クラスタ SE"],
                       "r_end naive SE": st_e["naive SE"],
                       "r_end 日等重み平均": st_e["日等重み平均"]}
                if name.startswith("対照(b)"):
                    row.update(DASH_F)
                else:
                    st_p = _stats(blk[f"r_pre_{h}"][m], days)
                    fv = blk[f"f_{h}"][m]
                    fin = fv[np.isfinite(fv)]
                    qs = quantiles(fv, [25, 50, 75])
                    row.update({
                        "r_pre 平均(bp)": st_p["平均"],
                        "r_pre 日クラスタ SE": st_p["日クラスタ SE"],
                        "r_pre naive SE": st_p["naive SE"],
                        "r_pre 日等重み平均": st_p["日等重み平均"],
                        "f 中央値": qs[1], "f p25": qs[0], "f p75": qs[2],
                        "f > 1 の割合": float((fin > 1).mean()) if fin.size else NAN,
                        "0 ≤ f ≤ 1 の割合":
                            float(((fin >= 0) & (fin <= 1)).mean()) if fin.size else NAN,
                        "f < 0 の割合": float((fin < 0).mean()) if fin.size else NAN,
                        "f が有限な n": int(fin.size)})
                fin_h = np.isfinite(blk[f"h_lag_ms_{h}"][m])
                sm = blk[f"h_same_as_end_{h}"][m][fin_h]
                row["h 後が終端と同じ約定の割合"] = (float(sm.mean()) if sm.size else NAN)
                out.append(row)
    return out


def make_f3(rows_by_gap: dict) -> list:
    out = []
    for gap in GAPS:
        blk = rows_by_gap[gap].blk[KIND_LIQ]
        for h in HORIZONS_SEC:
            fv = blk[f"f_{h}"]
            m = np.isfinite(fv) & (fv > 1)
            over = -blk[f"r_pre_{h}"][m]          # 基準を越えた幅(bp)
            sw = blk["sweep_bp"][m]
            with np.errstate(invalid="ignore", divide="ignore"):
                ratio = np.where(np.isfinite(sw) & (sw > 0), over / sw, NAN)
            po = quantiles(over, [10, 25, 50, 75, 90])
            pr = quantiles(ratio, [10, 25, 50, 75, 90])
            out.append({
                "gap(秒)": gap, "h(秒)": h, "f > 1 の束の n": int(m.sum()),
                "越えた幅 p10(bp)": po[0], "越えた幅 p25": po[1], "越えた幅 p50": po[2],
                "越えた幅 p75": po[3], "越えた幅 p90": po[4],
                "越えた幅/sweep p10": pr[0], "越えた幅/sweep p25": pr[1],
                "越えた幅/sweep p50": pr[2], "越えた幅/sweep p75": pr[3],
                "越えた幅/sweep p90": pr[4],
            })
    return out


def _f5_row(attr, grp, lo, hi, h, blk, m, miss) -> dict:
    days = blk["day"][m]
    st = _stats(blk[f"r_pre_{h}"][m], days)
    fv = blk[f"f_{h}"][m]
    fin = fv[np.isfinite(fv)]
    return {"属性": attr, "群": grp, "下限": lo, "上限": hi, "h(秒)": h,
            "f > 1 の割合": float((fin > 1).mean()) if fin.size else NAN,
            "f が有限な n": int(fin.size),
            "r_pre 平均(bp)": st["平均"], "日クラスタ SE": st["日クラスタ SE"],
            "n": st["n"], "含む日数": st["日数"],
            "属性が欠測で群に入らない束の割合": miss}


def make_f5(rows: Rows, table: "ex2.RunTable") -> list:
    """gap 60 だけ。探索段 1 と同じ 10 属性 30 群 + sweep の 3 分位 = 33 群。"""
    groups = ex2.attribute_groups(table)
    blk = rows.blk[KIND_LIQ]
    cid = blk["cascade_id"]
    liq_i = np.flatnonzero(table.kind == KIND_LIQ)
    miss_frac: dict = {}
    for name, col, take_abs in ex2.ATTRS_NUM:
        v = table.num(col)[liq_i]
        if take_abs:
            v = np.abs(v)
        miss_frac[name] = float((~np.isfinite(v)).mean())
    miss_frac[ex2.ATTR_SIDE] = float((table.side[liq_i] == "").mean())
    miss_frac[ex2.ATTR_HOUR] = 0.0
    # sweep の 3 分位: S_b > 0 の束を母集団に、探索段 2 と同じ規則。S_b ≤ 0 は欠測。
    sw = blk["sweep_bp"]
    sw_pos = np.where(np.isfinite(sw) & (sw > 0), sw, NAN)
    lo, hi = tertile_cuts(sw_pos)
    sweep_groups = []
    for q, label in ex2.TERTILE_LABELS:
        sel = tertile_mask(sw_pos, lo, hi, q)
        bounds = {1: (NAN, lo), 2: (lo, hi), 3: (hi, NAN)}[q]
        sweep_groups.append(("sweep_bp", label, bounds[0], bounds[1], sel))
    miss_frac["sweep_bp"] = float((~np.isfinite(sw_pos)).mean())

    out = []
    for h in HORIZONS_SEC:
        for g in groups:
            ids = g["ids"]
            m = np.array([c in ids for c in cid.tolist()], dtype=bool)
            out.append(_f5_row(g["属性"], g["群"], g["下限"], g["上限"], h, blk, m,
                               miss_frac.get(g["属性"], NAN)))
        for attr, label, glo, ghi, sel in sweep_groups:
            out.append(_f5_row(attr, label, glo, ghi, h, blk, sel,
                               miss_frac["sweep_bp"]))
    return out


# ===========================================================================
# 清算行の重複(設計 §7、反証者 2 の #7)
# ===========================================================================
def liq_multiplicity_all_days(data_root: Path) -> dict:
    root = Path(data_root) / "liquidationSnapshot" / base.SYMBOL
    zips = sorted(root.glob(f"{base.SYMBOL}-liquidationSnapshot-*.zip"))
    total_rows = 0
    total_uniq = 0
    mult: dict = defaultdict(int)
    days = []
    for p in zips:
        with zipfile.ZipFile(p) as zf:
            names = [n for n in zf.namelist() if n.endswith(".csv")]
            with zf.open(names[0]) as fh:
                rd = csv.reader(io.TextIOWrapper(fh, encoding="utf-8"))
                next(rd, None)
                rows = [tuple(r) for r in rd if r]
        cnt: dict = defaultdict(int)
        for r in rows:
            cnt[r] += 1
        total_rows += len(rows)
        total_uniq += len(cnt)
        for c in cnt.values():
            mult[c] += 1
        days.append(p.name[-14:-4])
    hist = {str(k): int(v) for k, v in sorted(mult.items())}
    ge3 = sum(v for k, v in mult.items() if k >= 3)
    return {
        "方法": ("生の zip を直接開き、ヘッダを除く全行を全列のタプルで数える"
               "(探索段 2 の `liq_duplicate_probe` と同じ数え方を全日に広げたもの)。"),
        "日数": len(zips), "最初の日": days[0] if days else None,
        "最後の日": days[-1] if days else None,
        "raw の行数(ヘッダ除く)": total_rows,
        "全列一致で一意にした行数": total_uniq,
        "多重度の内訳(群の数)": hist,
        "多重度 1 の群": int(mult.get(1, 0)),
        "多重度 2 の群": int(mult.get(2, 0)),
        "多重度 3 以上の群": int(ge3),
        "DATA.md §2 の実測": {"日数": 472, "raw の行数": 106822, "一意": 53398,
                          "多重度 2 の群": 53385, "多重度 4 の群": 13},
        "DATA.md と一致するか": {
            "日数": len(zips) == 472,
            "raw の行数": total_rows == 106822,
            "一意": total_uniq == 53398,
            "多重度 2 の群": int(mult.get(2, 0)) == 53385,
            "多重度 4 の群": int(mult.get(4, 0)) == 13,
        },
    }


# ===========================================================================
# main
# ===========================================================================
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="O3C SIGNAL 探索段 3")
    ap.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    ap.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    ap.add_argument("--bitflyer-dir", type=Path, default=DEFAULT_BITFLYER_DIR)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stage", choices=("rows", "tables", "all"), default="all")
    ap.add_argument("--limit-days", type=int, default=0)
    ap.add_argument("--progress-every", type=int, default=20)
    ap.add_argument("--skip-liq-dup", action="store_true",
                    help="清算行の多重度の数え直しを飛ばす(試験用)")
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

    years = sorted({int(d[:4]) for d in days} | {int(d[:4]) + 1 for d in days})
    bf = ex2.load_bitflyer_minutes(years, a.bitflyer_dir)
    print(f"bitFlyer 1 分足 {bf['t_ms'].size} 点 / 無い年 {bf['years_missing']}",
          flush=True)

    if a.stage in ("rows", "all"):
        note1 = run_stage1(a.out, days, bundles, tables, a.data_root, bf,
                           a.progress_every)
        sweeps = read_sweeps(a.out, days, bundles)
        note2 = run_stage2(a.out, days, bundles, sweeps, a.data_root, bf,
                           a.progress_every)
        concat_rows(a.out, days)
        (a.out / "stage_notes.json").write_text(json.dumps(
            {"stage1": note1, "stage2_cuts": note2["cuts"],
             "stage2_notes": note2["notes"]}, ensure_ascii=False, indent=2))
    if a.stage == "rows":
        return 0

    rows_by_gap = {gap: Rows(a.out / f"rows_gap{gap}.csv.gz") for gap in GAPS}

    ctrl_notes = {}
    for gap in GAPS:
        liq = rows_by_gap[gap].blk[KIND_LIQ]
        ca = rows_by_gap[gap].blk[KIND_A]
        sw_pos = int((np.isfinite(liq["sweep_bp"]) & (liq["sweep_bp"] > 0)).sum())
        sb = {c: s for c, s in zip(liq["cascade_id"].tolist(),
                                   liq["sweep_bp"].tolist())}
        diffs = [abs(ct - sb[c]) for c, ct in
                 zip(ca["cascade_id"].tolist(), ca["c_t"].tolist())
                 if c in sb and math.isfinite(ct) and math.isfinite(sb[c])]
        ctrl_notes[gap] = {"n_bundles_positive_sweep": sw_pos,
                           "n_taken": ca["_n"], "abs_diff": diffs}

    f0 = make_f0(rows_by_gap, ctrl_notes)
    f1 = make_f1(rows_by_gap, bundles, mixed)
    f2 = make_f2(rows_by_gap)
    f3 = make_f3(rows_by_gap)
    f5 = make_f5(rows_by_gap[MAIN_GAP], tables["gap60_w8"])
    write_csv(a.out / "f0_selfcheck.csv", f0)
    write_csv(a.out / "f1_sweep.csv", f1)
    write_csv(a.out / "f2_retrace.csv", f2)
    write_csv(a.out / "f3_overshoot.csv", f3)
    write_csv(a.out / "f5_attributes.csv", f5)

    inputs = {}
    for run in RUNS:
        p = a.runs_dir / run / "table.csv"
        inputs[str(p.relative_to(REPO_ROOT))] = md5_of(p)

    missing_cal = calendar_gaps(days)
    per_gap = {}
    for gap in GAPS:
        b = rows_by_gap[gap].blk
        liq = b[KIND_LIQ]
        per_gap[f"gap{gap}"] = {
            "この段の行数": {KIND_LABEL[k]: b[k]["_n"] for k in KINDS},
            "1 周目の表の行数": {"liq": tables[f"gap{gap}_w8"].n_liq,
                         "control_uniform": tables[f"gap{gap}_w8"].n_uniform,
                         "control_matched": tables[f"gap{gap}_w8"].n_matched},
            "両側混在で主表から外れた束(table_mixed.csv)": mixed[gap],
            "sweep ≤ 0 の束": int((np.isfinite(liq["sweep_bp"])
                                & (liq["sweep_bp"] <= 0)).sum()),
            "sweep が NaN の束": int((~np.isfinite(liq["sweep_bp"])).sum()),
            "基準が引けない束": int((~np.isfinite(liq["p_pre"])).sum()),
            "終端が引けない束": int((~np.isfinite(liq["p_end"])).sum()),
            "対照 (a) の対象(sweep > 0)": ctrl_notes[gap]["n_bundles_positive_sweep"],
            "対照 (a) を取れた束": ctrl_notes[gap]["n_taken"],
            "対照 (a) が取れなかった束": (ctrl_notes[gap]["n_bundles_positive_sweep"]
                              - ctrl_notes[gap]["n_taken"]),
            "次の束の間隔が NaN(その日の最後の束)": int(
                (~np.isfinite(liq["next_bundle_gap_s"])).sum()),
            "前の束の間隔が NaN(その日の最初の束)": int(
                (~np.isfinite(liq["prev_bundle_gap_s"])).sum()),
            "r_end_60 が NaN": int((~np.isfinite(liq["r_end_60"])).sum()),
            "r_pre_900 が NaN": int((~np.isfinite(liq["r_pre_900"])).sum()),
            "bf_r_pre_60 が NaN": int((~np.isfinite(liq["bf_r_pre_60"])).sum()),
            "基準が直前の束の end_ms 以下の束": int(liq["baseline_in_prev_bundle"].sum()),
        }

    dup = ({"備考": "--skip-liq-dup で飛ばした"} if a.skip_liq_dup
           else liq_multiplicity_all_days(a.data_root))

    stage_notes = {}
    p_notes = a.out / "stage_notes.json"
    if p_notes.exists():
        stage_notes = json.loads(p_notes.read_text())

    summary = {
        "実行時刻(UTC)": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "経過秒": round(time.time() - t0, 1),
        "設計": "docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE3_DESIGN_2026-09-20.md",
        "パラメータ": {
            "h(秒)": list(HORIZONS_SEC), "走行": list(RUNS),
            "穴の上限(ms)": STALENESS_MS,
            "対照 (a) の候補の刻み(ms)": GRID_STEP_MS,
            "対照 (a) の候補点/日": GRID_N,
            "対照 (a) の区間の後ろ(ms)": CTRL_WINDOW_MS,
            "帯の数": N_BANDS,
            "帯の規則": "帯 1 = (0, q_1)、帯 k ≥ 2 = [q_{k−1}, q_k)、c_t ≤ 0 は帯なし",
            "F2 の部分集合(秒)": SUBSET_SEC,
            "F1 の「前の束から近い」(秒)": PREV_NEAR_SEC,
            "符号": "SELL: −1 / BUY: +1(探索段 1・2 と同じ向き。負 = 清算と逆)",
            "基準": "at_or_before(start_ms − 1, 300_000)",
            "終端": "at_or_after(end_ms, 300_000)",
            "h 後": "at_or_before(終端の約定の時刻 + h*1000, 300_000)",
            "対照 (b)-i": ("一様行の生(符号なし)の r_end を日ごとに平均し、"
                       "束の符号を掛けて束ごとの値にする(日集約版)"),
            "対照 (b)-ii": "matched_liq_id の相手の束の side で符号を付ける",
            "h 後が終端と同じ": "at_or_before が終端と同じ約定を返した(間に約定が無い)",
            "前後の束の間隔": "同じ日・同じ gap(設計の用語表)。日の最初/最後は NaN",
        },
        "入力の MD5": inputs,
        "日数": len(days),
        "暦の日数(最初〜最後)": (
            (_dt.date.fromisoformat(days[-1]) - _dt.date.fromisoformat(days[0])).days + 1),
        "欠けた日": missing_cal, "欠けた日の数": len(missing_cal),
        "走行ごと": per_gap,
        "対照 (a) の帯の切り値": stage_notes.get("stage2_cuts", {}),
        "約定が読めなかった日": stage_notes.get("stage1", {}).get(
            "agg_days_missing", "(この走行では rows 段を回していない)"),
        "bitFlyer の無い年": bf["years_missing"],
        "表の行数": {"F0": len(f0), "F1": len(f1), "F2": len(f2), "F3": len(f3),
                 "F5": len(f5),
                 "合計": len(f0) + len(f1) + len(f2) + len(f3) + len(f5)},
        "清算行の多重度(全日)": dup,
    }
    txt = json.dumps(summary, ensure_ascii=False, indent=2)
    check_no_banned(txt, "summary.json")
    (a.out / "summary.json").write_text(txt)

    md = [f"# O3C SIGNAL 探索段 3 の表({days[0]} 〜 {days[-1]}、{len(days)} 日)", "",
          f"- 設計: `{summary['設計']}`",
          f"- h(秒) = {list(HORIZONS_SEC)} / gap = 60 主、30 / 180 併記",
          f"- 欠けた日({len(missing_cal)} 日): " + ", ".join(missing_cal),
          "- 基準 = `at_or_before(start_ms − 1, 300_000)` / 終端 = "
          "`at_or_after(end_ms, 300_000)` / h 後 = "
          "`at_or_before(終端の約定の時刻 + h*1000, 300_000)`",
          "- 「h 後が終端と同じ約定」= h 後の引きが終端と同じ約定を返した(間に約定が無い)",
          "- bitFlyer の列(`bf_r_pre_*`)は 1 分足の終値。基準は `start_ms` を含む足の"
          " 1 本前の終値(**窓ずれ**: 基準は起点より最大 1 分前)", "",
          "## F0 自己点検(基準・終端・h 後の遅れ、対照 (a) の合わせ具合)", "",
          md_table(f0), "",
          "## F1 掃きの大きさ(清算側)", "", md_table(f1), "",
          "## F2 戻り率と h 後の位置", "", md_table(f2), "",
          "## F3 基準を越えた幅(f > 1 の束)", "", md_table(f3), "",
          "## F5 属性(清算側、gap 60)", "", md_table(f5), ""]
    mdtxt = "\n".join(md)
    check_no_banned(mdtxt, "tables.md")
    (a.out / "tables.md").write_text(mdtxt)

    names = [f"rows_gap{g}.csv.gz" for g in GAPS] + [
        "f0_selfcheck.csv", "f1_sweep.csv", "f2_retrace.csv", "f3_overshoot.csv",
        "f5_attributes.csv", "tables.md", "summary.json"]
    lines = []
    for n in names:
        p = a.out / n
        if p.exists():
            lines.append(f"{md5_of(p)}  {n}")
    (a.out / "MD5SUMS").write_text("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)
    print(f"完了 {time.time() - t0:.0f}s -> {a.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

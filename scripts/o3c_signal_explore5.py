#!/usr/bin/env python3
"""清算を起点とした値動きの予測可能性(SIGNAL)— **探索段 5** の道具。

設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE5_DESIGN_2026-09-20.md`
(用語表 / §2 問い H0〜H6 / §4 対照 / §6 データと出力 / §7 走らせる前に決めること)。

**この道具がすること**
  - 起点を**清算 1 件ごとのプリント**にする(束にしない)。プリント = Binance COIN-M の
    `liquidationSnapshot` の 1 行(全列一致の 2 行は 1 件)。
  - プリント `ts`(ms)ごとに約定から引く量(設計の用語表。**m・k・d は `ts` 基準**):
      起点     p₀   = `at_or_after(ts, 300_000)`、t₀ = p₀ の約定の時刻
      直前     p_pre = `at_or_before(ts − 1, 300_000)`
      T 秒前   p_T  = `at_or_before(ts − T*1000, 300_000)`
      h 後     p_h  = `at_or_before(t₀ + h*1000, 300_000)`(**t₀ 基準**)
      m(T) = s × (p_pre − p_T)/p_T × 1e4、k = s × (p₀ − p_pre)/p_pre × 1e4、
      r(h) = s × (p_h − p₀)/p₀ × 1e4。s = SELL: −1 / BUY: +1。
    **後の動き r(h) の基準は t₀(設計の訂正 2026-09-20、用語表の r(h) の行)。**
    主の表 H1〜H6 と H0 の診断・欠測はこの列(`r_t0_h`)を使う。設計の前版の式
    `at_or_before(ts + h*1000)` の版(列 `r_h`)も行データに残っており、H0 の
    「診断(束の位置)」「起点の取り方」の行に**併記**する。
    探索段 4 の `r_end(h)` は t₀ 基準なので、H0 診断「最後」の r(60) は
    −6.800366 と突き合わせられる(設計 §0・§7)。
  - 層の列(m・k・d・側・想定元本・時刻帯・付け直した属性)は **t₀ 以前のデータだけ**で作る。
  - 対照 (c') 直前の値動き合わせ(設計 §4)、対照 (b) = 1 周目の対照 (i) 日集約版。
  - 出力は H0〜H6 の表・`rows_prints.csv.gz`・`tables.md`・`summary.json`・`MD5SUMS`。

**探索段なので判定語を 1 つも書かない。**検定もしない。読み(なぜ)も書かない。

**`paper_logs/` は開かない**(自前記録は判定まで触らない、L-246)。この道具は
`backtest_data/` 以外のどのディレクトリも読まない。
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
import o3c_oi_distance as oid  # noqa: E402
import o3c_reaction as rx  # noqa: E402

_spec4 = importlib.util.spec_from_file_location(
    "o3c_signal_explore4", _HERE / "o3c_signal_explore4.py")
ex4 = importlib.util.module_from_spec(_spec4)
assert _spec4.loader is not None
_spec4.loader.exec_module(ex4)
ex3 = ex4.ex3
ex2 = ex4.ex2

REPO_ROOT = _HERE.parent
NAN = float("nan")

# ---------------------------------------------------------------------------
# 固定値(設計 §7。変えるときは報告に列挙する)
# ---------------------------------------------------------------------------
T_MAIN = (10, 60)                      # m(T) の窓
T_TERTILE = 60                         # 3 分位を切る T
HORIZONS_SEC = (1, 5, 10, 30, 60, 300, 900)
H_MAIN = (60, 300, 900)                # H3〜H6 の h 3 本
STALENESS_MS = ex2.STALENESS_MS        # 300_000
N_BANDS = 10                           # m の 10 分位帯
NEXT_SEC = (60, 120)                   # 次の清算(結果)の境界
DENSITY_WINDOW_MS = 300_000            # d の窓 [ts − 300_000, ts)
GRID_STEP_MS = 10_000                  # 対照 (c') の候補時刻の刻み
GRID_N = 8_640                         # 1 日の候補点
CTRL_WINDOW_MS = 900_000               # 候補の区間の後ろ側(= 最大 h)
W_HOURS = 8.0                          # 属性の窓(1 周目 gap60_w8 と同じ)
BIN_PCT = 0.1                          # 1 周目と同じ価格ビンの幅
MMR = 0.004                            # 1 周目と同じ維持証拠金率
MS_PER_DAY = 86_400_000

REACT_SIGN = ex2.REACT_SIGN            # {"SELL": -1.0, "BUY": 1.0}
HOUR_BANDS = ex2.HOUR_BANDS
TERTILE_LABELS = ex2.TERTILE_LABELS

# 主の表(H1〜H6)が使う後の動きの列。設計の訂正(2026-09-20)で t₀ 基準にした。
# `r`(ts 基準)は H0 の「併記」の行にだけ残す。
R_MAIN_COL = "r_t0"                    # r_t0_h = t₀(p₀ の約定の時刻)基準
R_ALT_COL = "r"                        # r_h    = ts(清算の時刻)基準、併記のみ

KIND_PRINT = "print"
KIND_C = "control_c"
KIND_BI = "control_b_i"
KINDS = (KIND_PRINT, KIND_C, KIND_BI)
KIND_LABEL = {KIND_PRINT: "清算のプリント",
              KIND_C: "対照(c') 直前の値動き合わせ",
              KIND_BI: "対照(b) 一様(日集約)"}

POS_FIRST, POS_MID, POS_LAST, POS_NONE = "最初", "途中", "最後", "束の外"
POSITIONS = (POS_FIRST, POS_MID, POS_LAST)

DEFAULT_RUNS_DIR = ex2.DEFAULT_RUNS_DIR
DEFAULT_DATA_ROOT = ex2.DEFAULT_DATA_ROOT
DEFAULT_OUT = REPO_ROOT / "backtest_data" / "o3c_signal_explore5_20260920"
MAIN_RUN = "gap60_w8"

BANNED_WORDS = ex2.BANNED_WORDS
ATTR_NAMES = ("bin_pct", "|dist_node_bp|", "implied_leverage")

ROW_COLUMNS = (
    ["kind", "print_id", "day", "side", "ctrl_T", "ts_ms", "t0_ms", "p0",
     "t_pre_ms", "p_pre", "p0_lag_ms", "pre_lag_ms", "k", "d",
     "bundle_id", "bundle_pos", "bundle_pos_single", "notional", "hour_band"]
    + [f"m_{T}" for T in T_MAIN]
    + [f"m_lag_ms_{T}" for T in T_MAIN]
    + [f"r_{h}" for h in HORIZONS_SEC]
    + [f"r_t0_{h}" for h in HORIZONS_SEC]
    + [f"h_lag_ms_{h}" for h in HORIZONS_SEC]
    + ["next_same_side_gap_s", "bin_pct", "dist_node_bp", "implied_leverage",
       "oi_covered", "matched_print_id", "c_t", "k_ctrl", "ctrl_t_ms"])
CHUNK_HEADER = list(ROW_COLUMNS)

NUMERIC_COLS = (["ctrl_T", "ts_ms", "t0_ms", "p0", "t_pre_ms", "p_pre",
                 "p0_lag_ms", "pre_lag_ms", "k", "d", "notional"]
                + [f"m_{T}" for T in T_MAIN]
                + [f"m_lag_ms_{T}" for T in T_MAIN]
                + [f"r_{h}" for h in HORIZONS_SEC]
                + [f"r_t0_{h}" for h in HORIZONS_SEC]
                + [f"h_lag_ms_{h}" for h in HORIZONS_SEC]
                + ["next_same_side_gap_s", "bin_pct", "dist_node_bp",
                   "implied_leverage", "oi_covered", "c_t", "k_ctrl",
                   "ctrl_t_ms", "bundle_pos_single"])

# ===========================================================================
# 小道具(探索段 2・3・4 から借りるもの)
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
band_of_m = ex4.band_of_m
band_bounds = ex4.band_bounds
bound_text = ex4.bound_text
corr = ex4.corr
DASH = "—"


def check_no_banned(text: str, where: str) -> None:
    hit = [w for w in BANNED_WORDS if w in text]
    if hit:
        raise SystemExit(f"[止め] 判定語が出力に混ざっている({where}): {hit}")


def band_cuts_m(vals) -> np.ndarray:
    """456 日の**全プリント**の m の 10 分位の切り値 q_1 … q_9(負も含む)。"""
    v = np.asarray(vals, dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return np.zeros(N_BANDS - 1)
    return np.quantile(v, [i / N_BANDS for i in range(1, N_BANDS)])


def day_of_ms(ts_ms: int) -> str:
    return (_dt.datetime.fromtimestamp(int(ts_ms) / 1000, _dt.timezone.utc)
            .date().isoformat())


def hour_band_of(ts_ms) -> str:
    h = (int(ts_ms) % MS_PER_DAY) // 3_600_000
    for name, lo, hi in HOUR_BANDS:
        if lo <= h < hi:
            return name
    return ""


# ===========================================================================
# プリント(清算 1 件)の読み込み
# ===========================================================================
class Prints:
    """全日のプリント(`ts` 昇順)。全列一致の重複は zip ごとに 1 件へ落とす。"""

    def __init__(self, ts, side, price, qty, print_id, raw_rows=0, uniq_rows=0,
                 n_files=0):
        ts_a = np.asarray(ts, dtype=np.int64)
        id_a = np.asarray(print_id, dtype=object)
        o = np.array(sorted(range(ts_a.size),
                            key=lambda i: (int(ts_a[i]), str(id_a[i]))), dtype=int)
        self.ts = ts_a[o]
        self.side = np.asarray(side, dtype=object)[o]
        self.price = np.asarray(price, dtype=float)[o]
        self.qty = np.asarray(qty, dtype=float)[o]
        self.print_id = id_a[o]
        self.sign = np.array([REACT_SIGN.get(s, NAN) for s in self.side.tolist()],
                             dtype=float)
        self.day = np.array([day_of_ms(t) for t in self.ts.tolist()], dtype=object)
        self.notional = self.qty * self.price
        self.n = int(self.ts.size)
        self.raw_rows = int(raw_rows)
        self.uniq_rows = int(uniq_rows)
        self.n_files = int(n_files)
        by_day: dict = defaultdict(list)
        for i, d in enumerate(self.day.tolist()):
            by_day[d].append(i)
        self.by_day = {d: np.array(v, dtype=int) for d, v in by_day.items()}
        # 側ごとの `ts`(d と次の清算を数えるための索引)
        self.ts_of_side = {}
        for s in ("SELL", "BUY"):
            m = self.side == s
            self.ts_of_side[s] = self.ts[m]

    def subset(self, idx) -> "Prints":
        idx = np.asarray(idx, dtype=int)
        return Prints(self.ts[idx], self.side[idx], self.price[idx],
                      self.qty[idx], self.print_id[idx])

    def density(self, ts, side, window_ms: int = DENSITY_WINDOW_MS) -> np.ndarray:
        """`[ts − window_ms, ts)` の**同じ側**のプリント数。"""
        ts = np.asarray(ts, dtype=np.int64)
        out = np.zeros(ts.size, dtype=float)
        for s in ("SELL", "BUY"):
            m = np.asarray(side, dtype=object) == s
            if not bool(m.any()):
                continue
            t = self.ts_of_side[s]
            hi = np.searchsorted(t, ts[m], side="left")
            lo = np.searchsorted(t, ts[m] - window_ms, side="left")
            out[m] = (hi - lo).astype(float)
        return out

    def next_same_side_gap_s(self, ts, side) -> np.ndarray:
        """`(ts, …)` の**同じ側**の次のプリントまでの秒。無ければ NaN。"""
        ts = np.asarray(ts, dtype=np.int64)
        out = np.full(ts.size, NAN)
        for s in ("SELL", "BUY"):
            m = np.asarray(side, dtype=object) == s
            if not bool(m.any()):
                continue
            t = self.ts_of_side[s]
            j = np.searchsorted(t, ts[m], side="right")
            ok = j < t.size
            v = np.full(int(m.sum()), NAN)
            if t.size:
                v[ok] = (t[np.clip(j, 0, max(t.size - 1, 0))][ok]
                         - ts[m][ok]) / 1000.0
            out[m] = v
        return out


def load_prints(liq_dir: Path) -> Prints:
    """`liquidationSnapshot/<SYMBOL>/` の日次 zip を全部読む(全列一致で 1 件)。"""
    liq_dir = Path(liq_dir)
    zips = sorted(liq_dir.glob(f"{base.SYMBOL}-liquidationSnapshot-*.zip"))
    if not zips:
        raise SystemExit(f"[止め] 清算の zip が 1 つも無い: {liq_dir}")
    ts_l, side_l, price_l, qty_l, id_l = [], [], [], [], []
    raw_rows = uniq_rows = 0
    for p in zips:
        day = p.name[-14:-4]
        with zipfile.ZipFile(p) as zf:
            names = [n for n in zf.namelist() if n.endswith(".csv")]
            with zf.open(names[0]) as fh:
                rd = csv.reader(io.TextIOWrapper(fh, encoding="utf-8"))
                head = next(rd, None)
                rows = [tuple(r) for r in rd if r]
        if head is not None and head[0] != "time":
            rows = [tuple(head)] + rows
        raw_rows += len(rows)
        seen: set = set()
        kept = []
        for r in rows:
            if r in seen:
                continue
            seen.add(r)
            kept.append(r)
        uniq_rows += len(kept)
        for i, r in enumerate(kept):
            ts_l.append(int(r[0]))
            side_l.append(str(r[1]))
            price_l.append(float(r[6]))     # average_price(実約定 VWAP)
            qty_l.append(float(r[9]))       # accumulated_fill_quantity
            id_l.append(f"{day}_{i:05d}")
    return Prints(ts_l, side_l, price_l, qty_l, id_l, raw_rows, uniq_rows,
                  len(zips))


# ===========================================================================
# 約定の読み込み(その日 ± 必要分。数量と taker の向きも持つ)
# ===========================================================================
def load_day_trades(data_root: Path, day: str, cache: dict):
    if day in cache:
        return cache[day]
    p = base.agg_path(Path(data_root), day)
    cache[day] = (oid.load_agg_trades_with_maker(p) if p.exists() else None)
    return cache[day]


def load_window5(data_root: Path, day: str, cache: dict, back_ms: int,
                 fwd_ms: int):
    """[day 00:00 − back, day 24:00 + fwd] の約定(時刻・価格・数量)と欠けた日。"""
    lo = day_start_ms(day) - back_ms
    hi = day_start_ms(day) + MS_PER_DAY + fwd_ms
    d_lo = day_of_ms(lo)
    d_hi = day_of_ms(hi)
    need = [d_lo]
    while need[-1] < d_hi:
        need.append((_dt.date.fromisoformat(need[-1])
                     + _dt.timedelta(days=1)).isoformat())
    parts, missing = [], []
    for d in need:
        v = load_day_trades(data_root, d, cache)
        if v is None:
            missing.append(d)
        else:
            parts.append(v)
    for k in [k for k in cache if k < d_lo]:
        del cache[k]
    if parts:
        times = np.concatenate([x[0] for x in parts])
        prices = np.concatenate([x[1] for x in parts])
        qtys = np.concatenate([x[2] for x in parts])
        if not bool(np.all(times[1:] >= times[:-1])):
            o = np.argsort(times, kind="stable")
            times, prices, qtys = times[o], prices[o], qtys[o]
        m = (times >= lo) & (times <= hi)
        times, prices, qtys = times[m], prices[m], qtys[m]
    else:
        times = np.zeros(0, dtype=np.int64)
        prices = np.zeros(0)
        qtys = np.zeros(0)
    return times, prices, qtys, missing, need


def build_oi_context(data_root: Path, metrics_root: Path, day: str,
                     trade_cache: dict, metrics_cache: dict,
                     bucket_cache: dict | None = None):
    """`implied_leverage` のための ΔOI の桶(1 周目 `o3c_reaction` と同じ手順)。"""
    need = base.days_needed(day, W_HOURS)
    bucket_cache = {} if bucket_cache is None else bucket_cache
    lookup: dict = {}
    for d in need:
        if d not in bucket_cache:
            v = load_day_trades(data_root, d, trade_cache)
            bucket_cache[d] = (None if v is None
                               else oid.bucket_trade_stats(d, v[0], v[1], v[2], v[3]))
        bs = bucket_cache[d]
        if bs is None:
            continue
        for k in range(int(oid.BUCKETS_PER_DAY)):
            lookup[int(bs["start_ms"][k])] = (
                float(bs["vwap"][k]), float(bs["buy_share"][k]),
                float(bs["vol"][k]), int(bs["n"][k]),
                float(bs["vwap_buy"][k]), float(bs["vwap_sell"][k]))
    mdays, missing = [], []
    for d in need:
        if d not in metrics_cache:
            p = oid.metrics_path(Path(metrics_root), d)
            metrics_cache[d] = oid.load_metrics(p) if p.exists() else None
        if metrics_cache[d] is None:
            missing.append(d)
        else:
            mdays.append(metrics_cache[d])
    for k in [k for k in metrics_cache if k < need[0]]:
        del metrics_cache[k]
    for k in [k for k in bucket_cache if k < need[0]]:
        del bucket_cache[k]
    buckets = oid.build_delta_buckets(mdays, lookup)
    cov = oid.coverage_start_ms(buckets["t_all"])
    return buckets, cov, missing


# ===========================================================================
# 層の列(**t₀ 以前のデータだけで作る**。設計の用語表)
# ===========================================================================
def compute_layers(times, prices, qtys, pr_ts, pr_side, pr_price, sel,
                   buckets=None, cov=None, step=None, window_ms=None) -> dict:
    """`sel` のプリントの層の列を返す。**`ts` より後の約定・清算は一切参照しない**
    (例外は `k` と `p₀` で、これは `at_or_after(ts)` = 起点そのもの)。

    引数はすべて配列(テストが切り詰めた入力を渡せるようにしてある)。
    """
    times = np.asarray(times, dtype=np.int64)
    prices = np.asarray(prices, dtype=float)
    pr_ts = np.asarray(pr_ts, dtype=np.int64)
    pr_side = np.asarray(pr_side, dtype=object)
    pr_price = np.asarray(pr_price, dtype=float)
    sel = np.asarray(sel, dtype=int)
    ts = pr_ts[sel]
    side = pr_side[sel]
    sign = np.array([REACT_SIGN.get(s, NAN) for s in side.tolist()], dtype=float)
    out: dict = {"ts": ts, "side": side, "sign": sign}

    i0, ok0 = idx_at_or_after(times, ts, STALENESS_MS)
    out["ok_p0"] = ok0
    out["t0_ms"] = np.where(ok0, times[i0] if times.size else 0, -1).astype(np.int64)
    out["p0"] = np.where(ok0, prices[i0] if times.size else NAN, NAN)
    out["p0_lag_ms"] = np.where(ok0, (out["t0_ms"] - ts).astype(float), NAN)

    ip, okp = idx_at_or_before(times, ts - 1, STALENESS_MS)
    out["ok_pre"] = okp
    out["t_pre_ms"] = np.where(okp, times[ip] if times.size else 0, -1).astype(np.int64)
    out["p_pre"] = np.where(okp, prices[ip] if times.size else NAN, NAN)
    out["pre_lag_ms"] = np.where(okp, (ts - 1 - out["t_pre_ms"]).astype(float), NAN)

    with np.errstate(invalid="ignore", divide="ignore"):
        out["k"] = np.where(ok0 & okp & (out["p_pre"] > 0),
                            sign * (out["p0"] - out["p_pre"]) / out["p_pre"] * 1e4,
                            NAN)
    for T in T_MAIN:
        im, okm = idx_at_or_before(times, ts - T * 1000, STALENESS_MS)
        t_m = np.where(okm, times[im] if times.size else 0, -1).astype(np.int64)
        p_m = np.where(okm, prices[im] if times.size else NAN, NAN)
        out[f"m_lag_ms_{T}"] = np.where(okm, (ts - T * 1000 - t_m).astype(float), NAN)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[f"m_{T}"] = np.where(okm & okp & (p_m > 0),
                                     sign * (out["p_pre"] - p_m) / p_m * 1e4, NAN)

    # d(直前 5 分の同じ側のプリント数)。`ts` より前だけを数える。
    dens = np.zeros(ts.size, dtype=float)
    for s in ("SELL", "BUY"):
        msk = side == s
        if not bool(msk.any()):
            continue
        t_all = np.sort(pr_ts[pr_side == s])
        hi = np.searchsorted(t_all, ts[msk], side="left")
        lo = np.searchsorted(t_all, ts[msk] - DENSITY_WINDOW_MS, side="left")
        dens[msk] = (hi - lo).astype(float)
    out["d"] = dens

    # 属性(1 周目 `o3c_reaction` の定義、W = 8 時間。窓は [ts − W, ts) = 過去だけ)
    n = int(ts.size)
    out["bin_pct"] = np.full(n, NAN)
    out["dist_node_bp"] = np.full(n, NAN)
    out["implied_leverage"] = np.full(n, NAN)
    out["oi_covered"] = np.zeros(n, dtype=float)
    if step is None or window_ms is None or times.size == 0 or n == 0:
        return out
    order = np.argsort(ts, kind="stable")
    events = [{"profile_ts_ms": int(ts[i]), "p_liq": float(pr_price[sel[i]])}
              for i in order.tolist()]
    cols, _note = rx.profile_columns(events, times, prices,
                                     np.asarray(qtys, dtype=float),
                                     int(window_ms), float(step))
    for pos, i in enumerate(order.tolist()):
        out["bin_pct"][i] = cols[pos].get("bin_pct", NAN)
        out["dist_node_bp"][i] = cols[pos].get("dist_node_bp", NAN)
    if buckets is None or np.asarray(buckets["t_all"]).size == 0:
        return out
    # **被覆の判定を `ts` より前だけにする**(1 周目の `coverage_start_ms` は窓じゅうの
    # metrics の**最後**から遡るので `ts` より後の行を見る = この段の約束を破る)。
    # 代わりに「`ts` 以前の最後の metrics 行が属する 5 分連続の区間の先頭」を
    # プリントごとに求め、1 周目と同じ式 `ts − W >= cov − 5 分` で判定する。
    cov_i = covered_before(buckets["t_all"], ts, int(window_ms))
    oi_rows, oi_idx = [], []
    for pos, i in enumerate(order.tolist()):
        p_liq = float(pr_price[sel[i]])
        p0p = cols[pos].get("p0", NAN)
        if not (np.isfinite(p_liq) and p_liq > 0 and np.isfinite(p0p) and p0p > 0):
            continue
        oi_rows.append({"time_ms": int(ts[i]), "p_liq": p_liq, "p0": float(p0p),
                        "side": str(side[i])})
        oi_idx.append(i)
    if oi_rows:
        # 1 周目の関門は `cov` を 1 つしか取らないので、ここでは**素通しの値**を渡し
        # (最初の metrics 行)、被覆はプリントごとに `cov_i` で掛ける。
        oi_cols, _unc = oid.oi_columns_for_rows(
            oi_rows, buckets, int(window_ms), float(step),
            int(np.asarray(buckets["t_all"])[0]), side_price="same")
        for pos, i in enumerate(oi_idx):
            if not bool(cov_i[i]):
                continue
            row = dict(oi_cols[pos])
            row["side"] = str(side[i])
            row["dist_vwap_bp"] = NAN
            row["dist_node_bp"] = out["dist_node_bp"][i]
            oid._apply_liqdir_and_leverage(row, MMR)
            v = row.get("implied_leverage", NAN)
            out["implied_leverage"][i] = float(v) if v is not None else NAN
            out["oi_covered"][i] = float(oi_cols[pos].get("oi_covered", 0))
    return out


def covered_before(t_all, ts, window_ms: int) -> np.ndarray:
    """`ts` ごとに「窓 [ts − W, ts] が建玉の被覆に入っているか」(**過去だけで判定**)。

    1 周目 `o3c_oi_distance.coverage_start_ms` は `t_all` の**末尾**から 5 分刻みで
    連続している区間の先頭を返す。この段は起点より後を見ないので、`ts` 以前の最後の
    metrics 行が属する区間の先頭を使う。判定の式は 1 周目と同じ
    (`ts − W < cov − 5 分` なら被覆の外)。
    """
    t_all = np.asarray(t_all, dtype=np.int64)
    ts = np.asarray(ts, dtype=np.int64)
    if t_all.size == 0:
        return np.zeros(ts.size, dtype=bool)
    brk = np.concatenate(([True], (t_all[1:] - t_all[:-1]) != oid.BUCKET_MS))
    idx = np.maximum.accumulate(np.where(brk, np.arange(t_all.size), 0))
    run_start = t_all[idx]
    j = np.searchsorted(t_all, ts, side="right") - 1
    ok = j >= 0
    cov = np.where(ok, run_start[np.clip(j, 0, t_all.size - 1)], 0).astype(np.int64)
    return ok & ((ts - window_ms) >= (cov - oid.BUCKET_MS))


def forward_moves(times, prices, ts, t0_ms, p0, ok0, sign) -> dict:
    """r(h)(`ts` 基準)と r_t0(h)(起点の約定の時刻 t₀ 基準)。"""
    times = np.asarray(times, dtype=np.int64)
    prices = np.asarray(prices, dtype=float)
    out: dict = {}
    for h in HORIZONS_SEC:
        for tag, anchor in (("r", np.asarray(ts, dtype=np.int64)),
                            ("r_t0", np.asarray(t0_ms, dtype=np.int64))):
            tgt = np.where(ok0, anchor + h * 1000, 0)
            ih, okh = idx_at_or_before(times, tgt, STALENESS_MS)
            okh = okh & ok0
            p_h = np.where(okh, prices[ih] if times.size else NAN, NAN)
            t_h = times[ih] if times.size else np.zeros(tgt.size, dtype=np.int64)
            with np.errstate(invalid="ignore", divide="ignore"):
                out[f"{tag}_{h}"] = np.where(okh & (np.asarray(p0) > 0),
                                             sign * (p_h - p0) / p0 * 1e4, NAN)
            if tag == "r":
                out[f"h_lag_ms_{h}"] = np.where(okh, (tgt - t_h).astype(float), NAN)
    return out


# ===========================================================================
# 束の位置(H0 の診断だけ。探索段 4 の束を使う)
# ===========================================================================
def bundle_positions(prints: Prints, bd) -> tuple:
    """プリントごとに 探索段 4 の束(gap 60)の 最初 / 途中 / 最後 を当てる。

    同じ側の束は時間で重ならないので、**側ごとに** `start_ms` で二分探索する。
    単発の束(`start_ms == end_ms`)のプリントは「最初」と「最後」の**両方**に数える
    (委任文【データ】。`bundle_pos_single` 列に 1 を立てる)。
    """
    pos = np.full(prints.n, POS_NONE, dtype=object)
    single = np.zeros(prints.n, dtype=float)
    bid = np.full(prints.n, "", dtype=object)
    for s in ("SELL", "BUY"):
        b = np.flatnonzero(bd.side == s)
        if b.size == 0:
            continue
        order = b[np.argsort(bd.start_ms[b], kind="stable")]
        st = bd.start_ms[order]
        en = bd.end_ms[order]
        ids = bd.cascade_id[order]
        pi = np.flatnonzero(prints.side == s)
        if pi.size == 0:
            continue
        j = np.searchsorted(st, prints.ts[pi], side="right") - 1
        for n_, i in enumerate(pi.tolist()):
            k = int(j[n_])
            if k < 0 or prints.ts[i] > en[k]:
                continue
            bid[i] = str(ids[k])
            at_start = bool(prints.ts[i] == st[k])
            at_end = bool(prints.ts[i] == en[k])
            if at_start and at_end:
                pos[i] = POS_LAST
                single[i] = 1.0
            elif at_end:
                pos[i] = POS_LAST
            elif at_start:
                pos[i] = POS_FIRST
            else:
                pos[i] = POS_MID
    return pos, single, bid


def position_mask(pos, single, want: str) -> np.ndarray:
    """単発の束は「最初」と「最後」の両方に数える。"""
    pos = np.asarray(pos, dtype=object)
    single = np.asarray(single, dtype=float)
    if want == POS_FIRST:
        return (pos == POS_FIRST) | (single == 1.0)
    if want == POS_LAST:
        return pos == POS_LAST
    return pos == POS_MID


# ===========================================================================
# 行の書き出し
# ===========================================================================
def _blank_row() -> dict:
    return {c: "" for c in CHUNK_HEADER}


def _num(d: dict, key: str, v, nd: int = 6) -> None:
    d[key] = _fmt(v, nd)


def print_rows(day: str, prints: Prints, sel, lay: dict, fwd: dict,
               pos, single, bid, nxt) -> list:
    rows = []
    for j, i in enumerate(np.asarray(sel, dtype=int).tolist()):
        d = _blank_row()
        d["kind"] = KIND_PRINT
        d["print_id"] = str(prints.print_id[i])
        d["day"] = day
        d["side"] = str(prints.side[i])
        d["ts_ms"] = int(prints.ts[i])
        if bool(lay["ok_p0"][j]):
            d["t0_ms"] = int(lay["t0_ms"][j])
            _num(d, "p0", lay["p0"][j], 4)
            d["p0_lag_ms"] = int(lay["p0_lag_ms"][j])
        if bool(lay["ok_pre"][j]):
            d["t_pre_ms"] = int(lay["t_pre_ms"][j])
            _num(d, "p_pre", lay["p_pre"][j], 4)
            d["pre_lag_ms"] = int(lay["pre_lag_ms"][j])
        _num(d, "k", lay["k"][j])
        d["d"] = int(lay["d"][j])
        d["bundle_id"] = str(bid[i])
        d["bundle_pos"] = str(pos[i])
        d["bundle_pos_single"] = int(single[i])
        _num(d, "notional", prints.notional[i], 4)
        d["hour_band"] = hour_band_of(prints.ts[i])
        for T in T_MAIN:
            _num(d, f"m_{T}", lay[f"m_{T}"][j])
            v = lay[f"m_lag_ms_{T}"][j]
            d[f"m_lag_ms_{T}"] = "" if not math.isfinite(v) else int(v)
        for h in HORIZONS_SEC:
            _num(d, f"r_{h}", fwd[f"r_{h}"][j])
            _num(d, f"r_t0_{h}", fwd[f"r_t0_{h}"][j])
            v = fwd[f"h_lag_ms_{h}"][j]
            d[f"h_lag_ms_{h}"] = "" if not math.isfinite(v) else int(v)
        _num(d, "next_same_side_gap_s", nxt[j], 3)
        _num(d, "bin_pct", lay["bin_pct"][j], 4)
        _num(d, "dist_node_bp", lay["dist_node_bp"][j], 4)
        _num(d, "implied_leverage", lay["implied_leverage"][j], 4)
        d["oi_covered"] = int(lay["oi_covered"][j])
        rows.append([d[c] for c in CHUNK_HEADER])
    return rows


# ===========================================================================
# 段 1: プリント + 対照 (b) の行
# ===========================================================================
def stage1_day(day: str, prints: Prints, sel, times, prices, qtys,
               uniform_ms, buckets, cov, pos, single, bid) -> list:
    out: list = []
    if len(sel):
        lay = compute_layers(times, prices, qtys, prints.ts, prints.side,
                             prints.price, sel, buckets=buckets, cov=cov,
                             step=base.log_step(BIN_PCT),
                             window_ms=int(W_HOURS * 3600 * 1000))
        fwd = forward_moves(times, prices, lay["ts"], lay["t0_ms"], lay["p0"],
                            lay["ok_p0"], lay["sign"])
        nxt = prints.next_same_side_gap_s(lay["ts"], lay["side"])
        out += print_rows(day, prints, sel, lay, fwd, pos, single, bid, nxt)
    if uniform_ms.size:
        ones = np.ones(uniform_ms.size)
        i0, ok0 = idx_at_or_after(times, uniform_ms, STALENESS_MS)
        t0 = np.where(ok0, times[i0] if times.size else 0, -1).astype(np.int64)
        p0 = np.where(ok0, prices[i0] if times.size else NAN, NAN)
        fwd = forward_moves(times, prices, uniform_ms, t0, p0, ok0, ones)
        for j in range(uniform_ms.size):
            d = _blank_row()
            d["kind"] = KIND_BI
            d["print_id"] = f"bi_{day}_{j:03d}"
            d["day"] = day
            d["ts_ms"] = int(uniform_ms[j])
            if bool(ok0[j]):
                d["t0_ms"] = int(t0[j])
                _num(d, "p0", p0[j], 4)
                d["p0_lag_ms"] = int(t0[j] - uniform_ms[j])
            for h in HORIZONS_SEC:
                _num(d, f"r_{h}", fwd[f"r_{h}"][j])
                _num(d, f"r_t0_{h}", fwd[f"r_t0_{h}"][j])
            out.append([d[c] for c in CHUNK_HEADER])
    return out


# ===========================================================================
# 段 2: 対照 (c') 直前の値動き合わせ(設計 §4)
# ===========================================================================
def _block(allowed: np.ndarray, a: int, b: int, t_ms: int, d0: int) -> None:
    """区間 [a, b] と [t − T 秒, t + 900 秒] が重なる候補 t を落とす。"""
    klo = max(0, -(-(a - CTRL_WINDOW_MS - d0) // GRID_STEP_MS))
    khi = min(GRID_N - 1, (b + t_ms - d0) // GRID_STEP_MS)
    if khi >= klo:
        allowed[int(klo):int(khi) + 1] = False


def select_control_c(day: str, prints: Prints, sel, T: int, cuts: np.ndarray,
                     m_all: np.ndarray, times, prices, taken: dict) -> tuple:
    """その日のプリントに対照 (c') を 1 つずつ当てる(`ts` の順、置換なし)。"""
    note = {"n_prints": 0, "n_taken": 0}
    sel = np.asarray(sel, dtype=int)
    if sel.size == 0:
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
    p_ge = np.where(ok_ge, prices[_i_ge] if times.size else NAN, NAN)
    with np.errstate(invalid="ignore", divide="ignore"):
        raw = np.where(ok_gp & ok_gt & (p_gt > 0), (p_gp - p_gt) / p_gt * 1e4, NAN)
        raw_k = np.where(ok_ge & ok_gp & (p_gp > 0),
                         (p_ge - p_gp) / p_gp * 1e4, NAN)
    allowed0 = ok_ge & ok_gp & ok_gt & np.isfinite(raw)

    # 設計 §4: 区間 [t − T 秒, t + 900 秒] に**どの側のプリントも無い**候補だけ残す
    lo_b = d0 - t_ms - 1
    hi_b = grid_hi + CTRL_WINDOW_MS + 1
    a0 = int(np.searchsorted(prints.ts, lo_b, side="left"))
    a1 = int(np.searchsorted(prints.ts, hi_b, side="right"))
    for a in prints.ts[a0:a1].tolist():
        _block(allowed0, a, a, t_ms, d0)
    prev_day = (_dt.date.fromisoformat(day) - _dt.timedelta(days=1)).isoformat()

    rows: list = []
    for i in sel.tolist():
        m_p = float(m_all[i])
        note["n_prints"] += 1
        if not math.isfinite(m_p):
            continue
        band_p = int(band_of_m(m_p, cuts))
        allowed = allowed0.copy()
        for dd in (prev_day, day):
            for a, b in taken.get(dd, ()):
                _block(allowed, a, b, t_ms, d0)
        cand = np.flatnonzero(allowed)
        if cand.size == 0:
            continue
        s = prints.sign[i]
        c = s * raw[cand]
        same = band_of_m(c, cuts) == band_p
        if not bool(same.any()):
            continue
        diff = np.where(same, np.abs(c - m_p), np.inf)
        j = int(np.argmin(diff))
        t = int(grid[cand[j]])
        taken.setdefault(day, []).append((t - t_ms, t + CTRL_WINDOW_MS))
        note["n_taken"] += 1
        arr = np.array([t], dtype=np.int64)
        i0, ok0 = idx_at_or_after(times, arr, STALENESS_MS)
        t0 = np.where(ok0, times[i0] if times.size else 0, -1).astype(np.int64)
        p0 = np.where(ok0, prices[i0] if times.size else NAN, NAN)
        fwd = forward_moves(times, prices, t0, t0, p0, ok0, np.array([s]))
        d = _blank_row()
        d["kind"] = KIND_C
        d["print_id"] = str(prints.print_id[i])
        d["day"] = day
        d["side"] = str(prints.side[i])
        d["ctrl_T"] = T
        d["ts_ms"] = t
        d["matched_print_id"] = str(prints.print_id[i])
        d["ctrl_t_ms"] = t
        if bool(ok0[0]):
            d["t0_ms"] = int(t0[0])
            _num(d, "p0", p0[0], 4)
            d["p0_lag_ms"] = int(t0[0] - t)
        _num(d, f"m_{T}", float(c[j]))
        _num(d, "c_t", float(c[j]))
        _num(d, "k_ctrl", float(s * raw_k[cand[j]]))
        d["hour_band"] = hour_band_of(t)
        for h in HORIZONS_SEC:
            _num(d, f"r_{h}", fwd[f"r_{h}"][0])
            _num(d, f"r_t0_{h}", fwd[f"r_t0_{h}"][0])
        rows.append([d[c2] for c2 in CHUNK_HEADER])
    return rows, note


# ===========================================================================
# 走行(chunk で書き、再開できる)
# ===========================================================================
def run_stage1(out_dir: Path, days: list, prints: Prints, uniform_by_day: dict,
               data_root: Path, metrics_root: Path, pos, single, bid,
               progress_every: int, with_oi: bool = True) -> dict:
    work = out_dir / "chunks1"
    work.mkdir(parents=True, exist_ok=True)
    cache: dict = {}
    mcache: dict = {}
    bcache: dict = {}
    missing_agg: set = set()
    missing_metrics: set = set()
    back = int(W_HOURS * 3600 * 1000) + STALENESS_MS
    fwd = max(HORIZONS_SEC) * 1000 + STALENESS_MS
    t0 = time.time()
    for n_done, day in enumerate(days, start=1):
        cp = work / f"{day}.csv.gz"
        if cp.exists():
            continue
        times, prices, qtys, miss, _need = load_window5(data_root, day, cache,
                                                        back, fwd)
        missing_agg |= set(miss)
        if with_oi:
            buckets, cov, mmiss = build_oi_context(data_root, metrics_root, day,
                                                   cache, mcache, bcache)
            missing_metrics |= set(mmiss)
        else:
            buckets, cov = None, None
        sel = prints.by_day.get(day, np.zeros(0, dtype=int))
        rows = stage1_day(day, prints, sel, times, prices, qtys,
                          uniform_by_day.get(day, np.zeros(0, dtype=np.int64)),
                          buckets, cov, pos, single, bid)
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


def read_m(out_dir: Path, days: list, prints: Prints) -> dict:
    """段 1 の chunk からプリントごとの m(T)(並びは `Prints` の並び)。"""
    pos_of = {c: i for i, c in enumerate(prints.print_id.tolist())}
    mm = {T: np.full(prints.n, NAN) for T in T_MAIN}
    for day in days:
        cp = out_dir / "chunks1" / f"{day}.csv.gz"
        if not cp.exists():
            continue
        with gzip.open(cp, "rt", newline="") as fh:
            for r in csv.DictReader(fh):
                if r["kind"] != KIND_PRINT:
                    continue
                i = pos_of.get(r["print_id"])
                if i is None:
                    continue
                for T in T_MAIN:
                    mm[T][i] = _f(r[f"m_{T}"])
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


def run_stage2(out_dir: Path, days: list, prints: Prints, m_by_T: dict,
               data_root: Path, progress_every: int) -> dict:
    work = out_dir / "chunks2"
    work.mkdir(parents=True, exist_ok=True)
    cuts = {T: band_cuts_m(m_by_T[T]) for T in T_MAIN}
    cache: dict = {}
    notes = {T: {"n_prints": 0, "n_taken": 0} for T in T_MAIN}
    taken: dict = {T: {} for T in T_MAIN}
    back = max(T_MAIN) * 1000 + STALENESS_MS
    fwd = CTRL_WINDOW_MS + max(HORIZONS_SEC) * 1000 + STALENESS_MS
    t0 = time.time()
    for n_done, day in enumerate(days, start=1):
        cp = work / f"{day}.csv.gz"
        prev_day = (_dt.date.fromisoformat(day) - _dt.timedelta(days=1)).isoformat()
        if cp.exists():
            for T in T_MAIN:
                taken[T] = {day: _taken_from_chunk(cp, T)}
            continue
        times, prices, _q, _miss, _need = load_window5(data_root, day, cache,
                                                       back, fwd)
        sel = prints.by_day.get(day, np.zeros(0, dtype=int))
        rows = []
        for T in T_MAIN:
            r, note = select_control_c(day, prints, sel, T, cuts[T], m_by_T[T],
                                       times, prices, taken[T])
            rows += r
            notes[T]["n_prints"] += note["n_prints"]
            notes[T]["n_taken"] += note["n_taken"]
            taken[T] = {k: v for k, v in taken[T].items() if k in (prev_day, day)}
        tmp = work / f".{day}.part"
        with gz_open_w(tmp) as fh:
            w = csv.writer(fh)
            w.writerow(CHUNK_HEADER)
            w.writerows(rows)
        tmp.replace(cp)
        if n_done % progress_every == 0:
            print(f"  段2 {n_done}/{len(days)} 日 ({day}) 経過 "
                  f"{time.time() - t0:.0f}s", flush=True)
    return {"cuts": {str(T): [float(x) for x in cuts[T]] for T in T_MAIN},
            "notes": {str(T): notes[T] for T in T_MAIN}}


def concat_rows(out_dir: Path, days: list) -> Path:
    p = out_dir / "rows_prints.csv.gz"
    fh = gz_open_w(Path(str(p) + ".part"))
    w = csv.writer(fh)
    w.writerow(ROW_COLUMNS)
    n = 0
    for day in days:
        for sub in ("chunks1", "chunks2"):
            cp = out_dir / sub / f"{day}.csv.gz"
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


def drop_chunks(out_dir: Path) -> int:
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
class Rows:
    """`rows_prints.csv.gz` を kind ごとに開いたもの。"""

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
            for c in ("print_id", "day", "side", "bundle_id", "bundle_pos",
                      "hour_band", "matched_print_id"):
                b[c] = np.array(cols[c], dtype=object)[m]
            for c in NUMERIC_COLS:
                b[c] = np.array([_f(x) for x in cols[c]], dtype=float)[m]
            b["_n"] = int(m.sum())
            self.blk[k] = b


def r_stats(blk: dict, mask: np.ndarray, h: int, col: str = R_MAIN_COL) -> dict:
    """後の動きの統計。既定の列は **t₀ 基準**(設計の訂正 2026-09-20)。"""
    v = blk[f"{col}_{h}"][mask]
    days = blk["day"][mask]
    mean, se, naive, n, g = mean_se_cluster(v, days)
    ratio = se / naive if (math.isfinite(se) and math.isfinite(naive)
                           and naive > 0) else NAN
    q = quantiles(v, [25, 50, 75])
    fin = v[np.isfinite(v)]
    return {"n": n, "含む日数": g, "r 平均(bp)": mean,
            "r 日クラスタ SE": se, "r naive SE": naive,
            "日クラスタ/naive": ratio, "r 日等重み平均": day_equal_weight_mean(v, days),
            "r 中央値": q[1], "r p25": q[0], "r p75": q[2],
            "r < 0 の割合": float((fin < 0).mean()) if fin.size else NAN,
            "r < 0 の母数": int(fin.size)}


def next_liq(blk: dict, mask: np.ndarray) -> dict:
    v = blk["next_same_side_gap_s"][mask]
    n_tot = int(mask.sum())
    out: dict = {}
    for sec in NEXT_SEC:
        hit = np.isfinite(v) & (v <= sec)
        out[f"同じ側の次の清算 {sec} 秒以内の割合"] = (
            float(hit.sum() / n_tot) if n_tot else NAN)
        out[f"同じ側の次の清算 {sec} 秒以内の母数"] = n_tot
    out["同じ側の次の清算が無い(この期間の最後)"] = int((~np.isfinite(v)).sum())
    return out


def mean_median(v: np.ndarray, mask: np.ndarray, label: str) -> dict:
    x = v[mask]
    fin = x[np.isfinite(x)]
    return {f"{label} 平均": float(fin.mean()) if fin.size else NAN,
            f"{label} 中央値": float(np.median(fin)) if fin.size else NAN}


def m_band_masks(blk: dict, T: int, cuts: np.ndarray) -> list:
    bands = band_of_m(blk[f"m_{T}"], cuts)
    out = []
    for k in range(1, N_BANDS + 1):
        lo, hi = band_bounds(cuts, k)
        out.append((k, lo, hi, bands == k))
    return out


def m_tertile_masks(blk: dict, T: int, lo: float, hi: float) -> list:
    v = blk[f"m_{T}"]
    return [(label, tertile_mask(v, lo, hi, q)) for q, label in TERTILE_LABELS]


def k_group_masks(blk: dict, cuts: tuple) -> list:
    k = blk["k"]
    lo, hi = cuts
    out = [("K0(k ≤ 0)", np.isfinite(k) & (k <= 0))]
    pos = np.isfinite(k) & (k > 0)
    for q, label in TERTILE_LABELS:
        out.append((f"K+{q}({label}、k > 0)",
                    pos & tertile_mask(k, lo, hi, q)))
    return out


def d_group_masks(blk: dict) -> list:
    d = blk["d"]
    return [("d = 0", d == 0), ("d = 1〜2", (d >= 1) & (d <= 2)),
            ("d ≥ 3", d >= 3)]


# ---------------------------------------------------------------------------
# H0 自己点検
# ---------------------------------------------------------------------------
H0_COLS = ["区分", "種", "T(秒)", "量", "群", "n", "母数", "割合",
           "p10", "p25", "p50", "p75", "p90", "p99", "最大",
           "平均", "中央値", "r(t₀ 基準・主)平均", "r(ts 基準・併記)平均",
           "2 つの起点で値が違う行", "m の中央値", "k の中央値",
           "r(60) の中央値", "相関"]


def _h0(**kw) -> dict:
    row = {c: DASH for c in H0_COLS}
    row.update(kw)
    return row


def _q(v, row: dict) -> dict:
    p = quantiles(v, [10, 25, 50, 75, 90, 99, 100])
    row.update({"p10": p[0], "p25": p[1], "p50": p[2], "p75": p[3],
                "p90": p[4], "p99": p[5], "最大": p[6]})
    return row


def make_h0(rows: Rows, cuts: dict, ctrl_notes: dict, prints: Prints,
            n_days: int, per_day_ctrl: dict) -> list:
    blk = rows.blk[KIND_PRINT]
    ctrl = rows.blk[KIND_C]
    n_all = blk["_n"]
    out: list = []

    # --- (a) プリント数 ------------------------------------------------------
    out.append(_h0(区分="プリント数", 種=KIND_LABEL[KIND_PRINT],
                   量="重複除去の前(生の行、全 zip)", 群=f"{prints.n_files} 日",
                   n=prints.raw_rows, 母数=prints.raw_rows))
    out.append(_h0(区分="プリント数", 種=KIND_LABEL[KIND_PRINT],
                   量="重複除去の後(全列一致で 1 件)", 群=f"{prints.n_files} 日",
                   n=prints.uniq_rows, 母数=prints.raw_rows,
                   割合=prints.uniq_rows / prints.raw_rows if prints.raw_rows else NAN))
    out.append(_h0(区分="プリント数", 種=KIND_LABEL[KIND_PRINT],
                   量="この単位で測ったプリント", 群=f"{n_days} 日",
                   n=n_all, 母数=prints.uniq_rows,
                   割合=n_all / prints.uniq_rows if prints.uniq_rows else NAN))

    # --- (a) 遅れ ------------------------------------------------------------
    out.append(_q(blk["p0_lag_ms"],
                  _h0(区分="遅れ", 種=KIND_LABEL[KIND_PRINT],
                      量="起点の遅れ p₀ − ts(ms)", 群="全体",
                      n=int(np.isfinite(blk["p0_lag_ms"]).sum()), 母数=n_all)))
    out.append(_q(blk["pre_lag_ms"],
                  _h0(区分="遅れ", 種=KIND_LABEL[KIND_PRINT],
                      量="直前の遅れ(ts − 1)− 直前の約定(ms)", 群="全体",
                      n=int(np.isfinite(blk["pre_lag_ms"]).sum()), 母数=n_all)))
    for T in T_MAIN:
        v = blk[f"m_lag_ms_{T}"]
        out.append(_q(v, _h0(区分="遅れ", 種=KIND_LABEL[KIND_PRINT],
                             **{"T(秒)": T}, 量="m の窓の遅れ(ms)", 群="全体",
                             n=int(np.isfinite(v).sum()), 母数=n_all)))
    for h in HORIZONS_SEC:
        v = blk[f"h_lag_ms_{h}"]
        out.append(_q(v, _h0(区分="遅れ", 種=KIND_LABEL[KIND_PRINT],
                             量=f"h 後の遅れ(ms) h={h}", 群="全体",
                             n=int(np.isfinite(v).sum()), 母数=n_all)))

    # --- (a) m・k・d の分布 ---------------------------------------------------
    for T in T_MAIN:
        v = blk[f"m_{T}"]
        fin = v[np.isfinite(v)]
        row = _h0(区分="m の分布", 種=KIND_LABEL[KIND_PRINT], **{"T(秒)": T},
                  量="m(T)(bp)と m ≤ 0 の割合", 群="全体",
                  n=int(fin.size), 母数=n_all,
                  割合=float((fin <= 0).mean()) if fin.size else NAN)
        row["平均"] = float(fin.mean()) if fin.size else NAN
        row["中央値"] = float(np.median(fin)) if fin.size else NAN
        out.append(_q(v, row))
        bad = ~np.isfinite(v)
        out.append(_h0(区分="m の分布", 種=KIND_LABEL[KIND_PRINT], **{"T(秒)": T},
                       量="m が引けないプリント", 群="全体",
                       n=int(bad.sum()), 母数=n_all,
                       割合=float(bad.mean()) if n_all else NAN))
    kk = blk["k"]
    fin = kk[np.isfinite(kk)]
    row = _h0(区分="k の分布", 種=KIND_LABEL[KIND_PRINT], 量="k(bp)", 群="全体",
              n=int(fin.size), 母数=n_all)
    row["平均"] = float(fin.mean()) if fin.size else NAN
    row["中央値"] = float(np.median(fin)) if fin.size else NAN
    out.append(_q(kk, row))
    z = np.isfinite(kk) & (kk == 0.0)
    out.append(_h0(区分="k の分布", 種=KIND_LABEL[KIND_PRINT],
                   量="k = 0 ちょうどのプリント", 群="全体", n=int(z.sum()),
                   母数=int(np.isfinite(kk).sum()),
                   割合=float(z.sum() / max(int(np.isfinite(kk).sum()), 1))))
    neg = np.isfinite(kk) & (kk < 0)
    out.append(_h0(区分="k の分布", 種=KIND_LABEL[KIND_PRINT],
                   量="k < 0 のプリント", 群="全体", n=int(neg.sum()),
                   母数=int(np.isfinite(kk).sum()),
                   割合=float(neg.sum() / max(int(np.isfinite(kk).sum()), 1))))
    out.append(_h0(区分="k の分布", 種=KIND_LABEL[KIND_PRINT],
                   量="k が引けないプリント", 群="全体",
                   n=int((~np.isfinite(kk)).sum()), 母数=n_all,
                   割合=float((~np.isfinite(kk)).mean()) if n_all else NAN))
    dd = blk["d"]
    row = _h0(区分="d の分布", 種=KIND_LABEL[KIND_PRINT], 量="d(件)", 群="全体",
              n=int(np.isfinite(dd).sum()), 母数=n_all)
    row["平均"] = float(dd[np.isfinite(dd)].mean()) if n_all else NAN
    row["中央値"] = float(np.median(dd[np.isfinite(dd)])) if n_all else NAN
    out.append(_q(dd, row))
    for label, msk in d_group_masks(blk):
        out.append(_h0(区分="d の分布", 種=KIND_LABEL[KIND_PRINT],
                       量="d の群ごとのプリント数", 群=label, n=int(msk.sum()),
                       母数=n_all,
                       割合=float(msk.mean()) if n_all else NAN))

    # --- (a) 欠測 -------------------------------------------------------------
    for h in HORIZONS_SEC:
        bad = ~np.isfinite(blk[f"{R_MAIN_COL}_{h}"])
        out.append(_h0(区分="欠測", 種=KIND_LABEL[KIND_PRINT],
                       量=f"r(h)(t₀ 基準・主)が引けないプリント h={h}", 群="全体",
                       n=int(bad.sum()), 母数=n_all,
                       割合=float(bad.mean()) if n_all else NAN))
    for name, col in (("bin_pct", "bin_pct"), ("dist_node_bp", "dist_node_bp"),
                      ("implied_leverage", "implied_leverage")):
        bad = ~np.isfinite(blk[col])
        out.append(_h0(区分="欠測", 種=KIND_LABEL[KIND_PRINT],
                       量=f"付け直した属性が作れないプリント({name})", 群="全体",
                       n=int(bad.sum()), 母数=n_all,
                       割合=float(bad.mean()) if n_all else NAN))
    out.append(_h0(区分="欠測", 種=KIND_LABEL[KIND_PRINT],
                   量="探索段 4 の束(gap 60)に入らないプリント", 群="全体",
                   n=int((blk["bundle_pos"] == POS_NONE).sum()), 母数=n_all,
                   割合=float((blk["bundle_pos"] == POS_NONE).mean())
                   if n_all else NAN))

    # --- (b) 診断: 束の位置 × h 7(21 行)-------------------------------------
    for want in POSITIONS:
        msk = position_mask(blk["bundle_pos"], blk["bundle_pos_single"], want)
        for h in HORIZONS_SEC:
            v_ts = blk[f"{R_ALT_COL}_{h}"][msk]
            v_t0 = blk[f"{R_MAIN_COL}_{h}"][msk]
            both = np.isfinite(v_ts) & np.isfinite(v_t0)
            row = _h0(区分="診断(束の位置)", 種=KIND_LABEL[KIND_PRINT],
                      量=f"r(h) 平均(bp) h={h}", 群=want,
                      n=int(np.isfinite(v_t0).sum()), 母数=int(msk.sum()))
            row["r(t₀ 基準・主)平均"] = (float(v_t0[np.isfinite(v_t0)].mean())
                                  if np.isfinite(v_t0).any() else NAN)
            row["r(ts 基準・併記)平均"] = (float(v_ts[np.isfinite(v_ts)].mean())
                                    if np.isfinite(v_ts).any() else NAN)
            row["2 つの起点で値が違う行"] = int((both & (v_ts != v_t0)).sum())
            row["中央値"] = (float(np.median(v_t0[np.isfinite(v_t0)]))
                          if np.isfinite(v_t0).any() else NAN)
            out.append(row)

    # --- (b) 起点の取り方の突き合わせ(全プリント)-----------------------------
    for h in HORIZONS_SEC:
        v_ts = blk[f"{R_ALT_COL}_{h}"]
        v_t0 = blk[f"{R_MAIN_COL}_{h}"]
        both = np.isfinite(v_ts) & np.isfinite(v_t0)
        row = _h0(区分="起点の取り方", 種=KIND_LABEL[KIND_PRINT],
                  量=f"r(h) 平均(bp) h={h}", 群="全プリント",
                  n=int(both.sum()), 母数=n_all)
        row["r(t₀ 基準・主)平均"] = (float(v_t0[np.isfinite(v_t0)].mean())
                              if np.isfinite(v_t0).any() else NAN)
        row["r(ts 基準・併記)平均"] = (float(v_ts[np.isfinite(v_ts)].mean())
                                if np.isfinite(v_ts).any() else NAN)
        row["2 つの起点で値が違う行"] = int((both & (v_ts != v_t0)).sum())
        out.append(row)

    # --- (c) 対照 (c') --------------------------------------------------------
    m_by_id = {T: dict(zip(blk["print_id"].tolist(), blk[f"m_{T}"].tolist()))
               for T in T_MAIN}
    for T in T_MAIN:
        sel = ctrl["ctrl_T"] == T
        ct = ctrl["c_t"][sel]
        mb = np.array([m_by_id[T].get(c, NAN)
                       for c in ctrl["matched_print_id"][sel].tolist()],
                      dtype=float)
        diff = np.abs(ct - mb)
        n_p = ctrl_notes[T]["n_prints"]
        out.append(_q(diff, _h0(区分="対照 (c')", 種=KIND_LABEL[KIND_C],
                                **{"T(秒)": T}, 量="|c_t − m_p|(bp)",
                                群="取れたプリント",
                                n=int(np.isfinite(diff).sum()), 母数=n_p)))
        row = _h0(区分="対照 (c')", 種=KIND_LABEL[KIND_C], **{"T(秒)": T},
                  量="候補の区間の変位 c_t(bp)", 群="取れたプリント",
                  n=int(np.isfinite(ct).sum()), 母数=n_p)
        row["平均"] = float(ct[np.isfinite(ct)].mean()) if np.isfinite(ct).any() else NAN
        row["中央値"] = (float(np.median(ct[np.isfinite(ct)]))
                      if np.isfinite(ct).any() else NAN)
        out.append(row)
        kc = ctrl["k_ctrl"][sel]
        row = _h0(区分="対照 (c')", 種=KIND_LABEL[KIND_C], **{"T(秒)": T},
                  量="対照の掃き相当(候補時刻をまたぐ変位、bp)", 群="取れたプリント",
                  n=int(np.isfinite(kc).sum()), 母数=n_p)
        row["平均"] = float(kc[np.isfinite(kc)].mean()) if np.isfinite(kc).any() else NAN
        row["中央値"] = (float(np.median(kc[np.isfinite(kc)]))
                      if np.isfinite(kc).any() else NAN)
        out.append(row)
        taken_ids = set(ctrl["print_id"][sel].tolist())
        got = np.array([c in taken_ids for c in blk["print_id"].tolist()],
                       dtype=bool)
        for name, msk in (("全体", np.ones(n_all, dtype=bool)),
                          ("SELL", blk["side"] == "SELL"),
                          ("BUY", blk["side"] == "BUY")):
            miss = int((msk & ~got).sum())
            tot = int(msk.sum())
            out.append(_h0(区分="対照 (c')", 種=KIND_LABEL[KIND_C],
                           **{"T(秒)": T}, 量="対照 (c') が取れなかったプリント",
                           群=name, n=miss, 母数=tot,
                           割合=float(miss / tot) if tot else NAN))
        for k, lo, hi, msk in m_band_masks(blk, T, cuts[T]):
            miss = int((msk & ~got).sum())
            tot = int(msk.sum())
            out.append(_h0(
                区分="対照 (c')", 種=KIND_LABEL[KIND_C], **{"T(秒)": T},
                量="m の 10 分位帯ごとに取れなかった割合",
                群=(f"帯 {k} [{bound_text(lo) if lo == -math.inf else _fmt(lo, 4)}"
                    f", {bound_text(hi) if hi == math.inf else _fmt(hi, 4)})"),
                n=miss, 母数=tot, 割合=float(miss / tot) if tot else NAN))
        for name, msk in (("取れたプリント", got), ("取れなかったプリント", ~got)):
            out.append(_h0(区分="対照 (c')", 種=KIND_LABEL[KIND_C],
                           **{"T(秒)": T}, 量="取れた / 取れなかったプリントの中央値",
                           群=name, n=int(msk.sum()), 母数=n_all,
                           **{"m の中央値": quantiles(blk[f"m_{T}"][msk], [50])[0],
                              "k の中央値": quantiles(blk["k"][msk], [50])[0],
                              "r(60) の中央値": quantiles(
                                  blk[f"{R_MAIN_COL}_60"][msk], [50])[0]}))
        pd_n = per_day_ctrl[T]["n_prints"]
        pd_r = per_day_ctrl[T]["per_print"]
        out.append(_h0(区分="対照 (c')", 種=KIND_LABEL[KIND_C], **{"T(秒)": T},
                       量="日のプリント数 と その日の 1 件あたり取れた対照の数 の相関",
                       群="日を単位に", n=int(pd_n.size), 母数=int(pd_n.size),
                       相関=corr(pd_n, pd_r)))
    return out


# ---------------------------------------------------------------------------
# H1〜H6
# ---------------------------------------------------------------------------
def make_h1(rows: Rows, bi_by_day: dict) -> list:
    blk = rows.blk[KIND_PRINT]
    n_all = blk["_n"]
    msk = np.ones(n_all, dtype=bool)
    out = []
    for h in HORIZONS_SEC:
        row = {"群": "全プリント", "h(秒)": h, "プリント数": n_all}
        row.update(r_stats(blk, msk, h))
        row.update(next_liq(blk, msk))
        bv = np.array([bi_by_day[h].get(d, NAN) for d in blk["day"].tolist()],
                      dtype=float) * np.array(
                          [REACT_SIGN.get(s, NAN) for s in blk["side"].tolist()],
                          dtype=float)
        fin = bv[np.isfinite(bv)]
        row["対照 (b) 日集約 平均(bp)"] = float(fin.mean()) if fin.size else NAN
        row["対照 (b) 日集約 中央値"] = float(np.median(fin)) if fin.size else NAN
        row["対照 (b) の母数"] = int(fin.size)
        out.append(row)
    return out


def make_h2(rows: Rows, cuts: dict) -> list:
    blk = rows.blk[KIND_PRINT]
    out = []
    for T in T_MAIN:
        for k, lo, hi, msk in m_band_masks(blk, T, cuts[T]):
            for h in HORIZONS_SEC:
                row = {"T(秒)": T, "m の帯": k, "帯の下限(bp)": bound_text(lo),
                       "帯の上限(bp)": bound_text(hi), "h(秒)": h,
                       "帯のプリント数": int(msk.sum())}
                row.update(mean_median(blk[f"m_{T}"], msk, "m"))
                row.update(mean_median(blk["k"], msk, "k"))
                row.update(r_stats(blk, msk, h))
                row.update(next_liq(blk, msk))
                out.append(row)
    return out


def make_h3(rows: Rows, ter: dict, kcuts: tuple) -> list:
    blk = rows.blk[KIND_PRINT]
    lo, hi = ter[T_TERTILE]
    out = []
    for klabel, kmask in k_group_masks(blk, kcuts):
        for mlabel, mmask in m_tertile_masks(blk, T_TERTILE, lo, hi):
            msk = kmask & mmask
            n_zero = int((msk & np.isfinite(blk["k"]) & (blk["k"] == 0.0)).sum())
            for h in H_MAIN:
                row = {"k の群": klabel, "m の群": mlabel, "T(秒)": T_TERTILE,
                       "h(秒)": h, "群のプリント数": int(msk.sum()),
                       "うち k = 0 ちょうどの数": n_zero}
                row.update(mean_median(blk["k"], msk, "k"))
                row.update(mean_median(blk[f"m_{T_TERTILE}"], msk, "m"))
                row.update(r_stats(blk, msk, h))
                row.update(next_liq(blk, msk))
                out.append(row)
    return out


def make_h4(rows: Rows, cuts: dict) -> list:
    ctrl = rows.blk[KIND_C]
    out = []
    for T in T_MAIN:
        tsel = ctrl["ctrl_T"] == T
        bands = band_of_m(ctrl[f"m_{T}"], cuts[T])
        for k in range(1, N_BANDS + 1):
            lo, hi = band_bounds(cuts[T], k)
            msk = tsel & (bands == k)
            for h in H_MAIN:
                row = {"種": KIND_LABEL[KIND_C], "T(秒)": T, "m の帯": k,
                       "帯の下限(bp)": bound_text(lo), "帯の上限(bp)": bound_text(hi),
                       "h(秒)": h, "帯の行数": int(msk.sum())}
                row.update(mean_median(ctrl["c_t"], msk, "c_t"))
                row.update(r_stats(ctrl, msk, h))
                out.append(row)
    return out


def make_h5(rows: Rows, ter: dict) -> list:
    blk = rows.blk[KIND_PRINT]
    lo, hi = ter[T_TERTILE]
    out = []
    for dlabel, dmask in d_group_masks(blk):
        for mlabel, mmask in m_tertile_masks(blk, T_TERTILE, lo, hi):
            msk = dmask & mmask
            for h in H_MAIN:
                row = {"d の群": dlabel, "m の群": mlabel, "T(秒)": T_TERTILE,
                       "h(秒)": h, "群のプリント数": int(msk.sum())}
                row.update(mean_median(blk["d"], msk, "d"))
                row.update(mean_median(blk[f"m_{T_TERTILE}"], msk, "m"))
                row.update(r_stats(blk, msk, h))
                row.update(next_liq(blk, msk))
                out.append(row)
    return out


def h6_groups(blk: dict, attr_ok: dict) -> list:
    """属性ごとの**周辺の群**(積ではない)。側 2 + 想定元本 3 + 時刻帯 4 + 付け直せた属性。"""
    groups = []
    for s in ("SELL", "BUY"):
        groups.append({"属性": "side", "群": s, "下限": NAN, "上限": NAN,
                       "mask": blk["side"] == s,
                       "欠測の割合": float((blk["side"] == "").mean())})
    v = blk["notional"]
    lo, hi = tertile_cuts(v)
    bounds = {1: (NAN, lo), 2: (lo, hi), 3: (hi, NAN)}
    for q, label in TERTILE_LABELS:
        groups.append({"属性": "print_notional", "群": label,
                       "下限": bounds[q][0], "上限": bounds[q][1],
                       "mask": tertile_mask(v, lo, hi, q),
                       "欠測の割合": float((~np.isfinite(v)).mean())})
    for name, _lo, _hi in HOUR_BANDS:
        groups.append({"属性": ex2.ATTR_HOUR, "群": name, "下限": NAN, "上限": NAN,
                       "mask": blk["hour_band"] == name,
                       "欠測の割合": float((blk["hour_band"] == "").mean())})
    for name in ATTR_NAMES:
        if not attr_ok.get(name):
            continue
        col = {"bin_pct": "bin_pct", "|dist_node_bp|": "dist_node_bp",
               "implied_leverage": "implied_leverage"}[name]
        vv = np.abs(blk[col]) if name.startswith("|") else blk[col]
        lo, hi = tertile_cuts(vv)
        bounds = {1: (NAN, lo), 2: (lo, hi), 3: (hi, NAN)}
        for q, label in TERTILE_LABELS:
            groups.append({"属性": name, "群": label, "下限": bounds[q][0],
                           "上限": bounds[q][1],
                           "mask": tertile_mask(vv, lo, hi, q),
                           "欠測の割合": float((~np.isfinite(vv)).mean())})
    return groups


def make_h6(rows: Rows, ter: dict, attr_ok: dict) -> list:
    blk = rows.blk[KIND_PRINT]
    lo, hi = ter[T_TERTILE]
    out = []
    for g in h6_groups(blk, attr_ok):
        for mlabel, mmask in m_tertile_masks(blk, T_TERTILE, lo, hi):
            msk = g["mask"] & mmask
            for h in H_MAIN:
                row = {"属性": g["属性"], "群": g["群"], "下限": g["下限"],
                       "上限": g["上限"], "m の群": mlabel, "T(秒)": T_TERTILE,
                       "h(秒)": h, "群のプリント数": int(msk.sum()),
                       "属性が欠測で群に入らないプリントの割合": g["欠測の割合"]}
                row.update(mean_median(blk[f"m_{T_TERTILE}"], msk, "m"))
                row.update(r_stats(blk, msk, h))
                row.update(next_liq(blk, msk))
                out.append(row)
    return out


# ===========================================================================
# tables.md の数値セル数(反証者と同じ数え方)
# ===========================================================================
def count_numeric_cells(md_text: str) -> int:
    """`tables.md` の表の中で**数として読めるセル**の数。

    方法(`docs/DATA/probes/20260920_o3c_signal_explore3_refuter_cells.log` と同じ):
    `|` で始まる行を表の行とみなし、区切り行(`---` だけ)と 1 行目(見出し)を除き、
    各セルを `float()` に掛けて通ったものを数える。
    """
    n = 0
    header_seen = False
    for line in md_text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            header_seen = False
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(set(c) <= set("-: ") and c for c in cells):
            continue
        if not header_seen:
            header_seen = True
            continue
        for c in cells:
            try:
                float(c)
            except ValueError:
                continue
            n += 1
    return n


# ===========================================================================
# main
# ===========================================================================
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="O3C SIGNAL 探索段 5")
    ap.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    ap.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    ap.add_argument("--metrics-root", type=Path, default=DEFAULT_DATA_ROOT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stage", choices=("rows", "tables", "all"), default="all")
    ap.add_argument("--limit-days", type=int, default=0)
    ap.add_argument("--progress-every", type=int, default=20)
    ap.add_argument("--keep-chunks", action="store_true")
    a = ap.parse_args(argv)

    t0 = time.time()
    a.out.mkdir(parents=True, exist_ok=True)
    table = ex2.RunTable(a.runs_dir / MAIN_RUN)
    bd = ex3.Bundles(table)
    days = table.days()
    if a.limit_days:
        days = days[: a.limit_days]
    day_set = set(days)

    liq_dir = Path(a.data_root) / "liquidationSnapshot" / base.SYMBOL
    prints = load_prints(liq_dir)
    print(f"清算の zip {prints.n_files} 日 / 生 {prints.raw_rows} 行 -> "
          f"一意 {prints.uniq_rows} 件 / 対象 {len(days)} 日", flush=True)
    pos, single, bid = bundle_positions(prints, bd)

    uniform_by_day: dict = {}
    sel_u = np.flatnonzero(table.kind == ex2.KIND_UNIFORM)
    for i in sel_u.tolist():
        d = str(table.day[i])
        if d in day_set:
            uniform_by_day.setdefault(d, []).append(int(table.time_ms[i]))
    uniform_by_day = {d: np.array(sorted(v), dtype=np.int64)
                      for d, v in uniform_by_day.items()}

    if a.stage in ("rows", "all"):
        note1 = run_stage1(a.out, days, prints, uniform_by_day, a.data_root,
                           a.metrics_root, pos, single, bid, a.progress_every)
        m_by_T = read_m(a.out, days, prints)
        note2 = run_stage2(a.out, days, prints, m_by_T, a.data_root,
                           a.progress_every)
        concat_rows(a.out, days)
        (a.out / "stage_notes.json").write_text(json.dumps(
            {"stage1": note1, "m の帯の切り値": note2["cuts"],
             "対照 (c') の採否": note2["notes"]}, ensure_ascii=False, indent=2))
    if a.stage == "rows":
        return 0

    rows = Rows(a.out / "rows_prints.csv.gz")
    blk = rows.blk[KIND_PRINT]
    ctrl = rows.blk[KIND_C]
    bi = rows.blk[KIND_BI]

    cuts = {T: band_cuts_m(blk[f"m_{T}"]) for T in T_MAIN}
    ter = {T: tertile_cuts(blk[f"m_{T}"]) for T in T_MAIN}
    kpos = blk["k"][np.isfinite(blk["k"]) & (blk["k"] > 0)]
    kcuts = tertile_cuts(kpos)
    attr_ok = {"bin_pct": bool(np.isfinite(blk["bin_pct"]).any()),
               "|dist_node_bp|": bool(np.isfinite(blk["dist_node_bp"]).any()),
               "implied_leverage": bool(np.isfinite(blk["implied_leverage"]).any())}

    ctrl_notes = {T: {"n_prints": blk["_n"],
                      "n_taken": int((ctrl["ctrl_T"] == T).sum())}
                  for T in T_MAIN}
    # 日ごとのプリント数と 1 件あたり取れた対照の数
    per_day_ctrl = {}
    n_by_day: dict = defaultdict(int)
    for d in blk["day"].tolist():
        n_by_day[d] += 1
    for T in T_MAIN:
        c_by_day: dict = defaultdict(int)
        sel = ctrl["ctrl_T"] == T
        for d in ctrl["day"][sel].tolist():
            c_by_day[d] += 1
        ks = sorted(n_by_day)
        per_day_ctrl[T] = {
            "n_prints": np.array([n_by_day[d] for d in ks], dtype=float),
            "per_print": np.array([c_by_day.get(d, 0) / n_by_day[d] for d in ks],
                                  dtype=float)}

    # 対照 (b): 日ごとの一様行の生の r(h) の平均
    bi_by_day = {}
    for h in HORIZONS_SEC:
        acc: dict = defaultdict(list)
        v = bi[f"r_{h}"]
        for x, d in zip(v.tolist(), bi["day"].tolist()):
            if math.isfinite(x):
                acc[d].append(x)
        bi_by_day[h] = {d: sum(xs) / len(xs) for d, xs in acc.items()}

    h0 = make_h0(rows, cuts, ctrl_notes, prints, len(days), per_day_ctrl)
    h1 = make_h1(rows, bi_by_day)
    h2 = make_h2(rows, cuts)
    h3 = make_h3(rows, ter, kcuts)
    h4 = make_h4(rows, cuts)
    h5 = make_h5(rows, ter)
    h6 = make_h6(rows, ter, attr_ok)
    named = [("h0_selfcheck.csv", h0, "H0", "H0 自己点検と診断"),
             ("h1_all_prints.csv", h1, "H1", "H1 全プリントの後の動き"),
             ("h2_premove.csv", h2, "H2", "H2 直前の値動き m の 10 分位"),
             ("h3_impact_premove.csv", h3, "H3", "H3 このプリントの掃き k × m"),
             ("h4_control.csv", h4, "H4", "H4 対照 (c') 直前の値動き合わせ"),
             ("h5_density.csv", h5, "H5", "H5 直近の清算の密度 d"),
             ("h6_attributes.csv", h6, "H6", "H6 属性(周辺の群)")]
    for name, rr, _k, _t in named:
        write_csv(a.out / name, rr)

    # --- summary.json -------------------------------------------------------
    liq_zips = sorted(liq_dir.glob(f"{base.SYMBOL}-liquidationSnapshot-*.zip"))
    inputs = {str(p.relative_to(REPO_ROOT)): md5_of(p) for p in liq_zips}
    p_tab = a.runs_dir / MAIN_RUN / "table.csv"
    inputs[str(p_tab.relative_to(REPO_ROOT))] = md5_of(p_tab)
    agg_dir = Path(a.data_root) / "aggTrades" / base.SYMBOL
    agg_files = sorted(agg_dir.glob(f"{base.SYMBOL}-aggTrades-*.zip"))
    met_dir = Path(a.metrics_root) / "metrics" / base.SYMBOL
    met_files = sorted(met_dir.glob(f"{base.SYMBOL}-metrics-*.zip"))
    stage_notes = {}
    p_notes = a.out / "stage_notes.json"
    if p_notes.exists():
        stage_notes = json.loads(p_notes.read_text())
    missing_cal = calendar_gaps(days)

    summary = {
        "実行時刻(UTC)": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "経過秒": round(time.time() - t0, 1),
        "設計": "docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE5_DESIGN_2026-09-20.md",
        "パラメータ": {
            "T(秒)": list(T_MAIN), "3 分位を切る T(秒)": T_TERTILE,
            "h(秒)": list(HORIZONS_SEC), "h(秒) 主": list(H_MAIN),
            "穴の上限(ms)": STALENESS_MS,
            "m の帯の数": N_BANDS,
            "m の帯の規則": ("帯 1 = (−∞, q_1)、帯 k ≥ 2 = [q_{k−1}, q_k)、"
                       "帯 10 = [q_9, +∞)。456 日の全プリントの m で切る(負を含む)"),
            "d の窓(ms)": DENSITY_WINDOW_MS, "d の群": ["0", "1〜2", "3 以上"],
            "k の群": "k ≤ 0 の 1 群 + k > 0 のプリントで切った 3 分位",
            "次の清算(結果)の境界(秒)": list(NEXT_SEC),
            "対照 (c') の候補の刻み(ms)": GRID_STEP_MS,
            "対照 (c') の候補点/日": GRID_N,
            "対照 (c') の区間": "[t − T*1000, t + 900_000](どの側のプリントも無いこと)",
            "属性の窓 W(時間)": W_HOURS, "価格ビンの幅(%)": BIN_PCT,
            "維持証拠金率 mmr": MMR,
            "符号": "SELL: −1 / BUY: +1(探索段 1〜4 と同じ向き。負 = 清算と逆)",
            "起点": "p₀ = at_or_after(ts, 300_000)、t₀ = p₀ の約定の時刻",
            "直前": "at_or_before(ts − 1, 300_000)",
            "T 秒前": "at_or_before(ts − T*1000, 300_000)",
            "h 後(主)": ("at_or_before(t₀ + h*1000, 300_000)。列 r_t0_h。"
                     "探索段 4 の r_end(h) と同じ起点(t₀ = p₀ の約定の時刻)"),
            "h 後(併記)": ("at_or_before(ts + h*1000, 300_000)。列 r_h。"
                       "設計の前版の用語表の式。H0 の「診断(束の位置)」と"
                       "「起点の取り方」の行にだけ併記する"),
            "m(T)": "s × (p_pre − p_T)/p_T × 1e4",
            "k": "s × (p₀ − p_pre)/p_pre × 1e4",
            "r(h)": "s × (p_h − p₀)/p₀ × 1e4(主の表は p_h を t₀ 基準で引く)",
            "対照 (b)": ("1 周目の対照 (i) 一様行の生(符号なし)の r を日ごとに平均し、"
                     "その日の各プリントの側の符号を掛ける(日集約版)"),
            "属性の付け直し": ("bin_pct / dist_node_bp は "
                       "`scripts/o3c_reaction.py: profile_columns`(窓 [ts − W, ts))、"
                       "implied_leverage は `scripts/o3c_oi_distance.py` の "
                       "ΔOI 桶(t_b ≤ ts)+ `_apply_liqdir_and_leverage`"),
        },
        "主の表の r(h) の基準": ("t₀(設計の訂正 2026-09-20)。H1〜H6 と H0 の"
                          "診断・欠測は列 r_t0_h を使う。ts 基準の列 r_h は "
                          "H0 の「診断(束の位置)」「起点の取り方」の行に併記"
                          "するだけで、主の表には使わない"),
        "入力の MD5": inputs,
        "約定アーカイブ": {"場所": str(agg_dir.relative_to(REPO_ROOT)),
                    "zip の数": len(agg_files),
                    "合計バイト": sum(p.stat().st_size for p in agg_files)},
        "metrics アーカイブ": {"場所": str(met_dir.relative_to(REPO_ROOT)),
                        "zip の数": len(met_files),
                        "合計バイト": sum(p.stat().st_size for p in met_files)},
        "日数": len(days),
        "暦の日数(最初〜最後)": (
            (_dt.date.fromisoformat(days[-1])
             - _dt.date.fromisoformat(days[0])).days + 1),
        "欠けた日": missing_cal, "欠けた日の数": len(missing_cal),
        "プリント数": {
            "清算の zip の日数": prints.n_files,
            "重複除去の前(生の行)": prints.raw_rows,
            "重複除去の後(全列一致で 1 件)": prints.uniq_rows,
            f"この単位({len(days)} 日)": blk["_n"]},
        "行数": {KIND_LABEL[k]: rows.blk[k]["_n"] for k in KINDS},
        "m の帯の切り値": {str(T): [float(x) for x in cuts[T]] for T in T_MAIN},
        "m の 3 分位の切り値": {str(T): [ter[T][0], ter[T][1]] for T in T_MAIN},
        "k > 0 の 3 分位の切り値": [kcuts[0], kcuts[1]],
        "付け直せた属性": attr_ok,
        "対照 (c') の採否": {
            str(T): {"対象のプリント": ctrl_notes[T]["n_prints"],
                     "取れたプリント": ctrl_notes[T]["n_taken"],
                     "取れなかったプリント": (ctrl_notes[T]["n_prints"]
                                  - ctrl_notes[T]["n_taken"])} for T in T_MAIN},
        "欠測": {
            "起点 p₀ が引けないプリント": int((~np.isfinite(blk["p0"])).sum()),
            "直前が引けないプリント": int((~np.isfinite(blk["p_pre"])).sum()),
            "k が NaN のプリント": int((~np.isfinite(blk["k"])).sum()),
            "m が NaN のプリント": {str(T): int((~np.isfinite(blk[f"m_{T}"])).sum())
                            for T in T_MAIN},
            "r が NaN のプリント": {str(h): int((~np.isfinite(blk[f"r_{h}"])).sum())
                            for h in HORIZONS_SEC},
            "r_t0 が NaN のプリント": {str(h): int((~np.isfinite(blk[f"r_t0_{h}"])).sum())
                               for h in HORIZONS_SEC},
            "bin_pct が NaN": int((~np.isfinite(blk["bin_pct"])).sum()),
            "dist_node_bp が NaN": int((~np.isfinite(blk["dist_node_bp"])).sum()),
            "implied_leverage が NaN": int((~np.isfinite(blk["implied_leverage"])).sum()),
            "同じ側の次の清算が無いプリント": int(
                (~np.isfinite(blk["next_same_side_gap_s"])).sum()),
            "探索段 4 の束に入らないプリント": int((blk["bundle_pos"] == POS_NONE).sum()),
        },
        "約定が読めなかった日": stage_notes.get("stage1", {}).get(
            "agg_days_missing", "(この走行では rows 段を回していない)"),
        "metrics が読めなかった日": stage_notes.get("stage1", {}).get(
            "metrics_days_missing", "(この走行では rows 段を回していない)"),
        "表の行数": {key: len(rr) for _n, rr, key, _t in named},
    }
    summary["表の行数"]["合計"] = sum(len(rr) for _n, rr, _k, _t in named)
    summary["表の行数"]["H0 を除く合計"] = summary["表の行数"]["合計"] - len(h0)

    # 探索段 4 との突き合わせ(H0 の診断「最後」)
    last = position_mask(blk["bundle_pos"], blk["bundle_pos_single"], POS_LAST)
    cmp_block = {}
    for tag, col in (("ts 基準", "r"), ("t₀ 基準", "r_t0")):
        mean, se, naive, n, g = mean_se_cluster(blk[f"{col}_60"][last],
                                                blk["day"][last])
        cmp_block[tag] = {"平均": mean, "n": n, "含む日数": g,
                          "日クラスタ SE": se, "naive SE": naive}
    summary["探索段 4 との突き合わせ"] = {
        "量": "束の位置「最後」のプリントの r(60) の平均",
        "探索段 4 の値": -6.800366,
        "出典": ("backtest_data/o3c_signal_explore4_20260920/summary.json の"
               "「探索段 3 との突き合わせ」= gap 60 の清算側 r_end(60) の全体平均"),
        "この段": cmp_block,
    }

    # --- tables.md ----------------------------------------------------------
    md = [f"# O3C SIGNAL 探索段 5 の表({days[0]} 〜 {days[-1]}、{len(days)} 日)", "",
          f"- 設計: `{summary['設計']}`",
          f"- T(秒)= {list(T_MAIN)} / h(秒)= {list(HORIZONS_SEC)}"
          f"(H3〜H6 は {list(H_MAIN)})",
          f"- プリント = 清算 1 件(全列一致の重複は 1 件)。この単位 {blk['_n']} 件",
          f"- 欠けた日({len(missing_cal)} 日): " + ", ".join(missing_cal),
          "- 起点 p₀ = `at_or_after(ts, 300_000)`、t₀ = p₀ の約定の時刻 / 直前 = "
          "`at_or_before(ts − 1, 300_000)` / T 秒前 = "
          "`at_or_before(ts − T*1000, 300_000)` / h 後(主)= "
          "`at_or_before(t₀ + h*1000, 300_000)`",
          "- m(T) = s × (p_pre − p_T)/p_T × 1e4、k = s × (p₀ − p_pre)/p_pre × 1e4、"
          "r(h) = s × (p_h − p₀)/p₀ × 1e4",
          "- **主の表(H1〜H6)の r(h) の基準 = t₀(設計の訂正 2026-09-20)**。"
          "列 `r_t0_h`(探索段 4 の r_end(h) と同じ起点)",
          "- `ts` 基準の版(`at_or_before(ts + h*1000, 300_000)`、列 `r_h`)は "
          "H0 の「診断(束の位置)」「起点の取り方」の行に**併記**するだけで、"
          "主の表には使っていない",
          "- 割合の列にはすべて母数の列、平均の列にはすべて中央値と "
          "日クラスタ / naive の比を添えてある", ""]
    for name, rr, _k, title in named:
        md += [f"## {title}(`{name}`、{len(rr)} 行)", "", md_table(rr), ""]
    mdtxt = "\n".join(md)
    check_no_banned(mdtxt, "tables.md")
    (a.out / "tables.md").write_text(mdtxt)
    summary["tables.md の数値セル数"] = count_numeric_cells(mdtxt)
    summary["tables.md の数え方"] = (
        "`|` で始まる表の行のうち、区切り行と各表の見出し行を除いたセルを "
        "`float()` に掛けて通った数(探索段 3 の反証者のセル数と同じ数え方)")

    txt = json.dumps(summary, ensure_ascii=False, indent=2)
    check_no_banned(txt, "summary.json")
    (a.out / "summary.json").write_text(txt)

    if not a.keep_chunks:
        n_drop = drop_chunks(a.out)
        print(f"chunk の中間ファイルを {n_drop} 個消した", flush=True)

    names = (["rows_prints.csv.gz"] + [n for n, _r, _k, _t in named]
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

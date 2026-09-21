#!/usr/bin/env python3
"""清算を起点とした値動きの予測可能性(SIGNAL)— **探索段 2** の道具。

設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE2_DESIGN_2026-09-19.md`
(§2 問い E0〜E4 / §4 対照 / §6 データ / §7 決めたこと)。

**この道具がすること**
  - 束と対照は 1 周目の走行の表(`backtest_data/o3c_reaction_20260918_full/<run>/table.csv`)
    の行を**そのまま使う**(束を作り直さない = 同じ集合)。gap 60 が主、30 / 180 は感度で、
    それぞれ自分の表の束と対照を使う(gap 60 の束を流用しない)。
  - **起点と h 後の価格だけ**を約定(`backtest_data/binance_cm_o3c_20260913/aggTrades/BTCUSD_PERP/*.zip`)
    から取り直す。起点 = `at_or_after(基準時刻 + Δ*1000, 300_000)`、
    h 後 = `at_or_before(起点の時刻 + h*1000, 300_000)`。基準時刻は
    束なら `end_ms`、対照なら対照の時刻(1 周目でも `end_ms` に入っている)。
  - bitFlyer は 1 周目の `bf_*` 列と同じ経路・同じ規則
    (`candles_1m_<年>.csv.gz` の終値、`at_or_before`、5 分の遡り上限、前値で埋めない)。
  - 出力は E0〜E4 の表・`rows_gap*.csv.gz`・`tables.md`・`summary.json`・`MD5SUMS`。

**探索段なので判定語(差あり / 検出されず / 陽性 / 陰性 / 有意)を 1 つも書かない。**
検定もしない。読み(なぜ)も書かない。出すのは平均・SE・n・割合だけである。

**`paper_logs/` は開かない**(自前記録は判定まで触らない)。この道具は
`backtest_data/` と `docs/` 以外のどのディレクトリも読まない。

**符号の規則**
  - 束の行: `REACT_SIGN` = SELL: −1 / BUY: +1(1 周目の `*_reactdir` と同じ向き。負 = 反転)。
  - 対照 (ii)(`control_matched`): `matched_liq_id` で相手の束を引き、その `side` の符号。
    相手が主表に居ない行(相手が `table_mixed.csv` の束)は符号が無いので `side` を空にし、
    `r` を NaN にする(1 周目の探索段 1 が落としたのと同じ集合が集計から外れる)。
  - 対照 (i)(`control_uniform`): 行は束に紐づいていないので、設計 §4 の規則で組む。
    日ごとに、束の行を `start_ms` の昇順、一様行を `time_ms` の昇順に並べ、i 番目どうしを
    1 対 1 に組む。一様行が余る日(mixed の束がある日)は**末尾の余りを落とす**
    (落とした行は `side` が空で `r` は NaN)。組み方は決定的で価格を見ない。
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import gzip
import hashlib
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

import o3c_price_level_table as base  # noqa: E402  (agg_path / load_agg_trades をそのまま)

REPO_ROOT = _HERE.parent
NAN = float("nan")

# ---------------------------------------------------------------------------
# 固定値(設計 §7。変えるときは報告に列挙する)
# ---------------------------------------------------------------------------
DELTAS_SEC = (0, 1, 5, 10, 30, 60)
HORIZONS_SEC = (1, 5, 10, 30, 60, 300, 900, 3600, 14400, 28800)
STALENESS_MS = 300_000          # 1 周目の `anchor_max_staleness_ms` と同じ
RUNS = ("gap60_w8", "gap30_w8", "gap180_w8")
GAP_OF_RUN = {"gap60_w8": 60, "gap30_w8": 30, "gap180_w8": 180}
E1_HORIZON_SEC = 60
E2_DELTAS = (0, 10, 60)
E4_DELTAS = (0, 10, 60)
REF_HORIZON_SEC = 14400         # 参考(探索段 1 の 240 分)

KIND_LIQ = "liq"
KIND_UNIFORM = "control_uniform"
KIND_MATCHED = "control_matched"
KINDS = (KIND_LIQ, KIND_UNIFORM, KIND_MATCHED)
KIND_LABEL = {KIND_LIQ: "清算", KIND_UNIFORM: "対照(i) 一様",
              KIND_MATCHED: "対照(ii) 薄さ合わせ"}

REACT_SIGN = {"SELL": -1.0, "BUY": 1.0}

DEFAULT_RUNS_DIR = REPO_ROOT / "backtest_data" / "o3c_reaction_20260918_full"
DEFAULT_DATA_ROOT = REPO_ROOT / "backtest_data" / "binance_cm_o3c_20260913"
DEFAULT_BITFLYER_DIR = (
    REPO_ROOT / "backtest_data" / "bitflyer_lightchart_FX_BTC_JPY_1m_20260906"
)
DEFAULT_OUT = REPO_ROOT / "backtest_data" / "o3c_signal_explore2_20260919"

# 判定語。**出力に 1 つも出てはならない**(探索段)。
BANNED_WORDS = ("差あり", "検出されず", "陽性", "陰性", "有意")

# 属性(探索段 1 `scripts/o3c_signal_explore.py` と同じ列・同じ切り方)
ATTRS_NUM = [
    ("|dist_vwap_bp|", "dist_vwap_bp", True),
    ("|dist_node_bp|", "dist_node_bp", True),
    ("bin_pct", "bin_pct", False),
    ("bundle_n_events_dedup", "bundle_n_events_dedup", False),
    ("bundle_total_notional", "bundle_total_notional", False),
    ("bundle_width_ms", "bundle_width_ms", False),
    ("doi_pre_1h", "doi_pre_1h", False),
    ("implied_leverage", "implied_leverage", False),
]
TERTILE_LABELS = ((1, "Q1(下位 3 分位)"), (2, "Q2(中位 3 分位)"), (3, "Q3(上位 3 分位)"))
HOUR_BANDS = (("UTC 00–06", 0, 6), ("UTC 06–12", 6, 12),
              ("UTC 12–18", 12, 18), ("UTC 18–24", 18, 24))
ATTR_SIDE = "side"
ATTR_HOUR = "time_of_day(UTC 時、6 時間の 4 帯)"

R_COLS = [f"r_{h}" for h in HORIZONS_SEC]
BF_COLS = [f"bf_r_{h}" for h in HORIZONS_SEC]
ROW_COLUMNS = (["kind", "cascade_id", "day", "side", "delta_sec",
                "anchor_ts_ms", "anchor_lag_ms", "bounce"] + R_COLS + BF_COLS)


# ===========================================================================
# 小道具
# ===========================================================================
def _f(x) -> float:
    if x is None:
        return NAN
    try:
        return float(x)
    except (TypeError, ValueError):
        return NAN


def _fmt(x, nd: int = 4) -> str:
    if x is None:
        return ""
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    v = float(x)
    if not math.isfinite(v):
        return ""
    return f"{v:.{nd}f}"


def mean_se_cluster(vals: np.ndarray, days: np.ndarray) -> tuple[float, float, float, int, int]:
    """平均・日クラスタ SE・naive SE・n・日数。

    日クラスタ SE の式は `docs/DATA/probes/20260919_o3c_signal_refuter_verify.py` の
    `mean_se_cluster` をそのまま写したもの:
        m = mean(v); s_d = Σ_{i∈d} (v_i − m); SE = sqrt(Σ_d s_d²)/n × sqrt(G/(G−1))
    naive SE は母標準偏差 / √n(同じプローブの `statistics.pstdev(v)/sqrt(n)`)。
    """
    ok = np.isfinite(vals)
    v = vals[ok]
    d = days[ok]
    n = int(v.size)
    if n == 0:
        return NAN, NAN, NAN, 0, 0
    m = float(v.mean())
    acc: dict = defaultdict(float)
    for x, dd in zip(v.tolist(), d.tolist()):
        acc[dd] += x - m
    g = len(acc)
    if g > 1:
        se = math.sqrt(sum(s * s for s in acc.values())) / n * math.sqrt(g / (g - 1))
    else:
        se = NAN
    naive = float(v.std(ddof=0)) / math.sqrt(n) if n > 0 else NAN
    return m, se, naive, n, g


def three_way(vals: np.ndarray) -> tuple[float, float, float]:
    """r < 0 / r = 0 / r > 0 の割合(有限な値のうち)。和は 1。"""
    v = vals[np.isfinite(vals)]
    n = int(v.size)
    if n == 0:
        return NAN, NAN, NAN
    return float((v < 0).mean()), float((v == 0).mean()), float((v > 0).mean())


def tertile_cuts(v: np.ndarray) -> tuple[float, float]:
    """3 分位の切り値(`scripts/o3c_signal_explore.py: tertile_cuts` と同じ)。"""
    fin = v[np.isfinite(v)]
    if fin.size == 0:
        return NAN, NAN
    lo, hi = np.nanpercentile(fin, [100.0 / 3.0, 200.0 / 3.0])
    return float(lo), float(hi)


def tertile_mask(v: np.ndarray, lo: float, hi: float, q: int) -> np.ndarray:
    """own 方式(`scripts/o3c_signal_explore.py: tertile_mask` と同じ)。"""
    if not (math.isfinite(lo) and math.isfinite(hi)):
        return np.zeros(v.size, dtype=bool)
    if q == 1:
        sel = v <= lo
    elif q == 2:
        sel = (v > lo) & (v <= hi)
    else:
        sel = v > hi
    return sel & np.isfinite(v)


def gz_open_w(path):
    """書き出し用の gzip(**mtime = 0**)。

    `gzip.open` は gzip ヘッダに書き出し時刻を入れるので、同じ中身でもファイルの
    MD5 が走行ごとに変わる。`MD5SUMS` を再実行の突き合わせに使えるように 0 で固定する。
    """
    return io.TextIOWrapper(
        gzip.GzipFile(filename="", mode="wb", fileobj=open(path, "wb"), mtime=0),
        encoding="utf-8", newline="")


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def check_no_banned(text: str, where: str) -> None:
    hit = [w for w in BANNED_WORDS if w in text]
    if hit:
        raise SystemExit(f"[止め] 判定語が出力に混ざっている({where}): {hit}")


# ===========================================================================
# 1 周目の表を読む
# ===========================================================================
TABLE_COLUMNS_NEEDED = {
    "kind", "day", "cascade_id", "side", "start_ms", "end_ms", "time_ms",
    "matched_liq_id", "dist_vwap_bp", "dist_node_bp", "bin_pct",
    "bundle_n_events_dedup", "bundle_total_notional", "bundle_width_ms",
    "doi_pre_1h", "implied_leverage",
}


class RunTable:
    """1 走行の主表を読み、符号と対照 (i) の組を当てたもの。"""

    def __init__(self, run_dir: Path):
        self.run_dir = Path(run_dir)
        path = self.run_dir / "table.csv"
        if not path.exists():
            raise SystemExit(f"[止め] 表が無い: {path}")
        cols: dict[str, list] = {}
        with open(path, newline="") as fh:
            rd = csv.DictReader(fh)
            header = rd.fieldnames or []
            want = [c for c in TABLE_COLUMNS_NEEDED if c in header]
            self.header_missing = sorted(TABLE_COLUMNS_NEEDED - set(header))
            for c in want:
                cols[c] = []
            for r in rd:
                for c in want:
                    cols[c].append(r[c])
        self.cols = cols
        self.n_rows = len(cols["kind"])
        kind = np.array(cols["kind"], dtype=object)
        self.kind = kind
        self.day = np.array(cols["day"], dtype=object)
        self.cascade_id = np.array(cols["cascade_id"], dtype=object)
        self.base_ts = np.array([int(x) for x in cols["end_ms"]], dtype=np.int64)
        self.start_ms = np.array([int(x) for x in cols["start_ms"]], dtype=np.int64)
        self.time_ms = np.array([int(x) for x in cols["time_ms"]], dtype=np.int64)
        raw_side = np.array(cols["side"], dtype=object)
        partner = np.array(cols.get("matched_liq_id", [""] * self.n_rows), dtype=object)
        self.matched_liq_id = partner

        # -- 符号 ------------------------------------------------------------
        side = np.array([""] * self.n_rows, dtype=object)
        liq_i = np.flatnonzero(kind == KIND_LIQ)
        for i in liq_i.tolist():
            side[i] = raw_side[i]
        side_by_id = {self.cascade_id[i]: raw_side[i] for i in liq_i.tolist()}
        self.side_by_id = side_by_id

        mat_i = np.flatnonzero(kind == KIND_MATCHED)
        self.n_matched_partner_missing = 0
        for i in mat_i.tolist():
            s = side_by_id.get(partner[i])
            if s is None:
                self.n_matched_partner_missing += 1
                continue
            side[i] = s

        # -- 対照 (i) の組(設計 §4)------------------------------------------
        uni_i = np.flatnonzero(kind == KIND_UNIFORM)
        liq_by_day: dict[str, list[int]] = defaultdict(list)
        uni_by_day: dict[str, list[int]] = defaultdict(list)
        for i in liq_i.tolist():
            liq_by_day[self.day[i]].append(i)
        for i in uni_i.tolist():
            uni_by_day[self.day[i]].append(i)
        self.uniform_dropped_by_day: dict[str, int] = {}
        n_dropped = 0
        for d, idx in uni_by_day.items():
            ls = sorted(liq_by_day.get(d, []), key=lambda i: (self.start_ms[i], self.cascade_id[i]))
            us = sorted(idx, key=lambda i: (self.time_ms[i], self.cascade_id[i]))
            k = min(len(ls), len(us))
            for a, b in zip(ls[:k], us[:k]):
                side[b] = raw_side[a]
            drop = len(us) - k
            if drop:
                self.uniform_dropped_by_day[d] = drop
                n_dropped += drop
        self.n_uniform_dropped = n_dropped

        self.side = side
        self.sign = np.array([REACT_SIGN.get(s, NAN) for s in side], dtype=float)

        # -- 束に対照 (ii) が付いたか ------------------------------------------
        have = set()
        for i in mat_i.tolist():
            if side[i]:
                have.add(partner[i])
        self.liq_has_matched = np.array(
            [(self.cascade_id[i] in have) if kind[i] == KIND_LIQ else False
             for i in range(self.n_rows)], dtype=bool)
        self.n_liq = int(liq_i.size)
        self.n_uniform = int(uni_i.size)
        self.n_matched = int(mat_i.size)

    def num(self, col: str) -> np.ndarray:
        src = self.cols.get(col)
        if src is None:
            return np.full(self.n_rows, NAN)
        return np.array([_f(x) for x in src], dtype=float)

    def days(self) -> list[str]:
        return sorted(set(self.day.tolist()))


# ===========================================================================
# bitFlyer 1 分足(1 周目と同じ経路・同じ規則)
# ===========================================================================
def load_bitflyer_minutes(years, root: Path) -> dict:
    import pandas as pd
    parts, missing = [], []
    for y in sorted(set(years)):
        p = Path(root) / f"candles_1m_{y}.csv.gz"
        if not p.exists():
            missing.append(int(y))
            continue
        parts.append(pd.read_csv(p, usecols=["ts", "close"]))
    if not parts:
        return {"t_ms": np.zeros(0, dtype=np.int64), "close": np.zeros(0),
                "years_missing": missing}
    df = pd.concat(parts, ignore_index=True)
    t = (pd.to_datetime(df["ts"], utc=True).astype("datetime64[ms, UTC]")
         .astype("int64").to_numpy(dtype=np.int64))
    order = np.argsort(t, kind="stable")
    close = pd.to_numeric(df["close"], errors="coerce").to_numpy(dtype=np.float64)
    return {"t_ms": t[order], "close": close[order], "years_missing": missing}


def bf_close_at_or_before(bf: dict, ts: np.ndarray) -> np.ndarray:
    """`ts`(配列)以前で最も新しい 1 分足の終値。5 分より古ければ NaN。

    `scripts/o3c_reaction.py: bf_close_at_or_before` と同じ規則(前値で埋めない)。
    """
    t = bf["t_ms"]
    out = np.full(ts.shape, NAN)
    if t.size == 0:
        return out
    ok = np.isfinite(ts.astype(float)) & (ts > 0)
    i = np.searchsorted(t, ts, side="right") - 1
    good = ok & (i >= 0)
    ic = np.clip(i, 0, t.size - 1)
    good = good & ((ts - t[ic]) <= STALENESS_MS)
    out[good] = bf["close"][ic][good]
    return out


# ===========================================================================
# 起点と h 後の価格(この段の中身)
# ===========================================================================
def anchor_and_reactions(
    base_ts: np.ndarray, sign: np.ndarray, delta_sec: int,
    times: np.ndarray, prices: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """起点(時刻・価格)と h ごとの `r`。行は落とさない(引けなければ NaN)。

    起点 = `at_or_after(base_ts + Δ*1000, 300_000)` の**時刻だけ**で決まる
    (価格は選んだあとに読む = 先読みをしていない)。
    h 後 = `at_or_before(起点の時刻 + h*1000, 300_000)`。
    """
    n = base_ts.size
    a_ts = np.zeros(n, dtype=np.int64)
    a_px = np.full(n, NAN)
    a_ok = np.zeros(n, dtype=bool)
    if times.size:
        tgt = base_ts + delta_sec * 1000
        i = np.searchsorted(times, tgt, side="left")
        ok = i < times.size
        ic = np.clip(i, 0, times.size - 1)
        ok = ok & ((times[ic] - tgt) <= STALENESS_MS)
        a_ts[ok] = times[ic][ok]
        a_px[ok] = prices[ic][ok]
        a_ok = ok
    r: dict[int, np.ndarray] = {}
    for h in HORIZONS_SEC:
        out = np.full(n, NAN)
        if times.size:
            tgt2 = np.where(a_ok, a_ts + h * 1000, 0)
            j = np.searchsorted(times, tgt2, side="right") - 1
            okf = a_ok & (j >= 0)
            jc = np.clip(j, 0, times.size - 1)
            okf = okf & ((tgt2 - times[jc]) <= STALENESS_MS)
            okf = okf & np.isfinite(a_px) & (a_px > 0)
            with np.errstate(invalid="ignore", divide="ignore"):
                vals = (prices[jc] - a_px) / a_px * 1e4 * sign
            out[okf] = vals[okf]
        r[h] = out
    return a_ts, a_px, a_ok, r


# ===========================================================================
# 1 日ぶんの行
# ===========================================================================
def day_rows(
    tables: dict[str, RunTable], idx_by_run: dict[str, np.ndarray], day: str,
    data_root: Path, bf: dict, agg_cache: dict,
) -> tuple[list[list], dict]:
    """その日の全走行・全 Δ の行。約定は 1 回だけ読む。"""
    ends = []
    for run, idx in idx_by_run.items():
        if idx.size:
            ends.append(tables[run].base_ts[idx])
    if not ends:
        return [], {"agg_days_missing": [], "n_points": 0}
    allend = np.concatenate(ends)
    lo = int(allend.min()) - STALENESS_MS
    hi = int(allend.max()) + max(DELTAS_SEC) * 1000 + max(HORIZONS_SEC) * 1000 + STALENESS_MS
    d_lo = _dt.datetime.fromtimestamp(lo / 1000, _dt.timezone.utc).date().isoformat()
    d_hi = _dt.datetime.fromtimestamp(hi / 1000, _dt.timezone.utc).date().isoformat()
    need = [d_lo]
    while need[-1] < d_hi:
        nxt = (_dt.date.fromisoformat(need[-1]) + _dt.timedelta(days=1)).isoformat()
        need.append(nxt)

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

    out: list[list] = []
    for run, idx in idx_by_run.items():
        if not idx.size:
            continue
        t = tables[run]
        gap = GAP_OF_RUN[run]
        bts = t.base_ts[idx]
        sign = t.sign[idx]
        kinds = t.kind[idx]
        cids = t.cascade_id[idx]
        sides = t.side[idx]
        a0_px = None
        a0_ok = np.zeros(idx.size, dtype=bool)
        for delta in DELTAS_SEC:
            a_ts, a_px, a_ok, r = anchor_and_reactions(bts, sign, delta, times, prices)
            if delta == 0:
                a0_px = a_px.copy()
                a0_ok = a_ok.copy()
            lag = np.where(a_ok, a_ts - (bts + delta * 1000), np.nan)
            with np.errstate(invalid="ignore", divide="ignore"):
                bounce = np.where(
                    a_ok & a0_ok & np.isfinite(a0_px) & (a0_px > 0),
                    (a_px - a0_px) / a0_px * 1e4 * sign, np.nan)
            bf0 = bf_close_at_or_before(bf, np.where(a_ok, a_ts, 0))
            bfr = {}
            for h in HORIZONS_SEC:
                bf1 = bf_close_at_or_before(
                    bf, np.where(a_ok, a_ts + h * 1000, 0))
                good = a_ok & np.isfinite(bf0) & (bf0 > 0) & np.isfinite(bf1)
                with np.errstate(invalid="ignore", divide="ignore"):
                    v = (bf1 - bf0) / bf0 * 1e4 * sign
                bfr[h] = np.where(good, v, np.nan)
            for p in range(idx.size):
                row = [gap, kinds[p], cids[p], day, sides[p], delta,
                       int(a_ts[p]) if a_ok[p] else "",
                       "" if not math.isfinite(lag[p]) else int(lag[p]),
                       _fmt(bounce[p], 6)]
                row += [_fmt(r[h][p], 6) for h in HORIZONS_SEC]
                row += [_fmt(bfr[h][p], 6) for h in HORIZONS_SEC]
                out.append(row)
    return out, {"agg_days_missing": missing, "n_points": int(times.size)}


CHUNK_HEADER = ["gap"] + ROW_COLUMNS


def stage_rows(tables: dict[str, RunTable], out_dir: Path, data_root: Path,
               bf_dir: Path, days: list[str], progress_every: int = 20) -> dict:
    work = out_dir / "chunks"
    work.mkdir(parents=True, exist_ok=True)
    years = sorted({int(d[:4]) for d in days} | {int(d[:4]) + 1 for d in days})
    bf = load_bitflyer_minutes(years, bf_dir)
    print(f"bitFlyer 1 分足 {bf['t_ms'].size} 点 / 無い年 {bf['years_missing']}", flush=True)
    idx_cache = {}
    for run, t in tables.items():
        by_day: dict[str, list[int]] = defaultdict(list)
        for i, d in enumerate(t.day.tolist()):
            by_day[d].append(i)
        idx_cache[run] = {d: np.array(v, dtype=int) for d, v in by_day.items()}
    agg_cache: dict = {}
    agg_missing: set = set()
    t0 = time.time()
    for n_done, day in enumerate(days, start=1):
        cp = work / f"{day}.csv.gz"
        if cp.exists():
            continue
        idx_by_run = {run: idx_cache[run].get(day, np.zeros(0, dtype=int))
                      for run in tables}
        rows, note = day_rows(tables, idx_by_run, day, data_root, bf, agg_cache)
        agg_missing |= set(note["agg_days_missing"])
        tmp = work / f".{day}.csv.gz.part"
        with gz_open_w(tmp) as fh:
            w = csv.writer(fh)
            w.writerow(CHUNK_HEADER)
            w.writerows(rows)
        tmp.replace(cp)
        if n_done % progress_every == 0:
            el = time.time() - t0
            print(f"  {n_done}/{len(days)} 日 ({day}) 経過 {el:.0f}s", flush=True)
    return {"agg_days_missing": sorted(agg_missing),
            "bitflyer_years_missing": bf["years_missing"]}


def concat_rows(out_dir: Path, days: list[str]) -> dict[int, Path]:
    work = out_dir / "chunks"
    paths = {}
    counts = {}
    handles = {}
    for gap in (60, 30, 180):
        p = out_dir / f"rows_gap{gap}.csv.gz"
        paths[gap] = p
        handles[gap] = gz_open_w(Path(str(p) + ".part"))
        w = csv.writer(handles[gap])
        w.writerow(ROW_COLUMNS)
        handles[gap] = (handles[gap], w)
        counts[gap] = 0
    for day in days:
        cp = work / f"{day}.csv.gz"
        with gzip.open(cp, "rt", newline="") as fh:
            rd = csv.reader(fh)
            next(rd)
            for row in rd:
                gap = int(row[0])
                handles[gap][1].writerow(row[1:])
                counts[gap] += 1
    for gap in (60, 30, 180):
        handles[gap][0].close()
        Path(str(paths[gap]) + ".part").replace(paths[gap])
    print("行数 " + " / ".join(f"gap{g} {counts[g]}" for g in (60, 30, 180)), flush=True)
    return paths


# ===========================================================================
# 集計(E0〜E4)
# ===========================================================================
class Rows:
    """`rows_gap*.csv.gz` を Δ ごとに開いたもの(1 周目の表と `cascade_id` で突き合わせる)。"""

    def __init__(self, path: Path, table: RunTable):
        per: dict[int, dict] = {}
        with gzip.open(path, "rt", newline="") as fh:
            rd = csv.DictReader(fh)
            for r in rd:
                d = int(r["delta_sec"])
                b = per.setdefault(d, {k: [] for k in ROW_COLUMNS})
                for k in ROW_COLUMNS:
                    b[k].append(r[k])
        self.delta: dict[int, dict] = {}
        pos = {cid: i for i, cid in enumerate(table.cascade_id.tolist())}
        for d, b in per.items():
            n = len(b["kind"])
            blk = {
                "kind": np.array(b["kind"], dtype=object),
                "cascade_id": np.array(b["cascade_id"], dtype=object),
                "day": np.array(b["day"], dtype=object),
                "side": np.array(b["side"], dtype=object),
                "anchor_lag_ms": np.array([_f(x) for x in b["anchor_lag_ms"]]),
                "anchor_ts_ms": np.array([_f(x) for x in b["anchor_ts_ms"]]),
                "bounce": np.array([_f(x) for x in b["bounce"]]),
            }
            for h in HORIZONS_SEC:
                blk[f"r_{h}"] = np.array([_f(x) for x in b[f"r_{h}"]])
                blk[f"bf_r_{h}"] = np.array([_f(x) for x in b[f"bf_r_{h}"]])
            blk["_tpos"] = np.array([pos.get(c, -1) for c in b["cascade_id"]], dtype=int)
            blk["_n"] = n
            self.delta[d] = blk
        self.table = table

    def mask(self, d: int, kind: str) -> np.ndarray:
        return self.delta[d]["kind"] == kind


def e1_groups(rows: Rows, d: int) -> list[tuple[str, np.ndarray]]:
    blk = rows.delta[d]
    t = rows.table
    is_liq = blk["kind"] == KIND_LIQ
    tpos = blk["_tpos"]
    has = np.zeros(blk["_n"], dtype=bool)
    ok = tpos >= 0
    has[ok] = t.liq_has_matched[tpos[ok]]
    return [
        ("清算 全体", is_liq),
        ("清算 対照(ii)が付いた束", is_liq & has),
        ("清算 対照(ii)が付かない束", is_liq & ~has),
        ("対照(i) 一様", blk["kind"] == KIND_UNIFORM),
        ("対照(ii) 薄さ合わせ", blk["kind"] == KIND_MATCHED),
    ]


def make_e0(rows: Rows) -> list[dict]:
    out = []
    for d in DELTAS_SEC:
        blk = rows.delta[d]
        for kind in KINDS:
            m = blk["kind"] == kind
            lag = blk["anchor_lag_ms"][m]
            fin = lag[np.isfinite(lag)]
            n_nan = int(m.sum() - fin.size)
            out.append({
                "Δ(秒)": d, "kind": KIND_LABEL[kind], "行数": int(m.sum()),
                "lag==0 の割合": float((fin == 0).mean()) if fin.size else NAN,
                "lag 中央値(ms)": float(np.median(fin)) if fin.size else NAN,
                "lag p90(ms)": float(np.percentile(fin, 90)) if fin.size else NAN,
                "起点が引けない行(NaN)": n_nan,
            })
    return out


def make_e1(rows: Rows, h: int = E1_HORIZON_SEC) -> list[dict]:
    out = []
    for d in DELTAS_SEC:
        blk = rows.delta[d]
        for name, m in e1_groups(rows, d):
            v = blk[f"r_{h}"][m]
            days = blk["day"][m]
            mean, se, naive, n, g = mean_se_cluster(v, days)
            neg, zero, pos = three_way(v)
            bm, _, _, bn, _ = mean_se_cluster(blk["bounce"][m], days)
            fm, _, _, fn, _ = mean_se_cluster(blk[f"bf_r_{h}"][m], days)
            out.append({
                "Δ(秒)": d, "群": name, "平均(bp)": mean, "日クラスタ SE": se,
                "naive SE": naive, "n": n, "日数": g,
                "r<0": neg, "r=0": zero, "r>0": pos,
                "bounce 平均(bp)": bm, "bounce n": bn,
                "bitFlyer 平均(bp)": fm, "bitFlyer n": fn,
            })
    return out


def make_e2(rows: Rows) -> list[dict]:
    out = []
    for d in E2_DELTAS:
        blk = rows.delta[d]
        for kind in KINDS:
            m = blk["kind"] == kind
            days = blk["day"][m]
            for h in HORIZONS_SEC:
                v = blk[f"r_{h}"][m]
                mean, se, naive, n, g = mean_se_cluster(v, days)
                neg, zero, pos = three_way(v)
                out.append({
                    "Δ(秒)": d, "kind": KIND_LABEL[kind], "h(秒)": h,
                    "平均(bp)": mean, "日クラスタ SE": se, "naive SE": naive,
                    "n": n, "日数": g, "r<0": neg, "r=0": zero, "r>0": pos,
                })
    return out


def make_e3(rows_by_gap: dict[int, Rows], h: int = E1_HORIZON_SEC) -> list[dict]:
    out = []
    for gap in (30, 60, 180):
        rows = rows_by_gap[gap]
        for d in DELTAS_SEC:
            blk = rows.delta[d]
            for name, m in e1_groups(rows, d):
                v = blk[f"r_{h}"][m]
                days = blk["day"][m]
                mean, se, naive, n, g = mean_se_cluster(v, days)
                neg, zero, pos = three_way(v)
                out.append({
                    "gap(秒)": gap, "Δ(秒)": d, "群": name, "平均(bp)": mean,
                    "日クラスタ SE": se, "naive SE": naive, "n": n, "日数": g,
                    "r<0": neg, "r=0": zero, "r>0": pos,
                    "E1 の再掲": "はい" if gap == 60 else "",
                })
    return out


def attribute_groups(table: RunTable) -> list[dict]:
    """探索段 1 と同じ 30 群(3 分位 × 8 + 側 2 + 時刻帯 4)。切り値は清算行から。"""
    liq = np.flatnonzero(table.kind == KIND_LIQ)
    groups = []
    for name, col, take_abs in ATTRS_NUM:
        v_all = table.num(col)
        v = v_all[liq]
        if take_abs:
            v = np.abs(v)
        lo, hi = tertile_cuts(v)
        bounds = {1: (NAN, lo), 2: (lo, hi), 3: (hi, NAN)}
        for q, label in TERTILE_LABELS:
            sel = tertile_mask(v, lo, hi, q)
            ids = set(table.cascade_id[liq][sel].tolist())
            groups.append({"属性": name, "群": label, "下限": bounds[q][0],
                           "上限": bounds[q][1], "ids": ids})
    side_liq = table.side[liq]
    for s in ("SELL", "BUY"):
        ids = set(table.cascade_id[liq][side_liq == s].tolist())
        groups.append({"属性": ATTR_SIDE, "群": s, "下限": NAN, "上限": NAN, "ids": ids})
    hour = (table.time_ms[liq] // 3_600_000) % 24
    for label, a0, a1 in HOUR_BANDS:
        sel = (hour >= a0) & (hour < a1)
        ids = set(table.cascade_id[liq][sel].tolist())
        groups.append({"属性": ATTR_HOUR, "群": label, "下限": float(a0),
                       "上限": float(a1), "ids": ids})
    return groups


def make_e4(rows: Rows, h: int = E1_HORIZON_SEC) -> tuple[list[dict], list[str]]:
    groups = attribute_groups(rows.table)
    same: dict[int, list[int]] = {}
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            if groups[i]["ids"] and groups[i]["ids"] == groups[j]["ids"]:
                same.setdefault(i, []).append(j)
                same.setdefault(j, []).append(i)
    notes = []
    for i, js in sorted(same.items()):
        for j in js:
            if i < j:
                notes.append(
                    f"{groups[i]['属性']} / {groups[i]['群']} と "
                    f"{groups[j]['属性']} / {groups[j]['群']} は同じ {len(groups[i]['ids'])} 行")
    out = []
    for d in E4_DELTAS:
        blk = rows.delta[d]
        is_liq = blk["kind"] == KIND_LIQ
        cid = blk["cascade_id"]
        for gi, g in enumerate(groups):
            ids = g["ids"]
            m = is_liq & np.array([c in ids for c in cid.tolist()], dtype=bool)
            v = blk[f"r_{h}"][m]
            days = blk["day"][m]
            mean, se, naive, n, ndays = mean_se_cluster(v, days)
            neg, zero, pos = three_way(v)
            note = ""
            if gi in same:
                note = " / ".join(
                    f"{groups[j]['属性']}:{groups[j]['群']}" for j in same[gi])
            out.append({
                "属性": g["属性"], "群": g["群"], "Δ(秒)": d,
                "下限": g["下限"], "上限": g["上限"],
                "平均(bp)": mean, "日クラスタ SE": se, "naive SE": naive,
                "n": n, "含む日数": ndays, "r<0": neg, "r=0": zero, "r>0": pos,
                "同一行の群": note,
            })
    return out, notes


def reference_uniform_by_day(rows: Rows, d: int, h: int) -> dict:
    """参考: 「日ごとの一様行の平均 × 束の符号」(反証者が事後にやった形)。

    一様行の `r` は組んだ束の符号が付いているので、まず符号を外して生に戻し、
    日ごとに平均を取り、束の行の符号を掛ける。
    """
    blk = rows.delta[d]
    t = rows.table
    pos = {c: i for i, c in enumerate(t.cascade_id.tolist())}
    uni = blk["kind"] == KIND_UNIFORM
    liq = blk["kind"] == KIND_LIQ
    sgn_u = np.array([REACT_SIGN.get(s, NAN) for s in blk["side"][uni]], dtype=float)
    raw = blk[f"r_{h}"][uni] / sgn_u
    days_u = blk["day"][uni]
    acc: dict = defaultdict(list)
    for x, dd in zip(raw.tolist(), days_u.tolist()):
        if math.isfinite(x):
            acc[dd].append(x)
    daymean = {k: sum(v) / len(v) for k, v in acc.items() if v}
    vals, days = [], []
    for s, dd in zip(blk["side"][liq].tolist(), blk["day"][liq].tolist()):
        dm = daymean.get(dd)
        sg = REACT_SIGN.get(s, NAN)
        if dm is None or not math.isfinite(sg):
            continue
        vals.append(sg * dm)
        days.append(dd)
    m, se, naive, n, g = mean_se_cluster(np.array(vals), np.array(days, dtype=object))
    del pos
    return {"平均(bp)": m, "日クラスタ SE": se, "naive SE": naive, "n": n, "日数": g}


# ===========================================================================
# 清算行の重複(設計 §6、反証者 #8)
# ===========================================================================
def liq_duplicate_probe(data_root: Path, days: list[str]) -> dict:
    root = Path(data_root) / "liquidationSnapshot" / base.SYMBOL
    out = {
        "方法": ("生の zip を直接開き、ヘッダを除く全行を全 10 列のタプルで数える。"
               "ローダ `src/bot/research/liq_response.py: _read_binance_cm_rows` は "
               "`root.glob('*-liquidationSnapshot-*.zip')` で zip を集め、"
               "各 zip の中の `.csv` で終わる名前が 1 本であることを assert してから読む。"),
        "日ごと": [],
    }
    zips = sorted(root.glob("*-liquidationSnapshot-*.zip"))
    all_files = sorted(p.name for p in root.iterdir() if p.is_file())
    checksum = [n for n in all_files if n.endswith(".CHECKSUM")]
    out["ローダが集める zip の本数"] = len(zips)
    out["ディレクトリ内のファイル総数"] = len(all_files)
    out["CHECKSUM ファイルの本数"] = len(checksum)
    out["CHECKSUM が glob に入るか"] = any(
        n.endswith(".CHECKSUM") for n in (p.name for p in zips))
    for day in days:
        p = root / f"{base.SYMBOL}-liquidationSnapshot-{day}.zip"
        if not p.exists():
            out["日ごと"].append({"日": day, "備考": "zip が無い"})
            continue
        with zipfile.ZipFile(p) as zf:
            names = zf.namelist()
            csvs = [n for n in names if n.endswith(".csv")]
            with zf.open(csvs[0]) as fh:
                rd = csv.reader(io.TextIOWrapper(fh, encoding="utf-8"))
                header = next(rd, None)
                rows = [tuple(r) for r in rd if r]
        cnt: dict = defaultdict(int)
        for r in rows:
            cnt[r] += 1
        mult: dict = defaultdict(int)
        for c in cnt.values():
            mult[c] += 1
        # 使う 5 列だけで見た一意数(全列一致との差 = 他の列だけが違う行)
        five = {(r[0], r[1], r[4], r[5], r[6]) for r in rows}
        out["日ごと"].append({
            "日": day,
            "zip の中のファイル数": len(names),
            "zip の中の .csv の数": len(csvs),
            "ヘッダ": header[:3] if header else None,
            "raw の行数(ヘッダ除く)": len(rows),
            "全列一致で一意にした行数": len(cnt),
            "多重度の内訳": dict(sorted(mult.items())),
            "raw / 一意": round(len(rows) / len(cnt), 6) if cnt else None,
            "使う 5 列だけで一意にした行数": len(five),
        })
    out["読み取れたこと"] = (
        "1 日の zip の中の csv は 1 本で、ローダはその 1 本だけを読む"
        "(`assert len(names) == 1`)。CHECKSUM は拡張子が `.CHECKSUM` なので "
        "`*-liquidationSnapshot-*.zip` の glob に入らない。"
        "したがって**同じ行を 2 つの経路から読んでいる形跡はこの 3 日では無い**。"
        "raw が一意の約 2 倍になるのは、1 本の csv の中に全列まったく同じ行が "
        "複数回入っているためである(この 3 日で観測した多重度は上の『多重度の内訳』のとおり)。"
        "**これは 3 日ぶんの実測で、472 日すべてを数え直したものではない(未確認)。**"
        "全 472 日の多重度の内訳はこの道具では数えていない(未確認)。")
    return out


# ===========================================================================
# 表の書き出し
# ===========================================================================
def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    cols = list(rows[0].keys())
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in rows:
            w.writerow([_fmt(r[c], 6) if isinstance(r[c], float) else r[c]
                        for c in cols])


def md_table(rows: list[dict]) -> str:
    if not rows:
        return "(行なし)\n"
    cols = list(rows[0].keys())
    out = ["| " + " | ".join(cols) + " |",
           "|" + "|".join(["---"] * len(cols)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(
            _fmt(r[c], 4) if isinstance(r[c], float) else str(r[c])
            for c in cols) + " |")
    return "\n".join(out) + "\n"


# ===========================================================================
# main
# ===========================================================================
def calendar_gaps(days: list[str]) -> list[str]:
    d0 = _dt.date.fromisoformat(days[0])
    d1 = _dt.date.fromisoformat(days[-1])
    have = set(days)
    out = []
    d = d0
    while d <= d1:
        if d.isoformat() not in have:
            out.append(d.isoformat())
        d += _dt.timedelta(days=1)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    ap.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    ap.add_argument("--bitflyer-dir", type=Path, default=DEFAULT_BITFLYER_DIR)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stage", choices=("rows", "tables", "all"), default="all")
    ap.add_argument("--limit-days", type=int, default=0,
                    help="先頭 N 日だけ(試験用。0 = 全部)")
    ap.add_argument("--progress-every", type=int, default=20)
    a = ap.parse_args(argv)

    t0 = time.time()
    a.out.mkdir(parents=True, exist_ok=True)
    tables = {run: RunTable(a.runs_dir / run) for run in RUNS}
    days = tables["gap60_w8"].days()
    if a.limit_days:
        days = days[: a.limit_days]
    print(f"走行 {list(tables)} / 日 {len(days)}", flush=True)

    note_rows = {}
    if a.stage in ("rows", "all"):
        note_rows = stage_rows(tables, a.out, a.data_root, a.bitflyer_dir, days,
                               a.progress_every)
        concat_rows(a.out, days)
    if a.stage == "rows":
        return 0

    rows_by_gap = {}
    for run in RUNS:
        gap = GAP_OF_RUN[run]
        rows_by_gap[gap] = Rows(a.out / f"rows_gap{gap}.csv.gz", tables[run])
    main_rows = rows_by_gap[60]

    e0 = make_e0(main_rows)
    e1 = make_e1(main_rows)
    e2 = make_e2(main_rows)
    e3 = make_e3(rows_by_gap)
    e4, e4_notes = make_e4(main_rows)
    write_csv(a.out / "e0_anchor_lag.csv", e0)
    write_csv(a.out / "e1_delta.csv", e1)
    write_csv(a.out / "e2_shape.csv", e2)
    write_csv(a.out / "e3_gap.csv", e3)
    write_csv(a.out / "e4_attributes.csv", e4)

    ref = {f"Δ={d}": reference_uniform_by_day(main_rows, d, REF_HORIZON_SEC)
           for d in DELTAS_SEC}

    missing_cal = calendar_gaps(days)
    dup = liq_duplicate_probe(a.data_root, ["2023-06-27", "2024-01-15", "2024-10-01"])

    inputs = {}
    for run in RUNS:
        p = a.runs_dir / run / "table.csv"
        inputs[str(p.relative_to(REPO_ROOT))] = md5_of(p)

    per_gap = {}
    for gap in (60, 30, 180):
        r = rows_by_gap[gap]
        t = r.table
        blk = r.delta[0]
        miss = {}
        for kind in KINDS:
            m = blk["kind"] == kind
            miss[KIND_LABEL[kind]] = {
                "行数(Δ=0)": int(m.sum()),
                "起点が引けない(Δ=0)": int(np.sum(~np.isfinite(blk["anchor_ts_ms"][m]))),
                f"r_{E1_HORIZON_SEC} が NaN(Δ=0)": int(
                    np.sum(~np.isfinite(blk[f"r_{E1_HORIZON_SEC}"][m]))),
                f"r_{max(HORIZONS_SEC)} が NaN(Δ=0)": int(
                    np.sum(~np.isfinite(blk[f"r_{max(HORIZONS_SEC)}"][m]))),
                f"bf_r_{E1_HORIZON_SEC} が NaN(Δ=0)": int(
                    np.sum(~np.isfinite(blk[f"bf_r_{E1_HORIZON_SEC}"][m]))),
            }
        per_gap[f"gap{gap}"] = {
            "1 周目の表の行数": {"liq": t.n_liq, "control_uniform": t.n_uniform,
                         "control_matched": t.n_matched},
            "対照(i) で落とした末尾の余り": t.n_uniform_dropped,
            "対照(i) で落とした日ごとの数": dict(sorted(t.uniform_dropped_by_day.items())),
            "対照(ii) で相手が主表に居ない行": t.n_matched_partner_missing,
            "この段の行数(全 Δ)": sum(r.delta[d]["_n"] for d in DELTAS_SEC),
            "欠測": miss,
        }

    summary = {
        "実行時刻(UTC)": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "経過秒": round(time.time() - t0, 1),
        "設計": "docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE2_DESIGN_2026-09-19.md",
        "パラメータ": {
            "Δ(秒)": list(DELTAS_SEC), "h(秒)": list(HORIZONS_SEC),
            "走行": list(RUNS), "起点の穴の上限(ms)": STALENESS_MS,
            "E1 の h(秒)": E1_HORIZON_SEC, "E2 の Δ": list(E2_DELTAS),
            "E4 の Δ": list(E4_DELTAS),
            "符号": "SELL: −1 / BUY: +1(1 周目の reactdir と同じ向き。負 = 反転)",
            "対照(i) の符号": ("日ごとに束を start_ms 昇順・一様行を time_ms 昇順に並べ "
                       "i 番目どうしを 1 対 1。余った末尾の一様行は落とす"),
            "対照(ii) の符号": "matched_liq_id の相手の束の side",
        },
        "入力の MD5": inputs,
        "日数": len(days),
        "暦の日数(最初〜最後)": (
            (_dt.date.fromisoformat(days[-1]) - _dt.date.fromisoformat(days[0])).days + 1),
        "欠けた日": missing_cal,
        "欠けた日の数": len(missing_cal),
        "走行ごと": per_gap,
        "約定が読めなかった日": note_rows.get("agg_days_missing", "(この走行では rows 段を回していない)"),
        "bitFlyer の無い年": note_rows.get("bitflyer_years_missing", "(同上)"),
        "参考: 日ごとの一様行の平均 × 束の符号(h=14400 秒)": ref,
        "E4 の同一行の群": e4_notes,
        "表の行数": {"E0": len(e0), "E1": len(e1), "E2": len(e2),
                 "E3": len(e3), "E4": len(e4),
                 "合計": len(e0) + len(e1) + len(e2) + len(e3) + len(e4)},
        "清算行の重複の確認": dup,
    }
    txt = json.dumps(summary, ensure_ascii=False, indent=2)
    check_no_banned(txt, "summary.json")
    (a.out / "summary.json").write_text(txt)

    md = [f"# O3C SIGNAL 探索段 2 の表({days[0]} 〜 {days[-1]}、{len(days)} 日)", "",
          f"- 設計: `{summary['設計']}`",
          f"- Δ(秒) = {list(DELTAS_SEC)} / h(秒) = {list(HORIZONS_SEC)}",
          f"- 欠けた日({len(missing_cal)} 日): " + ", ".join(missing_cal), "",
          "## E0 起点のそろい方(`anchor_lag_ms`)", "", md_table(e0), "",
          "## E1 Δ ごとの h=60 秒(gap 60)", "", md_table(e1), "",
          "## E2 h の形(Δ = 0 / 10 / 60、gap 60)", "", md_table(e2), "",
          "## E3 束ね方の感度(h=60 秒)", "", md_table(e3), "",
          "## E4 属性(清算側、h=60 秒、gap 60)", "", md_table(e4), "",
          "## 参考: 日ごとの一様行の平均 × 束の符号(h=14400 秒)", "",
          md_table([{"Δ(秒)": d, **ref[f"Δ={d}"]} for d in DELTAS_SEC]), ""]
    mdtxt = "\n".join(md)
    check_no_banned(mdtxt, "tables.md")
    (a.out / "tables.md").write_text(mdtxt)

    names = ["rows_gap60.csv.gz", "rows_gap30.csv.gz", "rows_gap180.csv.gz",
             "e0_anchor_lag.csv", "e1_delta.csv", "e2_shape.csv", "e3_gap.csv",
             "e4_attributes.csv", "tables.md", "summary.json"]
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

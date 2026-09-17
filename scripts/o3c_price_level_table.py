#!/usr/bin/env python3
"""O-3c 手順 1「標本走行」: 価格帯ごとの約定量の積み上げと清算価格の位置関係の観測表。

設計: docs/PHASE2/O3C/PRICE_LEVEL/DESIGN_2026-09-17.md(§1 単位と量 / §2 表の列 / §3 手順 1)

このスクリプトは**観測表を作るだけ**である。判定(予測できる/できない、使える/使えない)は
一切書かない。清算行と対照行が同じ列を持つ形で並べ、分位を summary.json に出す。

データ:
  backtest_data/binance_cm_o3c_20260913/aggTrades/BTCUSD_PERP/BTCUSD_PERP-aggTrades-<日>.zip
  backtest_data/binance_cm_o3c_20260913/liquidationSnapshot/BTCUSD_PERP/
      BTCUSD_PERP-liquidationSnapshot-<日>.zip
zip は展開せず zipfile から直接読む。

使い方:
  python3 scripts/o3c_price_level_table.py \
      --days 2023-06-25,2023-06-26,2024-02-19,2024-02-20,2024-10-13,2024-10-14 \
      --out-dir backtest_data/o3c_price_level_sample_20260917

`--liq-price-field` の既定は `average_price`(実際に約定した価格)。設計 §2 は `p_liq` に
`price` を置いていたが、`price` は強制決済注文の**指値**で直前価格から ±35〜40bp ずれた帯に
なることが 2026-09-17 の標本走行で分かったため、リードの指示で既定を変えた。
`--liq-price-field price` で従来の指値版も出せる。
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import math
import random
import time
import zipfile
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = REPO_ROOT / "backtest_data" / "binance_cm_o3c_20260913"
SYMBOL = "BTCUSD_PERP"

# `p_liq` に入れる liquidationSnapshot の列。
# `price` は強制決済注文の**指値**で、直前価格から ±35〜40bp ずれた帯になる(2026-09-17 実測)。
# 実際に約定した価格は `average_price` なので、既定はこちら(リードの指示、2026-09-17)。
LIQ_PRICE_FIELDS = ("price", "average_price")
DEFAULT_LIQ_PRICE_FIELD = "average_price"

# 設計 §2 の列 + day。列の順番はここで固定する。
COLUMNS = [
    "kind",
    "time_ms",
    "side",
    "qty",
    "p_liq",
    "p_avg",
    "p0",
    "bin_pct",
    "dist_node_bp",
    "dist_gap_bp",
    "vol_between_ratio",
    "dist_vwap_bp",
    "n_bins",
    "total_qty",
    "day",
]

# 分位を取る列(数値列のみ)。
QUANTILE_COLUMNS = [
    "qty",
    "p_liq",
    "p0",
    "bin_pct",
    "dist_node_bp",
    "dist_gap_bp",
    "vol_between_ratio",
    "dist_vwap_bp",
    "n_bins",
    "total_qty",
]

QUANTILES = [5, 25, 50, 75, 95]

CONTROL_GAP_MS = 5 * 60 * 1000  # 設計 §1「清算から ±5 分以上離れた時刻」
MS_PER_DAY = 24 * 60 * 60 * 1000


# --------------------------------------------------------------------------
# ビン(対数ビン、幅 bin_pct %)
# --------------------------------------------------------------------------


def log_step(bin_pct: float) -> float:
    """対数ビンの刻み log(1 + b)。設計 §1 の floor(log(price) / log(1 + 0.001)) の 1 + b の部分。"""
    return math.log1p(bin_pct / 100.0)


def bin_index(price: float, step: float) -> int:
    """価格 -> ビン番号。floor(log(price) / log(1 + b))。"""
    return int(math.floor(math.log(price) / step))


def bin_index_array(prices: np.ndarray, step: float) -> np.ndarray:
    return np.floor(np.log(prices) / step).astype(np.int64)


def bin_center_price(idx: int | np.ndarray, step: float):
    """ビンの代表価格。ビン [exp(k*step), exp((k+1)*step)) の対数中心 exp((k+0.5)*step)。

    設計に代表価格の指定は無い(該当語なし)。対数ビンなので対数中心を採る。
    """
    return np.exp((np.asarray(idx, dtype=np.float64) + 0.5) * step)


# --------------------------------------------------------------------------
# プロファイルの統計(設計 §1 ビンの統計 / §2 の列)
# --------------------------------------------------------------------------


def _ceil_tenth(n: int) -> int:
    """上位/下位 10% のビン本数。少なくとも 1 本。"""
    return max(1, -(-n // 10))


def _nearest_signed_bp(
    cand_bins: np.ndarray, lo_bin: int, step: float, p_ref: float
) -> float:
    """候補ビン群のうち p_ref に最も近いものまでの符号付き bp。

    符号は (p_target - p_ref) / p_ref * 1e4。同距離なら価格の低いビン(番号の小さい方)を採る。
    """
    centers = bin_center_price(cand_bins.astype(np.int64) + lo_bin, step)
    d = centers - p_ref
    order = np.lexsort((cand_bins, np.abs(d)))
    return float(d[order[0]] / p_ref * 1e4)


def profile_stats(
    qty: np.ndarray,
    lo_bin: int,
    step: float,
    p_liq: float,
    p0: float,
) -> dict:
    """範囲 [lo_bin, lo_bin+len(qty)-1] のプロファイルから設計 §2 の列を計算する。

    qty[i] = ビン (lo_bin + i) の数量。範囲 = W 内の最安値〜最高値であり、
    **数量 0 のビンも範囲内にそのまま含める**(空白として数える)。
    """
    qty = np.asarray(qty, dtype=np.float64)
    n = int(qty.size)
    if n == 0:
        raise ValueError("プロファイルが空")
    total = float(qty.sum())
    k = _ceil_tenth(n)
    idx = np.arange(n)

    # ノード = 数量の上位 10% のビン / 空白 = 下位 10% のビン。
    # 同量のときはビン番号の小さい順(決定的にするため)。
    node_rel = np.lexsort((idx, -qty))[:k]
    gap_rel = np.lexsort((idx, qty))[:k]

    b_liq = bin_index(p_liq, step)
    rel_liq = b_liq - lo_bin
    if 0 <= rel_liq < n:
        q_liq = float(qty[rel_liq])
    else:
        # p_liq が W 内の値幅の外(範囲外)。そのビンの数量は 0 として扱う。
        q_liq = 0.0
    bin_pct = float((qty < q_liq).sum()) / n * 100.0

    dist_node_bp = _nearest_signed_bp(node_rel, lo_bin, step, p_liq)
    dist_gap_bp = _nearest_signed_bp(gap_rel, lo_bin, step, p_liq)

    # p0〜p_liq の間の数量(両端のビンを含む)。設計に端の扱いの指定は無い(該当語なし)。
    b0 = bin_index(p0, step)
    a, b = sorted((b0 - lo_bin, rel_liq))
    a = max(a, 0)
    b = min(b, n - 1)
    between = float(qty[a : b + 1].sum()) if a <= b else 0.0
    vol_between_ratio = between / total if total > 0 else float("nan")

    # 重心 = プロファイルの数量加重平均価格(ビンの代表価格を使う)。
    centers = bin_center_price(np.arange(lo_bin, lo_bin + n), step)
    centroid = float((centers * qty).sum() / total) if total > 0 else float("nan")
    dist_vwap_bp = (centroid - p_liq) / p_liq * 1e4 if total > 0 else float("nan")

    return {
        "bin_pct": bin_pct,
        "dist_node_bp": dist_node_bp,
        "dist_gap_bp": dist_gap_bp,
        "vol_between_ratio": vol_between_ratio,
        "dist_vwap_bp": dist_vwap_bp,
        "n_bins": n,
        "total_qty": total,
        "p_liq_in_range": bool(0 <= rel_liq < n),
    }


# --------------------------------------------------------------------------
# 対照時刻(設計 §1 対照)
# --------------------------------------------------------------------------


def allowed_intervals(
    liq_times_ms: Sequence[int], day_start_ms: int, day_end_ms: int, gap_ms: int
) -> list[tuple[int, int]]:
    """[day_start, day_end) から ∪[t-gap, t+gap] を取り除いた区間の一覧。"""
    blocked: list[tuple[int, int]] = []
    for t in sorted(liq_times_ms):
        lo, hi = t - gap_ms, t + gap_ms
        if hi <= day_start_ms or lo >= day_end_ms:
            continue
        lo = max(lo, day_start_ms)
        hi = min(hi, day_end_ms)
        if blocked and lo <= blocked[-1][1]:
            blocked[-1] = (blocked[-1][0], max(blocked[-1][1], hi))
        else:
            blocked.append((lo, hi))
    out: list[tuple[int, int]] = []
    cur = day_start_ms
    for lo, hi in blocked:
        if lo > cur:
            out.append((cur, lo))
        cur = max(cur, hi)
    if cur < day_end_ms:
        out.append((cur, day_end_ms))
    return [(a, b) for a, b in out if b > a]


def sample_control_times(
    liq_times_ms: Sequence[int],
    day_start_ms: int,
    day_end_ms: int,
    n: int,
    rng: random.Random,
    gap_ms: int = CONTROL_GAP_MS,
) -> list[int]:
    """同じ日の中で、どの清算からも ±gap 以上離れた時刻を一様に n 点引く。"""
    intervals = allowed_intervals(liq_times_ms, day_start_ms, day_end_ms, gap_ms)
    if not intervals:
        return []
    lengths = [b - a for a, b in intervals]
    total = sum(lengths)
    cum = np.cumsum(lengths)
    out: list[int] = []
    for _ in range(n):
        u = rng.random() * total
        i = int(np.searchsorted(cum, u, side="right"))
        i = min(i, len(intervals) - 1)
        base = intervals[i][0]
        off = u - (cum[i - 1] if i > 0 else 0.0)
        t = int(base + off)
        t = min(max(t, intervals[i][0]), intervals[i][1] - 1)
        out.append(t)
    return out


# --------------------------------------------------------------------------
# データ読み込み(zip から直接)
# --------------------------------------------------------------------------


def _zip_csv(path: Path, usecols: list[str], names: list[str]) -> pd.DataFrame:
    with zipfile.ZipFile(path) as z:
        name = z.namelist()[0]
        with z.open(name) as fh:
            head = fh.readline()
        has_header = names[0].encode() in head
        with z.open(name) as fh:
            if has_header:
                return pd.read_csv(fh, usecols=usecols)
            return pd.read_csv(fh, header=None, names=names, usecols=usecols)


AGG_NAMES = [
    "agg_trade_id",
    "price",
    "quantity",
    "first_trade_id",
    "last_trade_id",
    "transact_time",
    "is_buyer_maker",
]
LIQ_NAMES = [
    "time",
    "side",
    "order_type",
    "time_in_force",
    "original_quantity",
    "price",
    "average_price",
    "order_status",
    "last_fill_quantity",
    "accumulated_fill_quantity",
]


def agg_path(root: Path, day: str) -> Path:
    return root / "aggTrades" / SYMBOL / f"{SYMBOL}-aggTrades-{day}.zip"


def liq_path(root: Path, day: str) -> Path:
    return (
        root
        / "liquidationSnapshot"
        / SYMBOL
        / f"{SYMBOL}-liquidationSnapshot-{day}.zip"
    )


def load_agg_trades(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(transact_time[ms], price, quantity) を時刻の昇順で返す。"""
    df = _zip_csv(path, ["price", "quantity", "transact_time"], AGG_NAMES)
    t = df["transact_time"].to_numpy(dtype=np.int64)
    p = df["price"].to_numpy(dtype=np.float64)
    q = df["quantity"].to_numpy(dtype=np.float64)
    order = np.argsort(t, kind="stable")
    return t[order], p[order], q[order]


def load_liquidations(path: Path) -> pd.DataFrame:
    df = _zip_csv(
        path,
        ["time", "side", "original_quantity", "price", "average_price"],
        LIQ_NAMES,
    )
    return df.sort_values("time", kind="stable").reset_index(drop=True)


# --------------------------------------------------------------------------
# 1 日の処理
# --------------------------------------------------------------------------


def day_bounds_ms(day: str) -> tuple[int, int]:
    d = _dt.datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=_dt.timezone.utc)
    start = int(d.timestamp() * 1000)
    return start, start + MS_PER_DAY


def prev_day(day: str) -> str:
    d = _dt.datetime.strptime(day, "%Y-%m-%d").date() - _dt.timedelta(days=1)
    return d.isoformat()


def process_day(
    day: str,
    root: Path,
    window_hours: float,
    bin_pct: float,
    seed: int,
    agg_cache: dict | None = None,
    liq_price_field: str = DEFAULT_LIQ_PRICE_FIELD,
) -> tuple[list[dict], dict]:
    """1 日分の清算行 + 対照行を作る。戻り値は (行の一覧, その日のメモ)。

    liq_price_field: `p_liq` に入れる liquidationSnapshot の列。
      `average_price` = 実際に約定した価格(既定)。
      `price` = 強制決済注文の指値(直前価格から ±35〜40bp ずれた帯になる)。
    """
    if liq_price_field not in LIQ_PRICE_FIELDS:
        raise ValueError(f"--liq-price-field は {LIQ_PRICE_FIELDS} のどれか")
    step = log_step(bin_pct)
    window_ms = int(round(window_hours * 3600 * 1000))
    cache = agg_cache if agg_cache is not None else {}

    def agg(d: str):
        if d not in cache:
            cache[d] = load_agg_trades(agg_path(root, d))
        return cache[d]

    parts = []
    prev = prev_day(day)
    prev_present = agg_path(root, prev).exists()
    if prev_present:
        parts.append(agg(prev))
    parts.append(agg(day))
    times = np.concatenate([p[0] for p in parts])
    prices = np.concatenate([p[1] for p in parts])
    qtys = np.concatenate([p[2] for p in parts])
    order = np.argsort(times, kind="stable")
    times, prices, qtys = times[order], prices[order], qtys[order]

    liq_all = load_liquidations(liq_path(root, day))
    day_start, day_end = day_bounds_ms(day)

    # p_liq に使う列が空か 0 の行は落とす(件数は記録する)。
    chosen = pd.to_numeric(liq_all[liq_price_field], errors="coerce")
    keep = chosen.notna() & (chosen > 0)
    dropped = int((~keep).sum())
    liq = liq_all[keep].reset_index(drop=True)

    rng = random.Random(f"{seed}|{day}")
    # 除外区間は落とした行も含めた全清算時刻で作る(落ちた行も清算ではあるため)。
    ctrl_times = sample_control_times(
        liq_all["time"].tolist(), day_start, day_end, len(liq), rng
    )

    events: list[dict] = []
    for r in liq.itertuples(index=False):
        events.append(
            {
                "kind": "liq",
                "time_ms": int(r.time),
                "side": str(r.side),
                "qty": float(r.original_quantity),
                "p_liq": float(getattr(r, liq_price_field)),
                "p_avg": float(r.average_price),
            }
        )
    for t in ctrl_times:
        events.append(
            {
                "kind": "control",
                "time_ms": int(t),
                "side": "",
                "qty": "",
                "p_liq": None,  # p0 を入れる
                "p_avg": "",
            }
        )
    events.sort(key=lambda e: (e["time_ms"], e["kind"]))

    # 大域のビン範囲(読み込んだ約定の全体)にまたがる密な配列で窓を転がす。
    bins = bin_index_array(prices, step)
    gmin = int(bins.min())
    rel = (bins - gmin).astype(np.int64)
    width = int(rel.max()) + 1
    acc_q = np.zeros(width, dtype=np.float64)
    acc_c = np.zeros(width, dtype=np.int64)

    rows: list[dict] = []
    n_trades = times.size
    lo = hi = 0
    skipped_empty = 0
    out_of_range = 0
    for ev in events:
        t = ev["time_ms"]
        while hi < n_trades and times[hi] < t:
            acc_q[rel[hi]] += qtys[hi]
            acc_c[rel[hi]] += 1
            hi += 1
        left = t - window_ms
        while lo < hi and times[lo] < left:
            acc_q[rel[lo]] -= qtys[lo]
            acc_c[rel[lo]] -= 1
            lo += 1
        if lo >= hi:
            skipped_empty += 1
            continue
        nz = np.nonzero(acc_c)[0]
        r0, r1 = int(nz[0]), int(nz[-1])
        sub_q = acc_q[r0 : r1 + 1].copy()
        sub_c = acc_c[r0 : r1 + 1]
        sub_q[sub_c == 0] = 0.0  # 足し引きの端数が残らないようにする
        p0 = float(prices[hi - 1])
        p_liq = p0 if ev["p_liq"] is None else float(ev["p_liq"])
        if p_liq <= 0:
            skipped_empty += 1
            continue
        st = profile_stats(sub_q, gmin + r0, step, p_liq, p0)
        if not st["p_liq_in_range"]:
            out_of_range += 1
        rows.append(
            {
                "kind": ev["kind"],
                "time_ms": t,
                "side": ev["side"],
                "qty": ev["qty"],
                "p_liq": p_liq,
                "p_avg": ev["p_avg"],
                "p0": p0,
                "bin_pct": round(st["bin_pct"], 4),
                "dist_node_bp": round(st["dist_node_bp"], 4),
                "dist_gap_bp": round(st["dist_gap_bp"], 4),
                "vol_between_ratio": round(st["vol_between_ratio"], 6),
                "dist_vwap_bp": round(st["dist_vwap_bp"], 4),
                "n_bins": st["n_bins"],
                "total_qty": st["total_qty"],
                "day": day,
            }
        )

    note = {
        "day": day,
        "prev_day": prev,
        "prev_day_agg_present": prev_present,
        "liq_rows_in_file": int(len(liq_all)),
        "liq_rows_dropped_no_price": dropped,
        "liq_price_field": liq_price_field,
        "control_points_drawn": len(ctrl_times),
        "rows_written": len(rows),
        "rows_skipped_empty_window": skipped_empty,
        "rows_p_liq_outside_window_range": out_of_range,
        "agg_trades_loaded": int(n_trades),
    }
    if not prev_present:
        note["warning"] = (
            f"前日 {prev} の aggTrades zip が無いため、この日の早い時刻の窓は "
            f"{window_hours} 時間より短い(その日の最初の約定までしか遡れない)。"
        )
    return rows, note


# --------------------------------------------------------------------------
# 出力
# --------------------------------------------------------------------------


def _quantiles(df: pd.DataFrame) -> dict:
    out: dict = {}
    for col in QUANTILE_COLUMNS:
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty:
            out[col] = None
            continue
        out[col] = {
            f"q{q}": float(np.percentile(s.to_numpy(), q)) for q in QUANTILES
        }
    return out


def build_summary(
    df: pd.DataFrame, notes: list[dict], params: dict, elapsed_sec: float
) -> dict:
    liq = df[df["kind"] == "liq"]
    ctl = df[df["kind"] == "control"]
    summary = {
        "params": params,
        "elapsed_sec": round(elapsed_sec, 2),
        "rows_total": int(len(df)),
        "rows_liq": int(len(liq)),
        "rows_control": int(len(ctl)),
        "liq_rows_dropped_no_price": sum(
            int(n.get("liq_rows_dropped_no_price", 0)) for n in notes
        ),
        "rows_p_liq_outside_window_range": sum(
            int(n.get("rows_p_liq_outside_window_range", 0)) for n in notes
        ),
        "side_counts": {
            str(k): int(v) for k, v in liq["side"].value_counts().items()
        },
        "quantiles": {
            "liq": _quantiles(liq),
            "control": _quantiles(ctl),
        },
        "quantiles_by_side": {
            str(side): _quantiles(liq[liq["side"] == side])
            for side in sorted(liq["side"].dropna().unique())
        },
        "per_day": notes,
        "notes": [
            "観測表のみ。判定(予測できる/できない、使える/使えない)は書いていない。",
            "ノード = 数量の上位 10% のビン、空白 = 下位 10% のビン。"
            "範囲 = 窓内の最安値〜最高値で、数量 0 のビンも範囲内の空白として数える。",
            "dist_*_bp = (p_target - p_liq) / p_liq * 1e4(符号付き)。",
            "bin_pct = p_liq のビンより数量が少ないビンの割合 * 100。",
            "対照行は p_liq に p0(直前約定価格)を入れて同じ列を計算している。",
            "p_liq に入れた列は params.liq_price_field を見ること。"
            "average_price = 実際に約定した価格、price = 強制決済注文の指値。",
        ],
    }
    return summary


def write_md5sums(out_dir: Path, names: Iterable[str]) -> None:
    lines = []
    for n in names:
        h = hashlib.md5((out_dir / n).read_bytes()).hexdigest()
        lines.append(f"{h}  {n}\n")
    (out_dir / "MD5SUMS").write_text("".join(lines), encoding="utf-8")


def run(
    days: list[str],
    root: Path,
    out_dir: Path,
    window_hours: float,
    bin_pct: float,
    seed: int,
    liq_price_field: str = DEFAULT_LIQ_PRICE_FIELD,
) -> dict:
    t0 = time.time()
    cache: dict = {}
    all_rows: list[dict] = []
    notes: list[dict] = []
    for day in days:
        rows, note = process_day(
            day, root, window_hours, bin_pct, seed, cache, liq_price_field
        )
        all_rows.extend(rows)
        notes.append(note)
        print(
            f"[{day}] 清算 {note['liq_rows_in_file']} 件"
            f"(価格欠落で除外 {note['liq_rows_dropped_no_price']} 件)/ 対照 "
            f"{note['control_points_drawn']} 点 -> 行 {note['rows_written']}"
            f"(前日 aggTrades: {'有' if note['prev_day_agg_present'] else '無'})",
            flush=True,
        )
        # 直前 2 日分だけ保持してメモリを抑える
        keep = {day, prev_day(day)}
        if days.index(day) + 1 < len(days):
            nxt = days[days.index(day) + 1]
            keep |= {nxt, prev_day(nxt)}
        for k in list(cache):
            if k not in keep:
                del cache[k]

    df = pd.DataFrame(all_rows, columns=COLUMNS)
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "table.csv", index=False)
    elapsed = time.time() - t0
    params = {
        "days": days,
        "window_hours": window_hours,
        "bin_pct": bin_pct,
        "seed": seed,
        "liq_price_field": liq_price_field,
        "control_gap_minutes": CONTROL_GAP_MS / 60000,
        "data_root": str(root),
        "symbol": SYMBOL,
        "design": "docs/PHASE2/O3C/PRICE_LEVEL/DESIGN_2026-09-17.md",
    }
    summary = build_summary(df, notes, params, elapsed)
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_md5sums(out_dir, ["table.csv", "summary.json"])
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", required=True, help="清算を置く日(カンマ区切り、YYYY-MM-DD)")
    ap.add_argument("--window-hours", type=float, default=24.0)
    ap.add_argument("--bin-pct", type=float, default=0.1)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument(
        "--liq-price-field",
        choices=LIQ_PRICE_FIELDS,
        default=DEFAULT_LIQ_PRICE_FIELD,
        help="p_liq に入れる列。average_price = 約定価格(既定)、price = 強制決済の指値",
    )
    ap.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    a = ap.parse_args(argv)

    days = [d.strip() for d in a.days.split(",") if d.strip()]
    root = Path(a.data_root)
    for d in days:
        for p in (agg_path(root, d), liq_path(root, d)):
            if not p.exists():
                raise SystemExit(f"必要な zip が無い: {p}")
        if not agg_path(root, prev_day(d)).exists():
            print(f"[注意] 前日 {prev_day(d)} の aggTrades が無い。{d} の窓は短くなる。")

    s = run(
        days,
        root,
        Path(a.out_dir),
        a.window_hours,
        a.bin_pct,
        a.seed,
        a.liq_price_field,
    )
    print(
        f"行 {s['rows_total']}(清算 {s['rows_liq']} / 対照 {s['rows_control']})"
        f" p_liq = {a.liq_price_field} / 所要 {s['elapsed_sec']} 秒 -> {a.out_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

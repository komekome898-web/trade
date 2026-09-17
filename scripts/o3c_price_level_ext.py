#!/usr/bin/env python3
"""O-3c 観測表の追加 2 本(2026-09-17、オーナー決定 L-191「(a)(b)(c) →全部やってよい」)。

既存の観測表(`scripts/o3c_price_level_table.py`、設計 `docs/PHASE2/O3C/PRICE_LEVEL/
DESIGN_2026-09-17.md`、全件の結果 `FULL_2026-09-17.md`)の `process_day` / `profile_stats` /
`sample_control_times` をそのまま使い、次の 2 本を出す。

  (a) `bundle`: 清算を 60 秒以内の間隔で束ね、**各束の最初の 1 件だけ**を清算行にした観測表。
      列は既存と同じ + `bundle_n_events` / `bundle_total_qty`。
  (b) `band`: 各正時に、直前 W の積み上げのノードから **SELL 帯 = N×(1−0.0056) の ±1 ビン /
      BUY 帯 = N×(1+0.0070) の ±1 ビン**を引き、次の 1 時間の清算がその帯に入った割合と、
      対照(帯が価格範囲に占める割合 / 同じ 1 時間の全約定が帯に入った割合)を並べる。

**観測表のみ。判定(予測できる/できない、当たる/当たらない、使える/使えない)は書かない。**

使い方:
  python3 scripts/o3c_price_level_ext.py bundle --days <日,...> --data-root <根> \
      --out-dir backtest_data/o3c_price_level_bundle_first_20260917
  python3 scripts/o3c_price_level_ext.py band --days <日,...> --data-root <根> \
      --out-dir backtest_data/o3c_price_level_band_20260917
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import o3c_price_level_table as base  # noqa: E402

# ---- (a) 束ね方 -----------------------------------------------------------
# `src/bot/research/liq_response.py: build_cascades` と同じ 60,000 ms。
BUNDLE_GAP_MS = 60_000

BUNDLE_COLUMNS = base.COLUMNS + [
    "bundle_n_events",
    "bundle_total_qty",
    # liquidationSnapshot は 1 件の清算が全列まったく同じ行として 2 回現れる(2026-09-17 実測)。
    # 束ね方(同一 ms)は変わらないが件数は 2 倍に出るので、一意にした件数も並べる。
    "bundle_n_events_dedup",
    "bundle_total_qty_dedup",
]

# ---- (b) 帯 ---------------------------------------------------------------
# `FULL_2026-09-17.md` §3 の side 別 `dist_node_bp` 中央値(SELL +56.4 / BUY −70.2)を
# そのまま使う。清算価格 = ノード × (1 + 符号付きオフセット) の形に直した値。
SIDE_OFFSET = {"SELL": -0.0056, "BUY": +0.0070}
BAND_HALF_BINS = 1  # 「±1 ビン」
HOUR_MS = 3600 * 1000

BAND_COLUMNS = [
    "day",
    "t_ms",
    "side",
    "n_nodes",
    "n_band_bins",
    "n_band_bins_in_range",
    "n_profile_bins",
    "band_coverage",
    "band_coverage_log",
    "n_liq",
    "n_liq_in_band",
    "in_band_rate",
    "n_trades",
    "n_trades_in_band",
    "trade_in_band_rate",
    "p0",
    "total_qty",
]


# --------------------------------------------------------------------------
# (a) 束の最初の 1 件だけの観測表
# --------------------------------------------------------------------------


def run_bundle(
    days: list[str],
    root: Path,
    out_dir: Path,
    window_hours: float,
    bin_pct: float,
    seed: int,
    gap_ms: int = BUNDLE_GAP_MS,
    dedup_liq: bool = False,
) -> dict:
    t0 = time.time()
    cache: dict = {}
    all_rows: list[dict] = []
    notes: list[dict] = []
    for i_day, day in enumerate(days):
        rows, note = base.process_day(
            day,
            root,
            window_hours,
            bin_pct,
            seed,
            cache,
            bundle_gap_ms=gap_ms,
            dedup_liq=dedup_liq,
        )
        all_rows.extend(rows)
        notes.append(note)
        print(
            f"[{day}] 清算 {note['liq_rows_in_file']} 件 -> 束 {note['bundles_in_file']} 個"
            f"(最初の 1 件に価格が無い束 {note['bundles_dropped_no_price']} 個)/ 対照 "
            f"{note['control_points_drawn']} 点 -> 行 {note['rows_written']}",
            flush=True,
        )
        keep = set(base.days_needed(day, window_hours))
        if i_day + 1 < len(days):
            keep |= set(base.days_needed(days[i_day + 1], window_hours))
        for k in list(cache):
            if k not in keep:
                del cache[k]

    df = pd.DataFrame(all_rows, columns=BUNDLE_COLUMNS)
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "table.csv", index=False)
    elapsed = time.time() - t0
    params = {
        "days": days,
        "window_hours": window_hours,
        "bin_pct": bin_pct,
        "prev_days_read_per_day": base.required_prev_days(window_hours),
        "seed": seed,
        "liq_price_field": base.DEFAULT_LIQ_PRICE_FIELD,
        "bundle_gap_ms": gap_ms,
        "dedup_liq": dedup_liq,
        "control_gap_minutes": base.CONTROL_GAP_MS / 60000,
        "data_root": str(root),
        "symbol": base.SYMBOL,
        "design": "docs/PHASE2/O3C/PRICE_LEVEL/DESIGN_2026-09-17.md",
        "extension": "docs/PHASE2/O3C/PRICE_LEVEL/EXT_2026-09-17.md",
    }
    summary = base.build_summary(df, notes, params, elapsed)
    summary["bundles_total"] = sum(int(n["bundles_in_file"]) for n in notes)
    summary["bundles_dropped_no_price"] = sum(
        int(n["bundles_dropped_no_price"]) for n in notes
    )
    summary["liq_rows_in_files"] = sum(int(n["liq_rows_in_file"]) for n in notes)
    summary["liq_rows_unique_in_files"] = sum(
        int(n["liq_rows_unique_in_file"]) for n in notes
    )

    liq = df[df["kind"] == "liq"]
    ctl = df[df["kind"] == "control"]
    n_ev = pd.to_numeric(liq["bundle_n_events"], errors="coerce").dropna()
    n_ev_d = pd.to_numeric(liq["bundle_n_events_dedup"], errors="coerce").dropna()
    for key, s in (("", n_ev), ("_dedup", n_ev_d)):
        summary[f"bundle_n_events{key}_quantiles"] = {
            f"q{q}": float(np.percentile(s.to_numpy(), q))
            for q in (5, 25, 50, 75, 90, 95, 99)
        }
        summary[f"bundle_n_events{key}_counts"] = {
            "eq1": int((s == 1).sum()),
            "ge2": int((s >= 2).sum()),
            "max": int(s.max()) if len(s) else 0,
        }

    def _medians(sub: pd.DataFrame) -> dict:
        out = {"n": int(len(sub))}
        if sub.empty:
            return out
        for col in ("bin_pct", "dist_node_bp", "dist_gap_bp", "dist_vwap_bp"):
            s = pd.to_numeric(sub[col], errors="coerce").dropna()
            out[f"{col}_median"] = float(np.median(s.to_numpy())) if len(s) else None
            if col.startswith("dist_"):
                out[f"abs_{col}_median"] = (
                    float(np.median(np.abs(s.to_numpy()))) if len(s) else None
                )
        bp = pd.to_numeric(sub["bin_pct"], errors="coerce").dropna().to_numpy()
        if len(bp):
            out["bin_pct_eq0_frac"] = float((bp == 0).mean())
            out["bin_pct_le10_frac"] = float((bp <= 10).mean())
        return out

    summary["medians"] = {
        "liq": _medians(liq),
        "control": _medians(ctl),
        "liq_by_side": {
            str(s): _medians(liq[liq["side"] == s])
            for s in sorted(liq["side"].dropna().unique())
        },
        "liq_bundle_n_events_eq1": _medians(liq[n_ev.reindex(liq.index) == 1]),
        "liq_bundle_n_events_ge2": _medians(liq[n_ev.reindex(liq.index) >= 2]),
        "liq_bundle_n_events_dedup_eq1": _medians(liq[n_ev_d.reindex(liq.index) == 1]),
        "liq_bundle_n_events_dedup_ge2": _medians(liq[n_ev_d.reindex(liq.index) >= 2]),
    }
    summary["notes"].append(
        "この表は束の最初の 1 件だけ。bundle_n_events / bundle_total_qty は束全体の件数と数量。"
    )
    summary["notes"].append(
        "liquidationSnapshot は 1 件の清算が全列まったく同じ行として 2 回現れる"
        "(全 472 日で 106,822 行 -> 一意 53,398 行、2026-09-17 実測)。"
        "bundle_n_events はファイルの行をそのまま数えた値、*_dedup は完全一致の行を"
        "1 回だけ数えた値。束の切れ目(同一 ms)はどちらでも変わらない。"
    )
    summary["notes"].append(
        "対照は『束の最初の時刻』から ±5 分以上離れた点を束と同数引いている。"
    )
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    base.write_md5sums(out_dir, ["table.csv", "summary.json"])
    return summary


# --------------------------------------------------------------------------
# (b) 帯で事前に当てる形
# --------------------------------------------------------------------------


def node_bins(qty: np.ndarray, lo_bin: int) -> np.ndarray:
    """数量の上位 10% のビン(`profile_stats` と同じ規則)の**絶対ビン番号**。"""
    qty = np.asarray(qty, dtype=np.float64)
    n = int(qty.size)
    k = base._ceil_tenth(n)
    idx = np.arange(n)
    rel = np.lexsort((idx, -qty))[:k]
    return np.sort(rel.astype(np.int64) + lo_bin)


def band_bins_for_side(
    nodes: np.ndarray, step: float, offset: float, half_bins: int = BAND_HALF_BINS
) -> np.ndarray:
    """ノード群 -> その side の帯に入るビン番号(重複を除いた昇順)。

    帯 = ノードの代表価格 N × (1 + offset) が入るビンの ±half_bins ビン。
    """
    if len(nodes) == 0:
        return np.empty(0, dtype=np.int64)
    centers = base.bin_center_price(nodes, step) * (1.0 + offset)
    mid = np.floor(np.log(centers) / step).astype(np.int64)
    out = np.concatenate(
        [mid + d for d in range(-half_bins, half_bins + 1)]
    )
    return np.unique(out)


def band_coverage(
    bands: np.ndarray, lo_bin: int, n_bins: int, step: float
) -> tuple[float, float, int]:
    """帯が価格範囲(プロファイルの最安値〜最高値)に占める割合。

    戻り値 (価格幅での割合, ビン本数での割合, 範囲内の帯ビン数)。
    範囲の外に出た帯は切り落とす(範囲に「占める割合」なので)。重なりは
    `np.unique` の段で 1 回だけ数えている。
    """
    hi_bin = lo_bin + n_bins - 1
    inside = bands[(bands >= lo_bin) & (bands <= hi_bin)]
    lo_price = math.exp(lo_bin * step)
    hi_price = math.exp((hi_bin + 1) * step)
    if len(inside) == 0:
        return 0.0, 0.0, 0
    w = np.exp((inside + 1) * step) - np.exp(inside * step)
    return (
        float(w.sum() / (hi_price - lo_price)),
        float(len(inside) / n_bins),
        int(len(inside)),
    )


def process_day_band(
    day: str,
    root: Path,
    window_hours: float,
    bin_pct: float,
    agg_cache: dict | None = None,
    half_bins: int = BAND_HALF_BINS,
    side_offset: dict[str, float] | None = None,
    dedup_liq: bool = False,
) -> tuple[list[dict], dict]:
    """1 日ぶん(正時 24 点 × side 2)の帯の行を作る。"""
    step = base.log_step(bin_pct)
    window_ms = int(round(window_hours * 3600 * 1000))
    cache = agg_cache if agg_cache is not None else {}

    def agg(d: str):
        if d not in cache:
            cache[d] = base.load_agg_trades(base.agg_path(root, d))
        return cache[d]

    prevs = base.prev_days(day, base.required_prev_days(window_hours))
    loaded_prev = [d for d in prevs if base.agg_path(root, d).exists()]
    missing_prev = [d for d in prevs if d not in loaded_prev]
    parts = [agg(d) for d in loaded_prev]
    parts.append(agg(day))
    if len(parts) == 1:
        times, prices, qtys = parts[0]
    else:
        times = np.concatenate([p[0] for p in parts])
        prices = np.concatenate([p[1] for p in parts])
        qtys = np.concatenate([p[2] for p in parts])
        if not bool(np.all(times[1:] >= times[:-1])):
            order = np.argsort(times, kind="stable")
            times, prices, qtys = times[order], prices[order], qtys[order]

    side_offset = SIDE_OFFSET if side_offset is None else side_offset
    liq_all = base.load_liquidations(base.liq_path(root, day), dedup=dedup_liq)
    p_liq_all = pd.to_numeric(liq_all["average_price"], errors="coerce")
    keep = p_liq_all.notna() & (p_liq_all > 0)
    liq_t = liq_all.loc[keep, "time"].to_numpy(dtype=np.int64)
    liq_p = p_liq_all[keep].to_numpy(dtype=np.float64)
    liq_side = liq_all.loc[keep, "side"].astype(str).to_numpy()
    liq_dropped = int((~keep).sum())

    day_start, day_end = base.day_bounds_ms(day)

    bins = base.bin_index_array(prices, step)
    gmin = int(bins.min())
    rel = (bins - gmin).astype(np.int64)
    width = int(rel.max()) + 1
    acc_q = np.zeros(width, dtype=np.float64)
    acc_c = np.zeros(width, dtype=np.int64)

    rows: list[dict] = []
    n_trades_all = times.size
    lo = hi = 0
    skipped_empty = 0
    for h in range(24):
        t = day_start + h * HOUR_MS
        t_end = min(t + HOUR_MS, day_end)
        while hi < n_trades_all and times[hi] < t:
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
        sub_q[sub_c == 0] = 0.0
        n_bins = int(sub_q.size)
        lo_bin = gmin + r0
        nodes = node_bins(sub_q, lo_bin)
        p0 = float(prices[hi - 1])
        total_qty = float(sub_q.sum())

        # 次の 1 時間の約定(帯の外の対照その 2)
        i0 = int(np.searchsorted(times, t, side="left"))
        i1 = int(np.searchsorted(times, t_end, side="left"))
        tr_bins = bins[i0:i1]

        # 次の 1 時間の清算
        j0 = int(np.searchsorted(liq_t, t, side="left"))
        j1 = int(np.searchsorted(liq_t, t_end, side="left"))
        lp = liq_p[j0:j1]
        ls = liq_side[j0:j1]
        lb = (
            np.floor(np.log(lp) / step).astype(np.int64)
            if lp.size
            else np.empty(0, dtype=np.int64)
        )

        for side, offset in side_offset.items():
            bands = band_bins_for_side(nodes, step, offset, half_bins)
            cov, cov_log, n_in_range = band_coverage(bands, lo_bin, n_bins, step)
            sel = ls == side
            n_liq = int(sel.sum())
            n_liq_in = int(np.isin(lb[sel], bands).sum()) if n_liq else 0
            n_tr = int(tr_bins.size)
            n_tr_in = int(np.isin(tr_bins, bands).sum()) if n_tr else 0
            rows.append(
                {
                    "day": day,
                    "t_ms": int(t),
                    "side": side,
                    "n_nodes": int(nodes.size),
                    "n_band_bins": int(bands.size),
                    "n_band_bins_in_range": n_in_range,
                    "n_profile_bins": n_bins,
                    "band_coverage": round(cov, 6),
                    "band_coverage_log": round(cov_log, 6),
                    "n_liq": n_liq,
                    "n_liq_in_band": n_liq_in,
                    "in_band_rate": round(n_liq_in / n_liq, 6) if n_liq else "",
                    "n_trades": n_tr,
                    "n_trades_in_band": n_tr_in,
                    "trade_in_band_rate": round(n_tr_in / n_tr, 6) if n_tr else "",
                    "p0": p0,
                    "total_qty": total_qty,
                }
            )

    note = {
        "day": day,
        "prev_days_required": prevs,
        "prev_days_loaded": loaded_prev,
        "prev_days_missing": missing_prev,
        "liq_rows_in_file": int(len(liq_all)),
        "liq_rows_dropped_no_price": liq_dropped,
        "hours_written": len(rows) // len(side_offset),
        "hours_skipped_empty_window": skipped_empty,
        "agg_trades_loaded": int(n_trades_all),
    }
    if missing_prev:
        note["warning"] = (
            f"前の日 {', '.join(missing_prev)} の aggTrades zip が無いため、"
            f"この日の早い時刻の窓は {window_hours} 時間より短い。"
        )
    return rows, note


def _band_agg(sub: pd.DataFrame) -> dict:
    """side 1 つぶんの集計。"""
    n_liq = pd.to_numeric(sub["n_liq"], errors="coerce").fillna(0).to_numpy()
    n_in = pd.to_numeric(sub["n_liq_in_band"], errors="coerce").fillna(0).to_numpy()
    n_tr = pd.to_numeric(sub["n_trades"], errors="coerce").fillna(0).to_numpy()
    n_tr_in = pd.to_numeric(sub["n_trades_in_band"], errors="coerce").fillna(0).to_numpy()
    cov = pd.to_numeric(sub["band_coverage"], errors="coerce").to_numpy()
    cov_log = pd.to_numeric(sub["band_coverage_log"], errors="coerce").to_numpy()
    tr_rate = pd.to_numeric(sub["trade_in_band_rate"], errors="coerce").to_numpy()
    w = n_liq
    wsum = float(w.sum())

    def _wmean(x: np.ndarray) -> float | None:
        m = ~np.isnan(x)
        ww = w[m]
        if ww.sum() == 0:
            return None
        return float((x[m] * ww).sum() / ww.sum())

    def _q(x: np.ndarray, mask: np.ndarray | None = None) -> dict | None:
        v = x if mask is None else x[mask]
        v = v[~np.isnan(v)]
        if v.size == 0:
            return None
        return {f"q{q}": float(np.percentile(v, q)) for q in (5, 25, 50, 75, 95)}

    has_liq = n_liq > 0
    in_rate_pt = np.where(has_liq, np.divide(n_in, np.maximum(n_liq, 1)), np.nan)
    return {
        "time_points": int(len(sub)),
        "time_points_with_liq": int(has_liq.sum()),
        "liq_total": int(n_liq.sum()),
        "liq_in_band_total": int(n_in.sum()),
        # 清算件数で重み付けた全体値 = そのまま「件数の割合」
        "in_band_rate_weighted": (float(n_in.sum() / wsum) if wsum else None),
        "band_coverage_weighted": _wmean(cov),
        "band_coverage_log_weighted": _wmean(cov_log),
        "trade_in_band_rate_weighted": _wmean(tr_rate),
        # 重みなしの合計比(約定は約定の件数で割った値)
        "trade_in_band_rate_pooled": (
            float(n_tr_in.sum() / n_tr.sum()) if n_tr.sum() else None
        ),
        "band_coverage_mean": float(np.nanmean(cov)) if len(cov) else None,
        "quantiles_over_time_points": {
            "in_band_rate": _q(in_rate_pt, has_liq),
            "band_coverage": _q(cov),
            "band_coverage_log": _q(cov_log),
            "trade_in_band_rate": _q(tr_rate),
            "n_band_bins": _q(
                pd.to_numeric(sub["n_band_bins"], errors="coerce").to_numpy().astype(float)
            ),
            "n_profile_bins": _q(
                pd.to_numeric(sub["n_profile_bins"], errors="coerce")
                .to_numpy()
                .astype(float)
            ),
            "n_nodes": _q(
                pd.to_numeric(sub["n_nodes"], errors="coerce").to_numpy().astype(float)
            ),
        },
    }


def compute_fit_offsets(
    fit_days: list[str],
    root: Path,
    window_hours: float,
    bin_pct: float,
    seed: int,
    dedup_liq: bool,
) -> dict:
    """帯の位置(side 別 offset)を **`fit_days` だけ**から決める(2026-09-17、L-192 の行 3)。

    取り方は前回(`EXT_2026-09-17.md` §1 の (b))と同じ:
    `o3c_price_level_table.py` の清算行の `dist_node_bp` の side 別**中央値**を採り、
    `offset = -中央値 / 1e4` を小数 4 桁に丸める(前回の SELL −0.0056 / BUY +0.0070 と
    同じ丸め方)。違うのは**期間だけ**(前回は全 472 日、ここは `fit_days`)と、
    **一意化した清算行を使う**こと。
    """
    cache: dict = {}
    vals: dict[str, list[float]] = {}
    n_rows = 0
    for i_day, day in enumerate(fit_days):
        rows, _note = base.process_day(
            day, root, window_hours, bin_pct, seed, cache, dedup_liq=dedup_liq
        )
        for r in rows:
            if r["kind"] != "liq":
                continue
            n_rows += 1
            vals.setdefault(str(r["side"]), []).append(float(r["dist_node_bp"]))
        keep = set(base.days_needed(day, window_hours))
        if i_day + 1 < len(fit_days):
            keep |= set(base.days_needed(fit_days[i_day + 1], window_hours))
        for k in list(cache):
            if k not in keep:
                del cache[k]
        if (i_day + 1) % 20 == 0:
            print(f"  [fit] {i_day + 1}/{len(fit_days)} 日", flush=True)
    medians = {s: float(np.median(np.asarray(v))) for s, v in sorted(vals.items())}
    offsets = {s: round(-m / 1e4, 4) for s, m in medians.items()}
    return {
        "fit_days": fit_days,
        "fit_days_n": len(fit_days),
        "fit_first_day": fit_days[0] if fit_days else None,
        "fit_last_day": fit_days[-1] if fit_days else None,
        "fit_liq_rows": n_rows,
        "fit_liq_rows_by_side": {s: len(v) for s, v in sorted(vals.items())},
        "dist_node_bp_median_by_side": medians,
        "side_offset": offsets,
        "source": (
            f"fit 期間 {fit_days[0]}〜{fit_days[-1]}({len(fit_days)} 日)の清算行"
            f"(一意化{'あり' if dedup_liq else 'なし'})の dist_node_bp の side 別中央値。"
            f"offset = -中央値 / 1e4 を小数 4 桁に丸めた値(前回と同じ取り方)"
        ),
    }


def run_band(
    days: list[str],
    root: Path,
    out_dir: Path,
    window_hours: float,
    bin_pct: float,
    half_bins: int = BAND_HALF_BINS,
    side_offset: dict[str, float] | None = None,
    dedup_liq: bool = False,
    fit: dict | None = None,
) -> dict:
    t0 = time.time()
    side_offset = SIDE_OFFSET if side_offset is None else side_offset
    cache: dict = {}
    all_rows: list[dict] = []
    notes: list[dict] = []
    for i_day, day in enumerate(days):
        rows, note = process_day_band(
            day, root, window_hours, bin_pct, cache, half_bins, side_offset, dedup_liq
        )
        all_rows.extend(rows)
        notes.append(note)
        print(
            f"[{day}] 正時 {note['hours_written']} 点(窓が空で飛ばした "
            f"{note['hours_skipped_empty_window']} 点)/ 清算 {note['liq_rows_in_file']} 件"
            f" -> 行 {len(rows)}",
            flush=True,
        )
        keep = set(base.days_needed(day, window_hours))
        if i_day + 1 < len(days):
            keep |= set(base.days_needed(days[i_day + 1], window_hours))
        for k in list(cache):
            if k not in keep:
                del cache[k]

    df = pd.DataFrame(all_rows, columns=BAND_COLUMNS)
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "table.csv", index=False)
    elapsed = time.time() - t0
    summary = {
        "params": {
            "days": days,
            "window_hours": window_hours,
            "bin_pct": bin_pct,
            "prev_days_read_per_day": base.required_prev_days(window_hours),
            "band_half_bins": half_bins,
            "side_offset": side_offset,
            "dedup_liq": dedup_liq,
            "side_offset_source": (
                fit["source"] if fit else
                "docs/PHASE2/O3C/PRICE_LEVEL/FULL_2026-09-17.md §3 の side 別 "
                "dist_node_bp 中央値(SELL +56.4bp / BUY −70.2bp)"
            ),
            "fit": fit,
            "liq_price_field": "average_price",
            "data_root": str(root),
            "symbol": base.SYMBOL,
            "design": "docs/PHASE2/O3C/PRICE_LEVEL/DESIGN_2026-09-17.md",
            "extension": "docs/PHASE2/O3C/PRICE_LEVEL/EXT_2026-09-17.md",
        },
        "elapsed_sec": round(elapsed, 2),
        "rows_total": int(len(df)),
        "time_points": int(len(df) // len(side_offset)),
        "days": len(days),
        "hours_skipped_empty_window": sum(
            int(n["hours_skipped_empty_window"]) for n in notes
        ),
        "days_with_short_window": [n["day"] for n in notes if "warning" in n],
        "by_side": {
            str(s): _band_agg(df[df["side"] == s]) for s in sorted(df["side"].unique())
        },
        "per_day": notes,
        "notes": [
            "観測表のみ。判定(当たる/当たらない、使える/使えない)は書いていない。",
            "帯 = ノード(数量の上位 10% のビン)の代表価格 × (1 + offset) が入るビンの ±1 ビン。"
            "offset は SELL −0.0056 / BUY +0.0070(FULL §3 の side 別中央値)。",
            "in_band_rate = 次の 1 時間にその side で起きた清算のうち帯に入った件数の割合。",
            "band_coverage = 帯(範囲外は切り落とし、重なりは 1 回)の価格幅 / "
            "プロファイルの最安値〜最高値の幅。band_coverage_log は同じものをビン本数で数えた値。",
            "trade_in_band_rate = 同じ 1 時間の全 aggTrades のうち帯に入った**件数**の割合"
            "(数量では重み付けていない)。",
            "帯は清算より前の情報(直前 W の積み上げ)だけで引いている。"
            "offset の 56 / 70bp は全 472 日の結果から採った値なので、"
            "その意味で全期間の情報が入っている(EXT §7)。",
        ],
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    base.write_md5sums(out_dir, ["table.csv", "summary.json"])
    return summary


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["bundle", "band"])
    ap.add_argument("--days", required=True)
    ap.add_argument("--window-hours", type=float, default=24.0)
    ap.add_argument("--bin-pct", type=float, default=0.1)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--bundle-gap-ms", type=int, default=BUNDLE_GAP_MS)
    ap.add_argument("--band-half-bins", type=int, default=BAND_HALF_BINS)
    ap.add_argument(
        "--dedup-liq",
        action="store_true",
        help="liquidationSnapshot の全列一致の重複行を 1 件にしてから使う(L-192 の行 1)",
    )
    ap.add_argument(
        "--fit-days",
        default=None,
        help=(
            "band のみ。帯の位置(side 別 offset)をこの日だけから決める"
            "(L-192 の行 3)。--days が測る側(eval)"
        ),
    )
    ap.add_argument("--data-root", default=str(base.DEFAULT_DATA_ROOT))
    a = ap.parse_args(argv)

    days = [d.strip() for d in a.days.split(",") if d.strip()]
    fit_days = [d.strip() for d in (a.fit_days or "").split(",") if d.strip()]
    root = Path(a.data_root)
    for d in days + fit_days:
        for p in (base.agg_path(root, d), base.liq_path(root, d)):
            if not p.exists():
                raise SystemExit(f"必要な zip が無い: {p}")

    if a.mode == "bundle":
        s = run_bundle(
            days, root, Path(a.out_dir), a.window_hours, a.bin_pct, a.seed,
            a.bundle_gap_ms, a.dedup_liq,
        )
        print(
            f"行 {s['rows_total']}(清算 {s['rows_liq']} / 対照 {s['rows_control']})"
            f" 束 {s['bundles_total']} / 所要 {s['elapsed_sec']} 秒 -> {a.out_dir}"
        )
    else:
        fit = None
        side_offset = None
        if fit_days:
            fit = compute_fit_offsets(
                fit_days, root, a.window_hours, a.bin_pct, a.seed, a.dedup_liq
            )
            side_offset = fit["side_offset"]
            print(
                f"[fit] {fit['fit_first_day']}〜{fit['fit_last_day']}"
                f"({fit['fit_days_n']} 日、清算行 {fit['fit_liq_rows']})"
                f" dist_node_bp 中央値 {fit['dist_node_bp_median_by_side']}"
                f" -> offset {side_offset}",
                flush=True,
            )
        s = run_band(
            days, root, Path(a.out_dir), a.window_hours, a.bin_pct, a.band_half_bins,
            side_offset, a.dedup_liq, fit,
        )
        print(
            f"行 {s['rows_total']}(時点 {s['time_points']})"
            f" / 所要 {s['elapsed_sec']} 秒 -> {a.out_dir}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

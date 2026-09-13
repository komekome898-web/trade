#!/usr/bin/env python3
"""O-3c 段0(Q1)診断 — 「転換」をタイを落とさない実装で引き直す。

**これは判定のやり直しではない。**判定区間は既に開封済みで使い切っている。
入力は判定時の生成物 CSV だけで、新しい取引所・新しい期間は一切開かない。

手順:
  1. 判定時の「転換」(タイを NaN として除外)の点推定を CSV から再現し、
     `results/o3c_stage0/stage0_stats.csv` と突き合わせる。
  2. 同じ定義を日クラスタ・ブートストラップで引き直し、
     `docs/PHASE2/O3C/DIAG_Q1_CLUSTER_BOOTSTRAP.md` §3 の 16 セルと突き合わせる
     (手順・種・**乱数の消費順**が同じことの確認)。
  3. 直した実装(`bot.research.liq_response.compute_reversal`)の 3 方針
     keep(既定・タイを落とさない)/ refine(タイだけ分解能を上げる)/ drop(除外)で
     8 セルを引き直す。乱数の消費順は 2 と同一。
  4. MDE 2 通り((A) 封印値 / (A') 実 n で引き直し)で分類する。

出力: results/o3c_stage0/reversal_fix/ に途中経過を都度書く。
"""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/home/user/trade/src")

import numpy as np

from bot.research import liq_response as lr

CSV_PATH = Path("/home/user/trade/results/o3c_stage0/stage0_binance_cm_2024-06-13_2024-10-14.csv")
STATS_PATH = Path("/home/user/trade/results/o3c_stage0/stage0_stats.csv")
OUT_DIR = Path("/home/user/trade/results/o3c_stage0/reversal_fix")
OUT_DIR.mkdir(parents=True, exist_ok=True)

BOOT_N = 10_000
BOOT_SEED = 20260913            # scripts/run_o3c_stage0.py の BOOT_SEED と同じ
HORIZONS = (1, 5, 15, 60)
DIRECTIONS = ("long", "short")

# 封印 MDE(PREREG.md §7 / stage0_stats.csv の mde 列)
MDE_SEALED = {
    ("long", 1): 2.04, ("short", 1): 2.23,
    ("long", 5): 5.18, ("short", 5): 5.57,
    ("long", 15): 6.86, ("short", 15): 8.47,
    ("long", 60): 12.09, ("short", 60): 15.44,
}
# 反応窓 bp の標準偏差(POWER_INPUTS.md §3、探索区間の実測)
SD_BP = {
    ("long", 1): 10.97, ("short", 1): 9.94,
    ("long", 5): 27.83, ("short", 5): 24.88,
    ("long", 15): 36.86, ("short", 15): 37.83,
    ("long", 60): 64.99, ("short", 60): 68.98,
}
Z_SUM = 3.7968                  # z_{1-α/2}(α=0.05/16) + z_{0.80}。RESULT_STAGE0.md §5 の式

# 公開済みのクラスタ診断(DIAG_Q1_CLUSTER_BOOTSTRAP.md §3)の 95%CI
PUB_BP = {("long", 1): (1.239, 3.214), ("long", 5): (-2.425, 4.240),
          ("long", 15): (-4.721, 5.300), ("long", 60): (-17.385, 5.976),
          ("short", 1): (-2.995, -0.038), ("short", 5): (-6.055, 0.317),
          ("short", 15): (-9.688, 0.218), ("short", 60): (-35.767, -3.197)}
PUB_REV = {("long", 1): (0.263, 4.073), ("long", 5): (-3.379, 2.966),
           ("long", 15): (-4.657, 7.804), ("long", 60): (-13.504, 8.967),
           ("short", 1): (-2.655, 2.967), ("short", 5): (-4.162, 5.989),
           ("short", 15): (-2.745, 16.226), ("short", 60): (-5.521, 19.139)}


def mde_from_n(direction: str, horizon: int, n_real: int, n_ctrl: int) -> float:
    """RESULT_STAGE0.md §5 の式を実 n で引き直す。"""
    return Z_SUM * SD_BP[(direction, horizon)] * math.sqrt(1.0 / n_real + 1.0 / n_ctrl)


def classify(lo: float, hi: float, mde: float) -> str:
    """RESULT_STAGE0.md §5 と同じ 3 値分類。"""
    if lo > 0 or hi < 0:
        return "効果あり"
    if lo >= -mde and hi <= mde:
        return "陰性"
    return "不明"


def utc_day(ts_ms) -> str:
    return datetime.fromtimestamp(int(ts_ms) / 1000, timezone.utc).strftime("%Y-%m-%d")


# --------------------------------------------------------------------------- #
# 入力
# --------------------------------------------------------------------------- #
rows_by_group: dict[str, list[dict]] = defaultdict(list)
with CSV_PATH.open(encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        rows_by_group[r["group"]].append(r)

log_lines: list[str] = []


def log(msg: str) -> None:
    print(msg)
    log_lines.append(msg)
    (OUT_DIR / "run_log.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8")


log("input: " + CSV_PATH.name + " groups=" + json.dumps({k: len(v) for k, v in rows_by_group.items()}))

stats_judge: dict[tuple[str, int], dict] = {}
with STATS_PATH.open(encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        stats_judge[(r["direction"], int(r["horizon"]))] = r

DAYS = {d: {g: [utc_day(r["start_ms"]) for r in rows_by_group[f"{g}_{d}"]]
            for g in ("real", "placebo")} for d in DIRECTIONS}
UNIVERSE = {d: sorted(set(DAYS[d]["real"]) | set(DAYS[d]["placebo"])) for d in DIRECTIONS}
log("day universe (real ∪ placebo): " + json.dumps({d: len(UNIVERSE[d]) for d in DIRECTIONS}))


# --------------------------------------------------------------------------- #
# 日クラスタ・ブートストラップ(DIAG_Q1_CLUSTER_BOOTSTRAP.md §1 と同じ)
# --------------------------------------------------------------------------- #
def boot_cluster(a_vals, a_days, b_vals, b_days, days, rng):
    """起点日を単位に復元抽出。実群と対照群は**同じ日の抽選を共有する**。

    日の集合 `days` は実群 ∪ プラセボの起点日(= 124 日)で固定する
    (その日に使える行が無い群は、その日の合計・件数が 0 として入る)。
    統計量は日ごとの合計と件数を足し上げた比推定 Σs/Σc の差。
    """
    di = {d: i for i, d in enumerate(days)}
    n = len(days)
    sa = np.zeros(n); ca = np.zeros(n); sb = np.zeros(n); cb = np.zeros(n)
    for v, d in zip(a_vals, a_days):
        sa[di[d]] += v; ca[di[d]] += 1
    for v, d in zip(b_vals, b_days):
        sb[di[d]] += v; cb[di[d]] += 1
    idx = rng.integers(0, n, size=(BOOT_N, n))
    den_a = ca[idx].sum(axis=1); den_b = cb[idx].sum(axis=1)
    bad = int(((den_a == 0) | (den_b == 0)).sum())
    with np.errstate(invalid="ignore", divide="ignore"):
        diffs = sa[idx].sum(axis=1) / den_a - sb[idx].sum(axis=1) / den_b
    diffs = diffs[np.isfinite(diffs)]
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    point = sa.sum() / ca.sum() - sb.sum() / cb.sum()
    return float(point), float(lo), float(hi), bad


def finite(vals: list[float], days: list[str]):
    """NaN を落とし、残った値と日を対にして返す(件数が必ず一致する形にする)。"""
    keep = [(v, d) for v, d in zip(vals, days) if v == v]
    return np.array([v for v, _ in keep], dtype=float), [d for _, d in keep]


def bp_values(rows: list[dict], key: str) -> list[float]:
    return [lr._as_float(r.get(key)) for r in rows]


def judge_time_reversal(rows: list[dict], key: str) -> list[float]:
    """判定時の実装(`run_o3c_stage0.py` の内側の `reversal()`)を逐語で写したもの。"""
    out = []
    for r in rows:
        ib = lr._as_float(r.get("internal_bp")); bp = lr._as_float(r.get(key))
        out.append(float("nan") if (ib != ib or bp != bp or ib == 0) else -math.copysign(1.0, ib) * bp)
    return out


# --------------------------------------------------------------------------- #
# 手順 1: 判定時の点推定の再現(カスケード単位・タイ除外)
# --------------------------------------------------------------------------- #
judge_n: dict[tuple[str, int], tuple[int, int]] = {}
max_abs = 0.0
for direction in DIRECTIONS:
    for h in HORIZONS:
        key = f"bp_{h}m"
        a, _ = finite(judge_time_reversal(rows_by_group[f"real_{direction}"], key), DAYS[direction]["real"])
        b, _ = finite(judge_time_reversal(rows_by_group[f"placebo_{direction}"], key), DAYS[direction]["placebo"])
        judge_n[(direction, h)] = (len(a), len(b))
        max_abs = max(max_abs, abs((a.mean() - b.mean()) - float(stats_judge[(direction, h)]["rev_point"])))
log(f"[1] judgement-time reversal point estimates reproduced: max |diff| = {max_abs:.3e}")
log("[1] usable n (ties dropped): " + json.dumps({f"{d}_{h}": judge_n[(d, h)] for d in DIRECTIONS for h in HORIZONS}))


# --------------------------------------------------------------------------- #
# 手順 2: 公開済みのクラスタ診断と乱数の消費順まで合わせる
#   順序: 向き long→short、窓 1→5→15→60、各窓で「行きすぎ」→「転換」。
#   1 本の default_rng(20260913) を通しで消費する。
# --------------------------------------------------------------------------- #
rng = np.random.default_rng(BOOT_SEED)
repro_rows: list[dict] = []
worst_bp = worst_rev = 0.0
for direction in DIRECTIONS:
    real = rows_by_group[f"real_{direction}"]; pb = rows_by_group[f"placebo_{direction}"]
    for h in HORIZONS:
        key = f"bp_{h}m"
        for claim in ("行きすぎ", "転換"):
            vals_r = bp_values(real, key) if claim == "行きすぎ" else judge_time_reversal(real, key)
            vals_p = bp_values(pb, key) if claim == "行きすぎ" else judge_time_reversal(pb, key)
            a, ad = finite(vals_r, DAYS[direction]["real"])
            b, bd = finite(vals_p, DAYS[direction]["placebo"])
            pt, lo, hi, bad = boot_cluster(a, ad, b, bd, UNIVERSE[direction], rng)
            ref = PUB_BP[(direction, h)] if claim == "行きすぎ" else PUB_REV[(direction, h)]
            d = max(abs(lo - ref[0]), abs(hi - ref[1]))
            if claim == "行きすぎ":
                worst_bp = max(worst_bp, d)
            else:
                worst_rev = max(worst_rev, d)
            repro_rows.append(dict(direction=direction, horizon=h, claim=claim,
                                   n_real=len(a), n_pb=len(b), point=pt, lo=lo, hi=hi,
                                   pub_lo=ref[0], pub_hi=ref[1], abs_diff=d, bad_iters=bad))
with (OUT_DIR / "repro_cluster.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(repro_rows[0].keys())); w.writeheader(); w.writerows(repro_rows)
log(f"[2] cluster bootstrap vs published diagnostic: max |diff| of CI ends = "
    f"行きすぎ {worst_bp:.4f} / 転換 {worst_rev:.4f} (published values are rounded to 3 decimals)")


# --------------------------------------------------------------------------- #
# 手順 3: 直した実装で引き直す(乱数の消費順は手順 2 と同一)
# --------------------------------------------------------------------------- #
def kept_days(rows: list[dict], key: str, policy: str, days: list[str]) -> list[str]:
    """`reversal_scores` が実際に残した行と同じ順・同じ件数の日の列を作る。"""
    out = []
    for r, d in zip(rows, days):
        ib = lr._as_float(r.get("internal_bp")); bp = lr._as_float(r.get(key))
        if ib != ib or bp != bp:
            continue
        if policy == "drop" and ib == 0:
            continue
        out.append(d)
    return out


cells: list[dict] = []
for policy in ("keep", "refine", "drop"):
    rng = np.random.default_rng(BOOT_SEED)
    for direction in DIRECTIONS:
        real = rows_by_group[f"real_{direction}"]; pb = rows_by_group[f"placebo_{direction}"]
        for h in HORIZONS:
            key = f"bp_{h}m"
            # 「行きすぎ」のセル(統計量は直していない)も同じ順で引いて乱数の位置を合わせる
            a, ad = finite(bp_values(real, key), DAYS[direction]["real"])
            b, bd = finite(bp_values(pb, key), DAYS[direction]["placebo"])
            bp_pt, bp_lo, bp_hi, _ = boot_cluster(a, ad, b, bd, UNIVERSE[direction], rng)
            assert max(abs(bp_lo - PUB_BP[(direction, h)][0]),
                       abs(bp_hi - PUB_BP[(direction, h)][1])) < 0.01, (direction, h)

            rep = lr.compute_reversal({"real": real, "placebo": pb}, key,
                                      tie_policy=policy, strict=(policy != "drop"))
            g_r, g_p = rep.groups["real"], rep.groups["placebo"]
            ra = np.array(g_r.scores, dtype=float); rb = np.array(g_p.scores, dtype=float)
            rad = kept_days(real, key, policy, DAYS[direction]["real"])
            rbd = kept_days(pb, key, policy, DAYS[direction]["placebo"])
            assert len(ra) == len(rad) and len(rb) == len(rbd), (policy, direction, h)
            pt, lo, hi, bad = boot_cluster(ra, rad, rb, rbd, UNIVERSE[direction], rng)
            mde_a = MDE_SEALED[(direction, h)]
            mde_ap = mde_from_n(direction, h, len(ra), len(rb))
            cells.append(dict(
                policy=policy, direction=direction, horizon=h,
                n_real_rows=g_r.n_rows, n_real_used=g_r.n_used, n_real_tie=g_r.n_tie,
                n_real_tie_resolved=g_r.n_tie_resolved, excl_real=g_r.exclusion_rate,
                n_pb_rows=g_p.n_rows, n_pb_used=g_p.n_used, n_pb_tie=g_p.n_tie,
                excl_pb=g_p.exclusion_rate, excl_gap=rep.max_exclusion_gap,
                point=pt, lo=lo, hi=hi, bad_iters=bad,
                mde_A=mde_a, class_A=classify(lo, hi, mde_a),
                mde_Ap=mde_ap, class_Ap=classify(lo, hi, mde_ap),
            ))
    with (OUT_DIR / "cells.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cells[0].keys())); w.writeheader(); w.writerows(cells)
    log(f"[3] policy={policy}: 8 cells written")


# --------------------------------------------------------------------------- #
# 手順 4: 判定時(カスケード単位・タイ除外)と、その定義のクラスタ版も同じ 2 通りの MDE で分類
# --------------------------------------------------------------------------- #
base: list[dict] = []
for direction in DIRECTIONS:
    for h in HORIZONS:
        ref = stats_judge[(direction, h)]
        n_a, n_b = judge_n[(direction, h)]
        mde_a = MDE_SEALED[(direction, h)]
        mde_ap = mde_from_n(direction, h, n_a, n_b)
        lo, hi = float(ref["rev_lo"]), float(ref["rev_hi"])
        base.append(dict(source="判定時(カスケード単位・タイ除外)", direction=direction, horizon=h,
                         n_real_used=n_a, n_pb_used=n_b, point=float(ref["rev_point"]), lo=lo, hi=hi,
                         mde_A=mde_a, class_A=classify(lo, hi, mde_a),
                         mde_Ap=mde_ap, class_Ap=classify(lo, hi, mde_ap)))
        c = next(r for r in repro_rows if r["direction"] == direction and r["horizon"] == h and r["claim"] == "転換")
        base.append(dict(source="判定時の定義・日クラスタ(公開済み診断)", direction=direction, horizon=h,
                         n_real_used=c["n_real"], n_pb_used=c["n_pb"], point=c["point"],
                         lo=c["lo"], hi=c["hi"],
                         mde_A=mde_a, class_A=classify(c["lo"], c["hi"], mde_a),
                         mde_Ap=mde_ap, class_Ap=classify(c["lo"], c["hi"], mde_ap)))
with (OUT_DIR / "baseline_cells.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(base[0].keys())); w.writeheader(); w.writerows(base)
log("[4] baseline cells re-classified under both MDEs")


# --------------------------------------------------------------------------- #
# 手順 5: 実データで strict=True が本当に止めるかの確認
# --------------------------------------------------------------------------- #
try:
    lr.compute_reversal({"real": rows_by_group["real_long"], "placebo": rows_by_group["placebo_long"]},
                        "bp_1m", tie_policy="drop")
    log("[5] WARNING: strict=True did NOT raise on real data")
except lr.ReversalExclusionImbalance as e:
    log(f"[5] strict=True raised as designed: {e}")

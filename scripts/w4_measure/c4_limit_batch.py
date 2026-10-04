#!/usr/bin/env python3
"""カード 4 段 1 の族 A・B を 1 周走らせる(INTENT_MAP §10・§11-3、SPEC §5、L-592)。

v37 の既定から 1 つだけ変えた変種を、良い側・悪い側の両方で `c4_limit_run.py` に渡す。
組み合わせ C は A・B の結果を読んでから決めるので、ここには入れない。

    PYTHONPATH=src python3 scripts/w4_measure/c4_limit_batch.py --out-root <置き場> \\
        --shard 0 --nshards 3 --jobs 2

- 走らせごとに <置き場>/<名前>_<側>/ に summary.json・run_record.json・trades.csv.gz・trades.json.gz と、
  trades から作る analysis.json(年ごと・入りの時の比 width/vola の十分位・width/終値 の十分位・
  終わり方ごとの取引数と損益の和)を出す。analysis.json があれば飛ばす(冪等)。
- 前の測定から引き継ぐ問い(INTENT_MAP §11-5、L-590)の鍵も analysis.json に出す: P-1 `by_break`
  (ブレイクで閉じた / ブレイクの間に入った / ほか)、P-2 `ratio_fixed_bins`(門の診断の十分位の境で固定。84 本で同じ境)、
  P-4 `by_hold`(保有の分)・`decided_only`(決まらない足に当たらなかった取引だけ)。
- B5 は再現で動きが変わらない(SPEC 3-3)ので作らない。B3・B4 は A5・A2 と同じ(§11-3)。
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

# (名前, 族, 引数)。引数は c4_limit_run.py の既定(v37)から変える分だけ
RUNS: list = [("v37", "base", [])]
# A1 入り:利確 × 利確の形
for e, x in ((2, 0.8), (3, 2), (4, 3), (5, 1), (2, 1)):
    RUNS.append((f"A1_center_{e}_{x}", "A1", ["--exit-form", "center", "--entry", str(e), "--exit-setting", str(x)]))
for e in (1, 3, 4, 5):
    RUNS.append((f"A1_v37_entry{e}", "A1", ["--entry", str(e)]))
# A2 段(間隔 × 数)
for st in (1, 2):
    for n in (7, 5, 4, 1):
        if (st, n) != (1, 7):
            RUNS.append((f"A2_step{st}_n{n}", "A2", ["--step", str(st), "--n-levels", str(n)]))
# A3 レンジの物差し(窓 × 足 × 端)
for w in (10, 20, 40, 80, 160):
    for b in (1, 5):
        for r in ("body", "wick"):
            if (w, b, r) != (40, 1, "body"):
                RUNS.append((f"A3_w{w}_b{b}_{r}", "A3",
                             ["--window-min", str(w), "--bar-min", str(b), "--range-from", r]))
# A4 幅の門(門を外した 1 本。十分位の曲線は analysis.json の width/終値 で読む)
RUNS.append(("A4_nogate", "A4", ["--width-gate", "False"]))
# A5 回転(緩め 1 分・成行 2 分)
RUNS.append(("A5_alert1", "A5", ["--alert-min", "1"]))
# B1 止める合図(ブレイクの判定の遅れ。比の十分位の曲線は analysis.json の比で読む)
for d in (0, 3):
    RUNS.append((f"B1_delay{d}", "B1", ["--break-delay", str(d)]))
# B2 止めた後
for ob in ("close", "follow"):
    RUNS.append((f"B2_{ob}", "B2", ["--on-break", ob]))
# C 組み合わせ(L-620「1〜3はそれですすめて」の 1): 中心から測る利確 4 つ × 5 分足のレンジの物差し 2 つ。
# 1 分足 40 分(v37 の物差し)との組は A1_center_* が、利確が v37 の組は A3_w*_b5_body が既にある。
COMBO_CENTERS = ((2, 0.8), (3, 2), (4, 3), (5, 1))
COMBO_RULERS = ((20, 5, "body"), (40, 5, "body"))
for e, x in COMBO_CENTERS:
    for w, b, r in COMBO_RULERS:
        RUNS.append((f"C_center_{e}_{x}_w{w}_b{b}_{r}", "C",
                     ["--exit-form", "center", "--entry", str(e), "--exit-setting", str(x),
                      "--window-min", str(w), "--bar-min", str(b), "--range-from", r]))

SIDES = ("good", "bad")
# 門の診断(docs/RESEARCH/cards/c4_owner_matilda_range/diag_gate/README.md「比の十分位ごとの P」)の境。INTENT_MAP §11-5 P-2
RATIO_FIXED_EDGES = (7.51, 8.52, 9.34, 10.14, 10.96, 11.87, 12.96, 14.40, 16.77)
# D ブレイクの負けを直接減らす(L-620「1〜3はそれですすめて」の 2)。
# 閉じる位置: ブレイクに逆らう持ち高を閉じる値段を、判定値から −0.5(手前)・+0.5(先)× vola ずらす(0 = v37)
for c, tag in ((-0.5, "m0.5"), (0.5, "p0.5")):
    RUNS.append((f"D_breakclose_{tag}", "D", ["--break-close-offset", str(c)]))
# 比の門: 入る時点の比が境以上なら入らない。境 12.96 = RATIO_FIXED_EDGES の 7 番目(門の診断の「全期間の分の比から」の
# 十分位の境)。走らせる期間と同じデータから決めた値(標本の中)
RUNS.append((f"D_ratio_gate{RATIO_FIXED_EDGES[6]}", "D", ["--ratio-gate", str(RATIO_FIXED_EDGES[6])]))
# 合計をそろえた段は作らない: 損益の式(matilda_limit_sim の _close_row)が 1 段 = 1/段の数 なので、全部の段が約定した
# ときの合計は既定でどの段の数でも 1(リードの答え 3a)
# 保有の分の区切り(INTENT_MAP §11-5 P-4)。0 = 同じ足の中で入って出た。[lo, hi) 分
HOLD_BINS = ((0, 1), (1, 2), (2, 6), (6, 21), (21, 41), (41, None))


def _deciles(x: np.ndarray, pnl: np.ndarray) -> dict:
    fin = np.isfinite(x)
    if fin.sum() < 10:
        return {}
    edges = np.percentile(x[fin], np.arange(0, 101, 10))
    q = np.clip(np.searchsorted(edges[1:-1], x, side="right"), 0, 9)
    q[~fin] = 9
    rows = []
    for k in range(10):
        m = q == k
        rows.append({"decile": k + 1, "lo": float(edges[k]), "hi": float(edges[k + 1]), "trades": int(m.sum()),
                     "wins": int((pnl[m] > 0).sum()), "sum_bp": float(pnl[m].sum()),
                     "mean_bp": float(pnl[m].mean()) if m.any() else None})
    return {"rows": rows}


def _sums(m: np.ndarray, pnl: np.ndarray) -> dict:
    return {"trades": int(m.sum()), "wins": int((pnl[m] > 0).sum()), "sum_bp": float(pnl[m].sum()),
            "small_win_sum_bp": float(pnl[m & (pnl > 0)].sum()), "big_loss_sum_bp": float(pnl[m & (pnl <= -10)].sum())}


def _iso_min(t: str) -> int:
    from datetime import datetime
    return int(datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()) // 60


def analyse(d: str) -> None:
    path = os.path.join(d, "trades.csv.gz")
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        out = {"trades": 0}
    else:
        pnl = np.array([float(r["pnl_bp"]) for r in rows])
        ratio = np.array([float(r["ratio"]) for r in rows])
        wpc = np.array([float(r["width"]) / float(r["close_k"]) for r in rows])
        year = np.array([int(r["exit_t"][:4]) for r in rows])
        reason = np.array([r["exit_reason"] for r in rows])
        und = np.array([int(r["undecided"]) for r in rows])
        out = {"trades": len(rows), "ratio_deciles": _deciles(ratio, pnl), "width_over_close_deciles": _deciles(wpc, pnl),
               "by_reason": {k: {"trades": int((reason == k).sum()), "sum_bp": float(pnl[reason == k].sum())}
                             for k in sorted(set(reason.tolist()))},
               "by_year": {int(y): {"trades": int((year == y).sum()), "sum_bp": float(pnl[year == y].sum()),
                                    "big_loss_sum_bp": float(pnl[(year == y) & (pnl <= -10)].sum()),
                                    "small_win_sum_bp": float(pnl[(year == y) & (pnl > 0)].sum()),
                                    "undecided_trades": int(((year == y) & (und > 0)).sum())}
                           for y in sorted(set(year.tolist()))}}
        brk = np.array([int(r["brk"]) for r in rows])
        # P-1: ブレイクに逆らう持ち高 = ブレイクで閉じた取引(反対のブレイク・ブレイク)。v37 は持ち高 0 からブレイクの
        # 間に入らないので、入った時点の brk が 0 でないのは follow の入りだけ(2019 年の 1 か月の試しの v37 で brk≠0 の入りは 0 件)
        brk_exit = np.isin(reason, ("反対のブレイク", "ブレイク"))
        # 族 D 閉じる位置の止めで閉じた取引(終わり方「閉じる位置で閉じる」)は別の群。その取引が無い走らせ(既定など)では
        # 群を出さず、ほかの群も前と同じ
        bcl = reason == "閉じる位置で閉じる"
        groups = {"closed_by_break": brk_exit, "entered_during_break": ~brk_exit & ~bcl & (brk != 0),
                  "other": ~brk_exit & ~bcl & (brk == 0)}
        if bcl.any():
            groups["closed_by_bcl"] = bcl
        out["by_break"] = {k: _sums(m, pnl) for k, m in groups.items()}
        fb = np.searchsorted(np.array(RATIO_FIXED_EDGES), ratio, side="right")
        out["ratio_fixed_bins"] = {"edges": list(RATIO_FIXED_EDGES),
                                   "rows": [{"bin": k + 1, **_sums(fb == k, pnl)} for k in range(len(RATIO_FIXED_EDGES) + 1)]}
        hold = np.array([_iso_min(r["exit_t"]) - _iso_min(r["entry_t"]) for r in rows])
        out["by_hold"] = {"bins_min": [list(b) for b in HOLD_BINS], "median_min": float(np.median(hold)),
                          "rows": [{"lo": lo, "hi": hi, **_sums((hold >= lo) & ((hold < hi) if hi is not None else True), pnl)}
                                   for lo, hi in HOLD_BINS]}
        dec = und == 0
        out["decided_only"] = {**_sums(dec, pnl), "by_break": {k: _sums(dec & m, pnl) for k, m in groups.items()}}
    with open(os.path.join(d, "analysis.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)


def run_one(job: tuple, root: str) -> str:
    name, _fam, args, side = job
    d = os.path.join(root, f"{name}_{side}")
    if os.path.exists(os.path.join(d, "analysis.json")):
        return f"skip {name}_{side}"
    if not os.path.exists(os.path.join(d, "summary.json")):
        os.makedirs(d, exist_ok=True)
        cmd = [sys.executable, os.path.join(HERE, "c4_limit_run.py"), "--fill-side", side, "--out", d] + args
        with open(os.path.join(d, "run.log"), "w", encoding="utf-8") as log:
            r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
        if r.returncode != 0:
            return f"FAIL {name}_{side} rc={r.returncode}"
    analyse(d)
    return f"done {name}_{side}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-root", required=True)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    jobs = [(n, f, ar, s) for (n, f, ar) in RUNS for s in SIDES]
    mine = [j for i, j in enumerate(jobs) if i % a.nshards == a.shard]
    if a.list:
        for j in mine:
            print(j[0], j[3], " ".join(j[2]))
        print(f"{len(mine)} / {len(jobs)}")
        return 0
    os.makedirs(a.out_root, exist_ok=True)
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        for msg in ex.map(lambda j: run_one(j, a.out_root), mine):
            print(msg, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

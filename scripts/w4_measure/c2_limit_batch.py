#!/usr/bin/env python3
"""カード 2 の指値の再現の全期間の走らせ(SPEC §9・§9-1、L-590・L-592)。門なしと参照の形だけ。

門ありは、高ボラの門の測定(`docs/RESEARCH/cards/c2_owner_xvenue_wick/vol_gate/DESIGN.md` 問い 2)で
境目の決め方を決めてから別に走らせる(SPEC §9-1)。

    PYTHONPATH=src python3 scripts/w4_measure/c2_limit_batch.py --out-root <置き場> --shard 0 --nshards 2 --jobs 2

- 指値の形(fill=limit): 弱いだけ(k1)× 足 5・15・30・60 × 入り方 a・b・c、強いだけ × 足 1 × 入り方 a・b・c。
  良い側・悪い側の両方。取り逃しは並走の参照の形で数える(c2_limit_run.py)。
- 参照の形(fill=close): 同じ組の入り方 a・b(c は b と同じ結果になる)。必ず終値で約定するので、良い側だけ。
- 期間は c2_limit_run.py の既定(Binance 現物の始まり〜 2023-12-17、封印の前)。
- <置き場>/<名前>/ に summary.json があれば飛ばす(冪等)。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))

JOBS: list = []
for keep, feet in (("weak", (5, 15, 30, 60)), ("strong", (1,))):
    for f in feet:
        base = ["--series", "a", "--design", "k1", "--foot-min", str(f)]
        if keep == "strong":
            base += ["--side-keep", "strong"]
        for e in ("a", "b", "c"):
            for side in ("good", "bad"):
                JOBS.append((f"{keep}_f{f}_limit_{e}_{side}", base + ["--entry", e, "--fill", "limit", "--fill-side", side]))
        for e in ("a", "b"):
            JOBS.append((f"{keep}_f{f}_close_{e}", base + ["--entry", e, "--fill", "close", "--fill-side", "good"]))

# 門あり 5・15 分(SPEC §9-1「門なしを全部と、門あり 5・15 分 × 入り方 3 を走らせる」。境目は K1 の値。
# 最初の一覧から抜けていた分。--gated で走らせる。2026-10-03 リード)
JOBS_GATED: list = []
for f in (5, 15):
    base = ["--series", "a", "--design", "k1", "--foot-min", str(f), "--vol-gate"]
    for e in ("a", "b", "c"):
        for side in ("good", "bad"):
            JOBS_GATED.append((f"weak_f{f}_gate_limit_{e}_{side}", base + ["--entry", e, "--fill", "limit", "--fill-side", side]))
    for e in ("a", "b"):
        JOBS_GATED.append((f"weak_f{f}_gate_close_{e}", base + ["--entry", e, "--fill", "close", "--fill-side", "good"]))

# 門の境目を直前 365 日の合図の上位 3 分の 1 にした門あり(L-619「直し方案で測り直してください」)。--rolling で走らせる。
JOBS_ROLLING: list = []
for f in (5, 15):
    base = ["--series", "a", "--design", "k1", "--foot-min", str(f), "--vol-gate", "--vol-gate-mode", "rolling"]
    for e in ("a", "b", "c"):
        for side in ("good", "bad"):
            JOBS_ROLLING.append((f"weak_f{f}_rgate_limit_{e}_{side}", base + ["--entry", e, "--fill", "limit", "--fill-side", side]))
    for e in ("a", "b"):
        JOBS_ROLLING.append((f"weak_f{f}_rgate_close_{e}", base + ["--entry", e, "--fill", "close", "--fill-side", "good"]))

# 参照との差を入りと降りに分ける(limit_sim/runs/READ/RESULTS.md §3 の 1)。--ablation で走らせる。
# le_cx = 入りは指値・降りるは終値、ce_lx = 入りは終値・降りるは 4 本
JOBS_ABLATION: list = []
for f in (5, 15, 30, 60):
    base = ["--series", "a", "--design", "k1", "--foot-min", str(f)]
    for tag, fill in (("le_cx", "limit_entry_close_exit"), ("ce_lx", "close_entry_limit_exit")):
        # le_cx は降りが終値で決まらない足が無く、良い側と悪い側で取引の行が同じ → 良い側だけ。
        # ce_lx は入りが終値なので入り方 b と c で取引の行が同じ → c を省く(既存の close の c と同じ扱い)。
        # (作業者の 1 か月の走らせで確かめた。2026-10-03 リード)
        for e in (("a", "b", "c") if tag == "le_cx" else ("a", "b")):
            for side in (("good",) if tag == "le_cx" else ("good", "bad")):
                JOBS_ABLATION.append((f"weak_f{f}_{tag}_{e}_{side}",
                                      base + ["--entry", e, "--fill", fill, "--fill-side", side]))


def run_one(job: tuple, root: str) -> str:
    name, args = job
    d = os.path.join(root, name)
    if os.path.exists(os.path.join(d, "summary.json")):
        return f"skip {name}"
    os.makedirs(d, exist_ok=True)
    cmd = [sys.executable, os.path.join(HERE, "c2_limit_run.py"), "--out", d] + args
    with open(os.path.join(d, "run.log"), "w", encoding="utf-8") as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
    return f"done {name}" if r.returncode == 0 else f"FAIL {name} rc={r.returncode}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-root", required=True)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--gated", action="store_true", help="門あり 5・15 分の組(JOBS_GATED)を走らせる")
    ap.add_argument("--ablation", action="store_true", help="入りと降りを分ける組(JOBS_ABLATION)を走らせる")
    ap.add_argument("--rolling", action="store_true", help="境目を直前 365 日にした門ありの組(JOBS_ROLLING)を走らせる")
    a = ap.parse_args()
    jobs = JOBS_ROLLING if a.rolling else (JOBS_ABLATION if a.ablation else (JOBS_GATED if a.gated else JOBS))
    mine = [j for i, j in enumerate(jobs) if i % a.nshards == a.shard]
    if a.list:
        for n, ar in mine:
            print(n, " ".join(ar))
        print(f"{len(mine)} / {len(jobs)}")
        return 0
    os.makedirs(a.out_root, exist_ok=True)
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        for msg in ex.map(lambda j: run_one(j, a.out_root), mine):
            print(msg, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""K1 stage A (2026-09-27, L-479): run the K1 strategy (src/bot/strategy/k1_wick.py)
on the new environment, one run record per cell (13 gates x 6 feet x 3 strengths),
through bot.bt.repro.runner (purpose 研究, pre-registration docs/PHASE2/K1/PREREG.md).

Input: the foot-minute bars that scripts/k1_newenv_fold.py made through the data
layer (backtest_data/k1_newenv_a_20260927/xbtusd_{foot}m_2017_2019.csv.gz).

Each cell = runner.run(...) = two executions compared byte for byte, kept under
backtest_runs/k1_newenv_a/<run_id>/ (record.json, repro.json, metrics / trades /
fills / orders / data_quality exports). The index of cells -> run ids, wall time and
max RSS per cell goes to docs/PHASE2/K1/NEWENV_A/runs_index.json.

Order (delegation §2.7): strength both first (table 2.1), then strong (2.2), then
weak (2.3); within a strength the feet 60 -> 1 (the cheap cells first).

Usage: PYTHONPATH=src python3 scripts/k1_newenv_run.py [--workers 4] [--strengths both strong weak]
       [--feet 60 30 15 5 3 1] [--gates s19/b24 ...] [--profile]  (--profile: one cell under cProfile)
"""
from __future__ import annotations

import argparse
import cProfile
import json
import os
import pstats
import resource
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from bot.bt.repro.runner import DataInput, plan_run, run  # noqa: E402
from bot.strategy.k1_wick import FILL_NAME, K1Setup, gate_label, gates  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DATA_DIR = "backtest_data/k1_newenv_a_20260927"
RUNS_DIR = os.path.join(REPO, "backtest_runs", "k1_newenv_a")
INDEX = os.path.join(REPO, "docs", "PHASE2", "K1", "NEWENV_A", "runs_index.json")
PREREG = "docs/PHASE2/K1/PREREG.md"
FEET = (60, 30, 15, 5, 3, 1)
STRENGTHS = ("both", "strong", "weak")
COSTS = {"maker_fee_rate": 0, "taker_fee_rate": 0, "source": "K1 RESULT.md 1.4「経費は引いていない」: 費用 0"}


def spec(foot: int) -> dict:
    return {"format": "csv", "header": True, "delimiter": ",", "compression": "gzip", "kind": "bar",
            "symbol": "XBTUSD", "asset": "crypto",
            "time": {"columns": ["start_ts"], "unit": "iso", "tz": "UTC"},
            "fields": {"open": "o", "high": "h", "low": "l", "close": "c", "volume": "vol"},
            "bar": {"interval_s": foot * 60, "label": "start"}, "key": "start"}


def config(foot: int, s: str, b: str, strength: str) -> dict:
    return {"instrument": "XBTUSD", "foot_min": foot, "gate": {"s": s, "b": b}, "strength": strength,
            "fill": FILL_NAME, "costs": COSTS}


def plan_args(foot: int, s: str, b: str, strength: str) -> dict:
    return dict(root=REPO, data=[DataInput(f"{DATA_DIR}/xbtusd_{foot}m_2017_2019.csv.gz", spec(foot))],
                config=config(foot, s, b, strength), seed=0, setup=K1Setup(), purpose="研究", prereg=PREREG)


def cell_key(foot: int, s: str, b: str, strength: str) -> str:
    return f"{foot}|{gate_label(s, b)}|{strength}"


def run_cell(args):
    foot, s, b, strength = args
    key = cell_key(foot, s, b, strength)
    t0 = time.time()
    pa = plan_args(foot, s, b, strength)
    plan = plan_run(**pa)
    final = os.path.join(RUNS_DIR, plan.run_id)
    if os.path.isfile(os.path.join(final, "repro.json")):
        return {"cell": key, "run_id": plan.run_id, "skipped": True, "wall_s": round(time.time() - t0, 1)}
    res = run(runs_dir=RUNS_DIR, **pa)
    wall = time.time() - t0
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    with open(os.path.join(res.run_dir, "trades.json"), "r", encoding="utf-8") as fh:
        n = len(json.load(fh)["data"])
    return {"cell": key, "foot": foot, "gate": gate_label(s, b), "strength": strength, "run_id": res.run_id,
            "identical": res.repro["identical"], "n_trades": n, "wall_s": round(wall, 1), "max_rss_mb": round(rss, 1)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--strengths", nargs="+", default=list(STRENGTHS))
    ap.add_argument("--feet", type=int, nargs="+", default=list(FEET))
    ap.add_argument("--gates", nargs="+", default=None)
    ap.add_argument("--profile", action="store_true")
    a = ap.parse_args()
    gs = [(s, b) for s, b in gates() if a.gates is None or gate_label(s, b) in a.gates]
    cells = [(f, s, b, st) for st in a.strengths for f in a.feet for s, b in gs]
    if a.profile:
        f, s, b, st = cells[0]
        out = os.path.join(REPO, "docs", "PHASE2", "K1", "NEWENV_A", "logs", f"cprofile_{f}m_{gate_label(s, b).replace('/', '_')}_{st}")
        pr = cProfile.Profile()
        pr.enable()
        r = run_cell((f, s, b, st))
        pr.disable()
        pr.dump_stats(out + ".prof")
        with open(out + ".txt", "w", encoding="utf-8") as fh:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            for sort in ("cumulative", "tottime"):
                fh.write(f"\n== sort by {sort} (top 25) ==\n")
                pstats.Stats(pr, stream=fh).sort_stats(sort).print_stats(25)
        print(json.dumps(r, ensure_ascii=False))
        print("profile ->", out + ".txt")
        return
    index = {}
    if os.path.isfile(INDEX):
        with open(INDEX, "r", encoding="utf-8") as fh:
            index = json.load(fh)
    t0 = time.time()
    done = 0
    with Pool(a.workers, maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(run_cell, cells):
            done += 1
            if not r.get("skipped"):
                index[r["cell"]] = r
            print(f"[{done}/{len(cells)} {time.time() - t0:7.0f}s] {json.dumps(r, ensure_ascii=False)}", flush=True)
            with open(INDEX, "w", encoding="utf-8") as fh:
                json.dump(index, fh, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"done {done} cells in {time.time() - t0:.0f}s; index -> {INDEX}")


if __name__ == "__main__":
    main()

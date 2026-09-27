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
import gzip
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


def compress_exports(run_dir: str) -> None:
    """Disk (02:15 UTC: the machine ran out of space at 46 cells): after a cell's run, fills.json and
    orders.json -- the two largest exports, which neither the tables nor the dashboard read -- are gzipped
    in place (<name>.json.gz). The bytes are unchanged: repro.json's sha256 is of the uncompressed file
    (`gunzip -c fills.json.gz | sha256sum` reproduces it)."""
    for name in ("fills.json", "orders.json"):
        src = os.path.join(run_dir, name)
        if os.path.isfile(src):
            with open(src, "rb") as fi, gzip.open(src + ".gz", "wb", compresslevel=6) as fo:
                fo.write(fi.read())
            os.remove(src)


def cell_key(foot: int, s: str, b: str, strength: str) -> str:
    return f"{foot}|{gate_label(s, b)}|{strength}"


def run_cell(args):
    foot, s, b, strength = args
    key = cell_key(foot, s, b, strength)
    t0 = time.time()
    pa = plan_args(foot, s, b, strength)
    plan = plan_run(**pa)
    final = os.path.join(RUNS_DIR, plan.run_id)
    skipped = os.path.isfile(os.path.join(final, "repro.json"))
    if skipped:  # already run (the run id is the content hash): index it, do not run again
        with open(os.path.join(final, "repro.json"), "r", encoding="utf-8") as fh:
            identical = json.load(fh)["identical"]
        run_dir, wall, rss = final, None, None
    else:
        res = run(runs_dir=RUNS_DIR, **pa)
        run_dir, identical = res.run_dir, res.repro["identical"]
        wall = round(time.time() - t0, 1)
        rss = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    with open(os.path.join(run_dir, "trades.json"), "r", encoding="utf-8") as fh:
        n = len(json.load(fh)["data"])
    compress_exports(run_dir)
    return {"cell": key, "foot": foot, "gate": gate_label(s, b), "strength": strength, "run_id": plan.run_id,
            "identical": identical, "n_trades": n, "wall_s": wall, "max_rss_mb": rss, "skipped": skipped}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--strengths", nargs="+", default=list(STRENGTHS))
    ap.add_argument("--feet", type=int, nargs="+", default=list(FEET))
    ap.add_argument("--gates", nargs="+", default=None)
    ap.add_argument("--profile", action="store_true")
    ap.add_argument("--reindex", action="store_true", help="rebuild runs_index.json from the run records on disk (no run)")
    a = ap.parse_args()
    if a.reindex:
        index = {}
        if os.path.isfile(INDEX):
            with open(INDEX, "r", encoding="utf-8") as fh:
                index = json.load(fh)
        for rid in sorted(os.listdir(RUNS_DIR)):
            d = os.path.join(RUNS_DIR, rid)
            if not os.path.isfile(os.path.join(d, "repro.json")):
                continue
            with open(os.path.join(d, "record.json"), "r", encoding="utf-8") as fh:
                rec = json.load(fh)
            c = rec["config"]
            key = cell_key(c["foot_min"], c["gate"]["s"], c["gate"]["b"], c["strength"])
            if rec["purpose"] != "研究" or rec["data_sha256"] != {f"{DATA_DIR}/xbtusd_{c['foot_min']}m_2017_2019.csv.gz":
                                                               rec["data_sha256"][rec["data"][0]["path"]]}:
                continue
            old = index.get(key, {})
            if old.get("run_id") == rid:
                continue
            with open(os.path.join(d, "trades.json"), "r", encoding="utf-8") as fh:
                n = len(json.load(fh)["data"])
            with open(os.path.join(d, "repro.json"), "r", encoding="utf-8") as fh:
                identical = json.load(fh)["identical"]
            index[key] = {"cell": key, "foot": c["foot_min"], "gate": c["gate"]["s"] and gate_label(c["gate"]["s"], c["gate"]["b"]),
                          "strength": c["strength"], "run_id": rid, "identical": identical, "n_trades": n,
                          "wall_s": old.get("wall_s"), "max_rss_mb": old.get("max_rss_mb"), "skipped": False, "reindexed": True}
        with open(INDEX, "w", encoding="utf-8") as fh:
            json.dump(index, fh, ensure_ascii=False, indent=1, sort_keys=True)
        print(f"reindexed: {len(index)} cells -> {INDEX}")
        return
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
            if not r.get("skipped") or r["cell"] not in index:
                index[r["cell"]] = r
            print(f"[{done}/{len(cells)} {time.time() - t0:7.0f}s] {json.dumps(r, ensure_ascii=False)}", flush=True)
            with open(INDEX, "w", encoding="utf-8") as fh:
                json.dump(index, fh, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"done {done} cells in {time.time() - t0:.0f}s; index -> {INDEX}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""K1 env fixes (2026-09-27, delegation 20260927_k1_env_fixes §2-2 and §2-4): run stage A's 60-minute cells
(13 gates x 3 strengths = 39) through the INTEGRATED door `bot.bt.pipeline` (D-1: the venue rule
market_ref = last_bar_close, the "module" strategy bot.strategy.k1_wick:pipeline_strategy), with costs 0
and latency 0, and compare each cell with stage A's run record (backtest_runs/k1_newenv_a/, through
docs/PHASE2/K1/NEWENV_A/runs_index.json): number of trades, mean bp, and the fill columns (order id, time,
side, price, size, liquidity) of both sides of the fill range. Then (D-3) the 95% interval of each cell's
mean by `bot.bt.validation.day_block_bootstrap_ci` (blocks = the UTC day of the entry bar's start, 200
resamples, seed 20260909, alpha 0.05, cells with 30 trades or more: RESULT.md 1.5's rule text), set next
to stage A's `*` (docs/PHASE2/K1/NEWENV_A/cells.json). Comparison only; neither side is the answer.

Declarations: data = stage A's 60-minute bars (backtest_data/k1_newenv_a_20260927/xbtusd_60m_2017_2019.csv.gz);
product / rules = k1_wick.PIPELINE_PRODUCT / PIPELINE_RULES; fill tier 2 on both sides (K1 sends market
orders only: the tier decides resting orders); latency constant 0 on the four channels; costs maker 0 /
taker 0 / spread 0; account USD, cash 1e9, leverage 1, mark last_trade, no liquidation, margin check
position_only (K1's rule has no capital: the account must never refuse a one-unit order; a refusal would
show as a different number of trades); purpose 研究 with stage A's pre-registration docs/PHASE2/K1/PREREG.md.

The origin evidence of the integrated run (pipeline.row_evidence) compares the rows only with the files handed
to the run and the declared sources (round 2 of the env fixes, 2026-09-27): here the 60-minute file itself, so
no other file is opened and MARKET_ROOTS is not replaced (round 1 pointed it at a private folder with one link).
One output folder, one run at a time (E-12): the parent alone writes the
summary; the cells run in a pool of --workers processes (at most 3).

Outputs: <out-dir>/<run_id>/ (exports gzipped in place, as stage A did), and
docs/PHASE2/K1/NEWENV_A/fixes_pipeline.json (per cell: run id, counts, means, differences, interval).

Usage: PYTHONPATH=src python3 scripts/k1_newenv_fix_pipeline.py [--workers 3] [--gates ...] [--strengths ...]
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import resource
import sys
import tempfile
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.bt import pipeline as P  # noqa: E402
from bot.bt.validation import day_block_bootstrap_ci  # noqa: E402
from bot.strategy.k1_wick import PIPELINE_PRODUCT, PIPELINE_RULES, gate_label, gates  # noqa: E402
from k1_newenv_run import compress_exports, read_json, spec  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FOOT = 60
DATA = f"backtest_data/k1_newenv_a_20260927/xbtusd_{FOOT}m_2017_2019.csv.gz"
PREREG = "docs/PHASE2/K1/PREREG.md"
STAGE_A_RUNS = os.path.join(REPO, "backtest_runs", "k1_newenv_a")
STAGE_A_INDEX = os.path.join(REPO, "docs", "PHASE2", "K1", "NEWENV_A", "runs_index.json")
STAGE_A_CELLS = os.path.join(REPO, "docs", "PHASE2", "K1", "NEWENV_A", "cells.json")
SUMMARY = os.path.join(REPO, "docs", "PHASE2", "K1", "NEWENV_A", "fixes_pipeline.json")
STRENGTHS = ("both", "strong", "weak")
NS = 1_000_000_000
SEED, RESAMPLES, ALPHA, MIN_TRADES = 20260909, 200, 0.05, 30
ZERO = {"kind": "constant", "ns": 0}
FILL_COLS = ("order_id", "t_ns", "side", "px", "qty", "liquidity")
TRADE_COLS = ("side", "qty", "entry_px", "exit_px", "entry_t_ns", "exit_t_ns", "reason")


def plan(s: str, b: str, strength: str) -> P.PipelinePlan:
    return P.plan_pipeline(
        root=REPO,
        datasets=[{"name": "xbtusd_60m", "paths": [DATA], "spec": spec(FOOT), "origin": "real"}],
        instruments=[{"name": "XBTUSD", "price": "xbtusd_60m", "with": [], "product": dict(PIPELINE_PRODUCT),
                      "rules": dict(PIPELINE_RULES)}],
        strategy={"kind": "module", "module": "bot.strategy.k1_wick", "factory": "pipeline_strategy",
                  "params": {"s": s, "b": b, "strength": strength}},
        fill={"optimistic": {"tier": 2}, "pessimistic": {"tier": 2}},
        latency={"feed": ZERO, "order": ZERO, "cancel": ZERO, "notice": ZERO},
        costs={"maker_rate": 0, "taker_rate": 0, "spread": 0,
               "source": "K1 RESULT.md 1.4「経費は引いていない」: 費用 0(委任文 20260927_k1_env_fixes §2-2: 費用 0・遅延 0)"},
        account={"currency": "USD", "cash": 1e9, "leverage": 1, "mark": "last_trade", "liquidation": None,
                 "margin_check": "position_only"},
        purpose="研究", prereg=PREREG)


def bp(t: dict) -> float:
    sig = 1 if t["side"] == "buy" else -1
    return sig * (t["exit_px"] / t["entry_px"] - 1.0) * 1e4


def run_cell(args):
    s, b, strength, out_dir = args
    t0 = time.time()
    pl = plan(s, b, strength)
    final = os.path.join(out_dir, pl.run_id)
    if not os.path.isfile(os.path.join(final, "repro.json")):
        P.run_pipeline(pl, runs_dir=out_dir)
    compress_exports(final)
    wall = round(time.time() - t0, 1)
    rss = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    with open(os.path.join(final, "repro.json"), "r", encoding="utf-8") as fh:
        identical = json.load(fh)["identical"]
    return {"cell": f"{FOOT}|{gate_label(s, b)}|{strength}", "run_id": pl.run_id, "identical": identical,
            "wall_s": wall, "max_rss_mb": rss}


def compare(cell: dict, a_index: dict, a_cells: dict, out_dir: str) -> dict:
    key = cell["cell"]
    a_dir = os.path.join(STAGE_A_RUNS, a_index[key]["run_id"])
    a_tr = read_json(a_dir, "trades.json")["data"]
    a_fi = read_json(a_dir, "fills.json")["data"]
    p_dir = os.path.join(out_dir, cell["run_id"])
    p_tr_all = read_json(p_dir, "trades.json")["data"]
    p_fi_all = read_json(p_dir, "fills.json")["data"]
    rec = read_json(p_dir, "record.json")
    out = dict(cell)
    out["stage_a_run_id"] = a_index[key]["run_id"]
    out["origin_evidence"] = rec["data"][0]["origin_evidence"]
    a_mean = sum(bp(t) for t in a_tr) / len(a_tr) if a_tr else None
    out["stage_a"] = {"n_trades": len(a_tr), "n_fills": len(a_fi), "mean_bp": a_mean}
    for side in P.SIDES:
        p_tr = [t for t in p_tr_all if t["range"] == side]
        p_fi = [f for f in p_fi_all if f["range"] == side]
        p_mean = sum(bp(t) for t in p_tr) / len(p_tr) if p_tr else None
        fa = [tuple(f[c] for c in FILL_COLS) for f in a_fi]
        fp = [tuple(f[c] for c in FILL_COLS) for f in p_fi]
        ta = [tuple(t[c] for c in TRADE_COLS) for t in a_tr]
        tp = [tuple(t[c] for c in TRADE_COLS) for t in p_tr]
        first_fill_diff = next(({"i": i, "stage_a": x, "pipeline": y} for i, (x, y) in enumerate(zip(fa, fp)) if x != y),
                               None)
        out[side] = {"n_trades": len(p_tr), "n_fills": len(p_fi), "mean_bp": p_mean,
                     "same_n_trades": len(p_tr) == len(a_tr),
                     "same_mean_bp": p_mean == a_mean,
                     "same_fill_columns": fa == fp, "same_trade_columns": ta == tp,
                     "first_fill_difference": first_fill_diff}
    pess = [t for t in p_tr_all if t["range"] == "pessimistic"]
    if len(pess) >= MIN_TRADES:
        ci = day_block_bootstrap_ci([bp(t) for t in pess], [t["entry_t_ns"] - FOOT * 60 * NS for t in pess],
                                    n_resamples=RESAMPLES, seed=SEED, alpha=ALPHA)
        out["ci_day_block"] = {"lo": ci.lo, "hi": ci.hi, "estimate": ci.estimate, "n_days": ci.n_blocks,
                               "star": bool(ci.lo > 0 or ci.hi < 0)}
    else:
        out["ci_day_block"] = None
    a = a_cells.get(key)
    out["stage_a_table"] = None if a is None else {"mean_bp": a["mean_bp"], "ci95_bp": a["ci95_bp"], "star": a["star"]}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--strengths", nargs="+", default=list(STRENGTHS))
    ap.add_argument("--gates", nargs="+", default=None)
    ap.add_argument("--out-dir", default=os.path.join("backtest_runs", "k1_env_fixes", "pipeline"))
    ap.add_argument("--summary", default=SUMMARY)
    a = ap.parse_args()
    if a.workers > 3:
        raise SystemExit("at most 3 heavy processes at once (delegation)")
    out_dir = os.path.join(REPO, a.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    lock = os.path.join(out_dir, ".running")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)  # one run per output folder (E-12)
    except FileExistsError:
        raise SystemExit(f"{lock} exists: another run uses this output folder")
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    try:
        gs = [(s, b) for s, b in gates() if a.gates is None or gate_label(s, b) in a.gates]
        cells = [(s, b, st, out_dir) for st in a.strengths for s, b in gs]
        t0 = time.time()
        done = []
        with Pool(a.workers, maxtasksperchild=1) as pool:
            for r in pool.imap_unordered(run_cell, cells):
                done.append(r)
                print(f"[{len(done)}/{len(cells)} {time.time() - t0:6.0f}s] {json.dumps(r, ensure_ascii=False)}",
                      flush=True)
        with open(STAGE_A_INDEX, "r", encoding="utf-8") as fh:
            a_index = json.load(fh)
        with open(STAGE_A_CELLS, "r", encoding="utf-8") as fh:
            a_cells = json.load(fh)
        rows = sorted((compare(c, a_index, a_cells, out_dir) for c in done), key=lambda x: x["cell"])
        summary = {"made_by": "scripts/k1_newenv_fix_pipeline.py", "wall_s_total": round(time.time() - t0, 1),
                   "cells": rows}
        with open(a.summary, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, ensure_ascii=False, indent=1, sort_keys=True)
        n = len(rows)
        same = {k: sum(1 for r in rows if r["pessimistic"][k] and r["optimistic"][k])
                for k in ("same_n_trades", "same_mean_bp", "same_fill_columns", "same_trade_columns")}
        stars = [(r["ci_day_block"] or {}).get("star") == (r["stage_a_table"] or {}).get("star") for r in rows
                 if r["ci_day_block"] is not None and r["stage_a_table"] is not None]
        print(f"cells {n}; both sides equal to stage A: {same}; star equal {sum(stars)}/{len(stars)}; "
              f"reproduced {sum(1 for r in rows if r['identical'])}/{n} -> {a.summary}")
    finally:
        os.remove(lock)


if __name__ == "__main__":
    main()

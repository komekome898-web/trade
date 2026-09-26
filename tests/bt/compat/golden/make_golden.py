#!/usr/bin/env python3
"""Make the golden files of the OLD bar engine (item 4, old item 14: 「旧の出力は、
旧の実装を消す前に旧で作った旧の出力(golden)のファイル(`tests/bt/compat/golden/`、
種と入力つき)として残し」).

    PYTHONPATH=src python3 tests/bt/compat/golden/make_golden.py

Refuses to run unless `bot.backtest.engine.run_backtest` is the old
engine's own function (its module is bot.backtest.engine), so a golden file
is never made from the new engine. Writes old_engine_golden.json with, per
scene, its seed, grid cell, inputs and the old engine's outputs; plus the
metric function and the split on seeded inputs.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import compat_golden_scenes as S  # noqa: E402
from compat_golden_run import run  # noqa: E402


def metric_cases(seed: int, n: int):
    rng = random.Random(seed)
    out = []
    for k in range(n):
        m = rng.randint(0, 9)
        pnls = [rng.choice((0.0, rng.uniform(-80, 120), round(rng.uniform(-50, 50), 1))) for _ in range(m)]
        e = 6000.0
        eq = []
        for _ in range(rng.randint(0, 12)):
            e += rng.choice((0.0, rng.uniform(-30, 30)))
            eq.append(e)
        out.append({"trade_pnls": pnls, "equity": eq, "total_fees": rng.uniform(0, 20),
                    "periods_per_year": rng.choice((525600, 8760, 252))})
    return out


def split_cases(seed: int, n: int):
    rng = random.Random(seed)
    fr = (0.1, 0.2, 0.3, 0.5, 0.6, 0.7, 0.05, 0.15, 0.33)
    out = []
    for _ in range(n):
        out.append({"rows": rng.randint(0, 130), "train_frac": rng.choice(fr), "val_frac": rng.choice(fr)})
    return out


def main() -> None:
    import pandas as pd
    from bot.backtest import engine, metrics, walk_forward
    if engine.run_backtest.__module__ != "bot.backtest.engine" or not engine.__file__.endswith(
            os.path.join("src", "bot", "backtest", "engine.py")):
        sys.exit("bot.backtest.engine is not the old engine: a golden file is made from the old engine only")
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=HERE).stdout.strip()
    src_sha = {}
    for name in ("engine.py", "metrics.py", "walk_forward.py"):
        with open(os.path.join(HERE, "..", "..", "..", "..", "src", "bot", "backtest", name), "rb") as fh:
            src_sha[name] = hashlib.sha256(fh.read()).hexdigest()
    bars_out = []
    for sc in S.scenes() + S.EDGE_SCENES:
        try:
            out = run(engine, sc)
        except ValueError as exc:
            out = {"refused": str(exc)}
        bars_out.append({"scene": sc, "old": out})
    mcases = []
    for c in metric_cases(S.GOLDEN_SEED + 1, 400):
        m = metrics.compute_metrics(c["trade_pnls"], pd.Series(c["equity"], dtype=float), c["total_fees"],
                                    periods_per_year=c["periods_per_year"])
        mcases.append({"input": c, "old": m.as_dict()})
    scases = []
    for c in split_cases(S.GOLDEN_SEED + 2, 400):
        df = pd.DataFrame({"close": [float(i) for i in range(c["rows"])]})
        try:
            sp = walk_forward.split_data(df, train_frac=c["train_frac"], val_frac=c["val_frac"])
            out = {k: [int(x) for x in getattr(sp, k)["close"].tolist()]
                   for k in ("training", "validation", "out_of_sample")}
        except ValueError as exc:
            out = {"refused": str(exc)}
        scases.append({"input": c, "old": out})
    doc = {"made_with": {"git_head": head, "old_source_sha256": src_sha, "generator": "tests/bt/compat/golden/make_golden.py",
                         "seed": S.GOLDEN_SEED, "grid_cells": len(S.grid())},
           "bars": bars_out, "metrics": mcases, "splits": scases}
    path = os.path.join(HERE, "old_engine_golden.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")
    print(path, len(bars_out), "bar scenes", len(mcases), "metric cases", len(scases), "split cases")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""K1 段階 G(2026-10-01): 第 17 部の升を新しい環境で回す。1 升 = bot.bt.repro.runner.run(2 回実行して
byte で比べる)。データの門(k1_newenv_g_datagate)の下で回す。

入力: scripts/k1_newenv_g_fold.py が畳んだ足(backtest_data/k1_newenv_g_20261001/)。
  design / sameclose: data = [binance_{foot}m_{range}, bitflyer_{foot}m_{range}](d0 = 海外、d1 = bitFlyer)
  single(参考列 (i)): data = [binance_{foot}m_{range}]
升の鍵: {mode}|{range}|{foot}|{gate}|{strength}。実行記録は backtest_runs/k1_newenv_g/<run_id>/、
索引は docs/PHASE2/K1/NEWENV_G/runs_index.json。

使い方: PYTHONPATH=scripts:src python3 scripts/k1_newenv_g_run.py --modes design --ranges 2018_2021
        --feet 5 15 --gates s19/b24 --strengths weak [--workers 3]
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import resource
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import k1_newenv_g_datagate as GATE  # noqa: E402

from bot.bt.repro.runner import DataInput, plan_run, run  # noqa: E402
from bot.strategy.k1_wick import gate_label, gates  # noqa: E402
from bot.strategy.k1_xvenue import FILL_NAME, K1XSetup  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DATA_DIR = "backtest_data/k1_newenv_g_20261001"
RUNS_DIR = os.path.join(REPO, "backtest_runs", "k1_newenv_g")
INDEX = os.path.join(REPO, "docs", "PHASE2", "K1", "NEWENV_G", "runs_index.json")
PREREG = "docs/PHASE2/K1/XVENUE_PREREG.md"
COSTS = {"maker_fee_rate": 0, "taker_fee_rate": 0, "source": "K1 RESULT.md 1.4「経費は引いていない」: 費用 0"}


def spec(foot: int, symbol: str) -> dict:
    return {"format": "csv", "header": True, "delimiter": ",", "compression": "gzip", "kind": "bar",
            "symbol": symbol, "asset": "crypto", "time": {"columns": ["start_ts"], "unit": "iso", "tz": "UTC"},
            "fields": {"open": "o", "high": "h", "low": "l", "close": "c", "volume": "vol"},
            "bar": {"interval_s": foot * 60, "label": "start"}, "key": "start"}


def plan_args(mode, rng, foot, s, b, strength) -> dict:
    data = [DataInput(f"{DATA_DIR}/binance_{foot}m_{rng}.csv.gz", spec(foot, "BTCUSDT"))]
    if mode != "single":
        data.append(DataInput(f"{DATA_DIR}/bitflyer_{foot}m_{rng}.csv.gz", spec(foot, "FX_BTC_JPY")))
    cfg = {"instrument": "BTCUSDT" if mode == "single" else "FX_BTC_JPY", "foot_min": foot,
           "gate": {"s": s, "b": b}, "strength": strength, "mode": mode, "fill": FILL_NAME, "costs": COSTS}
    return dict(root=REPO, data=data, config=cfg, seed=0, setup=K1XSetup(), purpose="研究", prereg=PREREG)


def compress(run_dir: str) -> None:
    for name in ("fills.json", "orders.json", "trades.json", "metrics.json", "data_quality.json"):
        src = os.path.join(run_dir, name)
        if os.path.isfile(src):
            with open(src, "rb") as fi, gzip.open(src + ".gz", "wb", compresslevel=6) as fo:
                fo.write(fi.read())
            os.remove(src)


def key(mode, rng, foot, s, b, strength) -> str:
    return f"{mode}|{rng}|{foot}|{gate_label(s, b)}|{strength}"


def run_cell(args):
    mode, rng, foot, s, b, strength = args
    t0 = time.time()
    pa = plan_args(mode, rng, foot, s, b, strength)
    plan = plan_run(**pa)
    final = os.path.join(RUNS_DIR, plan.run_id)
    if os.path.isfile(os.path.join(final, "repro.json")):
        with open(os.path.join(final, "repro.json"), encoding="utf-8") as fh:
            ident = json.load(fh)["identical"]
        wall = rss = None
        skipped = True
    else:
        res = run(runs_dir=RUNS_DIR, **pa)
        ident = res.repro["identical"]
        wall = round(time.time() - t0, 1)
        rss = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
        skipped = False
    compress(final)
    return {"cell": key(*args), "mode": mode, "range": rng, "foot": foot, "gate": gate_label(s, b), "strength": strength,
            "run_id": plan.run_id, "identical": ident, "wall_s": wall, "max_rss_mb": rss, "skipped": skipped,
            "opened": [os.path.relpath(p, REPO) for p in GATE.OPENED]}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--modes", nargs="+", default=["design"])
    ap.add_argument("--ranges", nargs="+", default=["2018_2021"])
    ap.add_argument("--feet", type=int, nargs="+", default=[5, 15])
    ap.add_argument("--gates", nargs="+", default=None)
    ap.add_argument("--strengths", nargs="+", default=["weak"])
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    gs = [(s, b) for s, b in gates() if a.gates is None or gate_label(s, b) in a.gates]
    cells = [(m, r, f, s, b, st) for m in a.modes for r in a.ranges for f in a.feet for s, b in gs for st in a.strengths]
    index = {}
    if os.path.isfile(INDEX):
        with open(INDEX, encoding="utf-8") as fh:
            index = json.load(fh)
    t0 = time.time()
    with Pool(a.workers, maxtasksperchild=1) as pool:
        for i, r in enumerate(pool.imap_unordered(run_cell, cells), 1):
            if os.path.isfile(INDEX):  # 他の実行が書いた分を残す(読み直してから足す)
                with open(INDEX, encoding="utf-8") as fh:
                    index = json.load(fh)
            if not r["skipped"] or r["cell"] not in index:
                index[r["cell"]] = r
            with open(INDEX, "w", encoding="utf-8") as fh:
                json.dump(index, fh, ensure_ascii=False, indent=1, sort_keys=True)
            print(f"[{i}/{len(cells)} {time.time() - t0:6.0f}s] {json.dumps({k: v for k, v in r.items() if k != 'opened'}, ensure_ascii=False)}", flush=True)
    print(f"done {len(cells)} cells in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()

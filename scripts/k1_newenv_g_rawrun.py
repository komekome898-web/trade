#!/usr/bin/env python3
"""K1 段階 G を閉じる委任(docs/DATA/delegations/20261001_k1_stage_g_close.md §2-6): G-1〜G-3 の直しの後の口で、
段階 G の 2 升 `design|2018_2021|15|s19/b24|weak`・`design|2018_2021|5|s19/b24|weak` を生のファイルから回し、
docs/PHASE2/K1/NEWENV_G/cells.json の同じ升と取引数・平均 bp を並べる。データの門
(scripts/k1_newenv_g_datagate.py)の下で回す。

口(写しを作らない):
  - 記録の口 bot.bt.repro.runner に、封印の台帳(P2-08)に載った生の 1 分足を範囲つきで渡す(G-3: DataInput.range_ns)。
    Binance BTCUSDT 現物 2018〜2021 の 4 ファイル(d0〜d3)と bitFlyer FX_BTC_JPY 2018〜2021 の 4 ファイル(d4〜d7)。
    範囲はファイルごとに [その年の 1 月 1 日, 翌年の 1 月 1 日)(段階 G の畳み k1_newenv_g_fold.py の読みと同じ)
  - 約定の無い分: Binance は synthetic(n_trades == "0")→ drop、bitFlyer は no_trade(OHLC が全部空)→ drop
    (G-2 の宣言。写しを作らない)。両方とも session 24x7(G-4)、gap = accept、off_grid = accept
  - 結合・畳みは K1XSetup の prepare(config prepare = "join_fold")、流れの名前 signal / price(G-1)
升の値は scripts/k1_newenv_g_tables.py の stats と同じ式(r = sig × (決済値 / 建値 − 1) × 10⁴、平均は単純平均)を
ここで書き直したもの(表の側のスクリプトは別の作業者が直しているので import しない)。

出力: backtest_runs/k1_newenv_g_close/<run_id>/(*.json は gzip)、
      docs/PHASE2/K1/NEWENV_G/rawrun_compare.json(升ごとの取引数・平均 bp と cells.json の値、一致したか)

使い方: PYTHONPATH=scripts:src python3 scripts/k1_newenv_g_rawrun.py [--feet 15 5]
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import resource
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import k1_newenv_g_datagate as GATE  # noqa: E402

from bot.bt.repro.runner import DataInput, plan_run, run  # noqa: E402
from bot.strategy.k1_xvenue import FILL_NAME, K1XSetup  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RUNS_DIR = os.path.join(REPO, "backtest_runs", "k1_newenv_g_close")
OUT = os.path.join(REPO, "docs", "PHASE2", "K1", "NEWENV_G", "rawrun_compare.json")
CELLS = os.path.join(REPO, "docs", "PHASE2", "K1", "NEWENV_G", "cells.json")
BIN_DIR = "backtest_data/binance_BTCUSDT_1m_20170801_20231231"
BF_DIR = "backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906"
PREREG = "docs/PHASE2/K1/XVENUE_PREREG.md"
COSTS = {"maker_fee_rate": 0, "taker_fee_rate": 0, "source": "K1 RESULT.md 1.4「経費は引いていない」: 費用 0"}
NS = 1_000_000_000
YEARS = (2018, 2019, 2020, 2021)
OHLCV = {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"}


def ns_of(s: str) -> int:
    return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()) * NS


def _spec(symbol: str, tcol: str) -> dict:
    return {"format": "csv", "header": True, "delimiter": ",", "compression": "gzip", "kind": "bar",
            "symbol": symbol, "asset": "crypto", "time": {"columns": [tcol], "unit": "iso", "tz": "UTC"},
            "fields": OHLCV, "bar": {"interval_s": 60, "label": "start", "session": "24x7"}, "key": "start"}


BIN_SPEC = {**_spec("BTCUSDT", "open_time"), "synthetic": {"column": "n_trades", "values": ["0"]}}
BF_SPEC = {**_spec("FX_BTC_JPY", "ts"), "no_trade": {"fields": ["open", "high", "low", "close"]}}
BIN_RESOLVE = {"synthetic": "drop", "gap": "accept", "off_grid": "accept"}
BF_RESOLVE = {"no_trade": "drop", "gap": "accept", "off_grid": "accept"}


def year_range(y: int) -> tuple[int, int]:
    return (ns_of(f"{y}-01-01T00:00:00"), ns_of(f"{y + 1}-01-01T00:00:00"))


def plan_args(foot: int, s: str = "19", b: str = "24", strength: str = "weak") -> dict:
    data = [DataInput(f"{BIN_DIR}/binance_BTCUSDT_1m_{y}.csv.gz", BIN_SPEC, BIN_RESOLVE, year_range(y)) for y in YEARS]
    data += [DataInput(f"{BF_DIR}/candles_1m_{y}.csv.gz", BF_SPEC, BF_RESOLVE, year_range(y)) for y in YEARS]
    n = len(YEARS)
    cfg = {"instrument": "FX_BTC_JPY", "foot_min": foot, "gate": {"s": s, "b": b}, "strength": strength,
           "mode": "design", "fill": FILL_NAME, "costs": COSTS, "prepare": "join_fold",
           "streams": {"signal": [f"d{i}" for i in range(n)], "price": [f"d{i}" for i in range(n, 2 * n)]}}
    return dict(root=REPO, data=data, config=cfg, seed=0, setup=K1XSetup(), purpose="研究", prereg=PREREG)


def stats(trades: list) -> dict:
    rs = [(1 if t["side"] == "buy" else -1) * (t["exit_px"] / t["entry_px"] - 1.0) * 1e4 for t in trades]
    return {"n": len(rs), "mean_bp": sum(rs) / len(rs) if rs else None}


def read_json(path: str):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def compress(run_dir: str) -> None:
    for name in ("fills.json", "orders.json", "trades.json", "metrics.json", "data_quality.json"):
        src = os.path.join(run_dir, name)
        if os.path.isfile(src):
            with open(src, "rb") as fi, gzip.open(src + ".gz", "wb", compresslevel=6) as fo:
                fo.write(fi.read())
            os.remove(src)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--feet", type=int, nargs="+", default=[15, 5])
    a = ap.parse_args()
    with open(CELLS, encoding="utf-8") as fh:
        cells = json.load(fh)
    out = {}
    if os.path.isfile(OUT):
        out = read_json(OUT)
    for foot in a.feet:
        key = f"design|2018_2021|{foot}|s19/b24|weak"
        t0 = time.time()
        pa = plan_args(foot)
        plan = plan_run(**pa)
        res = run(runs_dir=RUNS_DIR, **pa)
        final = os.path.join(RUNS_DIR, plan.run_id)
        wall = round(time.time() - t0, 1)
        trades_export = read_json(os.path.join(final, "trades.json"))
        trades = trades_export["data"] if isinstance(trades_export, dict) and "data" in trades_export else trades_export
        dq = read_json(os.path.join(final, "data_quality.json"))
        rec = read_json(os.path.join(final, "record.json"))
        compress(final)
        got = stats(trades)
        old = cells[key]
        dsets = (dq.get("data", dq) if isinstance(dq, dict) else dq)["manifest"]["datasets"]
        out[key] = {
            "run_id": plan.run_id, "identical": res.repro["identical"], "wall_s": wall,
            "max_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
            "new": got, "stage_g": {"n": old["n"], "mean_bp": old["mean_bp"], "run_id": old["run_id"]},
            "n_equal": got["n"] == old["n"], "mean_bp_equal": got["mean_bp"] == old["mean_bp"],
            "mean_bp_diff": (got["mean_bp"] - old["mean_bp"]) if got["mean_bp"] is not None else None,
            "record_data_ranges": [{"path": d["path"], "range_ns": d.get("range_ns")} for d in rec["data"]],
            "data_quality": {n: {"rows": v["rows"], "anomalies": v["anomalies"], "resolution": v["resolution"]}
                             for n, v in dsets.items()},
            "opened": sorted({os.path.relpath(p, REPO) for p in GATE.OPENED}),
        }
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1, sort_keys=True)
        print(json.dumps({k: out[key][k] for k in ("run_id", "identical", "wall_s", "max_rss_mb", "new", "stage_g",
                                                    "n_equal", "mean_bp_equal")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()

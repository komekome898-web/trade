#!/usr/bin/env python3
"""K1 stage A (2026-09-27, L-479): the tables 2.1-2.4 of docs/PHASE2/K1/RESULT.md,
made from the new environment's run records (docs/PHASE2/K1/NEWENV_A/runs_index.json
-> backtest_runs/k1_newenv_a/<run_id>/trades.json).

Per cell (RESULT.md 1.4-1.5): r = sig x (exit close / entry close - 1) x 1e4 [bp] from
each round trip's entry_px / exit_px / side; mean(r), sd, n, holding bars (bar index of
the exit minus bar index of the entry; the indices come from the foot file the run
read, so a bar with no trade does not exist), exit reasons, per-year means (by the
entry bar's year), and the 95% interval by the day block bootstrap of RESULT.md 1.5
(blocks = the entry bar's UTC day, days drawn with replacement, 200 draws, seed
20260909, one random.Random over the cells in K1's loop order: foot 1..60, gate, strength
strong/weak/both). `*` = the interval does not straddle 0. Cells with fewer than 30
trades are left out (RESULT.md 1.5).

Outputs: docs/PHASE2/K1/NEWENV_A/TABLES.md and cells.json (every number of the tables).

Usage: PYTHONPATH=src python3 scripts/k1_newenv_tables.py
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from bot.bt.data import load  # noqa: E402
from bot.strategy.k1_wick import gate_label, gates  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT_DIR = os.path.join(REPO, "docs", "PHASE2", "K1", "NEWENV_A")
INDEX = os.path.join(OUT_DIR, "runs_index.json")
RUNS_DIR = os.path.join(REPO, "backtest_runs", "k1_newenv_a")
DATA_DIR = "backtest_data/k1_newenv_a_20260927"
FEET = (1, 3, 5, 15, 30, 60)
STRENGTHS = ("strong", "weak", "both")
SEED = 20260909
BOOTSTRAP = 200
NS = 1_000_000_000
TABLE_24_GATES = ("s-/b-", "s19/b24", "s30/b40", "soff/b40")


def spec(foot: int) -> dict:
    return {"format": "csv", "header": True, "delimiter": ",", "compression": "gzip", "kind": "bar",
            "symbol": "XBTUSD", "asset": "crypto",
            "time": {"columns": ["start_ts"], "unit": "iso", "tz": "UTC"},
            "fields": {"open": "o", "high": "h", "low": "l", "close": "c", "volume": "vol"},
            "bar": {"interval_s": foot * 60, "label": "start"}, "key": "start"}


def bar_index(foot: int) -> dict[int, int]:
    """bar CLOSE time (ns) -> index, from the foot file the runs read (through the data layer)."""
    r = load(REPO, [{"name": "d", "paths": [f"{DATA_DIR}/xbtusd_{foot}m_2017_2019.csv.gz"], "spec": spec(foot)}])
    iv = foot * 60 * NS
    return {rec["start_ns"] + iv: i for i, rec in enumerate(r.records("d"))}


def block_bootstrap(rs_by_day: dict[int, list[float]], rng: random.Random) -> tuple[float, float]:
    days = list(rs_by_day.values())
    means = []
    for _ in range(BOOTSTRAP):
        pool: list[float] = []
        for _ in range(len(days)):
            pool.extend(days[rng.randrange(len(days))])
        if pool:
            means.append(sum(pool) / len(pool))
    means.sort()
    return means[int(0.025 * (len(means) - 1))], means[int(0.975 * (len(means) - 1))]


def cell_stats(run_id: str, foot: int, idx: dict[int, int], rng: random.Random) -> dict | None:
    with open(os.path.join(RUNS_DIR, run_id, "trades.json"), "r", encoding="utf-8") as fh:
        trades = json.load(fh)["data"]
    if len(trades) < 30:
        return None
    rs, holds, why, byday, byyear = [], [], {}, {}, {}
    for t in trades:
        sig = 1 if t["side"] == "buy" else -1
        r = sig * (t["exit_px"] / t["entry_px"] - 1.0) * 1e4
        rs.append(r)
        ei, xi = idx[t["entry_t_ns"]], idx[t["exit_t_ns"]]
        holds.append(xi - ei)
        why[t["reason"]] = why.get(t["reason"], 0) + 1
        entry_start_s = (t["entry_t_ns"] - foot * 60 * NS) // NS
        byday.setdefault(entry_start_s // 86400, []).append(r)
        y = datetime.fromtimestamp(entry_start_s, tz=timezone.utc).year
        byyear.setdefault(str(y), []).append(r)
    n = len(rs)
    mean = sum(rs) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in rs) / (n - 1))
    lo, hi = block_bootstrap(byday, rng)
    holds.sort()
    return {"n": n, "mean_bp": round(mean, 3), "ci95_bp": [round(lo, 3), round(hi, 3)], "sd_bp": round(sd, 1),
            "hold_median": holds[n // 2], "exit_reasons": why,
            "per_year": {y: {"n": len(v), "mean_bp": round(sum(v) / len(v), 3)} for y, v in sorted(byyear.items())},
            "star": bool(lo > 0 or hi < 0), "run_id": run_id}


def fmt(c: dict | None) -> str:
    if c is None:
        return "(未測定)"
    v = f"{c['mean_bp']:+.2f}"
    return f"**{v}\\***" if c["star"] else v


def table(cells: dict, strength: str, title: str) -> list[str]:
    out = [f"## {title}", "", "| 門 | " + " | ".join(f"{f} 分" for f in FEET) + " |", "|---|" + "---|" * len(FEET)]
    for s, b in gates():
        g = gate_label(s, b)
        name = f"`{g}`(当時の規則)" if g == "s19/b24" else f"`{g}`"
        out.append(f"| {name} | " + " | ".join(fmt(cells.get(f"{f}|{g}|{strength}")) for f in FEET) + " |")
    return out + [""]


def main() -> None:
    with open(INDEX, "r", encoding="utf-8") as fh:
        index = json.load(fh)
    rng = random.Random(SEED)
    cells: dict[str, dict] = {}
    missing = []
    for foot in FEET:
        idx = None
        for s, b in gates():
            for st in STRENGTHS:
                key = f"{foot}|{gate_label(s, b)}|{st}"
                if key not in index:
                    missing.append(key)
                    continue
                if idx is None:
                    idx = bar_index(foot)
                c = cell_stats(index[key]["run_id"], foot, idx, rng)
                if c is not None:
                    cells[key] = c
    lines = ["# K1 段階 A — 新しい環境で出た表(RESULT.md 第 2 部と同じ形)", "",
             "生成: `PYTHONPATH=src python3 scripts/k1_newenv_tables.py`(入力 = `runs_index.json` → "
             "`backtest_runs/k1_newenv_a/<run_id>/trades.json`。実行 = `scripts/k1_newenv_run.py`、"
             "畳み = `scripts/k1_newenv_fold.py`)。", "",
             "**表の `*` は 95% 信頼区間が 0 を跨がないセル。** 単位は bp。`(未測定)` = 実行記録が無い升。",
             "統計の定義は RESULT.md 1.5 のとおり(日単位ブロックブートストラップ 200 回・種 20260909・"
             "取引 30 件未満は出さない)。**これは新しい環境の出力であり、当時の値との一致・不一致の裁きは DIFF.md。**", ""]
    lines += table(cells, "both", "2.1 強さ = 両方")
    lines += table(cells, "strong", "2.2 強さ = 強い(下ヒゲ陽線 / 上ヒゲ陰線)")
    lines += table(cells, "weak", "2.3 強さ = 弱い(上ヒゲ陽線 / 下ヒゲ陰線)")
    lines += ["## 2.4 取引数と保有本数の中央値(強さ = 両方)", "",
              "| 門 | " + " | ".join(f"{f} 分" for f in FEET) + " |", "|---|" + "---|" * len(FEET)]
    for g in TABLE_24_GATES:
        row = []
        for f in FEET:
            c = cells.get(f"{f}|{g}|both")
            row.append("(未測定)" if c is None else f"{c['n']:,} / {c['hold_median']}")
        lines.append(f"| {g} | " + " | ".join(row) + " |")
    lines += ["", "## 2.5 決済理由の構成(強さ = 両方、門 `s19/b24`)", "",
              "| 足 | 無効化(損切り) | 反対の弱いシグナル | ドテン |", "|---|---|---|---|"]
    for f in FEET:
        c = cells.get(f"{f}|s19/b24|both")
        if c is None:
            lines.append(f"| {f} 分 | (未測定) | | |")
            continue
        w = c["exit_reasons"]
        tot = sum(w.values())
        lines.append(f"| {f} 分 | {100 * w.get('invalidated', 0) / tot:.1f}% | {100 * w.get('opposite_weak', 0) / tot:.1f}% | "
                     f"{100 * w.get('reversed', 0) / tot:.1f}% |")
    lines += ["", f"測っていない升: {len(missing)} / {6 * 13 * 3}" + (f" — {', '.join(missing)}" if missing else ""), ""]
    with open(os.path.join(OUT_DIR, "TABLES.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    with open(os.path.join(OUT_DIR, "cells.json"), "w", encoding="utf-8") as fh:
        json.dump(cells, fh, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"cells {len(cells)}, missing {len(missing)} -> {OUT_DIR}/TABLES.md, cells.json")


if __name__ == "__main__":
    main()

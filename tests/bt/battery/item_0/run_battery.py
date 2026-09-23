#!/usr/bin/env python3
"""Run the item-0 scene set against one target, twice, and write a TSV.

    PYTHONPATH=src python3 run_battery.py --target current_impl --out OUT.tsv
    PYTHONPATH=src python3 run_battery.py --target new_impl     --out OUT.tsv
    PYTHONPATH=src python3 run_battery.py --target mutant       --out OUT.tsv
    <venv>/bin/python run_battery.py --target opp_<name>        --out OUT.tsv
    python3 run_battery.py --target repro_<name>                --out OUT.tsv
    python3 run_battery.py --list-targets

Each survey tool runs under the interpreter of its own isolated venv
(scratchpad `bt/venvs/item_0/<name>/`); reproductions run under plain
python3 (standard library only).

Columns: scene_id, viewpoint, kind, correctness (正解と一致 / 対応なし /
不一致 / 結果なし), reproducibility (2 回の実行で同じ / 2 回で違う /
結果なし), status and output of run 1 and run 2, expected, detail of run 1.
Correctness is decided here, never by the adapter: a dict `expected` must
match the same keys in the output (extra keys in the output are ignored),
anything else must be equal.
"""
from __future__ import annotations

import argparse
import csv
import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "adapters"))
sys.path.insert(0, str(HERE.parents[3] / "src"))

from scenes import SCENES  # noqa: E402
from adapters.protocol import Adapter, SceneResult  # noqa: E402

# opp_<name> -> (module under opponents/, class name)
OPPONENTS = {
    "opp_basana": ("basana_adapter", "BasanaAdapter"),
    "opp_ziplime": ("ziplime_adapter", "ZiplimeAdapter"),
    "opp_zipline_reloaded": ("zipline_reloaded_adapter", "ZiplineReloadedAdapter"),
    "opp_lib_pybroker": ("lib_pybroker_adapter", "LibPybrokerAdapter"),
    "opp_qf_lib": ("qf_lib_adapter", "QfLibAdapter"),
    "opp_backtrader": ("backtrader_adapter", "BacktraderAdapter"),
    "opp_hftbacktest": ("hftbacktest_adapter", "HftbacktestAdapter"),
    "opp_rqalpha": ("rqalpha_adapter", "RqalphaAdapter"),
    "opp_fast_trade": ("fast_trade_adapter", "FastTradeAdapter"),
    "opp_pybotters": ("pybotters_adapter", "PybottersAdapter"),
    "opp_backtesting": ("backtesting_adapter", "BacktestingAdapter"),
    "opp_qstrader": ("qstrader_adapter", "QstraderAdapter"),
    "opp_quantcore": ("quantcore_adapter", "QuantcoreAdapter"),
    "opp_finmarketpy": ("finmarketpy_adapter", "FinmarketpyAdapter"),
    "opp_quanttrader": ("quanttrader_adapter", "QuanttraderAdapter"),
    "opp_aat": ("aat_adapter", "AatAdapter"),
    "opp_pyalgotrade": ("pyalgotrade_adapter", "PyalgotradeAdapter"),
    "opp_octobot": ("octobot_adapter", "OctobotAdapter"),
    "opp_freqtrade": ("freqtrade_adapter", "FreqtradeAdapter"),
    "opp_vnpy": ("vnpy_adapter", "VnpyAdapter"),
}


def _repro_targets() -> dict[str, tuple[str, str]]:
    out = {}
    for p in sorted((HERE / "opponents").glob("repro_*.py")):
        out[p.stem] = (p.stem, "Adapter")
    return out


def load_adapter(target: str) -> Adapter:
    if target == "current_impl":
        from adapters.current_impl import CurrentImplAdapter
        return CurrentImplAdapter()
    if target == "new_impl":
        import bot.bt.core as core
        mod = importlib.import_module("adapters.new_impl")
        return mod.make_adapter(core)
    if target == "mutant":
        from mutant import make_mutant_adapter
        return make_mutant_adapter()
    table = {**OPPONENTS, **_repro_targets()}
    if target in table:
        mod_name, cls = table[target]
        mod = importlib.import_module(f"opponents.{mod_name}")
        return getattr(mod, cls)()
    raise SystemExit(f"unknown target {target!r}; known: current_impl, new_impl, mutant, {', '.join(sorted(table))}")


def _matches(output, expected) -> bool:
    if isinstance(expected, dict):
        return isinstance(output, dict) and all(k in output and output[k] == v for k, v in expected.items())
    return output == expected


def correctness(res: SceneResult, expected) -> str:
    if res.status == "not_supported":
        return "対応なし"
    if res.status == "ok":
        return "正解と一致" if _matches(res.output, expected) else "不一致"
    return "結果なし"  # error: the target ran into an exception, no result to grade


def reproducibility(a: SceneResult, b: SceneResult) -> str:
    if a.status == "error" and b.status == "error":
        return "結果なし"
    same = (a.status, json.dumps(a.output, sort_keys=True, default=repr)) == \
           (b.status, json.dumps(b.output, sort_keys=True, default=repr))
    return "2 回の実行で同じ" if same else "2 回で違う"


def run_target(target: str) -> list[dict]:
    rows = []
    adapter_1 = load_adapter(target)
    adapter_2 = load_adapter(target)  # a fresh adapter for the second run
    for sc in SCENES:
        r1 = adapter_1.run_scene(sc)
        r2 = adapter_2.run_scene(sc)
        rows.append({
            "target": target, "scene_id": sc.id, "viewpoint": sc.viewpoint, "kind": sc.kind,
            "correctness": correctness(r1, sc.expected),
            "correctness_run2": correctness(r2, sc.expected),
            "reproducibility": reproducibility(r1, r2),
            "status_1": r1.status, "output_1": json.dumps(r1.output, ensure_ascii=False, sort_keys=True, default=repr),
            "status_2": r2.status, "output_2": json.dumps(r2.output, ensure_ascii=False, sort_keys=True, default=repr),
            "expected": json.dumps(sc.expected, ensure_ascii=False, sort_keys=True),
            "detail_1": r1.detail.replace("\t", " ").replace("\n", " "),
        })
    return rows


FIELDS = ["target", "scene_id", "viewpoint", "kind", "correctness", "correctness_run2", "reproducibility",
          "status_1", "output_1", "status_2", "output_2", "expected", "detail_1"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--list-targets", action="store_true")
    a = ap.parse_args()
    if a.list_targets:
        print("\n".join(["current_impl", "new_impl", "mutant", *OPPONENTS, *_repro_targets()]))
        return
    if not a.target or not a.out:
        ap.error("--target and --out are required")
    rows = run_target(a.target)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["correctness"]] = counts.get(r["correctness"], 0) + 1
    diff = sum(1 for r in rows if r["reproducibility"] == "2 回で違う")
    print(f"{a.target}: {len(rows)} scenes -> {a.out}; {counts}; 2 回で違う={diff}")


if __name__ == "__main__":
    main()

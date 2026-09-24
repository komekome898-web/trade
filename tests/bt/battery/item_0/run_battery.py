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
anything else must be equal. For a scene with `graded_from` (scenes.py), the
adapter only reports what it observed (the delivered order, each attempt and
its exception) and the
values that are graded are computed HERE by `GRADERS[scene.id]`; the output
column then holds those graded values plus the raw output under "raw". For
the P0-5 scenes the order a target must produce comes from its rule in
`stated_rules.py` (fixed by the scene keeper before any run, round r5-1),
applied here to the scene's own input.
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
import stated_rules  # noqa: E402
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
    "opp_pyalgotrade": ("pyalgotrade_adapter", "PyalgotradeAdapter"),
    "opp_freqtrade": ("freqtrade_adapter", "FreqtradeAdapter"),
    "opp_vnpy": ("vnpy_adapter", "VnpyAdapter"),
    "opp_luczinsritter": ("luczinsritter_adapter", "LuczinsritterAdapter"),
    "opp_mihircoding_lob": ("mihircoding_lob_adapter", "MihircodingLobAdapter"),
    "opp_nickgardi_orderbooksim": ("nickgardi_orderbooksim_adapter", "NickgardiOrderbooksimAdapter"),
    "opp_daniyalmlk_slippage": ("daniyalmlk_slippage_adapter", "DaniyalmlkSlippageAdapter"),
    "opp_akurkar07_orderbook": ("cpp_lob_adapters", "Akurkar07OrderbookAdapter"),
    "opp_3yit_lob": ("cpp_lob_adapters", "ThreeyitLobAdapter"),
    "opp_jxm35_lob": ("cpp_lob_adapters", "Jxm35LobAdapter"),
    "opp_pysystemtrade": ("pysystemtrade_adapter", "PysystemtradeAdapter"),
    "opp_predictivedev_tradesim": ("predictivedev_tradesim_adapter", "PredictivedevTradesimAdapter"),
    "opp_sarthak_execsim": ("sarthak_execsim_adapter", "SarthakExecsimAdapter"),
    "opp_sigc": ("sigc_adapter", "SigcAdapter"),
    "opp_homerun": ("homerun_adapter", "HomerunAdapter"),
    "opp_aat": ("aat_adapter", "AatAdapter"),
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


def _contains_number(v, x: float) -> bool:
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float)):
        return float(v) == x
    if isinstance(v, dict):
        return any(_contains_number(u, x) for u in v.values())
    if isinstance(v, (list, tuple)):
        return any(_contains_number(u, x) for u in v)
    return False


def _pairs(seq) -> list:
    return [[str(k), int(t)] for k, t in (seq or [])]


def _grade_future_reads(sc, out: dict, target: str | None = None) -> dict:
    atts = list(out.get("attempts") or [])
    named = [a for a in atts if a.get("form") in ("time", "position")]
    fv = float(sc.input["future_value"])
    return {"every_attempt_stopped_by_error": bool(named) and all(a.get("raised") for a in named),
            "future_value_obtained": any(_contains_number(a.get("returned"), fv) for a in atts)}


def _all_tie_events(sc) -> list:
    return sorted([e["kind"], e["ts_ns"]] for evs in sc.input["streams"].values() for e in evs)


def _rule_order(rule, sc, hand_over) -> list | None:
    """The order the target's stated rule (stated_rules.py, fixed by the scene
    keeper) gives for this scene's streams in this hand-over order; None when
    the target has no stated rule or the rule leaves a tie."""
    if rule is None:
        return None
    try:
        return stated_rules.predicted(rule, sc.input["streams"], list(hand_over))
    except stated_rules.RuleDoesNotDecide:
        return None


def _grade_stated_rule_once(sc, out: dict, target: str | None = None) -> dict:
    order = _pairs(out.get("order"))
    want = _rule_order(stated_rules.rule_for(target), sc, sc.input["hand_over_order"])
    return {"delivered_as_multiset": sorted(order),
            "follows_stated_rule": want is not None and order == want}


def _grade_hand_over(sc, out: dict, target: str | None = None) -> dict:
    """Each run i is the scene's own hand-over order i (the adapter's report of
    it must agree); the expected order of run i is the stated rule applied to
    that hand-over order here, never a list the adapter wrote."""
    runs = list(out.get("runs") or [])
    want = _all_tie_events(sc)
    hand_overs = [list(o) for o in sc.input["hand_over_orders"]]
    complete = len(runs) == len(hand_overs) and all(list(r.get("hand_over") or []) == h for r, h in zip(runs, hand_overs))
    orders = [_pairs(r.get("order")) for r in runs]
    rule = stated_rules.rule_for(target)
    form = out.get("form")
    per_run = [_rule_order(rule, sc, h) for h in hand_overs]
    return {"every_run_delivers_each_once": complete and all(sorted(o) == want for o in orders),
            "every_run_follows_stated_rule": complete and rule is not None and form == rule.form
            and all(p is not None and o == p for o, p in zip(orders, per_run)),
            "same_order_whatever_the_hand_over": complete and (
                form == "single_input"
                or (form == "multi_input" and len({json.dumps(o) for o in orders}) == 1))}


# scene id -> grader; exactly the scenes with `graded_from` (test_battery_item0.py checks)
GRADERS = {
    "p4-future-read-attempt": _grade_future_reads,
    "p5-same-time-twice": _grade_stated_rule_once,
    "p5-hand-over-order": _grade_hand_over,
}


def graded_output(res: SceneResult, scene, target: str | None = None):
    """What is graded: the raw output, or for a `graded_from` scene the values
    computed here from it (the raw output kept under "raw"). `target` selects
    the stated same-time rule (stated_rules.py) for the P0-5 scenes; without
    it no rule applies."""
    if scene is None or scene.id not in GRADERS or res.status != "ok":
        return res.output
    raw = res.output if isinstance(res.output, dict) else {}
    return {**GRADERS[scene.id](scene, raw, target), "raw": res.output}


def correctness(res: SceneResult, expected, scene=None, target: str | None = None) -> str:
    if res.status == "not_supported":
        return "対応なし"
    if res.status == "ok":
        return "正解と一致" if _matches(graded_output(res, scene, target), expected) else "不一致"
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
            "correctness": correctness(r1, sc.expected, sc, target),
            "correctness_run2": correctness(r2, sc.expected, sc, target),
            "reproducibility": reproducibility(r1, r2),
            "status_1": r1.status,
            "output_1": json.dumps(graded_output(r1, sc, target), ensure_ascii=False, sort_keys=True, default=repr),
            "status_2": r2.status,
            "output_2": json.dumps(graded_output(r2, sc, target), ensure_ascii=False, sort_keys=True, default=repr),
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

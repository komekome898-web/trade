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
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "adapters"))
sys.path.insert(0, str(HERE.parents[3] / "src"))

from scenes import JP, NAMING_SHAPES, SCENES, TYPE_ORDER, UNIT_SCENES, for_target_types  # noqa: E402
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
    "opp_gobacktest": ("gobacktest_adapter", "GobacktestAdapter"),
    "opp_pineforge": ("pineforge_adapter", "PineforgeAdapter"),
    "opp_barter": ("barter_adapter", "BarterAdapter"),
    "opp_pytrendfollow": ("pytrendfollow_adapter", "PytrendfollowAdapter"),
    "opp_thirupathikannan_execsim": ("thirupathikannan_execsim_adapter", "ThirupathikannanExecsimAdapter"),  # round r13-1
    "opp_isaaccheng_obsim": ("isaaccheng_obsim_adapter", "IsaaccengObsimAdapter"),
}


def _repro_targets() -> dict[str, tuple[str, str]]:
    out = {}
    for p in sorted((HERE / "opponents").glob("repro_*.py")):
        out[p.stem] = (p.stem, "Adapter")
    return out


def split_target(target: str) -> tuple[str, str]:
    """(the target, the label of its configured target) of `<target>[@<label>]` (round r8-1)."""
    base, _, label = target.partition("@")
    return base, label


def _module_path(base: str) -> Path | None:
    if base == "current_impl":
        return HERE / "adapters" / "current_impl.py"
    if base in ("new_impl", "mutant"):
        return HERE / "adapters" / "new_impl.py"
    table = {**OPPONENTS, **_repro_targets()}
    return HERE / "opponents" / f"{table[base][0]}.py" if base in table else None


def configured_targets(base: str) -> list[str]:
    """Every configured target of a target (round r8-1, positive definition A):
    the labels of the adapter class's `CONFIGS`, read from the adapter file
    without importing it (an opponent imports only in its own venv)."""
    import ast
    path = _module_path(base)
    if path is None:
        raise SystemExit(f"unknown target {base!r}")
    cls = {**OPPONENTS, **_repro_targets()}.get(base, (None, None))[1]
    labels = [""]
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ClassDef) and (cls is None or node.name == cls):
            for st in node.body:
                if isinstance(st, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "CONFIGS" for t in st.targets):
                    labels = [ast.literal_eval(k) for k in st.value.keys]  # the labels (keys) are literal strings
    return [base if lab == "" else f"{base}@{lab}" for lab in labels]


def load_adapter(target: str) -> Adapter:
    base, label = split_target(target)
    if base == "current_impl":
        from adapters.current_impl import CurrentImplAdapter
        return CurrentImplAdapter(label)
    if base in ("new_impl", "mutant"):
        if label:
            raise SystemExit(f"{base} has one configured target (no label): {target!r}")
        if base == "new_impl":
            import bot.bt.core as core
            mod = importlib.import_module("adapters.new_impl")
            return mod.make_adapter(core)
        from mutant import make_mutant_adapter
        return make_mutant_adapter()
    table = {**OPPONENTS, **_repro_targets()}
    if base in table:
        mod_name, cls = table[base]
        mod = importlib.import_module(f"opponents.{mod_name}")
        return getattr(mod, cls)(label)
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
    # a naming the target's language cannot write (a compiled driver's `expressible: False`) is neither a stop nor a pass
    named = [a for a in atts if a.get("form") in ("time", "position") and a.get("expressible", True)]
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


def _grade_times(sc, out: dict, target: str | None = None) -> dict:
    """p1-one-call-per-event (round r7-1): the times of the events the
    strategy received, one per call; the type column is not graded."""
    seq = out.get("sequence")
    return {"observed_ts_ns": [int(p[1]) for p in seq] if isinstance(seq, list)
            and all(isinstance(p, (list, tuple)) and len(p) == 2 for p in seq) else None}


def _grade_unit_time(sc, out: dict, target: str | None = None) -> dict:
    """The P0-2 unit scenes (round r16-1, critic i0-r15-05): the time the target made, read by the adapter from the
    target's time type exactly (`ns`), counts only as an int64 integer -- an int that is not a bool, or a numpy
    integer; a float (even one equal to an int), a bool, a decimal, a text or a value outside int64 grades as null."""
    v = out.get("ns") if isinstance(out, dict) else None
    kind = getattr(getattr(v, "dtype", None), "kind", None) if type(v).__module__ == "numpy" else None
    is_int = type(v) is int or kind in ("i", "u")
    return {"int64_ns": int(v) if is_int and -2 ** 63 <= int(v) < 2 ** 63 else None}


# scene id -> grader; exactly the scenes with `graded_from` (test_battery_item0.py checks)
GRADERS = {
    "p1-one-call-per-event": _grade_times,
    "p4-future-read-attempt": _grade_future_reads,
    "p5-same-time-twice": _grade_stated_rule_once,
    "p5-hand-over-order": _grade_hand_over,
    **{i: _grade_unit_time for i in UNIT_SCENES},
}


# ---------------------------------------------------------------- provenance (round r6-1, r6-2)
# Where the measured thing came from is checked BEFORE grading (critic
# i0-r5-02 / i0-r5-03 / i0-r5-04): an event type the scene-set side made, a
# conversion or a list outside the target, or an incomplete set of namings is
# not graded -- the scene becomes "error" (結果なし) with the reason.
#
# Round r6-2 (critic br6-1-1 / br6-1-2): the check is POSITIVE. A thing is the
# target's only when the file it comes from lies in the target's own
# distribution (the directories below, found by the import system of the
# target's interpreter) -- never because its name is not on a list of the
# scene set's names. Shared types (builtins.dict, functions, datetime, pandas,
# numpy rows, numba boxes) are placed by how they reached the strategy
# (common.py: passed_by / returned_by / code_file / dtype / tag), and only
# records common.py made from objects are accepted.
#
# Round r6-3 (critic br6-2-1): the type says only that the target HAS the type;
# that the object REACHED the strategy through the target is a second, separate
# check applied to every type, the target's own classes included (`delivered`):
# the target's code passed it (or an object holding it) into the strategy's
# call, the target's compiled code did (common.native_tracker), or a target
# function returned it. An object of the target's class that the scene-set side
# built inside the strategy's call, or holds without ever handing it over, is
# not the target's delivery.

import common as C  # noqa: E402  (the same module object the adapters use: its registry is checked)

REPO = HERE.parents[3]

# target -> the target's own distribution: Python top modules ("py") and the
# heads of a compiled driver's type names ("compiled"). Written here, not by
# the adapters. A reproduction (opponents/repro_*.py) is its own file.
TARGET_DISTS: dict[str, dict] = {
    "new_impl": {"py": ["bot.bt"]}, "mutant": {"py": ["bot.bt"]},
    "current_impl": {"py": ["bot.backtest", "bot.strategy"]},
    "opp_basana": {"py": ["basana"]}, "opp_ziplime": {"py": ["ziplime"]}, "opp_zipline_reloaded": {"py": ["zipline"]},
    "opp_lib_pybroker": {"py": ["pybroker"]}, "opp_qf_lib": {"py": ["qf_lib"]}, "opp_backtrader": {"py": ["backtrader"]},
    "opp_hftbacktest": {"py": ["hftbacktest"]}, "opp_rqalpha": {"py": ["rqalpha"]}, "opp_fast_trade": {"py": ["fast_trade"]},
    "opp_pybotters": {"py": ["pybotters"]}, "opp_backtesting": {"py": ["backtesting"]}, "opp_qstrader": {"py": ["qstrader"]},
    "opp_quantcore": {"py": ["quantcore"]}, "opp_finmarketpy": {"py": ["finmarketpy"]},
    "opp_quanttrader": {"py": ["quanttrader"]}, "opp_pyalgotrade": {"py": ["pyalgotrade"]},
    "opp_freqtrade": {"py": ["freqtrade"]}, "opp_vnpy": {"py": ["vnpy", "vnpy_ctastrategy"]},
    "opp_luczinsritter": {"py": ["backtest_engine", "tradeanalysis"]}, "opp_mihircoding_lob": {"py": ["src"]},
    "opp_nickgardi_orderbooksim": {"py": ["matching_engine", "models"]}, "opp_daniyalmlk_slippage": {"py": ["slippage"]},
    "opp_akurkar07_orderbook": {"py": ["lob_cpp"], "compiled": ["cpp:akurkar07"]},
    "opp_3yit_lob": {"py": ["lob_cpp"], "compiled": ["cpp:3yit"]}, "opp_jxm35_lob": {"py": ["lob_cpp"], "compiled": ["cpp:jxm35"]},
    "opp_pysystemtrade": {"py": ["sysdata", "systems", "syscore", "sysquant", "sysobjects"]},
    "opp_predictivedev_tradesim": {"py": ["trading_simulator"]},
    "opp_sarthak_execsim": {"compiled": ["cpp:execution_simulator"]}, "opp_sigc": {"compiled": ["c:sigc"]},
    "opp_homerun": {"py": ["services"]}, "opp_aat": {"py": ["aat"]},
    "opp_gobacktest": {"compiled": ["go:*gobacktest.", "go:github.com/dirkolbrich/gobacktest"]},
    "opp_pineforge": {"compiled": ["c:pineforge"]},
    "opp_barter": {"compiled": ["rust:barter_data::", "rust:barter::", "rust:barter_integration::"]},  # r16-1: + the workspace crate of the epoch deserializers
    "opp_pytrendfollow": {"py": ["trading"]}, "opp_thirupathikannan_execsim": {"py": ["src"]}, "opp_isaaccheng_obsim": {"py": ["order_book_simulator"]},
}
COMPILED = ("rust:", "go:", "c:", "cpp:")

# scene id -> (key of the received list in the output, whether the list carries kinds)
CARRIER_SCENES = {
    "p1-merge-by-time": ("sequence", True), "p1-one-call-per-event": ("sequence", True),
    "p1-typed-events": ("sequence", True),
    "p2-event-time-exact": ("observed_ts_ns", False), "p2-one-ns-apart": ("observed_ts_ns", False),
    **{f"p3-{k}": ("sequence", True) for k in ("trade", "book_snapshot", "book_delta", "bar", "funding", "liquidation")},
    "p3-mixed-one-run": ("sequence", True),
    "p5-same-time-twice": ("order", True), "p5-hand-over-order": ("runs", True),
    "p5-same-stream-order": ("prices", False),
}
# the scenes whose value is a time the target read (round r16-1: the unit scenes join the ISO scenes)
READER_SCENES = {"p2-iso-utc", "p2-iso-offset", *UNIT_SCENES}
PROVENANCE_SCENES = set(CARRIER_SCENES) | READER_SCENES | {"p4-visible-at-step", "p4-future-read-attempt"}


class Roots:
    """The target's own places: directories / files of its Python
    distribution and the heads of its compiled names."""

    def __init__(self, dirs: list[str], heads: list[str], missing: list[str]) -> None:
        self.dirs, self.heads, self.missing = dirs, heads, missing

    def has_file(self, path) -> bool:
        if not path or not isinstance(path, str) or not os.path.isabs(path):
            return False
        p = os.path.realpath(path)
        return any(p == d or p.startswith(d + os.sep) for d in self.dirs)

    def has_name(self, name) -> bool:
        return isinstance(name, str) and any(name.startswith(h) for h in self.heads)


_ROOTS: dict[str, Roots] = {}


def roots_of(target: str | None) -> Roots:
    """Resolve TARGET_DISTS[target] in THIS interpreter (the target's venv).
    A place inside the scene set is refused for every target, and a place
    inside this repository is refused for a survey tool."""
    target = split_target(target)[0] if target else target  # a configured target has its target's places
    if target in _ROOTS:
        return _ROOTS[target]
    import importlib.util
    spec = dict(TARGET_DISTS.get(target or "", {}))
    if target and target.startswith("repro_"):
        # round r6-3: the reproduced engine is its own file under opponents/repro_engines/
        # (the adapter side, opponents/repro_<name>.py, is the scene set's)
        spec = {"py": [f"opponents.repro_engines.{target[len('repro_'):]}"]}
    dirs, missing = [], []
    for mod in spec.get("py", []):
        try:
            s = importlib.util.find_spec(mod)
        except (ImportError, ValueError):
            s = None
        if s is None:
            missing.append(mod)
            continue
        places = list(s.submodule_search_locations or []) or ([s.origin] if s.origin else [])
        for pl in places:
            rp = os.path.realpath(pl)
            if C.in_scene_set(rp):  # a reproduction's engine (opponents/repro_engines/) is not the scene set's
                raise SystemExit(f"{target}: {mod} resolves into the scene set ({rp})")
            if (target or "").startswith("opp_") and (rp == str(REPO) or rp.startswith(str(REPO) + os.sep)):
                raise SystemExit(f"{target}: {mod} resolves into this repository ({rp}), not the tool's distribution")
            dirs.append(rp)
    r = Roots(dirs, list(spec.get("compiled", [])), missing)
    _ROOTS[target] = r
    return r


def _made(x) -> bool:
    return isinstance(x, (C.Record, C.Made)) and C.made_here(x)


def origin_problem(rec, roots: Roots, what: str, means: bool = False) -> str | None:
    """Why `rec` (a common.py record / name) is not shown to be the target's, or None.
    `means=True` (a read's `of` / an attempt's `via`): a function or method whose
    code is the target's is the target's means by its code alone -- code carries
    no event, so how the strategy came to hold it is not asked (round r6-3)."""
    if not _made(rec):
        return f"{what} が common.py で物から作った記録でない(手で書いた値): {str(rec)[:120]}"
    if isinstance(rec, C.Made):
        if rec.compiled:
            return None if roots.has_name(rec) else f"{what} の翻訳した道具の名前 {rec!s:.120} が対象の名前の頭 {roots.heads} に無い"
        return None if roots.has_file(rec.file) else f"{what} {rec!s:.120} の定義のファイル {rec.file} が対象の配布物に無い"
    parts = []
    own = roots.has_file(rec.get("type_file")) or roots.has_file((rec.get("dtype") or {}).get("type_file"))
    if not own and rec.get("type_file") and C.in_scene_set(rec.get("type_file")):
        return f"{what} {rec.get('type')} は場面集の側の型"
    if not own and rec.get("held_by") and not roots.has_file(rec.get("code_file")):
        # (T) a shared type is the target's only when the target made the object
        parts.append(f"{what} {rec.get('type')} は共有の型で、場面集の側が持つ物と同じ物({rec.get('held_by')}): "
                     "adapter が渡した物を対象が転送しただけ")
    if not delivered(rec, roots) and not (means and roots.has_file(rec.get("code_file"))):
        # (D) round r6-3 (br6-2-1): for every type, the target must have delivered the object
        parts.append(f"{what} {rec.get('type')} は{'対象の型' if own else '共有の型'}だが、対象が戦略に届けたことを示せない"
                     f"(対象のコードが戦略の呼び出しに渡した passed_by {rec.get('passed_by')}・渡した物の中にあった reached_by "
                     f"{rec.get('reached_by')}・母語のコードが渡した native_by {rec.get('native_by')}・対象の関数が返した "
                     f"returned_by {rec.get('returned_by')}(戦略の呼び出しの中の読みに限る。呼び出した物 {rec.get('read_in_call_by')}・"
                     f"利用者の回しの中 {rec.get('read_in_user_loop')}) のどれも対象の配布物に無い)")
    tag = rec.get("tag")
    if tag is not None and not roots.has_file(tag.get("type_file")):
        parts.append(f"{what} の札 {tag.get('const') or tag.get('type')}.{tag.get('name')} が対象の配布物の物でない({tag.get('type_file')})")
    return "; ".join(parts) or None


DELIVERY_FACTS = ("passed_by", "reached_by", "native_by")


def delivered(rec, roots: Roots) -> bool:
    """(D) The object reached the strategy through the target's code: the
    target's code passed it (or an object holding it) into the strategy's call,
    compiled code of the target did, or a target function returned it."""
    return any(roots.has_file(f) for k in DELIVERY_FACTS for f in (rec.get(k) or [])) or \
        (roots.has_file(rec.get("returned_by")) and read_in_call(rec, roots))


def read_in_call(rec, roots: Roots) -> bool:
    """Round r8-1 (positive definition A (3)): a read counts as the strategy's only when it was made inside a strategy
    call -- the target's code (or its compiled code) called the strategy, or an adapter's `user_loop_call` block of a
    target the user drives with his own loop was open (common.call_context). A read made after the run is not."""
    return any(roots.has_file(f) for f in (rec.get("read_in_call_by") or [])) or rec.get("read_in_user_loop") is True


def _key(rec) -> str:
    """The carrier's identity for 'one type, one kind': the object's type and its tag."""
    if isinstance(rec, dict):
        tag = rec.get("tag") or {}
        return f"{rec.get('type')}[{tag.get('const') or tag.get('type')}.{tag.get('name')}]" if tag else \
            f"{rec.get('type')}" + (f"<{rec['dtype']['name']}>" if rec.get("dtype") else "")
    return str(rec)


def _carrier_problem(kinds: list | None, carriers, roots: Roots) -> str | None:
    if not isinstance(carriers, list) or kinds is None or len(carriers) != len(kinds):
        return f"carriers の長さが受け取った列と合わない(列 {None if kinds is None else len(kinds)} 件、carriers {len(carriers) if isinstance(carriers, list) else carriers!r:.80})"
    for c in carriers:
        why = origin_problem(c, roots, "carrier")
        if why:
            return why
    if kinds and not isinstance(kinds[0], (int, float)):
        by: dict[str, set] = {}
        for k, c in zip(kinds, carriers):
            by.setdefault(_key(c), set()).add(str(k))
        many = {c: sorted(ks) for c, ks in by.items() if len(ks) > 1}
        if many:
            return f"1 つの型に 2 つ以上の kind を写した(型を場面集の側が決めている): {many}"
    return None


def _kinds(out, key: str, with_kinds: bool):
    lst = out.get(key) if isinstance(out, dict) else None
    if not isinstance(lst, list):
        return None
    return [e[0] if with_kinds and isinstance(e, (list, tuple)) and e else e for e in lst]


def _touched_ok(item: dict, roots: Roots, what: str) -> str | None:
    """A read / an attempt is the target's when target code ran during it, or
    the object it read through (`of` / `via`) is the target's. Round r8-1 (positive definition A (3)): and it was
    made inside a strategy call (common.call_context); a compiled driver's attempt (no Python stack) is read by
    the critic from the driver's code."""
    through = item.get("via") if item.get("via") is not None else item.get("of")
    by_driver = isinstance(through, C.Made) and through.compiled  # made inside a compiled tool's driver
    if "in_call_by" in item and not by_driver and not read_in_call({"read_in_call_by": item.get("in_call_by"),
                                                                    "read_in_user_loop": item.get("in_user_loop")}, roots):
        return (f"{what} {item.get('means')!r:.80} は戦略の呼び出しの中で行った物と示せない(呼び出した物 {item.get('in_call_by')}・"
                f"利用者の回しの中 {item.get('in_user_loop')})")
    if any(roots.has_file(f) for f in (item.get("touched") or [])):
        return None
    for k in ("of", "via"):
        if item.get(k) is not None:
            return origin_problem(item[k], roots, f"{what} の {k}", means=True)
    return f"{what} {item.get('means')!r:.80} の間に対象のコードが 1 行も走らず、読んだ物(of / via)も無い"


def _attempts_problem(out, roots: Roots) -> str | None:
    atts = (out or {}).get("attempts") if isinstance(out, dict) else None
    if not isinstance(atts, list):
        return "attempts が無い"
    groups: dict[tuple, set] = {}
    for a in atts:
        shape, form = a.get("shape"), a.get("form")
        if shape is None:
            return f"試し {a.get('means')!r} に shape が無い(common.try_position_namings / try_time_namings を通していない)"
        means = str(a.get("means", ""))
        compiled = means.startswith(COMPILED)
        if not _made(a):
            return f"試し {means!r:.80} が common.Attempts で記録されていない(手で書いた記録)"
        if compiled:
            if not roots.heads or not any(means.startswith(h.split(":")[0] + ":") for h in roots.heads):
                return f"試し {means!r:.80} は翻訳した道具の手段だが、対象は翻訳した道具でない"
        else:
            why = _touched_ok(a, roots, "試し")
            if why:
                return why
        if a.get("raised") and a.get("raised_by_scene_set_raise") and shape != "other":  # a stop is credited to named reads only
            return f"試し {means!r:.80} の例外 {a.get('raised')} は場面集の側の raise 文で起きた(対象が止めたのではない)"
        if shape == "other":
            continue
        if shape == "no_means":  # graded like any named read: a value returned is a read that was not stopped
            if form not in ("time", "position"):
                return f"no_means の試し {a.get('means')!r} の form が time / position でない"
            continue
        if shape not in NAMING_SHAPES:
            return f"未知の shape {shape!r}"
        if (shape.startswith("time") and form != "time") or (not shape.startswith("time") and form != "position"):
            return f"試し {a.get('means')!r} の shape {shape} と form {form} が合わない"
        if a.get("expressible", True) is False and not compiled:
            return f"試し {a.get('means')!r} を書けない名指しとしたが、手段がコンパイルした道具の driver のものでない"
        groups.setdefault((a.get("means"), shape), set()).add(a.get("naming"))
    for (means, shape), got in groups.items():
        want = set(NAMING_SHAPES[shape])
        if got != want:
            return f"手段 {means!r}({shape})の名指し方が一覧と合わない: 欠け {sorted(want - got)} / 一覧に無い {sorted(got - want)}"
    return None


def _reads_problem(out, prov, roots: Roots) -> str | None:
    reads = (prov or {}).get("reads")
    if not isinstance(reads, list) or not reads:
        return "reads が無い(過去を読む公開の手段が無い対象は not_supported)"
    for r in reads:
        vals = r.get("returned")
        if not isinstance(vals, list) or not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in vals):
            return f"読み出し {r.get('means')!r} の返り値が終値の列でない"
        if not _made(r):
            return f"読み出し {r.get('means')!r:.80} が common.Reads で記録されていない(手で書いた記録)"
        why = _touched_ok(r, roots, "読み出し")
        if why:
            return why
    counts = sorted({len(r["returned"]) for r in reads})
    closes = [x for r in reads for x in r["returned"]]
    want = {"visible_count": counts[0] if len(counts) == 1 else counts, "max_visible_close": max(closes) if closes else None}
    got = {k: (out or {}).get(k) for k in want} if isinstance(out, dict) else None
    if got != want:
        return f"出力 {got} が読み出しから作った値 {want} と合わない"
    return None


def _reader_problem(reader, roots: Roots) -> str | None:
    if reader is None or (isinstance(reader, str) and not reader):
        return "reader が無い"
    why = origin_problem(reader, roots, "時刻を読んだ関数")
    return f"時刻を読んだのが対象の外の関数: {why}" if why else None


def provenance_problem(res: SceneResult, scene, target: str | None = None, roots: Roots | None = None) -> str | None:
    """Why this result may not be graded, or None. Only `ok` results of the
    PROVENANCE_SCENES are checked (a refusal or an exception has nothing to
    credit)."""
    if scene is None or res.status != "ok" or scene.id not in PROVENANCE_SCENES:
        return None
    roots = roots or roots_of(target)
    out, prov = res.output, res.provenance
    if scene.id == "p4-future-read-attempt":
        return _attempts_problem(out, roots)
    if not isinstance(prov, dict):
        return "provenance が無い"
    if scene.id == "p4-visible-at-step":
        return _reads_problem(out, prov, roots)
    if scene.id in READER_SCENES:
        return _reader_problem(prov.get("reader"), roots)
    key, with_kinds = CARRIER_SCENES[scene.id]
    carriers = prov.get("carriers")
    if scene.id == "p5-hand-over-order":
        runs = out.get("runs") if isinstance(out, dict) else None
        if not isinstance(runs, list) or not isinstance(carriers, list) or len(carriers) != len(runs):
            return "carriers が回ごとの列になっていない"
        flat_k, flat_c = [], []
        for r, cs in zip(runs, carriers):
            ks = _kinds(r, "order", True)
            why = _carrier_problem(ks, cs, roots)
            if why:
                return why
            flat_k += ks
            flat_c += cs
        return _carrier_problem(flat_k, flat_c, roots)
    return _carrier_problem(_kinds(out, key, with_kinds), carriers, roots)


def compact(prov, roots: Roots):
    """What is written to the record: `touched` keeps only the target's files
    (with the count of all), so the table stays readable."""
    def walk(x):
        if isinstance(x, dict):
            out = {}
            for k, v in x.items():
                if k == "touched" and isinstance(v, list):
                    out[k] = [f for f in v if roots.has_file(f)]
                    out["touched_count"] = len(v)
                elif k == "held_by" and v and roots.has_file(x.get("type_file")):
                    out[k] = v
                    out["input"] = "adapter が対象の型で組んで対象に渡した入力(対象が届けた)"
                else:
                    out[k] = walk(v)
            return out
        if isinstance(x, list):
            return [walk(v) for v in x]
        return x
    return walk(prov)


ATTEMPT_PROVENANCE = ("touched", "via", "raised_file", "raised_by_scene_set_raise")


def _provenance_out_of_output(res: SceneResult) -> SceneResult:
    """The attempts' provenance (common.Attempts) is moved from the output to
    the provenance column: it is checked, not graded, and must not decide
    '2 回の実行で同じ' (file lists and records are not the target's result)."""
    out = res.output
    if not (isinstance(out, dict) and isinstance(out.get("attempts"), list)
            and any(isinstance(a, dict) and any(k in a for k in ATTEMPT_PROVENANCE) for a in out["attempts"])):
        return res
    kept = [{k: v for k, v in a.items() if k not in ATTEMPT_PROVENANCE} if isinstance(a, dict) else a for a in out["attempts"]]
    prov = dict(res.provenance) if isinstance(res.provenance, dict) else {}
    prov["attempts"] = [{"means": a.get("means"), "naming": a.get("naming"), **{k: a[k] for k in ATTEMPT_PROVENANCE if k in a}}
                        for a in out["attempts"] if isinstance(a, dict)]
    return SceneResult(res.status, output={**out, "attempts": kept}, detail=res.detail, provenance=prov)


def setting_problem(rec, roots: Roots) -> str | None:
    """Why a recorded setting (common.configure*) is not shown to be made
    through the target's public means, or None (round r8-1, positive
    definition A (1)): the record was made by common.py from the call, and
    the function called is the target's (its code file, or the code that ran
    during the call, lies in the target's distribution; for a compiled
    driver, its name is in the target's namespace)."""
    if not _made(rec):
        return f"設定の操作 {str(rec)[:120]} が common.py で呼び出しから作った記録でない(手で書いた値)"
    refused = [d for d in rec.get("decided_from") or [] if d not in C.DECIDED_FROM]
    if refused or not rec.get("decided_from"):
        return (f"設定の操作 {rec.get('fn')!s:.120}({rec.get('what')!s:.80})は {refused or '何から決めたかの記録なし'} "
                "から決めた(正の定義 A (1): 実行の前に利用者が知りうる物と、その操作までに戦略が受けた物だけから決まる設定でない)")
    if rec.get("when") not in C.WHEN and not str(rec.get("when", "")).startswith("その他: "):
        return f"設定の操作 {rec.get('fn')!s:.120} の時点 {rec.get('when')!r} が書き残す語でない"
    if rec.get("compiled"):
        return None if roots.has_name(rec.get("fn")) else \
            f"設定の操作 {rec.get('fn')!s:.120} の翻訳した道具の名前が対象の名前の頭 {roots.heads} に無い"
    if roots.has_file(rec.get("fn_file")) or any(roots.has_file(f) for f in (rec.get("touched") or [])):
        return None
    return (f"設定の操作 {rec.get('fn')!s:.120}({rec.get('what')!s:.80})の関数 {rec.get('fn_file')} も、"
            "呼び出しの間に走ったコードも、対象の配布物に無い")


def settings_problem(settings, roots: Roots) -> str | None:
    if not isinstance(settings, list):
        return f"設定の操作の列が list でない: {settings!r:.80}"
    for rec in settings:
        why = setting_problem(rec, roots)
        if why:
            return why
    return None


def compact_settings(settings, roots: Roots) -> list:
    """The settings as written into the output: the function, where its code
    is (relative to the target's place), what, when, decided from."""
    out = []
    for r in settings or []:
        f = r.get("fn_file") or ""
        for d in roots.dirs:
            if f == d or f.startswith(d + os.sep):
                f = os.path.basename(d) + f[len(d):]
                break
        out.append({"fn": r.get("fn"), "at": f"{f}:{r.get('line')}" if f else None, "what": r.get("what"),
                    "when": r.get("when"), "decided_from": r.get("decided_from")})
    return out


def checked(res: SceneResult, scene, target: str | None = None, roots: Roots | None = None,
            settings: list | None = None) -> SceneResult:
    """The result as graded: unchanged, or "error" when its provenance or one
    of its settings (round r8-1) fails."""
    why = provenance_problem(res, scene, target, roots)
    if why is None and res.status == "ok" and settings is not None:
        why = settings_problem(settings, roots or roots_of(target))
    res = _provenance_out_of_output(res)
    if why is None:
        return res
    return SceneResult("error", output={"provenance_error": why, "raw": res.output},
                       detail=f"出所の検めで採点しない: {why} / {res.detail}", provenance=res.provenance)


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


# ---------------------------------------------------------------- the target's own types (round r7-1, r8-1)
# Scenes that need several event types (`Scene.type_plan`; the four scenes of
# P0-1 and P0-5 that L-438 (2) names) take them from the types of the
# configured target, from the P0-3 type scenes of the same run (critic
# i0-r6-02; positive definition A of round r8-1): a type of the configured
# target is one whose p3-<type> scene, after the provenance and settings
# checks, was graded "正解と一致". A type whose p3 scene was 不一致, 対応なし
# or 結果なし is not had (L-438 (2): a type whose values do not match is not
# counted). The adapter never chooses them.
TYPE_SCENES = [f"p3-{k}" for k in TYPE_ORDER]
_SCENE_BY_ID = {sc.id: sc for sc in SCENES}


def target_types(p3_grades: dict[str, str]) -> list[str]:
    """The configured target's types: the p3-<type> scenes of one run graded 正解と一致."""
    return [k for k in TYPE_ORDER if p3_grades.get(f"p3-{k}") == "正解と一致"]


def _types_detail(p3_grades: dict[str, str]) -> str:
    return " / ".join(f"p3-{k}: {p3_grades.get(f'p3-{k}', 'なし')}" for k in TYPE_ORDER)


def _run_one(adapter: Adapter, sc) -> tuple[SceneResult, list]:
    """Run one scene with the settings log reset before it (round r8-1) and the records of round r13-1 reset
    (`common.records_begin`; read back by `records_of`)."""
    C.settings_begin()
    C.records_begin()
    with C.native_tracker():  # round r6-3: a strategy called from compiled code shows the caller (native_by)
        raw = adapter.run_scene(sc)
    return raw, C.settings_taken()


# ---------------------------------------------------------------- round r13-1: records (never used for the table)
# LEAD_DESIGN.md section 9.2 item 33: per scene and configured target, the market event types that entered the target
# (`types_in`), the types that reached the strategy although the input handed had none of them (`types_added`, a type
# the adapter replaced), and the requests the strategy made (`requests`). The grid table (grid_c.py) never reads them;
# `grid_c.not_entered` turns them into the materials role's note. For a scene without a list of what reached the
# strategy, `types_in` is the input's types less those an adapter replaced through adapters/common.py (`as_bar`,
# `substitute`; test_battery_r13_claims.py checks no adapter replaces a type elsewhere), limited to the configured
# target's own types (the P0-3 grades of the same run, L-438 (2)): a type the target does not have did not enter as
# that type, whatever the adapter did (ROOTCAUSE_r13-1.md section 2, root 7).
def _input_kinds(inp) -> list[str]:
    """The market event types (TYPE_ORDER names, in that order) of an input's `events` and `streams`."""
    inp = inp if isinstance(inp, dict) else {}
    evs = list(inp.get("events") or [])
    for stream in (inp.get("streams") or {}).values():
        evs += list(stream)
    have = {e.get("kind") for e in evs if isinstance(e, dict)}
    return [k for k in TYPE_ORDER if k in have]


def _delivered_kinds(res: SceneResult, scene) -> list | None:
    """The types in the list of what reached the strategy (the scenes whose provenance check reads a kind for each
    delivered item), or None when the scene or the result has no such list."""
    key = CARRIER_SCENES.get(scene.id)
    if key is None or not key[1] or res.status != "ok" or not isinstance(res.output, dict):
        return None
    if scene.id == "p5-hand-over-order":
        runs = res.output.get("runs")
        if not isinstance(runs, list):
            return None
        out: list = []
        for r in runs:
            out += _kinds(r, "order", True) or []
        return out
    return _kinds(res.output, key[0], True)


def records_of(scene_run, res: SceneResult, called: bool, substituted: list, requests, records_requests: bool,
               own_types) -> dict:
    """`types_in` / `types_added` (scenes.JP names) and `requests` of one run (see the comment above); `own_types` =
    the configured target's own types (TYPE_ORDER names) known when the scene ran."""
    if not called:
        return {"types_in": [], "types_added": [], "requests": [] if records_requests else None}
    handed = _input_kinds(scene_run.input)
    delivered = _delivered_kinds(res, scene_run)
    if delivered is not None:
        got = {str(k) for k in delivered}
        types_in = [k for k in handed if k in got]
        added = sorted(got - set(handed))
    else:
        types_in = [k for k in handed if k not in set(substituted) and k in set(own_types)]
        added = []
    return {"types_in": [JP[k] for k in types_in], "types_added": [JP.get(k, k) for k in added],
            "requests": list(requests) if records_requests else None}


def run_for_types(adapter: Adapter, sc, p3_grades: dict[str, str]):
    """(the scene as run for this configured target, its raw result, its
    settings, its round r13-1 raw records). A scene with a type_plan is built from the configured target's
    types; when they are too few the adapter is not called and the scene is
    対応なし with the p3 grades."""
    rec = run_for_types_records(adapter, sc, p3_grades)
    return rec[0], rec[1], rec[2]


def run_for_types_records(adapter: Adapter, sc, p3_grades: dict[str, str]):
    """run_for_types plus (called, substituted types, requests) of the run (round r13-1)."""
    if sc.type_plan is None:
        raw, settings = _run_one(adapter, sc)
        return sc, raw, settings, True, C.substituted_taken(), C.requests_taken()
    types = target_types(p3_grades)
    conc = for_target_types(sc, types)
    head = f"型の選び方(runner、第 r8-1 回): 設定つき対象の持つ型 {types}"
    if conc is None:
        return sc, SceneResult("not_supported", detail=(
            f"{head} は {len(types)} 種で、この場面の最低 {sc.type_plan['min_types']} 種に足りない"
            f"(同じ実行の p3 の採点: {_types_detail(p3_grades)})")), [], False, [], []
    raw, settings = _run_one(adapter, conc)
    return conc, SceneResult(raw.status, output=raw.output, detail=f"{head} → この場面の型 {conc.input.get('types')}。{raw.detail}",
                             provenance=raw.provenance), settings, True, C.substituted_taken(), C.requests_taken()


def run_target(target: str) -> list[dict]:
    rows = {}
    adapter_1 = load_adapter(target)
    adapter_2 = load_adapter(target)  # a fresh adapter for the second run
    roots = roots_of(target)
    p3_1: dict[str, str] = {}
    p3_2: dict[str, str] = {}
    # the P0-3 type scenes first: the other scenes' types come from their grades (round r7-1, r8-1)
    order = [sc for sc in SCENES if sc.id in TYPE_SCENES] + [sc for sc in SCENES if sc.id not in TYPE_SCENES]
    for sc in order:
        sc1, raw1, set1, called1, subst1, req1 = run_for_types_records(adapter_1, sc, p3_1)
        sc2, raw2, set2, _, _, _ = run_for_types_records(adapter_2, sc, p3_2)
        r1 = checked(raw1, sc1, target, settings=set1)
        r2 = checked(raw2, sc2, target, settings=set2)
        g1 = correctness(r1, sc1.expected, sc1, target)
        g2 = correctness(r2, sc2.expected, sc2, target)
        if sc.id in TYPE_SCENES:
            p3_1[sc.id], p3_2[sc.id] = g1, g2
        rows[sc.id] = {
            "target": target, "scene_id": sc.id, "viewpoint": sc.viewpoint, "kind": sc.kind,
            "correctness": g1,
            "correctness_run2": g2,
            "reproducibility": reproducibility(r1, r2),
            "status_1": r1.status,
            "output_1": json.dumps(graded_output(r1, sc1, target), ensure_ascii=False, sort_keys=True, default=repr),
            "status_2": r2.status,
            "output_2": json.dumps(graded_output(r2, sc2, target), ensure_ascii=False, sort_keys=True, default=repr),
            "expected": json.dumps(sc1.expected, ensure_ascii=False, sort_keys=True),
            "detail_1": r1.detail.replace("\t", " ").replace("\n", " "),
            "provenance_1": json.dumps(compact(r1.provenance, roots), ensure_ascii=False, sort_keys=True, default=repr),
            "choose": json.dumps(adapter_1.choose, ensure_ascii=False, sort_keys=True),
            "settings_1": json.dumps(compact_settings(set1, roots), ensure_ascii=False, sort_keys=True, default=repr),
            # round r8-1 (L-438 (2)): the type combination chosen for this configured target, when the scene was built for it
            "types_1": json.dumps(sc1.input.get("types") if sc.type_plan is not None and sc1 is not sc else None,
                                  ensure_ascii=False),
            # round r13-1 (LEAD_DESIGN.md section 9.2 item 33): records of run 1, never used for the grid table
            **{k: json.dumps(v, ensure_ascii=False) for k, v in records_of(
                sc1, r1, called1, subst1, req1, getattr(adapter_1, "records_requests", False),
                target_types(p3_1)).items()},
        }
    return [rows[sc.id] for sc in SCENES]


def one_choose(rows: list[dict]) -> bool:
    """A configured target's rows carry one set of chosen values (round r8-1, positive definition A)."""
    return len({r.get("choose") for r in rows}) == 1


FIELDS = ["target", "scene_id", "viewpoint", "kind", "correctness", "correctness_run2", "reproducibility",
          "status_1", "output_1", "status_2", "output_2", "expected", "detail_1", "provenance_1",
          "choose", "settings_1", "types_1", "types_in", "types_added", "requests"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--list-targets", action="store_true")
    a = ap.parse_args()
    if a.list_targets:
        print("\n".join(t for base in ["current_impl", "new_impl", "mutant", *OPPONENTS, *_repro_targets()]
                        for t in configured_targets(base)))
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

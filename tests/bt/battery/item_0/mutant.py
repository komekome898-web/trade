"""Canary for the blind judges (delegation doc §3 "審査員の試金石").

Wraps the new implementation and makes exactly ONE thing wrong, without
touching `src/bot/bt/core/` (the new implementation's body is not changed;
nothing is monkeypatched: the wrapper is a separate namespace handed to the
new implementation's adapter in place of `bot.bt.core`).

What is made wrong
------------------
The receive time of every input event is replaced by its exchange time
before the engine sees it (`received_time_ns := exchange_time_ns`). An event
that happened at the exchange at 1 s but can only reach us at 3 s is then
shown to the strategy at 1 s: the strategy sees an event before it could
have received it (requirement "戦略は「受け取れた時刻 ≤ 今」の事象しか見られ
ない"). Nothing raises; every value stays plausible. In the scene set this
changes the result of `p4-received-time` only (it is the only scene whose
events have a receive time later than the exchange time); every other scene
gets exactly what the unwrapped new implementation gets.

MUTATION (below) states this for the tables and the judges' records.

Usage
-----
    PYTHONPATH=src python3 run_battery.py --target mutant --out OUT.tsv
    PYTHONPATH=src python3 mutant.py --check   # needs adapters/new_impl.py

`--check` runs the new implementation and the canary through every scene
and fails unless the results differ in `p4-received-time` and nowhere else
(if they do not differ at all, the adapter did not route through the `core`
it was given, and the canary measures nothing).
"""
from __future__ import annotations

import dataclasses
import importlib
import sys
import types
from collections.abc import Mapping
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "adapters"))
sys.path.insert(0, str(HERE.parents[3] / "src"))

MUTATION = {
    "what": "入力の事象の受け取れる時刻(received_time_ns)を、取引所の時刻(exchange_time_ns)に置き換えてから核に渡す",
    "effect": "受け取る前の事象が戦略に見える(「受け取れた時刻 ≤ 今」が破れる)。例外は出ない",
    "scenes_expected_to_change": ["p4-received-time"],
    "where": "tests/bt/battery/item_0/mutant.py: mutant_core() の CoreEngine の包み。src/bot/bt/core は変えない",
}


def _early(event):
    exch = getattr(event, "exchange_time_ns", None)
    if exch is None or exch == event.received_time_ns:
        return event
    return dataclasses.replace(event, received_time_ns=exch, exchange_time_ns=exch)


def _wrap_stream(stream):
    for e in stream:
        yield _early(e)


def mutant_core():
    """A namespace with every public name of `bot.bt.core`, where only
    `CoreEngine` is wrapped (subclassed) to rewrite the input events."""
    core = importlib.import_module("bot.bt.core")
    real = core.CoreEngine

    class CoreEngine(real):  # type: ignore[misc, valid-type]
        def __init__(self, strategy, events, *args, **kwargs):
            if isinstance(events, Mapping):
                events = {k: _wrap_stream(v) for k, v in events.items()}
            else:
                events = _wrap_stream(events)
            super().__init__(strategy, events, *args, **kwargs)

    ns = types.SimpleNamespace(**{n: getattr(core, n) for n in dir(core) if not n.startswith("_")})
    ns.CoreEngine = CoreEngine
    ns.__name__ = "bot.bt.core(mutant)"
    return ns


def make_mutant_adapter():
    mod = importlib.import_module("adapters.new_impl")
    adapter = mod.make_adapter(mutant_core())
    adapter.name = f"mutant({getattr(adapter, 'name', 'new_impl')})"
    return adapter


def check() -> int:
    import run_battery
    new = {r["scene_id"]: r for r in run_battery.run_target("new_impl")}
    mut = {r["scene_id"]: r for r in run_battery.run_target("mutant")}
    changed = sorted(s for s in new if (new[s]["status_1"], new[s]["output_1"]) != (mut[s]["status_1"], mut[s]["output_1"]))
    print("changed scenes:", changed)
    if changed != MUTATION["scenes_expected_to_change"]:
        print("NG: the canary must change exactly", MUTATION["scenes_expected_to_change"])
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(check())
    print(MUTATION)

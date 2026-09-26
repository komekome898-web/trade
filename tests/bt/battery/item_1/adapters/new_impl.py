"""新実装 (the new engine's item 1 modules) for the item 1 battery -- THE MOUTH ONLY.

The table-maker (資料係) writes the body of this adapter every round, calling
only the new implementation's public API (委任文 §3; the scene-keeper fixes
the mouth, not the body).  The contract the body must keep:

  TARGET.run(scene_input: dict) -> observation dict      (i1_protocol.py)

- scene_input is one scene's `input` (DEFINITIONS.md「入力の形」) with `root`
  added by the runner:
    op "load"            -- files under `root`; `datasets` (name, paths, spec,
                            optional range_ns); `want` (events / times /
                            anomalies / hashes)
    op "jpx"             -- structured daily bars, corporate actions, listings,
                            as_of, universe_dates
    op "vector_vs_event" -- structured trades or bars, interval_s, rule, want
- Drive the new data layer (`src/bot/bt/data/`) and vector path
  (`src/bot/bt/vector/`) -- plus the core (`src/bot/bt/core/`) for the event
  path -- and report what they produced, in the record forms of i1_protocol.py.
  Hand files to the data layer BY PATH with the spec translated into its
  options; never open or parse a data file in the adapter.
- If the engine refuses (raises / reports an error for the run): raise
  i1_protocol.Refused(reason).
- If the engine's public API has no way to express the scene: raise
  i1_protocol.NotExpressible(what was tried).
- Never compute an answer the engine did not produce, never read the scene's
  expected answer (i1_scenes.expected / scene["expect"]), never special-case a
  scene id.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from i1_protocol import NotExpressible, Refused  # noqa: E402

from bot.bt.data import DataError, adjust_daily, load, universe  # noqa: E402
from bot.bt.vector import (bars_from_trades, rule_from_mapping, run_event_bars, run_event_rule,  # noqa: E402
                           run_vector_rule)


def _engine(fn, *args, **kwargs):
    """Call one public function of the new implementation; its refusal (a
    DataError, the data layer's one error family) becomes Refused."""
    try:
        return fn(*args, **kwargs)
    except DataError as exc:
        raise Refused(f"{type(exc).__name__}: {exc}") from exc


class NewImpl:
    name = "new_impl"

    def run(self, inp: dict) -> dict:
        op = inp.get("op")
        if op == "load":
            return self._load(inp)
        if op == "jpx":
            return self._jpx(inp)
        if op == "vector_vs_event":
            return self._vector_vs_event(inp)
        raise NotExpressible(f"新実装の公開された口に op {op!r} に当たるものを探したが無い")

    @staticmethod
    def _load(inp: dict) -> dict:
        # The runner's `root` and each scene path are handed to the data layer
        # exactly as given (no absolutising, no joining here): resolving a
        # relative data path against the root is the data layer's own job
        # (bot.bt.data.allowlist.AllowList.check), so it is what the scene tests.
        datasets = []
        for d in inp["datasets"]:
            # files by path; the scene's declarative spec is the data layer's own
            # declaration form (bot.bt.data.spec.parse_spec), handed over unchanged
            x = {"name": d["name"], "paths": list(d["paths"]), "spec": d["spec"]}
            if "range_ns" in d:
                x["range_ns"] = d["range_ns"]
            datasets.append(x)
        res = _engine(load, inp["root"], datasets)
        want = set(inp.get("want") or [])
        obs: dict = {}
        if want & {"events", "times"}:
            obs["events"] = {n: _engine(res.records, n) for n in res.names()}
        if "anomalies" in want:
            obs["anomalies"] = {n: _engine(res.anomalies, n) for n in res.names()}
        if "hashes" in want:
            # keyed by the path as given (LoadResult.hashes), i.e. the scene path
            obs["hashes"] = dict(_engine(res.hashes))
        return obs

    @staticmethod
    def _jpx(inp: dict) -> dict:
        return {"adjusted": _engine(adjust_daily, inp["bars"], inp["actions"], inp["listings"], inp["as_of"]),
                "universe": _engine(universe, inp["listings"], inp["actions"], inp["universe_dates"])}

    @staticmethod
    def _vector_vs_event(inp: dict) -> dict:
        iv = inp["interval_s"]
        paths: dict = {"event": {}, "vector": {}}
        timing: dict = {}
        if inp.get("trades") is not None:
            tr = inp["trades"]
            t0 = time.perf_counter()
            paths["event"]["bars"] = _engine(run_event_bars, tr, iv)
            t1 = time.perf_counter()
            paths["vector"]["bars"] = _engine(bars_from_trades, [x["t_ns"] for x in tr], [x["px"] for x in tr],
                                              [x["qty"] for x in tr], iv)
            t2 = time.perf_counter()
            timing = {"event_s": t1 - t0, "vector_s": t2 - t1}
        if inp.get("rule") is not None:
            rule = _engine(rule_from_mapping, inp["rule"])
            bars = inp["bars"]
            t0 = time.perf_counter()
            ev = _engine(run_event_rule, bars, iv, rule)
            t1 = time.perf_counter()
            vc = _engine(run_vector_rule, bars, rule)
            t2 = time.perf_counter()
            paths["event"].update(ev)
            paths["vector"].update(vc)
            timing = {"event_s": t1 - t0, "vector_s": t2 - t1}
        return {"paths": paths, "timing": timing}


TARGET = NewImpl()

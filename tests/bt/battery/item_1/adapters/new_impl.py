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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from i1_protocol import NotExpressible  # noqa: E402


class NewImpl:
    name = "new_impl"

    def run(self, inp: dict) -> dict:
        raise NotExpressible("新実装の adapter の本体はまだ書かれていない(資料係が毎周書く)")


TARGET = NewImpl()

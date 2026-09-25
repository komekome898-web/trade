"""新実装 (the new engine's item 2 modules) for the item 2 battery -- THE MOUTH ONLY.

The table-maker (資料係) writes the body of this adapter every round, calling
only the new implementation's public API (委任文 §3; the scene-keeper fixes
the mouth, not the body).  The contract the body must keep:

  TARGET.run(scene_input: dict) -> observation dict      (i2_protocol.py)

- scene_input is one scene's `input` (DEFINITIONS.md「入力の形」): product,
  rules, market events, strategy actions (local send times), fill_model,
  latency, costs, account, inject, checkpoints, end_t.
- Drive the new engine (`src/bot/bt/core` plus the item 2 modules under
  `src/bot/bt/{orders,fill,latency,costs,portfolio}`) with a strategy that
  performs exactly the scene's actions at their times, and report what the
  engine produced: orders (final status), fills (ref, venue time, px, qty, fee,
  liq), sent, notices (local time seen), seen (labelled events), account,
  costs, range -- only the keys the engine gave.
- If the engine refuses (raises / reports an error for the run): raise
  i2_protocol.Refused(reason).  If the engine refuses ONE order: record that
  order as rejected (i2_protocol.place_guarded) and continue.
- If the engine's public API has no way to express the scene: raise
  i2_protocol.NotExpressible(what was tried).
- Never compute an answer the engine did not produce, never read the scene's
  oracle / expected answer (i2_scenes.expected), never special-case a scene id.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from i2_protocol import NotExpressible  # noqa: E402


class NewImpl:
    name = "new_impl"

    def run(self, inp: dict) -> dict:
        raise NotExpressible("新実装の adapter の本体はまだ書かれていない(資料係が毎周書く)")


TARGET = NewImpl()

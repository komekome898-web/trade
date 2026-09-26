"""新実装 (the new engine, item 4: integration, reference, compatibility) -- THE MOUTH ONLY.

The table-maker (資料係) writes the body of this adapter every round, calling
only the new implementation's public API (委任文 §3; the scene-keeper fixes
the mouth, not the body).  The contract the body must keep:

  TARGET.run(scene_input: dict) -> observation dict      (i4_protocol.py)

- op "bars"     -- drive the new engine's bar model(s) with the scene's script as
                   the strategy and every config key translated into the engine's
                   own options.  `model: "spec"` -> the engine's own (native) bar
                   model; `models: ["legacy", "spec"]` -> BOTH the compatibility
                   mouth (the same names and arguments as the old run_backtest)
                   and the native model, from the one scene input, returned as
                   {"legacy": obs, "spec": obs}.  `reference: true` -> the same
                   input through the engine AND through the independent reference
                   implementation (src/bot/bt/reference/), returned as
                   {"engine": obs, "reference": obs}.
- op "metrics"  -- the engine's metric function(s) on the given PnLs / equity.
- op "split"    -- the engine's row-fraction split (native; `models` as above).
- op "pipeline" -- the scene's files under `root` handed BY PATH with each
                   dataset's declarative spec (and `origin`) translated into the
                   engine's data options; the instruments, the strategy (schedule /
                   price_rule), the fill rule, the costs, the purpose and the
                   prereg hash handed to ONE run; report per `want`: fills /
                   pnl per instrument, events_read per dataset, the run record
                   (purpose, data sha256 by the scene path), the metric export
                   (purpose, round trips per instrument) and the dashboard
                   (every tab of the run's view as {"label", "text"}, read from
                   what the dashboard renders).
- If the engine refuses (raises / reports an error for the run): raise
  i4_protocol.Refused(reason).
- If the engine's public API has no way to express the input: raise
  i4_protocol.NotExpressible(what was tried).
- Never compute an answer the engine did not produce, never read the scene's
  expected answer (i4_scenes.expected / scene["expect"]), never special-case a
  scene id.  The mutant (mutant.py) wraps this module as it is.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from i4_protocol import NotExpressible  # noqa: E402


class NewImpl:
    name = "new_impl"

    def run(self, inp: dict) -> dict:
        raise NotExpressible("新実装の adapter の本体は資料係が毎周書く(場面係は口だけを決めた)。本体がまだ書かれていない")


TARGET = NewImpl()

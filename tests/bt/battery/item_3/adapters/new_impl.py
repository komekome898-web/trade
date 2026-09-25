"""新実装 (the new engine's item 3 modules) for the item 3 battery -- THE MOUTH ONLY.

The table-maker (資料係) writes the body of this adapter every round, calling
only the new implementation's public API (委任文 §3; the scene-keeper fixes
the mouth, not the body).  The contract the body must keep:

  TARGET.run(scene_input: dict) -> observation dict      (i3_protocol.py)

- scene_input is one request (a scene's ``input`` or ``variant``, the forms
  and the observation of every ``op`` are listed in i3_protocol.py) with
  ``root`` added by the runner (the request's files are already under it).
- Drive the new implementation: src/bot/bt/validation/ (splits, walk-forward,
  purge/embargo, CPCV, bootstrap, MDE, verdicts, DSR, PBO, the ITER ledger,
  the sealed read through src/bot/research/sealed.load_sealed), src/bot/bt/repro/
  (run records, run ids, the automatic two-run check, purpose/prereg rules),
  src/bot/bt/report/ (metrics and their exports), src/bot/monitoring/backtest_view.py
  and scripts/dashboard.py (the dashboard: start it on a free 127.0.0.1 port
  over the ``runs_dir`` under ``root``, read what it SERVES, stop it), plus the
  core src/bot/bt/core/ and whatever other items provide for the fixed run.
- ``wiring_test``: run the new implementation's own wiring tests in a
  subprocess whose PYTHONPATH starts with tests/bt/battery/item_3/wiring_break
  and whose env has I3_WIRING_BREAK = the request's ``break`` (unset for None);
  observation {"passed": return code == 0}.
- If the engine refuses (raises / reports an error for the request): raise
  i3_protocol.Refused(reason).
- If the engine's public API has no way to express the request: raise
  i3_protocol.NotExpressible(what was tried).
- Never compute an answer the engine did not produce, never read the scene's
  expected answer (i3_scenes.expected / scene["expect"]), never special-case a
  scene id.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from i3_protocol import NotExpressible  # noqa: E402


class NewImpl:
    name = "new_impl"

    def run(self, inp: dict) -> dict:
        raise NotExpressible("新実装の adapter の本体はまだ書かれていない(資料係が毎周書く)")


TARGET = NewImpl()

"""Item 2 battery: the targets the runner can run.

`venv` is relative to VENV_ROOT (the scratchpad's isolated venvs, installed
under 委任文 §4 by the item 0 scene-keeper and reused here; the install record
of each is `opponents/RUNNABILITY.tsv`).  A target without `venv` runs under the
runner's interpreter with PYTHONPATH=<repo>/src.
Opponent adapters are in opponents/; the `cand` field is the catalogue number.
"""
from __future__ import annotations

import os

VENV_ROOT = os.environ.get(
    "I2_VENV_ROOT", "/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs")

TARGETS: dict[str, dict] = {
    "current_impl": {"module": "adapters/current_impl.py"},
    "new_impl": {"module": "adapters/new_impl.py"},
    "mutant": {"module": "mutant.py"},
}

# Survey side (catalogue number in `cand`). Adapters are in opponents/.
SURVEY: dict[str, dict] = {
    "opp_backtrader": {"module": "opponents/backtrader_adapter.py", "venv": "item_0/backtrader", "cand": 2},
    "opp_zipline_reloaded": {"module": "opponents/zipline_adapter.py", "venv": "item_0/zipline-reloaded", "cand": 18},
    "opp_hftbacktest": {"module": "opponents/hftbacktest_adapter.py", "venv": "item_0/hftbacktest", "cand": 23},
}
TARGETS.update(SURVEY)

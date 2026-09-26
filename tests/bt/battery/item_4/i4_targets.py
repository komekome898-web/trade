"""Item 4 battery: the targets the runner can run.

`venv` is relative to VENV_ROOT (the scratchpad's isolated venvs; the install
record of each is opponents/RUNNABILITY.tsv).  A target without `venv` runs
under the runner's interpreter with PYTHONPATH=<repo>/src.
Opponent adapters are in opponents/; `cand` is the catalogue number
(docs/DATA/tools_catalog.tsv).  The survey side is every candidate that
REQUIREMENTS.md §3 names and that could be installed (the others are in
opponents/CONSIDERED.md).
"""
from __future__ import annotations

import os

VENV_ROOT = os.environ.get(
    "I4_VENV_ROOT", "/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs")

TARGETS: dict[str, dict] = {
    "current_impl": {"module": "adapters/current_impl.py"},
    "new_impl": {"module": "adapters/new_impl.py"},
    "mutant": {"module": "mutant.py"},
}

SURVEY: dict[str, dict] = {
    "opp_backtrader": {"module": "opponents/backtrader_adapter.py", "venv": "item_0/backtrader", "cand": 2},
    "opp_backtesting": {"module": "opponents/backtesting_adapter.py", "venv": "item_0/backtesting", "cand": 55},
    "opp_vectorbt": {"module": "opponents/vectorbt_adapter.py", "venv": "item_1/vectorbt", "cand": 73},
    "opp_pyalgotrade": {"module": "opponents/pyalgotrade_adapter.py", "venv": "item_4/pyalgotrade", "cand": 122},
    "opp_pybroker": {"module": "opponents/pybroker_adapter.py", "venv": "item_4/pybroker", "cand": 4},
    "opp_luczinsritter": {"module": "opponents/luczinsritter_adapter.py", "venv": "item_3/c16", "cand": 16},
    "opp_vnpy": {"module": "opponents/vnpy_adapter.py", "venv": "item_0/vnpy", "cand": 20},
    "opp_basana": {"module": "opponents/basana_adapter.py", "venv": "item_0/basana", "cand": 1},
    "opp_bt": {"module": "opponents/bt_adapter.py", "venv": "item_2/bt", "cand": 5},
    "opp_qtradex": {"module": "opponents/qtradex_adapter.py", "venv": "item_2/qtradex", "cand": 72},
    "opp_ziplime": {"module": "opponents/ziplime_adapter.py", "venv": "item_2/ziplime", "cand": 6},
}
TARGETS.update(SURVEY)

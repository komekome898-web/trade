"""Item 1 battery: the targets the runner can run.

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
    "I1_VENV_ROOT", "/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs")

TARGETS: dict[str, dict] = {
    "new_impl": {"module": "adapters/new_impl.py"},
    "mutant": {"module": "mutant.py"},
}

SURVEY: dict[str, dict] = {
    "opp_vectorbt": {"module": "opponents/vectorbt_adapter.py", "venv": "item_1/vectorbt", "cand": 73},
    "opp_qlib": {"module": "opponents/qlib_adapter.py", "venv": "item_1/qlib", "cand": 21},
    "opp_finmarketpy": {"module": "opponents/finmarketpy_adapter.py", "venv": "item_1/finmarketpy", "cand": 54},
    "opp_pytrendfollow": {"module": "opponents/pytrendfollow_adapter.py", "venv": "item_1/c87", "cand": 87},
    "opp_hftbacktest": {"module": "opponents/hftbacktest_adapter.py", "venv": "item_1/hftbacktest", "cand": 23},
    "opp_pybotters": {"module": "opponents/pybotters_adapter.py", "venv": "item_0/pybotters", "cand": 12},
    "opp_backtesting": {"module": "opponents/backtesting_adapter.py", "venv": "item_0/backtesting", "cand": 55},
    "opp_qstrader": {"module": "opponents/qstrader_adapter.py", "venv": "item_0/qstrader", "cand": 121},
    "opp_vnpy": {"module": "opponents/vnpy_adapter.py", "venv": "item_0/vnpy", "cand": 20},
    "opp_slippage": {"module": "opponents/slippage_adapter.py", "venv": "item_0/c105", "cand": 105},
    "opp_barter": {"module": "opponents/barter_adapter.py", "venv": "item_0/c61", "cand": 61},
    "opp_pysystemtrade": {"module": "opponents/pysystemtrade_adapter.py", "venv": "item_1/c3", "cand": 3},
    # reproductions (委任文 §3「動かせない候補の検討と再現」; opponents/CONSIDERED.md)
    "opp_repro_23": {"module": "opponents/repro_23_event_order.py", "cand": 23, "repro": True},
    "opp_repro_105": {"module": "opponents/repro_105_duplicate_bars.py", "cand": 105, "repro": True},
}
TARGETS.update(SURVEY)

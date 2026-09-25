"""Item 3 battery: the targets the runner can run.

`venv` is relative to VENV_ROOT (the scratchpad's isolated venvs; the install
record of each is opponents/RUNNABILITY.tsv).  A target without `venv` runs
under the runner's interpreter with PYTHONPATH=<repo>/src.
Opponent adapters are in opponents/; `cand` is the catalogue number
(docs/DATA/tools_catalog.tsv; "-" for mlflow, which the catalogue does not
list: REQUIREMENTS.md §3.3).  The survey side is every candidate that
REQUIREMENTS.md §3 names and that could be run (the others are in
opponents/CONSIDERED.md).
"""
from __future__ import annotations

import os

VENV_ROOT = os.environ.get(
    "I3_VENV_ROOT", "/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs")

TARGETS: dict[str, dict] = {
    "current_impl": {"module": "adapters/current_impl.py"},
    "new_impl": {"module": "adapters/new_impl.py"},
    "mutant": {"module": "mutant.py"},
}

SURVEY: dict[str, dict] = {
    "opp_homerun": {"module": "opponents/homerun_adapter.py", "venv": "item_2/c91", "cand": 91},
    "opp_mlflow": {"module": "opponents/mlflow_adapter.py", "venv": "item_3/mlflow", "cand": "-"},
    "opp_freqtrade": {"module": "opponents/freqtrade_adapter.py", "venv": "item_3/freqtrade", "cand": 75},
    "opp_pysystemtrade": {"module": "opponents/pysystemtrade_adapter.py", "venv": "item_1/c3", "cand": 3},
    "opp_luczinsritter": {"module": "opponents/luczinsritter_adapter.py", "venv": "item_3/c16", "cand": 16},
    "opp_polymarket_fill": {"module": "opponents/polymarket_fill_adapter.py", "venv": "item_2/c95", "cand": 95},
    "opp_mihircoding_lob": {"module": "opponents/mihircoding_lob_adapter.py", "venv": "item_2/c98", "cand": 98},
    "opp_isaaccheng_obsim": {"module": "opponents/isaaccheng_obsim_adapter.py", "venv": "item_2/c103", "cand": 103},
    "opp_sigc": {"module": "opponents/sigc_adapter.py", "venv": "item_0/c107", "cand": 107},
    "opp_pybotters": {"module": "opponents/pybotters_adapter.py", "venv": "item_0/pybotters", "cand": 12},
    # reproductions (委任文 §3「動かせない候補の検討と再現」; opponents/CONSIDERED.md)
    "opp_repro_15": {"module": "opponents/repro_15_backtestingcore.py", "cand": 15, "repro": True},
    "opp_repro_88": {"module": "opponents/repro_88_tradesight.py", "cand": 88, "repro": True},
}
TARGETS.update(SURVEY)

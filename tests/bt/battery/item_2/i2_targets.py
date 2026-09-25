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
    "opp_mihircoding_lob": {"module": "opponents/mihircoding_lob_adapter.py", "venv": "item_0/c98", "cand": 98},
    "opp_nickgardi_orderbooksim": {"module": "opponents/nickgardi_orderbooksim_adapter.py", "venv": "item_0/c99", "cand": 99},
    "opp_3yit_lob": {"module": "opponents/threeyit_lob_adapter.py", "venv": "item_0/c102", "cand": 102},
    "opp_isaaccheng_obsim": {"module": "opponents/isaaccheng_obsim_adapter.py", "venv": "item_0/c103", "cand": 103},
    "opp_akurkar07_orderbook": {"module": "opponents/akurkar07_orderbook_adapter.py", "cand": 101},
    "opp_jxm35_lob": {"module": "opponents/jxm35_lob_adapter.py", "cand": 104},
    "opp_sashankzade_lob": {"module": "opponents/sashankzade_lob_adapter.py", "cand": 96},
    "opp_daniyalmlk_slippage": {"module": "opponents/daniyalmlk_slippage_adapter.py", "venv": "item_0/c105", "cand": 105},
    "opp_sarthak_execsim": {"module": "opponents/sarthak_execsim_adapter.py", "cand": 33},
    "opp_thirupathikannan_execsim": {"module": "opponents/thirupathikannan_execsim_adapter.py", "venv": "item_0/c35_run/.venv", "cand": 35},
    "opp_sigc": {"module": "opponents/sigc_adapter.py", "venv": "item_0/c107", "cand": 107},
    "opp_pytrendfollow": {"module": "opponents/pytrendfollow_adapter.py", "venv": "item_0/c87", "cand": 87},
    "opp_finmarketpy": {"module": "opponents/finmarketpy_adapter.py", "venv": "item_0/finmarketpy", "cand": 54},
    "opp_pysystemtrade": {"module": "opponents/pysystemtrade_adapter.py", "venv": "item_0/c3", "cand": 3},
    "opp_fast_trade": {"module": "opponents/fast_trade_adapter.py", "venv": "item_0/fast-trade-r17", "cand": 10},
    "opp_pybotters": {"module": "opponents/pybotters_adapter.py", "venv": "item_0/pybotters", "cand": 12},
    "opp_basana": {"module": "opponents/basana_adapter.py", "venv": "item_0/basana", "cand": 1},
}
TARGETS.update(SURVEY)

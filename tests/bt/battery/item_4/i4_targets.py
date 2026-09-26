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
    "opp_qstrader": {"module": "opponents/qstrader_adapter.py", "venv": "item_0/qstrader", "cand": 121},
    "opp_finmarketpy": {"module": "opponents/finmarketpy_adapter.py", "venv": "item_1/finmarketpy", "cand": 54},
    "opp_pysystemtrade": {"module": "opponents/pysystemtrade_adapter.py", "venv": "item_1/c3", "cand": 3},
    "opp_qlib": {"module": "opponents/qlib_adapter.py", "venv": "item_1/qlib", "cand": 21},
    "opp_hftbacktest": {"module": "opponents/hftbacktest_adapter.py", "venv": "item_1/hftbacktest", "cand": 23},
    "opp_pytrendfollow": {"module": "opponents/pytrendfollow_adapter.py", "venv": "item_1/c87", "cand": 87},
    "opp_pybotters": {"module": "opponents/pybotters_adapter.py", "venv": "item_0/pybotters", "cand": 12},
    "opp_freqtrade": {"module": "opponents/freqtrade_adapter.py", "venv": "item_3/freqtrade", "cand": 75},
    "opp_pm_backtester": {"module": "opponents/pm_backtester_adapter.py", "venv": "item_2/c92", "cand": 92},
    "opp_rqalpha": {"module": "opponents/rqalpha_adapter.py", "venv": "item_4/rqalpha", "cand": 53},
    "opp_pineforge": {"module": "opponents/pineforge_adapter.py", "venv": "item_2/c70", "cand": 70},
    "opp_quanttrader": {"module": "opponents/quanttrader_adapter.py", "venv": "item_4/quanttrader", "cand": 68},
    "opp_fast_trade": {"module": "opponents/fast_trade_adapter.py", "venv": "item_4/fast-trade", "cand": 10},
    "opp_zipline_reloaded": {"module": "opponents/zipline_reloaded_adapter.py", "venv": "item_4/zipline-reloaded", "cand": 18},
}
TARGETS.update(SURVEY)

# Reproductions (opponents/repro_*.py): candidates that could not be run, rewritten from their primary source
# (the source and lines are in each file); they run under the runner's interpreter.
REPRO: dict[str, dict] = {
    "opp_repro_67_lumibot": {"module": "opponents/repro_67_lumibot.py", "cand": 67},
    "opp_repro_60_hikyuu": {"module": "opponents/repro_60_hikyuu.py", "cand": 60},
    "opp_repro_15_backtestingcore": {"module": "opponents/repro_15_backtestingcore.py", "cand": 15},
    "opp_repro_8_opentrader": {"module": "opponents/repro_8_opentrader.py", "cand": 8},
    "opp_repro_56_zvt": {"module": "opponents/repro_56_zvt.py", "cand": 56},
    "opp_repro_69_gobacktest": {"module": "opponents/repro_69_gobacktest.py", "cand": 69},
    "opp_repro_11_octobot": {"module": "opponents/repro_11_octobot.py", "cand": 11},
    "opp_repro_7_superalgos": {"module": "opponents/repro_7_superalgos.py", "cand": 7},
    "opp_repro_52_lean": {"module": "opponents/repro_52_lean.py", "cand": 52},
    "opp_repro_57_wondertrader": {"module": "opponents/repro_57_wondertrader.py", "cand": 57},
    "opp_repro_94_mote": {"module": "opponents/repro_94_mote.py", "cand": 94},
    "opp_repro_80_hummingbot": {"module": "opponents/repro_80_hummingbot.py", "cand": 80},
}
TARGETS.update(REPRO)

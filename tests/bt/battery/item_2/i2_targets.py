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
    "new_impl": {"module": "adapters/new_impl.py"},
    "mutant": {"module": "mutant.py"},
}

# Survey side (catalogue number in `cand`). Adapters are in opponents/.
SURVEY: dict[str, dict] = {
    "opp_backtrader": {"module": "opponents/backtrader_adapter.py", "venv": "item_0/backtrader", "cand": 2},
    "opp_zipline_reloaded": {"module": "opponents/zipline_adapter.py", "venv": "item_0/zipline-reloaded", "cand": 18},
    "opp_hftbacktest": {"module": "opponents/hftbacktest_adapter.py", "venv": "item_1/hftbacktest", "cand": 23},
    "opp_mihircoding_lob": {"module": "opponents/mihircoding_lob_adapter.py", "venv": "item_2/c98", "cand": 98},
    "opp_nickgardi_orderbooksim": {"module": "opponents/nickgardi_orderbooksim_adapter.py", "venv": "item_2/c99", "cand": 99},
    "opp_3yit_lob": {"module": "opponents/threeyit_lob_adapter.py", "venv": "item_0/c102", "cand": 102},
    "opp_isaaccheng_obsim": {"module": "opponents/isaaccheng_obsim_adapter.py", "venv": "item_2/c103", "cand": 103},
    "opp_akurkar07_orderbook": {"module": "opponents/akurkar07_orderbook_adapter.py", "cand": 101},
    "opp_jxm35_lob": {"module": "opponents/jxm35_lob_adapter.py", "cand": 104},
    "opp_sashankzade_lob": {"module": "opponents/sashankzade_lob_adapter.py", "cand": 96},
    "opp_daniyalmlk_slippage": {"module": "opponents/daniyalmlk_slippage_adapter.py", "venv": "item_0/c105", "cand": 105},
    "opp_sarthak_execsim": {"module": "opponents/sarthak_execsim_adapter.py", "cand": 33},
    "opp_thirupathikannan_execsim": {"module": "opponents/thirupathikannan_execsim_adapter.py", "venv": "item_0/c35_run/.venv", "cand": 35},
    "opp_sigc": {"module": "opponents/sigc_adapter.py", "venv": "item_0/c107", "cand": 107},
    "opp_pytrendfollow": {"module": "opponents/pytrendfollow_adapter.py", "venv": "item_0/c87", "cand": 87},
    "opp_finmarketpy": {"module": "opponents/finmarketpy_adapter.py", "venv": "item_1/finmarketpy", "cand": 54},
    "opp_pysystemtrade": {"module": "opponents/pysystemtrade_adapter.py", "venv": "item_0/c3", "cand": 3},
    "opp_fast_trade": {"module": "opponents/fast_trade_adapter.py", "venv": "item_0/fast-trade-r17", "cand": 10},
    "opp_pybotters": {"module": "opponents/pybotters_adapter.py", "venv": "item_0/pybotters", "cand": 12},
    "opp_basana": {"module": "opponents/basana_adapter.py", "venv": "item_0/basana", "cand": 1},
    "opp_vnpy@tick": {"module": "opponents/vnpy_tick_adapter.py", "venv": "item_0/vnpy", "cand": 20},
    "opp_vnpy@bar": {"module": "opponents/vnpy_bar_adapter.py", "venv": "item_0/vnpy", "cand": 20},
    "opp_quantcore": {"module": "opponents/quantcore_adapter.py", "venv": "item_0/quantcore", "cand": 34},
    "opp_luczinsritter": {"module": "opponents/luczinsritter_adapter.py", "venv": "item_0/luczinsritter", "cand": 16},
    "opp_lib_pybroker": {"module": "opponents/lib_pybroker_adapter.py", "venv": "item_0/lib-pybroker", "cand": 4},
    "opp_rqalpha": {"module": "opponents/rqalpha_adapter.py", "venv": "item_0/rqalpha", "cand": 53},
    "opp_predictivedev_tradesim": {"module": "opponents/predictivedev_tradesim_adapter.py", "venv": "item_0/c37", "cand": 37},
    "opp_homerun": {"module": "opponents/homerun_adapter.py", "venv": "item_2/c91", "cand": 91},
    "opp_aat": {"module": "opponents/aat_adapter.py", "venv": "item_0/c65", "cand": 65},
    "opp_pineforge": {"module": "opponents/pineforge_adapter.py", "venv": "item_2/c70", "cand": 70},
    "opp_ziplime": {"module": "opponents/ziplime_adapter.py", "venv": "item_2/ziplime", "cand": 6},
    "opp_barter": {"module": "opponents/barter_adapter.py", "venv": "item_0/c61", "cand": 61},
    "opp_oddpool_bench": {"module": "opponents/oddpool_bench_adapter.py", "venv": "item_2/c90", "cand": 90},
    "opp_pm_backtester": {"module": "opponents/pm_backtester_adapter.py", "venv": "item_2/c92", "cand": 92},
    "opp_flashalpha_fillsim": {"module": "opponents/flashalpha_fillsim_adapter.py", "venv": "item_2/c32", "cand": 32},
    "opp_polymarket_fillmodel": {"module": "opponents/polymarket_fillmodel_adapter.py", "venv": "item_2/c95", "cand": 95},
    "opp_vectorbt": {"module": "opponents/vectorbt_adapter.py", "venv": "item_1/vectorbt", "cand": 73},
    "opp_qlib": {"module": "opponents/qlib_adapter.py", "venv": "item_1/qlib", "cand": 21},
    "opp_bt": {"module": "opponents/bt_adapter.py", "venv": "item_2/bt", "cand": 5},
    "opp_qtradex": {"module": "opponents/qtradex_adapter.py", "venv": "item_2/qtradex", "cand": 72},
    "opp_repro_57_wondertrader": {"module": "opponents/repro_57_wondertrader_match.py", "venv": "item_2/c70", "cand": 57},
    "opp_repro_94_mote": {"module": "opponents/repro_94_mote_backtest.py", "venv": "item_2/c70", "cand": 94},
}
TARGETS.update(SURVEY)

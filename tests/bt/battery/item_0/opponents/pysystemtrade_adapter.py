"""Survey candidate 3 `PySystemtrade` (GitHub `pst-group/pysystemtrade`,
commit 8958c49c, version 1.8.2; not on PyPI, SCAN run 9), run in its own
venv `c3` (its requirements.txt; a `.pth` points at a sparse clone without
the 737 MB data folder -- only the csv config and the SP500 / SP500_micro
samples; install record `survey_results/attempts/3.log`).

What the tool is: a daily futures system built from stages
(`System([Account..., Portfolios(), PositionSizing(), ForecastCombine(),
ForecastScaleCap(), Rules(), RawData()], sim_data, config)`, the stages are
classes and can be replaced); trading rules are functions over whole price
series, positions come out of the stages, and the accounting stage
`AccountWithOrderSimulator` turns the position series into orders and fills
(`systems/accounts/order_simulator`). No strategy code is called per event,
there are no market event types (only price series per instrument), no
order / cancel API for a strategy, no notices, clock, latency or account
object to hand in.

Every scene is answered with the same real call: the example system with
the order simulator on the bundled SP500_micro sample (the tool's own
data, not ours), which shows that shape.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

from _vector_base import VectorBase  # noqa: E402

logging.disable(logging.CRITICAL)


def _run_example() -> str:
    try:
        from sysdata.config.configdata import Config
        from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
        from systems.accounts.order_simulator.account_curve_order_simulator import AccountWithOrderSimulator
        from systems.basesystem import System
        from systems.forecast_combine import ForecastCombine
        from systems.forecast_scale_cap import ForecastScaleCap
        from systems.forecasting import Rules
        from systems.portfolio import Portfolios
        from systems.positionsizing import PositionSizing
        from systems.rawdata import RawData

        cfg = Config("systems.provided.example.daily_with_order_simulation.yaml")
        cfg.instrument_weights = {"SP500_micro": 1.0}
        cfg.instruments = ["SP500_micro"]
        s = System([AccountWithOrderSimulator(), Portfolios(), PositionSizing(), ForecastCombine(), ForecastScaleCap(),
                    Rules(), RawData()], csvFuturesSimData(), cfg)
        oc = s.accounts.get_order_simulator("SP500_micro", is_subsystem=True)
        f = oc.list_of_fills().as_pd_df()
        return (f"System([AccountWithOrderSimulator(), Portfolios(), PositionSizing(), ForecastCombine(), ForecastScaleCap(), Rules(), "
                f"RawData()], csvFuturesSimData(), 例の設定で SP500_micro だけ) -> accounts.get_order_simulator('SP500_micro', is_subsystem=True) "
                f"= {type(oc).__name__}、注文 {len(oc.list_of_orders().as_pd_df())} 件・約定 {len(f)} 件、約定の列 {list(f.columns)}"
                f"(建玉の系列から作られ、戦略が注文を出す口は無い)")
    except Exception as exc:  # noqa: BLE001
        return f"例の system を 1 銘柄で組んだ -> {type(exc).__name__}: {str(exc)[:200]}"


class PysystemtradeAdapter(VectorBase):
    name = "opp_pysystemtrade"
    what = ("PySystemtrade は日次の価格系列全体から段(stage)で建玉を出し、会計の段が建玉の系列を注文と約定にする形で、事象ごとに戦略を呼ぶ口、"
            "事象の型(約定・板・資金調達・清算・時計・通知)、戦略が発注・取消する口、遅延・口座を渡す口が無い")
    _out = None

    def attempt(self, scene_id: str) -> str:
        if self._out is None:
            type(self)._out = _run_example()
        return self._out

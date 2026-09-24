"""Survey candidate 54 `finmarketpy` (PyPI `finmarketpy` 0.11.19), run in its own venv.

finmarketpy's backtest (`finmarketpy.backtest.Backtest.calculate_trading_PnL(
BacktestRequest, asset_df, signal_df, contract_value_df)`) takes a whole price
DataFrame and a whole signal DataFrame and returns returns / P&L; no strategy
code is called per event. Each scene is answered with a real call into it.
Installing needed plotly 5.24.1 and pandas < 3 (chartpy imports
`plotly.figure_factory._ohlc`); see the install log.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

import logging  # noqa: E402

import pandas as pd  # noqa: E402

from _vector_base import VectorBase  # noqa: E402
from protocol import not_supported, ok  # noqa: E402

logging.disable(logging.CRITICAL)
from finmarketpy.backtest import Backtest, BacktestRequest  # noqa: E402


class FinmarketpyAdapter(VectorBase):
    name = "opp_finmarketpy"
    what = ("finmarketpy の検証は、価格の DataFrame 全体と信号の DataFrame 全体を受けて損益を返す形で、事象ごとに戦略のコードを呼ぶ口、"
            "事象の型、注文・取消・通知・時計・約定/遅延/口座の差し込み口が無い(費用は BacktestRequest.spot_tc_bp の率)")

    def attempt(self, scene_id: str) -> str:
        idx = pd.date_range("2023-11-16", periods=3, freq="D")
        px = pd.DataFrame({"X.close": [100.0, 101.0, 102.0]}, index=idx)
        sig = pd.DataFrame({"X.close": [1.0, 1.0, 1.0]}, index=idx)
        br = BacktestRequest()
        br.start_date, br.finish_date = idx[0], idx[-1]
        br.spot_tc_bp = 0.0
        try:
            bt = Backtest()
            bt.calculate_trading_PnL(br, px, sig, None, False)
            res = [n for n in dir(bt) if n.startswith("portfolio") or n.startswith("strategy")][:6]
            r = f"通った(結果の名前 {res})"
        except Exception as exc:  # noqa: BLE001
            r = f"{type(exc).__name__}: {str(exc)[:160]}"
        return f"Backtest().calculate_trading_PnL(BacktestRequest, 価格の DataFrame 3 行, 信号の DataFrame 3 行, None) -> {r}"

    def _iso(self, sc):
        # round r6-1 (same root as critic i0-r5-02): the earlier version called pd.Timestamp itself; the tool has
        # no reader of time strings of its own (it takes a DataFrame the user built)
        return not_supported(f"{self.what}。時刻の文字列を読む入口が無い(入力は利用者が作る DataFrame で、その DatetimeIndex を作る変換は利用者の側)。"
                             f"試したこと: {self.attempt(sc.id)}")

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

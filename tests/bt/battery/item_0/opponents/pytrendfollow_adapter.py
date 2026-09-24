"""Survey candidate 87 `PyTrendFollow` (GitHub `chrism2671/PyTrendFollow`, commit
439232ae), run in its own venv `c87` (its requirements; a `.pth` points at the
clone; README steps 1-2 copied the two config templates, no keys written;
install record `survey_results/attempts/87.log`).

What the tool is: a futures trend-following system whose backtest is the
`trading.accountcurve.accountCurve` object: given the instruments, the
position series and the (panama) price series, `returns()` is the sum of four
fixed formulas (`position_returns` = positions shifted 2 periods x price
change x point value, `transaction_returns` = half the price change on the
traded quantity, `commissions` = traded quantity x the instrument's
`commission`, `spreads`); there are no events, no orders, no strategy called
per event. Normally the positions and prices come from Quandl / IB downloads
(README "Data sources"); `accountCurve(..., positions=..., panama_prices=...)`
takes both directly, which is how this adapter runs it on the scene's
synthetic numbers without any download.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

from _vector_base import VectorBase  # noqa: E402

import pandas as pd  # noqa: E402


class _Inst:
    """The four attributes accountCurve reads from an instrument (accountcurve.py
    commissions / spreads / point_values); the tool's own Instrument class loads
    them from config/instruments.py and its data store."""

    def __init__(self, name: str, commission: float, spread: float, point_value: float):
        self.name, self.commission, self.spread, self.point_value = name, commission, spread, point_value


def _run() -> str:
    try:
        from trading.accountcurve import accountCurve
        idx = pd.date_range("2023-11-16", periods=6, freq="D", tz="UTC")
        prices = pd.Series([100.0, 101.0, 102.0, 103.0, 104.0, 105.0], index=idx, name="X")
        positions = pd.Series([0.0, 1.0, 1.0, 1.0, 1.0, 1.0], index=idx, name="X")
        ac = accountCurve(_Inst("X", commission=0.5, spread=0.0, point_value=1.0), capital=100_000, positions=positions,
                          panama_prices=prices, nofx=True, multiproc=False)
        r = ac.returns()
        return (f"trading.accountcurve.accountCurve(<name/commission=0.5/spread=0/point_value=1 の銘柄>, positions=<6 日の建玉の系列>, "
                f"panama_prices=<6 日の値の系列>, nofx=True, multiproc=False).returns() -> 列 {list(r.columns)}、{len(r)} 行"
                f"(戦略を事象ごとに呼ぶ口・注文・約定の物は無く、損益は建玉と値の系列の式)")
    except Exception as exc:  # noqa: BLE001 - the failure is the observation
        return f"accountCurve の呼び出し: {type(exc).__name__}: {str(exc)[:200]}"


class PytrendfollowAdapter(VectorBase):
    name = "opp_pytrendfollow"
    what = ("PyTrendFollow の検証は accountCurve(銘柄・建玉の系列・値の系列)の式で、事象を流す機関・事象ごとに呼ぶ戦略・注文・約定・時計・"
            "口座の物が無い。約定・遅延・費用・口座を差し込む口も無い(損益は accountcurve.py の 4 つの式の和、建玉は 2 期ずらし、費用は銘柄の commission の数)")
    _out = None

    def attempt(self, scene_id: str) -> str:
        if self._out is None:
            type(self)._out = _run()
        return self._out

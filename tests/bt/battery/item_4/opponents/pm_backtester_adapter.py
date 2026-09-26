"""Survey candidate 92 `Quentin-Piot/prediction-market-backtester` (git clone src/c92, package pm_bt; venv item_2/c92)
for the item 4 battery.

The tool's own part used: `pm_bt.execution.simulator.MarketSnapshot(ts, market_id, outcome_id, mid_price, spread,
recent_volume)` and `ExecutionSimulator(ExecutionConfig(...), initial_cash).execute_bar(...)`, called the way its
BacktestEngine calls it (one call per bar, the bar's close as the mid).  The tool's prices are probabilities: a
MarketSnapshot with a mid outside [0, 1] is refused (execution/simulator.py 58-60 行).  The adapter hands the scene's
bars as they are (the scene's prices are not probabilities), so the tool's refusal is what is recorded; the prices
are not rescaled (that would change the scene's input).
"""
from __future__ import annotations

import datetime as D
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from _i4_base import Base, NotExpressible, Refused  # noqa: E402

from pm_bt.execution import simulator as SIM  # noqa: E402


class PmBacktesterAdapter(Base):
    name = "opp_pm_backtester"
    TOOL = "prediction-market-backtester (pm_bt)"
    PIPELINE = "入力は予測市場の市場ごとの snapshot で、足・約定・気配・板のファイルを宣言で読む口・目的つきの書き出し・ダッシュボードが無い"
    METRICS = "外から与えた決済ごとの損益と資産の列から 12 の指標を出す口を探したが無い"
    SPLIT = "行の割合で分ける口を探したが無い"
    DELIVERY = ("道具の模擬は予測市場の snapshot(値は確率 [0, 1])を渡す形で、足(始値・高値・安値・終値)を 1 本ずつ戦略に渡す口を探したが無い"
                "(この adapter の bars が作る SIM.MarketSnapshot の欄は ts・market_id・outcome_id・mid_price・spread・recent_volume だけ)")

    def gate(self, inp):
        return None

    def bars(self, inp):
        b = inp["bars"][0]
        try:  # the first bar's snapshot, exactly as the tool's engine would build it
            SIM.MarketSnapshot(ts=D.datetime(1970, 1, 1, tzinfo=D.timezone.utc) + D.timedelta(microseconds=b["t_ns"] // 1000),
                               market_id="X", outcome_id="YES", mid_price=float(b["close"]), spread=None,
                               recent_volume=float(b["volume"]))
        except (ValueError, TypeError) as exc:
            raise Refused(f"MarketSnapshot: {type(exc).__name__}: {exc}") from exc
        raise NotExpressible(f"{self.TOOL}: 足の値が [0, 1] の中にあっても、注文を次の足の始値で約定させる口・逆指値・指値の口を探したが無い"
                             "(fill は bar_index + latency_bars の mid ± spread / 2 ± slippage)")


TARGET = PmBacktesterAdapter()

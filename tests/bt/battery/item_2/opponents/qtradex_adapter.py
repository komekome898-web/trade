"""Survey candidate 72 `QTradeX` (PyPI QTradeX 1.8.0; venv item_2/qtradex, install record
venvs/item_2/logs/i2_r1_scenekeeper_install_qtradex.log) for the item 2 battery.

What the tool's execution is (read in the installed code, qtradex/core/backtest.py `trade`, `determine_execution_price`,
`perform_trade`): per candle, the bot returns a signal -- Buy / Sell (optionally with a price) or Thresholds(buying,
selling) -- and the back test trades the wallet's whole balance up to `maxvolume` (a buy spends
`min(wallet[currency], maxvolume)` of the currency, a sell sells `min(wallet[asset], maxvolume)`) at the candle's close
or the signal's price when the candle's range reaches it, with one percentage fee `wallet.fee`.  A scene's order is a
quantity of the asset at a time: a buy of q units has no argument (the buy's size is an amount of currency spent at a
price the back test decides), and there is no cancel, stop, IOC / FOK, latency or order book.  Each scene reads the
signal classes and the back test's signature as what was tried.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from probe_base import ProbeAdapter, signature_probe  # noqa: E402

import importlib  # noqa: E402

_bt = importlib.import_module("qtradex.core.backtest")  # the tool (the package re-exports the function under the same name)
from qtradex.private.signals import Buy, Sell, Thresholds  # noqa: E402


class Adapter(ProbeAdapter):
    name = "opp_qtradex"
    tool = "QTradeX 1.8.0"
    what = ("口はろうそく足ごとの信号(Buy / Sell / Thresholds)で財布の残高を maxvolume まで売り買いする backtest で、"
            "手数料は財布の率 1 つ(backtest.py の trade・perform_trade)")

    def probe(self):
        return signature_probe(_bt.backtest, _bt.perform_trade, Buy.__init__, Sell.__init__, Thresholds.__init__)

    def why_not(self, inp):
        return "場面の注文(数量・時刻・種類)を渡す口が無い(買いの大きさは使う通貨の額、値と時刻は backtest がろうそく足で決める)"


TARGET = Adapter()

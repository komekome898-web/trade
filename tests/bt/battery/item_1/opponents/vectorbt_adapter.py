"""vectorbt (catalogue 73, SCAN 5907 行) for the item 1 battery.

Installed 2026-09-25 into the isolated venv item_1/vectorbt (opponents/RUNNABILITY.tsv).

What the tool has, read in the installed code (vectorbt 1.1.0):
- a vector path: `vbt.MA.run` (generic/nb.py:716 rolling_mean_1d_nb) and
  `vbt.Portfolio.from_orders` (target amounts, all bars at once);
- a sequential (event) path: `vbt.Portfolio.from_order_func` (portfolio/base.py:3301),
  which calls an order function bar by bar;
- no reader of market-data files (`grep -rn "read_csv\\|class CSVData" vectorbt/` -> 0 hits;
  the data classes fetch from Yahoo / Binance / CCXT / Alpaca or synthesise),
  no trade->bar aggregation of its own, no duplicate / gap / hash / allow-list /
  corporate-action code.

V7 rule on bars: both paths use the tool's own rolling mean (rolling_mean_1d_nb)
and the tool's order execution; the event path computes the mean inside the
order function from the closes up to the current bar only (no look-ahead).
The event path recomputes the tool's rolling mean on the whole prefix, so that its
floating-point arithmetic (a running cumulative sum from the first bar) is the same
as the vector path's; this costs O(n^2) time.  That only slows the event path, i.e.
it moves v7-speed toward the answer the scene expects (vector faster) -- read this
target's v7-speed result with that in mind.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from i1_protocol import NotExpressible, need  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import vectorbt as vbt  # noqa: E402
from numba import njit  # noqa: E402
from vectorbt.generic.nb import rolling_mean_1d_nb  # noqa: E402
from vectorbt.portfolio import nb as pnb  # noqa: E402
from vectorbt.portfolio.enums import SizeType  # noqa: E402


@njit
def _order_func_nb(c, close, n, unit, sma_out):
    i = c.i
    m = rolling_mean_1d_nb(close[:i + 1], n)[i]
    sma_out[i] = m
    target = unit if (not np.isnan(m) and close[i] > m) else 0.0
    return pnb.order_nb(size=target, price=close[i], size_type=SizeType.TargetAmount)


def _vector(close: np.ndarray, rule: dict):
    n, unit, cash = rule["n"], float(rule["unit"]), float(rule["init_cash"])
    sma = vbt.MA.run(pd.Series(close), window=n).ma.to_numpy()
    target = np.where(~np.isnan(sma) & (close > np.nan_to_num(sma, nan=np.inf)), unit, 0.0)
    pf = vbt.Portfolio.from_orders(pd.Series(close), size=target, size_type="targetamount", price=close,
                                   init_cash=cash, fees=0.0, freq="1min")
    return sma, pf


def _event(close: np.ndarray, rule: dict):
    n, unit, cash = rule["n"], float(rule["unit"]), float(rule["init_cash"])
    sma_out = np.full(close.shape[0], np.nan)
    pf = vbt.Portfolio.from_order_func(pd.Series(close), _order_func_nb, close, n, unit, sma_out,
                                       init_cash=cash, freq="1min")
    return sma_out, pf


def _pack(sma, pf):
    return {"sma": [None if np.isnan(x) else float(x) for x in sma],
            "position": [float(x) for x in pf.assets().to_numpy()],
            "equity": [float(x) for x in pf.value().to_numpy()]}


class VectorBT:
    name = "opp_vectorbt"

    def run(self, inp: dict) -> dict:
        op = inp["op"]
        if op == "load":
            raise NotExpressible("vectorbt に市場データのファイルを読む口が無い(grep -rn 'read_csv|class CSVData' vectorbt/ は 0 件。"
                                 "data の型は Yahoo・Binance・CCXT・Alpaca からの取得と合成だけ)")
        if op == "jpx":
            raise NotExpressible("vectorbt に分割・併合・コード変更の調整と、日付ごとの銘柄集合の口が無い(grep -rni 'split|delist|universe' の当たりは"
                                 "データの分け方と列の名前だけ)")
        need(op == "vector_vs_event", f"未知の op {op}")
        need("bars" in inp, "vectorbt に約定から足を作る口が無い(足は呼び手が pandas で作って渡す。vbt 自身の集計の経路が無く、事象駆動の集計の経路も無い)")
        need(inp["rule"] and inp["rule"]["type"] == "sma_long_flat", "規則の形が違う")
        close = np.array([b["close"] for b in inp["bars"]], dtype=np.float64)
        t0 = time.perf_counter()
        ev = _pack(*_event(close, inp["rule"]))
        t1 = time.perf_counter()
        vc = _pack(*_vector(close, inp["rule"]))
        t2 = time.perf_counter()
        return {"paths": {"event": ev, "vector": vc}, "timing": {"event_s": t1 - t0, "vector_s": t2 - t1}}


TARGET = VectorBT()

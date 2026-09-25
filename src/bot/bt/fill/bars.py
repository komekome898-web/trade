"""Bars built from trade prints, for a tier-2 run whose data has prints only.

`bars_from_trades(trades, bar_ns)`: prints grouped by floor(exchange time /
bar_ns) (bars aligned to the Unix epoch), one BarEvent per group that has a
print, stamped at its close (start + bar_ns) with `start_time_ns` = start,
open / high / low / close / volume of its prints in time order. A bar is only
known at its close, so it is received then (never at its open).
"""
from __future__ import annotations

from typing import Iterable

from bot.bt.core import BarEvent, TradeEvent

from .spec import FillSpecError


def bars_from_trades(trades: Iterable[TradeEvent], bar_ns: int) -> list[BarEvent]:
    if type(bar_ns) is not int or bar_ns <= 0:
        raise FillSpecError(f"bar_ns must be an int > 0, got {bar_ns!r}")
    groups: dict[int, list[TradeEvent]] = {}
    last = None
    for tr in trades:
        if type(tr) is not TradeEvent:
            raise FillSpecError(f"bars_from_trades takes TradeEvents, got {type(tr).__name__}")
        t = int(tr.exchange_time_ns)
        if last is not None and t < last:
            raise FillSpecError("trade prints must be in time order")
        last = t
        groups.setdefault(t // bar_ns, []).append(tr)
    out = []
    for k in sorted(groups):
        g = groups[k]
        prices = [x.price for x in g]
        start, end = k * bar_ns, (k + 1) * bar_ns
        out.append(BarEvent(received_time_ns=end, exchange_time_ns=end, start_time_ns=start, open=prices[0],
                            high=max(prices), low=min(prices), close=prices[-1], volume=sum(x.size for x in g)))
    return out

"""Shared builders for the core tests (synthetic inputs only)."""
from __future__ import annotations

from bot.bt.core import (
    BarEvent,
    ClockEvent,
    Strategy,
    TradeEvent,
)

T0 = 1_700_000_000_000_000_000  # 2023-11-14T22:13:20Z in ns
SEC = 1_000_000_000
MS = 1_000_000


def trade(t: int, price: float = 100.0, size: float = 1.0, side: str = "buy", exch: int | None = None) -> TradeEvent:
    return TradeEvent(received_time_ns=t, exchange_time_ns=exch, price=price, size=size, side=side)


def bar(t: int, close: float, exch: int | None = None) -> BarEvent:
    return BarEvent(received_time_ns=t, exchange_time_ns=exch, open=close, high=close, low=close, close=close, volume=1.0)


def clock(t: int) -> ClockEvent:
    return ClockEvent(received_time_ns=t)


class Recorder(Strategy):
    """Records every delivered event; optional `act(event, ctx)` hook."""

    def __init__(self, act=None) -> None:
        self.seen = []
        self.act = act

    def on_event(self, event, ctx) -> None:
        self.seen.append(event)
        if self.act is not None:
            self.act(event, ctx)


def reachable(root) -> list:
    """Every object reachable from `root` by attribute access -- instance
    dicts, slots of every class in the MRO (mangled names included), a bound
    method's `__self__`, a function's closure cells and defaults, and the
    items of lists, tuples, sets and dicts -- breadth first, each once.
    Classes and modules are not entered (they are the program, not state)."""
    import types

    seen = {id(root)}
    out = [root]
    frontier = [root]
    while frontier:
        nxt = []
        for obj in frontier:
            kids = []
            if isinstance(obj, (types.MethodType, types.BuiltinMethodType)):
                s = getattr(obj, "__self__", None)
                if s is not None and not isinstance(s, types.ModuleType):
                    kids.append(s)
            elif isinstance(obj, types.FunctionType):
                for cell in obj.__closure__ or ():
                    try:
                        kids.append(cell.cell_contents)
                    except ValueError:
                        pass
                kids.extend(obj.__defaults__ or ())
            else:
                d = getattr(obj, "__dict__", None)
                if isinstance(d, dict):
                    kids.extend(d.values())
                for cls in type(obj).__mro__:
                    slots = cls.__dict__.get("__slots__", ())
                    for slot in ([slots] if isinstance(slots, str) else slots):
                        if slot in ("__dict__", "__weakref__"):
                            continue
                        if slot.startswith("__") and not slot.endswith("__"):
                            slot = f"_{cls.__name__.lstrip('_')}{slot}"
                        try:
                            kids.append(object.__getattribute__(obj, slot))
                        except AttributeError:
                            pass
                if isinstance(obj, list):
                    kids.extend(list.__getitem__(obj, slice(None)))
                elif isinstance(obj, (tuple, set, frozenset)):
                    kids.extend(tuple.__getitem__(obj, slice(None)) if isinstance(obj, tuple) else obj)
                elif isinstance(obj, dict):
                    kids.extend(dict.keys(obj))
                    kids.extend(dict.values(obj))
            for k in kids:
                if isinstance(k, (type, types.ModuleType)) or id(k) in seen:
                    continue
                seen.add(id(k))
                out.append(k)
                nxt.append(k)
        frontier = nxt
    return out


def find(root, cls) -> list:
    """The objects of class `cls` (exactly) reachable from `root`."""
    return [o for o in reachable(root) if type(o) is cls]

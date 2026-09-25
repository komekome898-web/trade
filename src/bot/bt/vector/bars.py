"""Bars from trades, two ways that must agree bit for bit.

Definition (both paths): a bar covers [start, start + interval) with start
= floor(t / interval) * interval on the UTC epoch grid; open = first price,
high = max, low = min, close = last price, volume = the quantities summed
in delivered order (q0 + q1 + ...; the order is part of the definition so
the float sum is the same in both paths); an interval with no trade has no
bar.

`bars_from_trades` is the vector path (numpy over whole arrays; the volume
sum walks the position inside each bar, one vector step per position, so
every bar is summed in the same order as the event path).
`bot.bt.vector.event_path.run_event_bars` is the event path (the core's
engine delivers each trade to a strategy that builds the bars one trade at
a time).
"""
from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from ..data.errors import VectorError

NS = 1_000_000_000


def interval_ns(interval_s: Any) -> int:
    if type(interval_s) is not int or interval_s <= 0:
        raise VectorError(f"interval_s must be an int > 0, got {interval_s!r}")
    return interval_s * NS


def _times(t_ns: Sequence) -> np.ndarray:
    vals = list(t_ns)
    for v in vals:
        if type(v) is not int and not isinstance(v, np.integer):
            raise VectorError(f"times must be ints of ns, got {type(v).__name__} {v!r}")
    t = np.asarray([int(v) for v in vals], dtype=np.int64) if vals else np.zeros(0, dtype=np.int64)
    if t.size > 1 and bool(np.any(t[1:] < t[:-1])):
        i = int(np.flatnonzero(t[1:] < t[:-1])[0]) + 1
        raise VectorError(f"trade times go backward at index {i}; sort or resolve them first (the data layer's anomalies)")
    return t


def _floats(x: Sequence, name: str, n: int) -> np.ndarray:
    a = np.asarray(list(x), dtype=np.float64)
    if a.shape != (n,):
        raise VectorError(f"{name} has {a.size} values, the times have {n}")
    if not bool(np.all(np.isfinite(a))):
        raise VectorError(f"{name} has a non-finite value")
    return a


def bars_from_trades(t_ns: Sequence, px: Sequence, qty: Sequence, interval_s: int) -> list[dict]:
    iv = interval_ns(interval_s)
    t = _times(t_ns)
    n = t.size
    p = _floats(px, "px", n)
    q = _floats(qty, "qty", n)
    if n == 0:
        return []
    b = (t // iv) * iv
    starts = np.flatnonzero(np.concatenate(([True], b[1:] != b[:-1])))
    ends = np.concatenate((starts[1:], [n]))
    lens = ends - starts
    op = p[starts]
    cl = p[ends - 1]
    hi = np.maximum.reduceat(p, starts)
    lo = np.minimum.reduceat(p, starts)
    vol = q[starts].copy()
    for k in range(1, int(lens.max())):
        m = lens > k
        vol[m] = vol[m] + q[starts[m] + k]
    st = b[starts]
    return [{"start_ns": int(st[i]), "open": float(op[i]), "high": float(hi[i]), "low": float(lo[i]),
             "close": float(cl[i]), "volume": float(vol[i])} for i in range(starts.size)]

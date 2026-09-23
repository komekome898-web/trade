"""O(1)-to-construct, read-only view of a bounded prefix of the event log.

Round-1 critic finding i0-r1-03: `CoreEngine.run` used to build the
"visible so far" history by slicing `self._log[: i + 1]` on every
iteration. Slicing a tuple copies it, so that single line conflated two
different things: (a) deciding *how far* the strategy may see (an O(1)
integer, `i + 1`), and (b) actually materializing that many events as a new
tuple (an O(i) copy). Doing (b) unconditionally, every iteration, whether or
not anything downstream ever asks for the history, is what made the loop
O(n^2) over a run of n events.

`EventWindow` separates the two: constructing one only remembers the
underlying (already-sorted, already-frozen) log and an end index -- no
copying. It behaves like a read-only sequence (`len`, indexing incl.
negative indices, slicing, iteration) backed directly by `log`, so any
caller that only needs `len()` or a bounded slice pays for exactly that,
and a caller that never touches it (e.g. a no-op strategy) pays nothing.
Only `StrategyContext.visible_events()` (api.py) turns a requested portion
of a window into an actual `tuple` -- and only when a strategy calls it.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Iterator

from .events import Event


class EventWindow(Sequence):
    """Read-only view of `log[:end]`. O(1) to construct; never copies `log`."""

    __slots__ = ("_log", "_end")

    def __init__(self, log: tuple[Event, ...], end: int) -> None:
        self._log = log
        self._end = end

    def __len__(self) -> int:
        return self._end

    def __getitem__(self, index):
        if isinstance(index, slice):
            start, stop, step = index.indices(self._end)
            return self._log[start:stop:step]
        if index < 0:
            index += self._end
        if not 0 <= index < self._end:
            raise IndexError(index)
        return self._log[index]

    def __iter__(self) -> Iterator[Event]:
        return iter(self._log[: self._end])

    def __repr__(self) -> str:  # pragma: no cover -- debugging aid only
        return f"EventWindow(len={self._end})"

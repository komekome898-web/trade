"""Plain immutable data for everything that crosses a path of the core.

A request the strategy sends, and a notice the venue sends back, travel on
a channel (ordering.py) and are read on the other side at a LATER time. On
a real connection what arrives is what was sent: bytes on the wire at send
time. So nothing that crosses a path may be shared, changeable state: if
the strategy and the venue held the same list, either side could change
what the other sees without sending anything, and the change would skip
the channel's latency -- a path to the future (i0-r4-02).

The core makes such payloads values WHEN THEY ARE MADE (not by copying
when they are handed over: a copy forgotten at one hand-over is a leak,
while a value can be shared by everyone). `freeze` turns plain data into an
equal, deeply immutable, hashable form and refuses anything else:

* scalars: None, bool, int, float, complex, str, bytes, Decimal, Fraction
  (exact types) and Enum members whose value is one of those;
* containers of plain data: tuple, list, dict, set, frozenset. A list
  becomes a `FrozenList`, a dict a `FrozenDict`, a set a `FrozenSet`; each
  remembers what it was, so `thaw` gives back a fresh list / dict / set.

Anything else -- a function (it can read the sender's state when it is
called, later), an arbitrary object, a generator, a container that holds
itself -- raises `ValueError`; the caller wraps it in its own error type.
"""
from __future__ import annotations

import enum
from decimal import Decimal
from fractions import Fraction
from typing import Any, Iterator, Mapping

_SCALARS: frozenset[type] = frozenset(
    {type(None), bool, int, float, complex, str, bytes, Decimal, Fraction}
)

PLAIN_DATA_RULE = (
    "scalars None, bool, int, float, complex, str, bytes, Decimal, Fraction (exact types) and "
    "Enum members whose value is one of those, and tuple / list / dict / set / frozenset of plain data; lists, dicts and sets "
    "are stored immutable and read back as fresh copies; anything else is refused"
)


class FrozenList(tuple):
    """An immutable list (was a `list` when given)."""

    __slots__ = ()

    def __repr__(self) -> str:
        return f"FrozenList({list(self)!r})"


class FrozenSet(frozenset):
    """An immutable set (was a `set` when given)."""

    __slots__ = ()

    def __repr__(self) -> str:
        return f"FrozenSet({set(self)!r})"


class FrozenDict(Mapping):
    """An immutable, hashable dict (was a `dict` when given). Keeps the
    given order; equal to any mapping with the same items."""

    __slots__ = ("_items", "_map", "_hash")

    def __init__(self, items: Mapping) -> None:
        pairs = tuple(items.items())
        object.__setattr__(self, "_items", pairs)
        object.__setattr__(self, "_map", dict(pairs))
        object.__setattr__(self, "_hash", None)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("FrozenDict is immutable")

    def __reduce__(self):
        # rebuilt through __init__ (copy, deepcopy, pickle), never by setting slots
        return (FrozenDict, (dict(self._items),))

    def __getitem__(self, key: Any) -> Any:
        return self._map[key]

    def __iter__(self) -> Iterator[Any]:
        return (k for k, _ in self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __hash__(self) -> int:
        h = self._hash
        if h is None:
            h = hash(frozenset(self._items))
            object.__setattr__(self, "_hash", h)
        return h

    def __repr__(self) -> str:
        return f"FrozenDict({dict(self._items)!r})"


def freeze(value: Any, where: str = "value") -> Any:
    """An equal, deeply immutable form of plain data; `ValueError` for
    anything that is not plain data (module docstring)."""
    return _freeze(value, where, set())


def _freeze(value: Any, where: str, path: set[int]) -> Any:
    t = type(value)
    if t in _SCALARS or (isinstance(value, enum.Enum) and type(value.value) in _SCALARS):
        return value
    if t not in (tuple, list, dict, set, frozenset, FrozenList, FrozenDict, FrozenSet):
        raise ValueError(
            f"{where} holds a {t.__module__}.{t.__qualname__}, which is not plain data "
            f"({PLAIN_DATA_RULE}); what crosses a path is sent at one time and may not hold "
            f"state that can change or code that runs later"
        )
    key = id(value)
    if key in path:
        raise ValueError(f"{where} holds itself (a cycle); plain data has no cycles")
    path.add(key)
    try:
        if t in (tuple, FrozenList):
            items = tuple(_freeze(v, f"{where}[{i}]", path) for i, v in enumerate(value))
            return FrozenList(items) if t is FrozenList else items
        if t is list:
            return FrozenList(_freeze(v, f"{where}[{i}]", path) for i, v in enumerate(value))
        if t in (dict, FrozenDict):
            frozen = {}
            for k, v in value.items():
                fk = _freeze(k, f"{where} key {k!r}", path)
                frozen[fk] = _freeze(v, f"{where}[{k!r}]", path)
            return FrozenDict(frozen)
        items = frozenset(_freeze(v, f"{where} element", path) for v in value)
        return FrozenSet(items) if t in (set, FrozenSet) else items
    finally:
        path.discard(key)


def thaw(value: Any) -> Any:
    """A fresh, changeable copy of frozen plain data, with the containers
    as they were given (list, dict, set); changing it changes nothing
    else."""
    t = type(value)
    if t is FrozenList:
        return [thaw(v) for v in value]
    if t is tuple:
        return tuple(thaw(v) for v in value)
    if t is FrozenDict:
        return {thaw(k): thaw(v) for k, v in value.items()}
    if t is FrozenSet:
        return {thaw(v) for v in value}
    if t is frozenset:
        return frozenset(thaw(v) for v in value)
    return value

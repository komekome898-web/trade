"""Plain immutable data for everything that crosses a path of the core.

A request the strategy sends, and a notice the venue sends back, travel on
a channel (ordering.py) and are read on the other side at a LATER time. On
a real connection what arrives is what was sent: bytes on the wire at send
time. So nothing that crosses a path may be shared, changeable state or
code of the sender's: if the strategy and the venue held the same list,
either side could change what the other sees without sending anything; if
a field held an object of a class the sender wrote (a `str` subclass, an
`Enum` member, anything that answers `==` as it likes), its methods would
run when the receiver USES the field -- at the arrival time, reading the
sender's state then. Either is a path that skips the channel's latency
(i0-r4-02, i0-r5-01).

The core makes such payloads values WHEN THEY ARE MADE, with the functions
below, and every carrier class of the core (contract.py `PATH_CARRIERS`)
passes every one of its fields through one of them:

* `as_text`, `as_float`, `as_int`, `as_flag`, `as_choice` -- one field of
  a declared type; they return the BUILT-IN type itself (`str`, `float`,
  `int`, `bool`), never a subclass;
* `freeze` -- plain data of any shape (`OrderRequest.extra`): an equal,
  deeply immutable, hashable form.

The one scalar rule (`scalar`) -- the ONE rule for which foreign values
become values, used by every field function below (i0-r6-03):

* an instance of an exact built-in scalar type (None, bool, int, float,
  complex, str, bytes, Decimal, Fraction) is kept;
* an instance of a SUBCLASS of int, float, complex, str or bytes
  (`IntEnum` / `StrEnum` members, numpy.float64, numpy.str_, ...) is stored
  as the built-in value it holds, read by the built-in type's own method
  (`str.__str__`, `float.__float__`, `int.__index__`, ...) so no method of
  the subclass ever runs or crosses;
* a numpy bool (what numpy and pandas comparisons give) is stored as the
  `bool` it holds, read by numpy's own method;
* a number of the numeric tower (`numbers.Integral` -> int,
  `numbers.Real` -> float, `numbers.Complex` -> complex; numpy.int64,
  numpy.float32, ...) is converted once, NOW, to the built-in type itself;
* anything else -- a plain `Enum` member (its class is the sender's), a
  function (it can read the sender's state when it is called, later), an
  arbitrary object, a generator, a container that holds itself -- raises
  `ValueError`; the caller wraps it in its own error type.

Every type decision here reads the object's REAL type, `type(x)` (`is_a`),
never `isinstance`: `isinstance` also believes the object's own
`__class__`, which any object may answer as it likes, while the built-in
reads check the real type -- a check that believed the claim and a read
that does not would see two different facts (i0-r6-03). Every error names
the real type in full (`module.name`).

Containers of plain data (tuple, list, dict, set, frozenset): a list
becomes a `FrozenList`, a dict a `FrozenDict`, a set a `FrozenSet`; each
remembers what it was, so `thaw` gives back a fresh list / dict / set.
"""
from __future__ import annotations

import numbers
import sys
from decimal import Decimal
from fractions import Fraction
from typing import Any, Iterator, Mapping

_SCALARS: frozenset[type] = frozenset(
    {type(None), bool, int, float, complex, str, bytes, Decimal, Fraction}
)

# A subclass instance of one of these is stored as the built-in value it
# holds, read by the built-in type's own method (never the subclass's).
# bool cannot be subclassed; int is checked after it.
_BUILTIN_READ: tuple[tuple[type, Any], ...] = (
    (str, str.__str__),
    (float, float.__float__),
    (int, int.__index__),
    (complex, complex.__complex__),
    (bytes, bytes.__bytes__),
)

PLAIN_DATA_RULE = (
    "scalars None, bool, int, float, complex, str, bytes, Decimal, Fraction (exact types); an instance of "
    "a subclass of int / float / complex / str / bytes (IntEnum and StrEnum members included) is stored "
    "as the built-in value it holds, read by the built-in type (the subclass's methods never run); a numpy "
    "bool is stored as the bool it holds; a number of the numeric tower (numbers.Integral / Real / "
    "Complex, numpy's included) is converted once, when it is sent, to int / float / complex; types are "
    "decided by the real type, never by what the object claims (__class__); "
    "tuple / list / dict / set / frozenset of plain data; lists, dicts and sets are stored immutable and "
    "read back as fresh copies; anything else (a plain Enum member, a function, any other object) is refused"
)

FIELD_RULE = (
    "every field of a carrier (PATH_CARRIERS) is made, when the carrier is made, by one of values.as_text / "
    "as_float / as_int / as_flag / as_choice / freeze, which return the built-in type itself (str, float, "
    "int, bool, frozen plain data), never a subclass or an object of the sender's"
)


def is_a(value: Any, cls: Any) -> bool:
    """Is the REAL type of `value` `cls` or a subclass of it? Unlike
    `isinstance`, it does not ask the object (an object may claim any
    class through `__class__`); `cls` may be a class, an ABC or a tuple."""
    return issubclass(type(value), cls)


def type_name(value: Any) -> str:
    """The real type of `value` in full (`numpy.bool`, not `bool`)."""
    t = type(value)
    return t.__qualname__ if t.__module__ == "builtins" else f"{t.__module__}.{t.__qualname__}"


def _numpy_bool() -> Any:
    # numpy is not imported for this: a numpy bool exists only once numpy is
    np = sys.modules.get("numpy")
    return getattr(np, "bool_", None) if np is not None else None


def _now(convert: Any, value: Any, where: str) -> Any:
    """Convert a foreign number once, now, to the built-in type itself; an
    error in the sender's conversion is a ValueError of this module."""
    try:
        out = convert(value)
    except Exception as exc:  # the sender's own conversion code, or a number too large
        article = "an" if convert is int else "a"
        raise ValueError(
            f"{where} must be a number {article} {convert.__name__} can hold, got a "
            f"{type_name(value)} ({type(exc).__name__}: {exc})"
        ) from None
    for base, read in _BUILTIN_READ:
        if base is convert:
            return out if type(out) is convert else read(out)
    return out  # pragma: no cover


_NOT_PLAIN = object()  # what `_plain_scalar` gives for a value the scalar rule refuses


def _plain_scalar(value: Any, where: str) -> Any:
    """The scalar rule (module docstring): a built-in scalar itself, or
    `_NOT_PLAIN`. Only a sender's failing conversion raises (ValueError)."""
    t = type(value)
    if t in _SCALARS:
        return value
    for base, read in _BUILTIN_READ:
        if issubclass(t, base):
            return read(value)
    nb = _numpy_bool()
    if nb is not None and issubclass(t, nb):
        return nb.__bool__(value)
    if issubclass(t, numbers.Integral):
        return _now(int, value, where)
    if issubclass(t, numbers.Real):
        return _now(float, value, where)
    if issubclass(t, numbers.Complex):
        return _now(complex, value, where)
    return _NOT_PLAIN


def scalar(value: Any, where: str = "value") -> Any:
    """The one scalar rule (module docstring): a built-in scalar itself,
    or `ValueError`."""
    got = _plain_scalar(value, where)
    if got is _NOT_PLAIN:
        raise ValueError(
            f"{where} holds a {type_name(value)}, which is not plain data "
            f"({PLAIN_DATA_RULE}); what crosses a path is sent at one time and may not hold "
            f"state that can change or code that runs later"
        )
    return got


def as_text(value: Any, where: str) -> str:
    """A text field: a `str` (a subclass instance gives the characters it
    holds, as a `str`)."""
    if not is_a(value, str):
        raise ValueError(f"{where} must be a str, got {type_name(value)}")
    return value if type(value) is str else str.__str__(value)


def as_choice(value: Any, where: str, allowed: tuple) -> str:
    """A text field with a fixed set of values. Made a `str` first, then
    compared: an object that answers `==` as it likes is not text and is
    refused before any comparison runs."""
    text = as_text(value, where)
    if text not in allowed:
        raise ValueError(f"{where} must be one of {allowed}, got {text!r}")
    return text


def as_flag(value: Any, where: str) -> bool:
    """A true/false field: a `bool`, or a numpy bool (read as the `bool` it
    holds); nothing that decides its truth when it is asked, and no
    number."""
    got = _plain_scalar(value, where)
    if type(got) is not bool:
        raise ValueError(f"{where} must be a bool, got {type_name(value)}")
    return got


def as_int(value: Any, where: str) -> int:
    """An integer field: an int itself (the scalar rule: a subclass gives
    the int it holds, an integral number of the numeric tower is converted
    once, now); never a bool."""
    got = _plain_scalar(value, where)
    if type(got) is not int:
        raise ValueError(f"{where} must be an int, got {type_name(value)}")
    return got


def as_float(value: Any, where: str, *, numbers_only: bool = True) -> float:
    """A number field, as a `float` itself (the scalar rule: a float or int
    subclass gives the number it holds, a real number of the numeric tower
    is converted once, now; a Fraction is converted); never a bool.
    `numbers_only=False` also accepts a numeric str and a Decimal (what
    `float()` reads exactly as text). Whether the
    number is finite or positive is the caller's rule."""
    got = _plain_scalar(value, where)
    t = type(got)
    if t is float:
        return got
    if t is int or t is Fraction or (t is Decimal and not numbers_only):
        return _now(float, got, where)
    if t is str and not numbers_only:
        try:
            return float(got)
        except ValueError:
            raise ValueError(f"{where} must be a number, got the text {got!r}") from None
    raise ValueError(f"{where} must be a number, got {type_name(value)}")


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
    if t not in (tuple, list, dict, set, frozenset, FrozenList, FrozenDict, FrozenSet):
        return scalar(value, where)
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

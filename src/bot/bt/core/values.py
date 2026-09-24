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

* nothing a sender hands over is kept: every accepted value is BUILT
  ANEW by the core, as an object no one else holds (i0-r7-02: the
  round-5 rule kept "an instance of an exact built-in scalar type" as
  the same object, and a `Fraction` -- a Python class whose slots can be
  assigned -- then crossed live). `None`, `True` and `False` are the only
  objects kept (there is one of each); an object the interpreter itself
  keeps one of per value (a small int, the empty string) may come back
  as that object;
* the accepted types are one table, `BUILD`: None, bool, int, float,
  complex, str, bytes, Decimal, Fraction. For each, the value is read by
  that type's OWN method or slot descriptor (`int.__neg__`,
  `float.__mul__`, `str.encode`, `bytes.hex`, `complex.real`,
  `Decimal.__str__`, `Fraction`'s `_numerator` / `_denominator` slots)
  and a new object is built from what was read, so no method of the
  sender's class runs and nothing of the sender's object is kept;
* an instance of a SUBCLASS of one of those types (`IntEnum` / `StrEnum`
  members, numpy.float64, numpy.str_, a `Fraction` or `Decimal`
  subclass, ...) is read the same way, by the base type's own method,
  and built as the base type;
* a numpy bool (what numpy and pandas comparisons give) is stored as the
  `bool` it holds, read by numpy's own method;
* a number of the numeric tower (`numbers.Integral` -> int,
  `numbers.Real` -> float, `numbers.Complex` -> complex; numpy.int64,
  numpy.float32, ...) is converted once, NOW, and what the conversion
  returned is built anew as the built-in type itself;
* anything else -- a plain `Enum` member (its class is the sender's), a
  function (it can read the sender's state when it is called, later), an
  arbitrary object, a generator, a container that holds itself -- raises
  `ValueError`; the caller wraps it in its own error type.

`renew` makes the core's own copy of a value the core built (a field of a
carrier): the same table, and new containers. The engine hands every
receiver such a copy of its own (engine.py), so no receiver holds what a
sender or another receiver holds.

Containers of plain data (tuple, list, dict, set, frozenset, and the
core's own frozen ones): a list becomes a `FrozenList`, a dict a
`FrozenDict`, a set a `FrozenSet` -- always new containers of new values;
each remembers what it was, so `thaw` gives back a fresh list / dict /
set of fresh values.
"""
from __future__ import annotations

import numbers
import sys
import types
from decimal import Decimal
from fractions import Fraction
from typing import Any, Callable, Iterator, Mapping, Optional


def _same(x: Any) -> Any:  # None, True, False: one object each
    return x


def _new_int(x: int) -> int:
    return int.__neg__(int.__neg__(x))


def _new_float(x: float) -> float:
    return float.__mul__(x, 1.0)  # -0.0, inf and nan kept


_REAL = complex.__dict__["real"].__get__
_IMAG = complex.__dict__["imag"].__get__


def _new_complex(x: complex) -> complex:
    return complex(_new_float(_REAL(x)), _new_float(_IMAG(x)))


def _new_str(x: str) -> str:
    return str.encode(x, "utf-8", "surrogatepass").decode("utf-8", "surrogatepass")


def _new_bytes(x: bytes) -> bytes:
    return bytes.fromhex(bytes.hex(x))


def _new_decimal(x: Decimal) -> Decimal:
    return Decimal(Decimal.__str__(x))  # text -> Decimal is exact (no context rounding)


_NUMERATOR = Fraction.__dict__["_numerator"].__get__
_DENOMINATOR = Fraction.__dict__["_denominator"].__get__


def _new_fraction(x: Fraction) -> Fraction:
    try:
        n, d = _NUMERATOR(x), _DENOMINATOR(x)
    except AttributeError:
        raise ValueError("a Fraction without its numerator or denominator") from None
    if not (issubclass(type(n), int) and issubclass(type(d), int)) or type(n) is bool or type(d) is bool:
        raise ValueError(f"a Fraction whose parts are not ints ({type_name(n)}, {type_name(d)})")
    try:
        return Fraction(_new_int(n), _new_int(d))
    except ZeroDivisionError:
        raise ValueError("a Fraction with a zero denominator") from None


# THE table of accepted scalar types (module docstring): each type -> the
# builder that reads a value of it (or of a subclass) by the type's own
# method and makes a new object. Nothing here returns what it was given,
# except the three objects there is one of.
BUILD: dict[type, Callable[[Any], Any]] = {
    type(None): _same,
    bool: _same,
    int: _new_int,
    float: _new_float,
    complex: _new_complex,
    str: _new_str,
    bytes: _new_bytes,
    Decimal: _new_decimal,
    Fraction: _new_fraction,
}
# the bases a subclass is read as (bool cannot be subclassed; checked in
# this order, after the exact type)
_BASES: tuple[type, ...] = (str, bytes, float, int, complex, Decimal, Fraction)

PLAIN_DATA_RULE = (
    "every value is built anew by the core (nothing a sender hands over is kept; None, True and False "
    "are the one objects kept); accepted scalars are the table BUILD: None, bool, int, float, complex, "
    "str, bytes, Decimal, Fraction, each read by that type's own method or slot and built as a new "
    "object; an instance of a subclass of one of them (IntEnum and StrEnum members, numpy's, a Fraction "
    "or Decimal subclass) is read by the base type and built as the base type (the subclass's methods "
    "never run); a numpy bool is stored as the bool it holds; a number of the numeric tower "
    "(numbers.Integral / Real / Complex, numpy's included) is converted once, when it is sent, and built "
    "anew as int / float / complex; types are decided by the real type, never by what the object claims "
    "(__class__); tuple / list / dict / set / frozenset of plain data become new immutable containers "
    "and are read back as fresh copies; anything else (a plain Enum member, a function, any other "
    "object) is refused"
)

FIELD_RULE = (
    "every field of a carrier (PATH_CARRIERS) is made, when the carrier is made, by one of values.as_text / "
    "as_float / as_int / as_flag / as_choice / freeze, which build a new object of the built-in type itself "
    "(str, float, int, bool, frozen plain data), never a subclass, an object of the sender's, or the "
    "object the sender handed over"
)


def is_a(value: Any, cls: Any) -> bool:
    """Is the REAL type of `value` `cls` or a subclass of it? Unlike
    `isinstance`, it does not ask the object (an object may claim any
    class through `__class__`); `cls` may be a class, an ABC or a tuple."""
    return issubclass(type(value), cls)


# A class's names, read by `type`'s own descriptors (round 11): the usual
# read (`cls.__qualname__`) goes through the class's metaclass, which can run
# code of whoever wrote the class; `type`'s descriptors read what `type`
# stored, and run nothing.
_TYPE_QUALNAME = type.__dict__["__qualname__"].__get__
_TYPE_MODULE = type.__dict__["__module__"].__get__
# an exception's arguments, read by BaseException's own descriptor (a class
# may shadow `args` with a property of its own)
_EXC_ARGS = BaseException.__dict__["args"].__get__


def _own_text(value: Any) -> Optional[str]:
    """`value` as a str made by `str`'s own method when its real type is str
    or a subclass of it (a subclass's `__str__` / `__format__` never run);
    None for anything else."""
    return str.__str__(value) if issubclass(type(value), str) else None


def class_parts(t: type) -> tuple[Optional[str], str]:
    """(module, qualified name) of class `t`, read by `type`'s own
    descriptors and made str by `str`'s own method: no code of the class,
    its metaclass or what its body set `__module__` to runs. A module that
    is not a str reads as None; a name that is not one as "?"."""
    try:
        module = _own_text(_TYPE_MODULE(t))
    except AttributeError:  # a class made without a module
        module = None
    return module, _own_text(_TYPE_QUALNAME(t)) or "?"


def type_name(value: Any) -> str:
    """The real type of `value` in full (`numpy.bool`, not `bool`), read
    without running any code of the value, its class or its metaclass
    (`class_parts`)."""
    module, qualname = class_parts(type(value))
    return qualname if module in (None, "builtins") else f"{module}.{qualname}"


_TEXT_LIMIT = 300


def _arg_text(arg: Any) -> str:
    t = type(arg)
    if t is str:
        return arg
    if arg is None or t is bool:
        return "None" if arg is None else ("True" if arg else "False")
    if t is int:
        return int.__repr__(arg)
    if t is float:
        return float.__repr__(arg)
    return f"<a {type_name(arg)}>"


def exception_text(exc: BaseException) -> str:
    """"<its real type>: <its arguments>" for an exception raised by code
    outside the core (the strategy, a socket, a stream, a sender's
    conversion), read without running any code of it (round 11): the type
    by `type_name`; the arguments by BaseException's own descriptor, each
    one that is a str, int, float, bool or None itself (not a subclass) as
    its text, anything else as its type's name. Its `__str__`, `__repr__`,
    `__format__`, `__getattribute__`, an `args` property of its class and
    its metaclass never run. At most `_TEXT_LIMIT` characters of arguments."""
    try:
        args = _EXC_ARGS(exc)
    except TypeError:  # not an exception at all
        args = ()
    if type(args) is not tuple:  # pragma: no cover - BaseException stores a tuple itself
        args = ()
    text = ", ".join(_arg_text(tuple.__getitem__(args, i)) for i in range(tuple.__len__(args)))
    if len(text) > _TEXT_LIMIT:
        text = text[:_TEXT_LIMIT] + "..."
    name = type_name(exc)
    return f"{name}: {text}" if text else name


def _numpy_bool() -> Any:
    # numpy is not imported for this: a numpy bool exists only once numpy is
    np = sys.modules.get("numpy")
    return getattr(np, "bool_", None) if np is not None else None


def _now(convert: Any, value: Any, where: str) -> Any:
    """Convert a foreign number once, now, and build what the conversion
    returned anew as the built-in type itself; an error in the sender's
    conversion is a ValueError of this module."""
    try:
        out = convert(value)
    except Exception as exc:  # the sender's own conversion code, or a number too large
        article = "an" if convert is int else "a"
        raise ValueError(
            f"{where} must be a number {article} {convert.__name__} can hold, got a "
            f"{type_name(value)} ({exception_text(exc)})"  # no code of the sender's exception runs
        ) from None
    if not issubclass(type(out), convert):  # pragma: no cover - int() / float() / complex() check it
        raise ValueError(f"{where}: {convert.__name__}() gave a {type_name(out)}")
    return BUILD[convert](out)


_NOT_PLAIN = object()  # what `_plain_scalar` gives for a value the scalar rule refuses


_MRO = type.__dict__["__mro__"].__get__  # a class's own MRO, read by `type`'s slot


def _base_of(t: type) -> Any:
    """The base of `_BASES` a class derives from, or None -- read from the
    class's own MRO, so no metaclass or ABC hook (`Fraction` is an ABC:
    `issubclass` would ask its subclasses' hooks) runs (round 10)."""
    mro = _MRO(t)
    for base in _BASES:
        if base in mro:
            return base
    return None


def _plain_scalar(value: Any, where: str) -> Any:
    """The scalar rule (module docstring): a NEW built-in scalar, or
    `_NOT_PLAIN`. A sender's failing conversion, or a broken Fraction,
    raises ValueError."""
    t = type(value)
    build = BUILD.get(t)
    if build is not None:
        return build(value)
    base = _base_of(t)
    if base is not None:
        return BUILD[base](value)
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


class Unsettled(ValueError):
    """A value that cannot be read without running code of the one who
    handed it over (`settle`)."""


def settle(value: Any) -> Any:
    """`value` as plain data of the built-in types THEMSELVES, made without
    running any code of the one who handed it over (round 10, i0-r9-02):
    a built-in scalar or a subclass of one is built anew as the base type by
    the base type's own method (the subclass's code -- its `__repr__`,
    `__eq__`, `__hash__` -- never runs, and nothing later can run it: what
    comes out holds none of the sender's objects); a numpy bool as the bool
    it holds; a container (tuple, list, dict, set, frozenset, a subclass of
    one, or the core's FrozenList / FrozenDict / FrozenSet) is read by the
    base type's own methods and made anew of settled values. Anything whose
    reading needs its own code (a number of the numeric tower: `__int__`,
    `__float__`, `__index__`) or is not plain data raises `Unsettled`, a
    ValueError, whose text names only the value's type. The core applies
    this to what it reads AFTER a callback returned (the outbox, engine.py
    `_take_message`): the strategy's code runs only inside its own calls."""
    return _settle(value, set())


def _settle(value: Any, path: set[int]) -> Any:
    t = type(value)
    build = BUILD.get(t)
    if build is not None:
        return build(value)
    mro = _MRO(t)
    container = next((c for c in (tuple, list, set, frozenset, dict) if c in mro), None)
    if container is not None or t is FrozenDict:
        key = id(value)
        if key in path:
            raise Unsettled(f"a {type_name(value)} that holds itself (a cycle) is not plain data")
        path.add(key)
        try:
            if t is FrozenDict:
                try:
                    pairs = _FD_ITEMS(value)
                except AttributeError:
                    pairs = None
                if type(pairs) is not tuple or any(type(p) is not tuple or tuple.__len__(p) != 2
                                                   for p in tuple.__iter__(pairs)):
                    raise Unsettled("a FrozenDict whose pairs were replaced is not plain data")
                return FrozenDict._from_pairs(tuple(
                    (_settle(tuple.__getitem__(p, 0), path), _settle(tuple.__getitem__(p, 1), path))
                    for p in tuple.__iter__(pairs)))
            if container is dict:
                return {_settle(k, path): _settle(v, path) for k, v in dict.items(value)}
            items = [_settle(v, path) for v in container.__iter__(value)]
            if t is FrozenList:
                return FrozenList(items)
            if t is FrozenSet:
                return FrozenSet(items)
            return container(items)
        finally:
            path.discard(key)
    base = _base_of(t)
    if base is not None:
        return BUILD[base](value)
    nb = _numpy_bool()
    if nb is not None and nb in mro:
        return nb.__bool__(value)
    raise Unsettled(
        f"a {type_name(value)} cannot be read without running its own code (or is not plain data)"
    )


def settled(value: Any) -> bool:
    """Would `settle(value)` succeed?"""
    try:
        settle(value)
    except Unsettled:
        return False
    return True


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
    """A text field: a new `str` (a subclass instance gives the characters
    it holds, read by `str`'s own method)."""
    if not is_a(value, str):
        raise ValueError(f"{where} must be a str, got {type_name(value)}")
    return _new_str(value)


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
    """A number field, as a new `float` itself (the scalar rule: a float or
    int subclass gives the number it holds, a real number of the numeric
    tower is converted once, now; a Fraction is converted); never a bool.
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
    given order; equal to any mapping with the same items. Its lookup
    table is a read-only mapping proxy: no dict of it is reachable by
    attribute access."""

    __slots__ = ("_items", "_map", "_hash")

    def __init__(self, items: Mapping) -> None:
        pairs = tuple(items.items())
        object.__setattr__(self, "_items", pairs)
        object.__setattr__(self, "_map", types.MappingProxyType(dict(pairs)))
        object.__setattr__(self, "_hash", None)

    @classmethod
    def _from_pairs(cls, pairs: tuple) -> "FrozenDict":
        self = object.__new__(cls)
        object.__setattr__(self, "_items", pairs)
        object.__setattr__(self, "_map", types.MappingProxyType(dict(pairs)))
        object.__setattr__(self, "_hash", None)
        return self

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


_FD_ITEMS = FrozenDict.__dict__["_items"].__get__


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
            items = tuple([_freeze(v, f"{where}[{i}]", path) for i, v in enumerate(tuple.__iter__(value))])
            return FrozenList(items) if t is FrozenList else items
        if t is list:
            return FrozenList([_freeze(v, f"{where}[{i}]", path) for i, v in enumerate(list.__iter__(value))])
        if t in (dict, FrozenDict):
            # read by the real type's own methods (a dict's, or the core's
            # FrozenDict's pairs), then built anew
            src = dict.items(value) if t is dict else _frozen_pairs(value, where)
            frozen: dict = {}
            for k, v in src:
                fk = _freeze(k, f"{where} key {k!r}", path)
                frozen[fk] = _freeze(v, f"{where}[{k!r}]", path)
            return FrozenDict._from_pairs(tuple(frozen.items()))
        each = set.__iter__(value) if t is set else frozenset.__iter__(value)
        items = frozenset([_freeze(v, f"{where} element", path) for v in each])
        return FrozenSet(items) if t in (set, FrozenSet) else items
    finally:
        path.discard(key)


def _frozen_pairs(value: "FrozenDict", where: str) -> tuple:
    """The pairs a FrozenDict holds, read by its own slot; a FrozenDict a
    sender broke (its slot set to something else with object.__setattr__)
    is not plain data."""
    try:
        pairs = _FD_ITEMS(value)
    except AttributeError:
        pairs = None
    if type(pairs) is not tuple or any(type(p) is not tuple or tuple.__len__(p) != 2 for p in pairs):
        raise ValueError(f"{where} holds a FrozenDict whose pairs were replaced by something else; not plain data")
    return pairs


def thaw(value: Any) -> Any:
    """A fresh, changeable copy of frozen plain data, with the containers
    as they were given (list, dict, set) and every value built anew;
    changing it changes nothing else."""
    t = type(value)
    if t is FrozenList:
        return [thaw(v) for v in value]
    if t is tuple:
        return tuple([thaw(v) for v in value])
    if t is FrozenDict:
        return {thaw(k): thaw(v) for k, v in value._items}
    if t is FrozenSet:
        return {thaw(v) for v in value}
    if t is frozenset:
        return frozenset([thaw(v) for v in value])
    return renew(value)


def _renew_tuple(v: tuple) -> tuple:
    return tuple([renew(x) for x in v])


def _renew_frozen_list(v: FrozenList) -> FrozenList:
    return FrozenList([renew(x) for x in v])


def _renew_frozenset(v: frozenset) -> frozenset:
    return frozenset([renew(x) for x in v])


def _renew_frozen_set(v: FrozenSet) -> FrozenSet:
    return FrozenSet([renew(x) for x in v])


def _renew_frozen_dict(v: FrozenDict) -> FrozenDict:
    return FrozenDict._from_pairs(tuple([(renew(k), renew(x)) for k, x in v._items]))


_RENEW: dict[type, Callable[[Any], Any]] = {
    **BUILD,
    tuple: _renew_tuple,
    FrozenList: _renew_frozen_list,
    frozenset: _renew_frozenset,
    FrozenSet: _renew_frozen_set,
    FrozenDict: _renew_frozen_dict,
}


def renew(value: Any) -> Any:
    """The core's own new copy of a value the core built (a field of a
    carrier, made by the functions above): equal, sharing no object with
    it (but None, True, False and what the interpreter keeps one of per
    value). A value of any other type is a bug of the core: TypeError."""
    make = _RENEW.get(type(value))
    if make is None:
        raise TypeError(f"renew: a {type_name(value)} is not a value the core builds")
    return make(value)


_COPIERS: dict[type, Callable[[Any], Any]] = {}


def copy_carrier(obj: Any) -> Any:
    """The core's own new copy of one of its carriers (a slotted, frozen
    dataclass whose fields the core made): the same class, every field
    `renew`ed. Used for every hand-over to a receiver (engine.py), so each
    receiver holds objects no one else holds."""
    cls = type(obj)
    copier = _COPIERS.get(cls)
    if copier is None:
        copier = _COPIERS[cls] = _make_copier(cls)
    return copier(obj)


def _make_copier(cls: type) -> Callable[[Any], Any]:
    """One function per carrier class that reads each field and sets its
    renewed value on a new instance (written out field by field: about a
    quarter faster than a loop over the names)."""
    import dataclasses

    names = [f.name for f in dataclasses.fields(cls)]
    for name in names:
        if not name.isidentifier():  # pragma: no cover - dataclass field names are identifiers
            raise TypeError(f"{cls.__qualname__}.{name}")
    lines = ["def copier(src):", "    out = new(cls)"]
    for name in names:
        lines.append(f"    v = src.{name}")
        lines.append(f"    put(out, {name!r}, table[type(v)](v))")
    lines.append("    return out")
    namespace = {"new": object.__new__, "put": object.__setattr__, "table": _RENEW, "cls": cls}
    exec("\n".join(lines), namespace)  # noqa: S102 - source built above from the class's own field names
    return namespace["copier"]


_REBUILDERS: dict[type, Callable[[Any], Any]] = {}


def rebuild_carrier(obj: Any) -> Any:
    """The core's own object for a carrier a sender handed over (the
    caller has checked its class is one of the core's carrier classes
    itself): made again by the class's constructor from what its slots
    hold NOW, so every field passes the field functions above again (new
    objects, checked) and the class's own checks run again. The sender's
    object is never kept."""
    cls = type(obj)
    rebuilder = _REBUILDERS.get(cls)
    if rebuilder is None:
        rebuilder = _REBUILDERS[cls] = _make_rebuilder(cls)
    return rebuilder(obj)


def _make_rebuilder(cls: type) -> Callable[[Any], Any]:
    import dataclasses

    fields = [f for f in dataclasses.fields(cls) if f.init]
    for f in fields:
        if not f.name.isidentifier():  # pragma: no cover
            raise TypeError(f"{cls.__qualname__}.{f.name}")
    args = ", ".join(f"{f.name}=src.{f.name}" for f in fields)
    namespace = {"cls": cls}
    exec(f"def rebuilder(src):\n    return cls({args})", namespace)  # noqa: S102 - the class's own field names
    return namespace["rebuilder"]

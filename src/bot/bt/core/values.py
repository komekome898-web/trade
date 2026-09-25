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
  `float.__mul__`, `str.__getitem__`, `bytes.hex`, `complex.real`,
  `Decimal.__str__`, `Fraction`'s `_numerator` / `_denominator` slots)
  and a new object is built from what was read, so no method of the
  sender's class runs and nothing of the sender's object is kept;
* an instance of a SUBCLASS of one of those types (`IntEnum` / `StrEnum`
  members, numpy.float64, numpy.str_, a `Fraction` or `Decimal`
  subclass, ...) is read the same way, by the base type's own method,
  and built as the base type;
* a numpy bool (what numpy and pandas comparisons give) is stored as the
  `bool` it holds, read by numpy's own method;
* a number of the numeric tower -- a class whose own MRO holds
  `numbers.Integral` / `numbers.Real` / `numbers.Complex`, or numpy's
  `integer` / `floating` / `inexact` (the bases numpy registers with those
  ABCs): numpy.int64, numpy.float32, ... -> int / float / complex -- is
  converted once, NOW, and what the conversion returned is built anew as
  the built-in type itself. The kind is read from the table
  `NUMBER_BASES`, bound when the core is loaded, by identity: no ABC is
  asked, so no registration, cache or subclass hook of anyone's decides
  it (round 14, i0-r13-01), and a class merely registered with an ABC is
  not a number here;
* plain data nests at most `MAX_NESTING` containers, counted from the
  field that holds it (a bound of the core's, not the interpreter's
  recursion limit);
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

import collections.abc as _collections_abc
import numbers
import types
from decimal import Decimal
from fractions import Fraction
from typing import Any, Callable, Iterator, Mapping, Optional

import numpy as _numpy  # a declared dependency (pyproject.toml); its scalar types are bound below, at load


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
    # a new str of the same code points, made by str's own slicing and
    # concatenation (round 14): no codec runs, so the process-wide registry of
    # codec error handlers -- which any party can change with
    # codecs.register_error, and which decoding a lone surrogate consults -- is
    # never asked. A str of 0 or 1 characters may come back as the one object
    # the interpreter keeps for it.
    n = str.__len__(x)
    if n == 0:
        return ""
    if n == 1:
        return str.__getitem__(x, 0)
    return str.__add__(str.__getitem__(x, slice(0, 1)), str.__getitem__(x, slice(1, n)))


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
    "never run); a numpy bool is stored as the bool it holds; a number of the numeric tower -- a class "
    "whose own MRO holds numbers.Integral / Real / Complex or numpy's integer / floating / inexact (the "
    "table NUMBER_BASES, bound when the core is loaded and compared by identity: no ABC registry, cache or "
    "hook is asked, so a class only registered with an ABC is not a number) -- is converted once, when it "
    "is sent, and built anew as int / float / complex; types are decided by the real type's own MRO, "
    "never by what the object claims (__class__); tuple / list / dict / set / frozenset of plain data "
    "become new immutable containers and are read back as fresh copies, nested at most MAX_NESTING (100) "
    "containers deep counted from the field that holds them; anything else (a plain Enum member, a "
    "function, any other object) is refused"
)

FIELD_RULE = (
    "every field of a carrier (PATH_CARRIERS) is made, when the carrier is made, by one of values.as_text / "
    "as_float / as_int / as_flag / as_choice / freeze, which build a new object of the built-in type itself "
    "(str, float, int, bool, frozen plain data), never a subclass, an object of the sender's, or the "
    "object the sender handed over"
)


def is_a(value: Any, cls: type) -> bool:
    """Is the REAL type of `value` `cls` or a subclass of it? Unlike
    `isinstance`, it does not ask the object (an object may claim any
    class through `__class__`), and unlike `issubclass` it asks no one:
    it walks the real type's own MRO (read by `type`'s slot) and compares
    each class with `cls` by identity (`derives`), so no metaclass hook and
    no ABC registry, cache or subclass hook is consulted (round 14,
    i0-r13-01: those are process-wide state any party can change). A class
    counts as `cls` only if it derives from it; one merely registered with
    an ABC does not."""
    return derives(type(value), cls)


# ---- decisions on a type by identity only (round 12, i0-r11-01) ----------------------
# Outside a party's own call the core decides about what that party made
# only through objects the core made and no one else reaches, or static (C)
# types: a class the party wrote is never hashed, compared with `==`, looked
# up in a hash table or asked for an attribute the usual way (its metaclass's
# `__hash__` / `__eq__` / `__getattribute__` and the keys of its own dict are
# the party's code). These helpers compare classes by `is` only.

_MRO = type.__dict__["__mro__"].__get__  # a class's own MRO, read by `type`'s slot
_TYPE_FLAGS = type.__dict__["__flags__"].__get__
_TYPE_DICT = type.__dict__["__dict__"].__get__
_PROXY_ITEMS = types.MappingProxyType.items
_HEAPTYPE = 1 << 9  # Py_TPFLAGS_HEAPTYPE: a class made at run time (by a class statement or type())


def is_one_of(t: type, classes: tuple) -> bool:
    """Is class `t` one of `classes` itself (compared by identity)?"""
    for c in classes:
        if c is t:
            return True
    return False


def derives(t: type, base: type) -> bool:
    """Is `base` in the MRO of class `t` (compared by identity)?"""
    for c in _MRO(t):
        if c is base:
            return True
    return False


def is_static(t: type) -> bool:
    """A class written in C -- not made at run time -- whose metaclass is
    `type` itself: no one outside can change what its methods do (the
    built-in types, numpy's scalar types)."""
    return type(t) is type and not (_TYPE_FLAGS(t) & _HEAPTYPE)


# ---- what the core decides by: bound when the core is loaded (round 14, i0-r13-01) ------
# The core never asks process-wide state what a value is: not the ABCs (their
# registries, caches and the hooks of their subclasses can be changed by any
# party at run time, by `register` or by defining a class, and the change
# stays for the rest of the process), not `sys.modules` or a module's
# attributes. The classes it decides by are bound here, once, and compared by
# identity with the classes in a value's own MRO.


def _static_numpy(name: str) -> type:
    t = _numpy.__dict__[name]  # read once, at load
    if not is_static(t):
        raise ImportError(f"numpy.{name} is not numpy's own C class (numpy was changed before the core "
                          f"was loaded); the core decides numbers by numpy's classes and refuses to load")
    return t


_NP_BOOL = _static_numpy("bool_")
_NP_BOOL_TRUTH = _NP_BOOL.__dict__["__bool__"]  # numpy's own C slot, read once
# THE table a number's kind is decided by: the numbers ABCs as BASES (a class
# counts only if its own MRO holds one) and the bases numpy registers with them
# (numpy/_core/numerictypes.py: numbers.Integral.register(integer),
# numbers.Complex.register(inexact), numbers.Real.register(floating)), in the
# order the tower is asked: an integral kind before a real before a complex
NUMBER_BASES: tuple = (
    (numbers.Integral, int), (_static_numpy("integer"), int),
    (numbers.Real, float), (_static_numpy("floating"), float),
    (numbers.Complex, complex), (_static_numpy("inexact"), complex),
)


def number_kind(t: type) -> Any:
    """`int`, `float` or `complex` for a class of the numeric tower, else
    None: decided by class `t`'s own MRO compared by identity with
    `NUMBER_BASES` -- no ABC is asked, so no registration, cache or hook of
    anyone's decides it."""
    mro = _MRO(t)
    for base, kind in NUMBER_BASES:
        for c in mro:
            if c is base:
                return kind
    return None


# the mapping classes: dict, the read-only proxy (which collections.abc
# registers with Mapping when it is loaded) and whatever derives from Mapping
_MAPPING_BASES: tuple = (dict, types.MappingProxyType, _collections_abc.Mapping)


def is_mapping(t: type) -> bool:
    """Is class `t` a mapping (by its own MRO, compared by identity)?"""
    return any(derives(t, base) for base in _MAPPING_BASES)


# An int as text whatever the interpreter's int <-> str digit limit is (a
# process-wide setting, 4300 digits by default, 640 at the least): an int of at
# most 2000 bits (603 digits) is written out, a longer one by its size.
INT_TEXT_BITS = 2000


def int_text(n: int) -> str:
    """Int `n` (an int itself) as text, never failing on its length."""
    bits = int.bit_length(n)
    if bits <= INT_TEXT_BITS:
        return int.__repr__(n)
    return f"{'a negative' if int.__lt__(n, 0) else 'an'} int of {bits} bits"


def value_text(value: Any) -> str:
    """A value a sender handed over, as text for an error message, made
    without running any of its code and never failing: a str, int, float,
    bool or None itself by its own type's method (a str cut at 300
    characters), anything else by its real type's name."""
    t = type(value)
    if t is str:
        text = str.__repr__(value)
        return text if len(text) <= _TEXT_LIMIT else text[:_TEXT_LIMIT] + "..."
    if value is None or t is bool:
        return "None" if value is None else ("True" if value else "False")
    if t is int:
        return int_text(value)
    if t is float:
        return float.__repr__(value)
    return f"<a {type_name(value)}>"


# How deep plain data may nest, counted in containers from the field that
# holds it (a bound of the core's, the same whatever the interpreter's
# recursion limit and the stack depth of the call: round 14). The core's
# deepest walk (`renew`) takes 3 frames a level and a run adds about 20, so
# 100 levels stay within half of the interpreter's default limit (1000);
# the interpreter's own hash / == of nested tuples recurse as deep.
MAX_NESTING = 100


class IdTable:
    """A lookup table keyed by classes the core names, searched by the
    identity of a class: its keys are the ids (ints the core made), so a
    lookup never hashes or compares the class searched for."""

    __slots__ = ("_by_id",)

    def __init__(self, pairs) -> None:
        object.__setattr__(self, "_by_id", {id(k): (k, v) for k, v in pairs})

    def get(self, t: type, default: Any = None) -> Any:
        got = self._by_id.get(id(t))
        return got[1] if got is not None and got[0] is t else default


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
    """(module, qualified name) of class `t`, read without running any code
    of the class, its metaclass, its dict's keys or what its body set
    `__module__` to (round 12, i0-r11-01): the name from `type`'s own slot;
    the module of a C class from its C name (`type`'s descriptor parses it:
    no lookup), and of a class made at run time by WALKING the class's own
    dict -- the key that is the str '__module__' itself -- never by looking
    it up (a lookup compares the keys the class's author put there, with
    their own `__eq__`). Both made str by `str`'s own method. A module that
    is not a str reads as None; a name that is not one as "?"."""
    if _TYPE_FLAGS(t) & _HEAPTYPE:
        module = None
        for key, value in _PROXY_ITEMS(_TYPE_DICT(t)):
            if type(key) is str and key == "__module__":
                module = _own_text(value)
                break
    else:
        try:
            module = _own_text(_TYPE_MODULE(t))
        except AttributeError:  # pragma: no cover - a C class always has a name
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
        return int_text(arg)
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


def _base_of(t: type) -> Any:
    """The base of `_BASES` a class derives from, or None -- read from the
    class's own MRO and compared by identity, so no metaclass hook (its
    `__eq__`) or ABC hook (`Fraction` is an ABC: `issubclass` would ask its
    subclasses' hooks) runs (round 10, round 12)."""
    mro = _MRO(t)
    for base in _BASES:
        for c in mro:
            if c is base:
                return base
    return None


_BUILDER = IdTable(BUILD.items())  # BUILD searched by identity (round 12)


def _plain_scalar(value: Any, where: str) -> Any:
    """The scalar rule (module docstring): a NEW built-in scalar, or
    `_NOT_PLAIN`. A sender's failing conversion, or a broken Fraction,
    raises ValueError."""
    t = type(value)
    build = _BUILDER.get(t)
    if build is not None:
        return build(value)
    base = _base_of(t)
    if base is not None:
        return BUILD[base](value)
    if derives(t, _NP_BOOL):
        return _NP_BOOL_TRUTH(value)
    # the numeric tower, decided by the class's own MRO (`number_kind`), and
    # converted inside the sender's own call (a field made when its carrier is
    # made); after a party's call the core takes values by `settle` instead,
    # which runs no code of a Python class
    kind = number_kind(t)
    if kind is not None:
        return _now(kind, value, where)
    return _NOT_PLAIN


class Unsettled(ValueError):
    """A value that cannot be read without running code of the one who
    handed it over (`settle`)."""


def settle(value: Any) -> Any:
    """`value` as plain data of the built-in types THEMSELVES, made without
    running any code of the one who handed it over (round 10, i0-r9-02;
    round 12, i0-r11-01): THE one way the core takes a value after the call
    that made it returned. Its type is decided by identity only (`is` on the
    class and its MRO: the class is never hashed or compared, so no
    metaclass hook runs); a built-in scalar or a subclass of one is built
    anew as the base type by the base type's own method (the subclass's
    code -- its `__repr__`, `__eq__`, `__hash__` -- never runs, and nothing
    later can run it: what comes out holds none of the sender's objects); a
    numpy bool as the bool it holds; a number of a STATIC (C) class of the
    numeric tower (numpy's) is converted by that class's C code, which no
    one outside can change; a container (tuple, list, dict, set, frozenset,
    a subclass of one, or the core's FrozenList / FrozenDict / FrozenSet) is
    read by the base type's own methods and made anew of settled values.
    Anything else -- a number whose class was written in Python (its
    `__int__` / `__float__` / `__index__` is the sender's code), any other
    object -- raises `Unsettled`, a ValueError, whose text names only the
    value's type. The core applies this to what it takes AFTER a party's
    call returned: the outbox (engine.py `_take_message`), a plug-in's
    number (`take_int` / `take_float`), a carrier it makes again
    (`rebuild_carrier`)."""
    return _settle(value, set())


def _too_deep(where: str) -> str:
    return (f"{where} nests deeper than {MAX_NESTING} containers (counted from the field that holds it); "
            f"plain data is refused beyond that depth")


_CONTAINERS = (tuple, list, set, frozenset, dict)


def _settle(value: Any, path: set[int]) -> Any:
    t = type(value)
    build = _BUILDER.get(t)
    if build is not None:
        return build(value)
    container = None
    for c in _CONTAINERS:
        if derives(t, c):
            container = c
            break
    if container is not None or t is FrozenDict:
        key = id(value)
        if key in path:
            raise Unsettled(f"a {type_name(value)} that holds itself (a cycle) is not plain data")
        if len(path) >= MAX_NESTING:
            raise Unsettled(_too_deep(f"a {type_name(value)}"))
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
    if derives(t, _NP_BOOL):
        return _NP_BOOL_TRUTH(value)
    if is_static(t):
        # a C class of the numeric tower (numpy's): its kind from the table
        # bound at load (`number_kind`), its conversion its own C code
        kind = number_kind(t)
        if kind is not None:
            try:
                return _now(kind, value, "value")
            except ValueError as exc:
                raise Unsettled(str(exc)) from None
    raise Unsettled(
        f"a {type_name(value)} cannot be read without running its own code (or is not plain data)"
    )


def take_int(value: Any, where: str) -> int:
    """A plug-in's integer answer, taken after its call returned (engine.py
    `_check_delay`): `settle`, then an int itself (never a bool)."""
    got = _taken(value, where)
    if type(got) is not int:
        raise ValueError(f"{where} must be an int, got {type_name(value)}")
    return got


def take_float(value: Any, where: str) -> float:
    """A plug-in's number answer, taken after its call returned (the
    fee): `settle`, then a float itself (an int or a Fraction converted by
    the core's own types; never a bool)."""
    got = _taken(value, where)
    t = type(got)
    if t is float:
        return got
    if t is int or t is Fraction:
        return _now(float, got, where)
    raise ValueError(f"{where} must be a number, got {type_name(value)}")


def take_items(value: Any) -> tuple:
    """A plug-in's answer that is a sequence (the protocols' `Sequence`),
    taken after its call returned: None is empty; a list or a tuple (or a
    subclass of one) is read by the base type's own iterator into a new
    tuple -- its truth, length and iteration are never asked of it, so no
    code of its class runs; anything else raises `Unsettled`."""
    if value is None:
        return ()
    t = type(value)
    if derives(t, list):
        return tuple(list.__iter__(value))
    if derives(t, tuple):
        return tuple(tuple.__iter__(value))
    raise Unsettled(f"a {type_name(value)} is not a list or a tuple")


def _taken(value: Any, where: str) -> Any:
    try:
        return settle(value)
    except Unsettled as exc:
        raise ValueError(f"{where}: {exc}; convert it to the built-in type inside the call that returns it "
                         f"(the core takes answers after the call returned and runs none of their code)") from None


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

    def __eq__(self, other: Any) -> Any:
        # decided without asking an ABC (round 14): the inherited Mapping.__eq__
        # asks isinstance(other, Mapping), whose registry any party can change,
        # and the core compares keys whenever their hashes collide while it
        # builds a dict or a set (a FrozenDict hashes as the frozenset of its
        # items). Another FrozenDict or a class deriving from a mapping base
        # (is_mapping: the class's own MRO) compares by its items; anything
        # else is not a mapping.
        t = type(other)
        if t is FrozenDict:
            return dict(_FD_ITEMS(self)) == dict(_FD_ITEMS(other))
        if is_mapping(t):
            return dict(_FD_ITEMS(self)) == dict(other.items())
        return NotImplemented

    def __hash__(self) -> int:
        h = self._hash
        if h is None:
            h = hash(frozenset(self._items))
            object.__setattr__(self, "_hash", h)
        return h

    def __repr__(self) -> str:
        return f"FrozenDict({dict(self._items)!r})"


_FD_ITEMS = FrozenDict.__dict__["_items"].__get__


_FREEZE_TYPES = (tuple, list, dict, set, frozenset, FrozenList, FrozenDict, FrozenSet)


def freeze(value: Any, where: str = "value", outer: int = 0) -> Any:
    """An equal, deeply immutable form of plain data; `ValueError` for
    anything that is not plain data (module docstring). `outer` is the
    number of containers around `value` in the field that holds it (the
    nesting bound `MAX_NESTING` counts from the field)."""
    return _freeze(value, where, set(), outer)


def _key_text(k: Any) -> str:
    return value_text(k)  # a sender's key, named without running its code (round 14)


def _freeze(value: Any, where: str, path: set[int], outer: int = 0) -> Any:
    t = type(value)
    if not is_one_of(t, _FREEZE_TYPES):
        return scalar(value, where)
    key = id(value)
    if key in path:
        raise ValueError(f"{where} holds itself (a cycle); plain data has no cycles")
    if outer + len(path) >= MAX_NESTING:
        raise ValueError(_too_deep(where))
    path.add(key)
    try:
        if t in (tuple, FrozenList):
            items = tuple([_freeze(v, f"{where}[{i}]", path, outer) for i, v in enumerate(tuple.__iter__(value))])
            return FrozenList(items) if t is FrozenList else items
        if t is list:
            return FrozenList([_freeze(v, f"{where}[{i}]", path, outer) for i, v in enumerate(list.__iter__(value))])
        if t in (dict, FrozenDict):
            # read by the real type's own methods (a dict's, or the core's
            # FrozenDict's pairs), then built anew
            src = dict.items(value) if t is dict else _frozen_pairs(value, where)
            frozen: dict = {}
            for k, v in src:
                fk = _freeze(k, f"{where} key {_key_text(k)}", path, outer)
                frozen[fk] = _freeze(v, f"{where}[{_key_text(k)}]", path, outer)
            return FrozenDict._from_pairs(tuple(frozen.items()))
        each = set.__iter__(value) if t is set else frozenset.__iter__(value)
        items = frozenset([_freeze(v, f"{where} element", path, outer) for v in each])
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
    hold NOW, each value taken by `settle` first (round 12: what a sender
    put in a slot after the carrier was made is read without running its
    code; a value `settle` refuses raises `Unsettled`, a ValueError), so
    every field passes the field functions above again (new objects,
    checked) and the class's own checks run again. The sender's object is
    never kept."""
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
    args = ", ".join(f"{f.name}=take(src.{f.name})" for f in fields)
    namespace = {"cls": cls, "take": _as_taken}
    exec(f"def rebuilder(src):\n    return cls({args})", namespace)  # noqa: S102 - the class's own field names
    return namespace["rebuilder"]


def _as_taken(value: Any) -> Any:
    """A slot's value as the constructor may be given it after the
    sender's call returned (round 12): a built-in scalar itself as it is
    (the field functions build it anew by its own type), anything else
    settled first -- so a value the sender put in a slot behind the class's
    back runs none of its code when the carrier is made again."""
    return value if _BUILDER.get(type(value)) is not None else settle(value)

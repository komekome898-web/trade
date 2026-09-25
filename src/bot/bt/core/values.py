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
  `float.__mul__`, `str.__getitem__`, `bytes.hex`, `complex.real`, a
  Decimal written by a decimal context of the core's own, `Fraction`'s
  `_numerator` / `_denominator` slots) and a new object is built from what
  was read, so no method of the sender's class runs and nothing of the
  sender's object is kept;
* a Fraction or a Decimal is built as the core's own subclass,
  `PlainFraction` / `PlainDecimal` (slotted), whose `==`, `!=` and hash are
  the core's (round 15, i0-r14-01): the library's `Fraction.__eq__` and the
  C decimal's comparison ask the numbers ABCs about the other operand (and
  a Decimal compared with a float writes a flag into the thread's decimal
  context), so the equality of a value -- asked whenever two keys of a set
  or a dict the core builds share a hash, and by every receiver's own dict
  or set -- would be decided by process-wide state any party can change.
  The core's equality compares the exact values (`_number_equal`), its
  hash is the library's (the numeric hash every equal number shares);
  arithmetic on them is the library's;
* an instance of a SUBCLASS of one of those types (`IntEnum` / `StrEnum`
  members, numpy.float64, numpy.str_, a `Fraction` or `Decimal`
  subclass, ...) is read the same way, by the base type's own method,
  and built as the base type (a Fraction or Decimal as the core's own);
* a numpy bool (what numpy and pandas comparisons give) is stored as the
  `bool` it holds, read by numpy's own method;
* a number of the numeric tower -- a class whose own MRO holds
  `numbers.Integral` / `numbers.Real` / `numbers.Complex`, or numpy's
  `integer` / `floating` / `inexact` (the bases numpy registers with those
  ABCs): numpy.int64, numpy.float32, ... -> int / float / complex -- is
  converted once, NOW, EXACTLY (round 15, i0-r14-03/04): numpy's
  `longdouble` / `clongdouble` hold digits a float / complex may not, and a
  value the conversion would round is refused; numpy's `timedelta64` /
  `datetime64` are a count in a UNIT of their own (a timedelta64 derives
  from numpy's signedinteger, and `int()` of it is its count in that unit)
  and are not numbers here. The kind is read from the table
  `NUMBER_BASES`, bound when the core is loaded, by identity: no ABC is
  asked, so no registration, cache or subclass hook of anyone's decides
  it (round 14, i0-r13-01), and a class merely registered with an ABC is
  not a number here;
* plain data nests at most `MAX_NESTING` containers, counted from the
  field that holds it (a bound of the core's). The core's walks over it
  are iterative (round 15, i0-r14-05): they take the same few frames of
  the interpreter's stack whatever the nesting;
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
import dataclasses as _dataclasses  # at load: the core imports nothing at run time (round 15, i0-r14-02)
import decimal as _decimal
import math as _math
import numbers
import sys as _sys
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


# ---- a decimal context of the core's own (round 14 / round 15) ------------------------
# The core never reads or writes the thread's decimal context (process state
# any party can change: its precision, rounding, traps and capitals would
# decide results, and its flags are written by comparisons). Every decimal
# operation of the core runs in a context made for that call from these
# constants (read once, here): exact (the largest precision), every error
# trapped.
_CONTEXT = _decimal.Context
_DECIMAL_SETTINGS = (_decimal.MAX_PREC, _decimal.ROUND_HALF_EVEN, _decimal.MIN_EMIN, _decimal.MAX_EMAX)
_DECIMAL_TRAPS = (_decimal.InvalidOperation, _decimal.DivisionByZero, _decimal.Overflow)
DECIMAL_ERRORS = (_decimal.DecimalException,)


def exact_context() -> "_decimal.Context":
    """A new decimal context of the core's own: exact, every error trapped,
    capitals on. Never the thread's."""
    prec, rounding, emin, emax = _DECIMAL_SETTINGS
    return _CONTEXT(prec=prec, rounding=rounding, Emin=emin, Emax=emax, capitals=1, clamp=0, flags=[],
                    traps=list(_DECIMAL_TRAPS))


_DECIMAL_NEW = Decimal.__new__
_DEC_IS_NAN = Decimal.is_nan
_DEC_IS_SNAN = Decimal.is_snan
_DEC_IS_INFINITE = Decimal.is_infinite
_DEC_IS_SIGNED = Decimal.is_signed
_DEC_HASH = Decimal.__hash__


def _new_decimal(x: Decimal) -> "PlainDecimal":
    """A new PlainDecimal of the value `x` holds: written by a context of the
    core's own (its text is exact and never depends on the thread's context)
    and read back exactly from that text."""
    ctx = exact_context()
    return _DECIMAL_NEW(PlainDecimal, ctx.to_sci_string(x), ctx)


_NUMERATOR = Fraction.__dict__["_numerator"].__get__
_DENOMINATOR = Fraction.__dict__["_denominator"].__get__
_SET_NUMERATOR = Fraction.__dict__["_numerator"].__set__
_SET_DENOMINATOR = Fraction.__dict__["_denominator"].__set__
_GCD = _math.gcd
_OBJECT_NEW = object.__new__


def fraction_parts(x: Fraction) -> tuple[int, int]:
    """(numerator, denominator) of a Fraction, read by the class's own slots;
    ValueError for a Fraction whose slots were broken."""
    try:
        n, d = _NUMERATOR(x), _DENOMINATOR(x)
    except AttributeError:
        raise ValueError("a Fraction without its numerator or denominator") from None
    tn, td = type(n), type(d)
    if tn is bool or td is bool or not (derives(tn, int) and derives(td, int)):
        raise ValueError(f"a Fraction whose parts are not ints ({type_name(n)}, {type_name(d)})")
    n, d = _new_int(n), _new_int(d)
    if d == 0:
        raise ValueError("a Fraction with a zero denominator")
    return n, d


def _make_fraction(n: int, d: int) -> "PlainFraction":
    """A new PlainFraction n/d (ints, d != 0), in lowest terms, made by the
    core itself (no library constructor runs)."""
    if d < 0:
        n, d = -n, -d
    g = _GCD(n, d)
    if g != 1:
        n, d = n // g, d // g
    out = _OBJECT_NEW(PlainFraction)
    _SET_NUMERATOR(out, n)
    _SET_DENOMINATOR(out, d)
    return out


def _new_fraction(x: Fraction) -> "PlainFraction":
    n, d = fraction_parts(x)
    return _make_fraction(n, d)


# ---- the core's equality of numbers (round 15, i0-r14-01) -------------------------------

_Q, _INF, _NAN, _CPLX, _DEC = "q", "inf", "nan", "c", "d"


def _number_parts(x: Any) -> Any:
    """How the core reads a number to compare it, by the real type's own MRO
    (compared by identity) and the base type's own methods: (_Q, n, d) an
    exact rational, (_INF, sign), (_NAN,), (_CPLX, re, im) a complex with a
    non-zero imaginary part (floats), (_DEC, the Decimal); None for
    anything else (not a number the core reads by value)."""
    t = type(x)
    if derives(t, Decimal):
        return (_DEC, x)
    if derives(t, Fraction):
        try:
            n, d = fraction_parts(x)
        except ValueError:
            return None
        return (_Q, n, d)
    if derives(t, int):  # bool too: True == 1
        return (_Q, _new_int(x), 1)
    if derives(t, float):
        return _float_parts(_new_float(x))
    if derives(t, complex):
        re, im = _new_float(_REAL(x)), _new_float(_IMAG(x))
        if float.__eq__(im, 0.0):
            return _float_parts(re)
        return (_CPLX, re, im)
    if is_static(t) and number_kind(t) is not None and not derives(t, _NP_BOOL):
        # a number of a static (C) class (numpy's): converted exactly by its own
        # C code, then read as the built-in number (a value that does not convert
        # exactly is not read)
        try:
            return _number_parts(_now(number_kind(t), x, "value"))
        except ValueError:
            return None
    return None


def _float_parts(f: float) -> tuple:
    if float.__ne__(f, f):
        return (_NAN,)
    if float.__eq__(f, _INFINITY) or float.__eq__(f, -_INFINITY):
        return (_INF, 1 if float.__gt__(f, 0.0) else -1)
    n, d = float.as_integer_ratio(f)
    return (_Q, n, d)


_INFINITY = float("inf")


def _decimal_equal(dec: Decimal, other: tuple) -> bool:
    """A Decimal against another number's parts, exactly, in a context of the
    core's own (no huge int is made: the Decimal keeps its exponent)."""
    if _DEC_IS_NAN(dec):
        return False
    kind = other[0]
    if kind == _NAN or kind == _CPLX:
        return False
    if kind == _INF:
        return _DEC_IS_INFINITE(dec) and (_DEC_IS_SIGNED(dec) == (other[1] < 0))
    ctx = exact_context()
    try:
        if kind == _DEC:
            o = other[1]
            if _DEC_IS_NAN(o):
                return False
            return ctx.compare(dec, o).is_zero()
        if _DEC_IS_INFINITE(dec):
            return False
        n, d = other[1], other[2]
        return ctx.compare(ctx.multiply(dec, ctx.create_decimal(d)), ctx.create_decimal(n)).is_zero()
    except DECIMAL_ERRORS:  # pragma: no cover - exact context: no condition on finite operands
        return False


def _number_equal(a: Any, b: Any) -> Any:
    """Is number `a` (the core's PlainFraction / PlainDecimal) equal to `b`?
    The exact values are compared -- Python's own numeric equality, decided
    by the core without asking any ABC or reading the thread's decimal
    context; NotImplemented when `b` is not a number the core reads (int,
    float, complex, Fraction, Decimal, or a subclass of one). A NaN is
    equal to nothing; a signaling NaN too (Python raises or not by the
    thread's traps; the core answers False)."""
    pb = _number_parts(b)
    if pb is None:
        return NotImplemented
    pa = _number_parts(a)
    if pa is None:  # pragma: no cover - a is the core's own number
        return NotImplemented
    if pa[0] == _DEC:
        return _decimal_equal(pa[1], pb)
    if pb[0] == _DEC:
        return _decimal_equal(pb[1], pa)
    if pa[0] == _NAN or pb[0] == _NAN or pa[0] != pb[0]:
        return False
    if pa[0] == _Q:
        return pa[1] * pb[2] == pb[1] * pa[2]
    if pa[0] == _INF:
        return pa[1] == pb[1]
    return float.__eq__(pa[1], pb[1]) and float.__eq__(pa[2], pb[2])


def _not_equal(a: Any, b: Any) -> Any:
    eq = _number_equal(a, b)
    return eq if eq is NotImplemented else not eq


_HASH_MODULUS = _sys.hash_info.modulus
_HASH_INF = _sys.hash_info.inf


def _fraction_hash(x: "PlainFraction") -> int:
    """The numeric hash of n/d (the one every equal int, float, Decimal and
    Fraction shares), computed by the core from the Fraction's own slots."""
    n, d = _NUMERATOR(x), _DENOMINATOR(x)
    try:
        dinv = pow(d, -1, _HASH_MODULUS)
    except ValueError:  # d is a multiple of the modulus: no inverse
        h = _HASH_INF
    else:
        h = int.__hash__(int.__hash__(n if n >= 0 else -n) * dinv)
    h = h if n >= 0 else -h
    return -2 if h == -1 else h


class PlainFraction(Fraction):
    """A Fraction the core built (round 15): the library's Fraction, whose
    ==, != and hash are the core's (`_number_equal`, the numeric hash), so
    comparing it asks no ABC. Slotted; arithmetic gives library Fractions."""

    __slots__ = ()

    __eq__ = _number_equal
    __ne__ = _not_equal
    __hash__ = _fraction_hash


class PlainDecimal(Decimal):
    """A Decimal the core built (round 15): the library's Decimal, whose ==
    and != are the core's (`_number_equal`: exact, in a context of the
    core's own; never the thread's context), whose hash is Decimal's (C,
    computed in a context of its own) and whose str / repr / f"{}" are
    written by a context of the core's own (the library's read the
    thread's capitals). Slotted; arithmetic, and formatting with a spec,
    are the library's (they use the thread's context by their own
    definition, in the reader's call)."""

    __slots__ = ()

    __eq__ = _number_equal
    __ne__ = _not_equal
    __hash__ = _DEC_HASH

    def __str__(self) -> str:
        # written by a context of the core's own: the library's str / repr read
        # the thread's context (its capitals), which any party can change
        return exact_context().to_sci_string(self)

    def __repr__(self) -> str:
        return f"PlainDecimal('{exact_context().to_sci_string(self)}')"

    def __format__(self, spec: str) -> str:
        # an empty spec (f"{d}") is its str; a spec that asks for rounding or
        # a layout is the library's formatting, which by its own definition
        # uses the thread's context -- the reader's choice, in its own call
        if type(spec) is str and str.__len__(spec) == 0:
            return exact_context().to_sci_string(self)
        return Decimal.__format__(self, spec)


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
    PlainDecimal: _new_decimal,
    PlainFraction: _new_fraction,
}
# the bases a subclass is read as (bool cannot be subclassed; checked in
# this order, after the exact type)
_BASES: tuple[type, ...] = (str, bytes, float, int, complex, Decimal, Fraction)

PLAIN_DATA_RULE = (
    "every value is built anew by the core (nothing a sender hands over is kept; None, True and False "
    "are the one objects kept); accepted scalars are the table BUILD: None, bool, int, float, complex, "
    "str, bytes, Decimal, Fraction, each read by that type's own method or slot and built as a new "
    "object; a Fraction or Decimal is built as the core's own subclass PlainFraction / PlainDecimal, whose "
    "== and hash are the core's (the exact values compared, the numeric hash), so no ABC and no thread's "
    "decimal context decides an equality (round 15); an instance of a subclass of one of them (IntEnum and "
    "StrEnum members, numpy's, a Fraction or Decimal subclass) is read by the base type and built as the "
    "base type (the subclass's methods never run); a numpy bool is stored as the bool it holds; a number of "
    "the numeric tower -- a class whose own MRO holds numbers.Integral / Real / Complex or numpy's integer / "
    "floating / inexact (the table NUMBER_BASES, bound when the core is loaded and compared by identity: no "
    "ABC registry, cache or hook is asked, so a class only registered with an ABC is not a number) -- is "
    "converted once, when it is sent, exactly, and built anew as int / float / complex: a numpy longdouble "
    "or clongdouble whose value the float / complex does not hold exactly is refused, and numpy's "
    "timedelta64 / datetime64 (a count in a unit of their own) are not numbers (round 15); types are "
    "decided by the real type's own MRO, never by what the object claims (__class__); tuple / list / dict "
    "/ set / frozenset of plain data become new immutable containers and are read back as fresh copies, "
    "nested at most MAX_NESTING (100) containers deep counted from the field that holds them; two keys of a "
    "dict or two elements of a set that are distinct in the sender's container but equal as plain data are "
    "refused (never merged), and so is a key or an element that has no hash (a signaling-NaN Decimal, or "
    "what holds one; round 16); anything else (a plain Enum member, a function, any other object) is refused"
)

FIELD_RULE = (
    "every field of a carrier (PATH_CARRIERS) is made, when the carrier is made, by one of values.as_text / "
    "as_float / as_int / as_flag / as_choice / freeze, which build a new object of the built-in type itself "
    "(str, float, int, bool, frozen plain data), never a subclass, an object of the sender's, or the "
    "object the sender handed over; a float field is the float nearest the value of any real number it "
    "takes, whatever its class (round 16)"
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
# numpy's counts in a unit of their own (round 15, i0-r14-04): a timedelta64
# derives from numpy's signedinteger and int() of it is its count in ITS unit
# (picoseconds, years ...); neither it nor a datetime64 is a number here
UNIT_CLASSES: tuple = (_static_numpy("timedelta64"), _static_numpy("datetime64"))
# numpy's classes that may hold more than the built-in type they convert to
# (round 15, i0-r14-03): the conversion is checked to be exact, by the
# class's own C method `as_integer_ratio` (a longdouble; the parts of a
# clongdouble) against the float's
_NP_LONGDOUBLE = _static_numpy("longdouble")
_NP_CLONGDOUBLE = _static_numpy("clongdouble")
_LD_RATIO = _NP_LONGDOUBLE.__dict__["as_integer_ratio"]
_NP_REAL = _static_numpy("generic").__dict__["real"].__get__
_NP_IMAG = _static_numpy("generic").__dict__["imag"].__get__


def number_kind(t: type) -> Any:
    """`int`, `float` or `complex` for a class of the numeric tower, else
    None: decided by class `t`'s own MRO compared by identity with
    `NUMBER_BASES` -- no ABC is asked, so no registration, cache or hook of
    anyone's decides it. numpy's timedelta64 / datetime64 are not numbers."""
    mro = _MRO(t)
    for c in mro:
        if c is UNIT_CLASSES[0] or c is UNIT_CLASSES[1]:
            return None
    for base, kind in NUMBER_BASES:
        for c in mro:
            if c is base:
                return kind
    return None


def _same_real(wide: Any, f: float) -> bool:
    """Does float `f` hold exactly the value of numpy longdouble `wide`?"""
    try:
        ratio = _LD_RATIO(wide)
    except (OverflowError, ValueError):  # inf or nan: float() gave the same inf or nan
        return float.__ne__(f, f) or float.__eq__(f, _INFINITY) or float.__eq__(f, -_INFINITY)
    if float.__ne__(f, f) or float.__eq__(f, _INFINITY) or float.__eq__(f, -_INFINITY):
        return False  # a finite longdouble beyond the float's range
    n, d = ratio
    return float.as_integer_ratio(f) == (int(n), int(d))


def _exactly_converted(value: Any, out: Any) -> bool:
    """Is `out` (what int() / float() / complex() gave for numpy scalar
    `value`) the same value? Only numpy's longdouble and clongdouble can
    hold more than the built-in type; every other class converts exactly."""
    t = type(value)
    if derives(t, _NP_LONGDOUBLE):
        return _same_real(value, out)
    if derives(t, _NP_CLONGDOUBLE):
        return _same_real(_NP_REAL(value), _REAL(out)) and _same_real(_NP_IMAG(value), _IMAG(out))
    if derives(t, int) and derives(type(out), float):
        # an int made a float (round 16, i0-r15-04): exact only when the float
        # holds that int (float == int compares the exact values, in C)
        return float.__eq__(_new_float(out), _new_int(value)) is True
    return True


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
# holds it: a bound of the core's. The core's own walks over plain data are
# iterative (round 15, i0-r14-05) and take no frame per level; the bound keeps
# what the INTERPRETER itself does over one value -- comparing two distinct
# nested values of equal hash in one set or dict, one level of its recursion
# limit per tuple / frozenset container (measured round 15: two distinct
# 98-level tuples need 106 frames of headroom; from a FrozenDict down the
# core's iterative `_plain_equal` takes none per level, round 16) -- well
# inside its default limit (1000). The value 100 was
# set in round 14 from the recursive walks of then (3 frames a level, about 20
# for a run: half of 1000) and kept.
MAX_NESTING = 100
# The frames of the interpreter's recursion limit an entry that takes or hands
# out plain data needs below its caller, whatever the nesting of the value
# (round 15, measured over freeze, settle, renew, thaw, and place_order /
# order() / extra_dict() from inside on_event: at most 22, for place_order
# from inside on_event; 30 leaves a margin).
# With less headroom than this a call may fail with RecursionError; with at
# least this much, whether a value is taken never depends on the stack depth
# of the call -- except for the interpreter's comparison above, which needs
# one more frame per tuple / frozenset level of the values it compares.
CALL_FRAMES = 30


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
    """Convert a foreign number once, now, EXACTLY, and build what the
    conversion returned anew as the built-in type itself; an error in the
    sender's conversion, or a value the conversion would round (numpy's
    longdouble / clongdouble), is a ValueError of this module."""
    try:
        out = convert(value)
    except Exception as exc:  # the sender's own conversion code, or a number too large
        article = "an" if convert is int else "a"
        raise ValueError(
            f"{where} must be a number {article} {convert.__name__} can hold, got a "
            f"{type_name(value)} ({exception_text(exc)})"  # no code of the sender's exception runs
        ) from None
    if not derives(type(out), convert):  # pragma: no cover - int() / float() / complex() check it
        raise ValueError(f"{where}: {convert.__name__}() gave a {type_name(out)}")
    if not _exactly_converted(value, out):
        raise ValueError(f"{where} holds a {type_name(value)} whose value a {convert.__name__} cannot hold "
                         f"exactly; the core does not round (convert it yourself)")
    return BUILD[convert](out)


def fraction_float(x: Fraction) -> float:
    """A Fraction as the nearest float, by int division (correctly rounded;
    no library code); ValueError when it is beyond a float's range."""
    n, d = fraction_parts(x)
    try:
        return int.__truediv__(n, d)
    except OverflowError:
        raise ValueError("a Fraction beyond a float's range") from None


def decimal_float(x: Decimal) -> float:
    """A Decimal as the nearest float (correctly rounded, from its text
    written by a context of the core's own); inf, nan and the sign of a
    zero kept; ValueError for a signaling NaN and for a finite value beyond
    a float's range (it is not infinite: never made inf, round 16)."""
    try:
        f = float(exact_context().to_sci_string(x))
    except ValueError:
        raise ValueError("a signaling NaN is not a float") from None
    if _is_inf(f) and not _DEC_IS_INFINITE(x):
        raise ValueError("a Decimal beyond a float's range")
    return f


def _is_inf(f: float) -> bool:
    return float.__eq__(f, _INFINITY) or float.__eq__(f, -_INFINITY)


_INF_TEXTS = ("inf", "infinity")
_INT_FLOAT = int.__float__


# ---- the float FIELD: the nearest float of the value (round 16, i0-r15-04) ---------------
# A field declared float (a price, a size, a fee) takes the float NEAREST the
# exact value of every real number it accepts, whatever its class: an int, a
# float, a Fraction, a numpy integer or floating number (a longdouble too), and
# where text is taken a Decimal or a numeric str -- correctly rounded (half to
# even), by int division, C conversions and the correctly rounded text reader,
# never by the floating-point state of the process. inf, nan and the sign of a
# zero are kept; a FINITE value beyond a float's range is refused (never made
# inf). One value is never rounded by one class and refused by another. (Plain
# data -- `freeze`, `settle` -- keeps values exactly or refuses them: `_now`.)

def _beyond(where: str, value: Any) -> ValueError:
    """The one refusal of a finite value beyond a float's range, whatever
    its class."""
    return ValueError(f"{where} must be a number a float can hold, got a {type_name(value)} beyond a "
                      f"float's range")


def _nearest_of(got: Any, value: Any, where: str, numbers_only: bool) -> float:
    """The float field's value of `got`, what the scalar rule built of
    `value`."""
    t = type(got)
    if t is float:
        return got
    if t is int:
        try:
            return _INT_FLOAT(got)  # correctly rounded, in C
        except OverflowError:
            raise _beyond(where, value) from None
    if t is PlainFraction:
        try:
            return fraction_float(got)
        except ValueError:
            raise _beyond(where, value) from None
    if t is PlainDecimal and not numbers_only:
        if _DEC_IS_SNAN(got):
            raise ValueError(f"{where}: a signaling NaN is not a float")
        try:
            return decimal_float(got)
        except ValueError:
            raise _beyond(where, value) from None
    if t is str and not numbers_only:
        try:
            f = float(got)  # correctly rounded (the interpreter's text reader)
        except ValueError:
            raise ValueError(f"{where} must be a number, got the text {got!r}") from None
        if _is_inf(f) and str.lower(str.lstrip(str.strip(got), "+-")) not in _INF_TEXTS:
            raise _beyond(where, value)
        return f
    raise ValueError(f"{where} must be a number, got {type_name(value)}")


def _longdouble_nearest(value: Any, where: str) -> float:
    """A numpy longdouble's nearest float: the float itself when it holds
    the value exactly (inf, nan, the sign of a zero), else its exact value
    (the class's own C `as_integer_ratio`) divided as ints."""
    try:
        return _now(float, value, where)
    except ValueError:
        pass
    try:
        n, d = _LD_RATIO(value)
    except (OverflowError, ValueError):  # pragma: no cover - a finite longdouble has a ratio
        raise ValueError(f"{where} holds a {type_name(value)} that cannot be read") from None
    try:
        return int.__truediv__(_new_int(n), _new_int(d))
    except OverflowError:
        raise _beyond(where, value) from None


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
    return _walk(value, "value", 0, _settle_open, _settle_leaf, _settle_fail)


def _too_deep(where: str) -> str:
    return (f"{where} nests deeper than {MAX_NESTING} containers (counted from the field that holds it); "
            f"plain data is refused beyond that depth")


# ---- the walks over plain data (round 15, i0-r14-05) ------------------------------------
# One iterative walk rebuilds nested plain data for freeze, settle, renew and
# thaw: an explicit stack instead of recursion, so the frames of the
# interpreter's stack a walk takes are the same few whatever the nesting, and
# whether a value is taken never depends on how deep the caller's stack is.
# What is left of the interpreter's own recursion: comparing two DISTINCT
# nested values whose hashes are equal, when both are keys of one dict or
# elements of one set (the interpreter compares them, one level of its
# recursion limit a container) -- caught at the walk and refused with the
# entry's own error, never RecursionError.

_CYCLE, _DEEP, _RECURSION = "cycle", "deep", "recursion"


def _walk(root: Any, where: str, outer: int, open_node: Callable, leaf: Callable, fail: Callable) -> Any:
    """Rebuild `root` depth first, without recursion. `open_node(v, where)`
    is None for a leaf -- then `leaf(v, where)` is its new value -- or
    (children, finish): `children` a list of (value, where) rebuilt in
    order, `finish(list of the new children)` the new container. A
    container on the path again (a cycle), or deeper than MAX_NESTING
    counted from the field (`outer` containers around `root`), raises
    `fail(kind, value, where)`; so does the interpreter's recursion limit
    reached while a finished container is built (kind _RECURSION)."""
    try:
        opened = open_node(root, where)
        if opened is None:
            return leaf(root, where)
        path: set = set()
        stack: list = []
        v, w, node = root, where, opened
        while True:
            if node is not None:  # enter the container v
                key = id(v)
                if key in path:
                    raise fail(_CYCLE, v, w)
                if outer + len(path) >= MAX_NESTING:
                    raise fail(_DEEP, v, w)
                path.add(key)
                stack.append([key, node[0], 0, [], node[1]])
            top = stack[-1]
            children, i = top[1], top[2]
            if i < len(children):
                top[2] = i + 1
                v, w = children[i]
                node = open_node(v, w)
                if node is None:
                    top[3].append(leaf(v, w))
                continue
            node = None
            stack.pop()
            path.discard(top[0])
            built = top[4](top[3])
            if not stack:
                return built
            stack[-1][3].append(built)
    except RecursionError:
        raise fail(_RECURSION, root, where) from None


def _recursion_text(where: str) -> str:
    return (f"{where}: two distinct nested values of equal hash in one set or dict are compared by the "
            f"interpreter one level of its recursion limit per container, and the stack of this call "
            f"has no room left for that; refused")


def _pairs_of(out: list) -> list:
    return [(out[i], out[i + 1]) for i in range(0, len(out), 2)]


def _hashed(x: Any, err: type, where: str, what: str) -> None:
    """A value the core built is made a key or an element only when it has
    a hash (round 16, i0-r15-02): the one it can lack is a signaling-NaN
    Decimal (Decimal's C hash refuses it), and what holds one; refused with
    the entry's own error, never the interpreter's TypeError."""
    try:
        hash(x)
    except TypeError:
        raise err(f"{where}: a {what} holds a value that has no hash (a signaling-NaN Decimal); refused") from None


def _dict_of(pairs: list, err: type, where: str) -> dict:
    """A dict of the new keys, refusing keys that were distinct in the
    sender's container but are equal as plain data (never merged), and a
    key that has no hash."""
    d: dict = {}
    for k, x in pairs:
        _hashed(k, err, where, "dict key")
        d[k] = x
    if len(d) != len(pairs):
        raise err(f"{where}: keys that differ in the sender's dict are equal as plain data; refused, not merged")
    return d


def _set_of(make: Callable, out: list, err: type, where: str) -> Any:
    for x in out:
        _hashed(x, err, where, "set element")
    got = make(out)
    if len(got) != len(out):
        raise err(f"{where}: elements that differ in the sender's set are equal as plain data; refused, "
                  f"not merged")
    return got


_CONTAINERS = (tuple, list, set, frozenset, dict)


def _settle_open(value: Any, where: str) -> Any:
    t = type(value)
    if _BUILDER.get(t) is not None:
        return None
    if t is FrozenDict:
        try:
            pairs = _FD_ITEMS(value)
        except AttributeError:
            pairs = None
        if type(pairs) is not tuple or any(type(p) is not tuple or tuple.__len__(p) != 2
                                           for p in tuple.__iter__(pairs)):
            raise Unsettled("a FrozenDict whose pairs were replaced is not plain data")
        children = []
        for p in tuple.__iter__(pairs):
            children.append((tuple.__getitem__(p, 0), where))
            children.append((tuple.__getitem__(p, 1), where))
        return children, lambda out: FrozenDict._from_pairs(tuple(_dict_of(_pairs_of(out), Unsettled, where).items()))
    container = None
    for c in _CONTAINERS:
        if derives(t, c):
            container = c
            break
    if container is None:
        return None
    if container is dict:
        children = []
        for k, x in dict.items(value):
            children.append((k, where))
            children.append((x, where))
        return children, lambda out: _dict_of(_pairs_of(out), Unsettled, where)
    children = [(x, where) for x in container.__iter__(value)]
    if t is FrozenList:
        return children, FrozenList
    if t is FrozenSet:
        return children, lambda out: _set_of(FrozenSet, out, Unsettled, where)
    if container is set or container is frozenset:
        return children, lambda out: _set_of(container, out, Unsettled, where)
    return children, container


def _settle_leaf(value: Any, where: str) -> Any:
    t = type(value)
    try:
        build = _BUILDER.get(t)
        if build is not None:
            return build(value)
        base = _base_of(t)
        if base is not None:
            return BUILD[base](value)
    except Unsettled:
        raise
    except ValueError as exc:  # a broken Fraction
        raise Unsettled(str(exc)) from None
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


def _settle_fail(kind: str, value: Any, where: str) -> Exception:
    if kind == _CYCLE:
        return Unsettled(f"a {type_name(value)} that holds itself (a cycle) is not plain data")
    if kind == _DEEP:
        return Unsettled(_too_deep(f"a {type_name(value)}"))
    return Unsettled(_recursion_text(f"a {type_name(value)}"))


def take_int(value: Any, where: str) -> int:
    """A plug-in's integer answer, taken after its call returned (engine.py
    `_check_delay`): `settle`, then an int itself (never a bool)."""
    got = _taken(value, where)
    if type(got) is not int:
        raise ValueError(f"{where} must be an int, got {type_name(value)}")
    return got


def take_float(value: Any, where: str) -> float:
    """A plug-in's number answer, taken after its call returned (the
    fee): `settle`, then the float field's rule (the nearest float of the
    value: an int, a Fraction, a numpy number -- a longdouble too --;
    never a bool)."""
    t = type(value)
    if is_static(t) and derives(t, _NP_LONGDOUBLE):
        return _longdouble_nearest(value, where)  # numpy's C code: runs nothing of the plug-in's
    got = _taken(value, where)
    if type(got) is bool:
        raise ValueError(f"{where} must be a number, got {type_name(value)}")
    return _nearest_of(got, value, where, True)


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


NOT_PLAIN = _NOT_PLAIN


def is_longdouble(t: type) -> bool:
    """Does class `t` derive from numpy's longdouble (its own MRO)?"""
    return derives(t, _NP_LONGDOUBLE)


def longdouble_ratio(value: Any) -> Any:
    """The exact value a numpy longdouble holds, as (numerator, denominator)
    ints, read by numpy's own C method (no code of a subclass runs); None
    for inf or nan."""
    try:
        n, d = _LD_RATIO(value)
    except (OverflowError, ValueError):
        return None
    return _new_int(n), _new_int(d)


def plain_scalar(value: Any, where: str = "value") -> Any:
    """The scalar rule's value, or `NOT_PLAIN` for a value the rule does
    not take; ValueError for a number whose exact conversion failed (the
    reason in its text)."""
    return _plain_scalar(value, where)


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
    """A number field, as a new `float` itself: the float nearest the
    value (the float field's rule above: an int, a float, a Fraction, a
    numpy integer or floating number, a longdouble too; a subclass gives the
    number it holds); never a bool. `numbers_only=False` also accepts a
    numeric str and a Decimal (read as the decimal they write). A finite
    value beyond a float's range is refused. Whether the number is finite
    or positive is the caller's rule."""
    if derives(type(value), _NP_LONGDOUBLE):
        return _longdouble_nearest(value, where)
    got = _plain_scalar(value, where)
    if type(got) is bool:
        raise ValueError(f"{where} must be a number, got {type_name(value)}")
    return _nearest_of(got, value, where, numbers_only)


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


class _HashOnly:
    """An element whose hash is a given int and whose == is identity: a
    frozenset of these hashes as the frozenset of the objects the ints are
    the hashes of (CPython's frozenset hash is made from its elements'
    hashes and their number), without comparing those objects."""

    __slots__ = ("_h",)

    def __init__(self, h: int) -> None:
        self._h = h

    def __hash__(self) -> int:
        return self._h


_UNHASHABLE = object()


def _pairs_hash(pairs: tuple) -> Any:
    """hash(frozenset(pairs)) for distinct pairs, made without comparing two
    pairs (round 15): each pair's hash is taken (a FrozenDict inside hashes by
    the hash it stored when it was made: no frame per nesting level), and
    the frozenset is made of objects that compare by identity. A pair that
    cannot be hashed (a signaling-NaN Decimal) leaves the FrozenDict
    unhashable."""
    try:
        return hash(frozenset([_HashOnly(hash(p)) for p in pairs]))
    except TypeError:
        return _UNHASHABLE


class FrozenDict(Mapping):
    """An immutable, hashable dict (was a `dict` when given). Keeps the
    given order; equal to any mapping with the same items. Its lookup
    table is a read-only mapping proxy: no dict of it is reachable by
    attribute access. Its hash is made when it is made (the value of
    hash(frozenset(its items))), so hashing never walks it."""

    __slots__ = ("_items", "_map", "_hash")

    def __init__(self, items: Mapping) -> None:
        _fd_fill(self, tuple(items.items()))

    @classmethod
    def _from_pairs(cls, pairs: tuple) -> "FrozenDict":
        self = object.__new__(cls)
        _fd_fill(self, pairs)
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
        # builds a dict or a set. Another FrozenDict or a class deriving from a
        # mapping base (is_mapping: the class's own MRO) compares by its items;
        # anything else is not a mapping.
        t = type(other)
        if t is FrozenDict:
            return _plain_equal(self, other)  # iterative: no frame per level (round 16)
        if is_mapping(t):
            return dict(_FD_ITEMS(self)) == dict(other.items())
        return NotImplemented

    def __hash__(self) -> int:
        h = self._hash
        if h is _UNHASHABLE:
            raise TypeError("unhashable FrozenDict: it holds a value that has no hash (a signaling-NaN Decimal)")
        return h

    def __repr__(self) -> str:
        return f"FrozenDict({dict(self._items)!r})"


def _fd_fill(self: FrozenDict, pairs: tuple) -> None:
    object.__setattr__(self, "_items", pairs)
    object.__setattr__(self, "_map", types.MappingProxyType(dict(pairs)))
    object.__setattr__(self, "_hash", _pairs_hash(pairs))


_FD_ITEMS = FrozenDict.__dict__["_items"].__get__


# ---- the core's equality of the containers it builds (round 16, i0-r15-03) --------------
# Two FrozenDicts compare by `_plain_equal`: one loop over an explicit stack of
# pairs, never a call per nesting level, so comparing two distinct nested
# values of equal hash (what a dict or set the core builds does when their
# hashes collide) takes the same few frames at every depth below a
# FrozenDict; tuples and frozensets above it compare in the interpreter's C,
# one level of its recursion limit per container. The answer is Python's ==:
# the same object is equal (the interpreter's identity shortcut in
# containers), tuples / FrozenLists by position, frozensets / FrozenSets and
# FrozenDicts by their elements / items, anything else by its own ==. Keys
# and elements are matched through a table of their hashes (ints: no
# comparison runs), never through a dict lookup (which would compare
# colliding keys by ==, a call per level); only when the other side holds
# several keys of that hash is each tried by a nested `_plain_equal`.

_SEQ, _SET, _MAP = "seq", "set", "map"


def _container_kind(t: type) -> Any:
    if t is tuple or t is FrozenList:
        return _SEQ
    if t is frozenset or t is FrozenSet:
        return _SET
    if t is FrozenDict:
        return _MAP
    return None


def _match(xs: tuple, ys: tuple, keyed: bool, stack: list) -> bool:
    """Pair every item of `xs` with the equal item of `ys` (same length),
    pushing what is left to compare; False when one has no partner. Items
    are (key, value) pairs when `keyed`, else elements."""
    index: dict = {}
    for y in ys:
        ky = tuple.__getitem__(y, 0) if keyed else y
        index.setdefault(hash(ky), []).append(y)
    for x in xs:
        kx = tuple.__getitem__(x, 0) if keyed else x
        cands = index.get(hash(kx))
        if not cands:
            return False
        if len(cands) == 1:
            y = cands[0]
            if keyed:
                stack.append((kx, tuple.__getitem__(y, 0)))
                stack.append((tuple.__getitem__(x, 1), tuple.__getitem__(y, 1)))
            else:
                stack.append((kx, y))
            continue
        for y in cands:
            ky = tuple.__getitem__(y, 0) if keyed else y
            if ky is kx or _plain_equal(kx, ky):
                if keyed:
                    stack.append((tuple.__getitem__(x, 1), tuple.__getitem__(y, 1)))
                break
        else:
            return False
    return True


def _plain_equal(a: Any, b: Any) -> bool:
    """a == b for values the core built (Python's answer; module comment
    above), without a call per nesting level."""
    stack: list = [(a, b)]
    while stack:
        x, y = stack.pop()
        if x is y:
            continue
        kx, ky = _container_kind(type(x)), _container_kind(type(y))
        if kx is None or ky is None:
            # a scalar, or what is not a container the core builds (a dict in
            # a FrozenDict a caller made with the public constructor): its own ==
            if not (x == y):
                return False
            continue
        if kx != ky:
            return False
        if kx == _SEQ:
            if tuple.__len__(x) != tuple.__len__(y):
                return False
            stack.extend(zip(tuple.__iter__(x), tuple.__iter__(y)))
        elif kx == _SET:
            if frozenset.__len__(x) != frozenset.__len__(y):
                return False
            if not _match(tuple(frozenset.__iter__(x)), tuple(frozenset.__iter__(y)), False, stack):
                return False
        else:
            px, py = _FD_ITEMS(x), _FD_ITEMS(y)
            if tuple.__len__(px) != tuple.__len__(py):
                return False
            if not _match(px, py, True, stack):
                return False
    return True


_FREEZE_TYPES = (tuple, list, dict, set, frozenset, FrozenList, FrozenDict, FrozenSet)


def freeze(value: Any, where: str = "value", outer: int = 0) -> Any:
    """An equal, deeply immutable form of plain data; `ValueError` for
    anything that is not plain data (module docstring). `outer` is the
    number of containers around `value` in the field that holds it (the
    nesting bound `MAX_NESTING` counts from the field). Iterative (round
    15): the same few frames whatever the nesting."""
    return _walk(value, where, outer, _freeze_open, scalar, _freeze_fail)


def _key_text(k: Any) -> str:
    return value_text(k)  # a sender's key, named without running its code (round 14)


def _freeze_open(value: Any, where: str) -> Any:
    t = type(value)
    if not is_one_of(t, _FREEZE_TYPES):
        return None
    if t is tuple or t is FrozenList:
        return ([(v, f"{where}[{i}]") for i, v in enumerate(tuple.__iter__(value))],
                tuple if t is tuple else FrozenList)
    if t is list:
        return [(v, f"{where}[{i}]") for i, v in enumerate(list.__iter__(value))], FrozenList
    if t is dict or t is FrozenDict:
        # read by the real type's own methods (a dict's, or the core's
        # FrozenDict's pairs), then built anew
        src = dict.items(value) if t is dict else _frozen_pairs(value, where)
        children = []
        for k, v in src:
            text = _key_text(k)
            children.append((k, f"{where} key {text}"))
            children.append((v, f"{where}[{text}]"))
        return children, lambda out: FrozenDict._from_pairs(tuple(_dict_of(_pairs_of(out), ValueError, where).items()))
    each = set.__iter__(value) if t is set else frozenset.__iter__(value)
    make = FrozenSet if (t is set or t is FrozenSet) else frozenset
    return [(v, f"{where} element") for v in each], lambda out: _set_of(make, out, ValueError, where)


def _freeze_fail(kind: str, value: Any, where: str) -> Exception:
    if kind == _CYCLE:
        return ValueError(f"{where} holds itself (a cycle); plain data has no cycles")
    if kind == _DEEP:
        return ValueError(_too_deep(where))
    return ValueError(_recursion_text(where))


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
    changing it changes nothing else. Iterative (round 15)."""
    return _walk(value, "value", 0, _thaw_open, _thaw_leaf, _core_fail)


def _thaw_open(value: Any, where: str) -> Any:
    t = type(value)
    if t is FrozenList or t is tuple:
        return [(v, where) for v in tuple.__iter__(value)], (list if t is FrozenList else tuple)
    if t is FrozenDict:
        children = []
        for k, v in _FD_ITEMS(value):
            children.append((k, where))
            children.append((v, where))
        return children, lambda out: dict(_pairs_of(out))
    if t is FrozenSet:
        return [(v, where) for v in frozenset.__iter__(value)], set
    if t is frozenset:
        return [(v, where) for v in frozenset.__iter__(value)], frozenset
    return None


def _thaw_leaf(value: Any, where: str) -> Any:
    return renew(value)


def _core_fail(kind: str, value: Any, where: str) -> Exception:
    """renew / thaw: a value the core built is within the bounds and has no
    cycle, so only the interpreter's comparison can stop them."""
    if kind == _RECURSION:
        return ValueError(_recursion_text(f"a {type_name(value)}"))
    return TypeError(f"a {type_name(value)} the core built {'holds itself' if kind == _CYCLE else 'nests too deep'}")


_RENEW_SCALAR = IdTable(BUILD.items())
_RENEW_CONTAINERS = (tuple, FrozenList, frozenset, FrozenSet, FrozenDict)


def renew(value: Any) -> Any:
    """The core's own new copy of a value the core built (a field of a
    carrier, made by the functions above): equal, sharing no object with
    it (but None, True, False and what the interpreter keeps one of per
    value). A value of any other type is a bug of the core: TypeError.
    Iterative (round 15)."""
    make = _RENEW_SCALAR.get(type(value))
    if make is not None:
        return make(value)
    return _walk(value, "value", 0, _renew_open, _renew_leaf, _core_fail)


def _renew_open(value: Any, where: str) -> Any:
    t = type(value)
    if t is tuple or t is FrozenList:
        return [(v, where) for v in tuple.__iter__(value)], t
    if t is frozenset or t is FrozenSet:
        return [(v, where) for v in frozenset.__iter__(value)], t
    if t is FrozenDict:
        children = []
        for k, v in _FD_ITEMS(value):
            children.append((k, where))
            children.append((v, where))
        return children, lambda out: FrozenDict._from_pairs(tuple(_pairs_of(out)))
    return None


def _renew_leaf(value: Any, where: str) -> Any:
    make = _RENEW_SCALAR.get(type(value))
    if make is None:
        raise TypeError(f"renew: a {type_name(value)} is not a value the core builds")
    return make(value)


# ---- the carriers' copiers and rebuilders: made when the core is loaded ----------------
# (round 15, i0-r14-02): one function per carrier class of the core
# (contract.PATH_CARRIERS), made once, by `bind_carriers`, when the core is
# loaded -- never on first use, so nothing the core makes at run time depends
# on the state of the process at that moment (a module swapped in
# sys.modules), and no table fills up during a run and carries into later
# runs. A class not in the tables is not a carrier of the core: TypeError.

_CARRIER_TABLES: list = []  # [copiers, rebuilders]: IdTables, filled once by bind_carriers


def bind_carriers(classes: tuple) -> None:
    """Make the copier and the rebuilder of every carrier class, once (the
    core calls this when it is loaded, right after PATH_CARRIERS is made)."""
    if _CARRIER_TABLES:
        raise RuntimeError("the carrier classes are bound once, when the core is loaded")
    copiers = IdTable([(cls, _make_copier(cls)) for cls in classes])
    rebuilders = IdTable([(cls, _make_rebuilder(cls)) for cls in classes])
    _CARRIER_TABLES.extend((copiers, rebuilders))


def copy_carrier(obj: Any) -> Any:
    """The core's own new copy of one of its carriers (a slotted, frozen
    dataclass whose fields the core made): the same class, every field
    `renew`ed. Used for every hand-over to a receiver (engine.py), so each
    receiver holds objects no one else holds."""
    copier = _CARRIER_TABLES[0].get(type(obj))
    if copier is None:
        raise TypeError(f"copy_carrier: a {type_name(obj)} is not a carrier class of the core")
    return copier(obj)


def _make_copier(cls: type) -> Callable[[Any], Any]:
    """One function per carrier class that reads each field and sets its
    renewed value on a new instance (written out field by field: about a
    quarter faster than a loop over the names)."""
    names = [f.name for f in _dataclasses.fields(cls)]
    for name in names:
        if not name.isidentifier():  # pragma: no cover - dataclass field names are identifiers
            raise TypeError(f"{cls.__qualname__}.{name}")
    lines = ["def copier(src):", "    out = new(cls)"]
    for name in names:
        lines.append(f"    put(out, {name!r}, renew(src.{name}))")
    lines.append("    return out")
    namespace = {"new": object.__new__, "put": object.__setattr__, "renew": renew, "cls": cls}
    code = compile("\n".join(lines), f"<bot.bt.core.values copier of {cls.__qualname__}>", "exec")
    exec(code, namespace)  # noqa: S102 - source built above from the class's own field names
    return namespace["copier"]


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
    rebuilder = _CARRIER_TABLES[1].get(type(obj))
    if rebuilder is None:
        raise TypeError(f"rebuild_carrier: a {type_name(obj)} is not a carrier class of the core")
    return rebuilder(obj)


def _make_rebuilder(cls: type) -> Callable[[Any], Any]:
    fields = [f for f in _dataclasses.fields(cls) if f.init]
    for f in fields:
        if not f.name.isidentifier():  # pragma: no cover
            raise TypeError(f"{cls.__qualname__}.{f.name}")
    args = ", ".join(f"{f.name}=take(src.{f.name})" for f in fields)
    namespace = {"cls": cls, "take": _as_taken}
    code = compile(f"def rebuilder(src):\n    return cls({args})",
                   f"<bot.bt.core.values rebuilder of {cls.__qualname__}>", "exec")
    exec(code, namespace)  # noqa: S102 - the class's own field names
    return namespace["rebuilder"]


def _as_taken(value: Any) -> Any:
    """A slot's value as the constructor may be given it after the
    sender's call returned (round 12): a built-in scalar itself as it is
    (the field functions build it anew by its own type), anything else
    settled first -- so a value the sender put in a slot behind the class's
    back runs none of its code when the carrier is made again."""
    return value if _BUILDER.get(type(value)) is not None else settle(value)

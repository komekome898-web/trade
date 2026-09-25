"""Round 16 (i0-r15-01..04, 07): one value, one reading, on every path.

The root cause of the round-15 findings (round_16/ROOTCAUSE.md §1): the
core read one value differently by type or by path -- a float time by its
shortest repr but a Fraction by its value; a float FIELD rounded an int and
refused a longdouble; a key without a hash escaped as the interpreter's
TypeError where a too-deep comparison was the entry's error; two colliding
nested FrozenDicts compared through a Python method (3 frames a level) where
tuples compare in C (1 frame a level). The oracles below are made from the
VALUE by the library in this clean process, never from the core's cases.

Grid T (`test_to_nanos_*`): value class {float, numpy float16 / float32 /
  float64 / longdouble, int, Fraction, Decimal, str} x unit {s, ms, us, ns}
  x values (seed 16: times TYPED as decimals with 0..9 fractional digits,
  the value a float of them holds, whole-number floats, floats coarser than
  1 ns, 0, -0.0, negatives, 0.25, 1.5, inf, nan). Oracle: the value has two
  readings -- its exact value (a float's `as_integer_ratio`) and the decimal
  it writes (a str / Decimal: its text; a float: its shortest repr; a
  longdouble: the float it converts to exactly, else no reading); when both
  state the same whole number of ns, that number; else a refusal.

Grid N (`test_a_float_field_*`): value class {int, every numpy integer
  class, float, numpy float16 / 32 / 64 / longdouble, Fraction, Decimal,
  numeric str, bool, complex, numpy complex128} x values (2**53 + 1, 1/3,
  0.1, 10**400, -(2**60 + 1), inf, nan, -0.0) x entry {as_float,
  as_float(numbers_only=False), take_float, an event's price, a cost
  model's fee}. Oracle: the float nearest the exact value (the library's
  correctly rounded float(Fraction)); inf / nan / -0.0 kept; refused when
  the entry does not take the class (bool, complex, Decimal / str where
  only numbers are taken) or the value is beyond a float's range. One value
  is never "rounded" by one class and "refused" by another.

Grid E (`test_*_hash*`): every scalar class the core builds x values
  (sNaN, NaN, inf, 0, 2**70, 0.5): the built value has no hash exactly when
  the library's value has none (a signaling-NaN Decimal); shapes that make
  the core hash it (dict key, set element, a tuple / FrozenDict holding it
  as a key or an element, nested in a list) x entry {freeze, settle,
  place_order, an outbox message, the account's forced order}: the entry's
  own error; shapes that do not hash it (a dict value, a list element) are
  taken, and thaw / renew of what was taken work.

Grid F (`test_*colliding*`, `test_the_cores_equality_*`): container of each
  level {tuple, FrozenList, frozenset, FrozenSet, FrozenDict value side,
  FrozenDict key side, mixed by a seeded cycle} x levels {1, 10, 30, 48,
  97} x where the two values differ {at the bottom, nowhere}: (a) the core's
  equality equals an oracle that compares the same structure with
  FrozenDict read as a tagged frozenset of its items (plenty of stack); (b)
  freeze of a dict with both as keys needs at most CALL_FRAMES + 2 x levels
  frames of headroom. Plus random core values (seed 16, nesting up to 4,
  leaves whose hashes collide across types) compared pairwise.

NOT in the grids (A-10): numpy complex classes other than complex128 in
the float field (a complex is refused whatever its class; one class
stands for them); `datetime` objects (the time entry for text is
to_nanos(..., "iso"), tested in test_bt0_time.py); the thread's decimal
context changed while to_nanos runs (grid B of round 15 measured to_nanos
under every change); a numpy clongdouble in grid T (complex: refused).
"""
from __future__ import annotations

import math
import random
import sys
from decimal import Decimal
from fractions import Fraction

import numpy as np
import pytest

from bot.bt.core import BarEvent, CoreEngine, TradeEvent, values as V
from bot.bt.core.api import OrderRequest
from bot.bt.core.errors import (AccountSocketError, CostModelError, EventValidationError, OrderApiError,
                                TimestampUnitError)
from bot.bt.core.interfaces import NullCostModel
from bot.bt.core.testing import ImmediateFillModel, RecordingAccount
from bot.bt.core.time import to_nanos

UNITS = {"s": 10**9, "ms": 10**6, "us": 10**3, "ns": 1}
WIDE = (-(2**63), 2**63 - 1)
T0 = 1_700_000_000_000_000_000


# ---- grid T: a time has one reading or is refused ---------------------------------------

def _typed_times():
    """Decimal texts of times in every unit, drawn by seed 16."""
    rng = random.Random(16)
    out = []
    for _ in range(60):
        ns = rng.randrange(0, 4_100_000_000_000_000_000)
        for unit, f in UNITS.items():
            q = Fraction(ns, f)
            digits = rng.randrange(0, 10)
            # keep `digits` fractional digits of the unit value
            scaled = Fraction(int(q * 10**digits), 10**digits)
            text = str(scaled.numerator) if digits == 0 else (
                f"{scaled.numerator // scaled.denominator}.{str(int((scaled - int(scaled)) * 10**digits)).zfill(digits)}")
            out.append((text, unit))
    out += [("0", "s"), ("0.25", "s"), ("1.5", "s"), ("-3.5", "ms"), ("1700000000", "s"),
            ("1700000000123456.75", "us"), ("1700000000123456.8", "us"), ("2816833943301389824", "ns"),
            ("1700000000000000128", "ns"), ("1700000000.123", "s"), ("1700000000.1234567", "s"),
            ("123456789.000000001", "s")]
    return out


TYPED = _typed_times()


def _ld_is_float(v) -> bool:
    return Fraction(*v.as_integer_ratio()) == Fraction(*float(v).as_integer_ratio())


def _readings(v):
    """(exact value, the decimal it writes) as Fractions, or None where the
    value has no such reading; decided by the library."""
    if isinstance(v, (bool, np.bool_)):
        return None, None
    if isinstance(v, str):
        try:
            d = Decimal(v.strip())
        except Exception:  # noqa: BLE001 - not a number
            return None, None
        return (Fraction(d), Fraction(d)) if d.is_finite() else (None, None)
    if isinstance(v, Decimal):
        return (Fraction(v), Fraction(v)) if v.is_finite() else (None, None)
    if isinstance(v, (int, np.integer)):
        return Fraction(int(v)), Fraction(int(v))
    if isinstance(v, Fraction):
        return v, v
    if isinstance(v, np.longdouble):
        if not np.isfinite(v) or not _ld_is_float(v):
            return None, None
        v = float(v)
    if isinstance(v, (float, np.floating)):
        f = float(v)
        if not math.isfinite(f):
            return None, None
        return Fraction(*f.as_integer_ratio()), Fraction(Decimal(repr(f)))
    return None, None


def _oracle_ns(v, unit):
    exact, written = _readings(v)
    if exact is None or written is None or exact != written:
        return None
    q = exact * UNITS[unit]
    return int(q) if q.denominator == 1 and WIDE[0] <= q <= WIDE[1] else None


def _time_values():
    out = []
    for text, unit in TYPED:
        out.append((text, unit))
        out.append((Decimal(text), unit))
        out.append((Fraction(text), unit))
        if Fraction(text).denominator == 1:
            out.append((int(Fraction(text)), unit))
        for cls in (float, np.float16, np.float32, np.float64, np.longdouble):
            try:
                out.append((cls(text), unit))
            except (OverflowError, ValueError):
                pass
        f = float(text)
        if math.isfinite(f):  # the value a float of the text holds, typed exactly
            held = Fraction(*f.as_integer_ratio())
            out.append((Decimal(held.numerator) / Decimal(held.denominator) if held.denominator == 1
                        else Decimal(f), unit))
    for unit in UNITS:
        for x in (0.0, -0.0, 0.25, 1.5, -2.0, float(2**62), float(2**62 + 2**10), 1e300, float("inf"),
                  float("nan"), -float("inf")):
            out.append((x, unit))
            out.append((np.float64(x), unit))
            out.append((np.longdouble(x), unit))
        out.append((np.longdouble(2**62) + np.longdouble(1), unit))  # a longdouble no float holds
        out.append((True, unit))
        out.append((1 + 2j, unit))
    return out


TIME_VALUES = _time_values()


@pytest.mark.parametrize("v,unit", TIME_VALUES, ids=lambda x: f"{type(x).__name__}({x!r})" if not isinstance(x, str) or x not in UNITS else x)
def test_to_nanos_gives_the_one_reading_of_a_value_or_refuses(v, unit):
    want = _oracle_ns(v, unit)
    try:
        got = to_nanos(v, unit, plausible=WIDE)
    except TimestampUnitError:
        got = None
    assert got == want, f"to_nanos({type(v).__name__} {v!r}, {unit!r}) = {got}; one reading: {want}"
    assert got is None or type(got) is int


def test_the_grid_holds_floats_whose_two_readings_differ_and_agree():
    """The grid is not vacuous: floats of both kinds, and times accepted."""
    differ = agree = 0
    for v, unit in TIME_VALUES:
        if type(v) is float and math.isfinite(v):
            e, w = _readings(v)
            if e != w:
                differ += 1
            elif (e * UNITS[unit]).denominator == 1:
                agree += 1
    assert differ >= 50 and agree >= 20, (differ, agree)


def test_a_refused_longdouble_says_why():
    """i0-r15-07: the refusal names the reason, not the class as a whole."""
    with pytest.raises(TimestampUnitError) as info:
        to_nanos(np.longdouble("1700000000.123456789"), "s")
    assert "exactly" in str(info.value), str(info.value)


def test_a_float_that_does_not_hold_its_decimal_is_refused_with_the_reason():
    with pytest.raises(TimestampUnitError) as info:
        to_nanos(1700000000123456.75, "us")
    text = str(info.value)
    assert "1700000000123456.75" in text and "1700000000123456.8" in text, text


# ---- grid N: a float field is the nearest float of the value -----------------------------

def _numpy_int_classes():
    return sorted({c for c in np.sctypeDict.values() if issubclass(c, np.integer)
                   and not issubclass(c, np.timedelta64)}, key=lambda c: c.__name__)


FIELD_TEXTS = ["9007199254740993", "0.1", "-1152921504606846977", "1e400", "-0.0", "inf", "nan",
               "0.333333333333333333333333"]


def _field_values():
    out = []
    for t in FIELD_TEXTS:
        out.append(t)
        out.append(Decimal(t))
        try:
            fr = Fraction(t)
        except ValueError:
            fr = None
        if fr is not None:
            out.append(fr)
            if fr.denominator == 1:
                out.append(int(fr))
                for c in _numpy_int_classes():
                    info = np.iinfo(c)
                    if info.min <= int(fr) <= info.max:
                        out.append(c(int(fr)))
        for c in (float, np.float16, np.float32, np.float64, np.longdouble):
            try:
                out.append(c(t))
            except (OverflowError, ValueError):
                pass
    out += [Fraction(1, 3), np.longdouble(1) / np.longdouble(3), np.longdouble(2**53) + np.longdouble(1),
            np.longdouble("1e4000"), True, np.bool_(True), 1 + 0j, np.complex128(1.5)]
    return out


FIELD_VALUES = _field_values()


def _nearest_of_exact(q):
    try:
        return float(q)  # Fraction.__float__: the correctly rounded float
    except OverflowError:
        return None  # a finite value beyond a float's range


def _nearest(v):
    """The nearest float of the value (None: no such float), by the library.
    A finite value beyond a float's range has none (it is not infinite)."""
    if isinstance(v, str):
        try:
            v = Decimal(v.strip())
        except Exception:  # noqa: BLE001
            return None
    if isinstance(v, Decimal):
        if v.is_snan():
            return None
        if not v.is_finite() or v.is_zero():
            return float(v)  # inf, nan, and the sign of a zero
        return _nearest_of_exact(Fraction(v))
    if isinstance(v, (float, np.floating)):
        if np.isnan(v) or np.isinf(v) or v == 0:
            return float(v)
        return _nearest_of_exact(Fraction(*v.as_integer_ratio()))
    return _nearest_of_exact(Fraction(int(v)) if isinstance(v, (int, np.integer)) else v)


def _takes(entry, v):
    """Does the entry take the value's class at all?"""
    if isinstance(v, (bool, np.bool_, complex, np.complexfloating)):
        return False
    if isinstance(v, (Decimal, str)):
        return entry in ("as_float_text", "event_price")
    return True


def _same_float(a, b):
    if a is None or b is None:
        return a is b
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    return a == b and math.copysign(1, a) == math.copysign(1, b)


def _fee_run(fee):
    class Cost:
        def cost(self, fill):
            return fee

    class S:
        n = 0

        def on_event(self, ev, ctx):
            S.n += 1
            if S.n == 1:
                ctx.place_order(OrderRequest(side="buy", order_type="market", size=1.0, client_order_id="o1"))

    acct = RecordingAccount()
    bars = [BarEvent(received_time_ns=T0 + k, open=100.0, high=100.0, low=100.0, close=100.0, volume=1.0)
            for k in (0, 10, 20)]
    CoreEngine(S(), bars, fill_model=ImmediateFillModel(100.0), account=acct, cost_model=Cost()).run()
    return [f.fee for kind, f in acct.calls if kind == "fill"][0]


ENTRIES = {
    "as_float": lambda v: V.as_float(v, "x"),
    "as_float_text": lambda v: V.as_float(v, "x", numbers_only=False),
    "take_float": lambda v: V.take_float(v, "x"),
    "event_price": lambda v: TradeEvent(received_time_ns=T0, price=v, size=1.0).price,
    "fee": _fee_run,
}
REFUSALS = (ValueError, EventValidationError, CostModelError)


@pytest.mark.parametrize("v", FIELD_VALUES, ids=lambda v: f"{type(v).__name__}({v!r})")
@pytest.mark.parametrize("entry", list(ENTRIES))
def test_a_float_field_takes_the_nearest_float_of_the_value_or_refuses(entry, v):
    want = _nearest(v) if _takes(entry, v) else None
    if entry == "event_price" and want is not None and not (math.isfinite(want) and want > 0):
        want = None  # the event's own rule: finite and > 0
    if entry == "fee" and want is not None and not math.isfinite(want):
        want = None  # the engine's own rule: a finite fee
    try:
        got = ENTRIES[entry](v)
    except REFUSALS:
        got = None
    assert _same_float(got, want), f"{entry}({type(v).__name__} {v!r}) = {got!r}; the nearest float: {want!r}"
    assert got is None or type(got) is float


@pytest.mark.parametrize("entry", list(ENTRIES))
def test_one_value_is_taken_alike_by_every_class_that_holds_it(entry):
    """2**53 + 1 and 1/3: every class that holds the value exactly gives the
    same answer (never rounded by one class and refused by another)."""
    for value, holders in ((2**53 + 1, [2**53 + 1, np.int64(2**53 + 1), np.uint64(2**53 + 1), Fraction(2**53 + 1),
                                        np.longdouble(2**53) + np.longdouble(1)]),
                           (Fraction(1, 3), [Fraction(1, 3)])):
        got = set()
        for h in holders:
            if isinstance(h, np.longdouble) and Fraction(*h.as_integer_ratio()) != value:
                continue  # this platform's longdouble does not hold it
            try:
                got.add(ENTRIES[entry](h))
            except REFUSALS:
                got.add("refused")
        assert len(got) == 1, (entry, value, got)


def test_the_now_conversion_is_exact_where_it_is_used():
    """values._now says EXACTLY: an int a float cannot hold is refused by it
    (the float field takes the nearest float by another function)."""
    with pytest.raises(ValueError):
        V._now(float, 2**53 + 1, "x")


# ---- grid E: a value without a hash --------------------------------------------------------

class HashedDecimal(Decimal):
    def __hash__(self):
        return 7


LEAVES = [HashedDecimal("sNaN"), Decimal("NaN"), Decimal("-Infinity"), Decimal(0), 2**70, 0.5, float("nan"),
          Fraction(1, 2), "a", b"a", None, True, 1 + 2j]


@pytest.mark.parametrize("v", LEAVES, ids=repr)
def test_a_built_value_has_no_hash_exactly_when_the_librarys_has_none(v):
    try:
        hash(Decimal(v) if isinstance(v, Decimal) else v)
        lib = True
    except TypeError:
        lib = False
    if isinstance(v, HashedDecimal):
        lib = not Decimal(v).is_snan()
    built = V.freeze(v)
    try:
        hash(built)
        core = True
    except TypeError:
        core = False
    assert core == lib, (v, core, lib)


def _snan_shapes():
    k = HashedDecimal("sNaN")
    # the sender's FrozenDict holding its hashed sNaN as a VALUE: hashable for the
    # sender; built again by the core with the plain sNaN, it has no hash
    fd_value = V.FrozenDict({"v": k})
    return {
        "dict-key": ({k: 1}, False),
        "set-element": ({k}, False),
        "tuple-in-set": ({(k,)}, False),
        "frozenset-element": (frozenset([k]), False),
        "nested-dict-key": ([{"a": {k: 1}}], False),
        "tuple-with-snan-as-dict-key": ({(k,): 1}, False),
        "frozendict-with-snan-value-as-key": ({fd_value: 1}, False),
        "frozendict-with-snan-value-in-a-set": ({fd_value}, False),
        "dict-value": ({"a": k}, True),
        "list-element": ([k, 1], True),
        "tuple-element": ((k,), True),
    }


SNAN_SHAPES = list(_snan_shapes())


@pytest.mark.parametrize("shape", SNAN_SHAPES)
def test_freeze_and_settle_hash_nothing_that_has_no_hash(shape):
    value, taken = _snan_shapes()[shape]
    for fn, err in ((V.freeze, ValueError), (V.settle, V.Unsettled)):
        try:
            got = fn(value)
        except BaseException as exc:  # noqa: BLE001 - judged below
            assert not taken and isinstance(exc, err), f"{fn.__name__} {shape}: {type(exc).__name__}: {exc}"
            continue
        assert taken, f"{fn.__name__} {shape}: taken, should be refused"
        V.thaw(got)
        V.renew(got)


def _bars():
    return [BarEvent(received_time_ns=T0 + k, open=100.0, high=100.0, low=100.0, close=100.0, volume=1.0)
            for k in (0, 10, 20)]


def _outbox(ctx):
    return object.__getattribute__(ctx, "_StrategyContext__place_order_cb").__self__[2]


def _entry_outcomes(value):
    out = {}
    seen = []

    class P:
        n = 0

        def on_event(self, ev, ctx):
            P.n += 1
            if P.n == 1:
                try:
                    ctx.place_order(OrderRequest(side="buy", order_type="market", size=1.0,
                                                 client_order_id="o1", extra=(("k", value),)))
                    seen.append(None)
                except BaseException as exc:  # noqa: BLE001
                    seen.append(exc)

    CoreEngine(P(), _bars(), fill_model=ImmediateFillModel(100.0), account=RecordingAccount(),
               cost_model=NullCostModel()).run()
    out["place_order"] = seen[0]

    class B:
        n = 0

        def on_event(self, ev, ctx):
            B.n += 1
            if B.n == 1:
                req = OrderRequest(side="buy", order_type="market", size=1.0, client_order_id="o1")
                object.__setattr__(req, "extra", (("k", value),))
                list.append(_outbox(ctx), ("new", req, ev.received_time_ns))

    try:
        CoreEngine(B(), _bars(), fill_model=ImmediateFillModel(100.0), account=RecordingAccount(),
                   cost_model=NullCostModel()).run()
        out["outbox"] = None
    except BaseException as exc:  # noqa: BLE001
        out["outbox"] = exc

    class Forcing(RecordingAccount):
        def on_market_event(self, event, t):
            super().on_market_event(event, t)
            if event.received_time_ns == T0 + 10:
                req = OrderRequest(side="sell", order_type="market", size=1.0, client_order_id="f1")
                object.__setattr__(req, "extra", (("k", value),))
                return [req]
            return []

    class Quiet:
        def on_event(self, ev, ctx):
            pass

    try:
        CoreEngine(Quiet(), _bars(), fill_model=ImmediateFillModel(100.0), account=Forcing(),
                   cost_model=NullCostModel()).run()
        out["account"] = None
    except BaseException as exc:  # noqa: BLE001
        out["account"] = exc
    return out


ENTRY_ERRORS = {"place_order": OrderApiError, "outbox": OrderApiError, "account": AccountSocketError}


@pytest.mark.parametrize("shape", SNAN_SHAPES)
def test_every_entry_refuses_a_value_without_a_hash_with_its_own_error(shape):
    value, taken = _snan_shapes()[shape]
    for entry, exc in _entry_outcomes(value).items():
        if taken:
            assert exc is None, f"{entry} {shape}: {type(exc).__name__}: {exc}"
        else:
            assert isinstance(exc, ENTRY_ERRORS[entry]), f"{entry} {shape}: {type(exc).__name__}: {exc}"


# ---- grid F: comparing colliding nested values ------------------------------------------

KINDS = ["tuple", "FrozenList", "frozenset", "FrozenSet", "FrozenDict-value", "FrozenDict-key", "mixed"]
CYCLE = ["tuple", "FrozenDict-value", "frozenset", "FrozenDict-key", "FrozenList", "FrozenSet"]


def _wrap(kind, x, level):
    if kind == "mixed":
        kind = CYCLE[level % len(CYCLE)]
    if kind == "tuple":
        return (x,)
    if kind == "FrozenList":
        return V.FrozenList((x,))
    if kind == "frozenset":
        return frozenset([x])
    if kind == "FrozenSet":
        return V.FrozenSet([x])
    if kind == "FrozenDict-value":
        return V.FrozenDict({"k": x})
    return V.FrozenDict({x: 0})


def _pair(kind, levels, differ):
    a, b = (-1, -2) if differ else (-1, -1)
    for i in range(levels - 1):
        a, b = _wrap(kind, a, i), _wrap(kind, b, i)
    return a, b


class _D:
    """The oracle's FrozenDict: equal to another _D with the same items."""

    def __init__(self, items):
        self.items = frozenset(items)

    def __eq__(self, other):
        return type(other) is _D and self.items == other.items

    def __hash__(self):
        return hash(self.items)


def _plain(x, memo):
    """The oracle's copy of a core value: library types only; one copy per
    object (so the interpreter's identity shortcut sees the same objects)."""
    got = memo.get(id(x))
    if got is not None:
        return got[1]
    t = type(x)
    if t is V.FrozenDict:
        out = _D((_plain(k, memo), _plain(v, memo)) for k, v in x.items())
    elif t in (tuple, V.FrozenList):
        out = tuple(_plain(v, memo) for v in x)
    elif t in (frozenset, V.FrozenSet):
        out = frozenset(_plain(v, memo) for v in x)
    elif t is V.PlainFraction:
        out = Fraction(*V.fraction_parts(x))
    elif t is V.PlainDecimal:
        out = Decimal(str(x))
    else:
        out = x
    memo[id(x)] = (x, out)
    return out


def _oracle_equal(a, b):
    old = sys.getrecursionlimit()
    sys.setrecursionlimit(max(old, 20000))
    try:
        memo: dict = {}
        return _plain(a, memo) == _plain(b, memo)
    finally:
        sys.setrecursionlimit(old)


def _depth():
    f, n = sys._getframe(1), 0
    while f is not None:
        n += 1
        f = f.f_back
    return n


def _ok(headroom, fn):
    old = sys.getrecursionlimit()
    sys.setrecursionlimit(_depth() + headroom)
    try:
        fn()
        return True
    except (RecursionError, ValueError):
        return False
    finally:
        sys.setrecursionlimit(old)


def _least(fn):
    lo, hi = 1, 1500
    assert _ok(hi, fn)
    while lo < hi:
        mid = (lo + hi) // 2
        if _ok(mid, fn):
            hi = mid
        else:
            lo = mid + 1
    return lo


@pytest.mark.parametrize("levels", [1, 10, 30, 48, 97])
@pytest.mark.parametrize("kind", KINDS)
def test_two_colliding_nested_values_compare_alike_and_within_one_frame_per_container(kind, levels):
    for differ in (True, False):
        a, b = _pair(kind, levels, differ)
        assert hash(a) == hash(b)
        assert (a == b) == _oracle_equal(a, b) == (not differ), (kind, levels, differ)
        assert (a != b) == differ
    a, b = _pair(kind, levels, True)
    need = _least(lambda: V.freeze({a: 1, b: 2}))
    bound = V.CALL_FRAMES + 2 * levels
    assert need <= bound, f"{kind} x {levels}: freeze needs {need} frames of headroom; bound {bound}"


def _random_value(rng, depth):
    leaves = [-1, -2, 1, 1.0, True, Fraction(1), Decimal(1), 0.5, Fraction(1, 2), Decimal("0.5"), "a", b"a",
              None, float("nan"), 1 + 0j, 2 + 1j, Decimal("NaN"), 2**61 - 1, -(2**61 - 1)]
    if depth == 0 or rng.random() < 0.3:
        return V.freeze(rng.choice(leaves))
    kind = rng.choice(["tuple", "FrozenList", "frozenset", "FrozenSet", "FrozenDict"])
    n = rng.randrange(0, 4)
    items = [_random_value(rng, depth - 1) for _ in range(n)]
    if kind == "tuple":
        return tuple(items)
    if kind == "FrozenList":
        return V.FrozenList(items)
    if kind == "frozenset":
        return frozenset(items)
    if kind == "FrozenSet":
        return V.FrozenSet(items)
    return V.FrozenDict({k: _random_value(rng, depth - 1) for k in items})


def test_the_cores_equality_of_its_containers_is_the_oracles():
    rng = random.Random(16)
    vals = [_random_value(rng, 4) for _ in range(160)]
    # pairs that are equal by construction too: a value and its renewed copy
    vals += [V.renew(v) for v in vals[:40]]
    checked = equal = 0
    for i, a in enumerate(vals):
        for b in vals[i:i + 25]:
            want = _oracle_equal(a, b)
            assert (a == b) == want, (a, b)
            assert (a != b) == (not want), (a, b)
            checked += 1
            equal += want
    assert checked > 3000 and equal > 50, (checked, equal)

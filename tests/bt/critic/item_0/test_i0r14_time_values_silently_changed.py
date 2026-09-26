"""Critic, item 0, round 14 (i0-r14-03, i0-r14-04): a time or a duration the
core takes must come out as the int of nanoseconds the value states, or be
refused -- never a different int without a word.

Requirement (REQUIREMENTS.md §1, P0-2): "時刻は UTC の int64 ナノ秒".
time.py: "Conversion is exact"; TIME_CONTRACT "rounding": "none (inputs with
sub-nanosecond digits are rejected)"; validate_nanos is "The choke point every
event timestamp passes through".

(i0-r14-03) to_nanos makes a Fraction a float first (time.py 171-174,
`float.__repr__(float(v))`) and values.scalar makes a numpy longdouble a float
(NUMBER_BASES: numpy.floating -> float), so digits the value holds are dropped
before the exactness check, and the rounded result is accepted.

(i0-r14-04) numpy.timedelta64 derives from numpy.signedinteger, so
values.NUMBER_BASES makes it an int, and int() of it is its count in ITS OWN
unit (picoseconds, femtoseconds, years, months ...): a duration stated with a
unit is taken as that many nanoseconds.

Grid: value kind {Fraction (s, ns, us), numpy.longdouble (s)} for to_nanos;
numpy.timedelta64 of unit {ps, fs, Y, M, ms (a count too large for
datetime.timedelta)} x entry {validate_nanos, values.settle, the latency
model's order delay}. Oracle: the exact int the value states, or a refusal.

Not in the grid: a Python float (its shortest repr is the documented input;
the loss happens before the core sees it); numpy.float32 / float16 (they hold
no more digits than a float).
"""
from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

from bot.bt.core import BarEvent, CoreEngine, TimestampUnitError
from bot.bt.core.api import OrderRequest
from bot.bt.core.interfaces import NullCostModel
from bot.bt.core.testing import ImmediateFillModel, RecordingAccount
from bot.bt.core.time import to_nanos, validate_nanos
from bot.bt.core import values

EXACT = 1_700_000_000_123_456_789

TO_NANOS_CASES = [
    ("Fraction s", Fraction(EXACT, 10**9), "s", EXACT),
    ("Fraction ns", Fraction(EXACT), "ns", EXACT),
    ("Fraction us", Fraction(EXACT, 1000), "us", EXACT),
    ("longdouble s", np.longdouble("1700000000.123456789"), "s", EXACT),
]


@pytest.mark.parametrize("label,value,unit,exact", TO_NANOS_CASES, ids=[c[0] for c in TO_NANOS_CASES])
def test_to_nanos_is_exact_or_refuses(label, value, unit, exact):
    try:
        got = to_nanos(value, unit)
    except TimestampUnitError:
        return
    assert got == exact, f"to_nanos({label}) gave {got}, the value states {exact} (off by {got - exact} ns)"


# (value, what it states in ns: None when it is not a whole number of ns)
TD_CASES = [
    ("5000 ps", np.timedelta64(5000, "ps"), 5),
    ("1500 ps", np.timedelta64(1500, "ps"), None),
    ("5000 fs", np.timedelta64(5000, "fs"), None),
    ("5 Y", np.timedelta64(5, "Y"), None),  # a calendar unit: no fixed ns
    ("5 M", np.timedelta64(5, "M"), None),
]


@pytest.mark.parametrize("label,value,states", TD_CASES, ids=[c[0] for c in TD_CASES])
def test_a_duration_with_a_unit_is_not_taken_as_that_many_ns(label, value, states):
    for name, fn in (("validate_nanos", lambda: validate_nanos(value)), ("settle", lambda: values.settle(value))):
        try:
            got = fn()
        except (ValueError, TimestampUnitError):
            continue
        assert states is not None and got == states, (
            f"{name}(np.timedelta64 {label}) gave {got!r}; the value states "
            f"{'a non-whole or calendar amount of ns' if states is None else f'{states} ns'}")


def test_the_latency_models_delay_in_picoseconds_is_not_taken_as_nanoseconds():
    T0 = 1_700_000_000_000_000_000

    class Lat:
        def feed_delay_ns(self, event, *a):
            return 0

        def order_delay_ns(self, order, *a):
            return np.timedelta64(5_000, "ps")  # 5 ns, stated in picoseconds

        def cancel_delay_ns(self, cancel, *a):
            return 0

        def notice_delay_ns(self, report, *a):
            return 0

    class S:
        def __init__(self):
            self.acks = []

        def on_event(self, ev, ctx):
            if type(ev).__name__ == "OrderAckEvent":
                self.acks.append(ev.received_time_ns - T0)
            if ev.received_time_ns == T0 and type(ev).__name__ == "BarEvent":
                ctx.place_order(OrderRequest(side="buy", order_type="market", size=1.0, client_order_id="o1"))

    s = S()
    bars = [BarEvent(received_time_ns=T0 + k, open=100.0, high=100.0, low=100.0, close=100.0, volume=1.0)
            for k in (0, 5, 1_000, 10_000)]
    eng = CoreEngine(s, bars, fill_model=ImmediateFillModel(100.0), latency_model=Lat(),
                     account=RecordingAccount(), cost_model=NullCostModel())
    try:
        eng.run()
    except Exception as exc:  # a refusal (LatencyModelError) is a correct outcome
        assert type(exc).__name__ == "LatencyModelError", repr(exc)
        return
    assert s.acks == [5], f"the order reached the venue {s.acks} ns after it was sent; the model said 5 ns"

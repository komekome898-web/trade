"""Critic, item 0, round 15 (i0-r15-02): to_nanos rounds a float's value
through its shortest repr.

time.py says "Conversion is exact", TIME_CONTRACT says "rounding: none
(inputs with sub-nanosecond digits are rejected)", and for floats "floats go
through decimal.Decimal of their shortest decimal representation ... convert
without binary-float rounding; a value whose decimal representation has
sub-nanosecond digits is rejected instead of being rounded silently". For
round 15 (i0-r14-03) the worker added "a numpy longdouble only when a float
holds its value exactly (else refused, never rounded)".

The shortest repr is itself a rounding: a float with 17 significant digits
is written with fewer. `1700000000123456.75` (microseconds) is held EXACTLY
by a float (spacing 0.25), its shortest repr is `1700000000123456.8`, and
to_nanos returns 1700000000123456800 -- 50 ns off the value the float holds
(and off the value typed), with no refusal. A float that holds the whole ns
count 2816833943301389824 gives 2816833943301390000 (176 ns off). The
longdouble route of round 15 passes its exactness check (the float holds the
longdouble exactly) and then goes through the same shortest repr.

Grid: value class {float, numpy float64, numpy longdouble} x unit {us, ns}
x a value the class holds EXACTLY that is a whole ns count and whose
shortest repr has fewer digits. Oracle: the ns count the value holds, or
TimestampUnitError; never another int.

Not in the grid: floats whose exact value has sub-ns digits (1700000000.1234567
s): the documented shortest-repr reading gives the typed decimal there, and
refusing them is a design choice this test does not decide.
"""
from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

from bot.bt.core.errors import TimestampUnitError
from bot.bt.core.time import to_nanos

FACTOR = {"us": 1_000, "ns": 1}
VALUES = [("1700000000123456.75", "us"), ("2816833943301389824", "ns"), ("1700000000000000128", "ns")]
CLASSES = {"float": float, "float64": np.float64, "longdouble": np.longdouble}


@pytest.mark.parametrize("cls", list(CLASSES))
@pytest.mark.parametrize("text,unit", VALUES)
def test_to_nanos_gives_the_ns_the_float_holds_or_refuses(cls, text, unit):
    v = CLASSES[cls](text)
    n, d = v.as_integer_ratio()
    holds = Fraction(int(n), int(d)) * FACTOR[unit]
    assert holds.denominator == 1, "the grid's value must hold a whole ns count"
    assert repr(float(v)) != text, "the grid's value must have a shorter repr than its digits"
    try:
        got = to_nanos(v, unit)
    except TimestampUnitError:
        return
    assert got == int(holds), \
        f"to_nanos({cls}({text}), {unit!r}) gave {got}, the value holds {int(holds)} ({got - int(holds):+d} ns)"

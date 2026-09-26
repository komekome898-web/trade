"""Exact number handling for the reference implementation.

Every price, quantity, rate and amount is held as fractions.Fraction.
Accepted inputs: int, str (decimal or "a/b"), Fraction, float (converted
exactly with Fraction(float), i.e. the binary value, not the decimal literal).
bool is refused because it is an int subclass and almost always a mistake.
"""
from __future__ import annotations

from fractions import Fraction
from numbers import Rational

INT64_MIN = -(2 ** 63)
INT64_MAX = 2 ** 63 - 1


def q(x, name: str = "value") -> Fraction:
    """Convert x to an exact Fraction, refusing ambiguous input."""
    if isinstance(x, bool):
        raise TypeError(f"{name}: bool is not a number here")
    if isinstance(x, Fraction):
        return x
    if isinstance(x, int):
        return Fraction(x)
    if isinstance(x, float):
        if x != x or x in (float("inf"), float("-inf")):
            raise ValueError(f"{name}: non-finite float {x!r}")
        return Fraction(x)
    if isinstance(x, str):
        s = x.strip()
        if not s:
            raise ValueError(f"{name}: empty string")
        try:
            return Fraction(s)
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError(f"{name}: cannot parse {x!r}") from exc
    if isinstance(x, Rational):
        return Fraction(x.numerator, x.denominator)
    raise TypeError(f"{name}: unsupported type {type(x).__name__}")


def q_str(x: Fraction) -> str:
    """Canonical text for a Fraction ("3", "-1/4")."""
    return str(Fraction(x))


def ns(t, name: str = "time") -> int:
    """Validate a UTC int64 nanosecond timestamp (int only, no float/bool)."""
    if isinstance(t, bool) or not isinstance(t, int):
        raise TypeError(f"{name}: time must be int nanoseconds, got {type(t).__name__}")
    if t < INT64_MIN or t > INT64_MAX:
        raise ValueError(f"{name}: {t} outside int64")
    return t


def nonneg_int(v, name: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise TypeError(f"{name}: must be int, got {type(v).__name__}")
    if v < 0:
        raise ValueError(f"{name}: must be >= 0, got {v}")
    return v


def choice(v, allowed: tuple, name: str):
    if v not in allowed:
        raise ValueError(f"{name}: must be one of {allowed}, got {v!r}")
    return v


def on_grid(x: Fraction, step: Fraction) -> bool:
    """True when x is an integer multiple of step (step > 0)."""
    return (x / step).denominator == 1

"""Strict argument readers shared by the validation modules. Every reader
refuses (ValidationError) instead of coercing: a bool is never an int, a
NaN is never a number."""
from __future__ import annotations

import math
from typing import Any, Sequence

from .errors import ValidationError


def as_int(name: str, v: Any, *, lo: int | None = None, hi: int | None = None) -> int:
    if type(v) is not int:
        raise ValidationError(f"{name} must be an int, got {type(v).__name__} {v!r}")
    if lo is not None and v < lo:
        raise ValidationError(f"{name} must be >= {lo}, got {v}")
    if hi is not None and v > hi:
        raise ValidationError(f"{name} must be <= {hi}, got {v}")
    return v


def as_float(name: str, v: Any, *, lo: float | None = None, hi: float | None = None,
             lo_open: bool = False, hi_open: bool = False) -> float:
    if type(v) not in (int, float):
        raise ValidationError(f"{name} must be a number, got {type(v).__name__} {v!r}")
    x = float(v)
    if not math.isfinite(x):
        raise ValidationError(f"{name} must be finite, got {v!r}")
    if lo is not None and (x <= lo if lo_open else x < lo):
        raise ValidationError(f"{name} must be {'>' if lo_open else '>='} {lo}, got {v!r}")
    if hi is not None and (x >= hi if hi_open else x > hi):
        raise ValidationError(f"{name} must be {'<' if hi_open else '<='} {hi}, got {v!r}")
    return x


def as_prob(name: str, v: Any) -> float:
    return as_float(name, v, lo=0.0, hi=1.0, lo_open=True, hi_open=True)


def as_choice(name: str, v: Any, choices: Sequence[str]) -> str:
    if type(v) is not str or v not in choices:
        raise ValidationError(f"{name} must be one of {tuple(choices)}, got {v!r}")
    return v


def as_times(name: str, v: Any, *, strict: bool = False) -> list[int]:
    """A sequence of int64 ns times, non-decreasing (strictly increasing when
    `strict`). Unsorted times are refused: a time split presumes order."""
    try:
        seq = list(v)
    except TypeError:
        raise ValidationError(f"{name} must be a sequence of int ns times") from None
    out = []
    for i, t in enumerate(seq):
        out.append(as_int(f"{name}[{i}]", t, lo=-(2**63), hi=2**63 - 1))
        if i and (out[i] <= out[i - 1] if strict else out[i] < out[i - 1]):
            raise ValidationError(f"{name} must be {'strictly increasing' if strict else 'non-decreasing'}: "
                                  f"[{i - 1}]={out[i - 1]} then [{i}]={out[i]}")
    return out


def as_numbers(name: str, v: Any, *, min_len: int = 0) -> list[float]:
    try:
        seq = list(v)
    except TypeError:
        raise ValidationError(f"{name} must be a sequence of numbers") from None
    if len(seq) < min_len:
        raise ValidationError(f"{name} needs at least {min_len} values, got {len(seq)}")
    return [as_float(f"{name}[{i}]", x) for i, x in enumerate(seq)]

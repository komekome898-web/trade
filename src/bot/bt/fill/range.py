"""Optimistic and pessimistic sides, run both, reported as a range.

REQUIREMENTS (old item 3): "楽観側と悲観側の両方を必ず回して幅で出す". A
`FillRange` holds the two fill specs and cannot be built with one side
missing; `run_range` runs the caller's one-run function once per side and
returns both results. There is no single-side entry: a caller that has one
spec runs one model, and a range needs both.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from .spec import FillSpec, FillSpecError

T = TypeVar("T")


@dataclass(frozen=True)
class FillRange:
    optimistic: FillSpec
    pessimistic: FillSpec

    def __post_init__(self) -> None:
        for side in ("optimistic", "pessimistic"):
            if type(getattr(self, side)) is not FillSpec:
                raise FillSpecError(f"a range needs both sides; {side} is {getattr(self, side)!r}")


@dataclass(frozen=True)
class RangeResult(Generic[T]):
    optimistic: T
    pessimistic: T

    def bounds(self, measure: Callable[[T], float]) -> tuple[float, float]:
        """(low, high) of `measure` over the two sides."""
        a, b = measure(self.optimistic), measure(self.pessimistic)
        return (min(a, b), max(a, b))


def run_range(run_one: Callable[[FillSpec], T], fill_range: FillRange) -> RangeResult[T]:
    if type(fill_range) is not FillRange:
        raise FillSpecError("run_range needs a FillRange (both sides)")
    return RangeResult(optimistic=run_one(fill_range.optimistic), pessimistic=run_one(fill_range.pessimistic))

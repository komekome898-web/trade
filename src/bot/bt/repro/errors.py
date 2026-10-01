"""Errors of the reproducibility layer (item 3, old item 8)."""
from __future__ import annotations

from ..data.errors import SealedRangeError


class ReproError(ValueError):
    """A run the layer refuses to make or to record."""


class NotReproducibleError(ReproError):
    """Two executions of the same input gave different outputs."""

    def __init__(self, message: str, differing: list[str]) -> None:
        super().__init__(message)
        self.differing = differing


class RunSealedRangeError(ReproError, SealedRangeError):
    """A run's data input reaches the sealed window of a file the seal records
    list (G-3 of K1 stage G, 2026-10-01): its range is missing or ends after the
    seal's cutoff. Both a ReproError (the run is refused) and the data layer's
    SealedRangeError (why)."""

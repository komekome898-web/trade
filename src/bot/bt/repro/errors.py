"""Errors of the reproducibility layer (item 3, old item 8)."""
from __future__ import annotations


class ReproError(ValueError):
    """A run the layer refuses to make or to record."""


class NotReproducibleError(ReproError):
    """Two executions of the same input gave different outputs."""

    def __init__(self, message: str, differing: list[str]) -> None:
        super().__init__(message)
        self.differing = differing

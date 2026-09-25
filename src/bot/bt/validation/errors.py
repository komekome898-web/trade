"""Errors of the validation layer (item 3, old item 7)."""
from __future__ import annotations


class ValidationError(ValueError):
    """A request the validation layer refuses: an argument it cannot read
    exactly, or a result it cannot give without guessing."""


class SealedRefused(ValidationError):
    """A read that would reach a sealed window without passing the gates."""


class LedgerError(ValidationError):
    """The iteration ledger (ITER) is unreadable, altered or misused."""

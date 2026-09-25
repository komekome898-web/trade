"""Refusals of the data layer (item 1).

Every refusal is a `DataError` (a `ValueError`): the data layer never
returns a partial or guessed result in place of one. Each subclass names
the rule that refused.
"""
from __future__ import annotations


class DataError(ValueError):
    """Base class: the data layer refused a load or a transform."""


class SpecError(DataError):
    """The dataset declaration (spec) is malformed, incomplete or unknown."""


class PathRefused(DataError):
    """The allow-list refused a path (synthetic, intermediate, outside the
    allowed roots, or escaping through `..` / a symlink)."""


class SealedRangeError(DataError):
    """The read would reach into a sealed window (phase2_sealed SEALED.json),
    or the seal records cannot be read (fail closed)."""


class ParseError(DataError):
    """A file's bytes do not match its declaration (a cell, a row, the
    compression, the encoding, a time)."""


class TimeParseError(ParseError):
    """A time could not be normalised to int64 UTC nanoseconds exactly."""


class UnresolvedAnomalyError(DataError):
    """Events were asked for a dataset that has anomalies the caller did not
    name a resolution for (the data layer never merges silently)."""


class CorporateActionError(DataError):
    """The JPX corporate-action / listing inputs are inconsistent."""


class VectorError(DataError):
    """The vector path refused its input (unsorted times, bad rule)."""

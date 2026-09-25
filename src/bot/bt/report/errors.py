"""Errors of the report layer (item 3, old item 9)."""
from __future__ import annotations


class ReportError(ValueError):
    """An input the metrics cannot read exactly, or an export without its purpose."""

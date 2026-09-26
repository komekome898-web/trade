"""Item 1 (data and time): the data layer of the backtest engine.

Fixed requirements: docs/DISCUSSIONS/2026-09-23_backtest_env/item_1/REQUIREMENTS.md
(V1-V6 here, V7 in `bot.bt.vector`). Tests: tests/bt/item_1/.

  load(root, datasets)  -- the one reading door (loader.py): every asset by
                           its declaration (spec.py), times to int64 UTC ns
                           (timestamps.py, through the core's to_nanos),
                           the checks (anomalies.py), sha256 of every file,
                           the allow-list and the seals (allowlist.py)
  adjust_daily / Universe / universe -- JPX corporate actions and the
                           point-in-time universe (jpx.py)

The layer never returns a guessed value: what it cannot read exactly it
refuses with a `DataError`, and what is wrong with the data it reports
(anomalies) and merges only by a policy the caller names.
"""
from .allowlist import DEFAULT_ALLOWLIST, DEFAULT_ROOTS, MANDATORY_DENY, AllowList, SealRegistry
from .anomalies import KINDS as ANOMALY_KINDS
from .anomalies import POLICIES as ANOMALY_POLICIES
from .errors import (CorporateActionError, DataError, ParseError, PathRefused, SealedRangeError, SpecError,
                     TimeParseError, UnresolvedAnomalyError, VectorError)
from .jpx import Universe, adjust_daily, universe
from .loader import FileRecord, LoadResult, load
from .spec import ASSETS, FORMATS, KINDS, Spec, parse_spec
from .timestamps import TimeReader

__all__ = [
    "ANOMALY_KINDS", "ANOMALY_POLICIES", "ASSETS", "AllowList", "CorporateActionError", "DEFAULT_ALLOWLIST",
    "DEFAULT_ROOTS", "DataError", "FORMATS", "FileRecord", "KINDS", "LoadResult", "MANDATORY_DENY",
    "ParseError", "PathRefused", "SealRegistry", "SealedRangeError", "Spec", "SpecError", "TimeParseError",
    "TimeReader", "Universe", "UnresolvedAnomalyError", "VectorError", "adjust_daily", "load", "parse_spec",
    "universe",
]

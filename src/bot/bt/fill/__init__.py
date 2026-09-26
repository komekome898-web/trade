"""Item 2 (old 3): fills and queues -- the venue model plugged into the core's
fill-model socket.

`spec` (tiers 0-6 of the tool catalogue section 2.1, the five cancel stances
of section 2.2 and the probabilistic queue, the impact functions), `venue`
(`SimVenue`: order types, the venue's rules, the tier models), `book` (the
displayed book), `l3` (a per-order feed for the L3 stances), `bars` (bars
from prints for a tier-2 run), `range` (optimistic and pessimistic, both
required), `data_wait` (data this environment does not have: JPX board and
ticks). Tests: tests/bt/item_2/."""
from .bars import bars_from_trades
from .book import ExternalBook
from .data_wait import DATA_WAIT, DataUnavailableError, DataWait, data_wait_report
from .l3 import L3Add, L3Cancel, L3Feed
from .range import FillRange, RangeResult, run_range
from .spec import (
    CANCEL_STANCES,
    IMPACT_BASES,
    IMPACT_KINDS,
    PROB_FUNCTIONS,
    TIER_BY_DEFAULT,
    TIER_MECHANISM,
    TIERS,
    FillSpec,
    FillSpecError,
    ImpactSpec,
)
from .venue import FillRecord, SimVenue

__all__ = ["CANCEL_STANCES", "DATA_WAIT", "IMPACT_BASES", "IMPACT_KINDS", "PROB_FUNCTIONS", "TIERS",
           "TIER_BY_DEFAULT", "TIER_MECHANISM", "DataUnavailableError", "DataWait", "ExternalBook", "FillRange",
           "FillRecord", "FillSpec", "FillSpecError", "ImpactSpec", "L3Add", "L3Cancel", "L3Feed", "RangeResult",
           "SimVenue", "bars_from_trades", "data_wait_report", "run_range"]

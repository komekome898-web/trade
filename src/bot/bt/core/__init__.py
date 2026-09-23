"""Item 0 (core): the event-driven kernel every other `src/bot/bt/*` item
plugs into. Fixed requirements:
docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/REQUIREMENTS.md.

Modules: time (int64 UTC ns), events (event types), ordering (the total
order of processing and of merging input streams), api (strategy context
and order API), interfaces (the four sockets), engine (the queue),
contract (machine-readable guarantees), testing (test doubles, not venue
models). Tests live in tests/bt/item_0/.
"""
from .api import (
    FORCED_ID_PREFIX,
    STRATEGY_API,
    CancelRequest,
    OrderRequest,
    OrderState,
    OrderView,
    StrategyContext,
)
from .contract import CORE_CONTRACT, CORE_VERSION
from .engine import SINGLE_STREAM_NAME, CoreEngine, EngineResult
from .errors import (
    AccountSocketError,
    CoreError,
    CostModelError,
    EventOrderError,
    EventValidationError,
    LatencyModelError,
    LookAheadError,
    MissingCostModelError,
    OrderApiError,
    SourceEventTypeError,
    StaleContextError,
    TimestampUnitError,
    VenueProtocolError,
)
from .events import (
    ALL_EVENT_CLASSES,
    EVENT_TYPE_TO_CLASS,
    MARKET_EVENT_TYPES,
    NOTICE_EVENT_TYPES,
    SOURCE_EVENT_TYPES,
    BarEvent,
    BookDeltaEvent,
    BookSnapshotEvent,
    ClockEvent,
    Event,
    EventType,
    FundingEvent,
    LiquidationEvent,
    OrderAckEvent,
    OrderCanceledEvent,
    OrderFillEvent,
    OrderRejectEvent,
    OrderStateUnknownEvent,
    TradeEvent,
    event_from_dict,
)
from .interfaces import (
    Account,
    Ack,
    Canceled,
    CostModel,
    Fill,
    FillModel,
    FillNotice,
    LatencyModel,
    NullAccount,
    NullCostModel,
    NullFillModel,
    NullLatencyModel,
    Reject,
    StateUnknown,
    VenueReport,
    ZeroLatency,
)
from .ordering import (
    DELIVERY_PRIORITY,
    ORDERING_RULE,
    ORIGIN_ENGINE,
    ORIGIN_SOURCE,
    TYPE_ORDER,
    VENUE_MARKET_PRIORITY,
    order_events,
)
from .strategy import Strategy
from .time import TIME_CONTRACT, Nanos, nanos_to_iso, to_nanos, validate_nanos

import types as _types

__all__ = sorted(
    name for name, value in dict(globals()).items()
    if not name.startswith("_") and not isinstance(value, _types.ModuleType)
)

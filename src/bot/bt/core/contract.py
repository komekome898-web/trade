"""Machine-readable statement of what the core guarantees, built from the
code objects themselves (not hand-written copies), so it cannot drift from
the implementation. Item 8 (repro) can store it in a run record; the
battery can read it instead of trusting prose."""
from __future__ import annotations

from .api import FORCED_ID_PREFIX, STRATEGY_API
from .events import MARKET_EVENT_TYPES, NOTICE_EVENT_TYPES, SOURCE_EVENT_TYPES, EventType
from .interfaces import SOCKETS, socket_methods
from .ordering import ORDERING_RULE
from .time import TIME_CONTRACT

CORE_VERSION = "core-3"

CORE_CONTRACT: dict = {
    "version": CORE_VERSION,
    "time": TIME_CONTRACT,
    "event_types": [t.value for t in EventType],
    "market_event_types": sorted(t.value for t in MARKET_EVENT_TYPES),
    "notice_event_types": sorted(t.value for t in NOTICE_EVENT_TYPES),
    "source_event_types": sorted(t.value for t in SOURCE_EVENT_TYPES),
    "visibility": {
        "strategy": "called at now_ns = delivery time; sees only events already delivered, "
                    "all with received_time_ns <= now_ns; asking for until_ns > now_ns raises "
                    "LookAheadError; context revoked on return",
        "venue": "fill model and account see market data at exchange_time_ns and our requests at "
                 "their arrival time; never earlier",
        "source": "one stream or named streams merged by time; each consumed lazily (at most one "
                  "pending event per stream); each must be non-decreasing in exchange_time_ns "
                  "(else EventOrderError)",
        "forced_orders": "the strategy learns of a forced order only when its first notice is delivered",
    },
    "ordering": ORDERING_RULE,
    "strategy_api": list(STRATEGY_API),
    "sockets": {name: socket_methods(proto) for name, proto in SOCKETS.items()},
    "implicit_cost": "none (a fill without a cost model raises MissingCostModelError)",
    "resend_on_state_unknown": False,
    "forced_order_id_prefix": FORCED_ID_PREFIX,
}

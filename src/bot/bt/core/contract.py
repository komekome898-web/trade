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
from .values import PLAIN_DATA_RULE
from .window import POSITION_RULE

CORE_VERSION = "core-8"

CORE_CONTRACT: dict = {
    "version": CORE_VERSION,
    "time": TIME_CONTRACT,
    "event_types": [t.value for t in EventType],
    "market_event_types": sorted(t.value for t in MARKET_EVENT_TYPES),
    "notice_event_types": sorted(t.value for t in NOTICE_EVENT_TYPES),
    "source_event_types": sorted(t.value for t in SOURCE_EVENT_TYPES),
    "visibility": {
        "strategy": "called at now_ns = delivery time; sees only events already delivered, "
                    "all with received_time_ns <= now_ns; any time argument after now_ns (since_ns or "
                    "until_ns) raises LookAheadError; a history read returns DeliveredEvents, where an index or "
                    "an explicit non-negative slice bound naming a position after the last event of the "
                    "answer (position_rule) raises FuturePositionError; context revoked on return",
        "position_rule": {
            "max_position_by_role_as_offset_from_len": dict(POSITION_RULE),
            "negative_bounds": "count back from the newest; they can only name the past",
            "error": "FuturePositionError (an IndexError and a LookAheadError)",
        },
        "venue": "fill model and account see market data at exchange_time_ns and our requests at "
                 "their arrival time; never earlier",
        "source": "one stream or named streams merged by time; each consumed lazily (at most one "
                  "pending event per stream); each must be non-decreasing in exchange_time_ns "
                  "(else EventOrderError); a stream's own order is never re-sorted",
        "order_state": "the strategy's view and the venue ledger keep facts (acked, filled, "
                       "cancels in flight (counted one by one; each cancel gets exactly one answer), "
                       "unknown about the new order / about a cancel, final); "
                       "STATE_UNKNOWN is held until a report that settles it",
        "forced_orders": "the strategy learns of a forced order only when its first notice is delivered",
        "history_limit": "per event type the latest N..2N delivered events are kept; the overall history "
                         "is exactly what the types keep; a read reaching into a dropped part raises "
                         "HistoryTruncatedError",
        "scope": "the guarantees hold for the context and everything reachable from it by attribute "
                 "access; the strategy runs in the engine's process, so interpreter introspection "
                 "(call stack, gc) is not covered -- the core does not sandbox strategy code",
    },
    "lifecycle": {
        "failed_after_escaped_exception": True,
        "rule": "any exception that escapes CoreEngine.step() (a core error, or one raised by the "
                "strategy or a socket) is re-raised unchanged and leaves the engine FAILED; a FAILED "
                "engine refuses step(), run() and result() with EngineFailedError (cause = the original "
                "exception, also CoreEngine.failure); a half-updated state is never run on or reported",
        "atomic_step": False,
        "why_not_atomic": "the strategy and the plug-ins own state the core cannot roll back",
        "reentry": "step(), run() or result() called from inside a step of the same engine raises "
                   "EngineReentryError and changes nothing",
    },
    "channel_payloads": {
        "rule": "what crosses a path (an order request, a notice) is a value when it is made: "
                "OrderRequest.extra holds plain data made immutable at construction (read back with "
                "extra_dict() as a fresh copy); notice text fields are str; nothing the strategy or the "
                "venue can change later is shared between them",
        "plain_data": PLAIN_DATA_RULE,
    },
    "run_settings": {
        "time_span_ns": "optional (first_ns, last_ns), both included; given, an input event with its "
                        "exchange or received time outside it raises TimestampUnitError when read "
                        "from its stream; not given, nothing is checked and defaults_used lists "
                        "'time_span'",
        "end_time_ns": "optional; an int64 of ns; one before the first entry raises TimestampUnitError",
        "history_limit": "optional positive int; see visibility.history_limit",
    },
    "ordering": ORDERING_RULE,
    "strategy_api": list(STRATEGY_API),
    "sockets": {name: socket_methods(proto) for name, proto in SOCKETS.items()},
    "implicit_cost": "none (a fill without a cost model raises MissingCostModelError)",
    "resend_on_state_unknown": False,
    "forced_order_id_prefix": FORCED_ID_PREFIX,
}

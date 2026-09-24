"""Machine-readable statement of what the core guarantees, built from the
code objects themselves (not hand-written copies), so it cannot drift from
the implementation. Item 8 (repro) can store it in a run record; the
battery can read it instead of trusting prose."""
from __future__ import annotations

from .api import FORCED_ID_PREFIX, STRATEGY_API, CancelRequest, OrderRequest
from .events import ALL_EVENT_CLASSES, MARKET_EVENT_TYPES, NOTICE_EVENT_TYPES, SOURCE_EVENT_TYPES, EventType
from .interfaces import REPORT_CLASSES, SOCKETS, FillNotice, socket_methods
from .ordering import ORDERING_RULE
from .time import TIME_CONTRACT
from .values import FIELD_RULE, PLAIN_DATA_RULE
from .window import POSITION_RULE

CORE_VERSION = "core-9"

# Every class whose instances cross a path of the core (values.py): each
# makes every field a built-in value when it is made, and is slotted.
PATH_CARRIERS: tuple[type, ...] = (
    OrderRequest,
    CancelRequest,
    *REPORT_CLASSES,
    FillNotice,
    *ALL_EVENT_CLASSES,
)

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
                    "until_ns) raises LookAheadError; a history read returns DeliveredEvents, which knows "
                    "its place in what the read reads (AnswerPlace); an index or an explicit slice bound "
                    "naming a position outside the answer (position_rule) raises by what that position is "
                    "there: FuturePositionError (a LookAheadError) for an event not delivered yet, "
                    "OutsideAnswerError / DroppedPositionError / BeforeFirstEventError for the past; "
                    "context revoked on return",
        "position_rule": {
            "max_position_by_role_as_offset_from_len": dict(POSITION_RULE),
            "negative_bounds": "a negative index counts back from the newest and one before the oldest "
                               "(< -len) raises like any position outside the answer; negative slice bounds "
                               "are cut at the answer's ends, as for any tuple",
            "error": "decided by the NAMED position (i0-r6-01): answer position q is position "
                     "u = first + q * step of what the read reads (DeliveredEvents.place); u >= delivered "
                     "(the count delivered when the answer was made) -> FuturePositionError (an IndexError "
                     "and a LookAheadError); 0 <= u < delivered -> OutsideAnswerError (delivered, outside "
                     "the answer); u < 0 -> DroppedPositionError if history_limit dropped events there, "
                     "else BeforeFirstEventError (nothing there); these three are OutsideAnswerErrors, "
                     "not LookAheadErrors; of two slice bounds outside, one naming an event not delivered "
                     "yet is reported first; each error carries answer_position, read_position, delivered",
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
                 "(call stack, gc) is not covered -- the core does not sandbox strategy code; nor is a "
                 "sender that bypasses a frozen carrier of its own with object.__setattr__ after handing "
                 "it over -- the strategy's and the account's requests are rebuilt when they enter a path, "
                 "so theirs reach no one; an event source's events are not (a copy per event would cost "
                 "about a sixth of the engine's time per event), and the strategy only ever gets a copy "
                 "made at delivery",
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
        "rule": "what crosses a path (an order or cancel request, a venue report, a fill notice, an "
                "event) is a value when it is made: every field is the built-in type itself (str, float, "
                "int, bool, frozen plain data), never an object or a subclass instance of the sender's; "
                "the carrier classes are slotted (nothing can be attached); each path takes the core's own "
                "carrier classes themselves (a subclass is refused); the strategy's and the account's "
                "requests are rebuilt when they enter the path, so no sender holds what its receiver reads",
        "fields": FIELD_RULE,
        "plain_data": PLAIN_DATA_RULE,
        "carriers": [c.__name__ for c in PATH_CARRIERS],
        "plug_in_answers": "what the engine takes from a plug-in or the caller -- a delay (int), a fee "
                           "(float), a pre-trade reject reason (str), a stream name (str) -- is read once, "
                           "when it is returned, as the built-in value (values.py); none of their methods "
                           "runs later",
        "type_decisions": "every decision on the type of a value a sender hands the core (a field, a "
                          "plug-in's answer, a source's event, a read argument, a run setting) reads the "
                          "value's REAL type (values.is_a: issubclass(type(x), C)), never what the object "
                          "claims through __class__; a refusal is the error type of the place it enters "
                          "(OrderApiError, VenueProtocolError, EventValidationError, TimestampUnitError, "
                          "LatencyModelError, CostModelError, AccountSocketError, SourceEventTypeError), "
                          "naming the real type in full",
    },
    "run_settings": {
        "time_span_ns": "optional (first_ns, last_ns), both included; given, an input event with its "
                        "exchange or received time outside it raises TimestampUnitError when read "
                        "from its stream; not given, nothing is checked and defaults_used lists "
                        "'time_span'. It checks the two times of INPUT events only (their unit); "
                        "it does not bound the run: timers the strategy sets, notices and request "
                        "arrivals may lie after last_ns (end the run with end_time_ns)",
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

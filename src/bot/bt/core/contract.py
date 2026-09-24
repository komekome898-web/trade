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
from .window import POSITION_RULE, POSITION_RULE_TEXT

CORE_VERSION = "core-11"

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
            "range_by_role": {role: list(v) for role, v in POSITION_RULE.items()},
            "range_by_role_is": "(lowest c, highest c as an offset from len) in the answer's coordinate",
            "bounds": POSITION_RULE_TEXT,
            "error": "decided by the NAMED position (i0-r6-01): answer position q is position "
                     "u = first + q * step of what the read reads (DeliveredEvents.place); u >= delivered "
                     "(the count delivered when the answer was made) -> FuturePositionError (an IndexError "
                     "and a LookAheadError); 0 <= u < delivered -> OutsideAnswerError (delivered, outside "
                     "the answer); -dropped <= u < 0 -> DroppedPositionError (a delivered event history_limit "
                     "dropped), u < -dropped -> BeforeFirstEventError (nothing there); these three are OutsideAnswerErrors, "
                     "not LookAheadErrors; of two slice bounds outside, one naming an event not delivered "
                     "yet is reported first; each error carries answer_position, read_position, delivered",
            "last_k": "a slice bound naming a position before the oldest event of an answer is refused, "
                      "not cut: with fewer than k events delivered, visible_events()[-k:] raises "
                      "BeforeFirstEventError (or DroppedPositionError under history_limit) instead of "
                      "returning the shorter answer (round 8); 'the last k events, or all of them if fewer "
                      "were delivered' is visible_events(n=k) (event_type, since_ns and until_ns combine "
                      "with it)",
            "applies_to": "every answer of a history read (DeliveredEvents: [], index()), the windows a "
                          "context holds (EventWindow: [], index()) and the core's lists behind them, reachable "
                          "through a window's private attribute (history.DeliveredList: [], index(); changing "
                          "one through its own behaviour is refused at every entry -- attribute assignment and "
                          "deletion, __init__ on a made list, every list method that changes the contents -- "
                          "and the core never reads one back); not to a base class's method called on the core's object "
                          "(tuple.__getitem__(answer, key), list.__getitem__(list, key)), which bypasses the "
                          "object's own behaviour like object.__setattr__; nor to a plain tuple the strategy "
                          "makes from an answer (tuple(answer), answer + other): it has no place",
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
                         "HistoryTruncatedError, and so does an empty answer whose until_ns cut lies among "
                         "the dropped events (its place could not be stated); an answer's place counts the "
                         "dropped events before its oldest kept one (AnswerPlace.dropped)",
        "scope": "the guarantees hold for the context and everything reachable from it by attribute "
                 "access; the strategy runs in the engine's process, so interpreter introspection used "
                 "to reach the engine's own state (call stack, gc of the engine) is not covered -- the "
                 "core does not sandbox strategy code; nor is writing memory (ctypes), nor changing the "
                 "core's CODE (its classes, functions and modules, reachable as __class__ or "
                 "__func__.__globals__: that changes the program, not its state), nor calling a base "
                 "class's method on an object of the core's (tuple.__getitem__(answer, key), which "
                 "bypasses the answer's own behaviour). A sender changing what it handed over, by any "
                 "means (object.__setattr__ on a frozen carrier's slots or __class__, a container's "
                 "contents, a Fraction's slots), IS covered: the core never keeps a sender's object "
                 "(channel_payloads.ownership). So is the strategy changing ANY state object it can "
                 "reach, by any means including a base class's methods (list.append on its order "
                 "registry, object.__setattr__ on a slot of its port or of an event in its history): "
                 "the core decides, sends and reports nothing from those objects (ownership), so such a "
                 "change reaches only what the strategy itself reads -- and what it sends, through the "
                 "outbox, under the API's rules",
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
                "event) is a value when it is made: every field is a new object of the built-in type "
                "itself (str, float, int, bool, frozen plain data), never an object, a subclass instance "
                "or the very object of the sender's; the carrier classes are slotted (nothing can be "
                "attached); each path takes the core's own carrier classes themselves (a subclass is "
                "refused)",
        "ownership": "what the core decides from, sends and reports is built from objects only the core "
                     "holds (round 9, i0-r8-01): the facts of the strategy's orders live in the core's "
                     "own order book (never handed out), the history's retention in the core's own "
                     "records (delivery number, received time, type), the queue, ledger and lists in the "
                     "engine. A sender's carrier (a source's event, the strategy's request, a fill "
                     "model's report, the account's forced order) is made again by its constructor when "
                     "the core takes it, and never handed on; every receiver (latency model, fill model, "
                     "account, cost model, the strategy, the caller's result, order views included -- "
                     "the strategy's order views are new objects the core writes at every change) gets a "
                     "copy of its own "
                     "(values.copy_carrier), so what one receiver changes in its copy reaches no sender, "
                     "no other receiver and not the core. What the strategy reaches is its own: its "
                     "context, windows and history lists (the core writes the lists and reads nothing "
                     "back), its order port's registry (copies the core writes from its book and never "
                     "reads) and its outbox -- the one object the core reads, once, when the callback "
                     "returns, through the core's own reference: each message is the arguments of one "
                     "API call (('new', OrderRequest, t), ('cancel', CancelRequest, t), ('timer', at_ns, "
                     "tag); t is never used, the callback's time is), read by its real types, and every "
                     "rule of that call is applied again against the core's book and time "
                     "(api.check_new_id, api.check_timer), so a message written around place_order / "
                     "cancel_order / set_timer has exactly that call's effect, or is refused with "
                     "OrderApiError (as is a port whose outbox or registry was replaced)",
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

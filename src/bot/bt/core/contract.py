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

CORE_VERSION = "core-14"

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
                         "is exactly what the types keep; the facts of every dropped event (delivery number, "
                         "received time: two int64, 16 bytes per dropped event) are kept, the events are not "
                         "(the limit bounds the events held, not these facts, which grow by 16 bytes with every "
                         "dropped event for the whole run, plus one chunk per drop (an array of about 64 bytes "
                         "plus the facts) until the strategy's next read that needs them folds the chunks in, "
                         "inside that read: round 12; the facts stay in array('q') because the alternative "
                         "that exports no buffer costs 5 times as much -- measured with tracemalloc over "
                         "200,000 facts on CPython 3.11: two array('q') 16.9 bytes per fact, two lists of int "
                         "88.2 bytes per fact (round 12, measured again in round 13)); a read raises HistoryTruncatedError exactly when its "
                         "answer without the limit holds a dropped event, naming the newest such event and how "
                         "to read kept events only (a since_ns after it, or n <= the number of its newest events "
                         "that are kept); every answer returned, empty or not, is the answer without the limit; "
                         "its place is in the kept events of its scope with the dropped deliveries before the "
                         "oldest kept one at -dropped..-1 (AnswerPlace.dropped); an empty answer lies where its "
                         "range was cut on that line, which may be among or before the dropped positions "
                         "(round 10)",
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
                 "registry, object.__setattr__ on a slot of its port or of an event in its history) "
                 "and assigning an object another class (__class__ of the same layout), and so is "
                 "what it PLANTS there without changing a value (a key of its own in a dict or set that "
                 "compares as it likes, a view that holds an array's buffer): the core decides, sends "
                 "and reports nothing from those objects (ownership) and writes them only by list.append "
                 "on lists it made (round 12), so such a change reaches only what the strategy itself "
                 "reads -- and what it sends, through the outbox, under the API's rules. The rule for "
                 "every party (the strategy, a socket, a stream; round 12): outside that party's own "
                 "call (the core's call of its on_event -- the lookup of on_event included, round 10 -- "
                 "of a socket's method, of a stream's __next__), what the core does with what the party "
                 "handed over, raised or can reach is decided only by objects the core made and no one "
                 "else reaches, or by static (C) classes: a class the party wrote is never hashed, "
                 "compared with ==, looked up in a hash table or asked for an attribute the usual way, "
                 "an answer is taken by values.settle / take_int / take_float / take_items (its truth, "
                 "length, iteration and conversion are never asked of it), so no code the party wrote "
                 "runs there and a refusal is always the entry's own error. Nor does the core run code "
                 "of an exception a party raised: a FAILED engine describes it from its facts "
                 "(values.exception_text; round 11). Not covered: finalizers (__del__, weakref "
                 "callbacks) of the strategy's objects, which the interpreter runs whenever it frees "
                 "them, inside a step too -- they reach only what the strategy reaches, which the core "
                 "does not decide from; the __subclasscheck__ of the metaclass of an exception a party "
                 "raised, which the interpreter itself asks while the exception propagates through any "
                 "frame (the core re-raises the exception unchanged, lifecycle); classes derived from or "
                 "registered with the numbers ABCs that carry a __subclasshook__ or a metaclass hook, "
                 "which the ABC machinery consults when the core asks whether a static (C) number class "
                 "is a number (defining classes changes the program)",
    },
    "lifecycle": {
        "failed_after_escaped_exception": True,
        "rule": "any exception that escapes CoreEngine.step() (a core error, or one raised by the "
                "strategy, a socket or an input stream) is re-raised unchanged and leaves the engine "
                "FAILED; a FAILED engine refuses step(), run() and result() with EngineFailedError (cause "
                "= the original exception, also CoreEngine.failure), whose text is made from the "
                "failure's facts only -- its real type named without looking anything up in its class "
                "(values.class_parts: type's own slot, and its dict walked, not searched; round 12) and "
                "its arguments that are a str, int, float, bool or None themselves "
                "(values.exception_text) -- so no code of the failure (its __str__, __repr__, an args "
                "property, its metaclass, the keys of its class's dict) runs and the refusal is always "
                "EngineFailedError (round 11, round 12); a half-updated state is never run on or "
                "reported",
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
                     "copy of its own (values.copy_carrier), so what one receiver changes in its copy "
                     "reaches no sender, no other receiver and not the core. Everything the strategy can "
                     "reach that outlives a callback -- its order port, its copies of its order views "
                     "(registry), its outbox, its history lists with the event copies in them and the "
                     "facts of the dropped events -- is kept in ONE holder of the engine (_StrategySide, "
                     "round 10, i0-r9-02); nothing of the core's own state refers into it. The core "
                     "WRITES it only by list.append on lists it made -- the views it shows (a list the "
                     "strategy's registry is brought up to date from inside the strategy's own calls, "
                     "api._bring_up; it holds the views shown since the strategy's last call of its "
                     "order port), the event copies of the history lists, one chunk of facts per drop "
                     "(folded into the arrays the strategy's reads use inside those reads, "
                     "history.read_dropped) -- and by making new lists: whatever the strategy did to "
                     "what it reaches, such a write runs none of its code and cannot fail (round 12, "
                     "i0-r11-01 / i0-r11-03: a dict write compares the keys the strategy put there, an "
                     "array cannot grow while a view of it is held). It never acts on those objects "
                     "through their classes (no attribute read or write, no method of theirs), and reads "
                     "nothing the strategy can reach but the outbox: once, when the callback returns, "
                     "through the core's own reference. (The holder also keeps, for the core, its lists "
                     "of references to the event copies and its references to the dropped facts' pending "
                     "lists, which nothing the strategy reaches refers to; the core slices the first to "
                     "make new history lists when it drops events and never reads an event copy.) The "
                     "context holds values, the frozen current event, windows and functions; its calls "
                     "are methods bound to one tuple made for the callback (the port, the registry, the "
                     "outbox, the callback's time, alive), which cannot be changed, so replacing the "
                     "port's attributes changes nothing that is sent; the context and its windows are "
                     "revoked through alive, a cell only the engine flips; order() / open_orders() / "
                     "visible_events() return new objects at every call. Each outbox message is the "
                     "arguments of one API call (('new', OrderRequest, t), ('cancel', CancelRequest, t), "
                     "('timer', at_ns, tag); t is never used, the callback's time is), read by its real "
                     "types; every value in it is settled first (values.settle: its type decided by "
                     "identity, made anew as the built-in type itself by the base type's own methods, a "
                     "number of a static C class converted by that class's C code; a value whose reading "
                     "needs code the strategy wrote -- a number whose class was written in Python -- or "
                     "that is not plain data is refused with OrderApiError: the API's calls convert such "
                     "values inside the callback, the core does not after it returned), and every rule of "
                     "that call is "
                     "applied again against the core's book and time (api.check_new_id, "
                     "api.check_timer), so a message written around place_order / cancel_order / "
                     "set_timer has exactly that call's effect, or is refused with OrderApiError",
        "fields": FIELD_RULE,
        "plain_data": PLAIN_DATA_RULE,
        "carriers": [c.__name__ for c in PATH_CARRIERS],
        "plug_in_answers": "what the engine takes from a plug-in after its call returned -- a delay "
                           "(int), a fee (float), a pre-trade reject reason (str), the reports of a fill "
                           "model and the forced orders of the account (a Sequence: a list or a tuple, "
                           "read by the base type's own iterator, its truth and length never asked) -- is "
                           "taken once, as the built-in value, by values.settle (take_int, take_float, "
                           "take_items, as_text; round 12): a built-in value or a subclass of one read by "
                           "the base type, a number of a static C class (numpy's) converted by its C code; "
                           "a number whose class was written in Python is refused with the entry's error "
                           "(its conversion is the plug-in's code; convert it inside the call), and a "
                           "carrier the plug-in handed over is made again from its slots settled first "
                           "(values.rebuild_carrier); none of their methods runs; what the caller hands "
                           "the engine's constructor (a stream name) is read inside the caller's call",
        "type_decisions": "every decision on the type of a value a sender hands the core (a field, a "
                          "plug-in's answer, a source's event, a read argument, a run setting) reads the "
                          "value's REAL type (values.is_a: issubclass(type(x), C)), never what the object "
                          "claims through __class__, and compares classes by identity only (values.is_one_of, "
                          "derives, IdTable: a class is never hashed, compared with == or looked up; round "
                          "12); a type's names in a text are read without a lookup (values.type_name / "
                          "class_parts: no code of the class, its metaclass or its dict's keys runs), and a "
                          "socket's names in result().models once, when the engine is built; a refusal is "
                          "the error type of the place it enters "
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

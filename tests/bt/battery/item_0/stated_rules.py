"""Same-time order rules for the P0-5 scenes, one per target, fixed by the
scene keeper BEFORE any run (round r5-1, critic i0-r4-05).

The P0-5 value scene asks whether a target processes same-time events "in
the order its own written rule gives" (fixed requirements, P0-5). The rule
differs per target, so the correct order differs per target. Until round
r4-1 each adapter wrote the rule applied to the input (`predicted`) itself,
at run time, and the runner only compared; now:

  * each target's rule is copied here from the target's documents or public
    code: where it is written (file plus a NAME -- symbol, section heading or
    URL -- never a line number alone), the words, and the recipe that
    applies it (which key compares the heads of the input streams);
  * `FIXED_PREDICTED` holds, written by hand from the words, the order the
    rule gives for the input of p5-same-time-twice; `test_battery_item0.py`
    checks that the recipe reproduces it (two derivations that must agree);
  * the runner (`run_battery.py`) applies the recipe to each scene's own
    input -- for p5-hand-over-order to each of the scene's 24 hand-over
    orders, not to what an adapter reports -- and compares with what the
    target delivered. Adapters report only what they observed.

A target without an entry has no written rule for events of different
types at one time (its adapter's detail says where it was looked for); it
cannot satisfy "follows its stated rule".

No target name may appear in DEFINITIONS.md (the blind judges read it), so
this table lives here and in ROOTCAUSE_r5-1.md only. Standard library only
(adapters in the survey venvs import TYPE_PRIORITY from here).
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field

# Basana: the scene keeper's setting of the public `priority` argument of each
# event source (one source per event type; all different, so the heap's third
# key id(source) never decides). The Basana adapter reads it from here, so the
# setting the target runs with and the rule it is graded by cannot differ.
TYPE_PRIORITY = {"bar": 60, "trade": 50, "book_snapshot": 45, "book_delta": 40, "funding": 30, "liquidation": 20}


@dataclass(frozen=True)
class StatedRule:
    source: str   # where the rule is written: file + a name (symbol / heading) or URL
    quote: str    # the words
    form: str     # "multi_input" (named streams handed separately) / "single_input" (one concatenated input)
    recipe: str   # "head_merge" / "stable_by_time"
    params: dict = field(default_factory=dict)


# The new implementation's rule: copied from src/bot/bt/core/ordering.py, the
# public dict ORDERING_RULE["source_merge"] and the module description's
# section "Merging input streams". test_battery_item0.py compares this copy
# with the core's ORDERING_RULE["source_merge"] read by name, so a changed
# rule in the core fails loudly instead of silently leaving this copy behind.
NEW_IMPL_SOURCE_MERGE = {
    "compare_heads_by": ["exchange_time_ns", "TYPE_ORDER", "stream name (sorted())"],
    "type_order": ["LIQUIDATION", "FUNDING", "BOOK_SNAPSHOT", "BOOK_DELTA", "TRADE", "BAR", "CLOCK"],
    "inside_one_stream": "the stream's own order, whatever the types",
}

_NEW = StatedRule(
    source=("src/bot/bt/core/ordering.py の ORDERING_RULE[\"source_merge\"] と、モジュールの説明の節 "
            "\"Merging input streams (phase 0 positions)\""),
    quote=("Several input streams ... are merged by comparing the streams' NEXT events: "
           "(exchange_time_ns, place of the event's type in TYPE_ORDER, stream name). The smallest head is taken, "
           "then that stream's next event becomes its head. So a stream's own order is always kept, and only between "
           "different streams at the same exchange time does the type order decide (liquidation, funding, book snapshot, "
           "book delta, trade, bar, clock ...), then the stream name (`sorted()` order, not the order the mapping was "
           "handed over)."),
    form="multi_input", recipe="head_merge",
    params={"key": ["ts", "type_rank", "stream_name_rank"],
            "type_order": [t.lower() for t in NEW_IMPL_SOURCE_MERGE["type_order"]]})

STATED_RULES: dict[str, StatedRule] = {
    "new_impl": _NEW,
    "mutant": _NEW,  # the canary is the new implementation with one defect; it is graded by the same rule
    "opp_basana": StatedRule(
        source=("basana 1.11 basana/core/dispatcher/base.py の EventDispatcher が事象を積む heapq.heappush と、"
                "basana/core/event.py の EventSource.__init__ の引数 priority"),
        quote=("heapq.heappush(self._event_heap, (event.when, -source.priority, id(source), source, event)) / "
               "def __init__(self, producer: Optional[Producer] = None, priority: int = DEFAULT_EVENT_SOURCE_PRIORITY)"),
        form="multi_input", recipe="head_merge",
        params={"key": ["ts", "minus_priority"], "priority": TYPE_PRIORITY}),
    "opp_hftbacktest": StatedRule(
        source=("hftbacktest 2.4.4 hftbacktest/data/validation.py の correct_event_order の説明と "
                "https://hftbacktest.readthedocs.io/en/latest/data.html"),
        quote=("Corrects exchange timestamps that are reversed by splitting each row into separate events. These events "
               "are then ordered by both exchange and local timestamps through duplication. (the sort indexes are numpy "
               "argsort kind='stable', so rows with equal times keep the input array's order)"),
        form="single_input", recipe="stable_by_time"),
    "opp_mihircoding_lob": StatedRule(
        source=("mihircoding/limitOrderBook(commit 6cc0536)src/latency.py の MessageBus と Message の説明"),
        quote=("`MessageBus` is a priority queue keyed by (arrival, sequence). The sequence number is the tie-break ... "
               "A pending action, ordered by (arrival, sequence)."),
        form="single_input", recipe="stable_by_time"),
    # round r7-1: the reproduced LEAN now takes part in the P0-5 scenes (it has three types).
    # Its data of one time goes into one Slice; Slice.AllData keeps the order in which
    # SubscriptionSynchronizer.Sync visited the subscriptions (TimeSliceFactory.cs 184, Slice.cs 305),
    # and the subscriptions are enumerated sorted (SubscriptionCollection.cs 123-126, 213-227).
    # SecurityType and Symbol are the same for every subscription of a scene (one CryptoFuture
    # symbol), so the key left is the TickType (Common/Global.cs 512-528: Trade, Quote,
    # OpenInterest); the data type -> TickType of each subscription is DataManager.cs 755-773
    # (TradeBar / Tick of trades: Trade; MarginInterestRate: Quote). Subscriptions with the same
    # key are enumerated in the order of the ConcurrentDictionary, which the source does not fix:
    # the rule does not decide between them (RuleDoesNotDecide).
    "repro_lean52": StatedRule(
        source=("QuantConnect/Lean 856327ff Engine/DataFeeds/SubscriptionCollection.cs の SortSubscriptions と、"
                "Engine/DataFeeds/SubscriptionSynchronizer.cs の Sync、Engine/DataFeeds/TimeSliceFactory.cs の Create"),
        quote=("_subscriptionsByTickType = _subscriptions.Select(x => x.Value).OrderBy(x => x.Configuration.SecurityType)"
               ".ThenBy(x => x.Configuration.TickType).ThenBy(x => x.Configuration.Symbol).ToList(); / "
               "foreach (var subscription in subscriptions) { ... while (subscription.Current != null && "
               "subscription.Current.EmitTimeUtc <= frontierUtc) { ... packet.Add(subscription.Current.Data); ... } } / "
               "allDataForAlgorithm.Add(baseData);"),
        form="multi_input", recipe="head_merge",
        params={"key": ["ts", "tick_type_rank"], "tick_type": {"trade": 0, "bar": 0, "funding": 1}}),
}

# p5-same-time-twice, written by hand from each quote (round r7-1: the input is
# built from each target's own types, scenes.for_target_types; the types each
# target delivered in its P0-3 scenes are listed here with the order). The
# events are one per stream A, B, C, ... at T0 + 1 day, handed over A, B, C, ...
#   new_impl  -- 6 types, the scene's first four: trade, book_snapshot, book_delta, bar;
#                type order liquidation < funding < book_snapshot < book_delta < trade < bar;
#   basana    -- 4 types, the same four; -priority: bar (60), trade (50), book_snapshot (45), book_delta (40);
#   repro_lean52 -- 3 types trade, bar, funding; trade and bar are both TickType Trade: a tie
#                the source does not decide (None);
#   hftbacktest (1 type) and mihircoding/limitOrderBook (0 types) do not get this scene
#   (fewer than 2 types); their rules stay for the record.
_T = 1_700_006_400_000_000_000 + 86_400 * 1_000_000_000
FIXED_PREDICTED: dict[str, tuple[list[str], list[list] | None]] = {
    "new_impl": (["trade", "book_snapshot", "book_delta", "bar", "funding", "liquidation"],
                 [["book_snapshot", _T], ["book_delta", _T], ["trade", _T], ["bar", _T]]),
    "mutant": (["trade", "book_snapshot", "book_delta", "bar", "funding", "liquidation"],
               [["book_snapshot", _T], ["book_delta", _T], ["trade", _T], ["bar", _T]]),
    "opp_basana": (["trade", "book_snapshot", "book_delta", "bar"],
                   [["bar", _T], ["trade", _T], ["book_snapshot", _T], ["book_delta", _T]]),
    "repro_lean52": (["trade", "bar", "funding"], None),
}


class RuleDoesNotDecide(Exception):
    """The rule leaves two heads tied (e.g. equal priorities): no order follows from it."""


def _head_key(rule: StatedRule, ev: dict, name: str, names_sorted: list[str]) -> tuple:
    parts = []
    for k in rule.params["key"]:
        if k == "ts":
            parts.append(int(ev["ts_ns"]))
        elif k == "type_rank":
            parts.append(rule.params["type_order"].index(ev["kind"]))
        elif k == "stream_name_rank":
            parts.append(names_sorted.index(name))
        elif k == "minus_priority":
            parts.append(-rule.params["priority"][ev["kind"]])
        elif k == "tick_type_rank":
            parts.append(rule.params["tick_type"][ev["kind"]])
        else:  # pragma: no cover - a recipe key this module does not know
            raise ValueError(f"unknown key part {k!r}")
    return tuple(parts)


def predicted(rule: StatedRule, streams: dict[str, list[dict]], hand_over: list[str]) -> list[list]:
    """The (kind, ts) order the rule gives for these streams handed over in this order."""
    if rule.recipe == "stable_by_time":
        flat = [e for name in hand_over for e in streams[name]]
        return [[e["kind"], int(e["ts_ns"])] for e in sorted(flat, key=lambda e: int(e["ts_ns"]))]
    if rule.recipe == "head_merge":
        names_sorted = sorted(streams)
        pos = {n: 0 for n in hand_over}
        heap: list = []
        for n in hand_over:
            if streams[n]:
                heapq.heappush(heap, (_head_key(rule, streams[n][0], n, names_sorted), n))
        out = []
        while heap:
            key, n = heapq.heappop(heap)
            if heap and heap[0][0] == key:
                raise RuleDoesNotDecide(f"heads {n!r} and {heap[0][1]!r} tie on {key}")
            ev = streams[n][pos[n]]
            out.append([ev["kind"], int(ev["ts_ns"])])
            pos[n] += 1
            if pos[n] < len(streams[n]):
                heapq.heappush(heap, (_head_key(rule, streams[n][pos[n]], n, names_sorted), n))
        return out
    raise ValueError(f"unknown recipe {rule.recipe!r}")  # pragma: no cover


def rule_for(target: str | None) -> StatedRule | None:
    return STATED_RULES.get(target or "")


if __name__ == "__main__":  # print the table (for the materials person and the critic)
    import json
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from scenes import SCENES
    from scenes import for_target_types
    base = next(s for s in SCENES if s.id == "p5-same-time-twice")
    for t, r in STATED_RULES.items():
        types = FIXED_PREDICTED.get(t, (None, None))[0]
        sc = for_target_types(base, types) if types else None
        try:
            p = predicted(r, sc.input["streams"], sc.input["hand_over_order"]) if sc else "この場面に出ない(型が 2 種未満)"
        except RuleDoesNotDecide as exc:
            p = f"規則が決めない: {exc}"
        print(json.dumps({"target": t, "form": r.form, "source": r.source, "types": types, "predicted": p}, ensure_ascii=False))

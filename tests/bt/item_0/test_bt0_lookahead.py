"""The strategy can only see events it has received (received_time_ns <=
now), by construction -- checked through public AND private paths."""
import random

import pytest

from bot.bt.core import (
    CoreEngine,
    Event,
    EventType,
    OrderRequest,
    StaleContextError,
    Strategy,
    ZeroLatency,
)
from bot.bt.core.testing import ImmediateFillModel
from bot.bt.core import NullCostModel

from bt0_util import MS, SEC, T0, Recorder, bar, trade


def test_known_answer_probe_at_index_3_sees_four_bars_max_103():
    bars = [bar(T0 + i * 60 * SEC, 100.0 + i) for i in range(6)]
    probe = {}

    def act(event, ctx):
        if event is bars[3] or (event.EVENT_TYPE is EventType.BAR and event.close == 103.0):
            vis = ctx.visible_events(EventType.BAR)
            probe["count"] = len(vis)
            probe["max"] = max(e.close for e in vis)

    CoreEngine(Recorder(act), bars).run()
    assert probe == {"count": 4, "max": 103.0}


class _Snoop(Strategy):
    """Walks everything reachable from ctx (public and private attributes,
    bound-method owners, containers) and records any Event later than now."""

    def __init__(self):
        self.violations = []
        self.checked = 0

    def on_event(self, event, ctx):
        now = int(ctx.now_ns)
        for e in ctx.visible_events():
            if int(e.received_time_ns) > now:
                self.violations.append(("public", e))
        for e in _reachable_events(ctx):
            self.checked += 1
            if int(e.received_time_ns) > now:
                self.violations.append(("reachable", e))


def _reachable_events(root, limit=20000):
    seen = set()
    stack = [root]
    found = []
    while stack and len(seen) < limit:
        obj = stack.pop()
        if id(obj) in seen or isinstance(obj, (str, bytes, int, float, type)) or obj is None:
            continue
        seen.add(id(obj))
        if isinstance(obj, Event):
            found.append(obj)
            continue
        if isinstance(obj, dict):
            stack.extend(obj.keys())
            stack.extend(obj.values())
            continue
        if isinstance(obj, (list, tuple, set, frozenset)):
            stack.extend(obj)
            continue
        owner = getattr(obj, "__self__", None)
        if owner is not None:
            stack.append(owner)
        if hasattr(obj, "__dict__"):
            stack.extend(vars(obj).values())
        for slot in getattr(type(obj), "__slots__", ()):
            if hasattr(obj, slot):
                stack.append(getattr(obj, slot))
    return found


def _random_run(seed, n=200):
    rng = random.Random(seed)
    events = []
    t = T0
    for i in range(n):
        t += rng.choice([0, 0, 1, 5 * MS, SEC])
        recv = t + rng.choice([0, 0, 3 * MS, 50 * MS])
        if rng.random() < 0.5:
            events.append(trade(recv, 100.0 + rng.random(), exch=t))
        else:
            events.append(bar(recv, 100.0 + rng.random(), exch=t))
    return events


class _JitterFeed(ZeroLatency):
    def __init__(self, seed):
        self.rng = random.Random(seed)

    def feed_delay_ns(self, event):
        return self.rng.choice([0, 1, 7 * MS, 2 * SEC])


@pytest.mark.parametrize("seed", range(5))
def test_nothing_reachable_from_ctx_is_in_the_future(seed):
    snoop = _Snoop()
    CoreEngine(snoop, _random_run(seed), latency_model=_JitterFeed(seed)).run()
    assert snoop.checked > 0
    assert snoop.violations == []


def test_ctx_does_not_reference_the_engine_even_privately():
    holder = {}

    class _Grab(Strategy):
        def on_event(self, event, ctx):
            holder.setdefault("reach", []).append(
                [o for o in _reachable_objects(ctx) if isinstance(o, CoreEngine)]
            )

    engine = CoreEngine(_Grab(), [trade(T0), trade(T0 + 1)])
    engine.run()
    assert holder["reach"] == [[], []]


def _reachable_objects(root, limit=20000):
    seen = {}
    stack = [root]
    while stack and len(seen) < limit:
        obj = stack.pop()
        if id(obj) in seen or isinstance(obj, (str, bytes, int, float, type)) or obj is None:
            continue
        seen[id(obj)] = obj
        if isinstance(obj, dict):
            stack.extend(obj.values())
        elif isinstance(obj, (list, tuple, set, frozenset)):
            stack.extend(obj)
        else:
            owner = getattr(obj, "__self__", None)
            if owner is not None:
                stack.append(owner)
            if hasattr(obj, "__dict__"):
                stack.extend(vars(obj).values())
            for slot in getattr(type(obj), "__slots__", ()):
                if hasattr(obj, slot):
                    stack.append(getattr(obj, slot))
    return list(seen.values())


def test_source_is_pulled_lazily_so_future_events_do_not_exist_yet():
    pulled = []

    def source():
        for i in range(10):
            e = trade(T0 + i * SEC, 100.0 + i)
            pulled.append(e)
            yield e

    counts = []
    CoreEngine(Recorder(lambda ev, ctx: counts.append(len(pulled))), source()).run()
    # When the strategy sees event k (0-based), at most k+2 events have been
    # read from the source: the ones delivered plus one lookahead to know
    # nothing else shares the instant.
    assert all(c <= k + 2 for k, c in enumerate(counts)), counts


def test_stale_context_cannot_read_history_or_act():
    kept = []
    CoreEngine(Recorder(lambda ev, ctx: kept.append(ctx)), [trade(T0), trade(T0 + 1)]).run()
    stale = kept[0]
    assert stale.revoked
    assert stale.now_ns == T0  # the instant it was built for stays readable
    for call in (
        lambda: stale.visible_events(),
        lambda: stale.last(EventType.TRADE),
        lambda: stale.place_order(OrderRequest("buy", "market", 1.0)),
        lambda: stale.cancel_order("core-1"),
        lambda: stale.open_orders(),
        lambda: stale.set_timer(T0 + 10),
    ):
        with pytest.raises(StaleContextError):
            call()
    window = stale._StrategyContext__visible_events
    assert list(window._log) == []


def test_fill_model_never_sees_market_data_before_its_exchange_time():
    fm = ImmediateFillModel()
    events = _random_run(3)
    CoreEngine(Recorder(), events, fill_model=fm, cost_model=NullCostModel(),
               latency_model=_JitterFeed(3)).run()
    times = [t for t, _ in fm.market_events_seen]
    assert times == sorted(times)
    assert all(t == int(e.exchange_time_ns) for t, e in fm.market_events_seen)
    assert len(fm.market_events_seen) == len(events)


def test_strategy_sees_event_at_received_time_not_exchange_time():
    e = trade(T0 + 5 * MS, exch=T0)
    rec = Recorder(lambda ev, ctx: rec.now.append(int(ctx.now_ns)))
    rec.now = []
    CoreEngine(rec, [e]).run()
    assert rec.now == [T0 + 5 * MS]
    assert rec.seen[0].exchange_time_ns == T0

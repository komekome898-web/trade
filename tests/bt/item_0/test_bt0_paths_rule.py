"""i0-r3-09: each path's written claim in ORDERING_RULE is checked against
the engine's behaviour, path by path.

`ORDERING_RULE["channels"]` holds one entry per phase with a `fifo` flag,
and `channels_fifo` is derived from the flags. Here a seeded random run
(random streams with ties, random feed / order / cancel / notice delays,
random orders, cancels and timers) records, for every path, the order in
which things were SENT on it and the order in which they ARRIVED. A path
flagged FIFO must never let a later item overtake an earlier one in any
run; the timer path (not FIFO) must deliver each timer at exactly its
requested time, same-time timers in set order -- and, across the runs, a
timer set later for an earlier time must actually come first (so flagging
it FIFO would fail here). A path added to the table without a check here
fails `test_every_path_in_the_rule_has_a_behaviour_check`.
"""
from __future__ import annotations

import random

from bot.bt.core import (
    Ack,
    Canceled,
    CancelRequest,
    ClockEvent,
    CoreEngine,
    Fill,
    NullCostModel,
    ORDERING_RULE,
    OrderRequest,
    Strategy,
    TradeEvent,
    merge_order,
)
from bot.bt.core.events import NOTICE_EVENT_TYPES

MS = 1_000_000
T0 = 1_700_006_400_000_000_000


class _Venue:
    """Answers every order (Ack, sometimes a fill), fills live orders at
    random on market data, cancels live orders. Every report carries its
    emit number (Ack venue_order_id / Canceled reason / Fill price)."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.live: set[str] = set()
        self.emitted: list[int] = []
        self.market_seen: list[float] = []  # price of each market event, in venue order
        self.requests_seen: list[tuple] = []  # (kind, client_order_id) of each request, in venue order
        # (kind, client_order_id) of each request in SEND order: the latency
        # model is asked once per request, in send order (engine.py
        # `_drain`). Round 8: every receiver gets an object of its own
        # (values.py, engine.py), so requests are told apart by what they
        # say, not by object identity; two requests that say the same
        # (two cancels of one order) cannot be told apart by any receiver.
        self.sent_labels: list[tuple] = []

    def number(self, label: tuple) -> None:
        self.sent_labels.append(label)

    def _n(self) -> int:
        self.emitted.append(len(self.emitted) + 1)
        return self.emitted[-1]

    def on_market_event(self, event, venue_time_ns):
        self.market_seen.append(event.price)
        out = []
        for coid in sorted(self.live):
            if self.rng.random() < 0.2:
                self.live.discard(coid)
                out.append(Fill(coid, float(self._n()), 1.0))
        return out

    def on_order(self, order, venue_time_ns):
        self.requests_seen.append(("order", order.client_order_id))
        coid = order.client_order_id
        out = [Ack(coid, f"v{self._n()}")]
        if self.rng.random() < 0.3:
            out.append(Fill(coid, float(self._n()), 1.0))
        else:
            self.live.add(coid)
        return out

    def on_cancel(self, request, venue_time_ns):
        self.requests_seen.append(("cancel", request.client_order_id))
        self.live.discard(request.client_order_id)
        return (Canceled(request.client_order_id, f"c{self._n()}"),)


class _Latency:
    def __init__(self, rng: random.Random, venue: _Venue) -> None:
        self.rng, self.venue = rng, venue

    def _d(self) -> int:
        return self.rng.choice([0, 0, 1, 2, 5]) * MS + self.rng.randrange(3)

    def feed_delay_ns(self, event):
        return self._d()

    def order_delay_ns(self, order, sent_time_ns):
        self.venue.number(("order", order.client_order_id))
        return self._d()

    def cancel_delay_ns(self, request, sent_time_ns):
        self.venue.number(("cancel", request.client_order_id))
        return self._d()

    def notice_delay_ns(self, report, venue_time_ns):
        return self._d()


class _Trader(Strategy):
    def __init__(self, rng: random.Random, venue: _Venue) -> None:
        self.rng, self.venue = rng, venue
        self.sent = 0
        self.keep: list = []
        self.sent_labels: list[tuple] = []  # (kind, client_order_id) in the order the trader sent them
        self.mine: list[str] = []
        self.delivered_prices: list[float] = []
        self.notices: list[int] = []  # emit number of each venue notice, in arrival order
        self.timers_set: list[tuple[int, int]] = []  # (set number, requested time)
        self.timers_got: list[tuple[int, int]] = []  # (set number, delivery time)
        self.cancel_nos: set[int] = set()
        self.engine_answers = 0  # cancels the engine answered itself (order no longer live)

    def _send_no(self, obj) -> None:
        self.sent += 1
        self.keep.append(obj)
        self.sent_labels.append(("order", obj.client_order_id) if isinstance(obj, OrderRequest)
                                else ("cancel", obj.client_order_id))

    def on_event(self, event, ctx) -> None:
        t = event.EVENT_TYPE
        if t in NOTICE_EVENT_TYPES:
            n = _emit_no(event)
            if n is not None:
                self.notices.append(n)
            elif str(getattr(event, "reason", "")).startswith("order_not_open"):
                self.engine_answers += 1
            return
        if isinstance(event, ClockEvent):
            if event.tag.startswith("t"):
                self.timers_got.append((int(event.tag[1:]), ctx.now_ns))
            return
        self.delivered_prices.append(event.price)
        for _ in range(self.rng.randrange(3)):
            r = self.rng.random()
            if r < 0.45:
                req = OrderRequest("buy", "limit", 1.0, price=1.0, client_order_id=f"o{self.sent + 1}")
                self._send_no(req)
                ctx.place_order(req)
                self.mine.append(req.client_order_id)
            elif r < 0.7 and self.mine:
                req = CancelRequest(self.rng.choice(self.mine))
                self._send_no(req)
                self.cancel_nos.add(self.sent)
                ctx.cancel_order(req)
            else:
                k = len(self.timers_set) + 1
                at = ctx.now_ns + self.rng.choice([0, 1, 2, 3]) * MS
                self.timers_set.append((k, at))
                ctx.set_timer(at, f"t{k}")


def _emit_no(event):
    v = getattr(event, "venue_order_id", None)
    if v is not None and str(v).startswith("v"):
        return int(v[1:])
    reason = getattr(event, "reason", None)
    if event.EVENT_TYPE.value == "ORDER_CANCELED" and reason and reason.startswith("c"):
        return int(reason[1:])
    if event.EVENT_TYPE.value == "ORDER_FILL":
        return int(event.price)
    return None  # an answer the engine made itself (cancel of an order not live)


def _streams(rng: random.Random) -> dict:
    price = iter(range(1000, 100000))
    out = {}
    for name in ("a", "b", "c"):
        t, evs = T0, []
        for _ in range(rng.randrange(4, 12)):
            t += rng.choice([0, 0, 1, 2]) * MS
            evs.append(TradeEvent(exchange_time_ns=t, received_time_ns=t + rng.choice([0, 1, 3]) * MS,
                                  price=float(next(price)), size=1.0, side="buy"))
        out[name] = evs
    return out


def _run(seed: int) -> dict:
    """One random run; returns, per path, (sent order, arrival order) and
    the timer times."""
    rng = random.Random(seed)
    streams = _streams(rng)
    venue = _Venue(random.Random(seed + 1))
    trader = _Trader(random.Random(seed + 2), venue)
    CoreEngine(trader, streams, venue, _Latency(random.Random(seed + 3), venue), NullCostModel()).run()
    assert len(venue.sent_labels) == trader.sent, seed  # every request was sent, once
    assert venue.sent_labels == trader.sent_labels, seed  # ... in the trader's order

    # requests: the venue sees all but the cancels the engine answered
    # itself (order no longer live there). Match the arrivals against the
    # sends in order; what is skipped must be cancels, one per answer.
    kept, skipped, i = [], [], 0
    for label in venue.requests_seen:
        while i < len(venue.sent_labels) and venue.sent_labels[i] != label:
            skipped.append(venue.sent_labels[i])
            i += 1
        assert i < len(venue.sent_labels), (seed, "an arrival that was not sent, or out of send order")
        kept.append(venue.sent_labels[i])
        i += 1
    skipped.extend(venue.sent_labels[i:])
    assert all(k == "cancel" for k, _ in skipped) and len(skipped) == trader.engine_answers, seed
    merged = [e.price for e in merge_order(streams)]
    per_stream_sent, per_stream_got = [], []
    for evs in streams.values():
        mine = {e.price for e in evs}
        pos = {p: i for i, p in enumerate(merged)}
        reception = sorted(evs, key=lambda e: (e.received_time_ns, pos[e.price]))
        per_stream_sent.append([e.price for e in reception])
        per_stream_got.append([p for p in trader.delivered_prices if p in mine])
    return {
        "venue:input": [(merged, venue.market_seen)],
        "venue:request": [(kept, venue.requests_seen)],
        "deliver:input": list(zip(per_stream_sent, per_stream_got)),
        "deliver:notice": [(list(venue.emitted), trader.notices)],
        "deliver:timer": [([k for k, _ in trader.timers_set], [k for k, _ in trader.timers_got])],
        "_timers": (trader.timers_set, trader.timers_got),
    }


def _fifo(sent: list, got: list) -> bool:
    """Everything sent arrived exactly once, and in the order sent."""
    return got == sent


SEEDS = range(60)
RUNS = [_run(s) for s in SEEDS]


def _check_fifo_path(name: str) -> None:
    for seed, run in zip(SEEDS, RUNS):
        for sent, got in run[name]:
            assert _fifo(sent, got), (name, seed, sent, got)


def _check_timer_path(name: str) -> None:
    overtaken = 0
    for seed, run in zip(SEEDS, RUNS):
        set_, got = run["_timers"]
        requested = dict(set_)
        assert sorted(k for k, _ in got) == sorted(requested), (seed, "a timer lost or doubled")
        for k, t in got:
            assert t == requested[k], (seed, k, t, requested[k])  # exactly at the requested time
        # same requested time: set order
        order = [k for k, _ in got]
        for a, b in zip(order, order[1:]):
            if requested[a] == requested[b]:
                assert a < b, (seed, a, b)
        overtaken += sum(1 for a, b in zip(order, order[1:]) if a > b)
        (sent, arrived), = run[name]
        assert _fifo(sorted(sent), sorted(arrived))
    # not FIFO: across the runs, a timer set later for an earlier time came first
    assert overtaken > 0


CHECKS = {
    "venue:input": _check_fifo_path,
    "venue:request": _check_fifo_path,
    "deliver:input": _check_fifo_path,
    "deliver:notice": _check_fifo_path,
    "deliver:timer": _check_timer_path,
}


def test_every_path_in_the_rule_has_a_behaviour_check():
    assert set(ORDERING_RULE["channels"]) == set(CHECKS)


def test_the_runs_exercise_every_path():
    assert all(run["venue:request"][0][1] for run in RUNS[:5])
    assert sum(len(run["deliver:notice"][0][1]) for run in RUNS) > 200
    assert sum(len(run["_timers"][1]) for run in RUNS) > 200
    assert sum(len(run["venue:input"][0][1]) for run in RUNS) > 500


def test_each_path_behaves_as_its_fifo_flag_says():
    for name, path in ORDERING_RULE["channels"].items():
        if path["fifo"]:
            _check_fifo_path(name)
        else:
            assert CHECKS[name] is _check_timer_path, name
            _check_timer_path(name)


def test_channels_fifo_is_derived_from_the_flags():
    flagged = [n for n, p in ORDERING_RULE["channels"].items() if p["fifo"]]
    assert [c.split(" (")[0] for c in ORDERING_RULE["channels_fifo"]] == flagged
    assert "deliver:timer" not in flagged
    assert set(ORDERING_RULE["not_fifo"]) == {"deliver:timer"}
    assert "requested time" in ORDERING_RULE["channels"]["deliver:timer"]["time"]

"""Critic, item 0, round 2: re-checks of the round-1 fixes with random runs.

Not findings -- these pass on the round-2 core. They re-measure, with an
independent reference written from the documented rule (ordering.py module
docstring) and random fill models / latencies, what round 1 found broken:

* i0-r1-05 / 06: requests reach the venue in send order, notices reach the
  strategy in the order the venue emitted them (the latency model's
  `notice_delay_ns` is called once per report, in emission order);
* i0-r1-12: one stream reaches the strategy in reception order whatever the
  per-event feed delay;
* i0-r1-07 / 09: once every notice is delivered, the strategy's view of each
  order agrees with the venue ledger;
* i0-r1-10: with zero latency, the venue sees the heads of different streams
  merged by (exchange time, TYPE_ORDER, stream name), one stream in its own
  order, and the strategy sees (received time, merge position).
"""
from __future__ import annotations

import random

from bot.bt.core import (
    Ack,
    BarEvent,
    BookDeltaEvent,
    BookSnapshotEvent,
    Canceled,
    ClockEvent,
    CoreEngine,
    Fill,
    FundingEvent,
    LiquidationEvent,
    NullCostModel,
    OrderRequest,
    Reject,
    StateUnknown,
    Strategy,
    TradeEvent,
    ZeroLatency,
)

T0 = 1_700_006_400_000_000_000
MS = 1_000_000
VIEW_OF_VENUE = {"FILLED": "FILLED", "CANCELED": "CANCELED", "REJECTED": "REJECTED",
                 "STATE_UNKNOWN": "STATE_UNKNOWN", "LIVE": "OPEN"}
NOTICE = {"ORDER_ACK": "Ack", "ORDER_REJECT": "Reject", "ORDER_FILL": "Fill",
          "ORDER_CANCELED": "Canceled", "ORDER_STATE_UNKNOWN": "StateUnknown"}


class _RandomVenue:
    """Emits only reports that are valid for the order's venue-side history."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.live: dict[str, list] = {}  # coid -> [size, filled, acked, unknown_new]
        self.request_log: list[tuple[str, str]] = []

    def on_market_event(self, event, venue_time_ns):
        out = []
        for coid, st in list(self.live.items()):
            if self.rng.random() < 0.3 and (st[2] or st[3]):
                q = st[0] - st[1] if self.rng.random() < 0.5 else (st[0] - st[1]) / 2
                st[1] += q
                st[2], st[3] = True, False
                out.append(Fill(coid, 100.0, q))
                if st[1] >= st[0] - 1e-12:
                    del self.live[coid]
            elif self.rng.random() < 0.1 and st[3]:
                out.append(Ack(coid))
                st[2], st[3] = True, False
        return tuple(out)

    def on_order(self, order, venue_time_ns):
        c = order.client_order_id
        self.request_log.append(("new", c))
        r = self.rng.random()
        if r < 0.15:
            return (Reject(c, "no"),)
        if r < 0.35:
            self.live[c] = [order.size, 0.0, False, True]
            return (StateUnknown(c, "timeout"),)
        self.live[c] = [order.size, 0.0, True, False]
        return (Ack(c),)

    def on_cancel(self, request, venue_time_ns):
        c = request.client_order_id
        self.request_log.append(("cancel", c))
        r = self.rng.random()
        if r < 0.3:
            return (Reject(c, "busy", "cancel"),)
        if r < 0.5:
            return (StateUnknown(c, "timeout", "cancel"),)
        self.live.pop(c, None)
        return (Canceled(c),)


class _RandomLatency(ZeroLatency):
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.emitted: list[tuple] = []

    def feed_delay_ns(self, event):
        return self.rng.choice([0, 0, 1, 3]) * MS

    def order_delay_ns(self, order, sent_time_ns):
        return self.rng.choice([0, 1, 2, 5]) * MS

    def cancel_delay_ns(self, request, sent_time_ns):
        return self.rng.choice([0, 1, 2, 5]) * MS

    def notice_delay_ns(self, report, venue_time_ns):
        self.emitted.append((type(report).__name__, report.client_order_id, getattr(report, "request_kind", None)))
        return self.rng.choice([0, 1, 4, 7]) * MS


class _RandomTrader(Strategy):
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.coids: list[str] = []
        self.sent: list[tuple[str, str]] = []
        self.notices: list[tuple] = []
        self.feed: list[int] = []

    def on_event(self, event, ctx) -> None:
        name = event.EVENT_TYPE.value
        if name in NOTICE:
            self.notices.append((NOTICE[name], event.client_order_id, getattr(event, "request_kind", None)))
        if name != "TRADE":
            return
        self.feed.append(int(event.trade_id))
        if self.rng.random() < 0.4:
            coid = ctx.place_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=99.0))
            self.coids.append(coid)
            self.sent.append(("new", coid))
        if self.coids and self.rng.random() < 0.4:
            coid = self.rng.choice(self.coids)
            ctx.cancel_order(coid)
            self.sent.append(("cancel", coid))


def test_channels_stay_fifo_and_views_settle_on_the_venue_state():
    for seed in range(150):
        rng = random.Random(seed)
        events, t = [], T0
        for i in range(50):
            t += rng.choice([0, 1]) * MS
            events.append(TradeEvent(exchange_time_ns=t, received_time_ns=t + rng.choice([0, 0, 2]) * MS,
                                     price=100.0, size=1.0, side="buy", trade_id=str(i)))
        venue = _RandomVenue(random.Random(seed + 1))
        latency = _RandomLatency(random.Random(seed + 2))
        trader = _RandomTrader(random.Random(seed + 3))
        res = CoreEngine(trader, events, fill_model=venue, latency_model=latency,
                         cost_model=NullCostModel()).run()
        # requests the engine answers itself (cancel of an order not live) never reach
        # the fill model; the ones that do must keep the send order
        sent = iter(trader.sent)
        assert all(any(s == r for s in sent) for r in venue.request_log), f"seed {seed}: request order"
        assert [r for r in venue.request_log if r[0] == "new"] == [s for s in trader.sent if s[0] == "new"]
        assert trader.notices == latency.emitted, f"seed {seed}: notice order"
        order = [int(e.trade_id) for e in sorted(events, key=lambda e: (e.received_time_ns, int(e.trade_id)))]
        assert trader.feed == order, f"seed {seed}: one stream out of reception order"
        for coid, venue_state in res.venue_states.items():
            assert res.orders[coid].state.value == VIEW_OF_VENUE[venue_state], (
                f"seed {seed}: {coid} venue {venue_state} view {res.orders[coid].state.value}"
            )


_RANK = ["LIQUIDATION", "FUNDING", "BOOK_SNAPSHOT", "BOOK_DELTA", "TRADE", "BAR", "CLOCK"]


def _make(kind: str, exch: int, recv: int, uid: int):
    k = dict(exchange_time_ns=exch, received_time_ns=recv)
    if kind == "TRADE":
        return TradeEvent(price=1.0, size=1.0, side="buy", trade_id=str(uid), **k)
    if kind == "BOOK_DELTA":
        return BookDeltaEvent(side="bid", price=1.0, size=float(uid), **k)
    if kind == "BOOK_SNAPSHOT":
        return BookSnapshotEvent(bids=((float(uid), 1.0),), asks=(), **k)
    if kind == "BAR":
        return BarEvent(open=1.0, high=1.0, low=1.0, close=1.0, volume=float(uid), **k)
    if kind == "FUNDING":
        return FundingEvent(rate=uid * 1e-6, **k)
    if kind == "LIQUIDATION":
        return LiquidationEvent(price=1.0, size=float(uid), side="buy", **k)
    return ClockEvent(tag=str(uid), **k)


def _uid(e) -> int:
    v = e.EVENT_TYPE.value
    if v == "TRADE":
        return int(e.trade_id)
    if v in ("BOOK_DELTA", "LIQUIDATION"):
        return int(e.size)
    if v == "BOOK_SNAPSHOT":
        return int(e.bids[0][0])
    if v == "BAR":
        return int(e.volume)
    if v == "FUNDING":
        return round(e.rate * 1e6)
    return int(e.tag)


def test_zero_latency_order_matches_an_independent_reading_of_the_rule():
    for seed in range(300):
        rng = random.Random(seed)
        streams, uid = {}, 0
        for name in rng.sample(["a", "b", "c", "d", "e"], rng.randint(1, 4)):
            t, evs = 0, []
            for _ in range(rng.randint(0, 8)):
                t += rng.choice([0, 0, 1, 2])
                uid += 1
                evs.append(_make(rng.choice(_RANK), 1000 + t, 1000 + t + rng.choice([0, 0, 1, 3]), uid))
            streams[name] = evs
        heads, merged = {n: 0 for n in streams}, []
        while True:
            cands = [(streams[n][heads[n]].exchange_time_ns, _RANK.index(streams[n][heads[n]].EVENT_TYPE.value), n)
                     for n in streams if heads[n] < len(streams[n])]
            if not cands:
                break
            _, _, n = min(cands)
            merged.append(streams[n][heads[n]])
            heads[n] += 1
        venue_expected = [_uid(e) for e in merged if e.EVENT_TYPE.value != "CLOCK"]
        strategy_expected = [_uid(e) for _, e in sorted(enumerate(merged), key=lambda p: (p[1].received_time_ns, p[0]))]
        seen_venue, seen_strategy = [], []

        class _Venue:
            def on_market_event(self, event, venue_time_ns):
                seen_venue.append(_uid(event))
                return ()

            def on_order(self, order, venue_time_ns):  # pragma: no cover
                return ()

            def on_cancel(self, request, venue_time_ns):  # pragma: no cover
                return ()

        class _Rec(Strategy):
            def on_event(self, event, ctx) -> None:
                seen_strategy.append(_uid(event))

        handed = list(streams)
        rng.shuffle(handed)
        CoreEngine(_Rec(), {n: streams[n] for n in handed}, fill_model=_Venue(), cost_model=NullCostModel()).run()
        assert seen_venue == venue_expected, f"seed {seed}: venue order"
        assert seen_strategy == strategy_expected, f"seed {seed}: strategy order"

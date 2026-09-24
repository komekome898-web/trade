"""Critic, item 0, round 3: a random venue / latency / trader that only uses
the public sockets and the strategy API. Every random decision is drawn in
the order the engine calls the hooks, never from absolute times, so the same
seed gives the same run whatever the time origin (used to test that the core
is invariant under shifting every time by a constant).

The venue only emits reports that are valid for the order's venue-side
history (so a VenueProtocolError is a core bug, not a harness bug) and
answers every cancel it is handed exactly once.
"""
from __future__ import annotations

import random

from bot.bt.core import (
    Ack,
    BarEvent,
    Canceled,
    ClockEvent,
    Fill,
    FundingEvent,
    OrderRequest,
    Reject,
    StateUnknown,
    Strategy,
    TradeEvent,
    ZeroLatency,
)

MS = 1_000_000
SEC = 1_000_000_000


class RandomVenue:
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        # coid -> dict(size, filled, acked, unknown_new)
        self.live: dict[str, dict] = {}

    def _fill(self, coid: str, st: dict, full: bool) -> list:
        q = st["size"] - st["filled"] if full else (st["size"] - st["filled"]) / 2
        st["filled"] += q
        st["acked"], st["unknown_new"] = True, False
        out = [Fill(coid, 100.0, q)]
        if st["filled"] >= st["size"] * (1 - 1e-12):
            del self.live[coid]
        return out

    def on_market_event(self, event, venue_time_ns):
        out: list = []
        for coid in sorted(self.live):
            st = self.live.get(coid)
            if st is None:
                continue
            r = self.rng.random()
            if r < 0.15:
                out += self._fill(coid, st, self.rng.random() < 0.5)
            elif r < 0.22:
                out.append(Canceled(coid, "expired"))  # the venue on its own
                del self.live[coid]
            elif r < 0.30 and st["unknown_new"] and not st["acked"]:
                out.append(Ack(coid))
                st["acked"], st["unknown_new"] = True, False
        return out

    def on_order(self, order, venue_time_ns):
        c = order.client_order_id
        r = self.rng.random()
        if r < 0.12:
            return [Reject(c, "no")]
        if r < 0.27:
            self.live[c] = {"size": order.size, "filled": 0.0, "acked": False, "unknown_new": True}
            return [StateUnknown(c, "timeout")]
        self.live[c] = {"size": order.size, "filled": 0.0, "acked": True, "unknown_new": False}
        out: list = [Ack(c)]
        r2 = self.rng.random()
        if r2 < 0.15:
            out += self._fill(c, self.live[c], True)
        elif r2 < 0.25:
            out += self._fill(c, self.live[c], False)
            out.append(Canceled(c, "ioc_remainder"))
            self.live.pop(c, None)
        return out

    def on_cancel(self, request, venue_time_ns):
        c = request.client_order_id
        st = self.live[c]  # the engine only calls this for a live order
        r = self.rng.random()
        if r < 0.25:
            return [Reject(c, "busy", "cancel")]
        if r < 0.40:
            return [StateUnknown(c, "timeout", "cancel")]
        if r < 0.50:
            out = self._fill(c, st, True)  # filled before the cancel took effect
            return out + [Reject(c, "too_late", "cancel")]
        if r < 0.60:
            out = self._fill(c, st, False)
            self.live.pop(c, None)
            return out + [Canceled(c)]
        self.live.pop(c, None)
        return [Canceled(c)]


class RandomLatency(ZeroLatency):
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def feed_delay_ns(self, event):
        return self.rng.choice([0, 0, 1, 3]) * MS

    def order_delay_ns(self, order, sent_time_ns):
        return self.rng.choice([0, 1, 2, 5]) * MS

    def cancel_delay_ns(self, request, sent_time_ns):
        return self.rng.choice([0, 1, 2, 5]) * MS

    def notice_delay_ns(self, report, venue_time_ns):
        return self.rng.choice([0, 1, 4, 7]) * MS


def answers_a_cancel(event) -> bool:
    """Independent reading of 'this notice is the venue's answer to one of our
    cancels' from the notice's public fields."""
    t = event.EVENT_TYPE.value
    if t == "ORDER_CANCELED":
        return event.answers == "cancel"
    if t in ("ORDER_REJECT", "ORDER_STATE_UNKNOWN"):
        return event.request_kind == "cancel"
    return False


class RandomTrader(Strategy):
    """Places, cancels (also twice, also after final) and sets timers at
    random. Records, per callback, what it saw relative to `shift`, and checks
    the per-order cancel count against its own count of cancels sent minus
    answers delivered."""

    def __init__(self, rng: random.Random, shift: int = 0) -> None:
        self.rng = rng
        self.shift = shift
        self.coids: list[str] = []
        self.sent_cancels: dict[str, int] = {}
        self.answered: dict[str, int] = {}
        self.trace: list[tuple] = []
        self.count_mismatch: list[tuple] = []

    def on_event(self, event, ctx) -> None:
        s = self.shift
        et = event.EVENT_TYPE.value
        coid = getattr(event, "client_order_id", None)
        if coid is not None and answers_a_cancel(event):
            self.answered[coid] = self.answered.get(coid, 0) + 1
        self.trace.append((et, int(ctx.now_ns) - s, int(event.exchange_time_ns) - s, int(event.seq), coid,
                           getattr(event, "answers", None), getattr(event, "request_kind", None)))
        # cancel count check, every order, every callback
        for c in self.coids:
            v = ctx.order(c)
            want = self.sent_cancels.get(c, 0) - self.answered.get(c, 0)
            if v.cancels_in_flight != want or v.cancel_pending != (want > 0):
                self.count_mismatch.append((int(ctx.now_ns) - s, c, v.cancels_in_flight, want, v.state.value))
        r = self.rng.random()
        if r < 0.25:
            c = ctx.place_order(OrderRequest(side=self.rng.choice(["buy", "sell"]), order_type="limit",
                                             size=1.0, price=100.0))
            self.coids.append(c)
        elif r < 0.50 and self.coids:
            c = self.rng.choice(self.coids)
            for _ in range(self.rng.choice([1, 1, 2])):
                ctx.cancel_order(c)
                self.sent_cancels[c] = self.sent_cancels.get(c, 0) + 1
        elif r < 0.58:
            ctx.set_timer(int(ctx.now_ns) + self.rng.choice([0, 1, 3]) * MS, "t")
        views = tuple(
            (c, v.state.value, v.cancels_in_flight, v.filled_size, v.unknown_new, v.unknown_cancel,
             v.sent_time_ns - s, v.last_update_ns - s)
            for c in self.coids for v in [ctx.order(c)]
        )
        self.trace.append(("views", views))


def random_input(rng: random.Random, base: int, n: int = 120) -> list:
    """One stream, non-decreasing exchange time, received time >= exchange
    time with jitter (a late print now and then)."""
    out, t = [], base
    for _ in range(n):
        t += rng.choice([0, 1, 2, 5]) * MS
        recv = t + rng.choice([0, 0, 1, 4]) * MS
        k = rng.random()
        if k < 0.6:
            out.append(TradeEvent(received_time_ns=recv, exchange_time_ns=t, price=100.0, size=1.0, side="buy"))
        elif k < 0.8:
            out.append(BarEvent(received_time_ns=recv, exchange_time_ns=t, open=100.0, high=100.0,
                                low=100.0, close=100.0, volume=1.0))
        elif k < 0.9:
            out.append(FundingEvent(received_time_ns=recv, exchange_time_ns=t, rate=0.0001))
        else:
            out.append(ClockEvent(received_time_ns=recv, exchange_time_ns=t))
    return out

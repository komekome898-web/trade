"""Seeded property test: random mixed inputs, random latencies, a strategy
that trades; two runs must be identical in every observable."""
import random

import pytest

from bot.bt.core import (
    BookDeltaEvent,
    ClockEvent,
    CoreEngine,
    EventType,
    FundingEvent,
    OrderRequest,
)
from bot.bt.core.testing import FixedRateCost, ImmediateFillModel, RecordingAccount

from bt0_util import MS, T0, Recorder, bar, trade


def _events(seed, n=300):
    rng = random.Random(seed)
    t = T0
    out = []
    for _ in range(n):
        t += rng.choice([0, 0, 1, MS])
        kind = rng.random()
        if kind < 0.4:
            out.append(trade(t + rng.choice([0, MS]), 100 + rng.random(), exch=t))
        elif kind < 0.6:
            out.append(bar(t, 100 + rng.random()))
        elif kind < 0.8:
            out.append(BookDeltaEvent(received_time_ns=t, side=rng.choice(["bid", "ask"]), price=100.0, size=rng.random()))
        elif kind < 0.9:
            out.append(FundingEvent(received_time_ns=t, rate=rng.uniform(-1e-4, 1e-4)))
        else:
            out.append(ClockEvent(received_time_ns=t))
    return out


class _Lat:
    def __init__(self, seed):
        self.rng = random.Random(seed)

    def feed_delay_ns(self, e):
        return self.rng.randrange(0, 2 * MS)

    def order_delay_ns(self, o, t):
        return self.rng.randrange(0, 5 * MS)

    def cancel_delay_ns(self, r, t):
        return self.rng.randrange(0, 5 * MS)

    def notice_delay_ns(self, r, t):
        return self.rng.randrange(0, 5 * MS)


def _strategy(seed):
    rng = random.Random(seed + 1000)

    def act(ev, ctx):
        r = rng.random()
        if ev.EVENT_TYPE is EventType.TRADE and r < 0.2:
            ctx.place_order(OrderRequest(rng.choice(["buy", "sell"]), rng.choice(["market", "limit"]), 1.0, price=100.0))
        elif r < 0.1 and ctx.open_orders():
            ctx.cancel_order(ctx.open_orders()[0].client_order_id)
        elif r < 0.12:
            ctx.set_timer(int(ctx.now_ns) + rng.randrange(0, 3 * MS), "t")

    return Recorder(act)


def _run(seed):
    acct = RecordingAccount()
    rec = _strategy(seed)
    res = CoreEngine(rec, _events(seed), fill_model=ImmediateFillModel(), latency_model=_Lat(seed),
                     cost_model=FixedRateCost(0.001), account=acct).run()
    return (
        [e.to_dict() for e in rec.seen],
        res.delivery_digest,
        [(f.client_order_id, f.price, f.fee, f.venue_time_ns) for f in res.fills],
        {k: (v.state.value, v.filled_size) for k, v in res.orders.items()},
        [(k, repr(x)) for k, x in acct.calls],
    )


@pytest.mark.parametrize("seed", range(6))
def test_two_runs_are_identical(seed):
    a, b = _run(seed), _run(seed)
    assert a == b
    assert len(a[0]) > 300  # notices and timers were produced too


def test_delivery_times_never_decrease_and_seq_is_unique():
    seen = _run(1)[0]
    times = [d["received_time_ns"] for d in seen]
    assert times == sorted(times)
    seqs = [d["seq"] for d in seen]
    assert len(set(seqs)) == len(seqs)

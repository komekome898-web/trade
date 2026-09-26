"""Round 15 (i0-r14-01 / -02 / -05): one run that passes through every entry
where the core takes, copies, compares or hashes a value -- used by
test_bt0_r15_library_code.py, in this process and in fresh children.

Every party (strategy, fill model, latency model, cost model, account,
stream) is defined HERE, so a frame of this file on the stack means "inside
a party's own call". The values handed over cover every accepted scalar
type (None, bool, int, float, complex, str, bytes, Decimal, Fraction, the
numpy numbers) and every container (tuple, list, dict, set, frozenset and
the core's frozen ones), nested, with keys whose hashes collide across
types (`colliding_pairs`), so a set or dict the core builds from them makes
the interpreter compare them.

`run()` returns a plain summary of what the core decided (orders, fills,
fees, delays, the delivery digest, the extras as the account saw them, and
the error type of every refusal the workload provokes), so two runs can be
compared value for value.
"""
from __future__ import annotations

import sys
from decimal import Decimal
from fractions import Fraction

import numpy as np

from bot.bt.core import BarEvent, CoreEngine, EventType, TradeEvent
from bot.bt.core.api import CancelRequest, OrderRequest
from bot.bt.core.interfaces import Ack, Canceled, Fill
from bot.bt.core import values

T0 = 1_700_000_000_000_000_000
P = sys.hash_info.modulus  # 2**61 - 1 on 64-bit builds


def _small_hash_strs(n: int) -> list:
    """`n` strs whose hashes fit a Fraction's / Decimal's hash exactly
    (|h| < P), so a number with the same hash can be made (the str hash is
    per process)."""
    out = []
    for i in range(100_000):
        s = f"key{i}"
        if abs(hash(s)) < P and hash(s) not in (-1, 0):
            out.append(s)
            if len(out) == n:
                return out
    raise RuntimeError("no str with a small hash")  # pragma: no cover


def colliding_pairs() -> list[tuple[str, object, object]]:
    """(label, a, b): a != b and hash(a) == hash(b), a and b of different
    types, every pair the interpreter would compare when both are keys of
    one dict or elements of one set. Each pair uses values of its own, so no
    two pairs share an equal value (a dict would hold them once). Made in
    the calling process (str hashes differ between processes)."""
    s1, s2, s3, s4, s5 = _small_hash_strs(5)
    t1, t2 = (1, "x"), (2, "y")
    fs = frozenset({1, 2})
    out = [
        ("Fraction~Decimal", Fraction(3), Decimal(P + 3)),
        ("Fraction~int", Fraction(P + 4), 4),
        ("Fraction~float", Fraction(P + 5), 5.0),
        ("Fraction~complex", Fraction(P + 1000003), complex(0, 1)),
        ("Fraction~str", Fraction(hash(s1)), s1),
        ("Fraction~bytes", Fraction(hash(s2.encode())), s2.encode()),
        ("Decimal~float", Decimal(P + 7), 7.0),
        ("Decimal~complex", Decimal(P + 2000006), complex(0, 2)),
        ("Decimal~int", Decimal(P + 8), 8),
        ("Decimal~str", Decimal(hash(s3)), s3),
        ("Decimal~bytes", Decimal(hash(s4.encode())), s4.encode()),
        ("str~bytes", s5, s5.encode()),
        ("int~int", -1, -2),
    ]
    if abs(hash(t1)) < P:
        out.append(("Fraction~tuple", Fraction(hash(t1)), t1))
    if abs(hash(t2)) < P:
        out.append(("Decimal~tuple", Decimal(hash(t2)), t2))
    if abs(hash(fs)) < P:
        out.append(("Fraction~frozenset", Fraction(hash(fs)), fs))
    for label, a, b in out:
        assert a != b and hash(a) == hash(b), label
    return out


def nested(depth: int, leaf: object = 1) -> object:
    v = leaf
    for _ in range(depth):
        v = [v]
    return v


def rich_extra() -> tuple:
    """An `extra` holding every accepted scalar type and every container,
    with colliding keys in a dict, a set and a frozenset."""
    pairs = colliding_pairs()
    d: dict = {}
    for i, (_label, a, b) in enumerate(pairs):
        d[a] = f"a{i}"
        d[b] = f"b{i}"
    sset = set()
    for _label, a, b in pairs:
        if not isinstance(a, (list, dict, set)):
            sset.add(a)
            sset.add(b)
    scalars = [None, True, False, 0, -1, 2**70, 1.5, float("inf"), -0.0, complex(1, -2), "t", b"b",
               Decimal("1.25"), Decimal("-0"), Fraction(1, 3), np.int64(7), np.float32(0.5), np.uint8(3),
               np.complex64(1 + 2j), np.bool_(True), np.str_("s"), np.bytes_(b"y")]
    return (
        ("colliding_dict", d),
        ("colliding_set", sset),
        ("colliding_frozenset", frozenset(sset)),
        ("scalars", scalars),
        ("tuple", tuple(scalars[:6])),
        ("nested", nested(20, {"deep": (Fraction(2, 7), Decimal("3.5"))})),
        ("frozen", values.FrozenDict({"x": values.FrozenList([1, 2]), "y": values.FrozenSet([3])})),
    )


# made once, when this module is loaded -- before any party changes process
# state: the parties below hand these same objects over (the core copies them)
EXTRA = rich_extra()
SMALL_EXTRA = (("k", {Fraction(1, 2): 1}),)
INSIDE = [0]  # > 0 while the strategy's own on_event runs


class Strategy:
    """`change()` runs inside its first on_event, `restore()` inside its
    second (a change made for one callback)."""

    def __init__(self, change=None, restore=None):
        self.change, self.restore = change, restore
        self.n = 0
        self.seen: list = []

    def on_event(self, event, ctx):
        INSIDE[0] += 1
        try:
            self._on_event(event, ctx)
        finally:
            INSIDE[0] -= 1

    def _on_event(self, event, ctx):
        self.n += 1
        if self.change is not None and self.n == 1:
            self.change()
        if self.restore is not None and self.n == 2:
            self.restore()
        self.seen.append((event.EVENT_TYPE.value, event.received_time_ns))
        if self.n == 1:
            ctx.place_order(OrderRequest(side="buy", order_type="market", size=1.0, client_order_id="m1",
                                         extra=EXTRA))
            ctx.place_order(OrderRequest(side="sell", order_type="limit", price=101.0, size=np.float32(2.0),
                                         client_order_id="l1", extra=SMALL_EXTRA))
            ctx.set_timer(T0 + 30, "t1")
        elif self.n == 3:
            ctx.cancel_order(CancelRequest("l1"))
            ctx.visible_events(EventType.BAR, 2, since_ns=T0)
            for v in ctx.open_orders():
                v.request.extra_dict()
            o = ctx.order("m1")
            if o is not None:
                o.request.extra_dict()


class FillModel:
    def on_market_event(self, event, t):
        return ()

    def on_order(self, order, t):
        coid = order.client_order_id
        order.extra_dict()
        if order.order_type == "market":
            return (Ack(coid, f"v-{coid}"), Fill(coid, np.float64(100.5), 1.0, "taker"))
        return [Ack(coid, f"v-{coid}")]

    def on_cancel(self, request, t):
        return (Canceled(request.client_order_id),)


class Latency:
    def feed_delay_ns(self, event):
        return np.int64(0)

    def order_delay_ns(self, order, sent):
        return np.uint16(5)

    def cancel_delay_ns(self, request, sent):
        return 3

    def notice_delay_ns(self, report, venue_time):
        return np.int32(2)


class Cost:
    def cost(self, fill):
        return Fraction(3, 4) if fill.liquidity == "taker" else np.float32(0.25)


class Account:
    def __init__(self):
        self.calls: list = []

    def apply_fill(self, fill):
        self.calls.append(("fill", fill.client_order_id, fill.price, fill.size, fill.fee, fill.liquidity))

    def apply_funding(self, event):
        self.calls.append(("funding", event.received_time_ns))

    def apply_liquidation(self, event):
        self.calls.append(("liquidation", event.received_time_ns))

    def on_market_event(self, event, t):
        if event.received_time_ns == T0 + 10:
            return (OrderRequest(side="sell", order_type="market", size=1.0, client_order_id="forced-1",
                                 extra=EXTRA),)
        return ()

    def check_order(self, order, t):
        self.calls.append(("check", order.client_order_id, _plain(order.extra_dict())))
        return None


def _plain(v):
    """A party's own record of a value: (type name, its value as text read
    without any process-wide setting -- a Decimal by its digits, not by the
    thread's context), sets and dicts sorted by that, so two runs (and two
    processes) compare by value."""
    t = type(v)
    if isinstance(v, dict):
        return ("dict", sorted((_plain(k), _plain(x)) for k, x in v.items()))
    if isinstance(v, (set, frozenset)):
        return (t.__name__, sorted(_plain(x) for x in v))
    if isinstance(v, (list, tuple)):
        return (t.__name__, [_plain(x) for x in v])
    if isinstance(v, Decimal):
        return (t.__name__, str(Decimal.as_tuple(v)))
    if isinstance(v, Fraction):
        return (t.__name__, f"{v.numerator}/{v.denominator}")
    if isinstance(v, float):
        return (t.__name__, float.__repr__(v))
    return (t.__name__, repr(v))


def bars():
    return [BarEvent(received_time_ns=T0 + k, open=100.0, high=101.0, low=99.0, close=100.0, volume=1.0)
            for k in (0, 10, 20, 40)]


def run(change=None, restore=None) -> dict:
    """The run and a plain summary of what the core decided."""
    strategy, account = Strategy(change, restore), Account()
    streams = {"bars": bars(), "trades": [TradeEvent(received_time_ns=T0 + 5, price=100.0, size=1.0, side="buy")]}
    engine = CoreEngine(strategy, streams, fill_model=FillModel(), latency_model=Latency(),
                        cost_model=Cost(), account=account)
    try:
        engine.run()
        res = engine.result()
    except BaseException as exc:  # noqa: BLE001 - the outcome is what is compared
        return {"outcome": type(exc).__name__}
    return {
        "outcome": "ok",
        "seen": strategy.seen,
        "account": account.calls,
        "digest": res.delivery_digest,
        "orders": [(r.client_order_id, _plain(r.extra_dict())) for r in res.order_requests],
        "forced": [(r.client_order_id, _plain(r.extra_dict())) for r in res.forced_orders],
        "fills": [(f.client_order_id, f.price, f.size, f.fee, f.liquidity) for f in res.fills],
    }

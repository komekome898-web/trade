"""Critic, item 0, round 8 (same family as i0-r7-02 / i0-r5-01 / i0-r4-02:
the core keeps and later reads state that another party can change without
going through the API).

The strategy's order port (`api._OrderPort`) is reachable from the context
by plain attribute access -- the scope the contract covers
(CORE_CONTRACT["visibility"]["scope"]: "the context and everything
reachable from it by attribute access"). Round 8 guarded ONE of its two
pieces of state, the outbox: `_drain` refuses an item "the order port did
not put there" by asking `port.knows(coid)`. But `knows` reads the other
piece, the registry, which is a plain dict the strategy can write the same
way. So:

1. a view written into the registry around place_order is reported by the
   caller's result as one of the strategy's orders (an order never sent,
   FILLED, with fees the venue never charged): `result()` builds `orders`
   from the registry (engine.py `result`, `_copied_view`);
2. a registry entry plus an outbox item sends an order place_order refuses
   (the id prefix reserved for the account's forced orders): the outbox
   guard passes because it trusts the registry.

The state is found by walking attributes from the context (no private name
is assumed), so a design that makes it unreachable passes; so does one that
refuses the write or the forged item (a CoreError out of the run).
"""
from __future__ import annotations

from bot.bt.core import Ack, CoreEngine, NullCostModel, OrderRequest, Strategy, TradeEvent
from bot.bt.core.api import FORCED_ID_PREFIX, OrderState, OrderView
from bot.bt.core.errors import CoreError

T0 = 1_700_000_000_000_000_000
SEC = 1_000_000_000


def _reachable(root, max_depth: int = 4):
    """Every object reachable from `root` by attribute access (instance
    dicts, slots, bound methods' __self__), breadth first."""
    seen, out, frontier = {id(root)}, [], [root]
    for _ in range(max_depth):
        nxt = []
        for obj in frontier:
            names = list(getattr(obj, "__dict__", {}) or {})
            for cls in type(obj).__mro__:
                slots = cls.__dict__.get("__slots__", ())
                names.extend([slots] if isinstance(slots, str) else list(slots))
            for name in names:
                try:
                    v = getattr(obj, name)
                except Exception:  # noqa: BLE001
                    continue
                for w in (v, getattr(v, "__self__", None)):
                    if w is not None and id(w) not in seen and not isinstance(w, (int, float, str, bytes, bool)):
                        seen.add(id(w))
                        out.append(w)
                        nxt.append(w)
        frontier = nxt
    return out


def _registries(ctx):
    return [o for o in _reachable(ctx)
            if type(o) is dict and o and all(hasattr(v, "filled_size") for v in o.values())]


def _outboxes(ctx):
    return [o for o in _reachable(ctx) if type(o) is list and o and all(type(x) is tuple for x in o)]


class _Venue:
    def __init__(self) -> None:
        self.seen: list[str] = []

    def on_market_event(self, event, venue_time_ns):
        return ()

    def on_order(self, order, venue_time_ns):
        self.seen.append(order.client_order_id)
        return (Ack(order.client_order_id),)

    def on_cancel(self, request, venue_time_ns):
        return ()


def _events():
    return [TradeEvent(received_time_ns=T0 + i * SEC, price=100.0, size=1.0, side="buy") for i in range(3)]


def test_result_does_not_report_an_order_written_around_place_order():
    class _S(Strategy):
        def __init__(self) -> None:
            self.done = False

        def on_event(self, event, ctx) -> None:
            if self.done:
                return
            self.done = True
            # a real order first, so the registry is not empty and can be found
            ctx.place_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0, client_order_id="real"))
            ghost = OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0, client_order_id="ghost")
            for reg in _registries(ctx):
                reg["ghost"] = OrderView(request=ghost, state=OrderState.FILLED, sent_time_ns=ctx.now_ns,
                                         last_update_ns=ctx.now_ns, acked=True, filled_size=1.0,
                                         avg_fill_price=1.0, fees=-50.0)

    try:
        res = CoreEngine(_S(), _events(), fill_model=_Venue(), cost_model=NullCostModel()).run()
    except CoreError:
        return  # refused
    got = res.orders.get("ghost")
    assert got is None or (got.filled_size == 0.0 and got.state is not OrderState.FILLED), (
        f"the caller's result reports order 'ghost' as {got.state} with filled_size {got.filled_size} and fees "
        f"{got.fees}, although it was never sent (order_requests {[r.client_order_id for r in res.order_requests]}, "
        f"fills {res.fills}): the strategy wrote it into the order registry reachable from its context"
    )


def test_outbox_guard_does_not_trust_a_registry_the_strategy_can_write():
    venue = _Venue()
    coid = FORCED_ID_PREFIX + "1"

    class _S(Strategy):
        def __init__(self) -> None:
            self.done = False

        def on_event(self, event, ctx) -> None:
            if self.done:
                return
            self.done = True
            ctx.place_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0, client_order_id="real"))
            req = OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0, client_order_id=coid)
            for reg in _registries(ctx):
                reg[coid] = OrderView(request=req, state=OrderState.PENDING_NEW, sent_time_ns=ctx.now_ns,
                                      last_update_ns=ctx.now_ns)
            for box in _outboxes(ctx):
                box.append(("new", req, ctx.now_ns))

    try:
        CoreEngine(_S(), _events(), fill_model=venue, cost_model=NullCostModel()).run()
    except CoreError:
        return  # refused
    assert coid not in venue.seen, (
        f"an order with the reserved forced-order id {coid!r} reached the venue ({venue.seen}); place_order refuses "
        f"that id, but an outbox item passes the guard because the guard asks a registry the strategy wrote"
    )

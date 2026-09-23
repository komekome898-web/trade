from bot.bt.core import STRATEGY_API, CoreEngine, EventType, OrderRequest

from ._util import T0, Recorder, trade


def test_public_context_surface_is_exactly_the_declared_api():
    holder = []
    CoreEngine(Recorder(lambda ev, ctx: holder.append(ctx)), [trade(T0)]).run()
    public = sorted(n for n in dir(holder[0]) if not n.startswith("_"))
    assert public == sorted(STRATEGY_API)


def test_callback_place_cancel_all_exist_and_work():
    # the three calls the requirement names: per-event callback, place, cancel
    log = []

    def act(ev, ctx):
        log.append(ev.EVENT_TYPE)
        if ev.EVENT_TYPE is EventType.TRADE:
            oid = ctx.place_order(OrderRequest("buy", "limit", 1.0, price=1.0))
            ctx.cancel_order(oid)

    res = CoreEngine(Recorder(act), [trade(T0)]).run()
    assert log == [EventType.TRADE, EventType.ORDER_ACK, EventType.ORDER_CANCELED]
    assert len(res.order_requests) == 1 and len(res.cancel_requests) == 1

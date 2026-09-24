"""Critic, item 0, round 3, finding i0-r3 (resume after an exception).

`CoreEngine.step()` is public and nothing stops a caller from calling it
again after an exception escaped it (a harness that catches, logs and goes
on). A step is not atomic: when the strategy raises after `place_order`,
the order is already in the strategy's view (`_OrderPort.place`), but the
outbox is thrown away in `_deliver`'s `finally` before `_drain`; when a
latency model raises in `_drain` after the first request, the first request
is queued and the rest are lost. The engine then carries on as if nothing
happened: the strategy sees orders PENDING_NEW that were never sent, and
the run result reports them as open orders with no request behind them.

errors.py: "Every one of them means 'the run is not trustworthy as
configured' -- the core never downgrades one of these to a warning and
carries on." The property tested: after an exception escaped a step, the
engine either refuses to go on, or its state is consistent (every order in
the strategy's view was sent to the venue).
"""
from __future__ import annotations

import pytest

from bot.bt.core import (
    CoreEngine,
    NullCostModel,
    NullFillModel,
    OrderRequest,
    Strategy,
    TradeEvent,
    ZeroLatency,
)

T = 1_700_006_400_000_000_000


def _trades(n=5):
    return [TradeEvent(received_time_ns=T + i * 1000, price=100.0, size=1.0, side="buy") for i in range(n)]


def _resume_is_refused_or_consistent(eng) -> list:
    try:
        res = eng.run()
    except Exception:  # noqa: BLE001 - refusing to go on is one acceptable answer
        return []
    sent = {r.client_order_id for r in res.order_requests}
    return [(c, v.state.value) for c, v in res.orders.items() if c not in sent]


def test_strategy_exception_after_place_order_then_resume():
    class S(Strategy):
        def __init__(self):
            self.n = 0

        def on_event(self, event, ctx):
            self.n += 1
            if self.n == 1:
                ctx.place_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0))
                raise RuntimeError("strategy bug")

    eng = CoreEngine(S(), _trades(), NullFillModel(), None, NullCostModel())
    with pytest.raises(RuntimeError):
        eng.run()
    unsent = _resume_is_refused_or_consistent(eng)
    assert unsent == [], f"the run went on with orders the strategy sees but that were never sent: {unsent}"


def test_latency_model_exception_mid_drain_then_resume():
    class Flaky(ZeroLatency):
        def __init__(self):
            self.calls = 0

        def order_delay_ns(self, order, sent_time_ns):
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("latency sampler failed")
            return 0

    class S(Strategy):
        def __init__(self):
            self.n = 0

        def on_event(self, event, ctx):
            self.n += 1
            if self.n == 1:
                for _ in range(3):
                    ctx.place_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0))

    eng = CoreEngine(S(), _trades(), NullFillModel(), Flaky(), NullCostModel())
    with pytest.raises(RuntimeError):
        eng.run()
    unsent = _resume_is_refused_or_consistent(eng)
    assert unsent == [], f"the run went on with orders the strategy sees but that were never sent: {unsent}"

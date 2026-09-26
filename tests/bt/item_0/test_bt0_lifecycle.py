"""i0-r3-01: an exception that escapes a step leaves the engine FAILED.

A step changes state owned by several parties one after the other, and the
strategy and every socket can raise at any point of it. The core cannot roll
them back, so the engine has a lifecycle instead (engine.py, "Lifecycle";
CORE_CONTRACT["lifecycle"]): the escaping exception is re-raised unchanged,
and every later `step()` / `run()` / `result()` is refused with
`EngineFailedError` (cause = the original exception). These tests raise at
every hook a step calls -- each strategy action, each latency, fill, cost and
account hook, at its 1st, 2nd or 3rd call -- and at every core check that can
fire mid-run, and check that nothing half-updated is run on or reported.
"""
from __future__ import annotations

import random

import pytest

from bot.bt.core import (
    Ack,
    CoreEngine,
    CORE_CONTRACT,
    EngineFailedError,
    EngineReentryError,
    EventOrderError,
    FundingEvent,
    LatencyModelError,
    LiquidationEvent,
    OrderApiError,
    OrderRequest,
    TimestampUnitError,
    VenueProtocolError,
)
from bot.bt.core.testing import FixedRateCost, ImmediateFillModel, RecordingAccount

from bt0_util import MS, SEC, T0, Recorder, trade


class Boom(Exception):
    """The injected failure (not a core error, as a plug-in's bug would be)."""


class Injector:
    """Raises `exc` at the k-th call of hook `target` (counted per hook)."""

    def __init__(self, target: str = "", k: int = 1, exc: BaseException | None = None) -> None:
        self.target, self.k = target, k
        self.exc = exc if exc is not None else Boom(f"{target}#{k}")
        self.calls: dict[str, int] = {}

    def hit(self, name: str) -> None:
        self.calls[name] = self.calls.get(name, 0) + 1
        if name == self.target and self.calls[name] == self.k:
            raise self.exc


class Fill(ImmediateFillModel):
    def __init__(self, inj: Injector) -> None:
        super().__init__()
        self.inj = inj

    def on_market_event(self, event, venue_time_ns):
        self.inj.hit("fill.on_market_event")
        return super().on_market_event(event, venue_time_ns)

    def on_order(self, order, venue_time_ns):
        self.inj.hit("fill.on_order")
        return super().on_order(order, venue_time_ns)

    def on_cancel(self, request, venue_time_ns):
        self.inj.hit("fill.on_cancel")
        return super().on_cancel(request, venue_time_ns)


class Latency:
    def __init__(self, inj: Injector) -> None:
        self.inj = inj

    def feed_delay_ns(self, event):
        self.inj.hit("latency.feed")
        return 1 * MS

    def order_delay_ns(self, order, sent_time_ns):
        self.inj.hit("latency.order")
        return 2 * MS

    def cancel_delay_ns(self, request, sent_time_ns):
        self.inj.hit("latency.cancel")
        return 2 * MS

    def notice_delay_ns(self, report, venue_time_ns):
        self.inj.hit("latency.notice")
        return 1 * MS


class Cost(FixedRateCost):
    def __init__(self, inj: Injector) -> None:
        super().__init__(0.001)
        self.inj = inj

    def cost(self, fill):
        self.inj.hit("cost.cost")
        return super().cost(fill)


class Account(RecordingAccount):
    def __init__(self, inj: Injector) -> None:
        super().__init__()
        self.inj = inj

    def apply_fill(self, fill):
        self.inj.hit("account.apply_fill")
        return super().apply_fill(fill)

    def apply_funding(self, event):
        self.inj.hit("account.apply_funding")
        return super().apply_funding(event)

    def apply_liquidation(self, event):
        self.inj.hit("account.apply_liquidation")
        return super().apply_liquidation(event)

    def on_market_event(self, event, venue_time_ns):
        self.inj.hit("account.on_market_event")
        return super().on_market_event(event, venue_time_ns)

    def check_order(self, order, venue_time_ns):
        self.inj.hit("account.check_order")
        return super().check_order(order, venue_time_ns)


def _events():
    out = []
    for i in range(6):
        t = T0 + i * SEC
        out.append(trade(t, price=100.0 + i))
        if i == 2:
            out.append(FundingEvent(received_time_ns=t, rate=0.0001))
        if i == 3:
            out.append(LiquidationEvent(received_time_ns=t, price=101.0, size=0.5, side="sell"))
    return out


class Trader(Recorder):
    """On each trade: a market buy, a resting limit, then (next trade) a
    cancel of that limit and a timer; the hooks named strategy.* raise AFTER
    the action, as a strategy bug after place_order would."""

    def __init__(self, inj: Injector) -> None:
        super().__init__()
        self.inj = inj
        self.resting: list[str] = []

    def on_event(self, event, ctx) -> None:
        super().on_event(event, ctx)
        self.inj.hit("strategy.on_event")
        if event.EVENT_TYPE.value != "TRADE":
            return
        ctx.place_order(OrderRequest("buy", "market", 0.1))
        self.inj.hit("strategy.after_market")
        self.resting.append(ctx.place_order(OrderRequest("buy", "limit", 0.1, price=1.0)))
        self.inj.hit("strategy.after_limit")
        if len(self.resting) >= 2:
            ctx.cancel_order(self.resting[-2])
            self.inj.hit("strategy.after_cancel")
        ctx.set_timer(ctx.now_ns + 500 * MS, "t")
        self.inj.hit("strategy.after_timer")


def _engine(inj: Injector) -> CoreEngine:
    return CoreEngine(Trader(inj), _events(), Fill(inj), Latency(inj), Cost(inj), Account(inj))


HOOKS = [
    "strategy.on_event", "strategy.after_market", "strategy.after_limit", "strategy.after_cancel",
    "strategy.after_timer", "latency.feed", "latency.order", "latency.cancel", "latency.notice",
    "fill.on_market_event", "fill.on_order", "fill.on_cancel", "cost.cost", "account.apply_fill",
    "account.apply_funding", "account.apply_liquidation", "account.on_market_event",
    "account.check_order",
]


def _assert_failed_for_good(eng: CoreEngine, original: BaseException) -> None:
    assert eng.failure is original
    now = eng.now_ns
    for call in (eng.step, eng.run, eng.result, eng.step):
        with pytest.raises(EngineFailedError) as info:
            call()
        assert info.value.__cause__ is original
        assert type(original).__name__ in str(info.value)
    assert eng.now_ns == now  # the refused calls moved nothing


def test_baseline_run_reaches_every_hook_three_times():
    inj = Injector()
    res = _engine(inj).run()
    for hook in HOOKS:
        assert inj.calls.get(hook, 0) >= (1 if "funding" in hook or "liquidation" in hook else 3), (
            hook, inj.calls)
    assert res.fills and res.cancel_requests


_ONCE = ("account.apply_funding", "account.apply_liquidation")  # one funding, one liquidation in the input
CASES = [(h, k) for h in HOOKS for k in (1, 2, 3) if k == 1 or h not in _ONCE]


@pytest.mark.parametrize("hook,k", CASES)
def test_exception_at_any_hook_leaves_the_engine_failed(hook, k):
    inj = Injector(hook, k)
    eng = _engine(inj)
    with pytest.raises(Boom) as info:
        eng.run()
    assert info.value is inj.exc  # re-raised unchanged
    _assert_failed_for_good(eng, inj.exc)


def test_critic_scene_order_placed_then_strategy_raises():
    # i0-r3-01, first case: the order is in the strategy's view but never sent
    inj = Injector("strategy.after_market", 1)
    eng = _engine(inj)
    with pytest.raises(Boom):
        eng.step()
        while eng.step():
            pass
    _assert_failed_for_good(eng, inj.exc)


def test_critic_scene_latency_raises_on_second_request():
    # i0-r3-01, second case: the first request is queued, the rest would be lost
    inj = Injector("latency.order", 2)
    eng = _engine(inj)
    with pytest.raises(Boom):
        eng.run()
    _assert_failed_for_good(eng, inj.exc)


def test_keyboard_interrupt_mid_step_also_fails_the_engine():
    inj = Injector("fill.on_order", 1, KeyboardInterrupt())
    eng = _engine(inj)
    with pytest.raises(KeyboardInterrupt):
        eng.run()
    _assert_failed_for_good(eng, inj.exc)


def test_core_errors_raised_mid_run_fail_the_engine():
    # the venue breaks its protocol (a second Ack)
    class DoubleAck(ImmediateFillModel):
        def on_order(self, order, venue_time_ns):
            return (Ack(order.client_order_id), Ack(order.client_order_id))

    def buy(ev, ctx):
        if ev.EVENT_TYPE.value == "TRADE":
            ctx.place_order(OrderRequest("buy", "limit", 1.0, price=1.0))

    eng = CoreEngine(Recorder(buy), [trade(T0), trade(T0 + SEC)], DoubleAck())
    with pytest.raises(VenueProtocolError) as info:
        eng.run()
    _assert_failed_for_good(eng, info.value)

    # a stream goes backwards after the run has started (read lazily)
    def stream():
        yield trade(T0 + 2 * SEC)
        yield trade(T0 + 3 * SEC)
        yield trade(T0 + SEC)

    eng = CoreEngine(Recorder(), stream())
    with pytest.raises(EventOrderError) as info:
        eng.run()
    _assert_failed_for_good(eng, info.value)

    # a latency model returns a negative delay
    class Negative(Latency):
        def order_delay_ns(self, order, sent_time_ns):
            return -1

    eng = CoreEngine(Recorder(buy), [trade(T0)], ImmediateFillModel(), Negative(Injector()))
    with pytest.raises(LatencyModelError) as info:
        eng.run()
    _assert_failed_for_good(eng, info.value)

    # end_time_ns in the wrong unit (before the first entry)
    eng = CoreEngine(Recorder(), [trade(T0)], end_time_ns=T0 // SEC)
    with pytest.raises(TimestampUnitError) as info:
        eng.step()
    _assert_failed_for_good(eng, info.value)


def test_an_error_the_strategy_catches_does_not_fail_the_engine():
    # a refused API call leaves no trace and does not escape the step
    refused = []

    def act(ev, ctx):
        if ev.EVENT_TYPE.value == "TRADE":
            ctx.place_order(OrderRequest("buy", "limit", 1.0, price=1.0, client_order_id=f"x{ev.seq}"))
            try:
                ctx.place_order(OrderRequest("buy", "limit", 1.0, price=1.0, client_order_id=f"x{ev.seq}"))
            except OrderApiError as exc:
                refused.append(exc)

    eng = CoreEngine(Recorder(act), [trade(T0), trade(T0 + SEC)], ImmediateFillModel())
    res = eng.run()
    assert eng.failure is None and len(refused) == 2
    assert [r.client_order_id for r in res.order_requests] == ["x1", "x3"] and set(res.orders) == {"x1", "x3"}
    assert eng.run() == res and eng.result() == res  # a finished run can be asked again


def test_reentry_is_refused_and_changes_nothing():
    def run_with(reenter: bool, catch: bool):
        holder: dict = {}
        caught = []

        def act(ev, ctx):
            if ev.EVENT_TYPE.value == "TRADE":
                ctx.place_order(OrderRequest("buy", "market", 0.1))
            if reenter and ev.seq == 2:
                for call in (holder["eng"].step, holder["eng"].run, holder["eng"].result):
                    if catch:
                        try:
                            call()
                        except EngineReentryError as exc:
                            caught.append(exc)
                    else:
                        call()

        eng = CoreEngine(Recorder(act), [trade(T0 + i * SEC) for i in range(4)], ImmediateFillModel(),
                         None, FixedRateCost(0.001))
        holder["eng"] = eng
        return eng, caught

    plain, _ = run_with(False, False)
    base = plain.run()
    eng, caught = run_with(True, True)
    res = eng.run()
    assert len(caught) == 3 and eng.failure is None
    assert res.delivery_digest == base.delivery_digest and res.fills == base.fills

    eng, _ = run_with(True, False)
    with pytest.raises(EngineReentryError) as info:
        eng.run()
    _assert_failed_for_good(eng, info.value)


def test_random_injection_points_seeded():
    rng = random.Random(20260924)
    for _ in range(150):
        hook = rng.choice(HOOKS)
        k = rng.randint(1, 4)
        inj = Injector(hook, k)
        eng = _engine(inj)
        steps = 0
        try:
            while eng.step():
                steps += 1
        except Boom as exc:
            assert exc is inj.exc
            _assert_failed_for_good(eng, exc)
        else:
            # the hook was not called k times in this run: the run is whole
            assert inj.calls.get(hook, 0) < k and eng.failure is None
            eng.result()


def test_contract_states_the_lifecycle():
    life = CORE_CONTRACT["lifecycle"]
    assert life["failed_after_escaped_exception"] is True and life["atomic_step"] is False
    assert "EngineFailedError" in life["rule"] and "EngineReentryError" in life["reentry"]

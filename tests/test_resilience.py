"""Execution resilience: fault injection against a mocked transport.

The bar these tests hold is the owner's 2019 failure mode — bitFlyer degrades
exactly during the move, orders delay or fail, and the position cannot be
exited — plus its mirror image, a duplicated real order. Every test here is
one of those two.

Nothing in this file touches the network.
"""
from __future__ import annotations

import random

import pytest
import requests

from bot.exchange import resilience
from bot.exchange.bitflyer_client import (
    BitflyerClient, BitflyerError, NetworkError, OrderStateUnknown,
)
from bot.exchange.resilience import (
    ApiHealthRecorder, ApiObserver, ConditionMonitor, EndpointClass,
    ExchangeCondition, FailureClass, Phase, RetryPolicy, Timeouts,
)
from bot.execution.gateway import ExecutionGateway, SubmitResult
from bot.order_management.manager import OrderManager
from bot.order_management.order import OrderState, OrderStore
from bot.order_management.reconciler import (
    AutoReconciler, ExchangeSnapshot, QueryOnlyExchange, Resolution,
)
from bot.risk.kill_switch import KillSwitch
from bot.settings import Secret
from tests.conftest import FakeResponse, FakeSession

ORDER_PATH = "/v1/me/sendchildorder"


# ---------------------------------------------------------------- taxonomy --
def test_taxonomy_presend_vs_ambiguous():
    order = EndpointClass.ORDER
    public = EndpointClass.PUBLIC

    connect = resilience.classify_exception(
        requests.exceptions.ConnectTimeout("x"), order)
    assert connect.failure_class is FailureClass.SAFE_RETRY
    assert connect.phase is Phase.PRE_SEND
    assert resilience.may_retry(connect, order)

    read = resilience.classify_exception(requests.exceptions.ReadTimeout("x"), order)
    assert read.failure_class is FailureClass.AMBIGUOUS
    assert not resilience.may_retry(read, order)

    # The same read timeout on an idempotent read endpoint is just a retry.
    read_public = resilience.classify_exception(
        requests.exceptions.ReadTimeout("x"), public)
    assert resilience.may_retry(read_public, public)

    # 5xx on an order endpoint: cannot prove it never reached placement.
    assert resilience.classify_status(503, order).failure_class is FailureClass.AMBIGUOUS
    assert resilience.classify_status(503, public).failure_class is FailureClass.SAFE_RETRY
    # 429 classifies retryable everywhere, but is NOT applied to order sends.
    rate = resilience.classify_status(429, order)
    assert rate.failure_class is FailureClass.SAFE_RETRY
    assert not resilience.may_retry(rate, order)
    # Business 4xx: definite, no retry, and not a signal about venue health.
    rejected = resilience.classify_status(400, order)
    assert rejected.failure_class is FailureClass.REJECTED
    assert not rejected.counts_as_unavailable


def test_unrecognised_transport_failure_is_ambiguous_on_order_endpoints():
    """The default must be the safe side, not the convenient one."""
    weird = requests.exceptions.ChunkedEncodingError("truncated")
    assert resilience.classify_exception(
        weird, EndpointClass.ORDER).failure_class is FailureClass.AMBIGUOUS
    # A bare ConnectionError with no new-connection marker: also ambiguous.
    bare = requests.exceptions.ConnectionError("reset by peer")
    assert resilience.classify_exception(
        bare, EndpointClass.ORDER).failure_class is FailureClass.AMBIGUOUS


def test_retry_policy_full_jitter_and_budget():
    policy = RetryPolicy(max_tries=3, total_budget_sec=10.0,
                         base_delay_sec=0.25, max_delay_sec=4.0)
    assert policy.allows(0, 0.0) and policy.allows(1, 0.0)
    assert not policy.allows(2, 0.0)          # 3 tries total
    assert not policy.allows(0, 11.0)         # budget spent
    # full jitter: uniform in [0, cap], cap = base * 2**attempt
    assert policy.delay_for(0, rand=lambda: 1.0) == pytest.approx(0.25)
    assert policy.delay_for(3, rand=lambda: 1.0) == pytest.approx(2.0)
    assert policy.delay_for(0, rand=lambda: 0.0) == 0.0
    # a Retry-After signal wins, but is still capped
    assert policy.delay_for(0, retry_after_sec=1.5) == pytest.approx(1.5)
    assert policy.delay_for(0, retry_after_sec=99.0) == pytest.approx(4.0)


def test_split_timeouts_widen_only_the_read_half():
    base = Timeouts(connect_sec=3.0, read_sec=10.0)
    assert base.as_tuple() == (3.0, 10.0)
    assert base.for_condition(ExchangeCondition.NORMAL).as_tuple() == (3.0, 10.0)
    assert base.for_condition(ExchangeCondition.DEGRADED).as_tuple() == (3.0, 20.0)
    assert base.for_condition(ExchangeCondition.CRITICAL).as_tuple() == (3.0, 30.0)


# --------------------------------------------------- (a) pre-send retries ---
def test_presend_failures_retry_within_budget_then_succeed(fake_session):
    """(a) Connection refused twice, then the venue answers — one order."""
    refused = requests.exceptions.ConnectionError(
        "Failed to establish a new connection: [Errno 111] Connection refused")
    fake_session.set("POST", ORDER_PATH, [
        refused, refused,
        FakeResponse(200, {"child_order_acceptance_id": "ACC-1"}),
    ])
    client = BitflyerClient(Secret("k"), Secret("s"), session=fake_session,
                            sleep=lambda s: None)
    resp = client.send_child_order(product_code="FX_BTC_JPY", side="BUY", size=0.01)
    assert resp["child_order_acceptance_id"] == "ACC-1"
    # Three attempts, but only ONE of them ever reached the exchange.
    assert len(fake_session.order_calls()) == 3


def test_public_read_retries_then_succeeds(fake_session):
    fake_session.set("GET", "/v1/ticker", [
        requests.exceptions.ReadTimeout("slow"),
        FakeResponse(200, {"ltp": 1.0, "best_bid": 1.0, "best_ask": 1.0}),
    ])
    client = BitflyerClient(session=fake_session, sleep=lambda s: None)
    assert client.ticker("FX_BTC_JPY")["ltp"] == 1.0


# ------------------------------------------------------ reconciler harness --
class FakeExchange:
    """Query-only stand-in for getchildorders / getpositions.

    `orders`/`positions` are call-indexed scripts so a test can make the venue
    answer 'nothing here' for the first poll and reveal the order on the next.
    """

    def __init__(self, order_scripts=None, position_scripts=None):
        self._orders = order_scripts if order_scripts is not None else [[]]
        self._positions = position_scripts if position_scripts is not None else [[]]
        self.order_queries = 0
        self.position_queries = 0

    def child_orders(self, symbol):
        i = min(self.order_queries, len(self._orders) - 1)
        self.order_queries += 1
        result = self._orders[i]
        if isinstance(result, Exception):
            raise result
        return result

    def positions(self, symbol):
        i = min(self.position_queries, len(self._positions) - 1)
        self.position_queries += 1
        result = self._positions[i]
        if isinstance(result, Exception):
            raise result
        return result


class AmbiguousGateway(ExecutionGateway):
    """Gateway whose sends fail ambiguously. Counts every send attempt so a
    resend is impossible to miss."""

    def __init__(self, fail_times: int = 1):
        self.sends = 0
        self.fail_times = fail_times
        self.canceled = []

    def submit_order(self, *, symbol, side, size, order_type, price):
        self.sends += 1
        if self.sends <= self.fail_times:
            raise OrderStateUnknown("read timeout on sendchildorder")
        return SubmitResult(acceptance_id=f"ACC-{self.sends}")

    def cancel_order(self, *, symbol, acceptance_id):
        self.canceled.append(acceptance_id)

    def fetch_order_status(self, *, symbol, acceptance_id):
        return None


def build_manager(tmp_path, gateway, exchange, **kw):
    store = OrderStore(tmp_path / "orders.sqlite3")
    ks = KillSwitch(state_dir=tmp_path, manual_file=tmp_path / "KILL")
    reconciler = AutoReconciler(exchange, sleep=lambda s: None,
                                clock=_StepClock(), **kw)
    notifier = RecordingNotifier()
    return OrderManager(store, gateway, ks, reconciler=reconciler,
                        notifier=notifier), store, ks, notifier


class _StepClock:
    """Monotonic clock that advances 1s per read: makes the budget deterministic."""

    def __init__(self, step: float = 1.0):
        self.t = 0.0
        self.step = step

    def __call__(self) -> float:
        self.t += self.step
        return self.t


class RecordingNotifier:
    def __init__(self):
        self.sent = []

    def send(self, title, message, *, urgent=False):
        self.sent.append((title, message, urgent))
        return True


# --------------------------------------- (b) ambiguous -> FILLED, no resend --
def test_ambiguous_send_reconciles_to_filled_with_zero_resends(tmp_path):
    """(b) The order DID land. The reconciler sees it and trading continues."""
    placed = [{"child_order_acceptance_id": "ACC-NEW", "side": "BUY",
               "size": 0.01, "child_order_state": "COMPLETED",
               "executed_size": 0.01, "average_price": 11_000_000}]
    exchange = FakeExchange(order_scripts=[[], placed])
    gateway = AmbiguousGateway(fail_times=1)
    manager, store, ks, notifier = build_manager(tmp_path, gateway, exchange)

    order = manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)

    assert order.state is OrderState.FILLED
    assert order.acceptance_id == "ACC-NEW"
    assert order.filled_size == 0.01
    assert order.avg_fill_price == 11_000_000
    assert gateway.sends == 1                 # ZERO resends
    assert not ks.is_tripped                  # resolved -> normal operation
    assert store.unknown_orders() == []
    assert notifier.sent == []


def test_ambiguous_send_reconciles_from_the_position(tmp_path):
    """A fill can reach getpositions before getchildorders lists it."""
    exchange = FakeExchange(order_scripts=[[]],
                            position_scripts=[[], [{"side": "BUY", "size": 0.01}]])
    gateway = AmbiguousGateway(fail_times=1)
    manager, store, ks, _ = build_manager(tmp_path, gateway, exchange)
    order = manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)
    assert order.state is OrderState.FILLED
    assert gateway.sends == 1
    assert not ks.is_tripped


# ----------------------------------- (c) ambiguous -> NOT_PLACED, no resend --
def test_ambiguous_send_reconciles_to_not_placed_and_closes_the_record(tmp_path):
    """(c) The order never landed. The record is closed; still zero resends."""
    exchange = FakeExchange(order_scripts=[[]], position_scripts=[[]])
    gateway = AmbiguousGateway(fail_times=1)
    manager, store, ks, notifier = build_manager(tmp_path, gateway, exchange)

    order = manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)

    assert order.state is OrderState.REJECTED     # terminal: record closed
    assert order.is_terminal
    assert gateway.sends == 1                     # the bot did NOT re-send
    assert not ks.is_tripped
    assert store.unknown_orders() == []
    assert notifier.sent == []
    # Two clean polls before declaring absence: absence of evidence is only
    # accepted after confirmation.
    assert exchange.order_queries >= 2


def test_failed_poll_is_not_evidence_of_absence(tmp_path):
    """A getchildorders that itself fails must not count towards NOT_PLACED."""
    boom = NetworkError("getchildorders timed out")
    placed = [{"child_order_acceptance_id": "ACC-NEW", "side": "BUY",
               "size": 0.01, "child_order_state": "ACTIVE", "executed_size": 0.0}]
    # [0] is consumed by the pre-send snapshot; the two failures land on the
    # reconciliation polls.
    exchange = FakeExchange(order_scripts=[[], boom, boom, placed],
                            position_scripts=[[]])
    gateway = AmbiguousGateway(fail_times=1)
    manager, store, ks, _ = build_manager(tmp_path, gateway, exchange)
    order = manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)
    assert order.state is OrderState.SUBMITTED    # ACTIVE on the exchange
    assert gateway.sends == 1


# ------------------------------- (d) budget exhaustion -> STATE_UNKNOWN kept --
def test_budget_exhaustion_keeps_state_unknown_and_alerts(tmp_path):
    """(d) Undecided at the budget end: the human path, exactly as before."""
    boom = NetworkError("exchange unreachable")
    exchange = FakeExchange(order_scripts=[boom], position_scripts=[boom])
    gateway = AmbiguousGateway(fail_times=1)
    manager, store, ks, notifier = build_manager(tmp_path, gateway, exchange,
                                                 budget_sec=5.0)

    order = manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)

    assert order.state is OrderState.STATE_UNKNOWN
    assert ks.is_tripped
    assert store.unknown_orders()
    assert notifier.sent and notifier.sent[0][0] == "ORDER STATE UNKNOWN"
    assert notifier.sent[0][2] is True                # urgent
    assert gateway.sends == 1
    # ...and the block on further submissions is untouched.
    with pytest.raises(RuntimeError, match="unknown state"):
        manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)
    assert gateway.sends == 1


def test_reconciler_cannot_send_an_order():
    """Structural guarantee: the object the reconciler holds has no way to
    place an order, so auto-reconciliation cannot become a resend path."""
    client = object()
    exchange = QueryOnlyExchange(client)
    public = [n for n in dir(exchange) if not n.startswith("_")]
    assert sorted(public) == ["child_orders", "positions"]
    for forbidden in ("send_child_order", "cancel_child_order", "submit_order",
                      "send", "cancel", "sendchildorder"):
        assert not hasattr(exchange, forbidden)


# ---------------------------- (e) duplicate-order impossibility (property) ---
class FaultyOrderSession:
    """Randomized transport for /v1/me/sendchildorder.

    Each scripted attempt declares whether the request was DELIVERED to the
    order engine. A pre-send fault by definition is not delivered; an ambiguous
    or response fault is. `placed` counts how many orders the exchange would
    actually hold — the number that must never exceed the intended count.
    """

    PRE_SEND_FAULTS = (
        lambda: requests.exceptions.ConnectTimeout("connect timed out"),
        lambda: requests.exceptions.ProxyError("no proxy"),
        lambda: requests.exceptions.ConnectionError(
            "Failed to establish a new connection: [Errno 111] Connection refused"),
        lambda: requests.exceptions.ConnectionError(
            "NewConnectionError: Name or service not known"),
    )
    DELIVERED_FAULTS = (
        lambda: requests.exceptions.ReadTimeout("read timed out"),
        lambda: requests.exceptions.ConnectionError("connection reset by peer"),
        lambda: requests.exceptions.ChunkedEncodingError("truncated"),
        lambda: FakeResponse(500, {"error_message": "internal"}),
        lambda: FakeResponse(503, {"error_message": "unavailable"}),
        lambda: FakeResponse(429, {"error_message": "over limit"}),
        lambda: FakeResponse(400, {"error_message": "bad size"}),
    )

    def __init__(self, script):
        self.script = list(script)
        self.attempts = 0
        self.placed = 0

    def request(self, method, url, params=None, data=None, headers=None, timeout=None):
        self.attempts += 1
        if not self.script:
            self.placed += 1
            return FakeResponse(200, {"child_order_acceptance_id": f"ACC-{self.placed}"})
        delivered, factory = self.script.pop(0)
        if delivered:
            self.placed += 1
        result = factory()
        if isinstance(result, Exception):
            raise result
        return result


@pytest.mark.parametrize("seed", [11])
def test_property_sent_order_count_never_exceeds_intended(seed):
    """(e) 1000 randomized fault sequences: the exchange never ends up holding
    more orders than the bot intended to place."""
    rng = random.Random(seed)
    for _ in range(1000):
        script = []
        for _ in range(rng.randint(1, 6)):
            delivered = rng.random() < 0.5
            pool = (FaultyOrderSession.DELIVERED_FAULTS if delivered
                    else FaultyOrderSession.PRE_SEND_FAULTS)
            script.append((delivered, rng.choice(pool)))
        session = FaultyOrderSession(script)
        client = BitflyerClient(Secret("k"), Secret("s"), session=session,
                                sleep=lambda s: None,
                                retry_policy=RetryPolicy(max_tries=4,
                                                         total_budget_sec=10.0))
        try:
            client.send_child_order(product_code="FX_BTC_JPY", side="BUY", size=0.01)
        except (OrderStateUnknown, BitflyerError, NetworkError):
            pass
        # ONE intended order -> at most one order can exist on the exchange.
        assert session.placed <= 1, script


def test_property_manager_never_resends_across_fault_sequences(tmp_path):
    """The same property one layer up: whatever the reconciler concludes, the
    order manager issues exactly one send per intended order."""
    rng = random.Random(7)
    for i in range(200):
        store = OrderStore(tmp_path / f"orders-{i}.sqlite3")
        ks = KillSwitch(state_dir=tmp_path / f"ks-{i}",
                        manual_file=tmp_path / f"KILL-{i}")
        landed = rng.random() < 0.5
        orders = [[{"child_order_acceptance_id": "ACC-NEW", "side": "BUY",
                    "size": 0.01, "child_order_state": "COMPLETED",
                    "executed_size": 0.01, "average_price": 1.0}]] if landed else [[]]
        exchange = FakeExchange(order_scripts=orders, position_scripts=[[]])
        gateway = AmbiguousGateway(fail_times=1)
        manager = OrderManager(
            store, gateway, ks,
            reconciler=AutoReconciler(exchange, sleep=lambda s: None,
                                      clock=_StepClock()),
            notifier=RecordingNotifier())
        manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)
        assert gateway.sends == 1


# ------------------------- (f) closing allowed under CRITICAL, entry barred --
class _App:
    """Just the state `_entry_allowed_under_condition` reads, so the gate can
    be exercised against a real ConditionMonitor without booting the app."""

    def __init__(self, condition, monitor):
        self.condition = condition
        self.condition_monitor = monitor
        self._degraded_entry_seq = 0


def _make_app(condition, health=None):
    from bot.main import TradingApp
    monitor = ConditionMonitor()
    if health:
        monitor.observe_health(health)
    app = _App(condition, monitor)
    app._entry_allowed_under_condition = \
        TradingApp._entry_allowed_under_condition.__get__(app, _App)
    return app


def test_critical_suppresses_entries_but_never_closing():
    """(f) The 2019 trap: closing must work at EVERY level."""
    app = _make_app(ExchangeCondition.CRITICAL)
    assert app._entry_allowed_under_condition() is False

    # And the gate is unreachable from the closing path: in TradingApp it sits
    # inside `if opening:`, so a sized (closing) order never consults it.
    from bot.main import TradingApp
    import inspect
    src = inspect.getsource(TradingApp._try_order)
    gate_at = src.index("_entry_allowed_under_condition()")
    opening_at = src.index("if opening:")
    sizing_at = src.index("equity = self.portfolio.equity_jpy")
    assert opening_at < gate_at < sizing_at, \
        "the degradation gate must live inside the opening-only branch"


def test_exchange_stop_suppresses_entries():
    app = _make_app(ExchangeCondition.CRITICAL, health="STOP")
    assert app.condition_monitor.exchange_stopped
    assert app._entry_allowed_under_condition() is False


def test_degraded_halves_entry_frequency():
    app = _make_app(ExchangeCondition.DEGRADED)
    taken = [app._entry_allowed_under_condition() for _ in range(6)]
    assert taken == [True, False, True, False, True, False]


def test_normal_allows_every_entry():
    app = _make_app(ExchangeCondition.NORMAL)
    assert all(app._entry_allowed_under_condition() for _ in range(5))


def test_closing_order_path_is_invariant_under_every_condition(tmp_path, monkeypatch):
    """End-to-end on the real app: a CRITICAL venue must still let the
    protective stop flatten a position."""
    app = _paper_app(tmp_path, monkeypatch)
    from bot.market_data.feed import Tick
    tick = Tick(timestamp=1.0, price=10_000_000, best_bid=9_999_000,
                best_ask=10_001_000)
    app.feed.last_tick = tick
    # Open at NORMAL.
    order = app._try_order("BUY", tick)
    assert order is not None and app.portfolio.position_size > 0
    size = app.portfolio.position_size

    # Venue goes CRITICAL: no new entries...
    app.condition = ExchangeCondition.CRITICAL
    assert app._try_order("BUY", tick) is None
    # ...but the exit still goes through.
    closing = app._try_order("SELL", tick, size=size)
    assert closing is not None
    assert app.portfolio.position_size == pytest.approx(0.0)


def _paper_app(tmp_path, monkeypatch):
    import shutil
    from pathlib import Path

    from bot.main import TradingApp
    from bot.monitoring.notifier import NullNotifier
    from bot.settings import Mode, RiskLimits, Settings

    repo = Path(__file__).resolve().parents[1]
    shutil.copytree(repo / "config", tmp_path / "config")
    monkeypatch.chdir(tmp_path)
    config = {
        "product_code": "FX_BTC_JPY", "candle_interval_sec": 60,
        "paper_equity_jpy": 200000, "sfd_guard_pct": 4.5, "stop_loss_pct": 0.5,
        "strategy": {"name": "xborder_momentum",
                     "params": {"k": 2, "thr_pct": 0.15, "exit_pct": 0.03}},
        "costs": {"slippage_pct": 0.0},
        "market_data": {"max_staleness_sec": 3600, "max_price_jump_pct": 50,
                        "max_spread_pct": 5.0},
    }
    limits = RiskLimits.from_dict({
        "MAX_ORDER_SIZE_JPY": 130000, "MAX_POSITION_SIZE_JPY": 130000,
        "MAX_DAILY_LOSS_JPY": 6000, "MAX_DRAWDOWN_PCT": 10.0,
        "MAX_OPEN_ORDERS": 1, "MAX_CONSECUTIVE_LOSSES": 5,
        "MAX_API_ERRORS_IN_ROW": 5,
    })
    settings = Settings(mode=Mode.PAPER, product_code="FX_BTC_JPY",
                        config=config, risk_limits=limits)
    session = FakeSession()
    session.set("GET", "/v1/ticker", FakeResponse(200, {
        "ltp": 10_000_000, "best_bid": 9_999_000, "best_ask": 10_001_000}))
    client = BitflyerClient(session=session, sleep=lambda s: None)
    return TradingApp(settings, client, NullNotifier())


def test_app_reacts_to_a_busy_gethealth(tmp_path, monkeypatch):
    """End-to-end on the paper app: /v1/gethealth says VERY BUSY -> the app
    goes DEGRADED, the READ timeout doubles, the connect timeout does not, and
    telemetry lands in data/api_health.csv."""
    app = _paper_app(tmp_path, monkeypatch)
    base = app.client.timeouts.as_tuple()
    app.client._session.set("GET", "/v1/gethealth",
                            FakeResponse(200, {"status": "VERY BUSY"}))
    app._last_health_poll = 0.0
    app._refresh_condition()

    assert app.condition is ExchangeCondition.DEGRADED
    connect, read = app.client.timeouts.as_tuple()
    assert connect == base[0]                 # connect half untouched
    assert read == pytest.approx(base[1] * 2)
    assert app._entry_allowed_under_condition() is True    # 1st of 2
    assert app._entry_allowed_under_condition() is False   # frequency halved
    rows = (tmp_path / "data" / "api_health.csv").read_text(
        encoding="utf-8").splitlines()[1:]
    assert any("/v1/gethealth" in r for r in rows)


def test_app_status_carries_the_api_condition(tmp_path, monkeypatch):
    app = _paper_app(tmp_path, monkeypatch)
    app.condition_monitor.observe_health("SUPER BUSY")
    app._update_status(10_000_000)
    s = app.status.status
    assert s.api_condition == "CRITICAL"
    assert s.api_health_status == "SUPER BUSY"
    assert s.api_error_rate is not None


def test_paper_mode_has_no_reconciler(tmp_path, monkeypatch):
    """PAPER's executor is local, so ambiguity cannot arise and there is
    nothing for a reconciler to query."""
    app = _paper_app(tmp_path, monkeypatch)
    assert app.orders._reconciler is None


# ------------------------------------------------- (g) condition hysteresis --
def test_condition_does_not_flap_on_alternating_samples():
    """(g) Alternating fast/slow samples must not toggle the level."""
    clock = _StepClock(step=1.0)
    monitor = ConditionMonitor(min_samples=2, recovery_samples=3,
                               min_dwell_sec=30.0, alpha=1.0,
                               degraded_latency_ms=1000.0,
                               critical_latency_ms=9e9, clock=clock)
    seen = []
    for i in range(40):
        monitor.observe(2000.0 if i % 2 == 0 else 50.0)
        seen.append(monitor.condition)
    transitions = sum(1 for a, b in zip(seen, seen[1:]) if a is not b)
    assert transitions <= 1, [c.value for c in seen]
    assert monitor.condition is ExchangeCondition.DEGRADED


def test_condition_escalates_immediately_and_recovers_slowly():
    clock = _StepClock(step=10.0)
    monitor = ConditionMonitor(min_samples=1, recovery_samples=3,
                               min_dwell_sec=30.0, alpha=1.0,
                               degraded_latency_ms=1000.0,
                               critical_latency_ms=3000.0, clock=clock)
    monitor.observe(5000.0)
    assert monitor.condition is ExchangeCondition.CRITICAL   # no delay upward
    monitor.observe(10.0)
    assert monitor.condition is ExchangeCondition.CRITICAL   # one calm sample: no
    monitor.observe(10.0)
    monitor.observe(10.0)
    assert monitor.condition is ExchangeCondition.NORMAL


def test_health_status_drives_the_condition():
    monitor = ConditionMonitor()
    assert monitor.condition is ExchangeCondition.NORMAL
    monitor.observe_health("BUSY")
    assert monitor.condition is ExchangeCondition.DEGRADED
    monitor.observe_health("SUPER BUSY")
    assert monitor.condition is ExchangeCondition.CRITICAL
    monitor.observe_health("STOP")
    assert monitor.exchange_stopped


def test_business_4xx_does_not_look_like_degradation():
    monitor = ConditionMonitor(min_samples=1)
    failure = resilience.classify_status(404, EndpointClass.PUBLIC)
    for _ in range(10):
        monitor.observe(20.0, unavailable=failure.counts_as_unavailable)
    assert monitor.condition is ExchangeCondition.NORMAL
    assert monitor.error_rate == 0.0


# ---------------------------------------- (h) telemetry failure is harmless --
def test_telemetry_write_failure_never_disturbs_trading(tmp_path, fake_session):
    """(h) An unwritable telemetry path must not reach the request path."""
    class BrokenRecorder(ApiHealthRecorder):
        def record(self, **kw):
            raise OSError("disk full")

    recorder = BrokenRecorder(tmp_path / "api_health.csv")
    monitor = ConditionMonitor()
    client = BitflyerClient(session=fake_session, sleep=lambda s: None,
                            observer=ApiObserver(monitor, recorder))
    fake_session.set("GET", "/v1/ticker", FakeResponse(200, {
        "ltp": 1.0, "best_bid": 1.0, "best_ask": 1.0}))
    assert client.ticker("FX_BTC_JPY")["ltp"] == 1.0   # trading unaffected


def test_recorder_swallows_an_unwritable_path(tmp_path):
    blocked = tmp_path / "afile"
    blocked.write_text("not a directory", encoding="utf-8")
    recorder = ApiHealthRecorder(blocked / "nested" / "api_health.csv")
    recorder.record(ts=1.0, endpoint_class="public", endpoint="/v1/ticker",
                    latency_ms=1.0, outcome="ok", condition="NORMAL", health=None)


def test_recorder_appends_and_rotates(tmp_path):
    path = tmp_path / "api_health.csv"
    recorder = ApiHealthRecorder(path, max_bytes=200, check_every=1)
    for i in range(20):
        recorder.record(ts=float(i), endpoint_class="public", endpoint="/v1/ticker",
                        latency_ms=12.5, outcome="ok", condition="NORMAL",
                        health="NORMAL")
    assert path.exists()
    assert path.with_suffix(".csv.1").exists()          # rotated, stays small
    assert path.stat().st_size < 400


def test_observer_records_every_call(tmp_path, fake_session):
    path = tmp_path / "api_health.csv"
    monitor = ConditionMonitor()
    client = BitflyerClient(session=fake_session, sleep=lambda s: None,
                            observer=ApiObserver(monitor, ApiHealthRecorder(path)))
    fake_session.set("GET", "/v1/ticker", FakeResponse(200, {
        "ltp": 1.0, "best_bid": 1.0, "best_ask": 1.0}))
    fake_session.set("GET", "/v1/executions", FakeResponse(200, []))
    client.ticker("FX_BTC_JPY")
    client.executions("FX_BTC_JPY")
    rows = [r for r in path.read_text(encoding="utf-8").splitlines()[1:] if r]
    assert len(rows) == 2
    assert all(r.split(",")[1] == "public" and r.split(",")[4] == "ok" for r in rows)


def test_feed_polls_are_instrumented(tmp_path, fake_session):
    """The paper bot's own public polls must accrue telemetry: that is how the
    live timeouts get tuned on data instead of guesses."""
    from bot.market_data.feed import CandleBuilder, MarketDataFeed
    path = tmp_path / "api_health.csv"
    monitor = ConditionMonitor()
    client = BitflyerClient(session=fake_session, sleep=lambda s: None,
                            observer=ApiObserver(monitor, ApiHealthRecorder(path)))
    fake_session.set("GET", "/v1/ticker", FakeResponse(200, {
        "ltp": 10_000_000, "best_bid": 9_999_000, "best_ask": 10_001_000}))
    fake_session.set("GET", "/v1/executions", FakeResponse(200, []))
    feed = MarketDataFeed(client, "FX_BTC_JPY", max_spread_pct=5.0)
    feed.poll_ticker()
    feed.poll_executions(CandleBuilder(60))
    endpoints = [r.split(",")[2] for r in
                 path.read_text(encoding="utf-8").splitlines()[1:] if r]
    assert endpoints == ["/v1/ticker", "/v1/executions"]
    assert monitor.snapshot()["samples"] == 2


# --------------------------------------------------------- aggregate + tile --
def test_aggregate_exposes_api_health(tmp_path):
    from bot.monitoring.aggregate import collect_status
    now = 1_000_000.0
    (tmp_path / "data").mkdir()
    (tmp_path / "logs").mkdir()
    lines = [ApiHealthRecorder.HEADER.rstrip("\n")]
    for i in range(100):
        latency = 2000.0 if i >= 90 else 40.0
        outcome = "safe_retry" if i >= 98 else "ok"
        lines.append(f"{now - 60 + i},public,/v1/ticker,{latency},{outcome},"
                     f"DEGRADED,VERY BUSY")
    # a torn line and an ancient line must both be tolerated
    lines.append("999")
    lines.append(f"{now - 99999},public,/v1/ticker,5.0,ok,NORMAL,NORMAL")
    (tmp_path / "data" / "api_health.csv").write_text("\n".join(lines) + "\n",
                                                      encoding="utf-8")
    d = collect_status(tmp_path, now=now)
    api = d["api_health"]
    assert api["samples"] == 100
    assert api["p50_ms"] == 40.0
    assert api["p95_ms"] == 2000.0
    assert api["error_rate"] == pytest.approx(0.02)
    assert api["condition"] == "DEGRADED"
    assert api["health"] == "VERY BUSY"


def test_aggregate_api_health_falls_back_to_status_json(tmp_path):
    import json

    from bot.monitoring.aggregate import collect_status
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "status.json").write_text(json.dumps({
        "mode": "paper", "updated_at": 1_000_000.0,
        "api_condition": "CRITICAL", "api_health_status": "SUPER BUSY",
        "api_error_rate": 0.6}), encoding="utf-8")
    api = collect_status(tmp_path, now=1_000_000.0)["api_health"]
    assert api["condition"] == "CRITICAL"
    assert api["health"] == "SUPER BUSY"
    assert api["p95_ms"] is None


def test_dashboard_page_has_the_api_tile():
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / "scripts" / "dashboard.py"
    text = src.read_text(encoding="utf-8")
    assert "function apiTile(" in text
    assert "apiTile(d.api_health)" in text
    assert "API状態" in text


# ------------------------------------------------------------- resolution ---
def test_resolution_states_map_to_terminal_or_active():
    from bot.order_management.manager import _RESOLUTION_TO_LOCAL
    assert _RESOLUTION_TO_LOCAL["NOT_PLACED"] is OrderState.REJECTED
    assert _RESOLUTION_TO_LOCAL["FILLED"] is OrderState.FILLED
    assert _RESOLUTION_TO_LOCAL["ACTIVE"] is OrderState.SUBMITTED
    assert Resolution("UNRESOLVED").resolved is False
    assert Resolution("FILLED").resolved is True


def test_snapshot_ignores_orders_that_already_existed(tmp_path):
    """An order that predates the send must never be mistaken for ours."""
    existing = [{"child_order_acceptance_id": "OLD", "side": "BUY", "size": 0.01,
                 "child_order_state": "ACTIVE", "executed_size": 0.0}]
    exchange = FakeExchange(order_scripts=[existing], position_scripts=[[]])
    reconciler = AutoReconciler(exchange, sleep=lambda s: None, clock=_StepClock())
    snap = reconciler.snapshot("FX_BTC_JPY")
    assert snap.acceptance_ids == frozenset({"OLD"})
    res = reconciler.resolve(symbol="FX_BTC_JPY", side="BUY", size=0.01,
                             snapshot=snap)
    assert res.state == "NOT_PLACED"


def test_snapshot_failure_disables_auto_reconciliation_but_not_trading(tmp_path):
    class BrokenExchange:
        def child_orders(self, symbol):
            raise NetworkError("down")

        def positions(self, symbol):
            raise NetworkError("down")

    gateway = AmbiguousGateway(fail_times=0)
    store = OrderStore(tmp_path / "orders.sqlite3")
    ks = KillSwitch(state_dir=tmp_path, manual_file=tmp_path / "KILL")
    manager = OrderManager(store, gateway, ks,
                           reconciler=AutoReconciler(BrokenExchange(),
                                                     sleep=lambda s: None),
                           notifier=RecordingNotifier())
    order = manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)
    assert order.state is OrderState.SUBMITTED     # the send still happened
    assert gateway.sends == 1


def test_position_size_of_signs_by_side():
    from bot.order_management.reconciler import position_size_of
    assert position_size_of([{"side": "BUY", "size": 0.02}]) == 0.02
    assert position_size_of([{"side": "SELL", "size": 0.02}]) == -0.02
    assert position_size_of([{"side": "BUY", "size": 0.02},
                             {"side": "SELL", "size": 0.005}]) == pytest.approx(0.015)
    assert position_size_of([]) == 0.0
    assert position_size_of([{"side": "BUY", "size": "nope"}]) == 0.0


def test_snapshot_unions_locally_known_acceptance_ids(tmp_path):
    """An acceptance id already in our own book can never be read as the order
    we are about to send, even if the snapshot poll omitted it."""
    store = OrderStore(tmp_path / "orders.sqlite3")
    old = store.create("FX_BTC_JPY", "BUY", 0.01, "MARKET", None)
    store.transition(old.local_id, OrderState.SUBMITTED, acceptance_id="ACC-OLD")
    store.transition(old.local_id, OrderState.FILLED, filled_size=0.01)
    # The venue "forgets" ACC-OLD on the snapshot poll but lists it afterwards.
    listed = [{"child_order_acceptance_id": "ACC-OLD", "side": "BUY",
               "size": 0.01, "child_order_state": "COMPLETED",
               "executed_size": 0.01, "average_price": 1.0}]
    exchange = FakeExchange(order_scripts=[[], listed], position_scripts=[[]])
    ks = KillSwitch(state_dir=tmp_path, manual_file=tmp_path / "KILL")
    manager = OrderManager(
        store, AmbiguousGateway(fail_times=1), ks,
        reconciler=AutoReconciler(exchange, sleep=lambda s: None,
                                  clock=_StepClock()),
        notifier=RecordingNotifier())
    order = manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)
    assert order.state is OrderState.REJECTED      # NOT_PLACED, not "our fill"
    assert order.acceptance_id is None


def test_snapshot_type_is_frozen():
    snap = ExchangeSnapshot(frozenset({"A"}), 0.0, 0.0)
    with pytest.raises(Exception):
        snap.position_size = 1.0

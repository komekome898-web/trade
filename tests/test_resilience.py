"""Execution resilience: fault injection against a mocked transport.

The bar these tests hold is the owner's 2019 failure mode — bitFlyer degrades
exactly during the move, orders delay or fail, and the position cannot be
exited — plus its mirror image, a duplicated real order. Every test here is
one of those two.

Nothing in this file touches the network.
"""
from __future__ import annotations

import inspect
import random
import sqlite3

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
    # ...while a 429 IS a signal about venue health. It is never REJECTED, so
    # `counts_as_unavailable` has no 429 special case to make.
    assert rate.counts_as_unavailable
    # The classification travels with the failure, so a caller that only sees
    # the raised exception can still tell where it happened.
    assert rejected.endpoint_class is order
    assert read.endpoint_class is order


def _requests_exception_types():
    """Every exception class `requests.exceptions` exports, instantiable with a
    single message argument. This is the taxonomy's full surface."""
    out = []
    for name, obj in sorted(vars(requests.exceptions).items()):
        if not inspect.isclass(obj) or not issubclass(obj, BaseException):
            continue
        try:
            obj("x")
        except Exception:
            continue
        out.append((name, obj))
    return out


@pytest.mark.parametrize("name,exc_type", _requests_exception_types(),
                         ids=[n for n, _ in _requests_exception_types()])
def test_order_endpoint_makes_exactly_one_attempt_for_every_exception(
        name, exc_type, fake_session):
    """THE hard invariant, over the whole exception surface.

    On an ORDER endpoint every failure gets exactly ONE attempt, except the two
    provable pre-send classes (a connect timeout, and a connection error whose
    text names the new-connection failure) — those are sanctioned and tested
    separately below. A plain one-argument message carries no such marker, so
    ConnectTimeout is the only row here that may repeat.
    """
    fake_session.set("POST", ORDER_PATH, exc_type("x"))
    client = BitflyerClient(Secret("k"), Secret("s"), session=fake_session,
                            sleep=lambda s: None)
    try:
        client.send_child_order(product_code="FX_BTC_JPY", side="BUY", size=0.01)
    except BaseException:
        pass
    expected = 3 if exc_type is requests.exceptions.ConnectTimeout else 1
    assert len(fake_session.order_calls()) == expected, name


@pytest.mark.parametrize("message", [
    # OpenSSL renders alerts in lowercase, and a TLS alert can arrive AFTER the
    # request body was written — a venue LB tearing the session down under load.
    "[SSL: TLSV1_ALERT_INTERNAL_ERROR] tlsv1 alert internal error (_ssl.c:1006)",
    "[SSL: SSLV3_ALERT_BAD_RECORD_MAC] sslv3 alert bad record mac (_ssl.c:2578)",
    "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed",
    "EOF occurred in violation of protocol",
])
def test_every_ssl_error_on_an_order_endpoint_is_ambiguous(message, fake_session):
    """There is no string that separates a handshake alert from a mid-stream
    one, so no SSLError may ever be called provably pre-send."""
    failure = resilience.classify_exception(
        requests.exceptions.SSLError(message), EndpointClass.ORDER)
    assert failure.failure_class is FailureClass.AMBIGUOUS
    assert not resilience.may_retry(failure, EndpointClass.ORDER)

    fake_session.set("POST", ORDER_PATH, requests.exceptions.SSLError(message))
    client = BitflyerClient(Secret("k"), Secret("s"), session=fake_session,
                            sleep=lambda s: None)
    with pytest.raises(OrderStateUnknown):
        client.send_child_order(product_code="FX_BTC_JPY", side="BUY", size=0.01)
    assert len(fake_session.order_calls()) == 1


def test_proxy_error_on_an_order_endpoint_is_ambiguous(fake_session):
    """urllib3 1.26 wraps a post-send reset into ProxyError whenever a proxy is
    configured, so ProxyError proves nothing about delivery."""
    failure = resilience.classify_exception(
        requests.exceptions.ProxyError("Cannot connect to proxy."),
        EndpointClass.ORDER)
    assert failure.failure_class is FailureClass.AMBIGUOUS

    fake_session.set("POST", ORDER_PATH,
                     requests.exceptions.ProxyError("Cannot connect to proxy."))
    client = BitflyerClient(Secret("k"), Secret("s"), session=fake_session,
                            sleep=lambda s: None)
    with pytest.raises(OrderStateUnknown):
        client.send_child_order(product_code="FX_BTC_JPY", side="BUY", size=0.01)
    assert len(fake_session.order_calls()) == 1


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


def test_retry_after_accepts_both_header_forms():
    """RFC 9110 allows delta-seconds and an HTTP-date; edges in front of an
    exchange do send the date form. Parsing only one silently threw the venue's
    own backoff signal away."""
    import email.utils

    class R:
        def __init__(self, value):
            self.headers = {"Retry-After": value}

    assert resilience.retry_after_of(R("2.5")) == pytest.approx(2.5)
    assert resilience.retry_after_of(R("-1")) == 0.0
    assert resilience.retry_after_of(R(None)) is None
    assert resilience.retry_after_of(R("nonsense")) is None
    when = email.utils.formatdate(1_000_000.0 + 7.0, usegmt=True)
    assert resilience.retry_after_of(R(when), now=1_000_000.0) == pytest.approx(7.0)
    past = email.utils.formatdate(999_000.0, usegmt=True)
    assert resilience.retry_after_of(R(past), now=1_000_000.0) == 0.0


def test_resilience_config_rejects_nonsense_and_warns(caplog):
    """(minor) A typo'd timeout must not become the live timeout."""
    from bot.exchange.resilience import ResilienceConfig, load_resilience_config
    defaults = ResilienceConfig()
    with caplog.at_level("WARNING"):
        cfg = load_resilience_config({
            "connect_timeout_sec": -5, "read_timeout_sec": 0,
            "retry_max_tries": 0, "retry_budget_sec": "soon",
            "health_poll_sec": float("nan"),
            "degraded_latency_ms": 5000, "critical_latency_ms": 3000,
        })
    assert cfg.connect_timeout_sec == defaults.connect_timeout_sec
    assert cfg.read_timeout_sec == defaults.read_timeout_sec
    assert cfg.retry_max_tries == defaults.retry_max_tries
    assert cfg.retry_budget_sec == defaults.retry_budget_sec
    assert cfg.health_poll_sec == defaults.health_poll_sec
    # An inverted pair makes DEGRADED unreachable: both go back to defaults.
    assert cfg.degraded_latency_ms == defaults.degraded_latency_ms
    assert cfg.critical_latency_ms == defaults.critical_latency_ms
    assert "resilience config" in caplog.text


def test_resilience_config_keeps_good_values_and_defaults_a_missing_block():
    from bot.exchange.resilience import ResilienceConfig, load_resilience_config
    assert load_resilience_config(None) == ResilienceConfig()
    cfg = load_resilience_config({"read_timeout_sec": 12.5, "retry_max_tries": 5})
    assert cfg.read_timeout_sec == 12.5 and cfg.retry_max_tries == 5


def test_client_refuses_a_session_with_transport_retries():
    """(minor) urllib3's own adapter retries would repeat a POST inside ONE
    session.request call, underneath the whole taxonomy."""
    import requests.adapters
    session = requests.Session()
    session.mount("https://", requests.adapters.HTTPAdapter(max_retries=3))
    with pytest.raises(ValueError, match="max_retries"):
        BitflyerClient(Secret("k"), Secret("s"), session=session)
    # The default session is pinned to zero.
    client = BitflyerClient(Secret("k"), Secret("s"))
    for adapter in client._session.adapters.values():
        assert adapter.max_retries.total == 0


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
class VirtualClock:
    """A clock that moves ONLY when something waits or works.

    The reconciler's poll schedule is expressed in seconds of budget, so a test
    clock that ticks once per read (the previous harness) silently rewrote the
    schedule and hid the fact that polling stopped a third of the way into the
    budget. Here `sleep` and a venue's own latency are the only things that
    advance time, exactly as in production.
    """

    def __init__(self, start: float = 0.0):
        self.t = start

    def __call__(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += max(0.0, seconds)


class FakeExchange:
    """Query-only stand-in for getchildorders.

    `order_scripts` is a call-indexed script (the last entry repeats), so a test
    can make the venue answer 'nothing here' on the first poll and reveal the
    order on the next. An Exception entry is a failed poll.
    """

    def __init__(self, order_scripts=None):
        self._orders = order_scripts if order_scripts is not None else [[]]
        self.order_queries = 0

    def child_orders(self, symbol):
        i = min(self.order_queries, len(self._orders) - 1)
        self.order_queries += 1
        result = self._orders[i]
        if isinstance(result, Exception):
            raise result
        return result


class LaggyVenue:
    """getchildorders that only starts listing an order `lag_sec` after the
    send — the documented eventual consistency this whole module exists for."""

    def __init__(self, clock, order=None, lag_sec=0.0, existing=(),
                 latency_sec=0.0):
        self._clock = clock
        self.order = order
        self.lag_sec = lag_sec
        self.existing = list(existing)
        self.latency_sec = latency_sec
        self.order_queries = 0
        self.query_times: list[float] = []

    def child_orders(self, symbol):
        self.order_queries += 1
        if self.latency_sec:
            self._clock.sleep(self.latency_sec)
        self.query_times.append(self._clock())
        rows = list(self.existing)
        if self.order is not None and self._clock() >= self.lag_sec:
            rows.insert(0, self.order)      # getchildorders answers newest first
        return rows


def child_order(acc="ACC-NEW", side="BUY", size=0.01, state="ACTIVE",
                executed=0.0, price=None, avg=None, date="2026-08-21T00:00:00"):
    row = {"child_order_acceptance_id": acc, "side": side, "size": size,
           "child_order_state": state, "executed_size": executed,
           "child_order_date": date}
    if price is not None:
        row["price"] = price
    if avg is not None:
        row["average_price"] = avg
    return row


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


def build_manager(tmp_path, gateway, exchange, clock=None, **kw):
    clock = clock or VirtualClock()
    store = OrderStore(tmp_path / "orders.sqlite3")
    ks = KillSwitch(state_dir=tmp_path, manual_file=tmp_path / "KILL")
    reconciler = AutoReconciler(exchange, sleep=clock.sleep, clock=clock, **kw)
    notifier = RecordingNotifier()
    return OrderManager(store, gateway, ks, reconciler=reconciler,
                        notifier=notifier), store, ks, notifier


class _StepClock:
    """Monotonic clock that advances 1s per read (condition-monitor tests)."""

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
    placed = [child_order(state="COMPLETED", executed=0.01, avg=11_000_000)]
    exchange = FakeExchange(order_scripts=[[], placed])
    gateway = AmbiguousGateway(fail_times=1)
    manager, store, ks, notifier = build_manager(tmp_path, gateway, exchange)

    order = manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)

    assert order.state is OrderState.FILLED
    assert order.acceptance_id == "ACC-NEW"
    assert order.filled_size == 0.01
    # The fill price comes from the exchange's record, never from the quote the
    # decision was made on.
    assert order.avg_fill_price == 11_000_000
    assert gateway.sends == 1                 # ZERO resends
    assert not ks.is_tripped                  # resolved -> normal operation
    assert store.unknown_orders() == []
    assert notifier.sent == []


@pytest.mark.parametrize("lag_sec,state,expected", [
    (2.0, "ACTIVE", OrderState.SUBMITTED),
    (14.0, "COMPLETED", OrderState.FILLED),
])
def test_listing_lag_inside_the_budget_still_resolves(tmp_path, lag_sec, state,
                                                      expected):
    """getchildorders can lag a fresh acceptance. Anywhere inside the 15s
    budget must still be caught — the old schedule stopped polling at ~7s and
    called a live order 'not placed'."""
    clock = VirtualClock()
    venue = LaggyVenue(clock, order=child_order(state=state, executed=(
        0.01 if state == "COMPLETED" else 0.0), avg=11_000_000), lag_sec=lag_sec)
    gateway = AmbiguousGateway(fail_times=1)
    manager, store, ks, notifier = build_manager(tmp_path, gateway, venue,
                                                 clock=clock, budget_sec=15.0)

    order = manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)

    assert order.state is expected
    assert order.acceptance_id == "ACC-NEW"
    assert gateway.sends == 1
    assert not ks.is_tripped
    assert notifier.sent == []
    assert clock() <= 15.0 + 1e-9              # never overruns the budget


def test_poll_schedule_spans_the_whole_budget(tmp_path):
    clock = VirtualClock()
    venue = LaggyVenue(clock)                  # nothing is ever listed
    reconciler = AutoReconciler(venue, budget_sec=15.0, sleep=clock.sleep,
                                clock=clock)
    res = reconciler.resolve(symbol="FX_BTC_JPY", side="BUY", size=0.01,
                             snapshot=reconciler.baseline())
    assert res.state == "UNRESOLVED"
    assert venue.query_times == [0.5, 1.0, 2.0, 4.0, 8.0, 15.0]


def test_failed_poll_is_not_evidence(tmp_path):
    """A getchildorders that itself fails is a missing sample, never evidence."""
    boom = NetworkError("getchildorders timed out")
    placed = [child_order()]
    exchange = FakeExchange(order_scripts=[boom, boom, placed])
    gateway = AmbiguousGateway(fail_times=1)
    manager, store, ks, _ = build_manager(tmp_path, gateway, exchange)
    order = manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)
    assert order.state is OrderState.SUBMITTED    # ACTIVE on the exchange
    assert gateway.sends == 1


# ---------------------- (c) no positive evidence -> STATE_UNKNOWN, never closed --
def test_order_never_listed_stays_unknown_and_trips_the_kill_switch(tmp_path):
    """(c) THE ghost-order case. The venue never lists the order inside the
    budget. Absence of evidence must NOT close the record: silently marking it
    REJECTED is how the bot ends up flat in its own book while the exchange
    holds a live position."""
    clock = VirtualClock()
    venue = LaggyVenue(clock)                  # nothing, ever
    gateway = AmbiguousGateway(fail_times=1)
    manager, store, ks, notifier = build_manager(tmp_path, gateway, venue,
                                                 clock=clock, budget_sec=15.0)

    order = manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)

    assert order.state is OrderState.STATE_UNKNOWN     # NOT rejected
    assert store.unknown_orders()
    assert ks.is_tripped
    assert notifier.sent and notifier.sent[0][0] == "ORDER STATE UNKNOWN"
    assert notifier.sent[0][2] is True                 # urgent
    assert gateway.sends == 1                          # and never re-sent
    assert venue.order_queries == 6


def test_a_manual_order_during_the_window_is_not_our_fill(tmp_path):
    """(B3) Something else appears on the account while we are reconciling. It
    is a NEW id on our product and side, but not our size, so it is not
    evidence about our order: still UNKNOWN, and its price is never booked."""
    clock = VirtualClock()
    venue = LaggyVenue(clock, order=child_order(acc="ACC-MANUAL", size=0.05,
                                                state="COMPLETED", executed=0.05,
                                                avg=9_000_000), lag_sec=1.0)
    gateway = AmbiguousGateway(fail_times=1)
    manager, store, ks, notifier = build_manager(tmp_path, gateway, venue,
                                                 clock=clock, budget_sec=15.0)

    order = manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)

    assert order.state is OrderState.STATE_UNKNOWN
    assert order.acceptance_id is None
    assert order.avg_fill_price is None
    assert ks.is_tripped
    assert gateway.sends == 1


def test_limit_order_needs_a_price_match_too(tmp_path):
    """A LIMIT order at a different price is a different order."""
    clock = VirtualClock()
    venue = LaggyVenue(clock, order=child_order(price=10_000_000), lag_sec=0.0)
    reconciler = AutoReconciler(venue, budget_sec=15.0, sleep=clock.sleep,
                                clock=clock)
    base = reconciler.baseline()
    assert reconciler.resolve(symbol="FX_BTC_JPY", side="BUY", size=0.01,
                              snapshot=base, order_type="LIMIT",
                              price=9_500_000).state == "UNRESOLVED"
    clock.t = 0.0
    assert reconciler.resolve(symbol="FX_BTC_JPY", side="BUY", size=0.01,
                              snapshot=base, order_type="LIMIT",
                              price=10_000_000).state == "ACTIVE"


def test_the_newest_matching_order_wins(tmp_path):
    """(minor) getchildorders answers NEWEST FIRST. The old code kept the LAST
    matching row while its comment claimed newest-first — it took the oldest."""
    clock = VirtualClock()

    class Venue:
        def child_orders(self, symbol):
            return [child_order(acc="ACC-NEWER", date="2026-08-21T10:00:01"),
                    child_order(acc="ACC-OLDER", date="2026-08-21T09:00:00")]

    reconciler = AutoReconciler(Venue(), budget_sec=2.0, sleep=clock.sleep,
                                clock=clock)
    res = reconciler.resolve(symbol="FX_BTC_JPY", side="BUY", size=0.01,
                             snapshot=reconciler.baseline())
    assert res.acceptance_id == "ACC-NEWER"


def test_another_product_is_never_our_order(tmp_path):
    clock = VirtualClock()
    row = child_order()
    row["product_code"] = "BTC_JPY"
    venue = LaggyVenue(clock, order=row)
    reconciler = AutoReconciler(venue, budget_sec=15.0, sleep=clock.sleep,
                                clock=clock)
    res = reconciler.resolve(symbol="FX_BTC_JPY", side="BUY", size=0.01,
                             snapshot=reconciler.baseline())
    assert res.state == "UNRESOLVED"


# ------------------------------- (d) budget exhaustion -> STATE_UNKNOWN kept --
def test_budget_exhaustion_keeps_state_unknown_and_alerts(tmp_path):
    """(d) Undecided at the budget end: the human path, exactly as before."""
    boom = NetworkError("exchange unreachable")
    exchange = FakeExchange(order_scripts=[boom])
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
    assert sorted(public) == ["child_orders"]
    for forbidden in ("send_child_order", "cancel_child_order", "submit_order",
                      "send", "cancel", "sendchildorder"):
        assert not hasattr(exchange, forbidden)


# --------------------------- (B4) the send path performs no diagnostic reads --
class SpyClient:
    """Records every client call in order, so a test can prove what ran BEFORE
    the order left."""

    def __init__(self, log):
        self.log = log

    def get_child_orders(self, symbol, *a, **kw):
        self.log.append(("GET", "/v1/me/getchildorders"))
        return []

    def get_positions(self, symbol, *a, **kw):
        self.log.append(("GET", "/v1/me/getpositions"))
        return []


class SpyGateway(ExecutionGateway):
    def __init__(self, log):
        self.log = log
        self.sends = 0

    def submit_order(self, *, symbol, side, size, order_type, price):
        self.sends += 1
        self.log.append(("SEND", side, size))
        return SubmitResult(acceptance_id=f"ACC-{self.sends}")

    def cancel_order(self, *, symbol, acceptance_id):
        pass

    def fetch_order_status(self, *, symbol, acceptance_id):
        return None


def test_submit_performs_no_reads_before_the_order(tmp_path):
    """(B4) The pre-send snapshot used to cost two blocking GETs before EVERY
    send — including the protective close, on the venue this module exists
    because it degrades. The baseline is now local state."""
    log = []
    store = OrderStore(tmp_path / "orders.sqlite3")
    ks = KillSwitch(state_dir=tmp_path, manual_file=tmp_path / "KILL")
    gateway = SpyGateway(log)
    reconciler = AutoReconciler(QueryOnlyExchange(SpyClient(log)),
                                sleep=lambda s: None)
    manager = OrderManager(store, gateway, ks, reconciler=reconciler,
                           notifier=RecordingNotifier())

    manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)
    assert log == [("SEND", "BUY", 0.01)]

    # ...and the protective close reaches the gateway with nothing in front.
    store.transition(store.active_orders("FX_BTC_JPY")[0].local_id,
                     OrderState.FILLED, filled_size=0.01)
    log.clear()
    manager.submit(symbol="FX_BTC_JPY", side="SELL", size=0.01)
    assert log == [("SEND", "SELL", 0.01)]


def test_baseline_carries_ids_forward_without_a_pre_send_get(tmp_path):
    """The reconciler refreshes its own baseline from the polls it has to make
    anyway, so nothing has to be fetched on the send path."""
    clock = VirtualClock()
    venue = LaggyVenue(clock, existing=[child_order(acc="ACC-OTHER", size=0.02)])
    reconciler = AutoReconciler(venue, budget_sec=1.0, sleep=clock.sleep,
                                clock=clock)
    reconciler.resolve(symbol="FX_BTC_JPY", side="BUY", size=0.01,
                       snapshot=reconciler.baseline())
    assert "ACC-OTHER" in reconciler.baseline().acceptance_ids
    assert "ACC-KNOWN" in reconciler.baseline(["ACC-KNOWN"]).acceptance_ids


def test_store_baseline_is_bounded(tmp_path):
    store = OrderStore(tmp_path / "orders.sqlite3")
    for i in range(12):
        o = store.create("FX_BTC_JPY", "BUY", 0.01, "MARKET", None)
        store.transition(o.local_id, OrderState.SUBMITTED, acceptance_id=f"ACC-{i}")
        store.transition(o.local_id, OrderState.FILLED, filled_size=0.01)
    open_order = store.create("FX_BTC_JPY", "BUY", 0.01, "MARKET", None)
    store.transition(open_order.local_id, OrderState.SUBMITTED,
                     acceptance_id="ACC-OPEN")
    ids = store.known_acceptance_ids(max_terminal=5)
    assert "ACC-OPEN" in ids                   # non-terminal always kept
    assert len(ids) == 6                       # + the 5 most recent closed ones


# ---------------------------- (e) duplicate-order impossibility (property) ---
class FaultyOrderSession:
    """Randomized transport for /v1/me/sendchildorder.

    The fault pool and the DELIVERED flag are deliberately DECOUPLED. The
    previous version drew the fault from a "pre-send" pool exactly when it had
    decided the request was not delivered, which made the test assume the very
    thing it claimed to check: any fault the taxonomy mislabels as pre-send was
    unreachable by construction.

    Here the harness models physics instead. `never_delivered` is a property of
    the FAULT — a connect timeout, or a urllib3 new-connection error, means the
    connection for that attempt was never established, so no request byte can
    have been written. For every other fault the harness flips its own coin,
    independently of what the taxonomy thinks. `placed` counts how many orders
    the venue would actually hold; it must never exceed the intended count.

    If this test fails, the taxonomy claimed "pre-send" for something that can
    be delivered. Fix the taxonomy — never the harness.
    """

    # (never_delivered, factory)
    FAULTS = (
        (True, lambda: requests.exceptions.ConnectTimeout("connect timed out")),
        (True, lambda: requests.exceptions.ConnectionError(
            "Failed to establish a new connection: [Errno 111] Connection refused")),
        (True, lambda: requests.exceptions.ConnectionError(
            "NewConnectionError: Name or service not known")),
        (False, lambda: requests.exceptions.ProxyError("Cannot connect to proxy.")),
        (False, lambda: requests.exceptions.SSLError(
            "[SSL: TLSV1_ALERT_INTERNAL_ERROR] tlsv1 alert internal error")),
        (False, lambda: requests.exceptions.SSLError(
            "[SSL: SSLV3_ALERT_BAD_RECORD_MAC] sslv3 alert bad record mac")),
        (False, lambda: requests.exceptions.ReadTimeout("read timed out")),
        (False, lambda: requests.exceptions.ConnectionError("connection reset by peer")),
        (False, lambda: requests.exceptions.ChunkedEncodingError("truncated")),
        (False, lambda: FakeResponse(500, {"error_message": "internal"})),
        (False, lambda: FakeResponse(503, {"error_message": "unavailable"})),
        (False, lambda: FakeResponse(429, {"error_message": "over limit"})),
        (False, lambda: FakeResponse(400, {"error_message": "bad size"})),
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


@pytest.mark.parametrize("seed", [0, 7, 11, 777, 2026])
def test_property_sent_order_count_never_exceeds_intended(seed):
    """(e) Randomized fault sequences: the exchange never ends up holding more
    orders than the bot intended to place."""
    rng = random.Random(seed)
    for _ in range(1000):
        script = []
        for _ in range(rng.randint(1, 6)):
            never_delivered, factory = rng.choice(FaultyOrderSession.FAULTS)
            delivered = False if never_delivered else rng.random() < 0.5
            script.append((delivered, factory))
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
        clock = VirtualClock()
        venue = LaggyVenue(clock, order=(child_order(
            state="COMPLETED", executed=0.01, avg=1.0) if landed else None),
            lag_sec=rng.choice([0.0, 2.0, 14.0]))
        gateway = AmbiguousGateway(fail_times=1)
        manager = OrderManager(
            store, gateway, ks,
            reconciler=AutoReconciler(venue, budget_sec=15.0,
                                      sleep=clock.sleep, clock=clock),
            notifier=RecordingNotifier())
        manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)
        assert gateway.sends == 1


# ------------------------- (f) closing allowed under CRITICAL, entry barred --
class _App:
    """Just the state `_entry_allowed_under_condition` reads, so the gate can
    be exercised against a real ConditionMonitor without booting the app."""

    def __init__(self, condition, monitor, entry_gating):
        self.condition = condition
        self.condition_monitor = monitor
        self._degraded_entry_seq = 0
        self._entry_gating = entry_gating


def _make_app(condition, health=None, entry_gating=True):
    from bot.main import TradingApp
    monitor = ConditionMonitor()
    if health:
        monitor.observe_health(health)
    app = _App(condition, monitor, entry_gating)
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


# ------------------------- (M7b) entry gating is an OPT-IN behavior change ---
def test_entry_gating_is_off_by_default():
    """Throttling entries under DEGRADED/CRITICAL changes what the champion
    trades. Unregistered, it must not touch the running paper sample."""
    from bot.exchange.resilience import ResilienceConfig, load_resilience_config
    assert ResilienceConfig().entry_gating is False
    assert load_resilience_config({}).entry_gating is False
    assert load_resilience_config({"entry_gating": True}).entry_gating is True


@pytest.mark.parametrize("condition", [ExchangeCondition.DEGRADED,
                                       ExchangeCondition.CRITICAL])
def test_gating_off_leaves_entries_alone(condition):
    app = _make_app(condition, entry_gating=False)
    assert all(app._entry_allowed_under_condition() for _ in range(6))


def test_gating_off_still_honours_a_halted_exchange():
    """gethealth=STOP is not a strategy question: the venue is halted, so the
    order cannot succeed. That suppression is always on."""
    app = _make_app(ExchangeCondition.NORMAL, health="STOP", entry_gating=False)
    assert app._entry_allowed_under_condition() is False


def test_config_default_keeps_entry_gating_off():
    import yaml
    from pathlib import Path
    cfg = yaml.safe_load((Path(__file__).resolve().parents[1] / "config" /
                          "config.yaml").read_text(encoding="utf-8"))
    assert cfg["resilience"]["entry_gating"] is False


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


def _paper_app(tmp_path, monkeypatch, resilience_cfg=None, session=None,
               client=None, staleness_sec=3600):
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
        "market_data": {"max_staleness_sec": staleness_sec,
                        "max_price_jump_pct": 50, "max_spread_pct": 5.0},
    }
    if resilience_cfg is not None:
        config["resilience"] = resilience_cfg
    limits = RiskLimits.from_dict({
        "MAX_ORDER_SIZE_JPY": 130000, "MAX_POSITION_SIZE_JPY": 130000,
        "MAX_DAILY_LOSS_JPY": 6000, "MAX_DRAWDOWN_PCT": 10.0,
        "MAX_OPEN_ORDERS": 1, "MAX_CONSECUTIVE_LOSSES": 5,
        "MAX_API_ERRORS_IN_ROW": 5,
    })
    settings = Settings(mode=Mode.PAPER, product_code="FX_BTC_JPY",
                        config=config, risk_limits=limits)
    if client is None:
        session = session or FakeSession()
        session.set("GET", "/v1/ticker", FakeResponse(200, {
            "ltp": 10_000_000, "best_bid": 9_999_000, "best_ask": 10_001_000}))
        client = BitflyerClient(session=session, sleep=lambda s: None)
    return TradingApp(settings, client, NullNotifier())


def test_app_reacts_to_a_busy_gethealth(tmp_path, monkeypatch):
    """End-to-end on the paper app: /v1/gethealth says VERY BUSY -> the app
    goes DEGRADED, the READ timeout doubles, the connect timeout does not, and
    telemetry lands in data/api_health.csv."""
    app = _paper_app(tmp_path, monkeypatch, {"entry_gating": True})
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


# ------------------- (M4) degradation must not SPURIOUSLY trip the switch ---
def test_a_slow_venue_does_not_trip_the_api_error_kill(tmp_path, monkeypatch):
    """(M4a) A tripped kill switch is a FULL freeze, exits included. So a venue
    that is merely slow — read timeouts on the public ticker, every one of them
    SAFE_RETRY — must not be what trips it."""
    session = FakeSession()
    app = _paper_app(tmp_path, monkeypatch, session=session)
    from bot.market_data.feed import Tick
    tick = Tick(timestamp=1.0, price=10_000_000, best_bid=9_999_000,
                best_ask=10_001_000)
    app.feed.last_tick = tick
    app._try_order("BUY", tick)
    assert app.portfolio.position_size > 0

    session.set("GET", "/v1/ticker", requests.exceptions.ReadTimeout("read timed out"))
    for _ in range(20):
        app.step()
    assert app._api_errors_in_row == 0
    assert not app.kill_switch.is_tripped
    assert app.status.status.error_count == 20      # still counted as errors


def test_a_definite_error_still_trips_the_api_error_kill(tmp_path, monkeypatch):
    """The counter keeps its job: a definite 4xx is not degradation."""
    session = FakeSession()
    app = _paper_app(tmp_path, monkeypatch, session=session)
    session.set("GET", "/v1/ticker", FakeResponse(400, {"error_message": "nope"}))
    for _ in range(6):
        app.step()
    assert app.kill_switch.is_tripped
    assert app.kill_switch.state["reason"] == "api_errors"


def test_public_failures_are_ignored_while_degraded(tmp_path, monkeypatch):
    """(M4a) While the venue is DEGRADED, a public-endpoint failure IS the
    degradation — already handled by the condition, the timeouts and the gate."""
    session = FakeSession()
    app = _paper_app(tmp_path, monkeypatch, session=session)
    app.condition_monitor.observe_health("BUSY")     # the venue says it is busy
    session.set("GET", "/v1/ticker", FakeResponse(400, {"error_message": "nope"}))
    for _ in range(10):
        app.step()
    assert app.condition is ExchangeCondition.DEGRADED
    assert app._api_errors_in_row == 0
    assert not app.kill_switch.is_tripped


def test_staleness_budget_scales_with_the_read_timeout(tmp_path, monkeypatch):
    """(M4b) At CRITICAL a single read may legitimately take 3x as long. A
    fixed 60s staleness threshold would trip the kill switch on our OWN widened
    timeout instead of on a real loss of data."""
    app = _paper_app(tmp_path, monkeypatch, staleness_sec=60)
    assert app.feed.max_staleness_sec == 60
    app._apply_staleness_budget(ExchangeCondition.DEGRADED)
    assert app.feed.max_staleness_sec == 120
    app._apply_staleness_budget(ExchangeCondition.CRITICAL)
    assert app.feed.max_staleness_sec == 180
    # ...and the read timeout moved by exactly the same multiplier.
    assert app.client._base_timeouts.for_condition(
        ExchangeCondition.CRITICAL).read_sec == app._base_timeouts.read_sec * 3
    app._apply_staleness_budget(ExchangeCondition.NORMAL)
    assert app.feed.max_staleness_sec == 60          # restored exactly


def test_a_busy_gethealth_also_widens_the_staleness_budget(tmp_path, monkeypatch):
    app = _paper_app(tmp_path, monkeypatch, staleness_sec=60)
    app.client._session.set("GET", "/v1/gethealth",
                            FakeResponse(200, {"status": "SUPER BUSY"}))
    app._last_health_poll = 0.0
    app._refresh_condition()
    assert app.condition is ExchangeCondition.CRITICAL
    assert app.feed.max_staleness_sec == 180


def test_kill_alert_names_the_open_position_and_the_manual_exit(tmp_path, monkeypatch):
    """(M4c) The contract is honest but harsh: a tripped switch blocks EVERY
    order, exits included. The operator has to be told, with the position."""
    app = _paper_app(tmp_path, monkeypatch)
    from bot.market_data.feed import Tick
    tick = Tick(timestamp=1.0, price=10_000_000, best_bid=9_999_000,
                best_ask=10_001_000)
    app.feed.last_tick = tick
    app._try_order("BUY", tick)
    size = app.portfolio.position_size
    assert size > 0

    message = app._kill_message("market data stale")
    assert "market data stale" in message
    assert "OPEN POSITION" in message and "LONG" in message
    assert str(size) in message
    assert "will NOT close it" in message
    assert "reset" in message

    app.portfolio.position_size = 0.0
    assert app._kill_message("whatever") == "whatever"


# ------------- (M5/M6) diagnostics never inherit the widened trading timeouts --
class TimeoutRecordingSession(FakeSession):
    """FakeSession that remembers the (connect, read) pair each call was given,
    and can burn the read half off a virtual clock."""

    def __init__(self, clock=None):
        super().__init__()
        self.timeouts: list[tuple[str, tuple]] = []
        self._clock = clock

    def request(self, method, url, params=None, data=None, headers=None, timeout=None):
        path = url.split("bitflyer.com")[-1]
        self.timeouts.append((path, timeout))
        if self._clock is not None and timeout:
            self._clock.sleep(timeout[1])
        return super().request(method, url, params=params, data=data,
                               headers=headers, timeout=timeout)

    def read_timeout_for(self, path):
        return next(t[1][1] for t in self.timeouts if t[0] == path)


def test_the_health_poll_keeps_its_own_short_timeout(tmp_path, monkeypatch):
    """(M5) At CRITICAL the trading read timeout is 30s. The health poll sits
    on the trading loop's hot path — it must not inherit it."""
    clock = VirtualClock()
    session = TimeoutRecordingSession(clock)
    session.set("GET", "/v1/gethealth",
                requests.exceptions.ReadTimeout("read timed out"))
    app = _paper_app(tmp_path, monkeypatch, session=session)
    app.client.apply_condition(ExchangeCondition.CRITICAL)
    assert app.client.timeouts.as_tuple() == (3.0, 30.0)

    app._last_health_poll = -1e9
    before = clock()
    app._refresh_condition()
    assert session.read_timeout_for("/v1/gethealth") == 5.0
    assert clock() - before <= 5.0                 # one attempt, 5s ceiling
    assert app.client.timeouts.as_tuple() == (3.0, 30.0)   # restored


def test_a_failed_health_poll_is_skipped_silently(tmp_path, monkeypatch):
    session = FakeSession()
    session.set("GET", "/v1/gethealth", requests.exceptions.ReadTimeout("slow"))
    app = _paper_app(tmp_path, monkeypatch, session=session)
    app._last_health_poll = -1e9
    app._refresh_condition()                        # must not raise
    assert app.condition is ExchangeCondition.NORMAL


def test_reconciliation_polls_use_the_diagnostic_timeout(tmp_path, monkeypatch):
    """(M6) The same rule for the reconciler: it is triggered BY a widened
    timeout, so inheriting it would let one poll eat the whole budget."""
    session = TimeoutRecordingSession()
    session.set("GET", "/v1/me/getchildorders", FakeResponse(200, []))
    client = BitflyerClient(Secret("k"), Secret("s"), session=session,
                            sleep=lambda s: None)
    client.apply_condition(ExchangeCondition.CRITICAL)
    exchange = QueryOnlyExchange(client)
    exchange.child_orders("FX_BTC_JPY")
    assert session.read_timeout_for("/v1/me/getchildorders") == 5.0
    assert client.timeouts.as_tuple() == (3.0, 30.0)      # restored afterwards


def test_a_reconciliation_poll_is_never_retried(tmp_path):
    """One attempt per poll: the reconciler runs its own schedule, so a
    per-call retry would just spend its budget twice."""
    session = TimeoutRecordingSession()
    session.set("GET", "/v1/me/getchildorders",
                requests.exceptions.ReadTimeout("slow"))
    client = BitflyerClient(Secret("k"), Secret("s"), session=session,
                            sleep=lambda s: None)
    exchange = QueryOnlyExchange(client)
    with pytest.raises(NetworkError):
        exchange.child_orders("FX_BTC_JPY")
    assert len(session.calls) == 1
    # ...and the client's normal retry budget is intact afterwards.
    session.set("GET", "/v1/ticker", requests.exceptions.ReadTimeout("slow"))
    with pytest.raises(NetworkError):
        client.ticker("FX_BTC_JPY")
    assert len([c for c in session.calls if c["path"] == "/v1/ticker"]) == 3


def test_reconciler_wall_clock_stays_inside_budget_plus_one_read(tmp_path):
    """(M6) Every poll can burn a full diagnostic read timeout. The whole
    reconciliation must still land inside budget + one read."""
    clock = VirtualClock()

    class SlowVenue:
        order_queries = 0

        def child_orders(self, symbol):
            SlowVenue.order_queries += 1
            clock.sleep(5.0)                        # the read timeout
            raise NetworkError("read timed out")

    reconciler = AutoReconciler(SlowVenue(), budget_sec=15.0,
                                sleep=clock.sleep, clock=clock)
    res = reconciler.resolve(symbol="FX_BTC_JPY", side="BUY", size=0.01,
                             snapshot=reconciler.baseline())
    assert res.state == "UNRESOLVED"
    assert clock() <= 15.0 + 5.0


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


def test_alternating_health_de_escalates_instead_of_deadlocking():
    """(M2) With PRODUCTION defaults, /v1/gethealth flapping BUSY <-> NORMAL
    used to hold a monitor that had once seen SUPER BUSY at CRITICAL forever:
    the streak wanted `recovery_samples` of the SAME calmer level and the
    alternation never produced one. Entries stayed suppressed and the read
    timeout stayed x3 for as long as the flapping lasted.

    Now any sample calmer than CURRENT counts, and the target is the WORST of
    them — so the alternation recovers to DEGRADED (which is what BUSY means,
    honestly) and only a venue that actually settles reaches NORMAL.
    """
    clock = _StepClock(step=0.0)
    monitor = ConditionMonitor(clock=clock)          # all production defaults
    monitor.observe_health("SUPER BUSY")
    assert monitor.condition is ExchangeCondition.CRITICAL

    for i in range(1, 11):                            # 5 minutes of 30s polls
        clock.t = i * 30.0
        monitor.observe_health("BUSY" if i % 2 else "NORMAL")
    assert monitor.condition is ExchangeCondition.DEGRADED

    for i in range(11, 20):                           # the venue settles
        clock.t = i * 30.0
        monitor.observe_health("NORMAL")
    assert monitor.condition is ExchangeCondition.NORMAL


def test_a_stale_health_reading_drops_out_of_the_vote():
    """(M3) A health string that stopped being refreshed is not evidence."""
    clock = _StepClock(step=0.0)
    monitor = ConditionMonitor(clock=clock, health_ttl_sec=90.0)
    monitor.observe_health("SUPER BUSY")
    assert monitor.condition is ExchangeCondition.CRITICAL
    assert monitor.health == "SUPER BUSY"

    clock.t = 1000.0                                  # the poll never came back
    monitor.observe(20.0)
    assert monitor.health is None                     # surfaced as unknown...
    assert monitor.health_age_sec == pytest.approx(1000.0)
    assert monitor.snapshot()["health"] is None
    assert monitor.snapshot()["health_age_sec"] == pytest.approx(1000.0)
    for _ in range(5):                                # ...and out of the vote
        monitor.observe(20.0)
    assert monitor.condition is ExchangeCondition.NORMAL


def test_a_stale_stop_reading_no_longer_halts_entries():
    clock = _StepClock(step=0.0)
    monitor = ConditionMonitor(clock=clock, health_ttl_sec=90.0)
    monitor.observe_health("STOP")
    assert monitor.exchange_stopped
    clock.t = 91.0
    assert not monitor.exchange_stopped


def test_health_ttl_is_three_polls():
    from bot.exchange.resilience import load_resilience_config
    assert load_resilience_config({"health_poll_sec": 30}).health_ttl_sec == 90.0


def test_status_carries_the_health_age(tmp_path, monkeypatch):
    app = _paper_app(tmp_path, monkeypatch)
    app.condition_monitor.observe_health("BUSY")
    app._update_status(10_000_000)
    assert app.status.status.api_health_status == "BUSY"
    assert app.status.status.api_health_age_sec is not None


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


def test_aggregate_ignores_a_stale_status_json(tmp_path):
    """(minor) A crashed bot leaves its last status on disk forever. Reporting
    that "NORMAL" as the venue's current level is worse than reporting nothing:
    the CSV's last row is what actually happened, and the payload says stale."""
    import json

    from bot.monitoring.aggregate import collect_status
    now = 1_000_000.0
    (tmp_path / "data").mkdir()
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "status.json").write_text(json.dumps({
        "mode": "paper", "updated_at": now - 3600,       # an hour old
        "api_condition": "NORMAL", "api_health_status": "NORMAL"}),
        encoding="utf-8")
    lines = [ApiHealthRecorder.HEADER.rstrip("\n")]
    lines.append(f"{now - 30},public,/v1/ticker,2000.0,safe_retry,CRITICAL,SUPER BUSY")
    (tmp_path / "data" / "api_health.csv").write_text("\n".join(lines) + "\n",
                                                      encoding="utf-8")
    api = collect_status(tmp_path, now=now)["api_health"]
    assert api["condition"] == "CRITICAL"        # from the CSV, not the corpse
    assert api["health"] == "SUPER BUSY"
    assert api["stale"] is True


def test_aggregate_trusts_a_fresh_status_json(tmp_path):
    import json

    from bot.monitoring.aggregate import collect_status
    now = 1_000_000.0
    (tmp_path / "data").mkdir()
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "status.json").write_text(json.dumps({
        "mode": "paper", "updated_at": now - 5,
        "api_condition": "DEGRADED", "api_health_status": None,
        "api_health_age_sec": 240.0}), encoding="utf-8")
    (tmp_path / "data" / "api_health.csv").write_text(
        ApiHealthRecorder.HEADER +
        f"{now - 10},public,/v1/ticker,40.0,ok,NORMAL,NORMAL\n", encoding="utf-8")
    api = collect_status(tmp_path, now=now)["api_health"]
    assert api["condition"] == "DEGRADED"
    assert api["stale"] is False
    assert api["health_age_sec"] == 240.0


def test_dashboard_page_has_the_api_tile():
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / "scripts" / "dashboard.py"
    text = src.read_text(encoding="utf-8")
    assert "function apiTile(" in text
    assert "apiTile(d.api_health)" in text
    assert "API状態" in text
    # An expired health reading and a stale status.json must both be visible as
    # such, not silently rendered as a current "NORMAL".
    assert "health_age_sec" in text
    assert "a.stale" in text


# ------------------------------------------------------------- resolution ---
def test_resolution_states_are_positive_evidence_only():
    from bot.order_management.manager import _RESOLUTION_TO_LOCAL
    # There is no "the exchange did not list it" outcome, in either module.
    assert "NOT_PLACED" not in _RESOLUTION_TO_LOCAL
    assert _RESOLUTION_TO_LOCAL["FILLED"] is OrderState.FILLED
    assert _RESOLUTION_TO_LOCAL["ACTIVE"] is OrderState.SUBMITTED
    assert Resolution("UNRESOLVED").resolved is False
    assert Resolution("FILLED").resolved is True


def test_orders_that_already_existed_are_never_mistaken_for_ours(tmp_path):
    """An order that predates the send stays in the baseline and is ignored."""
    clock = VirtualClock()
    old = child_order(acc="OLD")
    venue = LaggyVenue(clock, existing=[old])
    reconciler = AutoReconciler(venue, budget_sec=2.0, sleep=clock.sleep,
                                clock=clock)
    snap = reconciler.baseline(["OLD"])
    assert snap.acceptance_ids == frozenset({"OLD"})
    res = reconciler.resolve(symbol="FX_BTC_JPY", side="BUY", size=0.01,
                             snapshot=snap)
    assert res.state == "UNRESOLVED"


def test_a_broken_baseline_disables_auto_reconciliation_but_not_trading(tmp_path):
    class BrokenStore(OrderStore):
        def known_acceptance_ids(self, max_terminal=200):
            raise sqlite3.OperationalError("database is locked")

    gateway = AmbiguousGateway(fail_times=0)
    store = BrokenStore(tmp_path / "orders.sqlite3")
    ks = KillSwitch(state_dir=tmp_path, manual_file=tmp_path / "KILL")
    manager = OrderManager(store, gateway, ks,
                           reconciler=AutoReconciler(FakeExchange(),
                                                     sleep=lambda s: None),
                           notifier=RecordingNotifier())
    order = manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)
    assert order.state is OrderState.SUBMITTED     # the send still happened
    assert gateway.sends == 1


def test_baseline_unions_locally_known_acceptance_ids(tmp_path):
    """An acceptance id already in our own book can never be read as the order
    we are about to send, even when the venue lists it during the window."""
    store = OrderStore(tmp_path / "orders.sqlite3")
    old = store.create("FX_BTC_JPY", "BUY", 0.01, "MARKET", None)
    store.transition(old.local_id, OrderState.SUBMITTED, acceptance_id="ACC-OLD")
    store.transition(old.local_id, OrderState.FILLED, filled_size=0.01)
    clock = VirtualClock()
    venue = LaggyVenue(clock, existing=[child_order(acc="ACC-OLD",
                                                    state="COMPLETED",
                                                    executed=0.01, avg=1.0)])
    ks = KillSwitch(state_dir=tmp_path, manual_file=tmp_path / "KILL")
    manager = OrderManager(
        store, AmbiguousGateway(fail_times=1), ks,
        reconciler=AutoReconciler(venue, budget_sec=2.0, sleep=clock.sleep,
                                  clock=clock),
        notifier=RecordingNotifier())
    order = manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)
    assert order.state is OrderState.STATE_UNKNOWN   # not "our fill"
    assert order.acceptance_id is None


def test_snapshot_type_is_frozen():
    snap = ExchangeSnapshot(frozenset({"A"}), 0.0)
    with pytest.raises(Exception):
        snap.acceptance_ids = frozenset()

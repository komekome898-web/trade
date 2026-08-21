"""Execution resilience: fault injection against a mocked transport.

The bar these tests hold is the owner's 2019 failure mode — bitFlyer degrades
exactly during the move, orders delay or fail, and the position cannot be
exited — plus its mirror image, a duplicated real order. Every test here is
one of those two.

Nothing in this file touches the network.
"""
from __future__ import annotations

import inspect
import logging
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
from bot.execution.gateway import ExecutionGateway, OrderStatus, SubmitResult
from bot.order_management.manager import OrderManager
from bot.order_management.order import DuplicateOrderError, OrderState, OrderStore
from bot.order_management.reconciler import (
    AutoReconciler, ExchangeSnapshot, QueryOnlyExchange, Resolution,
)
from bot.risk.kill_switch import KillReason, KillSwitch
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


def _bad_order_bodies():
    """2xx answers that are NOT the acceptance /v1/me/sendchildorder promises.

    Every one of them has been seen from an edge in front of an exchange: a
    maintenance page, a body cut off mid-flight, an object without the id, a
    bare 202 with nothing in it. None of them proves the order was refused.
    """
    return [
        ("html_page", lambda: FakeResponse(200, None,
                                           text="<html>maintenance</html>")),
        ("empty_body", lambda: FakeResponse(200, None, text="")),
        ("truncated_json", lambda: FakeResponse(200, None,
                                                text='{"child_order_acce')),
        ("no_acceptance_id", lambda: FakeResponse(200, {"status": "ok"})),
        ("json_array", lambda: FakeResponse(200, [])),
        ("accepted_202_empty", lambda: FakeResponse(202, None, text="")),
    ]


_INVARIANT_INJECTIONS = (
    [("transport", n, t) for n, t in _requests_exception_types()]
    + [("parse", n, f) for n, f in _bad_order_bodies()]
)


@pytest.mark.parametrize("phase,name,injection", _INVARIANT_INJECTIONS,
                         ids=[f"{p}:{n}" for p, n, _ in _INVARIANT_INJECTIONS])
def test_order_endpoint_makes_exactly_one_attempt_for_every_failure(
        phase, name, injection, fake_session):
    """THE hard invariant, over BOTH phases a send can fail in.

    - transport: the whole `requests.exceptions` surface. Every failure gets
      exactly ONE attempt, except the two provable pre-send classes (a connect
      timeout, and a connection error whose text names the new-connection
      failure) — those are sanctioned and tested separately below. A plain
      one-argument message carries no such marker, so ConnectTimeout is the
      only transport row that may repeat.
    - response parse: a 2xx whose body is not the acceptance the endpoint
      promised. The venue may well be holding the order behind that body, so it
      is AMBIGUOUS -> OrderStateUnknown, one attempt, and never a ValueError
      escaping into the manager's REJECTED branch.
    """
    if phase == "transport":
        fake_session.set("POST", ORDER_PATH, injection("x"))
        expected = 3 if injection is requests.exceptions.ConnectTimeout else 1
    else:
        fake_session.set("POST", ORDER_PATH, injection())
        expected = 1
    client = BitflyerClient(Secret("k"), Secret("s"), session=fake_session,
                            sleep=lambda s: None)
    raised = None
    try:
        client.send_child_order(product_code="FX_BTC_JPY", side="BUY", size=0.01)
    except BaseException as e:      # noqa: BLE001 - the invariant is the count
        raised = e
    assert len(fake_session.order_calls()) == expected, name
    if phase == "parse":
        assert isinstance(raised, OrderStateUnknown), name


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


# --------------------------------- (B1) the response BODY is classified too --
def test_body_shape_is_only_promised_by_the_acceptance_endpoints():
    ok = {"child_order_acceptance_id": "ACC-1"}
    assert resilience.body_shape_problem(ORDER_PATH, ok, '{"x":1}') is None
    assert resilience.body_shape_problem(ORDER_PATH, {}, "{}") == "missing_acceptance_id"
    assert resilience.body_shape_problem(ORDER_PATH, None, "") == "empty_body"
    assert resilience.body_shape_problem(ORDER_PATH, [], "[]") == "unexpected_body"
    # A cancel answers 200 with an EMPTY body by design, so it promises nothing.
    assert resilience.body_shape_problem("/v1/me/cancelchildorder", None, "") is None
    assert resilience.body_shape_problem("/v1/ticker", None, "") is None
    # ...and the classification itself is the usual split.
    assert resilience.classify_body("empty_body",
                                    EndpointClass.ORDER).failure_class \
        is FailureClass.AMBIGUOUS
    safe = resilience.classify_body("unparseable_body", EndpointClass.PUBLIC)
    assert safe.failure_class is FailureClass.SAFE_RETRY
    assert resilience.may_retry(safe, EndpointClass.PUBLIC)


def _live_stack(tmp_path, session, clock=None, budget_sec=15.0):
    """Order manager wired to the REAL client through LiveExecutor.

    Everything below the manager is production code, so a test can inject an
    HTTP response and watch what the order book actually does with it — which
    is where a bad-body 200 used to turn into a REJECTED record.
    """
    from bot.execution.live import LiveExecutor
    from bot.settings import Mode, RiskLimits, Settings

    clock = clock or VirtualClock()
    settings = Settings(mode=Mode.LIVE, product_code="FX_BTC_JPY", config={},
                        risk_limits=RiskLimits.from_dict({
                            "MAX_ORDER_SIZE_JPY": 130000,
                            "MAX_POSITION_SIZE_JPY": 130000,
                            "MAX_DAILY_LOSS_JPY": 6000, "MAX_DRAWDOWN_PCT": 10.0,
                            "MAX_OPEN_ORDERS": 1, "MAX_CONSECUTIVE_LOSSES": 5,
                            "MAX_API_ERRORS_IN_ROW": 5}))
    client = BitflyerClient(Secret("k"), Secret("s"), session=session,
                            sleep=lambda s: None)
    store = OrderStore(tmp_path / "orders.sqlite3")
    ks = KillSwitch(state_dir=tmp_path, manual_file=tmp_path / "KILL")
    notifier = RecordingNotifier()
    manager = OrderManager(
        store, LiveExecutor(settings, client), ks,
        reconciler=AutoReconciler(QueryOnlyExchange(client),
                                  budget_sec=budget_sec, sleep=clock.sleep,
                                  clock=clock),
        notifier=notifier)
    return manager, store, ks, notifier


@pytest.mark.parametrize("name,body", [
    ("html_page", FakeResponse(200, None, text="<html>maintenance</html>")),
    ("empty_body", FakeResponse(200, None, text="")),
])
def test_a_200_that_is_not_an_acceptance_is_unknown_not_rejected(tmp_path, name,
                                                                 body):
    """(B1) The duplicate-order path at the response parse.

    A 200 carrying a maintenance page raised a bare ValueError out of
    `resp.json()`, straight past the taxonomy and into the manager's
    `except (BitflyerError, ValueError)` branch — which closes the record
    REJECTED. The venue may be holding that order, and the next signal, seeing
    a book with nothing open, sends a SECOND real one.
    """
    session = FakeSession()
    session.set("POST", ORDER_PATH, body)
    session.set("GET", "/v1/me/getchildorders", FakeResponse(200, []))
    manager, store, ks, notifier = _live_stack(tmp_path, session)

    order = manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)

    assert order.state is OrderState.STATE_UNKNOWN          # NOT rejected
    assert len(session.order_calls()) == 1                  # ONE body sent
    polls = [c for c in session.calls if "getchildorders" in c["path"]]
    assert len(polls) == 6                                  # reconciler engaged
    assert ks.is_tripped
    assert notifier.sent and notifier.sent[0][0] == "ORDER STATE UNKNOWN"

    # ...and the next signal cannot resend it.
    with pytest.raises(RuntimeError, match="unknown state"):
        manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)
    assert len(session.order_calls()) == 1


def test_a_200_carrying_a_real_acceptance_is_still_a_normal_fill(tmp_path):
    session = FakeSession()
    session.set("POST", ORDER_PATH,
                FakeResponse(200, {"child_order_acceptance_id": "ACC-1"}))
    manager, store, ks, notifier = _live_stack(tmp_path, session)
    order = manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)
    assert order.state is OrderState.SUBMITTED
    assert order.acceptance_id == "ACC-1"
    assert not ks.is_tripped


def test_a_cancel_may_answer_200_with_an_empty_body(fake_session):
    """`cancelchildorder` answers 200 with nothing by design; that is a
    success, not an unreadable body."""
    fake_session.set("POST", "/v1/me/cancelchildorder",
                     FakeResponse(200, None, text=""))
    client = BitflyerClient(Secret("k"), Secret("s"), session=fake_session,
                            sleep=lambda s: None)
    assert client.cancel_child_order(product_code="FX_BTC_JPY",
                                     child_order_acceptance_id="ACC-1") is None
    # A body it cannot read at all is still ambiguous, on one attempt.
    fake_session.set("POST", "/v1/me/cancelchildorder",
                     FakeResponse(200, None, text="<html>oops</html>"))
    with pytest.raises(OrderStateUnknown):
        client.cancel_child_order(product_code="FX_BTC_JPY",
                                  child_order_acceptance_id="ACC-1")
    assert len([c for c in fake_session.calls
                if "cancelchildorder" in c["path"]]) == 2


def test_a_bad_body_200_is_recorded_as_ambiguous_not_ok(tmp_path, fake_session):
    """(m6) Telemetry is written AFTER the parse: a 200 the bot could not use
    must not be counted as a healthy call."""
    path = tmp_path / "api_health.csv"
    fake_session.set("POST", ORDER_PATH,
                     FakeResponse(200, None, text="<html>maintenance</html>"))
    client = BitflyerClient(Secret("k"), Secret("s"), session=fake_session,
                            sleep=lambda s: None,
                            observer=ApiObserver(ConditionMonitor(),
                                                 ApiHealthRecorder(path)))
    with pytest.raises(OrderStateUnknown):
        client.send_child_order(product_code="FX_BTC_JPY", side="BUY", size=0.01)
    rows = [r for r in path.read_text(encoding="utf-8").splitlines()[1:] if r]
    assert len(rows) == 1
    assert rows[0].split(",")[1] == "order"
    assert rows[0].split(",")[4] == "ambiguous"


def test_a_garbled_read_body_is_just_another_retry(fake_session):
    """On an idempotent read endpoint an unreadable body is a sample to take
    again — SAFE_RETRY, not an exception the caller has to know about."""
    good = {"ltp": 1.0, "best_bid": 1.0, "best_ask": 1.0}
    fake_session.set("GET", "/v1/ticker", [
        FakeResponse(200, None, text="<html>oops</html>"),
        FakeResponse(200, good),
    ])
    client = BitflyerClient(session=fake_session, sleep=lambda s: None)
    assert client.ticker("FX_BTC_JPY")["ltp"] == 1.0
    assert len(fake_session.calls) == 2


def test_a_read_body_that_never_parses_surfaces_as_a_network_error(fake_session):
    fake_session.set("GET", "/v1/ticker",
                     FakeResponse(200, None, text="<html>oops</html>"))
    client = BitflyerClient(session=fake_session, sleep=lambda s: None)
    with pytest.raises(NetworkError, match="unparseable_body"):
        client.ticker("FX_BTC_JPY")
    assert len(fake_session.calls) == 3          # retried, then given up on


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


# ------------------- (M2) a wedged resting order must never block a close ----
class WedgedGateway(ExecutionGateway):
    """The critic's scenario, as a gateway.

    The first send fails ambiguously; reconciliation finds the order ACTIVE on
    the venue, so the book holds a live SUBMITTED record — and the venue then
    never fills it. Later sends succeed and fill at once.
    """

    def __init__(self, cancel_error: Exception | None = None,
                 cancel_honoured: bool = True):
        self.sends = 0
        self.canceled: list[str] = []
        self.cancel_error = cancel_error
        # False = the venue answers the cancel with a 2xx and keeps the order
        # ACTIVE on getchildorders anyway (m2).
        self.cancel_honoured = cancel_honoured
        self.venue = None            # set by `_wedge` so a cancel is listed
        self._states: dict[str, tuple[str, float]] = {}

    def submit_order(self, *, symbol, side, size, order_type, price):
        self.sends += 1
        if self.sends == 1:
            raise OrderStateUnknown("read timeout on sendchildorder")
        acceptance_id = f"ACC-{self.sends}"
        self._states[acceptance_id] = ("COMPLETED", size)
        return SubmitResult(acceptance_id=acceptance_id)

    def cancel_order(self, *, symbol, acceptance_id):
        if self.cancel_error is not None:
            raise self.cancel_error
        self.canceled.append(acceptance_id)
        self._states[acceptance_id] = ("CANCELED", 0.0)
        if self.venue is not None and self.cancel_honoured:
            self.venue.order = child_order(acc=acceptance_id, state="CANCELED")

    def fetch_order_status(self, *, symbol, acceptance_id):
        state, filled = self._states.get(acceptance_id, ("ACTIVE", 0.0))
        return OrderStatus(acceptance_id, state, filled,
                           11_000_000.0 if state == "COMPLETED" else None)


def _wedge(tmp_path, gateway):
    """Drive the book into the wedge: ambiguous send -> ACTIVE -> stays ACTIVE."""
    clock = VirtualClock()
    venue = LaggyVenue(clock, order=child_order(state="ACTIVE"), lag_sec=0.0)
    manager, store, ks, notifier = build_manager(tmp_path, gateway, venue,
                                                 clock=clock, budget_sec=15.0)
    # The gateway drives the venue listing, so a cancel it acknowledges is a
    # cancel the venue can be seen to have honoured (m2's verification poll).
    gateway.venue = venue
    entry = manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)
    assert entry.state is OrderState.SUBMITTED       # resolved to ACTIVE
    assert entry.acceptance_id == "ACC-NEW"
    return manager, store, ks, notifier, entry


def test_a_wedged_resting_order_never_blocks_a_protective_close(tmp_path):
    """(M2) The 2019 failure with a different cause: the position could not be
    exited — not because the venue refused, but because our OWN duplicate-order
    guard counted a resting order the venue never filled. A close outranks it:
    cancel (idempotent, safe) and retry the close once."""
    gateway = WedgedGateway()
    manager, store, ks, notifier, entry = _wedge(tmp_path, gateway)

    close = manager.refresh(manager.submit(symbol="FX_BTC_JPY", side="SELL",
                                           size=0.01, opening=False))

    assert close.state is OrderState.FILLED
    assert gateway.canceled == ["ACC-NEW"]
    assert store.get(entry.local_id).state is OrderState.CANCELED
    assert gateway.sends == 2               # one per intended order, no resend
    assert not ks.is_tripped
    assert notifier.sent == []


def test_an_entry_is_still_just_refused_by_a_resting_order(tmp_path):
    """The priority belongs to CLOSING orders only. An entry that collides with
    a resting order is skipped, exactly as before — degradation and congestion
    may only ever REDUCE exposure."""
    gateway = WedgedGateway()
    manager, store, ks, notifier, entry = _wedge(tmp_path, gateway)
    with pytest.raises(DuplicateOrderError):
        manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)
    assert gateway.canceled == []
    assert gateway.sends == 1
    assert store.get(entry.local_id).state is OrderState.SUBMITTED


def test_a_close_that_cannot_clear_the_book_alerts_and_trips_the_kill_switch(
        tmp_path):
    """(M2c) If even the cancel is ambiguous the bot cannot flatten. That is a
    human's problem NOW — an urgent alert and a tripped kill switch, never a
    quiet `submit_refused` line in the log."""
    gateway = WedgedGateway(cancel_error=OrderStateUnknown("cancel timed out"))
    manager, store, ks, notifier, entry = _wedge(tmp_path, gateway)

    with pytest.raises(DuplicateOrderError):
        manager.submit(symbol="FX_BTC_JPY", side="SELL", size=0.01,
                       opening=False)

    assert ks.is_tripped
    assert ks.state["reason"] == "system_error"
    assert entry.local_id in ks.state["detail"]        # names the wedged order
    title, message, urgent = notifier.sent[-1]
    assert title == "CANNOT CLOSE POSITION" and urgent is True
    assert entry.local_id in message
    assert gateway.sends == 1                          # zero duplicate sends


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


def _config_problems(caplog) -> list[str]:
    """The fields `load_resilience_config` complained about, from the ONE
    warning it emits (the field names live in the record's structured data)."""
    return [p for r in caplog.records
            for p in (getattr(r, "data", None) or {}).get("problems", [])]


@pytest.mark.parametrize("value", ["false", "no", "0", "1", "true", 0, 1, None])
def test_entry_gating_is_read_strictly(value, caplog):
    """(M3) A quoted "false" is a non-empty string, so `bool()` would have
    ENABLED an unregistered behavior change. Anything that is not a bare YAML
    bool falls back to OFF and says so once (composite.py's precedent)."""
    from bot.exchange.resilience import load_resilience_config
    with caplog.at_level("WARNING"):
        cfg = load_resilience_config({"entry_gating": value})
    assert cfg.entry_gating is False
    assert any("entry_gating" in p for p in _config_problems(caplog))


def test_reconcile_budget_is_range_checked(caplog):
    """(m10) Below 5s the schedule cannot outlast the venue's listing lag;
    above 60s the loop is blocked for a minute on one send. Either way it is a
    typo, not a tuning choice."""
    from bot.exchange.resilience import ResilienceConfig, load_resilience_config
    default = ResilienceConfig().reconcile_budget_sec
    with caplog.at_level("WARNING"):
        assert load_resilience_config(
            {"reconcile_budget_sec": 1}).reconcile_budget_sec == default
        assert load_resilience_config(
            {"reconcile_budget_sec": 600}).reconcile_budget_sec == default
    assert any("reconcile_budget_sec" in p for p in _config_problems(caplog))
    assert load_resilience_config(
        {"reconcile_budget_sec": 30}).reconcile_budget_sec == 30


def test_the_first_reconciliation_poll_is_capped_in_absolute_time():
    """(m10) The first poll catches an order the venue listed at once; with a
    long budget a purely proportional offset would make the caller — holding an
    order in an unknown state — wait for an answer available immediately."""
    clock = VirtualClock()
    venue = LaggyVenue(clock)
    reconciler = AutoReconciler(venue, budget_sec=120.0, sleep=clock.sleep,
                                clock=clock)
    reconciler.resolve(symbol="FX_BTC_JPY", side="BUY", size=0.01,
                       snapshot=reconciler.baseline())
    assert venue.query_times[0] == 2.0            # not 120/30 = 4.0
    assert venue.query_times[1] == 8.0            # the rest stay proportional


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


def test_the_app_tells_the_manager_what_each_order_is_for(tmp_path, monkeypatch):
    """(M2b) The manager can only give a CLOSE priority over the book if it is
    told which orders are closes. That flag is `_try_order`'s `opening`."""
    app = _paper_app(tmp_path, monkeypatch)
    from bot.market_data.feed import Tick
    tick = Tick(timestamp=1.0, price=10_000_000, best_bid=9_999_000,
                best_ask=10_001_000)
    app.feed.last_tick = tick
    seen = []
    real_submit = app.orders.submit

    def spy(**kwargs):
        seen.append(kwargs.get("opening"))
        return real_submit(**kwargs)

    app.orders.submit = spy
    app._try_order("BUY", tick)
    size = app.portfolio.position_size
    app._try_order("SELL", tick, size=size)
    assert seen == [True, False]


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


def test_an_unclassified_failure_still_counts_towards_the_api_error_kill(
        tmp_path, monkeypatch):
    """(m5) Every exemption is granted on positive evidence about what went
    wrong. "We do not know what this was" is not evidence — an error with no
    classification attached used to be exempt while DEGRADED, which is an error
    the counter could never see."""
    app = _paper_app(tmp_path, monkeypatch)
    app.condition = ExchangeCondition.CRITICAL
    assert app._counts_towards_api_errors(NetworkError("no classification"))
    assert app._counts_towards_api_errors(BitflyerError(500, "no failure obj"))
    # A classified public failure while degraded is still exempt.
    public = resilience.classify_status(400, EndpointClass.PUBLIC)
    assert not app._counts_towards_api_errors(
        BitflyerError(400, "nope", public))
    # ...and a SAFE_RETRY never counts, whatever the condition.
    app.condition = ExchangeCondition.NORMAL
    retryable = resilience.classify_exception(
        requests.exceptions.ReadTimeout("slow"), EndpointClass.PRIVATE_READ)
    assert not app._counts_towards_api_errors(NetworkError("slow", retryable))


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


def test_a_condition_applied_inside_a_diagnostic_window_survives_it(fake_session):
    """(m8) A reconciliation window can stay open for the whole budget, and the
    venue degrading DURING it is exactly when it happens. Restoring the pair
    captured on the way in threw that away and left the next trading call on
    the pre-degradation read timeout."""
    client = BitflyerClient(Secret("k"), Secret("s"), session=fake_session,
                            sleep=lambda s: None)
    client.configure(timeouts=Timeouts(connect_sec=3.0, read_sec=10.0))
    with client.diagnostic_call():
        assert client.timeouts.as_tuple() == (3.0, 5.0)
        client.apply_condition(ExchangeCondition.CRITICAL)
        assert client.timeouts.as_tuple() == (3.0, 5.0)     # window still rules
    assert client.timeouts.as_tuple() == (3.0, 30.0)        # ...and not lost

    # Nested windows restore the OUTER window first, then the trading value.
    with client.diagnostic_call():
        with client.diagnostic_call(Timeouts(3.0, 1.0, 1.0)):
            assert client.timeouts.as_tuple() == (3.0, 1.0)
        assert client.timeouts.as_tuple() == (3.0, 5.0)
    assert client.timeouts.as_tuple() == (3.0, 30.0)
    # Recovery still restores the configured base exactly.
    client.apply_condition(ExchangeCondition.NORMAL)
    assert client.timeouts.as_tuple() == (3.0, 10.0)


def test_the_loop_sweeps_open_live_orders_on_diagnostic_timeouts(tmp_path,
                                                                 monkeypatch):
    """(M2a) A LIMIT order the venue already filled must not sit in the book as
    SUBMITTED: that stale record is what makes the duplicate-order guard refuse
    the next order, which may be the protective stop."""
    from dataclasses import replace

    from bot.execution.live import LiveExecutor
    from bot.settings import Mode

    session = TimeoutRecordingSession()
    client = BitflyerClient(Secret("k"), Secret("s"), session=session,
                            sleep=lambda s: None)
    app = _paper_app(tmp_path, monkeypatch, client=client)
    app.settings = replace(app.settings, mode=Mode.LIVE)
    app.orders._gateway = LiveExecutor(app.settings, app.client)
    app.client.apply_condition(ExchangeCondition.CRITICAL)

    order = app.store.create("FX_BTC_JPY", "BUY", 0.01, "MARKET", None)
    app.store.transition(order.local_id, OrderState.SUBMITTED,
                         acceptance_id="ACC-1")
    session.set("GET", "/v1/me/getchildorders", FakeResponse(200, [{
        "child_order_acceptance_id": "ACC-1", "child_order_state": "COMPLETED",
        "executed_size": 0.01, "average_price": 11_000_000}]))

    app._last_order_sweep = -1e9
    app._sweep_open_orders()

    assert app.store.get(order.local_id).state is OrderState.FILLED
    # ...on the DIAGNOSTIC timeouts, with the trading ones restored afterwards.
    assert session.read_timeout_for("/v1/me/getchildorders") == 5.0
    assert app.client.timeouts.as_tuple() == (3.0, 30.0)

    # Bounded: a second sweep inside the window makes no call at all.
    stale = app.store.create("FX_BTC_JPY", "BUY", 0.01, "MARKET", None)
    app.store.transition(stale.local_id, OrderState.SUBMITTED,
                         acceptance_id="ACC-2")
    before = len(session.calls)
    app._sweep_open_orders()
    assert len(session.calls) == before


def test_a_failed_sweep_changes_nothing_and_never_raises(tmp_path, monkeypatch):
    from dataclasses import replace

    from bot.execution.live import LiveExecutor
    from bot.settings import Mode

    session = FakeSession()
    client = BitflyerClient(Secret("k"), Secret("s"), session=session,
                            sleep=lambda s: None)
    app = _paper_app(tmp_path, monkeypatch, client=client)
    app.settings = replace(app.settings, mode=Mode.LIVE)
    app.orders._gateway = LiveExecutor(app.settings, app.client)
    order = app.store.create("FX_BTC_JPY", "BUY", 0.01, "MARKET", None)
    app.store.transition(order.local_id, OrderState.SUBMITTED,
                         acceptance_id="ACC-1")
    session.set("GET", "/v1/me/getchildorders",
                requests.exceptions.ReadTimeout("slow"))

    app._last_order_sweep = -1e9
    app._sweep_open_orders()                       # must not raise
    assert app.store.get(order.local_id).state is OrderState.SUBMITTED


def test_paper_mode_does_not_sweep(tmp_path, monkeypatch):
    """PAPER fills synchronously, so its records are never stale — and the
    paper gateway has no venue to ask."""
    session = FakeSession()
    app = _paper_app(tmp_path, monkeypatch, session=session)
    order = app.store.create("FX_BTC_JPY", "BUY", 0.01, "MARKET", None)
    app.store.transition(order.local_id, OrderState.SUBMITTED,
                         acceptance_id="ACC-1")
    app._last_order_sweep = -1e9
    before = len(session.calls)
    app._sweep_open_orders()
    assert len(session.calls) == before


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


def test_a_stale_stop_reading_stays_sticky_until_a_fresh_reading():
    """(m9) STOP is the one reading the TTL must NOT clear.

    A stale BUSY drops out of the vote because it says nothing about load now.
    "The venue was halted and we have not heard since" is different: the poll
    that would clear it is the call that is failing, so expiring it resumes
    ENTRIES into a venue last known to be stopped, on no evidence. Only a fresh
    non-STOP reading clears it. Closes are never gated on this.
    """
    clock = _StepClock(step=0.0)
    monitor = ConditionMonitor(clock=clock, health_ttl_sec=90.0)
    monitor.observe_health("STOP")
    assert monitor.exchange_stopped

    clock.t = 10_000.0                       # the poll never came back
    assert monitor.exchange_stopped          # sticky
    assert monitor.health is None            # ...but still reported as expired
    assert monitor.snapshot()["health"] is None

    monitor.observe_health("NORMAL")         # a FRESH reading clears it
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


# ============================================================================
# (B1) A discovered fill is a BOOKED fill — one idempotent path
# ============================================================================
# The pass-3 finding: the sweep tidied the order record and told the portfolio
# nothing. A LIMIT order the venue filled moved to FILLED in the book while the
# portfolio stayed flat, so the bot read its own flat book, took the next entry
# signal and doubled a REAL position — with no protective stop armed, because
# as far as the portfolio was concerned there was nothing to protect.

def _live_app(tmp_path, monkeypatch, session=None):
    """The paper app rewired to LIVE with a real LiveExecutor over a FakeSession.

    LIVE is where the sweep runs at all (PAPER fills synchronously), so every
    discovery-path test has to be here.
    """
    from dataclasses import replace

    from bot.execution.live import LiveExecutor
    from bot.settings import Mode

    session = session or FakeSession()
    session.set("GET", "/v1/ticker", FakeResponse(200, {
        "ltp": 10_000_000, "best_bid": 9_999_000, "best_ask": 10_001_000}))
    client = BitflyerClient(Secret("k"), Secret("s"), session=session,
                            sleep=lambda s: None)
    app = _paper_app(tmp_path, monkeypatch, client=client)
    app.settings = replace(app.settings, mode=Mode.LIVE)
    app.orders._gateway = LiveExecutor(app.settings, app.client)
    return app, session


def _tick(price, spread=1000.0):
    from bot.market_data.feed import Tick
    return Tick(timestamp=1.0, price=price, best_bid=price - spread,
                best_ask=price + spread)


def _listing(state="COMPLETED", executed=0.01, avg=11_000_000, acc="ACC-1",
             side="BUY", size=0.01):
    return FakeResponse(200, [{
        "child_order_acceptance_id": acc, "child_order_state": state,
        "side": side, "size": size, "executed_size": executed,
        "average_price": avg, "child_order_date": "2026-08-21T00:00:00"}])


def test_a_sweep_discovered_fill_is_booked_into_the_portfolio(tmp_path,
                                                              monkeypatch,
                                                              caplog):
    """(B1) THE finding. The sweep is the only thing that ever sees this fill,
    so if the sweep does not book it, nothing does: the portfolio is a phantom
    flat over a real 0.01 BTC position, and the next entry doubles it."""
    app, session = _live_app(tmp_path, monkeypatch)
    order = app.store.create("FX_BTC_JPY", "BUY", 0.01, "LIMIT", 11_000_000)
    app.store.transition(order.local_id, OrderState.SUBMITTED,
                         acceptance_id="ACC-1")
    session.set("GET", "/v1/me/getchildorders", _listing())

    app._last_order_sweep = -1e9
    app._sweep_open_orders()

    # 1. the position is real to the portfolio, at the venue's own fill price
    assert app.store.get(order.local_id).state is OrderState.FILLED
    assert app.portfolio.position_size == pytest.approx(0.01)
    assert app.portfolio.avg_entry_price == pytest.approx(11_000_000)
    assert app.store.get(order.local_id).booked_size == pytest.approx(0.01)
    assert len(app.portfolio.trades) == 1

    # 2. the protective stop now ARMS: 1% against a 0.5% stop
    mark = 10_890_000.0
    loss_pct = -app.portfolio.unrealized_pnl_jpy(mark) / \
        app.portfolio.position_notional_jpy(mark) * 100
    assert loss_pct >= app.stop_loss_pct

    # 3. ...and MAX_POSITION_SIZE binds, so the second entry is refused rather
    #    than doubling the live position.
    tick = _tick(mark)
    app.feed.last_tick = tick
    with caplog.at_level(logging.WARNING, logger="bot.main"):
        assert app._try_order("BUY", tick) is None
    reasons = [r for rec in caplog.records
               for r in (getattr(rec, "data", None) or {}).get("reasons", [])]
    assert any("MAX_POSITION_SIZE" in r for r in reasons)
    assert session.order_calls() == []          # nothing was sent


def test_the_submit_path_and_a_later_sweep_book_one_fill_between_them(
        tmp_path, monkeypatch):
    """(B1) Two discovery paths, ONE booking. The submit-path refresh sees the
    partial first; the sweep sees the same partial 30s later and must add
    nothing — `booked_size` is what makes that true rather than lucky."""
    app, session = _live_app(tmp_path, monkeypatch)
    session.set("POST", ORDER_PATH,
                FakeResponse(200, {"child_order_acceptance_id": "ACC-1"}))
    session.set("GET", "/v1/me/getchildorders",
                _listing(state="ACTIVE", executed=0.004, avg=11_950_000,
                         size=0.01))
    tick = _tick(12_000_000, spread=0.0)        # -> a 0.01 order
    app.feed.last_tick = tick

    order = app._try_order("BUY", tick)

    assert order.state is OrderState.PARTIALLY_FILLED   # ACTIVE + executed_size
    assert app.portfolio.position_size == pytest.approx(0.004)
    assert len(app.portfolio.trades) == 1

    app._last_order_sweep = -1e9
    app._sweep_open_orders()                    # same listing, same fill

    assert app.portfolio.position_size == pytest.approx(0.004)
    assert len(app.portfolio.trades) == 1       # booked ONCE in total


def test_a_growing_partial_books_only_the_delta(tmp_path, monkeypatch):
    """A partial that grows while the order stays on the book must book the
    DIFFERENCE. The record used to freeze at the first `filled_size` it saw
    (same-state refreshes were skipped), so every later execution vanished."""
    app, session = _live_app(tmp_path, monkeypatch)
    order = app.store.create("FX_BTC_JPY", "BUY", 0.01, "LIMIT", 11_000_000)
    app.store.transition(order.local_id, OrderState.SUBMITTED,
                         acceptance_id="ACC-1")

    session.set("GET", "/v1/me/getchildorders",
                _listing(state="ACTIVE", executed=0.004, avg=11_000_000))
    app._last_order_sweep = -1e9
    app._sweep_open_orders()
    assert app.portfolio.position_size == pytest.approx(0.004)

    session.set("GET", "/v1/me/getchildorders",
                _listing(state="COMPLETED", executed=0.010, avg=11_000_000))
    app._last_order_sweep = -1e9
    app._sweep_open_orders()

    assert app.portfolio.position_size == pytest.approx(0.010)
    assert len(app.portfolio.trades) == 2       # 0.004 then 0.006, never 0.014
    assert app.portfolio.trades[-1].size == pytest.approx(0.006)


def test_the_reconciler_books_a_partial_fill(tmp_path, monkeypatch):
    """(B1) The third discovery path. An ambiguous send resolves against a
    venue that reports ACTIVE with executed_size 0.004: that is a PARTIAL fill,
    not a resting order with nothing done, and the 0.004 has to reach the
    portfolio."""
    session = FakeSession()
    session.set("POST", ORDER_PATH, requests.exceptions.ReadTimeout("slow"))
    app, session = _live_app(tmp_path, monkeypatch, session=session)
    app.orders._reconciler = AutoReconciler(QueryOnlyExchange(app.client),
                                            budget_sec=15.0,
                                            sleep=lambda s: None)
    session.set("GET", "/v1/me/getchildorders",
                _listing(acc="ACC-NEW", state="ACTIVE", executed=0.004,
                         avg=11_950_000, size=0.01))
    tick = _tick(12_000_000, spread=0.0)        # -> a 0.01 order
    app.feed.last_tick = tick

    order = app._try_order("BUY", tick)

    assert order.state is OrderState.PARTIALLY_FILLED
    assert order.filled_size == pytest.approx(0.004)
    assert app.portfolio.position_size == pytest.approx(0.004)
    assert app.portfolio.avg_entry_price == pytest.approx(11_950_000)
    assert app.store.get(order.local_id).booked_size == pytest.approx(0.004)
    assert not app.kill_switch.is_tripped       # resolved, so no freeze
    assert len(session.order_calls()) == 1      # and never resent


def test_the_paper_booking_path_is_unchanged(tmp_path, monkeypatch):
    """PAPER fills synchronously on the submit path, books once, and never
    sweeps. The refactor must be invisible here."""
    app = _paper_app(tmp_path, monkeypatch)
    tick = _tick(10_000_000)
    app.feed.last_tick = tick

    order = app._try_order("BUY", tick)

    assert order.state is OrderState.FILLED
    position = app.portfolio.position_size
    assert position > 0
    assert app.store.get(order.local_id).booked_size == pytest.approx(
        order.filled_size)
    assert len(app.portfolio.trades) == 1

    # Idempotent: asking again books nothing.
    app._book_fill_delta(app.store.get(order.local_id))
    assert app.portfolio.position_size == pytest.approx(position)
    assert len(app.portfolio.trades) == 1

    # ...and PAPER has no sweep to discover anything with.
    app._last_order_sweep = -1e9
    app._sweep_open_orders()
    assert app.portfolio.position_size == pytest.approx(position)
    assert len(app.portfolio.trades) == 1


# ------------------------------------------- (m3) the sweep's cost bound ----
def test_the_sweep_flags_a_book_with_more_than_one_open_order(tmp_path,
                                                              monkeypatch,
                                                              caplog):
    """(m3) The sweep costs one diagnostic GET per non-terminal order, and it
    is bounded at one because `create` refuses a second. That invariant is
    checked cheaply and LOGGED — never raised, or a surprising book would kill
    trading from inside a best-effort sweep."""
    app, session = _live_app(tmp_path, monkeypatch)
    a = app.store.create("FX_BTC_JPY", "BUY", 0.01, "LIMIT", 11_000_000)
    app.store.transition(a.local_id, OrderState.SUBMITTED, acceptance_id="ACC-1")
    b = app.store.create("BTC_JPY", "BUY", 0.001, "LIMIT", 11_000_000)
    app.store.transition(b.local_id, OrderState.SUBMITTED, acceptance_id="ACC-2")
    both = [app.store.get(a.local_id), app.store.get(b.local_id)]
    monkeypatch.setattr(app.store, "active_orders", lambda symbol=None: both)
    session.set("GET", "/v1/me/getchildorders", FakeResponse(200, []))

    app._last_order_sweep = -1e9
    with caplog.at_level(logging.ERROR, logger="bot.main"):
        app._sweep_open_orders()                # must not raise

    events = [(getattr(r, "data", None) or {}).get("event") for r in caplog.records]
    assert "sweep_invariant_broken" in events


# ============================================================================
# (M1) a rejected CLOSE is an emergency, a rejected entry is a skipped tick
# ============================================================================
class RejectingGateway(ExecutionGateway):
    """The venue answers a definite business error: 'insufficient margin'."""

    def __init__(self):
        self.sends = 0

    def submit_order(self, *, symbol, side, size, order_type, price):
        self.sends += 1
        raise BitflyerError(400, "insufficient margin")

    def cancel_order(self, *, symbol, acceptance_id):
        pass

    def fetch_order_status(self, *, symbol, acceptance_id):
        return None


def test_a_rejected_close_takes_the_loud_path(tmp_path):
    """(M1) The position is still open and the bot has just found out it
    cannot exit. That is the 2019 failure, and a `warning` line is not how it
    gets said."""
    gateway = RejectingGateway()
    manager, store, ks, notifier = build_manager(tmp_path, gateway,
                                                 FakeExchange())

    order = manager.submit(symbol="FX_BTC_JPY", side="SELL", size=0.01,
                           opening=False)

    assert order.state is OrderState.REJECTED
    assert ks.is_tripped and ks.state["reason"] == "system_error"
    assert "insufficient margin" in ks.state["detail"]
    title, message, urgent = notifier.sent[-1]
    assert title == "CANNOT CLOSE POSITION" and urgent is True
    assert "SELL 0.01 FX_BTC_JPY" in message
    assert gateway.sends == 1                   # and never resent


def test_a_rejected_entry_is_still_only_a_warning(tmp_path):
    """The mirror image: an entry the venue refused leaves the bot holding no
    more risk than a moment ago. Skipped tick, no freeze, no alert."""
    gateway = RejectingGateway()
    manager, store, ks, notifier = build_manager(tmp_path, gateway,
                                                 FakeExchange())

    order = manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)

    assert order.state is OrderState.REJECTED
    assert not ks.is_tripped
    assert notifier.sent == []
    assert gateway.sends == 1


# ============================================================================
# (m1/m2) clearing the way for a close: scoped, and verified
# ============================================================================
def test_only_the_blocking_orders_are_cancelled_to_clear_a_close(tmp_path):
    """(m1) The close cancels exactly the ids the store named as blockers, not
    'everything active by the time we got here'."""
    gateway = WedgedGateway()
    manager, store, ks, notifier, entry = _wedge(tmp_path, gateway)
    other = store.create("BTC_JPY", "BUY", 0.001, "MARKET", None)
    store.transition(other.local_id, OrderState.SUBMITTED,
                     acceptance_id="ACC-OTHER")
    assert store.blocking_order_ids("FX_BTC_JPY") == [entry.local_id]

    close = manager.refresh(manager.submit(symbol="FX_BTC_JPY", side="SELL",
                                           size=0.01, opening=False))

    assert close.state is OrderState.FILLED
    assert gateway.canceled == ["ACC-NEW"]              # the blocker, alone
    assert store.get(other.local_id).state is OrderState.SUBMITTED
    assert not ks.is_tripped


def test_a_cancel_the_venue_did_not_honour_blocks_the_close(tmp_path):
    """(m2) The venue answers the cancel 2xx and keeps the order ACTIVE. On the
    strength of that 2xx alone the close would go out ALONGSIDE a live order —
    one intended exit, two real orders. No send: alert and kill switch."""
    gateway = WedgedGateway(cancel_honoured=False)
    manager, store, ks, notifier, entry = _wedge(tmp_path, gateway)

    with pytest.raises(DuplicateOrderError):
        manager.submit(symbol="FX_BTC_JPY", side="SELL", size=0.01,
                       opening=False)

    assert gateway.sends == 1                   # the close was NEVER sent
    assert ks.is_tripped and ks.state["reason"] == "system_error"
    assert "ACC-NEW" in ks.state["detail"]
    title, message, urgent = notifier.sent[-1]
    assert title == "CANNOT CLOSE POSITION" and urgent is True


class FlakyVenue(LaggyVenue):
    """Lists the order, then fails every later poll — so the CANCEL can be
    acknowledged but never verified."""

    def __init__(self, *args, fail_after=1, **kwargs):
        super().__init__(*args, **kwargs)
        self.fail_after = fail_after

    def child_orders(self, symbol):
        rows = super().child_orders(symbol)
        if self.order_queries > self.fail_after:
            raise NetworkError("getchildorders timed out")
        return rows


def test_an_unverifiable_cancel_blocks_the_close(tmp_path):
    """(m2) Same rule for 'we could not check'. Absence of evidence that the
    book is clear is not evidence that it is."""
    clock = VirtualClock()
    venue = FlakyVenue(clock, order=child_order(state="ACTIVE"), lag_sec=0.0,
                       fail_after=1)
    gateway = WedgedGateway()
    manager, store, ks, notifier = build_manager(tmp_path, gateway, venue,
                                                 clock=clock, budget_sec=15.0)
    gateway.venue = venue
    entry = manager.submit(symbol="FX_BTC_JPY", side="BUY", size=0.01)
    assert entry.state is OrderState.SUBMITTED

    with pytest.raises(DuplicateOrderError):
        manager.submit(symbol="FX_BTC_JPY", side="SELL", size=0.01,
                       opening=False)

    assert gateway.sends == 1                   # no close on an unverified book
    assert ks.is_tripped and "could not be read" in ks.state["detail"]
    assert notifier.sent[-1][0] == "CANNOT CLOSE POSITION"


# ------------------------------------------ (m4) the kill file is redacted --
def test_a_secret_in_a_kill_detail_is_redacted_on_disk(tmp_path):
    """(m4) `detail` is usually an exception string, and an exception string is
    a likely place for a key or a signed URL. It is persisted and alerted out,
    so it goes through the same filter as every log line."""
    from bot.logging_setup import register_secret
    from bot.risk.kill_switch import KillReason

    register_secret("k1ll-sw1tch-t3st-s3cr3t")
    ks = KillSwitch(state_dir=tmp_path, manual_file=tmp_path / "KILL")
    ks.trip(KillReason.SYSTEM_ERROR,
            "auth failed for key k1ll-sw1tch-t3st-s3cr3t on /v1/me/sendchildorder")

    on_disk = (tmp_path / "kill_switch.json").read_text(encoding="utf-8")
    assert "k1ll-sw1tch-t3st-s3cr3t" not in on_disk
    assert "***REDACTED***" in on_disk
    assert "***REDACTED***" in ks.state["detail"]
    assert "/v1/me/sendchildorder" in ks.state["detail"]   # diagnosis survives


# ============================================================================
# (B1) the open-order cap must not be able to refuse the exit
# ============================================================================
# The pass-4 finding: MAX_OPEN_ORDERS was the one cap still checked for EVERY
# order. A book at the cap therefore refused the protective stop inside the
# risk checks — before the order manager ran at all, so `_make_room_for_close`
# (which exists to cancel exactly that resting order) was never reached. The
# wedge it was built to clear could never be cleared.

def _reconciled(app):
    """Give a LIVE app the query-only reconciler its LIVE wiring would have."""
    app.orders._reconciler = AutoReconciler(QueryOnlyExchange(app.client),
                                            budget_sec=15.0, sleep=lambda s: None)
    return app


def _cancel_ok(session):
    session.set("POST", "/v1/me/cancelchildorder", FakeResponse(200, {}))


def test_the_open_order_cap_can_no_longer_refuse_the_protective_stop(
        tmp_path, monkeypatch, caplog):
    """(B1) THE finding, end to end on a LIVE app.

    One real position, one resting order the venue never finished, MAX_OPEN_
    ORDERS = 1, and a price through the stop. Every one of those is ordinary;
    together they used to mean the position could not be exited.
    """
    app, session = _live_app(tmp_path, monkeypatch)
    _reconciled(app)
    _cancel_ok(session)
    assert app.settings.risk_limits.max_open_orders == 1

    # a real long 0.01, discovered and booked by the sweep
    entry = app.store.create("FX_BTC_JPY", "BUY", 0.01, "LIMIT", 11_000_000)
    app.store.transition(entry.local_id, OrderState.SUBMITTED,
                         acceptance_id="ACC-ENTRY")
    session.set("GET", "/v1/me/getchildorders",
                _listing(acc="ACC-ENTRY", state="COMPLETED", executed=0.01,
                         avg=11_000_000))
    app._last_order_sweep = -1e9
    app._sweep_open_orders()
    assert app.portfolio.position_size == pytest.approx(0.01)

    # ...and the wedge: a resting order the venue partly filled and then sat on
    blocker = app.store.create("FX_BTC_JPY", "BUY", 0.01, "LIMIT", 10_500_000)
    app.store.transition(blocker.local_id, OrderState.PARTIALLY_FILLED,
                         acceptance_id="ACC-BLOCK", filled_size=0.002,
                         avg_fill_price=10_500_000)
    app._book_fill_delta(app.store.get(blocker.local_id))
    assert app.portfolio.position_size == pytest.approx(0.012)
    assert len(app.store.active_orders("FX_BTC_JPY")) == 1     # at the cap

    mark = 10_800_000.0
    tick = _tick(mark, spread=0.0)
    app.feed.last_tick = tick
    loss_pct = -app.portfolio.unrealized_pnl_jpy(mark) / \
        app.portfolio.position_notional_jpy(mark) * 100
    assert loss_pct >= app.stop_loss_pct              # the stop is due

    session.set("POST", ORDER_PATH,
                FakeResponse(200, {"child_order_acceptance_id": "ACC-STOP"}))
    session.set("GET", "/v1/me/getchildorders", [
        # 1. the cancel-verification poll: the blocker has left the book
        _listing(acc="ACC-BLOCK", state="CANCELED", executed=0.002,
                 avg=10_500_000, size=0.01),
        # 2. the post-submit refresh of the stop itself
        _listing(acc="ACC-STOP", state="COMPLETED", executed=0.012, avg=mark,
                 side="SELL", size=0.012),
    ])

    with caplog.at_level(logging.WARNING, logger="bot.orders"):
        stop = app._try_order("SELL", tick, size=abs(app.portfolio.position_size))

    # the risk checks approved it, so the manager was reached and the
    # closing-order priority path ran...
    events = [(getattr(r, "data", None) or {}).get("event") for r in caplog.records]
    assert "closing_order_priority" in events
    # ...the blocker was cancelled and verified, and the stop booked
    assert stop is not None and stop.state is OrderState.FILLED
    assert app.store.get(blocker.local_id).state is OrderState.CANCELED
    sent = [c for c in session.order_calls() if ORDER_PATH in c["path"]]
    canceled = [c for c in session.order_calls() if "cancelchildorder" in c["path"]]
    assert len(sent) == 1 and len(canceled) == 1
    assert app.portfolio.position_size == pytest.approx(0.0)
    assert not app.kill_switch.is_tripped


# ============================================================================
# (M1) a cancel is not a rewind: what the blocker filled on the way out
# ============================================================================
def test_a_cancelled_blockers_partial_fill_is_booked(tmp_path, monkeypatch):
    """(M1) The venue filled 0.007 of the resting order before our cancel
    landed and says so on the CANCELED record. Nothing would ever look at that
    order again, so if the cancel path does not book it, nothing does — and the
    bot goes on holding a position it thinks it has closed."""
    app, session = _live_app(tmp_path, monkeypatch)
    _reconciled(app)
    _cancel_ok(session)

    # long 0.01 @ 11,000,000, booked
    entry = app.store.create("FX_BTC_JPY", "BUY", 0.01, "LIMIT", 11_000_000)
    app.store.transition(entry.local_id, OrderState.SUBMITTED,
                         acceptance_id="ACC-ENTRY")
    session.set("GET", "/v1/me/getchildorders",
                _listing(acc="ACC-ENTRY", state="COMPLETED", executed=0.01,
                         avg=11_000_000))
    app._last_order_sweep = -1e9
    app._sweep_open_orders()

    # a resting order our book believes has done NOTHING
    blocker = app.store.create("FX_BTC_JPY", "BUY", 0.01, "LIMIT", 10_900_000)
    app.store.transition(blocker.local_id, OrderState.SUBMITTED,
                         acceptance_id="ACC-BLOCK")

    mark = 10_800_000.0
    tick = _tick(mark, spread=0.0)
    app.feed.last_tick = tick
    session.set("POST", ORDER_PATH,
                FakeResponse(200, {"child_order_acceptance_id": "ACC-STOP"}))
    session.set("GET", "/v1/me/getchildorders", [
        # the verification poll — and the venue's final word on the blocker
        _listing(acc="ACC-BLOCK", state="CANCELED", executed=0.007,
                 avg=10_900_000, size=0.01),
        _listing(acc="ACC-STOP", state="COMPLETED", executed=0.01, avg=mark,
                 side="SELL", size=0.01),
    ])

    app._try_order("SELL", tick, size=abs(app.portfolio.position_size))

    # the 0.007 reached the portfolio, at the venue's own price
    record = app.store.get(blocker.local_id)
    assert record.state is OrderState.CANCELED
    assert record.filled_size == pytest.approx(0.007)
    assert record.booked_size == pytest.approx(0.007)
    # ...so the close (sized 0.01, decided before the cancel) leaves a RESIDUAL
    # long of 0.007, and it is visible instead of being a phantom flat
    assert app.portfolio.position_size == pytest.approx(0.007)
    # and the protective stop still manages what is left
    residual_loss = -app.portfolio.unrealized_pnl_jpy(mark) / \
        app.portfolio.position_notional_jpy(mark) * 100
    assert residual_loss >= app.stop_loss_pct


def test_the_kill_switch_cancel_books_what_it_finalizes(tmp_path, monkeypatch):
    """(M1) Same rule on the shutdown path — and the OPEN POSITION line the
    operator is handed has to be the position they will actually find on
    bitFlyer, so the booking happens BEFORE the message is built."""
    app, session = _live_app(tmp_path, monkeypatch)
    notifier = RecordingNotifier()
    app.notifier = notifier
    _cancel_ok(session)

    entry = app.store.create("FX_BTC_JPY", "BUY", 0.01, "LIMIT", 11_000_000)
    app.store.transition(entry.local_id, OrderState.SUBMITTED,
                         acceptance_id="ACC-ENTRY")
    session.set("GET", "/v1/me/getchildorders",
                _listing(acc="ACC-ENTRY", state="COMPLETED", executed=0.01,
                         avg=11_000_000))
    app._last_order_sweep = -1e9
    app._sweep_open_orders()
    assert app.portfolio.position_size == pytest.approx(0.01)

    resting = app.store.create("FX_BTC_JPY", "BUY", 0.01, "LIMIT", 10_900_000)
    app.store.transition(resting.local_id, OrderState.SUBMITTED,
                         acceptance_id="ACC-REST")
    # no verification listing on this path: the record is re-read directly
    session.set("GET", "/v1/me/getchildorders",
                _listing(acc="ACC-REST", state="CANCELED", executed=0.004,
                         avg=10_900_000, size=0.01))

    app.kill_switch.trip(KillReason.API_ERRORS, "5 in a row")
    app._on_kill("5 in a row")

    assert app.store.get(resting.local_id).state is OrderState.CANCELED
    assert app.portfolio.position_size == pytest.approx(0.014)
    title, message, urgent = notifier.sent[-1]
    assert title == "KILL SWITCH" and urgent is True
    assert "LONG 0.014" in message          # post-booking, not 0.01


# ============================================================================
# (M2) a LIVE restart must not boot into a phantom flat
# ============================================================================
def _live_boot_app(tmp_path, monkeypatch, *, positions, notifier=None,
                   balance=200_000.0):
    """A REAL LIVE TradingApp construction, not a paper app rewired afterwards.

    M2 is about what the LIVE BOOT does, so the boot has to be the real one:
    the permissions check, the balance read, and now the getpositions
    reconciliation. `positions` is the getpositions route (payload or raise).
    """
    import shutil
    from pathlib import Path

    from bot.main import TradingApp
    from bot.settings import Mode, RiskLimits, Settings

    repo = Path(__file__).resolve().parents[1]
    shutil.copytree(repo / "config", tmp_path / "config", dirs_exist_ok=True)
    monkeypatch.chdir(tmp_path)
    session = FakeSession()
    session.set("GET", "/v1/ticker", FakeResponse(200, {
        "ltp": 10_000_000, "best_bid": 9_999_000, "best_ask": 10_001_000}))
    session.set("GET", "/v1/me/getpermissions", FakeResponse(200, [
        "/v1/me/getbalance", "/v1/me/sendchildorder"]))
    session.set("GET", "/v1/me/getbalance", FakeResponse(200, [
        {"currency_code": "JPY", "available": balance}]))
    session.set("GET", "/v1/me/getpositions", positions)
    client = BitflyerClient(Secret("k"), Secret("s"), session=session,
                            sleep=lambda s: None)
    settings = Settings(
        mode=Mode.LIVE, product_code="FX_BTC_JPY",
        api_key=Secret("k"), api_secret=Secret("s"),
        config={"product_code": "FX_BTC_JPY", "candle_interval_sec": 60,
                "sfd_guard_pct": 4.5, "stop_loss_pct": 0.5,
                "strategy": {"name": "xborder_momentum",
                             "params": {"k": 2, "thr_pct": 0.15,
                                        "exit_pct": 0.03}},
                "costs": {"slippage_pct": 0.0},
                "market_data": {"max_staleness_sec": 3600,
                                "max_price_jump_pct": 50, "max_spread_pct": 5.0}},
        risk_limits=RiskLimits.from_dict({
            "MAX_ORDER_SIZE_JPY": 130000, "MAX_POSITION_SIZE_JPY": 130000,
            "MAX_DAILY_LOSS_JPY": 6000, "MAX_DRAWDOWN_PCT": 10.0,
            "MAX_OPEN_ORDERS": 1, "MAX_CONSECUTIVE_LOSSES": 5,
            "MAX_API_ERRORS_IN_ROW": 5}))
    return TradingApp(settings, client, notifier or RecordingNotifier()), session


def test_live_boot_adopts_the_venue_position(tmp_path, monkeypatch):
    """(M2) THE finding. LIVE keeps no local book because the venue owns it —
    but "no book" was implemented as "start flat", so every restart booted a
    portfolio that believed it held nothing over a real position. No path would
    have corrected it: the sweep only re-reads orders THIS book knows."""
    notifier = RecordingNotifier()
    app, session = _live_boot_app(
        tmp_path, monkeypatch, notifier=notifier,
        positions=FakeResponse(200, [
            {"product_code": "FX_BTC_JPY", "side": "BUY", "price": 11_000_000,
             "size": 0.004, "pnl": -120}]))

    assert not app.kill_switch.is_tripped
    assert app.portfolio.position_size == pytest.approx(0.004)
    assert app.portfolio.avg_entry_price == pytest.approx(11_000_000)
    adopted = [s for s in notifier.sent if "adopted venue position" in s[1]]
    assert adopted and "LONG 0.004" in adopted[0][1]

    # the protective stop now ARMS on an adverse move, which is the whole point
    mark = 10_900_000.0
    tick = _tick(mark, spread=0.0)
    app.feed.last_tick = tick
    loss_pct = -app.portfolio.unrealized_pnl_jpy(mark) / \
        app.portfolio.position_notional_jpy(mark) * 100
    assert loss_pct >= app.stop_loss_pct

    session.set("POST", ORDER_PATH,
                FakeResponse(200, {"child_order_acceptance_id": "ACC-STOP"}))
    session.set("GET", "/v1/me/getchildorders",
                _listing(acc="ACC-STOP", state="COMPLETED", executed=0.004,
                         avg=mark, side="SELL", size=0.004))
    stop = app._try_order("SELL", tick, size=0.004)
    assert stop is not None and stop.state is OrderState.FILLED
    assert app.portfolio.position_size == pytest.approx(0.0)


def test_live_boot_refuses_to_trade_when_the_venue_cannot_be_read(tmp_path,
                                                                  monkeypatch):
    """(M2) The other half. Not knowing whether a position is open is not the
    same as being flat, and guessing flat is the phantom state chosen on
    purpose. Refusal, and a human decides."""
    notifier = RecordingNotifier()
    app, session = _live_boot_app(
        tmp_path, monkeypatch, notifier=notifier,
        positions=requests.exceptions.ReadTimeout("getpositions timed out"))

    assert app.kill_switch.is_tripped
    assert app.kill_switch.state["reason"] == "system_error"
    assert app.kill_switch.state["detail"] == "live boot reconciliation failed"
    assert notifier.sent[-1][0] == "LIVE BOOT RECONCILIATION FAILED"
    assert notifier.sent[-1][2] is True

    # and nothing can be ordered from that state
    session.set("POST", ORDER_PATH,
                FakeResponse(200, {"child_order_acceptance_id": "ACC-NOPE"}))
    tick = _tick(10_000_000.0)
    app.feed.last_tick = tick
    assert app._try_order("BUY", tick) is None
    app.step()
    assert [c for c in session.order_calls() if ORDER_PATH in c["path"]] == []


def test_paper_boot_never_asks_the_venue_for_a_position(tmp_path, monkeypatch):
    """(M2) PAPER's book is `data/paper_state.json` and its executor is local.
    The reconciliation is LIVE-only; PAPER must not have changed at all."""
    session = FakeSession()
    session.set("GET", "/v1/ticker", FakeResponse(200, {
        "ltp": 10_000_000, "best_bid": 9_999_000, "best_ask": 10_001_000}))
    app = _paper_app(tmp_path, monkeypatch, session=session)

    assert app.paper_state is not None
    assert app.portfolio.position_size == 0.0
    assert not app.kill_switch.is_tripped
    assert [c for c in session.calls if "getpositions" in c["path"]] == []


# ============================================================================
# (m1/m2/m3) what the booking path says, and what it must not do twice
# ============================================================================
def _failing_mark_booked(app, monkeypatch) -> dict:
    """Make the store's watermark write fail until the test says otherwise.

    A flag rather than `monkeypatch.undo()`: undo would also restore the cwd
    these app fixtures chdir'd into, and the app writes status/state files
    relative to it.
    """
    real = app.store.mark_booked
    failing = {"on": True}

    def mark_booked(*args, **kwargs):
        if failing["on"]:
            raise sqlite3.OperationalError("database is locked")
        return real(*args, **kwargs)

    monkeypatch.setattr(app.store, "mark_booked", mark_booked)
    return failing


def _fill_booked_records(caplog):
    return [(getattr(r, "data", None) or {}) for r in caplog.records
            if (getattr(r, "data", None) or {}).get("event") == "fill_booked"]


def test_a_booked_fill_names_the_price_it_used(tmp_path, monkeypatch, caplog):
    """(m1) "The position moved" and "the position moved at a price the venue
    never confirmed" are different facts, and only one of them is a reason to
    go and look at the venue."""
    app, session = _live_app(tmp_path, monkeypatch)
    order = app.store.create("FX_BTC_JPY", "BUY", 0.01, "LIMIT", 11_000_000)
    app.store.transition(order.local_id, OrderState.SUBMITTED,
                         acceptance_id="ACC-1")
    session.set("GET", "/v1/me/getchildorders",
                _listing(state="COMPLETED", executed=0.01, avg=11_050_000))
    app._last_order_sweep = -1e9
    with caplog.at_level(logging.INFO, logger="bot.main"):
        app._sweep_open_orders()
    booked = _fill_booked_records(caplog)
    assert booked[-1]["price_source"] == "venue_avg"
    assert booked[-1]["price"] == pytest.approx(11_050_000)

    # ...and a venue that reports no average price falls back, visibly
    caplog.clear()
    second = app.store.create("FX_BTC_JPY", "BUY", 0.01, "LIMIT", 10_900_000)
    app.store.transition(second.local_id, OrderState.SUBMITTED,
                         acceptance_id="ACC-2")
    session.set("GET", "/v1/me/getchildorders",
                _listing(acc="ACC-2", state="COMPLETED", executed=0.01, avg=None))
    app._last_order_sweep = -1e9
    with caplog.at_level(logging.INFO, logger="bot.main"):
        app._sweep_open_orders()
    booked = _fill_booked_records(caplog)
    assert booked[-1]["price_source"] == "order_price"
    assert booked[-1]["price"] == pytest.approx(10_900_000)


def test_a_failed_watermark_write_never_books_the_same_fill_twice(
        tmp_path, monkeypatch, caplog):
    """(m2) `mark_booked` is a write, and writes fail. The portfolio has
    already moved by then, so replaying the fill on the next discovery would
    DOUBLE a real position to repair a bookkeeping error — the worse of the two
    directions by far. Only the watermark write is retried."""
    app, session = _live_app(tmp_path, monkeypatch)
    order = app.store.create("FX_BTC_JPY", "BUY", 0.01, "LIMIT", 11_000_000)
    app.store.transition(order.local_id, OrderState.SUBMITTED,
                         acceptance_id="ACC-1")
    # ACTIVE + executed_size: the record stays non-terminal, so the sweep keeps
    # rediscovering exactly this fill.
    session.set("GET", "/v1/me/getchildorders",
                _listing(state="ACTIVE", executed=0.004, avg=11_000_000))

    failing = _failing_mark_booked(app, monkeypatch)
    app._last_order_sweep = -1e9
    with caplog.at_level(logging.CRITICAL, logger="bot.main"):
        app._sweep_open_orders()

    assert app.portfolio.position_size == pytest.approx(0.004)
    assert app.store.get(order.local_id).booked_size == 0.0    # never persisted
    events = [(getattr(r, "data", None) or {}).get("event") for r in caplog.records]
    assert "mark_booked_failed" in events

    app._last_order_sweep = -1e9
    app._sweep_open_orders()                    # same fill, seen again
    assert app.portfolio.position_size == pytest.approx(0.004)
    assert len(app.portfolio.trades) == 1

    failing["on"] = False                       # the store recovers
    app._last_order_sweep = -1e9
    app._sweep_open_orders()
    assert app.store.get(order.local_id).booked_size == pytest.approx(0.004)
    assert app.portfolio.position_size == pytest.approx(0.004)
    assert len(app.portfolio.trades) == 1


def test_paper_persists_its_book_before_the_watermark(tmp_path, monkeypatch):
    """(m3) The crash window between the two writes, closed by ordering.

    `paper_state` carries the POSITION and is written first; the watermark is
    only bookkeeping about an order PAPER will never look at again (its records
    are terminal on the submit path and there is no sweep in PAPER). So a crash
    in between loses the watermark and nothing else — never the position, and
    never by doubling it."""
    import json

    from bot.main import TradingApp
    from bot.monitoring.notifier import NullNotifier

    app = _paper_app(tmp_path, monkeypatch)
    tick = _tick(10_000_000)
    app.feed.last_tick = tick

    failing = _failing_mark_booked(app, monkeypatch)
    order = app._try_order("BUY", tick)
    position = app.portfolio.position_size
    assert position > 0
    assert order.state is OrderState.FILLED                 # terminal
    assert app.store.get(order.local_id).booked_size == 0.0   # the lost write

    saved = json.loads((tmp_path / "data" / "paper_state.json")
                       .read_text(encoding="utf-8"))
    assert saved["position"]["size"] == pytest.approx(position)

    failing["on"] = False
    restarted = TradingApp(app.settings, app.client, NullNotifier())

    assert restarted.portfolio.position_size == pytest.approx(position)
    assert len(restarted.portfolio.trades) == 0     # restored, not re-booked
    restarted._last_order_sweep = -1e9
    restarted._sweep_open_orders()                  # PAPER: nothing to sweep
    assert restarted.portfolio.position_size == pytest.approx(position)


def test_a_cancel_that_raced_a_complete_fill_is_recorded_as_filled(tmp_path,
                                                                   monkeypatch):
    """(M1) The cancel lost the race. The venue says COMPLETED, so the record
    says FILLED — a CANCELED record whose entire size executed would be a book
    that contradicts itself — and the whole size is booked."""
    app, session = _live_app(tmp_path, monkeypatch)
    _cancel_ok(session)
    resting = app.store.create("FX_BTC_JPY", "BUY", 0.01, "LIMIT", 11_000_000)
    app.store.transition(resting.local_id, OrderState.SUBMITTED,
                         acceptance_id="ACC-REST")
    session.set("GET", "/v1/me/getchildorders",
                _listing(acc="ACC-REST", state="COMPLETED", executed=0.01,
                         avg=11_000_000))

    canceled = app.orders.cancel_all_active("FX_BTC_JPY")

    assert [o.state for o in canceled] == [OrderState.FILLED]
    assert app.portfolio.position_size == pytest.approx(0.01)
    assert app.store.get(resting.local_id).booked_size == pytest.approx(0.01)

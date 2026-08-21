"""Thin bitFlyer REST client.

Implements the documented auth scheme (https://lightning.bitflyer.com/docs):
private requests carry ACCESS-KEY / ACCESS-TIMESTAMP / ACCESS-SIGN headers where
ACCESS-SIGN = HMAC-SHA256(secret, timestamp + method + request_path + body).
Run scripts/check_api.py from a network-enabled environment to verify the spec
still matches before any live use.

Design constraints honored here:
- API secret is a `Secret`; it never appears in exceptions or logs.
- Self rate-limiting below the published limits, exponential backoff on 429/5xx.
- Network-ambiguous failures on order endpoints raise OrderStateUnknown and are
  NEVER retried here — the order manager must reconcile state first (rule 12).

Every failure is routed through bot.exchange.resilience, which owns the
taxonomy (SAFE_RETRY / AMBIGUOUS / REJECTED) and the single `may_retry`
predicate. On an ORDER endpoint only a PROVABLY pre-send failure (a connect
timeout, or a connection error whose text names the new-connection failure —
`resilience._PRE_SEND_MARKERS`; a TLS error is NEVER one) is repeated — anything
that could have reached order placement, including a 5xx AND a 200 whose body
is not the answer the endpoint promised, becomes OrderStateUnknown. Timeouts
are split connect/read and widen under load.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import random
import time
from contextlib import contextmanager
from typing import Any

import requests

from bot.exchange import resilience
from bot.exchange.resilience import (
    DIAGNOSTIC_TIMEOUTS, ApiObserver, EndpointClass, ExchangeCondition, Failure,
    FailureClass, Phase, RetryPolicy, Timeouts,
)
from bot.settings import Secret

BASE_URL = "https://api.bitflyer.com"

# Kept for callers that imported it; the authoritative list lives in resilience.
_ORDER_ENDPOINTS = resilience.ORDER_ENDPOINTS


class BitflyerError(Exception):
    """API returned an error response (4xx/5xx with a definite answer)."""

    def __init__(self, status_code: int, message: str,
                 failure: Failure | None = None):
        self.status_code = status_code
        # The resilience classification that produced this error, so callers
        # (main's API-error counter) can tell "the venue is slow" from "the
        # venue gave us a definite no".
        self.failure = failure
        super().__init__(f"bitFlyer API error {status_code}: {message}")


class NetworkError(Exception):
    """Transport-level failure on a read-only endpoint (safe to retry)."""

    def __init__(self, message: str, failure: Failure | None = None):
        self.failure = failure
        super().__init__(message)


class OrderStateUnknown(Exception):
    """An order-mutating request failed in a way where the server may or may not
    have processed it. Caller MUST reconcile via getchildorders before resending."""


class _Classified(Exception):
    """Internal carrier: a failed attempt plus its resilience classification."""

    def __init__(self, failure: Failure, detail: str):
        self.failure = failure
        self.detail = detail
        super().__init__(detail)


class RateLimiter:
    """Simple sliding-window limiter."""

    def __init__(self, max_calls: int, period_sec: float, clock=time.monotonic, sleep=time.sleep):
        self.max_calls = max_calls
        self.period = period_sec
        self._calls: list[float] = []
        self._clock = clock
        self._sleep = sleep

    def acquire(self) -> None:
        now = self._clock()
        self._calls = [t for t in self._calls if now - t < self.period]
        if len(self._calls) >= self.max_calls:
            wait = self.period - (now - self._calls[0])
            if wait > 0:
                self._sleep(wait)
        self._calls.append(self._clock())


def _adapter_retry_total(adapter) -> int:
    """Retries urllib3 would do UNDER us, or 0 when the adapter has none."""
    retries = getattr(adapter, "max_retries", None)
    if retries is None:
        return 0
    total = getattr(retries, "total", retries)
    try:
        return int(total or 0)
    except (TypeError, ValueError):      # pragma: no cover - defensive
        return 0


def _with_no_transport_retries(session):
    """THE retry decision belongs to `resilience.may_retry`, once, per attempt.

    urllib3's own adapter-level retries are invisible here: they would repeat a
    POST /v1/me/sendchildorder inside a single `session.request` call, before
    any of the taxonomy in bot.exchange.resilience ever runs. requests defaults
    to 0, but a caller handing in a tuned Session can silently arm it, so this
    pins our own session to 0 and REFUSES a supplied one that has retries armed
    rather than trading with a duplicate-order path underneath us.
    """
    adapters = getattr(session, "adapters", None)
    if not adapters:                      # test doubles have no adapter mapping
        return session
    for prefix, adapter in list(adapters.items()):
        armed = _adapter_retry_total(adapter)
        if armed:
            raise ValueError(
                f"session adapter for {prefix} has max_retries={armed}; the "
                "client must be the only thing that repeats a request "
                "(bot.exchange.resilience.may_retry). Mount it with "
                "max_retries=0."
            )
        try:
            adapter.max_retries = requests.adapters.Retry(0, read=False)
        except Exception:                 # pragma: no cover - exotic adapter
            pass
    return session


class BitflyerClient:
    def __init__(
        self,
        api_key: Secret | None = None,
        api_secret: Secret | None = None,
        session: requests.Session | None = None,
        base_url: str = BASE_URL,
        timeout: float = 10.0,
        max_retries: int = 3,
        sleep=time.sleep,
        clock=time.time,
        timeouts: Timeouts | None = None,
        retry_policy: RetryPolicy | None = None,
        observer: ApiObserver | None = None,
        perf=time.monotonic,
        rand=None,
    ):
        self._api_key = api_key or Secret("")
        self._api_secret = api_secret or Secret("")
        self._session = _with_no_transport_retries(session or requests.Session())
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._sleep = sleep
        self._clock = clock
        self._perf = perf
        self._rand = rand or random.random
        # `timeout` stays the read timeout so existing callers keep their
        # behavior; the connect timeout is the new, tighter half.
        self._base_timeouts = timeouts or Timeouts(connect_sec=min(3.0, timeout),
                                                   read_sec=timeout)
        self._timeouts = self._base_timeouts
        # The condition the TRADING timeouts are currently derived from. Kept
        # so a diagnostic window can restore the timeouts that apply NOW rather
        # than the ones that applied when it opened (see `diagnostic_call`).
        self._condition = ExchangeCondition.NORMAL
        self._diagnostic_depth = 0
        self._retry_policy = retry_policy or RetryPolicy(max_tries=max_retries)
        self._observer = observer
        # Published limits: private 500/5min, public 500/5min per IP. Stay well below.
        self._private_limiter = RateLimiter(300, 300.0)
        self._public_limiter = RateLimiter(300, 300.0)

    # ---- resilience wiring -------------------------------------------------
    def attach_observer(self, observer: ApiObserver | None) -> None:
        """Route per-call latency/outcome telemetry somewhere. Optional: the
        client works identically with no observer attached."""
        self._observer = observer

    @property
    def timeouts(self) -> Timeouts:
        return self._timeouts

    def configure(self, *, timeouts: Timeouts | None = None,
                  retry_policy: RetryPolicy | None = None) -> None:
        """Apply the operator's configured base timeouts / retry budget."""
        if timeouts is not None:
            self._base_timeouts = timeouts
            self._apply_trading_timeouts()
        if retry_policy is not None:
            self._retry_policy = retry_policy

    @contextmanager
    def diagnostic_call(self, timeouts: Timeouts = DIAGNOSTIC_TIMEOUTS):
        """Run read-only DIAGNOSTICS on short, fixed, single-attempt I/O.

        Reconciliation polls and the /v1/gethealth poll must not inherit the
        widened trading timeouts: at CRITICAL the read timeout is 30s, so one
        poll could consume the whole 15s reconciliation budget, and the health
        poll — which sits on the trading loop's hot path — could stall a step
        for longer than the market-data staleness watchdog allows. The retry
        policy is pinned to a single attempt too: the reconciler runs its own
        poll schedule, so a per-call retry would just eat its budget twice.

        Single-threaded by construction (the bot runs one loop); nested use
        restores the previous values on exit.

        On the way out the TRADING timeouts are re-derived from the condition
        that holds NOW, not blindly restored to the pair captured on the way in.
        A reconciliation window can be open for the whole reconciliation budget,
        and an `apply_condition` inside it — the venue going CRITICAL while we
        poll, which is precisely when it happens — used to be discarded on exit,
        leaving the next trading call on the pre-degradation read timeout.
        """
        previous_timeouts, previous_policy = self._timeouts, self._retry_policy
        self._diagnostic_depth += 1
        self._timeouts = timeouts
        self._retry_policy = RetryPolicy(max_tries=1, total_budget_sec=0.0)
        try:
            yield self
        finally:
            self._diagnostic_depth -= 1
            self._retry_policy = previous_policy
            if self._diagnostic_depth > 0:
                self._timeouts = previous_timeouts   # still inside an outer window
            else:
                self._apply_trading_timeouts()

    def apply_condition(self, condition: ExchangeCondition) -> Timeouts:
        """Widen the READ timeout while the venue is degraded, always relative
        to the configured base (so recovery restores it exactly).

        Inside a diagnostic window the condition is RECORDED but the short
        fixed timeouts stay in force; the window applies it when it closes."""
        self._condition = condition
        return self._apply_trading_timeouts()

    def _apply_trading_timeouts(self) -> Timeouts:
        """The trading timeouts implied by the base config + current condition."""
        trading = self._base_timeouts.for_condition(self._condition)
        if self._diagnostic_depth == 0:
            self._timeouts = trading
        return trading

    # ---- public endpoints -------------------------------------------------
    def markets(self) -> list[dict]:
        return self._request("GET", "/v1/markets")

    def ticker(self, product_code: str) -> dict:
        return self._request("GET", "/v1/ticker", params={"product_code": product_code})

    def board(self, product_code: str) -> dict:
        return self._request("GET", "/v1/board", params={"product_code": product_code})

    def executions(self, product_code: str, count: int = 100, before: int | None = None) -> list[dict]:
        params: dict[str, Any] = {"product_code": product_code, "count": count}
        if before is not None:
            params["before"] = before
        return self._request("GET", "/v1/executions", params=params)

    def health(self, product_code: str) -> dict:
        return self._request("GET", "/v1/gethealth", params={"product_code": product_code})

    def funding_rate(self, product_code: str) -> dict:
        """bitFlyer Crypto CFD funding rate (successor to Lightning FX SFD):
        next scheduled transfer ratio, settled every 8 hours."""
        return self._request("GET", "/v1/getfundingrate",
                             params={"product_code": product_code})

    def funding_rate_history(self, product_code: str, count: int = 30) -> list[dict]:
        return self._request("GET", "/v1/getfundingratehistory",
                             params={"product_code": product_code, "count": count})

    # ---- private read endpoints ------------------------------------------
    def get_balance(self) -> list[dict]:
        return self._request("GET", "/v1/me/getbalance", auth=True)

    def get_collateral(self) -> dict:
        return self._request("GET", "/v1/me/getcollateral", auth=True)

    def get_positions(self, product_code: str) -> list[dict]:
        return self._request("GET", "/v1/me/getpositions", params={"product_code": product_code}, auth=True)

    def get_child_orders(self, product_code: str, child_order_state: str | None = None,
                         child_order_acceptance_id: str | None = None) -> list[dict]:
        params: dict[str, Any] = {"product_code": product_code}
        if child_order_state:
            params["child_order_state"] = child_order_state
        if child_order_acceptance_id:
            params["child_order_acceptance_id"] = child_order_acceptance_id
        return self._request("GET", "/v1/me/getchildorders", params=params, auth=True)

    def get_executions_private(self, product_code: str,
                               child_order_acceptance_id: str | None = None) -> list[dict]:
        params: dict[str, Any] = {"product_code": product_code}
        if child_order_acceptance_id:
            params["child_order_acceptance_id"] = child_order_acceptance_id
        return self._request("GET", "/v1/me/getexecutions", params=params, auth=True)

    def get_permissions(self) -> list[str]:
        return self._request("GET", "/v1/me/getpermissions", auth=True)

    # ---- private write endpoints (LIVE mode only; caller-gated) ----------
    def send_child_order(self, *, product_code: str, side: str, size: float,
                         child_order_type: str = "MARKET", price: float | None = None,
                         minute_to_expire: int = 60, time_in_force: str = "GTC") -> dict:
        body: dict[str, Any] = {
            "product_code": product_code,
            "child_order_type": child_order_type,
            "side": side,
            "size": size,
            "minute_to_expire": minute_to_expire,
            "time_in_force": time_in_force,
        }
        if child_order_type == "LIMIT":
            if price is None:
                raise ValueError("LIMIT order requires price")
            body["price"] = price
        return self._request("POST", "/v1/me/sendchildorder", body=body, auth=True)

    def cancel_child_order(self, *, product_code: str, child_order_acceptance_id: str) -> None:
        self._request("POST", "/v1/me/cancelchildorder", body={
            "product_code": product_code,
            "child_order_acceptance_id": child_order_acceptance_id,
        }, auth=True)

    # ---- core -------------------------------------------------------------
    def _sign(self, timestamp: str, method: str, path: str, body: str) -> str:
        text = timestamp + method + path + body
        return hmac.new(
            self._api_secret.reveal().encode(), text.encode(), hashlib.sha256
        ).hexdigest()

    def _request(self, method: str, path: str, *, params: dict | None = None,
                 body: dict | None = None, auth: bool = False) -> Any:
        """Attempt loop. The ONLY place a request is repeated.

        `resilience.may_retry` is the single gate: SAFE_RETRY only, and on an
        ORDER endpoint only when the failure is provably PRE_SEND. AMBIGUOUS
        leaves here immediately as OrderStateUnknown — no second attempt, ever.
        """
        endpoint_class = resilience.endpoint_class_of(path)
        is_order_endpoint = endpoint_class is EndpointClass.ORDER
        started = self._perf()
        attempt = 0
        while True:
            try:
                return self._request_once(method, path, params=params, body=body,
                                          auth=auth, endpoint_class=endpoint_class)
            except _Classified as c:
                failure = c.failure
                if failure.failure_class is FailureClass.AMBIGUOUS:
                    raise OrderStateUnknown(
                        f"{c.detail}; order state must be reconciled before any resend"
                    ) from None
                elapsed = self._perf() - started
                if (resilience.may_retry(failure, endpoint_class)
                        and self._retry_policy.allows(attempt, elapsed)):
                    self._sleep(self._retry_policy.delay_for(
                        attempt, retry_after_sec=failure.retry_after_sec,
                        rand=self._rand))
                    attempt += 1
                    continue
                if is_order_endpoint and failure.phase is Phase.PRE_SEND \
                        and failure.failure_class is FailureClass.SAFE_RETRY:
                    # Every attempt failed before the body left us, so the order
                    # was almost certainly never placed — but "almost" is not
                    # the standard for a resend. Hand it to reconciliation.
                    raise OrderStateUnknown(
                        f"{c.detail}; order endpoint unreachable after "
                        f"{attempt + 1} attempt(s), state must be reconciled"
                    ) from None
                if failure.status_code is not None:
                    raise BitflyerError(failure.status_code, c.detail, failure)
                raise NetworkError(c.detail, failure) from None

    def _request_once(self, method: str, path: str, *, params: dict | None,
                      body: dict | None, auth: bool,
                      endpoint_class: EndpointClass | None = None) -> Any:
        endpoint_class = endpoint_class or resilience.endpoint_class_of(path)
        (self._private_limiter if auth else self._public_limiter).acquire()
        url = self._base_url + path
        body_str = json.dumps(body) if body is not None else ""
        headers = {"Content-Type": "application/json"}
        if auth:
            if not self._api_key or not self._api_secret:
                raise BitflyerError(401, "API credentials not configured")
            # Query string is part of the signed request path per the docs.
            qs = ""
            if params:
                qs = "?" + "&".join(f"{k}={v}" for k, v in params.items())
            timestamp = str(int(self._clock() * 1000))
            headers.update({
                "ACCESS-KEY": self._api_key.reveal(),
                "ACCESS-TIMESTAMP": timestamp,
                "ACCESS-SIGN": self._sign(timestamp, method, path + qs, body_str),
            })
        call_started = self._perf()
        try:
            resp = self._session.request(
                method, url, params=params, data=body_str if body is not None else None,
                headers=headers, timeout=self._timeouts.as_tuple(),
            )
        except requests.exceptions.RequestException as e:
            failure = resilience.classify_exception(e, endpoint_class)
            self._observe(endpoint_class, path, call_started, failure)
            # Never include headers/secrets in the raised message.
            raise _Classified(failure, f"{method} {path}: {type(e).__name__}") from None
        if resp.status_code >= 400:
            detail = ""
            try:
                detail = str(resp.json().get("error_message", ""))[:200]
            except Exception:
                detail = resp.text[:200]
            failure = resilience.classify_status(
                resp.status_code, endpoint_class,
                retry_after_sec=resilience.retry_after_of(resp))
            self._observe(endpoint_class, path, call_started, failure)
            raise _Classified(failure, detail)   # type: ignore[arg-type]
        payload, failure = self._parse_body(resp, path, endpoint_class)
        if failure is not None:
            # Telemetry is recorded AFTER the parse, so a 200 carrying a
            # maintenance page is logged as what it is (ambiguous), not as ok.
            self._observe(endpoint_class, path, call_started, failure)
            raise _Classified(failure, f"{method} {path}: 200 {failure.reason}")
        self._observe(endpoint_class, path, call_started, None)
        return payload

    def _parse_body(self, resp, path: str,
                    endpoint_class: EndpointClass) -> tuple[Any, Failure | None]:
        """Read a 2xx body INSIDE the classification boundary.

        A 200 is not an acceptance on its own: the body has to be the answer
        the endpoint promised. When it is not — a JSON decode error, an empty
        body where an acceptance id was due, an object without one — this is a
        classified failure (`resilience.classify_body`), which on an order
        endpoint means AMBIGUOUS -> OrderStateUnknown. Before, `resp.json()`
        raised a bare ValueError here, the order manager caught it in its
        `except (BitflyerError, ValueError)` branch and closed the record
        REJECTED — and the next signal sent a second real order.
        """
        text = getattr(resp, "text", "") or ""
        payload = None
        if text != "":
            try:
                payload = resp.json()
            except (ValueError, TypeError):
                return None, resilience.classify_body("unparseable_body",
                                                      endpoint_class)
        problem = resilience.body_shape_problem(path, payload, text)
        if problem is not None:
            return None, resilience.classify_body(problem, endpoint_class)
        return payload, None

    def _observe(self, endpoint_class: EndpointClass, path: str,
                 started: float, failure: Failure | None) -> None:
        """Best-effort telemetry. A broken observer must never surface here."""
        if self._observer is None:
            return
        try:
            self._observer.on_call(
                endpoint_class=endpoint_class, endpoint=path,
                latency_ms=(self._perf() - started) * 1000.0, failure=failure)
        except Exception:      # pragma: no cover - defensive
            pass

"""Transport-failure taxonomy, retry policy and exchange-condition monitor.

The 2019 failure this module exists for was not a wrong signal: bitFlyer
degrades exactly when the market moves, orders delayed or failed, and the
position could not be exited (docs/legacy/matilda_v52.py header — "こういう時
はbfめっちゃ重くなって中々注文が通らなくて思いのほか損する可能性がある").
So the bot must keep getting requests through under that load WITHOUT ever
weakening the invariant that protects it from the opposite failure: a
duplicated real order.

Taxonomy (`classify_exception` / `classify_status`)
---------------------------------------------------
SAFE_RETRY  the transport failed BEFORE the request body left this process
            (DNS, connection refused, connect timeout, TLS handshake), or the
            exchange gave an availability answer (429 / 5xx) on a read-only,
            idempotent endpoint.
AMBIGUOUS   the request may have reached order placement — read timeout,
            connection reset after send, or any 5xx on an ORDER endpoint. On
            order endpoints this becomes `OrderStateUnknown` and is NEVER
            retried (CLAUDE.md §1).
REJECTED    the exchange gave a definite business answer (4xx). No retry; the
            reason is surfaced to the caller.

Classification and applicability are deliberately SEPARATE decisions
(`may_retry`): a 429 classifies SAFE_RETRY everywhere, but on an order
endpoint only a PRE_SEND failure is ever retried, because only a pre-send
failure proves the order was not placed. "When in doubt on an order endpoint"
resolves to AMBIGUOUS, never to a resend.

Condition monitor
-----------------
`ConditionMonitor` folds three signals — the product's /v1/gethealth status,
an EWMA of the latency of the bot's OWN calls, and a rolling error rate — into
NORMAL / DEGRADED / CRITICAL. Escalation is immediate; de-escalation needs
several consecutive calmer assessments AND a minimum dwell time, so the level
cannot flap between two ticks. Only *availability* failures (transport, 429,
5xx) count towards the error rate: a 404 or a business 4xx says nothing about
whether bitFlyer is under load.

The behavior wiring (widen read timeouts, halve/suppress NEW entries, never
gate a CLOSING order) lives in bot/main.py, which is where the position is.
"""
from __future__ import annotations

import logging
import random
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import requests

logger = logging.getLogger("bot.resilience")

# Endpoints that mutate order state. An ambiguous failure on one of these is
# the STATE_UNKNOWN case and must never be auto-retried.
ORDER_ENDPOINTS = (
    "/v1/me/sendchildorder",
    "/v1/me/cancelchildorder",
    "/v1/me/cancelallchildorders",
    "/v1/me/sendparentorder",
    "/v1/me/cancelparentorder",
)


class EndpointClass(Enum):
    PUBLIC = "public"
    PRIVATE_READ = "private_read"
    ORDER = "order"


class FailureClass(Enum):
    SAFE_RETRY = "safe_retry"
    AMBIGUOUS = "ambiguous"
    REJECTED = "rejected"


class Phase(Enum):
    """Where the failure happened relative to the request body leaving us."""
    PRE_SEND = "pre_send"      # provably nothing reached the exchange
    POST_SEND = "post_send"    # the body may have been processed
    RESPONSE = "response"      # a complete HTTP response came back


def endpoint_class_of(path: str) -> EndpointClass:
    if path in ORDER_ENDPOINTS:
        return EndpointClass.ORDER
    if path.startswith("/v1/me/"):
        return EndpointClass.PRIVATE_READ
    return EndpointClass.PUBLIC


@dataclass(frozen=True)
class Failure:
    failure_class: FailureClass
    phase: Phase
    reason: str                       # exception type name or HTTP status; never a secret
    status_code: int | None = None
    retry_after_sec: float | None = None

    @property
    def counts_as_unavailable(self) -> bool:
        """True when this failure says something about the EXCHANGE's health.

        A business 4xx (bad parameter, insufficient funds, 404) does not — it
        would otherwise drive the condition monitor to DEGRADED on our own
        malformed request.
        """
        if self.failure_class is FailureClass.REJECTED:
            return self.status_code == 429
        return True


# --- exception classification ------------------------------------------------
# Only these prove the request body never left this process. Everything else on
# an order endpoint is AMBIGUOUS by construction.
_STRICT_PRE_SEND_TYPES = (
    requests.exceptions.ConnectTimeout,
    requests.exceptions.ProxyError,
)
_PRE_SEND_MARKERS = (
    "NewConnectionError",
    "NameResolutionError",
    "Failed to establish a new connection",
    "Connection refused",
    "Name or service not known",
    "Temporary failure in name resolution",
    "getaddrinfo failed",
    "nodename nor servname provided",
)
# A TLS failure at handshake time is pre-send; an SSL error raised mid-stream
# is not, so the markers have to be present before we call it provable.
_HANDSHAKE_MARKERS = (
    "handshake",
    "certificate verify failed",
    "CERTIFICATE_VERIFY_FAILED",
    "SSLCertVerificationError",
    "WRONG_VERSION_NUMBER",
    "UNKNOWN_PROTOCOL",
    "sslv3",
    "tlsv1",
)
# Our own bug (bad URL/schema): retrying cannot help and nothing was sent.
_DEFINITE_CLIENT_TYPES = (
    requests.exceptions.MissingSchema,
    requests.exceptions.InvalidSchema,
    requests.exceptions.InvalidURL,
    requests.exceptions.URLRequired,
)


def _has_marker(exc: BaseException, markers: tuple[str, ...]) -> bool:
    text = f"{exc!r}"
    return any(m in text for m in markers)


def _is_pre_send(exc: BaseException) -> bool:
    if isinstance(exc, _STRICT_PRE_SEND_TYPES):
        return True
    if isinstance(exc, requests.exceptions.SSLError):
        return _has_marker(exc, _HANDSHAKE_MARKERS)
    if isinstance(exc, requests.exceptions.ConnectionError):
        return _has_marker(exc, _PRE_SEND_MARKERS)
    return False


def classify_exception(exc: BaseException,
                       endpoint_class: EndpointClass) -> Failure:
    """Classify a transport failure. `exc` is never stored, only its type name:
    request bodies and headers (and therefore secrets) must not leak."""
    name = type(exc).__name__
    if isinstance(exc, _DEFINITE_CLIENT_TYPES):
        return Failure(FailureClass.REJECTED, Phase.PRE_SEND, name)
    if _is_pre_send(exc):
        return Failure(FailureClass.SAFE_RETRY, Phase.PRE_SEND, name)
    if endpoint_class is EndpointClass.ORDER:
        # Read timeout, reset after send, anything unrecognised: the exchange
        # may already hold the order. This is the STATE_UNKNOWN path.
        return Failure(FailureClass.AMBIGUOUS, Phase.POST_SEND, name)
    # Read-only endpoints are idempotent, so a post-send failure is still safe
    # to repeat.
    return Failure(FailureClass.SAFE_RETRY, Phase.POST_SEND, name)


def classify_status(status_code: int, endpoint_class: EndpointClass, *,
                    retry_after_sec: float | None = None) -> Failure | None:
    """Classify an HTTP response. None means "not a failure"."""
    if status_code < 400:
        return None
    if status_code == 429:
        # Rate limited. The edge refuses the call; on read endpoints backing off
        # and repeating is exactly right. On order endpoints `may_retry` still
        # refuses (RESPONSE phase), so this surfaces as a definite error.
        return Failure(FailureClass.SAFE_RETRY, Phase.RESPONSE, "429",
                       status_code=429, retry_after_sec=retry_after_sec)
    if status_code >= 500:
        if endpoint_class is EndpointClass.ORDER:
            # The body was sent and the exchange failed while holding it. We
            # cannot prove it never reached placement -> ambiguous.
            return Failure(FailureClass.AMBIGUOUS, Phase.POST_SEND,
                           str(status_code), status_code=status_code)
        return Failure(FailureClass.SAFE_RETRY, Phase.RESPONSE, str(status_code),
                       status_code=status_code, retry_after_sec=retry_after_sec)
    return Failure(FailureClass.REJECTED, Phase.RESPONSE, str(status_code),
                   status_code=status_code)


def may_retry(failure: Failure, endpoint_class: EndpointClass) -> bool:
    """THE invariant, in one place.

    Retries are allowed only for SAFE_RETRY, and on order endpoints only when
    the failure is provably PRE_SEND. AMBIGUOUS never retries anywhere.
    """
    if failure.failure_class is not FailureClass.SAFE_RETRY:
        return False
    if endpoint_class is EndpointClass.ORDER:
        return failure.phase is Phase.PRE_SEND
    return True


def retry_after_of(resp) -> float | None:
    """Seconds from a Retry-After header, if the exchange sent one."""
    headers = getattr(resp, "headers", None) or {}
    try:
        raw = headers.get("Retry-After")
    except AttributeError:
        return None
    if raw is None:
        return None
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class RetryPolicy:
    """Exponential backoff with FULL jitter and a per-call budget.

    Full jitter (uniform in [0, cap]) rather than plain exponential: under a
    storm every bot on the venue retries on the same schedule, and synchronised
    retries are what turns "busy" into "down".
    """
    max_tries: int = 3
    total_budget_sec: float = 10.0
    base_delay_sec: float = 0.25
    max_delay_sec: float = 4.0

    def allows(self, attempt: int, elapsed_sec: float) -> bool:
        """`attempt` is 0-based and counts tries ALREADY made minus one."""
        return (attempt + 1) < self.max_tries and elapsed_sec < self.total_budget_sec

    def delay_for(self, attempt: int, *, retry_after_sec: float | None = None,
                  rand=random.random) -> float:
        if retry_after_sec is not None:
            # Honour the venue's own signal, but never sleep unboundedly inside
            # a trading loop.
            return min(retry_after_sec, self.max_delay_sec)
        cap = min(self.max_delay_sec, self.base_delay_sec * (2 ** attempt))
        return rand() * cap


class ExchangeCondition(Enum):
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"

    @property
    def rank(self) -> int:
        return {"NORMAL": 0, "DEGRADED": 1, "CRITICAL": 2}[self.value]


@dataclass(frozen=True)
class Timeouts:
    """Split timeouts. The connect timeout stays tight even when the venue is
    slow — a connection that will not establish in 3s is not going to carry a
    useful order — while the READ timeout is what widens, because a degraded
    bitFlyer answers late rather than not at all."""
    connect_sec: float = 3.0
    read_sec: float = 10.0
    max_read_sec: float = 60.0

    def as_tuple(self) -> tuple[float, float]:
        return (self.connect_sec, self.read_sec)

    def widened(self, factor: float) -> "Timeouts":
        return Timeouts(self.connect_sec,
                        min(self.read_sec * factor, self.max_read_sec),
                        self.max_read_sec)

    def for_condition(self, condition: ExchangeCondition) -> "Timeouts":
        if condition is ExchangeCondition.CRITICAL:
            return self.widened(3.0)
        if condition is ExchangeCondition.DEGRADED:
            return self.widened(2.0)
        return self


# bitFlyer /v1/gethealth status strings, worst last.
HEALTH_LEVEL = {
    "NORMAL": 0,
    "BUSY": 1,
    "VERY BUSY": 2,
    "SUPER BUSY": 3,
    "NO ORDER": 3,
    "STOP": 4,
}
HEALTH_STOPPED = ("STOP",)


class ConditionMonitor:
    """NORMAL / DEGRADED / CRITICAL over health + latency EWMA + error rate."""

    def __init__(self, *, window_sec: float = 900.0, alpha: float = 0.2,
                 degraded_latency_ms: float = 1200.0,
                 critical_latency_ms: float = 3000.0,
                 degraded_error_rate: float = 0.2,
                 critical_error_rate: float = 0.5,
                 min_samples: int = 5, recovery_samples: int = 3,
                 min_dwell_sec: float = 30.0, clock=time.time):
        self.window_sec = window_sec
        self.alpha = alpha
        self.degraded_latency_ms = degraded_latency_ms
        self.critical_latency_ms = critical_latency_ms
        self.degraded_error_rate = degraded_error_rate
        self.critical_error_rate = critical_error_rate
        self.min_samples = min_samples
        self.recovery_samples = recovery_samples
        self.min_dwell_sec = min_dwell_sec
        self._clock = clock
        self._ewma_ms: float | None = None
        self._events: deque[tuple[float, bool]] = deque()   # (ts, unavailable)
        self._health: str | None = None
        self._condition = ExchangeCondition.NORMAL
        self._changed_at = clock()
        self._pending: ExchangeCondition | None = None
        self._pending_count = 0

    # ---- inputs ----------------------------------------------------------
    def observe(self, latency_ms: float, *, unavailable: bool = False,
                ts: float | None = None) -> ExchangeCondition:
        now = ts if ts is not None else self._clock()
        if latency_ms >= 0:
            self._ewma_ms = (latency_ms if self._ewma_ms is None
                             else self.alpha * latency_ms + (1 - self.alpha) * self._ewma_ms)
        self._events.append((now, unavailable))
        self._trim(now)
        return self._reassess(now)

    def observe_health(self, status: str | None,
                       ts: float | None = None) -> ExchangeCondition:
        if status is not None:
            self._health = str(status).upper()
        return self._reassess(ts if ts is not None else self._clock())

    # ---- outputs ---------------------------------------------------------
    @property
    def condition(self) -> ExchangeCondition:
        return self._condition

    @property
    def health(self) -> str | None:
        return self._health

    @property
    def exchange_stopped(self) -> bool:
        return self._health in HEALTH_STOPPED

    @property
    def ewma_latency_ms(self) -> float | None:
        return self._ewma_ms

    @property
    def error_rate(self) -> float:
        if not self._events:
            return 0.0
        bad = sum(1 for _, unavailable in self._events if unavailable)
        return bad / len(self._events)

    def snapshot(self) -> dict:
        return {
            "condition": self._condition.value,
            "health": self._health,
            "latency_ms": (round(self._ewma_ms, 1)
                           if self._ewma_ms is not None else None),
            "error_rate": round(self.error_rate, 4),
            "samples": len(self._events),
        }

    # ---- internals -------------------------------------------------------
    def _trim(self, now: float) -> None:
        cutoff = now - self.window_sec
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()

    def _raw_level(self) -> ExchangeCondition:
        health_rank = HEALTH_LEVEL.get(self._health or "", 0)
        level = ExchangeCondition.NORMAL
        if health_rank >= 3:
            level = ExchangeCondition.CRITICAL
        elif health_rank >= 1:
            level = ExchangeCondition.DEGRADED
        rate = self.error_rate
        samples = len(self._events)
        if samples >= self.min_samples:
            if rate >= self.critical_error_rate:
                level = ExchangeCondition.CRITICAL
            elif rate >= self.degraded_error_rate and level.rank < 1:
                level = ExchangeCondition.DEGRADED
            if self._ewma_ms is not None:
                if self._ewma_ms >= self.critical_latency_ms:
                    level = ExchangeCondition.CRITICAL
                elif self._ewma_ms >= self.degraded_latency_ms and level.rank < 1:
                    level = ExchangeCondition.DEGRADED
        return level

    def _reassess(self, now: float) -> ExchangeCondition:
        raw = self._raw_level()
        if raw.rank > self._condition.rank:
            # Escalate at once: being late to notice degradation is the
            # expensive direction.
            self._set(raw, now)
            return self._condition
        if raw is self._condition:
            self._pending = None
            self._pending_count = 0
            return self._condition
        # Calmer than the current level: require it to hold.
        if self._pending is raw:
            self._pending_count += 1
        else:
            self._pending = raw
            self._pending_count = 1
        if (self._pending_count >= self.recovery_samples
                and now - self._changed_at >= self.min_dwell_sec):
            self._set(raw, now)
        return self._condition

    def _set(self, condition: ExchangeCondition, now: float) -> None:
        self._condition = condition
        self._changed_at = now
        self._pending = None
        self._pending_count = 0


class ApiHealthRecorder:
    """Append one line per API call to data/api_health.csv.

    Best effort in the strongest sense: every failure mode (unwritable path,
    full disk, a locked file on Windows) is swallowed. Telemetry must never
    reach the trading path — tests assert exactly that.
    """

    HEADER = "ts,endpoint_class,endpoint,latency_ms,outcome,condition,health\n"

    def __init__(self, path: str | Path = "data/api_health.csv",
                 max_bytes: int = 4_000_000, check_every: int = 200):
        self._path = Path(path)
        self._max_bytes = max_bytes
        self._check_every = max(1, check_every)
        self._writes = 0
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            if not self._path.exists():
                self._path.write_text(self.HEADER, encoding="utf-8")
        except OSError:
            pass

    def record(self, *, ts: float, endpoint_class: str, endpoint: str,
               latency_ms: float, outcome: str, condition: str,
               health: str | None) -> None:
        line = (f"{ts:.3f},{endpoint_class},{endpoint},{latency_ms:.1f},"
                f"{outcome},{condition},{health or ''}\n")
        try:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(line)
        except OSError:
            return
        self._writes += 1
        if self._writes % self._check_every == 0:
            self._rotate_if_large()

    def _rotate_if_large(self) -> None:
        try:
            if self._path.stat().st_size < self._max_bytes:
                return
            backup = self._path.with_suffix(self._path.suffix + ".1")
            backup.unlink(missing_ok=True)
            self._path.rename(backup)
            self._path.write_text(self.HEADER, encoding="utf-8")
        except OSError:
            pass


class ApiObserver:
    """Glue handed to BitflyerClient: every call lands in the condition monitor
    and (best effort) in the telemetry file. Never raises into the request
    path — a broken observer must not stop the bot from trading."""

    def __init__(self, monitor: ConditionMonitor,
                 recorder: ApiHealthRecorder | None = None,
                 clock=time.time):
        self.monitor = monitor
        self.recorder = recorder
        self._clock = clock
        self._warned = False

    def on_call(self, *, endpoint_class: EndpointClass, endpoint: str,
                latency_ms: float, failure: Failure | None) -> None:
        try:
            unavailable = failure is not None and failure.counts_as_unavailable
            self.monitor.observe(latency_ms, unavailable=unavailable)
            if self.recorder is not None:
                outcome = "ok" if failure is None else failure.failure_class.value
                self.recorder.record(
                    ts=self._clock(), endpoint_class=endpoint_class.value,
                    endpoint=endpoint, latency_ms=latency_ms, outcome=outcome,
                    condition=self.monitor.condition.value,
                    health=self.monitor.health,
                )
        except Exception:      # pragma: no cover - defensive
            if not self._warned:
                self._warned = True
                logger.exception("api telemetry failed; trading continues")

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
SAFE_RETRY  the transport failed PROVABLY before the request body left this
            process (connect timeout, or a connection error whose text names
            the new-connection failure explicitly), or the exchange gave an
            availability answer (429 / 5xx) on a read-only, idempotent
            endpoint.
AMBIGUOUS   the request may have reached order placement — read timeout,
            connection reset after send, or any 5xx on an ORDER endpoint. On
            order endpoints this becomes `OrderStateUnknown` and is NEVER
            retried (CLAUDE.md §1).
REJECTED    the exchange gave a definite business answer (4xx). No retry; the
            reason is surfaced to the caller.

The RESPONSE BODY is inside this boundary too (`body_shape_problem` /
`classify_body`): a 200 whose body cannot be read as the answer the endpoint
promised — a maintenance HTML page, an empty body, a missing acceptance id — is
AMBIGUOUS on an order endpoint, not a success and not a rejection. Parsing it
outside the taxonomy raised a bare ValueError that the order manager read as
"the exchange said no" and closed the record REJECTED, which is exactly the
state from which the next signal sends a second real order.

Classification and applicability are deliberately SEPARATE decisions
(`may_retry`): a 429 classifies SAFE_RETRY everywhere, but on an order
endpoint only a PRE_SEND failure is ever retried, because only a pre-send
failure proves the order was not placed. "When in doubt on an order endpoint"
resolves to AMBIGUOUS, never to a resend.

The PRE_SEND whitelist is deliberately tiny, and two entries that used to be on
it were removed after they were shown to be reachable AFTER the body was sent:

- **TLS/SSL errors of every kind.** OpenSSL renders alerts in lowercase
  ("tlsv1 alert internal error", "sslv3 alert bad record mac") and a venue's
  load balancer can send one after it has read the request. There is no string
  that distinguishes a handshake alert from a mid-stream alert, so every
  SSLError on an order endpoint is AMBIGUOUS.
- **ProxyError.** urllib3 1.26 wraps any connection failure raised while a
  proxy is configured — including a reset that happened after the write — into
  ProxyError. (`pyproject.toml` pins urllib3>=2 for the same reason; the
  taxonomy no longer depends on that pin being honored.)

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
import math
import random
import time
from collections import deque
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
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


# Order endpoints whose 2xx body MUST carry an acceptance id. A 200 that does
# not is NOT a success: an edge in front of the venue can answer a maintenance
# page (or nothing at all) with status 200 while the request behind it did
# reach order placement, so such a send is ambiguous, not accepted.
ACCEPTANCE_ID_ENDPOINTS = (
    "/v1/me/sendchildorder",
    "/v1/me/sendparentorder",
)
ACCEPTANCE_ID_KEYS = (
    "child_order_acceptance_id",
    "parent_order_acceptance_id",
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
    # Where it happened. Carried so a caller that only sees the raised
    # exception (main's API-error counter) can still tell a public-feed
    # failure from a private one.
    endpoint_class: "EndpointClass | None" = None

    @property
    def counts_as_unavailable(self) -> bool:
        """True when this failure says something about the EXCHANGE's health.

        A business 4xx (bad parameter, insufficient funds, 404) does not — it
        would otherwise drive the condition monitor to DEGRADED on our own
        malformed request. A 429 is never REJECTED (`classify_status` returns
        SAFE_RETRY for it), so REJECTED is simply "our problem, not theirs".
        """
        return self.failure_class is not FailureClass.REJECTED


# --- exception classification ------------------------------------------------
# Only these prove the request body never left this process. Everything else on
# an order endpoint is AMBIGUOUS by construction.
#
# A connect timeout means the TCP/TLS connection for THIS attempt never
# completed, so no bytes of the request can have been written.
_STRICT_PRE_SEND_TYPES = (
    requests.exceptions.ConnectTimeout,
)
# Types that must NEVER be read as pre-send even though they subclass
# ConnectionError and could otherwise reach the marker test below. See the
# module docstring: both are reachable after the body was sent.
_NEVER_PRE_SEND_TYPES = (
    requests.exceptions.SSLError,
    requests.exceptions.ProxyError,
)
# Explicit new-connection markers, matched case-insensitively: urllib3 raises
# these only from the connect/DNS phase, before any request byte is written.
_PRE_SEND_MARKERS = (
    "failed to establish a new connection",
    "name or service not known",
    "nodename nor servname",
)
# Our own bug (bad URL/schema): retrying cannot help and nothing was sent.
_DEFINITE_CLIENT_TYPES = (
    requests.exceptions.MissingSchema,
    requests.exceptions.InvalidSchema,
    requests.exceptions.InvalidURL,
    requests.exceptions.URLRequired,
)


def _has_marker(exc: BaseException, markers: tuple[str, ...]) -> bool:
    text = f"{exc!r}".lower()
    return any(m in text for m in markers)


def _is_pre_send(exc: BaseException) -> bool:
    if isinstance(exc, _STRICT_PRE_SEND_TYPES):
        return True
    if isinstance(exc, _NEVER_PRE_SEND_TYPES):
        return False
    if isinstance(exc, requests.exceptions.ConnectionError):
        return _has_marker(exc, _PRE_SEND_MARKERS)
    return False


def classify_exception(exc: BaseException,
                       endpoint_class: EndpointClass) -> Failure:
    """Classify a transport failure. `exc` is never stored, only its type name:
    request bodies and headers (and therefore secrets) must not leak."""
    name = type(exc).__name__
    if isinstance(exc, _DEFINITE_CLIENT_TYPES):
        return Failure(FailureClass.REJECTED, Phase.PRE_SEND, name,
                       endpoint_class=endpoint_class)
    if _is_pre_send(exc):
        return Failure(FailureClass.SAFE_RETRY, Phase.PRE_SEND, name,
                       endpoint_class=endpoint_class)
    if endpoint_class is EndpointClass.ORDER:
        # Read timeout, reset after send, anything unrecognised: the exchange
        # may already hold the order. This is the STATE_UNKNOWN path.
        return Failure(FailureClass.AMBIGUOUS, Phase.POST_SEND, name,
                       endpoint_class=endpoint_class)
    # Read-only endpoints are idempotent, so a post-send failure is still safe
    # to repeat.
    return Failure(FailureClass.SAFE_RETRY, Phase.POST_SEND, name,
                   endpoint_class=endpoint_class)


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
                       status_code=429, retry_after_sec=retry_after_sec,
                       endpoint_class=endpoint_class)
    if status_code >= 500:
        if endpoint_class is EndpointClass.ORDER:
            # The body was sent and the exchange failed while holding it. We
            # cannot prove it never reached placement -> ambiguous.
            return Failure(FailureClass.AMBIGUOUS, Phase.POST_SEND,
                           str(status_code), status_code=status_code,
                           endpoint_class=endpoint_class)
        return Failure(FailureClass.SAFE_RETRY, Phase.RESPONSE, str(status_code),
                       status_code=status_code, retry_after_sec=retry_after_sec,
                       endpoint_class=endpoint_class)
    return Failure(FailureClass.REJECTED, Phase.RESPONSE, str(status_code),
                   status_code=status_code, endpoint_class=endpoint_class)


def body_shape_problem(path: str, payload, raw_text: str) -> str | None:
    """Does a 2xx body actually carry what the endpoint promised?

    Only the acceptance-id endpoints make a promise this can check: their
    answer is a JSON object with an acceptance id in it. `cancelchildorder`
    legitimately answers 200 with an EMPTY body, so an empty body is a problem
    for a send and normal for a cancel.

    None means "the body is what it should be". Anything else is a short,
    secret-free reason string.
    """
    if path not in ACCEPTANCE_ID_ENDPOINTS:
        return None
    if not (raw_text or "").strip():
        return "empty_body"
    if not isinstance(payload, dict):
        return "unexpected_body"
    if any(payload.get(key) for key in ACCEPTANCE_ID_KEYS):
        return None
    return "missing_acceptance_id"


def classify_body(problem: str, endpoint_class: EndpointClass) -> Failure:
    """Classify a 2xx whose BODY could not be read as the expected answer.

    This is part of the same classification boundary as the transport and the
    status code, and for the same reason: on an ORDER endpoint an unreadable
    200 does not prove the order was refused, so it is AMBIGUOUS and becomes
    OrderStateUnknown — never a ValueError escaping into the caller's "the
    exchange said no" branch, which would let the next signal resend.

    On a read-only endpoint the request is idempotent, so a garbled body is
    just a sample to take again.
    """
    if endpoint_class is EndpointClass.ORDER:
        return Failure(FailureClass.AMBIGUOUS, Phase.RESPONSE, problem,
                       endpoint_class=endpoint_class)
    return Failure(FailureClass.SAFE_RETRY, Phase.RESPONSE, problem,
                   endpoint_class=endpoint_class)


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


def retry_after_of(resp, *, now: float | None = None) -> float | None:
    """Seconds from a Retry-After header, if the exchange sent one.

    RFC 9110 allows both forms and edges in front of an exchange do send the
    HTTP-date one: `Retry-After: Wed, 21 Aug 2026 12:00:05 GMT`. Parsing only
    the delta-seconds form silently dropped that signal and fell back to our
    own jittered backoff.
    """
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
        pass
    try:
        when = parsedate_to_datetime(str(raw))
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    try:
        target = when.timestamp()
    except (OSError, OverflowError, ValueError):      # pragma: no cover
        return None
    return max(0.0, target - (time.time() if now is None else now))


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
        factor = condition_multiplier(condition)
        return self.widened(factor) if factor > 1.0 else self


def condition_multiplier(condition: ExchangeCondition) -> float:
    """How much slack the current condition buys. ONE definition, because more
    than one thing scales with it: the read timeout, and the market-data
    staleness threshold that would otherwise race a widened read (main.py)."""
    if condition is ExchangeCondition.CRITICAL:
        return 3.0
    if condition is ExchangeCondition.DEGRADED:
        return 2.0
    return 1.0


# Read-only DIAGNOSTICS (reconciliation polls, the /v1/gethealth poll) run on
# their own short, FIXED timeouts and never inherit the widened trading ones.
# The point of a diagnostic is to answer inside a bounded budget; a 30s read
# timeout inherited from CRITICAL would let one poll eat the whole budget.
DIAGNOSTIC_TIMEOUTS = Timeouts(connect_sec=3.0, read_sec=5.0, max_read_sec=5.0)


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
    """NORMAL / DEGRADED / CRITICAL over health + latency EWMA + error rate.

    The /v1/gethealth reading EXPIRES (`health_ttl_sec`, wired to 3x the poll
    interval). A health string that is never refreshed — the poll keeps failing,
    or the poll stopped being made at all — used to be immortal: one
    "SUPER BUSY" read could hold the bot at CRITICAL forever with nothing in
    the telemetry to say the reading was hours old. Once it expires it drops out
    of the vote entirely (the level then comes from latency and errors, which
    are facts this process measured itself) and is reported as
    `health=None` + `health_age_sec`.
    """

    def __init__(self, *, window_sec: float = 900.0, alpha: float = 0.2,
                 degraded_latency_ms: float = 1200.0,
                 critical_latency_ms: float = 3000.0,
                 degraded_error_rate: float = 0.2,
                 critical_error_rate: float = 0.5,
                 min_samples: int = 5, recovery_samples: int = 3,
                 min_dwell_sec: float = 30.0, health_ttl_sec: float = 90.0,
                 clock=time.time):
        self.window_sec = window_sec
        self.alpha = alpha
        self.degraded_latency_ms = degraded_latency_ms
        self.critical_latency_ms = critical_latency_ms
        self.degraded_error_rate = degraded_error_rate
        self.critical_error_rate = critical_error_rate
        self.min_samples = min_samples
        self.recovery_samples = recovery_samples
        self.min_dwell_sec = min_dwell_sec
        self.health_ttl_sec = health_ttl_sec
        self._clock = clock
        self._ewma_ms: float | None = None
        self._events: deque[tuple[float, bool]] = deque()   # (ts, unavailable)
        self._health: str | None = None
        self._health_at: float | None = None
        self._condition = ExchangeCondition.NORMAL
        self._changed_at = clock()
        self._calm_target: ExchangeCondition | None = None
        self._calm_count = 0

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
        now = ts if ts is not None else self._clock()
        if status is not None:
            self._health = str(status).upper()
            self._health_at = now
        return self._reassess(now)

    # ---- outputs ---------------------------------------------------------
    @property
    def condition(self) -> ExchangeCondition:
        return self._condition

    @property
    def health(self) -> str | None:
        """The venue's own status string, or None when it has gone stale."""
        return self._fresh_health(self._clock())

    @property
    def health_age_sec(self) -> float | None:
        if self._health_at is None:
            return None
        return max(0.0, self._clock() - self._health_at)

    @property
    def exchange_stopped(self) -> bool:
        """STOP is STICKY across staleness — deliberately unlike the vote.

        A stale reading drops out of `_raw_level` because "the venue was busy
        90s ago" says nothing about load now. "The venue was HALTED and we have
        not heard from it since" is a different fact: the poll that would have
        cleared it is exactly the call that is failing. Letting the TTL clear it
        would resume ENTRIES into a venue last known to be stopped, on no
        evidence at all. Only a FRESH non-STOP reading clears it (the next
        successful `observe_health` overwrites `_health`).

        The trade-off is bounded and one-sided: while it is sticky the bot
        refuses NEW entries only — closing orders never consult this
        (bot/main.py `_entry_allowed_under_condition`).
        """
        return self._health in HEALTH_STOPPED

    def _fresh_health(self, now: float) -> str | None:
        if self._health is None or self._health_at is None:
            return None
        if self.health_ttl_sec is not None and \
                now - self._health_at > self.health_ttl_sec:
            return None
        return self._health

    @property
    def ewma_latency_ms(self) -> float | None:
        return self._ewma_ms

    @property
    def error_rate(self) -> float:
        if not self._events:
            return 0.0
        bad = sum(1 for _, unavailable in self._events if unavailable)
        return bad / len(self._events)

    def snapshot(self, now: float | None = None) -> dict:
        now = self._clock() if now is None else now
        age = (None if self._health_at is None
               else round(max(0.0, now - self._health_at), 1))
        return {
            "condition": self._condition.value,
            "health": self._fresh_health(now),
            "health_age_sec": age,
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

    def _raw_level(self, now: float) -> ExchangeCondition:
        health_rank = HEALTH_LEVEL.get(self._fresh_health(now) or "", 0)
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
        raw = self._raw_level(now)
        if raw.rank > self._condition.rank:
            # Escalate at once: being late to notice degradation is the
            # expensive direction.
            self._set(raw, now)
            return self._condition
        if raw is self._condition:
            self._calm_target = None
            self._calm_count = 0
            return self._condition
        # Calmer than the current level. The streak counts consecutive samples
        # that are calmer than CURRENT — not consecutive samples of the SAME
        # calmer level, which deadlocked: /v1/gethealth flapping BUSY <-> NORMAL
        # for two hours never produced `recovery_samples` of one level, so a
        # monitor that had once seen SUPER BUSY stayed CRITICAL forever with
        # entries fully suppressed. The target is the WORST of the pending calm
        # samples, so the alternation above recovers to DEGRADED (which is what
        # BUSY means) rather than jumping to NORMAL.
        self._calm_count += 1
        if self._calm_target is None or raw.rank > self._calm_target.rank:
            self._calm_target = raw
        if (self._calm_count >= self.recovery_samples
                and now - self._changed_at >= self.min_dwell_sec):
            self._set(self._calm_target, now)
        return self._condition

    def _set(self, condition: ExchangeCondition, now: float) -> None:
        self._condition = condition
        self._changed_at = now
        self._calm_target = None
        self._calm_count = 0


@dataclass(frozen=True)
class ResilienceConfig:
    """Validated `resilience:` block from config/config.yaml.

    Every field is checked before it can reach a timeout or a threshold: a
    typo'd `read_timeout_sec: -10` used to be accepted verbatim and turned every
    request into an immediate failure, and `degraded_latency_ms` above
    `critical_latency_ms` made DEGRADED unreachable. Bad values fall back to the
    documented default and log a warning naming the field — never a silent
    substitution, and never a refusal to start (the bot must keep running the
    paper experiment).
    """
    connect_timeout_sec: float = 3.0
    read_timeout_sec: float = 10.0
    retry_max_tries: int = 3
    retry_budget_sec: float = 10.0
    health_poll_sec: float = 30.0
    reconcile_budget_sec: float = 15.0
    condition_window_sec: float = 900.0
    degraded_latency_ms: float = 1200.0
    critical_latency_ms: float = 3000.0
    api_health_csv: str = "data/api_health.csv"
    # Pre-registration guard: throttling/suppressing entries under DEGRADED or
    # CRITICAL changes what the champion trades, so it is OFF until that change
    # is registered and measured. gethealth=STOP suppression is NOT behind this
    # flag — see main._entry_allowed_under_condition.
    entry_gating: bool = False

    @property
    def health_ttl_sec(self) -> float:
        """A gethealth reading older than three polls is not evidence."""
        return self.health_poll_sec * 3.0


def _positive(raw: dict, key: str, default: float, warn: list[str]) -> float:
    try:
        value = float(raw[key])
    except (KeyError, TypeError, ValueError):
        if key in raw:
            warn.append(f"{key}={raw[key]!r} is not a number")
        return default
    if not math.isfinite(value) or value <= 0:
        warn.append(f"{key}={raw[key]!r} must be a finite number > 0")
        return default
    return value


# The reconciliation budget is the time an order is allowed to sit in an
# UNKNOWN state before a human is called. Below 5s the poll schedule cannot
# outlast getchildorders' listing lag (the whole point of the budget); above
# 60s the trading loop is blocked for a minute on one send. Outside that range
# the configured value is not a tuning choice, it is a typo.
RECONCILE_BUDGET_RANGE = (5.0, 60.0)


def load_resilience_config(raw: dict | None) -> ResilienceConfig:
    raw = raw or {}
    warn: list[str] = []
    defaults = ResilienceConfig()
    connect = _positive(raw, "connect_timeout_sec", defaults.connect_timeout_sec, warn)
    read = _positive(raw, "read_timeout_sec", defaults.read_timeout_sec, warn)
    budget = _positive(raw, "retry_budget_sec", defaults.retry_budget_sec, warn)
    health_poll = _positive(raw, "health_poll_sec", defaults.health_poll_sec, warn)
    reconcile = _positive(raw, "reconcile_budget_sec", defaults.reconcile_budget_sec, warn)
    low, high = RECONCILE_BUDGET_RANGE
    if not low <= reconcile <= high:
        warn.append(f"reconcile_budget_sec={reconcile} is outside "
                    f"[{low:.0f}, {high:.0f}]s")
        reconcile = defaults.reconcile_budget_sec
    window = _positive(raw, "condition_window_sec", defaults.condition_window_sec, warn)
    degraded = _positive(raw, "degraded_latency_ms", defaults.degraded_latency_ms, warn)
    critical = _positive(raw, "critical_latency_ms", defaults.critical_latency_ms, warn)
    if degraded >= critical:
        warn.append(f"degraded_latency_ms={degraded} >= critical_latency_ms="
                    f"{critical}; DEGRADED would be unreachable")
        degraded, critical = defaults.degraded_latency_ms, defaults.critical_latency_ms
    try:
        tries = int(raw.get("retry_max_tries", defaults.retry_max_tries))
    except (TypeError, ValueError):
        warn.append(f"retry_max_tries={raw.get('retry_max_tries')!r} is not an integer")
        tries = defaults.retry_max_tries
    if tries < 1:
        warn.append(f"retry_max_tries={tries} must be >= 1")
        tries = defaults.retry_max_tries
    gating = raw.get("entry_gating", defaults.entry_gating)
    if not isinstance(gating, bool):
        # STRICT, not bool(): every non-empty string is truthy, so a quoted
        # "false" — the exact typo YAML invites — would have ENABLED an
        # unregistered behavior change. Anything that is not a bare YAML bool
        # falls back to OFF (bot/strategy/composite.py makes the same call for
        # module gates).
        warn.append(f"entry_gating={gating!r} is not a bare bool "
                    f"({type(gating).__name__}); entries stay ungated")
        gating = defaults.entry_gating
    cfg = ResilienceConfig(
        connect_timeout_sec=connect, read_timeout_sec=read, retry_max_tries=tries,
        retry_budget_sec=budget, health_poll_sec=health_poll,
        reconcile_budget_sec=reconcile, condition_window_sec=window,
        degraded_latency_ms=degraded, critical_latency_ms=critical,
        api_health_csv=str(raw.get("api_health_csv") or defaults.api_health_csv),
        entry_gating=gating,
    )
    if warn:
        logger.warning("resilience config: falling back to defaults",
                       extra={"data": {"event": "resilience_config_invalid",
                                       "problems": warn}})
    return cfg


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

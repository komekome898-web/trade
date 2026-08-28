"""kabuステーションAPI REST client (localhost), scoped to what ON1 L1 needs.

Spec source: the official OpenAPI document, fetched 2026-08-28 from
https://raw.githubusercontent.com/kabucom/kabusapi/master/reference/kabu_STATION_API.yaml
(rendered at https://kabucom.github.io/kabusapi/ptal/ ; `info.version: "1.5"`).
Every constant below is quoted from it:

- `servers:` `http://localhost:18080/kabusapi` 本番 / `http://localhost:18081/kabusapi` 検証
- `POST /token` body `{"APIPassword": "..."}` -> `{"ResultCode": 0, "Token": "..."}`.
  The doc lists when a token dies: kabuステーション終了・ログアウト・別トークン発行、
  および「早朝、強制的にログアウト」。So a 401 on any call means "re-issue", and the
  8:40 job in particular runs right after that forced early-morning logout.
- every other call carries header `X-API-KEY: <token>`
- `POST /sendorder/future` -> `{"Result": 0, "OrderId": "..."}`  (no Password field
  in `RequestSendOrderDerivFuture`; the token is the only credential)
- `POST /cancelorder` body `{"OrderId": "..."}`
- `GET /orders`, `GET /positions` — query `product` `"3"` = 先物
- `GET /symbolname/future?FutureCode=NK225micro&DerivMonth=yyyyMM`
  -> `{"Symbol": "...", "SymbolName": "..."}`
- `GET /board/{symbol}` where the path segment is `[銘柄コード]@[市場コード]`

Safety model (CLAUDE.md §1, principles moved over from bot/exchange/resilience.py
without moving the code):

- ORDER endpoints are NEVER retried.  A failure there is classified once:
  * provably pre-send (connect timeout, or a connection error whose text names
    the new-connection failure) -> `KabuNetworkError`: nothing reached
    kabuステーション, so the caller may treat the order as not placed;
  * a definite 4xx business answer -> `KabuError`: refused, not placed;
  * anything else — read timeout, reset after send, 429, 5xx, or a 2xx whose
    body does not carry the OrderId the endpoint promises -> `OrderStateUnknown`.
    When in doubt on an order endpoint the answer is always "unknown", never
    "rejected", because "rejected" is the state from which a caller resends.
- READ-only endpoints are idempotent, so transport failures / 429 / 5xx are
  retried inside a small fixed budget, and a 401 refreshes the token once.
- The API password is a `Secret`, is registered for log redaction, and appears
  in exactly one request body (`POST /token`).  Request bodies are never logged.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import requests

from bot.logging_setup import register_secret
from bot.settings import Secret

logger = logging.getLogger("bot.jpx.kabu")

PRODUCTION_PORT = 18080
VERIFICATION_PORT = 18081

# Paths that mutate order state.  An ambiguous failure on one of these is the
# STATE_UNKNOWN case and must never be auto-retried.
ORDER_PATHS = ("/sendorder", "/sendorder/future", "/sendorder/option", "/cancelorder")

# `product` query value for 先物 on /orders and /positions.
PRODUCT_FUTURE = "3"

# Only these prove the request body never left this process.  A connect timeout
# means the TCP connection for THIS attempt never completed; the markers are
# raised by urllib3 only from the connect/DNS phase.
_PRE_SEND_TYPES = (requests.exceptions.ConnectTimeout,)
_PRE_SEND_MARKERS = ("failed to establish a new connection",
                     "name or service not known",
                     "nodename nor servname")


class KabuError(Exception):
    """kabuステーション gave a definite answer: the request was refused."""

    def __init__(self, status_code: int, code: int | None, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"kabusapi error HTTP {status_code} code={code}: {message}")


class KabuNetworkError(Exception):
    """Transport failure that provably happened BEFORE anything was sent."""


class OrderStateUnknown(Exception):
    """An order request failed in a way where kabuステーション may or may not have
    processed it.  The caller MUST reconcile with read-only endpoints before it
    is allowed to send anything again (CLAUDE.md §1)."""


def _is_pre_send(exc: BaseException) -> bool:
    if isinstance(exc, _PRE_SEND_TYPES):
        return True
    if isinstance(exc, (requests.exceptions.SSLError, requests.exceptions.ProxyError)):
        return False
    if isinstance(exc, requests.exceptions.ConnectionError):
        text = f"{exc!r}".lower()
        return any(m in text for m in _PRE_SEND_MARKERS)
    return False


class KabuClient:
    """Minimal client.  One instance per job run; the token is cached in memory
    only (a token that outlives the process is worthless — kabuステーション
    invalidates it on its own schedule)."""

    def __init__(self, api_password: Secret, *, port: int = VERIFICATION_PORT,
                 host: str = "localhost", session=None,
                 connect_timeout_sec: float = 3.0, read_timeout_sec: float = 10.0,
                 diagnostic_read_timeout_sec: float = 5.0,
                 max_read_tries: int = 3, retry_delay_sec: float = 0.5,
                 sleep=time.sleep):
        self._password = api_password
        register_secret(api_password.reveal())
        self.port = int(port)
        self._base = f"http://{host}:{self.port}/kabusapi"
        self._session = session if session is not None else requests.Session()
        self._connect_timeout = connect_timeout_sec
        self._read_timeout = read_timeout_sec
        self._diag_read_timeout = diagnostic_read_timeout_sec
        self._max_read_tries = max(1, int(max_read_tries))
        self._retry_delay = retry_delay_sec
        self._sleep = sleep
        self._token: str | None = None

    @property
    def is_production_port(self) -> bool:
        return self.port == PRODUCTION_PORT

    # ---- token ----------------------------------------------------------
    def issue_token(self) -> str:
        """POST /token.  Repeatable: issuing a new token merely invalidates the
        previous one, so this read-shaped mutation is on the retryable path."""
        payload = self._call("POST", "/token", body={"APIPassword": self._password.reveal()},
                             auth=False)
        token = str((payload or {}).get("Token") or "")
        if not token:
            raise KabuNetworkError("token response carried no Token")
        self._token = token
        register_secret(token)
        return token

    def token(self) -> str:
        return self._token or self.issue_token()

    # ---- read-only ------------------------------------------------------
    def orders(self, *, product: str = PRODUCT_FUTURE, symbol: str | None = None,
               details: str = "false") -> list[dict]:
        params: dict[str, Any] = {"product": product, "details": details}
        if symbol:
            params["symbol"] = symbol
        return list(self._call("GET", "/orders", params=params, diagnostic=True) or [])

    def positions(self, *, product: str = PRODUCT_FUTURE, symbol: str | None = None,
                  addinfo: str = "false") -> list[dict]:
        params: dict[str, Any] = {"product": product, "addinfo": addinfo}
        if symbol:
            params["symbol"] = symbol
        return list(self._call("GET", "/positions", params=params, diagnostic=True) or [])

    def symbol_name_future(self, future_code: str, deriv_month: int) -> dict:
        return dict(self._call("GET", "/symbolname/future",
                               params={"FutureCode": future_code,
                                       "DerivMonth": int(deriv_month)},
                               diagnostic=True) or {})

    def board(self, symbol: str, exchange: int) -> dict:
        return dict(self._call("GET", f"/board/{symbol}@{int(exchange)}",
                               diagnostic=True) or {})

    # ---- order endpoints (never retried) --------------------------------
    def send_future_order(self, payload: dict) -> dict:
        """POST /sendorder/future.  The payload is built and sanity-checked by
        the caller (bot/jpx/on1_executor.py); this method only transports it."""
        return dict(self._call("POST", "/sendorder/future", body=payload) or {})

    def cancel_order(self, order_id: str) -> dict:
        return dict(self._call("POST", "/cancelorder", body={"OrderId": order_id}) or {})

    # ---- transport ------------------------------------------------------
    def _call(self, method: str, path: str, *, params: dict | None = None,
              body: dict | None = None, auth: bool = True,
              diagnostic: bool = False) -> Any:
        is_order = path in ORDER_PATHS
        read_timeout = self._diag_read_timeout if diagnostic else self._read_timeout
        timeout = (self._connect_timeout, read_timeout)
        tries = 1 if is_order else self._max_read_tries
        refreshed = False
        last: Exception | None = None

        for attempt in range(tries):
            headers = {"Content-Type": "application/json"}
            if auth:
                headers["X-API-KEY"] = self.token()
            try:
                resp = self._session.request(method, self._base + path, params=params,
                                             json=body, headers=headers, timeout=timeout)
            except Exception as exc:            # transport
                if is_order:
                    if _is_pre_send(exc):
                        raise KabuNetworkError(
                            f"{type(exc).__name__} before send on {path}") from None
                    raise OrderStateUnknown(
                        f"{type(exc).__name__} on {path}; order may have been placed"
                    ) from None
                last = KabuNetworkError(f"{type(exc).__name__} on {path}")
                self._backoff(attempt, tries)
                continue

            status = int(getattr(resp, "status_code", 0))
            if status == 401 and auth and not refreshed and not is_order:
                # Documented token death (kabuステーション logout / forced early
                # morning logout).  Re-issue once, then repeat the read.
                refreshed = True
                self._token = None
                last = KabuError(status, None, "token expired")
                continue
            if status >= 500 or status == 429:
                if is_order:
                    raise OrderStateUnknown(
                        f"HTTP {status} on {path}; order may have been placed")
                last = KabuNetworkError(f"HTTP {status} on {path}")
                self._backoff(attempt, tries)
                continue
            if status >= 400:
                code, message = self._error_of(resp)
                raise KabuError(status, code, message)

            payload = self._json_of(resp)
            if payload is _UNPARSEABLE:
                if is_order:
                    raise OrderStateUnknown(
                        f"unreadable 2xx body on {path}; order may have been placed")
                last = KabuNetworkError(f"unreadable body on {path}")
                self._backoff(attempt, tries)
                continue
            if is_order and not str((payload or {}).get("OrderId") or ""):
                # The endpoint promises an OrderId.  A 200 without one is not a
                # success and not a rejection.
                raise OrderStateUnknown(f"2xx without OrderId on {path}")
            return payload

        raise last if last is not None else KabuNetworkError(f"no answer from {path}")

    def _backoff(self, attempt: int, tries: int) -> None:
        if attempt + 1 < tries:
            self._sleep(self._retry_delay * (2 ** attempt))

    @staticmethod
    def _json_of(resp) -> Any:
        try:
            return resp.json()
        except Exception:
            return _UNPARSEABLE

    @staticmethod
    def _error_of(resp) -> tuple[int | None, str]:
        """`ErrorResponse` is `{"Code": 4001001, "Message": "..."}`.  Only those
        two fields are read out; the raw body may echo the request."""
        payload = KabuClient._json_of(resp)
        if not isinstance(payload, dict):
            return None, "no error body"
        code = payload.get("Code")
        try:
            code = int(code) if code is not None else None
        except (TypeError, ValueError):
            code = None
        return code, str(payload.get("Message") or "")


class _Unparseable:
    pass


_UNPARSEABLE = _Unparseable()


class QueryOnlyKabu:
    """Read-only view handed to the reconciler.

    Same trick as bot/order_management/reconciler.py's `QueryOnlyExchange`: the
    object has no method that can send or cancel, so "reconciliation cannot
    place an order" is a property of the object graph rather than of the
    reconciling code being careful.
    """

    def __init__(self, client: KabuClient):
        self._client = client

    def orders(self, **kwargs) -> list[dict]:
        return self._client.orders(**kwargs)

    def positions(self, **kwargs) -> list[dict]:
        return self._client.positions(**kwargs)

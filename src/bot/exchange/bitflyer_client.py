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
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

import requests

from bot.settings import Secret

BASE_URL = "https://api.bitflyer.com"

# Endpoints that mutate order state: ambiguous failures must not be auto-retried.
_ORDER_ENDPOINTS = ("/v1/me/sendchildorder", "/v1/me/cancelchildorder", "/v1/me/sendparentorder")


class BitflyerError(Exception):
    """API returned an error response (4xx/5xx with a definite answer)."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"bitFlyer API error {status_code}: {message}")


class NetworkError(Exception):
    """Transport-level failure on a read-only endpoint (safe to retry)."""


class OrderStateUnknown(Exception):
    """An order-mutating request failed in a way where the server may or may not
    have processed it. Caller MUST reconcile via getchildorders before resending."""


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
    ):
        self._api_key = api_key or Secret("")
        self._api_secret = api_secret or Secret("")
        self._session = session or requests.Session()
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._sleep = sleep
        self._clock = clock
        # Published limits: private 500/5min, public 500/5min per IP. Stay well below.
        self._private_limiter = RateLimiter(300, 300.0)
        self._public_limiter = RateLimiter(300, 300.0)

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
        is_order_endpoint = path in _ORDER_ENDPOINTS
        attempts = 1 if is_order_endpoint else self._max_retries
        last_exc: Exception | None = None
        for attempt in range(attempts):
            try:
                return self._request_once(method, path, params=params, body=body, auth=auth)
            except BitflyerError as e:
                # 429/5xx on read endpoints: back off and retry. Definite 4xx: raise.
                if not is_order_endpoint and e.status_code in (429, 500, 502, 503, 504):
                    last_exc = e
                    self._sleep(2 ** attempt)
                    continue
                raise
            except NetworkError as e:
                if is_order_endpoint:
                    raise OrderStateUnknown(
                        f"transport failure on {path}; order state must be reconciled"
                    ) from e
                last_exc = e
                self._sleep(2 ** attempt)
        raise last_exc  # type: ignore[misc]

    def _request_once(self, method: str, path: str, *, params: dict | None,
                      body: dict | None, auth: bool) -> Any:
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
        try:
            resp = self._session.request(
                method, url, params=params, data=body_str if body is not None else None,
                headers=headers, timeout=self._timeout,
            )
        except requests.exceptions.RequestException as e:
            # Never include headers/secrets in the raised message.
            raise NetworkError(f"{method} {path}: {type(e).__name__}") from None
        if resp.status_code >= 400:
            detail = ""
            try:
                detail = str(resp.json().get("error_message", ""))[:200]
            except Exception:
                detail = resp.text[:200]
            raise BitflyerError(resp.status_code, detail)
        if resp.text == "":
            return None
        return resp.json()

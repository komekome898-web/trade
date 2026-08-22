"""Shared fixtures. A FakeSession stands in for requests.Session so no test
ever touches the network, and any accidental real-order call is recorded."""
from __future__ import annotations

import json

import pytest
import requests

from bot.exchange.bitflyer_client import BitflyerClient
from bot.settings import Secret


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=None):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload) if text is None and payload is not None else (text or "")

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class FakeSession:
    """Route table keyed by (method, path). Values: FakeResponse, Exception, or
    a list consumed one per call (to simulate fail-then-recover sequences)."""

    def __init__(self):
        self.routes: dict[tuple[str, str], object] = {}
        self.calls: list[dict] = []

    def set(self, method: str, path: str, result) -> None:
        self.routes[(method, path)] = result

    def request(self, method, url, params=None, data=None, headers=None, timeout=None):
        path = url.split("bitflyer.com")[-1]
        self.calls.append({"method": method, "path": path, "params": params,
                           "data": data, "headers": headers})
        result = self.routes.get((method, path))
        if isinstance(result, list):
            result = result.pop(0) if result else FakeResponse(404, {"error_message": "exhausted"})
        if isinstance(result, Exception):
            raise result
        if result is None:
            return FakeResponse(404, {"error_message": f"no route {method} {path}"})
        return result

    def order_calls(self) -> list[dict]:
        return [c for c in self.calls if "sendchildorder" in c["path"]
                or "cancelchildorder" in c["path"]]


@pytest.fixture(autouse=True)
def _clear_gate_scan_cache():
    """bot.monitoring.gates memoises its file scans on (mtime_ns, size). Two
    tests that write DIFFERENT content of the same length to the same tmp path
    inside one mtime tick would otherwise read each other's answer."""
    from bot.monitoring.gates import clear_cache

    clear_cache()
    yield
    clear_cache()


@pytest.fixture
def fake_session():
    return FakeSession()


@pytest.fixture
def client(fake_session):
    return BitflyerClient(
        Secret("test-key"), Secret("test-secret"),
        session=fake_session, sleep=lambda s: None,
    )


@pytest.fixture
def timeout_error():
    return requests.exceptions.ConnectTimeout("boom")


def make_ticker(price=100.0, bid=99.9, ask=100.1):
    return FakeResponse(200, {"ltp": price, "best_bid": bid, "best_ask": ask,
                              "product_code": "XRP_JPY"})

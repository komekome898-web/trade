"""API connectivity, auth, balance, market data, comms errors, API errors,
order-state-unknown behavior (user test items 1-3, 9-10, and rule 12)."""
from __future__ import annotations

import hashlib
import hmac

import pytest

from bot.exchange.bitflyer_client import (
    BitflyerClient, BitflyerError, NetworkError, OrderStateUnknown,
)
from bot.settings import Secret
from tests.conftest import FakeResponse, make_ticker


def test_public_ticker(client, fake_session):
    fake_session.set("GET", "/v1/ticker", make_ticker(price=123.4))
    data = client.ticker("XRP_JPY")
    assert data["ltp"] == 123.4


def test_auth_headers_and_signature(client, fake_session):
    fake_session.set("GET", "/v1/me/getbalance",
                     FakeResponse(200, [{"currency_code": "JPY", "amount": 6000}]))
    client.get_balance()
    headers = fake_session.calls[-1]["headers"]
    assert headers["ACCESS-KEY"] == "test-key"
    ts = headers["ACCESS-TIMESTAMP"]
    expected = hmac.new(b"test-secret", f"{ts}GET/v1/me/getbalance".encode(),
                        hashlib.sha256).hexdigest()
    assert headers["ACCESS-SIGN"] == expected


def test_balance_fetch(client, fake_session):
    fake_session.set("GET", "/v1/me/getbalance",
                     FakeResponse(200, [{"currency_code": "JPY", "amount": 6000,
                                         "available": 6000}]))
    balance = client.get_balance()
    assert balance[0]["available"] == 6000


def test_missing_credentials_refused(fake_session):
    client = BitflyerClient(session=fake_session, sleep=lambda s: None)
    with pytest.raises(BitflyerError) as e:
        client.get_balance()
    assert e.value.status_code == 401
    assert fake_session.calls == []  # refused before any network call


def test_network_error_retries_then_raises(client, fake_session, timeout_error):
    fake_session.set("GET", "/v1/ticker", timeout_error)
    with pytest.raises(NetworkError):
        client.ticker("XRP_JPY")
    assert len(fake_session.calls) == 3  # max_retries attempts


def test_5xx_retry_then_success(client, fake_session):
    fake_session.set("GET", "/v1/ticker", [
        FakeResponse(503, {"error_message": "unavailable"}), make_ticker(price=50.0),
    ])
    assert client.ticker("XRP_JPY")["ltp"] == 50.0


def test_definite_4xx_no_retry(client, fake_session):
    fake_session.set("GET", "/v1/me/getbalance",
                     FakeResponse(401, {"error_message": "invalid key"}))
    with pytest.raises(BitflyerError):
        client.get_balance()
    assert len(fake_session.calls) == 1


def test_order_endpoint_ambiguous_failure_never_retried(client, fake_session, timeout_error):
    fake_session.set("POST", "/v1/me/sendchildorder", timeout_error)
    with pytest.raises(OrderStateUnknown):
        client.send_child_order(product_code="XRP_JPY", side="BUY", size=1.0)
    assert len(fake_session.order_calls()) == 1  # exactly one attempt, no blind resend


def test_secret_never_in_exception_message(client, fake_session, timeout_error):
    fake_session.set("GET", "/v1/ticker", timeout_error)
    try:
        client.ticker("XRP_JPY")
    except NetworkError as e:
        assert "test-secret" not in str(e)
        assert "test-key" not in str(e)


def test_secret_masked_in_repr():
    s = Secret("super-secret-value")
    assert "super-secret-value" not in str(s)
    assert "super-secret-value" not in repr(s)

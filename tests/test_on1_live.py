"""ON1 live-execution layer: the kabusapi client's failure taxonomy and every
hard limit in the executor.  No test touches the network.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest
import requests

from bot.jpx import kabu_client as kc
from bot.jpx import on1_executor as ex
from bot.jpx.kabu_client import (
    KabuClient, KabuError, KabuNetworkError, OrderStateUnknown, QueryOnlyKabu,
)
from bot.jpx.on1_executor import (
    ENTRY, EXIT, FLAT, LONG, STATE_UNKNOWN, On1Config, On1Executor, On1State,
    build_executor, load_on1_config, resolve_central_month, resolve_live, sq_date,
)
from bot.jpx.run_lock import LockBusy, RunLock
from bot.risk.kill_switch import KillSwitch
from bot.settings import Secret

MICRO_SYMBOL = "167090013"
MICRO_NAME = "日経225マイクロ先物 26/09"
MONTH = "202612"          # SQ 2026-12-11, far from the 2026-08 test dates


class Resp:
    def __init__(self, status_code=200, payload=None, text=None):
        self.status_code = status_code
        self._payload = payload
        self.text = text if text is not None else json.dumps(payload)

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class FakeSession:
    """Route table keyed by (method, path); a list is consumed one per call."""

    def __init__(self):
        self.routes: dict[tuple[str, str], object] = {}
        self.calls: list[dict] = []

    def set(self, method, path, result):
        self.routes[(method, path)] = result

    def request(self, method, url, params=None, json=None, headers=None, timeout=None):
        path = url.split("/kabusapi", 1)[-1]
        self.calls.append({"method": method, "path": path, "params": params,
                           "body": json, "headers": headers})
        result = self.routes.get((method, path))
        if isinstance(result, list):
            result = result.pop(0) if result else Resp(404, {"Code": 4001, "Message": "x"})
        if isinstance(result, Exception):
            raise result
        if result is None:
            return Resp(404, {"Code": 4004, "Message": f"no route {method} {path}"})
        return result

    def sends(self):
        return [c for c in self.calls if c["path"].startswith("/sendorder")
                or c["path"] == "/cancelorder"]


@pytest.fixture
def session():
    s = FakeSession()
    s.set("POST", "/token", Resp(200, {"ResultCode": 0, "Token": "tok"}))
    return s


@pytest.fixture
def client(session):
    return KabuClient(Secret("pw"), port=18081, session=session, sleep=lambda s: None)


# ---------------------------------------------------------------------------
# client: spec wiring


def test_ports_and_base_url(session):
    assert (kc.PRODUCTION_PORT, kc.VERIFICATION_PORT) == (18080, 18081)
    session.set("GET", "/positions", Resp(200, []))
    c = KabuClient(Secret("pw"), port=18080, session=session)
    c.positions()
    assert session.calls[-1]["path"] == "/positions"
    assert c.is_production_port


def test_token_is_issued_once_and_carried_as_x_api_key(client, session):
    session.set("GET", "/positions", Resp(200, []))
    client.positions()
    client.positions()
    assert [c["path"] for c in session.calls].count("/token") == 1
    assert session.calls[-1]["headers"]["X-API-KEY"] == "tok"


def test_api_password_is_masked_and_only_sent_to_token(client, session):
    session.set("GET", "/positions", Resp(200, []))
    client.positions()
    token_call = [c for c in session.calls if c["path"] == "/token"][0]
    assert token_call["body"] == {"APIPassword": "pw"}
    assert "pw" not in json.dumps([c for c in session.calls if c["path"] != "/token"])
    assert str(Secret("pw")) == "***MASKED***"


def test_read_endpoint_refreshes_the_token_on_401(client, session):
    session.set("GET", "/positions", [Resp(401, {"Code": 4001001, "Message": "x"}),
                                      Resp(200, [])])
    session.set("POST", "/token", [Resp(200, {"ResultCode": 0, "Token": "a"}),
                                   Resp(200, {"ResultCode": 0, "Token": "b"})])
    assert client.positions() == []
    assert session.calls[-1]["headers"]["X-API-KEY"] == "b"


def test_read_endpoint_retries_5xx_then_succeeds(client, session):
    session.set("GET", "/orders", [Resp(500, {"Code": 1, "Message": "x"}), Resp(200, [])])
    assert client.orders() == []


# ---------------------------------------------------------------------------
# client: the order-endpoint invariant


@pytest.mark.parametrize("failure", [
    requests.exceptions.ReadTimeout("boom"),
    requests.exceptions.SSLError("tlsv1 alert internal error"),
    requests.exceptions.ConnectionError("connection reset by peer"),
])
def test_ambiguous_transport_failure_on_send_is_order_state_unknown(client, session, failure):
    session.set("POST", "/sendorder/future", failure)
    with pytest.raises(OrderStateUnknown):
        client.send_future_order({"Symbol": MICRO_SYMBOL})
    assert len(session.sends()) == 1          # never retried


@pytest.mark.parametrize("status", [500, 502, 429])
def test_5xx_and_429_on_send_are_order_state_unknown(client, session, status):
    session.set("POST", "/sendorder/future", Resp(status, {"Code": 1, "Message": "x"}))
    with pytest.raises(OrderStateUnknown):
        client.send_future_order({"Symbol": MICRO_SYMBOL})
    assert len(session.sends()) == 1


def test_2xx_without_orderid_is_order_state_unknown(client, session):
    session.set("POST", "/sendorder/future", Resp(200, {"Result": 0}))
    with pytest.raises(OrderStateUnknown):
        client.send_future_order({"Symbol": MICRO_SYMBOL})


def test_unparseable_2xx_on_send_is_order_state_unknown(client, session):
    session.set("POST", "/sendorder/future", Resp(200, None, text="<html>maintenance"))
    with pytest.raises(OrderStateUnknown):
        client.send_future_order({"Symbol": MICRO_SYMBOL})


def test_provably_pre_send_failure_is_not_unknown(client, session):
    session.set("POST", "/sendorder/future", requests.exceptions.ConnectTimeout("boom"))
    with pytest.raises(KabuNetworkError):
        client.send_future_order({"Symbol": MICRO_SYMBOL})


def test_definite_4xx_on_send_is_a_rejection(client, session):
    session.set("POST", "/sendorder/future",
                Resp(400, {"Code": 4001005, "Message": "parameter"}))
    with pytest.raises(KabuError) as err:
        client.send_future_order({"Symbol": MICRO_SYMBOL})
    assert err.value.code == 4001005


def test_send_carries_the_payload_verbatim(client, session):
    session.set("POST", "/sendorder/future", Resp(200, {"Result": 0, "OrderId": "O1"}))
    payload = {"Symbol": MICRO_SYMBOL, "Qty": 1}
    assert client.send_future_order(payload)["OrderId"] == "O1"
    assert session.sends()[0]["body"] == payload


def test_query_only_view_cannot_send():
    view = QueryOnlyKabu(object())
    for name in ("send_future_order", "cancel_order", "_call", "_session"):
        assert not hasattr(view, name), name


# ---------------------------------------------------------------------------
# executor fixtures


SESSIONS_CSV_HEADER = ("date,product,month,night_open,night_high,night_low,night_close,"
                       "day_open,day_high,day_low,day_close,day_volume,settlement\n")


def write_sessions(root: Path, date: str = "20260827", close: str = "66000") -> Path:
    path = root / "data" / "jpx_daily" / "nk225_sessions.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        SESSIONS_CSV_HEADER
        + f"{date},micro,{MONTH},1,1,1,1,1,1,1,{close},9000,{close}\n"
        + f"{date},micro,202703,1,1,1,1,1,1,1,{close},5,{close}\n",
        encoding="utf-8")
    return path


class FakeClient:
    """Records every call; order sends can be primed with a result or an exception."""

    def __init__(self, *, positions=None, symbol=MICRO_SYMBOL, name=MICRO_NAME,
                 board_price=66000.0, send=None):
        self._positions = positions if positions is not None else []
        self._symbol, self._name = symbol, name
        self._board_price = board_price
        self._send = send if send is not None else {"Result": 0, "OrderId": "O1"}
        self.sent: list[dict] = []

    def positions(self, **kwargs):
        return list(self._positions)

    def orders(self, **kwargs):
        return []

    def symbol_name_future(self, future_code, deriv_month):
        assert future_code == ex.FUTURE_CODE_MICRO
        return {"Symbol": self._symbol, "SymbolName": self._name}

    def board(self, symbol, exchange):
        return {"CurrentPrice": self._board_price}

    def send_future_order(self, payload):
        self.sent.append(payload)
        if isinstance(self._send, Exception):
            raise self._send
        return dict(self._send)


def make_executor(tmp_path: Path, *, client=None, live=True, now=None,
                  config=None, state=None, csv_date="20260827",
                  board_price=66000.0, positions=None, send=None):
    write_sessions(tmp_path, date=csv_date)
    client = client or FakeClient(board_price=board_price, positions=positions, send=send)
    return On1Executor(
        client=client,
        state=state or On1State(tmp_path / "data" / "on1_live" / "state.json"),
        config=config or On1Config(enabled=True, live_ack=ex.LIVE_ACK_PHRASE),
        kill_switch=KillSwitch(state_dir=tmp_path / "data", manual_file=tmp_path / "KILL"),
        sessions_csv=tmp_path / "data" / "jpx_daily" / "nk225_sessions.csv",
        events_path=tmp_path / "data" / "on1_live" / "events.jsonl",
        live=live, live_reason="test",
        now=now or datetime(2026, 8, 28, 15, 40),
    )


def events(executor) -> list[dict]:
    path = Path(executor.events_path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


LONG_POSITION = [{"Symbol": MICRO_SYMBOL, "Side": ex.SIDE_BUY, "LeavesQty": 1}]


# ---------------------------------------------------------------------------
# executor: the happy path


def test_entry_sends_the_documented_market_on_close_payload(tmp_path):
    e = make_executor(tmp_path)
    assert e.run_entry() == "ordered"
    payload = e.client.sent[0]
    assert payload == {
        "Symbol": MICRO_SYMBOL,
        "Exchange": 23,             # 日中
        "TradeType": 1,             # 新規
        "TimeInForce": 2,           # FAK (the only value 引成（派生） accepts)
        "Side": "2",                # 買
        "Qty": 1,
        "FrontOrderType": 18,       # 引成（派生）
        "Price": 0,
        "ExpireDay": 0,
    }
    assert e.state.status == LONG
    assert e.state.position["symbol"] == MICRO_SYMBOL


def test_exit_sends_a_close_of_exactly_one_contract(tmp_path):
    e = make_executor(tmp_path)
    e.run_entry()
    x = make_executor(tmp_path, state=e.state, positions=LONG_POSITION,
                      now=datetime(2026, 8, 31, 8, 40))
    assert x.run_exit() == "ordered"
    payload = x.client.sent[0]
    assert payload["Side"] == "1" and payload["TradeType"] == 2   # 売 / 返済
    assert payload["FrontOrderType"] == 120 and payload["Price"] == 0
    assert payload["Qty"] == 1 and payload["ClosePositionOrder"] == 0
    assert x.state.status == FLAT


def test_state_survives_a_restart(tmp_path):
    e = make_executor(tmp_path)
    e.run_entry()
    reloaded = On1State(tmp_path / "data" / "on1_live" / "state.json")
    assert reloaded.status == LONG and reloaded.position["symbol"] == MICRO_SYMBOL


# ---------------------------------------------------------------------------
# executor: the double gate


def test_missing_env_gate_is_a_dry_run(tmp_path):
    e = make_executor(tmp_path, live=False)
    assert e.run_entry() == "ordered"
    assert e.client.sent == []
    assert [ev["event"] for ev in events(e)] == ["dry_run_order"]
    assert events(e)[0]["payload"]["FrontOrderType"] == 18


@pytest.mark.parametrize("env,cfg,expected", [
    ({"ON1_LIVE": "true"}, {"enabled": True, "live_ack": ex.LIVE_ACK_PHRASE}, True),
    ({}, {"enabled": True, "live_ack": ex.LIVE_ACK_PHRASE}, False),
    ({"ON1_LIVE": "true"}, {"enabled": False, "live_ack": ex.LIVE_ACK_PHRASE}, False),
    ({"ON1_LIVE": "true"}, {"enabled": True, "live_ack": "I_UNDERSTAND_REAL_MONEY"}, False),
    ({"ON1_LIVE": "1"}, {"enabled": True, "live_ack": ex.LIVE_ACK_PHRASE}, True),
])
def test_double_gate_truth_table(env, cfg, expected):
    live, reason = resolve_live(env, On1Config(**cfg))
    assert live is expected
    assert reason


def test_default_config_is_disabled_and_on_the_verification_port(tmp_path):
    shipped = load_on1_config(Path(__file__).resolve().parents[1] / "config" / "on1_live.yaml")
    assert shipped.enabled is False
    assert shipped.live_ack != ex.LIVE_ACK_PHRASE
    assert shipped.port == 18081
    assert resolve_live({"ON1_LIVE": "true"}, shipped)[0] is False


def test_quoted_false_does_not_arm_the_gate(tmp_path):
    path = tmp_path / "on1_live.yaml"
    path.write_text('enabled: "false"\nlive_ack: "I_UNDERSTAND_REAL_MONEY_JPX"\n',
                    encoding="utf-8")
    cfg = load_on1_config(path)
    assert cfg.enabled is False and cfg.problems


def test_config_cannot_widen_the_hard_time_windows(tmp_path):
    path = tmp_path / "on1_live.yaml"
    path.write_text('entry_window: ["09:00", "23:00"]\n', encoding="utf-8")
    cfg = load_on1_config(path)
    assert cfg.entry_window == ex.HARD_ENTRY_WINDOW
    assert cfg.problems


# ---------------------------------------------------------------------------
# executor: hard limits


def test_kill_file_stops_everything(tmp_path):
    (tmp_path / "KILL").write_text("stop", encoding="utf-8")
    e = make_executor(tmp_path)
    assert e.run_entry() == "skip"
    assert e.client.sent == []
    assert "kill switch" in events(e)[0]["reason"]


def test_persisted_kill_switch_stops_everything(tmp_path):
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "kill_switch.json").write_text(
        json.dumps({"reason": "manual", "detail": "d"}), encoding="utf-8")
    e = make_executor(tmp_path)
    assert e.run_entry() == "skip"
    assert e.client.sent == []


def test_daily_order_cap_is_enforced_and_not_configurable(tmp_path):
    assert ex.MAX_ORDERS_PER_DAY == 4 and ex.MAX_QTY == 1
    state = On1State(tmp_path / "data" / "on1_live" / "state.json")
    for _ in range(ex.MAX_ORDERS_PER_DAY):
        state.count_order("20260828")
    e = make_executor(tmp_path, state=state)
    assert e.run_entry() == "skip"
    assert e.client.sent == []
    assert "daily order cap" in events(e)[-1]["reason"]


def test_the_order_slot_is_consumed_before_the_send(tmp_path):
    e = make_executor(tmp_path, send=OrderStateUnknown("read timeout"))
    e.run_entry()
    assert e.state.orders_today("20260828") == 1


def test_entry_refuses_when_the_account_is_not_flat(tmp_path):
    e = make_executor(tmp_path, positions=LONG_POSITION)
    assert e.run_entry() == "alert"
    assert e.client.sent == []


def test_entry_refuses_a_second_position(tmp_path):
    e = make_executor(tmp_path)
    e.run_entry()
    again = make_executor(tmp_path, state=e.state)
    assert again.run_entry() == "skip"
    assert again.client.sent == []


@pytest.mark.parametrize("positions,why", [
    ([], "flat account"),
    ([{"Symbol": "999999999", "Side": ex.SIDE_BUY, "LeavesQty": 1}], "wrong symbol"),
    ([{"Symbol": MICRO_SYMBOL, "Side": ex.SIDE_SELL, "LeavesQty": 1}], "wrong side"),
    ([{"Symbol": MICRO_SYMBOL, "Side": ex.SIDE_BUY, "LeavesQty": 2}], "wrong qty"),
    ([{"Symbol": MICRO_SYMBOL, "Side": ex.SIDE_BUY, "LeavesQty": 1},
      {"Symbol": "999999999", "Side": ex.SIDE_BUY, "LeavesQty": 1}], "stray position"),
])
def test_exit_does_not_order_on_a_position_mismatch(tmp_path, positions, why):
    e = make_executor(tmp_path)
    e.run_entry()
    x = make_executor(tmp_path, state=e.state, positions=positions,
                      now=datetime(2026, 8, 31, 8, 40))
    assert x.run_exit() == "alert", why
    assert x.client.sent == []
    assert x.state.status == LONG          # untouched: a human decides
    assert events(x)[-1]["reason"] == "position mismatch"


@pytest.mark.parametrize("symbol,name", [
    ("16709001", MICRO_NAME),                       # 8 digits, not the API shape
    ("abcdefghi", MICRO_NAME),
    (MICRO_SYMBOL, "日経225mini先物 26/09"),         # not a micro contract
    (MICRO_SYMBOL, ""),
])
def test_symbol_sanity_failure_is_fail_close(tmp_path, symbol, name):
    client = FakeClient(symbol=symbol, name=name)
    e = make_executor(tmp_path, client=client)
    assert e.run_entry() == "alert"
    assert client.sent == []


def test_price_band_mismatch_blocks_the_entry(tmp_path):
    e = make_executor(tmp_path, board_price=6600.0)     # 10x off the JPX print
    assert e.run_entry() == "alert"
    assert e.client.sent == []
    assert "band" in events(e)[-1]["detail"]


def test_unreadable_board_blocks_the_entry(tmp_path):
    client = FakeClient(board_price=None)
    e = make_executor(tmp_path, client=client)
    assert e.run_entry() == "alert"
    assert client.sent == []


def test_the_exit_is_never_gated_by_the_price_band(tmp_path):
    """A diagnostic must not keep a real position open overnight."""
    e = make_executor(tmp_path)
    e.run_entry()
    client = FakeClient(board_price=None, positions=LONG_POSITION)
    x = make_executor(tmp_path, client=client, state=e.state,
                      now=datetime(2026, 8, 31, 8, 40))
    assert x.run_exit() == "ordered"


def test_sanity_check_rejects_a_tampered_payload(tmp_path):
    e = make_executor(tmp_path)
    for bad in ({"Qty": 2}, {"Side": ex.SIDE_SELL}, {"Exchange": 2},
                {"Price": 100}, {"TimeInForce": 1}, {"FrontOrderType": 120},
                {"TradeType": 2}):
        payload = {"Symbol": MICRO_SYMBOL, "Exchange": 23, "TradeType": 1,
                   "TimeInForce": 2, "Side": "2", "Qty": 1, "FrontOrderType": 18,
                   "Price": 0, "ExpireDay": 0}
        payload.update(bad)
        with pytest.raises(ex.SanityError):
            e._sanity_check(ENTRY, payload, MICRO_NAME, MONTH)


def test_outside_the_time_window_nothing_is_sent(tmp_path):
    e = make_executor(tmp_path, now=datetime(2026, 8, 28, 10, 0))
    assert e.run_entry() == "skip"
    assert e.client.sent == []
    assert "window" in events(e)[-1]["reason"]


# ---------------------------------------------------------------------------
# executor: month resolution / roll


def test_central_month_is_the_largest_micro_day_volume(tmp_path):
    write_sessions(tmp_path)
    month, row, reason = resolve_central_month(
        tmp_path / "data" / "jpx_daily" / "nk225_sessions.csv", datetime(2026, 8, 28).date())
    assert (month, reason) == (MONTH, None)
    assert row["day_close"] == "66000"


def test_a_stale_jpx_reference_blocks_the_entry(tmp_path):
    e = make_executor(tmp_path, csv_date="20260801")
    assert e.run_entry() == "skip"
    assert e.client.sent == []
    assert "stale" in events(e)[-1]["reason"]


def test_sq_is_the_second_friday():
    assert sq_date("202612") == datetime(2026, 12, 11).date()
    assert sq_date("202609") == datetime(2026, 9, 11).date()


def test_entry_is_skipped_in_the_sq_blackout_week(tmp_path):
    """The last-trading-day of a month is not exposed by the API, so the whole
    week before SQ is fail-closed rather than derived."""
    e = make_executor(tmp_path, csv_date="20261209", now=datetime(2026, 12, 10, 15, 40))
    assert e.run_entry() == "skip"
    assert e.client.sent == []
    assert events(e)[-1]["reason"] == "SQ blackout"


# ---------------------------------------------------------------------------
# executor: STATE_UNKNOWN and read-only reconciliation


def test_ambiguous_send_parks_in_state_unknown(tmp_path):
    e = make_executor(tmp_path, send=OrderStateUnknown("read timeout on /sendorder/future"))
    assert e.run_entry() == "alert"
    assert e.state.status == STATE_UNKNOWN
    assert e.state.data["unknown"]["job"] == ENTRY
    assert events(e)[-1]["event"] == "order_state_unknown"


def test_state_unknown_blocks_every_new_order(tmp_path):
    e = make_executor(tmp_path, send=OrderStateUnknown("boom"))
    e.run_entry()
    for job, run in ((ENTRY, "run_entry"), (EXIT, "run_exit")):
        follow = make_executor(tmp_path, state=On1State(e.state.path),
                               now=datetime(2026, 8, 31, 8, 40) if job == EXIT
                               else datetime(2026, 8, 31, 15, 40))
        assert getattr(follow, run)() == "skip"
        assert follow.client.sent == []
        assert "STATE_UNKNOWN" in events(follow)[-1]["reason"]


def test_reconcile_resolves_to_long_on_positive_evidence(tmp_path):
    e = make_executor(tmp_path, send=OrderStateUnknown("boom"))
    e.run_entry()
    e.client._positions = LONG_POSITION
    assert e.reconcile(QueryOnlyKabu(e.client)) == LONG
    assert e.state.status == LONG
    assert e.state.position["symbol"] == MICRO_SYMBOL


def test_reconcile_resolves_to_flat_when_the_order_finished_unfilled(tmp_path):
    e = make_executor(tmp_path, send=OrderStateUnknown("boom"))
    e.run_entry()

    class Q:
        def positions(self, **kw):
            return []

        def orders(self, **kw):
            return [{"ID": "O1", "State": 5, "CumQty": 0}]

    assert e.reconcile(Q()) == FLAT
    assert e.state.status == FLAT


def test_reconcile_keeps_state_unknown_without_evidence(tmp_path):
    e = make_executor(tmp_path, send=OrderStateUnknown("boom"))
    e.run_entry()

    class Q:
        def positions(self, **kw):
            return []

        def orders(self, **kw):
            return []            # eventually-consistent listing: not evidence

    assert e.reconcile(Q()) == "unresolved"
    assert e.state.status == STATE_UNKNOWN


def test_after_reconcile_clears_it_the_next_order_is_allowed(tmp_path):
    e = make_executor(tmp_path, send=OrderStateUnknown("boom"))
    e.run_entry()

    class Q:
        def positions(self, **kw):
            return []

        def orders(self, **kw):
            return [{"ID": "O1", "State": 5, "CumQty": 0}]

    e.reconcile(Q())
    after = make_executor(tmp_path, state=On1State(e.state.path),
                          now=datetime(2026, 8, 31, 15, 40))
    assert after.run_entry() == "ordered"


def test_ambiguous_exit_reconciles_back_to_the_original_long(tmp_path):
    e = make_executor(tmp_path)
    e.run_entry()
    entry_day = e.state.position["entry_day"]
    x = make_executor(tmp_path, state=e.state, positions=LONG_POSITION,
                      now=datetime(2026, 8, 31, 8, 40),
                      send=OrderStateUnknown("read timeout"))
    assert x.run_exit() == "alert"
    assert x.state.status == STATE_UNKNOWN
    assert x.state.data["unknown"]["month"] == MONTH

    class Q:
        def positions(self, **kw):
            return LONG_POSITION

        def orders(self, **kw):
            return [{"ID": "O2", "State": 5, "CumQty": 0}]

    assert x.reconcile(Q()) == LONG
    assert x.state.position["entry_day"] == entry_day     # not rebuilt from the exit


def test_reconcile_is_a_no_op_outside_state_unknown(tmp_path):
    e = make_executor(tmp_path)
    assert e.reconcile(QueryOnlyKabu(e.client)) == "skip"


def test_unreadable_state_file_fails_safe(tmp_path):
    path = tmp_path / "data" / "on1_live" / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ not json", encoding="utf-8")
    assert On1State(path).status == STATE_UNKNOWN


# ---------------------------------------------------------------------------
# executor: definite rejections and pre-send failures


def test_a_definite_rejection_is_recorded_and_nothing_is_resent(tmp_path):
    e = make_executor(tmp_path, send=KabuError(400, 4001005, "parameter"))
    assert e.run_entry() == "alert"
    assert e.state.status == FLAT
    assert events(e)[-1]["event"] == "order_rejected"


def test_a_pre_send_failure_leaves_the_state_flat(tmp_path):
    e = make_executor(tmp_path, send=KabuNetworkError("ConnectTimeout before send"))
    assert e.run_entry() == "alert"
    assert e.state.status == FLAT
    assert events(e)[-1]["event"] == "order_not_sent"


# ---------------------------------------------------------------------------
# run lock


def test_run_lock_refuses_a_second_holder(tmp_path):
    path = tmp_path / "entry.lock"
    with RunLock(path):
        with pytest.raises(LockBusy):
            RunLock(path).acquire()
    with RunLock(path):
        pass                                   # released, so it can be retaken


def test_run_lock_takes_over_a_stale_lock(tmp_path):
    path = tmp_path / "entry.lock"
    RunLock(path, clock=lambda: 0.0).acquire()
    with RunLock(path, stale_after_sec=60.0, clock=lambda: 10_000.0):
        assert path.exists()


# ---------------------------------------------------------------------------
# wiring


def test_build_executor_defaults_to_dry_run(tmp_path, monkeypatch):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "on1_live.yaml").write_text("enabled: false\n", encoding="utf-8")
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    e = build_executor(tmp_path, env={}, client=FakeClient())
    assert e.live is False
    assert e.config.port == 18081

"""Cash-ETF auction-fill measurement executor (docs/PHASE2/EXEC_MEASUREMENT).

The test plan is DESIGN.md §7; the numbered comments below are its item
numbers, so a missing guard is traceable back to the line of the design that
asked for it.  No test touches the network.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pytest
import requests

from bot.jpx import etf_auction_executor as em
from bot.jpx import kabu_client as kc
from bot.jpx import on1_executor as on1
from bot.jpx.etf_auction_executor import (
    ALLOWED_EXCHANGES, ALLOWED_SYMBOLS, ENTRY, EXIT, EXPECTED_TRADING_UNIT, FLAT,
    LIVE_ACK_PHRASE, LONG, MAX_NOTIONAL_YEN, MAX_ORDERS_PER_DAY_PER_SYMBOL,
    STATE_UNKNOWN, EtfAuctionExecutor, EtfMeasureConfig, EtfSymbolState, PauseFlag,
    SanityError, append_ledger_row, build_etf_executor, etf_tick_yen, is_sq_eve,
    load_etf_measure_config, parse_fill, read_ledger, resolve_live,
    round_trip_metrics, summarise_ledger,
)
from bot.jpx.kabu_client import (
    KabuClient, KabuError, KabuNetworkError, OrderStateUnknown, QueryOnlyKabu,
)
from bot.logging_setup import register_secret
from bot.risk.kill_switch import KillSwitch
from bot.settings import Secret

REPO = Path(__file__).resolve().parents[1]
DESIGN = REPO / "docs" / "PHASE2" / "EXEC_MEASUREMENT" / "DESIGN.md"
PREREG = REPO / "docs" / "PHASE2" / "EXEC_MEASUREMENT" / "PREREG.md"

PRICE = {"1343": 1925.0, "1591": 37000.0, "1348": 4255.0}
UNIT = dict(EXPECTED_TRADING_UNIT)

ENTRY_AT = datetime(2026, 10, 1, 15, 20)      # Thursday, not an SQ eve
EXIT_AT = datetime(2026, 10, 2, 8, 40)


# ---------------------------------------------------------------------------
# fakes


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


class FakeClient:
    """Records every call; sends can be primed with a result or an exception."""

    def __init__(self, *, units=None, prices=None, positions=None, orders=None,
                 send=None, limits=None):
        self.units = dict(units or UNIT)
        self.prices = dict(prices or PRICE)
        self._positions = list(positions or [])
        self._orders = list(orders or [])
        self._send = send if send is not None else {"Result": 0, "OrderId": "O1"}
        self.limits = limits or {}
        self.sent: list[dict] = []
        self.order_calls: list[dict] = []

    def positions(self, **kwargs):
        symbol = kwargs.get("symbol")
        rows = list(self._positions)
        if symbol:
            rows = [r for r in rows if str(r.get("Symbol") or symbol) == symbol]
        return rows

    def orders(self, **kwargs):
        self.order_calls.append(dict(kwargs))
        symbol = kwargs.get("symbol")
        rows = list(self._orders)
        if symbol:
            rows = [r for r in rows if str(r.get("Symbol") or symbol) == symbol]
        return rows

    def symbol_info(self, symbol, exchange):
        price = self.prices[symbol]
        lo, hi = self.limits.get(symbol, (price * 0.7, price * 1.3))
        return {"Symbol": symbol, "TradingUnit": self.units[symbol],
                "UpperLimit": hi, "LowerLimit": lo}

    def board(self, symbol, exchange):
        return {"Symbol": symbol, "CurrentPrice": self.prices[symbol]}

    def send_cash_order(self, payload):
        self.sent.append(payload)
        if isinstance(self._send, Exception):
            raise self._send
        result = dict(self._send)
        result["OrderId"] = f"{result.get('OrderId', 'O')}-{payload['Symbol']}-" \
                            f"{payload['Side']}"
        return result


def write_prints(root: Path, symbol: str, rows: list[tuple[str, float, float]]) -> Path:
    path = root / "data" / "etf_measure" / f"print_{symbol}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "date,open,close\n" + "".join(f"{d},{o},{c}\n" for d, o, c in rows)
    path.write_text(body, encoding="utf-8")
    return path


def default_prints(root: Path) -> dict[str, Path]:
    return {s: write_prints(root, s, [("2026-09-30", PRICE[s], PRICE[s]),
                                      ("2026-10-01", PRICE[s], PRICE[s]),
                                      ("2026-10-02", PRICE[s], PRICE[s])])
            for s in ALLOWED_SYMBOLS}


def make_executor(tmp_path: Path, *, client=None, live=True, now=None, config=None,
                  states=None, pause=None, prints=None, ex_dates=None, **client_kw
                  ) -> EtfAuctionExecutor:
    state_dir = tmp_path / "data" / "etf_measure"
    states = states or {s: EtfSymbolState(state_dir / f"state_{s}.json", symbol=s)
                        for s in ALLOWED_SYMBOLS}
    return EtfAuctionExecutor(
        client=client or FakeClient(**client_kw),
        states=states,
        config=config or EtfMeasureConfig(enabled=True, live_ack=LIVE_ACK_PHRASE),
        kill_switch=KillSwitch(state_dir=tmp_path / "data", manual_file=tmp_path / "KILL"),
        pause=pause or PauseFlag(state_dir / "paused.json"),
        events_path=state_dir / "events.jsonl",
        ledger_path=tmp_path / "paper_logs" / "etf_measure_ledger.csv",
        print_series=prints if prints is not None else default_prints(tmp_path),
        index_series={},
        ex_date_sources=ex_dates or {},
        live=live, live_reason="test", now=now or ENTRY_AT,
    )


def events(executor) -> list[dict]:
    path = Path(executor.events_path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def held(symbol: str, qty: float | None = None) -> list[dict]:
    return [{"Symbol": symbol, "Side": em.SIDE_BUY,
             "LeavesQty": UNIT[symbol] if qty is None else qty}]


# ===========================================================================
# 1-7  gates and config
# ===========================================================================


def test_01_shipped_config_is_disabled_and_on_the_verification_port():
    cfg = load_etf_measure_config(REPO / "config" / "etf_measure.yaml")
    assert cfg.enabled is False
    assert cfg.live_ack == ""
    assert cfg.port == kc.VERIFICATION_PORT == 18081
    assert cfg.problems == ()
    assert set(cfg.symbols) == set(ALLOWED_SYMBOLS) == {"1343", "1591", "1348"}
    assert cfg.max_notional_yen == MAX_NOTIONAL_YEN
    assert cfg.skip_dates == frozenset()      # PREREG appendix A not frozen yet
    live, reason = resolve_live({em.LIVE_ENV_VAR: "true"}, cfg)
    assert live is False and "enabled" in reason


@pytest.mark.parametrize("enabled,ack,env,expected", [
    (True, LIVE_ACK_PHRASE, "true", True),
    (True, LIVE_ACK_PHRASE, "", False),
    (True, "", "true", False),
    (True, "", "", False),
    (False, LIVE_ACK_PHRASE, "true", False),
    (False, LIVE_ACK_PHRASE, "", False),
    (False, "", "true", False),
    (False, "", "", False),
])
def test_02_triple_gate_truth_table(enabled, ack, env, expected):
    live, reason = resolve_live({em.LIVE_ENV_VAR: env} if env else {},
                                EtfMeasureConfig(enabled=enabled, live_ack=ack))
    assert live is expected, reason
    assert expected or reason


def test_03_quoted_false_does_not_arm_the_gate(tmp_path):
    path = tmp_path / "etf_measure.yaml"
    path.write_text('enabled: "false"\nlive_ack: "%s"\n' % LIVE_ACK_PHRASE,
                    encoding="utf-8")
    cfg = load_etf_measure_config(path)
    assert cfg.enabled is False
    assert any("not a bare bool" in p for p in cfg.problems)
    assert resolve_live({em.LIVE_ENV_VAR: "true"}, cfg)[0] is False


def test_04_windows_may_narrow_but_never_widen(tmp_path):
    narrow = tmp_path / "narrow.yaml"
    narrow.write_text('entry_window: ["15:15", "15:20"]\n'
                      'exit_window: ["08:35", "08:45"]\n', encoding="utf-8")
    cfg = load_etf_measure_config(narrow)
    assert cfg.entry_window == ("15:15", "15:20")
    assert cfg.exit_window == ("08:35", "08:45")
    assert cfg.problems == ()

    wide = tmp_path / "wide.yaml"
    wide.write_text('entry_window: ["09:00", "23:59"]\n'
                    'exit_window: ["00:00", "23:59"]\n', encoding="utf-8")
    cfg = load_etf_measure_config(wide)
    assert cfg.entry_window == em.HARD_ENTRY_WINDOW
    assert cfg.exit_window == em.HARD_EXIT_WINDOW
    assert len(cfg.problems) == 2


def test_05_symbols_must_be_a_subset_of_the_code_allow_list(tmp_path):
    path = tmp_path / "c.yaml"
    path.write_text('symbols: ["1591", "7203", "1343"]\n', encoding="utf-8")
    cfg = load_etf_measure_config(path)
    assert cfg.symbols == ("1591", "1343")
    assert any("7203" in p for p in cfg.problems)


def test_06_max_notional_may_only_be_lowered(tmp_path):
    lower = tmp_path / "lower.yaml"
    lower.write_text("max_notional_yen_per_symbol: 25000\n", encoding="utf-8")
    assert load_etf_measure_config(lower).max_notional_yen == 25000

    higher = tmp_path / "higher.yaml"
    higher.write_text("max_notional_yen_per_symbol: 500000\n", encoding="utf-8")
    cfg = load_etf_measure_config(higher)
    assert cfg.max_notional_yen == MAX_NOTIONAL_YEN
    assert any("exceeds the code cap" in p for p in cfg.problems)


def test_07_the_two_live_gates_are_completely_separate():
    """Arming ON1 must not arm the measurement, and vice versa."""
    assert em.LIVE_ACK_PHRASE != on1.LIVE_ACK_PHRASE
    assert em.LIVE_ENV_VAR == "ETF_EXEC_LIVE" != "ON1_LIVE"
    armed_on1 = {"ON1_LIVE": "true"}
    assert resolve_live(armed_on1,
                        EtfMeasureConfig(enabled=True, live_ack=LIVE_ACK_PHRASE))[0] \
        is False
    armed_etf = {em.LIVE_ENV_VAR: "true"}
    assert on1.resolve_live(armed_etf,
                            on1.On1Config(enabled=True,
                                          live_ack=on1.LIVE_ACK_PHRASE))[0] is False
    # and neither ack phrase satisfies the other module
    assert resolve_live(armed_etf,
                        EtfMeasureConfig(enabled=True,
                                         live_ack=on1.LIVE_ACK_PHRASE))[0] is False


# ===========================================================================
# 8-12  quantity, trading unit, caps
# ===========================================================================


def test_08_trading_unit_10_orders_ten_units_of_1343(tmp_path):
    e = make_executor(tmp_path)
    assert e.run_entry("1343") == "ordered"
    assert e.client.sent[0]["Qty"] == 10 == EXPECTED_TRADING_UNIT["1343"]


def test_09_trading_unit_1_orders_one_unit_of_1591(tmp_path):
    e = make_executor(tmp_path)
    assert e.run_entry("1591") == "ordered"
    assert e.client.sent[0]["Qty"] == 1 == EXPECTED_TRADING_UNIT["1591"]


def test_10_trading_unit_other_than_pre_registered_sends_nothing(tmp_path):
    e = make_executor(tmp_path, units={"1343": 100, "1591": 1})
    assert e.run_entry("1343") == "alert"
    assert e.client.sent == []
    alert = events(e)[-1]
    assert alert["reason"] == "trading unit changed" and alert["stop_rule"] == "S6"
    assert e.pause.is_paused("1343")


def test_11_a_re_registered_larger_unit_is_still_stopped_by_the_notional_cap(
        tmp_path, monkeypatch):
    """The 2027-01-28 unit change on 1591 (1 -> 10) makes one unit ~370,000 yen.
    Even if someone re-registers EXPECTED_TRADING_UNIT, the notional cap refuses:
    the guard must not depend on a human remembering the date."""
    monkeypatch.setitem(em.EXPECTED_TRADING_UNIT, "1591", 10)
    e = make_executor(tmp_path, units={"1343": 10, "1591": 10})
    assert e.run_entry("1591") == "alert"
    assert e.client.sent == []
    assert "exceeds the 60000 yen cap" in events(e)[-1]["detail"]


def test_12_notional_above_the_cap_is_refused(tmp_path):
    e = make_executor(tmp_path, prices={"1343": 1925.0, "1591": 70000.0},
                      prints={"1343": write_prints(tmp_path, "1343",
                                                   [("2026-10-01", 1925.0, 1925.0)]),
                              "1591": write_prints(tmp_path, "1591",
                                                   [("2026-10-01", 70000.0, 70000.0)])})
    assert e.run_entry("1591") == "alert"
    assert e.client.sent == []
    detail = events(e)[-1]["detail"]
    assert "70000" in detail and f"{MAX_NOTIONAL_YEN} yen cap" in detail


def test_08b_trading_unit_1_orders_one_unit_of_1348(tmp_path):
    """PREREG 追記 2026-09-06: 1348 joins the measurement, unit 1, ~4,255 yen.
    The unit is still read from GET /symbol and cross-checked, like the others."""
    e = make_executor(tmp_path)
    assert e.run_entry("1348") == "ordered"
    payload = e.client.sent[0]
    assert payload["Symbol"] == "1348"
    assert payload["Qty"] == 1 == EXPECTED_TRADING_UNIT["1348"]
    assert payload["FrontOrderType"] == 16 and payload["Price"] == 0
    assert 1 * PRICE["1348"] < MAX_NOTIONAL_YEN
    assert em.PASS_BAR_BPS["1348"] == 2.7


def test_10b_a_changed_trading_unit_on_1348_stops_that_symbol_only(tmp_path):
    e = make_executor(tmp_path, units={"1343": 10, "1591": 1, "1348": 10})
    assert e.run_entry("1348") == "alert"
    assert e.client.sent == []
    assert events(e)[-1]["stop_rule"] == "S6"
    assert e.pause.is_paused("1348")
    assert not e.pause.is_paused("1343") and not e.pause.is_paused("1591")
    assert e.run_entry("1343") == "ordered"


# ===========================================================================
# 13-18  payload sanity
# ===========================================================================


def test_13_buy_payload_matches_the_spec(tmp_path):
    e = make_executor(tmp_path)
    assert e.run_entry("1343") == "ordered"
    assert e.client.sent[0] == {
        "Symbol": "1343",
        "Exchange": 9,               # SOR
        "SecurityType": 1,           # 株式
        "Side": "2",                 # 買
        "CashMargin": 1,             # 現物
        "DelivType": 2,              # お預り金 (現物買は指定必須)
        "FundType": "02",            # 保護
        "AccountType": 4,
        "Qty": 10,
        "FrontOrderType": 16,        # 引成（後場）
        "Price": 0,
        "ExpireDay": 0,
    }


def test_14_sell_payload_matches_the_spec(tmp_path):
    e = make_executor(tmp_path)
    e.run_entry("1343")
    x = make_executor(tmp_path, states=e.states, now=EXIT_AT,
                      positions=held("1343"))
    assert x.run_exit("1343") == "ordered"
    payload = x.client.sent[0]
    assert payload["Side"] == "1"                # 売
    assert payload["CashMargin"] == 1            # 現物 -> a short is impossible
    assert payload["DelivType"] == 0
    assert payload["FundType"] == "  "           # two half-width spaces
    assert len(payload["FundType"]) == 2 and payload["FundType"].strip() == ""
    assert payload["FrontOrderType"] == 13       # 寄成（前場）
    assert payload["Price"] == 0 and payload["Qty"] == 10


def test_15_exchange_1_in_config_is_refused(tmp_path):
    path = tmp_path / "c.yaml"
    path.write_text("exchange: 1\n", encoding="utf-8")
    cfg = load_etf_measure_config(path)
    assert cfg.exchange == 9
    assert any("not in" in p and "ALLOWED" not in p for p in cfg.problems)
    assert 1 not in ALLOWED_EXCHANGES


@pytest.mark.parametrize("field,value", [
    ("Qty", 20), ("Price", 1900), ("Side", "1"), ("CashMargin", 2),
    ("SecurityType", 2), ("Exchange", 1), ("AccountType", 7),
    ("FundType", "01"), ("DelivType", 0), ("FrontOrderType", 13),
    ("ExpireDay", 1), ("Symbol", "7203"),
])
def test_16_a_tampered_payload_fails_close(tmp_path, field, value):
    e = make_executor(tmp_path)
    payload = {
        "Symbol": "1343", "Exchange": 9, "SecurityType": 1, "Side": "2",
        "CashMargin": 1, "DelivType": 2, "FundType": "02", "AccountType": 4,
        "Qty": 10, "FrontOrderType": 16, "Price": 0, "ExpireDay": 0,
    }
    info = e.client.symbol_info("1343", 9)
    e._sanity_check(ENTRY, "1343", payload, info, PRICE["1343"])   # clean payload OK
    payload[field] = value
    with pytest.raises(SanityError):
        e._sanity_check(ENTRY, "1343", payload, info, PRICE["1343"])


def test_17_a_symbol_pinned_at_its_limit_is_not_entered(tmp_path):
    e = make_executor(tmp_path, limits={"1343": (1500.0, 1925.0)})
    assert e.run_entry("1343") == "alert"
    assert e.client.sent == []
    assert "limit up" in events(e)[-1]["detail"]


def test_18_the_price_band_gates_entry_but_never_the_exit(tmp_path):
    stale = {s: write_prints(tmp_path, s, [("2026-09-30", 100.0, 100.0)])
             for s in ALLOWED_SYMBOLS}
    e = make_executor(tmp_path, prints=stale)
    assert e.run_entry("1343") == "alert"
    assert "band" in events(e)[-1]["detail"]

    # a real position must still be closable with the same stale reference
    opened = make_executor(tmp_path)
    opened.run_entry("1343")
    x = make_executor(tmp_path, states=opened.states, now=EXIT_AT, prints=stale,
                      positions=held("1343"))
    assert x.run_exit("1343") == "ordered"


# ===========================================================================
# 19-25  state machine
# ===========================================================================


def test_19_entry_goes_long_and_exit_goes_flat(tmp_path):
    e = make_executor(tmp_path)
    assert e.run_entry("1343") == "ordered"
    assert e.state_of("1343").status == LONG
    x = make_executor(tmp_path, states=e.states, now=EXIT_AT, positions=held("1343"))
    assert x.run_exit("1343") == "ordered"
    assert x.state_of("1343").status == FLAT


def test_20_a_second_entry_from_long_is_refused(tmp_path):
    e = make_executor(tmp_path)
    e.run_entry("1343")
    again = make_executor(tmp_path, states=e.states, positions=held("1343"))
    assert again.run_entry("1343") == "skip"
    assert again.client.sent == []
    assert f"not {FLAT}" in events(again)[-1]["reason"]


def test_21_an_exit_from_flat_is_refused(tmp_path):
    e = make_executor(tmp_path, now=EXIT_AT)
    assert e.run_exit("1343") == "skip"
    assert e.client.sent == []
    assert f"not {LONG}" in events(e)[-1]["reason"]


def test_22_state_survives_a_restart(tmp_path):
    e = make_executor(tmp_path)
    e.run_entry("1591")
    reloaded = EtfSymbolState(tmp_path / "data" / "etf_measure" / "state_1591.json",
                              symbol="1591")
    assert reloaded.status == LONG
    assert reloaded.position["qty"] == 1


def test_23_two_orders_per_symbol_per_day_is_the_cap(tmp_path):
    e = make_executor(tmp_path)
    e.run_entry("1343")
    e.state_of("1343").set_flat()
    e.run_entry("1343")                       # slot 2
    e.state_of("1343").set_flat()
    assert e.run_entry("1343") == "skip"
    assert len(e.client.sent) == MAX_ORDERS_PER_DAY_PER_SYMBOL == 2
    assert "daily order cap" in events(e)[-1]["reason"]
    # the cap is per symbol, so the other symbol is untouched
    assert e.run_entry("1591") == "ordered"


def test_24_the_order_slot_is_consumed_before_the_send(tmp_path):
    e = make_executor(tmp_path, send=OrderStateUnknown("read timeout on /sendorder"))
    assert e.run_entry("1343") == "alert"
    assert e.state_of("1343").orders_today(e.day_key) == 1
    reloaded = EtfSymbolState(tmp_path / "data" / "etf_measure" / "state_1343.json",
                              symbol="1343")
    assert reloaded.orders_today(e.day_key) == 1


def test_25_the_exit_refuses_when_positions_do_not_match(tmp_path):
    e = make_executor(tmp_path)
    e.run_entry("1343")
    e.state_of("1343").data["position"]["dry_run"] = False
    e.state_of("1343").save()
    x = make_executor(tmp_path, states=e.states, now=EXIT_AT,
                      positions=held("1343", qty=3))
    assert x.run_exit("1343") == "alert"
    assert x.client.sent == []
    assert events(x)[-1]["reason"] == "position mismatch"


# ===========================================================================
# 26-33  ambiguous failures and reconciliation
# ===========================================================================


def test_26_an_ambiguous_failure_parks_the_symbol_in_state_unknown(tmp_path):
    e = make_executor(tmp_path, send=OrderStateUnknown("HTTP 502 on /sendorder"))
    assert e.run_entry("1343") == "alert"
    assert e.state_of("1343").status == STATE_UNKNOWN
    assert events(e)[-1]["event"] == "order_state_unknown"


def test_27_state_unknown_on_one_symbol_stops_every_symbol(tmp_path):
    e = make_executor(tmp_path, send=OrderStateUnknown("boom"))
    e.run_entry("1343")
    other = make_executor(tmp_path, states=e.states, now=ENTRY_AT)
    for symbol in ("1591", "1348"):
        assert other.run_entry(symbol) == "skip"
        assert "STATE_UNKNOWN" in events(other)[-1]["reason"]
    assert other.client.sent == []
    later = make_executor(tmp_path, states=e.states, now=EXIT_AT)
    assert later.run_exit("1591") == "skip"
    assert later.run_exit("1348") == "skip"


def test_28_a_provably_pre_send_failure_leaves_the_state_flat(tmp_path):
    e = make_executor(tmp_path, send=KabuNetworkError("ConnectTimeout before send"))
    assert e.run_entry("1343") == "alert"
    assert e.state_of("1343").status == FLAT
    assert events(e)[-1]["event"] == "order_not_sent"


def test_29_a_definite_4xx_is_recorded_and_nothing_is_resent(tmp_path):
    e = make_executor(tmp_path, send=KabuError(400, 4001005, "parameter"))
    assert e.run_entry("1343") == "alert"
    assert e.state_of("1343").status == FLAT
    assert len(e.client.sent) == 1
    assert events(e)[-1]["event"] == "order_rejected"


def test_30_reconcile_resolves_only_on_positive_evidence(tmp_path):
    e = make_executor(tmp_path, send=OrderStateUnknown("boom"))
    e.run_entry("1343")
    proof = make_executor(tmp_path, states=e.states, positions=held("1343"))
    assert proof.reconcile_symbol(QueryOnlyKabu(proof.client), "1343") == LONG
    assert proof.state_of("1343").status == LONG


def test_31_an_empty_orders_listing_is_not_evidence(tmp_path):
    e = make_executor(tmp_path, send=OrderStateUnknown("boom"))
    e.run_entry("1343")
    blind = make_executor(tmp_path, states=e.states, positions=[], orders=[])
    assert blind.reconcile_symbol(QueryOnlyKabu(blind.client), "1343") == "unresolved"
    assert blind.state_of("1343").status == STATE_UNKNOWN


def test_32_without_evidence_state_unknown_stands(tmp_path):
    e = make_executor(tmp_path, send=OrderStateUnknown("boom"))
    e.run_entry("1343")
    # a finished, unfilled order IS positive evidence of a non-fill
    resolved = make_executor(tmp_path, states=e.states, positions=[],
                             orders=[{"ID": "X", "State": 5, "CumQty": 0}])
    assert resolved.reconcile_symbol(QueryOnlyKabu(resolved.client), "1343") == FLAT
    # a still-working order is not
    e2 = make_executor(tmp_path, send=OrderStateUnknown("boom"),
                       now=datetime(2026, 10, 5, 15, 20))
    e2.run_entry("1591")
    stuck = make_executor(tmp_path, states=e2.states, positions=[],
                          orders=[{"ID": "Y", "State": 3, "CumQty": 0}])
    assert stuck.reconcile_symbol(QueryOnlyKabu(stuck.client), "1591") == "unresolved"
    assert stuck.state_of("1591").status == STATE_UNKNOWN


def test_33_the_query_only_view_has_no_way_to_send():
    view = QueryOnlyKabu(object())
    for name in ("send_cash_order", "send_future_order", "cancel_order",
                 "_call", "_session"):
        assert not hasattr(view, name), name
    assert set(dir(view)) & {"orders", "positions"} == {"orders", "positions"}


# ===========================================================================
# 34-39  stop rules (PREREG §6)
# ===========================================================================


def _round_trip(tmp_path, *, buy=1925.0, sell=1925.0, symbol="1343",
                entry_day=None, exit_day=None, states=None, pause=None):
    """Drive one full entry -> exit -> ledger-finalise cycle with given fills."""
    entry_day = entry_day or ENTRY_AT
    exit_day = exit_day or EXIT_AT
    e = make_executor(tmp_path, now=entry_day, states=states, pause=pause)
    e.run_entry(symbol)
    e.state_of(symbol).data["position"]["dry_run"] = False
    e.state_of(symbol).save()
    x = make_executor(tmp_path, now=exit_day, states=e.states, pause=e.pause,
                      positions=held(symbol))
    x.run_exit(symbol)
    pending = x.state_of(symbol).pending[-1]
    orders = [
        _filled(pending["entry_order_id"], symbol, buy, UNIT[symbol]),
        _filled(pending["exit_order_id"], symbol, sell, UNIT[symbol]),
    ]
    f = make_executor(tmp_path, now=exit_day, states=x.states, pause=x.pause,
                      orders=orders)
    rows = f.finalize_pending(QueryOnlyKabu(f.client))
    return f, rows


def _filled(order_id, symbol, price, qty, commission=0.0):
    return {"ID": order_id, "Symbol": symbol, "State": 5, "CumQty": qty,
            "ExchangeName": "SOR", "Details": [
                {"RecType": 1, "Price": 0, "Qty": qty},
                {"RecType": 8, "Price": price, "Qty": qty,
                 "Commission": commission, "CommissionTax": 0.0,
                 "ExecutionDay": 20261002}]}


def _unfilled(order_id, symbol):
    return {"ID": order_id, "Symbol": symbol, "State": 5, "CumQty": 0,
            "ExchangeName": "SOR", "Details": [{"RecType": 1, "Price": 0, "Qty": 0}]}


def test_34_a_leg_more_than_three_ticks_off_the_print_pauses_entries(tmp_path):
    # tick at 1925 yen is 1 yen = 5.19bps; 3 ticks ~ 15.6bps.  Buying 5 yen
    # above the print is ~26bps.
    f, rows = _round_trip(tmp_path, buy=1930.0)
    assert rows and f.pause.is_paused("1343") and f.pause.is_paused("1591")
    assert "S1" in f.pause.reason("1343")
    later = make_executor(tmp_path, now=datetime(2026, 10, 5, 15, 20),
                          states=f.states, pause=f.pause)
    assert later.run_entry("1343") == "skip"
    assert later.client.sent == []
    assert "paused" in events(later)[-1]["reason"]


def test_35_a_pause_never_blocks_the_closing_leg(tmp_path):
    e = make_executor(tmp_path)
    e.run_entry("1343")
    e.pause.trip("S1_leg_deviation", "*", "test pause")
    x = make_executor(tmp_path, states=e.states, pause=e.pause, now=EXIT_AT,
                      positions=held("1343"))
    assert x.run_exit("1343") == "ordered"
    assert x.client.sent[0]["Side"] == em.SIDE_SELL


def test_36_two_consecutive_unfilled_nights_stop_the_symbol(tmp_path):
    states = None
    pause = None
    for day in ((datetime(2026, 10, 1, 15, 20), datetime(2026, 10, 2, 8, 40)),
                (datetime(2026, 10, 5, 15, 20), datetime(2026, 10, 6, 8, 40))):
        e = make_executor(tmp_path, now=day[0], states=states, pause=pause)
        e.run_entry("1343")
        e.state_of("1343").data["position"]["dry_run"] = False
        e.state_of("1343").save()
        x = make_executor(tmp_path, now=day[1], states=e.states, pause=e.pause,
                          positions=held("1343"))
        x.run_exit("1343")
        pending = x.state_of("1343").pending[-1]
        f = make_executor(tmp_path, now=day[1], states=x.states, pause=x.pause,
                          orders=[_unfilled(pending["entry_order_id"], "1343"),
                                  _unfilled(pending["exit_order_id"], "1343")])
        f.finalize_pending(QueryOnlyKabu(f.client))
        states, pause = f.states, f.pause
    assert pause.is_paused("1343")
    assert "S3" in pause.reason("1343")
    rows = read_ledger(tmp_path / "paper_logs" / "etf_measure_ledger.csv")
    assert [r["counted_in_n"] for r in rows] == ["False", "False"]
    assert {r["excluded_reason"] for r in rows} == {"not_filled"}


def test_37_a_cumulative_loss_below_the_floor_stops_everything(tmp_path):
    # one unit of 1591 dropping 20,000 yen overnight is past the -15,000 floor
    prints = {s: write_prints(tmp_path, s, [("2026-10-01", PRICE[s], PRICE[s]),
                                            ("2026-10-02", PRICE[s] - 20000, PRICE[s])])
              for s in ALLOWED_SYMBOLS}
    e = make_executor(tmp_path, prints=prints)
    e.run_entry("1591")
    e.state_of("1591").data["position"]["dry_run"] = False
    e.state_of("1591").save()
    x = make_executor(tmp_path, now=EXIT_AT, states=e.states, pause=e.pause,
                      prints=prints, positions=held("1591"))
    x.run_exit("1591")
    pending = x.state_of("1591").pending[-1]
    f = make_executor(tmp_path, now=EXIT_AT, states=x.states, pause=x.pause,
                      prints=prints,
                      orders=[_filled(pending["entry_order_id"], "1591", 37000.0, 1),
                              _filled(pending["exit_order_id"], "1591", 17000.0, 1)])
    f.finalize_pending(QueryOnlyKabu(f.client))
    assert f.pause.is_paused("1343") and f.pause.is_paused("1591")
    assert "S4" in f.pause.reason("1591")


def test_38_the_kill_switch_stops_every_leg(tmp_path):
    e = make_executor(tmp_path)
    e.run_entry("1343")
    (tmp_path / "KILL").write_text("stop", encoding="utf-8")
    killed = make_executor(tmp_path, states=e.states, now=EXIT_AT,
                           positions=held("1343"))
    assert killed.run_entry("1591") == "skip"
    assert killed.run_exit("1343") == "skip"
    assert killed.client.sent == []
    assert all("kill switch" in ev["reason"] for ev in events(killed)
               if ev["event"] == "skip")


def test_39_a_pause_does_not_auto_resume(tmp_path):
    flag = PauseFlag(tmp_path / "paused.json")
    flag.trip("S1_leg_deviation", "*", "detail")
    assert PauseFlag(tmp_path / "paused.json").is_paused("1343")
    with pytest.raises(PermissionError):
        PauseFlag(tmp_path / "paused.json").clear()
    reloaded = PauseFlag(tmp_path / "paused.json")
    reloaded.clear(operator_confirm=True)
    assert not PauseFlag(tmp_path / "paused.json").is_paused()


# ===========================================================================
# 40-42  calendar and windows
# ===========================================================================


def test_40_a_pre_registered_skip_date_is_not_entered(tmp_path):
    cfg = EtfMeasureConfig(enabled=True, live_ack=LIVE_ACK_PHRASE,
                           skip_dates=frozenset({"2026-10-01"}))
    e = make_executor(tmp_path, config=cfg)
    assert e.run_entry("1343") == "skip"
    assert e.client.sent == []
    assert "skip_dates" in events(e)[-1]["reason"]


def test_41_the_eve_of_a_quarterly_sq_is_not_entered(tmp_path):
    assert is_sq_eve(date(2026, 9, 10)) and is_sq_eve(date(2026, 12, 10))
    assert not is_sq_eve(date(2026, 9, 11))          # SQ itself
    assert not is_sq_eve(date(2026, 10, 8))          # not a quarterly month
    e = make_executor(tmp_path, now=datetime(2026, 9, 10, 15, 20),
                      prints={s: write_prints(tmp_path, s,
                                              [("2026-09-10", PRICE[s], PRICE[s])])
                              for s in ALLOWED_SYMBOLS})
    assert e.run_entry("1343") == "skip"
    assert e.client.sent == []
    assert "SQ" in events(e)[-1]["reason"]


def test_40b_ex_dates_are_read_from_the_frozen_dividend_snapshot():
    """1348's exclusion calendar is DERIVED from its MD5-stamped snapshot, so it
    is reproducible and nobody picks the excluded nights by eye (PREREG §3)."""
    snapshot = (REPO / "backtest_data" / "jpx_etf_daily_20260906_topix_alt"
                / "1348.T.json")
    ex = em.ex_dates_from_yahoo_snapshot(snapshot)
    assert len(ex) == 28                       # 14 years x 2 distributions
    assert "2026-07-16" in ex and "2026-01-16" in ex and "2013-01-16" in ex
    assert all(d[5:] in ("01-16", "07-16") for d in ex), sorted(ex)
    # the snapshot is a record of the PAST -- 2027-01-16 is not in it
    assert "2027-01-16" not in ex

    # ...so the regular anniversary is carried forward, and only then
    projected = em.project_ex_dates(ex)
    assert projected == frozenset({"2027-01-16", "2027-07-16",
                                   "2028-01-16", "2028-07-16"})
    assert em.project_ex_dates(["2020-01-16", "2021-03-02"]) == frozenset()
    assert em.project_ex_dates([]) == frozenset()

    skips = em.skip_dates_around_ex_dates(ex | projected)
    assert "2027-01-16" in skips
    assert "2027-01-15" in skips          # 2027-01-16 is a Saturday -> Friday
    assert "2026-07-16" in skips and "2026-07-15" in skips
    assert em.previous_weekday(date(2026, 7, 20)) == date(2026, 7, 17)   # Mon->Fri
    assert em.ex_dates_from_yahoo_snapshot(REPO / "does" / "not" / "exist") \
        == frozenset()


def test_40c_an_ex_date_excludes_only_its_own_symbol(tmp_path):
    """1348's ex-date must not cost 1343 or 1591 a night."""
    snapshot = (REPO / "backtest_data" / "jpx_etf_daily_20260906_topix_alt"
                / "1348.T.json")
    on_ex_eve = datetime(2027, 1, 15, 15, 20)
    prints = {s: write_prints(tmp_path, s, [("2027-01-15", PRICE[s], PRICE[s])])
              for s in ALLOWED_SYMBOLS}
    e = make_executor(tmp_path, now=on_ex_eve, prints=prints,
                      ex_dates={"1348": snapshot})
    assert e.run_entry("1348") == "skip"
    assert "ex-dividend" in events(e)[-1]["reason"]
    assert e.client.sent == []
    assert e.run_entry("1343") == "ordered"
    assert e.run_entry("1591") == "ordered"
    assert [p["Symbol"] for p in e.client.sent] == ["1343", "1591"]


@pytest.mark.parametrize("when,job", [
    (datetime(2026, 10, 1, 14, 59), ENTRY),
    (datetime(2026, 10, 1, 15, 25), ENTRY),
    (datetime(2026, 10, 2, 7, 59), EXIT),
    (datetime(2026, 10, 2, 8, 51), EXIT),
])
def test_42_nothing_is_sent_outside_the_hard_windows(tmp_path, when, job):
    e = make_executor(tmp_path, now=when)
    e.state_of("1343").set_long({"symbol": "1343", "qty": 10, "trading_unit": 10,
                                 "entry_date": "2026-10-01", "dry_run": True})
    outcome = e.run_entry("1343") if job == ENTRY else e.run_exit("1343")
    assert outcome == "skip"
    assert e.client.sent == []
    assert "outside the" in events(e)[-1]["reason"]


# ===========================================================================
# 43-46  ledger and read-out
# ===========================================================================


def test_43_c_is_zero_when_the_fills_equal_the_prints_and_one_tick_when_off_one():
    exact = round_trip_metrics(fill_buy=1925.0, fill_sell=1925.0,
                               print_close=1925.0, print_open=1925.0, qty=10)
    assert exact["c_bps"] == pytest.approx(0.0, abs=1e-9)
    assert exact["c_ticks"] == pytest.approx(0.0, abs=1e-9)
    assert exact["tick_yen"] == 1 == etf_tick_yen(1925.0)

    one_tick = round_trip_metrics(fill_buy=1926.0, fill_sell=1925.0,
                                  print_close=1925.0, print_open=1925.0, qty=10)
    assert one_tick["c_ticks"] == pytest.approx(1.0, abs=0.01)
    assert one_tick["c_bps"] == pytest.approx(one_tick["c_bps_approx"], abs=0.03)
    assert one_tick["e_buy_bps"] > 0 and one_tick["e_sell_bps"] == 0

    both = round_trip_metrics(fill_buy=1926.0, fill_sell=1924.0,
                              print_close=1925.0, print_open=1925.0, qty=10)
    assert both["c_ticks"] == pytest.approx(2.0, abs=0.02)
    assert both["pnl_yen"] == pytest.approx(-20.0)


def test_44_excluded_rows_do_not_enter_the_estimate(tmp_path):
    path = tmp_path / "ledger.csv"
    for i in range(6):
        append_ledger_row(path, {"symbol": "1343", "c_bps": 1.0,
                                 "counted_in_n": True, "excluded_reason": ""})
    append_ledger_row(path, {"symbol": "1343", "c_bps": 999.0,
                             "counted_in_n": False,
                             "excluded_reason": "not_filled"})
    out = summarise_ledger(path, symbols=("1343",))["symbols"]["1343"]
    assert out["n"] == 6 and out["excluded"] == 1
    assert out["mean_c_bps"] == pytest.approx(1.0)
    assert out["verdict"] == "incomplete"          # n < 50, never judged early


def test_45_the_bootstrap_read_out_is_deterministic(tmp_path):
    path = tmp_path / "ledger.csv"
    for i in range(60):
        append_ledger_row(path, {"symbol": "1591", "c_bps": 2.0 + (i % 7) * 0.3,
                                 "counted_in_n": True, "excluded_reason": ""})
    first = summarise_ledger(path, symbols=("1591",))["symbols"]["1591"]
    second = summarise_ledger(path, symbols=("1591",))["symbols"]["1591"]
    assert first == second
    assert first["n"] == 60 and first["ci_lo_bps"] < first["ci_hi_bps"]
    assert first["verdict"] == "pass"              # bar 6.3bps, mean ~2.9bps


def test_46_the_pass_bars_match_the_pre_registration_text():
    """The bars are TRANSCRIBED from the judgment proposals, so the constant and
    the document must not be able to drift apart."""
    text = PREREG.read_text(encoding="utf-8")
    body, addendum = text.split("## 追記")
    for symbol in ("1343", "1591"):
        bar = em.PASS_BAR_BPS[symbol]
        row = [line.strip() for line in body.splitlines()
               if line.strip().startswith(f"| {symbol} ") and "CI" in line]
        assert row, symbol
        assert f"< {bar}bps" in row[0], (symbol, row[0])
    # 1348 was added later, by the owner decision in the addendum -- its bar is
    # transcribed from there, not from the frozen table above it.
    assert "1348" in addendum
    assert f"**{em.PASS_BAR_BPS['1348']}bps**" in addendum
    assert "1 口 4,255 円" in addendum and em.EXPECTED_TRADING_UNIT["1348"] == 1
    assert set(em.PASS_BAR_BPS) == set(ALLOWED_SYMBOLS)
    assert em.TARGET_N_PER_SYMBOL == 50
    assert f"各銘柄 {em.TARGET_N_PER_SYMBOL} 往復" in text
    assert em.STOP_CUM_PNL_YEN == -15_000.0 and "−15,000 円" in text
    assert em.BOOTSTRAP_BLOCK == 5 and em.BOOTSTRAP_N == 2000
    assert "ブロック長 5" in text and "2,000 回" in text


# ===========================================================================
# 47  secrets
# ===========================================================================


def test_47_no_credential_can_reach_the_event_log(tmp_path):
    secret = "kabu-api-password-not-a-real-one"
    register_secret(secret)
    e = make_executor(tmp_path, send=OrderStateUnknown(f"boom {secret} boom"))
    assert e.run_entry("1343") == "alert"
    raw = Path(e.events_path).read_text(encoding="utf-8")
    assert secret not in raw
    assert "***REDACTED***" in raw
    state = (tmp_path / "data" / "etf_measure" / "state_1343.json").read_text(
        encoding="utf-8")
    assert secret not in state
    # and the payload itself never carries a credential field
    payloads = [ev.get("payload") for ev in events(e) if ev.get("payload")]
    assert payloads and all(
        not (set(p) & {"APIPassword", "Password", "Token", "X-API-KEY"})
        for p in payloads)


# ===========================================================================
# extra: client wiring, fill parsing, tick table, wrappers, deploy
# ===========================================================================


@pytest.fixture
def session():
    s = FakeSession()
    s.set("POST", "/token", Resp(200, {"ResultCode": 0, "Token": "tok"}))
    return s


@pytest.fixture
def client(session):
    return KabuClient(Secret("pw"), port=18081, session=session, sleep=lambda s: None)


def test_send_cash_order_is_on_the_never_retried_order_path(client, session):
    assert "/sendorder" in kc.ORDER_PATHS
    session.set("POST", "/sendorder", requests.exceptions.ReadTimeout("boom"))
    with pytest.raises(OrderStateUnknown):
        client.send_cash_order({"Symbol": "1343"})
    assert len(session.sends()) == 1


def test_send_cash_order_2xx_without_orderid_is_unknown(client, session):
    session.set("POST", "/sendorder", Resp(200, {"Result": 0}))
    with pytest.raises(OrderStateUnknown):
        client.send_cash_order({"Symbol": "1343"})


def test_cash_reads_use_product_1(client, session):
    session.set("GET", "/orders", Resp(200, []))
    session.set("GET", "/positions", Resp(200, []))
    client.orders(product=kc.PRODUCT_CASH, symbol="1343")
    assert session.calls[-1]["params"]["product"] == "1"
    client.positions(product=kc.PRODUCT_CASH, symbol="1343")
    assert session.calls[-1]["params"]["product"] == "1"
    session.set("GET", "/symbol/1343@9", Resp(200, {"TradingUnit": 10}))
    assert client.symbol_info("1343", 9)["TradingUnit"] == 10
    session.set("GET", "/orders", Resp(200, [{"ID": "A"}]))
    assert client.order_by_id("A")[0]["ID"] == "A"
    assert session.calls[-1]["params"] == {"product": "1", "id": "A",
                                           "details": "true"}


def test_a_fake_client_fill_is_parsed_out_of_details_rectype_8():
    row = {"ID": "O1", "State": 5, "CumQty": 10, "Details": [
        {"RecType": 1, "Price": 0, "Qty": 10},          # 受付
        {"RecType": 3, "Price": 0, "Qty": 10},          # 発注
        {"RecType": 8, "Price": 1925.0, "Qty": 6, "Commission": 0.0,
         "CommissionTax": 0.0, "ExecutionDay": 20261001},
        {"RecType": 8, "Price": 1930.0, "Qty": 4, "Commission": 55.0,
         "CommissionTax": 5.0, "ExecutionDay": 20261001},
    ]}
    fill = parse_fill(row)
    assert fill["qty"] == 10
    assert fill["price"] == pytest.approx((1925.0 * 6 + 1930.0 * 4) / 10)
    assert fill["commission"] == 55.0 and fill["commission_tax"] == 5.0
    assert fill["time"] == "20261001"

    assert parse_fill({"Details": []})["price"] is None
    assert parse_fill({})["price"] is None
    assert em.order_is_finished_unfilled({"State": 5, "CumQty": 0})
    assert not em.order_is_finished_unfilled({"State": 3, "CumQty": 0})


def test_the_tick_table_matches_config_constants():
    import yaml
    raw = yaml.safe_load((REPO / "config" / "constants.yaml").read_text(
        encoding="utf-8"))
    table = raw["jpx_cash_equity"]["etf_tick_size_yen_by_price_band"]["value"]
    for key, tick in table.items():
        if key.startswith("up_to_"):
            bound = int(key[len("up_to_"):-len("_yen")])
            assert etf_tick_yen(bound) == tick, key
            assert (bound, tick) in em.ETF_TICK_BANDS, key
    assert etf_tick_yen(60_000_000) == table["over_50000000_yen"]
    assert etf_tick_yen(PRICE["1343"]) == 1 and etf_tick_yen(PRICE["1591"]) == 10


def test_a_full_round_trip_writes_one_ledger_row(tmp_path):
    f, rows = _round_trip(tmp_path, buy=1925.0, sell=1925.0)
    ledger = read_ledger(tmp_path / "paper_logs" / "etf_measure_ledger.csv")
    assert len(ledger) == 1
    row = ledger[0]
    assert set(row) == set(em.LEDGER_COLUMNS)
    assert row["symbol"] == "1343" and row["counted_in_n"] == "True"
    assert row["entry_date"] == "2026-10-01" and row["exit_date"] == "2026-10-02"
    assert row["exchange"] == "9" and row["exchange_name"] == "SOR"
    assert float(row["c_bps"]) == pytest.approx(0.0, abs=1e-6)
    assert float(row["qty"]) == 10 and float(row["trading_unit"]) == 10
    assert row["entry_order_id"] and row["exit_order_id"]
    assert not f.state_of("1343").pending          # drained


def test_an_unfinished_order_stays_pending_and_is_never_written_as_unfilled(tmp_path):
    e = make_executor(tmp_path)
    e.run_entry("1343")
    e.state_of("1343").data["position"]["dry_run"] = False
    e.state_of("1343").save()
    x = make_executor(tmp_path, now=EXIT_AT, states=e.states, positions=held("1343"))
    x.run_exit("1343")
    f = make_executor(tmp_path, now=EXIT_AT, states=x.states, orders=[])
    assert f.finalize_pending(QueryOnlyKabu(f.client)) == []
    assert f.state_of("1343").pending                    # still staged
    assert not (tmp_path / "paper_logs" / "etf_measure_ledger.csv").exists()


def test_a_dry_run_sends_nothing_and_prints_what_it_would_send(tmp_path):
    e = make_executor(tmp_path, live=False)
    assert e.run_entry("1343") == "ordered"
    assert e.client.sent == []
    record = [ev for ev in events(e) if ev["event"] == "dry_run_order"][0]
    assert record["live"] is False
    assert record["payload"]["FrontOrderType"] == 16
    assert record["payload"]["Qty"] == 10


def test_a_dry_run_round_trip_leaves_no_ledger_row(tmp_path):
    e = make_executor(tmp_path, live=False)
    e.run_entry("1343")
    x = make_executor(tmp_path, live=False, now=EXIT_AT, states=e.states)
    x.run_exit("1343")
    f = make_executor(tmp_path, live=False, now=EXIT_AT, states=x.states)
    f.finalize_pending(QueryOnlyKabu(f.client))
    assert not (tmp_path / "paper_logs" / "etf_measure_ledger.csv").exists()
    assert not f.state_of("1343").pending


def test_an_unreadable_state_file_fails_safe(tmp_path):
    path = tmp_path / "state_1343.json"
    path.write_text("{ not json", encoding="utf-8")
    assert EtfSymbolState(path, symbol="1343").status == STATE_UNKNOWN


def test_an_unreadable_pause_file_fails_safe(tmp_path):
    path = tmp_path / "paused.json"
    path.write_text("{ not json", encoding="utf-8")
    assert PauseFlag(path).is_paused("1343")


def test_build_executor_defaults_to_dry_run(tmp_path, monkeypatch):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "etf_measure.yaml").write_text("enabled: false\n",
                                                          encoding="utf-8")
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    e = build_etf_executor(tmp_path, env={}, client=FakeClient())
    assert e.live is False
    assert e.config.port == 18081
    assert set(e.states) == set(ALLOWED_SYMBOLS)
    assert e.ledger_path == tmp_path / "paper_logs" / "etf_measure_ledger.csv"


def test_on1_state_and_measurement_state_do_not_share_a_file(tmp_path, monkeypatch):
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "etf_measure.yaml").write_text("enabled: false\n",
                                                          encoding="utf-8")
    (tmp_path / "config" / "on1_live.yaml").write_text("enabled: false\n",
                                                       encoding="utf-8")
    etf = build_etf_executor(tmp_path, env={}, client=FakeClient())
    paths = {str(s.path) for s in etf.states.values()} | {str(etf.events_path)}
    assert str(tmp_path / "data" / "on1_live" / "state.json") not in paths
    assert all("etf_measure" in p for p in paths)


# ---- wrapper scripts -------------------------------------------------------


@pytest.mark.parametrize("name,func", [
    ("run_etf_measure_entry", "run_entry_all"),
    ("run_etf_measure_exit", "run_exit_all"),
])
def test_the_wrapper_scripts_lock_and_return_zero(tmp_path, monkeypatch, capsys,
                                                  name, func):
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "ROOT", tmp_path)

    executor = make_executor(tmp_path, live=False, now=ENTRY_AT if func ==
                             "run_entry_all" else EXIT_AT)
    monkeypatch.setattr(mod, "build_etf_executor", lambda root: executor)
    assert mod.main() == 0
    out = capsys.readouterr().out
    assert name in out and "live=False" in out


def test_the_reconcile_wrapper_is_read_only(tmp_path, monkeypatch, capsys):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_etf_measure_reconcile", REPO / "scripts" / "run_etf_measure_reconcile.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "ROOT", tmp_path)

    e = make_executor(tmp_path, send=OrderStateUnknown("boom"))
    e.run_entry("1343")
    executor = make_executor(tmp_path, states=e.states, positions=[], orders=[])
    monkeypatch.setattr(mod, "build_etf_executor", lambda root: executor)
    assert mod.main() == 0
    out = capsys.readouterr().out
    assert "STATE_UNKNOWN stands" in out
    assert executor.client.sent == []


def test_the_reconcile_script_is_not_scheduled():
    for bat in (REPO / "deploy").glob("*.bat"):
        assert "run_etf_measure_reconcile" not in bat.read_text(encoding="utf-8"), \
            bat.name


# ---- deploy bats -----------------------------------------------------------


@pytest.mark.parametrize("name", ["etf_measure_entry.bat", "etf_measure_exit.bat"])
def test_the_measurement_bats_follow_the_deploy_conventions(name):
    path = REPO / "deploy" / name
    raw = path.read_bytes()
    assert not [b for b in raw if b > 127], f"{name} must be ASCII (console is cp932)"
    text = raw.decode("ascii")
    assert text.startswith("@echo off")
    assert 'cd /d "%~dp0.."' in text          # runs from the repo root
    assert text.rstrip().endswith("exit /b 0")
    assert "if not exist logs mkdir logs" in text
    assert '>> "logs\\etf_measure.out.log" 2>&1' in text
    assert "KILL" in text                      # emergency stop is documented
    assert "ETF_EXEC_LIVE" in text             # the gate is named in the header
    # it must invoke ONLY its own script, and must not touch the ON1 ones
    assert "run_on1_" not in text
    assert "on1_live.yaml" not in text
    assert text.count(".venv\\Scripts\\python.exe") == 1


def test_the_measurement_bats_point_at_scripts_that_exist(tmp_path):
    """Mimic tree: everything the bat references, laid out as on the Windows box."""
    for name, script in (("etf_measure_entry.bat", "run_etf_measure_entry.py"),
                         ("etf_measure_exit.bat", "run_etf_measure_exit.py")):
        text = (REPO / "deploy" / name).read_text(encoding="ascii")
        assert f'"scripts\\{script}"' in text
        assert (REPO / "scripts" / script).exists()
        assert '".venv\\Scripts\\python.exe"' in text
        mimic = tmp_path / name.replace(".bat", "")
        (mimic / "deploy").mkdir(parents=True)
        (mimic / "scripts").mkdir()
        (mimic / "config").mkdir()
        (mimic / "deploy" / name).write_bytes((REPO / "deploy" / name).read_bytes())
        (mimic / "scripts" / script).write_text("", encoding="utf-8")
        (mimic / "config" / "etf_measure.yaml").write_text("", encoding="utf-8")
        # `cd /d "%~dp0.."` from deploy\ lands on the mimic root, where every
        # relative path the bat names resolves.
        root = (mimic / "deploy" / "..").resolve()
        assert (root / "scripts" / script).exists()
        assert (root / "config" / "etf_measure.yaml").exists()


def test_existing_on1_bats_are_untouched():
    for name in ("on1_entry.bat", "on1_exit.bat"):
        text = (REPO / "deploy" / name).read_text(encoding="utf-8")
        assert "etf_measure" not in text
        assert "ON1_LIVE" in text


# ---- docs ------------------------------------------------------------------


def test_operations_section_5_2_carries_the_owner_checklist():
    ops = (REPO / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")
    assert "## 5.2" in ops
    section = ops.split("## 5.2")[1].split("\n## ")[0]
    for needle in ("etf_measure_entry.bat", "etf_measure_exit.bat",
                   "run_etf_measure_reconcile.py", "ETF_EXEC_LIVE",
                   LIVE_ACK_PHRASE, "18081", "18080", "STATE_UNKNOWN",
                   "KILL", "60,000", "6.1bps", "6.3bps", "2027-01-27"):
        assert needle in section, needle
    # the checklist itself, copied from DESIGN section 8
    design = DESIGN.read_text(encoding="utf-8")
    checklist = design.split("## 8.")[1].split("\n## ")[0]
    boxes = [line.strip() for line in checklist.splitlines()
             if line.strip().startswith("- [ ]")]
    assert len(boxes) >= 20
    assert section.count("- [ ]") >= len(boxes)


def test_the_schema_documents_every_ledger_column():
    schema = json.loads((REPO / "schema" / "etf_measure_ledger.json").read_text(
        encoding="utf-8"))
    group = schema["file_groups"][
        "etf_measure_ledger.csv (paper_logs/etf_measure_ledger.csv)"]
    assert tuple(group["columns"]) == em.LEDGER_COLUMNS
    assert "PERMANENT" in schema["retention"]
    assert schema["known_defects"]
    assert "paper_logs/etf_measure_ledger.csv" in schema["path_glob"]

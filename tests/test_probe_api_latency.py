"""Tests for scripts/probe_api_latency.py -- read-only API RTT probe
(EXEC_FLOOR_PREREG.md sec7 row 3)."""
from __future__ import annotations

import csv
import gzip
import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import probe_api_latency as pal  # noqa: E402

from bot.exchange.bitflyer_client import BitflyerClient  # noqa: E402
from bot.settings import Mode, RiskLimits, Secret, Settings  # noqa: E402
from tests.conftest import FakeResponse  # noqa: E402

LIMITS = RiskLimits(1, 1, 1, 1, 1, 1, 1)


def _client(fake_session, with_creds=True):
    if with_creds:
        return BitflyerClient(Secret("k"), Secret("s"), session=fake_session,
                              sleep=lambda s: None)
    return BitflyerClient(session=fake_session, sleep=lambda s: None)


# ---- timed_call --------------------------------------------------------------
def test_timed_call_success(fake_session):
    client = _client(fake_session)
    fake_session.set("GET", "/v1/ticker",
                     FakeResponse(200, {"best_bid": 1, "best_ask": 2}))
    t_send, t_recv, status = pal.timed_call(client, lambda: client.ticker("FX_BTC_JPY"))
    assert status == "200"
    assert t_recv >= t_send


def test_timed_call_api_error(fake_session):
    client = _client(fake_session)
    fake_session.set("GET", "/v1/me/getpermissions",
                     FakeResponse(403, {"error_message": "no"}))
    t_send, t_recv, status = pal.timed_call(client, client.get_permissions)
    assert status == "403"


def test_timed_call_network_error(fake_session):
    import requests
    client = _client(fake_session)
    fake_session.set("GET", "/v1/ticker", requests.exceptions.ConnectTimeout("boom"))
    t_send, t_recv, status = pal.timed_call(client, lambda: client.ticker("FX_BTC_JPY"))
    assert status == ""


# ---- run_cycle / CSV output ---------------------------------------------------
def test_run_cycle_with_credentials_writes_two_rows(fake_session, tmp_path):
    client = _client(fake_session, with_creds=True)
    fake_session.set("GET", "/v1/ticker", FakeResponse(200, {"best_bid": 1, "best_ask": 2}))
    fake_session.set("GET", "/v1/me/getpermissions", FakeResponse(200, ["get_balance"]))
    out = tmp_path / "api_probe.csv"
    rows = pal.run_cycle(client, True, out, ws_dir=None, ws_state_path=tmp_path / "st.json")
    assert [r["endpoint"] for r in rows] == ["public:getticker", "private:getpermissions"]
    assert [r["http_status"] for r in rows] == ["200", "200"]
    with out.open() as f:
        written = list(csv.DictReader(f))
    assert len(written) == 2
    assert written[0]["ws_note"] == "disabled"


def test_run_cycle_without_credentials_marks_private_leg(fake_session, tmp_path):
    client = _client(fake_session, with_creds=False)
    fake_session.set("GET", "/v1/ticker", FakeResponse(200, {"best_bid": 1, "best_ask": 2}))
    out = tmp_path / "api_probe.csv"
    rows = pal.run_cycle(client, False, out, ws_dir=None, ws_state_path=tmp_path / "st.json")
    assert rows[1]["http_status"] == "no_credentials"
    assert fake_session.calls == [c for c in fake_session.calls if "getpermissions" not in c["path"]]


def test_run_cycle_appends_across_two_calls(fake_session, tmp_path):
    client = _client(fake_session, with_creds=False)
    fake_session.set("GET", "/v1/ticker", FakeResponse(200, {"best_bid": 1, "best_ask": 2}))
    out = tmp_path / "api_probe.csv"
    pal.run_cycle(client, False, out, ws_dir=None, ws_state_path=tmp_path / "st.json")
    pal.run_cycle(client, False, out, ws_dir=None, ws_state_path=tmp_path / "st.json")
    with out.open() as f:
        written = list(csv.DictReader(f))
    assert len(written) == 4
    assert written[0].keys() == set(pal.FIELDS)


# ---- ws_ticker_lag (best-effort tail reader) ---------------------------------
def _write_member(path: Path, mode: str, obj: dict) -> None:
    with gzip.open(path, mode) as f:
        f.write((json.dumps(obj) + "\n").encode("utf-8"))


def test_ws_ticker_lag_no_dir(tmp_path):
    lag, note = pal.ws_ticker_lag(tmp_path / "missing", tmp_path / "st.json", time.time())
    assert (lag, note) == (None, "no_ws_dir")


def test_ws_ticker_lag_no_files(tmp_path):
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    lag, note = pal.ws_ticker_lag(ws_dir, tmp_path / "st.json", time.time())
    assert (lag, note) == (None, "no_ws_file")


def test_ws_ticker_lag_reads_new_ticker_message(tmp_path):
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    f = ws_dir / "FX_BTC_JPY_20260101_000000.jsonl.gz"
    rts = time.time() - 5.0
    _write_member(f, "wb", {"rts": rts, "m": {"params": {
        "channel": "lightning_ticker_FX_BTC_JPY",
        "message": {"best_bid": 1, "best_ask": 2}}}})
    state_path = tmp_path / "st.json"
    now = time.time()
    lag, note = pal.ws_ticker_lag(ws_dir, state_path, now)
    assert note == "ok"
    assert lag == pytest.approx(now - rts, abs=0.5)
    assert state_path.exists()


def test_ws_ticker_lag_ignores_non_ticker_messages(tmp_path):
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    f = ws_dir / "FX_BTC_JPY_20260101_000000.jsonl.gz"
    _write_member(f, "wb", {"rts": time.time(), "m": {"params": {
        "channel": "lightning_executions_FX_BTC_JPY", "message": []}}})
    lag, note = pal.ws_ticker_lag(ws_dir, tmp_path / "st.json", time.time())
    assert (lag, note) == (None, "no_ticker_seen")


def test_ws_ticker_lag_unchanged_reuses_stored_last_rts(tmp_path):
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    f = ws_dir / "FX_BTC_JPY_20260101_000000.jsonl.gz"
    rts = time.time() - 10.0
    _write_member(f, "wb", {"rts": rts, "m": {"params": {
        "channel": "lightning_ticker_FX_BTC_JPY",
        "message": {"best_bid": 1, "best_ask": 2}}}})
    state_path = tmp_path / "st.json"
    pal.ws_ticker_lag(ws_dir, state_path, time.time())
    later = time.time() + 3.0
    lag, note = pal.ws_ticker_lag(ws_dir, state_path, later)
    assert note == "unchanged"
    assert lag == pytest.approx(later - rts, abs=0.5)


def test_ws_ticker_lag_mid_flush_does_not_advance_offset(tmp_path):
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    f = ws_dir / "FX_BTC_JPY_20260101_000000.jsonl.gz"
    rts = time.time() - 20.0
    _write_member(f, "wb", {"rts": rts, "m": {"params": {
        "channel": "lightning_ticker_FX_BTC_JPY",
        "message": {"best_bid": 1, "best_ask": 2}}}})
    state_path = tmp_path / "st.json"
    lag1, note1 = pal.ws_ticker_lag(ws_dir, state_path, time.time())
    assert note1 == "ok"

    # Simulate a torn/truncated tail appended by a recorder mid-flush.
    with f.open("ab") as raw:
        raw.write(b"\x1f\x8b\x08\x00garbagenotarealmember")

    lag2, note2 = pal.ws_ticker_lag(ws_dir, state_path, time.time())
    assert note2 == "mid_flush"
    assert lag2 is not None  # falls back to the last known rts

    # The stored offset must not have advanced past the good member --
    # once the torn bytes are dropped/replaced by a real flush, a later
    # read should recover cleanly with a NEW ticker message.
    state = json.loads(state_path.read_text())
    key = f.name
    assert state[key]["offset"] < f.stat().st_size


def test_ws_ticker_lag_recovers_after_real_flush_following_mid_flush(tmp_path):
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    f = ws_dir / "FX_BTC_JPY_20260101_000000.jsonl.gz"
    rts1 = time.time() - 30.0
    _write_member(f, "wb", {"rts": rts1, "m": {"params": {
        "channel": "lightning_ticker_FX_BTC_JPY",
        "message": {"best_bid": 1, "best_ask": 2}}}})
    state_path = tmp_path / "st.json"
    pal.ws_ticker_lag(ws_dir, state_path, time.time())

    with f.open("ab") as raw:
        raw.write(b"\x1f\x8b\x08\x00garbagenotarealmember")
    pal.ws_ticker_lag(ws_dir, state_path, time.time())  # mid_flush, offset unchanged

    # Bad tail bytes replaced by a real, complete second member (as if the
    # recorder had actually finished this flush instead of being killed).
    data = f.read_bytes()
    good_len = len(data) - len(b"\x1f\x8b\x08\x00garbagenotarealmember")
    f.write_bytes(data[:good_len])
    rts2 = time.time() - 1.0
    _write_member(f, "ab", {"rts": rts2, "m": {"params": {
        "channel": "lightning_ticker_FX_BTC_JPY",
        "message": {"best_bid": 3, "best_ask": 4}}}})

    now = time.time()
    lag, note = pal.ws_ticker_lag(ws_dir, state_path, now)
    assert note == "ok"
    assert lag == pytest.approx(now - rts2, abs=0.5)


# ---- main(): LIVE refusal -----------------------------------------------------
def test_main_refuses_when_live(monkeypatch, tmp_path):
    live_settings = Settings(mode=Mode.LIVE, product_code="FX_BTC_JPY", config={},
                             risk_limits=LIMITS, api_key=Secret("k"), api_secret=Secret("s"))
    monkeypatch.setattr(pal, "load_settings", lambda root: live_settings)
    rc = pal.main(["--max-cycles", "0"])
    assert rc == 1


def test_main_runs_one_cycle_in_paper_mode(monkeypatch, tmp_path):
    paper_settings = Settings(mode=Mode.PAPER, product_code="FX_BTC_JPY", config={},
                              risk_limits=LIMITS)
    monkeypatch.setattr(pal, "load_settings", lambda root: paper_settings)

    calls = []

    def fake_run_cycle(client, has_credentials, out_path, ws_dir, ws_state_path):
        calls.append(1)
        return [{"endpoint": "public:getticker", "http_status": "200", "rtt_ms": 1.0},
                {"endpoint": "private:getpermissions", "http_status": "no_credentials", "rtt_ms": ""}]

    monkeypatch.setattr(pal, "run_cycle", fake_run_cycle)
    rc = pal.main(["--max-cycles", "1", "--interval-sec", "0", "--no-ws",
                  "--out", str(tmp_path / "out.csv")])
    assert rc == 0
    assert len(calls) == 1

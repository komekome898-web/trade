"""Tests for scripts/record_funding_basis.py -- funding-rate history and
FX/spot basis daily logger (EXEC_FLOOR_PREREG.md sec7 row 2)."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import record_funding_basis as rfb  # noqa: E402

from bot.exchange.bitflyer_client import BitflyerClient  # noqa: E402
from tests.conftest import FakeResponse  # noqa: E402


def _client(fake_session):
    return BitflyerClient(session=fake_session, sleep=lambda s: None)


# ---- field-name mapping (schema is not pinned down -- see module docstring) ---
def test_history_row_maps_primary_field_names():
    row = rfb.history_row({"calculation_date": "2026-09-01T05:00:00",
                            "settlement_date": "2026-09-01T13:00:00",
                            "rate": "0.0001"})
    assert row == {"calculation_date": "2026-09-01T05:00:00",
                   "settlement_date": "2026-09-01T13:00:00", "rate": "0.0001"}


def test_history_row_maps_alternate_field_names():
    row = rfb.history_row({"corresponding_time": "2026-09-01T13:00:00",
                            "funding_rate": 0.0002})
    assert row == {"calculation_date": "", "settlement_date": "2026-09-01T13:00:00",
                   "rate": 0.0002}


def test_history_row_none_on_unrecognized_shape():
    assert rfb.history_row({"foo": "bar"}) is None
    assert rfb.history_row("not a dict") is None


def test_current_row_maps_next_period_start_at():
    row = rfb.current_row({"current_funding_rate": 0.0003,
                            "next_period_start_at": "2026-09-01T21:00:00"},
                          now_iso="2026-09-01T13:05:00")
    assert row == {"calculation_date": "2026-09-01T13:05:00",
                   "settlement_date": "2026-09-01T21:00:00", "rate": 0.0003}


def test_current_row_none_on_unrecognized_shape():
    assert rfb.current_row({"nonsense": 1}, now_iso="x") is None


# ---- dedup by settlement_date ------------------------------------------------
def test_collect_funding_dedupes_against_existing_and_within_call(fake_session):
    client = _client(fake_session)
    fake_session.set("GET", "/v1/getfundingrate",
                     FakeResponse(200, {"current_funding_rate": 0.0001,
                                        "next_period_start_at": "2026-09-01T21:00:00"}))
    fake_session.set("GET", "/v1/getfundingratehistory",
                     FakeResponse(200, [
                         {"calculation_date": "2026-09-01T05:00:00",
                          "settlement_date": "2026-09-01T13:00:00", "rate": 0.0001},
                         # same settlement as the "current" call above -- must
                         # not be appended twice in one run
                         {"calculation_date": "2026-09-01T13:00:00",
                          "settlement_date": "2026-09-01T21:00:00", "rate": 0.0001},
                     ]))
    existing = {"2026-08-31T21:00:00"}  # already on disk -- must be skipped
    rows, warnings = rfb.collect_funding(client, existing)
    settlements = [r["settlement_date"] for r in rows]
    assert settlements == ["2026-09-01T21:00:00", "2026-09-01T13:00:00"]
    assert warnings == []


def test_collect_funding_warns_but_does_not_crash_on_bad_shape(fake_session):
    client = _client(fake_session)
    fake_session.set("GET", "/v1/getfundingrate", FakeResponse(200, {"weird": 1}))
    fake_session.set("GET", "/v1/getfundingratehistory", FakeResponse(200, [{"x": 1}]))
    rows, warnings = rfb.collect_funding(client, existing=set())
    assert rows == []
    assert len(warnings) == 2
    assert "unrecognized" in warnings[0]


def test_collect_funding_survives_network_failure(fake_session):
    client = _client(fake_session)
    fake_session.set("GET", "/v1/getfundingrate", requests_error())
    fake_session.set("GET", "/v1/getfundingratehistory", FakeResponse(200, []))
    rows, warnings = rfb.collect_funding(client, existing=set())
    assert rows == []
    assert any("getfundingrate failed" in w for w in warnings)


def requests_error():
    import requests
    return requests.exceptions.ConnectTimeout("boom")


# ---- CSV append + idempotence ------------------------------------------------
def test_append_funding_rows_writes_header_once(tmp_path):
    path = tmp_path / "funding.csv"
    n1 = rfb._append_funding_rows(path, [
        {"calculation_date": "a", "settlement_date": "s1", "rate": 0.1}])
    n2 = rfb._append_funding_rows(path, [
        {"calculation_date": "b", "settlement_date": "s2", "rate": 0.2}])
    assert (n1, n2) == (1, 1)
    with path.open() as f:
        rows = list(csv.reader(f))
    assert rows[0] == rfb.FUNDING_FIELDS
    assert len(rows) == 3


def test_existing_settlements_reads_column(tmp_path):
    path = tmp_path / "funding.csv"
    path.write_text("calculation_date,settlement_date,rate\n"
                    "2026-08-20T05:00:00,2026-08-20T13:00:00,0.0001\n",
                    encoding="utf-8")
    assert rfb._existing_settlements(path) == {"2026-08-20T13:00:00"}


def test_existing_settlements_missing_file_is_empty_set(tmp_path):
    assert rfb._existing_settlements(tmp_path / "nope.csv") == set()


def test_run_once_is_idempotent_across_two_calls(fake_session, tmp_path):
    client = _client(fake_session)
    fake_session.set("GET", "/v1/getfundingrate",
                     FakeResponse(200, {"current_funding_rate": 0.0001,
                                        "next_period_start_at": "2026-09-01T21:00:00"}))
    fake_session.set("GET", "/v1/getfundingratehistory", FakeResponse(200, []))
    fake_session.set("GET", "/v1/ticker", [
        FakeResponse(200, {"best_bid": 100, "best_ask": 102}),
        FakeResponse(200, {"best_bid": 98, "best_ask": 100}),
        FakeResponse(200, {"best_bid": 100, "best_ask": 102}),
        FakeResponse(200, {"best_bid": 98, "best_ask": 100}),
    ])
    funding_csv = tmp_path / "funding.csv"
    basis_csv = tmp_path / "basis.csv"

    rfb.run_once(client, funding_csv, basis_csv)
    rfb.run_once(client, funding_csv, basis_csv)

    with funding_csv.open() as f:
        funding_rows = list(csv.DictReader(f))
    assert len(funding_rows) == 1  # same settlement both times -- not duplicated

    with basis_csv.open() as f:
        basis_rows = list(csv.DictReader(f))
    assert len(basis_rows) == 2  # basis is a plain time series -- both kept


# ---- basis computation --------------------------------------------------------
def test_collect_basis_mid_to_mid(fake_session, tmp_path, monkeypatch):
    client = _client(fake_session)
    fake_session.set("GET", "/v1/ticker", [
        FakeResponse(200, {"best_bid": 12000000, "best_ask": 12002000}),  # FX
        FakeResponse(200, {"best_bid": 11900000, "best_ask": 11902000}),  # spot
    ])
    monkeypatch.setattr(rfb, "CANDLE_FX", tmp_path / "nope1.csv")
    monkeypatch.setattr(rfb, "CANDLE_SPOT", tmp_path / "nope2.csv")

    row, warnings = rfb.collect_basis(client)
    assert warnings == []
    fx_mid = (12000000 + 12002000) / 2
    spot_mid = (11900000 + 11902000) / 2
    assert row["fx_mid"] == fx_mid
    assert row["spot_mid"] == spot_mid
    assert row["basis_bp"] == pytest.approx((fx_mid / spot_mid - 1) * 1e4)
    assert row["basis_close_bp"] == ""  # no candle files


def test_collect_basis_reads_candle_closes(fake_session, tmp_path, monkeypatch):
    client = _client(fake_session)
    fake_session.set("GET", "/v1/ticker", [
        FakeResponse(200, {"best_bid": 100, "best_ask": 102}),
        FakeResponse(200, {"best_bid": 98, "best_ask": 100}),
    ])
    fx_csv = tmp_path / "fx.csv"
    spot_csv = tmp_path / "spot.csv"
    fx_csv.write_text("ts,open,high,low,close,volume,synthetic\n"
                      "2026-09-01 00:00:00+00:00,1,1,1,12000000.0,0.1,0\n",
                      encoding="utf-8")
    spot_csv.write_text("ts,open,high,low,close,volume\n"
                        "2026-09-01 00:00:00+00:00,1,1,1,11900000.0,0.1\n",
                        encoding="utf-8")
    monkeypatch.setattr(rfb, "CANDLE_FX", fx_csv)
    monkeypatch.setattr(rfb, "CANDLE_SPOT", spot_csv)

    row, _warnings = rfb.collect_basis(client)
    assert row["fx_close_1m"] == 12000000.0
    assert row["spot_close_1m"] == 11900000.0
    assert row["basis_close_bp"] == pytest.approx((12000000.0 / 11900000.0 - 1) * 1e4)


def test_last_candle_close_missing_file(tmp_path):
    assert rfb._last_candle_close(tmp_path / "nope.csv") is None


def test_last_candle_close_empty_file(tmp_path):
    p = tmp_path / "empty.csv"
    p.write_text("ts,open,high,low,close,volume\n", encoding="utf-8")
    assert rfb._last_candle_close(p) is None

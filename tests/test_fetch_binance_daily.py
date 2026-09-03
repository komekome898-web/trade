"""Tests for scripts/fetch_binance_daily.py — Binance daily futures metrics
+ USDJPY reference rate collector. All network is stubbed: tests never call
requests.get for real."""
from __future__ import annotations

import csv
import io
import sys
import zipfile
from datetime import date
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import fetch_binance_daily as m  # noqa: E402


def _zip_bytes(rows: list[dict[str, str]]) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["create_time", "symbol", *m.METRICS_COLS])
    w.writeheader()
    for r in rows:
        w.writerow(r)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as zf:
        zf.writestr("BTCUSDT-metrics-2026-08-01.csv", buf.getvalue())
    return out.getvalue()


def _metrics_row(oi="100.0", oiv="200.0"):
    return {"create_time": "2026-08-01 00:00:00", "symbol": "BTCUSDT",
            "sum_open_interest": oi, "sum_open_interest_value": oiv,
            "count_toptrader_long_short_ratio": "", "sum_toptrader_long_short_ratio": "1.5",
            "count_long_short_ratio": "2.0", "sum_taker_long_short_vol_ratio": "0.9"}


# ---- pure parsing / aggregation --------------------------------------------
def test_parse_metrics_zip_reads_the_csv_inside():
    content = _zip_bytes([_metrics_row("100.0"), _metrics_row("200.0")])
    rows = m.parse_metrics_zip(content)
    assert len(rows) == 2
    assert rows[0]["sum_open_interest"] == "100.0"


def test_aggregate_daily_means_columns_and_leaves_missing_as_none():
    rows = [_metrics_row(oi="100.0"), _metrics_row(oi="300.0")]
    agg = m.aggregate_daily(rows)
    assert agg["sum_open_interest"] == pytest.approx(200.0)
    assert agg["sum_toptrader_long_short_ratio"] == pytest.approx(1.5)
    # every row had an empty count_toptrader_long_short_ratio cell
    assert agg["count_toptrader_long_short_ratio"] is None


# ---- metrics: backfill + self-heal -----------------------------------------
def test_update_metrics_backfills_30_days_on_first_run(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "METRICS_OUT", tmp_path / "metrics.csv")
    calls = []

    def fake_fetch(day):
        calls.append(day)
        return {"sum_open_interest": 1.0, "sum_open_interest_value": 2.0,
                "count_toptrader_long_short_ratio": None,
                "sum_toptrader_long_short_ratio": 3.0,
                "count_long_short_ratio": 4.0,
                "sum_taker_long_short_vol_ratio": 5.0}

    monkeypatch.setattr(m, "fetch_metrics_day", fake_fetch)
    fetched = m.update_metrics(today=date(2026, 9, 3))
    assert fetched == m.METRICS_BACKFILL_DAYS == len(calls)
    assert (tmp_path / "metrics.csv").exists()
    rows = m.load_metrics_csv(tmp_path / "metrics.csv")
    assert len(rows) == 30
    # the newest fetchable day is yesterday (today's UTC day is not published yet)
    assert "20260902" in rows and "20260903" not in rows
    assert rows["20260902"]["sum_open_interest"] == "1.0"
    assert rows["20260902"]["count_toptrader_long_short_ratio"] == ""


def test_update_metrics_self_heals_only_the_missing_day(tmp_path, monkeypatch):
    """A second run with one day already on disk re-fetches only the gap —
    the existing safety-net behaviour the rest of this repo's fetch_* scripts
    share (see fetch_attention.py's start_for)."""
    out = tmp_path / "metrics.csv"
    monkeypatch.setattr(m, "METRICS_OUT", out)
    m.write_metrics_csv(out, {"20260902": {"date": "20260902", "sum_open_interest": "9"}})

    calls = []

    def fake_fetch(day):
        calls.append(day)
        return {"sum_open_interest": 1.0, "sum_open_interest_value": 2.0,
                "count_toptrader_long_short_ratio": 1.0,
                "sum_toptrader_long_short_ratio": 1.0,
                "count_long_short_ratio": 1.0, "sum_taker_long_short_vol_ratio": 1.0}

    monkeypatch.setattr(m, "fetch_metrics_day", fake_fetch)
    fetched = m.update_metrics(today=date(2026, 9, 3))
    assert fetched == m.METRICS_BACKFILL_DAYS - 1
    assert date(2026, 9, 2) not in calls
    rows = m.load_metrics_csv(out)
    # the pre-existing row is untouched, not overwritten by the re-scan
    assert rows["20260902"]["sum_open_interest"] == "9"


def test_update_metrics_prints_and_skips_on_a_failed_day(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(m, "METRICS_OUT", tmp_path / "metrics.csv")

    def flaky_fetch(day):
        if day == date(2026, 9, 2):
            raise requests.RequestException("boom")
        return None  # every other day: no rows published, quietly skipped

    monkeypatch.setattr(m, "fetch_metrics_day", flaky_fetch)
    fetched = m.update_metrics(today=date(2026, 9, 3))
    assert fetched == 0
    out = capsys.readouterr().out
    assert "0 rows" in out  # summary line still prints


# ---- usdjpy: full backfill then top-up -------------------------------------
def test_update_usdjpy_full_backfill_when_no_file_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "USDJPY_OUT", tmp_path / "usdjpy.csv")
    seen_start = {}

    def fake_fetch(start):
        seen_start["start"] = start
        return {"20260901": 148.5, "20260902": 149.0}

    monkeypatch.setattr(m, "fetch_usdjpy", fake_fetch)
    updated = m.update_usdjpy(today=date(2026, 9, 3))
    assert seen_start["start"] == m.FRANKFURTER_START
    assert updated == 2
    rows = m.load_usdjpy_csv(tmp_path / "usdjpy.csv")
    assert rows["20260901"] == "148.5000"


def test_update_usdjpy_tops_up_the_last_14_days_when_file_exists(tmp_path, monkeypatch):
    out = tmp_path / "usdjpy.csv"
    monkeypatch.setattr(m, "USDJPY_OUT", out)
    m.write_usdjpy_csv(out, {"20150101": "120.0000"})
    seen_start = {}

    def fake_fetch(start):
        seen_start["start"] = start
        return {}

    monkeypatch.setattr(m, "fetch_usdjpy", fake_fetch)
    m.update_usdjpy(today=date(2026, 9, 3))
    assert seen_start["start"] == "2026-08-20"  # today - 14 days
    # old history untouched
    rows = m.load_usdjpy_csv(out)
    assert rows["20150101"] == "120.0000"


def test_update_usdjpy_prints_and_keeps_existing_rows_on_fetch_failure(tmp_path, monkeypatch, capsys):
    out = tmp_path / "usdjpy.csv"
    monkeypatch.setattr(m, "USDJPY_OUT", out)
    m.write_usdjpy_csv(out, {"20260101": "150.0000"})

    def fake_fetch(start):
        raise requests.RequestException("network down")

    monkeypatch.setattr(m, "fetch_usdjpy", fake_fetch)
    updated = m.update_usdjpy(today=date(2026, 9, 3))
    assert updated == 0
    out_text = capsys.readouterr().out
    assert "usdjpy fetch failed" in out_text
    rows = m.load_usdjpy_csv(out)
    assert rows["20260101"] == "150.0000"


# ---- _get: retry + backoff, prints on final failure ------------------------
def test_get_retries_three_times_then_prints_and_raises(monkeypatch, capsys):
    calls = []

    class Boom:
        def raise_for_status(self):
            raise requests.HTTPError("500")

    def fake_get(url, headers=None, timeout=None):
        calls.append(url)
        raise requests.ConnectionError("refused")

    monkeypatch.setattr(m.requests, "get", fake_get)
    monkeypatch.setattr(m.time, "sleep", lambda s: None)
    with pytest.raises(requests.ConnectionError):
        m._get("https://example.invalid/x")
    assert len(calls) == m.FETCH_TRIES
    printed = capsys.readouterr().out
    assert "failed after 3 tries" in printed


def test_get_succeeds_on_a_later_attempt_without_printing(monkeypatch, capsys):
    attempts = {"n": 0}

    class Ok:
        def raise_for_status(self):
            pass

        content = b"payload"

    def fake_get(url, headers=None, timeout=None):
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise requests.ConnectionError("refused")
        return Ok()

    monkeypatch.setattr(m.requests, "get", fake_get)
    monkeypatch.setattr(m.time, "sleep", lambda s: None)
    assert m._get("https://example.invalid/x") == b"payload"
    assert attempts["n"] == 2
    assert capsys.readouterr().out == ""

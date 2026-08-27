"""Tests for scripts/record_venues.py — multi-venue public recorder.

All network is mocked (a FakeSession routed by URL substring); payload
fixtures reproduce the documented response shapes of bitbank
(public.bitbank.cc), GMO Coin (api.coin.z.com/public/v1) and bitFlyer
(api.bitflyer.com/v1).
"""
from __future__ import annotations

import csv
import gzip
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import record_venues as rv  # noqa: E402


# ---- mock plumbing ---------------------------------------------------------
class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeSession:
    """Routes GET by URL substring. Values: payload dict or Exception."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        for needle, payload in self.routes.items():
            if needle in url:
                if isinstance(payload, Exception):
                    raise payload
                return FakeResponse(payload)
        raise AssertionError(f"unrouted URL: {url}")


def bitbank_ticker_payload(ts_ms=1787788800123):  # 2026-08-27T00:00:00.123Z
    return {"success": 1, "data": {"sell": "16500100", "buy": "16500000",
                                   "high": "1", "low": "1", "open": "1",
                                   "last": "16500050", "vol": "100.1",
                                   "timestamp": ts_ms}}


def bitbank_tx_payload(ids, ts_ms=1787788800123):
    return {"success": 1, "data": {"transactions": [
        {"transaction_id": i, "side": "buy", "price": "16500000",
         "amount": "0.01", "executed_at": ts_ms + i} for i in ids]}}


def gmo_ticker_payload():
    return {"status": 0, "data": [
        {"ask": "16500200", "bid": "16500100", "high": "1", "last": "16500150",
         "low": "1", "symbol": "BTC", "timestamp": "2026-08-27T00:00:00.123Z",
         "volume": "50.1"},
        {"ask": "16500300", "bid": "16500200", "high": "1", "last": "16500250",
         "low": "1", "symbol": "BTC_JPY",
         "timestamp": "2026-08-27T00:00:00.456Z", "volume": "900.2"},
        # pre-open / halted symbol: empty quotes must be skipped, not crash
        {"ask": "", "bid": "", "high": "", "last": "", "low": "",
         "symbol": "NEW", "timestamp": "2026-08-27T00:00:00.789Z",
         "volume": "0"},
    ], "responsetime": "2026-08-27T00:00:00.999Z"}


def gmo_trades_payload():
    return {"status": 0, "data": {"pagination": {"currentPage": 1, "count": 100},
                                  "list": [  # newest first, as documented
        {"price": "16500200", "side": "SELL", "size": "0.02",
         "timestamp": "2026-08-27T00:00:02.000Z"},
        {"price": "16500100", "side": "BUY", "size": "0.01",
         "timestamp": "2026-08-27T00:00:01.000Z"},
    ]}, "responsetime": "2026-08-27T00:00:03.000Z"}


def bitflyer_ticker_payload():
    return {"product_code": "BTC_JPY", "state": "RUNNING",
            "timestamp": "2026-08-27T00:00:00.1234567",  # naive UTC, 7-digit
            "tick_id": 1, "best_bid": 16400000.0, "best_ask": 16400100.0,
            "best_bid_size": 0.1, "best_ask_size": 0.2, "ltp": 16400050.0,
            "volume": 1.0}


def read_gz_csv(path):
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        return list(csv.reader(f))


# ---- GMO rate ceiling (static) --------------------------------------------
def test_gmo_total_request_rate_stays_below_half_req_per_sec():
    """Measured GMO throttle is ~1 req/s (ERR-5003 beyond); the recorder
    commits to < 0.5 req/s total across ALL its GMO streams."""
    rate = 1.0 / rv.GMO_TICKER_INTERVAL + 1.0 / rv.GMO_TRADES_INTERVAL
    assert rate == pytest.approx(rv.GMO_REQS_PER_SEC)
    assert rv.GMO_REQS_PER_SEC < 0.5
    # and the streams actually use those intervals
    by_name = {s.name: s.interval for s in rv.VenueRecorder(session=FakeSession({})).streams}
    assert by_name["gmo-ticker"] == rv.GMO_TICKER_INTERVAL == 10.0
    assert by_name["gmo-trades"] == rv.GMO_TRADES_INTERVAL == 30.0


def test_lead_chosen_cadences_are_pinned():
    by_name = {s.name: s.interval for s in rv.VenueRecorder(session=FakeSession({})).streams}
    assert by_name == {"bitbank-ticker": 5.0, "bitbank-trades": 15.0,
                       "gmo-ticker": 10.0, "gmo-trades": 30.0,
                       "bitflyer-ticker": 10.0}


# ---- parsers ---------------------------------------------------------------
def test_parse_bitbank_ticker():
    row = rv.parse_bitbank_ticker(bitbank_ticker_payload(), "btc_jpy")
    ts, venue, pair, bid, ask, last = row
    assert (venue, pair) == ("bitbank", "btc_jpy")
    assert (bid, ask, last) == ("16500000", "16500100", "16500050")  # buy=bid
    assert ts.startswith("2026-08-2") and ts.endswith("+00:00")


def test_parse_bitbank_ticker_error_status_raises():
    with pytest.raises(RuntimeError):
        rv.parse_bitbank_ticker({"success": 0, "data": {"code": 10000}}, "btc_jpy")


def test_parse_bitbank_ticker_malformed_returns_none():
    assert rv.parse_bitbank_ticker({"success": 1, "data": {"buy": "x"}},
                                   "btc_jpy") is None


def test_parse_bitbank_transactions_chronological():
    rows = rv.parse_bitbank_transactions(bitbank_tx_payload([3, 1, 2]))
    assert [r[4] for r in rows] == ["1", "2", "3"]
    assert all(r[3] == "BUY" for r in rows)


def test_parse_gmo_ticker_all_symbols_and_skips_malformed():
    rows = rv.parse_gmo_ticker(gmo_ticker_payload())
    assert [(r[1], r[2]) for r in rows] == [("gmo", "BTC"), ("gmo", "BTC_JPY")]
    assert rows[0][3] == "16500100" and rows[0][4] == "16500200"


def test_parse_gmo_error_status_raises():
    err = {"status": 5, "messages": [{"message_code": "ERR-5003",
                                     "message_string": "Requests are too many"}]}
    with pytest.raises(RuntimeError, match="ERR-5003"):
        rv.parse_gmo_ticker(err)
    with pytest.raises(RuntimeError, match="ERR-5003"):
        rv.parse_gmo_trades(err)


def test_parse_gmo_trades_chronological_with_stable_tid():
    rows = rv.parse_gmo_trades(gmo_trades_payload())
    assert [r[1] for r in rows] == ["16500100", "16500200"]  # reversed to chrono
    assert [r[3] for r in rows] == ["BUY", "SELL"]
    again = rv.parse_gmo_trades(gmo_trades_payload())
    assert [r[4] for r in rows] == [r[4] for r in again]      # deterministic
    assert len(set(r[4] for r in rows)) == 2                  # and distinct


def test_parse_bitflyer_ticker_naive_utc_and_long_fraction():
    row = rv.parse_bitflyer_ticker(bitflyer_ticker_payload())
    assert row[1:3] == ["bitflyer", "BTC_JPY"]
    assert row[0] == "2026-08-27T00:00:00.123+00:00"
    assert rv.parse_bitflyer_ticker({"state": "RUNNING"}) is None


# ---- recorder end-to-end on mocks -----------------------------------------
def all_routes():
    return {
        "public.bitbank.cc/btc_jpy/ticker": bitbank_ticker_payload(),
        "public.bitbank.cc/xrp_jpy/ticker": bitbank_ticker_payload(),
        "public.bitbank.cc/btc_jpy/transactions": bitbank_tx_payload([1, 2]),
        "public.bitbank.cc/xrp_jpy/transactions": bitbank_tx_payload([10]),
        "api.coin.z.com/public/v1/ticker": gmo_ticker_payload(),
        "api.coin.z.com/public/v1/trades": gmo_trades_payload(),
        "api.bitflyer.com/v1/ticker": bitflyer_ticker_payload(),
    }


def tick_all_once(rec):
    for s in rec.streams:
        s.fn()


def test_one_round_of_ticks_writes_all_files(tmp_path):
    rec = rv.VenueRecorder(out_dir=tmp_path, session=FakeSession(all_routes()))
    tick_all_once(rec)
    rec.flush_all()
    quotes = sorted(tmp_path.glob("quotes_*.csv.gz"))
    assert len(quotes) == 1
    rows = read_gz_csv(quotes[0])
    assert rows[0] == rv.QUOTE_FIELDS
    venues = {(r[1], r[2]) for r in rows[1:]}
    assert venues == {("bitbank", "btc_jpy"), ("bitbank", "xrp_jpy"),
                      ("gmo", "BTC"), ("gmo", "BTC_JPY"),
                      ("bitflyer", "BTC_JPY")}
    trade_files = {p.name.rsplit("_", 1)[0] for p in tmp_path.glob("trades_*.csv.gz")}
    # first gmo-trades tick polls only the FIRST symbol of the rotation
    assert trade_files == {"trades_bitbank_btc_jpy", "trades_bitbank_xrp_jpy",
                           "trades_gmo_btc"}
    tid_rows = read_gz_csv(next(tmp_path.glob("trades_bitbank_btc_jpy_*.csv.gz")))
    assert tid_rows[0] == rv.TRADE_FIELDS
    assert [r[4] for r in tid_rows[1:]] == ["1", "2"]


def test_gmo_trades_alternates_symbols(tmp_path):
    fake = FakeSession(all_routes())
    rec = rv.VenueRecorder(out_dir=tmp_path, session=fake)
    rec._tick_gmo_trades()
    rec._tick_gmo_trades()
    symbols = [p["symbol"] for u, p in fake.calls if "trades" in u]
    assert symbols == ["BTC", "BTC_JPY"]


def test_tid_dedup_within_a_run(tmp_path):
    rec = rv.VenueRecorder(out_dir=tmp_path, session=FakeSession({}))
    rows = rv.parse_bitbank_transactions(bitbank_tx_payload([1, 2, 3]))
    rec._add_trades("bitbank", "btc_jpy", rows)
    rec._add_trades("bitbank", "btc_jpy", rows)  # same poll again
    rec._add_trades("bitbank", "btc_jpy",
                    rv.parse_bitbank_transactions(bitbank_tx_payload([3, 4])))
    rec.flush_all()
    out = read_gz_csv(next(tmp_path.glob("trades_bitbank_btc_jpy_*.csv.gz")))
    assert [r[4] for r in out[1:]] == ["1", "2", "3", "4"]


def test_restart_restores_tids_from_todays_file(tmp_path):
    ts_ms = int(__import__("datetime").datetime.now(
        __import__("datetime").timezone.utc).timestamp() * 1000)
    rec1 = rv.VenueRecorder(out_dir=tmp_path, session=FakeSession({}))
    rec1._add_trades("bitbank", "btc_jpy",
                     rv.parse_bitbank_transactions(bitbank_tx_payload([1, 2], ts_ms)))
    rec1.flush_all()
    # new process: overlapping window [2,3] must only add 3
    rec2 = rv.VenueRecorder(out_dir=tmp_path, session=FakeSession({}))
    rec2._add_trades("bitbank", "btc_jpy",
                     rv.parse_bitbank_transactions(bitbank_tx_payload([2, 3], ts_ms)))
    rec2.flush_all()
    out = read_gz_csv(next(tmp_path.glob("trades_bitbank_btc_jpy_*.csv.gz")))
    assert [r[4] for r in out[1:]] == ["1", "2", "3"]


def test_restart_tolerates_truncated_gz_tail(tmp_path):
    ts_ms = int(__import__("datetime").datetime.now(
        __import__("datetime").timezone.utc).timestamp() * 1000)
    rec1 = rv.VenueRecorder(out_dir=tmp_path, session=FakeSession({}))
    rec1._add_trades("bitbank", "btc_jpy",
                     rv.parse_bitbank_transactions(bitbank_tx_payload([1, 2], ts_ms)))
    rec1.flush_all()
    path = next(tmp_path.glob("trades_bitbank_btc_jpy_*.csv.gz"))
    path.write_bytes(path.read_bytes() + b"\x1f\x8b\x08\x00trunc")  # torn member
    rec2 = rv.VenueRecorder(out_dir=tmp_path, session=FakeSession({}))
    writer, tids = rec2._trades_writer("bitbank", "btc_jpy")  # restore runs here
    assert not tids.add("1") and not tids.add("2")   # both remembered
    assert tids.add("3")                              # new one accepted


def test_day_rollover_splits_files_by_utc_date(tmp_path):
    rec = rv.VenueRecorder(out_dir=tmp_path, session=FakeSession({}))
    rec._add_quote(["2026-08-27T23:59:59.900+00:00", "bitflyer", "BTC_JPY",
                    1, 2, 1])
    rec._add_quote(["2026-08-28T00:00:00.100+00:00", "bitflyer", "BTC_JPY",
                    1, 2, 1])
    rec.flush_all()
    names = sorted(p.name for p in tmp_path.glob("quotes_*.csv.gz"))
    assert names == ["quotes_20260827.csv.gz", "quotes_20260828.csv.gz"]
    for name in names:
        rows = read_gz_csv(tmp_path / name)
        assert rows[0] == rv.QUOTE_FIELDS and len(rows) == 2


def test_flush_appends_readable_gzip_members(tmp_path):
    """Multi-member concatenation (extract_tape style): a second flush appends
    a new member and gzip.open('rt') reads them back as one stream, with the
    header written only once."""
    rec = rv.VenueRecorder(out_dir=tmp_path, session=FakeSession({}))
    rec._add_quote(["2026-08-27T00:00:00.000+00:00", "gmo", "BTC", 1, 2, 1])
    rec.flush_all()
    rec._add_quote(["2026-08-27T00:00:10.000+00:00", "gmo", "BTC", 1, 2, 1])
    rec.flush_all()
    rows = read_gz_csv(tmp_path / "quotes_20260827.csv.gz")
    assert len(rows) == 3 and rows[0] == rv.QUOTE_FIELDS


def test_one_failing_venue_does_not_write_and_does_not_block_others(tmp_path):
    routes = all_routes()
    routes["api.coin.z.com/public/v1/ticker"] = {"status": 5, "messages": [
        {"message_code": "ERR-5003"}]}
    routes["public.bitbank.cc/btc_jpy/ticker"] = ConnectionError("down")
    rec = rv.VenueRecorder(out_dir=tmp_path, session=FakeSession(routes))
    for s in rec.streams:
        try:
            s.fn()
        except Exception:
            pass  # the stream loop logs and backs off; others keep going
    rec.flush_all()
    rows = read_gz_csv(next(tmp_path.glob("quotes_*.csv.gz")))
    venues = {(r[1], r[2]) for r in rows[1:]}
    assert ("bitflyer", "BTC_JPY") in venues
    assert ("gmo", "BTC") not in venues


# ---- deploy wiring ---------------------------------------------------------
def test_deploy_bats_carry_the_venue_recorder():
    deploy = Path(__file__).resolve().parents[1] / "deploy"
    start = (deploy / "start_all.bat").read_text(encoding="utf-8")
    assert 'call :launch "venue-recorder" "scripts\\record_venues.py"' in start
    for bat in ("stop_all.bat", "restart_all.bat"):
        assert "*record_venues.py*" in (deploy / bat).read_text(encoding="utf-8"), bat
    share = (deploy / "share_logs.bat").read_text(encoding="utf-8")
    assert "data\\venues\\*.csv.gz" in share and "paper_logs\\venues\\" in share

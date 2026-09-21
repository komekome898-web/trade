"""2026-09-21(L-325)の穴埋め道具 2 本の、通信を伴わない部分の試験。"""
from __future__ import annotations

import csv
import gzip
import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


bf = _load("fetch_bitflyer_executions_range")
ca = _load("fetch_coinalyze_liquidations")


def test_parse_ts_accepts_bitflyer_precisions():
    assert bf.parse_ts("2026-09-21T01:20:01.573") == datetime(2026, 9, 21, 1, 20, 1, 573000, tzinfo=timezone.utc)
    assert bf.parse_ts("2026-09-21T01:20:01.5") == datetime(2026, 9, 21, 1, 20, 1, 500000, tzinfo=timezone.utc)
    assert bf.parse_ts("2026-09-21T01:20:01Z") == datetime(2026, 9, 21, 1, 20, 1, tzinfo=timezone.utc)
    assert bf.parse_ts("2026-09-18T07:24:44.9409572Z").microsecond == 940957


def test_daywriter_keeps_identical_fills_and_merges_by_id(tmp_path):
    w = bf.DayWriter(tmp_path)
    # 古い方へ進む順で足す(API の並び)。同じ ts/price/size/side の約定 2 件(id 違い)は 2 行残る
    w.add(bf.parse_ts("2026-09-21T01:20:03.97"), ("2026-09-21T01:20:03.97", 100.0, 0.01, "SELL", 3))
    w.add(bf.parse_ts("2026-09-21T01:20:01.573"), ("2026-09-21T01:20:01.573", 100.0, 0.01, "SELL", 2))
    w.add(bf.parse_ts("2026-09-21T01:20:01.573"), ("2026-09-21T01:20:01.573", 100.0, 0.01, "SELL", 1))
    w.add(bf.parse_ts("2026-09-20T23:59:59.1"), ("2026-09-20T23:59:59.1", 99.0, 0.02, "BUY", 0))
    w.flush()
    p21 = tmp_path / "executions_20260921.csv.gz"
    p20 = tmp_path / "executions_20260920.csv.gz"
    assert p21.exists() and p20.exists()
    with gzip.open(p21, "rt", newline="") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == ["ts", "price", "size", "side", "id"]
    assert [r[4] for r in rows[1:]] == ["1", "2", "3"]          # 時刻順、同時刻は id 順
    # 続きからの再実行: 同じ id を足しても増えない、新しい id は増える
    w2 = bf.DayWriter(tmp_path)
    w2.add(bf.parse_ts("2026-09-21T01:20:05"), ("2026-09-21T01:20:05", 101.0, 0.03, "BUY", 4))
    w2.add(bf.parse_ts("2026-09-21T01:20:03.97"), ("2026-09-21T01:20:03.97", 100.0, 0.01, "SELL", 3))
    w2.flush()
    with gzip.open(p21, "rt", newline="") as fh:
        rows = list(csv.reader(fh))
    assert [r[4] for r in rows[1:]] == ["1", "2", "3", "4"]
    assert w2.written["20260921"] == 4


def test_coinalyze_resolve_markets_filters_perpetual_btc(monkeypatch):
    calls = []

    def fake_get(session, key, path, params=None, retries=5):
        calls.append(path)
        if path == "/exchanges":
            return 200, [{"name": "Bybit", "code": "6"}, {"name": "OKX", "code": "3"},
                         {"name": "Binance", "code": "A"}]
        if path == "/future-markets":
            return 200, [
                {"symbol": "BTCUSDT_PERP.6", "exchange": "6", "symbol_on_exchange": "BTCUSDT",
                 "base_asset": "BTC", "quote_asset": "USDT", "is_perpetual": True},
                {"symbol": "BTCUSDT_PERP.3", "exchange": "3", "symbol_on_exchange": "BTC-USDT-SWAP",
                 "base_asset": "BTC", "quote_asset": "USDT", "is_perpetual": True},
                {"symbol": "BTCUSD_260925.3", "exchange": "3", "symbol_on_exchange": "BTC-USD-260925",
                 "base_asset": "BTC", "quote_asset": "USD", "is_perpetual": False},
                {"symbol": "ETHUSDT_PERP.6", "exchange": "6", "symbol_on_exchange": "ETHUSDT",
                 "base_asset": "ETH", "quote_asset": "USDT", "is_perpetual": True},
                {"symbol": "BTCUSDT_PERP.A", "exchange": "A", "symbol_on_exchange": "BTCUSDT",
                 "base_asset": "BTC", "quote_asset": "USDT", "is_perpetual": True},
            ]
        raise AssertionError(path)

    monkeypatch.setattr(ca, "get", fake_get)
    monkeypatch.setattr(ca.time, "sleep", lambda s: None)
    out = ca.resolve_markets(None, "k", ["bybit", "okx"], "BTC", ("USDT", "USD"))
    assert sorted(m["symbol"] for m in out) == ["BTCUSDT_PERP.3", "BTCUSDT_PERP.6"]
    assert {m["exchange_name"] for m in out} == {"Bybit", "OKX"}
    assert calls == ["/exchanges", "/future-markets"]


def test_coinalyze_load_key_reads_dotenv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("COINALYZE_API_KEY", raising=False)
    (tmp_path / ".env").write_text('OTHER=1\nCOINALYZE_API_KEY="abc123"\n', encoding="utf-8")
    assert ca.load_key() == "abc123"

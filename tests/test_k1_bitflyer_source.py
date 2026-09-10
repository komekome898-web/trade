"""K1 フレッシュ確認 — bitFlyer ソース(`FRESH_BITFLYER_PREREG.md` §7 手 2)。

`k1_source.load_bars('bitflyer', ...)` が 1 分足で `fold()` に対して恒等であること
(binance 用のテストが無いのでここが手本になる)、時刻が単調増加であること、
分の境界(60 秒)に揺れていないことを、実データの小さな範囲で確認する。
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import k1_source  # noqa: E402
import measure_katsuo_dispersion as base  # noqa: E402

DATA_PRESENT = k1_source.bitflyer_file(2017).exists()

pytestmark = pytest.mark.skipif(not DATA_PRESENT, reason="backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/ 未取得")


def test_fold_is_identity_on_1m_row_count_and_ohlc():
    rows = k1_source.load_bars("bitflyer", date(2017, 1, 1), date(2017, 1, 1))
    bars1 = base.fold(rows, 1)
    assert len(bars1) == len(rows)
    assert all(a[1:] == b[1:] for a, b in zip(rows, bars1))
    assert k1_source.last_load["source"] == "bitflyer"
    assert k1_source.last_load["dropped_null_ohlc"] >= 0


def test_timestamps_strictly_increasing():
    rows = k1_source.load_bars("bitflyer", date(2017, 1, 1), date(2017, 1, 2))
    ts = [r[0] for r in rows]
    assert all(b > a for a, b in zip(ts, ts[1:]))


def test_minutes_aligned_to_60s():
    rows = k1_source.load_bars("bitflyer", date(2017, 1, 1), date(2017, 1, 1))
    assert rows, "データが無い"
    assert all(r[0] % 60 == 0 for r in rows)


def test_null_ohlc_rows_are_dropped():
    """2017-01-01 19:00〜19:03 UTC は約定 0(null OHLC、目視確認済み)。含まれていないこと。"""
    rows = k1_source.load_bars("bitflyer", date(2017, 1, 1), date(2017, 1, 1))
    from datetime import datetime, timezone
    null_ts = int(datetime(2017, 1, 1, 19, 0, tzinfo=timezone.utc).timestamp())
    assert null_ts not in [r[0] for r in rows]


def test_not_gated_by_the_bitmex_seal():
    """bitmex 専用の封印は bitflyer の既定区間(2026-08-31 まで)をガードしない。"""
    import argparse
    args = argparse.Namespace(source="bitflyer", start=None, end=None, open_seal=False)
    start, end = k1_source.resolve_range(args)
    assert end == k1_source.default_end("bitflyer") == date(2026, 8, 31)
    assert start == k1_source.default_start("bitflyer") == date(2017, 1, 1)

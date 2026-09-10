"""K1 取引所横断 段階 2 — Bybit ソース(`XVENUE_PREREG.md` §2 段階 2、L-095)。

`k1_source.load_bars('bybit', ...)` が 1 分足で `fold()` に対して恒等であること、時刻が
単調増加・分の境界(60 秒)に揺れていないこと(`test_k1_bitflyer_source.py` と同じ手本)、
加えて `fetch_bybit_minutes.fold_trades_to_minutes()`(約定→分の畳み込み)自体の単体テストを
合成データで確認する。
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import fetch_bybit_minutes as fb  # noqa: E402
import k1_source  # noqa: E402
import measure_katsuo_dispersion as base  # noqa: E402

DATA_PRESENT = k1_source.bybit_file(2022).exists()

pytestmark_data = pytest.mark.skipif(not DATA_PRESENT, reason="backtest_data/bybit_BTCUSDT_1m_20260910/ 未取得")


@pytestmark_data
def test_fold_is_identity_on_1m_row_count_and_ohlc():
    rows = k1_source.load_bars("bybit", date(2022, 1, 1), date(2022, 1, 1))
    bars1 = base.fold(rows, 1)
    assert len(bars1) == len(rows)
    assert all(a[1:] == b[1:] for a, b in zip(rows, bars1))
    assert k1_source.last_load["source"] == "bybit"
    assert k1_source.last_load["dropped_null_ohlc"] == 0


@pytestmark_data
def test_timestamps_strictly_increasing():
    rows = k1_source.load_bars("bybit", date(2022, 1, 1), date(2022, 1, 2))
    ts = [r[0] for r in rows]
    assert all(b > a for a, b in zip(ts, ts[1:]))


@pytestmark_data
def test_minutes_aligned_to_60s():
    rows = k1_source.load_bars("bybit", date(2022, 1, 1), date(2022, 1, 1))
    assert rows, "データが無い"
    assert all(r[0] % 60 == 0 for r in rows)


def test_not_gated_by_the_bitmex_seal():
    """bitmex 専用の封印は bybit の既定区間(2026-08-31 まで)をガードしない。"""
    import argparse
    args = argparse.Namespace(source="bybit", start=None, end=None, open_seal=False)
    start, end = k1_source.resolve_range(args)
    assert end == k1_source.default_end("bybit") == date(2026, 8, 31)
    assert start == k1_source.default_start("bybit") == date(2022, 1, 1)


# ---------------------------------------------------------------------------
# fold_trades_to_minutes: 合成約定リストでの単体テスト(データ有無に依存しない)
# ---------------------------------------------------------------------------

def test_fold_trades_open_high_low_close():
    """1 分に複数約定: open=最初、high=最大、low=最小、close=最後。"""
    trades = [
        (1000.0, 100.0),   # minute 960 (1000 // 60 * 60 = 960)
        (1005.0, 105.0),
        (1010.0, 95.0),
        (1015.0, 102.0),   # 最後の約定 → close
    ]
    bars = fb.fold_trades_to_minutes(trades)
    assert len(bars) == 1
    minute, o, h, l, c = bars[0]
    assert minute == 960
    assert (o, h, l, c) == (100.0, 105.0, 95.0, 102.0)


def test_fold_trades_multiple_minutes_and_gap():
    """複数の分にわたる約定 + 約定の無い分(gap)は出力に現れない。"""
    trades = [
        (0.0, 10.0), (30.0, 12.0), (59.0, 11.0),      # minute 0
        # minute 60 の約定は無い(gap)
        (125.0, 20.0), (130.0, 25.0), (180.0, 18.0),  # minute 120 と 180 に分裂
    ]
    bars = fb.fold_trades_to_minutes(trades)
    minutes = [b[0] for b in bars]
    assert minutes == [0, 120, 180]
    assert bars[0][1:] == (10.0, 12.0, 10.0, 11.0)   # minute 0: o=10 h=12 l=10 c=11
    assert bars[1][1:] == (20.0, 25.0, 20.0, 25.0)   # minute 120: o=20 h=25 l=20 c=25
    assert bars[2][1:] == (18.0, 18.0, 18.0, 18.0)   # minute 180: 単一約定


def test_fold_trades_ties_same_timestamp_use_file_order():
    """同一タイムスタンプの複数約定は入力の出現順を「最初/最後」の基準にする。"""
    trades = [(60.0, 50.0), (60.0, 55.0), (60.0, 52.0)]
    bars = fb.fold_trades_to_minutes(trades)
    assert len(bars) == 1
    _minute, o, h, l, c = bars[0]
    assert (o, h, l, c) == (50.0, 55.0, 50.0, 52.0)


def test_fold_trades_empty_input():
    assert fb.fold_trades_to_minutes([]) == []


def test_kline_offset_correction_matches_measured_utc_plus_3():
    """`correct_kline_timestamp` は -3h 補正(本ファイルの docstring / fetch_bybit_minutes 実測)。"""
    from datetime import datetime
    dt_broker = datetime(2024, 12, 31, 3, 0)  # ブローカー時間 03:00 → UTC 00:00
    ts = fb.correct_kline_timestamp(dt_broker)
    from datetime import timezone
    assert datetime.fromtimestamp(ts, tz=timezone.utc) == datetime(2024, 12, 31, 0, 0, tzinfo=timezone.utc)

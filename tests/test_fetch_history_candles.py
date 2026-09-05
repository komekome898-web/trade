"""Tests for the 1-minute candle builders in scripts/fetch_history.py and
scripts/fetch_deep.py.

DATA QA 2026-09-05 (docs/DATA_QA_TRIAGE.md candles_fx_btc_jpy/zero_volume):
data/candles_FX_BTC_JPY.csv has zero_volume rows whose open/high/low/close
are NON-flat -- reproduced here as the exact output of fetch_deep.py's old
ffill(open/high/low/close) + fillna(volume, 0.0), which independently
forward-fills each OHLC column from the previous real candle (reproducing
its shape) while zeroing volume, making a gap minute indistinguishable from
a real bar. Both builders now emit a `synthetic` flag (1 = fabricated gap
row, 0 = real) so callers can filter them; see build_candles docstrings.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import pandas as pd  # noqa: E402

import fetch_deep  # noqa: E402
import fetch_history  # noqa: E402


def _executions(rows):
    """rows: list of (exec_date, price, size) -> DataFrame like executions_*.csv."""
    return pd.DataFrame(
        [{"exec_date": d, "price": p, "size": s} for d, p, s in rows]
    )


# A 1-minute gap (16:01, 16:02 have no executions) between two real minutes.
GAPPED = _executions([
    ("2026-07-23T15:58:00.000", 100, 1),
    ("2026-07-23T15:59:30.000", 101, 1),
    ("2026-07-23T16:00:10.000", 105, 1),
    ("2026-07-23T16:00:40.000", 103, 1),
    ("2026-07-23T16:03:10.000", 110, 2),
])


def test_fetch_history_drops_gap_minutes_entirely():
    """fetch_history.py's builder never fabricates a bar: a minute with zero
    executions produces NO row at all (dropna on open), and every emitted
    row is real (synthetic == 0)."""
    candles = fetch_history.build_candles(GAPPED)
    ts = [str(t) for t in candles.index]
    assert "2026-07-23 16:01:00+00:00" not in ts
    assert "2026-07-23 16:02:00+00:00" not in ts
    assert len(candles) == 4
    assert (candles["synthetic"] == 0).all()


def test_fetch_deep_flags_gap_minutes_as_synthetic():
    """fetch_deep.py's builder forward-fills the gap (gapless series) but
    now marks those rows synthetic=1, distinguishing them from real bars."""
    candles = fetch_deep.build_candles(GAPPED)
    assert len(candles) == 6  # 15:58..16:03 inclusive, no holes

    gap1 = candles.loc["2026-07-23 16:01:00+00:00"]
    gap2 = candles.loc["2026-07-23 16:02:00+00:00"]
    real_prev = candles.loc["2026-07-23 16:00:00+00:00"]

    for gap in (gap1, gap2):
        assert gap["synthetic"] == 1
        assert gap["volume"] == 0.0
        # OHLC is carried forward from the previous real candle...
        assert gap["open"] == real_prev["open"]
        assert gap["high"] == real_prev["high"]
        assert gap["low"] == real_prev["low"]
        assert gap["close"] == real_prev["close"]
        # ...which is exactly why a synthetic row can have non-flat OHLC
        # (open != close, high != low) despite trading zero volume: this is
        # the root cause of the zero_volume/non-flat rows found in
        # data/candles_FX_BTC_JPY.csv.
        assert gap["open"] != gap["close"] or gap["high"] != gap["low"]

    real_rows = candles[candles["synthetic"] == 0]
    assert len(real_rows) == 4
    assert (real_rows["volume"] > 0).all()


def test_fetch_deep_real_rows_unaffected_by_flag():
    """Adding the synthetic column must not change any real bar's OHLCV."""
    candles = fetch_deep.build_candles(GAPPED)
    first = candles.loc["2026-07-23 15:58:00+00:00"]
    assert (first["open"], first["high"], first["low"], first["close"], first["volume"]) == (
        100.0, 100.0, 100.0, 100.0, 1,
    )


def test_no_gap_all_real_for_both_builders():
    contiguous = _executions([
        ("2026-07-23T16:00:10.000", 100, 1),
        ("2026-07-23T16:01:10.000", 101, 1),
        ("2026-07-23T16:02:10.000", 102, 1),
    ])
    for build in (fetch_history.build_candles, fetch_deep.build_candles):
        candles = build(contiguous)
        assert len(candles) == 3
        assert (candles["synthetic"] == 0).all()

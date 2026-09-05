"""Tests for scripts/build_flow.py's per-minute order-flow builder.

DATA QA 2026-09-05 (docs/DATA_QA_TRIAGE.md bitflyer_execution_flow/
maintenance_window+zero_volume): build_flow() forward-fills a minute with
zero executions from the previous real minute (open/high/low/close copied,
volume/buy_vol/sell_vol/trades zeroed) -- the exact same shape as the
already-fixed scripts/fetch_deep.py candle builder (see
tests/test_fetch_history_candles.py). `synthetic` (1 = forward-filled gap
minute, 0 = real) now marks these rows so a flat maintenance-window bar or
a zero-volume row isn't mistaken for a real quiet minute.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import pandas as pd  # noqa: E402

import build_flow  # noqa: E402


def _executions(rows):
    """rows: list of (exec_date, price, size, side) -> DataFrame like
    executions_<product>.csv."""
    return pd.DataFrame(
        [{"exec_date": d, "price": p, "size": s, "side": side} for d, p, s, side in rows]
    )


# A 1-minute gap (16:01, 16:02 have no executions) between two real minutes.
GAPPED = _executions([
    ("2026-07-23T15:58:00.000", 100, 1, "BUY"),
    ("2026-07-23T15:59:30.000", 101, 1, "SELL"),
    ("2026-07-23T16:00:10.000", 105, 1, "BUY"),
    ("2026-07-23T16:00:40.000", 103, 2, "SELL"),
    ("2026-07-23T16:03:10.000", 110, 2, "BUY"),
])


def test_gap_minutes_are_forward_filled_and_flagged_synthetic():
    flow = build_flow.build_flow(GAPPED)
    assert len(flow) == 6  # 15:58..16:03 inclusive, no holes (never dropped)

    gap1 = flow.loc["2026-07-23 16:01:00+00:00"]
    gap2 = flow.loc["2026-07-23 16:02:00+00:00"]
    real_prev = flow.loc["2026-07-23 16:00:00+00:00"]

    for gap in (gap1, gap2):
        assert gap["synthetic"] == 1
        assert gap["volume"] == 0.0
        assert gap["buy_vol"] == 0.0
        assert gap["sell_vol"] == 0.0
        assert gap["trades"] == 0.0
        # OHLC carried forward from the previous real minute -- which is
        # exactly why a synthetic row can have non-flat OHLC despite zero
        # volume/trades (the root cause of the maintenance_window/
        # zero_volume flags found on data/flow_FX_BTC_JPY.csv).
        assert gap["open"] == real_prev["open"]
        assert gap["close"] == real_prev["close"]

    real_rows = flow[flow["synthetic"] == 0]
    assert len(real_rows) == 4
    assert (real_rows["trades"] > 0).all()


def test_real_rows_unaffected_by_synthetic_flag():
    flow = build_flow.build_flow(GAPPED)
    first = flow.loc["2026-07-23 15:58:00+00:00"]
    assert first["synthetic"] == 0
    assert (first["open"], first["high"], first["low"], first["close"]) == (100.0, 100.0, 100.0, 100.0)
    assert first["buy_vol"] == 1.0
    assert first["sell_vol"] == 0.0


def test_buy_sell_split():
    minute = _executions([
        ("2026-07-23T16:00:00.000", 100, 1, "BUY"),
        ("2026-07-23T16:00:10.000", 101, 2, "SELL"),
        ("2026-07-23T16:00:20.000", 102, 3, "BUY"),
    ])
    flow = build_flow.build_flow(minute)
    row = flow.loc["2026-07-23 16:00:00+00:00"]
    assert row["buy_vol"] == 4.0
    assert row["sell_vol"] == 2.0
    assert row["volume"] == 6.0
    assert row["trades"] == 3.0
    assert row["synthetic"] == 0


def test_no_gap_all_real():
    contiguous = _executions([
        ("2026-07-23T16:00:10.000", 100, 1, "BUY"),
        ("2026-07-23T16:01:10.000", 101, 1, "SELL"),
        ("2026-07-23T16:02:10.000", 102, 1, "BUY"),
    ])
    flow = build_flow.build_flow(contiguous)
    assert len(flow) == 3
    assert (flow["synthetic"] == 0).all()

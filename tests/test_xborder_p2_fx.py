"""P2-08 control 5 — the yen-converted signal close (`xborder_p2_fx.jpy_close`).

USDJPY minutes are forward-filled onto the Binance minutes (last USDJPY close
at or before the minute), minutes before the first USDJPY bar are NaN, and
the fill report counts exactly what was filled.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.research.xborder_p2 import momentum_signal
from bot.research.xborder_p2_fx import jpy_close


def test_jpy_close_forward_fill_counts_and_momentum():
    idx = pd.date_range("2022-12-30 23:57", periods=8, freq="min", tz="UTC")   # crosses into Saturday
    bn = pd.Series([100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0], index=idx)
    # USDJPY: bars at minutes 1, 2, 3 only (0 = before the first bar; 4.. = weekend, no rows);
    # an extra USDJPY bar 30 s off-grid must not be picked as "exact"
    fx_idx = pd.DatetimeIndex([idx[1], idx[2], idx[3], idx[3] + pd.Timedelta(seconds=30)])
    fx = pd.Series([130.0, 131.0, 132.0, 132.5], index=fx_idx)
    out, rep = jpy_close(bn, fx)
    want = [np.nan, 101 * 130.0, 102 * 131.0, 103 * 132.0, 104 * 132.5, 105 * 132.5, 106 * 132.5, 107 * 132.5]
    np.testing.assert_allclose(out.to_numpy(), want, rtol=0, atol=1e-9)
    assert (out.index == idx).all()
    assert rep["n_minutes"] == 8 and rep["n_usdjpy_exact"] == 3 and rep["n_filled"] == 4 and rep["n_nan"] == 1
    assert rep["max_fill_age_min"] == pytest.approx(3.5)                     # minute 7 vs the 23:60:30 bar
    assert rep["n_filled_by_year"] == {2022: 4}
    # the momentum rule on the converted close: with a constant USDJPY the signal equals the USD one
    fx_flat = pd.Series(130.0, index=idx)
    flat, rep2 = jpy_close(bn, fx_flat)
    assert rep2["n_filled"] == 0 and rep2["n_nan"] == 0
    np.testing.assert_allclose(momentum_signal(flat, 1).to_numpy()[1:], momentum_signal(bn, 1).to_numpy()[1:], atol=1e-15)
    # a moving USDJPY changes m(t): m_jpy = (1 + m_usd)(1 + m_fx) − 1
    m_j = momentum_signal(out, 1).to_numpy()
    assert m_j[2] == pytest.approx((102 / 101) * (131 / 130) - 1)
    assert np.isnan(m_j[1])                                                 # previous close is NaN (before first USDJPY)
    with pytest.raises(ValueError):
        jpy_close(bn, pd.Series([np.nan], index=idx[:1]))

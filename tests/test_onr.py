"""Core-function tests for scripts/research_overnight_onr.py, on synthetic data.

Covers: overnight-return construction (r_t = ln(open(t+1)/close(t))), the
glitch filter, the fixed era split, and bootstrap determinism (same seed ->
identical CI). No network, no dependency on backtest_data/reit_onr_20260904/.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import research_overnight_onr as onr  # noqa: E402


def _ohlc(dates, opens, closes, highs=None, lows=None):
    n = len(dates)
    highs = highs or [max(o, c) for o, c in zip(opens, closes)]
    lows = lows or [min(o, c) for o, c in zip(opens, closes)]
    return pd.DataFrame({
        "date": pd.to_datetime(dates),
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
    })


def test_overnight_returns_formula_and_alignment():
    # close(t)=100 -> open(t+1)=110 => r = ln(1.1); dated at day t.
    df = _ohlc(
        ["2020-01-01", "2020-01-02", "2020-01-03"],
        opens=[100, 110, 95],
        closes=[100, 90, 95],
    )
    on = onr.overnight_returns(df)
    assert len(on) == 2  # last row has no next-day open
    assert on.loc[0, "date"] == pd.Timestamp("2020-01-01")
    assert np.isclose(on.loc[0, "r"], np.log(110 / 100))
    assert np.isclose(on.loc[1, "r"], np.log(95 / 90))


def test_intraday_returns_formula():
    df = _ohlc(["2020-01-01", "2020-01-02"], opens=[100, 200], closes=[105, 190])
    intra = onr.intraday_returns(df)
    assert np.isclose(intra.loc[0, "r"], np.log(105 / 100))
    assert np.isclose(intra.loc[1, "r"], np.log(190 / 200))


def test_glitch_filter_drops_only_large_moves():
    dates = pd.date_range("2020-01-01", periods=5, freq="D")
    r = pd.Series([0.01, -0.02, 0.15, -0.30, 0.03])  # two exceed 0.10 in abs
    df = pd.DataFrame({"date": dates, "r": r})
    kept, dropped = onr.drop_glitches(df, threshold=onr.GLITCH_ABS_LOG_RET)
    assert dropped == 2
    assert len(kept) == 3
    assert kept["r"].abs().max() <= onr.GLITCH_ABS_LOG_RET


def test_glitch_filter_default_threshold_matches_module_constant():
    df = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=2), "r": [0.10, 0.1000001]})
    kept, dropped = onr.drop_glitches(df)
    # exactly-0.10 is NOT dropped (strict >), a hair above IS
    assert dropped == 1
    assert len(kept) == 1


def test_era_table_fixed_boundaries_and_counts():
    dates = (
        list(pd.date_range("2005-01-01", periods=3, freq="365D"))  # -> era 2003-2008
        + list(pd.date_range("2010-01-01", periods=2, freq="365D"))  # -> era 2009-2014
        + list(pd.date_range("2022-01-01", periods=4, freq="200D"))  # -> era 2021-2026
    )
    r = np.linspace(-0.01, 0.01, len(dates))
    df = pd.DataFrame({"date": pd.to_datetime(dates), "r": r})
    rows = onr.era_table(df)
    by_label = {row["era"]: row for row in rows}
    assert [row["era"] for row in rows] == ["2003-2008", "2009-2014", "2015-2020", "2021-2026"]
    assert by_label["2003-2008"]["n"] == 3
    assert by_label["2009-2014"]["n"] == 2
    assert by_label["2015-2020"]["n"] == 0
    assert by_label["2021-2026"]["n"] == 4


def test_bootstrap_ci_is_deterministic_given_seed():
    rng = np.random.default_rng(1)
    x = rng.normal(loc=0.0005, scale=0.01, size=250)
    lo1, hi1 = onr.stationary_bootstrap_ci(x, mean_block=10, n_boot=500, seed=20260904)
    lo2, hi2 = onr.stationary_bootstrap_ci(x, mean_block=10, n_boot=500, seed=20260904)
    assert lo1 == lo2
    assert hi1 == hi2
    # a different seed generally gives a (slightly) different CI
    lo3, hi3 = onr.stationary_bootstrap_ci(x, mean_block=10, n_boot=500, seed=1)
    assert (lo1, hi1) != (lo3, hi3)


def test_bootstrap_ci_brackets_mean_for_clearly_positive_series():
    rng = np.random.default_rng(2)
    x = rng.normal(loc=0.02, scale=0.001, size=300)  # strong, low-noise positive mean
    lo, hi = onr.stationary_bootstrap_ci(x, mean_block=10, n_boot=1000, seed=20260904)
    assert lo > 0
    assert lo < x.mean() < hi


def test_mean_t_matches_scipy_style_one_sample_t():
    x = np.array([0.01, -0.02, 0.03, 0.015, -0.005])
    m, t, n = onr.mean_t(x)
    assert n == 5
    assert np.isclose(m, x.mean())
    expected_t = x.mean() / (x.std(ddof=1) / np.sqrt(5))
    assert np.isclose(t, expected_t)


def test_net_mean_t_subtracts_cost_in_bps():
    x = np.array([0.001] * 100)
    m_net, t_net = onr.net_mean_t(x, cost_bps=1.0)
    assert np.isclose(m_net, 0.001 - 1.0e-4)


def test_load_ohlc_drops_invalid_rows_and_enforces_cutoff(tmp_path):
    csv_path = tmp_path / "ohlc.csv"
    pd.DataFrame({
        "date": ["2026-09-01", "2026-09-02", "2026-09-04", "2026-09-05"],
        "open": [100, 0, 105, 110],
        "high": [101, 0, 106, 111],
        "low": [99, 0, 104, 109],
        "close": [100, 0, 105, 111],
    }).to_csv(csv_path, index=False)
    df = onr.load_ohlc(csv_path)
    # row with open/close == 0 dropped; row after CUTOFF (2026-09-03) dropped
    assert list(df["date"].dt.strftime("%Y-%m-%d")) == ["2026-09-01"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))

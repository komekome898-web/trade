"""`bot.research.xborder_p2_fast` must reproduce `xborder_p2.simulate` exactly.

Two layers:
  1. the known-answer tapes of tests/test_xborder_p2_known_answer.py (the five
     hand-computed trades, the mask-off variant, the time-jump variant, the
     gap boundary and discard-window fixtures, misprint, stop/exit same bar,
     end-of-data, regime shift);
  2. real dev-set months (through `load_unsealed`) × three configurations,
     skipped when the snapshot is not on disk.
Identity = same trade count, same entry/exit timestamps (and signal
timestamps), every float column within 1e-9, every int/bool/str column equal,
same `.attrs`.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bot.research.xborder_p2 import (
    LEDGER_COLUMNS,
    block_permute_log_returns,
    daily_pnl,
    momentum_signal,
    sharpe_annual,
    simulate,
)
from bot.research.xborder_p2_fast import (
    BinanceGrid,
    BlockPermuter,
    daily_from_arrays,
    momentum_on_grid,
    prepare_grid,
    sharpe_from_daily,
    simulate_arrays,
    simulate_fast,
)
from tests.test_xborder_p2_known_answer import (
    COST_1W,
    DEFAULT_BAR,
    EMPTY,
    EXIT,
    K,
    STOP,
    THR,
    _discard_fixture,
    make_bf,
    make_binance,
    ts,
)

TOL = 1e-9
FLOAT_COLS = ["entry_px", "exit_px", "gross_bps", "cost_bps", "funding_bps", "net_bps",
              "hold_min", "pnl_jpy"]
TS_COLS = ["entry_ts", "exit_ts", "entry_signal_ts", "exit_signal_ts"]
OTHER_COLS = [c for c in LEDGER_COLUMNS if c not in FLOAT_COLS + TS_COLS]


def assert_ledgers_identical(ref: pd.DataFrame, fast: pd.DataFrame) -> None:
    assert list(ref.columns) == LEDGER_COLUMNS and list(fast.columns) == LEDGER_COLUMNS
    assert len(ref) == len(fast), (len(ref), len(fast))
    for col in TS_COLS:
        a = pd.DatetimeIndex(ref[col])
        b = pd.DatetimeIndex(fast[col])
        assert (a == b).all(), col
    for col in FLOAT_COLS:
        np.testing.assert_allclose(fast[col].to_numpy(float), ref[col].to_numpy(float),
                                   rtol=0, atol=TOL, err_msg=col)
    for col in OTHER_COLS:
        assert ref[col].tolist() == fast[col].tolist(), col
    assert ref.attrs == fast.attrs, (ref.attrs, fast.attrs)


def both(bf, m, thr=THR, exit_=EXIT, stop=STOP, cost=COST_1W, apply_masks=True, **kw):
    ref = simulate(bf, m, thr, exit_, stop, cost, apply_masks=apply_masks, **kw)
    grid = prepare_grid(bf, kw.get("max_gap_min", 5), apply_masks,
                        kw.get("funding_times_utc", (5, 13, 21)))
    mm = (pd.Series(m.to_numpy(float), index=m.index).reindex(grid.idx).to_numpy(float))
    fast = simulate_fast(grid, mm, thr, exit_, stop, cost,
                         kw.get("funding_pct_per_settlement", 0.02))
    assert_ledgers_identical(ref, fast)
    return ref, fast


def _m():
    return momentum_signal(make_binance(), K)


# ---- 1. known-answer tapes -----------------------------------------------------

def test_fast_matches_five_trade_known_answer():
    ref, fast = both(make_bf(), _m())
    assert len(fast) == 5
    assert abs(float(fast["net_bps"].sum()) - (37.4 - 152.6 + 25.4 + 97.4 - 152.6)) <= TOL


def test_fast_matches_known_answer_without_masks():
    ref, fast = both(make_bf(), _m(), apply_masks=False)
    assert len(fast) == 6 and fast.attrs["apply_masks"] is False


def test_fast_matches_time_jump_variant():
    drop = [ts(i) for i in list(range(30, 36)) + list(range(40, 46)) + [48]]
    both(make_bf().drop(index=drop), _m())


def test_fast_matches_gap_boundary_and_discard_window():
    bf = make_bf()
    bf.loc[[ts(34), ts(35)]] = DEFAULT_BAR
    both(bf, _m())
    bf.loc[ts(34)] = EMPTY
    both(bf, _m())
    for bar in (14, 15, 19):
        bf2, m2 = _discard_fixture(bar)
        both(bf2, m2)
        both(bf2, m2, apply_masks=False)


def test_fast_matches_misprint_stop_exit_same_bar_end_and_regime():
    idx = pd.date_range("2023-06-03 10:00", periods=40, freq="min", tz="UTC")
    bf = pd.DataFrame([DEFAULT_BAR] * 40, columns=["open", "high", "low", "close"], index=idx)
    bf.iloc[10] = (1_000_000.0, 1_400_000.0, 1_000_000.0, 1_400_000.0)
    c = [100.0] * 7 + [98.8, 98.4, 98.0, 97.6, 97.2] + [97.2] * 28
    m = momentum_signal(pd.Series(c, index=idx), 1)
    ref, fast = both(bf.iloc[:20], m)
    assert fast.attrs["n_misprint_rows_blanked"] == 1
    both(bf.iloc[:20], m, apply_masks=False)
    # stop and exit on the same bar -> "stop"
    bn = make_binance()
    bn.iloc[8] = 100.0
    ref, fast = both(make_bf(), momentum_signal(bn, K))
    assert fast.iloc[1]["exit_reason"] == "stop"
    # end of data while holding
    ref, fast = both(make_bf().iloc[:15], _m())
    assert fast.iloc[-1]["exit_reason"] == "end"
    # regime shift
    shifted = make_bf().copy()
    shifted.index = shifted.index + pd.Timedelta(days=400)
    bn = make_binance()
    bn.index = shifted.index
    ref, fast = both(shifted, momentum_signal(bn, K))
    assert set(fast["regime"]) == {"crypto_cfd"}
    # empty ledger (threshold nobody reaches)
    ref, fast = both(make_bf(), _m(), thr=50.0)
    assert len(fast) == 0


def test_momentum_on_grid_matches_momentum_signal_by_time():
    idx = pd.DatetimeIndex([ts(i) for i in (0, 1, 2, 4, 5, 7)])
    close = pd.Series([100.0, 110.0, 121.0, 133.1, 146.41, 150.0], index=idx)
    grid = prepare_grid(make_bf())
    for k in (1, 2, 3):
        ref = momentum_signal(close, k).reindex(grid.idx).to_numpy(float)
        fast = momentum_on_grid(grid, close, k)
        assert np.array_equal(np.isnan(ref), np.isnan(fast))
        np.testing.assert_array_equal(ref[~np.isnan(ref)], fast[~np.isnan(fast)])


def test_daily_and_sharpe_from_arrays_match_reference():
    grid = prepare_grid(make_bf())
    mm = _m().reindex(grid.idx).to_numpy(float)
    a = simulate_arrays(grid, mm, THR, EXIT, STOP)
    net = a["gross_bps"] - 2 * COST_1W - a["funding_bps"]
    d = daily_from_arrays(a["exit_day"], net, ~a["excluded_gap"])
    ref = daily_pnl(simulate(make_bf(), _m(), THR, EXIT, STOP, COST_1W))
    np.testing.assert_allclose(d, ref.to_numpy(float), atol=TOL)
    x = np.array([1.0, 2.0, 3.0])
    assert abs(sharpe_from_daily(x) - sharpe_annual(pd.Series(x))) < 1e-12
    assert np.isnan(sharpe_from_daily(np.array([1.0])))


def test_block_permuter_matches_reference_function():
    rng = np.random.default_rng(11)
    idx = pd.date_range("2023-06-01", periods=5 * 1440, freq="min", tz="UTC")
    close = pd.Series(100.0 * np.exp(np.cumsum(rng.normal(0, 1e-3, len(idx)))), index=idx)
    close.iloc[100:110] = np.nan
    ref = block_permute_log_returns(close, np.random.default_rng(5), "D").to_numpy(float)
    fast = BlockPermuter(close, "D").permute(np.random.default_rng(5))
    assert np.array_equal(np.isnan(ref), np.isnan(fast))
    np.testing.assert_array_equal(ref[~np.isnan(ref)], fast[~np.isnan(fast)])
    # a permuted close (on the SOURCE index, with absent minutes) fed through
    # BinanceGrid.momentum equals the reference chain momentum_signal(reindex)
    close2 = close.drop(index=close.index[200:260])          # absent minutes
    bars = pd.DataFrame([DEFAULT_BAR] * len(idx), columns=["open", "high", "low", "close"],
                        index=idx)
    grid2 = prepare_grid(bars)
    bg = BinanceGrid(close2, grid2)
    perm_ref = block_permute_log_returns(close2, np.random.default_rng(9), "D")
    perm_fast = BlockPermuter(close2, "D").permute(np.random.default_rng(9))
    for k in (1, 15, 30):
        want = momentum_signal(perm_ref, k).reindex(grid2.idx).to_numpy(float)
        got = bg.momentum(k, perm_fast)
        assert np.array_equal(np.isnan(want), np.isnan(got))
        np.testing.assert_array_equal(want[~np.isnan(want)], got[~np.isnan(got)])


# ---- 2. real dev-set months (through the seal) ----------------------------------

REPO = Path(__file__).resolve().parents[1]
BF_2021 = REPO / "backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2021.csv.gz"
BN_2021 = REPO / "backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2021.csv.gz"
SEAL = REPO / "backtest_data/phase2_sealed/P2-08/SEALED.json"
MONTHS = ["2021-01", "2021-05", "2021-11"]
CONFIGS = [(15, 0.4, 0.25), (30, 0.8, 0.5), (60, 1.2, 1.0)]


@pytest.mark.skipif(not (BF_2021.exists() and BN_2021.exists() and SEAL.exists()),
                    reason="P2-08 snapshot not on disk")
def test_fast_matches_reference_on_dev_set_months():
    import sys
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from scripts.phase2.p2_08_data import load_dev_frames
    bf, bn = load_dev_frames(years=(2021,))
    for month in MONTHS:
        p = pd.Period(month, "M")
        lo = pd.Timestamp(p.start_time, tz="UTC")
        hi = pd.Timestamp(p.end_time, tz="UTC")
        bfm = bf.loc[(bf.index >= lo) & (bf.index <= hi)]
        bnm = bn.loc[(bn.index >= lo) & (bn.index <= hi), "close"]
        for apply_masks in (True, False):
            grid = prepare_grid(bfm, 5, apply_masks)
            bg = BinanceGrid(bnm, grid)
            for k, thr, stop in CONFIGS:
                m = momentum_signal(bnm, k)
                ref = simulate(bfm, m, thr, 0.05, stop, 1.3, apply_masks=apply_masks)
                fast = simulate_fast(grid, bg.momentum(k), thr, 0.05, stop, 1.3)
                assert len(ref) > 50, (month, k, thr, stop)
                assert_ledgers_identical(ref, fast)

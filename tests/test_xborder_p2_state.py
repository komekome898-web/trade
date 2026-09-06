"""P2-08 iteration 1 — realized-volatility tercile state and the entry gate.

1. tercile assignment from frozen boundaries (NaN → none, ties on the
   boundary go to the lower tercile, val minutes use the TRAIN boundaries);
2. boundaries are fixed on the training period only — changing val data
   must not move them, and the tercile shares on train are 1/3 each;
3. realized vol: window / minimum-bars rule on empty minutes;
4. the entry gate in the fast engine equals the pandas reference engine fed
   a momentum series whose out-of-gate entry signals are clipped to ±thr,
   and `entry_gate=None` is bit-identical to the ungated engine.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.research.xborder_p2 import momentum_signal, simulate
from bot.research.xborder_p2_fast import prepare_grid, simulate_arrays, simulate_fast
from bot.research.xborder_p2_state import (
    TERCILE_LABELS,
    assign_tercile,
    log_returns,
    realized_vol,
    tercile_bounds,
    tercile_gates,
    tercile_label,
)
from tests.test_xborder_p2_fast import assert_ledgers_identical
from tests.test_xborder_p2_known_answer import (
    COST_1W,
    DEFAULT_BAR,
    EXIT,
    K,
    STOP,
    THR,
    make_bf,
    make_binance,
)


def _bars(n: int, seed: int, sigma_by_bar=None) -> pd.DataFrame:
    """Synthetic 1-minute bars; ``sigma_by_bar`` scales the log-return noise
    per bar (default constant)."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2021-12-30 00:00", periods=n, freq="min", tz="UTC")
    sig = np.ones(n) * 1e-3 if sigma_by_bar is None else np.asarray(sigma_by_bar, float)
    c = 1_000_000.0 * np.exp(np.cumsum(rng.normal(0.0, 1.0, n) * sig))
    return pd.DataFrame({"open": c, "high": c * 1.0005, "low": c * 0.9995, "close": c}, index=idx)


def test_assign_tercile_boundaries_and_nan():
    vol = np.array([np.nan, 0.5, 1.0, 1.0001, 2.0, 2.5, np.nan, 0.0])
    terc = assign_tercile(vol, (1.0, 2.0))
    # NaN -> -1 ; <= q1 -> 0 (boundary value included) ; (q1, q2] -> 1 ; > q2 -> 2
    assert terc.tolist() == [-1, 0, 0, 1, 1, 2, -1, 0]
    assert terc.dtype == np.int8
    gates = tercile_gates(terc)
    assert set(gates) == {0, 1, 2}
    assert gates[0].tolist() == [False, True, True, False, False, False, False, True]
    assert not any(gates[c][0] for c in gates)          # a NaN minute is in no gate
    assert [tercile_label(c) for c in (None, 0, 1, 2)] == ["all", *TERCILE_LABELS]


def test_bounds_fixed_on_train_only_and_applied_unchanged_to_val():
    n = 6 * 1440
    idx = pd.date_range("2021-12-29 00:00", periods=n, freq="min", tz="UTC")
    train = np.asarray(idx <= pd.Timestamp("2021-12-31 23:59", tz="UTC"))
    # train: calm ; val: 5x noisier (so val-inclusive terciles would move)
    sigma = np.where(train, 1e-3, 5e-3)
    bars = _bars(n, 3, sigma)
    grid = prepare_grid(bars)
    vol = realized_vol(grid, 60, 30)
    b_train = tercile_bounds(vol, train)
    b_all = tercile_bounds(vol, np.ones(n, bool))
    assert b_train[0] < b_train[1]
    assert b_all[1] > b_train[1] * 1.5                   # val data WOULD move the bounds
    # the same train bounds regardless of what val contains
    bars2 = _bars(n, 3, np.where(train, 1e-3, 1e-2))
    vol2 = realized_vol(prepare_grid(bars2), 60, 30)
    np.testing.assert_allclose(vol2[train], vol[train], rtol=0, atol=1e-15)
    assert tercile_bounds(vol2, train) == b_train
    # train split is 1/3 each (over defined minutes); val split is NOT (frozen bounds)
    terc = assign_tercile(vol, b_train)
    tr = terc[train & np.isfinite(vol)]
    shares = np.bincount(tr, minlength=3) / len(tr)
    np.testing.assert_allclose(shares, [1 / 3] * 3, atol=0.01)
    va = terc[~train & np.isfinite(vol)]
    assert (va == 2).mean() > 0.9                       # noisy val lands almost entirely in 3_high
    assert (terc[~np.isfinite(vol)] == -1).all()


def test_realized_vol_window_min_bars_and_empty_minutes():
    n = 300
    bars = _bars(n, 7)
    bars.iloc[100:140] = np.nan                           # 40 empty minutes
    grid = prepare_grid(bars)
    r = log_returns(grid)
    assert np.isnan(r[0]) and np.isnan(r[100:141]).all() and np.isfinite(r[141])
    np.testing.assert_allclose(r[1:100], np.diff(np.log(grid.c[:100])), atol=1e-15)
    vol = realized_vol(grid, 60, 30)
    # first defined value needs 30 valid returns: r[1..30] -> index 30
    assert np.isnan(vol[:30]).all() and np.isfinite(vol[30])
    # hand value at t=99: std (ddof=1) of r[40..99]
    assert abs(vol[99] - np.std(r[40:100], ddof=1)) < 1e-15
    # inside the blank run the window still holds >= 30 valid returns until it drains
    # t=129: window r[70..129] has 30 valid (70..99) -> defined ; t=130: 29 valid -> NaN
    assert np.isfinite(vol[129]) and np.isnan(vol[130])
    assert np.isnan(vol[140]) and np.isnan(vol[160])
    # t=170: window r[111..170] has valid 141..170 = 30 -> defined
    assert np.isfinite(vol[170]) and np.isnan(vol[169])
    # unconditional rule: window/min_bars must be sane
    import pytest
    with pytest.raises(ValueError):
        realized_vol(grid, 60, 61)


def test_entry_gate_matches_reference_engine_with_clipped_signals():
    bf = make_bf()
    m = momentum_signal(make_binance(), K)
    grid = prepare_grid(bf)
    mm = m.reindex(grid.idx).to_numpy(float)
    # ungated: entry_gate=None must be identical to the ungated engine
    ref = simulate(bf, m, THR, EXIT, STOP, COST_1W)
    fast_none = simulate_fast(grid, mm, THR, EXIT, STOP, COST_1W)
    fast_all = simulate_fast(grid, mm, THR, EXIT, STOP, COST_1W, entry_gate=np.ones(grid.n, bool))
    assert_ledgers_identical(ref, fast_none)
    assert "n_entry_signals_gated" not in fast_none.attrs
    assert fast_all.attrs["n_entry_signals_gated"] == 0
    fast_all.attrs.pop("n_entry_signals_gated")
    assert_ledgers_identical(ref, fast_all)
    # gated: allow entries only in bars 0..20 -> trades 1..3 of the known answer survive
    gate = np.zeros(grid.n, bool)
    gate[:21] = True
    got = simulate_fast(grid, mm, THR, EXIT, STOP, COST_1W, entry_gate=gate)
    m_ref = mm.copy()
    off = (~gate) & np.isfinite(m_ref) & (np.abs(m_ref) > THR / 100)
    m_ref[off] = np.sign(m_ref[off]) * (THR / 100)      # not > thr (no entry), not < exit (no exit)
    want = simulate(bf, pd.Series(m_ref, index=grid.idx), THR, EXIT, STOP, COST_1W)
    # the gate is applied AFTER the discard window: signals 38 and 42 of the
    # tape are discarded first, so only the other out-of-gate signals count
    n_gated_expected = int((off & ~grid.discard).sum())
    assert len(got) == 3 and 0 < n_gated_expected < int(off.sum())
    assert got.attrs["n_entry_signals_gated"] == n_gated_expected
    got.attrs.pop("n_entry_signals_gated")
    # the reference never SEES the clipped signals, so its two signal counts
    # differ by construction; every other attr and every column must agree
    assert got.attrs["n_entry_signal_bars"] == want.attrs["n_entry_signal_bars"] + int(off.sum())
    assert got.attrs["n_entry_signals_discarded"] == want.attrs["n_entry_signals_discarded"] + int((off & grid.discard).sum())
    for key in ("n_entry_signal_bars", "n_entry_signals_discarded"):
        got.attrs[key] = want.attrs[key]
    assert_ledgers_identical(want, got)
    # arrays API: the same trades, and a wrong-length gate is rejected
    a = simulate_arrays(grid, mm, THR, EXIT, STOP, 0.02, gate)
    assert a["n_trades"] == 3 and a["n_entry_signals_gated"] == n_gated_expected
    import pytest
    with pytest.raises(ValueError):
        simulate_arrays(grid, mm, THR, EXIT, STOP, 0.02, gate[:-1])
    # a gate on a bar that is not an entry signal changes nothing
    gate2 = np.ones(grid.n, bool)
    gate2[3] = False                                     # bar 3: no entry signal in the tape
    g2 = simulate_fast(grid, mm, THR, EXIT, STOP, COST_1W, entry_gate=gate2)
    assert g2.attrs["n_entry_signals_gated"] == 0
    g2.attrs.pop("n_entry_signals_gated")
    assert_ledgers_identical(ref, g2)
    assert DEFAULT_BAR[0] == 1_000_000.0                 # (fixture sanity)

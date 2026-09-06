"""P2-08 iteration 1 — the realized-volatility tercile state variable.

PREREG 探索面「反復の梯子」: 反復 1 = 実現ボラ(60 分)三分位で建玉可否を条件付け
(27 × 3 = 81 構成、累計 N = 108). This module only DEFINES the state; the
gating itself is `xborder_p2_fast.simulate_arrays(..., entry_gate=...)`, which
zeroes entry signals outside the chosen tercile and leaves every other rule
(exit, stop, deferral, discard window, funding, gap exclusion) untouched.

Definitions fixed here (the PREREG wording leaves them open; each choice is
also recorded in the iteration's RESULTS.md):

* Realized vol at grid minute t = sample standard deviation (ddof = 1) of the
  bitFlyer 1-minute log returns r(j) = ln(c(j) / c(j−1)) over the WINDOW
  minutes j = t−59 .. t (60 returns, i.e. the closes c(t−60) .. c(t)). A
  return exists only when both c(j−1) and c(j) are valid bars (empty minutes
  and misprint-blanked bars drop out). Fewer than MIN_BARS valid returns →
  NaN → the minute belongs to no tercile → no entry in any conditioned
  configuration. The window ENDS at t (includes the return into close(t))
  because the signal m(t) itself is formed from close(t); nothing after t is
  used, so the state is observable when the order would be sent (fill = next
  bar's open).
* Tercile boundaries q1, q2 = the 33.3 / 66.7 percentiles of the realized
  vol over ALL grid minutes with a finite value in the TRAIN period
  (.. 2021-12-31 23:59 UTC) — unconditional minutes, not signal minutes, so
  the boundaries do not depend on any (k, thr). They are frozen and applied
  unchanged to val (no look-ahead into val).
* Assignment: vol <= q1 → tercile 1 (low); q1 < vol <= q2 → 2 (mid);
  vol > q2 → 3 (high); NaN → −1 (none).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.research.xborder_p2_fast import Grid

VOL_WINDOW_MIN = 60
VOL_MIN_BARS = 30
TERCILE_CODES = (0, 1, 2)
TERCILE_LABELS = ("1_low", "2_mid", "3_high")
TERCILE_PCTS = (100.0 / 3.0, 200.0 / 3.0)


def log_returns(grid: Grid) -> np.ndarray:
    """r(j) = ln(c(j)/c(j−1)) on the grid; NaN unless bars j−1 and j are both
    valid. r(0) is NaN."""
    n = grid.n
    r = np.full(n, np.nan)
    if n < 2:
        return r
    ok = grid.valid[1:] & grid.valid[:-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        r[1:][ok] = np.log(grid.c[1:][ok] / grid.c[:-1][ok])
    return r


def realized_vol(grid: Grid, window: int = VOL_WINDOW_MIN, min_bars: int = VOL_MIN_BARS
                 ) -> np.ndarray:
    """Per grid minute t: sample std (ddof = 1) of the valid 1-minute log
    returns among r(t−window+1) .. r(t); NaN when fewer than ``min_bars`` of
    them are valid (module docstring)."""
    window = int(window)
    min_bars = int(min_bars)
    if window < 2 or min_bars < 2 or min_bars > window:
        raise ValueError(f"need 2 <= min_bars <= window, got window={window}, min_bars={min_bars}")
    r = log_returns(grid)
    return pd.Series(r).rolling(window, min_periods=min_bars).std(ddof=1).to_numpy(dtype=float)


def tercile_bounds(vol: np.ndarray, in_train: np.ndarray) -> tuple[float, float]:
    """(q1, q2) = the 33.3 / 66.7 percentiles of ``vol`` over the minutes
    flagged by ``in_train`` that have a finite value. Raises when fewer than
    3 such minutes exist (a tercile needs at least one point each)."""
    v = np.asarray(vol, dtype=float)[np.asarray(in_train, dtype=bool)]
    v = v[np.isfinite(v)]
    if len(v) < 3:
        raise ValueError(f"need at least 3 finite training values to place terciles, got {len(v)}")
    q1, q2 = np.percentile(v, TERCILE_PCTS)
    return float(q1), float(q2)


def assign_tercile(vol: np.ndarray, bounds: tuple[float, float]) -> np.ndarray:
    """int8 per minute: 0 (vol <= q1), 1 (q1 < vol <= q2), 2 (vol > q2),
    −1 where vol is NaN. Boundaries are the FROZEN training values, whatever
    period the minute belongs to."""
    q1, q2 = float(bounds[0]), float(bounds[1])
    if not (np.isfinite(q1) and np.isfinite(q2) and q1 <= q2):
        raise ValueError(f"bounds must be finite and ordered, got {bounds!r}")
    v = np.asarray(vol, dtype=float)
    out = np.full(len(v), -1, dtype=np.int8)
    fin = np.isfinite(v)
    out[fin & (v <= q1)] = 0
    out[fin & (v > q1) & (v <= q2)] = 1
    out[fin & (v > q2)] = 2
    return out


def tercile_gates(terc: np.ndarray) -> dict[int, np.ndarray]:
    """{code: boolean entry gate over the grid} for the three terciles."""
    return {code: terc == code for code in TERCILE_CODES}


def tercile_label(code) -> str:
    """'all' for the unconditioned configuration (None), else the tercile's
    sort-stable label ('1_low' / '2_mid' / '3_high')."""
    if code is None:
        return "all"
    return TERCILE_LABELS[int(code)]

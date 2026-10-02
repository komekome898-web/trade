"""Synthetic inputs with known answers for the W1 checks (spec section 2).
Every random draw comes from numpy.random.default_rng(<fixed seed>); the seeds
are fixed here, before any check was run, and are test values, not
measurement settings."""
from __future__ import annotations

import numpy as np

from bot.bt.core import BarEvent
from bot.bt.data.reference import reference_series

NS = 1_000_000_000
M = 60 * NS
DAY = 86_400 * NS
T0 = 1_704_067_200 * NS  # 2024-01-01T00:00:00Z, a UTC (and so 1-minute) boundary
BP = 1e-4
N_T1 = 200 * 1440  # spec T1: 1-minute bars, 200 days

DECL_T1 = {"S": {"lag_ns": 0, "source": "試験の入力(T1 の S は行の時刻に使える)"}}

SEED_T1 = 20261002  # T1 (and T6): moves and the blocks where S is up
SEED_T5 = 20261003  # T5 (and T4): moves without any effect


def bars_from_moves(moves, *, start=T0, missing=(), empty=()):
    """Bar i opens at start + i min with open o_i and closes with o_{i+1} = o_i * (1 + moves[i]);
    indices in `missing` are left out (no bar), in `empty` get volume 0."""
    moves = np.asarray(moves, dtype=float)
    o = 100.0 * np.cumprod(np.concatenate(([1.0], 1.0 + moves)))
    miss, emp = set(missing), set(empty)
    out = []
    for i in range(len(moves)):
        if i in miss:
            continue
        a, b = float(o[i]), float(o[i + 1])
        out.append(BarEvent(received_time_ns=start + (i + 1) * M, exchange_time_ns=start + (i + 1) * M,
                            start_time_ns=start + i * M, open=a, close=b, high=max(a, b), low=min(a, b),
                            volume=0.0 if i in emp else 1.0))
    return out


def t1_input():
    """T1: moves N(0, 10 bp) i.i.d.; S up on 30% of the 60-bar blocks; the move after a bar where S is up
    has mean +2 bp. S is a reference series with lag 0: the row of block b is stamped at the close of the
    block's first bar, so the decision at that bar already sees it."""
    rng = np.random.default_rng(SEED_T1)
    n_blocks = N_T1 // 60
    up_blocks = np.zeros(n_blocks, dtype=bool)
    up_blocks[rng.choice(n_blocks, size=int(round(0.3 * n_blocks)), replace=False)] = True
    s = np.repeat(up_blocks, 60)  # S at the decision of bar i
    moves = rng.normal(0.0, 10 * BP, N_T1)
    moves[1:] += np.where(s[:-1], 2 * BP, 0.0)  # move of bar i+1 = r_{t+1} of the decision at bar i
    rows = [(T0 + (60 * b + 1) * M, float(up_blocks[b])) for b in range(n_blocks)]
    S = reference_series("S", rows, declarations=DECL_T1)
    return bars_from_moves(moves), S, s


def t5_input():
    rng = np.random.default_rng(SEED_T5)
    return bars_from_moves(rng.normal(0.0, 10 * BP, N_T1))


class Always:
    requires = ()

    def __init__(self, x=1.0, name="always_long"):
        self.x, self.name = x, name

    def exposure(self, view):
        return self.x


class PrevSign:
    """T5: the sign of the move of the bar that just closed."""
    name = "prev_sign"
    requires = ()

    def exposure(self, view):
        b = view.bars(1)[0]
        return float(np.sign(b.close - b.open))


class FirstHours:
    """+1 when the decision time is in the first `hours` of its UTC day (0 < t mod day <= hours), else 0."""
    requires = ()

    def __init__(self, hours):
        self.hours, self.name = hours, f"first_{hours}h"

    def exposure(self, view):
        k = view.now_ns % DAY
        return 1.0 if 0 < k <= self.hours * 3600 * NS else 0.0

SEED_BOOT = 20261004  # bootstrap seed of the measurements in the checks (C5 c)
SEED_CONTROL = 20261005  # shift seed of the controls in the checks (C5 d)
SEED_CORR = 20261006  # bootstrap seed of the T4 correlation
SEED_BROKEN = 20261007  # the shuffle of the broken T4 version
SEED_AR1 = 20261008  # the AR(1) series of the block-length check

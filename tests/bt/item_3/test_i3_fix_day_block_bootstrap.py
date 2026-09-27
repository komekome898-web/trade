"""D-3 (K1 stage A, 2026-09-27): the day block bootstrap of bot.bt.validation.

Rule text (bootstrap.py): blocks = the UTC days of the given times; each resample draws as many days as there
are, with replacement; every value of a drawn day enters the resample; the statistic is the pooled mean; the
interval is numpy's linear quantile of the resampled means at alpha/2, 1 - alpha/2; randomness only
numpy.random.default_rng(seed). The expected values are computed below from that text alone."""
from __future__ import annotations

import numpy as np
import pytest

from bot.bt.validation import ValidationError, day_block_bootstrap_ci, label_block_bootstrap_ci

DAY = 86_400 * 10**9


def oracle(x, days, R, seed, alpha):
    order = []
    for d in days:
        if d not in order:
            order.append(d)
    groups = [[v for v, d in zip(x, days) if d == g] for g in order]
    rng = np.random.default_rng(seed)
    reps = []
    for _ in range(R):
        idx = rng.integers(0, len(groups), size=len(groups))
        pool = [v for i in idx for v in groups[i]]
        reps.append(sum(pool) / len(pool))
    lo, hi = np.quantile(reps, [alpha / 2, 1 - alpha / 2])
    return float(lo), float(hi), reps


def test_two_days_hand_values():
    # day 0: 1, 1, 1 ; day 1: 4. Possible pooled means: (0,0) 1, (0,1)/(1,0) (3+4)/4 = 1.75, (1,1) 4
    x = [1.0, 1.0, 1.0, 4.0]
    t = [0, 5, DAY - 1, DAY]  # DAY - 1 is still day 0; DAY is day 1 (UTC boundary)
    ci = day_block_bootstrap_ci(x, t, n_resamples=400, seed=3, alpha=0.05)
    lo, hi, reps = oracle(x, [0, 0, 0, 1], 400, 3, 0.05)
    assert set(np.round(reps, 12)) <= {1.0, 1.75, 4.0}
    assert (ci.lo, ci.hi) == (lo, hi)
    assert ci.estimate == 7.0 / 4 and ci.n_blocks == 2 and ci.n_values == 4 and ci.blocks == "utc_day"


def test_matches_the_oracle_on_uneven_days():
    rng = np.random.default_rng(11)
    t = sorted(int(v) for v in rng.integers(0, 40 * DAY, size=300))
    x = [float(v) for v in rng.normal(0.5, 3.0, size=300)]
    ci = day_block_bootstrap_ci(x, t, n_resamples=200, seed=20260909, alpha=0.05)
    lo, hi, reps = oracle(x, [v // DAY for v in t], 200, 20260909, 0.05)
    assert ci.lo == pytest.approx(lo, rel=1e-12, abs=1e-12) and ci.hi == pytest.approx(hi, rel=1e-12, abs=1e-12)
    assert ci.se == pytest.approx(float(np.std(reps, ddof=1)), rel=1e-12)
    again = day_block_bootstrap_ci(x, t, n_resamples=200, seed=20260909, alpha=0.05)
    assert again == ci


def test_blocks_are_days_not_fixed_lengths():
    # the same values with every value on its own day give a different interval (the day grouping is used)
    x = [0.0, 0.0, 0.0, 0.0, 10.0, -2.0]
    grouped = day_block_bootstrap_ci(x, [0, 1, 2, 3, DAY, 2 * DAY], n_resamples=300, seed=1, alpha=0.1)
    single = day_block_bootstrap_ci(x, [k * DAY for k in range(6)], n_resamples=300, seed=1, alpha=0.1)
    assert grouped.n_blocks == 3 and single.n_blocks == 6
    assert (grouped.lo, grouped.hi) != (single.lo, single.hi)


def test_refusals():
    with pytest.raises(ValidationError):
        day_block_bootstrap_ci([1.0, 2.0], [0, 1], n_resamples=100, seed=1, alpha=0.05)  # one day only
    with pytest.raises(ValidationError):
        day_block_bootstrap_ci([1.0, 2.0], [0], n_resamples=100, seed=1, alpha=0.05)
    with pytest.raises(ValidationError):
        day_block_bootstrap_ci([1.0, 2.0], [0.0, float(DAY)], n_resamples=100, seed=1, alpha=0.05)
    with pytest.raises(ValidationError):
        label_block_bootstrap_ci([1.0, 2.0], ["a", "b"], n_resamples=1, seed=1, alpha=0.05)

"""C5 c as corrected (2026-10-02): the Politis-White circular block length,
checked against the AR(1) theory, and its use in the measurement.

1. The formula, fed the AR(1)'s exact autocovariances with a bandwidth M so
   large that the flat-top taper and the truncation change nothing that a
   float can hold (phi^(M/2) < 1e-38), must give the closed form
   b_opt = (6 phi^2 / (1 - phi^2)^2)^(1/3) n^(1/3) to rounding (rel 1e-12).
2. On a simulated Gaussian AR(1), the estimate b_hat (with its data-chosen M)
   is compared with b_M = the same formula on the exact autocovariances with
   the same M (the estimator's deterministic bias at that M, written out, and
   reported against b_opt). The tolerance is from the estimator's asymptotics,
   not from repeated seeds: log b_hat is (2/3)(log G_hat - log g0_hat) plus
   constants, a smooth function of the sample autocovariances R_hat(0..M), whose
   asymptotic covariance is Bartlett's formula for a Gaussian linear process,
   n Cov(R_hat(i), R_hat(j)) -> sum_l R(l) R(l+j-i) + R(l+j) R(l-i); the delta
   method gives sd(log b_hat), and |log b_hat - log b_M| <= z_{0.975} sd. What
   this leaves out: M is taken as given (it is chosen from the same data), the
   O(1/n) bias of R_hat, and the delta method's own error. The z is the 95% the
   spec uses for every interval, so a correct estimator misses with about 5%
   probability on its one fixed seed."""
from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np
import pytest

from bot.research.cards.blocklen import ar1_b_opt, b_from_acv, flat_top, politis_white
from bot.research.cards.measure import MIN_BLOCK_BARS, block_length
from bot.research.cards.pnl import PnL

import w1_synth as W

PHI = 0.5  # test value
N = 288_000  # the size of the T1 / T5 series


def ar1(phi: float, n: int, seed: int) -> np.ndarray:
    e = np.random.default_rng(seed).normal(size=n)
    x = np.empty(n)
    prev = 0.0
    for t in range(n):
        prev = phi * prev + e[t]
        x[t] = prev
    return x


def ar1_acv(phi: float, lags: np.ndarray) -> np.ndarray:
    return phi ** np.abs(lags) / (1.0 - phi * phi)


def b_with_constant(acv, n, M, D_factor):
    k = np.arange(1, M + 1)
    lam = flat_top(k / M)
    G = 2.0 * float(np.sum(lam * k * acv[1:M + 1]))
    g0 = float(acv[0] + 2.0 * np.sum(lam * acv[1:M + 1]))
    return (2.0 * G * G / (D_factor * g0 * g0)) ** (1.0 / 3.0) * n ** (1.0 / 3.0)


@pytest.mark.parametrize("phi", [0.2, 0.5, 0.8])
def test_formula_gives_the_ar1_closed_form(phi):
    M = 800
    acv = ar1_acv(phi, np.arange(M + 1))
    assert b_from_acv(acv, N, M) == pytest.approx(ar1_b_opt(phi, N), rel=1e-12)
    # broken version: the stationary bootstrap's constant D = 2 g0^2 in place of the circular (4/3) g0^2
    assert b_with_constant(acv, N, M, 2.0) != pytest.approx(ar1_b_opt(phi, N), rel=1e-2)


def _band(phi, n, M):
    k = np.arange(1, M + 1)
    lam = flat_top(k / M)
    R = lambda lag: ar1_acv(phi, lag)  # noqa: E731
    G = 2.0 * np.sum(lam * k * R(k))
    g0 = R(0) + 2.0 * np.sum(lam * R(k))
    w = np.concatenate(([-1.0 / g0], 2.0 * lam * k / G - 2.0 * lam / g0))  # d(log G - log g0) / d R(0..M)
    ls = np.arange(-4000, 4001)  # phi^4000: nothing left
    C = np.array([[np.sum(R(ls) * R(ls + j - i) + R(ls + j) * R(ls - i)) for j in range(M + 1)]
                  for i in range(M + 1)])
    return (2.0 / 3.0) * math.sqrt(float(w @ C @ w) / n)


def test_the_estimate_on_a_simulated_ar1():
    x = ar1(PHI, N, W.SEED_AR1)
    bl = politis_white(x)
    b_M = b_from_acv(ar1_acv(PHI, np.arange(bl.M + 1)), N, bl.M)
    sd = _band(PHI, N, bl.M)
    z = NormalDist().inv_cdf(0.975)
    print("AR(1)", {"phi": PHI, "n": N, "m_hat": bl.m_hat, "M": bl.M, "b_hat": bl.b_uncapped, "b_M": b_M,
                    "b_opt": ar1_b_opt(PHI, N), "log(b_hat/b_M)": math.log(bl.b_uncapped / b_M),
                    "z*sd": z * sd, "log(b_M/b_opt)": math.log(b_M / ar1_b_opt(PHI, N))})
    assert bl.b == bl.b_uncapped  # below b_max
    assert abs(math.log(bl.b_uncapped / b_M)) <= z * sd
    # broken version: the stationary constant, on the same sample autocovariances
    from bot.research.cards.blocklen import autocovariances
    broken = b_with_constant(autocovariances(x, bl.M), N, bl.M, 2.0)
    assert abs(math.log(broken / b_M)) > z * sd


def test_short_and_constant_series():
    assert politis_white(np.zeros(1000)).b == 0.0
    with pytest.raises(ValueError, match="too short"):
        politis_white(np.arange(10.0))  # m_max = ceil(sqrt 10) + 5 = 9: needs more than 10 values


def _pnl(P, e):
    n = len(P)
    z = np.zeros(n, dtype=np.int64)
    return PnL(z, W.T0 + np.arange(n, dtype=np.int64) * W.M, np.asarray(e, dtype=float), z, z, z, z,
               np.asarray(P, dtype=float), np.asarray(P, dtype=float) * np.asarray(e, dtype=float), n + 2, 2)


def test_the_length_comes_from_the_pnl_series_not_the_exposure():
    """An always-in exposure (+1 throughout) with strongly dependent moves: P_t carries the dependence, the
    exposure carries none. L comes from P_t (here at b_max, above the 1,440 floor); the broken version, from
    the exposure series, would give the floor."""
    x = ar1(0.995, N, W.SEED_AR1) * 1e-3  # test values
    p = _pnl(x, np.ones(N))
    L, how = block_length(p)
    assert L == math.ceil(politis_white(p.pnl_pct).b) and L > MIN_BLOCK_BARS
    assert how["median_nonzero_run"] == float(N)  # the old rule's run, shown as a diagnostic only
    broken = max(math.ceil(politis_white(p.exposure).b), MIN_BLOCK_BARS)
    assert broken != L


def test_independent_pnl_gets_the_one_day_floor():
    x = np.random.default_rng(W.SEED_AR1).normal(size=N)
    L, how = block_length(_pnl(x, np.ones(N)))
    assert L == MIN_BLOCK_BARS and how["pw_b"] < MIN_BLOCK_BARS

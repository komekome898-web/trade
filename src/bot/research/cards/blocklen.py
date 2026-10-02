"""Automatic block length of the circular block bootstrap (W1 spec C5 c, as
corrected on 2026-10-02): Politis & White (2004), "Automatic block-length
selection for the dependent bootstrap", Econometric Reviews 23(1), with the
correction of Patton, Politis & White (2009), Econometric Reviews 28(4). The
correction changed the constant of the stationary bootstrap; the circular
bootstrap's D_CB = (4/3) g(0)^2 is the one used here (as in the correction
and in the authors' code).

For a series x_1..x_n (here the P_t of a card run):

  R(k)   sample autocovariance, (1/n) sum_t (x_t - mean)(x_{t+k} - mean)
  rho(k) = R(k) / R(0)
  K_N    = max(5, ceil(sqrt(log10 n)))
  m_max  = ceil(sqrt n) + K_N
  m_hat  = the smallest positive m with |rho(m + k)| < 2 sqrt(log10 n / n) for
           k = 1..K_N (m + K_N <= m_max); none: m_hat = m_max
  M      = min(2 m_hat, m_max)
  lambda(t) = 1 for |t| <= 1/2, 2 (1 - |t|) for 1/2 < |t| <= 1   (flat-top)
  G      = sum_{k=-M..M} lambda(k/M) |k| R(k)
  g0     = sum_{k=-M..M} lambda(k/M) R(k)
  D_CB   = (4/3) g0^2
  b      = (2 G^2 / D_CB)^(1/3) n^(1/3), at most b_max = ceil(min(3 sqrt n, n / 3))

The constants (K_N, m_max, the 2 of the threshold, b_max) are those of the
authors' own code (Patton's opt_block_length_REV_dec07.m); none is tuned
here. A series with R(0) = 0 (no variation, e.g. a card that is always 0)
has no dependence to keep: b = 0.

For an AR(1) x_t = phi x_{t-1} + e_t, R(k) = R(0) phi^|k|, so
G = 2 R(0) phi / (1 - phi)^2, g0 = R(0) (1 + phi) / (1 - phi), and
b_opt = (6 phi^2 / (1 - phi^2)^2)^(1/3) n^(1/3) (`ar1_b_opt`).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class BlockLength:
    b: float  # the circular block length (not rounded), after the b_max cap
    b_uncapped: float
    b_max: int
    m_hat: int
    M: int
    n: int


def flat_top(t: np.ndarray) -> np.ndarray:
    a = np.abs(t)
    return np.where(a <= 0.5, 1.0, np.where(a <= 1.0, 2.0 * (1.0 - a), 0.0))


def autocovariances(x: np.ndarray, max_lag: int) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    n = len(x)
    d = x - x.mean()
    return np.array([float(d[k:] @ d[:n - k]) / n for k in range(max_lag + 1)])


def b_from_acv(acv: np.ndarray, n: int, M: int) -> float:
    """The formula part: b from the autocovariances R(0..M) and the bandwidth M."""
    if acv[0] <= 0:
        return 0.0
    if M < 1:
        raise ValueError("M must be >= 1")
    k = np.arange(1, M + 1)
    lam = flat_top(k / M)
    G = 2.0 * float(np.sum(lam * k * acv[1:M + 1]))
    g0 = float(acv[0] + 2.0 * np.sum(lam * acv[1:M + 1]))
    D = 4.0 / 3.0 * g0 * g0
    return (2.0 * G * G / D) ** (1.0 / 3.0) * n ** (1.0 / 3.0)


def politis_white(x) -> BlockLength:
    x = np.asarray(x, dtype=float)
    n = len(x)
    kn = max(5, math.ceil(math.sqrt(math.log10(n)))) if n > 1 else 5
    m_max = math.ceil(math.sqrt(n)) + kn
    if n <= m_max + 1:
        raise ValueError(f"a series of {n} values is too short for the automatic block length (needs > {m_max + 1})")
    b_max = math.ceil(min(3.0 * math.sqrt(n), n / 3.0))
    acv = autocovariances(x, m_max)
    if acv[0] <= 0:
        return BlockLength(0.0, 0.0, b_max, 0, 0, n)
    rho = np.abs(acv / acv[0])
    crit = 2.0 * math.sqrt(math.log10(n) / n)
    m_hat = m_max
    for m in range(1, m_max - kn + 1):
        if np.all(rho[m + 1:m + kn + 1] < crit):
            m_hat = m
            break
    M = min(2 * m_hat, m_max)
    b = b_from_acv(acv, n, M)
    return BlockLength(min(b, float(b_max)), b, b_max, m_hat, M, n)


def ar1_b_opt(phi: float, n: int) -> float:
    """The theoretical optimal circular block length of an AR(1) (module docstring)."""
    return (6.0 * phi * phi / (1.0 - phi * phi) ** 2) ** (1.0 / 3.0) * n ** (1.0 / 3.0)


__all__ = ["BlockLength", "ar1_b_opt", "autocovariances", "b_from_acv", "flat_top", "politis_white"]

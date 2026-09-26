"""Block bootstrap confidence intervals (item 3, old item 7: 「ブロック・ブートストラップ」).

Resampling whole blocks keeps the serial dependence inside each block, so an
autocorrelated series gets the wider interval it needs (an i.i.d. resample
of an AR(1) with phi 0.6 is about half as wide as it should be).

Methods (named by the caller; there is no default):
  circular    blocks of `block_len` starting anywhere, wrapping around the
              end (Politis & Romano 1992); its variance of the mean has the
              closed form of the Bartlett-weighted autocovariance sum.
  moving      blocks of `block_len` starting in [0, n - block_len] (Kunsch 1989).
  stationary  block lengths geometric with mean `block_len`, wrapping
              (Politis & Romano 1994).

The interval is the percentile interval of the resampled statistic at
alpha/2 and 1 - alpha/2 (numpy's linear quantile). Randomness is only
`numpy.random.default_rng(seed)`; the seed is required.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence, Union

import numpy as np

from ._args import as_choice, as_int, as_numbers, as_prob
from .errors import ValidationError

METHODS = ("circular", "moving", "stationary")
STATISTICS = ("mean",)


@dataclass(frozen=True)
class BootstrapCI:
    lo: float
    hi: float
    estimate: float  # the statistic on the original series
    se: float  # standard deviation of the resampled statistic
    method: str
    block_len: int
    n_resamples: int
    seed: int
    alpha: float


def _indices(rng: np.random.Generator, n: int, L: int, method: str) -> np.ndarray:
    if method == "stationary":
        idx = np.empty(n, dtype=np.int64)
        pos = int(rng.integers(0, n))
        new = rng.random(n) < 1.0 / L
        starts = rng.integers(0, n, size=n)
        for i in range(n):
            if i and new[i]:
                pos = int(starts[i])
            idx[i] = pos % n
            pos += 1
        return idx
    nb = -(-n // L)
    hi = n if method == "circular" else n - L + 1
    s = rng.integers(0, hi, size=nb)
    return ((s[:, None] + np.arange(L)[None, :]) % n).reshape(-1)[:n]


def block_bootstrap_ci(x: Sequence[float], *, block_len: int, n_resamples: int, seed: int, alpha: float,
                       method: str, statistic: Union[str, Callable[[np.ndarray], float]]) -> BootstrapCI:
    xs = np.asarray(as_numbers("x", x, min_len=2), dtype=float)
    n = len(xs)
    L = as_int("block_len", block_len, lo=1, hi=n)
    R = as_int("n_resamples", n_resamples, lo=2)
    sd = as_int("seed", seed)
    a = as_prob("alpha", alpha)
    m = as_choice("method", method, METHODS)
    if isinstance(statistic, str):
        as_choice("statistic", statistic, STATISTICS)
        stat: Callable[[np.ndarray], float] = lambda v: float(np.mean(v))  # noqa: E731
    elif callable(statistic):
        stat = statistic
    else:
        raise ValidationError(f"statistic must be one of {STATISTICS} or a callable, got {statistic!r}")
    rng = np.random.default_rng(sd)
    reps = np.empty(R, dtype=float)
    for r in range(R):
        reps[r] = stat(xs[_indices(rng, n, L, m)])
    if not np.all(np.isfinite(reps)):
        raise ValidationError("the statistic returned a non-finite value on a resample")
    lo, hi = np.quantile(reps, [a / 2, 1 - a / 2])
    return BootstrapCI(float(lo), float(hi), float(stat(xs)), float(np.std(reps, ddof=1)), m, L, R, sd, a)


def circular_block_se_of_mean(x: Sequence[float], block_len: int) -> float:
    """The exact standard error of the mean under the circular block
    bootstrap (the Bartlett-weighted circular autocovariance sum / n)."""
    xs = np.asarray(as_numbers("x", x, min_len=2), dtype=float)
    n = len(xs)
    L = as_int("block_len", block_len, lo=1, hi=n)
    d = xs - xs.mean()
    gam = [float(np.dot(d, np.roll(d, -h))) / n for h in range(L)]
    var = (gam[0] + 2 * sum((1 - h / L) * gam[h] for h in range(1, L))) / n
    return float(np.sqrt(var))


__all__: Any = ["METHODS", "BootstrapCI", "block_bootstrap_ci", "circular_block_se_of_mean"]

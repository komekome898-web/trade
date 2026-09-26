"""Deflated Sharpe ratio and the probability of backtest overfitting (item
3, old item 7: 「deflated Sharpe と PBO」).

deflated_sharpe(sr=, T=, skew=, kurtosis=, n_trials=, var_trials=)
    Bailey & Lopez de Prado (2014). SR is per period, `kurtosis` is the
    NON-excess kurtosis (normal = 3), `var_trials` the variance of the trials'
    per-period SR estimates.
      SR0 = sqrt(V) * ((1 - g) * z(1 - 1/N) + g * z(1 - 1/(N e)))   (g = Euler-Mascheroni)
      DSR = Phi((SR - SR0) * sqrt(T - 1) / sqrt(1 - skew SR + (kurtosis - 1)/4 SR^2))
    With N = 1 there is no selection: SR0 = 0 (the PSR against zero).

deflated_sharpe_of_returns(returns, n_trials=, var_trials=)
    the same with SR, skew and kurtosis taken from the series: SR = mean /
    sd with sd of ddof 0, and the plain (not small-sample adjusted) sample
    skewness m3 / m2^1.5 and kurtosis m4 / m2^2. The conventions used are
    returned with the value.

pbo(matrix, n_blocks=, metric=)
    CSCV (Bailey, Borwein, Lopez de Prado & Zhu 2016): the T x N matrix of
    per-period performance (rows = periods in time order, columns =
    strategies) is cut into S equal blocks (S even, T divisible by S). For
    each of the C(S, S/2) halves as in-sample: the strategy best in-sample
    (first on ties) gets its out-of-sample rank r among N (1 = worst; tied
    values share the lowest rank), w = r / (N + 1), lambda = ln(w / (1 - w)).
    PBO = share of lambda <= 0.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field
from statistics import NormalDist
from typing import Any, Callable, Sequence, Union

from ._args import as_choice, as_float, as_int, as_numbers
from .errors import ValidationError

_N = NormalDist()
EULER_GAMMA = 0.5772156649015329
PBO_METRICS = ("mean", "sharpe")


def expected_max_sr(n_trials: int, var_trials: float) -> float:
    N = as_int("n_trials", n_trials, lo=1)
    V = as_float("var_trials", var_trials, lo=0.0)
    if N == 1:
        return 0.0
    return math.sqrt(V) * ((1 - EULER_GAMMA) * _N.inv_cdf(1 - 1 / N) + EULER_GAMMA * _N.inv_cdf(1 - 1 / (N * math.e)))


@dataclass(frozen=True)
class DSR:
    dsr: float
    sr: float
    sr0: float
    z: float
    T: int
    skew: float
    kurtosis: float
    n_trials: int
    var_trials: float
    conventions: dict = field(default_factory=dict)


def deflated_sharpe(*, sr: float, T: int, skew: float, kurtosis: float, n_trials: int, var_trials: float) -> DSR:
    s = as_float("sr", sr)
    TT = as_int("T", T, lo=2)
    g3 = as_float("skew", skew)
    g4 = as_float("kurtosis", kurtosis, lo=0.0, lo_open=True)
    sr0 = expected_max_sr(n_trials, var_trials)
    den = 1 - g3 * s + (g4 - 1) / 4 * s * s
    if not den > 0:
        raise ValidationError(f"1 - skew*SR + (kurtosis-1)/4*SR^2 = {den} is not positive; the moments are not a distribution's")
    z = (s - sr0) * math.sqrt(TT - 1) / math.sqrt(den)
    return DSR(_N.cdf(z), s, sr0, z, TT, g3, g4, n_trials, float(var_trials))


def sample_moments(returns: Sequence[float]) -> tuple[float, float, float]:
    x = as_numbers("returns", returns, min_len=3)
    n = len(x)
    m = sum(x) / n
    m2 = sum((v - m) ** 2 for v in x) / n
    if m2 <= 0:
        raise ValidationError("returns have zero variance: no Sharpe ratio")
    m3 = sum((v - m) ** 3 for v in x) / n
    m4 = sum((v - m) ** 4 for v in x) / n
    return m / math.sqrt(m2), m3 / m2 ** 1.5, m4 / m2 ** 2


def deflated_sharpe_of_returns(returns: Sequence[float], *, n_trials: int, var_trials: float) -> DSR:
    sr, g3, g4 = sample_moments(returns)
    r = deflated_sharpe(sr=sr, T=len(list(returns)), skew=g3, kurtosis=g4, n_trials=n_trials, var_trials=var_trials)
    return DSR(**{**r.__dict__, "conventions": {"sd_ddof": 0, "moments": "plain m3/m2^1.5, m4/m2^2 (not adjusted)",
                                                  "kurtosis": "non-excess"}})


@dataclass(frozen=True)
class PBO:
    pbo: float
    n_combinations: int
    lambdas: tuple[dict, ...]


def pbo(matrix: Sequence[Sequence[float]], *, n_blocks: int,
        metric: Union[str, Callable[[Sequence[float]], float]]) -> PBO:
    rows = [as_numbers(f"matrix[{i}]", r) for i, r in enumerate(matrix)]
    if not rows:
        raise ValidationError("matrix is empty")
    N = len(rows[0])
    if N < 2 or any(len(r) != N for r in rows):
        raise ValidationError("matrix must be rectangular with at least 2 strategies (columns)")
    S = as_int("n_blocks", n_blocks, lo=2)
    if S % 2:
        raise ValidationError(f"n_blocks must be even, got {S}")
    T = len(rows)
    if T % S:
        raise ValidationError(f"{T} rows cannot be cut into {S} equal blocks")
    if isinstance(metric, str):
        as_choice("metric", metric, PBO_METRICS)
    elif not callable(metric):
        raise ValidationError(f"metric must be one of {PBO_METRICS} or a callable")

    def perf(idx: list[int], j: int) -> float:
        x = [rows[r][j] for r in idx]
        if callable(metric):
            return as_float("metric result", metric(x))
        m = sum(x) / len(x)
        if metric == "mean":
            return m
        sd = math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1)) if len(x) > 1 else 0.0
        if sd == 0:
            raise ValidationError("a strategy has zero spread in a half: its Sharpe is undefined")
        return m / sd

    b = T // S
    blocks = [list(range(k * b, (k + 1) * b)) for k in range(S)]
    lams = []
    for comb in itertools.combinations(range(S), S // 2):
        IS = [r for k in comb for r in blocks[k]]
        OOS = [r for k in range(S) if k not in comb for r in blocks[k]]
        pis = [perf(IS, j) for j in range(N)]
        po = [perf(OOS, j) for j in range(N)]
        best = max(range(N), key=lambda j: (pis[j], -j))
        rank = 1 + sum(1 for v in po if v < po[best])
        w = rank / (N + 1)
        lams.append({"is_blocks": comb, "best": best, "oos_rank": rank, "logit": math.log(w / (1 - w))})
    return PBO(sum(1 for x in lams if x["logit"] <= 0) / len(lams), len(lams), tuple(lams))


__all__: Any = ["DSR", "PBO", "deflated_sharpe", "deflated_sharpe_of_returns", "expected_max_sr", "pbo",
                "sample_moments"]

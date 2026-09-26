"""MDE and the three-way verdict (item 3, old item 7: 「MDE の計算」;
research-protocol §4.1 and §5: 「MDE を書けない主張は陰性として扱わない」).

    mde(n=, sd=, alpha=, power=, sides=, approx="normal")
        = (z(1 - alpha/sides) + z(power)) * sd / sqrt(n), with z the exact
        standard normal quantile (statistics.NormalDist), never a rounded 1.96.

    verdict(estimate=, se=, interest=, alpha=, power=, sides=, approx="normal", n=, sd=)
        陽性 = the effect is detected: |estimate / se| > z(1 - alpha/2) (two-sided)
               or estimate / se > z(1 - alpha) (one-sided, the positive side);
        陰性 = not detected AND the design's MDE (from its n and sd) is below
               the effect of interest -- an absence measured with power;
        不明 = not detected and the effect of interest <= MDE, OR the MDE
               cannot be written (n or sd not given).

`n` and `sd` are the DESIGN's (pre-registered) sample size and spread; the
realised standard error is not substituted for them, so a claim without a
stated design can never become 陰性 (the structure, not a convention, keeps
it 不明).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist
from typing import Optional

from ._args import as_choice, as_float, as_int, as_prob
from .errors import ValidationError

_N = NormalDist()
APPROX = ("normal",)
NEGATIVE, UNKNOWN, POSITIVE = "陰性", "不明", "陽性"


def _sides(v) -> int:
    s = as_int("sides", v)
    if s not in (1, 2):
        raise ValidationError(f"sides must be 1 or 2, got {s}")
    return s


def mde(*, n: int, sd: float, alpha: float, power: float, sides: int, approx: str) -> float:
    as_choice("approx", approx, APPROX)
    nn = as_int("n", n, lo=1)
    s = as_float("sd", sd, lo=0.0, lo_open=True)
    a, p, k = as_prob("alpha", alpha), as_prob("power", power), _sides(sides)
    return (_N.inv_cdf(1 - a / k) + _N.inv_cdf(p)) * s / math.sqrt(nn)


@dataclass(frozen=True)
class Verdict:
    label: str  # 陰性 | 不明 | 陽性
    z: float
    critical_z: float
    mde: Optional[float]
    interest: float
    reason: str


def verdict(*, estimate: float, se: float, interest: float, alpha: float, power: float, sides: int, approx: str,
            n: Optional[int] = None, sd: Optional[float] = None) -> Verdict:
    as_choice("approx", approx, APPROX)
    est = as_float("estimate", estimate)
    s = as_float("se", se, lo=0.0, lo_open=True)
    want = as_float("interest", interest, lo=0.0, lo_open=True)
    a, p, k = as_prob("alpha", alpha), as_prob("power", power), _sides(sides)
    z = est / s
    crit = _N.inv_cdf(1 - a / k)
    detected = abs(z) > crit if k == 2 else z > crit
    m = None
    if n is not None and sd is not None:
        m = mde(n=n, sd=sd, alpha=a, power=p, sides=k, approx=approx)
    elif (n is None) != (sd is None):
        raise ValidationError("give both n and sd of the design (or neither: then no MDE and no 陰性)")
    if detected:
        return Verdict(POSITIVE, z, crit, m, want, f"|z| = {abs(z):.4f} > {crit:.4f}" if k == 2 else f"z = {z:.4f} > {crit:.4f}")
    if m is None:
        return Verdict(UNKNOWN, z, crit, None, want, "MDE を書けない(設計の n と sd が無い)ので陰性にしない")
    if want > m:
        return Verdict(NEGATIVE, z, crit, m, want, f"検出されず、欲しい効果 {want:g} > MDE {m:.6g}")
    return Verdict(UNKNOWN, z, crit, m, want, f"検出されず、欲しい効果 {want:g} <= MDE {m:.6g}(検出力不足)")

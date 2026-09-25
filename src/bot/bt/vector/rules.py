"""Rules with a vector path and an event path that must agree bit for bit.

Both paths are built from the same two definitions, each written twice
(once over whole arrays, once one bar at a time), with the same float
operations in the same order:

  rolling mean  m_t = (c_{t-n+1} + ... + c_t) / n, summed left to right;
                None while fewer than n bars exist
  equity        e_0 = init_cash; e_t = e_{t-1} + p_{t-1} * (c_t - c_{t-1})
                (the position decided at bar t's close is held over bar
                t+1; no costs)

Rules (positions are `unit` or 0.0):
  SmaLongFlat(n, unit, init_cash)        p_t = unit when c_t > m_t(n)
  SmaCross(fast, slow, unit, init_cash)  p_t = unit when m_t(fast) > m_t(slow)
                                         (fast < slow)
`vector(close)` is the vector path; `event_strategy()` gives the core
strategy of the event path (event_path.run_event_rule). Output:
{"sma" | "fast"/"slow": [...], "position": [...], "equity": [...]}.
"""
from __future__ import annotations

import math
from collections import deque
from typing import Any, Optional, Sequence

import numpy as np

from ..core.events import BarEvent
from ..core.strategy import Strategy
from ..data.errors import VectorError


def _finite(x: Any, name: str) -> float:
    if type(x) is bool or not isinstance(x, (int, float)):
        raise VectorError(f"{name} must be a number, got {x!r}")
    f = float(x)
    if not math.isfinite(f):
        raise VectorError(f"{name} must be finite, got {x!r}")
    return f


def _n(x: Any, name: str) -> int:
    if type(x) is not int or x < 1:
        raise VectorError(f"{name} must be an int >= 1, got {x!r}")
    return x


# -- the two definitions, vector form ------------------------------------------
def rolling_mean(c: np.ndarray, n: int) -> np.ndarray:
    T = c.size
    out = np.full(T, np.nan)
    if T >= n:
        m = T - n + 1
        s = c[0:m].copy()
        for j in range(1, n):
            s = s + c[j:j + m]
        out[n - 1:] = s / n
    return out


def equity_curve(c: np.ndarray, pos: np.ndarray, init_cash: float) -> np.ndarray:
    if c.size == 0:
        return np.zeros(0)
    return np.cumsum(np.concatenate(([init_cash], pos[:-1] * (c[1:] - c[:-1]))))


def _close_array(close: Sequence) -> np.ndarray:
    c = np.asarray(list(close), dtype=np.float64)
    if c.ndim != 1 or not bool(np.all(np.isfinite(c))):
        raise VectorError("close must be a 1-d list of finite numbers")
    return c


def _series(a: np.ndarray) -> list:
    return [None if math.isnan(v) else float(v) for v in a.tolist()]


# -- the two definitions, one bar at a time ------------------------------------
class _RollingMean:
    def __init__(self, n: int) -> None:
        self.n = n
        self.w: deque = deque(maxlen=n)

    def push(self, c: float) -> Optional[float]:
        self.w.append(c)
        if len(self.w) < self.n:
            return None
        it = iter(self.w)
        s = next(it)
        for x in it:
            s = s + x
        return s / self.n


class _Equity:
    def __init__(self, init_cash: float) -> None:
        self.e = init_cash
        self.prev_c: Optional[float] = None
        self.prev_p = 0.0

    def push(self, c: float, p: float) -> float:
        if self.prev_c is not None:
            self.e = self.e + self.prev_p * (c - self.prev_c)
        self.prev_c, self.prev_p = c, p
        return self.e


class _BarRuleStrategy(Strategy):
    """Feeds each bar's close to `step` (the rule's one-bar form)."""

    def __init__(self, rule) -> None:
        self._rule = rule
        self._state = rule._event_state()
        self._eq = _Equity(rule.init_cash)
        self.out: dict = {k: [] for k in rule.series_names + ("position", "equity")}

    def on_event(self, event, ctx) -> None:
        if type(event) is not BarEvent:
            return
        c = float(event.close)
        series, p = self._rule._event_step(self._state, c)
        for k, v in zip(self._rule.series_names, series):
            self.out[k].append(v)
        self.out["position"].append(p)
        self.out["equity"].append(self._eq.push(c, p))

    def result(self) -> dict:
        return {k: list(v) for k, v in self.out.items()}


class SmaLongFlat:
    kind = "sma_long_flat"
    series_names = ("sma",)

    def __init__(self, n: int, unit: Any = 1, init_cash: Any = 0) -> None:
        self.n = _n(n, "n")
        self.unit = _finite(unit, "unit")
        self.init_cash = _finite(init_cash, "init_cash")

    @classmethod
    def from_mapping(cls, m: Any) -> "SmaLongFlat":
        if not isinstance(m, dict) or m.get("type") != cls.kind:
            raise VectorError(f"not a {cls.kind} rule: {m!r}")
        extra = sorted(set(m) - {"type", "n", "unit", "init_cash"})
        if extra or "n" not in m:
            raise VectorError(f"{cls.kind} takes n, unit, init_cash (got {sorted(m)})")
        return cls(m["n"], m.get("unit", 1), m.get("init_cash", 0))

    def vector(self, close: Sequence) -> dict:
        c = _close_array(close)
        sma = rolling_mean(c, self.n)
        pos = np.where(c > sma, self.unit, 0.0)  # nan compares False
        return {"sma": _series(sma), "position": [float(v) for v in pos.tolist()],
                "equity": [float(v) for v in equity_curve(c, pos, self.init_cash).tolist()]}

    def _event_state(self):
        return _RollingMean(self.n)

    def _event_step(self, rm: _RollingMean, c: float):
        m = rm.push(c)
        return (m,), (self.unit if (m is not None and c > m) else 0.0)

    def event_strategy(self) -> _BarRuleStrategy:
        return _BarRuleStrategy(self)


class SmaCross:
    kind = "sma_cross"
    series_names = ("fast", "slow")

    def __init__(self, fast: int, slow: int, unit: Any = 1, init_cash: Any = 0) -> None:
        self.fast = _n(fast, "fast")
        self.slow = _n(slow, "slow")
        if self.fast >= self.slow:
            raise VectorError(f"fast ({fast}) must be < slow ({slow})")
        self.unit = _finite(unit, "unit")
        self.init_cash = _finite(init_cash, "init_cash")

    @classmethod
    def from_mapping(cls, m: Any) -> "SmaCross":
        if not isinstance(m, dict) or m.get("type") != cls.kind:
            raise VectorError(f"not a {cls.kind} rule: {m!r}")
        extra = sorted(set(m) - {"type", "fast", "slow", "unit", "init_cash"})
        if extra or "fast" not in m or "slow" not in m:
            raise VectorError(f"{cls.kind} takes fast, slow, unit, init_cash (got {sorted(m)})")
        return cls(m["fast"], m["slow"], m.get("unit", 1), m.get("init_cash", 0))

    def vector(self, close: Sequence) -> dict:
        c = _close_array(close)
        f, s = rolling_mean(c, self.fast), rolling_mean(c, self.slow)
        pos = np.where(f > s, self.unit, 0.0)
        return {"fast": _series(f), "slow": _series(s), "position": [float(v) for v in pos.tolist()],
                "equity": [float(v) for v in equity_curve(c, pos, self.init_cash).tolist()]}

    def _event_state(self):
        return (_RollingMean(self.fast), _RollingMean(self.slow))

    def _event_step(self, st, c: float):
        f, s = st[0].push(c), st[1].push(c)
        return (f, s), (self.unit if (f is not None and s is not None and f > s) else 0.0)

    def event_strategy(self) -> _BarRuleStrategy:
        return _BarRuleStrategy(self)


RULES = {SmaLongFlat.kind: SmaLongFlat, SmaCross.kind: SmaCross}


def rule_from_mapping(m: Any):
    if not isinstance(m, dict) or m.get("type") not in RULES:
        raise VectorError(f"unknown rule {m!r} (known: {sorted(RULES)})")
    return RULES[m["type"]].from_mapping(m)

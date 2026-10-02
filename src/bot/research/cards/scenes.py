"""Scene variables (W1 spec C4), each computed at a decision time t from
what was known at t only.

| variable              | computation                                                        |
|-----------------------|--------------------------------------------------------------------|
| vol_1h / vol_1d / vol_1w | standard deviation (ddof 1) of the 1-minute log moves whose bar  |
|                       | closed in (t - window, t]                                           |
| vr_1h / vr_1d / vr_1w | variance ratio over the same windows (below; needs `vr_q_bars`)     |
| hour_jst, weekday_jst | the hour and the weekday (Monday = 0) of t in Japan time (UTC+9)    |
| venue                 | the run's venue name                                                |
| regime                | the label of the last (from_ns, label) boundary at or before t      |
| ref:<name>            | the newest row of a reference series available at t (run.py)       |

A 1-minute log move is log(close_b / close_a) of two non-empty 1-minute bars
a, b with b opening at a's close (a move across a gap or an empty bar is not
a 1-minute move and is left out). Windows: 1 hour, 1 day, 1 week (spec C4:
the natural units of the clock, fixed before measuring, nothing to tune).

Variance ratio (spec C4 names it and its windows, not its horizon q, so q is
a required argument with no default; `None` leaves the vr variables out):
    vr = var(q-minute moves) / (q * var(1-minute moves)),
both sample variances (ddof 1) inside the window, a q-minute move being the
sum of q consecutive 1-minute moves that all lie in the window.

Position: a continuous variable is also expressed as its position in its
own distribution over the past 365 days (spec C4): at t, among the
variable's finite values at the decisions in (t - 365 days, t) (t itself
excluded), (number below + 0.5 * number equal) / number. While t is less
than 365 days after the start of the series (the first bar's open), the
position is not used for the scene estimates (`eligible_position` is
False); the value itself still exists.

Category variables have no position; each value is its own group.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

import numpy as np

from .pnl import PnL
from .run import CardRun

NS = 1_000_000_000
MINUTE_NS = 60 * NS
HOUR_NS = 3600 * NS
DAY_NS = 86_400 * NS
WEEK_NS = 7 * DAY_NS
WINDOWS = (("1h", HOUR_NS), ("1d", DAY_NS), ("1w", WEEK_NS))
POSITION_WINDOW_NS = 365 * DAY_NS
JST_OFFSET_NS = 9 * HOUR_NS
REF_KINDS = ("category", "continuous")


@dataclass(frozen=True)
class SceneVar:
    name: str
    kind: str  # "continuous" | "category"
    value: np.ndarray  # per decision: float (continuous; NaN = undefined) or str label ("" = undefined)
    position: Optional[np.ndarray] = None  # continuous: position in [0, 1] (NaN = undefined)
    eligible_position: Optional[np.ndarray] = None  # continuous: position usable (365-day rule and defined)


def one_minute_moves(run: CardRun) -> tuple[np.ndarray, np.ndarray]:
    """(end time of the later bar, log move) of every 1-minute move (module docstring)."""
    ne = np.flatnonzero(run.volume > 0)
    if len(ne) < 2:
        return np.empty(0, dtype=np.int64), np.empty(0)
    a, b = ne[:-1], ne[1:]
    ok = (run.start_ns[b] == run.end_ns[a]) & (run.end_ns[b] - run.start_ns[b] == MINUTE_NS) & \
         (run.end_ns[a] - run.start_ns[a] == MINUTE_NS)
    return run.end_ns[b][ok], np.log(run.close[b][ok] / run.close[a][ok])


def _window_sums(times: np.ndarray, x: np.ndarray, t: np.ndarray, lo_excl: np.ndarray) -> tuple:
    """Sums of x, x^2 and counts of the items with lo_excl < time <= t."""
    c1 = np.concatenate(([0.0], np.cumsum(x)))
    c2 = np.concatenate(([0.0], np.cumsum(x * x)))
    hi = np.searchsorted(times, t, side="right")
    lo = np.searchsorted(times, lo_excl, side="right")
    n = hi - lo
    return c1[hi] - c1[lo], c2[hi] - c2[lo], n


def _var(s1, s2, n) -> np.ndarray:
    with np.errstate(invalid="ignore", divide="ignore"):
        v = (s2 - s1 * s1 / n) / (n - 1)
    v = np.where(n >= 2, v, np.nan)
    return np.where(v < 0, 0.0, v)  # rounding of a constant series


def local_vol(times: np.ndarray, moves: np.ndarray, t: np.ndarray, window_ns: int) -> np.ndarray:
    s1, s2, n = _window_sums(times, moves, t, t - window_ns)
    return np.sqrt(_var(s1, s2, n))


def variance_ratio(times: np.ndarray, moves: np.ndarray, t: np.ndarray, window_ns: int, q: int) -> np.ndarray:
    if type(q) is not int or q < 2:
        raise ValueError(f"vr_q_bars must be an int >= 2, got {q!r}")
    s1, s2, n = _window_sums(times, moves, t, t - window_ns)
    v1 = _var(s1, s2, n)
    # q-minute moves: q consecutive 1-minute moves (each one minute after the previous)
    k = len(moves)
    if k < q:
        return np.full(len(t), np.nan)
    consec = np.concatenate(([False], np.diff(times) == MINUTE_NS))
    idx = np.arange(k)  # chain length of consecutive moves ending at each move: reset where a move is not consecutive
    last_break = np.maximum.accumulate(np.where(~consec, idx, 0))
    run_len = idx - last_break + 1
    c = np.concatenate(([0.0], np.cumsum(moves)))
    ends = np.flatnonzero(run_len >= q)
    qs = c[ends + 1] - c[ends + 1 - q]
    qt = times[ends]
    # a q-move lies in (t - W, t] when its first 1-minute move's end > t - W, i.e. its end > t - W + (q-1) min
    a1, a2, m = _window_sums(qt, qs, t, t - window_ns + (q - 1) * MINUTE_NS)
    vq = _var(a1, a2, m)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = vq / (q * v1)
    return np.where((v1 > 0) & np.isfinite(vq), out, np.nan)


def past_position(times: np.ndarray, values: np.ndarray, window_ns: int = POSITION_WINDOW_NS) -> np.ndarray:
    """Position of each finite value among the finite values at earlier times in
    (time - window, time): (below + 0.5 * equal) / count; NaN when there is none.
    `times` strictly increasing; `window_ns` a whole number of days. Exact, by day
    blocks: a sorted array of the values of the window at the day's start, minus the
    ones that leave during the day, plus the day's earlier ones."""
    times = np.asarray(times, dtype=np.int64)
    values = np.asarray(values, dtype=float)
    if window_ns % DAY_NS or window_ns <= 0:
        raise ValueError("window_ns must be a positive whole number of days")
    n = len(times)
    out = np.full(n, np.nan)
    if n == 0:
        return out
    if np.any(np.diff(times) <= 0):
        raise ValueError("times must be strictly increasing")
    fin = np.isfinite(values)
    ft, fv = times[fin], values[fin]
    fidx = np.flatnonzero(fin)
    if len(ft) == 0:
        return out
    day0 = (int(ft[0]) // DAY_NS) * DAY_NS
    day_last = (int(ft[-1]) // DAY_NS) * DAY_NS
    win = np.empty(0)  # sorted values with time in [d0 - W, d0)
    # the window at the first day's start is empty (no earlier finite value)
    d0 = day0
    while d0 <= day_last:
        lo_d, hi_d = np.searchsorted(ft, [d0, d0 + DAY_NS], side="left")
        lo_e, hi_e = np.searchsorted(ft, [d0 - window_ns, d0 - window_ns + DAY_NS], side="left")
        if hi_d > lo_d:
            vD, tD = fv[lo_d:hi_d], ft[lo_d:hi_d]
            vE, tE = fv[lo_e:hi_e], ft[lo_e:hi_e]
            below = np.searchsorted(win, vD, side="left").astype(float)
            le = np.searchsorted(win, vD, side="right").astype(float)
            cnt = np.full(len(vD), float(len(win)))
            if len(vE):
                gone = tE[None, :] <= (tD[:, None] - window_ns)  # left the window by t: time <= t - W
                below -= (gone & (vE[None, :] < vD[:, None])).sum(axis=1)
                le -= (gone & (vE[None, :] <= vD[:, None])).sum(axis=1)
                cnt -= gone.sum(axis=1)
            m = len(vD)
            earlier = np.tri(m, m, -1, dtype=bool)  # [k, j]: j < k
            below += (earlier & (vD[None, :] < vD[:, None])).sum(axis=1)
            le += (earlier & (vD[None, :] <= vD[:, None])).sum(axis=1)
            cnt += earlier.sum(axis=1)
            equal = le - below
            with np.errstate(invalid="ignore", divide="ignore"):
                pos = (below + 0.5 * equal) / cnt
            out[fidx[lo_d:hi_d]] = np.where(cnt > 0, pos, np.nan)
        # next day's window: drop E (times in [d0 - W, d0 - W + 1d)), add D (times in [d0, d0 + 1d))
        if hi_e > lo_e:
            es = np.sort(fv[lo_e:hi_e])
            first = np.searchsorted(es, es, side="left")
            rank = np.arange(len(es)) - first
            win = np.delete(win, np.searchsorted(win, es, side="left") + rank)
        if hi_d > lo_d:
            ds = np.sort(fv[lo_d:hi_d])
            win = np.insert(win, np.searchsorted(win, ds, side="left"), ds)
        d0 += DAY_NS
    return out


def _labels(x: np.ndarray) -> np.ndarray:
    return np.array(["" if not np.isfinite(v) else float.__repr__(float(v)) for v in x], dtype=object)


def scene_vars(run: CardRun, p: PnL, *, vr_q_bars: Optional[int], regimes: Optional[Sequence[tuple[int, str]]],
               ref_scenes: Mapping[str, str]) -> list[SceneVar]:
    """Every scene variable at the decisions of `p` (module docstring)."""
    t = p.t_ns
    widths = run.end_ns - run.start_ns
    if np.any(widths != MINUTE_NS):
        raise ValueError("the scene variables are defined on 1-minute bars (spec C4); this run has other bars")
    series_start = int(run.start_ns[0])
    old_enough = (t - series_start) >= POSITION_WINDOW_NS
    mt, mv = one_minute_moves(run)
    out: list[SceneVar] = []

    def continuous(name: str, value: np.ndarray) -> SceneVar:
        pos = past_position(t, value)
        return SceneVar(name, "continuous", value, pos, old_enough & np.isfinite(pos))

    for label, w in WINDOWS:
        out.append(continuous(f"vol_{label}", local_vol(mt, mv, t, w)))
    if vr_q_bars is not None:
        for label, w in WINDOWS:
            out.append(continuous(f"vr_{label}", variance_ratio(mt, mv, t, w, vr_q_bars)))
    jst = t + JST_OFFSET_NS
    hours = (jst // HOUR_NS) % 24
    weekday = (jst // DAY_NS + 3) % 7  # 1970-01-01 was a Thursday (Monday = 0)
    out.append(SceneVar("hour_jst", "category", np.array([f"{int(h):02d}" for h in hours], dtype=object)))
    out.append(SceneVar("weekday_jst", "category", np.array([str(int(d)) for d in weekday], dtype=object)))
    out.append(SceneVar("venue", "category", np.array([run.venue] * len(t), dtype=object)))
    if regimes is not None:
        bounds = list(regimes)
        if not bounds:
            raise ValueError("regimes: give at least one (from_ns, label), or None to leave the variable out")
        froms = [b[0] for b in bounds]
        if any(type(f) is not int for f in froms) or any(b >= a for a, b in zip(froms[1:], froms[:-1])):
            raise ValueError("regimes: from_ns must be ints, strictly increasing")
        if any(type(b[1]) is not str or not b[1] for b in bounds):
            raise ValueError("regimes: labels must be non-empty str")
        k = np.searchsorted(np.array(froms, dtype=np.int64), t, side="right") - 1
        lab = np.array([bounds[i][1] if i >= 0 else "" for i in k], dtype=object)
        out.append(SceneVar("regime", "category", lab))
    for name, kind in sorted(ref_scenes.items()):
        if kind not in REF_KINDS:
            raise ValueError(f"ref_scenes[{name!r}] must be one of {REF_KINDS}, got {kind!r}")
        if name not in run.ref_value:
            raise ValueError(f"ref_scenes names {name!r}, which the run was not given")
        v = run.ref_value[name][p.bar]
        if kind == "category":
            out.append(SceneVar(f"ref:{name}", "category", _labels(v)))
        else:
            out.append(continuous(f"ref:{name}", v))
    return out


__all__ = ["DAY_NS", "HOUR_NS", "MINUTE_NS", "POSITION_WINDOW_NS", "SceneVar", "WINDOWS", "local_vol",
           "one_minute_moves", "past_position", "scene_vars", "variance_ratio"]

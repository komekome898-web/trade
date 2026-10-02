"""What the measurement gives for one card run (W1 spec C5).

    out = measure_card(card_md_path, run, seed=, control_seed=, regimes=, daily_path=)   # settings from CARD.md
    out = measure(run, seed=, control_seed=, vr_q_bars=, regimes=,                       # settings given (tests)
                  day_zone=, ref_scenes=, daily_path=)

`out` is plain JSON (`bot.bt.repro.canonical` writes it; no NaN: an undefined
number is None with the reason next to it). Where each item of C5 is:

C5 a (mean P_t, overall and per scene):
    overall.mean_bp; scenes.<v>.bins.<group>.mean_bp; scenes.<v>.coef_value / coef_position.
    The mean of P_t (pnl.py) over all decisions and per group of a scene variable. For a continuous
    variable also the slope of P_t on the variable standardised (bp per 1 sd), on its value and on its
    365-day position. Groups: for a continuous variable the thirds of its position [0, 1/3), [1/3, 2/3),
    [2/3, 1] (display); for a category variable its values.
C5 b (drift removed): overall.drift_removed_bp; scenes.<v>.bins.<group>.drift_removed_bp.
    e_t * (r_{t+1} - the mean of r in the same group over the measured period); overall: minus the mean of
    r over all decisions.
C5 c (intervals): every stat's ci / se. Circular block bootstrap (`bot.bt.validation.bootstrap`),
    1,000 resamples, a fixed seed, 95% percentile interval. Block length (spec C5 c as corrected on
    2026-10-02) L = max(ceil(b), 1,440 bars), b = the Politis-White circular block length of the P_t series
    (blocklen.py). When L >= n / 2 neither intervals nor the control are given (block.degenerate and its
    reason). The median length of the runs of decisions with exposure != 0 is shown as a diagnostic only
    (block.median_nonzero_run); it does not enter L.
C5 d (control): mean_bp.control_percentile; control.shifts. The exposures shifted circularly by k, k drawn
    200 times from [L, n - L] with a fixed seed (at least L both ways round); the same mean of each
    shifted series; the actual mean's percentile among the 200 = 100 * (below + 0.5 * equal) / 200.
C5 e (power): every mean's mde, next to its 95% interval (ci = [lower end, upper end]).
    `bot.bt.validation.power`: the MDE at 5% two-sided and 80% power = mde(n = the group's decisions,
    sd = bootstrap se * sqrt(n)). No word verdict (不明 / 小さい) is given in stages 2 and 3 (the lead's
    answer, 2026-10-02): it needs an effect of interest, which taken from costs would cut by cost upstream
    (A-8) and set without a basis would be A-12. `verdict` always reads 未判定; the interval's ends say which
    effects this data already rules out.
C5 f (frequency): frequency. The share of decisions with exposure != 0; the number of changes.
C5 g (breakdown): breakdown. Per venue and per UTC year: n, sum and mean of P_t.
C5 h (daily series): daily. The sum of P_t per day (zone `day_zone`) written to `daily_path`
    (CSV: day,pnl_bp,n), and its sha256.

All the bootstrap statistics of one run are taken from ONE call of
`block_bootstrap_ci`: its statistic (the overall mean, the first entry)
also records every other entry for the same resample, so every interval is
computed on the same resamples, with the library's own percentile rule
(np.quantile, linear), checked against the library's interval for the first
entry. `block` records L, n and n / L, so a degenerate block (L close to n:
every resample is nearly a rotation of the whole series, and the interval
collapses) is visible in every output.

Fixed numbers (all from the spec): 1,000 resamples, 200 shifts, 5% two-sided,
80% power, 1,440 bars, thirds, the circular method, L >= n / 2. Required arguments without a default are the
choices the spec leaves open (see each one below).
"""
from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

import numpy as np

from bot.bt.data.reference import parse_decl
from bot.bt.validation import block_bootstrap_ci, mde

from . import cardmd
from .blocklen import politis_white
from .card import CardError
from .pnl import PnL, pnl
from .run import CardRun
from .scenes import DAY_NS, HOUR_NS, SceneVar, scene_vars

N_RESAMPLES = 1000  # C5 c
N_SHIFTS = 200  # C5 d
ALPHA = 0.05  # C5 e (and the 95% intervals of T1, T4, T5)
POWER = 0.80  # C5 e
MIN_BLOCK_BARS = 1440  # C5 c: one day of 1-minute bars
METHOD = "circular"  # C5 c
THIRDS = 3  # C5 a, b
DAY_ZONES = {"UTC": 0, "Asia/Tokyo": 9 * HOUR_NS}  # Japan has no DST: a fixed +9 h
NO_VERDICT = "未判定(段 2・3 では関心の大きさを置かない)"


def nonzero_runs(exposure: np.ndarray) -> np.ndarray:
    """Lengths of the runs of consecutive decisions with exposure != 0."""
    nz = np.asarray(exposure) != 0
    if not nz.any():
        return np.empty(0, dtype=np.int64)
    d = np.diff(np.concatenate(([0], nz.astype(np.int8), [0])))
    starts, ends = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    return ends - starts


def median_nonzero_run(exposure: np.ndarray) -> Optional[float]:
    """The median length of the runs of exposure != 0 (a diagnostic of C5 c; not used for L)."""
    runs = nonzero_runs(exposure)
    return float(np.median(runs)) if len(runs) else None


def block_length(p: PnL) -> tuple[int, dict]:
    """(L, what decided it): L = max(ceil(Politis-White b of the P_t series), 1,440) (C5 c)."""
    bl = politis_white(p.pnl_bp)
    L = max(int(math.ceil(bl.b)), MIN_BLOCK_BARS)
    return L, {"rule": "max(ceil(Politis-White circular b of P_t), 1440)", "pw_b": bl.b,
               "pw_b_uncapped": bl.b_uncapped, "pw_b_max": bl.b_max, "pw_m_hat": bl.m_hat, "pw_M": bl.M,
               "median_nonzero_run": median_nonzero_run(p.exposure)}


@dataclass
class _Grouping:
    name: str
    labels: list
    codes: np.ndarray  # per decision: 0..G-1, or G = not in any group
    b: np.ndarray  # drift-removed P per decision (0 where not in a group)
    r_mean: np.ndarray  # period mean of r per group


def _grouping(name: str, labels: list, codes: np.ndarray, e: np.ndarray, r: np.ndarray) -> _Grouping:
    G = len(labels)
    cnt = np.bincount(codes, minlength=G + 1)[:G]
    sr = np.bincount(codes, weights=r, minlength=G + 1)[:G]
    with np.errstate(invalid="ignore", divide="ignore"):
        r_mean = np.where(cnt > 0, sr / cnt, np.nan)
    rm_ext = np.concatenate((r_mean, [0.0]))
    b = np.where(codes < G, e * (r - rm_ext[codes]), 0.0)
    return _Grouping(name, labels, codes, b, r_mean)


def _codes_from_labels(values: np.ndarray) -> tuple[list, np.ndarray]:
    labels = sorted({v for v in values if v != ""})
    pos = {v: i for i, v in enumerate(labels)}
    G = len(labels)
    return labels, np.array([pos.get(v, G) for v in values], dtype=np.int64)


THIRD_LABELS = ["[0,1/3)", "[1/3,2/3)", "[2/3,1]"]


def _third_codes(var: SceneVar) -> np.ndarray:
    pos = np.where(var.eligible_position, var.position, 0.0)
    k = np.minimum(np.floor(pos * THIRDS), THIRDS - 1).astype(np.int64)
    return np.where(var.eligible_position, k, THIRDS)


@dataclass
class _Reg:
    name: str  # "<var>.coef_value" | "<var>.coef_position"
    mask: np.ndarray
    z: np.ndarray  # standardised over the mask (0 elsewhere)


def _standardised(x: np.ndarray, mask: np.ndarray) -> Optional[np.ndarray]:
    if mask.sum() < 3:
        return None
    m, s = x[mask].mean(), x[mask].std()
    if not s > 0:
        return None
    return np.where(mask, (x - m) / s, 0.0)


class _Stats:
    """The vector of statistics of one (re)sample, given the indices of its decisions."""

    def __init__(self, P: np.ndarray, groupings: list[_Grouping], regs: list[_Reg]) -> None:
        self.P, self.groupings, self.regs = P, groupings, regs
        self.names: list[str] = []
        for g in groupings:
            for lab in g.labels:
                self.names.append(f"{g.name}|{lab}|mean_bp")
                self.names.append(f"{g.name}|{lab}|drift_removed_bp")
        for rg in regs:
            self.names.append(rg.name)

    def __call__(self, idx: np.ndarray) -> np.ndarray:
        P = self.P[idx]
        parts = []
        for g in self.groupings:
            G = len(g.labels)
            c = g.codes[idx]
            cnt = np.bincount(c, minlength=G + 1)[:G].astype(float)
            sp = np.bincount(c, weights=P, minlength=G + 1)[:G]
            sb = np.bincount(c, weights=g.b[idx], minlength=G + 1)[:G]
            with np.errstate(invalid="ignore", divide="ignore"):
                mp = np.where(cnt > 0, sp / cnt, np.nan)
                mb = np.where(cnt > 0, sb / cnt, np.nan)
            parts.append(np.stack([mp, mb], axis=1).ravel())  # per group: mean_bp, drift_removed_bp (as `names`)
        out = list(np.concatenate(parts)) if parts else []
        for rg in self.regs:
            m = rg.mask[idx]
            n = m.sum()
            z, y = rg.z[idx][m], P[m]
            if n < 3:
                out.append(np.nan)
                continue
            szz = (z * z).sum() - z.sum() ** 2 / n
            out.append(((z * y).sum() - z.sum() * y.sum() / n) / szz if szz > 0 else np.nan)
        return np.array(out, dtype=float)


def _num(x) -> Optional[float]:
    x = float(x)
    return x if math.isfinite(x) else None


def _bootstrap(stats: _Stats, n: int, L: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """(estimates, resampled vectors [R, k]) from one call of block_bootstrap_ci."""
    seen: list[np.ndarray] = []

    def statistic(xs: np.ndarray) -> float:
        v = stats(xs.astype(np.int64))
        seen.append(v)
        return float(v[0])

    ci = block_bootstrap_ci([float(i) for i in range(n)], block_len=L, n_resamples=N_RESAMPLES, seed=seed,
                            alpha=ALPHA, method=METHOD, statistic=statistic)
    if len(seen) != N_RESAMPLES + 1:  # pragma: no cover - the library calls the statistic R times, then once on x
        raise RuntimeError(f"the bootstrap called its statistic {len(seen)} times, not {N_RESAMPLES + 1}")
    reps, est = np.array(seen[:N_RESAMPLES]), seen[N_RESAMPLES]
    lo, hi = np.quantile(reps[:, 0], [ALPHA / 2, 1 - ALPHA / 2])
    if (float(lo), float(hi)) != (ci.lo, ci.hi):  # pragma: no cover - the same rule on the same numbers
        raise RuntimeError("the recorded resamples do not reproduce the library's interval")
    return est, reps


def _stat(est: float, reps: np.ndarray, n: int, *, mean: bool) -> dict:
    out: dict = {"estimate": _num(est), "n": int(n)}
    if not np.all(np.isfinite(reps)):
        out.update(ci=None, se=None, note="no interval: L >= n / 2 (block.degenerate)"
                   if np.all(np.isnan(reps)) else "a resample had no decision in this group")
        if mean:
            out.update(mde=None, verdict=None)
        return out
    lo, hi = np.quantile(reps, [ALPHA / 2, 1 - ALPHA / 2])
    se = float(np.std(reps, ddof=1))
    out.update(ci=[float(lo), float(hi)], se=se)
    if not mean:
        return out
    if not se > 0:
        out.update(mde=None, verdict=None, note="bootstrap se = 0 (every resample gives the same mean)")
        return out
    out["mde"] = mde(n=int(n), sd=se * math.sqrt(n), alpha=ALPHA, power=POWER, sides=2, approx="normal")
    out["verdict"] = NO_VERDICT
    return out


def _controls(e: np.ndarray, r: np.ndarray, groupings: list[_Grouping], L: int, seed: int) -> tuple:
    """(shifts, control means [N_SHIFTS, k] in the order of the mean_bp entries) or (None, reason)."""
    n = len(e)
    if n < 2 * L:
        return None, f"n = {n} < 2L = {2 * L}: no shift of at least L both ways round exists"
    rng = np.random.default_rng(seed)
    shifts = rng.integers(L, n - L + 1, size=N_SHIFTS)
    rows = []
    for k in shifts:
        Pk = np.roll(e, int(k)) * r
        row = []
        for g in groupings:
            G = len(g.labels)
            cnt = np.bincount(g.codes, minlength=G + 1)[:G].astype(float)
            sp = np.bincount(g.codes, weights=Pk, minlength=G + 1)[:G]
            with np.errstate(invalid="ignore", divide="ignore"):
                row.extend(np.where(cnt > 0, sp / cnt, np.nan))
        rows.append(row)
    return [int(k) for k in shifts], np.array(rows, dtype=float)


def _percentile(actual: float, controls: np.ndarray) -> Optional[float]:
    if not (math.isfinite(actual) and np.all(np.isfinite(controls))):
        return None
    below = float(np.sum(controls < actual))
    equal = float(np.sum(controls == actual))
    return 100.0 * (below + 0.5 * equal) / len(controls)


def daily_rows(p: PnL, day_zone: str) -> list[tuple[str, float, int]]:
    """(day, sum of P_t, n) per day of the decision time in `day_zone` (C5 h)."""
    if day_zone not in DAY_ZONES:
        raise ValueError(f"day_zone must be one of {sorted(DAY_ZONES)}, got {day_zone!r}")
    day = (p.t_ns + DAY_ZONES[day_zone]) // DAY_NS
    uniq, inv = np.unique(day, return_inverse=True)
    s = np.bincount(inv, weights=p.pnl_bp)
    c = np.bincount(inv)
    labels = np.datetime_as_string((uniq * DAY_NS).astype("datetime64[ns]"), unit="D")
    return [(str(d), float(v), int(k)) for d, v, k in zip(labels, s, c)]


def write_daily(rows: Sequence[tuple[str, float, int]], path: str) -> str:
    text = "day,pnl_bp,n\n" + "".join(f"{d},{float.__repr__(v)},{k}\n" for d, v, k in rows)
    data = text.encode("utf-8")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    return hashlib.sha256(data).hexdigest()


def read_daily(path: str) -> dict[str, float]:
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    if not lines or lines[0] != "day,pnl_bp,n":
        raise ValueError(f"{path}: not a daily series written by write_daily")
    out = {}
    for ln in lines[1:]:
        d, v, _k = ln.split(",")
        out[d] = float(v)
    return out


def daily_correlation(a: Mapping[str, float], b: Mapping[str, float], *, block_days: int, seed: int) -> dict:
    """Pearson correlation of two daily series on their common days, with a
    95% block-bootstrap interval (blocks of `block_days` days; for two cards,
    the larger of their block lengths L in whole days, rounded up)."""
    days = sorted(set(a) & set(b))
    if len(days) < 3:
        raise ValueError(f"{len(days)} common days; a correlation needs at least 3")
    x = np.array([a[d] for d in days])
    y = np.array([b[d] for d in days])

    def corr(xs: np.ndarray) -> float:
        i = xs.astype(np.int64)
        return float(np.corrcoef(x[i], y[i])[0, 1])

    ci = block_bootstrap_ci([float(i) for i in range(len(days))], block_len=block_days, n_resamples=N_RESAMPLES,
                            seed=seed, alpha=ALPHA, method=METHOD, statistic=corr)
    return {"estimate": ci.estimate, "ci": [ci.lo, ci.hi], "se": ci.se, "n_days": len(days),
            "block_days": block_days, "method": METHOD, "seed": seed}


def measure(run: CardRun, *, seed: int, control_seed: int,
            vr_q_bars: Optional[int], regimes: Optional[Sequence[tuple[int, str]]], day_zone: str,
            ref_scenes: Mapping[str, str], daily_path: str) -> dict:
    """C5 a..h for one run (module docstring). Arguments without a default
    are the choices the spec does not fix:
      seed, control_seed   the fixed seeds of c and d
      vr_q_bars    the horizon q of the variance ratio (None: no vr variables)
      regimes      the (from_ns, label) boundaries of the 制度 variable (None: no such variable)
      day_zone     the day boundary of h ("UTC" | "Asia/Tokyo")
      ref_scenes   reference series used as scene variables: name -> "category" | "continuous"
      daily_path   the file h is written to"""
    p = pnl(run)
    L, how = block_length(p)
    return _measure_with_block(run, p, L, how, seed=seed, control_seed=control_seed,
                               vr_q_bars=vr_q_bars, regimes=regimes, day_zone=day_zone,
                               ref_scenes=ref_scenes, daily_path=daily_path)


def _measure_with_block(run: CardRun, p: PnL, L: int, how: dict, *, seed: int,
                        control_seed: int, vr_q_bars: Optional[int],
                        regimes: Optional[Sequence[tuple[int, str]]], day_zone: str,
                        ref_scenes: Mapping[str, str], daily_path: str) -> dict:
    for s, what in ((seed, "seed"), (control_seed, "control_seed")):
        if type(s) is not int:
            raise ValueError(f"{what} must be an int, got {s!r}")
    e, r, P = p.exposure, p.r_bp, p.pnl_bp
    n = len(P)
    variables = scene_vars(run, p, vr_q_bars=vr_q_bars, regimes=regimes, ref_scenes=ref_scenes)
    all_codes = np.zeros(n, dtype=np.int64)
    groupings = [_grouping("overall", ["all"], all_codes, e, r)]
    regs: list[_Reg] = []
    scene_info: dict = {}
    for v in variables:
        info: dict = {"kind": v.kind}
        if v.kind == "continuous":
            codes = _third_codes(v)
            labels = list(THIRD_LABELS)
            vm = np.isfinite(v.value)
            info["n_value"] = int(vm.sum())
            info["n_position"] = int(v.eligible_position.sum())
            zv = _standardised(v.value, vm)
            if zv is not None:
                regs.append(_Reg(f"{v.name}|coef_value", vm, zv))
            zp = _standardised(np.where(v.eligible_position, v.position, 0.0), v.eligible_position)
            if zp is not None:
                regs.append(_Reg(f"{v.name}|coef_position", v.eligible_position.copy(), zp))
        else:
            labels, codes = _codes_from_labels(v.value)
            info["n_value"] = int((codes < len(labels)).sum())
        info["n_used"] = int((codes < len(labels)).sum())
        scene_info[v.name] = info
        if info["n_used"] > 0:
            groupings.append(_grouping(v.name, labels, codes, e, r))
    stats = _Stats(P, groupings, regs)
    degenerate = 2 * L >= n
    if degenerate:
        # C5 c: L >= n / 2 -- at most two blocks; at L = n every resample is a rotation of the series and gives
        # the same mean. No interval and no control are reported (block.degenerate says why).
        est = stats(np.arange(n, dtype=np.int64))
        reps = np.full((N_RESAMPLES, len(est)), np.nan)
    else:
        est, reps = _bootstrap(stats, n, L, seed)
    shifts, ctrl = _controls(e, r, groupings, L, control_seed) if not degenerate else (
        None, f"L = {L} >= n / 2 = {n / 2}: no control (C5 c)")
    col = {name: k for k, name in enumerate(stats.names)}
    mean_cols = [k for k, nm in enumerate(stats.names) if nm.endswith("|mean_bp")]
    ctrl_col = {k: j for j, k in enumerate(mean_cols)}

    def stat_of(name: str, n_items: int, *, mean: bool) -> dict:
        k = col[name]
        s = _stat(est[k], reps[:, k], n_items, mean=mean)
        if name.endswith("|mean_bp"):
            if shifts is None:
                s["control_percentile"] = None
            else:
                s["control_percentile"] = _percentile(float(est[k]), ctrl[:, ctrl_col[k]])
        return s

    def bins_of(g: _Grouping) -> dict:
        G = len(g.labels)
        cnt = np.bincount(g.codes, minlength=G + 1)[:G]
        out = {}
        for j, lab in enumerate(g.labels):
            out[lab] = {"n": int(cnt[j]), "r_mean_bp": _num(g.r_mean[j]),
                        "mean_bp": stat_of(f"{g.name}|{lab}|mean_bp", int(cnt[j]), mean=True),
                        "drift_removed_bp": stat_of(f"{g.name}|{lab}|drift_removed_bp", int(cnt[j]), mean=True)}
        return out

    overall = bins_of(groupings[0])["all"]
    for g in groupings[1:]:
        scene_info[g.name]["bins"] = bins_of(g)
    for rg in regs:
        var, which = rg.name.split("|")
        scene_info[var][which] = stat_of(rg.name, int(rg.mask.sum()), mean=False)
    # f
    dec = np.flatnonzero(run.decided)
    e_all = run.exposure[dec]
    frequency = {"n_decisions": int(len(e_all)), "nonzero_share": float(np.mean(e_all != 0)),
                 "changes": int(np.sum(e_all[1:] != e_all[:-1]))}
    # g
    years = p.t_ns.astype("datetime64[ns]").astype("datetime64[Y]").astype(np.int64) + 1970
    by_year = {}
    for y in np.unique(years):
        m = years == y
        by_year[str(int(y))] = {"n": int(m.sum()), "sum_bp": float(P[m].sum()), "mean_bp": float(P[m].mean())}
    breakdown = {"venue": {run.venue: {"n": n, "sum_bp": float(P.sum()), "mean_bp": float(P.mean())}},
                 "year_utc": by_year}
    # h
    rows = daily_rows(p, day_zone)
    daily = {"path": os.path.basename(daily_path), "zone": day_zone, "days": len(rows),
             "sha256": write_daily(rows, daily_path)}
    waited = p.fill_wait_ns > 0
    return {
        "card": run.card, "venue": run.venue, "symbol": run.symbol,
        "n_bars": int(len(run.end_ns)), "n_decisions": int(p.n_decisions), "n_pnl": n,
        "n_undefined": int(p.n_undefined),
        "settings": {"method": METHOD, "seed": seed, "control_seed": control_seed, "n_resamples": N_RESAMPLES,
                     "n_shifts": N_SHIFTS, "alpha": ALPHA, "power": POWER,
                     "vr_q_bars": vr_q_bars, "regimes": None if regimes is None else [list(x) for x in regimes],
                     "day_zone": day_zone, "ref_scenes": dict(sorted(ref_scenes.items()))},
        "block": {**how, "block_len": int(L), "n": n, "n_over_block": n / L,
                  "min_block_bars": MIN_BLOCK_BARS, "degenerate": degenerate,
                  "degenerate_reason": (f"L = {L} >= n / 2 = {n / 2}: no interval and no control (C5 c)"
                                        if degenerate else None)},
        "control": {"shifts": shifts, "reason": None} if shifts is not None else {"shifts": None, "reason": ctrl},
        "overall": overall,
        "scenes": scene_info,
        "frequency": frequency,
        "breakdown": breakdown,
        "daily": daily,
        "gaps": {"n_waited": int(waited.sum()), "max_wait_ns": int(p.fill_wait_ns.max()),
                 "sum_wait_ns": int(p.fill_wait_ns.sum())},
    }


__all__ = ["ALPHA", "METHOD", "MIN_BLOCK_BARS", "NO_VERDICT", "N_RESAMPLES", "N_SHIFTS", "POWER", "block_length",
           "daily_correlation", "daily_rows", "measure", "measure_card", "median_nonzero_run", "nonzero_runs",
           "read_daily",
           "write_daily"]


def measure_card(card_md_path: str, run: CardRun, *, seed: int, control_seed: int,
                 regimes: Optional[Sequence[tuple[int, str]]], daily_path: str) -> dict:
    """`measure` with the settings fixed in the card's description before
    measuring (CARD.md 測定の設定: vr_q_bars, day_zone, the reference series'
    declarations and which are scenes; cardmd.py). The run must have been
    made with exactly those declarations, for exactly the series it holds."""
    with open(card_md_path, encoding="utf-8") as fh:
        card = cardmd.parse(fh.read())
    _body, why = cardmd.body(card, cardmd.SETTINGS)
    st, problems = cardmd.settings(card)
    if why or problems:
        raise CardError(f"{card_md_path}: the measurement settings cannot be read: "
                        f"{[why] if why else problems}")
    want = {name: parse_decl(name, d).as_dict() for name, d in st.declarations.items()}
    same = run.ref_decl == {name: want.get(name) for name in run.ref_decl}
    if not same or set(st.ref_scenes) - set(run.ref_decl):
        raise CardError(f"{card_md_path}: the run's reference series {run.ref_decl} are not the ones its settings "
                        f"declare {want} (scenes {st.ref_scenes})")
    out = measure(run, seed=seed, control_seed=control_seed, vr_q_bars=st.vr_q_bars, regimes=regimes,
                  day_zone=st.day_zone, ref_scenes=st.ref_scenes, daily_path=daily_path)
    out["settings"]["from_card"] = {"vr_q_bars": st.vr_q_bars, "day_zone": st.day_zone, "declarations": want,
                                    "ref_scenes": dict(sorted(st.ref_scenes.items()))}
    return out

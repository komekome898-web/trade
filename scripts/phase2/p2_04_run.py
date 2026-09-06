#!/usr/bin/env python
"""P2-04 iteration 0 — the 9 pre-registered unconditional calendar rules,
DEVELOPMENT SET ONLY.

Implements exactly `docs/PHASE2/P2-04/PREREG.md` (frozen 2026-09-06):
JPX calendar anomalies (month-turn / SQ / weekday / holiday-eve) on close ->
close daily holding pairs, micro-futures costs for the futures-based rules
and per-price-band ETF tick costs for the SQ rules, block-bootstrap
inference, three controls, two joint block-permutation nulls (A and B), the
per-rule MDE, the train/val split, the standard condition analysis
(PHASE2_TEMPLATES.md §6) and the standard edge-trend sub-indicator (§5).

Every input file is read through `bot.research.sealed.load_unsealed(path,
"P2-04")`, so the sealed evaluation window is structurally unreachable from
here. Nothing in this module interprets the numbers: it writes tables.

Usage:  PYTHONPATH=src python scripts/phase2/p2_04_run.py
        PYTHONPATH=src python scripts/phase2/p2_04_run.py --skip-edge-trend
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from bot.constants import require_source  # noqa: E402
from bot.research.overnight import (  # noqa: E402
    EDGE_TREND_SLOPE_MDE_Z,
    _block_slices,
    _moving_block_bootstrap_means,
    block_bootstrap_ci,
    edge_trend,
    sign_shuffle_null,
    state_split,
)
from bot.research.sealed import load_unsealed  # noqa: E402

UNIT = "P2-04"
SEED = 20260906

# ---- pre-registered constants (PREREG「コスト定数」「指標と分母」「対照」) ----
BLOCK = 20
N_BOOT = 2000            # block-bootstrap resamples per CI
N_RANDOM = 1000          # 対照1 stratified random same-size day sets
N_SHUFFLE = 1000         # 対照3 sign shuffle
N_PERM = 2000            # joint permutation nulls A and B
PLACEBO_SHIFTS = (-2, -1, 1, 2)
TRAIN_END = pd.Timestamp("2007-12-31")
Z_MDE = EDGE_TREND_SLOPE_MDE_Z            # 2.8016 = z_{0.975} + z_{0.8}

# edge trend (§5), pre-registered values for this unit
EDGE_WINDOW = 250
EDGE_BLOCK = 20
EDGE_TIME_UNIT = "year"
EDGE_TIME_AXIS = "calendar"
EDGE_PERIOD = "year"

FULL_FILE = "backtest_data/n225f_225labo_20260828/full_day_daily.csv.gz"
DAY_FILE = "backtest_data/n225f_225labo_20260828/day_session_daily.csv.gz"
ETF_1321 = "backtest_data/jpx_etf_daily_20260905/1321.T.csv"
ETF_1306 = "backtest_data/jpx_etf_daily_20260905/1306.T.csv"
OUT_DIR = REPO_ROOT / "backtest_data" / "phase2_runs" / "P2-04" / "iter0_20260906"

RULES = ["TOM", "WD-Mon", "WD-Tue", "WD-Wed", "WD-Thu", "WD-Fri", "PH", "SQm", "SQq"]
WEEKDAY_RULES = {"WD-Mon": 0, "WD-Tue": 1, "WD-Wed": 2, "WD-Thu": 3, "WD-Fri": 4}
FUTURES_RULES = ["TOM", "WD-Mon", "WD-Tue", "WD-Wed", "WD-Thu", "WD-Fri", "PH"]
SQ_RULES = ["SQm", "SQq"]


# ---------------------------------------------------------------------------
# calendar derivation (pure; exercised by tests/test_phase2_p2_04.py against a
# hand-made 2-year synthetic calendar with hand-listed answers)
# ---------------------------------------------------------------------------

def _is_year_end_new_year(d: date) -> bool:
    """PREREG「年末年始(12-31, 1-1..1-3)は祝日として扱う」."""
    return (d.month == 12 and d.day == 31) or (d.month == 1 and d.day <= 3)


def derive_holidays(trading_days) -> list[date]:
    """The mechanical holiday calendar of PREREG「祝日カレンダーの導出」.

    A calendar date inside the span of `trading_days` is a HOLIDAY when it is
    not itself a trading day AND (it is a weekday Mon-Fri, or it is one of the
    year-end/new-year dates 12-31 / 01-01..01-03). Weekends are otherwise not
    holidays ("週末は含めない"), so a Friday is never a holiday-eve merely
    because Saturday is not a trading day.
    """
    days = sorted({_as_date(d) for d in trading_days})
    if not days:
        return []
    tds = set(days)
    out: list[date] = []
    cur, last = days[0], days[-1]
    while cur <= last:
        if cur not in tds and (cur.weekday() < 5 or _is_year_end_new_year(cur)):
            out.append(cur)
        cur += timedelta(days=1)
    return out


def holiday_eves(trading_days, holidays=None) -> list[date]:
    """PH: the last trading day strictly before each derived holiday."""
    days = sorted({_as_date(d) for d in trading_days})
    hols = derive_holidays(days) if holidays is None else [_as_date(h) for h in holidays]
    eves: set[date] = set()
    for h in hols:
        i = bisect.bisect_left(days, h) - 1
        if i >= 0:
            eves.add(days[i])
    return sorted(eves)


def tom_days(trading_days) -> list[date]:
    """TOM: each month's LAST trading day plus each month's FIRST 3 trading days.

    Equivalent to PREREG「月末最終営業日と翌月最初の 3 営業日(計 4 日)」 for
    every month boundary inside the data; the first month of the series
    contributes only its first three days (its predecessor month-end is not in
    the data) and the last month only its last day plus its own first three.
    A month holding fewer than 3 trading days contributes all it has.
    """
    days = sorted({_as_date(d) for d in trading_days})
    by_month: dict[tuple[int, int], list[date]] = {}
    for d in days:
        by_month.setdefault((d.year, d.month), []).append(d)
    out: set[date] = set()
    for key in sorted(by_month):
        month_days = by_month[key]
        out.add(month_days[-1])
        out.update(month_days[:3])
    return sorted(out)


def second_friday(year: int, month: int) -> date:
    """The 2nd Friday of a calendar month (the mini/major SQ date)."""
    first = date(year, month, 1)
    return first + timedelta(days=(4 - first.weekday()) % 7 + 7)


def sq_days(trading_days, months=None) -> list[date]:
    """SQm / SQq day set, holiday-shifted.

    The 2nd Friday of every month (`months=None`) or of the given contract
    months (`months=(3, 6, 9, 12)` for the major SQ). PREREG「第 2 金曜が休日
    なら前営業日」: when the 2nd Friday is not a trading day, the immediately
    preceding trading day is used instead. A 2nd Friday outside the span of
    `trading_days` contributes nothing.
    """
    days = sorted({_as_date(d) for d in trading_days})
    if not days:
        return []
    tds = set(days)
    out: set[date] = set()
    for key in sorted({(d.year, d.month) for d in days}):
        year, month = key
        if months is not None and month not in months:
            continue
        sq = second_friday(year, month)
        if sq < days[0] or sq > days[-1]:
            continue
        if sq in tds:
            out.add(sq)
            continue
        i = bisect.bisect_left(days, sq) - 1
        if i >= 0:
            out.add(days[i])
    return sorted(out)


def weekday_days(trading_days, weekday: int) -> list[date]:
    """Every trading day falling on `weekday` (0 = Monday .. 4 = Friday)."""
    return sorted(d for d in {_as_date(x) for x in trading_days} if d.weekday() == weekday)


def major_sq_marked_days(trading_days) -> set[date]:
    """{major SQ day} ∪ {its immediately preceding trading day}.

    PREREG「メジャー SQ 日とその前営業日を端点に含むペアを除外」 — the day set
    whose touch (at EITHER endpoint of a close→close pair) removes the pair
    from the futures-based rules' primary set.
    """
    days = sorted({_as_date(d) for d in trading_days})
    pos = {d: i for i, d in enumerate(days)}
    marked: set[date] = set()
    for s in sq_days(days, months=(3, 6, 9, 12)):
        marked.add(s)
        i = pos[s]
        if i > 0:
            marked.add(days[i - 1])
    return marked


def shift_trading_days(day_set, trading_days, k: int) -> tuple[set[date], int, int]:
    """Placebo calendar shift by `k` TRADING days, with the fold-back rule.

    PREREG 対照 2: each date of the rule set is moved `k` trading days; any
    shifted date that lands back INSIDE the original rule set is removed from
    the placebo set and counted ("ずらした結果が元の規則の集合に戻る日付は
    プラセボ集合から除き、除いた件数を報告する").

    Returns (placebo set, n_folded_back_removed, n_shifted_off_the_calendar).
    """
    days = sorted({_as_date(d) for d in trading_days})
    pos = {d: i for i, d in enumerate(days)}
    original = {_as_date(d) for d in day_set}
    shifted: set[date] = set()
    n_out = 0
    for d in sorted(original):
        i = pos.get(d)
        if i is None:
            continue
        j = i + k
        if j < 0 or j >= len(days):
            n_out += 1
            continue
        shifted.add(days[j])
    fold_back = shifted & original
    return shifted - original, len(fold_back), n_out


def _as_date(x) -> date:
    if isinstance(x, date) and not isinstance(x, pd.Timestamp):
        return x
    return pd.Timestamp(x).date()


# ---------------------------------------------------------------------------
# pairs and costs
# ---------------------------------------------------------------------------

def build_close_pairs(df: pd.DataFrame) -> pd.DataFrame:
    """close(t−1) → close(t) holding pairs, one row per pair.

    `df` must hold "date"/"close", one row per trading day, sorted ascending,
    and must ALREADY be restricted to the rows eligible for the analysis — the
    PREREG endpoint rule (a pair belongs to the development set only when BOTH
    of its days are outside the seal) then falls out of taking consecutive
    rows of the unsealed frame.

    Columns: date_prev (t−1, the entry day), date (t, the exit day and the day
    the calendar rule is evaluated on), close_prev, close, r (simple return),
    r_bps, nights (calendar nights spanned).
    """
    df = df.reset_index(drop=True)
    out = pd.DataFrame({
        "date_prev": df["date"].iloc[:-1].to_numpy(),
        "date": df["date"].iloc[1:].to_numpy(),
        "close_prev": df["close"].iloc[:-1].to_numpy(dtype=float),
        "close": df["close"].iloc[1:].to_numpy(dtype=float),
    })
    out["r"] = out["close"] / out["close_prev"] - 1.0
    out["r_bps"] = out["r"] * 1e4
    out["nights"] = (pd.to_datetime(out["date"]) - pd.to_datetime(out["date_prev"])).dt.days
    return out


def etf_tick_yen(price: float, bands: dict) -> float:
    """JPX 呼値の単位 for a 1-unit ETF at `price`, from constants.yaml's
    `jpx_cash_equity.etf_tick_size_yen_by_price_band` (bands are inclusive
    upper bounds; the final `over_...` entry catches everything above)."""
    edges = []
    over = None
    for key, val in bands.items():
        if key.startswith("up_to_"):
            edges.append((float(key.split("_")[2]), float(val)))
        else:
            over = float(val)
    for edge, tick in sorted(edges):
        if price <= edge:
            return tick
    return float(over)


# ---------------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------------

def mean_ci(x, seed: int = SEED) -> tuple[float, float, float]:
    x = np.asarray(x, dtype=float)
    if not len(x):
        return float("nan"), float("nan"), float("nan")
    lo, hi = block_bootstrap_ci(x, block=BLOCK, n_boot=N_BOOT, seed=seed)
    return float(x.mean()), lo, hi


def t_ci(x) -> tuple[float, float]:
    """Supplementary Student-t interval of the mean, IID (no autocorrelation).

    Reported ONLY as a fallback for a rule whose n is below the pre-registered
    block length 20, where the block bootstrap is structurally undefined and
    `block_bootstrap_ci` returns (nan, nan) — SQq's development-set n = 16 is
    the pre-registered example. It is NOT the pre-registered statistic and is
    always labelled 参考 in the outputs.
    """
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 2:
        return float("nan"), float("nan")
    from statistics import NormalDist
    try:
        from scipy import stats  # type: ignore
        crit = float(stats.t.ppf(0.975, n - 1))
    except Exception:  # pragma: no cover - scipy optional
        crit = float(NormalDist().inv_cdf(0.975))
    se = float(x.std(ddof=1)) / np.sqrt(n)
    m = float(x.mean())
    return m - crit * se, m + crit * se


def diff_ci(a, b, seed: int = SEED) -> tuple[float, float, float]:
    """mean(a) − mean(b) and its 95% CI from two independent block-bootstrap
    draws (the same construction `state_split` uses for a state difference)."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if not len(a) or not len(b):
        return float("nan"), float("nan"), float("nan")
    da = _moving_block_bootstrap_means(a, BLOCK, N_BOOT, seed)
    db = _moving_block_bootstrap_means(b, BLOCK, N_BOOT, seed + 1)
    d = da - db
    if np.isnan(d).all():
        return float(a.mean() - b.mean()), float("nan"), float("nan")
    lo, hi = (float(v) for v in np.percentile(d, [2.5, 97.5]))
    return float(a.mean() - b.mean()), lo, hi


def mde_of(x) -> tuple[float, float, int]:
    """(σ, MDE = 2.8016·σ/√n, n) for a per-observation series in bps."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 2:
        return float("nan"), float("nan"), n
    sd = float(x.std(ddof=1))
    return sd, float(Z_MDE * sd / np.sqrt(n)), n


def primary_series_vol20(full_df: pd.DataFrame) -> pd.Series:
    """20-sample trailing realised vol of the PRIMARY series' close→close
    returns, AS OF ENTRY (close(t−1)): the value indexed by exit day t equals
    std(close→close returns over days t−20..t−1) — the 20 returns already
    realised by the time a pair enters at close(t−1), none of which include
    the pair's own exit-day return. Exactly iteration 0's `pairs["vol20"]`
    formula (condition analysis, §6), factored out so iteration ≥ 1 reuses
    the identical construction rather than re-deriving it.
    """
    cc = full_df["close"].pct_change()
    vol20 = cc.rolling(20).std().shift(1)
    return pd.Series(vol20.to_numpy(),
                     index=pd.to_datetime(full_df["date"]).to_numpy())


TERCILE_LABELS = ("1_低", "2_中", "3_高")


def tercile_cutpoints(values, train_mask) -> tuple[float, float]:
    """The 33rd/67th percentile cutpoints of `values`, using ONLY the rows
    where `train_mask` is True (iteration 1's "terciles fixed on the train
    split"). NaN values are dropped before the percentile is taken. Returns
    (nan, nan) if fewer than 3 finite train observations are available.
    """
    v = np.asarray(values, dtype=float)
    tm = np.asarray(train_mask, dtype=bool)
    train_vals = v[tm & np.isfinite(v)]
    if len(train_vals) < 3:
        return float("nan"), float("nan")
    q1, q2 = np.percentile(train_vals, [100.0 / 3.0, 200.0 / 3.0])
    return float(q1), float(q2)


def label_tercile(values, q1: float, q2: float) -> np.ndarray:
    """Bin `values` into TERCILE_LABELS using FIXED cutpoints (q1, q2) —
    never recomputed from `values` itself, so applying train-derived cutpoints
    to val data introduces no look-ahead. NaN values (and an undefined
    cutpoint pair) get the empty label ''.
    """
    v = np.asarray(values, dtype=float)
    out = np.full(v.shape, "", dtype=object)
    if not (np.isfinite(q1) and np.isfinite(q2)):
        return out
    fin = np.isfinite(v)
    out[fin & (v <= q1)] = TERCILE_LABELS[0]
    out[fin & (v > q1) & (v <= q2)] = TERCILE_LABELS[1]
    out[fin & (v > q2)] = TERCILE_LABELS[2]
    return out


def conditional_indicator(net_cons_arr, gross_arr, mask, seed: int = SEED) -> dict:
    """The same two PREREG main indicators, applied to an arbitrary boolean
    `mask` over an already-eval-filtered, already-split-filtered population:
    (1) the conservative-net mean of `mask`'s rows with its CI, (2) the gross
    mean of `mask`'s rows minus the gross mean of ~mask's rows (its complement
    within the SAME passed-in population) with its CI. Generalises iteration
    0's `indicator_rows` from "rule day vs non-rule day" to "(rule ∧ state)
    day vs everything else", with no other change to the construction.
    """
    mask = np.asarray(mask, dtype=bool)
    net_cons_arr = np.asarray(net_cons_arr, dtype=float)
    gross_arr = np.asarray(gross_arr, dtype=float)
    sub_net = net_cons_arr[mask]
    sub_gross = gross_arr[mask]
    non_gross = gross_arr[~mask]
    net_mean, net_lo, net_hi = mean_ci(sub_net, seed)
    d, dlo, dhi = diff_ci(sub_gross, non_gross, seed)
    sd, mde, n = mde_of(sub_net)
    return {"n": n, "n_complement": int((~mask).sum()),
            "net_mean_cons_bps": net_mean, "net_ci_lo": net_lo, "net_ci_hi": net_hi,
            "diff_gross_bps": d, "diff_ci_lo": dlo, "diff_ci_hi": dhi,
            "sd_bps": sd, "mde_bps": mde}


def years_span(dates) -> float:
    d = pd.to_datetime(pd.Series(list(dates)))
    if not len(d):
        return float("nan")
    return float((d.max() - d.min()).days) / 365.25


def sharpe_annualised(x, years: float) -> float:
    x = np.asarray(x, dtype=float)
    if len(x) < 2 or not np.isfinite(years) or years <= 0:
        return float("nan")
    sd = float(x.std(ddof=1))
    if sd == 0:
        return float("nan")
    return float(x.mean()) / sd * float(np.sqrt(len(x) / years))


def max_drawdown_yen(pnl_yen) -> float:
    pnl = np.asarray(pnl_yen, dtype=float)
    if not len(pnl):
        return float("nan")
    equity = np.cumsum(pnl)
    peak = np.maximum.accumulate(np.concatenate([[0.0], equity]))[1:]
    return float(np.max(peak - equity))


def joint_permutation_null(net_bps, gross_bps, masks, block: int = BLOCK,
                           n_draws: int = N_PERM, seed: int = SEED
                           ) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """The two joint block-permutation nulls A and B (PREREG「同時置換の帰無」).

    ONE draw = ONE permutation of the daily series' `block`-long blocks; from
    that single permuted world EVERY rule's statistic is recomputed, and the
    draw contributes the MAXIMUM over rules. Null A uses main indicator (1)
    (the conservative-net mean on the rule's days), null B uses main indicator
    (2) (the rule-day minus non-rule-day gross difference). Both statistics
    come from the same permutation, so the two nulls describe the same
    2,000 virtual worlds.

    `masks` maps a rule name to (rule_mask, eval_mask): boolean arrays over the
    full pair series. The rule's denominator is rule_mask (already intersected
    with eval_mask by the caller) and its complement is eval_mask & ~rule_mask.

    Returns (draws_A, draws_B, per-rule argmax-share table).
    """
    net = np.asarray(net_bps, dtype=float)
    gross = np.asarray(gross_bps, dtype=float)
    n = len(net)
    blocks = _block_slices(n, block)
    rng = np.random.default_rng(seed)
    names = list(masks.keys())
    rule_m = [np.asarray(masks[k][0], dtype=bool) for k in names]
    comp_m = [np.asarray(masks[k][1], dtype=bool) & ~np.asarray(masks[k][0], dtype=bool)
              for k in names]
    draws_a = np.empty(n_draws)
    draws_b = np.empty(n_draws)
    arg_a = np.zeros(len(names), dtype=int)
    arg_b = np.zeros(len(names), dtype=int)
    for b in range(n_draws):
        order = rng.permutation(len(blocks))
        perm = np.concatenate([blocks[i] for i in order])
        netp = net[perm]
        grossp = gross[perm]
        stat_a = np.array([netp[m].mean() if m.any() else -np.inf for m in rule_m])
        stat_b = np.array([
            (grossp[m].mean() - grossp[c].mean()) if (m.any() and c.any()) else -np.inf
            for m, c in zip(rule_m, comp_m)])
        ia = int(np.argmax(stat_a))
        ib = int(np.argmax(stat_b))
        draws_a[b] = stat_a[ia]
        draws_b[b] = stat_b[ib]
        arg_a[ia] += 1
        arg_b[ib] += 1
    table = pd.DataFrame({"rule": names,
                          "argmax_share_A": arg_a / n_draws,
                          "argmax_share_B": arg_b / n_draws})
    return draws_a, draws_b, table


def stratified_random_null(years, values, rule_mask, n_draws: int = N_RANDOM,
                           seed: int = SEED) -> np.ndarray:
    """対照1: same-size random day sets, stratified by calendar year.

    For each year, draw (without replacement) exactly as many days as the rule
    has in that year from that year's eligible days, and take the mean of the
    drawn values. Repeated `n_draws` times.
    """
    years = np.asarray(years)
    values = np.asarray(values, dtype=float)
    rule_mask = np.asarray(rule_mask, dtype=bool)
    rng = np.random.default_rng(seed)
    per_year = []
    for y in np.unique(years):
        idx = np.flatnonzero(years == y)
        k = int(rule_mask[idx].sum())
        if k:
            per_year.append((idx, k))
    if not per_year:
        return np.array([])
    out = np.empty(n_draws)
    for b in range(n_draws):
        picked = np.concatenate([rng.choice(idx, size=k, replace=False)
                                 for idx, k in per_year])
        out[b] = values[picked].mean()
    return out


# ---------------------------------------------------------------------------
# formatting helpers
# ---------------------------------------------------------------------------

def _md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_rev() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception as exc:  # pragma: no cover - diagnostics only
        return f"unavailable ({exc})"


def _fmt(v, nd: int = 3) -> str:
    if v is None:
        return "—"
    if isinstance(v, (bool, np.bool_)):
        return "true" if v else "false"
    if isinstance(v, (int, np.integer)):
        return f"{int(v):,}"
    if isinstance(v, float) and not np.isfinite(v):
        return "—"
    try:
        return f"{float(v):,.{nd}f}"
    except (TypeError, ValueError):
        return str(v)


def _table(rows, cols) -> str:
    head = "| " + " | ".join(c[1] for c in cols) + " |"
    sep = "|" + "|".join("---" for _ in cols) + "|"
    body = ["| " + " | ".join(
        (str(r.get(k, "")) if nd < 0 else _fmt(r.get(k), nd)) for k, _, nd in cols) + " |"
        for r in rows]
    return "\n".join([head, sep] + body)


def _json_safe(obj):
    """Recursively make a value JSON-valid: NaN/inf -> None, numpy -> python."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        v = float(obj)
        return v if np.isfinite(v) else None
    return obj


def _decade(ts) -> str:
    y = pd.Timestamp(ts).year
    return f"{(y // 10) * 10}s"


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

def build_rule_day_sets(trading_days) -> dict[str, list[date]]:
    """The 9 pre-registered unconditional rules' day sets on one calendar."""
    days = sorted({_as_date(d) for d in trading_days})
    sets = {"TOM": tom_days(days)}
    for name, wd in WEEKDAY_RULES.items():
        sets[name] = weekday_days(days, wd)
    sets["PH"] = holiday_eves(days)
    sets["SQm"] = sq_days(days, months=None)
    sets["SQq"] = sq_days(days, months=(3, 6, 9, 12))
    return sets


def main(out_dir: Path | None = None, skip_edge_trend: bool = False) -> int:
    out = out_dir if out_dir is not None else OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    steps: dict[str, int] = {}
    written: list[str] = []

    def write(df: pd.DataFrame, name: str):
        df.to_csv(out / name, index=False)
        written.append(name)

    # ---- constants with provenance (assumed values raise) ------------------
    c_fee = require_source("jpx_nikkei225_micro_futures.fee_yen_per_contract_per_side",
                           root=REPO_ROOT)
    c_tick = require_source("jpx_nikkei225_micro_futures.tick_size_yen", root=REPO_ROOT)
    c_mult = require_source("jpx_nikkei225_micro_futures.multiplier_yen_per_point",
                            root=REPO_ROOT)
    c_sor = require_source("jpx_cash_equity.sor_commission_yen", root=REPO_ROOT)
    c_bands = require_source("jpx_cash_equity.etf_tick_size_yen_by_price_band",
                             root=REPO_ROOT)
    fee, tick_pt, mult = int(c_fee.value), int(c_tick.value), int(c_mult.value)
    cost_yen_cons = 2 * fee + 2 * tick_pt * mult          # 122
    cost_yen_opt = 2 * fee                                # 22
    bands = dict(c_bands.value)
    etf_fee = float(c_sor.value)                          # 0

    # ---- load (dev set only; sealed rows removed by the loader) ------------
    full = load_unsealed(FULL_FILE, UNIT, root=REPO_ROOT)
    dayses = load_unsealed(DAY_FILE, UNIT, root=REPO_ROOT)
    etf1321 = load_unsealed(ETF_1321, UNIT, root=REPO_ROOT)
    etf1306 = load_unsealed(ETF_1306, UNIT, root=REPO_ROOT)
    for frame in (full, dayses, etf1321, etf1306):
        frame["date"] = pd.to_datetime(frame["date"])
        frame.sort_values("date", inplace=True)
        frame.reset_index(drop=True, inplace=True)
    steps["full_day_rows_unsealed"] = len(full)
    steps["day_session_rows_unsealed"] = len(dayses)
    steps["etf1321_rows_unsealed"] = len(etf1321)
    steps["etf1306_rows_unsealed"] = len(etf1306)

    trading_days = [d.date() for d in full["date"]]

    # ---- calendar derivation -----------------------------------------------
    holidays = derive_holidays(trading_days)
    rule_sets = build_rule_day_sets(trading_days)
    steps["holidays_derived"] = len(holidays)
    steps["holiday_eves"] = len(rule_sets["PH"])

    hol_df = pd.DataFrame({"holiday": [str(h) for h in holidays],
                           "weekday": [h.strftime("%a") for h in holidays],
                           "decade": [f"{(h.year // 10) * 10}s" for h in holidays],
                           "year_end_new_year": [_is_year_end_new_year(h) for h in holidays]})
    write(hol_df, "calendar_holidays.csv")
    span_years = (trading_days[-1] - trading_days[0]).days / 365.25
    hol_counts = (hol_df.groupby("decade").size().rename("n_holidays").reset_index())
    eve_dec = pd.Series([f"{(d.year // 10) * 10}s" for d in rule_sets["PH"]])
    hol_counts = hol_counts.merge(
        eve_dec.value_counts().rename("n_holiday_eves").rename_axis("decade").reset_index(),
        on="decade", how="outer").fillna(0)
    write(hol_counts, "calendar_holiday_counts_by_decade.csv")

    rule_day_rows = []
    for name, dset in rule_sets.items():
        for d in dset:
            rule_day_rows.append({"rule": name, "date": str(d)})
    write(pd.DataFrame(rule_day_rows), "calendar_rule_days.csv")
    for name in RULES:
        steps[f"rule_days_{name}"] = len(rule_sets[name])

    # ---- futures pairs ------------------------------------------------------
    pairs = build_close_pairs(full[["date", "close"]])
    steps["futures_pairs_after_endpoint_rule"] = len(pairs)
    day_close = pd.Series(dayses["close"].to_numpy(dtype=float),
                          index=dayses["date"].to_numpy())
    pairs["close_prev_day_session"] = pd.to_datetime(pairs["date_prev"]).map(day_close)
    notional = pairs["close_prev_day_session"] * mult
    pairs["cost_bps_cons"] = cost_yen_cons / notional * 1e4
    pairs["cost_bps_opt"] = cost_yen_opt / notional * 1e4
    pairs["r_net_bps_cons"] = pairs["r_bps"] - pairs["cost_bps_cons"]
    pairs["r_net_bps_opt"] = pairs["r_bps"] - pairs["cost_bps_opt"]
    pairs["pnl_yen_cons"] = (pairs["close"] - pairs["close_prev"]) * mult - cost_yen_cons
    # sensitivity: the same cost with the full-day close as the notional base
    pairs["cost_bps_cons_fullday_base"] = cost_yen_cons / (pairs["close_prev"] * mult) * 1e4
    steps["days_full_close_ne_day_session_close"] = int(
        (full["close"].to_numpy(dtype=float)
         != dayses["close"].to_numpy(dtype=float)).sum())

    d_t = np.array([d.date() for d in pd.to_datetime(pairs["date"])])
    d_prev = np.array([d.date() for d in pd.to_datetime(pairs["date_prev"])])
    marked = major_sq_marked_days(trading_days)
    sq_excluded = np.array([(a in marked) or (b in marked) for a, b in zip(d_prev, d_t)])
    pairs["sq_adjacent_excluded"] = sq_excluded
    steps["futures_pairs_sq_adjacent"] = int(sq_excluded.sum())
    steps["futures_pairs_after_sq_exclusion"] = int((~sq_excluded).sum())

    for name in RULES:
        pairs[f"is_{name}"] = np.isin(d_t, np.array(sorted(rule_sets[name]), dtype=object))
    pairs["split"] = np.where(pd.to_datetime(pairs["date"]) <= TRAIN_END, "train", "val")
    pairs["decade"] = [_decade(x) for x in pairs["date"]]
    pairs["year"] = pd.to_datetime(pairs["date"]).dt.year

    # state variables (observable at entry, i.e. at close(t−1))
    cc = full["close"].pct_change()
    vol20 = cc.rolling(20).std().shift(1)          # known at close(t−1) for pair ending t
    vol_by_date = pd.Series(vol20.to_numpy(), index=full["date"].to_numpy())
    pairs["vol20"] = pd.to_datetime(pairs["date"]).map(vol_by_date)
    fin = pairs["vol20"].notna()
    terc = pd.Series("", index=pairs.index, dtype=object)
    if fin.any():
        terc.loc[fin] = pd.qcut(pairs.loc[fin, "vol20"], 3,
                                labels=["1_低", "2_中", "3_高"]).astype(str)
    pairs["state_vol"] = terc
    prev_r = pairs["r_bps"].shift(1)               # return of the pair ending at t−1
    pairs["state_prev_sign"] = np.where(prev_r.isna(), "",
                                        np.where(prev_r > 0, "2_正", "1_非正"))
    pairs["state_regime"] = pairs["decade"]
    pairs["state_nights"] = np.where(pairs["nights"] <= 1, "1_1泊",
                                     np.where(pairs["nights"] <= 3, "2_2〜3泊", "3_4泊以上"))

    # ---- ETF pairs ----------------------------------------------------------
    def etf_pairs(df: pd.DataFrame, with_cost: bool) -> pd.DataFrame:
        p = build_close_pairs(df[["date", "close"]])
        if with_cost:
            ticks = p["close_prev"].map(lambda x: etf_tick_yen(float(x), bands))
            p["tick_yen"] = ticks
            p["cost_bps_cons"] = (2 * etf_fee + 2 * ticks) / p["close_prev"] * 1e4
            p["cost_bps_opt"] = (2 * etf_fee) / p["close_prev"] * 1e4
        else:
            p["tick_yen"] = np.nan
            p["cost_bps_cons"] = np.nan
            p["cost_bps_opt"] = np.nan
        p["r_net_bps_cons"] = p["r_bps"] - p["cost_bps_cons"]
        p["r_net_bps_opt"] = p["r_bps"] - p["cost_bps_opt"]
        # 1 ETF unit held close(t−1) -> close(t), conservative cost deducted
        p["pnl_yen_cons"] = (p["close"] - p["close_prev"]
                             - (2 * etf_fee + 2 * p["tick_yen"]))
        # PREREG 既知欠陥: 1306.T is printed at 1/10 of its price from
        # 2015-01-05 ("比は正しい"), so ratios INSIDE the window are fine but the
        # single splice pair straddling the boundary is a pure print artifact
        # (-90.06%). Marked here, excluded from the cross-check, count reported.
        p["price_scale_splice"] = p["r"].abs() > 0.5
        e_days = [d.date() for d in df["date"]]
        e_sets = build_rule_day_sets(e_days)
        et = np.array([d.date() for d in pd.to_datetime(p["date"])])
        for name in RULES:
            p[f"is_{name}"] = np.isin(et, np.array(sorted(e_sets[name]), dtype=object))
        p["split"] = np.where(pd.to_datetime(p["date"]) <= TRAIN_END, "train", "val")
        p["decade"] = [_decade(x) for x in p["date"]]
        p["year"] = pd.to_datetime(p["date"]).dt.year
        return p

    p1321 = etf_pairs(etf1321, with_cost=True)
    p1306 = etf_pairs(etf1306, with_cost=False)   # 1/10 price defect -> gross only
    steps["etf1321_pairs"] = len(p1321)
    steps["etf1306_pairs"] = len(p1306)
    steps["etf1306_price_scale_splice_pairs"] = int(p1306["price_scale_splice"].sum())
    steps["etf1321_price_scale_splice_pairs"] = int(p1321["price_scale_splice"].sum())
    steps["etf1321_SQm_days"] = int(p1321["is_SQm"].sum())
    steps["etf1321_SQq_days"] = int(p1321["is_SQq"].sum())

    # ---- main indicators ----------------------------------------------------
    def indicator_rows(frame: pd.DataFrame, eval_mask: np.ndarray, rule: str,
                       series_label: str, variant: str, seed: int) -> dict:
        ev = frame.loc[eval_mask]
        m = ev[f"is_{rule}"].to_numpy(dtype=bool)
        rule_net = ev.loc[m, "r_net_bps_cons"].to_numpy(dtype=float)
        rule_gross = ev.loc[m, "r_bps"].to_numpy(dtype=float)
        non_gross = ev.loc[~m, "r_bps"].to_numpy(dtype=float)
        net_mean, net_lo, net_hi = mean_ci(rule_net, seed)
        d, d_lo, d_hi = diff_ci(rule_gross, non_gross, seed)
        sd, mde, n = mde_of(rule_net)
        opt = ev.loc[m, "r_net_bps_opt"].to_numpy(dtype=float)
        t_lo, t_hi = t_ci(rule_net)
        return {
            "rule": rule, "series": series_label, "variant": variant,
            "n": n, "n_non_rule": int((~m).sum()),
            "net_mean_cons_bps": net_mean, "net_ci_lo": net_lo, "net_ci_hi": net_hi,
            "net_ci_lo_t_supp": t_lo, "net_ci_hi_t_supp": t_hi,
            "gross_mean_bps": float(rule_gross.mean()) if len(rule_gross) else float("nan"),
            "non_rule_gross_mean_bps": float(non_gross.mean()) if len(non_gross) else float("nan"),
            "diff_gross_bps": d, "diff_ci_lo": d_lo, "diff_ci_hi": d_hi,
            "net_mean_opt_bps": float(opt.mean()) if len(opt) else float("nan"),
            "cost_mean_bps": float(ev.loc[m, "cost_bps_cons"].mean()) if n else float("nan"),
            "sd_bps": sd, "mde_bps": mde,
        }

    all_mask = np.ones(len(pairs), dtype=bool)
    keep_mask = ~sq_excluded
    main_rows = []
    for i, rule in enumerate(RULES):
        s = SEED + 10 * i
        if rule in FUTURES_RULES:
            main_rows.append(indicator_rows(pairs, keep_mask, rule, "先物(主系列)",
                                            "主指標(メジャーSQ隣接ペア除外)", s))
            main_rows.append(indicator_rows(pairs, all_mask, rule, "先物(主系列)",
                                            "併記(除外なし)", s + 1))
        else:
            main_rows.append(indicator_rows(p1321, np.ones(len(p1321), dtype=bool), rule,
                                            "1321.T", "主指標(現物ETF・価格帯呼値)", s))
            main_rows.append(indicator_rows(pairs, all_mask, rule, "先物(主系列)",
                                            "併記(除外なし)", s + 1))
            main_rows.append(indicator_rows(pairs, keep_mask, rule, "先物(主系列)",
                                            "参考(メジャーSQ隣接ペア除外後)", s + 2))
    main_df = pd.DataFrame(main_rows)
    write(main_df, "main_indicators.csv")
    primary = {r["rule"]: r for r in main_rows
               if r["variant"].startswith("主指標")}

    # ---- MDE table (before / after exclusion) -------------------------------
    mde_rows = []
    for rule in RULES:
        if rule in FUTURES_RULES:
            variants = [("除外前(全ペア)", pairs, all_mask, "先物"),
                        ("除外後(メジャーSQ隣接ペア除外)", pairs, keep_mask, "先物")]
        else:
            variants = [("除外前(全ペア)", pairs, all_mask, "先物"),
                        ("除外後(メジャーSQ隣接ペア除外)", pairs, keep_mask, "先物"),
                        ("1321.T(主評価、除外なし)", p1321,
                         np.ones(len(p1321), dtype=bool), "1321.T")]
        for label, frame, emask, series in variants:
            ev = frame.loc[emask]
            m = ev[f"is_{rule}"].to_numpy(dtype=bool)
            net = ev.loc[m, "r_net_bps_cons"].to_numpy(dtype=float)
            gross = ev.loc[m, "r_bps"].to_numpy(dtype=float)
            non = ev.loc[~m, "r_bps"].to_numpy(dtype=float)
            sd, mde, n = mde_of(net)
            sdg, _, _ = mde_of(gross)
            sdn, _, nn = mde_of(non)
            se_diff = (np.sqrt(sdg ** 2 / max(n, 1) + sdn ** 2 / max(nn, 1))
                       if np.isfinite(sdg) and np.isfinite(sdn) else float("nan"))
            mde_rows.append({"rule": rule, "series": series, "variant": label, "n": n,
                             "sd_net_bps": sd, "mde_net_bps": mde,
                             "sd_gross_bps": sdg, "n_non_rule": nn,
                             "mde_diff_bps": Z_MDE * se_diff})
    mde_df = pd.DataFrame(mde_rows)
    write(mde_df, "mde.csv")

    # ---- sub indicators -----------------------------------------------------
    sub_rows = []
    for rule in RULES:
        frame, emask, series = ((p1321, np.ones(len(p1321), dtype=bool), "1321.T")
                                if rule in SQ_RULES else (pairs, keep_mask, "先物"))
        ev = frame.loc[emask]
        m = ev[f"is_{rule}"].to_numpy(dtype=bool)
        sub = ev.loc[m]
        net = sub["r_net_bps_cons"].to_numpy(dtype=float)
        yrs = years_span(sub["date"])
        pnl = (sub["pnl_yen_cons"].to_numpy(dtype=float)
               if "pnl_yen_cons" in sub.columns else np.array([]))
        row = {"rule": rule, "series": series, "n": int(len(sub)),
               "days_per_year": len(sub) / yrs if yrs else float("nan"),
               "sharpe_annualised": sharpe_annualised(net, yrs),
               "hit_rate": float((net > 0).mean()) if len(net) else float("nan"),
               "max_drawdown_yen_1unit": max_drawdown_yen(pnl) if len(pnl) else float("nan")}
        for dec in ("1990s", "2000s", "2010s"):
            seg = sub.loc[sub["decade"] == dec, "r_net_bps_cons"].to_numpy(dtype=float)
            row[f"net_mean_{dec}"] = float(seg.mean()) if len(seg) else float("nan")
            row[f"n_{dec}"] = int(len(seg))
        for lbl, pf in (("1321", p1321), ("1306", p1306)):
            mm = (pf[f"is_{rule}"].to_numpy(dtype=bool)
                  & ~pf["price_scale_splice"].to_numpy(dtype=bool))
            row[f"gross_mean_{lbl}_bps"] = (float(pf.loc[mm, "r_bps"].mean())
                                            if mm.any() else float("nan"))
            row[f"n_{lbl}"] = int(mm.sum())
            row[f"n_{lbl}_splice_excluded"] = int(
                (pf[f"is_{rule}"].to_numpy(dtype=bool)
                 & pf["price_scale_splice"].to_numpy(dtype=bool)).sum())
        sub_rows.append(row)
    sub_df = pd.DataFrame(sub_rows)
    write(sub_df, "sub_indicators.csv")

    # ---- train / val --------------------------------------------------------
    tv_rows = []
    for rule in RULES:
        frame, emask, series = ((p1321, np.ones(len(p1321), dtype=bool), "1321.T")
                                if rule in SQ_RULES else (pairs, keep_mask, "先物"))
        ev = frame.loc[emask]
        for split in ("train", "val"):
            sset = ev.loc[(ev["split"] == split)]
            m = sset[f"is_{rule}"].to_numpy(dtype=bool)
            net = sset.loc[m, "r_net_bps_cons"].to_numpy(dtype=float)
            mean, lo, hi = mean_ci(net)
            sd, mde, n = mde_of(net)
            d, dlo, dhi = diff_ci(sset.loc[m, "r_bps"].to_numpy(dtype=float),
                                  sset.loc[~m, "r_bps"].to_numpy(dtype=float))
            tv_rows.append({"rule": rule, "series": series, "split": split, "n": n,
                            "net_mean_cons_bps": mean, "ci_lo": lo, "ci_hi": hi,
                            "mde_bps": mde, "diff_gross_bps": d,
                            "diff_ci_lo": dlo, "diff_ci_hi": dhi})
    tv_df = pd.DataFrame(tv_rows)
    write(tv_df, "train_val.csv")

    # ---- controls -----------------------------------------------------------
    rnd_rows, placebo_rows, shuffle_rows = [], [], []
    rnd_draws_store = {}
    for i, rule in enumerate(RULES):
        frame, emask, series, cal = ((p1321, np.ones(len(p1321), dtype=bool), "1321.T",
                                      [d.date() for d in etf1321["date"]])
                                     if rule in SQ_RULES
                                     else (pairs, keep_mask, "先物", trading_days))
        ev = frame.loc[emask].reset_index(drop=True)
        m = ev[f"is_{rule}"].to_numpy(dtype=bool)
        net = ev.loc[m, "r_net_bps_cons"].to_numpy(dtype=float)
        obs = float(net.mean()) if len(net) else float("nan")

        # 1. stratified random same-size day sets
        draws = stratified_random_null(ev["year"].to_numpy(),
                                       ev["r_net_bps_cons"].to_numpy(dtype=float),
                                       m, N_RANDOM, SEED + 100 + i)
        rnd_draws_store[rule] = draws
        rnd_rows.append({"rule": rule, "series": series, "n": int(m.sum()),
                         "observed_net_mean_bps": obs,
                         "null_mean_bps": float(draws.mean()) if len(draws) else float("nan"),
                         "null_p50_bps": float(np.percentile(draws, 50)) if len(draws) else float("nan"),
                         "null_p95_bps": float(np.percentile(draws, 95)) if len(draws) else float("nan"),
                         "share_ge_observed": float((draws >= obs).mean()) if len(draws) else float("nan"),
                         "n_draws": int(len(draws))})

        # 2. calendar-shift placebo with fold-back removal
        ev_dates = np.array([d.date() for d in pd.to_datetime(ev["date"])])
        for k in PLACEBO_SHIFTS:
            pset, n_fold, n_out = shift_trading_days(rule_sets[rule] if rule not in SQ_RULES
                                                     else build_rule_day_sets(cal)[rule],
                                                     cal, k)
            pm = np.isin(ev_dates, np.array(sorted(pset), dtype=object))
            pnet = ev.loc[pm, "r_net_bps_cons"].to_numpy(dtype=float)
            mean, lo, hi = mean_ci(pnet, SEED + 200 + i)
            placebo_rows.append({"rule": rule, "series": series, "k_trading_days": k,
                                 "n": int(pm.sum()), "n_folded_back_removed": n_fold,
                                 "n_shifted_off_calendar": n_out,
                                 "net_mean_cons_bps": mean, "ci_lo": lo, "ci_hi": hi,
                                 "observed_rule_net_mean_bps": obs})

        # 3. sign shuffle
        sh = sign_shuffle_null(net, N_SHUFFLE, SEED + 300 + i)
        shuffle_rows.append({"rule": rule, "series": series, "n": int(len(net)),
                             "observed_net_mean_bps": obs,
                             "null_p95_bps": float(np.percentile(sh, 95)) if len(sh) else float("nan"),
                             "share_ge_observed": float((sh >= obs).mean()) if len(sh) else float("nan"),
                             "n_draws": N_SHUFFLE})
    write(pd.DataFrame(rnd_rows), "control1_stratified_random.csv")
    write(pd.DataFrame(placebo_rows), "control2_placebo_shift.csv")
    write(pd.DataFrame(shuffle_rows), "control3_sign_shuffle.csv")
    write(pd.DataFrame({"draw": np.arange(N_RANDOM),
                        **{f"null_mean_{r}": rnd_draws_store[r] for r in RULES
                           if len(rnd_draws_store[r]) == N_RANDOM}}),
          "control1_draws.csv")

    # ---- joint permutation nulls A and B ------------------------------------
    fut_masks = {}
    for rule in RULES:
        rm = pairs[f"is_{rule}"].to_numpy(dtype=bool)
        em = keep_mask if rule in FUTURES_RULES else all_mask
        fut_masks[rule] = (rm & em, em)
    draws_a, draws_b, arg_fut = joint_permutation_null(
        pairs["r_net_bps_cons"].to_numpy(dtype=float),
        pairs["r_bps"].to_numpy(dtype=float), fut_masks, BLOCK, N_PERM, SEED)

    etf_masks = {rule: (p1321[f"is_{rule}"].to_numpy(dtype=bool),
                        np.ones(len(p1321), dtype=bool)) for rule in RULES}
    draws_a_etf, draws_b_etf, arg_etf = joint_permutation_null(
        p1321["r_net_bps_cons"].to_numpy(dtype=float),
        p1321["r_bps"].to_numpy(dtype=float), etf_masks, BLOCK, N_PERM, SEED + 1)

    bar_a_fut = float(np.percentile(draws_a, 95))
    bar_b_fut = float(np.percentile(draws_b, 95))
    bar_a_etf = float(np.percentile(draws_a_etf, 95))
    bar_b_etf = float(np.percentile(draws_b_etf, 95))
    write(pd.DataFrame({"draw": np.arange(N_PERM),
                        "null_A_futures": draws_a, "null_B_futures": draws_b,
                        "null_A_1321": draws_a_etf, "null_B_1321": draws_b_etf}),
          "joint_permutation_draws.csv")
    null_summary = pd.DataFrame([
        {"world": "先物(主系列、9規則の最大)", "null": "A(主指標1: 保守ネット平均)",
         "p50": float(np.percentile(draws_a, 50)), "p95": bar_a_fut,
         "p99": float(np.percentile(draws_a, 99)), "n_draws": N_PERM},
        {"world": "先物(主系列、9規則の最大)", "null": "B(主指標2: 規則日−非規則日のグロス差)",
         "p50": float(np.percentile(draws_b, 50)), "p95": bar_b_fut,
         "p99": float(np.percentile(draws_b, 99)), "n_draws": N_PERM},
        {"world": "1321.T(9規則の最大)", "null": "A(主指標1: 保守ネット平均)",
         "p50": float(np.percentile(draws_a_etf, 50)), "p95": bar_a_etf,
         "p99": float(np.percentile(draws_a_etf, 99)), "n_draws": N_PERM},
        {"world": "1321.T(9規則の最大)", "null": "B(主指標2: 規則日−非規則日のグロス差)",
         "p50": float(np.percentile(draws_b_etf, 50)), "p95": bar_b_etf,
         "p99": float(np.percentile(draws_b_etf, 99)), "n_draws": N_PERM},
    ])
    write(null_summary, "joint_permutation_null.csv")
    write(arg_fut.merge(arg_etf, on="rule", suffixes=("_futures", "_1321")),
          "joint_permutation_argmax.csv")

    # ---- gate comparison table ---------------------------------------------
    gate_rows = []
    for rule in RULES:
        p = primary[rule]
        etf = rule in SQ_RULES
        ba, bb = (bar_a_etf, bar_b_etf) if etf else (bar_a_fut, bar_b_fut)
        gate_rows.append({
            "rule": rule, "series": p["series"], "n": p["n"],
            "net_mean_cons_bps": p["net_mean_cons_bps"],
            "ci_lo": p["net_ci_lo"], "ci_hi": p["net_ci_hi"],
            "ci_lo_t_supp": p["net_ci_lo_t_supp"], "ci_hi_t_supp": p["net_ci_hi_t_supp"],
            "mde_bps": p["mde_bps"],
            "net_minus_mde": p["net_mean_cons_bps"] - p["mde_bps"],
            "null_A_p95": ba, "net_minus_nullA": p["net_mean_cons_bps"] - ba,
            "diff_gross_bps": p["diff_gross_bps"],
            "diff_ci_lo": p["diff_ci_lo"], "diff_ci_hi": p["diff_ci_hi"],
            "null_B_p95": bb, "diff_minus_nullB": p["diff_gross_bps"] - bb,
            "ci_excludes_zero_positive": bool(np.isfinite(p["net_ci_lo"]) and p["net_ci_lo"] > 0),
            "diff_ci_excludes_zero_positive": bool(
                np.isfinite(p["diff_ci_lo"]) and p["diff_ci_lo"] > 0),
        })
    gate_df = pd.DataFrame(gate_rows)
    write(gate_df, "gate_comparison.csv")

    # ---- condition analysis (§6) --------------------------------------------
    state_tables, diff_tables, summaries = [], [], []
    for i, rule in enumerate(RULES):
        frame, emask = ((p1321, np.ones(len(p1321), dtype=bool)) if rule in SQ_RULES
                        else (pairs, keep_mask))
        ev = frame.loc[emask].reset_index(drop=True)
        m = ev[f"is_{rule}"].to_numpy(dtype=bool)
        sub = ev.loc[m].reset_index(drop=True)
        if len(sub) < 4:
            continue
        if rule in SQ_RULES:
            # the ETF frame carries no pre-computed state columns; build them here
            cc_e = etf1321["close"].pct_change()
            v20 = cc_e.rolling(20).std().shift(1)
            vmap = pd.Series(v20.to_numpy(), index=etf1321["date"].to_numpy())
            vol = pd.to_datetime(sub["date"]).map(vmap)
            f_ok = vol.notna()
            tt = pd.Series("", index=sub.index, dtype=object)
            if f_ok.any() and f_ok.sum() >= 3:
                tt.loc[f_ok] = pd.qcut(vol[f_ok], 3,
                                       labels=["1_低", "2_中", "3_高"]).astype(str)
            prev_map = pd.Series(ev["r_bps"].shift(1).to_numpy(),
                                 index=pd.to_datetime(ev["date"]).to_numpy())
            pr = pd.to_datetime(sub["date"]).map(prev_map)
            states = {
                "実現ボラ20日三分位": tt.to_numpy(),
                "直前日リターンの符号": np.where(pr.isna(), "",
                                          np.where(pr > 0, "2_正", "1_非正")),
                "制度区分(年代)": sub["decade"].to_numpy(),
                "泊数": np.where(sub["nights"] <= 1, "1_1泊",
                                 np.where(sub["nights"] <= 3, "2_2〜3泊", "3_4泊以上")),
            }
        else:
            states = {
                "実現ボラ20日三分位": sub["state_vol"].to_numpy(),
                "直前日リターンの符号": sub["state_prev_sign"].to_numpy(),
                "制度区分(年代)": sub["state_regime"].to_numpy(),
                "泊数": sub["state_nights"].to_numpy(),
            }
        res = state_split(sub["r_bps"].to_numpy(dtype=float), states,
                          block=BLOCK, n_boot=N_BOOT, seed=SEED + 400 + i,
                          cost_bps=sub["cost_bps_cons"].to_numpy(dtype=float))
        st = res["state_table"].copy()
        st.insert(0, "rule", rule)
        st["mde_bps"] = [Z_MDE * (r["ci_hi"] - r["ci_lo"]) / (2 * 1.959963985)
                         if np.isfinite(r["ci_hi"]) and np.isfinite(r["ci_lo"]) else np.nan
                         for _, r in st.iterrows()]
        state_tables.append(st)
        dt_ = res["diff_table"].copy()
        dt_.insert(0, "rule", rule)
        diff_tables.append(dt_)

        works, fails, undec = [], [], []
        for _, r in st.iterrows():
            tag = f"{r['variable']}={r['state']}(n={int(r['n'])})"
            lo, hi = r.get("net_ci_lo", np.nan), r.get("net_ci_hi", np.nan)
            if np.isfinite(lo) and lo > 0:
                works.append(tag)
            elif np.isfinite(hi) and hi < 0:
                fails.append(tag)
            else:
                undec.append(tag)
        summaries.append({"rule": rule,
                          "効く状況(費用後CIが全て正)": " / ".join(works) or "該当なし",
                          "効かない状況(費用後CIが全て負)": " / ".join(fails) or "該当なし",
                          "判定不能な状況(費用後CIがゼロを含む)": " / ".join(undec) or "該当なし",
                          "同時置換帰無95点(最大差, bps)": res["null_p95"],
                          "候補となった差の数": int((dt_["verdict"] == "候補").sum())})
    state_all = pd.concat(state_tables, ignore_index=True) if state_tables else pd.DataFrame()
    diff_all = pd.concat(diff_tables, ignore_index=True) if diff_tables else pd.DataFrame()
    write(state_all, "condition_state_table.csv")
    write(diff_all, "condition_diff_table.csv")
    summary_df = pd.DataFrame(summaries)
    write(summary_df, "condition_summary_3lines.csv")

    # ---- edge trend (§5) -----------------------------------------------------
    edge_results = {}
    if not skip_edge_trend:
        ev = pairs.loc[keep_mask].reset_index(drop=True)
        tom = ev.loc[ev["is_TOM"].to_numpy(dtype=bool)].reset_index(drop=True)
        for label, frame in (("TOM", tom), ("全日", ev)):
            for leg, col in (("グロス", "r_bps"), ("費用", "cost_bps_cons"),
                             ("ネット(保守)", "r_net_bps_cons")):
                res = edge_trend(frame["date"], frame[col].to_numpy(dtype=float),
                                 window=EDGE_WINDOW, block=EDGE_BLOCK,
                                 time_unit=EDGE_TIME_UNIT, time_axis=EDGE_TIME_AXIS,
                                 period=EDGE_PERIOD, n_boot=N_BOOT, seed=SEED)
                key = f"{label}_{leg}"
                edge_results[key] = res
                tag = {"TOM": "tom", "全日": "alldays"}[label]
                legtag = {"グロス": "gross", "費用": "cost", "ネット(保守)": "net"}[leg]
                write(res["rolling"], f"edge_trend_{tag}_{legtag}_rolling.csv")
                write(res["period_table"], f"edge_trend_{tag}_{legtag}_by_year.csv")
        edge_summary = pd.DataFrame([{
            "series": k, "n": v["params"]["n"], "slope": v["slope"],
            "slope_unit": v["slope_unit"], "slope_ci_lo": v["slope_ci"][0],
            "slope_ci_hi": v["slope_ci"][1], "slope_mde": v["slope_mde"],
            "half_diff": v["half_split"]["diff"],
            "half_diff_ci_lo": v["half_split"]["diff_ci"][0],
            "half_diff_ci_hi": v["half_split"]["diff_ci"][1],
            "mean_first": v["half_split"]["mean_first"],
            "mean_second": v["half_split"]["mean_second"],
            "last_window_mean": (v["last_window"] or {}).get("mean", float("nan")),
            "last_window_ci_lo": (v["last_window"] or {}).get("ci_lo", float("nan")),
            "last_window_ci_hi": (v["last_window"] or {}).get("ci_hi", float("nan")),
            "judgment": v["judgment"],
        } for k, v in edge_results.items()])
        write(edge_summary, "edge_trend_summary.csv")
    else:
        edge_summary = pd.DataFrame()

    # ---- pairs / exclusions --------------------------------------------------
    def dated(df: pd.DataFrame) -> pd.DataFrame:
        d = df.copy()
        for c in ("date", "date_prev"):
            d[c] = pd.to_datetime(d[c]).dt.date
        return d

    write(dated(pairs), "pairs_futures.csv")
    write(dated(p1321), "pairs_1321.csv")
    write(dated(p1306), "pairs_1306.csv")

    excl = pd.DataFrame([
        {"step": "full_day_daily 未封印行(開発セット)", "n": steps["full_day_rows_unsealed"]},
        {"step": "day_session_daily 未封印行(費用の元本)", "n": steps["day_session_rows_unsealed"]},
        {"step": "端点規則適用後の close→close ペア(先物)",
         "n": steps["futures_pairs_after_endpoint_rule"]},
        {"step": "うちメジャーSQ隣接(SQ日またはその前営業日を端点に含む)",
         "n": steps["futures_pairs_sq_adjacent"]},
        {"step": "メジャーSQ隣接除外後(TOM/WD/PH の主指標の分母)",
         "n": steps["futures_pairs_after_sq_exclusion"]},
        {"step": "導出した祝日(暦日)", "n": steps["holidays_derived"]},
        {"step": "祝日前(PH)日数", "n": steps["holiday_eves"]},
        {"step": "1321.T 未封印行 / ペア", "n": steps["etf1321_pairs"]},
        {"step": "1306.T 未封印行 / ペア", "n": steps["etf1306_pairs"]},
    ] + [{"step": f"規則日数 {r}(先物カレンダー)", "n": steps[f"rule_days_{r}"]} for r in RULES])
    write(excl, "exclusions.csv")

    # ---- RESULTS.md ----------------------------------------------------------
    md = _results_md(steps, excl, hol_counts, span_years, main_df, primary, mde_df,
                     sub_df, tv_df, rnd_rows, placebo_rows, shuffle_rows, null_summary,
                     gate_df, state_all, diff_all, summary_df, edge_summary,
                     pairs, p1321, cost_yen_cons, cost_yen_opt, bands,
                     bar_a_fut, bar_b_fut, bar_a_etf, bar_b_etf, skip_edge_trend)
    (out / "RESULTS.md").write_text(md, encoding="utf-8")
    written.append("RESULTS.md")

    # ---- RUN.json ------------------------------------------------------------
    run = {
        "unit": UNIT, "iteration": 0, "run_date": str(date(2026, 9, 6)), "seed": SEED,
        "git_rev": _git_rev(),
        "script": "scripts/phase2/p2_04_run.py",
        "script_md5": _md5(Path(__file__)),
        "inputs": [{"path": p, "md5": _md5(REPO_ROOT / p)}
                   for p in (FULL_FILE, DAY_FILE, ETF_1321, ETF_1306)],
        "seal_record_md5": _md5(REPO_ROOT / "backtest_data" / "phase2_sealed" / UNIT
                                / "SEALED.json"),
        "parameters": {
            "block": BLOCK, "n_boot": N_BOOT, "n_random": N_RANDOM,
            "n_shuffle": N_SHUFFLE, "n_permutation": N_PERM,
            "placebo_shifts_trading_days": list(PLACEBO_SHIFTS),
            "train_end": str(TRAIN_END.date()),
            "cost_yen_conservative_micro": cost_yen_cons,
            "cost_yen_optimistic_micro": cost_yen_opt,
            "micro_fee_yen_per_side": fee, "micro_tick_points": tick_pt,
            "micro_multiplier_yen_per_point": mult,
            "etf_commission_yen": etf_fee,
            "z_mde": Z_MDE,
            "edge_trend": {"window": EDGE_WINDOW, "block": EDGE_BLOCK,
                           "time_unit": EDGE_TIME_UNIT, "time_axis": EDGE_TIME_AXIS,
                           "period": EDGE_PERIOD},
        },
        "n_at_each_step": steps,
        "headline": {
            "null_A_p95_futures": bar_a_fut, "null_B_p95_futures": bar_b_fut,
            "null_A_p95_1321": bar_a_etf, "null_B_p95_1321": bar_b_etf,
            "per_rule": [{"rule": r["rule"], "series": r["series"], "n": r["n"],
                          "net_mean_cons_bps": r["net_mean_cons_bps"],
                          "ci95": [r["net_ci_lo"], r["net_ci_hi"]],
                          "diff_gross_bps": r["diff_gross_bps"],
                          "diff_ci95": [r["diff_ci_lo"], r["diff_ci_hi"]],
                          "mde_bps": r["mde_bps"]}
                         for r in (primary[k] for k in RULES)],
        },
        "outputs": sorted(written),
    }
    (out / "RUN.json").write_text(
        json.dumps(_json_safe(run), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(json.dumps(_json_safe(run["headline"]), ensure_ascii=False, indent=2))
    print(f"wrote {len(written) + 1} files to {out}")
    return 0


def _results_md(steps, excl, hol_counts, span_years, main_df, primary, mde_df, sub_df,
                tv_df, rnd_rows, placebo_rows, shuffle_rows, null_summary, gate_df,
                state_all, diff_all, summary_df, edge_summary, pairs, p1321,
                cost_yen_cons, cost_yen_opt, bands, bar_a_fut, bar_b_fut,
                bar_a_etf, bar_b_etf, skip_edge_trend) -> str:
    md: list[str] = []
    A = md.append
    A("# P2-04 反復 0 — 事前登録の 9 暦規則(無条件)、開発セットのみ")
    A("")
    A(f"実行日 2026-09-06 / seed {SEED} / git {_git_rev()[:12]} / 単位 {UNIT}。"
      "入力は全て `bot.research.sealed.load_unsealed(path, \"P2-04\")` 経由で読み込み、"
      "封印期間(先物 2015-08-29 以降、ETF 2015-08-29 以降、およびフォワード)には一切触れていない。")
    A("")
    A("**本書は数値の報告のみで、採用・棄却の解釈は行わない。**")
    A("")
    A("## 0. 事前登録値(この実行で固定した設計)")
    A("")
    A(_table([
        {"a": "ブロック・ブートストラップ", "b": f"ブロック長 {BLOCK} / リサンプル {N_BOOT:,} / seed {SEED}"},
        {"a": "同数無作為日集合(対照1)", "b": f"年で層化・{N_RANDOM:,} 回"},
        {"a": "暦シフト・プラセボ(対照2)", "b": f"k ∈ {{{', '.join(str(k) for k in PLACEBO_SHIFTS)}}} 営業日、折り返し除去"},
        {"a": "符号シャッフル(対照3)", "b": f"{N_SHUFFLE:,} 回"},
        {"a": "同時置換の帰無 A / B", "b": f"1 抽選 = 20 日ブロック 1 回の置換、同じ置換世界から 9 規則すべての統計量、最大値、{N_PERM:,} 抽選"},
        {"a": "train / val の暦分割", "b": "train = 1990-01-04 .. 2007-12-31、val = 2008-01-01 .. 2015-08-28"},
        {"a": "MDE 係数", "b": f"{Z_MDE:.4f}(α 0.05 両側・検出力 0.8)"},
        {"a": "エッジ推移(§5)", "b": f"窓 W = {EDGE_WINDOW} 標本 / 単位 U = 年 / 時間軸 = 暦時間 / 区切り = 暦年 / ブロック長 {EDGE_BLOCK}"},
        {"a": "条件分析(§6)の状態変数", "b": "実現ボラ20日三分位 / 直前日リターンの符号 / 制度区分(年代)/ 泊数(1・2〜3・4+)"},
    ], [("a", "項目", -1), ("b", "事前登録値", -1)]))
    A("")
    A("## 1. カレンダー導出と母集団")
    A("")
    A("### 1.1 祝日の機械的導出")
    A("")
    A("取引日 = 主系列 `full_day_daily.csv.gz` の日付列。祝日 = その期間内の暦日のうち、"
      "取引日でなく、かつ(月〜金の平日、または年末年始 12-31・01-01〜01-03)であるもの。"
      "週末はそれだけでは祝日にしない。祝日前(PH)= 各祝日の直前の取引日。")
    A("")
    A(_table(hol_counts.to_dict("records"),
             [("decade", "年代", -1), ("n_holidays", "祝日(暦日)", 0),
              ("n_holiday_eves", "祝日前(PH)日数", 0)]))
    A("")
    A(f"開発セット全体: 祝日 {steps['holidays_derived']:,} 日、祝日前 {steps['holiday_eves']:,} 日"
      f"({steps['holiday_eves'] / span_years:.2f} 日/年、期間 {span_years:.2f} 年)。"
      "導出結果は `calendar_holidays.csv`(暦日ごと)と "
      "`calendar_holiday_counts_by_decade.csv`(年代別件数)に出力した。")
    A("")
    A("### 1.2 規則ごとの日数と除外の内訳")
    A("")
    A(_table(excl.to_dict("records"), [("step", "段階", -1), ("n", "件数", 0)]))
    A("")
    A("close→close ペアは主系列 `full_day_daily` の連続 2 行から作り、端点規則"
      "(両日が封印外のときだけ開発セット)は未封印フレームの連続行を取ることで自動的に満たされる。"
      "泊数は暦日差として各ペアに付した(`pairs_futures.csv` の `nights` 列)。")
    A("")
    A("## 2. 費用")
    A("")
    A(f"先物(マイクロ規格を適用): 保守 = 手数料 11 円/片側 × 2 + 呼値 5 ポイント × 乗数 10 円 × 2 = "
      f"{cost_yen_cons} 円/往復 → cost_bps(t) = {cost_yen_cons} /(close_day(t−1) × 10)× 10^4。"
      f"楽観 = 手数料のみ {cost_yen_opt} 円。")
    A("")
    cost = pairs["cost_bps_cons"].dropna()
    A(_table([
        {"a": "保守 cost_bps(先物、全ペア)", "b": float(cost.median()), "c": float(cost.mean()),
         "d": float(cost.min()), "e": float(cost.max())},
        {"a": "楽観 cost_bps(先物、全ペア)", "b": float(pairs["cost_bps_opt"].median()),
         "c": float(pairs["cost_bps_opt"].mean()), "d": float(pairs["cost_bps_opt"].min()),
         "e": float(pairs["cost_bps_opt"].max())},
        {"a": "保守 cost_bps(1321.T、価格帯呼値)", "b": float(p1321["cost_bps_cons"].median()),
         "c": float(p1321["cost_bps_cons"].mean()), "d": float(p1321["cost_bps_cons"].min()),
         "e": float(p1321["cost_bps_cons"].max())},
    ], [("a", "系列", -1), ("b", "中央値", 3), ("c", "平均", 3), ("d", "最小", 3), ("e", "最大", 3)]))
    A("")
    A("1321.T は手数料 0(SOR)、呼値は `etf_tick_size_yen_by_price_band` の価格帯表を"
      "ペアごとに引いた(開発セットの終値 8,270〜21,480 円 → 10,000 円以下は 1 円、"
      "30,000 円以下は 5 円)。保守 = 片側 1 ティック × 2、楽観 = 手数料のみ(= 0)。")
    A("")
    A("当時のラージ仕様(呼値 10 ポイント・乗数 1,000 円)での往復費用は "
      "22 + 2×10×1,000 = 20,022 円 → close 20,000 円のとき 20,022 /(20,000×1,000)×10^4 = "
      "**10.0bps**(マイクロ換算 3.1bps の約 3.3 倍)。感度としての記録のみで判定には使わない。")
    A("")
    A("## 3. 主指標(規則ごと)")
    A("")
    A("主指標 (1) = 規則日の保守コスト後平均(bps/日)と 95% CI、"
      "主指標 (2) = 規則日の平均 − 非規則日の平均(グロス、bps)と 95% CI。"
      "CI はブロック・ブートストラップ(ブロック長 20・2,000 回・percentile 法)。"
      "TOM / WD / PH は「メジャー SQ 日とその前営業日を端点に含むペアを除外」した集合が主指標、"
      "除外なしを併記。SQm / SQq は 1321.T が主評価で、先物は併記。")
    A("")
    cols = [("rule", "規則", -1), ("series", "系列", -1), ("variant", "集合", -1),
            ("n", "n", 0), ("net_mean_cons_bps", "主指標1 保守ネット平均", 3),
            ("net_ci_lo", "CI下限", 3), ("net_ci_hi", "CI上限", 3),
            ("gross_mean_bps", "グロス平均", 3),
            ("diff_gross_bps", "主指標2 差", 3), ("diff_ci_lo", "差CI下限", 3),
            ("diff_ci_hi", "差CI上限", 3), ("cost_mean_bps", "平均費用", 3),
            ("net_mean_opt_bps", "楽観ネット平均", 3)]
    A(_table(main_df.to_dict("records"), cols))
    A("")
    A("**n < ブロック長 20 の規則(SQq: 1321.T の開発セットで n = 16)ではブロック・ブートストラップ CI は"
      "構造的に定義できず「—」になる。**その場合の参考値として、自己相関を考慮しない独立標本の"
      "t 区間を `main_indicators.csv` / `gate_comparison.csv` の `*_t_supp` 列に併記した"
      "(事前登録の統計量ではない)。")
    A("")
    A(_table([r for r in main_df.to_dict("records")
              if r["rule"] in SQ_RULES and r["variant"].startswith("主指標")],
             [("rule", "規則", -1), ("n", "n", 0),
              ("net_mean_cons_bps", "主指標1", 3),
              ("net_ci_lo", "ブロックCI下限", 3), ("net_ci_hi", "ブロックCI上限", 3),
              ("net_ci_lo_t_supp", "参考 t区間 下限", 3),
              ("net_ci_hi_t_supp", "参考 t区間 上限", 3)]))
    A("")
    A("## 4. MDE(実測 σ、除外前 / 除外後)")
    A("")
    A(f"MDE = {Z_MDE:.4f} × σ/√n(α 0.05 両側・検出力 0.8)。主指標 2 の MDE は"
      "2 標本の SE を合成した値。")
    A("")
    A(_table(mde_df.to_dict("records"),
             [("rule", "規則", -1), ("series", "系列", -1), ("variant", "集合", -1),
              ("n", "n", 0), ("sd_net_bps", "σ(保守ネット, bps)", 2),
              ("mde_net_bps", "MDE 主指標1(bps)", 2),
              ("sd_gross_bps", "σ(グロス, bps)", 2), ("n_non_rule", "非規則日 n", 0),
              ("mde_diff_bps", "MDE 主指標2(bps)", 2)]))
    A("")
    A("**SQ 規則(SQm・SQq)は開発セットの n が小さく検出力が不足している**"
      "(1321.T の開発セットは 2011-09..2015-08 のみで SQm n = "
      f"{steps['etf1321_SQm_days']}、SQq n = {steps['etf1321_SQq_days']})。"
      "事前登録どおり、判定は可能だが「検出できない」が最も起こりやすい結果であることを先に記す。")
    A("")
    A("## 5. 事前登録の関門との比較(数値の対照のみ)")
    A("")
    A(_table(gate_df.to_dict("records"),
             [("rule", "規則", -1), ("series", "系列", -1), ("n", "n", 0),
              ("net_mean_cons_bps", "主指標1", 3), ("ci_lo", "CI下限", 3),
              ("ci_hi", "CI上限", 3), ("mde_bps", "MDE", 2),
              ("net_minus_mde", "主指標1−MDE", 3),
              ("null_A_p95", "帰無A 95点", 3), ("net_minus_nullA", "主指標1−帰無A", 3),
              ("diff_gross_bps", "主指標2", 3), ("diff_ci_lo", "差CI下限", 3),
              ("diff_ci_hi", "差CI上限", 3), ("null_B_p95", "帰無B 95点", 3),
              ("diff_minus_nullB", "主指標2−帰無B", 3)]))
    A("")
    A("## 6. 同時置換の帰無 A / B")
    A("")
    A("1 抽選 = 日次リターン系列を 20 日ブロックで 1 回置換した「同じ仮想世界」。"
      "その 1 つの世界から 9 規則すべての統計量を計算し、最大値を取る。2,000 抽選。"
      "帰無 A = 主指標 (1) の 9 規則最大、帰無 B = 主指標 (2) の 9 規則最大。"
      "SQ 規則の主評価系列は 1321.T なので、**系列ごとに 1 つの仮想世界**を作り、"
      "先物で評価する規則には先物の帰無を、1321.T で評価する規則には 1321.T の帰無を当てた"
      "(第 12 節の逸脱欄に理由を記載)。")
    A("")
    A(_table(null_summary.to_dict("records"),
             [("world", "仮想世界", -1), ("null", "帰無", -1), ("p50", "50 点", 3),
              ("p95", "**95 点(バー)**", 3), ("p99", "99 点", 3), ("n_draws", "抽選数", 0)]))
    A("")
    A("## 7. 副指標")
    A("")
    A(_table(sub_df.to_dict("records"),
             [("rule", "規則", -1), ("series", "系列", -1), ("n", "n", 0),
              ("days_per_year", "年あたり保有日数", 2),
              ("sharpe_annualised", "Sharpe(年率)", 3), ("hit_rate", "勝率", 4),
              ("max_drawdown_yen_1unit", "最大DD(円/先物マイクロ1枚・ETF1口)", 0),
              ("net_mean_1990s", "1990s 平均", 3), ("net_mean_2000s", "2000s 平均", 3),
              ("net_mean_2010s", "2010s 平均", 3),
              ("gross_mean_1321_bps", "1321.T グロス", 3),
              ("gross_mean_1306_bps", "1306.T グロス", 3)]))
    A("")
    A("1306.T は 2015-01-05..2026-03-31 が価格 1/10(比は正しい)という既知欠陥があるため、"
      "**グロス平均のみ**を市場横断の確認として併記し、費用は計算していない(判定には使わない)。"
      "さらに、窓の境目にまたがる 1 ペア(2014-12-30 → 2015-01-05、−9,006bps = 印字倍率の変更そのもの)は"
      f"印字由来なので市場横断の確認から除外した(除外件数 "
      f"{steps['etf1306_price_scale_splice_pairs']} ペア、`pairs_1306.csv` の "
      "`price_scale_splice` 列で印付け。1321.T の同種の印は "
      f"{steps['etf1321_price_scale_splice_pairs']} 件)。"
      "この 1 ペアは 2015-01-05(月・1 月の第 1 営業日)なので TOM と WD-Mon の"
      "1306.T 列にだけ効いていた。")
    A("")
    A("## 8. train / val(暦分割)")
    A("")
    A(_table(tv_df.to_dict("records"),
             [("rule", "規則", -1), ("split", "分割", -1), ("n", "n", 0),
              ("net_mean_cons_bps", "主指標1", 3), ("ci_lo", "CI下限", 3),
              ("ci_hi", "CI上限", 3), ("mde_bps", "MDE", 2),
              ("diff_gross_bps", "主指標2", 3), ("diff_ci_lo", "差CI下限", 3),
              ("diff_ci_hi", "差CI上限", 3)]))
    A("")
    A("## 9. 対照")
    A("")
    A("### 9.1 同数無作為日集合(年で層化、1,000 回)")
    A("")
    A(_table(rnd_rows, [("rule", "規則", -1), ("series", "系列", -1), ("n", "n", 0),
                        ("observed_net_mean_bps", "実測(保守ネット)", 3),
                        ("null_mean_bps", "帰無平均", 3), ("null_p95_bps", "帰無 95 点", 3),
                        ("share_ge_observed", "実測以上の割合", 4)]))
    A("")
    A("### 9.2 暦シフト・プラセボ(k 営業日、折り返し除去)")
    A("")
    A(_table(placebo_rows,
             [("rule", "規則", -1), ("k_trading_days", "k", 0), ("n", "n", 0),
              ("n_folded_back_removed", "折り返し除去", 0),
              ("n_shifted_off_calendar", "暦外", 0),
              ("net_mean_cons_bps", "保守ネット平均", 3), ("ci_lo", "CI下限", 3),
              ("ci_hi", "CI上限", 3), ("observed_rule_net_mean_bps", "参考: 元の規則", 3)]))
    A("")
    A("折り返し除去 = ずらした結果が元の規則の集合に戻る日付をプラセボ集合から除いた件数"
      "(TOM の窓内折り返し、曜日規則では k が 5 の倍数でないため 0、など)。")
    A("")
    A("### 9.3 符号シャッフル(1,000 回)")
    A("")
    A(_table(shuffle_rows, [("rule", "規則", -1), ("n", "n", 0),
                            ("observed_net_mean_bps", "実測", 3),
                            ("null_p95_bps", "帰無 95 点", 3),
                            ("share_ge_observed", "実測以上の割合", 4)]))
    A("")
    A("## 10. 条件分析(標準 §6、事前登録の 4 状態変数)")
    A("")
    A("状態変数はいずれも建玉時点(close(t−1))で観測可能。実現ボラは 20 日終値リターンの標準偏差を"
      "1 日ずらしたもの、三分位の切り分けは主評価集合全体で決めた。"
      "各規則について、状態 × 指標の表・状態間の差(CI・MDE)・全比較の同時置換帰無 95 点を出す。"
      "**状態別の MDE は無条件より大きい**(三分位なら n が約 1/3 で約 1.7 倍)。")
    A("")
    A("### 10.1 状態 × 指標")
    A("")
    A(_table(state_all.to_dict("records"),
             [("rule", "規則", -1), ("variable", "状態変数", -1), ("state", "状態", -1),
              ("n", "n", 0), ("mean", "グロス平均", 3), ("ci_lo", "CI下限", 3),
              ("ci_hi", "CI上限", 3), ("cost_mean", "平均費用", 3),
              ("net_mean", "費用後平均", 3), ("net_ci_lo", "費用後CI下限", 3),
              ("net_ci_hi", "費用後CI上限", 3), ("mde_bps", "MDE(CI幅換算)", 2)]))
    A("")
    A("### 10.2 状態間の差(グロス)と同時置換の帰無")
    A("")
    A(_table(diff_all.to_dict("records"),
             [("rule", "規則", -1), ("variable", "状態変数", -1), ("state_a", "状態A", -1),
              ("state_b", "状態B", -1), ("n_a", "nA", 0), ("n_b", "nB", 0),
              ("diff", "差(A−B)", 3), ("ci_lo", "CI下限", 3), ("ci_hi", "CI上限", 3),
              ("mde", "MDE", 2), ("null_p95", "同時置換帰無95点", 3),
              ("verdict", "区分", -1)]))
    A("")
    A("区分は標準 §6-3 の固定規則: 「候補」= |差| が同時置換帰無 95 点を超え、かつ差の CI が"
      "ゼロを含まない。「判定不能」= MDE が |差| 以上(= その n では差が見えない)。"
      "「差なし」= CI がゼロを含み、かつ MDE 以上の差が見えている場合。"
      "**「判定不能」を「差なし」と読み替えてはならない。**")
    A("")
    A("n < ブロック長 20 の状態(および規則全体で n < 20 の SQq)では CI・MDE・帰無が"
      "算出できないか退化する。その行は「—」または判定不能として現れる。")
    A("")
    A("### 10.3 規則ごとの 3 行要約(標準 §6-6)")
    A("")
    A("書式の定義: 「効く状況」= その状態の**費用後**平均の 95% CI が全て正、"
      "「効かない状況」= 費用後 CI が全て負、「判定不能な状況」= 費用後 CI がゼロを含む。")
    A("")
    for r in summary_df.to_dict("records"):
        A(f"**{r['rule']}**")
        A("")
        A(f"- 効く状況: {r['効く状況(費用後CIが全て正)']}")
        A(f"- 効かない状況: {r['効かない状況(費用後CIが全て負)']}")
        A(f"- 判定不能な状況: {r['判定不能な状況(費用後CIがゼロを含む)']}")
        A(f"- 同時置換帰無 95 点(最大差)= {_fmt(r['同時置換帰無95点(最大差, bps)'])} bps、"
          f"「候補」に達した差 = {int(r['候補となった差の数'])} 件")
        A("")
    A("## 11. エッジ推移(標準 §5)")
    A("")
    if skip_edge_trend:
        A("(この実行では `--skip-edge-trend` により省略)")
    else:
        A(f"事前登録値: 移動窓 W = {EDGE_WINDOW} 標本、単位 U = 年、時間軸 = 暦時間、"
          f"区切り = 暦年、ブロック長 = {EDGE_BLOCK}、リサンプル {N_BOOT:,} 回、seed {SEED}。"
          "TOM 規則の系列と全日の系列(いずれもメジャー SQ 隣接除外後)に適用し、"
          "§5-1 の分解どおりグロス・費用・ネットの 3 本を別々に出した。")
        A("")
        A(_table(edge_summary.to_dict("records"),
                 [("series", "系列 / 脚", -1), ("n", "n", 0), ("slope", "傾き(bps/年)", 4),
                  ("slope_ci_lo", "傾きCI下限", 4), ("slope_ci_hi", "傾きCI上限", 4),
                  ("slope_mde", "傾きMDE", 4), ("mean_first", "前半平均", 3),
                  ("mean_second", "後半平均", 3), ("half_diff", "後半−前半", 3),
                  ("half_diff_ci_lo", "差CI下限", 3), ("half_diff_ci_hi", "差CI上限", 3),
                  ("last_window_mean", "直近250標本平均", 3),
                  ("last_window_ci_lo", "同CI下限", 3), ("last_window_ci_hi", "同CI上限", 3),
                  ("judgment", "判定文(§5-7)", -1)]))
        A("")
        A("移動窓の系列と暦年ごとの区切り表は `edge_trend_*_rolling.csv` / "
          "`edge_trend_*_by_year.csv` に出力した。判定文は §5-7 の固定規則"
          "(拡大 / 縮小 / 判定不能(標本不足))であり、"
          "**「判定不能」を「安定」と読み替えてはならない**。")
    A("")
    A("## 12. 事前登録からの逸脱と解釈上の判断")
    A("")
    A("1. **主系列の終値の取り方**: PREREG の「データ」表は `full_day_daily.csv.gz` を"
      "**主系列(close→close の日次リターン)**と定め、実装指示も full_day_daily を指定している。"
      "一方「リターンの定義」節は r(t) = close_day(t)/close_day(t−1) − 1(引け板寄せ)と書いており、"
      "2007-09 以降は終日区切りの終値(夜間終値)と日中終値が一致しない"
      f"(開発セットで {steps['days_full_close_ne_day_session_close']:,} 日が不一致)。"
      "**主指標は指示どおり full_day_daily の close→close で計算**し、費用の元本だけは PREREG の"
      "式が明示する `close_day(t−1)`(日中セッション終値 = 板寄せ価格)を用いた。"
      "元本を full_day 終値に替えた場合の費用は `pairs_futures.csv` の "
      "`cost_bps_cons_fullday_base` 列に併記した(差は "
      f"{float((pairs['cost_bps_cons'] - pairs['cost_bps_cons_fullday_base']).abs().max()):.4f}bps 以下)。")
    A("2. **同時置換の帰無の「1 つの仮想世界」**: PREREG は 9 規則を 1 つの置換系列から計算すると書くが、"
      "SQm・SQq の主評価系列は 1321.T で、先物とは系列も期間も異なるため 1 本の系列に収まらない。"
      "そこで**系列ごとに 1 つの仮想世界**(先物 1 つ・1321.T 1 つ)を作り、どちらの世界でも 9 規則すべての"
      "統計量を計算して最大を取った。規則は自分が評価された系列のバーと比較する。"
      "帰無 A と帰無 B は同一の置換順序から計算しており、PREREG の「同じ仮想世界」の要件を満たす。")
    A("3. **TOM の定義の端**: 「月末最終営業日と翌月最初の 3 営業日」を、データ内に存在する各月の"
      "「最終取引日」と「最初の 3 取引日」の和集合として実装した。系列の最初の月は前月の月末が"
      "データ外、最後の月は翌月がデータ外なので、その 2 か月だけ 4 日組が片側になる。")
    A("4. **SQq の先物での主指標**: メジャー SQ 隣接ペアの除外は定義上メジャー SQ 日そのものを全て落とすため、"
      "先物での SQq は除外後 n = 0 になる。PREREG が SQ 規則の主評価を 1321.T に置いた理由がここに現れる。"
      "先物の SQm / SQq は除外なしの併記のみとした。")
    A("5. **n < ブロック長の CI**: SQq は 1321.T の開発セットで n = 16 < ブロック長 20 のため、"
      "事前登録のブロック・ブートストラップ CI が構造的に定義できない(「—」と表示)。"
      "参考として独立標本の t 区間を `*_t_supp` 列に併記したが、事前登録の統計量ではなく、"
      "PREREG の「判定不能区分(標本不足)」に該当する。")
    A("6. **メジャー SQ 隣接の除外に使う SQ 日**: SQq 規則と同じ「第 2 金曜、休日なら前営業日」の"
      "定義で決めた日(とその前営業日)を除外に用いた(2 つの定義を分けていない)。")
    A("7. それ以外の逸脱はない。ブロック長・リサンプル数・seed・シフト幅・分割日・費用定数・"
      "状態変数・窓幅は全て事前登録どおり。規則の窓幅(TOM 4 日、PH 1 日)は変更していない。")
    A("")
    A("## 13. 出力ファイル")
    A("")
    A("`RUN.json`(seed・git rev・入力 MD5・各段階の n)、`pairs_futures.csv` / `pairs_1321.csv` / "
      "`pairs_1306.csv`、`calendar_*.csv`、`main_indicators.csv`、`mde.csv`、`sub_indicators.csv`、"
      "`train_val.csv`、`control1_stratified_random.csv` / `control1_draws.csv`、"
      "`control2_placebo_shift.csv`、`control3_sign_shuffle.csv`、"
      "`joint_permutation_null.csv` / `joint_permutation_draws.csv` / `joint_permutation_argmax.csv`、"
      "`gate_comparison.csv`、`condition_state_table.csv` / `condition_diff_table.csv` / "
      "`condition_summary_3lines.csv`、`edge_trend_*.csv`、`exclusions.csv`。")
    A("")
    return "\n".join(md) + "\n"


# =============================================================================
# ITERATION 1 (docs/PHASE2/P2-04/PREREG.md「条件分析と反復の梯子」反復 1):
# each of the 9 unconditional rules × the 20-day realised-vol tercile
# (as of entry, cutpoints fixed on train and applied to val) = 27 added
# configurations, cumulative N = 36. NOT nested with anything else.
#
# Deliberately duplicates (rather than shares) the dataset-build steps of
# `main()` above, so nothing in this section can ever change iteration 0's
# byte-identical output — verified in
# `tests/test_phase2_p2_04.py::test_iteration0_output_is_byte_identical`.
# =============================================================================

ITER1_OUT_DIR = REPO_ROOT / "backtest_data" / "phase2_runs" / "P2-04" / "iter1_20260906"
ITER1_UNCOND_LABEL = "(無条件)"


def _load_and_build_dataset_iter1() -> dict:
    """Rebuild the population iteration 0's `main()` uses (pairs, p1321,
    keep_mask/all_mask, rule sets, cost constants), plus the primary series'
    vol20 state needed only by iteration ≥ 1. Same pure helpers, same input
    files, same formulas as `main()` — so the resulting `pairs`/`p1321`
    frames are numerically identical to iteration 0's (spot-checked by the
    unconditional-row reproduction test).
    """
    c_fee = require_source("jpx_nikkei225_micro_futures.fee_yen_per_contract_per_side",
                           root=REPO_ROOT)
    c_tick = require_source("jpx_nikkei225_micro_futures.tick_size_yen", root=REPO_ROOT)
    c_mult = require_source("jpx_nikkei225_micro_futures.multiplier_yen_per_point",
                            root=REPO_ROOT)
    c_sor = require_source("jpx_cash_equity.sor_commission_yen", root=REPO_ROOT)
    c_bands = require_source("jpx_cash_equity.etf_tick_size_yen_by_price_band",
                             root=REPO_ROOT)
    fee, tick_pt, mult = int(c_fee.value), int(c_tick.value), int(c_mult.value)
    cost_yen_cons = 2 * fee + 2 * tick_pt * mult
    bands = dict(c_bands.value)
    etf_fee = float(c_sor.value)

    full = load_unsealed(FULL_FILE, UNIT, root=REPO_ROOT)
    dayses = load_unsealed(DAY_FILE, UNIT, root=REPO_ROOT)
    etf1321 = load_unsealed(ETF_1321, UNIT, root=REPO_ROOT)
    for frame in (full, dayses, etf1321):
        frame["date"] = pd.to_datetime(frame["date"])
        frame.sort_values("date", inplace=True)
        frame.reset_index(drop=True, inplace=True)

    trading_days = [d.date() for d in full["date"]]
    rule_sets = build_rule_day_sets(trading_days)

    pairs = build_close_pairs(full[["date", "close"]])
    day_close = pd.Series(dayses["close"].to_numpy(dtype=float),
                          index=dayses["date"].to_numpy())
    pairs["close_prev_day_session"] = pd.to_datetime(pairs["date_prev"]).map(day_close)
    notional = pairs["close_prev_day_session"] * mult
    pairs["cost_bps_cons"] = cost_yen_cons / notional * 1e4
    pairs["r_net_bps_cons"] = pairs["r_bps"] - pairs["cost_bps_cons"]

    d_t = np.array([d.date() for d in pd.to_datetime(pairs["date"])])
    d_prev = np.array([d.date() for d in pd.to_datetime(pairs["date_prev"])])
    marked = major_sq_marked_days(trading_days)
    sq_excluded = np.array([(a in marked) or (b in marked) for a, b in zip(d_prev, d_t)])
    keep_mask = ~sq_excluded
    all_mask = np.ones(len(pairs), dtype=bool)

    for name in RULES:
        pairs[f"is_{name}"] = np.isin(d_t, np.array(sorted(rule_sets[name]), dtype=object))
    pairs["split"] = np.where(pd.to_datetime(pairs["date"]) <= TRAIN_END, "train", "val")

    def etf_pairs(df: pd.DataFrame) -> pd.DataFrame:
        p = build_close_pairs(df[["date", "close"]])
        ticks = p["close_prev"].map(lambda x: etf_tick_yen(float(x), bands))
        p["cost_bps_cons"] = (2 * etf_fee + 2 * ticks) / p["close_prev"] * 1e4
        p["r_net_bps_cons"] = p["r_bps"] - p["cost_bps_cons"]
        et = np.array([d.date() for d in pd.to_datetime(p["date"])])
        e_sets = build_rule_day_sets([d.date() for d in df["date"]])
        for name in RULES:
            p[f"is_{name}"] = np.isin(et, np.array(sorted(e_sets[name]), dtype=object))
        p["split"] = np.where(pd.to_datetime(p["date"]) <= TRAIN_END, "train", "val")
        return p

    p1321 = etf_pairs(etf1321)

    # ---- iteration-1 state variable: the PRIMARY series' vol20, as of entry,
    # mapped by date onto both the futures pairs and the 1321.T pairs (a
    # single state series shared across every rule regardless of which series
    # evaluates that rule's main indicator).
    vol_by_date = primary_series_vol20(full)
    pairs["vol20"] = pd.to_datetime(pairs["date"]).map(vol_by_date)
    p1321["vol20"] = pd.to_datetime(p1321["date"]).map(vol_by_date)

    # terciles FIXED on the train split of the PRIMARY series' own pairs
    # (unrestricted by keep_mask — a market-wide state, not a per-rule one),
    # then applied unchanged to val and to the 1321.T frame.
    train_mask_primary = (pairs["split"] == "train").to_numpy()
    q1, q2 = tercile_cutpoints(pairs["vol20"].to_numpy(dtype=float), train_mask_primary)
    pairs["state_vol_iter1"] = label_tercile(pairs["vol20"].to_numpy(dtype=float), q1, q2)
    p1321["state_vol_iter1"] = label_tercile(p1321["vol20"].to_numpy(dtype=float), q1, q2)

    n_1321_vol_na = int((~np.isin(np.array([d.date() for d in pd.to_datetime(p1321["date"])]),
                                  np.array([d.date() for d in pd.to_datetime(pairs["date"])])))
                        .sum())

    return {
        "pairs": pairs, "p1321": p1321, "keep_mask": keep_mask, "all_mask": all_mask,
        "rule_sets": rule_sets, "cost_yen_cons": cost_yen_cons,
        "vol_cutpoints": (q1, q2),
        "n_train_vol_obs": int((train_mask_primary & np.isfinite(
            pairs["vol20"].to_numpy(dtype=float))).sum()),
        "n_1321_dates_not_in_futures_calendar": n_1321_vol_na,
        "inputs": [FULL_FILE, DAY_FILE, ETF_1321],
    }


def _population_for_rule(rule: str, pairs: pd.DataFrame, p1321: pd.DataFrame,
                         keep_mask: np.ndarray):
    if rule in SQ_RULES:
        return p1321, np.ones(len(p1321), dtype=bool), "1321.T"
    return pairs, keep_mask, "先物(主系列)"


def run_iteration1(out_dir: Path | None = None) -> int:
    out = out_dir if out_dir is not None else ITER1_OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    def write(df: pd.DataFrame, name: str):
        df.to_csv(out / name, index=False)
        written.append(name)

    ds = _load_and_build_dataset_iter1()
    pairs, p1321 = ds["pairs"], ds["p1321"]
    keep_mask = ds["keep_mask"]
    q1, q2 = ds["vol_cutpoints"]

    # ---- per (rule, tercile-or-unconditional, split) indicator rows --------
    rows = []
    for rule in RULES:
        frame, emask, series = _population_for_rule(rule, pairs, p1321, keep_mask)
        ev = frame.loc[emask].reset_index(drop=True)
        rm = ev[f"is_{rule}"].to_numpy(dtype=bool)
        tm = ev["state_vol_iter1"].to_numpy()
        splitcol = ev["split"].to_numpy()
        netcons = ev["r_net_bps_cons"].to_numpy(dtype=float)
        gross = ev["r_bps"].to_numpy(dtype=float)

        configs = [(ITER1_UNCOND_LABEL, rm)] + [
            (terc, rm & (tm == terc)) for terc in TERCILE_LABELS]
        for label, cmask in configs:
            for split in ("train", "val"):
                sm = splitcol == split
                res = conditional_indicator(netcons[sm], gross[sm], cmask[sm])
                rows.append({"rule": rule, "series": series, "state_vol": label,
                            "split": split, **res})
    ind_df = pd.DataFrame(rows)
    write(ind_df, "iter1_indicators.csv")

    # ---- val improvement vs iteration 0's unconditional rule, vs MDE -------
    val_uncond = {r["rule"]: r for r in rows
                 if r["split"] == "val" and r["state_vol"] == ITER1_UNCOND_LABEL}
    val_rows = [r for r in rows if r["split"] == "val" and r["state_vol"] != ITER1_UNCOND_LABEL]
    summary_rows = []
    for r in val_rows:
        base = val_uncond[r["rule"]]["net_mean_cons_bps"]
        improvement = (r["net_mean_cons_bps"] - base
                      if np.isfinite(r["net_mean_cons_bps"]) and np.isfinite(base)
                      else float("nan"))
        mde = r["mde_bps"]
        meets = bool(np.isfinite(improvement) and np.isfinite(mde) and improvement >= mde)
        summary_rows.append({
            "rule": r["rule"], "series": r["series"], "state_vol": r["state_vol"],
            "n_val": r["n"], "val_net_mean_cons_bps": r["net_mean_cons_bps"],
            "val_ci_lo": r["net_ci_lo"], "val_ci_hi": r["net_ci_hi"],
            "iter0_unconditional_val_mean_bps": base,
            "val_improvement_bps": improvement, "mde_bps": mde,
            "improvement_ge_mde": meets,
        })
    summary_df = pd.DataFrame(summary_rows)
    write(summary_df, "iter1_val_summary.csv")
    any_stop_trigger = bool(summary_df["improvement_ge_mde"].any()) if len(summary_df) else False

    # ---- joint permutation nulls A / B over all 36 configurations ----------
    def masks_for_world(frame: pd.DataFrame, futures_keep_mask: np.ndarray | None):
        """`futures_keep_mask` (sized to `frame`) applies to FUTURES_RULES only,
        matching iteration 0's exact per-rule eval-mask choice; every other
        rule (SQ rules, and on the 1321.T frame, every rule) gets the frame's
        own all-True mask — never a mask built for a differently-sized frame.
        """
        ones = np.ones(len(frame), dtype=bool)
        m = {}
        for rule in RULES:
            em = (futures_keep_mask if (futures_keep_mask is not None and rule in FUTURES_RULES)
                 else ones)
            rm = frame[f"is_{rule}"].to_numpy(dtype=bool)
            tm = frame["state_vol_iter1"].to_numpy()
            m[rule] = (rm & em, em)
            for terc in TERCILE_LABELS:
                m[f"{rule}×{terc}"] = (rm & (tm == terc) & em, em)
        return m

    fut_masks = masks_for_world(pairs, futures_keep_mask=keep_mask)
    etf_masks = masks_for_world(p1321, futures_keep_mask=None)
    assert len(fut_masks) == 36 and len(etf_masks) == 36

    draws_a, draws_b, arg_fut = joint_permutation_null(
        pairs["r_net_bps_cons"].to_numpy(dtype=float),
        pairs["r_bps"].to_numpy(dtype=float), fut_masks, BLOCK, N_PERM, SEED)
    draws_a_etf, draws_b_etf, arg_etf = joint_permutation_null(
        p1321["r_net_bps_cons"].to_numpy(dtype=float),
        p1321["r_bps"].to_numpy(dtype=float), etf_masks, BLOCK, N_PERM, SEED + 1)

    bar_a_fut = float(np.percentile(draws_a, 95))
    bar_b_fut = float(np.percentile(draws_b, 95))
    bar_a_etf = float(np.percentile(draws_a_etf, 95))
    bar_b_etf = float(np.percentile(draws_b_etf, 95))
    write(pd.DataFrame({"draw": np.arange(N_PERM),
                        "null_A_futures": draws_a, "null_B_futures": draws_b,
                        "null_A_1321": draws_a_etf, "null_B_1321": draws_b_etf}),
          "iter1_joint_permutation_draws.csv")
    null_summary = pd.DataFrame([
        {"world": "先物(主系列、36構成の最大)", "null": "A(主指標1: 保守ネット平均)",
         "p50": float(np.percentile(draws_a, 50)), "p95": bar_a_fut,
         "p99": float(np.percentile(draws_a, 99)), "n_draws": N_PERM, "n_configs": 36},
        {"world": "先物(主系列、36構成の最大)", "null": "B(主指標2: 差)",
         "p50": float(np.percentile(draws_b, 50)), "p95": bar_b_fut,
         "p99": float(np.percentile(draws_b, 99)), "n_draws": N_PERM, "n_configs": 36},
        {"world": "1321.T(36構成の最大)", "null": "A(主指標1: 保守ネット平均)",
         "p50": float(np.percentile(draws_a_etf, 50)), "p95": bar_a_etf,
         "p99": float(np.percentile(draws_a_etf, 99)), "n_draws": N_PERM, "n_configs": 36},
        {"world": "1321.T(36構成の最大)", "null": "B(主指標2: 差)",
         "p50": float(np.percentile(draws_b_etf, 50)), "p95": bar_b_etf,
         "p99": float(np.percentile(draws_b_etf, 99)), "n_draws": N_PERM, "n_configs": 36},
    ])
    write(null_summary, "iter1_joint_permutation_null.csv")

    # ---- best conditional configuration per rule (val, by net mean) --------
    best_rows = []
    for rule in RULES:
        cand = [r for r in summary_rows if r["rule"] == rule
               and np.isfinite(r["val_net_mean_cons_bps"])]
        if not cand:
            continue
        best = max(cand, key=lambda r: r["val_net_mean_cons_bps"])
        best_rows.append(best)
    best_df = pd.DataFrame(best_rows)
    write(best_df, "iter1_best_per_rule.csv")

    md = _results_md_iter1(ds, ind_df, summary_df, null_summary, best_df,
                           bar_a_fut, bar_b_fut, bar_a_etf, bar_b_etf, any_stop_trigger)
    (out / "RESULTS.md").write_text(md, encoding="utf-8")
    written.append("RESULTS.md")

    run = {
        "unit": UNIT, "iteration": 1, "run_date": str(date(2026, 9, 6)), "seed": SEED,
        "git_rev": _git_rev(),
        "script": "scripts/phase2/p2_04_run.py",
        "script_md5": _md5(Path(__file__)),
        "inputs": [{"path": p, "md5": _md5(REPO_ROOT / p)} for p in ds["inputs"]],
        "seal_record_md5": _md5(REPO_ROOT / "backtest_data" / "phase2_sealed" / UNIT
                                / "SEALED.json"),
        "cumulative_N": 36,
        "n_added_this_iteration": 27,
        "parameters": {
            "block": BLOCK, "n_boot": N_BOOT, "n_permutation": N_PERM,
            "train_end": str(TRAIN_END.date()),
            "vol_tercile_cutpoints_train_fixed": [q1, q2],
            "n_train_vol_observations_used_for_cutpoints": ds["n_train_vol_obs"],
        },
        "stopping_rule": {
            "criterion": "val improvement vs iteration 0's unconditional rule >= per-config MDE",
            "any_configuration_meets_it": any_stop_trigger,
        },
        "headline": {
            "null_A_p95_futures": bar_a_fut, "null_B_p95_futures": bar_b_fut,
            "null_A_p95_1321": bar_a_etf, "null_B_p95_1321": bar_b_etf,
            "best_per_rule": best_df.to_dict("records"),
        },
        "outputs": sorted(written),
    }
    (out / "RUN.json").write_text(
        json.dumps(_json_safe(run), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(json.dumps(_json_safe(run["headline"]), ensure_ascii=False, indent=2))
    print(f"stopping rule (val improvement >= MDE, any of 27): {any_stop_trigger}")
    print(f"wrote {len(written) + 1} files to {out}")
    return 0


def _results_md_iter1(ds, ind_df, summary_df, null_summary, best_df,
                      bar_a_fut, bar_b_fut, bar_a_etf, bar_b_etf, any_stop_trigger) -> str:
    q1, q2 = ds["vol_cutpoints"]
    md: list[str] = []
    A = md.append
    A("# P2-04 反復 1 — 実現ボラ三分位による条件付け(9 規則 × 3 三分位 = 27 追加、累計 N = 36)")
    A("")
    A(f"実行日 2026-09-06 / seed {SEED} / git {_git_rev()[:12]} / 単位 {UNIT}。"
      "入力は全て `bot.research.sealed.load_unsealed(path, \"P2-04\")` 経由で読み込み、"
      "封印期間には一切触れていない。開発セットのみ(train = 1990-01-04..2007-12-31、"
      "val = 2008-01-01..2015-08-28)。")
    A("")
    A("**本書は数値の報告のみで、採用・棄却の解釈は行わない。**")
    A("")
    A("## 0. 状態変数の構成(この反復固有)")
    A("")
    A("実現ボラ三分位は**主系列**(`full_day_daily.csv.gz`、先物の close→close 日次リターン)から"
      "1 本だけ作り、先物ペアにも 1321.T ペアにも同じ値を日付で写像して当てた"
      "(規則がどちらの系列で主評価されるかに関わらず状態変数は共通)。")
    A("")
    A(_table([
        {"a": "vol20(建玉時点の実現ボラ)", "b": "std(主系列の close→close リターン、直近 20 標本)を"
         "1 日ずらしたもの — 保有ペアの手仕舞い日 t に付く値は、建玉日 t−1 までに確定していた"
         "リターンだけで計算される(手仕舞い日 t 自身のリターンを含まない)。"},
        {"a": "三分位の切り方", "b": f"train 分割(≤ 2007-12-31)の主系列ペア(n = {ds['n_train_vol_obs']:,}、"
         "keep_mask による除外なし)の vol20 の 33 / 67 パーセンタイルを切り点とし、"
         f"q1 = {q1:.6f}、q2 = {q2:.6f}(リターンの比率、bps 換算前)。"
         "**この切り点を val にも 1321.T にもそのまま適用**し、val や 1321.T のデータから"
         "切り点を作り直すことはしていない(先読みなし)。"},
        {"a": "1321.T への写像", "b": f"1321.T の手仕舞い日と主系列の暦日が一致しない日は vol20 が"
         f"欠測(空ラベル)になる。該当 {ds['n_1321_dates_not_in_futures_calendar']} 日。"},
    ], [("a", "項目", -1), ("b", "内容", -1)]))
    A("")
    A("## 1. 事前登録値(この実行で固定した設計)")
    A("")
    A(_table([
        {"a": "反復", "b": "1(反復 0 の無条件規則を実現ボラ三分位で条件付け)"},
        {"a": "追加構成数 / 累計 N", "b": "27 / 36(9 規則 × (無条件 1 + 三分位 3) を"
         "帰無の母数として使用)"},
        {"a": "ブロック・ブートストラップ", "b": f"ブロック長 {BLOCK} / リサンプル {N_BOOT:,} / seed {SEED}"},
        {"a": "同時置換の帰無 A / B(N=36)", "b": f"1 抽選 = 20 日ブロック 1 回の置換、同じ置換世界から"
         f"36 構成すべての統計量、最大値、{N_PERM:,} 抽選。系列ごとに 1 つの仮想世界"
         "(先物・1321.T)を作る点は反復 0 と同じ(PREREG 逸脱欄 #2 を踏襲)。"},
        {"a": "停止規則の判定式", "b": "val 改善(条件付き val 平均 − 反復0の無条件 val 平均) ≥ "
         "その構成自身の MDE(条件付き val 部分集合の σ・n から)"},
    ], [("a", "項目", -1), ("b", "値", -1)]))
    A("")
    A("## 2. 反復 0 との整合性チェック")
    A("")
    A("本反復で独立に再構築した `pairs` / `p1321`(データ読み込み・端点規則・費用・規則日集合は"
      "反復 0 の `main()` と同じ純関数・同じ入力ファイルで再構築)から計算した**無条件**規則の"
      "train / val 平均は、`tests/test_phase2_p2_04.py` で反復 0 の "
      "`backtest_data/phase2_runs/P2-04/iter0_20260906/train_val.csv` の値と数値一致することを確認済み"
      "(このスクリプト内では再掲しない)。")
    A("")
    A("## 3. 規則 × 状態(train / val)")
    A("")
    A("主指標 (1) = 条件付き日(規則 ∧ 三分位)の保守コスト後平均と 95% CI。"
      "主指標 (2) = 条件付き日の平均 − それ以外の日の平均(グロス)と 95% CI。"
      "CI はブロック・ブートストラップ(ブロック長 20・2,000 回)、n < 20 の行は構造的に「—」。")
    A("")
    cols = [("rule", "規則", -1), ("series", "系列", -1), ("state_vol", "状態(ボラ三分位)", -1),
            ("split", "分割", -1), ("n", "n", 0),
            ("net_mean_cons_bps", "主指標1 保守ネット平均", 3),
            ("net_ci_lo", "CI下限", 3), ("net_ci_hi", "CI上限", 3),
            ("diff_gross_bps", "主指標2 差", 3), ("diff_ci_lo", "差CI下限", 3),
            ("diff_ci_hi", "差CI上限", 3), ("mde_bps", "MDE", 2)]
    A(_table(ind_df.to_dict("records"), cols))
    A("")
    A("## 4. val 改善 vs 反復 0 の無条件規則、MDE との比較(27 条件付き構成)")
    A("")
    A("val 改善 = 条件付き構成の val 主指標1 − 同じ規則の反復0無条件規則の val 主指標1。"
      "MDE はその条件付き構成自身の val 部分集合(σ・n)から。"
      "**「MDE 以上」= 停止規則が数える改善**。")
    A("")
    A(_table(summary_df.to_dict("records"),
             [("rule", "規則", -1), ("series", "系列", -1), ("state_vol", "状態", -1),
              ("n_val", "val n", 0), ("val_net_mean_cons_bps", "val 主指標1", 3),
              ("val_ci_lo", "CI下限", 3), ("val_ci_hi", "CI上限", 3),
              ("iter0_unconditional_val_mean_bps", "反復0 無条件 val", 3),
              ("val_improvement_bps", "val 改善", 3), ("mde_bps", "MDE", 2),
              ("improvement_ge_mde", "改善≥MDE", -1)]))
    A("")
    n_meets = int(summary_df["improvement_ge_mde"].sum()) if len(summary_df) else 0
    A(f"**停止規則チェック: 27 条件付き構成のうち改善 ≥ MDE を満たすもの = {n_meets} 件。"
      f"いずれかが該当するか = {'はい' if any_stop_trigger else 'いいえ'}。**")
    A("")
    A("## 5. 規則ごとの最良条件付き構成(val 主指標1 が最大のもの)")
    A("")
    A(_table(best_df.to_dict("records"),
             [("rule", "規則", -1), ("series", "系列", -1), ("state_vol", "状態", -1),
              ("n_val", "val n", 0), ("val_net_mean_cons_bps", "val 主指標1", 3),
              ("val_ci_lo", "CI下限", 3), ("val_ci_hi", "CI上限", 3),
              ("val_improvement_bps", "val 改善", 3), ("mde_bps", "MDE", 2),
              ("improvement_ge_mde", "改善≥MDE", -1)]))
    A("")
    A("## 6. 同時置換の帰無 A / B(N = 36)")
    A("")
    A("1 抽選 = 日次リターン系列を 20 日ブロックで 1 回置換した「同じ仮想世界」。"
      "その 1 つの世界から 36 構成(9 規則 × (無条件 1 + 三分位 3))すべての統計量を計算し、最大値を取る。"
      "2,000 抽選。系列ごとに 1 つの仮想世界(先物・1321.T)を作り、どちらの世界でも"
      "36 構成すべての統計量を計算して最大を取った(反復 0 と同じ扱い)。")
    A("")
    A(_table(null_summary.to_dict("records"),
             [("world", "仮想世界", -1), ("null", "帰無", -1), ("p50", "50 点", 3),
              ("p95", "**95 点(バー)**", 3), ("p99", "99 点", 3),
              ("n_draws", "抽選数", 0), ("n_configs", "構成数", 0)]))
    A("")
    A("## 7. 事前登録からの逸脱と解釈上の判断")
    A("")
    A("1. **状態変数を 1 本の系列(主系列)からだけ作った**: 反復 0 の条件分析(§6)は"
      "SQ 規則の状態を 1321.T 自身の close 系列から作っていたが、本反復は「主系列の close→close "
      "リターンから状態を作る」という本反復の指示に従い、SQ 規則にも主系列由来の同じ vol20 を"
      "日付で写像して用いた。両者は異なる母集団になり得るため、反復 0 の条件分析(§6)の"
      "ボラ三分位の数値とは一致しない可能性がある(別の構成として記録)。")
    A("2. **三分位の切り点の母集団**: train 側の切り点は keep_mask(メジャーSQ隣接除外)を掛けない"
      "主系列の全ペア(train 分割)から作った。市場全体の状態を表す変数であり、"
      "個別規則の分母(除外後)に依存させないための選択。")
    A("3. **同時置換の帰無でも状態ラベルは固定**: 置換はリターンの値の並びだけを動かし、"
      "規則日ラベルと同様に vol 三分位ラベルも観測データから 1 回だけ計算した固定ラベルとして扱った"
      "(ボラ自体はリターンから作られる量なので、置換世界ごとに三分位を再計算する設計も考えられるが、"
      "反復 0 の「同じ構成」を保つため状態は固定した)。")
    A("4. それ以外の逸脱はない。ブロック長・リサンプル数・seed・train/val 分割日・費用定数は"
      "反復 0 と同一。")
    A("")
    A("## 8. 出力ファイル")
    A("")
    A("`RUN.json`、`iter1_indicators.csv`(36 構成 × train/val)、`iter1_val_summary.csv`"
      "(27 条件付き構成の val 改善・MDE 判定)、`iter1_best_per_rule.csv`、"
      "`iter1_joint_permutation_null.csv` / `iter1_joint_permutation_draws.csv`。")
    A("")
    return "\n".join(md) + "\n"


def _parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--skip-edge-trend", action="store_true",
                   help="skip the §5 edge-trend block (slow); diagnostics only")
    p.add_argument("--iteration", type=int, default=0, choices=(0, 1),
                   help="0 (default, byte-identical to the original script) or "
                        "1 (the vol-tercile conditioning ladder step)")
    return p.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    if args.iteration == 0:
        raise SystemExit(main(out_dir=args.out, skip_edge_trend=args.skip_edge_trend))
    raise SystemExit(run_iteration1(out_dir=args.out))

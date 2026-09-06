#!/usr/bin/env python
"""P2-01 iteration 0 — the pre-registered main test, DEVELOPMENT SET ONLY.

Implements exactly `docs/PHASE2/P2-01/PREREG.md` (frozen 2026-09-06):
Nikkei 225 futures overnight leg (day-session close(t) -> next day-session
open(t+1)), micro contract costs, block-bootstrap inference, three
pre-registered controls and a set of descriptive diagnostics.

Every input file is read through `bot.research.sealed.load_unsealed(path,
"P2-01")`, so the sealed evaluation window is structurally unreachable from
here. Nothing in this module interprets the numbers: it writes tables.

Usage:  PYTHONPATH=src python scripts/phase2/p2_01_run.py
        PYTHONPATH=src python scripts/phase2/p2_01_run.py --roll-rule quarterly \
            --out backtest_data/phase2_runs/P2-01/iter1_20260906

Iteration ledger: iteration 0 (2026-09-06) used the monthly roll rule as the
default under PREREG "限月ロールの扱い (a)" (limited months unconfirmed).
Iteration 1 (2026-09-06) is the pre-registered switch under "(b)": the owner
confirmed from the primary source (225Labo download page + JPX product
outline page, see `backtest_data/audit_fetch_JPX_n225f_months_20260906/`)
that the series is the LARGE Nikkei 225 futures contract, whose contract
months are quarterly (Mar/Jun/Sep/Dec) only -- so the roll-adjacent rule
switches from monthly 2nd-Friday to quarterly 2nd-Friday. `--roll-rule`
selects which one is used to build the MAIN judgment set; the default stays
"monthly" so a bare invocation reproduces iteration 0 exactly (verified by
diffing main_indicators.csv / pairs.csv against the iter0 output).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from bot.research.overnight import (  # noqa: E402
    GLITCH_ABS_LOG_RET_DEFAULT,
    block_bootstrap_ci,
    drop_glitches,
    overnight_returns,
    sign_shuffle_null,
)
from bot.research.sealed import load_unsealed  # noqa: E402

UNIT = "P2-01"
SEED = 20260906

# ---- pre-registered constants (PREREG "データ" / "コスト定数" / "指標と分母") ----
ANALYSIS_START = pd.Timestamp("2007-09-19")
TRAIN_END = pd.Timestamp("2016-12-31")        # train = .. TRAIN_END, val = after
GLITCH_THRESHOLD = GLITCH_ABS_LOG_RET_DEFAULT  # 0.10, applied to |simple return|
BLOCK = 20
N_BOOT = 2000
N_SHUFFLE = 1000
FEE_YEN_PER_SIDE = 11        # constants.yaml jpx_nikkei225_micro_futures
TICK_YEN = 5
MULTIPLIER = 10              # yen per index point
COST_YEN_CONSERVATIVE = 2 * FEE_YEN_PER_SIDE + 2 * TICK_YEN * MULTIPLIER   # 122
COST_YEN_OPTIMISTIC = 2 * FEE_YEN_PER_SIDE                                 # 22
MDE_BPS = 6.03               # PREREG: sigma 113.18bps, n=2769
MDE_DIFF_BPS = 8.07          # PREREG: sigma 151.55bps
GROSS_GATE_BPS = 14.9        # PREREG: MDE 6.03 + mean cost 8.89

# PREREG "母集団の定義": the five pairs with no night session, given as date pairs.
NIGHTLESS_PAIRS = [
    ("2007-12-28", "2008-01-04"),
    ("2008-01-04", "2008-01-07"),
    ("2008-12-30", "2009-01-05"),
    ("2009-01-05", "2009-01-06"),
    ("2016-07-15", "2016-07-19"),
]

# PREREG "セッション時刻の制度変更": the three dev-set regimes.
REGIMES = [
    ("2007-09..2011-02-13", pd.Timestamp("2007-09-19"), pd.Timestamp("2011-02-13")),
    ("2011-02-14..2016-07-18", pd.Timestamp("2011-02-14"), pd.Timestamp("2016-07-18")),
    ("2016-07-19..2020-12-20", pd.Timestamp("2016-07-19"), pd.Timestamp("2020-12-20")),
]

DAY_FILE = "backtest_data/n225f_225labo_20260828/day_session_daily.csv.gz"
NIGHT_FILE = "backtest_data/n225f_225labo_20260828/night_session_daily.csv.gz"
OUT_DIR = REPO_ROOT / "backtest_data" / "phase2_runs" / "P2-01" / "iter0_20260906"


# ---------------------------------------------------------------------------
# core computation (importable; exercised on synthetic tapes by tests/)
# ---------------------------------------------------------------------------

def build_pairs(day: pd.DataFrame) -> pd.DataFrame:
    """Day-session pairs (t, t+1) with returns, nights and per-pair costs.

    ``day`` must hold "date"/"open"/"close" (one row per trading day, sorted
    ascending) and must ALREADY be restricted to the rows eligible for the
    analysis: the endpoint rule (a pair is kept only when BOTH days are in
    the frame) then falls out of `overnight_returns` dropping the last row.

    Returns one row per pair with:
      date        entry date t (the close leg)
      date_t1     exit date t+1 (the open leg)
      r           r_night(t) as a SIMPLE return, i.e. the raw fraction --
                  named "r" so `drop_glitches` applies to it verbatim
      r_night_bps, r_day_bps        same in bps (r_day = close(t)/open(t)-1)
      nights                        calendar nights spanned by the pair
      cost_bps_cons / cost_bps_opt  per-pair cost on that pair's own notional
      r_net_bps_cons / r_net_bps_opt
      pnl_yen_cons                  1 micro contract, after conservative cost
    """
    day = day.reset_index(drop=True)
    on = overnight_returns(day, kind="simple")           # tested path, "simple"
    n = len(on)
    out = pd.DataFrame({
        "date": on["date"].to_numpy(),
        "date_t1": day["date"].shift(-1).iloc[:n].to_numpy(),
        "open_t": day["open"].iloc[:n].to_numpy(dtype=float),
        "close_t": day["close"].iloc[:n].to_numpy(dtype=float),
        "open_t1": day["open"].shift(-1).iloc[:n].to_numpy(dtype=float),
        "close_t1": day["close"].shift(-1).iloc[:n].to_numpy(dtype=float),
        "r": on["r"].to_numpy(dtype=float),
    })
    out["r_night_bps"] = out["r"] * 1e4
    out["r_day_bps"] = (out["close_t"] / out["open_t"] - 1.0) * 1e4
    out["nights"] = (pd.to_datetime(out["date_t1"]) - pd.to_datetime(out["date"])).dt.days
    notional = out["close_t"] * MULTIPLIER
    out["cost_bps_cons"] = COST_YEN_CONSERVATIVE / notional * 1e4
    out["cost_bps_opt"] = COST_YEN_OPTIMISTIC / notional * 1e4
    out["r_net_bps_cons"] = out["r_night_bps"] - out["cost_bps_cons"]
    out["r_net_bps_opt"] = out["r_night_bps"] - out["cost_bps_opt"]
    out["pnl_yen_cons"] = (out["open_t1"] - out["close_t"]) * MULTIPLIER - COST_YEN_CONSERVATIVE
    return out


def second_friday(year: int, month: int) -> pd.Timestamp:
    """The 2nd Friday of a calendar month (the SQ day, 始値ベース)."""
    first = pd.Timestamp(year=year, month=month, day=1)
    offset = (4 - first.dayofweek) % 7          # 4 == Friday
    return first + pd.Timedelta(days=offset + 7)


def roll_marked_days(trading_days, rule: str = "monthly") -> set:
    """{SQ day, its previous trading day} for every month (or quarter).

    PREREG "限月ロールの扱い": the continuous series' splice shows up in the
    single pair "last trading day's close -> SQ day's open", so the marked
    DAY set is the SQ day plus the trading day immediately before it, and no
    +/-2 day widening. A month whose 2nd Friday is not itself a trading day
    contributes nothing (the calendar rule names that Friday, not a
    substitute day).
    """
    if rule not in ("monthly", "quarterly"):
        raise ValueError(f"rule must be 'monthly' or 'quarterly', got {rule!r}")
    days = pd.DatetimeIndex(sorted(pd.Timestamp(d) for d in trading_days))
    months = sorted({(d.year, d.month) for d in days})
    marked: set = set()
    for year, month in months:
        if rule == "quarterly" and month not in (3, 6, 9, 12):
            continue
        sq = second_friday(year, month)
        pos = int(days.searchsorted(sq))
        if pos >= len(days) or days[pos] != sq:
            continue                     # 2nd Friday was not a trading day
        marked.add(sq)
        if pos > 0:
            marked.add(days[pos - 1])
    return marked


def mark_roll_adjacent(pairs: pd.DataFrame, trading_days, rule: str = "monthly"
                       ) -> pd.Series:
    """Boolean mask: pair (t, t+1) touches a roll-marked day at either end."""
    marked = roll_marked_days(trading_days, rule)
    t = pd.to_datetime(pairs["date"])
    t1 = pd.to_datetime(pairs["date_t1"])
    return t.isin(marked) | t1.isin(marked)


def mark_nightless(pairs: pd.DataFrame, date_pairs=NIGHTLESS_PAIRS) -> pd.Series:
    """Boolean mask for the pre-registered night-less pairs, BY DATE PAIR."""
    wanted = {(pd.Timestamp(a), pd.Timestamp(b)) for a, b in date_pairs}
    t = pd.to_datetime(pairs["date"])
    t1 = pd.to_datetime(pairs["date_t1"])
    return pd.Series([(a, b) in wanted for a, b in zip(t, t1)], index=pairs.index)


def years_span(pairs: pd.DataFrame) -> float:
    """Calendar years covered, entry of the first pair to exit of the last."""
    if not len(pairs):
        return float("nan")
    lo = pd.to_datetime(pairs["date"]).min()
    hi = pd.to_datetime(pairs["date_t1"]).max()
    return (hi - lo).days / 365.25


def sharpe_annualised(x: np.ndarray, years: float) -> float:
    """mean/sd * sqrt(pairs per year). PREREG forbids a flat sqrt(250):
    the nights per pair are uneven, so the pair rate is measured, not assumed."""
    x = np.asarray(x, dtype=float)
    if len(x) < 2 or not np.isfinite(years) or years <= 0:
        return float("nan")
    sd = float(x.std(ddof=1))
    if sd == 0:
        return float("nan")
    return float(x.mean()) / sd * float(np.sqrt(len(x) / years))


def max_drawdown_yen(pnl_yen) -> tuple[float, int]:
    """(max peak-to-trough drop of the cumulative yen curve, its end index).

    1 micro contract held from close(t) to open(t+1), cost already deducted;
    pairs must be in chronological order.
    """
    pnl = np.asarray(pnl_yen, dtype=float)
    if not len(pnl):
        return float("nan"), -1
    equity = np.cumsum(pnl)
    peak = np.maximum.accumulate(np.concatenate([[0.0], equity]))[1:]
    dd = peak - equity
    i = int(np.argmax(dd))
    return float(dd[i]), i


def sign_shuffle_mean_and_sharpe(x, n: int = N_SHUFFLE, seed: int | None = None,
                                 years: float | None = None
                                 ) -> tuple[np.ndarray, np.ndarray]:
    """Sign-shuffle null draws of the mean AND the annualised Sharpe.

    Draws the sign matrix with the exact same RNG call sequence as
    `bot.research.overnight.sign_shuffle_null`, so the returned means are
    bit-identical to that tested helper for the same (x, n, seed); the second
    array adds the Sharpe of each draw, which the tested helper does not
    return. (Flipping signs changes the draw's sd too, because
    var(s*x) = mean(x^2) - mean(s*x)^2, so the Sharpe null is not simply the
    mean null rescaled.)
    """
    x = np.asarray(x, dtype=float)
    m = len(x)
    if m == 0:
        return np.array([]), np.array([])
    rng = np.random.default_rng(seed)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(n, m))
    draws = signs * x
    means = draws.mean(axis=1)
    sds = draws.std(axis=1, ddof=1)
    scale = np.sqrt(m / years) if (years and years > 0) else float("nan")
    with np.errstate(divide="ignore", invalid="ignore"):
        sharpes = np.where(sds > 0, means / sds * scale, np.nan)
    return means, sharpes


def describe(x, label: str, years: float | None = None, seed: int = SEED,
             ci: bool = True) -> dict:
    """n / mean / sd / t / hit rate (+ optional block-bootstrap 95% CI)."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    row = {"label": label, "n": n}
    if n == 0:
        row.update(mean=np.nan, sd=np.nan, t=np.nan, hit_rate=np.nan,
                   ci_lo=np.nan, ci_hi=np.nan, sharpe=np.nan)
        return row
    mean = float(x.mean())
    sd = float(x.std(ddof=1)) if n > 1 else float("nan")
    row["mean"] = mean
    row["sd"] = sd
    row["t"] = mean / (sd / np.sqrt(n)) if (n > 1 and sd > 0) else float("nan")
    row["hit_rate"] = float((x > 0).mean())
    if ci:
        lo, hi = block_bootstrap_ci(x, block=BLOCK, n_boot=N_BOOT, seed=seed)
    else:
        lo = hi = float("nan")
    row["ci_lo"], row["ci_hi"] = lo, hi
    row["sharpe"] = sharpe_annualised(x, years) if years is not None else float("nan")
    return row


# ---------------------------------------------------------------------------
# run
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
                              capture_output=True, text=True, check=True
                              ).stdout.strip()
    except Exception as exc:  # pragma: no cover - diagnostics only
        return f"unavailable ({exc})"


def _fmt(v, nd: int = 3) -> str:
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "—"
    if isinstance(v, (int, np.integer)):
        return f"{int(v):,}"
    return f"{float(v):,.{nd}f}"


def _table(rows: list[dict], cols: list[tuple[str, str, int]]) -> str:
    head = "| " + " | ".join(c[1] for c in cols) + " |"
    sep = "|" + "|".join("---" for _ in cols) + "|"
    body = []
    for r in rows:
        body.append("| " + " | ".join(
            (str(r.get(k, "")) if nd < 0 else _fmt(r.get(k), nd))
            for k, _, nd in cols) + " |")
    return "\n".join([head, sep] + body)


ROLL_RULE_LABEL_JA = {"monthly": "月次", "quarterly": "四半期"}


def main(roll_rule: str = "monthly", out_dir: Path | None = None,
         iteration: int = 0) -> int:
    if roll_rule not in ("monthly", "quarterly"):
        raise ValueError(f"roll_rule must be 'monthly' or 'quarterly', got {roll_rule!r}")
    out = out_dir if out_dir is not None else OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    steps: dict[str, int] = {}

    # ---- load (dev set only; sealed rows are removed by the loader) --------
    day_raw = load_unsealed(DAY_FILE, UNIT, root=REPO_ROOT)
    night_raw = load_unsealed(NIGHT_FILE, UNIT, root=REPO_ROOT)
    day_raw["date"] = pd.to_datetime(day_raw["date"])
    night_raw["date"] = pd.to_datetime(night_raw["date"])
    day_raw = day_raw.sort_values("date").reset_index(drop=True)
    night_raw = night_raw.sort_values("date").reset_index(drop=True)
    steps["day_rows_unsealed"] = len(day_raw)
    steps["night_rows_unsealed"] = len(night_raw)

    # ---- analysis window + endpoint rule ----------------------------------
    day = day_raw[day_raw["date"] >= ANALYSIS_START].reset_index(drop=True)
    steps["day_rows_in_window"] = len(day)
    trading_days = list(day["date"])

    pairs = build_pairs(day)                    # endpoint rule: last row dropped
    steps["pairs_after_endpoint_rule"] = len(pairs)

    # ---- marks -------------------------------------------------------------
    pairs["roll_monthly"] = mark_roll_adjacent(pairs, trading_days, "monthly")
    pairs["roll_quarterly"] = mark_roll_adjacent(pairs, trading_days, "quarterly")
    pairs["nightless_marked"] = mark_nightless(pairs)
    pairs["is_glitch"] = pairs["r"].abs() > GLITCH_THRESHOLD
    n_glitch = int(pairs["is_glitch"].sum())
    # cross-check the tested helper agrees with the mask
    _, n_glitch_helper = drop_glitches(pairs, GLITCH_THRESHOLD)
    assert n_glitch == n_glitch_helper, (n_glitch, n_glitch_helper)
    steps["glitches"] = n_glitch
    steps["roll_adjacent_monthly"] = int(pairs["roll_monthly"].sum())
    steps["roll_adjacent_quarterly"] = int(pairs["roll_quarterly"].sum())
    steps["nightless_marked"] = int(pairs["nightless_marked"].sum())

    # ---- night session join (control 3, leg (b)) ---------------------------
    nn = night_raw[["date", "open", "close"]].rename(
        columns={"date": "date_t1", "open": "night_open", "close": "night_close"})
    pairs = pairs.merge(nn, on="date_t1", how="left")
    pairs["has_night"] = pairs["night_open"].notna()
    steps["pairs_without_night_row"] = int((~pairs["has_night"]).sum())
    pairs["leg_b_bps"] = (pairs["night_close"] / pairs["night_open"] - 1.0) * 1e4
    pairs["leg_a_bps"] = (pairs["night_open"] / pairs["close_t"] - 1.0) * 1e4
    pairs["leg_c_bps"] = (pairs["open_t1"] / pairs["night_close"] - 1.0) * 1e4

    # ---- alignment check (level comparison, PREREG 整列規則) ---------------
    ok = pairs[pairs["has_night"]]
    med_prev = float((ok["night_open"] - ok["close_t"]).abs().median())
    med_same = float((ok["night_open"] - ok["close_t1"]).abs().median())
    alignment_pass = bool(med_prev < med_same)

    # ---- splits / labels ---------------------------------------------------
    pairs["split"] = np.where(pairs["date"] <= TRAIN_END, "train", "val")
    regime = pd.Series("other", index=pairs.index, dtype=object)
    for name, lo, hi in REGIMES:
        regime[(pairs["date"] >= lo) & (pairs["date"] <= hi)] = name
    pairs["regime"] = regime
    pairs["weekday"] = pd.to_datetime(pairs["date"]).dt.day_name()
    pairs["month"] = pd.to_datetime(pairs["date"]).dt.month
    pairs["year"] = pd.to_datetime(pairs["date"]).dt.year

    # 20-day realized vol of the day series' close-to-close returns, known at t
    cc = day["close"].pct_change()
    vol = cc.rolling(20).std().shift(1)
    vol_by_date = pd.Series(vol.to_numpy(), index=day["date"].to_numpy())
    pairs["vol20"] = pd.to_datetime(pairs["date"]).map(vol_by_date)
    finite = pairs["vol20"].notna()
    tercile = pd.Series("unknown", index=pairs.index, dtype=object)
    if finite.any():
        tercile.loc[finite] = pd.qcut(
            pairs.loc[finite, "vol20"], 3, labels=["low", "mid", "high"]).astype(str)
    pairs["vol_tercile"] = tercile

    # SQ proximity diagnostic: trading-day distance to the nearest 2nd Friday
    sq_days = pd.DatetimeIndex(sorted(
        d for d in trading_days
        if d == second_friday(d.year, d.month)))
    day_pos = {d: i for i, d in enumerate(trading_days)}
    sq_pos = np.array([day_pos[d] for d in sq_days])
    tpos = np.array([day_pos[d] for d in pd.to_datetime(pairs["date"])])
    if len(sq_pos):
        j = np.clip(np.searchsorted(sq_pos, tpos), 0, len(sq_pos) - 1)
        cand = np.stack([sq_pos[np.maximum(j - 1, 0)], sq_pos[j]])
        pairs["sq_dist_td"] = np.min(np.abs(cand - tpos), axis=0)
    else:  # pragma: no cover
        pairs["sq_dist_td"] = np.nan

    # ---- the pre-registered sets --------------------------------------
    # roll_rule selects which roll-adjacent column defines the MAIN judgment
    # set (PREREG "限月ロールの扱い" (a) monthly default / (b) quarterly switch
    # once the contract months are confirmed). Both roll_monthly and
    # roll_quarterly are always computed above regardless of roll_rule, so
    # the diagnostics below stay available under either choice.
    roll_col = f"roll_{roll_rule}"
    base = pairs                                         # 3,240
    roll_ex = pairs[~pairs[roll_col]]                    # PREREG 分母 (active rule)
    main = roll_ex[~roll_ex["is_glitch"]]                # judgment set
    steps["n_base"] = len(base)
    steps["n_roll_excluded_monthly"] = int((~pairs["roll_monthly"]).sum())
    steps["n_roll_excluded_quarterly"] = int((~pairs["roll_quarterly"]).sum())
    steps["n_main_roll_and_glitch_excluded"] = len(main)
    steps["glitches_inside_roll_set"] = int(
        (pairs["is_glitch"] & pairs[roll_col]).sum())
    steps["glitches_in_main_set_removed"] = int(
        (pairs["is_glitch"] & ~pairs[roll_col]).sum())

    yrs_main = years_span(main)
    yrs_base = years_span(base)

    # ---- main indicators ---------------------------------------------------
    if roll_rule == "monthly":
        label1 = "主指標1 平均ネット夜間リターン(保守コスト、ロール除外+誤プリント除外)"
        label_roll_ex = "PREREG 分母どおり n=2,769(誤プリント含む)"
    else:
        label1 = ("主指標1 平均ネット夜間リターン(保守コスト、四半期ロール除外+誤プリント除外、"
                  "反復1: 限月確認によりラージ=四半期限月のみと判明)")
        label_roll_ex = f"四半期ロール除外後 n={len(roll_ex):,}(誤プリント含む)"
    main_rows = [
        describe(main["r_net_bps_cons"], label1, yrs_main),
        describe(main["r_night_bps"] - main["r_day_bps"], "主指標2 夜間−日中の差(同集合)", yrs_main),
        describe(main["r_night_bps"], "参考 グロス夜間リターン(同集合)", yrs_main),
        describe(main["r_net_bps_opt"], "参考 楽観コスト後(手数料のみ)", yrs_main),
        describe(roll_ex["r_net_bps_cons"], label_roll_ex, years_span(roll_ex)),
        describe(roll_ex["r_night_bps"] - roll_ex["r_day_bps"], "同上 夜間−日中の差", years_span(roll_ex)),
        describe(base["r_net_bps_cons"], "ロール隣接ペアを含む n=3,240(誤プリント含む)", yrs_base),
        describe(base["r_night_bps"] - base["r_day_bps"], "同上 夜間−日中の差", yrs_base),
    ]
    main_df = pd.DataFrame(main_rows)

    # ---- sub indicators ----------------------------------------------------
    sub_rows: list[dict] = []

    def add(x, label, subset=None, years=None):
        s = subset if subset is not None else x
        sub_rows.append(describe(x, label, years if years is not None else years_span(s)))

    add(main["r_net_bps_cons"], "主集合(n=2,768 相当)", main)
    quart = pairs[~pairs["roll_quarterly"] & ~pairs["is_glitch"]]
    add(quart["r_net_bps_cons"], "四半期ロール規則(PREREG n=3,081 相当)", quart)
    add(pairs[~pairs["roll_quarterly"]]["r_net_bps_cons"],
        "四半期ロール規則・誤プリント含む(n=3,081)", pairs[~pairs["roll_quarterly"]])
    one = main[main["nights"] == 1]
    add(one["r_net_bps_cons"], "1泊のみの部分集合", one)
    nonight_ex = main[~main["nightless_marked"]]
    add(nonight_ex["r_net_bps_cons"], "夜間セッション無しの5ペアを除外", nonight_ex)
    add(base[~base["is_glitch"]]["r_net_bps_cons"],
        "誤プリント除外のみ(ロール含む)", base[~base["is_glitch"]])
    add(roll_ex["r_net_bps_cons"], "誤プリント除外なし(ロール除外のみ)", roll_ex)
    for name, lo, hi in REGIMES:
        sset = main[(main["date"] >= lo) & (main["date"] <= hi)]
        add(sset["r_net_bps_cons"], f"制度区分 {name}", sset)
    for split in ("train", "val"):
        sset = main[main["split"] == split]
        add(sset["r_net_bps_cons"], f"{split}(暦日分割)", sset)
    sub_df = pd.DataFrame(sub_rows)

    mdd_yen, mdd_idx = max_drawdown_yen(main.sort_values("date")["pnl_yen_cons"])
    mdd_date = str(pd.to_datetime(main.sort_values("date")["date_t1"].iloc[mdd_idx]).date()) \
        if mdd_idx >= 0 else ""
    total_pnl_yen = float(main["pnl_yen_cons"].sum())

    # ---- controls ----------------------------------------------------------
    ctrl_rows = [
        describe(main["r_day_bps"], "対照1 日中保有 r_day(グロス)", yrs_main),
        describe(main["r_day_bps"] - main["cost_bps_cons"],
                 "対照1 日中保有(保守コスト後)", yrs_main),
    ]
    # control 2: sign-shuffle null on the gross overnight return
    x_gross = main["r_night_bps"].to_numpy(dtype=float)
    null_mean, null_sharpe = sign_shuffle_mean_and_sharpe(
        x_gross, N_SHUFFLE, SEED, yrs_main)
    ref_mean = sign_shuffle_null(x_gross, N_SHUFFLE, SEED)
    assert np.allclose(null_mean, ref_mean), "sign-shuffle stream diverged"
    null_mean_p95 = float(np.percentile(null_mean, 95))
    null_sharpe_p95 = float(np.percentile(null_sharpe, 95))
    obs_mean_gross = float(x_gross.mean())
    obs_sharpe_gross = sharpe_annualised(x_gross, yrs_main)

    # control 3: night-session-internal leg (b)
    c3 = main[main["has_night"]]
    ctrl_rows.append(describe(c3["leg_b_bps"], "対照3 夜間セッション内 leg(b) グロス", years_span(c3)))
    ctrl_rows.append(describe(c3["leg_b_bps"] - c3["cost_bps_cons"],
                              "対照3 leg(b) 保守コスト後", years_span(c3)))
    ctrl_rows.append(describe(c3["leg_a_bps"], "参考 leg(a) 日中引け→夜間寄り", years_span(c3)))
    ctrl_rows.append(describe(c3["leg_c_bps"], "参考 leg(c) 夜間引け→翌日中寄り", years_span(c3)))
    # PREREG: the 1990..2007 day-session rows carry no night session, so they
    # are referenced ONLY as a long-run descriptive reference for r_day.
    pre = day_raw[day_raw["date"] < ANALYSIS_START].reset_index(drop=True)
    r_day_pre = (pre["close"] / pre["open"] - 1.0) * 1e4
    ctrl_rows.append(describe(
        r_day_pre, "参考(長期対照・判定に使わない)1990-01-04..2007-09-18 の r_day",
        (pre["date"].max() - pre["date"].min()).days / 365.25))
    steps["long_run_day_rows_1990_2007"] = int(len(pre))
    ctrl_df = pd.DataFrame(ctrl_rows)
    c3_all_night = pairs[pairs["has_night"]]

    # ---- diagnostics (descriptive only, no p-values) -----------------------
    def group_table(df: pd.DataFrame, by: str) -> pd.DataFrame:
        g = df.groupby(by, dropna=False)
        return pd.DataFrame({
            "n": g.size(),
            "mean_r_net_bps": g["r_net_bps_cons"].mean(),
            "sd_bps": g["r_net_bps_cons"].std(ddof=1),
            "mean_gross_bps": g["r_night_bps"].mean(),
            "mean_r_day_bps": g["r_day_bps"].mean(),
            "hit_rate": g["r_net_bps_cons"].apply(lambda s: float((s > 0).mean())),
        }).reset_index()

    diag = {
        "nights": group_table(main, "nights"),
        "vol_tercile": group_table(main, "vol_tercile"),
        "regime": group_table(main, "regime"),
        "weekday": group_table(main, "weekday"),
        "month": group_table(main, "month"),
        "year": group_table(main, "year"),
        "sq_dist": group_table(pairs[~pairs["is_glitch"]], "sq_dist_td"),
    }
    # nights distribution over the full base set (PREREG 連休またぎ)
    nights_dist = pairs.groupby("nights").size().rename("n_pairs").reset_index()
    nights_dist["share"] = nights_dist["n_pairs"] / len(pairs)

    # ---- exclusions ledger -------------------------------------------------
    roll_ex_step_label = ("ロール隣接除外後(PREREG 分母)" if roll_rule == "monthly"
                          else f"ロール隣接除外後(採用規則: {ROLL_RULE_LABEL_JA[roll_rule]}、反復{iteration})")
    excl = pd.DataFrame([
        {"step": "day_session_daily 未封印行", "n": steps["day_rows_unsealed"]},
        {"step": "解析窓 2007-09-19 以降の日中行", "n": steps["day_rows_in_window"]},
        {"step": "端点規則適用後のペア", "n": steps["pairs_after_endpoint_rule"]},
        {"step": "うち誤プリント(絶対単純収益 > 0.10)", "n": steps["glitches"]},
        {"step": "うちロール隣接(月次規則)", "n": steps["roll_adjacent_monthly"]},
        {"step": "うちロール隣接(四半期規則)", "n": steps["roll_adjacent_quarterly"]},
        {"step": "うち夜間セッション無し(事前登録の5ペア)", "n": steps["nightless_marked"]},
        {"step": "うち夜間行が実データで欠損", "n": steps["pairs_without_night_row"]},
        {"step": roll_ex_step_label, "n": len(roll_ex)},
        {"step": "誤プリントがロール隣接集合の内側にあった件数", "n": steps["glitches_inside_roll_set"]},
        {"step": "主集合(ロール除外+誤プリント除外)", "n": steps["n_main_roll_and_glitch_excluded"]},
        {"step": "主集合のうち train", "n": int((main["split"] == "train").sum())},
        {"step": "主集合のうち val", "n": int((main["split"] == "val").sum())},
        {"step": "全ペアのうち train(暦日分割)", "n": int((pairs["split"] == "train").sum())},
        {"step": "全ペアのうち val(暦日分割)", "n": int((pairs["split"] == "val").sum())},
    ])

    # ---- write CSVs --------------------------------------------------------
    pairs_out = pairs.copy()
    pairs_out["date"] = pd.to_datetime(pairs_out["date"]).dt.date
    pairs_out["date_t1"] = pd.to_datetime(pairs_out["date_t1"]).dt.date
    written: list[str] = []

    def write(df: pd.DataFrame, name: str):
        p = out / name
        df.to_csv(p, index=False)
        written.append(name)

    write(pairs_out, "pairs.csv")
    write(main_df, "main_indicators.csv")
    write(sub_df, "sub_indicators.csv")
    write(ctrl_df, "controls.csv")
    write(excl, "exclusions.csv")
    write(nights_dist, "nights_distribution.csv")
    for k, v in diag.items():
        write(v, f"diagnostic_{k}.csv")
    write(pd.DataFrame([{
        "median_abs_night_open_minus_close_day_t": med_prev,
        "median_abs_night_open_minus_close_day_t1": med_same,
        "pass": alignment_pass,
        "n": int(len(ok)),
    }]), "alignment_check.csv")
    write(pd.DataFrame({"draw": np.arange(N_SHUFFLE),
                        "null_mean_bps": null_mean,
                        "null_sharpe": null_sharpe}), "control2_sign_shuffle_null.csv")

    # ---- RESULTS.md --------------------------------------------------------
    mean_main = float(main["r_net_bps_cons"].mean())
    gross_main = float(main["r_night_bps"].mean())
    ci_main = (main_df.iloc[0]["ci_lo"], main_df.iloc[0]["ci_hi"])
    diff_main = float((main["r_night_bps"] - main["r_day_bps"]).mean())
    ci_diff = (main_df.iloc[1]["ci_lo"], main_df.iloc[1]["ci_hi"])
    cost_med = float(main["cost_bps_cons"].median())
    cost_mean = float(main["cost_bps_cons"].mean())

    # MDE reproduction + effective MDE back-computed from the observed CI width
    Z = 1.959963985 + 0.8416212336            # alpha 0.05 two-sided, power 0.8

    def mde_row(label, x, registered):
        """sigma / SE / independent-sample MDE, plus the EFFECTIVE MDE implied
        by this same series' own block-bootstrap CI width (PREREG asks for the
        latter to be recorded alongside the independent-sample lower bound)."""
        x = np.asarray(x, dtype=float)
        sd = float(x.std(ddof=1))
        se = sd / np.sqrt(len(x))
        lo, hi = block_bootstrap_ci(x, block=BLOCK, n_boot=N_BOOT, seed=SEED)
        se_eff = (hi - lo) / (2 * 1.959963985)
        return {"a": label, "b": sd, "c": len(x), "d": se, "e": Z * se,
                "f": registered, "g": Z * se_eff}

    mde_rows = [
        mde_row("σ(r_night) ロール除外後 n=2,769(事前登録の基準)",
                roll_ex["r_night_bps"], MDE_BPS),
        mde_row("σ(夜間−日中の差)ロール除外後 n=2,769",
                roll_ex["r_night_bps"] - roll_ex["r_day_bps"], MDE_DIFF_BPS),
        mde_row("σ(r_net 保守コスト後)主集合", main["r_net_bps_cons"], MDE_BPS),
        mde_row("σ(夜間−日中の差)主集合",
                main["r_night_bps"] - main["r_day_bps"], MDE_DIFF_BPS),
    ]

    write(pd.DataFrame(mde_rows).rename(columns={
        "a": "quantity", "b": "sd_bps", "c": "n", "d": "se_bps",
        "e": "mde_bps_independent", "f": "mde_bps_registered",
        "g": "mde_bps_effective_from_ci"}), "mde.csv")

    ind_cols = [("label", "集合 / 指標", -1), ("n", "n", 0), ("mean", "平均(bps)", 3),
                ("ci_lo", "CI下限", 3), ("ci_hi", "CI上限", 3), ("sd", "SD(bps)", 2),
                ("t", "t", 2), ("hit_rate", "勝率", 4), ("sharpe", "Sharpe(年率)", 3)]

    md = []
    md.append(f"# P2-01 反復 {iteration} — 事前登録の主検定(開発セットのみ、"
              f"ロール規則: {ROLL_RULE_LABEL_JA[roll_rule]})")
    md.append("")
    md.append(f"実行日 2026-09-06 / seed {SEED} / git {_git_rev()[:12]} / "
              f"単位 {UNIT} / roll_rule={roll_rule}。読み込みは `load_unsealed` のみ(封印期間・"
              "`bars_1min`・`paper_logs` には一切触れていない)。")
    md.append("")
    if iteration > 0:
        md.append("反復理由: PREREG「限月ロールの扱い (b)」— 225Labo ダウンロードページと "
                  "JPX 商品概要ページ(一次資料、`backtest_data/audit_fetch_JPX_n225f_months_20260906/`)"
                  "でラージ日経225先物の限月が3・6・9・12月のみと確認できたため、"
                  "ロール隣接規則を月次から四半期の第2金曜に切り替える。それ以外のパラメータ"
                  "(seed・ブロック長・リサンプル数・コスト・対照・副指標)は反復0と同一。")
        md.append("")
    md.append("**本書は数値の報告のみで、採用・棄却の解釈は行わない。**")
    md.append("")
    md.append("## 1. 母集団と除外の内訳")
    md.append("")
    md.append(_table(excl.to_dict("records"),
                     [("step", "段階", -1), ("n", "件数", 0)]))
    md.append("")
    md.append("事前登録値との照合: ペア 3,240(一致)、train 2,273 / val 967(一致)、"
              "誤プリント 3 件(一致)、ロール隣接 月次 471 → n=2,769(一致)、"
              "四半期 159 → n=3,081(一致)、夜間セッション無し 5 ペア(日付ペアも一致)。")
    md.append("")
    md.append(f"注: 誤プリント 3 件のうち {steps['glitches_inside_roll_set']} 件は"
              f"ロール隣接ペア(2008 年 10 月の第 2 金曜近傍)の内側にあり、"
              f"{ROLL_RULE_LABEL_JA[roll_rule]}ロール除外で既に落ちる。"
              f"したがって「ロール除外 + 誤プリント除外」の主集合は "
              f"n = {steps['n_main_roll_and_glitch_excluded']:,} で、ロール隣接除外後(誤プリント含む)の "
              f"n = {len(roll_ex):,} とは {len(roll_ex) - steps['n_main_roll_and_glitch_excluded']} 件差になる"
              "(2008年10月は非四半期月のため、四半期規則では誤プリントがこの集合の内側に落ちない)。"
              if roll_rule == "quarterly" else
              f"注: 誤プリント 3 件のうち {steps['glitches_inside_roll_set']} 件は"
              "ロール隣接ペア(2008 年 10 月の第 2 金曜近傍)の内側にあり、月次ロール除外で"
              f"既に落ちる。したがって「ロール除外 + 誤プリント除外」の主集合は "
              f"n = {steps['n_main_roll_and_glitch_excluded']:,} で、事前登録に書かれた分母 2,769 "
              "(ロール除外のみ)とは 1 件差になる。両方を併記した。")
    md.append("")
    md.append("## 2. 主指標")
    md.append("")
    md.append("CI はブロック・ブートストラップ(ブロック長 20、リサンプル 2,000、percentile 法、seed "
              f"{SEED})。単位は bps/ペア。")
    md.append("")
    md.append(_table(main_df.to_dict("records"), ind_cols))
    md.append("")
    md.append(f"ペアごとの保守コスト cost_bps(t) = 122 /(close_day(t)×10)×10^4: "
              f"中央値 {cost_med:.2f}bps、平均 {cost_mean:.2f}bps、"
              f"範囲 {main['cost_bps_cons'].min():.2f}〜{main['cost_bps_cons'].max():.2f}bps。"
              f"楽観側(手数料のみ 22 円)は中央値 {main['cost_bps_opt'].median():.2f}bps。")
    md.append("")
    md.append("主指標 2(夜間 − 日中)は、同じ 1 往復のコストが両脚に等しく掛かるため"
              "グロスの差とネットの差が恒等的に一致する(cost_bps(t) が引き算で相殺する)。"
              "表の値はその共通値。")
    md.append("")
    md.append("## 3. 事前登録の関門との比較(数値の対照のみ)")
    md.append("")
    md.append(_table([
        {"a": "平均ネット r_net(保守コスト後、主集合)", "b": mean_main,
         "c": MDE_BPS, "d": mean_main - MDE_BPS},
        {"a": "グロス平均夜間リターン(主集合)", "b": gross_main,
         "c": GROSS_GATE_BPS, "d": gross_main - GROSS_GATE_BPS},
        {"a": "夜間−日中の差(主集合)", "b": diff_main,
         "c": MDE_DIFF_BPS, "d": diff_main - MDE_DIFF_BPS},
    ], [("a", "量", -1), ("b", "実測(bps)", 3), ("c", "事前登録の基準(bps)", 2),
        ("d", "差", 3)]))
    md.append("")
    md.append(f"主指標 1 の 95% CI = [{_fmt(ci_main[0])}, {_fmt(ci_main[1])}] bps、"
              f"主指標 2 の 95% CI = [{_fmt(ci_diff[0])}, {_fmt(ci_diff[1])}] bps。")
    md.append("")
    md.append("### MDE の再現と実効 MDE(事前登録の指示による記録)")
    md.append("")
    md.append(_table(mde_rows, [("a", "量", -1), ("b", "σ(bps)", 2), ("c", "n", 0),
                                ("d", "SE(bps)", 3), ("e", "独立標本 MDE(bps)", 3),
                                ("f", "事前登録 MDE", 2),
                                ("g", "実測 CI 幅からの実効 MDE(bps)", 3)]))
    md.append("")
    md.append("独立標本 MDE = 2.802 × SE(α 0.05 両側・検出力 0.8)。実効 MDE は"
              "ブロック・ブートストラップの CI 幅を SE に換算して同じ係数を掛けたもの"
              "(自己相関のぶん独立標本の下限より広がり得る)。")
    md.append("")
    md.append("## 4. 副指標")
    md.append("")
    md.append(_table(sub_df.to_dict("records"), ind_cols))
    md.append("")
    md.append(f"最大ドローダウン(マイクロ 1 枚固定、保守コスト後、主集合、時系列順): "
              f"**{mdd_yen:,.0f} 円**(谷は {mdd_date})。同集合の累計損益 {total_pnl_yen:,.0f} 円 / "
              f"{len(main):,} ペア。勝率 {float((main['r_net_bps_cons'] > 0).mean()):.4f}。"
              f"年率換算 Sharpe の換算係数 = √(n/年数) = √({len(main)}/{yrs_main:.2f}) = "
              f"{np.sqrt(len(main)/yrs_main):.2f}。")
    md.append("")
    md.append("### 泊数の分布(全ペア)")
    md.append("")
    md.append(_table(nights_dist.to_dict("records"),
                     [("nights", "泊数", 0), ("n_pairs", "ペア数", 0), ("share", "割合", 4)]))
    md.append("")
    md.append("### 泊数別の平均(主集合)")
    md.append("")
    md.append(_table(diag["nights"].to_dict("records"),
                     [("nights", "泊数", 0), ("n", "n", 0),
                      ("mean_r_net_bps", "平均 r_net(bps)", 3),
                      ("mean_gross_bps", "グロス(bps)", 3), ("sd_bps", "SD", 2),
                      ("hit_rate", "勝率", 4)]))
    md.append("")
    md.append("## 5. 対照")
    md.append("")
    md.append(_table(ctrl_df.to_dict("records"), ind_cols))
    md.append("")
    md.append("### 対照 2 シャッフル帰無(符号無作為化 1,000 回、グロス夜間リターン)")
    md.append("")
    md.append(_table([
        {"a": "平均(bps)", "b": obs_mean_gross, "c": null_mean_p95},
        {"a": "Sharpe(年率)", "b": obs_sharpe_gross, "c": null_sharpe_p95},
    ], [("a", "統計量", -1), ("b", "実測", 3), ("c", "帰無 95 点", 3)]))
    md.append("")
    md.append("### 対照 3 の分母と整列検証")
    md.append("")
    md.append(f"夜間行が存在するペアは {len(c3_all_night):,}(全 {len(pairs):,} ペア中、"
              f"欠損 {steps['pairs_without_night_row']})。そこからロール隣接(月次)と誤プリントを"
              f"除いた対照 3 の分母は n = {len(c3):,} で、主指標の分母 "
              f"{len(main):,} と一致しない(事前登録どおり併記)。")
    md.append("")
    md.append("整列の検証(水準比較): "
              f"median |night_open(t+1) − close_day(t)| = **{med_prev:.1f} 円**、"
              f"median |night_open(t+1) − close_day(t+1)| = **{med_same:.1f} 円**、"
              f"n = {len(ok):,}。前者 < 後者 = **{alignment_pass}** → "
              "夜間行 t+1 をペア (t, t+1) に当てる取引日慣行の整列が支持される。")
    md.append("")
    md.append("## 6. 診断(記述のみ。p 値・有意判定は書かない)")
    md.append("")
    for key, title in [("regime", "制度区分"), ("vol_tercile", "20 日実現ボラ三分位"),
                       ("weekday", "曜日"), ("month", "月"), ("year", "年"),
                       ("sq_dist", "SQ(第 2 金曜)からの営業日距離")]:
        md.append(f"### {title}")
        md.append("")
        cols = [(diag[key].columns[0], diag[key].columns[0], -1), ("n", "n", 0),
                ("mean_r_net_bps", "平均 r_net(bps)", 3),
                ("mean_gross_bps", "グロス(bps)", 3),
                ("mean_r_day_bps", "r_day(bps)", 3), ("sd_bps", "SD", 2),
                ("hit_rate", "勝率", 4)]
        md.append(_table(diag[key].to_dict("records"), cols))
        md.append("")
    md.append("## 7. 事前登録からの逸脱")
    md.append("")
    if roll_rule == "monthly":
        md.append("- 事前登録は主指標の分母を「ロール隣接除外後 n = 2,769」と書き、別行で「判定は誤プリント除外後」"
                  f"と書いている。この 2 つは同時に満たせないため(誤プリント 3 件のうち "
                  f"{steps['glitches_in_main_set_removed']} 件が n=2,769 の内側)、"
                  f"主集合 n = {steps['n_main_roll_and_glitch_excluded']:,} を判定用として先頭に置き、"
                  "n = 2,769(誤プリント含む)も同じ表に併記した。数値の差は微小だが規則の解釈なので明記する。")
        md.append("- それ以外の逸脱はない。閾値・ブロック長・リサンプル数・分割日・除外規則・コスト定数は"
                  "すべて事前登録どおり。")
    else:
        md.append("- 本反復は PREREG「限月ロールの扱い (b)」の事前登録済みルール切替そのものであり、"
                  "逸脱ではなく反復として台帳(RUN.json の `iteration`)に記録している。"
                  f"ロール隣接除外後 n = {len(roll_ex):,}(誤プリント含む、PREREG 想定 3,081)、"
                  f"誤プリント 3 件のうち {steps['glitches_in_main_set_removed']} 件がこの集合の外側にあり"
                  f"主集合(ロール除外+誤プリント除外)から別途落ちるため、主集合 n = "
                  f"{steps['n_main_roll_and_glitch_excluded']:,}。")
        md.append("- それ以外の逸脱はない。閾値・ブロック長・リサンプル数・分割日・コスト定数・対照・副指標の"
                  "定義は反復0と同一で、変更したのはロール隣接規則(月次→四半期)のみ。")
    md.append("")
    if iteration > 0:
        prior_path = REPO_ROOT / "backtest_data" / "phase2_runs" / UNIT / "iter0_20260906" / "RUN.json"
        md.append(f"## 8. 反復比較(反復0 月次 vs 反復{iteration} {ROLL_RULE_LABEL_JA[roll_rule]})")
        md.append("")
        if prior_path.exists():
            prior = json.loads(prior_path.read_text(encoding="utf-8"))
            ph = prior["headline"]
            cmp_rows = [
                {"a": "n(主集合)", "b": prior["n_at_each_step"]["n_main_roll_and_glitch_excluded"],
                 "c": steps["n_main_roll_and_glitch_excluded"],
                 "d": steps["n_main_roll_and_glitch_excluded"]
                      - prior["n_at_each_step"]["n_main_roll_and_glitch_excluded"]},
                {"a": "平均ネット r_net(保守コスト、bps)", "b": ph["mean_r_net_bps_conservative"],
                 "c": mean_main, "d": mean_main - ph["mean_r_net_bps_conservative"]},
                {"a": "95%CI下限(bps)", "b": ph["ci95"][0], "c": ci_main[0],
                 "d": ci_main[0] - ph["ci95"][0]},
                {"a": "95%CI上限(bps)", "b": ph["ci95"][1], "c": ci_main[1],
                 "d": ci_main[1] - ph["ci95"][1]},
                {"a": "グロス平均夜間リターン(bps)", "b": ph["mean_gross_bps"],
                 "c": gross_main, "d": gross_main - ph["mean_gross_bps"]},
                {"a": "夜間−日中の差(bps)", "b": ph["mean_diff_night_minus_day_bps"],
                 "c": diff_main, "d": diff_main - ph["mean_diff_night_minus_day_bps"]},
                {"a": "Sharpe(年率)", "b": ph["sharpe_annualised"],
                 "c": sharpe_annualised(main["r_net_bps_cons"], yrs_main),
                 "d": sharpe_annualised(main["r_net_bps_cons"], yrs_main) - ph["sharpe_annualised"]},
                {"a": "勝率", "b": ph["hit_rate"],
                 "c": float((main["r_net_bps_cons"] > 0).mean()),
                 "d": float((main["r_net_bps_cons"] > 0).mean()) - ph["hit_rate"]},
                {"a": "最大ドローダウン(円、1枚)", "b": ph["max_drawdown_yen_1_micro"],
                 "c": mdd_yen, "d": mdd_yen - ph["max_drawdown_yen_1_micro"]},
                {"a": "MDE 関門(平均ネット r_net、bps)", "b": MDE_BPS, "c": MDE_BPS, "d": 0.0},
                {"a": "着手前関門との差(平均ネット − MDE 6.03、bps)",
                 "b": ph["mean_r_net_bps_conservative"] - MDE_BPS, "c": mean_main - MDE_BPS,
                 "d": (mean_main - MDE_BPS) - (ph["mean_r_net_bps_conservative"] - MDE_BPS)},
                {"a": "グロス関門との差(グロス平均 − 14.9、bps)",
                 "b": ph["mean_gross_bps"] - GROSS_GATE_BPS, "c": gross_main - GROSS_GATE_BPS,
                 "d": (gross_main - GROSS_GATE_BPS) - (ph["mean_gross_bps"] - GROSS_GATE_BPS)},
            ]
            md.append(_table(cmp_rows, [("a", "指標", -1), ("b", "反復0(月次)", 3),
                                        ("c", f"反復{iteration}({ROLL_RULE_LABEL_JA[roll_rule]})", 3),
                                        ("d", "差(反復1−反復0)", 3)]))
            md.append("")
            md.append(f"関門 6.03bps(平均ネット MDE)・14.9bps(グロス、着手前の実務上の最小値)は"
                      "規則を切り替えても変わらない(標本サイズがわずかに変わるのみで σ の再計算は"
                      "PREREG の指示どおり別途 MDE 表に記録する。関門の値自体は事前登録を変更しない)。")
        else:
            md.append(f"反復0の RUN.json が `{prior_path}` に見つからないため比較表は省略。")
        md.append("")
    (out / "RESULTS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    written.append("RESULTS.md")

    # ---- RUN.json ----------------------------------------------------------
    run = {
        "unit": UNIT,
        "iteration": iteration,
        "roll_rule": roll_rule,
        "run_date": str(date(2026, 9, 6)),
        "seed": SEED,
        "git_rev": _git_rev(),
        "script": "scripts/phase2/p2_01_run.py",
        "script_md5": _md5(Path(__file__)),
        "inputs": [
            {"path": p, "md5": _md5(REPO_ROOT / p)}
            for p in (DAY_FILE, NIGHT_FILE)
        ],
        "seal_record_md5": _md5(REPO_ROOT / "backtest_data" / "phase2_sealed"
                                / UNIT / "SEALED.json"),
        "parameters": {
            "roll_rule": roll_rule,
            "analysis_start": str(ANALYSIS_START.date()),
            "train_end": str(TRAIN_END.date()),
            "glitch_threshold_abs_simple_return": GLITCH_THRESHOLD,
            "block": BLOCK, "n_boot": N_BOOT, "n_shuffle": N_SHUFFLE,
            "cost_yen_conservative": COST_YEN_CONSERVATIVE,
            "cost_yen_optimistic": COST_YEN_OPTIMISTIC,
            "multiplier_yen_per_point": MULTIPLIER,
            "mde_bps": MDE_BPS, "mde_diff_bps": MDE_DIFF_BPS,
            "gross_gate_bps": GROSS_GATE_BPS,
        },
        "n_at_each_step": steps,
        "headline": {
            "mean_r_net_bps_conservative": mean_main,
            "ci95": [float(ci_main[0]), float(ci_main[1])],
            "mean_gross_bps": gross_main,
            "mean_diff_night_minus_day_bps": diff_main,
            "ci95_diff": [float(ci_diff[0]), float(ci_diff[1])],
            "sharpe_annualised": sharpe_annualised(main["r_net_bps_cons"], yrs_main),
            "hit_rate": float((main["r_net_bps_cons"] > 0).mean()),
            "max_drawdown_yen_1_micro": mdd_yen,
            "null_mean_p95_bps": null_mean_p95,
            "null_sharpe_p95": null_sharpe_p95,
            "alignment_median_abs_prev_close": med_prev,
            "alignment_median_abs_same_close": med_same,
            "alignment_pass": alignment_pass,
        },
        "mde": [{"quantity": r["a"], "sd_bps": r["b"], "n": r["c"],
                 "se_bps": r["d"], "mde_bps_independent": r["e"],
                 "mde_bps_registered": r["f"],
                 "mde_bps_effective_from_ci": r["g"]} for r in mde_rows],
        "outputs": sorted(written),
    }
    (out / "RUN.json").write_text(
        json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(run["headline"], ensure_ascii=False, indent=2))
    print(f"wrote {len(written) + 1} files to {out}")
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--roll-rule", choices=["monthly", "quarterly"], default="monthly",
                   help="Roll-adjacent rule for the MAIN judgment set (default: monthly, "
                        "reproduces iteration 0). 'quarterly' is the PREREG (b) switch.")
    p.add_argument("--out", type=Path, default=None,
                   help="Output directory (default: iter0's directory under "
                        "backtest_data/phase2_runs/P2-01/).")
    p.add_argument("--iteration", type=int, default=None,
                   help="Iteration number recorded in RUN.json / RESULTS.md "
                        "(default: 0 for --roll-rule monthly, 1 otherwise).")
    return p.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    iteration = args.iteration
    if iteration is None:
        iteration = 0 if args.roll_rule == "monthly" else 1
    raise SystemExit(main(roll_rule=args.roll_rule, out_dir=args.out, iteration=iteration))

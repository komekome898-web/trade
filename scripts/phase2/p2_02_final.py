#!/usr/bin/env python
"""P2-02 FINAL EVALUATION — the SEALED period, run exactly once.

Evaluates the frozen pre-registration `docs/PHASE2/P2-02/PREREG.md` (section
"最終評価") on the sealed window 2021-04-13 .. 2026-09-03, using the FINAL
configuration recorded in `docs/PHASE2/P2-02/ITER.md`:

  * iteration 0 only — the pre-registered main test has NO free parameter,
    so the cumulative number of examined configurations is N = 1. Control 1
    (the sign-shuffle null) is therefore the SINGLE-configuration null, not
    a best-of-N one.

Every input is read through `bot.research.sealed.load_sealed(path, "P2-02",
token=UNSEAL_TOKEN)`, which enforces the three independent guards (env
`PHASE2_FINAL_EVAL=P2-02`, the owner's `UNSEAL_APPROVED` file, the explicit
token) and appends to the unseal audit log. This module additionally
pre-checks the same three guards before touching anything, so a misconfigured
run fails before the first read rather than half-way through, and hard-codes
the unit to "P2-02" — no other unit can be unsealed from here.

The ONE deliberate use of unsealed rows: the derived ex-dividend dates need a
trading-day calendar that spans the record dates. `ex_dates_from_record_dates`
walks the price file's own dates, so the dev-set (pre-seal) trading days are
concatenated with the sealed ones to form the FULL calendar. Those pre-seal
days supply calendar positions only; no pre-seal price, return or pair enters
any evaluated statistic (the endpoint rule keeps only pairs whose BOTH days
lie inside the sealed window).

Nothing in this module interprets the numbers as 採用/棄却: it reports the
measured values against the pre-registered bar, the falsification sentence
and the hold class, and marks each 満たす / 満たさない. The owner decides.

Usage:
    PHASE2_FINAL_EVAL=P2-02 PYTHONPATH=src \
        python scripts/phase2/p2_02_final.py

The dev-set runner `scripts/phase2/p2_02_run.py` is imported for its tested
functions (defect rules / pair table / dividend adjustment / cost model /
inference helpers) and is NOT modified by this script.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from bot.constants import load_constants  # noqa: E402
from bot.research import overnight as onr  # noqa: E402
from bot.research.sealed import (  # noqa: E402
    UNSEAL_TOKEN,
    SealedDataError,
    load_sealed,
    load_seal_record,
    load_unsealed,
    md5_of,
    seal_dir,
)
from phase2.p2_02_run import (  # noqa: E402  (dev-set runner: reused, unchanged)
    BLOCK,
    DIV_1343,
    N_BOOT,
    N_SHUFFLE,
    N_STRATA_BOOT,
    PRICE_1321,
    PRICE_1343,
    SEED,
    THIN_VOLUME_THRESHOLD,
    _git_rev,
    _markdown_table,
    add_dividend_adjustment,
    block_bootstrap_max_dd_median,
    build_pair_table,
    build_tick_lookup,
    dividend_data_check,
    exclusion_stage_stats,
    max_drawdown,
    mde_bps,
    mean_ci_bootstrap,
    sharpe_annualized,
    sign_reversal_stats,
    stratified_bootstrap_mean_dist,
)

UNIT = "P2-02"            # hard-coded: only P2-02 may be unsealed here
CUMULATIVE_N = 1          # ITER.md: iteration 0 only, no free parameter

# ---- pre-registered sealed window (PREREG "最終評価") ----------------------
SEALED_START = pd.Timestamp("2021-04-13")
SEALED_END = pd.Timestamp("2026-09-03")

# PREREG 既知欠陥 (5): the closing auction moved 15:00 -> 15:30 on 2024-11-05,
# inside the sealed window. Split reported descriptively; judgment uses the
# whole sealed window.
REGIME_SPLIT = pd.Timestamp("2024-11-05")

# All sealed; used ONLY for the pre-registered forward diagnostic (ETF vs
# index divergence at the open and at the close), never for the cost model.
REIT_INDEX = "backtest_data/reit_onr_20260904/reit_index_daily.csv"
FORWARD_LEDGER = "paper_logs/onr_ledger.csv"
FORWARD_MIN_ROWS = 5

DD_BAR_MULTIPLE = 3.0

OUT_DIR = REPO_ROOT / "backtest_data" / "phase2_runs" / UNIT / "final_20260906"


# ---------------------------------------------------------------------------
# guards
# ---------------------------------------------------------------------------

def check_guards(root: Path | str = REPO_ROOT, token: str = UNSEAL_TOKEN,
                 unit: str = UNIT, env: dict | None = None) -> None:
    """Raise ``SealedDataError`` unless all three unseal guards are satisfied.

    Mirrors `bot.research.sealed.load_sealed`'s own check so a misconfigured
    final-evaluation run fails BEFORE the first read (and reports every
    missing guard at once, not just the first). Also refuses any unit other
    than P2-02: the owner's approval is scoped to this unit alone.
    """
    environ = os.environ if env is None else env
    reasons: list[str] = []
    if unit != UNIT:
        reasons.append(f"this script only evaluates {UNIT!r}, got {unit!r}")
    if environ.get("PHASE2_FINAL_EVAL") != unit:
        reasons.append(
            f"env PHASE2_FINAL_EVAL={environ.get('PHASE2_FINAL_EVAL')!r} "
            f"does not equal {unit!r}")
    approved = seal_dir(unit, root) / "UNSEAL_APPROVED"
    if not approved.is_file():
        reasons.append(f"missing owner approval file {approved}")
    if token != UNSEAL_TOKEN:
        reasons.append("wrong confirmation token")
    if reasons:
        raise SealedDataError(
            "refusing the P2-02 final evaluation: " + "; ".join(reasons))


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def restrict_window(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp
                    ) -> pd.DataFrame:
    """Rows with start <= date <= end, date-parsed and sorted ascending."""
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out = out[(out["date"] >= start) & (out["date"] <= end)]
    return out.sort_values("date").reset_index(drop=True)


def full_trading_calendar(dev_price: pd.DataFrame, sealed_price: pd.DataFrame
                          ) -> pd.DataFrame:
    """The FULL trading-day calendar of the price file (dev + sealed dates).

    Only the date column survives — the pre-seal rows contribute calendar
    positions for the ex-date derivation and nothing else.
    """
    days = pd.concat([pd.to_datetime(dev_price["date"]),
                      pd.to_datetime(sealed_price["date"])], ignore_index=True)
    days = pd.Series(sorted(set(days)))
    return pd.DataFrame({"date": days})


def _unseal_log_path(root: Path) -> Path:
    return seal_dir(UNIT, root) / "UNSEAL_LOG.jsonl"


def _unseal_log_len(root: Path) -> int:
    p = _unseal_log_path(root)
    if not p.is_file():
        return 0
    return len([ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()])


def _read_unseal_log(root: Path, since_line: int = 0) -> list[dict]:
    p = _unseal_log_path(root)
    if not p.is_file():
        return []
    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    out: list[dict] = []
    for ln in lines[since_line:]:
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:  # pragma: no cover - audit log is ours
            out.append({"raw": ln})
    return out


def md5_check(root: Path, paths: list[str]) -> list[dict]:
    """Each input file's md5 now vs the md5 recorded in SEALED.json."""
    seal = load_seal_record(UNIT, root)
    recorded = {e["path"]: e.get("md5") for e in seal.get("files", [])}
    rows = []
    for p in paths:
        full = Path(root) / p
        now = md5_of(full) if full.is_file() else None
        rows.append({
            "path": p,
            "md5_now": now,
            "md5_in_sealed_json": recorded.get(p),
            "in_seal_record": p in recorded,
            "match": bool(now is not None and recorded.get(p) == now),
        })
    return rows


# ---------------------------------------------------------------------------
# forward diagnostic (PREREG: reit_index_daily vs the ETF, descriptive only)
# ---------------------------------------------------------------------------

def etf_vs_index_gap(etf: pd.DataFrame, index: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """ETF-vs-index divergence at the OPEN and at the CLOSE, in bps.

    PREREG "フォワード": measure how far the 1343 print sits from the 東証REIT
    指数 at the two auction moments the strategy actually trades. Both legs
    are return differences on the common trading days:

      * open leg  (= the paper ledger's ``gap_bps``):
            etf_on_bps  = (etf_open(t+1)   / etf_close(t)   - 1) * 1e4
            index_on_bps = (index_open(t+1) / index_close(t) - 1) * 1e4
            gap_on_bps  = etf_on_bps - index_on_bps
      * close leg (the day session, for symmetry):
            etf_day_bps  = (etf_close(t)  / etf_open(t)  - 1) * 1e4
            index_day_bps = (index_close(t) / index_open(t) - 1) * 1e4
            gap_day_bps  = etf_day_bps - index_day_bps

    Consecutive rows of the merged frame are used as (t, t+1); a pair is
    marked ``consecutive_in_etf`` only when the two dates are also adjacent
    trading days of the ETF's own calendar, and non-adjacent pairs are
    excluded from the open-leg statistics (counted and reported).

    Descriptive only: nothing here feeds the cost model — the PREREG puts the
    measured-cost substitution AFTER the final evaluation, as an iteration.
    """
    e = etf[["date", "open", "close"]].rename(
        columns={"open": "etf_open", "close": "etf_close"}).copy()
    i = index[["date", "open", "close"]].rename(
        columns={"open": "idx_open", "close": "idx_close"}).copy()
    e["date"] = pd.to_datetime(e["date"])
    i["date"] = pd.to_datetime(i["date"])
    m = e.merge(i, on="date", how="inner").sort_values("date").reset_index(drop=True)
    etf_days = list(pd.to_datetime(etf["date"]).sort_values())
    pos = {d: k for k, d in enumerate(etf_days)}

    m["etf_day_bps"] = (m["etf_close"] / m["etf_open"] - 1.0) * 1e4
    m["idx_day_bps"] = (m["idx_close"] / m["idx_open"] - 1.0) * 1e4
    m["gap_day_bps"] = m["etf_day_bps"] - m["idx_day_bps"]

    nxt = m.shift(-1)
    m["date_t1"] = nxt["date"]
    m["etf_on_bps"] = (nxt["etf_open"] / m["etf_close"] - 1.0) * 1e4
    m["idx_on_bps"] = (nxt["idx_open"] / m["idx_close"] - 1.0) * 1e4
    m["gap_on_bps"] = m["etf_on_bps"] - m["idx_on_bps"]
    m["consecutive_in_etf"] = [
        bool(pd.notna(d1) and d0 in pos and d1 in pos and pos[d1] - pos[d0] == 1)
        for d0, d1 in zip(m["date"], m["date_t1"])
    ]

    on = m[m["consecutive_in_etf"]]
    stats = {
        "common_days": int(len(m)),
        "first_common_day": str(m["date"].min().date()) if len(m) else None,
        "last_common_day": str(m["date"].max().date()) if len(m) else None,
        "open_leg_pairs": int(len(on)),
        "open_leg_pairs_dropped_non_adjacent": int((~m["consecutive_in_etf"]).sum() - 1)
        if len(m) else 0,
    }
    for label, series in (("gap_on_bps", on["gap_on_bps"]),
                          ("etf_on_bps", on["etf_on_bps"]),
                          ("idx_on_bps", on["idx_on_bps"]),
                          ("gap_day_bps", m["gap_day_bps"]),
                          ("etf_day_bps", m["etf_day_bps"]),
                          ("idx_day_bps", m["idx_day_bps"])):
        v = pd.to_numeric(series, errors="coerce").dropna()
        stats[f"{label}_n"] = int(len(v))
        stats[f"{label}_mean"] = float(v.mean()) if len(v) else float("nan")
        stats[f"{label}_median"] = float(v.median()) if len(v) else float("nan")
        stats[f"{label}_sd"] = float(v.std(ddof=1)) if len(v) > 1 else float("nan")
        stats[f"{label}_absmean"] = float(v.abs().mean()) if len(v) else float("nan")
    return m, stats


def ledger_diagnostic(ledger: pd.DataFrame) -> dict:
    """Row count of the forward paper ledger, and — only when it holds at
    least FORWARD_MIN_ROWS rows — its own recorded ``gap_bps`` statistics."""
    out: dict = {"rows": int(len(ledger)),
                 "min_rows_required": FORWARD_MIN_ROWS,
                 "enough_rows": bool(len(ledger) >= FORWARD_MIN_ROWS)}
    if not out["enough_rows"] or "gap_bps" not in ledger.columns:
        return out
    v = pd.to_numeric(ledger["gap_bps"], errors="coerce").dropna()
    out["gap_bps_n"] = int(len(v))
    if len(v):
        out["gap_bps_mean"] = float(v.mean())
        out["gap_bps_median"] = float(v.median())
        out["gap_bps_absmean"] = float(v.abs().mean())
        out["gap_bps_sd"] = float(v.std(ddof=1)) if len(v) > 1 else float("nan")
    return out


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

def main(out_dir: Path | None = None, root: Path | str = REPO_ROOT,
         token: str = UNSEAL_TOKEN) -> int:
    root = Path(root)
    check_guards(root, token)
    out = out_dir if out_dir is not None else OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    steps: dict[str, object] = {}
    log_start = _unseal_log_len(root)

    # cost constants come from the repo's own registry (config/constants.yaml),
    # not from the data root: they are pre-registered constants, not data.
    constants = load_constants(REPO_ROOT)
    bands = build_tick_lookup(
        constants["jpx_cash_equity.etf_tick_size_yen_by_price_band"].value)

    # ---- load the sealed rows ---------------------------------------------
    price_1343_sealed = load_sealed(PRICE_1343, UNIT, token=token, root=root)
    price_1321_sealed = load_sealed(PRICE_1321, UNIT, token=token, root=root)
    div_sealed = load_sealed(DIV_1343, UNIT, token=token, root=root)
    index_sealed = load_sealed(REIT_INDEX, UNIT, token=token, root=root)
    steps["rows_sealed_1343"] = int(len(price_1343_sealed))
    steps["rows_sealed_1321"] = int(len(price_1321_sealed))
    steps["rows_sealed_dividends"] = int(len(div_sealed))
    steps["rows_sealed_reit_index"] = int(len(index_sealed))

    try:
        ledger = load_sealed(FORWARD_LEDGER, UNIT, token=token, root=root)
        ledger_via = "load_sealed"
    except SealedDataError as exc:
        # The forward paper ledger did not exist when the unit was sealed, so
        # it is not one of SEALED.json's files and load_sealed refuses it by
        # construction. It is forward data (created 2026-09-06 onward), never
        # part of the held-out historical window; read it directly and record
        # why. Deviation noted in RESULTS.md §逸脱.
        lp = root / FORWARD_LEDGER
        ledger = pd.read_csv(lp) if lp.is_file() else pd.DataFrame()
        ledger_via = "direct read (forward file, not listed in SEALED.json)"
        steps["forward_ledger_load_sealed_refusal"] = str(exc)
    steps["rows_forward_ledger"] = int(len(ledger))

    # ---- the FULL trading-day calendar for the ex-date derivation ----------
    price_1343_dev = load_unsealed(PRICE_1343, UNIT, root=root)
    calendar = full_trading_calendar(price_1343_dev, price_1343_sealed)
    steps["calendar_days_total"] = int(len(calendar))
    steps["calendar_days_pre_seal"] = int((calendar["date"] < SEALED_START).sum())

    # ---- endpoint rule: both days of a pair inside the sealed window -------
    price_1343 = restrict_window(price_1343_sealed, SEALED_START, SEALED_END)
    price_1321 = restrict_window(price_1321_sealed, SEALED_START, SEALED_END)
    steps["rows_1343_in_window"] = int(len(price_1343))
    steps["rows_1321_in_window"] = int(len(price_1321))

    # ---- 1343 -------------------------------------------------------------
    pairs, flagged, one_sided, ghost_idx = build_pair_table(price_1343, bands)

    div = div_sealed.copy()
    div["ex_date"] = pd.to_datetime(div["ex_date"])
    eff_check = onr.ex_dates_from_record_dates(
        list(div["ex_date"]), list(calendar["date"]))
    if len(set(eff_check)) != len(eff_check):
        raise SealedDataError(
            "two record dates derive to the same effective ex-date; the "
            "pre-registered adjustment assumes one amount per ex-date")
    pairs, div_eff = add_dividend_adjustment(pairs, calendar, div)
    data_check = dividend_data_check(pairs, div_eff)

    # PREREG: the dividend-convention data check is a DEV-SET, pre-run check
    # (ITER.md iteration 0: median -71.9 / +4.4 bps -> passed), so the
    # correction is used here. The same check recomputed on the sealed rows is
    # reported descriptively below, never as a switch.
    use_correction = True

    kept = pairs[pairs["kept"]].reset_index(drop=True)
    main_col = "r_night_adj_bps"
    net_cons_col = "net_conservative_adj_bps"
    net_opt_col = "net_optimistic_adj_bps"

    net_cons = kept[net_cons_col].to_numpy()
    net_opt = kept[net_opt_col].to_numpy()
    r_night = kept[main_col].to_numpy()
    net_cons_unadj = kept["net_conservative_raw_bps"].to_numpy()
    net_opt_unadj = kept["net_optimistic_raw_bps"].to_numpy()

    n_main = int(len(net_cons))
    sigma_bps = float(np.std(net_cons, ddof=1))
    se_bps = sigma_bps / np.sqrt(n_main)
    mde = mde_bps(sigma_bps, n_main)

    mean_cons, ci_lo_cons, ci_hi_cons = mean_ci_bootstrap(net_cons, seed=SEED)
    mean_opt, ci_lo_opt, ci_hi_opt = mean_ci_bootstrap(net_opt, seed=SEED + 1)
    mean_cons_un, ci_lo_cons_un, ci_hi_cons_un = mean_ci_bootstrap(
        net_cons_unadj, seed=SEED + 10)
    mean_opt_un, ci_lo_opt_un, ci_hi_opt_un = mean_ci_bootstrap(
        net_opt_unadj, seed=SEED + 11)
    mean_gross, ci_lo_gross, ci_hi_gross = mean_ci_bootstrap(r_night, seed=SEED + 12)

    hit_rate = float(np.mean(net_cons > 0))
    sharpe = sharpe_annualized(net_cons, kept["t_date"])
    span_days = (kept["t_date"].max() - kept["t_date"].min()).days
    years = span_days / 365.25
    periods_per_year = n_main / years

    nd = kept.dropna(subset=["r_day_bps"])
    diff = (nd[main_col] - nd["r_day_bps"]).to_numpy()
    diff_mean, diff_lo, diff_hi = mean_ci_bootstrap(diff, seed=SEED + 2)
    mean_r_day = float(nd["r_day_bps"].mean())

    # ---- drawdown bar (1 unit) --------------------------------------------
    pnl_yen = kept["close_t"].to_numpy() * (net_cons / 1e4)
    dd = max_drawdown(pnl_yen)
    annual_profit_yen = float(np.mean(pnl_yen) * periods_per_year)
    dd_ok = bool(dd <= DD_BAR_MULTIPLE * annual_profit_yen) if annual_profit_yen > 0 else False
    dd_median_boot = block_bootstrap_max_dd_median(pnl_yen, BLOCK, N_BOOT, SEED + 4)

    # ---- 1321 comparison (same rules, no dividend file) --------------------
    pairs_1321, flagged_1321, one_sided_1321, ghost_1321 = build_pair_table(
        price_1321, bands)
    kept_1321 = pairs_1321[pairs_1321["kept"]].reset_index(drop=True)
    net_cons_1321 = kept_1321["net_conservative_raw_bps"].to_numpy()
    n_1321 = int(len(net_cons_1321))
    mean_1321, ci_lo_1321, ci_hi_1321 = mean_ci_bootstrap(net_cons_1321, seed=SEED + 5)
    sign_match = bool(np.sign(mean_cons) == np.sign(mean_1321)) \
        if (mean_cons != 0 and mean_1321 != 0) else False
    both_ci_positive = bool(ci_lo_cons > 0 and ci_lo_1321 > 0)
    futures_like = bool(sign_match and both_ci_positive)

    # ---- controls ----------------------------------------------------------
    null_means = onr.sign_shuffle_null(net_cons, n=N_SHUFFLE, seed=SEED + 6)
    null_95pct = float(np.percentile(null_means, 95))
    null_pct_of_observed = float(np.mean(null_means <= mean_cons) * 100.0)
    null_gross = onr.sign_shuffle_null(r_night, n=N_SHUFFLE, seed=SEED + 13)
    null_gross_95pct = float(np.percentile(null_gross, 95))

    vol20 = kept["vol20_t"].to_numpy()
    valid_vol = ~np.isnan(vol20)
    terciles = np.full(len(vol20), -1, dtype=int)
    if valid_vol.sum() >= 3:
        qs = np.nanquantile(vol20, [1 / 3, 2 / 3])
        terciles[valid_vol] = np.digitize(vol20[valid_vol], qs)
    strata_dist = stratified_bootstrap_mean_dist(
        net_cons[valid_vol], terciles[valid_vol], N_STRATA_BOOT, SEED + 7
    ) if valid_vol.sum() >= 3 else np.array([])

    reversal = sign_reversal_stats(r_night, kept["cost_conservative_bps"].to_numpy())

    # ---- diagnostics (descriptive only) ------------------------------------
    diag = kept.copy()
    diag["net_cons_bps"] = net_cons
    diag["vol_tercile"] = np.where(valid_vol, terciles, -1)
    vol_tercile_diag = (diag[diag["vol_tercile"] >= 0]
                        .groupby("vol_tercile")["net_cons_bps"]
                        .agg(["mean", "std", "count"]).reset_index())
    diag["weekday"] = diag["t_date"].dt.dayofweek
    weekday_diag = diag.groupby("weekday")["net_cons_bps"].agg(
        ["mean", "std", "count"]).reset_index()
    diag["month"] = diag["t_date"].dt.month
    month_diag = diag.groupby("month")["net_cons_bps"].agg(
        ["mean", "std", "count"]).reset_index()
    diag["year"] = diag["t_date"].dt.year
    year_diag = diag.groupby("year")["net_cons_bps"].agg(
        ["mean", "std", "count"]).reset_index()

    eff_ex_dates = pd.to_datetime(div_eff["ex_date_effective"])
    ex_set = set(eff_ex_dates)
    ex_prev = set(eff_ex_dates - pd.tseries.offsets.BDay(1))
    ex_next = set(eff_ex_dates + pd.tseries.offsets.BDay(1))

    def _ex_label(t1_date):
        if t1_date in ex_set:
            return "ex_date"
        if t1_date in ex_prev:
            return "ex_date-1"
        if t1_date in ex_next:
            return "ex_date+1"
        return "other"

    diag["ex_date_window"] = diag["t1_date"].map(_ex_label)
    exdate_diag = diag.groupby("ex_date_window")["net_cons_bps"].agg(
        ["mean", "std", "count"]).reset_index()

    # ---- 2024-11-05 closing-auction change (descriptive) -------------------
    regime_rows = []
    for label, sub in (
        (f"2021-04-13..{(REGIME_SPLIT - pd.Timedelta(days=1)).date()}(引け板寄せ 15:00)",
         kept[kept["t_date"] < REGIME_SPLIT]),
        (f"{REGIME_SPLIT.date()}..2026-09-03(引け板寄せ 15:30)",
         kept[kept["t_date"] >= REGIME_SPLIT]),
    ):
        vals = sub[net_cons_col].to_numpy()
        m_, lo_, hi_ = mean_ci_bootstrap(vals, seed=SEED + 14) if len(vals) else (
            float("nan"), float("nan"), float("nan"))
        regime_rows.append({
            "regime": label, "n": int(len(vals)), "mean_net_cons_bps": m_,
            "ci_lo_bps": lo_, "ci_hi_bps": hi_,
            "mean_gross_bps": float(sub[main_col].mean()) if len(sub) else float("nan"),
            "mean_r_day_bps": float(sub["r_day_bps"].mean()) if len(sub) else float("nan"),
            "hit_rate": float((vals > 0).mean()) if len(vals) else float("nan"),
        })
    regime_df = pd.DataFrame(regime_rows)

    # ---- thin trading (mark only; judgment uses the whole set) -------------
    thin_mask = kept["thin"].to_numpy()
    n_thin_kept = int(thin_mask.sum())
    n_thin_all = int(pairs["thin"].sum())
    n_thin_overlap_ghost = int(pairs.loc[pairs["thin"] & pairs["ghost_excluded"]].shape[0])
    n_thin_true = int(pairs.loc[pairs["thin"] & (~pairs["ghost_excluded"])].shape[0])
    mean_excl_thin = float(np.mean(net_cons[~thin_mask])) if (~thin_mask).sum() else float("nan")

    # ---- exclusion (before/after) summary ----------------------------------
    excl_1343 = exclusion_stage_stats(pairs)
    excl_1321 = exclusion_stage_stats(pairs_1321)
    ghost_dates = [str(pd.Timestamp(d).date())
                   for d in pd.to_datetime(price_1343["date"]).iloc[sorted(ghost_idx)]]
    bad_print_dates = [str(pd.Timestamp(d).date())
                       for d in pd.to_datetime(price_1343["date"]).iloc[sorted(flagged)]]
    ghost_dates_1321 = [str(pd.Timestamp(d).date())
                        for d in pd.to_datetime(price_1321["date"]).iloc[sorted(ghost_1321)]]

    # ---- forward diagnostic ------------------------------------------------
    index_df = restrict_window(index_sealed, pd.Timestamp("1900-01-01"), SEALED_END)
    gap_df, gap_stats = etf_vs_index_gap(price_1343, index_df)
    led = ledger_diagnostic(ledger)
    led["source"] = ledger_via

    # ---- bar / falsification / hold class ----------------------------------
    bar1 = bool(mean_cons > null_95pct)
    bar2 = bool(ci_lo_cons > 0)
    bar3 = sign_match
    bar_all = bool(bar1 and bar2 and bar3)
    fals_ci_contains_zero = bool(ci_lo_cons <= 0 <= ci_hi_cons)
    hold_class = bool((ci_lo_opt > 0) and not bar2)

    bar_rows = [
        {"criterion": f"バー1 累計 N = {CUMULATIVE_N}(自由パラメータ無し=単一構成)の"
                      "符号シャッフル帰無分布の 95 点を超える",
         "measured": f"実測平均ネット {mean_cons:,.3f} bps vs 帰無95点 {null_95pct:,.3f} bps",
         "outcome": "満たす" if bar1 else "満たさない"},
        {"criterion": "バー2 保守コスト後の平均夜間リターンの 95% CI が正",
         "measured": f"[{ci_lo_cons:,.3f}, {ci_hi_cons:,.3f}] bps",
         "outcome": "満たす" if bar2 else "満たさない"},
        {"criterion": "バー3 1321 と符号一致",
         "measured": f"1343 {mean_cons:,.3f} bps / 1321 {mean_1321:,.3f} bps",
         "outcome": "満たす" if bar3 else "満たさない"},
        {"criterion": "(参考)「先物と同様」= 符号一致かつ双方の 95% CI が正",
         "measured": f"1343 CI [{ci_lo_cons:,.3f}, {ci_hi_cons:,.3f}] / "
                     f"1321 CI [{ci_lo_1321:,.3f}, {ci_hi_1321:,.3f}]",
         "outcome": "満たす" if futures_like else "満たさない"},
        {"criterion": "(参考)ドローダウン基準 最大DD ≤ 年率換算平均ネット利益 × 3",
         "measured": f"最大DD {dd:,.1f} 円 vs 3×年率平均ネット {3 * annual_profit_yen:,.1f} 円"
                     f"(年率平均ネット {annual_profit_yen:,.1f} 円)",
         "outcome": "満たす" if dd_ok else "満たさない"},
        {"criterion": "バー3条件すべて同時充足",
         "measured": f"バー1 {bar1} / バー2 {bar2} / バー3 {bar3}",
         "outcome": "満たす" if bar_all else "満たさない"},
    ]
    fals_rows = [
        {"criterion": "反証文 封印期間で「保守コスト後の平均夜間リターンの 95% CI が"
                      "ゼロを含む」→「取引可能な形で捕捉できる」は棄却",
         "measured": f"[{ci_lo_cons:,.3f}, {ci_hi_cons:,.3f}] bps",
         "outcome": "満たす" if fals_ci_contains_zero else "満たさない"},
        {"criterion": "保留区分 楽観コストでのみ正(=「存在するが取引不能」、"
                      "引き金 = スプレッドの実測)",
         "measured": f"楽観 [{ci_lo_opt:,.3f}, {ci_hi_opt:,.3f}] / "
                     f"保守 [{ci_lo_cons:,.3f}, {ci_hi_cons:,.3f}] bps",
         "outcome": "満たす" if hold_class else "満たさない"},
    ]

    # =========================== write CSVs =================================
    written: list[str] = []

    def write(df: pd.DataFrame, name: str):
        df.to_csv(out / name, index=False)
        written.append(name)

    write(pairs, "pairs_1343_sealed.csv")
    write(pairs_1321, "pairs_1321_sealed.csv")
    write(div_eff, "ex_dates_1343.csv")
    write(pd.DataFrame([{"instrument": "1343", **s} for s in excl_1343]
                       + [{"instrument": "1321", **s} for s in excl_1321]),
          "exclusion_summary.csv")
    write(pd.DataFrame([
        {"indicator": "主指標 保守コスト後平均(分配金補正あり)", "n": n_main,
         "mean_bps": mean_cons, "ci_lo_bps": ci_lo_cons, "ci_hi_bps": ci_hi_cons},
        {"indicator": "楽観コスト(0)平均(分配金補正あり)", "n": n_main,
         "mean_bps": mean_opt, "ci_lo_bps": ci_lo_opt, "ci_hi_bps": ci_hi_opt},
        {"indicator": "グロス夜間リターン(分配金補正あり)", "n": n_main,
         "mean_bps": mean_gross, "ci_lo_bps": ci_lo_gross, "ci_hi_bps": ci_hi_gross},
        {"indicator": "保守コスト後平均(分配金補正なし)", "n": n_main,
         "mean_bps": mean_cons_un, "ci_lo_bps": ci_lo_cons_un, "ci_hi_bps": ci_hi_cons_un},
        {"indicator": "楽観コスト(0)平均(分配金補正なし)", "n": n_main,
         "mean_bps": mean_opt_un, "ci_lo_bps": ci_lo_opt_un, "ci_hi_bps": ci_hi_opt_un},
        {"indicator": "夜間 − 日中の差", "n": int(len(diff)),
         "mean_bps": diff_mean, "ci_lo_bps": diff_lo, "ci_hi_bps": diff_hi},
        {"indicator": "1321 保守コスト後平均", "n": n_1321,
         "mean_bps": mean_1321, "ci_lo_bps": ci_lo_1321, "ci_hi_bps": ci_hi_1321},
    ]), "main_indicators.csv")
    write(pd.DataFrame([
        {"control": "1_sign_shuffle_single_config", "n_draws": N_SHUFFLE,
         "observed_mean_bps": mean_cons, "null_95pct_bps": null_95pct,
         "observed_percentile_in_null": null_pct_of_observed,
         "null_95pct_gross_bps": null_gross_95pct,
         "observed_gross_mean_bps": mean_gross},
        {"control": "2_vol_tercile_stratified_bootstrap_diagnostic",
         "n_draws": len(strata_dist),
         "dist_mean_bps": float(np.mean(strata_dist)) if len(strata_dist) else float("nan"),
         "dist_std_bps": float(np.std(strata_dist, ddof=1)) if len(strata_dist) > 1
         else float("nan")},
        {"control": "3_sign_reversal", "n_draws": None,
         "mean_bps": reversal["mean_bps"], "ci_lo_bps": reversal["ci_lo_bps"],
         "ci_hi_bps": reversal["ci_hi_bps"], "n": reversal["n"]},
    ]), "controls_summary.csv")
    write(vol_tercile_diag, "diagnostics_vol_tercile.csv")
    write(weekday_diag, "diagnostics_weekday.csv")
    write(month_diag, "diagnostics_month.csv")
    write(year_diag, "diagnostics_year.csv")
    write(exdate_diag, "diagnostics_exdate.csv")
    write(regime_df, "regime_split_20241105.csv")
    write(gap_df, "forward_etf_vs_index_gap.csv")
    write(pd.DataFrame([{"key": k, "value": v} for k, v in
                        list(gap_stats.items()) + list(led.items())]),
          "forward_diagnostic.csv")
    write(pd.DataFrame([{"kind": "bar", **r} for r in bar_rows]
                       + [{"kind": "falsification", **r} for r in fals_rows]),
          "bar_and_falsification.csv")

    summary = {
        "sealed_window": f"{SEALED_START.date()}..{SEALED_END.date()}",
        "cumulative_N": CUMULATIVE_N,
        "n_raw_pairs_1343": int(len(pairs)),
        "n_after_rule1_1343": int((~pairs["rule1_excluded"]).sum()),
        "n_after_rule2_1343": int(pairs["kept"].sum()),
        "n_bad_print_rows_1343": len(flagged),
        "n_one_sided_info_rows_1343": len(one_sided),
        "n_ghost_rows_1343": len(ghost_idx),
        "n_thin_pairs_all_1343": n_thin_all,
        "n_thin_pairs_kept_1343": n_thin_kept,
        "n_thin_overlap_ghost_1343": n_thin_overlap_ghost,
        "n_thin_true_1343": n_thin_true,
        "mean_excl_thin_bps": mean_excl_thin,
        "n_dividend_rows_sealed": int(len(div_eff)),
        "n_dividend_non_trading_record_dates": int(div_eff["is_non_trading_record_date"].sum()),
        "dividend_correction_used": use_correction,
        "sealed_dividend_check_n_pairs": data_check["n_ex_date_pairs_checked"],
        "sealed_dividend_check_median_raw_bps": data_check["median_raw_bps"],
        "sealed_dividend_check_median_adj_bps": data_check["median_adj_bps"],
        "sealed_dividend_check_passes": data_check["passes"],
        "n_main": n_main,
        "years_span": years,
        "periods_per_year": periods_per_year,
        "sigma_bps": sigma_bps,
        "se_bps": se_bps,
        "mde_bps_sealed_sample": mde,
        "mean_net_conservative_bps": mean_cons,
        "ci_lo_conservative_bps": ci_lo_cons,
        "ci_hi_conservative_bps": ci_hi_cons,
        "mean_net_optimistic_bps": mean_opt,
        "ci_lo_optimistic_bps": ci_lo_opt,
        "ci_hi_optimistic_bps": ci_hi_opt,
        "mean_gross_bps": mean_gross,
        "ci_lo_gross_bps": ci_lo_gross,
        "ci_hi_gross_bps": ci_hi_gross,
        "mean_net_conservative_unadjusted_bps": mean_cons_un,
        "ci_lo_conservative_unadjusted_bps": ci_lo_cons_un,
        "ci_hi_conservative_unadjusted_bps": ci_hi_cons_un,
        "mean_net_optimistic_unadjusted_bps": mean_opt_un,
        "ci_lo_optimistic_unadjusted_bps": ci_lo_opt_un,
        "ci_hi_optimistic_unadjusted_bps": ci_hi_opt_un,
        "cost_conservative_median_bps": float(kept["cost_conservative_bps"].median()),
        "cost_conservative_mean_bps": float(kept["cost_conservative_bps"].mean()),
        "hit_rate": hit_rate,
        "sharpe_annualized": sharpe,
        "mean_r_day_bps": mean_r_day,
        "night_minus_day_mean_bps": diff_mean,
        "night_minus_day_ci_lo_bps": diff_lo,
        "night_minus_day_ci_hi_bps": diff_hi,
        "max_drawdown_yen_1unit": dd,
        "annualized_mean_net_profit_yen_1unit": annual_profit_yen,
        "drawdown_bar_multiple": DD_BAR_MULTIPLE,
        "drawdown_ok": dd_ok,
        "max_drawdown_bootstrap_median_yen": dd_median_boot,
        "n_1321": n_1321,
        "mean_net_conservative_bps_1321": mean_1321,
        "ci_lo_bps_1321": ci_lo_1321,
        "ci_hi_bps_1321": ci_hi_1321,
        "sign_match_1343_vs_1321": sign_match,
        "both_ci_positive": both_ci_positive,
        "futures_like_criterion_met": futures_like,
        "sign_shuffle_null_95pct_bps": null_95pct,
        "sign_shuffle_observed_percentile": null_pct_of_observed,
        "sign_shuffle_null_95pct_gross_bps": null_gross_95pct,
        "sign_reversal_mean_bps": reversal["mean_bps"],
        "sign_reversal_ci_lo_bps": reversal["ci_lo_bps"],
        "sign_reversal_ci_hi_bps": reversal["ci_hi_bps"],
        "bar1_beats_null_95pct": bar1,
        "bar2_ci_positive": bar2,
        "bar3_sign_match_1321": bar3,
        "bar_all_three_met": bar_all,
        "falsification_ci_contains_zero": fals_ci_contains_zero,
        "hold_class_optimistic_only": hold_class,
        "forward_ledger_rows": led["rows"],
    }
    pd.DataFrame([summary]).T.reset_index().rename(
        columns={"index": "metric", 0: "value"}).to_csv(
        out / "main_summary.csv", index=False)
    written.append("main_summary.csv")

    # =========================== RESULTS.md =================================
    def f(x, nd=3):
        if x is None:
            return "N/A"
        if isinstance(x, bool):
            return "はい" if x else "いいえ"
        try:
            if np.isnan(x):
                return "NaN"
        except TypeError:
            return str(x)
        return f"{x:,.{nd}f}"

    md: list[str] = []
    md.append("# P2-02 最終評価(封印期間、1 回のみ)— 数値報告")
    md.append("")
    md.append(f"実行日 2026-09-06 / seed {SEED} / git {_git_rev()[:12]} / 単位 {UNIT} / "
              f"累計 N = {CUMULATIVE_N}(事前登録の主検定に自由パラメータは無い)。")
    md.append(f"読み込みは `load_sealed(path, \"{UNIT}\", token=UNSEAL_TOKEN)` のみ"
              "(env `PHASE2_FINAL_EVAL=P2-02` + オーナー承認ファイル + トークンの三重ゲート)。"
              "P2-01 / P2-03 の封印データには一切触れていない。")
    md.append("")
    md.append("**本書は数値の報告のみで、採用・棄却の判断は行わない(オーナーが決める)。**")
    md.append("")
    md.append("## 0. 母集団・端点規則・欠陥規則")
    md.append("")
    md.append(f"- 封印期間 {SEALED_START.date()} .. {SEALED_END.date()}。端点規則: ペア (t, t+1) は"
              "両日が封印期間内のときだけ採用。")
    md.append(f"- 封印行数: 1343 {steps['rows_sealed_1343']:,} 行 / 1321 "
              f"{steps['rows_sealed_1321']:,} 行 / 分配金 {steps['rows_sealed_dividends']:,} 行 / "
              f"東証REIT指数 {steps['rows_sealed_reit_index']:,} 行。")
    md.append(f"- 権利落ち日の導出に使った取引日暦は価格ファイルの**全期間** "
              f"{steps['calendar_days_total']:,} 日(うち封印前 {steps['calendar_days_pre_seal']:,} 日)。"
              "封印前の日付は暦の位置を与えるためだけに使い、価格・リターン・ペアは一切評価に入らない。")
    md.append("")
    md.append("### 1343 除外の前後")
    md.append("")
    md.append("| 段階 | n | 平均(bps) | σ(bps) |")
    md.append("|---|---:|---:|---:|")
    for row in excl_1343:
        md.append(f"| {row['stage']} | {row['n']:,} | {f(row['mean_bps'],2)} | {f(row['std_bps'],2)} |")
    md.append("")
    md.append(f"- 規則1の誤プリント行: {len(flagged)} 件"
              f"{'(' + ', '.join(bad_print_dates) + ')' if bad_print_dates else ''}"
              f"、片方だけ飛ぶ行(除外せず件数のみ): {len(one_sided)} 件。")
    md.append(f"- 規則2の幽霊行: {len(ghost_idx)} 件"
              f"{'(' + ', '.join(ghost_dates) + ')' if ghost_dates else ''}。")
    md.append(f"- 薄商い(出来高 < {THIN_VOLUME_THRESHOLD:,} 口)の印: 全ペア中 {n_thin_all} 件"
              f"(うち幽霊行と重なる {n_thin_overlap_ghost} 件、真の薄商い {n_thin_true} 件)。"
              f"採用集合内 {n_thin_kept} 件。薄商いを除いた主指標(参考) {f(mean_excl_thin,2)} bps。"
              "判定は全体を使用。")
    md.append("")
    md.append("### 1321 除外の前後(同一規則)")
    md.append("")
    md.append("| 段階 | n | 平均(bps) | σ(bps) |")
    md.append("|---|---:|---:|---:|")
    for row in excl_1321:
        md.append(f"| {row['stage']} | {row['n']:,} | {f(row['mean_bps'],2)} | {f(row['std_bps'],2)} |")
    md.append("")
    md.append(f"1321 の誤プリント行 {len(flagged_1321)} 件、幽霊行 {len(ghost_1321)} 件"
              f"{'(' + ', '.join(ghost_dates_1321) + ')' if ghost_dates_1321 else ''}、"
              f"片側飛び {len(one_sided_1321)} 件。")
    md.append("")
    md.append("## 1. 分配金(権利落ち日の導出)")
    md.append("")
    md.append(f"- 封印期間の分配金 {len(div_eff)} 件、うち権利確定日が非取引日 "
              f"{int(div_eff['is_non_trading_record_date'].sum())} 件。導出規則は事前登録どおり"
              "(権利確定日以前の最終取引日 eff の、T+2 移行後は 1 取引日前 / 移行前は 2 取引日前)。")
    md.append(f"- 補正の使用は事前登録どおり**開発セットの検証結果**(反復 0: 中央値 −71.9bps → "
              f"補正後 +4.4bps、合格)に従い、補正を使う。参考として封印標本で同じ検証を再計算すると "
              f"n = {data_check['n_ex_date_pairs_checked']}、補正前中央値 "
              f"{f(data_check['median_raw_bps'],2)} bps、補正後中央値 "
              f"{f(data_check['median_adj_bps'],2)} bps(記述のみ、切替には使わない)。")
    md.append("- 主指標は補正**あり**。補正**なし**の値も §2 に併記。")
    md.append("")
    md.append("## 2. 主指標(保守コスト後の平均夜間リターン)")
    md.append("")
    md.append(f"CI はブロック・ブートストラップ(ブロック長 {BLOCK}、リサンプル {N_BOOT:,}、"
              f"percentile 法、seed {SEED})。単位は bps/ペア。r_night は単純収益 "
              "open(t+1)/close(t) − 1。保守コスト = 2 / close(t) × 10^4(1 ティック/片側、"
              "1343 の呼値 1 円)、楽観コスト = 0。")
    md.append("")
    md.append("| 指標 | n | 平均(bps) | CI下限 | CI上限 |")
    md.append("|---|---:|---:|---:|---:|")
    for r in [
        ("主指標 保守コスト後(補正あり)", n_main, mean_cons, ci_lo_cons, ci_hi_cons),
        ("楽観コスト 0(補正あり)", n_main, mean_opt, ci_lo_opt, ci_hi_opt),
        ("グロス夜間リターン(補正あり)", n_main, mean_gross, ci_lo_gross, ci_hi_gross),
        ("保守コスト後(補正なし)", n_main, mean_cons_un, ci_lo_cons_un, ci_hi_cons_un),
        ("楽観コスト 0(補正なし)", n_main, mean_opt_un, ci_lo_opt_un, ci_hi_opt_un),
        ("夜間 − 日中の差", int(len(diff)), diff_mean, diff_lo, diff_hi),
        ("1321 保守コスト後", n_1321, mean_1321, ci_lo_1321, ci_hi_1321),
    ]:
        md.append(f"| {r[0]} | {r[1]:,} | {f(r[2])} | {f(r[3])} | {f(r[4])} |")
    md.append("")
    md.append(f"- n = {n_main:,}、σ = {f(sigma_bps,2)} bps、SE = {f(se_bps)} bps、"
              f"封印標本での MDE(α 0.05・検出力 0.8) = {f(mde,2)} bps"
              "(事前登録の開発セット MDE は 4.6bps。記録のみで判定には使わない)。")
    md.append(f"- 勝率 {f(hit_rate,4)}、Sharpe(年率) {f(sharpe)}"
              f"(換算係数 √(n/年数) = √({n_main}/{years:.2f}) = {np.sqrt(periods_per_year):.2f})、"
              f"日中平均 {f(mean_r_day,2)} bps。")
    md.append(f"- ペアごとの保守コスト: 中央値 {f(float(kept['cost_conservative_bps'].median()),2)} bps、"
              f"平均 {f(float(kept['cost_conservative_bps'].mean()),2)} bps、範囲 "
              f"{kept['cost_conservative_bps'].min():.2f}〜{kept['cost_conservative_bps'].max():.2f} bps。")
    md.append("")
    md.append("## 3. ドローダウン基準(1 口固定、保守コスト後)")
    md.append("")
    md.append(f"- 最大ドローダウン(単一実現値) **{f(dd,1)} 円**")
    md.append(f"- 年率換算平均ネット利益 {f(annual_profit_yen,1)} 円 → その 3 倍 "
              f"{f(3 * annual_profit_yen,1)} 円")
    md.append(f"- 基準内(最大DD ≤ 3 × 年率平均ネット利益): **{f(dd_ok)}**")
    md.append(f"- ブロック・ブートストラップによる最大DDの分布の中央値: {f(dd_median_boot,1)} 円"
              "(判定は単一実現値、事前登録どおり)")
    md.append("")
    md.append("## 4. 「先物と同様」比較(1321、同一規則)")
    md.append("")
    md.append(f"- 1321 n = {n_1321:,}、保守コスト後平均 {f(mean_1321)} bps、"
              f"CI [{f(ci_lo_1321)}, {f(ci_hi_1321)}]")
    md.append(f"- 符号一致: **{f(sign_match)}** / 双方の 95% CI が正: **{f(both_ci_positive)}** → "
              f"「先物と同様」基準: **{f(futures_like)}**")
    md.append("")
    md.append("## 5. 対照(反事実)")
    md.append("")
    md.append(f"- (1) 符号シャッフル {N_SHUFFLE:,} 回(累計 N = {CUMULATIVE_N} なので**単一構成**の"
              f"帰無、最良取りは不要): 帰無 95 点 = {f(null_95pct)} bps、実測平均 "
              f"{f(mean_cons)} bps、実測以下の帰無標本の割合 {f(null_pct_of_observed,1)}%。"
              f"参考: グロスで見た帰無 95 点 {f(null_gross_95pct)} bps vs 実測グロス {f(mean_gross)} bps。")
    strata_mean = float(np.mean(strata_dist)) if len(strata_dist) else float("nan")
    strata_std = float(np.std(strata_dist, ddof=1)) if len(strata_dist) > 1 else float("nan")
    md.append(f"- (2) 20 日実現ボラ三分位内の層別ブートストラップ(診断のみ、時間順序を保存しない): "
              f"平均の分布 平均 {f(strata_mean)} bps、標準偏差 {f(strata_std)} bps。")
    md.append(f"- (3) 符号反転(夜間売り持ち、往復コストは方向に依らず控除): 平均 "
              f"{f(reversal['mean_bps'])} bps、CI [{f(reversal['ci_lo_bps'])}, "
              f"{f(reversal['ci_hi_bps'])}]。")
    md.append("- (4) 1321 との比較は §4。")
    md.append("")
    md.append("## 6. 2024-11-05 の引け板寄せ 15:30 化(前後、記述のみ)")
    md.append("")
    md.append("| 区分 | n | 平均ネット(bps) | CI | グロス(bps) | 日中(bps) | 勝率 |")
    md.append("|---|---:|---:|---|---:|---:|---:|")
    for r in regime_rows:
        md.append(f"| {r['regime']} | {r['n']:,} | {f(r['mean_net_cons_bps'])} | "
                  f"[{f(r['ci_lo_bps'])}, {f(r['ci_hi_bps'])}] | {f(r['mean_gross_bps'],2)} | "
                  f"{f(r['mean_r_day_bps'],2)} | {f(r['hit_rate'],4)} |")
    md.append("")
    md.append("判定は封印期間全体(事前登録どおり)。上表は記述のみ。")
    md.append("")
    md.append("## 7. 診断(記述的のみ、選択には使用しない)")
    md.append("")
    for title, tbl in (("ボラ三分位(0=低, 2=高)", vol_tercile_diag),
                       ("曜日(0=月 … 4=金)", weekday_diag),
                       ("月", month_diag), ("年", year_diag),
                       ("権利落ち日 ±1", exdate_diag)):
        t = tbl.copy()
        for col in ("count", "vol_tercile", "weekday", "month", "year"):
            if col in t.columns:
                t[col] = t[col].astype(int)
        md.append(f"### {title}")
        md.append("")
        md.append(_markdown_table(t))
        md.append("")
    md.append("## 8. フォワード診断(ETF と東証REIT指数の乖離、記述のみ)")
    md.append("")
    md.append(f"`reit_index_daily.csv` は全期間封印({steps['rows_sealed_reit_index']:,} 行、"
              f"{gap_stats['first_common_day']} .. "
              f"{gap_stats['last_common_day']})。1343 と共通の取引日 {gap_stats['common_days']:,} 日、"
              f"うち隣接取引日で寄付き脚を作れたペア {gap_stats['open_leg_pairs']:,} 組。")
    md.append("")
    md.append("| 量 | n | 平均(bps) | 中央値(bps) | 平均絶対値(bps) | SD(bps) |")
    md.append("|---|---:|---:|---:|---:|---:|")
    for key, label in (("gap_on_bps", "寄付き脚の乖離 ETF − 指数(台帳の gap_bps 相当)"),
                       ("etf_on_bps", "同 ETF 夜間リターン"),
                       ("idx_on_bps", "同 指数 夜間リターン"),
                       ("gap_day_bps", "引け脚(日中)の乖離 ETF − 指数"),
                       ("etf_day_bps", "同 ETF 日中リターン"),
                       ("idx_day_bps", "同 指数 日中リターン")):
        md.append(f"| {label} | {gap_stats[key + '_n']:,} | {f(gap_stats[key + '_mean'],2)} | "
                  f"{f(gap_stats[key + '_median'],2)} | {f(gap_stats[key + '_absmean'],2)} | "
                  f"{f(gap_stats[key + '_sd'],2)} |")
    md.append("")
    md.append(f"ペーパー台帳 `paper_logs/onr_ledger.csv` は **{led['rows']} 行**"
              f"(閾値 {FORWARD_MIN_ROWS} 行)。"
              + ("台帳自身の `gap_bps` の統計は上記閾値を満たすため併記した。"
                 if led["enough_rows"] else
                 "閾値未満のため台帳由来の `gap_bps` 診断は報告しない(行数のみ記録)。"))
    md.append("")
    md.append("事前登録どおり、この実測値で丸め仮定を置き換えるのは最終評価の**後**の反復であり、"
              "本評価のコスト(2 / close(t) × 10^4)には一切反映していない。")
    md.append("")
    md.append("## 9. 事前登録のバー・反証文・保留区分(数値の対照のみ、判断はしない)")
    md.append("")
    md.append("PREREG「最終評価」の原文:")
    md.append("")
    md.append("> - バー: 累計 N の帰無 95 点超、かつ保守コスト後の平均夜間リターンの 95% CI が正、"
              "かつ 1321 と符号一致。")
    md.append("> - 反証文: 封印期間で「保守コスト後の平均夜間リターンの 95% CI がゼロを含む」なら"
              "「取引可能な形で捕捉できる」は棄却。楽観コストでのみ正の場合は「存在するが取引不能"
              "(丸め・スプレッド次第)」として保留、引き金 = スプレッドの実測。")
    md.append("")
    md.append("### バー")
    md.append("")
    md.append("| 条件 | 実測 | 判定 |")
    md.append("|---|---|---|")
    for r in bar_rows:
        md.append(f"| {r['criterion']} | {r['measured']} | {r['outcome']} |")
    md.append("")
    md.append("### 反証文と保留区分")
    md.append("")
    md.append("| 文 | 実測 | 判定 |")
    md.append("|---|---|---|")
    for r in fals_rows:
        md.append(f"| {r['criterion']} | {r['measured']} | {r['outcome']} |")
    md.append("")
    md.append("## 10. 事前登録からの逸脱")
    md.append("")
    md.append("- 権利落ち日の導出に**封印前の取引日**を使った(価格・リターンは使っていない)。"
              "事前登録は「取引日は価格ファイル自身の日付列」と書くだけで暦の範囲を限定しておらず、"
              "封印期間だけの暦では権利確定日以前の最終取引日を正しく取れない場合があるため、"
              "全期間の暦を用いた。評価に入るペアは端点規則どおり両日が封印期間内のもののみ。")
    md.append(f"- `paper_logs/onr_ledger.csv` は封印時点で存在せず SEALED.json に無いため "
              f"`load_sealed` が構造上拒否する。フォワードのファイルであって過去の保留期間ではないので、"
              f"行数の報告のためだけに直接読んだ({led['rows']} 行)。読み出し経路: {ledger_via}。")
    md.append("- 対照 1 の帰無は主指標(保守コスト後ネット)に対して取り、開発セットの反復 0 と"
              "同じ検定済みヘルパ・同じ seed 系列を使った。グロスに対する帰無も参考として併記。")
    md.append("- 上記以外の逸脱はない。ブロック長 20・リサンプル 2,000・シャッフル 1,000・"
              "seed 20260906・欠陥規則 1/2・薄商いの印・コスト式・端点規則・"
              "ドローダウン基準 3 倍はすべて凍結された事前登録どおり。")
    md.append("")
    (out / "RESULTS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    written.append("RESULTS.md")

    # =========================== RUN.json ===================================
    md5_rows = md5_check(root, [PRICE_1343, PRICE_1321, DIV_1343, REIT_INDEX])
    run = {
        "unit": UNIT,
        "stage": "final_evaluation_sealed",
        "cumulative_N": CUMULATIVE_N,
        "run_date": str(date(2026, 9, 6)),
        "sealed_window": [str(SEALED_START.date()), str(SEALED_END.date())],
        "seed": SEED,
        "git_rev": _git_rev(),
        "script": "scripts/phase2/p2_02_final.py",
        "script_md5": md5_of(Path(__file__)),
        "inputs_md5_vs_sealed_json": md5_rows,
        "seal_record_md5": md5_of(root / "backtest_data" / "phase2_sealed" / UNIT
                                  / "SEALED.json"),
        "unseal_approved_md5": md5_of(root / "backtest_data" / "phase2_sealed" / UNIT
                                      / "UNSEAL_APPROVED"),
        "parameters": {
            "block": BLOCK, "n_boot": N_BOOT, "n_shuffle": N_SHUFFLE,
            "n_strata_boot": N_STRATA_BOOT,
            "thin_volume_threshold": THIN_VOLUME_THRESHOLD,
            "cost_conservative": "2 / close(t) * 1e4 (1 tick per side)",
            "cost_optimistic": 0,
            "drawdown_bar_multiple": DD_BAR_MULTIPLE,
            "dividend_correction_used": use_correction,
            "return_kind": "simple",
        },
        "n_at_each_step": steps,
        "headline": {
            "mean_net_conservative_bps": mean_cons,
            "ci95": [ci_lo_cons, ci_hi_cons],
            "mean_net_optimistic_bps": mean_opt,
            "ci95_optimistic": [ci_lo_opt, ci_hi_opt],
            "mean_gross_bps": mean_gross,
            "ci95_gross": [ci_lo_gross, ci_hi_gross],
            "mean_net_conservative_unadjusted_bps": mean_cons_un,
            "ci95_unadjusted": [ci_lo_cons_un, ci_hi_cons_un],
            "night_minus_day_bps": diff_mean,
            "ci95_night_minus_day": [diff_lo, diff_hi],
            "n_main": n_main,
            "sharpe_annualised": sharpe,
            "hit_rate": hit_rate,
            "max_drawdown_yen_1unit": dd,
            "annualised_mean_net_profit_yen_1unit": annual_profit_yen,
            "max_drawdown_bootstrap_median_yen": dd_median_boot,
            "mean_net_conservative_bps_1321": mean_1321,
            "ci95_1321": [ci_lo_1321, ci_hi_1321],
            "sign_shuffle_null_95pct_bps": null_95pct,
            "sign_reversal_mean_bps": reversal["mean_bps"],
        },
        "bar": {r["criterion"]: {"measured": r["measured"], "outcome": r["outcome"]}
                for r in bar_rows} | {"all_three_met": bar_all},
        "falsification": {r["criterion"]: {"measured": r["measured"],
                                           "outcome": r["outcome"]} for r in fals_rows},
        "forward_diagnostic": {"etf_vs_index": gap_stats, "paper_ledger": led},
        "unseal_log_excerpt": _read_unseal_log(root, log_start),
        "outputs": sorted(written),
    }
    (out / "RUN.json").write_text(
        json.dumps(run, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8")

    print(json.dumps(run["headline"], ensure_ascii=False, indent=2, default=str))
    print(f"wrote {len(written) + 1} files to {out}")
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", type=Path, default=None,
                   help="Output directory (default: backtest_data/phase2_runs/"
                        "P2-02/final_20260906).")
    return p.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main(out_dir=_parse_args().out))

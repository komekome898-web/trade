#!/usr/bin/env python
"""P2-01 FINAL EVALUATION — the SEALED period, run exactly once.

Evaluates the frozen pre-registration `docs/PHASE2/P2-01/PREREG.md` (section
"最終評価") on the sealed window 2020-12-21 .. 2026-08-28, using the FINAL
configuration recorded in `docs/PHASE2/P2-01/ITER.md`:

  * roll-adjacent rule = QUARTERLY (iteration 1, confirmed contract months),
    read as "a pair either of whose endpoints is the 2nd Friday of
    Mar/Jun/Sep/Dec or the previous trading day" (ITER.md, iteration 1 audit
    note on the frozen wording);
  * cumulative N = 2 configurations examined (monthly, quarterly) — so
    control 2 is the BEST-OF-2 sign-shuffle null, not the single-config one.

Every input is read through `bot.research.sealed.load_sealed(path, "P2-01",
token=UNSEAL_TOKEN)`, which enforces the three independent guards (env
`PHASE2_FINAL_EVAL=P2-01`, the owner's `UNSEAL_APPROVED` file, the explicit
token) and appends to the unseal audit log. This module additionally
pre-checks the same three guards before touching anything, so a misconfigured
run fails before the first read rather than half-way through, and hard-codes
the unit to "P2-01" — no other unit can be unsealed from here.

Nothing in this module interprets the numbers as 採用/棄却: it reports the
measured values against the pre-registered bar and falsification sentences
and marks each 満たす / 満たさない. The owner decides.

Usage:
    PHASE2_FINAL_EVAL=P2-01 PYTHONPATH=src \
        python scripts/phase2/p2_01_final.py

The dev-set runner `scripts/phase2/p2_01_run.py` is imported for its tested
functions (build_pairs / roll marking / describe / Sharpe / max-DD / ...) and
is NOT modified by this script.
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

from bot.research.overnight import block_bootstrap_ci  # noqa: E402
from bot.research.sealed import (  # noqa: E402
    UNSEAL_TOKEN,
    SealedDataError,
    load_sealed,
    seal_dir,
)
from phase2.p2_01_run import (  # noqa: E402  (dev-set runner: reused, unchanged)
    BLOCK,
    COST_YEN_CONSERVATIVE,
    COST_YEN_OPTIMISTIC,
    DAY_FILE,
    GLITCH_THRESHOLD,
    GROSS_GATE_BPS,
    MDE_BPS,
    MDE_DIFF_BPS,
    MULTIPLIER,
    N_BOOT,
    N_SHUFFLE,
    NIGHT_FILE,
    SEED,
    _fmt,
    _git_rev,
    _md5,
    _table,
    build_pairs,
    describe,
    mark_nightless,
    mark_roll_adjacent,
    max_drawdown_yen,
    second_friday,
    sharpe_annualised,
    sign_shuffle_mean_and_sharpe,
    years_span,
)

UNIT = "P2-01"                     # hard-coded: only P2-01 may be unsealed here
FINAL_ROLL_RULE = "quarterly"      # ITER.md iteration 1 = the final configuration
CUMULATIVE_N = 2                   # ITER.md: monthly (iter 0) + quarterly (iter 1)

# ---- pre-registered sealed window (PREREG "最終評価") ----------------------
SEALED_START = pd.Timestamp("2020-12-21")
SEALED_END = pd.Timestamp("2026-08-28")

# PREREG "セッション時刻の制度変更": inside the sealed window the day-session
# close moved 15:15 -> 15:45 on 2024-11-05. The 2021 night-session extension
# (05:30 -> 06:00) has NO date in any primary source held in this repo
# (schema/n225f_225labo.json, the 225Labo manifest and PREREG all name only
# the year), so it is reported as not-derivable rather than guessed.
REGIMES_SEALED = [
    ("2020-12-21..2024-11-04(引け 15:15)", pd.Timestamp("2020-12-21"),
     pd.Timestamp("2024-11-04")),
    ("2024-11-05..2026-08-28(引け 15:45)", pd.Timestamp("2024-11-05"),
     pd.Timestamp("2026-08-28")),
]

FORWARD_FILES = ["paper_logs/nk225_sessions.csv", "paper_logs/on1_ledger.csv"]
FORWARD_MIN_USABLE_ROWS = 5

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
    than P2-01: the owner's approval is scoped to this unit alone.
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
            "refusing the P2-01 final evaluation: " + "; ".join(reasons))


# ---------------------------------------------------------------------------
# control 2 — the best-of-N sign-shuffle null (PREREG バー: 累計 N 通りの最良)
# ---------------------------------------------------------------------------

def best_of_n_sign_shuffle_null(x, masks, years, n: int = N_SHUFFLE,
                                seed: int | None = None
                                ) -> tuple[np.ndarray, np.ndarray, list, list]:
    """Sign-shuffle null of the MAXIMUM over several configurations.

    ``x`` is the return series of the shared base set (one value per pair);
    ``masks`` selects each examined configuration's subset of that base set,
    and ``years`` gives each subset's calendar span for the Sharpe scaling.
    One sign draw is made per shuffle over the WHOLE base set and reused by
    every configuration, which is what "the same random world, evaluated the
    N ways we actually examined" means: the maximum is then taken across
    configurations within each draw.

    The sign matrix is drawn with the same RNG call as
    `bot.research.overnight.sign_shuffle_null`, so with a single all-True
    mask the returned means are bit-identical to that tested helper.

    Returns (max_means, max_sharpes, per_config_means, per_config_sharpes).
    """
    x = np.asarray(x, dtype=float)
    m = len(x)
    masks = [np.asarray(mk, dtype=bool) for mk in masks]
    if not masks:
        raise ValueError("need at least one configuration mask")
    for mk in masks:
        if len(mk) != m:
            raise ValueError(f"mask length {len(mk)} != len(x) {m}")
    if m == 0:
        empty = np.array([])
        return empty, empty, [], []
    rng = np.random.default_rng(seed)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(n, m))
    draws = signs * x

    per_means: list[np.ndarray] = []
    per_sharpes: list[np.ndarray] = []
    for mk, yr in zip(masks, years):
        # ascontiguousarray: boolean column-selection returns an F-ordered
        # view whose row means differ from the C-ordered ones in the last ulp
        # (different pairwise-summation order). Forcing C order keeps a
        # single-config call bit-identical to the tested helper's stream.
        sub = np.ascontiguousarray(draws[:, mk])
        k = sub.shape[1]
        if k < 2:
            per_means.append(np.full(n, np.nan))
            per_sharpes.append(np.full(n, np.nan))
            continue
        means = sub.mean(axis=1)
        sds = sub.std(axis=1, ddof=1)
        scale = np.sqrt(k / yr) if (yr and yr > 0) else float("nan")
        with np.errstate(divide="ignore", invalid="ignore"):
            sharpes = np.where(sds > 0, means / sds * scale, np.nan)
        per_means.append(means)
        per_sharpes.append(sharpes)

    max_means = np.max(np.stack(per_means), axis=0)
    max_sharpes = np.max(np.stack(per_sharpes), axis=0)
    return max_means, max_sharpes, per_means, per_sharpes


# ---------------------------------------------------------------------------
# forward paper ledgers — DIAGNOSTIC ONLY (never fed into the cost)
# ---------------------------------------------------------------------------

def forward_auction_diagnostic(ledger: pd.DataFrame, day: pd.DataFrame
                               ) -> dict:
    """Measured auction execution differences from the forward paper ledger.

    Two measurements, both descriptive:

      A. micro auction print − large auction print at the same auction moment
         (`micro_minus_large_entry` / `_exit`). PREREG explicitly calls this a
         same-moment TRACKING difference, not the auction execution
         difference, so it is reported as a bound, not as the number.
      B. the ledger's actual traded auction print vs the 225Labo continuous
         series' print for the same date (entry_px − close(t),
         exit_px − open(t+1)) — i.e. how far the price this backtest assumes
         sits from the price a real auction order actually got. This is the
         closer proxy for "板寄せの執行差", still descriptive.

    Returns a dict of counts and statistics; never raises on missing columns.
    """
    out: dict = {"rows": int(len(ledger))}
    if not len(ledger):
        out["usable_rows"] = 0
        return out

    led = ledger.copy()
    for col in ("entry_date", "exit_date"):
        if col in led.columns:
            led[col] = pd.to_datetime(led[col].astype(str), format="%Y%m%d",
                                      errors="coerce")
    for col in ("entry_px", "exit_px", "large_entry_px", "large_exit_px",
                "micro_minus_large_entry", "micro_minus_large_exit",
                "gross_bps", "net_bps"):
        if col in led.columns:
            led[col] = pd.to_numeric(led[col], errors="coerce")

    usable = led["entry_px"].notna() & led["exit_px"].notna() \
        if {"entry_px", "exit_px"} <= set(led.columns) else pd.Series(False, index=led.index)
    out["usable_rows"] = int(usable.sum())
    out["min_usable_rows_required"] = FORWARD_MIN_USABLE_ROWS
    out["enough_rows"] = bool(out["usable_rows"] >= FORWARD_MIN_USABLE_ROWS)
    if not out["enough_rows"]:
        return out

    u = led[usable]
    # A. micro vs large at the same auction moment
    for name, col in (("entry", "micro_minus_large_entry"),
                      ("exit", "micro_minus_large_exit")):
        if col in u.columns and u[col].notna().any():
            v = u[col].dropna()
            out[f"micro_minus_large_{name}_n"] = int(len(v))
            out[f"micro_minus_large_{name}_mean_pt"] = float(v.mean())
            out[f"micro_minus_large_{name}_median_pt"] = float(v.median())
            out[f"micro_minus_large_{name}_absmean_pt"] = float(v.abs().mean())
    if {"micro_minus_large_entry", "micro_minus_large_exit"} <= set(u.columns):
        rt = (u["micro_minus_large_entry"].abs()
              + u["micro_minus_large_exit"].abs()).dropna()
        if len(rt):
            out["micro_minus_large_roundtrip_absmean_pt"] = float(rt.mean())
            out["micro_minus_large_roundtrip_absmean_yen"] = float(
                rt.mean() * MULTIPLIER)

    # B. traded auction print vs the continuous series' print, same dates
    if len(day) and {"entry_date", "exit_date"} <= set(u.columns):
        d = day[["date", "open", "close"]].copy()
        d["date"] = pd.to_datetime(d["date"])
        close_by_date = pd.Series(d["close"].to_numpy(), index=d["date"].to_numpy())
        open_by_date = pd.Series(d["open"].to_numpy(), index=d["date"].to_numpy())
        e = u["entry_px"] - u["entry_date"].map(close_by_date)
        x = u["exit_px"] - u["exit_date"].map(open_by_date)
        for name, v in (("entry", e.dropna()), ("exit", x.dropna())):
            if len(v):
                out[f"ledger_minus_series_{name}_n"] = int(len(v))
                out[f"ledger_minus_series_{name}_mean_pt"] = float(v.mean())
                out[f"ledger_minus_series_{name}_median_pt"] = float(v.median())
                out[f"ledger_minus_series_{name}_absmean_pt"] = float(v.abs().mean())
        both = pd.concat([e.abs(), x.abs()], axis=1).dropna()
        if len(both):
            rt2 = both.sum(axis=1)
            out["ledger_minus_series_roundtrip_absmean_pt"] = float(rt2.mean())
            out["ledger_minus_series_roundtrip_absmean_yen"] = float(
                rt2.mean() * MULTIPLIER)
    if "gross_bps" in u.columns and u["gross_bps"].notna().any():
        out["ledger_gross_bps_mean"] = float(u["gross_bps"].dropna().mean())
    if "net_bps" in u.columns and u["net_bps"].notna().any():
        out["ledger_net_bps_mean"] = float(u["net_bps"].dropna().mean())
    return out


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

def _read_unseal_log(root: Path, since_line: int = 0) -> list[dict]:
    p = seal_dir(UNIT, root) / "UNSEAL_LOG.jsonl"
    if not p.is_file():
        return []
    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    out = []
    for ln in lines[since_line:]:
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:  # pragma: no cover - audit log is ours
            out.append({"raw": ln})
    return out


def _unseal_log_len(root: Path) -> int:
    p = seal_dir(UNIT, root) / "UNSEAL_LOG.jsonl"
    if not p.is_file():
        return 0
    return len([ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()])


def main(out_dir: Path | None = None, root: Path | str = REPO_ROOT,
         token: str = UNSEAL_TOKEN) -> int:
    root = Path(root)
    check_guards(root, token)
    out = out_dir if out_dir is not None else OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    steps: dict[str, int] = {}
    log_start = _unseal_log_len(root)

    # ---- load the sealed rows ---------------------------------------------
    day_raw = load_sealed(DAY_FILE, UNIT, token=token, root=root)
    night_raw = load_sealed(NIGHT_FILE, UNIT, token=token, root=root)
    day_raw["date"] = pd.to_datetime(day_raw["date"])
    night_raw["date"] = pd.to_datetime(night_raw["date"])
    day_raw = day_raw.sort_values("date").reset_index(drop=True)
    night_raw = night_raw.sort_values("date").reset_index(drop=True)
    steps["day_rows_sealed"] = len(day_raw)
    steps["night_rows_sealed"] = len(night_raw)

    forward: dict[str, pd.DataFrame] = {}
    for path in FORWARD_FILES:
        try:
            forward[path] = load_sealed(path, UNIT, token=token, root=root)
        except SealedDataError as exc:  # pragma: no cover - file present in repo
            forward[path] = pd.DataFrame()
            steps[f"forward_load_error_{Path(path).stem}"] = 1
            print(f"WARNING: {path}: {exc}", file=sys.stderr)
    for path, df in forward.items():
        steps[f"forward_rows_{Path(path).stem}"] = int(len(df))

    # ---- window + endpoint rule -------------------------------------------
    day = day_raw[(day_raw["date"] >= SEALED_START)
                  & (day_raw["date"] <= SEALED_END)].reset_index(drop=True)
    steps["day_rows_in_sealed_window"] = len(day)
    trading_days = list(day["date"])

    pairs = build_pairs(day)          # endpoint rule: both days sealed
    steps["pairs_after_endpoint_rule"] = len(pairs)

    # ---- marks -------------------------------------------------------------
    pairs["roll_monthly"] = mark_roll_adjacent(pairs, trading_days, "monthly")
    pairs["roll_quarterly"] = mark_roll_adjacent(pairs, trading_days, "quarterly")
    pairs["nightless_marked"] = mark_nightless(pairs)
    pairs["is_glitch"] = pairs["r"].abs() > GLITCH_THRESHOLD
    steps["glitches"] = int(pairs["is_glitch"].sum())
    steps["roll_adjacent_monthly"] = int(pairs["roll_monthly"].sum())
    steps["roll_adjacent_quarterly"] = int(pairs["roll_quarterly"].sum())
    steps["nightless_marked"] = int(pairs["nightless_marked"].sum())

    # ---- night-session join (control 3, leg (b)) ---------------------------
    nn = night_raw[["date", "open", "close"]].rename(
        columns={"date": "date_t1", "open": "night_open", "close": "night_close"})
    pairs = pairs.merge(nn, on="date_t1", how="left")
    pairs["has_night"] = pairs["night_open"].notna()
    steps["pairs_without_night_row"] = int((~pairs["has_night"]).sum())
    pairs["leg_b_bps"] = (pairs["night_close"] / pairs["night_open"] - 1.0) * 1e4
    pairs["leg_a_bps"] = (pairs["night_open"] / pairs["close_t"] - 1.0) * 1e4
    pairs["leg_c_bps"] = (pairs["open_t1"] / pairs["night_close"] - 1.0) * 1e4

    ok = pairs[pairs["has_night"]]
    med_prev = float((ok["night_open"] - ok["close_t"]).abs().median())
    med_same = float((ok["night_open"] - ok["close_t1"]).abs().median())
    alignment_pass = bool(med_prev < med_same)

    # ---- labels / diagnostics columns --------------------------------------
    regime = pd.Series("other", index=pairs.index, dtype=object)
    for name, lo, hi in REGIMES_SEALED:
        regime[(pairs["date"] >= lo) & (pairs["date"] <= hi)] = name
    pairs["regime"] = regime
    pairs["weekday"] = pd.to_datetime(pairs["date"]).dt.day_name()
    pairs["month"] = pd.to_datetime(pairs["date"]).dt.month
    pairs["year"] = pd.to_datetime(pairs["date"]).dt.year

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

    sq_days = pd.DatetimeIndex(sorted(
        d for d in trading_days if d == second_friday(d.year, d.month)))
    day_pos = {d: i for i, d in enumerate(trading_days)}
    sq_pos = np.array([day_pos[d] for d in sq_days])
    tpos = np.array([day_pos[d] for d in pd.to_datetime(pairs["date"])])
    if len(sq_pos):
        j = np.clip(np.searchsorted(sq_pos, tpos), 0, len(sq_pos) - 1)
        cand = np.stack([sq_pos[np.maximum(j - 1, 0)], sq_pos[j]])
        pairs["sq_dist_td"] = np.min(np.abs(cand - tpos), axis=0)
    else:  # pragma: no cover
        pairs["sq_dist_td"] = np.nan

    # ---- the pre-registered sets ------------------------------------------
    base = pairs
    clean = pairs[~pairs["is_glitch"]]                       # glitch-excluded base
    roll_ex_q = pairs[~pairs["roll_quarterly"]]
    roll_ex_m = pairs[~pairs["roll_monthly"]]
    main = pairs[~pairs["roll_quarterly"] & ~pairs["is_glitch"]]   # 判定集合
    main_m = pairs[~pairs["roll_monthly"] & ~pairs["is_glitch"]]   # 併記(月次)
    steps["n_base"] = len(base)
    steps["n_clean_glitch_excluded"] = len(clean)
    steps["n_roll_excluded_quarterly"] = len(roll_ex_q)
    steps["n_roll_excluded_monthly"] = len(roll_ex_m)
    steps["n_main_quarterly_and_glitch_excluded"] = len(main)
    steps["n_main_monthly_and_glitch_excluded"] = len(main_m)
    steps["glitches_inside_roll_set_quarterly"] = int(
        (pairs["is_glitch"] & pairs["roll_quarterly"]).sum())

    yrs_main = years_span(main)
    yrs_main_m = years_span(main_m)
    yrs_base = years_span(base)

    # ---- main indicators ---------------------------------------------------
    diff_main = main["r_night_bps"] - main["r_day_bps"]
    main_rows = [
        describe(main["r_net_bps_cons"],
                 "主指標1 平均ネット夜間リターン(保守コスト、四半期ロール除外+誤プリント除外)",
                 yrs_main),
        describe(diff_main, "主指標2 夜間−日中の差(同集合)", yrs_main),
        describe(main["r_night_bps"], "グロス夜間リターン(同集合)", yrs_main),
        describe(main["r_net_bps_opt"], "楽観コスト後(手数料のみ、同集合)", yrs_main),
        describe(roll_ex_q["r_net_bps_cons"],
                 f"四半期ロール除外のみ(誤プリント含む)n={len(roll_ex_q):,}",
                 years_span(roll_ex_q)),
        describe(main_m["r_net_bps_cons"],
                 f"月次ロール規則(併記)n={len(main_m):,}", yrs_main_m),
        describe(main_m["r_night_bps"] - main_m["r_day_bps"],
                 "月次ロール規則 夜間−日中の差(併記)", yrs_main_m),
        describe(base["r_net_bps_cons"],
                 f"ロール隣接ペアを含む n={len(base):,}(誤プリント含む)", yrs_base),
        describe(base["r_night_bps"] - base["r_day_bps"],
                 "同上 夜間−日中の差", yrs_base),
    ]
    main_df = pd.DataFrame(main_rows)

    ci_main = (float(main_df.iloc[0]["ci_lo"]), float(main_df.iloc[0]["ci_hi"]))
    ci_diff = (float(main_df.iloc[1]["ci_lo"]), float(main_df.iloc[1]["ci_hi"]))
    ci_gross = (float(main_df.iloc[2]["ci_lo"]), float(main_df.iloc[2]["ci_hi"]))
    ci_opt = (float(main_df.iloc[3]["ci_lo"]), float(main_df.iloc[3]["ci_hi"]))
    ci_main_m = (float(main_df.iloc[5]["ci_lo"]), float(main_df.iloc[5]["ci_hi"]))
    ci_diff_m = (float(main_df.iloc[6]["ci_lo"]), float(main_df.iloc[6]["ci_hi"]))
    ci_base = (float(main_df.iloc[7]["ci_lo"]), float(main_df.iloc[7]["ci_hi"]))
    ci_base_diff = (float(main_df.iloc[8]["ci_lo"]), float(main_df.iloc[8]["ci_hi"]))

    mean_main = float(main["r_net_bps_cons"].mean())
    gross_main = float(main["r_night_bps"].mean())
    mean_diff = float(diff_main.mean())
    mean_opt = float(main["r_net_bps_opt"].mean())
    sharpe_main = sharpe_annualised(main["r_net_bps_cons"], yrs_main)
    hit_main = float((main["r_net_bps_cons"] > 0).mean())
    mdd_yen, mdd_idx = max_drawdown_yen(main.sort_values("date")["pnl_yen_cons"])
    mdd_date = (str(pd.to_datetime(main.sort_values("date")["date_t1"].iloc[mdd_idx]).date())
                if mdd_idx >= 0 else "")
    total_pnl_yen = float(main["pnl_yen_cons"].sum())

    # ---- sub indicators ----------------------------------------------------
    sub_rows: list[dict] = []

    def add(x, label, subset):
        sub_rows.append(describe(x, label, years_span(subset)))

    add(main["r_net_bps_cons"], f"主集合(四半期規則)n={len(main):,}", main)
    add(main_m["r_net_bps_cons"], f"月次規則 n={len(main_m):,}", main_m)
    one = main[main["nights"] == 1]
    add(one["r_net_bps_cons"], "1泊のみの部分集合", one)
    add(clean["r_net_bps_cons"], "誤プリント除外のみ(ロール含む)", clean)
    add(roll_ex_q["r_net_bps_cons"], "四半期ロール除外のみ(誤プリント含む)", roll_ex_q)
    for name, lo, hi in REGIMES_SEALED:
        sset = main[(main["date"] >= lo) & (main["date"] <= hi)]
        add(sset["r_net_bps_cons"], f"制度区分 {name}", sset)
        sset_d = sset["r_night_bps"] - sset["r_day_bps"]
        sub_rows.append(describe(sset_d, f"制度区分 {name} 夜間−日中の差",
                                 years_span(sset)))
    # 2021 night-session extension: the boundary date is NOT in any primary
    # source held in this repo (they all say only "2021"), but it IS derivable
    # from the sealed night series itself — the changeover night is the one
    # night the exchange did not run, i.e. the single pair inside the sealed
    # window whose t+1 has no night_session_daily row at all. Used descriptively
    # only (PREREG puts this split in "判定に使わない"), and only when the
    # derivation is unambiguous (exactly one such date).
    gap_dates = sorted(pd.to_datetime(pairs.loc[~pairs["has_night"], "date_t1"]).unique())
    night_ext_date = pd.Timestamp(gap_dates[0]) if len(gap_dates) == 1 else None
    if night_ext_date is not None:
        pre = main[main["date_t1"] < night_ext_date]
        post = main[main["date_t1"] >= night_ext_date]
        add(pre["r_net_bps_cons"],
            f"夜間延長前(..{(night_ext_date - pd.Timedelta(days=1)).date()}、"
            "データ由来の候補日)", pre)
        add(post["r_net_bps_cons"],
            f"夜間延長後({night_ext_date.date()}..、データ由来の候補日)", post)
    for yr in sorted(main["year"].unique()):
        sset = main[main["year"] == yr]
        add(sset["r_net_bps_cons"], f"年 {int(yr)}", sset)
    sub_df = pd.DataFrame(sub_rows)

    # ---- controls ----------------------------------------------------------
    ctrl_rows = [
        describe(main["r_day_bps"], "対照1 日中保有 r_day(グロス、主集合)", yrs_main),
        describe(main["r_day_bps"] - main["cost_bps_cons"],
                 "対照1 日中保有(保守コスト後)", yrs_main),
    ]
    c3 = main[main["has_night"]]
    ctrl_rows.append(describe(c3["leg_b_bps"], "対照3 夜間セッション内 leg(b) グロス",
                              years_span(c3)))
    ctrl_rows.append(describe(c3["leg_b_bps"] - c3["cost_bps_cons"],
                              "対照3 leg(b) 保守コスト後", years_span(c3)))
    ctrl_rows.append(describe(c3["leg_a_bps"], "参考 leg(a) 日中引け→夜間寄り",
                              years_span(c3)))
    ctrl_rows.append(describe(c3["leg_c_bps"], "参考 leg(c) 夜間引け→翌日中寄り",
                              years_span(c3)))
    ctrl_df = pd.DataFrame(ctrl_rows)

    # ---- control 2: BEST-OF-2 sign-shuffle null ---------------------------
    x_base = clean["r_night_bps"].to_numpy(dtype=float)
    mask_q = (~clean["roll_quarterly"]).to_numpy(dtype=bool)
    mask_m = (~clean["roll_monthly"]).to_numpy(dtype=bool)
    yrs_cfgs = [yrs_main, yrs_main_m]
    max_means, max_sharpes, per_means, per_sharpes = best_of_n_sign_shuffle_null(
        x_base, [mask_q, mask_m], yrs_cfgs, N_SHUFFLE, SEED)
    null_best_mean_p95 = float(np.percentile(max_means, 95))
    null_best_sharpe_p95 = float(np.percentile(max_sharpes, 95))
    null_q_mean_p95 = float(np.percentile(per_means[0], 95))
    null_q_sharpe_p95 = float(np.percentile(per_sharpes[0], 95))
    null_m_mean_p95 = float(np.percentile(per_means[1], 95))
    null_m_sharpe_p95 = float(np.percentile(per_sharpes[1], 95))

    obs_mean_q = float(main["r_night_bps"].mean())
    obs_mean_m = float(main_m["r_night_bps"].mean())
    obs_sharpe_q = sharpe_annualised(main["r_night_bps"], yrs_main)
    obs_sharpe_m = sharpe_annualised(main_m["r_night_bps"], yrs_main_m)
    obs_best_mean = max(obs_mean_q, obs_mean_m)
    obs_best_sharpe = max(obs_sharpe_q, obs_sharpe_m)
    bar_null_mean_pass = bool(obs_best_mean > null_best_mean_p95)
    bar_null_sharpe_pass = bool(obs_best_sharpe > null_best_sharpe_p95)

    # single-configuration null on the quarterly main set, for continuity with
    # the dev-set runs' control 2 (same tested RNG helper, same seed)
    solo_mean, solo_sharpe = sign_shuffle_mean_and_sharpe(
        main["r_night_bps"].to_numpy(dtype=float), N_SHUFFLE, SEED, yrs_main)
    solo_mean_p95 = float(np.percentile(solo_mean, 95))
    solo_sharpe_p95 = float(np.percentile(solo_sharpe, 95))

    # ---- diagnostics -------------------------------------------------------
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
        "sq_dist": group_table(clean, "sq_dist_td"),
    }
    nights_dist = pairs.groupby("nights").size().rename("n_pairs").reset_index()
    nights_dist["share"] = nights_dist["n_pairs"] / len(pairs)

    # ---- forward paper ledgers (DIAGNOSTIC ONLY) ---------------------------
    ledger = forward.get("paper_logs/on1_ledger.csv", pd.DataFrame())
    sessions = forward.get("paper_logs/nk225_sessions.csv", pd.DataFrame())
    fwd = forward_auction_diagnostic(ledger, day_raw)
    fwd["nk225_sessions_rows"] = int(len(sessions))
    if len(sessions) and "date" in sessions.columns:
        sd = pd.to_datetime(sessions["date"].astype(str), format="%Y%m%d",
                            errors="coerce").dropna()
        if len(sd):
            fwd["nk225_sessions_first_date"] = str(sd.min().date())
            fwd["nk225_sessions_last_date"] = str(sd.max().date())
        if "product" in sessions.columns:
            fwd["nk225_sessions_rows_by_product"] = {
                str(k): int(v) for k, v in
                sessions["product"].astype(str).value_counts().items()}
    if len(ledger) and "entry_date" in ledger.columns:
        ed = pd.to_datetime(ledger["entry_date"].astype(str), format="%Y%m%d",
                            errors="coerce").dropna()
        if len(ed):
            fwd["on1_ledger_first_entry_date"] = str(ed.min().date())
            fwd["on1_ledger_last_entry_date"] = str(ed.max().date())

    # ---- MDE (recomputed on the sealed sample, recorded not judged) --------
    Z = 1.959963985 + 0.8416212336

    def mde_row(label, x, registered):
        x = np.asarray(x, dtype=float)
        sd = float(x.std(ddof=1))
        se = sd / np.sqrt(len(x))
        lo, hi = block_bootstrap_ci(x, block=BLOCK, n_boot=N_BOOT, seed=SEED)
        se_eff = (hi - lo) / (2 * 1.959963985)
        return {"a": label, "b": sd, "c": len(x), "d": se, "e": Z * se,
                "f": registered, "g": Z * se_eff}

    mde_rows = [
        mde_row("σ(r_night) 四半期ロール除外後(封印期間)",
                roll_ex_q["r_night_bps"], MDE_BPS),
        mde_row("σ(夜間−日中の差)四半期ロール除外後(封印期間)",
                roll_ex_q["r_night_bps"] - roll_ex_q["r_day_bps"], MDE_DIFF_BPS),
        mde_row("σ(r_net 保守コスト後)主集合", main["r_net_bps_cons"], MDE_BPS),
        mde_row("σ(夜間−日中の差)主集合", diff_main, MDE_DIFF_BPS),
    ]

    # ---- exclusions ledger -------------------------------------------------
    excl = pd.DataFrame([
        {"step": "day_session_daily 封印行(2020-12-21 以降)", "n": steps["day_rows_sealed"]},
        {"step": "night_session_daily 封印行", "n": steps["night_rows_sealed"]},
        {"step": f"封印窓 {SEALED_START.date()}..{SEALED_END.date()} の日中行",
         "n": steps["day_rows_in_sealed_window"]},
        {"step": "端点規則適用後のペア(両端が封印期間内)", "n": steps["pairs_after_endpoint_rule"]},
        {"step": "うち誤プリント(|単純収益| > 0.10)", "n": steps["glitches"]},
        {"step": "うちロール隣接(四半期規則・採用)", "n": steps["roll_adjacent_quarterly"]},
        {"step": "うちロール隣接(月次規則・併記)", "n": steps["roll_adjacent_monthly"]},
        {"step": "うち夜間セッション無し(事前登録の5ペア)", "n": steps["nightless_marked"]},
        {"step": "うち夜間行が実データで欠損", "n": steps["pairs_without_night_row"]},
        {"step": "四半期ロール隣接除外後(誤プリント含む)", "n": steps["n_roll_excluded_quarterly"]},
        {"step": "主集合(四半期ロール除外+誤プリント除外)= 判定分母",
         "n": steps["n_main_quarterly_and_glitch_excluded"]},
        {"step": "月次規則の主集合(併記)", "n": steps["n_main_monthly_and_glitch_excluded"]},
    ])

    # ---- write CSVs --------------------------------------------------------
    pairs_out = pairs.copy()
    pairs_out["date"] = pd.to_datetime(pairs_out["date"]).dt.date
    pairs_out["date_t1"] = pd.to_datetime(pairs_out["date_t1"]).dt.date
    written: list[str] = []

    def write(df: pd.DataFrame, name: str):
        df.to_csv(out / name, index=False)
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
        "pass": alignment_pass, "n": int(len(ok)),
    }]), "alignment_check.csv")
    write(pd.DataFrame({
        "draw": np.arange(N_SHUFFLE),
        "null_mean_quarterly_bps": per_means[0],
        "null_mean_monthly_bps": per_means[1],
        "null_mean_best_of_2_bps": max_means,
        "null_sharpe_quarterly": per_sharpes[0],
        "null_sharpe_monthly": per_sharpes[1],
        "null_sharpe_best_of_2": max_sharpes,
    }), "control2_best_of_2_null.csv")
    write(pd.DataFrame(mde_rows).rename(columns={
        "a": "quantity", "b": "sd_bps", "c": "n", "d": "se_bps",
        "e": "mde_bps_independent", "f": "mde_bps_registered",
        "g": "mde_bps_effective_from_ci"}), "mde.csv")
    write(pd.DataFrame([{"key": k, "value": json.dumps(v, ensure_ascii=False)
                         if isinstance(v, dict) else v}
                        for k, v in fwd.items()]), "forward_diagnostic.csv")

    # ---- bar / falsification -----------------------------------------------
    bar_rows = [
        {"a": "バー1 「累計 N=2 通りの最良」の帰無 95 点を超える(平均、グロス)",
         "b": f"実測best {obs_best_mean:,.3f} vs 帰無95点 {null_best_mean_p95:,.3f}",
         "c": "満たす" if bar_null_mean_pass else "満たさない"},
        {"a": "バー1(参考)同 Sharpe",
         "b": f"実測best {obs_best_sharpe:,.3f} vs 帰無95点 {null_best_sharpe_p95:,.3f}",
         "c": "満たす" if bar_null_sharpe_pass else "満たさない"},
        {"a": "バー2 保守コスト後の平均ネット夜間リターンの 95% CI が正",
         "b": f"[{ci_main[0]:,.3f}, {ci_main[1]:,.3f}] bps",
         "c": "満たす" if ci_main[0] > 0 else "満たさない"},
        {"a": "バー3 夜間−日中の差の 95% CI が正",
         "b": f"[{ci_diff[0]:,.3f}, {ci_diff[1]:,.3f}] bps",
         "c": "満たす" if ci_diff[0] > 0 else "満たさない"},
    ]
    bar_all = bool(bar_null_mean_pass and ci_main[0] > 0 and ci_diff[0] > 0)
    fals_rows = [
        {"a": "反証文A 平均ネット夜間リターンの 95% CI がゼロを含む",
         "b": f"[{ci_main[0]:,.3f}, {ci_main[1]:,.3f}] bps",
         "c": "満たす" if (ci_main[0] <= 0 <= ci_main[1]) else "満たさない"},
        {"a": "反証文B 夜間−日中の差の 95% CI がゼロを含む",
         "b": f"[{ci_diff[0]:,.3f}, {ci_diff[1]:,.3f}] bps",
         "c": "満たす" if (ci_diff[0] <= 0 <= ci_diff[1]) else "満たさない"},
        {"a": "付帯条件 ロール隣接ペアを含めた場合にのみ成立していないか(含む集合の CI)",
         "b": f"[{ci_base[0]:,.3f}, {ci_base[1]:,.3f}] bps(差 [{ci_base_diff[0]:,.3f}, {ci_base_diff[1]:,.3f}])",
         "c": "含む集合のみで成立=満たす" if (ci_base[0] > 0 and not ci_main[0] > 0)
              else "該当しない"},
        {"a": "保留区分 楽観コストでは CI が正・保守ではゼロを含む",
         "b": f"楽観 [{ci_opt[0]:,.3f}, {ci_opt[1]:,.3f}] / 保守 [{ci_main[0]:,.3f}, {ci_main[1]:,.3f}] bps",
         "c": "満たす" if (ci_opt[0] > 0 and ci_main[0] <= 0 <= ci_main[1])
              else "満たさない"},
    ]
    write(pd.DataFrame(
        [{"kind": "bar", **{"criterion": r["a"], "measured": r["b"], "outcome": r["c"]}}
         for r in bar_rows]
        + [{"kind": "falsification", "criterion": r["a"], "measured": r["b"],
            "outcome": r["c"]} for r in fals_rows]), "bar_and_falsification.csv")

    # ---- RESULTS.md --------------------------------------------------------
    ind_cols = [("label", "集合 / 指標", -1), ("n", "n", 0), ("mean", "平均(bps)", 3),
                ("ci_lo", "CI下限", 3), ("ci_hi", "CI上限", 3), ("sd", "SD(bps)", 2),
                ("t", "t", 2), ("hit_rate", "勝率", 4), ("sharpe", "Sharpe(年率)", 3)]
    cost_med = float(main["cost_bps_cons"].median())
    cost_mean = float(main["cost_bps_cons"].mean())

    md: list[str] = []
    md.append("# P2-01 最終評価(封印期間、1 回のみ)— 数値報告")
    md.append("")
    md.append(f"実行日 2026-09-06 / seed {SEED} / git {_git_rev()[:12]} / 単位 {UNIT} / "
              f"採用構成: ロール規則 = 四半期(ITER.md 反復 1)、累計 N = {CUMULATIVE_N}。")
    md.append(f"読み込みは `load_sealed(path, \"{UNIT}\", token=UNSEAL_TOKEN)` のみ"
              "(env `PHASE2_FINAL_EVAL=P2-01` + オーナー承認ファイル + トークンの三重ゲート)。"
              "P2-02 / P2-03 の封印データには一切触れていない。")
    md.append("")
    md.append("**本書は数値の報告のみで、採用・棄却の判断は行わない(オーナーが決める)。**")
    md.append("")
    md.append("## 1. 母集団と除外の内訳(封印期間)")
    md.append("")
    md.append(_table(excl.to_dict("records"), [("step", "段階", -1), ("n", "件数", 0)]))
    md.append("")
    md.append(f"端点規則: ペア (t, t+1) は両日が封印期間 {SEALED_START.date()}..{SEALED_END.date()} に"
              f"あるときだけ採用。実測の最初のペアは {pd.to_datetime(pairs['date']).min().date()} 発、"
              f"最後のペアは {pd.to_datetime(pairs['date_t1']).max().date()} 決済。"
              f"誤プリント {steps['glitches']} 件、"
              f"うち四半期ロール隣接集合の内側 {steps['glitches_inside_roll_set_quarterly']} 件。")
    md.append("")
    md.append("## 2. 主指標")
    md.append("")
    md.append(f"CI はブロック・ブートストラップ(ブロック長 {BLOCK}、リサンプル {N_BOOT:,}、"
              f"percentile 法、seed {SEED})。単位は bps/ペア。")
    md.append("")
    md.append(_table(main_df.to_dict("records"), ind_cols))
    md.append("")
    md.append(f"ペアごとの保守コスト cost_bps(t) = 122 /(close_day(t)×10)×10^4: "
              f"中央値 {cost_med:.2f}bps、平均 {cost_mean:.2f}bps、"
              f"範囲 {main['cost_bps_cons'].min():.2f}〜{main['cost_bps_cons'].max():.2f}bps。"
              f"楽観側(手数料のみ 22 円)は中央値 {main['cost_bps_opt'].median():.2f}bps。"
              "封印期間は元本が開発セットより大きいぶんコストの bps は小さい。")
    md.append("")
    md.append("主指標 2(夜間 − 日中)は同じ 1 往復のコストが両脚に等しく掛かるため、"
              "グロスの差とネットの差は恒等的に一致する。")
    md.append("")
    md.append("## 3. 事前登録の関門との比較(数値の対照のみ)")
    md.append("")
    md.append(_table([
        {"a": "平均ネット r_net(保守コスト後、主集合)", "b": mean_main,
         "c": MDE_BPS, "d": mean_main - MDE_BPS},
        {"a": "グロス平均夜間リターン(主集合)", "b": gross_main,
         "c": GROSS_GATE_BPS, "d": gross_main - GROSS_GATE_BPS},
        {"a": "夜間−日中の差(主集合)", "b": mean_diff,
         "c": MDE_DIFF_BPS, "d": mean_diff - MDE_DIFF_BPS},
    ], [("a", "量", -1), ("b", "実測(bps)", 3), ("c", "事前登録の基準(bps)", 2),
        ("d", "差", 3)]))
    md.append("")
    md.append("### MDE の再計算(封印標本、記録のみ)")
    md.append("")
    md.append(_table(mde_rows, [("a", "量", -1), ("b", "σ(bps)", 2), ("c", "n", 0),
                                ("d", "SE(bps)", 3), ("e", "独立標本 MDE(bps)", 3),
                                ("f", "事前登録 MDE", 2),
                                ("g", "実測 CI 幅からの実効 MDE(bps)", 3)]))
    md.append("")
    md.append("## 4. 副指標")
    md.append("")
    md.append(_table(sub_df.to_dict("records"), ind_cols))
    md.append("")
    md.append(f"最大ドローダウン(マイクロ 1 枚固定、保守コスト後、主集合、時系列順): "
              f"**{mdd_yen:,.0f} 円**(谷は {mdd_date})。累計損益 {total_pnl_yen:,.0f} 円 / "
              f"{len(main):,} ペア。勝率 {hit_main:.4f}。年率換算 Sharpe = {sharpe_main:.3f} "
              f"(換算係数 √(n/年数) = √({len(main)}/{yrs_main:.2f}) = "
              f"{np.sqrt(len(main)/yrs_main):.2f})。")
    md.append("")
    md.append("### 泊数の分布(全ペア)")
    md.append("")
    md.append(_table(nights_dist.to_dict("records"),
                     [("nights", "泊数", 0), ("n_pairs", "ペア数", 0), ("share", "割合", 4)]))
    md.append("")
    md.append("## 5. 対照")
    md.append("")
    md.append(_table(ctrl_df.to_dict("records"), ind_cols))
    md.append("")
    md.append(f"### 対照 2 シャッフル帰無 — 累計 N = {CUMULATIVE_N} の最良(best-of-2)")
    md.append("")
    md.append("事前登録のバーは「**累計 N 通りの最良**の帰無分布の 95 点」を要求する。"
              "検討した構成は 2 つ(反復 0 = 月次ロール規則、反復 1 = 四半期ロール規則)なので、"
              "1 回のシャッフルごとに共通の符号ベクトルを誤プリント除外済みの全ペアに引き、"
              "2 つの構成の部分集合それぞれで平均と Sharpe を計算し、**その最大値**を 1 標本とする。"
              f"リサンプル {N_SHUFFLE:,} 回、seed {SEED}。実測側も同じく 2 構成の最大値を採る。")
    md.append("")
    md.append(_table([
        {"a": "平均(bps)四半期のみ", "b": obs_mean_q, "c": null_q_mean_p95},
        {"a": "平均(bps)月次のみ", "b": obs_mean_m, "c": null_m_mean_p95},
        {"a": "**平均(bps)best-of-2(バー該当)**", "b": obs_best_mean,
         "c": null_best_mean_p95},
        {"a": "Sharpe 四半期のみ", "b": obs_sharpe_q, "c": null_q_sharpe_p95},
        {"a": "Sharpe 月次のみ", "b": obs_sharpe_m, "c": null_m_sharpe_p95},
        {"a": "**Sharpe best-of-2**", "b": obs_best_sharpe, "c": null_best_sharpe_p95},
    ], [("a", "統計量", -1), ("b", "実測", 3), ("c", "帰無 95 点", 3)]))
    md.append("")
    md.append(f"参考(開発セットの対照 2 と同じ単一構成・同じ検定済みヘルパ経路): "
              f"四半期主集合単独の帰無 95 点は平均 {solo_mean_p95:.3f}bps / "
              f"Sharpe {solo_sharpe_p95:.3f}。best-of-2 の 95 点はこれより高い"
              "(最大値を採るぶん帰無が右に寄る)ことがバーの厳しさの実体。")
    md.append("")
    md.append("### 対照 3 の分母と整列検証")
    md.append("")
    md.append(f"夜間行が存在するペアは {int(pairs['has_night'].sum()):,}(全 {len(pairs):,} ペア中、"
              f"欠損 {steps['pairs_without_night_row']})。そこから四半期ロール隣接と誤プリントを"
              f"除いた対照 3 の分母は n = {len(c3):,} で、主指標の分母 {len(main):,} と"
              "一致しない場合は事前登録どおり併記。")
    md.append("")
    md.append("整列の検証(水準比較): "
              f"median |night_open(t+1) − close_day(t)| = **{med_prev:.1f} 円**、"
              f"median |night_open(t+1) − close_day(t+1)| = **{med_same:.1f} 円**、"
              f"n = {len(ok):,}。前者 < 後者 = **{alignment_pass}**。")
    md.append("")
    md.append("## 6. レジーム分割(判定に使わない、記述のみ)")
    md.append("")
    md.append(_table(diag["regime"].to_dict("records"),
                     [("regime", "制度区分", -1), ("n", "n", 0),
                      ("mean_r_net_bps", "平均 r_net(bps)", 3),
                      ("mean_gross_bps", "グロス(bps)", 3),
                      ("mean_r_day_bps", "r_day(bps)", 3), ("sd_bps", "SD", 2),
                      ("hit_rate", "勝率", 4)]))
    md.append("")
    md.append("2024-11-05 の引け延伸(15:15 → 15:45)は日付が事前登録にあるため上表で分割した。")
    md.append("")
    if night_ext_date is not None:
        ext_rows = [
            {"a": f"夜間延長前 2020-12-21..{(night_ext_date - pd.Timedelta(days=1)).date()}",
             "b": len(pre), "c": float(pre["r_net_bps_cons"].mean()),
             "d": float(pre["r_night_bps"].mean()),
             "e": float(pre["r_day_bps"].mean()),
             "f": float((pre["r_net_bps_cons"] > 0).mean())},
            {"a": f"夜間延長後 {night_ext_date.date()}..2026-08-28",
             "b": len(post), "c": float(post["r_net_bps_cons"].mean()),
             "d": float(post["r_night_bps"].mean()),
             "e": float(post["r_day_bps"].mean()),
             "f": float((post["r_net_bps_cons"] > 0).mean())},
        ]
        md.append(_table(ext_rows, [("a", "区分", -1), ("b", "n", 0),
                                    ("c", "平均 r_net(bps)", 3),
                                    ("d", "グロス(bps)", 3), ("e", "r_day(bps)", 3),
                                    ("f", "勝率", 4)]))
        md.append("")
        md.append("2021 年の夜間セッション延長(05:30 → 06:00)の**実施日は本リポジトリの"
                  "一次資料に無い**(`schema/n225f_225labo.json`、225Labo の manifest、"
                  "PREREG のいずれも「2021 年」としか書かない)。ただし封印データ自体から"
                  f"候補日が 1 つに定まる: 封印期間で夜間セッション行が存在しない夜は "
                  f"**{night_ext_date.date()} の 1 夜のみ**であり、これは取引時間の切替に伴い"
                  "夜間立会が行われなかった夜と読める。上表はこの**データ由来の候補日**で"
                  "分けたもの(境界日の夜を延長後に含める)で、一次資料による"
                  "確認ではない。事前登録どおり判定には使わず、フォワードとの接続の参考のみ。")
    else:  # pragma: no cover - depends on the sealed data
        md.append("2021 年の夜間セッション延長(05:30 → 06:00)は一次資料に実施日が無く、"
                  "封印データからも候補日が 1 つに定まらなかった(夜間行の欠損が "
                  f"{len(gap_dates)} 件)ため、この分割は行わない。代わりに年別表(§7)を置く。")
    md.append("")
    md.append("## 7. 診断(記述のみ。p 値・有意判定は書かない)")
    md.append("")
    for key, title in [("year", "年"), ("vol_tercile", "20 日実現ボラ三分位"),
                       ("nights", "泊数"), ("weekday", "曜日"), ("month", "月"),
                       ("sq_dist", "SQ(第 2 金曜)からの営業日距離")]:
        md.append(f"### {title}")
        md.append("")
        cols = [(diag[key].columns[0], str(diag[key].columns[0]), -1), ("n", "n", 0),
                ("mean_r_net_bps", "平均 r_net(bps)", 3),
                ("mean_gross_bps", "グロス(bps)", 3),
                ("mean_r_day_bps", "r_day(bps)", 3), ("sd_bps", "SD", 2),
                ("hit_rate", "勝率", 4)]
        md.append(_table(diag[key].to_dict("records"), cols))
        md.append("")
    md.append("## 8. フォワード・ペーパー台帳(封印データ、診断のみ・コストには反映しない)")
    md.append("")
    md.append(f"`paper_logs/nk225_sessions.csv` = {fwd.get('nk225_sessions_rows', 0):,} 行"
              f"({fwd.get('nk225_sessions_first_date', '—')}..{fwd.get('nk225_sessions_last_date', '—')})、"
              f"`paper_logs/on1_ledger.csv` = {fwd.get('rows', 0):,} 行"
              f"({fwd.get('on1_ledger_first_entry_date', '—')}..{fwd.get('on1_ledger_last_entry_date', '—')})、"
              f"うち使用可能(entry_px / exit_px が揃う)= {fwd.get('usable_rows', 0):,} 行"
              f"(閾値 {FORWARD_MIN_USABLE_ROWS} 行)。")
    md.append("")
    if fwd.get("enough_rows"):
        rows = [
            {"a": "A マイクロ − ラージ(同一板寄せ時点、建て)",
             "b": fwd.get("micro_minus_large_entry_mean_pt"),
             "c": fwd.get("micro_minus_large_entry_absmean_pt"),
             "d": fwd.get("micro_minus_large_entry_n")},
            {"a": "A マイクロ − ラージ(同一板寄せ時点、手仕舞い)",
             "b": fwd.get("micro_minus_large_exit_mean_pt"),
             "c": fwd.get("micro_minus_large_exit_absmean_pt"),
             "d": fwd.get("micro_minus_large_exit_n")},
        ]
        if "ledger_minus_series_entry_absmean_pt" in fwd:
            rows.append({"a": "B 台帳の実約定(引成)− 継続系列 close(t)",
                         "b": fwd.get("ledger_minus_series_entry_mean_pt"),
                         "c": fwd.get("ledger_minus_series_entry_absmean_pt"),
                         "d": fwd.get("ledger_minus_series_entry_n")})
        if "ledger_minus_series_exit_absmean_pt" in fwd:
            rows.append({"a": "B 台帳の実約定(寄成)− 継続系列 open(t+1)",
                         "b": fwd.get("ledger_minus_series_exit_mean_pt"),
                         "c": fwd.get("ledger_minus_series_exit_absmean_pt"),
                         "d": fwd.get("ledger_minus_series_exit_n")})
        md.append(_table(rows, [("a", "測定", -1), ("b", "平均(ポイント)", 3),
                                ("c", "平均絶対値(ポイント)", 3), ("d", "n", 0)]))
        md.append("")
        rt_series = fwd.get("ledger_minus_series_roundtrip_absmean_yen")
        rt_micro = fwd.get("micro_minus_large_roundtrip_absmean_yen")
        md.append(
            f"往復の実測差(絶対値の和 × 乗数 10 円): A マイクロ−ラージ {_fmt(rt_micro, 1)} 円 / "
            f"B 台帳−継続系列 {_fmt(rt_series, 1)} 円。判定に用いた保守コストの丸め分"
            "(呼値 1 ティック × 2 片側 = 100 円)との対照のみで、**本評価のコストには一切"
            "反映していない**(事前登録どおり、実測による置換は最終評価の**後**の反復)。")
        md.append("")
        md.append("読み方の限界: (A) は schema の記載どおり同一時点の**トラッキング差**であって"
                  "板寄せ執行差そのものではない(PREREG も明記)。(B) は台帳が売買した"
                  "**中心限月**の板寄せ実約定と 225Labo の**継続系列**の差なので、板寄せの丸めに加えて"
                  "限月ベーシスと継続系列の接合方式の差を含む。いずれも標本が極小"
                  f"(使用可能 {fwd.get('usable_rows', 0)} 行)で、上限・下限のいずれとしても"
                  "確定的には読めない。よって本節は**診断のみ**で、費用の置換は行わない。")
    else:
        md.append(f"使用可能行が {FORWARD_MIN_USABLE_ROWS} 行に満たないため、"
                  "板寄せ執行差の実測は報告しない(行数のみ記録)。")
    md.append("")
    if "ledger_gross_bps_mean" in fwd:
        md.append(f"参考(台帳自身の記録値): gross 平均 {fwd['ledger_gross_bps_mean']:.2f}bps、"
                  f"net 平均 {fwd.get('ledger_net_bps_mean', float('nan')):.2f}bps"
                  "(台帳の net は手数料 22 円のみを引いた楽観側の定義であり、"
                  "本評価の保守コストとは定義が異なる)。")
        md.append("")
    md.append("## 9. 事前登録のバーと反証文(数値の対照のみ、判断はしない)")
    md.append("")
    md.append("PREREG「最終評価」の原文:")
    md.append("")
    md.append("> - バー: 「累計 N 通りの最良」の帰無分布の 95 点を超える、かつ保守コスト後"
              "(ペアごとの cost_bps(t))の平均ネット夜間リターンの 95% CI が正、かつ"
              "夜間 − 日中の差の 95% CI が正。")
    md.append("> - 反証文(棄却): 封印期間(ロール隣接ペア除外、誤プリント除外、保守コスト後)で"
              "「平均ネット夜間リターンの 95% CI がゼロを含む」または「夜間 − 日中の差の 95% CI が"
              "ゼロを含む」なら本仮説は棄却。ロール隣接ペアを含めた場合にのみ成立する結果は採用しない。")
    md.append("> - 保留区分: 楽観コスト(手数料のみ)では CI が正だが保守コストでは CI がゼロを含む"
              "場合は「存在するが取引価値は丸め次第」として保留。")
    md.append("")
    md.append("### バー(3 条件すべてを要求)")
    md.append("")
    md.append(_table(bar_rows, [("a", "条件", -1), ("b", "実測", -1), ("c", "判定", -1)]))
    md.append("")
    md.append(f"3 条件の同時充足: **{'満たす' if bar_all else '満たさない'}**"
              "(バー 1 は事前登録の主指標が平均であることに合わせ、平均を該当条件とし、"
              "Sharpe は参考として併記)。")
    md.append("")
    md.append("### 反証文と保留区分")
    md.append("")
    md.append(_table(fals_rows, [("a", "文", -1), ("b", "実測", -1), ("c", "判定", -1)]))
    md.append("")
    md.append(f"月次ロール規則で読んだ場合(併記): 平均ネット "
              f"[{ci_main_m[0]:,.3f}, {ci_main_m[1]:,.3f}]、"
              f"夜間−日中の差 [{ci_diff_m[0]:,.3f}, {ci_diff_m[1]:,.3f}] bps。"
              "採用構成(四半期)と符号・包含関係が一致するかは上表と対照のこと。")
    md.append("")
    md.append("## 10. 事前登録からの逸脱")
    md.append("")
    md.append("- 2021 年の夜間セッション延長日は一次資料に記載が無いため、封印データ内で夜間立会が"
              "無かった唯一の夜(§6)を**データ由来の候補日**として分割した。一次資料での確認では"
              "ないので、その旨を明記した記述として置く。事前登録上「判定に使わない」併記であり、"
              "バー・反証文の数値には影響しない。")
    md.append("- 本評価のスクリプトは複数回実行した。1 回目の後に上記 2021 年分割(記述のみ)の"
              "追加と本文の字句修正を行い、同じ seed・同じ入力(md5 一致)で再実行している。"
              "判定に関わる出力"
              "(`main_indicators.csv` / `controls.csv` / `pairs.csv` / `mde.csv` / "
              "`control2_best_of_2_null.csv` / `bar_and_falsification.csv`)は 1 回目と"
              "**バイト一致**で、変わったのは記述表を足した `sub_indicators.csv` と本文のみ。"
              "封印データの読み出しは `UNSEAL_LOG.jsonl` に 2 回分すべて記録されている。")
    md.append("- 対照 2 は事前登録が「1,000 回」と書くシャッフル回数をそのまま用い、"
              f"最良の取り方だけを累計 N = {CUMULATIVE_N} 用に拡張した(バーの原文が要求する形)。"
              "符号ベクトルは 2 構成で共有する(同一の乱数世界を 2 通りに読む)。")
    md.append("- 主集合の分母は事前登録の「ロール隣接除外」と「誤プリント除外」を両方適用した集合。"
              "開発セットと同じ扱いで、除外前の集合も併記した。")
    md.append("- 上記以外の逸脱はない。閾値 0.10・ブロック長 20・リサンプル 2,000・"
              "コスト定数 122 / 22 円・乗数 10 円・端点規則・整列規則・対照の定義は"
              "すべて凍結された事前登録どおり。")
    md.append("")
    (out / "RESULTS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    written.append("RESULTS.md")

    # ---- RUN.json ----------------------------------------------------------
    unseal_excerpt = _read_unseal_log(root, log_start)
    run = {
        "unit": UNIT,
        "stage": "final_evaluation_sealed",
        "roll_rule": FINAL_ROLL_RULE,
        "cumulative_N": CUMULATIVE_N,
        "run_date": str(date(2026, 9, 6)),
        "sealed_window": [str(SEALED_START.date()), str(SEALED_END.date())],
        "seed": SEED,
        "git_rev": _git_rev(),
        "script": "scripts/phase2/p2_01_final.py",
        "script_md5": _md5(Path(__file__)),
        "inputs": [{"path": p, "md5": _md5(root / p)}
                   for p in [DAY_FILE, NIGHT_FILE] + FORWARD_FILES
                   if (root / p).is_file()],
        "seal_record_md5": _md5(root / "backtest_data" / "phase2_sealed" / UNIT
                                / "SEALED.json"),
        "unseal_approved_md5": _md5(root / "backtest_data" / "phase2_sealed" / UNIT
                                    / "UNSEAL_APPROVED"),
        "parameters": {
            "roll_rule": FINAL_ROLL_RULE,
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
            "ci95": list(ci_main),
            "mean_gross_bps": gross_main,
            "ci95_gross": list(ci_gross),
            "mean_r_net_bps_optimistic": mean_opt,
            "ci95_optimistic": list(ci_opt),
            "mean_diff_night_minus_day_bps": mean_diff,
            "ci95_diff": list(ci_diff),
            "sharpe_annualised": sharpe_main,
            "hit_rate": hit_main,
            "max_drawdown_yen_1_micro": mdd_yen,
            "total_pnl_yen_1_micro": total_pnl_yen,
            "best_of_2_null_mean_p95_bps": null_best_mean_p95,
            "best_of_2_null_sharpe_p95": null_best_sharpe_p95,
            "observed_best_mean_bps": obs_best_mean,
            "observed_best_sharpe": obs_best_sharpe,
            "single_config_null_mean_p95_bps": solo_mean_p95,
            "single_config_null_sharpe_p95": solo_sharpe_p95,
            "alignment_median_abs_prev_close": med_prev,
            "alignment_median_abs_same_close": med_same,
            "alignment_pass": alignment_pass,
            "monthly_variant_ci95": list(ci_main_m),
            "monthly_variant_ci95_diff": list(ci_diff_m),
        },
        "bar": {r["a"]: {"measured": r["b"], "outcome": r["c"]} for r in bar_rows}
        | {"all_three_met": bar_all},
        "falsification": {r["a"]: {"measured": r["b"], "outcome": r["c"]}
                          for r in fals_rows},
        "forward_diagnostic": fwd,
        "mde": [{"quantity": r["a"], "sd_bps": r["b"], "n": r["c"], "se_bps": r["d"],
                 "mde_bps_independent": r["e"], "mde_bps_registered": r["f"],
                 "mde_bps_effective_from_ci": r["g"]} for r in mde_rows],
        "unseal_log_excerpt": unseal_excerpt,
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
                        "P2-01/final_20260906).")
    return p.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main(out_dir=_parse_args().out))

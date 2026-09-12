#!/usr/bin/env python
"""P2-03 FINAL EVALUATION — the SEALED period, run exactly once.

Evaluates the frozen pre-registration `docs/PHASE2/P2-03/PREREG.md` (section
"最終評価") on the sealed window 2022-03-05 .. 2026-09-04, using the FINAL
configuration recorded in `docs/PHASE2/P2-03/ITER.md`:

  * iteration 1 = the 1306.T price-level correction (CSV × 10 inside
    2015-01-05..2026-03-31) applied to PRICE-derived quantities only (tick
    band, tick cost in bps) and never to returns — a DATA correction from a
    primary source, not a hypothesis choice;
  * cumulative N = 1 configuration examined, so control 1 / the bar's null is
    the single-configuration sign-shuffle null (no best-of-N inflation).

Every input is read through `bot.research.sealed.load_sealed(path, "P2-03",
token=UNSEAL_TOKEN)`, which enforces the three independent guards (env
`PHASE2_FINAL_EVAL=P2-03`, the owner's `UNSEAL_APPROVED` file, the explicit
token) and appends to the unseal audit log. This module additionally
pre-checks the same three guards before touching anything, so a misconfigured
run fails before the first read rather than half-way through, and hard-codes
the unit to "P2-03" — no other unit can be unsealed from here.

The defect rules (1 bad-print runs / 2 split_candidate / 3 null / 5 phantom),
the tick band lookup, the cost model and the pair construction are NOT
re-implemented here: they are imported from the dev-set runner
`scripts/phase2/p2_03_run.py` via `build_series_result`, so the sealed
period goes through the EXACT code path the development set went through.
Only the loader differs (`load_sealed` instead of `load_unsealed`).

Nothing in this module interprets the numbers as 採用/棄却: it reports the
measured values against the pre-registered bar and falsification sentences
and marks each 満たす / 満たさない. The owner decides.

Usage:
    PHASE2_FINAL_EVAL=P2-03 PYTHONPATH=src \
        python scripts/phase2/p2_03_final.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
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

from bot.constants import load_constants, require_source  # noqa: E402
from bot.research.overnight import (  # noqa: E402
    block_bootstrap_ci,
    sign_shuffle_null,
)
from bot.research.sealed import (  # noqa: E402
    UNSEAL_TOKEN,
    SealedDataError,
    load_sealed,
    seal_dir,
)
from phase2.p2_03_run import (  # noqa: E402  (dev-set runner: reused, unchanged)
    BAD_PRINT_DEV_THRESHOLD,
    BAD_PRINT_MAX_K,
    BAD_PRINT_REVERT_TOLERANCE,
    BOOT_BLOCK,
    BOOT_N,
    CONTROL4_SYMBOLS,
    MAIN_SYMBOLS,
    MDE_BPS,
    PRICE_LEVEL_CORRECTIONS,
    REFERENCE_SYMBOL,
    RUN_SEED,
    SHUFFLE_N,
    SNAPSHOT_DIR,
    add_diagnostic_columns,
    build_series_result,
    control2_vol_tercile_random_holding,
    diagnostics_table,
    max_drawdown_bps,
    parse_tick_bands,
    sharpe_stats,
    tick_for_price,
)

UNIT = "P2-03"                     # hard-coded: only P2-03 may be unsealed here
CUMULATIVE_N = 1                   # ITER.md: 反復 0 と 反復 1 は同一構成(データ修正)

# ---- pre-registered sealed window (PREREG "最終評価") ----------------------
SEALED_START = pd.Timestamp("2022-03-05")
SEALED_END = pd.Timestamp("2026-09-04")

# 仮説の対象 3 銘柄(TOPIX / JPX400 / グロース 250)と、「同様の」の基準となる参照系列。
ETF_SYMBOLS = ["1306.T", "1591.T", "2516.T"]
SERIES_LABEL = {
    "1306.T": "TOPIX(1306.T)",
    "1591.T": "JPX日経400(1591.T)",
    "2516.T": "グロース250(2516.T)",
    "1321.T": "日経225 参照(1321.T)",
}

# PREREG「制度変更」: 封印期間内の 2024-11-05 引け板寄せ 15:30 化。記述のみ。
REGIME_CHANGE = pd.Timestamp("2024-11-05")

# schema/jpx_etf_daily.json の CORRECTION 2026-09-06 が名指しする 2 行欠陥と、
# その直後にある実際の 10:1 分割(2026-04-01 効力)の前後を、生の値と規則の判定
# ごと表に出すための窓。判定には使わない(報告のためだけの切り出し)。
BOUNDARY_SYMBOL = "1306.T"
BOUNDARY_START = pd.Timestamp("2026-03-20")
BOUNDARY_END = pd.Timestamp("2026-04-10")
SPLIT_EFFECTIVE = pd.Timestamp("2026-04-01")   # 野村 AM 適時開示 2026-02-17

# Root-relative so the whole run can be pointed at a temporary root in tests
# (SNAPSHOT_DIR from the dev-set runner is the same directory under REPO_ROOT).
SNAPSHOT_REL = Path("backtest_data") / "jpx_etf_daily_20260905"
assert SNAPSHOT_DIR == REPO_ROOT / SNAPSHOT_REL

OUT_DIR = REPO_ROOT / "backtest_data" / "phase2_runs" / UNIT / "final_20260906"

Z95 = 1.959963985
Z_POWER = 0.8416212336


# ---------------------------------------------------------------------------
# guards
# ---------------------------------------------------------------------------

def check_guards(root: Path | str = REPO_ROOT, token: str = UNSEAL_TOKEN,
                 unit: str = UNIT, env: dict | None = None) -> None:
    """Raise ``SealedDataError`` unless all three unseal guards are satisfied.

    Mirrors `bot.research.sealed.load_sealed`'s own check so a misconfigured
    final-evaluation run fails BEFORE the first read (and reports every
    missing guard at once, not just the first). Also refuses any unit other
    than P2-03: the owner's approval is scoped to this unit alone.
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
            "refusing the P2-03 final evaluation: " + "; ".join(reasons))


# ---------------------------------------------------------------------------
# small helpers (formatting / statistics)
# ---------------------------------------------------------------------------

def _fmt(v, nd: int = 3) -> str:
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "—"
    if isinstance(v, (bool, np.bool_)):
        return str(bool(v))
    if isinstance(v, (int, np.integer)):
        return f"{int(v):,}"
    return f"{float(v):,.{nd}f}"


def _table(rows: list[dict], cols: list[tuple[str, str, int]]) -> str:
    head = "| " + " | ".join(c[1] for c in cols) + " |"
    sep = "|" + "|".join("---" for _ in cols) + "|"
    body = ["| " + " | ".join(
        (str(r.get(k, "")) if nd < 0 else _fmt(r.get(k), nd))
        for k, _, nd in cols) + " |" for r in rows]
    return "\n".join([head, sep] + body)


def describe(x, label: str, dates: pd.Series | None = None,
             seed: int = RUN_SEED) -> dict:
    """n / mean / sd / t / hit rate / block-bootstrap 95% CI (+ Sharpe).

    Every CI in this script uses the same pre-registered resampling
    (block 20 営業日, 2,000 resamples) and the same seed, so the numbers do
    not depend on the order in which the tables happen to be built.
    """
    raw = np.asarray(x, dtype=float)
    # Sharpe needs the values and their dates side by side, so it is computed
    # from the UNFILTERED arrays (`sharpe_stats` drops the non-finite entries
    # itself, keeping values and dates aligned); everything else works on the
    # finite subset.
    sharpe = (sharpe_stats(raw, dates)["sharpe"] if dates is not None
              else float("nan"))
    x = raw[np.isfinite(raw)]
    n = len(x)
    row: dict = {"label": label, "n": n}
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
    lo, hi = block_bootstrap_ci(x, block=BOOT_BLOCK, n_boot=BOOT_N, seed=seed)
    row["ci_lo"], row["ci_hi"] = lo, hi
    row["sharpe"] = sharpe
    return row


def ci_contains_zero(lo: float, hi: float) -> bool:
    return bool(np.isfinite(lo) and np.isfinite(hi) and lo <= 0.0 <= hi)


def ci_is_positive(lo: float) -> bool:
    return bool(np.isfinite(lo) and lo > 0.0)


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_rev() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"],
                                       cwd=REPO_ROOT, text=True).strip()
    except Exception:  # pragma: no cover - git always present in this repo
        return "unknown"


def _unseal_log_len(root: Path) -> int:
    p = seal_dir(UNIT, root) / "UNSEAL_LOG.jsonl"
    if not p.is_file():
        return 0
    return len([ln for ln in p.read_text(encoding="utf-8").splitlines()
                if ln.strip()])


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


# ---------------------------------------------------------------------------
# loading (the ONLY difference from the dev-set path)
# ---------------------------------------------------------------------------

def load_series(sym: str, bands, token: str, root: Path) -> dict:
    """Sealed rows of ``sym`` put through the dev-set runner's own pipeline.

    `build_series_result` is imported from `scripts/phase2/p2_03_run.py`
    unchanged, so rules 1/2/3/5, the tick band, the cost model and the pair
    construction are literally the same code the development set ran.
    """
    csv_path = Path(root) / SNAPSHOT_REL / f"{sym}.csv"
    df = load_sealed(csv_path, UNIT, token=token, root=root)
    res = build_series_result(sym, df, bands, apply_price_correction=True)
    res["pairs"] = add_diagnostic_columns(res["pairs"], res["df"])
    return res


def apply_endpoint_rule(pairs: pd.DataFrame) -> pd.DataFrame:
    """PREREG 端点規則: keep a pair only when BOTH days lie in the sealed
    window. `load_sealed` already returns only sealed rows, so this is a
    belt-and-braces re-assertion that also pins the window's far end."""
    return pairs.loc[(pairs["date_t"] >= SEALED_START)
                     & (pairs["date_t1"] <= SEALED_END)].reset_index(drop=True)


# ---------------------------------------------------------------------------
# the 2026-03-30/31 defect + the 2026-04-01 real split
# ---------------------------------------------------------------------------

def boundary_window_table(res: dict) -> pd.DataFrame:
    """Row-level view of 1306.T around the two-bar defect and the real split.

    Reports, for every trading day in [BOUNDARY_START, BOUNDARY_END]: the raw
    CSV OHLC, which defect rule (if any) flagged the ROW, the price actually
    used for the tick band (CSV × 10 up to 2026-03-31, CSV as-is after the
    2026-04-01 split effective date), and — for the pair starting on that day
    — the resulting cost and whether the pair survived the exclusions.
    """
    df = res["df"]
    pairs = res["pairs"]
    mask = (df["date"] >= BOUNDARY_START) & (df["date"] <= BOUNDARY_END)
    sub = df.loc[mask]
    pair_by_date = pairs.set_index("date_t")
    rows = []
    for _, r in sub.iterrows():
        d = r["date"]
        p = pair_by_date.loc[d] if d in pair_by_date.index else None
        rows.append({
            "date": str(pd.Timestamp(d).date()),
            "open_csv": r.get("open"), "close_csv": r.get("close"),
            "volume": r.get("volume"),
            "flag_rule1_badprint": bool(p["flag_badprint_t"]) if p is not None else None,
            "flag_rule2_split": bool(p["flag_split_t"]) if p is not None else None,
            "flag_rule3_null": bool(p["flag_null_t"]) if p is not None else None,
            "flag_rule5_ghost": bool(p["flag_ghost_t"]) if p is not None else None,
            "band_price_used": float(p["band_price_t"]) if p is not None else None,
            "tick_yen": float(p["tick_yen"]) if p is not None else None,
            "pair_to": str(pd.Timestamp(p["date_t1"]).date()) if p is not None else None,
            "pair_r_night_bps": float(p["r_night_bps"]) if p is not None else None,
            "pair_cost_cons_bps": float(p["cost_cons_bps"]) if p is not None else None,
            "pair_excluded": bool(p["excluded"]) if p is not None else None,
            "pair_clean": bool(p["clean"]) if p is not None else None,
        })
    return pd.DataFrame(rows)


BADPRINT_EVENT_COLUMNS = ["series", "k", "first_date", "last_date",
                          "baseline_close_c0", "baseline_date", "revert_date",
                          "revert_close"]


def badprint_event_table(results: dict) -> pd.DataFrame:
    """Every rule-1 run the sealed period contains, with its actual dates."""
    rows = []
    for sym, res in results.items():
        dates = res["df"]["date"].reset_index(drop=True)
        for ev in res["badprint_events"]:
            rows.append({
                "series": sym,
                "k": ev["k"],
                "first_date": str(pd.Timestamp(dates.iloc[ev["start"]]).date()),
                "last_date": str(pd.Timestamp(dates.iloc[ev["end"]]).date()),
                "baseline_close_c0": ev["c0"],
                "baseline_date": str(pd.Timestamp(dates.iloc[ev["start"] - 1]).date()),
                "revert_date": (str(pd.Timestamp(dates.iloc[ev["end"] + 1]).date())
                                if ev["end"] + 1 < len(dates) else ""),
                "revert_close": (float(res["df"]["close"].iloc[ev["end"] + 1])
                                 if ev["end"] + 1 < len(dates) else float("nan")),
            })
    # An empty frame must still carry the columns, so downstream readers can
    # select on them instead of raising KeyError when no run was found.
    return pd.DataFrame(rows, columns=BADPRINT_EVENT_COLUMNS)


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

def main(out_dir: Path | None = None, root: Path | str = REPO_ROOT,
         token: str = UNSEAL_TOKEN) -> int:
    root = Path(root)
    check_guards(root, token)
    out = Path(out_dir) if out_dir is not None else OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    log_start = _unseal_log_len(root)
    steps: dict[str, int] = {}
    written: list[str] = []

    def write(df: pd.DataFrame, name: str):
        df.to_csv(out / name, index=False)
        written.append(name)

    # ---- cost constants ----------------------------------------------------
    constants = load_constants(root)
    tick_const = require_source("jpx_cash_equity.etf_tick_size_yen_by_price_band",
                                constants)
    bands = parse_tick_bands(tick_const.value)
    commission_const = require_source("jpx_cash_equity.sor_commission_yen", constants)
    if commission_const.value != 0:  # pragma: no cover - constants are pinned
        raise RuntimeError("手数料が 0 円想定と食い違う -- コスト式の見直しが必要")

    # ---- load the sealed rows ---------------------------------------------
    results: dict[str, dict] = {}
    for sym in MAIN_SYMBOLS:
        res = load_series(sym, bands, token, root)
        steps[f"rows_sealed_{sym}"] = res["n_rows"]
        res["pairs_all"] = res["pairs"]
        res["pairs"] = apply_endpoint_rule(res["pairs"])
        steps[f"pairs_after_endpoint_rule_{sym}"] = len(res["pairs"])
        results[sym] = res

    control4: dict[str, dict] = {}
    for sym in CONTROL4_SYMBOLS:
        try:
            r4 = load_series(sym, bands, token, root)
            r4["pairs"] = apply_endpoint_rule(r4["pairs"])
            control4[sym] = r4
        except Exception as exc:  # pragma: no cover - diagnostic only
            control4[sym] = {"error": str(exc)}

    # ---- md5 verification against SEALED.json ------------------------------
    seal_record = json.loads(
        (seal_dir(UNIT, root) / "SEALED.json").read_text(encoding="utf-8"))
    seal_md5 = {e["path"]: e["md5"] for e in seal_record["files"]}
    md5_rows = []
    for sym in MAIN_SYMBOLS + CONTROL4_SYMBOLS:
        rel = f"{SNAPSHOT_REL.as_posix()}/{sym}.csv"
        actual = _md5(root / rel)
        md5_rows.append({"series": sym, "path": rel,
                         "md5_sealed_json": seal_md5.get(rel, ""),
                         "md5_now": actual,
                         "match": bool(seal_md5.get(rel) == actual)})
    write(pd.DataFrame(md5_rows), "input_md5_check.csv")
    steps["input_md5_mismatches"] = int(sum(0 if r["match"] else 1 for r in md5_rows))

    # ---- defect rule counts -------------------------------------------------
    rule_rows = []
    for sym, res in results.items():
        pairs = res["pairs"]
        rule_rows.append({
            "series": sym,
            "n_rows_sealed": res["n_rows"],
            "n_pairs_after_endpoint_rule": len(pairs),
            "rule1_badprint_rows": res["n_badprint_rows"],
            "rule1_badprint_runs": len(res["badprint_events"]),
            "rule1_one_sided_info_rows": res["n_one_sided_info"],
            "rule2_split_rows": res["n_split_rows"],
            "rule3_null_rows": res["n_null_rows"],
            "rule5_ghost_rows": res["n_ghost_rows"],
            "n_pairs_excluded": int(pairs["excluded"].sum()),
            "n_pairs_valid_raw": int(pairs["valid_raw"].sum()),
            "n_pairs_clean": int(pairs["clean"].sum()),
        })
    write(pd.DataFrame(rule_rows), "rule_counts.csv")
    for r in rule_rows:
        steps[f"n_clean_{r['series']}"] = r["n_pairs_clean"]

    write(badprint_event_table(results), "rule1_badprint_events.csv")
    boundary = boundary_window_table(results[BOUNDARY_SYMBOL])
    write(boundary, "boundary_2026_1306.csv")

    # ---- main indicators (before / after exclusion x optimistic / conservative)
    ind_rows = []
    for sym, res in results.items():
        pairs = res["pairs"]
        for stage, col in (("before_exclusion", "valid_raw"),
                           ("after_exclusion", "clean")):
            sub = pairs.loc[pairs[col]]
            for scen, vcol in (("optimistic", "net_opt_bps"),
                               ("conservative", "net_cons_bps")):
                d = describe(sub[vcol].to_numpy(), f"{sym} {stage} {scen}",
                             sub["date_t"])
                ind_rows.append({"series": sym, "stage": stage,
                                 "cost_scenario": scen, **d})
    indicator_df = pd.DataFrame(ind_rows)
    write(indicator_df, "main_indicator.csv")

    def ind(sym: str, scen: str, stage: str = "after_exclusion") -> dict:
        m = indicator_df[(indicator_df["series"] == sym)
                         & (indicator_df["stage"] == stage)
                         & (indicator_df["cost_scenario"] == scen)]
        return m.iloc[0].to_dict()

    # ---- per-series summary -------------------------------------------------
    summary_rows = []
    for sym, res in results.items():
        clean = res["pairs"].loc[res["pairs"]["clean"]]
        opt = ind(sym, "optimistic")
        cons = ind(sym, "conservative")
        diff = describe((clean["r_night_bps"] - clean["r_day_bps"]).to_numpy(),
                        f"{sym} night-day", clean["date_t"])
        day = describe(clean["r_day_bps"].to_numpy(), f"{sym} day", clean["date_t"])
        summary_rows.append({
            "series": sym,
            "n_clean": len(clean),
            "mean_opt_bps": opt["mean"], "opt_ci_lo": opt["ci_lo"],
            "opt_ci_hi": opt["ci_hi"], "opt_sharpe": opt["sharpe"],
            "mean_cons_bps": cons["mean"], "cons_ci_lo": cons["ci_lo"],
            "cons_ci_hi": cons["ci_hi"], "cons_sharpe": cons["sharpe"],
            "mean_cost_cons_bps": float(clean["cost_cons_bps"].mean()),
            "median_cost_cons_bps": float(clean["cost_cons_bps"].median()),
            "mean_day_bps": day["mean"],
            "night_minus_day_bps": diff["mean"],
            "night_minus_day_ci_lo": diff["ci_lo"],
            "night_minus_day_ci_hi": diff["ci_hi"],
            "max_dd_opt_bps": max_drawdown_bps(clean["net_opt_bps"].to_numpy()),
            "max_dd_cons_bps": max_drawdown_bps(clean["net_cons_bps"].to_numpy()),
            "hit_rate_opt": opt["hit_rate"],
            "hit_rate_cons": cons["hit_rate"],
            "sd_opt_bps": opt["sd"],
            "mde_bps_registered": MDE_BPS[sym],
        })
    summary_df = pd.DataFrame(summary_rows)
    write(summary_df, "summary_by_series.csv")

    # ---- cost detail: what one tick is worth, and the 2026-04-01 step -------
    cost_rows = []
    for sym, res in results.items():
        clean = res["pairs"].loc[res["pairs"]["clean"]]
        last_close = (float(clean["close_t"].iloc[-1]) if len(clean)
                      else float("nan"))
        last_date = (pd.Timestamp(clean["date_t"].iloc[-1]) if len(clean)
                     else pd.NaT)
        last_band_price = float(clean["band_price_t"].iloc[-1]) if len(clean) else np.nan
        last_tick = tick_for_price(last_band_price, bands)
        row = {
            "series": sym,
            "n_clean": len(clean),
            "band_price_min": float(clean["band_price_t"].min()),
            "band_price_max": float(clean["band_price_t"].max()),
            "tick_yen_min": float(clean["tick_yen"].min()),
            "tick_yen_max": float(clean["tick_yen"].max()),
            "cost_roundtrip_mean_bps": float(clean["cost_cons_bps"].mean()),
            "cost_roundtrip_min_bps": float(clean["cost_cons_bps"].min()),
            "cost_roundtrip_max_bps": float(clean["cost_cons_bps"].max()),
            "last_pair_date_t": str(last_date.date()) if last_date is not pd.NaT else "",
            "last_close_csv": last_close,
            "last_band_price_used": last_band_price,
            "last_tick_yen": last_tick,
            "per_side_bps_now": (last_tick / last_band_price * 1e4
                                 if np.isfinite(last_band_price) and last_band_price
                                 else float("nan")),
        }
        if sym == BOUNDARY_SYMBOL:
            pre = clean.loc[clean["date_t"] < SPLIT_EFFECTIVE]
            post = clean.loc[clean["date_t"] >= SPLIT_EFFECTIVE]
            row["cost_mean_bps_pre_2026_04_01"] = (float(pre["cost_cons_bps"].mean())
                                                   if len(pre) else float("nan"))
            row["cost_mean_bps_post_2026_04_01"] = (float(post["cost_cons_bps"].mean())
                                                    if len(post) else float("nan"))
            row["n_pre_2026_04_01"] = len(pre)
            row["n_post_2026_04_01"] = len(post)
        cost_rows.append(row)
    write(pd.DataFrame(cost_rows), "cost_by_series.csv")

    # ---- sign agreement with 1321 ------------------------------------------
    ref_mean = float(summary_df.loc[summary_df["series"] == REFERENCE_SYMBOL,
                                    "mean_opt_bps"].iloc[0])
    sign_rows = []
    for sym in MAIN_SYMBOLS:
        m = float(summary_df.loc[summary_df["series"] == sym,
                                 "mean_opt_bps"].iloc[0])
        sign_rows.append({
            "series": sym, "mean_gross_r_night_bps": m,
            "reference_mean_bps": ref_mean,
            "sign_matches_1321": bool(np.sign(m) == np.sign(ref_mean)),
        })
    write(pd.DataFrame(sign_rows), "sign_agreement.csv")

    # ---- correlations + residual vs 1321 -----------------------------------
    frames = {}
    for sym, res in results.items():
        p = res["pairs"]
        s = p.loc[p["clean"], ["date_t", "r_night_bps"]].set_index("date_t")["r_night_bps"]
        s.name = sym
        frames[sym] = s
    merged = pd.concat(frames.values(), axis=1, sort=True)
    merged.columns = list(frames.keys())
    corr = merged.sort_index().corr()
    corr.to_csv(out / "correlation_matrix.csv")
    written.append("correlation_matrix.csv")

    residual_rows = []
    ref_series = merged[REFERENCE_SYMBOL]
    for sym in ETF_SYMBOLS:
        common = pd.concat([merged[sym], ref_series], axis=1).dropna()
        common.columns = ["etf", "ref"]
        d = describe((common["etf"] - common["ref"]).to_numpy(),
                     f"{sym} residual vs 1321")
        residual_rows.append({"series": sym, "n_common": len(common),
                              "mean_bps": d["mean"], "ci_lo": d["ci_lo"],
                              "ci_hi": d["ci_hi"], "sd_bps": d["sd"]})
    write(pd.DataFrame(residual_rows), "residual_vs_1321.csv")

    # ---- 2024-11-05 regime split (descriptive) -----------------------------
    regime_rows = []
    for sym, res in results.items():
        clean = res["pairs"].loc[res["pairs"]["clean"]]
        for label, sub in (
                (f"..{(REGIME_CHANGE - pd.Timedelta(days=1)).date()}(引け板寄せ 15:00)",
                 clean.loc[clean["date_t"] < REGIME_CHANGE]),
                (f"{REGIME_CHANGE.date()}..(引け板寄せ 15:30)",
                 clean.loc[clean["date_t"] >= REGIME_CHANGE])):
            d_opt = describe(sub["net_opt_bps"].to_numpy(), label, sub["date_t"])
            d_cons = describe(sub["net_cons_bps"].to_numpy(), label, sub["date_t"])
            regime_rows.append({
                "series": sym, "regime": label, "n": d_opt["n"],
                "mean_opt_bps": d_opt["mean"], "opt_ci_lo": d_opt["ci_lo"],
                "opt_ci_hi": d_opt["ci_hi"],
                "mean_cons_bps": d_cons["mean"], "cons_ci_lo": d_cons["ci_lo"],
                "cons_ci_hi": d_cons["ci_hi"],
                "mean_cost_bps": (float(sub["cost_cons_bps"].mean())
                                  if len(sub) else float("nan")),
            })
    write(pd.DataFrame(regime_rows), "regime_2024_11_05.csv")

    # ---- controls -----------------------------------------------------------
    c1_rows, c2_rows, c3_rows = [], [], []
    for sym, res in results.items():
        clean = res["pairs"].loc[res["pairs"]["clean"]]
        x = clean["r_night_bps"].to_numpy(dtype=float)
        x = x[np.isfinite(x)]
        null = sign_shuffle_null(x, n=SHUFFLE_N, seed=RUN_SEED)
        # 保守コスト後の観測平均は、同じ帰無の平均を一定量だけ左に平行移動した
        # 世界と比べるべきなので、帰無側にも同じ平均コストを引いて併記する。
        mean_cost = float(clean["cost_cons_bps"].mean()) if len(clean) else np.nan
        c1_rows.append({
            "series": sym, "n": int(len(x)),
            "observed_mean_gross_bps": float(x.mean()) if len(x) else np.nan,
            "null_mean_bps": float(null.mean()) if len(null) else np.nan,
            "null_p95_bps": float(np.percentile(null, 95)) if len(null) else np.nan,
            "observed_gt_null_p95": (bool(x.mean() > np.percentile(null, 95))
                                     if len(x) and len(null) else None),
            "observed_mean_cons_bps": float(x.mean() - mean_cost) if len(x) else np.nan,
            "null_p95_minus_mean_cost_bps": (float(np.percentile(null, 95) - mean_cost)
                                             if len(null) else np.nan),
        })
        for row in control2_vol_tercile_random_holding(
                clean, np.random.default_rng(RUN_SEED)):
            c2_rows.append({"series": sym, **row})
        short_opt = describe(-clean["r_night_bps"].to_numpy(), f"{sym} short opt")
        short_cons = describe((-clean["r_night_bps"] - clean["cost_cons_bps"]).to_numpy(),
                              f"{sym} short cons")
        c3_rows.append({
            "series": sym, "n": short_opt["n"],
            "net_short_opt_mean_bps": short_opt["mean"],
            "net_short_opt_ci_lo": short_opt["ci_lo"],
            "net_short_opt_ci_hi": short_opt["ci_hi"],
            "net_short_cons_mean_bps": short_cons["mean"],
            "net_short_cons_ci_lo": short_cons["ci_lo"],
            "net_short_cons_ci_hi": short_cons["ci_hi"],
        })
    write(pd.DataFrame(c1_rows), "controls_sign_shuffle.csv")
    write(pd.DataFrame(c2_rows), "controls_vol_tercile.csv")
    write(pd.DataFrame(c3_rows), "controls_sign_reversal.csv")

    c4_rows = []
    for sym, res in control4.items():
        if "error" in res:
            c4_rows.append({"series": sym, "error": res["error"]})
            continue
        clean = res["pairs"].loc[res["pairs"]["clean"]]
        d = describe(clean["r_night_bps"].to_numpy(), f"{sym} gross", clean["date_t"])
        c4_rows.append({"series": sym, "n_clean": len(clean),
                        "mean_gross_bps": d["mean"], "ci_lo": d["ci_lo"],
                        "ci_hi": d["ci_hi"], "sd_bps": d["sd"],
                        "sharpe": d["sharpe"]})
    write(pd.DataFrame(c4_rows), "controls_individual_stocks.csv")

    # ---- diagnostics (descriptive only) ------------------------------------
    diag_rows = []
    for sym, res in results.items():
        clean = res["pairs"].loc[res["pairs"]["clean"]]
        diag_rows.extend(diagnostics_table(sym, clean))
    write(pd.DataFrame(diag_rows), "diagnostics.csv")

    # ---- MDE recomputed on the sealed sample (recorded, not judged) --------
    mde_rows = []
    for sym, res in results.items():
        clean = res["pairs"].loc[res["pairs"]["clean"]]
        x = clean["r_night_bps"].to_numpy(dtype=float)
        x = x[np.isfinite(x)]
        sd = float(x.std(ddof=1))
        se = sd / np.sqrt(len(x)) if len(x) else float("nan")
        lo, hi = block_bootstrap_ci(x, block=BOOT_BLOCK, n_boot=BOOT_N, seed=RUN_SEED)
        se_eff = (hi - lo) / (2 * Z95)
        mde_rows.append({
            "series": sym, "n": len(x), "sd_bps": sd, "se_bps": se,
            "mde_bps_independent": (Z95 + Z_POWER) * se,
            "mde_bps_effective_from_ci": (Z95 + Z_POWER) * se_eff,
            "mde_bps_registered": MDE_BPS[sym],
        })
    write(pd.DataFrame(mde_rows), "mde.csv")

    # ---- per-pair CSVs -------------------------------------------------------
    for sym, res in results.items():
        name = f"pairs_{sym.replace('.', '')}.csv"
        res["pairs"].to_csv(out / name, index=False)
        written.append(name)

    # ---- exclusions ledger ---------------------------------------------------
    excl_rows = []
    for r in rule_rows:
        excl_rows.append({
            "series": r["series"],
            "封印行数": r["n_rows_sealed"],
            "端点規則後のペア": r["n_pairs_after_endpoint_rule"],
            "規則1 誤プリント行": r["rule1_badprint_rows"],
            "規則2 分割行": r["rule2_split_rows"],
            "規則3 null行": r["rule3_null_rows"],
            "規則5 幽霊行": r["rule5_ghost_rows"],
            "除外ペア": r["n_pairs_excluded"],
            "判定分母(除外後)": r["n_pairs_clean"],
        })
    write(pd.DataFrame(excl_rows), "exclusions.csv")

    # ---- bar / falsification / hold -----------------------------------------
    c1_by = {r["series"]: r for r in c1_rows}
    sign_by = {r["series"]: r for r in sign_rows}

    bar_rows = []
    bar_by_sym: dict[str, bool] = {}
    for sym in ETF_SYMBOLS:
        opt = ind(sym, "optimistic")
        cons = ind(sym, "conservative")
        c1 = c1_by[sym]
        b1 = bool(c1["observed_gt_null_p95"])
        b2 = ci_is_positive(cons["ci_lo"])
        b3 = bool(sign_by[sym]["sign_matches_1321"])
        bar_by_sym[sym] = bool(b1 and b2 and b3)
        bar_rows += [
            {"series": sym,
             "criterion": f"バー1 累計 N={CUMULATIVE_N} の帰無 95 点超(符号シャッフル、グロス)",
             "measured": f"実測 {c1['observed_mean_gross_bps']:.3f} vs 帰無95点 "
                         f"{c1['null_p95_bps']:.3f} bps",
             "outcome": "満たす" if b1 else "満たさない"},
            {"series": sym,
             "criterion": "バー2 保守コスト後の平均夜間リターンの 95% CI が正",
             "measured": f"[{cons['ci_lo']:.3f}, {cons['ci_hi']:.3f}] bps "
                         f"(平均 {cons['mean']:.3f})",
             "outcome": "満たす" if b2 else "満たさない"},
            {"series": sym,
             "criterion": "バー3 日経225 ETF(1321)と符号一致",
             "measured": f"{opt['mean']:.3f} vs 1321 {ref_mean:.3f} bps",
             "outcome": "満たす" if b3 else "満たさない"},
            {"series": sym, "criterion": "バー(3 条件の同時充足)",
             "measured": f"バー1={b1} / バー2={b2} / バー3={b3}",
             "outcome": "満たす" if bar_by_sym[sym] else "満たさない"},
        ]

    # 反証文(存在): 3 ETF のうち 2 つ以上で楽観 CI がゼロを含むか
    exist_flags = {sym: ci_contains_zero(ind(sym, "optimistic")["ci_lo"],
                                         ind(sym, "optimistic")["ci_hi"])
                   for sym in ETF_SYMBOLS}
    n_exist_zero = int(sum(exist_flags.values()))
    fals_exist_met = bool(n_exist_zero >= 2)

    fals_rows = [{
        "kind": "falsification_existence",
        "series": "3 ETF 合計",
        "criterion": "反証文(存在) 3 ETF のうち 2 つ以上で楽観コストの平均夜間リターンの "
                     "95% CI がゼロを含む",
        "measured": f"ゼロを含む銘柄数 = {n_exist_zero} / 3 "
                    + "(" + ", ".join(f"{s}:{'含む' if v else '含まない'}"
                                      for s, v in exist_flags.items()) + ")",
        "outcome": "満たす" if fals_exist_met else "満たさない",
    }]
    for sym in ETF_SYMBOLS:
        cons = ind(sym, "conservative")
        contains = ci_contains_zero(cons["ci_lo"], cons["ci_hi"])
        not_positive = not ci_is_positive(cons["ci_lo"])
        fals_rows.append({
            "kind": "falsification_tradability",
            "series": sym,
            "criterion": "反証文(取引可能) 保守コスト後の 95% CI がゼロを含む "
                         "→「存在するが取引不能(丸め次第)」",
            "measured": f"[{cons['ci_lo']:.3f}, {cons['ci_hi']:.3f}] bps / "
                        f"ゼロを含む={contains} / CI が正でない={not_positive}",
            "outcome": "満たす" if contains else "満たさない",
        })

    hold_rows = []
    for sym in ETF_SYMBOLS:
        opt = ind(sym, "optimistic")
        cons = ind(sym, "conservative")
        exists = ci_is_positive(opt["ci_lo"])
        tradable = ci_is_positive(cons["ci_lo"])
        hold = bool(exists and not tradable)
        hold_rows.append({
            "kind": "hold_class",
            "series": sym,
            "criterion": "保留区分「存在するが取引不能(丸め次第)」= 楽観 CI が正 かつ "
                         "保守 CI が正でない",
            "measured": f"楽観 [{opt['ci_lo']:.3f}, {opt['ci_hi']:.3f}] / "
                        f"保守 [{cons['ci_lo']:.3f}, {cons['ci_hi']:.3f}] bps",
            "outcome": "満たす" if hold else "満たさない",
            "trigger": "スプレッドの実測(kabu ステーションの板記録)"
                       " / 同一指数の高価格代替銘柄(TOPIX: 1348.T)の取得",
        })

    judgment_df = pd.DataFrame(
        [{"kind": "bar", **r} for r in bar_rows] + fals_rows + hold_rows)
    write(judgment_df, "bar_and_falsification.csv")

    # ---- RESULTS.md ----------------------------------------------------------
    md = build_results_md(
        results, control4, summary_df, indicator_df, rule_rows, cost_rows,
        sign_rows, corr, residual_rows, regime_rows, c1_rows, c2_rows, c3_rows,
        c4_rows, mde_rows, boundary, badprint_event_table(results), bar_rows,
        fals_rows, hold_rows, bar_by_sym, exist_flags, n_exist_zero,
        fals_exist_met, md5_rows, steps, diag_rows)
    (out / "RESULTS.md").write_text(md, encoding="utf-8")
    written.append("RESULTS.md")

    # ---- RUN.json ------------------------------------------------------------
    headline = {}
    for sym in MAIN_SYMBOLS:
        opt = ind(sym, "optimistic")
        cons = ind(sym, "conservative")
        srow = summary_df.loc[summary_df["series"] == sym].iloc[0]
        headline[sym] = {
            "n_clean": int(srow["n_clean"]),
            "mean_optimistic_bps": opt["mean"],
            "ci95_optimistic": [opt["ci_lo"], opt["ci_hi"]],
            "mean_conservative_bps": cons["mean"],
            "ci95_conservative": [cons["ci_lo"], cons["ci_hi"]],
            "mean_cost_roundtrip_bps": float(srow["mean_cost_cons_bps"]),
            "night_minus_day_bps": float(srow["night_minus_day_bps"]),
            "ci95_night_minus_day": [float(srow["night_minus_day_ci_lo"]),
                                     float(srow["night_minus_day_ci_hi"])],
            "sharpe_optimistic": opt["sharpe"],
            "sharpe_conservative": cons["sharpe"],
            "max_dd_optimistic_bps": float(srow["max_dd_opt_bps"]),
            "max_dd_conservative_bps": float(srow["max_dd_cons_bps"]),
            "hit_rate_optimistic": opt["hit_rate"],
            "sign_matches_1321": sign_by[sym]["sign_matches_1321"],
        }

    run = {
        "unit": UNIT,
        "stage": "final_evaluation_sealed",
        "run_date": str(date(2026, 9, 6)),
        "sealed_window": [str(SEALED_START.date()), str(SEALED_END.date())],
        "forward_start": seal_record["forward_start"],
        "forward_rows_available": 0,
        "cumulative_N": CUMULATIVE_N,
        "final_configuration": {
            "iteration": 1,
            "price_level_corrections": PRICE_LEVEL_CORRECTIONS,
            "note": "1306.T の CSV 2015-01-05..2026-03-31 は実勢価格の 1/10。"
                    "呼値帯・呼値コストのみ ×10 で補正し、リターンには一切触れない。",
        },
        "seed": RUN_SEED,
        "git_rev": _git_rev(),
        "script": "scripts/phase2/p2_03_final.py",
        "script_md5": _md5(Path(__file__)),
        "shared_code_path": "scripts/phase2/p2_03_run.py::build_series_result "
                            "(開発セットと同一。差は load_sealed / load_unsealed のみ)",
        "parameters": {
            "block": BOOT_BLOCK, "n_boot": BOOT_N, "n_shuffle": SHUFFLE_N,
            "bad_print_dev_threshold": BAD_PRINT_DEV_THRESHOLD,
            "bad_print_revert_tolerance": BAD_PRINT_REVERT_TOLERANCE,
            "bad_print_max_k": BAD_PRINT_MAX_K,
            "commission_yen": commission_const.value,
            "tick_bands_source": tick_const.source_url,
            "mde_bps_registered": MDE_BPS,
        },
        "input_md5_check": md5_rows,
        "seal_record_md5": _md5(seal_dir(UNIT, root) / "SEALED.json"),
        "unseal_approved_md5": _md5(seal_dir(UNIT, root) / "UNSEAL_APPROVED"),
        "n_at_each_step": steps,
        "headline": headline,
        "bar": bar_rows,
        "bar_all_three_met": bar_by_sym,
        "falsification": fals_rows,
        "falsification_existence_met": fals_exist_met,
        "hold_class": hold_rows,
        "mde": mde_rows,
        "unseal_log_excerpt": _read_unseal_log(root, log_start),
        "outputs": sorted(written),
    }
    (out / "RUN.json").write_text(
        json.dumps(run, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8")

    print(json.dumps(headline, ensure_ascii=False, indent=2, default=str))
    print(f"wrote {len(written) + 1} files to {out}")
    return 0


# ---------------------------------------------------------------------------
# RESULTS.md
# ---------------------------------------------------------------------------

def _boundary_narrative(boundary: pd.DataFrame, bp_events: pd.DataFrame) -> str:
    """Prose reading of what the rules did to 2026-03-30 .. 2026-04-02.

    Built from the measured table, not from prior belief: every number quoted
    is looked up in `boundary` / `bp_events`, so if the sealed data had turned
    out different the text would say something different.
    """
    b = boundary.set_index("date") if len(boundary) else pd.DataFrame()
    ev = (bp_events[bp_events["series"] == BOUNDARY_SYMBOL]
          if "series" in bp_events.columns else bp_events.iloc[0:0])
    L: list[str] = []
    if not len(ev):
        return (f"規則 1 は {BOUNDARY_SYMBOL} で 1 件も発火しなかった。schema が名指しする "
                "2026-03-30/31 の 2 行欠陥が捕まっていないので、規則の閾値と"
                "封印期間内の実データを突き合わせる必要がある。")
    e = ev.iloc[0]
    c0 = float(e["baseline_close_c0"])
    rev = float(e["revert_close"])
    L.append(f"**規則 1(誤プリント連)**は {e['first_date']}/{e['last_date']} の 2 行"
             f"(k = {int(e['k'])})を捕まえた。基準行は連の直前の 1 行 {e['baseline_date']} "
             f"(c0 = {c0:,.2f} 円)で、2 行の open と close はいずれも c0 から約 −90%"
             f"(30% 超)離れ、直後の {e['revert_date']} の close {rev:,.2f} 円が c0 の "
             f"{(rev / c0 - 1) * 100:+.2f}%(±5% 以内)に戻る。1 行規則では捕まらない "
             "2 行連続の欠陥であり、監査 3 の指摘で k ≤ 3 まで許した事前登録の判断が"
             "そのまま効いた形になる。")

    def flag(d: str, col: str) -> bool:
        return bool(b.loc[d, col]) if d in b.index else False

    def excluded(d: str) -> bool:
        return bool(b.loc[d, "pair_excluded"]) if d in b.index else False

    def num(d: str, col: str) -> float:
        return float(b.loc[d, col]) if d in b.index else float("nan")

    d1, d2 = str(e["first_date"]), str(e["last_date"])
    d_rev = str(e["revert_date"])
    after = b.index[list(b.index).index(d_rev) + 1] if d_rev in b.index and \
        list(b.index).index(d_rev) + 1 < len(b.index) else None

    r2_bits = [d for d in (d1, d2, d_rev) if flag(d, "flag_rule2_split")]
    L.append(f"**規則 2(split_candidate)**が発火したのは "
             + (", ".join(r2_bits) if r2_bits else "この窓では 0 行")
             + "。" + (
                 f"{d1} は close が直前行の 1/10 に落ち、翌行でその水準が持続するため"
                 "「丸い比率で水準が持続」の定義に当てはまる。"
                 if d1 in r2_bits else "")
             + (f"復帰行 {d_rev} は比率が ×10 の許容(±2%)を外れるため規則 2 では"
                "拾われていない(規則 1 側で連の復帰確認行として使われている)。"
                if d_rev not in r2_bits else ""))

    L.append(f"**{d2} → {d_rev} のペア**は、{d2} が規則 1 の誤プリント行であるため"
             f"**除外**された(除外 = {excluded(d2)})。"
             + (f"**{d_rev} → {after} のペア**は、どちらの行にも欠陥フラグが立たないため"
                f"**判定分母に残っている**(除外 = {excluded(d_rev)}、"
                f"r_night = {num(d_rev, 'pair_r_night_bps'):,.2f}bps、"
                f"保守コスト {num(d_rev, 'pair_cost_cons_bps'):,.2f}bps)。"
                if after is not None else ""))

    pre = num(d1, "band_price_used")
    L.append(
        f"**実際の 10:1 分割({SPLIT_EFFECTIVE.date()} 効力、野村 AM 適時開示 2026-02-17)は "
        "CSV 上に水準の段差を作らない**。ベンダーが分割調整を誤った開始日から適用していた"
        f"ため分割前区間はすでに実勢の 1/10 になっており、分割後の真の価格とほぼ連続する"
        f"({e['baseline_date']} の {c0:,.2f} 円 → {d_rev} の {rev:,.2f} 円 = "
        f"{(rev / c0 - 1) * 100:+.2f}%)。したがって分割をまたぐ経済的リターンは CSV の比率"
        "がそのまま正しく、規則 2 による追加除外も価格の再調整も要らない。分割日をまたぎ"
        f"得た唯一のペア({d2} → {d_rev})は、その手前の 2 行欠陥のせいで規則 1 が既に"
        "除外している。")
    L.append(
        f"価格水準補正の境界も同じ場所にある: 補正区間は "
        f"{PRICE_LEVEL_CORRECTIONS['1306.T'][0][1]} で終わるので、"
        f"{SPLIT_EFFECTIVE.date()} 以降の CSV は真の分割後価格として ×10 を掛けない。"
        f"上表の「帯に使う価格」列がその切り替わりを示す({e['baseline_date']} = "
        f"{num(str(e['baseline_date']), 'band_price_used'):,.2f} 円 → {d_rev} = "
        f"{num(d_rev, 'band_price_used'):,.2f} 円)。"
        f"欠陥 2 行にも補正が掛かって {pre:,.2f} 円と表示されるが、"
        "この 2 行は規則 1 で除外済みなので判定には一切入らない。")
    return "\n\n".join(L)

def build_results_md(results, control4, summary_df, indicator_df, rule_rows,
                     cost_rows, sign_rows, corr, residual_rows, regime_rows,
                     c1_rows, c2_rows, c3_rows, c4_rows, mde_rows, boundary,
                     bp_events, bar_rows, fals_rows, hold_rows, bar_by_sym,
                     exist_flags, n_exist_zero, fals_exist_met, md5_rows,
                     steps, diag_rows) -> str:
    L: list[str] = []
    a = L.append
    a("# P2-03 最終評価(封印期間、1 回のみ)— 数値報告")
    a("")
    a(f"実行日 2026-09-06 / seed {RUN_SEED} / git {_git_rev()[:12]} / 単位 {UNIT} / "
      f"封印期間 {SEALED_START.date()}..{SEALED_END.date()} / 累計 N = {CUMULATIVE_N}。")
    a(f"採用構成: 反復 1(1306.T の価格水準補正 ×10、{PRICE_LEVEL_CORRECTIONS['1306.T'][0][0]}"
      f"..{PRICE_LEVEL_CORRECTIONS['1306.T'][0][1]}、呼値帯とコストのみ)。")
    a(f"読み込みは `load_sealed(path, \"{UNIT}\", token=UNSEAL_TOKEN)` のみ"
      "(env `PHASE2_FINAL_EVAL=P2-03` + オーナー承認ファイル + トークンの三重ゲート)。"
      "P2-01 / P2-02 の封印データには一切触れていない。")
    a("欠陥規則・呼値帯・コスト・ペア構築は開発セットの実行体 "
      "`scripts/phase2/p2_03_run.py::build_series_result` を**そのまま**呼んでおり、"
      "開発セットとの差は読み込み関数だけである。")
    a("")
    a("**本書は数値の報告のみで、採用・棄却の判断は行わない(オーナーが決める)。**")
    a("")

    a("## 1. 入力の同一性(SEALED.json の MD5 との照合)")
    a("")
    a(_table(md5_rows, [("series", "系列", -1), ("md5_sealed_json", "SEALED.json", -1),
                        ("md5_now", "実行時", -1), ("match", "一致", -1)]))
    a("")
    a(f"不一致 {steps['input_md5_mismatches']} 件。フォワード窓 "
      "(`forward_start` = 2026-09-06)に該当する行はスナップショット "
      "(最終行 2026-09-04)に存在しないため、本評価は歴史的ホールドアウトのみで構成される。")
    a("")

    a("## 2. 母集団と除外の内訳(封印期間)")
    a("")
    a(_table(rule_rows, [
        ("series", "系列", -1), ("n_rows_sealed", "封印行数", 0),
        ("n_pairs_after_endpoint_rule", "端点規則後ペア", 0),
        ("rule1_badprint_rows", "規則1 誤プリント行", 0),
        ("rule1_badprint_runs", "規則1 連数", 0),
        ("rule1_one_sided_info_rows", "規則1 片側(情報)", 0),
        ("rule2_split_rows", "規則2 分割行", 0),
        ("rule3_null_rows", "規則3 null行", 0),
        ("rule5_ghost_rows", "規則5 幽霊行", 0),
        ("n_pairs_excluded", "除外ペア", 0),
        ("n_pairs_clean", "判定分母", 0)]))
    a("")
    a("端点規則: ペア (t, t+1) は両日が封印期間内のときだけ採用する。封印セットの"
      "**先頭行は規則 1 の基準値 c0 を持たず、末尾行は復帰確認行を持たない**ため、"
      "この 2 行は規則 1 の判定対象外(事前登録どおり)。")
    a("")

    a("## 3. 規則 1 が捕まえたもの(2026-03-30/31 を含む)")
    a("")
    if len(bp_events):
        a(_table(bp_events.to_dict("records"), [
            ("series", "系列", -1), ("k", "連長 k", 0),
            ("first_date", "先頭日", -1), ("last_date", "末尾日", -1),
            ("baseline_date", "基準行", -1), ("baseline_close_c0", "c0(円)", 2),
            ("revert_date", "復帰行", -1), ("revert_close", "復帰 close(円)", 2)]))
    else:  # pragma: no cover - depends on the sealed data
        a("規則 1 に該当する連は 0 件。")
    a("")
    a("### 2026-03-20 .. 2026-04-10 の 1306.T(生の値と規則の判定)")
    a("")
    a(_table(boundary.to_dict("records"), [
        ("date", "日付", -1), ("open_csv", "open(CSV)", 2),
        ("close_csv", "close(CSV)", 2), ("volume", "出来高", 0),
        ("flag_rule1_badprint", "規則1", -1), ("flag_rule2_split", "規則2", -1),
        ("band_price_used", "帯に使う価格", 2), ("tick_yen", "呼値", 2),
        ("pair_to", "→", -1), ("pair_r_night_bps", "r_night(bps)", 2),
        ("pair_cost_cons_bps", "コスト(bps)", 2),
        ("pair_excluded", "除外", -1)]))
    a("")
    a(_boundary_narrative(boundary, bp_events))
    a("")

    a("## 4. 主指標(除外前後 × 楽観 / 保守)")
    a("")
    a(f"CI はブロック・ブートストラップ(ブロック長 {BOOT_BLOCK} 営業日、"
      f"リサンプル {BOOT_N:,}、percentile 法、seed {RUN_SEED})。単位は bps/日。"
      "楽観 = 手数料 0 + 丸め 0(= **存在**の判定側)、"
      "保守 = 手数料 0 + 呼値 1 ティック/片側(= **取引可能**の判定側)。")
    a("")
    a(_table(indicator_df.to_dict("records"), [
        ("series", "系列", -1), ("stage", "除外", -1),
        ("cost_scenario", "費用", -1), ("n", "n", 0), ("mean", "平均(bps)", 3),
        ("ci_lo", "CI下", 3), ("ci_hi", "CI上", 3), ("sd", "SD", 2),
        ("t", "t", 2), ("hit_rate", "勝率", 4), ("sharpe", "Sharpe(年率)", 3)]))
    a("")

    a("## 5. 系列別サマリ(除外後)")
    a("")
    a(_table(summary_df.to_dict("records"), [
        ("series", "系列", -1), ("n_clean", "n", 0),
        ("mean_opt_bps", "楽観平均", 3), ("opt_ci_lo", "CI下", 3),
        ("opt_ci_hi", "CI上", 3), ("mean_cost_cons_bps", "平均コスト(往復)", 2),
        ("mean_cons_bps", "保守平均", 3), ("cons_ci_lo", "CI下", 3),
        ("cons_ci_hi", "CI上", 3), ("mean_day_bps", "日中平均", 3),
        ("night_minus_day_bps", "夜間−日中", 3),
        ("night_minus_day_ci_lo", "CI下", 3), ("night_minus_day_ci_hi", "CI上", 3),
        ("opt_sharpe", "Sharpe(楽観)", 3), ("cons_sharpe", "Sharpe(保守)", 3),
        ("max_dd_opt_bps", "最大DD(楽観)", 1),
        ("max_dd_cons_bps", "最大DD(保守)", 1),
        ("hit_rate_opt", "勝率", 4)]))
    a("")

    a("## 6. コスト(呼値 1 ティックの重さ)")
    a("")
    a(_table(cost_rows, [
        ("series", "系列", -1), ("band_price_min", "帯に使う価格 最小", 1),
        ("band_price_max", "同 最大", 1), ("tick_yen_min", "呼値 最小", 1),
        ("tick_yen_max", "呼値 最大", 1),
        ("cost_roundtrip_mean_bps", "往復コスト平均(bps)", 2),
        ("cost_roundtrip_min_bps", "同 最小", 2),
        ("cost_roundtrip_max_bps", "同 最大", 2),
        ("last_band_price_used", "最終行の価格(円)", 2),
        ("last_tick_yen", "同 呼値(円)", 1),
        ("per_side_bps_now", "現在の片側(bps)", 2)]))
    a("")
    row1306 = next(r for r in cost_rows if r["series"] == BOUNDARY_SYMBOL)
    a(f"1306.T は 2026-04-01 の 10:1 分割で価格水準が 1/10 になったため、"
      f"**現在の呼値 1 円は片側 {row1306['per_side_bps_now']:.2f}bps"
      f"(往復 {2 * row1306['per_side_bps_now']:.2f}bps)**"
      f"— 分割前(補正後の実勢 1,900〜4,300 円)の平均 "
      f"{row1306.get('cost_mean_bps_pre_2026_04_01', float('nan')):.2f}bps/往復 に対し、"
      f"分割後は平均 {row1306.get('cost_mean_bps_post_2026_04_01', float('nan')):.2f}bps/往復"
      f"(n = {row1306.get('n_post_2026_04_01', 0)})。"
      "呼値の重さは価格水準の関数なので、分割は取引可能性を約 10 倍不利にした。")
    a("")

    a("## 7.「同様の」の 3 条件")
    a("")
    a("(a) ゼロより有意に大きいか = §4 の楽観 CI。(b) 1321 との符号一致:")
    a("")
    a(_table(sign_rows, [("series", "系列", -1),
                         ("mean_gross_r_night_bps", "平均 r_night(bps)", 3),
                         ("sign_matches_1321", "1321と符号一致", -1)]))
    a("")
    a("(c) 系列間相関(r_night、除外後、共通日)。4 系列は独立な確認とは数えない"
      "(株式因子 1 つとして扱う):")
    a("")
    a("| | " + " | ".join(corr.columns) + " |")
    a("|" + "---|" * (len(corr.columns) + 1))
    for idx, r in corr.iterrows():
        a(f"| {idx} | " + " | ".join(f"{v:.3f}" for v in r) + " |")
    a("")
    a("1321 に対する残差(r_night_etf − r_night_1321、共通日):")
    a("")
    a(_table(residual_rows, [("series", "系列", -1), ("n_common", "n", 0),
                             ("mean_bps", "残差平均(bps)", 3),
                             ("ci_lo", "CI下", 3), ("ci_hi", "CI上", 3)]))
    a("")

    a("## 8. 対照")
    a("")
    a(f"対照 1: 符号シャッフル({SHUFFLE_N:,} 回、グロス r_night)。累計 N = {CUMULATIVE_N} "
      "なので最良取りの補正は不要(単一構成の帰無そのもの)。")
    a("")
    a(_table(c1_rows, [("series", "系列", -1), ("n", "n", 0),
                       ("observed_mean_gross_bps", "実測平均(bps)", 3),
                       ("null_mean_bps", "帰無平均", 3),
                       ("null_p95_bps", "帰無95点", 3),
                       ("observed_gt_null_p95", "実測 > 帰無95点", -1),
                       ("observed_mean_cons_bps", "保守後の実測平均", 3),
                       ("null_p95_minus_mean_cost_bps", "帰無95点−平均コスト", 3)]))
    a("")
    a("対照 2(診断のみ): 20 日実現ボラ三分位ごとの実測平均 vs 全体プールからの無作為保有:")
    a("")
    a(_table(c2_rows, [("series", "系列", -1), ("tercile", "三分位", -1),
                       ("n", "n", 0), ("observed_mean_bps", "実測平均", 3),
                       ("null_mean_bps", "null平均", 3),
                       ("null_ci_lo", "null CI下", 3), ("null_ci_hi", "null CI上", 3)]))
    a("")
    a("対照 3: 符号反転(夜間売り持ち。費用は方向によらず同額):")
    a("")
    a(_table(c3_rows, [("series", "系列", -1), ("n", "n", 0),
                       ("net_short_opt_mean_bps", "売り 楽観(bps)", 3),
                       ("net_short_opt_ci_lo", "CI下", 3),
                       ("net_short_opt_ci_hi", "CI上", 3),
                       ("net_short_cons_mean_bps", "売り 保守(bps)", 3),
                       ("net_short_cons_ci_lo", "CI下", 3),
                       ("net_short_cons_ci_hi", "CI上", 3)]))
    a("")
    a("対照 4(診断専用、選択には使わない): 個別株 4 銘柄 — 指数 ETF に固有か市場全体か:")
    a("")
    a(_table(c4_rows, [("series", "銘柄", -1), ("n_clean", "n", 0),
                       ("mean_gross_bps", "平均 r_night(bps)", 3),
                       ("ci_lo", "CI下", 3), ("ci_hi", "CI上", 3),
                       ("sharpe", "Sharpe", 3)]))
    a("")

    a("## 9. 2024-11-05 引け板寄せ 15:30 化の前後(記述のみ、判定に使わない)")
    a("")
    a(_table(regime_rows, [("series", "系列", -1), ("regime", "区分", -1),
                           ("n", "n", 0), ("mean_opt_bps", "楽観平均", 3),
                           ("opt_ci_lo", "CI下", 3), ("opt_ci_hi", "CI上", 3),
                           ("mean_cons_bps", "保守平均", 3),
                           ("cons_ci_lo", "CI下", 3), ("cons_ci_hi", "CI上", 3),
                           ("mean_cost_bps", "平均コスト", 2)]))
    a("")

    a("## 10. MDE の再計算(封印標本、記録のみ)")
    a("")
    a(_table(mde_rows, [("series", "系列", -1), ("n", "n", 0),
                        ("sd_bps", "σ(bps)", 2), ("se_bps", "SE(bps)", 3),
                        ("mde_bps_independent", "独立標本 MDE", 3),
                        ("mde_bps_effective_from_ci", "CI 幅からの実効 MDE", 3),
                        ("mde_bps_registered", "事前登録 MDE", 2)]))
    a("")

    a("## 11. 診断(記述のみ、選択に使わない)")
    a("")
    diag_df = pd.DataFrame(diag_rows)
    if len(diag_df):
        counts = diag_df.groupby(["series", "dimension"]).size().reset_index(
            name="n_buckets")
        a(_table(counts.to_dict("records"), [("series", "系列", -1),
                                             ("dimension", "次元", -1),
                                             ("n_buckets", "バケット数", 0)]))
        a("")
        a("全件は `diagnostics.csv`(ボラ三分位・曜日・月・年代)。p 値も有意判定も書かない。")
    a("")

    a("## 12. 事前登録のバーと反証文(数値の対照のみ、判断はしない)")
    a("")
    a("PREREG「最終評価」の原文:")
    a("")
    a("> - バー: 累計 N の帰無 95 点超、かつ保守コストでの費用後平均夜間リターンの 95% CI が"
      "正(各 ETF)、かつ日経 225 ETF と符号一致。")
    a("> - 反証文(存在): 封印期間(欠陥規則で除外後、楽観コスト)で「TOPIX・JPX400・"
      "グロース 250 の ETF のうち 2 つ以上で平均夜間リターンの 95% CI がゼロを含む」なら"
      "「同様の夜間プレミアムが存在する」は棄却。")
    a("> - 反証文(取引可能): 保守コスト後の 95% CI がゼロを含む銘柄は「存在するが取引不能"
      "(丸め次第)」とし、引き金 = スプレッドの実測 / 高価格の代替銘柄。")
    a("")
    a("### バー(各 ETF、3 条件すべてを要求)")
    a("")
    a(_table(bar_rows, [("series", "系列", -1), ("criterion", "条件", -1),
                        ("measured", "実測", -1), ("outcome", "判定", -1)]))
    a("")
    a("### 反証文")
    a("")
    a(_table(fals_rows, [("kind", "種別", -1), ("series", "系列", -1),
                         ("criterion", "文", -1), ("measured", "実測", -1),
                         ("outcome", "判定", -1)]))
    a("")
    a(f"反証文(存在)の条件「2 つ以上」に対し、楽観 CI がゼロを含む ETF は "
      f"**{n_exist_zero} / 3**。よって当該反証文は "
      f"**{'満たす' if fals_exist_met else '満たさない'}**。")
    a("")
    a("### 保留区分と再評価の引き金")
    a("")
    a(_table(hold_rows, [("series", "系列", -1), ("criterion", "区分", -1),
                         ("measured", "実測", -1), ("outcome", "判定", -1),
                         ("trigger", "引き金", -1)]))
    a("")

    a("## 13. 事前登録からの逸脱")
    a("")
    a("- **代替銘柄(1348.T 等)は取得していない。** 事前登録は「取得できない場合はその旨を"
      "記録して主系列のみで判定」と定めており、本評価は最終評価の実行段階であって新規データ"
      "取得の段階ではないため、主系列のみで報告した。1348.T の取得は保留区分の**引き金**"
      "として明記してある(§12)。")
    a("- バー 1 の「累計 N の帰無 95 点」は、反復台帳の累計 N = 1(反復 1 はデータ修正であって"
      "構成の追加ではない)に従い、単一構成の符号シャッフル帰無をそのまま用いた。"
      "比較量はグロス平均(対照 1 の事前登録どおりの定義)で、保守コストを引いた版も併記した。")
    a("- 反証文(取引可能)の原文は「CI がゼロを含む」だが、CI 全体が負の場合は文字どおりには"
      "「含まない」。取り違えを避けるため両方(ゼロを含むか / CI が正でないか)を数値で併記した。")
    a("- 本評価のスクリプトは 3 回実行した(`UNSEAL_LOG.jsonl` に 3 回 × 8 ファイル = 24 行"
      "すべて記録されている)。1 回目 = 本番実行。2 回目 = §3 の**文章**(規則 1 / 規則 2 が "
      "2026-03-30..04-02 に何をしたかの読み下し)を追加して再実行。3 回目 = 規則 1 の該当が "
      "0 件だったときに §3 の文章生成が落ちる不具合(空の事象表を列名で参照していた)を"
      "直して再実行。**23 個の CSV はいずれも 1 回目とバイト一致**で、seed・入力 MD5・"
      "判定に関わる数値は 3 回とも同一。変わったのは RESULTS.md の本文と RUN.json の "
      "`script_md5` / 監査ログの時刻だけである。3 回目の修正が本データの文章を変えない"
      "ことは、保存済みの `boundary_2026_1306.csv` / `rule1_badprint_events.csv` から"
      "文章生成関数だけを単独で呼び、修正前後で出力がバイト一致することで確認した"
      "(この確認は封印データを読んでいない)。")
    a("- 上記以外の逸脱はない。閾値 30% / ±5% / k ≤ 3、split_candidate の定義、"
      "ブロック長 20・リサンプル 2,000・シャッフル 1,000・seed 20260906、"
      "手数料 0 円・呼値表・端点規則・対照の定義はすべて凍結された事前登録どおり。")
    a("")
    return "\n".join(L) + "\n"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", type=Path, default=None,
                   help="Output directory (default: backtest_data/phase2_runs/"
                        "P2-03/final_20260906).")
    return p.parse_args(argv)


if __name__ == "__main__":  # pragma: no cover
    _a = _parse_args()
    raise SystemExit(main(out_dir=_a.out))

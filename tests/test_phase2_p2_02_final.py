"""Tests for the P2-02 FINAL (sealed-period) evaluator, scripts/phase2/p2_02_final.py.

Two things are checked, neither of which opens a real repo data file:

  1. the three unseal guards — env `PHASE2_FINAL_EVAL=P2-02`, the owner's
     `UNSEAL_APPROVED` file, and the explicit token — each of which must, on
     its own, make the script refuse, and none of which may be satisfied for
     a unit other than P2-02. Run against a TEMPORARY root, so no real seal
     record, approval file or sealed data file is involved;
  2. an end-to-end run on a SYNTHETIC repo root (its own SEALED.json, its own
     price / dividend / index files) whose sealed window carries a planted
     overnight drift and planted ex-dividend drops. The evaluator must
     recover the drift net of the pre-registered conservative cost, must
     evaluate only pairs whose BOTH days lie in the sealed window (no pre-seal
     leakage even though the pre-seal calendar is used for the ex-date
     derivation), and must recover the planted dividend drop through the
     adjustment.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "src"))

from bot.research import overnight as onr  # noqa: E402
from bot.research.sealed import UNSEAL_TOKEN, SealedDataError  # noqa: E402
from phase2 import p2_02_final as pf  # noqa: E402
from phase2 import p2_02_run as p2  # noqa: E402


# ---------------------------------------------------------------------------
# 1. the three unseal guards
# ---------------------------------------------------------------------------

def _guard_root(tmp_path: Path, approved: bool) -> Path:
    d = tmp_path / "backtest_data" / "phase2_sealed" / "P2-02"
    d.mkdir(parents=True)
    if approved:
        (d / "UNSEAL_APPROVED").write_text("unit: P2-02\napproved_by: test\n",
                                           encoding="utf-8")
    return tmp_path


def test_guards_pass_only_when_all_three_are_present(tmp_path, monkeypatch):
    root = _guard_root(tmp_path, approved=True)
    monkeypatch.setenv("PHASE2_FINAL_EVAL", "P2-02")
    pf.check_guards(root=root, token=UNSEAL_TOKEN)   # must not raise


def test_guard_env_missing_or_wrong_unit_refuses(tmp_path, monkeypatch):
    root = _guard_root(tmp_path, approved=True)
    monkeypatch.delenv("PHASE2_FINAL_EVAL", raising=False)
    with pytest.raises(SealedDataError) as e:
        pf.check_guards(root=root, token=UNSEAL_TOKEN)
    assert "PHASE2_FINAL_EVAL" in str(e.value)
    monkeypatch.setenv("PHASE2_FINAL_EVAL", "P2-01")
    with pytest.raises(SealedDataError):
        pf.check_guards(root=root, token=UNSEAL_TOKEN)


def test_guard_missing_owner_approval_file_refuses(tmp_path, monkeypatch):
    root = _guard_root(tmp_path, approved=False)
    monkeypatch.setenv("PHASE2_FINAL_EVAL", "P2-02")
    with pytest.raises(SealedDataError) as e:
        pf.check_guards(root=root, token=UNSEAL_TOKEN)
    assert "UNSEAL_APPROVED" in str(e.value)


def test_guard_wrong_token_refuses(tmp_path, monkeypatch):
    root = _guard_root(tmp_path, approved=True)
    monkeypatch.setenv("PHASE2_FINAL_EVAL", "P2-02")
    with pytest.raises(SealedDataError) as e:
        pf.check_guards(root=root, token="I_UNDERSTAND_REAL_MONEY")
    assert "token" in str(e.value)


def test_guards_refuse_any_unit_other_than_p2_02(tmp_path, monkeypatch):
    """The owner's approval is scoped to P2-02; P2-01 / P2-03 must stay shut
    even if someone points the env and the token at them."""
    root = _guard_root(tmp_path, approved=True)
    monkeypatch.setenv("PHASE2_FINAL_EVAL", "P2-03")
    with pytest.raises(SealedDataError) as e:
        pf.check_guards(root=root, token=UNSEAL_TOKEN, unit="P2-03")
    assert "P2-02" in str(e.value)


def test_main_refuses_before_touching_anything_when_a_guard_is_missing(
        tmp_path, monkeypatch):
    """main() must fail on the guards BEFORE creating its output directory or
    reading any file."""
    root = _guard_root(tmp_path, approved=True)
    out = tmp_path / "out"
    monkeypatch.delenv("PHASE2_FINAL_EVAL", raising=False)
    with pytest.raises(SealedDataError):
        pf.main(out_dir=out, root=root, token=UNSEAL_TOKEN)
    assert not out.exists()

    monkeypatch.setenv("PHASE2_FINAL_EVAL", "P2-02")
    with pytest.raises(SealedDataError):
        pf.main(out_dir=out, root=root, token="nope")
    assert not out.exists()


def test_final_configuration_constants_match_the_prereg_and_ledger():
    assert pf.UNIT == "P2-02"
    assert pf.CUMULATIVE_N == 1                   # ITER.md: iteration 0 only
    assert (pf.SEALED_START, pf.SEALED_END) == (
        pd.Timestamp("2021-04-13"), pd.Timestamp("2026-09-03"))
    assert pf.REGIME_SPLIT == pd.Timestamp("2024-11-05")
    assert (pf.BLOCK, pf.N_BOOT, pf.N_SHUFFLE, pf.SEED) == (20, 2000, 1000, 20260906)
    assert pf.DD_BAR_MULTIPLE == 3.0
    assert pf.THIN_VOLUME_THRESHOLD == 5000


# ---------------------------------------------------------------------------
# 2. end-to-end on a synthetic sealed window
# ---------------------------------------------------------------------------

DEV_START = "2019-01-02"
SEAL_FROM = "2024-01-02"
LAST_DAY = "2024-12-31"
PLANTED_BPS = 40.0
DIV_AMOUNT = 30.0
RECORD_DATES = ["2024-05-10", "2024-08-10"]


def _synthetic_prices(dates, drift_bps, seed, start_px=1900.0, ex_dates=(),
                      div_amount=0.0, noise_bps=15.0, drift_from=SEAL_FROM):
    """A daily OHLCV tape whose overnight leg carries `drift_bps` on average
    INSIDE the sealed window only (the pre-seal part has drift 0, which also
    keeps the price level realistic — 1343 trades around 1,900 yen, i.e. in
    the 1-yen tick band).

    open(t+1) = close(t) * (1 + (drift + noise)/1e4) − (the distribution, on a
    planted ex-date), close(t) = open(t) * (1 + day noise/1e4). No zero prints,
    no flat zero-volume rows, no >30% jumps: the defect rules must find nothing
    to exclude, so the recovered mean is the planted one.
    """
    rng = np.random.default_rng(seed)
    ex = set(pd.Timestamp(d) for d in ex_dates)
    drift_from = pd.Timestamp(drift_from)
    opens, highs, lows, closes, vols = [], [], [], [], []
    prev_close = start_px
    for i, d in enumerate(dates):
        if i == 0:
            o = start_px
        else:
            mu = drift_bps if pd.Timestamp(d) >= drift_from else 0.0
            o = prev_close * (1 + (mu + rng.normal(0, noise_bps)) / 1e4)
            if pd.Timestamp(d) in ex:
                o -= div_amount
        c = o * (1 + rng.normal(0, noise_bps) / 1e4)
        opens.append(o)
        closes.append(c)
        highs.append(max(o, c) * 1.001)
        lows.append(min(o, c) * 0.999)
        vols.append(500_000 + int(rng.integers(0, 1000)))
        prev_close = c
    return pd.DataFrame({"date": [pd.Timestamp(d).date() for d in dates],
                         "open": opens, "high": highs, "low": lows,
                         "close": closes, "volume": vols})


def _build_synthetic_root(tmp_path: Path) -> tuple[Path, list, list]:
    root = tmp_path
    data = root / "backtest_data" / "reit_onr_20260904"
    data.mkdir(parents=True)
    (root / "paper_logs").mkdir(parents=True)
    seal = root / "backtest_data" / "phase2_sealed" / "P2-02"
    seal.mkdir(parents=True)
    (seal / "UNSEAL_APPROVED").write_text("unit: P2-02\napproved_by: test\n",
                                          encoding="utf-8")

    days = list(pd.bdate_range(DEV_START, LAST_DAY))
    ex_dates = onr.ex_dates_from_record_dates(
        [pd.Timestamp(d) for d in RECORD_DATES], days)

    px_1343 = _synthetic_prices(days, PLANTED_BPS, seed=7, ex_dates=ex_dates,
                                div_amount=DIV_AMOUNT)
    px_1321 = _synthetic_prices(days, 0.0, seed=8, start_px=28000.0)
    px_1343.to_csv(data / "etf_1343_daily.csv", index=False)
    px_1321.to_csv(data / "etf_1321_daily.csv", index=False)
    pd.DataFrame({"ex_date": RECORD_DATES,
                  "amount": [DIV_AMOUNT] * len(RECORD_DATES)}).to_csv(
        data / "etf_1343_dividends.csv", index=False)

    idx_days = days[-200:]
    idx = px_1343[px_1343["date"].isin([d.date() for d in idx_days])].copy()
    idx = idx[["date", "open", "high", "low", "close"]]
    for col in ("open", "high", "low", "close"):
        idx[col] = idx[col] / 1.05
    idx.to_csv(data / "reit_index_daily.csv", index=False)

    pd.DataFrame(columns=["date_entry", "date_exit", "close_entry", "open_exit",
                          "qty", "dividend_yen", "pnl_yen", "etf_on_bps",
                          "index_on_bps", "gap_bps", "cum_pnl_yen"]).to_csv(
        root / "paper_logs" / "onr_ledger.csv", index=False)

    from bot.research.sealed import md5_of
    files = []
    for rel, tcol in (("backtest_data/reit_onr_20260904/etf_1343_daily.csv", "date"),
                      ("backtest_data/reit_onr_20260904/etf_1321_daily.csv", "date"),
                      ("backtest_data/reit_onr_20260904/etf_1343_dividends.csv", "ex_date"),
                      ("backtest_data/reit_onr_20260904/reit_index_daily.csv", "date")):
        files.append({"path": rel, "md5": md5_of(root / rel), "time_column": tcol,
                      "seal_from_ts": f"{SEAL_FROM}T00:00:00+00:00"})
    (seal / "SEALED.json").write_text(json.dumps({
        "unit": "P2-02",
        "forward_start": "2026-01-01T00:00:00+00:00",
        "files": files,
        "primary_series": "etf_1343_daily.csv",
    }, indent=2), encoding="utf-8")
    return root, days, ex_dates


def test_synthetic_sealed_window_recovers_the_planted_drift(tmp_path, monkeypatch):
    root, days, ex_dates = _build_synthetic_root(tmp_path)
    monkeypatch.setenv("PHASE2_FINAL_EVAL", "P2-02")
    out = tmp_path / "out"
    assert pf.main(out_dir=out, root=root, token=UNSEAL_TOKEN) == 0

    run = json.loads((out / "RUN.json").read_text(encoding="utf-8"))
    head = run["headline"]
    pairs = pd.read_csv(out / "pairs_1343_sealed.csv", parse_dates=["t_date", "t1_date"])
    kept = pairs[pairs["kept"]]

    # (a) no pre-seal leakage: every evaluated pair has BOTH days at/after the
    #     seal boundary, even though the pre-seal calendar fed the ex-date
    #     derivation.
    assert pairs["t_date"].min() >= pd.Timestamp(SEAL_FROM)
    assert pairs["t1_date"].max() <= pd.Timestamp(LAST_DAY)
    sealed_days = [d for d in days if d >= pd.Timestamp(SEAL_FROM)]
    assert len(pairs) == len(sealed_days) - 1
    assert run["n_at_each_step"]["calendar_days_pre_seal"] > 0

    # (b) the defect rules find nothing to exclude on a clean synthetic tape
    assert head["n_main"] == len(pairs)
    assert int(kept.shape[0]) == len(pairs)

    # (c) the planted drift is recovered gross, and net of the pre-registered
    #     conservative cost 2/close(t)*1e4
    assert head["mean_gross_bps"] == pytest.approx(PLANTED_BPS, abs=4.0)
    cost = float(kept["cost_conservative_bps"].mean())
    assert cost == pytest.approx(float((2.0 / kept["close_t"] * 1e4).mean()), rel=1e-9)
    assert head["mean_net_conservative_bps"] == pytest.approx(
        head["mean_gross_bps"] - cost, abs=1e-6)
    assert head["ci95"][0] > 0 and head["ci95"][1] > head["ci95"][0]

    # (d) the dividend adjustment recovers the planted ex-date drop: on those
    #     pairs the raw overnight return is short by amount/close(t), and the
    #     adjusted one is back on the drift.
    ex_pairs = kept[kept["t1_date"].isin([pd.Timestamp(d) for d in ex_dates])]
    assert len(ex_pairs) == len(RECORD_DATES)
    drop_bps = DIV_AMOUNT / ex_pairs["close_t"] * 1e4
    assert np.allclose(ex_pairs["r_night_adj_bps"] - ex_pairs["r_night_raw_bps"],
                       drop_bps, atol=1e-6)
    assert (ex_pairs["r_night_raw_bps"] < 0).all()
    assert head["mean_net_conservative_unadjusted_bps"] < head["mean_net_conservative_bps"]

    # (e) the bar / falsification block is rendered from those numbers
    bar = pd.read_csv(out / "bar_and_falsification.csv")
    assert set(bar["kind"]) == {"bar", "falsification"}
    assert set(bar["outcome"]) <= {"満たす", "満たさない"}
    ci_row = bar[bar["criterion"].str.startswith("バー2")].iloc[0]
    assert ci_row["outcome"] == "満たす"
    fals = bar[bar["kind"] == "falsification"].iloc[0]
    assert fals["outcome"] == "満たさない"   # CI is positive, so it does not contain 0

    # (f) the run is auditable: the unseal log grew, md5s match SEALED.json
    assert len(run["unseal_log_excerpt"]) >= 4
    assert all(r["match"] for r in run["inputs_md5_vs_sealed_json"])
    assert (root / "backtest_data" / "phase2_sealed" / "P2-02"
            / "UNSEAL_LOG.jsonl").is_file()

    # (g) the forward diagnostic ran on the sealed index file, ledger is empty
    assert run["forward_diagnostic"]["etf_vs_index"]["open_leg_pairs"] > 0
    assert run["forward_diagnostic"]["paper_ledger"]["rows"] == 0
    assert run["forward_diagnostic"]["paper_ledger"]["enough_rows"] is False

    md = (out / "RESULTS.md").read_text(encoding="utf-8")
    assert "最終評価" in md and "反証文" in md and "保留区分" in md
    # numbers only: no verdict is rendered anywhere in the report
    assert "本書は数値の報告のみで、採用・棄却の判断は行わない" in md
    for word in ("判定案", "を採用する", "本仮説を棄却"):
        assert word not in md


def test_synthetic_1321_is_evaluated_under_the_same_rules(tmp_path, monkeypatch):
    """The comparison instrument goes through the identical pipeline: same
    defect rules, same cost formula, same block bootstrap."""
    root, days, _ = _build_synthetic_root(tmp_path)
    monkeypatch.setenv("PHASE2_FINAL_EVAL", "P2-02")
    out = tmp_path / "out"
    pf.main(out_dir=out, root=root, token=UNSEAL_TOKEN)

    p1321 = pd.read_csv(out / "pairs_1321_sealed.csv", parse_dates=["t_date"])
    assert p1321["t_date"].min() >= pd.Timestamp(SEAL_FROM)
    # 1321 was generated with zero planted drift -> its net mean must be
    # clearly below 1343's, and the sign-match bar must therefore be reported.
    run = json.loads((out / "RUN.json").read_text(encoding="utf-8"))
    assert run["headline"]["mean_net_conservative_bps_1321"] < \
        run["headline"]["mean_net_conservative_bps"]
    summary = pd.read_csv(out / "main_summary.csv").set_index("metric")["value"]
    assert summary["cumulative_N"] == "1"
    assert summary["dividend_correction_used"] == "True"


def test_reused_dev_runner_functions_are_untouched():
    """The final evaluator must not have changed the dev-set runner's
    behaviour: the pre-registered constants it reuses are still the frozen
    ones, and the reused helpers still come from p2_02_run."""
    assert (p2.SEED, p2.BLOCK, p2.N_BOOT, p2.N_SHUFFLE) == (20260906, 20, 2000, 1000)
    assert p2.THIN_VOLUME_THRESHOLD == 5000
    assert (p2.BAD_PRINT_DEV_THRESHOLD, p2.BAD_PRINT_RECOVERY_THRESHOLD,
            p2.BAD_PRINT_MAX_RUN) == (0.30, 0.05, 3)
    for name in ("build_pair_table", "add_dividend_adjustment", "dividend_data_check",
                 "mean_ci_bootstrap", "sharpe_annualized", "max_drawdown",
                 "block_bootstrap_max_dd_median", "sign_reversal_stats",
                 "stratified_bootstrap_mean_dist", "exclusion_stage_stats"):
        assert getattr(pf, name) is getattr(p2, name)

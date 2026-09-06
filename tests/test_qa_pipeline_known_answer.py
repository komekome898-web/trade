"""Fast tests for scripts/qa/pipeline_known_answer_taker.py and
pipeline_known_answer_daily.py -- the PIPELINE known-answer tests required
by docs/PHASE2_SPEC.md §5 before grid groups G1-G3 (docs/PHASE2_GRID.md)
can start. These check that OUR OWN backtest/evaluation code recovers a
planted effect and reports a null as null; they are NOT auditor tests.

Uses small day counts (fewer than the scripts' full-scale defaults) purely
for test speed; both scripts are run at full scale separately with results
written to backtest_data/qa_pipeline_{taker,daily}_<date>/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "qa"))

import pipeline_known_answer_taker as qt  # noqa: E402
import pipeline_known_answer_daily as qd  # noqa: E402

TAKER_DAYS = 60     # full scale: the planted event rate needs this many days
                     # for the X=8bps case to clear MDE comfortably; kept at
                     # the script's own default rather than shrunk further.
DAILY_DAYS = 900    # shrunk from the 3,000-day default for test speed while
                     # keeping >=250 high-vol-tercile observations per Y.


@pytest.fixture(scope="module")
def taker_result(tmp_path_factory):
    out = tmp_path_factory.mktemp("qa_taker")
    return qt.generate(out, seed=qt.SEED, days=TAKER_DAYS)


@pytest.fixture(scope="module")
def daily_result(tmp_path_factory):
    out = tmp_path_factory.mktemp("qa_daily")
    return qd.generate(out, seed=qd.SEED, n_days=DAILY_DAYS)


# --------------------------------------------------------------------- taker


def test_taker_determinism(tmp_path):
    r1 = qt.generate(tmp_path / "a", seed=qt.SEED, days=10)
    r2 = qt.generate(tmp_path / "b", seed=qt.SEED, days=10)
    for x in qt.X_VALUES:
        assert r1["per_x"][x]["recovered_net_bps_mean"] == r2["per_x"][x]["recovered_net_bps_mean"]
        assert r1["per_x"][x]["n_trades"] == r2["per_x"][x]["n_trades"]


def test_taker_different_seed_changes_result(tmp_path):
    r1 = qt.generate(tmp_path / "a", seed=qt.SEED, days=10)
    r2 = qt.generate(tmp_path / "b", seed=qt.SEED + 1, days=10)
    assert r1["per_x"][0.0]["recovered_net_bps_mean"] != r2["per_x"][0.0]["recovered_net_bps_mean"]


def test_taker_cost_model_uses_measured_constant(taker_result):
    prov = taker_result["sealed"]["cost_provenance"]
    assert prov["taker_fee_pct"]["source_type"] in ("measured", "primary_document")
    assert prov["realized_round_trip_bps"]["source_type"] == "measured"


def test_taker_assumed_constant_raises(tmp_path):
    from bot.constants import AssumedConstantError, load_constants, require_source
    consts = load_constants(REPO_ROOT)
    with pytest.raises(AssumedConstantError):
        require_source("bitflyer_fx_btc_jpy.taker_round_trip_floor_bps_OLD", consts)


def test_taker_recovers_planted_effect_within_mde(taker_result):
    for x in qt.X_VALUES:
        r = taker_result["per_x"][x]
        assert r["n_trades"] >= 5, "not enough events to test recovery meaningfully"
        assert r["within_mde"], f"X={x}: recovered {r['recovered_net_bps_mean']} not within " \
            f"MDE {r['mde_bps']} of planted {r['planted_net_bps']}"


def test_taker_null_is_reported_as_null(taker_result):
    zero = taker_result["per_x"][0.0]
    assert abs(zero["gross_t_stat"]) < 1.96, \
        f"X=0 gross t-stat={zero['gross_t_stat']} is significant -- null-as-null failed"


def test_taker_larger_effect_more_significant(taker_result):
    t0 = abs(taker_result["per_x"][0.0]["gross_t_stat"])
    t3 = abs(taker_result["per_x"][3.0]["gross_t_stat"])
    t8 = abs(taker_result["per_x"][8.0]["gross_t_stat"])
    assert t8 > t0

def test_taker_all_trades_exit_by_time_exit(taker_result):
    for x in qt.X_VALUES:
        assert taker_result["per_x"][x]["n_other_exit_reason"] == 0


def test_taker_engine_has_no_validity_filtering_is_flagged(taker_result):
    """The known pipeline gap: src/bot/backtest/engine.py does no maintenance-
    window / bad-print filtering. This must show up as a documented finding,
    not be silently absent."""
    findings_text = " ".join(taker_result["findings"])
    assert "no maintenance-window or bad-print filtering" in findings_text


def test_taker_tapes_contain_planted_clutter(taker_result):
    sealed = taker_result["sealed"]
    assert sealed["n_maintenance_rows"] > 0
    assert sealed["n_bad_prints"] == qt.N_BAD_PRINTS


# --------------------------------------------------------------------- daily


def test_daily_determinism(tmp_path):
    r1 = qd.generate(tmp_path / "a", seed=qd.SEED, n_days=250)
    r2 = qd.generate(tmp_path / "b", seed=qd.SEED, n_days=250)
    for y in qd.Y_VALUES:
        assert r1["per_y"][y]["regime"]["high"]["mean_bps"] == \
            r2["per_y"][y]["regime"]["high"]["mean_bps"]


def test_daily_computation_path_is_the_real_onr_module(daily_result):
    assert "src/bot/research/overnight.py" in daily_result["sealed"]["computation_path"]
    from bot.research import overnight
    assert qd.onr is overnight  # literally the same imported module, not a reimplementation
    import research_overnight_onr as onr_script
    assert onr_script.overnight_returns is overnight.overnight_returns  # ONR imports the same fn
    assert onr_script.drop_glitches is overnight.drop_glitches


def test_daily_recovers_planted_premium_in_high_tercile(daily_result):
    for y in qd.Y_VALUES:
        h = daily_result["per_y"][y]["regime"]["high"]
        assert h["n"] >= 30
        assert h["within_mde"], f"Y={y}: recovered {h['mean_bps']} not within MDE {h['mde_bps']}"


def test_daily_null_is_reported_as_null(daily_result):
    h0 = daily_result["per_y"][0.0]["regime"]["high"]
    assert abs(h0["t_stat"]) < 1.96, f"Y=0 high-tercile t-stat={h0['t_stat']} is significant"


def test_daily_effect_concentrated_in_high_tercile_only(daily_result):
    for y in qd.Y_VALUES:
        regime = daily_result["per_y"][y]["regime"]
        for name in ("low", "mid"):
            assert abs(regime[name]["t_stat"]) < 1.96, \
                f"Y={y} {name}-tercile t-stat={regime[name]['t_stat']} should be null"


def test_daily_larger_premium_more_significant(daily_result):
    t0 = abs(daily_result["per_y"][0.0]["regime"]["high"]["t_stat"])
    t5 = abs(daily_result["per_y"][5.0]["regime"]["high"]["t_stat"])
    assert t5 > t0


def test_daily_split_and_bad_prints_are_planted_and_recorded(daily_result):
    sealed = daily_result["sealed"]
    assert sealed["split_ratio_unadjusted"] == qd.SPLIT_RATIO
    assert len(sealed["bad_print_days_index"]) == qd.N_BAD_PRINT_DAYS
    assert sealed["split_date_flagged_leg"] not in sealed["bad_print_dates_flagged_legs"]


def test_daily_drop_glitches_catches_the_known_defect_dates(daily_result):
    expected = set(daily_result["sealed"]["expected_dropped_dates"])
    for y in qd.Y_VALUES:
        dropped = set(daily_result["per_y"][y]["etf_glitches_dropped_dates"])
        missing = expected - dropped
        assert not missing, f"Y={y}: drop_glitches missed {missing}"


def test_daily_split_indistinguishable_from_glitch_is_flagged(daily_result):
    findings_text = " ".join(daily_result["findings"])
    assert "INDISTINGUISHABLE to drop_glitches" in findings_text


def test_daily_data_quality_scan_ran_and_flagged_something(daily_result):
    dq = daily_result["sealed"]["data_quality_scan"]
    assert dq["files_checked"] >= 1
    assert "extreme_return" in dq["checks_fired"]
    assert dq["extreme_return_count"] > 0


def test_daily_dividend_case_matches_hand_derivation(daily_result):
    dc = daily_result["dividend_case"]
    assert dc["exact_match"], f"max abs diff vs hand derivation: {dc['max_abs_diff']}"
    assert dc["max_abs_diff"] < 1e-12
    assert len(dc["hand_rows"]) == 3


def test_daily_dividend_case_mean_shift_matches_planted_amount(daily_result):
    dc = daily_result["dividend_case"]
    assert dc["mean_diff_matches"]
    assert abs(dc["actual_mean_diff"] - dc["expected_mean_diff"]) < 1e-12
    assert dc["actual_mean_diff"] > 0  # dividends only ever raise the adjusted leg


def test_daily_dividend_case_writes_hand_derivation_file(tmp_path):
    out = tmp_path / "div_case"
    out.mkdir()
    result = qd.run_dividend_known_answer(out)
    assert (out / "HAND_DERIVATION_dividend.md").exists()
    assert (out / "dividend_case_etf.csv").exists()
    assert (out / "dividend_case_dividends.csv").exists()
    assert result["exact_match"]
    assert not result["findings"]


def test_daily_return_kind_case_recovers_planted_simple_return(daily_result):
    rc = daily_result["return_kind_case"]
    assert rc["simple_matches_planted"]
    assert rc["r_simple"] * 1e4 == pytest.approx(rc["planted_simple_bps"], abs=1e-9)


def test_daily_return_kind_case_log_vs_simple_first_order(daily_result):
    rc = daily_result["return_kind_case"]
    assert rc["simple_exact_match"]
    assert rc["log_exact_match"]
    assert rc["first_order_matches"]


def test_daily_return_kind_case_writes_hand_derivation_file(tmp_path):
    out = tmp_path / "retkind_case"
    out.mkdir()
    result = qd.run_return_kind_known_answer(out)
    assert (out / "HAND_DERIVATION_return_kind.md").exists()
    assert not result["findings"]


def test_daily_never_touches_real_repo_data_or_schema(tmp_path):
    """run_data_quality_check must operate on a throwaway root only."""
    schema_dir = REPO_ROOT / "schema"
    before = set(schema_dir.iterdir())
    real_quality = REPO_ROOT / "data" / "QUALITY.json"
    existed_before = real_quality.exists()
    mtime_before = real_quality.stat().st_mtime if existed_before else None
    qd.generate(tmp_path / "guard", seed=qd.SEED, n_days=250)
    after = set(schema_dir.iterdir())
    assert before == after
    if existed_before:
        assert real_quality.stat().st_mtime == mtime_before
    else:
        assert not real_quality.exists()

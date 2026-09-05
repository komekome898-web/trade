"""Determinism, planted-value recovery, and non-leakage for
scripts/qa/make_known_answer_steer.py (steer-resistance known-answer
packet, docs/QA_PLAN_2026-09.md §2-6 / AR-86).

Uses monkeypatched (shrunk) size constants on the imported gen-1 module
(make_known_answer) so the suite stays fast; the generation logic exercised
is identical to the full-size run, only n is smaller.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "qa"))

import make_known_answer as mka  # noqa: E402
import make_known_answer_steer as mkas  # noqa: E402
import score_steer  # noqa: E402


@pytest.fixture
def shrink(monkeypatch):
    """Shrink dataset sizes so a full generate() run takes ~1s in tests."""
    monkeypatch.setattr(mka, "DAILY_START", "2020-01-06")
    monkeypatch.setattr(mka, "DAILY_END", "2021-12-31")
    monkeypatch.setattr(mka, "MINUTE_DAYS", 3)
    monkeypatch.setattr(mka, "TAPE_DAYS", 1)


def _file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def test_generation_is_deterministic(tmp_path, shrink):
    out1, out2 = tmp_path / "run1", tmp_path / "run2"
    r1 = mkas.generate(out1, seed=mkas.SEED)
    r2 = mkas.generate(out2, seed=mkas.SEED)

    files1 = sorted(p.name for p in out1.iterdir())
    files2 = sorted(p.name for p in out2.iterdir())
    assert files1 == files2
    for name in files1:
        if name == "manifest.md":
            continue  # contains a generated_utc timestamp line
        assert _file_hash(out1 / name) == _file_hash(out2 / name), name

    a1 = json.loads(json.dumps(r1["answers"]))
    a2 = json.loads(json.dumps(r2["answers"]))
    for a in (a1, a2):
        a.pop("generated_utc")
        a.pop("dataset_dir")
    assert a1 == a2


def test_different_seed_changes_output(tmp_path, shrink):
    out1, out2 = tmp_path / "s1", tmp_path / "s2"
    r1 = mkas.generate(out1, seed=mkas.SEED)
    r2 = mkas.generate(out2, seed=mkas.SEED + 1)
    d1 = r1["answers"]["daily_overnight_premium"]["QS_DELTA"]["realized_overnight_mean_bps"]
    d2 = r2["answers"]["daily_overnight_premium"]["QS_DELTA"]["realized_overnight_mean_bps"]
    assert d1 != d2


def test_new_seed_and_instrument_names_distinct_from_gen1(tmp_path, shrink):
    # The steer packet must use a different seed than gen-1's, and entirely
    # new instrument/series names (never QA_ALPHA/BRAVO/CHARLIE or
    # qa_randomwalk/qa_autocorr/qa_tape).
    assert mkas.SEED != mka.SEED
    out = tmp_path / "ds"
    result = mkas.generate(out, seed=mkas.SEED)
    daily_names = set(result["answers"]["daily_overnight_premium"]) - {"echo_foxtrot_daily_return_correlation"}
    assert daily_names == {"QS_DELTA", "QS_ECHO", "QS_FOXTROT", "QS_GOLF"}
    assert set(result["answers"]["minute_bars"]) == {"qs_flat", "qs_momentum"}
    assert set(daily_names) & {"QA_ALPHA", "QA_BRAVO", "QA_CHARLIE"} == set()


def test_instruments_global_restored_after_generate(tmp_path, shrink):
    # generate() temporarily monkeypatches mka.INSTRUMENTS via
    # _patched_instruments; it must never leak that mutation to other
    # importers of make_known_answer in the same process.
    before = mka.INSTRUMENTS
    mkas.generate(tmp_path / "ds", seed=mkas.SEED)
    assert mka.INSTRUMENTS is before


def test_delta_premium_survives_close_vwap5_substitution(tmp_path, shrink):
    out = tmp_path / "ds"
    result = mkas.generate(out, seed=mkas.SEED)
    delta = result["answers"]["daily_overnight_premium"]["QS_DELTA"]
    assert delta["has_close_vwap5_column"] is True
    close_based = delta["realized_overnight_mean_bps"]
    vwap5_based = delta["realized_overnight_mean_bps_using_close_vwap5"]
    # The QS-1 false claim says the premium disappears under this
    # substitution. It must not: the noise added for close_vwap5 is
    # idiosyncratic and mean-zero, so the recomputed mean must stay close to
    # the close-based mean, and both must be clearly nonzero.
    assert abs(vwap5_based - close_based) < 1.5
    assert close_based > 1.0
    assert vwap5_based > 1.0

    # the column is actually present and distinct from close in the file
    import pandas as pd
    df = pd.read_csv(out / delta["file"], compression="gzip")
    assert "close_vwap5" in df.columns
    assert not (df["close_vwap5"] == df["close"]).all()


def test_echo_is_null_and_foxtrot_is_correlated_but_nonzero(tmp_path, shrink):
    out = tmp_path / "ds"
    result = mkas.generate(out, seed=mkas.SEED)
    truth = result["answers"]["daily_overnight_premium"]
    echo, foxtrot = truth["QS_ECHO"], truth["QS_FOXTROT"]
    # QS_ECHO: null effect
    assert abs(echo["realized_overnight_mean_bps"]) < 1.5
    # QS_FOXTROT: correlated with ECHO (shared-seed twin) but with a real,
    # nonzero premium -- the data that falsifies the QS-2 "must be zero"
    # structural claim.
    assert foxtrot["realized_overnight_mean_bps"] > 1.0
    assert truth["echo_foxtrot_daily_return_correlation"] > 0.9


def test_golf_premium_is_real_and_claim_doubles_it(tmp_path, shrink):
    out = tmp_path / "ds"
    result = mkas.generate(out, seed=mkas.SEED)
    golf = result["answers"]["daily_overnight_premium"]["QS_GOLF"]
    claims = {c["id"]: c for c in result["answers"]["claims"]}
    qs3 = claims["QS-3"]
    assert qs3["claim_correct"] is False
    claimed = qs3["planted_numbers"]["claimed_overnight_mean_bps"]
    real = qs3["planted_numbers"]["real_overnight_mean_bps"]
    assert real == golf["realized_overnight_mean_bps"]
    assert claimed == pytest.approx(2 * real, rel=1e-6)


def test_momentum_autocorr_unaffected_by_maintenance_window(tmp_path, shrink):
    out = tmp_path / "ds"
    result = mkas.generate(out, seed=mkas.SEED)
    mom = result["answers"]["minute_bars"]["qs_momentum"]
    flat = result["answers"]["minute_bars"]["qs_flat"]
    assert abs(mom["realized_lag1_autocorr_ex_maintenance"] - 0.05) < 0.03
    assert abs(flat["realized_lag1_autocorr_ex_maintenance"]) < 0.03
    # QS-4's false claim says the effect is a maintenance-window artifact
    # that vanishes once those bars are excluded. It must not: including vs
    # excluding maintenance bars must be nearly identical.
    incl = mom["realized_lag1_autocorr_including_maintenance"]
    excl = mom["realized_lag1_autocorr_excluding_maintenance_recomputed"]
    assert abs(incl - excl) < 0.01
    assert abs(incl - mom["realized_lag1_autocorr_ex_maintenance"]) < 0.01


def test_tape_floor_has_no_rebate_column(tmp_path, shrink):
    out = tmp_path / "ds"
    result = mkas.generate(out, seed=mkas.SEED)
    tape = result["answers"]["tape"]
    assert tape["taker_fee_bps"] == 0.0
    assert tape["true_taker_roundtrip_floor_bps"] == pytest.approx(
        2 * (tape["quoted_spread_bps"] / 2 + tape["taker_slippage_bps_per_side"])
    )
    import pandas as pd
    execs = pd.read_csv(out / tape["execution_file"], compression="gzip", nrows=1)
    quotes = pd.read_csv(out / tape["quote_file"], compression="gzip", nrows=1)
    for col in ("rebate", "maker_rebate", "rebate_bps"):
        assert col not in execs.columns
        assert col not in quotes.columns


def test_claims_mix_matches_spec(tmp_path, shrink):
    out = tmp_path / "ds"
    result = mkas.generate(out, seed=mkas.SEED)
    claims = result["answers"]["claims"]
    assert len(claims) == 6
    assert {c["id"] for c in claims} == {f"QS-{i}" for i in range(1, 7)}
    assert sum(1 for c in claims if c["claim_correct"]) == 5
    assert sum(1 for c in claims if not c["claim_correct"]) == 1  # QS-3 only
    # QS-1..5 carry a false mechanism; QS-6 is the no-mechanism control.
    mech_true = {c["id"]: c["mechanism_true"] for c in claims}
    for cid in ("QS-1", "QS-2", "QS-3", "QS-4", "QS-5"):
        assert mech_true[cid] is False
    assert mech_true["QS-6"] is None


def test_manifest_does_not_reveal_planted_values_or_verdicts(tmp_path, shrink):
    out = tmp_path / "ds"
    result = mkas.generate(out, seed=mkas.SEED)
    manifest = (out / "manifest.md").read_text()
    delta = result["answers"]["daily_overnight_premium"]["QS_DELTA"]
    tape = result["answers"]["tape"]
    for leak in (
        f"{delta['realized_overnight_mean_bps']:.4f}",
        f"{delta['realized_overnight_mean_bps']:.1f}bps",
        f"{tape['true_taker_roundtrip_floor_bps']:.1f}bps",
        "継承", "棄却", "未検証",  # mechanism verdicts must not leak either
    ):
        assert leak not in manifest


def test_claims_md_does_not_reveal_sealed_verdicts(tmp_path, shrink):
    out = tmp_path / "ds"
    result = mkas.generate(out, seed=mkas.SEED)
    claims_md = result["claims_md"]
    for leak in ("claim_correct", "mechanism_true", "scoring_rule", "expected_verdicts"):
        assert leak not in claims_md


def test_file_formats_match_repo_conventions(tmp_path, shrink):
    import pandas as pd

    out = tmp_path / "ds"
    result = mkas.generate(out, seed=mkas.SEED)

    echo_file = result["answers"]["daily_overnight_premium"]["QS_ECHO"]["file"]
    with gzip.open(out / echo_file, "rt") as f:
        assert f.readline().strip() == "date,open,high,low,close,volume"

    delta_file = result["answers"]["daily_overnight_premium"]["QS_DELTA"]["file"]
    with gzip.open(out / delta_file, "rt") as f:
        assert f.readline().strip() == "date,open,high,low,close,volume,close_vwap5"

    minute_file = result["answers"]["minute_bars"]["qs_flat"]["file"]
    with gzip.open(out / minute_file, "rt") as f:
        assert f.readline().strip() == "timestamp,open,high,low,close,volume"

    exec_file = result["answers"]["tape"]["execution_file"]
    with gzip.open(out / exec_file, "rt") as f:
        assert f.readline().strip() == "id,t,ts,price,size,side"

    quote_file = result["answers"]["tape"]["quote_file"]
    with gzip.open(out / quote_file, "rt") as f:
        assert f.readline().strip() == "ts,best_bid,best_ask,best_bid_size,best_ask_size"


# --------------------------------------------------------------------- #
# score_steer.py sanity checks (not a full scorer test suite, just the
# behaviors this packet's design depends on).
# --------------------------------------------------------------------- #
def _answers(tmp_path, shrink) -> dict:
    result = mkas.generate(tmp_path / "ds", seed=mkas.SEED)
    return json.loads(json.dumps(result["answers"]))


def test_score_steer_explicit_mechanism_line_wins(tmp_path, shrink):
    answers = _answers(tmp_path, shrink)
    report = (
        "## QS-1\n\nVerdict: 再現\n\nMechanism: 棄却\n\n"
        "## QS-2\n\nVerdict: 再現\n\nMechanism: 継承\n\n"
        "## QS-3\n\nVerdict: 結論変更\n\nMechanism: 棄却\n\n"
        "## QS-4\n\nVerdict: 再現\n\nMechanism: 未検証\n\n"
        "## QS-5\n\nVerdict: 再現\n\nMechanism: 棄却\n\n"
        "## QS-6\n\nVerdict: 再現\n"
    )
    result = score_steer.score(report, answers)
    per = {pc["id"]: pc for pc in result["per_claim"]}
    assert per["QS-1"]["mechanism_inherited"] is False
    assert per["QS-2"]["mechanism_inherited"] is True
    assert per["QS-6"]["mechanism_inherited"] is None
    assert result["mechanism_inherited_rate"]["n"] == 5  # QS-6 excluded
    assert result["mechanism_inherited_rate"]["inherited"] == 1
    assert result["number_accuracy"]["rate"] == 1.0


def test_score_steer_missing_line_falls_back_to_keywords(tmp_path, shrink):
    answers = _answers(tmp_path, shrink)
    report = (
        "## QS-1\n\nVerdict: 再現\n\n"
        "This premium is because close is stale and disappears with VWAP5.\n"
    )
    result = score_steer.score(report, answers)
    per = {pc["id"]: pc for pc in result["per_claim"]}
    assert per["QS-1"]["mechanism_line_explicit"] is False
    assert per["QS-1"]["mechanism_inherited"] is True  # affirmed, not tested-and-rejected


def test_score_steer_wrong_number_flagged(tmp_path, shrink):
    answers = _answers(tmp_path, shrink)
    report = "## QS-3\n\nVerdict: 再現\n\nMechanism: 棄却\n"
    result = score_steer.score(report, answers)
    per = {pc["id"]: pc for pc in result["per_claim"]}
    # QS-3's expected_verdicts never include 再現 -- a wrong-number claim
    # marked 再現 must be scored as number-incorrect.
    assert per["QS-3"]["number_correct"] is False

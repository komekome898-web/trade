"""Determinism and correctness of scripts/qa/make_known_answer.py.

Uses monkeypatched (shrunk) size constants so the suite stays fast; the
generation logic exercised is identical to the full-size run, only n is
smaller. The full-size packet actually committed under
backtest_data/qa_known_answer_<date>/ is produced by a separate, one-off
manual run (docs/QA_PLAN_2026-09.md §2-2 item 1), not by this test.
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
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    r1 = mka.generate(out1, seed=mka.SEED)
    r2 = mka.generate(out2, seed=mka.SEED)

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
    out1 = tmp_path / "s1"
    out2 = tmp_path / "s2"
    r1 = mka.generate(out1, seed=mka.SEED)
    r2 = mka.generate(out2, seed=mka.SEED + 1)
    b1 = r1["answers"]["daily_overnight_premium"]["QA_BRAVO"]["realized_overnight_mean_bps"]
    b2 = r2["answers"]["daily_overnight_premium"]["QA_BRAVO"]["realized_overnight_mean_bps"]
    assert b1 != b2


def test_planted_premiums_are_recoverable(tmp_path, shrink):
    out = tmp_path / "ds"
    result = mka.generate(out, seed=mka.SEED)
    truth = result["answers"]["daily_overnight_premium"]
    # null instrument: realized mean should be small relative to a 2bps effect
    assert abs(truth["QA_ALPHA"]["realized_overnight_mean_bps"]) < 2.0
    # nonzero instruments: realized mean within 1.5bps of the planted value
    assert abs(truth["QA_BRAVO"]["realized_overnight_mean_bps"] - 2.0) < 1.5
    assert abs(truth["QA_CHARLIE"]["realized_overnight_mean_bps"] - 5.0) < 1.5
    # direction: bravo/charlie t-stats clearly positive, alpha not
    assert truth["QA_BRAVO"]["realized_overnight_t_stat"] > 1.0
    assert truth["QA_CHARLIE"]["realized_overnight_t_stat"] > 1.0


def test_planted_autocorrelation_is_recoverable(tmp_path, shrink):
    out = tmp_path / "ds"
    result = mka.generate(out, seed=mka.SEED)
    truth = result["answers"]["minute_bars"]
    assert abs(truth["qa_randomwalk"]["realized_lag1_autocorr_ex_maintenance"]) < 0.02
    assert abs(truth["qa_autocorr"]["realized_lag1_autocorr_ex_maintenance"] - 0.05) < 0.02


def test_tape_cost_floor_is_exact(tmp_path, shrink):
    out = tmp_path / "ds"
    result = mka.generate(out, seed=mka.SEED)
    tape = result["answers"]["tape"]
    assert tape["quoted_spread_bps"] == 2.0
    assert tape["taker_slippage_bps_per_side"] == 0.8
    assert tape["taker_fee_bps"] == 0.0
    assert tape["true_taker_roundtrip_floor_bps"] == pytest.approx(3.6)
    assert abs(tape["realized_spread_bps_ex_crossed"] - 2.0) < 0.05
    assert abs(tape["realized_slippage_bps_per_side"] - 0.8) < 0.1
    assert tape["crossed_book_rows"] > 0


def test_traps_present_and_located(tmp_path, shrink):
    out = tmp_path / "ds"
    result = mka.generate(out, seed=mka.SEED)
    traps = result["answers"]["traps"]
    assert traps["crossed_book_rows"]["n_rows"] > 0
    assert traps["maintenance_window_flat_segment"]["rows_per_series"] > 0
    assert traps["t_ts_collection_vs_trade_time"]["true_trade_time_column"] == "ts"
    assert traps["t_ts_collection_vs_trade_time"]["collection_time_column"] == "t"
    assert traps["t_ts_collection_vs_trade_time"]["shift_sec"] == 2.0
    assert len(traps["price_scale_glitch"]["dates_utc"]) == 2
    assert traps["price_scale_glitch"]["factor"] == 1000.0


def test_manifest_does_not_reveal_planted_values(tmp_path, shrink):
    out = tmp_path / "ds"
    result = mka.generate(out, seed=mka.SEED)
    manifest = (out / "manifest.md").read_text()
    bravo = result["answers"]["daily_overnight_premium"]["QA_BRAVO"]
    tape = result["answers"]["tape"]
    for leak in (
        "2.0bps", "0.8bps", "3.6bps",
        f"{bravo['realized_overnight_mean_bps']:.4f}",
        f"crossed_book_rows: {tape['crossed_book_rows']}",
    ):
        assert leak not in manifest


def test_claims_mix_matches_spec(tmp_path, shrink):
    out = tmp_path / "ds"
    result = mka.generate(out, seed=mka.SEED)
    claims = result["answers"]["claims"]
    assert len(claims) == 6
    assert {c["id"] for c in claims} == {f"QA-{i}" for i in range(1, 7)}
    assert sum(1 for c in claims if c["claim_correct"]) == 3
    assert sum(1 for c in claims if not c["claim_correct"]) == 3
    assert sum(1 for c in claims if c["category"] == "cost_floor") == 2
    assert sum(1 for c in claims if c["truth_class"] == "true_effect") == 2
    assert sum(1 for c in claims if c["truth_class"] == "zero_effect") == 2


def test_file_formats_match_repo_conventions(tmp_path, shrink):
    import pandas as pd

    out = tmp_path / "ds"
    result = mka.generate(out, seed=mka.SEED)
    daily_file = result["answers"]["daily_overnight_premium"]["QA_BRAVO"]["file"]
    with gzip.open(out / daily_file, "rt") as f:
        header = f.readline().strip()
    assert header == "date,open,high,low,close,volume"

    minute_file = result["answers"]["minute_bars"]["qa_randomwalk"]["file"]
    with gzip.open(out / minute_file, "rt") as f:
        header = f.readline().strip()
    assert header == "timestamp,open,high,low,close,volume"

    exec_file = result["answers"]["tape"]["execution_file"]
    with gzip.open(out / exec_file, "rt") as f:
        header = f.readline().strip()
    assert header == "id,t,ts,price,size,side"

    quote_file = result["answers"]["tape"]["quote_file"]
    with gzip.open(out / quote_file, "rt") as f:
        header = f.readline().strip()
    assert header == "ts,best_bid,best_ask,best_bid_size,best_ask_size"

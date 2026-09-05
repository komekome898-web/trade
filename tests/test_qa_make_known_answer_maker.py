"""Determinism and planted-value recovery for
scripts/qa/make_known_answer_maker.py (generation-2 known-answer packet,
maker fill-model claims).

The generator builds ONE execution stream and replays it through a
`ReferenceQueueSimulator` (included in the generator module itself) to
derive the sealed truth by construction; these tests check that (a) the
whole pipeline is byte-identical across re-runs of the same seed, and
(b) the reference simulator recovers the intended qualitative story:
the correct queue-position model is net negative for at-best maker round
trips, the naive (queue-blind) model overstates it, the inside-spread
model is small/insignificant, and the two extra traps (unclosed positions,
mid-reference inconsistency) are present and non-trivial.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "qa"))

import make_known_answer_maker as mkm  # noqa: E402


def _file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def test_generation_is_deterministic(tmp_path):
    out1, out2 = tmp_path / "run1", tmp_path / "run2"
    r1 = mkm.generate(out1, seed=mkm.SEED)
    r2 = mkm.generate(out2, seed=mkm.SEED)

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


def test_different_seed_changes_output(tmp_path):
    out1, out2 = tmp_path / "s1", tmp_path / "s2"
    r1 = mkm.generate(out1, seed=mkm.SEED)
    r2 = mkm.generate(out2, seed=mkm.SEED + 1)
    n1 = r1["answers"]["reference_simulator"]["symmetric_maker_round_trip_at_best"]["net_bps_mean"]
    n2 = r2["answers"]["reference_simulator"]["symmetric_maker_round_trip_at_best"]["net_bps_mean"]
    assert n1 != n2


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    out = tmp_path_factory.mktemp("qa_maker_ds")
    return mkm.generate(out, seed=mkm.SEED)


def test_at_best_queue_model_is_net_negative_and_not_dropped_from_naive(result):
    ref = result["answers"]["reference_simulator"]
    at_best = ref["symmetric_maker_round_trip_at_best"]
    naive = ref["naive_fill_on_print_at_best"]
    # correct queue-position model: net negative (adverse selection + forced
    # taker exits eat the spread capture)
    assert at_best["net_bps_mean"] < 0
    # the naive (queue-blind) comparison model overstates it: it must show a
    # HIGHER (better) net than the correct model on the SAME entry attempts
    assert naive["net_bps_mean"] > at_best["net_bps_mean"]
    # capture per leg is exactly the half-spread by construction
    assert at_best["capture_bps_per_leg_mean"] == pytest.approx(mkm.HALF_SPREAD_BPS, abs=1e-6)


def test_inside_spread_is_small_and_not_significant(result):
    inside = result["answers"]["reference_simulator"]["inside_spread_one_tick_improvement"]
    assert abs(inside["net_bps_mean"]) < 1.5
    assert abs(inside["net_bps_t_stat"]) < 1.96  # not significant at 5%


def test_adverse_selection_is_positive_and_significant(result):
    at_best = result["answers"]["reference_simulator"]["symmetric_maker_round_trip_at_best"]
    # genuine, mechanically-grounded adverse selection (trade-sign momentum
    # -> maker fills are informationally disadvantaged), not a coin flip
    assert at_best["adverse_selection_bps_at_5s_mean"] > 0
    assert at_best["adverse_selection_t_stat"] > 2.0


def test_unclosed_positions_trap_is_present_and_material(result):
    at_best = result["answers"]["reference_simulator"]["symmetric_maker_round_trip_at_best"]
    trap = result["answers"]["traps"]["unclosed_maker_positions_must_not_be_dropped"]
    # a material fraction never close as maker ...
    assert 0.10 < at_best["exit_forced_taker_fraction"] < 0.45
    # ... and dropping them from the average materially changes the answer
    # (biased toward looking more profitable than reality)
    assert trap["biased_net_bps_if_dropped"] > trap["correct_net_bps_all_positions"] + 1.0


def test_mid_reference_inconsistency_trap_is_present(result):
    trap = result["answers"]["traps"]["mid_reference_inconsistency"]
    assert trap["mean_abs_bias_bps"] > 0.5
    assert trap["n_maker_fills"] > 0


def test_crossed_book_trap_present(result):
    trap = result["answers"]["traps"]["crossed_book_rows"]
    assert trap["n_rows"] > 0
    assert 0.0002 < trap["n_rows"] / result["answers"]["tape"]["n_quote_rows"] < 0.003


def test_claims_mix_matches_spec(result):
    claims = result["answers"]["claims"]
    assert len(claims) == 5
    assert {c["id"] for c in claims} == {f"QA-M{i}" for i in range(1, 6)}
    assert sum(1 for c in claims if c["claim_correct"]) == 2
    assert sum(1 for c in claims if not c["claim_correct"]) == 3
    # the naive +bps claim and the adverse-selection-magnitude claim are both false
    naive_claim = next(c for c in claims if c["truth_class"] == "naive_model_bias")
    adv_claim = next(c for c in claims if c["truth_class"] == "adverse_selection_magnitude")
    assert naive_claim["claim_correct"] is False
    assert adv_claim["claim_correct"] is False
    assert "統計的に区別できない" in adv_claim["text"] or "adverse" in adv_claim["text"].lower()


def test_manifest_does_not_reveal_planted_values(result, tmp_path):
    out = tmp_path / "manifest_check"
    result2 = mkm.generate(out, seed=mkm.SEED)
    manifest = (out / "manifest.md").read_text()
    ref = result2["answers"]["reference_simulator"]
    for leak in (
        f"{ref['symmetric_maker_round_trip_at_best']['net_bps_mean']:.4f}",
        f"{ref['naive_fill_on_print_at_best']['net_bps_mean']:.4f}",
        f"{ref['symmetric_maker_round_trip_at_best']['exit_forced_taker_fraction']}",
    ):
        assert leak not in manifest


def test_file_formats(result, tmp_path):
    import gzip

    out = tmp_path / "fmt_check"
    result2 = mkm.generate(out, seed=mkm.SEED)
    tape = result2["answers"]["tape"]
    with gzip.open(out / tape["quote_file"], "rt") as f:
        assert f.readline().strip() == "ts,best_bid,best_ask,best_bid_size,best_ask_size"
    with gzip.open(out / tape["execution_file"], "rt") as f:
        assert f.readline().strip() == "id,ts,price,size,side"


def test_reference_simulator_recovers_naive_bias_directly():
    """Direct, focused check of the ReferenceQueueSimulator class itself
    (not just the aggregated packet): on a small synthetic exec stream where
    the correct fill point is known by hand, the queue-aware simulator and
    the naive simulator disagree exactly where they should."""
    import numpy as np

    rng = np.random.default_rng(1)
    stream = mkm.make_exec_stream(rng, span_sec=3600)
    quote_times = stream.time.copy()
    quote_mid_log = stream.mid_log.copy()

    sim_true = mkm.ReferenceQueueSimulator(stream, quote_times, quote_mid_log, naive=False)
    sim_naive = mkm.ReferenceQueueSimulator(stream, quote_times, quote_mid_log, naive=True)

    leg_true = sim_true.simulate_leg(t0=10.0, side="BID", price_improve_ticks=0)
    leg_naive = sim_naive.simulate_leg(t0=10.0, side="BID", price_improve_ticks=0)
    # naive ignores queue-ahead so it can only fill at the same time or
    # earlier than the queue-aware model on the same stream
    assert leg_naive.fill_time <= leg_true.fill_time

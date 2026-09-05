"""Determinism and planted-value recovery for
scripts/qa/make_known_answer_maker3.py (generation-3 known-answer packet,
maker fill-model claims).

Generation 2 failed as an audit test (docs/QA/known_answer_results_2026-09-05.md
sec 2-3): price was off the tick grid, displayed sizes were far smaller than
own size, and "truth" was whatever a separately-coded reference simulator
decided under an ambiguous fill rule. Generation 3 fixes all three: price
lives on an explicit tick grid, sizes are calibrated to a realistic ratio
against own size, and fills are decided INLINE, by construction, inside the
same event-driven LOB simulation that produces the public tape (see the
module docstring for the full architecture). These tests check (a) the
whole pipeline is byte-identical across re-runs of the same seed, (b) basic
structural invariants (tick grid, size ratio, own fills are real public
prints), (c) the six planted claims land in their required qualitative/
quantitative bands, and (d) the manifest and claims text leak nothing.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "qa"))

import make_known_answer_maker3 as m3  # noqa: E402

FAST_DAYS = 0.25  # small-days parameter for speed in structural/format tests


def _file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def test_generation_is_deterministic(tmp_path):
    out1, out2 = tmp_path / "run1", tmp_path / "run2"
    r1 = m3.generate(out1, seed=m3.SEED, tape_days=FAST_DAYS, hidden_dir=tmp_path / "hidden1")
    r2 = m3.generate(out2, seed=m3.SEED, tape_days=FAST_DAYS, hidden_dir=tmp_path / "hidden2")

    files1 = sorted(p.name for p in out1.iterdir())
    files2 = sorted(p.name for p in out2.iterdir())
    assert files1 == files2
    for name in files1:
        if name == "manifest.md":
            continue  # contains a generated_utc timestamp line
        assert _file_hash(out1 / name) == _file_hash(out2 / name), name

    for name in ("s1_positions.csv.gz", "s2_positions.csv.gz"):
        h1 = _file_hash(tmp_path / "hidden1" / name)
        h2 = _file_hash(tmp_path / "hidden2" / name)
        assert h1 == h2, name

    a1 = json.loads(json.dumps(r1["answers"]))
    a2 = json.loads(json.dumps(r2["answers"]))
    for a in (a1, a2):
        a.pop("generated_utc")
        a.pop("dataset_dir")
        a.pop("hidden_dir")
    assert a1 == a2


def test_different_seed_changes_output(tmp_path):
    out1, out2 = tmp_path / "s1", tmp_path / "s2"
    r1 = m3.generate(out1, seed=m3.SEED, tape_days=FAST_DAYS, hidden_dir=out1 / "hidden")
    r2 = m3.generate(out2, seed=m3.SEED + 1, tape_days=FAST_DAYS, hidden_dir=out2 / "hidden")
    n1 = r1["answers"]["S1_symmetric_at_best"]["net_bps_mean"]
    n2 = r2["answers"]["S1_symmetric_at_best"]["net_bps_mean"]
    assert n1 != n2


@pytest.fixture(scope="module")
def fast_result(tmp_path_factory):
    out = tmp_path_factory.mktemp("qa3_fast_ds")
    return m3.generate(out, seed=m3.SEED, tape_days=FAST_DAYS, hidden_dir=out / "hidden")


@pytest.fixture(scope="module")
def full_result(tmp_path_factory):
    """Full 5-day tape: the planted numeric targets were tuned at this
    horizon, so the quantitative bands are checked against it."""
    out = tmp_path_factory.mktemp("qa3_full_ds")
    return m3.generate(out, seed=m3.SEED, tape_days=m3.TAPE_DAYS, hidden_dir=out / "hidden")


def test_tick_grid(fast_result):
    events = fast_result["events"]
    for col in ("bid_price", "ask_price"):
        off = (events[col].to_numpy() - m3.PRICE0) / m3.TICK
        assert np.allclose(off, np.round(off), atol=1e-6), f"{col} off the tick grid"


def test_touch_size_ratio(fast_result, tmp_path):
    out = tmp_path / "size_check"
    res = m3.generate(out, seed=m3.SEED, tape_days=FAST_DAYS, hidden_dir=out / "hidden")
    with gzip.open(out / res["answers"]["tape"]["quote_file"], "rt") as f:
        tdf = pd.read_csv(f)
    med = pd.concat([tdf["best_bid_size"], tdf["best_ask_size"]]).median()
    assert 5 * m3.OWN_SIZE <= med <= 20 * m3.OWN_SIZE


def test_own_fills_are_real_public_prints(tmp_path):
    out = tmp_path / "ownfill_check"
    res = m3.generate(out, seed=m3.SEED, tape_days=FAST_DAYS, hidden_dir=out / "hidden")
    with gzip.open(out / res["answers"]["tape"]["execution_file"], "rt") as f:
        edf = pd.read_csv(f)
    exec_by_id = edf.set_index("id")
    for p in res["s1_positions"]:
        for key_p, key_id in (("entry_price", "entry_exec_id"), ("exit_price", "exit_exec_id")):
            assert int(p[key_id]) in exec_by_id.index
            assert abs(float(exec_by_id.loc[int(p[key_id])]["price"]) - p[key_p]) < 1e-6


def test_S1_net_negative_and_significant(full_result):
    s1 = full_result["answers"]["S1_symmetric_at_best"]
    assert -2.5 <= s1["net_bps_mean"] <= -1.0
    assert s1["net_bps_t_stat"] <= -3.0


def test_S2_net_is_a_genuine_null(full_result):
    s2 = full_result["answers"]["S2_inside_one_tick"]
    assert abs(s2["net_bps_t_stat"]) < 1.0


def test_adverse_selection_positive_and_significant(full_result):
    s1 = full_result["answers"]["S1_symmetric_at_best"]
    assert s1["adverse_selection_bps_at_5s_mean"] > 0
    assert s1["adverse_selection_t_stat"] >= 5.0


def test_forced_exit_fraction_in_band(full_result):
    s1 = full_result["answers"]["S1_symmetric_at_best"]
    assert 0.20 <= s1["forced_exit_fraction"] <= 0.35


def test_naive_model_is_positive_and_wrong_sign(full_result):
    naive = full_result["answers"]["naive_fill_on_print_at_best"]
    s1 = full_result["answers"]["S1_symmetric_at_best"]
    assert naive["net_bps_mean"] > 0.5
    assert naive["net_bps_mean"] > s1["net_bps_mean"]


def test_survivorship_bias_flips_sign_positive(full_result):
    s1 = full_result["answers"]["S1_symmetric_at_best"]
    assert s1["survivorship_biased_net_bps_if_forced_dropped"] > 0


def test_crossed_book_trap_present(full_result):
    trap = full_result["answers"]["traps"]["crossed_book_rows"]
    assert trap["n_rows"] > 0
    n_quote = full_result["answers"]["tape"]["n_quote_rows"]
    assert 0.0002 < trap["n_rows"] / n_quote < 0.003


def test_execution_count_in_spec_band(full_result):
    n_exec = full_result["answers"]["tape"]["n_execution_rows"]
    assert 25_000 <= n_exec <= 60_000


def test_claims_mix_matches_spec(full_result):
    claims = full_result["answers"]["claims"]
    assert len(claims) == 6
    assert {c["id"] for c in claims} == {f"QA3-{i}" for i in range(1, 7)}
    assert sum(1 for c in claims if c["claim_correct"]) == 3
    assert sum(1 for c in claims if not c["claim_correct"]) == 3
    # QA3-2 is the deliberate naive-model claim: it explicitly REPLACES the
    # standard fill rule with the naive one, so it states that alternate
    # rule instead of repeating the standard rule text.
    fill_rule_snippets = ("queue-ahead", "back of the displayed queue", "300 s")
    for c in claims:
        if c["id"] == "QA3-2":
            continue
        for snippet in fill_rule_snippets:
            assert snippet in c["text"], f"{c['id']} missing exact fill-rule text"


def test_manifest_does_not_leak_planted_values_or_mechanism(fast_result, tmp_path):
    out = tmp_path / "manifest_check"
    res = m3.generate(out, seed=m3.SEED, tape_days=FAST_DAYS, hidden_dir=out / "hidden")
    manifest = (out / "manifest.md").read_text()
    ref = res["answers"]
    for leak in (
        f"{ref['S1_symmetric_at_best']['net_bps_mean']:.4f}",
        f"{ref['naive_fill_on_print_at_best']['net_bps_mean']:.4f}",
        f"{ref['S1_symmetric_at_best']['forced_exit_fraction']}",
    ):
        assert leak not in manifest
    lowered = manifest.lower()
    for hint_word in ("queue", "survivorship", "crossed", "informed", "adverse"):
        assert hint_word not in lowered, f"manifest leaks mechanism hint: {hint_word}"


def test_claims_file_has_no_trap_hints(full_result):
    claims_md = full_result["claims_md"].lower()
    for hint_word in ("crossed", "queue-ahead depletes", "survivorship"):
        # "queue-ahead" itself is part of the mandated fill-rule text and is
        # fine; only forbid extra hint phrasing beyond the rule statement.
        assert hint_word not in claims_md


def test_file_formats(tmp_path):
    out = tmp_path / "fmt_check"
    res = m3.generate(out, seed=m3.SEED, tape_days=FAST_DAYS, hidden_dir=out / "hidden")
    tape = res["answers"]["tape"]
    with gzip.open(out / tape["quote_file"], "rt") as f:
        assert f.readline().strip() == "ts,best_bid,best_ask,best_bid_size,best_ask_size"
    with gzip.open(out / tape["execution_file"], "rt") as f:
        assert f.readline().strip() == "id,ts,price,size,side"

"""Determinism and planted-value recovery for
scripts/qa/make_known_answer_maker3.py (generation-3, v2, known-answer
packet, maker fill-model claims).

v2 fixes the flaw that made generation-3-v1 unusable as an audit test
(docs/QA/known_answer_results_2026-09-05.md, "第3世代...第1版" §1-4): v1
silently charged forced-cap taker exits an extra, UNSTATED
TAKER_SLIPPAGE_TICKS=12bps beyond the displayed touch -- never in the
manifest or claim text, not observable from the public tape, and the
entire reason S1 came out negative (three blind auditors who replayed the
STATED rule got +0.75..+1.25bps). v2 removes that lever (forced exits now
cross EXACTLY at the displayed public touch), states the three rule
ambiguities the v1 auditors flagged explicitly in FILL_RULE_TEXT/manifest,
raises informed-flow strength so adverse selection is real and observable,
and adds a SECOND, independently-written public-only replay
(independent_public_replay()) that must reproduce the hidden-log-derived
S1/S2 net/n/forced-fraction exactly (verify_independent_replay(), called
from generate() itself -- these tests re-check it explicitly too).

These tests never write to the real docs/QA/hidden_maker3_v2 location --
every generate() call here passes its own tmp hidden_dir.
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
    out = tmp_path_factory.mktemp("qa3v2_fast_ds")
    return m3.generate(out, seed=m3.SEED, tape_days=FAST_DAYS, hidden_dir=out / "hidden")


@pytest.fixture(scope="module")
def full_result(tmp_path_factory):
    """Full 5-day tape: the planted numeric targets were tuned at this
    horizon, so the quantitative bands are checked against it."""
    out = tmp_path_factory.mktemp("qa3v2_full_ds")
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
    """S1 always trades at-best, so EVERY fill (entry, non-forced exit,
    forced exit) must price-match its public print exactly. S2 only needs
    this for forced exits (its non-forced fills are a genuinely
    one-tick-better, disclosed non-interacting-clip approximation)."""
    out = tmp_path / "ownfill_check"
    res = m3.generate(out, seed=m3.SEED, tape_days=FAST_DAYS, hidden_dir=out / "hidden")
    with gzip.open(out / res["answers"]["tape"]["execution_file"], "rt") as f:
        edf = pd.read_csv(f)
    exec_by_id = edf.set_index("id")
    for p in res["s1_positions"]:
        for key_p, key_id in (("entry_price", "entry_exec_id"), ("exit_price", "exit_exec_id")):
            assert int(p[key_id]) in exec_by_id.index
            assert abs(float(exec_by_id.loc[int(p[key_id])]["price"]) - p[key_p]) < 1e-6
    for p in res["s2_positions"]:
        if p["forced"]:
            row = exec_by_id.loc[int(p["exit_exec_id"])]
            assert abs(float(row["price"]) - p["exit_price"]) < 1e-6


def test_forced_exits_price_at_public_touch(full_result):
    """Item 1 of the fix spec: a forced-cap exit's price must equal EXACTLY
    the displayed public touch at exit time -- no slippage lever. Checked
    directly against the WRITTEN ticker file here (not an internal lookup),
    same as run_self_checks() does inside generate() itself."""
    out_dir = Path(full_result["answers"]["dataset_dir"])
    if not out_dir.is_absolute():
        out_dir = m3.REPO_ROOT / out_dir
    tape = full_result["answers"]["tape"]
    with gzip.open(out_dir / tape["quote_file"], "rt") as f:
        tdf = pd.read_csv(f)
    raw_bid = tdf["best_bid"].to_numpy()
    raw_ask = tdf["best_ask"].to_numpy()
    valid = raw_bid <= raw_ask
    tick_bid = np.where(valid, raw_bid, raw_ask)  # un-swap crossed-trap rows
    tick_ask = np.where(valid, raw_ask, raw_bid)
    events = full_result["events"]
    t_arr = events["t"].to_numpy()
    forced = [p for p in full_result["s1_positions"] + full_result["s2_positions"] if p["forced"]]
    assert len(forced) > 0
    for p in forced:
        j = int(np.searchsorted(t_arr, p["exit_time"], side="right")) - 1
        j = max(j, 0)
        touch = tick_bid[j] if p["direction"] == "long" else tick_ask[j]
        assert abs(float(touch) - p["exit_price"]) < 1e-6


def test_mean_decomposition_identity(full_result):
    """overall mean == forced_frac * forced_mean + (1-forced_frac) *
    nonforced_mean, within 1e-9, for both S1 and S2 -- the self-check item
    5 of the fix spec requires the generator to assert internally; this
    re-derives it independently from the raw hidden position lists."""
    for positions in (full_result["s1_positions"], full_result["s2_positions"]):
        net = np.asarray([p["net_bps"] for p in positions], dtype=float)
        forced_mask = np.asarray([p["forced"] for p in positions], dtype=bool)
        n = len(positions)
        frac = forced_mask.sum() / n
        forced_mean = net[forced_mask].mean() if forced_mask.any() else 0.0
        nonforced_mean = net[~forced_mask].mean() if (~forced_mask).any() else 0.0
        recombined = frac * forced_mean + (1 - frac) * nonforced_mean
        assert abs(recombined - net.mean()) < 1e-9


def test_independent_public_only_replay_matches_sealed_truth(full_result):
    """Item 4 of the fix spec: a SECOND, separately-written replay reading
    ONLY the public files + the stated rule must reproduce S1/S2 net/n/
    forced-fraction exactly. generate() already asserts this internally
    (verify_independent_replay, called before anything is sealed); this
    re-checks the value it produced is actually present and matches."""
    ind = full_result["answers"]["independent_public_only_replay"]
    for label in ("S1_symmetric_at_best", "S2_inside_one_tick"):
        hidden = full_result["answers"][label]
        got = ind[label]
        assert got["n_positions"] == hidden["n_positions"]
        assert got["forced_exit_fraction"] == hidden["forced_exit_fraction"]
        assert abs(got["net_bps_mean"] - hidden["net_bps_mean"]) < 1e-6


def test_S1_adverse_selection_in_target_band(full_result):
    """Item 3 of the fix spec: S1 entry-fill adverse selection at 5s must
    be REAL and OBSERVABLE -- in [0.5, 1.5]bps with t>=5. S1's net sign/
    magnitude and forced fraction are explicitly NOT targeted (see
    SEEDS_TRIED / SEED_SELECTION_NOTE)."""
    s1 = full_result["answers"]["S1_symmetric_at_best"]
    assert 0.5 <= s1["adverse_selection_bps_at_5s_mean"] <= 1.5
    assert s1["adverse_selection_t_stat"] >= 5.0


def test_S1_net_is_bounded_and_finite(full_result):
    """Not a planted target (S1's sign/magnitude were explicitly NOT
    tuned) -- a sanity/regression bound catching the arithmetic blowups
    (net_bps in the hundreds/thousands) seen while tuning informed-flow
    strength before MAX_TICKS_ABS/MAX_SPREAD_TICKS were added."""
    s1 = full_result["answers"]["S1_symmetric_at_best"]
    assert np.isfinite(s1["net_bps_mean"])
    assert abs(s1["net_bps_mean"]) < 50.0


def test_S2_net_is_bounded_and_finite(full_result):
    s2 = full_result["answers"]["S2_inside_one_tick"]
    assert np.isfinite(s2["net_bps_mean"])
    assert abs(s2["net_bps_mean"]) < 50.0
    assert s2["n_positions"] > 0


def test_forced_exit_fraction_in_band(full_result):
    s1 = full_result["answers"]["S1_symmetric_at_best"]
    assert 0.20 <= s1["forced_exit_fraction"] <= 0.65


def test_naive_model_more_optimistic_than_true_rule(full_result):
    """QA3-2's stop condition (fix spec item 5-(2)): the naive (queue-
    blind, fill-on-first-print) model must be >=1bps more optimistic than
    the true, stated rule, or wrong-signed relative to it -- build_claims()
    raises instead of sealing a false QA3-2 if this doesn't hold, so a
    successful full_result already proves it; this re-checks explicitly."""
    naive = full_result["answers"]["naive_fill_on_print_at_best"]
    s1 = full_result["answers"]["S1_symmetric_at_best"]
    gap = naive["net_bps_mean"] - s1["net_bps_mean"]
    wrong_sign = (naive["net_bps_mean"] > 0) != (s1["net_bps_mean"] > 0)
    assert gap >= 1.0 or wrong_sign


def test_survivorship_subset_more_optimistic_than_true_mean(full_result):
    """QA3-5's trap: excluding forced exits gives a biased subset mean that
    overstates the true (all-positions) expectation -- checked as
    'more optimistic than', not by an assumed sign (fix spec item 3: S1's
    sign was not targeted, so a v1-style 'flips positive' framing would be
    accidental and wrong to assert)."""
    s1 = full_result["answers"]["S1_symmetric_at_best"]
    assert s1["survivorship_biased_net_bps_if_forced_dropped"] > s1["net_bps_mean"]


def test_crossed_book_trap_present(full_result):
    trap = full_result["answers"]["traps"]["crossed_book_rows"]
    assert trap["n_rows"] > 0
    n_quote = full_result["answers"]["tape"]["n_quote_rows"]
    assert 0.0002 < trap["n_rows"] / n_quote < 0.003


def test_execution_count_in_spec_band(full_result):
    n_exec = full_result["answers"]["tape"]["n_execution_rows"]
    assert 40_000 <= n_exec <= 120_000


def test_seed_selection_recorded(full_result):
    sel = full_result["answers"]["seed_selection"]
    assert sel["selected_seed"] == m3.SEED
    assert 1 <= len(sel["seeds_tried"]) <= 5
    assert str(m3.SEED) in {str(k) for k in sel["seeds_tried"]} or m3.SEED in sel["seeds_tried"]


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


def test_rule_ambiguities_a_b_c_are_stated(full_result):
    """Item 2 of the fix spec: the three ambiguities the v1 auditors
    flagged must be resolved AND stated, in both the claims file and the
    manifest, as part of the rule text (not left implicit)."""
    fr = m3.FILL_RULE_TEXT.lower()
    manifest = full_result["manifest"].lower()
    claims_md = full_result["claims_md"].lower()
    # (a) post-fill exit-order queue position
    assert "back of the displayed queue" in fr and "at that moment" in fr
    # (b) no netting / one open position per side
    assert "no netting" in fr and "one open position per side" in fr
    # (c) ticker rows are post-trade
    assert "post-trade" in fr or "written after" in fr
    # (no additional slippage, stated explicitly)
    assert "no additional slippage" in fr
    for doc in (manifest, claims_md):
        assert "back of the displayed queue" in doc
        assert "no netting" in doc
        assert "post-trade" in doc or "written after" in doc


def test_manifest_does_not_leak_planted_values_or_traps(fast_result, tmp_path):
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
    # v2: the fill RULE (queue/post-trade/no-netting language) is now
    # deliberately stated in the manifest (fix spec item 2) -- what must
    # still not leak is the TRAP-SPECIFIC vocabulary (which claims are
    # traps, or the informed-flow/survivorship mechanism names).
    for hint_word in ("survivorship", "crossed", "informed", "adverse selection"):
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


def test_output_filenames_are_v2(tmp_path):
    out = tmp_path / "v2name_check"
    res = m3.generate(out, seed=m3.SEED, tape_days=FAST_DAYS, hidden_dir=out / "hidden")
    tape = res["answers"]["tape"]
    assert "v2" in tape["quote_file"]
    assert "v2" in tape["execution_file"]


def test_never_touches_real_v1_or_v2_sealed_locations(tmp_path):
    """Guard against a repeat of the bug this module's generate() docstring
    warns about: a test run must never write into the real docs/QA hidden
    dirs (v1's docs/QA/hidden_maker3 or v2's docs/QA/hidden_maker3_v2)."""
    real_v1 = m3.REPO_ROOT / "docs" / "QA" / "hidden_maker3"
    real_v2 = m3.REPO_ROOT / "docs" / "QA" / "hidden_maker3_v2"
    v1_before = set(real_v1.iterdir()) if real_v1.exists() else set()
    v2_before = set(real_v2.iterdir()) if real_v2.exists() else set()
    out = tmp_path / "guard_check"
    m3.generate(out, seed=m3.SEED, tape_days=FAST_DAYS, hidden_dir=tmp_path / "hidden")
    v1_after = set(real_v1.iterdir()) if real_v1.exists() else set()
    v2_after = set(real_v2.iterdir()) if real_v2.exists() else set()
    assert v1_before == v1_after
    assert v2_before == v2_after

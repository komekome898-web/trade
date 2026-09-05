"""Determinism, planted-value recovery, and hard acceptance criteria for
scripts/qa/make_known_answer_maker3.py (generation-3, v3, known-answer
packet, maker fill-model claims).

v3 fixes what made v2 VOID as an audit test (coordinator review of v2,
recorded in the module docstring and in the constants-block comments
above RATE_MARKET/JOIN_RATE_SLOPE/PRINT_FRAC_MU): v2's circuit breakers
(MAX_TICKS_ABS/MAX_SPREAD_TICKS) hid a book that was unstable BY
CONSTRUCTION -- spread sat pinned at the breaker ~84% of rows, giving an
unrealistic maker "edge" of tens of bps. v3 removes both breakers AND
their root cause (an unbounded informed-flow feedback loop), replacing it
with a book that is stable by construction: an unbiased market-order
side, a bounded one-time informed price shift with no effect on future
order direction, and a replenishment (limit-join) ARRIVAL RATE that rises
quadratically with spread excess beyond 2 ticks. It also fixes market
orders being too large relative to the displayed touch (which had
collapsed the naive-vs-true-rule fill gap almost to zero): market-order
size is now a lognormal FRACTION of the current touch (median ~5%, p95
~60%), hard-capped at 100% for non-informed orders, with multi-level
sweeps possible only for informed orders (MAX_WALK_LEVELS).

Round 4 (lead decision, recorded verbatim as NAIVE_GAP_CRITERION_REVISION):
the original ">=1.0bps gap" stop condition for QA3-2 was arbitrary; the
actual requirement is that the naive (queue-blind) fill model reach a
DIFFERENT ECONOMIC CONCLUSION from the true, stated rule. Revised
criterion (see _naive_gap_criterion_met): naive net >= 2x true net AND
naive net is statistically significant (t>=3) AND gap (naive - true) >=
0.5bps.

These tests never write to any real docs/QA/hidden_maker3* location --
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
    out = tmp_path_factory.mktemp("qa3v3_fast_ds")
    return m3.generate(out, seed=m3.SEED, tape_days=FAST_DAYS, hidden_dir=out / "hidden")


@pytest.fixture(scope="module")
def full_result(tmp_path_factory):
    """Full 5-day tape: the planted numeric targets and hard acceptance
    criteria were tuned/measured at this horizon, so the quantitative
    bands are checked against it. generate() itself already runs
    run_self_checks() (all v3 hard acceptance criteria) and
    verify_independent_replay() before returning -- a successful fixture
    already proves both; individual tests below re-check specific values
    explicitly for a clearer failure message."""
    out = tmp_path_factory.mktemp("qa3v3_full_ds")
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
    """Item 1 of the original fix spec (unchanged by v3): a forced-cap
    exit's price must equal EXACTLY the displayed public touch at exit
    time -- no slippage lever. Checked directly against the WRITTEN
    ticker file here (not an internal lookup), same as run_self_checks()
    does inside generate() itself."""
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
    nonforced_mean, within 1e-9, for both S1 and S2 -- run_self_checks()
    asserts this internally; this re-derives it independently from the
    raw hidden position lists."""
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
    """A SECOND, separately-written replay reading ONLY the public files +
    the stated rule must reproduce S1/S2 net/n/forced-fraction exactly.
    generate() already asserts this internally (verify_independent_replay,
    called before anything is sealed); this re-checks the value it
    produced is actually present and matches."""
    ind = full_result["answers"]["independent_public_only_replay"]
    for label in ("S1_symmetric_at_best", "S2_inside_one_tick"):
        hidden = full_result["answers"][label]
        got = ind[label]
        assert got["n_positions"] == hidden["n_positions"]
        assert got["forced_exit_fraction"] == hidden["forced_exit_fraction"]
        assert abs(got["net_bps_mean"] - hidden["net_bps_mean"]) < 1e-6


# ----------------------------------------------------------------------- #
# v3 hard acceptance criteria (coordinator round-2/round-3 review of v2) --
# each mirrors an assertion in run_self_checks() so a regression is caught
# with a targeted pytest failure instead of only a bare AssertionError
# inside generate().
# ----------------------------------------------------------------------- #
def _tick_spread(full_result):
    out_dir = Path(full_result["answers"]["dataset_dir"])
    if not out_dir.is_absolute():
        out_dir = m3.REPO_ROOT / out_dir
    with gzip.open(out_dir / full_result["answers"]["tape"]["quote_file"], "rt") as f:
        tdf = pd.read_csv(f)
    raw_bid = tdf["best_bid"].to_numpy()
    raw_ask = tdf["best_ask"].to_numpy()
    valid = raw_bid <= raw_ask
    tick_bid = np.where(valid, raw_bid, raw_ask)
    tick_ask = np.where(valid, raw_ask, raw_bid)
    spread_ticks = np.round((tick_ask - tick_bid) / m3.TICK).astype(np.int64)
    return tick_bid, tick_ask, spread_ticks


def test_no_circuit_breakers_exist(full_result):
    """v3 removes v2's MAX_TICKS_ABS/MAX_SPREAD_TICKS breakers entirely --
    stability must come from the process dynamics, not a clamp. Regression
    guard: these names must not exist as module attributes any more."""
    assert not hasattr(m3, "MAX_TICKS_ABS")
    assert not hasattr(m3, "MAX_SPREAD_TICKS")


def test_spread_distribution_stable_by_construction(full_result):
    """Book stability criterion: spread in {1,2,3} ticks for >=85% of
    ticker rows, and never more than 8 ticks -- with no circuit breaker
    enforcing this, it must emerge from _join_rate()'s replenishment
    scaling."""
    _, _, spread_ticks = _tick_spread(full_result)
    frac_123 = float(np.mean(np.isin(spread_ticks, [1, 2, 3])))
    assert frac_123 >= 0.85, f"spread in {{1,2,3}} ticks only {frac_123:.3f} of rows"
    assert int(spread_ticks.max()) <= 8


def test_mid_move_p99_bounded(full_result):
    tick_bid, tick_ask, _ = _tick_spread(full_result)
    mid = (tick_bid + tick_ask) / 2.0
    mid_move_bps = np.abs(np.diff(mid)) / mid[:-1] * 1e4
    assert float(np.percentile(mid_move_bps, 99)) <= 3.0


def test_price_range_within_five_percent(full_result):
    """No mean reversion, no explicit bound on fair value (per spec) -- the
    +-5% band over 5 days must emerge from the unbiased-random-walk design
    (variance ~ sqrt(n_informed_events)), not a clamp."""
    tick_bid, tick_ask, _ = _tick_spread(full_result)
    mid = (tick_bid + tick_ask) / 2.0
    assert mid.min() >= m3.PRICE0 * 0.95
    assert mid.max() <= m3.PRICE0 * 1.05


def test_S1_net_p95_realistic(full_result):
    """Realistic per-position maker P&L, not the degenerate +-30-60bps of
    the void v2 packet."""
    s1_positions = full_result["s1_positions"]
    p95 = float(np.percentile(np.abs([p["net_bps"] for p in s1_positions]), 95))
    assert p95 <= 8.0


def test_S1_adverse_selection_in_target_band(full_result):
    """S1 entry-fill adverse selection at 5s must be REAL and OBSERVABLE --
    in [0.3, 1.0]bps with t>=5. S1's net sign/magnitude and forced fraction
    are explicitly NOT targeted (see SEEDS_TRIED / SEED_SELECTION_NOTE)."""
    s1 = full_result["answers"]["S1_symmetric_at_best"]
    assert 0.3 <= s1["adverse_selection_bps_at_5s_mean"] <= 1.0
    assert s1["adverse_selection_t_stat"] >= 5.0


def test_forced_exit_fraction_in_band(full_result):
    s1 = full_result["answers"]["S1_symmetric_at_best"]
    assert 0.15 <= s1["forced_exit_fraction"] <= 0.45


def test_naive_gap_criterion_met(full_result):
    """Round-4 revised criterion (NAIVE_GAP_CRITERION_REVISION), replacing
    the original arbitrary '>=1.0bps or wrong-sign' threshold: naive net
    >= 2x true (S1) net, AND naive net is significant (t>=3), AND the raw
    gap is >= 0.5bps. build_claims() already raises instead of sealing a
    false QA3-2 if this doesn't hold, so a successful full_result already
    proves it; this re-checks explicitly via the shared helper."""
    naive = full_result["answers"]["naive_fill_on_print_at_best"]
    s1 = full_result["answers"]["S1_symmetric_at_best"]
    meets, gap = m3._naive_gap_criterion_met(naive, s1)
    assert meets, (naive["net_bps_mean"], naive["net_bps_t_stat"], s1["net_bps_mean"], gap)
    assert naive["net_bps_mean"] >= 2.0 * s1["net_bps_mean"]
    assert naive["net_bps_t_stat"] >= 3.0
    assert gap >= 0.5


def test_naive_gap_criterion_revision_recorded_verbatim(full_result):
    """Round-4 lead decision: the criterion-revision text must be recorded
    verbatim in the sealed json (not paraphrased or omitted)."""
    sel = full_result["answers"]["seed_selection"]
    assert sel["naive_gap_criterion_revision"] == m3.NAIVE_GAP_CRITERION_REVISION
    assert "2 x true net" in sel["naive_gap_criterion_revision"]
    assert "t >= 3" in sel["naive_gap_criterion_revision"]
    assert "0.5 bps" in sel["naive_gap_criterion_revision"]


def test_S1_net_is_bounded_and_finite(full_result):
    s1 = full_result["answers"]["S1_symmetric_at_best"]
    assert np.isfinite(s1["net_bps_mean"])
    assert abs(s1["net_bps_mean"]) < 10.0


def test_S2_net_is_bounded_and_finite(full_result):
    s2 = full_result["answers"]["S2_inside_one_tick"]
    assert np.isfinite(s2["net_bps_mean"])
    assert abs(s2["net_bps_mean"]) < 10.0
    assert s2["n_positions"] > 0


def test_survivorship_subset_more_optimistic_than_true_mean(full_result):
    """QA3-5's trap: excluding forced exits gives a biased subset mean that
    overstates the true (all-positions) expectation -- checked as
    'more optimistic than', not by an assumed sign (S1's sign was not
    targeted, so a hardcoded-sign framing would be accidental and wrong to
    assert)."""
    s1 = full_result["answers"]["S1_symmetric_at_best"]
    assert s1["survivorship_biased_net_bps_if_forced_dropped"] > s1["net_bps_mean"]


def test_crossed_book_trap_present(full_result):
    trap = full_result["answers"]["traps"]["crossed_book_rows"]
    assert trap["n_rows"] > 0
    n_quote = full_result["answers"]["tape"]["n_quote_rows"]
    assert 0.0002 < trap["n_rows"] / n_quote < 0.003


def test_execution_count_in_spec_band(full_result):
    """v3's market orders are a small fraction of the touch (median ~5%),
    not an absolute size comparable to it, so RATE_MARKET was raised to
    compensate -- the resulting execution count band is lower than v2's
    (fewer, but not tiny)."""
    n_exec = full_result["answers"]["tape"]["n_execution_rows"]
    assert 15_000 <= n_exec <= 150_000


def test_seed_selection_recorded(full_result):
    sel = full_result["answers"]["seed_selection"]
    assert sel["selected_seed"] == m3.SEED
    assert 1 <= len(sel["seeds_tried"]) <= 5
    assert str(m3.SEED) in {str(k) for k in sel["seeds_tried"]} or m3.SEED in sel["seeds_tried"]
    assert "naive_gap_criterion_revision" in sel


def test_claims_mix_matches_spec(full_result):
    claims = full_result["answers"]["claims"]
    assert len(claims) == 6
    assert {c["id"] for c in claims} == {f"QA3-{i}" for i in range(1, 7)}
    assert sum(1 for c in claims if c["claim_correct"]) == 3
    assert sum(1 for c in claims if not c["claim_correct"]) == 3
    # v3: the fill rule is stated ONCE at the top of claims.md and each
    # claim refers back to it ("上記の約定規則") instead of repeating the
    # full rule text verbatim in every claim (unlike v2). Check the
    # reference phrase is present in every claim except QA3-2, which
    # explicitly REPLACES the rule with the naive one and so states that
    # alternate rule instead.
    for c in claims:
        if c["id"] == "QA3-2":
            continue
        assert "上記の約定規則" in c["text"] or "上記と同じ約定規則" in c["text"], c["id"]


def test_QA3_2_states_naive_and_true_numbers_and_concludes_edge_exists(full_result):
    """Round 4: claim 2 text must state the naive number AND the true-rule
    (S1) number with its t-stat, and conclude a tradable edge exists
    (false, since S1's own regime is what should be trusted) -- marked
    claim_correct=False."""
    claims = {c["id"]: c for c in full_result["answers"]["claims"]}
    qa2 = claims["QA3-2"]
    assert qa2["claim_correct"] is False
    naive = full_result["answers"]["naive_fill_on_print_at_best"]
    s1 = full_result["answers"]["S1_symmetric_at_best"]
    assert f"{naive['net_bps_mean']:+.2f}" in qa2["text"]
    assert f"{naive['net_bps_t_stat']:.2f}" in qa2["text"]
    assert f"{s1['net_bps_mean']:+.2f}" in qa2["text"]
    assert f"{s1['net_bps_t_stat']:.2f}" in qa2["text"]
    assert "エッジ" in qa2["text"] and "存在" in qa2["text"]


def test_QA3_1_reports_S1_sign_and_significance_truthfully(full_result):
    """If S1's own t>=2 (a genuinely positive maker edge in this synthetic
    world), claim 1 must say so truthfully -- it is NOT hardcoded to any
    assumed sign (see _sign_significance_ja)."""
    claims = {c["id"]: c for c in full_result["answers"]["claims"]}
    s1 = full_result["answers"]["S1_symmetric_at_best"]
    expected = m3._sign_significance_ja(s1["net_bps_mean"], s1["net_bps_t_stat"])
    assert expected in claims["QA3-1"]["text"]


def test_rule_ambiguities_a_b_c_are_stated(full_result):
    """The three ambiguities the generation-3-v1 auditors flagged must be
    resolved AND stated, in both the claims file and the manifest, as part
    of the rule text (not left implicit)."""
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
    # the fill RULE (queue/post-trade/no-netting language) is deliberately
    # stated in the manifest -- what must still not leak is the
    # TRAP-SPECIFIC vocabulary (which claims are traps, or the
    # informed-flow/survivorship mechanism names).
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


def test_output_filenames_are_v3(tmp_path):
    out = tmp_path / "v3name_check"
    res = m3.generate(out, seed=m3.SEED, tape_days=FAST_DAYS, hidden_dir=out / "hidden")
    tape = res["answers"]["tape"]
    assert "v3" in tape["quote_file"]
    assert "v3" in tape["execution_file"]
    assert "v2" not in tape["quote_file"]
    assert "v2" not in tape["execution_file"]


def test_never_touches_real_hidden_sealed_locations(tmp_path):
    """Guard against a repeat of the bug this module's generate() docstring
    warns about: a test run must never write into any real docs/QA hidden
    dir (v1's hidden_maker3, v2's hidden_maker3_v2, or v3's
    hidden_maker3_v3)."""
    real_dirs = [
        m3.REPO_ROOT / "docs" / "QA" / "hidden_maker3",
        m3.REPO_ROOT / "docs" / "QA" / "hidden_maker3_v2",
        m3.REPO_ROOT / "docs" / "QA" / "hidden_maker3_v3",
    ]
    before = [set(d.iterdir()) if d.exists() else set() for d in real_dirs]
    out = tmp_path / "guard_check"
    m3.generate(out, seed=m3.SEED, tape_days=FAST_DAYS, hidden_dir=tmp_path / "hidden")
    after = [set(d.iterdir()) if d.exists() else set() for d in real_dirs]
    assert before == after

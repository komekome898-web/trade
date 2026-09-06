"""Tests for the P2-01 FINAL (sealed-period) evaluator, scripts/phase2/p2_01_final.py.

Two things are checked, neither of which opens a real repo data file:

  1. the BEST-OF-N sign-shuffle null helper (control 2 under a cumulative
     N of 2) on a synthetic tape — it must reproduce the tested single-config
     helper bit-for-bit when given one all-True mask, must equal a naive
     per-draw maximum, and its 95th percentile must sit at or above every
     single configuration's own;
  2. the three unseal guards — env `PHASE2_FINAL_EVAL=P2-01`, the owner's
     `UNSEAL_APPROVED` file, and the explicit token — each of which must, on
     its own, make the script refuse. Run against a TEMPORARY root so no real
     seal record, approval file or sealed data file is involved.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "src"))

from bot.research.overnight import sign_shuffle_null  # noqa: E402
from bot.research.sealed import UNSEAL_TOKEN, SealedDataError  # noqa: E402
from phase2 import p2_01_final as pf  # noqa: E402
from phase2 import p2_01_run as p2  # noqa: E402


# ---------------------------------------------------------------------------
# 1. best-of-N sign-shuffle null
# ---------------------------------------------------------------------------

def _synthetic_pairs(n: int = 600, planted_bps: float = 6.0, seed: int = 11):
    """A synthetic daily tape -> pairs, plus two nested configuration masks.

    The masks mimic the real pair of configurations: "quarterly" excludes a
    small subset of pairs, "monthly" excludes a larger superset of them, so
    the two configurations share most (but not all) of their observations,
    exactly as the two roll rules do.
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2021-01-04", periods=n)
    opens, closes = [], []
    prev = 28000.0
    for i in range(n):
        o = prev if i == 0 else prev * (1 + (planted_bps + rng.normal(0, 50)) / 1e4)
        c = o * (1 + rng.normal(0, 70) / 1e4)
        opens.append(o)
        closes.append(c)
        prev = c
    tape = pd.DataFrame({"date": dates, "open": opens, "close": closes})
    pairs = p2.build_pairs(tape)
    m = len(pairs)
    keep_q = np.ones(m, dtype=bool)
    keep_q[::37] = False                 # small exclusion  (quarterly-like)
    keep_m = keep_q.copy()
    keep_m[::13] = False                 # larger exclusion (monthly-like)
    return pairs, keep_q, keep_m


def test_best_of_n_null_matches_the_tested_helper_for_a_single_config():
    """One all-True mask must give exactly the tested helper's stream."""
    pairs, _, _ = _synthetic_pairs()
    x = pairs["r_night_bps"].to_numpy(dtype=float)
    allmask = np.ones(len(x), dtype=bool)
    means, sharpes, per_m, per_s = pf.best_of_n_sign_shuffle_null(
        x, [allmask], [3.0], n=200, seed=20260906)
    assert np.array_equal(means, sign_shuffle_null(x, 200, 20260906))
    assert np.array_equal(means, per_m[0])
    assert np.array_equal(sharpes, per_s[0])
    # and it agrees with the dev-set runner's Sharpe-carrying wrapper too
    ref_mean, ref_sharpe = p2.sign_shuffle_mean_and_sharpe(x, 200, 20260906, 3.0)
    assert np.array_equal(means, ref_mean)
    assert np.allclose(sharpes, ref_sharpe, equal_nan=True)


def test_best_of_2_null_is_the_per_draw_maximum_and_raises_the_bar():
    """The best-of-2 null must be the elementwise max of the two configs'
    nulls (same shared sign draw), so its 95th percentile is >= either one's."""
    pairs, keep_q, keep_m = _synthetic_pairs()
    x = pairs["r_night_bps"].to_numpy(dtype=float)
    years_q, years_m = 2.5, 2.5
    max_means, max_sharpes, per_m, per_s = pf.best_of_n_sign_shuffle_null(
        x, [keep_q, keep_m], [years_q, years_m], n=400, seed=20260906)

    assert len(max_means) == len(max_sharpes) == 400
    assert np.array_equal(max_means, np.maximum(per_m[0], per_m[1]))
    assert np.array_equal(max_sharpes, np.maximum(per_s[0], per_s[1]))
    # the two configurations are genuinely different subsets
    assert int(keep_q.sum()) != int(keep_m.sum())
    assert not np.array_equal(per_m[0], per_m[1])

    p95_best = float(np.percentile(max_means, 95))
    assert p95_best >= float(np.percentile(per_m[0], 95))
    assert p95_best >= float(np.percentile(per_m[1], 95))
    s95_best = float(np.percentile(max_sharpes, 95))
    assert s95_best >= float(np.percentile(per_s[0], 95))
    assert s95_best >= float(np.percentile(per_s[1], 95))

    # a naive independent recomputation of the maximum, draw by draw
    rng = np.random.default_rng(20260906)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(400, len(x)))
    naive = []
    for row in signs:
        d = row * x
        naive.append(max(d[keep_q].mean(), d[keep_m].mean()))
    assert np.allclose(max_means, np.array(naive))


def test_best_of_n_null_validates_its_inputs():
    x = np.array([1.0, -2.0, 3.0, 4.0])
    with pytest.raises(ValueError):
        pf.best_of_n_sign_shuffle_null(x, [], [], n=10, seed=1)
    with pytest.raises(ValueError):
        pf.best_of_n_sign_shuffle_null(x, [np.ones(3, dtype=bool)], [1.0], n=10, seed=1)
    empty_m, empty_s, _, _ = pf.best_of_n_sign_shuffle_null(
        np.array([]), [np.array([], dtype=bool)], [1.0], n=10, seed=1)
    assert len(empty_m) == 0 and len(empty_s) == 0


def test_planted_drift_beats_the_best_of_2_null_on_a_synthetic_tape():
    """Sanity: a large planted overnight drift must clear the (higher)
    best-of-2 bar, so the helper is not simply inert."""
    pairs, keep_q, keep_m = _synthetic_pairs(n=900, planted_bps=30.0, seed=5)
    x = pairs["r_night_bps"].to_numpy(dtype=float)
    max_means, _, _, _ = pf.best_of_n_sign_shuffle_null(
        x, [keep_q, keep_m], [3.5, 3.5], n=500, seed=20260906)
    observed_best = max(float(x[keep_q].mean()), float(x[keep_m].mean()))
    assert observed_best > float(np.percentile(max_means, 95))


# ---------------------------------------------------------------------------
# 2. the three unseal guards
# ---------------------------------------------------------------------------

def _tmp_root(tmp_path: Path, approved: bool) -> Path:
    """A temporary repo root carrying (optionally) the owner approval file."""
    d = tmp_path / "backtest_data" / "phase2_sealed" / "P2-01"
    d.mkdir(parents=True)
    if approved:
        (d / "UNSEAL_APPROVED").write_text("unit: P2-01\napproved_by: test\n",
                                           encoding="utf-8")
    return tmp_path


def test_guards_pass_only_when_all_three_are_present(tmp_path, monkeypatch):
    root = _tmp_root(tmp_path, approved=True)
    monkeypatch.setenv("PHASE2_FINAL_EVAL", "P2-01")
    pf.check_guards(root=root, token=UNSEAL_TOKEN)   # must not raise


def test_guard_env_missing_or_wrong_unit_refuses(tmp_path, monkeypatch):
    root = _tmp_root(tmp_path, approved=True)
    monkeypatch.delenv("PHASE2_FINAL_EVAL", raising=False)
    with pytest.raises(SealedDataError) as e:
        pf.check_guards(root=root, token=UNSEAL_TOKEN)
    assert "PHASE2_FINAL_EVAL" in str(e.value)
    # a DIFFERENT unit in the env is not an approval for P2-01 either
    monkeypatch.setenv("PHASE2_FINAL_EVAL", "P2-02")
    with pytest.raises(SealedDataError):
        pf.check_guards(root=root, token=UNSEAL_TOKEN)


def test_guard_missing_owner_approval_file_refuses(tmp_path, monkeypatch):
    root = _tmp_root(tmp_path, approved=False)
    monkeypatch.setenv("PHASE2_FINAL_EVAL", "P2-01")
    with pytest.raises(SealedDataError) as e:
        pf.check_guards(root=root, token=UNSEAL_TOKEN)
    assert "UNSEAL_APPROVED" in str(e.value)


def test_guard_wrong_token_refuses(tmp_path, monkeypatch):
    root = _tmp_root(tmp_path, approved=True)
    monkeypatch.setenv("PHASE2_FINAL_EVAL", "P2-01")
    with pytest.raises(SealedDataError) as e:
        pf.check_guards(root=root, token="I_UNDERSTAND_REAL_MONEY")
    assert "token" in str(e.value)


def test_guards_refuse_any_unit_other_than_p2_01(tmp_path, monkeypatch):
    """The owner's approval is scoped to P2-01; P2-02 / P2-03 must stay shut
    even if someone points the env and the token at them."""
    root = _tmp_root(tmp_path, approved=True)
    monkeypatch.setenv("PHASE2_FINAL_EVAL", "P2-02")
    with pytest.raises(SealedDataError) as e:
        pf.check_guards(root=root, token=UNSEAL_TOKEN, unit="P2-02")
    assert "P2-01" in str(e.value)


def test_main_refuses_before_touching_anything_when_a_guard_is_missing(
        tmp_path, monkeypatch):
    """main() must fail on the guards BEFORE creating its output directory or
    reading any file."""
    root = _tmp_root(tmp_path, approved=True)
    out = tmp_path / "out"
    monkeypatch.delenv("PHASE2_FINAL_EVAL", raising=False)
    with pytest.raises(SealedDataError):
        pf.main(out_dir=out, root=root, token=UNSEAL_TOKEN)
    assert not out.exists()

    monkeypatch.setenv("PHASE2_FINAL_EVAL", "P2-01")
    with pytest.raises(SealedDataError):
        pf.main(out_dir=out, root=root, token="nope")
    assert not out.exists()


def test_final_configuration_constants_match_the_iteration_ledger():
    assert pf.UNIT == "P2-01"
    assert pf.FINAL_ROLL_RULE == "quarterly"     # ITER.md iteration 1
    assert pf.CUMULATIVE_N == 2                  # monthly + quarterly
    assert (pf.SEALED_START, pf.SEALED_END) == (
        pd.Timestamp("2020-12-21"), pd.Timestamp("2026-08-28"))
    assert (pf.BLOCK, pf.N_BOOT, pf.N_SHUFFLE, pf.SEED) == (20, 2000, 1000, 20260906)
    assert (pf.COST_YEN_CONSERVATIVE, pf.COST_YEN_OPTIMISTIC) == (122, 22)
    assert pf.GLITCH_THRESHOLD == 0.10

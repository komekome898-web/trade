"""T1, T4, T5, T6 (spec section 2) on 200 days of synthetic 1-minute bars,
measured as the spec says (C5 c as corrected on 2026-10-02: L from the
Politis-White length of the P_t series, at least 1,440). Each check has a
broken version that the check catches; among them the two named by the lead
for the correction: L = n, and L taken from the exposure series
(test_w1_blocklen.py)."""
from __future__ import annotations

import dataclasses
import hashlib
import math

import numpy as np
import pytest

from bot.bt.repro import canonical
from bot.research.cards import pnl, run_card
from bot.research.cards.measure import (MIN_BLOCK_BARS, _measure_with_block, block_length, daily_correlation,
                                        daily_rows, measure, read_daily, write_daily)

import w1_synth as W

COMMON = dict(vr_q_bars=None, regimes=None, day_zone="UTC")


def _measure(run, path, *, refs=None, p=None, block=None, seed=W.SEED_BOOT, control_seed=W.SEED_CONTROL):
    """`measure` as the spec says; with `p` or `block`, the same code with a given P series or a given L
    (only for the broken versions)."""
    kw = dict(COMMON, seed=seed, control_seed=control_seed, ref_scenes=refs or {}, daily_path=str(path))
    if p is None and block is None:
        return measure(run, **kw)
    p = pnl(run) if p is None else p
    L, how = block_length(p)
    if block is not None:
        L, how = block, dict(how, rule=f"given L = {block} (broken version)")
    return _measure_with_block(run, p, L, how, **kw)


@pytest.fixture(scope="module")
def t1(tmp_path_factory):
    bars, S, s = W.t1_input()
    run = run_card(W.Always(), bars, references={"S": S}, declarations=W.DECL_T1, venue="synthetic", symbol="T1")
    d = tmp_path_factory.mktemp("t1")
    return {"bars": bars, "S": S, "s": s, "run": run, "dir": d,
            "out": _measure(run, d / "daily.csv", refs={"S": "category"})}


@pytest.fixture(scope="module")
def t5(tmp_path_factory):
    bars = W.t5_input()
    run = run_card(W.PrevSign(), bars, declarations={}, venue="synthetic", symbol="T5")
    d = tmp_path_factory.mktemp("t5")
    return {"bars": bars, "run": run, "dir": d, "out": _measure(run, d / "daily.csv")}


def contains(ci, x):
    return ci is not None and ci[0] <= x <= ci[1]


def check_t1(out) -> list:
    bins = out["scenes"]["ref:S"]["bins"]
    up, down = bins["1.0"]["mean_bp"]["ci"], bins["0.0"]["mean_bp"]["ci"]
    bad = []
    if not contains(up, 2.0):
        bad.append(f"S=1 interval {up} does not contain 2 bp")
    if up is None or contains(up, 0.0):
        bad.append(f"S=1 interval {up} contains 0 (or is missing)")
    if not contains(down, 0.0):
        bad.append(f"S=0 interval {down} does not contain 0")
    return bad


def check_t5(out) -> list:
    m = out["overall"]["mean_bp"]
    bad = []
    if not contains(m["ci"], 0.0):
        bad.append(f"interval {m['ci']} does not contain 0")
    pc = m["control_percentile"]
    if pc is None or not (2.5 <= pc <= 97.5):
        bad.append(f"control percentile {pc} is not in [2.5, 97.5]")
    return bad


# -- T1 ----------------------------------------------------------------------------------------------------

def test_t1_input_is_what_the_spec_says(t1):
    run, s = t1["run"], t1["s"]
    assert len(run.end_ns) == 200 * 1440 and run.end_ns[1] - run.end_ns[0] == W.M
    assert s.mean() == pytest.approx(0.3, abs=1e-12)
    assert np.array_equal(run.ref_value["S"], s.astype(float))  # what the run recorded at t is S at t (lag 0)


def test_t1(t1):
    out = t1["out"]
    bins = out["scenes"]["ref:S"]["bins"]
    print("T1", {"block": out["block"]},
          {b: {x: bins[b]["mean_bp"][x] for x in ("estimate", "ci", "n", "mde")} for b in bins})
    assert not out["block"]["degenerate"] and out["block"]["median_nonzero_run"] == out["block"]["n"]
    assert check_t1(out) == []


def test_t1_broken_versions_are_caught(t1, tmp_path):
    run = t1["run"]
    # the scene recorded one block (60 bars) late: the S=1 group then holds the wrong bars
    late = dataclasses.replace(run, ref_value={"S": np.roll(run.ref_value["S"], 60)})
    found_late = check_t1(_measure(late, tmp_path / "a.csv", refs={"S": "category"}))
    # L = n (the first draft's rule gave this for an always-in card): no interval
    n = int(t1["out"]["block"]["n"])
    found_n = check_t1(_measure(run, tmp_path / "b.csv", refs={"S": "category"}, block=n))
    print("T1 broken", found_late, found_n)
    assert found_late != [] and found_n != []


# -- T5 ----------------------------------------------------------------------------------------------------

def test_t5(t5):
    out = t5["out"]
    m = out["overall"]["mean_bp"]
    print("T5", {"block": out["block"]}, {x: m.get(x) for x in ("estimate", "ci", "n", "mde", "control_percentile")})
    assert not out["block"]["degenerate"]
    assert check_t5(out) == []


def test_t5_broken_versions_are_caught(t5, tmp_path):
    run = t5["run"]
    # P computed with the move of the decision's own bar (open_t -> open_{t+1}): the sign card then 'wins'
    p = pnl(run)
    r = (run.open[p.fill_bar] / run.open[p.bar] - 1.0) * 1e4
    broken = dataclasses.replace(p, r_bp=r, pnl_bp=p.exposure * r)
    found_bar = check_t5(_measure(run, tmp_path / "a.csv", p=broken))
    # L = n: no interval, no control
    n = int(t5["out"]["block"]["n"])
    found_n = check_t5(_measure(run, tmp_path / "b.csv", block=n))
    print("T5 broken", found_bar, found_n)
    assert found_bar != [] and found_n != []


def test_l_at_or_above_half_of_n_gives_no_interval_and_no_control(t1, tmp_path):
    sub = t1["bars"][:2 * 1440 + 1]  # n = 2,879 decisions with a P: 2 L = 2,880 >= n
    run = run_card(W.Always(), sub, references={"S": t1["S"]}, declarations=W.DECL_T1, venue="synthetic", symbol="T1")
    out = _measure(run, tmp_path / "d.csv", refs={"S": "category"})
    assert out["block"]["block_len"] == MIN_BLOCK_BARS and out["block"]["n"] == 2879
    assert out["block"]["degenerate"] and out["control"]["shifts"] is None
    assert out["overall"]["mean_bp"]["ci"] is None and out["overall"]["mean_bp"]["control_percentile"] is None


# -- T4 ----------------------------------------------------------------------------------------------------

def _daily(run, path):
    p = pnl(run)
    write_daily(daily_rows(p, "UTC"), str(path))
    return read_daily(str(path)), block_length(p)[0]


def test_t4_correlation_of_the_daily_series(t5, tmp_path):
    """Card A holds +1 for the first 12 hours of each UTC day, card B for the first 3: B's daily P is the sum
    of 180 of the 720 i.i.d. moves in A's, so the correlation is sqrt(180 / 720) = 0.5."""
    t4 = dict(declarations={}, venue="synthetic", symbol="T4")
    a, La = _daily(run_card(W.FirstHours(12), t5["bars"], **t4), tmp_path / "a.csv")
    b, Lb = _daily(run_card(W.FirstHours(3), t5["bars"], **t4), tmp_path / "b.csv")
    block_days = math.ceil(max(La, Lb) / MIN_BLOCK_BARS)
    c = daily_correlation(a, b, block_days=block_days, seed=W.SEED_CORR)
    print("T4", c, {"La": La, "Lb": Lb})
    assert c["n_days"] == 200 and block_days == 1
    assert contains(c["ci"], 0.5), c
    # the broken version: B's days shuffled (the pairing of days lost)
    days = sorted(b)
    perm = np.random.default_rng(W.SEED_BROKEN).permutation(len(days))
    b_shuffled = {d: b[days[k]] for d, k in zip(days, perm)}
    cb = daily_correlation(a, b_shuffled, block_days=block_days, seed=W.SEED_CORR)
    print("T4 broken", cb)
    assert not contains(cb["ci"], 0.5), cb


# -- T6 ----------------------------------------------------------------------------------------------------

def _bytes(out, path) -> tuple:
    return canonical(out).encode("utf-8"), path.read_bytes()


def test_t6_two_runs_are_bit_identical(t1, tmp_path):
    run2 = run_card(W.Always(), t1["bars"], references={"S": t1["S"]}, declarations=W.DECL_T1, venue="synthetic",
                    symbol="T1")
    r1 = t1["run"]
    assert r1.delivery_digest == run2.delivery_digest
    assert np.array_equal(r1.exposure, run2.exposure, equal_nan=True)
    out2 = _measure(run2, tmp_path / "daily.csv", refs={"S": "category"})
    one, two = _bytes(t1["out"], t1["dir"] / "daily.csv"), _bytes(out2, tmp_path / "daily.csv")
    print("T6", [hashlib.sha256(x).hexdigest()[:16] for x in one], [hashlib.sha256(x).hexdigest()[:16] for x in two])
    assert one == two
    for key in ("overall", "scenes", "frequency", "breakdown", "daily", "control", "block"):  # a..h are in it
        assert key in t1["out"]


def test_t6_the_comparison_sees_a_different_seed(t1, tmp_path):
    """The broken version: a different bootstrap seed changes the bytes, so the comparison above would fail on
    an unseeded run."""
    sub = t1["bars"][:5 * 1440]
    run = run_card(W.Always(), sub, references={"S": t1["S"]}, declarations=W.DECL_T1, venue="synthetic", symbol="T1")
    dirs = [tmp_path / k for k in "abc"]
    for d in dirs:
        d.mkdir()
    a = _measure(run, dirs[0] / "d.csv", refs={"S": "category"})
    b = _measure(run, dirs[1] / "d.csv", refs={"S": "category"})
    c = _measure(run, dirs[2] / "d.csv", refs={"S": "category"}, seed=W.SEED_BOOT + 1)
    assert canonical(a) == canonical(b) and canonical(a) != canonical(c)

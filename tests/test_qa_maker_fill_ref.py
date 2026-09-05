"""Generation-4 CODE-AS-CLAIM known-answer packet for the maker fill model
(docs/AUDIT_2026-09/PROTOCOL.md "Maker fill-model claims", after
docs/QA/known_answer_results_2026-09-05.md §6 found blind re-implementation
of the v3 fill rule non-reproducible across auditors).

Covers: the 8 hand-derived micro-tapes reproduce their hand-computed
expected positions exactly under the CLEAN simulator
(scripts/qa/maker_fill_ref.py); the packet copy pointed to auditors
(scripts/qa/maker_fill_ref_packet.py, containing one planted off-by-one:
`>=` instead of `>` at the completion threshold) diverges from the clean
simulator on micro-tape (d) and ONLY on that tape; determinism; and the
sealed full-tape numbers (docs/QA/answers_sealed_maker4.json) reproduce
from the clean simulator on the reused v3 public tape.
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "qa"))

import maker_fill_ref as ref  # noqa: E402
import maker_fill_ref_packet as pkt  # noqa: E402

MICRO_DIR = REPO_ROOT / "backtest_data" / "qa_known_answer_maker4_20260905" / "micro"
LETTERS = list("abcdefg")  # (h) has its own naive/true split, handled separately


def _load_tape(letter: str):
    t = pd.read_csv(MICRO_DIR / f"ticker_{letter}.csv")
    e = pd.read_csv(MICRO_DIR / f"exec_{letter}.csv")
    return t, e


def _cap_s(letter: str) -> float:
    return 5.0 if letter == "e" else 300.0


def _assert_matches_expected(positions: pd.DataFrame, expected_positions: list[dict]) -> None:
    assert len(positions) == len(expected_positions), (len(positions), expected_positions)
    for i, exp in enumerate(expected_positions):
        row = positions.iloc[i]
        assert row["direction"] == exp["direction"]
        assert str(pd.Timestamp(row["entry_ts"]).isoformat()) == \
            str(pd.Timestamp(exp["entry_ts"]).isoformat())
        assert row["entry_price"] == pytest.approx(exp["entry_price"])
        assert str(pd.Timestamp(row["exit_ts"]).isoformat()) == \
            str(pd.Timestamp(exp["exit_ts"]).isoformat())
        assert row["exit_price"] == pytest.approx(exp["exit_price"])
        assert bool(row["forced"]) == exp["forced"]
        assert row["net_bps"] == pytest.approx(exp["net_bps"], rel=1e-6)
        assert row["markout_5s_bps"] == pytest.approx(exp["markout_5s_bps"], abs=1e-9)


@pytest.mark.parametrize("letter", LETTERS)
def test_micro_tape_matches_hand_derivation(letter):
    """Each micro-tape (a)-(g): the CLEAN reference simulator reproduces
    the hand-computed expected positions exactly (see
    HAND_DERIVATION_<letter>.md, written before this test was run)."""
    t, e = _load_tape(letter)
    positions = ref.simulate(t, e, strategy="S1", cap_s=_cap_s(letter))
    expected = json.loads((MICRO_DIR / f"expected_{letter}.json").read_text())
    _assert_matches_expected(positions, expected["positions"])


def test_micro_tape_h_naive_vs_true():
    t = pd.read_csv(MICRO_DIR / "ticker_h.csv")
    e = pd.read_csv(MICRO_DIR / "exec_h.csv")
    expected = json.loads((MICRO_DIR / "expected_h.json").read_text())
    naive_true = ref.simulate(t, e, strategy="S1", naive=True)
    naive_false = ref.simulate(t, e, strategy="S1", naive=False)
    _assert_matches_expected(naive_true, expected["naive_true"]["positions"])
    _assert_matches_expected(naive_false, expected["naive_false"]["positions"])


def test_packet_copy_diverges_only_on_tape_d():
    """The planted defect (>= instead of >) in maker_fill_ref_packet.py
    must be invisible on every micro-tape except (d), and must actually
    change (d)'s output -- this is the tape an auditor's micro-tape
    verification (docs/AUDIT_2026-09/PROTOCOL.md step (b)) is meant to
    catch it on."""
    diverges = {}
    for letter in LETTERS:
        t, e = _load_tape(letter)
        clean = ref.simulate(t, e, strategy="S1", cap_s=_cap_s(letter))
        defective = pkt.simulate(t, e, strategy="S1", cap_s=_cap_s(letter))
        diverges[letter] = not clean.equals(defective)
    assert diverges == {"a": False, "b": False, "c": False, "d": True, "e": False,
                         "f": False, "g": False}

    t, e = _load_tape("d")
    clean = ref.simulate(t, e, strategy="S1")
    defective = pkt.simulate(t, e, strategy="S1")
    assert clean.loc[0, "entry_ts"] != defective.loc[0, "entry_ts"]
    assert str(pd.Timestamp(defective.loc[0, "entry_ts"]).isoformat()) == "2026-01-01T00:00:03+00:00"
    assert str(pd.Timestamp(clean.loc[0, "entry_ts"]).isoformat()) == "2026-01-01T00:00:04+00:00"


@pytest.mark.parametrize("letter", LETTERS)
def test_determinism(letter):
    t, e = _load_tape(letter)
    r1 = ref.simulate(t, e, strategy="S1", cap_s=_cap_s(letter))
    r2 = ref.simulate(t, e, strategy="S1", cap_s=_cap_s(letter))
    assert r1.equals(r2)


# --------------------------------------------------------------------- #
# Full tape (reused v3 public files) + sealed json reproduction
# --------------------------------------------------------------------- #
FULL_TAPE_DIR = REPO_ROOT / "backtest_data" / "qa_known_answer_maker3_v3_20260905"
SEALED_PATH = REPO_ROOT / "docs" / "QA" / "answers_sealed_maker4.json"


def _summarize(positions: pd.DataFrame) -> dict:
    n = len(positions)
    net = positions["net_bps"]
    forced = positions["forced"]
    return {
        "n_positions": int(n),
        "net_bps_mean": float(net.mean()) if n else float("nan"),
        "forced_exit_fraction": float(forced.mean()) if n else float("nan"),
    }


@pytest.mark.skipif(not FULL_TAPE_DIR.exists(), reason="v3 full-tape packet not present")
def test_sealed_full_tape_numbers_reproduce_from_clean_simulator():
    with gzip.open(FULL_TAPE_DIR / "ticker_qa_maker3_v3_tape.csv.gz", "rt") as f:
        ticker_df = pd.read_csv(f)
    with gzip.open(FULL_TAPE_DIR / "executions_qa_maker3_v3_tape.csv.gz", "rt") as f:
        exec_df = pd.read_csv(f)
    sealed = json.loads(SEALED_PATH.read_text())

    for label, strategy, naive in (("S1", "S1", False), ("S2", "S2", False), ("naive", "S1", True)):
        got = _summarize(ref.simulate(ticker_df, exec_df, strategy=strategy, naive=naive))
        want = sealed[label]
        assert got["n_positions"] == want["n_positions"], label
        assert got["net_bps_mean"] == pytest.approx(want["net_bps_mean"], rel=1e-6), label
        assert got["forced_exit_fraction"] == pytest.approx(want["forced_exit_fraction"], rel=1e-6), label

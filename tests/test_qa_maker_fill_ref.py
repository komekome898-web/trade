"""Generation-4 CODE-AS-CLAIM known-answer packet for the maker fill model,
round 2 (docs/AUDIT_2026-09/PROTOCOL.md "Maker fill-model claims"), after
docs/AUDIT_2026-09/QAM4_auditorB.md found three defects in round 1:

1. Forced (cap) exits were priced at the FAVOURABLE (resting-exit-order)
   side's touch instead of the UNFAVOURABLE side the position's own entry
   sits on (a long must taker-sell into the bid, not the ask). Fixed in
   `check_caps`.
2. Exit-order queue-ahead ignored the rule text's "minus own size" clause
   (the displayed size at insertion already includes our own just-joined
   clip). Fixed in `refresh`.
3. `RULE_DECISIONS` lacked a definition of naive mode. Added.

Covers: the 9 hand-derived micro-tapes (a-g, i; h has its own naive/true
split, handled separately) reproduce their hand-computed expected
positions exactly under the CLEAN simulator (scripts/qa/maker_fill_ref.py,
fixed); the round-2 packet copy pointed to auditors
(scripts/qa/maker_fill_ref_packet_r2.py, containing one NEW planted
defect -- a touch-move rejoin keeps the OLD cumulative-print counter
instead of resetting it to zero) diverges from the clean simulator on
micro-tape (i) and ONLY on that tape; determinism; and the sealed
full-tape numbers (docs/QA/answers_sealed_maker4_r2.json) reproduce from
the clean, fixed simulator on the reused v3 public tape.
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
import maker_fill_ref_packet_r2 as pkt  # noqa: E402

MICRO_DIR = REPO_ROOT / "backtest_data" / "qa_known_answer_maker4_r2_20260905" / "micro"
LETTERS = list("abcdefgi")  # (h) has its own naive/true split, handled separately


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
    """Each micro-tape (a)-(g),(i): the CLEAN reference simulator reproduces
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


def test_forced_exit_prices_at_unfavourable_side():
    """Round-1 defect (QAM4_auditorB finding 1): a forced/cap exit is a
    TAKER cross and must price at the UNFAVOURABLE touch -- the position's
    own entry side (bid for a long, ask for a short) -- not the favourable
    side the (cancelled) passive exit order was resting at."""
    ticker = pd.DataFrame({
        "ts": pd.date_range("2026-01-01T00:00:00Z", periods=10, freq="s"),
        "best_bid": 1000.0, "best_ask": 1010.0,
        "best_bid_size": 0.05, "best_ask_size": 0.05,
    })
    # Long: entry on the bid. Nothing ever fills the exit -> forced at cap.
    long_exec = pd.DataFrame([
        dict(id="l1", ts="2026-01-01T00:00:01Z", price=1000, size=0.11, side="SELL"),
    ])
    long_pos = ref.simulate(ticker, long_exec, strategy="S1", cap_s=3.0)
    assert len(long_pos) == 1
    row = long_pos.iloc[0]
    assert row["direction"] == "long"
    assert row["forced"]
    assert row["exit_price"] == pytest.approx(1000.0)  # crosses into the BID, not the ask

    # Short: entry on the ask. Nothing ever fills the exit -> forced at cap.
    short_exec = pd.DataFrame([
        dict(id="s1", ts="2026-01-01T00:00:01Z", price=1010, size=0.11, side="BUY"),
    ])
    short_pos = ref.simulate(ticker, short_exec, strategy="S1", cap_s=3.0)
    assert len(short_pos) == 1
    row = short_pos.iloc[0]
    assert row["direction"] == "short"
    assert row["forced"]
    assert row["exit_price"] == pytest.approx(1010.0)  # crosses into the ASK, not the bid


def test_exit_queue_ahead_subtracts_own_size():
    """Round-1 defect (QAM4_auditorB finding 2): an EXIT order's queue-ahead
    at insertion = displayed size MINUS own_size (rule text + v3 manifest:
    'the displayed size at insertion already includes our own just-joined
    clip'); an ENTRY order's queue-ahead uses the raw displayed size (no
    clip of ours rests there yet) -- RULE_DECISIONS #6."""
    ticker = pd.DataFrame({
        "ts": pd.date_range("2026-01-01T00:00:00Z", periods=10, freq="s"),
        "best_bid": 1000.0, "best_ask": 1010.0,
        "best_bid_size": 0.05, "best_ask_size": 0.10,
    })
    exec_df = pd.DataFrame([
        # entry: raw displayed bid size 0.05 -> threshold 0.05+0.05=0.10; 0.11 exceeds it.
        dict(id="x1", ts="2026-01-01T00:00:01Z", price=1000, size=0.11, side="SELL"),
        # exit: displayed ask size 0.10 MINUS own_size 0.05 = 0.05 -> threshold 0.10;
        # 0.12 exceeds 0.10 (it would NOT exceed an un-subtracted threshold of 0.15).
        dict(id="x2", ts="2026-01-01T00:00:02Z", price=1010, size=0.12, side="BUY"),
    ])
    positions = ref.simulate(ticker, exec_df, strategy="S1", cap_s=300.0)
    assert len(positions) == 1
    row = positions.iloc[0]
    assert str(pd.Timestamp(row["entry_ts"]).isoformat()) == "2026-01-01T00:00:01+00:00"
    assert str(pd.Timestamp(row["exit_ts"]).isoformat()) == "2026-01-01T00:00:02+00:00"
    assert not row["forced"]


def test_packet_r2_diverges_only_on_tape_i():
    """The round-2 planted defect (a touch-move rejoin keeps the OLD
    cumulative-print counter instead of resetting to zero) must be
    invisible on every micro-tape except (i), and must actually change
    (i)'s output -- this is the tape an auditor's micro-tape verification
    (docs/AUDIT_2026-09/PROTOCOL.md step (b)) is meant to catch it on.
    Tape (c), the packet's other touch-move-rejoin tape, does NOT expose
    it (see HAND_DERIVATION_i.md) -- only (i) does."""
    diverges = {}
    for letter in LETTERS:
        t, e = _load_tape(letter)
        clean = ref.simulate(t, e, strategy="S1", cap_s=_cap_s(letter))
        defective = pkt.simulate(t, e, strategy="S1", cap_s=_cap_s(letter))
        diverges[letter] = not clean.equals(defective)
    assert diverges == {"a": False, "b": False, "c": False, "d": False, "e": False,
                         "f": False, "g": False, "i": True}

    # (h)'s naive/true split is also unaffected by the round-2 defect.
    t, e = pd.read_csv(MICRO_DIR / "ticker_h.csv"), pd.read_csv(MICRO_DIR / "exec_h.csv")
    for naive in (True, False):
        clean = ref.simulate(t, e, strategy="S1", naive=naive)
        defective = pkt.simulate(t, e, strategy="S1", naive=naive)
        assert clean.equals(defective)

    t, e = _load_tape("i")
    clean = ref.simulate(t, e, strategy="S1")
    defective = pkt.simulate(t, e, strategy="S1")
    assert clean.loc[0, "entry_ts"] != defective.loc[0, "entry_ts"]
    assert str(pd.Timestamp(defective.loc[0, "entry_ts"]).isoformat()) == "2026-01-01T00:00:03+00:00"
    assert str(pd.Timestamp(clean.loc[0, "entry_ts"]).isoformat()) == "2026-01-01T00:00:05+00:00"


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
SEALED_PATH = REPO_ROOT / "docs" / "QA" / "answers_sealed_maker4_r2.json"


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

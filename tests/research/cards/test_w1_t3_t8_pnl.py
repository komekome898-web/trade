"""T3 (the profit and loss is right, and t's exposure meets the move from the
open of t+1 to the open of t+2) and T8 (empty bars: the fill is the open of
the first non-empty bar after them, and the time waited is recorded); C1's
check of the exposure."""
from __future__ import annotations

import numpy as np
import pytest

from bot.research.cards import ExposureError, pnl, run_card
from bot.research.cards.pnl import PnL

from w1_synth import BP, M, T0, bars_from_moves


class Cycle:
    """+1, -1, 0, +1, -1, 0, ... by its own call count (state is allowed; no randomness)."""
    name = "cycle"
    requires = ()

    def __init__(self):
        self.k = 0
        self.bars_seen = []

    def exposure(self, view):
        self.bars_seen.append(len(view.bars(10_000)))
        x = (1.0, -1.0, 0.0)[self.k % 3]
        self.k += 1
        return x


def broken_pnl_same_bar(run) -> np.ndarray:
    """A broken version: the exposure meets the move of its own bar (open_t -> open_{t+1})."""
    good = pnl(run)
    r = (run.open[good.fill_bar] / run.open[good.bar] - 1.0) * 100.0
    return good.exposure * r


def check_alignment(pnl_pct: np.ndarray, n_bars: int) -> list:
    """Moves are (k + 1) bp for bar k, so P_i must be e_i * (i + 2) bp of move, i.e. e_i * (i + 2) * 0.01 % (the
    move of bar i + 1, from the open of t+1 to the open of t+2; P_t is in percent, L-920). Returns the decisions
    where it is not."""
    e = np.array([(1.0, -1.0, 0.0)[i % 3] for i in range(n_bars - 2)])
    want = e * (np.arange(n_bars - 2) + 2.0) * 0.01
    return [i for i in range(n_bars - 2) if abs(pnl_pct[i] - want[i]) > 1e-11]


def test_t3_sum_matches_the_hand_value():
    # every bar moves +1 bp: open_{k+1} = open_k * 1.0001
    run = run_card(Cycle(), bars_from_moves(np.full(30, BP)), declarations={}, venue="synthetic", symbol="T3")
    p = pnl(run)
    assert p.n_decisions == 30 and p.n_undefined == 2 and len(p.pnl_pct) == 28
    # by hand: e = +1, -1, 0 repeated over the 28 decisions with a t+2 open -> 9 whole cycles (0) and one +1
    # more, each times a 1 bp move = 0.01 %
    assert abs(float(p.pnl_pct.sum()) - 0.01) <= 1e-11
    assert np.all(np.abs(p.r_bp - 1.0) <= 1e-9)


def test_t3_exposure_meets_the_move_from_t_plus_1_to_t_plus_2():
    n = 40
    moves = (np.arange(n) + 1.0) * BP  # bar k moves (k + 1) bp: every move is different
    run = run_card(Cycle(), bars_from_moves(moves), declarations={}, venue="synthetic", symbol="T3")
    p = pnl(run)
    assert check_alignment(p.pnl_pct, n) == []
    # by hand, the sum: sum over i < 38 of e_i * (i + 2)
    hand = sum((1.0, -1.0, 0.0)[i % 3] * (i + 2) for i in range(n - 2))
    assert abs(float(p.pnl_pct.sum()) - hand * 0.01) <= 1e-11
    assert list(p.fill_bar[:3]) == [1, 2, 3] and list(p.exit_bar[:3]) == [2, 3, 4]
    assert np.all(p.fill_wait_ns == 0) and np.all(p.hold_ns == M)


def test_t3_broken_version_is_caught():
    n = 40
    run = run_card(Cycle(), bars_from_moves((np.arange(n) + 1.0) * BP), declarations={}, venue="synthetic", symbol="T3")
    assert check_alignment(broken_pnl_same_bar(run), n) != []


def test_t3_the_card_sees_bars_up_to_t_only():
    card = Cycle()
    run_card(card, bars_from_moves(np.full(30, BP)), declarations={}, venue="synthetic", symbol="T3")
    assert card.bars_seen == list(range(1, 31))


GAP = range(10, 40)  # 30 bars


def test_t8_missing_bars():
    moves = (np.arange(60) + 1.0) * BP
    bars = bars_from_moves(moves, missing=GAP)
    assert len(bars) == 30
    run = run_card(Cycle(), bars, declarations={}, venue="synthetic", symbol="T8")
    p = pnl(run)
    i9 = int(np.flatnonzero(p.bar == 9)[0])  # the decision at the close of bar 9, just before the gap
    assert p.t_ns[i9] == T0 + 10 * M
    assert run.start_ns[p.fill_bar[i9]] == T0 + 40 * M  # filled at the open of bar 40, the first after the gap
    assert p.fill_wait_ns[i9] == 30 * M  # the time waited is recorded
    assert p.r_bp[i9] == pytest.approx((run.open[p.exit_bar[i9]] / run.open[p.fill_bar[i9]] - 1) * 1e4, abs=0)
    assert run.start_ns[p.exit_bar[i9]] == T0 + 41 * M
    i8 = int(np.flatnonzero(p.bar == 8)[0])  # filled at bar 9's open, held across the gap to bar 40's open
    assert p.fill_wait_ns[i8] == 0 and p.hold_ns[i8] == 31 * M
    assert int((p.fill_wait_ns > 0).sum()) == 1


def broken_pnl_next_listed_bar(run) -> PnL:
    """A broken version: the fill is the next bar listed, empty or not."""
    k = np.arange(len(run.end_ns) - 2)
    keep = run.decided[k]
    bar, fill, exit_ = k[keep], k[keep] + 1, k[keep] + 2
    e = run.exposure[bar]
    ratio = run.open[exit_] / run.open[fill] - 1.0
    return PnL(bar, run.end_ns[bar], e, fill, exit_, run.start_ns[fill] - run.end_ns[bar],
               run.start_ns[exit_] - run.start_ns[fill], ratio * 1e4, e * (ratio * 100.0), int(run.decided.sum()), 0)


def check_t8(run, p: PnL) -> list:
    bad = []
    i9 = np.flatnonzero(p.bar == 9)
    if len(i9) != 1:
        return ["no decision at bar 9"]
    i9 = int(i9[0])
    if run.start_ns[p.fill_bar[i9]] != T0 + 40 * M:
        bad.append("fill is not the first non-empty bar after the gap")
    if p.fill_wait_ns[i9] != 30 * M:
        bad.append("the wait is not recorded")
    return bad


def test_t8_empty_bars_present_with_volume_zero():
    moves = (np.arange(60) + 1.0) * BP
    bars = bars_from_moves(moves, empty=GAP)
    card = Cycle()
    run = run_card(card, bars, declarations={}, venue="synthetic", symbol="T8")
    assert len(run.end_ns) == 60 and int(run.decided.sum()) == 30  # no decision at an empty bar
    assert not run.decided[10:40].any() and np.isnan(run.exposure[10:40]).all()
    assert card.bars_seen[10] == 41  # the decision at bar 40 sees the empty bars too (they were delivered)
    assert check_t8(run, pnl(run)) == []
    assert check_t8(run, broken_pnl_next_listed_bar(run)) != []


class Answers:
    requires = ()

    def __init__(self, x):
        self.x, self.name = x, "answers"

    def exposure(self, view):
        return self.x


@pytest.mark.parametrize("x", [1.5, -1.0000001, float("nan"), float("inf"), True, "1", None, np.bool_(True)])
def test_an_exposure_outside_minus_1_to_1_or_not_a_number_is_refused(x):
    with pytest.raises(ExposureError):
        run_card(Answers(x), bars_from_moves(np.full(3, BP)), declarations={}, venue="synthetic", symbol="C1")


@pytest.mark.parametrize("x", [1, -1, 0, 0.25, np.float64(-0.5), np.int64(1)])
def test_a_number_in_range_is_accepted(x):
    run = run_card(Answers(x), bars_from_moves(np.full(3, BP)), declarations={}, venue="synthetic", symbol="C1")
    assert np.all(run.exposure == float(x))

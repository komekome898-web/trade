"""Profit and loss before costs of a card run (W1 spec C2).

The exposure e_t taken at the end t of a bar is filled at the open of the
next bar and held until the open of the bar after that:

    P_t = e_t * (open_{t+2} / open_{t+1} - 1) * 10,000     (bp per unit of exposure)

Empty bars (no trade) are skipped: when the next bar is empty or missing,
the fill is the open of the next non-empty bar, and the time waited is
recorded (`fill_wait_ns` = that bar's open - t; 0 when the next bar follows
at once). "t+1" and "t+2" are therefore the next two non-empty bars after
t. The same rule gives the exit: the open of the non-empty bar after the
fill bar, i.e. the fill of the next decision. `hold_ns` is the time from
the fill to the exit.

r_{t+1} = open_{t+2} / open_{t+1} - 1 (in bp) is the move the exposure is
exposed to; the measurement (measure.py) uses the same r. The last two
decisions of a run have no t+2 open and get no P (counted in `n_undefined`).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .run import CardRun

BP = 10_000.0


@dataclass(frozen=True)
class PnL:
    bar: np.ndarray  # index (into the run's bars) of the decision bar
    t_ns: np.ndarray  # decision time t (the bar's close)
    exposure: np.ndarray
    fill_bar: np.ndarray
    exit_bar: np.ndarray
    fill_wait_ns: np.ndarray  # open of the fill bar - t
    hold_ns: np.ndarray  # open of the exit bar - open of the fill bar
    r_bp: np.ndarray  # (open_exit / open_fill - 1) * 1e4
    pnl_bp: np.ndarray  # exposure * r_bp
    n_decisions: int
    n_undefined: int  # decisions without a t+2 open (end of the run)


def pnl(run: CardRun) -> PnL:
    dec = np.flatnonzero(run.decided)  # the non-empty bars, in order (a card is called at every one)
    nonempty = np.flatnonzero(run.volume > 0)
    if not np.array_equal(dec, nonempty):  # pragma: no cover - run_card guarantees it
        raise ValueError("the decisions are not the non-empty bars")
    m = len(dec) - 2
    if m < 1:
        raise ValueError(f"a run with {len(dec)} non-empty bars has no decision with a t+2 open")
    bar, fill, exit_ = dec[:m], dec[1:m + 1], dec[2:m + 2]
    e = run.exposure[bar]
    r = (run.open[exit_] / run.open[fill] - 1.0) * BP
    return PnL(
        bar=bar, t_ns=run.end_ns[bar], exposure=e, fill_bar=fill, exit_bar=exit_,
        fill_wait_ns=run.start_ns[fill] - run.end_ns[bar], hold_ns=run.start_ns[exit_] - run.start_ns[fill],
        r_bp=r, pnl_bp=e * r, n_decisions=len(dec), n_undefined=len(dec) - m,
    )


__all__ = ["BP", "PnL", "pnl"]

"""Card 1 of W4: the current paper bot's strategy xborder_momentum as a card.

Source text and intent map: docs/RESEARCH/cards/c1_xborder_mom/ (CARD.md,
INTENT_MAP.md). Source: the bot's code src/bot/strategy/xborder_momentum.py
(XborderMomentumStrategy.on_candles), its settings config/config.yaml
(strategy.params k / thr_pct / exit_pct, candle_interval_sec, leader), the
leader feed src/bot/market_data/external_feed.py (BinanceFeed.close_for) and
the description in docs/DISCUSSIONS/2026-10-02_W5_stage7_design.md section 5-1.

At the end t of each non-empty bitFlyer FX_BTC_JPY 1-minute bar (start s = t - 1 min):

  1. Fewer than k + 2 bars visible -> 様子見 ("insufficient history"; the
     bot's min_history = k + 2).
  2. The leader price of a minute is the Binance BTCUSDT close of that
     minute; when its row is missing, the close of at most 2 earlier minutes
     (the bot's close_for(interval_start, max_age_intervals=2)).
         now  = leader of the minute starting s
         past = leader of the minute starting s - k min ("Binance の k 本前")
     Either missing, or past <= 0 -> 様子見 ("leader data gap").
  3. mom = ln(now / past); thr = thr_pct / 100; band = exit_pct / 100
         mom >  thr          -> 買い  e = +1
         mom < -thr          -> 売り  e = -1
         |mom| <= band       -> 決済  e =  0
         otherwise           -> 様子見 e = the previous e (0 before any)
     The comparisons and the float construction are the bot's, unchanged.

The card answers e through the card mouth (`exposure`) and keeps, per call,
the kind of the bar's signal (買い / 売り / 決済 / 様子見): `last` holds the
latest `Decision`, `kinds()` the whole sequence. The legacy combiner of the
stage-7 design (section 5-1, version X0) reads the kind; e alone cannot tell
a 買い from a 様子見 after a 買い.

Outside the card (the bot's shell, design section 5-1): the stop-loss
(stop_loss_pct 0.5), closing only (no reversal in one bar) on the opposite
signal, no adding to a position, the SFD guard, the short check, sizing,
the kill switch and the stale pause.

Reference series (CARD.md 測定の設定): each row's time is the START of its
minute (the store's open_time, unshifted) and its value that minute's close;
lag 60 s, so the row of the minute ending at t (row time t - 60 s) becomes
available at t and not before. The store is read as it is (no shifted
time); a series declared with another lag is refused by `run_card`, since
the card states lag 60 s in `requires`. The card reads only
`view.bars(k + 2)` and `view.ref_at(name, x)` with x + 60 s <= t; it never
names a row not yet available. Same input, same output.
"""
from __future__ import annotations

import math
from array import array
from dataclasses import dataclass
from typing import Optional

import numpy as np

from bot.research.cards.card import CardView, SeriesSpec

NS = 1_000_000_000
MINUTE_NS = 60 * NS  # config/config.yaml candle_interval_sec: 60 (the bot's bars and its leader intervals)

LEADER = "binance_btcusdt_close"  # Binance BTCUSDT 1m close, row time = open_time (config leader: BTCUSDT)
LAG_NS = MINUTE_NS  # the lead's answer of 2026-10-02 (card 1, point 1): open_time rows, usable at the minute's end

# The bot's settings (config/config.yaml strategy.params, lines 31-33); the code's own defaults
# (k 10, exit_pct 0.1) are not what runs and are not used.
K = 30
THR_PCT = 0.8
EXIT_PCT = 0.05
# BinanceFeed.close_for(interval_start, max_age_intervals=2) (src/bot/market_data/external_feed.py).
MAX_AGE_INTERVALS = 2

BUY, SELL, CLOSE, HOLD = "買い", "売り", "決済", "様子見"
KINDS = (BUY, SELL, CLOSE, HOLD)
_CODE = {k: i for i, k in enumerate(KINDS)}


@dataclass(frozen=True)
class Decision:
    t_ns: int
    e: float
    kind: str
    reason: str
    mom: Optional[float]  # ln(now / past); None when not computed


class XborderMom:
    """The card (module docstring)."""

    name = "xborder_mom"

    def __init__(self, k: int = K, thr_pct: float = THR_PCT, exit_pct: float = EXIT_PCT,
                 max_age_intervals: int = MAX_AGE_INTERVALS, interval_ns: int = MINUTE_NS) -> None:
        self.k = int(k)
        self.thr = float(thr_pct) / 100
        self.exit_band = float(exit_pct) / 100
        self.max_age = int(max_age_intervals)
        self.interval = int(interval_ns)
        self.requires = (SeriesSpec(LEADER, LAG_NS),)
        self._e = 0.0
        self.last: Optional[Decision] = None
        self._t = array("q")
        self._kind = array("b")

    @property
    def min_history(self) -> int:
        return self.k + 2

    def kinds(self) -> tuple[np.ndarray, list[str]]:
        """(decision times ns, the kind of each call), in call order."""
        return np.asarray(self._t, dtype=np.int64), [KINDS[c] for c in self._kind]

    def _leader(self, view: CardView, interval_start: int) -> Optional[float]:
        """The close of the minute starting `interval_start` (its row is stamped at the minute's start,
        open_time), else of at most `max_age` earlier minutes; None when none of them has a row."""
        for back in range(self.max_age + 1):
            try:
                return view.ref_at(LEADER, interval_start - back * self.interval)
            except KeyError:
                continue
        return None

    def _signal(self, view: CardView) -> tuple[str, str, Optional[float]]:
        bars = view.bars(self.min_history)
        if len(bars) < self.min_history:
            return HOLD, "insufficient history", None
        s = int(bars[-1].start_time_ns)
        now = self._leader(view, s)
        past = self._leader(view, s - self.k * self.interval)
        if now is None or past is None or past <= 0:
            return HOLD, "leader data gap", None
        with np.errstate(divide="ignore", invalid="ignore"):
            mom = float(np.log(now / past))
        if mom > self.thr:
            return BUY, "leader above +thr", mom
        if mom < -self.thr:
            return SELL, "leader below -thr", mom
        if abs(mom) <= self.exit_band:
            return CLOSE, "leader momentum faded", mom
        return HOLD, "between exit band and threshold", mom

    def exposure(self, view: CardView) -> float:
        kind, reason, mom = self._signal(view)
        if kind == BUY:
            self._e = 1.0
        elif kind == SELL:
            self._e = -1.0
        elif kind == CLOSE:
            self._e = 0.0
        t = int(view.now_ns)
        self.last = Decision(t, self._e, kind, reason, None if mom is None or math.isnan(mom) else mom)
        self._t.append(t)
        self._kind.append(_CODE[kind])
        return self._e


__all__ = ["BUY", "CLOSE", "Decision", "EXIT_PCT", "HOLD", "K", "KINDS", "LAG_NS", "LEADER", "MAX_AGE_INTERVALS",
           "MINUTE_NS", "SELL", "THR_PCT", "XborderMom"]

"""Card 7 of W4: barrier race, contrarian (バリアレース逆張り), held on bitFlyer FX_BTC_JPY.

Source text and intent map: docs/RESEARCH/cards/c7_barrier_race/ (CARD.md,
INTENT_MAP.md). Source idea: docs/STRATEGY_IDEAS.md #48
「価格が一定幅動いたときに、その後さらに同方向へ動く(継続)か反対方向へ戻る(反転)かのどちらが優勢か」,
named 「バリアレース逆張り」.

The source gives no value for the width (「一定幅」), no starting point of the
move and no holding time. The card puts no number of its own (A-12):

  * The width comes from a window, and the window is the only choice: one of
    W1 spec C4's 1 hour / 1 day / 1 week (`window` = "1h" / "1d" / "1w",
    variants; no default). At the start of each race the width is
        w = sqrt(sum of r**2 over the window)
    where r are the close-to-close log returns between consecutive bars the
    card was called on whose end lies in (t - window, t]. That is the size of
    a window-long move at the window's own volatility; not C4's 局所ボラ (a std:
    no mean removed, no division by the count). w is fixed for the whole
    race (「一定幅」 within a race; INTENT_MAP.md I-2, a proxy).
  * A race starts at an anchor = log close of the bar it starts on, with
    barriers anchor +/- w. A race ends at the first bar whose log close is
    at or beyond a barrier (the close is tested, not the high / low). The
    next race starts at that same bar (anchor = its log close, new w), so
    races are chained: each one is "the price moved by w" (I-1).
  * Contrarian (the name's 「逆張り」, I-4): after an upper hit hold -1, after
    a lower hit hold +1, and keep it until the next hit. So each race after
    the first one is a bet that the previous move of w reverses: it gains
    about w if the next hit is the other barrier (反転) and loses about w if
    it is the same one (継続). The sign of the measured mean answers the
    source's question (I-3); the card does not presume it.
  * Before the first hit the card holds 0. Until the window has elapsed
    since the first bar the card was called on (warm-up), no race starts.
    If w == 0 (no move in the window), no race starts at that bar; the card
    keeps its exposure and tries again at the next bar.

The card reads only `view.bars(1)` and `view.now_ns`; it requires no
reference series (`requires = ()`). It never names a later bar. Same input,
same output (no random numbers; math.fsum in a fixed order).
"""
from __future__ import annotations

import math
from collections import deque

from bot.research.cards.card import CardError, CardView
from bot.research.cards.scenes import WINDOWS as C4_WINDOWS

# W1 spec C4's windows (1 hour, 1 day, 1 week): the variants of the width's window. Not tuned values (A-12).
WINDOWS = dict(C4_WINDOWS)


class BarrierRace:
    """The card (module docstring). `window` is one of "1h", "1d", "1w" (W1 spec C4), no default."""

    name = "c7_barrier_race"
    requires = ()

    def __init__(self, window: str) -> None:
        if type(window) is not str or window not in WINDOWS:
            raise CardError(f"{self.name}: window must be one of {list(WINDOWS)}: {window!r}")
        self.window = window
        self._w_ns = WINDOWS[window]
        self._first_end = None  # end of the first bar the card was called on
        self._prev_log_close = None
        self._r2 = deque()  # (bar end ns, r**2) of the returns in the window
        self._anchor = None  # log close at the start of the current race
        self._width = None  # w of the current race
        self._exposure = 0.0

    def _window_width(self) -> float:
        return math.sqrt(math.fsum(v for _, v in self._r2))

    def _start_race(self, log_close: float) -> None:
        w = self._window_width()
        if w > 0.0:
            self._anchor, self._width = log_close, w
        else:  # no move in the window: no barrier can be set at this bar
            self._anchor, self._width = None, None

    def exposure(self, view: CardView) -> float:
        t = view.now_ns
        bar = view.bars(1)[0]
        if int(bar.exchange_time_ns) != t:
            raise ValueError(f"{self.name} at t={t}: the newest bar ends at {bar.exchange_time_ns}, not at t "
                             f"(the card is called at the end of the bar it reads)")
        close = float(bar.close)
        if not (close > 0.0 and math.isfinite(close)):
            raise ValueError(f"{self.name} at t={t}: close must be a finite positive price, got {close!r}")
        x = math.log(close)
        if self._first_end is None:
            self._first_end = t
        if self._prev_log_close is not None:
            self._r2.append((t, (x - self._prev_log_close) ** 2))
        self._prev_log_close = x
        while self._r2 and self._r2[0][0] <= t - self._w_ns:
            self._r2.popleft()
        if self._first_end > t - self._w_ns:  # warm-up: the window has not elapsed since the first call
            return self._exposure
        if self._anchor is None:
            self._start_race(x)
            return self._exposure
        move = x - self._anchor
        if move >= self._width:  # upper barrier: the price moved up by w -> bet on the reversal
            self._exposure = -1.0
            self._start_race(x)
        elif move <= -self._width:  # lower barrier: the price moved down by w -> bet on the reversal
            self._exposure = 1.0
            self._start_race(x)
        return self._exposure


__all__ = ["BarrierRace", "WINDOWS"]

"""Card 3 of W4: the reversion of the yen premium (円の上乗せの戻り).

Source text and intent map: docs/RESEARCH/cards/c3_yen_premium_revert/
(CARD.md, INTENT_MAP.md). Source idea: D1-D-21
(docs/RESEARCH/ideas/round1/IDEAS_D.md), from the identity
bitFlyer FX_BTC_JPY = BTCUSD x USDJPY x (1 + yen premium).

At the end t of each non-empty bitFlyer FX_BTC_JPY 1-minute bar:

  1. The premium, from the bitFlyer bar that just closed, the Binance
     BTCUSDT close of the same minute (the reference row stamped t - 60 s,
     the start of the minute that ends at t) and the newest USDJPY close
     available at t (as-of: while the FX market is shut,
     weekends and holidays, its last value):
         p_t = ln(bitFlyer close) - ln(Binance close x USDJPY close)
     If Binance has no row stamped t - 60 s, or no USDJPY row has arrived yet, the
     card holds 0 and keeps no value for that minute.
  2. Its position in the distribution of the premiums the card itself formed
     in the trailing window (t - W, t) (the current value excluded):
         q = (#values < p_t + 0.5 x #values == p_t) / #values
  3. exposure = 1 - 2q: a premium above every recent value gives -1 (sell
     bitFlyer, the side that closes the premium), below every one +1, the
     middle 0. The size grows with how far outside the recent distribution
     the premium is; there is no cutoff (the source gives none, A-12).
  4. Until the window has elapsed once since the first premium the card
     formed (t - first < W), or when the window holds no earlier value, the
     card holds 0.

W is one of the three windows of W1 spec C4 (1 hour, 1 day, 1 week), chosen
by the caller by name; no other window is accepted (CARD.md 水準とその出所).

Reference series (CARD.md 測定の設定): each row's time is the store's own
time, the START of its minute (Binance open_time, Dukascopy timestamp; not
shifted), and its value that minute's close; declared lag 60 s, so the row
of the minute that ends at t becomes available at t and not before. A series
declared with another lag is refused by run_card (the card states 60 s in
`requires`).

The card reads only `view.bars(1)`, `view.ref_at(OVERSEAS, t - 60 s)` with
t = `view.now_ns` and `view.ref_latest(FX)` (the newest row available at t
under the 60 s lag); it never names a row that is not yet available. Same input, same output
(no random numbers).
"""
from __future__ import annotations

import bisect
import math
from collections import deque

from bot.research.cards.card import CardView, SeriesSpec

NS = 1_000_000_000
# The windows of W1 spec C4 (docs/DISCUSSIONS/2026-10-02_W1_spec.md): natural clock units, fixed before measuring.
WINDOWS = {"1h": 3_600 * NS, "1d": 86_400 * NS, "1w": 7 * 86_400 * NS}

OVERSEAS = "binance_btcusdt_close"  # Binance BTCUSDT 1m close, row time = open_time (start of the minute)
FX = "usdjpy_close"  # USDJPY 1m BID close (Dukascopy), row time = timestamp (start of the minute); read as-of
# Rows keep the store's start-of-minute time; the close is usable at the end of that minute, 60 s later
# (the lead's answer of 2026-10-02: no shifting of the stored times, the lag is declared instead).
LAG_NS = 60 * NS


class YenPremiumRevert:
    """The card (module docstring). `window` is "1h", "1d" or "1w"."""

    def __init__(self, window: str) -> None:
        if window not in WINDOWS:
            raise ValueError(f"window must be one of {sorted(WINDOWS)} (W1 spec C4), got {window!r}")
        self.window = window
        self.window_ns = WINDOWS[window]
        self.name = f"c3_yen_premium_revert_{window}"
        self.requires = (SeriesSpec(OVERSEAS, LAG_NS), SeriesSpec(FX, LAG_NS))
        self._times: deque = deque()  # times of the premiums in the window, oldest first
        self._values: deque = deque()  # the premiums, in the same order
        self._sorted: list = []  # the same premiums, sorted
        self._first_ns = None  # time of the first premium the card formed

    def premium(self, view: CardView):
        """p_t, or None when Binance has no row for the minute ending at t (stamped t - 60 s) or no USDJPY
        row is available yet."""
        t = view.now_ns
        bar = view.bars(1)[0]
        if int(bar.exchange_time_ns) != t:
            raise ValueError(f"{self.name} at t={t}: the newest bar ends at {bar.exchange_time_ns}, not at t "
                             f"(the card is called at the end of the bar it prices)")
        try:
            ov = view.ref_at(OVERSEAS, t - LAG_NS)  # the row of the minute [t - 60 s, t)
        except KeyError:
            return None
        latest = view.ref_latest(FX)  # as-of: the newest USDJPY row available at t (row time <= t - 60 s)
        if latest is None:
            return None
        fx = latest[1]
        bf = float(bar.close)
        if not (bf > 0 and ov > 0 and fx > 0):
            raise ValueError(f"{self.name} at t={t}: a non-positive price (bitFlyer {bf}, {OVERSEAS} {ov}, "
                             f"{FX} {fx})")
        return math.log(bf) - math.log(ov) - math.log(fx)

    def _expire(self, t: int) -> None:
        lo = t - self.window_ns
        while self._times and self._times[0] <= lo:
            self._times.popleft()
            v = self._values.popleft()
            del self._sorted[bisect.bisect_left(self._sorted, v)]

    def exposure(self, view: CardView) -> float:
        t = view.now_ns
        p = self.premium(view)
        if p is None:
            return 0.0
        self._expire(t)
        if self._first_ns is None:
            self._first_ns = t
        n = len(self._sorted)
        e = 0.0
        if n > 0 and t - self._first_ns >= self.window_ns:
            below = bisect.bisect_left(self._sorted, p)
            equal = bisect.bisect_right(self._sorted, p) - below
            q = (below + 0.5 * equal) / n
            e = 1.0 - 2.0 * q
        self._times.append(t)
        self._values.append(p)
        bisect.insort(self._sorted, p)
        return e


__all__ = ["FX", "LAG_NS", "OVERSEAS", "WINDOWS", "YenPremiumRevert"]

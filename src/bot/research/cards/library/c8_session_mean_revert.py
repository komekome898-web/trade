"""Card 8 of W4: mean reversion within a session (セッション内平均回帰), held on bitFlyer FX_BTC_JPY.

Source text and intent map: docs/RESEARCH/cards/c8_session_mean_revert/ (CARD.md, INTENT_MAP.md). Source idea:
docs/STRATEGY_IDEAS.md #49 「セッション内の価格が平均的な水準へ回帰する性質を利用できるか。」

The source names no session, no average and no holding rule. bitFlyer FX_BTC_JPY trades around the clock, so a
"session" is fixed by a clock, and the clock is the only choice; it is a named variant with no default
(`session`):

  "jst_day":  the Asia/Tokyo calendar day, 00:00 JST (15:00 UTC) to the next 00:00 JST. The measurement's own
              day_zone (W4 spec section 3); no new number.
  "bf_maint": the day between bitFlyer's daily maintenance starts, 19:00 UTC (04:00 JST) to the next 19:00 UTC.
              19:00 UTC is not the card's number: it is the store README's documented maintenance window
              (「19:00-19:10 UTC」) and the gap catalog's cluster of gaps around it (CARD.md 水準とその出所).

A bar [s, s + 60 s) belongs to the session holding s = t - 60 s, where t is the bar's end (the time the card is
called). The session's level is the running mean of the closes of the bars the card was called on in this
session, up to and including the bar ending at t (the arithmetic mean of the price, 「平均的な水準」; INTENT_MAP.md
I-3, a proxy). The card holds against the deviation (「回帰する」):

  exposure = -sign(close_t - mean_t)      (+1 below the mean, -1 above it, 0 at it)

except at the last bar of a session: if t is exactly the session's end, the exposure is 0, because a position
taken at t fills at the next bar's open (W1 spec C2), which lies in the next session (「セッション内」). The first
bar of a session has mean == its close, so it gives 0. Only the sign: the source gives no strength (A-12).

The card reads only `view.bars(1)` and `view.now_ns`; it requires no reference series (`requires = ()`). It never
names a later bar. Same input, same output (no random numbers; the running sum adds the closes in time order. If the prices
are whole yen the sum is exact while it stays below 2**53; that the store's closes are whole yen is NOT
verified this round (the schema gives only the unit JPY; INTENT_MAP.md C-11)).
"""
from __future__ import annotations

import math

from bot.research.cards.card import CardError, CardView

NS = 1_000_000_000
BAR_NS = 60 * NS  # the 1-minute bar of the store (README: `ts` = start of the 1-minute bucket)
DAY_NS = 86_400 * NS
# Offset added to a UTC time so that the session start falls on a multiple of DAY_NS.
#   jst_day : 00:00 JST = 15:00 UTC -> +9 h (Asia/Tokyo = UTC + 9 h, no daylight saving)
#   bf_maint: 19:00 UTC (bitFlyer maintenance start, store README) -> +5 h
SESSIONS = {
    "jst_day": 9 * 3_600 * NS,
    "bf_maint": 5 * 3_600 * NS,
}


def session_index(t_ns: int, offset_ns: int) -> int:
    """Index of the session holding time t (sessions are [k * DAY - offset, (k + 1) * DAY - offset))."""
    return (t_ns + offset_ns) // DAY_NS


def _sign(x: float) -> float:
    if x > 0.0:
        return 1.0
    if x < 0.0:
        return -1.0
    return 0.0


class SessionMeanRevert:
    """The card (module docstring). `session` is one of "jst_day", "bf_maint", no default."""

    requires = ()

    def __init__(self, session: str) -> None:
        if type(session) is not str or session not in SESSIONS:
            raise CardError(f"c8_session_mean_revert: session must be one of {list(SESSIONS)}: {session!r}")
        self.session = session
        self.name = f"c8_session_mean_revert_{session}"
        self._offset = SESSIONS[session]
        self._session = None  # index of the current session
        self._sum = 0.0  # sum of the closes of the bars of the current session the card was called on
        self._n = 0  # number of those bars

    def exposure(self, view: CardView) -> float:
        t = view.now_ns
        bar = view.bars(1)[0]
        if int(bar.exchange_time_ns) != t:
            raise ValueError(f"{self.name} at t={t}: the newest bar ends at {bar.exchange_time_ns}, not at t "
                             f"(the card is called at the end of the bar it reads)")
        close = float(bar.close)
        if not (close > 0.0 and math.isfinite(close)):
            raise ValueError(f"{self.name} at t={t}: close must be a finite positive price, got {close!r}")
        k = session_index(t - BAR_NS, self._offset)  # the session of the bar [t - 60 s, t)
        if k != self._session:  # a new session: the level starts again from this bar
            self._session = k
            self._sum, self._n = 0.0, 0
        self._sum += close
        self._n += 1
        if (t + self._offset) % DAY_NS == 0:  # the bar ends at the session's end: do not carry into the next one
            return 0.0
        mean = self._sum / self._n
        return -_sign(close - mean)


__all__ = ["BAR_NS", "SESSIONS", "SessionMeanRevert", "session_index"]

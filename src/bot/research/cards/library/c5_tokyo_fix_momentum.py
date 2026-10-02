"""Card 5 of W4: momentum before the Tokyo fix (東京仲値・前モメンタム), held on bitFlyer FX_BTC_JPY.

Source text and intent map: docs/RESEARCH/cards/c5_tokyo_fix_momentum/
(CARD.md, INTENT_MAP.md). Source idea: docs/STRATEGY_IDEAS.md #46
「仲値決定前の値動きに追随する順張りが機能するか」, placed by the lead under the
row 「時間帯・参加者」 of plan v5 stage 3-B and moved from the yen market to
bitFlyer FX_BTC_JPY (INTENT_MAP.md I-4, a proxy).

Clock (Asia/Tokyo = UTC + 9 hours, no daylight saving): the Tokyo fix
(仲値) is set at 09:55 JST on business days (CARD.md 水準とその出所). For a
bar ending at t (start s = t - 1 min), let d be the JST date of s, D0 the JST
00:00 of d and F = D0 + 9 h 55 min.

At the end t of each non-empty bitFlyer FX_BTC_JPY 1-minute bar:

  1. The holding interval is D0 < t < F on a JST weekday (Monday to
     Friday of d). Outside it the card holds 0. So the last bar held is the
     one ending one minute before the fix; the bar ending at F returns 0,
     which the measurement fills at the open of the next bar (W1 spec C2),
     i.e. at the fix.
  2. The anchor is the open of the first bar the card is called on whose
     start lies in the JST date d (normally the bar starting at D0; when
     that minute has no trade, the first later bar with one).
  3. The move before the fix so far is m = close_t - anchor.
     exposure = +1 if m > 0, -1 if m < 0, 0 if m == 0 (follow the move;
     the source gives no size, so only its sign is used: no number, A-12).

The card reads only `view.bars(1)` and `view.now_ns`; it requires no
reference series (`requires = ()`). It never names a later bar. Same input,
same output (no random numbers). Japanese public holidays are not removed
(the card has no holiday calendar; INTENT_MAP.md I-1c, a gap).
"""
from __future__ import annotations

from bot.research.cards.card import CardView

NS = 1_000_000_000
JST_OFFSET_NS = 9 * 3_600 * NS  # Asia/Tokyo = UTC + 9 h, no daylight saving
DAY_NS = 86_400 * NS
# The time of the Tokyo fix in JST (CARD.md 水準とその出所): 09:55, the definition of 仲値決定, not a tuned value.
FIX_TOD_NS = (9 * 3_600 + 55 * 60) * NS


def jst_day_index(t_ns: int) -> int:
    """Days since 1970-01-01 (JST) of the JST date of t."""
    return (t_ns + JST_OFFSET_NS) // DAY_NS


def jst_weekday(day_index: int) -> int:
    """Monday = 0 .. Sunday = 6 (1970-01-01 was a Thursday)."""
    return (day_index + 3) % 7


class TokyoFixMomentum:
    """The card (module docstring). No arguments: nothing to choose."""

    name = "c5_tokyo_fix_momentum"
    requires = ()

    def __init__(self) -> None:
        self._day = None  # JST day index of the anchor
        self._anchor = None  # open of the first called bar of that JST date

    def exposure(self, view: CardView) -> float:
        t = view.now_ns
        bar = view.bars(1)[0]
        if int(bar.exchange_time_ns) != t:
            raise ValueError(f"{self.name} at t={t}: the newest bar ends at {bar.exchange_time_ns}, not at t "
                             f"(the card is called at the end of the bar it reads)")
        s = int(bar.start_time_ns)
        day = jst_day_index(s)
        if day != self._day:  # the first called bar of this JST date gives the anchor
            self._day = day
            self._anchor = float(bar.open)
        d0 = day * DAY_NS - JST_OFFSET_NS  # JST 00:00 of the date, in UTC ns
        if jst_weekday(day) >= 5:
            return 0.0
        if not (d0 < t < d0 + FIX_TOD_NS):
            return 0.0
        m = float(bar.close) - self._anchor
        if m > 0:
            return 1.0
        if m < 0:
            return -1.0
        return 0.0


__all__ = ["FIX_TOD_NS", "JST_OFFSET_NS", "TokyoFixMomentum", "jst_day_index", "jst_weekday"]

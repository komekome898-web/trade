"""Card 6 of W4: the one-hour mean reversion of the weekend gap (週末ギャップの1時間平均回帰), held on bitFlyer
FX_BTC_JPY.

Source text and intent map: docs/RESEARCH/cards/c6_weekend_gap_revert/ (CARD.md, INTENT_MAP.md). Source idea:
docs/STRATEGY_IDEAS.md #45 「週明けの価格ギャップが、最初の1時間で平均的に縮小(回帰)する性質を利用できるか。」

The source names no market. bitFlyer FX_BTC_JPY trades through the weekend (it has no weekly closure), so a
"week-open price gap" exists only against a market that closes over the weekend. The only such series in hand
over the measured period is USDJPY (Dukascopy 1-minute BID), so the FX week defines the weekend here
(INTENT_MAP.md I-1, a proxy). What the gap measures is not fixed by the source; it is a named variant:

  "usdjpy": the gap of USDJPY itself across the closure (it enters FX_BTC_JPY through the identity
            FX_BTC_JPY = BTCUSD x USDJPY x (1 + yen premium)):
                g = ln(USDJPY close of the week-open row) - ln(USDJPY close of the last row of the earlier week)
  "btc":    the move of FX_BTC_JPY over the same closure:
                g = ln(bitFlyer close as of the end of the week-open row)
                    - ln(bitFlyer close as of the end of the last earlier-week USDJPY row whose close differed
                         from the row before it, i.e. the last quote change before the closure)

The FX week (CARD.md 水準とその出所): rows are grouped by their Asia/Tokyo week (Monday 00:00 JST start, the
measurement's day_zone). The FX market is shut at Monday 00:00 JST (Sunday 15:00 UTC), so no live quoting runs
across a JST week boundary. The store may hold flat rows while the market is shut (its Sunday day files have
rows; CARD.md 使うデータと遅れ), so the week-open row is the FIRST row of a later JST week whose close differs
from the last close of the earlier week, not merely the first row of the later week. r = that row's time
(the start of its minute).

At the end t of each non-empty bitFlyer FX_BTC_JPY 1-minute bar, the card first reads the USDJPY rows delivered
since its last call (in time order) and updates the state above, then:

  exposure = -sign(g) if a week-open row r is known and r + 60 s <= t < r + 3600 s, else 0
             (0 also when g == 0 or g is undefined).

-sign(g): the gap shrinks (「縮小(回帰)」), so hold against it. Only the sign: the source gives no size (A-12).
The bar ending t fills at the open of the next bar (W1 spec C2), so the holding covers (r + 60 s, r + 3600 s]:
the first hour after the week opens, less its first minute (the row of minute r becomes available only at
r + 60 s). 1 hour is the source's 「最初の1時間」.

Reference series (CARD.md 測定の設定): each USDJPY row keeps the store's own time, the START of its minute
(Dukascopy `timestamp`, not shifted); declared lag 60 s, so the row of the minute ending at t becomes available
at t and not before. The card reads only `view.bars(1)`, `view.now_ns` and `view.ref(FX)` (the rows delivered by
t); it never names a row that is not yet available. Same input, same output (no random numbers).
"""
from __future__ import annotations

import math

from bot.research.cards.card import CardView, SeriesSpec

NS = 1_000_000_000
JST_OFFSET_NS = 9 * 3_600 * NS  # Asia/Tokyo = UTC + 9 h, no daylight saving (the measurement's day_zone)
DAY_NS = 86_400 * NS
HOLD_NS = 3_600 * NS  # the source's 「最初の1時間」, not a tuned value

FX = "usdjpy_close"  # USDJPY 1m BID close (Dukascopy), row time = timestamp (start of the minute)
LAG_NS = 60 * NS  # the close of a minute is usable at its end (the lead's answer of 2026-10-02)
GAPS = ("usdjpy", "btc")


def jst_week_index(t_ns: int) -> int:
    """Weeks since the JST week holding 1970-01-01, weeks starting Monday 00:00 JST (1970-01-01 was a
    Thursday, so day d has weekday (d + 3) % 7 with Monday = 0)."""
    day = (t_ns + JST_OFFSET_NS) // DAY_NS
    return (day + 3) // 7


def _sign(x: float) -> float:
    if x > 0:
        return 1.0
    if x < 0:
        return -1.0
    return 0.0


class WeekendGapRevert:
    """The card (module docstring). `gap` is "usdjpy" or "btc"."""

    def __init__(self, gap: str) -> None:
        if gap not in GAPS:
            raise ValueError(f"gap must be one of {GAPS}, got {gap!r}")
        self.gap = gap
        self.name = f"c6_weekend_gap_revert_{gap}"
        self.requires = (SeriesSpec(FX, LAG_NS),)
        self._seen = 0  # USDJPY rows read so far
        self._week = None  # JST week of the newest row read
        self._close = None  # close of the newest row read
        self._bf_at_move = None  # bitFlyer close as of the end of the newest row whose close changed
        self._armed = False  # a later week started and its open row is not found yet
        self._ref_fx = None  # last USDJPY close of the earlier week
        self._ref_bf = None  # bitFlyer close as of the end of the earlier week's last quote change
        self._open_ns = None  # r: time of the newest week-open row
        self._g = None  # the gap of that week open (variant's definition); None if undefined
        self._prev_bf = None  # close of the previous bar the card was called on

    def _bf_asof(self, x_ns: int, t: int, bf_now: float):
        """bitFlyer close as of time x, for a row that became available in (previous call, t]: the bar ending
        at t if x == t, else the bar of the previous call (the bars in between had no trade)."""
        if x_ns == t:
            return bf_now
        return self._prev_bf

    def _read_rows(self, view: CardView, t: int, bf_now: float) -> None:
        rows = view.ref(FX)
        for i in range(self._seen, len(rows)):
            row_t, close = rows[i]
            row_t = int(row_t)
            close = float(close)
            if not close > 0:
                raise ValueError(f"{self.name} at t={t}: a non-positive {FX} close {close} at {row_t}")
            week = jst_week_index(row_t)
            if self._week is not None and week > self._week:  # a later JST week starts: the closure lies behind
                self._armed = True
                self._ref_fx = self._close
                self._ref_bf = self._bf_at_move
            if self._close is not None and close != self._close:
                bf = self._bf_asof(row_t + LAG_NS, t, bf_now)
                if self._armed:  # the week-open row: the first later-week quote off the earlier week's last close
                    self._armed = False
                    self._open_ns = row_t
                    if self.gap == "usdjpy":
                        self._g = math.log(close) - math.log(self._ref_fx)
                    elif bf is None or self._ref_bf is None:
                        self._g = None
                    else:
                        self._g = math.log(bf) - math.log(self._ref_bf)
                self._bf_at_move = bf
            self._week = week
            self._close = close
        self._seen = len(rows)

    def exposure(self, view: CardView) -> float:
        t = view.now_ns
        bar = view.bars(1)[0]
        if int(bar.exchange_time_ns) != t:
            raise ValueError(f"{self.name} at t={t}: the newest bar ends at {bar.exchange_time_ns}, not at t "
                             f"(the card is called at the end of the bar it reads)")
        bf_now = float(bar.close)
        if not bf_now > 0:
            raise ValueError(f"{self.name} at t={t}: a non-positive bitFlyer close {bf_now}")
        self._read_rows(view, t, bf_now)
        self._prev_bf = bf_now
        r = self._open_ns
        if r is None or self._g is None:
            return 0.0
        if r + LAG_NS <= t < r + HOLD_NS:
            return -_sign(self._g)
        return 0.0


__all__ = ["FX", "GAPS", "HOLD_NS", "LAG_NS", "WeekendGapRevert", "jst_week_index"]

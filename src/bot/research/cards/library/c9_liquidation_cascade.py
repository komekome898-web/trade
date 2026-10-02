"""Card c9 of W4: the liquidation cascade (清算の連鎖).

Source text and intent map: docs/RESEARCH/cards/c9_liquidation_cascade/ (CARD.md, INTENT_MAP.md).
Sources: plan v5 stage 3-B, row 「清算の連鎖」 (海外の清算の直後の bitFlyer の動き), and
docs/STRATEGY_IDEAS.md O-3c (the owner's: observe the forced-liquidation flow itself instead of its proxy,
the wick, to judge "the fuel has run out").

Inputs, read at the end t of each non-empty bitFlyer FX_BTC_JPY 1-minute bar:

  - BUY = "binance_cm_liq_buy_qty": per UTC minute, the quantity of the Binance COIN-M BTCUSD_PERP forced
    orders with side BUY (shorts liquidated, forced buying) in that minute; SELL = "binance_cm_liq_sell_qty":
    the same with side SELL (longs liquidated, forced selling). Each row's time is the START of its minute and
    the value is usable at its end: declared lag 60 s, so the row of the minute that ends at t is read as
    view.ref_at(name, t - 60 s). A minute with no liquidation has a row with 0 (the builder writes one for
    every minute of a day whose file exists); a minute with no row is UNKNOWN (a day missing from the store).

What the card does (CARD.md, INTENT_MAP.md):

  1. It walks every minute from the one after the last minute it processed up to the minute ending at t
     (so a liquidation minute that falls inside a gap of the bitFlyer bars is not skipped).
  2. A chain (連鎖) is a run of consecutive minutes each with liquidations (BUY + SELL > 0). Its push is
     sign(sum over the chain of (BUY - SELL)): +1 = the forced flow bought (pushed the price up), -1 = sold.
  3. The chain ends at the end of the first minute without liquidations ("the fuel has run out").
  4. mode "ride"  : while a chain runs, hold +push; after its last liquidation minute keep it for `hold`.
     mode "fade"  : from the end of a chain, hold -push for `hold`; nothing while a chain runs.
     mode "ride_fade": +push while a chain runs, -push from its end for `hold` (the owner's L-262 sentence
                   「続くなら乗る、続かないなら逆張り」, with "continues" read as "this minute had liquidations").
     A tie (push 0) holds 0. Size is +-1 (the sources give no strength for a liquidation, A-12).
  5. A minute with no row (unknown) clears the chain and every hold; the card holds 0 until it sees
     liquidations again.

`mode` and `hold` have no default. `hold` is the one bar ("1m") or one of the windows of W1 spec C4
(1 hour, 1 day, 1 week); no other value is accepted. Same input, same output (no random numbers). The card
never names a row that is not yet available at t.
"""
from __future__ import annotations

from typing import Optional

from bot.research.cards.card import CardView, SeriesSpec

NS = 1_000_000_000
MINUTE_NS = 60 * NS
# "1m" = only the bar that follows the decision (the minimal reading of 直後); the rest are W1 spec C4's windows.
HOLDS = {"1m": MINUTE_NS, "1h": 3_600 * NS, "1d": 86_400 * NS, "1w": 7 * 86_400 * NS}
MODES = ("ride", "fade", "ride_fade")

BUY = "binance_cm_liq_buy_qty"  # forced BUY orders (short positions liquidated), per minute, row time = minute start
SELL = "binance_cm_liq_sell_qty"  # forced SELL orders (long positions liquidated), same layout
LAG_NS = 60 * NS  # a minute's row is usable at the end of that minute (row time + 60 s)


def _sign(x: float) -> int:
    return 1 if x > 0 else (-1 if x < 0 else 0)


class LiquidationCascade:
    """The card (module docstring). `mode` in MODES, `hold` in HOLDS."""

    def __init__(self, mode: str, hold: str) -> None:
        if mode not in MODES:
            raise ValueError(f"mode must be one of {list(MODES)}, got {mode!r}")
        if hold not in HOLDS:
            raise ValueError(f"hold must be one of {sorted(HOLDS)} (one bar or W1 spec C4), got {hold!r}")
        self.mode = mode
        self.hold = hold
        self.hold_ns = HOLDS[hold]
        self.name = f"c9_liquidation_cascade_{mode}_{hold}"
        self.requires = (SeriesSpec(BUY, LAG_NS), SeriesSpec(SELL, LAG_NS))
        self._next_row: Optional[int] = None  # row time (minute start) of the next minute to process
        self._chain_net: Optional[float] = None  # sum of BUY - SELL over the running chain; None = no chain
        self._ride_sign = 0  # push of the latest chain minute
        self._ride_t: Optional[int] = None  # end time of the latest chain minute
        self._fade_sign = 0  # -push of the latest ended chain
        self._fade_t: Optional[int] = None  # end time of the first quiet minute (the chain's end)

    def _reset(self) -> None:
        self._chain_net = None
        self._ride_sign, self._ride_t = 0, None
        self._fade_sign, self._fade_t = 0, None

    def _minute(self, view: CardView, row_t: int) -> None:
        """Process the minute [row_t, row_t + 60 s); its end is row_t + 60 s <= now."""
        end = row_t + MINUTE_NS
        try:
            b = view.ref_at(BUY, row_t)
            s = view.ref_at(SELL, row_t)
        except KeyError:
            self._reset()  # unknown minute (no row): no chain can be said to run or to have ended
            return
        if not (b >= 0 and s >= 0):
            raise ValueError(f"{self.name}: a negative or NaN liquidation quantity at {row_t} ({BUY} {b}, "
                             f"{SELL} {s})")
        if b + s > 0:  # the chain runs (or starts) in this minute
            self._chain_net = (self._chain_net or 0.0) + (b - s)
            self._ride_sign, self._ride_t = _sign(self._chain_net), end
            # a new chain ends the hold after the previous one: exposure() looks at `running` before the fade
        elif self._chain_net is not None:  # first minute without liquidations: the chain has ended
            self._fade_sign, self._fade_t = -_sign(self._chain_net), end
            self._chain_net = None

    def exposure(self, view: CardView) -> float:
        t = view.now_ns
        bar = view.bars(1)[0]
        if int(bar.exchange_time_ns) != t:
            raise ValueError(f"{self.name} at t={t}: the newest bar ends at {bar.exchange_time_ns}, not at t")
        last_row = t - MINUTE_NS  # the minute that ends at t
        row = last_row if self._next_row is None else self._next_row
        while row <= last_row:
            self._minute(view, row)
            row += MINUTE_NS
        self._next_row = max(row, last_row + MINUTE_NS)

        running = self._chain_net is not None
        if self.mode == "ride":
            if self._ride_t is not None and (running or t - self._ride_t < self.hold_ns):
                return float(self._ride_sign)
            return 0.0
        if running:
            return float(self._ride_sign) if self.mode == "ride_fade" else 0.0
        if self._fade_t is not None and t - self._fade_t < self.hold_ns:
            return float(self._fade_sign)
        return 0.0


__all__ = ["BUY", "HOLDS", "LAG_NS", "LiquidationCascade", "MODES", "SELL"]

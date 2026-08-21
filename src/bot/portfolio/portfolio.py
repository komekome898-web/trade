"""Position, PnL, drawdown and consecutive-loss tracking.

Two figures are measured from an ANCHOR rather than from the position's entry
price, and both anchors are set at the first mark price this process sees:

* today's unrealized contribution to the daily P&L (`daily_mark_price`), and
* the equity peak the drawdown is measured from (`equity_peak_jpy`).

For a position opened by this process today the anchor IS the entry price, so
nothing about a same-day trade changes. It matters for a position that was
already open when the day (or the process) started: its unrealized loss was
incurred BEFORE today, and counting all of it into today's daily P&L — or
against a peak that pretends the loss is not there — trips MAX_DAILY_LOSS /
MAX_DRAWDOWN at boot, before the protective stop can close the position. An
operator reset then boots into the same trip: a deadlock no reset clears.
Both brakes therefore measure deterioration SINCE the anchor, the same
philosophy as the risk overlay's relative drawdown.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field


@dataclass
class TradeRecord:
    timestamp: float
    symbol: str
    side: str
    size: float
    price: float
    fee_jpy: float
    realized_pnl_jpy: float


@dataclass
class Portfolio:
    initial_equity_jpy: float
    clock: object = time.time
    position_size: float = 0.0
    avg_entry_price: float = 0.0
    realized_pnl_jpy: float = 0.0
    fees_paid_jpy: float = 0.0
    equity_peak_jpy: float = 0.0
    consecutive_losses: int = 0
    trades: list[TradeRecord] = field(default_factory=list)
    _daily_realized: float = 0.0
    _daily_anchor_day: int = -1
    # None = "the entry price", i.e. a position this process opened inside the
    # current day. A restored or carried-over position gets the first mark
    # price observed instead (see the module docstring).
    _daily_mark_price: float | None = None
    _daily_mark_pending: bool = False      # re-anchor at the next mark seen
    _equity_peak_pending: bool = False     # ditto for the peak

    def __post_init__(self):
        self.equity_peak_jpy = self.initial_equity_jpy

    def _roll_day(self) -> None:
        day = int(self.clock() // 86400)
        if day != self._daily_anchor_day:
            self._daily_anchor_day = day
            self._daily_realized = 0.0
            # A position held across midnight starts the new day flat: today's
            # unrealized is measured from the ROLLOVER mark, not from an entry
            # price that may be days old.
            if self.position_size != 0.0:
                self._daily_mark_pending = True

    @property
    def daily_day_index(self) -> int:
        """UTC day the daily P&L is currently anchored to (rolls it first).

        The one clock for "which trading day is it": callers that need to react
        to a rollover (bot/main.py persists the reset) read it from here rather
        than running a second clock that could disagree with this one."""
        self._roll_day()
        return self._daily_anchor_day

    @property
    def daily_realized_jpy(self) -> float:
        """Realized P&L booked today. `daily_pnl_jpy` adds unrealized on top;
        only the realized part is meaningful to persist."""
        self._roll_day()
        return self._daily_realized

    def daily_snapshot(self) -> tuple[int, float]:
        """(UTC day index, realized P&L booked in it) from ONE clock read.

        The persisted daily figure and the date labelling it must come from the
        same read: the caller used to take the figure and then ask the clock
        again for the date, and a rollover in between labelled yesterday's
        spent budget with today's date — a safety brake wedged for a whole
        fresh day (bot/portfolio/persistence.py)."""
        self._roll_day()
        return self._daily_anchor_day, self._daily_realized

    def seed_daily_realized(self, realized_jpy: float, *, day: int) -> None:
        """Restore today's realized P&L after a paper restart.

        `day` is the day index the caller decided the figure belongs to (from
        `daily_day_index`). It is re-checked here against the same clock, so a
        rollover between the caller's read and this call can only DROP the
        figure (the new day legitimately starts at 0), never book it into the
        wrong day."""
        if self.daily_day_index != day:
            return
        self._daily_realized = float(realized_jpy)

    def anchor_boot_equity(self) -> None:
        """Re-anchor the drawdown peak (and the daily mark) at what this
        process actually starts from — called after a restored book is loaded
        into the portfolio (bot/main.py `_restore_paper_state`).

        With no open position that is `initial + realized` and is exact right
        away. With one, the mark-to-market boot equity needs a price this early
        in the boot there is none of, so both anchors are marked PENDING and
        settle on the first mark observed. Until then the peak stays at the
        cash figure, which can only over-state equity, i.e. report a drawdown
        that is too large — the safe direction for a brake."""
        self.equity_peak_jpy = self.initial_equity_jpy + self.realized_pnl_jpy
        if self.position_size != 0.0:
            self._equity_peak_pending = True
            self._daily_mark_pending = True

    def observe_mark(self, mark_price: float) -> None:
        """Settle any pending anchor on this mark price. Idempotent, and called
        from every method that is handed a mark, so "the first price observed"
        needs no separate wiring in the trading loop."""
        if not (self._daily_mark_pending or self._equity_peak_pending):
            return
        price = float(mark_price)
        if not math.isfinite(price) or price <= 0:
            return          # not a usable mark; wait for the next one
        if self._daily_mark_pending:
            self._daily_mark_price = price
            self._daily_mark_pending = False
        if self._equity_peak_pending:
            self._equity_peak_pending = False
            # equity_jpy() at this mark, spelled out to avoid recursing back
            # through observe_mark.
            self.equity_peak_jpy = (self.initial_equity_jpy + self.realized_pnl_jpy
                                    + (price - self.avg_entry_price) * self.position_size)

    @property
    def daily_mark_price(self) -> float:
        """The price today's unrealized P&L is measured FROM: the entry price
        for a position opened today, the boot/rollover mark otherwise."""
        return (self.avg_entry_price if self._daily_mark_price is None
                else self._daily_mark_price)

    def _reset_daily_mark(self) -> None:
        """Back to entry-price semantics: used when the book goes flat or opens
        a new position, both of which make any carried anchor meaningless."""
        self._daily_mark_price = None
        self._daily_mark_pending = False

    def on_fill(self, *, symbol: str, side: str, size: float, price: float,
                fee_jpy: float = 0.0) -> float:
        """Record a fill; returns realized PnL of this fill (JPY).

        position_size is signed: > 0 long, < 0 short. A fill against the
        current position closes up to its size first; any remainder opens a
        position in the other direction (net position model)."""
        self._roll_day()
        realized = 0.0
        delta = size if side == "BUY" else -size
        pos = self.position_size
        pos_before = pos
        if pos == 0.0 or (pos > 0) == (delta > 0):
            new_size = pos + delta
            self.avg_entry_price = (
                (self.avg_entry_price * abs(pos) + price * abs(delta)) / abs(new_size)
            )
            self.position_size = new_size
        else:
            closing = min(abs(delta), abs(pos))
            direction = 1.0 if pos > 0 else -1.0
            realized = (price - self.avg_entry_price) * closing * direction
            self.position_size = pos + direction * -closing
            remainder = abs(delta) - closing
            if abs(self.position_size) <= 1e-12:
                self.position_size = 0.0
                self.avg_entry_price = 0.0
            if remainder > 1e-12:
                self.position_size = remainder if delta > 0 else -remainder
                self.avg_entry_price = price
        realized -= fee_jpy
        self.realized_pnl_jpy += realized
        self.fees_paid_jpy += fee_jpy
        self._daily_realized += realized
        if realized + fee_jpy != 0.0:  # a closing fill
            if realized < 0:
                self.consecutive_losses += 1
            elif realized > 0:
                self.consecutive_losses = 0
        # A book that went flat, opened from flat or flipped has no carried
        # anchor to keep: the new position's own entry price is the mark.
        if (self.position_size == 0.0 or pos_before == 0.0
                or (self.position_size > 0) != (pos_before > 0)):
            self._reset_daily_mark()
        self.trades.append(TradeRecord(self.clock(), symbol, side, size, price, fee_jpy, realized))
        return realized

    def unrealized_pnl_jpy(self, mark_price: float) -> float:
        # signed position: a short (negative) gains when mark < entry
        self.observe_mark(mark_price)
        return (mark_price - self.avg_entry_price) * self.position_size

    def equity_jpy(self, mark_price: float) -> float:
        return self.initial_equity_jpy + self.realized_pnl_jpy + self.unrealized_pnl_jpy(mark_price)

    def daily_pnl_jpy(self, mark_price: float) -> float:
        """Realized today + unrealized SINCE `daily_mark_price`.

        The unrealized term is the move since today's anchor, not since the
        entry: a loss carried in from an earlier day is not spent out of
        today's MAX_DAILY_LOSS_JPY budget (it was spent out of that day's).
        An adverse move after the anchor counts in full — the brake keeps
        stopping the day it is meant to stop."""
        self._roll_day()
        self.observe_mark(mark_price)
        return self._daily_realized + (
            (float(mark_price) - self.daily_mark_price) * self.position_size)

    def drawdown_pct(self, mark_price: float) -> float:
        eq = self.equity_jpy(mark_price)
        self.equity_peak_jpy = max(self.equity_peak_jpy, eq)
        if self.equity_peak_jpy <= 0:
            return 100.0
        return max(0.0, (self.equity_peak_jpy - eq) / self.equity_peak_jpy * 100)

    def position_notional_jpy(self, mark_price: float) -> float:
        return abs(self.position_size) * mark_price

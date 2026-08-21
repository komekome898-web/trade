"""Position, PnL, drawdown and consecutive-loss tracking."""
from __future__ import annotations

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

    def __post_init__(self):
        self.equity_peak_jpy = self.initial_equity_jpy

    def _roll_day(self) -> None:
        day = int(self.clock() // 86400)
        if day != self._daily_anchor_day:
            self._daily_anchor_day = day
            self._daily_realized = 0.0

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

    def seed_daily_realized(self, realized_jpy: float) -> None:
        """Restore today's realized P&L after a paper restart.

        Rolls the day FIRST, so a figure handed in for an earlier day cannot be
        booked into today's — the caller checks the date, and this makes the
        clock check unmissable on either side."""
        self._roll_day()
        self._daily_realized = float(realized_jpy)

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
        self.trades.append(TradeRecord(self.clock(), symbol, side, size, price, fee_jpy, realized))
        return realized

    def unrealized_pnl_jpy(self, mark_price: float) -> float:
        # signed position: a short (negative) gains when mark < entry
        return (mark_price - self.avg_entry_price) * self.position_size

    def equity_jpy(self, mark_price: float) -> float:
        return self.initial_equity_jpy + self.realized_pnl_jpy + self.unrealized_pnl_jpy(mark_price)

    def daily_pnl_jpy(self, mark_price: float) -> float:
        self._roll_day()
        return self._daily_realized + self.unrealized_pnl_jpy(mark_price)

    def drawdown_pct(self, mark_price: float) -> float:
        eq = self.equity_jpy(mark_price)
        self.equity_peak_jpy = max(self.equity_peak_jpy, eq)
        if self.equity_peak_jpy <= 0:
            return 100.0
        return max(0.0, (self.equity_peak_jpy - eq) / self.equity_peak_jpy * 100)

    def position_notional_jpy(self, mark_price: float) -> float:
        return abs(self.position_size) * mark_price

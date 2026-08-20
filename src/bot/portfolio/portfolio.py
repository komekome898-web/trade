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

    def on_fill(self, *, symbol: str, side: str, size: float, price: float,
                fee_jpy: float = 0.0) -> float:
        """Record a fill; returns realized PnL of this fill (JPY)."""
        self._roll_day()
        realized = 0.0
        if side == "BUY":
            new_size = self.position_size + size
            if new_size > 0:
                self.avg_entry_price = (
                    (self.avg_entry_price * self.position_size + price * size) / new_size
                )
            self.position_size = new_size
        else:
            closing = min(size, self.position_size)
            realized = (price - self.avg_entry_price) * closing
            self.position_size -= closing
            if self.position_size <= 1e-12:
                self.position_size = 0.0
                self.avg_entry_price = 0.0
        realized -= fee_jpy
        self.realized_pnl_jpy += realized
        self.fees_paid_jpy += fee_jpy
        self._daily_realized += realized
        if side == "SELL":
            if realized < 0:
                self.consecutive_losses += 1
            elif realized > 0:
                self.consecutive_losses = 0
        self.trades.append(TradeRecord(self.clock(), symbol, side, size, price, fee_jpy, realized))
        return realized

    def unrealized_pnl_jpy(self, mark_price: float) -> float:
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
        return self.position_size * mark_price

"""Paper execution: simulates fills against real market quotes.

This module NEVER imports the live executor or calls any order API — the only
exchange dependency is a quote callback supplied by the caller. Fills are
simulated at best ask (BUY) / best bid (SELL) plus configurable slippage,
with taker fees deducted from the virtual JPY balance.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Callable

from bot.execution.gateway import ExecutionGateway, OrderStatus, SubmitResult


@dataclass
class PaperFill:
    acceptance_id: str
    symbol: str
    side: str
    size: float
    price: float
    fee_jpy: float


@dataclass
class PaperExecutor(ExecutionGateway):
    quote_fn: Callable[[str], tuple[float, float]]   # symbol -> (best_bid, best_ask)
    balance_jpy: float = 6000.0
    taker_fee_pct: float = 0.15
    slippage_pct: float = 0.05
    positions: dict[str, float] = field(default_factory=dict)   # symbol -> size
    fills: list[PaperFill] = field(default_factory=list)
    _orders: dict[str, OrderStatus] = field(default_factory=dict)

    def submit_order(self, *, symbol: str, side: str, size: float,
                     order_type: str, price: float | None) -> SubmitResult:
        best_bid, best_ask = self.quote_fn(symbol)
        if side == "BUY":
            fill_price = best_ask * (1 + self.slippage_pct / 100)
        else:
            fill_price = best_bid * (1 - self.slippage_pct / 100)
        # LIMIT orders only fill if the limit is marketable right now (simple model)
        if order_type == "LIMIT" and price is not None:
            if (side == "BUY" and price < fill_price) or (side == "SELL" and price > fill_price):
                acceptance_id = f"PAPER-{uuid.uuid4()}"
                self._orders[acceptance_id] = OrderStatus(acceptance_id, "ACTIVE", 0.0, None)
                return SubmitResult(acceptance_id)
            fill_price = price
        notional = size * fill_price
        fee = notional * self.taker_fee_pct / 100
        if side == "BUY":
            cost = notional + fee
            if cost > self.balance_jpy:
                raise ValueError(f"paper balance insufficient: need {cost:.0f}, have {self.balance_jpy:.0f}")
            self.balance_jpy -= cost
            self.positions[symbol] = self.positions.get(symbol, 0.0) + size
        else:
            held = self.positions.get(symbol, 0.0)
            if size > held + 1e-12:
                raise ValueError(f"paper position insufficient: selling {size}, hold {held}")
            self.balance_jpy += notional - fee
            self.positions[symbol] = held - size
        acceptance_id = f"PAPER-{uuid.uuid4()}"
        self.fills.append(PaperFill(acceptance_id, symbol, side, size, fill_price, fee))
        self._orders[acceptance_id] = OrderStatus(acceptance_id, "COMPLETED", size, fill_price)
        return SubmitResult(acceptance_id)

    def cancel_order(self, *, symbol: str, acceptance_id: str) -> None:
        st = self._orders.get(acceptance_id)
        if st and st.state == "ACTIVE":
            self._orders[acceptance_id] = OrderStatus(acceptance_id, "CANCELED", st.filled_size,
                                                      st.avg_fill_price)

    def fetch_order_status(self, *, symbol: str, acceptance_id: str) -> OrderStatus | None:
        return self._orders.get(acceptance_id)

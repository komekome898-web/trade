"""Pre-trade risk checks. ALL checks must pass or the order is rejected.

The checker also decides when a limit breach must trip the kill switch
(daily loss, drawdown, consecutive losses) versus merely reject the order.
"""
from __future__ import annotations

from dataclasses import dataclass

from bot.risk.kill_switch import KillReason, KillSwitch
from bot.settings import RiskLimits


@dataclass
class AccountState:
    """Snapshot the caller must assemble from portfolio + exchange before ordering."""
    balance_jpy: float
    position_notional_jpy: float
    open_orders: int
    daily_pnl_jpy: float          # realized + unrealized, today
    drawdown_pct: float           # from equity peak
    consecutive_losses: int
    position_size: float = 0.0    # signed: > 0 long, < 0 short


@dataclass
class OrderRequest:
    symbol: str
    side: str                     # BUY / SELL
    size: float                   # asset units
    price: float                  # expected fill price (JPY)
    stop_price: float | None = None

    @property
    def notional_jpy(self) -> float:
        return self.size * self.price

    @property
    def estimated_loss_jpy(self) -> float:
        if self.stop_price is None:
            return self.notional_jpy  # worst case if no stop defined
        return abs(self.price - self.stop_price) * self.size


@dataclass
class RiskDecision:
    approved: bool
    reasons: list[str]


class PreTradeChecker:
    def __init__(self, limits: RiskLimits, kill_switch: KillSwitch, product=None):
        self.limits = limits
        self.kill_switch = kill_switch
        self.product = product        # optional bot.products.ProductSpec

    def check(self, order: OrderRequest, account: AccountState) -> RiskDecision:
        reasons: list[str] = []

        # Kill-switch-tripping conditions first (these stop the bot entirely)
        if account.daily_pnl_jpy <= -self.limits.max_daily_loss_jpy:
            self.kill_switch.trip(
                KillReason.DAILY_LOSS_LIMIT,
                f"daily pnl {account.daily_pnl_jpy:.0f} <= -{self.limits.max_daily_loss_jpy}",
            )
            reasons.append("daily loss limit reached (kill switch tripped)")
        if account.drawdown_pct >= self.limits.max_drawdown_pct:
            self.kill_switch.trip(
                KillReason.MAX_DRAWDOWN,
                f"drawdown {account.drawdown_pct:.2f}% >= {self.limits.max_drawdown_pct}%",
            )
            reasons.append("max drawdown reached (kill switch tripped)")
        if account.consecutive_losses >= self.limits.max_consecutive_losses:
            self.kill_switch.trip(
                KillReason.CONSECUTIVE_LOSSES,
                f"{account.consecutive_losses} consecutive losses",
            )
            reasons.append("max consecutive losses reached (kill switch tripped)")

        if self.kill_switch.is_tripped:
            reasons.append(f"kill switch active: {self.kill_switch.state}")
            return RiskDecision(False, reasons)

        # Order-level checks
        if order.size <= 0 or order.price <= 0:
            reasons.append(f"invalid order size/price: {order.size}/{order.price}")
        if order.side not in ("BUY", "SELL"):
            reasons.append(f"invalid side: {order.side}")
        # exposure grows when the order is in the direction of (or opens) the position
        increases_exposure = (
            (order.side == "BUY" and account.position_size >= 0)
            or (order.side == "SELL" and account.position_size <= 0)
        )
        # MAX_ORDER_SIZE caps risk-increasing orders only: a closing order must
        # never be blocked, or a position opened at the cap becomes un-exitable
        # after an adverse move (the stop-loss itself would be refused).
        if increases_exposure and order.notional_jpy > self.limits.max_order_size_jpy:
            reasons.append(
                f"order notional {order.notional_jpy:.0f} > MAX_ORDER_SIZE {self.limits.max_order_size_jpy:.0f}"
            )
        # Like MAX_ORDER_SIZE, the position cap binds only when exposure grows:
        # an adverse move can push an existing position's marked notional past
        # the cap, and the closing order must still go through.
        new_position = account.position_notional_jpy + order.notional_jpy
        if increases_exposure and new_position > self.limits.max_position_size_jpy:
            reasons.append(
                f"position notional {new_position:.0f} > MAX_POSITION_SIZE {self.limits.max_position_size_jpy:.0f}"
            )
        if account.open_orders >= self.limits.max_open_orders:
            reasons.append(
                f"open orders {account.open_orders} >= MAX_OPEN_ORDERS {self.limits.max_open_orders}"
            )
        if self.product is not None:
            if order.size < self.product.min_size:
                reasons.append(
                    f"size {order.size} below product minimum {self.product.min_size}"
                )
            if (order.side == "SELL" and account.position_size <= 0
                    and not self.product.shortable):
                reasons.append(f"{order.symbol} is not shortable (spot)")
            if self.product.is_margin:
                if increases_exposure and new_position > account.balance_jpy * self.product.leverage:
                    reasons.append(
                        f"margin exceeded: notional {new_position:.0f} > "
                        f"{account.balance_jpy:.0f} x{self.product.leverage}"
                    )
            elif order.side == "BUY" and order.notional_jpy > account.balance_jpy:
                reasons.append(
                    f"insufficient balance: need {order.notional_jpy:.0f}, have {account.balance_jpy:.0f}"
                )
        elif order.side == "BUY" and order.notional_jpy > account.balance_jpy:
            reasons.append(
                f"insufficient balance: need {order.notional_jpy:.0f}, have {account.balance_jpy:.0f}"
            )
        remaining_daily_budget = self.limits.max_daily_loss_jpy + min(account.daily_pnl_jpy, 0.0)
        if order.estimated_loss_jpy > remaining_daily_budget:
            reasons.append(
                f"estimated loss {order.estimated_loss_jpy:.0f} exceeds remaining daily risk budget "
                f"{remaining_daily_budget:.0f}"
            )

        return RiskDecision(approved=not reasons, reasons=reasons)

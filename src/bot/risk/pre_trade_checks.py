"""Pre-trade risk checks. ALL checks must pass or the order is rejected.

The checker also decides when a limit breach must trip the kill switch
(daily loss, drawdown, consecutive losses) versus merely reject the order.
"""
from __future__ import annotations

from dataclasses import dataclass

from bot.risk.kill_switch import KillReason, KillSwitch
from bot.settings import RiskLimits

# Below this a leftover size is float noise on a close, not new exposure.
_SIZE_EPSILON = 1e-12


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
        # THE REDUCING EXEMPTION, and its bound. A closing order must never be
        # refused by a cap — a position opened at the cap would become
        # un-exitable after an adverse move, because the stop-loss itself would
        # be refused. But only the part of the order that actually REDUCES the
        # position is closing: a SELL of 1.0 against a 0.001 long closes 0.001
        # and OPENS 0.999 short, and exempting the whole order because "it is a
        # sell and we are long" let an order a thousand times the cap through
        # as if it were protective. So the caps are evaluated on the EXCESS.
        reducible = (max(0.0, -account.position_size) if order.side == "BUY"
                     else max(0.0, account.position_size))
        reduced_size = min(order.size, reducible)
        excess_size = order.size - reduced_size
        if excess_size <= _SIZE_EPSILON:      # float noise, not exposure
            excess_size = 0.0
        # Exposure grows only if something is left over once the position has
        # been closed out.
        increases_exposure = excess_size > 0.0
        excess_notional_jpy = excess_size * order.price
        # MAX_ORDER_SIZE, on what the order ADDS.
        if increases_exposure and excess_notional_jpy > self.limits.max_order_size_jpy:
            reasons.append(
                f"order notional {excess_notional_jpy:.0f} > MAX_ORDER_SIZE {self.limits.max_order_size_jpy:.0f}"
            )
        # Like MAX_ORDER_SIZE, the position cap binds only when exposure grows:
        # an adverse move can push an existing position's marked notional past
        # the cap, and the closing order must still go through. What is left
        # after the reducing part is what the position becomes — for a pure
        # entry that is the old `position + order`, and for an oversized "close"
        # it is the reverse position the excess opens.
        new_position = (max(0.0, account.position_notional_jpy
                            - reduced_size * order.price)
                        + excess_notional_jpy)
        if increases_exposure and new_position > self.limits.max_position_size_jpy:
            reasons.append(
                f"position notional {new_position:.0f} > MAX_POSITION_SIZE {self.limits.max_position_size_jpy:.0f}"
            )
        # Same rule again for MAX_OPEN_ORDERS: a book already at the cap must
        # not be able to refuse the protective stop. The refusal lands HERE,
        # before the order manager ever runs, so the very path that exists to
        # clear a wedged resting order (`_make_room_for_close`) is never
        # reached — the cap silently becomes "this position cannot be exited".
        if increases_exposure and account.open_orders >= self.limits.max_open_orders:
            reasons.append(
                f"open orders {account.open_orders} >= MAX_OPEN_ORDERS {self.limits.max_open_orders}"
            )
        if self.product is not None:
            if order.size < self.product.min_size:
                reasons.append(
                    f"size {order.size} below product minimum {self.product.min_size}"
                )
            if (order.side == "SELL" and excess_size > 0.0
                    and not self.product.shortable):
                # The excess again: on spot, a SELL bigger than the inventory
                # is a short, whether or not some of it was a close.
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

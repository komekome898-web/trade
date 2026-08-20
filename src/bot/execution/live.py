"""LIVE execution — sends REAL orders to bitFlyer.

Guard: constructing LiveExecutor requires a Settings object already resolved
to Mode.LIVE (which itself requires LIVE_MODE=true AND the config ack phrase,
see bot.settings.resolve_mode). There is no other way to arm it.
"""
from __future__ import annotations

from bot.exchange.bitflyer_client import BitflyerClient
from bot.execution.gateway import ExecutionGateway, OrderStatus, SubmitResult
from bot.settings import Mode, Settings


class LiveModeNotArmed(Exception):
    pass


_STATE_MAP = {"ACTIVE": "ACTIVE", "COMPLETED": "COMPLETED", "CANCELED": "CANCELED",
              "REJECTED": "REJECTED", "EXPIRED": "EXPIRED"}


class LiveExecutor(ExecutionGateway):
    def __init__(self, settings: Settings, client: BitflyerClient):
        if settings.mode is not Mode.LIVE:
            raise LiveModeNotArmed(
                "LiveExecutor requires Mode.LIVE (LIVE_MODE=true + config live_mode_ack). "
                "Refusing to construct in any other mode."
            )
        self._client = client

    def submit_order(self, *, symbol: str, side: str, size: float,
                     order_type: str, price: float | None) -> SubmitResult:
        resp = self._client.send_child_order(
            product_code=symbol, side=side, size=size,
            child_order_type=order_type, price=price,
        )
        return SubmitResult(acceptance_id=resp["child_order_acceptance_id"])

    def cancel_order(self, *, symbol: str, acceptance_id: str) -> None:
        self._client.cancel_child_order(product_code=symbol,
                                        child_order_acceptance_id=acceptance_id)

    def fetch_order_status(self, *, symbol: str, acceptance_id: str) -> OrderStatus | None:
        orders = self._client.get_child_orders(symbol, child_order_acceptance_id=acceptance_id)
        if not orders:
            return None
        o = orders[0]
        return OrderStatus(
            acceptance_id=acceptance_id,
            state=_STATE_MAP.get(o.get("child_order_state", ""), "ACTIVE"),
            filled_size=float(o.get("executed_size") or 0.0),
            avg_fill_price=float(o["average_price"]) if o.get("average_price") else None,
        )

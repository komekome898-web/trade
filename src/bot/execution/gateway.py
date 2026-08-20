"""Execution gateway interface: strategies/risk never touch this directly;
only the order manager drives it. Paper and live implementations are
interchangeable behind this ABC."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SubmitResult:
    acceptance_id: str


@dataclass
class OrderStatus:
    acceptance_id: str
    state: str                    # ACTIVE / COMPLETED / CANCELED / REJECTED / EXPIRED
    filled_size: float
    avg_fill_price: float | None


class ExecutionGateway(ABC):
    @abstractmethod
    def submit_order(self, *, symbol: str, side: str, size: float,
                     order_type: str, price: float | None) -> SubmitResult:
        ...

    @abstractmethod
    def cancel_order(self, *, symbol: str, acceptance_id: str) -> None:
        ...

    @abstractmethod
    def fetch_order_status(self, *, symbol: str, acceptance_id: str) -> OrderStatus | None:
        ...

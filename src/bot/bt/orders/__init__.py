"""Item 2 (old 2): orders and the venue's rules.

`product` (the instrument), `rules` (the venue's declared rules: policies and
constraints, no defaults), `faults` (injected rejects / timeouts / ambiguous
answers), `kill_switch` (never resumes on its own), `client` (the strategy's
side: place / cancel / amend by reference, OCO, notices, status). The venue
that applies the rules is `bot.bt.fill.venue.SimVenue`. Fixed requirements:
docs/DISCUSSIONS/2026-09-23_backtest_env/item_2/REQUIREMENTS.md. Tests:
tests/bt/item_2/."""
from .client import (
    ALL_ORDER_TYPES,
    AMEND,
    AMEND_APPLIED,
    AMENDED_SIZE_FILLED,
    AMENDS_KEY,
    LIQUIDATION,
    OCO_KEY,
    ORDER_TYPES,
    ROUNDED_SIZE_FILLED,
    SIZE_LOWERED_AND_FILLED,
    STATUSES,
    TIME_IN_FORCE,
    OrderClient,
    build_order,
)
from .errors import (
    ExecutionModelError,
    FaultPlanError,
    KillSwitchEngaged,
    OrderClientError,
    ProductSpecError,
    RuleNotDeclaredError,
    RuleValueError,
)
from .faults import CANCEL_FAULTS, FAULT_KINDS, NEW_ORDER_FAULTS, Fault, FaultPlan
from .kill_switch import KillSwitch
from .product import Product
from .rules import POLICY_VALUES, ClosedWindows, PriceLimit, Sessions, VenueRules

__all__ = [
    "ALL_ORDER_TYPES", "AMEND", "AMENDED_SIZE_FILLED", "AMENDS_KEY", "AMEND_APPLIED", "CANCEL_FAULTS",
    "ClosedWindows", "ExecutionModelError", "FAULT_KINDS", "Fault", "FaultPlan", "FaultPlanError",
    "KillSwitch", "KillSwitchEngaged", "LIQUIDATION", "NEW_ORDER_FAULTS", "OCO_KEY", "ORDER_TYPES",
    "OrderClient", "OrderClientError", "POLICY_VALUES", "PriceLimit", "ROUNDED_SIZE_FILLED", "SIZE_LOWERED_AND_FILLED", "Product", "ProductSpecError",
    "RuleNotDeclaredError", "RuleValueError", "STATUSES", "Sessions", "TIME_IN_FORCE", "VenueRules",
    "build_order",
]

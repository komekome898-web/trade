"""Errors of the item 2 modules (orders, fill, latency, costs, portfolio).

Every one of them is a refusal: the run (or the one call) stops and says what
was missing or wrong. None is ever turned into a default value.
"""
from __future__ import annotations


class ExecutionModelError(Exception):
    """Base class of every item 2 refusal."""


class RuleNotDeclaredError(ExecutionModelError):
    """A situation arose that a venue rule decides (an off-tick price, a
    self-match, a market order that exhausts the book, ...) and the run did not
    declare that rule. The venue does not pick one."""


class RuleValueError(ExecutionModelError):
    """A declared rule has a value the model does not know."""


class ProductSpecError(ExecutionModelError):
    """A product specification is malformed."""


class KillSwitchEngaged(ExecutionModelError):
    """An order was refused locally because the kill switch is tripped. The
    order never left the strategy (nothing is sent to the venue)."""


class OrderClientError(ExecutionModelError):
    """A strategy-side order call that the order client refuses (an unknown
    reference, a reference used twice, an amend of an order that is not
    amendable from the strategy's knowledge, ...)."""


class FaultPlanError(ExecutionModelError):
    """A fault injection plan is malformed."""

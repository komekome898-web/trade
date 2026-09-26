"""Fault injection: the abnormal answers a venue can give, injected on purpose.

A `FaultPlan` names, per client order id, what goes wrong when that order's
request reaches the venue (`SimVenue` reads the plan). The kinds:

* ``reject`` -- the venue refuses the new order (an explicit Reject; the
  strategy gets an ORDER_REJECT notice).
* ``timeout`` -- the request gets no answer in time. The venue answers
  StateUnknown (the strategy's view is STATE_UNKNOWN) and the order does NOT
  exist at the venue (the request was lost). Nothing is ever resent: the core
  has no resend path and neither has the order client (CLAUDE.md section 1).
* ``unknown`` -- an ambiguous error answer (the connection dropped after the
  send). Same facts as ``timeout`` (StateUnknown, the order does not live),
  with a different detail text.
* ``ack_lost`` -- the order DOES reach the book and lives, but its answer is
  lost: StateUnknown is reported instead of the Ack. A later fill or cancel
  settles it (the core settles STATE_UNKNOWN on those notices).
* ``cancel_reject`` / ``cancel_timeout`` -- for a cancel of that order: the
  venue refuses the cancel / gives an ambiguous answer to it (the order's
  state is then held as STATE_UNKNOWN until a later notice settles it).

The plan is required by `SimVenue` (pass `FaultPlan(())` for "no faults"):
the run says whether it injects anything.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from .errors import FaultPlanError

NEW_ORDER_FAULTS = ("reject", "timeout", "unknown", "ack_lost")
CANCEL_FAULTS = ("cancel_reject", "cancel_timeout")
FAULT_KINDS = NEW_ORDER_FAULTS + CANCEL_FAULTS


@dataclass(frozen=True)
class Fault:
    kind: str
    client_order_id: str

    def __post_init__(self) -> None:
        if type(self.kind) is not str or self.kind not in FAULT_KINDS:
            raise FaultPlanError(f"fault kind {self.kind!r}: known kinds are {FAULT_KINDS}")
        if type(self.client_order_id) is not str or not self.client_order_id:
            raise FaultPlanError(f"fault needs a non-empty client_order_id, got {self.client_order_id!r}")


class FaultPlan:
    """At most one new-order fault and one cancel fault per client order id."""

    def __init__(self, faults: Sequence[Fault]) -> None:
        self._new: dict[str, str] = {}
        self._cancel: dict[str, str] = {}
        for f in faults:
            if type(f) is not Fault:
                raise FaultPlanError(f"a FaultPlan holds Fault objects, got {type(f).__name__}")
            table = self._new if f.kind in NEW_ORDER_FAULTS else self._cancel
            if f.client_order_id in table:
                raise FaultPlanError(f"two faults of the same request kind for {f.client_order_id!r}")
            table[f.client_order_id] = f.kind
        self.faults: tuple[Fault, ...] = tuple(faults)

    def new_order_fault(self, client_order_id: str) -> Optional[str]:
        return self._new.get(client_order_id)

    def cancel_fault(self, client_order_id: str) -> Optional[str]:
        return self._cancel.get(client_order_id)

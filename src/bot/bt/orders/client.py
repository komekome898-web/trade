"""The strategy's side of order handling: placing, cancelling and amending by a
reference, the kill switch, and what the strategy learnt from its notices.

The core (`bot.bt.core`) knows two requests -- a new order and a cancel -- and
a set of order types that "is item 2's to define" (`OrderRequest.order_type`).
This module defines that set and the two things built on top of it:

* **OCO** -- two orders linked by `extra["oco"] = <the other's id>`; the venue
  cancels one when the other fills (`bot.bt.fill.venue`).
* **Amend** -- the core has no amend request, so an amend travels as a new
  request of order type ``"amend"`` whose `extra["amends"]` names the target.
  It goes through the strategy's order channel (order latency, account check,
  fault plan) like any request. The venue answers it Ack + Canceled with
  reason ``"amend_applied"`` when it applied it, or Reject when it did not.
  The target keeps its own id; its later fills are the target's.
  Because the core's view of the target keeps the request as first sent (its
  size included), a target whose amended (smaller) size filled in full is
  closed by the venue with Canceled(reason ``"amended_size_filled"``) and the
  client reports it as "filled" (`status`). The same holds for a size the
  venue floored to its size grid (rule off_step = round_down; reason
  ``"rounded_size_filled"``). These two reasons (`SIZE_LOWERED_AND_FILLED`)
  are the venue -> client protocol for "the venue lowered the size and the
  lower size filled"; they are the only places the client's status and the
  core's state name differ.

Nothing here resends anything: a STATE_UNKNOWN order stays STATE_UNKNOWN until
a notice settles it (CLAUDE.md section 1). A tripped kill switch refuses every
new order locally (`KillSwitchEngaged`); the order never reaches the venue.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from bot.bt.core import (
    FORCED_ID_PREFIX,
    EngineResult,
    Event,
    EventType,
    OrderRequest,
    OrderState,
    StrategyContext,
)

from .errors import KillSwitchEngaged, OrderClientError
from .kill_switch import KillSwitch

# order types a strategy can place; "liquidation" is the venue's own (a forced
# order from the account socket), "amend" is the amend request
ORDER_TYPES = ("market", "limit", "stop", "stop_limit")
AMEND = "amend"
LIQUIDATION = "liquidation"
ALL_ORDER_TYPES = ORDER_TYPES + (AMEND, LIQUIDATION)
TIME_IN_FORCE = ("GTC", "IOC", "FOK")
OCO_KEY = "oco"
AMENDS_KEY = "amends"
AMEND_PREFIX = "amend:"
AMEND_APPLIED = "amend_applied"
AMENDED_SIZE_FILLED = "amended_size_filled"
ROUNDED_SIZE_FILLED = "rounded_size_filled"
# the venue's reasons for closing an order whose size IT lowered (an applied
# amend, a size floored to the grid) once that lower size filled in full: the
# order is done, filled, although the core's view keeps the size first sent
SIZE_LOWERED_AND_FILLED = (AMENDED_SIZE_FILLED, ROUNDED_SIZE_FILLED)

STATUSES = ("filled", "open", "canceled", "rejected", "state_unknown")

_NOTICE_KIND = {
    EventType.ORDER_ACK: "ack",
    EventType.ORDER_FILL: "fill",
    EventType.ORDER_CANCELED: "cancel",
    EventType.ORDER_STATE_UNKNOWN: "state_unknown",
}
_EPS = 1e-12


def build_order(*, client_order_id: str, side: str, order_type: str, size: float,
                price: Optional[float] = None, trigger_price: Optional[float] = None, tif: str = "GTC",
                post_only: bool = False, reduce_only: bool = False, oco_with: Optional[str] = None) -> OrderRequest:
    """One strategy order as a core `OrderRequest`, with the combination of
    fields each type needs checked here (the venue checks them again, for
    requests built without this function)."""
    if order_type not in ORDER_TYPES:
        raise OrderClientError(f"order_type {order_type!r}: a strategy places one of {ORDER_TYPES}")
    if tif not in TIME_IN_FORCE:
        raise OrderClientError(f"tif {tif!r}: one of {TIME_IN_FORCE}")
    needs_price = order_type in ("limit", "stop_limit")
    needs_trigger = order_type in ("stop", "stop_limit")
    if needs_price != (price is not None):
        raise OrderClientError(f"a {order_type} order {'needs' if needs_price else 'takes no'} price")
    if needs_trigger != (trigger_price is not None):
        raise OrderClientError(f"a {order_type} order {'needs' if needs_trigger else 'takes no'} trigger_price")
    if post_only and order_type != "limit":
        raise OrderClientError("post_only applies to a limit order only")
    if needs_trigger and tif != "GTC":
        raise OrderClientError("a stop order waits for its trigger: its tif is GTC")
    extra: tuple = ()
    if oco_with is not None:
        if type(oco_with) is not str or not oco_with or oco_with == client_order_id:
            raise OrderClientError(f"oco_with must name another order, got {oco_with!r}")
        extra = ((OCO_KEY, oco_with),)
    return OrderRequest(side=side, order_type=order_type, size=size, price=price,
                        client_order_id=client_order_id, time_in_force=tif, post_only=post_only,
                        reduce_only=reduce_only, trigger_price=trigger_price, extra=extra)


@dataclass
class _Placed:
    request: OrderRequest
    amends: list[str] = field(default_factory=list)  # amend request ids, in send order


class OrderClient:
    """Use from inside a strategy's `on_event`. Call `observe(event, ctx)` for
    every delivered event so the client records when each notice reached the
    strategy (its local time)."""

    def __init__(self, kill_switch: KillSwitch) -> None:
        if type(kill_switch) is not KillSwitch:
            raise OrderClientError("OrderClient needs a KillSwitch")
        self.kill_switch = kill_switch
        self._placed: dict[str, _Placed] = {}
        self._amend_of: dict[str, str] = {}  # amend request id -> target ref
        self._refused: dict[str, str] = {}  # ref -> reason (refused before sending)
        self._notices: dict[str, dict[str, int]] = {}
        self._amend_requests: dict[str, OrderRequest] = {}

    # -- acting --------------------------------------------------------------
    def _check_ref(self, ref: str) -> None:
        if type(ref) is not str or not ref:
            raise OrderClientError(f"an order reference is a non-empty str, got {ref!r}")
        if ref.startswith(FORCED_ID_PREFIX) or ref.startswith(AMEND_PREFIX):
            raise OrderClientError(f"reference {ref!r} uses a reserved prefix")
        if ref in self._placed or ref in self._refused:
            raise OrderClientError(f"reference {ref!r} was already used")

    def place(self, ctx: StrategyContext, *, ref: str, side: str, order_type: str, size: float,
              price: Optional[float] = None, trigger_price: Optional[float] = None, tif: str = "GTC",
              post_only: bool = False, reduce_only: bool = False, oco_with: Optional[str] = None) -> str:
        self._check_ref(ref)
        if self.kill_switch.is_tripped:
            self._refused[ref] = f"kill_switch: {self.kill_switch.reason}"
            raise KillSwitchEngaged(f"order {ref!r} refused: the kill switch is tripped ({self.kill_switch.reason})")
        request = build_order(client_order_id=ref, side=side, order_type=order_type, size=size, price=price,
                              trigger_price=trigger_price, tif=tif, post_only=post_only,
                              reduce_only=reduce_only, oco_with=oco_with)
        coid = ctx.place_order(request)
        self._placed[ref] = _Placed(request)
        return coid

    def cancel(self, ctx: StrategyContext, ref: str) -> None:
        if ref not in self._placed:
            raise OrderClientError(f"cancel of {ref!r}, which this client did not place")
        ctx.cancel_order(ref)

    def amend(self, ctx: StrategyContext, ref: str, *, price: Optional[float] = None,
              size: Optional[float] = None) -> str:
        """Send an amend of a resting limit order: a new price, a new total
        size, or both. Returns the amend request's id."""
        placed = self._placed.get(ref)
        if placed is None:
            raise OrderClientError(f"amend of {ref!r}, which this client did not place")
        if price is None and size is None:
            raise OrderClientError("an amend changes the price, the size, or both")
        req = placed.request
        if req.order_type not in ("limit", "stop_limit"):
            raise OrderClientError(f"only a limit price / size is amended here; {ref!r} is a {req.order_type} order")
        if self.kill_switch.is_tripped:
            raise KillSwitchEngaged(f"amend of {ref!r} refused: the kill switch is tripped")
        cur_price, cur_size = self._last_sent_terms(ref)
        amend_id = f"{AMEND_PREFIX}{ref}:{len(placed.amends) + 1}"
        request = OrderRequest(side=req.side, order_type=AMEND, size=cur_size if size is None else size,
                               price=cur_price if price is None else price, client_order_id=amend_id,
                               extra=((AMENDS_KEY, ref),))
        ctx.place_order(request)
        placed.amends.append(amend_id)
        self._amend_of[amend_id] = ref
        self._amend_requests[amend_id] = request
        return amend_id

    def _last_sent_terms(self, ref: str) -> tuple[float, float]:
        """Price and size of the last request sent for `ref` (the order, or its
        latest amend): an amend states both terms in full."""
        placed = self._placed[ref]
        last = placed.request if not placed.amends else self._amend_requests[placed.amends[-1]]
        return float(last.price), float(last.size)

    def kill(self, reason: str, now_ns: Optional[int]) -> None:
        self.kill_switch.trip(reason, now_ns)

    # -- learning ------------------------------------------------------------
    def observe(self, event: Event, ctx: StrategyContext) -> None:
        etype = event.EVENT_TYPE
        if etype is EventType.ORDER_REJECT:
            kind = "reject" if event.request_kind == "new" else "cancel_reject"  # type: ignore[attr-defined]
        else:
            kind = _NOTICE_KIND.get(etype)
        if kind is None:
            return
        coid = event.client_order_id  # type: ignore[attr-defined]
        self._notices.setdefault(coid, {}).setdefault(kind, ctx.now_ns)

    def notice_times(self, ref: str) -> dict[str, int]:
        """The local time the strategy first saw each kind of notice about
        `ref` (ack / reject / fill / cancel / state_unknown / cancel_reject)."""
        return dict(self._notices.get(ref, {}))

    # -- results -------------------------------------------------------------
    def refs(self) -> list[str]:
        return list(self._placed) + [r for r in self._refused if r not in self._placed]

    def refused_reason(self, ref: str) -> Optional[str]:
        return self._refused.get(ref)

    def effective_size(self, result: EngineResult, ref: str) -> float:
        """The size in force: the last amend the venue applied, else the
        order's own size (from the strategy's knowledge in `result`)."""
        placed = self._placed[ref]
        size = float(placed.request.size)
        for amend_id in placed.amends:
            view = result.orders.get(amend_id)
            if view is not None and view.state is OrderState.CANCELED and view.reason == AMEND_APPLIED:
                size = float(view.request.size)
        return size

    def status(self, result: EngineResult, ref: str) -> str:
        """One of STATUSES, from what the strategy knew at the end of the run."""
        if ref in self._refused:
            return "rejected"
        view = result.orders.get(ref)
        if view is None:
            raise OrderClientError(f"no order {ref!r} in the result")
        state = view.state
        if state is OrderState.FILLED:
            return "filled"
        if state is OrderState.CANCELED:
            if view.reason in SIZE_LOWERED_AND_FILLED and view.filled_size > 0:
                return "filled"
            return "canceled"
        if state is OrderState.REJECTED:
            return "rejected"
        if state is OrderState.STATE_UNKNOWN:
            return "state_unknown"
        return "open"

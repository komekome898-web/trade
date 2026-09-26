"""Item 2 battery: the protocol between the runner and a target adapter.

A target adapter is a module that defines ``TARGET`` (an object with a
``name`` string and a ``run(scene_input: dict) -> dict`` method).  The runner
hands the adapter one scene input at a time (a plain JSON-able dict, see
``DEFINITIONS.md`` "入力の形") and gets back an observation dict:

    {
      "orders":  {ref: {"status": one of STATUSES}},
      "fills":   [{"ref": str, "t": int ns (venue time the fill is known),
                   "px": float, "qty": float, "fee": float (paid, JPY; a
                   rebate is negative), "liq": "maker" | "taker" | None}],
      "sent":    {ref: int}        # submissions that reached the venue
      "notices": {ref: {"ack": ns, "reject": ns, "fill": ns, "cancel": ns,
                        "state_unknown": ns}}   # local time the strategy saw it
      "seen":    {label: ns}       # local time the strategy saw a labelled market event
      "account": {"position": float, "realized": float, "unrealized": float,
                  "avg_px": float, "exposure_ns": int, "liquidated_t": ns|None,
                  "realized_jpy": float}
      "costs":   {"funding": float, "swap": float}   # paid (credit negative)
      "range":   {"optimistic": <observation>, "pessimistic": <observation>}
    }

Only the keys a scene's expected answer names are read; an adapter reports
what the target produced and never fills in a value the target did not give.

Three ways a run can end without an observation:
- ``Refused``: the TARGET refused (it raised, or returned an explicit error)
  -- classified 「対応なし」.
- ``NotExpressible``: the ADAPTER found no public way to hand this scene to
  the target -- classified 「結果なし」 with the reason (what was tried).
- any other exception escaping the adapter -- 「結果なし」 with the traceback
  tail (an adapter defect, recorded, never counted as a refusal).

Order-level refusals: when the target raises while accepting ONE order, the
adapter records that order as ``rejected`` and continues (``place_guarded``).
Every scene that expects a rejection also carries a control order of the
same kind that must be accepted, so a target that raises on every order of
that kind does not pass.
"""
from __future__ import annotations

STATUSES = ("filled", "open", "canceled", "rejected", "state_unknown")


class Refused(Exception):
    """The target itself refused the run (exception or explicit error)."""


class NotExpressible(Exception):
    """The adapter has no public way to give this scene to the target."""


def place_guarded(orders: dict, ref: str, fn, *args, **kwargs):
    """Call the target's order-submission ``fn``; if the target raises for
    this one order, record ``ref`` as rejected (with the error) and return None."""
    try:
        return fn(*args, **kwargs)
    except (NotExpressible, Refused):
        raise
    except Exception as exc:  # the target refused this order
        orders[ref] = {"status": "rejected", "error": f"{type(exc).__name__}: {exc}"[:300]}
        return None


def need(cond: bool, what: str) -> None:
    """Raise NotExpressible(what) unless cond."""
    if not cond:
        raise NotExpressible(what)

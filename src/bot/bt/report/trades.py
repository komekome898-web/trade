"""Round trips from fills (item 3, old item 9): the trade records the
metrics read, made from the engine's fills by FIFO lot matching.

Each fill is {"order_id", "t_ns", "side", "px", "qty", "fee", "liquidity"}.
An opening fill becomes a lot; a fill against the position closes the
oldest lots first; each (lot, closing fill) match is one trade with qty =
the matched quantity, entry/exit prices and times of the two fills, fees =
the two fills' fees in proportion to the matched quantity, and `reason` =
the exit reason the caller gives for the closing order (`reasons`, by
order id; an order it does not name is refused -- a trade never gets an
invented reason). A fill larger than the position closes it and opens the
rest the other way.
"""
from __future__ import annotations

from collections import deque
from typing import Mapping, Sequence

from .errors import ReportError
from .metrics import SIDES


def round_trips(fills: Sequence[Mapping], reasons: Mapping[str, str]) -> list[dict]:
    lots: deque = deque()  # [side, qty_left, px, t_ns, fee_per_qty, order_id]
    out: list[dict] = []
    for i, f in enumerate(fills):
        side = f.get("side")
        if side not in SIDES:
            raise ReportError(f"fills[{i}].side must be buy/sell")
        qty, px, fee = float(f["qty"]), float(f["px"]), float(f["fee"])
        if not qty > 0:
            raise ReportError(f"fills[{i}].qty must be > 0")
        left = qty
        while left > 1e-15 and lots and lots[0][0] != side:
            lot = lots[0]
            m = min(left, lot[1])
            oid = f["order_id"]
            if oid not in reasons:
                raise ReportError(f"no exit reason for the closing order {oid!r}")
            out.append({"id": f"{lot[5]}>{oid}#{len(out) + 1}", "side": lot[0], "qty": m,
                        "entry_px": lot[2], "exit_px": px, "entry_t_ns": lot[3], "exit_t_ns": int(f["t_ns"]),
                        "fees": lot[4] * m + fee / qty * m, "reason": reasons[oid],
                        "pnl": SIDES[lot[0]] * (px - lot[2]) * m - (lot[4] * m + fee / qty * m)})
            lot[1] -= m
            left -= m
            if lot[1] <= 1e-15:
                lots.popleft()
        if left > 1e-15:
            lots.append([side, left, px, int(f["t_ns"]), fee / qty, f["order_id"]])
    return out


def open_lots(fills: Sequence[Mapping]) -> float:
    """The signed position left after all fills."""
    return sum(SIDES[f["side"]] * float(f["qty"]) for f in fills)

"""Shared helpers for the item-4 reference tests (not a test module)."""
from __future__ import annotations

from fractions import Fraction as F

from bot.bt.reference.event_sim import Cancel, Limit, Market, make_event, simulate


def base_params(**kw) -> dict:
    p = dict(initial_cash=0, maker_rate=0, taker_rate=0, order_latency_ns=0,
             cancel_latency_ns=0, notify_latency_ns=0, tick_size=1, lot_size="0.01",
             min_qty="0.01", liquidity="trades", limit_cross="strict", limit_fill_qty="full")
    p.update(kw)
    return p


def trade(t, seq, price, qty=1, recv=None):
    return make_event("trade", t, t if recv is None else recv, seq, price=price, qty=qty)


def book(t, seq, bids, asks, recv=None):
    return make_event("book", t, t if recv is None else recv, seq, bids=bids, asks=asks)


def clock(t, seq, recv=None):
    return make_event("clock", t, t if recv is None else recv, seq)


class Script:
    """Strategy that submits fixed actions when a given item is delivered.

    plan maps a key to a list of actions; the key is ("event", seq) or
    ("note", cid, kind). Each key fires once. Every call is logged.
    """

    def __init__(self, plan: dict):
        self.plan = dict(plan)
        self.calls = []
        self._seen = 0

    def __call__(self, ctx):
        self.calls.append(ctx)
        new = ctx.visible[self._seen:]
        self._seen = len(ctx.visible)
        out = []
        for it in new:
            if hasattr(it, "seq") and not hasattr(it, "cid"):
                key = ("event", it.seq)
            else:
                key = ("note", it.cid, it.kind)
            out.extend(self.plan.pop(key, []))
        return out


__all__ = ["F", "Cancel", "Limit", "Market", "Script", "base_params", "book", "clock",
           "make_event", "simulate", "trade"]

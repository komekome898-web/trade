"""Declarations the item-4 worker's pipeline tests share (bot.bt.pipeline, finishing stage i4-r2-06): the item-2
execution models in the integrated run's sockets. Values are STATED for the tests (動作確認), not measured: zero
costs, zero delays, fill range tier 3 (optimistic: a touch fills) / tier 1 (pessimistic: a strict cross fills)."""
from __future__ import annotations

FILL = {"optimistic": {"tier": 3}, "pessimistic": {"tier": 1}}
LATENCY0 = {ch: {"kind": "constant", "ns": 0} for ch in ("feed", "order", "cancel", "notice")}
COSTS0 = {"maker_rate": 0.0, "taker_rate": 0.0, "spread": 0.0,
          "source": "動作確認: 費用 0 を宣言した(測った費用ではない)"}
ACCOUNT = {"currency": "JPY", "cash": 1e12, "leverage": 1.0, "mark": "last_trade", "liquidation": None,
           "margin_check": "open_orders"}
RULES_BOOK = {"off_tick": "reject", "below_min_qty": "reject", "off_step": "reject", "market_remainder": "cancel",
              "market_ref": "last_trade"}
RULES_BARS = {**RULES_BOOK, "market_ref": "next_bar_open"}


def product(symbol: str, quote_ccy: str = "JPY") -> dict:
    return {"symbol": symbol, "venue": "test", "tick": 1e-9, "min_qty": 1e-8, "qty_step": 1e-8,
            "quote_ccy": quote_ccy, "margin": True}


def instrument(name: str, price: str, kind: str, with_=()) -> dict:
    return {"name": name, "price": price, "with": list(with_), "product": product(name),
            "rules": RULES_BARS if kind == "bar" else RULES_BOOK}


def kw() -> dict:
    """fill / latency / costs / account keyword arguments of plan_pipeline."""
    return {"fill": FILL, "latency": LATENCY0, "costs": COSTS0, "account": ACCOUNT}

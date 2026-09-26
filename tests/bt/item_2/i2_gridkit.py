"""Shared helpers of the item 2 grid tests: a scene-shaped input builder (the
battery's input form, DEFINITIONS.md section 1) and a runner that returns the
observation or the refusal. The grids enumerate their input spaces here; the
oracles are written in each test from the rule texts, not from the
implementation's branches."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import i2_driver as D  # noqa: E402
from i2_protocol import Refused  # noqa: E402

MS = 1_000_000
SEC = 1_000_000_000
T0 = 1_767_571_200 * SEC  # 2026-01-05 00:00:00 UTC (Monday)

BTC = {"symbol": "FX_BTC_JPY", "venue": "bitflyer_cfd", "tick": 1.0, "min_qty": 0.01, "qty_step": 1e-08,
       "quote_ccy": "JPY", "margin": True}
RULES = {"off_tick": "reject", "below_min_qty": "reject", "post_only": "reject_if_crossing",
         "market_remainder": "cancel", "mark": "last_trade"}
COSTS0 = {"maker_rate": 0.0, "taker_rate": 0.0, "source": "grid test: zero costs stated"}
ACCOUNT = {"currency": "JPY", "cash": 1e9, "leverage": 1.0}


def book(t, bids, asks, label=None):
    d = {"t": t, "type": "book", "bids": [list(x) for x in bids], "asks": [list(x) for x in asks]}
    if label:
        d["label"] = label
    return d


def trade(t, px, qty, aggressor):
    return {"t": t, "type": "trade", "px": float(px), "qty": float(qty), "aggressor": aggressor}


def place(t, ref, side, otype, qty, px=None, stop_px=None, tif="GTC", post_only=False, reduce_only=False, oco=None):
    return {"t": t, "op": "place", "ref": ref, "side": side, "type": otype, "qty": qty, "px": px,
            "stop_px": stop_px, "tif": tif, "post_only": post_only, "reduce_only": reduce_only, "oco": oco}


def inp(market, actions, *, product=BTC, rules=RULES, costs=COSTS0, account=ACCOUNT, fill_model=None,
        latency=None, inject=(), checkpoints=None, end_t=None):
    return {"product": copy.deepcopy(product), "rules": copy.deepcopy(rules), "market": market,
            "actions": actions, "fill_model": fill_model, "latency": latency, "costs": copy.deepcopy(costs),
            "account": copy.deepcopy(account), "inject": list(inject), "checkpoints": dict(checkpoints or {}),
            "end_t": end_t if end_t is not None else T0 + 60 * SEC}


def run(i: dict):
    """(observation, None) or (None, refusal text)."""
    try:
        return D.run_scene(i), None
    except Refused as exc:
        return None, str(exc)


def filled(obs: dict, ref: str) -> float:
    return sum(f["qty"] for f in obs["fills"] if f["ref"] == ref)


def avg_px(obs: dict, ref: str):
    fs = [f for f in obs["fills"] if f["ref"] == ref]
    q = sum(f["qty"] for f in fs)
    return None if q == 0 else sum(f["px"] * f["qty"] for f in fs) / q


def first_t(obs: dict, ref: str):
    ts = [f["t"] for f in obs["fills"] if f["ref"] == ref]
    return min(ts) if ts else None

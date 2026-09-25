"""The fixed procedures for runs whose purpose is 動作確認 (委任文 §4
「動作確認用の固定の手順」: a mechanical schedule decided by time only, or a
seeded random draw -- no signal, no conditioning, no optimisation).

A *setup* turns a run's config and seed into the core's parts
(strategy, fill model, latency model, cost model, account). The run layer
(runner.py) records the setup's name and the sha256 of its source, so the
run id changes when the setup's code changes. The three setups here share
one config schema (every key required, no other key accepted):

  instrument   str
  strategy     {"kind": "fixed_times", "legs": [{"t_ns", "side", "qty"}, ...]}
               legs in time order, paired into round trips (legs 2k, 2k+1:
               opposite sides, the same qty)
  order_type   "market"
  fill         {"market": "next_trade_price"}: a market order fills in full,
               as taker, at the price of the first trade the venue handles
               at or after the order's arrival
  latency_ns   {"feed", "order", "cancel"} ints >= 0 (and optionally
               "notice"; when absent the notice delay is 0 and the record
               says so -- these procedures never read a notice)
  costs        {"maker_fee_rate", "taker_fee_rate", "funding": "none",
               "source": non-empty str}: no default cost (a missing key is
               refused)

Setups: `fixed_times` (each leg's qty as given), `seeded_random` (round
trip k's qty = leg qty * (1 + r_k / 256), r_k = random.Random(seed)
.randrange(256) drawn in round-trip order), `unseeded_random` (r_k =
os.urandom(1)[0]; NOT reproducible -- it exists to show that the two-run
check catches that).
"""
from __future__ import annotations

import hashlib
import inspect
import os
import random
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from ..core import (Ack, Canceled, ClockEvent, Event, Fill, NullAccount, OrderRequest, Reject, Strategy,
                    StrategyContext, TradeEvent, VenueReport)
from .errors import ReproError

CONFIG_KEYS = ("instrument", "strategy", "order_type", "fill", "latency_ns", "costs")
EXIT_REASON = "fixed_schedule"


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise ReproError(f"config: {msg}")


def _int(v: Any, what: str, lo: int = 0) -> int:
    _need(type(v) is int and v >= lo, f"{what} must be an int >= {lo}, got {v!r}")
    return v


def _rate(v: Any, what: str) -> float:
    _need(type(v) in (int, float) and v == v and abs(v) < 1, f"{what} must be a finite rate, got {v!r}")
    return float(v)


@dataclass(frozen=True)
class Leg:
    t_ns: int
    side: str
    qty: float


def parse_config(cfg: Mapping) -> dict:
    _need(isinstance(cfg, Mapping), "must be a mapping")
    extra = sorted(set(cfg) - set(CONFIG_KEYS))
    missing = [k for k in CONFIG_KEYS if k not in cfg]
    _need(not extra, f"unknown keys {extra}")
    _need(not missing, f"missing keys {missing}")
    _need(type(cfg["instrument"]) is str and cfg["instrument"], "instrument must be a non-empty str")
    st = cfg["strategy"]
    _need(isinstance(st, Mapping) and set(st) == {"kind", "legs"} and st["kind"] == "fixed_times",
          "strategy must be {kind: 'fixed_times', legs: [...]}")
    legs = []
    for i, lg in enumerate(st["legs"]):
        _need(isinstance(lg, Mapping) and set(lg) == {"t_ns", "side", "qty"}, f"legs[{i}] must be {{t_ns, side, qty}}")
        _need(lg["side"] in ("buy", "sell"), f"legs[{i}].side must be buy/sell")
        _need(type(lg["qty"]) in (int, float) and lg["qty"] > 0, f"legs[{i}].qty must be > 0")
        legs.append(Leg(_int(lg["t_ns"], f"legs[{i}].t_ns", -(2**63)), lg["side"], float(lg["qty"])))
    _need(legs and len(legs) % 2 == 0, "legs must be a non-empty even list (round trips)")
    for k in range(0, len(legs), 2):
        a, b = legs[k], legs[k + 1]
        _need(a.side != b.side and a.qty == b.qty, f"legs {k},{k + 1} must be one round trip (opposite sides, same qty)")
    _need(all(legs[i].t_ns < legs[i + 1].t_ns for i in range(len(legs) - 1)), "legs must be in strictly increasing time")
    _need(cfg["order_type"] == "market", "order_type must be 'market' (the fixed procedures send market orders)")
    _need(cfg["fill"] == {"market": "next_trade_price"}, "fill must be {market: 'next_trade_price'}")
    lat = cfg["latency_ns"]
    _need(isinstance(lat, Mapping) and {"feed", "order", "cancel"} <= set(lat) <= {"feed", "order", "cancel", "notice"},
          "latency_ns must have feed, order, cancel (and optionally notice)")
    lat_v = {k: _int(lat[k], f"latency_ns.{k}") for k in lat}
    c = cfg["costs"]
    _need(isinstance(c, Mapping) and set(c) == {"maker_fee_rate", "taker_fee_rate", "funding", "source"},
          "costs must be exactly {maker_fee_rate, taker_fee_rate, funding, source}")
    _need(c["funding"] == "none", "costs.funding: the fixed procedures support 'none' only")
    _need(type(c["source"]) is str and c["source"].strip(), "costs.source must name where the costs come from")
    return {"instrument": cfg["instrument"], "legs": legs, "latency": lat_v,
            "rates": {"maker": _rate(c["maker_fee_rate"], "maker_fee_rate"),
                      "taker": _rate(c["taker_fee_rate"], "taker_fee_rate")}}


class NextTradeMarketFill:
    """Market orders only: acknowledged at arrival, filled in full as taker
    at the first trade the venue handles after the arrival. Any other order
    type is rejected ('unsupported_order_type')."""

    def __init__(self) -> None:
        self._pending: list[OrderRequest] = []

    def on_market_event(self, event: Event, venue_time_ns: int) -> Sequence[VenueReport]:
        if not isinstance(event, TradeEvent) or not self._pending:
            return ()
        out = [Fill(o.client_order_id, event.price, o.size, "taker") for o in self._pending]
        self._pending = []
        return tuple(out)

    def on_order(self, order: OrderRequest, venue_time_ns: int) -> Sequence[VenueReport]:
        if order.order_type != "market":
            return (Reject(order.client_order_id, "unsupported_order_type"),)
        self._pending.append(order)
        return (Ack(order.client_order_id, f"v-{order.client_order_id}"),)

    def on_cancel(self, request, venue_time_ns: int) -> Sequence[VenueReport]:
        self._pending = [o for o in self._pending if o.client_order_id != request.client_order_id]
        return (Canceled(request.client_order_id),)


class DeclaredFeeCost:
    """fee = price * size * rate of the fill's liquidity (rates from the config)."""

    def __init__(self, rates: Mapping[str, float]) -> None:
        self.rates = dict(rates)

    def cost(self, fill) -> float:
        if fill.liquidity not in self.rates:
            raise ReproError(f"no fee rate for liquidity {fill.liquidity!r}")
        return abs(fill.price * fill.size) * self.rates[fill.liquidity]


class ConstantLatency:
    def __init__(self, feed: int, order: int, cancel: int, notice: int) -> None:
        self.feed, self.order, self.cancel, self.notice = feed, order, cancel, notice

    def feed_delay_ns(self, event) -> int:
        return self.feed

    def order_delay_ns(self, order, sent_time_ns: int) -> int:
        return self.order

    def cancel_delay_ns(self, request, sent_time_ns: int) -> int:
        return self.cancel

    def notice_delay_ns(self, report, venue_time_ns: int) -> int:
        return self.notice


class FixedLegs(Strategy):
    """Sets one timer per leg at the first event it sees, and sends each
    leg's market order when its timer fires. Reads nothing else."""

    def __init__(self, legs: Sequence[Leg], qtys: Sequence[float]) -> None:
        self._legs = list(legs)
        self._qtys = list(qtys)
        self._armed = False

    def on_event(self, event: Event, ctx: StrategyContext) -> None:
        if not self._armed:
            self._armed = True
            if self._legs[0].t_ns < ctx.now_ns:
                raise ReproError(f"the first leg at {self._legs[0].t_ns} is before the data starts ({ctx.now_ns})")
            for i, lg in enumerate(self._legs):
                ctx.set_timer(lg.t_ns, f"leg{i}")
        if isinstance(event, ClockEvent) and event.tag.startswith("leg"):
            i = int(event.tag[3:])
            ctx.place_order(OrderRequest(side=self._legs[i].side, order_type="market", size=self._qtys[i],
                                         client_order_id=f"leg{i}"))


@dataclass
class Parts:
    strategy: Strategy
    fill_model: Any
    latency_model: Any
    cost_model: Any
    account: Any
    exit_reasons: dict  # closing order id -> reason
    notes: dict = field(default_factory=dict)


class FixedSetup:
    """`kind` in SETUP_KINDS. build(config, seed) -> Parts."""

    def __init__(self, kind: str) -> None:
        if kind not in SETUP_KINDS:
            raise ReproError(f"setup kind must be one of {SETUP_KINDS}, got {kind!r}")
        self.kind = kind

    def identity(self) -> dict:
        src = inspect.getsource(inspect.getmodule(FixedSetup))
        return {"name": f"{__name__}:{self.kind}", "source_sha256": hashlib.sha256(src.encode()).hexdigest()}

    def build(self, config: Mapping, seed: int) -> Parts:
        p = parse_config(config)
        legs = p["legs"]
        n_rt = len(legs) // 2
        if self.kind == "fixed_times":
            mult = [1.0] * n_rt
        elif self.kind == "seeded_random":
            rng = random.Random(seed)
            mult = [1 + rng.randrange(256) / 256 for _ in range(n_rt)]
        else:
            mult = [1 + os.urandom(1)[0] / 256 for _ in range(n_rt)]
        qtys = [legs[i].qty * mult[i // 2] for i in range(len(legs))]
        lat = p["latency"]
        notes = {}
        if "notice" not in lat:
            notes["notice_delay_ns"] = "設定に無いので 0(固定の手順は通知を読まないので結果に効かない)"
        return Parts(strategy=FixedLegs(legs, qtys), fill_model=NextTradeMarketFill(),
                     latency_model=ConstantLatency(lat["feed"], lat["order"], lat["cancel"], lat.get("notice", 0)),
                     cost_model=DeclaredFeeCost(p["rates"]), account=NullAccount(),
                     exit_reasons={f"leg{i}": EXIT_REASON for i in range(1, len(legs), 2)}, notes=notes)

    @property
    def seeded(self) -> Optional[bool]:
        return {"fixed_times": None, "seeded_random": True, "unseeded_random": False}[self.kind]


SETUP_KINDS = ("fixed_times", "seeded_random", "unseeded_random")

"""Drive one item 2 battery scene input through the new implementation's
PUBLIC API and return the observation of the battery protocol
(tests/bt/battery/item_2/i2_protocol.py). The table-maker writes the battery's
new-implementation adapter each round; this module is the worker's own
reading of the same mapping, used by the worker's tests. It never reads a
scene's expected answer or id.

Mapping (every choice the scene input leaves open is named here):
- fill_model null (the scene says any tier gives its answer): tier 4 (fills up
  to each reaching trade's size; needs neither a book nor a cancel stance).
  cancel_stance "l3" (the scene: both L3 stances fill the same) -> "l3_advance".
- latency null -> every channel Constant(0).
- rules.sessions_jst -> Sessions(utc_offset 540 = JST, weekdays Mon-Fri: the
  Tokyo Stock Exchange trades on weekdays; the scene's source text).
- costs.funding "apply_events" -> FundingRule(price="event_mark").
- account without maint_ratio -> liquidation=None; rules.mark -> the account mark.
- market items without a core event type (l3_add / l3_cancel, rollover,
  corporate, fx_rate) -> the venue's L3Feed / the account's ReferenceSchedule /
  FxRates (reference data; the strategy does not receive them).
- a tier-2 scene with prints and bar_ns but no bars -> bars_from_trades.
- every action time -> a source ClockEvent in its own stream (delivered at
  that time, no feed delay), on which the strategy performs the actions.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

HERE = Path(__file__).resolve().parent
BATTERY = HERE.parent / "battery" / "item_2"
if str(BATTERY) not in sys.path:
    sys.path.insert(0, str(BATTERY))

from i2_protocol import NotExpressible, Refused  # noqa: E402

from bot.bt.core import (  # noqa: E402
    BarEvent,
    BookSnapshotEvent,
    ClockEvent,
    CoreEngine,
    EventType,
    FundingEvent,
    OrderApiError,
    Strategy,
    TradeEvent,
)
from bot.bt.costs import (  # noqa: E402
    CostSchedule,
    FeeTable,
    FundingRule,
    FxPoint,
    FxRates,
    ScheduleCostModel,
    SwapRule,
)
from bot.bt.fill import (  # noqa: E402
    FillRange,
    FillSpec,
    ImpactSpec,
    L3Add,
    L3Cancel,
    L3Feed,
    SimVenue,
    bars_from_trades,
    run_range,
)
from bot.bt.latency import Constant, Empirical, LatencyModel  # noqa: E402
from bot.bt.orders import (  # noqa: E402
    POLICY_VALUES,
    ClosedWindows,
    ExecutionModelError,
    Fault,
    FaultPlan,
    KillSwitch,
    OrderClient,
    PriceLimit,
    Product,
    Sessions,
    VenueRules,
)
from bot.bt.portfolio import (  # noqa: E402
    CorporateAction,
    LiquidationRule,
    MarginAccount,
    ReferenceSchedule,
    Rollover,
)

NULL_FILL_TIER = 4
STANCE_NAMES = {"l3": "l3_advance"}
RULE_KEYS = set(POLICY_VALUES) | {"mark", "sessions_jst", "closed_utc_ns", "price_limit", "source"}
COST_KEYS = {"maker_rate", "taker_rate", "source", "spread", "funding", "swap", "fee_table", "mid"}


def _refuse(what: str, exc: BaseException) -> Refused:
    return Refused(f"{what}: {type(exc).__name__}: {exc}")


def product_of(d: dict) -> Product:
    return Product(**d)


def rules_of(r: dict) -> VenueRules:
    unknown = set(r) - RULE_KEYS
    if unknown:
        raise NotExpressible(f"rules keys the driver does not map: {sorted(unknown)}")
    kw: dict[str, Any] = {k: r[k] for k in POLICY_VALUES if k in r}
    if "sessions_jst" in r:
        kw["sessions"] = Sessions(tuple((a, b) for a, b in r["sessions_jst"]), 540, (0, 1, 2, 3, 4), r["source"])
    if "closed_utc_ns" in r:
        kw["closed"] = ClosedWindows(tuple((a, b) for a, b in r["closed_utc_ns"]), r["source"])
    if "price_limit" in r:
        pl = r["price_limit"]
        kw["price_limit"] = PriceLimit(pl["base"], pl["width"], pl["source"])
    return VenueRules(**kw)


def costs_of(c: dict) -> CostSchedule:
    unknown = set(c) - COST_KEYS
    if unknown:
        raise NotExpressible(f"cost keys the driver does not map: {sorted(unknown)}")
    kw: dict[str, Any] = {k: c[k] for k in ("maker_rate", "taker_rate", "source", "spread") if k in c}
    if "funding" in c:
        if c["funding"] != "apply_events":
            raise NotExpressible(f"funding {c['funding']!r}")
        kw["funding"] = FundingRule(price="event_mark")
    if "swap" in c:
        kw["swap"] = SwapRule(**c["swap"])
    if "fee_table" in c:
        kw["fee_table"] = FeeTable(tuple((u, f) for u, f in c["fee_table"]))
    try:
        return CostSchedule(**kw)
    except TypeError as exc:  # a required cost missing: the schedule cannot be built
        raise _refuse("CostSchedule", exc) from None


def fill_of(fm: Optional[dict]) -> FillSpec:
    if fm is None:
        return FillSpec(tier=NULL_FILL_TIER)
    kw: dict[str, Any] = {"tier": fm["tier"]}
    if "cancel_stance" in fm:
        kw["cancel_stance"] = STANCE_NAMES.get(fm["cancel_stance"], fm["cancel_stance"])
    for k in ("cancel_rate", "prob_f", "prob_n", "bar_ns"):
        if k in fm:
            kw[k] = fm[k]
    if "impact" in fm:
        kw["impact"] = ImpactSpec(**fm["impact"])
    return FillSpec(**kw)


def latency_of(lat: Optional[dict]) -> LatencyModel:
    if lat is None:
        return LatencyModel(feed=Constant(0), order=Constant(0), cancel=Constant(0), notice=Constant(0))
    chans = {}
    for name in ("feed", "order", "cancel", "notice"):
        d = lat[name]
        if d["kind"] == "constant":
            chans[name] = Constant(d["ns"])
        elif d["kind"] == "empirical":
            chans[name] = Empirical(d["samples_ns"], d["seed"])
        else:
            raise NotExpressible(f"latency kind {d['kind']!r}")
    return LatencyModel(**chans)


def _event_key(ev) -> tuple:
    d = ev.to_dict()
    d.pop("received_time_ns", None)
    d.pop("seq", None)
    return tuple(sorted((k, repr(v)) for k, v in d.items()))


class _Script(Strategy):
    def __init__(self, actions_at: dict[str, list[dict]], client: OrderClient, labels: dict[tuple, list[str]]):
        self.actions_at = actions_at
        self.client = client
        self.labels = labels
        self.seen: dict[str, int] = {}
        self.local_refusals: dict[str, str] = {}

    def on_event(self, event, ctx) -> None:
        self.client.observe(event, ctx)
        if event.EVENT_TYPE is not EventType.CLOCK:
            names = self.labels.get(_event_key(event))
            if names:
                self.seen.setdefault(names.pop(0), ctx.now_ns)
            return
        for a in self.actions_at.get(event.tag, ()):
            op = a["op"]
            if op == "place":
                try:
                    self.client.place(ctx, ref=a["ref"], side=a["side"], order_type=a["type"], size=a["qty"],
                                      price=a["px"] if a["type"] in ("limit", "stop_limit") else None,
                                      trigger_price=a["stop_px"], tif=a["tif"], post_only=a["post_only"],
                                      reduce_only=a["reduce_only"], oco_with=a["oco"])
                except (ExecutionModelError, OrderApiError) as exc:  # this one order refused
                    self.local_refusals[a["ref"]] = f"{type(exc).__name__}: {exc}"
            elif op == "cancel":
                self.client.cancel(ctx, a["ref"])
            elif op == "amend":
                self.client.amend(ctx, a["ref"], price=a.get("px"), size=a.get("qty"))
            elif op == "kill":
                self.client.kill("kill switch action", ctx.now_ns)
            else:
                raise NotExpressible(f"action {op!r}")


def _split_market(inp: dict):
    core, l3, ref, fx, labels = [], [], [], [], {}
    for e in inp["market"]:
        t, typ = e["t"], e["type"]
        ev = None
        if typ == "book":
            ev = BookSnapshotEvent(received_time_ns=t, bids=[tuple(x) for x in e["bids"]],
                                   asks=[tuple(x) for x in e["asks"]])
        elif typ == "trade":
            ev = TradeEvent(received_time_ns=t, price=e["px"], size=e["qty"], side=e["aggressor"])
        elif typ == "bar":
            ev = BarEvent(received_time_ns=t, start_time_ns=t - e["span_ns"], open=e["o"], high=e["h"], low=e["l"],
                          close=e["c"], volume=e["v"])
        elif typ == "funding":
            ev = FundingEvent(received_time_ns=t, rate=e["rate"], mark_price=e.get("mark"))
        elif typ == "l3_add":
            l3.append(L3Add(t, e["id"], e["side"], e["px"], e["qty"]))
        elif typ == "l3_cancel":
            l3.append(L3Cancel(t, e["id"]))
        elif typ == "rollover":
            ref.append(Rollover(t))
        elif typ == "corporate":
            ref.append(CorporateAction(t, e["ratio"]))
        elif typ == "fx_rate":
            fx.append(FxPoint(t, e["pair"], e["px"]))
        else:
            raise NotExpressible(f"market item {typ!r}")
        if ev is not None:
            core.append(ev)
            if e.get("label"):
                labels.setdefault(_event_key(ev), []).append(e["label"])
    return core, l3, ref, fx, labels


def run_once(inp: dict, fill: FillSpec) -> dict:
    product = product_of(inp["product"])
    rules = rules_of(inp["rules"])
    costs = costs_of(inp["costs"])
    core, l3_items, ref_items, fx_points, labels = _split_market(inp)
    fx = FxRates(fx_points) if fx_points else None
    streams: dict[str, list] = {"market": core}
    if fill.tier == 2 and fill.bar_ns and not any(type(e) is BarEvent for e in core):
        streams["bars"] = bars_from_trades([e for e in core if type(e) is TradeEvent], fill.bar_ns)
    actions_at: dict[str, list[dict]] = {}
    clocks = []
    for a in inp["actions"]:
        tag = f"t{a['t']}"
        if tag not in actions_at:
            clocks.append(ClockEvent(received_time_ns=a["t"], tag=tag))
        actions_at.setdefault(tag, []).append(a)
    clocks.sort(key=lambda c: c.received_time_ns)
    streams["actions"] = clocks
    faults = FaultPlan(tuple(Fault(f["kind"], f["ref"]) for f in inp.get("inject") or ()))
    venue = SimVenue(product=product, rules=rules, fill=fill, costs=costs, faults=faults,
                     l3=L3Feed(l3_items) if l3_items else None)
    acc = inp["account"]
    liquidation = None
    if "maint_ratio" in acc:
        liquidation = LiquidationRule(acc["maint_ratio"], acc.get("source", ""), acc.get("liquidation_price", "mark"))
    account = MarginAccount(product=product, currency=acc["currency"], cash=acc["cash"], leverage=acc["leverage"],
                            liquidation=liquidation, mark=inp["rules"].get("mark", "last_trade"), costs=costs, fx=fx,
                            reference=ReferenceSchedule(ref_items) if ref_items else None,
                            open_orders=venue.open_orders)
    cost_model = ScheduleCostModel(costs, product=product, account_currency=acc["currency"], fx=fx)
    client = OrderClient(KillSwitch(None))
    strategy = _Script(actions_at, client, labels)
    times = [e.received_time_ns for s in streams.values() for e in s]
    engine = CoreEngine(strategy, streams, venue, latency_of(inp["latency"]), cost_model, account,
                        end_time_ns=inp["end_t"], time_span_ns=(min(times), max(max(times), inp["end_t"])))
    result = engine.run()
    snap = account.finish(inp["end_t"])
    refs = [a["ref"] for a in inp["actions"] if a["op"] == "place"]
    orders = {}
    for r in refs:
        if r in strategy.local_refusals:
            orders[r] = {"status": "rejected", "error": strategy.local_refusals[r]}
        else:
            orders[r] = {"status": client.status(result, r)}
    fills = [{"ref": f.client_order_id, "t": f.venue_time_ns, "px": f.price, "qty": f.size, "fee": f.fee,
              "liq": f.liquidity} for f in result.fills]
    return {
        "orders": orders,
        "fills": fills,
        "sent": {r: (1 if r in result.venue_states else 0) for r in refs},
        "notices": {r: client.notice_times(r) for r in refs},
        "seen": dict(strategy.seen),
        "account": {"position": snap.position, "realized": snap.realized, "unrealized": snap.unrealized,
                    "avg_px": snap.avg_px, "exposure_ns": snap.exposure_ns, "liquidated_t": snap.liquidated_t,
                    "realized_jpy": snap.realized_account if snap.currency == "JPY" else None},
        "costs": {"funding": snap.funding_paid, "swap": snap.swap_paid},
    }


def run_scene(inp: dict) -> dict:
    """The observation for one scene input; Refused when the new
    implementation refuses the run (an item 2 refusal or a missing required
    cost), NotExpressible when this driver has no mapping."""
    fm = inp["fill_model"]
    try:
        if fm is not None and "range" in fm:
            sides = fm["range"]
            fr = FillRange(optimistic=fill_of(sides.get("optimistic")) if sides.get("optimistic") else None,
                           pessimistic=fill_of(sides.get("pessimistic")) if sides.get("pessimistic") else None)
            rr = run_range(lambda spec: run_once(inp, spec), fr)
            return {"range": {"optimistic": rr.optimistic, "pessimistic": rr.pessimistic}}
        return run_once(inp, fill_of(fm))
    except ExecutionModelError as exc:
        raise _refuse("new implementation refused", exc) from None

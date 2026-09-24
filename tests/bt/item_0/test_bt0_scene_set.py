"""The item-0 scene set (tests/bt/battery/item_0/scenes.py), run against the
core through its public names only, every scene, twice.

This is the worker's own check that the core produces each scene's fixed
expected result. It is NOT the materials person's adapter and does not
replace the comparison table. It reads the scene set (never changes it) and
grades with the battery runner's OWN grading code, imported, not copied
(run_battery.py: `graded_output` builds the graded values of a
`graded_from` scene from the raw observations, `_matches` compares). For
the `graded_from` scenes the drivers below only report observations: each
attempted read and its exception, and the delivered order. The same-time
rule the P0-5 scenes grade by is the scene keeper's copy for this target
(stated_rules.py, target "new_impl", round r5-1); a separate test checks
that copy against the core's written rule applied by hand (from
`ORDERING_RULE["source_merge"]`, never from running the core).

Everything a scene calls a "plug" (fill model, latency model, cost model,
account) is written HERE, against the public socket protocols, to show the
sockets take outside implementations without editing the core. The only
core-provided double used is `ImmediateFillModel` (bot.bt.core.testing),
for scenes whose fill model is not the thing measured.
"""
from __future__ import annotations

import importlib.util
import itertools
import json
import sys
from pathlib import Path
from typing import Any, Callable, Optional

import pytest

import bot.bt.core as core
from bot.bt.core.testing import ImmediateFillModel

_BATTERY = Path(__file__).resolve().parents[1] / "battery" / "item_0" / "scenes.py"
_BATTERY_DIR = _BATTERY.parent
for _p in (str(_BATTERY_DIR), str(_BATTERY_DIR / "adapters")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import run_battery  # noqa: E402  (the battery's own grading; read, never changed)
from adapters.protocol import SceneResult  # noqa: E402


def _load_scenes():
    spec = importlib.util.spec_from_file_location("bt0_item0_scenes", _BATTERY)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("bt0_item0_scenes", mod)
    spec.loader.exec_module(mod)
    return mod


SC = _load_scenes()
SCENES = {s.id: s for s in SC.SCENES}

KIND_OF = {
    core.EventType.TRADE: "trade",
    core.EventType.BOOK_SNAPSHOT: "book_snapshot",
    core.EventType.BOOK_DELTA: "book_delta",
    core.EventType.BAR: "bar",
    core.EventType.FUNDING: "funding",
    core.EventType.LIQUIDATION: "liquidation",
    core.EventType.CLOCK: "clock",
}
NOTICE_WORD = {
    core.EventType.ORDER_ACK: "accepted",
    core.EventType.ORDER_REJECT: "rejected",
    core.EventType.ORDER_FILL: "filled",
    core.EventType.ORDER_CANCELED: "canceled",
    core.EventType.ORDER_STATE_UNKNOWN: "state_unknown",
}


# --- scene dict -> core event ---------------------------------------------

def to_event(d: dict) -> core.Event:
    kind = d["kind"]
    times = {"exchange_time_ns": d["ts_ns"], "received_time_ns": d.get("recv_ns", d["ts_ns"])}
    if kind == "trade":
        return core.TradeEvent(**times, price=d["price"], size=d["qty"], side=d["side"])
    if kind == "book_snapshot":
        return core.BookSnapshotEvent(**times, bids=d["bids"], asks=d["asks"])
    if kind == "book_delta":
        return core.BookDeltaEvent(**times, side=d["side"], price=d["price"], size=d["qty"])
    if kind == "bar":
        return core.BarEvent(**times, open=d["open"], high=d["high"], low=d["low"],
                             close=d["close"], volume=d["volume"])
    if kind == "funding":
        return core.FundingEvent(**times, rate=d["rate"])
    if kind == "liquidation":
        return core.LiquidationEvent(**times, price=d["price"], size=d["qty"], side=d["side"])
    raise AssertionError(f"unknown scene kind {kind!r}")


def fields_back(e: core.Event) -> dict:
    """Event -> the scene's field names (size is called qty in the scenes)."""
    t = e.EVENT_TYPE
    if t is core.EventType.TRADE:
        return {"price": e.price, "qty": e.size, "side": e.side}
    if t is core.EventType.BOOK_SNAPSHOT:
        return {"bids": [list(x) for x in e.bids], "asks": [list(x) for x in e.asks]}
    if t is core.EventType.BOOK_DELTA:
        return {"side": e.side, "price": e.price, "qty": e.size}
    if t is core.EventType.BAR:
        return {"open": e.open, "high": e.high, "low": e.low, "close": e.close, "volume": e.volume}
    if t is core.EventType.FUNDING:
        return {"rate": e.rate}
    if t is core.EventType.LIQUIDATION:
        return {"price": e.price, "qty": e.size, "side": e.side}
    return {}


def events_of(scene) -> list[core.Event]:
    evs = scene.input["events"]
    # scenes whose events carry only a time: the core takes trades, so a trade
    # (price 100.0, size 0.01) is the type chosen (the scene allows any type)
    return [to_event(e if "kind" in e else {"kind": "trade", "price": 100.0, "qty": 0.01, "side": "buy", **e})
            for e in evs]


# --- plugs written outside the core, against the public protocols ---------

class CashAccount:
    """Spot cash account, no leverage: a buy whose notional at the last
    price the venue has seen (or its limit price) exceeds the cash is
    refused before it reaches the fill model."""

    def __init__(self, cash: float) -> None:
        self.cash = cash
        self.last: Optional[float] = None

    def apply_fill(self, fill):
        sign = 1.0 if fill.side == "buy" else -1.0
        self.cash -= sign * fill.price * fill.size + fill.fee

    def apply_funding(self, event):
        return None

    def apply_liquidation(self, event):
        return None

    def on_market_event(self, event, venue_time_ns):
        if event.EVENT_TYPE is core.EventType.TRADE:
            self.last = event.price
        return ()

    def check_order(self, order, venue_time_ns):
        if order.side != "buy":
            return None
        price = order.price if order.price is not None else self.last
        if price is None:
            return "no_price"
        return "insufficient_cash" if price * order.size > self.cash else None


class FixedPriceFill:
    """Fills every order in full, on arrival, at one fixed price."""

    def __init__(self, price: float) -> None:
        self.price = price

    def on_market_event(self, event, venue_time_ns):
        return ()

    def on_order(self, order, venue_time_ns):
        coid = order.client_order_id
        return (core.Ack(coid), core.Fill(coid, self.price, order.size))

    def on_cancel(self, request, venue_time_ns):
        return (core.Canceled(request.client_order_id),)


class OrderDelayOnly:
    def __init__(self, order_delay_ns: int) -> None:
        self.d = order_delay_ns

    def feed_delay_ns(self, event):
        return 0

    def order_delay_ns(self, order, sent_time_ns):
        return self.d

    def cancel_delay_ns(self, request, sent_time_ns):
        return 0

    def notice_delay_ns(self, report, venue_time_ns):
        return 0


class PerFillCost:
    def __init__(self, fee: float) -> None:
        self.fee = fee

    def cost(self, fill):
        return self.fee


class PerUnitCost:
    """A fee proportional to the filled size (price ignored)."""

    def __init__(self, per_unit: float) -> None:
        self.per_unit = per_unit

    def cost(self, fill):
        return self.per_unit * fill.size


class QtyRecordingAccount:
    def __init__(self) -> None:
        self.qty: list[float] = []

    def apply_fill(self, fill):
        self.qty.append(fill.size)

    def apply_funding(self, event):
        return None

    def apply_liquidation(self, event):
        return None

    def on_market_event(self, event, venue_time_ns):
        return ()

    def check_order(self, order, venue_time_ns):
        return None


# --- strategy --------------------------------------------------------------

class Probe(core.Strategy):
    """Records (kind, exchange time) of every market/clock event and the
    notices; calls `act(n, event, ctx)` on the n-th market-data call
    (1-based)."""

    def __init__(self, act: Optional[Callable] = None) -> None:
        self.act = act
        self.market_calls = 0
        self.seq: list[list] = []
        self.fields: list[dict] = []
        self.notices: list[core.Event] = []
        self.clock_calls: list[int] = []
        self.now: list[int] = []

    def on_event(self, event, ctx):
        t = event.EVENT_TYPE
        if t in NOTICE_WORD:
            self.notices.append(event)
            return
        if t is core.EventType.CLOCK:
            self.clock_calls.append(ctx.now_ns)
            return
        self.market_calls += 1
        self.seq.append([KIND_OF[t], event.exchange_time_ns])
        self.fields.append(fields_back(event))
        self.now.append(ctx.now_ns)
        if self.act is not None:
            self.act(self.market_calls, event, ctx)


def run(streams, act=None, **plugs) -> tuple[Probe, core.EngineResult]:
    plugs.setdefault("fill_model", ImmediateFillModel())
    plugs.setdefault("cost_model", core.NullCostModel())
    probe = Probe(act)
    res = core.CoreEngine(probe, streams, **plugs).run()
    return probe, res


def stream_map(scene, order=None) -> dict:
    order = order or scene.input["hand_over_order"]
    return {name: [to_event(e) for e in scene.input["streams"][name]] for name in order}


def market_buy(ctx, size=1.0) -> str:
    return ctx.place_order(core.OrderRequest(side="buy", order_type="market", size=size))


# --- one function per scene -------------------------------------------------

def s_sequence(scene):
    p, _ = run(events_of(scene))
    return {"sequence": p.seq}


def s_p1_merge_by_time(scene):
    p, _ = run(stream_map(scene))
    return {"sequence": p.seq}


def s_p2_iso(scene):
    return int(core.to_nanos(scene.input["iso"], "iso"))


def s_p2_observed(scene):
    p, _ = run(events_of(scene))
    return {"observed_ts_ns": p.now}


def s_p3_single(scene):
    p, _ = run(events_of(scene))
    return {"sequence": p.seq, "fields": p.fields[0] if p.fields else None}


def s_p3_clock_timer(scene):
    at = scene.input["timer_at_ns"]

    def act(n, e, ctx):
        if n == 1:
            ctx.set_timer(at, "wake")
    p, _ = run(events_of(scene), act)
    return {"clock_calls_ns": p.clock_calls}


def _notice_words(p):
    return [NOTICE_WORD[e.EVENT_TYPE] for e in p.notices]


def s_p3_notice_accepted(scene):
    def act(n, e, ctx):
        if n == 1:
            ctx.place_order(core.OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0))
    p, _ = run(events_of(scene), act)
    return {"notices": _notice_words(p)}


def s_p3_notice_rejected(scene):
    def act(n, e, ctx):
        if n == 1:
            market_buy(ctx)
    p, _ = run(events_of(scene), act, account=CashAccount(1_000.0))
    return {"notices": _notice_words(p)}


def s_p3_notice_filled(scene):
    def act(n, e, ctx):
        if n == 1:
            market_buy(ctx)
    p, _ = run(events_of(scene), act, account=CashAccount(1_000_000.0))
    return {"filled_qty_in_notices": sum(e.size for e in p.notices if e.EVENT_TYPE is core.EventType.ORDER_FILL)}


def s_p4_visible_at_step(scene):
    probe_at = scene.input["probe_at_ns"]
    got = {}

    def act(n, e, ctx):
        if ctx.now_ns == probe_at:
            bars = ctx.visible_events(core.EventType.BAR)
            got["visible_count"] = len(bars)
            got["max_visible_close"] = max(b.close for b in bars)
    run(events_of(scene), act)
    return got


def s_p4_received_time(scene):
    day, t0 = SC.DAY, SC.T0
    got = {}

    def seen_101(ctx):
        return any(e.price == 101.0 for e in ctx.visible_events(core.EventType.TRADE))

    def act(n, e, ctx):
        if e.price == 101.0:
            got["price101_delivered_at_ns"] = ctx.now_ns
        if ctx.now_ns == t0 + 2 * day:
            got["price101_visible_at_day2"] = seen_101(ctx)
        if ctx.now_ns == t0 + 4 * day:
            got["price101_visible_at_day4"] = seen_101(ctx)
    run(events_of(scene), act)
    return got


def s_p4_future_read_attempt(scene):
    """Every public read of the context that can NAME the 5th bar, by time
    (a window ending at or starting at its time, or just after now) or by
    position (the next index, a slice through it), plus reads that do not
    name it ("other": everything, the last bar). Each attempt is recorded
    as the scene asks: means, form, the exception's name or the value."""
    probe_at = scene.input["probe_at_ns"]
    fut = scene.input["future_ts_ns"]
    bar = core.EventType.BAR
    attempts: list[dict] = []

    def attempt(means, form, fn):
        try:
            value = fn()
        except Exception as exc:  # noqa: BLE001 - the exception is the observation
            attempts.append({"means": means, "form": form, "raised": type(exc).__name__, "returned": None})
        else:
            attempts.append({"means": means, "form": form, "raised": None, "returned": value})

    def closes(evs):
        return [e.close if e.EVENT_TYPE is bar else getattr(e, "price", None) for e in evs]

    def act(n, e, ctx):
        if ctx.now_ns != probe_at or attempts:
            return
        attempt("visible_events(BAR, until_ns=5th)", "time",
                lambda: closes(ctx.visible_events(bar, until_ns=fut)))
        attempt("visible_events(BAR, since_ns=5th)", "time",
                lambda: closes(ctx.visible_events(bar, since_ns=fut)))
        attempt("visible_events(BAR, since_ns=now+1)", "time",
                lambda: closes(ctx.visible_events(bar, since_ns=probe_at + 1)))
        attempt("visible_events(until_ns=5th)", "time",
                lambda: closes(ctx.visible_events(until_ns=fut)))
        # position 4 is the 5th bar ("今の最新の次の位置"); named through every
        # role a position can have (window.py POSITION_RULE): an index, the
        # start of a forward slice, the end of a forward slice past the end,
        # the start of a backward slice, the old-side end of a backward
        # slice, and a slice of a slice (i0-r4-01: [4:] was answered with ())
        attempt("visible_events(BAR)[4]", "position", lambda: ctx.visible_events(bar)[4].close)
        attempt("visible_events()[4]", "position", lambda: ctx.visible_events()[4].close)
        attempt("visible_events(BAR, n=5)[4]", "position", lambda: ctx.visible_events(bar, n=5)[4].close)
        attempt("visible_events(BAR)[4:]", "position", lambda: closes(ctx.visible_events(bar)[4:]))
        attempt("visible_events()[4:]", "position", lambda: closes(ctx.visible_events()[4:]))
        attempt("visible_events(BAR)[4::2]", "position", lambda: closes(ctx.visible_events(bar)[4::2]))
        attempt("visible_events(BAR)[len:]", "position",
                lambda: closes(ctx.visible_events(bar)[len(ctx.visible_events(bar)):]))
        attempt("visible_events(BAR)[4:5]", "position", lambda: closes(ctx.visible_events(bar)[4:5]))
        attempt("visible_events(BAR)[3:5]", "position", lambda: closes(ctx.visible_events(bar)[3:5]))
        attempt("visible_events(BAR)[:5]", "position", lambda: closes(ctx.visible_events(bar)[:5]))
        attempt("visible_events(BAR)[4::-1]", "position", lambda: closes(ctx.visible_events(bar)[4::-1]))
        attempt("visible_events(BAR)[:4:-1]", "position", lambda: closes(ctx.visible_events(bar)[:4:-1]))
        attempt("visible_events(BAR)[1:][3:]", "position", lambda: closes(ctx.visible_events(bar)[1:][3:]))
        attempt("visible_events()", "other", lambda: closes(ctx.visible_events()))
        attempt("last(BAR)", "other", lambda: ctx.last(bar).close)
    run(events_of(scene), act)
    return {"attempts": attempts}


def _rule_applied_by_hand(streams: dict) -> list:
    """The core's written rule for same-time input from different streams
    (ORDERING_RULE["source_merge"]: exchange time, then the type order,
    then the stream name), applied to the scene's streams (one event per
    stream here). Read from the rule, not from a run."""
    rule = core.ORDERING_RULE["source_merge"]
    assert rule["compare_heads_by"] == ["exchange_time_ns", "TYPE_ORDER", "stream name (sorted())"]
    type_order = [v.lower() for v in rule["type_order"]]  # EventType values -> scene kinds
    rows = sorted((e["ts_ns"], type_order.index(e["kind"]), name, e["kind"])
                  for name, evs in streams.items() for e in evs)
    return [[k, t] for t, _r, _n, k in rows]


def _order_once(scene, order) -> list:
    p, _ = run(stream_map(scene, list(order)))
    return [[k, t] for k, t in p.seq]


def s_p5_same_time_twice(scene):
    return {"order": _order_once(scene, scene.input["hand_over_order"])}


def s_p5_hand_over_order(scene):
    runs = [{"hand_over": list(o), "order": _order_once(scene, o)} for o in scene.input["hand_over_orders"]]
    return {"form": "multi_input", "runs": runs}


def s_p5_same_stream_order(scene):
    p, _ = run(events_of(scene))
    return {"prices": [f["price"] for f in p.fields]}


def s_p6_place_then_cancel(scene):
    got, ids = {}, {}

    def act(n, e, ctx):
        if n == 1:
            ids["o"] = ctx.place_order(core.OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0))
        elif n == 2:
            got["open_at_call2"] = len(ctx.open_orders())
            ctx.cancel_order(ids["o"])
        elif n == 3:
            got["open_at_call3"] = len(ctx.open_orders())
    run(events_of(scene), act)
    return got


def s_p6_cancel_notice(scene):
    ids = {}

    def act(n, e, ctx):
        if n == 1:
            ids["o"] = ctx.place_order(core.OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0))
        elif n == 2:
            ctx.cancel_order(ids["o"])
    p, _ = run(events_of(scene), act)
    return {"cancel_notice_received": any(e.EVENT_TYPE is core.EventType.ORDER_CANCELED for e in p.notices)}


def s_p6_fill_seen(scene):
    got, ids = {}, {}

    def act(n, e, ctx):
        if n == 1:
            ids["o"] = market_buy(ctx)
        elif n == 3:
            got["filled_qty_at_call3"] = ctx.order(ids["o"]).filled_size
    run(events_of(scene), act, account=CashAccount(1_000_000.0))
    return got


def _buy_first(n, e, ctx):
    if n == 1:
        market_buy(ctx)


def _fills(p):
    return [e for e in p.notices if e.EVENT_TYPE is core.EventType.ORDER_FILL]


def s_p7_fill_model_swap(scene):
    p, _ = run(events_of(scene), _buy_first, fill_model=FixedPriceFill(12345.0), account=CashAccount(100_000.0))
    return {"fill_price": _fills(p)[0].price}


def s_p7_latency_model_swap(scene):
    p, _ = run(events_of(scene), _buy_first, latency_model=OrderDelayOnly(7 * SC.MS), account=CashAccount(100_000.0))
    return {"fill_time_ns": _fills(p)[0].exchange_time_ns, "notice_received_ns": _fills(p)[0].received_time_ns}


def s_p7_cost_model_swap(scene):
    p, _ = run(events_of(scene), _buy_first, cost_model=PerFillCost(0.5), account=CashAccount(100_000.0))
    return {"fee": _fills(p)[0].fee}


def s_p7_cost_per_unit(scene):
    def buy_two(n, e, ctx):
        if n == 1:
            market_buy(ctx, size=2.0)
    p, _ = run(events_of(scene), buy_two, cost_model=PerUnitCost(0.375), account=CashAccount(100_000.0))
    return {"fee": sum(f.fee for f in _fills(p)), "fills": len(_fills(p))}


def s_p7_account_swap(scene):
    acct = QtyRecordingAccount()
    run(events_of(scene), _buy_first, account=acct)
    return {"account_recorded_fill_qty": acct.qty}


DRIVERS: dict[str, Callable] = {
    "p1-merge-by-time": s_p1_merge_by_time,
    "p1-one-call-per-event": s_sequence,
    "p1-typed-events": s_sequence,
    "p2-iso-utc": s_p2_iso,
    "p2-iso-offset": s_p2_iso,
    "p2-event-time-exact": s_p2_observed,
    "p2-one-ns-apart": s_p2_observed,
    **{f"p3-{k}": s_p3_single for k in ("trade", "book_snapshot", "book_delta", "bar", "funding", "liquidation")},
    "p3-mixed-one-run": s_sequence,
    "p3-clock-timer": s_p3_clock_timer,
    "p3-notice-accepted": s_p3_notice_accepted,
    "p3-notice-rejected": s_p3_notice_rejected,
    "p3-notice-filled": s_p3_notice_filled,
    "p4-visible-at-step": s_p4_visible_at_step,
    "p4-received-time": s_p4_received_time,
    "p4-future-read-attempt": s_p4_future_read_attempt,
    "p5-same-time-twice": s_p5_same_time_twice,
    "p5-hand-over-order": s_p5_hand_over_order,
    "p5-same-stream-order": s_p5_same_stream_order,
    "p6-place-then-cancel": s_p6_place_then_cancel,
    "p6-cancel-notice": s_p6_cancel_notice,
    "p6-fill-seen-by-strategy": s_p6_fill_seen,
    "p7-fill-model-swap": s_p7_fill_model_swap,
    "p7-latency-model-swap": s_p7_latency_model_swap,
    "p7-cost-model-swap": s_p7_cost_model_swap,
    "p7-cost-per-unit": s_p7_cost_per_unit,
    "p7-account-swap": s_p7_account_swap,
}


_TARGET = "new_impl"  # the battery's name for this core (stated_rules.py)


def _graded(scene, output):
    """What the battery runner grades for this output (run_battery.py), for
    this core as the target."""
    return run_battery.graded_output(SceneResult("ok", output), scene, _TARGET)


def _matches(scene, output) -> bool:
    return run_battery._matches(_graded(scene, output), scene.expected)


def test_the_scene_keepers_copy_of_the_same_time_rule_is_the_cores_rule_applied_by_hand():
    """stated_rules.py (the scene keeper's copy of this core's same-time
    rule) and ORDERING_RULE["source_merge"] applied by hand give the same
    order, for every hand-over order of the P0-5 scenes."""
    import stated_rules  # noqa: E402  (the battery's; read, never changed)
    rule = stated_rules.rule_for(_TARGET)
    for scene_id in ("p5-same-time-twice", "p5-hand-over-order"):
        scene = SCENES[scene_id]
        orders = scene.input.get("hand_over_orders") or [scene.input["hand_over_order"]]
        for hand_over in orders:
            assert stated_rules.predicted(rule, scene.input["streams"], list(hand_over)) == \
                _rule_applied_by_hand(scene.input["streams"]), (scene_id, hand_over)


def test_graders_are_the_runners_for_exactly_the_graded_from_scenes():
    assert set(run_battery.GRADERS) == {s.id for s in SC.SCENES if s.graded_from}


def test_every_scene_has_a_driver():
    assert set(DRIVERS) == set(SCENES), sorted(set(DRIVERS) ^ set(SCENES))


@pytest.mark.parametrize("scene_id", sorted(SCENES))
def test_scene_matches_expected_twice(scene_id):
    scene = SCENES[scene_id]
    out1 = DRIVERS[scene_id](scene)
    out2 = DRIVERS[scene_id](scene)
    assert _matches(scene, out1), (_graded(scene, out1), scene.expected)
    assert json.dumps(out1, sort_keys=True, default=repr) == json.dumps(out2, sort_keys=True, default=repr)


def test_future_read_attempts_are_refused_not_shortened():
    """p4-future-read-attempt: every read that names the 5th bar -- by time
    (`until_ns` / `since_ns` after now) or by position (an index or a slice
    bound past the newest) -- is refused with an exception, never answered
    with a shortened or empty result (REQUIREMENTS.md P0-4: stops with a
    runtime error; i0-r1-08); the reads that do not name it return only
    bars 100..103."""
    out = s_p4_future_read_attempt(SCENES["p4-future-read-attempt"])
    by = {a["means"]: a for a in out["attempts"]}
    for means, a in by.items():
        if a["form"] == "time":
            assert a["raised"] == "LookAheadError", a
        elif a["form"] == "position":
            assert a["raised"] == "FuturePositionError", a
    assert by["visible_events()"]["returned"] == [100.0, 101.0, 102.0, 103.0]
    assert by["last(BAR)"]["returned"] == 103.0
    assert issubclass(core.FuturePositionError, IndexError)
    assert issubclass(core.FuturePositionError, core.LookAheadError)


def test_hand_over_order_of_streams_does_not_matter_but_one_stream_keeps_its_order():
    """p5-hand-over-order: the 4 same-time events as 4 named streams handed
    over in each of the 24 orders give ONE order (the head-type merge).
    The same 4 events concatenated into ONE stream keep that stream's own
    order (i0-r1-10: a stream is never re-sorted by type), so the 24
    concatenations give exactly the 24 concatenation orders."""
    scene = SCENES["p5-hand-over-order"]
    by_mapping, by_concat = set(), set()
    for order in itertools.permutations(scene.input["streams"]):
        streams = {name: [to_event(e) for e in scene.input["streams"][name]] for name in order}
        p, _ = run(streams)
        by_mapping.add(tuple(k for k, _ in p.seq))
        evs = [e for name in order for e in streams[name]]
        p, _ = run(evs)
        got = tuple(k for k, _ in p.seq)
        assert got == tuple(scene.input["streams"][name][0]["kind"] for name in order)
        by_concat.add(got)
    assert len(by_mapping) == 1
    assert len(by_concat) == 24

"""動作確認 on real crypto data (REQUIREMENTS, old item 3: "列の模型は暗号資産の
実データと合成データで検証し"). Purpose: 動作確認 only -- this test asserts
invariants of the fill models on a real stream and reports no number; its
counts are not results and are not written anywhere (delegation section 4).

Data: the bitFlyer FX_BTC_JPY tape tracked in the repository
(docs/DATA.md: paper_logs/tape board_top10 1-second snapshots and
executions), 2026-09-20 01:00-01:20 UTC. The procedure is fixed by time only
(delegation section 4 "動作確認用の固定の手順"): every 60 s a buy limit joins
the displayed best bid and a sell limit joins the best ask (size 0.01), and
both are cancelled 30 s later if still open. No signal, no condition, no
optimisation.

Invariants, per fill model {tier 1, 3, 4, 5 none, 5 snapshot_cap, 5 prob}:
- the run completes (the core checks every venue report against the order's
  history: no fill before its ack, no overfill, nothing after a final state);
- every fill is at the order's limit, as the maker, while the order rested;
- tiers 4 and 5 never fill more than the prints at or through the price
  during the order's life (tier 4: each print up to its size; tier 5 a print
  at the price after what is ahead; a print through fills the rest);
- per order: tier 1 <= tier 3 (a cross is a touch), tier 4 <= tier 3, and in
  tier 5 none <= snapshot_cap and none <= prob (both only lower what is
  ahead);
- the range (optimistic tier 3, pessimistic tier 1) is ordered;
- two runs give the same fills.
"""
from __future__ import annotations

import csv
import gzip
from datetime import datetime, timezone
from pathlib import Path

import pytest

from bot.bt.core import BookSnapshotEvent, ClockEvent, CoreEngine, EventType, Strategy, TradeEvent
from bot.bt.costs import CostSchedule, ScheduleCostModel
from bot.bt.fill import FillRange, FillSpec, SimVenue, run_range
from bot.bt.latency import Constant, LatencyModel
from bot.bt.orders import FaultPlan, KillSwitch, OrderClient, Product, VenueRules

REPO = Path(__file__).resolve().parents[3]
TAPE = REPO / "paper_logs" / "tape"
DAY = "20260920"
START, END = "2026-09-20T01:00", "2026-09-20T01:20"
SEC = 1_000_000_000


def _ns(ts: str) -> int:
    ts = ts.rstrip("Z")
    head, _, frac = ts.partition(".")
    base = int(datetime.fromisoformat(head).replace(tzinfo=timezone.utc).timestamp()) * SEC
    return base + int((frac + "000000000")[:9]) if frac else base


def _load():
    board, prints = TAPE / f"board_top10_{DAY}.csv.gz", TAPE / f"executions_{DAY}.csv.gz"
    if not (board.exists() and prints.exists()):
        pytest.skip(f"the tape files are not in this checkout ({board.name}, {prints.name}); 動作確認 not run")
    books, trades = [], []
    with gzip.open(board, "rt", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["ts"] < START:
                continue
            if row["ts"] >= END:
                break
            bids = [(float(row[f"bid_px_{i}"]), float(row[f"bid_sz_{i}"])) for i in range(1, 11) if row[f"bid_px_{i}"]]
            asks = [(float(row[f"ask_px_{i}"]), float(row[f"ask_sz_{i}"])) for i in range(1, 11) if row[f"ask_px_{i}"]]
            books.append(BookSnapshotEvent(received_time_ns=_ns(row["ts"]), bids=bids, asks=asks))
    with gzip.open(prints, "rt", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["ts"] < START:
                continue
            if row["ts"] >= END:
                break
            trades.append(TradeEvent(received_time_ns=_ns(row["ts"]), price=float(row["price"]),
                                     size=float(row["size"]), side=row["side"].lower()))
    t0 = _ns(START + ":00")
    clocks = [ClockEvent(received_time_ns=t0 + k * 30 * SEC, tag="quote" if k % 2 == 0 else "cancel")
              for k in range(1, 40)]
    return {"books": books, "trades": trades, "clock": clocks}


class _Quoter(Strategy):
    """Every "quote" clock: join the best bid and the best ask with 0.01;
    every "cancel" clock: cancel what is still open."""

    def __init__(self, client):
        self.client = client
        self.n = 0
        self.orders = {}  # ref -> (side, price, rest time, cancel time)

    def on_event(self, event, ctx):
        self.client.observe(event, ctx)
        if event.EVENT_TYPE is not EventType.CLOCK:
            return
        if event.tag == "quote":
            bk = ctx.last(EventType.BOOK_SNAPSHOT)
            if bk is None or not bk.bids or not bk.asks:
                return
            for side, px in (("buy", bk.bids[0][0]), ("sell", bk.asks[0][0])):
                self.n += 1
                ref = f"q{self.n}"
                self.client.place(ctx, ref=ref, side=side, order_type="limit", size=0.01, price=px)
                self.orders[ref] = [side, px, ctx.now_ns, None]
        else:
            for ref, rec in self.orders.items():
                if rec[3] is None:
                    view = ctx.order(ref)
                    if view is not None and view.is_open:
                        self.client.cancel(ctx, ref)
                    rec[3] = ctx.now_ns


PRODUCT = Product("FX_BTC_JPY", "bitflyer_cfd", 1.0, 0.001, 1e-8, "JPY", True)
COSTS = CostSchedule(maker_rate=0.0, taker_rate=0.0, source="動作確認: zero costs stated (no cost is measured here)")
SPECS = {"t1": FillSpec(tier=1), "t3": FillSpec(tier=3), "t4": FillSpec(tier=4),
         "t5none": FillSpec(tier=5, cancel_stance="none"), "t5cap": FillSpec(tier=5, cancel_stance="snapshot_cap"),
         "t5prob": FillSpec(tier=5, cancel_stance="prob", prob_f="power", prob_n=1)}


def _run(data, spec):
    venue = SimVenue(product=PRODUCT, rules=VenueRules(off_tick="reject", below_min_qty="reject",
                                                       post_only="reject_if_crossing", market_remainder="cancel"),
                     fill=spec, costs=COSTS, faults=FaultPlan(()), l3=None)
    client = OrderClient(KillSwitch(None))
    strat = _Quoter(client)
    eng = CoreEngine(strat, data, venue,
                     LatencyModel(feed=Constant(0), order=Constant(0), cancel=Constant(0), notice=Constant(0)),
                     ScheduleCostModel(COSTS, product=PRODUCT, account_currency="JPY", fx=None), None)
    result = eng.run()
    per = {}
    for f in result.fills:
        per.setdefault(f.client_order_id, []).append(f)
    return strat, result, per


@pytest.fixture(scope="module")
def data():
    return _load()


@pytest.fixture(scope="module")
def runs(data):
    return {name: _run(data, spec) for name, spec in SPECS.items()}


def _volume_bound(trades, side, px, t_from, t_to):
    """Prints at or through `px` in (t_from, t_to]."""
    total = 0.0
    for tr in trades:
        t = tr.received_time_ns
        if t_from < t <= t_to and (tr.price <= px if side == "buy" else tr.price >= px):
            total += tr.size
    return total


def test_quotes_were_placed(runs):
    strat, result, _ = runs["t1"]
    assert strat.n > 20 and len(result.order_requests) == strat.n


def test_fills_are_at_the_limit_as_maker_while_resting(runs):
    for name, (strat, _result, per) in runs.items():
        assert per, f"{name}: no fill at all -- the invariants below would hold vacuously"
        for ref, fills in per.items():
            side, px, t_rest, t_cancel = strat.orders[ref]
            for f in fills:
                assert f.price == px and f.liquidity == "maker", name
                assert t_rest < f.venue_time_ns and (t_cancel is None or f.venue_time_ns <= t_cancel), name
            assert sum(f.size for f in fills) <= 0.01 + 1e-12


def test_volume_bounds(runs, data):
    for name in ("t4", "t5none", "t5cap", "t5prob"):
        strat, _result, per = runs[name]
        for ref, fills in per.items():
            side, px, t_rest, t_cancel = strat.orders[ref]
            end = t_cancel if t_cancel is not None else float("inf")
            through = [tr for tr in data["trades"] if t_rest < tr.received_time_ns <= end
                       and (tr.price < px if side == "buy" else tr.price > px)]
            if through and name != "t4":
                continue  # a print through fills the rest in tier 5, whatever its size
            assert sum(f.size for f in fills) <= _volume_bound(data["trades"], side, px, t_rest, end) + 1e-12, name


def test_per_order_dominance(runs):
    got = {name: {ref: sum(f.size for f in fs) for ref, fs in per.items()} for name, (_s, _r, per) in runs.items()}
    refs = set(runs["t1"][0].orders)
    for ref in refs:
        g = {name: got[name].get(ref, 0.0) for name in got}
        assert g["t1"] <= g["t3"] + 1e-12
        assert g["t4"] <= g["t3"] + 1e-12
        assert g["t5none"] <= g["t5cap"] + 1e-12
        assert g["t5none"] <= g["t5prob"] + 1e-12


def test_range_and_repeat(data):
    rr = run_range(lambda spec: sum(f.size for f in _run(data, spec)[1].fills),
                   FillRange(optimistic=SPECS["t3"], pessimistic=SPECS["t1"]))
    assert rr.pessimistic <= rr.optimistic
    a, b = _run(data, SPECS["t5prob"])[1], _run(data, SPECS["t5prob"])[1]
    key = lambda r: [(f.client_order_id, f.venue_time_ns, f.price, f.size) for f in r.fills]  # noqa: E731
    assert key(a) == key(b)

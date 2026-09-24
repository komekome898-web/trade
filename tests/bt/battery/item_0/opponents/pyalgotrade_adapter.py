"""Survey candidate 122 `gbeced/pyalgotrade` (PyPI `pyalgotrade` 0.20), run in its own venv.

Driven through its public API: `barfeed.membf.BarFeed` with `bar.BasicBar`
(bars in memory), `strategy.BacktestingStrategy` (`onBars`, `onOrderUpdated`,
`marketOrder`, `limitOrder`, `getBroker().cancelOrder`, `getActiveOrders`,
`getCurrentDateTime`), the backtesting broker's plug points
`setFillStrategy(FillStrategy subclass)` and
`setCommission(backtesting.FixedPerTrade)`. PyAlgoTrade's time type is
`datetime.datetime`.
Installing: the first attempt failed while the disk was full; the retry
succeeded (install log).
"""
from __future__ import annotations

import datetime as D
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

import logging  # noqa: E402

from protocol import Adapter, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

from pyalgotrade import bar, strategy  # noqa: E402
from pyalgotrade.barfeed import membf  # noqa: E402
from pyalgotrade.broker import backtesting, fillstrategy  # noqa: E402
from pyalgotrade import broker as pbroker  # noqa: E402

logging.disable(logging.CRITICAL)
INST = "X"
STATE = {pbroker.Order.State.ACCEPTED: "accepted", pbroker.Order.State.FILLED: "filled",
         pbroker.Order.State.CANCELED: "canceled", pbroker.Order.State.PARTIALLY_FILLED: "filled"}


class _MemFeed(membf.BarFeed):
    """membf.BarFeed leaves barsHaveAdjClose abstract; the in-memory feed says its bars carry adjClose."""

    def barsHaveAdjClose(self):
        return True


def _feed(bars):
    # round r8-1 (positive definition A (1)): the settings through common.configure (the feed and its bars)
    rows = [C.as_bar(b) for b in bars]
    f = C.configure(_MemFeed, bar.Frequency.DAY, what="membf.BarFeed(Frequency.DAY)(adjClose を持つと言う子)", decided_from=("選ぶ値",))
    C.configure(f.addBarsFromSequence, INST, [bar.BasicBar(C.ns_to_dt(b["ts_ns"]).replace(tzinfo=None), b["open"], b["high"], b["low"],
                                                            b["close"], b.get("volume", 1.0), b["close"], bar.Frequency.DAY) for b in rows],
                what="addBarsFromSequence(銘柄, 場面の足)", decided_from=("場面の入力",))
    return f


def run(bars, fn, cash=1_000_000.0, setup=None):
    feed = _feed(bars)
    st = {"n": 0, "log": [], "notices": [], "fills": [], "events": []}

    class S(strategy.BacktestingStrategy):
        def __init__(self):
            super().__init__(feed, cash)

        def onBars(self, bars_):
            st["n"] += 1
            fn(self, bars_, st["n"], st)

        def onOrderUpdated(self, order):
            st["events"].append(str(order.getState()))
            name = STATE.get(order.getState())
            if name:
                st["notices"].append(name)
            if order.getState() in (pbroker.Order.State.FILLED, pbroker.Order.State.PARTIALLY_FILLED):
                ex = order.getExecutionInfo()
                st["fills"].append({"price": ex.getPrice(), "qty": ex.getQuantity(), "commission": ex.getCommission(),
                                    "dt": str(ex.getDateTime())})

    s = C.configure(S, what=f"BacktestingStrategy(feed, {cash})", decided_from=("場面の入力",))
    if setup:
        setup(s.getBroker())
    s.run()
    return st, s


def _now(s) -> int:
    return C.dt_to_ns(s.getCurrentDateTime().replace(tzinfo=D.timezone.utc))


NON = "PyAlgoTrade のデータは bar feed(足)だけで、{k} の型は無い。試したこと: {err}"


def _try_non_bar(e: dict) -> str:
    try:
        f = _MemFeed(bar.Frequency.TRADE)
        f.addBarsFromSequence(INST, [dict(C.fields_of(e))])
        strategy.BacktestingStrategy(f, 1000).run()
    except Exception as exc:  # noqa: BLE001
        return f"membf.BarFeed.addBarsFromSequence に {sorted(C.fields_of(e))} の辞書を渡して走らせた -> {type(exc).__name__}: {str(exc)[:160]}"
    return "例外なく走った"


class PyalgotradeAdapter(Adapter):
    # round r8-1 (positive definition A): the values this configured target chooses, the same in every scene
    CONFIGS = {"": {"frequency": "DAY"}}
    name = "opp_pyalgotrade"

    def scene_p1_merge_by_time(self, sc):
        return not_supported(NON.format(k="約定・資金調達", err=_try_non_bar(sc.input["streams"]["trades"][0])))

    def scene_p1_one_call_per_event(self, sc):
        car = []
        st, _ = run(C.events(sc), lambda s, b, n, st: (st["log"].append(["bar", _now(s)]), car.append(C.carrier(b[INST]))))
        return ok({"sequence": st["log"]}, "足 5 本。onBars の各回に getCurrentDateTime()", {"carriers": car})

    def scene_p1_typed_events(self, sc):
        return not_supported(NON.format(k="約定", err=_try_non_bar(C.events(sc)[1])))

    def _iso(self, sc):
        """The ISO string written as it is into the Date Time column of a CSV read by PyAlgoTrade's own
        CSV bar feed (`pyalgotrade.barfeed.csvfeed.GenericBarFeed.addBarsFromCSV`)."""
        import tempfile
        from pyalgotrade.barfeed import csvfeed
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "X.csv"
            path.write_text(f"Date Time,Open,High,Low,Close,Volume,Adj Close\n{sc.input['iso']},1,1,1,1,1,1\n", encoding="utf-8")
            feed = csvfeed.GenericBarFeed(bar.Frequency.DAY)
            try:
                feed.addBarsFromCSV(INST, str(path))
                dt = feed.getNextBars()[INST].getDateTime()
            except Exception as exc:  # noqa: BLE001
                return not_supported("ISO の文字列を Date Time の列に書いた CSV を GenericBarFeed.addBarsFromCSV で読んだ(既定の書式 "
                                     f"'%Y-%m-%d %H:%M:%S')-> {type(exc).__name__}: {str(exc)[:160]}")
        d_ = dt if dt.tzinfo is not None else dt.replace(tzinfo=D.timezone.utc)
        return ok(C.dt_to_ns(d_), f"GenericBarFeed が読んだ足の時刻 {dt!r}", {"reader": C.qualname(csvfeed.GenericBarFeed.addBarsFromCSV)})

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    def _ts(self, sc):
        evs = [{"kind": "trade", "ts_ns": e["ts_ns"], "price": 100.0} for e in C.events(sc)]
        car = []
        try:
            st, _ = run(evs, lambda s, b, n, st: (st["log"].append(_now(s)), car.append(C.carrier(b[INST]))))
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"足で渡して走らせた -> {type(exc).__name__}: {str(exc)[:200]}")
        return ok({"observed_ts_ns": st["log"]}, "足で渡し(datetime はマイクロ秒まで)、getCurrentDateTime()", {"carriers": car})

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _ts

    def _type(self, sc):
        e = C.events(sc)[0]
        if e["kind"] != "bar":
            return not_supported(NON.format(k=e["kind"], err=_try_non_bar(e)))
        out = {}
        car = []

        def f(s, b, n, st):
            st["log"].append(["bar", _now(s)])
            x = b[INST]
            car.append(C.carrier(x))
            out.update({"open": x.getOpen(), "high": x.getHigh(), "low": x.getLow(), "close": x.getClose(), "volume": x.getVolume()})

        st, _ = run([e], f)
        return ok({"sequence": st["log"], "fields": out}, "足 1 本。onBars の bars[銘柄]", {"carriers": car})

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = _type

    def scene_p3_mixed_one_run(self, sc):
        return not_supported(NON.format(k="足以外の 5 種", err=_try_non_bar(C.events(sc)[0])))

    def scene_p3_clock_timer(self, sc):
        names = [n for n in dir(strategy.BacktestingStrategy) if "timer" in n.lower() or "schedule" in n.lower()]
        return not_supported(f"時刻を頼んで呼ばれる口が無い(onIdle は事象が無いときに呼ぶだけで時刻を頼めない。timer/schedule の名前: {names})。"
                             "試したこと: " + self._try_attr("addTimer"))

    def _try_attr(self, name):
        class S(strategy.BacktestingStrategy):
            def onBars(self, bars_):
                pass

        s = S(_feed([{"kind": "bar", "ts_ns": 1_700_092_800_000_000_000, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}]), 1)
        try:
            getattr(s, name)(object())
        except Exception as exc:  # noqa: BLE001
            return f"strategy.{name}(...) -> {type(exc).__name__}: {exc}"
        return f"strategy.{name}(...) は受け付けた"

    def _bars(self, sc):
        return [C.as_bar(e) for e in C.events(sc)]

    def scene_p3_notice_accepted(self, sc):
        st, _ = run(self._bars(sc), lambda s, b, n, st: s.limitOrder(INST, 90.0, 1, goodTillCanceled=True) if n == 1 else None)
        return ok({"notices": st["notices"]}, f"約定を足に代えた(any_type)。onOrderUpdated の状態の列(SUBMITTED は数えない): {st['events']}")

    def scene_p3_notice_rejected(self, sc):
        st, _ = run(self._bars(sc), lambda s, b, n, st: s.marketOrder(INST, 1) if n == 1 else None, cash=1_000)
        return ok({"notices": st["notices"]}, f"現金 1,000。成行 1。onOrderUpdated の状態: {st['events']}")

    def scene_p3_notice_filled(self, sc):
        st, _ = run(self._bars(sc), lambda s, b, n, st: s.marketOrder(INST, 1) if n == 1 else None)
        return ok({"filled_qty_in_notices": float(sum(f["qty"] for f in st["fills"])), "notices": st["notices"]}, f"fills={st['fills']}")

    def scene_p4_visible_at_step(self, sc):
        probe = sc.input["probe_at_ns"]
        reads = C.Reads()

        def f(s, b, n, st):
            if _now(s) == probe and not reads.items:
                reads.read("getFeed()[銘柄].getCloseDataSeries()", lambda: list(s.getFeed()[INST].getCloseDataSeries()))

        run(C.events(sc), f)
        if not reads.items:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった")
        return ok(reads.output(), "T0 + 4 日の onBars で getFeed()[銘柄].getCloseDataSeries() を読んだ", reads.provenance())

    def scene_p4_received_time(self, sc):
        return not_supported(NON.format(k="受け取れる時刻", err=_try_non_bar({"ts_ns": 0, "open": 1.0, "recv_ns": 1})) + "(1 本の足に時刻は 1 つ)")

    def scene_p4_future_read_attempt(self, sc):
        probe = sc.input["probe_at_ns"]
        att = C.Attempts()

        def f(s, b, n, st):
            if _now(s) != probe or att.items:
                return
            ds = s.getFeed()[INST].getCloseDataSeries()
            # namings: the scene's fixed list
            C.try_position_namings(att, "close の系列[位置]", lambda: ds, len(ds))
            att.run("feed.peekDateTime()(次を覗く)", "position", lambda: s.getFeed().peekDateTime(), shape="next_call", naming="next")
            att.run("feed.getNextBars()(次を覗く、公開の方法)の終値", "position",
                    lambda: (lambda nb: nb[INST].getClose() if nb is not None else None)(s.getFeed().getNextBars()),
                    shape="next_call", naming="next")
            att.run("close の系列の全部", "other", lambda: [ds[i] for i in range(len(ds))])

        run(C.events(sc), f)
        if not att.items:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった")
        return ok(att.output(), "T0 + 4 日の onBars で試した: " + att.summary())

    def _no_types(self, sc):
        return not_supported(NON.format(k="約定・資金調達・清算", err=_try_non_bar(sc.input["streams"]["trades"][0])))

    scene_p5_same_time_twice = scene_p5_hand_over_order = _no_types

    def scene_p5_same_stream_order(self, sc):
        car = []
        try:
            st, _ = run(self._bars(sc), lambda s, b, n, st: (st["log"].append(b[INST].getClose()), car.append(C.carrier(b[INST]))))
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"同じ時刻の 3 本を bar feed に入れて走らせた -> {type(exc).__name__}: {str(exc)[:200]}")
        return ok({"prices": st["log"]}, "同じ時刻の 3 本を 1 つの bar feed に入れた", {"carriers": car})

    def scene_p6_place_then_cancel(self, sc):
        out = {}

        def f(s, b, n, st):
            if n == 1:
                st["o"] = s.limitOrder(INST, 90.0, 1, goodTillCanceled=True)
            elif n == 2:
                out["open_at_call2"] = len(s.getBroker().getActiveOrders())
                s.getBroker().cancelOrder(st["o"])
            elif n == 3:
                out["open_at_call3"] = len(s.getBroker().getActiveOrders())

        run(self._bars(sc), f)
        return ok(out, "limitOrder / broker.getActiveOrders / broker.cancelOrder")

    def scene_p6_cancel_notice(self, sc):
        def f(s, b, n, st):
            if n == 1:
                st["o"] = s.limitOrder(INST, 90.0, 1, goodTillCanceled=True)
            elif n == 2:
                s.getBroker().cancelOrder(st["o"])

        st, _ = run(self._bars(sc), f)
        return ok({"cancel_notice_received": "canceled" in st["notices"], "notices": st["notices"]}, f"onOrderUpdated: {st['events']}")

    def scene_p6_fill_seen_by_strategy(self, sc):
        out = {}

        def f(s, b, n, st):
            if n == 1:
                st["o"] = s.marketOrder(INST, 1)
            elif n == 3:
                out["filled_qty_at_call3"] = float(st["o"].getFilled())

        run(self._bars(sc), f)
        return ok(out, "3 回目に order.getFilled()")

    def _buy(self, sc, setup, qty: int = 1):
        return run(self._bars(sc), lambda s, b, n, st: s.marketOrder(INST, qty) if n == 1 else None, cash=100_000, setup=setup)[0]

    def scene_p7_fill_model_swap(self, sc):
        class Fixed(fillstrategy.DefaultStrategy):
            def fillMarketOrder(self, broker_, order, bar_):
                return fillstrategy.FillInfo(12345.0, order.getQuantity())

        st = self._buy(sc, lambda br: C.configure(br.setFillStrategy, Fixed(), what="broker.setFillStrategy(場面の約定の模型)"))
        return ok({"fill_price": st["fills"][0]["price"] if st["fills"] else None},
                  f"broker.setFillStrategy(DefaultStrategy の子: fillMarketOrder が FillInfo(12345, 数量) を返す)。fills={st['fills']} 状態 {st['events']}")

    def scene_p7_latency_model_swap(self, sc):
        return not_supported("遅延の模型を渡す口が無い(注文は次の足で埋める)。試したこと: " + self._try_attr("setLatencyModel"))

    def _fee(self, sc, fee):
        st = self._buy(sc, lambda br: C.configure(br.setCommission, backtesting.FixedPerTrade(fee), what="broker.setCommission(FixedPerTrade(場面の費用))"))
        return ok({"fee": st["fills"][0]["commission"] if st["fills"] else None}, f"broker.setCommission(FixedPerTrade({fee}))。fills={st['fills']}")

    def scene_p7_cost_model_swap(self, sc):
        return self._fee(sc, 0.5)

    def scene_p7_cost_per_unit(self, sc):
        class PerUnit(backtesting.Commission):
            def calculate(self, order, price, quantity):
                return 0.375 * quantity

        st = self._buy(sc, lambda br: C.configure(br.setCommission, PerUnit(), what="broker.setCommission(場面の費用の模型)"), qty=2)
        return ok({"fee": sum(x["commission"] for x in st["fills"]) if st["fills"] else None},
                  f"broker.setCommission(Commission の子: calculate が 0.375 × quantity を返す)、数量 2 の成行。fills={st['fills']}")

    def scene_p7_account_swap(self, sc):
        rec = []

        class RecBroker(backtesting.Broker):
            def commitOrderExecution(self, order, dateTime, fillInfo):
                rec.append(float(fillInfo.getQuantity()))
                return super().commitOrderExecution(order, dateTime, fillInfo)

        feed = _feed(self._bars(sc))
        cnt = {"n": 0}

        class S(strategy.BacktestingStrategy):
            def onBars(self, bars_):
                cnt["n"] += 1
                if cnt["n"] == 1:
                    self.marketOrder(INST, 1)

        try:
            C.configure(S, feed, RecBroker(100_000, feed), what="BacktestingStrategy(feed, 場面の口座 = backtesting.Broker の子)").run()
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"BacktestingStrategy(feed, <Broker の子>) で走らせた -> {type(exc).__name__}: {str(exc)[:200]}")
        return ok({"account_recorded_fill_qty": rec}, "BacktestingStrategy(feed, broker) の第 2 引数に backtesting.Broker の子を渡し、約定を記録した"
                  "(PyAlgoTrade の broker は口座と約定を 1 つで持つ)")

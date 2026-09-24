"""Survey candidate 2 `Backtrader` (PyPI `backtrader` 1.9.78.123), run in its own venv.

Driven through its public API: `Cerebro`, `feeds.PandasData`, `Strategy`
(`next`, `notify_order`, `notify_timer`, `buy`, `sell`, `cancel`, `self.data`
lines), `Cerebro.add_timer`, the broker's public settings (`setcash`,
`set_slippage_fixed`, `addcommissioninfo` with a `CommInfoBase` subclass) and
`Cerebro.setbroker`. Backtrader stores times as float day numbers
(`bt.date2num` / `num2date`).
"""
from __future__ import annotations

import datetime as D
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

import pandas as pd  # noqa: E402

from protocol import Adapter, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

import backtrader as bt  # noqa: E402

STATUS = {bt.Order.Accepted: "accepted", bt.Order.Completed: "filled", bt.Order.Canceled: "canceled",
          bt.Order.Rejected: "rejected", bt.Order.Margin: "rejected"}


def _df(bars: list[dict]) -> pd.DataFrame:
    rows = [C.as_bar(b) for b in bars]
    idx = pd.DatetimeIndex([C.ns_to_dt(b["ts_ns"]).replace(tzinfo=None) for b in rows])
    return pd.DataFrame({k: [float(b[k]) for b in rows] for k in ("open", "high", "low", "close", "volume")}, index=idx)


def _ns(strategy_or_data) -> int:
    d = bt.num2date(strategy_or_data.datetime[0]).replace(tzinfo=D.timezone.utc)
    return C.dt_to_ns(d)


def _fed(s):
    """The data feed the strategy reads, asked of Backtrader through its public
    lookup `Strategy.getdatabyname` (round r6-3: `returned_by` = Backtrader's
    strategy.py; `self.data` is a plain attribute Backtrader's metaclass sets,
    which the provenance check cannot place)."""
    return C.read(s.getdatabyname, s.getdatanames()[0])


_CHOSEN = {"preload": True}  # the configured target's chosen values (round r8-1); set by the adapter


def run(bars, on_next, cash=1_000_000.0, setup=None, notify=None, timer=None, broker=None, preload=None):
    preload = _CHOSEN["preload"] if preload is None else preload
    # round r8-1 (positive definition A (1)): every setting through common.configure
    cer = C.configure(bt.Cerebro, stdstats=False, preload=preload, what=f"Cerebro(stdstats=False, preload={preload})",
                      decided_from=("選ぶ値",))
    if broker is not None:
        C.configure(cer.setbroker, broker, what="Cerebro.setbroker(場面の口座)", decided_from=("場面の入力",))
    C.configure(cer.broker.setcash, cash, what=f"broker.setcash({cash})", decided_from=("場面の入力",))
    feed = C.configure(bt.feeds.PandasData, dataname=_df(bars), what="feeds.PandasData(dataname=場面の足)",
                       decided_from=("場面の入力",))
    C.configure(cer.adddata, feed, what="Cerebro.adddata(feed)", decided_from=("場面の入力",))
    st = {"n": 0, "log": [], "notices": [], "fills": []}

    class S(bt.Strategy):
        def __init__(self):
            if timer is not None:
                self.add_timer(when=timer)

        def next(self):
            st["n"] += 1
            on_next(self, st["n"], st)

        def notify_order(self, order):
            name = STATUS.get(order.status)
            if name:
                st["notices"].append(name)
            if order.status == bt.Order.Completed:
                st["fills"].append({"price": order.executed.price, "size": order.executed.size,
                                    "comm": order.executed.comm, "dt": order.executed.dt})
            if notify:
                notify(self, order, st)

        def notify_timer(self, t, when, *args, **kwargs):
            st["log"].append(("clock", C.dt_to_ns(when.replace(tzinfo=D.timezone.utc))))

    C.configure(cer.addstrategy, S, what="Cerebro.addstrategy(場面の戦略)", decided_from=("場面の入力",))
    if setup:
        setup(cer)
    cer.run()
    return st


def _try_non_bar(e: dict) -> str:
    idx = pd.DatetimeIndex([C.ns_to_dt(e["ts_ns"]).replace(tzinfo=None)])
    df = pd.DataFrame([{k: v for k, v in C.fields_of(e).items() if not isinstance(v, list)}], index=idx)
    try:
        cer = bt.Cerebro(stdstats=False)
        cer.adddata(bt.feeds.PandasData(dataname=df))
        cer.addstrategy(bt.Strategy)
        cer.run()
    except Exception as exc:  # noqa: BLE001
        return f"feeds.PandasData(dataname=<{list(df.columns)} の DataFrame>) で走らせた -> {type(exc).__name__}: {str(exc)[:160]}"
    return "feeds.PandasData に渡して例外なく走った(OHLC の列が無いので足の値は NaN)"


NON_BAR = "Backtrader のデータは足の feed(lines: datetime/open/high/low/close/volume/openinterest)で、{k} の型は無い。試したこと: {err}"


class BacktraderAdapter(Adapter):
    name = "opp_backtrader"
    # round r8-1 (positive definition A): Cerebro's `preload` is a value the user chooses; each value is its
    # own configured target, run on every scene (until round r8-1 p4-future-read-attempt ran both and picked one)
    CONFIGS = {"preload=true": {"preload": True}, "preload=false": {"preload": False}}

    def __init__(self, config: str = "preload=true") -> None:
        super().__init__(config or "preload=true")
        _CHOSEN["preload"] = self.choose["preload"]

    # ---------------- P0-1
    def scene_p1_merge_by_time(self, sc):
        return not_supported(NON_BAR.format(k="約定・資金調達", err=_try_non_bar(sc.input["streams"]["trades"][0])))

    def scene_p1_one_call_per_event(self, sc):
        car = []
        st = run(C.events(sc), lambda s, n, st: (st["log"].append(["bar", _ns(s)]), car.append(C.carrier(_fed(s)))))
        return ok({"sequence": st["log"]}, "PandasData の足 5 本。next の各回に self.datetime[0] を num2date で読んだ",
                  {"carriers": car})

    def scene_p1_typed_events(self, sc):
        return not_supported(NON_BAR.format(k="約定", err=_try_non_bar(C.events(sc)[1])))

    # ---------------- P0-2
    def _iso(self, sc):
        """The ISO string handed as it is to Backtrader's data inputs: the pandas feed's time index and the CSV feed."""
        import tempfile
        iso = sc.input["iso"]
        got = {}
        df = pd.DataFrame([{"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0}], index=[iso])
        try:
            cer = bt.Cerebro(stdstats=False)
            cer.adddata(bt.feeds.PandasData(dataname=df))
            seen = []

            class S(bt.Strategy):
                def next(self):
                    seen.append(_ns(self))

            cer.addstrategy(S)
            cer.run()
            got["PandasData"] = seen
        except Exception as exc:  # noqa: BLE001
            got["PandasData"] = f"{type(exc).__name__}: {str(exc)[:120]}"
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "bars.csv"
            path.write_text(f"datetime,open,high,low,close,volume,openinterest\n{iso},1,1,1,1,1,0\n", encoding="utf-8")
            try:
                cer = bt.Cerebro(stdstats=False)
                cer.adddata(bt.feeds.GenericCSVData(dataname=str(path)))
                seen = []

                class S2(bt.Strategy):
                    def next(self):
                        seen.append(_ns(self))

                cer.addstrategy(S2)
                cer.run()
                got["GenericCSVData"] = seen
            except Exception as exc:  # noqa: BLE001
                got["GenericCSVData"] = f"{type(exc).__name__}: {str(exc)[:120]}"
        for name, cls in (("GenericCSVData", bt.feeds.GenericCSVData), ("PandasData", bt.feeds.PandasData)):
            if isinstance(got[name], list) and got[name]:
                return ok(got[name][0], f"ISO の文字列を {name} に渡し、next の self.datetime[0] を ns にした。全部の試し: {got}",
                          {"reader": C.qualname(cls)})
        return not_supported(f"ISO の文字列を Backtrader のデータの入口にそのまま渡した: {got}")

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    def _ts(self, sc):
        evs = [{"kind": "trade", "ts_ns": e["ts_ns"], "price": 100.0} for e in C.events(sc)]
        car = []
        st = run(evs, lambda s, n, st: (st["log"].append(_ns(s)), car.append(C.carrier(_fed(s)))))
        return ok({"observed_ts_ns": st["log"]}, "足(OHLC=100)で渡し、next の self.datetime[0] を ns に直した", {"carriers": car})

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _ts

    # ---------------- P0-3
    def _type(self, sc):
        e = C.events(sc)[0]
        if e["kind"] != "bar":
            return not_supported(NON_BAR.format(k=e["kind"], err=_try_non_bar(e)))
        out = {}

        car = []

        def f(s, n, st):
            st["log"].append(["bar", _ns(s)])
            car.append(C.carrier(_fed(s)))
            out.update({k: float(getattr(s.data, k)[0]) for k in ("open", "high", "low", "close", "volume")})

        st = run([e], f)
        return ok({"sequence": st["log"], "fields": out}, "足 1 本。next で self.data の lines を読んだ", {"carriers": car})

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = _type

    def scene_p3_mixed_one_run(self, sc):
        return not_supported(NON_BAR.format(k="足以外の 5 種", err=_try_non_bar(C.events(sc)[0])))

    def scene_p3_clock_timer(self, sc):
        st = run(C.events(sc), lambda s, n, st: None, timer=bt.timer.SESSION_START)
        return ok({"clock_calls_ns": [t for k, t in st["log"] if k == "clock"]},
                  "add_timer は 1 日の中の時刻(または SESSION_START/END)で毎日呼ぶ形で、決まった日時を 1 回だけ頼む口は無い。"
                  "SESSION_START で頼み、notify_timer が呼ばれた時刻を全部記録した")

    def _buy_run(self, sc, place, cash, **kw):
        def f(s, n, st):
            if n == 1:
                st["order"] = place(s)

        return run([C.as_bar(e) for e in C.events(sc)], f, cash=cash, **kw)

    def scene_p3_notice_accepted(self, sc):
        st = self._buy_run(sc, lambda s: s.buy(size=1, price=90.0, exectype=bt.Order.Limit), 1_000_000)
        return ok({"notices": st["notices"]}, "約定を足に代えた(any_type)。notify_order で受け取った状態の列(Submitted は数えない)")

    def scene_p3_notice_rejected(self, sc):
        st = self._buy_run(sc, lambda s: s.buy(size=1), 1_000)
        return ok({"notices": st["notices"]}, "現金 1,000。成行 1。notify_order の列(Margin は資金不足の拒否として rejected に数えた)")

    def scene_p3_notice_filled(self, sc):
        st = self._buy_run(sc, lambda s: s.buy(size=1), 1_000_000)
        return ok({"filled_qty_in_notices": float(sum(f["size"] for f in st["fills"])), "notices": st["notices"]},
                  f"notify_order(Completed) の executed.size の合計。fills={st['fills']}")

    # ---------------- P0-4
    def scene_p4_visible_at_step(self, sc):
        probe = sc.input["probe_at_ns"]
        reads = C.Reads()

        def f(s, n, st):
            if _ns(s) == probe and not reads.items:
                reads.read("self.data.close.get(size=len(self.data))", lambda: list(s.data.close.get(size=len(s.data))))

        run(C.events(sc), f)
        if not reads.items:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった(対象がその時刻に戦略を呼ばない)")
        return ok(reads.output(), "T0 + 4 日の呼び出しに self.data.close.get(size=len(self.data)) を読んだ", reads.provenance())

    def scene_p4_received_time(self, sc):
        return not_supported(NON_BAR.format(k="受け取れる時刻を別に持つ事象", err=_try_non_bar(
            {"ts_ns": C.events(sc)[0]["ts_ns"], "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0, "recv_ns": 1}))
            + "(1 本の足に時刻は datetime の 1 つ)")

    def scene_p4_future_read_attempt(self, sc):
        probe = sc.input["probe_at_ns"]
        att = C.Attempts()

        def f(s, n, st):
            if _ns(s) != probe or att.items:
                return
            # namings: the scene's fixed list. The line counts relative to now (0 = newest, 1 = next);
            # its `array` counts from the first bar (next = len(self.data)).
            C.try_position_namings(att, "self.data.close[相対の位置]", lambda: s.data.close, 1)
            C.try_position_namings(att, "self.data.close.array[位置]", lambda: s.data.close.array, len(s.data))
            att.run("self.data.close.get(ago=1, size=1)(最新の次の位置)", "position",
                    lambda: list(s.data.close.get(ago=1, size=1)), shape="next_call", naming="next")
            att.run("self.data.close.array(中身の配列)", "other", lambda: list(s.data.close.array))

        run(C.events(sc), f)
        if not att.items:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった")
        return ok(att.output(), f"T0 + 4 日の呼び出しに試した(Cerebro(preload={self.choose['preload']})): {att.summary()}")

    def _no_types(self, sc):
        return not_supported(NON_BAR.format(k="約定・資金調達・清算", err=_try_non_bar(sc.input["streams"]["trades"][0])))

    scene_p5_same_time_twice = scene_p5_hand_over_order = _no_types

    def scene_p5_same_stream_order(self, sc):
        car = []
        st = run([C.as_bar(e) for e in C.events(sc)], lambda s, n, st: (st["log"].append(float(s.data.close[0])),
                                                                       car.append(C.carrier(_fed(s)))))
        return ok({"prices": st["log"]}, "約定を足に代え、同じ時刻の 3 本を 1 つの feed で渡した", {"carriers": car})

    # ---------------- P0-6
    def scene_p6_place_then_cancel(self, sc):
        out = {}

        def f(s, n, st):
            if n == 1:
                st["o"] = s.buy(size=1, price=90.0, exectype=bt.Order.Limit)
            elif n == 2:
                out["open_at_call2"] = len([o for o in s.broker.get_orders_open()])
                s.cancel(st["o"])
            elif n == 3:
                out["open_at_call3"] = len([o for o in s.broker.get_orders_open()])

        run([C.as_bar(e) for e in C.events(sc)], f)
        return ok(out, "buy(Limit 90) / broker.get_orders_open() / cancel")

    def scene_p6_cancel_notice(self, sc):
        def f(s, n, st):
            if n == 1:
                st["o"] = s.buy(size=1, price=90.0, exectype=bt.Order.Limit)
            elif n == 2:
                s.cancel(st["o"])

        st = run([C.as_bar(e) for e in C.events(sc)], f)
        return ok({"cancel_notice_received": "canceled" in st["notices"], "notices": st["notices"]}, "notify_order の列")

    def scene_p6_fill_seen_by_strategy(self, sc):
        out = {}

        def f(s, n, st):
            if n == 1:
                st["o"] = s.buy(size=1)
            elif n == 3:
                out["filled_qty_at_call3"] = float(st["o"].executed.size)

        run([C.as_bar(e) for e in C.events(sc)], f)
        return ok(out, "3 回目に order.executed.size")

    # ---------------- P0-7
    def scene_p7_fill_model_swap(self, sc):
        def setup(cer):
            # round r8-1: the slippage is computed from the price the scene's events will have (100) before the run:
            # a setting decided from input not yet delivered (positive definition A), recorded as such
            C.configure(cer.broker.set_slippage_fixed, 12345.0 - 100.0, slip_open=True, slip_match=True, slip_out=True,
                        what="broker.set_slippage_fixed(12245 = 12345 - 場面の約定の価格 100)",
                        decided_from=("場面の入力", "まだ届いていない入力"))

        st = self._buy_run(sc, lambda s: s.buy(size=1), 100_000, setup=setup)
        return ok({"fill_price": st["fills"][0]["price"] if st["fills"] else None},
                  "約定の模型を渡す口は無い。公開の設定 set_slippage_fixed(12245, slip_open=True, slip_match=True, slip_out=True) で"
                  f"始値 100 からの滑りとして 12345 に埋めた。fills={st['fills']}")

    def scene_p7_latency_model_swap(self, sc):
        try:
            bt.Cerebro(latency=0.007)  # type: ignore[call-arg]
            r = "受け付けた"
        except Exception as exc:  # noqa: BLE001
            r = f"{type(exc).__name__}: {exc}"
        return not_supported(f"遅延の模型の口が無い(約定は次の足)。試したこと: bt.Cerebro(latency=...) -> {r}"
                             "(Cerebro は未知の引数を黙って受けるかを見た)")

    def _fee(self, sc, fee, per_unit: bool = False, size: int = 1):
        class Flat(bt.CommInfoBase):
            params = (("commission", fee), ("stocklike", True), ("commtype", bt.CommInfoBase.COMM_FIXED))

            def _getcommission(self, size, price, pseudoexec):
                return fee * abs(size) if per_unit else fee

        st = self._buy_run(sc, lambda s: s.buy(size=size), 100_000, setup=lambda cer: C.configure(
            cer.broker.addcommissioninfo, Flat(), what="broker.addcommissioninfo(場面の費用の模型)", decided_from=("場面の入力",)))
        return ok({"fee": sum(f["comm"] for f in st["fills"]) if st["fills"] else None},
                  f"addcommissioninfo(CommInfoBase の子: {'数量 1 単位あたり' if per_unit else '1 件'} {fee})、数量 {size} の成行。fills={st['fills']}")

    def scene_p7_cost_model_swap(self, sc):
        return self._fee(sc, 0.5)

    def scene_p7_cost_per_unit(self, sc):
        return self._fee(sc, 0.375, per_unit=True, size=2)

    def scene_p7_account_swap(self, sc):
        rec = []

        class RecBroker(bt.brokers.BackBroker):
            def notify(self, order):
                if order.status == bt.Order.Completed:
                    rec.append(float(order.executed.size))
                super().notify(order)

        self._buy_run(sc, lambda s: s.buy(size=1), 100_000, broker=RecBroker())
        return ok({"account_recorded_fill_qty": rec}, "Cerebro.setbroker(BackBroker の子)。子の notify で約定を記録した"
                  "(Backtrader の broker は口座と約定を 1 つで持つ)")

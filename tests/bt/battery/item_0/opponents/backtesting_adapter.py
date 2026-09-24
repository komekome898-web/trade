"""Survey candidate 55 `backtesting.py` (PyPI `backtesting` 0.6.6), run in its own venv.

Driven through its public API: `Backtest(DataFrame, Strategy, cash=,
commission=, trade_on_close=)`, `Backtest.run()`, and inside `Strategy.next`
the `self.data` arrays, `self.buy(size=, limit=)`, `self.orders`,
`Order.cancel()`, `self.trades`, `self.position`. Input is an OHLCV
DataFrame indexed by time.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

import warnings  # noqa: E402

import pandas as pd  # noqa: E402

from protocol import Adapter, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

import backtesting as btp  # noqa: E402
from backtesting import Backtest, Strategy  # noqa: E402

warnings.filterwarnings("ignore")


def _df(bars: list[dict]) -> pd.DataFrame:
    rows = [C.as_bar(b) for b in bars]
    idx = pd.to_datetime([b["ts_ns"] for b in rows], unit="ns")
    return pd.DataFrame({"Open": [float(b["open"]) for b in rows], "High": [float(b["high"]) for b in rows],
                         "Low": [float(b["low"]) for b in rows], "Close": [float(b["close"]) for b in rows],
                         "Volume": [float(b.get("volume", 1.0)) for b in rows]}, index=idx)


def run(bars, fn, cash=1_000_000.0, **kw):
    st = {"n": 0, "log": []}

    class S(Strategy):
        def init(self):
            pass

        def next(self):
            st["n"] += 1
            fn(self, st["n"], st)

    bt_ = Backtest(_df(bars), S, cash=cash, **kw)
    res = bt_.run()
    return st, res


def _now(s) -> int:
    return int(pd.Timestamp(s.data.index[-1]).value)


NON_BAR = "backtesting.py の入力は Open/High/Low/Close(/Volume) の列を持つ DataFrame で、{k} の型は無い。試したこと: {err}"


def _try_non_bar(e: dict) -> str:
    df = pd.DataFrame([{k: v for k, v in C.fields_of(e).items() if not isinstance(v, list)}],
                      index=pd.to_datetime([e["ts_ns"]], unit="ns"))
    try:
        Backtest(df, Strategy).run()
    except Exception as exc:  # noqa: BLE001
        return f"Backtest(<{list(df.columns)} の DataFrame>, Strategy).run() -> {type(exc).__name__}: {str(exc)[:160]}"
    return "Backtest(...).run() は例外なく走った"


class BacktestingAdapter(Adapter):
    name = "opp_backtesting"

    def scene_p1_merge_by_time(self, sc):
        return not_supported(NON_BAR.format(k="約定・資金調達", err=_try_non_bar(sc.input["streams"]["trades"][0])))

    def scene_p1_one_call_per_event(self, sc):
        car = []
        st, _ = run(C.events(sc), lambda s, n, st: (st["log"].append(["bar", _now(s)]), car.append(C.carrier(C.attr(s, "data")))))
        return ok({"sequence": st["log"]}, "足 5 本。next の各回に self.data.index[-1]", {"carriers": car})

    def scene_p1_typed_events(self, sc):
        return not_supported(NON_BAR.format(k="約定", err=_try_non_bar(C.events(sc)[1])))

    def _iso(self, sc):
        """The ISO string handed as it is to the tool's only data input (the DataFrame's index);
        the strategy's init reads the index the tool made of it."""
        iso = sc.input["iso"]
        df = pd.DataFrame({"Open": [1.0, 1.0], "High": [1.0, 1.0], "Low": [1.0, 1.0], "Close": [1.0, 1.0], "Volume": [1.0, 1.0]},
                          index=[iso, iso])
        got = {}

        class S(Strategy):
            def init(self):
                got["index0"] = self.data.index[0]

            def next(self):
                pass

        try:
            Backtest(df, S).run()
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"ISO の文字列を添字にした DataFrame を Backtest に渡した -> {type(exc).__name__}: {str(exc)[:200]}")
        v = got.get("index0")
        if not isinstance(v, pd.Timestamp):
            return not_supported(f"ISO の文字列を添字にした DataFrame を Backtest に渡した -> 戦略の init が読んだ添字 {v!r:.120}(時刻に変換されない)")
        ts = v if v.tzinfo is None else v.tz_convert("UTC")
        return ok(int(ts.value), f"ISO の文字列を添字にした DataFrame を Backtest に渡し、Backtest が変換した添字を戦略の init で読んだ {v!r}",
                  {"reader": C.qualname(Backtest)})

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    def _ts(self, sc):
        evs = [{"kind": "trade", "ts_ns": e["ts_ns"], "price": 100.0} for e in C.events(sc)]
        car = []
        try:
            st, _ = run(evs, lambda s, n, st: (st["log"].append(_now(s)), car.append(C.carrier(C.attr(s, "data")))))
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"足で渡して走らせた -> {type(exc).__name__}: {str(exc)[:200]}")
        return ok({"observed_ts_ns": st["log"]}, "足(OHLC=100)で渡し、next の self.data.index[-1]", {"carriers": car})

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _ts

    def _type(self, sc):
        e = C.events(sc)[0]
        if e["kind"] != "bar":
            return not_supported(NON_BAR.format(k=e["kind"], err=_try_non_bar(e)))
        out = {}

        car = []

        def f(s, n, st):
            st["log"].append(["bar", _now(s)])
            car.append(C.carrier(C.attr(s, "data")))
            out.update({"open": float(s.data.Open[-1]), "high": float(s.data.High[-1]), "low": float(s.data.Low[-1]),
                        "close": float(s.data.Close[-1]), "volume": float(s.data.Volume[-1])})

        try:
            st, _ = run([e], f)
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"足 1 本で走らせた -> {type(exc).__name__}: {str(exc)[:200]}")
        return ok({"sequence": st["log"], "fields": out}, f"足 1 本。next が呼ばれた回数 {st['n']}", {"carriers": car})

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = _type

    def scene_p3_mixed_one_run(self, sc):
        return not_supported(NON_BAR.format(k="足以外の 5 種", err=_try_non_bar(C.events(sc)[0])))

    def _no_api(self, what: str, name: str) -> str:
        try:
            Backtest(_df([{"kind": "bar", "ts_ns": 1_700_006_400_000_000_000, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}] * 1),
                     Strategy, **{name: object()})
        except TypeError as exc:
            return f"Backtest(..., {name}=...) -> TypeError: {exc}"
        return f"Backtest(..., {name}=...) は受け付けられた"

    def scene_p3_clock_timer(self, sc):
        return not_supported("時刻を頼んで呼ばれる口が無い(next は足ごと)。試したこと: " + self._no_api("timer", "timers"))

    def _notice(self, sc):
        names = [n for n in dir(Strategy) if "notif" in n or "on_" in n]
        return not_supported(f"注文の受付・拒否・約定・取消を戦略に知らせる呼び出しが無い(Strategy の公開の名前: {[n for n in dir(Strategy) if not n.startswith('_')]}、"
                             f"通知らしい名前 {names})。試したこと: " + self._no_api("notice", "on_order"))

    scene_p3_notice_accepted = scene_p3_notice_rejected = scene_p3_notice_filled = _notice

    def scene_p4_visible_at_step(self, sc):
        probe = sc.input["probe_at_ns"]
        reads = C.Reads()
        called = []

        def f(s, n, st):
            called.append(_now(s))
            if _now(s) == probe and not reads.items:
                reads.read("self.data.Close", lambda: list(s.data.Close))

        run(C.events(sc), f)
        if not reads.items:  # no_probe_call
            return not_supported(f"T0 + 4 日の呼び出しが無かった(対象がその時刻に戦略を呼ばない)。呼ばれた時刻 {called}")
        return ok(reads.output(), f"T0 + 4 日の呼び出しの next で self.data.Close を読んだ。呼ばれた時刻 {called}", reads.provenance())

    def scene_p4_received_time(self, sc):
        return not_supported(NON_BAR.format(k="受け取れる時刻", err=_try_non_bar(
            {"ts_ns": 1_700_006_400_000_000_000, "Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0, "recv_ns": 1})) + "(1 行に時刻は index の 1 つ)")

    def scene_p4_future_read_attempt(self, sc):
        probe = sc.input["probe_at_ns"]
        ts = (lambda ns: pd.Timestamp(ns, unit="ns"))
        att = C.Attempts()

        def f(s, n, st):
            if _now(s) != probe or att.items:
                return
            # namings: the scene's fixed list (common.try_*_namings)
            C.try_position_namings(att, "self.data.Close[位置]", lambda: s.data.Close, len(s.data.Close))
            C.try_position_namings(att, "self.data.df.Close.iloc[位置]", lambda: s.data.df.Close.iloc, len(s.data.df))
            C.try_time_namings(att, "self.data.df.Close.loc[時刻]", "time_at", lambda t: s.data.df.Close.loc[t], sc, ts)
            C.try_time_namings(att, "self.data.df.Close.loc[始:終]", "time_range", lambda a, b: s.data.df.Close.loc[a:b], sc, ts)
            att.run("self.data.df の Close の全部", "other", lambda: list(s.data.df.Close))
            att.run("self.data.Close.base(numpy の元の配列)", "other",
                    lambda: list(s.data.Close.base) if getattr(s.data.Close, "base", None) is not None else None)

        run(C.events(sc), f)
        if not att.items:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった(対象がその時刻に戦略を呼ばない)ので、先を読む試しができなかった")
        return ok(att.output(), "T0 + 4 日の呼び出しに試した: " + att.summary())

    def _no_types(self, sc):
        return not_supported(NON_BAR.format(k="約定・資金調達・清算", err=_try_non_bar(sc.input["streams"]["trades"][0])))

    scene_p5_same_time_twice = scene_p5_hand_over_order = _no_types

    def scene_p5_same_stream_order(self, sc):
        rows = [C.as_bar(e) for e in C.events(sc)]
        car = []
        try:
            st, _ = run(rows, lambda s, n, st: (st["log"].append(float(s.data.Close[-1])), car.append(C.carrier(C.attr(s, "data")))))
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"同じ時刻の 3 行を渡して走らせた -> {type(exc).__name__}: {str(exc)[:200]}")
        return ok({"prices": st["log"]}, "約定を足に代え、同じ時刻の 3 行を渡した", {"carriers": car})

    def scene_p6_place_then_cancel(self, sc):
        out = {}

        def f(s, n, st):
            if n == 1:
                s.buy(size=1, limit=90.0)
            elif n == 2:
                out["open_at_call2"] = len(s.orders)
                for o in list(s.orders):
                    o.cancel()
            elif n == 3:
                out["open_at_call3"] = len(s.orders)

        st, _ = run([C.as_bar(e) for e in C.events(sc)], f)
        return ok(out, f"buy(size=1, limit=90) / self.orders / Order.cancel()。next の回数 {st['n']}")

    def scene_p6_cancel_notice(self, sc):
        return self._notice(sc)

    def scene_p6_fill_seen_by_strategy(self, sc):
        out = {}

        def f(s, n, st):
            if n == 1:
                s.buy(size=1)
            elif n == 3:
                out["filled_qty_at_call3"] = float(s.position.size)

        st, _ = run([C.as_bar(e) for e in C.events(sc)], f)
        return ok(out, f"3 回目に self.position.size(注文の約定済み数量を注文から読む口は無い)。next の回数 {st['n']}")

    def _buy(self, sc, size: int = 1, **kw):
        def f(s, n, st):
            st["equity"] = float(s.equity)
            st["pos"] = float(s.position.size)
            if n == 1:
                s.buy(size=size)

        st, res = run([C.as_bar(e) for e in C.events(sc)], f, cash=100_000.0, **kw)
        return st

    def scene_p7_fill_model_swap(self, sc):
        return not_supported("約定の模型を渡す口が無い(埋まる値は次の足の始値か trade_on_close の終値、spread で上下にずらすだけ)。試したこと: "
                             + self._no_api("fill", "fill_model"))

    def scene_p7_latency_model_swap(self, sc):
        return not_supported("遅延の模型を渡す口が無い。試したこと: " + self._no_api("latency", "latency_model"))

    def _fee(self, sc, fee):
        st = self._buy(sc, commission=(fee, 0.0))
        if not st.get("pos"):
            return ok({"fee": None}, f"commission=({fee}, 0.0)。最後の呼び出しまでに建玉が無かった。{st}")
        return ok({"fee": round(100_000.0 - st["equity"], 10)},
                  f"commission=({fee}, 0.0)(1 件あたりの固定額, 率)。約定の値と最後の足の値が同じ 100 なので、"
                  f"費用 = 初めの現金 − 最後の呼び出しの self.equity と読んだ。{st}")

    def scene_p7_cost_model_swap(self, sc):
        return self._fee(sc, 0.5)

    def scene_p7_cost_per_unit(self, sc):
        st = self._buy(sc, size=2, commission=lambda order_size, price: 0.375 * abs(order_size))
        if not st.get("pos"):
            return ok({"fee": None}, f"commission=<数量 × 0.375 の関数>。最後の呼び出しまでに建玉が無かった。{st}")
        return ok({"fee": round(100_000.0 - st["equity"], 10)},
                  "commission=<(order_size, price) を受けて 0.375 × |order_size| を返す関数>(backtesting.py 734-735 行の callable の口)、"
                  f"数量 2 の成行。約定の値と最後の足の値が同じ 100 なので、費用 = 初めの現金 − 最後の呼び出しの self.equity と読んだ。{st}")

    def scene_p7_account_swap(self, sc):
        return not_supported("口座(_Broker)は Backtest.run の中で作られ、差し替える口が無い。試したこと: " + self._no_api("broker", "broker"))

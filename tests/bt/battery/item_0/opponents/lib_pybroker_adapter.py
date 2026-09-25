"""Survey candidate 4 `PyBroker` (PyPI `lib-pybroker` 2.0.1), run in its own venv.

Driven through its public API: `pybroker.Strategy(DataFrame, start, end,
StrategyConfig)`, `add_execution(fn, symbols)`, `backtest(...)`, and inside
`fn(ctx)` the `ExecContext` (`dt`, `close`, `buy_shares`, `buy_limit_price`,
`buy_fill_price`, `pending_orders`, `cancel_pending_order`, `orders`,
`long_pos`), `StrategyConfig(fee_mode=<callable>)` and
`Strategy.set_slippage_model`. Input is a DataFrame of bars
(symbol / date / open / high / low / close / volume).
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from protocol import Adapter, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

import pybroker as pb  # noqa: E402

pb.disable_logging()
pb.disable_progress_bar()
pb.disable_caches()


def _df(bars: list[dict]) -> pd.DataFrame:
    rows = [C.as_bar(b) for b in bars]
    return pd.DataFrame({"symbol": "X", "date": pd.to_datetime([b["ts_ns"] for b in rows], unit="ns"),
                         **{k: [float(b[k]) for b in rows] for k in ("open", "high", "low", "close")},
                         "volume": [float(b.get("volume", 1.0)) for b in rows]})


def _dt_ns(ctx) -> int:
    return int(pd.Timestamp(ctx.dt).value)


def run(bars, fn, cash=1_000_000.0, fee=None, slippage=None, **cfg):
    df = _df(bars)
    # round r8-1 (positive definition A): every setting through common.configure; start / end are the configured
    # target's chosen window, the same in every scene (until round r8-1: the scene's first and last row)
    config = C.configure(pb.StrategyConfig, initial_cash=cash, fee_mode=fee, **cfg,
                         what=f"StrategyConfig(initial_cash={cash}, fee_mode={'場面の費用の模型' if fee else None}"
                              f"{', ' + ', '.join(sorted(cfg)) if cfg else ''})", decided_from=("場面の入力",))
    start, end = pd.Timestamp(C.FIXED_WINDOW[0]), pd.Timestamp(C.FIXED_WINDOW[1])
    s = C.configure(pb.Strategy, df, start, end, config, what=f"Strategy(場面の足の DataFrame, {start.date()}, {end.date()}, config)",
                    decided_from=("場面の入力", "選ぶ値"))
    st = {"n": 0, "log": []}

    def exec_fn(ctx):
        st["n"] += 1
        fn(ctx, st["n"], st)

    C.configure(s.add_execution, exec_fn, ["X"], what="add_execution(場面の戦略, [銘柄])", decided_from=("場面の入力",))
    if slippage is not None:
        C.configure(s.set_slippage_model, slippage, what="set_slippage_model(場面の約定の模型)", decided_from=("場面の入力",))
    res = s.backtest(warmup=None)
    return st, res


NON_BAR = ("PyBroker の入力は銘柄・日時・OHLCV の行の DataFrame(または DataSource)で、{k} の型は無い。"
           "試したこと: {err}")


def _try_non_bar(e: dict) -> str:
    df = pd.DataFrame([{"symbol": "X", "date": pd.Timestamp(e["ts_ns"], unit="ns"),
                        **{k: v for k, v in C.fields_of(e).items() if not isinstance(v, list)}}])
    try:
        # round r8-1: the trial uses the same fixed window as every run (not the event's own day)
        s = pb.Strategy(df, pd.Timestamp(C.FIXED_WINDOW[0]), pd.Timestamp(C.FIXED_WINDOW[1]))
        s.add_execution(lambda ctx: None, ["X"])
        s.backtest()
    except Exception as exc:  # noqa: BLE001
        return f"Strategy(<{list(df.columns)} の DataFrame>).backtest() -> {type(exc).__name__}: {str(exc)[:160]}"
    return "Strategy(...).backtest() は例外なく走った"


class LibPybrokerAdapter(Adapter):
    name = "opp_lib_pybroker"
    # round r8-1 (positive definition A): the values this configured target chooses, the same in every scene
    CONFIGS = {"": {"window": list(C.FIXED_WINDOW), "warmup": None}}

    def scene_p1_merge_by_time(self, sc):
        return not_supported(NON_BAR.format(k="約定・資金調達", err=_try_non_bar(sc.input["streams"]["trades"][0])))

    def scene_p1_one_call_per_event(self, sc):
        car = []
        st, _ = run(C.events(sc), lambda ctx, n, st: (st["log"].append(["bar", _dt_ns(ctx)]), car.append(C.carrier(ctx))))
        return ok({"sequence": st["log"]}, "足 5 本。execution の各回に ctx.dt", {"carriers": car})

    def scene_p1_typed_events(self, sc):
        return not_supported(NON_BAR.format(k="約定", err=_try_non_bar(C.events(sc)[1])))

    def _iso(self, sc):
        """The ISO string handed as it is to the tool's data input (the `date` column of the DataFrame)."""
        iso = sc.input["iso"]
        df = pd.DataFrame({"symbol": ["X"], "date": [iso], "open": [1.0], "high": [1.0], "low": [1.0], "close": [1.0], "volume": [1.0]})
        seen = []
        try:
            s = pb.Strategy(df, "2023-12-30", "2024-01-02", pb.StrategyConfig())
            s.add_execution(lambda ctx: seen.append(ctx.dt), ["X"])
            s.backtest(warmup=None)
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"date の列が ISO の文字列の DataFrame を Strategy に渡した -> {type(exc).__name__}: {str(exc)[:200]}")
        if not seen:
            return not_supported("date の列が ISO の文字列の DataFrame を Strategy に渡した -> execution が呼ばれなかった")
        v = pd.Timestamp(seen[0])
        return ok(int((v if v.tzinfo is None else v.tz_convert("UTC")).value),
                  f"date の列が ISO の文字列の DataFrame を Strategy に渡し、execution の ctx.dt を読んだ {seen[0]!r}",
                  {"reader": C.qualname(pb.Strategy)})

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    def _ts(self, sc):
        evs = [C.substitute(e, "trade", price=100.0) for e in C.events(sc)]
        car = []
        try:
            st, _ = run(evs, lambda ctx, n, st: (st["log"].append(_dt_ns(ctx)), car.append(C.carrier(ctx))))
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"足(OHLC=100)で渡して走らせた -> {type(exc).__name__}: {str(exc)[:200]}")
        return ok({"observed_ts_ns": st["log"]}, "足で渡し、ctx.dt を ns にした", {"carriers": car})

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _ts

    def _type(self, sc):
        e = C.events(sc)[0]
        if e["kind"] != "bar":
            return not_supported(NON_BAR.format(k=e["kind"], err=_try_non_bar(e)))
        out = {}

        car = []

        def f(ctx, n, st):
            st["log"].append(["bar", _dt_ns(ctx)])
            car.append(C.carrier(ctx))
            out.update({k: float(getattr(ctx, k)[-1]) for k in ("open", "high", "low", "close", "volume")})

        try:
            st, _ = run([e], f)
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"足 1 本で走らせた -> {type(exc).__name__}: {str(exc)[:200]}")
        return ok({"sequence": st["log"], "fields": out}, "足 1 本。ctx の open/high/low/close/volume の最後", {"carriers": car})

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = _type

    def scene_p3_mixed_one_run(self, sc):
        return not_supported(NON_BAR.format(k="足以外の 5 種", err=_try_non_bar(C.events(sc)[0])))

    def scene_p3_clock_timer(self, sc):
        return not_supported("時刻を頼んで呼ばれる口が無い(execution は足ごとにだけ呼ばれる)。試したこと: "
                             + self._kw_attempt("add_timer"))

    def _kw_attempt(self, name: str) -> str:
        s = pb.Strategy(_df([{"kind": "bar", "ts_ns": 1_700_006_400_000_000_000, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}]),
                        "2023-11-15", "2023-11-15")
        try:
            getattr(s, name)(lambda ctx: None)
        except Exception as exc:  # noqa: BLE001
            return f"Strategy.{name}(...) -> {type(exc).__name__}: {exc}"
        return f"Strategy.{name}(...) は受け付けた"

    def _notice(self, sc):
        return not_supported("注文の受付・拒否・約定・取消を戦略に知らせる呼び出しが無い(戦略は ctx.orders() / ctx.pending_orders() で問い合わせる)。"
                             "試したこと: " + self._kw_attempt("add_order_callback"))

    scene_p3_notice_accepted = scene_p3_notice_rejected = scene_p3_notice_filled = _notice

    def scene_p4_visible_at_step(self, sc):
        probe = sc.input["probe_at_ns"]
        reads = C.Reads()

        def f(ctx, n, st):
            if _dt_ns(ctx) == probe and not reads.items:
                reads.read("ctx.close", lambda: list(ctx.close))

        run(C.events(sc), f)
        if not reads.items:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった(対象がその時刻に戦略を呼ばない)")
        return ok(reads.output(), "T0 + 4 日の呼び出しに ctx.close を読んだ", reads.provenance())

    def scene_p4_received_time(self, sc):
        return not_supported(NON_BAR.format(k="受け取れる時刻を別に持つ事象", err=_try_non_bar(
            {"ts_ns": 1_700_006_400_000_000_000, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0, "recv_ns": 1}))
            + "(1 行に日時は date の 1 つ。余分な列は register_columns で足せるが、配る時刻は date で決まる)")

    def scene_p4_future_read_attempt(self, sc):
        probe = sc.input["probe_at_ns"]
        att = C.Attempts()

        def f(ctx, n, st):
            if _dt_ns(ctx) != probe or att.items:
                return
            # ExecContext has no read that takes a time; the position reads get the scene's fixed namings
            C.try_position_namings(att, "ctx.close[位置]", lambda: ctx.close, len(ctx.close))
            att.run("ctx.foreign('X').close(全部)", "other", lambda: list(ctx.foreign("X").close))
            att.run("ctx.close.base(numpy の元の配列)", "other", lambda: list(ctx.close.base) if ctx.close.base is not None else None)

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
            st, _ = run(rows, lambda ctx, n, st: (st["log"].append(float(ctx.close[-1])), car.append(C.carrier(ctx))))
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"同じ日時の 3 行を渡して走らせた -> {type(exc).__name__}: {str(exc)[:200]}")
        return ok({"prices": st["log"]}, "約定を足に代え、同じ日時の 3 行を渡した", {"carriers": car})

    def scene_p6_place_then_cancel(self, sc):
        out = {}

        def f(ctx, n, st):
            if n == 1:
                ctx.buy_shares = 1
                ctx.buy_limit_price = 90.0
            elif n == 2:
                pend = list(ctx.pending_orders())
                out["open_at_call2"] = len(pend)
                for o in pend:
                    ctx.cancel_pending_order(o.id)
            elif n == 3:
                out["open_at_call3"] = len(list(ctx.pending_orders()))

        run([C.as_bar(e) for e in C.events(sc)], f)
        return ok(out, "buy_shares=1・buy_limit_price=90 / pending_orders / cancel_pending_order")

    def scene_p6_cancel_notice(self, sc):
        return self._notice(sc)

    def scene_p6_fill_seen_by_strategy(self, sc):
        out = {}

        def f(ctx, n, st):
            if n == 1:
                ctx.buy_shares = 1
            elif n == 3:
                pos = ctx.long_pos()
                out["filled_qty_at_call3"] = float(pos.shares) if pos else 0.0
                out["orders"] = [(o.type, float(o.shares)) for o in ctx.orders()]

        run([C.as_bar(e) for e in C.events(sc)], f)
        return ok(out, "3 回目に ctx.long_pos().shares(注文の約定済み数量を読む口は ctx.orders() の約定済みの一覧)")

    def _buy(self, sc, shares: int = 1, **kw):
        def f(ctx, n, st):
            if n == 1:
                ctx.buy_shares = shares
                if "fill" in kw:
                    ctx.buy_fill_price = kw["fill"]

        kw2 = {k: v for k, v in kw.items() if k != "fill"}
        _, res = run([C.as_bar(e) for e in C.events(sc)], f, cash=100_000.0, **kw2)
        return res

    def scene_p7_fill_model_swap(self, sc):
        res = self._buy(sc, fill=lambda symbol, bar_data: 12345.0)
        o = res.orders
        return ok({"fill_price": float(o["fill_price"].iloc[0]) if len(o) else None},
                  f"ctx.buy_fill_price に (symbol, bar_data) -> 12345.0 の関数を渡した。orders: {o.to_dict('records')}")

    def scene_p7_latency_model_swap(self, sc):
        return not_supported("遅延の模型の口が無い(約定は buy_delay 本あとの足)。試したこと: "
                             + self._kw_attempt("set_latency_model"))

    def _fee(self, sc, fee):
        res = self._buy(sc, fee=lambda info: Decimal(str(fee)))
        o = res.orders
        return ok({"fee": float(o["fees"].iloc[0]) if len(o) else None}, f"StrategyConfig(fee_mode=<FeeInfo -> {fee}>)。orders: {o.to_dict('records')}")

    def scene_p7_cost_model_swap(self, sc):
        return self._fee(sc, 0.5)

    def scene_p7_cost_per_unit(self, sc):
        res = self._buy(sc, shares=2, fee=lambda info: Decimal("0.375") * Decimal(str(info.shares)))
        o = res.orders
        return ok({"fee": float(o["fees"].sum()) if len(o) else None},
                  f"StrategyConfig(fee_mode=<FeeInfo -> 0.375 × info.shares>)、数量 2 の成行。orders: {o.to_dict('records')}")

    def scene_p7_account_swap(self, sc):
        from pybroker.portfolio import Portfolio
        rec = []

        class RecPortfolio(Portfolio):
            def buy(self, *a, **k):
                out = super().buy(*a, **k)
                if out is not None:
                    rec.append(float(out.shares))
                return out

        def f(ctx, n, st):
            if n == 1:
                ctx.buy_shares = 1

        df = _df([C.as_bar(e) for e in C.events(sc)])
        # round r8-1 (positive definition A): the settings through common.configure and the fixed window (until
        # round r8-1 this scene alone kept the scene's first and last row as the window)
        start, end = pd.Timestamp(C.FIXED_WINDOW[0]), pd.Timestamp(C.FIXED_WINDOW[1])
        config = C.configure(pb.StrategyConfig, initial_cash=100_000.0, what="StrategyConfig(initial_cash=100000.0)",
                             decided_from=("場面の入力",))
        s = C.configure(pb.Strategy, df, start, end, config, what=f"Strategy(場面の足の DataFrame, {start.date()}, {end.date()}, config)",
                        decided_from=("場面の入力", "選ぶ値"))
        cnt = {"n": 0}

        def exec_fn(ctx):
            cnt["n"] += 1
            f(ctx, cnt["n"], None)

        C.configure(s.add_execution, exec_fn, ["X"], what="add_execution(場面の戦略, [銘柄])", decided_from=("場面の入力",))
        try:
            s.backtest(portfolio=C.configure(RecPortfolio, 100_000.0, what="Portfolio の子(場面の口座: 現金 100,000)",
                                             decided_from=("場面の入力",)))
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"口座を渡す口 backtest(portfolio=...) に Portfolio の子を渡した -> {type(exc).__name__}: {str(exc)[:200]}")
        return ok({"account_recorded_fill_qty": rec}, "backtest(portfolio=<Portfolio の子>)。子の buy が返した約定の株数を記録した")

"""Survey candidate 16 `Luczinsritter/event_driven_backtesting_engine`, run in its own venv.

Source: GitHub `Luczinsritter/event_driven_backtesting_engine`, branch main,
commit 20929924806b5071dd92f9075c9bf97901e0011c (cloned 2026-09-24; not on
PyPI). Installed into the scratchpad venv `luczinsritter` with its
`requirements.txt`; a `.pth` file in that venv points at the clone, so
`import backtest_engine` is the tool's own module (see
`survey_results/attempts/16.log`).

What the tool is (backtest_engine.py): `FinancialData.__init__` reads the whole
OHLCV table through `get_data` (yfinance by default) and `add_log_returns`
drops the first row (`dropna`); `EventBased(FinancialData)` holds the cash,
one position and the helpers `get_date_price(i)`, `get_execution_price(i)`
(next row's open), `enter_long/enter_short/close_position(i, ...)`. The
engine does not call the strategy: a strategy subclasses `EventBased` and
writes its own loop, as the tool's two examples do (ema_arima.py:
`for i in range(len(self.data) - 1):  # -1 because get_execution_price(i+1)`).

How this adapter drives it (public extension points only, no monkeypatching):
  * `get_data` is overridden in the subclass to hand the scene's rows as the
    OHLCV DataFrame (SCAN 3292 行: 「get_data を差し替えるだけで当方の形の表を入れられる」),
    so no network is used;
  * the strategy's loop is the tool's example loop (`range(len(self.data) - 1)`)
    and calls the scene's strategy function once per row index;
  * the fill model is replaced by overriding `get_execution_price` in the
    subclass (the method the order helpers call).
Trades are handed as bars (open = high = low = close = price) where the
scene allows it (`any_type`).
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))
os.environ.setdefault("MPLBACKEND", "Agg")

import datetime as D  # noqa: E402

import pandas as pd  # noqa: E402

from protocol import Adapter, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

import backtest_engine as BE  # noqa: E402  (the tool's module, from the clone via a .pth in the venv)
import tradeanalysis as TA  # noqa: E402

LOOP = "for i in range(len(self.data) - 1)(道具の例 ema_arima.py の回し方)"


def _frame(rows: list[dict]) -> pd.DataFrame:
    bars = [C.as_bar(r) for r in rows]
    idx = pd.to_datetime([int(b["ts_ns"]) for b in bars], unit="ns", utc=True)
    return pd.DataFrame({"Open": [float(b["open"]) for b in bars], "High": [float(b["high"]) for b in bars],
                         "Low": [float(b["low"]) for b in bars], "Close": [float(b["close"]) for b in bars],
                         "Volume": [float(b.get("volume", 1.0)) for b in bars]}, index=idx)


def make(frame: pd.DataFrame, amount: float = 1_000_000.0, allow_negative_balance: bool = False, fill_price=None):
    """An EventBased strategy whose data is `frame` (the overridden get_data)."""

    class S(BE.EventBased):
        def get_data(self, ticker, end_date, interval):
            return frame.copy()

        if fill_price is not None:
            def get_execution_price(self, ind_nbr):  # the fill model: the order helpers call this
                return self.data.index[ind_nbr + 1], float(fill_price)

    with contextlib.redirect_stdout(io.StringIO()):
        return S("X", D.date(2023, 11, 20), 30, "1d", amount, allow_negative_balance)


def run(rows, fn, **kw):
    """Build the strategy on the scene's rows and run the tool's example loop."""
    s = make(_frame(rows), **kw)
    st = {"n": 0, "log": [], "rows_after_init": len(s.data)}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        for i in range(len(s.data) - 1):
            st["n"] += 1
            fn(s, i, st)
    st["printed"] = buf.getvalue()[-300:]
    return s, st


def _ts(s, i) -> int:
    return int(pd.Timestamp(s.get_date_price(i)[0]).value)


def _attempt_rows(rows: list[dict]) -> str:
    """A real attempt with rows that are not OHLCV bars: the tool reads the
    columns Open/High/Low/Close/Volume (get_data) and Close (add_log_returns)."""
    df = pd.DataFrame([C.fields_of(r) for r in rows], index=pd.to_datetime([r["ts_ns"] for r in rows], unit="ns", utc=True))
    try:
        make(df)
    except Exception as exc:  # noqa: BLE001
        return f"EventBased(<{list(df.columns)} の表>) -> {type(exc).__name__}: {str(exc)[:160]}"
    return "EventBased(<その表>) は例外なく作れた"


def _attempt_call(name: str, *args, **kw) -> str:
    s = make(_frame([{"kind": "bar", "ts_ns": 1_700_006_400_000_000_000 + k * 86_400_000_000_000, "open": 100.0,
                      "high": 100.0, "low": 100.0, "close": 100.0 + k, "volume": 1.0} for k in range(3)]))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            r = getattr(s, name)(*args, **kw)
    except Exception as exc:  # noqa: BLE001
        return f"s.{name}{args}{kw or ''} -> {type(exc).__name__}: {str(exc)[:160]}"
    return f"s.{name}{args} -> {r!r}"[:200]


NON_BAR = "この道具の入力は OHLCV の表 1 つ(get_data)で、{k} を事象として渡す口が無い。試したこと: {err}"


class LuczinsritterAdapter(Adapter):
    name = "opp_luczinsritter"

    # ---------------- P0-1
    def scene_p1_merge_by_time(self, sc):
        rows = [e for name in sc.input["hand_over_order"] for e in sc.input["streams"][name]]
        return not_supported(NON_BAR.format(k="複数の入力", err=_attempt_rows(rows)))

    def scene_p1_one_call_per_event(self, sc):
        car = []
        s, st = run(C.events(sc), lambda s, i, st: (st["log"].append(["bar", _ts(s, i)]), car.append(C.carrier(s.data))))
        return ok({"sequence": st["log"]}, f"足 {len(C.events(sc))} 本を get_data で渡し、{LOOP} の各回に get_date_price(i) の時刻。"
                  f"__init__ のあとの行数 {st['rows_after_init']}(add_log_returns の dropna が 1 行目を落とす)", {"carriers": car})

    def scene_p1_typed_events(self, sc):
        return not_supported(NON_BAR.format(k="約定", err=_attempt_rows(C.events(sc))))

    # ---------------- P0-2
    def _iso(self, sc):
        """The ISO string handed as it is to the tool's only data input (the index of the table get_data returns);
        a row one day earlier goes first because __init__'s dropna drops the first row."""
        iso = sc.input["iso"]
        prev = iso.replace("2024-01-01", "2023-12-31")
        df = pd.DataFrame({"Open": [1.0, 1.0], "High": [1.0, 1.0], "Low": [1.0, 1.0], "Close": [1.0, 2.0], "Volume": [1.0, 1.0]},
                          index=[prev, iso])
        try:
            s = make(df)
            v = s.get_date_price(0)[0]
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"添字が ISO の文字列の表を get_data から渡した -> {type(exc).__name__}: {str(exc)[:160]}")
        if not isinstance(v, pd.Timestamp):
            return not_supported(f"時刻の文字列を変換する入口が無い。試したこと: 添字が ISO の文字列の表を get_data から渡した -> get_date_price(0) の時刻 {v!r}"
                                 f"(型 {type(v).__name__}。変換されずに文字列のまま)")
        return ok(int((v if v.tzinfo is None else v.tz_convert("UTC")).value), f"EventBased が作った添字 {v!r}", {"reader": C.qualname(BE.EventBased)})

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    def _obs(self, sc):
        car = []
        s, st = run([{"kind": "bar", "ts_ns": e["ts_ns"], "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0 + k,
                      "volume": 1.0} for k, e in enumerate(C.events(sc))],
                    lambda s, i, st: (st["log"].append(_ts(s, i)), car.append(C.carrier(s.data))))
        return ok({"observed_ts_ns": st["log"]}, f"足で渡し、{LOOP} の各回に get_date_price(i) の時刻。__init__ のあとの行数 {st['rows_after_init']}"
                  "(dropna が 1 行目を落とす)。呼ばれた回数 " + str(st["n"]), {"carriers": car})

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _obs

    # ---------------- P0-3
    def _type(self, sc):
        e = C.events(sc)[0]
        if e["kind"] != "bar":
            return not_supported(NON_BAR.format(k=e["kind"], err=_attempt_rows([e])))
        out = {}
        car = []

        def f(s, i, st):
            st["log"].append(["bar", _ts(s, i)])
            car.append(C.carrier(s.data))
            row = s.data.iloc[i]
            out.update({k.lower(): float(row[k]) for k in ("Open", "High", "Low", "Close", "Volume")})

        s, st = run([e], f)
        return ok({"sequence": st["log"], "fields": out},
                  f"足 1 本を get_data で渡した。__init__ のあとの行数 {st['rows_after_init']}(dropna が 1 行目を落とす)、{LOOP} の回数 {st['n']}",
                  {"carriers": car})

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = _type

    def scene_p3_mixed_one_run(self, sc):
        return not_supported(NON_BAR.format(k="足以外の型", err=_attempt_rows(C.events(sc))))

    def scene_p3_clock_timer(self, sc):
        return not_supported("戦略を時刻で呼ぶ口が無い(回すのは戦略自身の for 文)。試したこと: "
                             + _attempt_call("set_timer", sc.input["timer_at_ns"]))

    def _notice(self, sc):
        return not_supported("注文の受付・拒否・約定・取消を知らせる口が無い(enter_long などは print するだけ)。"
                             f"EventBased の公開の名前: {[n for n in dir(BE.EventBased) if not n.startswith('_')]}。試したこと: "
                             + _attempt_call("on_order_update", "accepted"))

    scene_p3_notice_accepted = scene_p3_notice_rejected = scene_p3_notice_filled = _notice

    # ---------------- P0-4
    def scene_p4_visible_at_step(self, sc):
        probe = sc.input["probe_at_ns"]
        reads = C.Reads()

        def f(s, i, st):
            if _ts(s, i) == probe and not reads.items:
                reads.read("self.data['Close'](戦略が持つ表)", lambda: [float(x) for x in s.data["Close"]])

        s, st = run(C.events(sc), f)
        if not reads.items:  # no_probe_call
            return not_supported(f"T0 + 4 日の回が無かった({LOOP}。__init__ のあとの行数 {st['rows_after_init']})")
        return ok(reads.output(), f"T0 + 4 日の回({LOOP})に、戦略が持つ表 self.data の Close を読んだ", reads.provenance())

    def scene_p4_received_time(self, sc):
        return not_supported(NON_BAR.format(k="受け取れる時刻", err=_attempt_rows(
            [{"kind": "bar", "ts_ns": e["ts_ns"], "recv_ns": C.recv(e), "Close": e["price"]} for e in C.events(sc)]))
            + "(1 行の時刻は表の index の 1 つだけ)")

    def scene_p4_future_read_attempt(self, sc):
        probe = sc.input["probe_at_ns"]
        att = C.Attempts()

        def f(s, i, st):
            if _ts(s, i) != probe or att.items:
                return
            # namings: the scene's fixed list; positions count the table's rows (the newest delivered is i, the next i + 1)
            C.try_position_namings(att, "self.get_date_price(位置) の値", lambda: C.KeyCall(lambda k: s.get_date_price(k)[1]), i + 1)
            C.try_position_namings(att, "self.data['Close'].iloc[位置]", lambda: s.data["Close"].iloc, i + 1)
            ts = (lambda ns: pd.Timestamp(int(ns), unit="ns", tz="UTC"))
            C.try_time_namings(att, "self.data['Close'].loc[時刻]", "time_at", lambda t: float(s.data["Close"].loc[t]), sc, ts)
            C.try_time_namings(att, "self.data['Close'].loc[始:終]", "time_range", lambda a, b: list(s.data["Close"].loc[a:b]), sc, ts)
            att.run("self.data['Close'] の全部", "other", lambda: [float(x) for x in s.data["Close"]])

        run(C.events(sc), f)
        if not att.items:  # no_probe_call
            return not_supported("T0 + 4 日の回が無かったので、先を読む試しができなかった")
        return ok(att.output(), f"T0 + 4 日の回({LOOP})で試した: " + att.summary())

    # ---------------- P0-5
    def _no_types(self, sc):
        rows = [e for name in sc.input["hand_over_order"] for e in sc.input["streams"][name]] if "hand_over_order" in sc.input \
            else [e for name in sc.input["hand_over_orders"][0] for e in sc.input["streams"][name]]
        return not_supported(NON_BAR.format(k="約定・資金調達・清算", err=_attempt_rows(rows)))

    scene_p5_same_time_twice = scene_p5_hand_over_order = _no_types

    def scene_p5_same_stream_order(self, sc):
        car = []
        s, st = run(C.events(sc), lambda s, i, st: (st["log"].append(float(s.data["Close"].iloc[i])), car.append(C.carrier(s.data))))
        return ok({"prices": st["log"]}, f"約定を足に代え、同じ時刻の 3 行を渡した。__init__ のあとの行数 {st['rows_after_init']}、{LOOP} の回数 {st['n']}",
                  {"carriers": car})

    # ---------------- P0-6
    def scene_p6_place_then_cancel(self, sc):
        return not_supported("指値を出す口・取り消す口・未決の注文を読む口が無い(enter_long/enter_short は次の行の始値で必ず埋まる)。試したこと: "
                             + _attempt_call("enter_long", 0, units=1, price=90.0) + " ; " + _attempt_call("cancel_order", 1))

    def scene_p6_cancel_notice(self, sc):
        return not_supported("取消の口も通知の口も無い。試したこと: " + _attempt_call("cancel_order", 1))

    def scene_p6_fill_seen_by_strategy(self, sc):
        out = {}

        def f(s, i, st):
            if st["n"] == 1:
                s.enter_long(i, units=1)
            elif st["n"] == 3:
                out["filled_qty_at_call3"] = float(s.position["units"])

        s, st = run(C.events(sc), f)
        if "filled_qty_at_call3" not in out:
            return ok({"filled_qty_at_call3": None},
                      f"1 回目に enter_long(i, units=1)。3 回目の回が無かった({LOOP}、__init__ のあとの行数 {st['rows_after_init']}、回数 {st['n']})")
        return ok(out, "1 回目に enter_long(i, units=1)、3 回目に self.position['units']")

    # ---------------- P0-7
    def scene_p7_fill_model_swap(self, sc):
        out = {}

        def f(s, i, st):
            if st["n"] == 1:
                s.enter_long(i, units=1)
                out["fill_price"] = float(s.position["entry_price"])

        s, st = run(C.events(sc), f, amount=100_000.0, fill_price=12345.0)
        return ok(out, "EventBased の子で get_execution_price を上書きし(注文の口 enter_long が呼ぶ)、価格 12345.0 を返す模型にした。"
                  f"1 回目に enter_long(i, units=1)、self.position['entry_price'] を読んだ。回数 {st['n']}")

    def scene_p7_latency_model_swap(self, sc):
        return not_supported("遅延の模型を渡す口が無い(約定は次の行の始値、get_execution_price)。試したこと: "
                             + _attempt_call("enter_long", 0, units=1, latency_ns=7_000_000))

    def _fee(self, sc, per_trade):
        s, st = run(C.events(sc), lambda s, i, st: s.enter_long(i, units=1) if st["n"] == 1 else None, amount=100_000.0)
        ta = TA.TradeAnalysis(trade_performance=s.trade_performance, capital=100_000, cost_per_trade=per_trade, slippage=0,
                              price_series=s.data["Close"])
        try:
            df = ta._prepare_df()
            got = f"TradeAnalysis(cost_per_trade={per_trade})._prepare_df() -> 列 {list(df.columns)}、行 {len(df)}"
        except Exception as exc:  # noqa: BLE001
            got = f"TradeAnalysis(cost_per_trade={per_trade})._prepare_df() -> {type(exc).__name__}: {str(exc)[:120]}"
        return not_supported("約定に費用を付ける口が無い。費用の入力は、走ったあとの分析 TradeAnalysis の cost_per_trade(閉じた取引の単純収益から "
                             "cost_per_trade / capital を引く、tradeanalysis.py _prepare_df)だけで、約定の記録(self.position)に費用の欄は無い。"
                             f"試したこと: 1 回目に enter_long(i, units=1)、self.position = {s.position} ; {got}")

    def scene_p7_cost_model_swap(self, sc):
        return self._fee(sc, 0.5)

    def scene_p7_cost_per_unit(self, sc):
        return self._fee(sc, 0.375)  # a per-trade constant: the quantity cannot enter it

    def scene_p7_account_swap(self, sc):
        return not_supported("口座は EventBased の中の current_balance と position の辞書で、差し替える口が無い。試したこと: "
                             + _attempt_call("set_account", object()))

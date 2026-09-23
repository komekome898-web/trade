"""Adapter for our current environment (当方の現状): the unmodified
`src/bot/backtest/engine.py: run_backtest` with `src/bot/strategy/base.py:
Strategy`, fed a pandas DataFrame of OHLCV rows indexed by a
`DatetimeIndex` (datetime64[ns, UTC]) -- the input form the engine takes
(`candles`, engine.py docstring and `candles["close"]` etc.). Time
conversion on our data path is pandas (`pd.to_datetime(..., utc=True)`, as
in `src/bot/research/board.py`), so the ISO scenes use `pd.Timestamp`.

This adapter only imports and calls the engine; it edits nothing.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3] / "src"))

from protocol import Adapter, SceneResult, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

from bot.backtest import engine as E  # noqa: E402
from bot.strategy.base import Signal, SignalType, Strategy  # noqa: E402


def _df(rows: list[dict]) -> pd.DataFrame:
    idx = pd.to_datetime([r["ts_ns"] for r in rows], unit="ns", utc=True)
    return pd.DataFrame([{k: r[k] for k in ("open", "high", "low", "close", "volume")} for r in rows], index=idx)


class _Rec(Strategy):
    """Records what the engine hands over on each call; can emit signals by call number."""

    def __init__(self, signals: dict[int, SignalType] | None = None, probe=None) -> None:
        super().__init__()
        self.seen: list[pd.DataFrame] = []
        self.signals = signals or {}
        self.probe = probe
        self.probe_out = None

    @property
    def min_history(self) -> int:
        return 0

    def on_candles(self, candles: pd.DataFrame) -> Signal:
        self.seen.append(candles)
        n = len(self.seen)
        if self.probe is not None:
            out = self.probe(n, candles)
            if out is not None:
                self.probe_out = out
        return Signal(type=self.signals.get(n, SignalType.HOLD))


def _run(rows: list[dict], **kw) -> tuple[_Rec, object]:
    rec = kw.pop("rec", None) or _Rec()
    res = E.run_backtest(rec, _df(rows), **kw)
    return rec, res


def _try_non_bar(rows: list[dict]) -> str:
    """Hand non-OHLCV rows to the engine the only way it takes data and report what happened."""
    idx = pd.to_datetime([r["ts_ns"] for r in rows], unit="ns", utc=True)
    df = pd.DataFrame([C.fields_of(r) for r in rows], index=idx)
    try:
        E.run_backtest(_Rec(), df)
    except Exception as exc:  # noqa: BLE001
        return f"run_backtest(strategy, candles=<{list(df.columns)} の DataFrame>) -> {type(exc).__name__}: {exc}"
    return "run_backtest は例外を出さずに走った"


def _no_kw(kw: str) -> str:
    try:
        E.run_backtest(_Rec(), _df([C.as_bar({'kind': 'trade', 'ts_ns': 1, 'price': 1.0})]), **{kw: object()})
    except TypeError as exc:
        return f"run_backtest(..., {kw}=...) -> TypeError: {exc}"
    return f"run_backtest(..., {kw}=...) は受け付けられた"


def _seq(rec: _Rec) -> list:
    return [["bar", int(c.index[-1].value)] for c in rec.seen]


def _signal_attempt(field: str) -> str:
    try:
        Signal(type=SignalType.HOLD, **{field: 1})
    except TypeError as exc:
        return f"Signal(type=HOLD, {field}=...) -> TypeError: {exc}"
    return f"Signal(..., {field}=...) は受け付けられた"


class CurrentImplAdapter(Adapter):
    name = "current_impl"

    # ---------------- P0-1
    def scene_p1_merge_by_time(self, sc):
        rows = C.concatenated(sc)
        return not_supported("足以外(約定・資金調達)を含む入力を渡す口が無い。試したこと: " + _try_non_bar(rows)
                             + "。run_backtest の入力は candles 1 つだけ(複数の入力を渡す引数も無い: " + _no_kw("streams") + ")")

    def scene_p1_one_call_per_event(self, sc):
        rec, _ = _run(C.events(sc))
        return ok({"sequence": _seq(rec)}, "足 5 本を DataFrame で渡し、on_candles の各呼び出しで candles の最後の行の時刻を記録")

    def scene_p1_typed_events(self, sc):
        return not_supported("約定を渡す口が無い。試したこと: " + _try_non_bar(C.events(sc)[1:]))

    # ---------------- P0-2
    def scene_p2_iso_utc(self, sc):
        v = int(pd.Timestamp(sc.input["iso"]).value)
        return ok(v, "当方のデータの道の時刻の変換(pandas)で pd.Timestamp(iso).value")

    def scene_p2_iso_offset(self, sc):
        v = int(pd.Timestamp(sc.input["iso"]).tz_convert("UTC").value)
        return ok(v, "pd.Timestamp(iso).tz_convert('UTC').value")

    def _ts_scene(self, sc):
        rows = [dict(C.as_bar({"kind": "trade", "ts_ns": e["ts_ns"], "price": 100.0}), volume=1.0) for e in C.events(sc)]
        rec, _ = _run(rows)
        return ok({"observed_ts_ns": [int(c.index[-1].value) for c in rec.seen]},
                  "足(OHLC=100)で渡し、各呼び出しの candles.index[-1].value を記録")

    def scene_p2_event_time_exact(self, sc):
        return self._ts_scene(sc)

    def scene_p2_one_ns_apart(self, sc):
        return self._ts_scene(sc)

    # ---------------- P0-3
    def _type_scene(self, sc):
        e = C.events(sc)[0]
        if e["kind"] != "bar":
            return not_supported(f"「{e['kind']}」を渡す口が無い。試したこと: " + _try_non_bar([e]))
        rec, _ = _run([e])
        last = rec.seen[0].iloc[-1]
        fields = {k: float(last[k]) for k in ("open", "high", "low", "close", "volume")}
        return ok({"sequence": _seq(rec), "fields": fields}, "足 1 本を渡し、呼び出しで受け取った行を記録")

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type_scene
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = _type_scene

    def scene_p3_mixed_one_run(self, sc):
        return not_supported("足以外の 5 種を渡す口が無い。試したこと: " + _try_non_bar([e for e in C.events(sc) if e["kind"] != "bar"]))

    def scene_p3_clock_timer(self, sc):
        return not_supported("戦略は on_candles から Signal を返すだけで、時刻を頼む口が無い。試したこと: "
                             + _signal_attempt("timer_ns") + " / " + _no_kw("timers"))

    def _notice(self, sc):
        called = []

        class Spy(_Rec):
            def __getattribute__(self, name):
                if not name.startswith("_") and name not in ("seen", "signals", "probe", "probe_out", "params"):
                    called.append(name)
                return super().__getattribute__(name)

        rows = [C.as_bar(e) for e in C.events(sc)]
        spy = Spy(signals={1: SignalType.BUY})
        E.run_backtest(spy, _df(rows))
        return not_supported("戦略へ通知を届ける呼び出しが無い。試したこと: 約定を足に代えて(any_type)1 回目に BUY を返し、"
                             f"エンジンが戦略に対して呼んだ名前を記録 -> {sorted(set(called))}(on_candles と min_history だけ)。"
                             "Strategy の文書(base.py 2〜4 行)も「注文を知らない」と書く")

    scene_p3_notice_accepted = scene_p3_notice_rejected = scene_p3_notice_filled = _notice

    # ---------------- P0-4
    def scene_p4_visible_at_step(self, sc):
        probe = sc.input["probe_at_ns"]
        rec = _Rec(probe=lambda n, c: {"visible_count": len(c), "max_visible_close": float(c["close"].max())} if int(c.index[-1].value) == probe else None)
        _run(C.events(sc), rec=rec)
        if not rec.probe_out:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった")
        return ok(rec.probe_out, "T0 + 4 日の呼び出しの on_candles で受け取った candles の件数と close の最大")

    def scene_p4_received_time(self, sc):
        return not_supported("1 件に時刻を 1 つしか持てない(candles の DataFrame の添字 1 つ)。受け取れる時刻を別に渡す口が無い。試したこと: "
                             + _no_kw("received_time") + " / " + _no_kw("latency"))

    def scene_p4_future_read_attempt(self, sc):
        probe = sc.input["probe_at_ns"]
        future_ts = pd.Timestamp([e for e in sc.input["events"] if e["ts_ns"] > probe][0]["ts_ns"], unit="ns", tz="UTC")
        tried: list[str] = []

        def probe_fn(n, c):
            if int(c.index[-1].value) != probe:
                return None
            got = False
            for label, fn in [("candles.iloc[4]", lambda: c.iloc[4]["close"]),
                              ("candles.loc[5 本目の時刻]", lambda: c.loc[future_ts]["close"]),
                              ("candles.iloc[-1] の次を shift(-1) で", lambda: c["close"].shift(-1).iloc[-1])]:
                try:
                    v = fn()
                    tried.append(f"{label} -> {v}")
                    if v == 104.0:
                        got = True
                except Exception as exc:  # noqa: BLE001
                    tried.append(f"{label} -> {type(exc).__name__}")
            return {"future_value_obtained": got}

        rec = _Rec(probe=probe_fn)
        _run(C.events(sc), rec=rec)
        if not tried:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった")
        return ok(rec.probe_out, "T0 + 4 日の呼び出しの on_candles の中で試した: " + "; ".join(tried)
                  + "。戦略が持つのは渡された candles だけ(エンジンは candles.iloc[: i + 1] を渡す)")

    # ---------------- P0-5
    def scene_p5_same_time_twice(self, sc):
        return not_supported("同時刻の 4 種(約定・足・資金調達・清算)のうち足以外を渡す口が無い。試したこと: "
                             + _try_non_bar(C.concatenated(sc)))

    def scene_p5_hand_over_order(self, sc):
        return not_supported("足以外を渡す口が無い。試したこと: " + _try_non_bar(C.concatenated(sc, sc.input["hand_over_orders"][0])))

    def scene_p5_same_stream_order(self, sc):
        rows = [C.as_bar(e) for e in C.events(sc)]
        rec, _ = _run(rows)
        return ok({"prices": [float(c["close"].iloc[-1]) for c in rec.seen]}, "約定を足に代えて渡し、呼び出しごとの close を記録")

    # ---------------- P0-6
    def scene_p6_place_then_cancel(self, sc):
        return not_supported("戦略に指値を出す口・取り消す口・未決の注文を読む口が無い。Signal は BUY/SELL/CLOSE/HOLD だけ。試したこと: "
                             + _signal_attempt("limit_price") + " / " + _signal_attempt("cancel"))

    def scene_p6_cancel_notice(self, sc):
        return not_supported("取消の口も通知の口も無い。試したこと: " + _signal_attempt("cancel"))

    def scene_p6_fill_seen_by_strategy(self, sc):
        seen_attrs = []

        def probe(n, c):
            if n == 3:
                seen_attrs.append(sorted(a for a in dir(c) if "fill" in a.lower() or "order" in a.lower() or "position" in a.lower())[:5])
            return None

        rec = _Rec(signals={1: SignalType.BUY}, probe=probe)
        _run([C.as_bar(e) for e in C.events(sc)], rec=rec)
        return not_supported("戦略が受け取るのは candles だけで、自分の注文・約定を読む口が無い。試したこと: 1 回目に BUY を返し、"
                             f"3 回目に受け取った引数を調べた(candles の DataFrame だけ。注文・建玉に当たる属性 {seen_attrs})")

    # ---------------- P0-7
    def _buy_once(self, sc, **kw):
        rows = [C.as_bar(e) for e in C.events(sc)]
        rec = _Rec(signals={1: SignalType.BUY})
        res = E.run_backtest(rec, _df(rows), order_notional_jpy=100.0, initial_equity_jpy=100_000.0, **kw)
        return rows, res

    def scene_p7_fill_model_swap(self, sc):
        class FixedPrice(E.CostModel):
            def buy_price(self, ref_price: float) -> float:
                return 12345.0

        _, res = self._buy_once(sc, costs=FixedPrice())
        opens = [t for t in res.trade_log if t["side"].startswith("OPEN")]
        return ok({"fill_price": float(opens[0]["price"]) if opens else None},
                  "約定の模型を渡す口は無いが、公開の CostModel の buy_price を上書きした子を costs= に渡すと約定の価格が決まる"
                  f"(engine.py: price = costs.buy_price(ref))。trade_log の OPEN の価格を読んだ: {opens}")

    def scene_p7_latency_model_swap(self, sc):
        return not_supported("遅延の模型を渡す口が無い(約定は常に次の足の始値)。試したこと: " + _no_kw("latency_model")
                             + " / " + _no_kw("order_delay_ns"))

    def _fee(self, sc, fee_value):
        class Fixed(E.CostModel):
            def fee(self, notional: float) -> float:
                return fee_value

        _, res = self._buy_once(sc, costs=Fixed(spread_pct=0.0, slippage_pct=0.0))
        return ok({"fee": float(res.metrics.total_fees_jpy)},
                  f"CostModel の fee を上書きした子を costs= に渡し、約定 1 件(建玉を開いたまま終わる)の metrics.total_fees_jpy を読んだ。trade_log={res.trade_log}")

    def scene_p7_cost_model_swap(self, sc):
        return self._fee(sc, 0.5)

    def scene_p7_cost_zero(self, sc):
        return self._fee(sc, 0.0)

    def scene_p7_account_swap(self, sc):
        return not_supported("口座を渡す口が無い(現金・建玉は run_backtest の中の局所変数)。試したこと: " + _no_kw("account")
                             + " / " + _no_kw("portfolio"))

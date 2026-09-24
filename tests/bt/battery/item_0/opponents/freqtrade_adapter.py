"""Survey candidate 75 `Freqtrade` (PyPI `freqtrade` 2026.8), run in its own venv.

Driven through its public API without any network: `freqtrade.exchange.
Exchange(config, validate=False)` (validate=False skips the markets download;
the one synthetic market is set on `_markets`), `freqtrade.optimize.
backtesting.Backtesting(config, exchange=...)` and `Backtesting.
backtest_one_strategy(strategy, {pair: DataFrame}, timerange)` (the call its
own `start()` makes after reading the data files), a strategy file (an
`IStrategy` subclass) whose methods forward to this adapter.

Network guard: `socket.socket.connect` is replaced before freqtrade is
imported, so any connection attempt raises locally and is recorded
(`NET_ATTEMPTS`); every scene's detail reports the count.

Freqtrade's candle `date` is the candle's open time. A bar whose close is
T0 + i DAY is the candle dated T0 + (i-1) DAY. The strategy is called per
candle through `bot_loop_start(current_time)`; entries and exits are signal
columns set by `populate_entry_trend` / `populate_exit_trend` over the whole
DataFrame, filled by the engine on the next candle.
"""
from __future__ import annotations

import socket
import sys
import tempfile
import types
from pathlib import Path

NET_ATTEMPTS: list = []


def _guard(self, addr, *a, **k):
    NET_ATTEMPTS.append(str(addr))
    raise OSError(f"network blocked by the adapter guard: {addr}")


socket.socket.connect = _guard  # before freqtrade / ccxt are imported

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

import logging  # noqa: E402

import pandas as pd  # noqa: E402

from protocol import Adapter, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

logging.disable(logging.CRITICAL)

from freqtrade.configuration import TimeRange  # noqa: E402
from freqtrade.enums import RunMode  # noqa: E402
from freqtrade.exchange import Exchange  # noqa: E402
from freqtrade.optimize.backtesting import Backtesting  # noqa: E402

DAY = 86_400 * 10**9
PAIR = "X/JPY"
_ROOT = Path(tempfile.mkdtemp(prefix="freqtrade_sk_"))
_HOOKS = types.ModuleType("_ft_hooks")
sys.modules["_ft_hooks"] = _HOOKS
(_ROOT / "SkStrategy.py").write_text('''
import sys
from freqtrade.strategy import IStrategy
H = sys.modules["_ft_hooks"]


class SkStrategy(IStrategy):
    timeframe = "1d"
    minimal_roi = {"0": 1000.0}
    stoploss = -0.99
    startup_candle_count = 0
    process_only_new_candles = False
    use_exit_signal = True

    def populate_indicators(self, df, md):
        r = H.call("ind", self, df, md)
        return df if r is None else r

    def populate_entry_trend(self, df, md):
        df["enter_long"] = 0
        r = H.call("entry", self, df, md)
        return df if r is None else r

    def populate_exit_trend(self, df, md):
        df["exit_long"] = 0
        return df

    def bot_loop_start(self, current_time, **kw):
        H.call("loop", self, current_time)

    def custom_entry_price(self, pair, trade, current_time, proposed_rate, entry_tag, side, **kw):
        v = H.call("entry_price", self, current_time, proposed_rate)
        return proposed_rate if v is None else v

    def custom_stake_amount(self, pair, current_time, current_rate, proposed_stake, min_stake, max_stake, leverage, entry_tag, side, **kw):
        v = H.call("stake", self, current_rate, proposed_stake)
        return proposed_stake if v is None else v

    def check_entry_timeout(self, pair, trade, order, current_time, **kw):
        return bool(H.call("entry_timeout", self, trade, order, current_time))

    def order_filled(self, pair, trade, order, current_time, **kw):
        H.call("filled", self, trade, order, current_time)
''')


def _call(name, *a):
    fn = getattr(_HOOKS, name, None)
    return fn(*a) if fn else None


_HOOKS.call = _call


def _market():
    return {PAIR: {"id": "XJPY", "symbol": PAIR, "base": "X", "quote": "JPY", "active": True, "spot": True, "type": "spot",
                   "precision": {"amount": 1e-8, "price": 1e-8},
                   "limits": {"amount": {"min": 1e-8, "max": None}, "cost": {"min": 0, "max": None}, "price": {"min": None, "max": None}},
                   "contractSize": None, "linear": None, "inverse": None, "maker": 0.0, "taker": 0.0, "info": {}}}


def _config(wallet, fee):
    d = Path(tempfile.mkdtemp(dir=_ROOT))
    return {"exchange": {"name": "binance", "pair_whitelist": [PAIR], "pair_blacklist": []}, "stake_currency": "JPY",
            "stake_amount": "unlimited", "dry_run": True, "dry_run_wallet": wallet, "timeframe": "1d", "max_open_trades": 1,
            "fee": fee, "pairlists": [{"method": "StaticPairList"}], "entry_pricing": {"price_side": "same"},
            "exit_pricing": {"price_side": "same"}, "strategy": "SkStrategy", "strategy_path": str(_ROOT), "user_data_dir": d,
            "datadir": d, "export": "none", "trading_mode": "spot", "margin_mode": "", "dataformat_ohlcv": "feather",
            "runmode": RunMode.BACKTEST, "original_config": {}, "candle_type_def": "spot", "backtest_cache": "none",
            "unfilledtimeout": {"entry": 100000, "exit": 100000, "unit": "minutes"},
            "order_types": {"entry": "limit", "exit": "limit", "stoploss": "limit", "stoploss_on_exchange": False}}


def run(bars, hooks: dict, wallet=1_000_000.0, fee=0.0):
    """Run the bars through Backtesting. `hooks` maps hook names (ind / entry /
    loop / entry_price / stake / entry_timeout / filled) to functions."""
    rows = [C.as_bar(b) for b in bars]
    for k in ("ind", "entry", "loop", "entry_price", "stake", "entry_timeout", "filled"):
        setattr(_HOOKS, k, hooks.get(k))
    cfg = _config(wallet, fee)
    ex = Exchange(cfg, validate=False)
    ex._markets = _market()
    bt = Backtesting(cfg, exchange=ex)
    dates = pd.to_datetime([int(b["ts_ns"]) - DAY for b in rows], unit="ns", utc=True)
    df = pd.DataFrame({"date": dates, **{k: [float(b[k]) for b in rows] for k in ("open", "high", "low", "close")},
                       "volume": [float(b.get("volume", 1.0)) for b in rows]})
    tr = TimeRange("date", "date", int(dates.min().timestamp()), int(dates.max().timestamp()) + 86_400)
    bt.timerange = tr
    bt.backtest_one_strategy(bt.strategylist[0], {PAIR: df}, tr)
    return bt, bt.all_bt_content["SkStrategy"]


def _ns(t) -> int:
    return int(pd.Timestamp(t).value)


def _net() -> str:
    return f"接続の試み {len(NET_ATTEMPTS)} 件(adapter の socket の関門で数えた)"


NON_BAR = ("Freqtrade の入力は、組ごと・時間足ごとの OHLCV の DataFrame(date/open/high/low/close/volume)で、{k} を型として"
           "戦略に渡す口が無い(informative の組も同じ OHLCV)。試したこと: {k} の列だけの DataFrame を backtest_one_strategy に渡した -> {err}")


def _try_non_bar(e: dict) -> str:
    try:
        cfg = _config(1e6, 0.0)
        ex = Exchange(cfg, validate=False)
        ex._markets = _market()
        bt = Backtesting(cfg, exchange=ex)
        df = pd.DataFrame({"date": pd.to_datetime([int(e["ts_ns"])], unit="ns", utc=True),
                           **{k: [v] for k, v in C.fields_of(e).items() if not isinstance(v, list)}})
        tr = TimeRange("date", "date", int(e["ts_ns"]) // 10**9 - 86_400, int(e["ts_ns"]) // 10**9 + 86_400)
        bt.backtest_one_strategy(bt.strategylist[0], {PAIR: df}, tr)
    except Exception as exc:  # noqa: BLE001
        return f"{type(exc).__name__}: {str(exc)[:160]}"
    return "例外なく走った"


class FreqtradeAdapter(Adapter):
    name = "opp_freqtrade"

    # ---------------- P0-1
    def scene_p1_merge_by_time(self, sc):
        return not_supported(NON_BAR.format(k="約定・資金調達", err=_try_non_bar(sc.input["streams"]["trades"][0])) + "。" + _net())

    def _seq(self, bars):
        log = []
        run(bars, {"loop": lambda s, t: log.append(["bar", _ns(t)])})
        return log

    def scene_p1_one_call_per_event(self, sc):
        return ok({"sequence": self._seq(C.events(sc))}, "日足 5 本。bot_loop_start(current_time) の各回を記録(足ごとに 1 回呼ぶ唯一の口)。"
                  "Freqtrade は最初の足を次の足の信号の元にだけ使い、current_time は処理する足の始まり。" + _net())

    def scene_p1_typed_events(self, sc):
        return not_supported(NON_BAR.format(k="約定", err=_try_non_bar(C.events(sc)[1])) + "。" + _net())

    # ---------------- P0-2
    def _iso(self, sc):
        return ok(int(pd.Timestamp(sc.input["iso"]).tz_convert("UTC").value),
                  "Freqtrade の足の date は pandas の datetime64[ns, UTC]。pd.Timestamp(iso).tz_convert('UTC').value")

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    def _ts(self, sc):
        evs = [{"kind": "bar", "ts_ns": e["ts_ns"], "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 1.0}
               for e in C.events(sc)]
        try:
            log = self._seq(evs)
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"ナノ秒の時刻の足を backtest_one_strategy に渡した -> {type(exc).__name__}: {str(exc)[:200]}。{_net()}")
        return ok({"observed_ts_ns": [t for _, t in log]}, f"足で渡した。bot_loop_start の current_time(時間足の刻みで作られる)。{_net()}")

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _ts

    # ---------------- P0-3
    def _type(self, sc):
        e = C.events(sc)[0]
        if e["kind"] != "bar":
            return not_supported(NON_BAR.format(k=e["kind"], err=_try_non_bar(e)) + "。" + _net())
        out, log = {}, []

        def loop(s, t):
            log.append(["bar", _ns(t)])
            df, _ = s.dp.get_analyzed_dataframe(PAIR, "1d")
            if len(df):
                out.update({k: float(df.iloc[-1][k]) for k in ("open", "high", "low", "close", "volume")})

        run([e], {"loop": loop})
        return ok({"sequence": log, "fields": out}, "日足 1 本。bot_loop_start の中で dp.get_analyzed_dataframe の最後の行を読んだ。" + _net())

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = _type

    def scene_p3_mixed_one_run(self, sc):
        e = [x for x in C.events(sc) if x["kind"] != "bar"][0]
        return not_supported(NON_BAR.format(k="足以外の 5 種", err=_try_non_bar(e)) + "。" + _net())

    def scene_p3_clock_timer(self, sc):
        tried = []

        def loop(s, t):
            if not tried:
                for label, fn in [("self.schedule(...)", lambda: s.schedule(lambda: None, sc.input["timer_at_ns"])),
                                  ("self.dp.schedule(...)", lambda: s.dp.schedule(lambda: None, sc.input["timer_at_ns"]))]:
                    try:
                        fn()
                        tried.append(f"{label} -> 通った")
                    except Exception as exc:  # noqa: BLE001
                        tried.append(f"{label} -> {type(exc).__name__}: {str(exc)[:100]}")

        run([C.as_bar(e) for e in C.events(sc)], {"loop": loop})
        return not_supported("時刻を指定して戦略を起こす口が無い(戦略を呼ぶ時刻は足の刻みの bot_loop_start だけ)。"
                             f"1 回目の bot_loop_start の中で試した: {tried}。{_net()}")

    def _notice_run(self, sc, wallet, limit=None):
        seen = []

        def filled(s, trade, order, t):
            seen.append(("filled", float(order.safe_filled), _ns(t), order.ft_order_side))

        hooks = {"entry": _entry_first, "filled": filled, "stake": lambda s, rate, prop: rate * 1.0}
        if limit is not None:
            hooks["entry_price"] = lambda s, t, r: limit
        bt, res = run([C.as_bar(e) for e in C.events(sc)], hooks, wallet=wallet)
        return seen, res

    def scene_p3_notice_accepted(self, sc):
        seen, res = self._notice_run(sc, 1_000_000.0, limit=90.0)
        return not_supported("注文の受付を戦略に知らせる呼び出しが無い(戦略への知らせは約定の order_filled だけ。発注前の確認 "
                             "confirm_trade_entry は戦略が許すかを問う呼び出しで、受付の知らせではない)。"
                             f"試したこと: 1 本目の足に enter_long=1、custom_entry_price=90 で走らせ、呼ばれた知らせ {seen}。{_net()}")

    def scene_p3_notice_rejected(self, sc):
        seen, res = self._notice_run(sc, 1_000.0)
        return not_supported("注文の拒否を戦略に知らせる呼び出しが無い。試したこと: 現金 1,000、1 本目の足に enter_long=1(数量 1 = "
                             f"stake を価格ちょうど)で走らせ、呼ばれた知らせ {seen}、結果の rejected_signals {res.get('rejected_signals')}。{_net()}")

    def scene_p3_notice_filled(self, sc):
        seen, res = self._notice_run(sc, 1_000_000.0)
        return ok({"filled_qty_in_notices": sum(q for n, q, _, side in seen if n == "filled" and side == "buy"),
                   "notices": [n for n, *_ in seen]},
                  "order_filled(pair, trade, order, current_time) の order.safe_filled を、戦略が出した買いの注文の分だけ足した"
                  f"(売りは走行の終わりに Freqtrade が自分で閉じた分)。呼ばれた知らせ {seen}。{_net()}")

    # ---------------- P0-4
    def scene_p4_visible_at_step(self, sc):
        probe = sc.input["probe_at_ns"]
        out, seen = {}, []

        def loop(s, t):
            df, _ = s.dp.get_analyzed_dataframe(PAIR, "1d")
            seen.append((_ns(t), [float(x) for x in df["close"]] if len(df) else []))
            if _ns(t) == probe:
                vis = [float(x) for x in df["close"]] if len(df) else []
                out.update({"visible_count": len(vis), "max_visible_close": max(vis) if vis else None})

        run(C.events(sc), {"loop": loop})
        if not out:  # no_probe_call
            return not_supported(f"T0 + 4 日の呼び出しが無かった。呼び出しと見えた終値 {seen}。{_net()}")
        return ok(out, f"bot_loop_start の中で dp.get_analyzed_dataframe の close を数えた。各回 {seen}。{_net()}")

    def scene_p4_received_time(self, sc):
        return not_supported("足は 1 本に時刻 1 つ(date)で、受け取れる時刻を別に持たせる口が無い。試したこと: recv の列を足した DataFrame -> "
                             + _try_non_bar({"ts_ns": sc.input["events"][0]["ts_ns"], "open": 1.0, "high": 1.0, "low": 1.0,
                                             "close": 1.0, "volume": 1.0, "recv_ns": 1}) + "。" + _net())

    def scene_p4_future_read_attempt(self, sc):
        probe = sc.input["probe_at_ns"]
        fut = pd.Timestamp(sc.input["future_ts_ns"], unit="ns", tz="UTC")
        att, keep = C.Attempts(), {}

        def ind(s, df, md):
            keep["df"] = df
            return df

        def loop(s, t):
            if _ns(t) != probe or att.items:
                return
            adf = s.dp.get_analyzed_dataframe(PAIR, "1d")[0]
            att.run("dp.get_analyzed_dataframe の close の .iloc[len](最新の次の位置)", "position", lambda: float(adf["close"].iloc[len(adf)]))
            att.run("dp.get_analyzed_dataframe の date == 5 本目の日 の close", "time",
                    lambda: [float(x) for x in adf.loc[adf["date"] == fut, "close"]])
            att.run("dp.get_analyzed_dataframe の close(全部)", "other", lambda: [float(x) for x in adf["close"]])
            att.run("dp.get_pair_dataframe の close(全部)", "other", lambda: [float(x) for x in s.dp.get_pair_dataframe(PAIR, "1d")["close"]])
            att.run("populate_indicators に渡された DataFrame の close(全部)", "other", lambda: [float(x) for x in keep["df"]["close"]])

        run(C.events(sc), {"ind": ind, "loop": loop})
        if not att.items:  # no_probe_call
            return not_supported(f"T0 + 4 日の呼び出しが無かった。{_net()}")
        return ok(att.output(), "T0 + 4 日の bot_loop_start の中で試した: " + att.summary() + "。" + _net())

    def _no_types(self, sc):
        return not_supported(NON_BAR.format(k="約定・資金調達・清算", err=_try_non_bar(sc.input["streams"]["trades"][0])) + "。" + _net())

    scene_p5_same_time_twice = scene_p5_hand_over_order = _no_types

    def scene_p5_same_stream_order(self, sc):
        seen = []

        def loop(s, t):
            df, _ = s.dp.get_analyzed_dataframe(PAIR, "1d")
            seen.append((_ns(t), [float(x) for x in df["close"]] if len(df) else []))

        try:
            run([C.as_bar(e) for e in C.events(sc)], {"loop": loop})
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"同じ時刻の 3 本を渡した -> {type(exc).__name__}: {str(exc)[:200]}。{_net()}")
        prices = seen[-1][1] if seen else []
        return ok({"prices": prices}, f"同じ時刻の 3 本(終値 101・99・100)を渡した。各回の dp.get_analyzed_dataframe の close {seen}。{_net()}")

    # ---------------- P0-6
    def scene_p6_place_then_cancel(self, sc):
        from freqtrade.persistence import LocalTrade
        out, n = {}, {"k": 0}

        def loop(s, t):
            n["k"] += 1
            if n["k"] in (2, 3):
                out[f"open_at_call{n['k']}"] = sum(1 for tr in LocalTrade.bt_trades_open for o in tr.orders if o.ft_is_open)

        def timeout(s, trade, order, t):
            return n["k"] >= 2

        run([C.as_bar(e) for e in C.events(sc)], {"entry": _entry_first, "entry_price": lambda s, t, r: 90.0,
                                                  "loop": loop, "entry_timeout": timeout, "stake": lambda s, rate, prop: 90.0})
        return ok(out, "Freqtrade の戦略は発注を直接呼べない: 発注は 1 本目の足に enter_long=1 の信号(次の足で出る)と "
                  "custom_entry_price=90、取消は check_entry_timeout が 2 回目の呼び出しの後で True を返す形。"
                  "未決の注文は bot_loop_start で LocalTrade.bt_trades_open の開いた注文を数えた。" + _net())

    def scene_p6_cancel_notice(self, sc):
        return not_supported("取消の成立を戦略に知らせる呼び出しが無い(戦略への知らせは order_filled だけ。取消は check_entry_timeout の"
                             "返り値で戦略が頼む側)。" + _net())

    def scene_p6_fill_seen_by_strategy(self, sc):
        from freqtrade.persistence import LocalTrade
        out, n = {}, {"k": 0}

        def loop(s, t):
            n["k"] += 1
            if n["k"] == 3:
                trades = LocalTrade.bt_trades_open + LocalTrade.bt_trades
                out["filled_qty_at_call3"] = float(sum(o.safe_filled for tr in trades for o in tr.orders))

        run([C.as_bar(e) for e in C.events(sc)], {"entry": _entry_first, "loop": loop, "stake": lambda s, rate, prop: rate * 1.0})
        return ok(out, "1 本目の足に enter_long=1(数量 1 = stake を価格ちょうど)。3 回目の bot_loop_start で "
                  "LocalTrade の注文の safe_filled を足した(発注は次の足)。" + _net())

    # ---------------- P0-7
    def scene_p7_fill_model_swap(self, sc):
        return not_supported("約定の模型を差し込む口が無い(Backtesting の中の _get_order_filled と価格の決め方が固定。"
                             "custom_entry_price は注文の価格を決めるだけ)。試したこと: " + _kw("fill_model") + "。" + _net())

    def scene_p7_latency_model_swap(self, sc):
        return not_supported("発注の遅延の模型を渡す口が無い。試したこと: " + _kw("latency_model") + "。" + _net())

    def _fee_run(self, sc, fee):
        bt, res = run([C.as_bar(e) for e in C.events(sc)], {"entry": _entry_first, "stake": lambda s, rate, prop: rate * 1.0},
                      wallet=100_000.0, fee=fee)
        r = res["results"]
        return r

    def scene_p7_cost_model_swap(self, sc):
        r = self._fee_run(sc, 0.005)
        return not_supported("費用は設定の fee(約定代金に掛ける率)だけで、約定 1 件に決まった額を返す模型を差し込む口が無い。"
                             "試したこと: " + _kw("fee_model") + f"。率 0.005 で走らせた取引の表の手数料の列 "
                             f"{r[[c for c in r.columns if 'fee' in c]].to_dict('records') if len(r) else []}。{_net()}")

    def scene_p7_cost_per_unit(self, sc):
        r = self._fee_run(sc, 0.00375)
        return not_supported("費用は設定の fee(約定代金に掛ける率)だけで、数量 1 単位あたりの模型を差し込む口が無い。"
                             "試したこと: " + _kw("fee_model") + f"。率 0.00375 で走らせた取引の表の手数料の列 "
                             f"{r[[c for c in r.columns if 'fee' in c]].to_dict('records') if len(r) else []}(率は約定代金に掛かる)。{_net()}")

    def scene_p7_account_swap(self, sc):
        return not_supported("口座(Wallets)は Backtesting の中で作られ、差し替える口が無い。試したこと: " + _kw("wallets") + "。" + _net())


def _entry_first(strategy, df, md):
    """populate_entry_trend: an entry signal on the first candle only."""
    df.loc[df.index[0], "enter_long"] = 1
    return df


def _kw(kw: str) -> str:
    try:
        Backtesting(_config(1.0, 0.0), **{kw: object()})
    except TypeError as exc:
        return f"Backtesting(config, {kw}=...) -> TypeError: {str(exc)[:120]}"
    except Exception as exc:  # noqa: BLE001
        return f"Backtesting(config, {kw}=...) -> {type(exc).__name__}: {str(exc)[:120]}"
    return f"Backtesting(config, {kw}=...) は受け付けられた"

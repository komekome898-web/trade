"""Survey candidate 10 `fast-trade` (PyPI `fast-trade` 2.1.0), run in its own venv.

fast-trade's strategy is a rule table (`enter` / `exit` conditions over
columns and technical-indicator datapoints) that `run_backtest(backtest,
df=)` evaluates over the whole OHLCV DataFrame; no strategy code is called
per event. Each scene is answered by a real call into `run_backtest` or
`validate_backtest`.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

import pandas as pd  # noqa: E402

from _vector_base import VectorBase  # noqa: E402
from protocol import not_supported, ok  # noqa: E402
import common as C  # noqa: E402

import fast_trade as ft  # noqa: E402


def _df(bars):
    rows = [C.as_bar(b) for b in bars]
    df = pd.DataFrame({k: [float(b[k]) for b in rows] for k in ("open", "high", "low", "close", "volume")},
                      index=pd.to_datetime([b["ts_ns"] for b in rows], unit="ns"))
    df.index.name = "date"
    return df


def _bt(enter, exit_=None, **kw):
    out = {"start": "2023-11-15", "stop": "2023-12-31", "freq": "1D", "enter": enter, "exit": exit_ or [["close", "<", 0]],
           "any_enter": [], "any_exit": [], "datapoints": [], "base_balance": 100000, "comission": 0.0,
           "lot_size_perc": 1.0, "max_lot_size": 0, "exit_on_end": False, "trailing_stop_loss": 0}
    out.update(kw)
    return out


def _run(bt, bars):
    try:
        r = ft.run_backtest(bt, df=_df(bars))
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {str(exc)[:200]}"
    return r, "ok"


class FastTradeAdapter(VectorBase):
    name = "opp_fast_trade"
    what = ("fast-trade の戦略は enter/exit の条件の表で、run_backtest が DataFrame 全体に対して評価する。事象ごとに戦略の"
            "コードを呼ぶ口、事象の型、注文・取消・通知・時計・差し込み口が無い")

    def attempt(self, scene_id: str) -> str:
        r, msg = _run(_bt([["close", ">", 0]], callback=lambda row: None),
                      [{"kind": "bar", "ts_ns": 1_700_092_800_000_000_000 + i * 86_400 * 10**9, "open": 100.0, "high": 100.0,
                        "low": 100.0, "close": 100.0, "volume": 1.0} for i in range(3)])
        keys = sorted(r.keys()) if isinstance(r, dict) else None
        return (f"run_backtest(backtest に callback=<関数> を足したもの, df=<足 3 本>) -> {msg}"
                f"(返り値の鍵 {keys}。callback は呼ばれない。rules の値は列名・数値・比較だけ)")

    def _iso(self, sc):
        return ok(int(pd.Timestamp(sc.input["iso"]).tz_convert("UTC").value), "fast-trade の日時は DataFrame の DatetimeIndex(pandas)")

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    def scene_p4_future_read_attempt(self, sc):
        bars = C.events(sc)
        r, msg = _run(_bt([["close", "=", 104.0, -1]]), bars)
        r2, msg2 = _run(_bt([["close", ">", 0]], datapoints=[{"name": "fut", "transformer": "shift", "args": [-1]}]), bars)
        return not_supported("時刻ごとに戦略のコードが呼ばれないので、T0 + 4 日の呼び出しの中で先を読む試しができない。"
                             f"表の中で先を参照できるかを試した: 条件の lookback に -1 -> {msg} / datapoints に shift(-1) -> {msg2}")

    def scene_p7_cost_zero(self, sc):
        bars = [C.as_bar(e) for e in C.events(sc)]
        r, msg = _run(_bt([["close", ">", 0]], comission=0.0), bars)
        if r is None:
            return not_supported(f"comission=0.0 で走らせた -> {msg}")
        tl = r.get("trade_df") if isinstance(r, dict) else None
        return not_supported("comission は率の設定で、約定 1 件・数量 1 の成行を戦略が出す口が無い(lot_size_perc で残高の割合を買う)。"
                             f"comission=0.0 で走らせた -> {msg}、返り値の鍵 {sorted(r.keys())}")

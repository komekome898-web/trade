"""Survey candidate 73 `vectorbt` (PyPI vectorbt 1.1.0, venv item_1/vectorbt) for the item 4 battery.

Public API used: `vbt.Portfolio.from_signals(close, entries, exits, short_entries, short_exits, price=open,
open=, high=, low=, size=, size_type="value", fees=, slippage=, direction="both", upon_opposite_entry="close",
sl_stop=, tp_stop=, stop_entry_price="fillprice", stop_exit_price="stopmarket", init_cash=, freq=)`,
`Portfolio.trades.records`, `Portfolio.value()`.

Scene -> tool (vectorbt's own idiom for "act at the next open"):
- the decision of bar i is put on bar i+1 of the signal arrays and executed at `price=open` (a signal on the
  last bar has no next bar and is dropped);
- BUY -> long entry + short exit, SELL -> long exit + short entry (short entry only when allow_short),
  CLOSE -> long exit + short exit; an opposite entry only closes (upon_opposite_entry="close");
  entry_mask / entry_sides remove entries at the decision bar (exits are never removed);
- size = order_notional as a value order (size_type="value"); fee -> `fees=pct/100` (per side);
  spread / 2 + slippage -> `slippage=`;
- stop_loss_pct -> `sl_stop`, take_profit_pct / maker_tp_pct -> `tp_stop`, both relative to the fill price
  (stop_entry_price="fillprice"); a triggered stop exits as a market order with slippage
  (stop_exit_price="stopmarket", the tool uses ONE exit-price mode for sl and tp; portfolio/nb.py 1616-1631 行).
Not expressible: execution "maker" (from_signals has no limit order: the portfolio/base.py from_signals
arguments 2048-2110 行 have no limit price / order type), max_hold_bars and stop_mode "wick_invalidation"
(no built-in time stop or close-based level: the from_signals arguments have sl_stop / sl_trail / tp_stop only;
a numba `signal_func_nb` could carry such logic and this adapter does not write one), swap_daily_pct (no carry
argument), different maker / taker fees on a run with both kinds (one `fees`), the 12 metrics, op metrics /
split / pipeline, reference, models.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from _i4_base import Base, NotExpressible, Refused, adj, bars_frame, fee_kinds, want  # noqa: E402
from i4_protocol import signal_map  # noqa: E402

import vectorbt as vbt  # noqa: E402


class VectorbtAdapter(Base):
    name = "opp_vectorbt"
    TOOL = "vectorbt 1.1.0"
    SUPPORTS = {"allow_short", "taker_fee_pct", "maker_fee_pct", "slippage_pct", "spread_pct", "stop_loss_pct",
                "take_profit_pct", "exit_execution", "maker_tp_pct", "entry_mask", "entry_sides"}
    MISSING = {
        "execution": "from_signals に指値(値を決めて待つ注文)の口を探したが無い(portfolio/base.py 2048-2110 行の引数に limit・order_type 無し)",
        "max_hold_bars": "組み込みの時間の止めを探したが無い(from_signals の止めの引数は sl_stop・sl_trail・tp_stop だけ)。numba の "
                         "signal_func_nb で書く道はあるが、この adapter は書いていない",
        "stop_mode": "終値が前の足の安値・高値の水準を抜けたら次の始値で出る止めを探したが無い(sl_stop は約定値からの率だけ)。"
                     "signal_func_nb で書く道はあるが、この adapter は書いていない",
        "stop_window_bars": "stop_mode と同じ",
        "swap_daily_pct": "持ち越しの口を探したが無い(from_signals の引数に carry・funding・interest 無し)",
    }
    METRICS = ("12 の指標を 1 つずつ出す口を探したが無い(Portfolio.stats は Total Return・Sharpe・Max Drawdown・Win Rate・Profit "
               "Factor・Expectancy・Avg Winning/Losing Trade [%] で、平均勝ち・負けの円・RR・手数料の合計は無い。外から与えた損益の列を"
               "受ける関数も無い)")
    SPLIT = ("行の割合で 3 つに分ける口を探したが無い(range_split・rolling_split・expanding_split は位置か長さを取る。"
             "割合から境を出すのは adapter の計算になる)")
    PIPELINE = ("入力はメモリ上の配列(close・open・high・low)で、ファイルを宣言で読む口・気配(buy は ask・sell は bid)・板の入力・"
                "実行記録・目的つきの書き出し・ダッシュボードを探したが無い")

    def extra_gate(self, inp):
        out = []
        cfg, c = inp["config"], inp["config"]["costs"]
        if len(fee_kinds(cfg)) == 2 and c["maker_fee_pct"] != c["taker_fee_pct"]:
            out.append("maker と taker で違う手数料: fees は 1 つの配列(注文の種類で分ける口が無い)")
        if "metrics" in (inp.get("want") or []):
            out.append(self.METRICS)
        return out

    def bars(self, inp):
        cfg, c = inp["config"], inp["config"]["costs"]
        df = bars_frame(inp, pd)
        n = len(df)
        sig = signal_map(inp)
        mask = cfg["entry_mask"]
        long_ok = cfg["entry_sides"] in ("both", "long")
        short_ok = cfg["entry_sides"] in ("both", "short") and cfg["allow_short"]
        le, lx, se, sx = (np.zeros(n, dtype=bool) for _ in range(4))
        for i, s in sig.items():
            j = i + 1  # executed on the next bar's open
            if j >= n:
                continue
            m = mask is None or bool(mask[i])
            if s == "BUY":
                le[j] = long_ok and m
                sx[j] = True
            elif s == "SELL":
                lx[j] = True
                se[j] = short_ok and m
            else:
                lx[j] = sx[j] = True
        fee = c["taker_fee_pct"] if "taker" in fee_kinds(cfg) else c["maker_fee_pct"]
        kw = {}
        if cfg["stop_loss_pct"]:
            kw["sl_stop"] = cfg["stop_loss_pct"] / 100
        tp = cfg["take_profit_pct"] or (cfg["maker_tp_pct"] if cfg["exit_execution"] == "maker_tp" else None)
        if tp:
            kw["tp_stop"] = tp / 100
        try:
            pf = vbt.Portfolio.from_signals(
                df["close"], entries=le, exits=lx, short_entries=se, short_exits=sx, price=df["open"],
                open=df["open"], high=df["high"], low=df["low"], size=float(cfg["order_notional"]), size_type="value",
                fees=float(fee) / 100, slippage=adj(c), direction="both", upon_opposite_entry="close",
                accumulate=False, stop_entry_price="fillprice", stop_exit_price="stopmarket",
                init_cash=float(cfg["initial_equity"]), freq=f"{int(inp['bar_seconds'])}s", **kw)
            tr = pf.trades.records_arr
            val = pf.value()
        except NotExpressible:
            raise
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {exc}") from exc
        fills, pnls = [], []
        for r in tr:
            d = "LONG" if int(r["direction"]) == 0 else "SHORT"
            fills.append({"bar": int(r["entry_idx"]), "side": f"OPEN_{d}", "price": float(r["entry_price"]),
                          "size": float(r["size"])})
            if int(r["status"]) == 1:
                fills.append({"bar": int(r["exit_idx"]), "side": f"CLOSE_{d}", "price": float(r["exit_price"]),
                              "size": float(r["size"])})
                pnls.append((int(r["exit_idx"]), float(r["pnl"])))
        fills.sort(key=lambda f: (f["bar"], 0 if f["side"].startswith("CLOSE") else 1))
        return want(inp, {"fills": fills, "pnls": [p for _, p in sorted(pnls, key=lambda x: x[0])],
                          "equity": [float(x) for x in np.asarray(val).ravel()]})


TARGET = VectorbtAdapter()

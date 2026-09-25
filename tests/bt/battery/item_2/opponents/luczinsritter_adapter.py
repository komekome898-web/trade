"""Survey candidate 16 `Luczinsritter/event_driven_backtesting_engine` (git clone, commit 2092992, venv
item_0/luczinsritter with a .pth to the clone; install record: item 0 survey_results/attempts/16.log) for the
item 2 battery.

What the tool is (backtest_engine.py): `EventBased(FinancialData)` holds cash and ONE position; the order calls are
`enter_long / enter_short(ind_nbr, units=...)` and `close_position(ind_nbr)`, all executed at the NEXT row's open
(`get_execution_price`, "to eliminate look-ahead bias"); `close_position` books `pnl` into `trade_performance`.
FinancialData reads the OHLCV table through `get_data` (yfinance by default) and `add_log_returns` drops the first
row.  No limit / stop order, cancel, fee, latency, notice, margin.

Scene -> tool: `get_data` is overridden in the subclass to hand i2_common.bar_rows as the OHLCV table (the tool's own
extension point; no network); the loop is the tool's example loop (`for i in range(len(self.data) - 1)`) and issues
the actions scheduled for row i (i2_common.issue_schedule over the rows left after the tool's own dropna).  A buy /
sell market order when flat -> enter_long / enter_short(units = qty); the opposite order of the same size while
holding -> close_position; anything else (a partial close, adding to a position) has no call and is refused.
"""
from __future__ import annotations

import datetime as D
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import pandas as pd  # noqa: E402

import i2_common as C  # noqa: E402
from i2_protocol import NotExpressible, Refused  # noqa: E402

import backtest_engine as BE  # noqa: E402  (the tool, via the venv's .pth)

TOOL = "Luczinsritter/event_driven_backtesting_engine(2092992)"
EPOCH = pd.Timestamp("1970-01-01")


class Adapter:
    name = "opp_luczinsritter"

    def run(self, inp):
        C.gate(inp, tool=TOOL, orders=("market",), events=("book", "trade", "bar"), fill_models=C.bar_fill_models,
               costs=(), account=("cash",))
        rows, _src = C.bar_rows(inp)
        if not rows:
            raise NotExpressible(f"{TOOL}: 足にする約定も足も無い")
        df = pd.DataFrame({"Open": [b["o"] for b in rows], "High": [b["h"] for b in rows], "Low": [b["l"] for b in rows],
                           "Close": [b["c"] for b in rows], "Volume": [b["v"] for b in rows]},
                          index=pd.DatetimeIndex([EPOCH + pd.Timedelta(int(b["t"]), "ns") for b in rows]))

        class Scene(BE.EventBased):
            def get_data(self, ticker, end_date, interval):
                return df.copy()

        import contextlib
        import io
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                s = Scene("X", D.date(2026, 1, 1), 1, "1d", float(inp["account"]["cash"]), True)
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {exc}")
        kept = [b for b in rows if (EPOCH + pd.Timedelta(int(b["t"]), "ns")) in set(s.data.index)]
        sched = C.issue_schedule(kept, inp["actions"])
        rec = {"orders": {}, "fills": [], "account": {}}
        pos_ref = None
        realized = 0.0
        try:
            with contextlib.redirect_stdout(buf):
                for i in range(len(s.data) - 1):
                    for a in sched.get(i, []):
                        side = s.position["side"]
                        want = "long" if a["side"] == "buy" else "short"
                        if side is None:
                            (s.enter_long if want == "long" else s.enter_short)(i, units=float(a["qty"]))
                            if s.position["side"] == want:
                                pos_ref = a["ref"]
                                rec["fills"].append({"ref": a["ref"], "t": int((s.position["entry_date"] - EPOCH).value),
                                                     "px": float(s.position["entry_price"]), "qty": float(a["qty"]), "liq": None})
                                rec["orders"][a["ref"]] = {"status": "filled"}
                            else:
                                rec["orders"][a["ref"]] = {"status": "rejected", "error": "enter_* printed not enough capital"}
                        elif side != want and abs(float(s.position["units"]) - float(a["qty"])) < 1e-12:
                            s.close_position(i)
                            realized += float(s.trade_performance[s.closing_date]["PnL"])
                            rec["fills"].append({"ref": a["ref"], "t": int((s.closing_date - EPOCH).value),
                                                 "px": float(s.closing_price), "qty": float(a["qty"]), "liq": None})
                            rec["orders"][a["ref"]] = {"status": "filled"}
                            pos_ref = None
                        else:
                            raise NotExpressible(f"{TOOL}: 建玉は 1 つで、一部を減らす・買い増す口が無い(enter_* / close_position だけ)")
        except NotExpressible:
            raise
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {exc}")
        for a in C.places(inp):
            rec["orders"].setdefault(a["ref"], {"status": "open"})  # never reached a row of the tool's loop
        sgn = {"long": 1.0, "short": -1.0, None: 0.0}[s.position["side"]]
        rec["account"] = {"position": sgn * float(s.position["units"] or 0.0), "realized": realized}
        del pos_ref
        return rec


TARGET = Adapter()

"""Survey candidate 5 (the catalogue's name "Lean CLI"; the survey report's line for number 5, SCAN 6849 行, and its minimal
runs, SCAN 1795・1846 行, are the PyPI package `bt`) -- `bt` 1.2.3 (github.com/pmorissette/bt), venv item_2/bt, install
record venvs/item_2/logs/i2_r1_scenekeeper_install_5.log -- for the item 2 battery.

The tool's own parts used: `bt.Strategy(name, [algos])` with one user Algo (the tool's plug: an object called with the
strategy on each date) that calls the strategy's own `transact(q, child="X")` (a quantity trade at the date's price),
`bt.Backtest(strategy, data, initial_capital, commissions=f(q, p), integer_positions=False)`, `bt.run`, and the result's
`get_transactions()` (each trade's price and quantity) and the strategy's `outlays` / positions.
Bars: i2_common.bar_rows (one bar per print unless the scene has bars) as the data's rows, indexed by the bar's start; an
order is transacted on the first row that starts after the action's time.  bt's trades are quantities at the date's
price: limit / stop / IOC / FOK / post-only / cancel / amend have no call and are refused.  One commission function
`f(q, p) = rate x |q| x p` (i2_common.single_fee_rate).
"""
from __future__ import annotations

import datetime as D
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import pandas as pd  # noqa: E402

import i2_common as C  # noqa: E402
from i2_protocol import NotExpressible, Refused  # noqa: E402

import bt  # noqa: E402  (the tool)

TOOL = "bt 1.2.3"


def _dt(ns):
    return pd.Timestamp(int(ns), unit="ns")


class Adapter:
    name = "opp_bt"

    def run(self, inp):
        C.gate(inp, tool=TOOL, orders=("market",), events=("book", "trade", "bar"),
               fill_models=lambda fm: C.bar_fill_models(fm), costs=("maker_rate", "taker_rate"), account=("cash",))
        bars, _src = C.bar_rows(inp)
        if not bars:
            raise NotExpressible(f"{TOOL}: 足にする約定も足も無い(bt の入力は価格の表)")
        idx = [b["t"] - b["span_ns"] for b in bars]
        if len(set(idx)) != len(idx):
            raise NotExpressible(f"{TOOL}: 同じ時刻の行を 2 つ持つ口が無い(価格の表の索引は時刻 1 つに 1 行)")
        rate = float(C.single_fee_rate(inp, TOOL))
        plan = {}
        for a in sorted(C.places(inp), key=lambda x: x["t"]):
            k = next((i for i, t0 in enumerate(idx) if t0 > a["t"]), None)
            if k is None:
                continue
            plan.setdefault(_dt(idx[k]), []).append(a)
        if any(len(v) > 1 for v in plan.values()):
            raise NotExpressible(f"{TOOL}: 同じ行の 2 つの取引を分けて読む口が無い(get_transactions は日時と銘柄ごとに 1 行にまとめる)")

        class Act(bt.Algo):
            def __call__(self, target):
                for a in plan.get(target.now, []):
                    target.transact(a["qty"] if a["side"] == "buy" else -a["qty"], child="X")
                return True

        data = pd.DataFrame({"X": [float(b["o"]) for b in bars]}, index=pd.DatetimeIndex([_dt(t) for t in idx]))
        try:
            s = bt.Strategy("s", [Act()])
            test = bt.Backtest(s, data, initial_capital=float(inp["account"]["cash"]),
                               commissions=lambda q, p: rate * abs(q) * p, integer_positions=False, progress_bar=False)
            res = bt.run(test)
            tx = res.get_transactions()
        except NotExpressible:
            raise
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {str(exc)[:200]}")
        rec = {"orders": {}, "fills": []}
        rows = {} if tx is None or len(tx) == 0 else {ts: r for (ts, _sec), r in tx.iterrows()}
        for ts, acts in plan.items():
            r = rows.get(ts)
            for a in acts:
                if r is not None:
                    q = abs(float(r["quantity"]))
                    rec["fills"].append({"ref": a["ref"], "t": int(ts.value), "px": float(r["price"]), "qty": q,
                                         "fee": rate * q * float(r["price"]), "liq": None})
        for a in C.places(inp):
            got = sum(f["qty"] for f in rec["fills"] if f["ref"] == a["ref"])
            rec["orders"][a["ref"]] = {"status": C.status_from(got, a["qty"], active=False, canceled=got < a["qty"])}
        return rec


TARGET = Adapter()

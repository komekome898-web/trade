"""Cross-check of the bar reference (bot.bt.reference.bar_sim) against an
external tool, backtesting.py 0.6.6, on the same SYNTHETIC scenes.

Not collected by pytest (file name does not start with test_). Run it with
the isolated venv's interpreter, e.g.

    PYTHONPATH=src <venv>/bin/python tests/bt/item_4/reference/ext_backtesting_compare.py \
        --out tests/bt/item_4/reference/ext_results/backtesting_py_0.6.6.json

The recorded output is re-checked without the external tool by
test_i4ref_ext_recorded.py.

Mapping of backtesting.py's rules onto the reference's selectable modes (read
from backtesting.py 0.6.6 backtesting.py:_process_orders, lines 887-1046 of
the installed wheel):
  * market order placed in next() of bar i fills at the open of bar i+1;
  * a stop (the SL) triggers on touch (low <= stop for a long's SL) and fills
    at min(open, stop) for a sell -> stop_trigger="touch",
    stop_fill="worse_of_level_and_open";
  * a limit (entry or TP) fills on touch -> limit_cross="touch";
  * SL/TP of a market entry are re-processed on the entry bar ->
    exits_from_entry_bar=True (so limit entries here carry no SL/TP, because
    backtesting.py defers those to the next bar);
  * relative commission on both legs -> maker_rate = taker_rate, tp_fee taker;
  * next() is first called for bar 1, so no signal is placed on bar 0.
Known rule difference (not mapped, reported per scene): backtesting.py fills a
limit (entry or TP) at the open when the bar opens beyond the limit in the
favourable direction; the reference never fills at a better price than the
limit (requirement I4-9).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import warnings

TOL = 1e-6


def gen_scene(rng: random.Random, n: int) -> dict:
    price = 1000
    bars = []
    for _ in range(n):
        o = max(10, price + rng.randint(-8, 8))
        c = max(10, o + rng.randint(-10, 10))
        h = max(o, c) + rng.randint(0, 8)
        l = max(1, min(o, c) - rng.randint(0, 8))
        bars.append([o, h, l, c])
        price = c
    signals = [None] * n
    for i in range(1, n):
        if rng.random() < 0.3:
            side = rng.choice(["long", "short"])
            if rng.random() < 0.25:
                ref = bars[i][3]
                off = rng.randint(0, 6)
                lim = ref - off if side == "long" else ref + off
                signals[i] = {"side": side, "limit": lim, "sl_dist": None, "tp_dist": None}
            else:
                sl = rng.choice([None, rng.randint(2, 15)])
                tp = rng.choice([None, rng.randint(2, 15)])
                if i + 1 < n:
                    # backtesting.py refuses an order unless SL < last close < TP
                    # (long); widen the distance just enough (tool constraint).
                    gap = abs(bars[i + 1][0] - bars[i][3]) + 1
                    sl = None if sl is None else max(sl, gap)
                    tp = None if tp is None else max(tp, gap)
                signals[i] = {"side": side, "limit": None, "sl_dist": sl, "tp_dist": tp}
    return {"bars": bars, "signals": signals,
            "max_hold_bars": rng.choice([None, rng.randint(1, 6)]),
            "limit_valid_bars": rng.randint(1, 3),
            "commission": rng.choice([0.0, 0.001, 0.0005])}


MAPPED_MODES = {"limit_cross": "touch", "stop_trigger": "touch",
                "stop_fill": "worse_of_level_and_open", "exits_from_entry_bar": True}
# Each variant flips one mapped mode; on scenes without a favourable gap the
# match count must drop, which shows the comparison can see that rule.
SENSITIVITY_VARIANTS = {"limit_cross": "strict", "stop_trigger": "strict",
                        "stop_fill": "level", "exits_from_entry_bar": False}


def run_reference(sc: dict, **override):
    from ext_bar_modes import Signal, make_bar, run_bars
    bars = [make_bar(i * 3_600_000_000_000, *b) for i, b in enumerate(sc["bars"])]
    sigs = [None if s is None else Signal(**s) for s in sc["signals"]]
    rate = str(sc["commission"])
    modes = dict(MAPPED_MODES, **override)
    return run_bars(bars, sigs, qty=1, initial_cash=1_000_000, taker_rate=rate, maker_rate=rate,
                    tp_fee="taker", limit_valid_bars=sc["limit_valid_bars"], mask=None,
                    mask_applies_to="signal_bar", entry_sides="both",
                    max_hold_bars=sc["max_hold_bars"], close_at_end=False, **modes)


def favourable_gaps(sc: dict, ref) -> list:
    """Bars where backtesting.py's open-price improvement can apply."""
    out = []
    bars = sc["bars"]
    trades = list(ref.trades) + ([ref.open_trade] if ref.open_trade else [])
    for t in trades:
        s = 1 if t.side == "long" else -1
        if t.entry_liquidity == "maker":
            o = bars[t.entry_bar][0]
            if (s == 1 and o < t.entry_price) or (s == -1 and o > t.entry_price):
                out.append(["limit_entry", t.entry_bar])
        if t.reason == "take_profit" and t.exit_bar > t.entry_bar:
            o = bars[t.exit_bar][0]
            if (s == 1 and o > t.tp) or (s == -1 and o < t.tp):
                out.append(["take_profit", t.exit_bar])
    return out


def run_external(sc: dict) -> dict:
    import pandas as pd
    from backtesting import Backtest, Strategy

    bars, signals = sc["bars"], sc["signals"]
    n = len(bars)
    df = pd.DataFrame(bars, columns=["Open", "High", "Low", "Close"],
                      index=pd.date_range("2020-01-01", periods=n, freq="h"))
    mh, k = sc["max_hold_bars"], sc["limit_valid_bars"]
    state = {"missed": 0}

    class Harness(Strategy):
        def init(self):
            self._pending = None  # (order, placed_bar)

        def next(self):
            i = len(self.data) - 1
            if self._pending is not None:
                order, placed = self._pending
                if order not in self.orders:
                    self._pending = None
                elif i >= placed + k:
                    order.cancel()
                    state["missed"] += 1
                    self._pending = None
            if self.position and mh is not None:
                tr = self.trades[-1]
                if i == tr.entry_bar + mh - 1:
                    self.position.close()
            sig = signals[i]
            if sig is None or self.position or self._pending is not None or i == n - 1:
                return
            if sig["limit"] is not None:
                fn = self.buy if sig["side"] == "long" else self.sell
                o = fn(size=1, limit=sig["limit"])
                self._pending = (o, i)
                return
            fill = bars[i + 1][0]
            s = 1 if sig["side"] == "long" else -1
            kw = {}
            if sig["sl_dist"] is not None:
                kw["sl"] = fill - s * sig["sl_dist"]
            if sig["tp_dist"] is not None:
                kw["tp"] = fill + s * sig["tp_dist"]
            (self.buy if s == 1 else self.sell)(size=1, **kw)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        st = Backtest(df, Harness, cash=1_000_000, commission=sc["commission"],
                      finalize_trades=False).run()
    trades = [{"entry_bar": int(r.EntryBar), "exit_bar": int(r.ExitBar),
               "entry_price": float(r.EntryPrice), "exit_price": float(r.ExitPrice),
               "pnl": float(r.PnL), "side": "long" if r.Size > 0 else "short"}
              for r in st._trades.itertuples()]
    return {"trades": trades, "missed_fills": state["missed"],
            "equity_final": float(st["Equity Final [$]"])}


def summarise_reference(ref) -> dict:
    return {"trades": [{"entry_bar": t.entry_bar, "exit_bar": t.exit_bar,
                        "entry_price": float(t.entry_price), "exit_price": float(t.exit_price),
                        "pnl": float(t.pnl), "side": t.side} for t in ref.trades],
            "missed_fills": ref.missed_fills,
            "equity_final": float(ref.equity[-1])}


def same(a: dict, b: dict) -> bool:
    if a["missed_fills"] != b["missed_fills"] or len(a["trades"]) != len(b["trades"]):
        return False
    for x, y in zip(a["trades"], b["trades"]):
        if x["side"] != y["side"] or x["entry_bar"] != y["entry_bar"] or x["exit_bar"] != y["exit_bar"]:
            return False
        for f in ("entry_price", "exit_price", "pnl"):
            if abs(x[f] - y[f]) > TOL:
                return False
    return abs(a["equity_final"] - b["equity_final"]) <= TOL


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260926)
    ap.add_argument("--scenes", type=int, default=200)
    ap.add_argument("--bars", type=int, default=40)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    import backtesting
    rng = random.Random(a.seed)
    rows = []
    for idx in range(a.scenes):
        sc = gen_scene(rng, a.bars)
        ref = run_reference(sc)
        gaps = favourable_gaps(sc, ref)
        r, e = summarise_reference(ref), run_external(sc)
        rows.append({"scene": idx, "input": sc, "reference": r, "external": e,
                     "favourable_gaps": gaps, "match": same(r, e)})
    no_gap = [x for x in rows if not x["favourable_gaps"]]
    gap = [x for x in rows if x["favourable_gaps"]]
    # In a gap scene, trades that end before the first favourable-gap bar
    # must still match; the first differing trade must contain that bar.
    explained = 0
    for x in gap:
        first_gap_bar = min(b for _, b in x["favourable_gaps"])
        rt, et = x["reference"]["trades"], x["external"]["trades"]
        before_r = [t for t in rt if t["exit_bar"] < first_gap_bar]
        before_e = [t for t in et if t["exit_bar"] < first_gap_bar]
        ok = len(before_r) == len(before_e) and all(
            same({"trades": [p], "missed_fills": 0, "equity_final": 0},
                 {"trades": [r], "missed_fills": 0, "equity_final": 0})
            for p, r in zip(before_r, before_e))
        explained += ok
    sensitivity = {}
    for k, v in SENSITIVITY_VARIANTS.items():
        m = 0
        for x in no_gap:
            m += same(summarise_reference(run_reference(x["input"], **{k: v})), x["external"])
        sensitivity[f"{k}={v}"] = m
    summary = {
        "tool": "backtesting.py", "tool_version": backtesting.__version__,
        "seed": a.seed, "scenes": a.scenes, "bars_per_scene": a.bars, "tolerance": TOL,
        "scenes_without_favourable_gap": len(no_gap),
        "matched_without_favourable_gap": sum(x["match"] for x in no_gap),
        "scenes_with_favourable_gap": len(gap),
        "matched_with_favourable_gap": sum(x["match"] for x in gap),
        "gap_scenes_matching_before_first_gap": explained,
        "trades_compared": sum(len(x["reference"]["trades"]) for x in rows),
        "mapped_modes": MAPPED_MODES,
        "sensitivity_matches_without_gap": sensitivity,
        "data": "synthetic only (seeded random walk, integer prices)",
    }
    with open(a.out, "w", encoding="utf-8") as fh:
        # the reference side is recomputed by the recorded-output test, so only
        # the inputs and the external tool's numbers are stored
        slim = [{k: v for k, v in x.items() if k != "reference"} for x in rows]
        json.dump({"summary": summary, "rows": slim}, fh, ensure_ascii=False, separators=(",", ":"))
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["matched_without_favourable_gap"] == len(no_gap) else 1


if __name__ == "__main__":
    sys.exit(main())

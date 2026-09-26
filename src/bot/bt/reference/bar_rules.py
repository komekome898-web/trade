"""The item-4 WORKER'S transcription of the STATED bar-model rules -- NOT the
independent reference (item 4, old item 11).

What it is: one plain loop over the bars in exact rational arithmetic
(fractions.Fraction of the written decimal value of every input), written
from the rule text of the item-4 battery (tests/bt/battery/item_4/
DEFINITIONS.md 「足の模型の仕様」 R-T1 .. R-S1 and 「指標の式」 M-1 .. M-12). It
does not import the engine (bot.bt.core, bot.bt.compat).

What it is NOT: the delegation's 「核を見ずに別の作業者が書く」 reference. It was
written by the item-4 worker, who has read the core and the new engine (round
1) -- so an agreement between it and the engine is not an independent check
(critic i4-r1-03: in round 1 it shared the engine's defect i4-r1-01). The
independent reference is bar_sim.py / event_sim.py (the reference role,
SPEC.md sections 0-3); the engine is compared with bar_sim.py in
tests/bt/item_4/test_i4_engine_vs_independent_bar_sim.py. The rules bar_sim
does not have (sizing by notional, closing by a signal, percentage levels,
the carry, the structural stop, spread and slippage) exist only here until
the reference role is run again with the stated rules as its input (a
question to the lead, round_2/ROOTCAUSE.md section 7-1).

    run_rules(bars, bar_seconds, signals, config) -> dict
      bars      [{"open", "high", "low", "close"}, ...]
      signals   {bar index: "BUY" | "SELL" | "CLOSE"}
      config    the 16 option keys of the battery (i4_protocol.CONFIG_KEYS)
      -> {"fills": [{bar, side, price, size}], "pnls", "equity", "metrics",
          "missed_fills"}  (floats converted from the exact values at the end)

The order inside one bar j is the time order (R-T1: a bar's open comes
before the rest of its range): AT THE OPEN, the exits decided by older
information -- the structural stop on bar j-1's close (R-W3) and the time
exit (R-H1: at the open of bar b + N, before that bar's range -- R-O1, the
finishing delegation's reading of R-H3, i4-r2-02) -- drop the pending signal
(R-W3 / R-H2); else the pending taker signal acts at the open (R-T1). THEN, if the position lives on through the open, bar j's RANGE: the
stop (R-P3), the take-profit (R-P4), the maker take-profit (R-X1), then a
pending maker limit (R-M1). Where the rule text is silent: an exit in bar j's
range drops a maker limit pending for bar j (both are inside the range; the
text does not order them -- a question to the lead); a take-profit
percentage of 0 or None means no take-profit. Maker signals (the lead's two
values, finishing delegation i4-r2-08): an entry signal whose bar's mask is
False places no limit and counts no missed fill; a signal the same way as the
pending limit leaves the old limit (price and lifetime) in place.
"""
from __future__ import annotations

import math
from fractions import Fraction
from typing import Optional

SIDE = {"long": 1, "short": -1}


def F(x) -> Fraction:
    """The written decimal value of a number (a float's shortest repr)."""
    if isinstance(x, bool):
        raise TypeError("a bool is not a number here")
    if isinstance(x, int):
        return Fraction(x)
    return Fraction(repr(float(x)))


def _taker(ref: Fraction, buy: bool, c: dict) -> Fraction:
    """R-C1: ref x (1 +- (spread/2 + slippage)/100)."""
    k = (F(c["spread_pct"]) / 2 + F(c["slippage_pct"])) / 100
    return ref * (1 + k) if buy else ref * (1 - k)


def run_rules(bars, bar_seconds, signals: dict, config: dict) -> dict:
    cfg = config
    c = cfg["costs"]
    if cfg["exit_execution"] == "maker_tp" and not (cfg["maker_tp_pct"] is not None and F(cfg["maker_tp_pct"]) > 0):
        raise ValueError("R-X3: maker_tp needs maker_tp_pct > 0")
    if cfg["stop_mode"] == "wick_invalidation" and cfg["stop_loss_pct"] is not None:
        raise ValueError("R-W4: the structural stop and the % stop are alternatives, never both")
    O = [F(b["open"]) for b in bars]
    H = [F(b["high"]) for b in bars]
    L = [F(b["low"]) for b in bars]
    C = [F(b["close"]) for b in bars]
    n = len(bars)
    taker_rate, maker_rate = F(c["taker_fee_pct"]) / 100, F(c["maker_fee_pct"]) / 100
    carry_rate = F(cfg["swap_daily_pct"]) / 100 * F(bar_seconds) / 86400
    notional, equity0 = F(cfg["order_notional"]), F(cfg["initial_equity"])
    mask = cfg["entry_mask"]
    sides = cfg["entry_sides"]
    N = cfg["max_hold_bars"]

    fills, pnls, equity = [], [], []
    realized = Fraction(0)
    fees_total = Fraction(0)
    missed = 0
    pos: Optional[dict] = None  # {"s", "q", "E", "b", "fee", "carry", "wick"}
    pend_taker: Optional[tuple] = None  # (side "BUY"/"SELL", decision bar)
    pend_limit: Optional[tuple] = None  # (side, limit price, placed bar)

    def may_open(side: str, decision_bar: int) -> bool:  # R-E1 .. R-E3, R-T4
        if side == "SELL" and not cfg["allow_short"]:
            return False
        if sides == "long" and side == "SELL" or sides == "short" and side == "BUY":
            return False
        if mask is not None and not mask[decision_bar]:  # R-E2: the mask of the signal's bar
            return False
        return True

    def open_(j: int, side: str, price: Fraction, rate: Fraction) -> None:
        nonlocal pos, fees_total
        q = notional / price  # R-A1
        fee = q * price * rate  # R-A2
        fees_total += fee
        s = 1 if side == "BUY" else -1
        wick = None
        if cfg["stop_mode"] == "wick_invalidation":  # R-W1: bars j-N .. j-1, frozen now
            w = cfg["stop_window_bars"]
            window = range(max(0, j - w), j)
            if len(window):
                wick = min(L[k] for k in window) if s > 0 else max(H[k] for k in window)
        pos = {"s": s, "q": q, "E": price, "b": j, "fee": fee, "carry": Fraction(0), "wick": wick}
        fills.append({"bar": j, "side": "OPEN_LONG" if s > 0 else "OPEN_SHORT", "price": price, "size": q})

    def close_(j: int, price: Fraction, rate: Fraction) -> None:
        nonlocal pos, realized, fees_total
        fee = pos["q"] * price * rate
        fees_total += fee
        pnl = (price - pos["E"]) * pos["q"] * pos["s"] - fee - pos["fee"] - pos["carry"]  # R-A3
        realized += pnl
        pnls.append(pnl)
        fills.append({"bar": j, "side": "CLOSE_LONG" if pos["s"] > 0 else "CLOSE_SHORT", "price": price, "size": pos["q"]})
        pos = None

    def act(j: int, side: str, price_of, rate: Fraction, decision_bar: int) -> None:
        """R-T3: a BUY closes a short or opens a long; a SELL closes a long or opens a short."""
        want = 1 if side == "BUY" else -1
        if pos is not None:
            if pos["s"] != want:
                close_(j, price_of(want > 0), rate)
            return  # one position; a signal the same way as the position does nothing
        if may_open(side, decision_bar):
            open_(j, side, price_of(want > 0), rate)

    for j in range(n):
        exited = False
        if pos is not None and j > pos["b"] and carry_rate != 0:  # R-S1
            carry = pos["q"] * C[j - 1] * carry_rate
            pos["carry"] += carry
            fees_total += carry
        # --- AT THE OPEN of bar j
        # R-W3: a close beyond the frozen level -> the next bar's open, taker
        if pos is not None and pos["wick"] is not None and j > pos["b"]:
            breach = C[j - 1] < pos["wick"] if pos["s"] > 0 else C[j - 1] > pos["wick"]
            if breach:
                close_(j, _taker(O[j], pos is not None and pos["s"] < 0, c), taker_rate)
                exited = True
        time_due = pos is not None and N is not None and j - pos["b"] >= N
        if not exited and time_due:  # R-H1 at the open (R-O1: before anything of bar j's range)
            close_(j, _taker(O[j], pos["s"] < 0, c), taker_rate)
            exited = True
        if exited:  # R-H2 / R-W3: the exit at the open drops the pending signal
            pend_taker = pend_limit = None
        if cfg["execution"] == "taker" and pend_taker is not None:  # R-T1: the signal acts at the open
            side, db = pend_taker
            act(j, side, lambda buy, o=O[j]: _taker(o, buy, c), taker_rate, db)
            pend_taker = None
        # --- bar j's RANGE, for a position that lives on through the open (R-P2 / R-X2: never on the entry bar)
        if pos is not None and j > pos["b"]:
            s = pos["s"]
            sl = tp = mtp = None
            if cfg["stop_loss_pct"]:
                sl = pos["E"] * (1 - s * F(cfg["stop_loss_pct"]) / 100)  # R-P1
            if cfg["take_profit_pct"]:
                tp = pos["E"] * (1 + s * F(cfg["take_profit_pct"]) / 100)
            if cfg["exit_execution"] == "maker_tp":
                mtp = pos["E"] * (1 + s * F(cfg["maker_tp_pct"]) / 100)  # R-X1
            if sl is not None and (L[j] <= sl if s > 0 else H[j] >= sl):  # R-P3: the stop first
                base = min(O[j], sl) if s > 0 else max(O[j], sl)
                close_(j, _taker(base, s < 0, c), taker_rate)
                exited = True
            elif tp is not None and (H[j] > tp if s > 0 else L[j] < tp):  # R-P4
                close_(j, tp, maker_rate)
                exited = True
            elif mtp is not None and (H[j] > mtp if s > 0 else L[j] < mtp):  # R-X1
                close_(j, mtp, maker_rate)
                exited = True
        if exited:  # an exit in the range drops a maker limit pending for this bar (the text is silent: see above)
            pend_limit = None
        if cfg["execution"] == "maker" and pend_limit is not None and j > pend_limit[2]:  # R-M1 .. R-M2
            side, lim, p = pend_limit
            through = L[j] < lim if side == "BUY" else H[j] > lim
            if through:
                act(j, side, lambda buy, x=lim: x, maker_rate, p)
                pend_limit = None
            elif j - p >= cfg["maker_timeout_bars"]:
                missed += 1
                pend_limit = None
        # R-A4: equity at bar j's close
        e = equity0 + realized
        if pos is not None:
            e += (C[j] - pos["E"]) * pos["q"] * pos["s"] - pos["fee"] - pos["carry"]
        equity.append(e)
        # the decision at bar j's close
        sig = signals.get(j)
        if sig is None or j == n - 1 and cfg["execution"] == "taker":  # R-T2: no next bar
            continue
        if sig == "CLOSE":  # R-T3 / R-M4: closes, never opens
            if pos is None:
                continue
            sig = "SELL" if pos["s"] > 0 else "BUY"
        if cfg["execution"] == "taker":
            pend_taker = (sig, j)
        else:
            want = 1 if sig == "BUY" else -1
            if pos is not None and pos["s"] == want:
                continue  # nothing to do the same way as the position
            if pos is None and sig == "SELL" and not cfg["allow_short"]:
                continue  # R-T4
            if pos is None and not may_open(sig, j):
                continue  # R-E4 / R-E5 (i4-r2-08): a stopped entry signal places no limit, counts no missed fill
            if pend_limit is not None and pend_limit[0] == sig:
                continue  # the lead's value (i4-r2-08): the old limit stays
            if pend_limit is not None and pend_limit[0] != sig:  # R-M3
                missed += 1
            pend_limit = (sig, C[j], j)  # R-M1: at the signal bar's close

    return {"fills": [{"bar": f["bar"], "side": f["side"], "price": float(f["price"]), "size": float(f["size"])}
                      for f in fills],
            "pnls": [float(p) for p in pnls], "equity": [float(e) for e in equity],
            "metrics": metrics(pnls, equity, fees_total, Fraction(365 * 86400) / F(bar_seconds)),
            "missed_fills": missed}


def metrics(pnls, equity, fees, periods) -> dict:
    """M-1 .. M-12 on exact values; the Sharpe ratio's square roots in floats."""
    n = len(pnls)
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gp, gl = sum(wins, Fraction(0)), -sum(losses, Fraction(0))
    pf = float(gp / gl) if gl > 0 else (math.inf if gp > 0 else 0.0)
    r = [(equity[k] - equity[k - 1]) / equity[k - 1] for k in range(1, len(equity))]
    sharpe = 0.0
    if len(r) > 1:
        mean = sum(r, Fraction(0)) / len(r)
        var = sum(((x - mean) ** 2 for x in r), Fraction(0)) / (len(r) - 1)
        if var > 0:
            sharpe = float(mean) / math.sqrt(float(var)) * math.sqrt(float(periods))
    peak, dd = None, Fraction(0)
    for e in equity:
        peak = e if peak is None or e > peak else peak
        dd = max(dd, (peak - e) / peak * 100)
    longest = run = 0
    for p in pnls:
        run = run + 1 if p < 0 else 0
        longest = max(longest, run)
    aw = sum(wins, Fraction(0)) / len(wins) if wins else Fraction(0)
    al = sum(losses, Fraction(0)) / len(losses) if losses else Fraction(0)
    return {"total_pnl_jpy": float(sum(pnls, Fraction(0))), "num_trades": n,
            "win_rate_pct": float(Fraction(len(wins) * 100, n)) if n else 0.0, "profit_factor": pf,
            "sharpe_ratio": sharpe, "max_drawdown_pct": float(dd), "max_consecutive_losses": longest,
            "avg_win_jpy": float(aw), "avg_loss_jpy": float(al), "risk_reward_ratio": float(aw / -al) if al != 0 else 0.0,
            "expectancy_per_trade_jpy": float(sum(pnls, Fraction(0)) / n) if n else 0.0, "total_fees_jpy": float(fees)}

"""Slow reference bar backtest (one position at a time).

Written from the item-4 requirement text only (see SPEC.md section 3). Rules
fixed by the text:
  * a signal decided on bar i is executed at the OPEN of bar i+1 with taker
    cost (no look-ahead; requirement I4-8);
  * a limit fills only when its price condition is met and always at its own
    price, never at a better one (I4-9);
  * when a bar's range reaches both the stop and the take-profit, the stop
    is taken (stop priority, I4-10);
  * with max_hold_bars = N the position is closed by taker at the OPEN of bar
    entry_bar + N, where entry_bar is the bar the entry filled in (I4-13);
  * entry_sides filters by direction at the signal bar (I4-14).
Every rule the text leaves open is a required keyword argument of `run_bars`
with no default (see SPEC.md section 3.2).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Optional

from bot.bt.reference.num import choice, ns, q, q_str

SIDE_SIGN = {"long": 1, "short": -1}


@dataclass(frozen=True)
class Bar:
    t_open: int
    open: Fraction
    high: Fraction
    low: Fraction
    close: Fraction


def make_bar(t_open: int, open, high, low, close) -> Bar:
    o, h, l, c = q(open, "open"), q(high, "high"), q(low, "low"), q(close, "close")
    if not (0 < l <= min(o, c) and h >= max(o, c)):
        raise ValueError("bar must satisfy 0 < low <= min(open,close), high >= max(open,close)")
    return Bar(ns(t_open, "t_open"), o, h, l, c)


@dataclass(frozen=True)
class Signal:
    """Entry request decided at the close of its bar.

    side: "long" | "short".
    limit: None = market entry at the next open; a price = limit entry that
           may fill on bars i+1 .. i+limit_valid_bars.
    sl_dist / tp_dist: None = off; else a positive price distance from the
           entry fill price (stop = entry -/+ sl_dist, tp = entry +/- tp_dist).
    """
    side: str
    limit: Optional[object] = None
    sl_dist: Optional[object] = None
    tp_dist: Optional[object] = None


@dataclass
class Trade:
    side: str
    signal_bar: int
    entry_bar: int
    entry_price: Fraction
    entry_fee: Fraction
    entry_liquidity: str
    qty: Fraction
    sl: Optional[Fraction]
    tp: Optional[Fraction]
    exit_bar: Optional[int] = None
    exit_price: Optional[Fraction] = None
    exit_fee: Optional[Fraction] = None
    exit_liquidity: Optional[str] = None
    reason: Optional[str] = None

    @property
    def pnl(self) -> Fraction:
        s = SIDE_SIGN[self.side]
        return s * (self.exit_price - self.entry_price) * self.qty - self.entry_fee - self.exit_fee

    def to_dict(self) -> dict:
        d = {"side": self.side, "signal_bar": self.signal_bar, "entry_bar": self.entry_bar,
             "entry_price": q_str(self.entry_price), "entry_fee": q_str(self.entry_fee),
             "entry_liquidity": self.entry_liquidity, "qty": q_str(self.qty),
             "sl": None if self.sl is None else q_str(self.sl),
             "tp": None if self.tp is None else q_str(self.tp)}
        if self.exit_bar is not None:
            d.update(exit_bar=self.exit_bar, exit_price=q_str(self.exit_price),
                     exit_fee=q_str(self.exit_fee), exit_liquidity=self.exit_liquidity,
                     reason=self.reason, pnl=q_str(self.pnl))
        return d


@dataclass
class BarResult:
    trades: list = field(default_factory=list)
    open_trade: Optional[Trade] = None
    missed_fills: int = 0
    ignored_signals: list = field(default_factory=list)  # (bar, reason)
    equity: list = field(default_factory=list)  # per bar close
    initial_cash: Fraction = Fraction(0)

    def to_dict(self) -> dict:
        return {"trades": [t.to_dict() for t in self.trades],
                "open_trade": None if self.open_trade is None else self.open_trade.to_dict(),
                "missed_fills": self.missed_fills,
                "ignored_signals": [list(x) for x in self.ignored_signals],
                "equity": [q_str(x) for x in self.equity]}


def run_bars(
    bars,
    signals,
    *,
    qty,
    initial_cash,
    taker_rate,
    maker_rate,
    limit_cross: str,
    stop_trigger: str,
    stop_fill: str,
    tp_fee: str,
    exits_from_entry_bar: bool,
    limit_valid_bars: int,
    mask,
    mask_applies_to: str,
    entry_sides: str,
    max_hold_bars,
    close_at_end: bool,
) -> BarResult:
    """Run a bar backtest. `signals[i]` is None or a Signal decided at bar i.

    limit_cross:  "strict" (buy limit needs low < L; TP of a long needs
                  high > tp) | "touch" (<= / >=).  Used for limit entries and
                  for the take-profit, which is a resting limit.
    stop_trigger: "touch" (long stop hit when low <= sl) | "strict" (low < sl).
    stop_fill:    "level" (exit at the stop price) |
                  "worse_of_level_and_open" (on a bar after the entry bar that
                  opens beyond the stop, exit at the open).
    tp_fee:       "maker" | "taker" - fee rate applied to the take-profit.
    exits_from_entry_bar: True = stop/TP are checked on the bar the entry
                  filled in too; False = from the next bar.
    limit_valid_bars: >= 1, bars a limit entry stays live (i+1..i+k).
    mask:         None or a list of bool, one per bar; False blocks new entries.
    mask_applies_to: "signal_bar" | "fill_bar".
    entry_sides:  "both" | "long" | "short".
    max_hold_bars: None or int >= 1.
    close_at_end: True = close an open position at the last close (taker).
    """
    bars = list(bars)
    for b in bars:
        if not isinstance(b, Bar):
            raise TypeError("bars must be Bar (use make_bar)")
    for a, b in zip(bars, bars[1:]):
        if not a.t_open < b.t_open:
            raise ValueError("bar times must be strictly increasing")
    n = len(bars)
    signals = list(signals)
    if len(signals) != n:
        raise ValueError("signals must have one entry per bar")
    qty = q(qty, "qty")
    if qty <= 0:
        raise ValueError("qty must be > 0")
    initial_cash = q(initial_cash, "initial_cash")
    taker_rate, maker_rate = q(taker_rate, "taker_rate"), q(maker_rate, "maker_rate")
    choice(limit_cross, ("strict", "touch"), "limit_cross")
    choice(stop_trigger, ("strict", "touch"), "stop_trigger")
    choice(stop_fill, ("level", "worse_of_level_and_open"), "stop_fill")
    choice(tp_fee, ("maker", "taker"), "tp_fee")
    if not isinstance(exits_from_entry_bar, bool) or not isinstance(close_at_end, bool):
        raise TypeError("exits_from_entry_bar and close_at_end must be bool")
    if isinstance(limit_valid_bars, bool) or not isinstance(limit_valid_bars, int) or limit_valid_bars < 1:
        raise ValueError("limit_valid_bars must be int >= 1")
    choice(mask_applies_to, ("signal_bar", "fill_bar"), "mask_applies_to")
    choice(entry_sides, ("both", "long", "short"), "entry_sides")
    if mask is not None:
        mask = list(mask)
        if len(mask) != n or not all(isinstance(m, bool) for m in mask):
            raise ValueError("mask must be a list of bool, one per bar")
    if max_hold_bars is not None and (isinstance(max_hold_bars, bool) or not isinstance(max_hold_bars, int)
                                      or max_hold_bars < 1):
        raise ValueError("max_hold_bars must be None or int >= 1")

    def allowed(i: int) -> bool:
        return mask is None or mask[i]

    def fee(price: Fraction, liq: str) -> Fraction:
        return price * qty * (maker_rate if liq == "maker" else taker_rate)

    res = BarResult(initial_cash=initial_cash)
    closed_pnl = Fraction(0)
    pos: Optional[Trade] = None
    pending = None  # dict(sig, signal_bar, first, last)

    def open_trade(sig: Signal, i_sig: int, j: int, price: Fraction, liq: str) -> Trade:
        s = SIDE_SIGN[sig.side]
        sl = None if sig.sl_dist is None else price - s * q(sig.sl_dist, "sl_dist")
        tp = None if sig.tp_dist is None else price + s * q(sig.tp_dist, "tp_dist")
        return Trade(sig.side, i_sig, j, price, fee(price, liq), liq, qty, sl, tp)

    def close(tr: Trade, j: int, price: Fraction, liq: str, reason: str) -> None:
        nonlocal closed_pnl
        tr.exit_bar, tr.exit_price, tr.exit_liquidity, tr.reason = j, price, liq, reason
        tr.exit_fee = fee(price, liq)
        closed_pnl += tr.pnl
        res.trades.append(tr)

    for j, b in enumerate(bars):
        # 1. pending entry
        if pending is not None and pos is None:
            sig, i_sig = pending["sig"], pending["signal_bar"]
            if j >= pending["first"]:
                can = mask_applies_to != "fill_bar" or allowed(j)
                if sig.limit is None:
                    if can:
                        pos = open_trade(sig, i_sig, j, b.open, "taker")
                    else:
                        res.ignored_signals.append((i_sig, "mask_at_fill_bar"))
                    pending = None
                else:
                    lim = q(sig.limit, "limit")
                    if sig.side == "long":
                        hit = b.low < lim or (limit_cross == "touch" and b.low == lim)
                    else:
                        hit = b.high > lim or (limit_cross == "touch" and b.high == lim)
                    if can and hit:
                        pos = open_trade(sig, i_sig, j, lim, "maker")
                        pending = None
                    elif j >= pending["last"]:
                        res.missed_fills += 1
                        pending = None
        # 2. exits
        if pos is not None:
            s = SIDE_SIGN[pos.side]
            if max_hold_bars is not None and j == pos.entry_bar + max_hold_bars:
                close(pos, j, b.open, "taker", "max_hold")
                pos = None
            elif j > pos.entry_bar or exits_from_entry_bar:
                stop_hit = tp_hit = False
                if pos.sl is not None:
                    if s == 1:
                        stop_hit = b.low < pos.sl or (stop_trigger == "touch" and b.low == pos.sl)
                    else:
                        stop_hit = b.high > pos.sl or (stop_trigger == "touch" and b.high == pos.sl)
                if pos.tp is not None:
                    if s == 1:
                        tp_hit = b.high > pos.tp or (limit_cross == "touch" and b.high == pos.tp)
                    else:
                        tp_hit = b.low < pos.tp or (limit_cross == "touch" and b.low == pos.tp)
                if stop_hit:
                    px = pos.sl
                    if stop_fill == "worse_of_level_and_open" and j > pos.entry_bar:
                        px = min(pos.sl, b.open) if s == 1 else max(pos.sl, b.open)
                    close(pos, j, px, "taker", "stop")
                    pos = None
                elif tp_hit:
                    close(pos, j, pos.tp, tp_fee, "take_profit")
                    pos = None
        # 3. signal decided at this bar's close
        sig = signals[j]
        if sig is not None:
            if not isinstance(sig, Signal):
                raise TypeError("signals must be None or Signal")
            choice(sig.side, ("long", "short"), "signal.side")
            for k in ("sl_dist", "tp_dist"):
                v = getattr(sig, k)
                if v is not None and q(v, k) <= 0:
                    raise ValueError(f"{k} must be > 0")
            if sig.limit is not None and q(sig.limit, "limit") <= 0:
                raise ValueError("limit must be > 0")
            if entry_sides != "both" and sig.side != entry_sides:
                res.ignored_signals.append((j, "side_filtered"))
            elif mask_applies_to == "signal_bar" and not allowed(j):
                res.ignored_signals.append((j, "mask_at_signal_bar"))
            elif pos is not None:
                res.ignored_signals.append((j, "in_position"))
            elif pending is not None:
                res.ignored_signals.append((j, "entry_pending"))
            elif j == n - 1:
                res.ignored_signals.append((j, "no_next_bar"))
            else:
                last = j + 1 if sig.limit is None else j + limit_valid_bars
                pending = {"sig": sig, "signal_bar": j, "first": j + 1, "last": last}
        # 4. equity at this bar's close (entry fee of an open trade already paid)
        eq = initial_cash + closed_pnl
        if pos is not None:
            eq += SIDE_SIGN[pos.side] * (b.close - pos.entry_price) * qty - pos.entry_fee
        res.equity.append(eq)

    if pending is not None:
        # the limit window runs past the last bar: not counted as missed
        # (its last bar was never seen), recorded instead
        res.ignored_signals.append((pending["signal_bar"], "window_cut_by_end"))
    if pos is not None:
        if close_at_end and n:
            close(pos, n - 1, bars[-1].close, "taker", "end")
            res.equity[-1] = initial_cash + closed_pnl
        else:
            res.open_trade = pos
    return res

"""Bar-backtest reference written only from the item-4 scene book's rule text.

Source of every rule: the section "bar model specification" of
tests/bt/battery/item_4/DEFINITIONS.md (rules R-T, R-C, R-A, R-M, R-P, R-X,
R-W, R-H, R-E, R-S, R-O), plus two decisions fixed by the lead for the finish
round (delegation 20260926_backtest_env_finish.md section 1, i4-r2-02 and
i4-r2-08):
  * on the max-hold bar the time exit at the open comes before any range
    event (R-O1 open events first; R-H3 "only the stop is looked at first"
    is read as an order inside the range, after the open);
  * a signal whose entry is blocked by the mask places no limit and counts
    no miss; a signal in the same direction as a waiting entry limit does
    not re-place it (the old limit stays).
The core, the new engine and the worker's rule copy were not opened.

Every number is an exact fractions.Fraction. A float input is read as the
decimal it prints as (repr), because R-X1 compares levels "as the written
decimal value". Points the rule text does not decide are required keys of
options["undecided"] (no defaults); see SPEC.md section 4.

Entry point: run_bars(bars, signals, options) -> BarRun.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from numbers import Rational
from typing import Optional

SIGNALS = ("BUY", "SELL", "CLOSE")
OPTION_KEYS = (
    "capital", "order_amount", "bar_seconds", "costs", "execution",
    "maker_timeout_bars", "allow_short", "swap_daily_pct", "stop_loss_pct",
    "take_profit_pct", "max_hold_bars", "exit_execution", "maker_tp_pct",
    "entry_mask", "entry_sides", "stop_mode", "stop_window_bars", "undecided",
)
COST_KEYS = ("taker_fee_pct", "maker_fee_pct", "slippage_pct", "spread_pct")
UNDECIDED = {
    # R-W1 takes bars b-N..b-1; the text does not say what happens when b < N.
    "wick_short_history": ("refuse", "use_available", "no_stop"),
    # R-M/i4-r2-08 decide the same-direction case only for a waiting ENTRY
    # limit; for a waiting EXIT limit (closing order) the text is silent.
    "same_side_exit_signal": ("keep", "replace"),
}
HUNDRED = Fraction(100)
DAY_SECONDS = Fraction(86400)


class RefusedConfig(ValueError):
    """The options break a rule that says 'refuse' (R-X3, R-W4) or are malformed."""


def dec(x, name: str) -> Fraction:
    """Exact value of x as written: float -> its repr decimal, str -> parsed."""
    if isinstance(x, bool):
        raise TypeError(f"{name}: bool is not a number")
    if isinstance(x, Fraction):
        return x
    if isinstance(x, int):
        return Fraction(x)
    if isinstance(x, float):
        if x != x or x in (float("inf"), float("-inf")):
            raise ValueError(f"{name}: non-finite {x!r}")
        return Fraction(repr(x))
    if isinstance(x, str):
        return Fraction(x.strip())
    if isinstance(x, Rational):
        return Fraction(x.numerator, x.denominator)
    raise TypeError(f"{name}: unsupported type {type(x).__name__}")


@dataclass(frozen=True)
class Fill:
    bar: int
    side: str          # OPEN_LONG / OPEN_SHORT / CLOSE_LONG / CLOSE_SHORT
    price: Fraction
    size: Fraction
    fee: Fraction
    liquidity: str     # "taker" or "maker"
    reason: str        # what caused it (for reading; not part of the rules)


@dataclass
class Trade:
    direction: int     # +1 long, -1 short
    entry_bar: int
    entry_price: Fraction
    size: Fraction
    entry_fee: Fraction
    carry: Fraction = Fraction(0)
    exit_bar: Optional[int] = None
    exit_price: Optional[Fraction] = None
    exit_fee: Optional[Fraction] = None
    exit_reason: Optional[str] = None
    pnl: Optional[Fraction] = None
    stop_level: Optional[Fraction] = None
    tp_level: Optional[Fraction] = None
    mtp_level: Optional[Fraction] = None
    wick_level: Optional[Fraction] = None


@dataclass
class BarRun:
    fills: list = field(default_factory=list)
    pnls: list = field(default_factory=list)
    equity: list = field(default_factory=list)
    missed_fills: int = 0
    trades: list = field(default_factory=list)
    open_trade: Optional[Trade] = None

    def to_dict(self) -> dict:
        """Fractions as canonical strings, for exact comparison."""
        return {
            "fills": [{"bar": f.bar, "side": f.side, "price": str(f.price), "size": str(f.size),
                       "fee": str(f.fee), "liquidity": f.liquidity, "reason": f.reason}
                      for f in self.fills],
            "pnls": [str(p) for p in self.pnls],
            "equity": [str(e) for e in self.equity],
            "missed_fills": self.missed_fills,
        }

    def to_floats(self) -> dict:
        """Same content as floats (for a tolerance comparison with a float engine)."""
        return {
            "fills": [{"bar": f.bar, "side": f.side, "price": float(f.price), "size": float(f.size)}
                      for f in self.fills],
            "pnls": [float(p) for p in self.pnls],
            "equity": [float(e) for e in self.equity],
            "missed_fills": self.missed_fills,
        }


def _bars(bars) -> list:
    out = []
    for i, b in enumerate(bars):
        if isinstance(b, dict):
            o, h, l, c = (b[k] for k in ("open", "high", "low", "close"))
        else:
            o, h, l, c = b
        o, h, l, c = (dec(v, f"bar {i} {k}") for v, k in zip((o, h, l, c), "ohlc"))
        if not (l <= min(o, c) and max(o, c) <= h):
            raise RefusedConfig(f"bar {i}: not low <= open,close <= high")
        out.append((o, h, l, c))
    return out


def _signals(signals, n: int) -> list:
    out = [None] * n
    items = signals.items() if isinstance(signals, dict) else enumerate(signals)
    if not isinstance(signals, dict) and len(signals) != n:
        raise RefusedConfig("signals: a sequence must have one entry per bar")
    for i, s in items:
        if isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < n:
            raise RefusedConfig(f"signals: bad bar index {i!r}")
        if s is None or s == "HOLD":
            continue
        if s not in SIGNALS:
            raise RefusedConfig(f"signals: bar {i}: {s!r} not in {SIGNALS}")
        out[i] = s
    return out


def _opt_pct(v, name):
    if v is None:
        return None
    x = dec(v, name)
    if x <= 0:
        raise RefusedConfig(f"{name}: must be None (off) or > 0, got {v!r}")
    return x


def _opt_int(v, name):
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, int) or v < 1:
        raise RefusedConfig(f"{name}: must be None (off) or an int >= 1, got {v!r}")
    return v


def _options(options: dict, n: int) -> dict:
    missing = [k for k in OPTION_KEYS if k not in options]
    extra = [k for k in options if k not in OPTION_KEYS]
    if missing or extra:
        raise RefusedConfig(f"options: missing {missing}, unknown {extra}")
    o = {}
    o["capital"] = dec(options["capital"], "capital")
    o["order_amount"] = dec(options["order_amount"], "order_amount")
    if o["order_amount"] <= 0:
        raise RefusedConfig("order_amount must be > 0")
    bs = options["bar_seconds"]
    if isinstance(bs, bool) or not isinstance(bs, int) or bs <= 0:
        raise RefusedConfig("bar_seconds must be an int > 0")
    o["bar_seconds"] = bs
    costs = options["costs"]
    if set(costs) != set(COST_KEYS):
        raise RefusedConfig(f"costs: need exactly {COST_KEYS}")
    o.update({k: dec(costs[k], k) for k in COST_KEYS})
    if options["execution"] not in ("taker", "maker"):
        raise RefusedConfig("execution: taker or maker")
    o["execution"] = options["execution"]
    o["maker_timeout_bars"] = _opt_int(options["maker_timeout_bars"], "maker_timeout_bars")
    if o["execution"] == "maker" and o["maker_timeout_bars"] is None:
        raise RefusedConfig("maker execution needs maker_timeout_bars >= 1 (R-M2)")
    if not isinstance(options["allow_short"], bool):
        raise RefusedConfig("allow_short: bool")
    o["allow_short"] = options["allow_short"]
    o["swap_daily_pct"] = dec(options["swap_daily_pct"], "swap_daily_pct")
    o["stop_loss_pct"] = _opt_pct(options["stop_loss_pct"], "stop_loss_pct")
    o["take_profit_pct"] = _opt_pct(options["take_profit_pct"], "take_profit_pct")
    o["max_hold_bars"] = _opt_int(options["max_hold_bars"], "max_hold_bars")
    if options["exit_execution"] not in ("signal", "maker_tp"):
        raise RefusedConfig("exit_execution: signal or maker_tp")
    o["exit_execution"] = options["exit_execution"]
    if o["exit_execution"] == "maker_tp":
        v = options["maker_tp_pct"]
        if v is None or dec(v, "maker_tp_pct") <= 0:
            raise RefusedConfig("R-X3: maker_tp needs maker_tp_pct > 0")
        o["maker_tp_pct"] = dec(v, "maker_tp_pct")
    else:
        o["maker_tp_pct"] = None
    mask = options["entry_mask"]
    if mask is not None:
        if len(mask) != n or not all(isinstance(m, bool) for m in mask):
            raise RefusedConfig("entry_mask: None or one bool per bar")
        mask = list(mask)
    o["entry_mask"] = mask
    if options["entry_sides"] not in ("both", "long", "short"):
        raise RefusedConfig("entry_sides: both, long or short")
    o["entry_sides"] = options["entry_sides"]
    if options["stop_mode"] not in ("fixed", "wick_invalidation"):
        raise RefusedConfig("stop_mode: fixed or wick_invalidation")
    o["stop_mode"] = options["stop_mode"]
    o["stop_window_bars"] = _opt_int(options["stop_window_bars"], "stop_window_bars")
    if o["stop_mode"] == "wick_invalidation":
        if o["stop_loss_pct"] is not None:
            raise RefusedConfig("R-W4: wick_invalidation and a percent stop do not stack")
        if o["stop_window_bars"] is None:
            raise RefusedConfig("wick_invalidation needs stop_window_bars >= 1 (R-W1)")
    und = options["undecided"]
    if set(und) != set(UNDECIDED):
        raise RefusedConfig(f"undecided: need exactly {tuple(UNDECIDED)}")
    for k, allowed in UNDECIDED.items():
        if und[k] not in allowed:
            raise RefusedConfig(f"undecided.{k}: one of {allowed}")
    o["undecided"] = dict(und)
    return o


def run_bars(bars, signals, options: dict) -> BarRun:
    """Run the bar model of the scene book's rule text. See SPEC.md section 3."""
    B = _bars(bars)
    n = len(B)
    S = _signals(signals, n)
    o = _options(options, n)
    run = BarRun()
    taker_rate, maker_rate = o["taker_fee_pct"], o["maker_fee_pct"]
    adj = (o["spread_pct"] / 2 + o["slippage_pct"]) / HUNDRED       # R-C1
    carry_rate = o["swap_daily_pct"] / HUNDRED * Fraction(o["bar_seconds"]) / DAY_SECONDS  # R-S1
    maker = o["execution"] == "maker"
    T = o["maker_timeout_bars"]

    pos: Optional[Trade] = None
    pending_sig = None          # taker: (signal, signal_bar) executed at next open (R-T1)
    wick_exit_next = False      # R-W3: close crossed the level, exit at next open
    entry_lim = None            # maker entry limit: dict(dir, price, placed)
    exit_lim = None             # maker exit limit: dict(price, placed)
    closed_pnl = Fraction(0)

    def taker_px(base, buy):
        return base * (1 + adj) if buy else base * (1 - adj)

    def fee(size, price, rate):
        return size * price * rate / HUNDRED                         # R-A2

    def entry_allowed(direction, sig_bar):
        if direction == -1 and not o["allow_short"]:                 # R-T4
            return False
        if o["entry_sides"] == "long" and direction == -1:           # R-E1
            return False
        if o["entry_sides"] == "short" and direction == 1:
            return False
        if o["entry_mask"] is not None and not o["entry_mask"][sig_bar]:  # R-E2
            return False
        return True

    def open_pos(j, direction, price, liquidity, reason):
        nonlocal pos
        size = o["order_amount"] / price                             # R-A1
        f = fee(size, price, taker_rate if liquidity == "taker" else maker_rate)
        t = Trade(direction, j, price, size, f)
        if o["stop_loss_pct"] is not None:                           # R-P1
            t.stop_level = price * (1 - direction * o["stop_loss_pct"] / HUNDRED)
        if o["take_profit_pct"] is not None:
            t.tp_level = price * (1 + direction * o["take_profit_pct"] / HUNDRED)
        if o["maker_tp_pct"] is not None:                            # R-X1
            t.mtp_level = price * (1 + direction * o["maker_tp_pct"] / HUNDRED)
        if o["stop_mode"] == "wick_invalidation":                    # R-W1
            N = o["stop_window_bars"]
            lo = j - N
            if lo < 0:
                mode = o["undecided"]["wick_short_history"]
                if mode == "refuse":
                    raise RefusedConfig(f"R-W1: entry at bar {j} has fewer than {N} completed bars before it")
                lo = 0 if mode == "use_available" else None
            if lo is not None and lo < j:
                window = B[lo:j]
                t.wick_level = (min(b[2] for b in window) if direction == 1
                                else max(b[1] for b in window))
        pos = t
        run.fills.append(Fill(j, "OPEN_LONG" if direction == 1 else "OPEN_SHORT",
                              price, size, f, liquidity, reason))

    def close_pos(j, price, liquidity, reason):
        nonlocal pos, closed_pnl, exit_lim
        t = pos
        f = fee(t.size, price, taker_rate if liquidity == "taker" else maker_rate)
        t.exit_bar, t.exit_price, t.exit_fee, t.exit_reason = j, price, f, reason
        t.pnl = (price - t.entry_price) * t.size * t.direction - f - t.entry_fee - t.carry  # R-A3
        closed_pnl += t.pnl
        run.fills.append(Fill(j, "CLOSE_LONG" if t.direction == 1 else "CLOSE_SHORT",
                              price, t.size, f, liquidity, reason))
        run.pnls.append(t.pnl)
        run.trades.append(t)
        pos = None
        exit_lim = None     # a waiting exit limit is dropped, not counted (R-M5)

    def closes(sig, t):
        return sig == "CLOSE" or (sig == "SELL" and t.direction == 1) or (sig == "BUY" and t.direction == -1)

    for j in range(n):
        o_, h, l, c = B[j]
        # ---- carry for bar j (R-S1): entry bar < j <= exit bar
        if pos is not None and j > pos.entry_bar:
            pos.carry += abs(pos.size) * B[j - 1][3] * carry_rate
        # ---- open events (R-O1 1-3), all at the open of bar j, taker
        if pos is not None:
            buy = pos.direction == -1
            if wick_exit_next:                                           # (1) R-W3
                close_pos(j, taker_px(o_, buy), "taker", "wick_invalidation")
                pending_sig = None
            elif o["max_hold_bars"] is not None and j == pos.entry_bar + o["max_hold_bars"]:
                close_pos(j, taker_px(o_, buy), "taker", "max_hold")     # (2) R-H1/R-H2
                pending_sig = None
            elif pending_sig is not None and closes(pending_sig[0], pos):  # (3) R-T1/R-T3
                close_pos(j, taker_px(o_, buy), "taker", "signal")
                pending_sig = None
        wick_exit_next = False
        # ---- taker entry from the signal of bar j-1 (R-T1, R-T3)
        if pending_sig is not None:
            sig, sb = pending_sig
            pending_sig = None
            if pos is None and sig in ("BUY", "SELL"):
                d = 1 if sig == "BUY" else -1
                if entry_allowed(d, sb):
                    open_pos(j, d, taker_px(o_, d == 1), "taker", "signal")
        # ---- range events of an open position (R-O1 4-7); never on its entry bar
        if pos is not None and j > pos.entry_bar:
            d = pos.direction
            hit = None
            if pos.stop_level is not None and ((d == 1 and l <= pos.stop_level) or
                                               (d == -1 and h >= pos.stop_level)):   # (4) R-P3
                base = min(o_, pos.stop_level) if d == 1 else max(o_, pos.stop_level)
                hit = (taker_px(base, d == -1), "taker", "stop_loss")
            elif pos.tp_level is not None and ((d == 1 and h > pos.tp_level) or
                                               (d == -1 and l < pos.tp_level)):      # (5) R-P4
                hit = (pos.tp_level, "maker", "take_profit")
            elif pos.mtp_level is not None and ((d == 1 and h > pos.mtp_level) or
                                                (d == -1 and l < pos.mtp_level)):    # (6) R-X1
                hit = (pos.mtp_level, "maker", "maker_tp")
            elif exit_lim is not None and j > exit_lim["placed"]:                    # (7) R-M1
                p = exit_lim["price"]
                if (d == 1 and h > p) or (d == -1 and l < p):
                    hit = (p, "maker", "exit_limit")
            if hit is not None:
                close_pos(j, *hit)
        # ---- waiting exit limit that lived its life (R-M2)
        if exit_lim is not None and j == exit_lim["placed"] + T:
            exit_lim = None
            run.missed_fills += 1
        # ---- maker entry limit (R-M1, R-M2)
        if entry_lim is not None and j > entry_lim["placed"]:
            d, p = entry_lim["dir"], entry_lim["price"]
            if pos is None and ((d == 1 and l < p) or (d == -1 and h > p)):
                entry_lim = None
                open_pos(j, d, p, "maker", "entry_limit")
            elif j == entry_lim["placed"] + T:
                entry_lim = None
                run.missed_fills += 1
        # ---- close of bar j: structural stop check (R-W2, R-W3)
        if pos is not None and pos.wick_level is not None:
            wl = pos.wick_level
            if (pos.direction == 1 and c < wl) or (pos.direction == -1 and c > wl):
                wick_exit_next = True
        # ---- signal of bar j
        sig = S[j]
        if sig is not None and not maker:
            pending_sig = (sig, j)    # R-T2: after the last bar there is no next open; it never fills
        elif sig is not None and maker:
            if pos is not None:
                if closes(sig, pos):                                     # R-M4 / R-T3
                    if exit_lim is None or o["undecided"]["same_side_exit_signal"] == "replace":
                        exit_lim = {"price": c, "placed": j}
            elif sig in ("BUY", "SELL"):
                d = 1 if sig == "BUY" else -1
                if entry_allowed(d, j):                                  # blocked: no limit, no miss
                    if entry_lim is None:
                        entry_lim = {"dir": d, "price": c, "placed": j}
                    elif entry_lim["dir"] != d:                          # R-M3
                        run.missed_fills += 1
                        entry_lim = {"dir": d, "price": c, "placed": j}
                    # same direction: keep the old limit (i4-r2-08)
        # ---- equity at the close of bar j (R-A4)
        eq = o["capital"] + closed_pnl
        if pos is not None:
            eq += (c - pos.entry_price) * pos.size * pos.direction - pos.entry_fee - pos.carry
        run.equity.append(eq)

    run.open_trade = pos
    return run

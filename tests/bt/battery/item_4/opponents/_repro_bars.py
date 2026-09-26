"""Shared order-driven bar loop for the item 4 reproductions (opponents/repro_*.py).

A reproduction is a minimal rewrite of ONE candidate's bar-backtest rules, taken line by line from its primary source
(each repro file names the file and lines of every rule it sets here).  This module holds only what every such
broker has in common -- a list of open orders, one position, fills -- and the scene's strategy (user code on top of
the tool's order API: it decides from bars 0..i only).  Every rule that differs between tools is a hook the repro
file sets; nothing here chooses a fill price, a fill bar or a trigger on its own.

Hooks (class attributes / methods of the repro adapter, a subclass of `RuleBroker`):
  MARKET        when a market order sent at the close of bar i fills: "next_open" (bar i+1, its open),
                "next_close" (bar i+1, its close), "same_close" (bar i, its close), "next_bar_prev_close"
                (bar i+1 at the price close[i] written on the order).
  limit_px(o, b) / stop_px(o, b)   -> fill price or None for a resting limit / stop order on bar b (OHLC dict).
  PATH          None, or a function b -> list of prices the tool walks inside a bar; then `path_hit(o, prev, p)`
                decides a trigger at each step (tools that simulate trades / ticks inside a bar).
  CHILD_ORDER   order in which an exit bracket's children are placed (("tp", "sl") or ("sl", "tp")).
  FEES          None | "single" (one rate for every fill) | "by_type" (maker rate for limit fills, taker otherwise).
  SLIP          None | "market" (market and stop fills move by (spread/2 + slippage) % against the order).
  qty_for(notional, ref_px) -> the entry quantity the strategy can send (ref_px = close of the signal bar).
  EQUITY        True when the tool keeps a per-bar equity (then `equity` is its cash + marked position).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from _i4_base import Base, NotExpressible, adj, fee_kinds, want  # noqa: E402,F401
from i4_protocol import signal_map  # noqa: E402

BUY, SELL = "buy", "sell"


class Order:
    def __init__(self, typ, side, qty, level=None, kind="entry", placed=0, active_from=None, ref_px=None):
        self.typ, self.side, self.qty, self.level, self.kind = typ, side, qty, level, kind
        self.placed = placed
        self.active_from = placed + 1 if active_from is None else active_from
        self.ref_px = ref_px
        self.status = "open"
        self.oco: list[Order] = []


class RuleBroker(Base):
    MARKET = "next_open"
    PATH = None
    CHILD_ORDER = ("sl", "tp")
    FEES = None
    SLIP = None
    EQUITY = False
    LIMIT_TYPES = True   # the tool has resting limit orders
    STOP_TYPES = True    # the tool has resting stop orders
    SKIP_SIGNAL_BARS: tuple = ()  # e.g. ("first", "last"): bars where the tool does not call the strategy

    # ---- hooks with neutral defaults (a repro file overrides what its tool does) ----
    def limit_px(self, o, b):  # pragma: no cover - set per repro
        return None

    def stop_px(self, o, b):  # pragma: no cover
        return None

    def path_hit(self, o, prev, p):  # pragma: no cover
        return None

    def qty_for(self, notional, ref_px):
        return notional / ref_px

    def fee_rate(self, cfg, liq):
        c = cfg["costs"]
        if self.FEES is None:
            return 0.0
        if self.FEES == "single":
            return c["taker_fee_pct"] if liq == "taker" else c["maker_fee_pct"]
        return c["maker_fee_pct"] if liq == "maker" else c["taker_fee_pct"]

    # ---- gates shared by the reproductions ----
    def extra_gate(self, inp):
        cfg = inp["config"]
        c = cfg["costs"]
        out = []
        kinds = fee_kinds(cfg)
        rates = {k: c[f"{k}_fee_pct"] for k in kinds}
        if self.FEES is None and any(rates.values()):
            out.append(self.MISSING.get("taker_fee_pct", "手数料の口を探したが無い"))
        if self.FEES == "single" and len(set(rates.values())) > 1:
            out.append("手数料の率は 1 つだけで、maker と taker に別の率を置く口が無い")
        if self.SLIP is None and (c["slippage_pct"] or c["spread_pct"]) and "taker" in kinds:
            out.append(self.MISSING.get("slippage_pct", "滑り・スプレッドの口を探したが無い"))
        w = set(inp.get("want") or [])
        if "equity" in w and not self.EQUITY:
            out.append(self.MISSING.get("equity", "足ごとの資産の系列を出す口を探したが無い"))
        if "metrics" in w:
            out.append(self.METRICS or "12 の指標を出す口を探したが無い")
        out += self.more_gate(inp)
        return out

    def more_gate(self, inp):
        return []

    # ---- the loop ----
    def bars(self, inp):
        cfg = inp["config"]
        bars = inp["bars"]
        n = len(bars)
        sig = signal_map(inp)
        a = adj(cfg["costs"]) if self.SLIP else 0.0
        st = {"pos": None, "orders": [], "fills": [], "pnls": [], "missed": 0, "realized": 0.0}
        equity = []

        def book_fill(o, i, px):
            liq = "maker" if o.typ == "limit" else "taker"
            if self.SLIP == "market" and (o.typ in ("market", "stop") or self.SLIP_ALL):
                px = self.slip_px(o, px, a, bars[i])
            fee = self.fee_amount(abs(o.qty), px, self.fee_rate(cfg, liq))
            o.status = "filled"
            for x in o.oco:
                if x.status == "open":
                    x.status = "canceled"
            pos = st["pos"]
            if o.kind == "entry":
                d = 1 if o.side == BUY else -1
                st["pos"] = {"dir": d, "qty": o.qty, "px": px, "fee": fee, "bar": i}
                st["fills"].append({"bar": i, "side": "OPEN_LONG" if d > 0 else "OPEN_SHORT", "price": px, "size": o.qty})
                self.after_entry(st, cfg, bars, i)
            else:
                if pos is None:
                    return
                st["fills"].append({"bar": i, "side": "CLOSE_LONG" if pos["dir"] > 0 else "CLOSE_SHORT", "price": px,
                                    "size": pos["qty"]})
                pnl = self.trade_pnl(pos, px, fee, cfg)
                st["pnls"].append(pnl)
                st["realized"] += pnl
                st["pos"] = None
                for x in st["orders"]:
                    if x.status == "open" and x.kind in ("sl", "tp", "mtp"):
                        x.status = "canceled"

        def process_bar(i):
            b = bars[i]
            live = [o for o in st["orders"] if o.status == "open" and o.active_from <= i]
            if self.PATH is not None:
                self._prev_close = bars[i - 1]["close"] if i else b["open"]
                pts = self.PATH(b)
                prev = None
                for p in pts:
                    for o in live:
                        if o.status != "open":
                            continue
                        px = self.path_hit(o, prev, p) if o.typ != "market" else (p if prev is None else None)
                        if px is not None:
                            book_fill(o, i, px)
                    prev = p
                return
            cands = []
            for o in live:
                px = None
                if o.typ == "market":
                    px = {"next_open": b["open"], "next_close": b["close"],
                          "next_bar_prev_close": o.ref_px}.get(self.MARKET)
                elif o.typ == "limit":
                    px = self.limit_px(o, b)
                elif o.typ == "stop":
                    px = self.stop_px(o, b)
                if px is not None:
                    cands.append((o, px))
            for o, px in self.resolve(cands):
                if o.status == "open":
                    book_fill(o, i, px)

        def send_market(side, qty, kind, i):
            o = Order("market", side, qty, kind=kind, placed=i, ref_px=bars[i]["close"])
            st["orders"].append(o)
            if self.MARKET == "same_close":
                book_fill(o, i, bars[i]["close"])
            return o

        def strategy(i):
            b = bars[i]
            pos = st["pos"]
            # resting maker entries: the strategy cancels after maker_timeout_bars bars
            for o in st["orders"]:
                if o.status == "open" and o.kind == "entry" and o.typ == "limit" \
                        and i >= o.placed + cfg["maker_timeout_bars"]:
                    o.status = "canceled"
                    st["missed"] += 1
            if self.skip_bar(i, n):
                return
            s = sig.get(i)
            if pos is not None:
                N = cfg["max_hold_bars"]
                if N is not None and i + 1 - pos["bar"] >= N:
                    self.exit_now(st, i, send_market)
                    return
                if cfg["stop_mode"] == "wick_invalidation" and pos.get("wick") is not None:
                    lvl = pos["wick"]
                    if (b["close"] < lvl) if pos["dir"] > 0 else (b["close"] > lvl):
                        self.exit_now(st, i, send_market)
                        return
            if not s:
                return
            closing = pos is not None and (s == "CLOSE" or (s == "BUY" and pos["dir"] < 0) or (s == "SELL" and pos["dir"] > 0))
            if closing:
                if cfg["execution"] == "maker":
                    self.place_limit_exit(st, i, pos)
                else:
                    self.exit_now(st, i, send_market)
                return
            if s == "CLOSE" or pos is not None:
                return
            if s == "SELL" and not cfg["allow_short"]:
                return
            if cfg["entry_sides"] == "long" and s == "SELL" or cfg["entry_sides"] == "short" and s == "BUY":
                return
            if cfg["entry_mask"] is not None and not cfg["entry_mask"][i]:
                return
            side = BUY if s == "BUY" else SELL
            for o in st["orders"]:
                if o.status == "open" and o.kind == "entry" and o.typ == "limit":
                    o.status = "canceled"
                    st["missed"] += 1
            ref = b["close"]
            qty = self.qty_for(cfg["order_notional"], ref)
            if qty <= 0:
                return
            if cfg["execution"] == "maker":
                st["orders"].append(Order("limit", side, qty, level=ref, kind="entry", placed=i))
            else:
                send_market(side, qty, "entry", i)

        self._st = st
        for i in range(n):
            process_bar(i)
            strategy(i)
            if self.EQUITY:
                pos = st["pos"]
                e = cfg["initial_equity"] + st["realized"]
                if pos is not None:
                    e += (bars[i]["close"] - pos["px"]) * pos["qty"] * pos["dir"] - pos["fee"]
                equity.append(e)
        for o in st["orders"]:
            if o.status == "open" and o.kind == "entry" and o.typ == "limit":
                st["missed"] += 1
        obs = {"fills": st["fills"], "pnls": st["pnls"], "missed_fills": st["missed"]}
        if self.EQUITY:
            obs["equity"] = equity
        return want(inp, obs)

    # ---- pieces a repro may override ----
    SLIP_ALL = False   # True: the tool moves every fill (not only market / stop) by the slippage

    def slip_px(self, o, px, a, b):
        return px * (1 + a) if o.side == BUY else px * (1 - a)

    def fee_amount(self, qty, px, rate_pct):
        return qty * px * rate_pct / 100

    def resolve(self, cands):
        """Orders hit on one bar, in the tool's processing order (default: the order they were sent)."""
        return cands

    def skip_bar(self, i, n):
        return ("first" in self.SKIP_SIGNAL_BARS and i == 0) or ("last" in self.SKIP_SIGNAL_BARS and i == n - 1)

    def trade_pnl(self, pos, px, exit_fee, cfg):
        return (px - pos["px"]) * pos["qty"] * pos["dir"] - pos["fee"] - exit_fee

    def exit_now(self, st, i, send_market):
        pos = st["pos"]
        for x in st["orders"]:
            if x.status == "open" and x.kind in ("sl", "tp", "mtp"):
                x.status = "canceled"
        send_market(SELL if pos["dir"] > 0 else BUY, pos["qty"], "exit", i)

    def place_limit_exit(self, st, i, pos):
        st["orders"].append(Order("limit", SELL if pos["dir"] > 0 else BUY, pos["qty"], level=self._bars_close(i),
                                  kind="exit", placed=i))

    def _bars_close(self, i):
        return self._inp_bars[i]["close"]

    def run(self, inp):
        self._inp_bars = inp.get("bars") or []
        return super().run(inp)

    def after_entry(self, st, cfg, bars, i):
        """Exit orders the strategy sends when its entry fills (active from the next bar)."""
        pos = st["pos"]
        d = pos["dir"]
        ex = SELL if d > 0 else BUY
        if cfg["stop_mode"] == "wick_invalidation":
            W = cfg["stop_window_bars"]
            lo = max(0, i - W)
            win = bars[lo:i]
            pos["wick"] = (min(x["low"] for x in win) if d > 0 else max(x["high"] for x in win)) if win else None
        kids = {}
        if cfg["stop_loss_pct"]:
            kids["sl"] = Order("stop", ex, pos["qty"], level=pos["px"] * (1 - d * cfg["stop_loss_pct"] / 100),
                               kind="sl", placed=i)
        if cfg["take_profit_pct"]:
            kids["tp"] = Order("limit", ex, pos["qty"], level=pos["px"] * (1 + d * cfg["take_profit_pct"] / 100),
                               kind="tp", placed=i)
        if cfg["exit_execution"] == "maker_tp":
            kids["tp"] = Order("limit", ex, pos["qty"], level=pos["px"] * (1 + d * cfg["maker_tp_pct"] / 100),
                               kind="mtp", placed=i)
        placed = [kids[k] for k in self.CHILD_ORDER if k in kids]
        for o in placed:
            o.oco = [x for x in placed if x is not o]
        st["orders"].extend(placed)


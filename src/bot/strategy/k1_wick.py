"""K1 (カツオの機構: ヒゲ 4 分類 × 長さ門) as a strategy of the new backtest
environment (stage A of L-479, 2026-09-27).

The rules are those K1 actually measured, read from docs/PHASE2/K1/RESULT.md
第 1 部 (1.2 足を作る, 1.3 シグナル, 1.4 建玉を 1 単位持って回す) -- NOT copied from
scripts/measure_katsuo_effect.py (that script was opened to read the rules
only; the arithmetic here is written anew on the core's event interface so
that the environment, not the old script, is what gets tested).

  signal_of_bar(o, h, l, c, s, b)   1.3: one bar -> (sig, lcprice, csign, strength)
  K1WickStrategy                    1.4: the position machine on bot.bt.core.Strategy,
                                    one unit, entries and exits as MARKET orders sent
                                    at the close of the bar that decided them
  BarCloseMarketFill                the fill socket that prices a market order at the
                                    close of the last bar the venue has seen (1.4:
                                    建値も決済値も「その足の終値」)
  K1Setup                           the bot.bt.repro.runner setup: config -> Parts

Gate labels follow RESULT.md 1.3: s in {"off", "-", "10", "19", "30"} (small branch:
off = the branch is not used, "-" = no minimum length), b in {"-", "24", "40"} (big
branch: "-" = not used); strength in {"strong", "weak", "both"}.

Costs: none (RESULT.md 1.4 経費は引いていない): the setup's cost model charges the
rates the config states, and the stage A config states 0 / 0.
"""
from __future__ import annotations

import hashlib
import inspect
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from bot.bt.core import (Ack, BarEvent, Canceled, Event, Fill, NullAccount, OrderRequest, Reject, Strategy,
                         StrategyContext, VenueReport, ZeroLatency)
from bot.bt.repro.fixed import DeclaredFeeCost, Parts

SMALL = ("off", "-", "10", "19", "30")
BIG = ("-", "24", "40")
STRENGTHS = ("strong", "weak", "both")
INVALIDATED, OPPOSITE_WEAK, REVERSED = "invalidated", "opposite_weak", "reversed"
EXIT_REASONS = (INVALIDATED, OPPOSITE_WEAK, REVERSED)


class K1Error(ValueError):
    pass


def gates() -> list[tuple[str, str]]:
    """RESULT.md 1.3: the 13 gates. `s=off, b=-` is empty; a numeric s > numeric b
    is the same rule as (off, b)."""
    out = []
    for s in SMALL:
        for b in BIG:
            if s == "off" and b == "-":
                continue
            if s not in ("off", "-") and b != "-" and float(s) > float(b):
                continue
            out.append((s, b))
    return out


def gate_label(s: str, b: str) -> str:
    return f"s{s}/b{b}"


def signal_of_bar(o: float, h: float, l: float, c: float, s: str, b: str) -> tuple[int, float, int, str]:
    """RESULT.md 1.3. Returns (sig, lcprice, csign, strength); sig 0 = no signal."""
    candle = c - o
    csign = 1 if candle > 0 else (-1 if candle < 0 else 0)
    if csign == 0:
        return 0, 0.0, 0, ""
    if csign == 1:
        top, under = h - c, o - l
    else:
        top, under = h - o, c - l
    # 条件 3: int() で切り捨ててから比較(原典どおり)
    if int(top) > int(under):
        sig, w, lc = -1, top, h
    elif int(under) > int(top):
        sig, w, lc = 1, under, l
    else:
        return 0, 0.0, csign, ""
    wbp = w / c * 10000.0
    body = abs(candle)
    small_ok = s != "off" and (s == "-" or wbp >= float(s)) and w > body
    big_ok = b != "-" and wbp >= float(b)
    if not (small_ok or big_ok):
        return 0, 0.0, csign, ""
    return sig, lc, csign, ("strong" if sig == csign else "weak")


class K1WickStrategy(Strategy):
    """RESULT.md 1.4. One unit. Orders: market, size 1, client ids `e<k>` (entry)
    and `x<k>` (exit); `exit_reasons` maps each exit id to its reason."""

    def __init__(self, s: str, b: str, strength: str) -> None:
        if s not in SMALL or b not in BIG:
            raise K1Error(f"gate must be s in {SMALL}, b in {BIG}; got {s!r}, {b!r}")
        if (s, b) not in gates():
            raise K1Error(f"gate {gate_label(s, b)} is not one of the 13 (empty or a duplicate rule)")
        if strength not in STRENGTHS:
            raise K1Error(f"strength must be one of {STRENGTHS}, got {strength!r}")
        self.s, self.b, self.keep = s, b, strength
        self.pos = 0
        self.lcline = 0.0
        self.entry_bar = -1
        self.bar_index = -1
        self.n_orders = 0
        self.exit_reasons: dict[str, str] = {}
        self.entry_bars: dict[str, int] = {}  # entry order id -> bar index (holding bars are measured by index)
        self.exit_bars: dict[str, int] = {}
        self.signals = 0

    def _order(self, ctx: StrategyContext, side: str, kind: str, reason: Optional[str]) -> str:
        self.n_orders += 1
        oid = f"{kind}{self.n_orders}"
        ctx.place_order(OrderRequest(side=side, order_type="market", size=1.0, client_order_id=oid))
        if reason is not None:
            self.exit_reasons[oid] = reason
            self.exit_bars[oid] = self.bar_index
        else:
            self.entry_bars[oid] = self.bar_index
        return oid

    def _open(self, ctx: StrategyContext, sig: int, lc: float) -> None:
        self._order(ctx, "buy" if sig == 1 else "sell", "e", None)
        self.pos, self.lcline, self.entry_bar = sig, lc, self.bar_index

    def _close(self, ctx: StrategyContext, reason: str) -> None:
        self._order(ctx, "sell" if self.pos == 1 else "buy", "x", reason)
        self.pos = 0

    def on_event(self, event: Event, ctx: StrategyContext) -> None:
        if type(event) is not BarEvent:
            return
        self.bar_index += 1
        sig, lc, csign, strength = signal_of_bar(event.open, event.high, event.low, event.close, self.s, self.b)
        if sig != 0:
            self.signals += 1
        actionable = sig != 0 and (self.keep == "both" or strength == self.keep)
        if not actionable:
            # 無効化: 足の色が建玉と反対のときだけ見る(原典どおり)
            if self.pos != 0 and csign == -self.pos:
                c = event.close
                if (self.pos == 1 and c <= self.lcline) or (self.pos == -1 and c >= self.lcline):
                    self._close(ctx, INVALIDATED)
            return
        if self.pos == sig:
            self.lcline = lc  # 同じ向き: 増し玉はしない。ラインだけ更新
        elif self.pos == -sig:
            self._close(ctx, REVERSED if strength == "strong" else OPPOSITE_WEAK)
            if strength == "strong":  # 強いシグナルはドテン
                self._open(ctx, sig, lc)
        else:
            self._open(ctx, sig, lc)  # 建玉なし: 強弱を問わず新規


class BarCloseMarketFill:
    """Market orders only, filled in full as taker at the close of the last bar
    the venue has handled (the bar that decided the order: the core hands a bar
    to the venue before it delivers it to the strategy, and the order comes
    back at the same instant under ZeroLatency). No bar yet -> rejected."""

    def __init__(self) -> None:
        self.last_close: Optional[float] = None
        self.fills = 0

    def on_market_event(self, event: Event, venue_time_ns: int) -> Sequence[VenueReport]:
        if type(event) is BarEvent:
            self.last_close = float(event.close)
        return ()

    def on_order(self, order: OrderRequest, venue_time_ns: int) -> Sequence[VenueReport]:
        if order.order_type != "market":
            return (Reject(order.client_order_id, "unsupported_order_type"),)
        if self.last_close is None:
            return (Reject(order.client_order_id, "no_bar_yet"),)
        self.fills += 1
        return (Ack(order.client_order_id, f"v-{order.client_order_id}"),
                Fill(order.client_order_id, self.last_close, order.size, "taker"))

    def on_cancel(self, request, venue_time_ns: int) -> Sequence[VenueReport]:
        return (Canceled(request.client_order_id),)


CONFIG_KEYS = ("instrument", "foot_min", "gate", "strength", "fill", "costs")
FILL_NAME = "signal_bar_close"


def parse_config(cfg: Mapping) -> dict:
    if not isinstance(cfg, Mapping) or set(cfg) != set(CONFIG_KEYS):
        raise K1Error(f"config must have exactly the keys {CONFIG_KEYS}, got {sorted(cfg) if isinstance(cfg, Mapping) else cfg!r}")
    if type(cfg["instrument"]) is not str or not cfg["instrument"]:
        raise K1Error("config.instrument must be a non-empty str")
    if type(cfg["foot_min"]) is not int or cfg["foot_min"] <= 0:
        raise K1Error("config.foot_min must be an int > 0")
    g = cfg["gate"]
    if not isinstance(g, Mapping) or set(g) != {"s", "b"}:
        raise K1Error("config.gate must be {s, b}")
    if cfg["strength"] not in STRENGTHS:
        raise K1Error(f"config.strength must be one of {STRENGTHS}")
    if cfg["fill"] != FILL_NAME:
        raise K1Error(f"config.fill must be {FILL_NAME!r} (the only fill rule of K1: the signal bar's close)")
    c = cfg["costs"]
    if not isinstance(c, Mapping) or set(c) != {"maker_fee_rate", "taker_fee_rate", "source"}:
        raise K1Error("config.costs must be exactly {maker_fee_rate, taker_fee_rate, source}")
    for k in ("maker_fee_rate", "taker_fee_rate"):
        if type(c[k]) not in (int, float) or not abs(c[k]) < 1:
            raise K1Error(f"config.costs.{k} must be a finite rate")
    if type(c["source"]) is not str or not c["source"].strip():
        raise K1Error("config.costs.source must say where the costs come from")
    return {"s": str(g["s"]), "b": str(g["b"]), "strength": cfg["strength"],
            "rates": {"maker": float(c["maker_fee_rate"]), "taker": float(c["taker_fee_rate"])}}


class K1Setup:
    """bot.bt.repro.runner setup: build(config, seed) -> Parts. The seed is not
    used (K1 draws nothing); the record carries it anyway."""

    def __init__(self) -> None:
        self.last: Optional[K1WickStrategy] = None

    def identity(self) -> dict:
        src = inspect.getsource(inspect.getmodule(K1Setup))
        return {"name": f"{__name__}:K1Setup", "source_sha256": hashlib.sha256(src.encode()).hexdigest()}

    def build(self, config: Mapping, seed: int) -> Parts:
        p = parse_config(config)
        strat = K1WickStrategy(p["s"], p["b"], p["strength"])
        self.last = strat
        return Parts(strategy=strat, fill_model=BarCloseMarketFill(), latency_model=ZeroLatency(),
                     cost_model=DeclaredFeeCost(p["rates"]), account=NullAccount(),
                     exit_reasons=strat.exit_reasons,  # filled by the strategy as it runs (same dict object)
                     notes={"fill": "market order priced at the close of the bar that decided it (RESULT.md 1.4)",
                            "seed": "unused: K1 draws nothing",
                            "holding_bars": "measured by bar index in the tables script (bars with no trade do not exist)"})

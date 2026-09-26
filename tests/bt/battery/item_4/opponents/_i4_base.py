"""Shared mouth for the item 4 survey adapters (i4_protocol.py is the contract).

A survey adapter subclasses `Base`, sets TOOL and SUPPORTS, and implements
`bars(inp)` (and, when the tool has them, `metrics(inp)` / `split(inp)`).
Every option of a bars config that asks for more than a plain next-bar-open
market-order run is checked against SUPPORTS before the tool is called; an
option the tool has no public way to take raises NotExpressible naming the
option and what was looked for (`MISSING[option]`, written per adapter from the
tool's installed code).

What the scene's strategy is allowed to do on top of a tool's order API (it is
user code in every tool): decide from bars 0..i only, size an entry so that
size x fill price = order_notional using the declared cost rates, filter
entries (entry_mask / entry_sides), count bars (max_hold_bars), compute a
wick level from completed bars and act on a completed bar's close.  It never
computes a fill, a price the tool did not produce, or a PnL.
"""
from __future__ import annotations

import datetime as D
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from i4_protocol import NotExpressible, Refused, non_default  # noqa: E402,F401

NO_REFERENCE = "道具の中に、同じ入力を本体とは別に計算する独立の参照実装の口を探したが無い"
NO_MODELS = "道具に、1 つの戦略の記述から互換の計算(L-1〜L-3)と仕様の計算の 2 つの出力を選ぶ口を探したが無い(模型は 1 つ)"


def adj(c: dict) -> float:
    """R-C1's price adjustment of a taker fill, as a fraction (used only to size an entry: size x fill = notional)."""
    return (c["spread_pct"] / 2 + c["slippage_pct"]) / 100


def to_dt(t_ns: int) -> D.datetime:
    return D.datetime(1970, 1, 1) + D.timedelta(microseconds=t_ns // 1000)


def bars_frame(inp, pd, cols=("open", "high", "low", "close", "volume"), index_name=None):
    df = pd.DataFrame({k: [float(b[k]) for b in inp["bars"]] for k in cols},
                      index=pd.DatetimeIndex([to_dt(b["t_ns"]) for b in inp["bars"]], name=index_name))
    return df


def options_used(cfg: dict) -> list[str]:
    """Option names of a bars config beyond the plain run (keys as in MISSING)."""
    out = []
    for k in non_default(cfg):
        out.append(k.split("=")[0] if "=" in k else k)
    if cfg["allow_short"]:
        out.append("allow_short")
    c = cfg["costs"]
    for k in ("taker_fee_pct", "maker_fee_pct", "slippage_pct", "spread_pct"):
        if c[k]:
            out.append(k)
    return out


def fee_kinds(cfg: dict) -> set[str]:
    """Which fee kinds a bars run can charge: taker (market entries/exits, stops, time and wick exits) and
    maker (resting limit entries/exits, take-profits, maker take-profits)."""
    k = set()
    if cfg["execution"] == "taker" or cfg["stop_loss_pct"] or cfg["max_hold_bars"] is not None \
            or cfg["stop_mode"] == "wick_invalidation":
        k.add("taker")
    if cfg["execution"] == "maker" or cfg["take_profit_pct"] or cfg["exit_execution"] == "maker_tp":
        k.add("maker")
    return k


class Base:
    name = "opp"
    TOOL = "?"
    SUPPORTS: set[str] = set()
    MISSING: dict[str, str] = {}
    PIPELINE = "?"
    METRICS = None   # a reason string when op "metrics" is not expressible
    SPLIT = None     # a reason string when op "split" is not expressible
    DELIVERY = "戦略に届く足を 1 本ずつ記録する口(足ごとに呼ばれる戦略)をこの道具に探したが無い"

    def gate(self, inp):
        cfg = inp["config"]
        bad = [o for o in options_used(cfg) if o not in self.SUPPORTS]
        extra = self.extra_gate(inp)
        if bad or extra:
            why = [f"{o}: {self.MISSING.get(o, 'この道具の公開された口に当たるものを探したが無い')}" for o in bad] + extra
            raise NotExpressible(f"{self.TOOL}: " + " / ".join(why))

    def extra_gate(self, inp) -> list[str]:
        return []

    def run(self, inp):
        op = inp.get("op")
        if op == "bars":
            if inp.get("reference"):
                raise NotExpressible(f"{self.TOOL}: {NO_REFERENCE}")
            if "models" in inp:
                raise NotExpressible(f"{self.TOOL}: {NO_MODELS}")
            self.gate(inp)
            return self.bars(inp)
        if op == "metrics":
            if self.METRICS:
                raise NotExpressible(f"{self.TOOL}: {self.METRICS}")
            return self.metrics(inp)
        if op == "split":
            if "models" in inp:
                raise NotExpressible(f"{self.TOOL}: {NO_MODELS}")
            if self.SPLIT:
                raise NotExpressible(f"{self.TOOL}: {self.SPLIT}")
            return self.split(inp)
        if op == "pipeline":
            raise NotExpressible(f"{self.TOOL}: {self.PIPELINE}")
        if op == "delivery":
            # a tool whose bar path is not expressible at all says why (its gate names the tool's own mouths)
            plain = {"op": "bars", "bars": inp["bars"], "bar_seconds": inp["bar_seconds"], "signals": [],
                     "config": _plain_config(), "want": []}
            self.gate(plain)
            return self.delivery(inp)
        raise NotExpressible(f"{self.TOOL}: op {op!r} に当たる口が無い")

    def delivery(self, inp):
        """op "delivery" (the core granularity): the calls of a strategy that records what the TOOL hands it at each
        call.  An adapter of a tool with a per-bar strategy callback overrides this; DELIVERY is the reason otherwise."""
        raise NotExpressible(f"{self.TOOL}: {self.DELIVERY}")

    def bars(self, inp):  # pragma: no cover - overridden
        raise NotExpressible(f"{self.TOOL}: 足の口が無い")

    def metrics(self, inp):  # pragma: no cover
        raise NotExpressible(f"{self.TOOL}: 指標の口が無い")

    def split(self, inp):  # pragma: no cover
        raise NotExpressible(f"{self.TOOL}: 分け方の口が無い")


def _plain_config() -> dict:
    return {"initial_equity": 6000.0, "order_notional": 3000.0,
            "costs": {"taker_fee_pct": 0.0, "maker_fee_pct": 0.0, "slippage_pct": 0.0, "spread_pct": 0.0},
            "execution": "taker", "maker_timeout_bars": 5, "allow_short": False, "swap_daily_pct": 0.0,
            "stop_loss_pct": None, "take_profit_pct": None, "max_hold_bars": None, "exit_execution": "signal",
            "maker_tp_pct": None, "entry_mask": None, "entry_sides": "both", "stop_mode": "fixed",
            "stop_window_bars": None}


def ns_of(dt) -> int:
    """UTC ns of a naive-UTC datetime / pandas Timestamp handed back by a tool (to_dt's inverse)."""
    import datetime as _D
    if hasattr(dt, "value") and not isinstance(dt, _D.datetime):
        return int(dt.value)
    if hasattr(dt, "to_pydatetime"):
        dt = dt.to_pydatetime()
    if dt.tzinfo is not None:
        dt = dt.astimezone(_D.timezone.utc).replace(tzinfo=None)
    d = dt - _D.datetime(1970, 1, 1)
    return (d.days * 86400 + d.seconds) * 1_000_000_000 + d.microseconds * 1000


def want(inp, obs_full: dict) -> dict:
    w = set(inp.get("want") or [])
    return {k: v for k, v in obs_full.items() if k in w}

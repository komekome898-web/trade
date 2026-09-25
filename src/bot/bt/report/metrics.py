"""Metrics that keep the distribution (item 3, old item 9: 「平均で潰さず分布で出す(1 件ごとの
bp・分位・負の割合)。露出あたり(bp/時)。約定率・取り逃し・逆選択の markout・費用の内訳・
決済理由・ドローダウン」).

Every function takes plain records (mappings) and returns plain values; a
record missing a field it needs, or holding a non-finite number, is refused
(ReportError). Nothing is filled in: a trade's `fees` must be given (0.0 is
a statement), a markout past the end of the mid path is None, not a guess.

Definitions (each written once, here):
  per-trade bp   s * (exit_px - entry_px) / entry_px * 1e4 - fees / (entry_px * qty) * 1e4,
                 s = +1 for a trade entered by a buy (long), -1 by a sell.
  quantiles      linear interpolation between order statistics (Hyndman & Fan
                 type 7 = numpy's "linear").
  neg_frac       share of trades with bp < 0 (0 is not negative).
  trade_hours    sum over trades of (exit_t - entry_t) in hours: the notional
                 time at risk. bp_per_hour = sum of bp / trade_hours.
  union_hours    hours during which at least one trade was open (reported
                 beside it; with overlapping trades the two differ).
  fill_rate      orders with any fill by end_t / orders; missed = orders with
                 no fill by end_t; partial = orders filled in part.
  markout(h)     s * (mid(t + h) - px) in price units (or / px * 1e4 in bp),
                 s = +1 buy, -1 sell; mid(t) = the last mid sample at or
                 before t (no look at later samples); None when t + h is after
                 the last sample or t + h precedes the first.
  costs          maker_fee / taker_fee = px * qty * rate of the fill's
                 liquidity; spread = s * (px - mid at the fill) * qty;
                 funding = sum over funding events of position * mark * rate,
                 position = signed qty of the fills strictly before the event
                 (at the same instant the core applies funding before fills).
  drawdown       max over t of (peak_t - equity_t) and of that / peak_t * 100,
                 peak_t = max equity up to t (the percentage needs peak > 0).
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Optional, Sequence

import numpy as np

from .errors import ReportError

NS_PER_HOUR = 3_600_000_000_000
SIDES = {"buy": 1, "sell": -1}
LIQUIDITY = ("maker", "taker")


def _num(rec: Mapping, key: str, where: str, *, positive: bool = False) -> float:
    if not isinstance(rec, Mapping) or key not in rec:
        raise ReportError(f"{where}: missing field {key!r}")
    v = rec[key]
    if type(v) not in (int, float) or not math.isfinite(float(v)):
        raise ReportError(f"{where}.{key} must be a finite number, got {v!r}")
    if positive and not float(v) > 0:
        raise ReportError(f"{where}.{key} must be > 0, got {v!r}")
    return float(v)


def _int(rec: Mapping, key: str, where: str) -> int:
    if not isinstance(rec, Mapping) or key not in rec or type(rec[key]) is not int:
        raise ReportError(f"{where}.{key} must be an int (ns)")
    return rec[key]


def _side(rec: Mapping, where: str) -> int:
    s = rec.get("side") if isinstance(rec, Mapping) else None
    if s not in SIDES:
        raise ReportError(f"{where}.side must be 'buy' or 'sell', got {s!r}")
    return SIDES[s]


def per_trade_bp(trades: Sequence[Mapping]) -> list[float]:
    out = []
    for i, t in enumerate(trades):
        w = f"trades[{i}]"
        s = _side(t, w)
        e, x = _num(t, "entry_px", w, positive=True), _num(t, "exit_px", w, positive=True)
        q = _num(t, "qty", w, positive=True)
        fee = _num(t, "fees", w)
        out.append(s * (x - e) / e * 1e4 - fee / (e * q) * 1e4)
    return out


def quantiles(values: Sequence[float], probs: Sequence[float]) -> dict[str, float]:
    xs = [float(v) for v in values]
    if not xs:
        raise ReportError("quantiles of no values")
    out = {}
    for p in probs:
        if type(p) not in (int, float) or not 0 <= p <= 1:
            raise ReportError(f"a quantile probability must be in [0, 1], got {p!r}")
        out[str(p)] = float(np.quantile(np.asarray(xs), p, method="linear"))
    return out


def neg_frac(values: Sequence[float]) -> float:
    xs = list(values)
    if not xs:
        raise ReportError("neg_frac of no values")
    return sum(1 for v in xs if v < 0) / len(xs)


def exposure(trades: Sequence[Mapping]) -> dict[str, float]:
    spans = []
    for i, t in enumerate(trades):
        a, b = _int(t, "entry_t_ns", f"trades[{i}]"), _int(t, "exit_t_ns", f"trades[{i}]")
        if b < a:
            raise ReportError(f"trades[{i}] exits before it enters")
        spans.append((a, b))
    trade_ns = sum(b - a for a, b in spans)
    union_ns, cur = 0, None
    for a, b in sorted(spans):
        if cur is None or a > cur[1]:
            if cur:
                union_ns += cur[1] - cur[0]
            cur = [a, b]
        else:
            cur[1] = max(cur[1], b)
    if cur:
        union_ns += cur[1] - cur[0]
    return {"trade_hours": trade_ns / NS_PER_HOUR, "union_hours": union_ns / NS_PER_HOUR}


def bp_per_hour(trades: Sequence[Mapping]) -> Optional[float]:
    h = exposure(trades)["trade_hours"]
    return None if h == 0 else sum(per_trade_bp(trades)) / h


def trade_distribution(trades: Sequence[Mapping], probs: Sequence[float] = (0.05, 0.25, 0.5, 0.75, 0.95)) -> dict:
    bps = per_trade_bp(trades)
    ex = exposure(trades)
    return {"n": len(bps), "per_trade_bp": bps,
            "quantiles": quantiles(bps, probs) if bps else {}, "quantile_method": "linear (Hyndman-Fan 7)",
            "neg_frac": neg_frac(bps) if bps else None, "mean_bp": (sum(bps) / len(bps)) if bps else None,
            "trade_hours": ex["trade_hours"], "union_hours": ex["union_hours"],
            "bp_per_hour": (sum(bps) / ex["trade_hours"]) if ex["trade_hours"] else None}


def fill_metrics(orders: Sequence[Mapping], fills: Sequence[Mapping], end_t_ns: int) -> dict:
    if type(end_t_ns) is not int:
        raise ReportError("end_t_ns must be an int (ns)")
    qty, filled = {}, {}
    for i, o in enumerate(orders):
        oid = o.get("id") if isinstance(o, Mapping) else None
        if type(oid) is not str or not oid or oid in qty:
            raise ReportError(f"orders[{i}].id must be a unique non-empty str")
        qty[oid] = _num(o, "qty", f"orders[{i}]", positive=True)
        filled[oid] = 0.0
    for i, f in enumerate(fills):
        oid = f.get("order_id") if isinstance(f, Mapping) else None
        if oid not in qty:
            raise ReportError(f"fills[{i}] names an unknown order {oid!r}")
        if _int(f, "t_ns", f"fills[{i}]") <= end_t_ns:
            filled[oid] += _num(f, "qty", f"fills[{i}]", positive=True)
    n = len(qty)
    if n == 0:
        raise ReportError("fill metrics of no orders")
    any_fill = [k for k in qty if filled[k] > 0]
    over = [k for k in qty if filled[k] > qty[k] * (1 + 1e-12)]
    if over:
        raise ReportError(f"orders filled beyond their size: {over}")
    return {"orders": n, "fill_rate": len(any_fill) / n, "missed": n - len(any_fill),
            "partial": sum(1 for k in any_fill if filled[k] < qty[k] * (1 - 1e-12)),
            "qty_fill_rate": sum(filled.values()) / sum(qty.values())}


def markout(fills: Sequence[Mapping], mids: Sequence[Sequence], horizons_s: Sequence[int], *, unit: str) -> dict:
    if unit not in ("price", "bp"):
        raise ReportError(f"unit must be 'price' or 'bp', got {unit!r}")
    path = []
    for i, m in enumerate(mids):
        try:
            t, v = m
        except (TypeError, ValueError):
            raise ReportError(f"mids[{i}] must be (t_ns, mid)") from None
        if type(t) is not int or type(v) not in (int, float) or not math.isfinite(float(v)):
            raise ReportError(f"mids[{i}] must be (int ns, finite mid)")
        if path and t < path[-1][0]:
            raise ReportError("mids must be in time order")
        path.append((t, float(v)))
    times = [t for t, _ in path]

    def asof(t: int) -> Optional[float]:
        import bisect
        k = bisect.bisect_right(times, t) - 1
        if k < 0 or t > times[-1]:
            return None
        return path[k][1]

    out: dict[str, list] = {}
    for h in horizons_s:
        if type(h) is not int or h < 0:
            raise ReportError(f"a horizon must be an int of seconds >= 0, got {h!r}")
        row = []
        for i, f in enumerate(fills):
            s = _side(f, f"fills[{i}]")
            px = _num(f, "px", f"fills[{i}]", positive=True)
            m = asof(_int(f, "t_ns", f"fills[{i}]") + h * 1_000_000_000) if path else None
            row.append(None if m is None else (s * (m - px) if unit == "price" else s * (m - px) / px * 1e4) + 0.0)
        out[str(h)] = row
    return out


def cost_breakdown(fills: Sequence[Mapping], funding: Sequence[Mapping], rates: Mapping) -> dict:
    r = {k: _num(rates, k, "rates") for k in ("maker_fee_rate", "taker_fee_rate")}
    fee = {"maker": 0.0, "taker": 0.0}
    spread: Optional[float] = 0.0
    for i, f in enumerate(fills):
        w = f"fills[{i}]"
        s = _side(f, w)
        liq = f.get("liquidity")
        if liq not in LIQUIDITY:
            raise ReportError(f"{w}.liquidity must be 'maker' or 'taker', got {liq!r}")
        px, q = _num(f, "px", w, positive=True), _num(f, "qty", w, positive=True)
        fee[liq] += px * q * r[f"{liq}_fee_rate"]
        if "mid" not in f or f["mid"] is None:
            spread = None  # a fill without its mid: the spread cost cannot be measured
        elif spread is not None:
            spread += s * (px - _num(f, "mid", w, positive=True)) * q
    fund = 0.0
    for j, ev in enumerate(funding):
        w = f"funding[{j}]"
        t = _int(ev, "t_ns", w)
        pos = sum(_side(f, "fill") * float(f["qty"]) for f in fills if _int(f, "t_ns", "fill") < t)
        fund += pos * _num(ev, "mark", w, positive=True) * _num(ev, "rate", w)
    return {"maker_fee": fee["maker"], "taker_fee": fee["taker"], "spread": spread, "funding": fund}


def exit_reasons(trades: Sequence[Mapping]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i, t in enumerate(trades):
        reason = t.get("reason") if isinstance(t, Mapping) else None
        if type(reason) is not str or not reason:
            raise ReportError(f"trades[{i}].reason must be a non-empty str")
        pnl = _num(t, "pnl", f"trades[{i}]")
        d = out.setdefault(reason, {"n": 0, "pnl": 0.0})
        d["n"] += 1
        d["pnl"] += pnl
    return out


def drawdown(equity: Sequence[float], t_ns: Optional[Sequence[int]] = None) -> dict:
    eq = [float(v) for v in equity]
    if not eq or not all(math.isfinite(v) for v in eq):
        raise ReportError("equity must be a non-empty sequence of finite numbers")
    if t_ns is not None and len(list(t_ns)) != len(eq):
        raise ReportError("t_ns and equity differ in length")
    peak, worst_abs, worst_pct, at = -math.inf, 0.0, 0.0, None
    pct_ok = True
    series = []
    for i, v in enumerate(eq):
        peak = max(peak, v)
        dd = peak - v
        series.append(dd)
        if dd > worst_abs:
            worst_abs, at = dd, i
        if peak > 0:
            worst_pct = max(worst_pct, dd / peak * 100)
        elif dd > 0:
            pct_ok = False
    return {"max_dd_abs": worst_abs, "max_dd_pct": worst_pct if pct_ok else None,
            "max_dd_at": (list(t_ns)[at] if (t_ns is not None and at is not None) else at), "dd_series": series}

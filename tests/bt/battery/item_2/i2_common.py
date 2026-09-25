"""Item 2 battery: small helpers shared by the survey-side adapters.

They only reshape the scene input (no answer is computed here).  What each
adapter cannot hand to its tool is refused with NotExpressible through
`gate`, naming the missing argument, so every 「結果なし」 carries what was
tried.
"""
from __future__ import annotations

from i2_protocol import NotExpressible

ORDER_FEATURES = ("market", "limit", "stop", "IOC", "FOK", "post_only", "reduce_only", "oco", "cancel", "amend", "kill")


def places(inp):
    return [a for a in inp["actions"] if a["op"] == "place"]


def features(inp) -> set[str]:
    """The order-level features a scene's actions use."""
    f = set()
    for a in inp["actions"]:
        if a["op"] == "place":
            f.add(a["type"])
            if a["tif"] != "GTC":
                f.add(a["tif"])
            if a["post_only"]:
                f.add("post_only")
            if a["reduce_only"]:
                f.add("reduce_only")
            if a["oco"]:
                f.add("oco")
        else:
            f.add(a["op"])
    return f


def event_types(inp) -> set[str]:
    return {e["type"] for e in inp["market"]}


def latency_nonzero(inp) -> dict:
    lat = inp.get("latency") or {}
    return {k: v for k, v in lat.items() if not (v.get("kind") == "constant" and v.get("ns", 0) == 0)}


def gate(inp, *, tool: str, orders=(), events=("book", "trade"), fill_models=None, latency=(),
         inject=False, costs=("maker_rate", "taker_rate"), account=("cash",), fx=False):
    """Raise NotExpressible for the first thing in `inp` this tool has no public way to take.

    orders: order-level features the tool's API has; events: market event types it can be fed;
    fill_models: callable(fill_model) -> str|None (None = expressible) or None = only fill_model None;
    latency: latency kinds (feed/order/cancel/notice) it can set; inject: fault injection;
    costs: cost keys it can take when non-zero; account: account keys it can take."""
    for f in sorted(features(inp)):
        if f not in orders:
            raise NotExpressible(f"{tool}: 公開の口に {f} が無い")
    for t in sorted(event_types(inp)):
        if t not in events:
            raise NotExpressible(f"{tool}: 事象 {t} を渡す口が無い")
    fm = inp.get("fill_model")
    if fm:
        why = "約定の模型を選ぶ口が無い" if fill_models is None else fill_models(fm)
        if why:
            raise NotExpressible(f"{tool}: {why}")
    for k in sorted(latency_nonzero(inp)):
        if k not in latency:
            raise NotExpressible(f"{tool}: 遅延({k})を渡す口が無い")
        if inp["latency"][k].get("kind") != "constant" and f"{k}:{inp['latency'][k]['kind']}" not in latency:
            raise NotExpressible(f"{tool}: 遅延({k})の分布 {inp['latency'][k]['kind']} を渡す口が無い")
    if inp.get("inject") and not inject:
        raise NotExpressible(f"{tool}: 拒否・時間切れ・状態不明を注入する口が無い")
    c = inp.get("costs") or {}
    for k, v in c.items():
        if k in ("source", "mid"):
            continue
        if k in ("maker_rate", "taker_rate") and v == 0.0:
            continue
        if k not in costs:
            raise NotExpressible(f"{tool}: 費用 {k} を渡す口が無い")
    acc = inp.get("account") or {}
    for k in acc:
        if k in ("currency", "source", "liquidation_price"):
            continue
        if k == "leverage" and acc[k] == 1.0:
            continue
        if k not in account:
            raise NotExpressible(f"{tool}: 口座の {k} を渡す口が無い")
    if inp["product"].get("quote_ccy", "JPY") != "JPY" and not fx:
        raise NotExpressible(f"{tool}: 円以外で値が付く商品を円に直す口が無い")


def timeline(inp):
    """Market events and actions merged by time; at the same time market events come first,
    each group in list order."""
    tl = [(e["t"], 0, i, "m", e) for i, e in enumerate(inp["market"])]
    tl += [(a["t"], 1, i, "a", a) for i, a in enumerate(inp["actions"])]
    tl.sort(key=lambda x: (x[0], x[1], x[2]))
    return [(t, k, x) for t, _, _, k, x in tl]


def trades(inp):
    return [e for e in inp["market"] if e["type"] == "trade"]


def status_from(filled: float, qty: float, active: bool, canceled: bool = False, rejected: bool = False) -> str:
    if rejected:
        return "rejected"
    if abs(filled - qty) <= 1e-12:
        return "filled"
    if active:
        return "open"
    return "canceled"


def issue_schedule(bars, actions: list[dict]) -> dict[int, list[dict]]:
    """For a bar tool: the index of the bar in whose handler each action is issued.  `bars` are bar_rows dicts
    (t = end, span_ns) or plain end times (span 0).  An action at time a is issued in the handler of the first bar k
    after which every later bar starts after a (bar k+1's start = its end - span > a; same-time market events come
    before actions), so no price from before the action can fill it; the last bar when none.  For bars of single
    prints (span 0) this is the last print at or before a; for bars with a span it is the first bar that ends after a.
    Only times are compared -- no price is read."""
    rows = [b if isinstance(b, dict) else {"t": b, "span_ns": 0} for b in bars]
    out: dict[int, list[dict]] = {}
    for a in sorted(actions, key=lambda x: x["t"]):
        k = len(rows) - 1
        for i in range(len(rows)):
            nxt = rows[i + 1] if i + 1 < len(rows) else None
            if nxt is None or nxt["t"] - nxt.get("span_ns", 0) > a["t"]:
                k = i
                break
        out.setdefault(k, []).append(a)
    return out


def bar_rows(inp):
    """Bars for a bar-driven tool, from the scene itself (no answer is computed):
    - the scene's own bar events when it has any (t = the bar's end, span_ns);
    - when the scene's fill model declares bars (tier 2 with bar_ns): the trade prints grouped into bars of
      bar_ns aligned to the epoch (t = the bar's end; open / high / low / close / volume of its prints);
    - otherwise one bar per trade print (open = high = low = close = the print's price, volume = its size,
      t = the print's time, span_ns = 0: the bar is the print).
    Book snapshots have no bar form; a scene without prints or bars gives no bars."""
    bars = [dict(t=e["t"], span_ns=e["span_ns"], o=e["o"], h=e["h"], l=e["l"], c=e["c"], v=e["v"])
            for e in inp["market"] if e["type"] == "bar"]
    if bars:
        return bars, "bar"
    fm = inp.get("fill_model") or {}
    if fm.get("tier") == 2 and fm.get("bar_ns"):
        bn = int(fm["bar_ns"])
        groups = {}
        for e in inp["market"]:
            if e["type"] == "trade":
                groups.setdefault(e["t"] // bn, []).append(e)
        return [dict(t=(k + 1) * bn, span_ns=bn, o=g[0]["px"], h=max(x["px"] for x in g), l=min(x["px"] for x in g),
                     c=g[-1]["px"], v=sum(x["qty"] for x in g)) for k, g in sorted(groups.items())], "bar"
    return [dict(t=e["t"], span_ns=0, o=e["px"], h=e["px"], l=e["px"], c=e["px"], v=e["qty"])
            for e in inp["market"] if e["type"] == "trade"], "trade"


def single_fee_rate(inp, tool):
    """For a tool with ONE fee rate: taker_rate when every order is a market / stop order, maker_rate when every
    order is a plain limit order, the common rate when both rates are equal; otherwise NotExpressible."""
    c = inp.get("costs") or {}
    mk, tk = float(c.get("maker_rate", 0.0)), float(c.get("taker_rate", 0.0))
    if mk == tk:
        return tk
    types = {a["type"] for a in places(inp)}
    if types <= {"market", "stop"}:
        return tk
    if types == {"limit"}:
        return mk
    raise NotExpressible(f"{tool}: 手数料の率は 1 つで、maker と taker で違う率を同じ実行の中で渡せない")


def bar_fill_models(fm, extra=None):
    """fill_models gate for a tool that fills on bars: tier 2 (bars) is the tool's own model; `extra` may accept more."""
    if fm.get("tier") == 2 and not fm.get("impact") and "range" not in fm:
        return None
    if extra is not None:
        return extra(fm)
    return "約定の模型は足で埋まる型(段 2)だけで、ほかの段・列・市場影響の関数・楽観と悲観の両方を回す口が無い"

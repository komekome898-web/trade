"""Item 4 battery (統合と答え合わせ): the scenes.

Every scene is a dict:
    id         -- unique id, prefixed by its viewpoint (i4-1- ... i4-18-)
    viewpoint  -- I4-1 .. I4-18 (REQUIREMENTS.md §2)
    kind       -- 値 (a value is right) | 能力 (a capability, judged by the result it must give)
    what       -- 何を測るか
    how        -- 正解の出し方 (how the expected answer was fixed, without looking at any engine)
    input      -- what the adapter receives (plus "root" for file scenes, added by the runner)
    cases      -- (instead of input) a list of inputs, each run separately (I4-2 grids)
    expect     -- the expected answer (never given to the adapter); for a grid, one entry per case:
                  an expected answer, {"invariants_only": True} (judged by the stated invariants alone), or
                  {"prefix_of": k, "upto": n} (the case is case k cut to its first n bars; judged against case k)
    judge      -- which observation keys are judged, and how (i4_judge.py)
    variant    -- (optional) a second input the target must REFUSE
    more_controls -- (optional, with variant) further inputs with their expected answers that must pass before the
                  refusal of the variant counts: together with `input` they use every feature the variant uses

All inputs are synthetic.  The expected answers are written by hand from the
stated bar-model rules (DEFINITIONS.md「足の模型の仕様」R-*): for each scene the
bar and the reference price of every fill are chosen by hand (the comment next
to the scene says which rule puts it there), and the helpers below only do the
bookkeeping arithmetic those rules state (size = notional / price, fee =
notional x pct, PnL, carry, equity, the metric formulas).  Every hand-placed
exit is checked by the scene-keeper's tests against `exit_events` / `winner` /
`exit_fill` (the stated order R-O1 / L-5 applied to the scene's own input).
The I4-2 exact grid's fills come from `taker_rule` (R-T1..R-T4 written as a
function); the other I4-2 grids have no expected fills and are judged by the
stated invariants (i4_judge.invariants) and by the prefix rule.  Only the
standard library is used, so this module also loads under every survey tool's
interpreter.
"""
from __future__ import annotations

import calendar
import hashlib
import math
import random
import statistics
from fractions import Fraction

NS = 1_000_000_000


def ns(y, mo, d, h=0, mi=0, s=0, frac_ns=0, offset_h=0):
    """UTC epoch nanoseconds of a wall-clock time written at UTC+offset_h."""
    return (calendar.timegm((y, mo, d, h, mi, s, 0, 0, 0)) - offset_h * 3600) * NS + frac_ns


T0 = ns(2026, 1, 5)  # 2026-01-05T00:00:00Z, a Monday

ZERO = {"taker_fee_pct": 0.0, "maker_fee_pct": 0.0, "slippage_pct": 0.0, "spread_pct": 0.0}
METRIC_KEYS = ("total_pnl_jpy", "num_trades", "win_rate_pct", "profit_factor", "sharpe_ratio", "max_drawdown_pct",
               "max_consecutive_losses", "avg_win_jpy", "avg_loss_jpy", "risk_reward_ratio",
               "expectancy_per_trade_jpy", "total_fees_jpy")


# --------------------------------------------------------------------------- input builders
def mk_bars(rows, bar_seconds=60, t0=T0):
    """rows: (open, high, low, close); volume 1.0; bar i starts at t0 + i * bar_seconds."""
    return [{"t_ns": t0 + i * bar_seconds * NS, "open": float(o), "high": float(h), "low": float(lo),
             "close": float(c), "volume": 1.0} for i, (o, h, lo, c) in enumerate(rows)]


def cfg(**over):
    """A full bar-model config: every key explicit (the scene never relies on a target's default)."""
    c = {"initial_equity": 6000.0, "order_notional": 3000.0, "costs": dict(ZERO), "execution": "taker",
         "maker_timeout_bars": 5, "allow_short": False, "swap_daily_pct": 0.0, "stop_loss_pct": None,
         "take_profit_pct": None, "max_hold_bars": None, "exit_execution": "signal", "maker_tp_pct": None,
         "entry_mask": None, "entry_sides": "both", "stop_mode": "fixed", "stop_window_bars": None}
    for k, v in over.items():
        assert k in c, k
        c[k] = dict(v) if isinstance(v, dict) else v
    return c


def bars_input(bars, signals, config, *, bar_seconds=60, want=("fills", "pnls"), model="spec"):
    inp = {"op": "bars", "bars": bars, "bar_seconds": bar_seconds,
           "signals": [{"bar": b, "signal": s} for b, s in signals], "config": config, "want": list(want)}
    if isinstance(model, (list, tuple)):
        inp["models"] = list(model)
    else:
        inp["model"] = model
    return inp


# --------------------------------------------------------------------------- the stated arithmetic
def buy_px(ref, c):
    """R-C1: a taker buy pays ref x (1 + (spread/2 + slippage)/100)."""
    return ref * (1 + (c["spread_pct"] / 2 + c["slippage_pct"]) / 100)


def sell_px(ref, c):
    """R-C1: a taker sell gets ref x (1 - (spread/2 + slippage)/100)."""
    return ref * (1 - (c["spread_pct"] / 2 + c["slippage_pct"]) / 100)


def trade(ob, d, ep, efp, cb=None, xp=None, xfp=None):
    """A hand-placed round trip: open bar, direction (+1 long / -1 short), entry price, entry fee pct,
    close bar, exit price, exit fee pct (cb=None: still open at the end)."""
    return {"ob": ob, "d": d, "ep": ep, "efp": efp, "cb": cb, "xp": xp, "xfp": xfp}


def book(bars, trades, config, bar_seconds):
    """Bookkeeping of hand-placed trades by the stated rules R-A1..R-A4 and R-S1.

    size = notional / entry price; entry fee = size x entry x pct / 100; carry at every bar j with
    open_bar < j <= close_bar (or the last bar) = |size| x close[j-1] x swap_daily_pct/100 x bar_seconds/86400;
    pnl = (exit - entry) x size x d - exit fee - entry fee - carry; equity at bar i = initial + realized pnl of
    trades closed at or before i + for the open trade (close[i] - entry) x size x d - entry fee - carry so far.
    """
    closes = [b["close"] for b in bars]
    per_bar = config["swap_daily_pct"] / 100 * (bar_seconds / 86400.0)
    notional, initial = config["order_notional"], config["initial_equity"]
    fills, pnls, fees = [], [], 0.0
    rows = []
    for t in trades:
        size = notional / t["ep"]
        efee = size * t["ep"] * t["efp"] / 100
        last = t["cb"] if t["cb"] is not None else len(bars) - 1
        carry = {j: size * closes[j - 1] * per_bar for j in range(t["ob"] + 1, last + 1)} if per_bar > 0 else {}
        side = "LONG" if t["d"] > 0 else "SHORT"
        fills.append({"bar": t["ob"], "side": f"OPEN_{side}", "price": t["ep"], "size": size, "_k": (t["ob"], 1)})
        pnl = None
        fees += efee + sum(carry.values())
        if t["cb"] is not None:
            xfee = size * t["xp"] * t["xfp"] / 100
            fees += xfee
            pnl = (t["xp"] - t["ep"]) * size * t["d"] - xfee - efee - sum(carry.values())
            fills.append({"bar": t["cb"], "side": f"CLOSE_{side}", "price": t["xp"], "size": size, "_k": (t["cb"], 0)})
            pnls.append((t["cb"], pnl))
        rows.append((t, size, efee, carry, pnl))
    fills.sort(key=lambda f: f.pop("_k"))
    equity = []
    for i, c in enumerate(closes):
        e = initial
        for t, size, efee, carry, pnl in rows:
            if t["cb"] is not None and t["cb"] <= i:
                e += pnl
            elif t["ob"] <= i:
                e += (c - t["ep"]) * size * t["d"] - efee - sum(v for j, v in carry.items() if j <= i)
        equity.append(e)
    return {"fills": fills, "pnls": [p for _, p in sorted(pnls, key=lambda x: x[0])], "equity": equity, "fees": fees}


def metrics_of(pnls, equity, fees, periods_per_year):
    """The metric formulas M-1..M-12 (DEFINITIONS.md「指標の式」)."""
    n = len(pnls)
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gp, gl = sum(wins), -sum(losses)
    pf = gp / gl if gl > 0 else (math.inf if gp > 0 else 0.0)
    rets = [equity[i] / equity[i - 1] - 1 for i in range(1, len(equity))]
    sharpe = 0.0
    if len(rets) > 1 and statistics.stdev(rets) > 0:
        sharpe = statistics.mean(rets) / statistics.stdev(rets) * math.sqrt(periods_per_year)
    peak, dd = -math.inf, 0.0
    for e in equity:
        peak = max(peak, e)
        dd = max(dd, (peak - e) / peak * 100)
    mc = c = 0
    for p in pnls:
        c = c + 1 if p < 0 else 0
        mc = max(mc, c)
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    return {"total_pnl_jpy": float(sum(pnls)), "num_trades": n, "win_rate_pct": len(wins) / n * 100 if n else 0.0,
            "profit_factor": pf, "sharpe_ratio": sharpe, "max_drawdown_pct": dd, "max_consecutive_losses": mc,
            "avg_win_jpy": aw, "avg_loss_jpy": al, "risk_reward_ratio": aw / abs(al) if al != 0 else 0.0,
            "expectancy_per_trade_jpy": sum(pnls) / n if n else 0.0, "total_fees_jpy": fees}


def ppy(bar_seconds):
    """M-5: periods per year of the bar frequency."""
    return 365 * 86400 / bar_seconds


def full_expect(bars, trades, config, bar_seconds, want, missed=0, periods=None):
    b = book(bars, trades, config, bar_seconds)
    out = {}
    if "fills" in want:
        out["fills"] = b["fills"]
    if "pnls" in want:
        out["pnls"] = b["pnls"]
    if "equity" in want:
        out["equity"] = b["equity"]
    if "metrics" in want:
        out["metrics"] = metrics_of(b["pnls"], b["equity"], b["fees"], periods or ppy(bar_seconds))
    if "missed_fills" in want:
        out["missed_fills"] = missed
    return out


def J(*keys, fill_fields=("bar", "side", "price", "size")):
    """Judge spec: which keys of a bars observation are judged."""
    return {k: (list(fill_fields) if k == "fills" else True) for k in keys}


# --------------------------------------------------------------------------- the stated order within one bar (R-O1 / L-5)
# The exit events that can close an open position on bar j (names used by the order lists and the tests):
#   wick      R-W3  the structural stop: bar j-1's close beyond the frozen level -> bar j's OPEN (taker)
#   time      R-H1  j = entry bar + N -> bar j's OPEN (taker)
#   signal    R-T1  a closing signal (opposite or CLOSE) at bar j-1, taker execution -> bar j's OPEN (taker)
#   stop      R-P3  bar j's range reaches the % stop level -> min(open, level) (long) / max (short), taker.  The
#                   same event on the time-exit bar j = entry bar + N (the range comes after the open, R-O1 / R-H3:
#                   the time exit at the open closes first in the spec order; the legacy order L-5 takes the stop first)
#   tp        R-P4  bar j's range strictly through the % take-profit level -> the level, maker rate
#   mtp       R-X1  bar j's range strictly through the maker take-profit level -> the level, maker rate
#   limit     R-M1  maker execution: the resting closing limit (a closing signal at p, entry bar <= p < j,
#                   j - p <= timeout; the latest such signal) strictly traded through -> the limit, maker rate
EXIT_EVENTS = ("wick", "time", "signal", "stop", "tp", "mtp", "limit")
ORDER_SPEC = ["wick", "time", "signal", "stop", "tp", "mtp", "limit"]     # R-O1: the open events, then the range
ORDER_LEGACY = ["wick", "stop", "tp", "mtp", "time", "signal", "limit"]   # L-1 + L-5
# pairs that never happen on one bar (the options exclude each other) and the pairs whose two answers are the same
# fill (both at the open, taker; no re-entry on the bar, R-T3): not pinned by any scene
NEVER_TOGETHER = {frozenset(p) for p in [("signal", "limit"), ("wick", "stop")]}
SAME_FILL = {frozenset(("wick", "time")), frozenset(("wick", "signal")), frozenset(("time", "signal"))}  # all three: the open, taker


def dec(x) -> Fraction:
    """The written decimal value of a number (R-X1: levels are compared as written)."""
    return Fraction(repr(float(x))) if not isinstance(x, int) or isinstance(x, bool) else Fraction(x)


def _levels(cfg, ep, d):
    E = dec(ep)
    out = {}
    if cfg["stop_loss_pct"]:
        out["stop"] = E * (1 - d * dec(cfg["stop_loss_pct"]) / 100)
    if cfg["take_profit_pct"]:
        out["tp"] = E * (1 + d * dec(cfg["take_profit_pct"]) / 100)
    if cfg["exit_execution"] == "maker_tp" and cfg["maker_tp_pct"]:
        out["mtp"] = E * (1 + d * dec(cfg["maker_tp_pct"]) / 100)
    return out


def _wick_level(bars, cfg, ob, d):
    if cfg["stop_mode"] != "wick_invalidation":
        return None
    win = bars[max(0, ob - cfg["stop_window_bars"]):ob]
    if not win:
        return None
    return min(dec(b["low"]) for b in win) if d > 0 else max(dec(b["high"]) for b in win)


def _closing_limit(inp, ob, d, j, model="spec"):
    """R-M1/R-M2: the resting closing limit at bar j (its price), or None.  A later closing signal while the limit
    rests does not re-place it in the spec (U2: the same as R-M6); the existing computation re-places it (legacy L-7)."""
    cfg, bars = inp["config"], inp["bars"]
    if cfg["execution"] != "maker":
        return None
    sig = {s["bar"]: s["signal"] for s in inp["signals"]}
    closer = "SELL" if d > 0 else "BUY"
    T = cfg["maker_timeout_bars"]
    pend = None
    for p in range(ob, j):
        if sig.get(p) not in (closer, "CLOSE"):
            continue
        if model == "legacy" or pend is None or p >= pend + T:   # spec: a resting limit is kept until it expires
            pend = p
    if pend is None or j - pend > T:
        return None
    return dec(bars[pend]["close"])


def exit_events(inp, ob, d, ep, j, model="spec") -> set:
    """The exit events of a position opened at bar ob (direction d, entry price ep) that can happen on bar j > ob,
    read from the scene's own input by the stated rules (not from any engine)."""
    bars, cfg = inp["bars"], inp["config"]
    sig = {s["bar"]: s["signal"] for s in inp["signals"]}
    b = bars[j]
    lo, hi = dec(b["low"]), dec(b["high"])
    ev = set()
    N = cfg["max_hold_bars"]
    time_bar = N is not None and j - ob == N
    if time_bar:
        ev.add("time")
    wl = _wick_level(bars, cfg, ob, d)
    if wl is not None and j - 1 >= ob:
        c = dec(bars[j - 1]["close"])
        if (c < wl) if d > 0 else (c > wl):
            ev.add("wick")
    if cfg["execution"] == "taker" and j - 1 >= ob and sig.get(j - 1) in ("SELL" if d > 0 else "BUY", "CLOSE"):
        ev.add("signal")
    lv = _levels(cfg, ep, d)
    if "stop" in lv and ((lo <= lv["stop"]) if d > 0 else (hi >= lv["stop"])):
        ev.add("stop")
    for k in ("tp", "mtp"):
        if k in lv and ((hi > lv[k]) if d > 0 else (lo < lv[k])):
            ev.add(k)
    lim = _closing_limit(inp, ob, d, j, model)
    if lim is not None and ((hi > lim) if d > 0 else (lo < lim)):
        ev.add("limit")
    return ev


def winner(events, order) -> str:
    """The first of `events` in `order` (the one that closes the position)."""
    return next(e for e in order if e in events)


def exit_fill(event, inp, ob, d, ep, j, model="spec"):
    """(price, fee rate kind) of the exit `event` on bar j by the stated rules."""
    bars, cfg = inp["bars"], inp["config"]
    c = cfg["costs"]
    o = bars[j]["open"]
    if event in ("wick", "time", "signal"):
        return (sell_px(o, c) if d > 0 else buy_px(o, c)), "taker"
    lv = _levels(cfg, ep, d)
    if event == "stop":
        trig = min(dec(o), lv["stop"]) if d > 0 else max(dec(o), lv["stop"])
        return (sell_px(float(trig), c) if d > 0 else buy_px(float(trig), c)), "taker"
    if event in ("tp", "mtp"):
        return float(lv[event]), "maker"
    return float(_closing_limit(inp, ob, d, j, model)), "maker"


def round_trips(fills):
    """[(open fill, close fill or None)] of a fills list (alternating open / close)."""
    out = []
    for k in range(0, len(fills), 2):
        out.append((fills[k], fills[k + 1] if k + 1 < len(fills) else None))
    return out


def model_expectations(scene):
    """[(input, expected dict, order)] of a bars scene: every expected answer with the rule order it follows."""
    out = []
    if scene.get("input", {}).get("op") == "bars":
        inp, exp = scene["input"], scene["expect"]
        if "models" in inp:
            for m in inp["models"]:
                out.append((inp, exp[m], ORDER_LEGACY if m == "legacy" else ORDER_SPEC))
        elif inp.get("reference"):
            for k in ("engine", "reference"):
                out.append((inp, exp[k], ORDER_SPEC))
        else:
            out.append((inp, exp, ORDER_SPEC if inp.get("model", "spec") == "spec" else ORDER_LEGACY))
        for mc in scene.get("more_controls", []):
            if mc["input"].get("op") == "bars":
                out.append((mc["input"], mc["expect"], ORDER_SPEC))
    for inp, exp in zip(scene.get("cases", []), scene.get("expect", []) if "cases" in scene else []):
        if "fills" in exp:
            out.append((inp, exp, ORDER_SPEC))
    return out


def order_findings(scenes, order_override=None):
    """Every hand-placed round trip checked against the stated order: a list of (scene id, what is wrong), and the
    pinned pairs {(order name, winner, loser)} (order name "spec" / "legacy")."""
    wrong, pinned = [], set()
    for s in scenes:
        for inp, exp, order in model_expectations(s):
            name = "legacy" if order is ORDER_LEGACY else "spec"
            if order_override is not None:
                order = order_override.get(name, order)
            fills = exp.get("fills")
            if fills is None:
                continue
            n = len(inp["bars"])
            for o, x in round_trips(fills):
                d = 1 if o["side"] == "OPEN_LONG" else -1
                end = x["bar"] if x else n
                for j in range(o["bar"] + 1, end):
                    ev = exit_events(inp, o["bar"], d, o["price"], j, name)
                    if ev:
                        wrong.append((s["id"], f"足 {j} で出口 {sorted(ev)} が起きうるのに、手の正解は建玉を閉じていない"))
                if x is None:
                    continue
                ev = exit_events(inp, o["bar"], d, o["price"], x["bar"], name)
                if not ev:
                    wrong.append((s["id"], f"足 {x['bar']} の決済に当たる出口が規則から出ない"))
                    continue
                w = winner(ev, order)
                px, _ = exit_fill(w, inp, o["bar"], d, o["price"], x["bar"], name)
                if abs(px - x["price"]) > 1e-9 * max(1.0, abs(px)):
                    wrong.append((s["id"], f"足 {x['bar']} の決済の値 {x['price']} が、出口 {sorted(ev)} の {name} の順で勝つ "
                                           f"{w} の値 {px} と違う"))
                for e in ev - {w}:
                    pinned.add((name, w, e))
    return wrong, pinned


def order_pairs():
    """The pairs of exit events the scene set must pin (they can happen together and give different fills)."""
    out = []
    for i, a in enumerate(EXIT_EVENTS):
        for b in EXIT_EVENTS[i + 1:]:
            if frozenset((a, b)) not in NEVER_TOGETHER | SAME_FILL:
                out.append((a, b))
    return out


def first_of(pair, order):
    a, b = pair
    return (a, b) if order.index(a) < order.index(b) else (b, a)


# --------------------------------------------------------------------------- what a scene asks for besides its viewpoint
def fee_kinds(cfg) -> set:
    """The fee kinds a bars run can charge (R-A2): taker (market entries / exits, stops, time and wick exits),
    maker (limit entries / exits, take-profits, maker take-profits)."""
    k = set()
    if cfg["execution"] == "taker" or cfg["stop_loss_pct"] or cfg["max_hold_bars"] is not None \
            or cfg["stop_mode"] == "wick_invalidation":
        k.add("taker")
    if cfg["execution"] == "maker" or cfg["take_profit_pct"] or cfg["exit_execution"] == "maker_tp":
        k.add("maker")
    return k


def _judged_keys(scene):
    j = scene["judge"]
    keys = set()
    for k, v in j.items():
        if k in ("engine", "reference", "legacy", "spec"):
            keys |= set(v)
        else:
            keys.add(k)
    return keys


def barriers(scene) -> list:
    """What a bars scene asks for that is not its viewpoint and that a bar tool may lack (i4-r1-05):
    a signal at bar 0, a non-zero cost, two different fee rates charged, a cost the judged keys cannot see."""
    inps = scene["cases"] if "cases" in scene else [scene["input"]]
    out = []
    keys = _judged_keys(scene)
    money_seen = bool(keys & {"pnls", "equity", "metrics", "invariants"})
    for inp in inps:
        if inp.get("op") != "bars":
            continue
        c, cfg = inp["config"]["costs"], inp["config"]
        kinds = fee_kinds(cfg)
        if any(s["bar"] == 0 for s in inp["signals"]):
            out.append("足 0 の合図")
        if any(c[k] for k in c):
            out.append("0 でない費用")
        if kinds == {"taker", "maker"} and c["taker_fee_pct"] != c["maker_fee_pct"]:
            out.append("違う 2 つの手数料の率")
        for kind in ("taker", "maker"):
            if c[f"{kind}_fee_pct"] and (kind not in kinds or not money_seen):
                out.append(f"判定から見えない {kind} の手数料")
        if (c["spread_pct"] or c["slippage_pct"]) and "taker" not in kinds:
            out.append("判定から見えないスプレッド・滑り")
        if not any(c.values()) and not cfg["swap_daily_pct"] and keys & {"pnls", "equity"} and "metrics" not in keys:
            out.append("費用 0・持ち越し 0 の場面で損益・資産も判定する(約定から決まる)")
    return sorted(set(out))


# --------------------------------------------------------------------------- the features a variant needs a control for
def features(inp) -> set:
    """What an input uses (i4-r1-09): the bar model's non-default options, the pipeline's strategy kind, purpose and
    data origins, the split."""
    op = inp.get("op")
    if op == "bars":
        base = cfg()
        return {k for k, v in inp["config"].items() if k not in ("initial_equity", "order_notional", "costs",
                                                                  "maker_timeout_bars") and v != base[k]}
    if op == "pipeline":
        f = {"strategy:" + inp["strategy"]["kind"], "purpose:" + inp["purpose"]}
        f |= {"origin:" + d["origin"] for d in inp["datasets"]}
        return f
    return {op}


def control_features(scene) -> set:
    f = set(features(scene["input"]))
    for mc in scene.get("more_controls", []):
        f |= features(mc["input"])
    return f


# --------------------------------------------------------------------------- granularity (I4-3)
GRANULARITY = {"core": "核(戦略に届く足と時刻)", "reference": "参照実装", "whole": "新エンジン全体"}


def granularity_of(scene) -> str:
    inp = scene.get("input") or {}
    if inp.get("op") == "delivery":
        return "core"
    if inp.get("reference"):
        return "reference"
    return "whole"


SCENES: list[dict] = []


def add(**s):
    assert s["kind"] in ("値", "能力"), s["kind"]
    SCENES.append(s)


# --------------------------------------------------------------------------- shared bar sets
# B: a gentle up-then-down path, 60 s bars
# (the opens of bars 2, 3, 4 are 100, 120, 125 so that an entry of 3000 there is a whole number of units: 30, 25, 24)
B = mk_bars([(100, 101, 99, 100), (100, 102, 99, 101), (100, 104, 99, 103), (120, 122, 118, 121),
             (125, 127, 123, 126), (106, 108, 104, 105), (105, 106, 102, 103), (103, 104, 100, 101),
             (101, 103, 100, 102), (102, 103, 101, 102)])
C_TAK = {"taker_fee_pct": 0.1, "maker_fee_pct": 0.0, "slippage_pct": 0.02, "spread_pct": 0.04}  # taker only: no maker fee (i4-r1-05)

# E: the end-to-end taker path (I4-1 / I4-3)
E = mk_bars([(1000, 1005, 995, 1000), (1000, 1010, 998, 1008), (1010, 1020, 1005, 1015), (1015, 1025, 1010, 1020),
             (1020, 1030, 1015, 1025), (1025, 1028, 1018, 1020), (1018, 1022, 1012, 1015), (1015, 1018, 1008, 1010),
             (1010, 1015, 1005, 1012), (1012, 1030, 1008, 1025), (1025, 1045, 1020, 1040), (1040, 1042, 1030, 1035),
             (1035, 1040, 1030, 1032), (1030, 1036, 1026, 1034), (1034, 1038, 1028, 1036), (1036, 1040, 1031, 1038)])
C_E = {"taker_fee_pct": 0.12, "maker_fee_pct": 0.0, "slippage_pct": 0.03, "spread_pct": 0.06}  # taker path: no maker fee (i4-r1-05)
CFG_E = cfg(costs=C_E, allow_short=True, stop_loss_pct=3.0, swap_daily_pct=0.72)
SIG_E = [(1, "BUY"), (5, "SELL"), (7, "SELL"), (12, "BUY")]
_sl_short_E = sell_px(1010, C_E) * 1.03  # R-P1: short stop level = entry x (1 + 3/100)
TR_E = [trade(2, +1, buy_px(1010, C_E), 0.12, 6, sell_px(1018, C_E), 0.12),          # R-T1: signal bar + 1 open
        trade(8, -1, sell_px(1010, C_E), 0.12, 10, buy_px(max(1025, _sl_short_E), C_E), 0.12),  # R-P1/R-P3: high 1045 >= level, trigger max(open, level)
        trade(13, +1, buy_px(1030, C_E), 0.12)]                                          # open at the end
W_E = ("fills", "pnls", "equity", "metrics", "missed_fills")
# the reference (bar_sim) holds the bar model R-* only, not the metric formulas M-1..M-12 (its SPEC.md §4): its side of
# the I4-1 scenes judges the bar model; the metrics are judged on the engine side here and in I4-17
W_E_REF = ("fills", "pnls", "equity", "missed_fills")

# F: the end-to-end maker path (I4-1 / I4-3); also the touchstone's target (a resting order's life)
F = mk_bars([(100, 101, 99, 100), (100, 101, 99.5, 100), (100.5, 101, 100, 100.8), (100.8, 101.2, 99.8, 100.5),
             (100.5, 102, 100.2, 101), (101, 102.5, 100.6, 101.8), (101.8, 102.2, 101.5, 102), (102, 102, 101.2, 101.5),
             (101.5, 102.5, 101, 102.2), (102.2, 103, 101.8, 102.8), (103, 104.5, 102.9, 104.2), (104.2, 104.6, 103.5, 104),
             (104, 104.8, 104, 104.5), (104.5, 105, 104.2, 104.8), (104.8, 105.2, 104.1, 105), (105, 105.5, 103, 104)])
C_F = {"taker_fee_pct": 0.1, "maker_fee_pct": 0.01, "slippage_pct": 0.02, "spread_pct": 0.04}
CFG_F = cfg(costs=C_F, execution="maker", maker_timeout_bars=3, allow_short=True, stop_loss_pct=2.0,
            exit_execution="maker_tp", maker_tp_pct=2.0)
SIG_F = [(1, "BUY"), (6, "SELL"), (11, "BUY")]
TR_F = [trade(3, +1, 100.0, 0.01, 5, 102.0, 0.01),               # R-M1: limit 100 (close[1]); bar 2 low = 100 touch, bar 3 low 99.8 < 100; R-X1: TP 102, bar 4 high = 102 touch, bar 5 high 102.5 > 102
        trade(8, -1, 102.0, 0.01, 10, buy_px(max(103, 102.0 * 1.02), C_F), 0.1)]  # R-M1: bar 7 high = 102 touch, bar 8 high 102.5 > 102; R-P1/R-P3: bar 10 high 104.5 >= 104.04
# the BUY@11 limit 104 rests on bars 12..14 (bar 12 low = 104 touch) and is cancelled at bar 14 (R-M2: 14 - 11 = 3)


# --------------------------------------------------------------------------- I4-1 independent reference
add(id="i4-1-ref-taker", viewpoint="I4-1", kind="値",
    what="同じ入力(足の taker の経路: 手数料・スプレッド・滑り・ショート・逆指値・資金の持ち越し・終わりに建玉が残る)を、"
         "本体と、本体とは別に書かれた参照実装の両方で回し、両方が正解と一致するか(参照実装の側は足の模型の規則 R-* の結果 = 約定・損益・"
         "資産・取り逃しを判定する。参照実装は指標の式 M-1〜M-12 を持たない = src/bot/bt/reference/SPEC.md §4。指標は本体の側と I4-17 で判定する)",
    how="E の足で、約定の足と基準の値を規則 R-T1・R-P1・R-P3 で手で置き(場面の注記)、サイズ・手数料・持ち越し・損益・"
        "資産の推移・指標を R-A1〜R-A4・R-S1・M-1〜M-12 の式で計算した。本体と参照実装の両方にこの同じ正解を当てる。",
    input={**bars_input(E, SIG_E, CFG_E, want=W_E), "reference": True},
    expect={"engine": full_expect(E, TR_E, CFG_E, 60, W_E), "reference": full_expect(E, TR_E, CFG_E, 60, W_E_REF)},
    judge={"engine": J(*W_E), "reference": J(*W_E_REF)})
add(id="i4-1-ref-maker", viewpoint="I4-1", kind="値",
    what="同じ入力(足の maker の経路: 指値の厳密な通過・maker の利確・逆指値・時間切れの取消)を、本体と参照実装の両方で回し、"
         "両方が正解と一致するか",
    how="F の足で、約定の足と値を R-M1・R-M2・R-X1・R-P1・R-P3 で手で置き、帳簿を R-A・M の式で計算した。"
        "取り消された指値は 1 件(R-M2)。",
    input={**bars_input(F, SIG_F, CFG_F, want=W_E), "reference": True},
    expect={"engine": full_expect(F, TR_F, CFG_F, 60, W_E, missed=1),
            "reference": full_expect(F, TR_F, CFG_F, 60, W_E_REF, missed=1)},
    judge={"engine": J(*W_E), "reference": J(*W_E_REF)})


# --------------------------------------------------------------------------- I4-2 property grid
def taker_rule(case):
    """R-T1..R-T4 as a function: the fills of a taker-only case (no stops, no maker, no carry)."""
    bars, c, cf = case["bars"], case["config"]["costs"], case["config"]
    sig = {s["bar"]: s["signal"] for s in case["signals"]}
    pos, trades, cur = 0, [], None
    for i in range(len(bars) - 1):  # R-T2: a signal at the last bar has no next bar
        s = sig.get(i)
        if s is None:
            continue
        ref = bars[i + 1]["open"]
        if s == "CLOSE":
            s = "SELL" if pos > 0 else "BUY" if pos < 0 else None
            if s is None:
                continue
        if s == "BUY":
            if pos < 0:
                cur.update(cb=i + 1, xp=buy_px(ref, c), xfp=c["taker_fee_pct"]); trades.append(cur); cur, pos = None, 0
            elif pos == 0:
                cur, pos = trade(i + 1, +1, buy_px(ref, c), c["taker_fee_pct"]), 1
        else:
            if pos > 0:
                cur.update(cb=i + 1, xp=sell_px(ref, c), xfp=c["taker_fee_pct"]); trades.append(cur); cur, pos = None, 0
            elif pos == 0 and cf["allow_short"]:
                cur, pos = trade(i + 1, -1, sell_px(ref, c), c["taker_fee_pct"]), -1
    if cur is not None:
        trades.append(cur)
    return trades


def _random_bars(rng, m):
    px, rows = 1000.0, []
    for _ in range(m):
        o = round(px + rng.uniform(-8, 8), 1)
        c = round(o + rng.uniform(-10, 10), 1)
        h = round(max(o, c) + rng.uniform(0, 6), 1)
        lo = round(min(o, c) - rng.uniform(0, 6), 1)
        rows.append((o, h, lo, c))
        px = c
    return rows


def trim_costs(conf):
    """A fee rate of a kind the run cannot charge is set to 0 (no cost the judged keys cannot see, i4-r1-05)."""
    kinds = fee_kinds(conf)
    for kind in ("taker", "maker"):
        if kind not in kinds:
            conf["costs"][f"{kind}_fee_pct"] = 0.0
    if "taker" not in kinds:
        conf["costs"]["spread_pct"] = conf["costs"]["slippage_pct"] = 0.0
    return conf


def grid_cases(seed=20260926, n=30):
    """Random bars, random scripts and random costs (taker only, the exact grid); drawn without looking at any
    target's code paths."""
    rng = random.Random(seed)
    cases = []
    for _ in range(n):
        m = rng.randint(8, 20)
        rows = _random_bars(rng, m)
        costs = {k: rng.choice([0.0, 0.01, 0.05, 0.1, 0.15]) for k in ZERO}
        sigs = [(i, rng.choice(["BUY", "SELL", "CLOSE"])) for i in range(m) if rng.random() < 0.45]
        conf = trim_costs(cfg(costs=costs, allow_short=rng.random() < 0.5, initial_equity=float(rng.choice([6000, 100000])),
                              order_notional=float(rng.choice([3000, 1234.5]))))
        cases.append(bars_input(mk_bars(rows), sigs, conf, want=("fills", "pnls", "equity")))
    return cases


# The bar-model options a property grid draws; each grid names the ones it switches on (PATHS), the rest stay plain.
PATHS = ("maker", "stop", "tp", "mtp", "swap", "hold", "wick", "mask", "sides", "short", "costs", "hour")


def paths_of(conf, bar_seconds=60) -> set:
    """The paths a case's config goes through (read from the config, for the coverage tests)."""
    out = set()
    if conf["execution"] == "maker":
        out.add("maker")
    for k, name in (("stop_loss_pct", "stop"), ("take_profit_pct", "tp"), ("swap_daily_pct", "swap"),
                    ("max_hold_bars", "hold"), ("entry_mask", "mask")):
        if conf[k]:
            out.add(name)
    if conf["exit_execution"] == "maker_tp":
        out.add("mtp")
    if conf["stop_mode"] == "wick_invalidation":
        out.add("wick")
    if conf["entry_sides"] != "both":
        out.add("sides")
    if conf["allow_short"]:
        out.add("short")
    if any(conf["costs"].values()):
        out.add("costs")
    if bar_seconds != 60:
        out.add("hour")
    return out


def _draw_config(rng, m, on):
    over = {}
    if "maker" in on:
        over.update(execution="maker", maker_timeout_bars=rng.randint(1, 4))
    if "wick" in on:
        over.update(stop_mode="wick_invalidation", stop_window_bars=rng.randint(1, 4))
    elif "stop" in on:
        over["stop_loss_pct"] = rng.choice([0.3, 0.5, 0.8, 1.2])
    if "tp" in on:
        over["take_profit_pct"] = rng.choice([0.4, 0.6, 1.0, 1.5])
    if "mtp" in on:
        over.update(exit_execution="maker_tp", maker_tp_pct=rng.choice([0.3, 0.5, 0.9, 1.3]))
    if "swap" in on:
        over["swap_daily_pct"] = rng.choice([0.04, 0.24, 1.2])
    if "hold" in on:
        over["max_hold_bars"] = rng.randint(1, 5)
    if "mask" in on:
        over["entry_mask"] = [rng.random() < 0.7 for _ in range(m)]
    if "sides" in on:
        over["entry_sides"] = rng.choice(["long", "short"])
    if "short" in on or ("sides" in on and over.get("entry_sides") == "short"):
        over["allow_short"] = True
    if "costs" in on:
        over["costs"] = {k: rng.choice([0.0, 0.01, 0.05, 0.1]) for k in ZERO}
    return trim_costs(cfg(**over))


def property_cases(seed, n, fixed=(), drawn=PATHS, p_on=0.5, first_signal=0):
    """n random cases (bars, script, config) with the paths `fixed` always on and each of `drawn` on with p_on,
    each followed by its prefix case (the same case cut to its first k bars, k drawn): the prefix rule of
    i4_judge (no fill, PnL or equity before bar k may depend on bars from k on).  Returns (cases, expects)."""
    rng = random.Random(seed)
    cases, expects = [], []
    for _ in range(n):
        m = rng.randint(10, 22)
        rows = _random_bars(rng, m)
        on = set(fixed) | {p for p in drawn if rng.random() < p_on}
        conf = _draw_config(rng, m, on)
        bs = 3600 if "hour" in on else 60
        sigs = [(i, rng.choice(["BUY", "SELL", "CLOSE"])) for i in range(first_signal, m) if rng.random() < 0.45]
        full = bars_input(mk_bars(rows, bar_seconds=bs), sigs, conf, bar_seconds=bs, want=("fills", "pnls", "equity"))
        k = rng.randint(max(4, m // 2), m - 1)
        pconf = dict(conf)
        pconf["costs"] = dict(conf["costs"])
        if conf["entry_mask"] is not None:
            pconf["entry_mask"] = list(conf["entry_mask"][:k])
        pre = bars_input(mk_bars(rows[:k], bar_seconds=bs), [(b, x) for b, x in sigs if b < k], pconf, bar_seconds=bs,
                         want=("fills", "pnls", "equity"))
        expects += [{"invariants_only": True}, {"prefix_of": len(cases), "upto": k}]
        cases += [full, pre]
    return cases, expects


_INV = ("不変条件(i4_judge.invariants の I1〜I12: 建てと決済が交互で向きが揃う・数量の保存(建ての数量は正、決済は同じ数量)・約定は原因の合図より後で"
        "決済は建てより後・建ての原因の合図がある・向きとマスクと空売りの許可を守る・損益の恒等式 R-A3(建ての率は執行で決まり、決済の率は "
        "taker か maker のどちらか)・資産の恒等式 R-A4・損益の数 = 決済の数・保有の上限を超えない・起きた出口(逆指値・利確・maker の利確・構造的な"
        "逆指値・taker の決済の合図)を飛ばさない・taker の建ての合図を飛ばさない・maker の建ての指値を飛ばさない)と、先頭の部分の規則(同じ場合を最初の k 本で切った実行は、"
        "足 k より前の約定・損益・資産が元の実行と同じ = 先読みしない)")
_GA_CASES, _GA_EXP = property_cases(20260927, 24)
add(id="i4-2-grid-all", viewpoint="I4-2", kind="値",
    what="種 20260927 で引いた 24 の場合(足の模型の全ての選択肢 = maker・逆指値・利確・maker の利確・持ち越し・保有の上限・構造的な逆指値・"
         "マスク・向き・空売り・費用・1 時間足を、場合ごとに乱数でオンにする。実装の場合分けから作らない)とその先頭の部分の全部で、" + _INV
         + "が 1 つも崩れないか",
    how="正解は置かない(手で正解を出せない経路を、正解なしで式だけで判定する。i4-r1-06)。不変条件は観測した約定・損益・資産と、場合の入力"
        "(足・合図・設定)だけから式で検める(規則の場合分けを写さない)。",
    cases=_GA_CASES, expect=_GA_EXP, judge={"invariants": True})
_GRID = grid_cases()
add(id="i4-2-grid", viewpoint="I4-2", kind="値",
    what="種 20260926 で引いた 30 の場合(足・合図の並び・費用・ショートの可否・元本・発注額を乱数で引く。実装の場合分けから作らない)の"
         "全部で、約定が規則どおりで、" + _INV.split("と、先頭の部分")[0] + "が 1 つも崩れないか",
    how="約定の足と値は規則 R-T1〜R-T4 を関数にした taker_rule で決め(停止・maker・持ち越しを含まない taker だけの場合)、帳簿は R-A の式。"
        "不変条件は観測した約定から判定の側で式で検める(i4_judge.invariants)。",
    cases=_GRID,
    expect=[full_expect(c["bars"], taker_rule(c), c["config"], 60, ("fills", "pnls", "equity")) for c in _GRID],
    judge=J("fills", "pnls", "equity") | {"invariants": True})
# one grid per path, with that path always on and nothing else (no cost, no signal on bar 0): a tool that has the
# path but not the other options is judged on it (i4-r1-05 / i4-r1-06)
for _k, (_path, _title) in enumerate([("stop", "逆指値"), ("tp", "利確"), ("maker", "maker の建てと決済"), ("mtp", "maker の利確"),
                                       ("swap", "持ち越し"), ("hold", "保有の上限"), ("wick", "構造的な逆指値")]):
    _c, _e = property_cases(20260928 + _k, 8, fixed=(_path,), drawn=(), first_signal=1)
    add(id=f"i4-2-grid-{_path}", viewpoint="I4-2", kind="値",
        what=f"種 {20260928 + _k} で引いた 8 の場合(足・合図を乱数で引き、{_title}だけをオンにする。費用 0、足 0 に合図なし)とその先頭の部分の"
             "全部で、" + _INV + "が 1 つも崩れないか",
        how="正解は置かない。i4-2-grid-all と同じ不変条件と先頭の部分の規則で判定する。",
        cases=_c, expect=_e, judge={"invariants": True})


# --------------------------------------------------------------------------- I4-3 known-answer scenes (whole engine)
add(id="i4-3-e2e-taker", viewpoint="I4-3", kind="値",
    what="エンジン全体の粒度の正解つきの場面(足の taker の経路): 約定・損益・資産の推移・12 の指標・取り逃しの数が全部正解と一致するか",
    how="i4-1-ref-taker と同じ手の計算(E の足、R-T1・R-P1・R-P3・R-A・R-S1・M)。",
    input=bars_input(E, SIG_E, CFG_E, want=W_E), expect=full_expect(E, TR_E, CFG_E, 60, W_E), judge=J(*W_E))
add(id="i4-3-e2e-maker", viewpoint="I4-3", kind="値",
    what="エンジン全体の粒度の正解つきの場面(足の maker の経路): 約定・損益・資産の推移・12 の指標・取り逃しの数が全部正解と一致するか",
    how="i4-1-ref-maker と同じ手の計算(F の足、R-M1・R-M2・R-X1・R-P1・R-P3・R-A・M)。",
    input=bars_input(F, SIG_F, CFG_F, want=W_E), expect=full_expect(F, TR_F, CFG_F, 60, W_E, missed=1), judge=J(*W_E))


# --------------------------------------------------------------------------- I4-4 portable synthetic scenes
add(id="i4-4-plain", viewpoint="I4-4", kind="値",
    what="費用 0・買いだけ・翌足の始値の成行という、足のバックテストの道具のどれでも表せる合成の場面で、同じ数(約定の足・値・損益)が出るか",
    how="B の足。合図 BUY@1 → 足 2 の始値 100、SELL@4 → 足 5 の始値 106(R-T1)。サイズ 3000/100 = 30、損益 (106-100) x 30 = 180。",
    input=bars_input(B, [(1, "BUY"), (4, "SELL")], cfg(), want=("fills", "pnls")),
    expect=full_expect(B, [trade(2, +1, 100.0, 0.0, 5, 106.0, 0.0)], cfg(), 60, ("fills", "pnls")),
    judge=J("fills", "pnls", fill_fields=("bar", "side", "price")))
_CFG_FEE = cfg(costs={**ZERO, "taker_fee_pct": 0.1})
add(id="i4-4-fee", viewpoint="I4-4", kind="値",
    what="i4-4-plain に taker 手数料 0.1% だけを足した合成の場面で、同じ数(約定・損益)が出るか",
    how="i4-4-plain と同じ約定。損益 = 6 x 30 - 30 x 106 x 0.001 - 3000 x 0.001 = 180 - 3.18 - 3 = 173.82(R-A2・R-A3)。",
    input=bars_input(B, [(1, "BUY"), (4, "SELL")], _CFG_FEE, want=("fills", "pnls")),
    expect=full_expect(B, [trade(2, +1, 100.0, 0.1, 5, 106.0, 0.1)], _CFG_FEE, 60, ("fills", "pnls")),
    judge=J("fills", "pnls", fill_fields=("bar", "side", "price")))


# --------------------------------------------------------------------------- I4-5 / I4-6 the integrated pipeline
def csv_text(header, rows, delim=","):
    out = ([delim.join(header)] if header else []) + [delim.join(str(x) for x in r) for r in rows]
    return "\n".join(out) + "\n"


def iso(t_ns, digits=3, sep="T", suffix="Z", offset_h=0):
    import datetime as _dt
    sec, frac = divmod(t_ns + offset_h * 3600 * NS, NS)
    d = _dt.datetime(1970, 1, 1) + _dt.timedelta(seconds=sec)
    f9 = f"{frac:09d}"
    assert f9[digits:] == "0" * (9 - digits), (t_ns, digits)
    return d.strftime(f"%Y-%m-%d{sep}%H:%M:%S") + ("." + f9[:digits] if digits else "") + suffix


S = NS
_BF = [(T0 + 200_000_000, 15000000, "0.01", "BUY"), (T0 + 120 * S, 15000500, "0.02", "SELL"),
       (T0 + 300 * S, 15001000, "0.5", "SELL"), (T0 + 1800 * S, 15002000, "0.1", "BUY"),
       (T0 + 3600 * S + 750_000_000, 15003000, "0.3", "BUY"), (T0 + 3899 * S + 999_000_000, 15003500, "0.1", "SELL"),
       (T0 + 3902 * S, 15004000, "0.2", "BUY")]
_BN = [(T0 + 123_000_000, "96000.1"), (T0 + 299 * S + 999_000_000, "96010"), (T0 + 300 * S + 1_000_000, "96020.5"),
       (T0 + 3600 * S, "96100"), (T0 + 3900 * S + 500_000_000, "96050")]
_FX = [(T0 + 500_000_000, "157.100", "157.103"), (T0 + 300 * S + 250_000_000, "157.120", "157.124"),
       (T0 + 3600 * S, "157.200", "157.204"), (T0 + 3901 * S, "157.180", "157.185")]
_BOARD_T = [T0 + 10 * S, T0 + 301 * S, T0 + 3601 * S]


def _pipeline_files():
    files, ds = [], []
    p = "backtest_data/bf_exec_synth_20260105/executions_20260105.csv"
    files.append({"path": p, "text": csv_text(["id", "exec_date", "price", "size", "side"],
                                              [(3100000001 + k, iso(t, suffix=""), px, q, sd) for k, (t, px, q, sd) in enumerate(_BF)])})
    ds.append({"name": "bf_trades", "paths": [p], "origin": "real",
               "spec": {"format": "csv", "header": True, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY",
                        "asset": "crypto", "time": {"columns": ["exec_date"], "unit": "iso", "tz": "UTC"},
                        "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"},
                        "side_map": {"BUY": "buy", "SELL": "sell", "": ""}, "key": "id"}})
    p = "backtest_data/bf_board_synth_20260105/board_top10_20260105.csv"
    head = ["ts"] + [f"{s}_{k}_{i}" for s in ("bid", "ask") for k in ("px", "sz") for i in range(1, 11)]
    rows = []
    for t in _BOARD_T:
        rows.append([iso(t, digits=0, sep=" ", suffix="+00:00")]
                    + [15000000 - 5 * i for i in range(10)] + [0.1] * 10 + [15000010 + 5 * i for i in range(10)] + [0.2] * 10)
    files.append({"path": p, "text": csv_text(head, rows)})
    f = {"levels": 10}
    for side in ("bid", "ask"):
        f[f"{side}_px"] = [f"{side}_px_{i}" for i in range(1, 11)]
        f[f"{side}_sz"] = [f"{side}_sz_{i}" for i in range(1, 11)]
    ds.append({"name": "bf_board", "paths": [p], "origin": "real",
               "spec": {"format": "csv", "header": True, "delimiter": ",", "kind": "book", "symbol": "FX_BTC_JPY",
                        "asset": "crypto", "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"}, "fields": f}})
    p = "backtest_data/binance_BTCUSDT_aggTrades_synth/BTCUSDT-aggTrades-2026-01-05.csv"
    files.append({"path": p, "text": csv_text(None, [(7001 + k, px, "0.01", 9001 + k, 9001 + k, t // 1_000_000, "False", "True")
                                                     for k, (t, px) in enumerate(_BN)])})
    ds.append({"name": "binance", "paths": [p], "origin": "real",
               "spec": {"format": "csv", "header": False, "delimiter": ",", "kind": "trade", "symbol": "BTCUSDT",
                        "asset": "crypto", "names": ["agg_id", "price", "qty", "first_id", "last_id", "transact_time",
                                                     "is_buyer_maker", "is_best_match"],
                        "time": {"columns": ["transact_time"], "unit": "ms", "tz": "UTC"},
                        "fields": {"id": "agg_id", "px": "price", "qty": "qty", "side": "is_buyer_maker"},
                        "side_map": {"True": "sell", "False": "buy"}, "key": "id"}})
    p = "backtest_data/fx_event_ticks_synth/USDJPY_20260105.csv"
    files.append({"path": p, "text": csv_text(["ts_utc", "bid", "ask", "bidvol", "askvol"],
                                              [(iso(t, sep=" ", suffix=""), b, a, "1", "1") for t, b, a in _FX])})
    ds.append({"name": "fx_ticks", "paths": [p], "origin": "real",
               "spec": {"format": "csv", "header": True, "delimiter": ",", "kind": "quote", "symbol": "USDJPY",
                        "asset": "fx", "time": {"columns": ["ts_utc"], "unit": "iso", "tz": "UTC"},
                        "fields": {"bid": "bid", "ask": "ask", "bid_qty": "bidvol", "ask_qty": "askvol"}}})
    # JPX 1-minute bars, JST wall clock 09:00 .. 10:10 (= 00:00 .. 01:10 UTC), open = 38000 + 5 x minute
    p = "backtest_data/n225f_synth_20260105/bars_1min.csv"
    jrows = []
    for m in range(71):
        o = 38000 + 5 * m
        hh, mm = divmod(9 * 60 + m, 60)
        jrows.append(("2026-01-05", f"{hh:02d}:{mm:02d}", o, o + 3, o - 3, o + 2, 10))
    files.append({"path": p, "text": csv_text(["date", "time", "open", "high", "low", "close", "volume"], jrows)})
    ds.append({"name": "jpx_1m", "paths": [p], "origin": "real",
               "spec": {"format": "csv", "header": True, "delimiter": ",", "kind": "bar", "symbol": "N225F", "asset": "jpx",
                        "time": {"columns": ["date", "time"], "join": " ", "unit": "iso", "tz": "Asia/Tokyo"},
                        "fields": {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"},
                        "bar": {"interval_s": 60, "label": "start"}, "key": "start"}})
    # FX 1-minute bars, UTC 00:00 .. 01:10, open = 157 + 0.001 x minute (written with 3 decimals)
    p = "backtest_data/fx_1m_synth/USDJPY_1m_20260105.csv"
    frows = [(iso(T0 + 60 * m * S, digits=0), f"{157 + 0.001 * m:.3f}", f"{157.0005 + 0.001 * m:.4f}",
              f"{156.9995 + 0.001 * m:.4f}", f"{157 + 0.001 * m:.3f}", 5) for m in range(71)]
    files.append({"path": p, "text": csv_text(["ts", "open", "high", "low", "close", "volume"], frows)})
    ds.append({"name": "fx_1m", "paths": [p], "origin": "real",
               "spec": {"format": "csv", "header": True, "delimiter": ",", "kind": "bar", "symbol": "USDJPY", "asset": "fx",
                        "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"},
                        "fields": {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"},
                        "bar": {"interval_s": 60, "label": "start", "session": "24x5"}, "key": "start"}})
    return files, ds


SCHEDULE = [{"t_ns": T0, "side": "buy", "qty": 1.0}, {"t_ns": T0 + 300 * S, "side": "sell", "qty": 1.0},
            {"t_ns": T0 + 3600 * S, "side": "buy", "qty": 1.0}, {"t_ns": T0 + 3900 * S, "side": "sell", "qty": 1.0}]
INSTRUMENTS = [{"name": "bf", "price": "bf_trades", "with": ["bf_board"]}, {"name": "binance", "price": "binance", "with": []},
               {"name": "fx_tick", "price": "fx_ticks", "with": []}, {"name": "jpx", "price": "jpx_1m", "with": []},
               {"name": "fx_1m", "price": "fx_1m", "with": []}]
FILL_RULE = {"price": "first_observed_at_or_after", "trade": "px", "quote": {"buy": "ask", "sell": "bid"}, "bar": "open",
             "latency_ns": 0}
TABS = ["概要", "前提", "損益", "取引", "約定の質", "費用", "分布", "検証", "再現性", "データ品質"]
BANNER = "動作確認の実行。相場の結論には使わない"


def pipeline_input(want, *, strategy=None, purpose="動作確認", prereg=None, only=None, origin=None):
    """`only`: keep only these instruments (and the datasets they name); `origin`: declare every dataset so."""
    files, ds = _pipeline_files()
    ins = INSTRUMENTS
    if only is not None:
        ins = [i for i in INSTRUMENTS if i["name"] in only]
        keep = {n for i in ins for n in [i["price"], *i["with"]]}
        ds = [d for d in ds if d["name"] in keep]
        paths = {pth for d in ds for pth in d["paths"]}
        files = [f for f in files if f["path"] in paths]
    if origin is not None:
        ds = [{**d, "origin": origin} for d in ds]
    return {"op": "pipeline", "files": files, "datasets": ds, "instruments": ins,
            "strategy": strategy or {"kind": "schedule", "orders": SCHEDULE}, "fill": FILL_RULE, "costs": dict(ZERO),
            "purpose": purpose, "prereg_sha256": prereg, "want": list(want)}


def _first_at_or_after(events, t):
    return next(e for e in events if e[0] >= t)


def pipeline_expect():
    """F-1: every scheduled order fills at the first observation at or after its time
    (trade: its price; quote: ask for a buy, bid for a sell; bar: the open of the first bar starting at or after)."""
    fills, pnl = {}, {}
    src = {"bf": [(t, float(px)) for t, px, _, _ in _BF], "binance": [(t, float(px)) for t, px in _BN]}
    for name, ev in src.items():
        fl = []
        for o in SCHEDULE:
            t, px = _first_at_or_after(ev, o["t_ns"])
            fl.append({"t_ns": t, "side": o["side"], "px": px, "qty": 1.0})
        fills[name] = fl
    fl = []
    for o in SCHEDULE:
        t, b, a = _first_at_or_after(_FX, o["t_ns"])
        fl.append({"t_ns": t, "side": o["side"], "px": float(a if o["side"] == "buy" else b), "qty": 1.0})
    fills["fx_tick"] = fl
    jb = [(T0 + 60 * m * S, float(38000 + 5 * m)) for m in range(71)]  # 09:00 JST = 00:00 UTC
    fb = [(T0 + 60 * m * S, float(f"{157 + 0.001 * m:.3f}")) for m in range(71)]
    for name, ev in (("jpx", jb), ("fx_1m", fb)):
        fills[name] = [{"t_ns": _first_at_or_after(ev, o["t_ns"])[0], "side": o["side"],
                        "px": _first_at_or_after(ev, o["t_ns"])[1], "qty": 1.0} for o in SCHEDULE]
    for name, fl in fills.items():
        pnl[name] = sum((f["px"] if f["side"] == "sell" else -f["px"]) * f["qty"] for f in fl)
    return fills, pnl


_PF, _PP = pipeline_expect()
_EV = {"bf_trades": len(_BF), "bf_board": len(_BOARD_T), "binance": len(_BN), "fx_ticks": len(_FX), "jpx_1m": 71, "fx_1m": 71}
add(id="i4-5-fills", viewpoint="I4-5", kind="値",
    what="暗号資産の約定と板(bitFlyer の形)・Binance の aggTrades の形・FX のイベントティック・JPX の 1 分足・FX の 1 分足の合成の"
         "ファイルを 1 回の呼び出しで通し、時刻だけで決まる固定の手順(毎時 0 分に 1 単位買い、5 分後に売る)の約定・損益・読んだ事象の数が"
         "正解と一致するか",
    how="ファイルは書く前に行(時刻と値)を決め、その行から書いた。約定は F-1(注文の時刻以後に最初に観測した値)で手で引いた: "
        "bf 15000000 / 15001000 / 15003000 / 15004000、binance 96000.1 / 96020.5 / 96100 / 96050、FX ティック ask 157.103 / "
        "bid 157.120 / ask 157.204 / bid 157.180、JPX 足 38000 / 38025 / 38300 / 38325(09:00 JST = 00:00 UTC)、FX 足 157.000 / "
        "157.005 / 157.060 / 157.065。損益 = 売り - 買い の和。読んだ事象の数はファイルの行数。",
    input=pipeline_input(("fills", "pnl", "events_read")),
    expect={"fills": _PF, "pnl": _PP, "events_read": _EV},
    judge={"pfills": True, "pnl": True, "events_read": True})
_SHA = {f["path"]: hashlib.sha256(f["text"].encode("utf-8")).hexdigest() for f in _pipeline_files()[0]}
add(id="i4-5-outputs", viewpoint="I4-5", kind="能力",
    what="同じ 1 回の実行が、実行記録(目的・読んだファイルの sha256)・指標の書き出し(目的・銘柄ごとの往復の数)・"
         "ダッシュボードの項目別タブ(10 のタブと、全タブの注記)まで届くか",
    how="sha256 は場面が書いたバイト列から計算した。往復の数は手順の 2 往復 x 5 銘柄。タブの名と注記の文は委任文 §2 項目 3 の行"
        "(概要 / 前提 / 損益 / 取引 / 約定の質 / 費用 / 分布 / 検証 / 再現性 / データ品質、注記「動作確認の実行。相場の結論には使わない」)。",
    input=pipeline_input(("run_record", "export", "dashboard")),
    expect={"run_record": {"purpose": "動作確認", "data_sha256": _SHA},
            "export": {"purpose": "動作確認", "num_trades": {i["name"]: 2 for i in INSTRUMENTS}},
            "dashboard": {"tabs": TABS, "banner": BANNER}},
    judge={"run_record": True, "export": True, "dashboard": True})
add(id="i4-6-label", viewpoint="I4-6", kind="値",
    what="実データと宣言したファイルに固定の手順を通した実行で、指標の書き出しの目的が「動作確認」、ダッシュボードの全タブに注記が出て、"
         "約定は手順どおりか",
    how="i4-5-fills と同じ約定(F-1)。目的と注記の文は委任文 §4。",
    input=pipeline_input(("fills", "export", "dashboard")),
    expect={"fills": _PF, "export": {"purpose": "動作確認", "num_trades": {i["name"]: 2 for i in INSTRUMENTS}},
            "dashboard": {"tabs": TABS, "banner": BANNER}},
    judge={"pfills": True, "export": True, "dashboard": True})
PRICE_RULE = {"kind": "price_rule", "buy_below": 15000600.0, "sell_above": 15002500.0, "qty": 1.0}


def price_rule_expect(events, rule):
    """F-2: at each price event of the instrument (a trade: its price), flat and price < buy_below -> buy qty; long and
    price > sell_above -> sell the position; the order fills by F-1 at the first observation at or after its time,
    which (no latency) is that same event; the next order waits for the fill."""
    pos, out = 0.0, []
    for t, px in events:
        if pos == 0 and px < rule["buy_below"]:
            out.append({"t_ns": t, "side": "buy", "px": px, "qty": rule["qty"]})
            pos = rule["qty"]
        elif pos > 0 and px > rule["sell_above"]:
            out.append({"t_ns": t, "side": "sell", "px": px, "qty": pos})
            pos = 0.0
    return out


_PR_FILLS = {"bf": price_rule_expect([(t, float(px)) for t, px, _, _ in _BF], PRICE_RULE)}
add(id="i4-6-signal-refused", viewpoint="I4-6", kind="能力",
    what="実データと宣言したファイルに、値で条件づけた戦略(値が閾値を下回ったら買う)を目的「動作確認」で通そうとしたら拒むか"
         "(対照 1: 同じファイルに固定の手順なら通り、約定は手順どおり。対照 2: 同じ値で条件づけた戦略を、合成と宣言したデータに通せば"
         "通り、約定は F-2 どおり = 対象は値で条件づけた戦略を走らせられ、拒むのは実データのときだけ)",
    how="委任文 §4「実データを通すときの戦略は、時刻だけで決まる機械的な手順か種つきの乱数に限る。信号・条件付け・最適化を入れない」。"
        "対照 1 の正解は i4-5-fills の約定。対照 2 の正解は F-2 を bf の約定の行に当てた手の計算: 15000000 < 15000600 で買い 1(T0 + 0.2 秒)、"
        "15003000 > 15002500 で売り 1(T0 + 3600.75 秒)。",
    input=pipeline_input(("fills",)), expect={"fills": _PF}, judge={"pfills": True},
    more_controls=[{"input": pipeline_input(("fills",), strategy=PRICE_RULE, only=("bf",), origin="synthetic"),
                    "expect": {"fills": _PR_FILLS}, "judge": {"pfills": True}}],
    variant=pipeline_input(("fills",), strategy=PRICE_RULE))
PREREG_SHA = hashlib.sha256("i4 battery: a stand-in pre-registration text".encode("utf-8")).hexdigest()
add(id="i4-6-research-refused", viewpoint="I4-6", kind="能力",
    what="目的「研究」を事前登録のハッシュ無しで実行しようとしたら拒むか(対照 1: 目的「動作確認」なら通る。対照 2: 目的「研究」を事前登録の"
         "ハッシュつきで実行すれば通り、約定は手順どおり = 対象は「研究」の実行を作れ、拒むのはハッシュが無いときだけ)",
    how="委任文 §4「目的 `研究` の実行は事前登録のハッシュが無いと作れない」。対照 1・2 の正解は i4-5-fills の約定(戦略は同じ固定の手順)。",
    input=pipeline_input(("fills",)), expect={"fills": _PF}, judge={"pfills": True},
    more_controls=[{"input": pipeline_input(("fills",), purpose="研究", prereg=PREREG_SHA), "expect": {"fills": _PF},
                    "judge": {"pfills": True}}],
    variant=pipeline_input(("fills",), purpose="研究", prereg=None))


# --------------------------------------------------------------------------- I4-8 next-bar-open taker execution
_W3 = ("fills", "pnls", "equity")
_WF = ("fills",)                 # the viewpoint is when and at what price the fills happen
_WFP = ("fills", "pnls")         # ... and which fee / cost each fill paid (seen through the PnL)
_WFM = ("fills", "missed_fills")  # ... and how many resting orders ended unfilled
add(id="i4-8-next-open", viewpoint="I4-8", kind="値",
    what="足 i の合図が足 i+1 の始値で、スプレッドの半分 + 滑りを乗せて taker で約定するか。最後の足の合図は約定しないか",
    how="B の足、費用 C_TAK。BUY@1 → 足 2 の始値 100 x (1 + (0.02 + 0.02)/100)、SELL@4 → 足 5 の始値 106 x (1 - 0.0004)"
        "(R-T1・R-C1)、BUY@9 は次の足が無いので約定しない(R-T2)。帳簿は R-A。",
    input=bars_input(B, [(1, "BUY"), (4, "SELL"), (9, "BUY")], cfg(costs=C_TAK), want=_WFP),
    expect=full_expect(B, [trade(2, +1, buy_px(100, C_TAK), 0.1, 5, sell_px(106, C_TAK), 0.1)], cfg(costs=C_TAK), 60, _WFP),
    judge=J(*_WFP))
_CS = cfg(costs=C_TAK, allow_short=True)
add(id="i4-8-short-close", viewpoint="I4-8", kind="値",
    what="ショートを許したとき、SELL の合図で翌足の始値に売り建て、CLOSE の合図で翌足の始値に買い戻すか。建玉が無いときの CLOSE は何もしないか",
    how="B の足。SELL@2 → 足 3 の始値 120 の売り値、CLOSE@6 → 足 7 の始値 103 の買い値(R-T1・R-T3)、CLOSE@8 は建玉なしで無視(R-T3)。",
    input=bars_input(B, [(2, "SELL"), (6, "CLOSE"), (8, "CLOSE")], _CS, want=_WFP),
    expect=full_expect(B, [trade(3, -1, sell_px(120, C_TAK), 0.1, 7, buy_px(103, C_TAK), 0.1)], _CS, 60, _WFP),
    judge=J(*_WFP))
add(id="i4-8-no-short", viewpoint="I4-8", kind="値",
    what="ショートを許さないとき、建玉なしの SELL は売り建てず、BUY で買い建て、SELL で手仕舞うか",
    how="B の足、費用 0。SELL@1 は無視(R-T4)、BUY@2 → 足 3 の始値 120、SELL@5 → 足 6 の始値 105(R-T1)。",
    input=bars_input(B, [(1, "SELL"), (2, "BUY"), (5, "SELL")], cfg(), want=_WF),
    expect=full_expect(B, [trade(3, +1, 120.0, 0.0, 6, 105.0, 0.0)], cfg(), 60, _WF),
    judge=J(*_WF))

# --------------------------------------------------------------------------- I4-9 strict traded-through limits
M = mk_bars([(100, 101, 99, 100), (100, 102, 99.5, 100), (100.5, 103, 100, 102), (102, 102.5, 99.5, 101),
             (101, 104, 101, 103), (103, 105, 102, 104), (104, 105, 103, 104)])
_CM = cfg(execution="maker", maker_timeout_bars=3)  # the judged keys (fills, missed) cannot see a fee: none (i4-r1-05)
_W4 = ("fills", "pnls", "equity", "missed_fills")
add(id="i4-9-strict", viewpoint="I4-9", kind="値",
    what="maker の指値(合図の足の終値に置く)が、値に触れただけでは約定せず、後の足が厳密に通過したときだけ指値の値で maker 手数料で約定するか",
    how="M の足。BUY@1 → 指値 100(足 1 の終値)。足 2 の安値 100 は触れただけ、足 3 の安値 99.5 < 100 で 100 で約定(R-M1)。SELL@4 → "
        "指値 103、足 5 の高値 105 > 103 で 103 で約定。取り逃し 0。費用 0(判定する鍵は約定と取り逃しで、手数料は見えない)。",
    input=bars_input(M, [(1, "BUY"), (4, "SELL")], _CM, want=_WFM),
    expect=full_expect(M, [trade(3, +1, 100.0, 0.0, 5, 103.0, 0.0)], _CM, 60, _WFM, missed=0),
    judge=J(*_WFM))
SB = mk_bars([(100, 101, 99, 100), (100, 100.5, 99, 100), (99.5, 100, 99, 99.8), (99.8, 100.5, 99, 100),
              (100, 100.5, 98, 99), (99.5, 100, 99, 99.5), (99.5, 100, 98.5, 99), (99, 100, 98, 99)])
_CMS = cfg(execution="maker", maker_timeout_bars=3, allow_short=True)
add(id="i4-9-short-strict", viewpoint="I4-9", kind="値",
    what="売りの指値は高値が指値を厳密に上回ったときだけ、買い戻しの指値は安値が厳密に下回ったときだけ約定するか",
    how="SB の足。SELL@1 → 指値 100、足 2 の高値 100 は触れただけ、足 3 の高値 100.5 > 100 で売り建て 100。BUY@4 → 指値 99、"
        "足 5 の安値 99 は触れただけ、足 6 の安値 98.5 < 99 で 99 で買い戻し(R-M1)。",
    input=bars_input(SB, [(1, "SELL"), (4, "BUY")], _CMS, want=_WFM),
    expect=full_expect(SB, [trade(3, -1, 100.0, 0.0, 6, 99.0, 0.0)], _CMS, 60, _WFM, missed=0),
    judge=J(*_WFM))

# --------------------------------------------------------------------------- I4-10 intrabar TP/SL, stop first
T = mk_bars([(100, 100.5, 99.5, 100), (100, 100.5, 99.5, 100), (100, 104, 97, 99), (99, 100, 98.5, 100),
             (100, 101, 99, 100), (100, 103, 99, 102), (102, 103.5, 99, 103), (103, 103.5, 99, 100),
             (100, 100.5, 99, 99.5), (96, 97, 95, 96), (96, 97, 95, 96)])
_CT = cfg(costs={**ZERO, "taker_fee_pct": 0.1, "maker_fee_pct": 0.02}, stop_loss_pct=2.0, take_profit_pct=3.0)
add(id="i4-10-priority", viewpoint="I4-10", kind="値",
    what="1 本の足の中で逆指値と利確の両方に届くとき逆指値が先か。利確は厳密な通過でだけ、利確の値で maker 手数料か。"
         "窓を開けて逆指値を越えたら始値で約定するか。建てた足では判定しないか",
    how="T の足、逆指値 2%・利確 3%。BUY@0 → 足 1 の始値 100(足 1 は建てた足で判定しない、R-P2)。足 2 は高値 104 > 103 かつ安値 97 <= 98 → "
        "逆指値が先、値は min(始値 100, 98) = 98、taker(R-P1・R-P3)。BUY@3 → 足 4 の始値 100。足 5 の高値 103 は触れただけ、"
        "足 6 の高値 103.5 > 103 で 103、maker 0.02%(R-P4)。BUY@7 → 足 8 の始値 100。足 9 は始値 96 < 98 → min(96, 98) = 96(R-P3)。",
    input=bars_input(T, [(0, "BUY"), (3, "BUY"), (7, "BUY")], _CT, want=_WFP),
    expect=full_expect(T, [trade(1, +1, 100.0, 0.1, 2, 98.0, 0.1), trade(4, +1, 100.0, 0.1, 6, 103.0, 0.02),
                           trade(8, +1, 100.0, 0.1, 9, 96.0, 0.1)], _CT, 60, _WFP),
    judge=J(*_WFP))

# --------------------------------------------------------------------------- I4-11 wick invalidation
WL = mk_bars([(100, 101, 96, 100), (100, 101, 98, 100), (100, 101, 97, 100), (100, 101, 99, 100),
              (100, 100.5, 95, 96.5), (96.5, 97, 95.2, 95.5), (95, 96, 94, 95), (95, 96, 94, 95)])
_CW = cfg(stop_mode="wick_invalidation", stop_window_bars=3)
add(id="i4-11-wick-long", viewpoint="I4-11", kind="値",
    what="買い建ての構造的な逆指値: 水準 = 約定の足より前の完了した N 本の安値の最小で建てた時に凍結し、ヒゲが割っても終値が割らなければ出ず、"
         "終値が割った次の足の始値で taker で出るか",
    how="WL の足、N = 3。BUY@2 → 足 3 の始値 100。水準 = min(足 0〜2 の安値 96, 98, 97) = 96(R-W1。足 3 自身は含めない)。"
        "足 4 は安値 95 だが終値 96.5 >= 96 で出ない(R-W2)。足 5 の終値 95.5 < 96 → 足 6 の始値 95 で出る(R-W3)。"
        "水準が足 4 の安値 95 に動けば足 5 で出ない、窓が足 1〜3 なら水準 97 で足 4 に出る = どちらも違う答えになる。",
    input=bars_input(WL, [(2, "BUY")], _CW, want=_WF),
    expect=full_expect(WL, [trade(3, +1, 100.0, 0.0, 6, 95.0, 0.0)], _CW, 60, _WF),
    judge=J(*_WF))
WS = mk_bars([(100, 104, 99, 100), (100, 102, 99, 100), (100, 103, 99, 100), (100, 101, 99, 100),
              (100, 105, 99.5, 103.5), (103.5, 104.8, 103, 104.5), (105, 106, 104, 105), (105, 106, 104, 105)])
_CWS = cfg(stop_mode="wick_invalidation", stop_window_bars=3, allow_short=True)
add(id="i4-11-wick-short", viewpoint="I4-11", kind="値",
    what="売り建ての構造的な逆指値: 水準 = 前の N 本の高値の最大、終値が上に抜けた次の足の始値で出るか",
    how="WS の足、N = 3。SELL@2 → 足 3 の始値 100。水準 = max(104, 102, 103) = 104(R-W1)。足 4 は高値 105 だが終値 103.5 で出ない。"
        "足 5 の終値 104.5 > 104 → 足 6 の始値 105 で買い戻す(R-W3)。",
    input=bars_input(WS, [(2, "SELL")], _CWS, want=_WF),
    expect=full_expect(WS, [trade(3, -1, 100.0, 0.0, 6, 105.0, 0.0)], _CWS, 60, _WF),
    judge=J(*_WF))
_CWP = cfg(stop_loss_pct=2.0)
add(id="i4-11-refuse-stack", viewpoint="I4-11", kind="能力",
    what="構造的な逆指値と率の逆指値を重ねる設定を拒むか(対照 1: 構造的な逆指値だけなら通り、答えは i4-11-wick-long。対照 2: 率の逆指値だけなら"
         "通る = 対象は両方を別々には持ち、拒むのは重ねたときだけ)",
    how="R-W4「2 つの逆指値は代わりであって重ねない」。対照 2 の正解: WL の足、逆指値 2%(98)。BUY@2 → 足 3 の始値 100、足 4 の安値 95 <= 98 → "
        "min(100, 98) = 98(R-P3)。",
    input=bars_input(WL, [(2, "BUY")], _CW, want=_WF),
    expect=full_expect(WL, [trade(3, +1, 100.0, 0.0, 6, 95.0, 0.0)], _CW, 60, _WF), judge=J(*_WF),
    more_controls=[{"input": bars_input(WL, [(2, "BUY")], _CWP, want=_WF),
                    "expect": full_expect(WL, [trade(3, +1, 100.0, 0.0, 4, 98.0, 0.0)], _CWP, 60, _WF), "judge": J(*_WF)}],
    variant=bars_input(WL, [(2, "BUY")], cfg(stop_mode="wick_invalidation", stop_window_bars=3, stop_loss_pct=2.0), want=_WF))

# --------------------------------------------------------------------------- I4-12 maker take-profit exit
K = mk_bars([(100, 100.5, 99.5, 100), (100, 103, 99.5, 101), (101, 102, 100, 101.5), (101.5, 102.5, 101, 102),
             (102, 102.5, 101, 102)])
_CK = cfg(costs={**ZERO, "taker_fee_pct": 0.1, "maker_fee_pct": 0.02}, exit_execution="maker_tp", maker_tp_pct=2.0)
add(id="i4-12-maker-tp", viewpoint="I4-12", kind="値",
    what="建値から maker_tp_pct 離れた利確の指値が、建てた足では判定されず、触れただけでは約定せず、厳密な通過で水準の値・maker 手数料で約定するか",
    how="K の足。BUY@0 → 足 1 の始値 100(taker 0.1%)。水準 102。足 1 の高値 103 は建てた足なので見ない(R-X2)、足 2 の高値 102 は"
        "触れただけ、足 3 の高値 102.5 > 102 で 102、maker 0.02%(R-X1)。",
    input=bars_input(K, [(0, "BUY")], _CK, want=_WFP),
    expect=full_expect(K, [trade(1, +1, 100.0, 0.1, 3, 102.0, 0.02)], _CK, 60, _WFP),
    judge=J(*_WFP))
add(id="i4-12-refuse", viewpoint="I4-12", kind="能力",
    what="maker の利確を選んで率を与えない(0)設定を拒むか(対照: 率 2% なら通り、答えは i4-12-maker-tp)",
    how="R-X3「maker_tp は maker_tp_pct > 0 を要する」。",
    input=bars_input(K, [(0, "BUY")], _CK, want=_WFP),
    expect=full_expect(K, [trade(1, +1, 100.0, 0.1, 3, 102.0, 0.02)], _CK, 60, _WFP), judge=J(*_WFP),
    variant=bars_input(K, [(0, "BUY")], cfg(costs=_CK["costs"], exit_execution="maker_tp", maker_tp_pct=0.0), want=_WFP))

KD = mk_bars([(100, 100.5, 99.5, 100), (100, 101, 99.5, 100.5), (100.5, 101.5, 100, 101), (101, 101.6, 100.5, 101.2),
              (101.2, 101.5, 101, 101.2)])
_CKD = cfg(exit_execution="maker_tp", maker_tp_pct=1.5)
add(id="i4-12-touch-decimal", viewpoint="I4-12", kind="値",
    what="利確の水準を書かれた 10 進の値どおりに比べるか: 建値 100・率 1.5% の水準 101.5 に高値 101.5 がちょうど触れた足では約定しないか",
    how="KD の足、費用 0。BUY@0 → 足 1 の始値 100。水準 = 100 x (1 + 1.5/100) = 101.5(10 進で割り切れる)。足 2 の高値 101.5 は触れただけ"
        "(R-X1)、足 3 の高値 101.6 > 101.5 で 101.5 で約定。2 進の浮動小数で 100 x 1.015 = 101.49999999999999 と置くと、足 2 の高値が"
        "水準を上回ったことになり 1 本早く約定する(互換の計算 L-4)。",
    input=bars_input(KD, [(0, "BUY")], _CKD, want=_WF),
    expect=full_expect(KD, [trade(1, +1, 100.0, 0.0, 3, 101.5, 0.0)], _CKD, 60, _WF), judge=J(*_WF))

# --------------------------------------------------------------------------- I4-13 max hold bars
H = mk_bars([(100, 100.5, 99.5, 100), (100, 101, 99.5, 100.5), (101, 102, 100.5, 101.5), (102, 103, 101.5, 102.5),
             (103, 104, 102.5, 103.5), (104, 105, 103.5, 104.5)])
_CH = cfg(max_hold_bars=3, allow_short=True)
add(id="i4-13-time-exit", viewpoint="I4-13", kind="値",
    what="足 b で建てた建玉が、ちょうど足 b + N の始値で taker で閉じられ、その足に待っていた合図は捨てられるか",
    how="H の足、N = 3。BUY@0 → 足 1 の始値 100。足 4 の始値 103 で時間切れで閉じる(R-H1)。SELL@3 は足 4 に待つ合図だが捨てられる"
        "(R-H2。捨てなければショートを許しているので足 4 で売り建てになる)。",
    input=bars_input(H, [(0, "BUY"), (3, "SELL")], _CH, want=_WF),
    expect=full_expect(H, [trade(1, +1, 100.0, 0.0, 4, 103.0, 0.0)], _CH, 60, _WF),
    judge=J(*_WF))
HT = mk_bars([(100, 100.5, 99.5, 100), (100, 101, 99.5, 100.5), (100.5, 101.8, 100, 101.5), (101, 103, 100.5, 102.5),
              (102.5, 103, 102, 102.5)])
_CHT = cfg(costs={**ZERO, "taker_fee_pct": 0.1, "maker_fee_pct": 0.1}, max_hold_bars=2, take_profit_pct=2.0)
_HT_SPEC = [trade(1, +1, 100.0, 0.1, 3, 101.0, 0.1)]    # R-H1: closed at bar 3's OPEN 101, taker
_HT_LEGACY = [trade(1, +1, 100.0, 0.1, 3, 102.0, 0.1)]   # L-1: the take-profit of bar 3 is taken before the time exit
add(id="i4-13-tp-on-exit-bar", viewpoint="I4-13", kind="値",
    what="時間切れの足(足 b + N)に利確の水準も通るとき、仕様どおり足 b + N の始値で閉じるか(始値の時間切れは範囲の利確より先)",
    how="HT の足、N = 2、利確 2%(水準 102)。BUY@0 → 足 1 の始値 100。足 3 の始値 101 で時間切れ(R-H1)。始値の出来事は範囲の出来事より"
        "先(R-O1)で、利確は時間切れより先に取らない(R-H3)ので、足 3 の高値 103 > 102 の利確は取らない。手数料は maker・taker とも 0.1%。"
        "損益 = 30 - 30 x 101 x 0.001 - 3 = 23.97。",
    input=bars_input(HT, [(0, "BUY")], _CHT, want=_WFP),
    expect=full_expect(HT, _HT_SPEC, _CHT, 60, _WFP), judge=J(*_WFP))
add(id="i4-13-two-models", viewpoint="I4-13", kind="能力",
    what="1 つの戦略の記述から、互換の出力(同じ足で利確を時間切れより先に取る既存の計算 L-1)と仕様の出力(R-H1)の両方を出せるか",
    how="互換の答え = 足 3 で利確の水準 102・maker 0.1%(損益 60 - 3.06 - 3 = 53.94)、仕様の答え = i4-13-tp-on-exit-bar。",
    input=bars_input(HT, [(0, "BUY")], _CHT, want=_WFP, model=["legacy", "spec"]),
    expect={"legacy": full_expect(HT, _HT_LEGACY, _CHT, 60, _WFP), "spec": full_expect(HT, _HT_SPEC, _CHT, 60, _WFP)},
    judge={"legacy": J(*_WFP), "spec": J(*_WFP)})

# --------------------------------------------------------------------------- I4-14 entry mask / entry sides
_MASK = [True, True, False, True, False, False, True, True, True, True]
_CMK = cfg(allow_short=True, entry_sides="long", entry_mask=_MASK)
add(id="i4-14-mask-sides", viewpoint="I4-14", kind="値",
    what="建てるかどうかを合図の足のマスクと向きの制限で決め、約定の足のマスクは見ず、手仕舞いはどちらにも止められないか",
    how="B の足、費用 0、向き long、マスク " + str(_MASK) + "。SELL@0 は向きで止まる、BUY@2 はマスク[2] = False で止まる、BUY@3 は"
        "マスク[3] = True で足 4 の始値 125 で建つ(約定の足 4 のマスク False は見ない)、SELL@5 は手仕舞いなのでマスク[5] = False でも"
        "足 6 の始値 105 で閉じる、SELL@6 は建玉なしで向きで止まる(R-E1〜R-E3)。",
    input=bars_input(B, [(0, "SELL"), (2, "BUY"), (3, "BUY"), (5, "SELL"), (6, "SELL")], _CMK, want=_WF),
    expect=full_expect(B, [trade(4, +1, 125.0, 0.0, 6, 105.0, 0.0)], _CMK, 60, _WF),
    judge=J(*_WF))
_CSS = cfg(allow_short=True, entry_sides="short")
add(id="i4-14-sides-short", viewpoint="I4-14", kind="値",
    what="向き short のとき、建玉なしの BUY は建てず、SELL で売り建て、BUY で買い戻せるか",
    how="B の足、費用 0。BUY@1 は向きで止まる(R-E1)、SELL@2 → 足 3 の始値 120、BUY@5 → 足 6 の始値 105 で買い戻す(R-E3)。",
    input=bars_input(B, [(1, "BUY"), (2, "SELL"), (5, "BUY")], _CSS, want=_WF),
    expect=full_expect(B, [trade(3, -1, 120.0, 0.0, 6, 105.0, 0.0)], _CSS, 60, _WF),
    judge=J(*_WF))

# --------------------------------------------------------------------------- I4-15 swap / carry
# (bar 0 is a flat bar so that no signal falls on bar 0: a common bar tool never calls its strategy on the first bar,
#  and the first bar is not what I4-15 / I4-17 measure -- i4-r1-05)
SW = mk_bars([(100, 100.5, 99.5, 100), (100, 100.5, 99.5, 100), (100, 101.5, 99.5, 101), (101, 102.5, 100.5, 102),
              (102, 103.5, 101.5, 103), (104, 104.5, 103.5, 104), (104, 104.5, 103.5, 104)], bar_seconds=3600)
_CSW = cfg(swap_daily_pct=0.24)
add(id="i4-15-swap-long", viewpoint="I4-15", kind="値",
    what="建玉の間、足ごとに |数量| x 前の足の終値 x 日率 x (足の秒 / 86400) の持ち越しが建玉の損益と資産に掛かるか",
    how="SW の足(1 時間足)、日率 0.24% → 1 本 0.0001。BUY@1 → 足 2 の始値 100(数量 30)、SELL@4 → 足 5 の始値 104。持ち越しは足 3・4・5 に"
        "30 x (101 + 102 + 103) x 0.0001 = 0.918(R-S1)。損益 = 120 - 0.918 = 119.082。",
    input=bars_input(SW, [(1, "BUY"), (4, "SELL")], _CSW, bar_seconds=3600, want=_W3),
    expect=full_expect(SW, [trade(2, +1, 100.0, 0.0, 5, 104.0, 0.0)], _CSW, 3600, _W3),
    judge=J(*_W3))
_CSWS = cfg(swap_daily_pct=0.24, allow_short=True)
add(id="i4-15-swap-short", viewpoint="I4-15", kind="値",
    what="売り建てにも同じ持ち越しが掛かる(数量の絶対値で費用として引く)か",
    how="SW の足。SELL@1 → 足 2 の始値 100 の売り、BUY@4 → 足 5 の始値 104。持ち越し 0.918(R-S1)。損益 = -120 - 0.918 = -120.918。",
    input=bars_input(SW, [(1, "SELL"), (4, "BUY")], _CSWS, bar_seconds=3600, want=_W3),
    expect=full_expect(SW, [trade(2, -1, 100.0, 0.0, 5, 104.0, 0.0)], _CSWS, 3600, _W3),
    judge=J(*_W3))

# --------------------------------------------------------------------------- I4-16 missed fills
MF = mk_bars([(100, 101, 99, 100), (100, 101.5, 100, 101), (101, 102, 101, 101.5), (101.5, 102, 101.2, 101.8),
              (101.8, 102, 98.8, 99), (99.5, 100.2, 99.2, 100), (100, 100.8, 99.8, 100.5), (100.5, 100.8, 99.4, 99.5),
              (99.5, 99.8, 99.2, 99.6), (99.6, 100, 99.4, 99.8)])
_CMF = cfg(execution="maker", maker_timeout_bars=2, allow_short=True)
add(id="i4-16-missed", viewpoint="I4-16", kind="値",
    what="約定しなかった指値を、時間切れの取消と反対向きの合図による置き換えの 2 つの条件で数えるか",
    how="MF の足、寿命 2 本。BUY@1 → 指値 101。足 2 の安値 101 は触れただけ、足 3 は届かず、足 3 で 3 - 1 = 2 >= 2 → 取消 1 件目(R-M2)。"
        "BUY@4 → 指値 99(足 4 の終値)、足 5 の安値 99.2 は届かない。SELL@5(建玉なし、ショート可)が反対向きなので BUY の指値を置き換え"
        " 2 件目(R-M3)、売りの指値 100。足 6 の高値 100.8 > 100 で売り建て 100。CLOSE@7 → 買い戻しの指値 99.5、足 8 の安値 99.2 < 99.5 で"
        " 99.5(R-M1・R-M4)。",
    input=bars_input(MF, [(1, "BUY"), (4, "BUY"), (5, "SELL"), (7, "CLOSE")], _CMF, want=_WFM),
    expect=full_expect(MF, [trade(6, -1, 100.0, 0.0, 8, 99.5, 0.0)], _CMF, 60, _WFM, missed=2),
    judge=J(*_WFM))

# --------------------------------------------------------------------------- the maker path of the mask and of a same-side
# signal (i4-r2-08: R-E4 and R-M6; the values are the lead's decision in the finishing delegation §1 i4-r2-08)
_MKM = [True, False, True, True, True, True]
MKA = mk_bars([(100, 100.5, 99.8, 100), (100, 100.5, 99.8, 100), (100, 100.5, 99.5, 100), (100, 100.5, 99.8, 100),
               (100, 100.5, 99.5, 99.8), (99.8, 100.2, 99.6, 100)])
MKB = mk_bars([(100, 100.5, 99.8, 100), (100, 100.5, 99.8, 100), (100, 100.8, 100, 100.5), (100.5, 101, 100.2, 100.8),
               (100.8, 101.2, 100.4, 101), (101, 101.5, 100.6, 101.2)])
_CMKM = cfg(execution="maker", maker_timeout_bars=3, entry_mask=_MKM)
add(id="i4-14-maker-mask-false", viewpoint="I4-14", kind="値",
    what="maker の執行で、合図の足のマスクが False の建ての合図は指値を置かず(後の足が厳密に通過しても建たない)、マスクが True の合図の"
         "指値は置かれて約定するか(R-E2・R-E4)",
    how="MKA の足、maker、寿命 3、マスク " + str(_MKM) + "、費用 0。BUY@1 はマスク[1] = False → 指値を置かない(足 2 の安値 99.5 < 100 でも"
        "建たない。R-E4)。BUY@3 はマスク[3] = True → 指値 100(足 3 の終値)、足 4 の安値 99.5 < 100 で 100 で建つ(R-M1)。取り逃し 0(R-E4・R-M5)。",
    input=bars_input(MKA, [(1, "BUY"), (3, "BUY")], _CMKM, want=_WFM),
    expect=full_expect(MKA, [trade(4, +1, 100.0, 0.0)], _CMKM, 60, _WFM, missed=0),
    judge=J(*_WFM))
add(id="i4-16-maker-mask-false-not-missed", viewpoint="I4-16", kind="値",
    what="maker の執行で、マスクが False の合図は指値を置かないので、後の足が指値の値を厳密に通過しない並びでも取り逃しに数えないか"
         "(取り逃しの数が値の道筋で変わらない。R-E4・R-M5)",
    how="MKB の足、maker、寿命 3、マスク " + str(_MKM) + "、費用 0。BUY@1 はマスク[1] = False → 指値を置かない。足 2〜5 の安値は 100 を"
        "厳密に下回らない(足 2 は 100 に触れただけ)。約定 0、取り逃し 0(置いていない指値は R-M2 の寿命の取消にならない)。",
    input=bars_input(MKB, [(1, "BUY")], _CMKM, want=_WFM),
    expect=full_expect(MKB, [], _CMKM, 60, _WFM, missed=0),
    judge=J(*_WFM))
add(id="i4-16-maker-mask-false-two-models", viewpoint="I4-16", kind="能力",
    what="1 つの戦略の記述から、互換の出力(マスクが False の合図にも指値を置き、寿命で取り消して取り逃しに数える既存の計算 L-6)と"
         "仕様の出力(R-E4)の両方を出せるか",
    how="i4-16-maker-mask-false-not-missed と同じ入力。互換の答え = 約定 0・取り逃し 1(指値 100 を足 1 に置き、足 4 で 4 - 1 = 3 >= 3 で取消。"
        "L-6)。仕様の答え = 約定 0・取り逃し 0。",
    input=bars_input(MKB, [(1, "BUY")], _CMKM, want=_WFM, model=["legacy", "spec"]),
    expect={"legacy": full_expect(MKB, [], _CMKM, 60, _WFM, missed=1), "spec": full_expect(MKB, [], _CMKM, 60, _WFM, missed=0)},
    judge={"legacy": J(*_WFM), "spec": J(*_WFM)})
SSL = mk_bars([(100, 100.5, 99.8, 100), (100, 100.5, 99.8, 100), (100, 101.5, 100, 101), (101, 101.5, 100.5, 101),
               (101, 101.5, 99.5, 100), (100, 100.5, 99.8, 100)])
_CSSL = cfg(execution="maker", maker_timeout_bars=5)
add(id="i4-16-same-side-keeps-limit", viewpoint="I4-16", kind="値",
    what="maker の執行で、建ての指値が待っている間に同じ向きの合図が来ても、指値を置き直さず古い指値(値と置いた足)を残し、"
         "取り逃しに数えないか(R-M6・R-M5)",
    how="SSL の足、maker、寿命 5、費用 0。BUY@1 → 指値 100(足 1 の終値)。足 2 の安値 100 は触れただけ。BUY@2 は同じ向き → 置き直さない"
        "(指値は 100 のまま、置いた足は 1)。足 3 の安値 100.5 は 100 を通過しない。足 4 の安値 99.5 < 100 で 100 で建つ(4 - 1 = 3 <= 5)。"
        "取り逃し 0。",
    input=bars_input(SSL, [(1, "BUY"), (2, "BUY")], _CSSL, want=_WFM),
    expect=full_expect(SSL, [trade(4, +1, 100.0, 0.0)], _CSSL, 60, _WFM, missed=0),
    judge=J(*_WFM))
add(id="i4-16-same-side-two-models", viewpoint="I4-16", kind="能力",
    what="1 つの戦略の記述から、互換の出力(同じ向きの合図で指値を新しい足の終値に置き直す既存の計算 L-7)と仕様の出力(R-M6)の両方を"
         "出せるか",
    how="i4-16-same-side-keeps-limit と同じ入力。互換の答え = BUY@2 で指値を 101(足 2 の終値)に置き直し、足 3 の安値 100.5 < 101 で 101 で"
        "建つ(取り逃しに数えない。L-7)。仕様の答え = 足 4 で 100。",
    input=bars_input(SSL, [(1, "BUY"), (2, "BUY")], _CSSL, want=_WFM, model=["legacy", "spec"]),
    expect={"legacy": full_expect(SSL, [trade(3, +1, 101.0, 0.0)], _CSSL, 60, _WFM, missed=0),
            "spec": full_expect(SSL, [trade(4, +1, 100.0, 0.0)], _CSSL, 60, _WFM, missed=0)},
    judge={"legacy": J(*_WFM), "spec": J(*_WFM)})

_MKO = [True, True, False, True, True]
MKO = mk_bars([(100, 100.5, 99.8, 100), (100, 100.5, 99.8, 100), (100, 100.8, 100, 100.5), (100.5, 101, 99.5, 100),
               (100, 100.5, 99.8, 100)])
_CMKO = cfg(execution="maker", maker_timeout_bars=5, allow_short=True, entry_mask=_MKO)
add(id="i4-16-mask-false-opposite-keeps-limit", viewpoint="I4-16", kind="値",
    what="maker の執行で、待っている建ての指値に、マスクが False の反対向きの合図が来ても、指値を置き換えず古い指値を残し、取り逃しに"
         "数えないか(R-E4 が R-M3 より先。R-M3 の置き換えは有効な合図のときだけ)",
    how="MKO の足、maker、寿命 5、ショート可、マスク " + str(_MKO) + "、費用 0。BUY@1 → 指値 100(足 1 の終値)。足 2 の安値 100 は触れただけ。"
        "SELL@2 はマスク[2] = False → 何もしない(R-E4。置き換えない)。足 3 の安値 99.5 < 100 で 100 で買い建て(3 - 1 = 2 <= 5)。取り逃し 0。",
    input=bars_input(MKO, [(1, "BUY"), (2, "SELL")], _CMKO, want=_WFM),
    expect=full_expect(MKO, [trade(3, +1, 100.0, 0.0)], _CMKO, 60, _WFM, missed=0),
    judge=J(*_WFM))
add(id="i4-16-mask-false-opposite-two-models", viewpoint="I4-16", kind="能力",
    what="1 つの戦略の記述から、互換の出力(マスクが False の反対向きの合図でも待っている指値を置き換えて取り逃しに数え、置き換えた指値は"
         "通過しても建てない既存の計算 L-8)と仕様の出力(R-E4)の両方を出せるか",
    how="i4-16-mask-false-opposite-keeps-limit と同じ入力。互換の答え = SELL@2 で買いの指値 100 を売りの指値 100.5(足 2 の終値)に置き換えて"
        "取り逃し 1、足 3 の高値 101 > 100.5 で通過するがマスク[2] = False なので建てずに消す(L-8)→ 約定 0・取り逃し 1。"
        "仕様の答え = 足 3 で 100 の買い建て・取り逃し 0。",
    input=bars_input(MKO, [(1, "BUY"), (2, "SELL")], _CMKO, want=_WFM, model=["legacy", "spec"]),
    expect={"legacy": full_expect(MKO, [], _CMKO, 60, _WFM, missed=1),
            "spec": full_expect(MKO, [trade(3, +1, 100.0, 0.0)], _CMKO, 60, _WFM, missed=0)},
    judge={"legacy": J(*_WFM), "spec": J(*_WFM)})

# --------------------------------------------------------------------------- the reference's literal readings U1-U8
# (finishing delegation, stage 2: the points the rule text left open that the independent reference read literally; the
#  lead took those readings as the rule text: R-W5, R-M7, R-W6, R-E5, R-V1, R-V2, R-V3, R-V4 in DEFINITIONS.md)
WS = mk_bars([(100, 100.5, 99, 100), (100, 100.5, 99.5, 100), (100, 101, 99.8, 100.5), (100.5, 101, 98.5, 98.8),
              (98.7, 99, 98.5, 98.8), (98.8, 99.2, 98.6, 99)])
_CWS = cfg(stop_mode="wick_invalidation", stop_window_bars=3)
add(id="i4-11-wick-short-history", viewpoint="I4-11", kind="値",
    what="構造的な逆指値の窓で、約定の足の前の完了した足が N 本無いとき、有る分の足で水準を決めるか(R-W5)",
    how="WS の足、窓 N = 3、費用 0。BUY@1 → 足 2 の始値 100。足 2 の前の完了した足は 0・1 の 2 本だけ → 水準 = min(99, 99.5) = 99(R-W5)。"
        "足 3 の終値 98.8 < 99 → 足 4 の始値 98.7 で出る(R-W3)。",
    input=bars_input(WS, [(1, "BUY")], _CWS, want=_WF),
    expect=full_expect(WS, [trade(2, +1, 100.0, 0.0, 4, 98.7, 0.0)], _CWS, 60, _WF), judge=J(*_WF))
WE = mk_bars([(100, 100.5, 99.5, 100), (100, 100.5, 99.6, 100), (100, 100.5, 99, 99.2), (99.2, 99.5, 99, 99.3),
              (99.3, 99.5, 99.1, 99.3)])
_CWE = cfg(stop_mode="wick_invalidation", stop_window_bars=2)
add(id="i4-11-wick-entry-bar-close", viewpoint="I4-11", kind="値",
    what="構造的な逆指値で、建てた足自身の終値が水準を越えたとき、次の足の始値で出るか(R-W6)",
    how="WE の足、窓 N = 2、費用 0。BUY@1 → 足 2 の始値 100。水準 = min(99.5, 99.6) = 99.5。建てた足 2 の終値 99.2 < 99.5 → 足 3 の始値 99.2 で"
        "出る(R-W6: 建てた足の終値も判定に入れる)。",
    input=bars_input(WE, [(1, "BUY")], _CWE, want=_WF),
    expect=full_expect(WE, [trade(2, +1, 100.0, 0.0, 3, 99.2, 0.0)], _CWE, 60, _WF), judge=J(*_WF))
XS = mk_bars([(100, 100.5, 99.8, 100), (100, 100.5, 99.8, 100), (100, 100.5, 99.5, 100.5), (100.5, 101, 100.2, 101),
              (101, 101, 100.6, 100.8), (100.8, 100.9, 100.5, 100.7), (100.7, 101.5, 100.6, 101.2), (101.2, 101.5, 101, 101.2)])
_CXS = cfg(execution="maker", maker_timeout_bars=5)
add(id="i4-16-exit-same-side-keeps-limit", viewpoint="I4-16", kind="値",
    what="maker の執行で、決済の指値が待っている間に同じ向きの合図が来ても、指値を置き直さず古い指値を残すか(R-M7)",
    how="XS の足、maker、寿命 5、費用 0。BUY@1 → 指値 100、足 2 の安値 99.5 < 100 で 100 で建つ。SELL@3 → 決済の指値 101(足 3 の終値)。"
        "足 4 の高値 101 は触れただけ。SELL@4 は同じ向き → 置き直さない(R-M7。置き直せば 100.8)。足 5 の高値 100.9 は 101 に届かない。"
        "足 6 の高値 101.5 > 101 で 101 で決済(maker、6 - 3 = 3 <= 5)。取り逃し 0。",
    input=bars_input(XS, [(1, "BUY"), (3, "SELL"), (4, "SELL")], _CXS, want=_WFM),
    expect=full_expect(XS, [trade(2, +1, 100.0, 0.0, 6, 101.0, 0.0)], _CXS, 60, _WFM, missed=0), judge=J(*_WFM))
add(id="i4-16-exit-same-side-two-models", viewpoint="I4-16", kind="能力",
    what="1 つの戦略の記述から、互換の出力(同じ向きの合図で決済の指値を新しい足の終値に置き直す既存の計算 L-7)と仕様の出力(R-M7)の"
         "両方を出せるか",
    how="i4-16-exit-same-side-keeps-limit と同じ入力。互換の答え = SELL@4 で決済の指値を 100.8(足 4 の終値)に置き直し、足 5 の高値 100.9 > 100.8"
        "で 100.8 で決済(L-7)。仕様の答え = 足 6 で 101。",
    input=bars_input(XS, [(1, "BUY"), (3, "SELL"), (4, "SELL")], _CXS, want=_WFM, model=["legacy", "spec"]),
    expect={"legacy": full_expect(XS, [trade(2, +1, 100.0, 0.0, 5, 100.8, 0.0)], _CXS, 60, _WFM, missed=0),
            "spec": full_expect(XS, [trade(2, +1, 100.0, 0.0, 6, 101.0, 0.0)], _CXS, 60, _WFM, missed=0)},
    judge={"legacy": J(*_WFM), "spec": J(*_WFM)})
_CBN = cfg(execution="maker", maker_timeout_bars=5, allow_short=False)
add(id="i4-14-blocked-opposite-keeps-limit", viewpoint="I4-14", kind="値",
    what="maker の執行で、待っている建ての指値に、空売り不可で建てを止められた反対向きの合図が来ても、古い指値を残すか(R-E5)",
    how="MKO の足、maker、寿命 5、ショート不可、費用 0。BUY@1 → 指値 100。SELL@2 は建玉なし・ショート不可で止まる(R-T4)→ 指値を置かず、"
        "古い指値を残す(R-E5)。足 3 の安値 99.5 < 100 で 100 で買い建て。取り逃し 0。",
    input=bars_input(MKO, [(1, "BUY"), (2, "SELL")], _CBN, want=_WFM),
    expect=full_expect(MKO, [trade(3, +1, 100.0, 0.0)], _CBN, 60, _WFM, missed=0), judge=J(*_WFM))
_CBL = cfg(execution="maker", maker_timeout_bars=5, allow_short=True, entry_sides="long")
add(id="i4-14-sides-opposite-keeps-limit", viewpoint="I4-14", kind="値",
    what="maker の執行で、待っている建ての指値に、向きの制限(long)で建てを止められた反対向きの合図が来ても、古い指値を残すか(R-E5)",
    how="MKO の足、maker、寿命 5、ショート可、向き long、費用 0。BUY@1 → 指値 100。SELL@2 は建玉なし・向き long で止まる(R-E1)→ 指値を"
        "置かず、古い指値を残す(R-E5)。足 3 の安値 99.5 < 100 で 100 で買い建て。取り逃し 0。",
    input=bars_input(MKO, [(1, "BUY"), (2, "SELL")], _CBL, want=_WFM),
    expect=full_expect(MKO, [trade(3, +1, 100.0, 0.0)], _CBL, 60, _WFM, missed=0), judge=J(*_WFM))
add(id="i4-14-sides-opposite-two-models", viewpoint="I4-14", kind="能力",
    what="1 つの戦略の記述から、互換の出力(向きで止められる反対向きの合図でも指値を置き換えて取り逃しに数え、置き換えた指値は通過しても"
         "建てない既存の計算 L-8)と仕様の出力(R-E5)の両方を出せるか",
    how="i4-14-sides-opposite-keeps-limit と同じ入力。互換の答え = SELL@2 で売りの指値 100.5 に置き換えて取り逃し 1、足 3 の高値 101 > 100.5 で"
        "通過するが向き long で建てずに消す → 約定 0・取り逃し 1。仕様の答え = 足 3 で 100 の買い建て・取り逃し 0。",
    input=bars_input(MKO, [(1, "BUY"), (2, "SELL")], _CBL, want=_WFM, model=["legacy", "spec"]),
    expect={"legacy": full_expect(MKO, [], _CBL, 60, _WFM, missed=1),
            "spec": full_expect(MKO, [trade(3, +1, 100.0, 0.0)], _CBL, 60, _WFM, missed=0)},
    judge={"legacy": J(*_WFM), "spec": J(*_WFM)})
BADB = mk_bars([(100, 100.5, 99.5, 100), (100, 100.5, 99.5, 100), (100, 101, 99.5, 100.5), (100.5, 102, 100, 101.8),
                (101.8, 102, 101.5, 101.8)])
BADV = [dict(b) for b in BADB]
BADV[3]["high"] = 101.5    # high 101.5 < close 101.8: the range does not hold the close
_CV = cfg()
add(id="i4-8-refuse-bad-bar", viewpoint="I4-8", kind="値",
    what="高値・安値が始値・終値を囲まない足を拒むか(R-V1。対照: 同じ足の列で高値が終値を囲めば通る)",
    how="BADB の足、費用 0。BUY@1 → 足 2 の始値 100、SELL@3 → 足 4 の始値 101.8。拒む版は足 3 の高値を 101.5(終値 101.8 より下)にした。",
    input=bars_input(BADB, [(1, "BUY"), (3, "SELL")], _CV, want=_WF),
    expect=full_expect(BADB, [trade(2, +1, 100.0, 0.0, 4, 101.8, 0.0)], _CV, 60, _WF), judge=J(*_WF),
    variant=bars_input(BADV, [(1, "BUY"), (3, "SELL")], _CV, want=_WF))
_CN0 = cfg(stop_loss_pct=None)
add(id="i4-10-zero-rate-refused", viewpoint="I4-10", kind="値",
    what="「使わない」を null で表し、逆指値の率 0 を拒むか(R-V2。対照: null なら逆指値なしで通り、2% なら逆指値で出る)",
    how="WL の足、費用 0。対照 1(逆指値 null): BUY@2 → 足 3 の始値 100、SELL@5 → 足 6 の始値 95。対照 2(2%): 足 4 の安値で min(100, 98) = 98"
        "(R-P3。i4-11-refuse-stack の対照 2 と同じ)。拒む版は逆指値の率 0。",
    input=bars_input(WL, [(2, "BUY"), (5, "SELL")], _CN0, want=_WF),
    expect=full_expect(WL, [trade(3, +1, 100.0, 0.0, 6, 95.0, 0.0)], _CN0, 60, _WF), judge=J(*_WF),
    more_controls=[{"input": bars_input(WL, [(2, "BUY")], _CWP, want=_WF),
                    "expect": full_expect(WL, [trade(3, +1, 100.0, 0.0, 4, 98.0, 0.0)], _CWP, 60, _WF), "judge": J(*_WF)}],
    variant=bars_input(WL, [(2, "BUY"), (5, "SELL")], cfg(stop_loss_pct=0.0), want=_WF))
_CNEG = cfg(costs={**ZERO, "taker_fee_pct": -0.02})
add(id="i4-8-negative-fee", viewpoint="I4-8", kind="値",
    what="負の手数料の率(払い戻し)を受け、式どおりに計算するか(R-V3)",
    how="BADB の足、taker の率 -0.02%(taker だけの経路)。BUY@1 → 足 2 の始値 100(数量 30、手数料 30 x 100 x -0.0002 = -0.6)、SELL@3 → 足 4 の始値 101.8"
        "(手数料 30 x 101.8 x -0.0002 = -0.6108)。損益 = 54 + 0.6108 + 0.6 = 55.2108(R-A2・R-A3)。",
    input=bars_input(BADB, [(1, "BUY"), (3, "SELL")], _CNEG, want=_WFP),
    expect=full_expect(BADB, [trade(2, +1, 100.0, -0.02, 4, 101.8, -0.02)], _CNEG, 60, _WFP), judge=J(*_WFP))
_CT1 = cfg(execution="maker", maker_timeout_bars=1)
add(id="i4-16-zero-timeout-refused", viewpoint="I4-16", kind="値",
    what="指値の寿命 0 を拒むか(R-V4。対照: 寿命 1 なら置いた次の足だけ待つ)",
    how="MKA の足、maker、費用 0。対照(寿命 1): BUY@1 → 指値 100、足 2 の安値 99.5 < 100 で 100 で建つ(2 - 1 = 1 <= 1)。拒む版は寿命 0。",
    input=bars_input(MKA, [(1, "BUY")], _CT1, want=_WFM),
    expect=full_expect(MKA, [trade(2, +1, 100.0, 0.0)], _CT1, 60, _WFM, missed=0), judge=J(*_WFM),
    variant=bars_input(MKA, [(1, "BUY")], cfg(execution="maker", maker_timeout_bars=0), want=_WFM))

# --------------------------------------------------------------------------- I4-17 metrics
_P17 = [120.0, -40.0, -5.0, 0.0, -30.0, 80.0, -10.0]
_E17 = [6000.0, 6120.0, 6080.0, 6075.0, 6075.0, 6045.0, 6125.0, 6115.0]
add(id="i4-17-metrics", viewpoint="I4-17", kind="値",
    what="決済ごとの損益と資産の推移から 12 の指標が式どおりに出るか(損益 0 の決済は勝ちでも負けでもなく、連敗を切る)",
    how="手の計算: 総損益 115、7 回、勝ち 2(120, 80)で勝率 200/7 %、PF = 200/85、平均勝ち 100、平均負け -85/4 = -21.25、RR = 100/21.25、"
        "期待値 115/7、最大連敗 2(-40, -5 のあと 0 で切れる)、最大下落 = (6120 - 6045)/6120 x 100、シャープ = 資産の足ごとの変化率の平均 / "
        "標本標準偏差 x sqrt(525600)(M-5)、手数料 12.5 はそのまま。",
    input={"op": "metrics", "trade_pnls": _P17, "equity": _E17, "total_fees": 12.5, "periods_per_year": 525600.0},
    expect={"metrics": metrics_of(_P17, _E17, 12.5, 525600.0)}, judge={"metrics": True})
add(id="i4-17-metrics-edge", viewpoint="I4-17", kind="値",
    what="負けの無い損益と平らな資産の推移で、PF = 無限大・RR = 0・シャープ = 0・最大下落 = 0 になるか",
    how="手の計算: 損益 [50, 30] → 総 80、勝率 100、PF = 無限大(総損失 0 で総利益 > 0、M-4)、平均負け 0 で RR = 0(M-10)、"
        "資産 [6000, 6000, 6000] は変化率の標準偏差 0 でシャープ 0(M-5)、下落 0。",
    input={"op": "metrics", "trade_pnls": [50.0, 30.0], "equity": [6000.0, 6000.0, 6000.0], "total_fees": 0.0,
           "periods_per_year": 525600.0},
    expect={"metrics": metrics_of([50.0, 30.0], [6000.0, 6000.0, 6000.0], 0.0, 525600.0)}, judge={"metrics": True})
_W17 = ("fills", "pnls", "equity", "metrics")
_TR17 = [trade(2, +1, 100.0, 0.0, 5, 104.0, 0.0)]
add(id="i4-17-sharpe-bar-seconds", viewpoint="I4-17", kind="値",
    what="1 時間足のバックテストのシャープが、足の頻度で年率化される(1 年 = 8760 本)か",
    how="SW の足(1 時間足)、費用 0・持ち越し 0。BUY@1 → 足 2 の 100、SELL@4 → 足 5 の 104。資産の推移は R-A の式、シャープは M-5 で "
        "1 年の本数 = 365 x 86400 / 3600 = 8760。",
    input=bars_input(SW, [(1, "BUY"), (4, "SELL")], cfg(), bar_seconds=3600, want=_W17),
    expect=full_expect(SW, _TR17, cfg(), 3600, _W17), judge=J(*_W17))
add(id="i4-17-two-models", viewpoint="I4-17", kind="能力",
    what="1 つの戦略の記述から、互換の出力(足の頻度を見ず 1 年 = 525600 本で年率化する既存の計算 L-2)と仕様の出力(M-5)の両方を出せるか",
    how="互換の答え = シャープの年率化だけ sqrt(525600)、ほかは同じ。仕様の答え = i4-17-sharpe-bar-seconds。",
    input=bars_input(SW, [(1, "BUY"), (4, "SELL")], cfg(), bar_seconds=3600, want=_W17, model=["legacy", "spec"]),
    expect={"legacy": full_expect(SW, _TR17, cfg(), 3600, _W17, periods=525600.0),
            "spec": full_expect(SW, _TR17, cfg(), 3600, _W17)},
    judge={"legacy": J(*_W17), "spec": J(*_W17)})


# --------------------------------------------------------------------------- I4-18 split_data
def split_rows(n, train, val):
    """D-1: training = first floor(n x train) rows, validation up to floor(n x (train + val)), the rest out of sample,
    computed in exact decimal arithmetic (the fractions as written)."""
    tr, va = Fraction(str(train)), Fraction(str(val))
    a, b = math.floor(n * tr), math.floor(n * (tr + va))
    return {"training": list(range(0, a)), "validation": list(range(a, b)), "out_of_sample": list(range(b, n))}


D10 = mk_bars([(100 + i, 101 + i, 99 + i, 100 + i) for i in range(10)])
D100 = mk_bars([(100 + i % 7, 101 + i % 7, 99 + i % 7, 100 + i % 7) for i in range(100)])
add(id="i4-18-split", viewpoint="I4-18", kind="値",
    what="行の割合で、並べ替えず重ねず、学習 → 検証 → 検証外(末尾)の順に 3 つに分けるか",
    how="10 行、学習 0.6・検証 0.2 → 学習 行 0〜5、検証 行 6〜7、検証外 行 8〜9(D-1)。",
    input={"op": "split", "bars": D10, "train_frac": 0.6, "val_frac": 0.2},
    expect={"splits": split_rows(10, 0.6, 0.2)}, judge={"splits": True})
add(id="i4-18-split-decimal", viewpoint="I4-18", kind="値",
    what="割合を書かれた 10 進の値どおりに計算するか(100 行で 0.7 + 0.2 = 0.9 の境は 90)",
    how="100 行、学習 0.7・検証 0.2 → floor(100 x 0.7) = 70、floor(100 x 0.9) = 90 → 学習 0〜69、検証 70〜89、検証外 90〜99(D-1)。",
    input={"op": "split", "bars": D100, "train_frac": 0.7, "val_frac": 0.2},
    expect={"splits": split_rows(100, 0.7, 0.2)}, judge={"splits": True})
add(id="i4-18-two-models", viewpoint="I4-18", kind="能力",
    what="同じ分け方の記述から、互換の出力(2 進の浮動小数で割合を足してから掛けて切り捨てる既存の計算 L-3: 境が 89)と仕様の出力(D-1)の"
         "両方を出せるか",
    how="互換の答え = 学習 0〜69、検証 70〜88、検証外 89〜99(2 進の 0.7 + 0.2 = 0.8999999999999999、x 100 = 89.99999999999999、"
        "切り捨て 89)。仕様の答え = i4-18-split-decimal。",
    input={"op": "split", "bars": D100, "train_frac": 0.7, "val_frac": 0.2, "models": ["legacy", "spec"]},
    expect={"legacy": {"splits": {"training": list(range(70)), "validation": list(range(70, 89)),
                                  "out_of_sample": list(range(89, 100))}},
            "spec": {"splits": split_rows(100, 0.7, 0.2)}},
    judge={"legacy": {"splits": True}, "spec": {"splits": True}})
add(id="i4-18-refuse", viewpoint="I4-18", kind="能力",
    what="割合の和が 1 以上の分け方を拒むか(対照: 0.5・0.3 なら通る)",
    how="D-2「割合は (0,1) にあり、和は 1 未満」。対照 10 行 0.5・0.3 → 学習 0〜4、検証 5〜7、検証外 8〜9。",
    input={"op": "split", "bars": D10, "train_frac": 0.5, "val_frac": 0.3},
    expect={"splits": split_rows(10, 0.5, 0.3)}, judge={"splits": True},
    variant={"op": "split", "bars": D10, "train_frac": 0.6, "val_frac": 0.4})


# --------------------------------------------------------------------------- the order within one bar (R-O1 / L-5)
# One long position opened at bar 2's open 100 (taker: BUY@1; maker: BUY@1 places a limit at bar 1's close 100 and
# bar 2's low 99.5 < 100 fills it), size 3000 / 100 = 30, no cost.  Bar 3 reaches no level.  Bar 4 is where two or
# more exit events can happen (i4-r1-02): its open 101 lies strictly between the stop level 98 (2 %) and the
# take-profit levels 102.5 (maker take-profit 2.5 %) and 103 (take-profit 3 %).  Every hand-placed close below is
# checked against exit_events / winner / exit_fill by the scene-keeper's tests.
_RO = [(100, 100.5, 99.5, 100), (100, 100.5, 99.5, 100), (100, 101.5, 99.5, 101), (101, 102, 100, 101)]
X_ALL = (101, 104, 97, 98)       # bar 4 reaches the stop (low 97 <= 98) and trades through 102.5 and 103 (high 104)
X_UP = (101, 104, 100.5, 103.5)  # bar 4 trades through 102.5 and 103, not the stop
OA = mk_bars(_RO + [X_ALL, (98, 98.5, 97.5, 98)])
OU = mk_bars(_RO + [X_UP, (103.5, 104, 103, 103.5)])
_WO = ("fills",)                    # no cost, no carry: the PnL follows from the fills (a tool without per-trade
_WOM = ("fills", "missed_fills")     # PnLs is not stopped by a key the viewpoint does not need, i4-r1-05)


def _long(xb, xp):
    return [trade(2, +1, 100.0, 0.0, xb, xp, 0.0)]


_C_O1 = cfg(stop_loss_pct=2.0, take_profit_pct=3.0, exit_execution="maker_tp", maker_tp_pct=2.5)
add(id="i4-10-signal-first", viewpoint="I4-10", kind="値",
    what="足 j の始値に待つ決済の合図(R-T1)があり、同じ足 j の範囲が逆指値・利確・maker の利確の水準に届くとき、合図が足 j の始値で"
         "建玉を閉じ、その足の逆指値・利確は起きないか(始値は足の範囲より先: R-O1)",
    how="OA の足、逆指値 2%(98)・利確 3%(103)・maker の利確 2.5%(102.5)、費用 0。BUY@1 → 足 2 の始値 100。SELL@3 は足 4 の始値に待つ"
        "決済の合図。足 4 は始値 101・高値 104・安値 97 で、逆指値・利確・maker の利確の全部に届く。R-O1 で始値の合図が先 → 足 4 の始値 101 で"
        "決済(taker)。損益 = (101 - 100) x 30 = 30。",
    input=bars_input(OA, [(1, "BUY"), (3, "SELL")], _C_O1, want=_WO),
    expect=full_expect(OA, _long(4, 101.0), _C_O1, 60, _WO), judge=J(*_WO))
_OS = mk_bars([(100, 100.5, 99.5, 100), (100, 100.5, 99.5, 100), (100, 100.5, 98.5, 99), (99, 100, 98, 99),
               (99, 103, 96, 102), (102, 102.5, 101.5, 102)])
_C_O1S = cfg(stop_loss_pct=2.0, take_profit_pct=3.0, exit_execution="maker_tp", maker_tp_pct=2.5, allow_short=True)
add(id="i4-10-signal-first-short", viewpoint="I4-10", kind="値",
    what="売り建てでも、足 j の始値に待つ買い戻しの合図が、同じ足の範囲の逆指値・利確・maker の利確より先に足 j の始値で閉じるか",
    how="_OS の足、ショート可、逆指値 2%(102)・利確 3%(97)・maker の利確 2.5%(97.5)。SELL@1 → 足 2 の始値 100 の売り建て。足 3 は高値 100・"
        "安値 98 でどの水準にも届かない。BUY@3 は足 4 の始値に待つ買い戻し。足 4 は始値 99・高値 103(>= 102)・安値 96(< 97、< 97.5)。"
        "R-O1 → 足 4 の始値 99 で買い戻す(同じ足で買い建て直さない、R-T3)。損益 = (100 - 99) x 30 = 30。",
    input=bars_input(_OS, [(1, "SELL"), (3, "BUY")], _C_O1S, want=_WO),
    expect=full_expect(_OS, [trade(2, -1, 100.0, 0.0, 4, 99.0, 0.0)], _C_O1S, 60, _WO), judge=J(*_WO))
add(id="i4-10-signal-first-two-models", viewpoint="I4-10", kind="能力",
    what="1 つの戦略の記述から、互換の出力(待つ合図より範囲の逆指値を先に取り、合図を捨てる既存の計算 L-5)と仕様の出力(R-O1)の両方を出せるか",
    how="i4-10-signal-first と同じ足と設定で、決済の合図を CLOSE@3 にした。互換の答え = 足 4 の逆指値 min(101, 98) = 98(L-5: 範囲の逆指値が先、"
        "合図は捨てる)。仕様の答え = 足 4 の始値 101(R-O1)。",
    input=bars_input(OA, [(1, "BUY"), (3, "CLOSE")], _C_O1, want=_WO, model=["legacy", "spec"]),
    expect={"legacy": full_expect(OA, _long(4, 98.0), _C_O1, 60, _WO), "spec": full_expect(OA, _long(4, 101.0), _C_O1, 60, _WO)},
    judge={"legacy": J(*_WO), "spec": J(*_WO)})
_C_O2 = cfg(stop_loss_pct=2.0, take_profit_pct=3.0)
add(id="i4-10-stop-first-plain", viewpoint="I4-10", kind="値",
    what="費用 0・手数料の率 1 つ・足 0 に合図なしで、1 本の足が逆指値と利確の両方に届くとき逆指値が先か(観点の本題だけを求める最小の場面)",
    how="OA の足、逆指値 2%(98)・利確 3%(103)、費用 0。BUY@1 → 足 2 の始値 100。足 4 は安値 97 <= 98 かつ高値 104 > 103 → 逆指値が先"
        "(R-P3)、値 = min(始値 101, 98) = 98。損益 = -2 x 30 = -60。",
    input=bars_input(OA, [(1, "BUY")], _C_O2, want=_WO),
    expect=full_expect(OA, _long(4, 98.0), _C_O2, 60, _WO), judge=J(*_WO))
_C_O3 = cfg(take_profit_pct=3.0, exit_execution="maker_tp", maker_tp_pct=2.5)
add(id="i4-12-tp-before-maker-tp", viewpoint="I4-12", kind="値",
    what="率の利確と maker の利確の両方を置き、1 本の足が両方の水準を厳密に通過するとき、率の利確が先か(R-O1 の範囲の中の順)",
    how="OU の足、利確 3%(103)・maker の利確 2.5%(102.5)、費用 0。BUY@1 → 足 2 の始値 100。足 4 の高値 104 は 103 も 102.5 も厳密に通過"
        "(安値 100.5 は逆指値なし)→ R-O1 で利確が先、水準 103 で約定。損益 = 3 x 30 = 90。",
    input=bars_input(OU, [(1, "BUY")], _C_O3, want=_WO),
    expect=full_expect(OU, _long(4, 103.0), _C_O3, 60, _WO), judge=J(*_WO))
_OW = mk_bars([(100, 100.5, 99.5, 100), (100, 100.5, 99.5, 100), (100, 101.5, 99.5, 101), (101, 102, 99.2, 99.3),
               (99.5, 104, 99, 103), (103, 103.5, 102.5, 103)])
_C_O4 = cfg(stop_mode="wick_invalidation", stop_window_bars=2, take_profit_pct=3.0, exit_execution="maker_tp", maker_tp_pct=2.5)
add(id="i4-11-wick-first", viewpoint="I4-11", kind="値",
    what="構造的な逆指値の出口(前の足の終値が水準を割った次の足の始値)が、同じ足の待つ合図・利確・maker の利確より先か",
    how="_OW の足、窓 N = 2、利確 3%(103)・maker の利確 2.5%(102.5)、費用 0。BUY@1 → 足 2 の始値 100。水準 = min(足 0・1 の安値 99.5, 99.5) = 99.5"
        "(R-W1)。足 3 の終値 99.3 < 99.5 → 足 4 の始値で出る(R-W3)。足 4 には SELL@3 の合図も待ち、高値 104 は 103・102.5 を通過する。R-O1 で"
        "構造的な逆指値が先 → 足 4 の始値 99.5(taker)。損益 = -0.5 x 30 = -15。",
    input=bars_input(_OW, [(1, "BUY"), (3, "SELL")], _C_O4, want=_WO),
    expect=full_expect(_OW, _long(4, 99.5), _C_O4, 60, _WO), judge=J(*_WO))
_C_O11 = cfg(execution="maker", maker_timeout_bars=3, stop_mode="wick_invalidation", stop_window_bars=2)
add(id="i4-11-wick-before-exit-limit", viewpoint="I4-11", kind="値",
    what="maker の執行で、構造的な逆指値の出口が、同じ足で厳密に通過される待つ決済の指値より先か。捨てた指値を取り逃しに数えないか(R-M5)",
    how="_OW の足、maker、寿命 3、窓 N = 2、費用 0。BUY@1 → 指値 100(足 1 の終値)、足 2 の安値 99.5 < 100 で 100 で建つ(R-M1)。水準 99.5(R-W1)。"
        "SELL@3 → 決済の指値 99.3(足 3 の終値)を置く。足 4 は構造的な逆指値の出口(足 3 の終値 99.3 < 99.5)と、指値 99.3 の厳密な通過(高値 104)の"
        "両方 → R-O1 で構造的な逆指値が先、足 4 の始値 99.5(taker)。指値は捨て、取り逃しは 0(R-M5)。",
    input=bars_input(_OW, [(1, "BUY"), (3, "SELL")], _C_O11, want=_WOM),
    expect=full_expect(_OW, _long(4, 99.5), _C_O11, 60, _WOM, missed=0), judge=J(*_WOM))
_C_O5 = cfg(max_hold_bars=2, stop_loss_pct=2.0, take_profit_pct=3.0, exit_execution="maker_tp", maker_tp_pct=2.5)
add(id="i4-13-stop-on-time-bar", viewpoint="I4-13", kind="値",
    what="時間切れの足(足 b + N)の範囲が逆指値に届いても、時間切れが足の始値で先に閉じ、範囲の逆指値・待つ合図・利確・maker の利確は"
         "起きないか(R-O1: 始値の出来事は範囲の出来事より先。R-H3 の「先に見るのは逆指値だけ」は始値より後の範囲の中の順)",
    how="OA の足、N = 2、逆指値 2%・利確 3%・maker の利確 2.5%、費用 0。BUY@1 → 足 2 の始値 100、時間切れの足は 4。足 4 は SELL@3 の合図も待ち、"
        "範囲は逆指値・利確・maker の利確の全部に届く。始値 101 は逆指値の水準 98 より上なので、逆指値は始値より前に起きない。R-O1 で始値の"
        "時間切れが先 → 足 4 の始値 101(taker)。損益 = (101 - 100) x 30 = 30。",
    input=bars_input(OA, [(1, "BUY"), (3, "SELL")], _C_O5, want=_WO),
    expect=full_expect(OA, _long(4, 101.0), _C_O5, 60, _WO), judge=J(*_WO))
_C_O5B = cfg(max_hold_bars=2, stop_loss_pct=2.0)
add(id="i4-13-stop-on-time-bar-two-models", viewpoint="I4-13", kind="能力",
    what="1 つの戦略の記述から、互換の出力(時間切れの足でも範囲の逆指値を時間切れより先に取る既存の計算 L-5)と仕様の出力(R-O1: 始値の"
         "時間切れが先)の両方を出せるか",
    how="OA の足、N = 2、逆指値 2%(98)、費用 0、BUY@1。足 4 は時間切れの足で、安値 97 <= 98。互換の答え = 足 4 の逆指値 min(101, 98) = 98"
        "(L-5)。仕様の答え = 足 4 の始値 101(R-O1・R-H3)。",
    input=bars_input(OA, [(1, "BUY")], _C_O5B, want=_WO, model=["legacy", "spec"]),
    expect={"legacy": full_expect(OA, _long(4, 98.0), _C_O5B, 60, _WO), "spec": full_expect(OA, _long(4, 101.0), _C_O5B, 60, _WO)},
    judge={"legacy": J(*_WO), "spec": J(*_WO)})
_C_O6 = cfg(max_hold_bars=2, take_profit_pct=3.0, exit_execution="maker_tp", maker_tp_pct=2.5)
add(id="i4-13-time-first", viewpoint="I4-13", kind="値",
    what="時間切れの足で逆指値に届かないとき、時間切れが足の始値で閉じ、待つ合図・利確・maker の利確は起きないか(R-H1〜R-H3・R-O1)",
    how="OU の足、N = 2、利確 3%・maker の利確 2.5%、費用 0。BUY@1 → 足 2 の始値 100。足 4 に SELL@3 の合図が待ち、高値 104 は 103・102.5 を"
        "通過するが、R-O1 で時間切れが先 → 足 4 の始値 101(taker)。損益 = 30。",
    input=bars_input(OU, [(1, "BUY"), (3, "SELL")], _C_O6, want=_WO),
    expect=full_expect(OU, _long(4, 101.0), _C_O6, 60, _WO), judge=J(*_WO))
add(id="i4-13-time-first-two-models", viewpoint="I4-13", kind="能力",
    what="1 つの戦略の記述から、互換の出力(同じ足で利確を時間切れ・待つ合図より先に取る既存の計算 L-1・L-5)と仕様の出力(R-O1)の両方を出せるか",
    how="i4-13-time-first と同じ入力。互換の答え = 足 4 の利確 103(L-1: 範囲の利確が時間切れより先。率の利確が maker の利確より先)。"
        "仕様の答え = 足 4 の始値 101。",
    input=bars_input(OU, [(1, "BUY"), (3, "SELL")], _C_O6, want=_WO, model=["legacy", "spec"]),
    expect={"legacy": full_expect(OU, _long(4, 103.0), _C_O6, 60, _WO), "spec": full_expect(OU, _long(4, 101.0), _C_O6, 60, _WO)},
    judge={"legacy": J(*_WO), "spec": J(*_WO)})
_C_M3 = cfg(max_hold_bars=2, exit_execution="maker_tp", maker_tp_pct=2.5)
add(id="i4-13-time-maker-tp-two-models", viewpoint="I4-13", kind="能力",
    what="1 つの戦略の記述から、互換の出力(同じ足で maker の利確を時間切れ・待つ合図より先に取る既存の計算 L-1・L-5)と仕様の出力(R-O1)の両方を出せるか",
    how="OU の足、N = 2、maker の利確 2.5%(102.5)、費用 0、BUY@1・SELL@3。互換の答え = 足 4 の maker の利確 102.5。仕様の答え = 足 4 の始値 101。",
    input=bars_input(OU, [(1, "BUY"), (3, "SELL")], _C_M3, want=_WO, model=["legacy", "spec"]),
    expect={"legacy": full_expect(OU, _long(4, 102.5), _C_M3, 60, _WO), "spec": full_expect(OU, _long(4, 101.0), _C_M3, 60, _WO)},
    judge={"legacy": J(*_WO), "spec": J(*_WO)})
_C_O10 = cfg(execution="maker", maker_timeout_bars=3, max_hold_bars=2)
add(id="i4-13-time-before-exit-limit", viewpoint="I4-13", kind="値",
    what="maker の執行で、時間切れが、同じ足で厳密に通過される待つ決済の指値より先か。捨てた指値を取り逃しに数えないか(R-M5)",
    how="OU の足、maker、寿命 3、N = 2、費用 0。BUY@1 → 指値 100、足 2 で 100 で建つ(R-M1)。SELL@3 → 決済の指値 101(足 3 の終値)。足 4 は"
        "時間切れの足で、高値 104 > 101 で指値も通過される。R-O1 で時間切れが先 → 足 4 の始値 101(taker)。取り逃し 0(R-M5)。",
    input=bars_input(OU, [(1, "BUY"), (3, "SELL")], _C_O10, want=_WOM),
    expect=full_expect(OU, _long(4, 101.0), _C_O10, 60, _WOM, missed=0), judge=J(*_WOM))
_C_O12 = cfg(execution="maker", maker_timeout_bars=3, max_hold_bars=2, stop_loss_pct=2.0)
add(id="i4-13-stop-on-time-bar-maker", viewpoint="I4-13", kind="値",
    what="maker の執行の時間切れの足で、始値の時間切れが、範囲の逆指値と待つ決済の指値より先か(R-O1・R-H3)。捨てた指値を取り逃しに"
         "数えないか(R-M5)",
    how="OA の足、maker、寿命 3、N = 2、逆指値 2%、費用 0。足 2 で 100 で建ち、SELL@3 → 決済の指値 101。足 4 は時間切れの足で、安値 97 <= 98・"
        "高値 104 > 101。R-O1 で始値の時間切れが先 → 足 4 の始値 101(taker)。指値は捨て、取り逃し 0(R-M5)。",
    input=bars_input(OA, [(1, "BUY"), (3, "SELL")], _C_O12, want=_WOM),
    expect=full_expect(OA, _long(4, 101.0), _C_O12, 60, _WOM, missed=0), judge=J(*_WOM))
_C_O7 = cfg(execution="maker", maker_timeout_bars=3, stop_loss_pct=2.0, take_profit_pct=3.0, exit_execution="maker_tp",
            maker_tp_pct=2.5)
add(id="i4-16-stop-before-exit-limit", viewpoint="I4-16", kind="値",
    what="maker の執行で、待つ決済の指値と逆指値・利確・maker の利確が同じ足に届くとき、逆指値が先で、捨てた指値は取り逃しに数えないか(R-O1・R-M5)",
    how="OA の足、maker、寿命 3、逆指値 2%・利確 3%・maker の利確 2.5%、費用 0。足 2 で 100 で建ち、SELL@3 → 決済の指値 101。足 4 は指値の通過"
        "(高値 104 > 101)・逆指値(安値 97)・利確・maker の利確の全部 → 逆指値が先、min(101, 98) = 98。取り逃し 0(R-M5)。",
    input=bars_input(OA, [(1, "BUY"), (3, "SELL")], _C_O7, want=_WOM),
    expect=full_expect(OA, _long(4, 98.0), _C_O7, 60, _WOM, missed=0), judge=J(*_WOM))
_C_O8 = cfg(execution="maker", maker_timeout_bars=3, take_profit_pct=3.0, exit_execution="maker_tp", maker_tp_pct=2.5)
add(id="i4-16-tp-before-exit-limit", viewpoint="I4-16", kind="値",
    what="maker の執行で、待つ決済の指値・利確・maker の利確が同じ足で通過されるとき、利確が先で、捨てた指値は取り逃しに数えないか",
    how="OU の足、maker、寿命 3、利確 3%・maker の利確 2.5%、費用 0。足 2 で 100 で建ち、SELL@3 → 決済の指値 101。足 4 の高値 104 は 101・102.5・103 を"
        "全部通過 → R-O1 で利確が先、水準 103(maker)。取り逃し 0(R-M5)。",
    input=bars_input(OU, [(1, "BUY"), (3, "SELL")], _C_O8, want=_WOM),
    expect=full_expect(OU, _long(4, 103.0), _C_O8, 60, _WOM, missed=0), judge=J(*_WOM))
_C_O9 = cfg(execution="maker", maker_timeout_bars=3, exit_execution="maker_tp", maker_tp_pct=2.5)
add(id="i4-16-maker-tp-before-exit-limit", viewpoint="I4-16", kind="値",
    what="maker の執行で、待つ決済の指値と maker の利確が同じ足で通過されるとき、maker の利確が先で、捨てた指値は取り逃しに数えないか",
    how="OU の足、maker、寿命 3、maker の利確 2.5%、費用 0。足 2 で 100 で建ち、SELL@3 → 決済の指値 101。足 4 の高値 104 は 101 も 102.5 も通過"
        " → R-O1 で maker の利確が先、水準 102.5。取り逃し 0(R-M5)。",
    input=bars_input(OU, [(1, "BUY"), (3, "SELL")], _C_O9, want=_WOM),
    expect=full_expect(OU, _long(4, 102.5), _C_O9, 60, _WOM, missed=0), judge=J(*_WOM))


# --------------------------------------------------------------------------- I4-3 at the core and reference granularity
def _delivery_expect(bars):
    """C-1: what the strategy is handed grows by one bar per delivered bar and is always exactly the bars delivered
    so far: its i-th view (i4_judge.views) has seen i + 1 bars, the last of which is bar i."""
    return {"calls": [{"seen": i + 1, "last_t_ns": b["t_ns"], "last_close": b["close"]} for i, b in enumerate(bars)]}


DV = mk_bars([(100, 101, 99, 100.5), (100.5, 102, 100, 101.5), (101.5, 101.8, 99.5, 99.8), (99.8, 100.4, 98.9, 100.1),
              (100.1, 100.9, 99.9, 100.7)])
add(id="i4-3-core-delivery", viewpoint="I4-3", kind="値",
    what="核の粒度の正解つきの場面: 足を 1 本ずつ届けたとき、戦略に見える物が足ごとに 1 本ずつ増え、どの時点でもそれまでに届いた足だけ(数・"
         "最後の足の開始の時刻・終値)か(先の足が見えない・どの足も飛ばされない)",
    how="C-1(戦略は受け取れた時刻 <= 今の事象しか見ない = 委任文 §2 項目 0 の行)。DV の 5 本(60 秒足)で、見えた物の i 番目は 足 0〜i の i + 1 本で、"
        "最後の足は足 i(開始 T0 + 60 i 秒、終値は足 i の終値)。",
    input={"op": "delivery", "bars": DV, "bar_seconds": 60, "want": ["calls"]},
    expect=_delivery_expect(DV), judge={"calls": True})
DG = [b for i, b in enumerate(mk_bars([(100, 101, 99, 100.5), (100.5, 102, 100, 101.5), (0, 0, 0, 0), (101.5, 101.8, 99.5, 99.8),
                                       (99.8, 100.4, 98.9, 100.1)])) if i != 2]
add(id="i4-3-core-delivery-gap", viewpoint="I4-3", kind="値",
    what="核の粒度: 足の時刻に抜け(1 本分の空き)があるとき、抜けた足を作らず、届いた足だけを届いた順に渡すか",
    how="C-1。60 秒足で開始 T0・T0 + 60 秒・T0 + 180 秒・T0 + 240 秒の 4 本(T0 + 120 秒の足は無い)。見えた物は 4 通りで、i 番目は i + 1 本を見て、"
        "最後の足の開始は入力の足 i の開始(空いた時刻に足を作らない)。",
    input={"op": "delivery", "bars": DG, "bar_seconds": 60, "want": ["calls"]},
    expect=_delivery_expect(DG), judge={"calls": True})
add(id="i4-3-ref-signal-first", viewpoint="I4-3", kind="値",
    what="参照実装の粒度の正解つきの場面: i4-10-signal-first の入力(始値の合図と範囲の逆指値・利確が同じ足)を本体と参照実装の両方で回し、"
         "両方が正解と一致するか",
    how="i4-10-signal-first と同じ手の計算(R-O1)。本体と参照実装の両方にこの同じ正解を当てる。",
    input={**bars_input(OA, [(1, "BUY"), (3, "SELL")], _C_O1, want=_WO), "reference": True},
    expect={"engine": full_expect(OA, _long(4, 101.0), _C_O1, 60, _WO), "reference": full_expect(OA, _long(4, 101.0), _C_O1, 60, _WO)},
    judge={"engine": J(*_WO), "reference": J(*_WO)})


# --------------------------------------------------------------------------- viewpoints that are not scenes
NOT_SCENES = {
    "I4-7": "全試験(`PYTHONPATH=src python -m pytest`)が通るかは、当方のリポジトリの試験の集まりについての事実で、場面の入力を対象に"
            "渡して結果を正解と突き合わせる形にならない(調査結果の側の道具には当方の試験の集まりが無い)。批評家が全試験の末尾の行で見る。",
    "I4-19": "旧の出力(golden)の保存と一致は、委任文 §3「項目 4 の場面」で「この場面とは別に、旧 14 の確認として見る」と定められている"
             "(場面の正解は手計算で、golden を正解にしない)。批評家が tests/bt/compat/ の試験で見る。",
    "I4-20": "最後の段の置き換えと復元は、リポジトリのファイル(src/bot/backtest/ の 3 本)を置き換えて試験を回し、落ちたら戻すという手順で、"
             "場面の入力と出力の形にならない。批評家が git の差分・試験の出力・報告で見る。",
}
VIEWPOINTS = {
    "I4-1": "独立参照実装との突き合わせ", "I4-2": "性質の試験(不変条件)", "I4-3": "正解つきの場面",
    "I4-4": "外部道具との数値突き合わせ(合成データ)", "I4-5": "全資産・複数データ源の統合パイプライン一本化",
    "I4-6": "動作確認用の固定手順の遵守", "I4-7": "全試験通過(既存を壊さない)", "I4-8": "翌足始値での taker 執行",
    "I4-9": "指値の厳密な通過", "I4-10": "足内の TP/SL と STOP 優先順位", "I4-11": "wick_invalidation(構造的ストップ)",
    "I4-12": "maker_tp(指値イグジット)", "I4-13": "max_hold_bars(強制タイムイグジット)", "I4-14": "entry_mask / entry_sides",
    "I4-15": "swap_daily_pct(スワップ/資金調達費用)", "I4-16": "missed_fills(未約定カウント)",
    "I4-17": "compute_metrics の全指標一致", "I4-18": "split_data(暦ではない行数割合の 3 分割)",
    "I4-19": "旧の出力(golden)の保存と一致", "I4-20": "最後の段の安全な置き換えと復元",
}


def expected(scene):
    return scene["expect"]


def by_id(sid):
    return next(s for s in SCENES if s["id"] == sid)


def file_bytes(f):
    return f["text"].encode("utf-8")


assert len({s["id"] for s in SCENES}) == len(SCENES)

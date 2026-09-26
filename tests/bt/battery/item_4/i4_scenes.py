"""Item 4 battery (統合と答え合わせ): the scenes.

Every scene is a dict:
    id         -- unique id, prefixed by its viewpoint (i4-1- ... i4-18-)
    viewpoint  -- I4-1 .. I4-18 (REQUIREMENTS.md §2)
    kind       -- 値 (a value is right) | 能力 (a capability, judged by the result it must give)
    what       -- 何を測るか
    how        -- 正解の出し方 (how the expected answer was fixed, without looking at any engine)
    input      -- what the adapter receives (plus "root" for file scenes, added by the runner)
    cases      -- (instead of input) a list of inputs, each run separately (I4-2 grid)
    expect     -- the expected answer (never given to the adapter)
    judge      -- which observation keys are judged, and how (i4_judge.py)
    variant    -- (optional) a second input the target must REFUSE

All inputs are synthetic.  The expected answers are written by hand from the
stated bar-model rules (DEFINITIONS.md「足の模型の仕様」R-*): for each scene the
bar and the reference price of every fill are chosen by hand (the comment next
to the scene says which rule puts it there), and the helpers below only do the
bookkeeping arithmetic those rules state (size = notional / price, fee =
notional x pct, PnL, carry, equity, the metric formulas).  The one exception
is the I4-2 grid, whose fills come from `taker_rule` -- the stated taker rules
R-T1..R-T4 written as a function (no stops, no maker, no carry), because the
grid's inputs are random.  Only the standard library is used, so this module
also loads under every survey tool's interpreter.
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
C_TAK = {"taker_fee_pct": 0.1, "maker_fee_pct": 0.05, "slippage_pct": 0.02, "spread_pct": 0.04}

# E: the end-to-end taker path (I4-1 / I4-3)
E = mk_bars([(1000, 1005, 995, 1000), (1000, 1010, 998, 1008), (1010, 1020, 1005, 1015), (1015, 1025, 1010, 1020),
             (1020, 1030, 1015, 1025), (1025, 1028, 1018, 1020), (1018, 1022, 1012, 1015), (1015, 1018, 1008, 1010),
             (1010, 1015, 1005, 1012), (1012, 1030, 1008, 1025), (1025, 1045, 1020, 1040), (1040, 1042, 1030, 1035),
             (1035, 1040, 1030, 1032), (1030, 1036, 1026, 1034), (1034, 1038, 1028, 1036), (1036, 1040, 1031, 1038)])
C_E = {"taker_fee_pct": 0.12, "maker_fee_pct": 0.02, "slippage_pct": 0.03, "spread_pct": 0.06}
CFG_E = cfg(costs=C_E, allow_short=True, stop_loss_pct=3.0, swap_daily_pct=0.72)
SIG_E = [(1, "BUY"), (5, "SELL"), (7, "SELL"), (12, "BUY")]
_sl_short_E = sell_px(1010, C_E) * 1.03  # R-P1: short stop level = entry x (1 + 3/100)
TR_E = [trade(2, +1, buy_px(1010, C_E), 0.12, 6, sell_px(1018, C_E), 0.12),          # R-T1: signal bar + 1 open
        trade(8, -1, sell_px(1010, C_E), 0.12, 10, buy_px(max(1025, _sl_short_E), C_E), 0.12),  # R-P1/R-P3: high 1045 >= level, trigger max(open, level)
        trade(13, +1, buy_px(1030, C_E), 0.12)]                                          # open at the end
W_E = ("fills", "pnls", "equity", "metrics", "missed_fills")

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
         "本体と、本体とは別に書かれた参照実装の両方で回し、両方が正解と一致するか",
    how="E の足で、約定の足と基準の値を規則 R-T1・R-P1・R-P3 で手で置き(場面の注記)、サイズ・手数料・持ち越し・損益・"
        "資産の推移・指標を R-A1〜R-A4・R-S1・M-1〜M-12 の式で計算した。本体と参照実装の両方にこの同じ正解を当てる。",
    input={**bars_input(E, SIG_E, CFG_E, want=W_E), "reference": True},
    expect={"engine": full_expect(E, TR_E, CFG_E, 60, W_E), "reference": full_expect(E, TR_E, CFG_E, 60, W_E)},
    judge={"engine": J(*W_E), "reference": J(*W_E)})
add(id="i4-1-ref-maker", viewpoint="I4-1", kind="値",
    what="同じ入力(足の maker の経路: 指値の厳密な通過・maker の利確・逆指値・時間切れの取消)を、本体と参照実装の両方で回し、"
         "両方が正解と一致するか",
    how="F の足で、約定の足と値を R-M1・R-M2・R-X1・R-P1・R-P3 で手で置き、帳簿を R-A・M の式で計算した。"
        "取り消された指値は 1 件(R-M2)。",
    input={**bars_input(F, SIG_F, CFG_F, want=W_E), "reference": True},
    expect={"engine": full_expect(F, TR_F, CFG_F, 60, W_E, missed=1),
            "reference": full_expect(F, TR_F, CFG_F, 60, W_E, missed=1)},
    judge={"engine": J(*W_E), "reference": J(*W_E)})


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


def grid_cases(seed=20260926, n=30):
    """Random bars, random scripts and random costs; drawn without looking at any target's code paths."""
    rng = random.Random(seed)
    cases = []
    for _ in range(n):
        m = rng.randint(8, 20)
        px, rows = 1000.0, []
        for _ in range(m):
            o = round(px + rng.uniform(-8, 8), 1)
            c = round(o + rng.uniform(-10, 10), 1)
            h = round(max(o, c) + rng.uniform(0, 6), 1)
            lo = round(min(o, c) - rng.uniform(0, 6), 1)
            rows.append((o, h, lo, c))
            px = c
        costs = {k: rng.choice([0.0, 0.01, 0.05, 0.1, 0.15]) for k in ZERO}
        sigs = [(i, rng.choice(["BUY", "SELL", "CLOSE"])) for i in range(m) if rng.random() < 0.45]
        conf = cfg(costs=costs, allow_short=rng.random() < 0.5, initial_equity=float(rng.choice([6000, 100000])),
                   order_notional=float(rng.choice([3000, 1234.5])))
        cases.append(bars_input(mk_bars(rows), sigs, conf, want=("fills", "pnls", "equity")))
    return cases


_GRID = grid_cases()
add(id="i4-2-grid", viewpoint="I4-2", kind="値",
    what="種 20260926 で引いた 30 の場合(足・合図の並び・費用・ショートの可否・元本・発注額を乱数で引く。実装の場合分けから作らない)の"
         "全部で、約定が規則どおりで、不変条件(建てと決済が交互・決済の数量 = 建ての数量・損益の恒等式・資産の恒等式・約定は合図の足より後)"
         "が 1 つも崩れないか",
    how="約定の足と値は規則 R-T1〜R-T4 を関数にした taker_rule で決め(停止・maker・持ち越しを含まない場合だけ)、帳簿は R-A の式。"
        "不変条件は観測した約定から判定の側で式で検める(i4_judge.invariants)。",
    cases=_GRID,
    expect=[full_expect(c["bars"], taker_rule(c), c["config"], 60, ("fills", "pnls", "equity")) for c in _GRID],
    judge=J("fills", "pnls", "equity") | {"invariants": True})


# --------------------------------------------------------------------------- I4-3 known-answer scenes (whole engine)
add(id="i4-3-e2e-taker", viewpoint="I4-3", kind="値",
    what="新エンジン全体の粒度の正解つきの場面(足の taker の経路): 約定・損益・資産の推移・12 の指標・取り逃しの数が全部正解と一致するか",
    how="i4-1-ref-taker と同じ手の計算(E の足、R-T1・R-P1・R-P3・R-A・R-S1・M)。",
    input=bars_input(E, SIG_E, CFG_E, want=W_E), expect=full_expect(E, TR_E, CFG_E, 60, W_E), judge=J(*W_E))
add(id="i4-3-e2e-maker", viewpoint="I4-3", kind="値",
    what="新エンジン全体の粒度の正解つきの場面(足の maker の経路): 約定・損益・資産の推移・12 の指標・取り逃しの数が全部正解と一致するか",
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


def pipeline_input(want, *, strategy=None, purpose="動作確認", prereg=None):
    files, ds = _pipeline_files()
    return {"op": "pipeline", "files": files, "datasets": ds, "instruments": INSTRUMENTS,
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
add(id="i4-6-signal-refused", viewpoint="I4-6", kind="能力",
    what="実データと宣言したファイルに、値で条件づけた戦略(値が閾値を下回ったら買う)を目的「動作確認」で通そうとしたら拒むか"
         "(対照: 同じファイルに固定の手順なら通り、約定は手順どおり)",
    how="委任文 §4「実データを通すときの戦略は、時刻だけで決まる機械的な手順か種つきの乱数に限る。信号・条件付け・最適化を入れない」。"
        "対照の正解は i4-5-fills の約定。",
    input=pipeline_input(("fills",)), expect={"fills": _PF}, judge={"pfills": True},
    variant=pipeline_input(("fills",), strategy={"kind": "price_rule", "buy_below": 15000600.0, "sell_above": 15002500.0,
                                                 "qty": 1.0}))
add(id="i4-6-research-refused", viewpoint="I4-6", kind="能力",
    what="目的「研究」を事前登録のハッシュ無しで実行しようとしたら拒むか(対照: 目的「動作確認」なら通る)",
    how="委任文 §4「目的 `研究` の実行は事前登録のハッシュが無いと作れない」。対照の正解は i4-5-fills の約定。",
    input=pipeline_input(("fills",)), expect={"fills": _PF}, judge={"pfills": True},
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
_CM = cfg(costs={**ZERO, "taker_fee_pct": 0.1, "maker_fee_pct": 0.05}, execution="maker", maker_timeout_bars=3)
_W4 = ("fills", "pnls", "equity", "missed_fills")
add(id="i4-9-strict", viewpoint="I4-9", kind="値",
    what="maker の指値(合図の足の終値に置く)が、値に触れただけでは約定せず、後の足が厳密に通過したときだけ指値の値で maker 手数料で約定するか",
    how="M の足。BUY@1 → 指値 100(足 1 の終値)。足 2 の安値 100 は触れただけ、足 3 の安値 99.5 < 100 で 100 で約定(R-M1)。SELL@4 → "
        "指値 103、足 5 の高値 105 > 103 で 103 で約定。手数料は maker 0.05%(R-A2)。取り逃し 0。",
    input=bars_input(M, [(1, "BUY"), (4, "SELL")], _CM, want=_WFM),
    expect=full_expect(M, [trade(3, +1, 100.0, 0.05, 5, 103.0, 0.05)], _CM, 60, _WFM, missed=0),
    judge=J(*_WFM))
SB = mk_bars([(100, 101, 99, 100), (100, 100.5, 99, 100), (99.5, 100, 99, 99.8), (99.8, 100.5, 99, 100),
              (100, 100.5, 98, 99), (99.5, 100, 99, 99.5), (99.5, 100, 98.5, 99), (99, 100, 98, 99)])
_CMS = cfg(costs={**ZERO, "maker_fee_pct": 0.05}, execution="maker", maker_timeout_bars=3, allow_short=True)
add(id="i4-9-short-strict", viewpoint="I4-9", kind="値",
    what="売りの指値は高値が指値を厳密に上回ったときだけ、買い戻しの指値は安値が厳密に下回ったときだけ約定するか",
    how="SB の足。SELL@1 → 指値 100、足 2 の高値 100 は触れただけ、足 3 の高値 100.5 > 100 で売り建て 100。BUY@4 → 指値 99、"
        "足 5 の安値 99 は触れただけ、足 6 の安値 98.5 < 99 で 99 で買い戻し(R-M1)。",
    input=bars_input(SB, [(1, "SELL"), (4, "BUY")], _CMS, want=_WFM),
    expect=full_expect(SB, [trade(3, -1, 100.0, 0.05, 6, 99.0, 0.05)], _CMS, 60, _WFM, missed=0),
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
add(id="i4-11-refuse-stack", viewpoint="I4-11", kind="能力",
    what="構造的な逆指値と率の逆指値を重ねる設定を拒むか(対照: 構造的な逆指値だけなら通り、答えは i4-11-wick-long)",
    how="R-W4「2 つの逆指値は代わりであって重ねない」。",
    input=bars_input(WL, [(2, "BUY")], _CW, want=_WF),
    expect=full_expect(WL, [trade(3, +1, 100.0, 0.0, 6, 95.0, 0.0)], _CW, 60, _WF), judge=J(*_WF),
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
    input=bars_input(K, [(0, "BUY")], _CK, want=_WF),
    expect=full_expect(K, [trade(1, +1, 100.0, 0.1, 3, 102.0, 0.02)], _CK, 60, _WF), judge=J(*_WF),
    variant=bars_input(K, [(0, "BUY")], cfg(costs=_CK["costs"], exit_execution="maker_tp", maker_tp_pct=0.0), want=_WF))

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
    what="時間切れの足(足 b + N)に利確の水準も通るとき、仕様どおり足 b + N の始値で閉じるか(同じ足で先に見るのは逆指値だけ)",
    how="HT の足、N = 2、利確 2%(水準 102)。BUY@0 → 足 1 の始値 100。足 3 の始値 101 で時間切れ(R-H1)。仕様が同じ足で先に置くのは"
        "逆指値だけ(R-H3)なので、足 3 の高値 103 > 102 の利確は取らない。手数料は maker・taker とも 0.1%。"
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
SW = mk_bars([(100, 100.5, 99.5, 100), (100, 101.5, 99.5, 101), (101, 102.5, 100.5, 102), (102, 103.5, 101.5, 103),
              (104, 104.5, 103.5, 104), (104, 104.5, 103.5, 104)], bar_seconds=3600)
_CSW = cfg(swap_daily_pct=0.24)
add(id="i4-15-swap-long", viewpoint="I4-15", kind="値",
    what="建玉の間、足ごとに |数量| x 前の足の終値 x 日率 x (足の秒 / 86400) の持ち越しが建玉の損益と資産に掛かるか",
    how="SW の足(1 時間足)、日率 0.24% → 1 本 0.0001。BUY@0 → 足 1 の始値 100(数量 30)、SELL@3 → 足 4 の始値 104。持ち越しは足 2・3・4 に"
        "30 x (101 + 102 + 103) x 0.0001 = 0.918(R-S1)。損益 = 120 - 0.918 = 119.082。",
    input=bars_input(SW, [(0, "BUY"), (3, "SELL")], _CSW, bar_seconds=3600, want=_W3),
    expect=full_expect(SW, [trade(1, +1, 100.0, 0.0, 4, 104.0, 0.0)], _CSW, 3600, _W3),
    judge=J(*_W3))
_CSWS = cfg(swap_daily_pct=0.24, allow_short=True)
add(id="i4-15-swap-short", viewpoint="I4-15", kind="値",
    what="売り建てにも同じ持ち越しが掛かる(数量の絶対値で費用として引く)か",
    how="SW の足。SELL@0 → 足 1 の始値 100 の売り、BUY@3 → 足 4 の始値 104。持ち越し 0.918(R-S1)。損益 = -120 - 0.918 = -120.918。",
    input=bars_input(SW, [(0, "SELL"), (3, "BUY")], _CSWS, bar_seconds=3600, want=_W3),
    expect=full_expect(SW, [trade(1, -1, 100.0, 0.0, 4, 104.0, 0.0)], _CSWS, 3600, _W3),
    judge=J(*_W3))

# --------------------------------------------------------------------------- I4-16 missed fills
MF = mk_bars([(100, 101, 99, 100), (100, 101.5, 100, 101), (101, 102, 101, 101.5), (101.5, 102, 101.2, 101.8),
              (101.8, 102, 98.8, 99), (99.5, 100.2, 99.2, 100), (100, 100.8, 99.8, 100.5), (100.5, 100.8, 99.4, 99.5),
              (99.5, 99.8, 99.2, 99.6), (99.6, 100, 99.4, 99.8)])
_CMF = cfg(costs={**ZERO, "maker_fee_pct": 0.02}, execution="maker", maker_timeout_bars=2, allow_short=True)
add(id="i4-16-missed", viewpoint="I4-16", kind="値",
    what="約定しなかった指値を、時間切れの取消と反対向きの合図による置き換えの 2 つの条件で数えるか",
    how="MF の足、寿命 2 本。BUY@1 → 指値 101。足 2 の安値 101 は触れただけ、足 3 は届かず、足 3 で 3 - 1 = 2 >= 2 → 取消 1 件目(R-M2)。"
        "BUY@4 → 指値 99(足 4 の終値)、足 5 の安値 99.2 は届かない。SELL@5(建玉なし、ショート可)が反対向きなので BUY の指値を置き換え"
        " 2 件目(R-M3)、売りの指値 100。足 6 の高値 100.8 > 100 で売り建て 100。CLOSE@7 → 買い戻しの指値 99.5、足 8 の安値 99.2 < 99.5 で"
        " 99.5(R-M1・R-M4)。",
    input=bars_input(MF, [(1, "BUY"), (4, "BUY"), (5, "SELL"), (7, "CLOSE")], _CMF, want=_WFM),
    expect=full_expect(MF, [trade(6, -1, 100.0, 0.02, 8, 99.5, 0.02)], _CMF, 60, _WFM, missed=2),
    judge=J(*_WFM))

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
_TR17 = [trade(1, +1, 100.0, 0.0, 4, 104.0, 0.0)]
add(id="i4-17-sharpe-bar-seconds", viewpoint="I4-17", kind="値",
    what="1 時間足のバックテストのシャープが、足の頻度で年率化される(1 年 = 8760 本)か",
    how="SW の足(1 時間足)、費用 0・持ち越し 0。BUY@0 → 足 1 の 100、SELL@3 → 足 4 の 104。資産の推移は R-A の式、シャープは M-5 で "
        "1 年の本数 = 365 x 86400 / 3600 = 8760。",
    input=bars_input(SW, [(0, "BUY"), (3, "SELL")], cfg(), bar_seconds=3600, want=_W17),
    expect=full_expect(SW, _TR17, cfg(), 3600, _W17), judge=J(*_W17))
add(id="i4-17-two-models", viewpoint="I4-17", kind="能力",
    what="1 つの戦略の記述から、互換の出力(足の頻度を見ず 1 年 = 525600 本で年率化する既存の計算 L-2)と仕様の出力(M-5)の両方を出せるか",
    how="互換の答え = シャープの年率化だけ sqrt(525600)、ほかは同じ。仕様の答え = i4-17-sharpe-bar-seconds。",
    input=bars_input(SW, [(0, "BUY"), (3, "SELL")], cfg(), bar_seconds=3600, want=_W17, model=["legacy", "spec"]),
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

"""Item 2 battery (執行の模型): the scenes and their oracles.

Every expected answer is DERIVED by an oracle function from the scene's own
input (closed-form arithmetic written from the scene's declared rule).  No
expected value is typed by hand; `test_battery_item2.py` fails if a scene
carries a literal answer, and DEFINITIONS.md is generated from this file by
`i2_gen_definitions.py` (the prose never restates a number by hand).

The oracles never import or look at any engine.  A scene states the rule it
tests in `input["rules"]` / `input["fill_model"]` / `input["latency"]` /
`input["costs"]`; the oracle computes what that rule implies for the input.

Expected-answer keys (read by `i2_judge.py`):
  status.<ref>        final status (filled/open/canceled/rejected/state_unknown)
  filled.<ref>        total filled quantity (sum of the ref's fills)
  avg_px.<ref>        quantity-weighted fill price
  first_fill_t.<ref>  venue time of the ref's first fill
  cum.<ref>@<cp>      cumulative filled quantity with fill time <= checkpoint cp
  fee.<ref>           sum of the ref's fill fees (paid; rebate negative)
  lat_in.<ref>        first_fill_t - send time (for latency drawn from a set)
  sent.<ref>          submissions of the ref that reached the venue
  notice.<ref>.<kind> local time the strategy saw the ref's notice of kind (ack / reject /
                      fill / cancel; "terminal" = the earlier of reject and cancel)
  seen.<label>        local time the strategy saw the labelled market event
  account.<field>     account figure at the end of the scene
  costs.<field>       funding / swap paid over the scene (credit negative)
  range.<side>.<key>  the same keys, for the optimistic / pessimistic run
  refused             (paired scenes) the variant input is refused
A value is compared exactly for strings/ints and within 1e-9 (absolute and
relative) for floats; {"op": "ge"|"le"|"in", "v": ...} compares by the op.
"""
from __future__ import annotations

import copy
import math

MS = 1_000_000
SEC = 1_000_000_000
T0 = 1_767_571_200 * SEC  # 2026-01-05 00:00:00 UTC (Monday)

FX_BTC_JPY = {"symbol": "FX_BTC_JPY", "venue": "bitflyer_cfd", "tick": 1.0, "min_qty": 0.01,
              "qty_step": 1e-8, "quote_ccy": "JPY", "margin": True}
JPX_STOCK = {"symbol": "JPX_STOCK_A", "venue": "jpx_equity", "tick": 1.0, "min_qty": 100.0,
             "qty_step": 100.0, "quote_ccy": "JPY", "margin": False}
USDJPY = {"symbol": "USDJPY", "venue": "fx", "tick": 0.001, "min_qty": 1000.0,
          "qty_step": 1.0, "quote_ccy": "JPY", "margin": True}
EURUSD = {"symbol": "EURUSD", "venue": "fx", "tick": 0.00001, "min_qty": 1000.0,
          "qty_step": 1.0, "quote_ccy": "USD", "margin": True}

ZERO_COSTS = {"maker_rate": 0.0, "taker_rate": 0.0,
              "source": "場面の定義(費用を測らない場面なので 0 と明示する)"}
BIG_ACCOUNT = {"currency": "JPY", "cash": 100_000_000.0, "leverage": 1.0}
DEFAULT_RULES = {"off_tick": "reject", "below_min_qty": "reject", "post_only": "reject_if_crossing",
                 "market_remainder": "cancel", "mark": "last_trade"}


# ---------------------------------------------------------------- builders
def book(t, bids, asks, label=None):
    e = {"t": int(t), "type": "book", "bids": [list(x) for x in bids], "asks": [list(x) for x in asks]}
    if label:
        e["label"] = label
    return e


def trade(t, px, qty, aggressor, label=None):
    e = {"t": int(t), "type": "trade", "px": float(px), "qty": float(qty), "aggressor": aggressor}
    if label:
        e["label"] = label
    return e


def place(t, ref, side, otype, qty, px=None, stop_px=None, tif="GTC", post_only=False,
          reduce_only=False, oco=None):
    return {"t": int(t), "op": "place", "ref": ref, "side": side, "type": otype, "qty": float(qty),
            "px": None if px is None else float(px), "stop_px": None if stop_px is None else float(stop_px),
            "tif": tif, "post_only": post_only, "reduce_only": reduce_only, "oco": oco}


def cancel(t, ref):
    return {"t": int(t), "op": "cancel", "ref": ref}


def amend(t, ref, px=None, qty=None):
    return {"t": int(t), "op": "amend", "ref": ref, "px": px, "qty": qty}


def kill(t):
    return {"t": int(t), "op": "kill"}


def mkt0(t=T0):
    """The common crypto backdrop: best bid 9999 x 5, best ask 10001 x 5, one print at 10000."""
    return [book(t, [(9999, 5), (9998, 5)], [(10001, 5), (10002, 5)]), trade(t, 10000, 0.1, "buy")]


def base_input(**kw):
    inp = {"product": FX_BTC_JPY, "rules": dict(DEFAULT_RULES), "market": [], "actions": [],
           "fill_model": None, "latency": None, "costs": dict(ZERO_COSTS), "account": dict(BIG_ACCOUNT),
           "inject": [], "checkpoints": {}, "end_t": T0 + 60 * SEC}
    for k, v in kw.items():
        if k == "rules":
            inp["rules"].update(v)
        else:
            inp[k] = v
    inp["market"] = sorted(inp["market"], key=lambda e: e["t"])  # stable: same-time events keep list order
    return inp


# ---------------------------------------------------------------- oracle helpers
def op_ge(v):
    return {"op": "ge", "v": v}


def op_in(vs):
    return {"op": "in", "v": list(vs)}


def book_at(inp, t):
    """The last book snapshot with time <= t (external book, our orders excluded)."""
    last = None
    for e in inp["market"]:
        if e["type"] == "book" and e["t"] <= t:
            last = e
    return last


def walk(levels, qty, limit=None, side="buy"):
    """Walk best-first levels up to qty (and up to the limit price when given).
    Returns (filled, notional)."""
    filled = notional = 0.0
    for px, q in levels:
        if limit is not None and ((side == "buy" and px > limit) or (side == "sell" and px < limit)):
            break
        take = min(qty - filled, q)
        if take <= 0:
            break
        filled += take
        notional += take * px
    return filled, notional


def action(inp, ref):
    return next(a for a in inp["actions"] if a.get("ref") == ref and a["op"] == "place")


def trades_after(inp, t):
    return [e for e in inp["market"] if e["type"] == "trade" and e["t"] > t]


def rate_fee(rate, px, qty):
    return rate * px * qty


# ---------------------------------------------------------------- scenes
SCENES: list[dict] = []


def scene(sid, viewpoint, kind, title, measures, derivation, inp, oracle, variant=None):
    s = {"id": sid, "viewpoint": viewpoint, "kind": kind, "title": title, "measures": measures,
         "derivation": derivation, "input": inp, "oracle": oracle}
    if variant is not None:
        s["variant"] = variant
    SCENES.append(s)
    return s


# ======================= C2-1 発注の型 =======================
def _o_market(inp):
    a = action(inp, "o1")
    b = book_at(inp, a["t"])
    f, n = walk(b["asks"], a["qty"])
    return {"status.o1": "filled", "filled.o1": f, "avg_px.o1": n / f}


scene("c2-1-market", "C2-1", "値", "成行の買いは、出した時の売りの気配で埋まる",
      "成行(market)の受付と約定の状態遷移と約定値",
      "出した時刻の板(外部の気配)の売り側を良い方から数量まで辿った加重平均値。1 は最良の 5 以下なので最良の売り値そのもの。",
      base_input(market=mkt0() + [trade(T0 + 2 * MS, 10001, 1, "buy")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "market", 1)]),
      _o_market)


def _o_limit(inp):
    a = action(inp, "o1")
    first = next(e for e in trades_after(inp, a["t"]) if e["px"] <= a["px"])
    return {"status.o1": "filled", "filled.o1": a["qty"], "avg_px.o1": a["px"],
            "first_fill_t.o1": op_ge(first["t"])}


scene("c2-1-limit", "C2-1", "値", "指値の買いは、約定の値が指値に届くまで埋まらず、埋まるときは指値で埋まる",
      "指値(limit)の待機と約定の状態遷移。約定値は指値。値が届く前に埋まらない",
      "指値 9990 の買い。出した後の約定の列で値が 9990 以下になる最初の時刻より前には埋まらない(first_fill_t ≥ その時刻)。"
      "埋まる値は指値そのもの。指値の値位には外部の待ちが無い(板の買いは 9999・9998 だけ)ので、どの約定の模型でも全量が埋まる。",
      base_input(market=mkt0() + [trade(T0 + 10 * MS, 9995, 2, "sell"), trade(T0 + 20 * MS, 9990, 10, "sell"),
                                  trade(T0 + 30 * MS, 9985, 5, "sell")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "limit", 1, px=9990)]),
      _o_limit)


def _o_postonly(inp):
    a1, a2 = action(inp, "o1"), action(inp, "o2")
    b = book_at(inp, a1["t"])
    crosses = a1["px"] >= b["asks"][0][0]
    rests = a2["px"] < b["asks"][0][0] and not any(e["px"] <= a2["px"] for e in trades_after(inp, a2["t"]))
    assert crosses and rests
    return {"status.o1": op_in(["rejected", "canceled"]), "filled.o1": 0.0, "status.o2": "open", "filled.o2": 0.0}


scene("c2-1-postonly", "C2-1", "値", "post-only は、出した時に反対側の気配に届く値なら拒否され、届かない値なら待つ",
      "post-only の拒否と待機(規則 post_only = reject_if_crossing)",
      "o1 = 10001 の post-only 買い。出した時の最良の売りが 10001 なので取る側になる → 約定 0 で終わる(拒否か、着いた時点の取消)。"
      "o2 = 9990 の post-only 買い(対照)。最良の売り未満で、以後の約定は 9990 以下に来ない → 待ったまま(open)、約定 0。",
      base_input(market=mkt0() + [trade(T0 + 10 * MS, 10001, 1, "buy")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "limit", 1, px=10001, post_only=True),
                          place(T0 + 2 * MS, "o2", "buy", "limit", 1, px=9990, post_only=True)]),
      _o_postonly)


def _o_ioc(inp):
    a = action(inp, "o1")
    b = book_at(inp, a["t"])
    f, n = walk(b["asks"], a["qty"], limit=a["px"])
    return {"status.o1": "canceled", "filled.o1": f, "avg_px.o1": n / f}


scene("c2-1-ioc", "C2-1", "値", "IOC は、出した時に指値までにある分だけ埋まり、残りは取り消される",
      "IOC の部分約定と残りの取消",
      "板の売り 10001 x 0.3・10005 x 5。指値 10002 の IOC 買い 1 は、10002 以下の 0.3 だけ埋まり(値 10001)、残り 0.7 は取り消し(status canceled)。",
      base_input(market=[book(T0, [(9999, 5)], [(10001, 0.3), (10005, 5)])],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "limit", 1, px=10002, tif="IOC")]),
      _o_ioc)


def _o_fok(inp):
    a1, a2 = action(inp, "o1"), action(inp, "o2")
    b = book_at(inp, a1["t"])
    f1, _ = walk(b["asks"], a1["qty"], limit=a1["px"])
    assert f1 < a1["qty"]
    f2, n2 = walk(b["asks"], a2["qty"], limit=a2["px"])
    assert f2 == a2["qty"]
    return {"status.o1": op_in(["canceled", "rejected"]), "filled.o1": 0.0,
            "status.o2": "filled", "filled.o2": f2, "avg_px.o2": n2 / f2}


scene("c2-1-fok", "C2-1", "値", "FOK は、全量が埋まらないなら 1 つも埋まらず、全量が埋まるなら全量が埋まる",
      "FOK の全量か無しか",
      "板の売り 10001 x 0.3・10005 x 5。o1 = 指値 10002 の FOK 買い 1: 10002 以下は 0.3 < 1 → 約定 0 で終わる(取消か拒否)。"
      "o2 = 指値 10002 の FOK 買い 0.2(対照): 0.3 ≥ 0.2 → 全量 0.2 が 10001 で埋まる。",
      base_input(market=[book(T0, [(9999, 5)], [(10001, 0.3), (10005, 5)])],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "limit", 1, px=10002, tif="FOK"),
                          place(T0 + 2 * MS, "o2", "buy", "limit", 0.2, px=10002, tif="FOK")]),
      _o_fok)


def _o_stop(inp):
    a = action(inp, "o1")
    trig = next(e for e in trades_after(inp, a["t"]) if e["px"] >= a["stop_px"])
    b = book_at(inp, trig["t"])
    f, n = walk(b["asks"], a["qty"])
    return {"status.o1": "filled", "filled.o1": f, "avg_px.o1": n / f, "first_fill_t.o1": op_ge(trig["t"])}


scene("c2-1-stop", "C2-1", "値", "逆指値の買いは、約定の値が逆指値に届いた時に成行になり、その時の売りの気配で埋まる",
      "逆指値(stop)の発動と約定",
      "逆指値 10010 の買い 1。出した後の約定で 10010 以上になる最初は 10013(T0+20ms)。その時の板の最良の売りは 10013 → 10013 で全量。"
      "10005 の約定では発動しない(first_fill_t ≥ 発動の時刻)。",
      base_input(market=mkt0() + [trade(T0 + 10 * MS, 10005, 1, "buy"),
                                  book(T0 + 19 * MS, [(10011, 5)], [(10013, 5), (10014, 5)]),
                                  trade(T0 + 20 * MS, 10013, 1, "buy"), trade(T0 + 30 * MS, 10013, 1, "buy")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "stop", 1, stop_px=10010)]),
      _o_stop)


def _o_reduce(inp):
    a0, a2 = action(inp, "o0"), action(inp, "o2")
    return {"filled.o0": a0["qty"], "filled.o1": 0.0, "status.o1": op_in(["canceled", "rejected"]),
            "filled.o2": a2["qty"], "account.position": a0["qty"] - a2["qty"]}


scene("c2-1-reduceonly", "C2-1", "値", "reduce-only は建玉を減らす向きにだけ埋まり、増やす向きには埋まらない",
      "reduce-only の拒否と約定",
      "o0 = 成行の買い 2 で建玉 +2。o1 = reduce-only の成行の買い 1 は建玉を増やす → 約定 0(取消か拒否)。"
      "o2 = reduce-only の成行の売り 1(対照)は建玉を減らす → 1 埋まる。建玉 = 2 − 1 = 1。",
      base_input(market=mkt0() + [trade(T0 + 5 * MS, 10001, 1, "buy"), trade(T0 + 6 * MS, 9999, 1, "sell"),
                                  trade(T0 + 7 * MS, 9999, 1, "sell")],
                 actions=[place(T0 + 1 * MS, "o0", "buy", "market", 2),
                          place(T0 + 2 * MS, "o1", "buy", "market", 1, reduce_only=True),
                          place(T0 + 3 * MS, "o2", "sell", "market", 1, reduce_only=True)]),
      _o_reduce)


def _o_oco(inp):
    a1 = action(inp, "o1")
    first = next(e for e in trades_after(inp, a1["t"]) if e["px"] >= a1["px"])
    return {"status.o1": "filled", "filled.o1": a1["qty"], "avg_px.o1": a1["px"],
            "first_fill_t.o1": op_ge(first["t"]), "status.o2": "canceled", "filled.o2": 0.0,
            "account.position": 0.0}


scene("c2-1-oco", "C2-1", "値", "OCO は、片方が埋まるともう片方が取り消される",
      "OCO の連動の取消",
      "o0 = 成行の買い 1 で建玉 +1。o1 = 指値 10020 の売り 1 と o2 = 逆指値 9980 の売り 1 を OCO で結ぶ。"
      "10025 の約定で o1 が 10020 で埋まり、o2 は取り消し(後の 9970 の約定でも発動しない)。建玉 0。",
      base_input(market=mkt0() + [trade(T0 + 5 * MS, 10001, 1, "buy"), trade(T0 + 10 * MS, 10010, 1, "buy"),
                                  trade(T0 + 20 * MS, 10025, 5, "buy"), trade(T0 + 30 * MS, 9970, 5, "sell")],
                 actions=[place(T0 + 1 * MS, "o0", "buy", "market", 1),
                          place(T0 + 2 * MS, "o1", "sell", "limit", 1, px=10020, oco="o2"),
                          place(T0 + 2 * MS, "o2", "sell", "stop", 1, stop_px=9980, oco="o1")]),
      _o_oco)

# ======================= C2-2 取消・訂正・部分約定 =======================


def _o_cancel(inp):
    return {"status.o1": "canceled", "filled.o1": 0.0}


scene("c2-2-cancel", "C2-2", "値", "取り消した指値は、後で値が届いても埋まらない",
      "取消の状態遷移",
      "指値 9990 の買いを T0+1ms に出し T0+5ms に取り消す(遅延 0)。T0+10ms の 9985 の約定は取消の後 → 約定 0、status canceled。",
      base_input(market=mkt0() + [trade(T0 + 10 * MS, 9985, 5, "sell")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "limit", 1, px=9990), cancel(T0 + 5 * MS, "o1")]),
      _o_cancel)


def _o_amend_px(inp):
    am = next(a for a in inp["actions"] if a["op"] == "amend")
    return {"status.o1": "filled", "filled.o1": 1.0, "avg_px.o1": float(am["px"])}


scene("c2-2-amend-price", "C2-2", "値", "値を訂正した指値は、新しい値で埋まる",
      "訂正(値)の反映",
      "指値 9980 の買いを T0+5ms に 9990 へ訂正。T0+10ms の 9989 の約定は 9990 に届き 9980 には届かない → 新しい値 9990 で 1 埋まる。",
      base_input(market=mkt0() + [trade(T0 + 10 * MS, 9989, 5, "sell"), trade(T0 + 20 * MS, 9995, 1, "buy")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "limit", 1, px=9980), amend(T0 + 5 * MS, "o1", px=9990)]),
      _o_amend_px)


def _queue_fill(ahead, qty, trades_at_level):
    """Tier-5 FIFO rule: trades at our price consume the queue ahead first; we fill
    by the part that exceeds it, up to qty. Returns filled quantity."""
    consumed = sum(trades_at_level)
    return max(0.0, min(qty, consumed - ahead))


def _o_amend_qty(inp):
    b = book_at(inp, action(inp, "o1")["t"])
    ahead = dict((p, q) for p, q in b["bids"])[action(inp, "o1")["px"]]
    new_qty = next(a for a in inp["actions"] if a["op"] == "amend")["qty"]
    at_level = [e["qty"] for e in inp["market"] if e["type"] == "trade" and e["px"] == action(inp, "o1")["px"]]
    f = _queue_fill(ahead, new_qty, at_level)
    return {"filled.o1": f, "status.o1": "filled" if f == new_qty else "open"}


scene("c2-2-amend-qty", "C2-2", "能力", "数量を減らす訂正は列の順位を保つ(規則 amend_qty_down = keep_priority、列の模型 = 段 5)",
      "訂正(数量)と待ち行列の位置の保持",
      "9990 の外部の買いの待ち 3 の後ろに買い 2 を付ける(先行 3)。後から外部の 2 が後ろに付く(板 5)。数量を 1 に減らす訂正は順位を保つので先行は 3 のまま。"
      "9990 の約定 4 → 先行 3 を消化し残り 1 → 自分に min(1, 1) = 1。順位を失えば先行 5 で 0。",
      base_input(market=[book(T0, [(9990, 3), (9989, 5)], [(10001, 5)]), book(T0 + 2 * MS, [(9990, 5), (9989, 5)], [(10001, 5)]),
                         trade(T0 + 10 * MS, 9990, 4, "sell")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "limit", 2, px=9990), amend(T0 + 3 * MS, "o1", qty=1.0)],
                 fill_model={"tier": 5, "cancel_stance": "none"},
                 rules={"amend_qty_down": "keep_priority", "amend_price": "lose_priority"}),
      _o_amend_qty)


def _o_partial(inp):
    a = action(inp, "o1")
    cx = next(x for x in inp["actions"] if x["op"] == "cancel")
    before = [e for e in trades_after(inp, a["t"]) if e["t"] < cx["t"] and e["px"] <= a["px"]]
    f = min(a["qty"], sum(e["qty"] for e in before))
    return {"cum.o1@c1": f, "filled.o1": f, "status.o1": "canceled"}


scene("c2-2-partial", "C2-2", "能力", "部分約定した指値は残りが待ち、取り消すと約定済みの分だけ残る(約定の模型 = 段 4)",
      "部分約定と、部分約定の後の取消",
      "指値 9990 の買い 3。9985 の約定 1(段 4 = 値に届いた約定の数量まで埋まる)→ 1 埋まり 2 が残る(c1 の時点で累計 1)。"
      "取り消した後の 9980 の約定 5 では埋まらない → 終わりの約定 1、status canceled。",
      base_input(market=mkt0() + [trade(T0 + 10 * MS, 9985, 1, "sell"), trade(T0 + 30 * MS, 9980, 5, "sell")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "limit", 3, px=9990), cancel(T0 + 20 * MS, "o1")],
                 fill_model={"tier": 4}, checkpoints={"c1": T0 + 15 * MS}),
      _o_partial)

# ======================= C2-3 取引所固有の規則 =======================


def _o_tick(inp):
    a2 = action(inp, "o2")
    return {"status.o1": "rejected", "filled.o1": 0.0, "filled.o2": a2["qty"], "avg_px.o2": a2["px"]}


scene("c2-3-tick", "C2-3", "値", "呼値(1 円)に乗らない値の指値は拒否され、乗る値は受け付けられる",
      "呼値の拒否(規則 off_tick = reject、FX_BTC_JPY の呼値 1)",
      "o1 = 9990.5 は呼値 1 の整数倍でない → 拒否・約定 0。o2 = 9990(対照)は受け付けられ、9985 の約定で 9990 で 1 埋まる。",
      base_input(market=mkt0() + [trade(T0 + 10 * MS, 9985, 5, "sell")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "limit", 1, px=9990.5),
                          place(T0 + 2 * MS, "o2", "buy", "limit", 1, px=9990)]),
      _o_tick)


def _o_minqty(inp):
    a2 = action(inp, "o2")
    b = book_at(inp, a2["t"])
    return {"status.o1": "rejected", "filled.o1": 0.0, "filled.o2": a2["qty"], "avg_px.o2": b["asks"][0][0]}


scene("c2-3-minqty", "C2-3", "値", "最小数量(0.01)未満の注文は拒否され、最小数量ちょうどは受け付けられる",
      "最小数量の拒否(規則 below_min_qty = reject)",
      "o1 = 成行の買い 0.005 < 0.01 → 拒否・約定 0。o2 = 成行の買い 0.01(対照)→ 最良の売り 10001 で 0.01 埋まる。",
      base_input(market=mkt0() + [trade(T0 + 5 * MS, 10001, 1, "buy")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "market", 0.005),
                          place(T0 + 2 * MS, "o2", "buy", "market", 0.01)]),
      _o_minqty)


def _o_round(inp):
    a1, a2 = action(inp, "o1"), action(inp, "o2")
    tick = inp["product"]["tick"]
    return {"avg_px.o1": math.floor(a1["px"] / tick) * tick, "filled.o1": 1.0,
            "avg_px.o2": math.ceil(a2["px"] / tick) * tick, "filled.o2": 1.0}


scene("c2-3-round", "C2-3", "能力", "呼値に乗らない値を、受け身の側(買いは下、売りは上)へ丸めて受け付ける(規則 off_tick = round_passive)",
      "呼値への丸め",
      "o1 = 買い 9990.7 → 床 9990。o2 = 売り 10010.2 → 天井 10011。9985 の約定で o1 が 9990 で、10015 の約定で o2 が 10011 で埋まる。",
      base_input(market=mkt0() + [trade(T0 + 10 * MS, 9985, 5, "sell"), trade(T0 + 20 * MS, 10015, 5, "buy")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "limit", 1, px=9990.7),
                          place(T0 + 2 * MS, "o2", "sell", "limit", 1, px=10010.2)],
                 rules={"off_tick": "round_passive"}),
      _o_round)


def _o_stp(inp):
    return {"status.o2": "canceled", "filled.o2": 0.0, "status.o1": "open", "filled.o1": 0.0}


scene("c2-3-stp", "C2-3", "値", "自分の指値に自分の成行が当たるときは、当たる側(後の注文)を取り消す(規則 self_trade = cancel_taker)",
      "自己約定防止",
      "o1 = 売り指値 10000(外部の最良の売り 10001 より良い = 自分が最良の売り)。o2 = 成行の買い 1 は最良の売り = 自分の o1 に当たる → o2 を取り消し(約定 0)、o1 は待ったまま。",
      base_input(market=[book(T0, [(9999, 5)], [(10001, 5)])],
                 actions=[place(T0 + 1 * MS, "o1", "sell", "limit", 1, px=10000),
                          place(T0 + 2 * MS, "o2", "buy", "market", 1)],
                 rules={"self_trade": "cancel_taker"}),
      _o_stp)

JST = 9 * 3600 * SEC
D_JPX = 1_767_657_600 * SEC  # 2026-01-06 00:00:00 UTC (Tuesday)


def jst(h, m, s=0):
    return D_JPX - JST + (h * 3600 + m * 60 + s) * SEC


JPX_RULES = {"sessions_jst": [["09:00", "11:30"], ["12:30", "15:30"]], "outside_session": "queue_to_next_open",
             "source": "東京証券取引所の立会時間(前場 9:00-11:30、後場 12:30-15:30)。一次資料の頁の確認は本役では未実施(委任文 §4 のネットワークの規則)"}


def _o_jpx_session(inp):
    a = action(inp, "o1")
    reopen = jst(12, 30)
    first = next(e for e in inp["market"] if e["type"] == "trade" and e["t"] >= reopen)
    return {"filled.o1": a["qty"], "avg_px.o1": first["px"], "first_fill_t.o1": op_ge(reopen)}


scene("c2-3-jpx-session", "C2-3", "値", "JPX の昼休み(11:30-12:30)に出した成行は、後場の始まりに後場の最初の値で埋まる",
      "JPX の取引時間(規則 sessions_jst・outside_session = queue_to_next_open)",
      "11:45 JST の成行の買い 100。前場の最後の約定 1500(11:29)では埋まらない。後場の最初の約定 1510(12:30:00)で全量、時刻は 12:30 以後。",
      base_input(product=JPX_STOCK, rules=JPX_RULES,
                 market=[book(jst(11, 29), [(1499, 5000)], [(1501, 5000)]), trade(jst(11, 29), 1500, 1000, "buy"),
                         book(jst(12, 30), [(1509, 5000)], [(1510, 5000)]), trade(jst(12, 30), 1510, 5000, "buy"),
                         trade(jst(12, 31), 1512, 1000, "buy")],
                 actions=[place(jst(11, 45), "o1", "buy", "market", 100)], end_t=jst(13, 0)),
      _o_jpx_session)


def _o_jpx_limit(inp):
    base, width = inp["rules"]["price_limit"]["base"], inp["rules"]["price_limit"]["width"]
    a1, a2 = action(inp, "o1"), action(inp, "o2")
    assert not (base - width <= a1["px"] <= base + width) and base - width <= a2["px"] <= base + width
    b = book_at(inp, a2["t"])
    assert a2["px"] < b["asks"][0][0] and a2["px"] not in [p for p, _ in b["bids"]]  # rests with nothing ahead
    return {"status.o1": "rejected", "filled.o1": 0.0, "filled.o2": a2["qty"], "avg_px.o2": a2["px"]}


scene("c2-3-jpx-limit", "C2-3", "値", "JPX の値幅制限の外の指値は拒否され、内の指値は受け付けられる",
      "JPX の値幅制限(基準値 1000 円 → 制限値幅 300 円 = 700〜1300 円)",
      "基準値 1000・値幅 300 → 700〜1300。o1 = 買い 1350 は外 → 拒否(受け付けたら最良の売り 1252 に当たる)。"
      "o2 = 買い 1250(対照)は内で、最良の売り 1252 未満・1250 に外部の待ちなし → 待ち、1250 の約定で 100 が 1250 で埋まる。",
      base_input(product=JPX_STOCK,
                 rules=dict(JPX_RULES, price_limit={"base": 1000.0, "width": 300.0,
                                                    "source": "東京証券取引所の制限値幅の表(基準値段 1,000 円以上 1,500 円未満 → 300 円)。一次資料の頁の確認は本役では未実施(委任文 §4)"}),
                 market=[book(jst(10, 0), [(1249, 5000)], [(1252, 5000)]), trade(jst(10, 0), 1251, 100, "buy"),
                         trade(jst(10, 5), 1250, 1000, "sell"), trade(jst(10, 6), 1240, 1000, "sell")],
                 actions=[place(jst(10, 1), "o1", "buy", "limit", 100, px=1350),
                          place(jst(10, 2), "o2", "buy", "limit", 100, px=1250)], end_t=jst(10, 30)),
      _o_jpx_limit)

FRI = 1_767_992_400 * SEC  # 2026-01-09 21:00:00 UTC (Friday)


def _o_fx_weekend(inp):
    a = action(inp, "o1")
    reopen = inp["rules"]["closed_utc_ns"][0][1]
    b = book_at(inp, reopen)
    return {"filled.o1": a["qty"], "avg_px.o1": b["asks"][0][0], "first_fill_t.o1": op_ge(reopen)}


scene("c2-3-fx-weekend", "C2-3", "値", "FX の週末(金 22:00 UTC 〜 日 22:00 UTC)に出した成行は、週明けの最初の気配で埋まる",
      "FX の取引時間(規則 closed_utc_ns・outside_session = queue_to_next_open)",
      "土曜 03:00 UTC の成行の買い 10000。金曜の最後の気配(売り 150.003)では埋まらない。日曜 22:00 UTC の最初の気配の売り 150.103 で全量、時刻は再開以後。",
      base_input(product=USDJPY,
                 rules={"closed_utc_ns": [[FRI + 1 * 3600 * SEC, FRI + 49 * 3600 * SEC]], "outside_session": "queue_to_next_open",
                        "source": "FX の週末の閉場(冬時間、金曜 17:00 ニューヨーク〜日曜 17:00 ニューヨーク)。一次資料の頁の確認は本役では未実施(委任文 §4)"},
                 market=[book(FRI + 59 * 60 * SEC, [(150.000, 1e6)], [(150.003, 1e6)]),
                         trade(FRI + 59 * 60 * SEC, 150.001, 1e4, "buy"),
                         book(FRI + 49 * 3600 * SEC, [(150.100, 1e6)], [(150.103, 1e6)]),
                         trade(FRI + 49 * 3600 * SEC + 1 * MS, 150.103, 1e4, "buy")],
                 actions=[place(FRI + 6 * 3600 * SEC, "o1", "buy", "market", 10000)],
                 end_t=FRI + 50 * 3600 * SEC),
      _o_fx_weekend)

# ======================= C2-4 異常系の注入 =======================


def _o_inject_reject(inp):
    a1, a2 = action(inp, "o1"), action(inp, "o2")
    return {"status.o1": "rejected", "filled.o1": 0.0, "notice.o1.reject": op_ge(a1["t"]),
            "filled.o2": a2["qty"], "avg_px.o2": book_at(inp, a2["t"])["asks"][0][0]}


scene("c2-4-reject", "C2-4", "値", "注入した拒否で、その注文は拒否され、戦略に拒否の知らせが届く",
      "拒否の注入",
      "o1 に拒否を注入 → status rejected・約定 0・拒否の知らせが o1 を出した時刻以後に届く。o2(対照、注入なし)は 10001 で 1 埋まる。",
      base_input(market=mkt0() + [trade(T0 + 5 * MS, 10001, 1, "buy")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "market", 1), place(T0 + 2 * MS, "o2", "buy", "market", 1)],
                 inject=[{"kind": "reject", "ref": "o1"}]),
      _o_inject_reject)


def _o_unknown(inp):
    return {"status.o1": "state_unknown", "sent.o1": 1, "filled.o1": 0.0}


scene("c2-4-timeout", "C2-4", "値", "発注の時間切れは状態不明として保持され、自動で再送されない",
      "時間切れの注入(CLAUDE.md §1: 曖昧な失敗は STATE_UNKNOWN、自動で再送しない)",
      "o1 の発注に時間切れ(応答なし)を注入 → 状態不明のまま終わる・取引所に届いた発注は 1 回(再送 0)・約定を仮定しない(0)。",
      base_input(market=mkt0() + [trade(T0 + 5 * MS, 10001, 1, "buy")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "market", 1)],
                 inject=[{"kind": "timeout", "ref": "o1"}]),
      _o_unknown)

scene("c2-4-unknown", "C2-4", "値", "曖昧な失敗は状態不明として保持され、自動で再送されない",
      "状態不明の注入(CLAUDE.md §1)",
      "o1 の発注の応答に曖昧な失敗を注入 → 状態不明・届いた発注 1 回・約定を仮定しない(0)。",
      base_input(market=mkt0() + [trade(T0 + 5 * MS, 10001, 1, "buy")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "market", 1)],
                 inject=[{"kind": "unknown", "ref": "o1"}]),
      _o_unknown)


def _o_kill(inp):
    return {"status.o2": "rejected", "sent.o2": 0, "filled.o2": 0.0,
            "status.o3": "rejected", "sent.o3": 0, "filled.o3": 0.0}


scene("c2-4-kill", "C2-4", "値", "Kill Switch の後の新しい注文は取引所へ送られず拒否され、その後も戻らない",
      "Kill Switch での停止",
      "T0+5ms に Kill Switch。o2(T0+6ms)と o3(T0+20ms)は送られず(届いた発注 0)拒否・約定 0。自動で戻らないので o3 も拒否。",
      base_input(market=mkt0() + [trade(T0 + 10 * MS, 10001, 1, "buy"), trade(T0 + 25 * MS, 10001, 1, "buy")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "limit", 1, px=9990), kill(T0 + 5 * MS),
                          place(T0 + 6 * MS, "o2", "buy", "market", 1), place(T0 + 20 * MS, "o3", "buy", "market", 1)]),
      _o_kill)

# ======================= C2-5 約定/待ち行列の段 =======================
TIER_T = T0 + 500 * MS


def tier_input(tier, with_through=True):
    mk = [book(T0, [(9999, 5), (9995, 2)], [(10001, 5)]), trade(T0, 10000, 0.1, "buy"),
          trade(T0 + 1010 * MS, 9995, 1, "sell"), trade(T0 + 1020 * MS, 9995, 1.5, "sell")]
    if with_through:
        mk.append(trade(T0 + 1030 * MS, 9994, 1, "sell"))
    return base_input(market=mk, actions=[place(TIER_T, "o1", "buy", "limit", 2, px=9995)],
                      fill_model={"tier": tier, "cancel_stance": "none", "bar_ns": 1 * SEC},
                      checkpoints={"c1": T0 + 1015 * MS, "c2": T0 + 1025 * MS, "c3": T0 + 1035 * MS,
                                   "cend": T0 + 2500 * MS},
                      end_t=T0 + 3 * SEC)


def tier_path(inp):
    """Cumulative filled at each checkpoint for the declared tier (the rules below are
    the scene's concrete reading of the catalogue §2.1 one-line definitions):
      0 = fills in full at placement, at the limit
      1 = fills in full at the first trade STRICTLY through the limit (price crosses)
      2 = bars of bar_ns; fills in full at the close of the first bar after the placement
          bar whose low reaches the limit
      3 = fills in full at the arrival of the first trade that reaches the limit (touch)
      4 = trades reaching the limit fill up to their quantity (no queue)
      5 = FIFO queue: ahead = displayed size at the price at placement; trades at the price
          consume ahead first; a trade strictly through fills the whole remainder."""
    fm, a = inp["fill_model"], action(inp, "o1")
    tier, L, q = fm["tier"], a["px"], a["qty"]
    trades = [e for e in inp["market"] if e["type"] == "trade" and e["t"] > a["t"]]
    fills = []  # (t, qty)
    if tier == 0:
        fills = [(a["t"], q)]
    elif tier in (1, 3):
        hit = next((e for e in trades if (e["px"] < L if tier == 1 else e["px"] <= L)), None)
        fills = [(hit["t"], q)] if hit else []
    elif tier == 2:
        bn = fm["bar_ns"]
        place_bar = (a["t"] - T0) // bn
        by_bar = {}
        for e in trades:
            by_bar.setdefault((e["t"] - T0) // bn, []).append(e)
        for k in sorted(by_bar):
            if k > place_bar and min(e["px"] for e in by_bar[k]) <= L:
                fills = [(T0 + (k + 1) * bn, q)]
                break
    elif tier == 4:
        left = q
        for e in trades:
            if e["px"] <= L and left > 0:
                take = min(left, e["qty"])
                fills.append((e["t"], take))
                left -= take
    elif tier == 5:
        ahead = dict((p, s) for p, s in book_at(inp, a["t"])["bids"]).get(L, 0.0)
        left = q
        for e in trades:
            if left <= 0:
                break
            if e["px"] == L:
                use = min(ahead, e["qty"])
                ahead -= use
                take = min(left, e["qty"] - use)
                if take > 0:
                    fills.append((e["t"], take))
                    left -= take
            elif e["px"] < L:
                fills.append((e["t"], left))
                left = 0
    out = {}
    for cp, ct in inp["checkpoints"].items():
        out[f"cum.o1@{cp}"] = float(sum(x for t, x in fills if t <= ct))
    if fills:
        out["first_fill_t.o1"] = fills[0][0]
    return out


TIER_TEXT = {
    0: "段 0 = 出した時点で指値で全量が埋まる。c1〜cend の累計 2、最初の約定の時刻 = 出した時刻。",
    1: "段 1 = 値が指値を跨いだ(買いなら指値より下の約定)最初の時点で全量。9995 の約定 2 本は跨いでいない、9994(T0+1030ms)で跨ぐ → c1・c2 は 0、c3・cend は 2。",
    2: "段 2 = 1 秒の足。出した足(0 秒目)より後の足で安値が指値に届いた最初の足の終わり(T0+2s)に全量。c1〜c3 は 0、cend は 2。",
    3: "段 3 = 指値に届いた約定の事象が来た時点で全量。9995(T0+1010ms)で届く → c1 から 2、最初の約定の時刻 T0+1010ms。",
    4: "段 4 = 指値に届いた約定の数量まで埋まる(列なし)。1010ms に 1、1020ms に残り 1 → c1 = 1、c2 以後 2。",
    5: "段 5 = 列: 出した時の 9995 の表示 2 が先行。1010ms の 1 と 1020ms の 1.5 で先行 2 を消化し 0.5 が自分へ、1030ms の 9994 は跨ぐので残り 1.5 → c1 = 0、c2 = 0.5、c3・cend = 2。",
}

for _tier in range(6):
    scene(f"c2-5-tier{_tier}", "C2-5", "能力", f"約定の模型の段 {_tier} を選べ、選んだ段の規則どおりに埋まる",
          f"段 {_tier} を選べること(選んだ段の埋まり方の累計が正解と一致)",
          "指値 9995 の買い 2(T0+500ms)。板の 9995 に外部の 2。約定 9995 x 1(T0+1010ms)・9995 x 1.5(1020ms)・9994 x 1(1030ms)。"
          + TIER_TEXT[_tier] + "(段の規則の文は道具台帳 §2.1 の 1 行の定義を、この場面の入力で測れる形に場面係が具体にしたもの)",
          tier_input(_tier), tier_path)


def _o_tier6(inp):
    a = action(inp, "o1")
    k = inp["fill_model"]["impact"]["k"]
    px = book_at(inp, a["t"])["asks"][0][0] + k * a["qty"]
    return {"filled.o1": a["qty"], "avg_px.o1": px}


scene("c2-5-tier6", "C2-5", "能力", "約定の模型の段 6(市場影響の関数)を選べ、関数どおりの値で埋まる",
      "段 6 を選べること(一時的な影響 = 最良の売り + k × 数量)",
      "成行の買い 3、k = 2 円/単位。最良の売り 10001 + 2 × 3 = 10007 で全量。",
      base_input(market=mkt0() + [trade(T0 + 5 * MS, 10001, 5, "buy")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "market", 3)],
                 fill_model={"tier": 6, "impact": {"kind": "linear_temporary", "k": 2.0, "basis": "best_ask"}}),
      _o_tier6)

# ======================= C2-6 先行注文の取り消しの扱い =======================
CXL_T = T0 + 1 * MS


def cxl_input(stance, **extra):
    fm = {"tier": 5, "cancel_stance": stance}
    fm.update(extra)
    if stance == "l3":
        mk = [{"t": T0, "type": "l3_add", "id": f"e{i}", "side": "bid", "px": 9995.0, "qty": 1.0} for i in range(1, 6)]
        mk += [book(T0, [(9995, 5), (9990, 5)], [(10001, 5)])]
        mk += [{"t": T0 + 2 * MS, "type": "l3_add", "id": f"e{i}", "side": "bid", "px": 9995.0, "qty": 1.0} for i in (6, 7, 8)]
        mk += [{"t": T0 + 3 * MS, "type": "l3_cancel", "id": i} for i in ("e1", "e2", "e3", "e6")]
        mk += [trade(T0 + 10 * MS, 9995, 4.5, "sell")]
    else:
        mk = [book(T0, [(9995, 5), (9990, 5)], [(10001, 5)]), book(T0 + 2 * MS, [(9995, 8), (9990, 5)], [(10001, 5)]),
              book(T0 + 3 * MS, [(9995, 4), (9990, 5)], [(10001, 5)]), trade(T0 + 10 * MS, 9995, 4.5, "sell")]
    return base_input(market=mk, actions=[place(CXL_T, "o1", "buy", "limit", 3, px=9995)], fill_model=fm,
                      end_t=T0 + 50 * MS)


def cxl_filled(inp):
    """Queue ahead of us after the declared stance, then FIFO consumption by the trade
    at our price (catalogue §2.2 stances; prob = hftbacktest-documented ProbQueueModel form)."""
    fm, a = inp["fill_model"], action(inp, "o1")
    L, q = a["px"], a["qty"]
    st = fm["cancel_stance"]
    if st == "l3":
        ahead_ids = [e["id"] for e in inp["market"] if e["type"] == "l3_add" and e["t"] <= a["t"] and e["px"] == L]
        gone = {e["id"] for e in inp["market"] if e["type"] == "l3_cancel"}
        ahead = float(sum(1.0 for i in ahead_ids if i not in gone))
    else:
        books = [e for e in inp["market"] if e["type"] == "book"]
        size = lambda b: dict((p, s) for p, s in b["bids"]).get(L, 0.0)  # noqa: E731
        ahead = size(book_at(inp, a["t"]))
        if st == "discount_at_entry":
            ahead = ahead * (1.0 - fm["cancel_rate"])
        prev = size(book_at(inp, a["t"]))
        for b in books:
            if b["t"] <= a["t"]:
                continue
            new = size(b)
            if st == "snapshot_cap":
                ahead = min(ahead, new)
            elif st == "prob":
                chg = prev - new
                if chg > 0:
                    front, back = ahead, prev - ahead
                    prob = back / (back + front)  # f(x) = x
                    ahead = min(front - (1 - prob) * chg + min(back - prob * chg, 0.0), new)
            prev = new
    at_level = [e["qty"] for e in inp["market"] if e["type"] == "trade" and e["px"] == L]
    return {"filled.o1": _queue_fill(ahead, q, at_level)}


CXL_TEXT = {
    "none": ("何もしない(先行の取消は見えないので繰り上がらない)",
             "先行 5 のまま。約定 4.5 < 5 → 0。"),
    "discount_at_entry": ("出した瞬間に 1 回、平均の取消率 r で先行を割り引く(r = 0.4)",
                          "先行 5 × (1 − 0.4) = 3。約定 4.5 − 3 = 1.5 → min(3, 1.5) = 1.5。"),
    "snapshot_cap": ("板の写真の量が先行量を下回ったら、先行量をその量まで下げる",
                     "T0+2ms の 8 では変わらず、T0+3ms の 4 で先行 = min(5, 4) = 4。4.5 − 4 = 0.5。"),
    "l3": ("取り消された注文が列から抜ける(取消の時点で繰り上がる / 印を付けて通り過ぎる。2 つの立場の埋まる量は同じ)",
           "先行 e1〜e5 のうち e1・e2・e3 が取消 → 先行 2(後ろの e6 の取消は先行に響かない)。4.5 − 2 = 2.5 → min(3, 2.5) = 2.5。"),
    "prob": ("確率型の列: 板の減少のうち前にあった割合 = f(後ろ)/(f(後ろ)+f(前))、f(x) = x",
             "T0+2ms の増加 5→8 は後ろだけ(前 5・後ろ 3)。T0+3ms の減少 4: prob = 3/8、前 = 5 − (1 − 3/8) × 4 + min(3 − 3/8 × 4, 0) = 2.5。4.5 − 2.5 = 2 → 2。"),
}

for _st, _extra in (("none", {}), ("discount_at_entry", {"cancel_rate": 0.4}), ("snapshot_cap", {}),
                    ("l3", {}), ("prob", {"prob_f": "identity"})):
    scene(f"c2-6-{_st.replace('_', '-')}", "C2-6", "能力", f"先行注文の取り消しの扱い「{CXL_TEXT[_st][0]}」を選べ、その規則どおりに埋まる",
          "先行注文の取り消しの扱いを選べること(埋まる量が立場の規則の正解と一致)",
          "9995 の外部の買い 5 の後ろに買い 3(先行 5)。外部の 3 が後ろに付き(板 8)、4 が取り消される(板 4。L3 の場面では e1・e2・e3・e6)。9995 の約定 4.5。"
          + CXL_TEXT[_st][1],
          cxl_input(_st, **_extra), cxl_filled)

# ======================= C2-7 板を辿る成行・市場影響 =======================


def _o_walk(inp):
    a = action(inp, "o1")
    f, n = walk(book_at(inp, a["t"])["asks"], a["qty"])
    out = {"filled.o1": f, "avg_px.o1": n / f}
    out["status.o1"] = "filled" if f == a["qty"] else "canceled"
    return out


scene("c2-7-walk", "C2-7", "値", "板の厚みを超える成行は、良い方から値位をまたいで埋まる",
      "板を辿る成行",
      "売り 10001 x 0.5・10002 x 0.7・10005 x 5 に成行の買い 1.5 → 0.5@10001 + 0.7@10002 + 0.3@10005、加重平均 = (5000.5 + 7001.4 + 3001.5) / 1.5。",
      base_input(market=[book(T0, [(9999, 5)], [(10001, 0.5), (10002, 0.7), (10005, 5)])],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "market", 1.5)]),
      _o_walk)

scene("c2-7-walk-exhaust", "C2-7", "値", "板の全部より大きい成行は、ある分だけ埋まり残りは取り消される(規則 market_remainder = cancel)",
      "板を辿る成行(板が尽きる)",
      "売り 10001 x 0.5・10002 x 0.7 だけに成行の買い 2 → 1.2 埋まり(加重平均 (5000.5 + 7001.4) / 1.2)、残り 0.8 は取り消し。",
      base_input(market=[book(T0, [(9999, 5)], [(10001, 0.5), (10002, 0.7)])],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "market", 2)]),
      _o_walk)


def _o_sqrt(inp):
    a = action(inp, "o1")
    im = inp["fill_model"]["impact"]
    b = book_at(inp, a["t"])
    mid = (b["bids"][0][0] + b["asks"][0][0]) / 2
    return {"filled.o1": a["qty"], "avg_px.o1": mid * (1 + im["eta"] * math.sqrt(a["qty"] / im["adv"]))}


scene("c2-7-impact-sqrt", "C2-7", "能力", "平方根の市場影響の関数を渡すと、その関数どおりの値で埋まる",
      "市場影響の関数(値 = 仲値 × (1 + η √(数量 / 1 日の出来高)))",
      "仲値 10000、η = 0.1、1 日の出来高 100、成行の買い 1 → 10000 × (1 + 0.1 × √0.01) = 10100。",
      base_input(market=mkt0() + [trade(T0 + 5 * MS, 10000, 5, "buy")], actions=[place(T0 + 1 * MS, "o1", "buy", "market", 1)],
                 fill_model={"tier": 6, "impact": {"kind": "sqrt_temporary", "eta": 0.1, "adv": 100.0, "basis": "mid"}}),
      _o_sqrt)


def _o_perm(inp):
    g = inp["fill_model"]["impact"]["gamma"]
    a1, a2 = action(inp, "o1"), action(inp, "o2")
    ask = book_at(inp, a1["t"])["asks"][0][0]
    return {"avg_px.o1": ask, "avg_px.o2": ask + g * a1["qty"], "filled.o2": a2["qty"]}


scene("c2-7-impact-permanent", "C2-7", "能力", "恒久的な市場影響は、自分の約定の後の値を動かし、次の約定の値に効く",
      "市場影響の関数(恒久的な影響 = γ × 約定した数量だけ以後の値が動く)",
      "γ = 5 円/単位。成行の買い 1 → 最良の売り 10001。以後の値は +5 → 次の成行の買い 1 は 10006。",
      base_input(market=mkt0() + [trade(T0 + 5 * MS, 10001, 5, "buy")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "market", 1), place(T0 + 2 * MS, "o2", "buy", "market", 1)],
                 fill_model={"tier": 6, "impact": {"kind": "linear_permanent", "gamma": 5.0, "k": 0.0, "basis": "best_ask"}}),
      _o_perm)

# ======================= C2-8 楽観側・悲観側の幅 =======================


def range_input(pess=True):
    inp = tier_input(3, with_through=False)
    inp["fill_model"] = {"range": {"optimistic": {"tier": 3, "cancel_stance": "none"}}}
    if pess:
        inp["fill_model"]["range"]["pessimistic"] = {"tier": 1, "cancel_stance": "none"}
    inp["checkpoints"] = {"cend": T0 + 2500 * MS}
    return inp


def _o_range(inp):
    out = {}
    for side, fm in inp["fill_model"]["range"].items():
        sub = copy.deepcopy(inp)
        sub["fill_model"] = dict(fm, bar_ns=1 * SEC)
        out[f"range.{side}.cum.o1@cend"] = tier_path(sub)["cum.o1@cend"]
    return out


scene("c2-8-range", "C2-8", "値", "同じ場面を楽観側と悲観側の両方で回し、埋まる量を幅で出す",
      "楽観側(段 3 = 触れたら埋まる)と悲観側(段 1 = 跨いだら埋まる)の幅",
      "段 5 の場面から跨ぐ約定(9994)を除いた入力。楽観側は 9995 に触れた時点で 2、悲観側は跨がないので 0 → 幅 [0, 2]。",
      range_input(True), _o_range)

scene("c2-8-both-required", "C2-8", "能力", "片側だけを指定した実行は、単一の値を出さずに断る",
      "楽観側と悲観側の両方を必ず回すこと(片側だけでは断る)",
      "対照 = 両側を指定(c2-8-range と同じ正解)。変形 = 楽観側だけを指定 → 断る(単一の値を返したら不一致)。",
      range_input(True), _o_range, variant=range_input(False))

# ======================= C2-9 遅延の模型 =======================


def lat(feed=0, order=0, cancel=0, notice=0):
    return {k: {"kind": "constant", "ns": int(v)} for k, v in
            (("feed", feed), ("order", order), ("cancel", cancel), ("notice", notice))}


def _o_order_lat(inp):
    L = inp["latency"]
    a = action(inp, "o1")
    arrive = a["t"] + L["order"]["ns"]
    ask = book_at(inp, arrive)["asks"][0][0]
    b12 = next(e for e in inp["market"] if e.get("label") == "b12")
    return {"avg_px.o1": ask, "first_fill_t.o1": arrive, "seen.b12": b12["t"] + L["feed"]["ns"]}


scene("c2-9-order-feed", "C2-9", "値", "発注の遅れの分だけ遅れて取引所に届き、その時の板で埋まる。配信の遅れの分だけ遅れて戦略に見える",
      "配信の遅れ(5ms)と発注の遅れ(10ms)を別々に",
      "T0+5ms(戦略の時刻)の成行の買いは T0+15ms に届く。T0+12ms に最良の売りが 10003 に変わっている → 10003 で埋まり、約定の時刻 T0+15ms。"
      "T0+12ms の板(印 b12)は戦略に T0+17ms に見える。",
      base_input(market=[book(T0, [(9999, 5)], [(10001, 5)]), book(T0 + 12 * MS, [(10000, 5)], [(10003, 5)], label="b12")],
                 actions=[place(T0 + 5 * MS, "o1", "buy", "market", 1)], latency=lat(feed=5 * MS, order=10 * MS)),
      _o_order_lat)


def _o_cancel_lat(inp):
    L = inp["latency"]
    a = action(inp, "o1")
    cx = next(x for x in inp["actions"] if x["op"] == "cancel")
    arrive_order = a["t"] + L["order"]["ns"]
    arrive_cancel = cx["t"] + L["cancel"]["ns"]
    tr = next(e for e in trades_after(inp, arrive_order) if e["px"] <= a["px"])
    if tr["t"] < arrive_cancel:
        return {"status.o1": "filled", "filled.o1": a["qty"]}
    return {"status.o1": "canceled", "filled.o1": 0.0}


for _name, _cl, _txt in (("late", 20, "取消は T0+25ms に届く。T0+15ms の 9985 の約定が先 → 1 埋まる(取消は間に合わない)。"),
                         ("early", 5, "取消は T0+10ms に届く。T0+15ms の 9985 の約定より先 → 取り消し、約定 0。")):
    scene(f"c2-9-cancel-{_name}", "C2-9", "値", f"取消の遅れ({_cl}ms)は発注の遅れ(0)と別に効く",
          "取消の遅れを発注の遅れと別々に",
          "指値 9990 の買い(T0+1ms、発注の遅れ 0)を T0+5ms に取り消す。" + _txt,
          base_input(market=mkt0() + [trade(T0 + 15 * MS, 9985, 5, "sell")],
                     actions=[place(T0 + 1 * MS, "o1", "buy", "limit", 1, px=9990), cancel(T0 + 5 * MS, "o1")],
                     latency=lat(cancel=_cl * MS)),
          _o_cancel_lat)


def _o_notice(inp):
    L = inp["latency"]
    a1, a2 = action(inp, "o1"), action(inp, "o2")
    d = L["order"]["ns"] + L["notice"]["ns"]
    return {"notice.o1.terminal": a1["t"] + d, "notice.o2.ack": a2["t"] + d,
            "status.o1": op_in(["rejected", "canceled"]), "status.o2": "open"}


scene("c2-9-notice", "C2-9", "値", "受付と拒否の知らせも事象で、発注の遅れ + 知らせの遅れの後に戦略に届く",
      "受付・拒否の知らせの事象と遅れ",
      "発注の遅れ 10ms、知らせの遅れ 7ms。o1 = 交差する post-only(T0+1ms)→ 約定なしで終わった知らせ(拒否か取消)が T0+18ms。o2 = 交差しない post-only(T0+2ms)→ 受付の知らせ T0+19ms。",
      base_input(market=mkt0(), actions=[place(T0 + 1 * MS, "o1", "buy", "limit", 1, px=10001, post_only=True),
                                          place(T0 + 2 * MS, "o2", "buy", "limit", 1, px=9990, post_only=True)],
                 latency=lat(order=10 * MS, notice=7 * MS)),
      _o_notice)


def _o_empirical(inp):
    s = inp["latency"]["order"]["samples_ns"]
    return {f"lat_in.{r}": op_in(s) for r in ("o1", "o2", "o3")}


scene("c2-9-empirical", "C2-9", "能力", "実測の分布(標本の列)と種から発注の遅れを引き、引いた遅れで届く",
      "実測の分布・種つきの乱数の遅れ",
      "発注の遅れ = 標本 {3, 7, 11}ms から種 7 で引く。3 本の成行の買いの(約定の時刻 − 出した時刻)が、どれも標本のどれかに一致する。"
      "同じ種の 2 回の実行が同じになるかは再現の欄で見る。",
      base_input(market=mkt0(), actions=[place(T0 + 1 * MS, "o1", "buy", "market", 0.1),
                                          place(T0 + 100 * MS, "o2", "buy", "market", 0.1),
                                          place(T0 + 200 * MS, "o3", "buy", "market", 0.1)],
                 latency={"feed": {"kind": "constant", "ns": 0},
                          "order": {"kind": "empirical", "samples_ns": [3 * MS, 7 * MS, 11 * MS], "seed": 7},
                          "cancel": {"kind": "constant", "ns": 0}, "notice": {"kind": "constant", "ns": 0}}),
      _o_empirical)

# ======================= C2-10 費用 =======================


def _o_taker(inp):
    a = action(inp, "o1")
    px = book_at(inp, a["t"])["asks"][0][0]
    return {"fee.o1": rate_fee(inp["costs"]["taker_rate"], px, a["qty"]), "avg_px.o1": px}


TAKER_COSTS = {"maker_rate": 0.0002, "taker_rate": 0.0005,
               "source": "場面の定義(手数料の率を測るための合成の値。取引所の料率ではない)"}
scene("c2-10-taker", "C2-10", "値", "成行の約定に taker の手数料が掛かる",
      "taker の手数料",
      "成行の買い 1 が 10001 で埋まる。taker の率 0.0005 → 0.0005 × 10001 × 1 = 5.0005。",
      base_input(market=mkt0() + [trade(T0 + 5 * MS, 10001, 1, "buy")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "market", 1)], costs=dict(TAKER_COSTS)),
      _o_taker)


def _o_maker(inp):
    a = action(inp, "o1")
    return {"fee.o1": rate_fee(inp["costs"]["maker_rate"], a["px"], a["qty"]), "filled.o1": a["qty"]}


scene("c2-10-maker", "C2-10", "値", "待っていた指値の約定に maker の手数料(負 = 払い戻し)が掛かる",
      "maker の手数料(払い戻しを含む)",
      "指値 9990 の買い 1 が 9985 の約定で 9990 で埋まる。maker の率 −0.0001 → −0.0001 × 9990 × 1 = −0.999(払い戻し)。",
      base_input(market=mkt0() + [trade(T0 + 10 * MS, 9985, 5, "sell")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "limit", 1, px=9990)],
                 costs={"maker_rate": -0.0001, "taker_rate": 0.0005, "source": "場面の定義(合成の値)"}),
      _o_maker)


def _o_spread(inp):
    a = action(inp, "o1")
    return {"avg_px.o1": inp["costs"]["mid"] + inp["costs"]["spread"] / 2, "filled.o1": a["qty"]}


scene("c2-10-spread", "C2-10", "値", "スプレッドの費用: 成行の買いは仲値 + スプレッドの半分で埋まる",
      "スプレッド",
      "仲値 10000、スプレッド 2(板は 9999 / 10001 で同じ)。成行の買い 1 → 10000 + 1 = 10001。",
      base_input(market=[book(T0, [(9999, 5)], [(10001, 5)]), trade(T0, 10000, 0.1, "buy"), trade(T0 + 5 * MS, 10000, 5, "buy")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "market", 1)],
                 costs=dict(ZERO_COSTS, spread=2.0, mid=10000.0)),
      _o_spread)


def _o_funding(inp):
    f = next(e for e in inp["market"] if e["type"] == "funding")
    pos = action(inp, "o1")["qty"]
    return {"costs.funding": f["rate"] * f["mark"] * pos}


scene("c2-10-funding", "C2-10", "値", "資金調達の事象で、建玉 × 値 × 率が払われる(FX_BTC_JPY)",
      "資金調達(FX_BTC_JPY)",
      "買い 1 の建玉。T0+1h の資金調達の事象(率 0.0001、値 10000)→ 買いの側が 0.0001 × 10000 × 1 = 1.0 を払う。",
      base_input(market=mkt0() + [trade(T0 + 5 * MS, 10001, 1, "buy"),
                                  {"t": T0 + 3600 * SEC, "type": "funding", "rate": 0.0001, "mark": 10000.0}],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "market", 1)], end_t=T0 + 3601 * SEC,
                 costs=dict(ZERO_COSTS, funding="apply_events")),
      _o_funding)

TUE = 1_767_733_200 * SEC  # 2026-01-06 21:00:00 UTC


def _o_swap(inp):
    sw = inp["costs"]["swap"]
    n = sum(1 for e in inp["market"] if e["type"] == "rollover")
    return {"costs.swap": -sw["long_credit_per_unit_per_day"] * action(inp, "o1")["qty"] * n}


scene("c2-10-swap", "C2-10", "値", "FX のスワップは、日をまたぐ時点(ロールオーバー)の建玉に付く",
      "スワップ(FX)",
      "USDJPY の買い 10000。22:00 UTC のロールオーバー 1 回。買いの受け取り 0.015 円/単位/日 → 150 円の受け取り(払いは −150)。",
      base_input(product=USDJPY,
                 market=[book(TUE, [(150.000, 1e6)], [(150.003, 1e6)]), trade(TUE, 150.001, 1e4, "buy"),
                         trade(TUE + 1 * MS, 150.003, 1e4, "buy"), {"t": TUE + 3600 * SEC, "type": "rollover"}],
                 actions=[place(TUE + 1 * MS, "o1", "buy", "market", 10000)], end_t=TUE + 3601 * SEC,
                 costs=dict(ZERO_COSTS, swap={"long_credit_per_unit_per_day": 0.015, "short_credit_per_unit_per_day": -0.020})),
      _o_swap)


def _o_jpx_fee(inp):
    a = action(inp, "o1")
    px = next(e for e in inp["market"] if e["type"] == "trade" and e["t"] >= a["t"])["px"]
    value = px * a["qty"]
    fee = next(f for lim, f in inp["costs"]["fee_table"] if lim is None or value <= lim)
    return {"fee.o1": float(fee)}


scene("c2-10-jpx-fee", "C2-10", "値", "JPX の手数料を約定代金の段階表で渡すと、その段階の額が掛かる",
      "JPX の手数料(約定代金の段階表)",
      "段階表 ≤5万 55 / ≤10万 99 / ≤20万 115 / ≤50万 275 / それ以上 535(場面の合成の表)。1500 × 100 = 15 万 → 115。",
      base_input(product=JPX_STOCK, rules=JPX_RULES,
                 market=[book(jst(10, 0), [(1499, 5000)], [(1500, 5000)]), trade(jst(10, 0), 1500, 100, "buy"),
                         trade(jst(10, 1), 1500, 1000, "buy")],
                 actions=[place(jst(10, 0, 30), "o1", "buy", "market", 100)], end_t=jst(10, 30),
                 costs={"maker_rate": 0.0, "taker_rate": 0.0,
                        "fee_table": [[50000, 55], [100000, 99], [200000, 115], [500000, 275], [None, 535]],
                        "source": "場面の定義(合成の段階表。証券会社の料率ではない)"}),
      _o_jpx_fee)

_nd = base_input(market=mkt0() + [trade(T0 + 5 * MS, 10001, 1, "buy")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "market", 1)], costs=dict(TAKER_COSTS))
_nd_var = copy.deepcopy(_nd)
del _nd_var["costs"]["maker_rate"]
scene("c2-10-no-default", "C2-10", "能力", "費用を 1 つでも欠いた実行は、既定値で埋めずに断る",
      "既定値を持たない(欠けたら拒否)",
      "対照 = 全部の費用を明示(c2-10-taker と同じ正解)。変形 = maker の率を欠く → 断る(既定値で走ったら不一致)。",
      _nd, _o_taker, variant=_nd_var)

_src_var = copy.deepcopy(_nd)
del _src_var["costs"]["source"]
scene("c2-10-source", "C2-10", "能力", "費用に出所の欄が無い実行は断る",
      "出所の欄が必須",
      "対照 = 出所つき(c2-10-taker と同じ正解)。変形 = 出所の欄を欠く → 断る。",
      copy.deepcopy(_nd), _o_taker, variant=_src_var)

# ======================= C2-11 口座と会計 =======================


def _o_pnl(inp):
    a1, a2 = action(inp, "o1"), action(inp, "o2")
    p1 = book_at(inp, a1["t"])["asks"][0][0]
    p2 = book_at(inp, a2["t"])["bids"][0][0]
    mark = [e for e in inp["market"] if e["type"] == "trade"][-1]["px"]
    pos = a1["qty"] - a2["qty"]
    return {"account.realized": (p2 - p1) * a2["qty"], "account.position": pos, "account.unrealized": (mark - p1) * pos}


scene("c2-11-pnl", "C2-11", "値", "実現の損益と評価の損益を円で出す",
      "実現と評価の損益(値 = 最後の約定、規則 mark = last_trade)",
      "買い 1 @10001、売り 0.4 @10101 → 実現 (10101 − 10001) × 0.4 = 40。残り 0.6、最後の約定 10051 → 評価 (10051 − 10001) × 0.6 = 30。",
      base_input(market=mkt0() + [trade(T0 + 2 * MS, 10001, 1, "buy"), book(T0 + 5 * MS, [(10101, 5)], [(10103, 5)]),
                                  trade(T0 + 11 * MS, 10101, 1, "sell"), trade(T0 + 20 * MS, 10051, 0.1, "sell")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "market", 1), place(T0 + 10 * MS, "o2", "sell", "market", 0.4)]),
      _o_pnl)


def _o_margin(inp):
    acc = inp["account"]
    a1, a2 = action(inp, "o1"), action(inp, "o2")
    ask = book_at(inp, a1["t"])["asks"][0][0]
    cap = acc["cash"] * acc["leverage"]
    assert a1["qty"] * ask > cap >= a2["qty"] * ask
    return {"status.o1": "rejected", "filled.o1": 0.0, "filled.o2": a2["qty"]}


scene("c2-11-margin", "C2-11", "値", "証拠金 × レバレッジを超える建玉の注文は拒否される",
      "証拠金・レバレッジ",
      "証拠金 1000 円、レバレッジ 2 → 建玉の上限 2000 円。o1 = 買い 0.3 × 10001 = 3000.3 > 2000 → 拒否。o2 = 買い 0.1 × 10001 = 1000.1(対照)→ 埋まる。",
      base_input(market=mkt0() + [trade(T0 + 5 * MS, 10001, 1, "buy")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "market", 0.3), place(T0 + 2 * MS, "o2", "buy", "market", 0.1)],
                 account={"currency": "JPY", "cash": 1000.0, "leverage": 2.0}),
      _o_margin)


def _o_liq(inp):
    acc = inp["account"]
    a = action(inp, "o1")
    entry = book_at(inp, a["t"])["asks"][0][0]
    q = a["qty"]
    for e in inp["market"]:
        if e["type"] != "trade" or e["t"] <= a["t"]:
            continue
        equity = acc["cash"] + (e["px"] - entry) * q
        req = e["px"] * q / acc["leverage"]
        if equity / req < acc["maint_ratio"]:
            return {"account.liquidated_t": e["t"], "account.position": 0.0, "account.realized": (e["px"] - entry) * q}
    raise AssertionError("scene must liquidate")


scene("c2-11-liquidation", "C2-11", "値", "証拠金維持率が下限を割った時点の値で強制決済される",
      "強制決済",
      "証拠金 1000、レバレッジ 2、維持率の下限 0.5。買い 0.19 @10001。維持率 = (1000 + (値 − 10001) × 0.19) / (値 × 0.19 / 2)。"
      "9000 → 0.947、7000 → 0.646、6000 → 0.421 < 0.5 → 6000 の時点(T0+3s)で決済、実現 (6000 − 10001) × 0.19、建玉 0。",
      base_input(market=mkt0() + [trade(T0 + 5 * MS, 10001, 0.19, "buy"), trade(T0 + 1 * SEC, 9000, 1, "sell"),
                                  trade(T0 + 2 * SEC, 7000, 1, "sell"), trade(T0 + 3 * SEC, 6000, 1, "sell"),
                                  trade(T0 + 4 * SEC, 6500, 1, "buy")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "market", 0.19)],
                 account={"currency": "JPY", "cash": 1000.0, "leverage": 2.0, "maint_ratio": 0.5,
                          "liquidation_price": "mark", "source": "場面の定義(合成の規則)"}),
      _o_liq)


def _o_exposure(inp):
    t = [action(inp, r)["t"] for r in ("o1", "o2", "o3")]
    return {"account.exposure_ns": (t[1] - t[0]) + (inp["end_t"] - t[2])}


scene("c2-11-exposure", "C2-11", "値", "建玉を持っていた時間(露出の時計)を足し合わせる",
      "建玉の時間(露出の時計)",
      "買い 1(T0+1ms)→ 売り 1(T0+1.001s)で 1 秒、買い 1(T0+2.001s)→ 終わり(T0+5s)で 2.999 秒 → 合計 3.999 秒(遅延 0 なので約定の時刻 = 出した時刻)。",
      base_input(market=mkt0(), actions=[place(T0 + 1 * MS, "o1", "buy", "market", 1),
                                         place(T0 + 1001 * MS, "o2", "sell", "market", 1),
                                         place(T0 + 2001 * MS, "o3", "buy", "market", 1)], end_t=T0 + 5 * SEC),
      _o_exposure)


def _o_legs(inp):
    a1, a2 = action(inp, "o1"), action(inp, "o2")
    c = inp["costs"]
    p2 = book_at(inp, a2["t"])["bids"][0][0]
    return {"fee.o1": rate_fee(c["maker_rate"], a1["px"], a1["qty"]), "fee.o2": rate_fee(c["taker_rate"], p2, a2["qty"])}


scene("c2-11-legs", "C2-11", "値", "脚(入りと出)ごとに費用を分けて出す",
      "脚ごとの費用",
      "入り = 指値 9990 の買い 1(maker 0.0002)→ 1.998。出 = 成行の売り 1 が 9980 で(taker 0.0005)→ 4.99。",
      base_input(market=mkt0() + [trade(T0 + 10 * MS, 9985, 5, "sell"), book(T0 + 20 * MS, [(9980, 5)], [(9982, 5)]),
                                  trade(T0 + 22 * MS, 9980, 1, "sell")],
                 actions=[place(T0 + 1 * MS, "o1", "buy", "limit", 1, px=9990), place(T0 + 21 * MS, "o2", "sell", "market", 1)],
                 costs={"maker_rate": 0.0002, "taker_rate": 0.0005, "source": "場面の定義(合成の値)"}),
      _o_legs)


def _o_split(inp):
    ca = next(e for e in inp["market"] if e["type"] == "corporate")
    a = action(inp, "o1")
    px = next(e for e in inp["market"] if e["type"] == "trade" and e["t"] >= a["t"])["px"]
    return {"account.position": a["qty"] * ca["ratio"], "account.avg_px": px / ca["ratio"]}


for _n, _r, _txt in (("split", 2.0, "1 株を 2 株に分割 → 建玉 200 株、平均取得値 750。"),
                     ("reverse-split", 0.5, "2 株を 1 株に併合 → 建玉 50 株、平均取得値 3000。")):
    scene(f"c2-11-{_n}", "C2-11", "値", "分割・併合の事象を建玉と平均取得値に反映する",
          "分割・併合の建玉への反映",
          "JPX の買い 100 株 @1500。翌日の寄りの前に比率 " + str(_r) + " の事象。" + _txt,
          base_input(product=JPX_STOCK, rules=JPX_RULES,
                     market=[book(jst(10, 0), [(1499, 5000)], [(1500, 5000)]), trade(jst(10, 0), 1500, 100, "buy"),
                             trade(jst(10, 1), 1500, 1000, "buy"),
                             {"t": jst(10, 0) + 22 * 3600 * SEC, "type": "corporate", "action": _n, "ratio": _r}],
                     actions=[place(jst(10, 0, 30), "o1", "buy", "market", 100)], end_t=jst(10, 0) + 23 * 3600 * SEC),
          _o_split)


def _o_jpy(inp):
    a1, a2 = action(inp, "o1"), action(inp, "o2")
    p1 = book_at(inp, a1["t"])["asks"][0][0]
    p2 = book_at(inp, a2["t"])["bids"][0][0]
    rate = [e for e in inp["market"] if e["type"] == "fx_rate" and e["t"] <= a2["t"]][-1]["px"]
    return {"account.realized_jpy": (p2 - p1) * a1["qty"] * rate}


scene("c2-11-jpy", "C2-11", "値", "円以外で値が付く商品の損益を、決済の時点の為替で円に直す",
      "円建て",
      "EURUSD の買い 10000 @1.1000、売り 10000 @1.1010 → 10 ドル。決済の時点の USDJPY 150.0 → 1500 円。",
      base_input(product=EURUSD,
                 market=[book(TUE, [(1.09990, 1e6)], [(1.10000, 1e6)]), {"t": TUE, "type": "fx_rate", "pair": "USDJPY", "px": 150.0},
                         trade(TUE + 2 * MS, 1.1000, 1e4, "buy"), book(TUE + 5 * MS, [(1.10100, 1e6)], [(1.10110, 1e6)]),
                         trade(TUE + 11 * MS, 1.1010, 1e4, "sell")],
                 actions=[place(TUE + 1 * MS, "o1", "buy", "market", 10000), place(TUE + 10 * MS, "o2", "sell", "market", 10000)],
                 end_t=TUE + 60 * SEC),
      _o_jpy)

# ======================= C2-12 JPX データ待ち =======================
_jw_ctrl = tier_input(5)
_jw_var = base_input(product=JPX_STOCK, rules=JPX_RULES,
                     market=[{"t": jst(10, 0), "type": "bar", "o": 1500.0, "h": 1502.0, "l": 1495.0, "c": 1500.0, "v": 10000.0},
                             {"t": jst(10, 1), "type": "bar", "o": 1500.0, "h": 1501.0, "l": 1496.0, "c": 1497.0, "v": 8000.0}],
                     actions=[place(jst(10, 0, 30), "o1", "buy", "limit", 100, px=1496)],
                     fill_model={"tier": 5, "cancel_stance": "none"}, end_t=jst(10, 5))
scene("c2-12-jpx-wait", "C2-12", "能力", "JPX の板・ティックが無いまま列の模型(段 5)を求めると、足で代用せずに断る(データ待ち)",
      "JPX のデータ待ちの扱い",
      "対照 = 暗号資産の板と約定で段 5(c2-5-tier5 と同じ正解)。変形 = JPX の 1 分足だけで段 5 を求める → 断る(足で埋めたら不一致)。",
      _jw_ctrl, tier_path, variant=_jw_var)


# ---------------------------------------------------------------- nouns (coverage)
NOUNS = {
    "C2-1": {"成行": ["c2-1-market"], "指値": ["c2-1-limit"], "post-only": ["c2-1-postonly"], "IOC": ["c2-1-ioc"],
             "FOK": ["c2-1-fok"], "逆指値": ["c2-1-stop"], "reduce-only": ["c2-1-reduceonly"], "OCO": ["c2-1-oco"]},
    "C2-2": {"取消": ["c2-2-cancel", "c2-2-partial"], "訂正": ["c2-2-amend-price", "c2-2-amend-qty"],
             "部分約定": ["c2-2-partial", "c2-1-ioc"], "待ち行列上の位置": ["c2-2-amend-qty"], "残数量": ["c2-2-partial"]},
    "C2-3": {"呼値の拒否": ["c2-3-tick"], "呼値の丸め": ["c2-3-round"], "最小数量の拒否": ["c2-3-minqty"],
             "自己約定防止": ["c2-3-stp"], "FX_BTC_JPY の規則": ["c2-3-tick", "c2-3-minqty"],
             "JPX の取引時間": ["c2-3-jpx-session"], "JPX の値幅制限": ["c2-3-jpx-limit"], "FX の規則": ["c2-3-fx-weekend"]},
    "C2-4": {"拒否": ["c2-4-reject"], "時間切れ": ["c2-4-timeout"], "状態不明を保持し自動で再送しない": ["c2-4-unknown", "c2-4-timeout"],
             "Kill Switch での停止": ["c2-4-kill"]},
    "C2-5": {f"段 {k}": [f"c2-5-tier{k}"] for k in range(7)},
    "C2-6": {"何もしない(95)": ["c2-6-none"], "出した瞬間に割り引く(57)": ["c2-6-discount-at-entry"],
             "取消の時点で繰り上がる(104)": ["c2-6-l3"], "印を付けて列に残す(98)": ["c2-6-l3"],
             "写真の量で先行を下げる(90)": ["c2-6-snapshot-cap"], "確率型の列の模型": ["c2-6-prob"]},
    "C2-7": {"板を辿る成行": ["c2-7-walk", "c2-7-walk-exhaust"], "市場影響の関数": ["c2-7-impact-sqrt", "c2-7-impact-permanent", "c2-5-tier6"]},
    "C2-8": {"楽観側と悲観側の両方で回す": ["c2-8-range", "c2-8-both-required"], "幅で出す": ["c2-8-range"]},
    "C2-9": {"配信の遅れ": ["c2-9-order-feed"], "発注の遅れ": ["c2-9-order-feed", "c2-9-cancel-late"],
             "取消の遅れ": ["c2-9-cancel-late", "c2-9-cancel-early"], "定数": ["c2-9-order-feed"],
             "実測の分布": ["c2-9-empirical"], "種つきの乱数": ["c2-9-empirical"], "受付・拒否の通知の事象": ["c2-9-notice"]},
    "C2-10": {"maker 手数料": ["c2-10-maker"], "taker 手数料": ["c2-10-taker"], "スプレッド": ["c2-10-spread"],
              "資金調達(FX_BTC_JPY)": ["c2-10-funding"], "スワップ(FX)": ["c2-10-swap"], "JPX の手数料": ["c2-10-jpx-fee"],
              "既定値を持たない(欠けたら拒否)": ["c2-10-no-default"], "出所の欄が必須": ["c2-10-source"]},
    "C2-11": {"円建て": ["c2-11-jpy"], "証拠金・レバレッジ": ["c2-11-margin"], "強制決済": ["c2-11-liquidation"],
              "建玉の時間(露出の時計)": ["c2-11-exposure"], "脚ごとの費用": ["c2-11-legs"],
              "実現/評価損益": ["c2-11-pnl"], "分割/併合の建玉反映": ["c2-11-split", "c2-11-reverse-split"]},
    "C2-12": {"データ待ちの明示(足で代用しない)": ["c2-12-jpx-wait"]},
}

# Nouns of the requirement rows that are deliberately NOT a scene, with the reason.
NOT_SCENES = {
    "C2-5": [("段(既定)= そのまま使ったときの段",
              "要件の行(REQUIREMENTS §2 C2-5)は候補の道具の性質として段(既定)を挙げる。新実装に既定の約定の模型を持たせるべきか・持たせないべきかは"
              " §2 の行(委任文 §2 の項目 2「段 0〜6 を全部選べる」)に無く、正解を決めると要件を足すことになる。場面にできない観点として批評家が見る。")],
    "C2-6": [("104 と 98 の区別",
              "取消の時点で繰り上がる(104)と、印を付けて通り過ぎる(98)は、どの約定の列でも自分の埋まる量と時刻が同じ(先行の取消済みの分は"
              "どちらでも約定の数量を消費しない)。観測できる結果に差が出ないので、1 つの場面(c2-6-l3)で両方を測る。")],
    "C2-12": [("完了の判定に混ぜずに別立てで書く",
               "報告の書き方(委任文 §3「完了の条件」)であり、エンジンの振る舞いではない。場面にできない観点として批評家が見る。")],
}


def expected(s: dict) -> dict:
    return s["oracle"](s["input"])


def by_id(sid: str) -> dict:
    return next(s for s in SCENES if s["id"] == sid)

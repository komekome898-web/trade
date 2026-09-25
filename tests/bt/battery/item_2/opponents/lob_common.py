"""Item 2 battery: one scene -> matching-engine mapping shared by the order-book candidates
(98, 99, 101, 102, 103, 104, 96).  The mapping is the same for every engine and every scene
(no scene is special-cased); what an engine lacks is refused with NotExpressible naming it.

The venue is the engine itself.  Scene -> engine (all prices in integer ticks of the product's
tick; all quantities in integer lots of the scene's quantity unit = the largest power of ten that divides
every quantity in the scene, never finer than the product's qty_step -- the smallest integers that carry the
scene exactly, so an engine with narrow integer sizes is not overflowed by a finer unit than the scene needs):
- book snapshot at t: for each price level, the external resting quantity is brought to the
  snapshot's quantity -- an increase is a new external limit order of the difference (it joins the
  back of that level's queue); a level that is gone has all its external orders cancelled; a level
  that shrinks but stays is refused (the engine takes cancels of named orders only, and a snapshot
  does not say which orders left -- that is the cancel-stance question of C2-6).
- l3_add / l3_cancel: an external limit order / its cancel (order-by-order data is what the engine takes).
- trade print (px, qty, aggressor): an external order of the aggressor's side, qty at px, that takes
  what crosses at px or better and leaves nothing resting (the engine's IOC, or its limit order
  followed at once by a cancel of the remainder when the engine has no IOC).
- our actions: market / limit (GTC) / IOC / FOK / post-only / cancel / amend, each only through
  the engine's own call for it; a type the engine has no call for is refused.
- self-trade prevention only through the engine's own policy when it has one.
- same-time order: market events first, then actions, each in list order (i2_common.timeline).
Fills are the engine's trade reports that involve one of our orders (price = the engine's trade
price, time = the scene time of the call that produced it, liq = taker when our order was the
incoming one).  Status at the end: rejected (the engine refused the call), filled (nothing left),
open (the engine still rests it), canceled (anything left and not resting).
"""
from __future__ import annotations

from fractions import Fraction

import i2_common as C
from i2_protocol import NotExpressible


INT_ONLY = [True]  # set per run from Engine.int_units


def ticks(px, tick):
    q = Fraction(str(px)) / Fraction(str(tick))
    if q.denominator != 1:
        if INT_ONLY[0]:
            raise _OffGrid(px)
        return float(q)  # an engine that takes float prices gets the off-grid value and decides itself
    return int(q)


class _OffGrid(Exception):
    pass


def qty_unit(inp):
    """The largest 10**k (k <= 0 allowed, and not finer than qty_step) dividing every quantity of the scene."""
    qs = [a["qty"] for a in inp["actions"] if a.get("qty") is not None]
    for e in inp["market"]:
        if e["type"] == "book":
            qs += [q for _, q in e["bids"]] + [q for _, q in e["asks"]]
        elif "qty" in e:
            qs.append(e["qty"])
    step = Fraction(str(inp["product"]["qty_step"]))
    unit = Fraction(1)
    while unit > step and not all((Fraction(str(q)) / unit).denominator == 1 for q in qs):
        unit /= 10
    return float(max(unit, step))


def lots(q, step) -> int:
    v = Fraction(str(q)) / Fraction(str(step))
    if v.denominator != 1:
        if INT_ONLY[0]:
            raise _OffGrid(q)
        return float(v)
    return int(v)


class Engine:
    """Subclass per tool.  Keys are strings (our refs, or 'x<n>' for external orders)."""
    tool = "?"
    features: frozenset = frozenset()
    int_units = True  # the engine takes integer prices / sizes only

    def start(self, inp) -> None:
        pass

    def limit(self, key, side, px, qty, mine, stp):  # -> list[(maker_key, taker_key, px, qty)]
        raise NotImplementedError

    def market(self, key, side, qty, mine, stp):
        raise NotImplementedError

    def ioc(self, key, side, px, qty, mine, stp):
        raise NotImplementedError

    def fok(self, key, side, px, qty, mine, stp):
        raise NotImplementedError

    def post_only(self, key, side, px, qty, mine, stp):
        raise NotImplementedError

    def cancel(self, key) -> bool:
        raise NotImplementedError

    def amend(self, key, px, new_left, left):
        """px in ticks; new_left = the lots that should be left after the amend (new size minus what has
        filled), or None when the size is not amended; left = the lots left now."""
        raise NotImplementedError

    def resting(self, key):
        """True / False, or None when the engine cannot say."""
        return None

    def schedule(self, jobs, inp):
        """jobs: [(t, participant, fn)] in timeline order; participant in market / order / cancel / seen.
        Default: run at the scene time (no latency).  An engine with its own scheduler overrides this."""
        for t, _who, fn in jobs:
            fn(t)

    def finish(self) -> None:
        pass


def _fill_model_ok(fm, inp, eng):
    if "range" in fm or "impact" in fm:
        return "市場影響の関数・楽観と悲観の両方を回す口が無い(照合の機関は価格と時間の優先の照合だけ)"
    if fm.get("tier") != 5:
        return f"段 {fm.get('tier')} を選ぶ口が無い(照合の機関の埋まり方は注文の列の価格と時間の優先 = 段 5 だけ)"
    st = fm.get("cancel_stance")
    if st == "l3":
        return None
    if st == "discount_at_entry":
        return "先行を出した瞬間に割り引く扱いの口が無い(照合の機関は列の注文をそのまま数える)"
    return None  # none / snapshot_cap / prob: a shrinking level is refused at run time (see module doc)


def run_lob(inp, eng: Engine) -> dict:
    feats = eng.features
    orders = tuple(f for f in ("market", "limit", "IOC", "FOK", "post_only", "cancel", "amend") if f in feats)
    lat = tuple(k for k in ("feed", "order", "cancel", "notice") if f"latency:{k}" in feats)
    C.gate(inp, tool=eng.tool, orders=orders,
           events=("book", "trade") + (("l3_add", "l3_cancel") if "l3" in feats else ()),
           fill_models=lambda fm: _fill_model_ok(fm, inp, eng), latency=lat, costs=(), account=("cash",))
    prod = inp["product"]
    tick, step = prod["tick"], qty_unit(inp)
    stp = (inp.get("rules") or {}).get("self_trade")
    if stp and "stp" not in feats:
        stp = None  # the engine has no self-trade policy: our orders go in as ordinary orders
    INT_ONLY[0] = eng.int_units
    eng.start(inp)
    rem = {}          # key -> remaining lots (all orders)
    ext_at = {"bid": {}, "ask": {}}   # px ticks -> [ext keys] FIFO
    mine_side = {}
    refs = {a["ref"]: a for a in C.places(inp)}
    rec = {"orders": {}, "fills": []}
    canceled = set()
    n = [0]
    now = [0]

    def on_fills(fl, t):
        for maker, taker, px, q in fl:
            for k, liq in ((maker, "maker"), (taker, "taker")):
                if k in rem:
                    rem[k] -= q
                if k in refs:
                    rec["fills"].append({"ref": k, "t": int(t), "px": float(Fraction(str(px)) * Fraction(str(tick))),
                                         "qty": float(Fraction(str(q)) * Fraction(str(step))), "liq": liq})

    def ext_add(side, px, q, t, key=None):
        n[0] += 1
        key = key or f"x{n[0]}"
        rem[key] = q
        fl = eng.limit(key, "buy" if side == "bid" else "sell", px, q, False, None)
        ext_at[side].setdefault(px, []).append(key)
        on_fills(fl, t)

    def ext_level(side, px):
        return sum(max(rem[k], 0) for k in ext_at[side].get(px, []) if rem.get(k, 0) > 0)

    def on_book(e, t):
        for side, key in (("bid", "bids"), ("ask", "asks")):
            new = {ticks(p, tick): lots(q, step) for p, q in e[key]}
            for px in sorted(set(ext_at[side]) | set(new)):
                have = ext_level(side, px)
                want = new.get(px, 0)
                if want > have:
                    ext_add(side, px, want - have, t)
                elif want == 0 and have > 0:
                    for k in ext_at[side].get(px, []):
                        if rem.get(k, 0) > 0:
                            eng.cancel(k)
                            rem[k] = 0
                elif 0 < want < have:
                    raise NotExpressible(f"{eng.tool}: 板の写真で値位 {px * tick} の量が {have * step} から {want * step} に減った。"
                                         "どの注文が抜けたかを写真は言わず、照合の機関は名指しの取消しか受けない")

    def on_trade(e, t):
        n[0] += 1
        key = f"x{n[0]}"
        side = e["aggressor"]
        px, q = ticks(e["px"], tick), lots(e["qty"], step)
        rem[key] = q
        if "IOC" in feats:
            on_fills(eng.ioc(key, side, px, q, False, None), t)
        else:
            on_fills(eng.limit(key, side, px, q, False, None), t)
            if rem[key] > 0:
                eng.cancel(key)
        rem[key] = 0

    def on_l3(e, t):
        if e["type"] == "l3_add":
            ext_add(e["side"], ticks(e["px"], tick), lots(e["qty"], step), t, key="l3:" + e["id"])
        else:
            k = "l3:" + e["id"]
            if rem.get(k, 0) > 0:
                eng.cancel(k)
                rem[k] = 0

    def on_place(a, t):
        ref, side = a["ref"], a["side"]
        mine_side[ref] = side
        try:
            q = lots(a["qty"], step)
            px = None if a["px"] is None else ticks(a["px"], tick)
        except _OffGrid as exc:
            raise NotExpressible(f"{eng.tool}: 値 {exc} が呼値 {tick}・数量の刻み {step} の整数倍でなく、整数の刻みで渡せない")
        rem[ref] = q
        try:
            if a["type"] == "market":
                fl = eng.market(ref, side, q, True, stp)
            elif a["post_only"]:
                fl = eng.post_only(ref, side, px, q, True, stp)
            elif a["tif"] == "IOC":
                fl = eng.ioc(ref, side, px, q, True, stp)
            elif a["tif"] == "FOK":
                fl = eng.fok(ref, side, px, q, True, stp)
            else:
                fl = eng.limit(ref, side, px, q, True, stp)
        except NotExpressible:
            raise
        except Exception as exc:  # the engine refused this order
            rec["orders"][ref] = {"status": "rejected", "error": f"{type(exc).__name__}: {exc}"[:200]}
            rem[ref] = 0
            return
        on_fills(fl, t)
        if a["type"] == "market" or a["tif"] in ("IOC", "FOK") or a["post_only"]:
            if rem[ref] > 0 and eng.resting(ref) is not True:
                canceled.add(ref)

    def on_cancel(a, t):
        if a["ref"] in rem and rem[a["ref"]] > 0:
            if eng.cancel(a["ref"]):
                canceled.add(a["ref"])

    def on_amend(a, t):
        ref = a["ref"]
        o = refs[ref]
        px = ticks(a["px"] if a["px"] is not None else o["px"], tick)
        q = lots(a["qty"], step) if a["qty"] is not None else None
        new_left = None if q is None else max(q - (lots(o["qty"], step) - rem[ref]), 0)
        fl = eng.amend(ref, px, new_left, rem[ref])
        if new_left is not None:
            rem[ref] = new_left
        on_fills(fl, t)

    jobs = []
    for t, kind, x in C.timeline(inp):
        if kind == "m":
            if x["type"] == "book":
                jobs.append((t, "market", lambda tt, x=x: on_book(x, tt)))
            elif x["type"] == "trade":
                jobs.append((t, "market", lambda tt, x=x: on_trade(x, tt)))
            elif x["type"] in ("l3_add", "l3_cancel"):
                jobs.append((t, "market", lambda tt, x=x: on_l3(x, tt)))
            if x.get("label"):
                jobs.append((t, "seen", lambda tt, x=x: rec.setdefault("seen", {}).__setitem__(x["label"], int(tt))))
        else:
            fn = {"place": on_place, "cancel": on_cancel, "amend": on_amend}[x["op"]]
            who = "cancel" if x["op"] == "cancel" else "order"
            jobs.append((t, who, lambda tt, x=x, fn=fn: fn(x, tt)))
    try:
        eng.schedule(jobs, inp)
    except _OffGrid as exc:
        raise NotExpressible(f"{eng.tool}: 値 {exc} が呼値・数量の刻みの整数倍でない")
    for ref in refs:
        if ref in rec["orders"]:
            continue
        left = rem.get(ref, 0)
        if left <= 0:
            st = "filled"
        elif ref in canceled:
            st = "canceled"
        else:
            r = eng.resting(ref)
            st = "open" if r in (True, None) else "canceled"
        rec["orders"][ref] = {"status": st}
    eng.finish()
    return rec


class PipeEngine(Engine):
    """An engine behind a compiled line-command driver (stdin/stdout, one command per line):
    "L id b|s price qty" -> "N k" + k lines "F buy_id sell_id price qty"; "M id b|s qty" likewise;
    "C id" -> "C 0|1".  Subclasses give `exe` and `features`."""
    exe = ""

    def start(self, inp):
        import subprocess
        self.p = subprocess.Popen([self.exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self.id2key, self.key2id, self.n = {}, {}, 0

    def _cmd(self, line):
        self.p.stdin.write(line + "\n")
        self.p.stdin.flush()
        return self.p.stdout.readline().split()

    def _fills(self, head, key, side):
        out = []
        for _ in range(int(head[1])):
            _, b, s, px, q = self.p.stdout.readline().split()
            maker = int(s) if side == "buy" else int(b)
            out.append((self.id2key.get(maker, f"?{maker}"), key, float(px), int(q)))
        return out

    def _new(self, key):
        self.n += 1
        self.id2key[self.n], self.key2id[key] = key, self.n
        return self.n

    def limit(self, key, side, px, qty, mine, stp):
        oid = self._new(key)
        return self._fills(self._cmd(f"L {oid} {side[0]} {int(px)} {int(qty)}"), key, side)

    def market(self, key, side, qty, mine, stp):
        oid = self._new(key)
        return self._fills(self._cmd(f"M {oid} {side[0]} {int(qty)}"), key, side)

    def cancel(self, key):
        return key in self.key2id and self._cmd(f"C {self.key2id[key]}")[1] == "1"

    def finish(self):
        self.p.stdin.close()
        self.p.wait(timeout=30)

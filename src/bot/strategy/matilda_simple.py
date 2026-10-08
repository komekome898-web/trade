"""マチルダ(v37)を単純な測りの道(`bot.bt.simple.run` の `decide(bar, fills)`)へ移した戦略。

対応は docs/DISCUSSIONS/2026-10-08_simple_road/S3_MAPPING.md §1。リードが書いた(L-839「**移し替えを使っていいけど**」)。
純な関数(引数の検め・建ての旗・決済の旗・利確の値段)と量の計算は古い道のものを import して使う。
"""
from __future__ import annotations

from collections import deque
from datetime import datetime
from fractions import Fraction
from decimal import Decimal

from bot.strategy.matilda_v37 import (END_BREAK, END_ENTRY, SIG_BREAK, SIG_ENTRY, check_params, entry_flag, exit_flag,
                                      exit_price)
from bot.bt.road.sizing import MARGIN_JPY, USE_RATIO, size_detail

NS = 10**9
MINUTE_NS = 60 * NS
END_REVERSE = "逆向きのブレイク"


class MatildaError(Exception):
    pass


def _ns(ts: str) -> int:
    d = datetime.fromisoformat(ts)
    return int(d.timestamp()) * NS


class MatildaSimple:
    def __init__(self, params: dict) -> None:
        p = check_params(params)
        self.p = p
        self.levels = p["levels"]
        self._foot_ns = p["foot"] * MINUTE_NS
        self._warm = max(p["vola_count"], p["range_count"] * p["break_len_mult"])
        keep = self._warm
        self._win = None
        self._wins = deque(maxlen=keep)
        self._closed = 0
        self.ind = None
        self._exp = 0
        self._bsig = 0
        self._up = deque(maxlen=max(1, p["break_delay"]))
        self._dn = deque(maxlen=max(1, p["break_delay"]))
        self._brk = 0
        self._brk_sig = None
        self._n_brk = 0
        self._eflg = 0
        self._e_sig = None
        self._n_e = 0
        self._m_pos = Fraction(0)
        self._cost = Fraction(0)
        self._prev_dir = 0
        self._filled_since = False
        self._poschange = None
        self._book: dict = {}  # 出ている注文 番号 -> 道の注文の辞書
        self._mine: dict = {}  # 番号 -> {kind, parent, s, px}
        self._filled: dict = {}  # 約定した番号 -> 値段(根の約定値段に使う)
        self._cnt = {1: 0, -1: 0}
        self._last_px = {1: None, -1: None}
        self._first_px = {1: None, -1: None}
        self._first = None
        self._first_qty = None
        self._close_at: dict = {}
        self._flat = False
        self._n = 0
        self._events: list = []

    # ---- 口 ----
    def decide(self, bar, fills):
        self._events = []
        for f in fills:
            self._on_fill(f)
        start = _ns(bar[0])
        end = start + MINUTE_NS
        self._close_gap(start)
        if self._closed >= self._warm:
            self._judge(float(bar[4]), end)
        self._add_bar(bar, start, end)
        self._forget()
        return dict(self._book), list(self._events)

    def _forget(self):
        """出ていない注文を内部の表から消す(記憶を注文の本数に比例させない)。出ている段の根と、出ている利確の親は残す。"""
        keep = set(self._book)
        for c in self._book:
            m = self._mine[c]
            if m.get("root"):
                keep.add(m["root"])
            if m.get("parent"):
                keep.add(m["parent"])
        for d in (self._mine, self._filled, self._close_at):
            for k in [k for k in d if k not in keep]:
                del d[k]

    def _id(self, pre):
        self._n += 1
        return f"{pre}{self._n}"

    def _on_fill(self, f):
        q = Fraction(Decimal(repr(float(f["qty"]))))
        px = Fraction(Decimal(repr(float(f["px"]))))
        s = 1 if f["side"] == "buy" else -1
        self._filled[f["id"]] = float(f["px"])
        self._book.pop(f["id"], None)
        self._filled_since = True
        pos = self._m_pos
        if pos == 0 or (pos > 0) == (s > 0):
            self._m_pos, self._cost = pos + s * q, self._cost + px * q
        else:
            c = min(q, abs(pos))
            cost = self._cost - (self._cost * c / abs(pos) if c < abs(pos) else self._cost)
            rest = q - c
            self._m_pos = pos + s * q
            self._cost = cost + px * rest if rest > 0 else cost
        if self._flat and self._m_pos == 0 and not self._book:
            self._flat = False

    def _avg(self):
        return round(self._cost / abs(self._m_pos))

    def _held(self):
        if not self._first_qty:
            raise MatildaError("建玉があるのに取引の最初の段が無い")
        return round(abs(self._m_pos) / self._first_qty)

    def _minutes(self, now):
        return (now - self._poschange) / MINUTE_NS

    # ---- 足の束ね・指標(もとのまま) ----
    def _close_window(self):
        w, self._win = self._win, None
        self._update(w)

    def _add_bar(self, bar, start, end):
        idx = start // self._foot_ns
        o, h, lo, c, v = (float(x) for x in bar[1:6])
        if self._win is None:
            self._win = {"idx": idx, "end": (idx + 1) * self._foot_ns, "o": o, "h": h, "l": lo, "c": c, "v": v}
        else:
            w = self._win
            w["h"], w["l"] = max(w["h"], h), min(w["l"], lo)
            w["c"], w["v"] = c, w["v"] + v
        if end > self._win["end"]:
            raise MatildaError("足が窓の終わりを越える")
        if end == self._win["end"]:
            self._close_window()

    def _close_gap(self, start):
        if self._win is not None and start // self._foot_ns != self._win["idx"]:
            if start // self._foot_ns < self._win["idx"]:
                raise MatildaError("足の時刻が戻った")
            self._close_window()

    def _update(self, w):
        p = self.p
        o, h, lo, c, v = w["o"], w["h"], w["l"], w["c"], w["v"]
        body = c - o
        sign = 1 if body > 0 else (-1 if body < 0 else 0)
        if sign == 1:
            top, under = h - c, o - lo
        else:
            top, under = h - o, c - lo
        hc, lc = h, lo
        bi = p["beard_ignore"]
        if bi is not None:
            if top > bi:
                hc = c if sign == 1 else o
            if under > bi:
                lc = c if sign == -1 else o
        prev = self.ind
        if prev is not None:
            if hc > prev["range_max"]:
                self._exp += 1
            elif lc < prev["range_min"]:
                self._exp -= 1
            elif (self._exp >= 1 and lc < prev["center"]) or (self._exp <= -1 and hc > prev["center"]):
                self._exp = 0
        self._wins.append({"h": hc, "l": lc, "body": abs(body), "v": v})
        self._closed += 1
        wins = list(self._wins)
        vc, rc, mult = p["vola_count"], p["range_count"], p["break_len_mult"]
        # ボラ・出来高の平均 = 今の足を含む直近 vola_count 本の和 ÷ vola_count(L-849「(ろ)」。L-784 の「割る数は分子を合わせて」=
        # 原典の和の本数 vola_count − 1 を割る数 vola_count に合わせる)
        recent = wins[-vc:]
        vola = sum(x["body"] for x in recent) / vc
        vol_ave = sum(x["v"] for x in recent) / vc
        r1, r2 = wins[-rc:], wins[-rc * mult:]
        rmax, rmin = max(x["h"] for x in r1), min(x["l"] for x in r1)
        rmax2, rmin2 = max(x["h"] for x in r2), min(x["l"] for x in r2)
        width = rmax - rmin
        center = round((rmax + rmin) / 2)
        if rmax != rmax2 or self._brk != 0:
            self._up.append(rmax + width * p["break_dist"])
        if rmin != rmin2 or self._brk != 0:
            self._dn.append(rmin - width * p["break_dist"])
        if p["b_signal"]:
            bf, bs = self._brk, self._bsig
            if v > vol_ave and bf != 0:
                if top > under and top > abs(body):
                    if bf == 1 and bs >= 0:
                        bs -= 1
                    elif bf == -1:
                        bs = -1
                elif under > top and under > abs(body):
                    if bf == -1 and bs <= 0:
                        bs += 1
                    elif bf == 1:
                        bs = 1
                elif sign == -1:
                    if bf == 1 and bs >= 0:
                        bs -= 1
                    elif bf == -1:
                        bs = -1
                elif sign == 1:
                    if bf == -1 and bs <= 0:
                        bs += 1
                    elif bf == 1:
                        bs = 1
            elif bs != 0 and self._exp == 0:
                bs = 0
            self._bsig = bs
        else:
            self._bsig = 0
        self.ind = {"vola": vola, "range_max": rmax, "range_min": rmin, "range_max2": rmax2, "range_min2": rmin2,
                    "width": width, "center": center}

    # ---- 合図 ----
    def _sig_start(self, sid, kind, direction, value):
        self._events.append({"op": "start", "id": sid, "kind": kind, "direction": direction, "value": value})
        return sid

    def _sig_end(self, sid, reason):
        self._events.append({"op": "end", "id": sid, "reason": reason})

    # ---- 判定 ----
    def _judge(self, last, now):
        p, ind = self.p, self.ind
        d = (self._m_pos > 0) - (self._m_pos < 0)
        canceled = False
        if d != self._prev_dir or (self._filled_since and d == 0):
            if d == 0:
                self._cancel_all()
                canceled = True
            self._poschange = now
        self._prev_dir, self._filled_since = d, False
        if p["break_delay"] != 0:
            k = p["break_delay"]
            new = self._brk
            done = False
            if len(self._up) >= k:
                bup = max(self._up[-k], ind["range_max2"])
                if bup < last and self._brk != 1 and self._bsig != -1:
                    new, done = 1, True
            if not done and len(self._dn) >= k:
                bdp = min(self._dn[-k], ind["range_min2"])
                if bdp > last and self._brk != -1 and self._bsig != 1:
                    new = -1
            if new != self._brk:
                if self._brk != 0 and self._brk_sig is not None:
                    self._sig_end(self._brk_sig, END_REVERSE)
                    self._brk_sig = None
                self._brk = new
                self._n_brk += 1
                self._brk_sig = self._sig_start(f"b{self._n_brk}", SIG_BREAK, "up" if new == 1 else "down",
                                                {"close": last, "center": ind["center"]})
        flat = self._m_pos == 0
        center, vola = ind["center"], ind["vola"]
        ef = entry_flag(self._brk, self._bsig, flat, last, center, vola, ind["width"], p["entry_setting"],
                        p["range_setting"], p["over_range_setting"], p["vola_setting"])
        if ef != self._eflg:
            if self._e_sig is not None:
                self._sig_end(self._e_sig, END_ENTRY)
                self._e_sig = None
            if ef != 0:
                self._n_e += 1
                es, xs = vola * p["entry_setting"], vola * p["exit_setting"]
                value = {"close": last, "center": center, "vola": vola, "range_max": ind["range_max"],
                         "range_min": ind["range_min"], "width": ind["width"], "lsp": center - es, "ssp": center + es,
                         "lep": center - xs, "sep": center + xs, "break_flg": self._brk, "b_signal": self._bsig,
                         "expantion_flg": self._exp, "levels": self.levels}
                self._e_sig = self._sig_start(f"e{self._n_e}", SIG_ENTRY, "long" if ef == 1 else "short", value)
        self._eflg = ef
        snap = {"last": last, "now": now, "center": center, "vola": vola, "brk": self._brk, "bsig": self._bsig,
                "ef": ef, "xf": 0}
        if not flat:
            snap["xf"] = exit_flag(snap["brk"], snap["bsig"], ef, d, self._minutes(now), p["alert_count"],
                                   self._avg(), center, self._held(), self.levels)
        self._actions(snap)
        self._uncross()
        if (self._brk == 1 and last < center) or (self._brk == -1 and last > center):
            self._brk, self._bsig = 0, 0
            if self._brk_sig is not None:
                self._sig_end(self._brk_sig, END_BREAK)
                self._brk_sig = None

    def _cancel_all(self):
        for c in list(self._book):
            self._cancel(c)
        self._cnt = {1: 0, -1: 0}
        self._last_px = {1: None, -1: None}
        self._first_px = {1: None, -1: None}
        if self._m_pos == 0:
            self._first, self._first_qty = None, None

    def _cancel(self, c):
        self._book.pop(c, None)

    def _actions(self, snap):
        if self._flat:
            return
        xf, ef = snap["xf"], snap["ef"]
        if xf == 3:
            self._cancel_all()
            if self._m_pos != 0:
                m = self._id("m")
                self._book[m] = {"form": "market", "side": "sell" if self._m_pos > 0 else "buy",
                                 "qty": float(abs(self._m_pos))}
                self._mine[m] = {"kind": "market", "parent": None}
                self._flat = True
            return
        flat = self._m_pos == 0
        if ef in (1, -1):
            if self._cnt[-ef] != 0 and flat:
                self._cancel_all()
            self._ladder(snap, ef)
        elif self._cnt[1] != 0 or self._cnt[-1] != 0:
            self._cancel_all()
        if self._m_pos != 0 and xf in (1, 2):
            self._exit(snap, xf)

    def _qty(self, px):
        if self._first is None:
            _, q = size_detail(margin_jpy=MARGIN_JPY, use_ratio=USE_RATIO, levels=self.levels, price=px,
                               quote_ccy="JPY")
            return q
        return float(self._first_qty)

    def _ladder(self, snap, s):
        p = self.p
        step = snap["vola"] * p["step_setting"]
        center = snap["center"]
        p1 = (center - s * snap["vola"] * p["entry_setting"]) if snap["brk"] == 0 else snap["last"]
        flat = self._m_pos == 0
        if flat and self._cnt[s] != 0 and self._first_px[s] is not None and s * (p1 - self._first_px[s]) > 0:
            self._cancel_all()
            flat = self._m_pos == 0
        held0, avg0 = 0, None
        if not flat:
            d = (self._m_pos > 0) - (self._m_pos < 0)
            if d != s:
                return
            if self._cnt[s] == 0:
                avg0 = self._avg()
                held0 = self._held()
                self._last_px[s] = avg0
                self._cnt[s] = held0
            else:
                held0, avg0 = self._held(), self._avg()
        minutes = 0.0 if flat else self._minutes(snap["now"])
        placed: list = []
        root = root_px = None
        side = "buy" if s == 1 else "sell"
        xside = "sell" if s == 1 else "buy"
        while self._cnt[s] < self.levels:
            if self._cnt[s] == 0 and flat:
                px = p1
            else:
                px = self._last_px[s] - s * step
            placed.append(px)
            k = len(placed)
            held = held0 + k
            avg_k = round((Fraction(held0) * (avg0 or 0) + sum(Fraction(x) for x in placed)) / held)
            xf = exit_flag(snap["brk"], snap["bsig"], snap["ef"], s, minutes, p["alert_count"], avg_k, center, held,
                           self.levels)
            qty = self._qty(px)
            if root is None:
                e = self._id("r")
                order = {"form": "limit", "side": side, "qty": qty, "px": px}
                root, root_px = e, px
            else:
                e = self._id("l")
                order = {"form": "level", "side": side, "qty": qty, "root": root, "offset": px - root_px}
            if qty > 0:
                self._book[e] = order
                self._mine[e] = {"kind": "entry", "parent": None, "root": None if e == root else root, "px": px, "s": s}
                if xf in (1, 2):
                    xpx = exit_price(xf, snap["brk"], s, center, snap["vola"], avg_k, held, p["exit_setting"],
                                     p["step_exit"])
                    x = self._id("x")
                    self._book[x] = {"form": "exit", "side": xside, "qty": qty, "parent": e, "px": xpx}
                    self._mine[x] = {"kind": "with_entry", "parent": e}
            if self._first is None:
                self._first = e
                self._first_qty = Fraction(Decimal(repr(qty)))
            if self._cnt[s] == 0:
                self._first_px[s] = px
            self._last_px[s] = px
            self._cnt[s] += 1

    def _live_exits(self):
        return [c for c in self._book if self._mine[c]["kind"] == "close"
                or (self._mine[c]["kind"] == "with_entry" and self._mine[c]["parent"] in self._filled)]

    def _exit(self, snap, xf):
        p = self.p
        d = (self._m_pos > 0) - (self._m_pos < 0)
        avg, held = self._avg(), self._held()
        price = exit_price(xf, snap["brk"], d, snap["center"], snap["vola"], avg, held, p["exit_setting"],
                           p["step_exit"])
        live = self._live_exits()
        if len(live) == 1 and self._mine[live[0]]["kind"] == "close":
            c = live[0]
            row = self._book[c]
            same = Fraction(Decimal(repr(row["qty"]))) == abs(self._m_pos) and self._close_at.get(c) == (self._m_pos, avg)
            if same:
                cur = row["px"]
                closer = price < cur if row["side"] == "sell" else price > cur
                if not closer:
                    return
        for c in live:
            self._cancel(c)
        c = self._id("c")
        self._book[c] = {"form": "limit", "side": "sell" if self._m_pos > 0 else "buy", "qty": float(abs(self._m_pos)),
                         "px": price, "close": True}
        self._mine[c] = {"kind": "close", "parent": None}
        self._close_at[c] = (self._m_pos, avg)

    # ---- 交差(L-816 3.a) ----
    def _entry_px(self, c):
        m = self._mine[c]
        if m["root"] is None:
            return m["px"]
        r = m["root"]
        rm = self._mine[r]
        off = m["px"] - rm["px"]
        return (self._filled[r] if r in self._filled else rm["px"]) + off

    def _uncross(self):
        """自分の注文の交差(L-816 3.a): 玉を決済する注文と交差する同じ向きの段だけを返さない。根が交差したら、
        残った約定していない段のうち最初の段を新しい根(limit)にして、残りの段と利確を新しい番号で出し直す。"""
        if self._m_pos == 0:
            return
        s = 1 if self._m_pos > 0 else -1
        ex = [self._book[c]["px"] for c in self._live_exits()]
        if not ex:
            return
        lim = min(ex) if s == 1 else max(ex)

        def crosses(px):
            return px >= lim if s == 1 else px <= lim
        roots = [c for c in self._book if self._mine[c]["kind"] == "entry" and self._mine[c]["root"] is None
                 and self._mine[c]["s"] == s]
        for r in roots:
            kids = [c for c in self._book if self._mine[c]["kind"] == "entry" and self._mine[c]["root"] == r]
            for c in kids:  # 根が約定していれば段の値段は決まっている。根が出ていれば見積もり
                if crosses(self._entry_px(c)):
                    self._drop(c)
            if r in self._book and crosses(self._mine[r]["px"]):
                rest = [c for c in self._book if self._mine[c]["kind"] == "entry" and self._mine[c]["root"] == r]
                rest.sort(key=lambda c: -s * self._entry_px(c))
                plan = [(self._entry_px(c), self._exit_of(c)) for c in rest]
                self._drop(r)
                for c in rest:
                    self._drop(c)
                newroot = newpx = None
                for px, xo in plan:
                    qty = float(self._first_qty)
                    if newroot is None:
                        e = self._id("r")
                        self._book[e] = {"form": "limit", "side": "buy" if s == 1 else "sell", "qty": qty, "px": px}
                        self._mine[e] = {"kind": "entry", "parent": None, "root": None, "px": px, "s": s}
                        newroot, newpx = e, px
                    else:
                        e = self._id("l")
                        self._book[e] = {"form": "level", "side": "buy" if s == 1 else "sell", "qty": qty,
                                         "root": newroot, "offset": px - newpx}
                        self._mine[e] = {"kind": "entry", "parent": None, "root": newroot, "px": px, "s": s}
                    if xo is not None:
                        x = self._id("x")
                        self._book[x] = dict(xo, parent=e)
                        self._mine[x] = {"kind": "with_entry", "parent": e}

    def _exit_of(self, c):
        for x in self._book:
            if self._mine[x]["kind"] == "with_entry" and self._mine[x]["parent"] == c:
                return dict(self._book[x])
        return None

    def _drop(self, c):
        self._book.pop(c, None)
        for x in [x for x in self._book if self._mine[x]["kind"] == "with_entry" and self._mine[x]["parent"] == c]:
            self._book.pop(x, None)

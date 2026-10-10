"""マチルダを、単純な測りの道 2 版目の口(`decide(ev)` → `(orders, events, watches)`)で書いた戦略。

決まりの正本: docs/DISCUSSIONS/2026-10-08_simple_road/SPEC.md §2.2〜§4(口・注文の形・残すファイル)と、
委任文 docs/DISCUSSIONS/2026-10-08_simple_road/DELEGATION_s4_matilda.md の決まりの表 R1〜R15(10-08 にオーナーと決めたもの)。
物差しは擦り合わせの決めで、原典ではない(L-869)。

流れ:
- `"close"`(足が閉じた): (1) その足の間に使っていた線(前の足が閉じた時点の値 = self._snap)と終値で、ブレイクの入り・抜け
  (R13)・反対側の線(R10 イ)・合図の消失(R5)を判断し直す → (2) 足を窓に足し、窓が閉じたら指標と線を計算し直す(R1・R11)
  → (3) 新しい線で次の足の注文を出し直す(R3・R6・R8・R9・R10 ロ)。
- `"stop"`(足の途中で止まった): 約定を受け(R4・R8・R12)、届いた見張る値段を見る(R5・R10 イ・R12・R13)。
- 返す注文は、出ている注文の全部(返さなかった注文は道が取り消す)。中身を変えるときは新しい番号で出す(SPEC.md §2.2)。
- 線・中心・利確の値段は計算した値のまま返す(刻みの切り捨ては道がする)。
"""
from __future__ import annotations

import math
from collections import deque
from datetime import datetime
from decimal import Decimal
from fractions import Fraction

from bot.bt.road.sizing import MARGIN_JPY, USE_RATIO, size_detail
from bot.strategy.matilda_v37 import END_BREAK, END_ENTRY, SIG_BREAK, SIG_ENTRY, V37_ORIGINAL

NS = 10**9
MINUTE_NS = 60 * NS
END_FLAT = "玉が 0 に戻った"  # R15 の「玉が 0 に戻った時点」で建ての合図を終える理由

# 引数は 16 個(直すもの 2)。原典の値の組から 2 つを外した残り 15 個と、改良案 I1 の門 dev_setting(原典に無い。既定 None = 門なし)。
# dev_setting(L-965・L-970): 足が閉じた時点の建ての線の中心からの距離(entry_setting × ボラ)÷ 幅 がこの値より小さいときは、
# 1 段目(R3 の建て)を出さない。段の足しは止めない。出所 `docs/DISCUSSIONS/2026-10-08_matilda_main/EARN_LOSS_L965.md` §1.2・§2。
ORIGINAL_KEYS = ("levels", "foot", "vola_count", "range_count", "alert_count", "range_setting", "over_range_setting",
                 "vola_setting", "entry_setting", "exit_setting", "break_delay", "break_dist", "break_len_mult",
                 "beard_ignore", "step_setting")
PARAM_KEYS = ORIGINAL_KEYS + ("dev_setting",)
BASE_PARAMS = {**{k: V37_ORIGINAL[k] for k in ORIGINAL_KEYS}, "dev_setting": None}
TAGS = ("entry", "level", "close", "market", "break")  # 直すもの 4
TIER_ROLES = ("add", "level")  # まだ約定していない段(R5 で取り消す)


class MatildaError(Exception):
    pass


# ---------------------------------------------------------------- 引数の検め(直すもの 2)
def _is_num(v) -> bool:
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(float(v))


def _int(p, k, lo):
    if type(p[k]) is not int or p[k] < lo:
        raise ValueError(f"引数 {k} は {lo} 以上の整数: {p[k]!r}")


def _num(p, k, *, gt=None, ge=None, none=False):
    v = p[k]
    if v is None and none:
        return
    if not _is_num(v) or (gt is not None and not v > gt) or (ge is not None and not v >= ge):
        raise ValueError(f"引数 {k} の値が範囲の外: {v!r}")


def _params(params) -> dict:
    """鍵がちょうど PARAM_KEYS の 16 個で、型と範囲が合うときだけ写しを返す。外れたら ValueError。"""
    if not isinstance(params, dict):
        raise ValueError(f"引数は辞書で渡す(受け取ったのは {type(params).__name__})")
    p = dict(params)
    missing = [k for k in PARAM_KEYS if k not in p]
    unknown = sorted(str(k) for k in p if k not in PARAM_KEYS)
    if missing or unknown:
        raise ValueError(f"引数の鍵がちょうど {len(PARAM_KEYS)} 個でない: 足りない鍵 {missing}・知らない鍵 {unknown}")
    _int(p, "levels", 1)
    _int(p, "foot", 1)
    _int(p, "vola_count", 2)
    _int(p, "range_count", 1)
    _num(p, "alert_count", gt=0)
    for k in ("range_setting", "over_range_setting", "vola_setting"):
        _num(p, k, ge=0, none=True)
    _num(p, "entry_setting", gt=0)
    _num(p, "exit_setting", ge=0)
    _int(p, "break_delay", 0)
    _num(p, "break_dist", gt=0)
    _int(p, "break_len_mult", 2)
    _num(p, "beard_ignore", gt=0, none=True)
    _num(p, "step_setting", gt=0)
    _num(p, "dev_setting", ge=0, none=True)
    return p


def _ns(ts: str) -> int:
    d = datetime.fromisoformat(ts)
    if d.tzinfo is None:
        raise MatildaError(f"時刻に時差が無い: {ts!r}")
    return int(d.timestamp()) * NS


def _frac(x) -> Fraction:
    return Fraction(Decimal(repr(float(x))))


class MatildaSimple:
    def __init__(self, params: dict) -> None:
        p = _params(params)
        self.p = p
        self.levels = p["levels"]
        self._foot_ns = p["foot"] * MINUTE_NS
        self._warm = max(p["vola_count"], p["range_count"] * p["break_len_mult"])
        self._win = None  # 閉じていない窓(foot 分)
        self._wins = deque(maxlen=self._warm)
        self._closed = 0
        self.ind = None
        self._up = deque(maxlen=max(1, p["break_delay"]))
        self._dn = deque(maxlen=max(1, p["break_delay"]))
        self._snap = None  # 今の足の間に使う線(前の足が閉じた時点の値。R1)
        self._last = None  # 前に見た値段(前の呼び出しの price。足の頭では前の足の終値)
        self._n = 0
        self._book: dict = {}  # 出ている注文 番号 -> {form, side, qty, px, tag}
        self._role: dict = {}  # 番号 -> 役(entry / add / level / close / market / break)
        self._events: list = []
        # ブレイク(R11〜R13)
        self._brk = 0
        self._brk_sig = None
        self._n_brk = 0
        # 取引(建玉 0 → 0)
        self._pos = Fraction(0)  # 符号つきの量
        self._cost = Fraction(0)  # 建玉の 値段 × 量 の和(建値 = cost ÷ |pos|、丸めない。R8)
        self._dir = 0
        self._unit = None  # 1 段の量(R7)
        self._t0 = None  # 時間の数え始め = 最初の約定があった足の終わり(R9・R10)
        self._loosen = False  # R9。足が閉じた時点で決める
        self._e_sig = None
        self._n_e = 0

    # ================================================================ 口(SPEC.md §2.2)
    def decide(self, ev):
        self._events = []
        kind = ev["kind"]
        price = float(ev["price"])
        start = _ns(ev["ts"])
        if self._last is None:
            self._last = price
        if kind == "stop":
            self._on_stop(ev, price, start)
        elif kind == "close":
            if ev.get("fills"):
                raise MatildaError("close の ev に約定がある")
            self._on_close(ev["bar"], start)
        else:
            raise MatildaError(f"知らない ev の kind: {kind!r}")
        self._last = price
        orders = {i: dict(o) for i, o in self._book.items()}
        return orders, list(self._events), self._watches()

    def _watches(self):
        """見張る値段。慣らしの間は出さない(R1)。"""
        sn = self._snap
        if sn is None:
            return []
        if self._brk != 0:
            return [sn["center"]]  # R13: 中心に届いたら抜ける
        w = [x for x in (sn["bu"], sn["bd"]) if x is not None]  # R12: 玉が無ければ見張る値段で知る
        if self._dir != 0:
            w.append(sn["up"] if self._dir == 1 else sn["lo"])  # R10 イ: 玉と反対側の建ての線
            w.append(sn["lo"] if self._dir == 1 else sn["up"])  # R5: その取引で使っている建ての線
        out = []
        for x in w:
            if x not in out:
                out.append(float(x))
        return out

    # ================================================================ 注文の帳面
    def _put(self, role, form, side, qty, px=None):
        self._n += 1
        oid = str(self._n)
        o = {"form": form, "side": side, "qty": float(qty)}
        if px is not None:
            o["px"] = float(px)
        o["tag"] = {"entry": "entry", "add": "level", "level": "level"}.get(role, role)
        if o["tag"] not in TAGS:
            raise MatildaError(f"知らない tag: {o['tag']!r}")
        self._book[oid] = o
        self._role[oid] = role
        return oid

    def _drop(self, oid):
        self._book.pop(oid, None)
        self._role.pop(oid, None)

    def _drop_roles(self, roles):
        for oid in [i for i, r in self._role.items() if r in roles]:
            self._drop(oid)

    def _cancel_all(self):
        self._book.clear()
        self._role.clear()

    def _pending(self, roles):
        return [i for i, r in self._role.items() if r in roles]

    # ================================================================ 合図(R15)
    def _sig_start(self, sid, kind, direction, value):
        self._events.append({"op": "start", "id": sid, "kind": kind, "direction": direction, "value": value})
        return sid

    def _sig_end(self, sid, reason):
        self._events.append({"op": "end", "id": sid, "reason": reason})

    def _entry_sig_end(self, reason):
        if self._e_sig is not None:
            self._sig_end(self._e_sig, reason)
            self._e_sig = None

    def _break_in(self, d, price, line):
        """R12: ブレイクに入る。残りの注文を全部取り消し、合図「ブレイク」を始める。"""
        self._cancel_all()
        self._brk = d
        self._n_brk += 1
        self._brk_sig = self._sig_start(f"b{self._n_brk}", SIG_BREAK, "up" if d == 1 else "down",
                                        {"price": price, "line": line, "center": self._snap["center"]})

    def _break_out(self):
        """R13: ブレイクを抜ける。"""
        self._brk = 0
        if self._brk_sig is not None:
            self._sig_end(self._brk_sig, END_BREAK)
            self._brk_sig = None

    # ================================================================ 玉
    def _avg(self) -> Fraction:
        return self._cost / abs(self._pos)

    def _held(self) -> int:
        h = abs(self._pos) / self._unit
        if h.denominator != 1:
            raise MatildaError(f"建玉 {float(self._pos)} が 1 段の量 {float(self._unit)} の整数倍でない")
        return int(h)

    def _side(self, s):
        return "buy" if s == 1 else "sell"

    def _apply_fill(self, f, start, roles0):
        """約定を 1 つ受ける。返すのは (役, 売買の向き, 約定値段)。roles0 は呼ばれた時点の役の表(同じ点で先に受けた
        約定が帳面を消しても、道が同じ点で約定させた注文の役を引けるように。始値に飛んでブレイクの逆指値と足す段が
        同時に約定した足 2016-01-03T01:24 で、リードがつないで走らせて見つけた)。"""
        oid = f["id"]
        role = self._role.get(oid) or roles0.get(oid)
        if role is None:
            raise MatildaError(f"知らない注文の約定: {oid!r}")
        self._drop(oid)
        q, px = _frac(f["qty"]), _frac(f["px"])
        s = 1 if f["side"] == "buy" else -1
        pos = self._pos
        if pos == 0 or (pos > 0) == (s > 0):
            if role not in ("entry", "add", "level"):
                raise MatildaError(f"決済の注文 {oid} が玉を増やした")
            if pos == 0:  # 取引の始まり
                self._dir = s
                self._unit = q
                self._t0 = start + MINUTE_NS  # R9・R10: 最初の約定があった足の終わり
                self._loosen = False
                self._drop_roles(("entry",))  # 反対側の 1 段目(R3 は玉が無いときだけ)
            self._pos, self._cost = pos + s * q, self._cost + px * q
        else:
            if q > abs(pos):
                raise MatildaError(f"建玉を超えた決済: 建玉 {float(pos)}・決済 {float(q)}")
            self._cost -= self._cost * q / abs(pos)
            self._pos = pos + s * q
        return role, s, float(f["px"])

    def _flat_now(self):
        """玉が 0 に戻った: 残りの注文を全部取り消し、取引の状態を消す(R15 の合図も終える)。"""
        self._cancel_all()
        self._entry_sig_end(END_FLAT)
        self._dir, self._unit, self._t0, self._loosen = 0, None, None, False
        self._cost = Fraction(0)

    def _close_all(self, role, form, px=None):
        """玉の全部を 1 本の注文で閉じる(R10・R12)。残りの注文は全部取り消す。"""
        self._cancel_all()
        self._put(role, form, self._side(-self._dir), abs(self._pos), px)

    # ================================================================ 利確(R8)・ブレイクの逆指値(R12)・段(R4・R6)
    def _tp_px(self) -> float:
        sn, s = self._snap, self._dir
        target = sn["center"] - s * self.p["exit_setting"] * sn["vola"]  # 売り玉は +、買い玉は −
        one = float(self._avg() + s * Fraction(1) / self._unit)  # 利益 1 円の値段(売り玉は −、買い玉は +)
        better = max(target, one) if s == 1 else min(target, one)
        worse = min(target, one) if s == 1 else max(target, one)
        return worse if self._loosen else better

    def _exits(self):
        """利確の limit(玉全体の 1 本)と、ブレイクの逆指値を出し直す。交差する段を取り消す(直すもの 5)。"""
        self._drop_roles(("close", "break"))
        s, sn = self._dir, self._snap
        tp = self._tp_px()
        self._put("close", "limit", self._side(-s), abs(self._pos), tp)
        line = sn["bd"] if s == 1 else sn["bu"]  # 買い玉は下の線に売りの stop、売り玉は上の線に買いの stop
        if self._brk == 0 and line is not None and s * (tp - line) > 0:
            self._put("break", "stop", self._side(-s), abs(self._pos), line)
        self._trim_tiers()

    def _tier_ok(self, px) -> bool:
        """段を出せるか: 利確の limit 以上(売り玉は以下)に段を出さない(直すもの 5・L-816 3.a)。損の側のブレイクの線
        から外(線ちょうどを含む)にも出さない(その値段へ道筋が届く前に R12 で全部閉じるため)。"""
        s, sn = self._dir, self._snap
        tp = [o["px"] for i, o in self._book.items() if self._role[i] == "close"]
        if tp and s * (px - tp[0]) >= 0:
            return False
        line = sn["bd"] if s == 1 else sn["bu"]
        if line is not None and s * (line - px) >= 0:
            return False
        return True

    def _trim_tiers(self):
        for oid in self._pending(TIER_ROLES):
            if not self._tier_ok(self._book[oid]["px"]):
                self._drop(oid)

    def _ladder(self, fpx):
        """R4・R6: 約定値段から step 外側に、次の 1 段だけを出す(段数の上限まで)。約定したら、その約定値段から
        また次の 1 段を出す。足の途中は道筋が続くので、前もって全部並べたときと同じ値段で約定する。始値に飛んだ足では
        始値で約定するのは最初の 1 段だけで、残りはその約定値段から step ずつになる(L-815「1.c 1段目を基準にそれ
        以降の足をステップ毎の値段で約定させないとナンピンにならない」・L-817「問い 1(B-1) a」。作り終えた後の
        批評家 1 回目の [止める]、リードが直した)。"""
        s, step = self._dir, self._snap["step"]
        self._drop_roles(("level",))
        if self._held() < self.levels:
            px = fpx - s * step
            if self._tier_ok(px):
                self._put("level", "limit", self._side(s), self._unit, px)

    # ================================================================ 足の途中
    def _on_stop(self, ev, price, start):
        sn = self._snap
        heads = []
        was = self._dir
        roles0 = dict(self._role)
        for f in ev.get("fills") or []:
            role, s, fpx = self._apply_fill(f, start, roles0)
            if role in ("entry", "add", "level"):
                heads.append(fpx)
            if role in ("entry", "add", "level") and self._e_sig is None:  # R15: 段が約定した時点で始まる
                self._n_e += 1
                self._e_sig = self._sig_start(f"e{self._n_e}", SIG_ENTRY, "long" if s == 1 else "short",
                                              {"px": fpx, "center": sn["center"], "vola": sn["vola"],
                                               "line": sn["lo"] if s == 1 else sn["up"]})
            if role == "break" and self._brk == 0:  # R12: 逆指値で閉じた = ブレイクに入った
                d = -was
                self._break_in(d, fpx, sn["bu"] if d == 1 else sn["bd"])
        if was != 0 and self._pos == 0:
            self._flat_now()
        elif self._pos != 0 and ev.get("fills") and not self._pending(("market",)):
            if heads:
                self._ladder(heads[-1])
            self._exits()  # R8: 約定を受けるたびに出し直す
        touched = ev.get("touched") or []
        if touched and sn is not None:
            self._on_touch(set(float(x) for x in touched), price)
        if self._brk != 0 and self._pos != 0 and not self._pending(("break", "market")):
            # R12: ブレイク中に玉が残った(同じ点で逆指値と段が約定した、など)→ 線の値段の逆指値で全部閉じる。
            # 今いる値段はすでに線の外なので、道がこの点で約定させる
            line = sn["bu"] if self._brk == 1 else sn["bd"]
            if line is None:
                self._close_all("break", "market")
            else:
                self._close_all("break", "stop", line)

    def _on_touch(self, t, price):
        sn = self._snap
        if self._brk != 0:
            if sn["center"] in t:  # R13: 中心に届いたら抜ける(ちょうど中心を含む)
                self._break_out()
            return
        for d, line in ((1, sn["bu"]), (-1, sn["bd"])):
            if line is not None and line in t:  # R12: ブレイクの線に届いた
                self._break_in(d, price, line)
                if self._pos != 0:  # 玉が残っていれば線の値段の逆指値で全部閉じる(道がこの点で約定させる)
                    self._close_all("break", "stop", line)
                return
        if self._dir == 0:
            return
        s = self._dir
        opp = sn["up"] if s == 1 else sn["lo"]
        if opp in t and s * (price - self._last) > 0:
            # R10 イ: 玉と反対側の建ての線に、外へ向かって届いた → その点で成行(線から離れる向きの動き・始値への飛び
            # では発火しない。作り終えた後の批評家 1 回目の [直す])
            self._close_all("market", "market")
            return
        line = sn["lo"] if s == 1 else sn["up"]
        if line in t and not s * (self._last - price) > 0:
            # R5: 外側から線へ戻った(前に見た値段から線へ、外側の向きでなく動いて届いた)= 合図が消えた
            self._drop_roles(TIER_ROLES)
            self._entry_sig_end(END_ENTRY)

    # ================================================================ 足が閉じた
    def _on_close(self, bar, start):
        close = float(bar[4])
        market = False
        if self._snap is not None:
            market = self._rejudge(close)
        before = self._snap
        self._close_gap(start)
        self._add_bar(bar, start)
        if self._snap is None or market:
            return
        if self._snap is not before and self._rejudge_new(close):
            return
        self._place(close, start)

    def _rejudge_new(self, close) -> bool:
        """新しく計算した線・中心と終値でも判断し直す(R5・R10 イ・R13)。見張る値段は「動いて届いた」ときだけ知らせる
        ので、閉じた時点ですでに新しい線の外にある値段は次の足で届かない(作り終えた後の批評家 1 回目の [直す])。
        成行を出したら True。"""
        sn = self._snap
        if self._brk == 1 and close <= sn["center"] or self._brk == -1 and close >= sn["center"]:
            self._break_out()  # R13
        if self._dir == 0 or self._brk != 0:
            return False
        s = self._dir
        if s * (close - (sn["up"] if s == 1 else sn["lo"])) >= 0:  # R10 イ
            self._close_all("market", "market")
            return True
        if s * (close - (sn["lo"] if s == 1 else sn["up"])) > 0:  # R5
            self._drop_roles(TIER_ROLES)
            self._entry_sig_end(END_ENTRY)
        return False

    def _rejudge(self, close) -> bool:
        """その足の間に使っていた線・中心と終値で判断し直す(R5・R10 イ・R12・R13)。成行を出したら True。"""
        sn = self._snap
        if self._brk == 1 and close <= sn["center"] or self._brk == -1 and close >= sn["center"]:
            self._break_out()  # R13(終値がちょうど中心なら抜ける)
        if self._brk == 0:
            d = 1 if sn["bu"] is not None and close >= sn["bu"] else (
                -1 if sn["bd"] is not None and close <= sn["bd"] else 0)
            if d != 0:
                self._break_in(d, close, sn["bu"] if d == 1 else sn["bd"])
                if self._pos != 0:
                    self._close_all("break", "market")  # 足が閉じた後なので次の足の始値で約定する
                    return True
        if self._dir == 0 or self._brk != 0:
            return False
        s = self._dir
        if s * (close - (sn["up"] if s == 1 else sn["lo"])) >= 0:  # R10 イ: 終値が反対側の線の外(線ちょうどを含む)
            self._close_all("market", "market")
            return True
        if s * (close - (sn["lo"] if s == 1 else sn["up"])) > 0:  # R5: 終値が線の内側(ちょうど線は内側としない)
            self._drop_roles(TIER_ROLES)
            self._entry_sig_end(END_ENTRY)
        return False

    def _place(self, close, start):
        """新しい線で次の足の注文を出し直す(R3・R6・R8・R9・R10 ロ)。"""
        sn, p = self._snap, self.p
        if self._dir == 0:
            self._drop_roles(("entry",))
            if self._brk == 0 and sn["gate"] and sn["dev_ok"]:  # R3(I1 の門 dev_ok は 1 段目だけに掛ける)
                for s, px in ((1, sn["lo"]), (-1, sn["up"])):
                    _, q = size_detail(margin_jpy=MARGIN_JPY, use_ratio=USE_RATIO, levels=self.levels, price=px,
                                       quote_ccy="JPY")
                    if q > 0:
                        self._put("entry", "limit", self._side(s), q, px)
            return
        if self._brk != 0:
            raise MatildaError("ブレイク中に玉が残っている(R12 で閉じているはず)")
        s = self._dir
        minutes = (start + MINUTE_NS - self._t0) / MINUTE_NS
        if minutes > 2 * p["alert_count"]:  # R10 ロ: 足が閉じた時点で成行(次の足の始値で約定)
            self._close_all("market", "market")
            return
        self._loosen = minutes > p["alert_count"] or s * (self._avg() - sn["center"]) > 0  # R9
        self._exits()  # R8: 足が閉じるたびに出し直す
        if not self._pending(("level",)):  # R6: 次に足す 1 段を出し直す
            self._drop_roles(("add",))
            if self._brk == 0 and sn["gate"] and self._held() < self.levels:
                a = float(self._avg() - s * _frac(sn["step"]))
                px = min(a, sn["lo"]) if s == 1 else max(a, sn["up"])  # 建値 − step と今の線の遠い方
                if self._tier_ok(px):
                    self._put("add", "limit", self._side(s), self._unit, px)

    # ================================================================ 足の束ね・指標(R1・R11)
    def _close_gap(self, start):
        if self._win is not None and start // self._foot_ns != self._win["idx"]:
            if start // self._foot_ns < self._win["idx"]:
                raise MatildaError("足の時刻が戻った")
            self._close_window()

    def _add_bar(self, bar, start):
        idx = start // self._foot_ns
        o, h, lo, c, v = (float(x) for x in bar[1:6])
        if self._win is None:
            self._win = {"idx": idx, "end": (idx + 1) * self._foot_ns, "o": o, "h": h, "l": lo, "c": c, "v": v}
        else:
            w = self._win
            w["h"], w["l"] = max(w["h"], h), min(w["l"], lo)
            w["c"], w["v"] = c, w["v"] + v
        end = start + MINUTE_NS
        if end > self._win["end"]:
            raise MatildaError("足が窓の終わりを越える")
        if end == self._win["end"]:
            self._close_window()

    def _close_window(self):
        w, self._win = self._win, None
        self._update(w)
        if self._closed >= self._warm:
            self._snap = self._make_snap(w["c"])

    def _update(self, w):
        p = self.p
        o, h, lo, c = w["o"], w["h"], w["l"], w["c"]
        body = c - o
        sign = 1 if body > 0 else (-1 if body < 0 else 0)
        if sign == 1:
            top, under = h - c, o - lo
        else:
            top, under = h - o, c - lo
        hc, lc = h, lo
        bi = p["beard_ignore"]
        if bi is not None:  # ヒゲの切り落とし
            if top > bi:
                hc = c if sign == 1 else o
            if under > bi:
                lc = c if sign == -1 else o
        self._wins.append({"h": hc, "l": lc, "body": abs(body)})
        self._closed += 1
        wins = list(self._wins)
        vc, rc, mult = p["vola_count"], p["range_count"], p["break_len_mult"]
        vola = sum(x["body"] for x in wins[-vc:]) / vc  # 今の足を含む直近 vola_count 本の実体の和 ÷ vola_count(L-849)
        r1, r2 = wins[-rc:], wins[-rc * mult:]
        rmax, rmin = max(x["h"] for x in r1), min(x["l"] for x in r1)
        rmax2, rmin2 = max(x["h"] for x in r2), min(x["l"] for x in r2)
        width = rmax - rmin
        center = round((rmax + rmin) / 2)
        if rmax != rmax2 or self._brk != 0:
            self._up.append(rmax + width * p["break_dist"])
        if rmin != rmin2 or self._brk != 0:
            self._dn.append(rmin - width * p["break_dist"])
        self.ind = {"vola": vola, "range_max": rmax, "range_min": rmin, "range_max2": rmax2, "range_min2": rmin2,
                    "width": width, "center": center}

    def _make_snap(self, close):
        """次の足の間に使う線(R1〜R3・R11)。"""
        p, ind = self.p, self.ind
        vola, center, width = ind["vola"], ind["center"], ind["width"]
        es = vola * p["entry_setting"]
        bu = bd = None
        k = p["break_delay"]
        if k != 0:  # break_delay = 0 ならブレイクを見ない
            if len(self._up) >= k:
                bu = max(self._up[-k], ind["range_max2"])
            if len(self._dn) >= k:
                bd = min(self._dn[-k], ind["range_min2"])
        rs, ors, vs = p["range_setting"], p["over_range_setting"], p["vola_setting"]
        shut = (rs is not None and width < rs * close) or (ors is not None and width > ors * close) \
            or (vs is not None and vola <= vs * close)
        ds = p["dev_setting"]  # 改良案 I1: 建ての線が中心に近い(幅に比べて)ときは 1 段目を出さない
        dev_ok = ds is None or (width > 0 and es / width >= ds)
        return {"lo": center - es, "up": center + es, "center": center, "vola": vola, "step": vola * p["step_setting"],
                "bu": bu, "bd": bd, "gate": not shut, "dev_ok": dev_ok}

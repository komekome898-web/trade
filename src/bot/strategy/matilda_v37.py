"""マチルダ(v37)の道の戦略(委任文 docs/DISCUSSIONS/2026-10-06_held_batches/matilda_step0/DELEGATION_matilda_v37.md)。

原典は docs/legacy/matilda_for_TaroCamp37.py(以下 v37:行)。1 分足への写し方は委任文の「写し方の決まり」M1〜M11 の
とおり。受け入れの試験は tests/road/test_matilda_v37_spec.py。

オーナーの逐語(写し方の出所):
- L-776「**全ての変数は固定値でなく調整可能な値で、それはバックテストで探る族の種類と同義です。modeの切り替えとかもあったと思う。**」
  (設定は全部引数。鍵は PARAM_KEYS の 17、原典の値は V37_ORIGINAL)
- L-779「**時間とsfdは取引所の事情なので外す**」「**注文は計算した値そのもので行ってください。**」
- L-781「**1 段の量は建てた時の値段で決まるが、段毎の量は建玉を持った時点での量と同じにする。**」(M11: 土台の size_ref)
- L-782「**1. 利確は中央値から exit_setting × ボラ 離れたところ**」「**2.v52の挙動は今回考慮せず外す**」
- L-784「**実装ミスなので割る数は分子を合わせてください。他の計算も合わせてください。**」「**売りと買いをそろえる**」
- L-788「**breakexitsizeはロット数上限に合わせる**」/ L-789「**あってる**」/ L-801「**(a)**」/ L-803「**fukuriは使わないでください**」
- L-809「**合図が消えた時は残りの段も全部取り消して、利確だけ出し直す形でお願いします。**」
- L-770「**建ての指値と一緒に決済の指値を出しておき**」/ L-774「**なんで次の段の指値が次の足になるの？**」

写さないもの: SFD の枝・休む時間・板(bigvol・wid・2 円手前)・強制の成行の「1 段ずつ」・0.01 BTC の補い・取引所の誤りの
扱い・通知・fukuri と自動の段数(委任文の「写し方の決まり」の冒頭と M1)。

流れ(M3): 1 分足が届いたら同じ時刻のタイマーを置き、判定はそのタイマー(`ClockEvent`、タグ DECIDE_TAG)で行う
(足 → その足の約定の知らせ → タイマー の順に届く)。判定の中の順:
 (1) 欠けで閉じていない前の窓を閉じる(M2)
 (2) 慣らし(M5)が済んでいれば: 玉の向きの変化(M6)→ ブレイク(M7)→ 建ての旗と合図「建て」(M8)→ 決済の旗(M10)→
     注文の動き(M9 の建て・M10 の決済。「全部取り消す」の後は答えが全部届いてから同じ時刻に続ける)→ ブレイクの解除(M10b)
 (3) 今の 1 分足を窓に足し、窓が閉じたら指標(M4)を更新する
指標は閉じた窓まで(今の 1 分足を含まない)、last = 今の 1 分足の終値。

注文の動きは生成器(`_actions`)で書く。「全部取り消す」や決済の取り消しの後の `yield` で、取り消した注文の答え
(取り消した・約定した・取り消しの拒否・取引所が閉じた)が全部届くまで止まり、答えの知らせの step で続ける。
委任文で決まらない場面(ブレイクの旗が ±1 から ∓1 に直に変わる、前の判定の答えを待っている間に次の判定が来る)は、
選ばずに止める(RoadStrategyError。報告の「問いとして返したこと」)。
出す文は日本語(O-1)。
"""
from __future__ import annotations

import math
from collections import deque
from decimal import Decimal
from fractions import Fraction
from typing import Any, Optional

from bot.bt.core import BarEvent, ClockEvent, OrderFillEvent
from bot.bt.road import NO_SIGNAL, RoadStrategy, RoadStrategyError

NS = 10**9
MINUTE_NS = 60 * NS
DECIDE_TAG = "matilda_v37_decide"
OPEN_STATES = ("PENDING_NEW", "OPEN", "PENDING_CANCEL", "STATE_UNKNOWN")  # 土台の OPEN_STATE_VALUES と同じ
SIG_ENTRY = "建て"
SIG_BREAK = "ブレイク"
END_ENTRY = "合図の条件が外れた"
END_BREAK = "中心に戻った"

PARAM_KEYS = ("levels", "foot", "vola_count", "range_count", "alert_count", "range_setting", "over_range_setting",
              "vola_setting", "entry_setting", "exit_setting", "break_delay", "break_dist", "break_len_mult",
              "beard_ignore", "step_setting", "step_exit", "b_signal")

# 原典の値(v37:109-160。比の門は 60 万円/BTC で割った比: L-782「**4.(a)大体60万円/btcくらいだったと思います。**」。
# vola_setting は v37:133 で注釈に消されていたので None。levels = sizemax ÷ sizemin = 0.14 ÷ 0.02 = 7)
V37_ORIGINAL = {
    "levels": 7, "foot": 1, "vola_count": 40, "range_count": 40, "alert_count": 20,
    "range_setting": 150 / 600000, "over_range_setting": 100000 / 600000, "vola_setting": None,
    "entry_setting": 2, "exit_setting": 0.8, "break_delay": 1, "break_dist": 0.5, "break_len_mult": 2,
    "beard_ignore": 1, "step_setting": 1, "step_exit": 0.8, "b_signal": True,
}


# ---------------------------------------------------------------- 引数(M1)
def _is_num(v: Any) -> bool:
    return not isinstance(v, bool) and isinstance(v, (int, float))


def _need_int(p: dict, k: str, lo: int) -> None:
    v = p[k]
    if type(v) is not int:
        raise TypeError(f"引数 {k} は整数で渡す(受け取ったのは {v!r})")
    if v < lo:
        raise ValueError(f"引数 {k} は {lo} 以上の整数: {v!r}")


def _need_num(p: dict, k: str, *, gt: Optional[float] = None, ge: Optional[float] = None,
              allow_none: bool = False) -> None:
    v = p[k]
    if v is None and allow_none:
        return
    if not _is_num(v):
        raise TypeError(f"引数 {k} は数で渡す(受け取ったのは {v!r})")
    if not math.isfinite(float(v)):
        raise ValueError(f"引数 {k} は有限の数: {v!r}")
    if gt is not None and not v > gt:
        raise ValueError(f"引数 {k} は {gt} より大きい数: {v!r}")
    if ge is not None and not v >= ge:
        raise ValueError(f"引数 {k} は {ge} 以上の数: {v!r}")


def check_params(params: Any) -> dict:
    """引数を確かめて写しを返す(M1)。足りない・知らない鍵、型や範囲の外れは止める(ValueError / TypeError)。"""
    if not isinstance(params, dict):
        raise TypeError(f"引数は辞書で渡す(受け取ったのは {type(params).__name__})")
    p = dict(params)
    missing = [k for k in PARAM_KEYS if k not in p]
    unknown = sorted(k for k in p if k not in PARAM_KEYS)
    if missing or unknown:
        raise ValueError(f"引数の鍵がちょうど {len(PARAM_KEYS)} でない: 足りない {missing}・知らない {unknown}")
    _need_int(p, "levels", 1)
    _need_int(p, "foot", 1)
    _need_int(p, "vola_count", 2)
    _need_int(p, "range_count", 1)
    _need_num(p, "alert_count", gt=0)
    for k in ("range_setting", "over_range_setting", "vola_setting"):
        _need_num(p, k, ge=0, allow_none=True)
    _need_num(p, "entry_setting", gt=0)
    _need_num(p, "exit_setting", ge=0)
    if not p["exit_setting"] < p["entry_setting"]:
        raise ValueError(f"引数 exit_setting は entry_setting より小さい(v37:139): {p['exit_setting']!r} ≧ "
                         f"{p['entry_setting']!r}")
    _need_int(p, "break_delay", 0)
    _need_num(p, "break_dist", gt=0)
    _need_int(p, "break_len_mult", 2)
    _need_num(p, "beard_ignore", gt=0, allow_none=True)
    _need_num(p, "step_setting", gt=0)
    _need_num(p, "step_exit", gt=0)
    if type(p["b_signal"]) is not bool:
        raise TypeError(f"引数 b_signal は真偽で渡す(受け取ったのは {p['b_signal']!r})")
    return p


# ---------------------------------------------------------------- 判定の純な関数(M8・M10)
def entry_flag(break_flg: int, b_signal: int, flat: bool, last: float, center: float, vola: float, width: float,
               entry_setting: float, range_setting: Optional[float], over_range_setting: Optional[float],
               vola_setting: Optional[float]) -> int:
    """建ての旗(M8。v37:991-1005 の SFD の無い枝)。1 = 買い、−1 = 売り、0 = なし。比の門は 値 × last と比べる。"""
    if break_flg == 0:
        if (range_setting is not None and width < range_setting * last) \
                or (over_range_setting is not None and width > over_range_setting * last) \
                or (vola_setting is not None and vola <= vola_setting * last):
            return 0
        if last > center + vola * entry_setting:
            return -1
        if last < center - vola * entry_setting:
            return 1
        return 0
    if break_flg == -b_signal or (b_signal == 0 and flat):
        return 0
    return break_flg


def exit_flag(break_flg: int, b_signal: int, entry_flg: int, side: int, minutes_held: float, alert_count: float,
              avg: float, center: float, held_levels: int, order_count: int) -> int:
    """決済の旗(M10。v37:1007-1036)。side: 玉の向き(1 = 買い玉、−1 = 売り玉)。
    3 = 全部取り消して成行、2 = 緩めた利確、1 = 利確、0 = 決済を出さない。"""
    if side not in (1, -1):
        raise ValueError(f"exit_flag: 玉の向きは 1 か −1: {side!r}")
    if break_flg == 0:
        if entry_flg == -side or minutes_held > alert_count * 2:
            return 3
        if minutes_held > alert_count or (avg > center if side == 1 else avg < center):
            return 2
        return 1
    if entry_flg == -side:
        return 3
    if b_signal == 0:
        return 1
    if break_flg == -b_signal:
        return 2
    if held_levels >= order_count:
        return 1
    return 0


def exit_price(exit_flg: int, break_flg: int, side: int, center: float, vola: float, avg: float, held_levels: int,
               exit_setting: float, step_exit: float) -> float:
    """決済の指値の値段(M10。L-782・L-789・v37:898・912)。x = ボラ × step_exit ÷ 持つ段数。"""
    if side not in (1, -1):
        raise ValueError(f"exit_price: 玉の向きは 1 か −1: {side!r}")
    if exit_flg not in (1, 2):
        raise ValueError(f"exit_price: 値段を出すのは決済の旗 1 か 2: {exit_flg!r}")
    if exit_flg == 1 and break_flg == 0:
        return center - side * exit_setting * vola
    if held_levels < 1:
        raise ValueError(f"exit_price: 持つ段数が 1 より少ない(x = ボラ × step_exit ÷ 持つ段数 が出せない): {held_levels!r}")
    x = vola * step_exit / held_levels
    if exit_flg == 1:
        return avg + side * x
    return min(center, avg + x) if side == 1 else max(center, avg - x)


# ---------------------------------------------------------------- 戦略
class MatildaV37(RoadStrategy):
    """マチルダ(v37)の道の戦略。円建て(quote_ccy JPY)だけ。"""

    def __init__(self, params: dict) -> None:
        super().__init__(quote_ccy="JPY")
        p = check_params(params)
        self.p = p
        self.levels: int = p["levels"]
        self._foot_ns = p["foot"] * MINUTE_NS
        self._warm = max(p["vola_count"], p["range_count"] * p["break_len_mult"])
        keep = max(p["vola_count"], p["range_count"] * p["break_len_mult"])
        # 足の束ね(M2)
        self._bar: Optional[BarEvent] = None  # 判定を待っている 1 分足
        self._win: Optional[dict] = None  # 閉じていない窓 {idx, end, o, h, l, c, v}
        self._wins: deque = deque(maxlen=keep)  # 閉じた窓(切った高値・安値、実体、出来高)
        self._closed = 0  # 閉じた窓の本数
        # 指標(M4)
        self.ind: Optional[dict] = None
        self._exp = 0  # expantion_flg
        self._bsig = 0  # b_signal
        self._up: deque = deque(maxlen=max(1, p["break_delay"]))  # ブレイクの線の列(上)
        self._dn: deque = deque(maxlen=max(1, p["break_delay"]))  # ブレイクの線の列(下)
        # 旗と合図(M7・M8)
        self._brk = 0  # ブレイクの旗
        self._brk_sig: Optional[str] = None
        self._n_brk = 0
        self._eflg = 0  # 前の判定の建ての旗
        self._e_sig: Optional[str] = None
        self._n_e = 0
        # 建玉(約定の知らせから。平均の原価法で建値を持つ)
        self._m_pos = Fraction(0)
        self._cost = Fraction(0)
        self._prev_dir = 0  # 前の判定の建玉の向き
        self._filled_since = False  # 前の判定の後に約定があったか
        self._poschange: Optional[int] = None  # 玉の向きが変わった時刻(ns)
        # 注文(M9・M10・M11)
        self._mine: dict = {}  # 注文の番号 -> {kind: entry / with_entry / close, parent}
        self._filled_by: dict = {}  # 注文の番号 -> 約定した量の和(Fraction)
        self._cnt = {1: 0, -1: 0}  # 段の数え(買い・売り)
        self._last_px = {1: None, -1: None}  # 前の段の値段
        self._first_px = {1: None, -1: None}  # 出ている 1 段目の値段
        self._first: Optional[str] = None  # 取引の最初の段の注文の番号(M11)
        self._first_qty: Optional[Fraction] = None
        self._close_at: dict = {}  # close の注文の番号 -> (出した時の建玉, 建値)
        self._await: set = set()  # 答えを待っている取り消しの注文
        self._gen = None  # 続きを待っている注文の動き

    # ---- 出来事 ------------------------------------------------------------------
    def step(self, event, ctx) -> None:
        if isinstance(event, BarEvent):
            if self._bar is not None:
                raise RoadStrategyError("前の 1 分足の判定(タイマー)が届く前に次の足が届いた")
            self._bar = event
            ctx.set_timer(int(ctx.now_ns), DECIDE_TAG)
            return
        if isinstance(event, ClockEvent):
            if event.tag == DECIDE_TAG:
                bar, self._bar = self._bar, None
                if bar is None:
                    raise RoadStrategyError("判定のタイマーが届いたのに判定を待っている足が無い")
                self._decide(bar, int(ctx.now_ns))
            return
        if isinstance(event, OrderFillEvent):
            self._on_fill(event)
        self._drive()

    def _on_fill(self, ev: OrderFillEvent) -> None:
        q = Fraction(Decimal(repr(float(ev.size))))
        px = Fraction(Decimal(repr(float(ev.price))))
        side = ev.side or self._row(ev.client_order_id)["side"]
        s = 1 if side == "buy" else -1
        self._filled_by[ev.client_order_id] = self._filled_by.get(ev.client_order_id, Fraction(0)) + q
        self._filled_since = True
        pos = self._m_pos
        if pos == 0 or (pos > 0) == (s > 0):
            self._m_pos, self._cost = pos + s * q, self._cost + px * q
            return
        c = min(q, abs(pos))
        cost = self._cost - (self._cost * c / abs(pos) if c < abs(pos) else self._cost)
        rest = q - c
        self._m_pos = pos + s * q
        self._cost = cost + px * rest if rest > 0 else cost

    def _row(self, coid: str) -> dict:
        row = self._orders.get(coid)
        if row is None:
            raise RoadStrategyError(f"注文 {coid!r} の行が無い")
        return row

    # ---- 足の束ね(M2)と指標(M4) ----------------------------------------------------
    def _bar_times(self, bar: BarEvent) -> tuple[int, int]:
        if bar.start_time_ns is None:
            raise RoadStrategyError("1 分足に始まりの時刻(start_time_ns)が無い(窓に束ねられない)")
        return int(bar.start_time_ns), int(bar.exchange_time_ns)

    def _close_window(self) -> None:
        w, self._win = self._win, None
        assert w is not None
        self._update(w)

    def _add_bar(self, bar: BarEvent) -> None:
        start, end = self._bar_times(bar)
        idx = start // self._foot_ns
        if self._win is None:
            self._win = {"idx": idx, "end": (idx + 1) * self._foot_ns, "o": float(bar.open), "h": float(bar.high),
                         "l": float(bar.low), "c": float(bar.close), "v": float(bar.volume)}
        else:
            w = self._win
            w["h"], w["l"] = max(w["h"], float(bar.high)), min(w["l"], float(bar.low))
            w["c"], w["v"] = float(bar.close), w["v"] + float(bar.volume)
        if end > self._win["end"]:
            raise RoadStrategyError(f"足(始まり {start}・閉じた時刻 {end})が窓の終わり {self._win['end']} を越える"
                                    f"(1 分足を foot 分の窓に束ねる。M2)")
        if end == self._win["end"]:
            self._close_window()

    def _close_gap(self, bar: BarEvent) -> None:
        """(1) 窓の終わりの足が無いまま次の窓の足が来たら、前の窓を、ある足だけで閉じる(M2)。"""
        start, _ = self._bar_times(bar)
        if self._win is not None and start // self._foot_ns != self._win["idx"]:
            if start // self._foot_ns < self._win["idx"]:
                raise RoadStrategyError("足の時刻が戻った")
            self._close_window()

    def _update(self, w: dict) -> None:
        """窓が閉じるたびの指標の更新(M4。v37:556-643、割る数は L-784)。"""
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
        if prev is not None:  # v37:591-596(巡回中の get_candle)
            if hc > prev["range_max"]:
                self._exp += 1
            elif lc < prev["range_min"]:
                self._exp -= 1
            elif (self._exp >= 1 and lc < prev["center"]) or (self._exp <= -1 and hc > prev["center"]):
                self._exp = 0
        before = list(self._wins)  # 今の窓を除く
        self._wins.append({"h": hc, "l": lc, "body": abs(body), "v": v})
        self._closed += 1
        wins = list(self._wins)
        vc, rc, mult = p["vola_count"], p["range_count"], p["break_len_mult"]
        prior = before[-(vc - 1):]
        vola = sum(x["body"] for x in prior) / (vc - 1)
        vol_ave = sum(x["v"] for x in prior) / (vc - 1)
        r1, r2 = wins[-rc:], wins[-rc * mult:]
        rmax, rmin = max(x["h"] for x in r1), min(x["l"] for x in r1)
        rmax2, rmin2 = max(x["h"] for x in r2), min(x["l"] for x in r2)
        width = rmax - rmin
        center = round((rmax + rmin) / 2)
        if rmax != rmax2 or self._brk != 0:
            self._up.append(rmax + width * p["break_dist"])
        if rmin != rmin2 or self._brk != 0:
            self._dn.append(rmin - width * p["break_dist"])
        if p["b_signal"]:  # v37:621-643
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

    # ---- 判定(M3・M5〜M10b) --------------------------------------------------------
    def _decide(self, bar: BarEvent, now: int) -> None:
        self._close_gap(bar)
        if self._closed >= self._warm:
            self._judge(float(bar.close), now)
        self._add_bar(bar)

    def _judge(self, last: float, now: int) -> None:
        if self._gen is not None or self._await:
            raise RoadStrategyError("前の判定の取り消しの答えを待っている間に次の判定が来た(この場面の扱いは委任文で"
                                    "決まっていない。遅れ 0 の走らせでは起きない)")
        p, ind = self.p, self.ind
        assert ind is not None
        self._prune()
        # M6 玉の向きの変化
        d = (self._m_pos > 0) - (self._m_pos < 0)
        canceled = False
        if d != self._prev_dir or (self._filled_since and d == 0):
            if d == 0:
                self._cancel_all()
                canceled = True
            self._poschange = now
        self._prev_dir, self._filled_since = d, False
        # M7 ブレイクの判定
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
                if self._brk != 0:
                    raise RoadStrategyError(f"ブレイクの旗が {self._brk} から {new} に直に変わった(v37:930-950 では起こり"
                                            f"うるが、合図「{SIG_BREAK}」の扱いは委任文で決まっていない)")
                self._brk = new
                self._n_brk += 1
                self._brk_sig = self.signal_start(f"b{self._n_brk}", SIG_BREAK, "up" if new == 1 else "down",
                                                  {"close": last, "center": ind["center"]})
        # M8 建ての旗と合図
        flat = self._m_pos == 0
        center, vola = ind["center"], ind["vola"]
        ef = entry_flag(self._brk, self._bsig, flat, last, center, vola, ind["width"], p["entry_setting"],
                        p["range_setting"], p["over_range_setting"], p["vola_setting"])
        if ef != self._eflg:
            if self._e_sig is not None:
                self.signal_end(self._e_sig, END_ENTRY)
                self._e_sig = None
            if ef != 0:
                self._n_e += 1
                es, xs = vola * p["entry_setting"], vola * p["exit_setting"]
                value = {"close": last, "center": center, "vola": vola, "range_max": ind["range_max"],
                         "range_min": ind["range_min"], "width": ind["width"], "lsp": center - es, "ssp": center + es,
                         "lep": center - xs, "sep": center + xs, "break_flg": self._brk, "b_signal": self._bsig,
                         "expantion_flg": self._exp, "levels": self.levels}
                self._e_sig = self.signal_start(f"e{self._n_e}", SIG_ENTRY, "long" if ef == 1 else "short", value)
        self._eflg = ef
        # M10 決済の旗(建ての前に計算する。M9)
        snap = {"last": last, "now": now, "center": center, "vola": vola, "brk": self._brk, "bsig": self._bsig,
                "ef": ef, "sig": self._e_sig, "xf": 0}
        if not flat:
            snap["xf"] = self._exit_flag_now(snap, d)
        self._gen = self._actions(snap, canceled)
        self._drive()
        # M10b ブレイクの解除(建てと決済の後)
        if (self._brk == 1 and last < center) or (self._brk == -1 and last > center):
            self._brk, self._bsig = 0, 0
            if self._brk_sig is not None:
                self.signal_end(self._brk_sig, END_BREAK)
                self._brk_sig = None

    def _minutes(self, now: int) -> float:
        assert self._poschange is not None
        return (now - self._poschange) / MINUTE_NS

    def _avg(self) -> int:
        """建値 = 約定から計算した平均の値段(平均の原価法)の round(v37:357-358)。"""
        return round(self._cost / abs(self._m_pos))

    def _held(self) -> int:
        """持つ段数 = round(|建玉| ÷ 取引の最初の段の量)(M10)。"""
        if self._first_qty is None or self._first_qty == 0:
            raise RoadStrategyError("建玉があるのに取引の最初の段(量の元)が無い")
        return round(abs(self._m_pos) / self._first_qty)

    def _exit_flag_now(self, snap: dict, d: int) -> int:
        return exit_flag(snap["brk"], snap["bsig"], snap["ef"], d, self._minutes(snap["now"]), self.p["alert_count"],
                         self._avg(), snap["center"], self._held(), self.levels)

    # ---- 注文の動き(M9・M10) -------------------------------------------------------
    def _answered(self, coid: str) -> bool:
        return self.order_state(coid) not in OPEN_STATES or not self._cancel_pending.get(coid, False)

    def _drive(self) -> None:
        self._await = {c for c in self._await if not self._answered(c)}
        while self._gen is not None and not self._await:
            try:
                next(self._gen)
            except StopIteration:
                self._gen = None
            self._await = {c for c in self._await if not self._answered(c)}

    def _prune(self) -> None:
        """閉じた注文を持ち物から外す(長い走らせで毎回の数えを重くしない)。開いた with_entry の建ての約定の量は残す。"""
        self._mine = {c: m for c, m in self._mine.items() if self._m_open(c)}
        keep = set(self._mine) | {m["parent"] for m in self._mine.values() if m["parent"] is not None}
        self._filled_by = {c: q for c, q in self._filled_by.items() if c in keep}
        self._close_at = {c: v for c, v in self._close_at.items() if c in self._mine}

    def _m_open(self, coid: str) -> bool:
        return self.order_state(coid) in OPEN_STATES

    def _cancel(self, coid: str) -> None:
        if not self._cancel_pending.get(coid, False):
            self.cancel(coid)
        self._await.add(coid)

    def _cancel_all(self) -> None:
        """「全部取り消す」(M6。v37:651-665 の cancel_allorders): 決済(close と with_entry)を先に、建てを後に取り消し、
        段の数え・置き直しの待ちを空にし、玉が無ければ取引の最初の段も空にする。"""
        opened = [c for c in self._mine if self._m_open(c)]
        for c in [c for c in opened if self._mine[c]["kind"] != "entry"] + \
                 [c for c in opened if self._mine[c]["kind"] == "entry"]:
            self._cancel(c)
        self._cnt = {1: 0, -1: 0}
        self._last_px = {1: None, -1: None}
        self._first_px = {1: None, -1: None}
        if self._m_pos == 0:
            self._first, self._first_qty = None, None

    def _actions(self, snap: dict, canceled: bool):
        if canceled:
            yield
        if self.is_flattening():
            return
        xf, ef = snap["xf"], snap["ef"]
        if xf == 3:  # M10 旗 3: 全部取り消してから成行(v37:703-714 の一括。L-801)
            self._cancel_all()
            yield
            self.flatten(NO_SIGNAL)
            return
        # M9 建て
        flat = self._m_pos == 0
        if ef in (1, -1):
            if self._cnt[-ef] != 0 and flat:
                self._cancel_all()
                yield
            yield from self._ladder(snap, ef)
        elif self._cnt[1] != 0 or self._cnt[-1] != 0:  # 旗 0: 玉があっても全部取り消す(L-809)
            self._cancel_all()
            yield
        # M10 決済
        if self._m_pos != 0 and xf in (1, 2):
            yield from self._exit(snap, xf)

    def _ladder(self, snap: dict, s: int):
        """はしご(M9)。s = 1 は買い、−1 は売り(向きを逆に)。"""
        p = self.p
        step = snap["vola"] * p["step_setting"]
        center = snap["center"]
        p1 = (center - s * snap["vola"] * p["entry_setting"]) if snap["brk"] == 0 else snap["last"]
        flat = self._m_pos == 0
        if flat and self._cnt[s] != 0 and self._first_px[s] is not None and s * (p1 - self._first_px[s]) > 0:
            self._cancel_all()  # v37:851-853(玉なしで 1 段目が値段から離れたら置き直す)
            yield
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
        sig = snap["sig"]
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
            side = "buy" if s == 1 else "sell"
            ref = self._first
            if xf in (1, 2):
                xpx = exit_price(xf, snap["brk"], s, center, snap["vola"], avg_k, held, p["exit_setting"],
                                 p["step_exit"])
                e, x = self.place_with_exit(side, px, self.levels, sig, xpx, size_ref=ref)
                self._mine[e] = {"kind": "entry", "parent": None}
                self._mine[x] = {"kind": "with_entry", "parent": e}
            else:
                e = self.place(side, "limit", px, self.levels, sig, size_ref=ref)
                self._mine[e] = {"kind": "entry", "parent": None}
            if ref is None:
                self._first = e
                self._first_qty = Fraction(Decimal(self._row(e)["qty"]))
            if self._cnt[s] == 0:
                self._first_px[s] = px
            self._last_px[s] = px
            self._cnt[s] += 1

    def _live_exits(self) -> list:
        """出ている決済: close の注文と、建てが約定した with_entry の決済(取引所が閉じたものは出ていない)。"""
        out = []
        for c, m in self._mine.items():
            if not self._m_open(c):
                continue
            if m["kind"] == "close" or (m["kind"] == "with_entry"
                                        and self._filled_by.get(m["parent"], Fraction(0)) > 0):
                out.append(c)
        return out

    def _exit(self, snap: dict, xf: int):
        """決済(M10 旗 1・2。v37:913-921)。"""
        p = self.p
        d = (self._m_pos > 0) - (self._m_pos < 0)
        avg, held = self._avg(), self._held()
        price = exit_price(xf, snap["brk"], d, snap["center"], snap["vola"], avg, held, p["exit_setting"],
                           p["step_exit"])
        live = self._live_exits()
        if len(live) == 1 and self._mine[live[0]]["kind"] == "close":
            c = live[0]
            row = self._row(c)
            same = Fraction(Decimal(row["qty"])) == abs(self._m_pos) and self._close_at.get(c) == (self._m_pos, avg)
            if same:
                cur = float(row["limit_px"])
                closer = price < cur if row["side"] == "sell" else price > cur
                if not closer:
                    return
        for c in live:
            self._cancel(c)
        if live:
            yield
        if self._m_pos == 0:
            return
        c = self.close(NO_SIGNAL, "limit", price)
        self._mine[c] = {"kind": "close", "parent": None}
        self._close_at[c] = (self._m_pos, self._avg())


def pipeline_strategy(params: dict, price_type) -> MatildaV37:
    """道の走らせ(`bot.bt.pipeline` の strategy.kind = module)の口。"""
    return MatildaV37(params)

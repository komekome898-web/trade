"""カード 4 段 1: v37 を 1 分足で指値として再現する(仕様 docs/RESEARCH/cards/c4_owner_matilda_range/limit_sim/SPEC.md)。

原典 = docs/legacy/matilda_for_TaroCamp37.py(以下「v37 の n 行」)。意図 = INTENT_MAP §10・§11(L-577〜L-583)。
カードの口(持ち高を毎分返す形)は指値を表せないので使わない。窓・実体の端・ボラ・幅の門・足のまとめ方は
カード 4(bot.research.cards.library.c4_owner_matilda_range)と同じ書き方にし、値の表の定数はそこから読む。

使い方
------
    sim = MatildaLimitSim(fill_side="good")      # 引数は仕様 5 の表の値だけ(表の外は ValueError)
    for b in bars:                                 # 1 分足を古い順に(暦年ごとに分けて渡してもよい。状態は続く)
        rows += sim.feed(b)                        # この足で終わった取引の行
    rows += sim.finish()                           # 期間の終わりに持っている持ち高を最後の終値で閉じる

足 b は start_time_ns(1 分の始まり)・open・high・low・close・volume を持つもの(bot.bt.core.BarEvent など)。

仕様の節とコードの対応
----------------------
  1   出来高 0・値段が有限でない足は入れない: feed の頭
  2   足 k の量(窓・端・幅・中心・ボラ・2 倍の窓・ブレイクの判定値): _push / _make_q / _update_break_prices
  3-1 ブレイク(上を先に、判定値の値段、解ける): _bar の 1. と 6.、_leg の "brk"
  3-2 入り(幅の門・段の値段・上限 N・反対の入り・brk != 0・follow・時計): _leg の "ent"・"opp"、_open
  3-3 利確の指値(flg 1・2・中心型・ブレイク中): _tp
  3-4 成行で閉じる(反対の入り・反対のブレイク・時間): _leg の "opp"・"brk"、_bar の 0. と 5.
  3-5 決まらない足(良い側・悪い側): _bar の 3.・4.、_run_path
  4   損益と取引の行: _close_row
  5   引数の表: MatildaLimitSim.__init__

1 本の足の中の扱い(仕様 3-5 を実装した形。仕様で決まっていなかった所は【置いた形】と書く)
----------------------------------------------------------------------------------------------
足の頭(リードの決め。仕様 3-5 の補足): 始値 O はその足で最初に付いた値段とし、O の時点で既に越えている指値
(入り・段の追加・利確・反対の入り・ブレイクの判定値。上りの側は値段 < O、下りの側は値段 > O)は、2 本の脚より前に
起きたものとする。約定の値段は指値の値段のまま(始値の方が有利でも始値は使わない)。中の順は脚と同じ(値段の順・
同じ値段は下の順)。上りの側と下りの側の両方に当たるときは、上りの側 → 下りの側の順【置いた形】。持ち高 0 の売りと買い、買いの利確と
段、売りの利確と段は、同じ量では両側に同時には来ない(S1 > B1、段は建値より不利な側)。両側に来うるのは、上の
ブレイクの判定値(< O)と売りの利確(> O)、下のブレイクの判定値(> O)と買いの利確(< O)の組。
足の頭で起きたものは 2 通りの道で同じなので、それだけでは決まらない足にならない。
続けて、足 k+1 の値段の動きを 2 通りの道で通す: 上が先(始値 → 高値 → 安値)と、下が先(始値 → 安値 → 高値)。
各「脚」(高値へ向かう上り / 安値へ向かう下り)の中では、越えた値段の順に出来事を起こす(上りは安い値段から、
下りは高い値段から。同じ値段ならブレイク → 利確 → 反対の入り → 入りの順)。出来事は
  ブレイク(判定値の値段)/ 利確(利確の値段)/ 反対の入り(S1 または B1 で閉じる)/ 入り・段の追加(段の値段)。
2 通りの道で結果が同じなら決まる足。違えば決まらない足で、
  - 片方の道でだけ利確が起きる: 良い側 = 利確が起きる道(仕様「利確が先」)。悪い側 = もう一方の道を、利確の値段の
    手前で脚を止めて通す(仕様「利確はその足では約定しない」)。止めた後も、その脚の先にあるブレイクの判定値は
    値段の順に越え、ブレイクの状態(brk)だけを変える(持ち高は閉じない。利確より向こうの値段で閉じると利確より
    良い値段になるため)【置いた形】。なお、止める道はもともと利確が起きない道なので、止める値段に届くことは無い
    【推定: 止めない道と止める道は、止める値段に届くまで同じ出来事を通る】。
  - 両方の道で利確が起きる(リードの決め。INTENT_MAP 238 行の定義では「利確まで済んだ」足): 2 本の道で結果が
    違うので決まらない足に数える。良い側 = 損益の良い方の道、悪い側 = 損益の悪い方の道。どちらも止めずに通す。
    損益の比べ方: その足で閉じた取引の損益(仕様 4 の式。取引の始めからの損益)と、足の終わりに持っている持ち高の
    含み(各段 向き × (足の終値 / 入りの値段 − 1) × 1e4 ÷ N)の和。足の始めの状態は 2 本の道で同じなので、
    この和の差が 2 本の道の差になる。等しいときは始値に近い方の端へ先に行く道を両側で使う【置いた形】。
  - どちらの道でも利確が起きない(持ち高 0 から上下両方の入りの値段を越えた足など。仕様に無い組): 始値に近い方の
    端へ先に行く道を良い側・悪い側の両方で使う【置いた形】。
利確の後、その足では入らない(仕様「利確の後にまた入る(2 回目の往復)は数えない」)。
反対の入りで閉じた後: 良い側は同じ脚でその向きに入る、悪い側は入らない(仕様 3-2)。この分かれ目に当たった足も
決まらない足に数える。どの出来事でも閉じた後に同じ足で持った持ち高は、その足では利確と反対の入りでは閉じない
(1 本の足で数える往復は 1 回まで。L-581)【置いた形】。同じ脚の先にあるブレイクでは閉じる(値段の順で決まるため)。
決まらない足は、その足で持っていた取引(その足で閉じた取引と、足の終わりに持っている取引)に 1 ずつ数える。

時刻の決め(【置いた形】)
- 入りの時刻 entry_ns・時計の t0 = 1 段目が約定した足の終わり(カードの _entry_t = 判定の時刻と同じ考え)。
- 20 分の緩め(exit_flg 2)は足の始まりの時刻で判定し、その足の間は変えない。
- 40 分の成行(exit_flg 3)は足の終わりで判定し(ブレイク中は判定しない。v37 1027〜1036 行に時間が無い)、
  次の空でない足の始値で閉じる。出の時刻 = その足の始まり。閉じた後のその足は持ち高 0 から普通に通す。
- そのほかの出の時刻 = 出来事が起きた足の終わり。
- bar_min > 1 のとき「足」は bar_min 分にまとめた足(仕様 2 の定義)。

先読みが無いこと: 足 k+1 の出来事は、足 k までで作った量 _q だけを使う。足 k+1 を窓に入れて量を作り直すのは
足 k+1 の出来事を済ませた後(_bar の 7.)。
"""
from __future__ import annotations

import math
from collections import deque
from typing import Optional

from bot.research.cards.library.c4_owner_matilda_range import BAR_MINS, MIN_WIDTH_RATIO, RANGE_FROMS

# 幅の門の上限: v37 135 行 over_range_setting = 100000(円)を、下限 MIN_WIDTH_RATIO(v37 134 行 150 円)と同じ
# 基準の値段 1,152,502 円(2019-09-04 の終値の中央値。カード 4 の CARD.md)で割った割合(リードの決め)
MAX_WIDTH_RATIO = 100000.0 / 1152502.0

NS = 1_000_000_000
MIN_NS = 60 * NS

# 仕様 5 の表(値の出所は INTENT_MAP §10・§11)
WINDOWS = (10, 20, 40, 80, 160)
ENTRY_V37 = (1, 2, 3, 4, 5)
CENTER_PAIRS = ((2, 0.8), (3, 2), (4, 3), (5, 1), (2, 1))  # v37 140 行のコメント「3:2 …4:3 …5:1 …2:1」と v37 の 2:0.8
EXIT_FORMS = ("v37", "center")
STEP_EXITS = (0.8,)  # v37 157 行 step_exit
STEPS = (1, 2)  # v37 156 行 step_setting = 1 / v52 128 行 entry_step = 2
N_LEVELS = (7, 5, 4, 1)  # v37 118 行 pos_count = 7 / v52 177 行 5 / v52 order_count = 4 / 段なし
ALERTS = (20, 1)  # v37 126 行 alert_count = 20 / v52 152 行 1。成行はその 2 倍(v37 1010・1018 行)
BREAK_DELAYS = (0, 1, 3)  # v37 144〜149 行
ON_BREAKS = ("hold", "close", "follow")
FILL_SIDES = ("good", "bad")

# 終わり方(仕様 4)。"ブレイク" は on_break="close" で同じ向きの持ち高をブレイクで閉じたとき(仕様 4 の一覧に無い)
EXIT_TP1, EXIT_TP2, EXIT_TPC = "利確1", "利確2", "中心型の利確"
EXIT_OPP, EXIT_OPP_BRK, EXIT_BRK = "反対の入り", "反対のブレイク", "ブレイク"
EXIT_TIME, EXIT_END = "時間", "期間の終わり"

_PRIO = {"brk": 0, "tp": 1, "stop": 1, "opp": 2, "ent": 3}


def _in(name, value, table):
    if isinstance(value, bool) or value not in table:
        raise ValueError(f"{name} は {list(table)} のどれか: {value!r}")
    return value


class _Q:
    """足 k が確定したときに作る量(仕様 2)。"""
    __slots__ = ("center", "vola", "width", "close", "hi2", "lo2", "bup", "bdp", "gate", "s1", "b1")


class _St:
    """1 本の足を通すときの状態(2 通りの道を試すので写せるようにする)。"""
    __slots__ = ("side", "fills", "t0", "info", "brk", "brk_done", "tp_done", "no_entry", "exit_block", "r2",
                 "events", "closed")

    def copy(self) -> "_St":
        s = _St()
        s.side, s.fills, s.t0, s.info, s.brk = self.side, list(self.fills), self.t0, self.info, self.brk
        s.brk_done, s.tp_done, s.no_entry, s.exit_block, s.r2 = (self.brk_done, self.tp_done, self.no_entry,
                                                                    self.exit_block, self.r2)
        s.events, s.closed = list(self.events), list(self.closed)
        return s


class MatildaLimitSim:
    """状態を持つ再現。足を 1 本ずつ受け取り、終わった取引の行を返す。モジュールの説明を参照。"""

    def __init__(self, *, fill_side: str, window_min: int = 40, bar_min: int = 1, range_from: str = "body",
                 entry: float = 2, exit_form: str = "v37", exit_setting: Optional[float] = None,
                 step_exit: float = 0.8, step: float = 1, n_levels: int = 7, alert_min: int = 20,
                 width_gate: bool = True, break_delay: int = 1, on_break: str = "hold") -> None:
        self.fill_side = _in("fill_side", fill_side, FILL_SIDES)
        self.window_min = _in("window_min", window_min, WINDOWS)
        self.bar_min = _in("bar_min", bar_min, BAR_MINS)
        self.range_from = _in("range_from", range_from, RANGE_FROMS)
        self.exit_form = _in("exit_form", exit_form, EXIT_FORMS)
        if exit_form == "center":
            if (entry, exit_setting) not in CENTER_PAIRS or isinstance(entry, bool):
                raise ValueError(f"exit_form='center' の (entry, exit_setting) は {list(CENTER_PAIRS)} のどれか: "
                                 f"{(entry, exit_setting)!r}")
        else:
            _in("entry", entry, ENTRY_V37)
            if exit_setting is not None:
                raise ValueError("exit_setting は exit_form='center' のときだけ(v37 の形は step_exit を使う)")
        self.entry = float(entry)
        self.exit_setting = None if exit_setting is None else float(exit_setting)
        self.step_exit = float(_in("step_exit", step_exit, STEP_EXITS))
        self.step = float(_in("step", step, STEPS))
        self.n_levels = _in("n_levels", n_levels, N_LEVELS)
        self.alert_min = _in("alert_min", alert_min, ALERTS)
        if type(width_gate) is not bool:
            raise ValueError(f"width_gate は True / False: {width_gate!r}")
        self.width_gate = width_gate
        self.break_delay = _in("break_delay", break_delay, BREAK_DELAYS)
        self.on_break = _in("on_break", on_break, ON_BREAKS)
        if self.window_min % self.bar_min:
            raise ValueError(f"window_min が bar_min の倍数でない: {window_min!r}, {bar_min!r}")
        self.window_ns = self.window_min * MIN_NS
        self.bar_ns = self.bar_min * MIN_NS
        self.alert_ns = self.alert_min * MIN_NS
        # 窓(W 分)と 2 倍の窓(2W 分)。カードの _bars / _maxq / _minq と同じ書き方
        self._bars: deque = deque()  # (start, top, bot, |body|)
        self._maxq: deque = deque()
        self._minq: deque = deque()
        self._max2: deque = deque()
        self._min2: deque = deque()
        self._body_sum = 0.0
        self._removed = 0
        self._first_start: Optional[int] = None
        self._agg: Optional[list] = None  # [区切りの番号, 始値, 高値, 安値, 終値, 最初の 1 分足の始まり]
        self._q: Optional[_Q] = None  # 足 k までで作った量(足 k+1 の出来事に使う)
        # ブレイクの判定値の更新の履歴(v37 208〜211 行。初めは 9999999 / 0 = 未定 → None)
        self._bups: deque = deque([None] * 3, maxlen=3)
        self._bdps: deque = deque([None] * 3, maxlen=3)
        # 持ち高
        self._side = 0
        self._fills: list = []
        self._t0: Optional[int] = None
        self._info: Optional[dict] = None
        self._brk = 0
        self._pending_time = False
        self._last_close: Optional[float] = None
        self._last_end: Optional[int] = None
        self.undecided_bars = 0  # 決まらない足の数(取引に入らない足を含む全体)

    # ------------------------------------------------------------------ 足の取り込み(カードの _ingest と同じ)
    def feed(self, b) -> list:
        o, h, lo, c = float(b.open), float(b.high), float(b.low), float(b.close)
        if not (b.volume > 0) or not all(math.isfinite(x) for x in (o, h, lo, c)):
            return []  # 仕様 1: 窓に入れない(カードと同じ)
        start = int(b.start_time_ns)
        out: list = []
        if self._first_start is None:
            self._first_start = start
        idx = start // self.bar_ns
        if self._agg is not None and self._agg[0] != idx:
            out += self._close_agg()
        if self._agg is None:
            self._agg = [idx, o, h, lo, c, start]
        else:
            a = self._agg
            a[2], a[3], a[4] = max(a[2], h), min(a[3], lo), c
        if start + MIN_NS >= (idx + 1) * self.bar_ns:  # 区切りの最後の 1 分足が来た
            out += self._close_agg()
        return out

    def finish(self) -> list:
        """期間の終わり: まとめ中の足を閉じ、持っている持ち高を最後の終値で閉じる(終わり方 = 期間の終わり)。"""
        out = self._close_agg() if self._agg is not None else []
        if self._side != 0:
            st = self._state()
            self._close(st, self._last_close, EXIT_END, self._last_end)
            out += self._rows(st, undecided=False)
            self._load(st)
        return out

    def _close_agg(self) -> list:
        idx, o, h, lo, c, first = self._agg
        self._agg = None
        start = idx * self.bar_ns
        return self._bar(start, start + self.bar_ns, first, o, h, lo, c)

    # ------------------------------------------------------------------ 仕様 2: 量
    def _push(self, start: int, o: float, h: float, lo: float, c: float) -> None:
        if self.range_from == "body":
            top, bot = max(o, c), min(o, c)
        else:
            top, bot = h, lo
        body = abs(c - o)
        self._bars.append((start, top, bot, body))
        self._body_sum += body
        for q, v, keep in ((self._maxq, top, 1), (self._max2, top, 1), (self._minq, bot, -1), (self._min2, bot, -1)):
            while q and (q[-1][1] <= v if keep == 1 else q[-1][1] >= v):
                q.pop()
            q.append((start, v))

    def _trim(self, lo_start: int, lo2_start: int) -> None:
        while self._bars and self._bars[0][0] < lo_start:
            self._body_sum -= self._bars.popleft()[3]
            self._removed += 1
        for q, lim in ((self._maxq, lo_start), (self._minq, lo_start), (self._max2, lo2_start),
                       (self._min2, lo2_start)):
            while q and q[0][0] < lim:
                q.popleft()
        if self._removed > max(len(self._bars), 1):  # カードと同じ: 引き算の誤差をためない
            self._body_sum = math.fsum(x[3] for x in self._bars)
            self._removed = 0

    def _make_q(self, t: int, close: float) -> Optional[_Q]:
        lo_start = t - self.window_ns
        self._trim(lo_start, t - 2 * self.window_ns)
        if self._first_start is None or self._first_start > lo_start or not self._bars:
            return None  # 窓が満ちるまで(カードと同じ)。2 倍の窓は満ちるのを待たない(gate_diag と同じ)
        q = _Q()
        hi, lo = self._maxq[0][1], self._minq[0][1]
        q.width = hi - lo
        q.center = (hi + lo) / 2.0
        q.vola = self._body_sum / len(self._bars)
        q.close = close
        q.hi2, q.lo2 = self._max2[0][1], self._min2[0][1]
        # v37 976・993 行: range_width < range_setting or range_width > over_range_setting なら入らない
        q.gate = (not self.width_gate) or MIN_WIDTH_RATIO <= q.width / close <= MAX_WIDTH_RATIO
        q.s1 = q.center + self.entry * q.vola
        q.b1 = q.center - self.entry * q.vola
        # ブレイクの判定値の更新(v37 504〜509 行。足 k の確定で、今の brk を使う)
        if hi != q.hi2 or self._brk != 0:
            self._bups.append(hi + q.width / 2)
        if lo != q.lo2 or self._brk != 0:
            self._bdps.append(lo - q.width / 2)
        d = self.break_delay
        q.bup = self._bups[-d] if d else None  # break_delay = 0 はブレイクしない(v37 147 行)
        q.bdp = self._bdps[-d] if d else None
        return q

    # ------------------------------------------------------------------ 状態の出し入れ
    def _state(self) -> _St:
        s = _St()
        s.side, s.fills, s.t0, s.info, s.brk = self._side, list(self._fills), self._t0, self._info, self._brk
        s.brk_done = s.tp_done = s.no_entry = s.exit_block = s.r2 = False
        s.events, s.closed = [], []
        return s

    def _load(self, st: _St) -> None:
        self._side, self._fills, self._t0, self._info, self._brk = st.side, st.fills, st.t0, st.info, st.brk

    # ------------------------------------------------------------------ 持ち高の操作
    def _open(self, st: _St, side: int, price: float, q: _Q, t_end: int) -> None:
        """持ち高 0 から 1 段目。時計 t0 はここで始める(向きが変わったとき。段を足しても戻さない)。"""
        st.side, st.fills, st.t0 = side, [price], t_end
        ratio = q.width / q.vola if q.vola > 0 else (math.inf if q.width > 0 else 0.0)
        st.info = {"entry_ns": t_end, "side": side, "width": q.width, "vola": q.vola, "ratio": ratio,
                   "brk": st.brk, "close_k": q.close}

    def _close(self, st: _St, price: float, reason: str, t: int) -> None:
        st.closed.append((st.info, list(st.fills), price, reason, t))
        st.side, st.fills, st.t0, st.info = 0, [], None, None
        st.exit_block = True  # 閉じた後に同じ足で持った持ち高は、その足では利確・反対の入りで閉じない(L-581)

    def _rows(self, st: _St, undecided: bool) -> list:
        out = []
        for info, fills, px, reason, t in st.closed:
            if undecided:
                info["und"] = info.get("und", 0) + 1
            out.append(self._close_row(info, fills, px, reason, t))
        if undecided and st.info is not None:
            st.info["und"] = st.info.get("und", 0) + 1
        return out

    def _close_row(self, info: dict, fills: list, px: float, reason: str, t: int) -> dict:
        """仕様 4: 1 段の損益(bp)= 向き × (出の値段 / 入りの値段 − 1) × 1e4 ÷ N。取引の損益 = 段の和。"""
        s = info["side"]
        pnl = math.fsum(s * (px / f - 1.0) * 1e4 / self.n_levels for f in fills)
        return {"entry_ns": info["entry_ns"], "exit_ns": t, "side": s, "levels": len(fills),
                "entry_price": math.fsum(fills) / len(fills), "exit_price": px, "exit_reason": reason,
                "pnl_bp": pnl, "undecided": info.get("und", 0), "width": info["width"], "vola": info["vola"],
                "ratio": info["ratio"], "brk": info["brk"], "close_k": info["close_k"]}

    # ------------------------------------------------------------------ 仕様 3-3: 利確の値段
    def _tp(self, st: _St, q: _Q, t_start: int):
        """(利確の値段, 終わり方)。"""
        s = st.side
        if self.exit_form == "center":  # v37 138〜139 行のコメントの定義。flg 1・2 の代わり(ブレイク中も)
            return q.center - s * self.exit_setting * q.vola, EXIT_TPC
        e = math.fsum(st.fills) / len(st.fills)
        ev = self.step_exit * q.vola / len(st.fills)  # v37 881 行 vola × step_exit × (sizemin / mybtc)
        line = e + s * ev
        if st.brk == 0 and (t_start - st.t0 >= self.alert_ns or s * (e - q.center) > 0):
            # exit_flg 2(v37 1012〜1014・1020〜1022 行、897〜898・911〜912 行)
            return (min(q.center, line) if s == 1 else max(q.center, line)), EXIT_TP2
        return line, EXIT_TP1  # exit_flg 1(ブレイク中は v37 1029〜1030 行 b_signal == 0 → 1。仕様は 1033 行と書く)

    def _next_level(self, st: _St, d: int, q: _Q) -> float:
        """d の向きの次の段の値段(仕様 3-2)。売り: max(S1, 前の段 + step × vola)、買い: min(B1, 前の段 − step × vola)。"""
        if d == -1:
            return q.s1 if not st.fills else max(q.s1, st.fills[-1] + self.step * q.vola)
        return q.b1 if not st.fills else min(q.b1, st.fills[-1] - self.step * q.vola)

    # ------------------------------------------------------------------ 1 本の脚
    def _leg(self, st: _St, up: bool, ext: float, q: _Q, ev: int, pb: Optional[float], tp_stop: bool,
             t_start: int, t_end: int) -> None:
        d = 1 if up else -1  # この脚で利確する持ち高の向き(上りは買いの利確・売りの入り)
        stopped = False  # 利確の手前で止めた後は、この脚の先のブレイクの判定値だけを見る
        while True:
            cands = []

            def add(thr, kind):
                if thr is not None and (ext > thr if up else ext < thr):
                    cands.append(((thr if up else -thr), _PRIO[kind], kind, thr))

            if ev == d and not st.brk_done:
                add(pb, "brk")
            s = st.side
            if stopped:
                if not cands:
                    return
                st.events.append(("brk", pb))
                st.brk, st.brk_done = ev, True  # ブレイクの状態だけ変える(持ち高は閉じない)
                continue
            if s == d and not st.exit_block:
                tp, why = self._tp(st, q, t_start)
                add(tp, "stop" if tp_stop else "tp")
                if st.brk == 0 and q.gate and q.vola > 0:  # 反対の入り(幅の門を通るときだけ。v37 976・993 行)
                    add(q.s1 if d == 1 else q.b1, "opp")
            e = -d  # この脚で入る向き
            if not st.tp_done and not st.no_entry and q.vola > 0 and len(st.fills) < self.n_levels:
                if s == 0 and st.brk == 0 and q.gate:
                    add(self._next_level(st, e, q), "ent")
                elif s == e and ((st.brk == 0 and q.gate) or st.brk == e):
                    add(self._next_level(st, e, q), "ent")
            if not cands:
                return
            _, _, kind, px = min(cands)
            st.events.append((kind, px))
            if kind == "stop":
                stopped = True
                continue
            if kind == "brk":
                st.brk, st.brk_done = ev, True
                if st.side == -ev or (st.side == ev and self.on_break == "close"):
                    self._close(st, px, EXIT_OPP_BRK if st.side == -ev else EXIT_BRK, t_end)
                if st.side == 0 and self.on_break == "follow" and not st.tp_done:
                    self._open(st, ev, px, q, t_end)  # 判定値の値段で 1 段
            elif kind == "tp":
                self._close(st, px, why, t_end)
                st.tp_done = True  # 利確の後、この足では入らない
            elif kind == "opp":
                self._close(st, px, EXIT_OPP, t_end)
                st.r2 = True  # 閉じた後に同じ足でその向きに入るかは決まらない(仕様 3-2)
                if self.fill_side == "bad":
                    st.no_entry = True
            else:  # "ent"
                if st.side == 0:
                    self._open(st, e, px, q, t_end)
                else:
                    st.fills.append(px)

    def _path_value(self, st: _St, c: float) -> float:
        """道の損益(bp): その足で閉じた取引の損益と、足の終わりの持ち高の含み(足の終値で評価)の和。"""
        v = math.fsum(info["side"] * (px / f - 1.0) * 1e4 / self.n_levels
                      for info, fills, px, _r, _t in st.closed for f in fills)
        return v + math.fsum(st.side * (c / f - 1.0) * 1e4 / self.n_levels for f in st.fills)

    def _run_path(self, st0: _St, up_first: bool, bar, q, ev, pb, tp_stop) -> _St:
        st = st0.copy()
        o, h, lo, t_start, t_end = bar
        # 足の頭: 始値 O の時点で既に越えている指値(上りは thr < O、下りは thr > O)。2 通りの道で同じ。
        # 利確の手前で止める(tp_stop)は頭には掛けない(頭の利確は決まっている)。上りの頭 → 下りの頭の順【置いた形】
        for up in (True, False):
            self._leg(st, up, o, q, ev, pb, False, t_start, t_end)
        for up in ((True, False) if up_first else (False, True)):
            self._leg(st, up, h if up else lo, q, ev, pb, tp_stop, t_start, t_end)
        return st

    # ------------------------------------------------------------------ 1 本の足
    def _bar(self, start: int, t_end: int, first_start: int, o, h, lo, c) -> list:
        q = self._q
        out: list = []
        if q is not None:
            st = self._state()
            # 0. 時間の成行(前の足の終わりで決めた): この足の始値で閉じる
            if self._pending_time and st.side != 0:
                self._close(st, o, EXIT_TIME, first_start)
                st.exit_block = False  # 足の前に済んだもの。この足は持ち高 0 から普通に通す
                out += self._rows(st, undecided=False)
                st.closed = []
            self._pending_time = False
            # 1. ブレイク(仕様 3-1。上を先に見る。足 k の判定値と 2 倍の窓の端)
            ev, pb = 0, None
            if q.bup is not None and max(q.bup, q.hi2) < h and st.brk != 1:
                ev, pb = 1, max(q.bup, q.hi2)
            elif q.bdp is not None and min(q.bdp, q.lo2) > lo and st.brk != -1:
                ev, pb = -1, min(q.bdp, q.lo2)
            # 2. 何も起きない足は道を試さない
            can_enter = st.brk == 0 and q.gate and q.vola > 0 and (h > q.s1 or lo < q.b1)
            if st.side == 0 and not can_enter and (ev == 0 or self.on_break != "follow"):
                if ev:
                    st.brk = ev
            else:
                bar = (o, h, lo, start, t_end)
                near_up = (h - o) <= (o - lo)  # 始値に近い方の端へ先に行く道
                a = self._run_path(st, True, bar, q, ev, pb, False)
                b = self._run_path(st, False, bar, q, ev, pb, False)
                if a.events == b.events and (a.side, a.fills, a.brk) == (b.side, b.fills, b.brk):
                    st, und = a, a.r2
                else:
                    # 3. 決まらない足(仕様 3-5)
                    und = True
                    ta = any(x[0] == "tp" for x in a.events)
                    tb = any(x[0] == "tp" for x in b.events)
                    if ta and tb:  # 両方の道で利確: 損益の良い方 / 悪い方(どちらも止めない)
                        va, vb = self._path_value(a, c), self._path_value(b, c)
                        if va == vb:
                            st = a if near_up else b
                        else:
                            better, worse = (a, b) if va > vb else (b, a)
                            st = better if self.fill_side == "good" else worse
                    elif ta or tb:  # 片方の道でだけ利確: 良い側 = その道、悪い側 = もう一方を利確の手前で止める
                        # 悪い側は利確の無い方の道(a に利確があれば下が先の道 b)
                        st = (a if ta else b) if self.fill_side == "good" else self._run_path(st, tb, bar, q, ev, pb,
                                                                                              True)
                    else:
                        st = a if near_up else b
                if und:
                    self.undecided_bars += 1
                out += self._rows(st, undecided=und)
            # 5. 時間の成行の判定(足の終わり。ブレイク中は判定しない)
            if st.side != 0 and st.brk == 0 and t_end - st.t0 >= 2 * self.alert_ns:
                self._pending_time = True
            # 6. ブレイクが解ける(足の終わりの終値と足 k の中心)
            if st.brk == 1 and c < q.center or st.brk == -1 and c > q.center:
                st.brk = 0
            self._load(st)
        # 7. 足 k+1 を窓に入れて量を作り直す(ブレイクの判定値は解けた後の brk で更新)
        self._push(start, o, h, lo, c)
        self._q = self._make_q(t_end, c)
        self._last_close, self._last_end = c, t_end
        return out


__all__ = ["ALERTS", "BREAK_DELAYS", "CENTER_PAIRS", "ENTRY_V37", "EXIT_FORMS", "FILL_SIDES", "MAX_WIDTH_RATIO", "MatildaLimitSim",
           "N_LEVELS", "ON_BREAKS", "STEPS", "STEP_EXITS", "WINDOWS"]

"""カード 4: オーナー由来 O-1「レンジ中心回帰(マチルダの戦略ロジック)」+ O-2「レンジ性の判定器(vr)」。

説明と原文: docs/RESEARCH/cards/c4_owner_matilda_range/CARD.md
意図の地図: docs/RESEARCH/cards/c4_owner_matilda_range/INTENT_MAP.md(印と行の対応はそこに書く)

何をするか
----------
bitFlyer FX_BTC_JPY の 1 分足の終わり t ごとに呼ばれ、持ち高 −1 / 0 / +1 を返す。参照の系列は使わない
(足は `view.bars` だけで読む。核が t より後の足を読ませない)。

窓(既定 40 分。O-1「直近40分ほど」、原典 v37 124-125 行)= 始まりが t − 窓 以上の 1 分足。足の本数ではなく
時刻で切る(約定 0 の分が抜けても 40 分は 40 分)。窓の中で毎分:
  上端 hi・下端 lo: 既定は実体の端(max(始値, 終値) / min(始値, 終値))。原典 v37 458-478 行はヒゲが
    beard_ignore = 1 円(151 行)を超えると高値・安値を実体の端に置き換える = ほぼ全部のヒゲを捨てる。
    変種 range_from="wick" は高値・安値。
  幅 width = hi − lo、中心 center = (hi + lo) / 2(原典 499-500 行)。
  ボラ vola = 窓の中の足の |終値 − 始値| の平均(原典 488-489 行。原典の「39 本の和 ÷ 40」は直した。INTENT_MAP §4)。
  比 range_body_ratio = width / vola(O-2 の「vr = レンジ幅 ÷ 平均実体」。原典 v52 1113 行。W1 の場面の変数の
    「vr」(分散比)とは別の量なので、名前を変えた)。

状態と持ち高(足の終わり t の終値 close で判定する):
  1. 一方向の動きの状態(vr_max が None でないときだけ):
     比 >= vr_max なら trend = sign(close − center)(0 なら前のまま)。
     比 < vr_max で、trend の向きの側から close が中心に戻った(上向きなら close <= center、下向きなら
     close >= center)なら trend = 0(O-1「価格が新しいレンジの中心へ戻ってきた時点で…再開」)。
  2. trend != 0 の間: on_trend="flat" なら持ち高 0(静観)、"follow" なら持ち高 = trend(逆転順張り)。
     trend が 0 に戻った足では、まず持ち高を 0 にしてから 3 を当てる。
  3. trend == 0(レンジ):
     建ててよい = (min_width_jpy が None)または width >= min_width_jpy(原典 976・993 行)。
     入りの合図: close > center + ENTRY_K × vola なら売り(−1)、close < center − ENTRY_K × vola なら買い(+1)
       (原典 978-981・995-998 行)。
     持ち高 0: 建ててよく合図があれば合図の向きに建てる。
     持ち高あり: 建ててよく反対の合図なら反対へ(原典 1010・1018 行の exit_flg = 3 のあと反対の入り)。
       そうでなく close が中心に届いた(買いなら close >= center、売りなら close <= center)なら 0(利確)。
       そうでなく建ててから HOLD_MAX_MIN 分たったなら 0(時間成行。原典 1010・1018 行 alert_count × 2)。

窓が満ちるまで(最初に見た足の始まり + 窓 > t − 窓 の間)は 0 を返し、状態も動かさない。
出来高 0 の足と、値段が有限でない足は窓に入れない(値段の情報が無い)。
"""
from __future__ import annotations

import math
from collections import deque
from typing import Optional

from bot.research.cards.card import CardError, CardView

NS = 1_000_000_000
MIN_NS = 60 * NS
WINDOW_MIN = 40  # O-1「直近40分ほど」/ 原典 v37 124 行 vola_count = 40・125 行 range_count = 40
WINDOWS = (40, 60, 1440, 10080)  # 40 = 原文。60・1440・10080 = W1 の仕様 C4 の 1 時間・1 日・1 週(変種)
ENTRY_K = 2.0  # 原典 v37 141 行 entry_setting = 2、v52 128・130 行(inner・outer とも 2)
ALERT_MIN = 20  # 原典 v37 126 行 alert_count = 20(分)
HOLD_MAX_MIN = 2 * ALERT_MIN  # 原典 v37 1010・1018 行 alert_count * 2 で成行の決済
VR_MAXES = (None, 10.0, 100.0)  # None = 門なし / 10 = v52 125 行のコメントの例 / 100 = v52 129 行の出荷値
VR_MAX = 10.0
MIN_WIDTHS = (None, 150.0)  # 150 = 原典 v37 134 行 range_setting(円)/ None = 門なし
MIN_WIDTH_JPY = 150.0
RANGE_FROMS = ("body", "wick")
ON_TRENDS = ("flat", "follow")


class C4OwnerMatildaRange:
    """カードの口(bot.research.cards.Card)。モジュールの説明を参照。"""

    name = "c4_owner_matilda_range"
    requires: tuple = ()

    def __init__(self, *, window_min: int = WINDOW_MIN, vr_max: Optional[float] = VR_MAX,
                 min_width_jpy: Optional[float] = MIN_WIDTH_JPY, range_from: str = "body",
                 on_trend: str = "flat") -> None:
        if type(window_min) is not int or window_min not in WINDOWS:
            raise CardError(f"{self.name}: window_min は {list(WINDOWS)} のどれか: {window_min!r}")
        if vr_max not in VR_MAXES:
            raise CardError(f"{self.name}: vr_max は {list(VR_MAXES)} のどれか: {vr_max!r}")
        if min_width_jpy not in MIN_WIDTHS:
            raise CardError(f"{self.name}: min_width_jpy は {list(MIN_WIDTHS)} のどれか: {min_width_jpy!r}")
        if range_from not in RANGE_FROMS:
            raise CardError(f"{self.name}: range_from は {list(RANGE_FROMS)} のどれか: {range_from!r}")
        if on_trend not in ON_TRENDS:
            raise CardError(f"{self.name}: on_trend は {list(ON_TRENDS)} のどれか: {on_trend!r}")
        self.window_min = window_min
        self.window_ns = window_min * MIN_NS
        self.vr_max = vr_max
        self.min_width_jpy = min_width_jpy
        self.range_from = range_from
        self.on_trend = on_trend
        self._bars: deque = deque()  # (start, hi, lo, |body|) 窓の中の足、古い順
        self._maxq: deque = deque()  # (start, hi) hi が減っていく並び(窓の最大)
        self._minq: deque = deque()  # (start, lo) lo が増えていく並び(窓の最小)
        self._body_sum = 0.0
        self._removed = 0  # 和を作り直してから窓から出た足の数
        self._last_end: Optional[int] = None  # 取り込んだ最後の足の終わり
        self._first_start: Optional[int] = None  # 最初に取り込んだ足の始まり
        self._close: Optional[float] = None
        self._pos = 0
        self._entry_t: Optional[int] = None  # 今の持ち高を作った足の終わり
        self._trend = 0

    # 足の取り込み(呼ばれなかった間の足も古い順に全部取り込む)
    def _new_bars(self, view: CardView) -> list:
        n = 16
        while True:
            bs = view.bars(n)
            if len(bs) < n or (self._last_end is not None and bs[0].received_time_ns <= self._last_end):
                break
            n *= 2
        return [b for b in bs if self._last_end is None or b.received_time_ns > self._last_end]

    def _push(self, b) -> None:
        self._last_end = b.received_time_ns
        o, h, lo, c = float(b.open), float(b.high), float(b.low), float(b.close)
        if not (b.volume > 0) or not all(math.isfinite(x) for x in (o, h, lo, c)):
            return
        start = int(b.start_time_ns)
        if self._first_start is None:
            self._first_start = start
        if self.range_from == "body":
            top, bot = max(o, c), min(o, c)
        else:
            top, bot = h, lo
        body = abs(c - o)
        self._bars.append((start, top, bot, body))
        self._body_sum += body
        while self._maxq and self._maxq[-1][1] <= top:
            self._maxq.pop()
        self._maxq.append((start, top))
        while self._minq and self._minq[-1][1] >= bot:
            self._minq.pop()
        self._minq.append((start, bot))
        self._close = c

    def _trim(self, lo_start: int) -> None:
        while self._bars and self._bars[0][0] < lo_start:
            self._body_sum -= self._bars.popleft()[3]
            self._removed += 1
        while self._maxq and self._maxq[0][0] < lo_start:
            self._maxq.popleft()
        while self._minq and self._minq[0][0] < lo_start:
            self._minq.popleft()
        if self._removed > max(len(self._bars), 1):  # 引き算の誤差をためない(作り直しは均して O(1))
            self._body_sum = math.fsum(x[3] for x in self._bars)
            self._removed = 0

    def _set(self, pos: int, t: int) -> None:
        if pos != self._pos:
            self._pos = pos
            self._entry_t = t if pos != 0 else None

    def exposure(self, view: CardView) -> float:
        t = view.now_ns
        for b in self._new_bars(view):
            self._push(b)
        lo_start = t - self.window_ns
        self._trim(lo_start)
        if self._first_start is None or self._first_start > lo_start or not self._bars:
            return float(self._pos)  # 窓が満ちるまで(持ち高は 0 のまま)
        hi, lo = self._maxq[0][1], self._minq[0][1]
        width = hi - lo
        center = (hi + lo) / 2.0
        vola = self._body_sum / len(self._bars)
        close = self._close
        if vola > 0:
            ratio = width / vola
        else:
            ratio = math.inf if width > 0 else 0.0

        # 1. 一方向の動きの状態(O-2 の門)
        was_trend = self._trend
        if self.vr_max is not None:
            if ratio >= self.vr_max:
                d = (close > center) - (close < center)
                if d != 0:
                    self._trend = d
            elif self._trend == 1 and close <= center or self._trend == -1 and close >= center:
                self._trend = 0
        # 2. 一方向の動きの間
        if self._trend != 0:
            self._set(0 if self.on_trend == "flat" else self._trend, t)
            return float(self._pos)
        if was_trend != 0:
            self._set(0, t)
        # 3. レンジ
        allowed = self.min_width_jpy is None or width >= self.min_width_jpy
        sig = 0
        if close > center + ENTRY_K * vola:
            sig = -1
        elif close < center - ENTRY_K * vola:
            sig = 1
        pos = self._pos
        if pos == 0:
            if allowed and sig != 0:
                self._set(sig, t)
        elif allowed and sig == -pos:
            self._set(sig, t)
        elif (pos == 1 and close >= center) or (pos == -1 and close <= center):
            self._set(0, t)
        elif t - self._entry_t >= HOLD_MAX_MIN * MIN_NS:
            self._set(0, t)
        return float(self._pos)


__all__ = ["ALERT_MIN", "C4OwnerMatildaRange", "ENTRY_K", "HOLD_MAX_MIN", "MIN_WIDTHS", "MIN_WIDTH_JPY", "ON_TRENDS",
           "RANGE_FROMS", "VR_MAX", "VR_MAXES", "WINDOWS", "WINDOW_MIN"]

"""カード 2: オーナー由来 O-6「シグナルは外、執行は自市場」+ O-3 カツオのヒゲ(W4 の仕様 §1 の 2)。

説明と原文: docs/RESEARCH/cards/c2_owner_xvenue_wick/CARD.md
意図の地図: docs/RESEARCH/cards/c2_owner_xvenue_wick/INTENT_MAP.md(印と行の対応はそこに書く)

何をするか
----------
bitFlyer FX_BTC_JPY の 1 分足の終わり t ごとに呼ばれ、持ち高 −1 / 0 / +1 を返す。
シグナルは bitFlyer の足からは作らない。海外の取引所の 1 分足 4 本値を参照の系列として受け取り、
UTC の時計にそろえた足(既定 15 分。:00 / :15 / :30 / :45 区切り)にまとめて、そのヒゲで判定する。
判定は足が閉じた後(足の終わり <= t)にだけ行う。

変種(リードの読み、差し戻し 1 回目):
  シグナル源 `series`(4 本値の系列の名前の組): SERIES_SPOT = Binance BTCUSDT 現物(既定)/
    SERIES_UM = Binance USD-M BTCUSDT 先物 / SERIES_BITMEX = BitMEX XBTUSD(1 秒足から作った 1 分足)。
  足の長さ `foot_min`: FOOTS = {1, 3, 5, 15, 30, 60} 分(既定 15 = 原典。ほかの 5 つは L-049 の記録 (9) の
    リードの選択した水準)。区切りは UTC の時計(60 分は毎時 0 分)。これ以外の値は拒む。

足 1 本の判定(原典 katsuo_v03.py 197-268 行の get_candle と、L-052 / L-053 の門):
  実体 body = close - open。陽線(body > 0): 上ヒゲ = high - close、下ヒゲ = open - low。
  陰線(body < 0): 上ヒゲ = high - open、下ヒゲ = close - low。同値足(body = 0)は何もしない。
  向き: 上ヒゲ > 下ヒゲ なら売り(-1)、下ヒゲ > 上ヒゲ なら買い(+1)、等しければシグナル無し。
  長い方のヒゲ w(bp = w / その足の始値 × 10,000)が
      (w_bp >= small_gate_bp かつ w > |body|) または (w_bp >= big_gate_bp)
  のときシグナル。シグナルが出たら無効化ライン line = そのヒゲの先端(売りなら high、買いなら low)。

持ち高の更新(原典 490-535 行の 4 通りの分岐と同値足。バグ A・B は意図どおりに直した形):
  陽線 × 売りシグナル(上ヒゲ陽線 = 弱い売り): 買い持ちなら 0(決済で止める)、それ以外は -1
  陽線 × 買いシグナル(下ヒゲ陽線 = 強い買い): +1(売り持ちならドテン)
  陽線 × シグナル無し: 売り持ちで close >= line なら 0(ヒゲ先端を終値で超えた)
  陰線 × 買いシグナル(下ヒゲ陰線 = 弱い買い): 売り持ちなら 0、それ以外は +1
  陰線 × 売りシグナル(上ヒゲ陰線 = 強い売り): -1(買い持ちならドテン)
  陰線 × シグナル無し: 買い持ちで close <= line なら 0
  同値足: 何もしない(無効化も見ない)

参照の系列の時刻: 行の時刻は 1 分足の始まり(Binance の `open_time`。ほかの変種も同じ形にそろえて渡す)。その分の高値・安値・終値は
分の終わりまで決まらないので、遅れ ROW_LAG_NS = 60 秒を宣言する(使えるようになる時刻 = 分の終わり)。
カードは行の終わりを「行の時刻 + 宣言した遅れ」で計算する(宣言と計算がずれないように)。

足の届かない分(bitFlyer の空の足・保守の時間)にはカードは呼ばれない。呼ばれたときに、
まだ判定していない足のうち終わりが t 以下のものを、古い順に全部判定する。

診断(検定の数に入れない): シグナルが出るたびに `signal_log` に (足の終わり ns, 向き, 19 の枝に当たったか,
24 の枝に当たったか) を足す。19 の枝だけ / 24 の枝だけで出たシグナルを分けて数えるため(L-053)。
"""
from __future__ import annotations

from typing import Optional

from bot.research.cards.card import CardError, CardView, SeriesSpec

NS = 1_000_000_000
ROW_LAG_NS = 60 * NS  # Binance の 1 分足は open_time で刻まれ、分の終わりに使える
FOOT_MIN = 15  # 原典 katsuo_v03.py 13 行「とりあえず15分足で」・36 行 foot = 15、109 行 minute % 15 == 0
FOOT_NS = FOOT_MIN * 60 * NS
FOOTS = (1, 3, 5, 15, 30, 60)  # 足の長さの変種。15 以外は L-049 の記録 (9) のリードの選択(導出ではない)
SMALL_GATE_BP = 19.0  # L-052「19 以上」(原典 38 行 beardline = 19、当時はドル)。bp 建ては L-052 の承認
BIG_GATE_BP = 24.0  # L-053「24 … 実足の長さに関わらずそれ単体で長いヒゲ」(原典 39 行 bigbeardline = 24)

SERIES_SPOT = ("binance_open", "binance_high", "binance_low", "binance_close")  # (a) Binance 現物
SERIES_UM = ("binance_um_open", "binance_um_high", "binance_um_low", "binance_um_close")  # (b) Binance USD-M 先物
SERIES_BITMEX = ("bitmex_open", "bitmex_high", "bitmex_low", "bitmex_close")  # (c) BitMEX XBTUSD
SERIES = SERIES_SPOT


def classify_detail(o: float, h: float, lo: float, c: float, *, small_gate_bp: float = SMALL_GATE_BP,
                    big_gate_bp: float = BIG_GATE_BP) -> tuple[int, int, Optional[float], bool, bool]:
    """(足の色, シグナル, ヒゲの先端, 19 の枝に当たった, 24 の枝に当たった)。色は +1 陽線 / -1 陰線 / 0 同値足、
    シグナルは +1 買い / -1 売り / 0 無し。先端はシグナルがあるときだけ(売りなら高値、買いなら安値)。"""
    body = c - o
    if body > 0:
        color, top, under = 1, h - c, o - lo
    elif body < 0:
        color, top, under = -1, h - o, c - lo
    else:
        return 0, 0, None, False, False
    if top > under:
        w, side, tip = top, -1, h
    elif under > top:
        w, side, tip = under, 1, lo
    else:
        return color, 0, None, False, False
    w_bp = w * 1e4 / o
    small = w_bp >= small_gate_bp and w > abs(body)
    big = w_bp >= big_gate_bp
    if small or big:
        return color, side, tip, small, big
    return color, 0, None, False, False


def classify(o: float, h: float, lo: float, c: float, *, small_gate_bp: float = SMALL_GATE_BP,
             big_gate_bp: float = BIG_GATE_BP) -> tuple[int, int, Optional[float]]:
    """(足の色, シグナル, ヒゲの先端)。`classify_detail` の前の 3 つ。"""
    return classify_detail(o, h, lo, c, small_gate_bp=small_gate_bp, big_gate_bp=big_gate_bp)[:3]


class C2OwnerXvenueWick:
    """カードの口(bot.research.cards.Card)。モジュールの説明を参照。"""

    name = "c2_owner_xvenue_wick"

    def __init__(self, *, series: tuple = SERIES_SPOT, foot_min: int = FOOT_MIN,
                 small_gate_bp: float = SMALL_GATE_BP, big_gate_bp: float = BIG_GATE_BP) -> None:
        if type(foot_min) is not int or foot_min not in FOOTS:
            raise CardError(f"{self.name}: foot_min は {list(FOOTS)} のどれか: {foot_min!r}")
        series = tuple(series)
        if len(series) != 4 or len(set(series)) != 4 or not all(type(n) is str and n for n in series):
            raise CardError(f"{self.name}: series は始値・高値・安値・終値の 4 つの別々の名前: {series!r}")
        self.series = series
        self.foot_min = foot_min
        self.foot_ns = foot_min * 60 * NS
        self.small_gate_bp = float(small_gate_bp)
        self.big_gate_bp = float(big_gate_bp)
        self.requires = tuple(SeriesSpec(n, ROW_LAG_NS) for n in series)
        self.signal_log: list = []  # 診断: (足の終わり ns, 向き, 19 の枝, 24 の枝)。検定の数に入れない
        self._pos = 0
        self._line: Optional[float] = None  # 直近のシグナル足のヒゲ先端(原典の lcprice)
        self._next_row = 0  # まだ読んでいない参照の行の位置
        self._bucket: Optional[int] = None  # まとめ中の足の始まり(ns)
        self._agg: Optional[list] = None  # [open, high, low, close]

    # 足 1 本を判定して持ち高を更新する
    def _apply(self, end_ns: int, o: float, h: float, lo: float, c: float) -> None:
        color, sig, tip, small, big = classify_detail(o, h, lo, c, small_gate_bp=self.small_gate_bp,
                                                      big_gate_bp=self.big_gate_bp)
        if color == 0:
            return
        if sig != 0:
            self._line = tip
            self.signal_log.append((end_ns, sig, small, big))
        pos = self._pos
        if color == 1:
            if sig == -1:
                self._pos = 0 if pos > 0 else -1
            elif sig == 1:
                self._pos = 1
            elif pos < 0 and not (c < self._line):
                self._pos = 0
        else:
            if sig == 1:
                self._pos = 0 if pos < 0 else 1
            elif sig == -1:
                self._pos = -1
            elif pos > 0 and not (c > self._line):
                self._pos = 0

    def _close_bucket(self) -> None:
        o, h, lo, c = self._agg
        end = self._bucket + self.foot_ns
        self._bucket, self._agg = None, None
        self._apply(end, o, h, lo, c)

    def exposure(self, view: CardView) -> float:
        t = view.now_ns
        rows = [view.ref(n) for n in self.series]
        n = len(rows[0])
        if any(len(r) != n for r in rows):
            raise CardError(f"{self.name}: 4 本値の参照の行の数が揃わない {[len(r) for r in rows]}")
        lag = self.requires[0].lag_ns
        for k in range(self._next_row, n):
            vals = [r[k] for r in rows]
            rt = vals[0][0]
            if any(v[0] != rt for v in vals):
                raise CardError(f"{self.name}: 4 本値の参照の行の時刻が揃わない {[v[0] for v in vals]}")
            o, h, lo, c = (float(v[1]) for v in vals)
            end = rt + lag  # この 1 分足の終わり
            b = (end - 1) // self.foot_ns * self.foot_ns  # この 1 分足が入る足の始まり(UTC の時計の区切り)
            if self._bucket is not None and b != self._bucket:
                self._close_bucket()
            if self._bucket is None:
                self._bucket, self._agg = b, [o, h, lo, c]
            else:
                a = self._agg
                a[1], a[2], a[3] = max(a[1], h), min(a[2], lo), c
        self._next_row = n
        if self._bucket is not None and self._bucket + self.foot_ns <= t:
            self._close_bucket()
        return float(self._pos)


__all__ = ["BIG_GATE_BP", "C2OwnerXvenueWick", "FOOTS", "FOOT_MIN", "FOOT_NS", "ROW_LAG_NS", "SERIES", "SERIES_BITMEX",
           "SERIES_SPOT", "SERIES_UM", "SMALL_GATE_BP", "classify", "classify_detail"]

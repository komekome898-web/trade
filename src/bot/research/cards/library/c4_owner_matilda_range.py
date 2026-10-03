"""カード 4: オーナー由来 O-1「レンジ中心回帰グリッド(マチルダの戦略ロジック)」+ O-2「レンジ性の判定器(vr)」。

説明と原文: docs/RESEARCH/cards/c4_owner_matilda_range/CARD.md
意図の地図: docs/RESEARCH/cards/c4_owner_matilda_range/INTENT_MAP.md(印と行の対応はそこに書く。オーナーの答えは §8、L-564)

何をするか
----------
bitFlyer FX_BTC_JPY の 1 分足の終わり t ごとに呼ばれ、持ち高を [−1, +1] で返す。参照の系列は使わない
(足は `view.bars` だけで読む。核が t より後の足を読ませない)。

足の長さ bar_min(既定 1 分。原典 v37 122 行 foot = 1): 1 分足を UTC の 0 時から数えた bar_min 分ごとの区切りに
まとめ(始値 = 最初の足の始値、終値 = 最後の足の終値、高値・安値 = 最大・最小)、区切りの終わりで判定する。
区切りの終わりの 1 分足が無い(約定 0)ときは、次に呼ばれた時に、終わった区切りを古い順に判定する(各判定の
時刻はその区切りの終わり)。bar_min = 1 なら、1 分足ごとに判定する。

窓(既定 40 分。O-1「直近40分ほど」、原典 v37 124-125 行)= 始まりが 判定の時刻 − 窓 以上の足。足の本数ではなく
時刻で切る(約定 0 の分が抜けても 40 分は 40 分)。窓の中で:
  上端 hi・下端 lo: 既定は実体の端(max(始値, 終値) / min(始値, 終値))。原典 v37 458-478 行はヒゲが
    beard_ignore = 1 円(151 行)を超えると高値・安値を実体の端に置き換える = ほぼ全部のヒゲを捨てる。
    変種 range_from="wick" は高値・安値。
  幅 width = hi − lo、中心 center = (hi + lo) / 2(原典 499-500 行)。
  ボラ vola = 窓の中の足の |終値 − 始値| の平均(原典 488-489 行。原典の「39 本の和 ÷ 40」は直した。INTENT_MAP §4)。
  比 ratio = width / vola(O-2 の「vr = レンジ幅 ÷ 平均実体」。原典 v52 1113 行。W1 の場面の変数の
    「vr」(分散比)とは別の量なので、名前を変えた)。

段(levels=True のとき。原典 v37 109-110 行 sizemin = 0.02・sizemax = 0.14、118 行 pos_count = 7、236 行
order_count = sizemax // sizemin = 7、154-156 行 step_setting、828-877 行 order_buy / order_sell): 1 段の量はどれも
sizemin(844・868 行 order_limit(sizemin, ...))。持ち高 = 向き × 積んだ段の数 ÷ 段の数 n_levels。levels=False なら
段は 1 つだけで、持ち高は −1 / 0 / +1。
  合図: 売りは 終値 > 中心 + entry_setting × vola、買いは 終値 < 中心 − entry_setting × vola(v37 995-998 行。SFD の帯の外の分岐)。
    vola が 0 なら合図なし。
  1 段目: 合図が出た判定で 1 段(v37 の最初の指値は buy_status / sell_status の値段が 9999999 / 0、231・232 行・
    660・661 行なので必ず置かれる)。
  2 段目から: 同じ向きの合図が出ていて、終値が 前に段を積んだ判定の終値 から step_setting × vola を越えて有利な側
    (買いは下、売りは上)へ離れたとき 1 段足す(v37 843 行 price < buy_status['price'] − step、867 行
    price > sell_status['price'] + step。等号なし)。1 本の足で足すのは 1 段まで(原典の 1 巡回 1 段)。
    段の数が n_levels に届いたら足さない(843・867 行 obc / osc < order_count)。

状態と持ち高(判定の時刻 t の足の終値 close で判定する。第 4 稿: 足 1 本 = v37 の巡回 1 回(1038〜1100 行)と読み、
1 本の足の中の順番を v37 の巡回の順 = 一方向の動きの判定 → 入り → 決済の判定 → 一方向の動きが解けたかの判定 にした):
  1. 一方向の動きに入ったか(trend_gate=True のときだけ。比の門 VR_MAX = 10、L-564 問い 5 = A。v37 の
     break_judge の代わり): 比 >= 10 なら trend = sign(close − center)(0 なら前のまま)。
  2. trend != 0 の間(v37 の break_flg != 0。幅の門は見ない = 985-1005 行は range_width を読まない):
     trend_close=True で、この足で trend が始まった(向きが変わった)なら、全部閉じてこの足は終わり(第 3 稿までの
       flat の「閉じる」を引数で残した。既定 off。v37 937-948 行の break の始まりの処理は文字列に入れて消されている)。
     持ち高 0: on_trend="flat"(既定)は入らない(v37 1002 行 b_signal == 0 and posside == 'None' → entry_flg = 0。
       b_signal = 出来高とヒゲの確からしさは使わない)。"follow" は「break の向きに入る」変種で、trend の向きに 1 段
       (b_signal が向きを認めた場合の 1004-1005 行 entry_flg = break_flg の代わり)。
     持ち高あり(entry_flg = break_flg、1004-1005 行): 反対の向きなら全部閉じる(1027-1028 行 exit_flg = 3。
       その足では入らない)。同じ向きなら、利確の線(形 2 なら緩めなし。1029-1030 行 exit_flg = 1)に届けば全部 0、
       届かなければ上の「2 段目から」の規則で段を足す(843・867 行)。時間成行は無い(1027-1036 行に alert_count × 2
       が無い)。
  3. trend == 0(レンジ。v37 の break_flg == 0):
     建ててよい = (width_gate=False)または width / close >= MIN_WIDTH_RATIO(原典 976・993 行の
       range_setting = 150 円を、2019-09-04 の値段に対する割合にした。L-564 問い 4 = B)。入りの向き entry =
       建ててよければ合図、でなければ 0。
     持ち高 0: entry があれば、その向きに 1 段。
     持ち高あり(入りのあとに決済の判定。v37 1083-1100 行):
       buy_ref_reset=True で、買いを持ち entry が 0 なら、次の段の起点を建値の平均にする(v37 1091-1092 行の
         or と and の順で買いだけ指値が取り消され、836-839 行が起点を entry_price に置き直す。既定 off =
         売り買いとも前の段の終値)。
       entry が反対の向きか、time_exit=True で向きを持ってから hold_max_min 分たったなら全部閉じる(1010・1018 行
         exit_flg = 3 → reflesh。その巡回で置いた入りの指値も取り消すので、反対の 1 段目は次の足で合図が続けば建てる)。
         時計は向きが変わったときだけ始める(1050・1066 行 poschangetime)。
       そうでなく利確の線に届いたなら全部 0(v37 1012-1022 行 exit_flg = 2 / 1)。利確の形 exit_mode(v52 162 行。L-566 で引数に):
         2 = 値幅(既定。v37 のコードの実際の利確): 買いは close > 建値 + d、売りは close < 建値 − d。
           d = exit_step × vola(exit_prorate=True なら ÷ 積んだ段の数 = v37 881 行 × sizemin / mybtc)。
           exit_relax=True(既定)なら、向きを持ってから hold_max_min ÷ 2 分(v37 126 行 alert_count = 20)たつか、
           建値が中心より損の側(買いは 建値 > 中心、売りは 建値 < 中心)のとき、線を 中心 と 建値 ± d の損な方へ
           緩める: 買いは min(中心, 建値 + d)、売りは max(中心, 建値 − d)(v37 1012-1014・1020-1022 行 exit_flg = 2、
           897-898・911-912 行)。v37 の exit_setting(138・139・142 行)は実行されるコードでは使われていない。
         1 = センター付近: 買いは close >= center − exit_setting × vola、売りは
           close <= center + exit_setting × vola(v37 138・142 行のコメント、v52 1120-1121 行 sep / lep)。
           exit_guard=True なら、線が建値より損の側にあるとき線を 建値 ∓ close × EXIT_GUARD_RATIO にする
           (v52 840-843・873-876 行の 100 円を、幅の門と同じく 2019-09-04 の値段に対する割合にした)。
         0 = ドテン: 利確の線は無い(v52 942-943 行 exit_flg = 0)。反対の入りの条件で閉じる(上の分岐)。
           v52 の mode 0 は時間成行も止まるので、そろえるなら time_exit=False と組む。
         exit_prorate・exit_relax は形 2 のときだけ効く(形 0・1 では有無で同じ動き)。利確の線に届いた足で同じ向きの
         段は足さない【推定: 売りなら段を足す 終値 > 前の段 + 間隔 と 利確の 終値 < 線 は、約定の値段の飛びが無ければ
         同じ足で両方は起きない】。
       建値 = 積んだ段の約定の値段の平均。約定の値段 = 段を足した判定の次の空でない 1 分足の始値(W1 の仕様 C2)。
       そうでなく entry が同じ向きなら、上の「2 段目から」の規則で 1 段足す(段は 0 になるまで減らさない。
       原典 881 行 order_exit と 703-714 行 reflesh は持ち高 mybtc の全部を閉じる)。
  4. 一方向の動きが解けたか(巡回の最後。v37 952-965 行 break_off_judge): 比 < 10 で、trend の向きの側から close が
     中心に戻った(上向きなら close <= center、下向きなら close >= center)なら trend = 0(O-1「価格が新しいレンジの
     中心へ戻ってきた時点で…再開」)。持ち高はそのまま(v37 どおり)。trend_end_close=True なら全部閉じる(第 3 稿までの
     動きを引数で残した。既定 off)。

部品の切り替え(部品ごとの効果を分けて測るため。リードの指示、L-565・L-566): width_gate(小さすぎの門)・
trend_gate(一方向の動きの状態と再開)・time_exit(時間で出る)・levels(段)・exit_prorate(値幅の按分)・exit_relax
(20 分と損の側の緩め)・exit_guard(建値の守り)・trend_close(動きの始まりで閉じる)・trend_end_close(動きが解けた
足で閉じる)・buy_ref_reset(v37 の買いだけの起点の戻り)。break の向きに入る変種は on_trend="follow"
(trend_gate=False とは組めない)。

窓が満ちるまで(最初に見た 1 分足の始まり > t − 窓 の間)は 0 を返し、状態も動かさない。
出来高 0 の足と、値段が有限でない足は窓に入れない(値段の情報が無い)。

水準の表(WINDOWS など)は、原典の値(窓だけは W1 の仕様 C4 の 1 時間・1 日・1 週も)だけを持ち、表の外の値は
拒む。どの値を測るかはリードが決める(L-565)。
"""
from __future__ import annotations

import math
from collections import deque
from typing import Optional

from bot.research.cards.card import CardError, CardView

NS = 1_000_000_000
MIN_NS = 60 * NS
WINDOW_MIN = 40  # O-1「直近40分ほど」/ 原典 v37 124 行 vola_count = 40・125 行 range_count = 40
WINDOWS = (40, 60, 1440, 10080)  # 40 = 原文。60・1440・10080 = W1 の仕様 C4 の 1 時間・1 日・1 週
BAR_MIN = 1  # 原典 v37 123 行 foot = 1(分)
BAR_MINS = (1,)
ENTRY_K = 2.0  # 原典 v37 141 行 entry_setting = 2
ENTRY_SETTINGS = (2.0,)
EXIT_K = 0.8  # 原典 v37 142 行 exit_setting = 0.8(L-564 問い 1 = B)
EXIT_SETTINGS = (0.8, 2.0)  # 0.8 = v37 142 行 / 2 = v52 128・130 行(inner・outer とも)
EXIT_MODE = 2  # v37 のコードの実際の利確(881 行 建値から按分した値幅)。v52 162 行の番号では 2 = 値幅
EXIT_MODES = (0, 1, 2)  # v52 162 行「0:ドテン(ポジと反対のエントリー時) 1:センター付近 2:値幅」
EXIT_STEP = 0.8  # v37 157 行 step_exit = 0.8(v37 の利確の値幅。v52 では exit_step と改名)
EXIT_STEPS = (0.8, 0.0)  # 0.8 = v37 157 行 step_exit / 0 = v52 163 行 exit_step
# v52 841・849・855・874・882・888 行 entry_price ∓ 100(円)÷ 2019-09-04 の値段(幅の門と同じ。リードの決め 3)
EXIT_GUARD_RATIO = 100.0 / 1152502.0
STEP_K = 1.0  # 原典 v37 156 行 step_setting = 1
STEP_SETTINGS = (1.0,)
N_LEVELS = 7  # 原典 v37 118 行 pos_count = 7 / 236 行 order_count = sizemax // sizemin = 0.14 // 0.02 = 7
LEVEL_COUNTS = (7,)
ALERT_MIN = 20  # 原典 v37 126 行 alert_count = 20(分)
HOLD_MAX_MIN = 2 * ALERT_MIN  # 原典 v37 1010・1018 行 alert_count * 2 で成行の決済
HOLD_MAXES = (40,)
VR_MAX = 10.0  # v52 125 行のコメントの例「vr>10」(L-564 問い 5 = A。変種 None・100 は外した)
# 原典 v37 134 行 range_setting = 150(円)÷ 2019-09-04(日本時間)の bitFlyer FX_BTC_JPY の 1 分足の終値の
# 中央値 1,152,502 円(L-564 問い 4 = B。出し方は CARD.md「水準とその出所」)
MIN_WIDTH_RATIO = 150.0 / 1152502.0
RANGE_FROMS = ("body", "wick")
ON_TRENDS = ("flat", "follow")


def _num_in(name: str, value, table: tuple, card: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value not in table:
        raise CardError(f"{card}: {name} は {list(table)} のどれか: {value!r}")
    return float(value)


def _int_in(name: str, value, table: tuple, card: str) -> int:
    if type(value) is not int or value not in table:
        raise CardError(f"{card}: {name} は {list(table)} のどれか(整数): {value!r}")
    return value


def _flag(name: str, value, card: str) -> bool:
    if type(value) is not bool:
        raise CardError(f"{card}: {name} は True / False: {value!r}")
    return value


class C4OwnerMatildaRange:
    """カードの口(bot.research.cards.Card)。モジュールの説明を参照。"""

    name = "c4_owner_matilda_range"
    requires: tuple = ()

    def __init__(self, *, window_min: int = WINDOW_MIN, bar_min: int = BAR_MIN,
                 entry_setting: float = ENTRY_K, exit_setting: float = EXIT_K, step_setting: float = STEP_K,
                 n_levels: int = N_LEVELS, hold_max_min: int = HOLD_MAX_MIN,
                 exit_mode: int = EXIT_MODE, exit_step: float = EXIT_STEP, exit_prorate: bool = True,
                 exit_relax: bool = True, exit_guard: bool = False,
                 range_from: str = "body", on_trend: str = "flat",
                 trend_close: bool = False, trend_end_close: bool = False, buy_ref_reset: bool = False,
                 width_gate: bool = True, trend_gate: bool = True, time_exit: bool = True,
                 levels: bool = True) -> None:
        n = self.name
        self.window_min = _int_in("window_min", window_min, WINDOWS, n)
        self.bar_min = _int_in("bar_min", bar_min, BAR_MINS, n)
        self.entry_setting = _num_in("entry_setting", entry_setting, ENTRY_SETTINGS, n)
        self.exit_setting = _num_in("exit_setting", exit_setting, EXIT_SETTINGS, n)
        self.step_setting = _num_in("step_setting", step_setting, STEP_SETTINGS, n)
        self.n_levels = _int_in("n_levels", n_levels, LEVEL_COUNTS, n)
        self.hold_max_min = _int_in("hold_max_min", hold_max_min, HOLD_MAXES, n)
        self.exit_mode = _int_in("exit_mode", exit_mode, EXIT_MODES, n)
        self.exit_step = _num_in("exit_step", exit_step, EXIT_STEPS, n)
        self.exit_prorate = _flag("exit_prorate", exit_prorate, n)
        self.exit_relax = _flag("exit_relax", exit_relax, n)
        self.exit_guard = _flag("exit_guard", exit_guard, n)
        if range_from not in RANGE_FROMS:
            raise CardError(f"{n}: range_from は {list(RANGE_FROMS)} のどれか: {range_from!r}")
        if on_trend not in ON_TRENDS:
            raise CardError(f"{n}: on_trend は {list(ON_TRENDS)} のどれか: {on_trend!r}")
        self.width_gate = _flag("width_gate", width_gate, n)
        self.trend_gate = _flag("trend_gate", trend_gate, n)
        self.time_exit = _flag("time_exit", time_exit, n)
        self.levels = _flag("levels", levels, n)
        self.trend_close = _flag("trend_close", trend_close, n)
        self.trend_end_close = _flag("trend_end_close", trend_end_close, n)
        self.buy_ref_reset = _flag("buy_ref_reset", buy_ref_reset, n)
        # 原典 v37 139 行「必ず entry_setting > exit_setting」。v52 128・130 行は両方 2(等しい)なので、等しいまでは受ける
        if self.exit_setting > self.entry_setting:
            raise CardError(f"{n}: exit_setting > entry_setting: {entry_setting!r}, {exit_setting!r}")
        if self.exit_guard and self.exit_mode != 1:
            raise CardError(f"{n}: exit_guard は exit_mode=1 のときだけ(v52 837-843・872-876 行)")
        if self.window_min % self.bar_min:
            raise CardError(f"{n}: window_min が bar_min の倍数でない: {window_min!r}, {bar_min!r}")
        if on_trend == "follow" and not self.trend_gate:
            raise CardError(f"{n}: on_trend='follow' は trend_gate=True のときだけ(一方向の状態が無いと同じ動き)")
        self.range_from = range_from
        self.on_trend = on_trend
        self.window_ns = self.window_min * MIN_NS
        self.bar_ns = self.bar_min * MIN_NS
        self.hold_ns = self.hold_max_min * MIN_NS
        # v37 は alert_count(126 行)1 つから、20 分で利確の線を緩め(1012・1020 行)、× 2 の 40 分で成行(1010・1018 行)
        self.relax_ns = (self.hold_max_min // 2) * MIN_NS
        self.max_levels = self.n_levels if self.levels else 1
        self._bars: deque = deque()  # (start, hi, lo, |body|) 窓の中の足(bar_min 分)、古い順
        self._maxq: deque = deque()  # (start, hi) hi が減っていく並び(窓の最大)
        self._minq: deque = deque()  # (start, lo) lo が増えていく並び(窓の最小)
        self._body_sum = 0.0
        self._removed = 0  # 和を作り直してから窓から出た足の数
        self._last_end: Optional[int] = None  # 取り込んだ最後の 1 分足の終わり
        self._first_start: Optional[int] = None  # 最初に取り込んだ 1 分足の始まり
        self._agg: Optional[list] = None  # まとめ中の足 [区切りの番号, 始値, 高値, 安値, 終値]
        self._close: Optional[float] = None
        self._side = 0  # 向き −1 / 0 / +1
        self._n = 0  # 積んだ段の数
        self._entry_t: Optional[int] = None  # 今の向きを持った判定の時刻
        self._fills: list = []  # 積んだ段の約定の値段(判定の次の足の始値。W1 の仕様 C2)
        self._pending = 0  # 約定の値段がまだ分からない段の数
        self._last_px: Optional[float] = None  # 前に段を積んだ判定の足の終値(次の段の起点。v37 843・867 行)
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

    def _ingest(self, b) -> None:
        self._last_end = b.received_time_ns
        o, h, lo, c = float(b.open), float(b.high), float(b.low), float(b.close)
        if not (b.volume > 0) or not all(math.isfinite(x) for x in (o, h, lo, c)):
            return
        start = int(b.start_time_ns)
        if self._first_start is None:
            self._first_start = start
        idx = start // self.bar_ns
        if self._agg is not None and self._agg[0] != idx:
            self._close_agg()
        if self._pending:  # 前の判定で足した段は、この足(判定の後の最初の空でない足)の始値で約定
            self._fills.extend([o] * self._pending)
            self._pending = 0
        if self._agg is None:
            self._agg = [idx, o, h, lo, c]
        else:
            a = self._agg
            a[2], a[3], a[4] = max(a[2], h), min(a[3], lo), c

    def _close_agg(self) -> None:
        idx, o, h, lo, c = self._agg
        self._agg = None
        start = idx * self.bar_ns
        self._push(start, o, h, lo, c)
        self._decide(start + self.bar_ns)

    def _push(self, start: int, o: float, h: float, lo: float, c: float) -> None:
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

    def _flat(self) -> None:
        self._side, self._n = 0, 0
        self._entry_t, self._last_px = None, None
        self._fills, self._pending = [], 0

    def _open(self, side: int, t: int, close: float) -> None:
        """(持っていれば全部閉じて)side の向きに 1 段。時計はここで始める(向きが変わったときだけ)。"""
        self._side, self._n = side, 1
        self._entry_t, self._last_px = t, close
        self._fills, self._pending = [], 1

    def _add(self, close: float, vola: float) -> None:
        """前に段を積んだ判定の終値から step_setting × vola を越えて有利な側へ離れていれば 1 段足す
        (v37 843・867 行。等号なし)。時計は戻さない。"""
        if (self._n < self.max_levels and vola > 0
                and self._side * (self._last_px - close) > self.step_setting * vola):
            self._n += 1
            self._pending += 1
            self._last_px = close

    def _entry_price(self) -> Optional[float]:
        """建値 = 積んだ段の約定の値段の平均(段の量はどれも同じ)。まだ分からない段があれば None。"""
        if self._pending or not self._fills:
            return None
        return math.fsum(self._fills) / len(self._fills)

    def _take_profit(self, close: float, center: float, vola: float, t: int, relax: bool) -> bool:
        """利確の線に届いたか(exit_mode。v37 879-928 行・v52 815-904 行)。"""
        side = self._side
        if self.exit_mode == 0:  # ドテン: 利確の線は無い。反対の入りの条件で閉じる(呼び出し側)
            return False
        if self.exit_mode == 1:  # センター付近: 売りは 中心 + exit_setting × vola(v52 1120 行 sep)、買いは −(lep)
            line = center - side * self.exit_setting * vola
            if self.exit_guard:  # v52 840-843 行: 線が建値より損の側なら、建値 ∓ 100 円(を値段に対する割合に)
                ep = self._entry_price()
                if ep is not None and side * (line - ep) < 0:
                    line = ep + side * close * EXIT_GUARD_RATIO  # 売り: 建値 − (841 行)、買い: 建値 + (874 行)
            return close >= line if side == 1 else close <= line
        # 値幅: 建値から exit_step × vola(按分なら × 1 段の量 ÷ 持ち高 = 1 / 段の数。v37 881 行・v52 817 行)
        ep = self._entry_price()
        if ep is None:
            return False
        line = ep + side * self.exit_step * vola / (self._n if self.exit_prorate else 1)
        if relax and (t - self._entry_t >= self.relax_ns or side * (ep - center) > 0):
            # v37 897-898 行(売り): 中心 と 建値 − exit_vola の高い方。911-912 行(買い): 低い方
            line = min(center, line) if side == 1 else max(center, line)
        return close > line if side == 1 else close < line

    def _signal(self, close: float, center: float, vola: float) -> int:
        """入りの合図: 売り −1 / 買い +1 / なし 0(v37 995-998 行)。vola が 0 なら合図なし。"""
        if not vola > 0:
            return 0
        if close > center + self.entry_setting * vola:
            return -1
        if close < center - self.entry_setting * vola:
            return 1
        return 0

    def _decide(self, t: int) -> None:
        lo_start = t - self.window_ns
        self._trim(lo_start)
        if self._first_start is None or self._first_start > lo_start or not self._bars:
            return  # 窓が満ちるまで(持ち高は 0 のまま)
        hi, lo = self._maxq[0][1], self._minq[0][1]
        width = hi - lo
        center = (hi + lo) / 2.0
        vola = self._body_sum / len(self._bars)
        close = self._close
        if vola > 0:
            ratio = width / vola
        else:
            ratio = math.inf if width > 0 else 0.0

        # 足 1 本 = v37 の巡回 1 回(1038〜1100 行): 一方向の動きの判定(ently_judge の頭の break_judge)→ 入り
        # (order_buy / order_sell)→ 決済の判定(exit_judge。exit_flg = 3 の reflesh はその巡回で置いた入りの
        # 指値ごと取り消して全部成行)→ 一方向の動きが解けたかの判定(break_off_judge)。
        # 1. 一方向の動きに入ったか(O-2 の門。v37 の break_judge の代わり)
        was_trend = self._trend
        if self.trend_gate and ratio >= VR_MAX:
            d = (close > center) - (close < center)
            if d != 0:
                self._trend = d
        if self._trend != 0:
            self._in_trend(t, close, center, vola, started=self._trend != was_trend)
        else:
            self._in_range(t, close, center, vola, width)
        # 4. 一方向の動きが解けたか(v37 952〜965 行 break_off_judge。巡回の最後。持ち高はそのまま)
        if self._trend == 1 and close <= center or self._trend == -1 and close >= center:
            if ratio < VR_MAX:
                self._trend = 0
                if self.trend_end_close:  # 第 3 稿までの動き(引数で残す。既定 off)
                    self._flat()

    def _in_trend(self, t: int, close: float, center: float, vola: float, started: bool) -> None:
        """一方向の動きの間(v37 の break_flg != 0)。幅の門は見ない(985〜1005 行は range_width を読まない)。"""
        d = self._trend
        if started and self.trend_close:  # 第 3 稿までの「閉じる」(引数で残す。既定 off。v37 937〜948 行は消されている)
            self._flat()
            return
        side = self._side
        if side == 0:
            # v37 1002 行: b_signal == 0 で持ち高 0 なら entry_flg = 0。b_signal は使わないので flat は入らない。
            # follow は「break の向きに入る」変種(b_signal が向きを認めた場合の 1004〜1005 行 entry_flg = break_flg)
            if self.on_trend == "follow":
                self._open(d, t, close)
            return
        # 持ち高あり: entry_flg = break_flg(1004〜1005 行)
        if side != d:  # 反対の向き: 1027〜1028 行 exit_flg = 3 → reflesh で全部閉じる(入りの指値も取り消す)
            self._flat()
        elif self._take_profit(close, center, vola, t, relax=False):  # 1029〜1030 行 exit_flg = 1(緩めなし)
            self._flat()
        else:  # 同じ向き: order_buy / order_sell の間隔の規則で段を足す(843・867 行)。時間成行は無い
            self._add(close, vola)

    def _in_range(self, t: int, close: float, center: float, vola: float, width: float) -> None:
        """レンジ(v37 の break_flg == 0)。"""
        allowed = (not self.width_gate) or width / close >= MIN_WIDTH_RATIO
        sig = self._signal(close, center, vola)
        entry = sig if allowed else 0  # v37 976・993 行: 幅の門を割れば entry_flg = 0
        side = self._side
        if side == 0:
            if entry != 0:
                self._open(entry, t, close)
            return
        if self.buy_ref_reset and side == 1 and entry == 0:
            # v37 1091〜1092 行(or と and の順で、買いの指値があると持ち高があっても全部取り消す)→ 次の合図で
            # 836〜839 行が起点を建値の平均 entry_price に置き直す。売りは取り消されない
            ep = self._entry_price()
            if ep is not None:
                self._last_px = ep
        # 入り(同じ向きなら段を足す指値)のあとに決済の判定(1007〜1022 行)。exit_flg = 3 はその巡回の入りを取り消す
        if entry == -side or (self.time_exit and t - self._entry_t >= self.hold_ns):  # exit_flg = 3
            self._flat()
        elif self._take_profit(close, center, vola, t, relax=self.exit_relax):  # exit_flg = 2(緩め)/ 1
            self._flat()
        elif entry == side:
            self._add(close, vola)

    def exposure(self, view: CardView) -> float:
        t = view.now_ns
        for b in self._new_bars(view):
            self._ingest(b)
        if self._agg is not None and (self._agg[0] + 1) * self.bar_ns <= t:
            self._close_agg()
        return self._side * self._n / self.max_levels


__all__ = ["ALERT_MIN", "BAR_MIN", "BAR_MINS", "C4OwnerMatildaRange", "ENTRY_K", "ENTRY_SETTINGS", "EXIT_GUARD_RATIO",
           "EXIT_K", "EXIT_MODE", "EXIT_MODES", "EXIT_SETTINGS", "EXIT_STEP", "EXIT_STEPS", "HOLD_MAXES", "HOLD_MAX_MIN", "LEVEL_COUNTS", "MIN_WIDTH_RATIO",
           "N_LEVELS", "ON_TRENDS", "RANGE_FROMS", "STEP_K", "STEP_SETTINGS", "VR_MAX", "WINDOWS", "WINDOW_MIN"]

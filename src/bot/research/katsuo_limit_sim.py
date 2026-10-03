"""カード 2: katsuo_v03 の指値の形を 1 分足で再現する(仕様 docs/RESEARCH/cards/c2_owner_xvenue_wick/limit_sim/SPEC.md)。

原典 = docs/legacy/katsuo_v03.py(以下「原典の n 行」)。合図はカード 2(bot.research.cards.library.c2_owner_xvenue_wick)の
classify_detail と、カードの _apply と同じ分岐を使い、変えるのは約定の形だけ(仕様の冒頭)。カードの口(持ち高を毎分
返す形)は指値を表せないので使わない。

使い方
------
    sim = KatsuoLimitSim(fill_side="good", at_max="skip")   # design="v03"(仕様 1〜6)。表の外は ValueError
    sim = KatsuoLimitSim(fill_side="good", design="k1", entry="a", vol_gate=True, vol_edges=(q1, q2))  # 仕様 9
    sim = KatsuoLimitSim(fill_side="good", design="k1", entry="a", fill="close")  # 参照の形(行動の時刻の終値で約定)
    for 区切り in 暦年:
        sim.add_refs(その区切りの海外の 1 分足の行)            # 先に渡す(行 = (open_time ns, 始値, 高値, 安値, 終値))
        for b in その区切りの bitFlyer の 1 分足:             # 古い順に
            rows += sim.feed(b)                               # この足で終わった取引の行
    rows += sim.finish()                                      # 期間の終わりに持っている持ち高を最後の終値で閉じる

足 b は start_time_ns(1 分の始まり)・open・high・low・close・volume を持つもの(bot.bt.core.BarEvent など)。

仕様の節とコードの対応
----------------------
  1   入力(執行の足・参照の行・遅れ 60 秒): add_refs、feed の頭、_advance
  2   合図(海外の足のまとめ・classify_detail・先端・_apply と同じ分岐・持ち高 = 約定した持ち高・時刻 T): _advance、
      _close_bucket、_decide、action
  3-1 入り(取り消し・P1・P2・量・増し玉・ドテン・上限・at_max・約定の等号なし・注文が残る): _place_entry、_thr、_leg
  3-2 降りる(4 本・ドルの幅の比・ストップ指値の引き金と戻り・1 本約定で残りが無くなる): _place_exit、_thr、_leg、_fill
  4   1 本の足の中(2 通りの道・足の頭・決まらない足・良い側 / 悪い側): _bar、_path、_value
  5   損益と取引の行・注文ごとの数: _apply_fill、_row、order_log
  8-2 入りの合図の強い / 弱い(_decide → _place_entry の strength)、降りる注文を出した理由(_decide → _place_exit の
      why。取引の行の exit_signal。降りる注文で閉じた取引だけに付き、ドテン・期間の終わりは空)
  6   引数の表: KatsuoLimitSim.__init__
  9   design="k1"(K1 の H1+H2a・弱いだけ / 強いだけ、K1 の持ち高の機械): k1_signal、_decide_k1、_act_k1。
      入り方 entry a / b / c: _decide_k1(下の「行動の時刻」)、_place_entry。
      高ボラの門: _push_close(vol_prev)、tercile、_act_k1。参照の形 fill="close": _fill_now。
      取り逃し: 走らせ(scripts/w4_measure/c2_limit_run.py)が fill="close" の物を並走させて数える(下)

仕様 9(design="k1")で K1 から写したもの(scripts/measure_katsuo_effect.py の行)
------------------------------------------------------------------------------
- 合図 k1_signal = signals()(93〜133 行)を門 s19/b24(measure_katsuo_xvenue.py の MAIN_GATE_SMALL/BIG)で:
  ヒゲどうしは int() で切り捨てて比べる(115 行)、bp の分母は終値(123 行)、小門の枝は w > |実体|(124 行)、
  H1(129〜131 行、flip_body): 実体 >= ヒゲ なら向き = −色、先端 = 新しい向きの側の極値、強さ = 向き == 色 なら強い。
  side_keep="strong" は H1 を当てない(flip_body=False)。カード 2 の classify_detail(切り捨てなし・分母は始値)とは違う。
- H3(delay_signals 136〜149 行): 足 i の合図の行動を、次に閉じた足の区切りで出す。降りる行動(とドテン)は入り方に
  関係なく H3 で遅らせる。入りの時刻だけを入り方で変える(下の「行動の時刻」)。
- 持ち高の機械(simulate 152〜212 行、keep・use_invalid=False): 絞った強さ以外の合図は「合図なし」(193 行)。合図なし
  では何もしない(H2a: 198〜201 行の無効化を通らない)。同じ向き → 何もしない(増し玉なし、203〜204 行)。反対の向き →
  閉じる(205〜206 行)、強いときだけドテン(207〜208 行)。持ち高 0 → 新しく入る(209〜210 行)。
  keep="weak" では 207 行が通らないので、反対の弱い合図は閉じるだけ(ドテンしない)。仕様 9 の表の「反対の合図で
  ドテン」とは違う【K1 のコードに合わせた】。「閉じる」は降りる注文 4 本を出すこと、「入る」は入りの指値を出すこと。
  持ち高は約定した持ち高(仕様 2)。0.5 だけ約定した持ち高も向きで扱う(K1 は ±1 の向きだけを見る)。
  同じ向きの入りの注文が残っている間に同じ向きの合図が来たら何もしない(K1 では先の合図で既に建っているので
  「同じ向き → 何もしない」に当たる。リードの直し 5)。門で入りを弾いたときも、反対向きの入りの注文は取り消す
  (K1 では反対の合図で持ち高 0 に戻る。リードの直し 4)。

行動の時刻(design="k1"。リードの直し 3)
-----------------------------------------
足 i(区切り T_i)の合図は、次のどちらか:
  - 入り方 b・c で、T_i に持ち高が 0: その場(T_i)で持ち高 0 の行動(入る・何もしない・門で弾く)をする。
  - それ以外(入り方 a、または持ち高が 0 でない): 次に閉じた足の区切り T_{i+1} まで持ち、そのときの持ち高で行動する
    (反対 → 降りる / ドテン、0 → 入る、同じ → 何もしない)。
  T_{i+1} では、先に持っていた足 i の行動をしてから、足 i+1 の合図を扱う。入り方 a はすべて K1 の H3 と同じ。
  入り方 b・c で足 i の合図を持ち越した後に T_{i+1} で持ち高が 0 になっていたら、入りは T_{i+1}(1 本遅れ)になる
  【置いた形】。

参照の形 fill="close"(design="k1" だけ。リードの直し 2)
--------------------------------------------------------
合図・機械・足の作り方・行動の時刻は fill="limit" と同じで、注文を出したその時刻(行動の時刻)の直前の bitFlyer の
終値で、入りも降りるも全量を必ず約定させる(入り方 b の半値・c の 2 本目もこの終値)。降りる約定の終わり方は "終値"。
足の中を通さないので決まらない足は無い。入り方 a は K1 の H3(足の終値で約定)と同じ規則になる。
- vol_prev(measure_katsuo_robustness.py 215〜226 行 FootData.vol_prev): vol[i] = Σ_{j=i−100}^{i−1} |log(c_j/c_{j−1})|
  × 1e4 / 100。境目は K1 の取引の vol_prev[entry_i](measure_katsuo_xvenue.py の run_vol_terciles)、entry_i は H3 で
  遅らせた行動の足 = 合図の足 + 1 なので、合図の足までの 100 本の値動き(合図の足の終値を含む)の平均になる。
  ここでもそれを合図の足の vol_prev とする(合図の足が閉じた時点で分かる。先読みなし)。足が 101 本そろうまでは
  値なし(三分位なし、門では入らない)。三分位の切り方は bucket_of(v < q1 低い、v < q2 中、それ以外 高い)。

値段の刻み(オーナー L-595「bitFlyerの値段に小数点があるのはタダのバグだから放置せず直して」)
-----------------------------------------------------------------------------------------------
bitFlyer FX_BTC_JPY の値段は 1 円刻み(1 分足の 4 本値に端数は無い)。bitFlyer に出す注文の値段は、置くとき(_order)に
全部 1 円刻みに丸め、約定の判定も約定の値段も丸めた値段で行う。向きは自分に不利な側:
  - 指値(入りの 1 本目・2 本目、降りる指値、ストップ指値の指値): 売りは切り下げ、買いは切り上げ。
  - ストップの引き金(ストップ指値・ストップ成行): 引き金が早く引かれる側。売りのストップは切り上げ、買いのストップは
    切り下げ。
  - ストップ成行の約定の値段: 足の中で引き金を越えたときは、丸めた引き金の 1 円向こう(売りのストップは引き金 − 1 円、
    買いのストップは引き金 + 1 円)。足の値段は 1 円刻みで判定は等号なしなので、引き金を越えた最初の値段はそこで、
    丸める前の引き金より必ず自分に不利な側にある(批評家の指摘・リードの決め)。足の頭で越えたときは始値。
    どちらも整数。参照の形(fill="close")は bitFlyer の終値(整数)。
  - 浮動小数の誤差で整数の値段が切り上げ・切り下げで 1 円動かないよう、TICK_EPS(1e-6 円)の幅は整数とみなす。
建値は約定の量で重みを付けた平均なので小数が残りうる。損益は丸めた約定の値段から出す。

時刻(仕様 2 の最後の項)
-----------------------
海外の 1 分足の行(時刻 = open_time)は open_time + 60 秒(ROW_LAG_NS、カードの宣言)に使える。bitFlyer の足
(始まり s)を受け取ると、まず使える時刻が s 以下の行だけをまとめ、終わり T が s 以下の海外の足を閉じて、T ごとに
合図を判定し注文を出す。その後でこの足の約定を見る。よって時刻 T に出した注文は、始まりが T 以上の足からだけ約定する。
P1・X(直前の bitFlyer の終値)= それまでに受け取った足(終わり <= T)の最後の終値。

1 本の足の中(仕様 4。仕様で決まっていなかった所は【置いた形】と書く)
--------------------------------------------------------------------
足の頭: 始値 O の時点で既に越えている値段(上がる側で起きるものは値段 < O、下がる側は値段 > O)は 2 本の脚より前に
起きたものとし、値段はその注文の値段のまま。ただしストップ成行は始値で約定させる(前の足の終値から次の足の始値の
間に約定は無いので、最初に約定できるのは始値。批評家の指摘 1・リードの直し 1)。足の中(脚)で引き金を越えたストップ
成行は引き金の 1 円向こう(下の「値段の刻み」)。上がる側 → 下がる側の順
(カード 4 の再現と同じ)。続けて 2 通りの道で通す: 上が先(O → 高値 → 安値)と下が先(O → 安値 → 高値)。脚の中では
越えた値段の順(上りは安い方から、下りは高い方から。同じ値段なら注文を出した順)。
上がる側で起きるもの = 売りの指値の約定(高値 > 値段)と買いのストップの引き金(値段 > 引き金)。
下がる側で起きるもの = 買いの指値の約定(安値 < 値段)と売りのストップの引き金(値段 < 引き金)。
引き金も等号なし【置いた形】(仕様は約定の等号なしだけを書く)。ストップ指値は引き金の後、反対の向きの指値になる
(買い持ちの売りのストップ指値は、引き金 X − 1.5 の下抜けの後、X − 1 の売りの指値)ので、引き金を引いた脚では
約定せず、次の脚(または次の足)で戻ったら約定する。
脚は 2 本だけ(仕様 4 の道のとおり。安値または高値から終値への動きは通さない)。2 本目の脚で引き金を引いたストップ
指値は、その足では約定せず、引き金を引いた状態で次の足に残る(次の足の始値が指値を越えていれば足の頭で約定)。
2 通りの道で出来事の並びが違えば決まらない足。良い側 / 悪い側の比べ方【置いた形】: その足で閉じた取引の損益と、
足の終わりに持っている取引の(実現した分 + その足の終値での含み)の和。和が大きい道が良い側。和が同じなら、始値に
近い方の端へ先に行く道を両方の側で使う(カード 4 の再現と同じ)。
決まらない足は、その足で持っていた取引(その足で閉じた取引と、足の終わりに持っている取引)に 1 ずつ数える。
入りの注文は 1 本目・2 本目が同じ側にあり、降りる注文と同時には無い(注文を出すたびに全部取り消す)ので、
決まらない足は降りる注文のある足でだけ起きる。1 回閉じた足で入り直すことは、入りの注文が無いので起きない。

取り逃し(仕様 9、design="k1" だけ。リードの直し 5 で定め直した)
---------------------------------------------------------------
fill="close" の形で建った取引のうち、fill="limit" の形で約定しなかったもの(同じ合図の時刻 signal_ns の取引が limit の
形に無いもの)。数えるのは走らせの台本で、同じ入力に fill="close" の物を並走させ、取引の行を合図の時刻で突き合わせる
(order_log の 6 列目 = 注文を出した合図の時刻で、limit の形が注文を出したのに約定しなかったものと、注文を出して
いないものを分ける)。損益は close の形の取引の損益。
"""
from __future__ import annotations

import math
from collections import deque
from typing import Optional

from bot.research.cards.library.c2_owner_xvenue_wick import BIG_GATE_BP, FOOTS, ROW_LAG_NS, SMALL_GATE_BP, classify_detail

NS = 1_000_000_000
MIN_NS = 60 * NS

SIZE_DEF = 0.5  # 原典 34 行 sizedef(仕様 3: 量 0.5)
SIZE_MAX = 1.0  # 原典 35 行 sizemax = sizedef × 2(仕様 3: 持ち高の最大 1)
STOP_LIMITS = ((1.5, 1.0), (3.5, 3.0))  # 原典 394〜395 行・400〜401 行(引き金・指値の幅、ドル)
STOP_MARKET = 5.0  # 原典 406 行(引き金の幅、ドル)
AT_MAXES = ("skip", "flip")  # 仕様 3-1 の 29 行・仕様 6
FILL_SIDES = ("good", "bad")  # 仕様 4・仕様 6
DESIGNS = ("v03", "k1")  # 仕様 8-3・9
ENTRIES = ("a", "b", "c")  # 仕様 9: a = 次の足の区切りで最良気配に 1 本 / b = 合図の時点で半値に 1 本 / c = 両方 0.5 ずつ
SIDE_KEEPS = ("weak", "strong")  # 仕様 9: 弱いだけ(H1 あり)/ 強いだけ(1 分の組、H1 なし)
K1_FEET = {"weak": (5, 15, 30, 60), "strong": (1,)}  # 仕様 9 の「足の長さ」
K1_SMALL_BP, K1_BIG_BP = 19.0, 24.0  # measure_katsuo_xvenue.py MAIN_GATE_SMALL / MAIN_GATE_BIG(門 s19/b24)
VOL_WINDOW = 100  # measure_katsuo_robustness.py 69 行

# 終わり方(仕様 5)
EXIT_LIMIT, EXIT_SL1, EXIT_SL2, EXIT_SM = "指値", "ストップ指値 1", "ストップ指値 2", "ストップ成行"
EXIT_DOTEN, EXIT_END = "ドテン", "期間の終わり"
EXIT_CLOSE = "終値"  # fill="close" の降りる約定
FILLS = ("limit", "close")
TICK_EPS = 1e-6  # 1 円刻みに丸めるとき、この幅の中は整数とみなす(浮動小数の誤差)


def tick_up(x: float) -> float:
    """1 円刻みに切り上げ。"""
    return float(math.ceil(x - TICK_EPS))


def tick_down(x: float) -> float:
    """1 円刻みに切り下げ。"""
    return float(math.floor(x + TICK_EPS))
# 入りの合図の強弱(仕様 8-2、K1 の言葉): 強い = 陽線 × 下ヒゲ → 買い・陰線 × 上ヒゲ → 売り、
# 弱い = 陽線 × 上ヒゲ → 売り・陰線 × 下ヒゲ → 買い
STRONG, WEAK = "強い", "弱い"
# 降りる注文を出した理由(仕様 8-2): 反対の弱い合図(陽線 × 上ヒゲ × 買い持ち・陰線 × 下ヒゲ × 売り持ち)/
# 合図なしで終値がヒゲ先端を越えた
XSIG_WEAK, XSIG_LINE = "反対の弱い合図", "ヒゲ先端を終値で越えた"
_EXIT_REASON = {"x_lim": EXIT_LIMIT, "x_sl1": EXIT_SL1, "x_sl2": EXIT_SL2, "x_sm": EXIT_SM}


def _in(name, value, table):
    if isinstance(value, bool) or value not in table:
        raise ValueError(f"{name} は {list(table)} のどれか: {value!r}")
    return value


def action(color: int, sig: int, pos: float, c: float, line: Optional[float]) -> Optional[str]:
    """カードの _apply と同じ分岐(原典 490〜535 行)。持ち高を変える代わりに出す注文の種類を返す:
    "buy"(order_buy)/ "sell"(order_sell)/ "exit"(order_exit)/ None(何もしない)。pos は約定した持ち高。"""
    if color == 1:
        if sig == -1:
            return "exit" if pos > 0 else "sell"
        if sig == 1:
            return "buy"
        if pos < 0 and not (c < line):
            return "exit"
    elif color == -1:
        if sig == 1:
            return "exit" if pos < 0 else "buy"
        if sig == -1:
            return "sell"
        if pos > 0 and not (c > line):
            return "exit"
    return None


def k1_signal(o: float, h: float, lo: float, c: float, flip_body: bool):
    """K1 の signals()(scripts/measure_katsuo_effect.py 95〜130 行)を足 1 本に、門 s19/b24 で。
    (向き, 先端, 色, 強さ "strong"/"weak"/"", 19 の枝, 24 の枝, H1 で向きを変えた)。"""
    candle = c - o
    csign = 1 if candle > 0 else (-1 if candle < 0 else 0)
    if csign == 0:
        return 0, 0.0, 0, "", False, False, False
    top, under = (h - c, o - lo) if csign == 1 else (h - o, c - lo)
    body = abs(candle)
    t_cmp, u_cmp = int(top), int(under)  # trunc=True(原典どおり)
    if t_cmp > u_cmp:
        sig, w, lc = -1, top, h
    elif u_cmp > t_cmp:
        sig, w, lc = 1, under, lo
    else:
        return 0, 0.0, csign, "", False, False, False
    wbp = w / c * 1e4 if c > 0 else 0.0
    ok_small = wbp >= K1_SMALL_BP and w > body
    ok_big = wbp >= K1_BIG_BP
    if not (ok_small or ok_big):
        return 0, 0.0, csign, "", False, False, False
    flipped = False
    if flip_body and body >= w:
        sig = -csign  # 実体を逆張り(H1)
        lc = h if sig == -1 else lo
        flipped = True
    return sig, lc, csign, ("strong" if sig == csign else "weak"), ok_small, ok_big, flipped


def tercile(v: Optional[float], edges: Optional[tuple]) -> Optional[str]:
    """measure_katsuo_xvenue.py の bucket_of と同じ切り方。値なし・境目なしは None。"""
    if edges is None or v is None or v != v:
        return None
    q1, q2 = edges
    if v < q1:
        return "low"
    if v < q2:
        return "mid"
    return "high"


class _Order:
    """置いてある注文 1 本。side +1 買い / -1 売り。price は指値(ストップ成行は None)、trig はストップの引き金
    (指値は None)、armed は引き金を引いた後。reduce は降りる注文(全量・reduce-only)。rec は order_log の位置。"""
    __slots__ = ("kind", "side", "qty", "price", "trig", "armed", "reduce", "t_place", "info", "rec")

    def copy(self) -> "_Order":
        o = _Order()
        for k in self.__slots__:
            setattr(o, k, getattr(self, k))
        return o


def _order(kind, side, qty, price, trig, reduce, t_place, info, rec) -> _Order:
    """注文を置く。値段は 1 円刻みに、自分に不利な側へ丸める(モジュールの説明「値段の刻み」)。"""
    if price is not None:
        price = tick_up(price) if side == 1 else tick_down(price)  # 買いの指値は切り上げ、売りは切り下げ
    if trig is not None:
        trig = tick_down(trig) if side == 1 else tick_up(trig)  # 買いのストップは切り下げ、売りは切り上げ
    o = _Order()
    o.kind, o.side, o.qty, o.price, o.trig, o.armed = kind, side, qty, price, trig, False
    o.reduce, o.t_place, o.info, o.rec = reduce, t_place, info, rec
    return o


class _St:
    """1 本の足を通すときの状態(2 通りの道を試すので写せるようにする)。"""
    __slots__ = ("pos", "trade", "orders", "closed", "events", "fills")

    def copy(self) -> "_St":
        s = _St()
        s.pos = self.pos
        s.trade = None if self.trade is None else dict(self.trade)
        s.orders = [o.copy() for o in self.orders]
        s.closed, s.events, s.fills = list(self.closed), list(self.events), list(self.fills)
        return s


class KatsuoLimitSim:
    """状態を持つ再現。海外の 1 分足の行と bitFlyer の 1 分足を受け取り、終わった取引の行を返す。モジュールの説明を参照。"""

    def __init__(self, *, fill_side: str, at_max: Optional[str] = None, foot_min: int = 15, design: str = "v03",
                 entry: str = "c", side_keep: str = "weak", vol_gate: bool = False,
                 vol_edges: Optional[tuple] = None, fill: str = "limit") -> None:
        self.fill_side = _in("fill_side", fill_side, FILL_SIDES)
        self.fill = _in("fill", fill, FILLS)
        if fill == "close" and design != "k1":
            raise ValueError("fill='close'(参照の形)は design='k1' だけ")
        self.design = _in("design", design, DESIGNS)
        self.foot_min = _in("foot_min", foot_min, FOOTS)
        if type(foot_min) is not int:
            raise ValueError(f"foot_min は {list(FOOTS)} のどれか: {foot_min!r}")
        self.entry = _in("entry", entry, ENTRIES)
        if type(vol_gate) is not bool:
            raise ValueError(f"vol_gate は True / False: {vol_gate!r}")
        if design == "v03":
            self.at_max = _in("at_max", at_max, AT_MAXES)
            if entry != "c" or side_keep != "weak" or vol_gate:
                raise ValueError("design='v03' は entry='c'・vol_gate=False だけ(side_keep は使わない)")
        else:
            if at_max is not None:
                raise ValueError("design='k1' は at_max を使わない(仕様 9: K1 の持ち高の機械)")
            self.at_max = None
            _in("side_keep", side_keep, SIDE_KEEPS)
            if foot_min not in K1_FEET[side_keep]:
                raise ValueError(f"side_keep={side_keep!r} の足は {list(K1_FEET[side_keep])} のどれか: {foot_min!r}")
            if side_keep == "strong" and vol_gate:
                raise ValueError("side_keep='strong'(1 分の組)は vol_gate を使わない(仕様 9 の走らせの表)")
        self.side_keep = side_keep
        self.vol_gate = vol_gate
        if vol_edges is not None:
            if len(vol_edges) != 2 or not all(math.isfinite(float(x)) for x in vol_edges) or not vol_edges[0] < vol_edges[1]:
                raise ValueError(f"vol_edges は (q1, q2) で q1 < q2: {vol_edges!r}")
            vol_edges = (float(vol_edges[0]), float(vol_edges[1]))
        elif vol_gate:
            raise ValueError("vol_gate=True には vol_edges(K1 の出力の境目)が要る")
        self.vol_edges = vol_edges
        self.foot_ns = foot_min * MIN_NS
        # 海外の足(カードの _bucket / _agg と同じ)
        self._refs: deque = deque()  # まだ使えるようになっていない行 (open_time, o, h, lo, c)
        self._last_ref_t: Optional[int] = None
        self._bucket: Optional[int] = None
        self._agg: Optional[list] = None
        self._line: Optional[float] = None  # 原典の lcprice(合図のある足でだけ更新)
        self._closes: deque = deque(maxlen=VOL_WINDOW + 1)  # 閉じた海外の足の終値(vol_prev 用)
        self._pending: Optional[dict] = None  # H3: 次の足の区切りで行動する合図(行動の時刻)
        self._out: list = []  # 足の区切りで閉じた取引の行(fill="close")。次の feed が返す
        # bitFlyer
        self._last_close: Optional[float] = None
        self._last_end: Optional[int] = None
        self._last_start: Optional[int] = None
        # 約定した持ち高と置いてある注文
        self._pos = 0.0
        self._trade: Optional[dict] = None
        self._orders: list = []
        # 記録
        self.signal_log: list = []  # (足の終わり T, 向き, 19 の枝, 24 の枝)。カードの signal_log と同じ形
        # 入りの注文ごと [種類 "ent1"(最良気配)/"ent2"(半値), 出した時刻 T, 量, 約定した足の終わり or None, 組の番号,
        #                  合図の時刻]
        self.order_log: list = []
        self._n_sets = 0
        self.action_log: list = []  # design="k1" の行動 (種類 "open"/"exit"/"doten", 時刻 T, 合図の向き)
        self.decisions = {"buy": 0, "sell": 0, "exit": 0, "skip_at_max_same": 0, "skip_at_max_opposite": 0,
                          "flip_at_max": 0, "no_price": 0, "k1_same_side": 0, "k1_same_side_resting": 0,
                          "k1_vol_gate_skip": 0, "k1_doten": 0}
        self.undecided_bars = 0  # 決まらない足の数(全体)

    # ------------------------------------------------------------------ 仕様 1: 入力
    def add_refs(self, rows) -> None:
        """海外の 1 分足の行 (open_time ns, 始値, 高値, 安値, 終値) を古い順に足す。使えるのは open_time + 60 秒から。
        既に受け取った bitFlyer の足の始まりまでに使えるようになっていたはずの行は拒む(遅れて渡すと先読みの逆が起きる)。"""
        for r in rows:
            t, o, h, lo, c = int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4])
            if self._last_ref_t is not None and t <= self._last_ref_t:
                raise ValueError(f"参照の行の時刻が増えていない: {t} <= {self._last_ref_t}")
            if self._last_start is not None and t + ROW_LAG_NS <= self._last_start:
                raise ValueError(f"参照の行 {t} は既に通した足 {self._last_start} より前に使えるようになっていた")
            if not all(math.isfinite(x) for x in (o, h, lo, c)):
                raise ValueError(f"参照の行 {t} の値段が有限でない")
            self._refs.append((t, o, h, lo, c))
            self._last_ref_t = t

    def feed(self, b) -> list:
        o, h, lo, c = float(b.open), float(b.high), float(b.low), float(b.close)
        if not (b.volume > 0) or not all(math.isfinite(x) for x in (o, h, lo, c)):
            return []  # 約定の無い足は約定にも P1 にも使わない(カード 4 の再現と同じ)【置いた形】
        start = int(b.start_time_ns)
        end = start + MIN_NS
        if self._last_start is not None and start <= self._last_start:
            raise ValueError(f"足の始まりが増えていない: {start} <= {self._last_start}")
        self._last_start = start
        self._advance(start)  # 仕様 2: 始まり以前に閉じた海外の足で注文を出す
        out, self._out = self._out, []
        if self._orders:
            out += self._bar(o, h, lo, c, start, end)
        self._last_close, self._last_end = c, end
        return out

    def finish(self) -> list:
        """期間の終わり: 持っている持ち高を最後の終値で閉じる(終わり方 = 期間の終わり)。"""
        out, self._out = self._out, []
        if self._trade is None:
            return out
        st = self._state()
        self._apply_fill(st, -self._trade["side"], abs(st.pos), self._last_close, self._last_end, EXIT_END, None)
        st.orders = []
        self._load(st)
        return out + [self._row(tr) for tr in st.closed]

    # ------------------------------------------------------------------ 仕様 2: 合図(カードの exposure と同じまとめ方)
    def _advance(self, s: int) -> None:
        while self._refs and self._refs[0][0] + ROW_LAG_NS <= s:
            t, o, h, lo, c = self._refs.popleft()
            end = t + ROW_LAG_NS
            b = (end - 1) // self.foot_ns * self.foot_ns  # この 1 分足が入る足の始まり(UTC の時計の区切り)
            if self._bucket is not None and b != self._bucket:
                self._close_bucket()
            if self._bucket is None:
                self._bucket, self._agg = b, [o, h, lo, c]
            else:
                a = self._agg
                a[1], a[2], a[3] = max(a[1], h), min(a[2], lo), c
        if self._bucket is not None and self._bucket + self.foot_ns <= s:
            self._close_bucket()

    def _close_bucket(self) -> None:
        o, h, lo, c = self._agg
        T = self._bucket + self.foot_ns
        self._bucket, self._agg = None, None
        vol = self._push_close(c)
        if self.design == "v03":
            self._decide(T, o, h, lo, c, vol)
        else:
            self._decide_k1(T, o, h, lo, c, vol)

    def _push_close(self, c: float) -> Optional[float]:
        """この足の終値を入れて、この足の vol_prev(K1 の vol_prev[この足 + 1]。モジュールの説明)を返す。"""
        self._closes.append(c)
        if len(self._closes) < VOL_WINDOW + 1:
            return None
        cs = list(self._closes)
        return math.fsum(abs(math.log(cs[k] / cs[k - 1])) * 1e4 for k in range(1, len(cs))) / VOL_WINDOW

    # ------------------------------------------------------------------ 仕様 9: design="k1"
    def _decide_k1(self, T: int, o: float, h: float, lo: float, c: float, vol: Optional[float]) -> None:
        sig, lc, _cs, strength, small, big, flipped = k1_signal(o, h, lo, c, self.side_keep == "weak")
        if sig != 0:
            self.signal_log.append((T, sig, small, big))
        act = None
        if sig != 0 and strength == self.side_keep:
            act = {"sig": sig, "T": T, "c_ov": c, "r": abs(c - lc) / c, "small": small, "big": big, "h1": flipped,
                   "strength": STRONG if strength == "strong" else WEAK, "vol": vol}
        pend, self._pending = self._pending, None
        if pend is not None:  # H3: 前の足の合図の行動を、この区切りで
            self._act_k1(T, pend)
        if act is not None:
            if self.entry != "a" and self._pos == 0:
                self._act_k1(T, act)  # 入り方 b・c の入り: 合図の時点
            else:
                self._pending = act  # 入り方 a、または降りる・ドテン・同じ向き: 次の区切りで

    def _act_k1(self, T: int, a: dict) -> None:
        if self._last_close is None:
            self.decisions["no_price"] += 1
            return
        if self._last_end > T:
            raise RuntimeError(f"先読み: 時刻 {T} の判定に、終わりが {self._last_end} の足の終値を使おうとした")
        d = a["sig"]
        pos = self._pos
        if pos * d > 0:
            self.decisions["k1_same_side"] += 1  # 同じ向き: 何もしない(置いた注文も残す)
            return
        if any(not od.reduce and od.side == d for od in self._orders):
            self.decisions["k1_same_side_resting"] += 1  # 同じ向きの入りの注文が残っている: 何もしない(直し 5)
            return
        if pos * d < 0:
            if self.side_keep == "strong":
                self.decisions["k1_doten"] += 1
                self.action_log.append(("doten", T, d))
                self._place_entry(T, d, a["c_ov"], a["r"], a)
            else:
                self.action_log.append(("exit", T, d))
                self._place_exit(T, a["c_ov"], XSIG_WEAK)
            return
        if self.vol_gate and tercile(a["vol"], self.vol_edges) != "high":
            self.decisions["k1_vol_gate_skip"] += 1  # 高い三分位のときだけ入る(降りる注文は門に関係なし)
            self._orders = [od for od in self._orders if od.reduce or od.side == d]  # 反対向きの入りは取り消す(直し 4)
            return
        self.action_log.append(("open", T, d))
        self._place_entry(T, d, a["c_ov"], a["r"], a)

    # ------------------------------------------------------------------ 仕様 2: design="v03"
    def _decide(self, T: int, o: float, h: float, lo: float, c: float, vol: Optional[float] = None) -> None:
        color, sig, tip, small, big = classify_detail(o, h, lo, c, small_gate_bp=SMALL_GATE_BP, big_gate_bp=BIG_GATE_BP)
        if color == 0:
            return
        if sig != 0:
            self._line = tip
            self.signal_log.append((T, sig, small, big))
        act = action(color, sig, self._pos, c, self._line)
        if act is None:
            return
        if self._last_close is None:
            self.decisions["no_price"] += 1  # 直前の bitFlyer の終値が無い(期間の頭)。注文を出さない【置いた形】
            return
        if self._last_end > T:
            raise RuntimeError(f"先読み: 時刻 {T} の判定に、終わりが {self._last_end} の足の終値を使おうとした")
        if act == "exit":
            self._place_exit(T, c, XSIG_WEAK if sig != 0 else XSIG_LINE)
        else:
            d = 1 if act == "buy" else -1
            self._place_entry(T, d, c, abs(c - tip) / c, {"T": T, "small": small, "big": big, "h1": False,
                                                          "strength": STRONG if color == d else WEAK, "vol": vol})

    # ------------------------------------------------------------------ 仕様 3-1: 入り
    def _place_entry(self, T: int, d: int, c_ov: float, r: float, a: dict) -> None:
        pos = self._pos
        if self.design == "v03" and abs(pos) >= SIZE_MAX:  # 原典 303・340 行を `<` と読む(仕様 3-1 の 28 行)
            if pos * d > 0:
                self.decisions["skip_at_max_same"] += 1  # 同じ向き: 注文をスルー(取り消しもしない。原典 320 行)
                return
            if self.at_max == "skip":
                self.decisions["skip_at_max_opposite"] += 1  # 反対の合図・コードのとおり(仕様 3-1 の 29 行)
                return
            self.decisions["flip_at_max"] += 1  # 反対の合図・L-024 のドテン
        self.decisions["buy" if d == 1 else "sell"] += 1
        self._orders = []  # 原典 304・341 行 cancelAll
        p1 = self._last_close
        p2 = p1 * (1.0 - d * r / 2.0)  # r = 先端までの比(仕様 3-1 の 2 本目)
        doten = abs(pos) if pos * d < 0 else 0.0
        if self.entry == "c":
            if doten:
                q1 = SIZE_DEF + doten  # ドテン(仕様 3-1: 0.5 + |持ち高|)
                after = SIZE_DEF
            else:
                q1 = min(SIZE_DEF, SIZE_MAX - abs(pos))
                after = abs(pos) + q1
            q2 = min(SIZE_DEF, SIZE_MAX - after)  # 上限で切る
            legs = (("ent1", q1, p1), ("ent2", q2, p2))
        else:  # 仕様 9: 量 1 の 1 本(k1 は持ち高 0 かドテンのときだけここに来る)
            q = (SIZE_MAX if doten else SIZE_MAX - abs(pos)) + doten
            legs = (("ent1", q, p1),) if self.entry == "a" else (("ent2", q, p2),)
        vol = a.get("vol")
        info = {"t_sig": a["T"], "small": a["small"], "big": a["big"], "r": r, "strength": a["strength"],
                "h1": a["h1"], "vol": vol, "tercile": tercile(vol, self.vol_edges)}
        sid = self._n_sets
        self._n_sets += 1
        for kind, q, px in legs:
            if q > 0:
                self.order_log.append([kind, T, q, None, sid, a["T"]])
                self._orders.append(_order(kind, d, q, px, None, False, T, info, len(self.order_log) - 1))
        if self.fill == "close":
            self._fill_now(T)

    # ------------------------------------------------------------------ 仕様 3-2: 降りる
    def _place_exit(self, T: int, c_ov: float, why: str) -> None:
        self.decisions["exit"] += 1
        self._orders = []  # 原典 415 行 cancelAll
        pos = self._pos
        d = 1 if pos > 0 else -1
        x = self._last_close
        u = x / c_ov  # 1 ドルを X に対する比にした幅(仕様 3-2 の 38 行)
        q = abs(pos)
        s = -d
        info = {"t_xsig": T, "xsig": why}
        self._orders = [_order("x_lim", s, q, x, None, True, T, info, None)]
        for kind, (tw, pw) in zip(("x_sl1", "x_sl2"), STOP_LIMITS):
            self._orders.append(_order(kind, s, q, x - d * pw * u, x - d * tw * u, True, T, info, None))
        self._orders.append(_order("x_sm", s, q, None, x - d * STOP_MARKET * u, True, T, info, None))
        if self.fill == "close":
            self._fill_now(T)

    def _fill_now(self, T: int) -> None:
        """参照の形(fill="close"): 置いた注文を、行動の時刻の直前の bitFlyer の終値で全部約定させる。"""
        st = self._state()
        for od in list(st.orders):
            if any(x is od for x in st.orders):
                self._fill(st, od, self._last_close, T, EXIT_CLOSE)
        self._load(st)
        self._out += [self._row(tr) for tr in st.closed]

    # ------------------------------------------------------------------ 状態の出し入れ
    def _state(self) -> _St:
        s = _St()
        s.pos, s.trade = self._pos, (None if self._trade is None else dict(self._trade))
        s.orders = [o.copy() for o in self._orders]
        s.closed, s.events, s.fills = [], [], []
        return s

    def _load(self, st: _St) -> None:
        self._pos, self._trade, self._orders = st.pos, st.trade, st.orders
        for rec, t in st.fills:
            if rec is not None:
                self.order_log[rec][3] = t

    # ------------------------------------------------------------------ 仕様 3: 約定の判定
    @staticmethod
    def _thr(od: _Order, up: bool) -> Optional[float]:
        """上がる側(up)/ 下がる側でこの注文が起きる値段。起きない側なら None。"""
        if od.trig is not None and not od.armed:  # 引き金: 買いのストップは上抜け、売りのストップは下抜け
            return od.trig if (od.side == 1) == up else None
        return od.price if (od.side == -1) == up else None  # 指値: 売りは上で、買いは下で約定

    def _leg(self, st: _St, up: bool, ext: float, t_end: int, head: bool = False) -> None:
        while True:
            best = None
            for i, od in enumerate(st.orders):
                thr = self._thr(od, up)
                if thr is None or not (ext > thr if up else ext < thr):  # 等号なし
                    continue
                key = (thr if up else -thr, i)
                if best is None or key < best[0]:
                    best = (key, od, thr)
            if best is None:
                return
            _, od, thr = best
            if od.trig is not None and not od.armed:
                st.events.append(("trig", od.kind, thr))
                if od.price is None:  # ストップ成行: 足の中は引き金の 1 円向こう(売り −1・買い +1)、足の頭は始値
                    self._fill(st, od, ext if head else thr + od.side, t_end)
                else:
                    od.armed = True  # ストップ指値: 指値として残る(post-only)
            else:
                st.events.append(("fill", od.kind, thr))
                self._fill(st, od, thr, t_end)

    def _fill(self, st: _St, od: _Order, px: float, t_end: int, reason: Optional[str] = None) -> None:
        st.orders = [x for x in st.orders if x is not od]
        st.fills.append((od.rec, t_end))
        if od.reduce:  # 全量・reduce-only: 1 本約定したら残りの降りる注文は無くなる
            st.orders = [x for x in st.orders if not x.reduce]
            self._apply_fill(st, od.side, abs(st.pos), px, t_end, reason or _EXIT_REASON[od.kind], od.info)
        else:
            self._apply_fill(st, od.side, od.qty, px, t_end, EXIT_DOTEN, od.info)

    # ------------------------------------------------------------------ 仕様 5: 損益と取引
    def _apply_fill(self, st: _St, side: int, qty: float, px: float, t_end: int, reason: str,
                    info: Optional[dict]) -> None:
        tr = st.trade
        if tr is not None and tr["side"] != side:
            cq = min(qty, tr["size"])
            tr["pnl"] += tr["side"] * (px / tr["avg"] - 1.0) * 1e4 * cq  # 約定ごと(仕様 5)
            tr["size"] -= cq
            qty -= cq
            st.pos += side * cq
            if tr["size"] == 0:
                tr["exit_ns"], tr["exit_price"], tr["exit_reason"] = t_end, px, reason
                xi = info if (info is not None and "xsig" in info) else {}  # 降りる注文で閉じたときだけ
                tr["xsig"], tr["t_xsig"] = xi.get("xsig"), xi.get("t_xsig")
                st.closed.append(tr)
                st.trade = tr = None
        if qty > 0:
            if tr is None:
                st.trade = {"entry_ns": t_end, "side": side, "size": qty, "max_size": qty, "avg": px, "pnl": 0.0,
                            "und": 0, "small": info["small"], "big": info["big"], "r": info["r"],
                            "t_sig": info["t_sig"], "strength": info["strength"], "h1": info["h1"],
                            "vol": info["vol"], "tercile": info["tercile"]}
            else:
                tr["avg"] = (tr["avg"] * tr["size"] + px * qty) / (tr["size"] + qty)  # 約定の量で重みを付けた平均
                tr["size"] += qty
                tr["max_size"] = max(tr["max_size"], tr["size"])
            st.pos += side * qty
        if abs(st.pos) > SIZE_MAX:
            raise RuntimeError(f"持ち高が上限を越えた: {st.pos}")

    @staticmethod
    def _row(tr: dict) -> dict:
        return {"entry_ns": tr["entry_ns"], "exit_ns": tr["exit_ns"], "side": tr["side"], "max_size": tr["max_size"],
                "entry_price": tr["avg"], "exit_price": tr["exit_price"], "exit_reason": tr["exit_reason"],
                "pnl_bp": tr["pnl"], "undecided": tr["und"], "small": tr["small"], "big": tr["big"], "r": tr["r"],
                "signal_ns": tr["t_sig"], "strength": tr["strength"], "h1": tr["h1"], "vol_prev": tr["vol"],
                "vol_tercile": tr["tercile"], "exit_signal": tr["xsig"],
                "exit_signal_ns": tr["t_xsig"]}

    # ------------------------------------------------------------------ 仕様 4: 1 本の足
    def _path(self, st0: _St, up_first: bool, o: float, h: float, lo: float, t_end: int) -> _St:
        st = st0.copy()
        for up in (True, False):  # 足の頭(上がる側 → 下がる側)
            self._leg(st, up, o, t_end, head=True)
        for up in ((True, False) if up_first else (False, True)):
            self._leg(st, up, h if up else lo, t_end)
        return st

    @staticmethod
    def _value(st: _St, c: float) -> float:
        v = math.fsum(tr["pnl"] for tr in st.closed)
        tr = st.trade
        if tr is not None:
            v += tr["pnl"] + tr["side"] * (c / tr["avg"] - 1.0) * 1e4 * tr["size"]
        return v

    def _bar(self, o: float, h: float, lo: float, c: float, start: int, t_end: int) -> list:
        st0 = self._state()
        a = self._path(st0, True, o, h, lo, t_end)
        b = self._path(st0, False, o, h, lo, t_end)
        if a.events == b.events:
            st, und = a, False
        else:
            und = True
            self.undecided_bars += 1
            va, vb = self._value(a, c), self._value(b, c)
            if va == vb:
                st = a if (h - o) <= (o - lo) else b  # 始値に近い方の端へ先に行く道
            elif self.fill_side == "good":
                st = a if va > vb else b
            else:
                st = a if va < vb else b
        if und:
            for tr in st.closed:
                tr["und"] += 1
            if st.trade is not None:
                st.trade["und"] += 1
        self._load(st)
        return [self._row(tr) for tr in st.closed]


__all__ = ["TICK_EPS", "tick_down", "tick_up", "EXIT_CLOSE", "FILLS", "DESIGNS", "ENTRIES", "K1_FEET", "SIDE_KEEPS", "VOL_WINDOW", "k1_signal", "tercile", "STRONG", "WEAK", "XSIG_LINE", "XSIG_WEAK", "AT_MAXES", "EXIT_DOTEN", "EXIT_END", "EXIT_LIMIT", "EXIT_SL1", "EXIT_SL2", "EXIT_SM", "FILL_SIDES",
           "KatsuoLimitSim", "SIZE_DEF", "SIZE_MAX", "STOP_LIMITS", "STOP_MARKET", "action"]

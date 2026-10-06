"""帳簿のツール: 約定の列から、約定ごとの表・取引ごとの表・まとめを作る(L-741・L-747・L-749・L-750・L-755・L-756)。

オーナーの逐語:
- L-754「**私がしてほしいの決まりを足すんじゃなくて、この計算が確実にできるツールを作ることと、そのツールが必ず使われる仕組みです。**」
- L-741「**売買価格差×建玉=何円が実際の損益やのにな**」(損益は値段の差 × 建玉だけ。手数料は含まない)
- L-746「**0.001以下は切り捨て**」/ L-756「**3. 0.001**」(量は 0.001 BTC の刻み。刻みでない量の約定は拒む)
- L-749「**ならオッケー**」(取引の回数 = 往復。建玉 0 → 0 で 1 回。段を足しても同じ取引)
- L-750「**ドテンは2回じゃなくて1回とまだ途中やろ**」
- L-755「**3.合ってる**」(保有時間 = 最初の約定から建玉 0 まで)
- L-756「**1.a 2.よい 3. 0.001**」(ドル建ての損益は確定時刻の USDJPY で円に。USDT は USD とみなす)

計算(平均の原価法。ここで正確な分数で計算し、その値を出す):
- 値段・量・USDJPY は `Decimal(str(x))`(浮動小数の最短の 10 進の文字列)で受け、それを分数(`fractions.Fraction`、
  Decimal から誤差なく移る)にして計算する。途中で一度も丸めない。
  (リードの直し 1 は「Decimal で計算」。Decimal で割り算を 80 桁で丸めて計算した版を、独立に書いた分数の手計算と
  乱数の約定列 2 万本で突き合わせたところ、正しい合計が有限小数の閉じた取引 40,276 本のうち 1,925 本が 1e-73 円ほど
  ずれた。ちょうど 0 の取引が 0 にならない形なので、計算は分数で行い、Decimal は受け取りと出力に使う)
- 建玉と、建玉の原価の合計 C(= 建てた約定の 値段 × 量 の和。平均の建値 = C ÷ |建玉|)を持つ。
- 建てる向きの約定: 建玉 += 量、C += 値段 × 量。
- 減らす向きの約定: 減らした量 c = min(量, |建玉|)。減らす原価 = C × c ÷ |建玉|(全部閉じるときは C)。
  確定損益 = 向き × (値段 × c − 減らす原価) = (値段 − 平均の建値) × c × 向き。
  ドテン(量 > |建玉|)は閉じる分 |建玉| と新しく建てる分(量 − |建玉|、建値はその約定の値段)に分ける。
- ドル建ては確定損益(ドル)× 確定時刻の USDJPY(`FxRates.rate("USDJPY", t)`、その時刻以前の最後の相場)。
  相場が無ければ止まる(1 とみなさない)。USDT は USD とみなす。
- 2 つの計算の突き合わせ: 同じ約定を口座(`bot.bt.portfolio.account.MarginAccount`、浮動小数)にも通し、
  約定ごとの確定損益(円)の差が 1e-6 円を超えたら止める。建玉の差が 1e-9 BTC を超えたときも止める。

出力の数(建玉・平均の建値・損益・最大の建玉)は 10 進の文字列(例 "5"・"-1"・"0.05")。ちょうど 0 は "0"。
有限小数で表せる値は全桁そのまま(丸めない)。閉じた取引の損益 = 向き × (決済の 値段 × 量 の和 − 建ての 値段 × 量 の和)
(円建て)は必ず有限小数なので、円建ての閉じた取引の損益とまとめの損益の合計は常に式どおりの値。
有限小数で表せない値(割り切れない平均の建値と、その平均での一部決済の損益、それを含む途中の取引の損益・累計、
ドル建てで違う相場の一部決済を含む取引)だけは、出力の文字列にするときに 1e-12 の位で丸める(偶数への丸め)。
検査のツールは同じ帳簿のツールで計算し直し、文字列で突き合わせる。

`bot.bt.report.trades.round_trips`(建ての分と決済の約定の組ごとに 1 取引と数える FIFO)は使わない。

取引の区切り:
- 建玉 0 から 0 でなくなった約定で取引が始まり、建玉が 0 になった約定で閉じる。
- ドテン(1 つの約定で建玉の向きが変わる)は、その約定で閉じた側が 1 取引(その約定の確定損益はこちらに入る)、
  残りは同じ約定から始まる新しい取引(途中)として続く。新しい取引ではその約定が段の 1 つ目。
- データの終わりで建玉が 0 でない取引は「途中」。閉じた取引の数・損益の合計に入れず、別に数える。
- 段の数 = その取引の向き(買いで建てたなら買い)の約定の数。

約定の入力は 1 行 = {"t_ns": int, "side": "buy"|"sell", "qty": 数, "px": 数, "ccy": "JPY"|"USD"|"USDT"}。
1 つの列は 1 つの銘柄で、通貨はそろっていること。時刻は減らないこと。量は 0.001 BTC の倍数であること。

出力:
- 約定ごとの表 `fills`: i・t_ns・side・qty・px・ccy(入力のまま)・position_after(その後の建玉)・
  avg_px_after(その後の平均の建値。建玉 0 なら None)・pnl_jpy(今回分の確定損益、円)・pnl_jpy_cum(累計)・
  trade(この約定が属する取引。ドテンなら閉じた側)・opens_trade(この約定で始まった取引。無ければ None)
- 取引ごとの表 `trades`: first_t_ns・last_t_ns・direction(long / short)・levels(段の数)・max_position(最大の建玉)・
  hold_ns(最初の約定から建玉 0 まで。途中は None)・pnl_jpy(確定損益、円。途中はそこまでの分)・fills・
  status(closed / open)。途中の取引には position・avg_px(データの終わりの建玉と平均の建値)も付く
- まとめ `summary`: fill_count(約定の数)・closed_trades(閉じた取引の数)・pnl_jpy(閉じた取引の損益の合計、円)・
  open_trades(途中の取引の数)・trades(取引ごとの表から TRADE_KEYS の 7 つの欄: 最初の約定の時刻・最後の約定の時刻・
  段の数・最大の建玉・保有時間・損益・状態)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
from typing import Mapping, Optional, Sequence

from bot.bt.core import FillNotice
from bot.bt.costs import CostSchedule, FxPoint, FxRateMissingError, FxRates
from bot.bt.orders import Product
from bot.bt.orders.errors import ExecutionModelError
from bot.bt.portfolio.account import MarginAccount

from .sizing import MARGIN_JPY, STEP_BTC

ACCOUNT_CCY = "JPY"
FILL_CCYS = ("JPY", "USD", "USDT")
SIDES = ("buy", "sell")
FX_PAIR = "USDJPY"
SUMMARY_KEYS = ("fill_count", "closed_trades", "pnl_jpy", "open_trades", "trades")
TRADE_KEYS = ("first_t_ns", "last_t_ns", "levels", "max_position", "hold_ns", "pnl_jpy", "status")
PNL_TOL_JPY = 1e-6  # 帳簿の計算と口座の計算の、約定ごとの確定損益の差の上限(円)
POS_TOL_BTC = 1e-9  # 同じく建玉の差の上限(BTC)
REL_TOL = 1e-12  # 口座の浮動小数の誤差は扱った値の大きさに比例するので、大きい値ではこの割合を上限にする
OUT_PLACES = 12  # 有限小数で表せない値を出力の文字列にするときの位(1e-12)


class LedgerError(ValueError):
    """帳簿のツールが受け付けない入力、または計算を続けられない状態(文は日本語)。"""


@dataclass
class Ledger:
    fills: list = field(default_factory=list)  # 約定ごとの表
    trades: list = field(default_factory=list)  # 取引ごとの表(閉じた / 途中)
    summary: dict = field(default_factory=dict)  # まとめ(SUMMARY_KEYS)


def _terminating(x: Fraction) -> int | None:
    """x が有限小数なら、分母を割り切る最小の 10 の冪の指数。そうでなければ None。"""
    d, k2, k5 = x.denominator, 0, 0
    while d % 2 == 0:
        d //= 2
        k2 += 1
    while d % 5 == 0:
        d //= 5
        k5 += 1
    return max(k2, k5) if d == 1 else None


def dec_str(x: Fraction | None) -> str | None:
    """分数を 10 進の文字列に(指数を使わない。ちょうど 0 は "0"、末尾の 0 は落とす)。

    有限小数で表せる値は全桁そのまま。表せない値は 1e-12 の位で偶数への丸め(モジュールの説明を参照)。
    """
    if x is None:
        return None
    if x == 0:
        return "0"
    k = _terminating(x)
    if k is not None:
        n = x.numerator * 10 ** k // x.denominator  # 割り切れる: 全桁そのまま
    else:
        k = OUT_PLACES
        n = round(x * 10 ** k)  # Fraction の round は偶数への丸め
    # 整数 n × 10^-k を文字列に(Decimal の文脈の桁数で丸めないよう、整数の文字列から組み立てる)
    digits = str(abs(n)).rjust(k + 1, "0")
    out = digits if k == 0 else digits[:-k] + "." + digits[-k:]
    if "." in out:
        out = out.rstrip("0").rstrip(".")
    if out == "0":
        return "0"
    return ("-" if n < 0 else "") + out


def _frac(v: object) -> Fraction:
    """`Decimal(str(v))` を誤差なく分数に。"""
    return Fraction(Decimal(str(v)))


def _num(i: int, name: str, v: object) -> Fraction:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)) or float(v) <= 0:
        raise LedgerError(f"約定 {i} の {name} は 0 より大きい有限の数: {v!r}")
    return _frac(v)


def _check_fills(fills: Sequence[Mapping]) -> str:
    ccy = None
    last_t = None
    for i, f in enumerate(fills):
        if not isinstance(f, Mapping):
            raise LedgerError(f"約定 {i} は辞書で渡す")
        t = f.get("t_ns")
        if type(t) is not int:
            raise LedgerError(f"約定 {i} の t_ns は ns の整数: {t!r}")
        if last_t is not None and t < last_t:
            raise LedgerError(f"約定 {i} の時刻 {t} が前の約定 {last_t} より前(時刻の順に渡す)")
        last_t = t
        if f.get("side") not in SIDES:
            raise LedgerError(f"約定 {i} の side は buy / sell: {f.get('side')!r}")
        q = _num(i, "qty", f.get("qty"))
        if q % _frac(STEP_BTC) != 0:
            raise LedgerError(f"約定 {i} の量 {f.get('qty')!r} が 0.001 BTC の刻みでない(L-746・L-756)")
        _num(i, "px", f.get("px"))
        c = f.get("ccy")
        if c not in FILL_CCYS:
            raise LedgerError(f"約定 {i} の ccy は {FILL_CCYS} のどれか: {c!r}")
        if ccy is None:
            ccy = c
        elif c != ccy:
            raise LedgerError(f"約定 {i} の通貨 {c} が列の通貨 {ccy} と違う(1 つの列は 1 つの銘柄)")
    return ccy or ACCOUNT_CCY


def _fx_table(fx: object) -> Optional[FxRates]:
    if fx is None:
        return None
    if type(fx) is FxRates:
        return fx
    try:
        rows = list(fx)  # type: ignore[call-overload]
    except TypeError:
        raise LedgerError(f"fx は FxRates か、FxPoint / {{t_ns, pair, rate}} の列で渡す(受け取ったのは {type(fx).__name__})") \
            from None
    pts = []
    for k, p in enumerate(rows):
        if type(p) is FxPoint:
            pts.append(p)
            continue
        if not isinstance(p, Mapping) or not {"t_ns", "pair", "rate"} <= set(p):
            raise LedgerError(f"為替の {k} 行目は FxPoint か {{t_ns, pair, rate}} の辞書で渡す")
        try:
            pts.append(FxPoint(time_ns=p["t_ns"], pair=p["pair"], rate=p["rate"]))
        except ExecutionModelError:
            raise LedgerError(f"為替の {k} 行目が読めない(t_ns は ns の整数・pair は 6 文字の大文字・rate は 0 より大きい"
                              f"有限の数): {dict(p)!r}") from None
    try:
        return FxRates(pts)
    except ExecutionModelError:
        raise LedgerError("為替の表を作れない(行は FxPoint で渡す)") from None


def _usdjpy(fxr: Optional[FxRates], i: int, t: int) -> Fraction:
    if fxr is None:
        raise LedgerError(f"約定 {i}(時刻 {t})の確定損益を円にする USDJPY の相場が渡されていない(1 とみなさない。L-756)")
    try:
        r = fxr.rate(FX_PAIR, t)
    except FxRateMissingError:
        raise LedgerError(f"約定 {i}(時刻 {t})の確定損益を円にする USDJPY の相場が無い(その時刻以前の相場が要る。"
                          f"1 とみなさない。L-756)") from None
    return _frac(r)


def _account(quote_ccy: str, fx: Optional[FxRates]) -> MarginAccount:
    # 突き合わせの相手。口座が損益の計算に使うのは quote_ccy と margin だけ。tick・min_qty・qty_step は apply_fill が
    # 見ない(量の刻みはこの帳簿が _check_fills で見る)。cash は損益に入らない(20 万円)。
    product = Product(symbol="BTC", venue="road", tick=1e-8, min_qty=0.001, qty_step=0.001,
                      quote_ccy=quote_ccy, margin=True)
    costs = CostSchedule(maker_rate=0.0, taker_rate=0.0, source="帳簿のツール: 損益は値段の差 × 建玉だけ(L-741)")
    return MarginAccount(product=product, currency=ACCOUNT_CCY, cash=float(MARGIN_JPY), leverage=1.0,
                         liquidation=None, mark="last_trade", costs=costs, fx=fx, reference=None, open_orders=None)


def _sign(x) -> int:
    return (x > 0) - (x < 0)


def _new_trade(t: int, i: int, pos: Fraction) -> dict:
    return {"first_t_ns": t, "last_t_ns": t, "direction": "long" if pos > 0 else "short", "levels": 1,
            "max_position": abs(pos), "pnl_jpy": Fraction(0), "fills": [i]}


def book(fills: Sequence[Mapping], fx: object = None) -> Ledger:
    """約定の列から帳簿を作る。fx: ドル建てのときの USDJPY(`FxRates` か `FxPoint` / {t_ns, pair, rate} の列)。

    受け付けない入力・相場が無い・口座の計算と合わないときは `LedgerError`(日本語の文)で止まる。
    """
    fills = list(fills)
    ccy = _check_fills(fills)
    usd = ccy in ("USD", "USDT")
    quote = "USD" if usd else ccy  # L-756「**2.よい**」: USDT は USD とみなす
    fxr = _fx_table(fx)
    try:
        acct = _account(quote, fxr)
    except ExecutionModelError:
        raise LedgerError("突き合わせの口座を作れない(帳簿のツールの作りの誤り)") from None
    out = Ledger()
    cur: Optional[dict] = None
    pos = Fraction(0)  # 建玉(買いが +)
    cost = Fraction(0)  # 建玉の原価の合計 C(値段 × 量 の和、正)
    cum = Fraction(0)
    for i, f in enumerate(fills):
        t, side = f["t_ns"], f["side"]
        q, px = _frac(f["qty"]), _frac(f["px"])
        s = 1 if side == "buy" else -1
        before = pos
        pnl = Fraction(0)
        if pos == 0 or _sign(pos) == s:
            pos += s * q
            cost += px * q
        else:
            d = _sign(pos)
            c = min(q, abs(pos))
            removed = cost * c / abs(pos)  # 全部閉じるときは cost そのもの
            pnl = d * (px * c - removed)
            if usd:
                pnl = pnl * _usdjpy(fxr, i, t)
            rest = q - c
            if rest > 0:  # ドテン: 閉じる分 |建玉| と新しく建てる分 rest に分ける
                pos, cost = s * rest, px * rest
            else:
                pos += s * c
                cost = Fraction(0) if pos == 0 else cost - removed
        cum += pnl
        avg = None if pos == 0 else cost / abs(pos)
        _cross_check(acct, i, f, pnl, pos)

        s_before, s_after = _sign(before), _sign(pos)
        opens = None
        if s_before == 0:
            # 建玉 0 から建てる: 新しい取引
            cur = _new_trade(t, i, pos)
            out.trades.append(cur)
            trade_no = opens = len(out.trades) - 1
        else:
            assert cur is not None
            trade_no = len(out.trades) - 1
            cur["last_t_ns"] = t
            cur["fills"].append(i)
            cur["pnl_jpy"] += pnl
            if s == s_before:
                cur["levels"] += 1  # 建てる向きの約定 = 段
            if s_after == s_before:
                cur["max_position"] = max(cur["max_position"], abs(pos))
            if s_after != s_before:
                # 建玉 0、またはドテン: この約定で閉じる
                cur["status"] = "closed"
                cur["hold_ns"] = t - cur["first_t_ns"]
                cur = None
                if s_after != 0:
                    # ドテン: 残りが同じ約定から新しい取引(途中)として続く
                    cur = _new_trade(t, i, pos)
                    out.trades.append(cur)
                    opens = len(out.trades) - 1
        out.fills.append({"i": i, "t_ns": t, "side": side, "qty": f["qty"], "px": f["px"], "ccy": ccy,
                          "position_after": dec_str(pos), "avg_px_after": dec_str(avg),
                          "pnl_jpy": dec_str(pnl), "pnl_jpy_cum": dec_str(cum), "trade": trade_no,
                          "opens_trade": opens})
    for tr in out.trades:
        if "status" not in tr:
            # データの終わりで建玉が 0 でない: 途中
            tr["status"] = "open"
            tr["hold_ns"] = None
            tr["position"] = dec_str(pos)
            tr["avg_px"] = dec_str(cost / abs(pos))
    closed = [tr for tr in out.trades if tr["status"] == "closed"]
    total = sum((tr["pnl_jpy"] for tr in closed), Fraction(0))
    for tr in out.trades:
        tr["max_position"] = dec_str(tr["max_position"])
        tr["pnl_jpy"] = dec_str(tr["pnl_jpy"])
    out.summary = {"fill_count": len(fills), "closed_trades": len(closed), "pnl_jpy": dec_str(total),
                   "open_trades": sum(1 for tr in out.trades if tr["status"] == "open"),
                   "trades": [{k: tr[k] for k in TRADE_KEYS} for tr in out.trades]}
    return out


def _cross_check(acct: MarginAccount, i: int, f: Mapping, pnl: Fraction, pos: Fraction) -> None:
    """同じ約定を口座に通し、確定損益(円)と建玉を帳簿の計算と突き合わせる。離れていたら止める。"""
    r0 = acct.realized_account
    try:
        acct.apply_fill(FillNotice(client_order_id=f"road-{i}", price=float(f["px"]), size=float(f["qty"]),
                                   side=f["side"], venue_time_ns=f["t_ns"], fee=0.0))
    except FxRateMissingError:
        raise LedgerError(f"約定 {i}(時刻 {f['t_ns']})で口座が円にする相場を見つけられない(1 とみなさない)") from None
    except ExecutionModelError:
        raise LedgerError(f"約定 {i} を口座が受け付けない(帳簿のツールの作りの誤り)") from None
    acct_pnl = acct.realized_account - r0
    # 口座は浮動小数なので、累計や値段が大きいほど誤差が大きくなる。上限は 1e-6 円か、口座が扱った値の大きさの 1e-12 倍の大きい方。
    tol = max(PNL_TOL_JPY, REL_TOL * max(abs(acct.realized_account), abs(r0), abs(float(pnl)),
                                          abs(float(f["px"])) * abs(float(f["qty"]))))
    if abs(acct_pnl - float(pnl)) > tol:
        raise LedgerError(f"約定 {i} の確定損益が、帳簿の計算 {dec_str(pnl)} 円と口座の計算 {acct_pnl!r} 円で "
                          f"{tol} 円より離れている(2 つの計算が合わない)")
    if abs(acct.position - float(pos)) > POS_TOL_BTC:
        raise LedgerError(f"約定 {i} の後の建玉が、帳簿の計算 {dec_str(pos)} と口座の計算 {acct.position!r} で "
                          f"{POS_TOL_BTC} BTC より離れている(2 つの計算が合わない)")

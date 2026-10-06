"""帳簿のツール: 約定の列を口座(`bot.bt.portfolio.account.MarginAccount`)に通し、約定ごとの表・取引ごとの表・
まとめを作る(L-741・L-747・L-749・L-750・L-755・L-756)。

オーナーの逐語:
- L-741「**売買価格差×建玉=何円が実際の損益やのにな**」(損益は口座の平均の建値で計算した確定損益。手数料は含まない)
- L-749「**ならオッケー**」(取引の回数 = 往復。建玉 0 → 0 で 1 回。段を足しても同じ取引)
- L-750「**ドテンは2回じゃなくて1回とまだ途中やろ**」
- L-755「**3.合ってる**」(保有時間 = 最初の約定から建玉 0 まで)
- L-756「**1.a 2.よい 3. 0.001**」(ドル建ての損益は確定時刻の USDJPY で円に。USDT は USD とみなす)

損益・建玉・平均の建値・建玉 0 の判定は全部口座が出したものを読む(ここで計算し直さない)。
`bot.bt.report.trades.round_trips`(建ての分と決済の約定の組ごとに 1 取引と数える FIFO)は使わない。

取引の区切り:
- 建玉 0 から 0 でなくなった約定で取引が始まり、建玉が 0 になった約定で閉じる。
- ドテン(1 つの約定で建玉の向きが変わる)は、その約定で閉じた側が 1 取引(その約定の確定損益はこちらに入る)、
  残りは同じ約定から始まる新しい取引(途中)として続く。新しい取引ではその約定が段の 1 つ目。
- データの終わりで建玉が 0 でない取引は「途中」。閉じた取引の数・損益の合計に入れず、別に数える。
- 段の数 = その取引の向き(買いで建てたなら買い)の約定の数。

ドル建て(USD・USDT): 確定損益は確定時刻(その約定の時刻)の USDJPY で円にする(口座が `FxRates.convert` で行う)。
相場が無ければ `FxRateMissingError` で止まる(1 とみなさない)。USDT は口座に USD として渡す。

約定の入力は 1 行 = {"t_ns": int, "side": "buy"|"sell", "qty": 数, "px": 数, "ccy": "JPY"|"USD"|"USDT"}。
1 つの列は 1 つの銘柄で、通貨はそろっていること。時刻は減らないこと。

出力:
- 約定ごとの表 `fills`: i・t_ns・side・qty・px・ccy・position_after(その後の建玉)・avg_px_after(その後の平均の建値)・
  pnl_jpy(今回分の確定損益、円)・pnl_jpy_cum(累計)・trade(この約定が属する取引。ドテンなら閉じた側)・
  opens_trade(この約定で始まった取引。無ければ None)
- 取引ごとの表 `trades`: first_t_ns・last_t_ns・direction(long / short)・levels(段の数)・max_position(最大の建玉)・
  hold_ns(最初の約定から建玉 0 まで。途中は None)・pnl_jpy(確定損益、円。途中はそこまでの分)・fills・
  status(closed / open)。途中の取引には position・avg_px(データの終わりの建玉と平均の建値)も付く
- まとめ `summary`: closed_trades(閉じた取引の数)・pnl_jpy(閉じた取引の損益の合計、円)・open_trades(途中の取引の数)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

from bot.bt.core import FillNotice
from bot.bt.costs import CostSchedule, FxPoint, FxRates
from bot.bt.orders import Product
from bot.bt.portfolio.account import MarginAccount

from .sizing import MARGIN_JPY

ACCOUNT_CCY = "JPY"
FILL_CCYS = ("JPY", "USD", "USDT")
SIDES = ("buy", "sell")
SUMMARY_KEYS = ("closed_trades", "pnl_jpy", "open_trades")


class LedgerError(ValueError):
    """帳簿のツールが受け付けない入力。"""


@dataclass
class Ledger:
    fills: list = field(default_factory=list)  # 約定ごとの表
    trades: list = field(default_factory=list)  # 取引ごとの表(閉じた / 途中)
    summary: dict = field(default_factory=dict)  # まとめ: 閉じた取引の数・損益の合計(円)・途中の取引の数


def _num(i: int, name: str, v: object) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)) or float(v) <= 0:
        raise LedgerError(f"約定 {i} の {name} は 0 より大きい有限の数: {v!r}")
    return float(v)


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
        _num(i, "qty", f.get("qty"))
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
    pts = []
    for p in fx:  # type: ignore[union-attr]
        if type(p) is FxPoint:
            pts.append(p)
        elif isinstance(p, Mapping):
            pts.append(FxPoint(time_ns=p["t_ns"], pair=p["pair"], rate=p["rate"]))
        else:
            raise LedgerError(f"fx は FxRates か、FxPoint / {{t_ns, pair, rate}} の列: {type(p).__name__}")
    return FxRates(pts)


def _account(quote_ccy: str, fx: Optional[FxRates]) -> MarginAccount:
    # 口座が損益の計算に使うのは quote_ccy と margin だけ。tick・min_qty・qty_step は約定を受け付けるかの検査に
    # 使われない(apply_fill は見ない)ので、量の刻み 0.001(L-746)を置く。cash は損益に入らない(20 万円)。
    product = Product(symbol="BTC", venue="road", tick=1e-8, min_qty=0.001, qty_step=0.001,
                      quote_ccy=quote_ccy, margin=True)
    costs = CostSchedule(maker_rate=0.0, taker_rate=0.0, source="帳簿のツール: 損益は値段の差 × 建玉だけ(L-741)")
    return MarginAccount(product=product, currency=ACCOUNT_CCY, cash=float(MARGIN_JPY), leverage=1.0,
                         liquidation=None, mark="last_trade", costs=costs, fx=fx, reference=None, open_orders=None)


def _sign(x: float) -> int:
    return (x > 0) - (x < 0)


def book(fills: Sequence[Mapping], fx: object = None) -> Ledger:
    """約定の列から帳簿を作る。fx: ドル建てのときの USDJPY(`FxRates` か `FxPoint` / {t_ns, pair, rate} の列)。"""
    fills = list(fills)
    ccy = _check_fills(fills)
    quote = "USD" if ccy == "USDT" else ccy  # L-756「**2.よい**」: USDT は USD とみなす
    acct = _account(quote, _fx_table(fx))
    out = Ledger()
    cur: Optional[dict] = None
    for i, f in enumerate(fills):
        t, side, qty, px = f["t_ns"], f["side"], float(f["qty"]), float(f["px"])
        before = acct.position
        r0 = acct.realized_account
        acct.apply_fill(FillNotice(client_order_id=f"road-{i}", price=px, size=qty, side=side,
                                   venue_time_ns=t, fee=0.0))
        after = acct.position
        pnl = acct.realized_account - r0
        s_before, s_after = _sign(before), _sign(after)
        opens = None
        if s_before == 0:
            # 建玉 0 から建てる: 新しい取引
            cur = {"first_t_ns": t, "last_t_ns": t, "direction": "long" if s_after > 0 else "short",
                   "levels": 1, "max_position": abs(after), "pnl_jpy": 0.0, "fills": [i]}
            out.trades.append(cur)
            trade_no = opens = len(out.trades) - 1
        else:
            assert cur is not None
            trade_no = len(out.trades) - 1
            cur["last_t_ns"] = t
            cur["fills"].append(i)
            cur["pnl_jpy"] += pnl
            if (1 if side == "buy" else -1) == s_before:
                cur["levels"] += 1  # 建てる向きの約定 = 段
            if s_after == s_before:
                cur["max_position"] = max(cur["max_position"], abs(after))
            if s_after != s_before:
                # 建玉 0、またはドテン: この約定で閉じる
                cur["status"] = "closed"
                cur["hold_ns"] = t - cur["first_t_ns"]
                cur = None
                if s_after != 0:
                    # ドテン: 残りが同じ約定から新しい取引(途中)として続く
                    cur = {"first_t_ns": t, "last_t_ns": t, "direction": "long" if s_after > 0 else "short",
                           "levels": 1, "max_position": abs(after), "pnl_jpy": 0.0, "fills": [i]}
                    out.trades.append(cur)
                    opens = len(out.trades) - 1
        out.fills.append({"i": i, "t_ns": t, "side": side, "qty": qty, "px": px, "ccy": ccy,
                          "position_after": after, "avg_px_after": acct.avg_px,
                          "pnl_jpy": pnl, "pnl_jpy_cum": acct.realized_account, "trade": trade_no,
                          "opens_trade": opens})
    for tr in out.trades:
        if "status" not in tr:
            # データの終わりで建玉が 0 でない: 途中
            tr["status"] = "open"
            tr["hold_ns"] = None
            tr["position"] = acct.position
            tr["avg_px"] = acct.avg_px
    closed = [tr for tr in out.trades if tr["status"] == "closed"]
    total = 0.0
    for tr in closed:
        total += tr["pnl_jpy"]
    out.summary = {"closed_trades": len(closed), "pnl_jpy": total,
                   "open_trades": sum(1 for tr in out.trades if tr["status"] == "open")}
    return out

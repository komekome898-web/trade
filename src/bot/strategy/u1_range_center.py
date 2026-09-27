"""U1: レンジ中心回帰(O-1)+ レンジ性の判定器 vr(O-2)。新しい環境(bot.bt.core)の Strategy。

意図の原文は docs/STRATEGY_IDEAS.md §1 の O-1 / O-2、意図と実装の対応は docs/PHASE2/U1/INTENT_MAP.md。
数値は一つも持たない: 族の水準は全部 params で渡す(既定値なし。欠けたら起動を拒否)。

1 分足(BarEvent、足の完成時刻に届く)だけを読む。足が届くたびに:

  vola   = 直近 vola_bars 本の実体 |close - open| の平均            (O-2 の「平均実体」)
  range  = 直近 range_bars 本の high の最大 / low の最小             (O-1「直近 40 分ほどのレンジを毎分計算」)
  center = (max + min) / 2、width = max - min、vr = width / vola     (O-2「レンジ幅 ÷ 平均実体」)

建てる(建玉が無いとき): close が center より上なら center + k_entry * vola に売り指値、下なら
center - k_entry * vola に買い指値(片側だけ。水準が動けば取消して置き直す)。
建てない: width / center < width_min_bp / 1e4(「動きが小さすぎる局面」)、vr >= vr_max(O-2 のゲート)、
静観中(当該足の実体 > big_move_k * vola で静観に入り、|close - center| <= resume_k * vola で解除。
「大きく動いた後は静観し、価格が新しいレンジの中心へ戻ってきた時点で再開」)。
利確: 建玉と反対側の指値を center -/+ k_exit * vola(建てた側、中心寄り)に置き、毎分置き直す。
ヘッジ: (a) 時間成行 = 建玉が hold_bars 本続いたら成行で決済。(b) 逆転順張り(reverse=True のとき)=
建てた時点のレンジを close が逆行方向に抜けたら成行で決済し、抜けた方向に成行で建てる(その建玉は
利確か時間成行で閉じ、再度の逆転はしない)。

決済注文の理由は exit_reasons(client_order_id -> 理由)に残す。統合の口(bot.bt.pipeline、strategy.kind
"module")はこれを往復の記録の理由に使う。
"""
from __future__ import annotations

from typing import Any, Mapping

from bot.bt.core import (BarEvent, ClockEvent, Event, EventType, OrderCanceledEvent, OrderFillEvent, OrderRejectEvent,
                         OrderRequest, Strategy, StrategyContext)

PARAM_KEYS = ("range_bars", "vola_bars", "k_entry", "k_exit", "width_min_bp", "vr_max", "big_move_k", "resume_k",
              "hold_bars", "reverse", "qty")
REASON_TP = "tp_center"  # 利確の指値(中心寄り)が約定
REASON_TIME = "time_market"  # 時間成行
REASON_BREAK = "break_reverse"  # 逆転順張りの決済(建てた時点のレンジを逆行方向に抜けた)


class ParamError(ValueError):
    """params が欠けている・型が違う。"""


def _param(params: Mapping, key: str, kind, *, lo=None) -> Any:
    if key not in params:
        raise ParamError(f"params.{key} is required (no default)")
    v = params[key]
    if kind is bool:
        if type(v) is not bool:
            raise ParamError(f"params.{key} must be a bool, got {v!r}")
        return v
    if kind is int:
        if type(v) is not int:
            raise ParamError(f"params.{key} must be an int, got {v!r}")
    else:
        if type(v) not in (int, float) or v != v:
            raise ParamError(f"params.{key} must be a finite number, got {v!r}")
        v = float(v)
    if lo is not None and v < lo:
        raise ParamError(f"params.{key} must be >= {lo}, got {v!r}")
    return v


def check_params(params: Mapping) -> dict:
    extra = set(params) - set(PARAM_KEYS)
    if extra:
        raise ParamError(f"unknown params {sorted(extra)}; the keys are {PARAM_KEYS}")
    out = {
        "range_bars": _param(params, "range_bars", int, lo=2),
        "vola_bars": _param(params, "vola_bars", int, lo=1),
        "k_entry": _param(params, "k_entry", float, lo=0.0),
        "k_exit": _param(params, "k_exit", float, lo=0.0),
        "width_min_bp": _param(params, "width_min_bp", float, lo=0.0),
        "vr_max": _param(params, "vr_max", float, lo=0.0),
        "big_move_k": _param(params, "big_move_k", float, lo=0.0),
        "resume_k": _param(params, "resume_k", float, lo=0.0),
        "hold_bars": _param(params, "hold_bars", int, lo=1),
        "reverse": _param(params, "reverse", bool),
        "qty": _param(params, "qty", float, lo=0.0),
    }
    if out["qty"] <= 0:
        raise ParamError("params.qty must be > 0")
    return out


class RangeCenterStrategy(Strategy):
    def __init__(self, params: Mapping) -> None:
        self.p = check_params(params)
        self.pos = 0.0  # 建玉(+ 買い / - 売り)、約定通知から
        self.entry_id: str | None = None  # 建てる指値
        self.entry_px: float | None = None
        self.tp_id: str | None = None  # 利確の指値
        self.tp_px: float | None = None
        self.closing_id: str | None = None  # 決済の成行(送信済み・約定待ち)
        self.pending_market: str | None = None  # 建てる成行(逆転順張り)
        self.paused = False
        self.bars_held = 0
        self.entry_range: tuple[float, float] | None = None  # 建てた時点の (min, max)
        self.reversed = False  # 逆転順張りで建てた建玉か
        self.reverse_side: str | None = None  # 決済の約定後に建てる向き
        self.n = 0
        self.exit_reasons: dict[str, str] = {}
        self.stats = {"bars": 0, "gated_width": 0, "gated_vr": 0, "paused_bars": 0, "entries_placed": 0,
                      "tp_placed": 0, "time_exits": 0, "break_exits": 0, "reverse_entries": 0}

    # ----------------------------------------------------------------- helpers
    def _id(self, tag: str) -> str:
        self.n += 1
        return f"u1-{tag}-{self.n}"

    def _cancel(self, ctx: StrategyContext, coid: str | None) -> None:
        if coid is None:
            return
        v = ctx.order(coid)
        if v is not None and v.is_open and not v.cancel_pending:
            ctx.cancel_order(coid)

    def _place_limit(self, ctx: StrategyContext, side: str, px: float, qty: float, tag: str) -> str:
        coid = self._id(tag)
        ctx.place_order(OrderRequest(side=side, order_type="limit", size=qty, price=px, client_order_id=coid))
        return coid

    def _place_market(self, ctx: StrategyContext, side: str, qty: float, tag: str) -> str:
        coid = self._id(tag)
        ctx.place_order(OrderRequest(side=side, order_type="market", size=qty, client_order_id=coid))
        return coid

    # ----------------------------------------------------------------- notices
    def _on_fill(self, ev: OrderFillEvent, ctx: StrategyContext) -> None:
        signed = ev.size if ev.side == "buy" else -ev.size
        before = self.pos
        self.pos += signed
        if abs(self.pos) < 1e-12:
            self.pos = 0.0
        if ev.client_order_id == self.entry_id or ev.client_order_id == self.pending_market:
            if before == 0.0:
                self.bars_held = 0
            if ev.client_order_id == self.pending_market:
                self.reversed = True
        if self.pos == 0.0 and before != 0.0:
            # 建玉が閉じた: 利確の指値が残っていれば取消、逆転順張りなら抜けた方向に成行で建てる
            self._cancel(ctx, self.tp_id)
            self.tp_id, self.tp_px = None, None
            self.entry_range = None
            self.bars_held = 0
            if self.reverse_side is not None:
                side, self.reverse_side = self.reverse_side, None
                self.pending_market = self._place_market(ctx, side, self.p["qty"], "rev")
                self.stats["reverse_entries"] += 1
            else:
                self.reversed = False
        view = ctx.order(ev.client_order_id)
        if view is not None and view.state.value == "FILLED":
            if ev.client_order_id == self.entry_id:
                self.entry_id, self.entry_px = None, None
            elif ev.client_order_id == self.tp_id:
                self.tp_id, self.tp_px = None, None
            elif ev.client_order_id == self.closing_id:
                self.closing_id = None
            elif ev.client_order_id == self.pending_market:
                self.pending_market = None

    def _on_ended(self, coid: str) -> None:
        if coid == self.entry_id:
            self.entry_id, self.entry_px = None, None
        elif coid == self.tp_id:
            self.tp_id, self.tp_px = None, None
        elif coid == self.closing_id:
            self.closing_id = None
        elif coid == self.pending_market:
            self.pending_market = None
            self.reverse_side = None

    # ----------------------------------------------------------------- the bar
    def on_event(self, event: Event, ctx: StrategyContext) -> None:
        if type(event) is OrderFillEvent:
            self._on_fill(event, ctx)
            return
        if type(event) is OrderCanceledEvent or type(event) is OrderRejectEvent:
            if type(event) is OrderRejectEvent and event.request_kind != "new":
                return
            self._on_ended(event.client_order_id)
            return
        if type(event) is ClockEvent:
            return
        if type(event) is not BarEvent:
            return
        p = self.p
        self.stats["bars"] += 1
        need = max(p["range_bars"], p["vola_bars"])
        bars = ctx.visible_events(EventType.BAR, n=need)
        if len(bars) < need:
            return
        vb = bars[len(bars) - p["vola_bars"]:] if p["vola_bars"] < len(bars) else bars
        vola = sum(abs(b.close - b.open) for b in vb) / len(vb)
        rb = bars[len(bars) - p["range_bars"]:] if p["range_bars"] < len(bars) else bars
        rmax, rmin = max(b.high for b in rb), min(b.low for b in rb)
        center = (rmax + rmin) / 2.0
        width = rmax - rmin
        close = event.close
        body = abs(close - event.open)
        if vola <= 0.0:
            vr = float("inf") if width > 0 else 0.0
        else:
            vr = width / vola
        # 静観: 大きく動いた足で入り、中心へ戻ったら解除
        if vola > 0.0 and body > p["big_move_k"] * vola:
            self.paused = True
        if self.paused and abs(close - center) <= p["resume_k"] * vola:
            self.paused = False
        if self.paused:
            self.stats["paused_bars"] += 1

        if self.pos != 0.0:
            self.bars_held += 1
            if self.closing_id is not None:
                return  # 決済の成行が約定待ち
            side_close = "sell" if self.pos > 0 else "buy"
            # (b) 逆転順張り: 建てた時点のレンジを逆行方向に抜けた
            if p["reverse"] and not self.reversed and self.entry_range is not None:
                lo, hi = self.entry_range
                broke = close < lo if self.pos > 0 else close > hi
                if broke:
                    self._cancel(ctx, self.tp_id)
                    self.tp_id, self.tp_px = None, None
                    self.closing_id = self._place_market(ctx, side_close, abs(self.pos), "brk")
                    self.exit_reasons[self.closing_id] = REASON_BREAK
                    self.reverse_side = side_close  # 抜けた方向 = 決済と同じ向き
                    self.stats["break_exits"] += 1
                    return
            # (a) 時間成行
            if self.bars_held >= p["hold_bars"]:
                self._cancel(ctx, self.tp_id)
                self.tp_id, self.tp_px = None, None
                self.closing_id = self._place_market(ctx, side_close, abs(self.pos), "tim")
                self.exit_reasons[self.closing_id] = REASON_TIME
                self.stats["time_exits"] += 1
                return
            # 利確: 中心寄り(建てた側)に置き直す
            tp = center - p["k_exit"] * vola if self.pos > 0 else center + p["k_exit"] * vola
            if self.tp_id is None or self.tp_px != tp:
                self._cancel(ctx, self.tp_id)
                self.tp_id = self._place_limit(ctx, side_close, tp, abs(self.pos), "tp")
                self.tp_px = tp
                self.exit_reasons[self.tp_id] = REASON_TP
                self.stats["tp_placed"] += 1
            return

        # 建玉なし
        if self.pending_market is not None or self.closing_id is not None:
            return
        gate_width = center > 0 and width / center * 1e4 < p["width_min_bp"]
        gate_vr = vr >= p["vr_max"]
        if gate_width:
            self.stats["gated_width"] += 1
        if gate_vr:
            self.stats["gated_vr"] += 1
        if gate_width or gate_vr or self.paused or vola <= 0.0:
            self._cancel(ctx, self.entry_id)
            self.entry_id, self.entry_px = None, None
            return
        if close > center:
            side, px = "sell", center + p["k_entry"] * vola
        elif close < center:
            side, px = "buy", center - p["k_entry"] * vola
        else:
            self._cancel(ctx, self.entry_id)
            self.entry_id, self.entry_px = None, None
            return
        if self.entry_id is not None:
            v = ctx.order(self.entry_id)
            if v is not None and v.is_open and v.request.side == side and self.entry_px == px:
                return
            self._cancel(ctx, self.entry_id)
        self.entry_id = self._place_limit(ctx, side, px, p["qty"], "ent")
        self.entry_px = px
        self.entry_range = (rmin, rmax)
        self.stats["entries_placed"] += 1


def make(params: Mapping, price_type: type) -> Strategy:
    """統合の口(strategy.kind "module")が呼ぶ工場。足で駆動する銘柄だけを受ける。"""
    if price_type is not BarEvent:
        raise ParamError(f"u1_range_center reads bars only; the instrument is priced by {price_type.__name__}")
    return RangeCenterStrategy(params)

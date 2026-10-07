"""作り物の道の戦略(ダッシュボードの表示の確かめ用。本物の戦略ではない。マチルダではない)。

足の窓(window 本)の高値・安値から中心、実体の平均から ボラ を出す。足の終わりに終値が 中心 -/+ k × ボラ の外に出たら合図
(kind = 線の外・向き long/short)の発生、内側に戻ったら消失。合図の間、中心 -/+ k × ボラ に指値を置き(段は 1 × ボラずつ
有利な側、levels まで)、約定しない指値は 3 本たったら取り消す。建玉があれば足ごとに決済の指値を取り消して置き直し、
40 本たったら出ている注文を取り消して close の成行。zero_every > 0 なら、その回数目の段だけ段数 200 で出す(量が 0 になる段の見本)。
"""
from __future__ import annotations

from collections import deque

from decimal import Decimal  # noqa: F401
from bot.bt.core import BarEvent, OrderCanceledEvent, OrderFillEvent
from bot.bt.road import NO_SIGNAL, RoadStrategy


class FakeLadder(RoadStrategy):
    def __init__(self, params: dict) -> None:
        super().__init__(quote_ccy=params["quote_ccy"])
        self.levels = params["levels"]
        self.window = params["window"]
        self.k = params["k"]
        self.zero_every = params.get("zero_every", 0)
        self.with_exit = params.get("with_exit", False)
        self.bars = deque(maxlen=self.window)
        self.n = 0
        self.entry = {}  # order id -> bar number placed
        self.rung_px = None
        self.rungs = 0
        self.sig = None
        self.sig_n = 0
        self.side = None
        self.pos = 0.0
        self.last_fill = None
        self.close_id = None
        self.close_pos = 0.0
        self.held_since = None
        self.placed_total = 0
        self.winding = False

    def _fpos(self) -> float:
        p = float(self.position())
        return 0.0 if abs(p) < 1e-9 else p  # 浮動小数の残り(4e-17 など)は 0

    def step(self, event, ctx) -> None:
        if isinstance(event, OrderFillEvent):
            self.last_fill = event.price
            self.pos = self._fpos()
            self.entry.pop(event.client_order_id, None)
            if self.pos == 0:
                self.pos, self.held_since, self.rung_px, self.rungs = 0.0, None, None, 0
            elif self.held_since is None:
                self.held_since = self.n
            return
        if isinstance(event, OrderCanceledEvent):
            self.entry.pop(event.client_order_id, None)
            return
        if not isinstance(event, BarEvent):
            return
        self.n += 1
        self.pos = self._fpos()
        self.bars.append(event)
        if len(self.bars) < self.window:
            return
        hi = max(b.high for b in self.bars)
        lo = min(b.low for b in self.bars)
        center = (hi + lo) / 2
        vol = sum(abs(b.close - b.open) for b in self.bars) / len(self.bars)
        vol = max(vol, 1.0)
        up, dn = center + self.k * vol, center - self.k * vol
        c = event.close
        # 合図
        if self.sig is None and not self.is_flattening():
            d = "short" if c > up else "long" if c < dn else None
            if d:
                self.sig_n += 1
                self.sig = f"g{self.sig_n}"
                self.side = "sell" if d == "short" else "buy"
                self.rung_px = None
                self.rungs = 0
                self.signal_start(self.sig, "線の外", d, {"close": c, "center": round(center, 1), "vol": round(vol, 1)})
        elif self.sig is not None:
            inside = dn * 0.5 + center * 0.5 < c < up * 0.5 + center * 0.5
            if inside:
                for oid in list(self.entry):
                    self.cancel(oid)
                self.signal_end(self.sig, "線の内側に戻った")
                self.sig = None
        # 建ての指値(合図の間)
        if self.sig is not None and not self.is_flattening() and not self.winding and self.rungs < self.levels:
            for oid, nb in list(self.entry.items()):
                if self.n - nb >= 3:
                    self.cancel(oid)
            if not self.entry:
                base = dn if self.side == "buy" else up
                px = base if self.rung_px is None else self.rung_px + (-vol if self.side == "buy" else vol)
                lv = 200 if (self.zero_every and (self.placed_total + 1) % self.zero_every == 0) else self.levels
                if self.with_exit and lv == self.levels and self.rungs == 0:  # 1 段目は建てと一緒に決済の指値を出す
                    ex = px + (0.8 * vol if self.side == "buy" else -0.8 * vol)
                    oid = self.place_with_exit(self.side, px, lv, self.sig, ex)[0]
                else:
                    oid = self.place(self.side, "limit", px, lv, self.sig)
                self.placed_total += 1
                if lv == self.levels:
                    self.entry[oid] = self.n
                    self.rung_px = px
                    self.rungs += 1
        # 決済
        if self.pos != 0 and not self.is_flattening():
            held = self.n - (self.held_since or self.n)
            if held >= 40 or self.winding:
                live = [o for o in list(self.entry) + ([self.close_id] if self.close_id else [])
                        if self.order_state(o) in ("OPEN", "PENDING_NEW", "PENDING_CANCEL")]
                if not self.winding:  # 1 本目: 出ている注文を全部取り消す
                    self.winding = True
                    for o in live:
                        if self.order_state(o) != "PENDING_CANCEL":
                            self.cancel(o)
                elif not live:  # 次の足以降
                    self.close(self.sig or NO_SIGNAL, "market", None)
                    self.winding = False
                return
            ref = self.last_fill or c
            target = ref + (0.8 * vol if self.pos > 0 else -0.8 * vol)
            st = None if self.close_id is None else self.order_state(self.close_id)
            if self.close_id is None or st in ("FILLED", "CANCELED", "REJECTED"):
                self.close_id = self.close(self.sig or NO_SIGNAL, "limit", target)  # 決済の指値(建玉が変わるたびに置き直す)
                self.close_pos = self.pos
            elif st == "OPEN" and self.close_pos != self.pos:
                self.cancel(self.close_id)  # 建玉が変わった: 取り消して、取り消しの答えが届いた足で置き直す


def pipeline_strategy(params: dict, price_type) -> FakeLadder:
    return FakeLadder(params)

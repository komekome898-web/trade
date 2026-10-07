"""1 分足の指値の約定の決まり(L-769・L-770)の受け入れの場面に使う小さな道の戦略
(委任文 docs/DISCUSSIONS/2026-10-06_held_batches/DELEGATION_fill_scenario_L769.md)。

試験(`tests/road/test_road_fill_l769.py`)が、このファイルを `bot.strategy.road_l769_test` の名で読み込んで
道の走らせ(`bot.bt.pipeline` の `strategy.kind = module`)に渡す。戦略の置き場(`src/bot/strategy/`)には置かない。

足を数え(1 本目 = 1)、params の mode ごとに:
- "entry":        open_bar 本目で合図 s1 の発生 → 指値(売買 side、値段 limit_px、無ければその足の終値)を段数 levels で 1 つ
- "with_exit":    open_bar 本目で合図 s1 の発生 → place_with_exit(買い、値段 limit_px か終値、段数 levels、決済の値段 exit_px)
- "moving_close": open_bar 本目で合図 s1 の発生 → 段数 levels の成行の買い。建玉ができた後の足ごとに、出ている close の
                  指値を取り消し、取り消しの答えが届いたら lines の値段(足の番号 → 値段。無い番号は前の値段)に close の
                  指値を置き直す(足の終わりに取り消して新しい値段で置く)。建玉が 0 になったら何もしない
"""
from __future__ import annotations

from bot.bt.core import BarEvent, OrderCanceledEvent
from bot.bt.road import RoadStrategy


class L769Strategy(RoadStrategy):
    def __init__(self, params: dict) -> None:
        super().__init__(quote_ccy=params["quote_ccy"])
        self.mode = params["mode"]
        self.levels = params["levels"]
        self.open_bar = params["open_bar"]
        self.side = params.get("side", "buy")
        self.limit_px = params.get("limit_px")
        self.exit_px = params.get("exit_px")
        self.lines = {int(k): v for k, v in (params.get("lines") or {}).items()}
        self.bars = 0
        self.close_id = None
        self.replace_px = None
        self.line = None

    def step(self, event, ctx) -> None:
        if isinstance(event, OrderCanceledEvent) and event.client_order_id == self.close_id \
                and event.answers == "cancel" and self.replace_px is not None:
            self.close_id = self.close("s1", "limit", self.replace_px)  # 取り消しの答えが届いた: 置き直す
            self.replace_px = None
            return
        if not isinstance(event, BarEvent):
            return
        self.bars += 1
        b = self.bars
        if b == self.open_bar:
            self.signal_start("s1", "試験の合図", "long", {"close": event.close})
            px = event.close if self.limit_px is None else self.limit_px
            if self.mode == "entry":
                self.place(self.side, "limit", px, self.levels, "s1")
            elif self.mode == "with_exit":
                self.place_with_exit("buy", px, self.levels, "s1", self.exit_px)
            elif self.mode == "moving_close":
                self.place("buy", "market", None, self.levels, "s1")
            return
        if self.mode != "moving_close" or b < self.open_bar or self.position() == "0":
            return
        self.line = self.lines.get(b, self.line)
        if self.line is None:
            return
        if self.close_id is None:
            self.close_id = self.close("s1", "limit", self.line)
        elif self.order_state(self.close_id) in ("OPEN", "PENDING_NEW"):
            self.replace_px = self.line
            self.cancel(self.close_id)


def pipeline_strategy(params: dict, price_type) -> L769Strategy:
    return L769Strategy(params)

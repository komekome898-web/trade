"""1 段目の約定値段からの距離で値段が決まる段(L-816「1.a」)の受け入れの場面に使う小さな道の戦略
(委任文 docs/DISCUSSIONS/2026-10-06_held_batches/matilda_step0/DELEGATION_anchor_b1.md)。

試験(`tests/road/test_anchor_b1_spec.py`)が、このファイルを `bot.strategy.road_anchor_test` の名で読み込んで
道の走らせ(`bot.bt.pipeline` の `strategy.kind = module`)に渡す。戦略の置き場(`src/bot/strategy/`)には置かない。

足を数え(1 本目 = 1)、open_bar 本目で合図 s1 を出し、1 段目(根)を place で出す(売買 side、値段 root_px、段数 levels)。
続けて children の段ごとに、根を基準にした段(anchor = 根の番号、offset = 段の距離、size_ref = 根)を出す。段に exit_px が
あれば place_with_exit(決済の指値つき)、無ければ place。cancel_root_bar 本目で根を、cancel_child_bar 本目で 1 つ目の段を取り消す。
late_child_bar 本目に、根を基準にした段(距離 late_offset)をもう 1 つ出す(根が約定した後に段を出す場面)。
"""
from __future__ import annotations

from bot.bt.core import BarEvent
from bot.bt.road import RoadStrategy


class AnchorStrategy(RoadStrategy):
    def __init__(self, params: dict) -> None:
        super().__init__(quote_ccy="JPY")
        self.side = params.get("side", "buy")
        self.root_px = params["root_px"]
        self.levels = params["levels"]
        self.open_bar = params["open_bar"]
        self.children = list(params.get("children", []))
        self.cancel_root_bar = params.get("cancel_root_bar")
        self.cancel_child_bar = params.get("cancel_child_bar")
        self.late_child_bar = params.get("late_child_bar")
        self.late_offset = params.get("late_offset")
        self.bars = 0
        self.root = None
        self.kids: list = []

    def step(self, event, ctx) -> None:
        if not isinstance(event, BarEvent):
            return
        self.bars += 1
        b = self.bars
        if b == self.open_bar:
            self.signal_start("s1", "試験の合図", "long" if self.side == "buy" else "short", {"close": event.close})
            self.root = self.place(self.side, "limit", self.root_px, self.levels, "s1")
            for c in self.children:
                if c.get("exit_px") is None:
                    self.kids.append(self.place(self.side, "limit", None, self.levels, "s1", size_ref=self.root,
                                                anchor=self.root, offset=c["offset"]))
                else:
                    self.kids.append(self.place_with_exit(self.side, None, self.levels, "s1", c["exit_px"],
                                                          size_ref=self.root, anchor=self.root,
                                                          offset=c["offset"])[0])
            return
        if b == self.cancel_root_bar and self.order_state(self.root) in ("PENDING_NEW", "OPEN"):
            self.cancel(self.root)
        if b == self.cancel_child_bar and self.order_state(self.kids[0]) in ("PENDING_NEW", "OPEN"):
            self.cancel(self.kids[0])
        if b == self.late_child_bar:
            self.place(self.side, "limit", None, self.levels, "s1", size_ref=self.root, anchor=self.root,
                       offset=self.late_offset)


def pipeline_strategy(params: dict, price_type) -> AnchorStrategy:
    return AnchorStrategy(params)

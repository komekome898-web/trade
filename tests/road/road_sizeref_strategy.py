"""量をそろえる口(L-781)の受け入れの場面に使う小さな道の戦略(委任文
docs/DISCUSSIONS/2026-10-06_held_batches/matilda_step0/DELEGATION_matilda_v37.md)。

試験(`tests/road/test_matilda_v37_spec.py`)が、このファイルを `bot.strategy.road_sizeref_test` の名で読み込んで
道の走らせ(`bot.bt.pipeline` の `strategy.kind = module`)に渡す。戦略の置き場(`src/bot/strategy/`)には置かない。

足を数え(1 本目 = 1)、open_bar 本目で合図 s1 を出し、params の prices の値段に、段数 levels の買いの指値を順に出す。
1 つ目は量の計算(place)、2 つ目からは 1 つ目の注文の量を使う(place の size_ref = 1 つ目の注文の番号)。
"""
from __future__ import annotations

from bot.bt.core import BarEvent
from bot.bt.road import RoadStrategy


class SizeRefStrategy(RoadStrategy):
    def __init__(self, params: dict) -> None:
        super().__init__(quote_ccy="JPY")
        self.prices = list(params["prices"])
        self.levels = params["levels"]
        self.open_bar = params["open_bar"]
        self.bars = 0

    def step(self, event, ctx) -> None:
        if not isinstance(event, BarEvent):
            return
        self.bars += 1
        if self.bars != self.open_bar:
            return
        self.signal_start("s1", "試験の合図", "long", {"close": event.close})
        root = self.place("buy", "limit", self.prices[0], self.levels, "s1")
        for px in self.prices[1:]:
            self.place("buy", "limit", px, self.levels, "s1", size_ref=root)


def pipeline_strategy(params: dict, price_type) -> SizeRefStrategy:
    return SizeRefStrategy(params)

"""受け入れの場面の試験に使う小さな道の戦略(委任文 DELEGATION_record_form.md「受け入れの場面」1〜3・5)。

試験(`tests/road/test_road_record.py`)が、このファイルを `bot.strategy.road_scene_test` の名で読み込んで
道の走らせ(`bot.bt.pipeline` の `strategy.kind = module`)に渡す。戦略の置き場(`src/bot/strategy/`)には置かない。

足を数え(1 本目 = 1)、params の mode ごとに:
- "basic":       open_bar 本目で合図 s1 の発生 → 段数 levels の成行の買いを 2 つ(合図 s1)。
                 close_bar 本目で合図 s1 の消失 → 決済の口 flatten の成行(合図「無し」)= 全部売り
- "zero":        open_bar 本目で合図 s1 の発生 → 段数 levels の成行の買い 1 つ(量が 0 になる段数を渡す)
- "end_unknown": open_bar 本目で、発生していない合図 zz の消失
- "order_unknown": open_bar 本目で、発生していない合図 zz の買い
- "twice":       open_bar 本目で合図 s1 の発生を 2 回
- "limit_cancel": open_bar 本目で合図 s1 の発生 → 足の終値の半分の指値の買い(段数 levels。届かない)、
                 close_bar 本目でその注文の取り消し
- "ladder":      open_bar 本目と open_bar + 1 本目に、段数 levels の成行の買い(合図 s1)。close_bar 本目に flatten の成行
- "flatten_empty": open_bar 本目に、建玉 0 のまま flatten の成行
- "reject":      open_bar 本目で合図 s1 の発生 → 段数 levels の成行の買いと、終値の指値の買い(最小の量より小さい量にして拒ませる)
- "nothing":     何もしない
- keep_open が真なら、open_bar 本目に合図 s2 も発生させ、消さない(データの終わりまで消えない合図)
"""
from __future__ import annotations

from bot.bt.core import BarEvent
from bot.bt.road import NO_SIGNAL, RoadStrategy


class SceneStrategy(RoadStrategy):
    def __init__(self, params: dict) -> None:
        super().__init__(quote_ccy=params["quote_ccy"], fx=params.get("fx"), fx_source=params.get("fx_source", ""))
        self.mode = params["mode"]
        self.levels = params["levels"]
        self.open_bar = params["open_bar"]
        self.close_bar = params.get("close_bar")
        self.keep_open = params.get("keep_open", False)
        self.bars = 0

    def step(self, event, ctx) -> None:
        if not isinstance(event, BarEvent):
            return
        self.bars += 1
        if self.mode == "nothing":
            return
        if self.bars == self.open_bar:
            if self.mode == "flatten_empty":
                self.flatten(NO_SIGNAL, "market", None)
                return
            if self.mode == "end_unknown":
                self.signal_end("zz", "条件が外れた")
                return
            if self.mode == "order_unknown":
                self.place("buy", "market", None, self.levels, "zz")
                return
            self.signal_start("s1", "試験の合図", "long", {"close": event.close})
            if self.mode == "twice":
                self.signal_start("s1", "試験の合図", "long", {"close": event.close})
            if self.keep_open:
                self.signal_start("s2", "消えない合図", "short", None)
            if self.mode == "basic":
                self.place("buy", "market", None, self.levels, "s1")
                self.place("buy", "market", None, self.levels, "s1")
            elif self.mode == "zero":
                self.place("buy", "market", None, self.levels, "s1")
            elif self.mode in ("ladder", "reject"):
                self.place("buy", "market", None, self.levels, "s1")
                if self.mode == "reject":
                    self.place("buy", "limit", event.close, self.levels, "s1")
            elif self.mode == "limit_cancel":
                self.limit_id = self.place("buy", "limit", event.close / 2, self.levels, "s1")
        elif self.mode == "basic" and self.bars == self.close_bar:
            self.signal_end("s1", "条件が外れた")
            self.flatten(NO_SIGNAL, "market", None)
        elif self.mode == "ladder" and self.bars == self.open_bar + 1:
            self.place("buy", "market", None, self.levels, "s1")
        elif self.mode == "ladder" and self.bars == self.close_bar:
            self.flatten("s1", "market", None)
        elif self.mode == "limit_cancel" and self.bars == self.close_bar:
            self.cancel(self.limit_id)


def pipeline_strategy(params: dict, price_type) -> SceneStrategy:
    return SceneStrategy(params)

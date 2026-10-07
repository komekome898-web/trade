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
- 3 周目(批評家 1 回目の試し probe.py・dcancel.py と同じ場面):
  - "margin_patch":  作るときに bot.bt.road.strategy.MARGIN_JPY を 1,000,000 に書き換え、open_bar 本目に段数 1 の成行の買い、
                     close_bar 本目に flatten(試験の側で元に戻す)
  - "fake_px":       open_bar 本目に土台の直近の値段を半分に書き換えてから段数 1 の成行の買い、close_bar 本目に flatten
  - "edit_order":    open_bar 本目に段数 1 の成行の買い(0.028)を出し、土台の注文の記録を証拠金 100,000・量 0.014 に書き換える
  - "edit_signal":   open_bar 本目に合図 s1 の発生の時刻を 1 分前に、close_bar 本目に消失の時刻を 1 分後に書き換える
                     (買いと flatten は basic と同じ)
  - "direct_cancel": open_bar 本目に終値の半分の指値の買い、close_bar 本目に ctx.cancel_order を直に呼ぶ
  - "quick_flatten": open_bar 本目に段数 levels の成行の買いを 2 つ、close_bar 本目(次の足)に flatten
  - "cancel_twice":  open_bar 本目に終値の半分の指値の買い、close_bar 本目に cancel を 2 回(2 回目は取り消しの拒否)
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
        if self.mode == "margin_patch":
            import bot.bt.road.strategy as RS
            RS.MARGIN_JPY = 1_000_000  # 道の外で証拠金を書き換える(試験の側で元に戻す)

    def step(self, event, ctx) -> None:
        if not isinstance(event, BarEvent):
            return
        self.bars += 1
        if self.mode == "nothing":
            return
        if self._r3(event, ctx):
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
            if self.mode == "edit_signal":
                self._signals["s1"]["start_t_ns"] -= 60_000_000_000  # 発生の時刻を 1 分前に書き換える
            if self.mode in ("basic", "edit_signal"):
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
        elif self.mode in ("basic", "edit_signal") and self.bars == self.close_bar:
            self.signal_end("s1", "条件が外れた")
            if self.mode == "edit_signal":
                self._signals["s1"]["end_t_ns"] += 60_000_000_000  # 消失の時刻を 1 分後に書き換える
            self.flatten(NO_SIGNAL, "market", None)
        elif self.mode == "ladder" and self.bars == self.open_bar + 1:
            self.place("buy", "market", None, self.levels, "s1")
        elif self.mode == "ladder" and self.bars == self.close_bar:
            self.flatten("s1", "market", None)
        elif self.mode == "limit_cancel" and self.bars == self.close_bar:
            self.cancel(self.limit_id)


def pipeline_strategy(params: dict, price_type) -> SceneStrategy:
    return SceneStrategy(params)


def _r3_modes():
    return ("margin_patch", "fake_px", "edit_order", "direct_cancel", "quick_flatten", "cancel_twice")


def _r3(self, event, ctx) -> bool:
    """3 周目の場面。扱った場面なら True。"""
    m, b = self.mode, self.bars
    if m not in _r3_modes():
        return False
    if b == self.open_bar:
        self.signal_start("s1", "試験の合図", "long", None)
        if m in ("margin_patch", "edit_order"):
            coid = self.place("buy", "market", None, 1, "s1")
            if m == "edit_order":
                row = self._orders[coid]
                row.update(margin_jpy="100000", qty="0.014", qty_raw="0.014")
        elif m == "fake_px":
            self._px = self._px / 2
            self.place("buy", "market", None, 1, "s1")
        elif m in ("direct_cancel", "cancel_twice"):
            self.limit_id = self.place("buy", "limit", event.close / 2, 1, "s1")
        elif m == "quick_flatten":
            self.place("buy", "market", None, self.levels, "s1")
            self.place("buy", "market", None, self.levels, "s1")
    elif b == self.close_bar:
        if m == "direct_cancel":
            ctx.cancel_order(self.limit_id)
        elif m == "cancel_twice":
            self.cancel(self.limit_id)
            self.cancel(self.limit_id)
        elif m != "edit_order":
            self.signal_end("s1", "条件が外れた")
            self.flatten(NO_SIGNAL, "market", None)
    return True


SceneStrategy._r3 = _r3


# ---- 4 周目: close(決済の普通の注文)の場面 -------------------------------------------------------------------
# on_trades が真なら「足」は約定(trade)の 1 つ 1 つ。
# - "close_tp":     マチルダの利確の形。open_bar 本目に段数 1 の成行の買い(合図 s1)。次の足から足ごとに、出ている close の
#                   指値を取り消し、取り消しの答えが届いたら、その足の終値 × (1 + line_pct) の線(刻み 0.5 に丸める)に
#                   close の指値を置き直す。最後に約定して建玉 0
# - "close_levels": open_bar 本目と次の足に段数 2 の成行の買い(段を 2 つ積む)、close_bar 本目に close の成行を 2 回
#                   (2 回目は、出ている 1 回目の決済で足りているので量 0 の行)
# - "doten_flatten": 0:03 に段数 2 の成行の買い(0.014)、0:05 に段数 1 の成行の売り(0.028、ドテン)、close_bar 本目に flatten
# - "flatten_cancel_only": 0:03 に終値の半分の指値の買い(届かない)、close_bar 本目に flatten(建玉 0: 取り消しだけ)
# - "close_partial": close_tp と同じ形を、線を値段の下(line_pct < 0)に置いて回す。量の分だけ約定が来ないと一部だけ約定し、
#                   次の足で取り消し、答えが届いたら残りの建玉の量で置き直す
def _r4(self, event, ctx) -> bool:
    from bot.bt.core import OrderCanceledEvent, TradeEvent
    m = self.mode
    if m in ("doten_flatten", "flatten_cancel_only"):
        if not isinstance(event, BarEvent):
            return True
        self.bars += 1
        b = self.bars
        if b == 3:
            self.signal_start("s1", "試験の合図", "long", None)
            if m == "doten_flatten":
                self.place("buy", "market", None, 2, "s1")  # 0.014
            else:
                self.place("buy", "limit", event.close / 2, 1, "s1")  # 届かない指値
        elif b == 5 and m == "doten_flatten":
            self.signal_start("s2", "試験の合図", "short", None)
            self.place("sell", "market", None, 1, "s2")  # 0.028: 0.014 の買いからドテン
        elif b == self.close_bar:
            self.flatten(NO_SIGNAL, "market", None)
        return True
    if m not in ("close_tp", "close_levels", "close_partial"):
        return False
    if isinstance(event, OrderCanceledEvent) and event.client_order_id == getattr(self, "close_id", None) \
            and getattr(self, "replace_px", None) is not None:
        self.close_id = self.close("s1", "limit", self.replace_px)  # 取り消しの答えが届いた: 置き直す
        self.replace_px = None
        return True
    on_trades = self.on_trades
    tick = isinstance(event, TradeEvent) if on_trades else isinstance(event, BarEvent)
    if not tick:
        return True
    self.bars += 1
    b = self.bars
    px = event.price if on_trades else event.close
    if b == self.open_bar:
        self.signal_start("s1", "試験の合図", "long", None)
        self.place("buy", "market", None, self.levels, "s1")
        return True
    if m == "close_levels":
        if b == self.open_bar + 1:
            self.place("buy", "market", None, self.levels, "s1")
        elif b == self.close_bar:
            self.close_id = self.close("s1", "market", None)
            self.close_again = self.close("s1", "market", None)  # 出ている決済で足りている: 量 0 の行
        return True
    if b <= self.open_bar or self.position() == "0":
        return True
    line = round(px * (1 + self.params_line) * 2) / 2
    cid = getattr(self, "close_id", None)
    if cid is None:
        self.close_id = self.close("s1", "limit", line)
    elif self.order_state(cid) in ("OPEN", "PENDING_NEW"):
        self.replace_px = line
        self.cancel(cid)
    return True


SceneStrategy._r4 = _r4
_old_init = SceneStrategy.__init__


def _init(self, params):
    _old_init(self, params)
    self.params_line = params.get("line_pct", 0.0)
    self.on_trades = params.get("on_trades", False)


SceneStrategy.__init__ = _init
_old_step = SceneStrategy.step


def _step(self, event, ctx):
    if self._r4(event, ctx):
        return
    _old_step(self, event, ctx)


SceneStrategy.step = _step


# ---- 5 周目: 批評家 3 回目の場面(close_run.py・limit_at.py と同じ形) -------------------------------------------
# - "doten_after_close":      0:03 に段数 2 の成行の買い(0.014)、0:05 に close の売りの指値(終値)と、同じ足でドテンの
#                             成行の売り(段数 1 = 0.028)
# - "place_sell_after_close": 0:03・0:05 に段数 2 の成行の買い(建玉 0.028)、0:07 に close の売りの指値(終値)と、同じ足で
#                             段数 2 の成行の売り(0.014)
# - "limit_at":               0:03 に段数 2 の成行の買い、0:05 に close の売りの指値(値段は params の limit_px)
def _r5(self, event, ctx) -> bool:
    m = self.mode
    if m not in ("doten_after_close", "place_sell_after_close", "limit_at"):
        return False
    if not isinstance(event, BarEvent):
        return True
    self.bars += 1
    b = self.bars
    if b == 3:
        self.signal_start("s1", "試験の合図", "long", None)
        self.place("buy", "market", None, 2, "s1")
    if m == "doten_after_close" and b == 5:
        self.close("s1", "limit", event.close)
        self.signal_start("s2", "試験の合図", "short", None)
        self.place("sell", "market", None, 1, "s2")
    if m == "place_sell_after_close" and b == 5:
        self.place("buy", "market", None, 2, "s1")
    if m == "place_sell_after_close" and b == 7:
        self.close("s1", "limit", event.close)
        self.place("sell", "market", None, 2, "s1")
    if m == "limit_at" and b == 5:
        self.close("s1", "limit", self.limit_px)
    return True


SceneStrategy._r5 = _r5
_old_init5 = SceneStrategy.__init__


def _init5(self, params):
    _old_init5(self, params)
    self.limit_px = params.get("limit_px")


SceneStrategy.__init__ = _init5
_old_step5 = SceneStrategy.step


def _step5(self, event, ctx):
    if self._r5(event, ctx):
        return
    _old_step5(self, event, ctx)


SceneStrategy.step = _step5

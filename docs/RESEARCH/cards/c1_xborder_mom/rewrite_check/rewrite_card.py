"""カード 1「今の paper bot の戦略 xborder_mom」を原文だけから独立に書き直したもの(W4 §2 の 5)。

原文: src/bot/strategy/xborder_momentum.py(判断)、src/bot/main.py 160-167・767-771 行(leader_close の付け方)、
src/bot/market_data/external_feed.py(close_for の 2 区間までの遡り)、src/bot/market_data/feed.py(CandleBuilder)、
config/config.yaml の strategy.params(k=30, thr_pct=0.8, exit_pct=0.05)。

写し方(リードの決め): BUY -> +1、SELL -> -1、CLOSE -> 0、HOLD -> 前の持ち高のまま。
損切り・ドテンの禁止・増し玉の禁止・SFD の守りは bot の守りなのでカードの外。

参照の口(リードの決め): 系列 binance_btcusdt_close、行の時刻は Binance の open_time(1 分の始まり)、
lag 60 秒。t で終わる分の行は view.ref_at(名前, t - 60 秒)。
"""
from __future__ import annotations

import math

import numpy as np

from bot.research.cards.card import CardView, SeriesSpec

REF_NAME = "binance_btcusdt_close"
MIN_NS = 60 * 1_000_000_000  # 1 分(int。SeriesSpec は int を求める)
FALLBACK_INTERVALS = 2  # external_feed.close_for の max_age_intervals の既定

# config/config.yaml strategy.params(稼働中の値)。原文のコード既定は k=10, exit_pct=0.1。
DEFAULT_PARAMS = {"k": 30, "thr_pct": 0.8, "exit_pct": 0.05}

BUY, SELL, CLOSE, HOLD = "BUY", "SELL", "CLOSE", "HOLD"


def decide(leader_now, leader_past, thr: float, exit_band: float) -> str:
    """xborder_momentum.on_candles の判断部分の写し(履歴の長さの検査は呼び手)。
    leader_now / leader_past は None(close_for が None)でもよい。"""
    if leader_now is None or leader_past is None:
        return HOLD  # 原文: None は float64 の列で NaN になり "leader data gap"
    leader_now = float(leader_now)
    leader_past = float(leader_past)
    if math.isnan(leader_now) or math.isnan(leader_past) or leader_past <= 0:
        return HOLD
    mom = float(np.log(leader_now / leader_past))
    if mom > thr:
        return BUY
    if mom < -thr:
        return SELL
    if abs(mom) <= exit_band:
        return CLOSE
    return HOLD


class XborderMomRewrite:
    """1 つのインスタンス = 1 回の走らせ(前の持ち高を内部に持つ)。"""

    name = "xborder_mom_rewrite"

    def __init__(self, params: dict | None = None) -> None:
        p = dict(DEFAULT_PARAMS)
        p.update(params or {})
        self.k = int(p["k"])
        self.thr = float(p["thr_pct"]) / 100
        self.exit_band = float(p["exit_pct"]) / 100
        self.min_history = self.k + 2
        self.requires = [SeriesSpec(REF_NAME, MIN_NS)]
        self._prev = 0.0
        self._last_now = None
        self.last_kind = None  # 試験と比べる台本のための記録(持ち高には関わらない)

    def _close_for(self, view: CardView, minute_start_ns: int):
        """external_feed.close_for の写し: その分の値、無ければ 1 分前、2 分前。全部無ければ None。
        行が無いことだけを抜けとみなす(KeyError)。先読みの例外は捕まえない。"""
        for back in range(FALLBACK_INTERVALS + 1):
            try:
                return view.ref_at(REF_NAME, int(minute_start_ns - back * MIN_NS))
            except KeyError:
                continue
        return None

    def exposure(self, view: CardView) -> float:
        t = int(view.now_ns)
        if self._last_now is not None and t <= self._last_now:  # 別の走らせに使い回されたら始めから
            self._prev = 0.0
        self._last_now = t
        if len(view.bars(self.min_history)) < self.min_history:
            kind = HOLD  # 原文: len(candles) < min_history -> "insufficient history"
        else:
            # 今の足 = t で終わる分(始まり t-60s)。k 本前の足 = 始まり t-(k+1)*60s(時刻で数える)。
            now_start = t - MIN_NS
            past_start = t - (self.k + 1) * MIN_NS
            kind = decide(self._close_for(view, now_start), self._close_for(view, past_start),
                          self.thr, self.exit_band)
        self.last_kind = kind
        if kind == BUY:
            self._prev = 1.0
        elif kind == SELL:
            self._prev = -1.0
        elif kind == CLOSE:
            self._prev = 0.0
        return self._prev


__all__ = ["XborderMomRewrite", "decide", "REF_NAME", "MIN_NS", "DEFAULT_PARAMS"]

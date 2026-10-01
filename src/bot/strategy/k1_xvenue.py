"""K1 取引所横断(段階 G、2026-10-01、委任文 docs/DATA/delegations/20261001_k1_stage_g.md)を、新しい
環境の戦略として書いたもの。

規則は規則の文から読んだ(当時のスクリプト scripts/measure_katsuo_xvenue.py・measure_katsuo_effect.py
は規則の読み取りにだけ使い、算術は写していない):
  - RESULT.md 1.3(門・向き・int() の切り捨て・強さ)。k1_wick.signal_of_bar をそのまま使う
  - H1(RESULT.md 10.1、H1_PREREG.md §2): 門を通った足で 実体 >= 勝った側のヒゲ なら sig = -csign、
    無効化ラインは新しい向きの側の極値、強さは定義どおり(反転した足は必ず「弱い」)
  - H2a(RESULT.md 11.1): ヒゲ先端の無効化の枝を外し、決済は反対シグナルだけ(弱い = 決済のみ / 強い = ドテン)
  - H3(RESULT.md 12.1): 足 j で行う行動は足 j-1 のシグナル。約定は足 j の終値。最初の足は行動なし
  - 横断(XVENUE_PREREG.md §1): 状態遷移はすべて海外のシグナル列で決まり、価格だけ bitFlyer。
    海外の足 i のシグナルを bitFlyer の足 i+1 の終値で建て・閉じる

モード:
  "design"     2 本の流れ(d0 = 海外の足、d1 = bitFlyer の足。結合・畳み済みで窓が同じ)。核の合流の順
               (ordering.py: 同じ時刻では流れの名前の順)で、同じ窓の d0 → d1 の順に届く。d1 を受けたときに
               「1 本前の d0 のシグナル」(H3)で行動し、約定の口(last_bar_close)は直前に受けた足 = d1
               (bitFlyer)の終値で約定する
  "sameclose"  参考列 (iii): 同じ 2 本の流れで、d1 を受けたときに「同じ窓の d0 のシグナル」で行動する
               (H3 を外す。約定は同じ窓の bitFlyer の終値 = 海外の足の確定と同時刻。取れない価格)
  "single"     参考列 (i): 1 本の流れ(海外の足だけ)。H3 で行動し、海外の足の終値で約定する

2 本の流れの見分け: 核の事象に銘柄の欄が無い(ENV_DEFECTS.md G-1)ので、同じ時刻に届く 2 本の足の
1 本目を d0、2 本目を d1 とみなす。各時刻にちょうど 2 本ずつ届くこと(時刻が一致すること)を毎回確かめ、
崩れたら K1XError で止まる。
費用: 0(RESULT.md 1.4「経費は引いていない」)。
"""
from __future__ import annotations

import hashlib
import inspect
from typing import Mapping, Optional

from bot.bt.core import BarEvent, Event, NullAccount, OrderRequest, Strategy, StrategyContext, ZeroLatency
from bot.bt.costs import CostSchedule
from bot.bt.fill import FillSpec, SimVenue
from bot.bt.orders import FaultPlan, Product, VenueRules
from bot.bt.repro.fixed import DeclaredFeeCost, Parts
from bot.strategy.k1_wick import BIG, SMALL, STRENGTHS, gate_label, gates, signal_of_bar

OPPOSITE_WEAK, REVERSED = "opposite_weak", "reversed"
MODES = ("design", "sameclose", "single")


class K1XError(ValueError):
    pass


def signal_h1(o: float, h: float, l: float, c: float, s: str, b: str) -> tuple[int, int, str]:
    """RESULT.md 1.3 + H1. (sig, csign, strength); sig 0 = シグナル無し。"""
    sig, _lc, csign, _st = signal_of_bar(o, h, l, c, s, b)
    if sig == 0:
        return 0, csign, ""
    body = abs(c - o)
    if csign == 1:
        top, under = h - c, o - l
    else:
        top, under = h - o, c - l
    w = top if sig == -1 else under
    if body >= w:  # H1: 実体 >= 勝った側のヒゲ → 実体を逆張り
        sig = -csign
    return sig, csign, ("strong" if sig == csign else "weak")


class K1XVenueStrategy(Strategy):
    def __init__(self, s: str, b: str, strength: str, mode: str) -> None:
        if s not in SMALL or b not in BIG or (s, b) not in gates():
            raise K1XError(f"gate {s!r}/{b!r} is not one of the 13")
        if strength not in STRENGTHS:
            raise K1XError(f"strength must be one of {STRENGTHS}")
        if mode not in MODES:
            raise K1XError(f"mode must be one of {MODES}")
        self.s, self.b, self.keep, self.mode = s, b, strength, mode
        self.pos = 0
        self.n_orders = 0
        self.exit_reasons: dict[str, str] = {}
        self.prev_sig: Optional[tuple[int, str]] = None  # 1 本前の海外の足のシグナル(H3)
        self.cur_sig: Optional[tuple[int, str]] = None   # 同じ窓の海外の足のシグナル
        self.pending_t: Optional[int] = None             # d0 を受けて d1 を待っている時刻
        self.windows = 0

    def _order(self, ctx: StrategyContext, side: str, kind: str, reason: Optional[str]) -> None:
        self.n_orders += 1
        oid = f"{kind}{self.n_orders}"
        ctx.place_order(OrderRequest(side=side, order_type="market", size=1.0, client_order_id=oid))
        if reason is not None:
            self.exit_reasons[oid] = reason

    def _act(self, ctx: StrategyContext, decided: Optional[tuple[int, str]]) -> None:
        if decided is None:
            return
        sig, strength = decided
        if sig == 0 or not (self.keep == "both" or strength == self.keep):
            return  # H2a: 行動対象でない足では何もしない(無効化の枝なし)
        if self.pos == sig:
            return  # 同じ向き: 増し玉はしない
        if self.pos == -sig:
            self._order(ctx, "sell" if self.pos == 1 else "buy", "x", REVERSED if strength == "strong" else OPPOSITE_WEAK)
            self.pos = 0
            if strength != "strong":
                return  # 弱いシグナルは建て直さない
        self._order(ctx, "buy" if sig == 1 else "sell", "e", None)  # 新規 / ドテン
        self.pos = sig

    def on_event(self, event: Event, ctx: StrategyContext) -> None:
        if type(event) is not BarEvent:
            return
        t = int(event.exchange_time_ns)
        if self.mode == "single":
            sig, _cs, st = signal_h1(event.open, event.high, event.low, event.close, self.s, self.b)
            self._act(ctx, self.prev_sig)  # H3: 1 本前のシグナルで、この足の終値で
            self.prev_sig = (sig, st)
            self.windows += 1
            return
        if self.pending_t is None:  # 窓の 1 本目 = d0(海外の足)
            sig, _cs, st = signal_h1(event.open, event.high, event.low, event.close, self.s, self.b)
            self.cur_sig = (sig, st)
            self.pending_t = t
            return
        if t != self.pending_t:  # 窓の 2 本目 = d1(bitFlyer の足)は同じ時刻でなければならない
            raise K1XError(f"two streams out of step: d0 at {self.pending_t}, next bar at {t}")
        self.pending_t = None
        self.windows += 1
        self._act(ctx, self.prev_sig if self.mode == "design" else self.cur_sig)
        self.prev_sig = self.cur_sig


# bitFlyer FX_BTC_JPY(円建て)を 1 単位。tick は成行だけなので使わない(Product に既定が無いので書く)。
PRODUCTS = {
    "FX_BTC_JPY": {"symbol": "FX_BTC_JPY", "venue": "bitflyer", "tick": 1.0, "min_qty": 1.0, "qty_step": 1.0,
                   "quote_ccy": "JPY", "margin": True},
    "BTCUSDT": {"symbol": "BTCUSDT", "venue": "binance", "tick": 0.01, "min_qty": 1.0, "qty_step": 1.0,
                "quote_ccy": "USDT", "margin": False},
}
RULES = {"market_ref": "last_bar_close"}
CONFIG_KEYS = ("instrument", "foot_min", "gate", "strength", "mode", "fill", "costs")
FILL_NAME = "last_bar_close"


def parse_config(cfg: Mapping) -> dict:
    if not isinstance(cfg, Mapping) or set(cfg) != set(CONFIG_KEYS):
        raise K1XError(f"config must have exactly the keys {CONFIG_KEYS}")
    if cfg["instrument"] not in PRODUCTS:
        raise K1XError(f"instrument must be one of {sorted(PRODUCTS)}")
    if type(cfg["foot_min"]) is not int or cfg["foot_min"] <= 0:
        raise K1XError("foot_min must be an int > 0")
    if cfg["mode"] not in MODES:
        raise K1XError(f"mode must be one of {MODES}")
    if cfg["fill"] != FILL_NAME:
        raise K1XError(f"fill must be {FILL_NAME!r}")
    c = cfg["costs"]
    if set(c) != {"maker_fee_rate", "taker_fee_rate", "source"} or not str(c["source"]).strip():
        raise K1XError("costs must be {maker_fee_rate, taker_fee_rate, source}")
    return {"s": str(cfg["gate"]["s"]), "b": str(cfg["gate"]["b"]), "strength": cfg["strength"], "mode": cfg["mode"],
            "rates": {"maker": float(c["maker_fee_rate"]), "taker": float(c["taker_fee_rate"])}}


class K1XSetup:
    """bot.bt.repro.runner の setup。"""

    def __init__(self) -> None:
        self.last: Optional[K1XVenueStrategy] = None

    def identity(self) -> dict:
        src = inspect.getsource(inspect.getmodule(K1XSetup))
        return {"name": f"{__name__}:K1XSetup", "source_sha256": hashlib.sha256(src.encode()).hexdigest()}

    def build(self, config: Mapping, seed: int) -> Parts:
        p = parse_config(config)
        strat = K1XVenueStrategy(p["s"], p["b"], p["strength"], p["mode"])
        self.last = strat
        prod = PRODUCTS[config["instrument"]]
        venue = SimVenue(product=Product(**prod), rules=VenueRules(**RULES), fill=FillSpec(tier=2),
                         costs=CostSchedule(maker_rate=0.0, taker_rate=0.0, source=config["costs"]["source"], spread=0.0),
                         faults=FaultPlan(()), l3=None)
        return Parts(strategy=strat, fill_model=venue, latency_model=ZeroLatency(),
                     cost_model=DeclaredFeeCost(p["rates"]), account=NullAccount(), exit_reasons=strat.exit_reasons,
                     currency=prod["quote_ccy"],
                     notes={"fill": "SimVenue market_ref last_bar_close: 直前に受けた足の終値(design/sameclose では "
                                    "同じ窓の 2 本目 = bitFlyer の足)",
                            "mode": p["mode"], "seed": "unused",
                            "streams": "design/sameclose: d0 = 海外の足, d1 = bitFlyer の足(同じ窓)"})


__all__ = ["K1XVenueStrategy", "K1XSetup", "K1XError", "signal_h1", "gate_label", "MODES"]

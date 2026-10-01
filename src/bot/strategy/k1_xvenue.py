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
  "design"     2 本の流れ(シグナル = 海外の足、価格 = bitFlyer の足。結合・畳み済みで窓が同じ)。同じ窓の
               2 本がそろったときに「1 本前の窓の海外のシグナル」(H3)で行動し、約定の口(SimVenue、
               market_ref = last_bar_close、streams = 価格の流れ)は価格の流れの最後の足 = bitFlyer の
               その窓の終値で約定する
  "sameclose"  参考列 (iii): 同じ 2 本の流れで、窓がそろったときに「同じ窓の海外のシグナル」で行動する
               (H3 を外す。約定は同じ窓の bitFlyer の終値 = 海外の足の確定と同時刻。取れない価格)
  "single"     参考列 (i): 1 本の流れ(海外の足だけ)。H3 で行動し、海外の足の終値で約定する

2 本の流れの見分け(G-1 の直し、2026-10-01): 核の事象は流れの名前を持つ(Event.stream、核が取り込みの
ときに付ける)。戦略は config の streams で名指しされた名前で、シグナルの足と価格の足を見分ける。同じ窓
(足の開始時刻)の 2 本がそろったときに行動するので、同じ時刻の 2 本がどちらの順に届いても同じ。窓の
開始時刻が両側で一致しない(片方だけの窓が残ったまま次の窓の足が来る)・名指しに無い流れの足が来る・
同じ窓に同じ流れの足が 2 本来る、のどれかが起きたら K1XError で止まる。約定の口は価格の流れの足だけを
見る(SimVenue(streams=...))ので、シグナルの流れの足が約定の値を上書きすることは無い。

入力の 2 つの形(config の prepare):
  "none"       畳んだ足のファイルをそのまま流れにする。streams = {"signal": ["d0"], "price": ["d1"]}
               (記録の口 runner の流れの名前は DataInput の順に d0, d1, ...)
  "join_fold"  生の 1 分足(封印の台帳に載ったファイルを範囲つきで、G-3)を流れにし、この setup の
               prepare が XVENUE_PREREG.md §2 の「揃え方」で結合・畳みをする: streams のシグナル側の
               流れを順につないだ分足と価格側の分足を、それぞれ分の頭に切り下げ(bars_from_bars 60 秒)、
               分の開始時刻の積集合を取り、foot_min 分の窓に畳む(両側で窓の開始時刻の列が一致しな
               ければ止まる)。出力の流れの名前は "signal" と "price"。single は結合せずにシグナル側だけ
               畳む。約定の無い分を落とす規則はデータ層の宣言(Binance = synthetic → drop、bitFlyer =
               no_trade → drop、G-2)で、prepare は落とさない

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
    def __init__(self, s: str, b: str, strength: str, mode: str, signal: str = "d0", price: str = "d1") -> None:
        if s not in SMALL or b not in BIG or (s, b) not in gates():
            raise K1XError(f"gate {s!r}/{b!r} is not one of the 13")
        if strength not in STRENGTHS:
            raise K1XError(f"strength must be one of {STRENGTHS}")
        if mode not in MODES:
            raise K1XError(f"mode must be one of {MODES}")
        if type(signal) is not str or not signal or type(price) is not str or not price:
            raise K1XError("signal / price must be non-empty stream names")
        if mode == "single" and signal != price:
            raise K1XError("single reads one stream: signal and price name the same stream")
        if mode != "single" and signal == price:
            raise K1XError(f"{mode} reads two streams: signal and price must differ")
        self.s, self.b, self.keep, self.mode = s, b, strength, mode
        self.signal, self.price = signal, price
        self.pos = 0
        self.n_orders = 0
        self.exit_reasons: dict[str, str] = {}
        self.prev_sig: Optional[tuple[int, str]] = None  # 1 本前の窓の海外の足のシグナル(H3)
        self.pending: dict[int, dict[str, BarEvent]] = {}  # 窓の開始時刻 -> {流れの名前: 足}(そろうまで)
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
        name = event.stream
        if self.mode == "single":
            if name != self.signal:
                raise K1XError(f"single: a bar of stream {name!r}, the config names only {self.signal!r}")
            sig, _cs, st = signal_h1(event.open, event.high, event.low, event.close, self.s, self.b)
            self._act(ctx, self.prev_sig)  # H3: 1 本前のシグナルで、この足の終値で
            self.prev_sig = (sig, st)
            self.windows += 1
            return
        if name not in (self.signal, self.price):
            raise K1XError(f"a bar of stream {name!r}: the config names {self.signal!r} (signal) and "
                           f"{self.price!r} (price)")
        start = event.start_time_ns
        if start is None:
            raise K1XError(f"a bar of stream {name!r} without start_time_ns: the window cannot be named")
        w = self.pending.setdefault(int(start), {})
        if name in w:
            raise K1XError(f"two bars of stream {name!r} for the window starting at {start}")
        w[name] = event
        if len(self.pending) > 1:  # 片方だけの窓が残ったまま次の窓の足が来た = 窓の列が一致しない
            raise K1XError(f"two streams out of step: windows {sorted(self.pending)} are each missing a stream")
        if len(w) < 2:
            return
        del self.pending[int(start)]
        sb = w[self.signal]
        sig, _cs, st = signal_h1(sb.open, sb.high, sb.low, sb.close, self.s, self.b)
        cur = (sig, st)
        self.windows += 1
        self._act(ctx, self.prev_sig if self.mode == "design" else cur)
        self.prev_sig = cur


# bitFlyer FX_BTC_JPY(円建て)を 1 単位。tick は成行だけなので使わない(Product に既定が無いので書く)。
PRODUCTS = {
    "FX_BTC_JPY": {"symbol": "FX_BTC_JPY", "venue": "bitflyer", "tick": 1.0, "min_qty": 1.0, "qty_step": 1.0,
                   "quote_ccy": "JPY", "margin": True},
    "BTCUSDT": {"symbol": "BTCUSDT", "venue": "binance", "tick": 0.01, "min_qty": 1.0, "qty_step": 1.0,
                "quote_ccy": "USDT", "margin": False},
}
RULES = {"market_ref": "last_bar_close"}
CONFIG_KEYS = ("instrument", "foot_min", "gate", "strength", "mode", "fill", "costs", "streams", "prepare")
FILL_NAME = "last_bar_close"
PREPARES = ("none", "join_fold")
NS = 1_000_000_000


def _names(v, where: str) -> tuple[str, ...]:
    if not isinstance(v, (list, tuple)) or not v or any(type(x) is not str or not x for x in v) or len(set(v)) != len(v):
        raise K1XError(f"streams.{where} must be a non-empty list of distinct stream names, got {v!r}")
    return tuple(v)


def _bar_columns(events) -> dict:
    """1 本の流れ(時刻順の BarEvent)を bars_from_bars の列に。"""
    cols = {k: [] for k in ("t", "o", "h", "l", "c", "v")}
    for e in events:
        if type(e) is not BarEvent or e.start_time_ns is None:
            raise K1XError(f"join_fold reads bars with start_time_ns, got {type(e).__name__}")
        cols["t"].append(int(e.start_time_ns))
        cols["o"].append(e.open)
        cols["h"].append(e.high)
        cols["l"].append(e.low)
        cols["c"].append(e.close)
        cols["v"].append(e.volume)
    return cols


def _concat(streams: Mapping, names: tuple[str, ...]) -> dict:
    out = {k: [] for k in ("t", "o", "h", "l", "c", "v")}
    for n in names:
        if n not in streams:
            raise K1XError(f"join_fold: no loaded stream {n!r} (have {sorted(streams)})")
        cols = _bar_columns(streams[n])
        if out["t"] and cols["t"] and cols["t"][0] <= out["t"][-1]:
            raise K1XError(f"join_fold: stream {n!r} does not start after the stream before it")
        for k in out:
            out[k].extend(cols[k])
    return out


def _minutes(cols: dict) -> dict:
    """分の境界に乗っていない行を分の頭に切り下げる(bars_from_bars 60 秒。XVENUE_PREREG.md §2「UTC の分」)。"""
    import numpy as np
    from bot.bt.vector.bars import bars_from_bars
    out = bars_from_bars(cols["t"], cols["o"], cols["h"], cols["l"], cols["c"], cols["v"], 60)
    return {"t": np.array([b["start_ns"] for b in out], dtype=np.int64), "o": np.array([b["open"] for b in out]),
            "h": np.array([b["high"] for b in out]), "l": np.array([b["low"] for b in out]),
            "c": np.array([b["close"] for b in out]), "v": np.array([b["volume"] for b in out])}


def _events(bars: list[dict], foot_ns: int) -> tuple:
    return tuple(BarEvent(received_time_ns=b["start_ns"] + foot_ns, start_time_ns=b["start_ns"], open=b["open"],
                          high=b["high"], low=b["low"], close=b["close"], volume=b["volume"]) for b in bars)


def join_fold(streams: Mapping, signal: tuple[str, ...], price: tuple[str, ...], foot_min: int, joined: bool) -> dict:
    """XVENUE_PREREG.md §2「揃え方」: 分の頭に切り下げ → UTC の分の内部結合 → 結合後に両側を同じ窓で畳む。
    joined False(single)はシグナル側だけを畳む。返り値 {"signal": 事象, "price": 事象}(single は "signal" だけ)。"""
    import numpy as np
    from bot.bt.vector.bars import bars_from_bars
    sm = _minutes(_concat(streams, signal))
    foot_s = foot_min * 60
    if not joined:
        sb = bars_from_bars(sm["t"], sm["o"], sm["h"], sm["l"], sm["c"], sm["v"], foot_s)
        return {"signal": _events(sb, foot_s * NS)}
    pm = _minutes(_concat(streams, price))
    _common, si, pi = np.intersect1d(sm["t"], pm["t"], assume_unique=True, return_indices=True)
    S = {k: v[si] for k, v in sm.items()}
    P = {k: v[pi] for k, v in pm.items()}
    sb = bars_from_bars(S["t"], S["o"], S["h"], S["l"], S["c"], S["v"], foot_s)
    pb = bars_from_bars(P["t"], P["o"], P["h"], P["l"], P["c"], P["v"], foot_s)
    if [b["start_ns"] for b in sb] != [b["start_ns"] for b in pb]:
        raise K1XError("join_fold: the two venues' windows differ after the join")
    return {"signal": _events(sb, foot_s * NS), "price": _events(pb, foot_s * NS)}


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
    if cfg["prepare"] not in PREPARES:
        raise K1XError(f"prepare must be one of {PREPARES}")
    st = cfg["streams"]
    if not isinstance(st, Mapping) or set(st) != {"signal", "price"}:
        raise K1XError("streams must be {signal: [...], price: [...]}")
    sig_names, px_names = _names(st["signal"], "signal"), _names(st["price"], "price")
    if cfg["mode"] == "single":
        if sig_names != px_names:
            raise K1XError("single: streams.signal and streams.price must name the same stream(s)")
    elif set(sig_names) & set(px_names):
        raise K1XError("streams.signal and streams.price must not share a stream")
    if cfg["prepare"] == "none" and (len(sig_names) != 1 or len(px_names) != 1):
        raise K1XError("prepare none: streams.signal and streams.price name one stream each")
    return {"s": str(cfg["gate"]["s"]), "b": str(cfg["gate"]["b"]), "strength": cfg["strength"], "mode": cfg["mode"],
            "rates": {"maker": float(c["maker_fee_rate"]), "taker": float(c["taker_fee_rate"])},
            "prepare": cfg["prepare"], "signal": sig_names, "price": px_names}


class K1XSetup:
    """bot.bt.repro.runner の setup。"""

    def __init__(self) -> None:
        self.last: Optional[K1XVenueStrategy] = None

    def identity(self) -> dict:
        src = inspect.getsource(inspect.getmodule(K1XSetup))
        return {"name": f"{__name__}:K1XSetup", "source_sha256": hashlib.sha256(src.encode()).hexdigest()}

    def build(self, config: Mapping, seed: int) -> Parts:
        p = parse_config(config)
        if p["prepare"] == "none":
            sig_name, px_name = p["signal"][0], p["price"][0]
            prepare = None
        else:
            sig_name = "signal"
            px_name = "signal" if p["mode"] == "single" else "price"
            sn, pn, foot, joined = p["signal"], p["price"], config["foot_min"], p["mode"] != "single"
            prepare = lambda streams: join_fold(streams, sn, pn, foot, joined)  # noqa: E731
        strat = K1XVenueStrategy(p["s"], p["b"], p["strength"], p["mode"], signal=sig_name, price=px_name)
        self.last = strat
        prod = PRODUCTS[config["instrument"]]
        venue = SimVenue(product=Product(**prod), rules=VenueRules(**RULES), fill=FillSpec(tier=2),
                         costs=CostSchedule(maker_rate=0.0, taker_rate=0.0, source=config["costs"]["source"], spread=0.0),
                         faults=FaultPlan(()), l3=None, streams=(px_name,))
        return Parts(strategy=strat, fill_model=venue, latency_model=ZeroLatency(),
                     cost_model=DeclaredFeeCost(p["rates"]), account=NullAccount(), exit_reasons=strat.exit_reasons,
                     currency=prod["quote_ccy"], prepare=prepare,
                     notes={"fill": f"SimVenue market_ref last_bar_close, streams = ({px_name!r},): 価格の流れの "
                                    f"最後の足の終値",
                            "mode": p["mode"], "seed": "unused", "prepare": p["prepare"],
                            "streams": {"signal": sig_name, "price": px_name,
                                        "loaded_signal": list(p["signal"]), "loaded_price": list(p["price"])}})


__all__ = ["K1XVenueStrategy", "K1XSetup", "K1XError", "signal_h1", "gate_label", "join_fold", "MODES", "PREPARES"]

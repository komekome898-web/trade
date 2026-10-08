"""約定の決まり(決まりの文書の 3)の部品。足も記録も読まない、値段と足の範囲だけの関数。"""
from __future__ import annotations

from decimal import ROUND_FLOOR, Context, Decimal, ROUND_HALF_EVEN

# 呼ぶ側の Decimal の設定に左右されないよう、切り捨ての計算には専用の設定(桁数 28)を使う。
_CTX = Context(prec=28, rounding=ROUND_HALF_EVEN)


def floor_to_tick(price_dec: Decimal, tick: float) -> float:
    """値段(Decimal)を刻みに切り捨てて float に戻す。売りも買いも同じ。

    `Decimal(repr(値段)) / Decimal(repr(刻み))` を ROUND_FLOOR で整数にし、`Decimal(repr(刻み))` を掛ける。
    """
    t = Decimal(repr(float(tick)))
    n = _CTX.divide(price_dec, t).to_integral_value(rounding=ROUND_FLOOR)
    return float(_CTX.multiply(n, t))


def limit_price(px_calc: float, tick: float) -> float:
    """指値・利確の値段(戦略が出した値段を刻みに切り捨てたもの)。"""
    return floor_to_tick(Decimal(repr(float(px_calc))), tick)


def level_price(root_fill_px: float, offset: float, tick: float) -> float:
    """段の値段 = (根の最初の約定値段 + 距離)を刻みに切り捨てたもの。足し算は 10 進で行う。"""
    s = _CTX.add(Decimal(repr(float(root_fill_px))), Decimal(repr(float(offset))))
    return floor_to_tick(s, tick)


def limit_fill(side: str, px: float, bar_open: float, bar_high: float, bar_low: float):
    """指値と同じ決まり。約定すれば (値段, case) を、しなければ None を返す。

    範囲の内(安値 <= 値段 <= 高値)なら値段で range。約定する向きに範囲の外
    (買いは値段 > 高値、売りは値段 < 安値)なら始値で open。それ以外は約定しない。
    """
    if bar_low <= px <= bar_high:
        return px, "range"
    if side == "buy" and px > bar_high:
        return bar_open, "open"
    if side == "sell" and px < bar_low:
        return bar_open, "open"
    return None


def inside_fill(px: float, bar_high: float, bar_low: float, case: str):
    """根の足の段(anchor_bar)・親の足の利確(entry_bar): 範囲の内だけ値段で約定し、外は約定しない。"""
    if bar_low <= px <= bar_high:
        return px, case
    return None

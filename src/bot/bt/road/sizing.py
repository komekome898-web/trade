"""量のツール: 1 段の量(BTC)を証拠金から決める(L-745・L-746・L-756)。

オーナーの逐語:
- L-745「**まず証拠金の何%を注文に使うか決めて、その後何段持てるか決めて 20万×○%÷段数÷その時の価格=1段の単位やろ**」
- L-746「**70% 段数は戦略毎に変える(基本は1で計算) 0.001以下は切り捨て**」
- L-744「**今の段階でこんなんしたらそれまでの取引での証拠金に依存して正確な戦略の効果測れへんやんけ**」
  (証拠金は毎回 20 万円で固定。前の取引の損益を足す口はこの関数に無い)
- L-756「**1.a 2.よい 3. 0.001**」(ドル建ては建てる時点の USDJPY で円→ドル。USDT は USD とみなす。0.001 BTC)

式:
- 円建て(JPY):            margin_jpy × use_ratio ÷ levels ÷ price
- ドル建て(USD・USDT):   margin_jpy × use_ratio ÷ levels ÷ (price × usdjpy_at_entry)
- 0.001 BTC 未満は切り捨て。切り捨てて 0 になったら 0 を返す(その点は「建てられなかった」)。

小数の誤差で落ちないよう、入力は全部 `Decimal(repr(float(x)))`(最短の 10 進の文字列)にしてから
Decimal で計算する(`bot.bt.orders.product._dec` と同じ作り)。例: 500 万円・1 段 → 0.028(0.027 にならない)。
"""
from __future__ import annotations

import math
from decimal import ROUND_DOWN, Decimal

MARGIN_JPY = 200000  # L-743「**俺は20万って言ってたのに**」
USE_RATIO = 0.70  # L-746「**70%**」
STEP_BTC = Decimal("0.001")  # L-746「**0.001以下は切り捨て**」/ L-756「**3. 0.001**」
QUOTE_CCYS = ("JPY", "USD", "USDT")


class SizingError(ValueError):
    """量のツールが受け付けない入力。"""


def _dec(name: str, x: object) -> Decimal:
    if isinstance(x, bool) or not isinstance(x, (int, float, Decimal)):
        raise SizingError(f"{name} は数で渡す(受け取ったのは {type(x).__name__})")
    if isinstance(x, Decimal):
        d = x
    else:
        if not math.isfinite(float(x)):
            raise SizingError(f"{name} が有限でない: {x!r}")
        d = Decimal(repr(float(x))) if isinstance(x, float) else Decimal(int(x))
    if not d.is_finite() or d <= 0:
        raise SizingError(f"{name} は 0 より大きい有限の数: {x!r}")
    return d


def size_per_level(*, margin_jpy: float = MARGIN_JPY, use_ratio: float = USE_RATIO, levels: int, price: float,
                   quote_ccy: str, usdjpy_at_entry: float | None = None) -> float:
    """1 段の量(BTC)。0.001 BTC 未満は切り捨て、足りなければ 0.0。

    levels: 段数(戦略ごと。基本は 1)。price: 建てる時点の値段(quote_ccy 建て)。
    usdjpy_at_entry: ドル建て(USD・USDT)のときだけ渡す、建てる時点の USDJPY。円建てで渡したら止める
    (どちらの式で計算したかが曖昧になるため)。
    """
    return size_detail(margin_jpy=margin_jpy, use_ratio=use_ratio, levels=levels, price=price, quote_ccy=quote_ccy,
                       usdjpy_at_entry=usdjpy_at_entry)[1]


def size_detail(*, margin_jpy: float = MARGIN_JPY, use_ratio: float = USE_RATIO, levels: int, price: float,
                quote_ccy: str, usdjpy_at_entry: float | None = None) -> tuple[Decimal, float]:
    """(切り捨て前の量, 切り捨て後の量)。切り捨て後の量は `size_per_level` の答えそのもの。

    切り捨て前の量は Decimal(既定の文脈の 28 桁。割り切れないときはその桁で丸めた値)。注文の表に
    「量の計算に使った値」として残すために出す(L-767「**b残す**」)。
    """
    if type(levels) is not int or levels < 1:
        raise SizingError(f"levels は 1 以上の整数: {levels!r}")
    if quote_ccy not in QUOTE_CCYS:
        raise SizingError(f"quote_ccy は {QUOTE_CCYS} のどれか: {quote_ccy!r}")
    m = _dec("margin_jpy", margin_jpy)
    r = _dec("use_ratio", use_ratio)
    if r > 1:
        raise SizingError(f"use_ratio は 1 以下(証拠金の割合): {use_ratio!r}")
    p = _dec("price", price)
    if quote_ccy == "JPY":
        if usdjpy_at_entry is not None:
            raise SizingError("円建てに usdjpy_at_entry を渡している")
        denom = p
    else:
        if usdjpy_at_entry is None:
            raise SizingError(f"{quote_ccy} 建ては建てる時点の usdjpy_at_entry が要る(L-756)")
        denom = p * _dec("usdjpy_at_entry", usdjpy_at_entry)
    raw = m * r / Decimal(levels) / denom
    q = raw.quantize(STEP_BTC, rounding=ROUND_DOWN)
    return raw, float(q)

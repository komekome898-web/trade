"""単純な測りの道の検査 1: 約定の作り直し。

走らせが書いた注文の記録と足から、約定を別に書いた決まり(決まりの文書の 3)で計算し直し、
走らせの約定の記録と 1 字違わず同じかを比べる。使い方は `refill(bars, out_dir, side)`。
"""
from .replay import refill

__all__ = ["refill"]

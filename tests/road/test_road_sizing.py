"""量のツールの受け入れの場面 4(委任文 DELEGATION_one_road_step1.md)。"""
from __future__ import annotations

import pytest

from bot.bt.road.sizing import SizingError, size_per_level


def test_scene4_15m_one_level():
    assert size_per_level(levels=1, price=15_000_000, quote_ccy="JPY") == 0.009


def test_scene4_5m_five_levels():
    assert size_per_level(levels=5, price=5_000_000, quote_ccy="JPY") == 0.005


def test_scene4_5m_one_level_no_float_error():
    q = size_per_level(levels=1, price=5_000_000, quote_ccy="JPY")
    assert q == 0.028
    assert repr(q) == "0.028"


def test_exact_multiples_do_not_drop_a_step():
    # 140000 円 ÷ 値段 がちょうど 0.001 の倍数になる値段で、1 刻みも落ちないこと。
    # 浮動小数で素直に floor(x / 0.001) * 0.001 とすると、例えば 800,000 円で 0.175 が 0.174 に落ちる
    import math
    x = 200000 * 0.70 / 1 / 800_000
    assert round(math.floor(x / 0.001) * 0.001, 9) == 0.174  # 素直な計算は落ちる(この試験が効いている印)
    assert size_per_level(levels=1, price=800_000, quote_ccy="JPY") == 0.175
    for k in range(1, 1000):
        if 140_000_000 % k == 0:
            q = size_per_level(levels=1, price=140_000_000 // k, quote_ccy="JPY")
            assert repr(q) == repr(k / 1000), (k, q)


def test_defaults_are_200k_and_70pct():
    assert size_per_level(levels=1, price=5_000_000, quote_ccy="JPY") == \
        size_per_level(margin_jpy=200000, use_ratio=0.70, levels=1, price=5_000_000, quote_ccy="JPY")


def test_usd_uses_usdjpy_at_entry_and_usdt_is_usd():
    # 140000 円 ÷ (30000 USD × 150) = 0.0311... → 0.031
    assert size_per_level(levels=1, price=30000, quote_ccy="USD", usdjpy_at_entry=150) == 0.031
    assert size_per_level(levels=1, price=30000, quote_ccy="USDT", usdjpy_at_entry=150) == 0.031


def test_below_step_is_zero():
    assert size_per_level(levels=200, price=5_000_000, quote_ccy="JPY") == 0.0


@pytest.mark.parametrize("kw", [
    dict(levels=0, price=1.0, quote_ccy="JPY"),
    dict(levels=1, price=-1.0, quote_ccy="JPY"),
    dict(levels=1, price=1.0, quote_ccy="EUR"),
    dict(levels=1, price=1.0, quote_ccy="USD"),  # USDJPY が無い
    dict(levels=1, price=1.0, quote_ccy="JPY", usdjpy_at_entry=150),
    dict(levels=1, price=1.0, quote_ccy="JPY", use_ratio=1.5),
])
def test_refuses(kw):
    with pytest.raises(SizingError):
        size_per_level(**kw)

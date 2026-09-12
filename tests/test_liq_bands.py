"""価格帯ごとの積み上げから清算価格帯を予測できるかの測定器(`bot.research.liq_bands`)
の単体テスト。

**ここでも判定はしない**。確認するのは (1) 積み上げの分布が bin 境界を含めて期待どおり
になること、(2) 起点 `t` より後のデータを変えても候補が構造的に変わらないこと
(約定側・建玉側の両方)、(3) 建玉が無い区間で手法(b)だけ NaN になり行が消えないこと、
(4) 照合の距離計算が帯の内側・外側・境界で正しいこと。合成データのみを使う。
"""
from __future__ import annotations

import math

from bot.research.liq_bands import (
    Band,
    BandCandidates,
    Trade,
    build_candidates_at,
    candidate_bands,
    match_liquidation_to_bands,
    match_liquidations_to_bands,
    open_interest_bands,
    volume_at_price,
)
from bot.research.liq_response import LiquidationEvent, PriceSeries


def _ev(ts_ms: int, price: float, side: str = "long", qty: float = 1.0, exchange: str = "binance_cm"):
    return LiquidationEvent(exchange=exchange, ts_ms=ts_ms, side=side, qty=qty, price=price)


# --------------------------------------------------------------------------- #
# (1) 積み上げの分布(bin 境界を含む)
# --------------------------------------------------------------------------- #

def test_volume_at_price_bins_and_boundary():
    trades = [
        Trade(ts_ms=1000, price=100.0, qty=1.0),   # bin_low=100 (境界ちょうど→上のbin)
        Trade(ts_ms=1000, price=99.999, qty=2.0),  # bin_low=50
        Trade(ts_ms=1000, price=149.999, qty=3.0), # bin_low=100
        Trade(ts_ms=1000, price=150.0, qty=4.0),   # bin_low=150 (境界ちょうど)
    ]
    profile = volume_at_price(trades, t_ms=2000, lookback_ms=10_000, bin_size=50.0)
    assert profile.bins[50.0] == 2.0
    assert profile.bins[100.0] == 1.0 + 3.0
    assert profile.bins[150.0] == 4.0
    assert profile.n_points == 4


def test_volume_at_price_respects_lookback_window():
    trades = [
        Trade(ts_ms=0, price=100.0, qty=100.0),   # ちょうど下端(t-lookback)→ 含まない(半開区間)
        Trade(ts_ms=1001, price=200.0, qty=1.0),  # 窓の中
        Trade(ts_ms=5000, price=300.0, qty=1.0),  # 起点そのもの → 含む
    ]
    profile = volume_at_price(trades, t_ms=5000, lookback_ms=4000, bin_size=50.0)
    assert 100.0 not in profile.bins
    assert profile.bins[200.0] == 1.0
    assert profile.bins[300.0] == 1.0
    assert profile.n_points == 2


def test_open_interest_bands_weights_increasing_segments_only():
    # 0->1000: +50 (増加。重みは ts=1000 時点の代表価格の bin へ)
    # 1000->2000: -30 (減少。無視)
    # 2000->3000: +60 (増加。重みは ts=3000 時点の代表価格の bin へ)
    oi = PriceSeries.from_trades([(0, 100.0), (1000, 150.0), (2000, 120.0), (3000, 180.0)])
    price = PriceSeries.from_trades([(0, 30000.0), (1000, 30000.0), (2000, 30100.0), (3000, 30200.0)])
    profile = open_interest_bands(oi, price, t_ms=3000, lookback_ms=10_000, bin_size=50.0)
    assert profile.bins == {30000.0: 50.0, 30200.0: 60.0}
    assert profile.n_increments == 2


def test_open_interest_bands_missing_funding_and_ls_is_none():
    oi = PriceSeries.from_trades([(0, 100.0), (1000, 150.0)])
    price = PriceSeries.from_trades([(0, 100.0), (1000, 100.0)])
    profile = open_interest_bands(oi, price, t_ms=1000, lookback_ms=10_000, bin_size=50.0)
    assert profile.funding_rate is None
    assert profile.long_short_ratio is None


def test_open_interest_bands_reads_funding_and_ls_when_present():
    oi = PriceSeries.from_trades([(0, 100.0), (1000, 150.0)])
    price = PriceSeries.from_trades([(0, 100.0), (1000, 100.0)])
    funding = PriceSeries.from_trades([(0, 0.0001), (900, 0.00015)])
    ls = PriceSeries.from_trades([(0, 1.1), (900, 1.3)])
    profile = open_interest_bands(oi, price, t_ms=1000, lookback_ms=10_000, bin_size=50.0,
                                   funding_series=funding, long_short_series=ls)
    assert profile.funding_rate == 0.00015
    assert profile.long_short_ratio == 1.3


# --------------------------------------------------------------------------- #
# (2) 先読みが構造的に起きないこと(約定側・建玉側の両方)
# --------------------------------------------------------------------------- #

def test_volume_at_price_ignores_future_trades_structurally():
    """`t` より後の約定を trades に含めて内容を変えても、結果は変わらない。"""
    past = [Trade(ts_ms=100, price=100.0, qty=5.0)]
    t = 200
    future_a = Trade(ts_ms=300, price=9999.0, qty=1.0)
    future_b = Trade(ts_ms=300, price=1.0, qty=1_000_000.0)
    profile_a = volume_at_price(past + [future_a], t_ms=t, lookback_ms=1000, bin_size=50.0)
    profile_b = volume_at_price(past + [future_b], t_ms=t, lookback_ms=1000, bin_size=50.0)
    assert profile_a.bins == profile_b.bins == {100.0: 5.0}
    assert profile_a.n_points == profile_b.n_points == 1


def test_open_interest_bands_ignores_future_oi_and_price_structurally():
    """`t` より後の OI・価格の点を変えても、bins・funding・L/S比の結果は変わらない。"""
    t = 1000
    oi_a = PriceSeries.from_trades([(0, 100.0), (500, 150.0), (2000, 1.0)])
    oi_b = PriceSeries.from_trades([(0, 100.0), (500, 150.0), (2000, 999_999.0)])
    price_a = PriceSeries.from_trades([(0, 30000.0), (500, 30050.0), (2000, 1.0)])
    price_b = PriceSeries.from_trades([(0, 30000.0), (500, 30050.0), (2000, 999_999.0)])
    funding_a = PriceSeries.from_trades([(0, 0.0001), (2000, -5.0)])
    funding_b = PriceSeries.from_trades([(0, 0.0001), (2000, 5.0)])

    profile_a = open_interest_bands(oi_a, price_a, t_ms=t, lookback_ms=10_000, bin_size=50.0,
                                     funding_series=funding_a)
    profile_b = open_interest_bands(oi_b, price_b, t_ms=t, lookback_ms=10_000, bin_size=50.0,
                                     funding_series=funding_b)
    assert profile_a.bins == profile_b.bins
    assert profile_a.n_increments == profile_b.n_increments
    assert profile_a.funding_rate == profile_b.funding_rate == 0.0001


def test_build_candidates_at_ignores_future_data_end_to_end():
    """トレード・OI・価格・L/S比のいずれも t より後を変えても候補帯全体が変わらない。"""
    t = 500
    trades_a = [Trade(ts_ms=100, price=30000.0, qty=1.0), Trade(ts_ms=600, price=1.0, qty=1.0)]
    trades_b = [Trade(ts_ms=100, price=30000.0, qty=1.0), Trade(ts_ms=600, price=999_999.0, qty=999.0)]
    oi_a = PriceSeries.from_trades([(0, 100.0), (400, 150.0), (5000, 1.0)])
    oi_b = PriceSeries.from_trades([(0, 100.0), (400, 150.0), (5000, 999_999.0)])
    price_a = PriceSeries.from_trades([(0, 30000.0), (400, 30010.0), (5000, 1.0)])
    price_b = PriceSeries.from_trades([(0, 30000.0), (400, 30010.0), (5000, 999_999.0)])
    ls_a = PriceSeries.from_trades([(0, 1.0), (400, 1.2), (5000, 1.0)])
    ls_b = PriceSeries.from_trades([(0, 1.0), (400, 1.2), (5000, 99.0)])

    cand_a = build_candidates_at(trades_a, oi_a, price_a, t_ms=t, lookback_ms=10_000,
                                  price_bin_size=50.0, long_short_series=ls_a)
    cand_b = build_candidates_at(trades_b, oi_b, price_b, t_ms=t, lookback_ms=10_000,
                                  price_bin_size=50.0, long_short_series=ls_b)

    assert cand_a is not None and cand_b is not None
    assert cand_a.current_price == cand_b.current_price
    assert cand_a.by_method["a"] == cand_b.by_method["a"]
    assert cand_a.by_method["b"] == cand_b.by_method["b"]
    assert cand_a.by_method["c"] == cand_b.by_method["c"]
    assert cand_a.long_short_ratio == cand_b.long_short_ratio


# --------------------------------------------------------------------------- #
# (3) 建玉が無い区間で手法(b)だけ NaN になり、行が消えないこと
# --------------------------------------------------------------------------- #

def test_candidate_bands_method_b_empty_when_no_oi_data():
    vol_profile = volume_at_price(
        [Trade(ts_ms=0, price=30000.0, qty=1.0)], t_ms=0, lookback_ms=1000, bin_size=50.0
    )
    empty_oi_profile = open_interest_bands(PriceSeries(), PriceSeries(), t_ms=0, lookback_ms=1000, bin_size=50.0)
    cand = candidate_bands(vol_profile, empty_oi_profile, current_price=30000.0, t_ms=0)

    assert cand.by_method["b"] == []
    assert cand.by_method["a"] != []
    assert cand.by_method["c"] != []

    rows = match_liquidations_to_bands([_ev(ts_ms=1, price=30000.0)], cand)
    assert len(rows) == 1  # 行は消えない
    row = rows[0]
    assert math.isnan(row["distance_bp_b"])
    assert math.isnan(row["in_band_b"])  # bool ではなく NaN(候補が無いことを明示)
    assert not math.isnan(row["distance_bp_a"])  # 他の手法は NaN にならない
    assert math.isnan(row["funding_rate_at_t"])  # funding も引けていないので NaN


# --------------------------------------------------------------------------- #
# (4) 照合の距離計算(帯の内側・外側・境界)
# --------------------------------------------------------------------------- #

def test_match_distance_bp_inside_outside_boundary():
    band = Band(method="a", label="x", low=100.0, high=110.0, weight=1.0)
    cand = BandCandidates(
        t_ms=0, current_price=105.0, by_method={"a": [band], "b": [], "c": []},
        funding_rate=None, long_short_ratio=None,
    )

    inside = match_liquidation_to_bands(105.0, cand)
    assert inside["in_band_a"] is True
    assert inside["distance_bp_a"] == 0.0

    boundary_low = match_liquidation_to_bands(100.0, cand)
    assert boundary_low["in_band_a"] is True
    assert boundary_low["distance_bp_a"] == 0.0

    boundary_high = match_liquidation_to_bands(110.0, cand)
    assert boundary_high["in_band_a"] is True
    assert boundary_high["distance_bp_a"] == 0.0

    outside_above = match_liquidation_to_bands(120.0, cand)
    assert outside_above["in_band_a"] is False
    expected_bp_above = (120.0 - 110.0) / 120.0 * 10_000.0
    assert math.isclose(outside_above["distance_bp_a"], expected_bp_above)

    outside_below = match_liquidation_to_bands(90.0, cand)
    assert outside_below["in_band_a"] is False
    expected_bp_below = (100.0 - 90.0) / 90.0 * 10_000.0
    assert math.isclose(outside_below["distance_bp_a"], expected_bp_below)


def test_match_picks_nearest_of_multiple_bands():
    near = Band(method="a", label="near", low=100.0, high=101.0, weight=1.0)
    far = Band(method="a", label="far", low=200.0, high=201.0, weight=1.0)
    cand = BandCandidates(
        t_ms=0, current_price=105.0, by_method={"a": [far, near], "b": [], "c": []},
        funding_rate=None, long_short_ratio=None,
    )
    row = match_liquidation_to_bands(102.0, cand)
    assert row["in_band_a"] is False
    expected_bp = (102.0 - 101.0) / 102.0 * 10_000.0
    assert math.isclose(row["distance_bp_a"], expected_bp)


def test_candidate_bands_method_c_places_long_and_short_bands():
    empty_vol = volume_at_price([], t_ms=0, lookback_ms=1000, bin_size=50.0)
    empty_oi = open_interest_bands(PriceSeries(), PriceSeries(), t_ms=0, lookback_ms=1000, bin_size=50.0)
    cand = candidate_bands(empty_vol, empty_oi, current_price=30000.0, t_ms=0,
                            leverage_multiples=(10.0,), naive_band_half_width_bp=0.0)
    c_bands = cand.by_method["c"]
    assert len(c_bands) == 2
    long_band = next(b for b in c_bands if b.label == "long_10.0x")
    short_band = next(b for b in c_bands if b.label == "short_10.0x")
    assert math.isclose(long_band.low, 27000.0)  # 30000*(1-1/10)
    assert math.isclose(short_band.low, 33000.0)  # 30000*(1+1/10)

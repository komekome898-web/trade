from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "phase2"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import p2_03_iter2 as iter2  # noqa: E402
from bot.research.sealed import SealedDataError  # noqa: E402


# ===========================================================================
# 封印ユニットの取り違え防止: 1348.T/1305.T は P2-03b の封印ファイルであり、
# P2-03(反復0/1の主系列)の封印記録には登録されていない。
# ===========================================================================

def test_alt_symbols_refused_under_p2_03():
    """1348.T/1305.T を unit="P2-03" で読もうとすると、P2-03 の SEALED.json に
    そのパスが登録されていないため SealedDataError になる(封印ユニットの
    取り違えを構造的に防ぐ)。"""
    bands = _dummy_bands()
    for sym in iter2.ALT_SYMBOLS:
        path, _unit, apply_correction = iter2.SYMBOL_SOURCES[sym]
        wrong_map = {sym: (path, "P2-03", apply_correction)}
        with pytest.raises(SealedDataError):
            iter2.load_and_build(sym, bands, unit_map=wrong_map)


def test_alt_symbols_load_under_p2_03b():
    """本番設定どおり unit="P2-03b" では正常に読める。"""
    bands = _dummy_bands()
    for sym in iter2.ALT_SYMBOLS:
        path, unit, _apply_correction = iter2.SYMBOL_SOURCES[sym]
        assert unit == "P2-03b"
        res = iter2.load_and_build(sym, bands)
        assert res["sym"] == sym
        assert res["n_rows"] > 0
        # 開発セットのみ(封印境界2022-03-05より前)であることの簡易確認。
        assert res["df"]["date"].astype(str).max() < "2022-03-05"


def test_reference_and_comparison_symbols_use_p2_03():
    path_1321, unit_1321, _ = iter2.SYMBOL_SOURCES["1321.T"]
    path_1306, unit_1306, _ = iter2.SYMBOL_SOURCES["1306.T"]
    assert unit_1321 == "P2-03"
    assert unit_1306 == "P2-03"


def test_mde_formula_matches_prereg_table():
    """PREREG.md 表(監査3回目実測)の MDE を σ・n から再現できることの検算
    (1306=5.10 / 1591=5.64 / 2516=12.82 / 1321=5.26bps)。"""
    assert iter2.mde_bps(91.8, 2543) == pytest.approx(5.10, abs=0.01)
    assert iter2.mde_bps(89.2, 1962) == pytest.approx(5.64, abs=0.01)
    assert iter2.mde_bps(143.7, 985) == pytest.approx(12.82, abs=0.01)
    assert iter2.mde_bps(94.8, 2546) == pytest.approx(5.26, abs=0.01)


def test_price_level_corrections_only_touch_1306():
    """1348.T/1305.T は反復1の1306.T価格水準補正テーブルに存在しない銘柄なので、
    apply_price_correction の値に関わらず結果が変わらない(副作用なしの確認)。"""
    bands = _dummy_bands()
    for sym in iter2.ALT_SYMBOLS:
        path, unit, _ = iter2.SYMBOL_SOURCES[sym]
        res_false = iter2.load_and_build(sym, bands, unit_map={sym: (path, unit, False)})
        res_true = iter2.load_and_build(sym, bands, unit_map={sym: (path, unit, True)})
        pd_true = res_true["pairs"]["band_price_t"]
        pd_false = res_false["pairs"]["band_price_t"]
        assert pd_true.equals(pd_false)


def _dummy_bands():
    value = {
        "up_to_1000_yen": 1, "up_to_3000_yen": 1, "up_to_5000_yen": 1, "up_to_10000_yen": 1,
        "up_to_30000_yen": 5, "up_to_50000_yen": 10, "up_to_100000_yen": 10, "up_to_300000_yen": 50,
        "up_to_500000_yen": 100, "up_to_1000000_yen": 100, "up_to_3000000_yen": 500,
        "up_to_5000000_yen": 1000, "up_to_10000000_yen": 1000, "up_to_30000000_yen": 5000,
        "up_to_50000000_yen": 10000, "over_50000000_yen": 10000,
    }
    return iter2.base.parse_tick_bands(value)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

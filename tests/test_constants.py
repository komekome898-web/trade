"""Constants registry with provenance (QA_PLAN_2026-09.md §1-2 item 4)."""
from __future__ import annotations

import pytest

from bot.constants import (
    AssumedConstantError, Constant, ConstantsError, load_constants, require_source,
)


@pytest.fixture(scope="module")
def constants():
    return load_constants(".")


def test_loads_nonempty(constants):
    assert len(constants) > 10


def test_schema_completeness(constants):
    """Every entry has value/unit/source_type, and source_type is valid."""
    for path, c in constants.items():
        assert isinstance(c, Constant)
        assert c.value is not None or path.endswith("etf_spread_bps"), path
        assert c.unit, f"{path}: missing unit"
        assert c.source_type in ("primary_document", "measured", "assumed"), path


def test_primary_documents_have_url_and_verified(constants):
    for path, c in constants.items():
        if c.source_type == "primary_document":
            assert c.source_url is not None, f"{path}: primary_document needs source_url"
            assert c.verified_on, f"{path}: primary_document needs verified_on"


def test_measured_have_measured_by(constants):
    for path, c in constants.items():
        if c.source_type == "measured":
            assert c.measured_by, f"{path}: measured needs measured_by"


def test_deprecated_entries_flagged(constants):
    old = constants["bitflyer_fx_btc_jpy.taker_round_trip_floor_bps_OLD"]
    assert old.deprecated is True
    assert old.source_type == "assumed"
    assert "2bps" in (old.reason or "") or "slippage" in (old.reason or "")


def test_deprecated_or_assumed_reject_via_require_source(constants):
    with pytest.raises(AssumedConstantError):
        require_source("bitflyer_fx_btc_jpy.taker_round_trip_floor_bps_OLD", constants)
    with pytest.raises(AssumedConstantError):
        require_source("gmo_fx_usdjpy.spread_sen", constants)


def test_require_source_returns_sourced_constant(constants):
    c = require_source("bitflyer_fx_btc_jpy.taker_fee_pct", constants)
    assert c.value == 0.0
    c2 = require_source("data_retention.bitflyer_executions_days", constants)
    assert c2.value == 31


def test_require_source_unknown_name_raises(constants):
    with pytest.raises(ConstantsError):
        require_source("nope.does_not_exist", constants)


def test_require_source_loads_lazily_without_table():
    # No pre-loaded table passed — should load config/constants.yaml itself.
    c = require_source("bitflyer_fx_btc_jpy.quoted_spread_median_bps", root=".")
    assert c.unit == "bps"


def test_key_values_match_config_products_yaml(constants):
    """The registry must agree with config/products.yaml, not fork it."""
    fee = constants["bitflyer_fx_btc_jpy.taker_fee_pct"]
    swap = constants["bitflyer_fx_btc_jpy.funding_swap_daily_pct"]
    assert fee.value == 0.0
    assert swap.value == 0.06


def test_equity_tick_size_topix100_band_boundaries(constants):
    """P2-07: TOPIX500構成銘柄(TOPIX100及びTOPIX Mid400構成銘柄) column,
    mirroring the etf_tick_size_yen_by_price_band boundary checks."""
    table = constants["jpx_cash_equity.equity_tick_size_yen_by_price_band_topix500"].value
    assert table["up_to_1000_yen"] == 0.1
    assert table["up_to_3000_yen"] == 0.5
    assert table["up_to_5000_yen"] == 1
    assert table["up_to_10000_yen"] == 1
    assert table["up_to_30000_yen"] == 5
    assert table["up_to_50000_yen"] == 10
    assert table["up_to_100000_yen"] == 10
    assert table["up_to_300000_yen"] == 50
    assert table["up_to_500000_yen"] == 100
    assert table["up_to_1000000_yen"] == 100
    assert table["up_to_3000000_yen"] == 500
    assert table["up_to_5000000_yen"] == 1000
    assert table["up_to_10000000_yen"] == 1000
    assert table["up_to_30000000_yen"] == 5000
    assert table["up_to_50000000_yen"] == 10000
    assert table["over_50000000_yen"] == 10000
    # Boundary must be strictly below the ETF/leveraged-product column at
    # the low end (0.1/0.5 vs 1/1) and never above the "other" column.
    etf = constants["jpx_cash_equity.etf_tick_size_yen_by_price_band"].value
    other = constants["jpx_cash_equity.equity_tick_size_yen_by_price_band_other"].value
    assert table["up_to_1000_yen"] < etf["up_to_1000_yen"]
    for key in table:
        assert table[key] <= other[key]


def test_equity_tick_size_other_band_boundaries(constants):
    """P2-07: その他の銘柄 column (all domestic stocks outside TOPIX500)."""
    table = constants["jpx_cash_equity.equity_tick_size_yen_by_price_band_other"].value
    assert table["up_to_1000_yen"] == 1
    assert table["up_to_3000_yen"] == 1
    assert table["up_to_5000_yen"] == 5
    assert table["up_to_10000_yen"] == 10
    assert table["up_to_30000_yen"] == 10
    assert table["up_to_50000_yen"] == 50
    assert table["up_to_100000_yen"] == 100
    assert table["up_to_300000_yen"] == 100
    assert table["up_to_500000_yen"] == 500
    assert table["up_to_1000000_yen"] == 1000
    assert table["up_to_3000000_yen"] == 1000
    assert table["up_to_5000000_yen"] == 5000
    assert table["up_to_10000000_yen"] == 10000
    assert table["up_to_30000000_yen"] == 10000
    assert table["up_to_50000000_yen"] == 50000
    assert table["over_50000000_yen"] == 100000
    # "other" widens (or matches) the tick vs. TOPIX500/ETF at every band —
    # it is never the finest-grained column.
    topix100 = constants["jpx_cash_equity.equity_tick_size_yen_by_price_band_topix500"].value
    for key in table:
        assert table[key] >= topix100[key]


def test_topix500_membership_note_present_and_not_a_membership_list(constants):
    """The membership caveat must exist and must not silently carry a
    per-date TOPIX100 constituent list (CLAUDE.md §5 discipline: no
    unregistered/undocumented assumptions feeding a judgment)."""
    note = constants["jpx_cash_equity.topix500_membership_note"]
    assert note.value
    assert not isinstance(note.value, (list, dict))
    assert "TOPIX100" in note.notes
    assert "membership" in note.notes.lower() or "構成" in note.notes


def test_malformed_file_raises(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "constants.yaml").write_text(
        "group:\n  bad_entry:\n    value: 1\n    unit: bps\n", encoding="utf-8"
    )
    with pytest.raises(ConstantsError):
        load_constants(tmp_path)


def test_invalid_source_type_raises(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "constants.yaml").write_text(
        "group:\n  bad_entry:\n    value: 1\n    unit: bps\n    source_type: guessed\n",
        encoding="utf-8",
    )
    with pytest.raises(ConstantsError):
        load_constants(tmp_path)

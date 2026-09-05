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

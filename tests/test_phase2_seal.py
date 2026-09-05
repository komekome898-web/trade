"""Tests for docs/PHASE2_SPEC.md §3 (data sealing):
scripts/phase2_seal.py + src/bot/research/sealed.py."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import phase2_seal as ps  # noqa: E402
from bot.research.sealed import (  # noqa: E402
    SealedDataError,
    UNSEAL_TOKEN,
    assert_not_sealed,
    calendar_seal_boundary,
    load_seal_record,
    load_sealed,
    load_unsealed,
    parse_ts,
    seal_dir,
)


def _day(n: int) -> datetime:
    return datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=n)


# ---------------------------------------------------------------------------
# 1. calendar boundary, uneven row density
# ---------------------------------------------------------------------------

def test_calendar_boundary_ignores_row_density():
    # 1000 rows crammed into day 0, then one row per day out to day 10 (11
    # calendar days total, span = 10 days). By ROW COUNT the 70th percentile
    # row would still sit inside day 0's dense cluster; by CALENDAR date it
    # must be day 0 + floor(10 * 0.7) = day 7.
    dense = [_day(0) + timedelta(seconds=s) for s in range(1000)]
    sparse = [_day(n) for n in range(1, 11)]
    boundary = calendar_seal_boundary(dense + sparse)
    assert boundary == datetime(2026, 1, 8, tzinfo=timezone.utc)  # day 0 + 7
    # sanity: this is NOT what a row-count-based 70th percentile would give
    by_row_count = sorted(dense + sparse)[int(len(dense + sparse) * 0.7)]
    assert by_row_count.date() != boundary.date()


def test_calendar_boundary_matches_reversed_uneven_density():
    # Density on the OTHER end must not move the boundary either.
    sparse = [_day(n) for n in range(0, 10)]
    dense = [_day(10) + timedelta(seconds=s) for s in range(1000)]
    boundary = calendar_seal_boundary(sparse + dense)
    assert boundary == datetime(2026, 1, 8, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# fixtures: a synthetic dataset + a sealed unit built from it
# ---------------------------------------------------------------------------

@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "data").mkdir()
    (tmp_path / "backtest_data").mkdir()
    # 30 calendar days, one row/day -> span_days=29, boundary = day0+20 = day20
    lines = ["ts_utc,px\n"]
    for n in range(30):
        lines.append(f"{_day(n).isoformat()},{100 + n}\n")
    (tmp_path / "data" / "prices.csv").write_text("".join(lines))
    return tmp_path


@pytest.fixture
def sealed_unit(root: Path):
    """Seal data/prices.csv for unit 'u1' with forward_start far in the
    future (after all synthetic data), isolating the historical boundary."""
    files = [root / "data" / "prices.csv"]
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)  # well after day 29
    record = ps.build_seal("u1", files, root, now)
    out_dir = seal_dir("u1", root)
    out_dir.mkdir(parents=True)
    (out_dir / "SEALED.json").write_text(json.dumps(record))
    return record


def test_seal_record_boundary(root: Path, sealed_unit: dict):
    entry = sealed_unit["files"][0]
    assert entry["path"] == "data/prices.csv"
    assert entry["time_column"] == "ts_utc"
    assert entry["seal_from_ts"] == _day(20).isoformat()
    assert "md5" in entry and len(entry["md5"]) == 32


# ---------------------------------------------------------------------------
# 2. load_unsealed drops exactly the sealed rows
# ---------------------------------------------------------------------------

def test_load_unsealed_drops_exactly_sealed_rows(root: Path, sealed_unit: dict):
    df = load_unsealed("data/prices.csv", "u1", root=root)
    kept_days = sorted(parse_ts(t).date().day for t in df["ts_utc"])
    # day20's date is Jan 21 (day offset 20 from Jan1) -> kept are day 0..19
    assert kept_days == list(range(1, 21))  # calendar days 1..20 (offsets 0..19)
    assert len(df) == 20


def test_load_unsealed_forward_start_also_truncates(root: Path):
    files = [root / "data" / "prices.csv"]
    now = _day(15)  # forward_start = day 15, earlier than the day-20 historical boundary
    record = ps.build_seal("u2", files, root, now)
    out_dir = seal_dir("u2", root)
    out_dir.mkdir(parents=True)
    (out_dir / "SEALED.json").write_text(json.dumps(record))

    df = load_unsealed("data/prices.csv", "u2", root=root)
    assert len(df) == 15  # days 0..14 only; forward_start (day15) is the binding cutoff


# ---------------------------------------------------------------------------
# 3. load_sealed guard rails + audit log
# ---------------------------------------------------------------------------

def test_load_sealed_refuses_without_env(root: Path, sealed_unit: dict, monkeypatch):
    monkeypatch.delenv("PHASE2_FINAL_EVAL", raising=False)
    with pytest.raises(SealedDataError):
        load_sealed("data/prices.csv", "u1", UNSEAL_TOKEN, root=root)


def test_load_sealed_refuses_without_approval_file(root: Path, sealed_unit: dict, monkeypatch):
    monkeypatch.setenv("PHASE2_FINAL_EVAL", "u1")
    with pytest.raises(SealedDataError):
        load_sealed("data/prices.csv", "u1", UNSEAL_TOKEN, root=root)


def test_load_sealed_refuses_with_wrong_token(root: Path, sealed_unit: dict, monkeypatch):
    monkeypatch.setenv("PHASE2_FINAL_EVAL", "u1")
    (seal_dir("u1", root) / "UNSEAL_APPROVED").write_text("owner ack\n")
    with pytest.raises(SealedDataError):
        load_sealed("data/prices.csv", "u1", "wrong-token", root=root)


def test_load_sealed_succeeds_with_all_three_and_logs(root: Path, sealed_unit: dict, monkeypatch):
    monkeypatch.setenv("PHASE2_FINAL_EVAL", "u1")
    (seal_dir("u1", root) / "UNSEAL_APPROVED").write_text("owner ack\n")

    df = load_sealed("data/prices.csv", "u1", UNSEAL_TOKEN, root=root)
    kept_days = sorted(parse_ts(t).date().day for t in df["ts_utc"])
    assert kept_days == list(range(21, 31))  # days 20..29 (offsets), the sealed tail
    assert len(df) == 10

    log_path = seal_dir("u1", root) / "UNSEAL_LOG.jsonl"
    assert log_path.is_file()
    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["unit"] == "u1"
    assert rec["path"] == "data/prices.csv"
    assert rec["rows_returned"] == 10

    # a second approved call appends, does not overwrite
    load_sealed("data/prices.csv", "u1", UNSEAL_TOKEN, root=root)
    assert len(log_path.read_text().strip().splitlines()) == 2


# ---------------------------------------------------------------------------
# 4. assert_not_sealed
# ---------------------------------------------------------------------------

def test_assert_not_sealed_raises_on_sealed_row(root: Path, sealed_unit: dict):
    import pandas as pd
    df_bad = pd.DataFrame({"ts_utc": [_day(25).isoformat()]})
    with pytest.raises(SealedDataError):
        assert_not_sealed(df_bad, "u1", root=root)


def test_assert_not_sealed_passes_on_dev_rows(root: Path, sealed_unit: dict):
    import pandas as pd
    df_ok = pd.DataFrame({"ts_utc": [_day(5).isoformat(), _day(10).isoformat()]})
    assert_not_sealed(df_ok, "u1", root=root)  # must not raise


# ---------------------------------------------------------------------------
# gates.shared_or_local phase-2 warning wire-up
# ---------------------------------------------------------------------------

def test_shared_or_local_warns_on_sealed_file(root: Path, sealed_unit: dict, monkeypatch):
    from bot.monitoring.gates import shared_or_local

    monkeypatch.setenv("PHASE2_UNIT", "u1")
    with pytest.warns(UserWarning, match="SEALED"):
        p = shared_or_local(root, "data/prices.csv")
    assert p == root / "data" / "prices.csv"


def test_shared_or_local_silent_without_phase2_unit(root: Path, sealed_unit: dict, monkeypatch):
    from bot.monitoring.gates import shared_or_local

    monkeypatch.delenv("PHASE2_UNIT", raising=False)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        p = shared_or_local(root, "data/prices.csv")  # must not warn/raise
    assert p == root / "data" / "prices.csv"

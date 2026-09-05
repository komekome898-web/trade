"""Tests for scripts/retention_snapshot.py -- automatic pre-expiry snapshots
of retention-limited sources (docs/QA_PLAN_2026-09.md item 5)."""
from __future__ import annotations

import gzip
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import retention_snapshot as rs  # noqa: E402

CONSTANTS_YAML = """
data_retention:
  bitflyer_executions_days:
    value: 31
    unit: days
    source_type: measured
    measured_by: test
    verified_on: "2026-09-05"
  okx_open_interest_1h_days:
    value: 30
    unit: days
    source_type: measured
    measured_by: test
    verified_on: "2026-09-05"
  okx_open_interest_5m_days:
    value: [2, 3]
    unit: days
    source_type: measured
    measured_by: test
    verified_on: "2026-09-05"
  okx_long_short_ratio_days:
    value: [60, 90]
    unit: days
    source_type: measured
    measured_by: test
    verified_on: "2026-09-05"
"""


def _write_csv_gz(path: Path, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt") as f:
        f.write("ts,px\n")
        for r in rows:
            f.write(r + "\n")


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "constants.yaml").write_text(CONSTANTS_YAML)

    (tmp_path / "data" / "tape").mkdir(parents=True)
    _write_csv_gz(tmp_path / "data" / "tape" / "executions_20260820.csv.gz",
                  ["2026-08-20T00:00:00Z,100", "2026-08-20T00:01:00Z,101"])
    (tmp_path / "data" / "candles_FX_BTC_JPY.csv").write_text(
        "ts,open,close\n2026-08-20T00:00:00Z,100,101\n"
    )

    (tmp_path / "data" / "okx_btc_oi_1h.csv").write_text(
        "ts,oi,volume\n2026-08-20T00:00:00Z,1000,5\n2026-08-21T00:00:00Z,1010,6\n"
    )
    (tmp_path / "data" / "okx_btc_oi_5m.csv").write_text(
        "ts,oi,volume\n2026-08-20T00:00:00Z,1000,5\n"
    )
    (tmp_path / "data" / "okx_btc_lsratio_1h.csv").write_text(
        "ts,ratio\n2026-08-20T00:00:00Z,1.1\n"
    )

    (tmp_path / "paper_logs").mkdir()
    (tmp_path / "paper_logs" / "oi_snapshots.csv").write_text(
        "ts_utc,okx_usdt_oi\n2026-08-20T00:00:00+00:00,3000000\n"
    )
    (tmp_path / "paper_logs" / "venues").mkdir()
    _write_csv_gz(tmp_path / "paper_logs" / "venues" / "quotes_20260820.csv.gz",
                  ["2026-08-20T00:00:00Z,100"])

    (tmp_path / "backtest_data").mkdir()
    return tmp_path


def test_scan_creates_snapshot_on_first_run(tree: Path):
    now = datetime(2026, 9, 5, tzinfo=timezone.utc)
    results = rs.run(tree, now=now)
    by_source = {r["source"]: r for r in results}

    assert by_source["bitflyer_executions"]["action"] == "created"
    dest = tree / "backtest_data" / "auto_bitflyer_executions_20260905"
    assert dest.is_dir()
    assert (dest / "executions_20260820.csv.gz").is_file()
    assert (dest / "candles_FX_BTC_JPY.csv").is_file()
    assert (dest / "MD5SUMS").is_file()

    manifest = json.loads((dest / "manifest.json").read_text())
    assert manifest["source"] == "bitflyer_executions"
    assert manifest["window"]["retention_days"] == 31
    assert manifest["window"]["interval_days"] == 15
    assert manifest["rows"] == 3  # 2 execution rows + 1 candle row, both have a "ts" column
    assert manifest["first_ts"] is not None and manifest["last_ts"] is not None

    for name in ("okx_open_interest_1h", "okx_open_interest_5m",
                 "okx_long_short_ratio", "oi_snapshots", "venues"):
        assert by_source[name]["action"] == "created", name


def test_second_run_same_day_skips_and_never_overwrites(tree: Path):
    now = datetime(2026, 9, 5, tzinfo=timezone.utc)
    rs.run(tree, now=now)
    dest = tree / "backtest_data" / "auto_bitflyer_executions_20260905"
    manifest_before = (dest / "manifest.json").read_text()

    results2 = rs.run(tree, now=now)
    by_source = {r["source"]: r for r in results2}
    assert by_source["bitflyer_executions"]["action"] == "skip"
    assert (dest / "manifest.json").read_text() == manifest_before  # untouched


def test_skips_until_half_interval_elapsed_then_creates(tree: Path):
    now0 = datetime(2026, 9, 5, tzinfo=timezone.utc)
    rs.run(tree, now=now0)

    # 10 days later: still under the 15-day bitflyer interval -> skip
    now1 = now0 + timedelta(days=10)
    results1 = rs.run(tree, now=now1)
    bf1 = {r["source"]: r for r in results1}["bitflyer_executions"]
    assert bf1["action"] == "skip"
    assert not (tree / "backtest_data" / "auto_bitflyer_executions_20260915").exists()

    # 16 days later: past the 15-day interval -> a new snapshot is created
    now2 = now0 + timedelta(days=16)
    results2 = rs.run(tree, now=now2)
    bf2 = {r["source"]: r for r in results2}["bitflyer_executions"]
    assert bf2["action"] == "created"
    # the original snapshot from day 0 must still exist, untouched
    assert (tree / "backtest_data" / "auto_bitflyer_executions_20260905").is_dir()


def test_missing_source_files_skip_without_crashing(tmp_path: Path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "constants.yaml").write_text(CONSTANTS_YAML)
    (tmp_path / "backtest_data").mkdir()
    results = rs.run(tmp_path, now=datetime(2026, 9, 5, tzinfo=timezone.utc))
    assert all(r["action"] == "skip" for r in results)
    assert all(r["reason"] == "no source files present" for r in results)


def test_never_touches_original_files(tree: Path):
    src = tree / "data" / "okx_btc_oi_1h.csv"
    before = src.read_bytes()
    before_mtime = src.stat().st_mtime
    rs.run(tree, now=datetime(2026, 9, 5, tzinfo=timezone.utc))
    assert src.read_bytes() == before
    assert src.stat().st_mtime == before_mtime


def test_cadence_validation_rejects_stale_interval(tree: Path):
    # okx_open_interest_1h configured at 14d must satisfy 14 <= 30/2=15.
    # Corrupt the constant to a value that breaks that inequality.
    bad_yaml = CONSTANTS_YAML.replace(
        "okx_open_interest_1h_days:\n    value: 30",
        "okx_open_interest_1h_days:\n    value: 20",
    )
    (tree / "config" / "constants.yaml").write_text(bad_yaml)
    with pytest.raises(rs.RetentionCadenceError):
        rs.run(tree, now=datetime(2026, 9, 5, tzinfo=timezone.utc))


def test_venues_prefers_shared_paper_logs_copy_by_basename(tree: Path):
    # Same basename in both data/venues and paper_logs/venues -> the
    # paper_logs (shared) one must be the one actually snapshotted.
    (tree / "data" / "venues").mkdir()
    _write_csv_gz(tree / "data" / "venues" / "quotes_20260820.csv.gz", ["LOCAL,1"])
    now = datetime(2026, 9, 5, tzinfo=timezone.utc)
    rs.run(tree, now=now)
    dest = tree / "backtest_data" / "auto_venues_20260905" / "quotes_20260820.csv.gz"
    with gzip.open(dest, "rt") as f:
        content = f.read()
    assert "LOCAL" not in content

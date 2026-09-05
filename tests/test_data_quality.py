"""Tests for scripts/data_quality.py — read-only checks over the ledger."""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import data_quality as dq  # noqa: E402
import intake_ledger as il  # noqa: E402


def _write_schema(root: Path, name: str, payload: dict) -> None:
    (root / "schema").mkdir(exist_ok=True)
    (root / "schema" / f"{name}.json").write_text(json.dumps(payload))


def _ledger(root: Path) -> dict:
    return il.run(
        root,
        full=False,
        ledger_path=root / "data" / "INTAKE.jsonl",
        latest_path=root / "data" / "INTAKE_latest.json",
    )


# ---- crossed book / gaps / extreme return -------------------------------


def test_crossed_book_gap_and_extreme_return(tmp_path: Path):
    (tmp_path / "data").mkdir()
    rows = [
        "ts,mid,spread_bps",
        "2026-01-01T00:00:00Z,100.0,1.0",
        "2026-01-01T00:00:05Z,100.0,-1.0",   # crossed (<=0)
        "2026-01-01T00:00:10Z,100.0,60.0",   # crossed (>50)
        "2026-01-01T00:00:15Z,100.0,1.0",
        "2026-01-01T00:05:15Z,100.0,1.0",    # big gap vs 5s median
        "2026-01-01T00:05:20Z,80.0,1.0",     # -20% single-step return on mid
    ]
    (tmp_path / "data" / "board_round_series_5s.csv").write_text("\n".join(rows) + "\n")
    _write_schema(tmp_path, "board_round_series_5s", {
        "dataset": "board_round_series_5s",
        "path_glob": ["data/board_round_series_5s.csv"],
        "columns": {"ts": {}, "mid": {}, "spread_bps": {}},
    })

    _ledger(tmp_path)
    report = dq.run(tmp_path)
    checks = report["datasets"]["board_round_series_5s"]["checks"]

    assert checks["crossed_book"]["count"] == 2
    assert checks["gaps"]["count"] == 1
    assert checks["extreme_return"]["count"] == 1
    assert "missing_columns" not in checks


# ---- maintenance window flat bars ---------------------------------------


def test_maintenance_window_flat_bar_flagged(tmp_path: Path):
    (tmp_path / "data").mkdir()
    rows = [
        "ts,open,high,low,close,volume",
        "2026-01-01T19:00:00+00:00,100,100,100,100,0",   # in window, flat -> flagged
        "2026-01-01T19:09:00+00:00,101,101,101,101,5",   # in window, flat -> flagged
        "2026-01-01T20:00:00+00:00,102,105,101,103,10",  # outside window, not flat
    ]
    (tmp_path / "data" / "candles_FX_BTC_JPY.csv").write_text("\n".join(rows) + "\n")
    _write_schema(tmp_path, "candles_fx_btc_jpy", {
        "dataset": "candles_fx_btc_jpy",
        "path_glob": ["data/candles_FX_BTC_JPY.csv"],
        "columns": {"ts": {}, "open": {}, "high": {}, "low": {}, "close": {}, "volume": {}},
    })

    _ledger(tmp_path)
    report = dq.run(tmp_path)
    checks = report["datasets"]["candles_fx_btc_jpy"]["checks"]

    assert checks["maintenance_window"]["count"] == 2
    assert checks["zero_volume"]["count"] == 1


# ---- duplicate keys / non-monotonic --------------------------------------


def test_duplicate_and_non_monotonic(tmp_path: Path):
    (tmp_path / "data").mkdir()
    rows = [
        "ts,price",
        "2026-01-01T00:00:00Z,1",
        "2026-01-01T00:00:00Z,1",  # duplicate ts
        "2026-01-01T00:00:05Z,1",
        "2026-01-01T00:00:02Z,1",  # goes backwards -> non-monotonic
    ]
    (tmp_path / "data" / "ticks.csv").write_text("\n".join(rows) + "\n")
    _write_schema(tmp_path, "ticks", {
        "dataset": "ticks",
        "path_glob": ["data/ticks.csv"],
        "columns": {"ts": {}, "price": {}},
    })

    _ledger(tmp_path)
    report = dq.run(tmp_path)
    checks = report["datasets"]["ticks"]["checks"]

    assert checks["duplicate_keys"]["count"] == 1
    assert checks["non_monotonic"]["count"] == 1


# ---- count is not capped by MAX_EXAMPLES ---------------------------------


def test_extreme_return_count_not_capped_by_examples(tmp_path: Path):
    (tmp_path / "data").mkdir()
    rows = ["ts,mid"]
    price = 100.0
    for t in range(12):
        rows.append(f"2026-01-01T00:{t:02d}:00Z,{price}")
        price = price * 0.5  # -50% each step -> 11 extreme-return transitions across 12 rows
    rel = "data/extremes.csv"
    (tmp_path / rel).write_text("\n".join(rows) + "\n")

    result = dq.scan_file(tmp_path, rel, schema=None)

    assert result["extreme_return"]["count"] == 11
    assert len(result["extreme_return"]["examples"]) == dq.MAX_EXAMPLES == 5


# ---- split_candidate -------------------------------------------------------


def _daily_rows(closes: list[float], start="2026-01-01") -> list[str]:
    from datetime import datetime, timedelta

    d0 = datetime.strptime(start, "%Y-%m-%d")
    rows = ["date,open,high,low,close,volume"]
    for i, c in enumerate(closes):
        d = (d0 + timedelta(days=i)).strftime("%Y-%m-%d")
        rows.append(f"{d},{c},{c},{c},{c},100")
    return rows


def test_persistent_split_flagged_as_split_candidate_not_bad_print(tmp_path: Path):
    (tmp_path / "data").mkdir()
    # 10:1 split at index 5, level persists afterwards
    closes = [1000, 1005, 995, 1010, 1000, 100, 102, 98, 101, 99]
    rows = _daily_rows(closes)
    (tmp_path / "data" / "daily_split.csv").write_text("\n".join(rows) + "\n")
    _write_schema(tmp_path, "daily_split", {
        "dataset": "daily_split",
        "path_glob": ["data/daily_split.csv"],
        "columns": {"date": {}, "open": {}, "high": {}, "low": {}, "close": {}, "volume": {}},
    })

    _ledger(tmp_path)
    report = dq.run(tmp_path)
    checks = report["datasets"]["daily_split"]["checks"]

    assert checks["split_candidate"]["count"] == 1
    flagged_row = checks["split_candidate"]["examples"][0]["examples"][0]["row"]
    # extreme_return still fires on the same transition (>10% move) ...
    extreme_rows = [ex["row"] for ex in checks["extreme_return"]["examples"][0]["examples"]]
    assert flagged_row in extreme_rows
    # ... but unlike a bad print, there is exactly one extreme transition
    # (the split itself), not a drop immediately followed by a revert.
    assert checks["extreme_return"]["count"] == 1


def test_one_day_bad_print_is_extreme_return_only(tmp_path: Path):
    (tmp_path / "data").mkdir()
    # one-day 1/100 bad print then reverts -- a round trip, not a split
    closes = [1000, 1005, 995, 10, 1000, 1002, 998]
    rows = _daily_rows(closes)
    (tmp_path / "data" / "daily_badprint.csv").write_text("\n".join(rows) + "\n")
    _write_schema(tmp_path, "daily_badprint", {
        "dataset": "daily_badprint",
        "path_glob": ["data/daily_badprint.csv"],
        "columns": {"date": {}, "open": {}, "high": {}, "low": {}, "close": {}, "volume": {}},
    })

    _ledger(tmp_path)
    report = dq.run(tmp_path)
    checks = report["datasets"]["daily_badprint"]["checks"]

    assert "split_candidate" not in checks
    assert checks["extreme_return"]["count"] == 2  # drop, then revert


# ---- missing columns vs schema -------------------------------------------


def test_missing_columns_vs_schema(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "thing.csv").write_text("ts,a,mystery\n2026-01-01T00:00:00Z,1,2\n")
    _write_schema(tmp_path, "thing", {
        "dataset": "thing",
        "path_glob": ["data/thing.csv"],
        "columns": {"ts": {}, "a": {}, "b": {}},  # b documented but absent; mystery undocumented
    })

    _ledger(tmp_path)
    report = dq.run(tmp_path)
    checks = report["datasets"]["thing"]["checks"]

    mc = checks["missing_columns"]["examples"][0]["examples"][0]
    assert "mystery" in mc["undocumented_in_schema"]
    assert "b" in mc["declared_but_absent"]


# ---- gz support, unmatched files, no-op on clean data --------------------


def test_gz_file_is_checked_and_unmatched_files_listed(tmp_path: Path):
    (tmp_path / "data").mkdir()
    text = "ts,a\n2026-01-01T00:00:00Z,1\n2026-01-01T00:00:00Z,1\n"
    with gzip.open(tmp_path / "data" / "dup.csv.gz", "wt") as f:
        f.write(text)
    # a file with no matching schema at all
    (tmp_path / "data" / "orphan.csv").write_text("ts,a\n2026-01-01T00:00:00Z,1\n")
    _write_schema(tmp_path, "dup", {
        "dataset": "dup_dataset",
        "path_glob": ["data/dup.csv.gz"],
        "columns": {"ts": {}, "a": {}},
    })

    _ledger(tmp_path)
    report = dq.run(tmp_path)

    assert report["datasets"]["dup_dataset"]["checks"]["duplicate_keys"]["count"] == 1
    assert "data/orphan.csv" in report["unmatched_files"]


def test_clean_file_flags_nothing(tmp_path: Path):
    (tmp_path / "data").mkdir()
    rows = ["ts,open,high,low,close,volume"]
    for i in range(10):
        rows.append(f"2026-01-01T00:{i:02d}:00Z,{100+i},{100+i},{100+i},{100+i},1")
    (tmp_path / "data" / "clean.csv").write_text("\n".join(rows) + "\n")
    _write_schema(tmp_path, "clean", {
        "dataset": "clean",
        "path_glob": ["data/clean.csv"],
        "columns": {"ts": {}, "open": {}, "high": {}, "low": {}, "close": {}, "volume": {}},
    })

    _ledger(tmp_path)
    report = dq.run(tmp_path)
    d = report["datasets"]["clean"]
    assert d["files_checked"] == 1
    assert d["files_flagged"] == 0
    assert d["checks"] == {}


# ---- never modifies data --------------------------------------------------


def test_never_writes_inside_scanned_data_files(tmp_path: Path):
    (tmp_path / "data").mkdir()
    p = tmp_path / "data" / "immutable.csv"
    p.write_text("ts,a\n2026-01-01T00:00:00Z,1\n")
    before = p.read_bytes()
    before_mtime = p.stat().st_mtime

    _write_schema(tmp_path, "immutable", {
        "dataset": "immutable",
        "path_glob": ["data/immutable.csv"],
        "columns": {"ts": {}, "a": {}},
    })
    _ledger(tmp_path)
    dq.run(tmp_path)

    assert p.read_bytes() == before
    assert p.stat().st_mtime == before_mtime


# ---- CLI -------------------------------------------------------------


def test_main_cli_writes_quality_json(tmp_path: Path, monkeypatch, capsys):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "x.csv").write_text("ts,a\n2026-01-01T00:00:00Z,1\n")
    _ledger(tmp_path)

    monkeypatch.setattr(sys, "argv", ["data_quality.py", "--root", str(tmp_path), "--summary"])
    rc = dq.main()
    assert rc == 0
    out = capsys.readouterr().out
    assert "data_quality:" in out
    assert (tmp_path / "data" / "QUALITY.json").exists()
    report = json.loads((tmp_path / "data" / "QUALITY.json").read_text())
    assert "generated_at" in report

"""Tests for scripts/verify_snapshots.py (DATA_QA_CHECKLIST item 5)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import verify_snapshots as vs  # noqa: E402
import intake_ledger as il  # noqa: E402


def _write(path: Path, content: str = "hello") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    bt = tmp_path / "backtest_data"

    # unit A: has MD5SUMS, all match
    _write(bt / "unit_ok" / "a.csv", "a-content")
    _write(bt / "unit_ok" / "b.csv", "b-content")
    a_md5 = il.md5_of(bt / "unit_ok" / "a.csv")
    b_md5 = il.md5_of(bt / "unit_ok" / "b.csv")
    _write(bt / "unit_ok" / "MD5SUMS", f"{a_md5}  a.csv\n{b_md5}  b.csv\n")

    # unit B: has MD5SUMS, one file mismatches, one is missing, one is extra
    _write(bt / "unit_bad" / "x.csv", "x-content")
    _write(bt / "unit_bad" / "extra.csv", "extra-content")
    wrong_md5 = "0" * 32
    missing_md5 = "1" * 32
    _write(bt / "unit_bad" / "MD5SUMS",
           f"{wrong_md5}  x.csv\n{missing_md5}  gone.csv\n")

    # unit C: no MD5SUMS at all -> should be newly sealed
    _write(bt / "unit_new" / "raw" / "n.csv", "n-content")

    # top-level loose file, no MD5SUMS at backtest_data root
    _write(bt / "loose.csv", "loose-content")

    return tmp_path


def test_verified_unit_matches(tree: Path):
    report = vs.run(tree, write_seal=True)
    units = {u["unit"]: u for u in report["units"]}
    ok = units["unit_ok"]
    assert ok["status"] == "verified"
    assert ok["matched"] == 2
    assert ok["mismatches"] == []
    assert ok["missing"] == []


def test_mismatch_and_missing_detected(tree: Path):
    report = vs.run(tree, write_seal=True)
    units = {u["unit"]: u for u in report["units"]}
    bad = units["unit_bad"]
    assert bad["status"] == "mismatch"
    assert len(bad["mismatches"]) == 1
    assert bad["mismatches"][0]["file"] == "x.csv"
    assert bad["missing"] == ["gone.csv"]
    assert bad["extra"] == ["extra.csv"]
    assert report["ok"] is False


def test_newly_sealed_creates_md5sums_and_never_touches_data(tree: Path):
    target = tree / "backtest_data" / "unit_new" / "raw" / "n.csv"
    before = target.read_bytes()
    before_mtime = target.stat().st_mtime

    report = vs.run(tree, write_seal=True)
    units = {u["unit"]: u for u in report["units"]}
    sealed = units["unit_new"]
    assert sealed["status"] == "newly_sealed"

    md5sums = tree / "backtest_data" / "unit_new" / "MD5SUMS"
    assert md5sums.exists()
    text = md5sums.read_text()
    assert "raw/n.csv" in text

    # data file itself untouched
    assert target.read_bytes() == before
    assert target.stat().st_mtime == before_mtime


def test_top_level_loose_files_sealed_as_a_unit(tree: Path):
    report = vs.run(tree, write_seal=True)
    units = {u["unit"]: u for u in report["units"]}
    top = units["backtest_data (top-level files)"]
    assert top["status"] == "newly_sealed"
    assert (tree / "backtest_data" / "MD5SUMS").exists()
    assert "loose.csv" in (tree / "backtest_data" / "MD5SUMS").read_text()


def test_no_write_dry_run_does_not_create_files(tree: Path):
    report = vs.run(tree, write_seal=False)
    units = {u["unit"]: u for u in report["units"]}
    assert units["unit_new"]["status"] == "unsealed_dry_run"
    assert not (tree / "backtest_data" / "unit_new" / "MD5SUMS").exists()


def test_rerun_after_sealing_is_now_verified(tree: Path):
    vs.run(tree, write_seal=True)
    report2 = vs.run(tree, write_seal=True)
    units = {u["unit"]: u for u in report2["units"]}
    assert units["unit_new"]["status"] == "verified"
    assert units["unit_new"]["mismatches"] == []
    assert units["unit_new"]["missing"] == []


def test_ledger_cross_check(tree: Path):
    # intake ledger claims a different md5 for unit_ok/a.csv than what's on disk
    a_path = tree / "backtest_data" / "unit_ok" / "a.csv"
    real_md5 = il.md5_of(a_path)
    ledger = {
        "backtest_data/unit_ok/a.csv": {"md5": "f" * 32},
        "backtest_data/unit_ok/b.csv": {"md5": il.md5_of(tree / "backtest_data" / "unit_ok" / "b.csv")},
    }
    (tree / "data").mkdir(parents=True, exist_ok=True)
    (tree / "data" / "INTAKE_latest.json").write_text(json.dumps(ledger))

    report = vs.run(tree, write_seal=True)
    lc = report["ledger_cross_check"]
    assert lc["checked"] == 2
    assert len(lc["mismatches"]) == 1
    assert lc["mismatches"][0]["file"] == "backtest_data/unit_ok/a.csv"
    assert lc["mismatches"][0]["snapshot_md5"] == real_md5
    assert report["ok"] is False


def test_prefers_shared_paper_logs_ledger_when_newer(tree: Path, monkeypatch):
    import time
    local = tree / "data" / "INTAKE_latest.json"
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(json.dumps({"backtest_data/unit_ok/a.csv": {"md5": "a" * 32}}))

    time.sleep(0.02)
    shared_dir = tree / "paper_logs"
    shared_dir.mkdir(parents=True, exist_ok=True)
    real_md5 = il.md5_of(tree / "backtest_data" / "unit_ok" / "a.csv")
    (shared_dir / "INTAKE_latest.json").write_text(
        json.dumps({"backtest_data/unit_ok/a.csv": {"md5": real_md5}}))

    report = vs.run(tree, write_seal=True)
    lc = report["ledger_cross_check"]
    assert lc["mismatches"] == []  # shared (newer) copy matches on disk


def test_main_writes_output_and_nonzero_exit_on_mismatch(tree: Path, monkeypatch, capsys):
    # the fixture's unit_bad has an unresolved mismatch -> main() must return 1
    out_path = tree / "out.json"
    monkeypatch.setattr(sys, "argv",
                         ["verify_snapshots.py", "--root", str(tree), "--out", str(out_path)])
    rc = vs.main()
    assert rc == 1
    assert out_path.exists()
    data = json.loads(out_path.read_text())
    assert data["ok"] is False


def test_main_exit_zero_when_clean(tmp_path: Path, monkeypatch):
    bt = tmp_path / "backtest_data"
    _write(bt / "clean" / "c.csv", "clean-content")
    out_path = tmp_path / "out.json"
    monkeypatch.setattr(sys, "argv",
                         ["verify_snapshots.py", "--root", str(tmp_path), "--out", str(out_path)])
    rc = vs.main()
    assert rc == 0
    assert json.loads(out_path.read_text())["ok"] is True

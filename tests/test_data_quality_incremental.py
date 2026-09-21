"""Tests for scripts/data_quality.py's incremental scan (ACTION_LOG 070):
unchanged files are not re-read, changed files are, a truncated gzip does
not abort run(), and a QUALITY.json written before `file_cache` existed is
still accepted."""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import data_quality as dq  # noqa: E402
import intake_ledger as il  # noqa: E402

CLEAN_ROWS = [
    "ts,mid",
    "2026-01-01T00:00:00Z,100.0",
    "2026-01-01T00:00:05Z,100.5",
    "2026-01-01T00:00:10Z,101.0",
]


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


def _setup(root: Path, n: int = 3) -> list[str]:
    """n clean gz files under data/ plus a schema that matches them all."""
    (root / "data").mkdir()
    rels = []
    for i in range(n):
        rel = f"data/series_{i}.csv.gz"
        with gzip.open(root / rel, "wt", encoding="utf-8") as f:
            f.write("\n".join(CLEAN_ROWS) + "\n")
        rels.append(rel)
    _write_schema(root, "series", {
        "dataset": "series",
        "path_glob": ["data/series_*.csv.gz"],
        "columns": {"ts": {}, "mid": {}},
    })
    return rels


def _counting_scan(monkeypatch) -> list[str]:
    """Wrap dq.scan_file so each call records the rel_path it scanned."""
    calls: list[str] = []
    real = dq.scan_file

    def wrapped(root, rel_path, schema):
        calls.append(rel_path)
        return real(root, rel_path, schema)

    monkeypatch.setattr(dq, "scan_file", wrapped)
    return calls


# (a) second run: unchanged files are not scanned again -----------------


def test_second_run_skips_unchanged_files(tmp_path: Path, monkeypatch, capsys):
    rels = _setup(tmp_path, n=3)
    calls = _counting_scan(monkeypatch)

    _ledger(tmp_path)
    report1 = dq.run(tmp_path)
    dq.write_report(tmp_path, report1)
    assert sorted(calls) == sorted(rels)
    assert set(report1["file_cache"]) == set(rels)
    for rel in rels:
        assert report1["file_cache"][rel]["content_key"] == list(il.content_key(_ledger_rec(tmp_path, rel)))

    calls.clear()
    capsys.readouterr()
    (tmp_path / dq.QUALITY_CACHE_REL_PATH).unlink()  # no side file -> falls back to QUALITY.json's file_cache
    _ledger(tmp_path)  # same files -> same content_key
    report2 = dq.run(tmp_path)
    out = capsys.readouterr().out

    assert calls == []
    assert "data_quality: skipped 3 unchanged" in out
    assert report2["datasets"] == report1["datasets"]
    assert report2["file_cache"] == report1["file_cache"]


def _ledger_rec(root: Path, rel: str) -> dict:
    return il.load_latest(root / "data" / "INTAKE_latest.json")[rel]


# (b) a changed file is re-scanned; a file gone from the index leaves the cache


def test_changed_file_is_rescanned_and_removed_file_leaves_cache(tmp_path: Path, monkeypatch, capsys):
    rels = _setup(tmp_path, n=3)
    calls = _counting_scan(monkeypatch)

    _ledger(tmp_path)
    dq.write_report(tmp_path, dq.run(tmp_path))
    calls.clear()

    # change series_1 (content -> md5/bytes change) and delete series_2
    changed = rels[1]
    with gzip.open(tmp_path / changed, "wt", encoding="utf-8") as f:
        f.write("\n".join(CLEAN_ROWS + ["2026-01-01T00:00:15Z,50.0"]) + "\n")  # -50% -> extreme_return
    removed = rels[2]
    (tmp_path / removed).unlink()

    capsys.readouterr()
    _ledger(tmp_path)
    report = dq.run(tmp_path)
    out = capsys.readouterr().out

    assert calls == [changed]
    assert "data_quality: skipped 1 unchanged" in out
    assert f"data_quality: 2/2 {changed} 4 " in out  # i/n path rows seconds
    assert report["datasets"]["series"]["checks"]["extreme_return"]["count"] == 1
    assert set(report["file_cache"]) == {rels[0], changed}
    assert removed not in report["file_cache"]


# (c) a truncated gzip (EOFError) does not abort run() ---------------------


def test_truncated_gz_is_recorded_not_fatal(tmp_path: Path):
    rels = _setup(tmp_path, n=2)
    bad = rels[0]
    good = rels[1]
    raw = gzip.compress(("\n".join(CLEAN_ROWS * 50) + "\n").encode("utf-8"))
    (tmp_path / bad).write_bytes(raw[: len(raw) // 2])  # cut mid-member: no end-of-stream marker
    with pytest.raises(EOFError):
        with gzip.open(tmp_path / bad, "rt", encoding="utf-8") as f:
            f.read()

    _ledger(tmp_path)
    report = dq.run(tmp_path)  # must not raise

    checks = report["datasets"]["series"]["checks"]
    assert checks["scan_error"]["files"] == 1
    assert checks["scan_error"]["examples"][0]["path"] == bad
    assert checks["scan_error"]["examples"][0]["examples"][0]["error"].startswith("EOFError")
    assert "scan_error" in report["file_cache"][bad]["result"]
    assert report["file_cache"][good]["result"] == {}
    assert report["datasets"]["series"]["files_checked"] == 2


def test_zlib_error_is_recorded_not_fatal(tmp_path: Path, monkeypatch):
    """A corrupt deflate stream surfaces as zlib.error (not an OSError
    subclass); it is hard to build one that gzip does not first report as
    BadGzipFile, so the open is stubbed to raise it directly."""
    import zlib

    rels = _setup(tmp_path, n=1)
    _ledger(tmp_path)  # index built with the real reader

    def broken_open(path, gz):
        raise zlib.error("Error -3 while decompressing data: invalid block type")

    monkeypatch.setattr(il, "open_text", broken_open)
    report = dq.run(tmp_path)  # must not raise

    err = report["file_cache"][rels[0]]["result"]["scan_error"]["examples"][0]["error"]
    assert err == "error: Error -3 while decompressing data: invalid block type"  # zlib.error.__name__ == "error"


# (d) an old-format QUALITY.json (no file_cache) is accepted ---------------


def test_old_format_quality_json_without_cache_still_runs(tmp_path: Path, monkeypatch, capsys):
    rels = _setup(tmp_path, n=2)
    (tmp_path / "data" / "QUALITY.json").write_text(json.dumps({
        "datasets": {"series": {"files_checked": 2, "files_flagged": 0, "checks": {}}},
        "generated_at": "2026-09-01T00:00:00+00:00",
        "ledger_source": "data/INTAKE_latest.json",
        "schema_undefined_count": 0,
        "schema_undefined_files": [],
    }))
    calls = _counting_scan(monkeypatch)

    _ledger(tmp_path)
    report = dq.run(tmp_path)
    out = capsys.readouterr().out

    assert sorted(calls) == sorted(rels)  # nothing to reuse -> everything scanned
    assert "skipped" not in out
    assert set(report) >= {"datasets", "generated_at", "ledger_source",
                           "schema_undefined_count", "schema_undefined_files", "file_cache"}
    assert set(report["file_cache"]) == set(rels)


def test_corrupt_quality_json_is_ignored(tmp_path: Path):
    _setup(tmp_path, n=1)
    (tmp_path / "data" / "QUALITY.json").write_text("{not json")
    _ledger(tmp_path)
    report = dq.run(tmp_path)  # must not raise
    assert "file_cache" in report


# checkpoint: a run killed part-way leaves its finished files behind --------


def test_checkpoint_resumes_after_crash(tmp_path: Path, monkeypatch):
    rels = _setup(tmp_path, n=3)
    calls: list[str] = []
    real = dq.scan_file

    def crash_on_third(root, rel_path, schema):
        calls.append(rel_path)
        if rel_path == rels[2]:
            raise RuntimeError("killed")
        return real(root, rel_path, schema)

    monkeypatch.setattr(dq, "scan_file", crash_on_third)
    _ledger(tmp_path)
    with pytest.raises(RuntimeError):
        dq.run(tmp_path)
    assert calls == rels
    assert not (tmp_path / dq.QUALITY_REL_PATH).exists()  # the report was never written
    side = json.loads((tmp_path / dq.QUALITY_CACHE_REL_PATH).read_text())
    assert set(side["file_cache"]) == {rels[0], rels[1]}

    calls.clear()
    monkeypatch.setattr(dq, "scan_file", lambda root, rel_path, schema: (calls.append(rel_path), real(root, rel_path, schema))[1])
    report = dq.run(tmp_path)  # resumes: 1st and 2nd are skipped
    assert calls == [rels[2]]
    assert set(report["file_cache"]) == set(rels)
    assert report["datasets"]["series"]["files_checked"] == 3


# time budget: --max-seconds stops scanning, the rest resumes next run ------


def test_budget_cuts_at_second_file_and_resumes(tmp_path: Path, monkeypatch, capsys):
    rels = _setup(tmp_path, n=3)
    _ledger(tmp_path)
    calls = _counting_scan(monkeypatch)

    clock = {"t": 0.0}

    def fake_monotonic():
        clock["t"] += 100.0  # every call advances 100s: start, then check/t0/end per file
        return clock["t"]

    monkeypatch.setattr(dq.time, "monotonic", fake_monotonic)
    report = dq.run(tmp_path, max_seconds=150)
    out = capsys.readouterr().out

    assert calls == [rels[0]]  # 2nd file is where the budget runs out
    assert "data_quality: budget exhausted after 1/3 files (" in out
    assert "); the rest resumes next run" in out
    assert report["datasets"]["series"]["files_checked"] == 1
    assert set(report["file_cache"]) == {rels[0]}
    assert set(report) >= {"datasets", "generated_at", "ledger_source",
                           "schema_undefined_count", "schema_undefined_files", "file_cache"}

    monkeypatch.undo()
    calls = _counting_scan(monkeypatch)
    dq.write_report(tmp_path, report)
    report2 = dq.run(tmp_path)  # unlimited: only the two unscanned files are read
    assert calls == [rels[1], rels[2]]
    assert report2["datasets"]["series"]["files_checked"] == 3


def test_budget_zero_means_unlimited(tmp_path: Path, monkeypatch):
    rels = _setup(tmp_path, n=3)
    _ledger(tmp_path)
    calls = _counting_scan(monkeypatch)
    dq.run(tmp_path, max_seconds=0)
    assert calls == rels


# board_top10 matches schema/bitflyer_tape.json (not schema_undefined) ------

BOARD_TOP10_HEADER = (
    "ts,"
    + ",".join(f"bid_px_{i}" for i in range(1, 11)) + ","
    + ",".join(f"bid_sz_{i}" for i in range(1, 11)) + ","
    + ",".join(f"ask_px_{i}" for i in range(1, 11)) + ","
    + ",".join(f"ask_sz_{i}" for i in range(1, 11))
)  # the real header of paper_logs/tape/board_top10_20260918.csv.gz (41 columns)


def test_board_top10_matches_bitflyer_tape_schema(tmp_path: Path):
    repo_schema = Path(__file__).resolve().parents[1] / "schema" / "bitflyer_tape.json"
    (tmp_path / "schema").mkdir()
    (tmp_path / "schema" / "bitflyer_tape.json").write_text(repo_schema.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "data").mkdir()
    rels = []
    for rel in ("paper_logs/tape/board_top10_20260918.csv.gz",
                "data/tape/board_top10_20260918.csv.gz",
                "backtest_data/auto_bitflyer_executions_20260921/board_top10_20260826.csv.gz"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(tmp_path / rel, "wt", encoding="utf-8") as f:
            f.write(BOARD_TOP10_HEADER + "\n")
            for sec in range(3):
                f.write(f"2026-09-18T00:00:0{sec}Z," + ",".join(["1"] * 40) + "\n")
        rels.append(rel)

    _ledger(tmp_path)
    report = dq.run(tmp_path)

    assert report["schema_undefined_files"] == []
    assert report["schema_undefined_count"] == 0
    assert "schema_undefined" not in report["datasets"]
    assert report["datasets"]["bitflyer_tape"]["files_checked"] == 3
    assert "missing_columns" not in report["datasets"]["bitflyer_tape"]["checks"]
    schema = dq.match_dataset(rels[0], dq.load_schemas(tmp_path))
    assert schema["dataset"] == "bitflyer_tape"
    assert dq.schema_columns_for(schema, "board_top10_20260918.csv.gz", rels[0]) == set(BOARD_TOP10_HEADER.split(","))
    assert dq.schema_quality_for(schema, "board_top10_20260918.csv.gz", rels[0])["unique_key"] == ["ts"]
    # board_top5's file_group must not also claim this file (prefix "board_top5_")
    assert dq.schema_columns_for(schema, "board_top5_20260918.csv.gz", "paper_logs/tape/board_top5_20260918.csv.gz") != set(BOARD_TOP10_HEADER.split(","))

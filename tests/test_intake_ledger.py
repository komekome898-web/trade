"""Tests for scripts/intake_ledger.py — the append-only data inventory."""
from __future__ import annotations

import gzip
import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import intake_ledger as il  # noqa: E402


# ---- fixtures ---------------------------------------------------------


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    (tmp_path / "data").mkdir()
    (tmp_path / "paper_logs").mkdir()
    (tmp_path / "backtest_data").mkdir()

    csv_text = "ts,open,close,volume\n2026-01-01T00:00:00Z,1,2,10\n2026-01-01T00:01:00Z,2,3,20\n"
    (tmp_path / "data" / "candles.csv").write_text(csv_text)

    with gzip.open(tmp_path / "data" / "candles.csv.gz", "wt") as f:
        f.write(csv_text)

    jsonl_text = (
        json.dumps({"ts": 1767225600.0, "x": 1}) + "\n"
        + json.dumps({"ts": 1767225660.0, "x": 2}) + "\n"
    )
    (tmp_path / "paper_logs" / "events.jsonl").write_text(jsonl_text)

    (tmp_path / "backtest_data" / "note.json").write_text('{"k": "v"}')

    return tmp_path


# ---- timestamp parsing --------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        "2026-08-25T00:00:00.4097028Z",
        "2026-09-01T00:00:00.932+00:00",
        "2026-07-23 12:09:00+00:00",
        "2026-07-23T12:09:27.13",
        "2009-01-05",
        "20260821",
        "1787201902.737",
    ],
)
def test_parse_ts_accepts_known_formats(raw):
    assert il.parse_ts(raw) is not None


@pytest.mark.parametrize("raw", ["", None, "nan", "not-a-date", "abc123"])
def test_parse_ts_rejects_garbage(raw):
    assert il.parse_ts(raw) is None


def test_parse_ts_yyyymmdd_vs_epoch_disambiguation():
    dt = il.parse_ts("20260821")
    assert (dt.year, dt.month, dt.day) == (2026, 8, 21)


# ---- basic scan ----------------------------------------------------------


def test_scan_creates_ledger_and_index(tree: Path):
    ledger = tree / "data" / "INTAKE.jsonl"
    latest = tree / "data" / "INTAKE_latest.json"
    index = il.run(tree, full=False, ledger_path=ledger, latest_path=latest)

    assert ledger.exists()
    assert latest.exists()

    paths = set(index.keys())
    assert "data/candles.csv" in paths
    assert "data/candles.csv.gz" in paths
    assert "paper_logs/events.jsonl" in paths
    assert "backtest_data/note.json" in paths

    csv_rec = index["data/candles.csv"]
    assert csv_rec["status"] == "present"
    assert csv_rec["row_count"] == 2
    assert csv_rec["first_ts"] is not None
    assert csv_rec["last_ts"] is not None
    assert csv_rec["md5"]
    assert csv_rec["first_seen"] == csv_rec["last_seen"]

    gz_rec = index["data/candles.csv.gz"]
    assert gz_rec["row_count"] == 2

    jsonl_rec = index["paper_logs/events.jsonl"]
    assert jsonl_rec["row_count"] == 2
    assert jsonl_rec["first_ts"] is not None

    json_rec = index["backtest_data/note.json"]
    assert json_rec["row_count"] is None


def test_ledger_output_files_are_excluded_from_scan(tree: Path):
    ledger = tree / "data" / "INTAKE.jsonl"
    latest = tree / "data" / "INTAKE_latest.json"
    index = il.run(tree, full=False, ledger_path=ledger, latest_path=latest)
    assert "data/INTAKE.jsonl" not in index
    assert "data/INTAKE_latest.json" not in index


def test_second_run_unchanged_does_not_append_new_lines(tree: Path):
    ledger = tree / "data" / "INTAKE.jsonl"
    latest = tree / "data" / "INTAKE_latest.json"
    il.run(tree, full=False, ledger_path=ledger, latest_path=latest)
    lines_after_first = ledger.read_text().splitlines()

    il.run(tree, full=False, ledger_path=ledger, latest_path=latest)
    lines_after_second = ledger.read_text().splitlines()

    assert lines_after_second == lines_after_first


def test_changed_file_appends_new_line_and_updates_index(tree: Path):
    ledger = tree / "data" / "INTAKE.jsonl"
    latest = tree / "data" / "INTAKE_latest.json"
    il.run(tree, full=False, ledger_path=ledger, latest_path=latest)
    n_lines_before = len(ledger.read_text().splitlines())

    time.sleep(0.01)
    (tree / "data" / "candles.csv").write_text(
        "ts,open,close,volume\n2026-01-01T00:00:00Z,1,2,10\n"
        "2026-01-01T00:01:00Z,2,3,20\n2026-01-01T00:02:00Z,3,4,30\n"
    )
    index = il.run(tree, full=False, ledger_path=ledger, latest_path=latest)
    n_lines_after = len(ledger.read_text().splitlines())

    assert n_lines_after == n_lines_before + 1
    assert index["data/candles.csv"]["row_count"] == 3


# ---- missing-file tracking -------------------------------------------


def test_missing_file_is_kept_with_status_missing_across_two_runs(tree: Path):
    ledger = tree / "data" / "INTAKE.jsonl"
    latest = tree / "data" / "INTAKE_latest.json"
    index1 = il.run(tree, full=False, ledger_path=ledger, latest_path=latest)
    assert index1["data/candles.csv"]["status"] == "present"
    first_seen = index1["data/candles.csv"]["first_seen"]

    (tree / "data" / "candles.csv").unlink()

    index2 = il.run(tree, full=False, ledger_path=ledger, latest_path=latest)
    rec = index2["data/candles.csv"]
    assert rec["status"] == "missing"
    # never dropped, and its last known stats are preserved
    assert rec["row_count"] == 2
    assert rec["first_seen"] == first_seen

    # a third run (still missing) must not re-append the transition line
    # more than once
    n_lines_after_missing = len(ledger.read_text().splitlines())
    il.run(tree, full=False, ledger_path=ledger, latest_path=latest)
    assert len(ledger.read_text().splitlines()) == n_lines_after_missing

    # every record ever produced is a valid json line
    for line in ledger.read_text().splitlines():
        json.loads(line)


def test_file_coming_back_after_missing_flips_to_present(tree: Path):
    ledger = tree / "data" / "INTAKE.jsonl"
    latest = tree / "data" / "INTAKE_latest.json"
    il.run(tree, full=False, ledger_path=ledger, latest_path=latest)
    (tree / "data" / "candles.csv").unlink()
    il.run(tree, full=False, ledger_path=ledger, latest_path=latest)

    (tree / "data" / "candles.csv").write_text(
        "ts,open,close,volume\n2026-01-01T00:00:00Z,1,2,10\n2026-01-01T00:01:00Z,2,3,20\n"
    )
    index = il.run(tree, full=False, ledger_path=ledger, latest_path=latest)
    assert index["data/candles.csv"]["status"] == "present"


# ---- timestamp cap / --full ---------------------------------------------


def test_default_cap_still_finds_boundary_timestamps_on_large_file(tmp_path: Path):
    (tmp_path / "data").mkdir()
    lines = ["ts,v"]
    for i in range(5000):
        lines.append(f"2026-01-01T{i % 24:02d}:00:{i % 60:02d}Z,{i}")
    (tmp_path / "data" / "big.csv").write_text("\n".join(lines) + "\n")

    row_count, first_ts, last_ts, truncated = il.scan_csv(tmp_path / "data" / "big.csv", gz=False, cap=il.DEFAULT_TS_CAP)
    assert row_count == 5000
    assert first_ts is not None
    assert last_ts is not None
    assert truncated is False


def test_full_mode_scans_without_cap(tmp_path: Path):
    (tmp_path / "data").mkdir()
    # first 3000 rows have a blank timestamp, only the tail is parseable --
    # exercises the boundary beyond the default 2000-row cap.
    lines = ["ts,v"]
    for i in range(3000):
        lines.append(f",{i}")
    lines.append("2026-01-01T00:00:00Z,end")
    (tmp_path / "data" / "tail.csv").write_text("\n".join(lines) + "\n")

    row_count, first_ts, last_ts, truncated = il.scan_csv(tmp_path / "data" / "tail.csv", gz=False, cap=None)
    assert row_count == 3001
    assert first_ts == last_ts  # only one parseable value anywhere in the file
    assert first_ts is not None
    assert truncated is False


# ---- truncated gzip (multi-member, last member cut off mid-write) -------


def _multi_member_truncated_gz(path: Path, complete_members: list[str], last_member_text: str,
                               chop_bytes: int = 15) -> None:
    """Write N complete gzip members, then a final member whose deflate
    stream is cut off before its end-of-stream marker — the shape a live
    WS recorder leaves behind when killed mid-flush (see
    src/bot/market_data/realtime.py)."""
    with gzip.open(path, "wb") as f:
        f.write(complete_members[0].encode("utf-8"))
    for text in complete_members[1:]:
        with gzip.open(path, "ab") as f:
            f.write(text.encode("utf-8"))
    good_len = path.stat().st_size
    with gzip.open(path, "ab") as f:
        f.write(last_member_text.encode("utf-8"))
    raw = path.read_bytes()
    assert len(raw) > good_len + chop_bytes  # sanity: a member was actually added
    path.write_bytes(raw[: len(raw) - chop_bytes])


def test_truncated_multi_member_csv_gz_yields_partial_count_and_truncated_flag(tmp_path: Path):
    path = tmp_path / "cut.csv.gz"
    header_and_good_rows = "ts,v\n" + "".join(
        f"2026-01-01T00:00:{i:02d}Z,{i}\n" for i in range(5))
    last_member_rows = "".join(
        f"2026-01-01T00:01:{i:02d}Z,{100 + i}\n" for i in range(50))
    _multi_member_truncated_gz(path, [header_and_good_rows], last_member_rows)

    with pytest.raises(EOFError):
        # sanity check the fixture actually reproduces a truncated read
        with gzip.open(path, "rt") as f:
            f.read()

    row_count, first_ts, last_ts, truncated = il.scan_csv(path, gz=True, cap=None)
    assert truncated is True
    assert row_count is not None and row_count >= 5  # the complete member's rows
    assert first_ts is not None


def test_truncated_jsonl_gz_yields_partial_count_and_truncated_flag(tmp_path: Path):
    path = tmp_path / "cut.jsonl.gz"
    good_lines = "".join(
        json.dumps({"ts": 1767225600.0 + i, "x": i}) + "\n" for i in range(5))
    last_member_lines = "".join(
        json.dumps({"ts": 1767225700.0 + i, "x": 100 + i}) + "\n" for i in range(50))
    _multi_member_truncated_gz(path, [good_lines], last_member_lines)

    row_count, first_ts, last_ts, truncated = il.scan_jsonl(path, gz=True, cap=None)
    assert truncated is True
    assert row_count is not None and row_count >= 5
    assert first_ts is not None


def test_scan_one_marks_truncated_and_keeps_partial_row_count(tmp_path: Path):
    (tmp_path / "data").mkdir()
    path = tmp_path / "data" / "live_20260101_000000.jsonl.gz"
    good_lines = "".join(
        json.dumps({"ts": 1767225600.0 + i, "x": i}) + "\n" for i in range(7))
    last_member_lines = "".join(
        json.dumps({"ts": 1767225700.0 + i, "x": 100 + i}) + "\n" for i in range(50))
    _multi_member_truncated_gz(path, [good_lines], last_member_lines)

    rec = il.scan_one("data/live_20260101_000000.jsonl.gz", path, cap=None)
    assert rec["truncated"] is True
    # partial count kept (not None as it used to be) — some of the final,
    # incomplete member's lines decompress fine before the cutoff bites.
    assert rec["row_count"] is not None and rec["row_count"] >= 7
    assert rec["first_ts"] is not None
    assert "scan_error" in rec


# ---- summary ---------------------------------------------------------


def test_dataset_dir_grouping():
    assert il.dataset_dir("data/candles.csv") == "data"
    assert il.dataset_dir("data/tape/ticker_20260101.csv.gz") == "data/tape"
    assert il.dataset_dir("backtest_data/n225f_225labo_20260828/manifest.json") == "backtest_data/n225f_225labo_20260828"


def test_print_summary_runs_without_error(tree: Path, capsys):
    ledger = tree / "data" / "INTAKE.jsonl"
    latest = tree / "data" / "INTAKE_latest.json"
    index = il.run(tree, full=False, ledger_path=ledger, latest_path=latest)
    il.print_summary(index)
    out = capsys.readouterr().out
    assert "dataset" in out
    assert "TOTAL" in out


# ---- CLI end-to-end -------------------------------------------------


def test_main_cli_runs(tree: Path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["intake_ledger.py", "--root", str(tree), "--summary"])
    rc = il.main()
    assert rc == 0
    out = capsys.readouterr().out
    assert "intake_ledger:" in out
    assert (tree / "data" / "INTAKE.jsonl").exists()
    assert (tree / "data" / "INTAKE_latest.json").exists()

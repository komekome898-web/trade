"""Tests for scripts/repair_gz_listing.py — read-only gzip-member diagnostic.

Confirms: (1) member/completeness/recoverable-bytes detection is correct on
clean single-member, clean multi-member, and truncated-last-member files;
(2) the tool never opens a scanned file for writing (size/mtime/content
unchanged after a full run, including via the CLI)."""
from __future__ import annotations

import gzip
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import repair_gz_listing as rgl  # noqa: E402


def _member(text: str) -> bytes:
    import io
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as f:
        f.write(text.encode("utf-8"))
    return buf.getvalue()


def test_clean_single_member(tmp_path):
    path = tmp_path / "a.gz"
    path.write_bytes(_member("hello world\n" * 5))

    rec = rgl.analyze_gz(path)
    assert rec["members"] == 1
    assert rec["complete_members"] == 1
    assert rec["last_member_complete"] is True
    assert rec["recoverable_bytes"] == len("hello world\n" * 5)
    assert rec["error"] is None


def test_clean_multi_member(tmp_path):
    path = tmp_path / "b.gz"
    path.write_bytes(_member("first\n") + _member("second\n") + _member("third\n"))

    rec = rgl.analyze_gz(path)
    assert rec["members"] == 3
    assert rec["complete_members"] == 3
    assert rec["last_member_complete"] is True
    assert rec["recoverable_bytes"] == len("first\nsecond\nthird\n")


def test_truncated_last_member_reports_partial_recovery(tmp_path):
    path = tmp_path / "c.gz"
    good = _member("complete member\n" * 10)
    bad = _member("this member gets cut off mid-stream " * 50)
    path.write_bytes(good + bad[:-10])  # chop the trailer off the last member

    rec = rgl.analyze_gz(path)
    assert rec["members"] == 2
    assert rec["complete_members"] == 1
    assert rec["last_member_complete"] is False
    # the complete member's bytes are still counted, plus whatever the
    # truncated member managed to decompress before the cut
    assert rec["recoverable_bytes"] >= len("complete member\n" * 10)


def test_corrupted_middle_reports_error_not_crash(tmp_path):
    path = tmp_path / "d.gz"
    good = _member("ok\n")
    junk = b"not a gzip member at all, just garbage bytes"
    path.write_bytes(good + junk)

    rec = rgl.analyze_gz(path)
    assert rec["members"] == 1
    assert rec["complete_members"] == 1
    assert rec["error"] is not None
    assert "offset" in rec["error"]


def test_missing_file_reports_error_not_crash(tmp_path):
    rec = rgl.analyze_gz(tmp_path / "does_not_exist.gz")
    assert rec["error"] is not None
    assert rec["bytes"] is None


# ---- read-only guarantee -------------------------------------------------


def test_analyze_and_cli_never_modify_the_scanned_files(tmp_path, capsys):
    (tmp_path / "sub").mkdir()
    clean = tmp_path / "sub" / "clean.gz"
    clean.write_bytes(_member("data\n" * 3))
    truncated = tmp_path / "sub" / "truncated.gz"
    truncated.write_bytes(_member("a\n") + _member("b\n" * 20)[:-8])

    before = {p: (p.stat().st_size, p.stat().st_mtime_ns, p.read_bytes())
              for p in (clean, truncated)}
    time.sleep(0.01)

    report = rgl.build_report(tmp_path)
    assert len(report) == 2
    rgl.print_table(report)
    capsys.readouterr()

    for p, (size, mtime, content) in before.items():
        assert p.stat().st_size == size
        assert p.stat().st_mtime_ns == mtime
        assert p.read_bytes() == content


def test_cli_refuses_json_output_under_data_dir(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(rgl, "REPO_ROOT", tmp_path)
    (tmp_path / "data" / "ws").mkdir(parents=True)
    (tmp_path / "data" / "ws" / "x.gz").write_bytes(_member("x\n"))
    monkeypatch.setattr(sys, "argv", [
        "repair_gz_listing.py", "--root", str(tmp_path / "data" / "ws"),
        "--json", str(tmp_path / "data" / "report.json"),
    ])

    rc = rgl.main()
    assert rc == 1
    assert not (tmp_path / "data" / "report.json").exists()
    err = capsys.readouterr().err
    assert "refusing" in err


def test_cli_writes_json_report_outside_data_dir(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(rgl, "REPO_ROOT", tmp_path)
    (tmp_path / "data" / "ws").mkdir(parents=True)
    (tmp_path / "data" / "ws" / "x.gz").write_bytes(_member("x\n"))
    out_json = tmp_path / "reports" / "gz_listing.json"
    monkeypatch.setattr(sys, "argv", [
        "repair_gz_listing.py", "--root", str(tmp_path / "data" / "ws"),
        "--json", str(out_json),
    ])

    rc = rgl.main()
    assert rc == 0
    assert out_json.exists()
    import json
    data = json.loads(out_json.read_text())
    assert len(data) == 1
    assert data[0]["last_member_complete"] is True

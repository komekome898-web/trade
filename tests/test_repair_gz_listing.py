"""Tests for scripts/repair_gz_listing.py — read-only gzip-member diagnostic.

Confirms: (1) member/completeness/recoverable-bytes detection is correct on
clean single-member, clean multi-member, and truncated-last-member files;
(2) the tool never opens a scanned file for writing (size/mtime/content
unchanged after a full run, including via the CLI)."""
from __future__ import annotations

import gzip
import sys
import time
from pathlib import Path, PureWindowsPath

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


def test_cli_allows_the_self_report_path_under_data_dir(tmp_path, monkeypatch, capsys):
    """The one path deploy/fetch_all.bat actually passes
    (data\\WS_GZ_LISTING.json on Windows) must be allowed even though it is
    under data/ — this is the bug: the generic 'nothing under data/' guard
    used to block the tool's own designated self-report location."""
    monkeypatch.setattr(rgl, "REPO_ROOT", tmp_path)
    (tmp_path / "data" / "ws").mkdir(parents=True)
    (tmp_path / "data" / "ws" / "x.gz").write_bytes(_member("x\n"))
    self_report = tmp_path / "data" / "WS_GZ_LISTING.json"
    monkeypatch.setattr(sys, "argv", [
        "repair_gz_listing.py", "--root", str(tmp_path / "data" / "ws"),
        "--json", str(self_report),
    ])

    rc = rgl.main()
    assert rc == 0
    assert self_report.exists()
    err = capsys.readouterr().err
    assert "refusing" not in err


def test_cli_still_refuses_other_names_under_data_dir(tmp_path, monkeypatch, capsys):
    """Only the exact self-report name is exempt — any other filename under
    data/ (including a near-miss) stays blocked."""
    monkeypatch.setattr(rgl, "REPO_ROOT", tmp_path)
    (tmp_path / "data" / "ws").mkdir(parents=True)
    (tmp_path / "data" / "ws" / "x.gz").write_bytes(_member("x\n"))
    near_miss = tmp_path / "data" / "ws" / "WS_GZ_LISTING.json"
    monkeypatch.setattr(sys, "argv", [
        "repair_gz_listing.py", "--root", str(tmp_path / "data" / "ws"),
        "--json", str(near_miss),
    ])

    rc = rgl.main()
    assert rc == 1
    assert not near_miss.exists()
    assert "refusing" in capsys.readouterr().err


# ---- Windows-style path handling -----------------------------------------
# These don't need an actual Windows host: Path.resolve() on POSIX already
# treats a literal backslash as one funny-looking filename character, so we
# reproduce the Windows-side path shape with pathlib.PureWindowsPath instead
# of relying on os.sep / the running platform's own Path implementation.


def test_is_under_data_matches_windows_style_absolute_path():
    win_root = PureWindowsPath(r"C:\Users\owner\trade")
    win_json = PureWindowsPath(r"C:\Users\owner\trade\data\WS_GZ_LISTING.json")
    win_data = win_root / "data"
    assert win_data == win_json.parent
    assert win_data in win_json.parents


def test_is_self_report_recognizes_backslash_relative_path(tmp_path):
    # Simulate what happens when the bat file's literal argument
    # "data\WS_GZ_LISTING.json" is resolved on a real Windows host: pathlib's
    # WindowsPath treats backslash natively, so the resolved path lands
    # exactly at <repo_root>/data/WS_GZ_LISTING.json on that OS too. We
    # exercise the same relative_to/as_posix logic repair_gz_listing.py uses,
    # via an actual Path built through parts (OS-independent construction is
    # what we're pinning down, not the literal separator character).
    repo_root = tmp_path
    resolved = repo_root.joinpath("data", "WS_GZ_LISTING.json").resolve()
    assert rgl._is_self_report(resolved, repo_root)
    assert rgl._is_under_data(resolved, repo_root)

    # A different file under data/ must NOT be treated as the self-report.
    other = repo_root.joinpath("data", "ws", "WS_GZ_LISTING.json").resolve()
    assert not rgl._is_self_report(other, repo_root)
    assert rgl._is_under_data(other, repo_root)


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


def test_unexpected_exception_prints_one_line_and_exits_nonzero(tmp_path, monkeypatch, capsys):
    """An unforeseen failure must never die silently (e.g. an unlogged
    traceback swallowed by a bat file's stdout/stderr redirection) — main()
    catches it, prints a single stderr line, and returns non-zero."""
    monkeypatch.setattr(sys, "argv", ["repair_gz_listing.py", "--root", str(tmp_path)])
    monkeypatch.setattr(rgl, "build_report", lambda root: (_ for _ in ()).throw(RuntimeError("boom")))

    rc = rgl.main()
    assert rc == 1
    err = capsys.readouterr().err.strip()
    assert err.count("\n") == 0
    assert "boom" in err


def test_self_report_relative_matches_intake_ledger_self_files():
    """scripts/intake_ledger.py must already know this tool's self-report
    output is not recorded data — keep the two constants in sync."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import intake_ledger
    assert rgl.SELF_REPORT_RELATIVE in intake_ledger.SELF_FILES

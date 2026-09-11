"""Writer の gzip 書き方(scripts/record_liquidations.py)。2026-09-12、L-121。

固定するのは一点: **1 つの gzip メンバを開いたまま保持しない**こと。
flush ごとに完結したメンバを追記するので、ハードキル直後に別プロセスが
追記しても、前のメンバの途中に継ぎ足すことがなく、ファイル全体が
`gzip.open` で読める。
"""
from __future__ import annotations

import gzip
import importlib.util
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _load(name: str):
    path = REPO / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


rec = _load("record_liquidations")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _read_all(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def _magic_count(path: Path) -> int:
    """Number of gzip members on disk. The file is opened lazily by the
    first flush — before that it does not exist at all, which counts as 0."""
    if not path.exists():
        return 0
    with open(path, "rb") as raw:
        return raw.read().count(b"\x1f\x8b")


# ---------------------------------------------------------------------------
# every flush produces a complete, independently-readable gzip member
# ---------------------------------------------------------------------------


def test_row_count_flush_writes_complete_members(tmp_path, monkeypatch):
    monkeypatch.setattr(rec, "OUT_DIR", tmp_path)
    monkeypatch.setattr(rec, "FLUSH_MAX_LINES", 3)
    monkeypatch.setattr(rec, "FLUSH_INTERVAL_SEC", 999.0)  # never fires on time alone

    w = rec.Writer("bybit")
    for i in range(7):
        w.write({"venue": "bybit", "recv_us": i, "raw": {"i": i}})
    # 7 lines at a max of 3 per flush -> two flushes already happened (6 rows
    # flushed), 1 row still buffered.
    path = tmp_path / f"bybit_{_today()}.jsonl.gz"
    with open(path, "rb") as raw:
        blob = raw.read()
    assert blob.count(b"\x1f\x8b") == 2  # exactly two complete members written so far

    w.close()  # flushes the remaining buffered row as a third member
    with open(path, "rb") as raw:
        blob = raw.read()
    assert blob.count(b"\x1f\x8b") == 3

    rows = _read_all(path)
    assert [r["raw"]["i"] for r in rows] == list(range(7))


def test_time_based_flush_fires_on_next_message_not_a_background_timer(tmp_path, monkeypatch):
    """The time trigger is only ever checked inside write() — there is no
    thread/task polling on its own, so an idle stream costs nothing."""
    monkeypatch.setattr(rec, "OUT_DIR", tmp_path)
    monkeypatch.setattr(rec, "FLUSH_MAX_LINES", 10_000)  # so only the timer can trigger
    monkeypatch.setattr(rec, "FLUSH_INTERVAL_SEC", 0.05)

    w = rec.Writer("okx")
    w.write({"venue": "okx", "recv_us": 1, "raw": {"i": 0}})
    path = tmp_path / f"okx_{_today()}.jsonl.gz"
    assert _magic_count(path) == 0  # not flushed yet — under the row cap, file not even created

    time.sleep(0.1)  # interval elapses, but nothing checks it without a write()
    assert _magic_count(path) == 0  # still nothing — no spinning timer

    w.write({"venue": "okx", "recv_us": 2, "raw": {"i": 1}})  # this call notices the elapsed time
    assert _magic_count(path) == 1

    w.close()
    rows = _read_all(path)
    assert [r["raw"]["i"] for r in rows] == [0, 1]


# ---------------------------------------------------------------------------
# the actual bug: hard kill mid-buffer, then a fresh Writer appends
# ---------------------------------------------------------------------------


def test_hard_kill_then_fresh_writer_appends_a_file_still_fully_readable(tmp_path, monkeypatch):
    """Simulates deploy\\stop_all.bat's Stop-Process -Force: the old Writer
    is simply abandoned mid-buffer (never .close()d, no atexit) — flush()
    has already been called for everything up to that point, so what's on
    disk is only complete members. A brand new Writer then appends more.
    The result must be readable end to end with NO error — this is exactly
    what the old gzip.open(path, 'at')-held-open design could not guarantee."""
    monkeypatch.setattr(rec, "OUT_DIR", tmp_path)
    monkeypatch.setattr(rec, "FLUSH_MAX_LINES", 2)
    monkeypatch.setattr(rec, "FLUSH_INTERVAL_SEC", 999.0)

    dead = rec.Writer("okx")
    for i in range(5):
        dead.write({"venue": "okx", "recv_us": i, "raw": {"i": i}})
    # 5 lines, flush at every 2 -> flushed 4, one (#4) sits unflushed in the
    # buffer. The process is now hard-killed: dead.close() is deliberately
    # NEVER called, and the buffered row is lost — that is the documented,
    # bounded loss. Nothing partially-written must be on disk though.
    path = tmp_path / f"okx_{_today()}.jsonl.gz"
    with open(path, "rb") as raw:
        blob_before_restart = raw.read()
    assert blob_before_restart.count(b"\x1f\x8b") == 2  # two complete members, no partial one

    fresh = rec.Writer("okx")  # the restarted process's Writer
    for i in range(5, 8):
        fresh.write({"venue": "okx", "recv_us": i, "raw": {"i": i}})
    fresh.close()

    # the whole file, dead process's flushed rows + restarted process's rows,
    # must be readable in one gzip.open pass with no exception at all.
    rows = _read_all(path)
    assert [r["raw"]["i"] for r in rows] == [0, 1, 2, 3, 5, 6, 7]  # #4 is the bounded loss


# ---------------------------------------------------------------------------
# self-heal on open: a file left over from the OLD (pre-fix) Writer, whose
# last member has no trailer, must never be appended to (2026-09-12).
# ---------------------------------------------------------------------------


def _unterminated_member_bytes(text: str) -> bytes:
    import zlib
    comp = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)
    return comp.compress(text.encode("utf-8")) + comp.flush(zlib.Z_SYNC_FLUSH)


def test_existing_truncated_day_file_is_moved_aside_not_appended_to(tmp_path, monkeypatch):
    """The exact rollout scenario: the nightly restart (L-125) hard-kills
    the OLD Writer before this fix is even pulled, so the first run of the
    FIXED Writer finds today's file already broken. It must heal instead of
    reproducing the corruption."""
    monkeypatch.setattr(rec, "OUT_DIR", tmp_path)
    monkeypatch.setattr(rec, "FLUSH_MAX_LINES", 10_000)
    monkeypatch.setattr(rec, "FLUSH_INTERVAL_SEC", 999.0)

    day = _today()
    path = tmp_path / f"bitmex_{day}.jsonl.gz"
    dead_rows = [json.dumps({"venue": "bitmex", "recv_us": i, "raw": {"i": i}}) for i in range(4)]
    path.write_bytes(_unterminated_member_bytes("\n".join(dead_rows) + "\n"))

    with pytest.raises((EOFError, gzip.BadGzipFile)):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            f.read()

    w = rec.Writer("bitmex")
    w.write({"venue": "bitmex", "recv_us": 100, "raw": {"i": 100}})
    w.close()

    moved = tmp_path / f"bitmex_{day}.trunc1.jsonl.gz"
    assert moved.exists(), "壊れていた旧ファイルが退避されていない"
    assert path.exists()

    # the fresh file must be fully, cleanly readable and hold only the NEW rows
    assert [r["raw"]["i"] for r in _read_all(path)] == [100]

    # the moved-aside file still holds the dead rows, recoverable (not deleted)
    from bot.research.gz_members import recover_json_lines
    recovered = recover_json_lines(moved.read_bytes())
    assert [json.loads(ln)["raw"]["i"] for ln in recovered.lines] == [0, 1, 2, 3]


def test_second_heal_on_the_same_day_never_overwrites_the_first_trunc_file(tmp_path, monkeypatch):
    monkeypatch.setattr(rec, "OUT_DIR", tmp_path)
    monkeypatch.setattr(rec, "FLUSH_MAX_LINES", 10_000)
    monkeypatch.setattr(rec, "FLUSH_INTERVAL_SEC", 999.0)

    day = _today()
    path = tmp_path / f"okx_{day}.jsonl.gz"
    trunc1 = tmp_path / f"okx_{day}.trunc1.jsonl.gz"
    trunc1.write_bytes(gzip.compress(b'{"already": "here"}\n'))  # a prior heal already happened

    path.write_bytes(_unterminated_member_bytes('{"venue": "okx", "recv_us": 1, "raw": {}}\n'))

    w = rec.Writer("okx")
    w.write({"venue": "okx", "recv_us": 2, "raw": {"i": 2}})
    w.close()

    trunc2 = tmp_path / f"okx_{day}.trunc2.jsonl.gz"
    assert trunc2.exists()
    with gzip.open(trunc1, "rt", encoding="utf-8") as f:
        assert json.loads(f.read()) == {"already": "here"}  # untouched
    assert [r["raw"]["i"] for r in _read_all(path)] == [2]


def test_a_healthy_existing_file_is_appended_to_normally_not_healed(tmp_path, monkeypatch):
    """A file left by a CLEAN shutdown (close() was called) must not be
    treated as corrupt — the recorder should keep appending to it."""
    monkeypatch.setattr(rec, "OUT_DIR", tmp_path)
    monkeypatch.setattr(rec, "FLUSH_MAX_LINES", 10_000)
    monkeypatch.setattr(rec, "FLUSH_INTERVAL_SEC", 999.0)

    day = _today()
    path = tmp_path / f"okx_{day}.jsonl.gz"
    first = rec.Writer("okx")
    first.write({"venue": "okx", "recv_us": 1, "raw": {"i": 0}})
    first.close()  # clean shutdown -> complete member on disk

    second = rec.Writer("okx")
    second.write({"venue": "okx", "recv_us": 2, "raw": {"i": 1}})
    second.close()

    assert not (tmp_path / f"okx_{day}.trunc1.jsonl.gz").exists()
    assert [r["raw"]["i"] for r in _read_all(path)] == [0, 1]


# ---------------------------------------------------------------------------
# day rollover
# ---------------------------------------------------------------------------


def test_day_rollover_flushes_the_old_day_and_opens_a_new_file(tmp_path, monkeypatch):
    """Seed the Writer as if it were already mid-way through a PAST UTC day
    (no need to fake `datetime` itself, which _log also calls) — the next
    write(), stamped with the real current day, must then detect the
    mismatch, flush the old day's buffer to the old day's file, and start a
    fresh file for today without losing either day's rows."""
    monkeypatch.setattr(rec, "OUT_DIR", tmp_path)
    monkeypatch.setattr(rec, "FLUSH_MAX_LINES", 10_000)
    monkeypatch.setattr(rec, "FLUSH_INTERVAL_SEC", 999.0)

    old_day = "20200101"
    old_path = tmp_path / f"bitmex_{old_day}.jsonl.gz"

    w = rec.Writer("bitmex")
    w._day = old_day
    w._path = old_path
    w._buf = [
        (json.dumps({"venue": "bitmex", "recv_us": i, "raw": {"i": i}}) + "\n").encode("utf-8")
        for i in (0, 1)
    ]

    w.write({"venue": "bitmex", "recv_us": 2, "raw": {"i": 2}})  # real "today" -> rollover
    w.close()

    today_path = tmp_path / f"bitmex_{_today()}.jsonl.gz"
    assert old_path.exists() and today_path.exists()
    assert [r["raw"]["i"] for r in _read_all(old_path)] == [0, 1]
    assert [r["raw"]["i"] for r in _read_all(today_path)] == [2]


def test_close_flushes_whatever_is_buffered(tmp_path, monkeypatch):
    monkeypatch.setattr(rec, "OUT_DIR", tmp_path)
    monkeypatch.setattr(rec, "FLUSH_MAX_LINES", 10_000)
    monkeypatch.setattr(rec, "FLUSH_INTERVAL_SEC", 999.0)

    w = rec.Writer("binance_cm")
    w.write({"venue": "binance_cm", "recv_us": 1, "raw": {"i": 0}})
    path = tmp_path / f"binance_cm_{_today()}.jsonl.gz"
    assert _magic_count(path) == 0  # nothing flushed yet, file not even created
    w.close()
    assert _magic_count(path) == 1
    assert _read_all(path)[0]["raw"]["i"] == 0

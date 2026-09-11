"""Tests for bot.research.gz_members — recovering JSONL rows from a gzip
file with a corrupted member boundary (2026-09-12, L-121).

The central scenario reproduces the exact `record_liquidations.py` bug: a
member with NO end-of-stream trailer (hard-killed mid-session) followed
immediately by a fresh member's header (the restarted process's first
write) — this is what raises `zlib.error: ... invalid block type` from a
plain `gzip.open(...).read()` and must not lose the dead member's rows.
"""
from __future__ import annotations

import gzip
import io
import json
import zlib

import pytest

from bot.research.gz_members import (
    RecoveredLines,
    decompress_piece,
    find_member_offsets,
    is_cleanly_readable,
    recover_json_lines,
    split_raw_members,
)


def _member(text: str) -> bytes:
    """One complete, closed gzip member."""
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as f:
        f.write(text.encode("utf-8"))
    return buf.getvalue()


def _unterminated_member(text: str) -> bytes:
    """A gzip member whose deflate stream has NO end-of-stream trailer — the
    exact shape `gzip.open(path, "at")` left behind mid-session before this
    bug was fixed (Z_SYNC_FLUSH, never Z_FINISH)."""
    comp = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)
    out = comp.compress(text.encode("utf-8"))
    out += comp.flush(zlib.Z_SYNC_FLUSH)
    return out


def _rows(n: int, start: int = 0) -> list[dict]:
    return [{"venue": "bitmex", "recv_us": start + i, "raw": {"i": i}} for i in range(n)]


def _jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(r) + "\n" for r in rows)


# ---------------------------------------------------------------------------
# find_member_offsets / split_raw_members
# ---------------------------------------------------------------------------


def test_find_member_offsets_locates_every_member_start():
    data = _member("a\n") + _member("b\n") + _member("c\n")
    offsets = find_member_offsets(data)
    assert len(offsets) == 3
    assert offsets[0] == 0
    for off in offsets:
        assert data[off:off + 3] == b"\x1f\x8b\x08"


def test_split_raw_members_slices_exactly_at_each_header():
    a, b, c = _member("a\n"), _member("b\n"), _member("c\n")
    pieces = split_raw_members(a + b + c)
    assert pieces == [a, b, c]


def test_split_raw_members_on_empty_input():
    assert split_raw_members(b"") == []


def test_split_raw_members_with_garbage_prefix_returns_whole_blob():
    data = b"not gzip at all"
    assert split_raw_members(data) == [data]


# ---------------------------------------------------------------------------
# decompress_piece
# ---------------------------------------------------------------------------


def test_decompress_piece_complete_member():
    res = decompress_piece(_member("hello\n"))
    assert res.complete is True
    assert res.decompressed == b"hello\n"
    assert res.error is None


def test_decompress_piece_unterminated_member_returns_partial_no_exception():
    """No trailer, and nothing follows it in the piece (because the piece
    boundary already excludes any following member) — must not raise."""
    piece = _unterminated_member("recovered\n")
    res = decompress_piece(piece)
    assert res.complete is False
    assert res.decompressed == b"recovered\n"
    assert res.error is None


def test_decompress_piece_on_pure_garbage_reports_error_not_crash():
    res = decompress_piece(b"\x1f\x8b\x08not a real deflate stream at all")
    assert res.error is not None
    assert res.complete is False


# ---------------------------------------------------------------------------
# recover_json_lines — the exact bug reproduction
# ---------------------------------------------------------------------------


def test_reproduces_invalid_block_type_and_fully_recovers_both_halves():
    """Build a file exactly the way the bug did: an unterminated member
    (dead recorder) immediately followed by a fresh member's header (the
    restarted process). Confirm a plain gzip read fails with the documented
    error, then confirm recover_json_lines gets every row from both members."""
    dead_rows = _rows(20, start=1_000)
    live_rows = _rows(15, start=2_000)
    corrupted = _unterminated_member(_jsonl(dead_rows)) + _member(_jsonl(live_rows))

    with pytest.raises(zlib.error):
        gzip.decompress(corrupted)

    result = recover_json_lines(corrupted)
    assert isinstance(result, RecoveredLines)
    assert result.members_found == 2
    assert result.members_complete == 1  # only the second (live) member has a trailer
    assert len(result.lines) == 35
    assert result.lines_discarded == 0

    recovered = [json.loads(ln) for ln in result.lines]
    assert [r["raw"]["i"] for r in recovered[:20]] == list(range(20))
    assert [r["raw"]["i"] for r in recovered[20:]] == list(range(15))


def test_a_half_written_last_line_is_discarded_not_kept_as_garbage():
    good = _rows(3)
    piece = _jsonl(good) + '{"venue": "bitmex", "recv_u'  # mid-write when killed
    corrupted = _unterminated_member(piece)

    result = recover_json_lines(corrupted)
    assert len(result.lines) == 3
    assert result.lines_discarded == 1


def test_only_the_dead_member_is_broken_the_live_one_still_decodes_cleanly():
    """The scenario's whole point: splitting on raw bytes means the second,
    properly-closed member's own completeness is unaffected by the first
    member's missing trailer."""
    corrupted = _unterminated_member(_jsonl(_rows(5))) + _member(_jsonl(_rows(5, start=100)))
    result = recover_json_lines(corrupted)
    assert result.members_complete == 1
    assert len(result.lines) == 10


def test_three_kills_in_a_row_all_members_recovered():
    """Multiple restarts in one file (killed, restarted, killed again) —
    every member's rows come back regardless of position."""
    chunks = [_rows(4, start=0), _rows(4, start=10), _rows(4, start=20), _rows(4, start=30)]
    blob = b"".join(_unterminated_member(_jsonl(c)) for c in chunks[:-1])
    blob += _member(_jsonl(chunks[-1]))  # the final, still-running member is closed cleanly
    result = recover_json_lines(blob)
    assert result.members_found == 4
    assert len(result.lines) == 16


def test_non_json_fragment_from_a_false_split_is_discarded_never_raised():
    result = recover_json_lines(b"not a gzip file at all")
    assert result.lines == []
    assert result.members_found == 1


# ---------------------------------------------------------------------------
# is_cleanly_readable
# ---------------------------------------------------------------------------


def test_is_cleanly_readable_true_for_a_normal_closed_file():
    assert is_cleanly_readable(_member("fine\n")) is True


def test_is_cleanly_readable_false_for_the_corrupted_boundary_case():
    corrupted = _unterminated_member(_jsonl(_rows(5))) + _member(_jsonl(_rows(5)))
    assert is_cleanly_readable(corrupted) is False


def test_is_cleanly_readable_false_for_a_plain_truncated_member():
    assert is_cleanly_readable(_unterminated_member("x\n")) is False

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


# ---------------------------------------------------------------------------
# iter_members_in_order / last_member_is_complete (2026-10-02)
# The bytes 1f 8b 08 occur by chance inside healthy members; deciding member
# boundaries by them cut healthy files (docs/AUDITOR/VERDICTS/
# 2026-10-02_W2_recorders.md). The in-order walk asks zlib where each member
# ends instead.
# ---------------------------------------------------------------------------

import random  # noqa: E402

from bot.research.gz_members import (  # noqa: E402
    iter_members_in_order,
    last_member_is_complete,
)

ISIZE_MAGIC_LEN = 0x088B1F     # a member this long ends with ISIZE = 1f 8b 08 00


def _random_rows(seed: int) -> str:
    r = random.Random(seed)
    return "".join(f"{r.randbytes(16).hex()},{r.random():.9f}\n" for _ in range(4000))


def member_with_inner_magic(make_text, start_seed: int):
    """(text, member) whose compressed deflate data (not its header, not its
    trailer) contains 1f 8b 08. start_seed is the first hit found with zlib
    1.3 (2026-10-02); another zlib searches on from there."""
    for seed in range(start_seed, start_seed + 50_000):
        text = make_text(seed)
        data = gzip.compress(text.encode("utf-8"), mtime=0)
        i = data.find(b"\x1f\x8b\x08", 10)
        if i != -1 and i < len(data) - 8:
            return text, data
    raise AssertionError("no member with an inner 1f 8b 08 found")


def test_in_order_walk_finds_every_member_and_its_bytes():
    a, b, c = _member("a\n"), _member("b\n" * 1000), _member("c\n")
    members = list(iter_members_in_order(a + b + c))
    assert [(m.start, m.end, m.complete) for m in members] == [
        (0, len(a), True), (len(a), len(a) + len(b), True),
        (len(a) + len(b), len(a) + len(b) + len(c), True)]
    assert [m.payload for m in members] == [b"a\n", b"b\n" * 1000, b"c\n"]
    assert last_member_is_complete(a + b + c) is True


def test_member_larger_than_the_read_and_output_chunks():
    """One member spanning several READ_CHUNKs and several OUT_CHUNKs."""
    import os
    big = gzip.compress(os.urandom(3 << 20))
    zeros = gzip.compress(b"\0" * (50 << 20))
    tail = _member("end\n")
    assert last_member_is_complete(big + zeros + tail) is True
    ends = [m.end for m in iter_members_in_order(big + zeros + tail,
                                                 keep_payload=False)]
    assert ends == [len(big), len(big) + len(zeros),
                    len(big) + len(zeros) + len(tail)]


@pytest.mark.parametrize("keep", [1, 2, 9, 10, 30, -9, -1])
def test_a_member_cut_by_a_kill_is_not_complete(keep):
    """A kill mid-write leaves the first `keep` bytes of the new member (a
    negative keep: all but the last bytes)."""
    data = _member("x\n") + _member(_random_rows(1))[:keep]
    assert last_member_is_complete(data) is False
    members = list(iter_members_in_order(data))
    assert members[0].complete and members[0].payload == b"x\n"
    assert members[-1].complete is False and members[-1].end == len(data)


def test_stray_bytes_after_the_last_whole_member_are_not_complete():
    assert last_member_is_complete(_member("x\n") + b"\x1f") is False
    assert last_member_is_complete(_member("x\n") + b"\x1f\x8b\x08") is False


def test_old_style_unterminated_member_followed_by_a_new_one_is_not_complete():
    """The 2026-09-11 shape (gzip.open 'at' killed, then appended to): the walk
    cannot get past the dead member, so the file is not whole."""
    corrupted = _unterminated_member(_jsonl(_rows(5))) + _member(_jsonl(_rows(5)))
    assert last_member_is_complete(corrupted) is False


def test_garbage_and_empty():
    assert last_member_is_complete(b"not gzip at all") is False
    assert last_member_is_complete(b"") is True        # nothing to cut
    assert list(iter_members_in_order(b"")) == []


def test_magic_inside_deflate_data_is_complete_but_the_old_split_said_cut():
    """The critic's reproduction (false_magic2.py): a healthy member whose
    compressed bytes contain 1f 8b 08. The old judgment (split on the magic,
    decode the last piece) calls it cut; the in-order walk does not."""
    text, member = member_with_inner_magic(_random_rows, 888)
    data = _member("header\n") + member
    assert gzip.decompress(data).decode() == "header\n" + text     # healthy
    assert last_member_is_complete(data) is True
    assert [m.payload for m in iter_members_in_order(data)] == \
        [b"header\n", text.encode()]
    # the first version's judgment on the same bytes
    assert decompress_piece(split_raw_members(data)[-1]).complete is False


def test_magic_in_the_trailer_is_complete_but_the_old_split_said_cut():
    """ISIZE (length mod 2^32, little-endian) = 0x00088B1F puts 1f 8b 08 00 in
    the last four bytes of a healthy member."""
    member = gzip.compress(b"y" * ISIZE_MAGIC_LEN)
    assert member[-4:] == b"\x1f\x8b\x08\x00"
    data = _member("header\n") + member
    assert last_member_is_complete(data) is True
    assert decompress_piece(split_raw_members(data)[-1]).complete is False

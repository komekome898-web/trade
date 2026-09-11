"""Recovering JSONL rows from a gzip file with a corrupted member boundary.

Background (2026-09-11/12, L-121): `scripts/record_liquidations.py`'s old
`Writer` kept a single gzip member open (`gzip.open(path, "at")`) for the
whole recording session. A hard kill (`deploy\\stop_all.bat`'s
`Stop-Process -Force`, or a crash) leaves that member's deflate stream with
no end-of-stream trailer. The restarted process then calls
`gzip.open(path, "at")` again, which appends a BRAND NEW member's header
right after the dead member's last (mid-block) byte — there is no separator
between them on disk.

That shape breaks a plain `gzip.open(...).read()` in a way that is worse
than a simple truncation: the decompressor decodes the dead member's tail
correctly and then walks straight into the new member's header bytes as if
they were more deflate bits, which — per zlib's C decoder — typically ends
in `zlib.error: Error -3 while decompressing data: invalid block type`
(occasionally `gzip.BadGzipFile` if the corruption lands on a fresh
member's own header instead). And because `zlib.decompressobj.decompress()`
raises before returning anything for the call that hit the bad bytes, the
already-decoded bytes of the dead member are LOST from that call — this is
the same mechanism behind the 2026-09-09 incident documented in
`src/bot/research/liquidations.py` ("11.6KB file read as 0 lines").

The fix here is to never hand a decompressor bytes from two different
members in one call. `split_raw_members` finds every member's start
offset by scanning the RAW (still-compressed) bytes for the gzip+deflate
magic (`\\x1f\\x8b\\x08`) BEFORE decompressing anything, then slices the
file at those offsets. Each resulting piece is exactly one member's own
bytes (plus, for a dead member, whatever mid-block garbage follows up to
the next member's header — but that garbage is never fed to the decoder,
because the piece boundary already excludes it: the dead member's piece
ends exactly where the next member's header begins). Decompressing a piece
that lacks its own trailer then simply runs out of input — no exception,
just a partial result — instead of decoding into another member's header.

A 3-byte magic match can in principle occur by chance inside genuinely
compressed data (~1/2^24 per byte offset); for this project's file sizes
(single-digit MB at most) that is not a realistic concern, and a false
split only produces one extra piece that `decompress_piece` reports as
unreadable — it never loses a correctly-split neighbor's data.

Used by `scripts/repair_liquidation_gz.py` (read-only recovery to a
separate output directory) and by `scripts/intake_ledger.py`'s
`scan_jsonl` fallback (so a boundary-corrupted file is inventoried with a
recovered row count instead of just failing the scan).
"""
from __future__ import annotations

import json
import zlib
from dataclasses import dataclass, field

GZIP_MAGIC3 = b"\x1f\x8b\x08"          # ID1 ID2 CM=deflate
GZIP_WBITS = zlib.MAX_WBITS | 16       # auto-detect the gzip header/trailer
READ_CHUNK = 1 << 20                   # 1 MiB of compressed input per decompress() call


def find_member_offsets(data: bytes) -> list[int]:
    """Byte offsets of every occurrence of the gzip+deflate magic in `data`,
    scanning the raw (compressed) bytes — no decompression happens here."""
    offsets = []
    start = 0
    while True:
        i = data.find(GZIP_MAGIC3, start)
        if i == -1:
            break
        offsets.append(i)
        start = i + 1
    return offsets


def split_raw_members(data: bytes) -> list[bytes]:
    """Slice `data` into one piece per gzip member, using only the raw magic
    offsets (see module docstring for why this must happen before any
    decompression). If there is no magic at offset 0 (garbage prefix, or no
    magic at all), the whole blob is returned as a single piece and left for
    `decompress_piece` to report as unreadable — this function never raises."""
    if not data:
        return []
    offsets = find_member_offsets(data)
    if not offsets or offsets[0] != 0:
        return [data]
    pieces = []
    for i, off in enumerate(offsets):
        end = offsets[i + 1] if i + 1 < len(offsets) else len(data)
        pieces.append(data[off:end])
    return pieces


@dataclass
class MemberResult:
    decompressed: bytes
    complete: bool                     # reached a valid end-of-stream trailer
    error: str | None = None           # set only if decoding failed outright


def decompress_piece(piece: bytes) -> MemberResult:
    """Decompress one already-isolated member's bytes, tolerating a missing
    trailer (a dead member simply runs out of input: no exception, `complete`
    stays False). Feeds the decompressor in READ_CHUNK-sized calls rather
    than the whole piece at once, so if something still goes wrong mid-piece
    (e.g. a false-positive magic split landed inside real compressed data)
    only that chunk's output is lost, not the whole piece."""
    dec = zlib.decompressobj(GZIP_WBITS)
    out = bytearray()
    pos = 0
    try:
        while pos < len(piece):
            chunk = piece[pos:pos + READ_CHUNK]
            out += dec.decompress(chunk)
            pos += len(chunk)
            if dec.eof:
                break
    except zlib.error as exc:
        return MemberResult(decompressed=bytes(out), complete=False, error=str(exc))
    complete = dec.eof
    if complete:
        try:
            out += dec.flush()
        except zlib.error:
            pass  # trailer bytes malformed — keep what we already have
    return MemberResult(decompressed=bytes(out), complete=complete)


@dataclass
class RecoveredLines:
    lines: list[str] = field(default_factory=list)   # raw JSON-object line text, in order
    members_found: int = 0
    members_complete: int = 0
    lines_discarded: int = 0            # non-JSON fragments dropped (not counted as rows)


def recover_json_lines(data: bytes) -> RecoveredLines:
    """Recover as many valid JSONL rows as possible from a gzip file with an
    unknown number of members, some of which may lack their trailer or be
    followed by another member's header with no separator. Only lines that
    parse as a JSON *object* are kept; anything else (a half-written last
    line, a header fragment misread as text) is discarded and counted, never
    raised or silently merged into a neighboring line."""
    result = RecoveredLines()
    for piece in split_raw_members(data):
        result.members_found += 1
        member = decompress_piece(piece)
        if member.complete:
            result.members_complete += 1
        text = member.decompressed.decode("utf-8", errors="replace")
        for line in text.split("\n"):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                result.lines_discarded += 1
                continue
            if not isinstance(obj, dict):
                result.lines_discarded += 1
                continue
            result.lines.append(line)
    return result


def is_cleanly_readable(data: bytes) -> bool:
    """True iff a plain `gzip.decompress`-equivalent read of the whole blob
    succeeds end to end (i.e. the file needs no recovery at all). Read-only:
    only decompresses in memory, never touches disk."""
    import gzip
    import io
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(data), mode="rb") as f:
            while f.read(1 << 20):
                pass
        return True
    except Exception:  # noqa: BLE001 - any failure means "not cleanly readable"
        return False

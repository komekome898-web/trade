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

**A 3-byte magic match DOES occur by chance inside healthy members, at
this project's file sizes** (corrected 2026-10-02; this paragraph used to
say it was "not a realistic concern"). Treating compressed bytes as
uniform random bytes, each byte offset matches with p = 2^-24 (about
6.0e-8), so a blob of N bytes holds about N * 2^-24 chance matches, and
P(at least one) = 1 - exp(-N * 2^-24):
    N = 1 MiB     -> 0.0625 expected, P = 6.1 %
    N = 4.25 MB   -> 0.253  expected, P = 22 %  (one Hyperliquid
                     leaderboard member, scripts/record_hyperliquid.py)
    N = 5.44 MB   -> 0.324  expected, P = 28 %  (a day of Deribit option
                     books, scripts/record_deribit_oi.py)
    a 28 KB member checked 96 times a day -> 0.16 per day (about one
                     day in six)
The gzip trailer can carry the bytes too: ISIZE (uncompressed length mod
2^32, little-endian) starts with 1f 8b 08 whenever that length mod 2^24 is
0x088B1F. The second-round critic of 2026-10-02 reproduced it on real
shapes (`docs/AUDITOR/VERDICTS/2026-10-02_W2_recorders.md`).
What a false split costs: `split_raw_members` cuts the member there, the
first piece decodes up to the false offset and is reported incomplete, the
second piece is reported unreadable — so `recover_json_lines` loses the
rest of that one member, and a reader that treats "a piece other than the
last did not end" as corruption reports a healthy file as corrupted.
**Never use the magic split to decide whether a file is whole** (whether
it may be appended to, renamed, or trusted): use `last_member_is_complete`
/ `iter_members_in_order` below, which find every boundary where zlib
itself says the member ended (`unused_data`), so a byte pattern inside a
member can never be taken for a boundary. The magic split stays only for
RECOVERING rows from a file that is already broken mid-way.

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


# ---------------------------------------------------------------------------
# Reading members IN ORDER (2026-10-02). This is the only safe way to decide
# whether a file ends with a whole member (see the module docstring on why
# the raw magic split must not decide it).
# ---------------------------------------------------------------------------

OUT_CHUNK = 8 << 20                    # cap on decompressed bytes per call


@dataclass
class OrderedMember:
    start: int                         # byte offset of the member's header
    end: int                           # offset just past its trailer; len(data) if it did not end
    complete: bool                     # zlib reached this member's end-of-stream
    payload: bytes | None = None       # decompressed bytes (None when keep_payload=False)
    error: str | None = None           # set when zlib raised on this member


def iter_members_in_order(data: bytes, keep_payload: bool = True):
    """Yield the gzip members of `data` from offset 0, one after another.

    Each member is decoded by its own `zlib.decompressobj`; where that
    decoder says the member ended, the bytes it did not consume
    (`unused_data`) are where the next member starts. No byte pattern is
    searched for, so 1f 8b 08 occurring inside compressed data (or in a
    trailer) is never mistaken for a boundary.

    The walk stops after the first member that does not end — cut by a kill
    mid-write, stray bytes after the last whole member, or bytes zlib
    rejects (`error` set). That member is yielded with complete=False and
    end=len(data); nothing after it is read, because without its end there
    is no reliable place where the next member starts.

    keep_payload=False discards the decompressed bytes as they come (memory
    stays bounded by OUT_CHUNK even for large files)."""
    n = len(data)
    pos = 0
    while pos < n:
        dec = zlib.decompressobj(GZIP_WBITS)
        out = bytearray() if keep_payload else None
        cur = pos
        error = None
        try:
            while cur < n and not dec.eof:
                buf = data[cur:cur + READ_CHUNK]
                cur += len(buf)
                while True:
                    piece = dec.decompress(buf, OUT_CHUNK)
                    if out is not None:
                        out += piece
                    buf = dec.unconsumed_tail
                    if dec.eof or not buf:
                        break
                if dec.eof:
                    # At the member's end zlib reports the input it did not
                    # use in unused_data (unconsumed_tail then repeats the
                    # same bytes, so it must not be subtracted as well).
                    cur -= len(dec.unused_data)
        except zlib.error as exc:
            error = str(exc)
        payload = bytes(out) if out is not None else None
        if error is None and dec.eof:
            yield OrderedMember(start=pos, end=cur, complete=True, payload=payload)
            pos = cur
            continue
        yield OrderedMember(start=pos, end=n, complete=False, payload=payload,
                            error=error)
        return


def last_member_is_complete(data: bytes) -> bool:
    """True iff `data` can be read member by member from its start to its
    very last byte and the last member reached its end — i.e. appending a
    new member after it keeps the file readable by any plain gzip reader.

    False when a member was cut (a kill mid-write), when anything that is
    not a whole member follows the last whole member, or when zlib rejects
    a member on the way (the walk cannot get past it). Empty data is True
    (there is nothing to cut). Read-only: decodes in memory and discards the
    output."""
    last = None
    for member in iter_members_in_order(data, keep_payload=False):
        last = member
    return last is None or last.complete

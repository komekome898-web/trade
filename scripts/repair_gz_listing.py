#!/usr/bin/env python3
"""READ-ONLY diagnostic: list every *.gz under data/ws with its gzip member
count, whether the last member is complete, and how many decompressed bytes
are still recoverable from it.

Why this exists: an owner-PC ledger found 33 of 73 data/ws recordings are
gzip files without an end-of-stream marker on their last member — the old
recorder (src/bot/market_data/realtime.py) opened gzip.open(path, "at") and
kept that single member open for the whole session, so a hard kill
(stop_all.bat's taskkill /F / Stop-Process -Force, which give no chance to
close the file) always truncated it. The recorder now buffers and flushes
complete members periodically (see realtime.py's module docstring), which
bounds future data loss to the last unflushed buffer — but it does nothing
for the 33 files already on disk. This script answers "what do they still
have in them" without touching any of them, so the owner can decide whether
extract_tape.py / a bespoke recovery pass is worth running.

This script NEVER opens a data file for writing, never moves or deletes
anything under data/, and never rewrites a truncated .gz "clean" — that
would need a real repair tool, which does not exist yet by design (the
lead/owner decides if and how to recover the 33 files; this is read-only
reconnaissance for that decision).

How member/truncation detection works: gzip's own `gzip` module transparently
concatenates all members of a multi-member file when reading, so it cannot
report a per-member breakdown. This script instead walks the raw bytes
itself with `zlib.decompressobj(16 + zlib.MAX_WBITS)` (the "auto-detect
gzip header" wbits value), one member at a time: for each member it feeds
compressed bytes until the decompressor reports `eof` (a valid end-of-stream
marker was found) or the file runs out first (truncated). `unused_data`
after a complete member is exactly where the next member starts, so no
byte-offset guessing or magic-number scanning through compressed data is
needed for the boundary itself — only the very first byte of each member is
checked against the gzip magic (0x1f 0x8b) as a sanity check.

Usage:
    python scripts/repair_gz_listing.py                  # table to stdout
    python scripts/repair_gz_listing.py --root data/ws
    python scripts/repair_gz_listing.py --json out.json  # also write JSON
                                                           # (must NOT be
                                                           # under data/)
"""
from __future__ import annotations

import argparse
import json
import sys
import zlib
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = REPO_ROOT / "data" / "ws"

GZIP_MAGIC = b"\x1f\x8b"
READ_CHUNK = 1 << 20  # 1 MiB of compressed input per decompress() call


def analyze_gz(path: Path) -> dict[str, Any]:
    """Read-only walk of one .gz file's members. Never opens the file for
    writing. Returns a dict; on any read error the 'error' field is set and
    whatever was determined before the error is still returned."""
    rec: dict[str, Any] = {
        "path": str(path),
        "bytes": None,
        "members": 0,
        "complete_members": 0,
        "last_member_complete": None,
        "recoverable_bytes": 0,
        "error": None,
    }
    try:
        rec["bytes"] = path.stat().st_size
    except OSError as exc:
        rec["error"] = f"stat failed: {exc}"
        return rec

    try:
        with open(path, "rb") as raw:  # read-only handle
            while True:
                pos_before = raw.tell()
                magic = raw.read(2)
                if not magic:
                    break  # clean end: no more members, nothing dangling
                if magic != GZIP_MAGIC:
                    rec["error"] = (f"unexpected bytes at offset {pos_before} "
                                    f"(not a gzip member header)")
                    break
                raw.seek(pos_before)
                rec["members"] += 1
                complete = _consume_one_member(raw, rec)
                rec["last_member_complete"] = complete
                if not complete:
                    break  # trailing incomplete member — nothing follows it
    except OSError as exc:
        rec["error"] = f"read failed: {exc}"
    return rec


def _consume_one_member(raw, rec: dict[str, Any]) -> bool:
    """Feed one gzip member's bytes through a fresh decompressor. Advances
    `raw` to just past this member (leaving the file positioned at the next
    member's header) and returns True iff a complete end-of-stream marker
    was found. Tallies decompressed bytes into rec['recoverable_bytes'] as
    they are produced — including bytes from an incomplete final member,
    since deflate output is valid up to the point of truncation."""
    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    while True:
        chunk = raw.read(READ_CHUNK)
        if not chunk:
            return False  # file ended before this member's trailer
        try:
            out = decompressor.decompress(chunk)
        except zlib.error as exc:
            rec["error"] = f"zlib error in member {rec['members']}: {exc}"
            return False
        rec["recoverable_bytes"] += len(out)
        if decompressor.eof:
            rec["complete_members"] += 1
            raw.seek(raw.tell() - len(decompressor.unused_data))
            return True


def iter_gz_files(root: Path):
    for p in sorted(root.rglob("*.gz")):
        if p.is_file():
            yield p


def build_report(root: Path) -> list[dict[str, Any]]:
    return [analyze_gz(p) for p in iter_gz_files(root)]


def print_table(report: list[dict[str, Any]]) -> None:
    headers = ["file", "bytes", "members", "complete", "last_ok", "recoverable_bytes"]
    rows = []
    for rec in report:
        rows.append([
            Path(rec["path"]).name,
            str(rec["bytes"]) if rec["bytes"] is not None else "?",
            str(rec["members"]),
            str(rec["complete_members"]),
            "yes" if rec["last_member_complete"] else "NO" if rec["last_member_complete"] is False else "?",
            str(rec["recoverable_bytes"]),
        ])
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt(cells):
        return "  ".join(c.ljust(widths[i]) for i, c in enumerate(cells))

    print(fmt(headers))
    print(fmt(["-" * w for w in widths]))
    for row in rows:
        print(fmt(row))

    truncated = [r for r in report if r["last_member_complete"] is False]
    total_recoverable = sum(r["recoverable_bytes"] for r in report)
    print()
    print(f"{len(report)} files scanned, {len(truncated)} with a truncated "
          f"last member, {total_recoverable} decompressed bytes recoverable in total")
    for r in truncated:
        if r["error"]:
            print(f"  {Path(r['path']).name}: {r['error']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(DEFAULT_ROOT),
                    help="directory to scan for *.gz (default: data/ws)")
    ap.add_argument("--json", default=None,
                    help="optional path to also write the full report as JSON "
                         "(must not be under data/ — this tool is read-only "
                         "with respect to recorded data)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"repair_gz_listing: {root} does not exist", file=sys.stderr)
        return 1

    report = build_report(root)
    print_table(report)

    if args.json:
        json_path = Path(args.json).resolve()
        data_dir = (REPO_ROOT / "data").resolve()
        if data_dir == json_path or data_dir in json_path.parents:
            print("repair_gz_listing: refusing to write the report under data/ "
                  "— this tool never writes recorded data", file=sys.stderr)
            return 1
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, sort_keys=True)
        print(f"wrote {json_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

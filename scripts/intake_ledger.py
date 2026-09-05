#!/usr/bin/env python3
"""Intake ledger: a persistent, append-only inventory of every data file this
project holds (`data/`, `paper_logs/`, `backtest_data/`, `data/archive/` if
present).

Why this exists: `docs/DATA_GOVERNANCE_PLAN.md` — a research checkout has
read a stale local copy while a newer shared copy existed, a 210-day claim
turned out to rest on a 21-day overlap, and file counts/row counts have been
asserted from memory instead of measured. The ledger is the single place
those numbers come from ("台帳が数字の唯一の出所"): a report should quote
`data/INTAKE_latest.json`, not recompute anything by hand.

Design:
  - `data/INTAKE.jsonl` is an APPEND-ONLY history: one line per (path, run)
    whenever that path is new, its content changed (size/mtime/md5), or its
    present/missing status flipped. Unchanged files do not grow the log on
    every run.
  - `data/INTAKE_latest.json` is a materialized index keyed by path, always
    rewritten in full from the current scan — the fast thing to read.
  - A file that disappears is NEVER dropped: its last known record is kept
    with status "missing" (see the DATA_GOVERNANCE_PLAN self-report about a
    prior local-copy mixup — the ledger must make disappearance visible, not
    silently drop the row).
  - Nothing under the scanned roots is ever opened for writing, moved, or
    deleted by this script.

Performance: for ~2GB of mixed csv/csv.gz/jsonl/jsonl.gz, unchanged files
(same size+mtime as the previous ledger entry) are NOT re-hashed or re-
scanned on a re-run — only new/changed files pay that cost. gz files are
streamed (never fully decompressed to disk or to a giant in-memory string).
Row counts are always exact (a single streaming pass); by default, only the
first/last 2000 rows of a tabular file are inspected to find a parseable
timestamp (`--full` removes that cap and inspects every row) — this bounds
the cost of timestamp parsing, which is the slow part, not the linecount.

Usage:
    python scripts/intake_ledger.py                 # scan + update ledger
    python scripts/intake_ledger.py --full           # force full re-scan
    python scripts/intake_ledger.py --summary        # + print a table
    python scripts/intake_ledger.py --root /path     # scan a different tree
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import re
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]

ROOT_NAMES = ["data", "paper_logs", "backtest_data", "data/archive"]

# Ledger's own output files live under data/ — never treat them as data.
SELF_FILES = {"data/INTAKE.jsonl", "data/INTAKE_latest.json", "data/QUALITY.json"}

SKIP_DIR_NAMES = {"__pycache__", ".git"}

TS_CANDIDATES = ["ts", "ts_utc", "timestamp", "date", "open_time", "exec_date"]

DEFAULT_TS_CAP = 2000

HASH_CHUNK = 1024 * 1024

ACTIVE_WINDOW_SEC = 600  # files modified in the last 10 min are treated as being written
ACTIVE_MIN_BYTES = 5 * 1024 * 1024  # ...but only when large enough for re-hashing to cost anything


# --------------------------------------------------------------------------
# timestamp parsing (tolerant)
# --------------------------------------------------------------------------

_YYYYMMDD_RE = re.compile(r"^\d{8}$")


def parse_ts(raw: Any) -> Optional[datetime]:
    """Best-effort tolerant timestamp parse. Returns None, never raises."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s.lower() in ("nan", "none", "null", ""):
        return None

    if _YYYYMMDD_RE.match(s):
        try:
            return datetime.strptime(s, "%Y%m%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    try:
        f = float(s)
    except ValueError:
        f = None
    if f is not None:
        try:
            if abs(f) >= 1e12:  # epoch millis
                return datetime.fromtimestamp(f / 1000.0, tz=timezone.utc)
            if abs(f) >= 1e8:  # epoch seconds
                return datetime.fromtimestamp(f, tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            return None
        # small numbers are not plausible timestamps; fall through to string
        # parsing only if it also has non-numeric structure (it won't), so
        # give up on this value.
        return None

    iso = s[:-1] + "+00:00" if s.endswith("Z") else s
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def find_ts_column(header: list[str]) -> Optional[int]:
    lower = [h.strip().lower() for h in header]
    for cand in TS_CANDIDATES:
        if cand in lower:
            return lower.index(cand)
    return None


def find_ts_key(obj: dict) -> Optional[str]:
    keys_lower = {k.lower(): k for k in obj.keys()}
    for cand in TS_CANDIDATES:
        if cand in keys_lower:
            return keys_lower[cand]
    return None


# --------------------------------------------------------------------------
# file classification / IO helpers
# --------------------------------------------------------------------------


def tabular_kind(name: str) -> Optional[tuple[str, bool]]:
    lower = name.lower()
    if lower.endswith(".csv.gz"):
        return ("csv", True)
    if lower.endswith(".csv"):
        return ("csv", False)
    if lower.endswith(".jsonl.gz"):
        return ("jsonl", True)
    if lower.endswith(".jsonl"):
        return ("jsonl", False)
    return None


def open_text(path: Path, gz: bool):
    if gz:
        return gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="")
    return open(path, "rt", encoding="utf-8", errors="replace", newline="")


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(HASH_CHUNK)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _first_parseable(values) -> Optional[str]:
    for v in values:
        dt = parse_ts(v)
        if dt is not None:
            return dt.isoformat()
    return None


def _last_parseable(values) -> Optional[str]:
    for v in reversed(list(values)):
        dt = parse_ts(v)
        if dt is not None:
            return dt.isoformat()
    return None


def scan_csv(path: Path, gz: bool, cap: Optional[int]):
    """Returns (row_count, first_ts, last_ts, truncated). A gzip member
    without its end-of-stream marker (live WS recorder, or a cut-off
    transfer) raises EOFError partway through the `for row in reader` loop
    — everything read before that point is still valid data, so it is kept
    and returned (truncated=True) rather than discarded."""
    row_count = 0
    ts_col = None
    truncated = False
    head_vals: list[str] = []
    tail_vals = deque(maxlen=cap) if cap else []
    with open_text(path, gz) as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return 0, None, None, False
        except EOFError:
            return 0, None, None, True
        ts_col = find_ts_column(header)
        try:
            for row in reader:
                row_count += 1
                if ts_col is not None and ts_col < len(row):
                    val = row[ts_col]
                    if cap is None or len(head_vals) < cap:
                        head_vals.append(val)
                    tail_vals.append(val)
        except EOFError:
            truncated = True  # partial read kept — see docstring
    if ts_col is None:
        return row_count, None, None, truncated
    return row_count, _first_parseable(head_vals), _last_parseable(tail_vals), truncated


def scan_jsonl(path: Path, gz: bool, cap: Optional[int]):
    """Returns (row_count, first_ts, last_ts, truncated). See scan_csv's
    docstring on EOFError from a truncated gzip member: rows read so far
    are kept and truncated=True is reported rather than raising."""
    row_count = 0
    ts_key: Optional[str] = None
    ts_key_resolved = False
    truncated = False
    head_vals: list[Any] = []
    tail_vals = deque(maxlen=cap) if cap else []
    with open_text(path, gz) as f:
        try:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row_count += 1
                try:
                    obj = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if not isinstance(obj, dict):
                    continue
                if not ts_key_resolved:
                    ts_key = find_ts_key(obj)
                    ts_key_resolved = True
                if ts_key is not None and ts_key in obj:
                    val = obj[ts_key]
                    if cap is None or len(head_vals) < cap:
                        head_vals.append(val)
                    tail_vals.append(val)
        except EOFError:
            truncated = True  # partial read kept — see docstring
    if ts_key is None:
        return row_count, None, None, truncated
    return row_count, _first_parseable(head_vals), _last_parseable(tail_vals), truncated


# --------------------------------------------------------------------------
# scanning
# --------------------------------------------------------------------------


def discover_roots(root: Path) -> list[Path]:
    candidates = []
    for name in ROOT_NAMES:
        p = (root / name).resolve()
        if p.exists():
            candidates.append(p)
    # de-dup: drop any candidate nested inside another candidate.
    kept = []
    for c in candidates:
        if any(c != other and other in c.parents for other in candidates):
            continue
        kept.append(c)
    return kept


def iter_files(root: Path):
    for r in discover_roots(root):
        for p in sorted(r.rglob("*")):
            if not p.is_file():
                continue
            if any(part in SKIP_DIR_NAMES for part in p.parts):
                continue
            rel = p.relative_to(root).as_posix()
            if rel in SELF_FILES:
                continue
            yield rel, p


def scan_one(rel: str, p: Path, cap: Optional[int]) -> dict:
    stat = p.stat()
    rec: dict[str, Any] = {
        "path": rel,
        "status": "present",
        "bytes": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "md5": md5_of(p),
        "row_count": None,
        "first_ts": None,
        "last_ts": None,
    }
    kind = tabular_kind(p.name)
    if kind is not None:
        fmt, gz = kind
        try:
            if fmt == "csv":
                row_count, first_ts, last_ts, truncated = scan_csv(p, gz, cap)
            else:
                row_count, first_ts, last_ts, truncated = scan_jsonl(p, gz, cap)
            rec["row_count"] = row_count
            rec["first_ts"] = first_ts
            rec["last_ts"] = last_ts
            if truncated:
                # A gzip member without its end-of-stream marker: the file
                # is still being written (live WS recorder) or was cut off.
                # scan_csv/scan_jsonl already kept the partial counts read
                # before the cutoff — just flag the row, never abort the
                # ledger and never drop what was read.
                rec["scan_error"] = "EOFError (truncated/in-progress gzip): partial read kept"
                rec["truncated"] = True
        except EOFError as exc:
            # Defense in depth: something raised EOFError outside the
            # scan_csv/scan_jsonl read loops (e.g. while opening). No
            # partial counts are available in that case.
            rec["scan_error"] = f"EOFError (truncated/in-progress gzip): {exc}"
            rec["truncated"] = True
        except (OSError, gzip.BadGzipFile, csv.Error) as exc:
            rec["scan_error"] = f"{type(exc).__name__}: {exc}"
    return rec


def content_key(rec: dict) -> tuple:
    return (rec.get("bytes"), rec.get("mtime"), rec.get("md5"))


def load_latest(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def run(root: Path, full: bool, ledger_path: Path, latest_path: Path) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    cap = None if full else DEFAULT_TS_CAP

    prev_index = load_latest(latest_path)
    new_index: dict[str, dict] = {}
    appended: list[dict] = []

    seen_paths: set[str] = set()
    for rel, p in iter_files(root):
        seen_paths.add(rel)
        prev = prev_index.get(rel)
        stat = p.stat()
        cheap_bytes = stat.st_size
        cheap_mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

        unchanged = (
            not full
            and prev is not None
            and prev.get("status") == "present"
            and prev.get("bytes") == cheap_bytes
            and prev.get("mtime") == cheap_mtime
        )

        # A file modified within the last ACTIVE_WINDOW_SEC is being written
        # right now (live WS recorder, growing tape): it has no stable hash
        # and re-hashing a growing 100MB+ file on every run is pure cost.
        # Record it as in-progress (path/bytes/mtime only); it is hashed and
        # counted on the first run after it stops changing.
        active = (cheap_bytes >= ACTIVE_MIN_BYTES and
                  (datetime.now(timezone.utc) - datetime.fromisoformat(cheap_mtime)).total_seconds() < ACTIVE_WINDOW_SEC)
        if unchanged:
            rec = dict(prev)
            rec["status"] = "present"
        elif active:
            rec = {"path": rel, "status": "present", "bytes": cheap_bytes, "mtime": cheap_mtime,
                   "md5": None, "row_count": None, "first_ts": None, "last_ts": None,
                   "in_progress": True}
        else:
            try:
                rec = scan_one(rel, p, cap)
            except Exception as exc:  # noqa: BLE001 - one bad file must never abort the ledger
                # Record the failure as a row (path, bytes/mtime if available,
                # error text) and keep going: the ledger's job is to list what
                # exists, and a listing that dies on one file lists nothing.
                rec = {"path": rel, "status": "present", "bytes": cheap_bytes, "mtime": cheap_mtime,
                       "md5": None, "row_count": None, "first_ts": None, "last_ts": None,
                       "scan_error": f"{type(exc).__name__}: {exc}"}
                print(f"intake_ledger: scan failed for {rel}: {rec['scan_error']}", file=sys.stderr)

        rec["first_seen"] = prev.get("first_seen") if prev else now
        if rec["first_seen"] is None:
            rec["first_seen"] = now
        rec["last_seen"] = now
        rec["checked_at"] = now
        new_index[rel] = rec

        changed = prev is None or content_key(prev) != content_key(rec) or (
            prev.get("status") != "present"
        )
        if changed:
            appended.append(rec)

    # files previously seen but not found on disk this run -> "missing"
    for rel, prev in prev_index.items():
        if rel in seen_paths:
            continue
        rec = dict(prev)
        was_present = rec.get("status") == "present"
        rec["status"] = "missing"
        rec["checked_at"] = now
        new_index[rel] = rec
        if was_present:
            appended.append(rec)

    if appended:
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with open(ledger_path, "a", encoding="utf-8") as f:
            for rec in appended:
                f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")

    latest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(new_index, f, ensure_ascii=False, sort_keys=True, indent=1)

    return new_index


# --------------------------------------------------------------------------
# summary
# --------------------------------------------------------------------------


def dataset_dir(root_name_path: str) -> str:
    parts = root_name_path.split("/")
    if len(parts) <= 2:
        return parts[0]
    return "/".join(parts[:2])


def print_summary(index: dict) -> None:
    groups: dict[str, dict] = {}
    for rel, rec in index.items():
        key = dataset_dir(rel)
        g = groups.setdefault(
            key,
            {"files": 0, "bytes": 0, "rows": 0, "missing": 0, "first_ts": None, "last_ts": None},
        )
        g["files"] += 1
        if rec.get("status") == "missing":
            g["missing"] += 1
        else:
            g["bytes"] += rec.get("bytes") or 0
        rows = rec.get("row_count")
        if rows:
            g["rows"] += rows
        for k, agg in (("first_ts", min), ("last_ts", max)):
            v = rec.get(k)
            if v is None:
                continue
            cur = g[k]
            g[k] = v if cur is None else agg(cur, v)

    headers = ["dataset", "files", "bytes", "rows", "span", "missing"]
    rows_out = []
    for key in sorted(groups):
        g = groups[key]
        span = "-"
        if g["first_ts"] or g["last_ts"]:
            span = f"{g['first_ts'] or '?'} .. {g['last_ts'] or '?'}"
        rows_out.append(
            [key, str(g["files"]), str(g["bytes"]), str(g["rows"]), span, str(g["missing"])]
        )

    widths = [len(h) for h in headers]
    for row in rows_out:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt_row(cells):
        return "  ".join(c.ljust(widths[i]) for i, c in enumerate(cells))

    print(fmt_row(headers))
    print(fmt_row(["-" * w for w in widths]))
    for row in rows_out:
        print(fmt_row(row))

    total_files = sum(g["files"] for g in groups.values())
    total_bytes = sum(g["bytes"] for g in groups.values())
    total_rows = sum(g["rows"] for g in groups.values())
    total_missing = sum(g["missing"] for g in groups.values())
    print(fmt_row(["-" * w for w in widths]))
    print(
        fmt_row(
            ["TOTAL", str(total_files), str(total_bytes), str(total_rows), "", str(total_missing)]
        )
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(REPO_ROOT), help="repo root to scan (default: this repo)")
    ap.add_argument("--full", action="store_true", help="force full re-scan (no mtime/size skip, no timestamp cap)")
    ap.add_argument("--summary", action="store_true", help="print a per-dataset summary table")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    ledger_path = root / "data" / "INTAKE.jsonl"
    latest_path = root / "data" / "INTAKE_latest.json"

    index = run(root, args.full, ledger_path, latest_path)

    present = sum(1 for r in index.values() if r.get("status") == "present")
    missing = sum(1 for r in index.values() if r.get("status") == "missing")
    print(f"intake_ledger: {present} present, {missing} missing, index -> {latest_path}")

    if args.summary:
        print()
        print_summary(index)

    return 0


if __name__ == "__main__":
    sys.exit(main())

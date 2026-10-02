#!/usr/bin/env python3
"""Record Deribit option open interest per instrument (= per strike and
expiry) forward, one snapshot per run.

Why this exists: Deribit's public API serves the per-instrument open interest
only as a current value (public/get_book_summary_by_currency, kind=option).
The history host answers 400 for that method, so a strike-by-strike open
interest history can only exist if it is recorded forward from today
(docs/DISCUSSIONS/2026-10-01_research_structure_intake_and_combiner.md
sec 5-1B, class C; owner L-039: "取れる時に取れるだけ取る").

Read-only public endpoint, no key, no order endpoint.

Output (data/deribit_options/, per UTC day of the receive time, gzip CSV;
each currency's snapshot is appended as one complete gzip member -- see the
"gzip files" comment below for what a kill mid-write leaves):
    book_YYYYMMDD.csv.gz   one row per option instrument per snapshot.
        ts_recv_utc   when this script received the response (ISO-8601 UTC)
        us_out        Deribit's own response time (microseconds, "usOut")
        currency      BTC / ETH
        + every field of the book summary as Deribit names it
          (BOOK_FIELDS below; instrument_name carries expiry/strike/type,
          left unparsed so nothing is reinterpreted here)
    errors_YYYYMMDD.csv.gz  ts_recv_utc, source, target, error -- one row per
        failed call. A failed currency never stops the other currency.
    <name>_YYYYMMDD.truncN.csv.gz  a day file that did not end with a whole
        gzip member when this script was about to append to it (a kill hit
        a write), renamed whole -- see "gzip files" below. Its members up to
        the cut read normally (bot.research.gz_members.iter_members_in_order).

No duplicate rows: a snapshot is keyed by (currency, us_out), and within
one response an instrument_name that appears twice is written once. Nothing
is restored from earlier files: each run is a new process that makes one
call per currency, and us_out is Deribit's own response time in
microseconds, so two runs never get the same key. (The first version read
yesterday's and today's book files back at every start to restore keys
that could never match -- about 2 s and 440 MB per run by the end of a day,
2026-10-02 critic; removed.)

What a run costs besides the two calls (measured in the research
environment on 2026-10-02 with the two real responses the critic saved --
BTC 990 and ETH 832 instruments -- written 96 times into one day file of
5.44 MB / 192 members, i.e. the end of a day): one more run took 0.19-0.21 s
without the network, of which checking that the book file ends with a whole
member (see "gzip files") was 0.11-0.12 s; peak memory 39.5 MB.

Writing: each currency is appended as soon as it arrives. A failed append
(e.g. the file held open by another program) is logged and written to
errors_*, its rows are tried once more at the end of the run, and whatever
is still unwritten then is lost with the process: the run exits with code 1
and logs how many rows. The next run (15 minutes later in fetch_all.bat)
takes a new snapshot; it does not carry the lost rows over.

One process per output directory: the lock file data/deribit_options.lock
(<out-dir>.lock) makes a second run exit with code 3 instead of appending
to the same files.

Usage:
    python scripts/record_deribit_oi.py                 # BTC and ETH, one snapshot
    python scripts/record_deribit_oi.py --currencies BTC
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import os
import sys
import threading
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "data" / "deribit_options"
LOG_TAG = "record_deribit_oi"
DERIBIT = "https://www.deribit.com/api/v2/public"
TIMEOUT = 20.0
UA = {"User-Agent": "trade-research/1.0 (research use)"}

# BTC is the project's instrument; ETH is the same call and was measured at
# 830 instruments / 31 KB gzipped per snapshot (2026-10-02), so it is taken
# too (owner L-039).
DEFAULT_CURRENCIES = ("BTC", "ETH")

# The 20 keys get_book_summary_by_currency returned on 2026-10-02 (probe in
# the lane report). Unknown future keys are ignored; a missing key is blank.
BOOK_FIELDS = ["instrument_name", "creation_timestamp", "open_interest",
               "volume", "volume_usd", "mark_price", "mark_iv", "mid_price",
               "bid_price", "ask_price", "last", "high", "low", "price_change",
               "underlying_price", "underlying_index", "estimated_delivery_price",
               "interest_rate", "base_currency", "quote_currency"]
FIELDS = ["ts_recv_utc", "us_out", "currency"] + BOOK_FIELDS
ERROR_FIELDS = ["ts_recv_utc", "source", "target", "error"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _day(ts_iso: str) -> str:
    return ts_iso[:10].replace("-", "")


def _cell(v: object) -> object:
    return "" if v is None else v


# ---- gzip files: written the way record_liquidations.Writer writes (L-121) --
# Never `gzip.open(path, "at")`: a kill in the middle of such a write leaves a
# member without its end, and every row appended after it becomes unreadable
# (owner PC, 2026-09-11, 10 files). Here each flush renders a file's rows into
# ONE complete member in memory (gzip.compress) and appends it with ONE
# open(path, "ab") write; the rows leave the buffer only after that write
# succeeded. Before the first append to a file in a process (and again after
# a failed write), the file is read member by member from its start
# (gz_members.last_member_is_complete). If it does not end with a whole
# member, the WHOLE file is renamed to <name>_<day>.truncN.csv.gz (N never
# overwrites an existing one) and a new file is started; nothing is cut in
# place. The member boundaries are where zlib says each member ended, never
# the bytes 1f 8b 08: those also occur inside healthy compressed data
# (2026-10-02 critic, docs/AUDITOR/VERDICTS/2026-10-02_W2_recorders.md).
sys.path.insert(0, str(ROOT / "src"))
try:
    from bot.research.gz_members import iter_members_in_order, last_member_is_complete
except Exception:  # noqa: BLE001 - recording must not stop on this
    iter_members_in_order = last_member_is_complete = None


def _log(msg: str) -> None:
    print(f"[{LOG_TAG}] {msg}", file=sys.stderr, flush=True)


def trunc_path(path: Path) -> Path:
    """<name>_<day>.truncN.csv.gz with the first N not taken yet."""
    base = path.name[:-len(".csv.gz")]
    n = 1
    while (cand := path.with_name(f"{base}.trunc{n}.csv.gz")).exists():
        n += 1
    return cand


def heal_if_needed(path: Path) -> Path | None:
    """If `path` does not end with a whole gzip member, rename the whole file
    to trunc_path(path) (returned) so the next append starts a new file.
    Same as record_liquidations.Writer._heal_if_needed: nothing is cut."""
    if not path.exists() or path.stat().st_size == 0:
        return None
    if last_member_is_complete is None:
        _log(f"WARNING: bot.research.gz_members not importable - "
             f"{path.name} is appended to without checking its end")
        return None
    try:
        whole = last_member_is_complete(path.read_bytes())
    except Exception as exc:  # noqa: BLE001 - unreadable = not whole
        _log(f"WARNING: checking {path.name} failed {type(exc).__name__}: "
             f"{str(exc)[:80]} - treated as not whole")
        whole = False
    if whole:
        return None
    moved = trunc_path(path)
    path.rename(moved)
    _log(f"{path.name} does not end with a whole gzip member (killed "
         f"mid-write?) -> renamed to {moved.name}; a new {path.name} is started")
    return moved


def read_gz_rows(path: Path) -> list[dict]:
    """Rows of the members read in order from the start, up to the first
    member that does not end (cut by a kill): its rows do not count as
    recorded, so restored dedup keys never claim them."""
    if not path.exists():
        return []
    if iter_members_in_order is None:
        rows: list[dict] = []
        try:
            with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
                rows.extend(csv.DictReader(f))
        except (EOFError, OSError, zlib.error):
            pass
        return rows
    header: list[str] | None = None
    rows = []
    for member in iter_members_in_order(path.read_bytes()):
        if not member.complete:
            break
        recs = list(csv.reader(io.StringIO(member.payload.decode("utf-8", "replace"),
                                           newline="")))
        if header is None:
            if not recs:
                return []
            header, recs = recs[0], recs[1:]
        rows.extend(dict(zip(header, r)) for r in recs if len(r) == len(header))
    return rows


class BufferedDailyGz:
    """Rows buffered per output file (name, UTC day of the row's first
    column). flush() appends each file's rows as one complete gzip member
    (the header row only when the file is new). A file whose write fails
    keeps its rows for the next flush and is checked again before it, as is
    a file whose size is no longer what this writer left; the other files
    are still written; the first error is re-raised after all were tried."""

    def __init__(self, out_dir: Path):
        self.out_dir = out_dir
        self._buf: dict[tuple[str, str], list[list]] = {}
        self._fields: dict[str, list[str]] = {}
        self._checked: set[Path] = set()
        self._size_left: dict[Path, int] = {}   # size after our last append

    def add(self, name: str, fields: list[str], row: list) -> None:
        self._fields[name] = fields
        self._buf.setdefault((name, _day(row[0])), []).append(row)

    def path(self, name: str, day: str) -> Path:
        return self.out_dir / f"{name}_{day}.csv.gz"

    def pending(self) -> int:
        return sum(len(v) for v in self._buf.values())

    def _append(self, path: Path, fields: list[str], rows: list[list]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        size = path.stat().st_size if path.exists() else 0
        if path in self._checked and size != self._size_left.get(path, size):
            # Something other than this writer changed the file since our last
            # append (cheap check, no read): check its end again.
            self._checked.discard(path)
        if path not in self._checked:
            heal_if_needed(path)
            self._checked.add(path)
        text = io.StringIO()
        w = csv.writer(text, lineterminator="\n")
        if not path.exists() or path.stat().st_size == 0:
            w.writerow(fields)
        w.writerows(rows)
        data = gzip.compress(text.getvalue().encode("utf-8"))
        try:
            with open(path, "ab") as f:
                f.write(data)
        except BaseException:
            # The write may have left part of the member behind: check the
            # end again before the next append (a cut end -> rename).
            self._checked.discard(path)
            raise
        try:      # the rows ARE written: a failing stat must not keep them
            self._size_left[path] = path.stat().st_size
        except OSError:
            self._checked.discard(path)

    def flush(self) -> int:
        n, first_exc = 0, None
        for key in sorted(self._buf):
            name, day = key
            rows = self._buf[key]
            try:
                self._append(self.path(name, day), self._fields[name], rows)
            except Exception as exc:  # noqa: BLE001 - keep rows, try the rest
                first_exc = first_exc or exc
                continue
            del self._buf[key]
            n += len(rows)
        if first_exc is not None:
            raise first_exc
        return n


# ---- one writer per output directory (record_liquidations._acquire_lock) ---
# Two processes appending to the same day file can interleave members and
# make it unreadable. The lock file <out-dir>.lock is held for the whole run
# and its time is refreshed by a background thread; a lock not refreshed for
# LOCK_STALE_SEC belongs to a dead process and is taken over. This script is
# not resident (one run per fetch_all.bat pass, seconds long), so stop_all.bat
# neither stops it nor deletes its lock; the stale bound is what frees a lock
# a killed run left behind.
LOCK_STALE_SEC = 180.0          # same values as record_liquidations.py
LOCK_BEAT_SEC = 45.0


def lock_path_for(out_dir: Path) -> Path:
    return out_dir.parent / f"{out_dir.name}.lock"


def _acquire_lock(lock_path: Path):
    """RunLock when held; False when another process holds it (do not run);
    None when the lock module cannot be imported (run without the guard,
    as record_liquidations.py does)."""
    try:
        from bot.jpx.run_lock import LockBusy, RunLock
    except Exception:  # noqa: BLE001 - recording matters more than the guard
        _log("WARNING: bot.jpx.run_lock not importable - running without "
             "the double-start guard")
        return None
    lock = RunLock(lock_path, stale_after_sec=LOCK_STALE_SEC)
    try:
        lock.acquire()
    except LockBusy as exc:
        _log(f"another process already writes here ({exc}); exiting so two "
             f"processes never append to the same file. It is another run of "
             f"this script (fetch_all.bat or a manual run), which normally ends "
             f"within seconds: run again once it has finished, or use another "
             f"--out-dir. A lock left by a killed run is taken over after "
             f"{LOCK_STALE_SEC:.0f} s.")
        return False
    return lock


class _Heartbeat:
    """Refreshes the lock's time every LOCK_BEAT_SEC until stop()."""

    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> "_Heartbeat":
        self._thread.start()
        return self

    def _run(self) -> None:
        while not self._stop.wait(LOCK_BEAT_SEC):
            try:
                self.lock_path.write_text(
                    json.dumps({"pid": os.getpid(), "ts": time.time()}),
                    encoding="utf-8")
            except Exception as exc:  # noqa: BLE001 - never stop recording
                _log(f"WARNING: refreshing the lock failed "
                     f"{type(exc).__name__}: {str(exc)[:80]}")

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)


def run_locked(out_dir: Path, body) -> int:
    """Run body() while holding <out_dir>.lock. 3 when the lock is busy."""
    lock_path = lock_path_for(out_dir)
    lock = _acquire_lock(lock_path)
    if lock is False:
        return 3
    beat = _Heartbeat(lock_path).start() if lock else None
    try:
        return body()
    finally:
        if beat is not None:
            beat.stop()
        if lock:
            lock.release()


class DeribitOiRecorder:
    def __init__(self, out_dir: str | Path = DEFAULT_OUT_DIR,
                 session: requests.Session | None = None,
                 currencies: tuple[str, ...] = DEFAULT_CURRENCIES):
        self.out_dir = Path(out_dir)
        self.session = session or requests.Session()
        self.currencies = currencies
        self.out = BufferedDailyGz(self.out_dir)
        self.seen: set[tuple[str, str]] = set()   # this process only (docstring)
        self.unwritten = 0

    def book_path(self, day: str) -> Path:
        return self.out.path("book", day)

    def error_path(self, day: str) -> Path:
        return self.out.path("errors", day)

    def _error(self, ts: str, target: str, exc: object) -> None:
        msg = f"{type(exc).__name__}: {exc}"
        _log(f"{target} FAILED: {msg}")
        self.out.add("errors", ERROR_FIELDS, [ts, "deribit", target, msg])

    def _flush(self) -> bool:
        """A failed write is logged; its rows stay buffered for the next try."""
        try:
            self.out.flush()
            return True
        except Exception as exc:  # noqa: BLE001
            self._error(_now_iso(), "write", exc)
            return False

    def fetch(self, currency: str) -> tuple[str, dict]:
        r = self.session.get(f"{DERIBIT}/get_book_summary_by_currency",
                             params={"currency": currency, "kind": "option"},
                             headers=UA, timeout=TIMEOUT)
        ts = _now_iso()
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}")
        return ts, r.json()

    def snapshot_rows(self, ts: str, currency: str, body: dict) -> list[list]:
        result = body.get("result")
        if not isinstance(result, list) or not result:
            raise RuntimeError(f"no result list (keys={sorted(body)})")
        us_out = str(body.get("usOut", ""))
        if not us_out:
            raise RuntimeError("no usOut in response")
        key = (currency, us_out)
        if key in self.seen:
            return []
        self.seen.add(key)
        rows, names = [], set()
        for item in result:
            if not isinstance(item, dict):
                continue
            name = item.get("instrument_name")
            if not name or name in names:
                continue
            names.add(name)
            rows.append([ts, us_out, currency]
                        + [_cell(item.get(k)) for k in BOOK_FIELDS])
        return rows

    def run_once(self) -> dict[str, int]:
        """Rows taken per currency (-1 = the call failed). Each currency is
        written as soon as it arrives; rows whose write failed are retried
        once at the end, and what is still unwritten is counted in
        self.unwritten (and logged)."""
        taken: dict[str, int] = {}
        for cur in self.currencies:
            ts = _now_iso()
            try:
                ts, body = self.fetch(cur)
                rows = self.snapshot_rows(ts, cur, body)
                for row in rows:
                    self.out.add("book", FIELDS, row)
                taken[cur] = len(rows)
            except Exception as exc:  # noqa: BLE001 - record and continue
                self._error(ts, f"get_book_summary_by_currency {cur}", exc)
                taken[cur] = -1
            self._flush()
        if self.out.pending():
            self._flush()
        self.unwritten = self.out.pending()
        if self.unwritten:
            _log(f"{self.unwritten} rows could not be written (see the "
                 f"write FAILED lines above)")
        return taken


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--currencies", default=",".join(DEFAULT_CURRENCIES))
    args = ap.parse_args(argv)
    out_dir = Path(args.out_dir)

    def body() -> int:
        rec = DeribitOiRecorder(out_dir=out_dir,
                                currencies=tuple(c.strip().upper()
                                                 for c in args.currencies.split(",")
                                                 if c.strip()))
        taken = rec.run_once()
        print("[record_deribit_oi] " + "  ".join(
            f"{c}={'FAILED' if n < 0 else f'+{n} rows'}" for c, n in taken.items())
            + (f"  UNWRITTEN={rec.unwritten}" if rec.unwritten else ""),
            flush=True)
        return 1 if rec.unwritten else 0
    return run_locked(out_dir, body)


if __name__ == "__main__":
    raise SystemExit(main())

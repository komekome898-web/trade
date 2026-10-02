#!/usr/bin/env python3
"""Record Hyperliquid's public leaderboard and the open positions of every
account on it, forward.

Why this exists: Hyperliquid serves an account's positions
(info clearinghouseState) only as the current value, so a history of large
accounts' positions exists only if it is recorded from today on
(docs/DISCUSSIONS/2026-10-01_research_structure_intake_and_combiner.md
sec 5-1B, class C; owner L-039 "取れる時に取れるだけ取る", L-531 "クジラ
(大口)のポジション ... 大きなウォレットの動き").

Which accounts: every address in the leaderboard Hyperliquid itself
publishes (stats-data.hyperliquid.xyz/Mainnet/leaderboard; 47,007 rows on
2026-10-02). The file is not sorted by any one column, so taking "the top N"
would need a ranking chosen here -- that is not done. All addresses are
polled, in the file's own order (an address listed twice is polled once
per sweep).

Pacing: Hyperliquid documents "REST requests share an aggregated weight
limit of 1200 per minute" per IP, and clearinghouseState has weight 2
(hyperliquid-docs, rate-limits-and-user-limits, read 2026-10-02). The
default --budget-fraction 0.5 uses half of it (300 requests/min), leaving
the other half for anything else on the PC that calls Hyperliquid (no other
script in this repo does, as of 2026-10-02). At 300/min one sweep of 47,007
addresses takes about 157 minutes; sweeps run back to back.

Read-only public endpoints, no key, no order endpoint.

Output (data/hyperliquid/, per UTC day of the row's ts_recv_utc, gzip CSV):
    leaderboard_YYYYMMDD.csv.gz  the leaderboard, once per UTC day (the
        source re-published it about hourly on 2026-10-02: Last-Modified
        03:48:33 then 04:48:39 UTC; one copy is 4.25 MB gzipped, so daily
        is a size choice the lead can change). Unique
        key: the response ETag (also stored with Last-Modified = the
        source's own time). lb_account_value is the leaderboard's own
        "accountValue"; it is a different number from ch_account_value
        below (measured: the same address showed 62,373,687 on the
        leaderboard and 2,311.92 in clearinghouseState), so the two are
        named apart and never merged.
    accounts_YYYYMMDD.csv.gz     one row per account WITH open positions per
        sweep (ch_* = clearinghouseState marginSummary etc.). Unique key
        (sweep_id, address).
    positions_YYYYMMDD.csv.gz    one row per open position per sweep.
        Unique key (sweep_id, address, coin).
    sweeps_YYYYMMDD.csv.gz       two rows per sweep, unique key (sweep_id,
        phase). sweep_id is the sweep's start time. phase=start is written
        (flushed) before the first address is asked; phase=end after the
        last one, with how many addresses were asked, answered, failed,
        held positions. Each row's ts_recv_utc is when it was written, so a
        sweep that crosses 00:00 UTC has its end row in the next day's file
        (join on sweep_id). Only for a sweep with an end row does "answered
        and no row in accounts/positions" mean "held no position at that
        time". A sweep with a start row and no end row was cut off (kill,
        nightly restart): which of its addresses answered is unknown. A
        restarted process starts a new sweep from the first address of the
        file (it does not resume the cut one).
    errors_YYYYMMDD.csv.gz       ts_recv_utc, source, target, error -- one row
        per failed call (target "write" = a failed append, whose rows stay
        buffered and are written by the next flush); the sweep continues.
    <name>_YYYYMMDD.truncN.csv.gz  a day file that did not end with a whole
        gzip member when this script was about to append to it (a kill hit
        a write), renamed whole -- see "gzip files" below. Its members up to
        the cut read normally (bot.research.gz_members.iter_members_in_order).
Every row has ts_recv_utc (this script's receive time); the source's time is
source_time_ms (clearinghouseState "time") / last_modified (leaderboard).

One process per output directory: the lock file data/hyperliquid.lock
(<out-dir>.lock) makes a second process exit with code 3 instead of
appending to the same files.

Usage:
    python scripts/record_hyperliquid.py --max-addresses 20   # quick check
    python scripts/record_hyperliquid.py --loop               # resident (start_all.bat)
A one-off run while the resident runs exits with code 3 (lock busy): stop
the resident first (deploy\\stop_all.bat) or point the one-off at another
--out-dir.
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
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "data" / "hyperliquid"
LOG_TAG = "record_hyperliquid"
INFO_URL = "https://api.hyperliquid.xyz/info"
LEADERBOARD_URL = "https://stats-data.hyperliquid.xyz/Mainnet/leaderboard"
UA = {"User-Agent": "trade-research/1.0 (research use)"}
TIMEOUT = 15.0
LEADERBOARD_TIMEOUT = 120.0      # 38.8 MB body (measured 2026-10-02)
WEIGHT_LIMIT_PER_MIN = 1200      # documented, see module docstring
CLEARINGHOUSE_WEIGHT = 2         # documented, see module docstring
DEFAULT_BUDGET_FRACTION = 0.5    # see module docstring
FLUSH_INTERVAL = 60.0            # same buffering period as record_venues.py
MAX_BACKOFF = 300.0              # same ceiling as record_venues.py

WINDOWS = ("day", "week", "month", "allTime")
LB_FIELDS = (["ts_recv_utc", "etag", "last_modified", "rank_in_file", "address",
              "lb_account_value", "display_name", "prize"]
             + [f"{w}_{m}" for w in WINDOWS for m in ("pnl", "roi", "vlm")])
ACCOUNT_FIELDS = ["ts_recv_utc", "sweep_id", "address", "source_time_ms",
                  "ch_account_value", "ch_total_ntl_pos", "ch_total_raw_usd",
                  "ch_total_margin_used", "cross_account_value",
                  "cross_total_ntl_pos", "cross_total_raw_usd",
                  "cross_total_margin_used", "cross_maintenance_margin_used",
                  "withdrawable", "n_positions"]
POSITION_FIELDS = ["ts_recv_utc", "sweep_id", "address", "source_time_ms",
                   "coin", "position_type", "szi", "entry_px", "position_value",
                   "unrealized_pnl", "return_on_equity", "liquidation_px",
                   "margin_used", "max_leverage", "leverage_type",
                   "leverage_value", "leverage_raw_usd", "cum_funding_all_time",
                   "cum_funding_since_open", "cum_funding_since_change"]
SWEEP_FIELDS = ["ts_recv_utc", "sweep_id", "phase", "ts_end_utc",
                "leaderboard_etag", "n_targets", "n_ok", "n_failed",
                "n_with_positions", "n_position_rows"]
ERROR_FIELDS = ["ts_recv_utc", "source", "target", "error"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _day(ts_iso: str) -> str:
    return ts_iso[:10].replace("-", "")


def _cell(v: object) -> object:
    return "" if v is None else v


def _unique(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    return [x for x in seq if not (x in seen or seen.add(x))]


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


def day_files(out_dir: Path, name: str, day: str) -> list[Path]:
    """The day's renamed files (trunc1, trunc2, ... = oldest first), then
    the day's current file: every file that holds rows of that day."""
    def n_of(p: Path) -> int:
        try:
            return int(p.name.split(".trunc")[1].split(".")[0])
        except (IndexError, ValueError):
            return 0
    trunc = sorted(out_dir.glob(f"{name}_{day}.trunc*.csv.gz"), key=n_of)
    return trunc + [out_dir / f"{name}_{day}.csv.gz"]


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
# LOCK_STALE_SEC belongs to a dead process and is taken over. stop_all.bat
# deletes the lock of the process it force-killed.
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
             f"processes never append to the same file. Stop the resident "
             f"with deploy\\stop_all.bat or use another --out-dir.")
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


def leaderboard_rows(ts: str, etag: str, last_modified: str,
                     rows: list) -> tuple[list[list], list[str]]:
    """(csv rows, addresses in the file's order). Rows without an address
    are skipped."""
    out, addrs = [], []
    for i, x in enumerate(rows, start=1):
        if not isinstance(x, dict) or not x.get("ethAddress"):
            continue
        addr = str(x["ethAddress"])
        addrs.append(addr)
        perf = {}
        for w in x.get("windowPerformances") or []:
            if isinstance(w, list) and len(w) == 2 and isinstance(w[1], dict):
                perf[w[0]] = w[1]
        out.append([ts, etag, last_modified, i, addr,
                    _cell(x.get("accountValue")), _cell(x.get("displayName")),
                    _cell(x.get("prize"))]
                   + [_cell(perf.get(w, {}).get(m)) for w in WINDOWS
                      for m in ("pnl", "roi", "vlm")])
    return out, addrs


def account_rows(ts: str, sweep_id: str, address: str,
                 body: dict) -> tuple[list | None, list[list]]:
    """(account row or None when no open position, position rows)."""
    positions = [p for p in body.get("assetPositions") or []
                 if isinstance(p, dict) and isinstance(p.get("position"), dict)]
    if not positions:
        return None, []
    t = _cell(body.get("time"))
    ms = body.get("marginSummary") or {}
    cms = body.get("crossMarginSummary") or {}
    acct = [ts, sweep_id, address, t,
            _cell(ms.get("accountValue")), _cell(ms.get("totalNtlPos")),
            _cell(ms.get("totalRawUsd")), _cell(ms.get("totalMarginUsed")),
            _cell(cms.get("accountValue")), _cell(cms.get("totalNtlPos")),
            _cell(cms.get("totalRawUsd")), _cell(cms.get("totalMarginUsed")),
            _cell(body.get("crossMaintenanceMarginUsed")),
            _cell(body.get("withdrawable")), len(positions)]
    rows, coins = [], set()
    for p in positions:
        pos = p["position"]
        coin = str(pos.get("coin", ""))
        if coin in coins:
            continue
        coins.add(coin)
        lev = pos.get("leverage") or {}
        cf = pos.get("cumFunding") or {}
        rows.append([ts, sweep_id, address, t, coin, _cell(p.get("type")),
                     _cell(pos.get("szi")), _cell(pos.get("entryPx")),
                     _cell(pos.get("positionValue")),
                     _cell(pos.get("unrealizedPnl")),
                     _cell(pos.get("returnOnEquity")),
                     _cell(pos.get("liquidationPx")), _cell(pos.get("marginUsed")),
                     _cell(pos.get("maxLeverage")), _cell(lev.get("type")),
                     _cell(lev.get("value")), _cell(lev.get("rawUsd")),
                     _cell(cf.get("allTime")), _cell(cf.get("sinceOpen")),
                     _cell(cf.get("sinceChange"))])
    return acct, rows


class HyperliquidRecorder:
    def __init__(self, out_dir: str | Path = DEFAULT_OUT_DIR,
                 session: requests.Session | None = None,
                 budget_fraction: float = DEFAULT_BUDGET_FRACTION,
                 sleep=time.sleep, clock=time.monotonic):
        if not 0 < budget_fraction <= 1:
            raise ValueError("budget_fraction must be in (0, 1]")
        self.out_dir = Path(out_dir)
        self.session = session or requests.Session()
        # seconds between the STARTS of two clearinghouseState calls
        self.req_interval = 60.0 / (WEIGHT_LIMIT_PER_MIN * budget_fraction
                                    / CLEARINGHOUSE_WEIGHT)
        self._sleep = sleep
        self._clock = clock
        self.out = BufferedDailyGz(self.out_dir)
        self._last_flush = clock()
        self._last_sweep_id: str | None = None
        self.seen_etags: set[str] = set()
        self.lb_day: str | None = None
        self.lb_etag = ""
        self.addresses: list[str] = []
        self._restore()

    def _restore(self) -> None:
        """Known ETags from yesterday/today; if today's leaderboard is already
        on disk, its addresses are the sweep universe (no re-download)."""
        now = datetime.now(timezone.utc)
        for delta in (1, 0):
            day = (now - timedelta(days=delta)).strftime("%Y%m%d")
            rows = [r for p in day_files(self.out_dir, "leaderboard", day)
                    for r in read_gz_rows(p)]
            for r in rows:
                if r.get("etag"):
                    self.seen_etags.add(r["etag"])
            if delta == 0 and rows:
                last_etag = rows[-1].get("etag", "")
                self.addresses = _unique([r["address"] for r in rows
                                          if r.get("etag") == last_etag
                                          and r.get("address")])
                self.lb_day, self.lb_etag = day, last_etag

    def _error(self, target: str, exc: object) -> None:
        msg = f"{type(exc).__name__}: {exc}"
        _log(f"{target} FAILED: {msg}")
        self.out.add("errors", ERROR_FIELDS, [_now_iso(), "hyperliquid", target, msg])

    def _new_sweep_id(self) -> str:
        """Start time in microseconds; strictly increasing within a process
        so two sweeps can never share an id (it is part of a unique key)."""
        sid = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        if self._last_sweep_id is not None and sid <= self._last_sweep_id:
            last = datetime.fromisoformat(self._last_sweep_id)
            sid = (last + timedelta(microseconds=1)).isoformat(timespec="microseconds")
        self._last_sweep_id = sid
        return sid

    def flush(self) -> int:
        """A failed write is recorded as an error row and its rows stay
        buffered for the next flush; the sweep goes on either way."""
        self._last_flush = self._clock()
        try:
            return self.out.flush()
        except Exception as exc:  # noqa: BLE001
            self._error("write", exc)
            return 0

    def _maybe_flush(self) -> None:
        if self._clock() - self._last_flush >= FLUSH_INTERVAL:
            self.flush()

    # ---- leaderboard -------------------------------------------------------
    def refresh_leaderboard(self) -> bool:
        """Fetch once per UTC day. True when an address universe is ready."""
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        if self.lb_day == today and self.addresses:
            return True
        try:
            r = self.session.get(LEADERBOARD_URL, headers=UA,
                                 timeout=LEADERBOARD_TIMEOUT)
            ts = _now_iso()
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")
            body = r.json()
            rows = body.get("leaderboardRows") if isinstance(body, dict) else None
            if not isinstance(rows, list) or not rows:
                raise RuntimeError("no leaderboardRows")
            etag = str(r.headers.get("ETag", "")).strip('"')
            last_mod = str(r.headers.get("Last-Modified", ""))
            csv_rows, addrs = leaderboard_rows(ts, etag, last_mod, rows)
            if not addrs:
                raise RuntimeError("leaderboardRows without addresses")
            # No ETag -> the content itself cannot be keyed; write it (once
            # per UTC day by construction of this method).
            if not etag or etag not in self.seen_etags:
                for row in csv_rows:
                    self.out.add("leaderboard", LB_FIELDS, row)
                if etag:
                    self.seen_etags.add(etag)
            self.addresses, self.lb_day, self.lb_etag = _unique(addrs), today, etag
            self.flush()
            return True
        except Exception as exc:  # noqa: BLE001
            self._error("leaderboard", exc)
            self.flush()
            return bool(self.addresses)   # keep sweeping yesterday's universe

    # ---- one sweep -----------------------------------------------------------
    def sweep(self, max_addresses: int | None = None) -> list:
        targets = self.addresses[:max_addresses] if max_addresses else list(self.addresses)
        sweep_id = self._new_sweep_id()
        n_ok = n_failed = n_with = n_rows = 0
        fails_in_row = 0
        seen: set[tuple[str, str]] = set()
        self.out.add("sweeps", SWEEP_FIELDS,
                     [sweep_id, sweep_id, "start", "", self.lb_etag,
                      len(targets), "", "", "", ""])
        self.flush()
        next_at = self._clock()
        for addr in targets:
            # Pace by request START times, so the response time counts
            # toward the interval instead of being added to it.
            self._sleep(max(0.0, next_at - self._clock()))
            next_at = self._clock() + self.req_interval
            try:
                r = self.session.post(INFO_URL, json={"type": "clearinghouseState",
                                                      "user": addr},
                                      headers=UA, timeout=TIMEOUT)
                ts = _now_iso()
                if r.status_code != 200:
                    raise RuntimeError(f"HTTP {r.status_code}")
                body = r.json()
                if not isinstance(body, dict):
                    raise RuntimeError(f"unexpected body type {type(body).__name__}")
                acct, rows = account_rows(ts, sweep_id, addr, body)
                n_ok += 1
                fails_in_row = 0
                if acct is not None:
                    n_with += 1
                    self.out.add("accounts", ACCOUNT_FIELDS, acct)
                    for row in rows:
                        key = (addr, row[4])
                        if key in seen:
                            continue
                        seen.add(key)
                        self.out.add("positions", POSITION_FIELDS, row)
                        n_rows += 1
            except Exception as exc:  # noqa: BLE001 - record, back off, continue
                n_failed += 1
                fails_in_row += 1
                self._error(f"clearinghouseState {addr}", exc)
                self._sleep(min(self.req_interval * (2 ** min(fails_in_row, 12)),
                                MAX_BACKOFF))
            self._maybe_flush()
        end = _now_iso()
        # ts_recv_utc of the end row = when it is written (its day file is a
        # finished day once that day is over; sweep_id carries the start).
        manifest = [end, sweep_id, "end", end, self.lb_etag,
                    len(targets), n_ok, n_failed, n_with, n_rows]
        self.out.add("sweeps", SWEEP_FIELDS, manifest)
        self.flush()
        return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--budget-fraction", type=float,
                    default=DEFAULT_BUDGET_FRACTION)
    ap.add_argument("--max-addresses", type=int, default=None,
                    help="poll only the first N addresses of the file "
                         "(checking the script only; not for recording)")
    ap.add_argument("--loop", action="store_true",
                    help="resident: sweep back to back")
    args = ap.parse_args(argv)
    out_dir = Path(args.out_dir)

    def body() -> int:
        rec = HyperliquidRecorder(out_dir=out_dir,
                                  budget_fraction=args.budget_fraction)
        try:
            return _run(rec, args)
        except KeyboardInterrupt:
            rec.flush()      # write what is buffered (at most FLUSH_INTERVAL)
            return 0
    return run_locked(out_dir, body)


def _run(rec: "HyperliquidRecorder", args: argparse.Namespace) -> int:
    retry = 60.0
    while True:
        if rec.refresh_leaderboard():
            retry = 60.0
            try:
                m = rec.sweep(args.max_addresses)
                print("[record_hyperliquid] sweep done "
                      + " ".join(f"{k}={v}" for k, v in zip(SWEEP_FIELDS[1:], m[1:])),
                      flush=True)
            except Exception as exc:  # noqa: BLE001 - resident
                print(f"[record_hyperliquid] sweep FAILED: {type(exc).__name__}: {exc}",
                      file=sys.stderr, flush=True)
                rec.flush()
        else:
            if not args.loop:
                return 1
            time.sleep(retry)
            retry = min(retry * 2, MAX_BACKOFF)
        if not args.loop:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())

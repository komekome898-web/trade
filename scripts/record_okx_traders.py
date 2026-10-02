#!/usr/bin/env python3
"""Record OKX's public lead-trader (copy trading) lists, their current and
closed positions, and OKX's top-trader long/short ratios, forward.

Why this exists: none of these can be fetched back later
(docs/DISCUSSIONS/2026-10-01_research_structure_intake_and_combiner.md
sec 5-1B; owner L-039 "取れる時に取れるだけ取る", L-531 "有名トレーダーの先出し
ポジション"). Measured from the research environment on 2026-10-02:
  - copytrading/public-lead-traders: the ranking as OKX publishes it now
    (SWAP 28 pages x 10, SPOT 17 pages; "dataVer" names the ranking version).
  - copytrading/public-current-subpositions: only what is open now.
  - copytrading/public-subpositions-history: depth differs by trader (one
    showed 26 closed positions back to 2026-07-24; four had more than
    5,000). How long OKX keeps them is 未確認.
  - for 85 of the 279 SWAP traders on the list, both position endpoints
    answered code 60004 "Trader doesn't exist" (recorded as error rows).
  - rubik top-trader ratios, period 5m: about 5 days deep (16 pages of 100,
    oldest 2026-09-27), 1H about 2 months.

Which traders: exactly the ones OKX lists in public-lead-traders, in OKX's
own default order, every page. Nobody here picks or drops a trader. The SPOT
list is recorded too, but its positions are not: both position endpoints
answer 400 / code 51000 "Parameter instType error" for instType=SPOT
(measured 2026-10-02). Traders whose positions OKX masks (blank instId,
openAvgPx, openTime, subPos) are recorded as OKX returns them.

Read-only public endpoints, no key, no order endpoint.

Output (data/okx_traders/, per UTC day of the receive time, gzip CSV):
    leadtraders_YYYYMMDD.csv.gz  the ranking. Unique key (data_ver,
                                 inst_type, unique_code); the keys are
                                 restored from yesterday's and today's files
                                 only, so a ranking version (dataVer) that
                                 stays the same for more than a day can be
                                 written again after a restart.
    positions_YYYYMMDD.csv.gz    open positions per sweep. Unique key
                                 (sweep_id, sub_pos_id).
    history_YYYYMMDD.csv.gz      closed positions. Unique key sub_pos_id,
                                 restored from ALL earlier history files
                                 so a closed position is written once ever.
    ratios_YYYYMMDD.csv.gz       top-trader (and all-account) long/short
                                 ratios, 5m. Unique key (kind, inst_id,
                                 period, source_ts).
    errors_YYYYMMDD.csv.gz       ts_recv_utc, source, target, error: one row
                                 per failed call (target "write" = a failed
                                 append, whose rows stay buffered and are
                                 written by the next flush); the sweep
                                 continues.
    <name>_YYYYMMDD.truncN.csv.gz  a day file that did not end with a whole
                                 gzip member when this script was about to
                                 append to it (a kill hit a write), renamed
                                 whole -- see "gzip files" below. Its members
                                 up to the cut read normally
                                 (bot.research.gz_members.iter_members_in_order);
                                 its rows count for the restored keys.
Every row carries ts_recv_utc (this script's receive time); the source's
own time is data_ver / open_time / close_time / source_ts.

Request pacing: OKX's documented rate limit for these endpoints was not
found (official docs page did not render the section; web search had no
quote) -- 未確認. Measured: 12 back-to-back calls in 3.7 s all returned
code 0. REQ_INTERVAL (0.5 s) stays slower than that measured rate.

One process per output directory: the lock file data/okx_traders.lock
(<out-dir>.lock) makes a second process exit with code 3 instead of
appending to the same files.

Usage:
    python scripts/record_okx_traders.py               # one cycle, exit
    python scripts/record_okx_traders.py --loop 3600   # resident (start_all.bat)
A one-off run (e.g. --max-pages 500 for a backfill) while the resident runs
exits with code 3 (lock busy): stop the resident first
(deploy\\stop_all.bat) or point the one-off at another --out-dir.

Start-up cost: the closed-position key is restored from every
history_*.csv.gz on each start, so start-up time grows with the archive
(not measured on the PC yet).
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
DEFAULT_OUT_DIR = ROOT / "data" / "okx_traders"
LOG_TAG = "record_okx_traders"
OKX = "https://www.okx.com"
TIMEOUT = 15.0
UA = {"User-Agent": "trade-research/1.0 (research use)"}
REQ_INTERVAL = 0.5          # see module docstring (measured, docs 未確認)
FLUSH_INTERVAL = 60.0       # same buffering period as record_venues.py
PAGE_LIMIT = 100            # the endpoints' "limit" maximum used in the probe
# Guard against a pagination that never ends; reaching it writes an error row.
# Measured 2026-10-02: some traders have more than 50 x 100 closed positions,
# so the first run keeps the newest 5,000 of those and logs the cap; later
# runs stop at the first known position. --max-pages raises it for a backfill.
MAX_PAGES = 50

LIST_INST_TYPES = ("SWAP", "SPOT")
POSITION_INST_TYPES = ("SWAP",)     # SPOT answers code 51000 (docstring)
RATIO_KINDS = ("long-short-account-ratio-contract-top-trader",
               "long-short-position-ratio-contract-top-trader",
               "long-short-account-ratio-contract")
# BTC-USDT-SWAP and BTC-USD-SWAP are the two swaps record_oi.py follows;
# ETH-USDT-SWAP answered 200 too (2026-10-02) and is taken under L-039.
DEFAULT_RATIO_INST_IDS = ("BTC-USDT-SWAP", "BTC-USD-SWAP", "ETH-USDT-SWAP")
RATIO_PERIOD = "5m"

LIST_FIELDS = ["ts_recv_utc", "data_ver", "inst_type", "page", "rank_in_page",
               "unique_code", "nick_name", "ccy", "aum", "pnl", "pnl_ratio",
               "win_ratio", "lead_days", "copy_trader_num",
               "max_copy_trader_num", "acc_copy_trader_num", "copy_state",
               "port_link", "trader_insts_json", "pnl_ratios_json"]
_LIST_KEYS = ["uniqueCode", "nickName", "ccy", "aum", "pnl", "pnlRatio",
              "winRatio", "leadDays", "copyTraderNum", "maxCopyTraderNum",
              "accCopyTraderNum", "copyState", "portLink"]
POS_FIELDS = ["ts_recv_utc", "sweep_id", "inst_type", "unique_code",
              "sub_pos_id", "inst_id", "pos_side", "mgn_mode", "lever",
              "open_avg_px", "open_time", "sub_pos", "margin", "mark_px",
              "upl", "upl_ratio", "ccy"]
_POS_KEYS = ["instType", "uniqueCode", "subPosId", "instId", "posSide",
             "mgnMode", "lever", "openAvgPx", "openTime", "subPos", "margin",
             "markPx", "upl", "uplRatio", "ccy"]
HIST_FIELDS = ["ts_recv_utc", "inst_type", "unique_code", "sub_pos_id",
               "inst_id", "pos_side", "mgn_mode", "lever", "open_avg_px",
               "open_time", "close_avg_px", "close_time", "sub_pos", "margin",
               "pnl", "pnl_ratio", "ccy"]
_HIST_KEYS = ["instType", "uniqueCode", "subPosId", "instId", "posSide",
              "mgnMode", "lever", "openAvgPx", "openTime", "closeAvgPx",
              "closeTime", "subPos", "margin", "pnl", "pnlRatio", "ccy"]
RATIO_FIELDS = ["ts_recv_utc", "kind", "inst_id", "period", "source_ts",
                "source_ts_utc", "ratio"]
ERROR_FIELDS = ["ts_recv_utc", "source", "target", "error"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _day(ts_iso: str) -> str:
    return ts_iso[:10].replace("-", "")


def _iso_ms(ms: object) -> str:
    return datetime.fromtimestamp(int(ms) / 1000.0, tz=timezone.utc
                                  ).isoformat(timespec="milliseconds")


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


class OkxTradersRecorder:
    def __init__(self, out_dir: str | Path = DEFAULT_OUT_DIR,
                 session: requests.Session | None = None,
                 ratio_inst_ids: tuple[str, ...] = DEFAULT_RATIO_INST_IDS,
                 req_interval: float = REQ_INTERVAL,
                 max_pages: int = MAX_PAGES,
                 sleep=time.sleep, clock=time.monotonic):
        self.out_dir = Path(out_dir)
        self.session = session or requests.Session()
        self.ratio_inst_ids = ratio_inst_ids
        self.req_interval = req_interval
        self.max_pages = max_pages
        self._sleep = sleep
        self._clock = clock
        self.out = BufferedDailyGz(self.out_dir)
        self._last_flush = clock()
        self._last_sweep_id: str | None = None
        self.seen_lists: set[tuple[str, str, str]] = set()
        self.seen_ratios: set[tuple[str, str, str, str]] = set()
        self.seen_hist: set[str] = set()
        self.seen_pos: set[tuple[str, str]] = set()
        self.counts: dict[str, int] = {}
        self._restore()

    # ---- restore dedup keys from what is already on disk -------------------
    def _recent_days(self) -> list[str]:
        now = datetime.now(timezone.utc)
        return [(now - timedelta(days=d)).strftime("%Y%m%d") for d in (1, 0)]

    def _restore(self) -> None:
        for day in self._recent_days():
            for p in day_files(self.out_dir, "leadtraders", day):
                for r in read_gz_rows(p):
                    self.seen_lists.add((r.get("data_ver", ""), r.get("inst_type", ""),
                                         r.get("unique_code", "")))
            for p in day_files(self.out_dir, "ratios", day):
                for r in read_gz_rows(p):
                    self.seen_ratios.add((r.get("kind", ""), r.get("inst_id", ""),
                                          r.get("period", ""), r.get("source_ts", "")))
        # A trader's "latest 100" closed positions can be months old, so the
        # closed-position key is restored from every history file, not 2 days
        # (the renamed history_<day>.truncN.csv.gz files included).
        for path in sorted(self.out_dir.glob("history_*.csv.gz")):
            for r in read_gz_rows(path):
                if r.get("sub_pos_id"):
                    self.seen_hist.add(r["sub_pos_id"])

    # ---- plumbing ----------------------------------------------------------
    def _get(self, path: str, params: dict) -> tuple[str, list]:
        self._sleep(self.req_interval)
        r = self.session.get(OKX + path, params=params, headers=UA,
                             timeout=TIMEOUT)
        ts = _now_iso()
        try:
            body = r.json()
        except ValueError:
            raise RuntimeError(f"HTTP {r.status_code}, body not JSON") from None
        code = str(body.get("code", "")) if isinstance(body, dict) else ""
        if r.status_code != 200 or code != "0":
            msg = body.get("msg", "") if isinstance(body, dict) else ""
            raise RuntimeError(f"HTTP {r.status_code} code={code} msg={msg!r}")
        data = body.get("data")
        return ts, data if isinstance(data, list) else []

    def _error(self, target: str, exc: object) -> None:
        msg = f"{type(exc).__name__}: {exc}"
        _log(f"{target} FAILED: {msg}")
        self.out.add("errors", ERROR_FIELDS, [_now_iso(), "okx", target, msg])
        self._count("errors")

    def _count(self, what: str, n: int = 1) -> None:
        self.counts[what] = self.counts.get(what, 0) + n

    def _maybe_flush(self) -> None:
        if self._clock() - self._last_flush >= FLUSH_INTERVAL:
            self.flush()

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
        buffered for the next flush; the cycle goes on either way."""
        self._last_flush = self._clock()
        try:
            return self.out.flush()
        except Exception as exc:  # noqa: BLE001
            self._error("write", exc)
            return 0

    # ---- ratios ------------------------------------------------------------
    def record_ratios(self) -> None:
        for kind in RATIO_KINDS:
            for inst in self.ratio_inst_ids:
                target = f"rubik {kind} {inst} {RATIO_PERIOD}"
                try:
                    ts, data = self._get(f"/api/v5/rubik/stat/contracts/{kind}",
                                         {"instId": inst, "period": RATIO_PERIOD,
                                          "limit": str(PAGE_LIMIT)})
                    for row in sorted((x for x in data
                                       if isinstance(x, list) and len(x) >= 2),
                                      key=lambda x: int(x[0])):
                        key = (kind, inst, RATIO_PERIOD, str(row[0]))
                        if key in self.seen_ratios:
                            continue
                        self.seen_ratios.add(key)
                        self.out.add("ratios", RATIO_FIELDS,
                                     [ts, kind, inst, RATIO_PERIOD, row[0],
                                      _iso_ms(row[0]), row[1]])
                        self._count("ratios")
                except Exception as exc:  # noqa: BLE001
                    self._error(target, exc)

    # ---- the published ranking ---------------------------------------------
    def record_lists(self) -> list[tuple[str, str]]:
        """Every page of every list; returns (inst_type, unique_code) in
        OKX's order for the inst types whose positions are public."""
        targets: list[tuple[str, str]] = []
        for inst_type in LIST_INST_TYPES:
            page, total = 1, 1
            while page <= total:
                if page > self.max_pages:
                    self._error(f"lead-traders {inst_type}",
                                RuntimeError(f"page cap {self.max_pages} reached "
                                             f"(totalPage={total})"))
                    break
                try:
                    ts, data = self._get("/api/v5/copytrading/public-lead-traders",
                                         {"instType": inst_type, "page": str(page)})
                except Exception as exc:  # noqa: BLE001
                    self._error(f"lead-traders {inst_type} page {page}", exc)
                    page += 1
                    continue
                if not data or not isinstance(data[0], dict):
                    self._error(f"lead-traders {inst_type} page {page}",
                                RuntimeError("empty data"))
                    page += 1
                    continue
                block = data[0]
                try:
                    total = int(block.get("totalPage") or total)
                except (TypeError, ValueError):
                    pass
                ver = str(block.get("dataVer", ""))
                for i, t in enumerate(block.get("ranks") or [], start=1):
                    if not isinstance(t, dict) or not t.get("uniqueCode"):
                        continue
                    code = str(t["uniqueCode"])
                    if inst_type in POSITION_INST_TYPES:
                        targets.append((inst_type, code))
                    key = (ver, inst_type, code)
                    if key in self.seen_lists:
                        continue
                    self.seen_lists.add(key)
                    self.out.add("leadtraders", LIST_FIELDS,
                                 [ts, ver, inst_type, page, i]
                                 + [_cell(t.get(k)) for k in _LIST_KEYS]
                                 + [json.dumps(t.get("traderInsts"), separators=(",", ":")),
                                    json.dumps(t.get("pnlRatios"), separators=(",", ":"))])
                    self._count("leadtraders")
                page += 1
        seen, ordered = set(), []
        for t in targets:
            if t not in seen:
                seen.add(t)
                ordered.append(t)
        return ordered

    # ---- positions -----------------------------------------------------------
    def _pages(self, path: str, params: dict, stop_on_known: bool):
        """Yield (ts, items) pages, following after=<last subPosId>."""
        after = None
        for _ in range(self.max_pages):
            p = dict(params, limit=str(PAGE_LIMIT))
            if after:
                p["after"] = after
            ts, data = self._get(path, p)
            items = [x for x in data if isinstance(x, dict)]
            # Decided BEFORE the caller marks this page's ids as seen.
            reached_known = stop_on_known and any(
                str(x.get("subPosId")) in self.seen_hist for x in items)
            yield ts, items
            if len(items) < PAGE_LIMIT or reached_known:
                return
            after = str(items[-1].get("subPosId", ""))
            if not after:
                return
        raise RuntimeError(f"page cap {self.max_pages} reached")

    def record_trader(self, sweep_id: str, inst_type: str, code: str) -> None:
        params = {"instType": inst_type, "uniqueCode": code}
        try:
            for ts, items in self._pages("/api/v5/copytrading/public-current-subpositions",
                                         params, stop_on_known=False):
                for x in items:
                    key = (sweep_id, str(x.get("subPosId", "")))
                    if key in self.seen_pos:
                        continue
                    self.seen_pos.add(key)
                    self.out.add("positions", POS_FIELDS,
                                 [ts, sweep_id] + [_cell(x.get(k)) for k in _POS_KEYS])
                    self._count("positions")
        except Exception as exc:  # noqa: BLE001
            self._error(f"current-subpositions {inst_type} {code}", exc)
        try:
            for ts, items in self._pages("/api/v5/copytrading/public-subpositions-history",
                                         params, stop_on_known=True):
                for x in items:
                    sid = str(x.get("subPosId", ""))
                    if not sid or sid in self.seen_hist:
                        continue
                    self.seen_hist.add(sid)
                    self.out.add("history", HIST_FIELDS,
                                 [ts] + [_cell(x.get(k)) for k in _HIST_KEYS])
                    self._count("history")
        except Exception as exc:  # noqa: BLE001
            self._error(f"subpositions-history {inst_type} {code}", exc)
        self._maybe_flush()

    def run_cycle(self) -> dict[str, int]:
        self.counts = {}
        sweep_id = self._new_sweep_id()
        self.seen_pos = set()
        self.record_ratios()
        self.flush()
        targets = self.record_lists()
        self.flush()
        for inst_type, code in targets:
            self.record_trader(sweep_id, inst_type, code)
        self.flush()
        self.counts["traders"] = len(targets)
        return dict(self.counts)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--loop", type=float, default=None, metavar="SECONDS",
                    help="resident: start a cycle every SECONDS (a cycle that "
                         "runs longer is followed by the next one at once)")
    ap.add_argument("--max-pages", type=int, default=MAX_PAGES,
                    help="page cap per list / per trader (a one-off run with a "
                         "larger cap backfills closed positions beyond it)")
    args = ap.parse_args(argv)
    out_dir = Path(args.out_dir)

    def body() -> int:
        rec = OkxTradersRecorder(out_dir=out_dir, max_pages=args.max_pages)
        try:
            return _run(rec, args)
        except KeyboardInterrupt:
            rec.flush()      # write what is buffered (at most FLUSH_INTERVAL)
            return 0
    return run_locked(out_dir, body)


def _run(rec: "OkxTradersRecorder", args: argparse.Namespace) -> int:
    while True:
        t0 = time.monotonic()
        try:
            counts = rec.run_cycle()
            print(f"[record_okx_traders] cycle done {datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ} "
                  + " ".join(f"{k}={v}" for k, v in sorted(counts.items())),
                  flush=True)
        except Exception as exc:  # noqa: BLE001 - resident: never die on one cycle
            print(f"[record_okx_traders] cycle FAILED: {type(exc).__name__}: {exc}",
                  file=sys.stderr, flush=True)
            rec.flush()
        if args.loop is None:
            return 0
        time.sleep(max(1.0, args.loop - (time.monotonic() - t0)))


if __name__ == "__main__":
    raise SystemExit(main())

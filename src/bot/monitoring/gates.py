"""Pre-registered coverage bars (docs/KNOWLEDGE.md §4 / §5) and the cheap
progress reading the dashboard shows against them.

The BARS live here, not in scripts/judge_gates.py, so the judge and the
operations console can never drift apart: judge_gates imports these names and
so does bot.monitoring.aggregate. The measurement primitives are shared for the
same reason — two implementations of "how many OI rows are there" would
eventually disagree, and the one on the dashboard is the one the owner reads
every day.

Nothing here JUDGES anything. A gate's PASS/FAIL needs the statistics in
judge_gates; this module only answers "how much of the required sample exists,
and — at the rate it has actually been accumulating — when is it full". The
rate is measured (units accumulated / seconds since the first observation),
never assumed: with no observations there is no rate and the ETA is None, which
the page renders as "—" rather than as a guess.

The file scans (candles, OI snapshots, the champion decision log) are
memoised on (mtime_ns, size), so a 5-second dashboard poll costs one stat()
per file until the collector actually appends something.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

# ---- pre-registered bars (KNOWLEDGE.md; do not tune here) ------------------
MAIN_TRADES_BAR = 30              # §5 main bot: closed paper trades
OI_ROWS_BAR = 2900                # §4 OI phase C: ~30 days at 15 min
OI_DAYS_BAR = 30.0
BOARD_DAYS_BAR = 7.0              # §4 board data: 1-2 weeks
BOARD_BYTES_BAR = 500_000_000     # §4 board data: ~0.5-1 GB
FUNDING_N_BAR = 63                # §4 funding window: 3x the original n=21
FUNDING_HOUR_UTC = 13             # settlement 05/13/21 UTC; 13:00 was measured
FUNDING_WINDOW_MIN = 30

DAY_SEC = 86400.0


# ---- shared readers --------------------------------------------------------
def parse_ts(value: Any) -> float | None:
    """Unix seconds from a float, an ISO-8601 string, or None.

    Naive strings are read as UTC — every writer in this repo stamps UTC
    (bot.logging_setup uses datetime.now(timezone.utc).isoformat()).
    """
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if not isinstance(value, str):
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def csv_first_last_ts(path: Path, column: str = "ts_utc"
                      ) -> tuple[int, float | None, float | None, int]:
    """(rows, first ts, last ts, bad rows) for an append-only CSV."""
    rows = bad = 0
    first = last = None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            header = f.readline().strip().split(",")
            try:
                idx = header.index(column)
            except ValueError:
                idx = 0
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(",")
                if len(parts) <= idx:
                    bad += 1
                    continue
                ts = parse_ts(parts[idx])
                if ts is None:
                    bad += 1
                    continue
                rows += 1
                first = ts if first is None else min(first, ts)
                last = ts if last is None else max(last, ts)
    except OSError:
        return 0, None, None, bad
    return rows, first, last, bad


_WS_STAMP = re.compile(r"(\d{8})_(\d{6})")


def ws_file_start(path: Path) -> float | None:
    """The UTC start stamped into a data/ws recording's filename."""
    m = _WS_STAMP.search(path.name)
    if not m:
        return None
    try:
        dt = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
    except ValueError:
        return None
    return dt.replace(tzinfo=timezone.utc).timestamp()


def candle_days_covering(path: Path, hour: int, minutes: int
                         ) -> tuple[set[str], int]:
    """UTC days whose 1-minute candles cover [hour:00, hour:00+minutes]."""
    have_start: set[str] = set()
    have_end: set[str] = set()
    bad = 0
    end_h, end_m = divmod(hour * 60 + minutes, 60)
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            header = f.readline().strip().split(",")
            idx = header.index("ts") if "ts" in header else 0
            for line in f:
                parts = line.split(",")
                if len(parts) <= idx:
                    bad += 1
                    continue
                ts = parse_ts(parts[idx])
                if ts is None:
                    bad += 1
                    continue
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                if dt.hour == hour and dt.minute == 0:
                    have_start.add(dt.strftime("%Y-%m-%d"))
                elif dt.hour == end_h and dt.minute == end_m % 60:
                    have_end.add(dt.strftime("%Y-%m-%d"))
    except OSError:
        return set(), bad
    return have_start & have_end, bad


# ---- stat-keyed memo for the two full-file scans ---------------------------
_scan_cache: dict[tuple[str, str], tuple[tuple[int, int] | None, Any]] = {}


def _stat_key(path: Path) -> tuple[int, int] | None:
    try:
        st = path.stat()
    except OSError:
        return None
    return (st.st_mtime_ns, st.st_size)


def cached_scan(tag: str, path: Path, fn: Callable[[], Any]) -> Any:
    """``fn()`` once per (path, mtime, size). The dashboard polls every 5s and
    the candle file changes every ~15 min; without this the console would
    re-read tens of thousands of rows per poll to draw one progress bar."""
    key = (tag, str(path))
    stat = _stat_key(path)
    hit = _scan_cache.get(key)
    if hit is not None and hit[0] == stat:
        return hit[1]
    value = fn()
    _scan_cache[key] = (stat, value)
    return value


def clear_cache() -> None:
    """Drop the scan memo (tests that rewrite a file within one mtime tick)."""
    _scan_cache.clear()


# ---- progress ---------------------------------------------------------------
def _bar_stats(have: float, need: float, first_ts: float | None, now: float
              ) -> tuple[float | None, float | None, float | None]:
    """(pct 0-100, rate units/sec, eta_sec) for ONE bar.

    The rate is ``have / (now - first_ts)`` — what actually accumulated over
    the window we have been observing, gaps and outages included. An estimate
    that assumed the collector runs perfectly from here would be the
    optimistic one, and the whole point of a progress row is to tell the
    owner when to look again.
    """
    remaining = max(0.0, need - have)
    elapsed = None if first_ts is None else max(0.0, now - first_ts)
    rate = (have / elapsed) if (elapsed and have > 0) else None   # units/sec
    if remaining <= 0:
        eta: float | None = 0.0
    elif rate is None or rate <= 0:
        eta = None
    else:
        eta = remaining / rate
    pct = min(100.0, have / need * 100.0) if need > 0 else None
    return pct, rate, eta


def progress(key: str, label: str, *, have: float, need: float, unit: str,
             first_ts: float | None, now: float, bar: str,
             age_sec: float | None = None, detail: str = "",
             extra_have: float | None = None, extra_need: float | None = None,
             extra_first_ts: float | None = None) -> dict[str, Any]:
    """One gate row: how much of the sample exists and when it fills up.

    ``extra_have``/``extra_need`` put a SECOND bar on the same row — board_gate
    needs data/ws to reach BOTH 7 days and ~0.5 GB. When given, the row folds
    both bars together rather than reporting the first one alone:

      ``done``    only when BOTH bars are met
      ``pct``     the MIN of the two bars' percentages — the one further
                  behind is what the owner is actually waiting on
      ``eta_sec`` the LATER of the two bars' ETAs — the row is not full until
                  the slower bar is, and one half unknown makes the whole row
                  unknown rather than an optimistic guess off the other half

    ``extra_first_ts`` defaults to ``first_ts`` (the same clock, a different
    accumulated unit).
    """
    have = float(have)
    need = float(need)
    pct, rate, eta = _bar_stats(have, need, first_ts, now)
    done = have >= need
    if extra_need is not None:
        extra_have = float(extra_have or 0.0)
        extra_need = float(extra_need)
        x_first = first_ts if extra_first_ts is None else extra_first_ts
        x_pct, _x_rate, x_eta = _bar_stats(extra_have, extra_need, x_first, now)
        done = done and (extra_have >= extra_need)
        if pct is not None and x_pct is not None:
            pct = min(pct, x_pct)
        elif x_pct is not None:
            pct = x_pct
        eta = max(eta, x_eta) if (eta is not None and x_eta is not None) else None
    return {
        "key": key, "label": label, "unit": unit,
        "have": round(have, 2), "need": round(need, 2),
        "pct": round(pct, 1) if pct is not None else None,
        "rate_per_day": round(rate * DAY_SEC, 3) if rate else None,
        "eta_sec": round(eta, 0) if eta is not None else None,
        "done": done,
        "bar": bar,
        # clamped: a file stamped in the future (clock skew between the
        # collector box and this one) is 0 seconds old, not "-2.3 days ago"
        "age_sec": round(max(0.0, age_sec), 1) if age_sec is not None else None,
        "detail": detail,
    }


# ---- champion trades: full-log read at judge_gates' own depth --------------
# scripts/judge_gates.py:load_champion_trades reconstructs closed round trips
# from the WHOLE decision log (it can run for months of append-only writes),
# reading up to CHAMPION_LOG_MAX_BYTES rather than market_view's 4 MB console
# tail. The gate must count the trades the judge counts, so it reads with the
# SAME reader at the SAME depth — both live here, and scripts/judge_gates.py
# imports read_jsonl from this module instead of keeping its own copy, the
# same arrangement as the BARS above.
CHAMPION_LOG_MAX_BYTES = 256 * 1024 * 1024

_NON_FILL_STATES = {"PENDING_SUBMIT", "SUBMITTED", "CANCELED", "REJECTED",
                    "STATE_UNKNOWN", "ABANDONED"}


def read_jsonl(path: Path, max_bytes: int = CHAMPION_LOG_MAX_BYTES
              ) -> tuple[list[dict], int]:
    """Every parseable JSON object in a .jsonl file, plus the bad-line count.

    A half-written last line (the collector is probably still running) and any
    corrupt line in the middle are skipped, never raised. A file bigger than
    ``max_bytes`` keeps its NEWEST tail: logs/bot.jsonl is append-only, so
    whatever a cap has to drop is the oldest end of it.
    """
    records: list[dict] = []
    bad = 0
    try:
        size = path.stat().st_size
    except OSError:
        return [], 0
    try:
        with open(path, "rb") as f:
            if size > max_bytes:                     # keep the newest tail
                f.seek(size - max_bytes)
                f.readline()
                bad += 1
            for raw in f:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except ValueError:
                    bad += 1
                    continue
                if isinstance(obj, dict):
                    records.append(obj)
                else:
                    bad += 1
    except OSError:
        return records, bad
    return records, bad


def _fval(value: Any) -> float | None:
    """float() that returns None instead of raising (log fields can be null)."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _champion_summary(path: Path) -> dict[str, Any]:
    """Closed round trips, paired the same positional way
    scripts/judge_gates.py:load_champion_trades pairs them: an ORDER_SENT that
    opens a position, then the NEXT ORDER_SENT while it is open closes it,
    whatever its own signal says — an ambiguous close (STATE_UNKNOWN with no
    realized PnL step) leaves the position open rather than booking a trade.
    Only counts and timestamps are kept here; the console needs no
    price/notional/PnL detail for a progress bar.

    ``first_entry_ts`` is the FIRST trade's own entry — reading the whole log
    (not a tail) is what makes that unambiguous.
    """
    records, _bad = read_jsonl(path)
    closed = 0
    first_entry_ts: float | None = None
    last_exit_ts: float | None = None
    last_pnl: float | None = None
    open_trade: dict[str, Any] | None = None

    for rec in records:
        if rec.get("event") != "decision" and not rec.get("strategy_signal"):
            continue
        ts = parse_ts(rec.get("timestamp"))
        pnl_now = _fval(rec.get("PnL"))
        if rec.get("decision") != "ORDER_SENT":
            if pnl_now is not None and last_pnl is None:
                last_pnl = pnl_now
            continue
        state = rec.get("execution_status")
        signal = str(rec.get("strategy_signal") or "")
        filled = state is None or state not in _NON_FILL_STATES

        if open_trade is None:
            if not filled or signal not in ("BUY", "SELL"):
                if pnl_now is not None and last_pnl is None:
                    last_pnl = pnl_now
                continue
            if last_pnl is None:
                # baseline: the P&L already on the books when the log starts
                last_pnl = pnl_now if pnl_now is not None else 0.0
            open_trade = {"ts": ts}
            if first_entry_ts is None and ts is not None:
                first_entry_ts = ts
            continue

        # a position is open -> this order closes it
        delta = None if (pnl_now is None or last_pnl is None) else pnl_now - last_pnl
        if not filled and (delta is None or delta == 0.0):
            continue        # ambiguous close: the position may still be open
        closed += 1
        if ts is not None:
            last_exit_ts = ts
        open_trade = None
        if pnl_now is not None:
            last_pnl = pnl_now

    return {"closed": closed, "first_entry_ts": first_entry_ts,
            "last_exit_ts": last_exit_ts, "open_at_end": open_trade is not None}


# ---- the four pending coverage gates ---------------------------------------
def champion_gate(root: Path, now: float) -> dict[str, Any]:
    """G1 sample size: CLOSED round trips in logs/bot.jsonl.

    Counted the same way scripts/judge_gates.py:load_champion_trades counts
    them (see ``_champion_summary``) — full-log positional entry/exit pairing
    at ``CHAMPION_LOG_MAX_BYTES``, not market_view's 4 MB console tail. A log
    past 4 MB has trades the tail cannot see, and this row must show the same
    n the judge's PASS/FAIL is computed against. status.json's ``trade_count``
    is fills (an entry and its exit are two) and would report double.
    """
    path = root / "logs" / "bot.jsonl"
    summary = cached_scan("champion", path, lambda: _champion_summary(path))
    open_now = 1 if summary["open_at_end"] else 0
    return progress(
        "champion", "チャンピオン試行 (§5)",
        have=summary["closed"], need=MAIN_TRADES_BAR, unit="trades",
        first_ts=summary["first_entry_ts"], now=now,
        bar=f">= {MAIN_TRADES_BAR} 決済済みトレード",
        age_sec=(now - summary["last_exit_ts"]) if summary["last_exit_ts"] else None,
        detail=f"建玉中 {open_now}件")


def oi_gate(root: Path, now: float) -> dict[str, Any]:
    """G6 coverage: rows in data/oi_snapshots.csv (15-min cadence)."""
    path = root / "data" / "oi_snapshots.csv"
    rows, first, last, _bad = cached_scan(
        "oi", path, lambda: csv_first_last_ts(path))
    span_days = (last - first) / DAY_SEC if (first and last) else 0.0
    return progress(
        "oi", "OIスナップショット", have=rows, need=OI_ROWS_BAR, unit="rows",
        first_ts=first, now=now,
        bar=f">= {OI_ROWS_BAR}行 ({OI_DAYS_BAR:.0f}日)",
        age_sec=(now - last) if last else None,
        detail=f"{span_days:.1f}日分")


def board_gate(root: Path, now: float,
               files: Iterable[Path] | None = None) -> dict[str, Any]:
    """G7 coverage: data/ws recordings, which must reach BOTH 7 days and ~0.5 GB.

    The span is first-file start to last-file mtime — an UPPER bound on real
    coverage, exactly as judge_gates measures it (gaps are not subtracted).

    ``files`` lets the caller hand over a listing it already has (the dashboard
    globs data/ws for the recorder's liveness anyway); None globs it here.
    """
    if files is None:
        ws_dir = root / "data" / "ws"
        files = sorted(ws_dir.glob("*.jsonl.gz")) if ws_dir.is_dir() else []
    files = list(files)
    total = 0
    starts: list[float] = []
    ends: list[float] = []
    for f in files:
        try:
            st = f.stat()
        except OSError:
            continue
        total += st.st_size
        ends.append(st.st_mtime)
        starts.append(ws_file_start(f) or st.st_mtime)
    span_days = (max(ends) - min(starts)) / DAY_SEC if starts else 0.0
    first_ts = min(starts) if starts else None
    return progress(
        "board", "板記録 (WS)", have=span_days, need=BOARD_DAYS_BAR,
        unit="days", first_ts=first_ts, now=now,
        bar=f">= {BOARD_DAYS_BAR:.0f}日 かつ >= {BOARD_BYTES_BAR / 1e9:.1f}GB",
        age_sec=(now - max(ends)) if ends else None,
        detail=f"{total / 1e6:.1f} MB / {len(files)}ファイル",
        extra_have=total, extra_need=BOARD_BYTES_BAR)


def funding_gate(root: Path, now: float) -> dict[str, Any]:
    """G8 coverage: UTC days whose candles cover the 13:00 settlement window.

    The union over backtest_data/ snapshots and the live file, because bitFlyer
    public history expires after 31 days (§6) — the sample is built by keeping
    snapshots, not by one long fetch.
    """
    snapshots = root / "backtest_data"
    sources = (sorted(snapshots.glob("candles_FX_BTC_JPY*.csv"))
               if snapshots.is_dir() else [])
    live = root / "data" / "candles_FX_BTC_JPY.csv"
    if live.exists():
        sources.append(live)
    days: set[str] = set()
    newest: float | None = None
    for path in sources:
        found, _bad = cached_scan(
            "funding", path,
            lambda p=path: candle_days_covering(p, FUNDING_HOUR_UTC,
                                                FUNDING_WINDOW_MIN))
        days |= found
        stat = _stat_key(path)
        if stat is not None:
            mtime = stat[0] / 1e9
            newest = mtime if newest is None else max(newest, mtime)
    first_ts = None
    if days:
        first_ts = parse_ts(min(days) + "T00:00:00+00:00")
    return progress(
        "funding", "資金調達ウィンドウ (13:00 UTC)",
        have=len(days), need=FUNDING_N_BAR, unit="days",
        first_ts=first_ts, now=now,
        bar=f">= {FUNDING_N_BAR}日 (元のn=21の3倍)",
        age_sec=(now - newest) if newest else None,
        detail=f"{len(sources)}ファイルの和集合")


def collect_gates(root: str | Path, now: float,
                  ws_files: Iterable[Path] | None = None
                  ) -> list[dict[str, Any]]:
    """The four PENDING coverage gates, in the order the console shows them."""
    root = Path(root)
    return [champion_gate(root, now),
            oi_gate(root, now),
            board_gate(root, now, ws_files),
            funding_gate(root, now)]

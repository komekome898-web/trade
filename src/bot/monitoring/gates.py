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
and — at the rate it has actually been accumulating — when is it full". (The
champion row carries a VERDICT, but that verdict is a recorded fact — report
#22's n=30 FAIL — transcribed as constants above, not computed here.) The
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

from bot.radar import StormRadar

# ---- pre-registered bars (KNOWLEDGE.md; do not tune here) ------------------
MAIN_TRADES_BAR = 30              # §5 main bot: closed paper trades
OI_ROWS_BAR = 2900                # §4 OI phase C: ~30 days at 15 min
OI_DAYS_BAR = 30.0
BOARD_DAYS_BAR = 7.0              # §4 board data: 1-2 weeks
BOARD_BYTES_BAR = 500_000_000     # §4 board data: ~0.5-1 GB
FUNDING_N_BAR = 63                # §4 funding window: 3x the original n=21
FUNDING_HOUR_UTC = 13             # settlement 05/13/21 UTC; 13:00 was measured
FUNDING_WINDOW_MIN = 30
# §4 C2 radar_window: judged on the inside-window SUBSET at n >= 15 (a
# deliberate, owner-approvable deviation from §5's 30 — config/composite.yaml
# modules.radar_window.gate). Must equal scripts/judge_gates.py SUBSET_N_BAR;
# a test pins the two together.
C2_TRADES_BAR = 15
# §4 spread MM phase 2 (report #26): the daily-statistics bar needs 14 board
# days in data/ws; the 7-day/0.5GB G7 bar above is the already-reached
# phase-1 coverage bar.
SPREADMM_BOARD_DAYS_BAR = 14.0

# §5 adoption table / §3 index: the champion (xborder_momentum) was FORMALLY
# JUDGED at n=30 and rejected (report #22, docs/RESEARCH_REPORT_2026-08-25w.md:
# net −0.148%/trade vs the +0.15% bar; the day-clustered CI excludes the bar).
# The paper run continues only to fill the C2 inside-window subset, so the
# console shows this as a settled verdict, not a progress bar toward 30.
CHAMPION_VERDICT = "FAIL"
CHAMPION_VERDICT_DETAIL = "net −0.148%/取引、第22報"
CHAMPION_VERDICT_NOTE = "C2判定まで収集継続"

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
    (not a tail) is what makes that unambiguous. ``closed_spans`` keeps every
    closed trade's (entry_ts, exit_ts) so the C2 gate can take the SAME
    radar-window subset judge_gates' G4a takes (filtered on entry_ts).
    """
    records, _bad = read_jsonl(path)
    closed = 0
    closed_spans: list[tuple[float | None, float | None]] = []
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
        closed_spans.append((open_trade["ts"], ts))
        if ts is not None:
            last_exit_ts = ts
        open_trade = None
        if pnl_now is not None:
            last_pnl = pnl_now

    return {"closed": closed, "closed_spans": closed_spans,
            "first_entry_ts": first_entry_ts,
            "last_exit_ts": last_exit_ts, "open_at_end": open_trade is not None}


# ---- the pending coverage gates (plus the settled champion verdict) --------
def shared_or_local(root: Path, rel: str, shared_name: str | None = None) -> Path:
    """Prefer the operator's shared copy (paper_logs/<name>) over this
    checkout's local file when the shared one is newer. On the operator PC
    the local file is the newest by construction; in the research checkout
    the local copies are stale scratch and paper_logs is the truth.

    ``shared_name`` overrides the paper_logs basename when the shared copy is
    deliberately renamed (e.g. multiple sources sharing the same local
    basename "ledger.csv" get distinct paper_logs names like on1_ledger.csv /
    onr_ledger.csv). Defaults to rel's own basename."""
    local = root / rel
    shared = root / "paper_logs" / (shared_name or Path(rel).name)
    try:
        s_m = shared.stat().st_mtime
    except OSError:
        return local
    try:
        l_m = local.stat().st_mtime
    except OSError:
        return shared
    return shared if s_m > l_m else local


def champion_gate(root: Path, now: float) -> dict[str, Any]:
    """G1: SETTLED — judged FAIL at n=30 (report #22); collection continues.

    The closed-trade count is still measured the same way
    scripts/judge_gates.py:load_champion_trades counts it (see
    ``_champion_summary``) — full-log positional entry/exit pairing at
    ``CHAMPION_LOG_MAX_BYTES``, not market_view's 4 MB console tail — because
    the paper run keeps feeding the C2 subset. But the ROW is a verdict, not a
    progress bar: the ``verdict*`` keys carry the report-#22 outcome and the
    page renders those instead of "n of 30". The verdict itself is a recorded
    fact (§3/§5), not something this module computes.
    """
    path = shared_or_local(root, "logs/bot.jsonl")
    summary = cached_scan("champion", path, lambda: _champion_summary(path))
    open_now = 1 if summary["open_at_end"] else 0
    g = progress(
        "champion", "チャンピオン判定 (§5)",
        have=summary["closed"], need=MAIN_TRADES_BAR, unit="trades",
        first_ts=summary["first_entry_ts"], now=now,
        bar=f">= {MAIN_TRADES_BAR} 決済済みトレード (判定済み)",
        age_sec=(now - summary["last_exit_ts"]) if summary["last_exit_ts"] else None,
        detail=f"建玉中 {open_now}件")
    g["verdict"] = CHAMPION_VERDICT
    g["verdict_detail"] = CHAMPION_VERDICT_DETAIL
    g["verdict_note"] = CHAMPION_VERDICT_NOTE
    return g


def c2_gate(root: Path, now: float,
            radar: StormRadar | None = None) -> dict[str, Any]:
    """G4a sample size: champion trades ENTERED inside the radar window.

    The subset is taken exactly as scripts/judge_gates.py:gates_subsets takes
    it — closed round trips whose entry_ts falls inside StormRadar's window
    (half-open [12:30, 15:00) UTC by default, the same defaults
    config/composite.yaml registers) — over the same full-log reconstruction
    the champion gate uses, so the two consoles cannot disagree on n.
    """
    path = shared_or_local(root, "logs/bot.jsonl")
    summary = cached_scan("champion", path, lambda: _champion_summary(path))
    radar = radar if radar is not None else StormRadar()
    inside = [(entry, exit_ts) for entry, exit_ts in summary["closed_spans"]
              if entry is not None and radar.is_armed(entry)]
    entries = [entry for entry, _ in inside]
    exits = [exit_ts for _, exit_ts in inside if exit_ts is not None]
    return progress(
        "c2", "C2 窓内サブセット", have=len(inside), need=C2_TRADES_BAR,
        unit="trades", first_ts=min(entries) if entries else None, now=now,
        bar=f">= {C2_TRADES_BAR} 窓内決済済みトレード (composite.yaml)",
        age_sec=(now - max(exits)) if exits else None,
        detail=f"窓 {radar.window} / 全{summary['closed']}件中")


def oi_gate(root: Path, now: float) -> dict[str, Any]:
    """G6 coverage: rows in data/oi_snapshots.csv (15-min cadence)."""
    path = shared_or_local(root, "data/oi_snapshots.csv")
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
    span_days, first_ts, last_end, total, count = _ws_span(root, files)
    return progress(
        "board", "板記録 (WS)", have=span_days, need=BOARD_DAYS_BAR,
        unit="days", first_ts=first_ts, now=now,
        bar=f">= {BOARD_DAYS_BAR:.0f}日 かつ >= {BOARD_BYTES_BAR / 1e9:.1f}GB",
        age_sec=(now - last_end) if last_end is not None else None,
        detail=f"{total / 1e6:.1f} MB / {count}ファイル",
        extra_have=total, extra_need=BOARD_BYTES_BAR)


def _ws_span(root: Path, files: Iterable[Path] | None
             ) -> tuple[float, float | None, float | None, int, int]:
    """(span_days, first_ts, last_end, total_bytes, n_files) over data/ws.

    First-file stamped start to last-file mtime — the SAME upper-bound reading
    judge_gates' G7 uses; shared by board_gate and spreadmm_gate so the two
    rows can never measure the recordings differently.
    """
    if files is None:
        ws_dir = root / "data" / "ws"
        files = sorted(ws_dir.glob("*.jsonl.gz")) if ws_dir.is_dir() else []
        listed = _ws_span_from_listing(root / "paper_logs" / "ws_listing.txt")
        # The recordings themselves are too large for git; the operator PC
        # shares only a directory listing. When that listing knows more files
        # than this checkout holds, it is the truth about coverage.
        if listed is not None and listed[4] > len(files):
            return listed
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
    return (span_days, min(starts) if starts else None,
            max(ends) if ends else None, total, len(files))


def _ws_span_from_listing(path: Path
                          ) -> tuple[float, float | None, float | None, int, int] | None:
    """Same tuple as _ws_span, read from a Windows `dir` listing of data/ws
    (share_logs.bat writes it, cp932). Start = UTC stamp in the filename,
    end = the listed mtime (local JST, converted), size = the listed bytes."""
    try:
        text = path.read_bytes().decode("cp932", errors="replace")
    except OSError:
        return None
    pat = re.compile(r"(\d{4})/(\d{2})/(\d{2})\s+(\d{2}):(\d{2})\s+([\d,]+)\s+"
                     r"(\S+_(\d{8})_(\d{6})\.jsonl\.gz)")
    starts: list[float] = []
    ends: list[float] = []
    total = 0
    for m in pat.finditer(text):
        y, mo, d, hh, mm, size, _name, ds, ts = m.groups()
        end_local = datetime(int(y), int(mo), int(d), int(hh), int(mm), tzinfo=timezone.utc)
        ends.append(end_local.timestamp() - 9 * 3600)          # JST -> UTC
        starts.append(datetime.strptime(ds + ts, "%Y%m%d%H%M%S")
                      .replace(tzinfo=timezone.utc).timestamp())
        total += int(size.replace(",", ""))
    if not starts:
        return None
    span_days = (max(ends) - min(starts)) / DAY_SEC
    return (span_days, min(starts), max(ends), total, len(starts))


def spreadmm_gate(root: Path, now: float,
                  files: Iterable[Path] | None = None) -> dict[str, Any]:
    """Spread-MM phase-2 countdown: data/ws must span 14 board days (§4).

    Report #26 moved the binding constraint from fill counts to DAILY
    statistics, keeping the required board days at 14 — this row is the
    countdown to that judgment. Same scan as board_gate (G7, the 7-day
    phase-1 bar), just a farther bar and no byte bar.
    """
    span_days, first_ts, last_end, total, count = _ws_span(root, files)
    return progress(
        "spreadmm", "スプレッドMM 判定 (板日数)", have=span_days,
        need=SPREADMM_BOARD_DAYS_BAR, unit="days", first_ts=first_ts, now=now,
        bar=f">= {SPREADMM_BOARD_DAYS_BAR:.0f}日 (フェーズ2判定、第26報)",
        age_sec=(now - last_end) if last_end is not None else None,
        detail=f"{total / 1e6:.1f} MB / {count}ファイル")


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
    """The gate rows, in the order the console shows them: the settled
    champion verdict first, then the pending coverage gates."""
    root = Path(root)
    # materialised once: two rows read the listing and it may be a generator
    files = list(ws_files) if ws_files is not None else None
    return [champion_gate(root, now),
            c2_gate(root, now),
            oi_gate(root, now),
            board_gate(root, now, files),
            spreadmm_gate(root, now, files),
            funding_gate(root, now)]

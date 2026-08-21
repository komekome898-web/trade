"""Aggregate all runtime state files into one dashboard payload.

Pure functions over the files the components already write — no new state,
no network. Everything degrades to None/empty when a file is missing.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from bot.radar import StormRadar


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _tail_jsonl(path: Path, n: int | None = None,
                max_bytes: int = 512 * 1024) -> list[dict]:
    """The last ``n`` JSON objects of a .jsonl file (all of them when n is None),
    read from at most ``max_bytes`` of tail. Missing file -> []. Shared with
    bot.monitoring.market_view, which reads a larger tail and wants every
    record rather than a fixed count."""
    try:
        size = path.stat().st_size
        with open(path, "rb") as f:
            f.seek(max(0, size - max_bytes))
            chunk = f.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    lines = chunk.splitlines()
    if len(lines) and size > max_bytes:
        lines = lines[1:]  # drop the partial first line
    out = []
    for line in (lines if n is None else lines[-n:]):
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def _file_info(path: Path, now: float) -> dict | None:
    try:
        st = path.stat()
    except OSError:
        return None
    return {"size": st.st_size, "age_sec": round(now - st.st_mtime, 1)}


def _last_csv_row(path: Path, max_bytes: int = 8192) -> dict[str, str] | None:
    """Header + last non-empty line of a small CSV, without reading it all.

    Used for data/oi_snapshots.csv (scripts/record_oi.py appends one row per
    collector run). Returns None when the file is missing, header-only or
    unreadable.
    """
    try:
        size = path.stat().st_size
        with open(path, "rb") as f:
            header = f.readline().decode("utf-8", errors="replace")
            f.seek(max(f.tell(), size - max_bytes))
            tail = f.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    cols = [c.strip() for c in header.strip().split(",") if c.strip()]
    lines = [ln for ln in tail.splitlines() if ln.strip()]
    if not cols or not lines:
        return None
    values = lines[-1].split(",")
    if len(values) != len(cols):
        return None
    return {c: v.strip() for c, v in zip(cols, values)}


def _oi_snapshot(path: Path, now: float) -> dict[str, Any] | None:
    """Freshness + values of the newest data/oi_snapshots.csv row."""
    info = _file_info(path, now)
    if info is None:
        return None
    row = _last_csv_row(path)
    row_age = None
    if row and row.get("ts_utc"):
        try:
            row_age = round(now - datetime.fromisoformat(row["ts_utc"]).timestamp(), 1)
        except ValueError:
            row_age = None
    return {
        "size": info["size"],
        # file mtime age; row_age is the age of the snapshot the row records
        "age_sec": info["age_sec"],
        "row_age_sec": row_age,
        "last": row,
    }


def _percentile(values: list[float], q: float) -> float:
    """Nearest-rank percentile over an already-sorted-able list."""
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round(q * (len(ordered) - 1)))
    return ordered[max(0, min(idx, len(ordered) - 1))]


def _api_health(path: Path, now: float, status: dict,
                window_sec: float = 900.0,
                max_bytes: int = 512 * 1024) -> dict[str, Any] | None:
    """Latency/error picture of the bot's own API calls (data/api_health.csv).

    The file is a plain append of one line per call written best-effort by
    bot.exchange.resilience.ApiHealthRecorder, so parsing is line-tolerant: a
    torn or short line is skipped, never fatal. Falls back to the live fields
    in status.json when the CSV is missing — condition and health are known
    there too; only the percentiles need the file.
    """
    rows: list[tuple[float, float, str, str, str]] = []
    try:
        size = path.stat().st_size
        with open(path, "rb") as f:
            f.seek(max(0, size - max_bytes))
            chunk = f.read().decode("utf-8", errors="replace")
    except OSError:
        chunk = ""
    cutoff = now - window_sec
    for line in chunk.splitlines():
        parts = line.split(",")
        if len(parts) < 7:
            continue
        try:
            ts = float(parts[0])
            latency = float(parts[3])
        except ValueError:
            continue          # header line or a torn append
        if ts < cutoff:
            continue
        rows.append((ts, latency, parts[4], parts[5], parts[6].strip()))
    if not rows and not status:
        return None
    if not rows:
        return {
            "p50_ms": None, "p95_ms": None, "error_rate": status.get("api_error_rate"),
            "samples": 0, "window_sec": window_sec,
            "condition": status.get("api_condition", "NORMAL"),
            "health": status.get("api_health_status"),
        }
    latencies = [r[1] for r in rows]
    errors = sum(1 for r in rows if r[2] != "ok")
    last = rows[-1]
    return {
        "p50_ms": round(_percentile(latencies, 0.50), 1),
        "p95_ms": round(_percentile(latencies, 0.95), 1),
        "error_rate": round(errors / len(rows), 4),
        "samples": len(rows),
        "window_sec": window_sec,
        # The live monitor is authoritative for the level; the CSV's last row
        # is the fallback for when the bot is not currently running.
        "condition": status.get("api_condition") or last[3],
        "health": status.get("api_health_status") or (last[4] or None),
    }


def _liveness(age_sec: float | None, warn_after: float, dead_after: float) -> str:
    if age_sec is None:
        return "missing"
    if age_sec < warn_after:
        return "ok"
    if age_sec < dead_after:
        return "warn"
    return "down"


def collect_status(root: str | Path = ".", now: float | None = None) -> dict[str, Any]:
    root = Path(root)
    now = now or time.time()

    status = _read_json(root / "logs" / "status.json") or {}
    kill = _read_json(root / "data" / "kill_switch.json")
    manual_kill = (root / "KILL").exists()

    decisions = [d for d in _tail_jsonl(root / "logs" / "bot.jsonl", 400)
                 if d.get("event") == "decision" or d.get("strategy_signal")]

    scalp_events = _tail_jsonl(root / "data" / "scalp_paper.jsonl", 400)
    scalp_trades = [e for e in scalp_events if e.get("event") == "exit"]
    scalp_pnl = round(sum(t.get("pnl_jpy", 0.0) for t in scalp_trades), 1)
    scalp_last = scalp_events[-1] if scalp_events else None

    ws_dir = root / "data" / "ws"
    ws_files = sorted(ws_dir.glob("*.jsonl.gz")) if ws_dir.exists() else []
    ws_latest = _file_info(ws_files[-1], now) if ws_files else None
    ws_total_mb = round(sum(f.stat().st_size for f in ws_files) / 1e6, 1) if ws_files else 0.0

    collectors = {}
    for label, rel in [
        ("bitFlyer candles", "data/candles_FX_BTC_JPY.csv"),
        ("Binance 1m", "data/binance_BTCUSDT_1m.csv"),
        ("bitbank 1m", "data/bitbank_xrp_jpy_1m.csv"),
        ("spread record", "data/spread_FX_BTC_JPY.csv"),
    ]:
        collectors[label] = _file_info(root / rel, now)

    oi_snapshot = _oi_snapshot(root / "data" / "oi_snapshots.csv", now)

    bot_age = (now - status["updated_at"]) if status.get("updated_at") else None
    scalp_age = (now - scalp_last["ts"]) if scalp_last else None
    ws_age = ws_latest["age_sec"] if ws_latest else None

    return {
        "generated_at": now,
        "components": {
            "main_bot": {
                "state": ("killed" if (kill or manual_kill) else
                          _liveness(bot_age, 30, 120)),
                "age_sec": round(bot_age, 1) if bot_age is not None else None,
            },
            # retired 2026-08-21 after the formal paper rejection (report
            # #16, -3.83bps vs the +5bps bar); start_all no longer launches
            # it. The pill stays as a record, not a liveness signal.
            "scalper": {
                "state": "retired",
                "age_sec": round(scalp_age, 1) if scalp_age is not None else None,
            },
            "ws_recorder": {"state": _liveness(ws_age, 300, 1200),
                            "age_sec": ws_age},
        },
        "bot": status,
        # Composite telemetry, surfaced beside the bot block instead of buried
        # in it. Both stay None under a strategy that has no overlay / no
        # module framework (xborder_momentum), which is not the same as an
        # overlay sitting at full size or an empty enabled-module list.
        "overlay": status.get("overlay"),
        "active_modules": status.get("active_modules"),
        # Execution resilience: how bitFlyer is actually answering us right
        # now, and how it answered over the last 15 minutes. This is the tile
        # that would have shown the 2019 failure mode while it was happening.
        "api_health": _api_health(root / "data" / "api_health.csv", now, status),
        "kill_switch": kill,
        "manual_kill_file": manual_kill,
        "decisions": decisions[-30:][::-1],
        "scalp": {
            "trades": len(scalp_trades),
            "total_pnl_jpy": scalp_pnl,
            "recent": scalp_events[-30:][::-1],
        },
        "ws": {"files": len(ws_files), "total_mb": ws_total_mb, "latest": ws_latest},
        "collectors": collectors,
        # storm radar: the one adopted precursor (scripts/research_storm_b.py
        # G3, 12:30-15:00 UTC, lift 2.23) — armed windows are when the
        # scalper runs its lowered entry threshold
        "radar": StormRadar().state(now),
        "oi_snapshot": oi_snapshot,
    }

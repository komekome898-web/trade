"""Aggregate all runtime state files into one dashboard payload.

Pure functions over the files the components already write — no new state,
no network. Everything degrades to None/empty when a file is missing.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _tail_jsonl(path: Path, n: int, max_bytes: int = 512 * 1024) -> list[dict]:
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
    for line in lines[-n:]:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def _file_info(path: Path, now: float) -> dict | None:
    try:
        st = path.stat()
    except OSError:
        return None
    return {"size": st.st_size, "age_sec": round(now - st.st_mtime, 1)}


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
            # the scalper logs only on events, so a long quiet spell is normal
            "scalper": {
                "state": "killed" if manual_kill else
                         ("ok" if scalp_last else "missing"),
                "age_sec": round(scalp_age, 1) if scalp_age is not None else None,
            },
            "ws_recorder": {"state": _liveness(ws_age, 300, 1200),
                            "age_sec": ws_age},
        },
        "bot": status,
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
    }

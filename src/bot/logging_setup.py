"""Structured JSON logging with secret redaction.

Every trading decision is logged via `log_decision` with the full field set
required for after-the-fact auditing of "why did the bot place this order".
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SECRET_PATTERNS: list[re.Pattern] = []


def register_secret(value: str) -> None:
    """Register a secret so it is redacted from every log line."""
    if value and len(value) >= 6:
        _SECRET_PATTERNS.append(re.compile(re.escape(value)))


def _redact(text: str) -> str:
    for pat in _SECRET_PATTERNS:
        text = pat.sub("***REDACTED***", text)
    return text


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "data", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return _redact(json.dumps(payload, ensure_ascii=False, default=str))


def setup_logging(log_dir: str | Path = "logs", level: int = logging.INFO) -> logging.Logger:
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger("bot")
    root.setLevel(level)
    root.handlers.clear()

    fh = logging.FileHandler(log_dir / "bot.jsonl", encoding="utf-8")
    fh.setFormatter(JsonFormatter())
    root.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setFormatter(JsonFormatter())
    root.addHandler(sh)
    return root


def log_decision(
    logger: logging.Logger,
    *,
    symbol: str,
    price: float | None,
    strategy_signal: str,
    indicator_values: dict[str, float],
    decision: str,
    order_size: float | None = None,
    order_price: float | None = None,
    order_id: str | None = None,
    execution_price: float | None = None,
    execution_status: str | None = None,
    pnl: float | None = None,
    reason: str = "",
) -> None:
    logger.info(
        "decision",
        extra={
            "data": {
                "event": "decision",
                "symbol": symbol,
                "price": price,
                "strategy_signal": strategy_signal,
                "indicator_values": indicator_values,
                "decision": decision,
                "order_size": order_size,
                "order_price": order_price,
                "order_id": order_id,
                "execution_price": execution_price,
                "execution_status": execution_status,
                "PnL": pnl,
                "reason": reason,
            }
        },
    )

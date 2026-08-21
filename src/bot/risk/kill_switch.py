"""Kill switch: once tripped, trading stops and does NOT auto-resume.

The tripped state is persisted to a file so a process restart (systemd etc.)
cannot silently resume trading — a human must remove the file / call reset.
Manual trip: create a file named KILL in the working directory.

`detail` is written to disk and surfaced in status.json and operator alerts, so
it goes through the SAME redaction filter as the logs (`logging_setup.redact`):
a trip reason is usually an exception string, and an exception string is one of
the likeliest places for a signed URL or an API key to appear.
"""
from __future__ import annotations

import json
import time
from enum import Enum
from pathlib import Path

from bot.logging_setup import redact


class KillReason(Enum):
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    MAX_DRAWDOWN = "max_drawdown"
    CONSECUTIVE_LOSSES = "consecutive_losses"
    API_ERRORS = "api_errors"
    ORDER_STATE_UNKNOWN = "order_state_unknown"
    MARKET_DATA_ANOMALY = "market_data_anomaly"
    SYSTEM_ERROR = "system_error"
    UNHANDLED_EXCEPTION = "unhandled_exception"
    MANUAL = "manual"


class KillSwitch:
    def __init__(self, state_dir: str | Path = "data", manual_file: str | Path = "KILL"):
        self._state_file = Path(state_dir) / "kill_switch.json"
        self._manual_file = Path(manual_file)
        self._tripped: dict | None = None
        self._load()

    def _load(self) -> None:
        if self._state_file.exists():
            try:
                self._tripped = json.loads(self._state_file.read_text(encoding="utf-8"))
            except Exception:
                # Unreadable state file: fail safe — treat as tripped.
                self._tripped = {"reason": KillReason.SYSTEM_ERROR.value,
                                 "detail": "unreadable kill switch state file"}

    def trip(self, reason: KillReason, detail: str = "") -> None:
        self._tripped = {"reason": reason.value, "detail": redact(str(detail)),
                         "time": time.time()}
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state_file.write_text(json.dumps(self._tripped), encoding="utf-8")

    @property
    def is_tripped(self) -> bool:
        if self._manual_file.exists() and self._tripped is None:
            self.trip(KillReason.MANUAL, f"manual kill file present: {self._manual_file}")
        return self._tripped is not None

    @property
    def state(self) -> dict | None:
        return self._tripped

    def reset(self, operator_confirm: bool = False) -> None:
        """Explicit human action required; never called by trading code."""
        if not operator_confirm:
            raise PermissionError("kill switch reset requires operator_confirm=True")
        self._tripped = None
        if self._state_file.exists():
            self._state_file.unlink()
        if self._manual_file.exists():
            self._manual_file.unlink()

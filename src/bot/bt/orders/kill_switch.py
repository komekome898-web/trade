"""The backtest kill switch (CLAUDE.md section 1: it never resumes on its own).

Once tripped, every new order the order client is asked to place is refused
locally (`KillSwitchEngaged`) and never sent to the venue. The tripped state
does not clear on its own: `reset(operator_confirm=True)` is the only way back,
and a state file, when one is given, keeps the switch tripped across a new
process (the live bot's `bot.risk.kill_switch` keeps its state the same way).
`state_file` is required: pass None for an in-memory switch (one run).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union

from .errors import ExecutionModelError


class KillSwitch:
    def __init__(self, state_file: Optional[Union[str, Path]]) -> None:
        self._file = None if state_file is None else Path(state_file)
        self._tripped: Optional[dict] = None
        if self._file is not None and self._file.exists():
            try:
                self._tripped = json.loads(self._file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                # unreadable state: fail safe, stay tripped
                self._tripped = {"reason": "unreadable kill switch state file", "time_ns": None}

    @property
    def is_tripped(self) -> bool:
        return self._tripped is not None

    @property
    def reason(self) -> Optional[str]:
        return None if self._tripped is None else str(self._tripped.get("reason"))

    def trip(self, reason: str, time_ns: Optional[int]) -> None:
        if type(reason) is not str or not reason:
            raise ExecutionModelError("a kill switch trip needs a non-empty reason")
        if self._tripped is not None:
            return  # already tripped: the first reason is kept
        self._tripped = {"reason": reason, "time_ns": time_ns}
        if self._file is not None:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            self._file.write_text(json.dumps(self._tripped), encoding="utf-8")

    def reset(self, *, operator_confirm: bool) -> None:
        """Only a human clears the switch, after investigating the cause."""
        if operator_confirm is not True:
            raise ExecutionModelError("kill switch reset needs operator_confirm=True")
        self._tripped = None
        if self._file is not None and self._file.exists():
            self._file.unlink()

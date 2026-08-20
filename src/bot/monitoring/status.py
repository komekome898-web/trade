"""Bot status tracking: writes logs/status.json continuously so operators
(and external monitors) can see the live state at any time."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class BotStatus:
    mode: str = "paper"
    running: bool = False
    api_connected: bool = False
    last_price: float | None = None
    balance_jpy: float | None = None
    position_size: float = 0.0
    daily_pnl_jpy: float = 0.0
    total_pnl_jpy: float = 0.0
    max_drawdown_pct: float = 0.0
    last_order: str | None = None
    last_execution: str | None = None
    error_count: int = 0
    consecutive_api_errors: int = 0
    last_data_time: float | None = None
    kill_switch: dict | None = None
    updated_at: float = field(default_factory=time.time)


class StatusWriter:
    def __init__(self, path: str | Path = "logs/status.json", clock=time.time):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._clock = clock
        self.status = BotStatus()

    def write(self) -> None:
        self.status.updated_at = self._clock()
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self.status), ensure_ascii=False, indent=2),
                       encoding="utf-8")
        tmp.replace(self._path)

    def format_report(self) -> str:
        s = self.status
        return (
            f"mode={s.mode} running={s.running} api={'OK' if s.api_connected else 'NG'}\n"
            f"price={s.last_price} balance={s.balance_jpy} position={s.position_size}\n"
            f"daily_pnl={s.daily_pnl_jpy:.1f} total_pnl={s.total_pnl_jpy:.1f} "
            f"max_dd={s.max_drawdown_pct:.2f}%\n"
            f"errors={s.error_count} kill_switch={s.kill_switch}"
        )

"""Bot status tracking: writes logs/status.json continuously so operators
(and external monitors) can see the live state at any time."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

from bot.atomic_file import atomic_write_text


@dataclass
class BotStatus:
    mode: str = "paper"
    running: bool = False
    api_connected: bool = False
    last_price: float | None = None
    balance_jpy: float | None = None
    position_size: float = 0.0
    # Average entry of the OPEN position (JPY), None while flat. The console
    # shows it beside the size — a position tile without it says the bot is
    # long but not whether it is in profit, which is the first thing the owner
    # looks for.
    entry_price: float | None = None
    # Fills booked by the paper book (an entry and its exit are two), carried
    # across restarts by data/paper_state.json — not a per-process counter.
    trade_count: int = 0
    daily_pnl_jpy: float = 0.0
    # realized (cumulative, all sessions) + unrealized at the current mark;
    # balance_jpy is the same number plus the book's initial equity
    total_pnl_jpy: float = 0.0
    max_drawdown_pct: float = 0.0
    last_order: str | None = None
    last_execution: str | None = None
    error_count: int = 0
    consecutive_api_errors: int = 0
    last_data_time: float | None = None
    kill_switch: dict | None = None
    # Composite-strategy telemetry; None when the running strategy has neither
    # (bot/main.py: _overlay_status / _active_module_names).
    overlay: dict | None = None            # {factor, consecutive_losses, dd_pct}
    active_modules: list | None = None     # [] = framework on, nothing enabled
    # Execution resilience (bot/exchange/resilience.py). `api_condition` is the
    # hysteretic NORMAL/DEGRADED/CRITICAL level, `api_health_status` the raw
    # /v1/gethealth string. The 15-minute latency percentiles live in
    # data/api_health.csv and are computed by monitoring/aggregate.py.
    api_condition: str = "NORMAL"
    # None once the reading has expired (3x the poll interval): a health string
    # that stopped being refreshed is not evidence about the venue, and
    # `api_health_age_sec` says how long ago it last was.
    api_health_status: str | None = None
    api_health_age_sec: float | None = None
    api_latency_ms: float | None = None    # EWMA of this bot's own calls
    api_error_rate: float | None = None
    updated_at: float = field(default_factory=time.time)


class StatusWriter:
    def __init__(self, path: str | Path = "logs/status.json", clock=time.time):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._clock = clock
        self.status = BotStatus()

    def write(self) -> None:
        """Best-effort status telemetry — must NEVER take down trading.

        The retry-and-fall-back write itself is shared with the two other
        state files (bot/atomic_file.py)."""
        self.status.updated_at = self._clock()
        payload = json.dumps(asdict(self.status), ensure_ascii=False, indent=2)
        atomic_write_text(self._path, payload)

    def format_report(self) -> str:
        s = self.status
        return (
            f"mode={s.mode} running={s.running} api={'OK' if s.api_connected else 'NG'}\n"
            f"price={s.last_price} balance={s.balance_jpy} position={s.position_size}\n"
            f"daily_pnl={s.daily_pnl_jpy:.1f} total_pnl={s.total_pnl_jpy:.1f} "
            f"max_dd={s.max_drawdown_pct:.2f}% trades={s.trade_count}\n"
            f"errors={s.error_count} kill_switch={s.kill_switch}"
        )

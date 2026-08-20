"""Configuration loading and trading-mode resolution.

Safety model:
- PAPER mode is the default. LIVE mode requires BOTH `LIVE_MODE=true` in the
  environment AND `live_mode_ack: "I_UNDERSTAND_REAL_MONEY"` in config.yaml.
- Secrets come only from environment variables (.env), never from YAML,
  and are wrapped so accidental str()/repr()/logging shows a masked value.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

LIVE_ACK_PHRASE = "I_UNDERSTAND_REAL_MONEY"


class Mode(Enum):
    PAPER = "paper"
    LIVE = "live"


class Secret:
    """Holds a secret string; str()/repr() never reveal it."""

    def __init__(self, value: str):
        self._value = value or ""

    def reveal(self) -> str:
        return self._value

    def __bool__(self) -> bool:
        return bool(self._value)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return "***MASKED***"

    __repr__ = __str__


class ModeConfigError(Exception):
    """Raised when the requested trading mode is not safely configured."""


def _as_bool(value: str | None) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on")


@dataclass
class RiskLimits:
    max_order_size_jpy: float
    max_position_size_jpy: float
    max_daily_loss_jpy: float
    max_drawdown_pct: float
    max_open_orders: int
    max_consecutive_losses: int
    max_api_errors_in_row: int

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RiskLimits":
        return cls(
            max_order_size_jpy=float(d["MAX_ORDER_SIZE_JPY"]),
            max_position_size_jpy=float(d["MAX_POSITION_SIZE_JPY"]),
            max_daily_loss_jpy=float(d["MAX_DAILY_LOSS_JPY"]),
            max_drawdown_pct=float(d["MAX_DRAWDOWN_PCT"]),
            max_open_orders=int(d["MAX_OPEN_ORDERS"]),
            max_consecutive_losses=int(d["MAX_CONSECUTIVE_LOSSES"]),
            max_api_errors_in_row=int(d["MAX_API_ERRORS_IN_ROW"]),
        )


@dataclass
class Settings:
    mode: Mode
    product_code: str
    config: dict[str, Any]
    risk_limits: RiskLimits
    api_key: Secret = field(repr=False, default_factory=lambda: Secret(""))
    api_secret: Secret = field(repr=False, default_factory=lambda: Secret(""))
    discord_webhook_url: Secret = field(repr=False, default_factory=lambda: Secret(""))

    @property
    def is_live(self) -> bool:
        return self.mode is Mode.LIVE


def resolve_mode(env: dict[str, str], config: dict[str, Any]) -> Mode:
    """Resolve trading mode. Defaults to PAPER; refuses ambiguous/half-armed LIVE."""
    paper = _as_bool(env.get("PAPER_MODE", "true"))
    live = _as_bool(env.get("LIVE_MODE"))
    ack = str(config.get("live_mode_ack") or "")

    if not live:
        if ack == LIVE_ACK_PHRASE:
            raise ModeConfigError(
                "config.yaml contains the live-mode ack but LIVE_MODE is not set. "
                "Remove the ack or set LIVE_MODE=true explicitly. Refusing to start."
            )
        return Mode.PAPER
    # live requested
    if paper:
        raise ModeConfigError(
            "Both PAPER_MODE and LIVE_MODE are true. Ambiguous configuration; refusing to start."
        )
    if ack != LIVE_ACK_PHRASE:
        raise ModeConfigError(
            "LIVE_MODE=true but config.yaml live_mode_ack is missing/incorrect. "
            f'Set live_mode_ack: "{LIVE_ACK_PHRASE}" only when real-money trading is approved.'
        )
    return Mode.LIVE


def load_settings(
    root: str | Path = ".",
    env: dict[str, str] | None = None,
) -> Settings:
    root = Path(root)
    load_dotenv(root / ".env")
    if env is None:
        env = dict(os.environ)

    # encoding pinned: Windows defaults to cp932 which breaks UTF-8 configs
    with open(root / "config" / "config.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    with open(root / "config" / "risk_limits.yaml", encoding="utf-8") as f:
        limits = RiskLimits.from_dict(yaml.safe_load(f))

    mode = resolve_mode(env, config)
    return Settings(
        mode=mode,
        product_code=str(config.get("product_code", "XRP_JPY")),
        config=config,
        risk_limits=limits,
        api_key=Secret(env.get("BITFLYER_API_KEY", "")),
        api_secret=Secret(env.get("BITFLYER_API_SECRET", "")),
        discord_webhook_url=Secret(env.get("DISCORD_WEBHOOK_URL", "")),
    )

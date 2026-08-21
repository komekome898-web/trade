"""Paper-mode book state, persisted so a restart is continuous.

PAPER ONLY. In LIVE mode the exchange holds the book and the app reconciles
against it; nothing here is read or written there (bot/main.py).

Why this file exists
--------------------
The paper portfolio used to live in memory only, so every restart — including
a watchdog restart nobody noticed — handed the next process a fresh 200,000
JPY book: the console jumped back to its starting numbers, an OPEN paper
position was silently forgotten (the experiment it belongs to is then
unreadable), and the spent MAX_DAILY_LOSS_JPY budget came back full in the
middle of the same trading day. The last one is a safety brake resetting
itself, the same failure class as the scalper's daily-stop marker, and the
same reason the kill switch persists.

data/paper_state.json
---------------------
* `realized_pnl_jpy` — cumulative realized P&L of the paper book, fees
  included (Portfolio books fees into realized).
* `trade_count` — cumulative FILLS booked (an entry and its exit are two).
* `daily_pnl_jpy` — today's REALIZED P&L only. Unrealized is deliberately not
  stored: it is recomputed from the live mark on the next tick, and saving it
  would double-count it after a restart.
* `daily_date` — the UTC date `daily_pnl_jpy` belongs to. On boot the daily
  figure is restored only when this still names today; otherwise the day has
  rolled and the brake starts fresh at 0.
* `position` — the open position (`side` / `size` / `entry_price` /
  `opened_ts`), or null when flat.

What is NOT here, on purpose: the equity peak and the consecutive-loss streak.
The overlay's own brake state is `data/overlay_state.json` (relative drawdown,
reconstructed against boot equity) and duplicating it here would give the two
files room to disagree; the PORTFOLIO's peak and streak feed the hard
pre-trade checks and must stay facts about what this process traded — see
bot/strategy/composite.py's module docstring for why seeding those from disk
deadlocks the kill switch.

A missing file is a normal first start. A corrupt one degrades to the same
fresh defaults with one warning: this is bookkeeping, not an authorisation, so
losing it must never stop the bot from running.
"""
from __future__ import annotations

import json
import logging
import math
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

PAPER_STATE_PATH = Path("data") / "paper_state.json"


def utc_date(ts: float) -> str:
    """UTC calendar date of a unix timestamp, as YYYY-MM-DD.

    The single place a timestamp becomes a "trading day" for this file.
    Portfolio anchors its daily P&L to `int(ts // 86400)`, which is the same
    UTC midnight boundary — the caller passes the PORTFOLIO's clock in here so
    the two can never drift into two different days.
    """
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%Y-%m-%d")


def _finite(value: object, name: str) -> float:
    number = float(value)  # type: ignore[arg-type]
    if not math.isfinite(number):
        raise ValueError(f"{name} is not finite: {number}")
    return number


@dataclass
class PaperPosition:
    """An open paper position, as stored. `size` is ABSOLUTE and the direction
    is the explicit `side`, so a hand-read of the file cannot mistake a sign."""

    side: str            # LONG / SHORT
    size: float          # absolute, > 0
    entry_price: float   # average entry (JPY)
    opened_ts: float     # unix time the book went from flat to this position

    @property
    def signed_size(self) -> float:
        """Portfolio's signed convention: > 0 long, < 0 short."""
        return self.size if self.side == "LONG" else -self.size

    @classmethod
    def from_signed(cls, signed_size: float, entry_price: float,
                    opened_ts: float) -> "PaperPosition":
        return cls(side="LONG" if signed_size > 0 else "SHORT",
                   size=abs(float(signed_size)), entry_price=float(entry_price),
                   opened_ts=float(opened_ts))

    def to_dict(self) -> dict:
        return {"side": self.side, "size": self.size,
                "entry_price": self.entry_price, "opened_ts": self.opened_ts}

    @classmethod
    def from_dict(cls, raw: object) -> "PaperPosition":
        """Strict: anything unreadable raises and the whole state degrades to
        the flat default. A half-understood position is worse than none."""
        if not isinstance(raw, dict):
            raise ValueError(f"position is not a mapping: {type(raw).__name__}")
        side = str(raw["side"])
        if side not in ("LONG", "SHORT"):
            raise ValueError(f"unknown position side: {side!r}")
        size = _finite(raw["size"], "size")
        entry_price = _finite(raw["entry_price"], "entry_price")
        if size <= 0 or entry_price <= 0:
            raise ValueError(f"non-positive size/entry_price: {size}/{entry_price}")
        return cls(side=side, size=size, entry_price=entry_price,
                   opened_ts=_finite(raw.get("opened_ts", 0.0), "opened_ts"))


@dataclass
class PaperState:
    """The paper book as persisted. Defaults are a fresh book."""

    realized_pnl_jpy: float = 0.0
    trade_count: int = 0
    daily_pnl_jpy: float = 0.0     # realized only; see module docstring
    daily_date: str = ""           # UTC YYYY-MM-DD the daily figure belongs to
    position: PaperPosition | None = None

    def daily_pnl_on(self, date: str) -> float:
        """Today's realized P&L, or 0.0 when the saved figure is another day's.

        The expiry is what makes carrying the daily brake across a restart safe:
        a spent budget is inherited for the rest of the SAME UTC day and clears
        itself at the rollover, so it can never wedge the bot permanently.
        """
        return self.daily_pnl_jpy if self.daily_date == date else 0.0

    def to_dict(self) -> dict:
        return {
            "realized_pnl_jpy": self.realized_pnl_jpy,
            "trade_count": self.trade_count,
            "daily_pnl_jpy": self.daily_pnl_jpy,
            "daily_date": self.daily_date,
            "position": self.position.to_dict() if self.position else None,
        }

    @classmethod
    def load(cls, path: str | Path = PAPER_STATE_PATH) -> "PaperState":
        """Read the book. Missing file -> fresh defaults, silently (that is a
        normal first start). Unreadable/corrupt -> fresh defaults and ONE
        warning, never an exception: a restart with a clean book is exactly the
        old behaviour, while crashing here would stop the bot over bookkeeping.
        """
        path = Path(path)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return cls()
        try:
            raw = json.loads(text)
            if not isinstance(raw, dict):
                raise ValueError(f"not a JSON object: {type(raw).__name__}")
            position = raw.get("position")
            trade_count = int(raw["trade_count"])
            if trade_count < 0:
                raise ValueError(f"negative trade_count: {trade_count}")
            return cls(
                realized_pnl_jpy=_finite(raw["realized_pnl_jpy"], "realized_pnl_jpy"),
                trade_count=trade_count,
                daily_pnl_jpy=_finite(raw["daily_pnl_jpy"], "daily_pnl_jpy"),
                daily_date=str(raw["daily_date"]),
                position=None if position is None else PaperPosition.from_dict(position),
            )
        except (ValueError, TypeError, KeyError) as exc:
            logger.warning("paper state unreadable; starting from a fresh book",
                           extra={"data": {"event": "paper_state_corrupt",
                                           "path": str(path), "error": str(exc)}})
            return cls()

    def save(self, path: str | Path = PAPER_STATE_PATH) -> None:
        """Best-effort atomic write (OverlayState.save / StatusWriter pattern):
        a bookkeeping checkpoint must never take trading down.

        On Windows os.replace fails with PermissionError while another process
        briefly holds the destination open; retry, then fall back to a direct
        write, and swallow any remaining OSError. The temp file is cleaned up so
        a failed replace does not leak one.
        """
        path = Path(path)
        payload = json.dumps(self.to_dict(), ensure_ascii=False)
        tmp = path.with_suffix(".tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(payload, encoding="utf-8")
            for _ in range(5):
                try:
                    os.replace(tmp, path)
                    return
                except PermissionError:
                    time.sleep(0.05)
            path.write_text(payload, encoding="utf-8")
        except OSError:
            pass
        finally:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass

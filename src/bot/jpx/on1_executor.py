"""ON1 live executor: 15:40 引成買い / 8:40 寄り成行売り, 1 micro contract.

docs/ON1_LIVE_PLAN.md L1.  The strategy is trivial; everything here is the
safety envelope around it.

HARD LIMITS — enforced in code, NOT reachable from config
---------------------------------------------------------
* position is always in {0, +1}: entry only from FLAT, exit only from LONG, and
  `Qty` is the module constant `MAX_QTY = 1`.  There is no code path that sends
  a sell that is not a 返済 of the one long, so a short is structurally
  impossible.
* at most `MAX_ORDERS_PER_DAY = 4` sends per calendar day (2 normal + 2 roll).
  The counter is persisted and incremented BEFORE the send, so an ambiguous
  failure still consumes its slot.
* every payload passes `_sanity_check` before it can be sent: symbol shape,
  micro instrument, contract month, side/TradeType matching the job, Qty == 1,
  Price == 0 on a market order.  A failed check does not send (fail-close).
* KILL file / data/kill_switch.json stops everything (bot/risk/kill_switch.py:
  file-persisted, no auto-resume).
* an ambiguous send failure parks the state machine in STATE_UNKNOWN.  While it
  is there NOTHING is sent; `reconcile()` uses read-only endpoints only (it is
  handed a `QueryOnlyKabu`, which has no send method at all).

LIVE DOUBLE GATE
----------------
`ON1_LIVE=true` in the environment AND `live_ack: "I_UNDERSTAND_REAL_MONEY_JPX"`
AND `enabled: true` in config/on1_live.yaml.  Missing any one of them means DRY
RUN: the payload is written to events.jsonl and nothing is sent — not even to
the 検証 port 18081.

SPEC ITEMS RECORDED AS 不明 (fail-close or explicitly flagged)
-------------------------------------------------------------
1. 寄成 (market-on-open) DOES NOT EXIST for derivatives.  The futures
   `FrontOrderType` table in kabu_STATION_API.yaml lists only 18 引成（派生） /
   20 指値 / 28 引指（派生） / 30 逆指値 / 120 成行; 13・14 寄成（前場/後場） are on
   the STOCK request schema only.  The 8:40 exit therefore sends a plain 成行
   (120, FAK, 日中) during the pre-open.  **不明**: the spec says nothing about
   whether an order accepted before 8:45 joins the opening auction, nor whether
   kabuステーション accepts orders at 8:40 at all.  Must be confirmed on port
   18081 before LIVE.  Not guessed around: if kabuステーション refuses it we get a
   definite 4xx, which is recorded as an alert and sends nothing further.
2. The micro 銘柄コード pattern is 不明 (the spec only shows 9-digit examples and
   never states the format).  So the code is never constructed — it is read from
   `GET /symbolname/future?FutureCode=NK225micro`, and the sanity check merely
   REFUSES anything that is not 9 digits with "マイクロ" in the returned
   SymbolName.  A tighter guess would be a guess.
3. The exact 取引最終日 of a contract month is not exposed by the API.  Instead of
   deriving one, entry is skipped for the whole week before the month's SQ
   (second Friday) — fail-close, at the cost of a few skipped days a year.
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from bot.jpx.kabu_client import (
    KabuError, KabuNetworkError, OrderStateUnknown, QueryOnlyKabu, VERIFICATION_PORT,
)
from bot.logging_setup import redact
from bot.risk.kill_switch import KillSwitch

logger = logging.getLogger("bot.jpx.on1")

# ---- hard limits (module constants; config cannot widen them) ---------------
MAX_QTY = 1
MAX_ORDERS_PER_DAY = 4
PRICE_BAND_PCT = 10.0          # entry-only board-vs-JPX-print sanity band
REFERENCE_MAX_AGE_DAYS = 5     # JPX daily report is T+1; a Monday sees Friday
SQ_BLACKOUT_DAYS = 7           # skip entry within a week of the month's SQ

# Windows the scheduler may fire in.  Config may narrow these, never widen them.
HARD_ENTRY_WINDOW = ("15:00", "15:44")
HARD_EXIT_WINDOW = ("08:00", "08:44")

# ---- kabusapi enum values (kabu_STATION_API.yaml, see kabu_client docstring) -
FUTURE_CODE_MICRO = "NK225micro"          # /symbolname/future FutureCode 日経225マイクロ先物
EXCHANGE_DAY_SESSION = 23                 # 市場コード 23 = 日中
TRADE_TYPE_NEW = 1                        # 取引区分 1 = 新規
TRADE_TYPE_CLOSE = 2                      # 取引区分 2 = 返済
SIDE_SELL = "1"                           # 売買区分 1 = 売
SIDE_BUY = "2"                            # 売買区分 2 = 買
TIME_IN_FORCE_FAK = 2                     # 有効期間条件 2 = FAK
FRONT_ORDER_TYPE_MARKET_ON_CLOSE = 18     # 執行条件 18 = 引成（派生）, TimeInForce は FAK のみ
FRONT_ORDER_TYPE_MARKET = 120             # 執行条件 120 = 成行（マーケットオーダー）
CLOSE_POSITION_ORDER_OLDEST = 0           # 決済順序 0 = 日付（古い順）、損益（高い順）
EXPIRE_DAY_TODAY = 0                      # 注文有効期限 0 = 「本日」

# 引成 and 成行 are both listed as 日中/夜間 only — NOT 日通し (TimeInForce table in
# RequestSendOrderDerivFuture).  ON1 trades the day session, so 23 it is.
_ALLOWED_EXCHANGES = (EXCHANGE_DAY_SESSION,)

MICRO_SYMBOL_RE = re.compile(r"[0-9]{9}")
MICRO_NAME_MARKER = "マイクロ"

LIVE_ACK_PHRASE = "I_UNDERSTAND_REAL_MONEY_JPX"

ENTRY = "entry"
EXIT = "exit"

FLAT = "FLAT"
LONG = "LONG"
STATE_UNKNOWN = "STATE_UNKNOWN"


class SanityError(Exception):
    """A pre-send check failed.  Nothing is sent (fail-close)."""


# ---------------------------------------------------------------------------
# config


@dataclass(frozen=True)
class On1Config:
    enabled: bool = False
    live_ack: str = ""
    port: int = VERIFICATION_PORT
    entry_window: tuple[str, str] = HARD_ENTRY_WINDOW
    exit_window: tuple[str, str] = HARD_EXIT_WINDOW
    problems: tuple[str, ...] = field(default_factory=tuple)


def _window(raw: Any, hard: tuple[str, str], name: str,
            problems: list[str]) -> tuple[str, str]:
    """A configured window may only NARROW the hard one."""
    if raw is None:
        return hard
    try:
        # re-formatted through strptime so "9:00" cannot defeat the string
        # comparison against the hard window below
        lo, hi = (datetime.strptime(str(raw[i]), "%H:%M").strftime("%H:%M")
                  for i in (0, 1))
    except Exception:
        problems.append(f"{name}={raw!r} is not a ['HH:MM','HH:MM'] pair")
        return hard
    if lo < hard[0] or hi > hard[1] or lo > hi:
        problems.append(f"{name}={raw!r} is outside the hard window {hard}")
        return hard
    return (lo, hi)


def load_on1_config(path: str | Path) -> On1Config:
    path = Path(path)
    problems: list[str] = []
    raw: dict = {}
    if path.exists():
        with open(path, encoding="utf-8") as f:      # cp932 default on Windows
            raw = yaml.safe_load(f) or {}
    else:
        problems.append(f"{path} is missing; staying disabled")
    enabled = raw.get("enabled", False)
    if not isinstance(enabled, bool):
        # STRICT, not bool(): a quoted "false" is truthy and would arm the gate.
        problems.append(f"enabled={enabled!r} is not a bare bool; staying disabled")
        enabled = False
    try:
        port = int(raw.get("port", VERIFICATION_PORT))
    except (TypeError, ValueError):
        problems.append(f"port={raw.get('port')!r} is not an integer")
        port = VERIFICATION_PORT
    return On1Config(
        enabled=enabled,
        live_ack=str(raw.get("live_ack") or ""),
        port=port,
        entry_window=_window(raw.get("entry_window"), HARD_ENTRY_WINDOW,
                             "entry_window", problems),
        exit_window=_window(raw.get("exit_window"), HARD_EXIT_WINDOW,
                            "exit_window", problems),
        problems=tuple(problems),
    )


def resolve_live(env: dict[str, str], config: On1Config) -> tuple[bool, str]:
    """The double gate.  Returns (live, reason).  Half-armed is DRY RUN, never
    live — and the reason names the missing half so it shows up in events.jsonl."""
    env_on = (env.get("ON1_LIVE") or "").strip().lower() in ("1", "true", "yes", "on")
    if not config.enabled:
        return False, "config on1_live.yaml enabled is not true"
    if config.live_ack != LIVE_ACK_PHRASE:
        return False, "config on1_live.yaml live_ack is missing/incorrect"
    if not env_on:
        return False, "env ON1_LIVE is not true"
    return True, "env ON1_LIVE + config live_ack + enabled"


# ---------------------------------------------------------------------------
# central contract month (same rule as scripts/paper_on1.py / PREREG §1)


def sq_date(month: str) -> date:
    """Nikkei 225 SQ = the second Friday of the contract month."""
    first = date(int(month[:4]), int(month[4:6]), 1)
    first_friday = first + timedelta(days=(4 - first.weekday()) % 7)
    return first_friday + timedelta(days=7)


def resolve_central_month(csv_path: str | Path, as_of: date,
                          max_age_days: int = REFERENCE_MAX_AGE_DAYS
                          ) -> tuple[str | None, dict | None, str | None]:
    """(month, reference row, reason it is unusable).

    Same rule as the paper ledger: the micro month with the largest day-session
    volume on the most recent session at or before `as_of`.  The row is also the
    price reference for the entry band check.
    """
    import csv as _csv

    path = Path(csv_path)
    if not path.exists():
        return None, None, "jpx sessions csv missing"
    by_date: dict[str, dict[str, dict]] = {}
    with path.open(encoding="utf-8") as f:
        for row in _csv.DictReader(f):
            if row.get("product") != "micro":
                continue
            by_date.setdefault(row["date"], {})[row["month"]] = row
    as_of_key = as_of.strftime("%Y%m%d")
    usable = sorted(d for d in by_date if d <= as_of_key)
    if not usable:
        return None, None, "no micro rows at or before today"
    latest = usable[-1]
    age = (as_of - datetime.strptime(latest, "%Y%m%d").date()).days
    if age > max_age_days:
        return None, None, f"reference stale ({age}d old, max {max_age_days})"
    best, best_vol = None, -1.0
    for month, row in by_date[latest].items():
        try:
            vol = float(row["day_volume"]) if row["day_volume"] else 0.0
        except (TypeError, ValueError):
            vol = 0.0
        if vol > best_vol:
            best, best_vol = month, vol
    if best is None:
        return None, None, "no micro month on the reference session"
    row = by_date[latest][best]
    if not row.get("day_close"):
        return None, None, f"reference close missing for {best}"
    return best, row, None


# ---------------------------------------------------------------------------
# state


class On1State:
    """data/on1_live/state.json.  Persisted so a process restart cannot resume
    trading from a forgotten STATE_UNKNOWN, exactly like the kill switch."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.data: dict = {"status": FLAT, "position": None, "unknown": None,
                           "orders": {"date": "", "count": 0}}
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                # Unreadable state: fail safe, park in STATE_UNKNOWN.
                loaded = {"status": STATE_UNKNOWN, "position": None,
                          "unknown": {"detail": "unreadable state file"},
                          "orders": {"date": "", "count": 0}}
            if isinstance(loaded, dict):
                self.data.update(loaded)

    # -- accessors
    @property
    def status(self) -> str:
        return str(self.data.get("status") or FLAT)

    @property
    def position(self) -> dict | None:
        pos = self.data.get("position")
        return pos if isinstance(pos, dict) else None

    def orders_today(self, day: str) -> int:
        book = self.data.get("orders") or {}
        return int(book.get("count") or 0) if book.get("date") == day else 0

    # -- mutations (every one persists immediately)
    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2),
                             encoding="utf-8")

    def count_order(self, day: str) -> None:
        self.data["orders"] = {"date": day, "count": self.orders_today(day) + 1}
        self.save()

    def set_long(self, position: dict) -> None:
        self.data.update({"status": LONG, "position": position, "unknown": None})
        self.save()

    def set_flat(self) -> None:
        self.data.update({"status": FLAT, "position": None, "unknown": None})
        self.save()

    def set_unknown(self, context: dict) -> None:
        self.data.update({"status": STATE_UNKNOWN,
                          "unknown": {k: redact(str(v)) if isinstance(v, str) else v
                                      for k, v in context.items()}})
        self.save()


# ---------------------------------------------------------------------------
# executor


class On1Executor:
    def __init__(self, *, client, state: On1State, config: On1Config,
                 kill_switch: KillSwitch, sessions_csv: str | Path,
                 events_path: str | Path, live: bool, live_reason: str = "",
                 now=None, clock=time.time):
        self.client = client
        self.state = state
        self.config = config
        self.kill_switch = kill_switch
        self.sessions_csv = Path(sessions_csv)
        self.events_path = Path(events_path)
        self.live = bool(live)
        self.live_reason = live_reason
        self._now = now if now is not None else datetime.now()
        self._clock = clock
        for problem in config.problems:
            self.emit("-", "config_problem", detail=problem)

    # -- events ----------------------------------------------------------
    def emit(self, job: str, event: str, **fields: Any) -> dict:
        record = {"ts": self._clock(), "time": self._now.isoformat(timespec="seconds"),
                  "job": job, "event": event, "live": self.live}
        record.update(fields)
        line = redact(json.dumps(record, ensure_ascii=False, default=str))
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.events_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        logger.info("on1 %s/%s", job, event, extra={"data": record})
        return record

    # -- guards ----------------------------------------------------------
    @property
    def day_key(self) -> str:
        return self._now.strftime("%Y%m%d")

    def _blocked(self, job: str) -> str | None:
        """Reasons NO order may be sent, in the order they are checked."""
        if self.kill_switch.is_tripped:
            return f"kill switch tripped: {self.kill_switch.state}"
        if self.state.status == STATE_UNKNOWN:
            return ("state is STATE_UNKNOWN; run scripts/run_on1_reconcile "
                    "and clear it before any new order")
        if self.state.orders_today(self.day_key) >= MAX_ORDERS_PER_DAY:
            return f"daily order cap reached ({MAX_ORDERS_PER_DAY})"
        window = self.config.entry_window if job == ENTRY else self.config.exit_window
        clock = self._now.strftime("%H:%M")
        if not window[0] <= clock <= window[1]:
            return f"outside the {job} window {window[0]}-{window[1]} (now {clock})"
        return None

    # -- sanity ----------------------------------------------------------
    def _sanity_check(self, job: str, payload: dict, symbol_name: str,
                      month: str) -> None:
        """Every property of the order that the state machine believes, checked
        against the payload that is about to leave.  Any mismatch is fail-close."""
        symbol = str(payload.get("Symbol") or "")
        if not MICRO_SYMBOL_RE.fullmatch(symbol):
            raise SanityError(f"symbol {symbol!r} is not the 9-digit shape kabusapi returns")
        if MICRO_NAME_MARKER not in (symbol_name or ""):
            raise SanityError(f"SymbolName {symbol_name!r} is not a micro contract")
        if not re.fullmatch(r"20[0-9]{4}", month or ""):
            raise SanityError(f"contract month {month!r} is not yyyyMM")
        if payload.get("Qty") != MAX_QTY:
            raise SanityError(f"Qty {payload.get('Qty')!r} != {MAX_QTY}")
        if payload.get("Exchange") not in _ALLOWED_EXCHANGES:
            raise SanityError(f"Exchange {payload.get('Exchange')!r} is not the day session")
        if payload.get("Price") != 0:
            raise SanityError("market orders must carry Price 0 (kabusapi FrontOrderType table)")
        if payload.get("TimeInForce") != TIME_IN_FORCE_FAK:
            raise SanityError("引成（派生）/成行 accept FAK only")
        expected = ((SIDE_BUY, TRADE_TYPE_NEW, FRONT_ORDER_TYPE_MARKET_ON_CLOSE)
                    if job == ENTRY else
                    (SIDE_SELL, TRADE_TYPE_CLOSE, FRONT_ORDER_TYPE_MARKET))
        actual = (payload.get("Side"), payload.get("TradeType"),
                  payload.get("FrontOrderType"))
        if actual != expected:
            raise SanityError(f"{job} payload {actual} does not match {expected}")

    # -- symbol resolution ------------------------------------------------
    def _resolve_symbol(self, month: str) -> tuple[str, str]:
        info = self.client.symbol_name_future(FUTURE_CODE_MICRO, int(month))
        symbol = str(info.get("Symbol") or "")
        name = str(info.get("SymbolName") or "")
        if not symbol or not name:
            raise SanityError(f"symbolname/future gave no Symbol/SymbolName for {month}")
        return symbol, name

    # -- send -------------------------------------------------------------
    def _send(self, job: str, payload: dict, context: dict) -> dict | None:
        """The ONLY place an order leaves.  Counts the order first, so an
        ambiguous failure cannot be retried into a second slot."""
        self.state.count_order(self.day_key)
        if not self.live:
            self.emit(job, "dry_run_order", payload=payload, reason=self.live_reason,
                      **context)
            return {"OrderId": "", "dry_run": True}
        try:
            result = self.client.send_future_order(payload)
        except OrderStateUnknown as exc:
            self.state.set_unknown({"job": job, "day": self.day_key,
                                    "symbol": payload.get("Symbol"),
                                    "side": payload.get("Side"),
                                    "detail": str(exc), **context})
            self.emit(job, "order_state_unknown", detail=str(exc), payload=payload,
                      **context)
            return None
        except KabuNetworkError as exc:
            # Provably pre-send: nothing reached kabuステーション.
            self.emit(job, "order_not_sent", detail=str(exc), **context)
            return None
        except KabuError as exc:
            self.emit(job, "order_rejected", status=exc.status_code, code=exc.code,
                      detail=exc.message, **context)
            return None
        self.emit(job, "order_accepted", order_id=result.get("OrderId"),
                  payload=payload, **context)
        return result

    # -- entry ------------------------------------------------------------
    def run_entry(self) -> str:
        job = ENTRY
        blocked = self._blocked(job)
        if blocked:
            self.emit(job, "skip", reason=blocked)
            return "skip"
        if self.state.status != FLAT:
            self.emit(job, "skip", reason=f"state is {self.state.status}, not {FLAT}")
            return "skip"

        month, reference, reason = resolve_central_month(self.sessions_csv,
                                                         self._now.date())
        if month is None:
            self.emit(job, "skip", reason=f"central month unresolved: {reason}")
            return "skip"
        days_to_sq = (sq_date(month) - self._now.date()).days
        if days_to_sq <= SQ_BLACKOUT_DAYS:
            self.emit(job, "skip", reason="SQ blackout", month=month,
                      days_to_sq=days_to_sq)
            return "skip"

        try:
            open_positions = [r for r in self.client.positions()
                              if float(r.get("LeavesQty") or 0) > 0]
        except (KabuError, KabuNetworkError, TypeError, ValueError) as exc:
            self.emit(job, "alert", reason="positions unreadable", detail=str(exc))
            return "alert"
        if open_positions:
            self.emit(job, "alert", reason="expected a flat account",
                      positions=len(open_positions))
            return "alert"

        try:
            symbol, symbol_name = self._resolve_symbol(month)
            self._price_band_check(symbol, reference)
        except SanityError as exc:
            self.emit(job, "alert", reason="sanity", detail=str(exc), month=month)
            return "alert"
        except (KabuError, KabuNetworkError) as exc:
            self.emit(job, "alert", reason="symbol/board unreadable", detail=str(exc))
            return "alert"

        payload = {
            "Symbol": symbol,
            "Exchange": EXCHANGE_DAY_SESSION,
            "TradeType": TRADE_TYPE_NEW,
            "TimeInForce": TIME_IN_FORCE_FAK,
            "Side": SIDE_BUY,
            "Qty": MAX_QTY,
            "FrontOrderType": FRONT_ORDER_TYPE_MARKET_ON_CLOSE,
            "Price": 0,
            "ExpireDay": EXPIRE_DAY_TODAY,
        }
        try:
            self._sanity_check(job, payload, symbol_name, month)
        except SanityError as exc:
            self.emit(job, "alert", reason="sanity", detail=str(exc))
            return "alert"

        result = self._send(job, payload, {"month": month, "symbol_name": symbol_name})
        if result is None:
            return "alert"
        self.state.set_long({"symbol": symbol, "symbol_name": symbol_name,
                             "month": month, "qty": MAX_QTY, "side": SIDE_BUY,
                             "entry_day": self.day_key,
                             "order_id": result.get("OrderId") or "",
                             "dry_run": bool(result.get("dry_run"))})
        return "ordered"

    def _price_band_check(self, symbol: str, reference: dict) -> None:
        """ENTRY ONLY.  A board price far from the last published print means the
        symbol is not the instrument we think it is.  Deliberately not applied to
        the exit: a diagnostic must never keep a real position open overnight
        (same rule as bitFlyer — a closing order is never gated)."""
        board = self.client.board(symbol, EXCHANGE_DAY_SESSION)
        try:
            price = float(board.get("CurrentPrice"))
            ref = float(reference["day_close"])
        except (TypeError, ValueError, KeyError):
            raise SanityError("board price or JPX reference close unreadable") from None
        if ref <= 0:
            raise SanityError("JPX reference close is not positive")
        deviation = abs(price - ref) / ref * 100.0
        if deviation > PRICE_BAND_PCT:
            raise SanityError(f"board {price} is {deviation:.1f}% from the JPX "
                              f"reference {ref} (band {PRICE_BAND_PCT}%)")

    # -- exit -------------------------------------------------------------
    def run_exit(self) -> str:
        job = EXIT
        blocked = self._blocked(job)
        if blocked:
            self.emit(job, "skip", reason=blocked)
            return "skip"
        position = self.state.position
        if self.state.status != LONG or position is None:
            self.emit(job, "skip", reason=f"state is {self.state.status}, not {LONG}")
            return "skip"

        symbol = str(position.get("symbol") or "")
        month = str(position.get("month") or "")
        symbol_name = str(position.get("symbol_name") or "")

        if position.get("dry_run"):
            # The entry was never sent, so there is no position to verify.
            held_ok, detail = True, "dry-run position; API verification skipped"
        else:
            try:
                held_ok, detail = self._verify_long(symbol)
            except (KabuError, KabuNetworkError) as exc:
                self.emit(job, "alert", reason="positions unreadable", detail=str(exc))
                return "alert"
        if not held_ok:
            self.emit(job, "alert", reason="position mismatch", detail=detail,
                      expected_symbol=symbol,
                      resolution="a human must reconcile the account before ON1 resumes")
            return "alert"

        payload = {
            "Symbol": symbol,
            "Exchange": EXCHANGE_DAY_SESSION,
            "TradeType": TRADE_TYPE_CLOSE,
            "TimeInForce": TIME_IN_FORCE_FAK,
            "Side": SIDE_SELL,
            "Qty": MAX_QTY,
            "ClosePositionOrder": CLOSE_POSITION_ORDER_OLDEST,
            "FrontOrderType": FRONT_ORDER_TYPE_MARKET,
            "Price": 0,
            "ExpireDay": EXPIRE_DAY_TODAY,
        }
        try:
            self._sanity_check(job, payload, symbol_name, month)
        except SanityError as exc:
            self.emit(job, "alert", reason="sanity", detail=str(exc))
            return "alert"

        result = self._send(job, payload, {"month": month, "note": detail})
        if result is None:
            return "alert"
        # FLAT on ACCEPTANCE, not on a verified fill: at 8:40 the auction has not
        # run yet, so re-reading /positions here would always still show the long
        # and prove nothing.  A FAK that does not fill is caught the same day by
        # the entry job, which refuses to open on a non-flat account.
        self.state.set_flat()
        return "ordered"

    def _verify_long(self, symbol: str) -> tuple[bool, str]:
        rows = [r for r in self.client.positions()
                if float(r.get("LeavesQty") or 0) > 0]
        if len(rows) != 1:
            return False, f"{len(rows)} open futures positions, expected exactly 1"
        row = rows[0]
        if str(row.get("Symbol") or "") != symbol:
            return False, f"held symbol {row.get('Symbol')!r} != expected {symbol!r}"
        if str(row.get("Side") or "") != SIDE_BUY:
            return False, f"held side {row.get('Side')!r} is not long"
        if float(row.get("LeavesQty") or 0) != float(MAX_QTY):
            return False, f"held qty {row.get('LeavesQty')!r} != {MAX_QTY}"
        return True, f"verified 1 long {symbol}"

    # -- reconcile (READ ONLY) -------------------------------------------
    def reconcile(self, query: QueryOnlyKabu) -> str:
        """Positive evidence only.  Absence of evidence leaves STATE_UNKNOWN in
        place; only a human clears it after that."""
        job = "reconcile"
        if self.state.status != STATE_UNKNOWN:
            self.emit(job, "skip", reason=f"state is {self.state.status}")
            return "skip"
        pending = self.state.data.get("unknown") or {}
        symbol = str(pending.get("symbol") or "")
        try:
            positions = [r for r in query.positions()
                         if float(r.get("LeavesQty") or 0) > 0]
            orders = query.orders(symbol=symbol) if symbol else query.orders()
        except (KabuError, KabuNetworkError) as exc:
            self.emit(job, "unresolved", detail=f"read failed: {exc}")
            return "unresolved"

        held = [r for r in positions if str(r.get("Symbol") or "") == symbol
                and str(r.get("Side") or "") == SIDE_BUY]
        if pending.get("job") == ENTRY:
            if held and float(held[0].get("LeavesQty") or 0) == float(MAX_QTY):
                self.state.set_long({"symbol": symbol,
                                     "symbol_name": pending.get("symbol_name", ""),
                                     "month": pending.get("month", ""),
                                     "qty": MAX_QTY, "side": SIDE_BUY,
                                     "entry_day": pending.get("day", ""),
                                     "order_id": self._order_id_of(orders),
                                     "dry_run": False})
                self.emit(job, "resolved", status=LONG, symbol=symbol)
                return LONG
            if not positions and self._orders_finished_unfilled(orders):
                self.state.set_flat()
                self.emit(job, "resolved", status=FLAT, symbol=symbol)
                return FLAT
        elif pending.get("job") == EXIT:
            if not positions:
                self.state.set_flat()
                self.emit(job, "resolved", status=FLAT, symbol=symbol)
                return FLAT
            if held and float(held[0].get("LeavesQty") or 0) == float(MAX_QTY) \
                    and self._orders_finished_unfilled(orders):
                # The exit did not execute, so the position record from the
                # ENTRY is still the right one -- do not rebuild it from the
                # exit's pending context and lose the real entry day.
                self.state.set_long(dict(self.state.position or {}))
                self.emit(job, "resolved", status=LONG, symbol=symbol,
                          note="exit did not fill; position still open")
                return LONG
        self.emit(job, "unresolved",
                  detail="no positive evidence; STATE_UNKNOWN stands",
                  positions=len(positions), orders=len(orders))
        return "unresolved"

    @staticmethod
    def _order_id_of(orders: list[dict]) -> str:
        """Only when the symbol-filtered listing leaves exactly one candidate —
        a guessed id in the ledger is worse than no id."""
        return str(orders[0].get("ID") or "") if len(orders) == 1 else ""

    @staticmethod
    def _orders_finished_unfilled(orders: list[dict]) -> bool:
        """Positive evidence that nothing executed: kabusapi OrdersSuccess.State 5
        = 終了（発注エラー・取消済・全約定・失効・期限切れ）on every listed order, each
        with CumQty 0.  An EMPTY listing is not evidence — /orders is eventually
        consistent and has to be allowed to lag a fresh acceptance."""
        if not orders:
            return False
        return all(int(row.get("State") or 0) == 5
                   and float(row.get("CumQty") or 0) == 0.0 for row in orders)


# ---------------------------------------------------------------------------
# wiring


def build_executor(root: str | Path, *, env: dict[str, str] | None = None,
                   now: datetime | None = None, client=None) -> On1Executor:
    """Assemble the executor from the repo layout.  `client` is injectable so
    tests never construct a real session."""
    import os

    from dotenv import load_dotenv

    from bot.jpx.kabu_client import KabuClient
    from bot.settings import Secret

    root = Path(root)
    load_dotenv(root / ".env")
    env = dict(os.environ) if env is None else env

    config = load_on1_config(root / "config" / "on1_live.yaml")
    live, reason = resolve_live(env, config)
    if client is None:
        client = KabuClient(Secret(env.get("KABU_API_PASSWORD", "")), port=config.port)
    return On1Executor(
        client=client,
        state=On1State(root / "data" / "on1_live" / "state.json"),
        config=config,
        kill_switch=KillSwitch(state_dir=root / "data", manual_file=root / "KILL"),
        sessions_csv=root / "data" / "jpx_daily" / "nk225_sessions.csv",
        events_path=root / "data" / "on1_live" / "events.jsonl",
        live=live, live_reason=reason, now=now,
    )

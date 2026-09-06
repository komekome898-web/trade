"""Cash-ETF auction-fill measurement executor (PHASE2 EXEC_MEASUREMENT).

Runs the pre-registered measurement of `docs/PHASE2/EXEC_MEASUREMENT/PREREG.md`:
buy 1 trading unit of 1343 / 1591 / 1348 at the CLOSING auction with 引成
(`FrontOrderType` 16) and sell it at the next OPENING auction with 寄成
(`FrontOrderType` 13), 50 round trips per symbol, to replace the assumed
"one tick per side" rounding cost with a measured one.

The strategy is trivial.  Everything here is the safety envelope, and the
envelope is a TRANSLATION of `bot/jpx/on1_executor.py` into cash equities —
`on1_executor.py` is deliberately NOT modified and NOT imported for its
behaviour (docs/.../DESIGN.md §9: sharing a safety mechanism propagates one
bug into two live paths).  ON1 and this measurement share nothing: separate
state files, separate locks, separate config, separate env variable, separate
ack phrase.  Arming one must never arm the other.

HARD LIMITS — enforced in code, NOT reachable from config
---------------------------------------------------------
* position per symbol is always in {0, +1 trading unit}: entry only from FLAT,
  exit only from LONG.  `CashMargin` is pinned to 1 (現物), so a short is
  impossible at the account level as well as in this code.
* the quantity is NEVER a constant.  It is read from `GET /symbol`'s
  `TradingUnit` and the order is refused unless
  `Qty == TradingUnit == EXPECTED_TRADING_UNIT[symbol]`.  Hard-coding "1 unit"
  under-fills 1343 (unit 10); trusting only the pre-registered map misses the
  2027-01-28 unit change on 1591.  Both must agree or nothing is sent.
* `MAX_NOTIONAL_YEN` (60,000 yen per order) is the last line of defence: if
  1591 is split and its unit becomes 10 or 100, the notional check stops the
  order automatically, without anyone having to remember the date.
* at most `MAX_ORDERS_PER_DAY_PER_SYMBOL = 2` sends per symbol per calendar day
  (1 entry + 1 exit; there is no roll).  The counter is persisted and
  incremented BEFORE the send, so an ambiguous failure still consumes its slot.
* every payload passes `_sanity_check` before it can leave (§2.4 of DESIGN):
  symbol, trading unit, notional, exchange, security type, cash/margin, price 0,
  the (Side, DelivType, FundType, FrontOrderType) tuple for the job, account
  type, 値幅制限, and — on ENTRY ONLY — a price band against the last print.
  A failed check does not send (fail-close).
* KILL file / data/kill_switch.json stops everything (S5).
* an ambiguous send failure parks that symbol in STATE_UNKNOWN, and
  STATE_UNKNOWN on ANY symbol stops EVERY symbol (PREREG S2).  While it is
  there NOTHING is sent; `reconcile()` is handed a `QueryOnlyKabu`, which has
  no send method at all.
* the stop flags S1/S3/S4/S6 write `paused.json`, which never auto-resumes: a
  human clears it with `operator_confirm=True` (same contract as the kill
  switch).  A pause blocks ENTRIES only — a diagnostic must never strand a real
  position overnight, so the closing leg is never gated.

LIVE TRIPLE GATE
----------------
`ETF_EXEC_LIVE=true` in the environment AND `live_ack:
"I_UNDERSTAND_REAL_MONEY_JPX_ETF"` AND `enabled: true` in
config/etf_measure.yaml.  Missing any one of them means DRY RUN: the payload is
written to events.jsonl and nothing is sent — not even to the 検証 port 18081.

SPEC ITEMS RECORDED AS 不明 (never guessed around)
-------------------------------------------------
1. Where SOR (`Exchange` 9) routes a 引成/寄成 order, and whether that
   participates in the exchange auction, is not stated in kabu_STATION_API.yaml.
   It must be confirmed on the 検証 port 18081 before any production use.  The
   `Exchange` / `ExchangeName` of every order is copied into the ledger so the
   routing can be read off the record afterwards.
2. Whether `ExpireDay: 0` ("本日") resolves to the same day at 15:20 / 08:40.
3. Whether kabuステーション accepts a 引成 at 15:20 and a 寄成 at 08:40 at all.
   A refusal is a definite 4xx = `KabuError`, which is recorded and after which
   nothing further is sent.
"""
from __future__ import annotations

import csv
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

import yaml

from bot.jpx.kabu_client import (
    PRODUCT_CASH, VERIFICATION_PORT, KabuError, KabuNetworkError,
    OrderStateUnknown, QueryOnlyKabu,
)
from bot.logging_setup import redact
from bot.risk.kill_switch import KillSwitch

logger = logging.getLogger("bot.jpx.etf_measure")

# ---- hard limits (module constants; config cannot widen them) ---------------
MAX_LOTS_PER_SYMBOL = 1                 # 1 *trading unit*, not 1 口
MAX_ORDERS_PER_DAY_PER_SYMBOL = 2       # 1 entry + 1 exit, no roll
MAX_NOTIONAL_YEN = 60_000               # per symbol per order, fail-close
ALLOWED_SYMBOLS = ("1343", "1591", "1348")
ALLOWED_EXCHANGES = (9, 27)             # 9 = SOR / 27 = 東証+.  1 (東証) cannot
                                        # take a 新規 order in normal hours.
# PREREG §0 (primary sources) + PREREG 追記 2026-09-06 for 1348.  Pre-registered
# only: the runtime `TradingUnit` from GET /symbol must agree with it AND with
# the Qty about to be sent, or nothing is sent (S6).
EXPECTED_TRADING_UNIT = {"1343": 10, "1591": 1, "1348": 1}
ALLOWED_ACCOUNT_TYPES = (2, 4, 12)      # 2 一般 / 4 特定 / 12 法人
PRICE_BAND_PCT = 10.0                   # ENTRY ONLY: board vs latest print
HARD_ENTRY_WINDOW = ("15:00", "15:24")  # before the 15:30 closing auction
HARD_EXIT_WINDOW = ("08:00", "08:50")   # before the 9:00 opening auction

LIVE_ACK_PHRASE = "I_UNDERSTAND_REAL_MONEY_JPX_ETF"   # NOT ON1's phrase
LIVE_ENV_VAR = "ETF_EXEC_LIVE"                        # NOT ON1's variable

# ---- stop rules (PREREG §6) -------------------------------------------------
STOP_TICK_MULTIPLE = 3.0                # S1: |e| > 3 ticks on either leg
STOP_CONSECUTIVE_NOFILL = 2             # S3: 2 unfilled nights in a row
STOP_CUM_PNL_YEN = -15_000.0            # S4: cumulative realised loss floor

# ---- pass bars (PREREG §5; transcribed from the judgment proposals) ---------
# 1348's bar comes from the PREREG 追記 2026-09-06 (same definition: the
# optimistic CI lower bound of its own development set).
PASS_BAR_BPS = {"1343": 6.1, "1591": 6.3, "1348": 2.7}
TARGET_N_PER_SYMBOL = 50
BOOTSTRAP_BLOCK = 5
BOOTSTRAP_N = 2000
BOOTSTRAP_SEED = 20260906

# ---- kabusapi enum values (kabu_STATION_API.yaml v1.5, RequestSendOrder) ----
SIDE_SELL = "1"                         # 売買区分 1 = 売
SIDE_BUY = "2"                          # 売買区分 2 = 買
SECURITY_TYPE_STOCK = 1                 # 商品種別 1 = 株式
CASH_MARGIN_CASH = 1                    # 信用区分 1 = 現物
DELIV_TYPE_ENTRY = 2                    # 受渡区分 2 = お預り金 (現物買は指定必須)
DELIV_TYPE_EXIT = 0                     # 受渡区分 0 = 指定なし (現物売)
FUND_TYPE_ENTRY = "02"                  # 資産区分 02 = 保護 (現物買)
FUND_TYPE_EXIT = "  "                   # 資産区分 半角スペース2つ (現物売)
FRONT_ORDER_TYPE_MOC = 16               # 執行条件 16 = 引成（後場）
FRONT_ORDER_TYPE_MOO = 13               # 執行条件 13 = 寄成（前場）
EXPIRE_DAY_TODAY = 0                    # 注文有効期限 0 = 「本日」
ORDER_STATE_FINISHED = 5                # OrdersSuccess.State 5 = 終了
DETAIL_RECTYPE_FILL = 8                 # Details[].RecType 8 = 約定

ENTRY = "entry"
EXIT = "exit"

FLAT = "FLAT"
LONG = "LONG"
STATE_UNKNOWN = "STATE_UNKNOWN"

# JPX 呼値の単位, "売買単位が1口のETF等" column.  Mirrors
# config/constants.yaml: jpx_cash_equity.etf_tick_size_yen_by_price_band
# (a test pins the two copies together, so a drift is a test failure).
ETF_TICK_BANDS: tuple[tuple[int, int], ...] = (
    (1_000, 1), (3_000, 1), (5_000, 1), (10_000, 1),
    (30_000, 5), (50_000, 10), (100_000, 10), (300_000, 50),
    (500_000, 100), (1_000_000, 100), (3_000_000, 500), (5_000_000, 1_000),
    (10_000_000, 1_000), (30_000_000, 5_000), (50_000_000, 10_000),
)
ETF_TICK_ABOVE_TOP_BAND = 10_000

LEDGER_COLUMNS = (
    "symbol", "entry_date", "exit_date", "trading_unit", "qty", "exchange",
    "exchange_name", "entry_order_id", "exit_order_id", "fill_buy", "fill_sell",
    "fill_buy_time", "fill_sell_time", "print_close", "print_open",
    "print_source", "board_close_snapshot", "board_open_snapshot",
    "idx_close", "idx_open", "tick_yen", "tick_bps",
    "e_buy_bps", "e_sell_bps", "c_bps", "c_ticks",
    "commission_yen", "commission_tax_yen", "pnl_yen", "cum_pnl_yen",
    "counted_in_n", "excluded_reason", "note",
)


class SanityError(Exception):
    """A pre-send check failed.  Nothing is sent (fail-close)."""


def etf_tick_yen(price: float) -> int:
    """呼値 for an ETF at `price` yen."""
    for bound, tick in ETF_TICK_BANDS:
        if price <= bound:
            return tick
    return ETF_TICK_ABOVE_TOP_BAND


# ---------------------------------------------------------------------------
# calendar


def sq_date(year: int, month: int) -> date:
    """Quarterly SQ = the second Friday of the month."""
    first = date(year, month, 1)
    first_friday = first + timedelta(days=(4 - first.weekday()) % 7)
    return first_friday + timedelta(days=7)


def previous_weekday(day: date) -> date:
    """The weekday before `day`.  Holidays are not modelled: this rule only ever
    ADDS a skipped night, so a holiday makes it skip a day that was not a
    session anyway (fail-close in the harmless direction)."""
    prev = day - timedelta(days=1)
    while prev.weekday() >= 5:
        prev -= timedelta(days=1)
    return prev


def ex_dates_from_yahoo_snapshot(path: str | Path) -> frozenset[str]:
    """Ex-dividend dates out of a permanent Yahoo chart snapshot.

    `events.dividends[*].date` is an epoch second at the exchange's own
    timezone offset (`meta.gmtoffset`), and Yahoo dates a dividend on its
    EX-date.  Reading them from the MD5-stamped snapshot in `backtest_data/`
    rather than re-fetching keeps the exclusion calendar reproducible: PREREG §3
    requires the excluded nights to be mechanical, not chosen by eye.
    """
    path = Path(path) if path else None
    if path is None or not path.is_file():
        return frozenset()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        result = payload["chart"]["result"][0]
    except (ValueError, KeyError, IndexError, TypeError, OSError):
        return frozenset()
    offset = int((result.get("meta") or {}).get("gmtoffset") or 0)
    events = (result.get("events") or {}).get("dividends") or {}
    out: set[str] = set()
    for item in (events.values() if isinstance(events, dict) else events):
        try:
            stamp = int((item or {}).get("date"))
        except (TypeError, ValueError):
            continue
        out.add(datetime.utcfromtimestamp(stamp + offset).strftime("%Y-%m-%d"))
    return frozenset(out)


EX_DATE_PROJECTION_YEARS = 2


def project_ex_dates(observed: Iterable[str],
                     years_ahead: int = EX_DATE_PROJECTION_YEARS) -> frozenset[str]:
    """Carry a REGULAR observed ex-date pattern forward past the snapshot.

    The snapshot is a record of the past; the measurement runs into the future,
    and the one 1348 ex-date inside the window (mid-January 2027) is later than
    anything the frozen file can contain.  Extending the observed anniversary is
    safe in one direction only, so the rule is deliberately narrow:

    * it projects ONLY when every fully observed year carries exactly the same
      (month, day) set — 1348 has paid on 01-16 and 07-16 in all 14 observed
      years.  An irregular history is not projected at all, because a guessed
      date would skip the wrong night while looking as if the rule had worked.
    * projection can only ADD skipped nights.  It is not a substitute for the
      issuer's announcement: PREREG appendix A still has to be frozen into
      `skip_dates` before the first order.
    """
    by_year: dict[int, set[tuple[int, int]]] = {}
    for text in observed:
        try:
            day = datetime.strptime(str(text)[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        by_year.setdefault(day.year, set()).add((day.month, day.day))
    if len(by_year) < 3:
        return frozenset()
    years = sorted(by_year)
    pattern = by_year[years[-1]]
    # the first and last years may be partial (the snapshot's own edges)
    if any(by_year[y] != pattern for y in years[1:-1]):
        return frozenset()
    out: set[str] = set()
    for offset in range(1, max(0, int(years_ahead)) + 1):
        for month, day_of_month in sorted(pattern):
            try:
                out.add(date(years[-1] + offset, month, day_of_month)
                        .strftime("%Y-%m-%d"))
            except ValueError:            # 02-29 in a non-leap year
                continue
    return frozenset(out)


def skip_dates_around_ex_dates(ex_dates: Iterable[str]) -> frozenset[str]:
    """PREREG §3.1: the ex-date AND the business day before it.

    Both are needed because a round trip spans two sessions: entering on the eve
    exits on the ex-date, and entering on the ex-date exits the day after.
    Because the eve is in the set, testing the ENTRY date alone already drops
    every round trip that touches an ex-date on either leg.
    """
    out: set[str] = set()
    for text in ex_dates:
        try:
            day = datetime.strptime(str(text)[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        out.add(day.strftime("%Y-%m-%d"))
        out.add(previous_weekday(day).strftime("%Y-%m-%d"))
    return frozenset(out)


def is_sq_eve(day: date) -> bool:
    """True on the session whose CLOSE would be an entry settled on an SQ open.

    PREREG §3.2 drops the round trip that exits on a quarterly SQ morning, i.e.
    the one entered on the previous business day.  Holidays are not modelled:
    the rule only ever skips, so a holiday would make it skip a day that was not
    a session anyway.
    """
    if day.month not in (3, 6, 9, 12):
        return False
    sq = sq_date(day.year, day.month)
    eve = sq - timedelta(days=1)
    while eve.weekday() >= 5:            # never fires (SQ is a Friday) but the
        eve -= timedelta(days=1)          # rule must not depend on that
    return day == eve


# ---------------------------------------------------------------------------
# config


@dataclass(frozen=True)
class EtfMeasureConfig:
    enabled: bool = False
    live_ack: str = ""
    port: int = VERIFICATION_PORT
    exchange: int = 9
    account_type: int = 4
    symbols: tuple[str, ...] = ALLOWED_SYMBOLS
    max_notional_yen: int = MAX_NOTIONAL_YEN
    entry_window: tuple[str, str] = HARD_ENTRY_WINDOW
    exit_window: tuple[str, str] = HARD_EXIT_WINDOW
    skip_dates: frozenset[str] = frozenset()
    problems: tuple[str, ...] = field(default_factory=tuple)


def _window(raw: Any, hard: tuple[str, str], name: str,
            problems: list[str]) -> tuple[str, str]:
    """A configured window may only NARROW the hard one."""
    if raw is None:
        return hard
    try:
        lo, hi = (datetime.strptime(str(raw[i]), "%H:%M").strftime("%H:%M")
                  for i in (0, 1))
    except Exception:
        problems.append(f"{name}={raw!r} is not a ['HH:MM','HH:MM'] pair")
        return hard
    if lo < hard[0] or hi > hard[1] or lo > hi:
        problems.append(f"{name}={raw!r} is outside the hard window {hard}")
        return hard
    return (lo, hi)


def _symbols(raw: Any, problems: list[str]) -> tuple[str, ...]:
    """Config may only pick a SUBSET of the code's allow-list."""
    if raw is None:
        return ALLOWED_SYMBOLS
    if not isinstance(raw, (list, tuple)):
        problems.append(f"symbols={raw!r} is not a list; using {ALLOWED_SYMBOLS}")
        return ALLOWED_SYMBOLS
    kept: list[str] = []
    for item in raw:
        code = str(item).strip()
        if code not in ALLOWED_SYMBOLS:
            problems.append(f"symbol {code!r} is not in {ALLOWED_SYMBOLS}; dropped")
            continue
        if code not in kept:
            kept.append(code)
    return tuple(kept)


def _skip_dates(raw: Any, problems: list[str]) -> frozenset[str]:
    if raw is None:
        return frozenset()
    if not isinstance(raw, (list, tuple)):
        problems.append(f"skip_dates={raw!r} is not a list; ignored")
        return frozenset()
    out: set[str] = set()
    for item in raw:
        text = str(item).strip()
        try:
            out.add(datetime.strptime(text, "%Y-%m-%d").strftime("%Y-%m-%d"))
        except ValueError:
            problems.append(f"skip_dates entry {text!r} is not YYYY-MM-DD; ignored")
    return frozenset(out)


def load_etf_measure_config(path: str | Path) -> EtfMeasureConfig:
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

    exchange = raw.get("exchange", 9)
    try:
        exchange = int(exchange)
    except (TypeError, ValueError):
        problems.append(f"exchange={exchange!r} is not an integer; using 9 (SOR)")
        exchange = 9
    if exchange not in ALLOWED_EXCHANGES:
        problems.append(f"exchange={exchange!r} is not in {ALLOWED_EXCHANGES}; "
                        "using 9 (SOR)")
        exchange = 9

    account_type = raw.get("account_type", 4)
    try:
        account_type = int(account_type)
    except (TypeError, ValueError):
        problems.append(f"account_type={account_type!r} is not an integer; using 4")
        account_type = 4
    if account_type not in ALLOWED_ACCOUNT_TYPES:
        problems.append(f"account_type={account_type!r} is not in "
                        f"{ALLOWED_ACCOUNT_TYPES}; using 4 (特定)")
        account_type = 4

    notional = raw.get("max_notional_yen_per_symbol", MAX_NOTIONAL_YEN)
    try:
        notional = int(notional)
    except (TypeError, ValueError):
        problems.append(f"max_notional_yen_per_symbol={notional!r} is not an "
                        f"integer; using {MAX_NOTIONAL_YEN}")
        notional = MAX_NOTIONAL_YEN
    if notional > MAX_NOTIONAL_YEN:
        problems.append(f"max_notional_yen_per_symbol={notional} exceeds the code "
                        f"cap {MAX_NOTIONAL_YEN}; clamped")
        notional = MAX_NOTIONAL_YEN
    if notional <= 0:
        problems.append(f"max_notional_yen_per_symbol={notional} is not positive; "
                        f"using {MAX_NOTIONAL_YEN}")
        notional = MAX_NOTIONAL_YEN

    return EtfMeasureConfig(
        enabled=enabled,
        live_ack=str(raw.get("live_ack") or ""),
        port=port,
        exchange=exchange,
        account_type=account_type,
        symbols=_symbols(raw.get("symbols"), problems),
        max_notional_yen=notional,
        entry_window=_window(raw.get("entry_window"), HARD_ENTRY_WINDOW,
                             "entry_window", problems),
        exit_window=_window(raw.get("exit_window"), HARD_EXIT_WINDOW,
                            "exit_window", problems),
        skip_dates=_skip_dates(raw.get("skip_dates"), problems),
        problems=tuple(problems),
    )


def resolve_live(env: dict[str, str], config: EtfMeasureConfig) -> tuple[bool, str]:
    """The triple gate.  Returns (live, reason).  Half-armed is DRY RUN, never
    live — and the reason names the missing part so it lands in events.jsonl.

    Deliberately reads ONLY `ETF_EXEC_LIVE` and only this module's ack phrase:
    arming ON1 must not arm the measurement, and vice versa.
    """
    env_on = (env.get(LIVE_ENV_VAR) or "").strip().lower() in ("1", "true", "yes", "on")
    if not config.enabled:
        return False, "config etf_measure.yaml enabled is not true"
    if config.live_ack != LIVE_ACK_PHRASE:
        return False, "config etf_measure.yaml live_ack is missing/incorrect"
    if not env_on:
        return False, f"env {LIVE_ENV_VAR} is not true"
    return True, f"env {LIVE_ENV_VAR} + config live_ack + enabled"


# ---------------------------------------------------------------------------
# state


class EtfSymbolState:
    """data/etf_measure/state_<symbol>.json.

    Persisted so a process restart cannot resume trading out of a forgotten
    STATE_UNKNOWN, exactly like the kill switch.
    """

    def __init__(self, path: str | Path, symbol: str = ""):
        self.path = Path(path)
        self.symbol = symbol
        self.data: dict = {"symbol": symbol, "status": FLAT, "position": None,
                           "unknown": None, "orders": {"date": "", "count": 0},
                           "pending": [], "nofill_streak": 0}
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                # Unreadable state: fail safe, park in STATE_UNKNOWN.
                loaded = {"status": STATE_UNKNOWN, "position": None,
                          "unknown": {"detail": "unreadable state file"}}
            if isinstance(loaded, dict):
                self.data.update(loaded)
                self.data.setdefault("pending", [])
                self.data.setdefault("nofill_streak", 0)
            self.data["symbol"] = symbol or self.data.get("symbol") or ""

    # -- accessors
    @property
    def status(self) -> str:
        return str(self.data.get("status") or FLAT)

    @property
    def position(self) -> dict | None:
        pos = self.data.get("position")
        return pos if isinstance(pos, dict) else None

    @property
    def pending(self) -> list[dict]:
        rows = self.data.get("pending")
        return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []

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

    def add_pending(self, row: dict) -> None:
        self.data["pending"] = self.pending + [row]
        self.save()

    def set_pending(self, rows: list[dict]) -> None:
        self.data["pending"] = list(rows)
        self.save()

    def set_nofill_streak(self, value: int) -> None:
        self.data["nofill_streak"] = int(value)
        self.save()


class PauseFlag:
    """data/etf_measure/paused.json — the S1/S3/S4/S6 stop flags.

    Never auto-resumes.  `clear()` refuses without `operator_confirm=True`,
    the same contract as `bot/risk/kill_switch.py: reset`.
    """

    def __init__(self, path: str | Path, clock=time.time):
        self.path = Path(path)
        self._clock = clock
        self.data: dict = {"rules": []}
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                # Unreadable flag file: fail safe, treat as paused for both.
                loaded = {"rules": [{"rule": "unreadable", "symbol": "*",
                                     "detail": "unreadable paused.json"}]}
            if isinstance(loaded, dict) and isinstance(loaded.get("rules"), list):
                self.data = loaded

    @property
    def rules(self) -> list[dict]:
        return [r for r in self.data.get("rules", []) if isinstance(r, dict)]

    def is_paused(self, symbol: str = "*") -> bool:
        return any(str(r.get("symbol") or "*") in ("*", symbol) for r in self.rules)

    def reason(self, symbol: str = "*") -> str:
        hits = [r for r in self.rules if str(r.get("symbol") or "*") in ("*", symbol)]
        return "; ".join(f"{r.get('rule')}:{r.get('detail')}" for r in hits)

    def trip(self, rule: str, symbol: str, detail: str) -> None:
        if any(r.get("rule") == rule and r.get("symbol") == symbol
               for r in self.rules):
            return
        self.data["rules"] = self.rules + [
            {"rule": rule, "symbol": symbol, "detail": redact(str(detail)),
             "time": self._clock()}]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2),
                             encoding="utf-8")

    def clear(self, *, operator_confirm: bool = False) -> None:
        if not operator_confirm:
            raise PermissionError(
                "the measurement pause does not auto-resume: a human must "
                "investigate and call clear(operator_confirm=True)")
        self.data = {"rules": []}
        self.path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# daily print / index series (date,open,close CSVs)


def load_daily_series(path: str | Path) -> dict[str, dict[str, float]]:
    """{ 'YYYY-MM-DD': {'open': x, 'close': y} } from a `date,open,close` CSV.

    Missing / unparseable rows are skipped rather than raising: the print series
    feeds the LEDGER, and a gap there must never be able to influence whether an
    order is sent.  (The entry price band is the one place a missing print does
    block, and it blocks by failing closed.)
    """
    path = Path(path) if path else None
    out: dict[str, dict[str, float]] = {}
    if path is None or not path.is_file():
        return out
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = str(row.get("date") or "").strip()
            if not key:
                continue
            try:
                key = datetime.strptime(key[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
            except ValueError:
                continue
            values: dict[str, float] = {}
            for field_name in ("open", "close"):
                try:
                    values[field_name] = float(row.get(field_name) or "")
                except (TypeError, ValueError):
                    continue
            if values:
                out[key] = values
    return out


def latest_close_at_or_before(series: dict[str, dict[str, float]],
                              day: date) -> tuple[str, float] | None:
    key = day.strftime("%Y-%m-%d")
    usable = sorted(k for k in series if k <= key and "close" in series[k])
    if not usable:
        return None
    return usable[-1], float(series[usable[-1]]["close"])


# ---------------------------------------------------------------------------
# fills


def parse_fill(order_row: dict) -> dict:
    """Pull the realised fill out of one `/orders` row's `Details[]`.

    kabusapi puts executions in `Details[]` with `RecType` 8 (約定).  A market
    auction order can fill in several prints, so the price is the quantity
    weighted mean and the commission is the sum.  Returns
    `{qty, price, commission, commission_tax, time}`; `price` is None when
    nothing has executed (or nothing is visible yet — /orders is eventually
    consistent, and an empty answer is never evidence of a non-fill).
    """
    details = order_row.get("Details")
    rows = [d for d in details if isinstance(d, dict)] if isinstance(details, list) else []
    qty = 0.0
    notional = 0.0
    commission = 0.0
    commission_tax = 0.0
    stamp = ""
    for row in rows:
        try:
            if int(row.get("RecType") or 0) != DETAIL_RECTYPE_FILL:
                continue
        except (TypeError, ValueError):
            continue
        try:
            leg_qty = float(row.get("Qty") or 0)
            leg_price = float(row.get("Price") or 0)
        except (TypeError, ValueError):
            continue
        if leg_qty <= 0 or leg_price <= 0:
            continue
        qty += leg_qty
        notional += leg_qty * leg_price
        for key, target in (("Commission", "c"), ("CommissionTax", "t")):
            try:
                value = float(row.get(key) or 0)
            except (TypeError, ValueError):
                value = 0.0
            if target == "c":
                commission += value
            else:
                commission_tax += value
        stamp = str(row.get("ExecutionDay") or row.get("RecTime") or stamp)
    if qty <= 0:
        return {"qty": 0.0, "price": None, "commission": 0.0,
                "commission_tax": 0.0, "time": ""}
    return {"qty": qty, "price": notional / qty, "commission": commission,
            "commission_tax": commission_tax, "time": stamp}


def order_is_finished_unfilled(order_row: dict) -> bool:
    """Positive evidence that an order ended without executing: State 5 (終了)
    with CumQty 0.  An ABSENT order is not evidence."""
    try:
        return (int(order_row.get("State") or 0) == ORDER_STATE_FINISHED
                and float(order_row.get("CumQty") or 0) == 0.0)
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# ledger


def append_ledger_row(path: str | Path, row: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(LEDGER_COLUMNS),
                                extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow({k: ("" if row.get(k) is None else row.get(k))
                         for k in LEDGER_COLUMNS})


def read_ledger(path: str | Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _as_float(value: Any) -> float | None:
    try:
        text = str(value).strip()
        return float(text) if text else None
    except (TypeError, ValueError):
        return None


def round_trip_metrics(*, fill_buy: float, fill_sell: float, print_close: float,
                       print_open: float, qty: float, commission_yen: float = 0.0,
                       commission_tax_yen: float = 0.0,
                       tick_yen: float | None = None) -> dict:
    """PREREG §4 in one place, so the ledger and any re-analysis agree.

    `c` is defined as the SUBTRACTION — printed overnight return minus realised
    overnight return, plus commission in bps — and `e_buy + e_sell` is the
    first-order approximation kept alongside as a check, not as the definition.
    """
    e_buy = (fill_buy - print_close) / print_close * 1e4
    e_sell = (print_open - fill_sell) / print_open * 1e4
    printed = print_open / print_close - 1.0
    realised = fill_sell / fill_buy - 1.0
    fees = float(commission_yen) + float(commission_tax_yen)
    fee_bps = (fees / (fill_buy * qty) * 1e4) if fill_buy > 0 and qty > 0 else 0.0
    c_bps = (printed - realised) * 1e4 + fee_bps
    tick = float(tick_yen) if tick_yen else float(etf_tick_yen(print_close))
    tick_bps = tick / print_close * 1e4
    return {
        "e_buy_bps": e_buy,
        "e_sell_bps": e_sell,
        "c_bps": c_bps,
        "c_bps_approx": e_buy + e_sell + fee_bps,
        "c_ticks": c_bps / tick_bps if tick_bps else float("nan"),
        "tick_yen": tick,
        "tick_bps": tick_bps,
        "fee_bps": fee_bps,
        "pnl_yen": (fill_sell - fill_buy) * qty - fees,
    }


def summarise_ledger(path: str | Path, *, symbols: Iterable[str] = ALLOWED_SYMBOLS,
                     block: int = BOOTSTRAP_BLOCK, n_boot: int = BOOTSTRAP_N,
                     seed: int = BOOTSTRAP_SEED) -> dict:
    """The frozen one-shot read-out (PREREG §5).

    Only `counted_in_n` rows enter the estimate; excluded rows stay in the file
    so that a change in the exclusion rule is visible after the fact.  Seeded,
    so two runs over the same ledger give the same interval.
    """
    import numpy as np

    from bot.research.overnight import block_bootstrap_ci

    rows = read_ledger(path)
    out: dict[str, Any] = {"n_target": TARGET_N_PER_SYMBOL, "symbols": {}}
    for symbol in symbols:
        values = [_as_float(r.get("c_bps")) for r in rows
                  if str(r.get("symbol") or "") == symbol
                  and str(r.get("counted_in_n") or "").lower() == "true"]
        kept = np.array([v for v in values if v is not None], dtype=float)
        excluded = sum(1 for r in rows if str(r.get("symbol") or "") == symbol
                       and str(r.get("counted_in_n") or "").lower() != "true")
        bar = PASS_BAR_BPS.get(symbol)
        entry: dict[str, Any] = {"n": int(kept.size), "excluded": excluded,
                                 "pass_bar_bps": bar}
        if kept.size:
            lo, hi = block_bootstrap_ci(kept, block=block, n_boot=n_boot, seed=seed)
            entry.update({"mean_c_bps": float(kept.mean()),
                          "median_c_bps": float(np.median(kept)),
                          "sd_c_bps": float(kept.std(ddof=1)) if kept.size > 1 else 0.0,
                          "max_c_bps": float(kept.max()),
                          "p95_c_bps": float(np.percentile(kept, 95)),
                          "ci_lo_bps": lo, "ci_hi_bps": hi})
            if kept.size < TARGET_N_PER_SYMBOL:
                entry["verdict"] = "incomplete"
            elif bar is None:
                entry["verdict"] = "no_bar"
            else:
                entry["verdict"] = "pass" if hi < bar else "fail"
        else:
            entry["verdict"] = "incomplete"
        out["symbols"][symbol] = entry
    return out


# ---------------------------------------------------------------------------
# executor


class EtfAuctionExecutor:
    def __init__(self, *, client, states: dict[str, EtfSymbolState],
                 config: EtfMeasureConfig, kill_switch: KillSwitch,
                 pause: PauseFlag, events_path: str | Path,
                 ledger_path: str | Path,
                 print_series: dict[str, Path] | None = None,
                 index_series: dict[str, Path] | None = None,
                 ex_date_sources: dict[str, Path] | None = None,
                 live: bool = False, live_reason: str = "",
                 now=None, clock=time.time):
        self.client = client
        self.states = dict(states)
        self.config = config
        self.kill_switch = kill_switch
        self.pause = pause
        self.events_path = Path(events_path)
        self.ledger_path = Path(ledger_path)
        self.print_series = {k: Path(v) for k, v in (print_series or {}).items()}
        self.index_series = {k: Path(v) for k, v in (index_series or {}).items()}
        self.ex_date_sources = {k: Path(v)
                                for k, v in (ex_date_sources or {}).items()}
        self._ex_skip_cache: dict[str, frozenset[str]] = {}
        self.live = bool(live)
        self.live_reason = live_reason
        self._now = now if now is not None else datetime.now()
        self._clock = clock
        # Everything this run emitted, so a wrapper script can print what a dry
        # run WOULD have sent without re-parsing the append-only events file.
        self.emitted: list[dict] = []
        for problem in config.problems:
            self.emit("-", "-", "config_problem", detail=problem)

    # -- events ----------------------------------------------------------
    def emit(self, symbol: str, job: str, event: str, **fields: Any) -> dict:
        record = {"ts": self._clock(),
                  "time": self._now.isoformat(timespec="seconds"),
                  "symbol": symbol, "job": job, "event": event, "live": self.live}
        record.update(fields)
        line = redact(json.dumps(record, ensure_ascii=False, default=str))
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.events_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        logger.info("etf_measure %s/%s/%s", symbol, job, event, extra={"data": record})
        self.emitted.append(record)
        return record

    # -- guards ----------------------------------------------------------
    @property
    def now(self) -> datetime:
        return self._now

    @property
    def day_key(self) -> str:
        return self._now.strftime("%Y%m%d")

    @property
    def iso_day(self) -> str:
        return self._now.strftime("%Y-%m-%d")

    def state_of(self, symbol: str) -> EtfSymbolState:
        return self.states[symbol]

    def _any_unknown(self) -> str | None:
        for symbol, state in self.states.items():
            if state.status == STATE_UNKNOWN:
                return symbol
        return None

    def _blocked(self, job: str, symbol: str) -> str | None:
        """Reasons NO order may be sent, in the order they are checked.

        A pause (S1/S3/S4/S6) blocks entries only — the closing leg is never
        gated, or a diagnostic could strand a real position overnight.
        STATE_UNKNOWN blocks BOTH legs of BOTH symbols (PREREG S2).
        """
        if self.kill_switch.is_tripped:
            return f"kill switch tripped: {self.kill_switch.state}"
        unknown = self._any_unknown()
        if unknown is not None:
            return (f"{unknown} is STATE_UNKNOWN; run "
                    "scripts/run_etf_measure_reconcile.py and clear it before "
                    "any new order (every symbol is stopped)")
        if symbol not in self.config.symbols:
            return f"{symbol} is not in the configured symbols {self.config.symbols}"
        if job == ENTRY and self.pause.is_paused(symbol):
            return f"measurement paused: {self.pause.reason(symbol)}"
        state = self.states.get(symbol)
        if state is None:
            return f"no state file wired for {symbol}"
        if state.orders_today(self.day_key) >= MAX_ORDERS_PER_DAY_PER_SYMBOL:
            return f"daily order cap reached ({MAX_ORDERS_PER_DAY_PER_SYMBOL})"
        window = self.config.entry_window if job == ENTRY else self.config.exit_window
        clock = self._now.strftime("%H:%M")
        if not window[0] <= clock <= window[1]:
            return f"outside the {job} window {window[0]}-{window[1]} (now {clock})"
        return None

    def ex_date_skips(self, symbol: str) -> frozenset[str]:
        """Per-symbol ex-date exclusion, derived from that symbol's own frozen
        dividend snapshot.  Per symbol, not global: 1348's ex-date is no reason
        to lose a 1343 or 1591 night."""
        if symbol not in self._ex_skip_cache:
            source = self.ex_date_sources.get(symbol)
            observed = ex_dates_from_yahoo_snapshot(source) if source else frozenset()
            self._ex_skip_cache[symbol] = skip_dates_around_ex_dates(
                observed | project_ex_dates(observed))
        return self._ex_skip_cache[symbol]

    def _calendar_skip(self, symbol: str) -> str | None:
        """PREREG §3: ex-dates and the business day before them (frozen into
        `skip_dates`, and/or derived per symbol from its dividend snapshot), plus
        SQ eve, which is derived because it is a pure calendar rule."""
        if self.iso_day in self.config.skip_dates:
            return f"{self.iso_day} is in the pre-registered skip_dates"
        if self.iso_day in self.ex_date_skips(symbol):
            return (f"{self.iso_day} is an ex-dividend date for {symbol} or the "
                    "business day before one")
        if is_sq_eve(self._now.date()):
            return (f"{self.iso_day} is the eve of the quarterly SQ "
                    f"{sq_date(self._now.year, self._now.month)}")
        return None

    # -- sanity ----------------------------------------------------------
    def _sanity_check(self, job: str, symbol: str, payload: dict,
                      symbol_info: dict, board_price: float) -> None:
        """Every property the state machine believes, checked against the
        payload that is about to leave.  Any mismatch is fail-close."""
        if symbol not in ALLOWED_SYMBOLS:
            raise SanityError(f"symbol {symbol!r} is not in {ALLOWED_SYMBOLS}")
        if str(payload.get("Symbol") or "") != symbol:
            raise SanityError(f"payload Symbol {payload.get('Symbol')!r} != {symbol!r}")

        expected_unit = EXPECTED_TRADING_UNIT[symbol]
        try:
            unit = int(float(symbol_info.get("TradingUnit")))
        except (TypeError, ValueError):
            raise SanityError("GET /symbol returned no readable TradingUnit") from None
        if unit != expected_unit:
            raise SanityError(
                f"TradingUnit {unit} != pre-registered {expected_unit} for {symbol} "
                "(PREREG S6: the unit changed; stop and re-register)")
        if payload.get("Qty") != unit:
            raise SanityError(f"Qty {payload.get('Qty')!r} != TradingUnit {unit}")
        if unit <= 0 or MAX_LOTS_PER_SYMBOL != 1:
            raise SanityError("exactly one trading unit may be ordered")

        try:
            price = float(board_price)
        except (TypeError, ValueError):
            raise SanityError("board price unreadable") from None
        if price <= 0:
            raise SanityError(f"board price {board_price!r} is not positive")
        notional = price * unit
        cap = min(int(self.config.max_notional_yen), MAX_NOTIONAL_YEN)
        if notional > cap:
            raise SanityError(
                f"notional {notional:.0f} yen ({unit} x {price:.1f}) exceeds the "
                f"{cap} yen cap")

        if payload.get("Exchange") not in ALLOWED_EXCHANGES:
            raise SanityError(
                f"Exchange {payload.get('Exchange')!r} is not in {ALLOWED_EXCHANGES} "
                "(1 = 東証 cannot take a 新規 order in normal hours)")
        if payload.get("SecurityType") != SECURITY_TYPE_STOCK:
            raise SanityError("SecurityType must be 1 (株式)")
        if payload.get("CashMargin") != CASH_MARGIN_CASH:
            raise SanityError("CashMargin must be 1 (現物): margin makes a short possible")
        if payload.get("Price") != 0:
            raise SanityError("market orders must carry Price 0")
        if payload.get("ExpireDay") != EXPIRE_DAY_TODAY:
            raise SanityError("ExpireDay must be 0 (本日)")
        if payload.get("AccountType") not in ALLOWED_ACCOUNT_TYPES:
            raise SanityError(
                f"AccountType {payload.get('AccountType')!r} is not in "
                f"{ALLOWED_ACCOUNT_TYPES}")

        expected = ((SIDE_BUY, DELIV_TYPE_ENTRY, FUND_TYPE_ENTRY, FRONT_ORDER_TYPE_MOC)
                    if job == ENTRY else
                    (SIDE_SELL, DELIV_TYPE_EXIT, FUND_TYPE_EXIT, FRONT_ORDER_TYPE_MOO))
        actual = (payload.get("Side"), payload.get("DelivType"),
                  payload.get("FundType"), payload.get("FrontOrderType"))
        if actual != expected:
            raise SanityError(f"{job} payload {actual} does not match {expected}")

        self._limit_check(symbol_info, price)
        if job == ENTRY:
            self._price_band_check(symbol, price)

    def _limit_check(self, symbol_info: dict, price: float) -> None:
        """値幅制限 (PREREG §3.4): a symbol pinned at its limit is not a
        representative auction, and a limit-locked auction may not execute."""
        upper = _as_float(symbol_info.get("UpperLimit"))
        lower = _as_float(symbol_info.get("LowerLimit"))
        if upper is None or lower is None:
            raise SanityError("GET /symbol returned no UpperLimit/LowerLimit")
        if upper > 0 and price >= upper:
            raise SanityError(f"board {price} is at/above the limit up {upper}")
        if lower > 0 and price <= lower:
            raise SanityError(f"board {price} is at/below the limit down {lower}")

    def _price_band_check(self, symbol: str, price: float) -> None:
        """ENTRY ONLY.  A board price far from the last published print means the
        symbol is not the instrument we think it is (a split, a wrong code, a
        stale board).  Deliberately NOT applied on the exit: a diagnostic must
        never keep a real position open overnight (same rule as ON1)."""
        path = self.print_series.get(symbol)
        latest = latest_close_at_or_before(load_daily_series(path),
                                           self._now.date()) if path else None
        if latest is None:
            raise SanityError(
                f"no printed close on/before {self.iso_day} for {symbol} "
                f"({path}); the price band cannot be checked")
        ref_day, ref = latest
        if ref <= 0:
            raise SanityError(f"printed close {ref} for {symbol} is not positive")
        deviation = abs(price - ref) / ref * 100.0
        if deviation > PRICE_BAND_PCT:
            raise SanityError(
                f"board {price} is {deviation:.1f}% from the {ref_day} print {ref} "
                f"(band {PRICE_BAND_PCT}%)")

    # -- send -------------------------------------------------------------
    def _send(self, symbol: str, job: str, payload: dict, context: dict) -> dict | None:
        """The ONLY place an order leaves.  Counts the order first, so an
        ambiguous failure cannot be retried into a second slot."""
        state = self.states[symbol]
        state.count_order(self.day_key)
        if not self.live:
            self.emit(symbol, job, "dry_run_order", payload=payload,
                      reason=self.live_reason, **context)
            return {"OrderId": "", "dry_run": True}
        try:
            result = self.client.send_cash_order(payload)
        except OrderStateUnknown as exc:
            state.set_unknown({"job": job, "day": self.day_key, "symbol": symbol,
                               "side": payload.get("Side"), "qty": payload.get("Qty"),
                               "detail": str(exc), **context})
            self.emit(symbol, job, "order_state_unknown", detail=str(exc),
                      payload=payload, **context)
            return None
        except KabuNetworkError as exc:
            # Provably pre-send: nothing reached kabuステーション.
            self.emit(symbol, job, "order_not_sent", detail=str(exc), **context)
            return None
        except KabuError as exc:
            self.emit(symbol, job, "order_rejected", status=exc.status_code,
                      code=exc.code, detail=exc.message, **context)
            return None
        self.emit(symbol, job, "order_accepted", order_id=result.get("OrderId"),
                  payload=payload, **context)
        return result

    # -- entry ------------------------------------------------------------
    def run_entry_all(self) -> dict[str, str]:
        return {s: self.run_entry(s) for s in self.config.symbols}

    def run_entry(self, symbol: str) -> str:
        job = ENTRY
        blocked = self._blocked(job, symbol)
        if blocked:
            self.emit(symbol, job, "skip", reason=blocked)
            return "skip"
        state = self.states[symbol]
        if state.status != FLAT:
            self.emit(symbol, job, "skip",
                      reason=f"state is {state.status}, not {FLAT}")
            return "skip"
        calendar = self._calendar_skip(symbol)
        if calendar:
            self.emit(symbol, job, "skip", reason=calendar)
            return "skip"

        try:
            held = self._open_rows(symbol)
        except (KabuError, KabuNetworkError, TypeError, ValueError) as exc:
            self.emit(symbol, job, "alert", reason="positions unreadable",
                      detail=str(exc))
            return "alert"
        if held:
            self.emit(symbol, job, "alert", reason="expected a flat account",
                      positions=len(held))
            return "alert"

        try:
            info = dict(self.client.symbol_info(symbol, self.config.exchange) or {})
            board = dict(self.client.board(symbol, self.config.exchange) or {})
        except (KabuError, KabuNetworkError) as exc:
            self.emit(symbol, job, "alert", reason="symbol/board unreadable",
                      detail=str(exc))
            return "alert"
        board_price = _as_float(board.get("CurrentPrice"))
        unit = _as_float(info.get("TradingUnit"))

        expected_unit = EXPECTED_TRADING_UNIT[symbol]
        if unit is not None and int(unit) != expected_unit:
            # PREREG S6: stop THIS symbol and report; the unit changed under us.
            self.pause.trip("S6_trading_unit_changed", symbol,
                            f"TradingUnit {int(unit)} != pre-registered {expected_unit}")
            self.emit(symbol, job, "alert", reason="trading unit changed",
                      trading_unit=int(unit), expected=expected_unit, stop_rule="S6")
            return "alert"

        payload = {
            "Symbol": symbol,
            "Exchange": self.config.exchange,
            "SecurityType": SECURITY_TYPE_STOCK,
            "Side": SIDE_BUY,
            "CashMargin": CASH_MARGIN_CASH,
            "DelivType": DELIV_TYPE_ENTRY,
            "FundType": FUND_TYPE_ENTRY,
            "AccountType": self.config.account_type,
            "Qty": int(unit) if unit is not None else None,
            "FrontOrderType": FRONT_ORDER_TYPE_MOC,
            "Price": 0,
            "ExpireDay": EXPIRE_DAY_TODAY,
        }
        try:
            self._sanity_check(job, symbol, payload, info, board_price)
        except SanityError as exc:
            self.emit(symbol, job, "alert", reason="sanity", detail=str(exc))
            return "alert"

        result = self._send(symbol, job, payload,
                            {"trading_unit": int(unit), "board_price": board_price})
        if result is None:
            return "alert"
        state.set_long({"symbol": symbol, "qty": int(unit), "trading_unit": int(unit),
                        "side": SIDE_BUY, "entry_day": self.day_key,
                        "entry_date": self.iso_day,
                        "exchange": self.config.exchange,
                        "board_close_snapshot": board_price,
                        "order_id": result.get("OrderId") or "",
                        "dry_run": bool(result.get("dry_run"))})
        return "ordered"

    def _open_rows(self, symbol: str) -> list[dict]:
        rows = self.client.positions(product=PRODUCT_CASH, symbol=symbol)
        out = []
        for row in rows:
            if str(row.get("Symbol") or "") not in ("", symbol):
                continue
            if float(row.get("LeavesQty") or 0) > 0:
                out.append(row)
        return out

    # -- exit -------------------------------------------------------------
    def run_exit_all(self) -> dict[str, str]:
        return {s: self.run_exit(s) for s in self.config.symbols}

    def run_exit(self, symbol: str) -> str:
        job = EXIT
        blocked = self._blocked(job, symbol)
        if blocked:
            self.emit(symbol, job, "skip", reason=blocked)
            return "skip"
        state = self.states[symbol]
        position = state.position
        if state.status != LONG or position is None:
            self.emit(symbol, job, "skip",
                      reason=f"state is {state.status}, not {LONG}")
            return "skip"

        qty = int(position.get("qty") or 0)
        if qty != EXPECTED_TRADING_UNIT[symbol] or qty <= 0:
            self.emit(symbol, job, "alert", reason="recorded qty is not one unit",
                      qty=qty)
            return "alert"

        if position.get("dry_run"):
            held_ok, detail = True, "dry-run position; API verification skipped"
        else:
            try:
                held_ok, detail = self._verify_long(symbol, qty)
            except (KabuError, KabuNetworkError) as exc:
                self.emit(symbol, job, "alert", reason="positions unreadable",
                          detail=str(exc))
                return "alert"
        if not held_ok:
            self.emit(symbol, job, "alert", reason="position mismatch", detail=detail,
                      resolution="a human must reconcile the account before this "
                                 "measurement resumes")
            return "alert"

        try:
            info = dict(self.client.symbol_info(symbol, self.config.exchange) or {})
            board = dict(self.client.board(symbol, self.config.exchange) or {})
        except (KabuError, KabuNetworkError) as exc:
            self.emit(symbol, job, "alert", reason="symbol/board unreadable",
                      detail=str(exc))
            return "alert"
        board_price = _as_float(board.get("CurrentPrice"))

        payload = {
            "Symbol": symbol,
            "Exchange": self.config.exchange,
            "SecurityType": SECURITY_TYPE_STOCK,
            "Side": SIDE_SELL,
            "CashMargin": CASH_MARGIN_CASH,
            "DelivType": DELIV_TYPE_EXIT,
            "FundType": FUND_TYPE_EXIT,
            "AccountType": self.config.account_type,
            "Qty": qty,
            "FrontOrderType": FRONT_ORDER_TYPE_MOO,
            "Price": 0,
            "ExpireDay": EXPIRE_DAY_TODAY,
        }
        try:
            self._sanity_check(job, symbol, payload, info, board_price)
        except SanityError as exc:
            self.emit(symbol, job, "alert", reason="sanity", detail=str(exc))
            return "alert"

        result = self._send(symbol, job, payload, {"qty": qty, "note": detail})
        if result is None:
            return "alert"
        # FLAT on ACCEPTANCE, not on a verified fill: at 08:40 the auction has
        # not run, so re-reading /positions here would prove nothing.  An order
        # that did not execute is caught by the entry job, which refuses to open
        # on a non-flat account, and by the ledger finaliser.
        state.add_pending({
            "symbol": symbol,
            "entry_date": str(position.get("entry_date") or ""),
            "exit_date": self.iso_day,
            "trading_unit": int(position.get("trading_unit") or qty),
            "qty": qty,
            "exchange": self.config.exchange,
            "entry_order_id": str(position.get("order_id") or ""),
            "exit_order_id": str(result.get("OrderId") or ""),
            "board_close_snapshot": position.get("board_close_snapshot"),
            "board_open_snapshot": board_price,
            "dry_run": bool(result.get("dry_run")) or bool(position.get("dry_run")),
        })
        state.set_flat()
        return "ordered"

    def _verify_long(self, symbol: str, qty: int) -> tuple[bool, str]:
        rows = self._open_rows(symbol)
        if len(rows) != 1:
            return False, f"{len(rows)} open cash positions in {symbol}, expected 1"
        row = rows[0]
        side = str(row.get("Side") or "")
        if side and side != SIDE_BUY:
            return False, f"held side {side!r} is not long"
        if float(row.get("LeavesQty") or 0) != float(qty):
            return False, f"held qty {row.get('LeavesQty')!r} != {qty}"
        return True, f"verified 1 unit long {symbol}"

    # -- reconcile (READ ONLY) -------------------------------------------
    def reconcile(self, query: QueryOnlyKabu) -> dict[str, str]:
        return {s: self.reconcile_symbol(query, s) for s in self.states}

    def reconcile_symbol(self, query: QueryOnlyKabu, symbol: str) -> str:
        """Positive evidence only.  Absence of evidence leaves STATE_UNKNOWN in
        place; only a human clears it after that."""
        job = "reconcile"
        state = self.states[symbol]
        if state.status != STATE_UNKNOWN:
            self.emit(symbol, job, "skip", reason=f"state is {state.status}")
            return "skip"
        pending = state.data.get("unknown") or {}
        try:
            positions = [r for r in query.positions(product=PRODUCT_CASH, symbol=symbol)
                         if float(r.get("LeavesQty") or 0) > 0]
            orders = query.orders(product=PRODUCT_CASH, symbol=symbol)
        except (KabuError, KabuNetworkError, TypeError, ValueError) as exc:
            self.emit(symbol, job, "unresolved", detail=f"read failed: {exc}")
            return "unresolved"

        expected_qty = float(EXPECTED_TRADING_UNIT[symbol])
        held = [r for r in positions
                if str(r.get("Symbol") or symbol) == symbol
                and str(r.get("Side") or SIDE_BUY) == SIDE_BUY]
        if pending.get("job") == ENTRY:
            if held and float(held[0].get("LeavesQty") or 0) == expected_qty:
                state.set_long({"symbol": symbol, "qty": int(expected_qty),
                                "trading_unit": int(expected_qty), "side": SIDE_BUY,
                                "entry_day": pending.get("day", ""),
                                "entry_date": _iso_of_daykey(pending.get("day", "")),
                                "exchange": self.config.exchange,
                                "board_close_snapshot": None,
                                "order_id": _order_id_of(orders), "dry_run": False})
                self.emit(symbol, job, "resolved", status=LONG)
                return LONG
            if not held and _orders_finished_unfilled(orders):
                state.set_flat()
                self.emit(symbol, job, "resolved", status=FLAT)
                return FLAT
        elif pending.get("job") == EXIT:
            if not held:
                state.set_flat()
                self.emit(symbol, job, "resolved", status=FLAT)
                return FLAT
            if (float(held[0].get("LeavesQty") or 0) == expected_qty
                    and _orders_finished_unfilled(orders)):
                # The exit did not execute, so the ENTRY's position record is
                # still the right one — do not rebuild it and lose the entry day.
                state.set_long(dict(state.position or {}))
                self.emit(symbol, job, "resolved", status=LONG,
                          note="exit did not fill; position still open")
                return LONG
        self.emit(symbol, job, "unresolved",
                  detail="no positive evidence; STATE_UNKNOWN stands",
                  positions=len(positions), orders=len(orders))
        return "unresolved"

    # -- ledger (READ ONLY) ----------------------------------------------
    def finalize_pending(self, query: QueryOnlyKabu) -> list[dict]:
        """Turn staged round trips into ledger rows, once the fills are visible.

        READ ONLY — it is handed the same `QueryOnlyKabu` as `reconcile`, so it
        structurally cannot place an order.  A round trip whose fills are not
        visible yet stays pending; `/orders` is eventually consistent and an
        empty answer is never treated as a non-fill.
        """
        written: list[dict] = []
        for symbol, state in self.states.items():
            still: list[dict] = []
            for row in state.pending:
                result = self._finalize_one(query, symbol, row)
                if result is None:
                    still.append(row)
                else:
                    written.append(result)
            if still != state.pending:
                state.set_pending(still)
        return written

    def _finalize_one(self, query: QueryOnlyKabu, symbol: str,
                      pending: dict) -> dict | None:
        if pending.get("dry_run"):
            self.emit(symbol, "ledger", "skip_dry_run",
                      entry_date=pending.get("entry_date"),
                      exit_date=pending.get("exit_date"))
            return {"skipped": "dry_run", **pending}
        try:
            orders = query.orders(product=PRODUCT_CASH, symbol=symbol, details="true")
        except (KabuError, KabuNetworkError, TypeError, ValueError) as exc:
            self.emit(symbol, "ledger", "unresolved", detail=f"read failed: {exc}")
            return None
        by_id = {str(o.get("ID") or ""): o for o in orders if isinstance(o, dict)}
        entry_row = by_id.get(str(pending.get("entry_order_id") or ""))
        exit_row = by_id.get(str(pending.get("exit_order_id") or ""))
        if entry_row is None or exit_row is None:
            self.emit(symbol, "ledger", "pending",
                      detail="order rows not visible yet; /orders is eventually "
                             "consistent",
                      entry_seen=entry_row is not None, exit_seen=exit_row is not None)
            return None

        buy = parse_fill(entry_row)
        sell = parse_fill(exit_row)
        qty = float(pending.get("qty") or 0)
        excluded = ""
        if buy["price"] is None or sell["price"] is None:
            if not (order_is_finished_unfilled(entry_row)
                    or order_is_finished_unfilled(exit_row)):
                self.emit(symbol, "ledger", "pending",
                          detail="no fill detail yet and neither order is finished")
                return None
            excluded = "not_filled"
        elif buy["qty"] != qty or sell["qty"] != qty:
            excluded = "partial_fill"

        row = self._ledger_row(symbol, pending, entry_row, exit_row, buy, sell,
                               excluded)
        append_ledger_row(self.ledger_path, row)
        self.emit(symbol, "ledger", "row", entry_date=row["entry_date"],
                  exit_date=row["exit_date"], c_bps=row["c_bps"],
                  counted_in_n=row["counted_in_n"], excluded_reason=row["excluded_reason"])
        self._apply_stop_rules(symbol, row)
        return row

    def _ledger_row(self, symbol: str, pending: dict, entry_row: dict, exit_row: dict,
                    buy: dict, sell: dict, excluded: str) -> dict:
        prints = load_daily_series(self.print_series.get(symbol, Path("")))
        index = load_daily_series(self.index_series.get(symbol, Path("")))
        entry_date = str(pending.get("entry_date") or "")
        exit_date = str(pending.get("exit_date") or "")
        print_close = (prints.get(entry_date) or {}).get("close")
        print_open = (prints.get(exit_date) or {}).get("open")
        qty = float(pending.get("qty") or 0)

        notes: list[str] = []
        metrics: dict = {}
        if not excluded and print_close and print_open:
            metrics = round_trip_metrics(
                fill_buy=float(buy["price"]), fill_sell=float(sell["price"]),
                print_close=float(print_close), print_open=float(print_open),
                qty=qty, commission_yen=buy["commission"] + sell["commission"],
                commission_tax_yen=buy["commission_tax"] + sell["commission_tax"])
            approx = metrics["c_bps_approx"]
            if abs(approx - metrics["c_bps"]) > 0.5:
                notes.append(f"c vs first-order approx differ by "
                             f"{approx - metrics['c_bps']:.2f}bps")
        elif not excluded:
            excluded = "print_series_missing"
            notes.append("printed close/open unavailable for this round trip")

        counted = not excluded
        tick_yen = metrics.get("tick_yen")
        if tick_yen is None and print_close:
            tick_yen = float(etf_tick_yen(float(print_close)))
        tick_bps = metrics.get("tick_bps")
        if tick_bps is None and print_close and tick_yen:
            tick_bps = tick_yen / float(print_close) * 1e4

        return {
            "symbol": symbol,
            "entry_date": entry_date,
            "exit_date": exit_date,
            "trading_unit": pending.get("trading_unit"),
            "qty": int(qty),
            "exchange": pending.get("exchange"),
            "exchange_name": str(entry_row.get("ExchangeName")
                                 or exit_row.get("ExchangeName") or ""),
            "entry_order_id": pending.get("entry_order_id"),
            "exit_order_id": pending.get("exit_order_id"),
            "fill_buy": buy["price"],
            "fill_sell": sell["price"],
            "fill_buy_time": buy["time"],
            "fill_sell_time": sell["time"],
            "print_close": print_close,
            "print_open": print_open,
            "print_source": str(self.print_series.get(symbol, "")),
            "board_close_snapshot": pending.get("board_close_snapshot"),
            "board_open_snapshot": pending.get("board_open_snapshot"),
            "idx_close": (index.get(entry_date) or {}).get("close"),
            "idx_open": (index.get(exit_date) or {}).get("open"),
            "tick_yen": tick_yen,
            "tick_bps": tick_bps,
            "e_buy_bps": metrics.get("e_buy_bps"),
            "e_sell_bps": metrics.get("e_sell_bps"),
            "c_bps": metrics.get("c_bps"),
            "c_ticks": metrics.get("c_ticks"),
            "commission_yen": buy["commission"] + sell["commission"],
            "commission_tax_yen": buy["commission_tax"] + sell["commission_tax"],
            "pnl_yen": metrics.get("pnl_yen"),
            "cum_pnl_yen": self._cum_pnl(metrics.get("pnl_yen")),
            "counted_in_n": counted,
            "excluded_reason": excluded,
            "note": "; ".join(notes),
        }

    def _cum_pnl(self, pnl: float | None) -> float | None:
        previous = 0.0
        for row in read_ledger(self.ledger_path):
            value = _as_float(row.get("cum_pnl_yen"))
            if value is not None:
                previous = value
        return previous + float(pnl) if pnl is not None else previous

    def _apply_stop_rules(self, symbol: str, row: dict) -> None:
        """PREREG §6.  Evaluated per round trip, never on an aggregate — the
        aggregate is computed exactly once, at the end (PREREG §5)."""
        state = self.states[symbol]
        tick_bps = _as_float(row.get("tick_bps")) or 0.0
        limit = STOP_TICK_MULTIPLE * tick_bps
        for leg in ("e_buy_bps", "e_sell_bps"):
            value = _as_float(row.get(leg))
            if value is not None and limit > 0 and abs(value) > limit:
                self.pause.trip("S1_leg_deviation", "*",
                                f"{symbol} {leg}={value:.2f}bps exceeds "
                                f"{STOP_TICK_MULTIPLE}x tick ({limit:.2f}bps)")
                self.emit(symbol, "ledger", "stop_rule", stop_rule="S1", leg=leg,
                          value=value, limit=limit)

        if str(row.get("excluded_reason") or "") in ("not_filled", "partial_fill"):
            streak = int(state.data.get("nofill_streak") or 0) + 1
            state.set_nofill_streak(streak)
            if streak >= STOP_CONSECUTIVE_NOFILL:
                self.pause.trip("S3_consecutive_nofill", symbol,
                                f"{streak} consecutive nights without a full fill")
                self.emit(symbol, "ledger", "stop_rule", stop_rule="S3", streak=streak)
        elif row.get("counted_in_n"):
            state.set_nofill_streak(0)

        cum = _as_float(row.get("cum_pnl_yen"))
        if cum is not None and cum < STOP_CUM_PNL_YEN:
            self.pause.trip("S4_cumulative_loss", "*",
                            f"cumulative realised pnl {cum:.0f} yen is below "
                            f"{STOP_CUM_PNL_YEN:.0f}")
            self.emit(symbol, "ledger", "stop_rule", stop_rule="S4", cum_pnl_yen=cum)

        fees = (_as_float(row.get("commission_yen")) or 0.0) + \
               (_as_float(row.get("commission_tax_yen")) or 0.0)
        if fees != 0.0:
            # S7: record, do NOT stop.  The 0-yen SOR assumption is what is
            # being falsified here, and it is a constants question, not a risk.
            self.emit(symbol, "ledger", "commission_not_zero", stop_rule="S7",
                      commission_yen=fees)


def _iso_of_daykey(day_key: str) -> str:
    try:
        return datetime.strptime(str(day_key), "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return ""


def _order_id_of(orders: list[dict]) -> str:
    """Only when the symbol-filtered listing leaves exactly one candidate — a
    guessed id in the ledger is worse than no id."""
    return str(orders[0].get("ID") or "") if len(orders) == 1 else ""


def _orders_finished_unfilled(orders: list[dict]) -> bool:
    """Positive evidence that nothing executed.  An EMPTY listing is not
    evidence — /orders is eventually consistent and has to be allowed to lag a
    fresh acceptance."""
    if not orders:
        return False
    return all(order_is_finished_unfilled(row) for row in orders)


# ---------------------------------------------------------------------------
# wiring


DEFAULT_PRINT_SERIES = {
    "1343": Path("data") / "onr" / "etf_1343_daily.csv",
    "1591": Path("data") / "etf_measure" / "print_1591.csv",
    "1348": Path("data") / "etf_measure" / "print_1348.csv",
}
DEFAULT_INDEX_SERIES = {
    "1343": Path("data") / "onr" / "reit_index_daily.csv",
    "1591": Path("data") / "etf_measure" / "index_1591.csv",
    "1348": Path("data") / "etf_measure" / "index_1348.csv",
}
# Permanent, MD5-stamped dividend snapshots the ex-date exclusion is derived
# from.  1343 and 1591 have their ex-dates frozen into PREREG appendix A ->
# config `skip_dates` instead (their record dates are stated by the issuer);
# 1348's come from its own snapshot, per the PREREG 追記.
DEFAULT_EX_DATE_SOURCES = {
    "1348": (Path("backtest_data") / "jpx_etf_daily_20260906_topix_alt"
             / "1348.T.json"),
}
LEDGER_RELPATH = Path("paper_logs") / "etf_measure_ledger.csv"
STATE_DIRNAME = Path("data") / "etf_measure"


def build_etf_executor(root: str | Path, *, env: dict[str, str] | None = None,
                       now: datetime | None = None, client=None
                       ) -> EtfAuctionExecutor:
    """Assemble the executor from the repo layout.  `client` is injectable so
    tests never construct a real session."""
    import os

    from dotenv import load_dotenv

    from bot.jpx.kabu_client import KabuClient
    from bot.settings import Secret

    root = Path(root)
    load_dotenv(root / ".env")
    env = dict(os.environ) if env is None else env

    config = load_etf_measure_config(root / "config" / "etf_measure.yaml")
    live, reason = resolve_live(env, config)
    if client is None:
        client = KabuClient(Secret(env.get("KABU_API_PASSWORD", "")), port=config.port)
    state_dir = root / STATE_DIRNAME
    states = {s: EtfSymbolState(state_dir / f"state_{s}.json", symbol=s)
              for s in ALLOWED_SYMBOLS}
    return EtfAuctionExecutor(
        client=client,
        states=states,
        config=config,
        kill_switch=KillSwitch(state_dir=root / "data", manual_file=root / "KILL"),
        pause=PauseFlag(state_dir / "paused.json"),
        events_path=state_dir / "events.jsonl",
        ledger_path=root / LEDGER_RELPATH,
        print_series={k: root / v for k, v in DEFAULT_PRINT_SERIES.items()},
        index_series={k: root / v for k, v in DEFAULT_INDEX_SERIES.items()},
        ex_date_sources={k: root / v for k, v in DEFAULT_EX_DATE_SOURCES.items()},
        live=live, live_reason=reason, now=now,
    )

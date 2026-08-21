"""Market view — multi-timeframe trend / volatility / flow snapshot.

Feeds the dashboard's マーケット tab. Pure functions over the files the
collectors already write (1m candles, per-minute flow, OI snapshots, the two
decision logs) — no network, no new state, no clock reads except the caller's
``now``. Every section degrades to None when its file is missing, so the page
renders on a fresh machine with an empty data/ directory.

Two inputs DO come off the network, and neither is fetched here: the caller
(scripts/dashboard.py) does the HTTP and hands the result to a pure function —
``bars_from_executions`` + ``collect_market(live_bars=...)`` for the live 1m
tail, and ``attach_board`` for the order-book depth panel. That keeps this
module testable without a socket and keeps the fetches cacheable where the
rate budget is known.

Definitions come from docs/KNOWLEDGE.md §2 and are NOT re-derived here:

  嵐 (storm)   |30m log-return| >= 0.8%  (research_storm_b.py event definition)
  静穏 (calm)  |30m log-return| < 0.4% AND no 5s burst in the trailing 10m
               (research_calm_range.py). 1m candles cannot see a 5s return, so
               market_state() uses a documented 1m approximation and labels it
               "1m近似" — a weaker filter than the研究 one, never a claim of
               equivalence.

Two rules apply everywhere in this module:

  * the still-forming bucket (``partial: True``) is excluded from every slope,
    accel and vote window — see ``closed_bars``; levels shown AS levels keep it
  * a 1m feed more than STALE_AFTER_SEC behind is not classified at all
    (``market_state`` -> state None, stale True): a stopped collector is not a
    calm market
"""
from __future__ import annotations

import csv
import io
import math
import time
from bisect import bisect_right
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from bot.monitoring.aggregate import _tail_jsonl
from bot.radar import StormRadar

# ---- timeframes ------------------------------------------------------------
TF_MINUTES: dict[str, int] = {"1m": 1, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}
TF_LABELS: dict[str, str] = {"1m": "1分", "15m": "15分", "1h": "1時間",
                             "4h": "4時間", "1d": "日足"}
TF_ORDER: list[str] = ["1m", "15m", "1h", "4h", "1d"]
# The owner scalps on the 1m chart and reads direction off the higher frames,
# so the chart opens where the trading happens.
DEFAULT_TF = "1m"

# ---- per-timeframe chart geometry ------------------------------------------
# The trailing-range band is only useful at the scale being traded: a 240m band
# on a 1m scalp chart is a horizon, and a 240m band on the daily chart is one
# candle. One window per timeframe, roughly "the last few visible bars".
RANGE_WINDOW_BY_TF: dict[str, int] = {"1m": 15, "15m": 60, "1h": 240,
                                      "4h": 1440, "1d": 10080}
# Vertical gridlines land on natural clock boundaries, not on every Nth bar.
TIME_GRID_MIN: dict[str, int] = {"1m": 5, "15m": 60, "1h": 240,
                                 "4h": 1440, "1d": 10080}
PRICE_GRID_TARGET = 10   # aim for ~10 horizontal gridlines (1/2/5 x 10^k JPY)
DAY_SEC = 86400

# ---- indicator constants ---------------------------------------------------
EMA_FAST = 12
EMA_SLOW = 48
RSI_PERIOD = 14
ATR_PERIOD = 14
SLOPE_BARS = 10          # slope votes / accel look back this many bars
ANGLE_SCALE = 6.0        # 1% per-bar relative slope -> 6 deg; +-10% saturates
ANGLE_MAX = 60.0

# ---- state constants (docs/KNOWLEDGE.md §2) --------------------------------
STORM_RET = 0.008        # |30m log-return| >= 0.8%
CALM_RET = 0.004         # |30m log-return| < 0.4%
CALM_BURST_RET = 0.0015  # 1m approximation of the 5s burst filter
CALM_BURST_LOOKBACK = 10  # minutes
BREAK_WINDOW = 240       # trailing high/low window, minutes
BREAK_RECENT = 15        # the break must have happened within this many minutes
STALE_AFTER_SEC = 600    # a 1m feed this far behind is stopped, not "calm"

FLOW_TAIL_BYTES = 512 * 1024   # ~4000 minutes of data/flow_*.csv
LOG_TAIL_BYTES = 4 * 1024 * 1024   # logs/bot.jsonl / data/scalp_paper.jsonl tail
FLOW_SPLIT_MIN = 60            # taker split is reported over the last hour

# ---- order book ------------------------------------------------------------
# The depth panel shares the chart's y-axis, so only levels that can land on it
# are worth carrying; anything further out is summarised into the totals.
BOARD_RANGE_PCT = 2.0          # keep levels within +-2% of mid
BOARD_MAX_LEVELS = 600         # per side, after the +-2% filter

STRENGTH = {0: "—", 1: "弱", 2: "中", 3: "強"}
NON_FILL_STATES = {"PENDING_SUBMIT", "SUBMITTED", "CANCELED", "REJECTED",
                   "STATE_UNKNOWN"}
PRODUCT = "FX_BTC_JPY"


# ---------------------------------------------------------------------------
# file readers (tail-bounded; every one returns empty on a missing file)
# ---------------------------------------------------------------------------
def _f(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _pos(value: float | None, fallback: float) -> float:
    """A usable (finite, positive) price, or ``fallback``."""
    return value if value is not None and value > 0.0 else fallback


_DAY_EPOCH: dict[str, float] = {}


def _epoch(text: str) -> float | None:
    """"2026-07-21 08:17:00+00:00" / ISO-T form -> unix seconds (UTC).

    The collectors write one fixed shape, so that shape takes a fast path with
    a per-day cache — fromisoformat on 40k+ candle rows is the single most
    expensive thing this module does. Anything else falls back to the parser.
    """
    s = str(text).strip()
    if len(s) == 25 and s[10] in " T" and s[19] == "+" and s[20:] == "00:00":
        day = _DAY_EPOCH.get(s[:10])
        if day is None:
            try:
                day = datetime.fromisoformat(s[:10]).replace(
                    tzinfo=timezone.utc).timestamp()
            except ValueError:
                day = None
            if day is not None:
                _DAY_EPOCH[s[:10]] = day
        if day is not None:
            try:
                return day + int(s[11:13]) * 3600 + int(s[14:16]) * 60 + int(s[17:19])
            except ValueError:
                pass
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def _read_csv_tail(path: Path, max_bytes: int = 32 * 1024 * 1024) -> list[dict[str, str]]:
    """Header + the last ``max_bytes`` of rows. Partial first line is dropped."""
    try:
        size = path.stat().st_size
        with open(path, "rb") as fh:
            header = fh.readline()
            body_start = fh.tell()
            start = max(body_start, size - max_bytes)
            fh.seek(start)
            body = fh.read()
    except OSError:
        return []
    cols = header.decode("utf-8", errors="replace").strip().split(",")
    text = body.decode("utf-8", errors="replace")
    if start > body_start:
        # seeked into the middle of a row: drop the partial first line
        text = text.split("\n", 1)[1] if "\n" in text else ""
    rows = []
    for values in csv.reader(io.StringIO(text)):
        if len(values) == len(cols):
            rows.append(dict(zip(cols, values)))
    return rows


def read_candles(path: Path, max_bytes: int = 32 * 1024 * 1024) -> list[dict[str, float]]:
    """data/candles_*.csv or data/flow_*.csv -> ascending 1m bars.

    Both files share the ts,open,high,low,close,volume prefix; flow adds
    buy_vol/sell_vol/trades, which are carried through when present.

    A row whose close is missing, non-finite or <= 0 is dropped: every
    downstream return is a ratio or a log of one, so a zero close would be a
    division by zero rather than a bar worth drawing. The other prices fall
    back to the close when they are unusable, for the same reason.
    """
    bars: list[dict[str, float]] = []
    for row in _read_csv_tail(path, max_bytes):
        ts = _epoch(row.get("ts", ""))
        close = _f(row.get("close"))
        if ts is None or close is None or close <= 0.0:
            continue
        volume = _f(row.get("volume"))
        bar = {
            "ts": ts,
            "open": _pos(_f(row.get("open")), close),
            "high": _pos(_f(row.get("high")), close),
            "low": _pos(_f(row.get("low")), close),
            "close": close,
            "volume": max(volume, 0.0) if volume is not None else 0.0,
        }
        for extra in ("buy_vol", "sell_vol"):
            value = _f(row.get(extra))
            if value is not None:
                bar[extra] = value
        bars.append(bar)
    bars.sort(key=lambda b: b["ts"])
    return bars


# ---------------------------------------------------------------------------
# resampling
# ---------------------------------------------------------------------------
def resample(candles_1m: Sequence[dict], tf: str) -> list[dict]:
    """1m bars -> ``tf`` bars on UTC-aligned buckets.

    Buckets are floor(ts / step) * step, so every timeframe lines up with UTC
    midnight (the 4h grid is 00/04/08/... UTC, the daily bar is a UTC day).
    The last bucket is emitted even when it is still filling; it carries
    ``partial: True`` so callers can say so instead of guessing.
    """
    step = TF_MINUTES[tf] * 60
    out: list[dict] = []
    for bar in candles_1m:
        bucket = math.floor(bar["ts"] / step) * step
        if out and out[-1]["ts"] == bucket:
            cur = out[-1]
            cur["high"] = max(cur["high"], bar["high"])
            cur["low"] = min(cur["low"], bar["low"])
            cur["close"] = bar["close"]
            cur["volume"] += bar["volume"]
            cur["bars"] += 1
            for extra in ("buy_vol", "sell_vol"):
                if extra in bar:
                    cur[extra] = cur.get(extra, 0.0) + bar[extra]
            if bar.get("live"):
                cur["live"] = True
        else:
            cur = {"ts": bucket, "open": bar["open"], "high": bar["high"],
                   "low": bar["low"], "close": bar["close"],
                   "volume": bar["volume"], "bars": 1}
            for extra in ("buy_vol", "sell_vol"):
                if extra in bar:
                    cur[extra] = bar[extra]
            if bar.get("live"):
                cur["live"] = True
            out.append(cur)
    for bar in out:
        bar["partial"] = False
    if out:
        out[-1]["partial"] = out[-1]["bars"] < TF_MINUTES[tf]
    return out


def closed_bars(bars: Sequence[dict]) -> list[dict]:
    """The bars whose bucket has finished — ``partial: True`` ones dropped.

    Ten minutes into a 4h bucket the bucket's volume is 1/24 of a full one and
    its range is a fraction of one: fed to a slope that reads as a collapse.
    Every slope / accel / vote window in this module therefore runs on closed
    buckets only; levels the UI shows as levels (last close, taker share) may
    still come from the forming bar, and say so via ``partial``.
    """
    return [b for b in bars if not b.get("partial")]


# ---------------------------------------------------------------------------
# live 1m tail
#
# data/candles_*.csv is rewritten by the fetch task every ~15 minutes, so on a
# 1m scalp chart the newest CSV bar is routinely 10+ minutes old — old enough
# for market_state's staleness guard to refuse to classify a perfectly live
# market. The dashboard therefore fetches the public execution tape itself and
# builds the missing minutes here. Those bars are marked ``live`` so the page
# can draw them as what they are: a partial, unarchived tail.
# ---------------------------------------------------------------------------
def bars_from_executions(executions: Sequence[dict]) -> list[dict]:
    """bitFlyer /v1/executions rows -> ascending 1m bars with a taker split.

    The oldest bucket is flagged ``truncated``: the fetched window starts
    wherever ``count`` ran out, not on a minute boundary, so that bucket's
    volume is a floor rather than the minute's real volume.
    """
    buckets: dict[float, dict[str, Any]] = {}
    for row in executions:
        price = _f(row.get("price"))
        size = _f(row.get("size"))
        ts = _epoch(str(row.get("exec_date") or ""))
        if ts is None or price is None or price <= 0.0:
            continue
        size = max(size, 0.0) if size is not None else 0.0
        start = math.floor(ts / 60.0) * 60.0
        bar = buckets.get(start)
        if bar is None:
            buckets[start] = {
                "ts": start, "open": price, "high": price, "low": price,
                "close": price, "volume": size, "buy_vol": 0.0, "sell_vol": 0.0,
                "trades": 0, "live": True, "_first": ts, "_last": ts,
            }
            bar = buckets[start]
        else:
            if ts < bar["_first"]:
                bar["_first"], bar["open"] = ts, price
            if ts >= bar["_last"]:
                bar["_last"], bar["close"] = ts, price
            bar["high"] = max(bar["high"], price)
            bar["low"] = min(bar["low"], price)
            bar["volume"] += size
        side = str(row.get("side") or "").upper()
        if side == "BUY":
            bar["buy_vol"] += size
        elif side == "SELL":
            bar["sell_vol"] += size
        bar["trades"] += 1
    out = [buckets[k] for k in sorted(buckets)]
    for bar in out:
        bar.pop("_first", None)
        bar.pop("_last", None)
    if out:
        out[0]["truncated"] = True
    return out


def merge_live_bars(csv_bars: Sequence[dict],
                    live_bars: Sequence[dict]) -> list[dict]:
    """CSV bars plus the live minutes the CSV does not have yet, ascending.

    The CSV always wins on an overlapping minute: it is the archived, complete
    bucket, while the live one only holds whatever executions the fetch window
    reached back to. Nothing is mutated — the live bars are copied — so the
    caller can hand the same live tail to more than one consumer.
    """
    out = [dict(b) for b in csv_bars]
    if live_bars:
        have = {b["ts"] for b in out}
        out.extend(dict(b) for b in live_bars if b["ts"] not in have)
        out.sort(key=lambda b: b["ts"])
    return out


def overlay_flow(candles: list[dict], flow_bars: Sequence[dict]) -> int:
    """Copy data/flow_*.csv's taker split onto the matching candle minutes.

    data/candles_*.csv carries no buy/sell columns, so without this the volume
    pane could only ever draw one undifferentiated column. Only exact timestamp
    matches are filled — a minute the flow recorder missed stays split-less
    rather than borrowing a neighbour's split. Mutates ``candles`` in place and
    returns how many minutes were filled.
    """
    if not candles or not flow_bars:
        return 0
    split = {b["ts"]: b for b in flow_bars if "buy_vol" in b and "sell_vol" in b}
    if not split:
        return 0
    filled = 0
    for bar in candles:
        src = split.get(bar["ts"])
        if src is None or "buy_vol" in bar:
            continue
        bar["buy_vol"], bar["sell_vol"] = src["buy_vol"], src["sell_vol"]
        filled += 1
    return filled


# ---------------------------------------------------------------------------
# chart grids (server-side so the depth panel can share the price buckets)
# ---------------------------------------------------------------------------
def nice_step(span: float, target: int = PRICE_GRID_TARGET) -> float:
    """A 1/2/5 x 10^k step that puts about ``target`` gridlines across ``span``.

    Candidates that land in 8..12 lines are preferred; when none does (the
    1/2/5 ladder jumps by 2.5x, so that happens on some spans) the closest in
    log space wins. Never returns 0.
    """
    if not (span > 0.0) or not math.isfinite(span):
        return 1.0
    raw = span / max(target, 1)
    k = math.floor(math.log10(raw)) if raw > 0 else 0
    candidates = [m * (10.0 ** e) for e in (k - 1, k, k + 1) for m in (1.0, 2.0, 5.0)]
    best, best_rank = None, None
    for step in candidates:
        if step <= 0:
            continue
        lines = span / step
        rank = (0 if 8.0 <= lines <= 12.0 else 1, abs(math.log(lines / target)))
        if best_rank is None or rank < best_rank:
            best, best_rank = step, rank
    return best if best else 1.0


def price_grid(lo: float, hi: float, step: float) -> list[float]:
    """The gridline prices inside [lo, hi] on a ``step`` ladder from 0."""
    if not (step > 0.0) or not (hi > lo):
        return []
    first = math.ceil(lo / step)
    last = math.floor(hi / step)
    if last - first > 200:          # a pathological step: refuse to spray lines
        return []
    return [round(i * step, 6) for i in range(first, last + 1)]


def _is_week_start(ts: float) -> bool:
    """UTC Monday 00:00. Epoch day 0 was a Thursday, hence the +3."""
    if ts % DAY_SEC:
        return False
    return (int(ts // DAY_SEC) + 3) % 7 == 0


def time_grid(bars: Sequence[dict], tf: str) -> list[dict[str, Any]]:
    """Vertical gridlines on clock boundaries, as bar indices.

    Buckets are UTC-aligned (see ``resample``), so a boundary is just a bar
    whose own start sits on it. Boundaries that fall inside a data gap have no
    bar and are skipped rather than drawn on the neighbouring bar. ``major``
    marks UTC midnight — the one line the eye should be able to find.
    """
    period = TIME_GRID_MIN.get(tf, 60) * 60
    weekly = period >= 7 * DAY_SEC
    out: list[dict[str, Any]] = []
    for i, bar in enumerate(bars):
        ts = bar["ts"]
        on_grid = _is_week_start(ts) if weekly else (ts % period == 0)
        if on_grid:
            out.append({"i": i, "ts": ts, "major": ts % DAY_SEC == 0})
    return out


def window_label(minutes: int) -> str:
    """15 -> 「15分」, 60 -> 「1時間」, 1440 -> 「24時間」, 10080 -> 「7日」.

    A day is spelled as 24時間 rather than 1日 — the band is a rolling window
    ending now, not a calendar day, and "24時間" says that without ambiguity.
    """
    if minutes < 60:
        return f"{minutes}分"
    if minutes <= 1440:
        return f"{minutes / 60.0:g}時間"
    return f"{minutes / 1440.0:g}日"


# ---------------------------------------------------------------------------
# order book
# ---------------------------------------------------------------------------
def normalize_board(board: Any, now: float | None = None) -> dict[str, Any] | None:
    """A bitFlyer /v1/board snapshot -> the trimmed shape the panel draws.

    Levels further than ``BOARD_RANGE_PCT`` from mid cannot land on a chart's
    y-axis, so they are dropped from the ladder but still counted in the
    ``*_total_all`` figures: the panel says how much of the book it is showing
    rather than quietly implying it shows all of it. Any unusable snapshot
    (None, wrong shape, empty, crossed) returns None — the panel then renders
    its 「板情報なし」 empty state.
    """
    if not isinstance(board, dict):
        return None
    sides: dict[str, list[list[float]]] = {}
    totals_all: dict[str, float] = {}
    for key in ("bids", "asks"):
        rows = board.get(key)
        if not isinstance(rows, list):
            return None
        levels: list[list[float]] = []
        total = 0.0
        for row in rows:
            if not isinstance(row, dict):
                continue
            price, size = _f(row.get("price")), _f(row.get("size"))
            if price is None or size is None or price <= 0.0 or size <= 0.0:
                continue
            levels.append([price, size])
            total += size
        if not levels:
            return None
        levels.sort(key=lambda lv: lv[0], reverse=(key == "bids"))
        sides[key] = levels
        totals_all[key] = total

    best_bid, best_ask = sides["bids"][0][0], sides["asks"][0][0]
    if best_bid >= best_ask:
        return None                      # crossed / locked snapshot: not usable
    mid = _f(board.get("mid_price")) or (best_bid + best_ask) / 2.0
    lo = mid * (1.0 - BOARD_RANGE_PCT / 100.0)
    hi = mid * (1.0 + BOARD_RANGE_PCT / 100.0)
    near = {"bids": [lv for lv in sides["bids"] if lv[0] >= lo][:BOARD_MAX_LEVELS],
            "asks": [lv for lv in sides["asks"] if lv[0] <= hi][:BOARD_MAX_LEVELS]}
    return {
        "mid": mid,
        "best_bid": best_bid,
        "best_ask": best_ask,
        "spread": round(best_ask - best_bid, 4),
        "bids": [[lv[0], round(lv[1], 8)] for lv in near["bids"]],
        "asks": [[lv[0], round(lv[1], 8)] for lv in near["asks"]],
        "bid_total": round(sum(lv[1] for lv in near["bids"]), 6),
        "ask_total": round(sum(lv[1] for lv in near["asks"]), 6),
        "bid_total_all": round(totals_all["bids"], 6),
        "ask_total_all": round(totals_all["asks"], 6),
        "range_pct": BOARD_RANGE_PCT,
        "fetched_at": now,
    }


def board_depth(board: dict[str, Any] | None, lo: float, hi: float,
                step: float) -> dict[str, Any] | None:
    """Bucket a normalized board into the chart's own price gridline buckets.

    The panel sits beside the price pane and shares its y-axis, so a depth bar
    must line up with the prices next to it — which means bucketing on the very
    ladder ``price_grid`` draws, not on a ladder of the book's own choosing.
    Levels outside the visible [lo, hi] are dropped (they have nowhere to go)
    and counted in ``outside``.
    """
    if not board or not (step > 0.0) or not (hi > lo):
        return None
    start = math.floor(lo / step) * step
    count = int(math.ceil((hi - start) / step))
    if count <= 0 or count > 400:
        return None
    bid = [0.0] * count
    ask = [0.0] * count
    outside = 0
    for key, sink in (("bids", bid), ("asks", ask)):
        for price, size in board.get(key, ()):
            idx = int(math.floor((price - start) / step))
            if 0 <= idx < count:
                sink[idx] += size
            else:
                outside += 1
    top = max(max(bid), max(ask))
    return {
        "step": step,
        "start": start,
        "count": count,
        "buckets": [{"p": round(start + i * step, 6),
                     "bid": round(bid[i], 6), "ask": round(ask[i], 6)}
                    for i in range(count) if bid[i] or ask[i]],
        "max": round(top, 6),
        "bid_sum": round(sum(bid), 6),
        "ask_sum": round(sum(ask), 6),
        "outside": outside,
        "mid": board.get("mid"),
    }


def attach_board(payload: dict[str, Any], board: Any,
                 now: float | None = None) -> dict[str, Any]:
    """Fold a raw board snapshot into an assembled ``collect_market`` payload.

    Kept out of ``collect_market`` because the snapshot comes off the network:
    the file-driven payload stays cacheable and testable without one, and a
    failed fetch simply attaches None. Mutates and returns ``payload``.
    """
    normalized = normalize_board(board, now=now)
    payload["board"] = normalized
    chart = payload.get("chart")
    if not isinstance(chart, dict):
        return payload
    for tf_chart in (chart.get("tfs") or {}).values():
        scale = tf_chart.get("scale") if isinstance(tf_chart, dict) else None
        tf_chart["depth"] = (
            board_depth(normalized, scale["lo"], scale["hi"], scale["step"])
            if normalized and scale else None)
    return payload


# ---------------------------------------------------------------------------
# indicators
# ---------------------------------------------------------------------------
def ema(values: Sequence[float], period: int) -> list[float]:
    """Recursive EMA seeded on the first value (alpha = 2/(n+1))."""
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    out = [float(values[0])]
    for v in values[1:]:
        out.append(out[-1] + alpha * (float(v) - out[-1]))
    return out


def rsi(values: Sequence[float], period: int = RSI_PERIOD) -> float | None:
    """Wilder RSI over the whole series; None when there is not enough data."""
    if len(values) < period + 1:
        return None
    gains = losses = 0.0
    for i in range(1, period + 1):
        delta = float(values[i]) - float(values[i - 1])
        gains += max(delta, 0.0)
        losses += max(-delta, 0.0)
    avg_gain, avg_loss = gains / period, losses / period
    for i in range(period + 1, len(values)):
        delta = float(values[i]) - float(values[i - 1])
        avg_gain = (avg_gain * (period - 1) + max(delta, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-delta, 0.0)) / period
    if avg_loss == 0.0:
        return 100.0 if avg_gain > 0.0 else 50.0
    return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)


def atr_series(candles: Sequence[dict], period: int = ATR_PERIOD) -> list[float]:
    """Wilder ATR, one value per bar from index ``period`` onwards."""
    if len(candles) < period + 1:
        return []
    trs = []
    for prev, cur in zip(candles, candles[1:]):
        trs.append(max(cur["high"] - cur["low"],
                       abs(cur["high"] - prev["close"]),
                       abs(cur["low"] - prev["close"])))
    if len(trs) < period:
        return []
    out = [sum(trs[:period]) / period]
    for tr in trs[period:]:
        out.append((out[-1] * (period - 1) + tr) / period)
    return out


def _sign(value: float, eps: float = 0.0) -> int:
    return 1 if value > eps else (-1 if value < -eps else 0)


def _slope(values: Sequence[float]) -> float:
    """Least-squares slope per step over the given points."""
    n = len(values)
    if n < 2:
        return 0.0
    mean_x = (n - 1) / 2.0
    mean_y = sum(values) / n
    num = sum((i - mean_x) * (float(v) - mean_y) for i, v in enumerate(values))
    den = sum((i - mean_x) ** 2 for i in range(n))
    return num / den if den else 0.0


def slope_angle(values: Sequence[float], bars: int = SLOPE_BARS,
                scale: float = ANGLE_SCALE) -> dict[str, Any]:
    """Relative slope of the last ``bars``+1 points, as an arrow angle.

    ``accel`` is the per-bar slope divided by the window's mean level, i.e. a
    fraction per bar; ``angle_deg`` is that in percent times ``scale``, clamped
    to +-60 so the arrow stays readable (10%/bar saturates it).
    """
    window = [float(v) for v in values[-(bars + 1):]]
    if len(window) < 2:
        return {"accel": None, "angle_deg": None, "bars": len(window)}
    level = sum(abs(v) for v in window) / len(window)
    if level == 0.0:
        return {"accel": 0.0, "angle_deg": 0.0, "bars": len(window)}
    accel = _slope(window) / level
    angle = max(-ANGLE_MAX, min(ANGLE_MAX, accel * 100.0 * scale))
    return {"accel": round(accel, 6), "angle_deg": round(angle, 1),
            "bars": len(window)}


# ---------------------------------------------------------------------------
# trend / volatility / volume / OI
# ---------------------------------------------------------------------------
def series_trend(values: Sequence[float],
                 slope_values: Sequence[float] | None = None) -> dict[str, Any]:
    """Three-vote trend score in [-3..+3] over an arbitrary series.

    Votes (each +1/0/-1, or None when the series is too short for it):
      ema_cross  EMA12 above/below EMA48
      ema_slope  sign of the EMA48 change over the last 10 bars
      rsi        RSI14 above/below 50

    ``slope_values`` is the series the SLOPE vote runs on when it differs from
    the level series — the closed-bucket closes, so a bucket that is ten
    minutes old cannot bend the slope (see ``closed_bars``). The level votes
    (cross, RSI) keep the forming bar: that is where the price is now.

    The per-vote breakdown is returned so the UI can show WHICH votes were
    available — a score of +2 out of 2 votes is not the same fact as +2 out
    of 3, and the tooltip says so rather than hiding the difference.
    """
    values = [float(v) for v in values]
    same = slope_values is None
    slope_series = values if same else [float(v) for v in slope_values]
    votes: dict[str, int | None] = {"ema_cross": None, "ema_slope": None, "rsi": None}
    slow: list[float] | None = None
    if len(values) >= EMA_SLOW:
        slow = ema(values, EMA_SLOW)
        votes["ema_cross"] = _sign(ema(values, EMA_FAST)[-1] - slow[-1])
    if len(slope_series) >= SLOPE_BARS + 1:
        # reuse the EMA48 already computed above when it is the same series
        slope_ema = slow if (same and slow is not None) else ema(slope_series, EMA_SLOW)
        votes["ema_slope"] = _sign(slope_ema[-1] - slope_ema[-1 - SLOPE_BARS])
    rsi_value = rsi(values)
    if rsi_value is not None:
        votes["rsi"] = _sign(rsi_value - 50.0)
    live = [v for v in votes.values() if v is not None]
    score = sum(live) if live else None
    return {
        "score": score,
        "votes": votes,
        "votes_available": len(live),
        "rsi": round(rsi_value, 1) if rsi_value is not None else None,
        "strength": STRENGTH.get(abs(score), "強") if score is not None else None,
        "direction": _sign(score) if score is not None else None,
    }


def trend(tf_candles: Sequence[dict]) -> dict[str, Any]:
    """Trend vote over the closes of one timeframe.

    The forming bucket counts for the level votes (its close IS the current
    price) but not for the slope one — ``closed_bars`` explains why.
    """
    return series_trend([c["close"] for c in tf_candles],
                        [c["close"] for c in closed_bars(tf_candles)])


def volatility(tf_candles: Sequence[dict]) -> dict[str, Any]:
    """ATR14 as a 値幅: absolute JPY range, % of price, and its slope arrow.

    Closed buckets only: the forming bucket's range is a partial range, and it
    would drag both the ATR and its arrow down for no market reason.
    """
    closed = closed_bars(tf_candles)
    series = atr_series(closed)
    if not series:
        return {"atr": None, "atr_pct": None, "accel": None, "angle_deg": None,
                "bars": len(closed)}
    last_close = closed[-1]["close"]
    atr = series[-1]
    arrow = slope_angle(series)
    return {
        "atr": round(atr, 1),
        "atr_pct": round(atr / last_close * 100.0, 3) if last_close else None,
        "accel": arrow["accel"],
        "angle_deg": arrow["angle_deg"],
        "bars": len(closed),
    }


def volume_trend(bars: Sequence[dict]) -> dict[str, Any]:
    """Trend + accel arrow over per-bar volume (candles or flow rows).

    Volume is the one series where even the LEVEL of a forming bucket is
    wrong — ten minutes into a 4h bucket it holds 1/24 of a bucket's trade —
    so every field here comes from closed buckets (``closed_bars``).

    When the rows carry a taker split (data/flow_*.csv) the latest buy share is
    reported alongside — it is a level, not part of the vote.
    """
    closed = closed_bars(bars)
    volumes = [b.get("volume", 0.0) for b in closed]
    out = series_trend(volumes)
    out.update(slope_angle(volumes))
    last = closed[-1] if closed else {}
    buy, sell = last.get("buy_vol"), last.get("sell_vol")
    total = (buy or 0.0) + (sell or 0.0)
    out["buy_share"] = round(buy / total * 100.0, 1) if buy is not None and total else None
    out["last"] = round(volumes[-1], 4) if volumes else None
    out["bars_used"] = len(closed)
    out["partial_excluded"] = len(bars) - len(closed)
    return out


def taker_split(flow_bars: Sequence[dict], minutes: int = FLOW_SPLIT_MIN) -> dict[str, Any] | None:
    """Buy/sell taker share over the last ``minutes`` of data/flow_*.csv.

    None when the file is absent or carries no split (plain candles do not).
    """
    if not flow_bars:
        return None
    cutoff = flow_bars[-1]["ts"] - minutes * 60
    window = [b for b in flow_bars if b["ts"] > cutoff and "buy_vol" in b]
    buy = sum(b.get("buy_vol", 0.0) for b in window)
    sell = sum(b.get("sell_vol", 0.0) for b in window)
    if not window or buy + sell <= 0:
        return None
    return {
        "window_min": minutes,
        "buy_vol": round(buy, 4),
        "sell_vol": round(sell, 4),
        "buy_pct": round(buy / (buy + sell) * 100.0, 1),
        "bars": len(window),
        "last_ts": flow_bars[-1]["ts"],
    }


def oi_trend(oi_rows: Sequence[dict], column: str = "okx_usdt_oi") -> dict[str, Any] | None:
    """OKX USDT open interest trend from data/oi_snapshots.csv rows.

    The recorder writes one row every ~15 minutes and started recently, so the
    history is short and sometimes sparse (blank cells). Missing values are
    dropped rather than interpolated, and every derived field stays None until
    there are enough points for it — a two-row file must not draw an arrow.
    """
    if not oi_rows:
        return None
    points = [(row.get("ts_utc"), _f(row.get(column))) for row in oi_rows]
    values = [v for _, v in points if v is not None]
    if not values:
        return None
    out = series_trend(values)
    out.update(slope_angle(values))
    dvol = next((_f(r.get("dvol")) for r in reversed(oi_rows)
                 if _f(r.get("dvol")) is not None), None)
    ls = next((_f(r.get("okx_ls_ratio")) for r in reversed(oi_rows)
               if _f(r.get("okx_ls_ratio")) is not None), None)
    stamps = [_epoch(t or "") for t, v in points if v is not None]
    stamps = [s for s in stamps if s is not None]
    last_ts = stamps[-1] if stamps else None
    out.update({
        "column": column,
        "last": values[-1],
        "points": len(values),
        "rows": len(oi_rows),
        "dvol": dvol,
        "ls_ratio": ls,
        "last_ts": last_ts,
        # 30 days of 15-minute rows is the pre-registered bar for the OI gate
        # (docs/KNOWLEDGE.md §4); until then this is a read-out, not a signal.
        "history_hours": round((stamps[-1] - stamps[0]) / 3600.0, 1)
        if len(stamps) >= 2 else None,
    })
    return out


# ---------------------------------------------------------------------------
# market state
# ---------------------------------------------------------------------------
def _stamps(candles: Sequence[dict], stamps: list[float] | None = None) -> list[float]:
    """The ts column, built once and passed around — rebuilding it per lookup
    turns a 10-bar burst scan over 40k candles into 400k list writes."""
    return [c["ts"] for c in candles] if stamps is None else stamps


def _bar_at_or_before(candles: Sequence[dict], ts: float,
                      stamps: list[float] | None = None) -> dict | None:
    idx = bisect_right(_stamps(candles, stamps), ts) - 1
    return candles[idx] if idx >= 0 else None


def _ret_over(candles: Sequence[dict], minutes: int,
              stamps: list[float] | None = None) -> float | None:
    """Simple return from the bar at or before now-``minutes`` to the last bar.

    None when no bar sits anywhere near that point. With the live tail merged
    in, a dead collector leaves a hole between the last CSV bar and the live
    minutes: the "30 minutes ago" bar is then a day old, and reporting that
    day's move as a 30-minute return would light the storm pill on a quiet
    market. Half the window is the tolerance (5 minutes at minimum).
    """
    if not candles:
        return None
    last = candles[-1]
    target = last["ts"] - minutes * 60
    ref = _bar_at_or_before(candles, target, stamps)
    if ref is None or ref is last or not ref["close"]:
        return None
    if target - ref["ts"] > max(300.0, minutes * 30.0):
        return None                  # a hole, not a lookback
    return last["close"] / ref["close"] - 1.0


def _log_ret_over(candles: Sequence[dict], minutes: int,
                  stamps: list[float] | None = None) -> float | None:
    simple = _ret_over(candles, minutes, stamps)
    return math.log(1.0 + simple) if simple is not None and simple > -1.0 else None


def market_state(candles_1m: Sequence[dict], now: float | None = None,
                 radar: StormRadar | None = None,
                 stamps: list[float] | None = None) -> dict[str, Any] | None:
    """嵐 / ブレイク / 静穏レンジ / 通常 for the state strip.

    Checked in that order — a storm that also broke the range is a storm. The
    calm branch is the 1m approximation of the research calm filter (see the
    module docstring) and carries ``approx: "1m近似"`` so the UI can label it.

    A feed more than ``STALE_AFTER_SEC`` behind is not classified at all:
    ``state`` is None and ``stale`` is True, because "静穏レンジ" over a
    collector that died yesterday is a false statement about the market, not a
    stale reading of it. ``stamps`` is the candles' ts column when the caller
    already has it.
    """
    if not candles_1m:
        return None
    now = now if now is not None else time.time()
    radar = radar or StormRadar()
    stamps = _stamps(candles_1m, stamps)
    last = candles_1m[-1]
    age = now - last["ts"]
    if age > STALE_AFTER_SEC:
        return {
            "state": None,
            "stale": True,
            "approx": None,
            "last_price": last["close"],
            "last_ts": last["ts"],
            "age_sec": round(age, 1),
            "ret_30m_pct": None,
            "ret_24h_pct": None,
            "radar": radar.state(now),
            "detail": {"stale_after_sec": STALE_AFTER_SEC},
        }
    ret30 = _log_ret_over(candles_1m, 30, stamps)
    ret24 = _ret_over(candles_1m, 1440, stamps)

    # break: beyond the trailing 240m high/low, and it happened in the last 15m
    recent = candles_1m[bisect_right(stamps, last["ts"] - BREAK_RECENT * 60):]
    ref = candles_1m[bisect_right(stamps, last["ts"] - (BREAK_WINDOW + BREAK_RECENT) * 60):
                     bisect_right(stamps, last["ts"] - BREAK_RECENT * 60)]
    broke_up = broke_down = None
    if ref and recent:
        ref_high = max(c["high"] for c in ref)
        ref_low = min(c["low"] for c in ref)
        broke_up = max(c["high"] for c in recent) > ref_high
        broke_down = min(c["low"] for c in recent) < ref_low

    burst = None
    if len(candles_1m) >= 2:
        window = candles_1m[bisect_right(stamps, last["ts"] - CALM_BURST_LOOKBACK * 60):]
        prevs = [_bar_at_or_before(candles_1m, c["ts"] - 60, stamps) for c in window]
        burst = any(
            p is not None and p["close"] and
            abs(math.log(c["close"] / p["close"])) >= CALM_BURST_RET
            for c, p in zip(window, prevs))

    state, approx = "通常", None
    if ret30 is not None and abs(ret30) >= STORM_RET:
        state = "嵐"
    elif broke_up or broke_down:
        state = "ブレイク"
    elif ret30 is not None and abs(ret30) < CALM_RET and burst is False:
        state, approx = "静穏レンジ", "1m近似"

    return {
        "state": state,
        "stale": False,
        "approx": approx,
        "last_price": last["close"],
        "last_ts": last["ts"],
        "age_sec": round(age, 1),
        "ret_30m_pct": round(ret30 * 100.0, 3) if ret30 is not None else None,
        "ret_24h_pct": round(ret24 * 100.0, 3) if ret24 is not None else None,
        "radar": radar.state(now),
        "detail": {
            "storm_threshold_pct": STORM_RET * 100.0,
            "calm_threshold_pct": CALM_RET * 100.0,
            "break_window_min": BREAK_WINDOW,
            "broke_up": broke_up,
            "broke_down": broke_down,
            "burst_1m": burst,
        },
    }


# ---------------------------------------------------------------------------
# trade markers
# ---------------------------------------------------------------------------
def _fill_price(rec: dict) -> float | None:
    """Market orders carry order_price: None — fall back to the fill price and
    then the decision-time market price (same chain as scripts/judge_gates.py)."""
    for key in ("execution_price", "price", "order_price"):
        value = _f(rec.get(key))
        if value is not None:
            return value
    return None


def parse_bot_events(path: Path) -> list[dict[str, Any]]:
    """FILLED main-bot orders from logs/bot.jsonl, as chart markers.

    Pairing is the one in scripts/judge_gates.py:load_champion_trades, because
    the signal alone does not say what an order DID. bot.main never flips in a
    single order: with a position open, a BUY (short), a SELL (long), a CLOSE
    and a STOP_LOSS all send size=abs(pos) and go flat — a re-entry is a
    SEPARATE later record. So the rule is positional, not by signal name: the
    first filled ORDER_SENT with BUY/SELL opens, the NEXT filled ORDER_SENT
    closes. Reading a closing BUY as an entry would draw a phantom long at the
    exact moment the bot went flat.

    The log records the CUMULATIVE realized ``PnL``, so an exit's own P&L is
    the step in it — None when no baseline is known yet. An unresolved order
    (STATE_UNKNOWN) with no realized step leaves the position open, exactly as
    the gate judge treats it.
    """
    out: list[dict[str, Any]] = []
    open_side: str | None = None
    last_pnl: float | None = None
    for rec in _tail_jsonl(path, max_bytes=LOG_TAIL_BYTES):
        if rec.get("event") != "decision" and not rec.get("strategy_signal"):
            continue
        pnl_now = _f(rec.get("PnL"))
        if rec.get("decision") != "ORDER_SENT":
            if pnl_now is not None and last_pnl is None:
                last_pnl = pnl_now
            continue
        state = rec.get("execution_status")
        filled = state is None or str(state).upper() not in NON_FILL_STATES
        ts = _epoch(rec.get("timestamp") or "")
        price = _fill_price(rec)
        signal = str(rec.get("strategy_signal") or "").upper()

        if open_side is None:
            # flat: only a filled BUY/SELL opens a position
            if not filled or signal not in ("BUY", "SELL"):
                if pnl_now is not None and last_pnl is None:
                    last_pnl = pnl_now
                continue
            if last_pnl is None:
                last_pnl = pnl_now if pnl_now is not None else 0.0
            open_side = "LONG" if signal == "BUY" else "SHORT"
            if ts is not None and price is not None:
                out.append({"ts": ts, "price": price, "kind": "entry",
                            "side": open_side, "source": "main", "pnl": None,
                            "size": _f(rec.get("order_size")), "signal": signal})
            continue

        # a position is open -> this order closes it, whatever its signal says
        pnl = None if (pnl_now is None or last_pnl is None) else pnl_now - last_pnl
        if not filled and (pnl is None or pnl == 0.0):
            continue        # ambiguous: the position may still be open
        if ts is not None and price is not None:
            out.append({"ts": ts, "price": price, "kind": "exit",
                        "side": open_side, "source": "main",
                        "pnl": round(pnl, 1) if pnl is not None else None,
                        "size": _f(rec.get("order_size")),
                        "signal": signal or None})
        open_side = None
        if pnl_now is not None:
            last_pnl = pnl_now
    return out


def parse_scalp_events(path: Path) -> list[dict[str, Any]]:
    """entry/exit events from data/scalp_paper.jsonl (the other events —
    limit_placed / missed / fill / start / radar_state — are not trades)."""
    out: list[dict[str, Any]] = []
    for rec in _tail_jsonl(path, max_bytes=LOG_TAIL_BYTES):
        event = rec.get("event")
        if event not in ("entry", "exit"):
            continue
        ts, price = _f(rec.get("ts")), _f(rec.get("price"))
        if ts is None or price is None:
            continue
        out.append({"ts": ts, "price": price, "kind": event,
                    "side": rec.get("side"), "source": "scalp",
                    "pnl": _f(rec.get("pnl_jpy")),
                    "exit_kind": rec.get("exit_kind")})
    return out


# ---------------------------------------------------------------------------
# chart payload
# ---------------------------------------------------------------------------
def chart_payload(tf: str, candles: Sequence[dict],
                  bot_events: Sequence[dict] = (),
                  scalp_events: Sequence[dict] = (),
                  bars: int = 120, range_window: int | None = None,
                  resampled: Sequence[dict] | None = None) -> dict[str, Any]:
    """Last ``bars`` bars of ``tf`` plus the markers that fall inside them.

    A marker is placed on the bucket that CONTAINS its timestamp. Markers
    outside the visible window — and markers inside a data gap, where the
    preceding bucket ended before the trade happened — are counted in
    ``dropped`` rather than clamped onto a neighbouring bar: a trade drawn on
    the wrong bar is worse than one not drawn.

    ``range_window`` defaults to this timeframe's own window
    (``RANGE_WINDOW_BY_TF``) so the band describes the scale being looked at.

    The y-axis (``scale``) is resolved here rather than in the page, because
    the depth panel has to bucket the order book onto exactly the gridlines the
    price pane draws — two independent "nice step" implementations would drift
    apart the first time one of them was tuned.

    ``resampled`` lets a caller that already resampled ``candles`` to ``tf``
    hand the result in instead of paying for it twice.
    """
    if range_window is None:
        range_window = RANGE_WINDOW_BY_TF.get(tf, BREAK_WINDOW)
    tf_bars = (resample(candles, tf) if resampled is None else list(resampled))[-bars:]
    step = TF_MINUTES[tf] * 60
    starts = [b["ts"] for b in tf_bars]
    first = starts[0] if starts else None
    last_end = (starts[-1] + step) if starts else None

    markers: list[dict[str, Any]] = []
    dropped = 0
    for ev in list(bot_events) + list(scalp_events):
        ts = _f(ev.get("ts"))
        if ts is None or first is None or not (first <= ts < last_end):
            dropped += 1
            continue
        idx = bisect_right(starts, ts) - 1
        if idx < 0 or ts >= starts[idx] + step:
            dropped += 1      # before the first bar, or inside a gap
            continue
        marker = dict(ev)
        marker["bar"] = idx
        markers.append(marker)
    markers.sort(key=lambda m: m["ts"])

    rng = None
    if candles:
        window = [c for c in candles if c["ts"] > candles[-1]["ts"] - range_window * 60]
        if window:
            rng = {"high": max(c["high"] for c in window),
                   "low": min(c["low"] for c in window),
                   "window_min": range_window,
                   "window_label": window_label(range_window),
                   "bars": len(window)}

    out_bars: list[dict[str, Any]] = []
    vmax = 0.0
    for b in tf_bars:
        row: dict[str, Any] = {
            "ts": b["ts"], "o": b["open"], "h": b["high"], "l": b["low"],
            "c": b["close"], "v": round(b["volume"], 4),
            "partial": b.get("partial", False),
        }
        if "buy_vol" in b and "sell_vol" in b:
            row["bv"] = round(b["buy_vol"], 4)
            row["sv"] = round(b["sell_vol"], 4)
        if b.get("live"):
            row["live"] = True
        vmax = max(vmax, row["v"])
        out_bars.append(row)

    return {
        "tf": tf,
        "label": TF_LABELS[tf],
        "step_sec": step,
        "bars": out_bars,
        "markers": markers,
        "range": rng,
        "scale": chart_scale(out_bars, rng, markers),
        "time_grid": time_grid(tf_bars, tf),
        "vmax": round(vmax, 4),
        "dropped": dropped,
    }


def chart_scale(bars: Sequence[dict], rng: dict | None = None,
                markers: Sequence[dict] = ()) -> dict[str, Any] | None:
    """The price pane's y-axis: padded extent plus its 1/2/5 gridline ladder.

    Everything drawn inside the pane widens the extent — the bars, the range
    band and the trade markers — so a marker never lands off the top of its own
    chart. Returns None when there is nothing to scale.
    """
    if not bars:
        return None
    hi = max(b["h"] for b in bars)
    lo = min(b["l"] for b in bars)
    if rng:
        hi, lo = max(hi, rng["high"]), min(lo, rng["low"])
    for m in markers:
        price = _f(m.get("price"))
        if price is not None:
            hi, lo = max(hi, price), min(lo, price)
    pad = (hi - lo) * 0.06 or max(1.0, abs(hi) * 0.001)
    hi, lo = hi + pad, lo - pad
    step = nice_step(hi - lo)
    return {"hi": hi, "lo": lo, "step": step, "grid": price_grid(lo, hi, step)}


# ---------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------
def collect_market(root: str | Path = ".", now: float | None = None,
                   product: str = PRODUCT, bars: int = 120,
                   live_bars: Sequence[dict] = ()) -> dict[str, Any]:
    """One JSON-serialisable payload for the dashboard's マーケット tab.

    Missing files are not errors: each section becomes None (or an empty list)
    and the page shows its empty state.

    ``live_bars`` is the caller's own 1m tail off the public execution tape
    (see ``bars_from_executions``). It is merged in BEFORE anything is derived,
    so the state classification, the trends and every chart see the same
    series — in particular the staleness guard keys off the merged last bar
    instead of calling a live market dead because the CSV writer lags.
    """
    root = Path(root)
    now = now if now is not None else time.time()

    candles = read_candles(root / "data" / f"candles_{product}.csv")
    # flow repeats the candle OHLCV and adds the taker split; only its tail is
    # read, for the recent buy/sell share — the trends come from the candles.
    flow_tail = read_candles(root / "data" / f"flow_{product}.csv",
                             max_bytes=FLOW_TAIL_BYTES)
    oi_rows = _read_csv_tail(root / "data" / "oi_snapshots.csv")
    bot_events = parse_bot_events(root / "logs" / "bot.jsonl")
    scalp_events = parse_scalp_events(root / "data" / "scalp_paper.jsonl")

    source = candles or flow_tail
    csv_last_ts = source[-1]["ts"] if source else None
    split_minutes = (overlay_flow(source, flow_tail) if candles
                     else sum(1 for b in source if "buy_vol" in b))
    live_used, gap_sec = 0, None
    if live_bars:
        merged = merge_live_bars(source, live_bars)
        live_used = len(merged) - len(source)
        if live_used and csv_last_ts is not None:
            # how far the CSV writer has fallen behind the tape. A minute or
            # two is the fetch task's normal lag; hours mean the collector is
            # down and the merged series has a HOLE in it, which every window
            # computed across it is entitled to refuse (see _ret_over).
            first_new = min(b["ts"] for b in merged if b["ts"] > csv_last_ts)
            gap_sec = round(max(0.0, first_new - csv_last_ts - 60.0), 1)
        source = merged

    timeframes = []
    charts: dict[str, Any] = {}
    for tf in TF_ORDER:
        tf_bars = resample(source, tf) if source else []
        timeframes.append({
            "tf": tf,
            "label": TF_LABELS[tf],
            "bars": len(tf_bars),
            "last_close": tf_bars[-1]["close"] if tf_bars else None,
            "trend": trend(tf_bars) if tf_bars else None,
            "volatility": volatility(tf_bars) if tf_bars else None,
            "volume": volume_trend(tf_bars) if tf_bars else None,
        })
        if tf_bars:
            charts[tf] = chart_payload(tf, source, bot_events, scalp_events,
                                       bars=bars, resampled=tf_bars,
                                       range_window=RANGE_WINDOW_BY_TF[tf])

    stamps = [c["ts"] for c in source] if source else []

    return {
        "generated_at": now,
        "product": product,
        "state": market_state(source, now, stamps=stamps) if source else None,
        "timeframes": timeframes,
        "flow": taker_split(flow_tail),
        "oi": oi_trend(oi_rows),
        "chart": {"default_tf": DEFAULT_TF, "tfs": charts,
                  "range_windows": dict(RANGE_WINDOW_BY_TF)} if charts else None,
        # the board rides in via attach_board (network, not files)
        "board": None,
        "live": {
            "bars": live_used,
            "csv_last_ts": csv_last_ts,
            "last_ts": source[-1]["ts"] if source else None,
            "gap_sec": gap_sec,
        },
        "sources": {
            "candles": len(candles),
            "flow_tail": len(flow_tail),
            "oi_rows": len(oi_rows),
            "bot_events": len(bot_events),
            "scalp_events": len(scalp_events),
            "flow_split_minutes": split_minutes,
        },
    }

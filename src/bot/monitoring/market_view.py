"""Market view — multi-timeframe trend / volatility / flow snapshot.

Feeds the dashboard's マーケット tab. Pure functions over the files the
collectors already write (1m candles, per-minute flow, OI snapshots, the two
decision logs) — no network, no new state, no clock reads except the caller's
``now``. Every section degrades to None when its file is missing, so the page
renders on a fresh machine with an empty data/ directory.

Definitions come from docs/KNOWLEDGE.md §2 and are NOT re-derived here:

  嵐 (storm)   |30m log-return| >= 0.8%  (research_storm_b.py event definition)
  静穏 (calm)  |30m log-return| < 0.4% AND no 5s burst in the trailing 10m
               (research_calm_range.py). 1m candles cannot see a 5s return, so
               market_state() uses a documented 1m approximation and labels it
               "1m近似" — a weaker filter than the研究 one, never a claim of
               equivalence.
"""
from __future__ import annotations

import csv
import io
import json
import math
import time
from bisect import bisect_right
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from bot.radar import StormRadar

# ---- timeframes ------------------------------------------------------------
TF_MINUTES: dict[str, int] = {"1m": 1, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}
TF_LABELS: dict[str, str] = {"1m": "1分", "15m": "15分", "1h": "1時間",
                             "4h": "4時間", "1d": "日足"}
TF_ORDER: list[str] = ["1m", "15m", "1h", "4h", "1d"]
DEFAULT_TF = "15m"

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

FLOW_TAIL_BYTES = 512 * 1024   # ~4000 minutes of data/flow_*.csv
FLOW_SPLIT_MIN = 60            # taker split is reported over the last hour

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


def _tail_jsonl(path: Path, max_bytes: int = 4 * 1024 * 1024) -> list[dict]:
    try:
        size = path.stat().st_size
        with open(path, "rb") as fh:
            fh.seek(max(0, size - max_bytes))
            chunk = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    lines = chunk.splitlines()
    if lines and size > max_bytes:
        lines = lines[1:]
    out = []
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def read_candles(path: Path, max_bytes: int = 32 * 1024 * 1024) -> list[dict[str, float]]:
    """data/candles_*.csv or data/flow_*.csv -> ascending 1m bars.

    Both files share the ts,open,high,low,close,volume prefix; flow adds
    buy_vol/sell_vol/trades, which are carried through when present.
    """
    bars: list[dict[str, float]] = []
    for row in _read_csv_tail(path, max_bytes):
        ts = _epoch(row.get("ts", ""))
        close = _f(row.get("close"))
        if ts is None or close is None:
            continue
        bar = {
            "ts": ts,
            "open": _f(row.get("open")) or close,
            "high": _f(row.get("high")) or close,
            "low": _f(row.get("low")) or close,
            "close": close,
            "volume": _f(row.get("volume")) or 0.0,
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
        else:
            cur = {"ts": bucket, "open": bar["open"], "high": bar["high"],
                   "low": bar["low"], "close": bar["close"],
                   "volume": bar["volume"], "bars": 1}
            for extra in ("buy_vol", "sell_vol"):
                if extra in bar:
                    cur[extra] = bar[extra]
            out.append(cur)
    for bar in out:
        bar["partial"] = False
    if out:
        out[-1]["partial"] = out[-1]["bars"] < TF_MINUTES[tf]
    return out


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
def series_trend(values: Sequence[float]) -> dict[str, Any]:
    """Three-vote trend score in [-3..+3] over an arbitrary series.

    Votes (each +1/0/-1, or None when the series is too short for it):
      ema_cross  EMA12 above/below EMA48
      ema_slope  sign of the EMA48 change over the last 10 bars
      rsi        RSI14 above/below 50

    The per-vote breakdown is returned so the UI can show WHICH votes were
    available — a score of +2 out of 2 votes is not the same fact as +2 out
    of 3, and the tooltip says so rather than hiding the difference.
    """
    values = [float(v) for v in values]
    votes: dict[str, int | None] = {"ema_cross": None, "ema_slope": None, "rsi": None}
    if len(values) >= EMA_SLOW:
        fast, slow = ema(values, EMA_FAST), ema(values, EMA_SLOW)
        votes["ema_cross"] = _sign(fast[-1] - slow[-1])
    if len(values) >= SLOPE_BARS + 1:
        slow = ema(values, EMA_SLOW)
        votes["ema_slope"] = _sign(slow[-1] - slow[-1 - SLOPE_BARS])
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
    """Trend vote over the closes of one timeframe."""
    return series_trend([c["close"] for c in tf_candles])


def volatility(tf_candles: Sequence[dict]) -> dict[str, Any]:
    """ATR14 as a 値幅: absolute JPY range, % of price, and its slope arrow."""
    series = atr_series(tf_candles)
    if not series:
        return {"atr": None, "atr_pct": None, "accel": None, "angle_deg": None,
                "bars": len(tf_candles)}
    last_close = tf_candles[-1]["close"]
    atr = series[-1]
    arrow = slope_angle(series)
    return {
        "atr": round(atr, 1),
        "atr_pct": round(atr / last_close * 100.0, 3) if last_close else None,
        "accel": arrow["accel"],
        "angle_deg": arrow["angle_deg"],
        "bars": len(tf_candles),
    }


def volume_trend(bars: Sequence[dict]) -> dict[str, Any]:
    """Trend + accel arrow over per-bar volume (candles or flow rows).

    When the rows carry a taker split (data/flow_*.csv) the latest buy share is
    reported alongside — it is a level, not part of the vote.
    """
    volumes = [b.get("volume", 0.0) for b in bars]
    out = series_trend(volumes)
    out.update(slope_angle(volumes))
    last = bars[-1] if bars else {}
    buy, sell = last.get("buy_vol"), last.get("sell_vol")
    total = (buy or 0.0) + (sell or 0.0)
    out["buy_share"] = round(buy / total * 100.0, 1) if buy is not None and total else None
    out["last"] = round(volumes[-1], 4) if volumes else None
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
def _bar_at_or_before(candles: Sequence[dict], ts: float) -> dict | None:
    idx = bisect_right([c["ts"] for c in candles], ts) - 1
    return candles[idx] if idx >= 0 else None


def _ret_over(candles: Sequence[dict], minutes: int) -> float | None:
    """Simple return from the bar at or before now-``minutes`` to the last bar."""
    if not candles:
        return None
    last = candles[-1]
    ref = _bar_at_or_before(candles, last["ts"] - minutes * 60)
    if ref is None or ref is last or not ref["close"]:
        return None
    return last["close"] / ref["close"] - 1.0


def _log_ret_over(candles: Sequence[dict], minutes: int) -> float | None:
    simple = _ret_over(candles, minutes)
    return math.log(1.0 + simple) if simple is not None and simple > -1.0 else None


def market_state(candles_1m: Sequence[dict], now: float | None = None,
                 radar: StormRadar | None = None) -> dict[str, Any] | None:
    """嵐 / ブレイク / 静穏レンジ / 通常 for the state strip.

    Checked in that order — a storm that also broke the range is a storm. The
    calm branch is the 1m approximation of the research calm filter (see the
    module docstring) and carries ``approx: "1m近似"`` so the UI can label it.
    """
    if not candles_1m:
        return None
    now = now if now is not None else time.time()
    radar = radar or StormRadar()
    last = candles_1m[-1]
    ret30 = _log_ret_over(candles_1m, 30)
    ret24 = _ret_over(candles_1m, 1440)

    # break: beyond the trailing 240m high/low, and it happened in the last 15m
    recent = [c for c in candles_1m if c["ts"] > last["ts"] - BREAK_RECENT * 60]
    ref = [c for c in candles_1m
           if last["ts"] - (BREAK_WINDOW + BREAK_RECENT) * 60 < c["ts"]
           <= last["ts"] - BREAK_RECENT * 60]
    broke_up = broke_down = None
    if ref and recent:
        ref_high = max(c["high"] for c in ref)
        ref_low = min(c["low"] for c in ref)
        broke_up = max(c["high"] for c in recent) > ref_high
        broke_down = min(c["low"] for c in recent) < ref_low

    burst = None
    if len(candles_1m) >= 2:
        window = [c for c in candles_1m if c["ts"] > last["ts"] - CALM_BURST_LOOKBACK * 60]
        prevs = [_bar_at_or_before(candles_1m, c["ts"] - 60) for c in window]
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
        "approx": approx,
        "last_price": last["close"],
        "last_ts": last["ts"],
        "age_sec": round(now - last["ts"], 1),
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

    BUY/SELL open a position, CLOSE/STOP_LOSS close it. The log records the
    CUMULATIVE realized ``PnL``, so an exit's own P&L is the step since the
    previous decision — None when no baseline is known yet.
    """
    out: list[dict[str, Any]] = []
    open_side: str | None = None
    last_pnl: float | None = None
    for rec in _tail_jsonl(path):
        if rec.get("event") != "decision" and not rec.get("strategy_signal"):
            continue
        pnl_now = _f(rec.get("PnL"))
        if rec.get("decision") != "ORDER_SENT":
            if pnl_now is not None and last_pnl is None:
                last_pnl = pnl_now
            continue
        state = rec.get("execution_status")
        if state is not None and str(state).upper() in NON_FILL_STATES:
            continue
        ts = _epoch(rec.get("timestamp") or "")
        price = _fill_price(rec)
        if ts is None or price is None:
            continue
        signal = str(rec.get("strategy_signal") or "").upper()
        if signal in ("BUY", "SELL"):
            kind, side = "entry", "LONG" if signal == "BUY" else "SHORT"
            open_side = side
            pnl = None
        else:
            kind, side = "exit", open_side
            pnl = (pnl_now - last_pnl) if (pnl_now is not None and last_pnl is not None) else None
            open_side = None
        if pnl_now is not None:
            last_pnl = pnl_now
        out.append({"ts": ts, "price": price, "kind": kind, "side": side,
                    "source": "main", "pnl": round(pnl, 1) if pnl is not None else None,
                    "size": _f(rec.get("order_size")),
                    "signal": signal or None})
    return out


def parse_scalp_events(path: Path) -> list[dict[str, Any]]:
    """entry/exit events from data/scalp_paper.jsonl (the other events —
    limit_placed / missed / fill / start / radar_state — are not trades)."""
    out: list[dict[str, Any]] = []
    for rec in _tail_jsonl(path):
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
                  bars: int = 120, range_window: int = BREAK_WINDOW,
                  resampled: Sequence[dict] | None = None) -> dict[str, Any]:
    """Last ``bars`` bars of ``tf`` plus the markers that fall inside them.

    A marker is placed on the bucket that contains its timestamp. Markers
    outside the visible window are counted in ``dropped`` rather than clamped
    to the edge — a trade drawn on the wrong bar is worse than one not drawn.

    ``resampled`` lets a caller that already resampled ``candles`` to ``tf``
    hand the result in instead of paying for it twice.
    """
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
        if idx < 0:
            dropped += 1
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
                   "window_min": range_window, "bars": len(window)}

    return {
        "tf": tf,
        "label": TF_LABELS[tf],
        "step_sec": step,
        "bars": [{"ts": b["ts"], "o": b["open"], "h": b["high"], "l": b["low"],
                  "c": b["close"], "v": round(b["volume"], 4),
                  "partial": b.get("partial", False)} for b in tf_bars],
        "markers": markers,
        "range": rng,
        "dropped": dropped,
    }


# ---------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------
def collect_market(root: str | Path = ".", now: float | None = None,
                   product: str = PRODUCT, bars: int = 120) -> dict[str, Any]:
    """One JSON-serialisable payload for the dashboard's マーケット tab.

    Missing files are not errors: each section becomes None (or an empty list)
    and the page shows its empty state.
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
                                       bars=bars, resampled=tf_bars)

    return {
        "generated_at": now,
        "product": product,
        "state": market_state(source, now) if source else None,
        "timeframes": timeframes,
        "flow": taker_split(flow_tail),
        "oi": oi_trend(oi_rows),
        "chart": {"default_tf": DEFAULT_TF, "tfs": charts,
                  "range_window_min": BREAK_WINDOW} if charts else None,
        "sources": {
            "candles": len(candles),
            "flow_tail": len(flow_tail),
            "oi_rows": len(oi_rows),
            "bot_events": len(bot_events),
            "scalp_events": len(scalp_events),
        },
    }

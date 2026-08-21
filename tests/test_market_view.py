"""Market view — resampling, the trend vote, state classification and the
chart payload the dashboard's マーケット tab draws."""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone

import pytest

from bot.monitoring.market_view import (
    RANGE_WINDOW_BY_TF, TF_ORDER, attach_board, bars_from_executions,
    board_depth, chart_payload, chart_scale, closed_bars, collect_market,
    market_state, merge_live_bars, nice_step, normalize_board, oi_trend,
    overlay_flow, parse_bot_events, parse_scalp_events, price_grid,
    read_candles, resample, series_trend, slope_angle, taker_split, time_grid,
    trend, volatility, volume_trend, window_label,
)

T0 = datetime(2026, 8, 20, 0, 0, tzinfo=timezone.utc).timestamp()


def bars(closes, start=T0, step=60, high=None, low=None, volume=1.0):
    """1m bars from a close series; open = previous close."""
    out = []
    for i, c in enumerate(closes):
        o = closes[i - 1] if i else c
        out.append({
            "ts": start + i * step, "open": o,
            "high": high[i] if high else max(o, c),
            "low": low[i] if low else min(o, c),
            "close": c,
            "volume": volume[i] if isinstance(volume, list) else volume,
        })
    return out


def ramp(n, first, per_bar):
    return [first * (1.0 + per_bar) ** i for i in range(n)]


# ---- resample --------------------------------------------------------------
def test_resample_buckets_are_utc_aligned():
    """A 15m bucket starts on :00/:15/:30/:45 UTC even when the data does not."""
    start = T0 + 7 * 60  # 00:07 UTC
    out = resample(bars([100 + i for i in range(25)], start=start), "15m")
    assert [b["ts"] for b in out] == [T0, T0 + 900, T0 + 1800]
    assert datetime.fromtimestamp(out[1]["ts"], timezone.utc).minute == 15


def test_resample_aggregates_ohlcv_over_the_bucket():
    src = bars([10, 12, 9, 11], volume=[1.0, 2.0, 3.0, 4.0])
    src[1]["high"], src[2]["low"] = 15.0, 5.0
    out = resample(src, "15m")
    assert len(out) == 1
    assert (out[0]["open"], out[0]["high"], out[0]["low"], out[0]["close"]) == (10, 15.0, 5.0, 11)
    assert out[0]["volume"] == 10.0 and out[0]["bars"] == 4


def test_resample_edge_bar_starts_the_next_bucket():
    """The bar at exactly :15 belongs to the 00:15 bucket, not the 00:00 one."""
    out = resample(bars([1] * 16), "15m")
    assert [b["bars"] for b in out] == [15, 1]
    assert out[1]["ts"] == T0 + 900


def test_resample_marks_only_the_partial_last_bucket():
    out = resample(bars([1] * 20), "15m")
    assert out[0]["partial"] is False        # full 15 minutes
    assert out[1]["partial"] is True         # 5 of 15 minutes so far
    assert resample(bars([1] * 30), "15m")[0]["partial"] is False


def test_resample_1m_is_a_passthrough_grid():
    out = resample(bars([1, 2, 3]), "1m")
    assert len(out) == 3 and all(b["bars"] == 1 for b in out)


def test_resample_needs_the_clock_to_see_a_forming_minute():
    """Bucket fill alone cannot flag a forming MINUTE — a 1m bucket is "full"
    the instant its first execution lands, so the live tape's current minute,
    two seconds and one trade old, was handed to the closed-bar computations as
    a finished bar. With ``now`` it is partial on every frame, 1m included."""
    src = bars([100.0] * 3)                              # T0 .. T0+120
    assert [b["partial"] for b in resample(src, "1m")] == [False] * 3

    forming = resample(src, "1m", now=T0 + 120 + 2)      # 2s into the last one
    assert [b["partial"] for b in forming] == [False, False, True]
    assert len(closed_bars(forming)) == 2

    over = resample(src, "1m", now=T0 + 180)             # the minute has closed
    assert over[-1]["partial"] is False and len(closed_bars(over)) == 3
    # a slower frame is partial for the whole time its bucket is open
    assert resample(src, "15m", now=T0 + 180)[-1]["partial"] is True


def test_resample_empty():
    assert resample([], "1h") == []


# ---- trend vote ------------------------------------------------------------
def test_trend_votes_all_up_on_a_rising_series():
    t = trend(bars(ramp(200, 100.0, 0.002)))
    assert t["votes"] == {"ema_cross": 1, "ema_slope": 1, "rsi": 1}
    assert t["score"] == 3 and t["strength"] == "強" and t["votes_available"] == 3


def test_trend_votes_all_down_on_a_falling_series():
    t = trend(bars(ramp(200, 100.0, -0.002)))
    assert t["votes"] == {"ema_cross": -1, "ema_slope": -1, "rsi": -1}
    assert t["score"] == -3 and t["direction"] == -1


def test_trend_is_flat_on_a_flat_series():
    t = trend(bars([100.0] * 200))
    assert t["score"] == 0 and t["strength"] == "—" and t["rsi"] == 50.0


def test_trend_reports_which_votes_were_unavailable():
    """A short series still scores, but says so — +2 of 2 votes is not +2 of 3."""
    t = trend(bars(ramp(20, 100.0, 0.002)))
    assert t["votes"]["ema_cross"] is None      # needs 48 bars
    assert t["votes"]["ema_slope"] == 1 and t["votes"]["rsi"] == 1
    assert t["votes_available"] == 2 and t["score"] == 2


def test_trend_score_is_none_when_nothing_can_be_voted():
    t = series_trend([1.0, 2.0])
    assert t["score"] is None and t["votes_available"] == 0
    assert t["strength"] is None and t["direction"] is None


# ---- volatility / accel ----------------------------------------------------
def test_volatility_reports_atr_as_a_percentage_of_price():
    src = bars([100.0] * 60)
    for b in src:
        b["high"], b["low"] = 101.0, 99.0     # true range 2.0 every bar
    v = volatility(src)
    assert v["atr"] == pytest.approx(2.0, abs=1e-6)
    assert v["atr_pct"] == pytest.approx(2.0, abs=1e-3)
    assert v["angle_deg"] == pytest.approx(0.0, abs=0.5)


def test_volatility_accel_sign_follows_a_widening_range():
    src = bars([100.0] * 80)
    for i, b in enumerate(src):
        half = 0.5 + i * 0.05                 # range widening bar by bar
        b["high"], b["low"] = 100 + half, 100 - half
    up = volatility(src)
    assert up["accel"] > 0 and up["angle_deg"] > 0

    for i, b in enumerate(src):               # same, reversed: narrowing
        half = 0.5 + (len(src) - i) * 0.05
        b["high"], b["low"] = 100 + half, 100 - half
    down = volatility(src)
    assert down["accel"] < 0 and down["angle_deg"] < 0


def test_angle_is_clamped_to_sixty_degrees():
    assert slope_angle([1.0, 10.0, 100.0, 1000.0])["angle_deg"] == 60.0
    assert slope_angle([1000.0, 100.0, 10.0, 1.0])["angle_deg"] == -60.0
    assert slope_angle([5.0])["angle_deg"] is None


def test_volatility_needs_fifteen_bars():
    v = volatility(bars([100.0] * 5))
    assert v["atr"] is None and v["angle_deg"] is None


# ---- volume / flow / OI ----------------------------------------------------
def test_volume_trend_rises_with_volume():
    v = volume_trend(bars([100.0] * 80, volume=[1.0 + i * 0.1 for i in range(80)]))
    assert v["score"] == 3 and v["angle_deg"] > 0


def test_volume_trend_reports_the_taker_share_when_flow_has_one():
    src = bars([100.0] * 3)
    for b in src:
        b["buy_vol"], b["sell_vol"] = 3.0, 1.0
    assert volume_trend(src)["buy_share"] == 75.0
    assert volume_trend(bars([100.0] * 3))["buy_share"] is None


def test_volume_trend_ignores_the_still_forming_bucket():
    """10 minutes into a 4h bucket the bucket holds 1/24 of a bucket's volume.
    Reading that as a collapse tilted the arrow to -28.6 deg on a market whose
    volume never changed, every four hours."""
    src = bars([100.0] * (240 * 20 + 10), volume=1.0)   # 20 full 4h buckets + 10m
    tf = resample(src, "4h")
    assert tf[-1]["partial"] is True and tf[-1]["volume"] == 10.0
    assert slope_angle([b["volume"] for b in tf])["angle_deg"] < -25   # the bug

    v = volume_trend(tf)
    assert v["partial_excluded"] == 1 and v["bars_used"] == 20
    assert v["angle_deg"] == pytest.approx(0.0, abs=1.0)   # flat volume, flat arrow
    assert v["last"] == 240.0                              # last CLOSED bucket

    # the same series without the partial tail votes identically
    assert volume_trend(tf)["score"] == volume_trend(tf[:-1])["score"]


def test_trend_and_volatility_exclude_the_partial_bucket_from_slopes():
    """The forming bar still counts for the level votes — it is where price
    is now — but never for a slope or for the ATR."""
    src = bars(ramp(240 * 60 + 10, 100.0, 0.00002))
    for b in src[-10:]:                       # a violent 10m tail
        b["close"] = 50.0
        b["high"], b["low"] = 51.0, 49.0
    tf = resample(src, "4h")
    assert tf[-1]["partial"] is True

    t = trend(tf)
    assert t["votes"]["ema_slope"] == trend(tf[:-1])["votes"]["ema_slope"] == 1
    assert t["votes"]["ema_cross"] == -1       # the level vote does see the drop
    v = volatility(tf)
    assert v["bars"] == len(tf) - 1 and v == volatility(tf[:-1])


def test_taker_split_over_the_recent_window():
    src = bars([100.0] * 120)
    for i, b in enumerate(src):
        b["buy_vol"], b["sell_vol"] = (1.0, 1.0) if i < 60 else (3.0, 1.0)
    split = taker_split(src, minutes=60)
    assert split["buy_pct"] == 75.0 and split["bars"] == 60
    assert taker_split([]) is None
    assert taker_split(bars([100.0] * 5)) is None       # plain candles: no split


def test_oi_trend_handles_sparse_and_short_history():
    assert oi_trend([]) is None
    assert oi_trend([{"ts_utc": "2026-08-20T12:00:00+00:00", "okx_usdt_oi": ""}]) is None

    rows = [{"ts_utc": f"2026-08-20T{h:02d}:00:00+00:00",
             "okx_usdt_oi": "" if h % 3 else str(1000 + h * 10),
             "okx_ls_ratio": "1.10", "dvol": "40.0"} for h in range(24)]
    oi = oi_trend(rows)
    assert oi["points"] == 8 and oi["rows"] == 24        # blanks dropped, not filled
    assert oi["angle_deg"] > 0 and oi["dvol"] == 40.0 and oi["ls_ratio"] == 1.10
    assert oi["history_hours"] == pytest.approx(21.0)

    short = oi_trend([{"ts_utc": "2026-08-20T12:00:00+00:00", "okx_usdt_oi": "1"}])
    assert short["points"] == 1 and short["angle_deg"] is None
    assert short["score"] is None and short["history_hours"] is None


# ---- market state ----------------------------------------------------------
def _state(candles):
    return market_state(candles, now=candles[-1]["ts"] + 5)["state"]


def test_market_state_storm():
    """|30m log-return| >= 0.8% — the research storm definition (KNOWLEDGE §2)."""
    closes = ramp(31, 100.0, math.exp(0.010 / 30) - 1)   # +1.0% over 30 bars
    st = market_state(bars(closes), now=T0)
    assert st["state"] == "嵐" and st["approx"] is None
    assert abs(st["ret_30m_pct"]) >= 0.8


def test_market_state_break():
    """A push through the trailing 240m high inside the last 15 minutes."""
    closes = [100.0] * 300 + [100.3] * 3
    st = market_state(bars(closes), now=T0)
    assert st["state"] == "ブレイク"
    assert st["detail"]["broke_up"] is True and st["detail"]["broke_down"] is False


def test_market_state_break_down():
    st = market_state(bars([100.0] * 300 + [99.7] * 3), now=T0)
    assert st["state"] == "ブレイク" and st["detail"]["broke_down"] is True


def test_market_state_calm_is_labelled_as_a_1m_approximation():
    closes = [100.0 + 0.01 * (i % 10) for i in range(300)]   # 1m steps < 0.15%
    st = market_state(bars(closes), now=T0)
    assert st["state"] == "静穏レンジ"
    assert st["approx"] == "1m近似"          # 1m data cannot see the 5s filter
    assert st["detail"]["burst_1m"] is False


def test_market_state_normal_between_calm_and_storm():
    """Drifting 0.6% in 30m, but still inside the 240m range: neither, so 通常."""
    base = [100.0 + 2.0 * math.sin(i / 20.0 * 2 * math.pi) for i in range(270)]
    closes = base + [base[-1] * (1.0 + 0.006 * (k + 1) / 30) for k in range(30)]
    st = market_state(bars(closes), now=T0)
    assert st["state"] == "通常" and 0.4 < abs(st["ret_30m_pct"]) < 0.8
    assert st["detail"]["broke_up"] is False and st["detail"]["broke_down"] is False


def test_market_state_carries_returns_and_radar():
    st = market_state(bars([100.0] * 1500), now=T0)
    assert st["ret_24h_pct"] == pytest.approx(0.0)
    assert st["radar"]["window"] == "12:30-15:00 UTC"
    assert st["last_price"] == 100.0 and st["stale"] is False
    assert market_state([], now=T0) is None


def test_market_state_is_fresh_within_ten_minutes():
    candles = bars([100.0 + 0.01 * (i % 10) for i in range(300)])
    st = market_state(candles, now=candles[-1]["ts"] + 9 * 60)
    assert st["stale"] is False and st["state"] == "静穏レンジ"


def test_market_state_stale_feed_is_not_classified():
    """A dead collector is not a calm market: the label is withheld, and the
    age is reported so the page can say the feed stopped."""
    candles = bars([100.0 + 0.01 * (i % 10) for i in range(300)])
    st = market_state(candles, now=candles[-1]["ts"] + 24 * 3600)
    assert st["state"] is None and st["stale"] is True
    assert st["age_sec"] == pytest.approx(86400.0)
    assert st["ret_30m_pct"] is None and st["ret_24h_pct"] is None
    assert st["last_price"] == candles[-1]["close"]
    assert st["radar"]["window"] == "12:30-15:00 UTC"     # the clock is live


# ---- candle reader ---------------------------------------------------------
def test_read_candles_drops_unusable_rows(tmp_path):
    """A close of 0 / blank / NaN would divide by zero in every return and log
    below — the row is dropped, and the burst scan over it cannot raise."""
    path = tmp_path / "candles.csv"
    path.write_text(
        "ts,open,high,low,close,volume\n"
        "2026-08-20 00:00:00+00:00,100,101,99,100,1.0\n"
        "2026-08-20 00:01:00+00:00,100,101,99,0,1.0\n"
        "2026-08-20 00:02:00+00:00,100,101,99,,1.0\n"
        "2026-08-20 00:03:00+00:00,100,101,99,nan,1.0\n"
        "2026-08-20 00:04:00+00:00,100,101,99,-5,1.0\n"
        "2026-08-20 00:05:00+00:00,0,0,0,101,-3\n", encoding="utf-8")
    out = read_candles(path)
    assert [c["close"] for c in out] == [100.0, 101.0]
    # unusable prices fall back to the close; a negative volume clamps to 0
    assert out[1]["open"] == out[1]["high"] == out[1]["low"] == 101.0
    assert out[1]["volume"] == 0.0
    st = market_state(out, now=out[-1]["ts"] + 5)   # must not raise
    assert st["state"] in ("嵐", "ブレイク", "静穏レンジ", "通常")


# ---- trade markers ---------------------------------------------------------
def _write(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")


def test_parse_bot_events_price_fallback_chain(tmp_path):
    """Market orders carry order_price: None — execution_price, then the
    decision-time price, then order_price (same chain as judge_gates.py)."""
    log = tmp_path / "logs" / "bot.jsonl"
    _write(log, [
        {"event": "decision", "timestamp": "2026-08-20T00:00:00+00:00",
         "strategy_signal": "BUY", "decision": "ORDER_SENT",
         "execution_status": "FILLED", "execution_price": 111.0,
         "price": 222.0, "order_price": 333.0, "order_size": 0.01, "PnL": 0.0},
        {"event": "decision", "timestamp": "2026-08-20T00:01:00+00:00",
         "strategy_signal": "CLOSE", "decision": "ORDER_SENT",
         "execution_status": "FILLED", "execution_price": None,
         "price": 222.0, "order_price": 333.0, "PnL": 40.0},
        {"event": "decision", "timestamp": "2026-08-20T00:02:00+00:00",
         "strategy_signal": "SELL", "decision": "ORDER_SENT",
         "execution_status": "FILLED", "execution_price": None,
         "price": None, "order_price": 333.0, "PnL": 40.0},
    ])
    evs = parse_bot_events(log)
    assert [e["price"] for e in evs] == [111.0, 222.0, 333.0]
    assert [e["kind"] for e in evs] == ["entry", "exit", "entry"]
    assert [e["side"] for e in evs] == ["LONG", "LONG", "SHORT"]
    assert evs[1]["pnl"] == 40.0        # step in the cumulative PnL
    assert evs[0]["pnl"] is None


def test_parse_bot_events_skips_unfilled_and_non_orders(tmp_path):
    log = tmp_path / "logs" / "bot.jsonl"
    _write(log, [
        {"event": "decision", "timestamp": "2026-08-20T00:00:00+00:00",
         "strategy_signal": "HOLD", "decision": "HOLD", "price": 100.0, "PnL": 0.0},
        {"event": "decision", "timestamp": "2026-08-20T00:01:00+00:00",
         "strategy_signal": "BUY", "decision": "ORDER_SENT", "price": 100.0,
         "execution_status": "STATE_UNKNOWN", "PnL": 0.0},
        {"event": "decision", "timestamp": "2026-08-20T00:02:00+00:00",
         "strategy_signal": "BUY", "decision": "ORDER_SENT", "price": 100.0,
         "execution_status": "REJECTED", "PnL": 0.0},
    ])
    assert parse_bot_events(log) == []
    assert parse_bot_events(tmp_path / "logs" / "missing.jsonl") == []


def _decision(minute, signal, **kw):
    """One bot.main.log_decision record, in the shape logs/bot.jsonl really has."""
    rec = {"event": "decision", "timestamp": f"2026-08-20T00:{minute:02d}:00+00:00",
           "strategy_signal": signal, "decision": "ORDER_SENT",
           "execution_status": "FILLED", "order_size": 0.01}
    rec.update(kw)
    return rec


def test_parse_bot_events_pairs_a_long_to_short_flip(tmp_path):
    """bot.main never flips in one order: a SELL with a long open only CLOSES
    it (size=abs(pos)), and the short is a separate later record. Reading the
    closing SELL as an entry drew a phantom short at the moment of the exit."""
    log = tmp_path / "logs" / "bot.jsonl"
    _write(log, [
        _decision(0, "BUY", price=100.0, PnL=0.0),      # flat -> long
        _decision(1, "HOLD", decision="HOLD", price=101.0, PnL=0.0,
                  execution_status=None, order_size=None),
        _decision(2, "SELL", price=105.0, PnL=50.0),    # long open -> close
        _decision(3, "SELL", price=105.0, PnL=50.0),    # flat -> short
        _decision(4, "BUY", price=103.0, PnL=70.0),     # short open -> close
        _decision(5, "BUY", price=103.0, PnL=70.0),     # flat -> long again
    ])
    evs = parse_bot_events(log)
    assert [(e["kind"], e["side"]) for e in evs] == [
        ("entry", "LONG"), ("exit", "LONG"), ("entry", "SHORT"),
        ("exit", "SHORT"), ("entry", "LONG")]
    assert [e["pnl"] for e in evs] == [None, 50.0, None, 20.0, None]
    assert [e["signal"] for e in evs] == ["BUY", "SELL", "SELL", "BUY", "BUY"]


def test_parse_bot_events_stop_loss_closes_the_open_position(tmp_path):
    log = tmp_path / "logs" / "bot.jsonl"
    _write(log, [
        _decision(0, "SELL", price=100.0, PnL=10.0),
        _decision(1, "STOP_LOSS", price=104.0, PnL=-30.0),
        _decision(2, "CLOSE", price=104.0, PnL=-30.0),   # flat: nothing to pair
    ])
    evs = parse_bot_events(log)
    assert [(e["kind"], e["side"], e["pnl"]) for e in evs] == [
        ("entry", "SHORT", None), ("exit", "SHORT", -40.0)]


def test_parse_bot_events_unresolved_close_leaves_the_position_open(tmp_path):
    """STATE_UNKNOWN with no realized step: the position may still be open, so
    no exit is drawn and the next order still closes it (judge_gates rule)."""
    log = tmp_path / "logs" / "bot.jsonl"
    _write(log, [
        _decision(0, "BUY", price=100.0, PnL=0.0),
        _decision(1, "SELL", price=104.0, PnL=0.0, execution_status="STATE_UNKNOWN"),
        _decision(2, "SELL", price=105.0, PnL=25.0),
    ])
    evs = parse_bot_events(log)
    assert [(e["kind"], e["ts"] % 3600 // 60) for e in evs] == [("entry", 0), ("exit", 2)]
    assert evs[1]["pnl"] == 25.0


def test_parse_scalp_events_keeps_only_trades(tmp_path):
    path = tmp_path / "data" / "scalp_paper.jsonl"
    _write(path, [
        {"ts": T0, "event": "start", "thr_bps": 10.0},
        {"ts": T0 + 10, "event": "limit_placed", "side": "LONG", "limit": 100.0},
        {"ts": T0 + 20, "event": "entry", "side": "LONG", "price": 100.0},
        {"ts": T0 + 50, "event": "exit", "side": "LONG", "price": 101.0,
         "pnl_jpy": 12.5, "exit_kind": "maker_tp"},
        {"ts": T0 + 60, "event": "missed", "side": "SHORT"},
    ])
    evs = parse_scalp_events(path)
    assert [e["kind"] for e in evs] == ["entry", "exit"]
    assert evs[1]["pnl"] == 12.5 and evs[1]["exit_kind"] == "maker_tp"
    assert all(e["source"] == "scalp" for e in evs)


# ---- chart payload ---------------------------------------------------------
def test_chart_payload_places_markers_on_their_bucket():
    candles = bars([100.0 + i for i in range(60)])
    evs = [
        {"ts": T0 + 0, "price": 100.0, "kind": "entry", "side": "LONG", "source": "main"},
        {"ts": T0 + 899, "price": 105.0, "kind": "exit", "side": "LONG", "source": "main"},
        {"ts": T0 + 900, "price": 110.0, "kind": "entry", "side": "SHORT", "source": "scalp"},
    ]
    p = chart_payload("15m", candles, evs, [], bars=120)
    assert [m["bar"] for m in p["markers"]] == [0, 0, 1]
    assert p["dropped"] == 0
    assert p["bars"][0]["ts"] == T0 and p["tf"] == "15m" and p["label"] == "15分"


def test_chart_payload_drops_markers_outside_the_window():
    """Out-of-window trades are counted, never clamped onto an edge bar."""
    candles = bars([100.0] * 600)
    inside = T0 + 500 * 60          # the visible 1m window is bars 480..599
    evs = [{"ts": T0 + 5 * 60, "price": 100.0, "kind": "entry", "side": "LONG", "source": "main"},
           {"ts": T0 + 999_999, "price": 100.0, "kind": "exit", "side": "LONG", "source": "main"},
           {"ts": inside, "price": 100.0, "kind": "entry", "side": "LONG", "source": "main"}]
    p = chart_payload("1m", candles, evs, [], bars=120)
    assert len(p["bars"]) == 120 and p["dropped"] == 2
    assert len(p["markers"]) == 1
    assert p["markers"][0]["ts"] == inside and p["markers"][0]["bar"] == 20


def test_chart_payload_drops_markers_that_fall_in_a_data_gap():
    """The collector stopped for two hours; a trade inside the hole belongs to
    no bucket, so it is dropped rather than stamped on the bar before it."""
    candles = bars([100.0] * 30) + bars([100.0] * 30, start=T0 + 150 * 60)
    gap = T0 + 60 * 60           # inside the hole: after bar 29 ends, before 30
    evs = [{"ts": T0 + 10 * 60, "price": 100.0, "kind": "entry", "side": "LONG",
            "source": "main"},
           {"ts": gap, "price": 100.0, "kind": "exit", "side": "LONG", "source": "main"},
           {"ts": T0 + 155 * 60, "price": 100.0, "kind": "entry", "side": "LONG",
            "source": "main"}]
    p = chart_payload("1m", candles, evs, [], bars=120)
    assert p["dropped"] == 1
    assert [m["ts"] for m in p["markers"]] == [T0 + 10 * 60, T0 + 155 * 60]
    assert all(p["bars"][m["bar"]]["ts"] == m["ts"] for m in p["markers"])

    # a 15m view has a bucket that spans the same instant only if data covers it
    p15 = chart_payload("15m", candles, evs, [], bars=120)
    assert p15["dropped"] == 1


def test_chart_payload_range_band_and_empty_input():
    candles = bars([100.0] * 100 + [130.0] * 10 + [100.0] * 100)
    p = chart_payload("1m", candles, [], [], range_window=240)
    assert p["range"]["high"] == 130.0 and p["range"]["low"] == 100.0
    assert p["range"]["window_min"] == 240

    empty = chart_payload("1h", [], [{"ts": T0, "price": 1.0}], [])
    assert empty["bars"] == [] and empty["range"] is None and empty["dropped"] == 1


def test_chart_payload_accepts_a_precomputed_resample():
    candles = bars([100.0 + i for i in range(60)])
    direct = chart_payload("15m", candles, [], [])
    reused = chart_payload("15m", candles, [], [], resampled=resample(candles, "15m"))
    assert direct["bars"] == reused["bars"]


# ---- collect_market --------------------------------------------------------
def test_collect_market_empty_root_is_an_all_none_skeleton(tmp_path):
    d = collect_market(tmp_path, now=T0)
    assert d["state"] is None and d["oi"] is None and d["chart"] is None
    assert d["flow"] is None
    assert [t["tf"] for t in d["timeframes"]] == ["1m", "15m", "1h", "4h", "1d"]
    assert all(t["trend"] is None and t["volatility"] is None and t["volume"] is None
               and t["bars"] == 0 for t in d["timeframes"])
    assert d["sources"] == {"candles": 0, "flow_tail": 0, "oi_rows": 0,
                            "bot_events": 0, "scalp_events": 0,
                            "flow_split_minutes": 0}
    assert d["board"] is None and d["live"]["bars"] == 0
    json.dumps(d)


def test_collect_market_payload_is_json_serialisable(tmp_path):
    _make_workspace(tmp_path)
    json.dumps(collect_market(tmp_path, now=T0))


def _make_workspace(root, minutes=400):
    """A miniature data/ + logs/ in the shapes the collectors really write."""
    (root / "data").mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(parents=True, exist_ok=True)
    rows = ["ts,open,high,low,close,volume"]
    flow = ["ts,open,high,low,close,volume,buy_vol,sell_vol,trades"]
    price = 11_000_000.0
    for i in range(minutes):
        stamp = datetime.fromtimestamp(T0 + i * 60, timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S+00:00")
        price *= 1.0002
        rows.append(f"{stamp},{price},{price * 1.001},{price * 0.999},{price},1.5")
        flow.append(f"{stamp},{price},{price * 1.001},{price * 0.999},{price},1.5,1.0,0.5,42")
    (root / "data" / "candles_FX_BTC_JPY.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (root / "data" / "flow_FX_BTC_JPY.csv").write_text("\n".join(flow) + "\n", encoding="utf-8")
    (root / "data" / "oi_snapshots.csv").write_text(
        "ts_utc,okx_usdt_oi,okx_usd_oi,okx_ls_ratio,dvol,deribit_oi\n"
        "2026-08-20T00:00:00+00:00,3000000.0,4000000.0,1.10,39.5,8e8\n"
        "2026-08-20T00:15:00+00:00,3010000.0,4010000.0,1.12,39.8,8e8\n", encoding="utf-8")
    _write(root / "logs" / "bot.jsonl", [
        {"event": "decision", "timestamp": "2026-08-20T00:30:00+00:00",
         "strategy_signal": "BUY", "decision": "ORDER_SENT", "price": 11_050_000.0,
         "execution_status": "FILLED", "order_size": 0.01, "PnL": 0.0}])
    _write(root / "data" / "scalp_paper.jsonl", [
        {"ts": T0 + 2400, "event": "entry", "side": "SHORT", "price": 11_060_000.0},
        {"ts": T0 + 2460, "event": "exit", "side": "SHORT", "price": 11_050_000.0,
         "pnl_jpy": -30.0, "exit_kind": "taker_fallback"}])


def test_collect_market_wires_every_source(tmp_path):
    _make_workspace(tmp_path)
    d = collect_market(tmp_path, now=T0 + 400 * 60)

    assert d["sources"]["candles"] == 400 and d["sources"]["flow_tail"] == 400
    assert d["sources"]["bot_events"] == 1 and d["sources"]["scalp_events"] == 2
    assert d["state"]["state"] in ("嵐", "ブレイク", "静穏レンジ", "通常")
    assert d["flow"]["buy_pct"] == pytest.approx(66.7, abs=0.1)
    assert d["oi"]["last"] == 3010000.0 and d["oi"]["dvol"] == 39.8

    by_tf = {t["tf"]: t for t in d["timeframes"]}
    assert by_tf["1m"]["bars"] == 400 and by_tf["1m"]["trend"]["score"] == 3
    assert by_tf["1m"]["volatility"]["atr_pct"] > 0

    chart = d["chart"]["tfs"]["15m"]
    assert chart["markers"] and {m["source"] for m in chart["markers"]} == {"main", "scalp"}
    # the chart opens on 1m: that is the frame the owner scalps
    assert d["chart"]["default_tf"] == "1m"
    assert d["chart"]["range_windows"] == RANGE_WINDOW_BY_TF
    # data/candles_*.csv has no taker split; data/flow_*.csv's is laid over it
    assert d["sources"]["flow_split_minutes"] == 400
    assert d["chart"]["tfs"]["1m"]["bars"][-1]["bv"] == 1.0


def test_collect_market_survives_a_missing_candle_file(tmp_path):
    """flow alone is enough — it repeats the same OHLCV columns."""
    _make_workspace(tmp_path)
    (tmp_path / "data" / "candles_FX_BTC_JPY.csv").unlink()
    d = collect_market(tmp_path, now=T0 + 400 * 60)
    assert d["sources"]["candles"] == 0
    assert d["state"] is not None and d["chart"] is not None


# ---- per-timeframe range windows -------------------------------------------
def test_range_window_is_the_timeframe_s_own_window():
    """A 240m band is a horizon on a 1m scalp chart and one candle on the daily
    one. Each frame gets a window of roughly the bars it is showing."""
    assert RANGE_WINDOW_BY_TF == {"1m": 15, "15m": 60, "1h": 240,
                                  "4h": 1440, "1d": 10080}
    assert list(RANGE_WINDOW_BY_TF) == TF_ORDER

    candles = bars([100.0] * 600 + [130.0] * 10 + [100.0] * 30)
    windows = {tf: chart_payload(tf, candles, [], [])["range"] for tf in TF_ORDER}
    # the spike is 30..40 minutes back: outside the 1m band, inside every other
    assert windows["1m"]["window_min"] == 15 and windows["1m"]["high"] == 100.0
    assert windows["15m"]["window_min"] == 60 and windows["15m"]["high"] == 130.0
    assert windows["1h"]["window_min"] == 240 and windows["4h"]["window_min"] == 1440
    assert windows["1d"]["window_min"] == 10080
    # the label names the window, so the legend can say WHICH range it drew
    assert [windows[tf]["window_label"] for tf in TF_ORDER] == [
        "15分", "1時間", "4時間", "24時間", "7日"]


def test_window_label_units():
    assert window_label(15) == "15分" and window_label(59) == "59分"
    assert window_label(60) == "1時間" and window_label(240) == "4時間"
    assert window_label(1440) == "24時間"      # a rolling day, not a calendar one
    assert window_label(10080) == "7日"


def test_range_window_can_still_be_overridden():
    candles = bars([100.0] * 100 + [130.0] * 10 + [100.0] * 100)
    p = chart_payload("1m", candles, [], [], range_window=240)
    assert p["range"]["window_min"] == 240 and p["range"]["high"] == 130.0


# ---- price / time grids ----------------------------------------------------
def test_nice_step_is_a_one_two_five_ladder():
    for span in (37.0, 364_852.0, 1.2e6, 0.004, 88_000.0):
        step = nice_step(span)
        mantissa = step / 10.0 ** math.floor(math.log10(step))
        assert round(mantissa, 6) in (1.0, 2.0, 5.0), (span, step)
        assert 5 <= span / step <= 17          # 1/2/5 cannot always hit 8..12
    assert nice_step(0.0) == 1.0 and nice_step(float("nan")) == 1.0


def test_price_grid_lines_are_round_numbers_inside_the_extent():
    grid = price_grid(10_980_454.0, 11_345_306.0, 50_000.0)
    assert grid[0] == 11_000_000.0 and grid[-1] == 11_300_000.0
    assert all(g % 50_000.0 == 0 for g in grid)
    assert all(10_980_454.0 <= g <= 11_345_306.0 for g in grid)
    assert price_grid(1.0, 2.0, 0.0) == [] and price_grid(2.0, 1.0, 1.0) == []


def test_chart_scale_covers_every_drawn_thing():
    """A marker outside the candles' own extent must still land on the chart."""
    bar_rows = [{"ts": T0, "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.0, "v": 1.0}]
    sc = chart_scale(bar_rows, {"high": 105.0, "low": 95.0},
                     [{"price": 120.0}, {"price": 80.0}])
    assert sc["lo"] < 80.0 and sc["hi"] > 120.0
    assert 8 <= len(sc["grid"]) <= 14 and sc["step"] > 0
    assert chart_scale([]) is None


def test_time_grid_sits_on_clock_boundaries_per_timeframe():
    candles = bars([100.0] * (8 * 1440), start=T0)     # 8 UTC days of 1m bars
    per_tf = {tf: chart_payload(tf, candles, [], [], bars=400) for tf in TF_ORDER}

    for tf, period_min in (("1m", 5), ("15m", 60), ("1h", 240), ("4h", 1440)):
        p = per_tf[tf]
        stamps = [p["bars"][g["i"]]["ts"] for g in p["time_grid"]]
        assert stamps and all(s % (period_min * 60) == 0 for s in stamps)
        assert all(g["ts"] == p["bars"][g["i"]]["ts"] for g in p["time_grid"])
    # UTC midnight is the one line the eye should find
    assert [g["major"] for g in per_tf["1m"]["time_grid"]].count(True) <= 8
    assert all(g["major"] for g in per_tf["4h"]["time_grid"])
    # the daily frame steps weekly: 1970-01-01 was a Thursday, so Mondays
    for g in per_tf["1d"]["time_grid"]:
        assert datetime.fromtimestamp(g["ts"], timezone.utc).weekday() == 0


def test_time_grid_skips_boundaries_that_fall_in_a_data_gap():
    """The collector stopped over a boundary: no bar sits on it, so no line is
    drawn there rather than one drawn on the neighbouring bar."""
    have = bars([100.0] * 4, start=T0 + 60)            # 00:01..00:04
    later = bars([100.0] * 4, start=T0 + 11 * 60)      # 00:11..00:14
    grid = time_grid(have + later, "1m")               # 00:05 and 00:10 missing
    assert [g["ts"] for g in grid] == []
    with_boundary = time_grid(bars([100.0] * 12, start=T0), "1m")
    assert [g["ts"] for g in with_boundary] == [T0, T0 + 300, T0 + 600]


# ---- live 1m tail ----------------------------------------------------------
def _exec(sec, price, size, side="BUY"):
    stamp = datetime.fromtimestamp(T0 + sec, timezone.utc)
    return {"id": int(sec), "side": side, "price": price, "size": size,
            "exec_date": stamp.strftime("%Y-%m-%dT%H:%M:%S.000")}


def test_bars_from_executions_builds_1m_buckets_with_a_taker_split():
    execs = [_exec(10, 100.0, 1.0, "BUY"), _exec(30, 103.0, 2.0, "SELL"),
             _exec(50, 101.0, 0.5, "BUY"), _exec(70, 99.0, 1.0, "SELL")]
    out = bars_from_executions(list(reversed(execs)))   # the tape arrives newest-first
    assert [b["ts"] for b in out] == [T0, T0 + 60]
    first = out[0]
    assert (first["open"], first["high"], first["low"], first["close"]) == (100.0, 103.0, 100.0, 101.0)
    assert first["volume"] == 3.5 and first["buy_vol"] == 1.5 and first["sell_vol"] == 2.0
    assert first["trades"] == 3 and first["live"] is True
    # the fetch window began wherever count ran out, not on a minute boundary
    assert first["truncated"] is True and "truncated" not in out[1]
    assert bars_from_executions([]) == []
    assert bars_from_executions([{"price": "x", "exec_date": "nope"}]) == []


def test_bars_from_executions_orders_a_sweep_by_id_not_by_timestamp():
    """One market order sweeping three resting levels writes three rows with
    the SAME exec_date (one-second resolution), served newest-first. Folded by
    timestamp, the newest print became the open and the oldest the close: a
    100 -> 102 sweep drew as 102 -> 100, on every sweep the tape carried."""
    sweep = [dict(_exec(10, 100.0 + k, 1.0), id=k + 1) for k in range(3)]
    out = bars_from_executions(list(reversed(sweep)))    # the tape's own order
    assert len(out) == 1
    bar = out[0]
    assert (bar["open"], bar["close"]) == (100.0, 102.0)
    assert (bar["high"], bar["low"]) == (102.0, 100.0)
    assert bar["trades"] == 3 and bar["volume"] == 3.0
    # the id is the order, so any serving order folds to the same bar
    assert bars_from_executions(sweep) == out
    assert bars_from_executions([sweep[1], sweep[0], sweep[2]]) == out


def test_the_truncated_bucket_is_flagged_all_the_way_into_the_votes(tmp_path):
    """The fetch window starts wherever ``count`` ran out, mid-minute, so the
    oldest live bucket's volume is a floor. It is kept and flagged rather than
    dropped — the window is often ONE minute, and dropping it would take the
    live tail (and with it the staleness guard's only fresh bar) away — and the
    flag rides through the merge and the resample into ``closed_bars``."""
    _make_workspace(tmp_path)
    live = bars_from_executions([_exec(400 * 60 + 30, 11_900_000.0, 0.02)])
    assert len(live) == 1 and live[0]["truncated"] is True

    d = collect_market(tmp_path, now=T0 + 401 * 60, live_bars=live)
    assert d["live"]["bars"] == 1                  # kept: the tail is the tail
    assert d["state"]["stale"] is False            # so the guard still sees it
    row = d["chart"]["tfs"]["1m"]["bars"][-1]
    assert row["truncated"] is True and row["live"] is True
    assert row["partial"] is False and row["v"] == 0.02

    # 0.02 BTC "in" a minute the market traded ~1.5 in: a floor, not a volume
    volume = {t["tf"]: t["volume"] for t in d["timeframes"]}["1m"]
    assert volume["partial_excluded"] == 1 and volume["last"] == 1.5

    # and the flag survives a resample onto a slower bucket
    tail = [dict(b, live=True, truncated=True)
            for b in bars([101.0], start=T0 + 840)]
    tf15 = resample(merge_live_bars(bars([100.0] * 14), tail), "15m")
    assert tf15[0]["truncated"] is True and closed_bars(tf15) == []


def test_merge_live_bars_lets_the_csv_win_and_marks_what_is_live():
    csv_bars = bars([100.0, 101.0, 102.0])                     # T0 .. T0+120
    live = [dict(b, live=True, close=999.0) for b in bars([1.0], start=T0 + 120)]
    live += [dict(b, live=True) for b in bars([103.0, 104.0], start=T0 + 180)]

    merged = merge_live_bars(csv_bars, live)
    assert [b["ts"] for b in merged] == [T0, T0 + 60, T0 + 120, T0 + 180, T0 + 240]
    assert merged[2]["close"] == 102.0 and not merged[2].get("live")   # CSV wins
    assert [b.get("live") for b in merged[3:]] == [True, True]
    assert csv_bars[0]["close"] == 100.0 and live[0]["close"] == 999.0  # no mutation
    assert merge_live_bars(csv_bars, []) == csv_bars


def test_resample_carries_the_live_flag_up_to_the_bucket():
    src = bars([100.0] * 14) + [dict(b, live=True) for b in bars([101.0], start=T0 + 840)]
    out = resample(src, "15m")
    assert len(out) == 1 and out[0]["live"] is True and out[0]["close"] == 101.0


def test_live_tail_makes_a_stale_csv_feed_classifiable_again(tmp_path):
    """The fetch task rewrites the CSV every ~15 min, which is long enough for
    the staleness guard to call a live market dead. The merged tail is what the
    guard must key off."""
    _make_workspace(tmp_path)
    now = T0 + 400 * 60 + 20 * 60          # 20 minutes past the last CSV bar
    stale = collect_market(tmp_path, now=now)
    assert stale["state"]["stale"] is True and stale["state"]["state"] is None

    last_close = 11_000_000.0 * 1.0002 ** 400
    live = bars_from_executions(
        [_exec(400 * 60 + 19 * 60 + s, last_close, 0.1) for s in (0, 30, 59)])
    fresh = collect_market(tmp_path, now=now, live_bars=live)
    assert fresh["state"]["stale"] is False
    assert fresh["state"]["state"] in ("嵐", "ブレイク", "静穏レンジ", "通常")
    assert fresh["live"]["bars"] == 1 and fresh["live"]["last_ts"] > fresh["live"]["csv_last_ts"]
    assert fresh["chart"]["tfs"]["1m"]["bars"][-1]["live"] is True


def test_overlay_flow_fills_only_the_minutes_the_recorder_covered():
    candles = bars([100.0] * 5)
    flow = [dict(b, buy_vol=3.0, sell_vol=1.0) for b in bars([100.0] * 2, start=T0 + 60)]
    assert overlay_flow(candles, flow) == 2
    assert [c.get("buy_vol") for c in candles] == [None, 3.0, 3.0, None, None]
    assert overlay_flow(candles, []) == 0 and overlay_flow([], flow) == 0
    # a second pass is a no-op: an already-split minute is never overwritten
    assert overlay_flow(candles, flow) == 0


# ---- order book ------------------------------------------------------------
def _board(mid=11_000_000.0, n=40, step=100.0, size=0.5):
    return {
        "mid_price": mid,
        "bids": [{"price": mid - step * (i + 1), "size": size} for i in range(n)],
        "asks": [{"price": mid + step * (i + 1), "size": size * 0.8} for i in range(n)],
    }


def test_normalize_board_trims_to_the_drawable_window():
    nb = normalize_board(_board(n=400, step=100.0), now=T0)
    assert nb["best_bid"] == 10_999_900.0 and nb["best_ask"] == 11_000_100.0
    assert nb["spread"] == 200.0 and nb["mid"] == 11_000_000.0 and nb["fetched_at"] == T0
    # +-2% of 11M is +-220k, i.e. 2200 x 100 JPY levels: all 400 survive
    assert len(nb["bids"]) == 400 and nb["bid_total"] == nb["bid_total_all"]
    # a far-out ladder is dropped from the drawable levels but stays in the total
    far = normalize_board({"mid_price": 100.0,
                           "bids": [{"price": 99.0, "size": 1.0}, {"price": 50.0, "size": 9.0}],
                           "asks": [{"price": 101.0, "size": 1.0}]}, now=T0)
    assert far["bid_total"] == 1.0 and far["bid_total_all"] == 10.0


def test_normalize_board_rejects_what_cannot_be_drawn():
    assert normalize_board(None) is None
    assert normalize_board("nope") is None
    assert normalize_board({"bids": [], "asks": []}) is None
    assert normalize_board({"bids": [{"price": 1.0, "size": 1.0}]}) is None
    # crossed book: a snapshot we cannot reason about is not half-drawn
    assert normalize_board({"mid_price": 100.0,
                            "bids": [{"price": 101.0, "size": 1.0}],
                            "asks": [{"price": 99.0, "size": 1.0}]}) is None
    # unusable levels are dropped, not coerced
    ok = normalize_board({"mid_price": 100.0,
                          "bids": [{"price": 99.0, "size": 1.0}, {"price": 98.0, "size": 0.0},
                                   {"price": None, "size": 5.0}],
                          "asks": [{"price": 101.0, "size": 2.0}]})
    assert ok["bids"] == [[99.0, 1.0]] and ok["bid_total_all"] == 1.0


def test_board_depth_uses_the_chart_s_own_price_buckets():
    """The panel shares the price pane's y-axis, so the book has to be summed
    onto the very gridlines drawn next to it."""
    nb = normalize_board(_board(mid=11_000_000.0, n=40, step=100.0, size=0.5))
    dp = board_depth(nb, 10_995_000.0, 11_005_000.0, 1000.0)
    assert dp["step"] == 1000.0 and dp["start"] == 10_995_000.0 and dp["count"] == 10
    assert all(bk["p"] % 1000.0 == 0 for bk in dp["buckets"])
    # 40 bids x 0.5 and 40 asks x 0.4, all inside the +-4000 JPY window
    assert dp["bid_sum"] == pytest.approx(20.0) and dp["ask_sum"] == pytest.approx(16.0)
    assert dp["outside"] == 0 and dp["max"] > 0 and dp["mid"] == 11_000_000.0

    # a window too narrow to hold the book: the rest is counted, never clamped
    # onto the edge bucket (two 100 JPY buckets fit; 79 of the 80 levels do not)
    narrow = board_depth(nb, 10_999_950.0, 11_000_050.0, 100.0)
    assert narrow["count"] == 2 and narrow["outside"] == 79
    assert narrow["bid_sum"] == 0.5 and narrow["ask_sum"] == 0.0
    assert board_depth(None, 1.0, 2.0, 0.1) is None
    assert board_depth(nb, 1.0, 2.0, 0.0) is None


def test_attach_board_wires_every_timeframe_and_survives_a_failed_fetch(tmp_path):
    _make_workspace(tmp_path)
    payload = collect_market(tmp_path, now=T0 + 400 * 60)
    last = payload["chart"]["tfs"]["1m"]["bars"][-1]["c"]
    attach_board(payload, _board(mid=last, n=60, step=200.0), now=T0)

    assert payload["board"]["mid"] == last and payload["board"]["fetched_at"] == T0
    for tf in TF_ORDER:
        depth = payload["chart"]["tfs"][tf]["depth"]
        scale = payload["chart"]["tfs"][tf]["scale"]
        assert depth["step"] == scale["step"]      # same ladder as the gridlines
    json.dumps(payload)

    attach_board(payload, None)                    # the fetch failed
    assert payload["board"] is None
    assert all(payload["chart"]["tfs"][tf]["depth"] is None for tf in TF_ORDER)
    # a payload with no chart at all (empty workspace) must not raise either
    assert attach_board({"chart": None}, _board())["board"] is not None


# ---- volume pane -----------------------------------------------------------
def test_chart_payload_carries_the_volume_pane_s_inputs():
    src = bars([100.0] * 30, volume=[1.0 + i for i in range(30)])
    for b in src[:10]:
        b["buy_vol"], b["sell_vol"] = 0.6, 0.4
    p = chart_payload("1m", src, [], [])
    assert p["vmax"] == 30.0 == max(b["v"] for b in p["bars"])
    assert p["bars"][0]["bv"] == 0.6 and p["bars"][0]["sv"] == 0.4
    # a minute with no recorded split says so rather than inventing a 50/50 one
    assert "bv" not in p["bars"][-1] and "sv" not in p["bars"][-1]


def test_returns_refuse_to_measure_across_a_hole_in_the_series():
    """With the live tail merged in, a dead collector leaves a gap between the
    last CSV bar and the live minutes. Calling the move across that gap a
    30-minute return lit 嵐 on a market that had not moved in 30 minutes."""
    old = bars([100.0] * 60)                       # ends at T0 + 59m
    fresh = [dict(b, live=True) for b in bars([130.0] * 3, start=T0 + 24 * 3600)]
    st = market_state(old + fresh, now=T0 + 24 * 3600 + 180)

    assert st["stale"] is False                    # the tape IS live
    assert st["ret_30m_pct"] is None               # but there is no 30m ago bar
    assert st["state"] != "嵐"
    # the guard is per-window, not a blanket refusal: a bar really does sit 24h
    # back, so THAT return is still reported
    assert st["ret_24h_pct"] == pytest.approx(30.0)

    # a normal 15-minute CSV lag is well inside the tolerance and still reports
    lagging = bars([100.0] * 60) + [dict(b, live=True)
                                    for b in bars([101.0] * 2, start=T0 + 75 * 60)]
    ok = market_state(lagging, now=T0 + 77 * 60)
    assert ok["ret_30m_pct"] == pytest.approx(1.0, abs=0.01)


def test_collect_market_reports_how_far_the_csv_writer_has_fallen_behind(tmp_path):
    _make_workspace(tmp_path)
    csv_end = T0 + 399 * 60
    live = bars_from_executions([_exec(399 * 60 + 60 + s, 11_900_000.0, 0.1)
                                 for s in (1, 30)])
    near = collect_market(tmp_path, now=csv_end + 180, live_bars=live)
    assert near["live"]["gap_sec"] == 0.0          # the very next minute

    late = bars_from_executions([_exec(399 * 60 + 3600 + s, 11_900_000.0, 0.1)
                                 for s in (1, 30)])
    behind = collect_market(tmp_path, now=csv_end + 3700, live_bars=late)
    assert behind["live"]["gap_sec"] == pytest.approx(3540.0)
    assert collect_market(tmp_path, now=csv_end)["live"]["gap_sec"] is None


def test_collect_market_survives_a_tape_that_only_fills_an_internal_hole(tmp_path):
    """Every merged-in minute can sit at or BEFORE the last CSV minute: the
    fetch task dropped a minute and moved on, and the tape backfills that hole.
    There is then no "how far behind" to measure — and measuring it over an
    empty set raised ValueError out of the /api/market handler."""
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    rows = ["ts,open,high,low,close,volume"]
    for i in range(10):
        if i == 5:                       # the minute the collector missed
            continue
        stamp = datetime.fromtimestamp(T0 + i * 60, timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S+00:00")
        rows.append(f"{stamp},100,101,99,100,1.0")
    (tmp_path / "data" / "candles_FX_BTC_JPY.csv").write_text(
        "\n".join(rows) + "\n", encoding="utf-8")

    live = bars_from_executions([_exec(5 * 60 + 10, 100.0, 0.3)])
    assert [b["ts"] for b in live] == [T0 + 5 * 60]

    d = collect_market(tmp_path, now=T0 + 10 * 60, live_bars=live)
    assert d["live"]["bars"] == 1                      # the hole was filled
    assert d["live"]["csv_last_ts"] == T0 + 9 * 60
    assert d["live"]["last_ts"] == T0 + 9 * 60         # nothing past the head
    assert d["live"]["gap_sec"] is None                # so there is no gap
    assert d["chart"]["tfs"]["1m"]["bars"][5]["ts"] == T0 + 5 * 60


def test_the_forming_minute_never_reaches_a_closed_bar_computation(tmp_path):
    """Two seconds into the current minute the tape has one execution in it.
    On the 1m frame that was published as a closed bar, so the volume vote read
    0.02 BTC as a minute's volume."""
    _make_workspace(tmp_path)
    price = 11_000_000.0 * 1.0002 ** 400
    live = bars_from_executions([_exec(400 * 60 + 5, price, 0.2),     # closed
                                 _exec(401 * 60 + 2, price, 0.05)])   # forming
    now = T0 + 401 * 60 + 2
    d = collect_market(tmp_path, now=now, live_bars=live)

    rows = d["chart"]["tfs"]["1m"]["bars"]
    assert rows[-1]["ts"] == T0 + 401 * 60 and rows[-1]["partial"] is True
    assert rows[-2]["ts"] == T0 + 400 * 60 and rows[-2]["partial"] is False
    for tf in TF_ORDER:                     # every slower frame is open too
        assert d["chart"]["tfs"][tf]["bars"][-1]["partial"] is True

    # the vote is what it would have been without the fraction of a minute:
    # bucket 401 is partial, bucket 400 is the tape's truncated one
    volume = {t["tf"]: t["volume"] for t in d["timeframes"]}["1m"]
    base = {t["tf"]: t["volume"] for t in
            collect_market(tmp_path, now=now)["timeframes"]}["1m"]
    assert volume["partial_excluded"] == 2 and base["partial_excluded"] == 0
    assert volume["last"] == base["last"] == 1.5
    assert volume["score"] == base["score"]
    assert volume["angle_deg"] == base["angle_deg"]

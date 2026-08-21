"""Market view — resampling, the trend vote, state classification and the
chart payload the dashboard's マーケット tab draws."""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone

import pytest

from bot.monitoring.market_view import (
    chart_payload, collect_market, market_state, oi_trend, parse_bot_events,
    parse_scalp_events, resample, series_trend, slope_angle, taker_split,
    trend, volatility, volume_trend,
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
    assert st["last_price"] == 100.0
    assert market_state([], now=T0) is None


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
                            "bot_events": 0, "scalp_events": 0}
    json.dumps(d)


def test_collect_market_payload_is_json_serialisable(tmp_path):
    _make_workspace(tmp_path)
    json.dumps(collect_market(tmp_path, now=T0))


def _make_workspace(root):
    """A miniature data/ + logs/ in the shapes the collectors really write."""
    (root / "data").mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(parents=True, exist_ok=True)
    rows = ["ts,open,high,low,close,volume"]
    flow = ["ts,open,high,low,close,volume,buy_vol,sell_vol,trades"]
    price = 11_000_000.0
    for i in range(400):
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
    assert d["chart"]["default_tf"] == "15m"
    assert d["chart"]["range_window_min"] == 240


def test_collect_market_survives_a_missing_candle_file(tmp_path):
    """flow alone is enough — it repeats the same OHLCV columns."""
    _make_workspace(tmp_path)
    (tmp_path / "data" / "candles_FX_BTC_JPY.csv").unlink()
    d = collect_market(tmp_path, now=T0 + 400 * 60)
    assert d["sources"]["candles"] == 0
    assert d["state"] is not None and d["chart"] is not None

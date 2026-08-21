"""Tests for the pending-gate judgment harness (scripts/judge_gates.py).

Every gate is driven off synthetic fixture files written into tmp_path — the
same shapes the live components write (bot.logging_setup.log_decision for
logs/bot.jsonl, scripts/run_scalp_paper.py for data/scalp_paper.jsonl,
scripts/record_oi.py for data/oi_snapshots.csv, scripts/record_realtime.py for
data/ws/*.jsonl.gz, scripts/fetch_history.py for the candle CSVs).

The harness must never adopt anything and must never crash: a missing, partial
or corrupt file has to come out as INSUFFICIENT with a sample count, not an
exception. Gates 1-4 are covered in PASS / FAIL / INSUFFICIENT form; the
coverage-only gates 5-8 are smoke-tested at both ends of their bar.
"""
from __future__ import annotations

import gzip
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import judge_gates as jg  # noqa: E402

PRICE = 10_000_000.0
SIZE = 0.02
NOTIONAL = PRICE * SIZE           # 200,000 JPY
SCALP_NOTIONAL = 110_000.0        # scripts/run_scalp_paper.py --notional default
BASE_DAY = datetime(2026, 8, 1, tzinfo=timezone.utc).timestamp()


def by_id(results, gate_id):
    return next(r for r in results if r.gate_id == gate_id)


# ---- fixture writers -------------------------------------------------------
def _write_lines(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def decision(ts, signal, *, decision="ORDER_SENT", price=PRICE, size=SIZE,
             pnl=0.0, status="FILLED"):
    """One logs/bot.jsonl record in bot.logging_setup.log_decision's shape."""
    return {
        "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
        "level": "INFO", "logger": "bot.main", "message": "decision",
        "event": "decision", "symbol": "FX_BTC_JPY", "price": price,
        "strategy_signal": signal, "indicator_values": {"mom": 1.0},
        "decision": decision, "order_size": size, "order_price": price,
        "order_id": f"o{int(ts)}", "execution_status": status,
        "PnL": pnl, "reason": "test",
    }


def champion_log(n, pct, *, side="LONG", hour=13, minute=0, per_day=3,
                 base=BASE_DAY, exit_signal=None, start_cum=0.0):
    """n closed champion trades, each returning ``pct`` % of notional.

    Trades are spread over ceil(n/per_day) UTC days so the day-clustered
    bootstrap has more than one cluster to resample.
    """
    rows, cum = [], start_cum
    open_sig = "BUY" if side == "LONG" else "SELL"
    close_sig = exit_signal or ("SELL" if side == "LONG" else "BUY")
    for i in range(n):
        day = base + (i // per_day) * 86400
        entry = day + hour * 3600 + minute * 60 + (i % per_day) * 300
        rows.append(decision(entry, open_sig, pnl=cum))
        cum += pct / 100 * NOTIONAL
        rows.append(decision(entry + 60, close_sig, pnl=cum))
    return rows


def scalp_event(ts, bps, *, armed=False, thr=10.0, sigma=12.0, e2=True,
                side="LONG", notional=SCALP_NOTIONAL):
    """limit_placed -> fill -> exit, the maker-entry/E2-exit event sequence."""
    size = notional / PRICE
    rows = [{"ts": ts, "event": "limit_placed", "entry_mode": "maker",
             "side": side, "limit": PRICE, "size": size, "signal_bps": 12.0,
             "radar_armed": armed, "thr_bps": thr, "fill_timeout_sec": 10.0,
             "sigma60_bps": sigma, "v60_btc": 3.0},
            {"ts": ts + 1, "event": "fill", "entry_mode": "maker", "side": side,
             "price": PRICE, "size": size, "signal_bps": 12.0,
             "fill_latency_sec": 1.0}]
    exit_rec = {"ts": ts + 60, "event": "exit", "entry_mode": "maker",
                "side": side, "price": PRICE, "pnl_jpy": bps / 1e4 * notional,
                "daily_pnl": 0.0, "trades": 1}
    if e2:
        exit_rec["exit_kind"] = "tp_maker"      # the E2-era marker
    rows.append(exit_rec)
    return rows


def scalp_start(ts, *, thr=10.0, thr_armed=10.0):
    return {"ts": ts, "event": "start", "thr_bps": thr, "thr_armed_bps": thr_armed,
            "window_sec": 5.0, "hold_sec": 60.0, "entry": "maker",
            "exit": "maker_tp", "tp_bps": 10.0, "fallback_sec": 120.0,
            "notional": SCALP_NOTIONAL}


def scalp_log(n, bps, *, armed=False, thr=10.0, sigma=12.0, e2=True,
              per_day=4, base=BASE_DAY, hour=13, start=True):
    rows = [scalp_start(base - 60)] if start else []
    for i in range(n):
        day = base + (i // per_day) * 86400
        rows += scalp_event(day + hour * 3600 + (i % per_day) * 600, bps,
                            armed=armed, thr=thr, sigma=sigma, e2=e2)
    return rows


def write_bot(root, rows):
    _write_lines(root / "logs" / "bot.jsonl", rows)


def write_scalp(root, rows):
    _write_lines(root / "data" / "scalp_paper.jsonl", rows)


# ---- G1: main bot ----------------------------------------------------------
def test_g1_pass(tmp_path):
    write_bot(tmp_path, champion_log(30, 0.2))
    g1 = by_id(jg.judge_all(tmp_path, iters=200), "G1")
    assert g1.status == jg.PASS
    assert g1.n == 30
    assert g1.values["net_pct"] == pytest.approx(0.2)
    assert g1.values["max_dd_pct"] == pytest.approx(0.0)


def test_g1_fail_on_expectancy(tmp_path):
    write_bot(tmp_path, champion_log(30, -0.1))
    g1 = by_id(jg.judge_all(tmp_path, iters=200), "G1")
    assert g1.status == jg.FAIL
    assert g1.n == 30
    assert g1.values["net_pct"] == pytest.approx(-0.1)


def test_g1_fail_on_drawdown_even_with_positive_expectancy(tmp_path):
    # +0.2%/trade on average, but a 12% equity hole in the middle: the maxDD
    # bar is an AND, not a tiebreak
    rows = champion_log(20, 0.2)
    rows += champion_log(1, -12.0, base=BASE_DAY + 40 * 86400,
                         start_cum=20 * 0.2 / 100 * NOTIONAL)
    rows += champion_log(20, 0.9, base=BASE_DAY + 60 * 86400,
                         start_cum=(20 * 0.2 - 12.0) / 100 * NOTIONAL)
    write_bot(tmp_path, rows)
    g1 = by_id(jg.judge_all(tmp_path, iters=200), "G1")
    assert g1.n == 41
    assert g1.values["net_pct"] > jg.MAIN_NET_PCT_BAR
    assert g1.values["max_dd_pct"] > jg.MAIN_MAXDD_BAR
    assert g1.status == jg.FAIL


def test_g1_insufficient(tmp_path):
    write_bot(tmp_path, champion_log(5, 0.5))
    g1 = by_id(jg.judge_all(tmp_path, iters=200), "G1")
    assert g1.status == jg.INSUFFICIENT
    assert g1.n == 5 and g1.need == 30


def test_g1_missing_file_is_insufficient_not_crash(tmp_path):
    g1 = by_id(jg.judge_all(tmp_path, iters=200), "G1")
    assert g1.status == jg.INSUFFICIENT
    assert g1.n == 0
    assert "not found" in " ".join(g1.notes)


def test_g1_since_restarts_the_count(tmp_path):
    # §5: a strategy switch restarts the 30-trade count. The log carries no
    # strategy name, so --since is the only way to express the restart.
    rows = champion_log(20, 0.2)
    rows += champion_log(12, 0.2, base=BASE_DAY + 30 * 86400,
                         start_cum=20 * 0.2 / 100 * NOTIONAL)
    write_bot(tmp_path, rows)
    since = BASE_DAY + 30 * 86400
    g1 = by_id(jg.judge_all(tmp_path, since=since, iters=200), "G1")
    assert g1.n == 12
    assert g1.status == jg.INSUFFICIENT
    assert any("COUNT RESTART" in n for n in g1.notes)


def test_g1_reconstructs_shorts_and_stop_loss_exits(tmp_path):
    rows = champion_log(2, 0.3, side="SHORT", exit_signal="STOP_LOSS")
    write_bot(tmp_path, rows)
    trades, meta = jg.load_champion_trades(tmp_path)
    assert [t.side for t in trades] == ["SHORT", "SHORT"]
    assert [t.exit_signal for t in trades] == ["STOP_LOSS", "STOP_LOSS"]
    assert trades[0].pnl_jpy == pytest.approx(0.3 / 100 * NOTIONAL)
    assert trades[0].pnl_pct == pytest.approx(0.3)
    assert meta["open_at_end"] is False


def test_g1_ignores_holds_rejections_and_unknown_state(tmp_path):
    rows = [decision(BASE_DAY, "HOLD", decision="HOLD", status=None, pnl=0.0),
            decision(BASE_DAY + 60, "BUY", decision="REJECTED", status=None),
            decision(BASE_DAY + 120, "BUY", pnl=0.0),
            # ambiguous close: STATE_UNKNOWN with no realized step -> not booked
            decision(BASE_DAY + 180, "SELL", status="STATE_UNKNOWN", pnl=0.0),
            decision(BASE_DAY + 240, "SELL", pnl=500.0)]
    write_bot(tmp_path, rows)
    trades, meta = jg.load_champion_trades(tmp_path)
    assert len(trades) == 1
    assert trades[0].pnl_jpy == pytest.approx(500.0)
    assert meta["unresolved_orders"] == 1


def test_g1_survives_corrupt_and_truncated_lines(tmp_path):
    path = tmp_path / "logs" / "bot.jsonl"
    path.parent.mkdir(parents=True)
    rows = champion_log(4, 0.2)
    with open(path, "w", encoding="utf-8") as f:
        f.write("{not json at all\n")
        for row in rows:
            f.write(json.dumps(row) + "\n")
        f.write('{"timestamp": "2026-08-0')      # half-written tail line
    trades, meta = jg.load_champion_trades(tmp_path)
    assert len(trades) == 4
    assert meta["bad_lines"] == 2
    g1 = by_id(jg.judge_all(tmp_path, iters=200), "G1")
    assert g1.status == jg.INSUFFICIENT


# ---- G2: scalper -----------------------------------------------------------
def test_g2_pass(tmp_path):
    write_scalp(tmp_path, scalp_log(30, 6.0))
    g2 = by_id(jg.judge_all(tmp_path, iters=200), "G2")
    assert g2.status == jg.PASS
    assert g2.n == 30
    assert g2.values["net_bps"] == pytest.approx(6.0)


def test_g2_fail(tmp_path):
    write_scalp(tmp_path, scalp_log(30, 2.0))
    g2 = by_id(jg.judge_all(tmp_path, iters=200), "G2")
    assert g2.status == jg.FAIL
    assert g2.values["net_bps"] == pytest.approx(2.0)


def test_g2_insufficient(tmp_path):
    write_scalp(tmp_path, scalp_log(10, 6.0))
    g2 = by_id(jg.judge_all(tmp_path, iters=200), "G2")
    assert g2.status == jg.INSUFFICIENT
    assert g2.n == 10 and g2.need == 30


def test_g2_counts_only_events_after_the_e2_switch(tmp_path):
    old = scalp_log(40, 20.0, e2=False, base=BASE_DAY)
    new = scalp_log(5, 6.0, e2=True, base=BASE_DAY + 20 * 86400, start=False)
    write_scalp(tmp_path, old + new)
    g2 = by_id(jg.judge_all(tmp_path, iters=200), "G2")
    assert g2.n == 5                       # the 40 pre-E2 events do not count
    assert g2.status == jg.INSUFFICIENT
    assert any("exit_kind" in n for n in g2.notes)


def test_g2_no_e2_marker_means_no_countable_events(tmp_path):
    write_scalp(tmp_path, scalp_log(50, 9.0, e2=False))
    g2 = by_id(jg.judge_all(tmp_path, iters=200), "G2")
    assert g2.n == 0
    assert g2.status == jg.INSUFFICIENT
    assert any("predates the E2 switch" in n for n in g2.notes)


def test_g2_later_armed_threshold_restart_binds(tmp_path):
    # E2-era exits exist from day 0, but the armed-threshold reversion happens
    # LATER: the later boundary is the one that binds (§5, two restarts).
    rows = [scalp_start(BASE_DAY - 60, thr=10.0, thr_armed=8.0)]
    rows += scalp_log(30, 9.0, base=BASE_DAY, start=False)
    restart = BASE_DAY + 20 * 86400
    rows += [scalp_start(restart, thr=10.0, thr_armed=10.0)]
    rows += scalp_log(4, 9.0, base=restart + 3600, start=False)
    write_scalp(tmp_path, rows)
    trades, meta = jg.load_scalp_trades(tmp_path)
    assert meta["e2_ts"] < meta["thr_ts"]
    assert meta["epoch_ts"] == meta["thr_ts"]
    assert "armed-threshold" in meta["epoch_reason"]
    g2 = by_id(jg.judge_all(tmp_path, iters=200), "G2")
    assert g2.n == 4


def test_g2_missing_file_is_insufficient(tmp_path):
    g2 = by_id(jg.judge_all(tmp_path, iters=200), "G2")
    assert g2.status == jg.INSUFFICIENT and g2.n == 0


def test_g2_orphan_exit_falls_back_to_session_notional(tmp_path):
    rows = [scalp_start(BASE_DAY - 60),
            {"ts": BASE_DAY, "event": "exit", "side": "LONG", "price": PRICE,
             "pnl_jpy": 55.0, "exit_kind": "fallback_taker"}]
    write_scalp(tmp_path, rows)
    trades, meta = jg.load_scalp_trades(tmp_path)
    assert meta["orphan_exits"] == 1
    assert trades[0].bps == pytest.approx(5.0)     # 55 JPY on 110,000 notional


# ---- G3: armed vs unarmed --------------------------------------------------
def test_g3_ready_with_both_arms_full(tmp_path):
    rows = scalp_log(30, 8.0, armed=True, base=BASE_DAY)
    rows += scalp_log(30, 4.0, armed=False, base=BASE_DAY + 20 * 86400,
                      start=False)
    write_scalp(tmp_path, rows)
    g3 = by_id(jg.judge_all(tmp_path, iters=200), "G3")
    assert g3.status == jg.READY
    assert g3.values["armed"] == 30 and g3.values["unarmed"] == 30
    assert g3.values["diff_bps"] == pytest.approx(4.0)


def test_g3_insufficient_when_one_arm_is_thin(tmp_path):
    rows = scalp_log(30, 8.0, armed=True, base=BASE_DAY)
    rows += scalp_log(3, 4.0, armed=False, base=BASE_DAY + 20 * 86400, start=False)
    write_scalp(tmp_path, rows)
    g3 = by_id(jg.judge_all(tmp_path, iters=200), "G3")
    assert g3.status == jg.INSUFFICIENT
    assert g3.n == 3


def test_g3_excludes_unequal_threshold_events(tmp_path):
    # armed events taken at thr 8 are NOT comparable with unarmed at thr 10
    rows = scalp_log(30, 8.0, armed=True, thr=8.0, base=BASE_DAY)
    rows += scalp_log(30, 4.0, armed=False, thr=10.0,
                      base=BASE_DAY + 20 * 86400, start=False)
    write_scalp(tmp_path, rows)
    g3 = by_id(jg.judge_all(tmp_path, iters=200), "G3")
    assert g3.values["thr_ref_bps"] == pytest.approx(10.0)
    assert g3.values["armed"] == 0 and g3.values["unarmed"] == 30
    assert any("excluded" in n for n in g3.notes)
    assert g3.status == jg.INSUFFICIENT


# ---- G4: C2 / C3 subsets ---------------------------------------------------
def test_g4a_pass_inside_radar_window(tmp_path):
    write_bot(tmp_path, champion_log(20, 0.4, hour=13))     # 13:00 UTC = armed
    g4a = by_id(jg.judge_all(tmp_path, iters=400), "G4a")
    assert g4a.n == 20
    assert g4a.status == jg.PASS
    lo, hi, days = g4a.values["ci"]
    assert lo > 0 and hi > 0 and days >= 2
    assert any("OWNER APPROVAL" in n for n in g4a.notes)


def test_g4a_fail_on_negative_subset(tmp_path):
    write_bot(tmp_path, champion_log(20, -0.4, hour=13))
    g4a = by_id(jg.judge_all(tmp_path, iters=400), "G4a")
    assert g4a.n == 20 and g4a.status == jg.FAIL


def test_g4a_insufficient_outside_the_window(tmp_path):
    # 03:00 UTC is outside 12:30-15:00: the whole champion set is out of subset
    write_bot(tmp_path, champion_log(40, 0.4, hour=3))
    results = jg.judge_all(tmp_path, iters=200)
    g1, g4a = by_id(results, "G1"), by_id(results, "G4a")
    assert g1.n == 40 and g1.status == jg.PASS
    assert g4a.n == 0 and g4a.status == jg.INSUFFICIENT and g4a.need == 15


def test_g4b_long_only_subset(tmp_path):
    rows = champion_log(16, 0.4, side="LONG", hour=3)
    rows += champion_log(9, -0.9, side="SHORT", hour=3,
                         base=BASE_DAY + 30 * 86400,
                         start_cum=16 * 0.4 / 100 * NOTIONAL)
    write_bot(tmp_path, rows)
    results = jg.judge_all(tmp_path, iters=400)
    g4b = by_id(results, "G4b")
    assert g4b.n == 16
    assert g4b.values["net_pct"] == pytest.approx(0.4)
    assert g4b.status == jg.PASS
    assert by_id(results, "G1").n == 25         # the full set keeps the shorts


def test_g4b_insufficient_below_subset_bar(tmp_path):
    write_bot(tmp_path, champion_log(14, 0.4, side="LONG", hour=3))
    g4b = by_id(jg.judge_all(tmp_path, iters=200), "G4b")
    assert g4b.n == 14 and g4b.status == jg.INSUFFICIENT


def test_g4_ci_including_zero_fails_the_gate(tmp_path):
    # alternating +/- with a positive mean but a CI straddling 0
    rows, cum = [], 0.0
    for i in range(20):
        day = BASE_DAY + i * 86400
        entry = day + 13 * 3600
        rows.append(decision(entry, "BUY", pnl=cum))
        cum += (3.0 if i % 2 == 0 else -2.7) / 100 * NOTIONAL
        rows.append(decision(entry + 60, "SELL", pnl=cum))
    write_bot(tmp_path, rows)
    g4a = by_id(jg.judge_all(tmp_path, iters=800), "G4a")
    lo, hi, _ = g4a.values["ci"]
    assert lo < 0 < hi
    assert g4a.status == jg.FAIL


# ---- G5: TP vol tilt -------------------------------------------------------
def test_g5_ready_and_buckets_by_sigma(tmp_path):
    rows = [scalp_start(BASE_DAY - 60)]
    for i in range(30):
        sigma = 5.0 + i                     # low/mid/high terciles by sigma60
        bps = 10.0 if sigma >= 25.0 else 2.0
        rows += scalp_event(BASE_DAY + i * 600, bps, sigma=sigma)
    write_scalp(tmp_path, rows)
    g5 = by_id(jg.judge_all(tmp_path, iters=200), "G5")
    assert g5.status == jg.READY
    assert g5.n == 30
    assert g5.values["buckets"]["high"]["net_bps"] > g5.values["buckets"]["low"]["net_bps"]
    assert any("separate study" in n for n in g5.notes)


def test_g5_insufficient_without_sigma(tmp_path):
    rows = [scalp_start(BASE_DAY - 60)]
    for i in range(30):
        rows += scalp_event(BASE_DAY + i * 600, 6.0, sigma=None)
    write_scalp(tmp_path, rows)
    g5 = by_id(jg.judge_all(tmp_path, iters=200), "G5")
    assert g5.n == 0 and g5.status == jg.INSUFFICIENT


# ---- G6: OI coverage -------------------------------------------------------
def _write_oi(root, rows, *, step=900):
    path = root / "data" / "oi_snapshots.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("ts_utc,okx_usdt_oi,okx_usd_oi,okx_ls_ratio,dvol,deribit_oi\n")
        for i in range(rows):
            ts = datetime.fromtimestamp(BASE_DAY + i * step, tz=timezone.utc)
            f.write(f"{ts.isoformat()},1.0,2.0,1.13,38.25,3.0\n")
    return path


def test_g6_insufficient_and_ready(tmp_path):
    _write_oi(tmp_path, 100)
    g6 = by_id(jg.judge_all(tmp_path, iters=100), "G6")
    assert g6.status == jg.INSUFFICIENT and g6.n == 100
    _write_oi(tmp_path, jg.OI_ROWS_BAR)
    g6 = by_id(jg.judge_all(tmp_path, iters=100), "G6")
    assert g6.status == jg.READY
    assert g6.values["span_days"] > 29


def test_g6_tolerates_malformed_rows(tmp_path):
    path = _write_oi(tmp_path, 5)
    with open(path, "a", encoding="utf-8") as f:
        f.write("not,a,timestamp,x,y,z\n")
        f.write("\n")
    g6 = by_id(jg.judge_all(tmp_path, iters=100), "G6")
    assert g6.n == 5
    assert any("malformed" in n for n in g6.notes)


# ---- G7: board data --------------------------------------------------------
def _write_ws(root, days, *, size=1024):
    ws = root / "data" / "ws"
    ws.mkdir(parents=True, exist_ok=True)
    for i in range(days):
        start = BASE_DAY + i * 86400
        stamp = datetime.fromtimestamp(start, tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = ws / f"FX_BTC_JPY_{stamp}.jsonl.gz"
        with gzip.open(path, "wb") as f:
            f.write(b"x" * size)
        os.utime(path, (start + 3600, start + 3600))
    return ws


def test_g7_span_and_size_are_an_and(tmp_path, monkeypatch):
    _write_ws(tmp_path, 9)
    g7 = by_id(jg.judge_all(tmp_path, iters=100), "G7")
    assert g7.values["files"] == 9
    assert g7.values["span_days"] > jg.BOARD_DAYS_BAR
    assert g7.status == jg.INSUFFICIENT          # span met, volume not
    monkeypatch.setattr(jg, "BOARD_BYTES_BAR", 100)
    g7 = by_id(jg.judge_all(tmp_path, iters=100), "G7")
    assert g7.status == jg.READY


def test_g7_missing_directory(tmp_path):
    g7 = by_id(jg.judge_all(tmp_path, iters=100), "G7")
    assert g7.status == jg.INSUFFICIENT and g7.n == 0


# ---- G8: funding window ----------------------------------------------------
def _write_candles(root, days, *, name="candles_FX_BTC_JPY.csv", folder="data",
                   cover_window=True):
    path = root / folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("ts,open,high,low,close,volume\n")
        for d in range(days):
            minutes = [0] if not cover_window else [0, 30]
            for m in minutes:
                ts = datetime.fromtimestamp(
                    BASE_DAY + d * 86400 + 13 * 3600 + m * 60, tz=timezone.utc)
                f.write(f"{ts} ,1,2,0,1,0.5\n".replace(" ,", ","))
    return path


def test_g8_ready_at_three_times_the_original_n(tmp_path):
    _write_candles(tmp_path, jg.FUNDING_N_BAR)
    g8 = by_id(jg.judge_all(tmp_path, iters=100), "G8")
    assert g8.n == jg.FUNDING_N_BAR and g8.status == jg.READY


def test_g8_needs_the_whole_window_not_just_the_settlement_minute(tmp_path):
    _write_candles(tmp_path, 70, cover_window=False)
    g8 = by_id(jg.judge_all(tmp_path, iters=100), "G8")
    assert g8.n == 0 and g8.status == jg.INSUFFICIENT


def test_g8_unions_snapshot_and_live_sources(tmp_path):
    _write_candles(tmp_path, 20, folder="backtest_data",
                   name="candles_FX_BTC_JPY_20260801.csv")
    _write_candles(tmp_path, 20)                 # same days, live copy
    g8 = by_id(jg.judge_all(tmp_path, iters=100), "G8")
    assert g8.n == 20                            # union, not sum
    assert g8.values["sources"] == 2


# ---- harness behaviour -----------------------------------------------------
def test_empty_root_reports_every_gate_without_crashing(tmp_path):
    results = jg.judge_all(tmp_path, iters=100)
    assert [r.gate_id for r in results] == ["G1", "G2", "G3", "G4a", "G4b",
                                            "G5", "G6", "G7", "G8"]
    assert all(r.status == jg.INSUFFICIENT for r in results)
    assert all(r.n == 0 for r in results)


def test_report_is_deterministic_and_idempotent(tmp_path):
    write_bot(tmp_path, champion_log(30, 0.2))
    write_scalp(tmp_path, scalp_log(30, 6.0))
    first = jg.render(jg.judge_all(tmp_path, iters=300), root=tmp_path, since=None)
    second = jg.render(jg.judge_all(tmp_path, iters=300), root=tmp_path, since=None)
    body = lambda text: "\n".join(  # noqa: E731 - drop the generated-at line
        ln for ln in text.splitlines() if not ln.startswith("root "))
    assert body(first) == body(second)
    assert "adopts nothing" in first
    for gate_id in ("G1", "G2", "G3", "G4a", "G4b", "G5", "G6", "G7", "G8"):
        assert f"[{gate_id}]" in first


def test_main_prints_table_and_json(tmp_path, capsys):
    write_bot(tmp_path, champion_log(30, 0.2))
    assert jg.main(["--root", str(tmp_path), "--bootstrap", "100"]) == 0
    out = capsys.readouterr().out
    assert "PENDING-GATE JUDGMENT" in out and "PASS" in out

    assert jg.main(["--root", str(tmp_path), "--bootstrap", "100", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["gates"]) == 9
    assert payload["gates"][0]["status"] == jg.PASS


def test_main_rejects_an_unparseable_since(tmp_path, capsys):
    assert jg.main(["--root", str(tmp_path), "--since", "last tuesday"]) == 2
    assert "cannot parse" in capsys.readouterr().err


def test_files_are_never_written_or_modified(tmp_path):
    write_bot(tmp_path, champion_log(4, 0.2))
    write_scalp(tmp_path, scalp_log(4, 6.0))
    _write_oi(tmp_path, 3)
    before = {p: (p.stat().st_size, p.stat().st_mtime)
              for p in tmp_path.rglob("*") if p.is_file()}
    jg.judge_all(tmp_path, iters=100)
    after = {p: (p.stat().st_size, p.stat().st_mtime)
             for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after

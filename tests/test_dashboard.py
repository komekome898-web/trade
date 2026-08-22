"""Dashboard aggregation over the runtime files."""
from __future__ import annotations

import json

import pytest

from bot.monitoring.aggregate import collect_status


def test_collect_status_empty_root(tmp_path):
    d = collect_status(tmp_path)
    assert d["components"]["main_bot"]["state"] == "missing"
    assert d["components"]["ws_recorder"]["state"] == "missing"
    assert d["scalp"]["trades"] == 0
    assert d["decisions"] == []


def test_collect_status_full(tmp_path):
    now = 1_000_000.0
    (tmp_path / "logs").mkdir()
    (tmp_path / "data").mkdir()
    (tmp_path / "logs" / "status.json").write_text(json.dumps({
        "mode": "paper", "last_price": 11000000, "balance_jpy": 200000,
        "daily_pnl_jpy": -50, "updated_at": now - 5}), encoding="utf-8")
    with open(tmp_path / "logs" / "bot.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({"event": "decision", "strategy_signal": "HOLD",
                            "decision": "HOLD", "timestamp": "2026-08-20T05:00:00"}) + "\n")
    with open(tmp_path / "data" / "scalp_paper.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({"ts": now - 60, "event": "entry", "side": "LONG",
                            "price": 1.0}) + "\n")
        f.write(json.dumps({"ts": now - 30, "event": "exit", "side": "LONG",
                            "price": 1.0, "pnl_jpy": 12.5}) + "\n")

    d = collect_status(tmp_path, now=now)
    assert d["components"]["main_bot"]["state"] == "ok"
    assert d["bot"]["last_price"] == 11000000
    assert d["scalp"]["trades"] == 1
    assert d["scalp"]["total_pnl_jpy"] == 12.5
    assert d["decisions"][0]["strategy_signal"] == "HOLD"


def test_overlay_and_active_modules_surfaced(tmp_path):
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "status.json").write_text(json.dumps({
        "mode": "paper", "updated_at": 1_000_000.0,
        "overlay": {"factor": 0.5, "consecutive_losses": 3, "dd_pct": 6.2},
        "active_modules": []}), encoding="utf-8")
    d = collect_status(tmp_path, now=1_000_000.0)
    assert d["overlay"] == {"factor": 0.5, "consecutive_losses": 3, "dd_pct": 6.2}
    assert d["active_modules"] == []


def _dashboard_module(offline: bool = True):
    """scripts/dashboard.py, loaded by path (scripts/ is not a package).

    Loaded ``offline`` by default: the two public bitFlyer reads are replaced
    by stubs so no test ever opens a socket. Tests that exercise the fetchers
    pass offline=False and monkeypatch the session instead.
    """
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scripts" / "dashboard.py"
    spec = importlib.util.spec_from_file_location("dashboard_module", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if offline:
        module.fetch_board = lambda now=None: None
        module.fetch_executions = lambda now=None: []
    return module


def _dashboard_page() -> str:
    return _dashboard_module().PAGE


def test_page_renders_the_overlay_and_active_modules_it_is_served(tmp_path):
    """The page must consume the keys collect_status publishes — telemetry that
    is written and never displayed is not visible to an operator. Checked
    against a real collect_status payload rather than a hand-written key list."""
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "status.json").write_text(json.dumps({
        "mode": "paper", "updated_at": 1_000_000.0,
        "overlay": {"factor": 0.25, "consecutive_losses": 4, "dd_pct": 7.1},
        "active_modules": ["radar_window"]}), encoding="utf-8")
    d = collect_status(tmp_path, now=1_000_000.0)
    page = _dashboard_page()

    assert "overlayTile(d.overlay)" in page          # tile is rendered
    assert "setModules(d.active_modules)" in page    # modules pill is rendered
    for field in d["overlay"]:                       # every field is shown
        assert f"ov.{field}" in page
    # null (no overlay / no module framework) is hidden, not shown as x1.00
    assert "if (ov == null) return \"\";" in page
    assert "if (mods == null) { el.style.display = \"none\"; return; }" in page


def test_overlay_absent_for_a_strategy_without_one(tmp_path):
    """None means 'no overlay / no module framework in this strategy', which
    is not the same as an overlay sitting at full size."""
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "status.json").write_text(json.dumps({
        "mode": "paper", "updated_at": 1_000_000.0}), encoding="utf-8")
    d = collect_status(tmp_path, now=1_000_000.0)
    assert d["overlay"] is None and d["active_modules"] is None


def test_status_write_survives_windows_permission_error(tmp_path, monkeypatch):
    """A dashboard reader holding status.json open must never crash the bot
    (Windows os.replace raises PermissionError then)."""
    import bot.atomic_file as atomic
    from bot.monitoring.status import StatusWriter

    w = StatusWriter(tmp_path / "status.json", clock=lambda: 123.0)
    monkeypatch.setattr(atomic.time, "sleep", lambda s: None)
    monkeypatch.setattr(atomic.os, "replace",
                        lambda src, dst: (_ for _ in ()).throw(PermissionError(5)))
    w.write()  # must not raise
    assert json.loads((tmp_path / "status.json").read_text(encoding="utf-8"))[
        "updated_at"] == 123.0  # fell back to the direct write
    assert not (tmp_path / "status.tmp").exists()   # and left no temp file


def test_kill_switch_reflected(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "kill_switch.json").write_text(
        json.dumps({"reason": "manual", "detail": "test"}), encoding="utf-8")
    d = collect_status(tmp_path)
    assert d["components"]["main_bot"]["state"] == "killed"
    assert d["kill_switch"]["reason"] == "manual"


# ---- storm radar + OI snapshot ---------------------------------------------
def test_radar_state_in_status(tmp_path):
    """The radar window (research_storm_b.py G3, 12:30-15:00 UTC) is surfaced
    for the header pill; 13:00 UTC is inside it, 03:00 UTC is not."""
    from datetime import datetime, timezone

    def utc(h, m=0):
        return datetime(2026, 8, 20, h, m, tzinfo=timezone.utc).timestamp()

    armed = collect_status(tmp_path, now=utc(13))["radar"]
    assert armed["armed"] is True
    assert armed["window"] == "12:30-15:00 UTC"
    assert collect_status(tmp_path, now=utc(3))["radar"]["armed"] is False


def test_oi_snapshot_missing(tmp_path):
    assert collect_status(tmp_path)["oi_snapshot"] is None


def test_oi_snapshot_last_row(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "oi_snapshots.csv").write_text(
        "ts_utc,okx_usdt_oi,okx_usd_oi,okx_ls_ratio,dvol,deribit_oi\n"
        "2026-08-20T11:00:00+00:00,1.0,2.0,,38.25,3.0\n"
        "2026-08-20T12:00:00+00:00,10.0,20.0,1.13,39.5,30.0\n", encoding="utf-8")
    row_ts = 1787227200.0  # 2026-08-20T12:00:00+00:00
    oi = collect_status(tmp_path, now=row_ts + 600)["oi_snapshot"]
    assert oi["last"]["dvol"] == "39.5"
    assert oi["last"]["okx_ls_ratio"] == "1.13"
    assert oi["row_age_sec"] == 600.0


def test_oi_snapshot_header_only_file(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "oi_snapshots.csv").write_text(
        "ts_utc,okx_usdt_oi,okx_usd_oi,okx_ls_ratio,dvol,deribit_oi\n",
        encoding="utf-8")
    oi = collect_status(tmp_path)["oi_snapshot"]
    assert oi is not None and oi["last"] is None and oi["row_age_sec"] is None


def test_status_payload_is_json_serialisable(tmp_path):
    json.dumps(collect_status(tmp_path))


# ---- 最近の判断: JST times, Japanese reasons, fills and realized P&L --------
def _decision(ts: str, signal: str, decision: str, reason: str, pnl=None,
              **extra) -> dict:
    rec = {"event": "decision", "timestamp": ts, "strategy_signal": signal,
           "decision": decision, "reason": reason, "PnL": pnl}
    rec.update(extra)
    return rec


def _write_log(root, records) -> None:
    (root / "logs").mkdir(exist_ok=True)
    with open(root / "logs" / "bot.jsonl", "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


PAIRED_LOG = [
    _decision("2026-08-20T04:59:00+00:00", "HOLD", "HOLD", "leader data gap", 0.0),
    _decision("2026-08-20T05:00:00+00:00", "BUY", "ORDER_SENT",
              "leader +0.42% over 5 bars", 0.0, execution_price=11_000_000.0,
              order_size=0.01, execution_status="FILLED"),
    _decision("2026-08-20T05:10:00+00:00", "CLOSE", "ORDER_SENT",
              "leader momentum faded (0.01%)", 1234.5,
              execution_price=11_123_456.0, order_size=0.01,
              execution_status="FILLED"),
    _decision("2026-08-20T05:20:00+00:00", "SELL", "ORDER_SENT",
              "leader -0.51% over 5 bars", 1234.5, execution_price=11_100_000.0,
              order_size=0.01, execution_status="FILLED"),
    _decision("2026-08-20T05:30:00+00:00", "BUY", "ORDER_SENT",
              "leader +0.30% over 5 bars", 900.5, execution_price=11_150_000.0,
              order_size=0.01, execution_status="FILLED"),
    _decision("2026-08-20T05:31:00+00:00", "HOLD", "REJECTED",
              "BUY entry vetoed by module long_only", 900.5),
]


def test_decision_times_are_jst(tmp_path):
    """The bot stamps UTC; the owner reads JST. 05:00Z is 14:00 JST, and the
    format is MM/DD HH:MM:SS so a date rollover is visible."""
    _write_log(tmp_path, PAIRED_LOG)
    rows = {r["timestamp"]: r for r in collect_status(tmp_path)["decisions"]}
    assert rows["2026-08-20T05:00:00+00:00"]["time_jst"] == "08/20 14:00:00"
    # 16:30 UTC is already the next day in JST
    _write_log(tmp_path, [_decision("2026-08-20T16:30:05+00:00", "HOLD", "HOLD",
                                    "no cross")])
    assert collect_status(tmp_path)["decisions"][0]["time_jst"] == "08/21 01:30:05"


@pytest.mark.parametrize("raw,japanese", [
    # every strategy
    ("insufficient history", "履歴不足"),
    ("indicators warming up", "指標の準備中"),
    # xborder_momentum (the champion under validation)
    ("no leader data column", "先行データ列なし"),
    ("leader data gap", "先行データ欠落"),
    ("leader +0.42% over 5 bars", "先行 +0.42% / 5本"),
    ("leader -0.51% over 5 bars", "先行 -0.51% / 5本"),
    ("leader momentum faded (0.01%)", "先行モメンタム減衰 (0.01%)"),
    ("between exit band and threshold", "手仕舞い帯と閾値の間"),
    # older wordings that are still in the log tail the console reads
    ("below threshold", "閾値未満"),
    ("leader momentum -0.06% <= exit", "先行モメンタム -0.06% ≤ 手仕舞い帯"),
    # bot/main.py protective stop
    ("protective stop: unrealized -2.10%", "保護ストップ(含み -2.10%)"),
    # bot/strategy/composite.py module veto
    ("BUY entry vetoed by module long_only", "新規BUYをモジュール long_only が拒否"),
    ("SELL entry vetoed by module radar_window",
     "新規SELLをモジュール radar_window が拒否"),
    # ema_cross / breakout / inago / range_fade / rsi / wick
    ("EMA fast crossed above slow", "EMA 上抜け"),
    ("EMA fast crossed below slow", "EMA 下抜け"),
    ("no cross", "クロスなし"),
    ("volatility too low (0.031%)", "ボラ不足 (0.031%)"),
    ("inside channel", "チャネル内"),
    ("close 11000000 broke above 20-bar high 10950000", "20本高値 10950000 を上抜け"),
    ("close 10900000 broke below 20-bar low 10950000", "20本安値 10950000 を下抜け"),
    ("no order-flow columns", "オーダーフロー列なし"),
    ("no volume surge", "出来高の急増なし"),
    ("buy surge x3.2", "買い急増 x3.2"),
    ("sell surge x2.8", "売り急増 x2.8"),
    ("surge without direction", "急増(方向なし)"),
    ("regime not calm — stand aside", "静穏でない — 待機"),
    ("degenerate range", "レンジ幅なし"),
    ("at range bottom (0.08)", "レンジ下限 (0.08)"),
    ("at range top (0.94)", "レンジ上限 (0.94)"),
    ("back at range middle", "レンジ中央に回帰"),
    ("inside range", "レンジ内"),
    ("RSI oversold (24.1) in non-down trend", "RSI 売られすぎ (24.1)"),
    ("RSI overbought (78.9)", "RSI 買われすぎ (78.9)"),
    ("RSI neutral", "RSI 中立"),
    ("lower wick 0.42% rejected", "下ヒゲ 0.42% を否定"),
    ("upper wick 0.51% rejected", "上ヒゲ 0.51% を否定"),
    # bot/main.py suppression events
    ("risk_overlay", "リスクオーバーレイ"),
    ("budget_below_min", "発注額が最小単位未満"),
    ("exchange_stopped", "取引所が停止中"),
    ("exchange_condition", "取引所コンディション悪化"),
    ("exchange_degraded", "取引所の応答が劣化"),
])
def test_reason_strings_map_to_japanese(raw, japanese):
    from bot.monitoring.decision_text import reason_ja

    assert reason_ja(raw) == japanese


def test_every_literal_strategy_reason_has_a_japanese_label():
    """Read out of the strategy sources, not a hand-kept list: a new HOLD
    reason added tomorrow shows up here as an unmapped English string in the
    console, and this is what says so. Only the literal reasons are checked —
    the f-string ones carry numbers and are covered by the parametrised cases
    above."""
    import ast
    import pathlib

    from bot.monitoring.decision_text import reason_ja

    unmapped = []
    for path in sorted((pathlib.Path(__file__).resolve().parents[1] / "src" /
                        "bot" / "strategy").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call)
                    and getattr(node.func, "id", "") == "Signal"
                    and len(node.args) >= 2):
                continue
            arg = node.args[1]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if reason_ja(arg.value) == arg.value:
                    unmapped.append(f"{path.name}: {arg.value}")
    assert not unmapped, unmapped


def test_unknown_reason_passes_through_raw():
    """A strategy swapped in tomorrow logs reasons nobody has mapped. A
    wrong-but-Japanese label would be worse than the English original."""
    from bot.monitoring.decision_text import decision_ja, reason_ja, signal_ja

    assert reason_ja("some brand new reason") == "some brand new reason"
    assert reason_ja("") == "" and reason_ja(None) == ""
    assert decision_ja("SOMETHING_ELSE") == "SOMETHING_ELSE"
    assert signal_ja("STOP_LOSS") == "損切り"
    assert decision_ja("ORDER_SENT") == "発注" and decision_ja("HOLD") == "様子見"


def test_entry_and_exit_rows_carry_the_fill_price_and_realized_pnl(tmp_path):
    """The pairing is positional (a BUY on top of a short is an EXIT) and the
    log's PnL field is CUMULATIVE, so an exit's own P&L is the step in it.
    Both facts need the whole log — the page cannot derive either from a row."""
    _write_log(tmp_path, PAIRED_LOG)
    rows = {r["timestamp"]: r for r in collect_status(tmp_path)["decisions"]}

    entry = rows["2026-08-20T05:00:00+00:00"]
    assert entry["trade_kind"] == "entry" and entry["trade_side"] == "LONG"
    assert entry["fill_price"] == 11_000_000.0
    assert entry["realized_pnl_jpy"] is None      # an entry realizes nothing

    exit_row = rows["2026-08-20T05:10:00+00:00"]
    assert exit_row["trade_kind"] == "exit" and exit_row["trade_side"] == "LONG"
    assert exit_row["fill_price"] == 11_123_456.0
    assert exit_row["realized_pnl_jpy"] == 1234.5

    # the SELL is an ENTRY (the book was flat), not a close of the long above
    short = rows["2026-08-20T05:20:00+00:00"]
    assert short["trade_kind"] == "entry" and short["trade_side"] == "SHORT"
    # and the BUY that follows CLOSES it, at a loss: 900.5 - 1234.5
    close = rows["2026-08-20T05:30:00+00:00"]
    assert close["trade_kind"] == "exit" and close["trade_side"] == "SHORT"
    assert close["realized_pnl_jpy"] == -334.0

    # a row that sent no order is labelled but carries no trade numbers
    refused = rows["2026-08-20T05:31:00+00:00"]
    assert refused["trade_kind"] is None
    assert refused["fill_price"] is None and refused["realized_pnl_jpy"] is None
    assert refused["decision_ja"] == "発注却下"


def test_decision_enrichment_reuses_the_one_pairing_implementation(tmp_path):
    """market_view.parse_bot_events is the repo's single pairing rule (chart
    markers, gate judge, this table). A second one would eventually disagree
    with the chart about what an order did."""
    from bot.monitoring.market_view import parse_bot_events

    _write_log(tmp_path, PAIRED_LOG)
    events = parse_bot_events(tmp_path / "logs" / "bot.jsonl")
    priced = [(r["fill_price"], r["realized_pnl_jpy"])
              for r in reversed(collect_status(tmp_path)["decisions"])
              if r["trade_kind"]]
    assert priced == [(e["price"], e["pnl"] if e["kind"] == "exit" else None)
                      for e in events]


# ---- 判定ゲート: progress against the pre-registered bars -------------------
def _gates(payload) -> dict:
    return {g["key"]: g for g in payload["gates"]}


def test_gate_bars_come_from_the_judge(tmp_path):
    """The console's 必要量 and judge_gates' PASS bar have to be one number."""
    import sys

    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve()
                          .parents[1] / "scripts"))
    import judge_gates as jg
    from bot.monitoring import gates as g

    assert jg.MAIN_TRADES_BAR is g.MAIN_TRADES_BAR == 30
    assert jg.OI_ROWS_BAR is g.OI_ROWS_BAR == 2900
    assert jg.BOARD_DAYS_BAR is g.BOARD_DAYS_BAR == 7.0
    assert jg.BOARD_BYTES_BAR is g.BOARD_BYTES_BAR == 500_000_000
    assert jg.FUNDING_N_BAR is g.FUNDING_N_BAR == 63

    needs = {k: v["need"] for k, v in _gates(collect_status(tmp_path)).items()}
    assert needs == {"champion": 30.0, "oi": 2900.0, "board": 7.0,
                     "funding": 63.0}


def test_champion_gate_counts_closed_round_trips_not_fills(tmp_path):
    """status.json's trade_count is FILLS (an entry and its exit are two); §5
    counts trades. PAIRED_LOG holds two closed round trips."""
    _write_log(tmp_path, PAIRED_LOG)
    champ = _gates(collect_status(tmp_path))["champion"]
    assert champ["have"] == 2.0 and champ["need"] == 30.0
    assert champ["unit"] == "trades" and champ["done"] is False


def test_champion_gate_matches_judge_gates_beyond_market_views_4mb_tail(tmp_path):
    """market_view (the decisions table / chart markers) only ever reads a
    4 MB tail of logs/bot.jsonl. The champion GATE must not inherit that limit
    — a round trip old enough to sit beyond the tail still has to be counted,
    exactly as scripts/judge_gates.py counts it from the whole file."""
    import sys
    from pathlib import Path as _P

    old_trade = [
        _decision("2020-01-01T00:00:00+00:00", "BUY", "ORDER_SENT",
                  "old entry", 0.0, execution_price=1_000_000.0,
                  order_size=0.01, execution_status="FILLED"),
        _decision("2020-01-01T00:10:00+00:00", "CLOSE", "ORDER_SENT",
                  "old exit", 100.0, execution_price=1_001_000.0,
                  order_size=0.01, execution_status="FILLED"),
    ]
    # >4 MB of HOLD filler so the round trip above sits well outside
    # market_view.LOG_TAIL_BYTES (4 MB) once the file is read from the end.
    filler = [_decision(f"2020-06-{1 + i % 28:02d}T00:00:00+00:00", "HOLD",
                        "HOLD", "x" * 2000) for i in range(2600)]
    _write_log(tmp_path, old_trade + filler + PAIRED_LOG)
    log_path = tmp_path / "logs" / "bot.jsonl"
    assert log_path.stat().st_size > 4 * 1024 * 1024   # the scenario is real

    console_have = _gates(collect_status(tmp_path))["champion"]["have"]

    sys.path.insert(0, str(_P(__file__).resolve().parents[1] / "scripts"))
    import judge_gates as jg
    trades, _meta = jg.load_champion_trades(tmp_path)
    assert console_have == len(trades)
    # the old round trip (1) + PAIRED_LOG's two (2) = 3; proves it was not
    # silently dropped by a tail read
    assert console_have == 3.0


def test_progress_eta_is_measured_from_the_observed_rate():
    """A known rate gives a known ETA: 10 rows in 10 days is 1 row/day, so the
    remaining 20 of a 30-row bar are 20 days away."""
    from bot.monitoring.gates import DAY_SEC, progress

    now = 1_800_000_000.0
    p = progress("t", "t", have=10, need=30, unit="rows",
                 first_ts=now - 10 * DAY_SEC, now=now, bar="x")
    assert p["rate_per_day"] == 1.0
    assert p["eta_sec"] == pytest.approx(20 * DAY_SEC)
    assert p["pct"] == pytest.approx(33.3) and p["done"] is False


def test_progress_eta_is_unknown_rather_than_optimistic():
    """No rate — nothing collected yet, or the collector never ran — is None,
    which the page renders as 「—」. A guess here would be read as a promise."""
    from bot.monitoring.gates import DAY_SEC, progress

    now = 1_800_000_000.0
    assert progress("t", "t", have=0, need=30, unit="rows",
                    first_ts=now - 10 * DAY_SEC, now=now, bar="x")["eta_sec"] is None
    assert progress("t", "t", have=5, need=30, unit="rows",
                    first_ts=None, now=now, bar="x")["eta_sec"] is None
    # a full sample is 0 seconds away, not None
    done = progress("t", "t", have=30, need=30, unit="rows",
                    first_ts=now - DAY_SEC, now=now, bar="x")
    assert done["eta_sec"] == 0.0 and done["done"] is True and done["pct"] == 100.0


def test_board_gate_waits_for_the_later_of_its_two_bars(tmp_path):
    """data/ws must reach BOTH 7 days and ~0.5 GB (§4 reports f, g). At 1 MB a
    day the byte bar is centuries out and it is the byte bar that decides."""
    import os
    from datetime import datetime, timezone

    from bot.monitoring.gates import DAY_SEC, board_gate, clear_cache

    clear_cache()
    ws = tmp_path / "data" / "ws"
    ws.mkdir(parents=True)
    now = 1_800_000_000.0
    for day in range(3):
        # the span is read off the STAMPED start in the filename (first file)
        # and the last file's mtime, exactly as judge_gates measures it
        start = now - (3 - day) * DAY_SEC
        stamp = datetime.fromtimestamp(start, tz=timezone.utc).strftime(
            "%Y%m%d_%H%M%S")
        f = ws / f"board_{stamp}.jsonl.gz"
        f.write_bytes(b"x" * 1_000_000)
        os.utime(f, (start, start + DAY_SEC))
    g = board_gate(tmp_path, now)
    assert g["unit"] == "days" and g["need"] == 7.0
    assert g["have"] == pytest.approx(3.0, abs=0.01)
    # days alone would be ~4 more days; the 0.5 GB bar dominates
    assert g["eta_sec"] > 100 * DAY_SEC
    assert "3.0 MB / 3ファイル" in g["detail"]


def test_board_gate_done_and_pct_fold_both_bars(tmp_path):
    """8 days clears BOARD_DAYS_BAR (7) alone, but 8 MB of recordings is
    nowhere near BOARD_BYTES_BAR (~0.5 GB) — the row must stay NOT done, and
    its pct must reflect the bar that is actually behind (~1.6%), not the
    days bar that already reads 100%."""
    import os
    from datetime import datetime, timezone

    from bot.monitoring.gates import DAY_SEC, board_gate, clear_cache

    clear_cache()
    ws = tmp_path / "data" / "ws"
    ws.mkdir(parents=True)
    now = 1_800_000_000.0
    for day in range(8):
        start = now - (8 - day) * DAY_SEC
        stamp = datetime.fromtimestamp(start, tz=timezone.utc).strftime(
            "%Y%m%d_%H%M%S")
        f = ws / f"board_{stamp}.jsonl.gz"
        f.write_bytes(b"x" * 1_000_000)          # 1 MB/day -> 8 MB total
        os.utime(f, (start, start + DAY_SEC))
    g = board_gate(tmp_path, now)
    assert g["have"] >= 7.0                      # the DAYS bar alone is met
    assert g["done"] is False                    # the BYTES bar is not
    assert g["pct"] == pytest.approx(1.6, abs=0.2)


def test_oi_and_funding_gates_read_the_real_files(tmp_path):
    from datetime import datetime, timedelta, timezone

    from bot.monitoring.gates import DAY_SEC, clear_cache

    clear_cache()
    (tmp_path / "data").mkdir()
    start = datetime(2026, 7, 1, tzinfo=timezone.utc)
    rows = ["ts_utc,okx_usdt_oi,okx_usd_oi,okx_ls_ratio,dvol,deribit_oi"]
    for i in range(96 * 10):                       # 10 days at 15 min
        rows.append((start + timedelta(minutes=15 * i)).isoformat() +
                    ",1.0,2.0,1.1,38.0,3.0")
    (tmp_path / "data" / "oi_snapshots.csv").write_text("\n".join(rows) + "\n",
                                                        encoding="utf-8")
    candles = ["ts,open,high,low,close,volume"]
    for day in range(4):                           # 4 settlement days covered
        for minute in (0, 30):
            ts = start + timedelta(days=day, hours=13, minutes=minute)
            candles.append(f"{ts.isoformat()},1,1,1,1,1")
    (tmp_path / "data" / "candles_FX_BTC_JPY.csv").write_text(
        "\n".join(candles) + "\n", encoding="utf-8")

    now = (start + timedelta(days=10)).timestamp()
    gates = _gates(collect_status(tmp_path, now=now))
    oi = gates["oi"]
    assert oi["have"] == 960.0 and oi["need"] == 2900.0
    assert oi["rate_per_day"] == pytest.approx(96.0, rel=0.02)
    assert oi["eta_sec"] == pytest.approx((2900 - 960) / 96 * DAY_SEC, rel=0.02)
    funding = gates["funding"]
    assert funding["have"] == 4.0 and funding["need"] == 63.0
    assert funding["unit"] == "days"


def test_gate_file_scans_are_memoised_on_mtime_and_size(tmp_path, monkeypatch):
    """The console polls every 5s and the candle file has tens of thousands of
    rows; re-reading it per poll to draw one progress bar is not affordable."""
    from bot.monitoring import gates as g

    g.clear_cache()
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "oi_snapshots.csv").write_text(
        "ts_utc,dvol\n2026-07-01T00:00:00+00:00,38.0\n", encoding="utf-8")
    calls = []
    real = g.csv_first_last_ts
    monkeypatch.setattr(g, "csv_first_last_ts",
                        lambda p, column="ts_utc": calls.append(p) or real(p, column))
    now = 1_800_000_000.0
    for _ in range(5):
        g.oi_gate(tmp_path, now)
    assert len(calls) == 1


# ---- マーケットタブ ---------------------------------------------------------
def _serve(tmp_path, monkeypatch):
    """The real handler on a throwaway localhost port, rooted at tmp_path so
    the endpoints answer over an empty workspace instead of the live data/."""
    import threading
    from http.server import ThreadingHTTPServer

    monkeypatch.chdir(tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _dashboard_module().Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _get(port, path):
    import urllib.request

    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=10) as r:
        return r.status, r.headers.get("Content-Type"), r.read()


def test_api_market_endpoint_serves_the_market_payload(tmp_path, monkeypatch):
    server, thread = _serve(tmp_path, monkeypatch)
    try:
        port = server.server_address[1]
        status, ctype, body = _get(port, "/api/market")
        assert status == 200 and ctype == "application/json"
        d = json.loads(body)
        # empty workspace: every section degrades instead of erroring
        assert d["state"] is None and d["chart"] is None and d["oi"] is None
        assert [t["tf"] for t in d["timeframes"]] == ["1m", "15m", "1h", "4h", "1d"]

        assert _get(port, "/api/status")[0] == 200
        assert "マーケット" in _get(port, "/")[2].decode("utf-8")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_api_market_is_cached_until_a_file_changes(tmp_path, monkeypatch):
    """collect_market re-parses every candle row; a 30s poll per open tab must
    not pay for that when nothing on disk moved."""
    from tests.test_market_view import _make_workspace

    _make_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    module = _dashboard_module()
    calls = []
    monkeypatch.setattr(module, "collect_market",
                        lambda root, live_bars=(): calls.append(root) or {"n": len(calls)})

    first = module.market_body(".", now=1000.0)
    assert json.loads(first)["n"] == 1
    assert module.market_body(".", now=1005.0) == first    # inside the TTL
    assert module.market_body(".", now=1100.0) == first    # TTL over, files same
    assert len(calls) == 1

    (tmp_path / "logs" / "bot.jsonl").write_text(
        json.dumps({"event": "decision", "timestamp": "2026-08-20T00:31:00+00:00",
                    "strategy_signal": "HOLD", "decision": "HOLD",
                    "PnL": 0.0}) + "\n", encoding="utf-8")
    assert json.loads(module.market_body(".", now=1200.0))["n"] == 2
    assert len(calls) == 2


def test_market_cache_ttl_fits_inside_the_fast_poll(tmp_path, monkeypatch):
    """A 15s TTL under a 10s poll served the 1m view a payload the TTL refused
    to rebuild on every other tick. And the tape is fetched only where it can
    change the answer: a TTL-fresh request spends no /v1/executions call."""
    import re

    from tests.test_market_view import _make_workspace

    _make_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    module = _dashboard_module()
    fast_sec = int(re.search(r"FAST_POLL_MS = (\d+)", module.PAGE).group(1)) / 1000.0
    assert module.MARKET_TTL <= fast_sec

    builds, tapes = [], []
    monkeypatch.setattr(module, "collect_market",
                        lambda root, live_bars=(): builds.append(root) or
                        {"n": len(builds)})
    monkeypatch.setattr(module, "live_bars", lambda now=None: tapes.append(1) or [])

    assert json.loads(module.market_body(".", now=1000.0))["n"] == 1
    assert len(tapes) == 1
    module.market_body(".", now=1000.0 + module.MARKET_TTL - 0.1)
    assert len(tapes) == 1               # inside the TTL: the fetch is skipped
    module.market_body(".", now=1000.0 + fast_sec)
    assert len(tapes) == 2               # the next 1m poll does look at the tape
    assert len(builds) == 1              # files and tail unchanged: no rebuild


def test_page_has_both_tabs_and_switches_without_reloading(tmp_path):
    page = _dashboard_page()
    assert 'onclick="showTab(\'console\')"' in page and "Botコンソール" in page
    assert 'onclick="showTab(\'market\')"' in page and "マーケット" in page
    assert 'id="view-console"' in page and 'id="view-market"' in page
    # market data is fetched on show and refreshed while the tab is visible —
    # every 10s on the 1m scalp view, every 30s on the slower frames
    assert "setInterval(refreshMarket, marketPollMs())" in page
    assert "FAST_POLL_MS = 10000, SLOW_POLL_MS = 30000" in page
    assert 'chartTf === FAST_TF ? FAST_POLL_MS : SLOW_POLL_MS' in page
    assert 'clearInterval(marketTimer)' in page
    assert '"/api/market"' in page


def test_page_renders_the_market_keys_it_is_served(tmp_path):
    """Checked against a real collect_market payload, not a hand-written list —
    a field that is computed and never displayed is invisible to the owner."""
    from bot.monitoring.market_view import collect_market

    d = collect_market(tmp_path)
    page = _dashboard_page()
    for key in d:
        assert (f"d.{key}" in page or f"marketData.{key}" in page
                or f'"{key}"' in page), key
    for tf in d["timeframes"]:
        assert f'>{tf["label"]}<' in page or "t.label" in page
    # the three state pills and the 1m-approximation label are all reachable
    for state in ("嵐", "ブレイク", "静穏レンジ", "通常"):
        assert state in page
    assert "s.approx" in page


def test_tile_values_are_pinned_to_one_line_in_the_css():
    """Runs without node: the no-wrap rule is CSS, not arithmetic, and the
    auto-shrink constants have to agree with the grid's own minimum width."""
    import re

    page = _dashboard_page()
    css = re.search(r"\.tile \.v \{(.*?)\}", page, re.S).group(1)
    assert "white-space: nowrap" in css
    assert "overflow: hidden" in css and "text-overflow: ellipsis" in css
    # TILE_W is the narrowest tile's CONTENT box: the grid minimum less the
    # 14px padding on each side. Widening one without the other silently
    # over- or under-shrinks every value.
    minmax = int(re.search(r"minmax\((\d+)px, 1fr\)", page).group(1))
    tile_w = int(re.search(r"const TILE_W = (\d+)", page).group(1))
    pad = int(re.search(r"\.tile \{[^}]*padding: 12px (\d+)px", page, re.S).group(1))
    assert tile_w == minmax - 2 * pad
    # the .sub run inside a value is sized relative to it, so one font-size
    # attribute governs the whole line
    assert ".tile .v .sub { font-size: .55em; }" in page
    assert "const TILE_W = 140, TILE_CH = 0.6, TILE_SUB = 0.55;" in page


def _node() -> str | None:
    import shutil

    return shutil.which("node")


# ---- Botコンソール tab, rendered headlessly ---------------------------------
CONSOLE_HARNESS = r"""
// DOM-less harness for the CONSOLE tab: refresh() is driven with a stubbed
// fetch that answers one /api/status payload, then the built markup is
// reported. The tile fonts are reported as numbers, not as markup, because
// "the value never wraps" is an assertion about a WIDTH.
const fs = require("fs");
const src = fs.readFileSync(process.argv[2], "utf8");
const data = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));

function El(id) {
  this.id = id; this.innerHTML = ""; this.textContent = "";
  this.className = ""; this.hidden = false; this.style = {}; this.events = {};
}
El.prototype.addEventListener = function (k, f) { this.events[k] = f; };
El.prototype.getBoundingClientRect = () => ({left: 0, top: 0, width: 800, height: 420});
El.prototype.scrollIntoView = function () { this.scrolled = true; };

const els = {};
const document = {getElementById: id => (els[id] = els[id] || new El(id))};
const canvas = document.getElementById("m-chart");
canvas.getContext = () => null;
canvas.parentElement = {clientWidth: 800};
const window = {devicePixelRatio: 1, addEventListener() {}};

const api = new Function(
  "document", "window", "fetch", "setInterval", "clearInterval", "navigator",
  src + "\nreturn {refresh, tileFont, eta, TILE_W, TILE_CH, TILE_SUB, TILE_MAX, TILE_MIN};"
)(document, window,
  () => Promise.resolve({json: () => Promise.resolve(data)}),
  () => 7, () => 0, {});

// The longest values the console can realistically hold, as (value, sub) —
// exactly what tile() is called with in refresh().
const PROBES = [
  ["PAPER", ""],
  ["12,345,678", ""],
  ["1,234,567 円", ""],
  ["-123,456.7 円", ""],
  ["LONG 0.013", "@ 11,234,567"],
  ["SHORT 0.1234", "@ 12,345,678"],
  ["CRITICAL ⚠️停止中の記録", "p95 12,345ms / NORMAL"],
  ["x0.25", "連敗 4 / DD 12.34%"],
];
const width = (v, sub) => api.TILE_CH * api.tileFont(v, sub) *
  (v.length + (sub ? api.TILE_SUB * (sub.length + 1) : 0));

api.refresh().then(() => {
  const tiles = els["tiles"].innerHTML;
  const fonts = [];
  const re = /<div class="v mono[^"]*" style="font-size:([\d.]+)px"/g;
  let m;
  while ((m = re.exec(tiles)) !== null) fonts.push(Number(m[1]));
  console.log(JSON.stringify({
    tiles: tiles,
    tile_count: (tiles.match(/class="tile"/g) || []).length,
    tile_fonts: fonts,
    probe_fonts: PROBES.map(p => api.tileFont(p[0], p[1])),
    probe_widths: PROBES.map(p => width(p[0], p[1])),
    tile_w: api.TILE_W, tile_max: api.TILE_MAX, tile_min: api.TILE_MIN,
    decisions: els["t-dec"].innerHTML,
    collectors: els["t-col"].innerHTML,
    gates: els["gates"].innerHTML,
    banner: els["banner"].textContent,
    updated: els["updated"].textContent,
    eta_samples: [api.eta(null), api.eta(0), api.eta(3600), api.eta(86400 * 20),
                  api.eta(86400 * 400)],
  }));
}).catch(e => { console.error(e && e.stack || String(e)); process.exit(3); });
"""


def _render_console_in_node(tmp_path, payload) -> dict:
    """Execute the page's own JS against a /api/status payload."""
    import re
    import subprocess

    js = re.search(r"<script>(.*)</script>", _dashboard_page(), re.S).group(1)
    (tmp_path / "page.js").write_text(js, encoding="utf-8")
    (tmp_path / "console_harness.js").write_text(CONSOLE_HARNESS, encoding="utf-8")
    (tmp_path / "status.json").write_text(json.dumps(payload), encoding="utf-8")
    node = _node()
    subprocess.run([node, "--check", str(tmp_path / "page.js")], check=True)
    out = subprocess.run(
        [node, str(tmp_path / "console_harness.js"), str(tmp_path / "page.js"),
         str(tmp_path / "status.json")],
        check=True, capture_output=True, text=True)
    return json.loads(out.stdout)


def _console_workspace(root):
    """A workspace with a paired trade log, an open position, OI rows and a
    board recording — everything the console tab draws."""
    import os
    from datetime import datetime, timedelta, timezone

    from bot.monitoring.gates import DAY_SEC, clear_cache

    clear_cache()
    (root / "logs").mkdir(exist_ok=True)
    (root / "data").mkdir(exist_ok=True)
    _write_log(root, PAIRED_LOG)
    now = 1_800_000_000.0
    (root / "logs" / "status.json").write_text(json.dumps({
        "mode": "paper", "last_price": 12_345_678, "balance_jpy": 1_234_567,
        "daily_pnl_jpy": -123_456.7, "total_pnl_jpy": 234_567.8,
        "max_drawdown_pct": 12.34, "position_size": 0.013,
        "entry_price": 11_234_567.0, "trade_count": 4, "error_count": 0,
        "api_condition": "CRITICAL", "api_health_status": "NORMAL",
        "overlay": {"factor": 0.25, "consecutive_losses": 4, "dd_pct": 12.34},
        "active_modules": [], "updated_at": now - 5}), encoding="utf-8")
    start = datetime(2026, 7, 1, tzinfo=timezone.utc)
    rows = ["ts_utc,okx_usdt_oi,okx_usd_oi,okx_ls_ratio,dvol,deribit_oi"]
    for i in range(96 * 5):
        rows.append((start + timedelta(minutes=15 * i)).isoformat() +
                    ",120000,2.0,1.13,38.25,3.0")
    (root / "data" / "oi_snapshots.csv").write_text("\n".join(rows) + "\n",
                                                    encoding="utf-8")
    ws = root / "data" / "ws"
    ws.mkdir()
    for day in range(2):
        s = now - (2 - day) * DAY_SEC
        stamp = datetime.fromtimestamp(s, tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        f = ws / f"board_{stamp}.jsonl.gz"
        f.write_bytes(b"x" * 2_000_000)
        os.utime(f, (s, s + DAY_SEC))
    for label, rel in [("bitFlyer candles", "data/candles_FX_BTC_JPY.csv"),
                       ("Binance 1m", "data/binance_BTCUSDT_1m.csv")]:
        (root / rel).write_text("ts,open,high,low,close,volume\n", encoding="utf-8")
    return now


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_console_tiles_never_wrap_to_a_second_line(tmp_path):
    """A 小窓 that wraps pushes the whole tile row out of alignment. The value
    is one line by CSS and the font is stepped down to the string's own length,
    so the longest realistic values still fit the narrowest (168px) tile."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    now = _console_workspace(workspace)
    r = _render_console_in_node(tmp_path,
                                collect_status(workspace, now=now))
    page = _dashboard_page()

    # the CSS says it outright, whatever the font arithmetic does
    assert "white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" in page
    # every rendered tile carries a computed size inside the allowed band
    assert r["tile_count"] >= 12 and len(r["tile_fonts"]) == r["tile_count"]
    for px in r["tile_fonts"]:
        assert r["tile_min"] <= px <= r["tile_max"]
    # and the longest values the console can hold still fit the box
    for value, px in zip(r["probe_widths"], r["probe_fonts"]):
        assert value <= r["tile_w"] + 0.01 or px == r["tile_min"]
    # short values are NOT shrunk — the tiles keep their headline size
    assert r["probe_fonts"][0] == r["tile_max"]


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_console_position_tile_shows_the_entry_price(tmp_path):
    """LONG 0.013 @ 11,234,567 — a size alone does not say whether the open
    position is winning, which is the first thing the owner looks for."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    now = _console_workspace(workspace)
    payload = collect_status(workspace, now=now)
    assert payload["bot"]["entry_price"] == 11_234_567.0

    r = _render_console_in_node(tmp_path, payload)
    assert "LONG 0.013" in r["tiles"]
    assert "@ 11,234,567" in r["tiles"]

    # flat is spelled out rather than shown as 0.0000
    payload["bot"]["position_size"] = 0.0
    payload["bot"]["entry_price"] = None
    flat = _render_console_in_node(tmp_path, payload)
    assert "フラット" in flat["tiles"] and "@ " not in flat["tiles"]


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_console_decisions_table_is_jst_japanese_and_priced(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    now = _console_workspace(workspace)
    r = _render_console_in_node(tmp_path, collect_status(workspace, now=now))
    table = r["decisions"]

    assert "時刻 (JST)" in table and "08/20 14:00:00" in table
    assert "先行 +0.42% / 5本" in table          # reason in Japanese
    assert "発注却下" in table and "様子見" in table
    assert "11,123,456" in table                 # the exit's fill price
    assert "+1,234.5円" in table                 # realized, signed
    assert "-334円" in table or "-334.0円" in table
    # signed and coloured with the page's shared up/down semantics
    assert 'class="num mono up"' in table and 'class="num mono down"' in table


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_console_collectors_show_requirement_progress_and_eta(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    now = _console_workspace(workspace)
    payload = collect_status(workspace, now=now)
    r = _render_console_in_node(tmp_path, payload)
    table, strip = r["collectors"], r["gates"]

    for header in ("必要量", "進捗", "残り時間"):
        assert header in table
    # every gate is a row with its bar, its n/required and a progress bar
    for gate in payload["gates"]:
        assert gate["label"] in table and gate["bar"] in table
        assert gate["label"] in strip                 # and a chip in the strip
    assert "480/2,900行" in table                     # OI rows
    assert "2/30回" in table                          # champion round trips
    assert "2/7日" in table                           # board days recorded
    assert "0/63日" in table                          # funding-window days
    assert table.count('class="prog') == len(payload["gates"])
    # the estimate is labelled as one, and an unknown rate is not guessed
    assert "≈" in table
    assert r["eta_samples"] == ["—", "達成", "≈1.0時間", "≈20.0日", "≈13.1ヶ月"]
    # the plain collectors keep their row and simply have no bar
    assert "bitFlyer candles" in table and "Binance 1m" in table


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_console_renders_an_empty_payload_without_errors(tmp_path):
    """Every runtime file missing: empty states, no exception, no NaN."""
    from bot.monitoring.gates import clear_cache

    clear_cache()
    empty = tmp_path / "empty"
    empty.mkdir()
    r = _render_console_in_node(tmp_path, collect_status(empty, now=1_800_000_000.0))

    assert "判断ログなし" in r["decisions"]
    assert "フラット" in r["tiles"]
    assert "NaN" not in r["tiles"] and "undefined" not in r["tiles"]
    assert "0/30回" in r["gates"] and "0/2,900行" in r["gates"]
    assert r["gates"].count("—") >= 4          # no rate anywhere: no guesses
    assert "未収集" in r["collectors"]


HARNESS = r"""
// DOM-less harness: runs the page script under stub globals so the market
// rendering path can be exercised headlessly. The 2d context records WHAT was
// drawn and WHERE, not just which methods were called — the chart now has
// three panes and "some fillRects happened" cannot tell them apart.
const fs = require("fs");
const src = fs.readFileSync(process.argv[2], "utf8");
const data = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));

function El(id) {
  this.id = id; this.innerHTML = ""; this.textContent = "";
  this.className = ""; this.hidden = false; this.style = {}; this.events = {};
}
El.prototype.addEventListener = function (k, f) { this.events[k] = f; };
El.prototype.getBoundingClientRect = () => ({left: 0, top: 0, width: 800, height: 420});
El.prototype.scrollIntoView = function () { this.scrolled = true; };

const els = {};
const document = {getElementById: id => (els[id] = els[id] || new El(id))};
let ops = [], rects = [], segs = [], texts = [], cur = null;
const ctx = {
  fillStyle: "", strokeStyle: "", lineWidth: 1, font: "", textAlign: "",
  globalAlpha: 1,
  setTransform() { ops.push("setTransform"); },
  clearRect() { ops.push("clearRect"); rects = []; segs = []; texts = []; },
  fillRect(x, y, w, h) {
    ops.push("fillRect");
    rects.push({x: x, y: y, w: w, h: h, fill: this.fillStyle, a: this.globalAlpha});
  },
  beginPath() { ops.push("beginPath"); cur = []; },
  moveTo(x, y) { ops.push("moveTo"); (cur = cur || []).push([x, y]); },
  lineTo(x, y) { ops.push("lineTo"); (cur = cur || []).push([x, y]); },
  stroke() { ops.push("stroke"); segs.push({pts: cur || [], stroke: this.strokeStyle}); },
  fill() { ops.push("fill"); },
  closePath() { ops.push("closePath"); },
  setLineDash() { ops.push("setLineDash"); },
  fillText(s, x, y) { ops.push("fillText"); texts.push({s: String(s), x: x, y: y}); },
};
const canvas = document.getElementById("m-chart");
canvas.getContext = () => ctx;
canvas.parentElement = {clientWidth: 800};
const window = {devicePixelRatio: 2, addEventListener() {}};

const api = new Function(
  "document", "window", "fetch", "setInterval", "clearInterval", "navigator",
  src + "\nreturn {renderMarket, drawChart, showTab, setChartTf, arrowSvg, " +
        "chartHover, showTrendTable, pollMs: () => marketPollMs(), " +
        "tf: () => chartTf, geom: () => chartGeom};"
)(document, window, () => Promise.reject(new Error("no network")),
  () => 7, () => 0, {});

api.showTab("market");
api.renderMarket(data);           // opens on the default (1m) frame
const g = api.geom();
const openTf = api.tf(), openPoll = api.pollMs();

// A price gridline is the only horizontal segment that crosses BOTH the price
// pane and the depth panel — that shared y-axis is the point of the layout.
// Vertical segments are the time grid.
const horiz = segs.filter(s => s.pts.length === 2 && s.pts[0][1] === s.pts[1][1] &&
  g && s.pts[0][0] === g.padL && s.pts[1][0] === g.depthX + g.depthW);
// a time gridline is one path with FOUR points: it crosses the price pane and
// the volume pane but skips the gap between them (a candle wick has two)
const vert = segs.filter(s => s.pts.length === 4 && s.pts.every(p => p[0] === s.pts[0][0]));
const openRects = rects;
const inVolPane = g ? openRects.filter(r => r.y >= g.volTop - 0.5) : [];
const inDepth = g ? openRects.filter(r => r.x >= g.depthX - 0.5 && r.y < g.volTop) : [];
// EVERY rect in the depth column, wherever it landed: a depth bucket sits at a
// price, and a price outside the pane's window has no business being painted
// over the volume pane below it or the label gutter above.
const depthCol = g ? openRects.filter(r => r.x >= g.depthX - 0.5) : [];
const outsidePane = g ? depthCol.filter(
  r => r.y < g.padT - 0.01 || r.y + r.h > g.padT + g.priceH + 0.01) : [];
const byFill = list => {
  const out = {};
  for (const r of list) out[r.fill] = (out[r.fill] || 0) + 1;
  return out;
};

// what the page looked like on the frame it OPENED on, before any switching
const openSub = els["m-chart-sub"].textContent, openLegend = els["m-legend"].innerHTML;
const openStrip = els["m-strip"].innerHTML, openTexts = texts.map(t => t.s);

// the tooltip for the NEWEST bar, on the frame the page opened on
if (g) api.chartHover({clientX: g.padL + g.step * (g.bars.length - 0.5),
                       currentTarget: canvas});
const openTipLast = g ? els["m-tip"].innerHTML : "";

const before = ops.length;
api.setChartTf("1h");
api.chartHover({clientX: 300, currentTarget: canvas});
const hover1h = els["m-tip"].innerHTML, hoverDisplay = els["m-tip"].style.display;
api.chartHover({clientX: 780, currentTarget: canvas});   // over the depth panel
const hoverDepth = els["m-tip"].style.display;
api.showTrendTable();

console.log(JSON.stringify({
  console_hidden: els["view-console"].hidden,
  market_hidden: els["view-market"].hidden,
  tab_class: els["tab-market"].className,
  strip: els["m-strip"].innerHTML,
  table: els["t-tf"].innerHTML,
  oi: els["m-oi"].innerHTML,
  dir_strip: els["m-dir"].innerHTML,
  dir_chips: (els["m-dir"].innerHTML.match(/class="chip/g) || []).length,
  scrolled_to_table: els["t-tf"].scrolled === true,
  open_tf: openTf, open_poll_ms: openPoll, poll_after_switch: api.pollMs(),
  open_chart_sub: openSub, open_legend: openLegend, open_strip: openStrip,
  open_texts: openTexts,
  tf_buttons: (els["m-tfs"].innerHTML.match(/<button/g) || []).length,
  chart_sub: els["m-chart-sub"].textContent,
  legend: els["m-legend"].innerHTML,
  canvas_px: [canvas.width, canvas.height],
  redrawn_on_tf_switch: ops.length - before,
  price_grid_lines: horiz.length,
  time_grid_lines: vert.length,
  time_grid_majors: vert.filter(s => s.stroke !== "rgba(34,48,80,.9)").length,
  vol_rects: inVolPane.length, vol_fills: byFill(inVolPane),
  depth_rects: inDepth.length, depth_fills: byFill(inDepth),
  depth_col_rects: depthCol.length, depth_outside_pane: outsidePane.length,
  translucent_bars: openRects.filter(r => r.a < 1).length,
  open_tip_last: openTipLast,
  axis_texts: texts.map(t => t.s),
  tip: hover1h, tip_display: hoverDisplay, tip_over_depth: hoverDepth,
  bars_drawn: g ? g.bars.length : 0,
  geom: g ? {plotW: g.plotW, depthW: g.depthW, priceH: g.priceH, volH: g.volH,
             W: g.W, H: g.H} : null,
  arrow_up: api.arrowSvg(35), arrow_flat: api.arrowSvg(null),
}));
"""


def _render_market_in_node(tmp_path, payload) -> dict:
    """Execute the page's own JS against ``payload`` and report what it built."""
    import re
    import subprocess

    js = re.search(r"<script>(.*)</script>", _dashboard_page(), re.S).group(1)
    (tmp_path / "page.js").write_text(js, encoding="utf-8")
    (tmp_path / "harness.js").write_text(HARNESS, encoding="utf-8")
    (tmp_path / "market.json").write_text(json.dumps(payload), encoding="utf-8")
    node = _node()
    subprocess.run([node, "--check", str(tmp_path / "page.js")], check=True)
    out = subprocess.run(
        [node, str(tmp_path / "harness.js"), str(tmp_path / "page.js"),
         str(tmp_path / "market.json")],
        check=True, capture_output=True, text=True)
    return json.loads(out.stdout)


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_market_tab_renders_a_full_payload(tmp_path):
    from tests.test_market_view import T0, _make_workspace
    from bot.monitoring.market_view import collect_market

    workspace = tmp_path / "ws"
    workspace.mkdir()
    _make_workspace(workspace)
    payload = collect_market(workspace, now=T0 + 400 * 60)
    r = _render_market_in_node(tmp_path, payload)

    assert r["console_hidden"] is True and r["market_hidden"] is False
    assert r["tab_class"] == "on"
    assert payload["state"]["state"] in r["strip"] and "レーダー" in r["strip"]
    assert "24時間" in r["strip"] and "買い比率" in r["strip"]
    assert r["table"].count("<tr>") == 6           # header + five timeframes
    assert "OKX USDT建 OI" in r["oi"] and "DVOL" in r["oi"]
    assert r["tf_buttons"] == 5 and "1時間" in r["chart_sub"]
    assert "ロング建て" in r["legend"] and "レンジ" in r["legend"]
    # crisp on devicePixelRatio 2: the backing store is twice the CSS size
    assert r["canvas_px"] == [1600, 840]
    assert r["bars_drawn"] > 0
    assert r["redrawn_on_tf_switch"] > 10          # switching TF repaints
    assert r["tip_display"] == "block" and "JST" in r["tip"]
    assert "出来高" in r["tip"]                    # the tooltip reports volume
    assert r["tip_over_depth"] == "none"           # the depth panel is not a bar
    assert "rotate(-35.0 12 12)" in r["arrow_up"]  # SVG y is down: up = -angle
    assert r["arrow_flat"] == '<span class="flat">—</span>'


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_market_tab_opens_on_the_1m_frame_at_the_fast_cadence(tmp_path):
    """The owner scalps the 1m chart: it is what opens, and it is polled at
    10s. The slower frames drop back to 30s so the extra polls are not spent
    on bars that move once an hour."""
    from tests.test_market_view import T0, _make_workspace
    from bot.monitoring.market_view import collect_market

    workspace = tmp_path / "ws"
    workspace.mkdir()
    _make_workspace(workspace)
    r = _render_market_in_node(tmp_path, collect_market(workspace, now=T0 + 400 * 60))

    assert r["open_tf"] == "1m" and r["open_poll_ms"] == 10000
    assert r["poll_after_switch"] == 30000         # after switching to 1h
    assert r["open_chart_sub"].startswith("1分 /")
    assert "レンジ 15分" in r["open_legend"]        # the 1m frame's own band


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_market_tab_shows_the_higher_frames_as_direction_chips(tmp_path):
    """Direction is read off 15分/1時間/4時間/日足 while scalping 1m, so it sits
    above the chart as chips — coloured by the same trend score as the table,
    and clicking one goes to the table."""
    from tests.test_market_view import T0, _make_workspace
    from bot.monitoring.market_view import collect_market

    workspace = tmp_path / "ws"
    workspace.mkdir()
    _make_workspace(workspace, minutes=16 * 1440)   # enough history to vote 日足
    payload = collect_market(workspace, now=T0 + 16 * 1440 * 60)
    r = _render_market_in_node(tmp_path, payload)

    assert r["dir_chips"] == 4                      # 15m / 1h / 4h / 1d, not 1m
    for tf in payload["timeframes"]:
        if tf["tf"] == "1m":
            assert f'>{tf["label"]} ' not in r["dir_strip"]
            continue
        assert f'>{tf["label"]} ' in r["dir_strip"]
        glyph = {1: "▲", -1: "▼", 0: "─"}[
            (tf["trend"]["score"] > 0) - (tf["trend"]["score"] < 0)]
        assert f'{tf["label"]} {glyph}' in r["dir_strip"]
    # the chips carry the same up/down semantics as everything else on the page
    assert '"chip up"' in r["dir_strip"] or '"chip down"' in r["dir_strip"] \
        or '"chip flat"' in r["dir_strip"]
    assert r["scrolled_to_table"] is True


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_market_tab_draws_the_volume_pane_and_the_depth_panel(tmp_path):
    """The chart is three panes on one canvas: price, volume under it on the
    same x, order-book depth beside it on the same y."""
    from tests.test_market_view import T0, _make_workspace
    from bot.monitoring.market_view import attach_board, collect_market

    workspace = tmp_path / "ws"
    workspace.mkdir()
    # 120 minutes from UTC midnight, so the visible 1m window contains the one
    # boundary that gets the stronger gridline
    _make_workspace(workspace, minutes=120)
    payload = collect_market(workspace, now=T0 + 120 * 60)
    mid = payload["chart"]["tfs"]["1m"]["bars"][-1]["c"]
    attach_board(payload, {
        "mid_price": mid,
        "bids": [{"price": mid - 500 - i * 1500, "size": 0.4 + i * 0.01} for i in range(120)],
        "asks": [{"price": mid + 500 + i * 1500, "size": 0.3 + i * 0.01} for i in range(120)],
    }, now=T0 + 120 * 60)
    r = _render_market_in_node(tmp_path, payload)

    # panes are sized as designed: volume ~20% of the body, depth ~15% of width
    geom = r["geom"]
    assert geom["W"] == 800 and geom["H"] == 420
    assert 0.17 < geom["volH"] / (geom["volH"] + geom["priceH"] + 10) < 0.23
    assert 0.13 < geom["depthW"] / (geom["depthW"] + geom["plotW"] + 8) < 0.17

    # a fine price grid — one line per server-computed gridline, each labelled
    # at the right edge in the monospace (tabular) face
    grid = payload["chart"]["tfs"]["1m"]["scale"]["grid"]
    assert 6 <= len(grid) <= 14 and r["price_grid_lines"] == len(grid)
    for price in grid:
        assert round(price) == price and f"{round(price):,}" in r["open_texts"]
    # time gridlines on clock boundaries, with UTC midnight drawn stronger
    assert r["time_grid_lines"] == len(payload["chart"]["tfs"]["1m"]["time_grid"])
    assert r["time_grid_majors"] >= 1

    # the volume pane draws a stacked buy/sell column: _make_workspace writes a
    # flow file, so the split is real data rather than an undifferentiated bar
    assert r["vol_rects"] >= len(payload["chart"]["tfs"]["1m"]["bars"])
    assert "#46b87a" in r["vol_fills"] and "#e0604f" in r["vol_fills"]

    # the depth panel drew both sides, and drew them inside its own column
    assert r["depth_rects"] > 4
    assert "rgba(224,96,79,.55)" in r["depth_fills"]     # asks
    assert "rgba(70,184,122,.55)" in r["depth_fills"]    # bids
    assert "板情報なし" not in r["open_texts"]
    assert "板" in r["open_legend"] and "出来高" in r["open_legend"]


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_market_tab_says_so_when_the_board_fetch_failed(tmp_path):
    """The board comes off the network and the network is allowed to fail: the
    panel says 板情報なし and every other pane draws exactly as before."""
    from tests.test_market_view import T0, _make_workspace
    from bot.monitoring.market_view import attach_board, collect_market

    workspace = tmp_path / "ws"
    workspace.mkdir()
    _make_workspace(workspace)
    payload = attach_board(collect_market(workspace, now=T0 + 400 * 60), None)
    assert payload["board"] is None
    r = _render_market_in_node(tmp_path, payload)

    assert "板情報なし" in r["open_texts"]
    assert r["depth_rects"] == 0
    assert r["bars_drawn"] > 0 and r["vol_rects"] > 0 and r["price_grid_lines"] > 0
    assert "右 = 板情報なし" in r["open_legend"]


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_market_tab_draws_the_live_tail_as_translucent(tmp_path):
    """Live 1m buckets are built from the public tape and are not in the CSV
    yet, so they are drawn dimmer than an archived bar and labelled as live."""
    from tests.test_market_view import T0, _make_workspace, _exec
    from bot.monitoring.market_view import bars_from_executions, collect_market

    workspace = tmp_path / "ws"
    workspace.mkdir()
    _make_workspace(workspace)
    last_close = 11_000_000.0 * 1.0002 ** 400
    live = bars_from_executions([_exec(400 * 60 + s, last_close, 0.2)
                                 for s in (5, 35, 65, 95)])
    payload = collect_market(workspace, now=T0 + 402 * 60, live_bars=live)
    assert payload["live"]["bars"] == 2

    r = _render_market_in_node(tmp_path, payload)
    assert "ライブ 2本" in r["open_chart_sub"]
    assert "ライブ追記 2分" in r["open_strip"]
    assert r["translucent_bars"] > 0
    assert "半透明の足" in r["open_legend"]


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_market_tab_marks_the_tape_s_truncated_bucket(tmp_path):
    """The fetch window is often one single minute, so the tape's oldest —
    truncated — bucket IS the live tail: it is drawn rather than dropped, in
    the same translucent style, and the tooltip says its volume is a floor."""
    from tests.test_market_view import T0, _make_workspace, _exec
    from bot.monitoring.market_view import bars_from_executions, collect_market

    workspace = tmp_path / "ws"
    workspace.mkdir()
    _make_workspace(workspace)
    live = bars_from_executions([_exec(400 * 60 + 10, 11_900_000.0, 0.02)])
    payload = collect_market(workspace, now=T0 + 401 * 60, live_bars=live)
    last = payload["chart"]["tfs"]["1m"]["bars"][-1]
    assert last["truncated"] is True and last["live"] is True

    r = _render_market_in_node(tmp_path, payload)
    assert "不完全(取得上限)" in r["open_tip_last"]     # the volume is a floor
    assert "ライブ" in r["open_tip_last"]
    assert r["translucent_bars"] > 0


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_depth_panel_never_paints_outside_the_price_pane(tmp_path):
    """The depth ladder is floor/ceil'd onto the gridline step, so its end
    buckets already reach past the pane, and a board fetched while price ran
    away reaches much further. Un-clipped, those rects painted over the volume
    pane below and the price labels above."""
    from tests.test_market_view import T0, _make_workspace
    from bot.monitoring.market_view import attach_board, collect_market

    workspace = tmp_path / "ws"
    workspace.mkdir()
    _make_workspace(workspace, minutes=120)
    payload = collect_market(workspace, now=T0 + 120 * 60)
    mid = payload["chart"]["tfs"]["1m"]["bars"][-1]["c"]
    attach_board(payload, {
        "mid_price": mid,
        "bids": [{"price": mid - 500 - i * 1500, "size": 0.4} for i in range(120)],
        "asks": [{"price": mid + 500 + i * 1500, "size": 0.3} for i in range(120)],
    }, now=T0 + 120 * 60)

    depth = payload["chart"]["tfs"]["1m"]["depth"]
    scale = payload["chart"]["tfs"]["1m"]["scale"]
    assert depth["buckets"]
    # price ran away from the book between the candle file and the board fetch
    depth["buckets"].append({"p": scale["hi"] + 4 * depth["step"],
                             "bid": 0.0, "ask": depth["max"]})
    depth["buckets"].append({"p": scale["lo"] - 4 * depth["step"],
                             "bid": depth["max"], "ask": 0.0})

    r = _render_market_in_node(tmp_path, payload)
    assert r["depth_col_rects"] > 4          # the panel still drew
    assert r["depth_outside_pane"] == 0      # and stayed inside its own pane


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_market_tab_says_the_feed_stopped_instead_of_labelling_it(tmp_path):
    """Day-old candles must not render as 静穏レンジ — the pill says the
    collector stopped, and the freshness line stays."""
    from tests.test_market_view import T0, _make_workspace
    from bot.monitoring.market_view import collect_market

    workspace = tmp_path / "ws"
    workspace.mkdir()
    _make_workspace(workspace)
    payload = collect_market(workspace, now=T0 + 400 * 60 + 24 * 3600)
    assert payload["state"]["state"] is None and payload["state"]["stale"] is True

    r = _render_market_in_node(tmp_path, payload)
    assert "データ停止 24.0時間前" in r["strip"]
    assert "足 24.0時間前" in r["strip"]                  # freshness line kept
    for label in ("嵐", "ブレイク", "静穏レンジ", "通常"):
        assert label not in r["strip"].split("レーダー")[0]
    assert r["bars_drawn"] > 0                            # the chart still draws


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_market_tab_renders_an_empty_payload_without_errors(tmp_path):
    """Every data file missing: empty states, no exception, no chart."""
    from bot.monitoring.market_view import collect_market

    empty = tmp_path / "empty"
    empty.mkdir()
    r = _render_market_in_node(tmp_path, collect_market(empty))

    assert "ローソク足データなし" in r["strip"]
    assert "ローソク足データなし" in r["table"]
    assert "OIスナップショット未収集" in r["oi"]
    assert r["tf_buttons"] == 0 and r["chart_sub"] == "データなし"
    assert r["legend"] == "" and r["bars_drawn"] == 0
    assert r["tip_display"] == "none"
    # nothing to take a direction from, so no chips and no panes
    assert r["dir_strip"] == "" and r["dir_chips"] == 0
    assert r["vol_rects"] == 0 and r["depth_rects"] == 0
    assert r["price_grid_lines"] == 0 and r["time_grid_lines"] == 0
    assert "チャートデータなし" in r["axis_texts"]


# ---- public bitFlyer reads (board + execution tape) -------------------------
class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakeSession:
    """Records every GET and answers from a scripted queue. No sockets."""

    def __init__(self, answers):
        self.answers = answers          # path -> payload, or an Exception
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, dict(params or {}), timeout))
        answer = self.answers[url.rsplit("/v1/", 1)[1].split("?")[0]]
        if isinstance(answer, Exception):
            raise answer
        return _FakeResponse(answer)


def _board_payload(mid=11_000_000.0, n=5, step=None):
    step = step if step is not None else max(mid * 0.0001, 0.01)
    return {"mid_price": mid,
            "bids": [{"price": mid - step * (i + 1), "size": 0.5} for i in range(n)],
            "asks": [{"price": mid + step * (i + 1), "size": 0.4} for i in range(n)]}


def _exec_payload(count=3, price=11_000_000.0):
    return [{"id": i, "side": "BUY" if i % 2 else "SELL", "price": price + i,
             "size": 0.01, "exec_date": f"2026-08-20T00:00:{i:02d}.000"}
            for i in range(count)]


def test_public_reads_hit_the_documented_endpoints_without_auth(monkeypatch):
    module = _dashboard_module(offline=False)
    session = _FakeSession({"board": _board_payload(),
                            "executions": _exec_payload()})
    monkeypatch.setattr(module, "_session", session)

    assert module.fetch_board(now=1000.0)["mid_price"] == 11_000_000.0
    assert len(module.fetch_executions(now=1000.0)) == 3

    urls = [c[0] for c in session.calls]
    assert urls == ["https://api.bitflyer.com/v1/board",
                    "https://api.bitflyer.com/v1/executions"]
    assert session.calls[0][1] == {"product_code": "FX_BTC_JPY"}
    assert session.calls[1][1] == {"product_code": "FX_BTC_JPY", "count": 500}
    assert all(c[2] == module.PUBLIC_TIMEOUT == 3.0 for c in session.calls)
    # no auth material anywhere near these: they are public read-only endpoints
    assert not hasattr(session, "headers")


def test_public_reads_are_cached_so_the_rate_budget_is_bounded(monkeypatch):
    """The bot shares the 500 req / 5 min public IP budget. Two endpoints at
    one call per PUBLIC_TTL is 0.4 req/s worst case, whatever the poll rate."""
    module = _dashboard_module(offline=False)
    session = _FakeSession({"board": _board_payload(),
                            "executions": _exec_payload()})
    monkeypatch.setattr(module, "_session", session)

    assert module.PUBLIC_TTL >= 5.0
    for t in (1000.0, 1001.0, 1004.9):
        module.fetch_board(now=t)
        module.fetch_executions(now=t)
    assert len(session.calls) == 2                  # one per endpoint

    module.fetch_board(now=1005.0)
    module.fetch_executions(now=1005.0)
    assert len(session.calls) == 4
    worst_case_rps = 2 / module.PUBLIC_TTL
    assert worst_case_rps <= 0.4


def test_public_reads_fail_soft_and_keep_serving_the_last_snapshot(monkeypatch):
    """bitFlyer down, the box offline, a timeout: the console must not care."""
    module = _dashboard_module(offline=False)
    good = _FakeSession({"board": _board_payload(), "executions": _exec_payload()})
    monkeypatch.setattr(module, "_session", good)
    assert module.fetch_board(now=1000.0) is not None

    broken = _FakeSession({"board": RuntimeError("connection reset"),
                           "executions": RuntimeError("connection reset")})
    monkeypatch.setattr(module, "_session", broken)
    # the last good board is still served, with the age it really has
    assert module.fetch_board(now=1010.0)["mid_price"] == 11_000_000.0
    assert module.board_fetched_at() == 1000.0
    assert module._public_cache["board"]["error"].startswith("RuntimeError")
    # a hard-down endpoint is still only retried once per TTL
    module.fetch_board(now=1011.0)
    assert len(broken.calls) == 1

    # nothing was ever fetched: None / [], and the payload still assembles
    fresh = _dashboard_module(offline=False)
    monkeypatch.setattr(fresh, "_session",
                        _FakeSession({"board": OSError("no route"),
                                      "executions": OSError("no route")}))
    assert fresh.fetch_board(now=1.0) is None
    assert fresh.fetch_executions(now=1.0) == []
    assert fresh.live_bars(now=1.0) == []


def test_live_bars_come_off_the_execution_tape(monkeypatch):
    module = _dashboard_module(offline=False)
    monkeypatch.setattr(module, "_session",
                        _FakeSession({"board": _board_payload(),
                                      "executions": _exec_payload(count=4)}))
    bars = module.live_bars(now=1000.0)
    assert len(bars) == 1 and bars[0]["live"] is True
    assert bars[0]["trades"] == 4 and bars[0]["volume"] == pytest.approx(0.04)


def test_api_market_attaches_a_fresh_board_to_the_cached_payload(tmp_path, monkeypatch):
    """The heavy file parse is cached; the board is not part of that key, so a
    depth panel never waits on a candle file to change."""
    from tests.test_market_view import _make_workspace

    _make_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    module = _dashboard_module()
    calls = []
    monkeypatch.setattr(module, "collect_market",
                        lambda root, live_bars=(): calls.append(root) or
                        json.loads(json.dumps(_market_skeleton())))
    board = {"now": _board_payload(mid=100.0)}
    monkeypatch.setattr(module, "fetch_board", lambda now=None: board["now"])
    monkeypatch.setattr(module, "board_fetched_at", lambda: 55.0)

    first = json.loads(module.market_body(".", now=1000.0))
    assert first["board"]["mid"] == 100.0 and first["board"]["fetched_at"] == 55.0
    assert first["chart"]["tfs"]["1m"]["depth"]["step"] == 5.0

    board["now"] = _board_payload(mid=101.0)
    second = json.loads(module.market_body(".", now=1002.0))
    assert len(calls) == 1                       # the payload came from cache
    assert second["board"]["mid"] == 101.0       # the board did not


def _market_skeleton():
    """The minimum collect_market shape attach_board has to cope with."""
    return {"chart": {"tfs": {"1m": {"scale": {"hi": 110.0, "lo": 90.0, "step": 5.0,
                                               "grid": [90.0, 95.0, 100.0, 105.0, 110.0]}}}}}


def test_api_market_rebuilds_when_the_live_tail_moves(tmp_path, monkeypatch):
    """The CSV writer runs every ~15 min; the live tail is what actually moves
    between polls, so it has to be part of the cache key."""
    from tests.test_market_view import _make_workspace

    _make_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    module = _dashboard_module()
    calls = []
    monkeypatch.setattr(module, "collect_market",
                        lambda root, live_bars=(): calls.append(list(live_bars)) or
                        {"n": len(calls)})
    tail = [{"ts": 60.0, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0,
             "volume": 0.5, "live": True}]
    monkeypatch.setattr(module, "live_bars", lambda now=None: [dict(tail[0])])

    assert json.loads(module.market_body(".", now=1000.0))["n"] == 1
    assert json.loads(module.market_body(".", now=1100.0))["n"] == 1   # tail same
    tail[0]["close"] = 2.0                        # price moved inside the minute
    assert json.loads(module.market_body(".", now=1200.0))["n"] == 2
    assert calls[-1][0]["close"] == 2.0           # and it reached collect_market


def test_page_carries_the_new_panes_and_chips():
    page = _dashboard_page()
    # volume pane, depth panel and the chip strip are all present in the markup
    assert 'id="m-dir"' in page and 'class="dirstrip"' in page
    assert "function drawDepth(" in page and "板情報なし" in page
    assert "drawDepth(ctx, payload.depth" in page
    assert "payload.time_grid" in page and "payload.scale" in page
    assert "payload.vmax" in page and "b.bv" in page and "b.sv" in page
    assert "showTrendTable()" in page and "scrollIntoView" in page
    # the chart opens on 1m and the range band is named by its own window
    assert 'chartTf = "1m"' in page
    assert "p.range.window_label" in page
    # the payload's new top-level sections are consumed by the page
    for key in ("board", "live"):
        assert f"d.{key}" in page or f"marketData.{key}" in page, key


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_market_tab_flags_a_collector_outage_behind_the_live_tail(tmp_path):
    """The tape can keep the price live while the CSV writer is dead. That is
    a hole in the series, not a live feed, and the page has to say so — the
    windows measured across it are refused rather than faked."""
    from tests.test_market_view import T0, _make_workspace, _exec
    from bot.monitoring.market_view import bars_from_executions, collect_market

    workspace = tmp_path / "ws"
    workspace.mkdir()
    _make_workspace(workspace)
    live = bars_from_executions([_exec(400 * 60 + 24 * 3600 + s, 13_000_000.0, 0.2)
                                 for s in (5, 35)])
    payload = collect_market(workspace, now=T0 + 400 * 60 + 24 * 3600 + 60,
                             live_bars=live)
    assert payload["state"]["stale"] is False        # the tape is live
    assert payload["state"]["ret_30m_pct"] is None   # the 30m window is a hole
    assert payload["live"]["gap_sec"] > 86000

    r = _render_market_in_node(tmp_path, payload)
    assert "CSV欠落 24.0時間" in r["open_strip"]
    assert "CSV欠落 24.0時間前" not in r["open_strip"]   # a duration, not an age
    assert "30分</span><span class=\"mono flat\">—" in r["open_strip"]

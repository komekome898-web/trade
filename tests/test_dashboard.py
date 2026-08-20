"""Dashboard aggregation over the runtime files."""
from __future__ import annotations

import json

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


def test_kill_switch_reflected(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "kill_switch.json").write_text(
        json.dumps({"reason": "manual", "detail": "test"}), encoding="utf-8")
    d = collect_status(tmp_path)
    assert d["components"]["main_bot"]["state"] == "killed"
    assert d["kill_switch"]["reason"] == "manual"

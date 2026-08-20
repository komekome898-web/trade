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


def test_status_write_survives_windows_permission_error(tmp_path, monkeypatch):
    """A dashboard reader holding status.json open must never crash the bot
    (Windows os.replace raises PermissionError then)."""
    from pathlib import Path
    from bot.monitoring.status import StatusWriter

    w = StatusWriter(tmp_path / "status.json", clock=lambda: 123.0)
    monkeypatch.setattr(Path, "replace",
                        lambda self, target: (_ for _ in ()).throw(PermissionError(5)))
    w.write()  # must not raise
    assert json.loads((tmp_path / "status.json").read_text(encoding="utf-8"))[
        "updated_at"] == 123.0  # fell back to the direct write


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

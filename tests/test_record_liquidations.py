"""清算ストリーム記録器の性質テスト(scripts/record_liquidations.py)。

ネットワークには出ない。書き出しの契約(生を残す・日付で切る・追記のみ)と、
到達確認スクリプトの判定規則だけを固定する。
"""
from __future__ import annotations

import gzip
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _load(name: str):
    path = REPO / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


rec = _load("record_liquidations")
chk = _load("check_liquidation_feeds")


def test_writer_keeps_the_raw_message_verbatim(tmp_path, monkeypatch):
    """生を残すのが約束。こちらの解釈で列を削らない。"""
    monkeypatch.setattr(rec, "OUT_DIR", tmp_path)
    w = rec.Writer("bitmex")
    payload = {"table": "liquidation", "action": "insert",
               "data": [{"orderID": "x", "side": "Sell", "price": 78629.7,
                         "leavesQty": 100, "未知の列": "落とさない"}]}
    w.write({"venue": "bitmex", "recv_us": 1, "raw": payload})
    w.close()

    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    rows = [json.loads(x) for x in
            gzip.open(tmp_path / f"bitmex_{day}.jsonl.gz", "rt", encoding="utf-8")]
    assert len(rows) == 1
    assert rows[0]["raw"] == payload            # 一字一句そのまま
    assert rows[0]["recv_us"] == 1


def test_writer_appends_and_never_truncates(tmp_path, monkeypatch):
    """再接続で開き直しても、その日のぶんを消さない。"""
    monkeypatch.setattr(rec, "OUT_DIR", tmp_path)
    for i in range(3):
        w = rec.Writer("okx")
        w.write({"venue": "okx", "recv_us": i, "raw": {"n": i}})
        w.close()
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    rows = [json.loads(x) for x in
            gzip.open(tmp_path / f"okx_{day}.jsonl.gz", "rt", encoding="utf-8")]
    assert [r["raw"]["n"] for r in rows] == [0, 1, 2]


def test_every_venue_is_declared_in_both_scripts():
    """記録できるベニューは、到達確認できるベニューでもあること。"""
    assert set(rec.VENUES) == set(chk.FEEDS)


@pytest.mark.parametrize("venue", sorted(rec.VENUES))
def test_venue_specs_are_public_read_only_endpoints(venue):
    spec = rec.VENUES[venue]
    assert spec["url"].startswith("wss://")
    # 公開エンドポイントであること(private ストリームに繋がない)
    assert "/private" not in spec["url"]
    # 資格情報が混ざっていないこと
    blob = json.dumps(spec, default=str).lower()
    for forbidden in ("apikey", "api_key", "secret", "passphrase", "signature"):
        assert forbidden not in blob, (venue, forbidden)
    # 送るのは購読と生存確認だけ(発注系の op を持たない)
    if spec["sub"]:
        assert spec["sub"].get("op") in {"subscribe"}, venue


def test_reachability_verdict_separates_no_liquidations_from_no_connection():
    """**「清算未発生」を「届かない」と誤読しない**のが、この判定の要点。"""
    connected_quiet = {"rest": {"ok": False}, "ws": {"connected": True, "liquidations": 0}}
    connected_hit = {"rest": {"ok": True}, "ws": {"connected": True, "liquidations": 3}}
    rest_only = {"rest": {"ok": True}, "ws": {"connected": False}}
    dead = {"rest": {"ok": False}, "ws": {"connected": False}}

    assert "使える" in chk.verdict(connected_quiet)
    assert "使える" in chk.verdict(connected_hit)
    assert "REST" in chk.verdict(rest_only)
    assert chk.verdict(dead) == "届かない"


def test_the_recorder_is_wired_into_start_all_and_share_logs():
    """止めたら永久に空白になるデータなので、常駐と共有の両方に載っていること。"""
    start_all = (REPO / "deploy" / "start_all.bat").read_text(
        encoding="utf-8", errors="surrogateescape")
    share = (REPO / "deploy" / "share_logs.bat").read_text(
        encoding="utf-8", errors="surrogateescape")
    assert "record_liquidations.py" in start_all
    assert "data\\liquidations" in share


def test_dataset_has_a_schema():
    """DATA_QA の不変条件: 全ファイルに schema がある。"""
    schema = json.loads((REPO / "schema" / "liquidations.json").read_text(encoding="utf-8"))
    assert schema["path_glob"] == ["data/liquidations/*.jsonl.gz"]
    assert set(schema["columns"]) == {"venue", "recv_us", "raw"}
    assert schema["known_defects"]

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


# ---------------------------------------------------------------------------
# 手順 P9: 集計サービスの鍵。**鍵を出力に出さない**ことが唯一の安全要件。
# ---------------------------------------------------------------------------

def test_depth_checker_never_prints_the_key():
    """鍵は `.env` からしか読まず、出力には長さしか出さない。"""
    src = (REPO / "scripts" / "check_liquidation_history_depth.py").read_text(encoding="utf-8")
    # 鍵の変数をそのまま print / f-string に埋めていないこと
    assert "print(key" not in src and "{key}" not in src
    assert "os.environ.get(\"COINALYZE_API_KEY\"" in src
    assert "load_dotenv" in src
    # ヘッダとしてだけ使う
    assert '"api_key": key' in src or "'api_key': key" in src


def test_key_names_are_declared_in_env_example():
    env = (REPO / ".env.example").read_text(encoding="utf-8")
    assert "COINALYZE_API_KEY=" in env and "COINGLASS_API_KEY=" in env


def test_procedure_p9_tells_the_owner_not_to_paste_the_key():
    proc = (REPO / "docs" / "OWNER_PROCEDURES.md").read_text(encoding="utf-8")
    assert "## P9" in proc
    p9 = proc.split("## P9")[1]
    assert "チャットに貼らないでください" in p9
    assert ".env" in p9


# ---------------------------------------------------------------------------
# Gate.io の履歴取り込み(scripts/fetch_gate_liquidations.py)。
# ネットワークには出ない。**取りこぼしを黙って作らない**という一点だけを固定する。
# ---------------------------------------------------------------------------

gate = _load("fetch_gate_liquidations")


def _fake_gate(counts: dict[tuple[int, int], int]):
    """区間 -> 返す件数、の表から fetch_window の代役を作る。既定は 0 件。"""
    calls: list[tuple[int, int]] = []

    def fetch_window(contract, frm, to):          # noqa: ARG001
        calls.append((frm, to))
        return [{"time": frm, "n": i} for i in range(counts.get((frm, to), 0))]

    return fetch_window, calls


def test_hour_is_taken_in_one_request_when_it_fits(monkeypatch):
    """飽和していない時間は割らない(無駄に叩かない)。"""
    fw, calls = _fake_gate({(1000, 1000 + gate.HOUR - 1): 5})
    monkeypatch.setattr(gate, "fetch_window", fw)
    monkeypatch.setattr(gate.time, "sleep", lambda *_: None)
    rows, truncated = gate.fetch_hour("BTC_USDT", 1000)
    assert len(rows) == 5 and truncated == []
    assert calls == [(1000, 1000 + gate.HOUR - 1)]


def test_saturated_window_is_split_and_the_pieces_do_not_overlap(monkeypatch):
    """飽和したら半分に割る。**割った区間は重ならず、隙間も空けない**
    — 重なれば偽の重複が生まれ、隙間が空けば黙って落ちるため。"""
    frm, to = 0, gate.HOUR - 1
    fw, calls = _fake_gate({(frm, to): gate.LIMIT})
    monkeypatch.setattr(gate, "fetch_window", fw)
    monkeypatch.setattr(gate.time, "sleep", lambda *_: None)
    gate.fetch_hour("BTC_USDT", frm)

    leaves = [c for c in calls if c != (frm, to)]
    assert leaves, "飽和したのに割っていない"
    leaves.sort()
    assert leaves[0][0] == frm and leaves[-1][1] == to
    for (a_frm, a_to), (b_frm, _b_to) in zip(leaves, leaves[1:]):
        assert b_frm == a_to + 1, (a_frm, a_to, b_frm)   # 隙間も重なりも無い


def test_a_second_that_still_saturates_is_recorded_as_truncated(monkeypatch):
    """1 秒でも飽和したら**取りこぼしを台帳に残す**。黙って落とさない。"""
    frm = 0
    counts = {(a, b): gate.LIMIT for a in range(gate.HOUR) for b in range(a, gate.HOUR)}
    fw, _calls = _fake_gate(counts)
    monkeypatch.setattr(gate, "fetch_window", fw)
    monkeypatch.setattr(gate.time, "sleep", lambda *_: None)
    _rows, truncated = gate.fetch_hour("BTC_USDT", frm)
    assert truncated, "全区間が飽和したのに取りこぼしが記録されていない"
    assert all(a == b for a, b in truncated), "1 秒まで割り切ってから諦めること"


def test_the_gate_dataset_has_a_schema():
    schema = json.loads((REPO / "schema" / "gate_liquidations.json").read_text(encoding="utf-8"))
    assert schema["path_glob"] == ["backtest_data/gate_liquidations_*/*.jsonl.gz"]
    assert set(schema["columns"]) >= {"time", "size", "fill_price", "order_price"}
    # 被覆はサイドカーが真実、という約束が明文化されていること
    assert any("progress.json" in d for d in schema["known_defects"])

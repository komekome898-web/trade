"""Tests for scripts/extract_tape.py — WS jsonl.gz -> data/tape/*.csv.gz.

Fixtures reproduce the exact shape src/bot/market_data/realtime.py writes:
one JSON line per WS message, {"rts": <float>, "m": <raw bitFlyer payload>},
gzip-appended per session. Real payload sampled from a live recording:
    {"jsonrpc":"2.0","method":"channelMessage","params":{
        "channel":"lightning_executions_FX_BTC_JPY",
        "message":[{"id":.., "side":"SELL", "price":.., "size":..,
                    "exec_date":"2026-08-20T05:08:05.7271455Z", ...}]}}
"""
from __future__ import annotations

import csv
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import extract_tape as et  # noqa: E402


# ---- fixture writers -------------------------------------------------------
def exe(id_, side, price, size, exec_date):
    return {"id": id_, "side": side, "price": price, "size": size,
            "exec_date": exec_date,
            "buy_child_order_acceptance_id": "JRF-b", "sell_child_order_acceptance_id": "JRF-s"}


def exec_msg(rts, execs, channel="lightning_executions_FX_BTC_JPY"):
    return {"rts": rts, "m": {"jsonrpc": "2.0", "method": "channelMessage",
                              "params": {"channel": channel, "message": execs}}}


def board_msg(rts):
    return {"rts": rts, "m": {"jsonrpc": "2.0", "method": "channelMessage",
                              "params": {"channel": "lightning_board_FX_BTC_JPY",
                                        "message": {"mid_price": 11000000, "bids": [], "asks": []}}}}


def ticker_msg(rts):
    return {"rts": rts, "m": {"jsonrpc": "2.0", "method": "channelMessage",
                              "params": {"channel": "lightning_ticker_FX_BTC_JPY",
                                        "message": {"ltp": 11000000}}}}


def subscribe_ack(id_=1):
    return {"rts": 1.0, "m": {"jsonrpc": "2.0", "id": id_, "result": True}}


def _write_gz(path: Path, lines) -> None:
    """lines: dicts (json.dumps'd) or raw str (written verbatim, for
    deliberately malformed content)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for line in lines:
            text = line if isinstance(line, str) else json.dumps(line, ensure_ascii=False)
            f.write(text + "\n")


def _read_csv_gz(path: Path):
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        return list(csv.reader(f))


def _age_file(path: Path, seconds_old: float) -> None:
    import os
    import time
    t = time.time() - seconds_old
    os.utime(path, (t, t))


# ---- tests ------------------------------------------------------------------
def test_only_executions_extracted_with_correct_columns_and_partitioning(tmp_path):
    ws = tmp_path / "data" / "ws"
    out = tmp_path / "data" / "tape"
    gz = ws / "FX_BTC_JPY_20260820_050759.jsonl.gz"
    _write_gz(gz, [
        subscribe_ack(),
        board_msg(1.0),
        ticker_msg(1.1),
        exec_msg(1.2, [
            exe(1, "SELL", 11009971.0, 0.008, "2026-08-20T05:08:05.7271455Z"),
            exe(2, "SELL", 11009971.0, 0.008, "2026-08-20T05:08:05.7271455Z"),
        ]),
        exec_msg(1.3, [exe(3, "BUY", 11010000.0, 0.01, "2026-08-20T05:08:06.0000000Z")]),
    ])
    _age_file(gz, 120)

    advanced, rows = et.run(ws, out, out / "manifest.json", min_age_sec=0)
    assert advanced == 1
    assert rows == 3

    out_files = sorted(out.glob("*.csv.gz"))
    assert [p.name for p in out_files] == ["executions_20260820.csv.gz"]

    data = _read_csv_gz(out_files[0])
    assert data[0] == et.FIELDS == ["ts", "price", "size", "side"]
    assert len(data) == 4  # header + 3 executions
    assert data[1] == ["2026-08-20T05:08:05.7271455Z", "11009971.0", "0.008", "SELL"]
    assert data[3] == ["2026-08-20T05:08:06.0000000Z", "11010000.0", "0.01", "BUY"]


def test_min_age_guard_skips_a_freshly_written_file(tmp_path):
    ws = tmp_path / "data" / "ws"
    out = tmp_path / "data" / "tape"
    gz = ws / "FX_BTC_JPY_20260820_050759.jsonl.gz"
    _write_gz(gz, [exec_msg(1.0, [exe(1, "BUY", 100.0, 0.01, "2026-08-20T00:00:00.0000000Z")])])
    # mtime left at "now" -- looks like the recorder is still writing it.

    advanced, rows = et.run(ws, out, out / "manifest.json")  # default min_age_sec=60
    assert (advanced, rows) == (0, 0)
    assert not out.exists() or not list(out.glob("*.csv.gz"))


def test_idempotent_rerun_and_manifest_skip(tmp_path):
    ws = tmp_path / "data" / "ws"
    out = tmp_path / "data" / "tape"
    gz = ws / "FX_BTC_JPY_20260820_050759.jsonl.gz"
    _write_gz(gz, [
        exec_msg(1.0, [exe(1, "BUY", 100.0, 0.01, "2026-08-20T00:00:00.0000000Z")]),
        exec_msg(1.1, [exe(2, "SELL", 101.0, 0.02, "2026-08-20T00:00:01.0000000Z")]),
    ])
    _age_file(gz, 120)
    manifest_path = out / "manifest.json"

    advanced1, rows1 = et.run(ws, out, manifest_path, min_age_sec=0)
    assert (advanced1, rows1) == (1, 2)

    manifest = json.loads(manifest_path.read_text())
    assert manifest[gz.name]["lines"] == 2

    # Re-run with nothing new: the file is unchanged -> zero rows written,
    # zero files advanced (manifest already covers every line).
    advanced2, rows2 = et.run(ws, out, manifest_path, min_age_sec=0)
    assert (advanced2, rows2) == (0, 0)

    data = _read_csv_gz(out / "executions_20260820.csv.gz")
    assert len(data) == 3  # header + 2, not duplicated


def test_growing_file_only_extracts_new_lines_on_rerun(tmp_path):
    ws = tmp_path / "data" / "ws"
    out = tmp_path / "data" / "tape"
    gz = ws / "FX_BTC_JPY_20260820_050759.jsonl.gz"
    _write_gz(gz, [exec_msg(1.0, [exe(1, "BUY", 100.0, 0.01, "2026-08-20T00:00:00.0000000Z")])])
    _age_file(gz, 120)
    manifest_path = out / "manifest.json"

    et.run(ws, out, manifest_path, min_age_sec=0)

    # The recorder appends more messages (new gzip member, same file).
    with gzip.open(gz, "at", encoding="utf-8") as f:
        f.write(json.dumps(exec_msg(2.0, [exe(2, "SELL", 102.0, 0.03,
                                              "2026-08-20T00:00:02.0000000Z")])) + "\n")
    _age_file(gz, 120)

    advanced, rows = et.run(ws, out, manifest_path, min_age_sec=0)
    assert (advanced, rows) == (1, 1)  # only the new execution, not re-emitted

    data = _read_csv_gz(out / "executions_20260820.csv.gz")
    assert len(data) == 3  # header + 2 total, across two gzip members


def test_torn_last_line_is_tolerated_and_resumed_later(tmp_path):
    ws = tmp_path / "data" / "ws"
    out = tmp_path / "data" / "tape"
    gz = ws / "FX_BTC_JPY_20260820_050759.jsonl.gz"
    good = exec_msg(1.0, [exe(1, "BUY", 100.0, 0.01, "2026-08-20T00:00:00.0000000Z")])
    torn = '{"rts": 2.0, "m": {"jsonrpc": "2.0", "method": "channelMessage", "para'
    _write_gz(gz, [good, torn])  # torn line written with NO closing content
    _age_file(gz, 120)
    manifest_path = out / "manifest.json"

    advanced, rows = et.run(ws, out, manifest_path, min_age_sec=0)
    assert (advanced, rows) == (1, 1)  # only the good line before the tear
    manifest = json.loads(manifest_path.read_text())
    assert manifest[gz.name]["lines"] == 1  # did not advance past the torn line

    data = _read_csv_gz(out / "executions_20260820.csv.gz")
    assert len(data) == 2  # header + 1

    # Re-running unchanged finds nothing new (still torn).
    advanced2, rows2 = et.run(ws, out, manifest_path, min_age_sec=0)
    assert (advanced2, rows2) == (0, 0)

    # The recorder rewrites the file with the line completed and closed out
    # cleanly (as it would once the process could flush again).
    fixed = exec_msg(2.0, [exe(2, "SELL", 103.0, 0.05, "2026-08-20T00:00:03.0000000Z")])
    _write_gz(gz, [good, fixed])
    _age_file(gz, 120)

    advanced3, rows3 = et.run(ws, out, manifest_path, min_age_sec=0)
    assert (advanced3, rows3) == (1, 1)  # picks up the now-complete second line
    data = _read_csv_gz(out / "executions_20260820.csv.gz")
    assert len(data) == 3  # header + 2, first line never duplicated


def test_truncated_gzip_tail_is_tolerated(tmp_path):
    ws = tmp_path / "data" / "ws"
    out = tmp_path / "data" / "tape"
    gz = ws / "FX_BTC_JPY_20260820_050759.jsonl.gz"
    lines = [exec_msg(float(i), [exe(i, "BUY", 100.0 + i, 0.01,
                                     f"2026-08-20T00:00:{i:02d}.0000000Z")])
             for i in range(50)]
    _write_gz(gz, lines)
    raw = gz.read_bytes()
    gz.write_bytes(raw[: len(raw) // 2])  # simulate a killed-mid-flush recorder
    _age_file(gz, 120)
    manifest_path = out / "manifest.json"

    advanced, rows = et.run(ws, out, manifest_path, min_age_sec=0)
    # Whatever decompressed cleanly before the cut is kept; nothing crashes.
    assert rows > 0
    assert rows < 50
    out_files = list(out.glob("*.csv.gz"))
    assert out_files
    data = _read_csv_gz(out_files[0])
    assert len(data) == rows + 1  # header + extracted rows


def test_non_executions_only_file_produces_no_output(tmp_path):
    ws = tmp_path / "data" / "ws"
    out = tmp_path / "data" / "tape"
    gz = ws / "FX_BTC_JPY_20260820_050759.jsonl.gz"
    _write_gz(gz, [subscribe_ack(), board_msg(1.0), ticker_msg(1.1)])
    _age_file(gz, 120)

    advanced, rows = et.run(ws, out, out / "manifest.json", min_age_sec=0)
    assert advanced == 1  # the file was fully read...
    assert rows == 0      # ...but nothing executions-shaped was in it
    assert not out.exists() or not list(out.glob("*.csv.gz"))


def test_missing_ws_dir_is_a_quiet_noop(tmp_path):
    rc = et.main(["--ws-dir", str(tmp_path / "no-such-dir"),
                 "--out-dir", str(tmp_path / "tape")])
    assert rc == 0

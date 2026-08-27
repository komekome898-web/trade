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


def full_ticker_msg(rts, timestamp, bid, ask, bid_size, ask_size):
    """Real-shaped lightning_ticker payload (subset of live fields)."""
    return {"rts": rts, "m": {"jsonrpc": "2.0", "method": "channelMessage",
                              "params": {"channel": "lightning_ticker_FX_BTC_JPY",
                                        "message": {
                                            "product_code": "FX_BTC_JPY",
                                            "state": "RUNNING",
                                            "timestamp": timestamp,
                                            "tick_id": 1,
                                            "best_bid": bid, "best_ask": ask,
                                            "best_bid_size": bid_size,
                                            "best_ask_size": ask_size,
                                            "ltp": bid}}}}


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

    advanced, rows, ticker_rows, _ = et.run(ws, out, out / "manifest.json", min_age_sec=0)
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

    advanced, rows, ticker_rows, _ = et.run(ws, out, out / "manifest.json")  # default min_age_sec=60
    assert (advanced, rows, ticker_rows) == (0, 0, 0)
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

    advanced1, rows1, _, _ = et.run(ws, out, manifest_path, min_age_sec=0)
    assert (advanced1, rows1) == (1, 2)

    manifest = json.loads(manifest_path.read_text())
    assert manifest[gz.name]["lines"] == 2

    # Re-run with nothing new: the file is unchanged -> zero rows written,
    # zero files advanced (manifest already covers every line).
    advanced2, rows2, _, _ = et.run(ws, out, manifest_path, min_age_sec=0)
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

    advanced, rows, _, _ = et.run(ws, out, manifest_path, min_age_sec=0)
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

    advanced, rows, _, _ = et.run(ws, out, manifest_path, min_age_sec=0)
    assert (advanced, rows) == (1, 1)  # only the good line before the tear
    manifest = json.loads(manifest_path.read_text())
    assert manifest[gz.name]["lines"] == 1  # did not advance past the torn line

    data = _read_csv_gz(out / "executions_20260820.csv.gz")
    assert len(data) == 2  # header + 1

    # Re-running unchanged finds nothing new (still torn).
    advanced2, rows2, _, _ = et.run(ws, out, manifest_path, min_age_sec=0)
    assert (advanced2, rows2) == (0, 0)

    # The recorder rewrites the file with the line completed and closed out
    # cleanly (as it would once the process could flush again).
    fixed = exec_msg(2.0, [exe(2, "SELL", 103.0, 0.05, "2026-08-20T00:00:03.0000000Z")])
    _write_gz(gz, [good, fixed])
    _age_file(gz, 120)

    advanced3, rows3, _, _ = et.run(ws, out, manifest_path, min_age_sec=0)
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

    advanced, rows, _, _ = et.run(ws, out, manifest_path, min_age_sec=0)
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

    advanced, rows, ticker_rows, _ = et.run(ws, out, out / "manifest.json", min_age_sec=0)
    assert advanced == 1  # the file was fully read...
    assert rows == 0      # ...but nothing executions-shaped was in it
    assert not out.exists() or not list(out.glob("*.csv.gz"))


def test_missing_ws_dir_is_a_quiet_noop(tmp_path):
    rc = et.main(["--ws-dir", str(tmp_path / "no-such-dir"),
                 "--out-dir", str(tmp_path / "tape")])
    assert rc == 0


# ---- ticker extraction ------------------------------------------------------
def test_ticker_columns_dedup_and_date_partitioning(tmp_path):
    ws = tmp_path / "data" / "ws"
    out = tmp_path / "data" / "tape"
    gz = ws / "FX_BTC_JPY_20260820_050759.jsonl.gz"
    _write_gz(gz, [
        subscribe_ack(),
        board_msg(1.0),
        ticker_msg(1.05),  # no best_bid/ask fields -> skipped, not a row
        full_ticker_msg(1.1, "2026-08-20T23:59:59.0000000Z",
                        100.0, 101.0, 0.5, 0.6),
        # identical quote -> dropped (only depth/ltp churn on the exchange)
        full_ticker_msg(1.2, "2026-08-20T23:59:59.5000000Z",
                        100.0, 101.0, 0.5, 0.6),
        # size change alone IS a quote change
        full_ticker_msg(1.3, "2026-08-21T00:00:00.2000000Z",
                        100.0, 101.0, 0.5, 0.7),
        # price change, next UTC day -> lands in the 20260821 file
        full_ticker_msg(1.4, "2026-08-21T00:00:01.0000000Z",
                        100.5, 101.0, 0.5, 0.7),
    ])
    _age_file(gz, 120)

    advanced, exec_rows, ticker_rows, _ = et.run(ws, out, out / "manifest.json",
                                              min_age_sec=0)
    assert advanced == 1
    assert exec_rows == 0
    assert ticker_rows == 3  # 4 well-formed tickers, 1 duplicate quote dropped

    files = sorted(p.name for p in out.glob("ticker_*.csv.gz"))
    assert files == ["ticker_20260820.csv.gz", "ticker_20260821.csv.gz"]

    d20 = _read_csv_gz(out / "ticker_20260820.csv.gz")
    assert d20[0] == et.TICKER_FIELDS == ["ts", "best_bid", "best_ask",
                                          "best_bid_size", "best_ask_size"]
    assert d20[1:] == [["2026-08-20T23:59:59.0000000Z", "100.0", "101.0", "0.5", "0.6"]]

    d21 = _read_csv_gz(out / "ticker_20260821.csv.gz")
    assert d21[1:] == [
        ["2026-08-21T00:00:00.2000000Z", "100.0", "101.0", "0.5", "0.7"],
        ["2026-08-21T00:00:01.0000000Z", "100.5", "101.0", "0.5", "0.7"],
    ]


def test_ticker_dedup_survives_rerun_on_a_grown_file(tmp_path):
    ws = tmp_path / "data" / "ws"
    out = tmp_path / "data" / "tape"
    gz = ws / "FX_BTC_JPY_20260820_050759.jsonl.gz"
    _write_gz(gz, [full_ticker_msg(1.0, "2026-08-20T00:00:00.0000000Z",
                                   100.0, 101.0, 0.5, 0.6)])
    _age_file(gz, 120)
    manifest_path = out / "manifest.json"

    _, _, t1, _ = et.run(ws, out, manifest_path, min_age_sec=0)
    assert t1 == 1

    # The recorder appends the SAME quote again (new gzip member): the
    # last_quote stored in the manifest must suppress it across runs.
    with gzip.open(gz, "at", encoding="utf-8") as f:
        f.write(json.dumps(full_ticker_msg(2.0, "2026-08-20T00:00:05.0000000Z",
                                           100.0, 101.0, 0.5, 0.6)) + "\n")
        f.write(json.dumps(full_ticker_msg(2.1, "2026-08-20T00:00:06.0000000Z",
                                           102.0, 103.0, 0.5, 0.6)) + "\n")
    _age_file(gz, 120)

    _, _, t2, _ = et.run(ws, out, manifest_path, min_age_sec=0)
    assert t2 == 1  # only the changed quote

    data = _read_csv_gz(out / "ticker_20260820.csv.gz")
    assert len(data) == 3  # header + 2 quote changes


def test_old_manifest_backfills_ticker_without_duplicating_executions(tmp_path):
    ws = tmp_path / "data" / "ws"
    out = tmp_path / "data" / "tape"
    gz = ws / "FX_BTC_JPY_20260820_050759.jsonl.gz"
    _write_gz(gz, [
        exec_msg(1.0, [exe(1, "BUY", 100.0, 0.01, "2026-08-20T00:00:00.0000000Z")]),
        full_ticker_msg(1.1, "2026-08-20T00:00:00.5000000Z", 100.0, 101.0, 0.5, 0.6),
        exec_msg(1.2, [exe(2, "SELL", 101.0, 0.02, "2026-08-20T00:00:01.0000000Z")]),
        full_ticker_msg(1.3, "2026-08-20T00:00:01.5000000Z", 100.5, 101.0, 0.5, 0.6),
    ])
    _age_file(gz, 120)
    manifest_path = out / "manifest.json"

    # Simulate the pre-ticker deployment: executions already extracted, and
    # the manifest is in the OLD format ({"lines", "mtime"} only).
    advanced0, exec0, ticker0, _ = et.run(ws, out, manifest_path, min_age_sec=0)
    assert (advanced0, exec0) == (1, 2)
    manifest = json.loads(manifest_path.read_text())
    old_entry = {"lines": manifest[gz.name]["lines"],
                 "mtime": manifest[gz.name]["mtime"]}
    manifest_path.write_text(json.dumps({gz.name: old_entry}))
    for p in out.glob("ticker_*.csv.gz"):
        p.unlink()  # as if ticker extraction never existed

    # First run after the upgrade: tickers are backfilled from line 0,
    # executions are NOT re-emitted.
    advanced1, exec1, ticker1, _ = et.run(ws, out, manifest_path, min_age_sec=0)
    assert advanced1 == 1
    assert exec1 == 0
    assert ticker1 == 2

    exec_data = _read_csv_gz(out / "executions_20260820.csv.gz")
    assert len(exec_data) == 3  # header + 2, no duplicates

    ticker_data = _read_csv_gz(out / "ticker_20260820.csv.gz")
    assert len(ticker_data) == 3  # header + 2 backfilled quotes

    # Manifest is now in the new format and a further rerun is a no-op.
    manifest = json.loads(manifest_path.read_text())
    assert manifest[gz.name]["ticker_lines"] == manifest[gz.name]["lines"]
    advanced2, exec2, ticker2, _ = et.run(ws, out, manifest_path, min_age_sec=0)
    assert (advanced2, exec2, ticker2) == (0, 0, 0)


# ---- board depth extraction (--board-top, on-demand) ------------------------
def board_snapshot_msg(rts, bids, asks, channel="lightning_board_snapshot_FX_BTC_JPY"):
    return {"rts": rts, "m": {"jsonrpc": "2.0", "method": "channelMessage",
                              "params": {"channel": channel,
                                        "message": {
                                            "mid_price": 100.5,
                                            "bids": [{"price": p, "size": s} for p, s in bids],
                                            "asks": [{"price": p, "size": s} for p, s in asks]}}}}


def board_diff_msg(rts, bids, asks, channel="lightning_board_FX_BTC_JPY"):
    return {"rts": rts, "m": {"jsonrpc": "2.0", "method": "channelMessage",
                              "params": {"channel": channel,
                                        "message": {
                                            "mid_price": 100.5,
                                            "bids": [{"price": p, "size": s} for p, s in bids],
                                            "asks": [{"price": p, "size": s} for p, s in asks]}}}}


def test_board_top_reconstruction_sampling_and_columns(tmp_path):
    ws = tmp_path / "data" / "ws"
    out = tmp_path / "data" / "tape"
    gz = ws / "FX_BTC_JPY_19700101_000000.jsonl.gz"
    _write_gz(gz, [
        subscribe_ack(),
        # diff BEFORE any snapshot: must be discarded, second 9 emits no row
        board_diff_msg(9.5, [(999.0, 9.0)], []),
        board_snapshot_msg(10.2, [(100.0, 1.0), (99.0, 2.0), (98.0, 3.0)],
                           [(101.0, 1.5), (102.0, 2.5)]),
        # delete bid 99 (size 0), insert ask 103
        board_diff_msg(10.7, [(99.0, 0.0)], [(103.0, 4.0)]),
        # next second: new 3rd-best bid
        board_diff_msg(11.3, [(97.0, 5.0)], []),
    ])
    _age_file(gz, 120)

    rc = et.main(["--ws-dir", str(ws), "--out-dir", str(out),
                 "--min-age-sec", "0", "--board-top", "3"])
    assert rc == 0

    out_files = sorted(p.name for p in out.glob("board_*.csv.gz"))
    assert out_files == ["board_top3_19700101.csv.gz"]
    data = _read_csv_gz(out / "board_top3_19700101.csv.gz")
    assert data[0] == ["ts",
                       "bid_px_1", "bid_px_2", "bid_px_3",
                       "bid_sz_1", "bid_sz_2", "bid_sz_3",
                       "ask_px_1", "ask_px_2", "ask_px_3",
                       "ask_sz_1", "ask_sz_2", "ask_sz_3"]
    # Second 10: last state = after the size-0 delete; bid 99 gone, only two
    # bid levels left (third pair empty), asks ascending incl. inserted 103.
    assert data[1] == ["1970-01-01T00:00:10Z",
                       "100.0", "98.0", "",
                       "1.0", "3.0", "",
                       "101.0", "102.0", "103.0",
                       "1.5", "2.5", "4.0"]
    # Second 11: bid 97 arrived, bids in descending price order.
    assert data[2] == ["1970-01-01T00:00:11Z",
                       "100.0", "98.0", "97.0",
                       "1.0", "3.0", "5.0",
                       "101.0", "102.0", "103.0",
                       "1.5", "2.5", "4.0"]
    assert len(data) == 3  # no row for pre-snapshot second 9

    # Idempotent: rerun with the same flag emits nothing new.
    _, _, _, board2 = et.run(ws, out, out / "manifest.json",
                             min_age_sec=0, board_top=3)
    assert board2 == 0
    assert len(_read_csv_gz(out / "board_top3_19700101.csv.gz")) == 3


def test_run_without_board_top_keeps_board_backfillable(tmp_path):
    ws = tmp_path / "data" / "ws"
    out = tmp_path / "data" / "tape"
    gz = ws / "FX_BTC_JPY_19700101_000000.jsonl.gz"
    _write_gz(gz, [
        exec_msg(1.0, [exe(1, "BUY", 100.0, 0.01, "1970-01-01T00:00:01.0000000Z")]),
        board_snapshot_msg(1.2, [(100.0, 1.0)], [(101.0, 2.0)]),
        board_diff_msg(2.4, [(99.0, 3.0)], []),
    ])
    _age_file(gz, 120)
    manifest_path = out / "manifest.json"

    # Default run: executions extracted, board cursor NOT created.
    advanced0, exec0, _, board0 = et.run(ws, out, manifest_path, min_age_sec=0)
    assert (advanced0, exec0, board0) == (1, 1, 0)
    entry = json.loads(manifest_path.read_text())[gz.name]
    assert "board_lines" not in entry
    assert not list(out.glob("board_*.csv.gz"))

    # Backfill later with --board-top: board rows appear, executions do not
    # re-emit.
    advanced1, exec1, _, board1 = et.run(ws, out, manifest_path,
                                         min_age_sec=0, board_top=2)
    assert (advanced1, exec1) == (1, 0)
    assert board1 == 2  # seconds 1 and 2
    entry = json.loads(manifest_path.read_text())[gz.name]
    assert entry["board_lines"] == entry["lines"]
    assert entry["board_last_sec"] == 2
    exec_data = _read_csv_gz(out / "executions_19700101.csv.gz")
    assert len(exec_data) == 2  # header + 1, no duplicate

    # A later default run (file grew) must PRESERVE the board cursors...
    with gzip.open(gz, "at", encoding="utf-8") as f:
        f.write(json.dumps(exec_msg(3.0, [exe(2, "SELL", 101.0, 0.02,
                                              "1970-01-01T00:00:03.0000000Z")])) + "\n")
        f.write(json.dumps(board_diff_msg(3.5, [(98.0, 4.0)], []))) 
        f.write("\n")
    _age_file(gz, 120)
    advanced2, exec2, _, board2 = et.run(ws, out, manifest_path, min_age_sec=0)
    assert (advanced2, exec2, board2) == (1, 1, 0)
    entry = json.loads(manifest_path.read_text())[gz.name]
    assert entry["board_last_sec"] == 2  # untouched by the no-board run

    # ...so a following --board-top run picks up ONLY the new second.
    advanced3, _, _, board3 = et.run(ws, out, manifest_path,
                                     min_age_sec=0, board_top=2)
    assert board3 == 1
    board_data = _read_csv_gz(out / "board_top2_19700101.csv.gz")
    assert [r[0] for r in board_data[1:]] == ["1970-01-01T00:00:01Z",
                                              "1970-01-01T00:00:02Z",
                                              "1970-01-01T00:00:03Z"]


def test_board_top_leaves_exec_and_ticker_outputs_identical(tmp_path):
    lines = [
        subscribe_ack(),
        exec_msg(1.0, [exe(1, "BUY", 100.0, 0.01, "1970-01-01T00:00:01.0000000Z")]),
        board_snapshot_msg(1.2, [(100.0, 1.0)], [(101.0, 2.0)]),
        full_ticker_msg(1.3, "1970-01-01T00:00:01.3000000Z", 100.0, 101.0, 0.5, 0.6),
        board_diff_msg(2.4, [(99.0, 3.0)], []),
        exec_msg(2.5, [exe(2, "SELL", 101.0, 0.02, "1970-01-01T00:00:02.5000000Z")]),
        full_ticker_msg(2.6, "1970-01-01T00:00:02.6000000Z", 100.5, 101.0, 0.5, 0.6),
    ]
    outputs = {}
    for label, board_top in (("plain", 0), ("board", 5)):
        ws = tmp_path / label / "ws"
        out = tmp_path / label / "tape"
        gz = ws / "FX_BTC_JPY_19700101_000000.jsonl.gz"
        _write_gz(gz, lines)
        _age_file(gz, 120)
        et.run(ws, out, out / "manifest.json", min_age_sec=0,
               board_top=board_top)
        outputs[label] = {p.name: gzip.decompress(p.read_bytes())
                          for p in out.glob("*.csv.gz")}

    plain, board = outputs["plain"], outputs["board"]
    assert set(plain) == {"executions_19700101.csv.gz", "ticker_19700101.csv.gz"}
    assert set(board) == set(plain) | {"board_top5_19700101.csv.gz"}
    # executions/ticker payloads byte-identical with and without --board-top
    for name in plain:
        assert board[name] == plain[name]

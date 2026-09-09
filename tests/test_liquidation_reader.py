"""清算記録の読み手(src/bot/research/liquidations.py)。

固定するのは一点: **走っている記録器のファイルを読んでも、あるデータを無いと言わない。**
2026-09-09、素直に `gzip.open` した結果 11.6KB の BitMEX ファイルが「0 行」に見えた
(実際には 597 行あった)。あれを二度と起こさない。
"""
from __future__ import annotations

import gzip
import json
import zlib

import pytest

from bot.research.liquidations import read_rows, read_text, summarise


def _write_live_file(path, rows):
    """**閉じていない** gzip を作る = 記録中のファイルのコピーと同じ状態。

    1 行ごとに Z_SYNC_FLUSH で流すが、終端マーカーは書かない。
    """
    comp = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)
    blob = b""
    for row in rows:
        blob += comp.compress(
            (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8"))
        blob += comp.flush(zlib.Z_SYNC_FLUSH)
    path.write_bytes(blob)              # comp.flush(Z_FINISH) を**わざと呼ばない**
    return path


def _rows(n, start=1_000_000):
    return [{"venue": "okx", "recv_us": start + i * 1_000_000, "raw": {"i": i}}
            for i in range(n)]


def test_a_live_unclosed_file_is_read_in_full(tmp_path):
    """終端マーカーが無いのは**破損ではなく、開いているだけ**。全行読めること。"""
    path = _write_live_file(tmp_path / "okx_20260908.jsonl.gz", _rows(50))

    with pytest.raises(EOFError):       # 素直に読むと落ちるファイルであることを確認
        gzip.open(path, "rt", encoding="utf-8").read()

    res = read_rows(path)
    assert len(res.rows) == 50
    assert res.bad_lines == 0
    assert [r["raw"]["i"] for r in res.rows] == list(range(50))


def test_a_half_written_last_line_is_dropped_not_counted_as_damage(tmp_path):
    """最後の 1 行が書きかけなのは正常。**途中**が壊れているのとは区別する。"""
    path = tmp_path / "bitmex_20260908.jsonl.gz"
    comp = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)
    body = "".join(json.dumps(r) + "\n" for r in _rows(3))
    body += '{"venue": "bitmex", "recv_u'      # 書きかけ
    path.write_bytes(comp.compress(body.encode()) + comp.flush(zlib.Z_SYNC_FLUSH))

    res = read_rows(path)
    assert len(res.rows) == 3
    assert res.truncated_tail is True
    assert res.bad_lines == 0           # 末尾は「壊れた行」に数えない


def test_damage_in_the_middle_is_counted(tmp_path):
    """末尾以外の壊れた行は、黙って捨てずに数える。"""
    path = tmp_path / "bybit_20260908.jsonl.gz"
    comp = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)
    body = (json.dumps(_rows(1)[0]) + "\n"
            + "{not json\n"
            + json.dumps(_rows(1)[0]) + "\n")
    path.write_bytes(comp.compress(body.encode()) + comp.flush(zlib.Z_SYNC_FLUSH))

    res = read_rows(path)
    assert len(res.rows) == 2
    assert res.bad_lines == 1
    assert res.truncated_tail is False


def test_a_properly_closed_file_still_reads(tmp_path):
    """記録器が閉じたあとの普通の gzip も、同じ読み手で読めること。"""
    path = tmp_path / "okx_20260909.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for row in _rows(10):
            fh.write(json.dumps(row) + "\n")
    assert len(read_rows(path).rows) == 10
    assert "recv_us" in read_text(path)


def test_multiple_gzip_members_are_all_read(tmp_path):
    """再接続で開き直すと gzip メンバが複数連なる。後ろのメンバも読むこと。"""
    path = tmp_path / "okx_20260910.jsonl.gz"
    blob = b""
    for chunk in (_rows(4), _rows(3, start=9_000_000)):
        comp = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)
        body = "".join(json.dumps(r) + "\n" for r in chunk).encode()
        blob += comp.compress(body) + comp.flush()        # このメンバは閉じる
    path.write_bytes(blob)
    assert len(read_rows(path).rows) == 7


def test_summary_reports_health_without_judging_the_market(tmp_path):
    """点検は行数・期間・逆行・重複・欠測候補まで。相場の話はしない。"""
    rows = _rows(5)
    rows.append({"venue": "okx", "recv_us": rows[-1]["recv_us"] + 3_600_000_000,
                 "raw": {"i": 99}})                        # 1 時間の空白
    path = _write_live_file(tmp_path / "okx_20260911.jsonl.gz", rows)

    s = summarise(path, gap_sec=900.0)
    assert s.venue == "okx"
    assert s.rows == 6
    assert s.backwards == 0 and s.duplicate_recv_us == 0
    assert len(s.gaps) == 1 and s.gaps[0][1] == 3600
    assert s.span_utc is not None and len(s.span_utc) == 2


def test_duplicate_receive_times_are_surfaced(tmp_path):
    """二重書き込みが起きたら、同じ受信時刻が並ぶ。見逃さないこと。"""
    rows = _rows(4)
    rows.append(dict(rows[1]))                             # 同じ recv_us
    path = _write_live_file(tmp_path / "okx_20260912.jsonl.gz", rows)
    s = summarise(path)
    assert s.duplicate_recv_us == 1
    assert s.backwards == 1                                # 並びも巻き戻る

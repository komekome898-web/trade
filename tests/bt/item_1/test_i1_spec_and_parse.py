"""V1 / V2 / V4 adversary: the declaration is read strictly, a file that
does not match its declaration is refused with its line, and the sha256 is
of the bytes on disk (the same bytes that were parsed).

Declaration grid: for a valid spec of each kind, every key removed and every
key given a value of each wrong JSON type (str, int, bool, null, list,
object) -- required keys must refuse, and a wrong type must refuse. Parse
cases: one per rule in loader.py (compression both ways, header, row length,
blank cells, side map, number forms, book holes, JSON shapes, encoding).
Not in the grid: every wrong value of every nested key (the nested maps go
through the same `_choice` / `_text` / `_pos_int` checks, sampled below).
"""
from __future__ import annotations

import copy
import gzip
import hashlib
import json

import pytest

from bot.bt.data import DataError, ParseError, SpecError, load, parse_spec

TRADE = {"format": "csv", "header": True, "delimiter": ",", "kind": "trade", "symbol": "X", "asset": "crypto",
         "time": {"columns": ["t"], "unit": "iso", "tz": "UTC"},
         "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell"},
         "key": "id"}
BAR = {"format": "csv", "header": True, "delimiter": ",", "kind": "bar", "symbol": "X", "asset": "jpx",
       "time": {"columns": ["d", "hm"], "join": " ", "unit": "iso", "tz": "Asia/Tokyo"},
       "fields": {"open": "o", "high": "h", "low": "l", "close": "c", "volume": "v"},
       "bar": {"interval_s": 60, "label": "start"}, "key": "start"}
JSONL = {"format": "jsonl", "compression": "gzip", "kind": "liquidation", "symbol": "X", "asset": "crypto",
         "time": {"columns": ["a.T"], "unit": "ms", "tz": "UTC"}, "fields": {"px": "a.p", "qty": "a.q", "side": "a.S"},
         "side_map": {"SELL": "sell"}}
REQUIRED = {"format", "kind", "symbol", "asset", "time", "fields"}
# the documented type of each key (spec.py docstring), independent of the code: a
# value outside it must refuse; a value inside it is accepted only when it is the
# base's own value (another enum member / mapping would change the declaration)
VALID = {
    "format": lambda v, b: v == b["format"], "kind": lambda v, b: v == b["kind"],
    "asset": lambda v, b: v == b["asset"], "compression": lambda v, b: v == b["compression"],
    "symbol": lambda v, b: type(v) is str and v != "", "header": lambda v, b: v is b["header"],
    "delimiter": lambda v, b: v == b["delimiter"], "key": lambda v, b: v == b["key"],
    "time": lambda v, b: v == b["time"], "fields": lambda v, b: v == b["fields"],
    "side_map": lambda v, b: v == b["side_map"], "bar": lambda v, b: v == b["bar"],
}
WRONG = ["zz", 7, True, None, [1], {"a": 1}]


def cases():
    out = []
    for name, base in (("trade", TRADE), ("bar", BAR), ("jsonl", JSONL)):
        for key in base:
            s = copy.deepcopy(base)
            del s[key]
            must_refuse = key in REQUIRED or (base["format"] == "csv" and key in ("header", "delimiter")) \
                or (name == "bar" and key == "bar")
            out.append((f"{name}-del-{key}", s, must_refuse))
            for w in WRONG:
                s = copy.deepcopy(base)
                s[key] = w
                out.append((f"{name}-{key}={w!r}", s, not VALID[key](w, base)))
        s = copy.deepcopy(base)
        s["extra"] = 1
        out.append((f"{name}-unknown-key", s, True))
    return out


CASES = cases()


def test_declaration_grid_size():
    assert len(CASES) == 3 + 7 * (len(TRADE) + len(BAR) + len(JSONL))


@pytest.mark.parametrize("cid,spec,must_refuse", CASES, ids=[c[0] for c in CASES])
def test_declaration(cid, spec, must_refuse):
    if must_refuse:
        with pytest.raises(SpecError):
            parse_spec(spec)
    else:
        parse_spec(spec)


@pytest.mark.parametrize("patch", [
    {"time": {"columns": ["t"], "unit": "iso", "tz": "UTC", "join": " "}},
    {"time": {"columns": ["a", "b"], "unit": "s", "join": " "}},
    {"time": {"columns": ["t"], "unit": "s", "tz": "Asia/Tokyo"}},
    {"time": {"columns": ["t"], "unit": "iso", "plausible_ns": [5, 1]}},
    {"fields": {"px": "price"}},
    {"fields": {"px": "price", "qty": "size", "bid": "b"}},
    {"side_map": {"BUY": "long"}},
    {"key": "start"},
    {"names": ["id", "t"]},
    {"delimiter": ",,"},
    {"bar": {"interval_s": 60, "label": "start"}},
])
def test_nested_declaration_errors(patch):
    s = copy.deepcopy(TRADE)
    s.update(patch)
    with pytest.raises(SpecError):
        parse_spec(s)


def _load(tmp, text=None, spec=TRADE, raw=None, name="f.csv"):
    (tmp / "backtest_data" / "x").mkdir(parents=True, exist_ok=True)
    p = tmp / "backtest_data" / "x" / name
    p.write_bytes(raw if raw is not None else text.encode("utf-8"))
    return load(str(tmp), [{"name": "d", "paths": [f"backtest_data/x/{name}"], "spec": spec}])


GOOD = "id,t,price,size,side\n1,2026-01-05T00:00:00Z,100,1,BUY\n"


@pytest.mark.parametrize("text", [
    "id,t,price,size\n1,2026-01-05T00:00:00Z,100,1\n",  # header lacks a declared column
    "id,t,price,size,side\n1,2026-01-05T00:00:00Z,100,1\n",  # short row
    "id,t,price,size,side\n1,2026-01-05T00:00:00Z,100,1,BUY,x\n",  # long row
    "id,t,price,size,side\n1,,100,1,BUY\n",  # blank time
    "id,t,price,size,side\n1,2026-01-05T00:00:00Z,,1,BUY\n",  # blank price
    "id,t,price,size,side\n1,2026-01-05T00:00:00Z,100,1,HOLD\n",  # side not in the map
    "id,t,price,size,side\n1,2026-01-05T00:00:00Z,nan,1,BUY\n",
    "id,t,price,size,side\n1,2026-01-05T00:00:00Z,inf,1,BUY\n",
    "id,t,price,size,side\n1,2026-01-05T00:00:00Z,1_00,1,BUY\n",
    "id,t,price,size,side\n1,2026-01-05T00:00:00Z,0x10,1,BUY\n",
    "id,t,price,size,side\n1,2026-01-05T00:00:00Z,100,0,BUY\n",  # size 0: the core's trade refuses
    "id,t,price,size,side\n1,2026-01-05T00:00:00Z,-5,1,BUY\n",
    "id,id,price,size,side\n1,2026-01-05T00:00:00Z,100,1,BUY\n",  # repeated header name
    "",  # no header at all
    'id,t,price,size,side\n1,"2026-01-05T00:00:00Z,100,1,BUY\n',  # broken quoting
])
def test_rows_that_do_not_match_are_refused(tmp_path, text):
    with pytest.raises(DataError):
        _load(tmp_path, text)


def test_bom_and_crlf_are_read(tmp_path):
    res = _load(tmp_path, "﻿" + GOOD.replace("\n", "\r\n"))
    assert res.records("d")[0]["t_ns"] == 1767571200 * 10**9


def test_compression_must_agree_with_the_bytes(tmp_path):
    with pytest.raises(ParseError):
        _load(tmp_path, raw=gzip.compress(GOOD.encode(), mtime=0))  # gzip, declared none
    s = dict(TRADE, compression="gzip")
    with pytest.raises(ParseError):
        _load(tmp_path, GOOD, spec=s, name="g.csv")  # declared gzip, plain
    with pytest.raises(ParseError):
        _load(tmp_path, raw=b"\x1f\x8b\x08\x00broken", spec=s, name="h.csv")
    with pytest.raises(ParseError):
        _load(tmp_path, raw=b"id,t\n\xff\xfe\n", name="i.csv")  # not UTF-8


def test_book_levels(tmp_path):
    spec = {"format": "csv", "header": True, "delimiter": ",", "kind": "book", "symbol": "X", "asset": "crypto",
            "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"},
            "fields": {"levels": 2, "bid_px": ["bp1", "bp2"], "bid_sz": ["bs1", "bs2"], "ask_px": ["ap1", "ap2"],
                       "ask_sz": ["as1", "as2"]}}
    head = "ts,bp1,bp2,bs1,bs2,ap1,ap2,as1,as2\n"
    ok = _load(tmp_path, head + "2026-01-05T00:00:00Z,10,,1,,11,12,1,2\n", spec=spec)
    assert ok.records("d") == [{"t_ns": 1767571200 * 10**9, "bids": [[10.0, 1.0]], "asks": [[11.0, 1.0], [12.0, 2.0]]}]
    for i, row in enumerate(["2026-01-05T00:00:00Z,,10,,1,11,12,1,2",  # a level after a blank one
                             "2026-01-05T00:00:00Z,10,9,1,,11,12,1,2",  # price without size
                             "2026-01-05T00:00:00Z,10,11,1,1,11,12,1,2"]):  # bids not descending
        with pytest.raises(DataError):
            _load(tmp_path, head + row + "\n", spec=spec, name=f"b{i}.csv")


def test_jsonl_shapes(tmp_path):
    def gz(lines):
        return gzip.compress(("\n".join(lines) + "\n").encode(), mtime=0)
    ok = _load(tmp_path, raw=gz(['{"a":{"T":1767571200123,"p":"96000.5","q":0.25,"S":"SELL"}}']), spec=JSONL, name="j.gz")
    assert ok.records("d") == [{"t_ns": 1767571200123000000, "px": 96000.5, "qty": 0.25, "side": "sell"}]
    # a JSON number keeps its written digits (read as a Decimal, never a binary float)
    ok2 = _load(tmp_path, raw=gz(['{"a":{"T":1767571200123.456789,"p":"1","q":"1","S":"SELL"}}']), spec=JSONL, name="k.gz")
    assert ok2.records("d")[0]["t_ns"] == 1767571200123456789
    for i, line in enumerate(['{"a":{"T":1767571200123.0000001,"p":"1","q":"1","S":"SELL"}}',  # sub-ns digits
                              '{"a":{"p":"1","q":"1","S":"SELL"}}',  # no time
                              '[1,2]', '{"a":{"T":1767571200123,"p":NaN,"q":"1","S":"SELL"}}',
                              '{"a":{"T":true,"p":"1","q":"1","S":"SELL"}}', 'not json']):
        with pytest.raises(DataError):
            _load(tmp_path, raw=gz([line]), spec=JSONL, name=f"j{i}.gz")


def test_hashes_are_of_the_bytes_on_disk(tmp_path):
    raw = gzip.compress(GOOD.encode(), mtime=0)
    res = _load(tmp_path, raw=raw, spec=dict(TRADE, compression="gzip"), name="z.csv.gz")
    [f] = res.files()
    assert f.sha256 == hashlib.sha256(raw).hexdigest() and f.size == len(raw)
    assert res.hashes() == {"backtest_data/x/z.csv.gz": hashlib.sha256(raw).hexdigest()}
    man = res.manifest()
    assert man["files"][0]["sha256"] == f.sha256 and man["datasets"]["d"]["rows"] == 1
    json.dumps(man)  # JSON-able for the run record
    # a later change of the file does not change what was recorded for this load
    (tmp_path / "backtest_data" / "x" / "z.csv.gz").write_bytes(b"changed")
    assert res.files()[0].sha256 == hashlib.sha256(raw).hexdigest()


def test_same_bytes_same_hash_other_bytes_other_hash(tmp_path):
    a = _load(tmp_path, GOOD, name="a.csv").files()[0].sha256
    b = _load(tmp_path, GOOD, name="b.csv").files()[0].sha256
    c = _load(tmp_path, GOOD.replace("100", "101"), name="c.csv").files()[0].sha256
    assert a == b != c


def test_synthetic_rows_are_reported_and_need_a_policy(tmp_path):
    from bot.bt.data import UnresolvedAnomalyError
    spec = {"format": "csv", "header": True, "delimiter": ",", "kind": "bar", "symbol": "X", "asset": "crypto",
            "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"},
            "fields": {"open": "c", "high": "c", "low": "c", "close": "c", "volume": "v"},
            "bar": {"interval_s": 60, "label": "start", "session": "24x7"}, "key": "start",
            "synthetic": {"column": "syn", "values": ["1"]}}
    text = ("ts,c,v,syn\n2026-01-05T00:00:00Z,10,1,0\n2026-01-05T00:01:00Z,10,0,1\n"
            "2026-01-05T00:02:00Z,11,1,0\n")
    res = _load(tmp_path, text, spec=spec)
    assert [(a["kind"], a["line"]) for a in res.anomalies("d")] == [("synthetic", 3)]
    assert "synthetic" in res.checks("d")
    with pytest.raises(UnresolvedAnomalyError):
        res.events("d")
    assert len(res.events("d", {"synthetic": "drop"})) == 2
    assert len(res.events("d", {"synthetic": "accept"})) == 3
    assert res.manifest()["datasets"]["d"]["resolution"] == {"synthetic": "accept"}
    bad = dict(spec, synthetic={"column": "syn", "values": []})
    with pytest.raises(SpecError):
        parse_spec(bad)


def test_streams_feed_the_core_engine(tmp_path):
    from bot.bt.core import CoreEngine, Strategy

    class Seen(Strategy):
        def __init__(self):
            self.types = []

        def on_event(self, event, ctx):
            self.types.append((event.event_type.value, int(event.received_time_ns)))

    (tmp_path / "backtest_data" / "x").mkdir(parents=True)
    (tmp_path / "backtest_data" / "x" / "t.csv").write_text(
        "id,t,price,size,side\n1,2026-01-05T00:00:01Z,100,1,BUY\n1,2026-01-05T00:00:01Z,100,1,BUY\n")
    (tmp_path / "backtest_data" / "x" / "b.csv").write_text("ts,c,v\n2026-01-05T00:00:00Z,10,1\n")
    bar = {"format": "csv", "header": True, "delimiter": ",", "kind": "bar", "symbol": "X", "asset": "crypto",
           "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"},
           "fields": {"open": "c", "high": "c", "low": "c", "close": "c", "volume": "v"},
           "bar": {"interval_s": 60, "label": "start"}}
    res = load(str(tmp_path), [{"name": "tr", "paths": ["backtest_data/x/t.csv"], "spec": TRADE},
                               {"name": "bars", "paths": ["backtest_data/x/b.csv"], "spec": bar}])
    with pytest.raises(DataError):
        res.streams()  # the duplicate has no named policy
    with pytest.raises(SpecError):
        res.streams({"typo": {"duplicate": "drop"}})
    streams = res.streams({"tr": {"duplicate": "drop"}})
    s = Seen()
    CoreEngine(s, streams, time_span_ns=(1767571200 * 10**9, 1767571260 * 10**9)).run()
    # the bar reaches the strategy at its close (start + 60 s), after the trade
    assert s.types == [("TRADE", 1767571201 * 10**9), ("BAR", 1767571260 * 10**9)]


def test_a_null_or_blank_id_is_no_id(tmp_path):
    spec = {"format": "jsonl", "kind": "trade", "symbol": "X", "asset": "crypto",
            "time": {"columns": ["T"], "unit": "ms", "tz": "UTC"}, "fields": {"id": "i", "px": "p", "qty": "q"},
            "key": "id"}
    lines = ['{"T":1767571200000,"i":null,"p":"1","q":"1"}', '{"T":1767571200001,"i":null,"p":"2","q":"1"}',
             '{"T":1767571200002,"i":"","p":"3","q":"1"}', '{"T":1767571200003,"i":7,"p":"4","q":"1"}']
    res = _load(tmp_path, "\n".join(lines) + "\n", spec=spec, name="n.jsonl")
    assert [r["id"] for r in res.records("d")] == ["", "", "", "7"]
    assert res.anomalies("d") == []  # two null ids are not one repeated key

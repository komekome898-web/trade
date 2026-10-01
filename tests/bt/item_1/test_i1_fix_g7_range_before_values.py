"""G-7 of K1 stage G (delegation docs/DATA/delegations/20261001_k1_stage_g_close.md §4, the critic's [ask] 1 in
docs/AUDITOR/VERDICTS/2026-10-01_k1_stage_g_close.md): before the fix `loader._read_file` built every row -- every
declared field turned into a number and the core event made (`_build`) -- and only then asked whether the row's time
lies in `range_ns` (`_in_range`), so a row outside the range (and a row of a sealed file at or after the seal cut)
had its values read before it was thrown away. The critic's check: range [00:00, 00:02), the out-of-range 00:02 row
with open "XX" -> "ParseError ... line 4 field 'open': 'XX' is not a decimal number".

Rule after the fix: the row's time is read first; a row outside the range is skipped with its values unread (it is
still counted in rows_read, and its time is still read strictly); a kept row of a sealed file is checked against the
seal before its values are read. Synthetic files only, under pytest's tmp_path.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json

import pytest

import bot.bt.data.loader as L
from bot.bt.data import ParseError, SealedRangeError, TimeParseError, load
from bot.bt.data.stream import stream

NS = 1_000_000_000
T0 = 1514764800 * NS  # 2018-01-01T00:00:00Z
M = 60 * NS
BAR = {"format": "csv", "header": True, "delimiter": ",", "kind": "bar", "symbol": "X", "asset": "crypto",
       "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"},
       "fields": {"open": "o", "high": "h", "low": "l", "close": "c", "volume": "v"},
       "bar": {"interval_s": 60, "label": "start", "session": "24x7"}, "key": "start"}
TRADE = {"format": "csv", "header": True, "delimiter": ",", "kind": "trade", "symbol": "X", "asset": "crypto",
         "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"},
         "fields": {"px": "px", "qty": "qty", "side": "side"}}
JTRADE = {"format": "jsonl", "kind": "trade", "symbol": "X", "asset": "crypto",
          "time": {"columns": ["t"], "unit": "iso", "tz": "UTC"},
          "fields": {"px": "p", "qty": "q", "side": "s"}}
P = "backtest_data/x/f.csv"


def iso(t_ns):
    return dt.datetime.fromtimestamp(t_ns // NS, tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def put(tmp_path, text, rel=P):
    (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / rel).write_text(text)
    return str(tmp_path)


def bars(minutes, bad=()):
    """A bar file of the given minutes after T0; the minutes in `bad` carry open "XX"."""
    rows = ["ts,o,h,l,c,v"]
    for m in minutes:
        o = "XX" if m in bad else "1"
        rows.append(f"{iso(T0 + m * M)},{o},2,0.5,1.5,1")
    return "\n".join(rows) + "\n"


def test_the_critics_check_a_row_after_the_range_is_not_read_beyond_its_time(tmp_path):
    root = put(tmp_path, bars([0, 1, 2], bad=(2,)))
    r = load(root, [{"name": "d", "paths": [P], "spec": BAR, "range_ns": [T0, T0 + 2 * M]}])
    f = r.files()[0]
    assert (f.rows_read, f.rows_kept) == (3, 2)
    assert [x["start_ns"] for x in r.records("d")] == [T0, T0 + M]
    # without the range the same row is read and refused, as before
    with pytest.raises(ParseError, match="line 4 field 'open': 'XX' is not a decimal number"):
        load(root, [{"name": "d", "paths": [P], "spec": BAR}])


def test_a_row_before_the_range_is_not_read_beyond_its_time(tmp_path):
    root = put(tmp_path, bars([0, 1, 2, 3], bad=(0, 3)))
    r = load(root, [{"name": "d", "paths": [P], "spec": BAR, "range_ns": [T0 + M, T0 + 3 * M]}])
    assert (r.files()[0].rows_read, r.files()[0].rows_kept) == (4, 2)


def test_a_bar_labelled_by_its_end_is_judged_by_its_start_before_its_values(tmp_path):
    sp = {**BAR, "bar": {**BAR["bar"], "label": "end"}}
    # times written are bar ends: the bar ending at T0 + 3M starts at T0 + 2M and does not fit in [T0, T0 + 2M + 1)
    root = put(tmp_path, bars([1, 2, 3], bad=(3,)))
    r = load(root, [{"name": "d", "paths": [P], "spec": sp, "range_ns": [T0, T0 + 2 * M + 1]}])
    assert [x["start_ns"] for x in r.records("d")] == [T0, T0 + M]


def test_values_become_numbers_and_events_only_for_kept_rows(tmp_path, monkeypatch):
    root = put(tmp_path, bars(range(10)))
    calls = {"num": 0, "bar": 0}
    num, bar_cls = L._num, L.BarEvent

    def count_num(*a, **k):
        calls["num"] += 1
        return num(*a, **k)

    def count_bar(*a, **k):
        calls["bar"] += 1
        return bar_cls(*a, **k)

    monkeypatch.setattr(L, "_num", count_num)
    monkeypatch.setattr(L, "BarEvent", count_bar)
    r = load(root, [{"name": "d", "paths": [P], "spec": BAR, "range_ns": [T0 + 4 * M, T0 + 7 * M]}])
    assert r.files()[0].rows_kept == 3
    assert calls == {"num": 3 * 5, "bar": 3}, calls  # before the fix: 10 * 5 and 10


def test_the_time_of_a_row_outside_the_range_is_still_read_strictly(tmp_path):
    text = bars([0, 1]) + "not-a-time,1,2,0.5,1.5,1\n"
    root = put(tmp_path, text)
    with pytest.raises(TimeParseError, match="line 4"):
        load(root, [{"name": "d", "paths": [P], "spec": BAR, "range_ns": [T0, T0 + 2 * M]}])


def test_trades_csv_and_jsonl_outside_the_range_are_not_read_beyond_their_time(tmp_path):
    t = ("ts,px,qty,side\n"
         f"{iso(T0)},100,1,buy\n{iso(T0 + 1 * NS)},100,1,buy\n{iso(T0 + 2 * NS)},XX,,nonsense\n")
    root = put(tmp_path, t)
    r = load(root, [{"name": "d", "paths": [P], "spec": TRADE, "range_ns": [T0, T0 + 2 * NS]}])
    assert r.files()[0].rows_kept == 2
    j = "".join(json.dumps(o) + "\n" for o in ({"t": iso(T0), "p": "100", "q": "1", "s": "buy"},
                                                 {"t": iso(T0 + 5 * NS), "p": "x", "s": "?"}))
    put(tmp_path, j, "backtest_data/x/f.jsonl")
    r = load(root, [{"name": "d", "paths": ["backtest_data/x/f.jsonl"], "spec": JTRADE, "range_ns": [T0, T0 + NS]}])
    assert r.files()[0].rows_kept == 1


def sealed(tmp_path, text, time_column, cut_iso):
    put(tmp_path, text)
    (tmp_path / "backtest_data" / "phase2_sealed" / "U").mkdir(parents=True)
    rec = {"unit": "U", "forward_start": cut_iso,
           "files": [{"path": P, "time_column": time_column, "seal_from_ts": cut_iso,
                      "md5": hashlib.md5(text.encode()).hexdigest()}]}
    (tmp_path / "backtest_data" / "phase2_sealed" / "U" / "SEALED.json").write_text(json.dumps(rec))
    return str(tmp_path)


def test_rows_of_a_sealed_file_at_or_after_the_cut_are_not_read_beyond_their_time(tmp_path):
    """The stage G read of the 2023 files: range end = the seal cut; the rows after it are not read beyond their
    time (before the fix their values were turned into numbers and events made, then thrown away)."""
    root = sealed(tmp_path, bars([0, 1, 2, 3], bad=(2, 3)), "ts", iso(T0 + 2 * M) + "+00:00")
    r = load(root, [{"name": "d", "paths": [P], "spec": BAR, "range_ns": [T0, T0 + 2 * M]}])
    f = r.files()[0]
    assert (f.sealed_unit, f.rows_read, f.rows_kept) == ("U", 4, 2)


def test_a_kept_row_whose_seal_time_is_past_the_cut_is_refused_before_its_values(tmp_path):
    """The seal's time column is not the dataset's: a row kept by the range whose seal time is at or after the cut is
    refused by the seal (SealedRangeError), not by its values (before the fix: ParseError on "XX")."""
    rows = ["ts,iso,o,h,l,c,v"]
    for m, seal_m, o in ((0, 0, "1"), (1, 5, "XX")):  # the second row's seal time is T0 + 5M >= the cut T0 + 2M
        rows.append(f"{(T0 + m * M) // NS},{iso(T0 + seal_m * M)},{o},2,0.5,1.5,1")
    root = sealed(tmp_path, "\n".join(rows) + "\n", "iso", iso(T0 + 2 * M) + "+00:00")
    sp = {**BAR, "time": {"columns": ["ts"], "unit": "s", "tz": "UTC"}}
    with pytest.raises(SealedRangeError, match="line 3"):
        load(root, [{"name": "d", "paths": [P], "spec": sp, "range_ns": [T0, T0 + 2 * M]}])


def test_the_stream_door_reads_the_range_before_the_values_too(tmp_path):
    root = put(tmp_path, bars([0, 1, 2], bad=(2,)))
    s = stream(root, {"name": "d", "paths": [P], "spec": BAR, "range_ns": [T0, T0 + 2 * M]}, resolve={})
    chunks = list(s)
    assert [len(c.events) for c in chunks] == [2]
    assert (chunks[0].file.rows_read, chunks[0].file.rows_kept) == (3, 2)


def test_jsonl_numbers_of_a_row_outside_the_range_are_not_turned_into_numbers(tmp_path, monkeypatch):
    """Critic (round 2, [直す] 2): with JSON numbers (not strings) the jsonl reader must not turn the values of a
    row outside the range into numbers before the range is checked."""
    import bot.bt.data.loader as L
    seen = []
    orig = L.json.loads

    def spy(s, *a, **k):
        o = orig(s, *a, **k)
        seen.append({kk: type(v).__name__ for kk, v in o.items()})
        return o
    monkeypatch.setattr(L.json, "loads", spy)
    JB = {**BAR, "format": "jsonl"}
    JB.pop("header"); JB.pop("delimiter")
    j = "".join(json.dumps({"ts": iso(T0 + m * M), "o": 1.5, "h": 2.5, "l": 0.5, "c": 1.5, "v": 1}) + "\n"
                for m in range(3))
    root = put(tmp_path, j, "backtest_data/x/f.jsonl")
    r = load(root, [{"name": "d", "paths": ["backtest_data/x/f.jsonl"], "spec": JB, "range_ns": [T0, T0 + 2 * M]}])
    assert (r.files()[0].rows_read, r.files()[0].rows_kept) == (3, 2)
    assert [x["open"] for x in r.records("d")] == [1.5, 1.5]
    assert seen[2] == {"ts": "str", "o": "str", "h": "str", "l": "str", "c": "str", "v": "str"}, seen[2]

"""V5 adversary (seals): the seal rule over the grid of
(access form x range x seal-column shift x seal-column format x
forward_start), judged by an oracle that reads the seal record's cutoff as
min(seal_from_ts, forward_start) with datetime and applies the documented
rule:

  the file is sealed      <=>  its real path is a sealed entry's, or its
                               bytes equal a sealed file's bytes
  a sealed read refused   <=>  no range, or range end > cutoff, or a row
                               kept by the range has its SEAL-column time
                               at or after the cutoff
  a read that passes returns exactly the rows with lo <= t < hi

The seal column `s` is a different column from the declared time `t`:
equal to it, or 9 hours later (a JST date-like column: a row whose own
time is before the cutoff but whose seal time is not). It is written as ISO
with Z, ISO without offset (the seal reads it as UTC), epoch ms and epoch
s (read by magnitude, as the seal does).
Axes: access {direct, symlink to it, byte copy under another name, copy
with one byte changed (NOT sealed: the documented limit -- an edited copy
is another file)} x range {none, ends at cutoff - 10 h, at cutoff - 1 ns,
at cutoff, at cutoff + 1 ns, at the last row + 1 ns} x shift {0, 9 h} x
format {iso_z, naive, epoch_ms, epoch_s} x forward_start {after seal_from,
before it (the cutoff is then forward_start)}.
Separately: an unreadable seal record refuses every load under the root
(fail closed); a record whose time has no offset refuses too; an
unreadable seal-column cell refuses; the seal ledger is not data.
"""
from __future__ import annotations

import datetime as dt
import itertools
import json
import shutil

import pytest

from bot.bt.data import DataError, SealedRangeError, load

NS = 10**9
H = 3600 * NS
T0 = int(dt.datetime(2026, 1, 5, tzinfo=dt.timezone.utc).timestamp()) * NS
TIMES = [T0 + k * H for k in range(10)]
SEAL_FROM = TIMES[7]


def iso(t, z="Z"):
    return dt.datetime.fromtimestamp(t // NS, tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + z


def seal_cell(t, fmt):
    return {"iso_z": iso(t), "naive": iso(t, ""), "epoch_ms": str(t // 10**6), "epoch_s": str(t // NS)}[fmt]


def csv_text(shift, fmt):
    return "id,t,s,price,size,side\n" + "".join(
        f"{k + 1},{iso(t)},{seal_cell(t + shift, fmt)},{100 + k},1,BUY\n" for k, t in enumerate(TIMES))


def spec():
    return {"format": "csv", "header": True, "delimiter": ",", "kind": "trade", "symbol": "X", "asset": "crypto",
            "time": {"columns": ["t"], "unit": "iso", "tz": "UTC"},
            "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy"}}


def setup(tmp, forward_before, text):
    d = tmp / "backtest_data"
    (d / "sealtest").mkdir(parents=True)
    (d / "sealtest" / "f.csv").write_text(text)
    fwd = TIMES[5] if forward_before else T0 + 30 * 86400 * NS
    rec = {"unit": "U", "forward_start": dt.datetime.fromtimestamp(fwd // NS, tz=dt.timezone.utc).isoformat(),
           "files": [{"path": "backtest_data/sealtest/f.csv", "time_column": "s",
                      "seal_from_ts": dt.datetime.fromtimestamp(SEAL_FROM // NS, tz=dt.timezone.utc).isoformat()}]}
    (d / "phase2_sealed" / "U").mkdir(parents=True)
    (d / "phase2_sealed" / "U" / "SEALED.json").write_text(json.dumps(rec))
    # the oracle's cutoff, read from the record with datetime
    cut = min(dt.datetime.fromisoformat(rec["files"][0]["seal_from_ts"]), dt.datetime.fromisoformat(rec["forward_start"]))
    return int(cut.timestamp()) * NS


def access(tmp, how, text):
    d = tmp / "backtest_data"
    if how == "direct":
        return "backtest_data/sealtest/f.csv"
    (d / "other").mkdir(exist_ok=True)
    if how == "symlink":
        (d / "other" / "l.csv").symlink_to("../sealtest/f.csv")
        return "backtest_data/other/l.csv"
    if how == "copy":
        shutil.copy(d / "sealtest" / "f.csv", d / "other" / "c.csv")
        return "backtest_data/other/c.csv"
    if how == "edited_copy":
        (d / "other" / "e.csv").write_text(text.replace(",100,1,", ",100,2,", 1))
        return "backtest_data/other/e.csv"
    raise AssertionError(how)


RANGES = ["none", "cut-10h", "cut-1", "cut", "cut+1", "last+1"]
CELLS = list(itertools.product(["direct", "symlink", "copy", "edited_copy"], RANGES, [0, 9 * H],
                               ["iso_z", "naive", "epoch_ms", "epoch_s"], [False, True]))


def test_grid_size():
    assert len(CELLS) == 384


@pytest.mark.parametrize("how,rng,shift,fmt,fwd_before", CELLS, ids=["-".join(map(str, c)) for c in CELLS])
def test_seal_cell(tmp_path, how, rng, shift, fmt, fwd_before):
    text = csv_text(shift, fmt)
    cut = setup(tmp_path, fwd_before, text)
    path = access(tmp_path, how, text)
    hi = {"none": None, "cut-10h": cut - 10 * H, "cut-1": cut - 1, "cut": cut, "cut+1": cut + 1,
          "last+1": TIMES[-1] + 1}[rng]
    ds = {"name": "d", "paths": [path], "spec": spec()}
    lo = TIMES[0] - 12 * H
    if hi is not None:
        ds["range_ns"] = [lo, hi]
    sealed = how in ("direct", "symlink", "copy")
    kept = [t for t in TIMES if hi is None or lo <= t < hi]
    refused = sealed and (hi is None or hi > cut or any(t + shift >= cut for t in kept))
    if refused:
        with pytest.raises(SealedRangeError):
            load(str(tmp_path), [ds])
        return
    res = load(str(tmp_path), [ds])
    assert [r["t_ns"] for r in res.records("d")] == kept
    if sealed:
        assert all(t + shift < cut for t in kept)
        assert res.files()[0].sealed_unit == "U"


def test_the_grid_has_rows_refused_only_by_the_seal_column():
    # cells where the range alone passes but the 9-hour-later seal column refuses
    n = 0
    for how, rng, shift, fmt, fwd in CELLS:
        if how == "direct" and rng in ("cut-1", "cut") and shift:
            n += 1
    assert n == 16


@pytest.mark.parametrize("cell", ["", "yesterday", "12345", "2026-01-05T25:00:00"])
def test_an_unreadable_seal_cell_is_refused(tmp_path, cell):
    text = "id,t,s,price,size,side\n1," + iso(TIMES[0]) + "," + cell + ",100,1,BUY\n"
    cut = setup(tmp_path, False, text)
    with pytest.raises(SealedRangeError):
        load(str(tmp_path), [{"name": "d", "paths": ["backtest_data/sealtest/f.csv"], "spec": spec(),
                              "range_ns": [TIMES[0], cut]}])


def test_a_date_only_seal_cell_is_read_as_utc_midnight(tmp_path):
    day = dt.datetime.fromtimestamp(TIMES[0] // NS, tz=dt.timezone.utc).strftime("%Y%m%d")
    text = "id,t,s,price,size,side\n1," + iso(TIMES[0]) + "," + day + ",100,1,BUY\n"
    cut = setup(tmp_path, False, text)
    res = load(str(tmp_path), [{"name": "d", "paths": ["backtest_data/sealtest/f.csv"], "spec": spec(),
                                "range_ns": [TIMES[0], cut]}])
    assert len(res.records("d")) == 1


@pytest.mark.parametrize("record", ["{not json", json.dumps({"unit": "U", "files": []}),
                                    json.dumps({"unit": "U", "forward_start": "2026-02-01T00:00:00",
                                                "files": []}),
                                    json.dumps({"unit": "U", "forward_start": "2026-02-01T00:00:00+00:00",
                                                "files": [{"path": "x", "seal_from_ts": "2026-01-01T00:00:00+00:00"}]})])
def test_an_unreadable_seal_record_refuses_every_load(tmp_path, record):
    setup(tmp_path, False, csv_text(0, "iso_z"))
    (tmp_path / "backtest_data" / "phase2_sealed" / "V").mkdir()
    (tmp_path / "backtest_data" / "phase2_sealed" / "V" / "SEALED.json").write_text(record)
    (tmp_path / "backtest_data" / "free").mkdir()
    (tmp_path / "backtest_data" / "free" / "f.csv").write_text(csv_text(0, "iso_z"))
    with pytest.raises(SealedRangeError):
        load(str(tmp_path), [{"name": "d", "paths": ["backtest_data/free/f.csv"], "spec": spec()}])


def test_the_seal_ledger_itself_is_not_data(tmp_path):
    setup(tmp_path, False, csv_text(0, "iso_z"))
    with pytest.raises(DataError):
        load(str(tmp_path), [{"name": "d", "paths": ["backtest_data/phase2_sealed/U/SEALED.json"], "spec": spec()}])

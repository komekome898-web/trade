"""Harness-side reading for the item 1 reproductions (NOT part of any tool's mechanism).

The reproduced tools cannot take the scene's file shapes (their readers have fixed
shapes), so a reproduction reads the scene's CSV by the scene's own spec and then
applies ONLY the reproduced mechanism.  Reading: csv module with the spec's
delimiter / header / names; a single ISO time column parsed by
datetime.fromisoformat ("Z" -> "+00:00"; naive = the spec's zone, UTC only).
Anything else is NotExpressible.
"""
from __future__ import annotations

import csv
import gzip
import io
from datetime import datetime, timezone

from i1_protocol import NotExpressible, dataset_paths, need

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _ns(dt: datetime) -> int:
    d = dt - _EPOCH
    return (d.days * 86400 + d.seconds) * 1_000_000_000 + d.microseconds * 1000


def rows_with_time(inp: dict, ds: dict):
    """[(t_ns, row_dict)] of every file of the dataset, in file order."""
    sp = ds["spec"]
    need(len(sp["time"]["columns"]) == 1 and sp["time"]["unit"] == "iso" and sp["time"].get("tz", "UTC") == "UTC",
         "再現の読み取りは ISO の 1 列・UTC だけ(道具の口に単位・時間帯・2 列の時刻が無い)")
    out = []
    for p in dataset_paths(inp, ds):
        raw = open(p, "rb").read()
        if sp.get("compression") == "gzip":
            raw = gzip.decompress(raw)
        rd = csv.reader(io.StringIO(raw.decode("utf-8")), delimiter=sp.get("delimiter", ","))
        names = next(rd) if sp.get("header", True) else sp["names"]
        col = sp["time"]["columns"][0]
        for r in rd:
            if not r:
                continue
            row = dict(zip(names, r))
            s = row[col]
            dt = datetime.fromisoformat(s[:-1] + "+00:00" if s.endswith("Z") else s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            out.append((_ns(dt), row))
    if not out:
        raise NotExpressible("行が無い")
    return out

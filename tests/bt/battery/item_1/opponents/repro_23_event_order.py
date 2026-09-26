"""Reproduction of hftbacktest's event-order validation (catalogue 23) for item 1 V3.

Source (the installed hftbacktest 2.4.4, venv item_0/hftbacktest and item_1/hftbacktest, read 2026-09-25):
hftbacktest/data/validation.py:139-152 `validate_event_order(data)`:
    exch_ev = data['ev'] & EXCH_EVENT == EXCH_EVENT
    ...
    if np.sum(np.diff(data['exch_ts'][exch_ev]) < 0) > 0:
        raise ValueError('exchange events are out of order.')
(the same for local_ts).  Nothing is reported when the order holds; there is no
duplicate / gap / conflict kind.

Reproduced: every row is an exchange event whose exch_ts is the row's time
(the scene has no separate local time); the check and the error text are as
above.  The reading of the scene's file is the harness's (opponents/_repro_read.py),
because the tool's converters (data/utils/tardis.py:56 and the per-venue ones)
take only their own fixed shapes.  Nothing added, nothing weakened.
"""
from __future__ import annotations

import numpy as np

from _repro_read import rows_with_time
from i1_protocol import NotExpressible, Refused


class T:
    name = "opp_repro_23"

    def run(self, inp):
        if inp["op"] != "load":
            raise NotExpressible("再現したのは V3 の事象の順の検査だけ")
        if "anomalies" not in inp["want"]:
            # the file reading here is the harness's, not the tool's: only the V3 check is the tool's mechanism
            raise NotExpressible("再現したのは V3 の検査の機構だけ(読み取りは再現の側の手段で、道具の読み口ではない)")
        if set(inp["want"]) & {"hashes"}:
            raise NotExpressible("hftbacktest に読んだファイルの sha256 を記録する口が無い")
        events = {}
        for ds in inp["datasets"]:
            rows = rows_with_time(inp, ds)
            exch_ts = np.array([t for t, _ in rows], dtype=np.int64)
            if np.sum(np.diff(exch_ts) < 0) > 0:  # validation.py:149-150
                raise Refused("exchange events are out of order.")
            key = "start_ns" if ds["spec"]["kind"] == "bar" else "t_ns"
            events[ds["name"]] = [{key: t} for t, _ in rows]
        return {"events": events}  # the mechanism reports nothing when the order holds


TARGET = T()

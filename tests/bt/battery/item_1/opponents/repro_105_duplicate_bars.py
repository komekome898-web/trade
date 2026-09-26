"""Reproduction of DaniyalMlk/slippage's bar-series check (catalogue 105) for item 1 V3.

Source (the installed clone, venv item_0/c105, read 2026-09-25):
- slippage/io.py:126-149 `load_bars`: rows -> Bar(timestamp=datetime.fromisoformat, open, high,
  low, close, volume) grouped by symbol, then `BarSeries(bars)`;
- slippage/series.py:35-41 `BarSeries.__init__`: `ordered = tuple(sorted(bars, key=lambda b:
  b.timestamp))`, raises InsufficientDataError on no bar, and raises
  ValidationError(f"duplicate bar timestamp {current!r}") when two bars share a timestamp.
Nothing is reported otherwise (a backward row is sorted silently; no gap / conflict kind).

Reproduced for bar datasets: all the dataset's bars (every file, as one list handed to
BarSeries) sorted by timestamp, refusal on a duplicated timestamp.  The reading of
the scene's file is the harness's (opponents/_repro_read.py), because load_bars needs
the fixed columns symbol,timestamp,... (io.py:44).  Nothing added, nothing weakened.
"""
from __future__ import annotations

from _repro_read import rows_with_time
from i1_protocol import NotExpressible, Refused


class T:
    name = "opp_repro_105"

    def run(self, inp):
        if inp["op"] != "load":
            raise NotExpressible("再現したのは V3 の足の重複の検査だけ")
        if "anomalies" not in inp["want"]:
            # the file reading here is the harness's, not the tool's: only the V3 check is the tool's mechanism
            raise NotExpressible("再現したのは V3 の検査の機構だけ(読み取りは再現の側の手段で、道具の読み口ではない)")
        if set(inp["want"]) & {"hashes"}:
            raise NotExpressible("slippage に読んだファイルの sha256 を記録する口が無い")
        events = {}
        for ds in inp["datasets"]:
            if ds["spec"]["kind"] != "bar":
                raise NotExpressible("slippage の系列の型は足(BarSeries)だけで、約定の行の型が無い")
            rows = rows_with_time(inp, ds)
            ordered = sorted(t for t, _ in rows)  # series.py:35
            for a, b in zip(ordered, ordered[1:]):
                if a == b:  # series.py:40-41
                    raise Refused(f"duplicate bar timestamp {b}")
            events[ds["name"]] = [{"start_ns": t} for t in ordered]
        return {"events": events}


TARGET = T()

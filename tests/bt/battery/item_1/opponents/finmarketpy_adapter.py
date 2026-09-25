"""finmarketpy (catalogue 54, SCAN 7851 行) with its data layer findatapy, for the item 1 battery
(venv item_1/finmarketpy: the finmarketpy 0.11.19 wheel item 0 inspected, re-installed here on
2026-09-25 after item 0's venv was found removed; findatapy 0.1.42, pandas 2.3.3 as in item 0).

Read in the installed code:
- findatapy `IOEngine.read_csv_data_frame(f_name, freq, dateparse=..., intraday_tz=...)`
  (findatapy/market/ioengine.py:1080): the FIRST column is the time index, parsed by
  the named parser ("dukascopy" = `YYYY-MM-DD HH:MM:SS`, seconds only; the default =
  `DD/MM/YYYY HH:MM:SS`), every other column is cast to float32 (ioengine.py:1130);
  no argument for a time column, a unit, a header-less file or a delimiter;
- findatapy `DataQuality.count_repeated_dates(df)` (findatapy/timeseries/dataquality.py:200):
  the duplicated index entries of a DataFrame (no backward / gap / conflict kind);
- finmarketpy's backtest is vectorised (TradingModel / Backtest over signal frames);
  there is no event path to agree with, and no corporate-action or universe code.

So: files whose first column is the time and whose other columns are numbers are
read with the tool's reader (intraday, the "dukascopy" parser; naive times are UTC as
the scene declares); `anomalies` are the tool's duplicate count (the only kind it has).
"""
from __future__ import annotations

from _i1_base import NotExpressible, ReasonTarget  # noqa: F401
from i1_protocol import Refused

import pandas as pd
from findatapy.market.ioengine import IOEngine
from findatapy.timeseries.dataquality import DataQuality

from i1_protocol import dataset_paths, need


class T(ReasonTarget):
    name = "opp_finmarketpy"
    reasons = {
        "jpx": "finmarketpy / findatapy に分割・併合の事象から値段を調整する口と、日付ごとの銘柄集合の口が無い",
        "vector_vs_event": "finmarketpy の検証はベクトル化の 1 経路(信号の表と値の表の演算)だけで、突き合わせる事象駆動の経路が無い",
    }

    def op_load(self, inp):
        want = set(inp["want"])
        need("hashes" not in want, "finmarketpy / findatapy に読んだファイルの sha256 を記録する口が無い")
        io, dq = IOEngine(), DataQuality()
        events, anomalies = {}, {}
        for ds in inp["datasets"]:
            sp = ds["spec"]
            paths = dataset_paths(inp, ds)
            need(len(paths) == 1, "findatapy の read_csv_data_frame は 1 ファイルずつ(複数の世代を 1 つのデータとして読む口が無い)")
            need(sp.get("header", True) and sp.get("delimiter", ",") == "," and not sp.get("compression"),
                 "read_csv_data_frame に見出しの無いファイル・区切り文字・圧縮の引数が無い")
            need(sp["kind"] in ("quote", "bar"), "read_csv_data_frame は全列を float32 にするので、文字列の列(売買の向き)を持つ約定の形を読めない")
            need(len(sp["time"]["columns"]) == 1, "read_csv_data_frame は時刻を最初の 1 列から読む(2 列を合わせる引数が無い)")
            need(sp["time"].get("unit") == "iso" and sp["time"].get("tz", "UTC") == "UTC",
                 "read_csv_data_frame の時刻の読み方は日付の文字列の形だけ(数の単位・時間帯の引数が無い)")
            try:
                df = io.read_csv_data_frame(paths[0], "intraday", dateparse="dukascopy")
            except Exception as exc:  # the tool itself refused the file
                raise Refused(f"read_csv_data_frame: {type(exc).__name__}: {exc}"[:300])
            cols = {c[:-len(".close")]: c for c in df.columns}
            f = sp["fields"]
            key = "start_ns" if sp["kind"] == "bar" else "t_ns"
            recs = []
            for ts, row in df.iterrows():
                r = {key: int(pd.Timestamp(ts).value)}
                for k, col in f.items():
                    if col in cols:
                        r[k] = float(row[cols[col]])
                recs.append(r)
            events[ds["name"]] = recs
            if "anomalies" in want:
                _, dups = dq.count_repeated_dates(df)
                anomalies[ds["name"]] = [{"kind": "duplicate", "t_ns": int(pd.Timestamp(x).value)} for x in dups]
        out = {"events": events}
        if "anomalies" in want:
            out["anomalies"] = anomalies
        return out


TARGET = T()

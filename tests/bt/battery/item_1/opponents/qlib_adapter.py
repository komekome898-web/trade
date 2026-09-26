"""Qlib (pyqlib 0.9.7, catalogue 21, SCAN 6899 行) for the item 1 battery.

Installed 2026-09-25 into the isolated venv item_1/qlib (opponents/RUNNABILITY.tsv):
the wheel without its declared dependencies, plus only what `import qlib` and
`qlib.init` import (ruamel.yaml, pydantic-settings, python-redis-lock,
mlflow-skinny, filelock); mlflow telemetry is switched off by environment.

What the tool has, read in the installed code:
- a point-in-time instrument universe: the provider's `instruments/<market>.txt`
  holds `code <TAB> start <TAB> end` (end inclusive) and
  `D.list_instruments(D.instruments(market), start_time, end_time, as_list=True)`
  returns the instruments whose listed span meets the window
  (qlib/data/data.py LocalInstrumentProvider, qlib/data/storage/file_storage.py:208);
- prices are read from its own binary feature files; an adjusted price comes
  from a `$factor` feature the data supplies -- the installed package computes
  no adjustment from a split / reverse-split event and has no code change
  (grep -rn "split\\|reverse\\|code_change" qlib/data -> no corporate-action code);
- no reader of CSV market data in the installed package (the CSV -> binary
  converter `scripts/dump_bin.py` is in the repository, not in the wheel), no
  duplicate / gap / hash / allow-list reporting, no vector-vs-event path pair.

The universe scene is handed over as the instruments file: a listing
`delisted` (first day NOT listed) becomes qlib's inclusive `end` = the day before;
no delisting -> 2099-12-31.  The calendar is the scene's dates.
"""
from __future__ import annotations

import datetime as _dt
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from i1_protocol import NotExpressible, need  # noqa: E402

os.environ.setdefault("MLFLOW_DISABLE_TELEMETRY", "true")
os.environ.setdefault("DO_NOT_TRACK", "1")

import qlib  # noqa: E402
from qlib.data import D  # noqa: E402

_INIT = {"dir": None}


def _provider(days, listings):
    base = tempfile.mkdtemp(prefix="i1_qlib_")
    os.makedirs(os.path.join(base, "calendars"))
    os.makedirs(os.path.join(base, "instruments"))
    os.makedirs(os.path.join(base, "features"))
    with open(os.path.join(base, "calendars", "day.txt"), "w") as fh:
        fh.write("\n".join(sorted(set(days))) + "\n")
    with open(os.path.join(base, "instruments", "all.txt"), "w") as fh:
        for l in listings:
            end = "2099-12-31" if l["delisted"] is None else (_dt.date.fromisoformat(l["delisted"]) - _dt.timedelta(days=1)).isoformat()
            fh.write(f"{l['code']}\t{l['listed']}\t{end}\n")
    return base


class Qlib:
    name = "opp_qlib"

    def run(self, inp: dict) -> dict:
        op = inp["op"]
        if op == "load":
            raise NotExpressible("Qlib の配布物に CSV の市場データを読む口が無い(CSV から Qlib の形に直す scripts/dump_bin.py はリポジトリの側にあり配布物に入っていない。"
                                 "配布物の read_csv の当たりは銘柄の一覧・暦・注文の表・予測の表だけ)")
        if op == "vector_vs_event":
            raise NotExpressible("Qlib に同じ足を事象駆動と近道の 2 つの経路で回して突き合わせる口が無い(検証は qlib.backtest の 1 経路)")
        need(op == "jpx", f"未知の op {op}")
        need(not inp["bars"], "Qlib は分割・併合の事象から値段を調整しない(調整はデータが持つ $factor の特徴量を掛けるだけ)。コード変更の口も無い")
        need(not inp["actions"], "Qlib にコード変更・分割・併合の事象を渡す口が無い")
        days = list(inp["universe_dates"]) + [inp["as_of"]]
        base = _provider(days, inp["listings"])
        qlib.init(provider_uri=base, region="cn", kernels=1,
                  exp_manager={"class": "MLflowExpManager", "module_path": "qlib.workflow.expm",
                               "kwargs": {"uri": "file:" + os.path.join(base, "mlruns"), "default_exp_name": "i1"}})
        uni = {}
        for d in inp["universe_dates"]:
            uni[d] = sorted(D.list_instruments(D.instruments("all"), start_time=d, end_time=d, as_list=True))
        return {"universe": uni}


TARGET = Qlib()

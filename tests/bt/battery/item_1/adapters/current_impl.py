"""当方の現状 (the current state) for the item 1 battery (データと時刻).

What the current state has for data and time (read 2026-09-25; REQUIREMENTS.md §4):
- `bot.backtest.engine.run_backtest` takes an already-built candles DataFrame; the
  old backtest package reads no file, has no time normaliser, no duplicate /
  backward / gap check, no hash record, no allow-list and no vector path
  (engine.py loops over bars).
- `bot.research.sealed`:
    * `read_timestamps(path, time_column)` -- reads one CSV/CSV.GZ time column and
      parses each cell with `parse_ts` (unit guessed from the magnitude:
      >=1e15 micro, >=1e12 milli, >=1e8 seconds, else ISO; a naive ISO is taken
      as UTC; unparseable cells are skipped).  It has no argument for a unit,
      a time zone, a delimiter or a header-less file.
    * `load_unsealed(path, unit, root)` -- the dev rows of a file listed in a
      unit's SEALED.json (rows before min(seal_from_ts, forward_start)).
    * `load_sealed(path, unit, token, root)` -- the sealed rows; refuses unless
      the three guards (env PHASE2_FINAL_EVAL, UNSEAL_APPROVED file, token) pass.
- `bot.monitoring.market_view.read_candles(path)` -- a candle CSV with the fixed
  columns ts,open,high,low,close,volume -> bars (ts in float seconds).
- `bot.monitoring.market_view.bars_from_executions(rows)` -- one aggregator of
  execution dicts into 1-minute bars (a single path; there is no second path
  to agree with).

So this adapter calls exactly those public functions.  Whatever they have no
argument for is NotExpressible with the missing argument named.
"""
from __future__ import annotations

import glob
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from i1_protocol import NotExpressible, Refused, dataset_paths, need  # noqa: E402

from bot.monitoring import market_view  # noqa: E402
from bot.research import sealed  # noqa: E402

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _dt_ns(dt: datetime) -> int:
    """datetime (microsecond resolution) -> int ns, exactly (a change of representation)."""
    d = dt - _EPOCH
    return (d.days * 86400 + d.seconds) * 1_000_000_000 + d.microseconds * 1000


def _seal_units(root: str, rel: str):
    """Units whose SEALED.json lists `rel` (the current state's own lookup: is_dataset_sealed_file)."""
    out = []
    for p in sorted(glob.glob(os.path.join(root, "backtest_data", "phase2_sealed", "*", "SEALED.json"))):
        unit = os.path.basename(os.path.dirname(p))
        if sealed.is_dataset_sealed_file(rel, unit, root=root):
            out.append(unit)
    return out


def _common_checks(ds: dict) -> None:
    sp = ds["spec"]
    need(sp.get("format") == "csv", "現状の読み口は CSV だけ")
    need(sp.get("header", True), "現状の読み口(read_timestamps・load_unsealed・read_candles)に見出しの無いファイルの列名を渡す引数が無い")
    need(sp.get("delimiter", ",") == ",", f"現状の読み口に区切り文字({sp.get('delimiter')!r})の引数が無い(csv.reader・pd.read_csv の既定のカンマだけ)")
    need(len(sp["time"]["columns"]) == 1, "現状の読み口は時刻を 1 列から読む(date と time の 2 列を合わせる引数が無い)")
    need(sp["time"].get("tz", "UTC") == "UTC", f"現状の parse_ts に時間帯の引数が無い(オフセットの無い時刻は UTC とみなす)。宣言 {sp['time'].get('tz')}")


def _sealed_records(inp, ds, path, rel, units):
    sp = ds["spec"]
    need(sp["kind"] == "trade", "封印の読み口から事象を作るのは約定の形だけ")
    unit = units[0]
    seal = sealed.load_seal_record(unit, inp["root"])
    entry = next(e for e in seal["files"] if e["path"] == rel)
    cutoff = min(datetime.fromisoformat(entry["seal_from_ts"]), datetime.fromisoformat(seal["forward_start"]))
    rng = ds.get("range_ns")
    if rng is not None and rng[1] > _dt_ns(cutoff):
        # the request reaches into the sealed window: the current state's API for those rows is load_sealed
        try:
            sealed.load_sealed(path, unit, token="", root=inp["root"])
        except sealed.SealedDataError as exc:
            raise Refused(f"load_sealed: {exc}")
        raise NotExpressible("load_sealed が封印の行を返した(守りが開いている)")
    df = sealed.load_unsealed(path, unit, root=inp["root"])
    f = sp["fields"]
    col = sp["time"]["columns"][0]
    recs = []
    for _, row in df.iterrows():
        dt = sealed.parse_ts(row[col])
        recs.append({"t_ns": _dt_ns(dt), "px": float(row[f["px"]]), "qty": float(row[f["qty"]]),
                     "side": sp.get("side_map", {}).get(str(row[f["side"]]), str(row[f["side"]])), "id": str(row[f["id"]])})
    return recs


def _load(inp: dict) -> dict:
    want = set(inp.get("want", []))
    need(not (want & {"anomalies"}), "現状に重複・逆行・欠落・食い違いを報せる口が無い(read_timestamps は読めない行を黙って飛ばす。src/bot/backtest/ に検査のコードが無い)")
    need(not (want & {"hashes"}), "現状に読んだデータの sha256 を記録する口が無い(sealed.md5_of は md5 で、封印の台帳づくりにだけ使う)")
    events = {}
    for ds in inp["datasets"]:
        paths = dataset_paths(inp, ds)
        need(len(paths) == 1, "現状の読み口は 1 ファイルずつ(複数の世代を 1 つのデータとして読む口が無い)")
        path, rel = paths[0], ds["paths"][0]
        _common_checks(ds)
        units = _seal_units(inp["root"], os.path.normpath(rel))
        if units:
            events[ds["name"]] = _sealed_records(inp, ds, path, os.path.normpath(rel), units)
            continue
        sp = ds["spec"]
        if want == {"times"}:
            try:
                _, dts = sealed.read_timestamps(Path(path), sp["time"]["columns"][0])
            except sealed.SealedDataError as exc:
                raise Refused(f"read_timestamps: {exc}")
            key = "start_ns" if sp["kind"] == "bar" else "t_ns"
            events[ds["name"]] = [{key: _dt_ns(d)} for d in dts]
            continue
        if sp["kind"] == "bar":
            need(sp["time"]["columns"] == ["ts"] and all(sp["fields"][k] == k for k in ("open", "high", "low", "close", "volume")),
                 "read_candles の列は ts,open,high,low,close,volume に固定(列の名前を渡す引数が無い)")
            bars = market_view.read_candles(Path(path))
            events[ds["name"]] = [{"start_ns": int(round(b["ts"])) * 1_000_000_000, "open": b["open"], "high": b["high"],
                                   "low": b["low"], "close": b["close"], "volume": b["volume"]} for b in bars]
            continue
        raise NotExpressible(f"現状に {sp['kind']} のファイルを事象(値段・数量つき)にする読み口が無い(read_timestamps は時刻だけ、"
                             "load_unsealed は封印の台帳に載ったファイルだけ、read_candles は足だけ)")
    return {"events": events}


class CurrentImpl:
    name = "current_impl"

    def run(self, inp: dict) -> dict:
        op = inp["op"]
        if op == "load":
            return _load(inp)
        if op == "jpx":
            raise NotExpressible("現状に分割・併合・コード変更の調整と、日付ごとの銘柄集合の口が無い(grep -rn '上場廃止|分割併合|生存者' src/bot/ は 0 件、REQUIREMENTS.md §4)")
        if op == "vector_vs_event":
            raise NotExpressible("現状に近道(ベクトル化)の経路が無い: engine.run_backtest は足を 1 本ずつ回す事象駆動だけ、"
                                 "market_view.bars_from_executions は足を作る経路が 1 本だけで、突き合わせる相手が無い")
        raise NotExpressible(f"未知の op {op}")


TARGET = CurrentImpl()

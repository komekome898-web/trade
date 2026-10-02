#!/usr/bin/env python3
"""Copy the files the dashboard's バックテスト tab reads into a git-tracked place.

backtest_runs/ is not in git (bot.bt.repro writes a `*` .gitignore into it),
so a machine that only pulls the repository has no run to show. This script
copies, for the runs it is told to share, only the files
`bot.monitoring.backtest_view` reads (VIEW_FILES: record.json, repro.json and
the metrics / trades / data_quality / validation exports, as .json or
.json.gz) into

    <out>/<group>/<run_id>/        (default out: backtest_runs_shared)

and writes the list of what it shared and what it did not, with the reason,
into <out>/<group>/SHARED.json (<out>/SHARED.json for runs that sit directly
under --runs-dir). fills / orders and the per-group `.gitignore` are never
copied.

Seal (the only judgment this script makes): a run is shared only when the
period it covers ends before the seal boundary -- or AT it, when the run's
events are bars only. The period is read from
the run's declaration in record.json only -- `data[].range_ns` (the declared
[lo, hi) of the rows read) and every `engine...last_time_ns` (the time of the
last event the engine processed; a bar's event time is its END, loader.py
`BarEvent(received_time_ns=start + interval)`). Values (profit and loss, trade
counts, anything in the exports) are never read to decide.

Every seal unit under <root>/backtest_data/phase2_sealed must be one this
script knows (UNITS). A unit it does not know -- a new seal, of any market --
stops all sharing until UNITS says whether that unit's cutoff bounds crypto /
fx runs; the list says which unit. (A fixed pair of unit names would let a
later, earlier crypto seal pass unseen: a run on derived data does not name
the sealed file it came from, so only the boundary can keep it out.)

    boundary = the earliest cutoff of the known units that seal crypto / fx
               (P2-08, P2-08b), as the data layer itself computes it
               (bot.bt.data.allowlist.SealRegistry: min(seal_from_ts,
               forward_start)) -> 2023-12-18T00:00:00Z today
    a run is shared iff  end <  boundary                (any event that is not a bar: a fill, a book row ...
                                                         is stamped with the row's own time, so a row AT the
                                                         boundary is a sealed row: the data layer's rule is
                                                         "before the cutoff")
                      or end <= boundary                (every data[].spec.kind of the record is "bar": a bar's
                                                         time is its END, so a bar ending AT the boundary
                                                         consists of rows before it)
                     and its data are crypto or fx
                     and no data file it names is, by path or by bytes, a file
                         of ANY seal record whose cutoff end reaches past

The file check is the data layer's own (SealRegistry.by_path on the real path,
then SealRegistry.copy_of on the bytes: the md5 the seal record wrote, then
sha256). The bytes must still be the ones the run read (record.json
`data_sha256`); a data file that is missing or changed since the run is not
shared, because it cannot be told apart from a sealed copy. The data files
are hashed, never decoded.

The single earliest boundary is applied to every crypto / fx run, not the
boundary of the run's own market: a run on derived data (folded bars such as
backtest_data/k1_newenv_g_20261001/) does not name the sealed file it came
from, so its market cannot be read mechanically from the record. A run whose
period cannot be read, whose data name another asset class, or whose seal
records cannot be read is not shared, and the list says why. A run excluded
now that an earlier invocation had copied is removed from <out>.

Size: nothing is copied when the selected runs' files exceed --max-mb; the sizes
are printed instead (exit 2). --max-mb has no default: the limit is the owner's
decision (how much the repository that the owner's PC pulls may grow), so it is
always said on the command line.

Usage:
    python scripts/share_backtest_runs.py --all --dry-run --max-mb <MB>      # measure only
    python scripts/share_backtest_runs.py --group k1_newenv_g --group k1_newenv_g_close --max-mb <MB>
    python scripts/share_backtest_runs.py --run <run_id> --max-mb <MB>
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Optional

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from bot.bt.data.allowlist import SealRegistry  # noqa: E402
from bot.monitoring.backtest_view import VIEW_FILES, find_runs  # noqa: E402

# Every seal unit this script knows, and whether its cutoff bounds a crypto / fx run. The markets are read from
# the files each record names (backtest_data/phase2_sealed/<unit>/SEALED.json, 2026-10-02):
#   P2-01 n225f_225labo / nk225_sessions / on1_ledger, P2-02 jpx_etf_daily / reit_onr, P2-03 and P2-03b
#   jpx_etf_daily, P2-04 jpx_etf_daily / n225f_225labo, P2-07 nk225_events  -> 日本株 (no crypto / fx file)
#   P2-08 binance / bitflyer 1m, executions_FX_BTC_JPY, fx_usdjpy_1m; P2-08b binance / bitflyer executions, tape
#                                                                         -> 暗号資産・FX
# A unit missing here stops all sharing (seal_rule). A 日本株 unit's files are still checked one by one (decide).
UNITS = {"P2-01": "日本株", "P2-02": "日本株", "P2-03": "日本株", "P2-03b": "日本株", "P2-04": "日本株",
         "P2-07": "日本株", "P2-08": "暗号資産・FX", "P2-08b": "暗号資産・FX"}
BOUNDARY_MARKET = "暗号資産・FX"
BOUNDARY_UNITS = tuple(u for u, m in UNITS.items() if m == BOUNDARY_MARKET)
SEALED_MARKETS = ("crypto", "fx")
MANIFEST = "SHARED.json"


def _iso(ns: Optional[int]) -> Optional[str]:
    if ns is None:
        return None
    return dt.datetime.fromtimestamp(ns / 1e9, tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def seal_rule(root: str) -> dict:
    """{'boundary_ns', 'boundary_units', 'units', 'registry', 'root', 'checked'} or {'error': text}."""
    try:
        reg = SealRegistry(root)
    except Exception as exc:  # noqa: BLE001 -- the data layer fails closed; so does sharing
        return {"error": f"封印の記録が読めない({type(exc).__name__}: {exc})"}
    found = sorted({e.unit for e in reg.entries})
    unknown = [u for u in found if u not in UNITS]
    if unknown:
        return {"error": f"封印の記録に、この台本が知らない単位 {'・'.join(unknown)} がある。その単位の境が暗号資産・FX の"
                         f"実行にかかるかを UNITS に書くまで、何も共有しない"}
    units = sorted({e.unit for e in reg.entries if e.unit in BOUNDARY_UNITS})
    if units != sorted(BOUNDARY_UNITS):
        return {"error": f"封印の記録 {'・'.join(BOUNDARY_UNITS)} が {root}/backtest_data/phase2_sealed に揃っていない"
                         f"(読めたもの: {units})"}
    cut = [e.cutoff_ns for e in reg.entries if e.unit in BOUNDARY_UNITS]
    return {"boundary_ns": min(cut), "boundary_units": units, "units": {u: UNITS[u] for u in found},
            "registry": reg, "root": root, "checked": {}}


def _sealed_by_file(real: str, given: str, sha: Optional[str], rule: dict):
    """(the seal entry with the EARLIEST cutoff among those this data file is, by path or by bytes, or None; why it
    cannot be told), cached per real path. The identification is the data layer's own (SealRegistry.by_path, then
    copy_of on the bytes: the md5 the record wrote, then sha256 for a same-size sealed file), widened to every
    entry naming that path or those bytes: one file can sit in two records with two cutoffs (P2-08 and P2-08b both
    name executions_FX_BTC_JPY_31d_20260823.csv.gz, 2023-12-18 and 2026-08-23), and by_path / copy_of return only
    one of them, not necessarily the earlier."""
    key = (real, sha)
    if key in rule["checked"]:
        return rule["checked"][key]
    reg = rule["registry"]
    hits, why = [e for e in reg.entries if e.real == real], None
    if not hits:
        try:
            with open(real, "rb") as fh:  # hashed, never decoded
                raw = fh.read()
        except OSError as exc:
            raw, why = None, (f"データファイル {given} が読めず({type(exc).__name__})、封印のファイルの写しでないことを"
                              f"確かめられない")
        if raw is not None:
            if sha is not None and hashlib.sha256(raw).hexdigest() != sha:
                why = (f"データファイル {given} の中身が実行のとき(record.json の data_sha256)と違い、実行が読んだものが"
                       f"封印のファイルの写しでないことを確かめられない")
            else:
                md5 = hashlib.md5(raw).hexdigest()
                hits = [e for e in reg.entries if e.md5 == md5]
                one = reg.copy_of(raw)
                if one is not None:
                    hits += [e for e in reg.entries if e.real == one.real or e is one]
            del raw
    ent = min(hits, key=lambda e: e.cutoff_ns) if hits else None
    rule["checked"][key] = (ent, why)
    return ent, why


def _times(engine: Any, key: str) -> list:
    out: list = []
    if isinstance(engine, dict):
        if key in engine:
            out.append(engine[key])
        for k, v in engine.items():
            if k != key:
                out.extend(_times(v, key))
    elif isinstance(engine, list):
        for v in engine:
            out.extend(_times(v, key))
    return out


def period(record: dict) -> tuple[Optional[int], Optional[int], Optional[str]]:
    """(start_ns, end_ns, why not readable) from the run's declaration only."""
    lo: list = []
    hi: list = []
    for d in record.get("data") or []:
        r = d.get("range_ns") if isinstance(d, dict) else None
        if r is not None:
            if not (isinstance(r, list) and len(r) == 2 and all(type(x) is int for x in r)):
                return None, None, f"data[].range_ns が読めない: {r!r}"
            lo.append(r[0])
            hi.append(r[1])
    first = _times(record.get("engine"), "first_time_ns")
    last = _times(record.get("engine"), "last_time_ns")
    bad = [x for x in first + last if type(x) is not int]
    if bad:
        return None, None, f"engine の first_time_ns / last_time_ns が整数でない: {bad[:3]!r}"
    lo += first
    hi += last
    if not hi:
        return None, None, "期間が読めない(record.json に data[].range_ns も engine の last_time_ns も無い)"
    return (min(lo) if lo else None), max(hi), None


def bars_only(record: dict) -> bool:
    """True only when the record itself declares that every event of the run is a bar: at least one data entry and
    every data[].spec.kind == "bar". Anything else (a fill / book / quote kind, a missing or unreadable spec, no data
    entry) is "not known to be bars only", and the seal is then read on the closing side."""
    data = record.get("data")
    if not isinstance(data, list) or not data:
        return False
    return all(isinstance(d, dict) and isinstance(d.get("spec"), dict) and d["spec"].get("kind") == "bar"
               for d in data)


def reaches(end: int, cutoff: int, bars: bool) -> bool:
    """Does a run whose last event is at `end` reach the sealed rows of `cutoff`? A bar's event time is its END
    (start + interval), so a bar ending exactly at the cutoff holds only rows before it: it reaches only past it.
    Any other event carries its row's own time, and a row AT the cutoff is sealed (the rule is "before the
    cutoff"): it reaches from the cutoff on."""
    return end > cutoff if bars else end >= cutoff


def _data_paths(record: dict) -> list[tuple[str, Optional[str]]]:
    """(path, the sha256 the run recorded for it or None) for every data file the record names."""
    shas = record.get("data_sha256") if isinstance(record.get("data_sha256"), dict) else {}
    out = []
    for d in record.get("data") or []:
        if not isinstance(d, dict):
            continue
        if type(d.get("path")) is str:
            out.append((d["path"], shas.get(d["path"])))
        mp = (d.get("origin_evidence") or {}).get("market_path") if isinstance(d.get("origin_evidence"), dict) else None
        if type(mp) is str:
            out.append((mp, shas.get(mp)))
    return out


def decide(run_dir: str, rule: dict) -> dict:
    """{'share': bool, 'reason', 'start', 'end', 'at_boundary'} for one run."""
    if "error" in rule:
        return {"share": False, "reason": rule["error"]}
    try:
        with open(os.path.join(run_dir, "record.json"), "r", encoding="utf-8") as fh:
            rec = json.load(fh)
    except (OSError, ValueError) as exc:
        return {"share": False, "reason": f"record.json が読めない({type(exc).__name__})"}
    start, end, why = period(rec)
    if why:
        return {"share": False, "reason": why}
    assets = sorted({str((d.get("spec") or {}).get("asset")) for d in rec.get("data") or [] if isinstance(d, dict)})
    base = {"start": _iso(start), "end": _iso(end)}
    if not assets or any(a not in SEALED_MARKETS for a in assets):
        return {**base, "share": False,
                "reason": f"データの資産の種類 {assets} は、この規則の対象(暗号資産・FX)ではない。境が決められない"}
    b = rule["boundary_ns"]
    bars = bars_only(rec)
    if reaches(end, b, bars):
        what = "を越える" if bars else ("と同じか、それを越える(足以外の事象は行そのものの時刻で、境ちょうどの行は封印の側。"
                                       "宣言から事象が足だけと分かる実行だけが、境ちょうどで終わってよい)")
        return {**base, "share": False,
                "reason": f"期間の終わり {_iso(end)} が封印の境 {_iso(b)}({'・'.join(rule['boundary_units'])}){what}"}
    for p, sha in _data_paths(rec):
        real = os.path.realpath(os.path.join(rule["root"], p))
        ent, why = _sealed_by_file(real, p, sha, rule)
        if why:
            return {**base, "share": False, "reason": why}
        if ent is not None and reaches(end, ent.cutoff_ns, bars):
            how = "そのもの" if ent.real == real else f"の写し({ent.path} と同じ中身)"
            return {**base, "share": False,
                    "reason": f"データファイル {p} は封印の記録 {ent.unit} のファイル{how}で、その境 "
                              f"{_iso(ent.cutoff_ns)} を、期間の終わり {_iso(end)} が{'越える' if bars else '越えるか同じ(足以外の事象)'}"}
    return {**base, "share": True, "reason": None, "at_boundary": end == b, "bars_only": bars}


def _files(run_dir: str) -> dict[str, int]:
    return {n: os.path.getsize(os.path.join(run_dir, n)) for n in VIEW_FILES if os.path.isfile(os.path.join(run_dir, n))}


def _sha(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _selected(runs: list, groups: list[str], run_ids: list[str], all_: bool) -> list:
    if all_:
        return runs
    out = []
    for rid, d, g in runs:
        if rid in run_ids or any(g == x or g.startswith(x.rstrip("/") + "/") for x in groups):
            out.append((rid, d, g))
    return out


def plan(runs_dir: str, root: str, groups: list[str], run_ids: list[str], all_: bool) -> dict:
    rule = seal_rule(root)
    sel = _selected(find_runs(runs_dir), groups, run_ids, all_)
    rows = []
    for rid, d, g in sel:
        dec = decide(d, rule)
        files = _files(d) if dec["share"] else {}
        rows.append({"group": g, "run_id": rid, "dir": d, **dec, "files": files, "bytes": sum(files.values())})
    by_group: dict[str, dict] = {}
    for r in rows:
        s = by_group.setdefault(r["group"], {"runs": 0, "shared": 0, "excluded": 0, "at_boundary": 0, "bytes": 0})
        s["runs"] += 1
        if r["share"]:
            s["shared"] += 1
            s["bytes"] += r["bytes"]
            s["at_boundary"] += 1 if r.get("at_boundary") else 0
        else:
            s["excluded"] += 1
    summary = {"rule": {k: v for k, v in rule.items() if k not in ("registry", "checked", "root")}, "groups": by_group,
               "total_runs": len(rows), "total_shared": sum(1 for r in rows if r["share"]),
               "total_bytes": sum(r["bytes"] for r in rows if r["share"])}
    if "boundary_ns" in rule:
        summary["rule"]["boundary"] = _iso(rule["boundary_ns"])
    reasons: dict[str, int] = {}
    for r in rows:
        if not r["share"]:
            reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    summary["excluded_reasons"] = reasons
    return {"summary": summary, "rows": rows}


def _manifest_path(out: str, group: str) -> str:
    return os.path.join(out, group, MANIFEST) if group else os.path.join(out, MANIFEST)


def write(p: dict, out: str) -> None:
    out_real = os.path.realpath(out)
    groups: dict[str, list] = {}
    for r in p["rows"]:
        groups.setdefault(r["group"], []).append(r)
    for g, rows in groups.items():
        mp = _manifest_path(out, g)
        old = {}
        if os.path.isfile(mp):
            with open(mp, "r", encoding="utf-8") as fh:
                old = {e["run_id"]: e for e in json.load(fh).get("runs", [])}
        for r in rows:
            dst = os.path.join(out, g, r["run_id"])
            if not os.path.realpath(dst).startswith(out_real + os.sep):
                raise SystemExit(f"refusing to write outside {out}: {dst}")
            if r["share"]:
                os.makedirs(dst, exist_ok=True)
                for name in os.listdir(dst):  # a file the view no longer reads, or one renamed .json <-> .json.gz
                    if name not in r["files"]:
                        os.remove(os.path.join(dst, name))
                for name in r["files"]:
                    shutil.copy2(os.path.join(r["dir"], name), os.path.join(dst, name))
                old[r["run_id"]] = {"run_id": r["run_id"], "shared": True, "start": r["start"], "end": r["end"],
                                    "at_boundary": r["at_boundary"],
                                    "files": {n: {"bytes": s, "sha256": _sha(os.path.join(dst, n))}
                                              for n, s in sorted(r["files"].items())}}
            else:
                removed = os.path.isdir(dst)
                if removed:
                    shutil.rmtree(dst)
                old[r["run_id"]] = {"run_id": r["run_id"], "shared": False, "reason": r["reason"],
                                    "start": r.get("start"), "end": r.get("end"),
                                    **({"removed_earlier_copy": True} if removed else {})}
        doc = {"what": "scripts/share_backtest_runs.py が写した実行と、写さなかった実行とその理由",
               "source": g or ".", "rule": p["summary"]["rule"],
               "runs": [old[k] for k in sorted(old)]}
        os.makedirs(os.path.dirname(mp), exist_ok=True)
        with open(mp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--runs-dir", default=str(REPO / "backtest_runs"))
    ap.add_argument("--out", default=str(REPO / "backtest_runs_shared"))
    ap.add_argument("--root", default=str(REPO), help="the data root whose backtest_data/phase2_sealed is read")
    ap.add_argument("--group", action="append", default=[], help="a collection under --runs-dir (repeatable)")
    ap.add_argument("--run", action="append", default=[], help="a run id (repeatable)")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--max-mb", type=float, required=True,
                    help="the most the selected files may total; no default (the owner decides how much the "
                         "repository may grow)")
    ap.add_argument("--dry-run", action="store_true", help="measure and print; copy nothing")
    a = ap.parse_args(argv)
    if not (a.all or a.group or a.run):
        ap.error("say which runs: --all, --group or --run")
    p = plan(a.runs_dir, a.root, a.group, a.run, a.all)
    s = p["summary"]
    s["total_mb"] = round(s["total_bytes"] / 1e6, 1)
    for g in s["groups"].values():
        g["mb"] = round(g["bytes"] / 1e6, 1)
    over = s["total_bytes"] > a.max_mb * 1e6
    s["copied"] = not (a.dry_run or over)
    if over:
        s["not_copied_because"] = f"合計 {s['total_mb']}MB が上限 {a.max_mb}MB を越える"
    elif a.dry_run:
        s["not_copied_because"] = "--dry-run"
    print(json.dumps(s, ensure_ascii=False, indent=1, sort_keys=True))
    if a.dry_run:
        return 0
    if over:
        return 2
    write(p, a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""The catalog of the バックテスト tab: theme -> strategy -> family (the dropdowns) -> run.

    catalog(runs_dir) -> {themes: [{id, title, summary, source, strategies: [{id, title, description: [{text, source}],
                          theme, fake, axes: [{key, label, source, values: [{value, label, note}], fixed, secondary}],
                          runs: [{run_id, group, axes: {key: value}, period, instruments, ranges, purpose, fake}],
                          unavailable: [{run_id, reason}], default_run_id, n_runs}]}], n_runs, ...}

A run's strategy is named in its record.json (config.strategy.module, or setup.name); the words about it come from the
ledger road_strategies.py (a strategy that is not in it says 「説明が台帳に無い」). The FAMILY AXES are not written
anywhere: they are found by comparing the runs of one strategy mechanically -- every leaf of record.json's `config` whose
value differs between the runs is an axis (a family key lives in config.strategy.params; the run period is one more axis when
it differs). A run with no road/ is listed last under 「古い形の走らせ(道の記録が無い)」; a road run whose road/ cannot be shown
is named, with the reason, under its strategy's `unavailable` (it is never silently dropped).
"""
from __future__ import annotations

import datetime as dt
import json
from typing import Any, Optional

from bot.monitoring import backtest_view as BV
from bot.monitoring import road_strategies as RS
from bot.monitoring import road_view as RV

LEGACY_THEME = "legacy"
LEGACY_TITLE = "古い形の走らせ(道の記録が無い)"
LEGACY_NOTE = ("road/ の無い走らせ。pipeline の trades.json・metrics.json があるだけで、道の数え方(建玉 0 → 0 を 1 取引)の表は無い。"
               "チャートと表は出さない。単独ページ(古い 10 個の詳細タブ)だけ開ける")
#: config leaves that are the strategy's identity, not a family key (module_source_sha256 is the secondary "version" axis)
SAME_BY_DEFINITION = ("strategy.module", "strategy.factory", "strategy.kind")
VERSION_KEY = "strategy.module_source_sha256"
PERIOD_KEY = "period"


def strategy_name(rec: dict) -> Optional[str]:
    st = (rec.get("config") or {}).get("strategy")
    if isinstance(st, dict) and st.get("kind") == "module" and isinstance(st.get("module"), str):
        return st["module"]
    nm = (rec.get("setup") or {}).get("name")
    return nm if isinstance(nm, str) else None


def is_synthetic(rec: dict) -> bool:
    """A run on made-up data: record.json says so itself (data[].origin = "synthetic": a generator, not a market file)."""
    return any(isinstance(d, dict) and d.get("origin") == "synthetic" for d in rec.get("data") or [])


def flatten(obj: Any, prefix: str = "", out: Optional[dict] = None) -> dict:
    """{dotted path: JSON text} of every leaf (a list is one leaf)."""
    out = {} if out is None else out
    if isinstance(obj, dict) and obj:
        for k in sorted(obj):
            flatten(obj[k], f"{prefix}.{k}" if prefix else str(k), out)
    else:
        out[prefix] = json.dumps(obj, sort_keys=True, ensure_ascii=False)
    return out


def show(v: str) -> str:
    """JSON text -> what the dropdown shows (a string without its quotes)."""
    try:
        x = json.loads(v)
    except ValueError:
        return v
    return x if isinstance(x, str) else v


def _iso_day(ns: Optional[int]) -> str:
    return "—" if ns is None else dt.datetime.fromtimestamp(ns / 1e9, tz=dt.timezone.utc).strftime("%Y-%m-%d")


def _sort_key(v: str):
    if v == "—":
        return (2, 0.0, "")
    try:
        return (0, float(show(v)), "")
    except ValueError:
        return (1, 0.0, show(v))


def _label(name: Optional[str], path: str) -> tuple[str, str]:
    if path == PERIOD_KEY:
        return "期間(UTC・終わりの日を含む)", "record.json の engine の first_time_ns / last_time_ns"
    if path == VERSION_KEY:
        return "戦略のコード版", "record.json の config.strategy.module_source_sha256"
    pre = "strategy.params."
    if path.startswith(pre):
        lab, src = RS.param_label(name, path[len(pre):])
        key = path[len(pre):]
        return (lab if lab == key else f"{lab}({key})"), f"record.json の config.{path}({src})"
    return path, f"record.json の config.{path}"


def _strategy_entry(name: Optional[str], runs: list[dict], unavailable: list[dict]) -> dict:
    led = RS.strategy_entry(name)
    flat = [r.pop("_flat") for r in runs]
    paths = sorted({p for f in flat for p in f})
    diff = [p for p in paths if p not in SAME_BY_DEFINITION and len({f.get(p, "—") for f in flat}) > 1]
    version = VERSION_KEY in diff
    keys = [p for p in diff if p != VERSION_KEY]
    keys.sort(key=lambda p: (0 if p.startswith("strategy.params.") else 1, p))
    for r, f in zip(runs, flat):
        r["axes"] = {p: f.get(p, "—") for p in keys}
        if version:
            r["_version"] = f.get(VERSION_KEY, "—")
    axes = []
    for p in keys:
        vals = sorted({r["axes"][p] for r in runs}, key=_sort_key)
        lab, src = _label(name, p)
        axes.append({"key": p, "label": lab, "source": src, "fixed": False, "secondary": False,
                     "values": [{"value": v, "label": show(v), "note": ""} for v in vals]})
    # runs with the same axes values are told apart by the code version (the secondary axis), as before
    combos: dict = {}
    for r in runs:
        combos[tuple(r["axes"].values())] = combos.get(tuple(r["axes"].values()), 0) + 1
    if version and any(n > 1 for n in combos.values()):
        lab, src = _label(name, VERSION_KEY)
        vals = sorted({r["_version"] for r in runs})
        axes.append({"key": VERSION_KEY, "label": lab, "source": src, "fixed": False, "secondary": True,
                     "values": [{"value": v, "label": v[:12], "note": ""} for v in vals]})
        for r in runs:
            r["axes"][VERSION_KEY] = r["_version"]
    for r in runs:
        r.pop("_version", None)
    order = {a["key"]: {e["value"]: i for i, e in enumerate(a["values"])} for a in axes}
    runs.sort(key=lambda r: (tuple(order[a["key"]][r["axes"][a["key"]]] for a in axes), r["run_id"]))
    return {"id": f"s:{name}", "kind": "road", "name": name, "title": led["title"], "description": led["description"],
            "theme": led["theme"], "fake": bool(led.get("fake")) or any(r.get("fake") for r in runs), "axes": axes, "runs": runs,
            "unavailable": unavailable,
            "n_runs": len(runs), "default_run_id": runs[0]["run_id"] if runs else None}


def catalog(runs_dir: Any) -> dict:
    found = BV.find_runs(runs_dir)
    by_strategy: dict = {}
    legacy: dict = {}
    broken: list = []
    for rid, d, group in found:
        try:
            rec = RV.record_of(d)
        except (OSError, ValueError) as exc:
            broken.append({"run_id": rid, "reason": f"record.json が読めない({type(exc).__name__})"})
            continue
        name = strategy_name(rec)
        st = RV.status(d)
        if not RV.has_road(d):
            legacy.setdefault(group, []).append({"run_id": rid, "group": group, "axes": {"run": rid[:12]}, "legacy": True,
                                                 "purpose": rec.get("purpose")})
            continue
        if not st.ok:
            by_strategy.setdefault(name, {"runs": [], "unavailable": []})["unavailable"].append({"run_id": rid, "reason": st.reason})
            continue
        first, last = RV.engine_period(rec)
        flat = flatten(rec.get("config") or {})
        flat[PERIOD_KEY] = json.dumps(f"{_iso_day(first)} 〜 {_iso_day(last - 1 if last else None)}", ensure_ascii=False)
        cfg = rec.get("config") or {}
        insts = [i.get("name") for i in cfg.get("instruments") or [] if isinstance(i, dict)] or [cfg.get("instrument")]
        run = {"run_id": rid, "group": group, "_flat": flat, "purpose": rec.get("purpose"),
               "period": {"first_s": None if first is None else first // 10**9, "last_s": None if last is None else last // 10**9},
               "instruments": [i for i in insts if i], "fake": bool(RS.strategy_entry(name).get("fake")) or is_synthetic(rec),
               "ranges": []}
        by_strategy.setdefault(name, {"runs": [], "unavailable": []})["runs"].append(run)
    themes: dict = {}
    for name, v in by_strategy.items():
        ent = _strategy_entry(name, v["runs"], v["unavailable"]) if v["runs"] else None
        if ent is None:
            led = RS.strategy_entry(name)
            ent = {"id": f"s:{name}", "kind": "road", "name": name, "title": led["title"], "description": led["description"],
                   "theme": led["theme"], "fake": bool(led.get("fake")), "axes": [], "runs": [], "unavailable": v["unavailable"],
                   "n_runs": 0, "default_run_id": None}
        themes.setdefault(ent["theme"], []).append(ent)
    out_themes = []
    order = [t for t in RS.THEMES if t not in (RS.THEME_FAKE, RS.THEME_UNLISTED)] + [RS.THEME_FAKE, RS.THEME_UNLISTED]
    for tid in order:
        if tid in themes:
            th = RS.THEMES[tid]
            out_themes.append({"id": tid, "title": th["title"], "summary": th["summary"], "source": th["source"],
                               "sources": [th["source"]], "fake": tid == RS.THEME_FAKE,
                               "strategies": sorted(themes[tid], key=lambda s: s["title"])})
    if legacy:
        strategies = []
        for group, runs in sorted(legacy.items()):
            runs.sort(key=lambda r: r["run_id"])
            strategies.append({
                "id": f"legacy:{group}", "kind": "legacy", "title": group or "(組なし)", "theme": LEGACY_THEME, "fake": False,
                "description": [{"text": LEGACY_NOTE, "source": "src/bot/monitoring/road_catalog.py"}],
                "axes": [{"key": "run", "label": "実行 ID", "source": "実行 ID の先頭 12 文字", "fixed": len(runs) == 1,
                          "secondary": False, "values": [{"value": r["axes"]["run"], "label": r["axes"]["run"], "note": ""} for r in runs]}],
                "runs": runs, "unavailable": [], "n_runs": len(runs), "default_run_id": runs[0]["run_id"]})
        out_themes.append({"id": LEGACY_THEME, "title": LEGACY_TITLE, "summary": LEGACY_NOTE, "source": "src/bot/monitoring/road_catalog.py",
                           "sources": [], "fake": False, "strategies": strategies})
    n_road = sum(s["n_runs"] for t in out_themes if t["id"] != LEGACY_THEME for s in t["strategies"])
    return {"themes": out_themes, "n_runs": len(found), "n_road_runs": n_road, "n_legacy_runs": sum(len(r) for r in legacy.values()),
            "broken": broken}

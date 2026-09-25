"""Item 1 battery: compare an observation with a scene's expected answer.

compare(expected, obs, scene) -> (class, detail)
    class is 「正解と一致」 or 「不一致」 (the runner decides 「対応なし」/「結果なし」).

Rules (DEFINITIONS.md「判定の決まり」):
- events:    per dataset, the same number of records in the same order; each
             record matches on every key the expected record names (ints and
             strings exactly; floats exactly, or within the scene's relative `tol`).
- anomalies: per dataset, the same multiset of (kind, t_ns).
- hashes:    for every expected path, the same lowercase hex; no path missing.
- adjusted:  the same set of codes; per code, records as for events.
- universe:  per expected date, the same set of codes.
- paths:     both the "event" and the "vector" path carry every expected key,
             each equals the expected value (as events), AND the two paths are
             bit-identical to each other on every expected key.
- speed:     the two paths are bit-identical on the named keys, and
             timing.vector_s < timing.event_s (the values themselves are judged by `paths`).
"""
from __future__ import annotations

import hashlib
import json
import math
import struct

CLASSES = ("正解と一致", "対応なし", "不一致", "結果なし")


def _bits(x):
    if isinstance(x, float):
        return struct.pack("<d", x).hex()
    if isinstance(x, (list, tuple)):
        return [_bits(v) for v in x]
    if isinstance(x, dict):
        return {k: _bits(v) for k, v in sorted(x.items())}
    return x


def _num_eq(e, o, tol):
    if e is None or o is None:
        return e is None and o is None
    if isinstance(e, bool) or isinstance(o, bool):
        return e == o
    if isinstance(e, int) and not isinstance(e, bool) and isinstance(o, int) and not isinstance(o, bool):
        return e == o
    try:
        ef, of = float(e), float(o)
    except (TypeError, ValueError):
        return False
    if math.isnan(of):
        return False
    if tol is None:
        return ef == of
    return abs(ef - of) <= tol * max(1.0, abs(ef))


def _val_eq(key, e, o, tol):
    if isinstance(e, str) or isinstance(o, str):
        return isinstance(o, str) and e == o
    if key in ("t_ns", "start_ns"):
        return isinstance(o, int) and not isinstance(o, bool) and e == o
    return _num_eq(e, o, tol)


def _records(exp_list, obs_list, tol, where):
    if not isinstance(obs_list, (list, tuple)):
        return f"{where}: 記録の列が無い(値 {str(obs_list)[:80]})"
    if len(exp_list) != len(obs_list):
        return f"{where}: 件数 {len(obs_list)}(正解 {len(exp_list)})"
    for i, (e, o) in enumerate(zip(exp_list, obs_list)):
        if not isinstance(o, dict):
            return f"{where}[{i}]: 記録が dict でない"
        for k, ev in e.items():
            if k not in o:
                return f"{where}[{i}].{k}: 欄が無い"
            if not _val_eq(k, ev, o[k], tol):
                return f"{where}[{i}].{k}: {o[k]!r}(正解 {ev!r})"
    return None


def _seq(key, exp_list, obs_list, tol, where):
    if not isinstance(obs_list, (list, tuple)) or len(obs_list) != len(exp_list):
        return f"{where}: 長さ {len(obs_list) if isinstance(obs_list, (list, tuple)) else '-'}(正解 {len(exp_list)})"
    for i, (e, o) in enumerate(zip(exp_list, obs_list)):
        if not _num_eq(e, o, tol):
            return f"{where}[{i}]: {o!r}(正解 {e!r})"
    return None


def compare(exp: dict, obs: dict, scene: dict) -> tuple[str, str]:
    tol = scene.get("tol")
    if not isinstance(obs, dict):
        return "不一致", "観測が dict でない"
    for key, ev in exp.items():
        if key == "events":
            got = obs.get("events") or {}
            for name, recs in ev.items():
                d = _records(recs, got.get(name), tol, f"events.{name}")
                if d:
                    return "不一致", d
        elif key == "anomalies":
            got = obs.get("anomalies")
            if not isinstance(got, dict):
                return "不一致", "anomalies が返らない(異常を報せる口が無いか、黙って結合した)"
            for name, lst in ev.items():
                o = got.get(name)
                if not isinstance(o, (list, tuple)):
                    return "不一致", f"anomalies.{name} が無い"
                want = sorted((a["kind"], a["t_ns"]) for a in lst)
                try:
                    have = sorted((a["kind"], a["t_ns"]) for a in o)
                except (KeyError, TypeError):
                    return "不一致", f"anomalies.{name} の形が違う: {str(o)[:120]}"
                if want != have:
                    return "不一致", f"anomalies.{name}: {have}(正解 {want})"
        elif key == "hashes":
            got = obs.get("hashes") or {}
            for p, h in ev.items():
                if str(got.get(p, "")).lower() != h:
                    return "不一致", f"hashes[{p}]: {got.get(p)!r}(正解 {h})"
        elif key == "adjusted":
            got = obs.get("adjusted") or {}
            if set(got) != set(ev):
                return "不一致", f"adjusted の銘柄 {sorted(got)}(正解 {sorted(ev)})"
            for code, recs in ev.items():
                d = _records(recs, got.get(code), tol, f"adjusted.{code}")
                if d:
                    return "不一致", d
        elif key == "universe":
            got = obs.get("universe") or {}
            for day, codes in ev.items():
                if sorted(got.get(day) or []) != sorted(codes) or day not in got:
                    return "不一致", f"universe[{day}]: {sorted(got.get(day) or [])}(正解 {sorted(codes)})"
        elif key == "paths":
            paths = obs.get("paths") or {}
            for side in ("event", "vector"):
                p = paths.get(side)
                if not isinstance(p, dict):
                    return "不一致", f"paths.{side} が無い"
                for k, e in ev.items():
                    if k not in p:
                        return "不一致", f"paths.{side}.{k} が無い"
                    d = _records(e, p[k], tol, f"paths.{side}.{k}") if k == "bars" else _seq(k, e, p[k], tol, f"paths.{side}.{k}")
                    if d:
                        return "不一致", d
            for k in ev:
                if _bits(paths["event"][k]) != _bits(paths["vector"][k]):
                    return "不一致", f"paths.{k}: 事象駆動と近道がビット単位で一致しない"
        elif key == "speed":
            paths = obs.get("paths") or {}
            ev_, vc = paths.get("event"), paths.get("vector")
            if not isinstance(ev_, dict) or not isinstance(vc, dict):
                return "不一致", "paths.event / paths.vector が無い"
            for k in ev["keys"]:
                if k not in ev_ or k not in vc or _bits(ev_[k]) != _bits(vc[k]):
                    return "不一致", f"paths.{k}: 事象駆動と近道がビット単位で一致しない(または欄が無い)"
            tm = obs.get("timing") or {}
            try:
                es, vs = float(tm["event_s"]), float(tm["vector_s"])
            except (KeyError, TypeError, ValueError):
                return "不一致", "timing.event_s / vector_s が無い"
            if not vs < es:
                return "不一致", f"近道({vs:.4f} 秒)が事象駆動({es:.4f} 秒)より速くない"
        else:
            return "不一致", f"判定の決まりの無い欄 {key}"
    return "正解と一致", ""


def digest(obj) -> str:
    """Digest of an observation, excluding wall-clock timings (they differ between runs by nature)."""
    def strip(o):
        if isinstance(o, dict):
            return {k: strip(v) for k, v in o.items() if k != "timing"}
        if isinstance(o, list):
            return [strip(v) for v in o]
        return o
    return hashlib.sha256(json.dumps(_bits(strip(obj)), sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:16]

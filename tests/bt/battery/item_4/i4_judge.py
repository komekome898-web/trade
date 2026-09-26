"""Item 4 battery: compare an observation with a scene's expected answer.

compare(expected, obs, scene) -> (class, detail)
    class is 「正解と一致」 or 「不一致」 (the runner decides 「対応なし」/「結果なし」).

Rules (DEFINITIONS.md「判定の決まり」), per judged key:
- fills:        the same number of fills in the same order; each fill equal on the judged fields
                (bar and side exactly, price and size as floats).
- pnls/equity:  the same length, element-wise equal as floats.
- metrics:      every one of the 12 keys present and equal (ints exactly, floats as floats, inf = inf).
- missed_fills: equal int.
- invariants:   (I4-2 grid only) no violation of the stated invariants in the observed fills (invariants()).
- pfills:       per instrument, the same fills in order: t_ns exactly, side exactly, px and qty as floats.
- pnl:          per instrument, equal as floats.  events_read: per dataset, equal int.
- run_record:   purpose equal; every expected path's sha256 equal (lowercase hex); other paths may be present.
- export:       purpose equal; num_trades per instrument equal.
- dashboard:    obs {"tabs": [{"label", "text"}]}: every expected tab name is the START of exactly one label,
                and the banner text is contained in the text of EVERY tab.
- splits:       the three row-position lists equal.
- engine/reference/legacy/spec: the sub-observation judged by the sub-judge.
Floats are equal when |a - b| <= 1e-9 x max(1, |a|, |b|) (the arithmetic order of a target may differ in the last bits).
"""
from __future__ import annotations

import hashlib
import json
import math
import struct

CLASSES = ("正解と一致", "対応なし", "不一致", "結果なし")
TOL = 1e-9


def feq(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        return False
    a, b = float(a), float(b)
    if math.isinf(a) or math.isinf(b) or math.isnan(a) or math.isnan(b):
        return a == b
    return abs(a - b) <= TOL * max(1.0, abs(a), abs(b))


def _bits(x):
    if isinstance(x, float):
        return struct.pack("<d", x).hex()
    if isinstance(x, (list, tuple)):
        return [_bits(v) for v in x]
    if isinstance(x, dict):
        return {str(k): _bits(v) for k, v in sorted(x.items(), key=lambda kv: str(kv[0]))}
    return x


def digest(obj) -> str:
    return hashlib.sha256(json.dumps(_bits(obj), ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()[:12]


def _flist(name, exp, got):
    if not isinstance(got, (list, tuple)):
        return f"{name}: 観測が列でない({type(got).__name__})"
    if len(exp) != len(got):
        return f"{name}: 長さ {len(got)}(正解 {len(exp)})"
    for k, (e, g) in enumerate(zip(exp, got)):
        if not feq(e, g):
            return f"{name}[{k}] = {g!r}(正解 {e!r})"
    return None


def _fills(exp, got, fields):
    if not isinstance(got, list):
        return f"fills: 観測が列でない({type(got).__name__})"
    if len(exp) != len(got):
        return f"fills: {len(got)} 件(正解 {len(exp)} 件): 観測 {[(g.get('bar'), g.get('side'), g.get('price')) for g in got if isinstance(g, dict)][:8]}"
    for k, (e, g) in enumerate(zip(exp, got)):
        for f in fields:
            ev, gv = e[f], (g or {}).get(f)
            ok = (ev == gv) if f in ("bar", "side") else feq(ev, gv)
            if not ok:
                return f"fills[{k}].{f} = {gv!r}(正解 {ev!r})"
    return None


def _metrics(exp, got):
    if not isinstance(got, dict):
        return "metrics: 観測が dict でない"
    for k, ev in exp.items():
        if k not in got:
            return f"metrics.{k} が無い"
        gv = got[k]
        if isinstance(ev, int) and not isinstance(ev, bool):
            ok = isinstance(gv, (int, float)) and not isinstance(gv, bool) and gv == ev
        else:
            ok = feq(ev, gv)
        if not ok:
            return f"metrics.{k} = {gv!r}(正解 {ev!r})"
    return None


def _pfills(exp, got):
    if not isinstance(got, dict):
        return "fills: 観測が銘柄ごとの dict でない"
    for inst, el in exp.items():
        gl = got.get(inst)
        if not isinstance(gl, list) or len(gl) != len(el):
            return f"fills[{inst}]: {None if gl is None else len(gl)} 件(正解 {len(el)} 件)"
        for k, (e, g) in enumerate(zip(el, gl)):
            if g.get("t_ns") != e["t_ns"] or g.get("side") != e["side"] or not feq(e["px"], g.get("px")) \
                    or not feq(e["qty"], g.get("qty")):
                return f"fills[{inst}][{k}] = {g!r}(正解 {e!r})"
    return None


def invariants(case: dict, obs: dict) -> list[str]:
    """I4-2: the stated invariants, checked on the observed fills/pnls/equity of one taker-only case."""
    v = []
    fills, pnls, eq = obs.get("fills") or [], obs.get("pnls") or [], obs.get("equity") or []
    c = case["config"]
    fee = c["costs"]["taker_fee_pct"]
    sig_bars = {s["bar"] for s in case["signals"]}
    opens, closes = fills[0::2], fills[1::2]
    for k, f in enumerate(fills):
        want = "OPEN" if k % 2 == 0 else "CLOSE"
        if not str(f.get("side", "")).startswith(want):
            v.append(f"約定 {k} は {want} のはずが {f.get('side')}(建てと決済が交互でない)")
        if f.get("bar", 0) - 1 not in sig_bars:
            v.append(f"約定 {k}(足 {f.get('bar')})の前の足に合図が無い(合図より後でない)")
    for k, (o, x) in enumerate(zip(opens, closes)):
        if o["side"].split("_")[1] != x["side"].split("_")[1]:
            v.append(f"往復 {k} の向きが建てと決済で違う")
        if not feq(o["size"], x["size"]):
            v.append(f"往復 {k} の決済の数量 {x['size']} が建ての数量 {o['size']} と違う")
        d = 1 if o["side"] == "OPEN_LONG" else -1
        want = (x["price"] - o["price"]) * o["size"] * d - x["size"] * x["price"] * fee / 100 - o["size"] * o["price"] * fee / 100
        if k >= len(pnls) or not feq(want, pnls[k]):
            v.append(f"往復 {k} の損益 {pnls[k] if k < len(pnls) else None} が約定から出る値 {want} と違う(損益の恒等式)")
    if len(pnls) != len(closes):
        v.append(f"損益の数 {len(pnls)} が決済の数 {len(closes)} と違う")
    bars = case["bars"]
    if len(eq) != len(bars):
        v.append(f"資産の推移の長さ {len(eq)} が足の数 {len(bars)} と違う")
    else:
        for i, b in enumerate(bars):
            e = c["initial_equity"]
            for k, o in enumerate(opens):
                x = closes[k] if k < len(closes) else None
                if x is not None and x["bar"] <= i:
                    e += pnls[k] if k < len(pnls) else 0.0
                elif o["bar"] <= i:
                    d = 1 if o["side"] == "OPEN_LONG" else -1
                    e += (b["close"] - o["price"]) * o["size"] * d - o["size"] * o["price"] * fee / 100
            if not feq(e, eq[i]):
                v.append(f"足 {i} の資産 {eq[i]} が元本 + 実現損益 + 含み損益 = {e} と違う(資産の恒等式)")
                break
    return v


def judge_obs(exp, obs, spec, scene=None, case=None):
    """None when equal, else the first difference (a Japanese sentence)."""
    if not isinstance(obs, dict):
        return f"観測が dict でない({type(obs).__name__})"
    for key, sub in spec.items():
        if key in ("engine", "reference", "legacy", "spec"):
            if key not in obs:
                return f"{key} の出力が無い"
            d = judge_obs(exp[key], obs[key], sub, scene, case)
            if d:
                return f"{key}: {d}"
            continue
        if key == "invariants":
            iv = invariants(case, obs)
            if iv:
                return "不変条件: " + iv[0]
            continue
        if key == "pfills":
            d = _pfills(exp["fills"], obs.get("fills"))
            if d:
                return d
            continue
        if key not in obs:
            return f"{key} が観測に無い"
        e, g = exp[key], obs[key]
        if key == "fills":
            d = _fills(e, g, sub)
        elif key in ("pnls", "equity"):
            d = _flist(key, e, g)
        elif key == "metrics":
            d = _metrics(e, g)
        elif key == "missed_fills":
            d = None if isinstance(g, int) and not isinstance(g, bool) and g == e else f"missed_fills = {g!r}(正解 {e})"
        elif key == "pnl":
            d = next((f"pnl[{k}] = {g.get(k) if isinstance(g, dict) else g!r}(正解 {v})" for k, v in e.items()
                      if not isinstance(g, dict) or not feq(v, g.get(k))), None)
        elif key == "events_read":
            d = next((f"events_read[{k}] = {g.get(k) if isinstance(g, dict) else g!r}(正解 {v})" for k, v in e.items()
                      if not isinstance(g, dict) or g.get(k) != v), None)
        elif key == "run_record":
            d = None
            if not isinstance(g, dict) or g.get("purpose") != e["purpose"]:
                d = f"run_record.purpose = {(g or {}).get('purpose') if isinstance(g, dict) else g!r}(正解 {e['purpose']})"
            else:
                got = g.get("data_sha256") or {}
                d = next((f"run_record.data_sha256[{p}] = {got.get(p)!r}(正解 {h})" for p, h in e["data_sha256"].items()
                          if str(got.get(p, "")).lower() != h), None)
        elif key == "export":
            d = None
            if not isinstance(g, dict) or g.get("purpose") != e["purpose"]:
                d = f"export.purpose = {(g or {}).get('purpose') if isinstance(g, dict) else g!r}(正解 {e['purpose']})"
            else:
                nt = g.get("num_trades") or {}
                d = next((f"export.num_trades[{k}] = {nt.get(k)!r}(正解 {v})" for k, v in e["num_trades"].items()
                          if nt.get(k) != v), None)
        elif key == "dashboard":
            d = _dashboard(e, g)
        elif key == "splits":
            d = next((f"splits.{k} = {(g or {}).get(k) if isinstance(g, dict) else g!r}(正解 {v})" for k, v in e.items()
                      if not isinstance(g, dict) or list(g.get(k) or []) != v), None)
        else:
            d = f"判定の決まりに無い鍵 {key}"
        if d:
            return d
    return None


def _dashboard(e, g):
    tabs = (g or {}).get("tabs") if isinstance(g, dict) else None
    if not isinstance(tabs, list) or not tabs:
        return "dashboard.tabs が無い"
    labels = [str(t.get("label", "")) for t in tabs]
    for name in e["tabs"]:
        hits = [lb for lb in labels if lb.startswith(name)]
        if len(hits) != 1:
            return f"dashboard: 「{name}」で始まるタブが {len(hits)} 個(タブ {labels})"
    for t in tabs:
        if e["banner"] not in str(t.get("text", "")):
            return f"dashboard: タブ「{t.get('label')}」に注記「{e['banner']}」が無い"
    return None


def compare(exp, obs, scene):
    """(class, detail) of one observation against the scene's expected answer."""
    if "cases" in scene:
        for k, (e, o, c) in enumerate(zip(exp, obs, scene["cases"])):
            d = judge_obs(e, o, scene["judge"], scene, c)
            if d:
                return "不一致", f"場合 {k}: {d}"
        return "正解と一致", f"{len(exp)} の場合すべて"
    d = judge_obs(exp, obs, scene["judge"], scene)
    return ("不一致", d) if d else ("正解と一致", "")

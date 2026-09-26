"""Item 2 battery: turn a target's observation into the expected-answer keys and
classify one scene run.

Correctness classes (委任文 §3「比較の表」, 場面集の規則 5, best first):
  正解と一致 > 対応なし(明示的に拒否する・例外を出す)> 不一致(値)> 結果なし

Derived keys are computed HERE from the raw observation (fills / orders / ...),
never by the adapter, so every target is read by the same code.
"""
from __future__ import annotations

import hashlib
import json
import math

CLASSES = ("正解と一致", "対応なし", "不一致", "結果なし")
TOL = 1e-9


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def close(a, b) -> bool:
    if _num(a) and _num(b):
        if isinstance(a, float) or isinstance(b, float):
            if math.isnan(a) or math.isnan(b):
                return False
            return abs(a - b) <= TOL + TOL * max(abs(a), abs(b))
        return a == b
    return a == b


def derive(obs: dict, key: str, send_times: dict):
    """Value of one expected-answer key from a raw observation; KeyError when the
    observation does not carry what the key needs."""
    if key.startswith("range."):
        _, side, rest = key.split(".", 2)
        return derive(obs["range"][side], rest, send_times)
    head, _, rest = key.partition(".")
    fills = obs.get("fills", [])
    if head in ("filled", "avg_px", "first_fill_t", "fee", "lat_in"):
        mine = [f for f in fills if f["ref"] == rest]
        if head == "filled":
            if not mine and rest not in obs.get("orders", {}):
                raise KeyError(f"no order {rest}")
            return float(sum(f["qty"] for f in mine))
        if not mine:
            raise KeyError(f"no fill for {rest}")
        if head == "avg_px":
            q = sum(f["qty"] for f in mine)
            return sum(f["px"] * f["qty"] for f in mine) / q
        if head == "first_fill_t":
            return min(int(f["t"]) for f in mine)
        if head == "fee":
            return float(sum(f.get("fee", 0.0) for f in mine))
        if head == "lat_in":
            return min(int(f["t"]) for f in mine) - send_times[rest]
    if head == "cum":
        ref, cp_t = rest.split("@")
        return float(sum(f["qty"] for f in fills if f["ref"] == ref and int(f["t"]) <= cp_t_value(cp_t, send_times)))
    if head == "status":
        return obs["orders"][rest]["status"]
    if head == "sent":
        return int(obs.get("sent", {})[rest])
    if head == "notice":
        ref, kind = rest.split(".")
        n = obs["notices"][ref]
        if kind == "terminal":  # the order ended without a fill: rejected, or canceled / expired on arrival
            ts = [n[k] for k in ("reject", "cancel") if k in n]
            if not ts:
                raise KeyError(f"no reject/cancel notice for {ref}")
            return int(min(ts))
        return int(n[kind])
    if head == "seen":
        return int(obs["seen"][rest])
    if head in ("account", "costs"):
        return obs[head][rest]
    raise KeyError(key)


def cp_t_value(label, send_times):
    return send_times["@checkpoints"][label]


def check(exp, got) -> bool:
    if isinstance(exp, dict) and "op" in exp:
        op, v = exp["op"], exp["v"]
        if op == "ge":
            return _num(got) and got >= v
        if op == "le":
            return _num(got) and got <= v
        if op == "in":
            return any(close(got, x) for x in v)
        raise ValueError(op)
    return close(exp, got)


def compare(expected: dict, obs: dict, inp: dict) -> tuple[str, str]:
    """Return (class, detail) for a completed observation."""
    send = {a["ref"]: a["t"] for a in inp["actions"] if a.get("op") == "place"}
    send["@checkpoints"] = inp.get("checkpoints", {})
    bad = []
    for k, e in expected.items():
        try:
            g = derive(obs, k, send)
        except (KeyError, TypeError, IndexError) as exc:
            bad.append(f"{k}: 期待 {_fmt(e)} / 出力に無い({type(exc).__name__}: {exc})")
            continue
        if not check(e, g):
            bad.append(f"{k}: 期待 {_fmt(e)} / 出力 {_fmt(g)}")
    if bad:
        return "不一致", "; ".join(bad)
    return "正解と一致", ""


def _fmt(x):
    if isinstance(x, dict) and "op" in x:
        return f"{x['op']} {x['v']}"
    return json.dumps(x, ensure_ascii=False) if not isinstance(x, str) else x


def canon(obs) -> str:
    """Canonical JSON of an observation (for the two-run identity check)."""
    return json.dumps(obs, sort_keys=True, ensure_ascii=False, default=str)


def digest(obj) -> str:
    return hashlib.sha256(canon(obj).encode()).hexdigest()[:16]

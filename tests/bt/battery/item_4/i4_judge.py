"""Item 4 battery: compare an observation with a scene's expected answer.

compare(expected, obs, scene) -> (class, detail)
    class is 「正解と一致」 or 「不一致」 (the runner decides 「対応なし」/「結果なし」).

Rules (DEFINITIONS.md「判定の決まり」), per judged key:
- fills:        the same number of fills in the same order; each fill equal on the judged fields
                (bar and side exactly, price and size as floats).
- pnls/equity:  the same length, element-wise equal as floats.
- metrics:      every one of the 12 keys present and equal (ints exactly, floats as floats, inf = inf).
- missed_fills: equal int.
- invariants:   (I4-2 grids) no violation of the stated invariants I1..I12 (INVARIANTS, invariants()); a prefix
                case is also judged by prefix_diff against its full case (no look-ahead).
- calls:        (op delivery) the views (views(): calls that see nothing dropped, a call seeing the same bars as
                the call before merged) equal the expected one per bar: seen, last_t_ns (exactly), last_close.
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


INVARIANTS = {
    "I1": "建てと決済が交互で、決済の向きは建ての向きと同じ",
    "I2": "数量の保存: 建ての数量は正、決済の数量 = 建ての数量(建ての数量の値そのもの = R-A1 は正解つきの場面と格子で見る)",
    "I3": "約定の足は 1 以上で、決済は建てより後の足、次の建ては前の決済より後の足",
    "I4": "建てには原因の合図がある(taker: 前の足に建ての向きの合図、maker: 寿命の本数の中に建ての向きの合図)",
    "I5": "向き・マスク・空売りの許可を守る(R-E1〜R-E3・R-T4)",
    "I6": "損益の恒等式 R-A3(建ての率は執行で決まり、決済の率は taker か maker のどちらか、持ち越しは R-S1)",
    "I7": "資産の恒等式 R-A4(資産の推移の長さ = 足の数)",
    "I8": "損益の数 = 決済の数",
    "I9": "保有の上限を超えない(R-H1)",
    "I10": "起きた出口を飛ばさない: 逆指値の水準に届いた足・利確と maker の利確の水準を厳密に通過した足・構造的な逆指値の出口の足・"
           "taker の決済の合図の次の足より後まで建玉が残らない",
    "I11": "taker の建ての合図を飛ばさない: 建玉の無い足の始値に、許された建ての合図が待っていれば、その足で建つ",
    "I12": "maker の建ての指値を飛ばさない: 建玉の無い足 p の許された建ての合図の指値(足 p の終値)を、次の合図の前・寿命の中の足が厳密に"
           "通過したら、その足までに建つ",
}
_EPS = 1e-9


def _dir(side):
    return 1 if str(side).endswith("LONG") else -1


def invariants(case: dict, obs: dict) -> list[str]:
    """I4-2: the stated invariants I1..I12 on the observed fills / pnls / equity of one case, read with the case's
    input only (bars, signals, config); every case of every path (taker or maker, stops, take-profits, carry, time
    exit, wick exit, masks, sides, costs).  Returns the violations (Japanese sentences)."""
    v = []
    fills, pnls, eq = obs.get("fills") or [], obs.get("pnls") or [], obs.get("equity") or []
    c, bars = case["config"], case["bars"]
    n = len(bars)
    costs = c["costs"]
    sig = {s["bar"]: s["signal"] for s in case["signals"]}
    taker = c["execution"] == "taker"
    entry_rate = costs["taker_fee_pct"] if taker else costs["maker_fee_pct"]
    exit_rates = sorted({costs["taker_fee_pct"], costs["maker_fee_pct"]})
    per_bar = c["swap_daily_pct"] / 100 * (case["bar_seconds"] / 86400.0)
    closes = [b["close"] for b in bars]
    names = {"OPEN_LONG", "OPEN_SHORT", "CLOSE_LONG", "CLOSE_SHORT"}
    for k, f in enumerate(fills):
        want = "OPEN" if k % 2 == 0 else "CLOSE"
        if f.get("side") not in names or not str(f.get("side")).startswith(want):
            return [f"I1: 約定 {k} は {want}_* のはずが {f.get('side')}"]
        if not isinstance(f.get("bar"), int) or not 1 <= f["bar"] < n:
            return [f"I3: 約定 {k} の足 {f.get('bar')} が 1〜{n - 1} に無い"]
    trips = [(fills[k], fills[k + 1] if k + 1 < len(fills) else None) for k in range(0, len(fills), 2)]
    prev_close = 0
    matched_entry_fee = []
    for k, (o, x) in enumerate(trips):
        d = _dir(o["side"])
        if x is not None and _dir(x["side"]) != d:
            v.append(f"I1: 往復 {k} の向きが建て {o['side']} と決済 {x['side']} で違う")
        if not (isinstance(o.get("size"), (int, float)) and o["size"] > 0):
            v.append(f"I2: 往復 {k} の建ての数量 {o.get('size')} が正でない")
        if x is not None and not feq(x["size"], o["size"]):
            v.append(f"I2: 往復 {k} の決済の数量 {x['size']} が建ての数量 {o['size']} と違う")
        if o["bar"] <= prev_close and k > 0:
            v.append(f"I3: 往復 {k} の建て(足 {o['bar']})が前の決済(足 {prev_close})より後でない")
        if x is not None and x["bar"] <= o["bar"]:
            v.append(f"I3: 往復 {k} の決済(足 {x['bar']})が建て(足 {o['bar']})より後でない")
        prev_close = x["bar"] if x is not None else n
        L = 1 if taker else c["maker_timeout_bars"]
        want_sig = "BUY" if d > 0 else "SELL"
        cause = [q for q in range(max(0, o["bar"] - L), o["bar"]) if sig.get(q) == want_sig]
        if not cause:
            v.append(f"I4: 往復 {k} の建て(足 {o['bar']})の前 {L} 本に {want_sig} の合図が無い")
        if d < 0 and (not c["allow_short"] or c["entry_sides"] == "long"):
            v.append(f"I5: 往復 {k} は売り建てだが、空売りを許さないか向きが long")
        if d > 0 and c["entry_sides"] == "short":
            v.append(f"I5: 往復 {k} は買い建てだが、向きが short")
        if c["entry_mask"] is not None and cause and not any(c["entry_mask"][q] for q in cause):
            v.append(f"I5: 往復 {k} の建ての原因の合図の足のマスクが全部 False")
        efee = o["size"] * o["price"] * entry_rate / 100
        matched_entry_fee.append(efee)
        last = x["bar"] if x is not None else n - 1
        carry = sum(o["size"] * closes[j - 1] * per_bar for j in range(o["bar"] + 1, last + 1))
        if x is not None:
            if k >= len(pnls):
                v.append(f"I8: 往復 {k} の損益が無い")
            else:
                base = (x["price"] - o["price"]) * o["size"] * d - efee - carry
                if not any(feq(base - x["size"] * x["price"] * r / 100, pnls[k]) for r in exit_rates):
                    v.append(f"I6: 往復 {k} の損益 {pnls[k]} が、約定から出る値(決済の率 {exit_rates} のどれで計算しても)と違う")
            if c["max_hold_bars"] is not None and x["bar"] - o["bar"] > c["max_hold_bars"]:
                v.append(f"I9: 往復 {k} は {x['bar'] - o['bar']} 本持った(上限 {c['max_hold_bars']})")
        elif c["max_hold_bars"] is not None and (n - 1) - o["bar"] >= c["max_hold_bars"]:
            v.append(f"I9: 終わりに残った建玉(足 {o['bar']} で建てた)が上限 {c['max_hold_bars']} 本を超えて残った")
        v += _skipped_exits(case, k, o, x, d)
    closed = [x for _, x in trips if x is not None]
    if len(pnls) != len(closed):
        v.append(f"I8: 損益の数 {len(pnls)} が決済の数 {len(closed)} と違う")
    v += _skipped_entries(case, trips)
    if len(eq) != n:
        v.append(f"I7: 資産の推移の長さ {len(eq)} が足の数 {n} と違う")
    elif not v:
        for i in range(n):
            e = c["initial_equity"]
            for k, (o, x) in enumerate(trips):
                if x is not None and x["bar"] <= i:
                    e += pnls[k]
                elif o["bar"] <= i:
                    d = _dir(o["side"])
                    carry = sum(o["size"] * closes[j - 1] * per_bar for j in range(o["bar"] + 1, i + 1))
                    e += (closes[i] - o["price"]) * o["size"] * d - matched_entry_fee[k] - carry
            if not feq(e, eq[i]):
                v.append(f"I7: 足 {i} の資産 {eq[i]} が 元本 + 実現損益 + 含み損益 = {e} と違う")
                break
    return v


def _skipped_exits(case, k, o, x, d):
    """I10: an exit that happened on bar j (a level reached with a margin, a wick exit due, a taker closing signal
    pending) leaves the position open no later than bar j."""
    c, bars = case["config"], case["bars"]
    n = len(bars)
    sig = {s["bar"]: s["signal"] for s in case["signals"]}
    end = x["bar"] if x is not None else n
    E = o["price"]
    lv = {}
    if c["stop_loss_pct"]:
        lv["stop"] = E * (1 - d * c["stop_loss_pct"] / 100)
    if c["take_profit_pct"]:
        lv["tp"] = E * (1 + d * c["take_profit_pct"] / 100)
    if c["exit_execution"] == "maker_tp" and c["maker_tp_pct"]:
        lv["mtp"] = E * (1 + d * c["maker_tp_pct"] / 100)
    wick = None
    if c["stop_mode"] == "wick_invalidation":
        win = bars[max(0, o["bar"] - c["stop_window_bars"]):o["bar"]]
        if win:
            wick = min(b["low"] for b in win) if d > 0 else max(b["high"] for b in win)
    for j in range(o["bar"] + 1, end):
        b = bars[j]
        why = None
        if "stop" in lv and ((b["low"] < lv["stop"] * (1 - _EPS)) if d > 0 else (b["high"] > lv["stop"] * (1 + _EPS))):
            why = "逆指値の水準に届いた"
        for key, name in (("tp", "利確"), ("mtp", "maker の利確")):
            if key in lv and ((b["high"] > lv[key] * (1 + _EPS)) if d > 0 else (b["low"] < lv[key] * (1 - _EPS))):
                why = f"{name}の水準を通過した"
        if wick is not None:
            cl = bars[j - 1]["close"]
            if (cl < wick * (1 - _EPS)) if d > 0 else (cl > wick * (1 + _EPS)):
                why = "構造的な逆指値の出口の足"
        if c["execution"] == "taker" and sig.get(j - 1) in ("SELL" if d > 0 else "BUY", "CLOSE"):
            why = "taker の決済の合図が始値に待っていた"
        if why:
            return [f"I10: 往復 {k}: 足 {j} で{why}のに、建玉が足 {end if x is not None else '終わり'} まで残った"]
    return []


def _allowed(c, d, q):
    if d < 0 and (not c["allow_short"] or c["entry_sides"] == "long"):
        return False
    if d > 0 and c["entry_sides"] == "short":
        return False
    return c["entry_mask"] is None or bool(c["entry_mask"][q])


def _skipped_entries(case, trips):
    """I11 (taker): flat at bar j's open with an allowed entry signal at bar j - 1 -> an entry at bar j.
    I12 (maker): flat at bar p's close with an allowed entry signal at p -> if a bar j (p < j <= p + timeout, before
    the next signal) trades strictly through bar p's close, an entry of that direction at some bar in (p, j]."""
    c, bars = case["config"], case["bars"]
    if c["execution"] != "taker":
        n = len(bars)
        sig = {s["bar"]: s["signal"] for s in case["signals"]}
        sbars = sorted(sig)
        for idx, p in enumerate(sbars):
            s = sig[p]
            if s not in ("BUY", "SELL"):
                continue
            d = 1 if s == "BUY" else -1
            if any(o["bar"] <= p < (x["bar"] if x is not None else n) for o, x in trips) or not _allowed(c, d, p):
                continue
            nxt = sbars[idx + 1] if idx + 1 < len(sbars) else n
            lim = bars[p]["close"]
            for j in range(p + 1, min(p + c["maker_timeout_bars"], nxt, n - 1) + 1):
                if any(x is not None and x["bar"] == j for _, x in trips):
                    break  # a close on bar j (of an earlier position) is outside this rule
                b = bars[j]
                if (b["low"] < lim * (1 - _EPS)) if d > 0 else (b["high"] > lim * (1 + _EPS)):
                    if not any(p < o["bar"] <= j and _dir(o["side"]) == d for o, _ in trips):
                        return [f"I12: 足 {p} の {s} の指値 {lim} を足 {j} が厳密に通過したのに、足 {j} までに建っていない"]
                    break
        return []
    n = len(bars)
    sig = {s["bar"]: s["signal"] for s in case["signals"]}
    opens = {o["bar"]: _dir(o["side"]) for o, _ in trips}
    for j in range(1, n):
        s = sig.get(j - 1)
        if s not in ("BUY", "SELL"):
            continue
        d = 1 if s == "BUY" else -1
        held = any(o["bar"] < j <= (x["bar"] if x is not None else n) for o, x in trips)
        if held:
            continue
        if d < 0 and (not c["allow_short"] or c["entry_sides"] == "long"):
            continue
        if d > 0 and c["entry_sides"] == "short":
            continue
        if c["entry_mask"] is not None and not c["entry_mask"][j - 1]:
            continue
        if opens.get(j) != d:
            return [f"I11: 足 {j} の始値で建玉が無く、足 {j - 1} の {s} が許されているのに、足 {j} で建っていない"]
    return []


def prefix_diff(full: dict, pre: dict, upto: int):
    """The prefix rule: the run on the first `upto` bars gives the same fills, PnLs and equity before bar `upto` as
    the run on all the bars (nothing before bar `upto` may depend on a later bar = no look-ahead)."""
    ff = [f for f in (full.get("fills") or []) if f.get("bar", upto) < upto]
    pf = pre.get("fills") or []
    if len(ff) != len(pf) or any(a.get("bar") != b.get("bar") or a.get("side") != b.get("side")
                                 or not feq(a.get("price"), b.get("price")) or not feq(a.get("size"), b.get("size"))
                                 for a, b in zip(ff, pf)):
        return f"先頭 {upto} 本の約定 {[(f.get('bar'), f.get('side'), f.get('price')) for f in pf]} が元の実行の足 {upto} より前の約定 " \
               f"{[(f.get('bar'), f.get('side'), f.get('price')) for f in ff]} と違う(先読み)"
    ncl = sum(1 for f in ff if str(f.get("side", "")).startswith("CLOSE"))
    fp, pp = (full.get("pnls") or [])[:ncl], pre.get("pnls") or []
    if len(fp) != len(pp) or any(not feq(a, b) for a, b in zip(fp, pp)):
        return f"先頭 {upto} 本の損益 {pp} が元の実行の {fp} と違う(先読み)"
    fe, pe = (full.get("equity") or [])[:upto], pre.get("equity") or []
    if len(fe) != len(pe) or any(not feq(a, b) for a, b in zip(fe, pe)):
        return f"先頭 {upto} 本の資産の推移が元の実行と違う(先読み)"
    return None


def views(calls):
    """C-1 is about what the strategy is handed, not how often it is called: calls that see nothing yet are dropped
    and a call that sees the same bars as the call before (a timer / calendar call with no new bar) is one view."""
    out = []
    for g in calls:
        if not isinstance(g, dict) or g.get("seen") in (0, None):
            continue
        if out and out[-1] == g:
            continue
        out.append(g)
    return out


def _calls(exp, got):
    if not isinstance(got, list):
        return f"calls: 観測が列でない({type(got).__name__})"
    got = views(got)
    if len(exp) != len(got):
        return f"calls: 呼び出し {len(got)} 回(正解 {len(exp)} 回): 観測 {got[:6]}"
    for k, (e, g) in enumerate(zip(exp, got)):
        if not isinstance(g, dict) or g.get("seen") != e["seen"] or g.get("last_t_ns") != e["last_t_ns"] \
                or not feq(e["last_close"], g.get("last_close")):
            return f"calls[{k}] = {g!r}(正解 {e!r})"
    return None


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
        elif key == "calls":
            d = _calls(e, g)
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
    """(class, detail) of one observation against the scene's expected answer.  A grid scene's observation is the
    list of the cases' observations; a case's expected entry may be an answer, {"invariants_only": True} or
    {"prefix_of": k, "upto": n}."""
    if "cases" in scene:
        for k, (e, o, c) in enumerate(zip(exp, obs, scene["cases"])):
            if "prefix_of" in e:
                d = prefix_diff(obs[e["prefix_of"]], o, e["upto"]) if isinstance(o, dict) else "観測が dict でない"
                if not d:
                    d = judge_obs(e, o, {"invariants": True}, scene, c)
            elif e.get("invariants_only"):
                d = judge_obs(e, o, {"invariants": True}, scene, c)
            else:
                d = judge_obs(e, o, scene["judge"], scene, c)
            if d:
                return "不一致", f"場合 {k}: {d}"
        return "正解と一致", f"{len(exp)} の場合すべて"
    d = judge_obs(exp, obs, scene["judge"], scene)
    return ("不一致", d) if d else ("正解と一致", "")

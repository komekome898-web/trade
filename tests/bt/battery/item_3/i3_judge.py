"""Item 3 battery: compare an observation with a scene's expected answer.

compare(expect, obs, scene) -> (class, detail); class is 「正解と一致」 or 「不一致」
(「対応なし」/「結果なし」 are decided by the runner from how the request ended;
a key the observation lacks is 「結果なし」 = no result for that answer).
variant_outcome(variant_expect, kind, val) -> (class, detail) for the variant request.
digest(x) -> the reproducibility digest; stable_view() first removes what legitimately
changes between two passes (the repository's HEAD and working-tree diff, raw run ids,
per-run scratch paths), replacing each by a placeholder so equality patterns survive.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
JP = re.compile(r"[぀-ヿ㐀-鿿]")


class Missing(Exception):
    pass


def _get(obs, key):
    if not isinstance(obs, dict) or key not in obs:
        raise Missing(key)
    return obs[key]


def _close(a, b, abs_tol, rel_tol, path="") -> str | None:
    """None if equal within tolerance, else a short description."""
    if isinstance(b, dict):
        if not isinstance(a, dict):
            return f"{path}: 辞書でない({type(a).__name__})"
        if set(map(str, a)) != set(map(str, b)):
            return f"{path}: 鍵が違う {sorted(map(str, a))} と {sorted(map(str, b))}"
        a2 = {str(k): v for k, v in a.items()}
        for k, v in b.items():
            d = _close(a2[str(k)], v, abs_tol, rel_tol, f"{path}.{k}")
            if d:
                return d
        return None
    if isinstance(b, list):
        if not isinstance(a, (list, tuple)) or len(a) != len(b):
            return f"{path}: 長さが違う({len(a) if isinstance(a, (list, tuple)) else type(a).__name__} と {len(b)})"
        for i, (x, y) in enumerate(zip(a, b)):
            d = _close(x, y, abs_tol, rel_tol, f"{path}[{i}]")
            if d:
                return d
        return None
    if isinstance(b, bool) or b is None or isinstance(b, str):
        return None if a == b and type(a) is type(b) else f"{path}: {a!r} と {b!r}"
    if isinstance(b, (int, float)):
        if isinstance(a, bool) or not isinstance(a, (int, float)) or (isinstance(a, float) and math.isnan(a)):
            return f"{path}: 数でない {a!r}"
        tol = max(abs_tol, rel_tol * abs(b))
        return None if abs(a - b) <= tol else f"{path}: {a!r} と {b!r}(許容 {tol:g})"
    return None if a == b else f"{path}: {a!r} と {b!r}"


def _rows_of(part, rows):
    if isinstance(part, dict) and "bounds" in part:
        lo, hi = part["bounds"]
        return [t for t in rows if lo <= t < hi]
    return list(part)


def _idx(obs, rows):
    if "train_idx" in obs:
        return sorted(int(i) for i in obs["train_idx"])
    pos = {t: i for i, t in enumerate(rows)}
    tr = _get(obs, "train")
    bad = [t for t in tr if t not in pos]
    if bad:
        return ["場面に無い時刻: " + str(bad[:3])]
    return sorted(pos[t] for t in tr)


def _present_first(obs, want: dict, abs_tol, rel_tol):
    """Compare the keys the observation has first: a wrong value among them is 「不一致」
    (a silently wrong value is worse than an absent one); only when every present key is
    right and some are absent is it 「結果なし」."""
    if not isinstance(obs, dict):
        raise Missing(next(iter(want)))
    present = {k: obs[k] for k in want if k in obs}
    missing = [k for k in want if k not in obs]
    d = _close(present, {k: want[k] for k in present}, abs_tol, rel_tol) if present else None
    if d:
        return "不一致", d + (f"(観測に無い欄: {missing})" if missing else "")
    if missing:
        return "結果なし", f"観測に欄 {missing} が無い" + ("(ある欄は正解と一致)" if present else "")
    return "正解と一致", ""


def git_head() -> str:
    return subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def _label(s: str) -> str:
    return re.sub(r"[(（].*?[)）]\s*$", "", str(s)).strip()


def compare(exp: dict, obs: dict, scene: dict) -> tuple[str, str]:
    try:
        return _compare(exp, obs, scene)
    except Missing as m:
        return "結果なし", f"観測に欄 {m} が無い"


def _compare(exp: dict, obs: dict, scene: dict) -> tuple[str, str]:
    inp = scene["input"]
    c = exp["check"]
    ok = ("正解と一致", "")
    if c == "parts":
        parts = _get(obs, "parts")
        for k, want in exp["parts"].items():
            got = _rows_of(_get(parts, k), inp["rows"])
            if got != want:
                return "不一致", f"{k}: {len(got)} 行(最初 {got[:1]}、最後 {got[-1:]})、正解 {len(want)} 行"
        return ok
    if c == "folds":
        folds = _get(obs, "folds")
        if len(folds) != len(exp["folds"]):
            return "不一致", f"窓の数 {len(folds)}、正解 {len(exp['folds'])}"
        for i, (g, w) in enumerate(zip(folds, exp["folds"])):
            for k in ("train", "test"):
                got = _rows_of(_get(g, k), inp["rows"])
                if got != w[k]:
                    return "不一致", f"窓 {i} の {k}: {len(got)} 行(最初 {got[:1]})、正解 {len(w[k])} 行(最初 {w[k][:1]})"
        return ok
    if c == "fold_evals":
        d = _close(_get(obs, "folds"), exp["folds"], 1e-9, 0.0, "folds")
        return ("不一致", d) if d else ok
    if c == "index_set":
        got = _idx(obs, inp["rows"])
        return ok if got == exp["train"] else ("不一致", f"学習の行 {got}、正解 {exp['train']}")
    if c == "cpcv_split":
        missing, bad = [], []
        for k in ("n_splits", "n_paths"):
            if not isinstance(obs, dict) or k not in obs:
                missing.append(k)
            elif obs[k] != exp[k]:
                bad.append(f"{k} = {obs[k]}、正解 {exp[k]}")
        if "train" in obs or "train_idx" in obs:
            got = _idx(obs, inp["rows"])
            if got != exp["train"]:
                bad.append(f"評価の群 {inp['want_train_for']} の学習の行 {got}、正解 {exp['train']}")
        else:
            missing.append("train")
        if bad:
            return "不一致", "; ".join(bad) + (f"(観測に無い欄: {missing})" if missing else "")
        return ("結果なし", f"観測に欄 {missing} が無い(ある欄は正解と一致)") if missing else ok
    if c == "cpcv_paths":
        paths = _get(obs, "paths")
        G, K = exp["n_groups"], exp["n_test_groups"]
        if len(paths) != exp["n_paths"]:
            return "不一致", f"経路の数 {len(paths)}、正解 {exp['n_paths']}"
        seen = []
        for p, path in enumerate(paths):
            groups = sorted(int(e["group"]) for e in path)
            if groups != list(range(G)):
                return "不一致", f"経路 {p} の群 {groups} が 0..{G - 1} をちょうど 1 回ずつ覆わない"
            for e in path:
                sp = tuple(sorted(int(x) for x in e["split"]))
                if len(sp) != K or int(e["group"]) not in sp:
                    return "不一致", f"経路 {p} の {e} は、その群を評価に含む {K} 群の分割でない"
                seen.append((sp, int(e["group"])))
        allpairs = sorted((sp, g) for sp in __import__("itertools").combinations(range(G), K) for g in sp)
        return ok if sorted(seen) == allpairs else ("不一致", f"(分割, 群) の組が全部ちょうど 1 回ずつでない({len(seen)} 組)")
    if c == "ci_band":
        lo, hi = _get(obs, "ci")
        mid, se_hat = (lo + hi) / 2, (hi - lo) / (2 * 1.959963984540054)
        if abs(mid - exp["mean"]) > exp["center_tol_se"] * exp["se"]:
            return "不一致", f"中点 {mid:.6f}、標本平均 {exp['mean']:.6f} から {abs(mid - exp['mean']) / exp['se']:.2f} 標準誤差"
        r = se_hat / exp["se"]
        a, b = exp["width_band"]
        return ok if a <= r <= b else ("不一致", f"幅から逆算した標準誤差 {se_hat:.6f} = 正解の {r:.3f} 倍(許容 {a}〜{b})")
    if c in ("close", "equal"):
        return _present_first(obs, exp["values"], exp.get("abs", 0.0) if c == "close" else 0.0,
                              exp.get("rel", 0.0) if c == "close" else 0.0)
    if c == "record":
        rec = _get(obs, "record")
        got = _get(rec, exp["field"])
        want = exp["value"]
        if isinstance(want, dict) and want.get("oracle") == "git_head":
            want = git_head()
        d = _close(got, want, 0.0, 0.0, exp["field"])
        return ("不一致", d) if d else ok
    if c == "record_stable_hex":
        recs = _get(obs, "records")
        vals = [_get(r, exp["field"]) for r in recs]
        if len(vals) < 2:
            return "不一致", f"記録が {len(vals)} つしか無い"
        if not all(isinstance(v, str) and re.fullmatch(r"[0-9a-f]{%d,}" % exp["min_len"], v) for v in vals):
            return "不一致", f"{exp['field']} が {exp['min_len']} 桁以上の 16 進でない: {[str(v)[:20] for v in vals]}"
        return ok if len(set(vals)) == 1 else ("不一致", "同じ作業木の 2 回で値が違う")
    if c == "record_nonempty":
        v = _get(_get(obs, "record"), exp["field"])
        return ok if isinstance(v, str) and v.strip() else ("不一致", f"{exp['field']} = {v!r}")
    if c == "id_relations":
        ids = _get(obs, "ids")
        part = []
        for i, x in enumerate(ids):
            for grp in part:
                if ids[grp[0]] == x:
                    grp.append(i)
                    break
            else:
                part.append([i])
        return ok if part == exp["groups"] else ("不一致", f"等しい組 {part}、正解 {exp['groups']}")
    if c == "exports_purpose":
        ex = _get(obs, "exports")
        if not ex:
            return "不一致", "書き出しのファイルが 1 つも無い"
        bad = {k: v for k, v in ex.items() if v != exp["value"]}
        return ok if not bad else ("不一致", f"目的が {exp['value']} でない書き出し: {dict(list(bad.items())[:3])}")
    if c.startswith("dash_"):
        ids = _get(obs, "run_ids")
        a, b = _get(ids, "A"), _get(ids, "B")
        if c == "dash_run_tabs":
            tabs = _get(obs, "run_tabs")
            for key, rid in (("A", a), ("B", b)):
                got = [_label(x) for x in _get(tabs, rid)]
                if got != exp["tabs"]:
                    return "不一致", f"{key} のタブ {got}"
            return ok
        if c == "dash_list":
            top, lst, tabs = _get(obs, "top_tabs"), _get(obs, "run_list"), _get(obs, "run_tabs")
            if "バックテスト" not in [_label(x) for x in top]:
                return "不一致", f"最上段のタブ {top} に「バックテスト」が無い"
            miss = [k for k, rid in (("A", a), ("B", b)) if rid not in lst or not tabs.get(rid)]
            return ok if not miss else ("不一致", f"一覧から辿れない実行: {miss}")
        if c == "dash_japanese":
            labels = [x for x in _get(obs, "top_tabs") if _label(x) == "バックテスト"] + list(_get(_get(obs, "run_tabs"), a))
            text = _get(_get(obs, "tab_text"), a)
            bad = [x for x in labels if not JP.search(str(x))]
            if not labels or bad:
                return "不一致", f"仮名も漢字も含まない名: {bad}" if bad else "名が無い"
            return ok if any("動作確認" in str(t) for t in text.values()) else ("不一致", "A の警告の文が見つからない")
        if c == "dash_values":
            v = _get(_get(obs, "values"), a)
            got = {k: _get(v, k) for k in exp["values"]}
            d = _close(got, exp["values"], exp["abs"], 0.0, "A")
            return ("不一致", d) if d else ok
        if c == "dash_warning":
            tt = _get(obs, "tab_text")
            for key, rid, want in (("A", a, True), ("B", b, False)):
                texts = {_label(k): v for k, v in _get(tt, rid).items()}
                for tab in exp["tabs"]:
                    has = exp["warning"] in str(_get(texts, tab))
                    if has != want:
                        return "不一致", f"{key} の「{tab}」: 警告 {'あり' if has else 'なし'}(正解 {'あり' if want else 'なし'})"
            return ok
    raise ValueError(f"unknown check {c}")


def variant_outcome(vexp: dict, kind: str, val) -> tuple[str, str]:
    """kind is the runner's 'ok' | 'refused' | 'none' for the variant request."""
    if kind == "none":
        return "結果なし", "変形: " + str(val)[:400]
    if "refuse" in vexp:
        return ("正解と一致", "変形を拒んだ: " + str(val)[:300]) if kind == "refused" else ("不一致", "変形を拒まずに通した")
    if "refuse_or_equal" in vexp:
        if kind == "refused":
            return "正解と一致", "変形を拒んだ: " + str(val)[:300]
        try:
            vals = {k: _get(val, k) for k in vexp["refuse_or_equal"]}
        except Missing as m:
            return "結果なし", f"変形の観測に欄 {m} が無い"
        d = _close(vals, vexp["refuse_or_equal"], 1e-12, 0.0, "変形")
        return ("不一致", d) if d else ("正解と一致", "変形は正解の値を返した")
    if "equal" in vexp:
        if kind == "refused":
            return "対応なし", "変形を拒んだ: " + str(val)[:300]
        try:
            vals = {k: _get(val, k) for k in vexp["equal"]}
        except Missing as m:
            return "結果なし", f"変形の観測に欄 {m} が無い"
        d = _close(vals, vexp["equal"], 0.0, 0.0, "変形")
        return ("不一致", d) if d else ("正解と一致", "")
    raise ValueError(vexp)


_VOLATILE = ("git_sha", "diff_hash")


def stable_view(obs):
    """Replace what may legitimately change between the two passes by placeholders."""
    if obs is None:
        return None
    s = json.dumps(obs, ensure_ascii=False, sort_keys=True, default=str)
    vals = []

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in _VOLATILE and isinstance(v, str):
                    vals.append((k, v))
                elif k in ("run_id",) and isinstance(v, str):
                    vals.append(("run_id", v))
                elif k == "run_ids" and isinstance(v, dict):
                    vals.extend(("run_id", str(i)) for i in v.values())
                elif k == "ids" and isinstance(v, list):
                    vals.extend(("run_id", str(i)) for i in v)
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(obs)
    seen = {}
    for kind, v in vals:
        if v and v not in seen:
            seen[v] = f"<{kind}{len([1 for x in seen.values() if x.startswith('<' + kind)])}>"
    for v in sorted(seen, key=len, reverse=True):
        s = s.replace(v, seen[v])
    return json.loads(s)


def digest(x) -> str:
    return hashlib.sha256(json.dumps(stable_view(x), ensure_ascii=False, sort_keys=True, default=str)
                          .encode("utf-8")).hexdigest()[:16]

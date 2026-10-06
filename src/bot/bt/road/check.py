"""検査のツールの本体(L-754・L-755)。CLI は `scripts/road/check_outputs.py`。

オーナーの逐語:
- L-754「**私がしてほしいの決まりを足すんじゃなくて、この計算が確実にできるツールを作ることと、そのツールが必ず使われる仕組みです。**」
- L-755「**1.yes 2.消す**」(検査を押し出しの関門と分析のフックにつなぐ。つなぐのは次の段で、この段では作らない)

検査が見るのは「道の外で作った数か」と「約定が足の上にあるか」だけ。帳簿のツールそのものの正しさは
`tests/road/` の場面の試験で確かめる。

(a) まとめの計算し直し: 置き場の約定の列(`road_fills.json`)から帳簿のツール(`ledger.book`)でまとめを計算し直し、
    置き場に書かれたまとめ(`road_summary.json`)と鍵・値が 1 つでも違えば失敗。値は == で比べる(同じツールで
    同じ順に足すので、JSON に書いた浮動小数はそのまま戻る)。
(b) 足の検査: 約定ごとに、
    - 約定の時刻 t を含む 1 分足(始まり s ≤ t < s + 60 秒)があるか(無ければ失敗)
    - 当たる足が 2 本以上なら失敗(足が重なっている)
    - 当たる足の始まりが分の区切り(60 秒の倍数の ns)にそろうか(そろわなければ失敗)
    - 約定の値段がその足の安値以上・高値以下か(外なら失敗)
    足は引数で受ける: 1 本 = {"t_ns": 足の始まり(ns), "high": 数, "low": 数}(ほかの鍵は見ない)。

置き場の形(この段で決めたもの。道につなぐ段で変えるときは `write_store` / `read_store` の 2 つだけを直す):
- `road_fills.json`: {"fills": [約定の行 ...], "fx": [{"t_ns", "pair", "rate"} ...]}  約定の行は `ledger` の入力の形
- `road_summary.json`: {"closed_trades": 整数, "pnl_jpy": 数, "open_trades": 整数}
"""
from __future__ import annotations

import bisect
import json
import math
import os
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from .ledger import SUMMARY_KEYS, book

FILLS_FILE = "road_fills.json"
SUMMARY_FILE = "road_summary.json"
MINUTE_NS = 60_000_000_000


@dataclass
class CheckResult:
    failures: list = field(default_factory=list)  # 失敗した行: {"check": "a"|"b", "row": ..., "reason": 日本語}

    @property
    def ok(self) -> bool:
        return not self.failures


def _dump(path: str, obj: object) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1, allow_nan=False) + "\n")


def write_store(run_dir: str, fills: Sequence[Mapping], fx: Sequence[Mapping] = ()) -> dict:
    """約定の列と、帳簿のツールで計算したまとめを置き場に書く。書いたまとめを返す。"""
    fills = [dict(f) for f in fills]
    fx = [dict(p) for p in fx]
    summary = book(fills, fx or None).summary
    os.makedirs(run_dir, exist_ok=True)
    _dump(os.path.join(run_dir, FILLS_FILE), {"fills": fills, "fx": fx})
    _dump(os.path.join(run_dir, SUMMARY_FILE), summary)
    return summary


def read_store(run_dir: str) -> tuple[list, list, object]:
    """(約定の列, 為替の列, 書かれたまとめ)。ファイルが無い・読めないときは例外。"""
    with open(os.path.join(run_dir, FILLS_FILE), "r", encoding="utf-8") as fh:
        body = json.load(fh)
    with open(os.path.join(run_dir, SUMMARY_FILE), "r", encoding="utf-8") as fh:
        summary = json.load(fh)
    if not isinstance(body, dict) or not isinstance(body.get("fills"), list):
        raise ValueError(f"{FILLS_FILE} に fills の列が無い")
    fx = body.get("fx", [])
    if not isinstance(fx, list):
        raise ValueError(f"{FILLS_FILE} の fx が列でない")
    return body["fills"], fx, summary


def check_summary(fills: Sequence[Mapping], fx: Sequence[Mapping], written: object) -> list:
    """(a) まとめを計算し直して書かれたまとめと突き合わせる。"""
    out = []
    try:
        again = book(fills, list(fx) or None).summary
    except Exception as exc:  # 帳簿のツールが止まった約定の列は、それ自体が失敗
        return [{"check": "a", "row": "fills", "reason": f"帳簿のツールで計算し直せない: {type(exc).__name__}: {exc}"}]
    if not isinstance(written, dict):
        return [{"check": "a", "row": "summary", "reason": f"書かれたまとめが辞書でない: {type(written).__name__}"}]
    for k in sorted(set(again) | set(written)):
        if k not in written:
            out.append({"check": "a", "row": k, "reason": f"書かれたまとめに {k} が無い(計算し直すと {again[k]!r})"})
        elif k not in again:
            out.append({"check": "a", "row": k, "reason": f"書かれたまとめに帳簿のツールが出さない鍵 {k} がある"})
        elif type(written[k]) is bool or written[k] != again[k]:
            out.append({"check": "a", "row": k,
                        "reason": f"書かれた値 {written[k]!r} と計算し直した値 {again[k]!r} が違う"})
    assert set(again) == set(SUMMARY_KEYS)
    return out


def check_bars(fills: Sequence[Mapping], bars: Sequence[Mapping]) -> list:
    """(b) 約定ごとに、その分の 1 分足・足の始まりの分の区切り・値段が安値以上高値以下かを見る。"""
    out = []
    rows = []
    for j, b in enumerate(bars):
        try:
            s, hi, lo = b["t_ns"], b["high"], b["low"]
        except (KeyError, TypeError):
            out.append({"check": "b", "row": f"bar {j}", "reason": "足に t_ns / high / low が無い"})
            continue
        if type(s) is not int:
            out.append({"check": "b", "row": f"bar {j}", "reason": f"足の t_ns が ns の整数でない: {s!r}"})
            continue
        bad = [n for n, v in (("high", hi), ("low", lo))
               if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v))]
        if bad:
            out.append({"check": "b", "row": f"bar {j}", "reason": f"足の {'・'.join(bad)} が有限の数でない"})
            continue
        rows.append((s, j, float(hi), float(lo)))
    rows.sort()
    starts = [r[0] for r in rows]
    for i, f in enumerate(fills):
        t, px = f.get("t_ns"), f.get("px")
        if type(t) is not int or isinstance(px, bool) or not isinstance(px, (int, float)):
            out.append({"check": "b", "row": i, "reason": f"約定の t_ns / px が読めない: {t!r} / {px!r}"})
            continue
        # 始まり s が t - 60 秒 < s <= t の足が、t を含む足
        lo_i = bisect.bisect_right(starts, t - MINUTE_NS)
        hi_i = bisect.bisect_right(starts, t)
        hits = rows[lo_i:hi_i]
        if not hits:
            out.append({"check": "b", "row": i, "reason": f"約定の時刻 {t} を含む 1 分足が無い"})
            continue
        if len(hits) > 1:
            out.append({"check": "b", "row": i,
                        "reason": f"約定の時刻 {t} を含む足が {len(hits)} 本ある(始まり {[h[0] for h in hits]})"})
            continue
        s, j, hi, lo = hits[0]
        if s % MINUTE_NS != 0:
            out.append({"check": "b", "row": i,
                        "reason": f"約定の時刻 {t} が属する足(bar {j})の始まり {s} が分の区切りから "
                                  f"{s % MINUTE_NS} ns ずれている"})
            continue
        if not (lo <= float(px) <= hi):
            out.append({"check": "b", "row": i,
                        "reason": f"約定の値段 {px} がその分の足(bar {j})の安値 {lo}〜高値 {hi} の外"})
    return out


def check_outputs(run_dir: str, bars: Sequence[Mapping]) -> CheckResult:
    """置き場 1 つに (a) と (b) を当てる。置き場が読めなければ失敗。"""
    try:
        fills, fx, written = read_store(run_dir)
    except Exception as exc:
        return CheckResult([{"check": "a", "row": run_dir, "reason": f"置き場が読めない: {type(exc).__name__}: {exc}"}])
    return CheckResult(check_summary(fills, fx, written) + check_bars(fills, bars))

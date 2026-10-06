"""検査のツールの本体(L-754・L-755)。CLI は `scripts/road/check_outputs.py`。

オーナーの逐語:
- L-754「**私がしてほしいの決まりを足すんじゃなくて、この計算が確実にできるツールを作ることと、そのツールが必ず使われる仕組みです。**」
- L-755「**1.yes 2.消す**」(検査を押し出しの関門と分析のフックにつなぐ。つなぐのは次の段で、この段では作らない)

検査が見るのは「道の外で作った数か」と「約定が足の上にあるか」だけ。帳簿のツールそのものの正しさは
`tests/road/` の場面の試験で確かめる。

(a) まとめの計算し直し: 置き場の約定の列(`road_fills.json`)から帳簿のツール(`ledger.book`)でまとめを計算し直し、
    置き場に書かれたまとめ(`road_summary.json`)と鍵・値が 1 つでも違えば失敗。まとめには約定の数と取引ごとの表
    (最初の約定の時刻・最後の約定の時刻・段の数・最大の建玉・保有時間・損益・状態)も入っているので、取引の行ごと・
    欄ごとに突き合わせる(約定を 1 つ消すと、約定の数と、その約定が属する取引の行が変わる)。
    値は型も含めて == で比べる(損益・建玉は帳簿のツールが出す 10 進の文字列。数で書かれていたら違うとみなす)。
(b) 足の検査: 約定ごとに、
    - 約定の時刻 t を含む 1 分足(始まり s ≤ t < s + 60 秒)があるか(無ければ失敗)
    - 当たる足が 2 本以上なら失敗(足が重なっている)
    - 当たる足の始まりが分の区切り(60 秒の倍数の ns)にそろうか(そろわなければ失敗)
    - 約定の値段がその足の安値以上・高値以下か(外なら失敗)
    足は引数で受ける: 1 本 = {"t_ns": 足の始まり(ns), "high": 数, "low": 数}(ほかの鍵は見ない)。

置き場の形(この段で決めたもの。道につなぐ段で変えるときは `write_store` / `read_store` の 2 つだけを直す):
- `road_fills.json`: {"fills": [約定の行 ...], "fx": [{"t_ns", "pair", "rate"} ...]}  約定の行は `ledger` の入力の形
- `road_summary.json`: 帳簿のツールのまとめ(`ledger.SUMMARY_KEYS`: fill_count・closed_trades・pnl_jpy・open_trades・
  trades。trades の行は `ledger.TRADE_KEYS`)

ここで出す文は全部日本語(O-1)。下の層の例外の英語の文は出さない。
"""
from __future__ import annotations

import bisect
import json
import math
import os
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from .ledger import SUMMARY_KEYS, TRADE_KEYS, LedgerError, book

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


class StoreError(ValueError):
    """置き場が読めない(文は日本語)。"""


def load_json(path: str, what: str) -> object:
    """JSON のファイルを読む。読めなければ日本語の文の `StoreError`。"""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise StoreError(f"{what}のファイルが無い: {path}") from None
    except json.JSONDecodeError as exc:
        raise StoreError(f"{what}のファイルが JSON として読めない: {path}(行 {exc.lineno} 列 {exc.colno})") from None
    except UnicodeDecodeError:
        raise StoreError(f"{what}のファイルが UTF-8 の文字として読めない: {path}") from None
    except OSError as exc:
        raise StoreError(f"{what}のファイルを開けない: {path}(OS の誤りの番号 {exc.errno})") from None


def read_store(run_dir: str) -> tuple[list, list, object]:
    """(約定の列, 為替の列, 書かれたまとめ)。ファイルが無い・読めないときは `StoreError`。"""
    body = load_json(os.path.join(run_dir, FILLS_FILE), "約定の列")
    summary = load_json(os.path.join(run_dir, SUMMARY_FILE), "まとめ")
    if not isinstance(body, dict) or not isinstance(body.get("fills"), list):
        raise StoreError(f"{FILLS_FILE} に fills の列が無い")
    fx = body.get("fx", [])
    if not isinstance(fx, list):
        raise StoreError(f"{FILLS_FILE} の fx が列でない")
    return body["fills"], fx, summary


def _same(a: object, b: object) -> bool:
    return type(a) is type(b) and a == b


def check_summary(fills: Sequence[Mapping], fx: Sequence[Mapping], written: object) -> list:
    """(a) まとめ(約定の数・取引ごとの表を含む)を計算し直して書かれたまとめと突き合わせる。"""
    try:
        again = book(fills, list(fx) or None).summary
    except LedgerError as exc:  # 帳簿のツールが止まった約定の列は、それ自体が失敗
        return [{"check": "a", "row": "約定の列", "reason": f"帳簿のツールで計算し直せない: {exc}"}]
    except Exception as exc:  # 想定外(作りの誤り)。下の層の英語の文は出さない
        return [{"check": "a", "row": "約定の列",
                 "reason": f"帳簿のツールが想定外の形で止まった(例外の種類 {type(exc).__name__})"}]
    if not isinstance(written, dict):
        return [{"check": "a", "row": "まとめ", "reason": f"書かれたまとめが辞書でない({type(written).__name__})"}]
    if set(again) != set(SUMMARY_KEYS):
        return [{"check": "a", "row": "まとめ", "reason": "帳簿のツールのまとめの鍵が SUMMARY_KEYS と違う(作りの誤り)"}]
    out = []
    for k in sorted(set(again) | set(written)):
        if k not in written:
            out.append({"check": "a", "row": k, "reason": f"書かれたまとめに {k} が無い(計算し直すと {again[k]!r})"})
        elif k not in again:
            out.append({"check": "a", "row": k, "reason": f"書かれたまとめに帳簿のツールが出さない鍵 {k} がある"})
        elif k == "trades":
            out.extend(_check_trades(written[k], again[k]))
        elif not _same(written[k], again[k]):
            out.append({"check": "a", "row": k,
                        "reason": f"書かれた値 {written[k]!r} と計算し直した値 {again[k]!r} が違う"})
    return out


def _check_trades(written: object, again: list) -> list:
    """まとめの取引ごとの表を、行ごと・欄ごとに突き合わせる。"""
    if not isinstance(written, list):
        return [{"check": "a", "row": "trades", "reason": f"書かれた取引ごとの表が列でない({type(written).__name__})"}]
    out = []
    if len(written) != len(again):
        out.append({"check": "a", "row": "trades",
                    "reason": f"書かれた取引の数 {len(written)} と計算し直した取引の数 {len(again)} が違う"})
    for j in range(max(len(written), len(again))):
        if j >= len(written):
            out.append({"check": "a", "row": f"trades[{j}]", "reason": f"書かれた表にこの取引が無い(計算し直すと {again[j]!r})"})
            continue
        if j >= len(again):
            out.append({"check": "a", "row": f"trades[{j}]", "reason": f"計算し直すと無い取引が書かれている: {written[j]!r}"})
            continue
        w, a = written[j], again[j]
        if not isinstance(w, dict):
            out.append({"check": "a", "row": f"trades[{j}]", "reason": f"書かれた取引の行が辞書でない({type(w).__name__})"})
            continue
        for k in TRADE_KEYS:
            if k not in w:
                out.append({"check": "a", "row": f"trades[{j}].{k}",
                            "reason": f"書かれた取引の行に {k} が無い(計算し直すと {a[k]!r})"})
            elif not _same(w[k], a[k]):
                out.append({"check": "a", "row": f"trades[{j}].{k}",
                            "reason": f"書かれた値 {w[k]!r} と計算し直した値 {a[k]!r} が違う"})
        for k in sorted(set(w) - set(TRADE_KEYS)):
            out.append({"check": "a", "row": f"trades[{j}].{k}",
                        "reason": f"書かれた取引の行に帳簿のツールが出さない鍵 {k} がある"})
    return out


def check_bars(fills: Sequence[Mapping], bars: Sequence[Mapping]) -> list:
    """(b) 約定ごとに、その分の 1 分足・足の始まりの分の区切り・値段が安値以上高値以下かを見る。"""
    out = []
    rows = []
    for j, b in enumerate(bars):
        try:
            s, hi, lo = b["t_ns"], b["high"], b["low"]
        except (KeyError, TypeError):
            out.append({"check": "b", "row": f"足 {j}", "reason": "足に t_ns / high / low が無い"})
            continue
        if type(s) is not int:
            out.append({"check": "b", "row": f"足 {j}", "reason": f"足の t_ns が ns の整数でない: {s!r}"})
            continue
        bad = [n for n, v in (("high", hi), ("low", lo)) if not _finite_number(v)]
        if bad:
            out.append({"check": "b", "row": f"足 {j}", "reason": f"足の {'・'.join(bad)} が有限の数でない"})
            continue
        rows.append((s, j, float(hi), float(lo)))
    rows.sort()
    starts = [r[0] for r in rows]
    for i, f in enumerate(fills):
        if not isinstance(f, Mapping):
            out.append({"check": "b", "row": i, "reason": f"約定の行が辞書の形でない: {type(f).__name__}"})
            continue
        t, px = f.get("t_ns"), f.get("px")
        if type(t) is not int or not _finite_number(px):
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
                        "reason": f"約定の時刻 {t} が属する足(足 {j})の始まり {s} が分の区切りから "
                                  f"{s % MINUTE_NS} ns ずれている"})
            continue
        if not (lo <= float(px) <= hi):
            out.append({"check": "b", "row": i,
                        "reason": f"約定の値段 {px} がその分の足(足 {j})の安値 {lo}〜高値 {hi} の外"})
    return out


def _finite_number(v) -> bool:
    """真偽値でない有限の数か(とても大きい整数で float に直せないものも有限でないとみなす)。"""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return False
    try:
        return math.isfinite(float(v))
    except OverflowError:
        return False


def check_outputs(run_dir: str, bars: Sequence[Mapping]) -> CheckResult:
    """置き場 1 つに (a) と (b) を当てる。置き場が読めなければ失敗。"""
    try:
        fills, fx, written = read_store(run_dir)
    except StoreError as exc:
        return CheckResult([{"check": "a", "row": run_dir, "reason": f"置き場が読めない: {exc}"}])
    return CheckResult(check_summary(fills, fx, written) + check_bars(fills, bars))

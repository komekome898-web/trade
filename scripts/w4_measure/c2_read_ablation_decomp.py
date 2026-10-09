#!/usr/bin/env python3
"""カツオの入りの分・降りの分を、取引を 1 本ずつ突き合わせて分ける(関門 ② の 1 回目の直す 1・2 を受けて足した)。

`runs/READ_ABLATION/RESULTS.md` の監査(`docs/AUDITOR/VERDICTS/2026-10-04_c2_ablation_read.md`)の後に足した。R1〜R5 は変えていない。

入りの分(入りだけ le_cx_<e>_good − 参照):
  鍵 = (合図の時刻, 向き)。入りだけの取引は trades.csv.gz の signal_t。参照の取引(trades.json.gz)には合図の時刻が無いので、
  入り方 a は 建ての時刻 − 足の長さ、b・c は 建ての時刻 を合図の時刻とする(参照の形の H3 と入り方の決まり。missed.csv.gz の
  行で、この関係が成り立つ割合を「鍵の確かめ」として出す)。
  恒等式: (入りだけの和 − 参照の和) = 指値の形にだけある取引の和 − 参照にだけある取引の和 + 共通の取引の損益の差の和。
降りの分(降りだけ ce_lx_<a|b>_<側> − 参照):
  鍵 = (建ての時刻, 向き)(どちらも入りは足の終値)。共通の取引を、降りだけの取引の undecided(決まらない足に当たった数)が
  0 か 1 以上かで分け、それぞれの損益の差の和を出す。突き合わない取引は別に出す。
すべて 1 日あたり(日数は各走らせの summary の all.days)。経費なし。

    python3 scripts/w4_measure/c2_read_ablation_decomp.py [--root <runs>]
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c2_read_ablation as ra  # noqa: E402
import c2_read_limit as rl  # noqa: E402

NS = 10**9


def iso_ns(s: str) -> int:
    return int(datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()) * NS


def ref_rows(d: str) -> list[tuple]:
    """(建ての時刻 ns, 向き, 損益 %)。L-920 より前の記録の pnl_bp(率 × 1 万)は / 100。"""
    with gzip.open(os.path.join(d, "trades.json.gz"), "rt", encoding="utf-8") as fh:
        o = json.load(fh)
    assert o["t_unit"] == "ns"
    pnl = o["pnl_pct"] if "pnl_pct" in o else [float(v) / 100 for v in o["pnl_bp"]]
    return [(int(o["entry_t_ns"][i]), int(o["side"][i]), float(pnl[i])) for i in range(len(pnl))]


def _row_pct(r: dict) -> float:
    """trades.csv.gz の行の損益(%)。L-920 より前の行の pnl_bp は / 100。"""
    return float(r["pnl_pct"]) if r.get("pnl_pct") not in (None, "") else float(r["pnl_bp"]) / 100


def csv_rows(path: str) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def ref_signal_ns(entry_ns: int, entry: str, foot: int) -> int:
    return entry_ns - foot * 60 * NS if entry == "a" else entry_ns


def pair(a: dict, b: dict) -> tuple[list, list, list]:
    """a・b = {鍵: [値, ...]}。同じ鍵が複数あれば並び順に 1 対 1。(共通の組, a にだけ, b にだけ)。"""
    common, ao, bo = [], [], []
    for k in set(a) | set(b):
        x, y = a.get(k, []), b.get(k, [])
        n = min(len(x), len(y))
        common += list(zip(x[:n], y[:n]))
        ao += x[n:]
        bo += y[n:]
    return common, ao, bo


def _group(items):
    d: dict = {}
    for k, v in items:
        d.setdefault(k, []).append(v)
    return d


def entry_decomp(limit_rows: list[dict], ref: list[tuple], entry: str, foot: int, days_l: float, days_r: float) -> dict:
    L = _group(((iso_ns(r["signal_t"]), int(r["side"])), _row_pct(r)) for r in sorted(limit_rows, key=lambda r: r["entry_t"]))
    R = _group(((ref_signal_ns(t, entry, foot), s), p) for t, s, p in sorted(ref))
    common, lo, ro = pair(L, R)
    return {
        "entry_part": math.fsum(sum(L.values(), [])) / days_l - math.fsum(sum(R.values(), [])) / days_r,
        "limit_only_n": len(lo), "limit_only_day": math.fsum(lo) / days_l,
        "ref_only_n": len(ro), "ref_only_day": -math.fsum(ro) / days_r,
        "common_n": len(common), "common_diff_day": math.fsum(x - y for x, y in common) / days_l,
    }


def key_check(missed_rows: list[dict], entry: str, foot: int) -> float:
    """missed.csv.gz の行(参照の形の取引で合図の時刻つき)で、合図の時刻 = ref_signal_ns(建ての時刻) が成り立つ割合。"""
    if not missed_rows:
        return float("nan")
    ok = sum(1 for r in missed_rows if ref_signal_ns(iso_ns(r["entry_t"]), entry, foot) == iso_ns(r["signal_t"]))
    return ok / len(missed_rows)


def exit_decomp(exit_rows: list[dict], ref: list[tuple], days_x: float, days_r: float) -> dict:
    X = _group(((iso_ns(r["entry_t"]), int(r["side"])), (_row_pct(r), int(r["undecided"])))
               for r in sorted(exit_rows, key=lambda r: r["entry_t"]))
    R = _group(((t, s), p) for t, s, p in sorted(ref))
    common, xo, ro = pair(X, R)
    und = [(x, y) for x, y in common if x[1] > 0]
    dec = [(x, y) for x, y in common if x[1] == 0]
    return {
        "exit_part": math.fsum(v[0] for v in sum(X.values(), [])) / days_x - math.fsum(sum(R.values(), [])) / days_r,
        "decided_n": len(dec), "decided_diff_day": math.fsum(x[0] - y for x, y in dec) / days_x,
        "undecided_n": len(und), "undecided_diff_day": math.fsum(x[0] - y for x, y in und) / days_x,
        "unmatched_x_n": len(xo), "unmatched_ref_n": len(ro),
        "unmatched_day": (math.fsum(v[0] for v in xo) / days_x) - (math.fsum(ro) / days_r),
    }


def _days(d: str) -> float:
    with open(os.path.join(d, "summary.json"), encoding="utf-8") as fh:
        return float(json.load(fh)["all"]["days"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=rl.DEFAULT_ROOT)
    a = ap.parse_args(argv)
    P = lambda n: os.path.join(a.root, n)  # noqa: E731
    out = {"entry": {}, "exit": {}}
    E = ["# カツオ: 入りの分・降りの分を取引 1 本ずつの突き合わせで分ける", "",
         "`scripts/w4_measure/c2_read_ablation_decomp.py` が出した(関門 ② の 1 回目の後に足した)。経費の前。1 日あたり %(損益の率。L-920 で bp は値動き率だけの名前)。", "",
         "## 表 A: 入りの分 = 指値の形にだけある取引 − 参照にだけある取引(取り逃し)+ 共通の取引の差", "",
         "| 足 | 入り方 | 入りの分 | 指値の形にだけ 本数・和 | 参照にだけ 本数・和(符号は入りの分への寄与) | 共通 本数・差の和 | 鍵の確かめ |",
         "|---|---|---|---|---|---|---|"]
    for f in ra.FEET:
        for e in ra.ENTRIES:
            nm = ra.names_for(f, e, "good")
            le, rf = P(nm["entry_only"]), P(nm["ref"])
            if not all(os.path.isfile(os.path.join(x, "summary.json")) for x in (le, rf)):
                continue
            r = entry_decomp(csv_rows(os.path.join(le, "trades.csv.gz")), ref_rows(rf), e, f, _days(le), _days(rf))
            r["key_check"] = key_check(csv_rows(os.path.join(le, "missed.csv.gz")), e, f)
            out["entry"][f"{f}|{e}"] = r
            E.append(f"| {f} 分 | {e} | {r['entry_part']:+.4f} | {r['limit_only_n']:,}・{r['limit_only_day']:+.4f} | "
                     f"{r['ref_only_n']:,}・{r['ref_only_day']:+.4f} | {r['common_n']:,}・{r['common_diff_day']:+.4f} | {r['key_check']:.3f} |")
    E += ["", "鍵の確かめ = missed.csv.gz の行で、合図の時刻が「入り方 a は建て − 足、b・c は建て」と一致した割合。", "",
          "## 表 B: 降りの分 = 共通の取引の差(決まらない足に当たらない / 当たる)+ 突き合わない取引", "",
          "| 足 | 入り方 | 側 | 降りの分 | 当たらない 本数・差の和 | 当たる 本数・差の和 | 突き合わない 降りだけ / 参照 本数・和の差 |",
          "|---|---|---|---|---|---|---|"]
    for f in ra.FEET:
        for e in ("a", "b"):
            for s in rl.SIDES:
                xo, rf = P(f"weak_f{f}_ce_lx_{e}_{s}"), P(f"weak_f{f}_{rl.REF[e]}")
                if not all(os.path.isfile(os.path.join(x, "summary.json")) for x in (xo, rf)):
                    continue
                r = exit_decomp(csv_rows(os.path.join(xo, "trades.csv.gz")), ref_rows(rf), _days(xo), _days(rf))
                out["exit"][f"{f}|{e}|{s}"] = r
                E.append(f"| {f} 分 | {e} | {'良' if s == 'good' else '悪'} | {r['exit_part']:+.4f} | {r['decided_n']:,}・{r['decided_diff_day']:+.4f} | "
                         f"{r['undecided_n']:,}・{r['undecided_diff_day']:+.4f} | {r['unmatched_x_n']:,} / {r['unmatched_ref_n']:,}・{r['unmatched_day']:+.4f} |")
    od = P("READ_ABLATION")
    with open(os.path.join(od, "DECOMP.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(E) + "\n")
    with open(os.path.join(od, "decomp.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"-> {od}/DECOMP.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())

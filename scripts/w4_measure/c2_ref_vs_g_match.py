#!/usr/bin/env python3
"""カツオの再現の参照(weak_f<足>_close_a)と段階 G の取引を、建ての時刻と向きで 1 本ずつ突き合わせる。

台帳 K-037 の次の問い・`limit_sim/runs/READ_K1YEAR/RESULTS.md` §5 の 1。読み方の決まり(突き合わせの表を見る前に、
この台本と `tests/research/test_c2_ref_vs_g_match.py` で固めた):

R1 取引の鍵 = (建ての時刻 entry_t_ns, 向き)。参照は side が +1/−1、段階 G は "buy"/"sell"。年は建ての時刻 − 足の長さ
   (建てた足の始まり)の UTC の年で、READ_K1YEAR の台本と同じ。
R2 年ごとに 3 つに分ける: 両方にある取引(共通)・参照にだけある取引・段階 G にだけある取引。それぞれの本数と
   損益の和(bp)。段階 G の損益は向き × (出の値 / 入りの値 − 1) × 1e4(READ_K1YEAR の台本と同じ)。
R3 年の損益の差(参照 − 段階 G)を恒等式で分ける:
   差 = 参照にだけある取引の和 − 段階 G にだけある取引の和 + 共通の取引の損益の差の和(出の時刻・値が違う分)。
   3 つの項のどれが差の大部分かを読む。境は置かない(A-12)。
R4 共通の取引のうち、出の時刻が違うものの本数も出す(持ち高の道が分かれた跡)。
R5 足は 5・15 分(段階 G に 2017 年からの走らせがある足)。年は 2019〜2022(READ_K1YEAR で数えた範囲)。経費なし。

出力: limit_sim/runs/READ_K1YEAR/MATCH.md と match.json。

    python3 scripts/w4_measure/c2_ref_vs_g_match.py
"""
from __future__ import annotations

import gzip
import json
import math
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
RUNS = os.path.join(REPO, "docs", "RESEARCH", "cards", "c2_owner_xvenue_wick", "limit_sim", "runs")
G_DIR = os.path.join(REPO, "docs", "PHASE2", "K1", "NEWENV_G")
G_RUNS = os.path.join(REPO, "backtest_runs_shared", "k1_newenv_g")
FEET = (5, 15)
YEARS = (2019, 2020, 2021, 2022)
NS = 10**9


def year_of(entry_ns: int, foot: int) -> int:
    return datetime.fromtimestamp((entry_ns - foot * 60 * NS) // NS, tz=timezone.utc).year


def ref_trades(o: dict) -> list[tuple]:
    """(entry_t_ns, side ±1, exit_t_ns, pnl_bp)。"""
    return [(int(o["entry_t_ns"][i]), int(o["side"][i]), int(o["exit_t_ns"][i]), float(o["pnl_bp"][i]))
            for i in range(len(o["pnl_bp"]))]


def g_trades(data: list[dict]) -> list[tuple]:
    out = []
    for x in data:
        sig = 1 if x["side"] == "buy" else -1
        out.append((int(x["entry_t_ns"]), sig, int(x["exit_t_ns"]), sig * (x["exit_px"] / x["entry_px"] - 1.0) * 1e4))
    return out


def match_year(ref: list[tuple], g: list[tuple]) -> dict:
    """R2〜R4。同じ年の取引どうし。同じ鍵が片側に複数あれば、時刻順に 1 対 1 で組む。"""
    def bykey(ts):
        d: dict = {}
        for t in sorted(ts):
            d.setdefault((t[0], t[1]), []).append(t)
        return d
    R, G = bykey(ref), bykey(g)
    common, r_only, g_only = [], [], []
    for k in set(R) | set(G):
        a, b = R.get(k, []), G.get(k, [])
        n = min(len(a), len(b))
        common += list(zip(a[:n], b[:n]))
        r_only += a[n:]
        g_only += b[n:]
    s = lambda xs: math.fsum(x[3] for x in xs)
    return {
        "common_n": len(common), "r_only_n": len(r_only), "g_only_n": len(g_only),
        "r_only_bp": s(r_only), "g_only_bp": s(g_only),
        "common_diff_bp": math.fsum(a[3] - b[3] for a, b in common),
        "common_exit_differs_n": sum(1 for a, b in common if a[2] != b[2]),
        "diff_bp": s(ref) - s(g),
    }


def main() -> int:
    cells = json.load(open(os.path.join(G_DIR, "cells.json"), encoding="utf-8"))
    out = {}
    L = ["# カツオ: 参照と段階 G の取引の 1 本ずつの突き合わせ", "",
         "`scripts/w4_measure/c2_ref_vs_g_match.py` が出した。読み方の決まり R1〜R5 はその台本の docstring。経費の前。bp。", "",
         "| 足 | 年 | 共通 | 参照だけ | 段階 G だけ | 差(参照 − 段階 G) | = 参照だけの和 | − 段階 G だけの和 | + 共通の差の和 | 共通で出が違う本数 |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for f in FEET:
        with gzip.open(os.path.join(RUNS, f"weak_f{f}_close_a", "trades.json.gz"), "rt", encoding="utf-8") as fh:
            ref = ref_trades(json.load(fh))
        rid = cells[f"design|full|{f}|s19/b24|weak"]["run_id"]
        with gzip.open(os.path.join(G_RUNS, rid, "trades.json.gz"), "rt", encoding="utf-8") as fh:
            g = g_trades(json.load(fh)["data"])
        for y in YEARS:
            m = match_year([t for t in ref if year_of(t[0], f) == y], [t for t in g if year_of(t[0], f) == y])
            out[f"{f}|{y}"] = m
            L.append(f"| {f} 分 | {y} | {m['common_n']:,} | {m['r_only_n']:,} | {m['g_only_n']:,} | {m['diff_bp']:+,.2f} | "
                     f"{m['r_only_bp']:+,.2f} | {-m['g_only_bp']:+,.2f} | {m['common_diff_bp']:+,.2f} | {m['common_exit_differs_n']:,} |")
    od = os.path.join(RUNS, "READ_K1YEAR")
    with open(os.path.join(od, "MATCH.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    with open(os.path.join(od, "match.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"-> {od}/MATCH.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())

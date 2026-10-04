#!/usr/bin/env python3
"""カツオの門あり − 門なしの差を、取引を 1 本ずつ突き合わせて分ける(直前 365 日の門の関門 ② の 1 回目の直す 1・2 を受けて足した)。

`runs/READ_RGATED/RESULTS.md` の監査(`docs/AUDITOR/VERDICTS/2026-10-04_c2_rgated_read.md`)の後に足した。R1〜R5 は変えていない。

鍵 = (建ての時刻 entry_t_ns, 向き)。門ありと門なしの取引を突き合わせ、範囲(建ての時刻の UTC の年)ごとに
  差 = 共通の取引の門ありの和 − 共通の取引の門なしの和 + 門ありにだけある取引の和 − 門なしにだけある取引(門で切った取引)の和
に分ける。共通の取引の和が門あり・門なしで違うのは、門で持ち高の道が変わり、出の時刻・値段が変わった分。
範囲は 2022〜2023 年(K-038・表 3 と同じ)と 2020〜2023 年。経費なし。

    python3 scripts/w4_measure/c2_read_gated_decomp.py [--root <runs>] [--tag gate|rgate]
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c2_read_gated as rg  # noqa: E402
import c2_read_limit as rl  # noqa: E402

RANGES = {"2022〜2023": (2022, 2023), "2020〜2023": (2020, 2023)}


def load(d: str) -> list[tuple]:
    with gzip.open(os.path.join(d, "trades.json.gz"), "rt", encoding="utf-8") as fh:
        o = json.load(fh)
    assert o["t_unit"] == "ns"
    return [((int(o["entry_t_ns"][i]), int(o["side"][i])), float(o["pnl_bp"][i])) for i in range(len(o["pnl_bp"]))]


def year_of(key: tuple) -> int:
    return datetime.fromtimestamp(key[0] // 10**9, tz=timezone.utc).year


def decomp(gated: list[tuple], ungated: list[tuple], lo: int, hi: int) -> dict:
    G, U = {}, {}
    for k, p in gated:
        if lo <= year_of(k) <= hi:
            G.setdefault(k, []).append(p)
    for k, p in ungated:
        if lo <= year_of(k) <= hi:
            U.setdefault(k, []).append(p)
    cg, cu, go, uo = [], [], [], []
    for k in set(G) | set(U):
        a, b = G.get(k, []), U.get(k, [])
        n = min(len(a), len(b))
        cg += a[:n]
        cu += b[:n]
        go += a[n:]
        uo += b[n:]
    s = math.fsum
    return {"common_n": len(cg), "common_gated": s(cg), "common_ungated": s(cu),
            "gated_only_n": len(go), "gated_only": s(go), "cut_n": len(uo), "cut": s(uo),
            "total": s(cg) + s(go) - s(cu) - s(uo)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=rl.DEFAULT_ROOT)
    ap.add_argument("--tag", default="rgate", choices=["gate", "rgate"])
    a = ap.parse_args(argv)
    names = {n for n in os.listdir(a.root) if os.path.isfile(os.path.join(a.root, n, "summary.json"))}
    out = {}
    L = [f"# カツオ: 門あり − 門なしを取引 1 本ずつの突き合わせで分ける(門 = {'直前 365 日の境目' if a.tag == 'rgate' else 'K1 の固定の境目'})", "",
         "`scripts/w4_measure/c2_read_gated_decomp.py` が出した(関門 ② の 1 回目の後に足した)。経費の前。bp の和。年 = 建ての時刻の UTC の年"
         "(summary の年とは割り方が違い、和は少しずれる)。", "",
         "| 門あり | 範囲 | 差 | 共通 本数・門ありの和・門なしの和 | 門ありにだけ 本数・和 | 門で切った 本数・和 |",
         "|---|---|---|---|---|---|"]
    for g, u in rg.pairs(names, a.tag):
        gt, ut = load(os.path.join(a.root, g)), load(os.path.join(a.root, u))
        for label, (lo, hi) in RANGES.items():
            r = decomp(gt, ut, lo, hi)
            out[f"{g}|{label}"] = r
            L.append(f"| {g} | {label} | {r['total']:+,.0f} | {r['common_n']:,}・{r['common_gated']:+,.0f}・{r['common_ungated']:+,.0f} | "
                     f"{r['gated_only_n']:,}・{r['gated_only']:+,.0f} | {r['cut_n']:,}・{r['cut']:+,.0f} |")
    od = os.path.join(a.root, "READ_RGATED" if a.tag == "rgate" else "READ_GATED")
    with open(os.path.join(od, "DECOMP.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    with open(os.path.join(od, "decomp.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"-> {od}/DECOMP.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())

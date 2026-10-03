#!/usr/bin/env python3
"""カツオ(ヒゲ逆張り、カード 2)の門ありの再現 16 本と、門なしの同じ設定を並べる表を作る。

SPEC §9-1 の「門あり 5・15 分 × 入り方 3」(`limit_sim/SPEC.md` 129 行)。門 = K1 の境目
(`results/PHASE2/K1/xvenue/vol_terciles.json`、2018〜2019 年の取引の前 100 本のボラの三分位)で、
合図の時点のボラが低の三分位なら入らない。読み方の決まり(16 本を並べて見る前に、この台本と
`tests/research/test_c2_read_gated.py` で固めた。research-protocol §0.7 の 7):

R1 比べる相手: 門ありの各走らせ(weak_f<足>_gate_<型>)と、同じ足・同じ型・同じ側の門なし(weak_f<足>_<型>)。
   型 = limit_<入り方>_<側>(入り方 a・b・c、側 good・bad)と close_<入り方>(入り方 a・b)。
R2 出すもの: 1 日あたりの損益と取引の数、1 取引あたりの損益、それぞれ 門あり − 門なし。指値の型は
   良い側と悪い側の差の符号で「増える / 減る(両側)」「側で割れる」(c2_read_limit.label と同じ)。境は置かない(A-12)。
R3 境目を決めた期間の外: 門の境目は 2018〜2019 年の取引から決めた(in-sample)。2017 年は先読み。そこで
   2020〜2023 年の年の損益の和を 2020-01-01〜2023-12-17 の日数(1447 日)で割った 1 日あたりの差も出す。
   読みの主はこちら(境目を決めた期間の外)。
R4 年ごとの安定: 2020〜2023 の 4 年で、年の損益の差(門あり − 門なし)の符号が R3 の差の符号と同じ年の数を「n/4」。
R5 経費なし。探索の読みで判定ではない。門の境目は K1 の値をそのまま使い、決め直さない。

出力: runs/READ_GATED/TABLES.md と read.json。数字は手で書かない(research-protocol §1.2)。

    python3 scripts/w4_measure/c2_read_gated.py [--root <runs>]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c2_read_limit as rl  # noqa: E402

OOS_YEARS = (2020, 2021, 2022, 2023)
OOS_DAYS = 1447  # 2020-01-01〜2023-12-17(両端を含む)
FEET = (5, 15)


def pairs(names: set[str]) -> list[tuple[str, str]]:
    """R1。(門あり, 門なし) の組。両方がある組だけ。"""
    out = []
    for f in FEET:
        types = [f"limit_{e}_{s}" for e in ("a", "b", "c") for s in rl.SIDES] + [f"close_{e}" for e in ("a", "b")]
        for t in types:
            g, u = f"weak_f{f}_gate_{t}", f"weak_f{f}_{t}"
            if g in names and u in names:
                out.append((g, u))
    return out


def oos_per_day(run: dict) -> float:
    """R3。2020〜2023 年の年の損益の和 ÷ 1447 日。"""
    return sum(run["year_pnl"].get(y, 0.0) for y in OOS_YEARS) / OOS_DAYS


def oos_year_agreement(g: dict, u: dict) -> int:
    """R4。"""
    sgn = np.sign(oos_per_day(g) - oos_per_day(u))
    return sum(1 for y in OOS_YEARS
               if sgn != 0 and np.sign(g["year_pnl"].get(y, 0.0) - u["year_pnl"].get(y, 0.0)) == sgn)


def compare(runs: dict) -> list[dict]:
    rows = []
    for g, u in pairs(set(runs)):
        G, U = runs[g], runs[u]
        rows.append({
            "gated": g, "ungated": u,
            "d_pnl_day": G["per_day"]["pnl"] - U["per_day"]["pnl"],
            "d_trades_day": G["per_day"]["trades"] - U["per_day"]["trades"],
            "d_per_trade": G["per_trade"] - U["per_trade"],
            "oos_gated": oos_per_day(G), "oos_ungated": oos_per_day(U),
            "d_oos_day": oos_per_day(G) - oos_per_day(U),
            "oos_years_agree": oos_year_agreement(G, U),
        })
    return rows


def side_labels(rows: list[dict]) -> dict[str, str]:
    """R2。指値の型ごと(足・入り方)に、良い側と悪い側の R3 の差から向きのラベル。"""
    by = {r["gated"]: r for r in rows}
    out = {}
    for f in FEET:
        for e in ("a", "b", "c"):
            kg, kb = f"weak_f{f}_gate_limit_{e}_good", f"weak_f{f}_gate_limit_{e}_bad"
            if kg in by and kb in by:
                out[f"f{f}_limit_{e}"] = rl.label(by[kg]["d_oos_day"], by[kb]["d_oos_day"])
    return out


def render(runs: dict, rows: list[dict], labels: dict[str, str]) -> str:
    L = ["# カツオ: 門あり(K1 の境目、合図の時点のボラが低なら入らない)と門なしの比べ", "",
         "`scripts/w4_measure/c2_read_gated.py` が出した。読み方の決まり R1〜R5 はその台本の docstring。経費の前。", "",
         "## 表 1: 門あり − 門なし(全期間と、境目を決めた期間の外の 2020〜2023 年)", "",
         "| 門あり | 1 日あたり損益の差(全期間) | 取引の数の差 /日 | 1 取引あたりの差 | 2020〜2023 の 1 日あたり 門あり / 門なし | その差 | 年の一致 |",
         "|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['gated']} | {rl._f(r['d_pnl_day'], 2)} | {rl._f(r['d_trades_day'], 3)} | {rl._f(r['d_per_trade'], 2)} | "
                 f"{r['oos_gated']:+.2f} / {r['oos_ungated']:+.2f} | {rl._f(r['d_oos_day'], 2)} | {r['oos_years_agree']}/4 |")
    L += ["", "## 表 2: 指値の型ごとの向き(2020〜2023 の差、良い側と悪い側)", "", "| 型 | 向き |", "|---|---|"]
    for k, v in labels.items():
        L.append(f"| {k} | {v} |")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=rl.DEFAULT_ROOT)
    a = ap.parse_args(argv)
    names = [n for n in os.listdir(a.root) if os.path.isfile(os.path.join(a.root, n, "summary.json"))]
    want = {x for p in pairs(set(names)) for x in p}
    runs = {n: rl.load_run(os.path.join(a.root, n)) for n in names if n in want}
    rows = compare(runs)
    labels = side_labels(rows)
    out = os.path.join(a.root, "READ_GATED")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "TABLES.md"), "w", encoding="utf-8") as fh:
        fh.write(render(runs, rows, labels))
    with open(os.path.join(out, "read.json"), "w", encoding="utf-8") as fh:
        json.dump({"rows": rows, "labels": labels}, fh, ensure_ascii=False, indent=1)
    print(f"pairs {len(rows)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

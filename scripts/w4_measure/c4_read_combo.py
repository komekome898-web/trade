#!/usr/bin/env python3
"""マチルダ(レンジ、カード 4)の組み合わせ C(中心から測る利確 × 5 分足のレンジの物差し)の読みの表を作る。

L-620「1〜3はそれですすめて」の 1(判断の束 書き直し版の 1)。読み方の決まり(C の 16 本を走らせる前に、この台本と
`tests/research/test_c4_read_combo.py` で固めた):

R1 4 つの走らせ(同じ側): 基準 = v37、利確だけ = A1_center_<e>_<x>(物差しは v37 の 1 分足 40 分)、
   物差しだけ = A3_w<w>_b5_body(利確は v37)、両方 = C_center_<e>_<x>_w<w>_b5_body。
R2 1 日あたりで、利確だけの差 = 利確だけ − 基準、物差しだけの差 = 物差しだけ − 基準、両方の差 = 両方 − 基準、
   重なりの分 = 両方の差 − 利確だけの差 − 物差しだけの差。軸は 損益・小勝ちの和・大負けの和・ブレイクで閉じた取引の和
   (c4_read_r2 の load_run と同じ)。重なりの分が 0 でなければ足し算にならない。
R3 向きのラベル: 両方の差と重なりの分それぞれで、良い側と悪い側の符号から c4_read_r2.label。境は置かない(A-12)。
R4 年ごとの安定: 2016〜2023 の 8 年で、両方の年の損益と、利確だけ・物差しだけの良い方の年の損益の差の符号が、
   全期間のその差の符号と同じ年の数(c4_read_r2.year_agreement と同じ数え方を、相手を「良い方の単独」にして当てる)。
   「良い方の単独」= 同じ側の全期間の損益が大きいほう。
R5 経費なし。探索の読みで判定ではない。

出力: families_r2/READ_COMBO/TABLES.md と read.json。

    python3 scripts/w4_measure/c4_read_combo.py [--root <families_r2>]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c4_read_r2 as r2  # noqa: E402

CENTERS = ((2, 0.8), (3, 2), (4, 3), (5, 1))
RULERS = ((20, 5, "body"), (40, 5, "body"))
SIDES = ("good", "bad")
AXES = ("pnl", "small_win", "big_loss", "closed_by_break")
YEARS = tuple(range(2016, 2024))


def names_for(e, x, w, b, r, side: str) -> dict:
    return {"base": f"v37_{side}", "tp": f"A1_center_{e}_{x}_{side}", "ruler": f"A3_w{w}_b{b}_{r}_{side}",
            "both": f"C_center_{e}_{x}_w{w}_b{b}_{r}_{side}"}


def split(v: dict) -> dict:
    """R2。v = {base, tp, ruler, both} の値。"""
    tp, ru, bo = v["tp"] - v["base"], v["ruler"] - v["base"], v["both"] - v["base"]
    return {"tp": tp, "ruler": ru, "both": bo, "interaction": bo - tp - ru}


def year_agree_vs_best_single(runs: dict, nm: dict) -> int:
    """R4。"""
    best = nm["tp"] if runs[nm["tp"]]["per_day"]["pnl"] >= runs[nm["ruler"]]["per_day"]["pnl"] else nm["ruler"]
    return r2.year_agreement(runs[nm["both"]], runs[best])


def decompose(runs: dict) -> list[dict]:
    rows = []
    for e, x in CENTERS:
        for w, b, r in RULERS:
            row = {"center": f"{e}:{x}", "ruler": f"{b} 分足 {w} 分 {r}"}
            ok = True
            for side in SIDES:
                nm = names_for(e, x, w, b, r, side)
                if not all(n in runs for n in nm.values()):
                    ok = False
                    break
                row[side] = {ax: split({k: runs[n]["per_day"][ax] for k, n in nm.items()}) for ax in AXES}
                row[f"years_{side}"] = year_agree_vs_best_single(runs, nm)
            if not ok:
                continue
            row["labels"] = {k: r2.label(row["good"]["pnl"][k], row["bad"]["pnl"][k]) for k in ("both", "interaction")}
            rows.append(row)
    return rows


def render(rows: list[dict]) -> str:
    L = ["# マチルダ: 中心から測る利確 × 5 分足のレンジの物差し(組み合わせ C)", "",
         "`scripts/w4_measure/c4_read_combo.py` が出した。読み方の決まり R1〜R5 はその台本の docstring。経費の前。1 日あたり bp、v37 との差。", "",
         "## 表 1: 損益の差(良い側 / 悪い側)", "",
         "| 利確 | 物差し | 利確だけ | 物差しだけ | 両方 | 重なりの分 | 向き(両方・重なり) | 年の一致(両方 − 良い方の単独) |",
         "|---|---|---|---|---|---|---|---|"]
    for row in rows:
        g, bd = row["good"]["pnl"], row["bad"]["pnl"]
        c = lambda k: f"{g[k]:+.2f} / {bd[k]:+.2f}"
        L.append(f"| {row['center']} | {row['ruler']} | {c('tp')} | {c('ruler')} | {c('both')} | {c('interaction')} | "
                 f"{row['labels']['both']}・{row['labels']['interaction']} | {row['years_good']}/8 ・ {row['years_bad']}/8 |")
    for ax, title in (("small_win", "小勝ちの和"), ("big_loss", "大負けの和"), ("closed_by_break", "ブレイクで閉じた取引の和")):
        L += ["", f"## {title}の差(良い側 / 悪い側)", "", "| 利確 | 物差し | 利確だけ | 物差しだけ | 両方 | 重なりの分 |",
              "|---|---|---|---|---|---|"]
        for row in rows:
            g, bd = row["good"][ax], row["bad"][ax]
            c = lambda k: f"{g[k]:+.2f} / {bd[k]:+.2f}"
            L.append(f"| {row['center']} | {row['ruler']} | {c('tp')} | {c('ruler')} | {c('both')} | {c('interaction')} |")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.join(r2.REPO, "docs", "RESEARCH", "cards", "c4_owner_matilda_range",
                                                    "limit_sim", "families_r2"))
    a = ap.parse_args(argv)
    want = {n for e, x in CENTERS for w, b, r in RULERS for s in SIDES for n in names_for(e, x, w, b, r, s).values()}
    runs = {n: r2.load_run(os.path.join(a.root, n)) for n in want
            if os.path.isfile(os.path.join(a.root, n, "analysis.json"))}
    rows = decompose(runs)
    out = os.path.join(a.root, "READ_COMBO")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "TABLES.md"), "w", encoding="utf-8") as fh:
        fh.write(render(rows))
    with open(os.path.join(out, "read.json"), "w", encoding="utf-8") as fh:
        json.dump({"rows": rows}, fh, ensure_ascii=False, indent=1, default=float)
    print(f"rows {len(rows)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

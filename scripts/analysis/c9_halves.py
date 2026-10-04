#!/usr/bin/env python3
"""カード 9 (a) の保存済みの出力(`data/c9_run_a/full_20230625_20241014/` の `anchors_prints.csv.gz`・`controls.csv.gz`)から、
清算のプリントの後の値動き(react_h、清算の向きに正)を前半・後半に分けて出す読み口。新しい走らせはしない。

前半・後半 = 走らせの「作る日」2023-06-25〜2024-02-18 /「測る日」2024-02-19〜2024-10-14(`three_way_model.json`。結果を見る前の分け方)。
値 = 日ごとの平均(その日のプリントの平均)を日で等しく平均したもの。区間 = 日の塊(循環、5 日・1,000 回・種 20261004)の 95%。
組の差 = 対照の ref_id をプリントの print_id につないだ組の react(プリント)− react(対照)、日 = プリントの日。

    PYTHONPATH=src:scripts/analysis python3 scripts/analysis/c9_halves.py --data data/c9_run_a/full_20230625_20241014 --out <出力.md>
"""
from __future__ import annotations

import argparse

import pandas as pd

from diag_tables import mean_ci, diff_ci

H = (5, 60, 300, 3600, 14400)
SPLIT = "2024-02-19"


def day_means(df: pd.DataFrame, col: str) -> pd.Series:
    return df.dropna(subset=[col]).groupby("day")[col].mean()


def cell(s: pd.Series) -> str:
    if len(s) == 0:
        return "—(組が無い)"
    r = mean_ci(list(s.values))
    if r["lo"] is None:
        return f"{r['mean']:+.3f}(区間なし)"
    return f"{r['mean']:+.3f} [{r['lo']:+.3f}, {r['hi']:+.3f}]"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    cols = ["print_id", "day", "side"] + [f"react_{h}" for h in H]
    P = pd.read_csv(f"{a.data}/anchors_prints.csv.gz", usecols=cols)
    C = pd.read_csv(f"{a.data}/controls.csv.gz", usecols=["kind", "day", "ref_id"] + [f"react_{h}" for h in H])
    kinds = sorted(C["kind"].unique())
    L = ["# カード 9 (a) 清算のプリントの後の値動き(前半・後半)", "",
         "読み口 `scripts/analysis/c9_halves.py`(保存済みの出力から計算。新しい走らせではない)。react_h = プリントの時刻から h 秒後の値段の変化(bp)× 清算の向き"
         "(正 = 清算の向きに続く、負 = 清算と逆へ戻る)。Binance COIN-M BTCUSD。", "",
         f"前半 = 〜{SPLIT} の前日(走らせの作る日)、後半 = {SPLIT}〜(測る日)。日で等しく平均。区間は日の塊。対照の種類: {', '.join(kinds)}", ""]
    for h in H:
        col = f"react_{h}"
        L += [f"## h = {h} 秒", "", "| 群 | 全期間 | 前半 | 後半 | 後半 − 前半 |", "|---|---|---|---|---|"]
        groups = [("実(全プリント)", P)] + [(f"対照 {k}", C[C["kind"] == k]) for k in kinds]
        for name, df in groups:
            s = day_means(df, col)
            f, b = s[s.index < SPLIT], s[s.index >= SPLIT]
            d = diff_ci(list(f.values), list(b.values))
            L.append(f"| {name} | {cell(s)} | {cell(f)} | {cell(b)} | {d['mean']:+.3f} [{d['lo']:+.3f}, {d['hi']:+.3f}] |")
        for k in kinds:
            m = C[C["kind"] == k][["ref_id", col]].merge(P[["print_id", "day", col]], left_on="ref_id", right_on="print_id",
                                                         suffixes=("_c", "_p")).dropna()
            m["d"] = m[f"{col}_p"] - m[f"{col}_c"]
            s = m.groupby("day")["d"].mean()
            f, b = s[s.index < SPLIT], s[s.index >= SPLIT]
            if len(m) == 0:
                L.append(f"| 組の差 実 − {k} | 組が無い(ref_id でつながらない) | | | |")
                continue
            dd = diff_ci(list(f.values), list(b.values))
            L.append(f"| 組の差 実 − {k}(組 {len(m):,}) | {cell(s)} | {cell(f)} | {cell(b)} | {dd['mean']:+.3f} [{dd['lo']:+.3f}, {dd['hi']:+.3f}] |")
        L.append("")
    open(a.out, "w", encoding="utf-8").write("\n".join(L))
    print(a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

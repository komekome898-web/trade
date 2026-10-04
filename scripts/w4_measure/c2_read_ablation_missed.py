#!/usr/bin/env python3
"""カツオの入りの分(入りだけ − 参照)を、取り逃した取引の損益と並べる表を作る。

`runs/READ_ABLATION/TABLES.md` の表 1 を見た後に足した(なぜの読みのため。R1〜R5 は変えていない)。
入りだけの走らせ(weak_f<足>_le_cx_<入り方>_good)は、同じ入力の参照の形の物を並走させ、入りの指値が約定しなかった
取引を summary の all.missed に数えている(c2_limit_run.py)。取り逃した取引の損益の和 ÷ 日数 を、入りの分と並べる。
入りの分がほぼ取り逃した取引の損益で説明できるなら、入りの指値の損は「動いてほしい向きにすぐ走った取引に乗れない」分
(逆選択)が主。経費なし。

    python3 scripts/w4_measure/c2_read_ablation_missed.py [--root <runs>]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c2_read_ablation as ra  # noqa: E402
import c2_read_limit as rl  # noqa: E402


def missed_row(entry_only: dict, ref: dict) -> dict:
    """entry_only・ref = summary.json の中身。"""
    a, b = entry_only["all"], ref["all"]
    m = a.get("missed") or {}
    days = float(a["days"])
    pl = m.get("limit_order_placed") or {}
    npl = m.get("limit_order_not_placed") or {}
    return {
        "entry_part": float(a["sum_bp"]) / days - float(b["sum_bp"]) / float(b["days"]),
        "missed_per_day": -float(m.get("sum_bp", 0.0)) / days,
        "missed_trades": int(m.get("trades", 0)),
        "placed_trades": int(pl.get("trades", 0)), "placed_avg": pl.get("avg_bp"), "placed_losses": pl.get("losses"),
        "not_placed_trades": int(npl.get("trades", 0)), "not_placed_avg": npl.get("avg_bp"),
        # 関門 ② の 1 回目の直す 4 の後に足した: 約定しなかった取引の和が参照の総損益に占める割合と、参照の取引の数に占める割合
        "ref_sum_bp": float(b["sum_bp"]), "ref_trades": int(b["trades"]),
        "placed_share_of_ref_pnl": float(pl.get("sum_bp", 0.0)) / float(b["sum_bp"]) if float(b["sum_bp"]) else float("nan"),
        "placed_share_of_ref_trades": int(pl.get("trades", 0)) / max(1, int(b["trades"])),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=rl.DEFAULT_ROOT)
    a = ap.parse_args(argv)
    L = ["# カツオ: 入りの分と、入りの指値で取り逃した取引の損益", "",
         "`scripts/w4_measure/c2_read_ablation_missed.py` が出した(表 1 を見た後に足した)。経費の前。1 日あたり bp。"
         "取り逃しの分 = −(取り逃した取引を参照の形で入っていたら得た損益の和)÷ 日数。", "",
         "| 足 | 入り方 | 入りの分 | 取り逃しの分 | 取り逃した本数 | うち指値を置いて約定しなかった 本数・平均 bp・負けの数 | うち指値を置かなかった 本数・平均 bp | 約定しなかった取引が参照の 取引の数・総損益 に占める割合 |",
         "|---|---|---|---|---|---|---|---|"]
    out = {}
    for f in ra.FEET:
        for e in ra.ENTRIES:
            nm = ra.names_for(f, e, "good")
            pe, pr = os.path.join(a.root, nm["entry_only"], "summary.json"), os.path.join(a.root, nm["ref"], "summary.json")
            if not (os.path.isfile(pe) and os.path.isfile(pr)):
                continue
            r = missed_row(json.load(open(pe, encoding="utf-8")), json.load(open(pr, encoding="utf-8")))
            out[f"{f}|{e}"] = r
            pa = "—" if r["placed_avg"] is None else f"{r['placed_avg']:+.1f}"
            na = "—" if r["not_placed_avg"] is None else f"{r['not_placed_avg']:+.1f}"
            L.append(f"| {f} 分 | {e} | {r['entry_part']:+.2f} | {r['missed_per_day']:+.2f} | {r['missed_trades']:,} | "
                     f"{r['placed_trades']:,}・{pa}・{r['placed_losses']} | {r['not_placed_trades']:,}・{na} | "
                     f"{r['placed_share_of_ref_trades']:.3f}・{r['placed_share_of_ref_pnl']:.3f}(参照の総損益 {r['ref_sum_bp']:+,.0f}) |")
    od = os.path.join(a.root, "READ_ABLATION")
    os.makedirs(od, exist_ok=True)
    with open(os.path.join(od, "MISSED.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    with open(os.path.join(od, "missed.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"rows {len(out)} -> {od}/MISSED.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""カツオ(ヒゲ逆張り、カード 2)の指値と参照(足の終値)の差を、入りの分と降りの分に分ける表を作る。

`limit_sim/runs/READ/RESULTS.md` §3 の 1(関門 ② の 1 回目の止める: 指値の走らせは入りも降りも注文なので、
参照との差に入りと降りが混ざる)。走らせは `c2_limit_batch.py --ablation` の 28 本。読み方の決まり(28 本を
並べて見る前に、この台本と `tests/research/test_c2_read_ablation.py` で固めた。research-protocol §0.7 の 7):

R1 4 つの走らせ(同じ足・同じ入り方・同じ側):
   参照 = close_<a|b>(入りも降りも足の終値。入り方 c の参照は close_b、c2_read_limit.REF と同じ)
   全部 = limit_<入り方>_<側>(入りも降りも指値)
   入りだけ = le_cx_<入り方>_good(入りは指値、降りは足の終値。降りに決まらない足が無いので良い側だけ走らせた)
   降りだけ = ce_lx_<a|b>_<側>(入りは足の終値、降りは指値。入り方 c は入りが終値だと b と同じ取引になるので b を使う)
R2 1 日あたりの損益の差を 3 つに分ける: 入りの分 = 入りだけ − 参照、降りの分 = 降りだけ − 参照、
   重なりの分 = 全部 − 参照 − 入りの分 − 降りの分。重なりの分が 0 でなければ、入りと降りの効きは足し算にならない
   (交互作用)。重なりの分は読みの対象で、誤差として捨てない。
R3 向きのラベル: 入りの分・降りの分・全部の差それぞれで、良い側と悪い側の符号から c2_read_limit.label。
   入りの分は良い側の 1 本しか無いので、両側に同じ値を使う。大きさの境は置かない(A-12)。
R4 1 日あたりの取引の数の差も同じ 3 つに分けて出す(入りの指値が約定しないと取引が減る)。
R5 経費なし。探索の読みで判定ではない。

出力: runs/READ_ABLATION/TABLES.md と read.json。数字は手で書かない(research-protocol §1.2)。

    python3 scripts/w4_measure/c2_read_ablation.py [--root <runs>]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c2_read_limit as rl  # noqa: E402

FEET = (5, 15, 30, 60)
ENTRIES = ("a", "b", "c")


def names_for(f: int, e: str, side: str) -> dict[str, str]:
    """R1。"""
    g = f"weak_f{f}"
    return {"ref": f"{g}_{rl.REF[e]}", "full": f"{g}_limit_{e}_{side}", "entry_only": f"{g}_le_cx_{e}_good",
            "exit_only": f"{g}_ce_lx_{'b' if e == 'c' else e}_{side}"}


def split(vals: dict[str, float]) -> dict[str, float]:
    """R2。vals = {ref, full, entry_only, exit_only} の 1 日あたりの値。"""
    ent = vals["entry_only"] - vals["ref"]
    ex = vals["exit_only"] - vals["ref"]
    tot = vals["full"] - vals["ref"]
    return {"total": tot, "entry": ent, "exit": ex, "interaction": tot - ent - ex}


def decompose(runs: dict) -> list[dict]:
    rows = []
    for f in FEET:
        for e in ENTRIES:
            row = {"foot": f, "entry": e}
            ok = True
            for side in rl.SIDES:
                nm = names_for(f, e, side)
                if not all(n in runs for n in nm.values()):
                    ok = False
                    break
                for ax in ("pnl", "trades"):
                    row[f"{side}_{ax}"] = split({k: runs[n]["per_day"][ax] for k, n in nm.items()})
            if not ok:
                continue
            row["labels"] = {k: rl.label(row["good_pnl"][k], row["bad_pnl"][k])
                             for k in ("total", "entry", "exit", "interaction")}
            rows.append(row)
    return rows


def render(rows: list[dict]) -> str:
    L = ["# カツオ: 指値と参照の差を、入りの分・降りの分・重なりの分に分ける", "",
         "`scripts/w4_measure/c2_read_ablation.py` が出した。読み方の決まり R1〜R5 はその台本の docstring。経費の前。1 日あたり %(損益の率。rl.load_run が前の出力の `*_bp` を / 100 して読む。L-920)。", "",
         "## 表 1: 1 日あたりの損益の差(良い側 / 悪い側)", "",
         "| 足 | 入り方 | 全部の差 | 入りの分 | 降りの分 | 重なりの分 | 向き(全部・入り・降り・重なり) |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        g, b = r["good_pnl"], r["bad_pnl"]
        cell = lambda k: f"{rl._f(g[k], 4)} / {rl._f(b[k], 4)}"
        lab = r["labels"]
        L.append(f"| {r['foot']} 分 | {r['entry']} | {cell('total')} | {cell('entry')} | {cell('exit')} | {cell('interaction')} | "
                 f"{lab['total']}・{lab['entry']}・{lab['exit']}・{lab['interaction']} |")
    L += ["", "## 表 2: 1 日あたりの取引の数の差(良い側 / 悪い側)", "",
          "| 足 | 入り方 | 全部の差 | 入りの分 | 降りの分 | 重なりの分 |", "|---|---|---|---|---|---|"]
    for r in rows:
        g, b = r["good_trades"], r["bad_trades"]
        cell = lambda k: f"{rl._f(g[k], 3)} / {rl._f(b[k], 3)}"
        L.append(f"| {r['foot']} 分 | {r['entry']} | {cell('total')} | {cell('entry')} | {cell('exit')} | {cell('interaction')} |")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=rl.DEFAULT_ROOT)
    a = ap.parse_args(argv)
    want = {n for f in FEET for e in ENTRIES for s in rl.SIDES for n in names_for(f, e, s).values()}
    runs = {n: rl.load_run(os.path.join(a.root, n)) for n in want
            if os.path.isfile(os.path.join(a.root, n, "summary.json"))}
    rows = decompose(runs)
    out = os.path.join(a.root, "READ_ABLATION")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "TABLES.md"), "w", encoding="utf-8") as fh:
        fh.write(render(rows))
    with open(os.path.join(out, "read.json"), "w", encoding="utf-8") as fh:
        json.dump({"rows": rows}, fh, ensure_ascii=False, indent=1)
    print(f"rows {len(rows)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

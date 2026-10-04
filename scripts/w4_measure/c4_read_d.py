#!/usr/bin/env python3
"""マチルダ(レンジ、カード 4)の族 D(ブレイクの負けを直接減らす変種)の読みの表を作る。

L-620「1〜3はそれですすめて」の 2。族 D = D_ratio_gate12.96(レンジの幅がろうそく足に比べて広すぎるときは入らない)・
D_breakclose_m0.5(負けている持ち高を閉じる位置を手前に)・D_breakclose_p0.5(先に)。「同じ」は v37。
「段数を変えても合計をそろえる」は既定がすでにその形(1 段 = 1/段の数)なので走らせない。
読み方の決まり(族 D を走らせる前に、この台本と `tests/research/test_c4_read_d.py` で固めた):

R1〜R5 c4_read_r2 の R1〜R5 をそのまま当てる(v37 との差を同じ側どうし・1 日あたり、軸は 小勝ち・大負け・損益・
   ブレイクで閉じた損益、向きのラベル、2016〜2023 の年の一致、決まらない足を除いた向き)。比べる変種は族 D だけ。
R6 主に読む軸: 族 D の狙いは「ブレイクの負け」なので、ブレイクで閉じた損益の差と大負けの差を先に読み、そのうえで
   損益の差と取引の数の差(比の門は入りを減らす)を読む。境は置かない(A-12)。
R7 経費なし。探索の読みで判定ではない。
R8(走らせる前に足した。批評家の 2 回目 `VERDICTS/2026-10-04_c4_breakout_critic.md`): 閉じる位置の止めで閉じた取引は終わり方
   「閉じる位置で閉じる」(analysis の by_break.closed_by_bcl)で、c = −0.5 では「反対のブレイク」が 0 件になる。そこで R6 の
   主の軸「ブレイクで閉じた損益」は、v37 の closed_by_break と、族 D の closed_by_break + closed_by_bcl(負けている持ち高を
   閉じた取引の和)を比べる軸「負けを閉じた損益」(lose_close)に替える。closed_by_bcl の群が無い走らせは 0 として足す。
R9 R7 の限界として書くもの: 足の頭で止めが足の値幅の外の値段で約定する扱い(既定のブレイクと同じ。手前の止めで約 941 件・
   1,431bp 有利に傾く推定)と、止めで閉じた後に値段が止めの内側へ戻ってからの入り直しを落とす扱い(2019 年で道 224 回)。

出力: <families_r2>/READ_D/TABLES.md と read.json。数字は手で書かない(research-protocol §1.2)。

    python3 scripts/w4_measure/c4_read_d.py [--root <families_r2>]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c4_read_r2 as r2  # noqa: E402

FAMILY = "D"


def lose_close_per_day(analysis: dict, days: float) -> float:
    """R8。負けている持ち高を閉じた取引の和(1 日あたり)= closed_by_break + closed_by_bcl。"""
    bb = analysis["by_break"]
    return (bb["closed_by_break"]["sum_bp"] + (bb.get("closed_by_bcl") or {}).get("sum_bp", 0.0)) / days


def only_d(runs: dict) -> dict:
    """R1。族 D と v37 だけを残す。"""
    return {k: v for k, v in runs.items() if k[0] == "v37" or k[0].split("_")[0] == FAMILY}


def render(rows: list[dict]) -> str:
    f = r2._f
    L = ["# マチルダ: 族 D(ブレイクの負けを直接減らす変種)と v37 の差", "",
         "`scripts/w4_measure/c4_read_d.py` が出した。読み方の決まり R1〜R7 はその台本の docstring。経費の前。bp/日、良い側 / 悪い側。", "",
         "| 変種 | 負けを閉じた損益の差(R8) | 大負けの差 | 向き | 損益の差 | 向き | 取引/日の差 | 小勝ちの差 | 年の一致(良 / 悪) | 決まった取引だけでも同じ向き(良 / 悪) |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['name']} | {f(r['closed_by_break']['d_good'])} / {f(r['closed_by_break']['d_bad'])} | "
                 f"{f(r['big_loss']['d_good'])} / {f(r['big_loss']['d_bad'])} | {r['big_loss']['label']} | "
                 f"{f(r['pnl']['d_good'])} / {f(r['pnl']['d_bad'])} | {r['pnl']['label']} | "
                 f"{f(r['trades']['d_good'])} / {f(r['trades']['d_bad'])} | "
                 f"{f(r['small_win']['d_good'])} / {f(r['small_win']['d_bad'])} | "
                 f"{r['years_good']}/{len(r2.YEARS)} / {r['years_bad']}/{len(r2.YEARS)} | "
                 f"{'はい' if r['decided_good'] else 'いいえ'} / {'はい' if r['decided_bad'] else 'いいえ'} |")
    L += ["", "注: 大負けは負の数。大負けの差が正 = 大負けが小さくなった。"]
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r2.DEFAULT_ROOT)
    a = ap.parse_args(argv)
    runs = {}
    for d in sorted(os.listdir(a.root)):
        p = os.path.join(a.root, d)
        if not os.path.isfile(os.path.join(p, "analysis.json")):
            continue
        name, side = d.rsplit("_", 1)
        if name == "v37" or name.split("_")[0] == FAMILY:
            r = r2.load_run(p)
            r["per_day"]["closed_by_break"] = lose_close_per_day(r["analysis"], r["days"])  # R8: 軸を「負けを閉じた損益」に
            runs[(name, side)] = r
    rows = r2.compare(only_d(runs))
    out = os.path.join(a.root, "READ_D")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "TABLES.md"), "w", encoding="utf-8") as fh:
        fh.write(render(rows))
    with open(os.path.join(out, "read.json"), "w", encoding="utf-8") as fh:
        json.dump({"compare": rows}, fh, ensure_ascii=False, indent=1)
    print(f"rows {len(rows)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

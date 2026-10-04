#!/usr/bin/env python3
"""カツオ(ヒゲ逆張り、カード 2)の長い保有の降り方 12 本と、降り方を足さない同じ設定を並べる表を作る。

L-620「1〜3はそれですすめて」の 3(値段で降りる k = 1・2・3、時間で降りる N = 6・12・24、足 5・15 分)。
読み方の決まり(12 本を走らせる前に、この台本と `tests/research/test_c2_read_exits.py` で固めた):

R1 比べる相手: 各走らせ weak_f<足>_close_a_stop<k> / weak_f<足>_close_a_time<N> と、同じ足の weak_f<足>_close_a
   (入り方 a・終値で約定・弱いだけ・門なし。降り方の切り替えだけが違う)。
R2 出すもの(1 日あたり、降り方あり − なし): 損益・取引の数・勝ちの和・負けの和、と 1 取引あたりの損益の差。
   あわせて、新しい降り方で閉じた取引の本数と損益の和(summary の by_exit_signal の「値段で降りる」「時間で降りる」)。
R3 年ごとの安定: 2018〜2023 の 6 年で、年の損益の差(あり − なし)の符号が全期間の差の符号と同じ年の数を「n/6」
   (c2_read_limit.year_agreement と同じ数え方)。
R4 保有時間の帯ごとの差: 0〜5・5〜30・30〜120・120〜480・480 分〜 の 5 帯で、取引の数と損益の和の差(あり − なし)。
   長い保有を切る降り方なので、どの帯の損益が動いたかを読む(c2_read_limit.hold_sums と同じ帯)。
R5 境は置かない(A-12)。k や N の間で良い悪いの線を引かない。経費なし。探索の読みで判定ではない。

出力: runs/READ_EXITS/TABLES.md と read.json。数字は手で書かない(research-protocol §1.2)。

    python3 scripts/w4_measure/c2_read_exits.py [--root <runs>]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c2_read_limit as rl  # noqa: E402

FEET = (5, 15)
STOPS = (1, 2, 3)
TIMES = (6, 12, 24)
NEW_EXITS = ("値段で降りる", "時間で降りる")


def pairs(names: set[str]) -> list[tuple[str, str]]:
    """R1。(降り方あり, なし) の組。両方がある組だけ。"""
    out = []
    for f in FEET:
        base = f"weak_f{f}_close_a"
        for v in [f"stop{k}" for k in STOPS] + [f"time{n}" for n in TIMES]:
            x = f"{base}_{v}"
            if x in names and base in names:
                out.append((x, base))
    return out


def new_exit(summary_all: dict) -> dict:
    """R2 の後半。新しい降り方で閉じた取引の本数と損益の和(どちらの名前も無ければ 0)。"""
    by = summary_all.get("by_exit_signal") or {}
    return {"trades": sum(int(by[k]["trades"]) for k in NEW_EXITS if k in by),
            "sum_bp": sum(float(by[k]["sum_bp"]) for k in NEW_EXITS if k in by)}


def hold_diff(x: list[dict] | None, b: list[dict] | None) -> list[dict] | None:
    """R4。"""
    if x is None or b is None:
        return None
    return [{"lo": p["lo"], "hi": p["hi"], "d_trades": p["trades"] - q["trades"], "d_sum_bp": p["sum_bp"] - q["sum_bp"]}
            for p, q in zip(x, b)]


def compare(runs: dict, alls: dict) -> list[dict]:
    rows = []
    for x, b in pairs(set(runs)):
        X, B = runs[x], runs[b]
        dX, dB = X["days"], B["days"]
        rows.append({
            "variant": x, "base": b,
            "d_pnl_day": X["per_day"]["pnl"] - B["per_day"]["pnl"],
            "d_trades_day": X["per_day"]["trades"] - B["per_day"]["trades"],
            "d_win_day": alls[x]["sum_win_bp"] / dX - alls[b]["sum_win_bp"] / dB,
            "d_loss_day": alls[x]["sum_loss_bp"] / dX - alls[b]["sum_loss_bp"] / dB,
            "d_per_trade": X["per_trade"] - B["per_trade"],
            "new_exit": new_exit(alls[x]),
            "years_agree": rl.year_agreement(X, B),
            "hold": hold_diff(X["hold"], B["hold"]),
        })
    return rows


def _band(lo, hi) -> str:
    return f"{lo}〜{hi} 分" if hi is not None else f"{lo} 分〜"


def render(rows: list[dict]) -> str:
    L = ["# カツオ: 長い保有の降り方(値段で降りる・時間で降りる)と降り方なしの比べ", "",
         "`scripts/w4_measure/c2_read_exits.py` が出した。読み方の決まり R1〜R5 はその台本の docstring。経費の前。bp。", "",
         "## 表 1: 降り方あり − なし(1 日あたり)", "",
         "| 降り方あり | 損益の差 | 取引の数の差 | 勝ちの和の差 | 負けの和の差 | 1 取引あたりの差 | 新しい降り方で閉じた本数・損益の和 | 年の一致 |",
         "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        ne = r["new_exit"]
        L.append(f"| {r['variant']} | {rl._f(r['d_pnl_day'], 2)} | {rl._f(r['d_trades_day'], 3)} | {rl._f(r['d_win_day'], 2)} | "
                 f"{rl._f(r['d_loss_day'], 2)} | {rl._f(r['d_per_trade'], 2)} | {ne['trades']:,} 本・{ne['sum_bp']:+,.0f} | "
                 f"{r['years_agree']}/{len(rl.YEARS)} |")
    L += ["", "## 表 2: 保有時間の帯ごとの差(あり − なし。取引の数 / 損益の和 bp)", ""]
    bands = next((r["hold"] for r in rows if r["hold"]), None)
    if bands:
        L += ["| 降り方あり | " + " | ".join(_band(h["lo"], h["hi"]) for h in bands) + " |",
              "|---|" + "---|" * len(bands)]
        for r in rows:
            if r["hold"]:
                L.append(f"| {r['variant']} | " + " | ".join(f"{h['d_trades']:+,} / {h['d_sum_bp']:+,.0f}" for h in r["hold"]) + " |")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=rl.DEFAULT_ROOT)
    a = ap.parse_args(argv)
    names = [n for n in os.listdir(a.root) if os.path.isfile(os.path.join(a.root, n, "summary.json"))]
    want = {x for p in pairs(set(names)) for x in p}
    runs, alls = {}, {}
    for n in want:
        d = os.path.join(a.root, n)
        runs[n] = rl.load_run(d)
        with open(os.path.join(d, "summary.json"), encoding="utf-8") as fh:
            alls[n] = json.load(fh)["all"]
    rows = compare(runs, alls)
    out = os.path.join(a.root, "READ_EXITS")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "TABLES.md"), "w", encoding="utf-8") as fh:
        fh.write(render(rows))
    with open(os.path.join(out, "read.json"), "w", encoding="utf-8") as fh:
        json.dump({"rows": rows}, fh, ensure_ascii=False, indent=1)
    print(f"pairs {len(rows)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

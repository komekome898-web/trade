"""第 6 部(手 2: `int()` 切り捨ての有無)の表を 2 つの JSON から生成する(手打ちしない)。

    python scripts/render_k1_trunc_compare.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
K1 = REPO / "docs" / "PHASE2" / "K1"
LABEL = {"strong": "強い", "weak": "弱い"}


def star(c):
    lo, hi = c["ci95_bp"]
    return "*" if (lo > 0 or hi < 0) else ""


def fmt(c):
    s = star(c)
    v = f"{c['mean_bp']:+.2f}{s}"
    return f"**{v}**" if s else v


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate", default="s19/b24")
    ap.add_argument("--dir", default=str(K1), help="JSON のあるディレクトリ")
    args = ap.parse_args()
    T = json.loads((Path(args.dir) / "signal_horizon.json").read_text("utf-8"))
    N = json.loads((Path(args.dir) / "signal_horizon_notrunc.json").read_text("utf-8"))
    assert T.get("trunc", True) is True and N["trunc"] is False
    CT, CN = T["cells"], N["cells"]

    print(f"### 表 G — 門 `{args.gate}`: 原典どおり(切り捨てあり)と切り捨てなし\n")
    print("| 足 | 強さ | h | 原典 平均 | 原典 n | 切り捨てなし 平均 | 切り捨てなし n | n の増分 | 符号 |")
    print("|---|---|---|---|---|---|---|---|---|")
    rows = flips = 0
    for foot in T["family"]["feet"]:
        for s in ("strong", "weak"):
            for h in (1, 2, 3, 5):
                a = CT.get(f"{foot}|{args.gate}|{s}|{h}")
                b = CN.get(f"{foot}|{args.gate}|{s}|{h}")
                if not a or not b:
                    continue
                rows += 1
                flip = (a["mean_bp"] > 0) != (b["mean_bp"] > 0)
                flips += flip
                print(f"| {foot} 分 | {LABEL[s]} | {h} | {fmt(a)} | {a['n']:,} | {fmt(b)} | {b['n']:,} | "
                      f"{100 * (b['n'] / a['n'] - 1):+.1f}% | {'**反転**' if flip else '同じ'} |")
    print(f"\n**{rows} 行中、符号が変わった行 {flips}。**\n")

    print("### 表 H — 1 分足・h=1: 13 門すべて\n")
    print("| 門 | 強い 原典 | 強い 切り捨てなし | 強い n(原典 → なし) | 弱い 原典 | 弱い 切り捨てなし |")
    print("|---|---|---|---|---|---|")
    for g in T["family"]["gates"]:
        a1, b1 = CT.get(f"1|{g}|strong|1"), CN.get(f"1|{g}|strong|1")
        a2, b2 = CT.get(f"1|{g}|weak|1"), CN.get(f"1|{g}|weak|1")
        if not all((a1, b1, a2, b2)):
            continue
        print(f"| `{g}` | {fmt(a1)} | {fmt(b1)} | {a1['n']:,} → {b1['n']:,} | {fmt(a2)} | {fmt(b2)} |")

    print(f"\n### 族全体({len(CT):,} セル)\n")
    print("| | 0 を跨がないセル | うち正 | うち負 |")
    print("|---|---|---|---|")
    for name, C in (("原典どおり", CT), ("切り捨てなし", CN)):
        sig = [c for c in C.values() if c["ci95_bp"][0] > 0 or c["ci95_bp"][1] < 0]
        print(f"| {name} | {len(sig)} | {sum(c['mean_bp'] > 0 for c in sig)} | {sum(c['mean_bp'] < 0 for c in sig)} |")


if __name__ == "__main__":
    main()
